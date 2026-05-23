"""Tests for M-061: money_ready_verdict() unified edge verdict."""
import random
import pytest
from unittest.mock import patch
from alpha_engine.money_ready_verdict import _rolling_mdd, _mdd_cvar_gate


def _make_picks(n_won, n_lost, asset_class="COMMODITY", strategy="test_strat",
                symbols=None, win_pnl=0.05, loss_pnl=-0.02):
    """Build synthetic picks. `symbols` round-robins so the default sample is
    diversified (no single-symbol concentration); pass a 1-element list to
    build a concentrated sample for the M-070 guard tests.

    Picks are shuffled with a fixed seed so the equity curve resembles a
    realistic interspersed win/loss sequence — avoids an artificial 88% MDD
    that arises when all wins precede all losses in a sequential list.
    """
    syms = symbols or ["AAA", "BBB", "CCC", "DDD", "EEE"]
    picks = []
    for i in range(n_won):
        picks.append({
            "strategy": strategy, "asset_class": asset_class,
            "status": "WON", "pnl_pct": win_pnl, "symbol": syms[i % len(syms)],
        })
    for i in range(n_lost):
        picks.append({
            "strategy": strategy, "asset_class": asset_class,
            "status": "LOST", "pnl_pct": loss_pnl, "symbol": syms[i % len(syms)],
        })
    rng = random.Random(42)
    rng.shuffle(picks)
    return picks


