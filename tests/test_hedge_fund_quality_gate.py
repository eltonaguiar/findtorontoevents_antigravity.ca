"""Tests for alpha_engine.hedge_fund_quality_gate."""
from __future__ import annotations

import pytest

from alpha_engine.hedge_fund_quality_gate import (
    batch_evaluate,
    passes_hedge_fund_gate,
    why_rejected,
)


def _p(**kwargs):
    base = {"asset_class": "CRYPTO", "symbol": "BTCUSDT", "strategy": "ok", "signal_type": "LONG", "confidence": 0.75}
    base.update(kwargs)
    return base


class TestCrypto:
    def test_banned_symbol_rejects(self):
        ok, reason = passes_hedge_fund_gate(_p(symbol="DOGEUSDT"))
        assert not ok
        assert "DOGEUSDT" in reason

    def test_good_crypto_pick_passes(self):
        ok, _ = passes_hedge_fund_gate(_p(symbol="NEARUSDT", confidence=0.75))
        assert ok

    def test_dead_band_rejects(self):
        ok, reason = passes_hedge_fund_gate(_p(confidence=0.65))
        assert not ok
        assert "dead band" in reason

    def test_dead_band_lower_bound_inclusive(self):
        ok, _ = passes_hedge_fund_gate(_p(confidence=0.60))
        assert not ok

    def test_dead_band_upper_bound_exclusive(self):
        ok, _ = passes_hedge_fund_gate(_p(confidence=0.70))
        assert ok

    def test_banned_strategy_rejects(self):
        ok, reason = passes_hedge_fund_gate(_p(strategy="macd_rsi_confluence"))
        assert not ok
        assert "macd_rsi_confluence" in reason


class TestEquity:
    def test_short_rejected(self):
        ok, reason = passes_hedge_fund_gate(_p(asset_class="EQUITY", symbol="CVX", signal_type="SHORT"))
        assert not ok
        assert "SHORT" in reason

    def test_long_passes(self):
        ok, _ = passes_hedge_fund_gate(_p(asset_class="EQUITY", symbol="CVX", signal_type="LONG", confidence=0.5))
        assert ok

    def test_aapl_passes(self):
        # 2026-05-16: AAPL un-banned. Original ban was below 30-pick charter minimum.
        # fwd_wr=73.0% (forward_validated=True), n=17, PF=1.03 — marginal but not sub-floor.
        ok, _ = passes_hedge_fund_gate(_p(asset_class="EQUITY", symbol="AAPL", signal_type="LONG"))
        assert ok

    def test_equity_reject_band_confidence_rejects(self):
        # Structural: confidence [0.60, 0.65) is the active EQUITY danger zone.
        ok, reason = passes_hedge_fund_gate(_p(asset_class="EQUITY", symbol="AAPL", signal_type="LONG", confidence=0.62))
        assert not ok
        assert "reject band" in reason

    def test_classic_momentum_rejected(self):
        ok, reason = passes_hedge_fund_gate(_p(asset_class="EQUITY", symbol="CVX", strategy="Classic Momentum"))
        assert not ok
        assert "Classic Momentum" in reason

    def test_equity_reject_band_0_60_0_65_rejects(self):
        # EQUITY [0.60, 0.65): n=52, WR 35.3%, cum -28.1%.
        ok, reason = passes_hedge_fund_gate(
            _p(asset_class="EQUITY", symbol="CVX", signal_type="LONG", confidence=0.62)
        )
        assert not ok
        assert "reject band" in reason

    def test_equity_reject_band_lower_bound_inclusive(self):
        ok, reason = passes_hedge_fund_gate(
            _p(asset_class="EQUITY", symbol="CVX", signal_type="LONG", confidence=0.60)
        )
        assert not ok
        assert "reject band" in reason

    def test_equity_reject_band_upper_bound_exclusive(self):
        # 0.65 is NOT in the reject band; next bucket (0.65-0.70) is strong (+31% cum)
        ok, _ = passes_hedge_fund_gate(
            _p(asset_class="EQUITY", symbol="CVX", signal_type="LONG", confidence=0.65)
        )
        assert ok

    def test_equity_below_reject_band_passes(self):
        # EQUITY <0.60 is the strongest bucket (+167% cum on n=176)
        ok, _ = passes_hedge_fund_gate(
            _p(asset_class="EQUITY", symbol="CVX", signal_type="LONG", confidence=0.55)
        )
        assert ok

    def test_equity_missing_confidence_allowed(self):
        p = _p(asset_class="EQUITY", symbol="CVX", signal_type="LONG")
        p.pop("confidence", None)
        ok, _ = passes_hedge_fund_gate(p)
        assert ok


