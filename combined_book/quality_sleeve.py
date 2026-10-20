"""Quality/value sleeve: equal-weight blend of QUAL/VLUE/MTUM/USMV monthly returns."""
from __future__ import annotations

import pandas as pd

QUALITY_UNIVERSE = ("QUAL", "VLUE", "MTUM", "USMV")


def quality_monthly_returns(monthly_by_symbol):
    """Equal-weight average of the monthly return series for each quality ETF."""
    series = [
        s for sym, s in monthly_by_symbol.items()
        if sym in QUALITY_UNIVERSE and not s.empty
    ]
    if not series:
        return pd.Series(dtype=float)
    frame = pd.concat(series, axis=1).fillna(0.0)
    return frame.mean(axis=1)
