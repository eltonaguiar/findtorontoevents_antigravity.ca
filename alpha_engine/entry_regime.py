"""Regime stamping at entry (2026-11-20).

The peer question "did the 65% time-cap exits cluster in a regime?" was
unanswerable because trade rows carry no regime at the moment of entry. These
helpers are pure (list in, dict out) so they can stamp picks without pandas and
be tested exactly.
"""

from __future__ import annotations

import statistics

TREND_WINDOW = 200
VOL_WINDOW = 20


def _pct_rank(values: list[float], x: float) -> float:
    if not values:
        return 0.5
    return sum(1 for v in values if v <= x) / len(values)


def classify_regime(closes: list[float], index: int) -> dict:
    """Classify the regime as of ``index`` using only bars up to and including it."""
    if index < 0 or index >= len(closes):
        raise IndexError("index outside series")
    window = closes[: index + 1]
    close = window[-1]
    sma = statistics.fmean(window[-TREND_WINDOW:]) if len(window) >= TREND_WINDOW else None
    rets = [window[i] / window[i - 1] - 1 for i in range(1, len(window)) if window[i - 1]]
    vol20 = statistics.pstdev(rets[-VOL_WINDOW:]) if len(rets) >= 2 else None
    hist = [statistics.pstdev(rets[i - VOL_WINDOW:i]) for i in range(VOL_WINDOW, len(rets) + 1) if i <= len(rets)]
    hist = [h for h in hist if h is not None]
    vol_pct = _pct_rank(hist, vol20) if (vol20 is not None and hist) else 0.5
    trend = "unknown" if sma is None else ("up" if close > sma else "down")
    vol = "high" if vol_pct >= 0.67 else ("low" if vol_pct <= 0.33 else "mid")
    return {
        "regime_trend": trend,
        "regime_vol": vol,
        "regime_label": f"{trend}/{vol}",
        "regime_vol_percentile": round(vol_pct, 3),
        "regime_close_vs_sma": (round(close / sma - 1, 5) if sma else None),
        "regime_bars_available": len(window),
    }


def stamp_regime_at_entry(pick: dict, closes: list[float], index: int) -> dict:
    """Return ``pick`` with regime_at_entry_* fields added (no mutation)."""
    out = dict(pick)
    for k, v in classify_regime(closes, index).items():
        out[f"at_entry_{k}"] = v
    out["entry_regime_stamped"] = True
    return out
