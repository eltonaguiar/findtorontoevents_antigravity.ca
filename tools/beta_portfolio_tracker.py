#!/usr/bin/env python3
"""beta_portfolio_tracker.py — the honest, deployable system after an exhaustive
alpha hunt found no net-of-cost systematic edge on free data (see
reports/FREE_DATA_EDGE_HUNT_CAPSTONE_2026-07-04.md; swarm 3/3 verdict = deploy beta).

This is BETA HARVESTING, not alpha: own a diversified basket, weight sleeves by
INVERSE VOLATILITY (risk-parity-lite), and apply a LIGHT crash guard (halve a
sleeve's weight when it is below its 200-day MA — captures sustained-bear
protection without the whipsaw of a binary in/out trend overlay, which we showed
does NOT improve risk-adjusted return: Calmar 0.73->0.65 on 2021-26).

Sleeves (deployable proxies in parentheses — the tracker computes weights from the
free DB feeds; a real account holds the liquid ETF/asset):
  EQUITY     (VTI / SPY)         <- equity_daily_ohlcv equal-weight basket
  COMMODITY  (DBC / a broad CTA) <- futures_daily_ohlcv 11-contract basket
  CRYPTO     (BTC)               <- crypto_ohlcv BTCUSDT daily (small sleeve; short history)
  BONDS      (AGG / TLT)         <- NOT in the free DB; recommended sleeve, add a feed to enable

Success metric is NOT "beat the market" — it is: capture the diversified risk
premium (~0.8-1.0 Sharpe historically) with controlled drawdown, at near-zero
cost and effort. Benchmark against 60/40, not against imaginary alpha.

Opt-in / read-only sidecar: writes ONE status JSON (target weights + NAV log). It
places no orders and changes no production path.

    python3 tools/beta_portfolio_tracker.py            # write status JSON
    python3 tools/beta_portfolio_tracker.py --stdout   # print, no write
"""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)
from tools.db_env import get_stocks_creds  # noqa: E402
import pymysql  # noqa: E402

OUT_PATH = os.path.join(REPO, "audit_dashboard", "data", "beta_portfolio_status.json")
VOL_LOOKBACK = 60      # trailing days for inverse-vol weighting
MA_LEN = 200           # crash-guard MA
CRASH_HAIRCUT = 0.5    # halve a sleeve's weight when below its 200d MA


def _db():
    keep = ("host", "user", "password", "database", "port", "connect_timeout")
    return pymysql.connect(**{k: v for k, v in get_stocks_creds().items() if k in keep})


def _eqw_index(rows_by_day):
    days = sorted(rows_by_day)
    idx = {}
    prev = None
    lvl = 1.0
    for d in days:
        cur = rows_by_day[d]
        if prev is not None:
            common = set(cur) & set(prev)
            if common:
                lvl *= 1 + sum(cur[s] / prev[s] - 1 for s in common) / len(common)
        idx[d] = lvl
        prev = cur
    return idx


def _load_sleeves(conn):
    sleeves = {}
    with conn.cursor() as cur:
        cur.execute("SELECT symbol,trade_date,close FROM equity_daily_ohlcv WHERE close>0 AND symbol<>'SPY' ORDER BY trade_date")
        eq = defaultdict(dict)
        for s, d, cl in cur.fetchall():
            eq[str(d)][s] = float(cl)
        sleeves["EQUITY"] = _eqw_index(eq)
        cur.execute("SELECT symbol,trade_date,close FROM futures_daily_ohlcv WHERE close>0 ORDER BY trade_date")
        co = defaultdict(dict)
        for s, d, cl in cur.fetchall():
            co[str(d)][s] = float(cl)
        sleeves["COMMODITY"] = _eqw_index(co)
        cur.execute(
            """SELECT DATE(FROM_UNIXTIME(timestamp/1000)) d,
                      CAST(SUBSTRING_INDEX(GROUP_CONCAT(close ORDER BY timestamp),',',-1) AS DECIMAL(30,10))
                 FROM crypto_ohlcv WHERE symbol='BTCUSDT' AND timeframe IN ('1h','1H','60m') GROUP BY d ORDER BY d"""
        )
        btc = {str(d): float(c) for d, c in cur.fetchall() if c}
        if len(btc) > VOL_LOOKBACK + 2:
            sleeves["CRYPTO"] = btc
    return sleeves