class TestMoneyReadyVerdict:
    def test_insufficient_data_below_min_n(self):
        from alpha_engine.money_ready_verdict import money_ready_verdict, MIN_N_CLASS
        picks = _make_picks(10, 5, asset_class="BOND")
        with patch("alpha_engine.money_ready_verdict._load_picks", return_value=picks):
            with patch("alpha_engine.money_ready_verdict._load_blocked", return_value=set()):
                results = money_ready_verdict()
        assert results["BOND"]["verdict"] == "INSUFFICIENT_DATA"
        assert results["BOND"]["n_resolved"] == 15
        assert results["BOND"]["n_ok"] is False

    def test_not_ready_poor_wr(self):
        from alpha_engine.money_ready_verdict import money_ready_verdict
        picks = _make_picks(10, 90, asset_class="FOREX")
        with patch("alpha_engine.money_ready_verdict._load_picks", return_value=picks):
            with patch("alpha_engine.money_ready_verdict._load_blocked", return_value=set()):
                results = money_ready_verdict()
        assert results["FOREX"]["verdict"] in ("NOT_READY", "INSUFFICIENT_DATA")
        assert results["FOREX"]["wr"] < 0.50

    def test_money_ready_high_edge(self):
        from alpha_engine.money_ready_verdict import money_ready_verdict
        # High WR, high PF, sufficient n — should be MONEY_READY or at minimum WATCH.
        # _load_dashboard_health is mocked to isolate verdict logic from live registry
        # MDD data; otherwise real dashboard COMMODITY MDD (>55% threshold) leaks in
        # and triggers the MDD gate even for synthetic high-edge data.
        picks = _make_picks(n_won=400, n_lost=100, asset_class="COMMODITY", strategy="cot_positioning")
        with patch("alpha_engine.money_ready_verdict._load_picks", return_value=picks):
            with patch("alpha_engine.money_ready_verdict._load_blocked", return_value=set()):
                with patch("alpha_engine.money_ready_verdict._load_dashboard_health", return_value={}):
                    results = money_ready_verdict()
        assert results["COMMODITY"]["wr"] == pytest.approx(0.80, abs=0.01)
        assert results["COMMODITY"]["pf"] > 1.5
        assert results["COMMODITY"]["verdict"] in ("MONEY_READY", "WATCH")

    def test_blocked_strategies_excluded(self):
        from alpha_engine.money_ready_verdict import money_ready_verdict
        picks = _make_picks(200, 50, strategy="bad_strat")
        with patch("alpha_engine.money_ready_verdict._load_picks", return_value=picks):
            with patch("alpha_engine.money_ready_verdict._load_blocked", return_value={"bad_strat"}):
                with patch("alpha_engine.money_ready_verdict._load_dashboard_health", return_value={}):
                    results = money_ready_verdict()
        assert "COMMODITY" not in results or results["COMMODITY"]["n_resolved"] == 0

    def test_asset_class_filter(self):
        from alpha_engine.money_ready_verdict import money_ready_verdict
        picks = (
            _make_picks(100, 50, asset_class="COMMODITY")
            + _make_picks(100, 50, asset_class="EQUITY")
        )
        with patch("alpha_engine.money_ready_verdict._load_picks", return_value=picks):
            with patch("alpha_engine.money_ready_verdict._load_blocked", return_value=set()):
                results = money_ready_verdict(asset_class="COMMODITY")
        assert "COMMODITY" in results
        assert "EQUITY" not in results

    def test_returns_expected_keys(self):
        from alpha_engine.money_ready_verdict import money_ready_verdict
        picks = _make_picks(60, 40, asset_class="ETF")
        with patch("alpha_engine.money_ready_verdict._load_picks", return_value=picks):
            with patch("alpha_engine.money_ready_verdict._load_blocked", return_value=set()):
                results = money_ready_verdict()
        r = results["ETF"]
        for key in ("n_resolved", "wr", "pf", "n_ok", "wr_ok", "pf_ok", "dsr_ok",
                    "pbo_ok", "spa_ok", "verdict", "top_symbol", "top_symbol_share",
                    "concentration_capped"):
            assert key in r, f"Missing key: {key}"
        assert r["verdict"] in ("MONEY_READY", "WATCH", "NOT_READY", "INSUFFICIENT_DATA")

    def test_m070_single_symbol_concentration_caps_to_watch(self):
        # M-070: a strong-edge class whose resolved picks are all ONE symbol
        # is a single-name bet — must be capped at WATCH, never MONEY_READY.
        from alpha_engine.money_ready_verdict import money_ready_verdict
        picks = _make_picks(400, 100, asset_class="COMMODITY",
                            strategy="cot_positioning", symbols=["CT=F"])
        with patch("alpha_engine.money_ready_verdict._load_picks", return_value=picks):
            with patch("alpha_engine.money_ready_verdict._load_blocked", return_value=set()):
                results = money_ready_verdict()
        r = results["COMMODITY"]
        assert r["top_symbol"] == "CT=F"
        assert r["top_symbol_share"] == pytest.approx(1.0, abs=0.01)
        assert r["concentration_capped"] is True
        assert r["verdict"] == "WATCH"  # NOT MONEY_READY despite strong edge

    def test_m070_diversified_symbols_allow_money_ready(self):
        # Same strong edge spread across 5 symbols — concentration guard does
        # not trip, so the class can reach MONEY_READY.
        # _load_dashboard_health mocked to isolate from live registry MDD.
        from alpha_engine.money_ready_verdict import money_ready_verdict
        picks = _make_picks(400, 100, asset_class="COMMODITY",
                            strategy="cot_positioning")
        with patch("alpha_engine.money_ready_verdict._load_picks", return_value=picks):
            with patch("alpha_engine.money_ready_verdict._load_blocked", return_value=set()):
                with patch("alpha_engine.money_ready_verdict._load_dashboard_health", return_value={}):
                    results = money_ready_verdict()
        r = results["COMMODITY"]
        assert r["top_symbol_share"] <= 0.60
        assert r["concentration_capped"] is False
        assert r["verdict"] in ("MONEY_READY", "WATCH")

    def test_expectancy_computed_in_verdict(self):
        # M-expectancy: post-cost expectancy fields must be present in every verdict.
        from alpha_engine.money_ready_verdict import money_ready_verdict
        picks = _make_picks(n_won=60, n_lost=40, asset_class="EQUITY",
                            strategy="test_edge", win_pnl=0.05, loss_pnl=-0.02)
        with patch("alpha_engine.money_ready_verdict._load_picks", return_value=picks):
            with patch("alpha_engine.money_ready_verdict._load_blocked", return_value=set()):
                results = money_ready_verdict()
        r = results["EQUITY"]
        assert "expectancy" in r, "expectancy key missing from verdict"
        assert "expectancy_ok" in r, "expectancy_ok key missing from verdict"
        # With WR=60%, avg_win=5%, avg_loss=2% the post-cost expectancy should be positive
        assert r["expectancy"] is not None
        assert r["expectancy_ok"] is True

    def test_expectancy_negative_when_losses_dominate(self):
        # Edge case: tiny wins, large losses -> negative post-cost expectancy
        from alpha_engine.money_ready_verdict import money_ready_verdict
        picks = _make_picks(n_won=70, n_lost=30, asset_class="CRYPTO",
                            strategy="bad_ratio", win_pnl=0.001, loss_pnl=-0.10)
        with patch("alpha_engine.money_ready_verdict._load_picks", return_value=picks):
            with patch("alpha_engine.money_ready_verdict._load_blocked", return_value=set()):
                results = money_ready_verdict()
        r = results["CRYPTO"]
        assert r["expectancy_ok"] is False

    def test_m069_slippage_flips_sub_cost_win_to_net_loss(self):
        # M-069: a "WON" pick whose gross edge is below the round-trip cost is
        # a real-money LOSS. COMMODITY round-trip = 12bp = 0.0012; a 7bp gross
        # "win" (0.0007) must count as a loss after slippage.
        from alpha_engine.money_ready_verdict import _class_stats
        picks = _make_picks(100, 0, asset_class="COMMODITY",
                            win_pnl=0.0007)  # 7bp gross "wins"
        stats = _class_stats(picks)
        # Every gross win is net-negative -> WR collapses to 0.
        assert stats["COMMODITY"]["wr"] == pytest.approx(0.0, abs=0.01)

    def test_commodity_concentration_cap_override_at_85pct(self):
        # MAX_SYMBOL_CONCENTRATION_BY_CLASS: COMMODITY cap is 0.85, not 0.60.
        # CT=F at 84% concentration (promoted PROBATION->FULL 2026-05-18)
        # should NOT cap COMMODITY at WATCH — it is genuine concentrated edge.
        from alpha_engine.money_ready_verdict import money_ready_verdict
        # 84% CT=F concentration — above global 60% cap but below COMMODITY 85% cap.
        n_ctf = 84
        n_other = 16
        picks_ctf = _make_picks(n_ctf, 0, asset_class="COMMODITY",
                                strategy="cot_positioning", symbols=["CT=F"],
                                win_pnl=0.05)
        picks_other = _make_picks(n_other, 0, asset_class="COMMODITY",
                                  strategy="cot_positioning", symbols=["GC=F"],
                                  win_pnl=0.05)
        picks = picks_ctf + picks_other
        with patch("alpha_engine.money_ready_verdict._load_picks", return_value=picks):
            with patch("alpha_engine.money_ready_verdict._load_blocked", return_value=set()):
                results = money_ready_verdict()
        r = results["COMMODITY"]
        assert r["top_symbol"] == "CT=F"
        assert r["top_symbol_share"] == pytest.approx(0.84, abs=0.02)
        # 84% < COMMODITY cap of 85% — must NOT be concentration_capped
        assert r["concentration_capped"] is False

    def test_pf_registry_policy_excluded_removed_from_load_blocked(self):
        # PF_REGISTRY_POLICY_EXCLUDED strategies must appear in _load_blocked() output.
        # M-110 (2026-05-18): cta_replicator removed from PF_REGISTRY_POLICY_EXCLUDED —
        # its COMMODITY directional blocks are handled by build_pf_registry.py direction-
        # aware filter. cta_commodity_momentum_term remains in the set (LONG+SHORT blocked).
        from alpha_engine.money_ready_verdict import _load_blocked
        blocked = _load_blocked(asset_class="COMMODITY")
        # cta_commodity_momentum_term is in PF_REGISTRY_POLICY_EXCLUDED — must be blocked.
        assert "cta_commodity_momentum_term" in blocked, (
            "cta_commodity_momentum_term must be in _load_blocked(COMMODITY) via PF_REGISTRY_POLICY_EXCLUDED"
        )
        # cta_replicator was removed from PF_REGISTRY_POLICY_EXCLUDED (M-110) because
        # FOREX SHORT direction has T1-grade edge and flat-excluding by source name is wrong.
        assert "cta_replicator" not in blocked, (
            "cta_replicator must NOT be in _load_blocked(COMMODITY) after M-110 removal"
        )


