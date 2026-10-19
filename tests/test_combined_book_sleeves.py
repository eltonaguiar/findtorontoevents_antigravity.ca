"""Tests for trend / quality / put sleeves."""
import pandas as pd

from combined_book import put_sleeve, quality_sleeve, trend_sleeve


def _daily_series(dates, prices):
    s = pd.Series(prices, index=pd.to_datetime(dates))
    s.index.name = "date"
    return s


def _monthly_series(months, vals):
    return pd.Series(vals, index=pd.to_datetime([f"{m}-01" for m in months]))


_MONTH_ENDS = pd.date_range("2025-01-31", periods=13, freq="ME")


# --- trend ---

def test_blend_trend_score_uses_lookbacks():
    # 12 months of data ending at price 110, 1m ago 100 -> score > 0
    closes = _daily_series(
        ["2025-10-01", "2025-11-01", "2025-12-01", "2026-01-01",
         "2026-02-01", "2026-03-01", "2026-04-01", "2026-05-01",
         "2026-06-01", "2026-07-01", "2026-08-01", "2026-09-01",
         "2026-10-01"],
        [100.0] * 12 + [110.0],
    )
    score = trend_sleeve.blend_trend_score(closes)
    assert score is not None
    assert score > 0.0


def test_blend_trend_score_short_history_returns_none():
    closes = _daily_series(["2026-10-01", "2026-10-02"], [100.0, 101.0])
    assert trend_sleeve.blend_trend_score(closes) is None


def test_trend_target_weights_sum_to_cap_fraction():
    closes = {
        "SPY": _daily_series(_MONTH_ENDS, [100 + i for i in range(13)]),
        "TLT": _daily_series(_MONTH_ENDS, [100 - i for i in range(13)]),
    }
    w = trend_sleeve.trend_target_weights(closes, vol_target=0.10, cap_fraction=0.35)
    assert abs(sum(w.values()) - 0.35) < 1e-9
    assert set(w.keys()) == {"SPY", "TLT"}


# --- quality ---

def test_quality_monthly_returns_is_equal_weight_blend():
    months = ["2026-01", "2026-02", "2026-03"]
    q = _monthly_series(months, [0.01, 0.02, -0.01])
    v = _monthly_series(months, [0.03, 0.01, 0.00])
    m = _monthly_series(months, [0.02, -0.01, 0.01])
    u = _monthly_series(months, [0.00, 0.00, 0.02])
    monthly = {"QUAL": q, "VLUE": v, "MTUM": m, "USMV": u}
    r = quality_sleeve.quality_monthly_returns(monthly)
    # mean of the four per month
    assert abs(r["2026-01-01"] - (0.01 + 0.03 + 0.02 + 0.00) / 4) < 1e-9
    assert abs(r["2026-02-01"] - (0.02 + 0.01 - 0.01 + 0.00) / 4) < 1e-9


# --- put ---

def test_put_monthly_returns_prefers_index():
    months = ["2026-01", "2026-02"]
    idx = _monthly_series(months, [0.01, 0.00])
    proxy = _monthly_series(months, [0.05, 0.05])
    monthly = {"PUT": idx, "XYLD": proxy}
    r = put_sleeve.put_monthly_returns(monthly, use_index=True)
    assert abs(r["2026-01-01"] - 0.01) < 1e-9


def test_put_monthly_returns_uses_proxy_when_requested():
    months = ["2026-01", "2026-02"]
    idx = _monthly_series(months, [0.01, 0.00])
    proxy = _monthly_series(months, [0.05, 0.05])
    monthly = {"PUT": idx, "XYLD": proxy}
    r = put_sleeve.put_monthly_returns(monthly, use_index=False)
    assert abs(r["2026-01-01"] - 0.05) < 1e-9
