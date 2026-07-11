#!/usr/bin/env python3
"""tactical_rotation_tracker.py — asset-class MOMENTUM ROTATION (dual-momentum / TAA).

The one strategy that beat passive on a risk-adjusted basis in the 2026-07 hunt
(reports/TACTICAL_ROTATION_EDGE_2026-07-04.md): hold the top-N asset-class ETFs by
trailing momentum, monthly, with an absolute-momentum filter to cash/bonds. Rotating
across LOW-CORRELATION asset classes works where single-stock momentum was null.

Robustness (2018-2026, look-ahead-free, net cost, both-halves): ALL 16 (top-N x
lookback) cells cut drawdown to -12/-17% vs SPY -24%; the 9-month lookback region is
uniformly best (Sharpe 1.09-1.21, Calmar 0.81-1.10 vs SPY 1.00/0.68). Default here:
top-5, 9-month lookback, monthly. It is smart-beta / TAA (better RISK-ADJUSTED return
via drawdown control), NOT excess return over the market — and it is in-sample-robust,
which is not proven-forward. Deploy at modest size; forward-track.

Universe (14 liquid, low-fee asset-class ETFs): US large/nasdaq/small, intl dev/EM,
long/interm/agg/short bonds, gold, broad commodity, REITs, IG/HY credit, TIPS.

Read-only sidecar: writes ONE status JSON (current target holdings). No orders.

    python3 tools/tactical_rotation_tracker.py            # write status JSON
    python3 tools/tactical_rotation_tracker.py --stdout   # print, no write
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)
from tools.db_env import get_stocks_creds  # noqa: E402
import pymysql  # noqa: E402

OUT_PATH = os.path.join(REPO, "audit_dashboard", "data", "tactical_rotation_status.json")
UNIVERSE = ["SPY", "QQQ", "IWM", "EFA", "EEM", "TLT", "IEF", "AGG", "GLD", "DBC", "VNQ", "LQD", "HYG", "TIP"]
TOP_N = 5
# 6-month lookback is the REGIME-ROBUST default: over 2007-2026 (incl the 2008 GFC where SPY
# drew down -51%) top5-6m had Sharpe 0.88 vs SPY 0.74, MaxDD -19%, positive in all 3 time-thirds.
# (9-month was marginally better in the 2018-26 window only; 6-month generalizes across crashes.)
# The POC picks (poc_picks, entered 2026-07-04) were locked with the 9-month signal — both are in
# the robust region; future rebalances use 6-month.
LOOKBACK_MONTHS = 6
CASH_ASSET = "AGG"  # where negative-absolute-momentum slots go


def _db():
    keep = ("host", "user", "password", "database", "port", "connect_timeout")
    return pymysql.connect(**{k: v for k, v in get_stocks_creds().items() if k in keep})


def compute_status():
    now = datetime.now(timezone.utc)
    conn = _db()
    px = defaultdict(dict)
    try:
        with conn.cursor() as cur:
            fmt = ",".join(["%s"] * len(UNIVERSE))
            cur.execute(f"SELECT symbol,trade_date,close FROM etf_daily_ohlcv WHERE close>0 AND symbol IN ({fmt}) ORDER BY trade_date", UNIVERSE)
            for s, d, cl in cur.fetchall():
                px[s][str(d)] = float(cl)
    finally:
        conn.close()

    def mom(s):
        ds = sorted(px.get(s, {}))
        n = LOOKBACK_MONTHS * 21
        if len(ds) < n + 1:
            return None
        d0, d1 = ds[-n], ds[-1]
        return (px[s][d1] / px[s][d0] - 1) if px[s][d0] > 0 else None

    scored = [(s, mom(s)) for s in UNIVERSE if mom(s) is not None]
    scored.sort(key=lambda x: -x[1])
    top = scored[:TOP_N]
    w = round(1.0 / TOP_N, 4)
    holdings = []
    cash_slots = 0
    for s, m in top:
        if m > 0:
            holdings.append({"etf": s, "weight": w, "mom_9m": round(m, 4)})
        else:
            cash_slots += 1
    if cash_slots:
        holdings.append({"etf": CASH_ASSET, "weight": round(w * cash_slots, 4), "mom_9m": None, "note": "abs-momentum filter -> bonds/cash"})

    latest = max((max(px[s]) for s in px if px[s]), default=None)
    return {
        "strategy": "asset-class momentum rotation (dual-momentum / TAA)",
        "kind": "smart-beta / tactical allocation — better risk-adjusted return via drawdown control; NOT excess return vs market; in-sample-robust, forward-track",
        "generated_at": now.isoformat(),
        "params": {"top_n": TOP_N, "lookback_months": LOOKBACK_MONTHS, "rebalance": "monthly", "abs_filter": "negative-momentum slots -> " + CASH_ASSET},
        "as_of_price_date": latest,
        "target_holdings": holdings,
        "full_ranking": [{"etf": s, "mom_9m": round(m, 4)} for s, m in scored],
        "note": "Rebalance monthly. Deployable with these ETFs or low-fee index-fund equivalents. Benchmark vs SPY buy-hold (Sharpe ~1.0); this improves Calmar/DD, roughly matches return.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Asset-class momentum rotation tracker (read-only sidecar)")
    ap.add_argument("--stdout", action="store_true")
    args = ap.parse_args()
    st = compute_status()
    if args.stdout:
        print(json.dumps(st, indent=2, default=str))
        return 0
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w") as f:
        json.dump(st, f, indent=2, default=str)
    print(f"wrote {OUT_PATH} | holdings={[h['etf'] for h in st['target_holdings']]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