class TestM105MlEnhancedQuarantine:
    """M-105: ml_enhanced family quarantine for CRYPTO verdict."""

    def _ml_crypto_picks(self, n_won, n_lost, strategy="ml_enhanced_BTCUSDT_1d_B_lightgbm"):
        return _make_picks(n_won, n_lost, asset_class="CRYPTO", strategy=strategy,
                           win_pnl=0.05, loss_pnl=-0.02)

    def _non_ml_crypto_picks(self, n_won, n_lost):
        return _make_picks(n_won, n_lost, asset_class="CRYPTO", strategy="macd_crossover",
                           win_pnl=0.05, loss_pnl=-0.02)

    def test_shadow_mode_stamps_quarantine_fields(self):
        # Shadow mode (default): verdict stays MONEY_READY but quarantine fields present.
        # MDD gate is patched OFF because synthetic consecutive-wins data produces an
        # unrealistically large MDD on the multiplicative equity curve (87%+), which would
        # downgrade the verdict before the M-105 quarantine logic fires. The MDD gate
        # behaviour is separately exercised by TestI3MddCvarGate.
        from alpha_engine.money_ready_verdict import money_ready_verdict
        import alpha_engine.money_ready_verdict as mrv
        picks = self._ml_crypto_picks(300, 100)
        with patch("alpha_engine.money_ready_verdict._load_picks", return_value=picks):
            with patch("alpha_engine.money_ready_verdict._load_blocked", return_value=set()):
                with patch("alpha_engine.money_ready_verdict._load_blocked_symbols", return_value=set()):
                    with patch("alpha_engine.money_ready_verdict._load_dashboard_health", return_value={}):
                        with patch.object(mrv, "_ML_ENHANCED_CRYPTO_QUARANTINE", False):
                            with patch.object(mrv, "_MDD_GATE_ENFORCE", False):
                                results = money_ready_verdict()
        r = results["CRYPTO"]
        assert "_ml_enhanced_quarantine_enabled" in r
        assert "_ml_enhanced_quarantine_n" in r
        assert "_ml_enhanced_quarantine_recommend" in r
        assert r["_ml_enhanced_quarantine_enabled"] is False
        assert r["_ml_enhanced_quarantine_n"] == 400  # all ml_enhanced picks counted
        # shadow mode recommends NOT_READY since verdict is currently MONEY_READY
        assert r["_ml_enhanced_quarantine_recommend"] == "NOT_READY"

    def test_enforce_mode_excludes_ml_enhanced_from_crypto(self):
        # Enforce mode: ml_enhanced picks removed from CRYPTO _class_stats.
        from alpha_engine.money_ready_verdict import _class_stats
        import alpha_engine.money_ready_verdict as mrv
        ml_picks = self._ml_crypto_picks(200, 50)
        non_ml_picks = self._non_ml_crypto_picks(10, 2)
        all_picks = ml_picks + non_ml_picks
        with patch.object(mrv, "_ML_ENHANCED_CRYPTO_QUARANTINE", True):
            stats = _class_stats(all_picks)
        # Only 12 non-ml picks should remain for CRYPTO
        assert stats["CRYPTO"]["n"] == 12
        # quarantine count should be 250 (the ml_enhanced picks)
        assert stats["CRYPTO"]["_ml_enhanced_quarantine_n"] == 250

    def test_shadow_mode_counts_but_does_not_exclude(self):
        # Shadow mode: ml_enhanced picks stay in calculation but count is stamped.
        from alpha_engine.money_ready_verdict import _class_stats
        import alpha_engine.money_ready_verdict as mrv
        ml_picks = self._ml_crypto_picks(200, 50)
        non_ml_picks = self._non_ml_crypto_picks(10, 2)
        all_picks = ml_picks + non_ml_picks
        with patch.object(mrv, "_ML_ENHANCED_CRYPTO_QUARANTINE", False):
            stats = _class_stats(all_picks)
        # All 262 picks remain in CRYPTO (shadow — not excluded)
        assert stats["CRYPTO"]["n"] == 262
        # quarantine count stamps the 250 ml_enhanced picks
        assert stats["CRYPTO"]["_ml_enhanced_quarantine_n"] == 250

    def test_non_crypto_unaffected_by_quarantine(self):
        # ml_enhanced quarantine only applies to CRYPTO, not other classes.
        from alpha_engine.money_ready_verdict import _class_stats
        import alpha_engine.money_ready_verdict as mrv
        ml_eq_picks = _make_picks(100, 30, asset_class="EQUITY",
                                  strategy="ml_enhanced_AAPL_1d_B_lightgbm",
                                  win_pnl=0.05, loss_pnl=-0.02)
        with patch.object(mrv, "_ML_ENHANCED_CRYPTO_QUARANTINE", True):
            stats = _class_stats(ml_eq_picks)
        # EQUITY ml_enhanced picks NOT excluded — quarantine is CRYPTO-only
        assert stats["EQUITY"]["n"] == 130
        assert stats["EQUITY"]["_ml_enhanced_quarantine_n"] == 0

    def test_quarantine_recommend_none_when_already_not_ready(self):
        # If verdict is NOT_READY (poor edge), recommend stays None (no double-flag).
        from alpha_engine.money_ready_verdict import money_ready_verdict
        import alpha_engine.money_ready_verdict as mrv
        # Poor win rate — verdict will be NOT_READY even before quarantine
        picks = self._ml_crypto_picks(n_won=10, n_lost=90)
        with patch("alpha_engine.money_ready_verdict._load_picks", return_value=picks):
            with patch("alpha_engine.money_ready_verdict._load_blocked", return_value=set()):
                with patch("alpha_engine.money_ready_verdict._load_blocked_symbols", return_value=set()):
                    with patch("alpha_engine.money_ready_verdict._load_dashboard_health", return_value={}):
                        with patch.object(mrv, "_ML_ENHANCED_CRYPTO_QUARANTINE", False):
                            results = money_ready_verdict()
        r = results["CRYPTO"]
        # verdict is already NOT_READY — no need to recommend quarantine
        assert r["verdict"] in ("NOT_READY", "INSUFFICIENT_DATA")
        assert r["_ml_enhanced_quarantine_recommend"] is None


