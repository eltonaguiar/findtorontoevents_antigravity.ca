from __future__ import annotations

from audit_trail import dashboard_generator
from audit_trail import quality_gates


def test_normalize_pick_backfills_pm_vetted_badge_and_trader_label() -> None:
    raw = {
        "symbol": "BTCUSDT",
        "direction": "LONG",
        "entry_price": 100000.0,
        "take_profit": 102500.0,
        "stop_loss": 98500.0,
        "confidence": 0.88,
        "strategy": "copy_pm_justdance",
        "signal_origin": "vetted_wallet_copy",
        "trader_name": "justdance",
    }

    norm = dashboard_generator._normalize_pick(raw, "pm_whale_signals", "OPEN")

    assert norm["source_system"] == "pm_whale_signals"
    assert norm["type_label"] == "🔮 PM Vetted"
    assert norm["trader_label"] == "justdance"


def test_normalize_pick_backfills_pm_whale_badge_from_whale_data() -> None:
    raw = {
        "symbol": "ETHUSDT",
        "direction": "SHORT",
        "entry_price": 2500.0,
        "take_profit": 2400.0,
        "stop_loss": 2550.0,
        "confidence": 0.77,
        "strategy": "pm_whale_0xeee92f",
        "signal_origin": "direct_position_inference",
        "whale_data": {
            "username": "ComTruise",
            "wallet": "0x1234567890abcdef1234567890abcdef12345678",
        },
    }

    norm = dashboard_generator._normalize_pick(raw, "pm_whale_signals", "OPEN")

    assert norm["type_label"] == "🔮 PM Whale"
    assert norm["trader_label"] == "ComTruise"


def test_normalize_pick_backfills_pm_kalshi_badge() -> None:
    raw = {
        "symbol": "BTCUSDT",
        "direction": "SHORT",
        "entry_price": 68000.0,
        "take_profit": 66300.0,
        "stop_loss": 69020.0,
        "confidence": 0.72,
        "strategy": "kalshi_mtf_consensus",
        "source_system": "kalshi_signal_agent",
    }

    norm = dashboard_generator._normalize_pick(raw, "pm_kalshi_signals", "OPEN")

    assert norm["type_label"] == "🔮 PM Kalshi"


def test_derive_asset_class_keeps_equity_tickers_out_of_commodity_bucket() -> None:
    assert (
        dashboard_generator._derive_asset_class(
            "COP",
            raw={"ticker": "COP"},
            source_system="goldmine_stocks",
            strategy="goldmine_1x_consensus",
        )
        == "EQUITY"
    )
    assert (
        dashboard_generator._derive_asset_class(
            "HON",
            raw={"ticker": "HON"},
            source_system="goldmine_stocks",
            strategy="goldmine_2x_consensus",
        )
        == "EQUITY"
    )


def test_derive_asset_class_keeps_crypto_pairs_out_of_commodity_bucket() -> None:
    assert (
        dashboard_generator._derive_asset_class(
            "SIGNUSDT",
            raw={},
            source_system="rapid_fire",
            strategy="macd_crossover",
        )
        == "CRYPTO"
    )


def test_derive_asset_class_keeps_explicit_futures_as_commodity() -> None:
    assert (
        dashboard_generator._derive_asset_class(
            "CL=F",
            raw={},
            source_system="multi_asset_copytrader",
            strategy="cftc_cot_commercial_signal",
        )
        == "COMMODITY"
    )


def test_normalize_pick_synthesizes_id_for_kalshi_signal() -> None:
    raw = {
        "symbol": "BTCUSDT",
        "direction": "SHORT",
        "confidence": 0.903,
        "strategy": "kalshi_mtf_consensus",
        "timestamp": "2026-03-26T16:30:35.160360+00:00",
    }

    norm = dashboard_generator._normalize_pick(raw, "pm_kalshi_signals", "OPEN")

    assert norm["id"].startswith("pm_kalshi_signals_BTCUSDT_SHORT_kalshi_mtf_consensus")


