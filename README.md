# claude-session-starter

このマシンで常駐させる Claude Code セッションを台帳で管理し、
**1 セッション = 1 ターミナルウィンドウ**で起動・停止・一括再起動するツール。
VS Code を閉じて開き直すと最後のウィンドウが全部戻るのと同じことを、素の `claude` CLI で行う。

- Windows: Windows Terminal（`wt.exe -w new`）で 1 セッション 1 ウィンドウ
- mac: Terminal.app で 1 セッション 1 ウィンドウ
- 各セッションは `--remote-control <名前>` 付きで起動するので、他マシンの司令塔から `SendMessage` で届く
- 再起動しても `--resume <sessionId>` で会話を引き継ぐ

必要なもの:

- `claude` CLI（claude.ai アカウントでログイン済み。Remote Control を使う）
- Python 3.10 以上（標準ライブラリのみ。Windows は `py` ランチャー付きで入れる）
- Windows: Windows Terminal と PowerShell 7（`pwsh`）
- mac: Terminal.app（初回に「オートメーション」の許可が要る）

## 日々の使い方

操作はすべて、そのマシンの制御用セッション `session-starter <マシン名>` に**日本語で頼む**だけでよい。
頼む場所はどこでもよい（そのマシンの制御用セッションのウィンドウ、別のセッション、別マシンの司令塔、
スマホの Claude アプリ）。別のセッションから頼むときは「`session-starter <マシン名>` に〜を頼んで」と言う。

| やりたいこと | 頼み方の例 |
|---|---|
| 一覧を見る | 「一覧を見せて」 |
| 新しいセッションを追加する | 「`D:\work\foo` で `foo win` というセッションを追加して起動して」 |
| 今使っているセッションを追加する（VS Code などから移す） | そのセッションで「`session-starter <マシン名>` にこのセッションを追加して。今すぐウィンドウに移して」 |
| 止める | 「`foo win` を止めて」 |
| 起動する（会話は前回の続き） | 「`foo win` を起動して」 |
| 再起動する | 「`foo win` を再起動して」 |
| 削除する | 「`foo win` を削除して」（止めてから台帳から外す。会話そのものは残る） |
| PC 起動時の復元対象から外す／戻す | 「`foo win` を自動起動の対象から外して」 |
| 起動先の仮想デスクトップを決める（Windows） | 「`foo win` は `作業` デスクトップで起動するようにして」 |
| claude を更新して全部開き直す | 「全部再起動して」 |

注意:

- **初めて使うフォルダ**でセッションを追加すると、開いたウィンドウに「このフォルダを信頼しますか？」が出る。
  そのマシンの前で承認する必要がある（離れた場所からは承認できない）。
- セッション名はアカウント内で一意にする（他のマシンのセッションとも重ならない名前。例: `foo win` / `foo mac`）。
  今使っているセッションを追加するときは、名前が自動生成のままだと探せないので、先に `/rename` で名前を付ける。
- 「今すぐウィンドウに移して」と頼むと、今の場所（VS Code のパネルなど）のセッションは止まり、
  新しいウィンドウで会話の続きから始まる。
- ウィンドウを閉じるとそのセッションは止まるが、台帳には残る。「起動して」で会話の続きから戻る。
- 作業中のセッションを止める・削除するときは、作業が終わるまで待ってから止める。
- 別のセッションから制御用セッションへ頼むときは、宛先を名前（`session-starter <マシン名>`）で指定する。
  制御用セッションが再起動しても、名前宛てなら届く。

## コマンド（制御用セッションや手動操作向け）

```
css list                       台帳と稼働状態（● 稼働中 / ○ 停止）
css add <name> <cwd> [--start] [--no-autostart] [--desktop <名前|番号>] [--arg=<claude への追加引数>]...
css adopt <name> [--move]      いま動いているセッションを名前で台帳に取り込む（--move ですぐウィンドウへ移す）
css start <name>               起動（会話があれば --resume で引き継ぐ）
css stop <name> [--force]      idle になるまで待って停止（--force は待たない）
css restart <name> [--detach] [--notify <名前>]
                               停止して起動し直す（制御用セッションが自分自身に使うときは --detach。
                               --notify で、起動し直したセッションに <名前> へ完了を知らせさせる）
css remove <name> [--force]    停止して台帳から削除（会話そのものは消えない）
css set <name> [--[no-]autostart] [--arg=...]... [--clear-args] [--desktop <名前|番号>] [--clear-desktop]
                               restore / restart-all の対象にするか切り替え・claude への追加引数・起動先の仮想デスクトップを変更
css desktops                   仮想デスクトップの一覧（Windows）
css restore [--update] [--delay <秒>]
                               autostart で止まっているものを全部起動（--update で先に claude update）
css restart-all [--no-update]  全部 idle まで待って閉じる → claude update → 全部復活
```

