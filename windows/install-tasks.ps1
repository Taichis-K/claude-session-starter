# ログオン時に台帳の autostart セッションを復元するタスクを登録する（ログオン中のユーザーとして、画面ありで実行）。
# 解除するときは -Uninstall を付けて実行する。
# 常駐用の PC でだけ使う（普段使いの PC では登録せず、手動で css restore する）。
# -Update を付けると、復元の前に claude update する。
param([switch]$Update, [switch]$Uninstall)

$name = 'ClaudeSessionStarter-Restore'
if ($Uninstall) {
    Unregister-ScheduledTask -TaskName $name -Confirm:$false -ErrorAction SilentlyContinue
    'タスクを削除しました'
    return
}

$css = Join-Path $PSScriptRoot '..\css.py' | Resolve-Path
$pyw = (Get-Command pyw.exe -ErrorAction Stop).Source
$user = "$env:USERDOMAIN\$env:USERNAME"
$principal = New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30)

$logon = New-ScheduledTaskTrigger -AtLogOn -User $user
$logon.Delay = 'PT30S'   # ログオン直後はネットワーク等が未準備のことがあるので少し待つ
Register-ScheduledTask -TaskName $name -Force -Principal $principal -Settings $settings `
    -Trigger $logon -Action (New-ScheduledTaskAction -Execute $pyw -Argument "-3 `"$css`" restore$(if ($Update) { ' --update' })") | Out-Null

"登録しました: ログオン時の復元$(if ($Update) { '（先に claude update）' })"