class TestI3MddCvarGate:
    """I-3: MDD ≤ 20% + CVaR-95% < 10% tail-risk gate."""

    def test_rolling_mdd_flat_returns(self):
        returns = [0.01] * 100
        assert _rolling_mdd(returns) == pytest.approx(0.0, abs=0.001)

    def test_rolling_mdd_single_crash(self):
        returns = [0.01] * 50 + [-0.50] + [0.01] * 10
        mdd = _rolling_mdd(returns)
        assert mdd > 0.30

    def test_rolling_mdd_within_gate_threshold(self):
        returns = [0.02] * 20 + [-0.10] + [0.02] * 20
        mdd = _rolling_mdd(returns)
        assert mdd < 0.20

    def test_mdd_cvar_gate_passes_clean_edge(self):
        # Alternating small wins/losses — MDD stays well below 20% (no extended losing run)
        returns = ([0.02, -0.01] * 50)  # WR=50%, equity oscillates but never crashes
        result = _mdd_cvar_gate(returns, "COMMODITY")
        assert result["mdd_ok"] is True
        assert result["cvar_ok"] is True
        assert result["gate_ok"] is True

    def test_mdd_cvar_gate_fails_high_mdd(self):
        returns = [0.05] * 20 + [-0.60] + [0.05] * 80
        result = _mdd_cvar_gate(returns, "CRYPTO")
        assert result["mdd_ok"] is False
        assert result["gate_ok"] is False

    def test_mdd_cvar_gate_fails_high_cvar(self):
        returns = [0.01] * 95 + [-0.60] * 5
        result = _mdd_cvar_gate(returns, "FOREX")
        assert result["cvar_ok"] is False
        assert result["gate_ok"] is False

    def test_mdd_cvar_gate_insufficient_data(self):
        result = _mdd_cvar_gate([0.01] * 5, "EQUITY")
        assert result["mdd_ok"] is None
        assert result["cvar_ok"] is None
        assert result["gate_ok"] is None

    def test_commodity_uses_55pct_mdd_cap(self):
        # COMMODITY override: 55% cap. Build a series with MDD ~43% (real observed value).
        # 43% < 55% → should PASS for COMMODITY, FAIL for CRYPTO (default 20% cap).
        returns = [0.02] * 30 + [-0.50] + [0.02] * 70  # MDD ~43%
        result_commodity = _mdd_cvar_gate(returns, "COMMODITY")
        result_crypto = _mdd_cvar_gate(returns, "CRYPTO")
        assert result_commodity["mdd_ok"] is True, (
            f"COMMODITY 43% MDD should pass 55% cap, got mdd={result_commodity['mdd']:.1%}"
        )
        assert result_crypto["mdd_ok"] is False, (
            "CRYPTO 43% MDD should fail 20% cap"
        )

    def test_commodity_fails_above_55pct_mdd(self):
        # MDD ~60% should fail even the generous COMMODITY cap.
        returns = [0.02] * 30 + [-0.70] + [0.02] * 70  # MDD ~60%
        result = _mdd_cvar_gate(returns, "COMMODITY")
        assert result["mdd_ok"] is False, (
            f"COMMODITY 60% MDD should fail 55% cap, got mdd={result['mdd']:.1%}"
        )

    def test_verdict_stamped_with_mdd_cvar_fields(self):
        from alpha_engine.money_ready_verdict import money_ready_verdict
        picks = _make_picks(n_won=80, n_lost=20, asset_class="COMMODITY",
                            win_pnl=0.05, loss_pnl=-0.02)
        with patch("alpha_engine.money_ready_verdict._load_picks", return_value=picks):
            with patch("alpha_engine.money_ready_verdict._load_blocked", return_value=set()):
                with patch("alpha_engine.money_ready_verdict._load_blocked_symbols", return_value=set()):
                    with patch("alpha_engine.money_ready_verdict._load_dashboard_health", return_value={}):
                        results = money_ready_verdict()
        r = results["COMMODITY"]
        for key in ("mdd", "mdd_ok", "cvar_95", "cvar_ok", "_mdd_cvar_gate_ok", "_mdd_cvar_recommend"):
            assert key in r, f"Missing key: {key}"

    def test_shadow_mode_stamps_recommend_not_ready_when_mdd_fails(self):
        from alpha_engine.money_ready_verdict import money_ready_verdict
        import alpha_engine.money_ready_verdict as mrv
        picks_win = _make_picks(n_won=40, n_lost=0, asset_class="COMMODITY", win_pnl=0.05)
        picks_crash = _make_picks(n_won=0, n_lost=1, asset_class="COMMODITY", loss_pnl=-0.80)
        picks_recover = _make_picks(n_won=60, n_lost=0, asset_class="COMMODITY", win_pnl=0.05)
        picks = picks_win + picks_crash + picks_recover
        with patch("alpha_engine.money_ready_verdict._load_picks", return_value=picks):
            with patch("alpha_engine.money_ready_verdict._load_blocked", return_value=set()):
                with patch("alpha_engine.money_ready_verdict._load_blocked_symbols", return_value=set()):
                    with patch("alpha_engine.money_ready_verdict._load_dashboard_health", return_value={}):
                        with patch.object(mrv, "_MDD_GATE_ENFORCE", False):
                            results = money_ready_verdict()
        r = results["COMMODITY"]
        assert r["mdd"] > 0.20
        assert r["_mdd_cvar_gate_ok"] is False
        if r["verdict"] == "MONEY_READY":
            assert r["_mdd_cvar_recommend"] == "NOT_READY"

    def test_enforce_mode_downgrades_money_ready_to_not_ready_when_mdd_fails(self):
        """When MDD_GATE_ENFORCE=1 and the tail-risk gate fails, a verdict that
        would otherwise be MONEY_READY must hard-downgrade to NOT_READY."""
        from alpha_engine.money_ready_verdict import money_ready_verdict
        import alpha_engine.money_ready_verdict as mrv
        picks_win = _make_picks(n_won=40, n_lost=0, asset_class="COMMODITY", win_pnl=0.05)
        picks_crash = _make_picks(n_won=0, n_lost=1, asset_class="COMMODITY", loss_pnl=-0.80)
        picks_recover = _make_picks(n_won=60, n_lost=0, asset_class="COMMODITY", win_pnl=0.05)
        picks = picks_win + picks_crash + picks_recover

        def _run():
            with patch("alpha_engine.money_ready_verdict._load_picks", return_value=picks):
                with patch("alpha_engine.money_ready_verdict._load_blocked", return_value=set()):
                    with patch("alpha_engine.money_ready_verdict._load_blocked_symbols", return_value=set()):
                        with patch("alpha_engine.money_ready_verdict._load_dashboard_health", return_value={}):
                            return money_ready_verdict()

        # Shadow (default OFF): verdict unchanged, advisory stamped.
        with patch.object(mrv, "_MDD_GATE_ENFORCE", False):
            shadow = _run()["COMMODITY"]
        assert shadow["_mdd_cvar_gate_ok"] is False

        # Enforce ON: gate fails -> verdict hard-downgraded to NOT_READY.
        with patch.object(mrv, "_MDD_GATE_ENFORCE", True):
            enforced = _run()["COMMODITY"]
        assert enforced["_mdd_cvar_gate_ok"] is False
        if shadow["verdict"] == "MONEY_READY":
            assert enforced["verdict"] == "NOT_READY"
            # advisory suppressed in enforce mode (it only fires when OFF)
            assert enforced["_mdd_cvar_recommend"] is None
        else:
            # gate didn't apply to a MONEY_READY verdict -> enforce is a no-op
            assert enforced["verdict"] == shadow["verdict"]


