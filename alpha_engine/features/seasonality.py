"""
Feature Family 11: Seasonality / Calendar

Day-of-week, month effects, earnings weeks, turn-of-month, holiday effects.
These are well-documented anomalies with varying persistence.
"""
import numpy as np
import pandas as pd


def compute_seasonality_features(close: pd.DataFrame) -> pd.DataFrame:
    """
    Compute calendar and seasonality features.
    
    Features (stacked):
    - Day of week
    - Month of year
    - Turn of month (last 3 + first 3 trading days)
    - January effect flag
    - Quarter-end effect
    - Pre-holiday effect
    - Sell in May flag
    - Monthly seasonal return (historical average for this month)
    """
    features = {}
    dates = close.index

    # ── Day of Week ───────────────────────────────────────────────────────
    # Monday effect: historically weaker returns on Mondays
    dow = dates.dayofweek  # 0=Monday, 4=Friday
    for d in range(5):
        flag = (dow == d).astype(float)
        for ticker in close.columns:
            pass  # We'll broadcast below

    # Create as wide then stack
    dow_wide = pd.DataFrame(index=dates, columns=close.columns, dtype=float)
    for ticker in close.columns:
        dow_wide[ticker] = dow
    features["day_of_week"] = dow_wide.stack()

    # Monday flag (historically negative)
    monday = pd.DataFrame((dow == 0).astype(float).values[:, np.newaxis],
                           index=dates, columns=close.columns)
    features["is_monday"] = monday.stack().astype(float)

    # Friday flag (historically positive)
    friday = pd.DataFrame((dow == 4).astype(float).values[:, np.newaxis],
                           index=dates, columns=close.columns)
    features["is_friday"] = friday.stack().astype(float)

    # ── Month of Year ─────────────────────────────────────────────────────
    month = dates.month
    month_wide = pd.DataFrame(month.values[:, np.newaxis] * np.ones(len(close.columns)),
                               index=dates, columns=close.columns)
    features["month"] = month_wide.stack()

    # ── January Effect ────────────────────────────────────────────────────
    jan = pd.DataFrame((month == 1).astype(float).values[:, np.newaxis],
                        index=dates, columns=close.columns)
    features["january_effect"] = jan.stack().astype(float)

    # ── Sell in May (May-October historically weaker) ─────────────────────
    sell_may = pd.DataFrame(((month >= 5) & (month <= 10)).astype(float).values[:, np.newaxis],
                             index=dates, columns=close.columns)
    features["sell_in_may"] = sell_may.stack().astype(float)

    # ── Turn of Month (last 3 + first 3 trading days) ────────────────────
    day = dates.day
    days_in_month = dates.to_series().dt.days_in_month
    is_month_end_area = (day >= (days_in_month - 3).values).astype(float)
    is_month_start_area = (day <= 3).astype(float)
    tom = is_month_end_area + is_month_start_area
    tom_wide = pd.DataFrame(tom.values[:, np.newaxis],
                             index=dates, columns=close.columns)
    features["turn_of_month"] = tom_wide.stack().astype(float)

    # ── Quarter End Effect ────────────────────────────────────────────────
    is_quarter_end_month = np.isin(month, [3, 6, 9, 12])
    is_last_week = day >= (days_in_month - 7).values
    quarter_end = (is_quarter_end_month & is_last_week).astype(float)
    qe_wide = pd.DataFrame(quarter_end.values[:, np.newaxis],
                            index=dates, columns=close.columns)
    features["quarter_end"] = qe_wide.stack().astype(float)

    # ── Historical Monthly Return (seasonal pattern) ──────────────────────
    # Average return for this calendar month historically
    returns = close.pct_change()
    monthly_avg = {}
    for m in range(1, 13):
        mask = month == m
        if mask.any():
            monthly_avg[m] = returns[mask].mean()
        else:
            monthly_avg[m] = pd.Series(0.0, index=close.columns)

    seasonal_return = pd.DataFrame(index=dates, columns=close.columns, dtype=float)
    for m in range(1, 13):
        mask = month == m
        if mask.any():
            seasonal_return.loc[mask] = monthly_avg[m].values
    features["seasonal_return"] = seasonal_return.stack()

    # ── Days to Next Month End ────────────────────────────────────────────
    days_to_month_end = days_in_month.values - day
    dtme_wide = pd.DataFrame(days_to_month_end[:, np.newaxis] * np.ones(len(close.columns)),
                              index=dates, columns=close.columns)
    features["days_to_month_end"] = dtme_wide.stack()

    result = pd.DataFrame(features)
    result.index.names = ["date", "ticker"]
    return result
