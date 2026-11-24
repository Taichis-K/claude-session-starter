# vdesk.ps1 - Windows 11 の仮想デスクトップを扱う（css から使う）
#
#   pwsh -NoProfile -File vdesk.ps1 list                    デスクトップの一覧（JSON: index, name）
#   pwsh -NoProfile -File vdesk.ps1 move <hwnd> <デスクトップ名>  ウィンドウを指定デスクトップへ移す
#
# Windows の非公開 COM インターフェースを使う。インターフェースの GUID とメソッドの並びは
# MScholtes/VirtualDesktop（VirtualDesktop11-24H2.cs）に基づく。Windows の大型アップデートで
# 変わることがあり、そのときは失敗する（css は失敗しても起動自体は続ける）。
#
# 以下の COM 定義は次の著作物に基づく:
#   VirtualDesktop - Copyright (c) 2017 Markus Scholtes
#   MIT License: Permission is hereby granted, free of charge, to any person obtaining a copy of this
#   software and associated documentation files (the "Software"), to deal in the Software without
#   restriction, including without limitation the rights to use, copy, modify, merge, publish,
#   distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the
#   Software is furnished to do so, subject to the following conditions: The above copyright notice
#   and this permission notice shall be included in all copies or substantial portions of the Software.
#   THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED.
param(
    [Parameter(Mandatory, Position = 0)][ValidateSet('list', 'move')][string]$Command,
    [Parameter(Position = 1)][string]$Hwnd,
    [Parameter(Position = 2)][string]$Desktop
)
$ErrorActionPreference = 'Stop'

$src = @'
using System;
using System.Runtime.InteropServices;

namespace CssVDesk {
    internal static class Guids {
        public static readonly Guid CLSID_ImmersiveShell = new Guid("C2F03A33-21F5-47FA-B4BB-156362A2F239");
        public static readonly Guid CLSID_VirtualDesktopManagerInternal = new Guid("C5E0CDCA-7B6E-41B2-9FC4-D93975CC467B");
    }

    // メソッドは呼ばないので並びは不要（型と GUID だけ合っていればよい）。
    // 本来は IInspectable だが、.NET 5 以降（pwsh 7）は IInspectable のマーシャリングに対応しないので IUnknown として扱う
    [ComImport, InterfaceType(ComInterfaceType.InterfaceIsIUnknown), Guid("372E1D3B-38D3-42E4-A15B-8AB2B178F513")]
    internal interface IApplicationView { }

    // GetViewForHwnd（4 番目）まで
    [ComImport, InterfaceType(ComInterfaceType.InterfaceIsIUnknown), Guid("1841C6D7-4F9D-42C0-AF41-8747538F10E5")]
    internal interface IApplicationViewCollection {
        int GetViews(out IObjectArray array);
        int GetViewsByZOrder(out IObjectArray array);
        int GetViewsByAppUserModelId(string id, out IObjectArray array);
        int GetViewForHwnd(IntPtr hwnd, out IApplicationView view);
    }

    // GetName（3 番目）まで。.NET 5 以降は HString のマーシャリングに対応しないので、HSTRING を生のポインタで受ける
    [ComImport, InterfaceType(ComInterfaceType.InterfaceIsIUnknown), Guid("3F07F4BE-B107-441A-AF0F-39D82529072C")]
    internal interface IVirtualDesktop {
        bool IsViewVisible(IApplicationView view);
        Guid GetId();
        IntPtr GetName();
    }

    internal static class HString {
        [DllImport("combase.dll")] static extern IntPtr WindowsGetStringRawBuffer(IntPtr hstring, out uint length);
        [DllImport("combase.dll")] static extern int WindowsDeleteString(IntPtr hstring);
        public static string Take(IntPtr h) {
            if (h == IntPtr.Zero) return "";
            uint len; IntPtr p = WindowsGetStringRawBuffer(h, out len);
            string s = Marshal.PtrToStringUni(p, (int)len);
            WindowsDeleteString(h);
            return s;
        }
    }

    // GetDesktops（5 番目）まで
    [ComImport, InterfaceType(ComInterfaceType.InterfaceIsIUnknown), Guid("53F5CA0B-158F-4124-900C-057158060B27")]
    internal interface IVirtualDesktopManagerInternal {
        int GetCount();
        void MoveViewToDesktop(IApplicationView view, IVirtualDesktop desktop);
        bool CanViewMoveDesktops(IApplicationView view);
        IVirtualDesktop GetCurrentDesktop();
        void GetDesktops(out IObjectArray desktops);
    }

