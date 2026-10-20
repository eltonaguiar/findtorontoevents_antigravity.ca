"""Trend-following sleeve: 1/3/12-m lookback blend, ~10% vol sizing."""
from __future__ import annotations

import numpy as np

from combined_book.fetch import monthly_returns

TREND_LOOKBACKS = (1, 3, 12)


def blend_trend_score(closes, lookbacks=TREND_LOOKBACKS):
    if len(closes) <= max(lookbacks):
        return None
    scores = []
    for m in lookbacks:
        ret = closes.iloc[-1] / closes.iloc[-m - 1] - 1.0
        scores.append(float(ret))
    return float(np.mean(scores))


def realized_vol(monthly, window=12):
    if len(monthly) < 2:
        return 0.0
    return float(monthly.tail(window).std(ddof=0))


def trend_target_weights(closes_by_symbol, vol_target=0.10, cap_fraction=1.0):
    eligible = {
        s: c for s, c in closes_by_symbol.items()
        if blend_trend_score(c) is not None
    }
    raw = {}
    for s, c in eligible.items():
        v = realized_vol(monthly_returns(c))
        raw[s] = vol_target / v if v > 0 else 0.0
    total = sum(raw.values())
    if total <= 0:
        return {s: 0.0 for s in eligible}
    return {s: (x / total) * cap_fraction for s, x in raw.items()}