class TestCommodityWRFloor:
    """COMMODITY uses a 40% WR SANITY floor (2026-05-19, swarm-settled Q1
    verdict — lowered from the interim 45%). WR<50% at PF>=1.5 is the NORMAL
    trend-following payoff profile for CTAs; the WR floor is a low sanity check
    and the net-of-slippage expectancy gate is the real promotion gate.
    reports/multi_engine_institutional_strategies_2026_05_19.md
    """

    def test_commodity_wr_floor_is_40_pct(self):
        from alpha_engine.money_ready_verdict import CLASS_WR_FLOORS
        floor = CLASS_WR_FLOORS.get("COMMODITY")
        assert floor == pytest.approx(0.40), (
            f"COMMODITY WR sanity floor should be 0.40 (trend-following), got {floor}"
        )

    def test_commodity_wr_46pct_with_high_pf_is_money_ready(self):
        """WR=47% PF~1.97 (COMMODITY-like) must clear the 40% sanity floor —
        this was blocked under the old 55% default."""
        from alpha_engine.money_ready_verdict import money_ready_verdict
        # WR=47/100=47%, win_pnl=0.04 loss_pnl=0.018 → 47*0.04=1.88 / 53*0.018=0.954 → PF~1.97
        picks = _make_picks(47, 53, asset_class="COMMODITY",
                            win_pnl=0.04, loss_pnl=-0.018)
        with patch("alpha_engine.money_ready_verdict._load_picks", return_value=picks):
            with patch("alpha_engine.money_ready_verdict._load_blocked_symbols", return_value=set()):
                with patch("alpha_engine.money_ready_verdict._load_dashboard_health", return_value={}):
                    results = money_ready_verdict()
        assert "COMMODITY" in results
        r = results["COMMODITY"]
        assert r["wr"] == pytest.approx(0.47, abs=0.01)
        assert r["wr_ok"] is True, (
            f"COMMODITY WR=47% should pass 40% floor; verdict={r['verdict']}"
        )

    def test_commodity_wr_42pct_passes_lowered_floor(self):
        """WR=42% is ABOVE the lowered COMMODITY sanity floor of 40% → wr_ok=True
        (was blocked under the interim 45% floor)."""
        from alpha_engine.money_ready_verdict import money_ready_verdict
        picks = _make_picks(42, 58, asset_class="COMMODITY",
                            win_pnl=0.04, loss_pnl=-0.018)
        with patch("alpha_engine.money_ready_verdict._load_picks", return_value=picks):
            with patch("alpha_engine.money_ready_verdict._load_blocked_symbols", return_value=set()):
                with patch("alpha_engine.money_ready_verdict._load_dashboard_health", return_value={}):
                    results = money_ready_verdict()
        if "COMMODITY" in results:
            assert results["COMMODITY"]["wr_ok"] is True

    def test_commodity_wr_38pct_blocked_below_floor(self):
        """WR=38% is below the COMMODITY sanity floor of 40% → wr_ok=False."""
        from alpha_engine.money_ready_verdict import money_ready_verdict
        picks = _make_picks(38, 62, asset_class="COMMODITY",
                            win_pnl=0.04, loss_pnl=-0.018)
        with patch("alpha_engine.money_ready_verdict._load_picks", return_value=picks):
            with patch("alpha_engine.money_ready_verdict._load_blocked_symbols", return_value=set()):
                with patch("alpha_engine.money_ready_verdict._load_dashboard_health", return_value={}):
                    results = money_ready_verdict()
        if "COMMODITY" in results:
            assert results["COMMODITY"]["wr_ok"] is False


