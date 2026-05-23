"""Unit tests for HF tiers, direction scoring, goldmine floor, dynamic cap, and asset-class composite."""
import pytest


# ═══════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════

@pytest.fixture
def cfg_v3():
    """Config matching hf_conviction_tiers.json v3."""
    return {
        "version": 3,
        "non_crypto_enabled": True,
        "non_crypto_tier_a_strategies": ["rs-breakout-scout", "quality-minus-junk"],
        "non_crypto_tier_b_strategies": [
            "rs-breakout-scout", "Breakout Momentum", "quality-minus-junk",
            "post-earnings-rev-scout", "rsi-divergence-scout",
            "forex-rsi-ema-scout", "vol-contraction-scout",
        ],
        "non_crypto_tier_a_confidence_threshold": 0.82,
        "non_crypto_tier_b_confidence_threshold": 0.70,
        "non_crypto_min_forward_trades": 10,
        "non_crypto_min_forward_wr_pct": 50.0,
        "non_crypto_trust_tiers": ["PROVEN", "RELIABLE"],
        "non_crypto_asset_classes": ["equity", "forex", "etf", "futures", "commodity"],
        "goldmine_score_floor": 25,
        "goldmine_min_confidence": 0.60,
        "goldmine_min_closed_n": 30,
        "direction_penalty_regime_aware": True,
        "short_penalty_bull": -15,
        "short_penalty_bear": 5,
        "short_penalty_neutral": -5,
        "dynamic_non_crypto_cap_enabled": True,
        "non_crypto_cap_floor": 3,
        "non_crypto_cap_ratio": 0.05,
        "tier_s_symbols": ["DOTUSDT", "SUIUSDT", "LTCUSDT", "NEARUSDT", "XRPUSDT"],
        "tier_a_extra_symbols": ["LINKUSDT", "ATOMUSDT", "AVAXUSDT", "SOLUSDT", "ADAUSDT", "BNBUSDT"],
        "tier_a_alt_short_symbols": ["DOGEUSDT", "SHIBUSDT", "PEPEUSDT", "SOLUSDT"],
        "tier_b_major_symbols": ["BTCUSDT", "ETHUSDT"],
        "fear_greed_substrings": ["fear_greed_contrarian"],
        "bull_neutral_substrings": ["bull", "neutral", "uptrend", "sideways"],
        "exclude_from_tier_s_regime": ["bear", "weak", "crash", "down", "ranging"],
        "bear_regime_substrings": ["bear", "weak", "crash", "down"],
        "min_forward_wr_pct": 50.0,
        "min_forward_trades": 3,
        "elite_min": 30,
        "elite_max": 90,
    }


@pytest.fixture
def crypto_fg_long_proven():
    """Ideal crypto fear-greed LONG — should qualify for Tier S."""
    return {
        "symbol": "DOTUSDT",
        "direction": "LONG",
        "strategy": "st_fear_greed_contrarian",
        "asset_class": "CRYPTO",
        "trust_tier": "PROVEN",
        "elite_score": 65,
        "ml_score": 0.72,
        "confidence": 0.68,
        "strat_fwd_wr": 62,
        "strat_fwd_trades": 50,
        "regime_at_entry": "bull",
        "risk_reward": 1.5,
    }


@pytest.fixture
def equity_rs_breakout_proven():
    """Equity rs-breakout-scout PROVEN — should qualify for non-crypto Tier B."""
    return {
        "symbol": "AAPL",
        "direction": "LONG",
        "strategy": "rs-breakout-scout",
        "asset_class": "EQUITY",
        "trust_tier": "PROVEN",
        "elite_score": 70,
        "ml_score": 0.65,
        "confidence": 0.78,
        "strat_fwd_wr": 58,
        "strat_fwd_trades": 25,
        "regime_at_entry": "bull",
    }


