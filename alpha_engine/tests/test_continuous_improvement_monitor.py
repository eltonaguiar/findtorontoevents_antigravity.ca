from alpha_engine.continuous_improvement_monitor import (
    build_peer_consensus,
    build_recommendations,
    generate_alerts,
)


def test_build_peer_consensus_detects_conflicts_and_alignment():
    picks = [
        {"symbol": "BTCUSDT", "peer": "alpha_engine", "direction": "LONG", "strategy": "alpha_long"},
        {"symbol": "BTCUSDT", "peer": "copy_trader_intel", "direction": "SHORT", "strategy": "copy_short"},
        {"symbol": "ETHUSDT", "peer": "alpha_engine", "direction": "LONG", "strategy": "alpha_eth"},
        {"symbol": "ETHUSDT", "peer": "paper_trading", "direction": "LONG", "strategy": "paper_eth"},
    ]

    consensus = build_peer_consensus(picks)

    assert consensus["conflict_count"] == 1
    assert consensus["aligned_count"] == 1
    assert consensus["conflicts"][0]["symbol"] == "BTCUSDT"
    assert consensus["aligned"][0]["symbol"] == "ETHUSDT"


def test_generate_alerts_routes_decay_to_rehabilitation_signals():
    sections = {
        "peer_status": {
            "alpha_engine": {"age_minutes": 12},
            "copy_trader_intel": {"age_minutes": 61},
            "paper_trading": {"age_minutes": 5},
        },
        "price_status": {"coverage_pct": 72.0, "missing_symbols": ["NVDA", "EURUSD=X"]},
        "alpha_summary": {"summary": {"win_rate": 0.39}},
        "paper_trading": {"worst_drawdown_pct": 10.1, "worst_portfolio": "derivatives"},
        "by_confidence": {
            "HIGH": {"directional_correctness_pct": 31.0},
            "LOW": {"directional_correctness_pct": 58.0},
        },
        "benchmark": {"alpha_generated_pct": -4.5},
        "peer_consensus": {
            "conflict_count": 1,
            "conflicts": [{"symbol": "BTCUSDT", "direction_counts": {"LONG": 1, "SHORT": 1}}],
        },
        "strategy_watchlist": {
            "rehabilitation_candidates": [
                {
                    "strategy": "winner_pattern_precursor",
                    "win_rate_pct": 16.3,
                    "profit_factor": 0.325,
                    "sharpe": -6.609,
                    "mutation_action": "kimi_inverse_scan",
                }
            ],
            "leaders": [],
        },
        "regime_context": {"regime": {"regime": "CHOPPY"}},
        "topline": {"open_avg_pnl_pct": -2.4},
    }
    previous_snapshot = {"regime": "TRENDING", "open_avg_pnl_pct": 0.5}
    config = {
        "peer_stale_minutes": 45,
        "price_coverage_floor_pct": 80.0,
        "directional_correctness_floor_pct": 45.0,
        "portfolio_drawdown_limit_pct": 8.0,
        "confidence_inversion_gap_pct": 10.0,
        "benchmark_alpha_floor_pct": 0.0,
        "regime_change_pnl_drop_pct": 1.5,
    }

    alerts = generate_alerts(sections, previous_snapshot, config)
    codes = {alert["code"] for alert in alerts}

    assert "PEER_STALE" in codes
    assert "PRICE_COVERAGE_GAP" in codes
    assert "REALIZED_WIN_RATE_BREACH" in codes
    assert "PORTFOLIO_DRAWDOWN_BREACH" in codes
    assert "CONFIDENCE_INVERSION" in codes
    assert "BENCHMARK_LAG" in codes
    assert "PEER_DIRECTION_CONFLICT" in codes
    assert "STRATEGY_DECAY" in codes
    assert "REGIME_SHIFT" in codes


def test_recommendations_use_mutation_language_not_kill_language():
    sections = {
        "regime_context": {"regime": {"regime": "CHOPPY"}},
        "strategy_watchlist": {
            "rehabilitation_candidates": [
                {"strategy": "winner_pattern_precursor", "mutation_action": "kimi_inverse_scan"}
            ],
            "leaders": [],
        },
    }
    alerts = [
        {"code": "STRATEGY_DECAY", "severity": "HIGH"},
        {"code": "PORTFOLIO_DRAWDOWN_BREACH", "severity": "CRITICAL"},
    ]

    recommendations = build_recommendations(sections, alerts)
    serialized = str(recommendations).lower()

    assert "kill" not in serialized
    assert "disable" not in serialized
    assert "mutate" in serialized or "invert" in serialized