class TestCommodity:
    def test_broken_strategy_rejects(self):
        ok, reason = passes_hedge_fund_gate(_p(asset_class="COMMODITY", strategy="cta_commodity_momentum_term", confidence=0.8))
        assert not ok
        assert "cta_commodity_momentum_term" in reason

    def test_low_confidence_rejects(self):
        ok, reason = passes_hedge_fund_gate(_p(asset_class="COMMODITY", strategy="futures_momentum", confidence=0.65))
        assert not ok
        assert "confidence" in reason

    def test_high_confidence_passes(self):
        ok, _ = passes_hedge_fund_gate(_p(asset_class="COMMODITY", strategy="futures_momentum", confidence=0.75))
        assert ok

    def test_missing_confidence_allowed(self):
        # No confidence field: don't artificially reject (gate is additive).
        p = _p(asset_class="COMMODITY", strategy="futures_momentum")
        p.pop("confidence")
        ok, _ = passes_hedge_fund_gate(p)
        assert ok


class TestForex:
    def test_drag_symbol_rejected(self):
        ok, reason = passes_hedge_fund_gate(_p(asset_class="FOREX", symbol="EURJPY=X"))
        assert not ok
        assert "EURJPY=X" in reason

    def test_good_forex_passes(self):
        ok, _ = passes_hedge_fund_gate(_p(asset_class="FOREX", symbol="USDJPY=X"))
        assert ok

    def test_forex_overconfidence_band_rejects_0_95(self):
        # FOREX [0.95, 1.0001): n=38, WR 39.5%, cum -30.3%.
        ok, reason = passes_hedge_fund_gate(
            _p(asset_class="FOREX", symbol="USDJPY=X", confidence=0.96)
        )
        assert not ok
        assert "overconfidence trap" in reason

    def test_forex_overconfidence_band_rejects_1_00(self):
        ok, reason = passes_hedge_fund_gate(
            _p(asset_class="FOREX", symbol="USDJPY=X", confidence=1.00)
        )
        assert not ok
        assert "overconfidence trap" in reason

    def test_forex_below_overconfidence_band_passes(self):
        ok, _ = passes_hedge_fund_gate(
            _p(asset_class="FOREX", symbol="USDJPY=X", confidence=0.94)
        )
        assert ok

    def test_forex_missing_confidence_allowed(self):
        p = _p(asset_class="FOREX", symbol="USDJPY=X")
        p.pop("confidence", None)
        ok, _ = passes_hedge_fund_gate(p)
        assert ok

    def test_forex_breakout_momentum_rejected(self):
        # "Breakout Momentum" on FOREX: n=20, 45% WR, -0.551% avg in recent 790.
        ok, reason = passes_hedge_fund_gate(
            _p(asset_class="FOREX", symbol="USDJPY=X", strategy="Breakout Momentum")
        )
        assert not ok
        assert "Breakout Momentum" in reason

    def test_breakout_momentum_allowed_on_equity(self):
        # Same strategy is a positive contributor on EQUITY (37 picks, 59.5% WR)
        # and must still pass the gate there. Use confidence=0.55 to stay clear
        # of the new EQUITY reject band [0.60, 0.65).
        ok, _ = passes_hedge_fund_gate(
            _p(asset_class="EQUITY", symbol="CVX", signal_type="LONG",
               strategy="Breakout Momentum", confidence=0.55)
        )
        assert ok


