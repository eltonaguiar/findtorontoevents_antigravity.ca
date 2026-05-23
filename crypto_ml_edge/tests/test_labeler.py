"""
Tests for Triple-Barrier Labeler (Phase 2 — LABL-01 through LABL-04)
======================================================================
Run: py -m pytest crypto_ml_edge/tests/test_labeler.py -v

Design philosophy:
  - Every test uses synthetic data with KNOWN outcomes so assertions are exact.
  - No randomness in price construction for the barrier tests; we place prices
    deterministically to guarantee which barrier is hit and when.
  - The lookahead test verifies the structural guarantee: the label for bar T
    is computed using only bars T+1 onward.
"""

import numpy as np
import pandas as pd
import pytest
from datetime import timezone

from crypto_ml_edge.labeler import (
    build_labels,
    apply_embargo,
    embargo_from_datetimes,
    label_distribution,
    label_dataframe,
)
from crypto_ml_edge.config import (
    TPSL_CONFIG,
    PURGE_GAP_BARS,
    get_total_cost,
)


# ─── Shared fixtures ──────────────────────────────────────────────────────────

def _make_flat_ohlcv(
    n: int,
    base_price: float = 100.0,
    start: str = "2024-01-01",
    freq: str = "1h",
) -> pd.DataFrame:
    """
    Flat OHLCV: every bar has close=open=high=low=base_price, volume=1000.
    ATR will be zero — useful for testing degenerate paths.
    """
    dates = pd.date_range(start, periods=n, freq=freq, tz="UTC")
    return pd.DataFrame(
        {
            "open":   base_price,
            "high":   base_price,
            "low":    base_price,
            "close":  base_price,
            "volume": 1000.0,
        },
        index=dates,
    )


def _make_atr(n: int, value: float, index: pd.Index) -> pd.Series:
    """Constant ATR series."""
    return pd.Series(value, index=index, name="atr")


def _make_ohlcv_with_tp_hit(
    entry_price: float = 100.0,
    atr: float = 2.0,
    tp_mult: float = 3.0,
    sl_mult: float = 2.0,
    tp_hit_bar: int = 3,   # bar index AFTER entry (1-based relative)
    n: int = 50,
    freq: str = "1h",
    start: str = "2024-01-01",
) -> tuple[pd.DataFrame, pd.Series]:
    """
    Build OHLCV where:
      - Bar 0 (entry): close = entry_price, flat bar
      - Bar tp_hit_bar: high exceeds TP level
      - All other bars: flat at entry_price (SL never touched)

    Returns (df, atr_series)
    """
    tp_level = entry_price + tp_mult * atr
    dates = pd.date_range(start, periods=n, freq=freq, tz="UTC")
    close  = np.full(n, entry_price)
    high   = np.full(n, entry_price)
    low    = np.full(n, entry_price)
    open_  = np.full(n, entry_price)
    volume = np.full(n, 1000.0)

    # The bar that hits TP: high must be >= tp_level
    high[tp_hit_bar] = tp_level + 0.01

    df = pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=dates,
    )
    atr_series = _make_atr(n, atr, dates)
    return df, atr_series


def _make_ohlcv_with_sl_hit(
    entry_price: float = 100.0,
    atr: float = 2.0,
    tp_mult: float = 3.0,
    sl_mult: float = 2.0,
    sl_hit_bar: int = 3,
    n: int = 50,
    freq: str = "1h",
    start: str = "2024-01-01",
) -> tuple[pd.DataFrame, pd.Series]:
    """
    Build OHLCV where:
      - Bar 0 (entry): flat at entry_price
      - Bar sl_hit_bar: low drops below SL level
      - All other bars: flat at entry_price (TP never touched)
    """
    sl_level = entry_price - sl_mult * atr
    dates = pd.date_range(start, periods=n, freq=freq, tz="UTC")
    close  = np.full(n, entry_price)
    high   = np.full(n, entry_price)
    low    = np.full(n, entry_price)
    open_  = np.full(n, entry_price)
    volume = np.full(n, 1000.0)

    low[sl_hit_bar] = sl_level - 0.01

    df = pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=dates,
    )
    atr_series = _make_atr(n, atr, dates)
    return df, atr_series