    [ComImport, InterfaceType(ComInterfaceType.InterfaceIsIUnknown), Guid("92CA9DCD-5622-4BBA-A805-5E9F541BD8C9")]
    internal interface IObjectArray {
        void GetCount(out int count);
        void GetAt(int index, ref Guid iid, [MarshalAs(UnmanagedType.Interface)] out object obj);
    }

    [ComImport, InterfaceType(ComInterfaceType.InterfaceIsIUnknown), Guid("6D5140C1-7436-11CE-8034-00AA006009FA")]
    internal interface IServiceProvider10 {
        [return: MarshalAs(UnmanagedType.IUnknown)] object QueryService(ref Guid service, ref Guid riid);
    }

    public static class VDesk {
        static IVirtualDesktopManagerInternal mgr;
        static IApplicationViewCollection views;

        static void Init() {
            if (mgr != null) return;
            var shell = (IServiceProvider10)Activator.CreateInstance(Type.GetTypeFromCLSID(Guids.CLSID_ImmersiveShell));
            Guid s1 = Guids.CLSID_VirtualDesktopManagerInternal, i1 = typeof(IVirtualDesktopManagerInternal).GUID;
            mgr = (IVirtualDesktopManagerInternal)shell.QueryService(ref s1, ref i1);
            Guid s2 = typeof(IApplicationViewCollection).GUID, i2 = s2;
            views = (IApplicationViewCollection)shell.QueryService(ref s2, ref i2);
        }

        static IVirtualDesktop At(int index) {
            IObjectArray arr; mgr.GetDesktops(out arr);
            object o; Guid g = typeof(IVirtualDesktop).GUID;
            arr.GetAt(index, ref g, out o);
            return (IVirtualDesktop)o;
        }

        // 名前が無いデスクトップは Windows の表示に合わせて空文字のまま返す（呼び出し側で番号でも探す）
        public static string[] Names() {
            Init();
            int n = mgr.GetCount();
            var r = new string[n];
            for (int i = 0; i < n; i++) r[i] = HString.Take(At(i).GetName());
            return r;
        }

        public static string[] Ids() {
            Init();
            int n = mgr.GetCount();
            var r = new string[n];
            for (int i = 0; i < n; i++) r[i] = At(i).GetId().ToString();
            return r;
        }

        public static void Move(IntPtr hwnd, int index) {
            Init();
            IApplicationView view;
            int hr = views.GetViewForHwnd(hwnd, out view);
            if (hr != 0 || view == null) throw new Exception("ウィンドウのビューを取得できません (hr=0x" + hr.ToString("X8") + ")");
            mgr.MoveViewToDesktop(view, At(index));
        }
    }
}
'@
if (-not ('CssVDesk.VDesk' -as [type])) { Add-Type -TypeDefinition $src -Language CSharp }

$names = [CssVDesk.VDesk]::Names()
if ($Command -eq 'list') {
    $ids = [CssVDesk.VDesk]::Ids()
    0..($names.Count - 1) | ForEach-Object { [pscustomobject]@{ index = $_ + 1; name = $names[$_]; id = $ids[$_] } } | ConvertTo-Json -AsArray -Compress
    return
}

# move: 名前（完全一致）→ 番号（"2" や "デスクトップ 2" / "Desktop 2"）の順で探す
$idx = [Array]::IndexOf($names, $Desktop)
if ($idx -lt 0 -and $Desktop -match '^\D*(\d+)\s*$') {
    $n = [int]$Matches[1]
    if ($n -ge 1 -and $n -le $names.Count -and [string]::IsNullOrEmpty($names[$n - 1]) -or $Desktop -match '^\d+$') { $idx = $n - 1 }
}
if ($idx -lt 0 -or $idx -ge $names.Count) {
    # css が結果に載せるので、色付きのエラー表示ではなく 1 行の平文で返す
    $have = ($names | ForEach-Object -Begin { $k = 0 } -Process { $k++; if ($_) { $_ } else { "#$k" } }) -join ', '
    [Console]::Error.WriteLine("デスクトップ '$Desktop' が見つかりません（あるもの: $have）")
    exit 2
}
try {
    [CssVDesk.VDesk]::Move([IntPtr][long]$Hwnd, $idx)
} catch {
    [Console]::Error.WriteLine("移動に失敗しました: $($_.Exception.InnerException.Message ?? $_.Exception.Message)")
    exit 1
}
"moved to desktop $($idx + 1)"
