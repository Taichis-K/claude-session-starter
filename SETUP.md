# 導入手順（Claude 向け）

この手順書は、ユーザーから「このリポジトリを導入して」と頼まれた Claude Code セッションが読んで実行するもの。
各ステップの「人に聞く」は AskUserQuestion などで必ず確認し、勝手に決めない。
コマンドは PowerShell（Windows）/ bash・zsh（mac）から実行する前提で書いている。

## 1. 前提の確認

- `claude --version` が動くこと。
- claude.ai アカウントでログインしていること（各セッションを `--remote-control` 付きで起動するため）。
- Python 3.10 以上があること（Windows: `py -3 --version`、mac: `python3 --version`）。
  Windows は `py` ランチャーで呼ぶので、`py` が使えること。
  mac の `/usr/bin/python3` は古い（3.9）ことがあるが、css は `python3` で呼んだ Python をランチャーにも使うので問題ない。
- Windows なら `wt.exe`（Windows Terminal）と `pwsh`（PowerShell 7）があること。
- mac では、初回に `osascript` が Terminal を操作する許可（「オートメーション」）を求めるダイアログが出る。人に承認を頼む。
- 足りないものがあれば、入れ方を人に伝えて止まる。

## 2. インストール先を決める（人に聞く）

- 既定の候補は `~/claude-session-starter`（Windows なら `$env:USERPROFILE\claude-session-starter`）。
- このフォルダがそのまま制御用セッションのワークスペースになる。
- 決まったら、そこへ**最新の Release タグ**を clone する（main ではなくタグを使う）。
  ```
  gh release view --repo Taichis-K/claude-session-starter --json tagName -q .tagName
  git clone --branch <タグ> https://github.com/Taichis-K/claude-session-starter.git <インストール先>
  ```
  `gh` が無ければ https://github.com/Taichis-K/claude-session-starter/releases/latest を開いてタグ名を確かめる。
  タグを clone すると detached HEAD になるが、それで正常。

## 3. マシン名を決める（人に聞く）

- 制御用セッションの名前は `session-starter <マシン名>` になる。
- この名前はアカウント内の全セッション一覧に出るので、ホスト名そのままより**短い呼び名**を勧める
  （例: `win1`、`mac1`、`office-win`）。
- アカウント内で一意である必要がある。ListAgents で同じ名前が無いことを確かめる。

## 4. 制御用 CLAUDE.md を作る

インストール先に `CLAUDE.md` を次の内容で作る（`.gitignore` 済みなので git には入らない）。

```
@CONTROLLER.md

このマシンの名前: <マシン名>
```

## 5. 制御用セッションのモデル（人に聞く）

- 既定の候補は `haiku`。仕事は css の実行と返信だけなので軽いモデルで足りる（待機中はトークンを使わない）。
- 判断の正確さを優先したい人には `sonnet` も選べると伝える。指定しない（アカウントの既定モデル）も可。
- 決まったモデルを、次の手順 6 の `add` に `--arg=--model --arg=<モデル>` として付ける。
  後から変えるときは `css set "session-starter <マシン名>" --arg=--model --arg=<モデル>` のあと再起動する。

## 6. 制御用セッションを起動する

初めて使うフォルダなので、開いたウィンドウに「このフォルダを信頼しますか？」が出る。
これは OS のダイアログではなく、**ターミナルの画面の中**に表示される claude の確認である
（mac で最初に出る「オートメーション」の許可は OS のダイアログなので別物。人に聞くときは区別して聞く）。
**実行する前に**人へ次を伝える。

- これから `session-starter <マシン名>` のウィンドウが開くので、信頼を承認してほしい。
- 承認画面に、このキットの `.claude/settings.json` が許可する操作の一覧が出る。中身は `css` の実行だけで、
  制御用セッションが確認なしで起動・停止・自分自身の再起動をするために必要なもの。

インストール先で次を実行する。台帳（`~/.claude-session-starter/sessions.json`）がすでにある場合は、そこに追記される（既存の登録はそのまま）。

- Windows: `.\windows\css.cmd add "session-starter <マシン名>" . --start --arg=--model --arg=haiku`
- mac: `python3 css.py add "session-starter <マシン名>" . --start --arg=--model --arg=haiku`

（モデルを指定しない場合は `--arg=...` を付けない。）

結果で分岐する。

- `started`: 60 秒以内に承認された。そのまま 7 へ。
- `start-timeout`: まだ承認されていない。人に承認を促し、承認されたら `list` で running になったことを確かめる。

## 7. 動作確認

`SendMessage` で `session-starter <マシン名>` に「list を実行して結果を返して」と送り、返事が来ることを確かめる。

## 8. PC 再起動後の復元（人に聞く）

PC を再起動するとセッションは止まる（会話と台帳は残る）。どう戻すかを、次の 3 つから選んでもらう（複数可）。

- **デスクトップのショートカット**（普段使いの PC 向け）: ダブルクリックで止まっているセッションを起動する。
  - Windows: `.\windows\install-shortcut.ps1`、mac: `bash mac/install-shortcut.sh`
  - 先に claude update する版は `-Update` / `--update`
- **ログイン時に自動で復元**（常駐用の PC 向け）: 起動前に `claude update` もするかを聞く。
  - Windows: `.\windows\install-tasks.ps1`（更新もするなら `-Update`）
  - mac: `bash mac/install-launchagent.sh`（更新もするなら `--update`）。登録した瞬間に一度 restore が走る
    （止まっている autostart セッションが起動される）ので、そのことを人に伝えてから実行する。
    約 30 秒後、macOS が「python が Terminal を操作する許可」（オートメーション）のダイアログを出すことがある。
    launchd から起動すると許可を求める主体が Terminal ではなく python になるため。**人に許可してもらう**
    （許可しないと、ログイン時の復元でウィンドウを開けない）。
- **何もしない**（手で `css restore` する）

補足: 台帳の `autostart` は「`restore` / `restart-all` で起動する対象か」の印にすぎない。
どれを選んでも、制御用セッションは `autostart` のままでよい。

## 9. 終わりに伝えること

- 制御用セッションの名前（他マシンの司令塔からはこの名前で依頼する）
- セッションを追加するときは、制御用セッションに「<名前> を <フォルダ> で追加して起動して」と頼めばよいこと。
  今使っているセッションを移すときは、そのセッションで「`session-starter <マシン名>` にこのセッションを追加して」と頼む
- 初めて使うフォルダでセッションを起動すると、そのウィンドウで信頼の承認が必要なこと
- PC を再起動したあとの戻し方（手順 8 で選んだもの）

## 更新するとき

「claude-session-starter を更新して」と頼まれたら、インストール先で次を実行する。

```
git fetch --tags
git tag --sort=-v:refname   # 先頭が最新
git checkout <最新タグ>
```

ファイルを入れ替えるだけで、制御用セッションの再起動は不要（`css` は呼ぶたびに読み直される。
ただし `CONTROLLER.md` が変わった場合は、制御用セッションを再起動すると新しい指示が読み込まれる）。
`.claude/settings.json` が変わる場合は、権限が変わるので人に承認を求めてから checkout する。
`CLAUDE.md` と台帳（`~/.claude-session-starter/`）はそのまま残る。
