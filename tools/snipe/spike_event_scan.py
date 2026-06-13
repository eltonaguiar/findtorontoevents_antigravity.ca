#!/usr/bin/env python3
"""spike_event_scan.py — H-113 step 1: historical 1-min spike-event extraction.

Detects the FROZEN H-113 trigger (docs/plans/2026-06-13-snipe-shortterm-spike-design.md §1)
on Binance 1-minute klines and emits candidate trades for BOTH arms in the
tools/replay_harness.py --trades-json format. The trigger spec is pre-registered;
DO NOT add CLI knobs for thresholds — tuning = a new family with FDR accounting.

Trigger (frozen): 5-min rolling |return| >= 2.0% AND 5-min volume >= 5x the
trailing 2-hour median 5-min volume; one event per symbol per 2h (first wins).
Arms: CHASE (with spike direction) + FADE (against). Geometry: TP +1.0% /
SL -0.7% from the first 1-min close AFTER the event bar; 30-min time-exit is
applied by the replay/loop layer (horizon), not encoded here.

Binance failover chain per CLAUDE.md: api, api1, api2, api3 mirrors.
1-min history depth on spot klines is ample; we default to the last 14 days
(cap per run) to keep request counts sane: 14d x 1min = ~20k bars = 14 requests
of 1500 bars per symbol.

Usage:
    python3 tools/snipe/spike_event_scan.py --symbols BTCUSDT,ETHUSDT --days 7
    python3 tools/snipe/spike_event_scan.py --top 100 --days 14 \
        --out /tmp/snipe_trades.json
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

MIRRORS = ["https://api.binance.com", "https://api1.binance.com",
           "https://api2.binance.com", "https://api3.binance.com"]

# ── FROZEN H-113 trigger constants (pre-registered; do not parametrize) ──
RET_5M_MIN = 0.02          # |5-min return| >= 2.0%
VOL_5M_MULT = 5.0          # 5-min volume >= 5x trailing 2h median 5-min volume
COOLDOWN_MIN = 120         # one event per symbol per 2h
TP_PCT, SL_PCT = 0.010, 0.007  # +1.0% / -0.7% from post-event entry


def _get(path: str, params: dict) -> object:
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    last_err = None
    for base in MIRRORS:
        try:
            req = urllib.request.Request(f"{base}{path}?{qs}",
                                         headers={"User-Agent": "snipe-scan/1.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                return json.loads(r.read())
        except Exception as e:  # noqa: BLE001 — failover chain
            last_err = e
            continue
    raise RuntimeError(f"all Binance mirrors failed for {path}: {last_err}")


def top_usdt_symbols(n: int) -> list[str]:
    tickers = _get("/api/v3/ticker/24hr", {})
    rows = [t for t in tickers
            if t.get("symbol", "").endswith("USDT")
            and not any(x in t["symbol"] for x in ("UP", "DOWN", "BULL", "BEAR"))]
    rows.sort(key=lambda t: float(t.get("quoteVolume", 0)), reverse=True)
    return [t["symbol"] for t in rows[:n]]


def fetch_1m(symbol: str, days: int) -> list[tuple[int, float, float]]:
    """[(open_ms, close, volume)] ascending for the last `days` days."""
    end = int(time.time() * 1000)
    start = end - days * 86400_000
    out: list[tuple[int, float, float]] = []
    cur = start
    while cur < end:
        kl = _get("/api/v3/klines", {"symbol": symbol, "interval": "1m",
                                     "startTime": cur, "limit": 1500})
        if not kl:
            break
        for k in kl:
            out.append((int(k[0]), float(k[4]), float(k[5])))
        nxt = int(kl[-1][0]) + 60_000
        if nxt <= cur:
            break
        cur = nxt
        time.sleep(0.15)  # stay friendly to the public endpoint
    return out


def scan_symbol(symbol: str, bars: list[tuple[int, float, float]]) -> list[dict]:
    """Frozen-trigger events -> two candidate trades each (CHASE + FADE)."""
    events: list[dict] = []
    if len(bars) < 125:
        return events
    last_event_ms = 0
    # rolling structures: 5-min return needs close[i-5]; 2h median needs 24
    # trailing 5-min volume buckets ending before the current 5-min window.
    vols = [b[2] for b in bars]
    closes = [b[1] for b in bars]
    for i in range(125, len(bars)):
        ts = bars[i][0]
        if ts - last_event_ms < COOLDOWN_MIN * 60_000:
            continue
        c_now, c_prev = closes[i], closes[i - 5]
        if c_prev <= 0:
            continue
        ret5 = (c_now - c_prev) / c_prev
        if abs(ret5) < RET_5M_MIN:
            continue
        vol5 = sum(vols[i - 4:i + 1])
        trailing = [sum(vols[j - 4:j + 1]) for j in range(i - 5, i - 125, -5)]
        med = statistics.median(trailing) if trailing else 0.0
        if med <= 0 or vol5 < VOL_5M_MULT * med:
            continue
        if i + 1 >= len(bars):
            break
        entry_ts, entry = bars[i + 1][0], closes[i + 1]  # first close AFTER event bar
        if entry <= 0:
            continue
        last_event_ms = ts
        spike_dir = "UP" if ret5 > 0 else "DOWN"
        for arm in ("CHASE", "FADE"):
            long_side = (spike_dir == "UP") == (arm == "CHASE")
            direction = "LONG" if long_side else "SHORT"
            tp = entry * (1 + TP_PCT) if long_side else entry * (1 - TP_PCT)
            sl = entry * (1 - SL_PCT) if long_side else entry * (1 + SL_PCT)
            events.append({
                "symbol": symbol, "direction": direction,
                "entry_time": datetime.fromtimestamp(entry_ts / 1000,
                                                     timezone.utc).isoformat(),
                "entry": entry, "tp": round(tp, 10), "sl": round(sl, 10),
                "arm": arm, "spike_dir": spike_dir,
                "ret5_pct": round(ret5 * 100, 3),
                "vol5_mult": round(vol5 / med, 2),
            })
    return events


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--symbols", help="comma list (smoke runs)")
    g.add_argument("--top", type=int, help="top-N USDT symbols by 24h quote volume")
    ap.add_argument("--days", type=int, default=14)
    ap.add_argument("--out", default=str(REPO / "reports" / "snipe_events.json"))
    args = ap.parse_args()

    symbols = ([s.strip().upper() for s in args.symbols.split(",") if s.strip()]
               if args.symbols else top_usdt_symbols(args.top))
    print(f"[snipe-scan] {len(symbols)} symbols x {args.days}d 1-min")
    all_events: list[dict] = []
    for n, sym in enumerate(symbols, 1):
        try:
            bars = fetch_1m(sym, args.days)
            ev = scan_symbol(sym, bars)
            all_events.extend(ev)
            print(f"  [{n}/{len(symbols)}] {sym}: {len(bars)} bars -> {len(ev)//2} events")
        except Exception as e:  # noqa: BLE001 — one bad symbol must not kill the scan
            print(f"  [{n}/{len(symbols)}] {sym}: FAILED ({e})")
    Path(args.out).write_text(json.dumps(all_events, indent=1))
    n_events = len(all_events) // 2
    print(f"[snipe-scan] {n_events} events ({len(all_events)} arm-trades) -> {args.out}")
    print("Next: split by arm and feed each to tools/replay_harness.py "
          "--family snipe_spike_30m_<arm> --asset-class CRYPTO --horizon-bars 1 "
          "(NOTE: harness uses 1h bars — for true 30-min resolution use the "
          "1-min replay in the upcoming snipe_loop; harness run is the coarse gate)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