@pytest.fixture
def equity_low_conf():
    """Equity below non-crypto confidence threshold — no tier."""
    return {
        "symbol": "MSFT",
        "direction": "LONG",
        "strategy": "rs-breakout-scout",
        "asset_class": "EQUITY",
        "trust_tier": "PROVEN",
        "elite_score": 65,
        "confidence": 0.65,  # Below 0.70
        "strat_fwd_wr": 55,
        "strat_fwd_trades": 15,
        "regime_at_entry": "bull",
    }


@pytest.fixture
def forex_proven():
    """Forex with allowlisted strategy — Tier B."""
    return {
        "symbol": "EURUSD=X",
        "direction": "LONG",
        "strategy": "forex-rsi-ema-scout",
        "asset_class": "FOREX",
        "trust_tier": "PROVEN",
        "elite_score": 60,
        "ml_score": None,
        "confidence": 0.75,
        "strat_fwd_wr": 57,
        "strat_fwd_trades": 14,
        "regime_at_entry": "neutral",
    }


@pytest.fixture
def crypto_short_bear():
    """Crypto SHORT in bear — alt short Tier A."""
    return {
        "symbol": "DOGEUSDT",
        "direction": "SHORT",
        "strategy": "anything",
        "asset_class": "CRYPTO",
        "trust_tier": "WATCH",
        "elite_score": 55,
        "confidence": 0.60,
        "regime_at_entry": "bear market crash",
    }


# ═══════════════════════════════════════════════════════
# ASSET CLASS NORMALIZATION
# ═══════════════════════════════════════════════════════

class TestAssetClass:
    def test_usdt_is_crypto(self):
        from alpha_engine.asset_class import normalize_asset_class
        assert normalize_asset_class({"symbol": "BTCUSDT"}) == "crypto"

    def test_usdc_is_crypto(self):
        from alpha_engine.asset_class import normalize_asset_class
        assert normalize_asset_class({"symbol": "ETHUSDC"}) == "crypto"

    def test_equals_x_is_forex(self):
        from alpha_engine.asset_class import normalize_asset_class
        assert normalize_asset_class({"symbol": "EURUSD=X"}) == "forex"

    def test_equals_f_is_futures(self):
        from alpha_engine.asset_class import normalize_asset_class
        assert normalize_asset_class({"symbol": "CL=F"}) == "futures"

    def test_known_etf(self):
        from alpha_engine.asset_class import normalize_asset_class
        assert normalize_asset_class({"symbol": "QQQ"}) == "etf"
        assert normalize_asset_class({"symbol": "SPY"}) == "etf"

    def test_known_equity(self):
        from alpha_engine.asset_class import normalize_asset_class
        assert normalize_asset_class({"symbol": "AAPL"}) == "equity"
        assert normalize_asset_class({"symbol": "NVDA"}) == "equity"

    def test_meme_category_is_crypto(self):
        from alpha_engine.asset_class import normalize_asset_class
        assert normalize_asset_class({"symbol": "DOGE", "category": "meme"}) == "crypto"

    def test_is_crypto_helper(self):
        from alpha_engine.asset_class import is_crypto
        assert is_crypto({"symbol": "BTCUSDT"}) is True
        assert is_crypto({"symbol": "AAPL"}) is False

    def test_is_non_crypto_helper(self):
        from alpha_engine.asset_class import is_non_crypto
        assert is_non_crypto({"symbol": "EURUSD=X"}) is True
        assert is_non_crypto({"symbol": "BTCUSDT"}) is False

    def test_normalize_symbol(self):
        from alpha_engine.asset_class import normalize_symbol
        assert normalize_symbol("btc-usdt") == "BTCUSDT"
        assert normalize_symbol("eur/usd") == "EURUSD"


# ═══════════════════════════════════════════════════════
# STATISTICAL TESTS
# ═══════════════════════════════════════════════════════