# ─── LABL-01: No lookahead bias ───────────────────────────────────────────────

class TestNoLookahead:
    """
    LABL-01: Labels use forward returns only (close[t+N]) with zero lookahead.

    Test strategy: build_labels internally uses only indices i+1 … i+horizon
    when evaluating barriers for bar i.  We verify this structurally by:

      a) Building labels on a price series where the entry bar's OHLC is all
         at a neutral value (no TP/SL touching bar T itself).  The label must
         be driven entirely by future bars.

      b) Verifying that mutating bar T's high/low (which should NOT be scanned)
         does not change the label.
    """

    def test_bar_T_high_low_not_scanned(self):
        """
        If we set bar T's high absurdly above TP, label should still be
        determined by future bars only (not bar T's high).
        """
        entry_price = 100.0
        atr_val = 2.0
        tf = "1h"
        cfg = TPSL_CONFIG[tf]
        tp_level = entry_price + cfg["tp_atr_mult"] * atr_val  # 106.0

        n = 30
        dates = pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC")
        close  = np.full(n, entry_price)
        high   = np.full(n, entry_price)
        low    = np.full(n, entry_price)
        volume = np.full(n, 1000.0)

        # Bar T (index 0): high way above TP — should NOT trigger a TP label
        # because the scan only looks at bars i+1 onward.
        high[0] = tp_level + 1000.0

        df = pd.DataFrame(
            {"open": close.copy(), "high": high, "low": low,
             "close": close, "volume": volume},
            index=dates,
        )
        atr_s = _make_atr(n, atr_val, dates)
        labels = build_labels(df["close"], df["high"], df["low"], atr_s, tf)

        # All future bars are flat (no TP/SL touch) → label 0 (timeout)
        assert labels.iloc[0] == 0, (
            "Label for bar 0 should be 0 (timeout) — bar T high must not be scanned"
        )

    def test_label_index_aligns_with_input(self):
        """Output label series must be aligned to the input index."""
        df, atr_s = _make_ohlcv_with_tp_hit(tp_hit_bar=5)
        labels = build_labels(df["close"], df["high"], df["low"], atr_s, "1h")

        assert list(labels.index) == list(df.index), (
            "Label index must match input DataFrame index exactly"
        )

    def test_label_dtype_is_int8(self):
        """Labels should be int8 to save memory."""
        df, atr_s = _make_ohlcv_with_tp_hit()
        labels = build_labels(df["close"], df["high"], df["low"], atr_s, "1h")
        assert labels.dtype == np.int8

    def test_last_bars_are_zero(self):
        """
        The last max_hold_bars rows have no full forward window available.
        They must be 0 (not labelled as +1 or -1 based on partial future data).
        """
        tf = "1h"
        max_hold = TPSL_CONFIG[tf]["max_hold_bars"]
        n = max_hold + 10
        df, atr_s = _make_ohlcv_with_tp_hit(n=n, tp_hit_bar=2)
        labels = build_labels(df["close"], df["high"], df["low"], atr_s, tf)

        # The very last bar should be 0 (loop doesn't process i = n-1)
        assert labels.iloc[-1] == 0, "Last bar must be 0 — no forward window exists"

    def test_no_future_close_used_in_barrier_check(self):
        """
        Structural check: if we replace all future closes with a different
        value but keep highs/lows the same, labels should be identical.
        This confirms the barrier scan uses high/low (not close) for future
        bars, and uses close[T] only as the entry price.
        """
        df, atr_s = _make_ohlcv_with_tp_hit(tp_hit_bar=4)
        # Poison future closes — if labeler uses them for barrier check it would
        # change behaviour; but barriers are checked via high and low.
        df2 = df.copy()
        df2.loc[df2.index[1:], "close"] = 999_999.0   # absurd value

        labels_orig = build_labels(df["close"],  df["high"],  df["low"],  atr_s, "1h")
        labels_mod  = build_labels(df2["close"], df2["high"], df2["low"], atr_s, "1h")

        # Only bar 0's close is used as entry price — the poisoned future closes
        # should not affect the label at bar 0.
        assert labels_orig.iloc[0] == labels_mod.iloc[0], (
            "Label must not change when future closes are poisoned — "
            "only HIGH/LOW should be scanned for barrier checks"
        )


