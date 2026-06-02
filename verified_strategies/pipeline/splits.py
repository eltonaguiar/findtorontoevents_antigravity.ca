"""Purged + embargoed walk-forward fold generator (EAGLE2 §3.2)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Tuple

import pandas as pd


@dataclass
class WalkForwardSpec:
    train_bars: int
    test_bars: int
    purge_bars: int = 0
    embargo_bars: int = 0
    step_bars: int | None = None


def generate_purged_embargo_folds(
    df: pd.DataFrame,
    spec: WalkForwardSpec,
) -> Iterator[Tuple[pd.DataFrame, pd.DataFrame]]:
    """Yield (train, test) slices with purge gap before test and embargo after train end."""
    n = len(df)
    step = spec.step_bars or spec.test_bars

    for test_start in range(spec.train_bars, n - spec.test_bars + 1, step):
        train_end = test_start - spec.purge_bars
        embargo_end = test_start + spec.embargo_bars

        if train_end <= 0:
            continue

        train = df.iloc[:train_end]
        test = df.iloc[embargo_end : embargo_end + spec.test_bars]

        if len(test) < spec.test_bars:
            break

        yield train, test
