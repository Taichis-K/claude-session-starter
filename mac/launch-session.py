#!/usr/bin/env python3
"""Terminal.app のウィンドウの中で実行され、claude セッションを 1 つ起動する。

起動内容（名前・作業フォルダ・claude に渡す引数）は css.py が書いた JSON ファイルから読む。
空白や日本語を含む値をコマンドラインで渡すと壊れるため。
"""
import json
import os
import shutil
import sys

spec_path = sys.argv[1]
with open(spec_path, encoding="utf-8") as f:
    spec = json.load(f)
os.remove(spec_path)

# 起動元から継承した環境変数を消す
for k in list(os.environ):
    if k.startswith(("CLAUDE", "VSCODE_", "ELECTRON_")) or k in ("NO_COLOR", "FORCE_COLOR"):
        del os.environ[k]

sys.stdout.write(f"\033]0;{spec['name']}\007")
sys.stdout.flush()
os.chdir(spec["cwd"])

claude = shutil.which("claude")
if not claude:
    sys.exit("claude コマンドが見つかりません")
os.execv(claude, [claude, *spec["args"]])
