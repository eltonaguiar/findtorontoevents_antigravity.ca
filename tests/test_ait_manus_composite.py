"""Unit tests for baby_strategies.ait_manus_composite."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from baby_strategies import ait_manus_composite as M


# ---------------------------------------------------------------------------
# Synthetic OHLCV fixtures
# ---------------------------------------------------------------------------
def _frame(close_values: list[float]) -> pd.DataFrame:
    n = len(close_values)
    return pd.DataFrame({
        "Open": close_values,
        "High": [c * 1.01 for c in close_values],
        "Low": [c * 0.99 for c in close_values],
        "Close": close_values,
        "Volume": [1000.0] * n,
    })


def _oversold_frame() -> pd.DataFrame:
    # 30 bars trending hard down -> RSI well below 30
    return _frame([100.0 - i * 1.2 for i in range(30)])


def _overbought_frame() -> pd.DataFrame:
    # 30 bars trending hard up -> RSI well above 70
    return _frame([100.0 + i * 1.2 for i in range(30)])


def _flat_frame() -> pd.DataFrame:
    return _frame([100.0] * 30)


# ---------------------------------------------------------------------------
# TA factor
# ---------------------------------------------------------------------------
def test_ta_factor_oversold_returns_plus3():
    assert M.ta_factor(_oversold_frame()) == 3


def test_ta_factor_overbought_returns_minus3():
    assert M.ta_factor(_overbought_frame()) == -3


def test_ta_factor_flat_returns_zero():
    assert M.ta_factor(_flat_frame()) == 0


def test_ta_factor_tolerates_bad_input():
    assert M.ta_factor(None) == 0
    assert M.ta_factor(pd.DataFrame()) == 0
    assert M.ta_factor(pd.DataFrame({"NotClose": [1, 2, 3]})) == 0


# ---------------------------------------------------------------------------
# News factor — patched upstream
# ---------------------------------------------------------------------------
def test_news_factor_positive_maps_to_plus2():
    with patch("alpha_engine.cryptopanic_feargreed.fetch_cryptopanic_news",
               return_value={"votes": {"positive": 10, "negative": 1}}), \
         patch("alpha_engine.cryptopanic_feargreed._classify_sentiment",
               return_value="positive"):
        assert M.news_factor("BTCUSDT") == 2


def test_news_factor_negative_maps_to_minus2():
    with patch("alpha_engine.cryptopanic_feargreed.fetch_cryptopanic_news",
               return_value={"votes": {}}), \
         patch("alpha_engine.cryptopanic_feargreed._classify_sentiment",
               return_value="negative"):
        assert M.news_factor("BTCUSDT") == -2


def test_news_factor_neutral_maps_to_zero():
    with patch("alpha_engine.cryptopanic_feargreed.fetch_cryptopanic_news",
               return_value={"votes": {}}), \
         patch("alpha_engine.cryptopanic_feargreed._classify_sentiment",
               return_value="neutral"):
        assert M.news_factor("BTCUSDT") == 0


def test_news_factor_upstream_exception_returns_zero():
    with patch("alpha_engine.cryptopanic_feargreed.fetch_cryptopanic_news",
               side_effect=RuntimeError("boom")):
        assert M.news_factor("BTCUSDT") == 0


def test_news_factor_empty_symbol_returns_zero():
    assert M.news_factor("") == 0


# ---------------------------------------------------------------------------
# Macro factor — patched filesystem
# ---------------------------------------------------------------------------
def _write_regime_file(tmp_path: Path, bull: int, bear: int, hours_old: float = 1.0) -> Path:
    from datetime import timedelta
    ts = (datetime.now(timezone.utc) - timedelta(hours=hours_old)).isoformat().replace("+00:00", "Z")
    p = tmp_path / "regime_state.json"
    p.write_text(json.dumps({
        "generated_at": ts,
        "market_overview": {"bull_count": bull, "bear_count": bear, "neutral_count": 10},
    }), encoding="utf-8")
    return p


def test_macro_factor_bull_dominant(tmp_path):
    p = _write_regime_file(tmp_path, bull=20, bear=5)
    assert M.macro_factor(p) == 2


def test_macro_factor_bear_dominant(tmp_path):
    p = _write_regime_file(tmp_path, bull=5, bear=20)
    assert M.macro_factor(p) == -2


def test_macro_factor_balanced(tmp_path):
    p = _write_regime_file(tmp_path, bull=12, bear=10)
    assert M.macro_factor(p) == 0


def test_macro_factor_stale_file_returns_zero(tmp_path):
    p = _write_regime_file(tmp_path, bull=20, bear=5, hours_old=48)
    assert M.macro_factor(p) == 0


def test_macro_factor_missing_file_returns_zero(tmp_path):
    assert M.macro_factor(tmp_path / "does_not_exist.json") == 0


# ---------------------------------------------------------------------------
# Community factor — patched upstream
# ---------------------------------------------------------------------------
def test_community_factor_bullish_bucket():
    with patch("alpha_engine.lunarcrush_signal.get_lunarcrush_score",
               return_value={"galaxy_score": 75}):
        assert M.community_factor("BTCUSDT") == 2


def test_community_factor_bearish_bucket():
    with patch("alpha_engine.lunarcrush_signal.get_lunarcrush_score",
               return_value={"galaxy_score": 25}):
        assert M.community_factor("BTCUSDT") == -2


def test_community_factor_neutral_bucket():
    with patch("alpha_engine.lunarcrush_signal.get_lunarcrush_score",
               return_value={"galaxy_score": 50}):
        assert M.community_factor("BTCUSDT") == 0


def test_community_factor_upstream_exception_returns_zero():
    with patch("alpha_engine.lunarcrush_signal.get_lunarcrush_score",
               side_effect=RuntimeError("boom")):
        assert M.community_factor("BTCUSDT") == 0


# ---------------------------------------------------------------------------
# Composite scoring
# ---------------------------------------------------------------------------
def test_compute_score_uniform_weights():
    assert M.compute_score(3, 2, 2, 1) == 8


def test_compute_score_weighted():
    w = {"ta": 2.0, "news": 1.0, "macro": 0.5, "community": 0.0}
    assert M.compute_score(3, 2, 4, 5, weights=w) == 2 * 3 + 1 * 2 + 0.5 * 4 + 0
    assert M.compute_score(3, 2, 4, 5, weights=w) == 10.0


def test_score_to_signal_thresholds():
    assert M.score_to_signal(4.0) == "BUY"
    assert M.score_to_signal(4.1) == "BUY"
    assert M.score_to_signal(3.9) == "NEUTRAL"
    assert M.score_to_signal(-2.0) == "SELL"
    assert M.score_to_signal(-1.9) == "NEUTRAL"
    assert M.score_to_signal(0) == "NEUTRAL"


def test_confidence_clamped_to_band():
    assert 50 <= M._confidence_from_score(0) <= 95
    assert 50 <= M._confidence_from_score(100) <= 95
    assert M._confidence_from_score(0) == 50.0


# ---------------------------------------------------------------------------
# ManusCompositeStrategy integration
# ---------------------------------------------------------------------------
def test_strategy_returns_buy_when_all_factors_bullish(tmp_path):
    df = _oversold_frame()  # TA=+3
    regime = _write_regime_file(tmp_path, bull=20, bear=5)  # macro=+2
    with patch("alpha_engine.cryptopanic_feargreed.fetch_cryptopanic_news",
               return_value={"votes": {}}), \
         patch("alpha_engine.cryptopanic_feargreed._classify_sentiment",
               return_value="positive"), \
         patch("alpha_engine.lunarcrush_signal.get_lunarcrush_score",
               return_value={"galaxy_score": 80}):
        strat = M.ManusCompositeStrategy(regime_path=regime)
        sigs = strat.generate_signals(df, "BTCUSDT")
    assert len(sigs) == 1
    assert sigs[0].direction == "BUY"
    assert sigs[0].take_profit > sigs[0].entry_price
    assert sigs[0].stop_loss < sigs[0].entry_price
    assert "manus score=" in sigs[0].reason


def test_strategy_returns_empty_on_neutral_score(tmp_path):
    df = _flat_frame()  # TA=0
    regime = _write_regime_file(tmp_path, bull=11, bear=10)  # macro=0
    with patch("alpha_engine.cryptopanic_feargreed.fetch_cryptopanic_news",
               return_value={"votes": {}}), \
         patch("alpha_engine.cryptopanic_feargreed._classify_sentiment",
               return_value="neutral"), \
         patch("alpha_engine.lunarcrush_signal.get_lunarcrush_score",
               return_value={"galaxy_score": 50}):
        strat = M.ManusCompositeStrategy(regime_path=regime)
        assert strat.generate_signals(df, "BTCUSDT") == []


def test_strategy_returns_sell_on_bearish_stack(tmp_path):
    df = _overbought_frame()  # TA=-3
    regime = _write_regime_file(tmp_path, bull=5, bear=20)  # macro=-2
    with patch("alpha_engine.cryptopanic_feargreed.fetch_cryptopanic_news",
               return_value={"votes": {}}), \
         patch("alpha_engine.cryptopanic_feargreed._classify_sentiment",
               return_value="negative"), \
         patch("alpha_engine.lunarcrush_signal.get_lunarcrush_score",
               return_value={"galaxy_score": 20}):
        strat = M.ManusCompositeStrategy(regime_path=regime)
        sigs = strat.generate_signals(df, "BTCUSDT")
    assert len(sigs) == 1
    assert sigs[0].direction == "SELL"


def test_compute_score_clamps_runaway_weights():
    # weights of 100 on every factor with max-magnitude inputs would yield 1000
    w = {"ta": 100.0, "news": 100.0, "macro": 100.0, "community": 100.0}
    assert M.compute_score(3, 2, 2, 2, weights=w) == M._SCORE_CLAMP
    assert M.compute_score(-3, -2, -2, -2, weights=w) == -M._SCORE_CLAMP


def test_macro_factor_caches_by_mtime(tmp_path):
    M._regime_cache.clear()
    p = _write_regime_file(tmp_path, bull=20, bear=5)
    assert M.macro_factor(p) == 2
    assert len(M._regime_cache) == 1
    # Second call hits cache — verify by removing the file mid-flight
    p.unlink()
    assert M.macro_factor(p) == 0  # file now gone -> 0, NOT cached value
    # Rewrite the file with different content -> mtime changes -> cache miss
    import time
    time.sleep(0.02)
    p2 = _write_regime_file(tmp_path, bull=5, bear=20)
    assert M.macro_factor(p2) == -2


def test_from_meta_loads_weights_and_thresholds(tmp_path):
    meta = tmp_path / "meta.json"
    meta.write_text(json.dumps({
        "runtime": {
            "weights": {"ta": 2.0, "news": 0.5, "macro": 1.0, "community": 0.0},
            "buy_threshold": 5.0,
            "sell_threshold": -3.0,
        }
    }), encoding="utf-8")
    strat = M.ManusCompositeStrategy.from_meta(meta)
    assert strat.weights == {"ta": 2.0, "news": 0.5, "macro": 1.0, "community": 0.0}
    assert strat.buy_threshold == 5.0
    assert strat.sell_threshold == -3.0


def test_from_meta_uses_defaults_when_runtime_block_missing(tmp_path):
    meta = tmp_path / "meta.json"
    meta.write_text(json.dumps({"name": "ait_manus_composite"}), encoding="utf-8")
    strat = M.ManusCompositeStrategy.from_meta(meta)
    assert strat.weights == M.DEFAULT_WEIGHTS
    assert strat.buy_threshold == M.BUY_THRESHOLD
    assert strat.sell_threshold == M.SELL_THRESHOLD


def test_from_meta_raises_on_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        M.ManusCompositeStrategy.from_meta(tmp_path / "nope.json")


def test_shipped_meta_json_is_loadable():
    """The committed baby_strategies/ait_manus_composite.meta.json must load."""
    meta = Path("baby_strategies/ait_manus_composite.meta.json")
    if not meta.exists():
        pytest.skip("meta file not present in this checkout")
    strat = M.ManusCompositeStrategy.from_meta(meta)
    assert strat.weights["ta"] == 1.0
    assert strat.buy_threshold == 4.0


def test_strategy_degrades_gracefully_when_all_upstreams_fail():
    df = _oversold_frame()  # only TA=+3 from clean input
    with patch("alpha_engine.cryptopanic_feargreed.fetch_cryptopanic_news",
               side_effect=RuntimeError("net")), \
         patch("alpha_engine.lunarcrush_signal.get_lunarcrush_score",
               side_effect=RuntimeError("net")):
        strat = M.ManusCompositeStrategy(regime_path=Path("/nonexistent"))
        # TA=3, news=0, macro=0, community=0 -> score=3, below BUY threshold
        assert strat.generate_signals(df, "BTCUSDT") == []
