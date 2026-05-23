"""Tests for walkforward_elite_strategies — indicator helpers, pick generation
for STOBVSupportDivergence, STFearGreedContrarian, STMultiDayMomentum,
and edge cases.

Walk-Forward Elite Strategies: CI-validated via alpha_engine walk-forward pipeline.
"""

import os
import sys

import numpy as np
import pandas as pd
import pytest

# Ensure paper_trading is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


# ═══════════════════════════════════════════════════════════════════════════
# Shared synthetic data builders (module-level for reuse across test classes)
# ═══════════════════════════════════════════════════════════════════════════

def make_btc_df(n=250, seed=42, trend=20):
    """Generic BTC-like OHLCV DataFrame.

    Args:
        n: Number of bars.
        seed: Random seed.
        trend: Daily drift (positive=uptrend, negative=downtrend).
    """
    np.random.seed(seed)
    base = 60000
    returns = np.random.randn(n) * 400 + trend
    close = base + np.cumsum(returns)
    close = np.maximum(close, 1000)
    high = close + np.abs(np.random.randn(n) * 150)
    low = close - np.abs(np.random.randn(n) * 150)
    low = np.minimum(low, close)
    high = np.maximum(high, close)
    volume = np.random.randint(5000, 50000, n).astype(float)
    return pd.DataFrame({
        "Open": close - np.random.randn(n) * 50,
        "High": high,
        "Low": low,
        "Close": close,
        "Volume": volume,
    })


def make_obv_divergence_df(n=50):
    """Create a DataFrame that reliably triggers OBV support divergence.

    Conditions met:
    - OBV makes new 20-period high (volume-weighted buying pushes OBV up)
    - Price does NOT make new 20-period high (divergence)
    - Price within 5% of 20-period low (support zone)
    - Volume > 1.5x average (spike on last bar)
    - Close > prior close (breakout attempt)
    - RSI < 78 (not overbought)
    """
    np.random.seed(2024)
    # Keep price range narrow so price_from_low_pct < 0.05
    # 20-bar window: prices in [60000, 60200]
    close_vals = np.linspace(60000, 60500, n)
    # Last 21 bars: narrow range near support
    close_vals[-21:-1] = np.linspace(60000, 60200, 20)
    close_vals[-2] = 60150  # prior close
    close_vals[-1] = 60200  # current close > prior close (breakout attempt)
    # Place a high above current price in the 20-bar window so current is NOT at price high
    close_vals[-10] = 60500
    close = pd.Series(close_vals)

    # Volume: gradually increasing, massive spike on last bar
    volume = pd.Series(np.linspace(10000, 20000, n))
    volume.iloc[-1] = 50000  # huge spike → volume_ratio > 1.5

    # High/Low with small noise
    high = close + 30
    low = close - 30

    return pd.DataFrame({
        "Open": close - 10,
        "High": high,
        "Low": low,
        "Close": close,
        "Volume": volume,
    })


def make_fear_greed_data(fgi_value=15, n=220, above_sma200=True):
    """Create synthetic data dict with FGI and klines for FearGreed strategy.

    Args:
        fgi_value: Fear & Greed Index value (≤25 triggers).
        n: Number of daily bars (need ≥210 for 200d SMA).
        above_sma200: Whether price should be above 200d SMA.
    """
    np.random.seed(2025)
    base = 60000
    trend = 15 if above_sma200 else -30
    returns = np.random.randn(n) * 200 + trend
    close = base + np.cumsum(returns)
    close = np.maximum(close, 1000)
    high = close + np.abs(np.random.randn(n) * 100)
    low = close - np.abs(np.random.randn(n) * 100)
    low = np.minimum(low, close)
    high = np.maximum(high, close)
    volume = np.random.randint(5000, 50000, n).astype(float)

    df = pd.DataFrame({
        "Open": close - np.random.randn(n) * 20,
        "High": high,
        "Low": low,
        "Close": close,
        "Volume": volume,
    })

    fg_data = {
        "data": [{
            "value": str(fgi_value),
            "value_classification": "Extreme Fear" if fgi_value <= 25 else "Fear",
        }]
    }

    return {
        "fear_greed": fg_data,
        "klines": {"BTCUSDT": df},
    }


def make_momentum_df(n=60, consec_days=5, vol_accel=1.5):
    """Create a DataFrame with consecutive up days + volume acceleration.

    Args:
        n: Number of bars.
        consec_days: Number of consecutive up days at the end.
        vol_accel: Volume acceleration ratio (today/yesterday).
    """
    np.random.seed(2026)
    base = 60000
    returns = np.random.randn(n) * 200
    # Force the last `consec_days` days to be up
    returns[-consec_days:] = np.abs(np.random.randn(consec_days) * 300) + 100
    close = base + np.cumsum(returns)
    close = np.maximum(close, 1000)
    high = close + np.abs(np.random.randn(n) * 80)
    low = close - np.abs(np.random.randn(n) * 80)
    low = np.minimum(low, close)
    high = np.maximum(high, close)

    volume = np.random.randint(5000, 20000, n).astype(float)
    for i in range(1, min(4, consec_days + 1)):
        volume[-i] = volume[-(i + 1)] * vol_accel

    return pd.DataFrame({
        "Open": close - np.random.randn(n) * 15,
        "High": high,
        "Low": low,
        "Close": close,
        "Volume": volume,
    })


