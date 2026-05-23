"""Tests for alpha_engine.scoring_enhancement (supplementary dashboard ranking)."""

from __future__ import annotations

from datetime import datetime, timezone

from alpha_engine.scoring_enhancement import (
    apply_enhanced_scoring_to_payload,
    compute_enhanced_score,
    confidence_score,
    forward_wr_score,
    strat_symbol_affinity_boost,
)


def test_forward_wr_score_high_n_trusts_sample() -> None:
    s = forward_wr_score(0.65, 25, None, 20, 0.45)
    assert 24.0 <= s <= 30.0


def test_confidence_score_peaks_near_067() -> None:
    assert confidence_score(0.67) > confidence_score(0.5)
    assert confidence_score(0.67) > confidence_score(0.95)


def test_strat_symbol_affinity_fear_greed_dot() -> None:
    cfg_path_rows = [
        {"strategy_substring": "fear_greed_contrarian", "symbol": "DOTUSDT", "boost": 25},
    ]
    b = strat_symbol_affinity_boost("st_fear_greed_contrarian", "DOTUSDT", cfg_path_rows)
    assert b == 25.0


def test_compute_enhanced_score_dot_fear_greed() -> None:
    pick = {
        "strategy": "st_fear_greed_contrarian",
        "symbol": "DOTUSDT",
        "direction": "LONG",
        "regime": "bull",
        "confidence": 0.67,
        "strat_fwd_wr": 0.60,
        "strat_fwd_trades": 30,
        "score": 55,
    }
    score, br, tier = compute_enhanced_score(
        pick, now=datetime(2026, 4, 6, 1, 0, tzinfo=timezone.utc)
    )
    assert score >= 50.0
    assert br["strat_symbol_affinity"] == 25.0
    assert tier in ("ELITE", "HIGH", "STANDARD", "LOW", "SPECULATIVE")


def test_apply_enhanced_scoring_to_payload_adds_ranked() -> None:
    payload = {
        "picks": {
            "active": [
                {
                    "symbol": "BTCUSDT",
                    "strategy": "super_signal_trend",
                    "direction": "LONG",
                    "confidence": 0.7,
                    "strat_fwd_wr": 0.55,
                    "strat_fwd_trades": 25,
                },
                {
                    "symbol": "DOTUSDT",
                    "strategy": "st_fear_greed_contrarian",
                    "direction": "LONG",
                    "regime": "bull",
                    "confidence": 0.67,
                    "strat_fwd_wr": 0.70,
                    "strat_fwd_trades": 40,
                },
            ],
            "smart_picks": [],
            "recent_closed": [],
        },
        "summary": {},
    }
    apply_enhanced_scoring_to_payload(payload)
    assert "enhanced_score" in payload["picks"]["active"][0]
    ranked = payload["picks"].get("enhanced_ranked") or []
    assert len(ranked) >= 1
    assert ranked[0]["symbol"] == "DOTUSDT"
