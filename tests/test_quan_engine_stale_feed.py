"""Tests for quan_engine.scanner._is_feed_stale.

Regression target: the MATIC->POL artifact (PR #371 + #374) where yfinance
returned a frozen feed at $0.3794 and the scanner emitted 760 bogus picks
over 28 days. Without these checks, any future symbol delisting or rebrand
would silently produce the same artifact.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from quan_engine.scanner import _is_feed_stale


def _make_df(prices: list[float], interval_hours: float = 1.0,
             end: datetime | None = None) -> pd.DataFrame:
    """Build an OHLCV df with timestamp index ending at `end`."""
    end = end or datetime.now(timezone.utc)
    n = len(prices)
    idx = [end - timedelta(hours=interval_hours * (n - 1 - i)) for i in range(n)]
    return pd.DataFrame(
        {
            "open": prices,
            "high": [p * 1.001 for p in prices],
            "low": [p * 0.999 for p in prices],
            "close": prices,
            "volume": [1.0] * n,
        },
        index=pd.DatetimeIndex(idx),
    )


class TestStaleByAge:
    def test_recent_bar_not_stale(self):
        # Last bar 30 min ago on 1h interval -> well within tolerance.
        now = datetime.now(timezone.utc)
        df = _make_df([100.0, 101.0, 102.0], interval_hours=1.0,
                      end=now - timedelta(minutes=30))
        stale, reason = _is_feed_stale(df, "1h", _now=now)
        assert not stale, reason

    def test_bar_older_than_24h_is_stale_on_1h(self):
        # Last bar 30h ago on 1h interval -> exceeds 24h tolerance.
        now = datetime.now(timezone.utc)
        df = _make_df([100.0, 101.0, 102.0], interval_hours=1.0,
                      end=now - timedelta(hours=30))
        stale, reason = _is_feed_stale(df, "1h", _now=now)
        assert stale
        assert "last-bar age" in reason

    def test_unknown_interval_falls_back_to_24h(self):
        # Unknown interval like "weekly" -> default 24h tolerance.
        now = datetime.now(timezone.utc)
        df = _make_df([100.0, 101.0, 102.0], interval_hours=1.0,
                      end=now - timedelta(hours=48))
        stale, _ = _is_feed_stale(df, "weekly", _now=now)
        assert stale

    def test_daily_interval_allows_week_long_gap(self):
        # 1d interval tolerates 7-day gap (covers weekends + holidays).
        now = datetime.now(timezone.utc)
        df = _make_df([100.0, 101.0, 102.0], interval_hours=24.0,
                      end=now - timedelta(hours=120))  # 5 days
        stale, _ = _is_feed_stale(df, "1d", _now=now)
        assert not stale


class TestFrozenTail:
    def test_frozen_5_bar_tail_is_stale(self):
        # MATIC->POL regression case: last 5 closes all 0.3794.
        now = datetime.now(timezone.utc)
        df = _make_df([0.40, 0.39, 0.3794, 0.3794, 0.3794, 0.3794, 0.3794],
                      interval_hours=1.0, end=now)
        stale, reason = _is_feed_stale(df, "1h", _now=now)
        assert stale
        assert "frozen feed" in reason
        assert "0.3794" in reason

    def test_normal_price_movement_not_stale(self):
        now = datetime.now(timezone.utc)
        df = _make_df([100.0, 100.5, 101.2, 100.8, 101.5, 102.0, 101.7],
                      interval_hours=1.0, end=now)
        stale, _ = _is_feed_stale(df, "1h", _now=now)
        assert not stale

    def test_4_identical_then_1_different_not_stale(self):
        # Exactly 4 frozen + 1 movement at the very end -> not stale.
        now = datetime.now(timezone.utc)
        df = _make_df([0.40, 0.3794, 0.3794, 0.3794, 0.3794, 0.3795],
                      interval_hours=1.0, end=now)
        stale, _ = _is_feed_stale(df, "1h", _now=now)
        assert not stale

    def test_short_df_skipped(self):
        # Fewer than 5 bars -> can't trigger frozen-tail check; not flagged.
        now = datetime.now(timezone.utc)
        df = _make_df([0.3794, 0.3794, 0.3794], interval_hours=1.0, end=now)
        stale, _ = _is_feed_stale(df, "1h", _now=now)
        assert not stale


class TestEdgeCases:
    def test_empty_df_not_stale(self):
        # Empty df handled by caller separately; this fn returns (False, "").
        df = pd.DataFrame()
        stale, reason = _is_feed_stale(df, "1h")
        assert not stale
        assert reason == ""

    def test_non_timestamp_index_age_check_skipped(self):
        # Index is integer range -> age check bails; only frozen-tail applies.
        df = pd.DataFrame(
            {"close": [100.0, 100.0, 100.0, 100.0, 100.0]},
            index=range(5),
        )
        stale, reason = _is_feed_stale(df, "1h")
        # Frozen-tail still triggers.
        assert stale
        assert "frozen feed" in reason

    def test_naive_timestamp_treated_as_utc(self):
        now = datetime.now()  # naive
        df = _make_df([100, 101, 102, 103, 104], interval_hours=1.0,
                      end=now - timedelta(hours=30))
        # Strip tzinfo to simulate naive index.
        df.index = pd.DatetimeIndex([t.replace(tzinfo=None) for t in df.index])
        stale, _ = _is_feed_stale(df, "1h", _now=now.replace(tzinfo=timezone.utc))
        assert stale