def _daily_rets(idx):
    days = sorted(idx)
    return [idx[days[i]] / idx[days[i - 1]] - 1 for i in range(1, len(days)) if idx[days[i - 1]] > 0]


def compute_status():
    now = datetime.now(timezone.utc)
    conn = _db()
    try:
        sleeves = _load_sleeves(conn)
    finally:
        conn.close()

    info = {}
    inv_vol = {}
    for name, idx in sleeves.items():
        days = sorted(idx)
        rets = _daily_rets(idx)[-VOL_LOOKBACK:]
        vol = statistics.pstdev(rets) * math.sqrt(252) if len(rets) > 5 else None
        last = idx[days[-1]]
        ma = (sum(idx[days[k]] for k in range(len(days) - MA_LEN, len(days))) / MA_LEN) if len(days) >= MA_LEN else None
        below_ma = (ma is not None and last < ma)
        if vol and vol > 0:
            inv_vol[name] = (1.0 / vol) * (CRASH_HAIRCUT if below_ma else 1.0)
        info[name] = {
            "ann_vol": round(vol, 3) if vol else None,
            "below_200d_ma": below_ma,
            "crash_guard_applied": below_ma,
            "history_days": len(days),
        }
    tot = sum(inv_vol.values())
    weights = {k: round(v / tot, 4) for k, v in inv_vol.items()} if tot > 0 else {}
    cash = round(1.0 - sum(weights.values()), 4)  # crash-guard haircuts leak to cash after renorm? keep explicit
    # renormalize so weights+cash=1 with haircut going to cash:
    raw_full = {}
    for name, idx in sleeves.items():
        days = sorted(idx); rets = _daily_rets(idx)[-VOL_LOOKBACK:]
        vol = statistics.pstdev(rets) * math.sqrt(252) if len(rets) > 5 else None
        if vol and vol > 0:
            raw_full[name] = 1.0 / vol
    tot_full = sum(raw_full.values()) or 1.0
    target = {}
    for name in sleeves:
        base = raw_full.get(name, 0) / tot_full
        target[name] = round(base * (CRASH_HAIRCUT if info[name]["below_200d_ma"] else 1.0), 4)
    cash = round(1.0 - sum(target.values()), 4)

    return {
        "system": "diversified beta harvesting (inverse-vol + light 200d crash guard)",
        "kind": "BETA — not alpha (see reports/FREE_DATA_EDGE_HUNT_CAPSTONE_2026-07-04.md)",
        "generated_at": now.isoformat(),
        "target_weights": target,
        "cash_weight": cash,
        "deployable_proxies": {"EQUITY": "VTI/SPY", "COMMODITY": "DBC", "CRYPTO": "BTC (small)", "BONDS": "AGG/TLT (add a feed to enable)"},
        "sleeve_info": info,
        "rebalance": "monthly or quarterly; benchmark vs 60/40, not vs alpha",
        "note": "Crash guard halves a sleeve below its 200d MA (leaks to cash). Bonds sleeve recommended but not in the free DB.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Diversified beta-harvesting portfolio tracker (read-only sidecar)")
    ap.add_argument("--stdout", action="store_true")
    args = ap.parse_args()
    st = compute_status()
    if args.stdout:
        print(json.dumps(st, indent=2, default=str))
        return 0
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w") as f:
        json.dump(st, f, indent=2, default=str)
    print(f"wrote {OUT_PATH} | weights={st['target_weights']} cash={st['cash_weight']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
