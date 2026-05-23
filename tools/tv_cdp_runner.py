#!/usr/bin/env python3
"""Minimal CDP client for TradingView Desktop launched with --remote-debugging-port=9222.

Requires TV launched with BOTH:
    --remote-debugging-port=9222
    --remote-allow-origins=*

Usage:
    python tools/tv_cdp_runner.py --eval "1+1"
    python tools/tv_cdp_runner.py --eval-file expr.js
    python tools/tv_cdp_runner.py --list-pages
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request

import websocket  # pip install websocket-client

if sys.platform == "win32":
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            try:
                s.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def list_pages(host="localhost", port=9222):
    with urllib.request.urlopen(f"http://{host}:{port}/json") as r:
        return json.loads(r.read().decode("utf-8"))


def find_chart_page(pages):
    for p in pages:
        if p.get("type") == "page" and "tradingview.com/chart" in (p.get("url") or ""):
            return p
    for p in pages:
        if p.get("type") == "page" and "tradingview.com" in (p.get("url") or ""):
            return p
    return pages[0] if pages else None


def evaluate(expression: str, host="localhost", port=9222, await_promise=True, returnByValue=True, timeout=30):
    pages = list_pages(host, port)
    page = find_chart_page(pages)
    if not page:
        raise SystemExit("no chart page found in CDP")
    ws_url = page["webSocketDebuggerUrl"]
    # Chrome >= 111 rejects WS connections from non-allowed Origins. Suppress
    # the Origin header (works when TV launched with --remote-allow-origins=*).
    try:
        ws = websocket.create_connection(ws_url, timeout=timeout, suppress_origin=True)
    except Exception:
        try:
            ws = websocket.create_connection(ws_url, timeout=timeout, origin="chrome-extension://abc")
        except Exception:
            raise SystemExit(
                "CDP WS rejected by TradingView. Relaunch TV with:\n"
                "  & 'C:/Program Files/WindowsApps/TradingView.Desktop_<ver>/TradingView.exe' "
                "--remote-debugging-port=9222 --remote-allow-origins=*"
            )
    try:
        msg_id = 1
        ws.send(json.dumps({
            "id": msg_id,
            "method": "Runtime.evaluate",
            "params": {
                "expression": expression,
                "returnByValue": returnByValue,
                "awaitPromise": await_promise,
                "timeout": timeout * 1000,
            },
        }))
        while True:
            raw = ws.recv()
            data = json.loads(raw)
            if data.get("id") == msg_id:
                return data
    finally:
        ws.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--eval", help="JS expression to run")
    ap.add_argument("--eval-file", help="Path to JS file to run")
    ap.add_argument("--list-pages", action="store_true")
    ap.add_argument("--host", default="localhost")
    ap.add_argument("--port", type=int, default=9222)
    ap.add_argument("--raw", action="store_true", help="dump full CDP response")
    args = ap.parse_args()

    if args.list_pages:
        for p in list_pages(args.host, args.port):
            print(f"[{p.get('type')}] {p.get('title','?')[:50]} | {p.get('url','')[:90]}")
        return

    expr = args.eval
    if args.eval_file:
        from pathlib import Path
        expr = Path(args.eval_file).read_text(encoding="utf-8")
    if not expr:
        ap.print_help()
        sys.exit(2)

    res = evaluate(expr, args.host, args.port)
    if args.raw:
        print(json.dumps(res, indent=2, default=str))
        return
    r = res.get("result", {})
    if "exceptionDetails" in res or "exceptionDetails" in r:
        print("CDP_EXCEPTION:", json.dumps(res.get("exceptionDetails") or r.get("exceptionDetails"), default=str, indent=2)[:2000])
        sys.exit(1)
    inner = r.get("result", r)
    val = inner.get("value")
    if val is None:
        val = inner.get("description") or inner
    if isinstance(val, (dict, list)):
        print(json.dumps(val, indent=2, default=str))
    else:
        print(val)


if __name__ == "__main__":
    main()