# ─── LABL-02: Triple-barrier correctness ─────────────────────────────────────

class TestTripleBarrierLabeling:
    """LABL-02: +1 = TP hit first, -1 = SL hit first, 0 = timeout."""

    def test_tp_hit_produces_label_plus_one(self):
        """When high crosses TP level before SL — label +1."""
        df, atr_s = _make_ohlcv_with_tp_hit(
            entry_price=100.0, atr=2.0, tp_mult=3.0, sl_mult=2.0,
            tp_hit_bar=5,
        )
        labels = build_labels(df["close"], df["high"], df["low"], atr_s, "1h")
        assert labels.iloc[0] == 1, f"Expected +1, got {labels.iloc[0]}"

    def test_sl_hit_produces_label_zero(self):
        """When low crosses SL level before TP — label 0 (binary long-only: no-trade)."""
        df, atr_s = _make_ohlcv_with_sl_hit(
            entry_price=100.0, atr=2.0, tp_mult=3.0, sl_mult=2.0,
            sl_hit_bar=4,
        )
        labels = build_labels(df["close"], df["high"], df["low"], atr_s, "1h")
        assert labels.iloc[0] == 0, f"Expected 0 (SL = no-trade), got {labels.iloc[0]}"

    def test_timeout_produces_label_zero(self):
        """When neither barrier is hit within max_hold_bars — label 0."""
        n = 50
        tf = "1h"
        entry_price = 100.0
        atr_val = 2.0
        # Both high and low stay within barriers for all bars
        df = _make_flat_ohlcv(n, base_price=entry_price)
        atr_s = _make_atr(n, atr_val, df.index)
        labels = build_labels(df["close"], df["high"], df["low"], atr_s, tf)
        assert labels.iloc[0] == 0, f"Expected 0 (timeout), got {labels.iloc[0]}"

    def test_tp_before_sl_wins(self):
        """If TP is hit before SL (even if SL is also hit later) — label +1."""
        entry_price = 100.0
        atr_val = 2.0
        tf = "1h"
        cfg = TPSL_CONFIG[tf]
        tp_level = entry_price + cfg["tp_atr_mult"] * atr_val   # 106.0
        sl_level = entry_price - cfg["sl_atr_mult"] * atr_val   # 96.0

        n = 30
        dates = pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC")
        close  = np.full(n, entry_price)
        high   = np.full(n, entry_price)
        low    = np.full(n, entry_price)
        volume = np.full(n, 1000.0)

        high[3] = tp_level + 0.01   # TP hit at bar 3
        low[7]  = sl_level - 0.01   # SL hit at bar 7 (later)

        df = pd.DataFrame(
            {"open": close.copy(), "high": high, "low": low,
             "close": close, "volume": volume},
            index=dates,
        )
        atr_s = _make_atr(n, atr_val, dates)
        labels = build_labels(df["close"], df["high"], df["low"], atr_s, tf)

        assert labels.iloc[0] == 1, (
            f"Expected +1 (TP hit first at bar 3 vs SL at bar 7), got {labels.iloc[0]}"
        )

    def test_sl_before_tp_wins(self):
        """If SL is hit before TP — label 0 (binary long-only)."""
        entry_price = 100.0
        atr_val = 2.0
        tf = "1h"
        cfg = TPSL_CONFIG[tf]
        tp_level = entry_price + cfg["tp_atr_mult"] * atr_val
        sl_level = entry_price - cfg["sl_atr_mult"] * atr_val

        n = 30
        dates = pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC")
        close  = np.full(n, entry_price)
        high   = np.full(n, entry_price)
        low    = np.full(n, entry_price)
        volume = np.full(n, 1000.0)

        low[2]  = sl_level - 0.01   # SL hit at bar 2
        high[8] = tp_level + 0.01   # TP hit at bar 8 (later)

        df = pd.DataFrame(
            {"open": close.copy(), "high": high, "low": low,
             "close": close, "volume": volume},
            index=dates,
        )
        atr_s = _make_atr(n, atr_val, dates)
        labels = build_labels(df["close"], df["high"], df["low"], atr_s, tf)

        assert labels.iloc[0] == 0, (
            f"Expected 0 (SL hit first at bar 2 vs TP at bar 8 — binary: no-trade), got {labels.iloc[0]}"
        )

    def test_same_bar_tp_and_sl_hit_tp_wins(self):
        """
        When TP and SL are both touched on the same bar (wide-range candle),
        the barrier that was hit first within that bar is ambiguous from OHLCV.
        Convention: if TP and SL are tied on the same bar, TP wins (+1).
        This is the optimistic (realistic for a long trade) assumption.
        """
        entry_price = 100.0
        atr_val = 2.0
        tf = "1h"
        cfg = TPSL_CONFIG[tf]
        tp_level = entry_price + cfg["tp_atr_mult"] * atr_val
        sl_level = entry_price - cfg["sl_atr_mult"] * atr_val

        n = 20
        dates = pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC")
        close  = np.full(n, entry_price)
        high   = np.full(n, entry_price)
        low    = np.full(n, entry_price)
        volume = np.full(n, 1000.0)

        # Bar 1: both TP and SL touched simultaneously
        high[1] = tp_level + 0.01
        low[1]  = sl_level - 0.01

        df = pd.DataFrame(
            {"open": close.copy(), "high": high, "low": low,
             "close": close, "volume": volume},
            index=dates,
        )
        atr_s = _make_atr(n, atr_val, dates)
        labels = build_labels(df["close"], df["high"], df["low"], atr_s, tf)

        # When tp_bar == sl_bar, condition is tp_bar <= sl_bar → +1
        assert labels.iloc[0] == 1, (
            f"Expected +1 when TP and SL hit on same bar (tp <= sl), got {labels.iloc[0]}"
        )

    def test_all_labels_in_valid_set(self):
        """Every label must be one of {0, 1} (binary long-only)."""
        import random
        random.seed(0)
        n = 200
        np.random.seed(0)
        close = 100 + np.cumsum(np.random.randn(n) * 0.5)
        high  = close + np.abs(np.random.randn(n) * 0.3)
        low   = close - np.abs(np.random.randn(n) * 0.3)
        dates = pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC")
        df = pd.DataFrame(
            {"open": close, "high": high, "low": low, "close": close, "volume": 1000.0},
            index=dates,
        )
        atr_s = _make_atr(n, 1.5, dates)
        labels = build_labels(df["close"], df["high"], df["low"], atr_s, "1h")

        invalid = labels[~labels.isin([0, 1])]
        assert len(invalid) == 0, f"Found invalid labels: {invalid.unique()}"

    def test_4h_config_used_correctly(self):
        """4h timeframe uses its own tp/sl multiples from TPSL_CONFIG."""
        tf = "4h"
        cfg = TPSL_CONFIG[tf]
        entry_price = 100.0
        atr_val = 3.0
        tp_level = entry_price + cfg["tp_atr_mult"] * atr_val  # 4.0 * 3 = 112.0

        n = 40
        dates = pd.date_range("2024-01-01", periods=n, freq="4h", tz="UTC")
        close  = np.full(n, entry_price)
        high   = np.full(n, entry_price)
        low    = np.full(n, entry_price)
        volume = np.full(n, 1000.0)

        high[5] = tp_level + 0.01   # TP hit according to 4h config

        df = pd.DataFrame(
            {"open": close.copy(), "high": high, "low": low,
             "close": close, "volume": volume},
            index=dates,
        )
        atr_s = _make_atr(n, atr_val, dates)
        labels = build_labels(df["close"], df["high"], df["low"], atr_s, tf)

        assert labels.iloc[0] == 1

    def test_max_hold_bars_respected(self):
        """
        A TP touch beyond max_hold_bars should NOT trigger a +1 label for
        bar 0.  Only touches within [bar1 … bar_max_hold] are valid.
        """
        tf = "1h"
        cfg = TPSL_CONFIG[tf]
        max_hold = cfg["max_hold_bars"]   # 24
        entry_price = 100.0
        atr_val = 2.0
        tp_level = entry_price + cfg["tp_atr_mult"] * atr_val

        n = max_hold + 15
        dates = pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC")
        close  = np.full(n, entry_price)
        high   = np.full(n, entry_price)
        low    = np.full(n, entry_price)
        volume = np.full(n, 1000.0)

        # TP hit at bar max_hold + 5 — beyond the horizon
        beyond_bar = max_hold + 5
        high[beyond_bar] = tp_level + 0.01

        df = pd.DataFrame(
            {"open": close.copy(), "high": high, "low": low,
             "close": close, "volume": volume},
            index=dates,
        )
        atr_s = _make_atr(n, atr_val, dates)
        labels = build_labels(df["close"], df["high"], df["low"], atr_s, tf)

        # Bar 0 should be 0 (timeout) because TP is outside horizon
        assert labels.iloc[0] == 0, (
            f"Expected 0 — TP at bar {beyond_bar} is beyond max_hold={max_hold}"
        )


