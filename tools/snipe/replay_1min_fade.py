#!/usr/bin/env python3
"""replay_1min_fade.py — H-113's FINAL registered comparison (then the family closes).

The 1h coarse gate (replay_harness, 2026-06-12) REFUTED the CHASE arm outright
(WR 21.8% / net PF 0.27) and scored FADE null-with-a-caveat (47.2% / 0.863) —
~25% of its bars were ambiguity-penalized because 1h bars cannot order an
intra-hour TP-and-SL double touch. This tool is the pre-registered TRUE
instrument: 1-minute first-touch replay over the exact 30-minute horizon.

Methodology (matches the H-113 registration; nothing tunable here):
  * per FADE trade: the 30 1-min bars strictly AFTER entry_time
  * first-touch TP/SL walk; same-1-min-bar double touch -> SL (conservative)
    + ambiguous flag (at 1-min this should be rare — that's the point)
  * neither touched in 30 bars -> TIME_EXIT at bar-30 close
  * net of 16bp RT; metrics via tools/pf_ci_lower (clusters = symbol|UTC-hour)
  * R1 time-split halves by entry_time

Outcome contract (registered): FADE pf_ci_lower > 1.0 at n_eff >= 80 AND both
halves net PF > 1.0 -> nominate to the live 30-min shadow loop. Otherwise the
snipe_spike_30m family is CLOSED — no further comparisons.

Usage: python3 tools/snipe/replay_1min_fade.py [--events reports/snipe_events_14d.json]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.pf_ci_lower import pf_ci_lower, effective_n  # noqa: E402
from tools.snipe.spike_event_scan import _get  # noqa: E402  (mirror failover)

COST_FRAC = 0.0016  # 16bp RT
HORIZON_MIN = 30


def fetch_1m_window(symbol: str, start_ms: int, minutes: int):
    kl = _get("/api/v3/klines", {"symbol": symbol, "interval": "1m",
                                 "startTime": start_ms, "limit": minutes + 2})
    return [(int(k[0]), float(k[2]), float(k[3]), float(k[4])) for k in kl]


def replay_trade(t: dict, bars) -> dict | None:
    entry_ms = int(datetime.fromisoformat(t["entry_time"]).timestamp() * 1000)
    entry, tp, sl = float(t["entry"]), float(t["tp"]), float(t["sl"])
    is_long = t["direction"] == "LONG"
    walk = [b for b in bars if b[0] > entry_ms][:HORIZON_MIN]
    if len(walk) < HORIZON_MIN // 2:
        return None  # insufficient coverage
    for (ts, high, low, close) in walk:
        tp_hit = high >= tp if is_long else low <= tp
        sl_hit = low <= sl if is_long else high >= sl
        if sl_hit:
            pnl = (sl / entry - 1) if is_long else (entry / sl - 1)
            return {"exit": "SL_HIT", "pnl_net": pnl * 100 - COST_FRAC * 100,
                    "ambiguous": bool(tp_hit)}
        if tp_hit:
            pnl = (tp / entry - 1) if is_long else (entry / tp - 1)
            return {"exit": "TP_HIT", "pnl_net": pnl * 100 - COST_FRAC * 100,
                    "ambiguous": False}
    last = walk[-1][3]
    pnl = (last / entry - 1) if is_long else (entry / last - 1)
    return {"exit": "TIME_EXIT", "pnl_net": pnl * 100 - COST_FRAC * 100,
            "ambiguous": False}


def block(results):
    pnls = [r["pnl_net"] for r in results]
    clusters = [r["cluster"] for r in results]
    n = len(pnls)
    wins = sum(1 for p in pnls if p > 0)
    ci = pf_ci_lower(pnls, clusters=clusters)
    neff = effective_n(pnls, clusters) if n else {"n_eff": 0}
    return {"n": n, "wr_pct": round(100 * wins / n, 1) if n else None,
            "pf_net": (round(ci["pf"], 3) if ci["pf"] not in (None, float("inf"))
                       else ci["pf"]),
            "pf_ci_lower": ci["pf_ci_lower"], "n_eff": neff["n_eff"],
            "exits": {e: sum(1 for r in results if r["exit"] == e)
                      for e in ("TP_HIT", "SL_HIT", "TIME_EXIT")},
            "ambiguous_n": sum(1 for r in results if r["ambiguous"])}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--events", default=str(REPO / "reports" / "snipe_events_14d.json"))
    ap.add_argument("--out", default=str(REPO / "reports" / "snipe_fade_1min_verdict.json"))
    args = ap.parse_args()

    trades = [t for t in json.load(open(args.events)) if t.get("arm") == "FADE"]
    trades.sort(key=lambda t: t["entry_time"])
    print(f"[fade-1min] {len(trades)} FADE trades to replay")

    results, no_data = [], 0
    for i, t in enumerate(trades, 1):
        try:
            entry_ms = int(datetime.fromisoformat(t["entry_time"]).timestamp() * 1000)
            bars = fetch_1m_window(t["symbol"], entry_ms - 60_000, HORIZON_MIN + 2)
            r = replay_trade(t, bars)
            if r is None:
                no_data += 1
                continue
            hour = datetime.fromtimestamp(entry_ms / 1000, timezone.utc).strftime("%Y-%m-%dT%H")
            r["cluster"] = f"{t['symbol']}|{hour}"
            r["entry_time"] = t["entry_time"]
            results.append(r)
        except Exception:
            no_data += 1
        if i % 100 == 0:
            print(f"  {i}/{len(trades)} replayed ({no_data} no-data)")
        time.sleep(0.05)

    main_b = block(results)
    half = len(results) // 2
    h1, h2 = block(results[:half]), block(results[half:])
    pass_ci = (main_b["pf_ci_lower"] is not None and main_b["pf_ci_lower"] > 1.0
               and main_b["n_eff"] >= 80)
    pass_halves = all(isinstance(b["pf_net"], (int, float)) and b["pf_net"] > 1.0
                      for b in (h1, h2))
    verdict = "NOMINATE_TO_LIVE_SHADOW_LOOP" if (pass_ci and pass_halves) \
        else "FAMILY_CLOSED"
    out = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "method": "1-min first-touch, SL-wins-ties, 30-min time-exit, net 16bp "
                     "(H-113 registered final comparison)",
           "no_data": no_data, "main": main_b, "r1_split": {"h1": h1, "h2": h2},
           "bars_granularity_note": "ambiguous_n at 1-min should be << the 1h gate's "
                                    "(133/527); if not, geometry is too tight to order even at 1m",
           "verdict": verdict}
    Path(args.out).write_text(json.dumps(out, indent=1))
    print(json.dumps({k: out[k] for k in ("main", "r1_split", "verdict")}, indent=1))
    print(f"-> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