class TestPipelineHygiene:
    def test_empty_strategy_rejected_forex(self):
        ok, reason = passes_hedge_fund_gate(
            _p(asset_class="FOREX", symbol="USDJPY=X", strategy="")
        )
        assert not ok
        assert "empty strategy" in reason

    def test_empty_strategy_rejected_crypto(self):
        # Cross-AC guard: empty strategy is a pipeline defect anywhere.
        ok, reason = passes_hedge_fund_gate(
            _p(asset_class="CRYPTO", symbol="BTCUSDT", strategy="", confidence=0.75)
        )
        assert not ok
        assert "empty strategy" in reason

    def test_whitespace_only_strategy_rejected(self):
        ok, reason = passes_hedge_fund_gate(
            _p(asset_class="EQUITY", symbol="CVX", signal_type="LONG", strategy="   ")
        )
        assert not ok
        assert "empty strategy" in reason

    def test_missing_strategy_key_rejected(self):
        p = _p(asset_class="EQUITY", symbol="CVX", signal_type="LONG")
        p.pop("strategy")
        ok, reason = passes_hedge_fund_gate(p)
        assert not ok
        assert "empty strategy" in reason


class TestETFAndBond:
    def test_etf_drag_rejected(self):
        ok, reason = passes_hedge_fund_gate(_p(asset_class="ETF", symbol="IWM"))
        assert not ok
        assert "IWM" in reason

    def test_etf_good_passes(self):
        ok, _ = passes_hedge_fund_gate(_p(asset_class="ETF", symbol="QQQ"))
        assert ok

    def test_bond_passes_regardless(self):
        # Sample too small; gate allows everything in BOND.
        ok, _ = passes_hedge_fund_gate(_p(asset_class="BOND", symbol="TLT"))
        assert ok


class TestAliasesAndDefensive:
    def test_stocks_alias_maps_to_equity(self):
        # asset_class "STOCKS" should behave as EQUITY — verify via confidence reject band.
        ok, reason = passes_hedge_fund_gate(_p(asset_class="STOCKS", symbol="CVX", signal_type="LONG", confidence=0.62))
        assert not ok
        assert "reject band" in reason

    def test_etfs_alias_maps_to_etf(self):
        ok, _ = passes_hedge_fund_gate(_p(asset_class="ETFS", symbol="IWM"))
        assert not ok

    def test_unknown_asset_class_allows(self):
        ok, _ = passes_hedge_fund_gate(_p(asset_class="SPORTS", symbol="NYY"))
        assert ok

    def test_why_rejected_returns_none_when_ok(self):
        assert why_rejected(_p(symbol="BTCUSDT", confidence=0.75)) is None

    def test_why_rejected_returns_reason(self):
        r = why_rejected(_p(symbol="DOGEUSDT"))
        assert r and "DOGEUSDT" in r


class TestBatch:
    def test_batch_evaluate_counts(self):
        # 2026-05-16: AAPL un-banned; use confidence reject band to create a rejected EQUITY pick.
        picks = [
            _p(symbol="NEARUSDT", confidence=0.75),
            _p(symbol="DOGEUSDT"),
            _p(asset_class="EQUITY", symbol="CVX", signal_type="LONG", confidence=0.62),  # reject band
            _p(asset_class="EQUITY", symbol="CVX", signal_type="LONG"),
        ]
        result = batch_evaluate(picks)
        assert result["total"] == 4
        assert result["kept"] == 2
        assert result["rejected"] == 2
        assert result["by_asset_class"]["CRYPTO"]["kept"] == 1
        assert result["by_asset_class"]["CRYPTO"]["rejected"] == 1
        assert result["by_asset_class"]["EQUITY"]["kept"] == 1
        assert result["by_asset_class"]["EQUITY"]["rejected"] == 1
        assert len(result["rejection_reasons"]) >= 1