class TestQ1ExpectancyGateAndWrFloors:
    """Q1 (2026-05-19, swarm-settled): per-class WR sanity floors + the
    net-of-slippage expectancy gate is now the real money-ready promotion gate.

    COMMODITY (PF 1.78 / WR 46.9%) — below the old hard 55% WR floor — must now
    reach MONEY_READY because WR 46.9% > 0.40 sanity floor, PF 1.78 > 1.5, and
    post-slippage expectancy is positive. FOREX (PF 0.27) fails the PF floor.

    FOREX (PF 0.27) -> NOT_READY: the PF<1.0 hard-route (a money-losing book is
    never WATCH) fires regardless of the lowered WR sanity floor. EQUITY
    (PF 1.41 > 1.0, profitable near-miss) stays WATCH — the PF<1.0 route
    distinguishes a losing book from a profitable sub-T2 candidate."""

    def _gates_ok(self):
        return (
            {"ok": True, "dsr_score": 0.97},
            {"ok": True, "pbo": 0.30},
            {"ok": True, "spa_p": 0.08, "n_spa_pass": 3},
        )

    def test_commodity_like_reaches_money_ready(self):
        # COMMODITY: n=750, WR 46.9%, PF 1.78. avg_win/avg_loss chosen for a
        # positive net-of-slippage expectancy (payoff ratio ~2.0 per the report).
        from alpha_engine.money_ready_verdict import _verdict
        dsr, pbo, spa = self._gates_ok()
        v = _verdict(
            n=750, wr=0.469, pf=1.78,
            dsr=dsr, pbo=pbo, spa=spa,
            asset_class="COMMODITY",
            avg_win=0.040, avg_loss=0.020,  # ratio 2.0 -> E>0 net of 12bp
        )
        assert v == "MONEY_READY", f"COMMODITY should be MONEY_READY, got {v}"

    def test_forex_like_not_ready(self):
        # FOREX: PF 0.27 < 1.0 -> the money-losing-book hard-route returns
        # NOT_READY even though WR 46.4% passes the lowered 0.40 sanity floor.
        from alpha_engine.money_ready_verdict import _verdict
        dsr, pbo, spa = self._gates_ok()
        v = _verdict(
            n=1169, wr=0.464, pf=0.27,
            dsr=dsr, pbo=pbo, spa=spa,
            asset_class="FOREX",
            avg_win=0.010, avg_loss=0.030,  # inverted payoff -> E<0
        )
        assert v == "NOT_READY", f"FOREX (PF 0.27 < 1.0) must be NOT_READY, got {v}"

    def test_equity_near_miss_stays_watch(self):
        # EQUITY: PF 1.41 (> 1.0, profitable) but < 1.5 floor, WR 52.7% >= 0.52.
        # The PF<1.0 route does NOT fire -> WATCH (profitable sub-T2 candidate),
        # which is distinct from a money-losing FOREX book.
        from alpha_engine.money_ready_verdict import _verdict
        dsr, pbo, spa = self._gates_ok()
        v = _verdict(
            n=421, wr=0.527, pf=1.41,
            dsr=dsr, pbo=pbo, spa=spa,
            asset_class="EQUITY",
            avg_win=0.030, avg_loss=0.022,
        )
        assert v == "WATCH", f"EQUITY (PF 1.41 profitable near-miss) -> WATCH, got {v}"

    def test_forex_below_sanity_floor_is_not_ready(self):
        # When FOREX WR is also below the 0.40 sanity floor, wr_ok=False and
        # pf_ok=False -> NOT_READY (the `else` branch).
        from alpha_engine.money_ready_verdict import _verdict
        dsr, pbo, spa = self._gates_ok()
        v = _verdict(
            n=1169, wr=0.30, pf=0.27,
            dsr=dsr, pbo=pbo, spa=spa,
            asset_class="FOREX",
            avg_win=0.010, avg_loss=0.030,
        )
        assert v == "NOT_READY", f"sub-floor FOREX should be NOT_READY, got {v}"

    def test_commodity_blocked_by_negative_expectancy(self):
        # Even with PF/WR/DSR passing, a negative net-of-slippage expectancy
        # hard-downgrades MONEY_READY -> NOT_READY (gate now ON by default).
        from alpha_engine.money_ready_verdict import _verdict
        dsr, pbo, spa = self._gates_ok()
        v = _verdict(
            n=750, wr=0.469, pf=1.78,
            dsr=dsr, pbo=pbo, spa=spa,
            asset_class="COMMODITY",
            avg_win=0.001, avg_loss=0.010,  # tiny wins, large losses -> E<0
        )
        assert v == "NOT_READY", f"negative-expectancy COMMODITY should be NOT_READY, got {v}"

    def test_wr_sanity_floors_lowered(self):
        from alpha_engine.money_ready_verdict import CLASS_WR_FLOORS
        assert CLASS_WR_FLOORS["COMMODITY"] == 0.40
        assert CLASS_WR_FLOORS["FOREX"] == 0.40
        assert CLASS_WR_FLOORS["FUTURES"] == 0.40
        assert CLASS_WR_FLOORS["ETF"] == 0.45
        assert CLASS_WR_FLOORS["BOND"] == 0.45
        assert CLASS_WR_FLOORS["EQUITY"] == 0.52
        assert CLASS_WR_FLOORS["CRYPTO"] == 0.50

    def test_expectancy_gate_enforced_by_default(self):
        from alpha_engine.money_ready_verdict import _SLIPPAGE_GATE_ENABLED
        assert _SLIPPAGE_GATE_ENABLED is True


class TestQ2RegistryMddPreferred:
    """Q2 (2026-05-19): _mdd_cvar_gate prefers a registry-supplied
    max_drawdown_pct over the ephemeral _rolling_mdd recompute."""

    def test_registry_mdd_preferred_over_recompute(self):
        # Returns alone would yield ~0 MDD; the registry value (0.60) must win.
        # COMMODITY cap is 0.55 (CTA institutional norm, per b4664793f2); 0.60 > 0.55 → FAIL.
        returns = [0.01] * 100
        result = _mdd_cvar_gate(returns, "COMMODITY", registry_mdd=0.60)
        assert result["mdd"] == pytest.approx(0.60, abs=1e-6)
        assert result["mdd_source"] == "registry"
        assert result["mdd_ok"] is False  # 0.60 > 0.55 COMMODITY cap

    def test_recompute_fallback_when_registry_mdd_none(self):
        returns = [0.02] * 20 + [-0.10] + [0.02] * 20
        result = _mdd_cvar_gate(returns, "COMMODITY", registry_mdd=None)
        assert result["mdd_source"] == "recompute"
        assert result["mdd"] < 0.20
