#!/usr/bin/env python3
"""§3 Liquidity score stub (Mercury / HEDGE_FUND plan — order book vs 24h flow).

Computes a **book-depth–to–volume ratio** for each eligible symbol:

  * ``depth_top5_base`` = sum of top-5 bid quantities + top-5 ask quantities (base asset)
  * ``volume_24h_base`` = Binance/Bybit 24h ``volume`` from ticker
  * ``liquidity_ratio`` = depth_top5_base / (volume_24h_base + ε)

Higher ratio ⇒ more visible resting liquidity relative to yesterday's traded base volume
(rough **market depth** proxy — not Kyle λ).

Also records **spread_pct** = (best_ask − best_bid) / mid · 100.

Symbols: unique ``symbol`` from ``dashboard_data.json`` **active** picks that normalize
to ``*USDT`` spot pairs. Non-crypto symbols are skipped after first failed fetch.

Data sources: ``alpha_engine.api_failover`` (Binance mirror chain + Bybit fallbacks).

Usage:
  python tools/liquidity_score_stub.py
  python tools/liquidity_score_stub.py --max-symbols 25 --redis-alert
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

try:
    from alpha_engine.api_failover import fetch_orderbook, fetch_ticker_24h
except ImportError:
    fetch_orderbook = None  # type: ignore
    fetch_ticker_24h = None  # type: ignore

DEFAULT_DASHBOARD = REPO / "audit_dashboard" / "data" / "dashboard_data.json"
OUT_JSON = REPO / "tools" / "data" / "liquidity_snapshot.json"


def _norm(sym: str) -> str:
    if not sym:
        return ""
    s = str(sym).upper().replace("-", "").replace("/", "")
    if s.endswith("USD") and not s.endswith("USDT"):
        s = s + "T"
    return s


def load_usdt_symbols(path: Path, cap: int) -> List[str]:
    with open(path, "r", encoding="utf-8") as f:
        doc = json.load(f)
    picks = (doc.get("picks") or {}).get("active") or []
    if not isinstance(picks, list):
        return []
    seen = set()
    out: List[str] = []
    for p in picks:
        if not isinstance(p, dict):
            continue
        s = _norm(p.get("symbol") or "")
        if not s.endswith("USDT") or len(s) < 6:
            continue
        if s in seen:
            continue
        seen.add(s)
        out.append(s)
        if len(out) >= cap:
            break
    return out


def sum_qty_top5(levels: List) -> float:
    total = 0.0
    for row in levels[:5]:
        if not row or len(row) < 2:
            continue
        try:
            total += float(row[1])
        except (TypeError, ValueError):
            continue
    return total


def analyze_symbol(sym: str) -> Optional[Dict[str, Any]]:
    if not fetch_orderbook or not fetch_ticker_24h:
        return None
    ob = fetch_orderbook(sym, limit=5)
    tk = fetch_ticker_24h(sym)
    if not ob or not tk:
        return None
    bids = ob.get("bids") or []
    asks = ob.get("asks") or []
    if not bids or not asks:
        return None
    try:
        bp = float(bids[0][0])
        ap = float(asks[0][0])
    except (TypeError, ValueError, IndexError):
        return None
    mid = 0.5 * (bp + ap)
    spread_pct = 100.0 * (ap - bp) / mid if mid > 0 else 0.0

    depth_b = sum_qty_top5(bids) + sum_qty_top5(asks)
    try:
        vol_b = float(tk.get("volume") or 0)
    except (TypeError, ValueError):
        vol_b = 0.0
    try:
        qv = float(tk.get("quoteVolume") or 0)
    except (TypeError, ValueError):
        qv = 0.0

    eps = 1e-12
    ratio = depth_b / (vol_b + eps)

    return {
        "symbol": sym,
        "source_book": ob.get("source"),
        "spread_pct": round(spread_pct, 6),
        "depth_top5_base": round(depth_b, 8),
        "volume_24h_base": round(vol_b, 4),
        "quote_volume_24h": round(qv, 2),
        "liquidity_ratio": round(ratio, 12),
        "mid_price": round(mid, 8),
    }


def redis_broadcast(msg: str) -> None:
    bus = Path(r"C:\Users\zerou\redis-bus\agent_bus.py")
    if not bus.is_file():
        return
    try:
        subprocess.run(
            [sys.executable, str(bus), "broadcast", "cursor-composer", msg],
            check=False,
            timeout=15,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.SubprocessError):
        pass


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--dashboard", type=str, default=str(DEFAULT_DASHBOARD))
    ap.add_argument("--max-symbols", type=int, default=35)
    ap.add_argument("--out", type=str, default=str(OUT_JSON))
    ap.add_argument(
        "--spread-alert-pct",
        type=float,
        default=0.25,
        help="alert if any symbol spread_pct exceeds this",
    )
    ap.add_argument(
        "--ratio-floor",
        type=float,
        default=1e-8,
        help="alert if liquidity_ratio below this (very thin vs 24h vol)",
    )
    ap.add_argument("--redis-alert", action="store_true")
    args = ap.parse_args()

    path = Path(args.dashboard)
    if not path.is_file():
        print("ERROR: dashboard not found: %s" % path, file=sys.stderr)
        return 1
    if fetch_orderbook is None:
        print("ERROR: could not import alpha_engine.api_failover", file=sys.stderr)
        return 1

    symbols = load_usdt_symbols(path, args.max_symbols)
    rows: List[Dict[str, Any]] = []
    failed: List[str] = []
    spread_alert = False
    ratio_alert = False

    for sym in symbols:
        row = analyze_symbol(sym)
        if row is None:
            failed.append(sym)
            continue
        rows.append(row)
        if row["spread_pct"] > args.spread_alert_pct:
            spread_alert = True
        if row["liquidity_ratio"] < args.ratio_floor:
            ratio_alert = True

    rows.sort(key=lambda r: r.get("liquidity_ratio", 0), reverse=True)

    report: Dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_dashboard": str(path).replace("\\", "/"),
        "symbols_requested": len(symbols),
        "symbols_ok": len(rows),
        "symbols_failed": failed,
        "thresholds": {
            "spread_alert_pct": args.spread_alert_pct,
            "ratio_floor": args.ratio_floor,
        },
        "liquidity_alert": bool(spread_alert or ratio_alert),
        "symbols": rows,
        "note": "Mercury: extend with top-5 notional / full L2; cap size at 2% of liquidity — not implemented here.",
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print("ok=%d failed=%d alert=%s -> %s" % (len(rows), len(failed), report["liquidity_alert"], out_path))

    if args.redis_alert:
        msg = (
            "LIQUIDITY-STUB: ok=%d failed=%d spread_alert=%s ratio_alert=%s | %s"
            % (
                len(rows),
                len(failed),
                spread_alert,
                ratio_alert,
                str(out_path).replace("\\", "/"),
            )
        )
        redis_broadcast(msg)

    return 2 if report["liquidity_alert"] else 0


if __name__ == "__main__":
    sys.exit(main())