def test_normalize_pick_preserves_upstream_alpha_scores() -> None:
    raw = {
        "symbol": "FETUSDT",
        "direction": "LONG",
        "entry_price": 0.2271,
        "take_profit": 0.33506429,
        "stop_loss": 0.16232143,
        "confidence": 0.8,
        "strategy": "ml_enhanced_FETUSDT_1d_B_lightgbm",
        "ml_score": 0.9287,
        "elite_score": 85.0,
        "ml_composite_score": 85.0,
        "method_a_score": 94,
        "elite_grade": "A",
        "trust_level": "HIGH",
    }

    norm = dashboard_generator._normalize_pick(raw, "alpha_engine", "OPEN")

    assert norm["score"] == 85.0
    assert norm["elite_score"] == 85.0
    assert norm["ml_score"] == 0.9287
    assert norm["elite_grade"] == "A"
    assert norm["trust_label"] == "HIGH"


def test_normalize_pick_does_not_treat_probability_as_final_score() -> None:
    raw = {
        "symbol": "BTCUSDT",
        "direction": "LONG",
        "entry_price": 68000.0,
        "take_profit": 70000.0,
        "stop_loss": 66800.0,
        "confidence": 0.82,
        "score": 0.82,
        "strategy": "probability_only_signal",
    }

    norm = dashboard_generator._normalize_pick(raw, "ml_crypto_pred", "OPEN")

    assert norm["score"] is None


def test_snapshot_prediction_market_entry_backfills_trade_levels() -> None:
    pick = {
        "symbol": "BTCUSDT",
        "direction": "SHORT",
        "source_system": "pm_kalshi_signals",
        "strategy": "kalshi_mtf_consensus",
        "confidence": 0.903,
        "entry_price": 0,
        "take_profit": 0,
        "stop_loss": 0,
        "consensus_data": {"num_sources": 4},
    }

    updated = dashboard_generator._snapshot_prediction_market_entry(pick, 68000.0)

    assert updated is True
    assert pick["entry_price"] == 68000.0
    assert pick["take_profit"] < pick["entry_price"]
    assert pick["stop_loss"] > pick["entry_price"]


def test_prepare_prediction_market_consensus_signal_preserves_pm_source_lineage() -> None:
    raw = {
        "symbol": "BTCUSDT",
        "direction": "LONG",
        "confidence": 0.82,
        "strategy": "prediction_market_consensus",
        "source_system": "prediction_market_agents",
        "consensus_data": {
            "num_sources": 2,
            "sources": ["kalshi_signal_agent", "polymarket_prediction"],
            "high_conviction": True,
        },
    }

    prepared = dashboard_generator._prepare_prediction_market_consensus_signal(raw)

    assert prepared["source_system"] == "prediction_market_consensus"
    assert prepared["source_count"] == 2
    assert prepared["agreement_count"] == 2
    assert prepared["pm_source_systems"] == ["kalshi_signal_agent", "polymarket_prediction"]
    assert prepared["high_conviction"] is True


def test_pre_score_active_candidate_keeps_valid_zero_score_pick_alive() -> None:
    pick = {
        "id": "pm_consensus_BTCUSDT_202603270550",
        "symbol": "BTCUSDT",
        "direction": "LONG",
        "entry_price": 68000.0,
        "take_profit": 70000.0,
        "stop_loss": 66800.0,
        "confidence": 0.82,
        "strategy": "prediction_market_consensus",
        "source_system": "prediction_market_consensus",
        "status": "OPEN",
        # Score must meet CRYPTO min raw floor (30) after gate hardening.
        # Zero-score picks are no longer allowed to pass active gate.
        "score": 55,
    }

    assert dashboard_generator._is_pre_score_active_candidate(pick) is True
    # Active gate is permissive for crypto — score >= 30 passes through
    # (quality is expressed via sort order, not visibility hard-reject)
    assert quality_gates.passes_active_gate(pick) is True