# ─── LABL-03: Cost-based threshold ───────────────────────────────────────────

class TestCostBasedThreshold:
    """
    LABL-03: Label threshold is the minimum profitable trade after round-trip
    fees and slippage.  Labels are NOT adjusted for class balance.
    """

    def test_tp_below_cost_threshold_is_zero(self):
        """
        If ATR is tiny so that tp_level - entry_price < cost threshold,
        the label must be 0 even when high touches tp_level.

        We force this by using an ATR so small that tp_atr_mult * ATR
        is less than the minimum_profitable_move * entry_price.
        """
        pair = "BTCUSDT"
        min_cost = get_total_cost(pair)   # e.g. 0.003
        tf = "1h"
        cfg = TPSL_CONFIG[tf]
        entry_price = 100.0

        # ATR so small that gross move < cost threshold
        # gross_move = tp_mult * atr  <  entry_price * min_cost
        # atr < entry_price * min_cost / tp_mult
        tiny_atr = (entry_price * min_cost / cfg["tp_atr_mult"]) * 0.5  # half of threshold

        tp_level = entry_price + cfg["tp_atr_mult"] * tiny_atr

        n = 30
        dates = pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC")
        close  = np.full(n, entry_price)
        high   = np.full(n, entry_price)
        low    = np.full(n, entry_price)
        volume = np.full(n, 1000.0)

        high[3] = tp_level + 0.01  # TP touched but too small to clear costs

        df = pd.DataFrame(
            {"open": close.copy(), "high": high, "low": low,
             "close": close, "volume": volume},
            index=dates,
        )
        atr_s = _make_atr(n, tiny_atr, dates)
        labels = build_labels(df["close"], df["high"], df["low"], atr_s, tf, pair=pair)

        assert labels.iloc[0] == 0, (
            f"Expected 0: TP touched but gross_move={cfg['tp_atr_mult']*tiny_atr:.5f} "
            f"< cost_threshold={entry_price * min_cost:.5f}.  Got {labels.iloc[0]}"
        )

    def test_tp_above_cost_threshold_is_plus_one(self):
        """Normal ATR produces a TP move well above the cost threshold → +1."""
        pair = "BTCUSDT"
        min_cost = get_total_cost(pair)
        tf = "1h"
        cfg = TPSL_CONFIG[tf]
        entry_price = 100.0

        # ATR generous enough to ensure tp move >> costs
        # gross_move = tp_mult * atr > entry_price * min_cost * 5
        generous_atr = (entry_price * min_cost / cfg["tp_atr_mult"]) * 10
        tp_level = entry_price + cfg["tp_atr_mult"] * generous_atr

        n = 30
        dates = pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC")
        close  = np.full(n, entry_price)
        high   = np.full(n, entry_price)
        low    = np.full(n, entry_price)
        volume = np.full(n, 1000.0)

        high[4] = tp_level + 0.01

        df = pd.DataFrame(
            {"open": close.copy(), "high": high, "low": low,
             "close": close, "volume": volume},
            index=dates,
        )
        atr_s = _make_atr(n, generous_atr, dates)
        labels = build_labels(df["close"], df["high"], df["low"], atr_s, tf, pair=pair)

        assert labels.iloc[0] == 1

    def test_cost_threshold_differs_per_pair(self):
        """
        Lower-liquidity pairs have higher costs → higher minimum move required
        → same tiny ATR that produces +1 on BTC should produce 0 on a smaller pair.
        """
        tf = "1h"
        cfg = TPSL_CONFIG[tf]
        entry_price = 100.0

        # Find an ATR that clears BTC costs but not INJUSDT costs
        btc_cost  = get_total_cost("BTCUSDT")
        inj_cost  = get_total_cost("INJUSDT")
        assert inj_cost > btc_cost, "INJUSDT should be more expensive than BTCUSDT"

        # ATR that gives gross_move just above BTC cost but below INJ cost
        # gross_move = tp_mult * atr
        # We want: entry * btc_cost < gross_move < entry * inj_cost
        mid_cost = (btc_cost + inj_cost) / 2
        mid_atr  = (entry_price * mid_cost / cfg["tp_atr_mult"])

        tp_level = entry_price + cfg["tp_atr_mult"] * mid_atr

        n = 30
        dates = pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC")
        close  = np.full(n, entry_price)
        high   = np.full(n, entry_price)
        low    = np.full(n, entry_price)
        volume = np.full(n, 1000.0)
        high[3] = tp_level + 0.01

        df = pd.DataFrame(
            {"open": close.copy(), "high": high, "low": low,
             "close": close, "volume": volume},
            index=dates,
        )
        atr_s = _make_atr(n, mid_atr, dates)

        label_btc = build_labels(df["close"], df["high"], df["low"], atr_s, tf, pair="BTCUSDT")
        label_inj = build_labels(df["close"], df["high"], df["low"], atr_s, tf, pair="INJUSDT")

        assert label_btc.iloc[0] == 1,  "BTC: should clear lower cost bar"
        assert label_inj.iloc[0] == 0,  "INJ: should NOT clear higher cost bar"

    def test_nan_atr_produces_zero_label(self):
        """ATR=NaN (warmup period) must yield label 0, not an exception."""
        n = 30
        df = _make_flat_ohlcv(n)
        atr_s = _make_atr(n, np.nan, df.index)   # All NaN
        labels = build_labels(df["close"], df["high"], df["low"], atr_s, "1h")

        assert (labels == 0).all(), "All-NaN ATR should produce all-zero labels"

    def test_class_distribution_is_not_forced_to_balance(self):
        """
        Label distribution may be skewed.  The labeler must not re-weight
        or resample to achieve balance — that is the model layer's job.
        Verify by checking that a sideways market produces mostly-timeout (0).
        """
        n = 100
        df = _make_flat_ohlcv(n, base_price=100.0)
        # Small ATR so barriers are tight and no flat bar touches them
        atr_s = _make_atr(n, 0.001, df.index)
        labels = build_labels(df["close"], df["high"], df["low"], atr_s, "1h")

        dist = label_distribution(labels)
        # Flat data with tiny ATR → all timeout
        assert dist["pct_timeout"] > 50, (
            "Sideways market should produce mostly timeouts; "
            f"got {dist['pct_timeout']}% timeout"
        )


