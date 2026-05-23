"""
Integration tests for the full picks routing pipeline.

Tests the end-to-end flow: signal -> validation -> scoring -> routing -> caps.
Uses mocked Discord webhooks (no actual HTTP calls).
"""
import sys
import json
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

sys.path.insert(0, '.')


class TestPicksRouterIntegration:
    """End-to-end tests for the picks routing pipeline."""

    def _make_signal(self, **overrides):
        """Create a valid test signal with sensible defaults."""
        base = {
            "symbol": "BTCUSDT",
            "direction": "BUY",
            "confidence": 0.75,
            "system": "test_system",
            "strategy": "funding_carry",  # must be a core strategy in core_whitelist.json
            "entry_price": 60000,
            "tp_price": 63000,
            "sl_price": 58800,
            "timeframe": "1h",
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "consensus_score": 0.7,
            "consensus_count": 2,
            "agreeing_systems": ["alpha_engine", "mercury2"],
        }
        base.update(overrides)
        return base

    @patch("signal_aggregator.picks_router.PRICE_FETCHER_AVAILABLE", False)
    def test_high_confidence_routes_to_master(self):
        """Signal with conf >= 0.80 + consensus should route to master_picks.

        We mock _score_signal to return a non-F grade because the Monte Carlo
        scorer is stochastic and could randomly produce an F, causing a
        non-deterministic downgrade.
        """
        from signal_aggregator.picks_router import PicksRouter
        router = PicksRouter()
        signal = self._make_signal(confidence=0.85, consensus_count=3, consensus_score=0.75)
        # Deterministic: mock _score_signal to avoid stochastic MC downgrade
        with patch.object(router, "_score_signal", side_effect=lambda s: s.update({"mc_grade": "B"}) or s):
            channel = router.route_signal(signal)
        assert channel == "master_picks", f"Expected master_picks, got {channel}"

    @patch("signal_aggregator.picks_router.PRICE_FETCHER_AVAILABLE", False)
    def test_medium_confidence_routes_to_freshpicks(self):
        """Typical mid-band confidence (0.70) routes to freshpicks under current thresholds."""
        from signal_aggregator.picks_router import PicksRouter
        router = PicksRouter()
        signal = self._make_signal(confidence=0.70)
        channel = router.route_signal(signal)
        assert channel == "freshpicks", f"Expected freshpicks, got {channel}"

    @patch("signal_aggregator.picks_router.PRICE_FETCHER_AVAILABLE", False)
    def test_low_confidence_routes_to_sandbox(self):
        """Below FRESHPICKS_THRESHOLD (0.62) routes to sandbox."""
        from signal_aggregator.picks_router import PicksRouter

        router = PicksRouter()
        signal = self._make_signal(confidence=0.50)
        channel = router.route_signal(signal)
        assert channel == "sandbox", f"Expected sandbox, got {channel}"

    @patch("signal_aggregator.picks_router.PRICE_FETCHER_AVAILABLE", False)
    def test_threshold_raised_to_062(self):
        """Confidence 0.61 should go to sandbox (freshpicks floor 0.62)."""
        from signal_aggregator.picks_router import PicksRouter

        router = PicksRouter()
        signal = self._make_signal(confidence=0.61)
        channel = router.route_signal(signal)
        assert channel == "sandbox", f"0.61 should be below freshpicks threshold, got {channel}"

    @patch("signal_aggregator.picks_router.PRICE_FETCHER_AVAILABLE", False)
    def test_circuit_breaker_red_blocks_everything(self):
        """RED circuit breaker should route everything to sandbox."""
        from signal_aggregator.picks_router import PicksRouter
        from risk_management.portfolio_circuit_breaker import PortfolioCircuitBreaker

        router = PicksRouter()
        # Create a RED status: need DD between 5% and 8% from peak
        # Peak = 10500, current = 9950 => DD = 550/10500 = 5.24% => RED
        cb = PortfolioCircuitBreaker(portfolio_value=10000.0)
        status = cb.check([10000.0, 10500.0, 9950.0])
        assert status.level == "RED", f"Expected RED, got {status.level} (DD={status.current_dd})"

        signal = self._make_signal(confidence=0.90, consensus_count=5)
        channel = router.route_signal(signal, _cb_status=status)
        assert channel == "sandbox", f"RED breaker should route to sandbox, got {channel}"

    @patch("signal_aggregator.picks_router.PRICE_FETCHER_AVAILABLE", False)
    def test_circuit_breaker_green_passes_through(self):
        """GREEN circuit breaker should not interfere with routing."""
        from signal_aggregator.picks_router import PicksRouter
        from risk_management.portfolio_circuit_breaker import PortfolioCircuitBreaker

        router = PicksRouter()
        cb = PortfolioCircuitBreaker(portfolio_value=100.0)
        status = cb.check([100.0, 101.0, 102.0])  # rising equity = GREEN

        signal = self._make_signal(confidence=0.70)
        channel = router.route_signal(signal, _cb_status=status)
        assert channel == "freshpicks", f"GREEN breaker should allow through, got {channel}"

    def test_get_max_picks_centralized(self):
        """get_max_picks should return correct caps for each level."""
        from signal_aggregator.picks_router import PicksRouter

        green = PicksRouter.get_max_picks("GREEN")
        assert green == {"master": 5, "fresh": 10, "send_allowed": True}

        yellow = PicksRouter.get_max_picks("YELLOW")
        assert yellow == {"master": 2, "fresh": 5, "send_allowed": True}

        red = PicksRouter.get_max_picks("RED")
        assert red == {"master": 0, "fresh": 0, "send_allowed": False}

        halt = PicksRouter.get_max_picks("HALT")
        assert halt == {"master": 0, "fresh": 0, "send_allowed": False}

    @patch("signal_aggregator.picks_router.PRICE_FETCHER_AVAILABLE", False)
    def test_mc_scorer_enriches_signal(self):
        """Monte Carlo scorer should add mc_grade to the signal dict."""
        from signal_aggregator.picks_router import PicksRouter
        router = PicksRouter()
        signal = self._make_signal(confidence=0.70)
        router._score_signal(signal)
        assert "mc_grade" in signal, "Signal should be enriched with mc_grade"

    @patch("signal_aggregator.picks_router.PRICE_FETCHER_AVAILABLE", False)
    def test_mc_grade_f_downgrades_master(self):
        """F-grade MC score should downgrade master_picks to freshpicks."""
        from signal_aggregator.picks_router import PicksRouter
        router = PicksRouter()
        signal = self._make_signal(
            confidence=0.85,
            consensus_count=3,
            consensus_score=0.75,
            entry_price=60000,
            tp_price=60100,   # tiny target (0.17%)
            sl_price=54000,   # huge stop (10%)
        )
        channel = router.route_signal(signal)
        # With such terrible RR (0.017), MC should grade F and downgrade
        assert channel in ("freshpicks", "master_picks"), f"Unexpected channel: {channel}"
        # If MC scoring is working, this should be freshpicks due to downgrade
        if signal.get("mc_grade") == "F":
            assert channel == "freshpicks", "F-grade should downgrade master to freshpicks"

    @patch("signal_aggregator.picks_router.PRICE_FETCHER_AVAILABLE", False)
    def test_stale_signal_goes_to_sandbox(self):
        """Signal older than 15 minutes should go to sandbox."""
        from signal_aggregator.picks_router import PicksRouter
        router = PicksRouter()
        signal = self._make_signal(
            confidence=0.85,
            timestamp="2020-01-01T00:00:00Z",  # very old
        )
        channel = router.route_signal(signal)
        assert channel == "sandbox", f"Stale signal should go to sandbox, got {channel}"

    @patch("signal_aggregator.picks_router.PRICE_FETCHER_AVAILABLE", False)
    def test_missing_tp_sl_still_routes(self):
        """No TP/SL: MC skipped; high conf can still route (often master when >= MASTER threshold)."""
        from signal_aggregator.picks_router import PicksRouter

        router = PicksRouter()
        signal = self._make_signal(
            confidence=0.70,
            tp_price=None,
            sl_price=None,
        )
        channel = router.route_signal(signal)
        assert channel in (
            "freshpicks",
            "master_picks",
            "incubator",
        ), f"Expected a live channel without TP/SL, got {channel}"

    def test_max_open_positions_defined(self):
        """MAX_OPEN_POSITIONS caps concurrent sends (production default 15)."""
        from signal_aggregator.picks_router import PicksRouter

        assert hasattr(PicksRouter, "MAX_OPEN_POSITIONS")
        assert PicksRouter.MAX_OPEN_POSITIONS <= 15