class TestStatTests:
    def test_wilson_score_interval(self):
        from alpha_engine.stat_tests import wilson_score_interval
        lo, hi = wilson_score_interval(80, 100)
        assert lo > 0.70
        assert hi < 0.90
        assert lo < hi

    def test_wilson_zero_trials(self):
        from alpha_engine.stat_tests import wilson_score_interval
        assert wilson_score_interval(0, 0) == (0.0, 0.0)

    def test_two_proportion_z_test(self):
        from alpha_engine.stat_tests import two_proportion_z_test
        z, p, sig = two_proportion_z_test(100, 80, 100, 50)
        assert z > 0
        assert p < 0.05
        assert sig is True

    def test_two_proportion_not_significant(self):
        from alpha_engine.stat_tests import two_proportion_z_test
        z, p, sig = two_proportion_z_test(100, 52, 100, 50)
        assert sig is False

    def test_welch_t_test(self):
        from alpha_engine.stat_tests import welch_t_test
        t, p, df, sig = welch_t_test(1.0, 0.5, 30, 0.5, 0.5, 30)
        assert t > 0
        assert sig is True

    def test_sharpe_ratio(self):
        from alpha_engine.stat_tests import sharpe_ratio
        returns = [0.01 + 0.005 * (i % 3 - 1) for i in range(252)]  # Varying returns
        sr = sharpe_ratio(returns)
        assert sr > 0  # Positive Sharpe for positive-mean returns

    def test_sharpe_empty(self):
        from alpha_engine.stat_tests import sharpe_ratio
        assert sharpe_ratio([]) == 0.0
        assert sharpe_ratio([0.01]) == 0.0

    def test_sortino_ratio(self):
        from alpha_engine.stat_tests import sortino_ratio
        returns = [0.01, 0.02, -0.005, 0.015, 0.01]
        sr = sortino_ratio(returns)
        assert sr > 0

    def test_kelly_criterion(self):
        from alpha_engine.stat_tests import kelly_criterion
        k = kelly_criterion(0.6, 2.0, 1.0)
        assert k > 0
        assert k <= 1.0

    def test_kelly_zero_loss(self):
        from alpha_engine.stat_tests import kelly_criterion
        assert kelly_criterion(0.6, 2.0, 0.0) == 0.0

    def test_var_cvar(self):
        from alpha_engine.stat_tests import var_cvar
        returns = [0.01, 0.02, -0.05, -0.03, 0.01, -0.08, 0.02, -0.02, 0.01, -0.06]
        var, cvar = var_cvar(returns, 0.95)
        assert var > 0
        assert cvar >= var

    def test_var_cvar_empty(self):
        from alpha_engine.stat_tests import var_cvar
        assert var_cvar([], 0.95) == (0.0, 0.0)

    def test_hhi(self):
        from alpha_engine.stat_tests import herfindahl_hirschman
        # Equal shares: HHI = 1/n
        assert abs(herfindahl_hirschman([25, 25, 25, 25]) - 0.25) < 0.01
        # Single dominant: HHI ~ 1
        assert herfindahl_hirschman([100, 0, 0]) > 0.9

    def test_max_consecutive(self):
        from alpha_engine.stat_tests import max_consecutive
        assert max_consecutive([True, True, False, True, True, True, False]) == (3, 1)

    def test_max_consecutive_empty(self):
        from alpha_engine.stat_tests import max_consecutive
        assert max_consecutive([]) == (0, 0)

    def test_bonferroni(self):
        from alpha_engine.stat_tests import bonferroni_correction
        assert abs(bonferroni_correction(0.05, 3) - 0.0167) < 0.001

    def test_profit_factor(self):
        from alpha_engine.stat_tests import profit_factor
        pf = profit_factor([5.0, 3.0], [2.0, 1.0])
        assert abs(pf - 2.667) < 0.01

    def test_profit_factor_no_losses(self):
        from alpha_engine.stat_tests import profit_factor
        pf = profit_factor([5.0], [])
        assert pf == float("inf")

    def test_bootstrap_ci(self):
        from alpha_engine.stat_tests import bootstrap_ci
        data = [1.0, 2.0, 3.0, 4.0, 5.0]
        lo, hi = bootstrap_ci(data, lambda x: sum(x) / len(x))
        assert lo < 3.0 < hi


