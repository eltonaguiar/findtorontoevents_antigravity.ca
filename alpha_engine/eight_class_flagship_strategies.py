"""One WINNING strategy per asset class — backtest or walk-forward validated.

Switched 2026-06-01 from experimental flagships to measured winners.
Paper-pilot until forward n>=20 + full 8-layer pass.

Wire-Up: alpha_engine/priority_picks_emitter.py
"""
from __future__ import annotations

import logging
import os
from typing import Any

from alpha_engine.protocol_layer25 import normalize_pick_for_emitter

logger = logging.getLogger(__name__)


def _gen_crypto() -> list[dict[str, Any]]:
    from alpha_engine.winners.crypto_fear_greed_winner import generate_crypto_fear_greed_winner_picks
    picks = generate_crypto_fear_greed_winner_picks()
    if picks:
        return picks
    from alpha_engine.winners.crypto_multi_day_momentum_winner import (
        generate_crypto_multi_day_momentum_winner_picks,
    )
    picks = generate_crypto_multi_day_momentum_winner_picks()
    if picks:
        return picks
    from alpha_engine.crypto_vol_regime_accumulation import generate_vol_regime_accumulation_picks
    picks = generate_vol_regime_accumulation_picks()
    if picks:
        return picks
    from alpha_engine.winners.crypto_funding_carry_winner import generate_crypto_funding_carry_winner_picks
    return generate_crypto_funding_carry_winner_picks()


def _gen_equity() -> list[dict[str, Any]]:
    from alpha_engine.winners.equity_sector_rotation_winner import generate_equity_sector_rotation_winner_picks
    picks = generate_equity_sector_rotation_winner_picks()
    if picks:
        return picks
    from alpha_engine.equity_sector_dispersion_convergence import generate_sector_dispersion_convergence_picks
    return generate_sector_dispersion_convergence_picks()


def _gen_etf() -> list[dict[str, Any]]:
    from alpha_engine.winners.etf_sector_momentum_winner import generate_etf_sector_momentum_winner_picks
    picks = generate_etf_sector_momentum_winner_picks()
    if picks:
        return picks
    from alpha_engine.etf_factor_regime_rotation import generate_etf_factor_regime_rotation_picks
    return generate_etf_factor_regime_rotation_picks()


def _gen_forex() -> list[dict[str, Any]]:
    from alpha_engine.fx_carry_vix_regime import generate_fx_carry_vix_regime_picks
    picks = generate_fx_carry_vix_regime_picks()
    if picks:
        return picks
    from alpha_engine.fx_dxy_divergence import generate_picks
    picks = generate_picks()
    if picks:
        return picks
    from alpha_engine.fx_cross_pair_momentum_correlation_break import generate_fx_cross_pair_momentum_picks
    return generate_fx_cross_pair_momentum_picks()


def _gen_commodity() -> list[dict[str, Any]]:
    os.environ.setdefault("COMMODITY_SEASONAL_ENABLED", "1")
    os.environ.setdefault("COMMODITY_SEASONAL_CROPS", "WHEAT,COTTON")
    from alpha_engine.commodity_seasonal import generate_picks
    picks = generate_picks()
    if picks:
        return picks
    from alpha_engine.winners.commodity_cross_momentum_winner import (
        generate_commodity_cross_momentum_winner_picks,
    )
    picks = generate_commodity_cross_momentum_winner_picks()
    if picks:
        return picks
    from alpha_engine.commodity_currency_beta_divergence import generate_commodity_currency_divergence_picks
    return generate_commodity_currency_divergence_picks()


def _gen_futures() -> list[dict[str, Any]]:
    from alpha_engine.winners.futures_tsmom_winner import generate_futures_tsmom_winner_picks
    picks = generate_futures_tsmom_winner_picks()
    if picks:
        return picks
    from alpha_engine.futures_cot_extreme_positioning import generate_futures_cot_extreme_picks
    return generate_futures_cot_extreme_picks()


def _gen_bond() -> list[dict[str, Any]]:
    from alpha_engine.winners.bond_hyg_lqd_winner import generate_bond_hyg_lqd_winner_picks
    picks = generate_bond_hyg_lqd_winner_picks()
    if picks:
        return picks
    from alpha_engine.bond_real_rate_momentum import generate_bond_real_rate_momentum_picks
    return generate_bond_real_rate_momentum_picks()


def _gen_cheap_stocks() -> list[dict[str, Any]]:
    from alpha_engine.winners.cheap_stock_momentum_winner import generate_cheap_stock_momentum_winner_picks
    return generate_cheap_stock_momentum_winner_picks()