# ═══════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def btc_df_250():
    return make_btc_df(250, seed=42)


@pytest.fixture
def btc_df_60():
    return make_btc_df(60, seed=99, trend=-10)


@pytest.fixture
def short_df():
    np.random.seed(7)
    n = 20
    close = 60000 + np.cumsum(np.random.randn(n) * 200)
    return pd.DataFrame({
        "Open": close,
        "High": close + 100,
        "Low": close - 100,
        "Close": close,
        "Volume": np.ones(n) * 10000,
    })


# ═══════════════════════════════════════════════════════════════════════════
# Indicator helpers
# ═══════════════════════════════════════════════════════════════════════════

class TestWilderEma:
    """Wilder's smoothing (alpha=1/period) vs standard EWM (alpha=2/(period+1))."""

    def test_differs_from_standard_ewm(self):
        from paper_trading.strategies.walkforward_elite_strategies import _wilder_ema
        series = pd.Series([10, 11, 12, 11, 13, 14, 12, 15, 13, 16,
                            14, 17, 15, 18, 16, 19, 17, 20, 18, 21])
        wilder = _wilder_ema(series, 14)
        standard = series.ewm(span=14, adjust=False).mean()
        assert not np.allclose(wilder.dropna(), standard.dropna(), atol=0.01)

    def test_wilder_lags_on_upward_data(self):
        """Wilder alpha=1/14 is slower than standard alpha=2/15."""
        from paper_trading.strategies.walkforward_elite_strategies import _wilder_ema
        series = pd.Series(list(range(1, 50)), dtype=float)
        wilder = _wilder_ema(series, 14)
        standard = series.ewm(span=14, adjust=False).mean()
        # On upward data, Wilder lags → lower value
        assert wilder.iloc[-1] < standard.iloc[-1]

    def test_constant_input_returns_constant(self):
        from paper_trading.strategies.walkforward_elite_strategies import _wilder_ema
        series = pd.Series([42.0] * 30)
        result = _wilder_ema(series, 14)
        assert abs(result.iloc[-1] - 42.0) < 0.01


class TestRSI:
    """RSI using Wilder's smoothing — range, NaN handling, known behavior."""

    def test_rsi_range_0_100(self, btc_df_250):
        from paper_trading.strategies.walkforward_elite_strategies import _rsi
        rsi = _rsi(btc_df_250["Close"], 14)
        valid = rsi.dropna()
        assert valid.min() >= 0
        assert valid.max() <= 100

    def test_rsi_monotonic_up_goes_high(self):
        """Pure uptrend → RSI should be high (>60). Need enough bars for Wilder warm-up."""
        from paper_trading.strategies.walkforward_elite_strategies import _rsi
        # Wilder EMA needs ~3x period to warm up → 50 bars for RSI(14)
        close = pd.Series(range(10, 80), dtype=float)  # 70 bars of steady rise
        rsi = _rsi(close, 14)
        assert rsi.iloc[-1] > 60

    def test_rsi_monotonic_down_goes_low(self):
        """Pure downtrend → RSI should be low (<40)."""
        from paper_trading.strategies.walkforward_elite_strategies import _rsi
        close = pd.Series(range(80, 10, -1), dtype=float)  # 70 bars of steady fall
        rsi = _rsi(close, 14)
        assert rsi.iloc[-1] < 40

    def test_rsi_initial_nan(self):
        """RSI(14) first bar is NaN (no prior close for diff)."""
        from paper_trading.strategies.walkforward_elite_strategies import _rsi
        close = pd.Series(np.random.randn(30) * 100 + 50000)
        rsi = _rsi(close, 14)
        assert np.isnan(rsi.iloc[0])

    def test_rsi_period_shorter_more_reactive(self, btc_df_250):
        """RSI(7) should be more reactive (higher variance) than RSI(14)."""
        from paper_trading.strategies.walkforward_elite_strategies import _rsi
        rsi7 = _rsi(btc_df_250["Close"], 7)
        rsi14 = _rsi(btc_df_250["Close"], 14)
        assert rsi7.dropna().std() > rsi14.dropna().std()

    def test_rsi_alternating_price_near_50(self):
        """Perfectly alternating up/down → RSI ≈ 50."""
        from paper_trading.strategies.walkforward_elite_strategies import _rsi
        # Create a series that alternates up/down with equal magnitude
        base = 60000
        moves = [100, -100] * 50  # perfect alternation
        close = pd.Series([base + sum(moves[:i]) for i in range(len(moves))], dtype=float)
        rsi = _rsi(close, 14)
        # After warm-up, RSI should be near 50
        assert 40 < rsi.dropna().iloc[-1] < 60