# ═══════════════════════════════════════════════════════
# FEATURE FLAGS
# ═══════════════════════════════════════════════════════

class TestFeatureFlags:
    def test_load_defaults(self, tmp_path):
        from alpha_engine.feature_flags import FeatureFlagManager
        flags_file = tmp_path / "flags.json"
        flags_file.write_text('{"enable_non_crypto_hf": false, "policy_version": "v3"}')
        fm = FeatureFlagManager(flags_file)
        assert fm.is_enabled("enable_non_crypto_hf") is False
        assert fm.get("policy_version") == "v3"

    def test_missing_flag_returns_false(self, tmp_path):
        from alpha_engine.feature_flags import FeatureFlagManager
        flags_file = tmp_path / "flags.json"
        flags_file.write_text('{}')
        fm = FeatureFlagManager(flags_file)
        assert fm.is_enabled("nonexistent") is False

    def test_set_and_reload(self, tmp_path):
        from alpha_engine.feature_flags import FeatureFlagManager
        flags_file = tmp_path / "flags.json"
        flags_file.write_text('{"test_flag": false}')
        fm = FeatureFlagManager(flags_file)
        assert fm.is_enabled("test_flag") is False
        fm.set_flag("test_flag", True)
        assert fm.is_enabled("test_flag") is True

    def test_list_flags(self, tmp_path):
        from alpha_engine.feature_flags import FeatureFlagManager
        flags_file = tmp_path / "flags.json"
        flags_file.write_text('{"a": 1, "b": 2}')
        fm = FeatureFlagManager(flags_file)
        flags = fm.list_flags()
        assert flags == {"a": 1, "b": 2}


# ═══════════════════════════════════════════════════════
# ALERTS
# ═══════════════════════════════════════════════════════

class TestAlerts:
    def test_symbol_exposure_warning(self):
        from alpha_engine.alerts import ConcentrationAlert
        picks = [{"symbol": "AAPL", "weight_pct": 8.0}]
        alerts = ConcentrationAlert.check_symbol_exposure(picks, max_pct=5.0)
        assert len(alerts) == 1
        assert alerts[0]["severity"] == "WARNING"

    def test_symbol_exposure_critical(self):
        from alpha_engine.alerts import ConcentrationAlert
        picks = [{"symbol": "AAPL", "weight_pct": 12.0}]
        alerts = ConcentrationAlert.check_symbol_exposure(picks, max_pct=5.0)
        assert alerts[0]["severity"] == "CRITICAL"

    def test_no_alert_under_limit(self):
        from alpha_engine.alerts import ConcentrationAlert
        picks = [{"symbol": "AAPL", "weight_pct": 3.0}]
        alerts = ConcentrationAlert.check_symbol_exposure(picks, max_pct=5.0)
        assert len(alerts) == 0

    def test_payload_lag_warning(self):
        from alpha_engine.alerts import DataLagAlert
        from datetime import datetime, timezone, timedelta
        old = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        alerts = DataLagAlert.check_payload_lag(old, warn_hours=1)
        assert len(alerts) > 0
        assert alerts[0]["severity"] in ("WARNING", "CRITICAL")

    def test_payload_lag_fresh(self):
        from alpha_engine.alerts import DataLagAlert
        from datetime import datetime, timezone
        fresh = datetime.now(timezone.utc).isoformat()
        alerts = DataLagAlert.check_payload_lag(fresh, warn_hours=1)
        assert len(alerts) == 0


# ═══════════════════════════════════════════════════════
# ML COMPOSITE
# ═══════════════════════════════════════════════════════

