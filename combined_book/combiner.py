"""Inverse-vol sleeve combination, per-sleeve cap, book-level vol-cap selection rule."""
from __future__ import annotations

import numpy as np

from combined_book.rules import KILL_DRAWDOWN, PER_SLEEVE_CAP, VOL_TARGET_MAX, VOL_TARGET_MIN


def inverse_vol_weights(vols):
    inv = {k: (1.0 / v if v > 0 else 0.0) for k, v in vols.items()}
    total = sum(inv.values())
    if total <= 0:
        return {k: 0.0 for k in vols}
    return {k: v / total for k, v in inv.items()}


def apply_per_sleeve_cap(weights, cap=PER_SLEEVE_CAP):
    capped = {k: min(v, cap) for k, v in weights.items()}
    total = sum(capped.values())
    if total <= 0:
        return {k: 0.0 for k in weights}
    shortfall = 1.0 - total
    uncapped = [k for k in weights if weights[k] < cap]
    if uncapped and shortfall > 0:
        bonus = shortfall / len(uncapped)
        for k in uncapped:
            capped[k] += bonus
    return {k: v for k, v in capped.items()}


def max_drawdown(equity):
    arr = np.asarray(equity, dtype=float)
    if len(arr) == 0:
        return 0.0
    peak = np.maximum.accumulate(arr)
    dd = arr / peak - 1.0
    return float(dd.min())


def select_vol_cap(pre2016_max_dd_by_target):
    for target in sorted(pre2016_max_dd_by_target, reverse=True):
        if VOL_TARGET_MIN <= target <= VOL_TARGET_MAX:
            if pre2016_max_dd_by_target[target] >= KILL_DRAWDOWN:
                return target
    return None