def test_compute_verified_alpha_summary_segments_pm_and_curated_copy_rows() -> None:
    active = [
        {
            "symbol": "BTCUSDT",
            "source_system": "pm_whale_signals",
            "strategy": "copy_pm_elpolloloco",
            "history_wr_bayes": 0.67,
            "history_trades": 48,
        },
        {
            "symbol": "NZDUSD=X",
            "source_system": "multi_asset_copytrader",
            "strategy": "forex_rsi2_mean_reversion",
            "forward_wr": 0.61,
            "forward_trades": 12,
        },
        {
            "symbol": "SOLUSDT",
            "source_system": "super_signals",
            "strategy": "super_signal_trend",
        },
    ]
    smart = [
        {
            "symbol": "BTCUSDT",
            "source_system": "pm_whale_signals",
            "strategy": "copy_pm_elpolloloco",
        }
    ]
    closed = [
        {
            "symbol": "BTCUSDT",
            "source_system": "pm_whale_signals",
            "strategy": "copy_pm_elpolloloco",
            "pnl_pct": 4.2,
        },
        {
            "symbol": "NZDUSD=X",
            "source_system": "multi_asset_copytrader",
            "strategy": "forex_rsi2_mean_reversion",
            "pnl_pct": -1.1,
        },
        {
            "symbol": "SOLUSDT",
            "source_system": "super_signals",
            "strategy": "super_signal_trend",
            "pnl_pct": 9.0,
        },
    ]

    summary = dashboard_generator._compute_verified_alpha_summary(active, smart, closed)

    assert summary["active_count"] == 2
    assert summary["smart_count"] == 1
    assert summary["unique_sources"] == 2
    assert summary["source_mix"]["pm_whale_signals"] == 1
    assert summary["source_mix"]["multi_asset_copytrader"] == 1
    assert summary["realized"]["trades"] == 2
    assert summary["realized"]["win_rate"] == 50.0
    assert summary["audited"]["covered_active_picks"] == 2
    assert summary["audited"]["weighted_wr_pct"] is not None


def test_collect_system_stats_uses_audited_wr_for_verified_alpha_without_realized_closes() -> None:
    active = [
        dashboard_generator._normalize_pick(
            {
                "symbol": "BTCUSDT",
                "direction": "LONG",
                "entry_price": 68000.0,
                "take_profit": 72000.0,
                "stop_loss": 66000.0,
                "strategy": "copy_pm_elpolloloco",
                "timestamp": "2026-03-26T18:40:16+00:00",
                "history_wr_bayes": 0.68,
                "history_trades": 48,
            },
            "pm_whale_signals",
            "OPEN",
        )
    ]

    systems = dashboard_generator.collect_system_stats(active, [], [])
    row = next(s for s in systems if s["name"] == "pm_whale_signals")

    assert row["resolved_picks"] == 0
    assert row["win_rate_basis"] == "audited"
    assert row["audited_wr_pct"] is not None
    assert row["display_win_rate_pct"] == row["audited_wr_pct"]


def test_refresh_verified_alpha_system_stats_uses_forward_wr_fallback() -> None:
    systems = [{
        "name": "multi_asset_copytrader",
        "resolved_picks": 0,
        "win_rate_basis": "none",
        "audited_wr_pct": None,
        "audited_wr_coverage": 0,
        "display_win_rate_pct": None,
    }]
    active = [
        dashboard_generator._normalize_pick(
            {
                "symbol": "NZDUSD=X",
                "direction": "LONG",
                "entry_price": 0.57,
                "take_profit": 0.58,
                "stop_loss": 0.56,
                "strategy": "forex_rsi2_mean_reversion",
                "timestamp": "2026-03-26T18:40:16+00:00",
                "forward_wr": 100.0,
                "forward_trades": 6,
            },
            "multi_asset_copytrader",
            "OPEN",
        )
    ]

    dashboard_generator._refresh_verified_alpha_system_stats(systems, active)
    row = systems[0]

    assert row["win_rate_basis"] == "audited"
    assert row["audited_wr_pct"] == 65.0
    assert row["audited_wr_coverage"] == 1
    assert row["display_win_rate_pct"] == 65.0


def test_prepare_prediction_market_consensus_signal_prefers_source_count_and_label() -> None:
    raw = {
        "symbol": "ETHUSDT",
        "direction": "LONG",
        "strategy": "prediction_market_consensus",
        "source_count": 2,
        "sources": ["wallet_copy", "polymarket_reverse"],
        "type_label": "🔮 PM Consensus",
        "consensus_data": {
            "source_category_count": 99,
            "num_sources": 99,
            "high_conviction": False,
        },
    }

    prepared = dashboard_generator._prepare_prediction_market_consensus_signal(raw)

    assert prepared["agreement_count"] == 2
    assert prepared["source_count"] == 2
    assert prepared["source_systems"] == ["wallet_copy", "polymarket_reverse"]
    assert prepared["type_label"] == "🔮 PM Consensus"
    assert prepared["high_conviction"] is False


