from __future__ import annotations

from datetime import datetime, timedelta, timezone

from copy_trader_intel.polymarket_scraper import (
    PROFILE_BAYES_PRIOR_WIN_RATE,
    _apply_copyability_gate,
    _bayes_win_rate,
    _classify_wallet_archetype,
    _compute_concentration_metrics,
    _compute_recent_form,
    _detect_latency_arb,
    _evaluate_entry_quality,
    _profile_rank_score,
    _profile_rank_sort_key,
    _resolve_direction_conflicts,
)


def test_bayes_win_rate_uses_prior_for_empty_sample() -> None:
    assert _bayes_win_rate(0, 0, prior_mean=0.62, prior_strength=20.0) == 0.62


def test_profile_rank_score_rewards_larger_samples() -> None:
    small_sample = _profile_rank_score(wins=8, decisions=10)
    larger_sample = _profile_rank_score(wins=32, decisions=40)
    assert larger_sample > small_sample


def test_profile_rank_sort_key_prefers_copyable_recent_established_wallets() -> None:
    stronger = {
        "established_crypto_history": True,
        "copyable_archetype": True,
        "crypto_recent_decisions_30d": 8,
        "crypto_recent_score_30d": 0.70,
        "crypto_recent_decisions_90d": 16,
        "crypto_recent_score_90d": 0.66,
        "crypto_total_pnl": 12000,
        "crypto_decisions": 24,
        "crypto_win_rate_bayes": 0.82,
        "crypto_profile_score": 0.61,
        "crypto_profit_rank": 3,
    }
    weaker = {
        "established_crypto_history": True,
        "copyable_archetype": False,
        "crypto_recent_decisions_30d": 8,
        "crypto_recent_score_30d": 0.70,
        "crypto_recent_decisions_90d": 16,
        "crypto_recent_score_90d": 0.66,
        "crypto_total_pnl": 15000,
        "crypto_decisions": 24,
        "crypto_win_rate_bayes": 0.84,
        "crypto_profile_score": 0.63,
        "crypto_profit_rank": 2,
    }
    assert _profile_rank_sort_key(stronger) > _profile_rank_sort_key(weaker)


def test_recent_form_and_concentration_metrics_capture_windows_and_dominance() -> None:
    now = datetime.now(timezone.utc)
    directional_history = [
        {"market_ts": (now - timedelta(days=7)).isoformat(), "net_pnl": 120.0},
        {"market_ts": (now - timedelta(days=20)).isoformat(), "net_pnl": -40.0},
        {"market_ts": (now - timedelta(days=70)).isoformat(), "net_pnl": 80.0},
        {"market_ts": (now - timedelta(days=120)).isoformat(), "net_pnl": 500.0},
    ]

    recent = _compute_recent_form(directional_history)
    assert recent["crypto_recent_decisions_30d"] == 2
    assert recent["crypto_recent_pnl_30d"] == 80.0
    assert recent["crypto_recent_decisions_90d"] == 3
    assert recent["crypto_recent_score_30d"] > 0.0
    assert recent["crypto_recent_win_rate_bayes_30d"] > recent["crypto_recent_win_rate_30d"]

    concentration = _compute_concentration_metrics(
        {
            "BTCUSDT": {"total_pnl": 900.0, "decisions": 9},
            "ETHUSDT": {"total_pnl": 100.0, "decisions": 3},
        }
    )
    assert concentration["crypto_top_symbol"] == "BTCUSDT"
    assert concentration["crypto_top_symbol_pnl_share"] == 0.9
    assert concentration["crypto_concentration_flag"] is True
    assert concentration["crypto_concentration_penalty"] > 0.0


def test_wallet_archetype_flags_hft_micro_as_non_copyable() -> None:
    history = [
        {
            "title": "Bitcoin up or down in 15 minutes?",
            "dominant_avg_price": 0.51,
        }
        for _ in range(6)
    ]
    history.extend(
        [
            {
                "title": "Ethereum up or down in 5 minutes?",
                "dominant_avg_price": 0.49,
            }
            for _ in range(4)
        ]
    )

    archetype = _classify_wallet_archetype(
        directional_history=history,
        qualified_symbols={"BTCUSDT": {}, "ETHUSDT": {}},
        leaderboard_volume=10_000_000,
    )
    assert archetype["wallet_archetype"] == "hft_micro"
    assert archetype["copyable_archetype"] is False
    assert archetype["wallet_archetype_hft_share"] == 1.0


def test_bayes_profile_prior_is_conservative_for_small_samples() -> None:
    adjusted = _bayes_win_rate(
        8,
        10,
        prior_mean=PROFILE_BAYES_PRIOR_WIN_RATE,
        prior_strength=20.0,
    )
    assert 0.62 < adjusted < 0.80


def test_resolve_direction_conflicts_keeps_only_winning_side() -> None:
    picks = [
        {"symbol": "BTCUSDT", "direction": "LONG", "confidence": 0.80, "id": "l1"},
        {"symbol": "BTCUSDT", "direction": "LONG", "confidence": 0.70, "id": "l2"},
        {"symbol": "BTCUSDT", "direction": "SHORT", "confidence": 0.90, "id": "s1"},
        {"symbol": "ETHUSDT", "direction": "SHORT", "confidence": 0.60, "id": "e1"},
    ]

    resolved = _resolve_direction_conflicts(picks)
    btc = [pick for pick in resolved if pick["symbol"] == "BTCUSDT"]
    eth = [pick for pick in resolved if pick["symbol"] == "ETHUSDT"]

    assert {pick["direction"] for pick in btc} == {"LONG"}
    assert {pick["id"] for pick in btc} == {"l1", "l2"}
    assert len(eth) == 1


def test_detect_latency_arb_flags_short_expiry_micro_markets() -> None:
    now = datetime.now(timezone.utc)
    history = [
        {
            "title": "Bitcoin up or down in 15 minutes?",
            "dominant_avg_price": 0.51,
            "market_ts": (now - timedelta(minutes=10)).isoformat(),
            "end_date": (now + timedelta(minutes=5)).isoformat(),
        }
        for _ in range(12)
    ]

    latency = _detect_latency_arb(history, leaderboard_volume=150_000_000)
    gate = _apply_copyability_gate(
        {"wallet_archetype": "directional_generalist", "copyable_archetype": True},
        latency,
    )

    assert latency["latency_arb_flag"] is True
    assert latency["latency_arb_score"] >= 0.55
    assert latency["latency_arb_short_expiry_share"] == 1.0
    assert gate["copyable_archetype"] is False
    assert gate["copyability_gate_reason"] == "latency_arb"


def test_entry_quality_passes_liquid_multiday_contract() -> None:
    quality = _evaluate_entry_quality(
        directional_notional=18_000.0,
        lead_notional=6_500.0,
        hours_to_expiry=96.0,
        contract_price=0.82,
        market_count=4,
    )

    assert quality["entry_quality_pass"] is True
    assert quality["entry_quality_gate_reason"] == ""
    assert quality["entry_quality_score"] >= 0.75


def test_entry_quality_blocks_micro_expiry_even_with_size() -> None:
    quality = _evaluate_entry_quality(
        directional_notional=9_000.0,
        lead_notional=4_000.0,
        hours_to_expiry=0.2,
        contract_price=0.52,
        market_count=1,
    )

    assert quality["entry_quality_pass"] is False
    assert quality["entry_quality_gate_reason"] == "expiry_horizon"
