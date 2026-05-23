#!/usr/bin/env python3
"""
TV Paper TP/SL Audit — standalone watchdog for missing/inverted TP/SL on TV
paper positions.

Problem (cycle 7, 2026-04-05): live MCP agents invoking the tv-paper-trade
skill are ignoring the Step 4 BLOCKER_FAIL gate and opening positions with
NO TP/SL on all 5 paper accounts. Same symbols cycle: JTO, SUI, OP, KITE,
BTC, ADA, LINK.

This script:
  1. Reads a snapshot of current positions from
     alpha_engine/data/tv_paper_positions_snapshot.json (produced by the
     agent that owns the TV desktop session via ui_evaluate).
  2. Flags positions with missing/empty TP, missing/empty SL, or TP/SL on the
     wrong side of entry for the position side.
  3. Logs violators to alpha_engine/data/tv_paper_tpsl_violators.jsonl.
  4. Optionally broadcasts violators on the Redis agent bus so whoever is on
     the integrity lane can auto-fix.

The snapshot file schema (one position per entry):
  [{"account": "zerounderscore", "symbol": "BINANCE:SUIUSDT", "side": "LONG",
    "qty": 2315, "entry": 0.8653, "tp": 0.9515, "sl": 0.82175,
    "opened_at": "2026-04-05T03:30:00Z"}, ...]

TP/SL may be None, null, "", 0, or a numeric string — all treated as missing.

Usage:
  python tools/tv_paper_tpsl_audit.py                # audit, log to jsonl
  python tools/tv_paper_tpsl_audit.py --broadcast    # also push to Redis bus
  python tools/tv_paper_tpsl_audit.py --snapshot PATH
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

REPO = Path(__file__).resolve().parents[1]
DEFAULT_SNAPSHOT = REPO / "alpha_engine" / "data" / "tv_paper_positions_snapshot.json"
VIOLATORS_LOG = REPO / "alpha_engine" / "data" / "tv_paper_tpsl_violators.jsonl"

WATCHED_SYMBOLS = {
    "JTOUSDT", "SUIUSDT", "OPUSDT", "KITEUSDT",
    "BTCUSDT", "ADAUSDT", "LINKUSDT",
}


def _as_float(v: Any) -> float | None:
    if v is None:
        return None
    if isinstance(v, bool):
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if f == 0.0:
        return None
    return f


def _normalize_symbol(sym: str) -> str:
    # Strip exchange prefix "BINANCE:BTCUSDT" -> "BTCUSDT"
    if ":" in sym:
        sym = sym.split(":", 1)[1]
    return sym.upper()


def audit_positions(positions: Iterable[dict]) -> list[dict]:
    """Return a list of violation records. Empty list means all clean."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out: list[dict] = []
    for p in positions:
        sym = _normalize_symbol(str(p.get("symbol", "")))
        side = str(p.get("side", "")).upper().strip()
        entry = _as_float(p.get("entry"))
        tp = _as_float(p.get("tp"))
        sl = _as_float(p.get("sl"))
        account = p.get("account", "UNKNOWN")
        reasons: list[str] = []

        if tp is None:
            reasons.append("missing_tp")
        if sl is None:
            reasons.append("missing_sl")
        if entry is not None and tp is not None and sl is not None:
            if side in ("LONG", "BUY", "L"):
                if not (tp > entry > sl):
                    reasons.append(
                        f"inverted_long tp={tp} entry={entry} sl={sl}"
                    )
            elif side in ("SHORT", "SELL", "S"):
                if not (sl > entry > tp):
                    reasons.append(
                        f"inverted_short sl={sl} entry={entry} tp={tp}"
                    )
            else:
                reasons.append(f"unknown_side:{side!r}")

        if reasons:
            out.append({
                "timestamp": now,
                "account": account,
                "symbol": sym,
                "side": side,
                "entry": entry,
                "tp": tp,
                "sl": sl,
                "reasons": reasons,
                "watched": sym in WATCHED_SYMBOLS,
            })
    return out


def append_violators(violations: list[dict]) -> None:
    VIOLATORS_LOG.parent.mkdir(parents=True, exist_ok=True)
    with VIOLATORS_LOG.open("a", encoding="utf-8") as fh:
        for v in violations:
            fh.write(json.dumps(v, ensure_ascii=False) + "\n")


def broadcast(violations: list[dict]) -> bool:
    try:
        import redis
    except ImportError:
        print("redis-py not installed; skipping broadcast", file=sys.stderr)
        return False
    try:
        r = redis.Redis(host="localhost", port=6379, decode_responses=False)
        r.ping()
    except Exception as exc:  # noqa: BLE001
        print(f"Redis unavailable, skipping broadcast: {exc}", file=sys.stderr)
        return False
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    summary = ", ".join(
        f"{v['account']}/{v['symbol']}({'|'.join(v['reasons'])})"
        for v in violations[:10]
    )
    body = (
        f"[TV-TPSL-AUDIT] {len(violations)} violator(s): {summary}"
        + (" ..." if len(violations) > 10 else "")
    )
    msg = json.dumps(
        {"from": "tv-paper-tpsl-audit", "timestamp": now, "body": body},
        ensure_ascii=False,
    ).encode("utf-8")
    r.lpush("bus:broadcast:log", msg)
    r.ltrim("bus:broadcast:log", 0, 99)
    return True


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--snapshot", default=str(DEFAULT_SNAPSHOT),
                    help="Path to positions snapshot JSON")
    ap.add_argument("--broadcast", action="store_true",
                    help="Broadcast violators on Redis bus")
    args = ap.parse_args(argv)

    snap_path = Path(args.snapshot)
    if not snap_path.exists():
        print(f"Snapshot not found: {snap_path}", file=sys.stderr)
        print(
            "Produce one via mcp__tradingview-desktop__ui_evaluate reading the "
            "positions table, or pass --snapshot PATH.",
            file=sys.stderr,
        )
        return 2

    try:
        data = json.loads(snap_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"Invalid snapshot JSON: {exc}", file=sys.stderr)
        return 2

    if isinstance(data, dict) and "positions" in data:
        data = data["positions"]
    if not isinstance(data, list):
        print("Snapshot must be a list of positions (or {positions: [...]})",
              file=sys.stderr)
        return 2

    violations = audit_positions(data)
    print(f"Audited {len(data)} positions, {len(violations)} violator(s)")
    for v in violations:
        mark = "WATCHED" if v["watched"] else "       "
        print(
            f"  [{mark}] {v['account']:<16} {v['symbol']:<14} {v['side']:<5} "
            f"entry={v['entry']} tp={v['tp']} sl={v['sl']} :: "
            f"{','.join(v['reasons'])}"
        )

    if violations:
        append_violators(violations)
        print(f"Logged to {VIOLATORS_LOG}")
        if args.broadcast:
            ok = broadcast(violations)
            print("Broadcast sent" if ok else "Broadcast skipped")
        return 1  # non-zero exit if violators present
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
