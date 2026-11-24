#!/bin/bash
# デスクトップに「Claude セッション復元.command」を作る。
# ダブルクリックすると Terminal が開き、台帳の autostart セッションのうち止まっているものを全部起動する（css restore）。
# ログイン時の自動復元（install-launchagent.sh）を使わない Mac 向け。
#   mac/install-shortcut.sh              作成
#   mac/install-shortcut.sh --update     復元の前に claude update する版を作成
#   mac/install-shortcut.sh --uninstall  削除
set -euo pipefail

file="$HOME/Desktop/Claude セッション復元.command"
if [ "${1:-}" = "--uninstall" ]; then
  rm -f "$file"
  echo "ショートカットを削除しました"
  exit 0
fi

kit="$(cd "$(dirname "$0")/.." && pwd)"
python="$(command -v python3)"
restore="restore"
[ "${1:-}" = "--update" ] && restore="restore --update"

cat > "$file" <<EOF
#!/bin/bash
# claude-session-starter: 止まっているセッションを会話の続きから起動する
cd $(printf '%q' "$kit")
$(printf '%q' "$python") css.py $restore
echo
echo "完了しました。このウィンドウは閉じてかまいません。"
EOF
chmod +x "$file"
echo "作成しました: $file"
echo "デスクトップがウィンドウに隠れている場合は、Finder の「デスクトップ」フォルダから開けます。"