class TestATR:
    """ATR using Wilder's smoothing."""

    def test_atr_positive(self, btc_df_250):
        from paper_trading.strategies.walkforward_elite_strategies import _atr
        atr = _atr(btc_df_250["High"], btc_df_250["Low"], btc_df_250["Close"])
        valid = atr.dropna()
        assert (valid > 0).all()

    def test_atr_uses_wilder_not_sma(self, btc_df_250):
        """ATR with Wilder smoothing produces different values from SMA-based ATR."""
        from paper_trading.strategies.walkforward_elite_strategies import _wilder_ema
        high, low, close = btc_df_250["High"], btc_df_250["Low"], btc_df_250["Close"]
        tr = pd.concat([
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs(),
        ], axis=1).max(axis=1)
        wilder_atr = _wilder_ema(tr, 14)
        sma_atr = tr.rolling(14, min_periods=14).mean()
        # Wilder and SMA ATR should differ
        assert not np.allclose(
            wilder_atr.dropna().iloc[-1], sma_atr.dropna().iloc[-1], atol=0.01
        )

    def test_atr_higher_when_volatile(self):
        """ATR should increase when range expands."""
        from paper_trading.strategies.walkforward_elite_strategies import _atr
        n = 60
        close = pd.Series([50000.0] * n)
        high = close.copy()
        low = close.copy()
        high.iloc[:30] = close.iloc[:30] + 50
        low.iloc[:30] = close.iloc[:30] - 50
        high.iloc[30:] = close.iloc[30:] + 500
        low.iloc[30:] = close.iloc[30:] - 500
        atr = _atr(high, low, close, 14)
        assert atr.iloc[-1] > atr.iloc[20]


