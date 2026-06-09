"""Academic Strategies Emitter — Paper-pilot batch for 30 literature-backed strategies.

Wiring plan per TESTING_PROTOCOL §0.6 + Wire-Up Rule:
- All picks carry forward_test_only=True / forward_validated=False.
- Called by alpha_engine.priority_picks_emitter as secondary source.
- Institutional backtest suite (bootstrap 10K, Holm FDR, Wilson LB) is the
  promotion gate out of paper-pilot.

Status (2026-06-01):
  CRYPTO 5/5 wired  |  EQUITY 5/5 wired
  FOREX  5/5 wired  |  COMMODITY 5/5 wired
  ETF    5/5 wired  |  BOND     5/5 wired
  MEME   1/3 wired (prototype)
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from alpha_engine.protocol_layer25 import normalize_pick_for_emitter

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Wrapper registry: strategy_name -> callable that returns list[dict]
# ---------------------------------------------------------------------------

_GENERATORS: dict[str, tuple[str, Any]] = {}


def _register(name: str, asset_class: str, fn: Any) -> None:
    _GENERATORS[name] = (asset_class, fn)


# ---------------------------------------------------------------------------
# CRYPTO (5/5)
# ---------------------------------------------------------------------------
try:
    from alpha_engine.crypto_funding_rate_carry import generate_funding_rate_carry_picks as _gen_crypto_funding
    _register("crypto_funding_rate_carry", "CRYPTO", _gen_crypto_funding)
except Exception as e:
    logger.debug("crypto_funding_rate_carry not available: %s", e)

try:
    from alpha_engine.crypto_volatility_regime import generate_volatility_regime_picks as _gen_crypto_vol
    _register("crypto_volatility_regime", "CRYPTO", _gen_crypto_vol)
except Exception as e:
    logger.debug("crypto_volatility_regime not available: %s", e)

try:
    from alpha_engine.crypto_mean_reversion_zscore import generate_mean_reversion_zscore_picks as _gen_crypto_mr
    _register("crypto_mean_reversion_zscore", "CRYPTO", _gen_crypto_mr)
except Exception as e:
    logger.debug("crypto_mean_reversion_zscore not available: %s", e)

try:
    from alpha_engine.crypto_whale_accumulation import generate_whale_accumulation_picks as _gen_crypto_whale
    _register("crypto_whale_accumulation", "CRYPTO", _gen_crypto_whale)
except Exception as e:
    logger.debug("crypto_whale_accumulation not available: %s", e)

try:
    from alpha_engine.crypto_liquidation_fade import generate_liquidation_fade_picks as _gen_crypto_liq
    _register("crypto_liquidation_fade", "CRYPTO", _gen_crypto_liq)
except Exception as e:
    logger.debug("crypto_liquidation_fade not available: %s", e)

# Mutation-validated paper-pilot strategy (M-107 mutation hunt 2026-06-01).
# Baseline keltner_bounce failed T3 (PF 0.995 NO_EDGE). The wider-band
# variant (EMA=20, ATR=10, mult=3.0) passes T3 in the 1y rigorous backtest:
# PF 1.145, WR 46.4%, n=677, DSR 7.88, PF_LB95 1.10.
# Tagged source_system='academic_keltner_bounce_v2_wide' by the emitter
# loop so pf_registry attributes per-strategy. Paper-pilot only — 30+ day
# rolling proof + PF_LB > 1.05 on rolling 60d required before sizing.
try:
    from alpha_engine.dormant_winners_wrappers import generate_keltner_bounce_v2_wide_picks as _gen_keltner_v2
    _register("keltner_bounce_v2_wide", "CRYPTO", _gen_keltner_v2)
except Exception as e:
    logger.debug("keltner_bounce_v2_wide not available: %s", e)

# TSMOM volatility-scaled (Moskowitz-Ooi-Pedersen 2012) — time-series momentum on
# top-volume crypto with a BTC 50-SMA regime filter + volatility targeting. Exits on
# momentum sign-flip (SIGNAL-BASED), which structurally avoids the TIME_EXPIRED
# failure mode that sinks fixed-TP/SL sleeves (56-94% expiry per 2026-06-06 audit).
# Wired 2026-06-09: was a genuine orphan (zero importers); stdlib-only deps; no-arg
# callable; emits signal_type BUY/SELL (direction injected in the emit loop below).
# Paper-pilot only (forward_test_only=True) until PF_LB95 > 1.05 on rolling 60d.
# residual_momentum was deliberately NOT added here — it already emits live via
# scanner.run_strategies (forward_validator cron); re-registering would double-count
# its pf_registry attribution. basis_carry / bond_strategy_harness excluded (broken
# imports / non-pick return shape per workflow wxvpxigh2 adversarial verify).
try:
    from alpha_engine.tsmom_strategy import generate_tsmom_picks as _gen_tsmom
    _register("tsmom_volscaled", "CRYPTO", _gen_tsmom)
except Exception as e:
    logger.debug("tsmom_volscaled not available: %s", e)


# ---------------------------------------------------------------------------
# EQUITY (5/5 wired)
# ---------------------------------------------------------------------------
try:
    from alpha_engine.equity_qmom_residual import equity_qmom_residual_signals as _eq_qmom_raw
    def _gen_eq_qmom():
        # Month-end rebalance per Asness et al.; force=False respects gate
        return _eq_qmom_raw(force=False)
    _register("equity_qmom_residual", "EQUITY", _gen_eq_qmom)
except Exception as e:
    logger.debug("equity_qmom_residual not available: %s", e)

try:
    from alpha_engine.equity_post_earnings_drift import equity_post_earnings_drift_signals as _eq_pead_raw
    _register("equity_post_earnings_drift", "EQUITY", _eq_pead_raw)
except Exception as e:
    logger.debug("equity_post_earnings_drift not available: %s", e)

try:
    from alpha_engine.equity_insider_buying import generate_picks as _gen_eq_insider
    _register("equity_insider_buying", "EQUITY", _gen_eq_insider)
except Exception as e:
    logger.debug("equity_insider_buying not available: %s", e)

try:
    from alpha_engine.equity_short_squeeze import generate_picks as _gen_eq_squeeze
    _register("equity_short_squeeze", "EQUITY", _gen_eq_squeeze)
except Exception as e:
    logger.debug("equity_short_squeeze not available: %s", e)

try:
    from alpha_engine.equity_sector_rotation import generate_picks as _gen_eq_sector
    _register("equity_sector_rotation", "EQUITY", _gen_eq_sector)
except Exception as e:
    logger.debug("equity_sector_rotation not available: %s", e)


# ---------------------------------------------------------------------------
# FOREX (5/5)
# ---------------------------------------------------------------------------
try:
    from alpha_engine.fx_carry_vix_regime import generate_fx_carry_vix_regime_picks as _gen_fx_carry
    _register("fx_carry_vix_regime", "FOREX", _gen_fx_carry)
except Exception as e:
    logger.debug("fx_carry_vix_regime not available: %s", e)

try:
    from alpha_engine.fx_overnight_reversal import generate_picks as _gen_fx_overnight
    _register("fx_overnight_reversal", "FOREX", _gen_fx_overnight)
except Exception as e:
    logger.debug("fx_overnight_reversal not available: %s", e)

try:
    from alpha_engine.fx_asian_range_break import generate_picks as _gen_fx_asian
    _register("fx_asian_range_break", "FOREX", _gen_fx_asian)
except Exception as e:
    logger.debug("fx_asian_range_break not available: %s", e)

try:
    from alpha_engine.fx_dxy_divergence import generate_picks as _gen_fx_dxy
    _register("fx_dxy_divergence", "FOREX", _gen_fx_dxy)
except Exception as e:
    logger.debug("fx_dxy_divergence not available: %s", e)

try:
    from alpha_engine.fx_cot_extremes import generate_picks as _gen_fx_cot
    _register("fx_cot_extremes", "FOREX", _gen_fx_cot)
except Exception as e:
    logger.debug("fx_cot_extremes not available: %s", e)


# ---------------------------------------------------------------------------
# COMMODITY (5/5)
# ---------------------------------------------------------------------------
try:
    from alpha_engine.commodity_basis_carry import generate_commodity_basis_carry_picks as _gen_comm_basis
    _register("commodity_basis_carry", "COMMODITY", _gen_comm_basis)
except Exception as e:
    logger.debug("commodity_basis_carry not available: %s", e)

try:
    from alpha_engine.commodity_inventory_report import generate_picks as _gen_comm_inv
    _register("commodity_inventory_report", "COMMODITY", _gen_comm_inv)
except Exception as e:
    logger.debug("commodity_inventory_report not available: %s", e)

try:
    from alpha_engine.commodity_gold_silver_ratio import generate_picks as _gen_comm_gs
    _register("commodity_gold_silver_ratio", "COMMODITY", _gen_comm_gs)
except Exception as e:
    logger.debug("commodity_gold_silver_ratio not available: %s", e)

try:
    from alpha_engine.commodity_cross_momentum import generate_picks as _gen_comm_cm
    _register("commodity_cross_momentum", "COMMODITY", _gen_comm_cm)
except Exception as e:
    logger.debug("commodity_cross_momentum not available: %s", e)

try:
    from alpha_engine.commodity_seasonal_v2 import generate_picks as _gen_comm_season
    _register("commodity_seasonal_v2", "COMMODITY", _gen_comm_season)
except Exception as e:
    logger.debug("commodity_seasonal_v2 not available: %s", e)


# ---------------------------------------------------------------------------
# ETF (5/5)
# ---------------------------------------------------------------------------
try:
    from alpha_engine.etf_managed_futures_proxy import generate_etf_managed_futures_picks as _gen_etf_mfp
    _register("etf_managed_futures_proxy", "ETF", _gen_etf_mfp)
except Exception as e:
    logger.debug("etf_managed_futures_proxy not available: %s", e)

try:
    from alpha_engine.etf_sector_momentum_rotation import generate_sector_momentum_rotation_picks as _gen_etf_smr
    _register("etf_sector_momentum_rotation", "ETF", _gen_etf_smr)
except Exception as e:
    logger.debug("etf_sector_momentum_rotation not available: %s", e)

try:
    from alpha_engine.etf_risk_parity import generate_risk_parity_picks as _gen_etf_rp
    _register("etf_risk_parity", "ETF", _gen_etf_rp)
except Exception as e:
    logger.debug("etf_risk_parity not available: %s", e)

try:
    from alpha_engine.etf_vix_term_structure import generate_vix_term_structure_picks as _gen_etf_vix
    _register("etf_vix_term_structure", "ETF", _gen_etf_vix)
except Exception as e:
    logger.debug("etf_vix_term_structure not available: %s", e)

try:
    from alpha_engine.etf_country_rotation import generate_country_rotation_picks as _gen_etf_cr
    _register("etf_country_rotation", "ETF", _gen_etf_cr)
except Exception as e:
    logger.debug("etf_country_rotation not available: %s", e)


# ---------------------------------------------------------------------------
# BOND (5/5)
# ---------------------------------------------------------------------------
try:
    from alpha_engine.bond_tlt_trend_vol_scaled import generate_bond_tlt_trend_vol_picks as _gen_bond_tlt
    _register("bond_tlt_trend_vol_scaled", "BOND", _gen_bond_tlt)
except Exception as e:
    logger.debug("bond_tlt_trend_vol_scaled not available: %s", e)

try:
    from alpha_engine.bond_credit_spread import generate_bond_credit_spread_picks as _gen_bond_cs
    _register("bond_credit_spread", "BOND", _gen_bond_cs)
except Exception as e:
    logger.debug("bond_credit_spread not available: %s", e)

try:
    from alpha_engine.bond_duration_rotation import generate_bond_duration_rotation_picks as _gen_bond_dr
    _register("bond_duration_rotation", "BOND", _gen_bond_dr)
except Exception as e:
    logger.debug("bond_duration_rotation not available: %s", e)

try:
    from alpha_engine.bond_yield_curve_slope import generate_bond_yield_curve_slope_picks as _gen_bond_ycs
    _register("bond_yield_curve_slope", "BOND", _gen_bond_ycs)
except Exception as e:
    logger.debug("bond_yield_curve_slope not available: %s", e)

try:
    from alpha_engine.bond_tips_breakeven import generate_bond_tips_breakeven_picks as _gen_bond_tips
    _register("bond_tips_breakeven", "BOND", _gen_bond_tips)
except Exception as e:
    logger.debug("bond_tips_breakeven not available: %s", e)


# ---------------------------------------------------------------------------
# MEME (1/3 wired — prototype)
# ---------------------------------------------------------------------------
try:
    from alpha_engine.meme_momentum_squeeze import generate_meme_momentum_squeeze_picks as _gen_meme
    _register("meme_momentum_squeeze", "MEME", _gen_meme)
except Exception as e:
    logger.debug("meme_momentum_squeeze not available: %s", e)


# ---------------------------------------------------------------------------
# Emitter core
# ---------------------------------------------------------------------------

def generate_academic_picks() -> list[dict[str, Any]]:
    """Run all wired academic strategy generators; return protocol-normalized picks."""
    all_picks: list[dict[str, Any]] = []
    for strategy_name, (asset_class, fn) in _GENERATORS.items():
        try:
            raw_list = fn()
        except Exception as e:
            logger.warning("%s failed: %s", strategy_name, e)
            continue
        if not raw_list:
            continue
        for raw in raw_list:
            raw.setdefault("asset_class", asset_class)
            raw.setdefault("strategy", strategy_name)
            # Direction injection (2026-06-09): TSMOM/CTA sleeves emit signal_type
            # BUY/SELL but normalize_pick_for_emitter reads ONLY `direction`
            # (defaults LONG), so a SELL pick would be silently mislabeled LONG and
            # given backwards TP/SL. Map signal_type -> direction before normalize.
            if not raw.get("direction") and raw.get("signal_type"):
                _st = str(raw["signal_type"]).upper()
                raw["direction"] = "SHORT" if _st in ("SELL", "SHORT") else "LONG"
            # 2026-06-01 wire-up: distinct source_system per strategy so
            # pf_registry / dashboard can attribute WR/PF per academic strategy.
            # Without this, all 30+ academic strategies collapse into one
            # bucket (or NULL) and we cannot tell which is producing edge.
            raw.setdefault("source_system", f"academic_{strategy_name}")
            norm = normalize_pick_for_emitter(raw)
            if norm is None:
                continue
            norm["forward_test_only"] = True
            norm["forward_validated"] = False
            norm["paper_pilot"] = True
            norm["academic_source"] = True
            # P0 §15 dedup harmonization (TON-validated 2026-06-01): inject canonical ID at emission
            from alpha_engine.dedup import build_canonical_outcomes_pick_id
            norm.setdefault("id", build_canonical_outcomes_pick_id(norm))
            all_picks.append(norm)
        logger.info("%s: %d picks", strategy_name, len(raw_list))
    return all_picks


if __name__ == "__main__":
    import json, sys
    logging.basicConfig(level=logging.INFO)
    picks = generate_academic_picks()
    print(json.dumps({"n": len(picks), "strategies": sorted({p["strategy"] for p in picks})}, indent=2))
    sys.exit(0 if picks else 1)