def _gen_ipo() -> list[dict[str, Any]]:
    from alpha_engine.winners.ipo_post_listing_winner import generate_ipo_post_listing_winner_picks
    return generate_ipo_post_listing_winner_picks()


def _gen_prediction() -> list[dict[str, Any]]:
    try:
        from alpha_engine.polymarket_signals import generate_polymarket_picks
        raw = generate_polymarket_picks()
    except Exception as e:
        logger.warning("Polymarket picks unavailable: %s", e)
        return []

    out: list[dict[str, Any]] = []
    for p in raw[:5]:
        pm = p.get("polymarket_data") or {}
        entry = float(p.get("entry_price") or pm.get("probability") or 0)
        if entry <= 0 or entry >= 1:
            continue
        direction = str(p.get("direction", "LONG")).upper()
        conf = float(p.get("confidence", 0.62))
        tp = p.get("take_profit") or min(0.95, entry + 0.12)
        sl = p.get("stop_loss") or max(0.05, entry - 0.12)
        out.append({
            "symbol": p.get("symbol") or "POLYMARKET",
            "asset_class": "PREDICTION_MARKETS",
            "direction": direction,
            "strategy": "unique_prediction_market_bts_consensus",
            "source_system": "polymarket_bts_consensus_v1",
            "confidence": min(0.78, conf),
            "entry_price": entry,
            "take_profit": float(tp),
            "stop_loss": float(sl),
            "forced_resolution": {
                "max_hold_hours": 72,
                "tp_pct": 12.0,
                "sl_pct": 12.0,
                "time_exit_at_market": True,
            },
            "reason": pm.get("reason") or p.get("reason") or "Polymarket live API consensus",
            "paper_pilot": True,
            "extra": {
                "live_api": True,
                "expected_slippage_bps": 25,
                "market_id": pm.get("market_id"),
                "question": pm.get("question"),
            },
        })
    return out


FLAGSHIP_BY_CLASS: dict[str, dict[str, Any]] = {
    "CRYPTO": {
        "strategy": "st_fear_greed_contrarian_winner",
        "unique_edge": "WF: FGI≤25 PF 2.50; fallback ST multi-day momentum PF 3.84",
        "backtest_evidence": "alpha_engine/data/walkforward_results.json",
        "tier": "TIER_3",
        "not_mean_reversion_monoculture": True,
        "generator": _gen_crypto,
    },
    "EQUITY": {
        "strategy": "equity_sector_rotation",
        "unique_edge": "Sector dual-momentum top-3: 51.4% WR, PF 1.27 (baby backtest)",
        "backtest_evidence": "audit_dashboard/data/equity_baby_strategies_backtest.json",
        "tier": "TIER_3",
        "not_mean_reversion_monoculture": True,
        "generator": _gen_equity,
    },
    "ETF": {
        "strategy": "etf_sector_momentum_rotation",
        "unique_edge": "SPDR 3m momentum top-3; VIX-filtered book PF 2.06",
        "backtest_evidence": "audit_dashboard/data/etf_rotation_vix_regime_backtest.json",
        "tier": "TIER_2",
        "not_mean_reversion_monoculture": True,
        "generator": _gen_etf,
    },
    "FOREX": {
        "strategy": "fx_carry_vix_regime",
        "unique_edge": "Top carry pairs when VIX<20; flat when VIX≥25 (Brunnermeier et al. 2009)",
        "backtest_evidence": "live VIX-gated carry; DXY divergence as fallback",
        "tier": "REHAB",
        "not_mean_reversion_monoculture": True,
        "generator": _gen_forex,
    },
    "COMMODITY": {
        "strategy": "commodity_seasonal_planting_harvest",
        "unique_edge": "WHEAT+CT seasonal PF 1.37; fallback cross-momentum book",
        "backtest_evidence": "reports/backtest_commodity_seasonal_2026_05_31_2358Z.md",
        "tier": "TIER_3",
        "not_mean_reversion_monoculture": True,
        "generator": _gen_commodity,
    },
    "FUTURES": {
        "strategy": "futures_tsmom_winner",
        "unique_edge": "12m TS-momentum book: 58.1% WR, PF 1.68",
        "backtest_evidence": "audit_dashboard/data/futures_ts_momentum_backtest.json",
        "tier": "TIER_2",
        "not_mean_reversion_monoculture": True,
        "generator": _gen_futures,
        "probation": True,
    },
    "BOND": {
        "strategy": "bond_hyg_lqd_momentum_winner",
        "unique_edge": "HYG/LQD 6m momentum: PF 1.65 baseline",
        "backtest_evidence": "audit_dashboard/data/bond_credit_spread_overlay_backtest.json",
        "tier": "TIER_2",
        "not_mean_reversion_monoculture": True,
        "generator": _gen_bond,
    },
    "PREDICTION_MARKETS": {
        "strategy": "unique_prediction_market_bts_consensus",
        "unique_edge": "Live Polymarket consensus + BTS scoring intent (Dai et al. 2021)",
        "not_mean_reversion_monoculture": True,
        "generator": _gen_prediction,
    },
    "CHEAP_STOCKS": {
        "strategy": "cheap_stock_cross_momentum_winner",
        "unique_edge": "$2–$12 liquid momentum top-5: backtest WR 61%, PF 2.79",
        "backtest_evidence": "audit_dashboard/data/cheap_stock_momentum_backtest.json",
        "tier": "TIER_2",
        "not_mean_reversion_monoculture": True,
        "generator": _gen_cheap_stocks,
        "probation": True,
    },
    "IPO": {
        "strategy": "ipo_post_listing_momentum_long",
        "unique_edge": "T+90 LONG window (lockup SHORT killed PF 0.18); REHAB until n≥100",
        "backtest_evidence": "audit_dashboard/data/ipo_post_listing_long_backtest.json",
        "tier": "REHAB",
        "not_mean_reversion_monoculture": True,
        "generator": _gen_ipo,
    },
}


