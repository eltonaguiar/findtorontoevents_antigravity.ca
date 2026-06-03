#!/usr/bin/env python3
"""Purged-embargoed cross-validation for the ETF dual-momentum sleeve (2026-06-03).

PR #502 reported PF 3.57 / Sharpe 1.62 / attribution t=2.36 on the full 48-month
walk-forward. The cross-review demanded out-of-sample confirmation (not full-sample
only). This splits the realized monthly-return stream into an EARLY train window and
a LATER held-out test window separated by an EMBARGO gap (drop the boundary months so
the 12m-lookback signal of the first test month cannot peek across the split), then
compares train-PF vs test-PF and reports decay.

Decision rule: the sleeve STAYS a forward-candidate only if test-PF >= 0.8 * train-PF
(<=20% decay) AND test stays profitable (PF>1). Else downgrade to WATCH.

Reuses backtest_dual_momentum (the realized returns are already walk-forward, so an
early/late split is a valid OOS test). Pure metrics are unit-tested; run() is live.
"""
from __future__ import annotations

import math
import os
import sys
from typing import Dict, List

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from etf_dual_momentum_backtest import (RISK_ASSETS, CASH, backtest_dual_momentum,
                                        monthly_closes)


def _pf(arr: np.ndarray) -> float:
    g, l = arr[arr > 0].sum(), -arr[arr < 0].sum()
    return float(g / l) if l > 0 else (999.0 if g > 0 else 0.0)


def _sharpe(arr: np.ndarray) -> float:
    return float(arr.mean() / arr.std(ddof=1) * math.sqrt(12)) if len(arr) > 1 and arr.std(ddof=1) > 0 else 0.0


def purged_split_metrics(monthly_returns: List[float], train_frac: float = 0.6,
                         embargo: int = 1) -> Dict:
    """Early-train vs late-test split with an embargo gap. Returns per-segment
    PF/Sharpe + decay + verdict."""
    arr = np.asarray(monthly_returns, dtype=float)
    n = len(arr)
    n_train = int(n * train_frac)
    train = arr[:n_train]
    test = arr[n_train + embargo:]
    if len(train) < 6 or len(test) < 6:
        return {"verdict": "INSUFFICIENT", "n_train": len(train), "n_test": len(test)}
    train_pf, test_pf = _pf(train), _pf(test)
    decay = (train_pf - test_pf) / train_pf if train_pf > 0 else None
    holds = (test_pf >= 0.8 * train_pf) and (test_pf > 1.0)
    return {
        "n_train": len(train), "n_test": len(test), "embargo": embargo,
        "train_pf": round(train_pf, 3), "test_pf": round(test_pf, 3),
        "train_sharpe": round(_sharpe(train), 3), "test_sharpe": round(_sharpe(test), 3),
        "decay_pct": round(decay * 100, 1) if decay is not None else None,
        "verdict": "HOLDS_OOS" if holds else "DECAYS",
    }


def run():  # pragma: no cover — live network
    import json
    import data_fetcher
    import return_attribution as ra
    price = {a: data_fetcher.fetch_ohlcv(a, period_days=2600)[0]
             for a in RISK_ASSETS + [CASH]}
    res = backtest_dual_momentum(price)
    rets = res.get("monthly_returns", [])
    cv = purged_split_metrics(rets)
    out = {"full_pf": res.get("profit_factor"), "full_sharpe": res.get("sharpe_annual"),
           "n_months": res.get("n_months"), "cv": cv}
    # test-segment attribution vs SPY (thin-n caveat noted)
    spy = monthly_closes(price["SPY"]).pct_change().dropna().tolist()
    n_train = int(len(rets) * 0.6)
    test = rets[n_train + 1:]
    if len(test) >= 6 and len(spy) >= len(rets):
        bench_test = spy[-len(test):]
        out["test_attribution_vs_spy"] = ra.attribution_gate(test, bench_test)
    print(json.dumps(out, indent=2, default=str))
    return out


if __name__ == "__main__":  # pragma: no cover
    run()