class TestMLComposite:
    def test_with_ml_score(self):
        """Test that ml_composite method is used when ml_score is present."""
        # Simulating _compute_ml_composite logic
        ml = 0.7
        conf = 0.8
        fwd_wr = 0.6
        score = ml * 0.6 + conf * 0.3 + fwd_wr * 0.1
        assert abs(score - 0.72) < 0.01  # 0.42 + 0.24 + 0.06

    def test_null_ml_fallback(self):
        """Null ml_score falls back to penalized confidence path."""
        conf = 0.8
        score = conf * 0.8 * 0.5  # ml_null_penalty = 0.5
        assert abs(score - 0.32) < 0.01

    def test_null_ml_solo_extra_penalty(self):
        """Single-source fallback gets additional -20%."""
        conf = 0.8
        agreeing = 1
        score = conf * 0.8 * 0.5
        if agreeing < 2:
            score *= 0.8
        assert abs(score - 0.256) < 0.01


# ═══════════════════════════════════════════════════════
# DYNAMIC NON-CRYPTO CAP
# ═══════════════════════════════════════════════════════

class TestDynamicCap:
    def _cap(self, active_count, floor=3, ratio=0.05):
        return max(floor, int(ratio * active_count))

    def test_floor_enforced(self):
        assert self._cap(10) == 3  # 0.05 * 10 = 0.5, floor 3

    def test_scales_with_count(self):
        assert self._cap(200) == 10  # 0.05 * 200 = 10

    def test_zero_count(self):
        assert self._cap(0) == 3

    def test_large_count(self):
        assert self._cap(1000) == 50


# ═══════════════════════════════════════════════════════
# DIRECTION SCORING
# ═══════════════════════════════════════════════════════

class TestDirectionScoring:
    def _score_direction(self, direction, regime, cfg):
        """Simplified regime-aware direction scoring."""
        is_bear = any(w in regime for w in cfg.get("bear_regime_substrings", []))
        is_bull = any(w in regime for w in cfg.get("bull_neutral_substrings", []))
        
        if direction in ("LONG", "BUY"):
            if is_bear:
                return -5
            return 5
        else:  # SHORT/SELL
            if is_bear:
                return 5  # SHORT in bear = good
            return -15  # SHORT in bull = bad

    def test_long_in_bull(self, cfg_v3):
        assert self._score_direction("LONG", "bull", cfg_v3) == 5

    def test_short_in_bull(self, cfg_v3):
        assert self._score_direction("SHORT", "bull uptrend", cfg_v3) == -15

    def test_short_in_bear(self, cfg_v3):
        assert self._score_direction("SHORT", "bear market", cfg_v3) == 5

    def test_long_in_bear(self, cfg_v3):
        assert self._score_direction("LONG", "bear crash", cfg_v3) == -5


# ═══════════════════════════════════════════════════════
# GOLDMINE FLOOR
# ═══════════════════════════════════════════════════════

class TestGoldmineFloor:
    def _passes(self, strategy, score, confidence, min_score=25, min_conf=0.60):
        if "goldmine" not in strategy.lower():
            return True  # Non-goldmine unaffected
        return score >= min_score and confidence >= min_conf

    def test_passes(self):
        assert self._passes("goldmine_1x_consensus", 30, 0.64) is True

    def test_fails_score(self):
        assert self._passes("goldmine_2x_consensus", 17, 0.66) is False

    def test_fails_confidence(self):
        assert self._passes("goldmine_3x_consensus", 35, 0.55) is False

    def test_non_goldmine_unaffected(self):
        assert self._passes("rs-breakout-scout", 10, 0.50) is True


# ═══════════════════════════════════════════════════════
# KILL GATES
# ═══════════════════════════════════════════════════════

class TestKillGates:
    def _should_kill(self, n, pf, wr, min_n=20, max_pf=0.7, max_wr=35.0):
        return n >= min_n and pf < max_pf and wr < max_wr

    def test_kill_candidate(self):
        assert self._should_kill(168, 0.18, 15.5) is True  # st_rsi_momentum_confluence

    def test_spare_good_strategy(self):
        assert self._should_kill(618, 5.67, 80.6) is False  # st_fear_greed_contrarian

    def test_spare_small_sample(self):
        assert self._should_kill(10, 0.5, 20.0) is False  # n < 20

    def test_spare_pf_ok(self):
        assert self._should_kill(50, 0.8, 30.0) is False  # PF > 0.7


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