def test_build_recent_closed_picks_reserves_copy_and_pm_track_record_rows() -> None:
    resolved = []
    for i in range(5):
        resolved.append({
            "symbol": f"GEN{i}USDT",
            "direction": "LONG",
            "source_system": "baby_strats_forward",
            "strategy": "generic",
            "timestamp": f"2026-03-27T09:0{i}:00+00:00",
            "status": "WON",
        })
    resolved.append({
        "symbol": "NZDUSD=X",
        "direction": "LONG",
        "source_system": "multi_asset_copytrader",
        "strategy": "forex_rsi2_mean_reversion",
        "timestamp": "2026-03-20T09:00:00+00:00",
        "status": "WON",
    })
    resolved.append({
        "symbol": "BTCUSDT",
        "direction": "LONG",
        "source_system": "prediction_market_consensus",
        "strategy": "prediction_market_consensus",
        "timestamp": "2026-03-19T09:00:00+00:00",
        "status": "WON",
    })

    recent = dashboard_generator._build_recent_closed_picks(
        resolved,
        max_picks=4,
        reserved_slots=2,
    )

    recent_sources = {row["source_system"] for row in recent}
    assert len(recent) == 4
    assert "multi_asset_copytrader" in recent_sources
    assert "prediction_market_consensus" in recent_sources


def test_build_recent_closed_picks_excludes_banned_sources_and_tiers() -> None:
    resolved = [
        {
            "symbol": "BTCUSDT",
            "direction": "LONG",
            "source_system": "rapid_fire",  # BANNED tier in system_trust_registry
            "strategy": "macd_rsi_confluence",
            "timestamp": "2026-04-30T09:00:00+00:00",
            "status": "WON",
        },
        {
            "symbol": "AAPL",
            "direction": "LONG",
            "source_system": "alpha_engine",
            "strategy": "breakout_momentum",
            "timestamp": "2026-04-30T08:00:00+00:00",
            "status": "WON",
            "trust_tier": "BANNED",  # explicitly banned trust tier
        },
        {
            "symbol": "MSFT",
            "direction": "LONG",
            "source_system": "alpha_engine",
            "strategy": "quality_value",
            "timestamp": "2026-04-30T07:00:00+00:00",
            "status": "WON",
        },
    ]

    recent = dashboard_generator._build_recent_closed_picks(
        resolved,
        max_picks=10,
        reserved_slots=0,
        nc_reserved_slots=0,
    )

    assert [row["symbol"] for row in recent] == ["MSFT"]


