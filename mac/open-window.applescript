-- Terminal.app に新しいウィンドウを 1 つ開き、渡されたコマンドを実行する。
-- 引数: 実行するコマンドとその引数（css.py が <css.py を動かしている python> launch-session.py <spec> を渡す）
on run argv
	set cmd to ""
	repeat with a in argv
		set cmd to cmd & quoted form of (a as text) & " "
	end repeat
	-- claude が終わったらシェルも終わらせ、ウィンドウを閉じられる状態にする
	set cmd to "exec " & cmd
	tell application "Terminal"
		set t to do script cmd
		-- 新しいウィンドウがほかのウィンドウの後ろに隠れないよう前面に出す
		activate
		return t
	end tell
end run
