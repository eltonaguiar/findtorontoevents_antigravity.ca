"""Vol/trend regime labels and robustness gate (EAGLE2 §3.5)."""

from __future__ import annotations

from typing import Dict

import numpy as np
import pandas as pd


def assign_regimes(df: pd.DataFrame) -> pd.DataFrame:
    """Add vol_regime and trend_regime columns from close prices."""
    rets = df["close"].pct_change().dropna()
    vol = rets.rolling(20).std() * np.sqrt(252)
    trend = df["close"] / df["close"].rolling(100).mean()

    out = df.loc[vol.index.min() :].copy()
    out["vol_regime"] = pd.qcut(vol.reindex(out.index), 2, labels=["low_vol", "high_vol"], duplicates="drop")
    out["trend_regime"] = np.where(trend.reindex(out.index) > 1.0, "uptrend", "downtrend")
    return out


def regime_gate(pass_counts: Dict[str, bool], min_regimes: int = 3) -> bool:
    """True when at least min_regimes buckets passed admissibility."""
    return sum(1 for ok in pass_counts.values() if ok) >= min_regimes