class TestMLPumpProbability:
    """Claude ML's pump_probability has a non-monotonic edge: mid [0.35, 0.50) profitable,
    high (>=0.50) net-negative, low (<0.35) also weak. See reports/LATENT_FEATURES_AND_PIPELINE_EXTENSION_2026_04_22.md."""

    def test_ml_sweet_spot_passes(self):
        ok, _ = passes_hedge_fund_gate(_p(
            source_system="claude_gainer_st", strategy="claude_gainer_st",
            pump_probability=0.42, confidence=0.75,
        ))
        assert ok

    def test_ml_high_pump_rejects(self):
        ok, reason = passes_hedge_fund_gate(_p(
            source_system="claude_gainer_st", strategy="claude_gainer_st",
            pump_probability=0.60, confidence=0.75,
        ))
        assert not ok
        assert "overconfidence" in reason.lower() or "0.50" in reason

    def test_ml_very_high_pump_rejects(self):
        ok, reason = passes_hedge_fund_gate(_p(
            source_system="claude_gainer_st", strategy="claude_gainer_st",
            pump_probability=0.80, confidence=0.75,
        ))
        assert not ok
        assert "0.50" in reason

    def test_ml_low_pump_rejects(self):
        ok, reason = passes_hedge_fund_gate(_p(
            source_system="claude_gainer_st", strategy="claude_gainer_st",
            pump_probability=0.20, confidence=0.75,
        ))
        assert not ok
        assert "0.35" in reason or "floor" in reason.lower()

    def test_ml_boundary_lower_inclusive(self):
        """0.35 should pass (>= floor)."""
        ok, _ = passes_hedge_fund_gate(_p(
            source_system="claude_gainer_st", strategy="claude_gainer_st",
            pump_probability=0.35, confidence=0.75,
        ))
        assert ok

    def test_ml_boundary_upper_exclusive(self):
        """0.50 should reject (>= ceiling)."""
        ok, reason = passes_hedge_fund_gate(_p(
            source_system="claude_gainer_st", strategy="claude_gainer_st",
            pump_probability=0.50, confidence=0.75,
        ))
        assert not ok
        assert "0.50" in reason

    def test_non_ml_source_skips_pump_check(self):
        """A normal pick without pump_probability must not get rejected by the ML check."""
        ok, _ = passes_hedge_fund_gate(_p(
            source_system="quan_engine", strategy="ok", confidence=0.75,
        ))
        assert ok

    def test_pump_prob_on_unknown_source_still_checked(self):
        """Any pick carrying pump_probability counts as ML-sourced even without source_system match."""
        ok, reason = passes_hedge_fund_gate(_p(
            source_system="weird_new_source", strategy="whatever",
            pump_probability=0.85, confidence=0.75,
        ))
        assert not ok
        assert "0.50" in reason


