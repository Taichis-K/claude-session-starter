# デスクトップに「Claude セッション復元」のショートカットを作る。
# ダブルクリックすると、台帳の autostart セッションのうち止まっているものを全部起動する（css restore）。
# PC 起動時の自動復元（install-tasks.ps1）を使わない PC 向け。
#   .\windows\install-shortcut.ps1            作成
#   .\windows\install-shortcut.ps1 -Update    復元の前に claude update する版を作成
#   .\windows\install-shortcut.ps1 -Uninstall 削除
param([switch]$Update, [switch]$Uninstall)

$desktop = [Environment]::GetFolderPath('Desktop')
$lnk = Join-Path $desktop 'Claude セッション復元.lnk'
if ($Uninstall) {
    Remove-Item -LiteralPath $lnk -ErrorAction SilentlyContinue
    'ショートカットを削除しました'
    return
}

$kit = Resolve-Path (Join-Path $PSScriptRoot '..')
$pwsh = (Get-Command pwsh.exe -ErrorAction Stop).Source
$restore = if ($Update) { 'restore --update' } else { 'restore' }
# 結果を読めるよう、終わったあと少し待ってから閉じる
$cmd = "& '.\windows\css.cmd' $restore; Write-Host ''; Write-Host '完了しました。10 秒後に閉じます。'; Start-Sleep 10"

$shell = New-Object -ComObject WScript.Shell
$s = $shell.CreateShortcut($lnk)
$s.TargetPath = $pwsh
$s.Arguments = "-NoLogo -NoProfile -Command `"$cmd`""
$s.WorkingDirectory = "$kit"
$s.Description = 'claude-session-starter: 止まっているセッションを会話の続きから起動する'
$s.Save()
"作成しました: $lnk$(if ($Update) { '（先に claude update）' })"