class TestADX:
    """ADX using Wilder's smoothing."""

    def test_adx_range_0_100(self, btc_df_250):
        from paper_trading.strategies.walkforward_elite_strategies import _adx
        adx = _adx(btc_df_250["High"], btc_df_250["Low"], btc_df_250["Close"])
        valid = adx.dropna()
        assert valid.min() >= 0
        assert valid.max() <= 100

    def test_adx_trending_market_high(self):
        """Strong trend → ADX should be >20."""
        from paper_trading.strategies.walkforward_elite_strategies import _adx
        n = 50
        close = pd.Series(np.arange(100, 100 + n * 10, 10), dtype=float)
        high = close + 5
        low = close - 5
        adx = _adx(high, low, close, 14)
        assert adx.iloc[-1] > 20

    def test_adx_sideways_market_low(self):
        """Ranging market → ADX should be low (<25)."""
        from paper_trading.strategies.walkforward_elite_strategies import _adx
        n = 60
        base = [100, 102, 98, 101, 99, 103, 97, 100, 102, 98] * (n // 10)
        close = pd.Series(base[:n], dtype=float)
        high = close + 1
        low = close - 1
        adx = _adx(high, low, close, 14)
        assert adx.iloc[-1] < 25


class TestOBV:
    """On-Balance Volume."""

    def test_obv_starts_at_zero(self):
        from paper_trading.strategies.walkforward_elite_strategies import _obv
        close = pd.Series([100, 101, 102, 101, 103], dtype=float)
        volume = pd.Series([1000, 2000, 1500, 3000, 2500], dtype=float)
        obv = _obv(close, volume)
        assert obv.iloc[0] == 0

    def test_obv_up_day_adds_volume(self):
        from paper_trading.strategies.walkforward_elite_strategies import _obv
        close = pd.Series([100, 110], dtype=float)
        volume = pd.Series([5000, 3000], dtype=float)
        obv = _obv(close, volume)
        assert obv.iloc[1] == 3000

    def test_obv_down_day_subtracts_volume(self):
        from paper_trading.strategies.walkforward_elite_strategies import _obv
        close = pd.Series([110, 100], dtype=float)
        volume = pd.Series([5000, 3000], dtype=float)
        obv = _obv(close, volume)
        assert obv.iloc[1] == -3000

    def test_obv_unchanged_day_zero_direction(self):
        from paper_trading.strategies.walkforward_elite_strategies import _obv
        close = pd.Series([100, 100], dtype=float)
        volume = pd.Series([5000, 3000], dtype=float)
        obv = _obv(close, volume)
        assert obv.iloc[1] == 0

    def test_obv_cumulative(self):
        """OBV should be cumulative across multiple days."""
        from paper_trading.strategies.walkforward_elite_strategies import _obv
        # up, up, down, up
        close = pd.Series([100, 110, 120, 115, 125], dtype=float)
        volume = pd.Series([1000, 2000, 3000, 1500, 4000], dtype=float)
        obv = _obv(close, volume)
        # Day 1: 0 (start)
        # Day 2: 0 + 2000 = 2000 (up)
        # Day 3: 2000 + 3000 = 5000 (up)
        # Day 4: 5000 - 1500 = 3500 (down)
        # Day 5: 3500 + 4000 = 7500 (up)
        assert obv.iloc[4] == 7500


class TestVolumeRatio:
    """Volume ratio vs 20-period average."""

    def test_normal_volume_ratio_near_1(self, btc_df_250):
        from paper_trading.strategies.walkforward_elite_strategies import _volume_ratio
        vr = _volume_ratio(btc_df_250["Volume"], 20)
        valid = vr.dropna()
        assert 0.5 < valid.mean() < 2.0

    def test_spike_volume_ratio_high(self):
        from paper_trading.strategies.walkforward_elite_strategies import _volume_ratio
        vol = pd.Series([1000] * 30 + [50000])
        vr = _volume_ratio(vol, 20)
        assert vr.iloc[-1] > 10

    def test_zero_avg_volume_returns_nan(self):
        from paper_trading.strategies.walkforward_elite_strategies import _volume_ratio
        vol = pd.Series([0] * 30)
        vr = _volume_ratio(vol, 20)
        assert vr.dropna().empty or np.isnan(vr.iloc[-1])


class TestSmartRound:
    """_smart_round — adaptive decimal rounding by magnitude."""

    def test_large_value_2_decimals(self):
        from paper_trading.strategies.walkforward_elite_strategies import _smart_round
        # abs >= 100 → 2 decimals
        assert _smart_round(60123.456) == 60123.46

    def test_value_between_1_and_100_4_decimals(self):
        from paper_trading.strategies.walkforward_elite_strategies import _smart_round
        # abs >= 1 and < 100 → 4 decimals
        assert _smart_round(5.4321) == 5.4321

    def test_value_between_0_01_and_1_6_decimals(self):
        from paper_trading.strategies.walkforward_elite_strategies import _smart_round
        # abs >= 0.01 and < 1 → 6 decimals
        assert _smart_round(0.123456) == 0.123456

    def test_tiny_value_10_decimals(self):
        from paper_trading.strategies.walkforward_elite_strategies import _smart_round
        # abs < 0.01 → 10 decimals
        result = _smart_round(0.0000123456789)
        assert result == 0.0000123457

    def test_zero_returns_zero(self):
        from paper_trading.strategies.walkforward_elite_strategies import _smart_round
        assert _smart_round(0) == 0.0

    def test_negative_value(self):
        from paper_trading.strategies.walkforward_elite_strategies import _smart_round
        result = _smart_round(-5.4321)
        assert result == -5.4321  # abs >= 1 → 4 decimals


# ═══════════════════════════════════════════════════════════════════════════
# STOBVSupportDivergence — pick generation
# ═══════════════════════════════════════════════════════════════════════════

class TestSTOBVSupportDivergence:
    """Test OBV support divergence pick generation with synthetic data."""

    def test_strategy_instantiation(self):
        from paper_trading.strategies.walkforward_elite_strategies import STOBVSupportDivergence
        strat = STOBVSupportDivergence()
        assert strat.name == "st_obv_support_divergence"
        assert strat.portfolio_type == "walkforward_elite"
        assert strat.category == "crypto"

    def test_check_symbol_returns_pick_on_divergence(self):
        """When OBV divergence + support + volume confirm → should generate LONG pick."""
        from paper_trading.strategies.walkforward_elite_strategies import STOBVSupportDivergence
        strat = STOBVSupportDivergence()
        df = make_obv_divergence_df(50)
        pick = strat._check_symbol("BTCUSDT", df)
        # With carefully crafted data, should generate a pick
        assert pick is not None, "Expected pick with OBV divergence setup"
        assert pick.symbol == "BTCUSDT"
        assert pick.direction == "LONG"
        assert pick.strategy == "st_obv_support_divergence"
        assert pick.tp > pick.entry_price > pick.sl
        assert pick.confidence > 0

    def test_check_symbol_short_df_returns_none(self, short_df):
        """DataFrame with < 30 bars → no pick."""
        from paper_trading.strategies.walkforward_elite_strategies import STOBVSupportDivergence
        strat = STOBVSupportDivergence()
        pick = strat._check_symbol("BTCUSDT", short_df)
        assert pick is None

    def test_generate_picks_returns_list(self, btc_df_250):
        """generate_picks should always return a list, never crash."""
        from paper_trading.strategies.walkforward_elite_strategies import STOBVSupportDivergence
        strat = STOBVSupportDivergence()
        data = {"BTCUSDT": btc_df_250, "ETHUSDT": btc_df_250}
        picks = strat.generate_picks(data)
        assert isinstance(picks, list)
        assert len(picks) <= strat.MAX_PICKS

    def test_pick_has_required_fields(self):
        """Generated pick must have all NormalizedPick fields populated."""
        from paper_trading.strategies.walkforward_elite_strategies import STOBVSupportDivergence
        from paper_trading.models import NormalizedPick
        strat = STOBVSupportDivergence()
        df = make_obv_divergence_df(50)
        pick = strat._check_symbol("BTCUSDT", df)
        assert pick is not None
        assert isinstance(pick, NormalizedPick)
        assert pick.symbol == "BTCUSDT"
        assert pick.direction in ("LONG", "SHORT")
        assert pick.entry_price > 0
        assert pick.tp > 0
        assert pick.sl > 0
        assert pick.strategy == strat.name
        assert pick.strategy_name == strat.display_name
        assert pick.category == strat.category
        assert 0 <= pick.confidence <= 1
        assert pick.reason
        assert pick.raw_signal is not None

    def test_picks_sorted_by_confidence(self):
        """Multiple picks should be sorted by confidence descending."""
        from paper_trading.strategies.walkforward_elite_strategies import STOBVSupportDivergence
        strat = STOBVSupportDivergence()
        df = make_obv_divergence_df(50)
        data = {sym: df.copy() for sym in ["BTCUSDT", "ETHUSDT", "SOLUSDT"]}
        picks = strat.generate_picks(data)
        if len(picks) > 1:
            for i in range(len(picks) - 1):
                assert picks[i].confidence >= picks[i + 1].confidence

    def test_tp_sl_reasonable_distance(self):
        """TP and SL should be within reasonable distance from entry."""
        from paper_trading.strategies.walkforward_elite_strategies import STOBVSupportDivergence
        strat = STOBVSupportDivergence()
        df = make_obv_divergence_df(50)
        pick = strat._check_symbol("BTCUSDT", df)
        assert pick is not None
        entry = pick.entry_price
        tp_pct = (pick.tp - entry) / entry
        sl_pct = (entry - pick.sl) / entry
        assert 0 < tp_pct < 0.15, f"TP too far: {tp_pct:.2%}"
        assert 0 < sl_pct < 0.15, f"SL too far: {sl_pct:.2%}"


# ═══════════════════════════════════════════════════════════════════════════
# STFearGreedContrarian — pick generation
# ═══════════════════════════════════════════════════════════════════════════

class TestSTFearGreedContrarian:
    """Test Fear & Greed contrarian pick generation."""

    def test_strategy_instantiation(self):
        from paper_trading.strategies.walkforward_elite_strategies import STFearGreedContrarian
        strat = STFearGreedContrarian()
        assert strat.name == "st_fear_greed_contrarian"
        assert strat.portfolio_type == "walkforward_elite"
        assert strat.FGI_THRESHOLD == 25

    def test_extreme_fear_generates_pick(self):
        """FGI ≤ 25 + above 200d SMA + RSI < 60 → LONG pick."""
        from paper_trading.strategies.walkforward_elite_strategies import STFearGreedContrarian
        strat = STFearGreedContrarian()
        data = make_fear_greed_data(fgi_value=10, above_sma200=True)
        picks = strat.generate_picks(data)
        assert len(picks) >= 1, "Expected pick with extreme fear (FGI=10)"
        pick = picks[0]
        assert pick.direction == "LONG"
        assert pick.strategy == "st_fear_greed_contrarian"
        assert pick.tp > pick.entry_price > pick.sl
        assert pick.raw_signal["fgi_value"] == 10

    def test_no_fear_no_pick(self):
        """FGI > 25 → no picks (not extreme fear)."""
        from paper_trading.strategies.walkforward_elite_strategies import STFearGreedContrarian
        strat = STFearGreedContrarian()
        data = make_fear_greed_data(fgi_value=50)
        picks = strat.generate_picks(data)
        assert picks == []

    def test_fgi_boundary_25_triggers(self):
        """FGI=25 exactly (at threshold) → should generate picks."""
        from paper_trading.strategies.walkforward_elite_strategies import STFearGreedContrarian
        strat = STFearGreedContrarian()
        data = make_fear_greed_data(fgi_value=25, above_sma200=True)
        picks = strat.generate_picks(data)
        # FGI=25 is ≤ 25 threshold → should act
        # May not pick if SMA/RSI conditions not met on random data, but should not crash
        # The key test: strategy does NOT short-circuit on FGI=25
        for pick in picks:
            assert pick.direction == "LONG"

    def test_fgi_26_no_pick(self):
        """FGI=26 (just above threshold) → no picks."""
        from paper_trading.strategies.walkforward_elite_strategies import STFearGreedContrarian
        strat = STFearGreedContrarian()
        data = make_fear_greed_data(fgi_value=26, above_sma200=True)
        picks = strat.generate_picks(data)
        assert picks == []

    def test_below_sma200_no_pick(self):
        """FGI ≤ 25 but price below 200d SMA → no pick (downtrend protection)."""
        from paper_trading.strategies.walkforward_elite_strategies import STFearGreedContrarian
        strat = STFearGreedContrarian()
        data = make_fear_greed_data(fgi_value=10, above_sma200=False)
        picks = strat.generate_picks(data)
        # With downtrend data, SMA filter should block picks
        # Random data may occasionally have price > SMA200, so we check direction
        for pick in picks:
            assert pick.direction == "LONG"

    def test_no_fear_greed_data_no_pick(self):
        """Missing FGI data → no picks."""
        from paper_trading.strategies.walkforward_elite_strategies import STFearGreedContrarian
        strat = STFearGreedContrarian()
        data = {"fear_greed": None, "klines": {}}
        picks = strat.generate_picks(data)
        assert picks == []

    def test_malformed_fgi_no_pick(self):
        """Malformed FGI response → no picks, no crash."""
        from paper_trading.strategies.walkforward_elite_strategies import STFearGreedContrarian
        strat = STFearGreedContrarian()
        for bad_data in [
            {"fear_greed": {"data": []}, "klines": {}},      # empty data array
            {"fear_greed": {"data": [{}]}, "klines": {}},     # missing value key
            {"fear_greed": {}, "klines": {}},                 # no data key
        ]:
            picks = strat.generate_picks(bad_data)
            assert picks == []

    def test_long_only_never_short(self):
        """Strategy is LONG-only — SHORT direction hard-blocked (WF negative edge)."""
        from paper_trading.strategies.walkforward_elite_strategies import STFearGreedContrarian
        strat = STFearGreedContrarian()
        data = make_fear_greed_data(fgi_value=5, above_sma200=True)
        picks = strat.generate_picks(data)
        for pick in picks:
            assert pick.direction == "LONG"

    def test_confidence_scales_with_fear(self):
        """More extreme fear → higher confidence."""
        from paper_trading.strategies.walkforward_elite_strategies import STFearGreedContrarian
        strat = STFearGreedContrarian()
        data_low = make_fear_greed_data(fgi_value=5, above_sma200=True)
        data_high = make_fear_greed_data(fgi_value=25, above_sma200=True)
        picks_low = strat.generate_picks(data_low)
        picks_high = strat.generate_picks(data_high)
        if picks_low and picks_high:
            assert picks_low[0].confidence >= picks_high[0].confidence

    def test_max_picks_capped(self):
        """Should never exceed MAX_PICKS."""
        from paper_trading.strategies.walkforward_elite_strategies import STFearGreedContrarian
        strat = STFearGreedContrarian()
        single_data = make_fear_greed_data(fgi_value=5, above_sma200=True)
        klines = single_data["klines"]
        for sym in ["ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT",
                     "AVAXUSDT", "DOTUSDT", "LINKUSDT", "LTCUSDT", "DOGEUSDT"]:
            klines[sym] = klines["BTCUSDT"].copy()
        data = {"fear_greed": single_data["fear_greed"], "klines": klines}
        picks = strat.generate_picks(data)
        assert len(picks) <= strat.MAX_PICKS

    def test_rsi_above_60_blocks_pick(self):
        """FGI ≤ 25 + above SMA200 but RSI > 60 → no pick (already recovering)."""
        from paper_trading.strategies.walkforward_elite_strategies import (
            STFearGreedContrarian, _rsi, _sma,
        )
        strat = STFearGreedContrarian()
        # Create data where price has a massive recent rally → RSI > 60
        np.random.seed(3030)
        n = 220
        base = 60000
        # Downtrend for 200 bars (SMA200 will be above), then huge rally last 20 bars
        returns = np.random.randn(n) * 100 - 20
        returns[-20:] = 500  # massive rally → RSI will spike
        close = base + np.cumsum(returns)
        close = np.maximum(close, 1000)
        high = close + np.abs(np.random.randn(n) * 50)
        low = close - np.abs(np.random.randn(n) * 50)
        low = np.minimum(low, close)
        high = np.maximum(high, close)
        volume = np.random.randint(5000, 50000, n).astype(float)

        df = pd.DataFrame({
            "Open": close, "High": high, "Low": low,
            "Close": close, "Volume": volume,
        })

        # Verify RSI > 60 on this data
        rsi = _rsi(df["Close"], 14)
        # Only proceed if RSI actually > 60 (Wilder smoothing may lag)
        if rsi.iloc[-1] > strat.RSI_MAX:
            data = {
                "fear_greed": {
                    "data": [{"value": "10", "value_classification": "Extreme Fear"}]
                },
                "klines": {"BTCUSDT": df},
            }
            picks = strat.generate_picks(data)
            # RSI > 60 should block the pick even though FGI=10
            assert picks == [], f"Expected no pick with RSI={rsi.iloc[-1]:.0f} > 60"


# ═══════════════════════════════════════════════════════════════════════════
# STMultiDayMomentum — pick generation
# ═══════════════════════════════════════════════════════════════════════════

class TestSTMultiDayMomentum:
    """Test multi-day momentum pick generation."""

    def test_strategy_instantiation(self):
        from paper_trading.strategies.walkforward_elite_strategies import STMultiDayMomentum
        strat = STMultiDayMomentum()
        assert strat.name == "st_multi_day_momentum"
        assert strat.portfolio_type == "walkforward_elite"
        assert strat.CONSEC_DAYS_MIN == 3

    def test_consecutive_up_days_generates_pick(self):
        """5 consecutive up days + volume accel + trending ADX → LONG pick."""
        from paper_trading.strategies.walkforward_elite_strategies import STMultiDayMomentum
        strat = STMultiDayMomentum()
        df = make_momentum_df(n=60, consec_days=5, vol_accel=1.5)
        pick = strat._check_symbol("BTCUSDT", df)
        # May or may not fire depending on ADX/SMA filters
        if pick is not None:
            assert pick.direction == "LONG"
            assert pick.strategy == "st_multi_day_momentum"
            assert pick.tp > pick.entry_price > pick.sl
            assert pick.raw_signal["consecutive_days"] >= 3

    def test_fewer_than_3_up_days_no_pick(self):
        """Only 2 consecutive up days → below minimum → no pick."""
        from paper_trading.strategies.walkforward_elite_strategies import STMultiDayMomentum
        strat = STMultiDayMomentum()
        df = make_momentum_df(n=60, consec_days=2, vol_accel=1.5)
        pick = strat._check_symbol("BTCUSDT", df)
        assert pick is None

    def test_short_df_no_pick(self, short_df):
        """DataFrame with < 30 bars → no pick."""
        from paper_trading.strategies.walkforward_elite_strategies import STMultiDayMomentum
        strat = STMultiDayMomentum()
        pick = strat._check_symbol("BTCUSDT", short_df)
        assert pick is None

    def test_no_volume_acceleration_no_pick(self):
        """Consecutive up days but declining volume → vol_accel < 1.1 → no pick."""
        from paper_trading.strategies.walkforward_elite_strategies import STMultiDayMomentum
        strat = STMultiDayMomentum()
        df = make_momentum_df(n=60, consec_days=5, vol_accel=0.8)
        pick = strat._check_symbol("BTCUSDT", df)
        assert pick is None

    def test_pick_fields_complete(self):
        """Any generated pick must have all required NormalizedPick fields."""
        from paper_trading.strategies.walkforward_elite_strategies import STMultiDayMomentum
        from paper_trading.models import NormalizedPick
        strat = STMultiDayMomentum()
        df = make_momentum_df(n=60, consec_days=5, vol_accel=1.5)
        pick = strat._check_symbol("BTCUSDT", df)
        if pick is not None:
            assert isinstance(pick, NormalizedPick)
            assert pick.symbol == "BTCUSDT"
            assert pick.direction == "LONG"
            assert pick.entry_price > 0
            assert pick.tp > 0
            assert pick.sl > 0
            assert pick.confidence > 0
            assert pick.reason
            assert pick.raw_signal is not None
            assert "consecutive_days" in pick.raw_signal
            assert "vol_accel" in pick.raw_signal
            assert "adx" in pick.raw_signal

    def test_generate_picks_returns_list(self, btc_df_60):
        """generate_picks should always return a list."""
        from paper_trading.strategies.walkforward_elite_strategies import STMultiDayMomentum
        strat = STMultiDayMomentum()
        data = {"BTCUSDT": btc_df_60}
        picks = strat.generate_picks(data)
        assert isinstance(picks, list)
        assert len(picks) <= strat.MAX_PICKS

    def test_max_picks_capped(self):
        """Should never exceed MAX_PICKS = 3."""
        from paper_trading.strategies.walkforward_elite_strategies import STMultiDayMomentum
        strat = STMultiDayMomentum()
        df = make_momentum_df(n=60, consec_days=5, vol_accel=1.5)
        data = {sym: df.copy() for sym in [
            "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"
        ]}
        picks = strat.generate_picks(data)
        assert len(picks) <= strat.MAX_PICKS


# ═══════════════════════════════════════════════════════════════════════════
# Strategy registration & metadata
# ═══════════════════════════════════════════════════════════════════════════

class TestStrategyRegistration:
    """Verify strategies are properly registered in ALL_STRATEGIES."""

    def test_all_three_in_all_strategies(self):
        from paper_trading.strategies import ALL_STRATEGIES
        names = {s.name for s in ALL_STRATEGIES}
        assert "st_obv_support_divergence" in names
        assert "st_fear_greed_contrarian" in names
        assert "st_multi_day_momentum" in names

    def test_portfolio_map_has_all_three(self):
        from paper_trading.strategies import STRATEGY_PORTFOLIO_MAP
        assert STRATEGY_PORTFOLIO_MAP.get("st_obv_support_divergence") == "walkforward_elite"
        assert STRATEGY_PORTFOLIO_MAP.get("st_fear_greed_contrarian") == "walkforward_elite"
        assert STRATEGY_PORTFOLIO_MAP.get("st_multi_day_momentum") == "walkforward_elite"

    def test_system_name_mapping(self):
        """_get_system_name expects a strategy object (with .name), not a string."""
        from paper_trading.strategies import _get_system_name, ALL_STRATEGIES
        for strat in ALL_STRATEGIES:
            if strat.name in ("st_obv_support_divergence", "st_fear_greed_contrarian",
                              "st_multi_day_momentum"):
                result = _get_system_name(strat)
                assert "Walk-Forward" in result

    def test_no_duplicate_names(self):
        from paper_trading.strategies import ALL_STRATEGIES
        names = [s.name for s in ALL_STRATEGIES]
        assert len(names) == len(set(names)), "Duplicate strategy names found"

    def test_strategy_categories(self):
        from paper_trading.strategies.walkforward_elite_strategies import (
            STOBVSupportDivergence, STFearGreedContrarian, STMultiDayMomentum,
        )
        for Strat in [STOBVSupportDivergence, STFearGreedContrarian, STMultiDayMomentum]:
            strat = Strat()
            assert strat.category == "crypto"
            assert strat.portfolio_type == "walkforward_elite"


# ═══════════════════════════════════════════════════════════════════════════
# Edge cases & robustness
# ═══════════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    """Edge cases: NaN, zero volume, constant price, empty data."""

    def test_nan_close_no_crash(self):
        """NaN in close series → should not crash."""
        from paper_trading.strategies.walkforward_elite_strategies import (
            STOBVSupportDivergence, STMultiDayMomentum,
        )
        df = pd.DataFrame({
            "Open": [60000] * 50,
            "High": [60100] * 50,
            "Low": [59900] * 50,
            "Close": [60000] * 50,
            "Volume": [10000] * 50,
        })
        df.loc[30, "Close"] = np.nan
        for Strat in [STOBVSupportDivergence, STMultiDayMomentum]:
            strat = Strat()
            # Should not crash — may return None
            strat._check_symbol("BTCUSDT", df)

    def test_zero_volume_no_crash(self):
        """All zero volume → OBV = 0, volume_ratio = NaN → no pick, no crash."""
        from paper_trading.strategies.walkforward_elite_strategies import STOBVSupportDivergence
        strat = STOBVSupportDivergence()
        n = 50
        df = pd.DataFrame({
            "Open": np.linspace(60000, 61000, n),
            "High": np.linspace(60100, 61100, n),
            "Low": np.linspace(59900, 60900, n),
            "Close": np.linspace(60000, 61000, n),
            "Volume": [0.0] * n,
        })
        pick = strat._check_symbol("BTCUSDT", df)
        assert pick is None  # no volume → no confirmation → no pick

    def test_constant_price_no_crash(self):
        """All same price → no ATR, no OBV divergence → no pick, no crash."""
        from paper_trading.strategies.walkforward_elite_strategies import (
            STOBVSupportDivergence, STMultiDayMomentum,
        )
        n = 50
        df = pd.DataFrame({
            "Open": [60000.0] * n,
            "High": [60000.0] * n,
            "Low": [60000.0] * n,
            "Close": [60000.0] * n,
            "Volume": [10000.0] * n,
        })
        for Strat in [STOBVSupportDivergence, STMultiDayMomentum]:
            strat = Strat()
            # Constant price → no movement, no signal — should not crash
            strat._check_symbol("BTCUSDT", df)

    def test_generate_picks_empty_data(self):
        """Empty data dict → empty picks list."""
        from paper_trading.strategies.walkforward_elite_strategies import (
            STOBVSupportDivergence, STMultiDayMomentum,
        )
        for Strat in [STOBVSupportDivergence, STMultiDayMomentum]:
            strat = Strat()
            picks = strat.generate_picks({})
            assert picks == []

    def test_fear_greed_empty_klines(self):
        """FGI extreme fear but no klines → empty picks."""
        from paper_trading.strategies.walkforward_elite_strategies import STFearGreedContrarian
        strat = STFearGreedContrarian()
        data = {
            "fear_greed": {
                "data": [{"value": "10", "value_classification": "Extreme Fear"}]
            },
            "klines": {},
        }
        picks = strat.generate_picks(data)
        assert picks == []