class TestCircuitBreakerScenarios:
    """Test circuit breaker with synthetic equity curves."""

    def test_green_flat_equity(self):
        from risk_management.portfolio_circuit_breaker import PortfolioCircuitBreaker
        cb = PortfolioCircuitBreaker(portfolio_value=10000.0)
        status = cb.check([10000.0] * 20)
        assert status.level == "GREEN"

    def test_green_rising_equity(self):
        from risk_management.portfolio_circuit_breaker import PortfolioCircuitBreaker
        cb = PortfolioCircuitBreaker(portfolio_value=10000.0)
        curve = [10000.0 + i * 50 for i in range(20)]
        status = cb.check(curve)
        assert status.level == "GREEN"

    def test_yellow_moderate_drawdown(self):
        """DD between 3% and 5% from peak should trigger YELLOW."""
        from risk_management.portfolio_circuit_breaker import PortfolioCircuitBreaker
        cb = PortfolioCircuitBreaker(portfolio_value=10000.0)
        # Peak = 10500, current = 10100 => DD = 400/10500 = 3.81% => YELLOW
        status = cb.check([10000.0, 10500.0, 10100.0])
        assert status.level == "YELLOW", f"Expected YELLOW, got {status.level} (DD={status.current_dd})"

    def test_red_significant_drawdown(self):
        """DD between 5% and 8% from peak should trigger RED."""
        from risk_management.portfolio_circuit_breaker import PortfolioCircuitBreaker
        cb = PortfolioCircuitBreaker(portfolio_value=10000.0)
        # Peak = 10500, current = 9950 => DD = 550/10500 = 5.24% => RED
        status = cb.check([10000.0, 10500.0, 9950.0])
        assert status.level == "RED", f"Expected RED, got {status.level} (DD={status.current_dd})"

    def test_halt_severe_drawdown(self):
        """DD >= 8% from peak should trigger HALT."""
        from risk_management.portfolio_circuit_breaker import PortfolioCircuitBreaker
        cb = PortfolioCircuitBreaker(portfolio_value=10000.0)
        # Peak = 10500, current = 9600 => DD = 900/10500 = 8.57% => HALT
        status = cb.check([10000.0, 10500.0, 9600.0])
        assert status.level == "HALT", f"Expected HALT, got {status.level} (DD={status.current_dd})"

    def test_empty_curve_green(self):
        from risk_management.portfolio_circuit_breaker import PortfolioCircuitBreaker
        cb = PortfolioCircuitBreaker(portfolio_value=10000.0)
        status = cb.check([])
        assert status.level == "GREEN"