- Windows では `.\windows\css.cmd`（PowerShell から）、それ以外では `python3 css.py` で呼ぶ。
- どのコマンドも `--json` で機械可読な出力になる。
- `restart-all` は自分自身（制御用セッション）も止めるので、切り離したプロセスで動き、
  すぐに戻る。経過は `~/.claude-session-starter/logs/restart-*.log` に出る。
- 台帳は `~/.claude-session-starter/sessions.json`（環境変数 `CSS_HOME` で変更可）。
  `CSS_HOME` を使う場合、Windows ではユーザー環境変数として設定する（ログオン時のタスクやショートカットは
  PowerShell のプロファイルを読まない）。mac の LaunchAgent は、登録したときの `CSS_HOME` を引き継ぐ。

## 起動先の仮想デスクトップ（Windows）

セッションごとに、ウィンドウを開く仮想デスクトップを名前（タスクビューで付けた名前）か 1 始まりの番号で指定できる。
指定が無ければ、その時に表示しているデスクトップに開く。

```powershell
.\windows\css.cmd desktops                          # 一覧（名前の無いデスクトップは番号で指定する）
.\windows\css.cmd set "foo win" --desktop 作業       # 次の起動から「作業」デスクトップに開く
.\windows\css.cmd set "foo win" --clear-desktop      # 指定を外す
```

- Windows の非公開の仕組み（仮想デスクトップの内部 COM インターフェース）を使うので、Windows の大型アップデートで
  動かなくなることがある。動かないときも起動自体は成功し、結果に `desktop=failed: …` と理由が出る。
- 開いたウィンドウは一瞬いまのデスクトップに出てから、指定のデスクトップへ移る。
- mac は未対応（指定しても無視される）。

## PC 起動時の復元（オプション）

PC を再起動するとセッションは止まる（会話と台帳は残る）。戻し方は 3 通り。

| 方法 | 向いている PC |
|---|---|
| デスクトップのショートカット「Claude セッション復元」をダブルクリック | 普段使いの PC（戻すタイミングを自分で決めたい） |
| ログイン時に自動で復元（下記） | 常駐用の PC |
| `css restore`（`--update` で先に claude update）を手で実行 | どちらでも |

ショートカットの作成:

```powershell
.\windows\install-shortcut.ps1            # Windows（-Update で先に claude update する版、-Uninstall で削除）
```

```bash
bash mac/install-shortcut.sh              # mac（--update / --uninstall）
```

ログイン時の自動復元:

Windows（タスクスケジューラ）:

```powershell
.\windows\install-tasks.ps1              # ログオン時に復元するタスクを登録
.\windows\install-tasks.ps1 -Update      # 同上。復元の前に claude update する
.\windows\install-tasks.ps1 -Uninstall   # 解除
```

mac（launchd の LaunchAgent）:

```bash
bash mac/install-launchagent.sh              # ログイン時に復元する LaunchAgent を登録（登録時にも一度走る）
bash mac/install-launchagent.sh --update     # 同上。復元の前に claude update する
bash mac/install-launchagent.sh --uninstall  # 解除
```

どちらもログイン後 30 秒待ってから復元する。経過は Windows では `~/.claude-session-starter/logs/css-<日付>.log`、
mac では `~/.claude-session-starter/logs/launchagent.log` に出る。
mac では、登録の約 30 秒後に macOS が「python が Terminal を操作する許可」を求めるので許可する。

一括再起動（`restart-all`）は定期実行しない。必要なときに手動か、司令塔からの依頼で実行する。

## 導入

その PC で動いている Claude Code セッションに、このリポジトリの URL を渡して「導入して」と頼む。
Claude が [SETUP.md](SETUP.md) に従って、clone・制御用セッション `session-starter <マシン名>` の作成・起動まで行う。
人がする操作は、開いたウィンドウでの「このフォルダを信頼しますか？」の承認（ターミナル内の表示）と、
mac では「オートメーション」の許可（OS のダイアログ）だけ。

制御用セッションの役割は [CONTROLLER.md](CONTROLLER.md) に書いてある。

## 第三者のコード

`windows/vdesk.ps1` の COM インターフェース定義は、MScholtes/VirtualDesktop（Copyright (c) 2017 Markus Scholtes、
MIT License）に基づく。著作権表示と許諾表示はファイル冒頭にある。

## 仕組みのメモ

- 稼働状態は `claude agents --json`（pid / sessionId / name / status）で取る。1 回に 6 秒ほどかかる。
- 停止はプロセスの終了（Windows は TerminateProcess）。会話は随時ディスクに書かれているので
  `--resume` で戻る。busy の間は idle になるまで待つ。
- 起動元の環境変数（`CLAUDE*`・`VSCODE_*`・`ELECTRON_*`・`NO_COLOR`・`FORCE_COLOR`）は
  子に渡さない。渡すと子セッション扱いになったり白黒表示になったりする。
