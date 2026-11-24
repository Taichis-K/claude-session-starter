#!/usr/bin/env python3
"""claude-session-starter (css)

このマシンで常駐させる Claude Code セッションを台帳で管理し、
1 セッション = 1 ターミナルウィンドウで起動・停止・一括再起動する。

  css list                       台帳と稼働状態の一覧
  css add <name> <cwd> [--start] 新しいセッションを台帳に登録
  css adopt <name> [--move]      いま動いているセッションを台帳に取り込む（--move ですぐウィンドウへ移す）
  css start <name>               起動（会話があれば --resume で引き継ぐ）
  css stop <name> [--force]      idle になるのを待って停止
  css restart <name> [--detach] [--notify <名前>]
                                 停止して起動し直す（自分自身なら --detach。--notify で完了を知らせさせる）
  css remove <name> [--force]    停止して台帳から削除（会話自体は消さない）
  css set <name> [--[no-]autostart] [--arg=...]... [--clear-args]
                                 復元対象の切り替え・claude への追加引数の変更
  css restore [--update] [--delay <秒>]
                                 autostart のうち止まっているものを全部起動
  css restart-all [--no-update]  全部閉じる → claude update → 全部復活

すべてのコマンドは --json で機械可読な出力になる（制御用 Claude 向け）。
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
import uuid
from pathlib import Path

HOME = Path.home()
DATA_DIR = Path(os.environ.get("CSS_HOME", HOME / ".claude-session-starter"))
REGISTRY = DATA_DIR / "sessions.json"
LOG_DIR = DATA_DIR / "logs"
APP_DIR = Path(__file__).resolve().parent
IS_WIN = sys.platform == "win32"
IS_MAC = sys.platform == "darwin"

# 起動元（VS Code 拡張や別の claude）から子に漏らしてはいけない環境変数
SCRUB_PREFIXES = ("CLAUDE", "VSCODE_", "ELECTRON_")
SCRUB_NAMES = {"NO_COLOR", "FORCE_COLOR"}


class CssError(Exception):
    pass


# ---------------------------------------------------------------- 台帳

def load_registry() -> list[dict]:
    if not REGISTRY.exists():
        return []
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def save_registry(entries: list[dict]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = REGISTRY.with_suffix(".tmp")
    tmp.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(REGISTRY)


def find_entry(entries: list[dict], name: str) -> dict:
    for e in entries:
        if e["name"] == name:
            return e
    raise CssError(f"台帳に '{name}' がありません")


# ---------------------------------------------------------------- claude

def claude_bin() -> str:
    path = shutil.which("claude")
    if not path:
        raise CssError("claude コマンドが見つかりません")
    return path


def clean_env() -> dict:
    return {k: v for k, v in os.environ.items()
            if not k.startswith(SCRUB_PREFIXES) and k not in SCRUB_NAMES}


def live_sessions() -> dict[str, dict]:
    """claude agents --json の結果を sessionId をキーにして返す。"""
    out = subprocess.run([claude_bin(), "agents", "--json"], capture_output=True, stdin=subprocess.DEVNULL,
                         text=True, encoding="utf-8", env=clean_env(), timeout=60)
    if out.returncode != 0:
        raise CssError(f"claude agents に失敗: {out.stderr.strip()}")
    # 終了直後のセッションがしばらく一覧に残るので、プロセスが消えたものは除く
    return {s["sessionId"]: s for s in json.loads(out.stdout or "[]")
            if s.get("pid") and pid_alive(s["pid"])}


def has_transcript(session_id: str) -> bool:
    projects = HOME / ".claude" / "projects"
    return any(projects.glob(f"*/{session_id}.jsonl"))


# ---------------------------------------------------------------- ウィンドウ

def mac_window_file(session_id: str) -> Path:
    d = DATA_DIR / "windows"
    d.mkdir(parents=True, exist_ok=True)
    return d / session_id


def close_mac_window(session_id: str) -> None:
    """mac: stop したセッションの Terminal ウィンドウを閉じる（プロセス終了済みなら確認なしで閉じる）。"""
    f = mac_window_file(session_id)
    if not IS_MAC or not f.exists():
        return
    wid = f.read_text(encoding="utf-8").strip()
    f.unlink()
    if wid.isdigit():
        subprocess.run(["osascript", "-e",
                        f'tell application "Terminal" to close (every window whose id is {wid})'],
                       capture_output=True, stdin=subprocess.DEVNULL, env=clean_env())


def open_window(entry: dict, prompt: str | None = None) -> None:
    """prompt を渡すと、起動直後にそれを最初の入力として送る（再起動完了の通知などに使う）。"""
    # 名前・追加引数・プロンプトには空白や日本語が入るので、コマンドラインでは渡さない。
    # 起動内容を JSON ファイルに書き、ランチャーにはそのパスだけを渡す（読んだら消す）。
    # 引数は claude にそのまま渡す配列として組み立てる。
    resume = has_transcript(entry["sessionId"])
    claude_args = ["--name", entry["name"], "--remote-control", entry["name"]]
    claude_args += ["--resume" if resume else "--session-id", entry["sessionId"]]
    claude_args += list(entry.get("args", []))
    if prompt:
        claude_args.append(prompt)  # claude の位置引数 = 最初のプロンプト
    spec_dir = DATA_DIR / "launch"
    spec_dir.mkdir(parents=True, exist_ok=True)
    spec = spec_dir / f"{entry['sessionId']}.json"
    spec.write_text(json.dumps({"name": entry["name"], "cwd": entry["cwd"], "args": claude_args},
                               ensure_ascii=False), encoding="utf-8")
    if IS_WIN:
        script = APP_DIR / "windows" / "launch-session.ps1"
        cmd = ["wt.exe", "-w", "new", "--title", entry["name"], "-d", entry["cwd"],
               "pwsh", "-NoLogo", "-NoProfile", "-File", str(script), "-Spec", str(spec)]
        # wt はセミコロンをコマンド区切りとして扱うのでエスケープする
        cmd = [c.replace(";", "\\;") for c in cmd]
        subprocess.Popen(cmd, env=clean_env())
    elif IS_MAC:
        # ランチャーは css.py を動かしている Python で起動する（/usr/bin/python3 は古いかスタブのことがある）。
        # osascript の戻り値（"tab 1 of window id N"）はウィンドウ ID として控え、stop 時にそのウィンドウを閉じる
        # （Terminal は既定でプロセス終了後もウィンドウを残すため）。標準出力には流さない（--json に混ざる）。
        script = APP_DIR / "mac" / "launch-session.py"
        out = subprocess.run(["osascript", str(APP_DIR / "mac" / "open-window.applescript"),
                              sys.executable, str(script), str(spec)], check=True, env=clean_env(),
                             capture_output=True, text=True, stdin=subprocess.DEVNULL)
        m = re.search(r"window id (\d+)", out.stdout)
        if m:
            mac_window_file(entry["sessionId"]).write_text(m.group(1), encoding="utf-8")
    else:
        raise CssError(f"未対応の OS です: {sys.platform}")


def pid_alive(pid: int) -> bool:
    if IS_WIN:
        import ctypes
        k32 = ctypes.windll.kernel32
        h = k32.OpenProcess(0x00100000, False, pid)  # SYNCHRONIZE
        if not h:
            return False
        try:
            return k32.WaitForSingleObject(h, 0) == 0x102  # WAIT_TIMEOUT = まだ動いている
        finally:
            k32.CloseHandle(h)
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def kill_pid(pid: int) -> None:
    try:
        os.kill(pid, signal.SIGTERM)  # Windows では TerminateProcess になる
    except ProcessLookupError:
        pass
    except OSError as ex:  # Windows で既に終了している場合など
        if IS_WIN and getattr(ex, "winerror", None) in (5, 87):
            return
        raise


# ---------------------------------------------------------------- 操作

def wait_until(pred, timeout: float, interval: float = 2.0) -> bool:
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if pred():
            return True
        time.sleep(interval)
    return pred()


def start(entry: dict, timeout: float = 60, prompt: str | None = None) -> dict:
    live = live_sessions()
    if entry["sessionId"] in live:
        return {"name": entry["name"], "result": "already-running"}
    open_window(entry, prompt)
    ok = wait_until(lambda: entry["sessionId"] in live_sessions(), timeout)
    if ok:
        return {"name": entry["name"], "result": "started"}
    return {"name": entry["name"], "result": "start-timeout",
            "hint": "初めて使うフォルダだと、ウィンドウが「このフォルダを信頼しますか？」で止まっている。"
                    "人に承認してもらってから `list` で running になったか確認する。"}


def stop(entry: dict, force: bool = False, idle_timeout: float = 1800) -> dict:
    # claude agents は 1 回 6 秒ほどかかるので、呼ぶ回数を最小にする
    sid = entry["sessionId"]
    s = live_sessions().get(sid)
    deadline = time.monotonic() + idle_timeout
    while s and not force and s.get("status") == "busy":
        if time.monotonic() > deadline:
            return {"name": entry["name"], "result": "busy-timeout"}
        time.sleep(5)
        s = live_sessions().get(sid)
    if not s:
        return {"name": entry["name"], "result": "not-running"}
    kill_pid(s["pid"])
    # claude agents の一覧は終了後もしばらく残るので、プロセスの消滅で判定する
    ok = wait_until(lambda: not pid_alive(s["pid"]), 30, interval=0.5)
    if ok:
        close_mac_window(sid)
    return {"name": entry["name"], "result": "stopped" if ok else "stop-timeout"}


def status_rows() -> list[dict]:
    live = live_sessions()
    rows = []
    for e in load_registry():
        s = live.get(e["sessionId"])
        rows.append({**e, "running": bool(s), "status": s["status"] if s else "stopped",
                     "pid": s["pid"] if s else None})
    return rows


def restart_all(update: bool, log) -> list[dict]:
    entries = load_registry()
    live = live_sessions()
    # 止まっていたもの（autostart 対象）も含めて、最後に全部起動し直す
    targets = [e for e in entries if e["sessionId"] in live or e.get("autostart", True)]
    log(f"対象: {[e['name'] for e in targets]}")
    for e in targets:
        r = stop(e)
        log(f"stop {e['name']}: {r['result']}")
    if update:
        out = subprocess.run([claude_bin(), "update"], capture_output=True, stdin=subprocess.DEVNULL, text=True,
                             encoding="utf-8", errors="replace", env=clean_env(), timeout=600)
        log(f"claude update (exit {out.returncode}):\n{out.stdout}{out.stderr}")
    results = []
    for e in targets:
        r = start(e)
        log(f"start {e['name']}: {r['result']}")
        results.append(r)
    return results


def spawn_detached(argv: list[str], log_path: Path, stdout_to_log: bool = False) -> None:
    """自分（制御用 claude）が停止対象に含まれても最後まで走るよう、切り離して実行する。"""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logf = open(log_path, "a", encoding="utf-8")
    kw: dict = {"stdout": logf if stdout_to_log else subprocess.DEVNULL, "stderr": logf,
                "stdin": subprocess.DEVNULL, "env": clean_env()}
    if IS_WIN:
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        try:
            subprocess.Popen(argv, creationflags=flags | subprocess.CREATE_BREAKAWAY_FROM_JOB, **kw)
            return
        except OSError:
            pass  # ジョブからの離脱が許されない環境
        subprocess.Popen(argv, creationflags=flags, **kw)
    else:
        subprocess.Popen(argv, start_new_session=True, **kw)


# ---------------------------------------------------------------- CLI

def main(argv: list[str] | None = None) -> int:
    # pythonw（タスクスケジューラから起動）では出力先が無く、エラーも消えてしまうのでログへ書く
    if sys.stdout is None or sys.stderr is None:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        f = open(LOG_DIR / f"css-{dt.datetime.now():%Y%m%d}.log", "a", encoding="utf-8")
        f.write(f"\n[{dt.datetime.now():%Y-%m-%d %H:%M:%S}] css {' '.join(sys.argv[1:])}\n")
        sys.stdout = sys.stdout or f
        sys.stderr = sys.stderr or f
    p = argparse.ArgumentParser(prog="css", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--json", action="store_true", help="JSON で出力する")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    a = sub.add_parser("add")
    a.add_argument("name")
    a.add_argument("cwd")
    a.add_argument("--start", action="store_true")
    a.add_argument("--no-autostart", action="store_true")
    a.add_argument("--arg", action="append", default=[], dest="args",
                   help="claude に渡す追加引数（例: --arg=--model --arg=opus）")
    ad = sub.add_parser("adopt")
    ad.add_argument("name")
    ad.add_argument("--move", action="store_true",
                    help="今の場所で止めて、すぐ独立したウィンドウで起動し直す")
    sub.add_parser("start").add_argument("name")
    rs = sub.add_parser("restart")
    rs.add_argument("name")
    rs.add_argument("--force", action="store_true", help="busy でも待たずに止める")
    rs.add_argument("--detach", action="store_true",
                    help="切り離して実行（制御用セッションが自分自身を再起動するとき）")
    rs.add_argument("--notify", metavar="NAME",
                    help="再起動後のセッションに、NAME へ完了を SendMessage させる")
    s = sub.add_parser("stop")
    s.add_argument("name")
    s.add_argument("--force", action="store_true", help="busy でも待たずに止める")
    rm = sub.add_parser("remove")
    rm.add_argument("name")
    rm.add_argument("--force", action="store_true", help="busy でも待たずに止めて削除する")
    st = sub.add_parser("set")
    st.add_argument("name")
    g = st.add_mutually_exclusive_group()
    g.add_argument("--autostart", dest="autostart", action="store_true", default=None)
    g.add_argument("--no-autostart", dest="autostart", action="store_false")
    st.add_argument("--arg", action="append", default=[], dest="args",
                    help="claude に渡す追加引数を置き換える（例: --arg=--model --arg=haiku）")
    st.add_argument("--clear-args", action="store_true", help="追加引数を空にする")
    rst = sub.add_parser("restore")
    rst.add_argument("--update", action="store_true", help="起動する前に claude update する")
    rst.add_argument("--delay", type=int, default=0, metavar="SEC",
                     help="始める前に待つ秒数（ログイン直後はネットワーク等が未準備のことがあるため）")
    r = sub.add_parser("restart-all")
    r.add_argument("--no-update", action="store_true")
    r.add_argument("--foreground", action="store_true", help="切り離さずにこのプロセスで実行")
    r.add_argument("--log", help="ログファイルのパス（省略時は logs/restart-<日時>.log）")
    # --json はサブコマンドの前後どちらに書いてもよい
    argv = list(sys.argv[1:] if argv is None else argv)
    as_json = "--json" in argv
    args = p.parse_args([a for a in argv if a != "--json"])
    args.json = as_json

    def emit(obj, text: str) -> None:
        print(json.dumps(obj, ensure_ascii=False, indent=2) if args.json else text)

    try:
        if args.cmd == "list":
            rows = status_rows()
            emit(rows, "\n".join(
                f"{'●' if r['running'] else '○'} {r['name']:<28} {r['status']:<8} {r['cwd']}"
                for r in rows) or "(台帳は空です)")
        elif args.cmd == "add":
            entries = load_registry()
            if any(e["name"] == args.name for e in entries):
                raise CssError(f"'{args.name}' は登録済みです")
            cwd = str(Path(args.cwd).expanduser().resolve())
            if not Path(cwd).is_dir():
                raise CssError(f"ディレクトリがありません: {cwd}")
            entry = {"name": args.name, "cwd": cwd, "sessionId": str(uuid.uuid4()),
                     "autostart": not args.no_autostart, "args": args.args}
            entries.append(entry)
            save_registry(entries)
            res = {"added": entry}
            if args.start:
                res["start"] = start(entry)
            emit(res, f"登録しました: {args.name}" + (f"（{res['start']['result']}）" if args.start else ""))
        elif args.cmd == "adopt":
            entries = load_registry()
            if any(e["name"] == args.name for e in entries):
                raise CssError(f"'{args.name}' は登録済みです")
            match = [s for s in live_sessions().values() if s.get("name") == args.name]
            if len(match) != 1:
                raise CssError(f"稼働中で名前が '{args.name}' のセッションが {len(match)} 件です")
            m = match[0]
            entry = {"name": args.name, "cwd": m["cwd"], "sessionId": m["sessionId"],
                     "autostart": True, "args": []}
            entries.append(entry)
            save_registry(entries)
            res = {"adopted": entry}
            if args.move:
                # 今の場所（VS Code など）で止めて、独立したウィンドウで会話の続きから起動する
                res["stop"] = stop(entry)["result"]
                if res["stop"] in ("stopped", "not-running"):
                    res["start"] = start(entry)["result"]
                emit(res, f"取り込みました: {args.name}（stop: {res['stop']}, start: {res.get('start', '-')}）")
            else:
                emit(res, f"取り込みました: {args.name}（次回の再起動からウィンドウで動きます）")
        elif args.cmd == "restart":
            entry = find_entry(load_registry(), args.name)
            if args.detach:
                # 自分自身（制御用セッション）を再起動するときは、止められても最後まで走るよう切り離す
                log_path = LOG_DIR / f"restart-{dt.datetime.now():%Y%m%d-%H%M%S}.log"
                child = [sys.executable, str(Path(__file__).resolve()), "--json", "restart", args.name]
                if args.notify:
                    child += ["--notify", args.notify]
                spawn_detached(child, log_path, stdout_to_log=True)
                emit({"result": "spawned", "log": str(log_path)},
                     f"{args.name} の再起動をバックグラウンドで開始しました。ログ: {log_path}")
            else:
                r = {"name": args.name, "stop": stop(entry, force=args.force)["result"]}
                if r["stop"] in ("stopped", "not-running"):
                    prompt = None
                    if args.notify:
                        prompt = (f"[claude-session-starter] 再起動が完了しました。"
                                  f"{args.notify} に SendMessage（宛先は名前）で、再起動が終わって"
                                  f"稼働中であることを知らせてください。確かめた事実だけを書き、"
                                  f"相手に届いたかどうかなど自分にわからないことは書かないでください。")
                    r["start"] = start(entry, prompt=prompt)["result"]
                emit(r, f"{args.name}: stop={r['stop']} start={r.get('start', '-')}")
        elif args.cmd == "start":
            r = start(find_entry(load_registry(), args.name))
            emit(r, f"{r['name']}: {r['result']}" + (f"\n{r['hint']}" if r.get("hint") else ""))
        elif args.cmd == "stop":
            r = stop(find_entry(load_registry(), args.name), force=args.force)
            emit(r, f"{r['name']}: {r['result']}")
        elif args.cmd == "remove":
            # 動いていれば先に止める（作業中なら終わるまで待つ）。止められなければ削除しない
            r = stop(find_entry(load_registry(), args.name), force=args.force)
            if r["result"] not in ("stopped", "not-running"):
                raise CssError(f"'{args.name}' を停止できなかったので削除していません（{r['result']}）")
            entries = load_registry()
            save_registry([e for e in entries if e["name"] != args.name])
            emit({"removed": args.name, "stop": r["result"]},
                 f"停止して台帳から削除しました: {args.name}（会話は残っています）")
        elif args.cmd == "set":
            entries = load_registry()
            e = find_entry(entries, args.name)
            if args.autostart is not None:
                e["autostart"] = args.autostart
            if args.clear_args:
                e["args"] = []
            if args.args:
                e["args"] = args.args
            save_registry(entries)
            emit(e, f"{args.name}: autostart={'on' if e.get('autostart', True) else 'off'} "
                    f"args={e.get('args', [])}（args の変更は次の起動から有効）")
        elif args.cmd == "restore":
            if args.delay > 0:
                time.sleep(args.delay)
            if args.update:
                subprocess.run([claude_bin(), "update"], stdin=subprocess.DEVNULL, env=clean_env(), timeout=600,
                               stdout=subprocess.DEVNULL if args.json or not sys.stdout else None)
            live = live_sessions()
            res = [start(e) for e in load_registry()
                   if e.get("autostart", True) and e["sessionId"] not in live]
            # ログイン時にログファイルへ追記されていくので、行頭に時刻を付ける
            ts = f"[{dt.datetime.now():%Y-%m-%d %H:%M:%S}] restore: "
            emit(res, "\n".join(ts + f"{r['name']}: {r['result']}" for r in res)
                 or ts + "起動が必要なセッションはありません")
        elif args.cmd == "restart-all":
            log_path = Path(args.log) if args.log else \
                LOG_DIR / f"restart-{dt.datetime.now():%Y%m%d-%H%M%S}.log"
            if args.foreground:
                LOG_DIR.mkdir(parents=True, exist_ok=True)

                def log(msg: str) -> None:
                    line = f"[{dt.datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(line + "\n")
                    if sys.stdout:  # pythonw では None
                        print(line, flush=True)
                restart_all(not args.no_update, log)
            else:
                child = [sys.executable, str(Path(__file__).resolve()), "restart-all",
                         "--foreground", "--log", str(log_path)]
                if args.no_update:
                    child.append("--no-update")
                spawn_detached(child, log_path.with_suffix(".stderr.log"))
                emit({"result": "spawned", "log": str(log_path)},
                     f"再起動をバックグラウンドで開始しました。ログ: {log_path}")
        return 0
    except CssError as ex:
        emit({"error": str(ex)}, f"エラー: {ex}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