def test_build_btc_strategy_replication_report_flags_contradictions(
    tmp_path,
) -> None:
    (tmp_path / "FINAL_INVESTIGATION_REPORT.txt").write_text(
        "\n".join(
            [
                "Win Rate: 91.67%",
                "Only 2 of 12 trades matched real BTC market data.",
                "Estimated $216-324 in unreported costs",
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / "FINAL_STRATEGY.txt").write_text(
        "Win Rate: 60-75%\nThe practical replacement is VWAP Scalper Pro.",
        encoding="utf-8",
    )
    (tmp_path / "backtest_results.txt").write_text(
        "\n".join(
            [
                "DATASET 1",
                "Win Rate: 40.00%",
                "DATASET 2",
                "Win Rate: 86.67%",
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / "timing_analysis_report.txt").write_text(
        "CONFIDENCE LEVEL: 95%",
        encoding="utf-8",
    )
    (tmp_path / "FINAL_DELIVERABLES.txt").write_text(
        "EXPECTED WIN RATE:         91.67%",
        encoding="utf-8",
    )
    (tmp_path / "strategy_synthesis_summary.txt").write_text(
        "The 91.67% win rate is achievable",
        encoding="utf-8",
    )
    (tmp_path / "bybit_microstructure_scalper.py").write_text(
        "Target: 91.67% Win Rate Replication",
        encoding="utf-8",
    )
    (tmp_path / "bybit_price_discrepancy_investigation_report.md").write_text(
        "Bybit testnet likely explains the mismatch.",
        encoding="utf-8",
    )
    (tmp_path / "final_strategy.py").write_text(
        "# production-ready replacement",
        encoding="utf-8",
    )

    report = dashboard_generator._build_btc_strategy_replication_report(tmp_path)

    assert report is not None
    assert report["verdict"]["status"] == "not_replicable"
    assert report["metrics"]["matched_real_trades"] == 2
    assert report["metrics"]["trade_count"] == 12
    assert report["metrics"]["best_backtest_win_rate_pct"] == 86.67
    assert report["metrics"]["automation_confidence_pct"] == 95.0
    assert report["metrics"]["realistic_win_rate_range"] == "60-75%"
    assert report["metrics"]["contradiction_count"] == 3
    assert any(
        finding["severity"] == "high" for finding in report["review_findings"]
    )
    assert {
        artifact["name"] for artifact in report["superseded_artifacts"]
    } == {
        "FINAL_DELIVERABLES.txt",
        "strategy_synthesis_summary.txt",
        "bybit_microstructure_scalper.py",
    }
    assert {
        artifact["name"] for artifact in report["final_artifacts"]
    } >= {
        "FINAL_INVESTIGATION_REPORT.txt",
        "FINAL_STRATEGY.txt",
        "backtest_results.txt",
        "final_strategy.py",
    }


# ── B10 Path B: _build_ueps_kpi_sidecar ─────────────────────────────────────

def _make_ueps_pick(symbol: str, entry: float = 100.0) -> dict:
    return {
        "symbol": symbol,
        "source_system": "ueps",
        "direction": "LONG",
        "entry_price": entry,
        "take_profit": entry * 1.08,
        "stop_loss": entry * 0.95,
        "score": 55.0,
        "confidence": 0.72,
        "age_hours": 4.5,
        "pnl_pct": 0.0,
        "concept_family": "long_term_value",
        "strategy": "magic_formula_x_piotroski_x_acquirers",
    }


def test_build_ueps_kpi_sidecar_empty_returns_empty_status() -> None:
    result = dashboard_generator._build_ueps_kpi_sidecar([])
    assert result["status"] == "empty"
    assert result["open_positions"] == 0
    assert result["aggregate"] is None
    assert result["picks"] == []


def test_build_ueps_kpi_sidecar_excludes_non_ueps_picks() -> None:
    non_ueps = {
        "symbol": "AAPL",
        "source_system": "goldmine_stocks",
        "direction": "LONG",
        "entry_price": 200.0,
        "take_profit": 216.0,
        "stop_loss": 190.0,
        "score": 70.0,
    }
    result = dashboard_generator._build_ueps_kpi_sidecar([non_ueps])
    assert result["status"] == "empty"
    assert result["open_positions"] == 0


def test_build_ueps_kpi_sidecar_with_ueps_picks() -> None:
    picks = [_make_ueps_pick("QCOM", 202.0), _make_ueps_pick("META", 600.0)]
    result = dashboard_generator._build_ueps_kpi_sidecar(picks)

    assert result["status"] == "active"
    assert result["open_positions"] == 2
    assert set(result["tickers"]) == {"QCOM", "META"}
    assert result["strategies"] == ["magic_formula_x_piotroski_x_acquirers"]

    agg = result["aggregate"]
    assert agg is not None
    assert agg["n_closed"] == 0
    assert agg["closed_wr"] is None
    assert agg["closed_pf"] is None
    assert abs(agg["avg_tp_pct"] - 8.0) < 0.1
    assert abs(agg["avg_sl_pct"] - (-5.0)) < 0.1
    assert abs(agg["avg_rr"] - 1.6) < 0.1
    assert abs(agg["avg_confidence"] - 0.72) < 0.01
    assert abs(agg["avg_score"] - 55.0) < 0.1
    assert len(result["picks"]) == 2


def test_build_ueps_kpi_sidecar_message_mentions_accumulating() -> None:
    picks = [_make_ueps_pick("JNJ")]
    result = dashboard_generator._build_ueps_kpi_sidecar(picks)
    assert "accumulating" in result["message"].lower() or "Accumulating" in result["message"]