def _deduplicate_by_symbol_direction(picks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep highest-confidence pick per (symbol, direction).
    Resolve LONG+SHORT conflicts on same symbol by keeping dominant side.
    P0 §15 Trap #2 fix — dedup at emission point before DB write.
    """
    best: dict[tuple[str, str], dict[str, Any]] = {}
    for p in picks:
        sym = str(p.get("symbol", "")).strip().upper()
        direction = str(p.get("direction") or p.get("signal_type") or "LONG").strip().upper()
        direction = "SHORT" if direction in ("SELL", "SHORT") else "LONG"
        key = (sym, direction)
        conf = float(p.get("confidence") or 0)
        if key not in best or conf > float(best[key].get("confidence") or 0):
            best[key] = p

    # Resolve conflicts: same symbol with both LONG and SHORT
    by_symbol: dict[str, list[dict[str, Any]]] = {}
    for p in best.values():
        sym = str(p.get("symbol", "")).strip().upper()
        by_symbol.setdefault(sym, []).append(p)

    final: list[dict[str, Any]] = []
    for sym, group in by_symbol.items():
        if len(group) <= 1:
            final.extend(group)
            continue
        group.sort(key=lambda p: float(p.get("confidence") or 0), reverse=True)
        winner = group[0]
        w_dir = str(winner.get("direction") or winner.get("signal_type") or "LONG").strip().upper()
        w_dir = "SHORT" if w_dir in ("SELL", "SHORT") else "LONG"
        logger.info("[DEDUP] %s: conflict resolved → %s (conf=%.2f, strat=%s)",
                    sym, w_dir, float(winner.get("confidence", 0)), winner.get("strategy", ""))
        final.append(winner)

    removed = len(picks) - len(final)
    if removed:
        logger.info("[DEDUP] Removed %d picks, kept %d unique", removed, len(final))
    return final


def generate_all_flagship_picks() -> list[dict[str, Any]]:
    """Run all eight class generators; apply Layer 2.5 normalization + dedup."""
    all_picks: list[dict[str, Any]] = []
    for asset_class, spec in FLAGSHIP_BY_CLASS.items():
        try:
            raw_list = spec["generator"]()
        except Exception as e:
            logger.warning("%s flagship failed: %s", asset_class, e)
            continue
        for raw in raw_list:
            raw.setdefault("asset_class", asset_class)
            norm = normalize_pick_for_emitter(raw)
            if norm is None:
                continue
            norm["flagship_meta"] = {
                "unique_edge": spec["unique_edge"],
                "probation": spec.get("probation", False),
            }
            all_picks.append(norm)
        logger.info("%s: %d raw → kept after L2.5", asset_class, len(raw_list))

    # P0 §15 final safety net (2026-06-01, per 2026-05-31 findings + Claude notes)
    # Post-process all returned picks to guarantee forward_test_only=True / validated=False
    # for the 30 academic strategies, regardless of individual generator behavior.
    for p in all_picks:
        p["forward_test_only"] = True
        p["forward_validated"] = False

    deduped = _deduplicate_by_symbol_direction(all_picks)
    logger.info("ALL: %d picks → %d after dedup", len(all_picks), len(deduped))
    return deduped


if __name__ == "__main__":
    import json
    logging.basicConfig(level=logging.INFO)
    picks = generate_all_flagship_picks()
    print(json.dumps({"n": len(picks), "classes": sorted({p["asset_class"] for p in picks})}, indent=2))
