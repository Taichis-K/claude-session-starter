# Changelog

## v0.2.1 (2026-11-26)

- セッションの中で `/clear` すると sessionId が変わり、css が「停止」と誤表示していた（再起動すると `/clear` 前の会話が
  もう 1 つ起動してしまう）のを修正。台帳の sessionId が動いていないとき、同じ名前・同じフォルダで動いている
  セッションが 1 つだけあれば、台帳を新しい sessionId に書き換えて追従する

## v0.2.0 (2026-11-24)

- Windows: セッションごとに起動先の仮想デスクトップを名前か番号で指定できるように（`add --desktop` / `set --desktop` / `set --clear-desktop`、
  一覧は `desktops`）。Windows の非公開の仕組みを使うため、動かないときは今のデスクトップに開いて結果に理由を出す

## v0.1.0 (2026-11-24)

初版。

- 台帳によるセッション管理: `list` / `add` / `adopt` / `start` / `stop` / `restart` / `set` / `remove` / `restore` / `restart-all`
- 1 セッション = 1 ウィンドウで起動（Windows: Windows Terminal、mac: Terminal.app）。
  `--remote-control <名前>` 付きで起動し、停止・再起動しても `--resume` で会話を引き継ぐ
- `restart-all`: 全セッションを idle まで待って閉じ、`claude update` のあと全部復活（制御用セッション自身も対象）
- `adopt --move`: 今使っているセッション（VS Code など）を台帳に取り込み、すぐ独立ウィンドウへ移す
- `restart --detach --notify`: 制御用セッションが自分を再起動し、完了を依頼元へ知らせる
- 制御用セッション（`session-starter <マシン名>`）の役割 `CONTROLLER.md` と、`css` の実行だけを許可する `.claude/settings.json`
- Claude 向け導入手順 `SETUP.md`（「このリポジトリを導入して」で導入できる）
- PC 再起動後の復元（オプション）: デスクトップの「Claude セッション復元」ショートカット、
  またはログイン時の自動復元（Windows はタスクスケジューラ、mac は LaunchAgent）