class TestPretradeScorer:
    """Test the Monte Carlo pre-trade scorer independently."""

    def test_good_rr_signal(self):
        from risk_management.pretrade_scorer import score_signal
        result = score_signal(
            symbol="BTCUSDT", entry_price=60000,
            target_price=63000, stop_price=58800,
            vol_override=0.015, n_sims=500,
        )
        assert result["grade"] in ("A", "B", "C"), f"Good RR should not be F: {result}"
        assert result["rr_ratio"] >= 2.0

    def test_terrible_rr_signal(self):
        from risk_management.pretrade_scorer import score_signal
        result = score_signal(
            symbol="BTCUSDT", entry_price=60000,
            target_price=60100, stop_price=54000,
            vol_override=0.02, n_sims=500,
        )
        assert result["grade"] == "F"

    def test_short_signal(self):
        from risk_management.pretrade_scorer import score_signal
        result = score_signal(
            symbol="ETHUSDT", entry_price=3000,
            target_price=2850, stop_price=3060,
            direction="SELL", vol_override=0.02, n_sims=500,
        )
        assert result["rr_ratio"] >= 2.0
        assert "prob_tp" in result


class TestCryptoVolForecaster:
    """Test the volatility forecaster adapter."""

    def test_cache_and_fallback(self, monkeypatch):
        import risk_management.crypto_vol_forecaster as cvf
        import pandas as pd
        import numpy as np

        cvf.clear_cache()
        monkeypatch.setattr(cvf, "HAS_ARCH", False)

        def mock_fetch(pair, interval="1h", limit=500):
            np.random.seed(42)
            prices = 100 * np.exp(np.cumsum(np.random.normal(0, 0.02, limit)))
            return pd.DataFrame({"Close": prices})

        import ml_battleground.shared.data_fetcher as df_mod
        monkeypatch.setattr(df_mod, "fetch_single", mock_fetch)

        vol = cvf.forecast_crypto_vol("BTCUSDT")
        assert 0.005 <= vol <= 0.50
