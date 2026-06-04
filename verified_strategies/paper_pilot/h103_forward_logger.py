#!/usr/bin/env python3
"""H-103 forward-paper logger — starts the binding forward test (2026-06-03).

H-103 (hypothesis_registry) pre-registers the ETF cross-asset dual-momentum sleeve
(SPY/QQQ/EFA/AGG/GLD vs BIL). The backtest passed (PR #502/#509) but the BINDING test
is forward paper, n>=100. This logger computes the sleeve's CURRENT monthly pick from
live data and appends ONE dated record per month to a forward-paper log. Run monthly
(cron) — each run advances the forward sample. No capital, no ledger mutation: it only
records what the rule says to hold, so future-self can score realized forward PF/WR.

Idempotent per month (won't double-log the same YYYY-MM). Report-only.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Dict, List, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # verified_strategies/
sys.path.insert(0, ROOT)
from etf_dual_momentum_backtest import (RISK_ASSETS, CASH, LOOKBACK_M, TOP_K,
                                        dual_momentum_pick, monthly_closes)

LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "h103_forward_log.jsonl")
HYP_ID = "H-103"


def _existing_months(path: str) -> set:
    if not os.path.exists(path):
        return set()
    out = set()
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    out.add(json.loads(line).get("month"))
                except json.JSONDecodeError:
                    pass
    return out


def build_record(closes_by_asset: Dict, asof, asof_iso: str) -> Dict:
    """Compute the H-103 pick for the month following `asof`."""
    pick = dual_momentum_pick(closes_by_asset, asof, LOOKBACK_M, TOP_K, CASH)
    return {
        "hypothesis_id": HYP_ID,
        "strategy": "etf_dual_momentum_crossasset",
        "month": asof_iso[:7],
        "asof": asof_iso,
        "pick": pick,
        "universe": RISK_ASSETS, "cash": CASH,
        "lookback_m": LOOKBACK_M, "top_k": TOP_K,
        "note": "forward-paper record (no capital); score realized next-month return later",
    }


def log_current(closes_by_asset: Dict, asof, asof_iso: str,
                log_path: str = LOG_PATH) -> Optional[Dict]:
    """Append one record for the current month iff not already logged."""
    month = asof_iso[:7]
    if month in _existing_months(log_path):
        return None
    rec = build_record(closes_by_asset, asof, asof_iso)
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec) + "\n")
    return rec


def run():  # pragma: no cover — live network
    import data_fetcher
    price = {a: data_fetcher.fetch_ohlcv(a, period_days=500)[0]
             for a in RISK_ASSETS + [CASH]}
    closes = {a: monthly_closes(df) for a, df in price.items() if df is not None}
    asof = max(s.index[-1] for s in closes.values())
    rec = log_current(closes, asof, asof.isoformat())
    n = len(_existing_months(LOG_PATH))
    if rec:
        print(f"LOGGED {rec['month']}: hold {rec['pick']}  (forward n={n}/100)")
    else:
        print(f"already logged this month (forward n={n}/100)")
    return rec


if __name__ == "__main__":  # pragma: no cover
    run()
