# Changelog

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
