#!/bin/bash
# ログイン時に台帳の autostart セッションを復元する LaunchAgent を登録する（mac 版の install-tasks.ps1）。
# 常駐用の Mac でだけ使う（普段使いの Mac では登録せず、手動で css restore する）。
#
#   mac/install-launchagent.sh              登録
#   mac/install-launchagent.sh --update     登録。復元の前に claude update する
#   mac/install-launchagent.sh --uninstall  解除
set -euo pipefail

label="com.claude-session-starter.restore"
plist="$HOME/Library/LaunchAgents/$label.plist"
domain="gui/$(id -u)"

if [ "${1:-}" = "--uninstall" ]; then
  launchctl bootout "$domain/$label" 2>/dev/null || true
  rm -f "$plist"
  echo "LaunchAgent を削除しました"
  exit 0
fi

kit="$(cd "$(dirname "$0")/.." && pwd)"
python="$(command -v python3)"
claude="$(command -v claude || true)"
if [ -z "$claude" ]; then
  echo "claude コマンドが PATH に見つかりません" >&2
  exit 1
fi
logdir="${CSS_HOME:-$HOME/.claude-session-starter}/logs"

# launchd に渡す PATH は、実行したシェルの PATH ではなく必要な場所だけで組み立てる
# （どのシェルから実行しても同じ中身になり、重複や ~ の混じった項目が入らない）
path=""
for d in "$(dirname "$claude")" "$(dirname "$python")" "$(dirname "$(command -v git || echo /usr/bin/git)")" \
         /opt/homebrew/bin /usr/local/bin /usr/bin /bin /usr/sbin /sbin; do
  [ -d "$d" ] || continue
  case ":$path:" in *":$d:"*) ;; *) path="${path:+$path:}$d" ;; esac
done
mkdir -p "$logdir" "$HOME/Library/LaunchAgents"

update_arg=""
[ "${1:-}" = "--update" ] && update_arg="<string>--update</string>"

# XML に埋め込む値のエスケープ
esc() { printf '%s' "$1" | sed -e 's/&/\&amp;/g' -e 's/</\&lt;/g' -e 's/>/\&gt;/g'; }

# launchd は PATH が最小限なので、上で組み立てた PATH を渡す（claude や git を見つけるため）
cat > "$plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$label</string>
  <key>ProgramArguments</key>
  <array>
    <string>$(esc "$python")</string>
    <string>$(esc "$kit/css.py")</string>
    <string>restore</string>
    <string>--delay</string><string>30</string>
    $update_arg
  </array>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key><string>$(esc "$path")</string>
$( if [ -n "${CSS_HOME:-}" ]; then printf '    <key>CSS_HOME</key><string>%s</string>\n' "$(esc "$CSS_HOME")"; fi )
  </dict>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>$(esc "$logdir/launchagent.log")</string>
  <key>StandardErrorPath</key><string>$(esc "$logdir/launchagent.log")</string>
</dict>
</plist>
EOF
plutil -lint "$plist" >/dev/null

# 登録し直す。bootstrap は RunAtLoad によりその場で一度実行されるので、
# 登録直後に restore が走る（止まっている autostart セッションが起動される）点に注意
launchctl bootout "$domain/$label" 2>/dev/null || true
launchctl bootstrap "$domain" "$plist"
echo "登録しました: ログイン時の復元${update_arg:+（先に claude update）}"
echo "  plist: $plist"
echo "  ログ:  $logdir/launchagent.log"
echo "約 30 秒後、macOS が「python が Terminal を操作する許可」（オートメーション）を求めることがあります。"
echo "許可しないとログイン時の復元でウィンドウを開けません。"
