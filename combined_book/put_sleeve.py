"""Put-write sleeve: XYLD tradeable proxy; CBOE PUT index for backtest series."""
from __future__ import annotations

import pandas as pd

PUT_PROXY = "XYLD"
PUT_INDEX = "PUT"


def put_monthly_returns(monthly_by_symbol, use_index=True):
    key = PUT_INDEX if use_index else PUT_PROXY
    if key not in monthly_by_symbol:
        return pd.Series(dtype=float)
    return monthly_by_symbol[key]
