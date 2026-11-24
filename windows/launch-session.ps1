# 新しい Windows Terminal ウィンドウの中で実行され、claude セッションを 1 つ起動する。
# 起動内容（名前・claude に渡す引数）は css.py が書いた JSON ファイルから読む。
# 空白や日本語を含む値をコマンドラインで渡すと壊れるため。
# claude が終了したらこのスクリプトも終了し、ウィンドウが閉じる。
param([Parameter(Mandatory)][string]$Spec)

$s = Get-Content -LiteralPath $Spec -Raw -Encoding utf8 | ConvertFrom-Json
Remove-Item -LiteralPath $Spec -ErrorAction SilentlyContinue

# 起動元（VS Code 拡張や別の claude）から継承した環境変数を消す。
# 残っていると子セッション扱いになったり、色が出なかったりする。
Get-ChildItem env: |
    Where-Object { $_.Name -match '^(CLAUDE|VSCODE_|ELECTRON_)|^(NO_COLOR|FORCE_COLOR)$' } |
    ForEach-Object { Remove-Item "env:$($_.Name)" }

$Host.UI.RawUI.WindowTitle = $s.name
$claudeArgs = @($s.args)

& claude @claudeArgs
exit 0