# ─── LABL-04: Embargo ─────────────────────────────────────────────────────────

class TestEmbargo:
    """LABL-04: Embargo period masks labels near train/test boundary."""

    def _make_labels(self, n: int = 100) -> Labels:
        """Build a label series of known values for embargo testing."""
        dates = pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC")
        # Alternating 1/-1/0 for easy visual checking
        vals = np.array([1, -1, 0] * (n // 3 + 1), dtype="int8")[:n]
        return pd.Series(vals, index=dates, dtype="int8", name="label")

    def test_embargo_sets_boundary_region_to_nan(self):
        """
        Bars within the embargo window must become NaN.
        """
        n = 100
        test_start = 70          # Test set begins at iloc 70
        horizon = 10
        purge = 5

        labels = self._make_labels(n)
        embargoed = apply_embargo(labels, test_start, horizon, purge)

        # Region: [70-10, 70+5) = [60, 75) should be NaN
        embargo_start = max(0, test_start - horizon)          # 60
        embargo_end   = min(n, test_start + purge)            # 75

        assert embargoed.iloc[embargo_start:embargo_end].isna().all(), (
            f"Bars {embargo_start}–{embargo_end-1} must be NaN (embargoed)"
        )

    def test_non_embargoed_bars_preserve_values(self):
        """
        Bars outside the embargo region must retain their original labels.
        """
        n = 100
        test_start = 70
        horizon = 10
        purge = 5

        labels = self._make_labels(n)
        embargoed = apply_embargo(labels, test_start, horizon, purge)

        embargo_start = max(0, test_start - horizon)  # 60
        embargo_end   = min(n, test_start + purge)    # 75

        # Before embargo region
        before = embargoed.iloc[:embargo_start]
        assert not before.isna().any(), "Pre-embargo bars must not be NaN"
        pd.testing.assert_series_equal(
            before.astype("int8"), labels.iloc[:embargo_start], check_names=False
        )

        # After embargo region
        after = embargoed.iloc[embargo_end:]
        assert not after.isna().any(), "Post-embargo bars must not be NaN"
        pd.testing.assert_series_equal(
            after.astype("int8"), labels.iloc[embargo_end:], check_names=False
        )

    def test_embargo_correct_bar_count(self):
        """
        Number of embargoed bars = horizon + purge (or less near boundaries).
        """
        n = 200
        test_start = 100
        horizon = 15
        purge = PURGE_GAP_BARS  # 20

        labels = self._make_labels(n)
        embargoed = apply_embargo(labels, test_start, horizon, purge)

        n_nan = embargoed.isna().sum()
        expected = (test_start + purge) - (test_start - horizon)  # horizon + purge
        assert n_nan == expected, (
            f"Expected {expected} NaN bars, got {n_nan}"
        )

    def test_embargo_from_datetimes_matches_iloc(self):
        """
        embargo_from_datetimes must produce the same result as apply_embargo
        when train_end and test_start align to the same integer positions.
        """
        n = 100
        horizon = 10
        purge = PURGE_GAP_BARS
        labels = self._make_labels(n)

        test_start_iloc = 70
        test_start_ts   = labels.index[test_start_iloc]

        # Use iloc-based API
        by_iloc = apply_embargo(labels, test_start_iloc, horizon, purge)
        # Use datetime API
        train_end_ts = labels.index[test_start_iloc - 1]
        by_dt = embargo_from_datetimes(labels, train_end_ts, test_start_ts, horizon, purge)

        pd.testing.assert_series_equal(by_iloc, by_dt, check_names=False)

    def test_embargo_at_start_boundary(self):
        """Embargo starting at iloc 0 should not raise an error."""
        n = 50
        labels = self._make_labels(n)
        # test_start very close to beginning
        embargoed = apply_embargo(labels, test_start_iloc=3, horizon_bars=10, purge_gap=5)
        # Just verify it doesn't crash and returns right length
        assert len(embargoed) == n

    def test_embargo_at_end_boundary(self):
        """Embargo reaching past end of series should clip gracefully."""
        n = 50
        labels = self._make_labels(n)
        # test_start near end so embargo_end > n
        embargoed = apply_embargo(labels, test_start_iloc=45, horizon_bars=10, purge_gap=20)
        assert len(embargoed) == n

    def test_embargoed_bars_excluded_from_split(self):
        """
        After embargo, the NaN rows can be identified and dropped for training.
        This is a workflow integration test: verify we can cleanly split
        train / embargo / test without any cross-contamination.
        """
        n = 120
        horizon = 12
        purge = 5
        test_start = 80

        labels = self._make_labels(n)
        embargoed = apply_embargo(labels, test_start, horizon, purge)

        train = embargoed.iloc[:test_start].dropna()
        test  = embargoed.iloc[test_start:]

        # Train set must end before embargo region starts
        embargo_start = test_start - horizon  # 68
        assert train.index[-1] == labels.index[embargo_start - 1], (
            "After dropping NaN, last train bar must be just before embargo region"
        )

        # Test set must contain no NaN (embargo is on training side only,
        # plus purge_gap which is excluded from the test set in walk-forward CV)
        test_no_purge = test.iloc[purge:]
        assert not test_no_purge.isna().any(), (
            "Test set (beyond purge gap) must contain no embargoed labels"
        )


# ─── label_dataframe helper ───────────────────────────────────────────────────

class TestLabelDataframe:
    def test_adds_label_column(self):
        df, atr_s = _make_ohlcv_with_tp_hit()
        result = label_dataframe(df, atr_s, "1h")
        assert "label" in result.columns

    def test_does_not_mutate_input(self):
        df, atr_s = _make_ohlcv_with_tp_hit()
        original_cols = list(df.columns)
        _ = label_dataframe(df, atr_s, "1h")
        assert list(df.columns) == original_cols, "Input DataFrame must not be mutated"

    def test_missing_column_raises(self):
        df, atr_s = _make_ohlcv_with_tp_hit()
        bad_df = df.drop(columns=["high"])
        with pytest.raises(ValueError, match="missing columns"):
            label_dataframe(bad_df, atr_s, "1h")

    def test_invalid_timeframe_raises(self):
        df, atr_s = _make_ohlcv_with_tp_hit()
        with pytest.raises(ValueError, match="not in TPSL_CONFIG"):
            label_dataframe(df, atr_s, "15m")


# ─── label_distribution diagnostics ─────────────────────────────────────────

class TestLabelDistribution:
    def test_returns_all_keys(self):
        labels = pd.Series([1, 0, 0, 1, 0, 0], dtype="int8")
        dist = label_distribution(labels)
        for key in ["n_total", "n_valid", "n_long", "n_short", "n_timeout",
                    "pct_long", "pct_short", "pct_timeout"]:
            assert key in dist

    def test_counts_match(self):
        labels = pd.Series([1, 1, 0, 0, 0, 0], dtype="int8")
        dist = label_distribution(labels)
        assert dist["n_long"]    == 2
        assert dist["n_short"]   == 0   # binary long-only: no shorts
        assert dist["n_timeout"] == 4
        assert dist["n_total"]   == 6

    def test_nan_excluded_from_valid(self):
        labels = pd.Series([1.0, np.nan, 0.0, np.nan, 0.0])
        dist = label_distribution(labels)
        assert dist["n_valid"] == 3
        assert dist["n_total"] == 5