class TestCryptoRSI4hKillzone:
    """CRYPTO RSI-4h killzone DISABLED 2026-04-28 (writer artifact, see
    `reports/crypto_rsi4h_killzone_review_2026_04_28.md`).
    Default LO=HI=0 so `LO <= rsi4h < HI` is the empty interval.
    Tests now assert disabled-by-default; legacy reject behavior is covered
    by tests/test_crypto_rsi4h_disable.py via env-var override."""

    def test_rsi_4h_in_old_killzone_passes_by_default(self):
        # Was previously a reject at RSI=50 ([40,60) killzone). Now passes.
        ok, _ = passes_hedge_fund_gate(_p(
            symbol="BTCUSDT", confidence=0.75, technical_rsi_4h=50.0,
        ))
        assert ok

    def test_rsi_4h_below_old_killzone_passes(self):
        ok, _ = passes_hedge_fund_gate(_p(
            symbol="BTCUSDT", confidence=0.75, technical_rsi_4h=35.0,
        ))
        assert ok

    def test_rsi_4h_above_old_killzone_passes(self):
        ok, _ = passes_hedge_fund_gate(_p(
            symbol="BTCUSDT", confidence=0.75, technical_rsi_4h=65.0,
        ))
        assert ok

    def test_rsi_4h_old_lower_bound_passes_by_default(self):
        # 40.0 was previously rejected. Now passes (killzone disabled).
        ok, _ = passes_hedge_fund_gate(_p(
            symbol="BTCUSDT", confidence=0.75, technical_rsi_4h=40.0,
        ))
        assert ok

    def test_rsi_4h_old_upper_bound_passes(self):
        ok, _ = passes_hedge_fund_gate(_p(
            symbol="BTCUSDT", confidence=0.75, technical_rsi_4h=60.0,
        ))
        assert ok

    def test_rsi_killzone_does_not_apply_to_non_crypto(self):
        """Non-crypto picks with RSI 4h = 50 should still pass (rule is crypto-only)."""
        ok, _ = passes_hedge_fund_gate(_p(
            asset_class="EQUITY", symbol="CVX", signal_type="LONG",
            technical_rsi_4h=50.0, confidence=0.5,
        ))
        assert ok

    def test_missing_rsi_does_not_reject(self):
        """Picks without technical_rsi_4h pass the RSI check."""
        p = _p(symbol="BTCUSDT", confidence=0.75)
        p.pop("technical_rsi_4h", None)
        ok, _ = passes_hedge_fund_gate(p)
        assert ok

class TestCryptoRSI1hOverbought:
    """CRYPTO RSI-1h strong+overbought bands have catastrophic realized PF.
    Per tools/edge_latent_features.py on closed_picks (2026-04-23):
      strong_60_70:     n=322, PF 0.57
      overbought_70_80: n=54,  PF 0.13
    Reject rsi_1h >= 60 on crypto."""

    def test_rsi_1h_overbought_rejects(self):
        ok, reason = passes_hedge_fund_gate(_p(
            symbol="BTCUSDT", confidence=0.75, technical_rsi_1h=75.0,
        ))
        assert not ok
        assert "rsi_1h" in reason and "overbought" in reason.lower()

    def test_rsi_1h_strong_rejects(self):
        ok, reason = passes_hedge_fund_gate(_p(
            symbol="BTCUSDT", confidence=0.75, technical_rsi_1h=65.0,
        ))
        assert not ok
        assert "60" in reason

    def test_rsi_1h_boundary_inclusive(self):
        ok, _ = passes_hedge_fund_gate(_p(
            symbol="BTCUSDT", confidence=0.75, technical_rsi_1h=60.0,
        ))
        assert not ok

    def test_rsi_1h_below_threshold_passes(self):
        ok, _ = passes_hedge_fund_gate(_p(
            symbol="BTCUSDT", confidence=0.75, technical_rsi_1h=59.9,
        ))
        assert ok

    def test_rsi_1h_neutral_passes(self):
        ok, _ = passes_hedge_fund_gate(_p(
            symbol="BTCUSDT", confidence=0.75, technical_rsi_1h=45.0,
        ))
        assert ok

    def test_rsi_1h_killzone_does_not_apply_to_non_crypto(self):
        ok, _ = passes_hedge_fund_gate(_p(
            asset_class="FOREX", symbol="USDJPY=X", technical_rsi_1h=80.0,
        ))
        assert ok

    def test_rsi_1h_missing_passes(self):
        p = _p(symbol="BTCUSDT", confidence=0.75)
        p.pop("technical_rsi_1h", None)
        ok, _ = passes_hedge_fund_gate(p)
        assert ok

    def test_rsi_1h_env_const_present(self):
        from alpha_engine import hedge_fund_quality_gate
        assert hasattr(hedge_fund_quality_gate, "CRYPTO_RSI1H_OVERBOUGHT_MIN")
        assert float(hedge_fund_quality_gate.CRYPTO_RSI1H_OVERBOUGHT_MIN) == 60.0


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
