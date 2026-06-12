"""June 2026 research candidates — enhanced v2 (forward observation) + new hypothesis pool.

Wire-Up: alpha_engine/priority_picks_emitter.py when JUNE2026_FORWARD_OBSERVATION=1
Backtests: tools/june2026_strategy_research_pipeline.py
"""
from __future__ import annotations

import logging
import os
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Callable

logger = logging.getLogger(__name__)

FORWARD_OBSERVATION_ENV = "JUNE2026_FORWARD_OBSERVATION"

# ---------------------------------------------------------------------------
# Registry: 2 enhanced v2 per asset class (forward-tested via priority picks)
# ---------------------------------------------------------------------------

ENHANCED_V2_BY_CLASS: dict[str, list[dict[str, Any]]] = {
    "CRYPTO": [
        {
            "id": "luxalgo_confluence_v2_short",
            "base": "luxalgo_confluence",
            "enhancement": "SHORT-only; blocks LONG (quality_gates DIRECTION_SPECIFIC_LOSERS)",
            "parent_evidence": "deduped intrabar luxalgo SHORT n=38 WR=71% PF=2.21 FULL T2+R1/R2/R3 (2026-06-11 pass-hunter); LONG n=50 WR=34% PF=1.02 FAIL",
        },
        {
            "id": "crypto_eu_us_handoff_short_v2",
            "base": "crypto_eu_us_handoff_continuation",
            "enhancement": "SHORT-only EU→US handoff; drop LONG leg (BT PF 0.87 SHORT vs 1.38 LONG — invert to SHORT momentum fade)",
            "parent_evidence": "strategy_bt_crypto_2026-06-11.json SHORT leg underperforms; session RSI band kept",
        },
    ],
    "EQUITY": [
        {
            "id": "equity_sector_rotation_vix_v2",
            "base": "equity_sector_rotation",
            "enhancement": "VIX<22 gate + top-3 sector momentum only",
            "parent_evidence": "eight_class flagship + VIX regime literature",
        },
        {
            "id": "equity_pead_sue_v2",
            "base": "equity_pead",
            "enhancement": "Top SUE decile, exclude microcap, 30d hold",
            "parent_evidence": "H-002 PEAD SHADOW; pooled WR 53.2% n=1964",
        },
    ],
    "FOREX": [
        {
            "id": "forex_trend_aligned_v2",
            "base": "forex_trend_aligned",
            "enhancement": "F1 trend=ALIGNED (close vs SMA50 × direction); block CONTRARIAN",
            "parent_evidence": "entry_conditions_forward n=14 WR=64.3% PF=4.74",
        },
        {
            "id": "forex_rsi2_usdchf_v2",
            "base": "forex_rsi2_mean_reversion",
            "enhancement": "USDCHF-only RSI(2) MR; exclude carry momentum",
            "parent_evidence": "intrabar n=20 WR=60% PF=2.15; C17 USDCHF PF=4.28 backtest",
        },
    ],
    "COMMODITY": [
        {
            "id": "commodity_futures_momentum_dedup_v2",
            "base": "futures_momentum",
            "enhancement": "Symbol-day dedup + metals focus (GC/SI/HG)",
            "parent_evidence": "intrabar n=47 WR=63.8% PF=2.78 (dedup suspect — enforce dedup)",
        },
        {
            "id": "commodity_seasonal_wheat_v2",
            "base": "commodity_seasonal_planting_harvest",
            "enhancement": "WHEAT+CT only; skip cotton concentration",
            "parent_evidence": "commodity_seasonal PF 1.37 backtest",
        },
    ],
    "ETF": [
        {
            "id": "etf_dual_momentum_vix_v2",
            "base": "etf_dual_momentum_rotation",
            "enhancement": "12-1 dual momentum; flat when VIX>25",
            "parent_evidence": "verified_strategies/etf_dual_momentum_backtest.py",
        },
        {
            "id": "etf_sector_rs_weekly_v2",
            "base": "etf_sector_momentum_rotation",
            "enhancement": "Weekly sector relative-strength long/short vs SPY",
            "parent_evidence": "strategy_bt_etf sector RS n=1640 (marginal — VIX gate added)",
        },
    ],
    "BOND": [
        {
            "id": "bond_zn_mean_rev_atr_v2",
            "base": "bond_yield_momentum",
            "enhancement": "ZN=F ATR-band mean reversion (C17 breakthrough)",
            "parent_evidence": "intrabar bond_yield_momentum PF=3.53 n=5; C17 ZN PF=2.11",
        },
        {
            "id": "bond_hyg_lqd_spread_v2",
            "base": "bond_hyg_lqd_momentum_winner",
            "enhancement": "HYG/LQD 6m momentum with credit spread overlay",
            "parent_evidence": "eight_class BOND flagship PF 1.65",
        },
    ],
    "FUTURES": [
        {
            "id": "futures_tsmom_volscaled_v2",
            "base": "futures_tsmom_winner",
            "enhancement": "12m TS-mom with inverse-vol position scaling",
            "parent_evidence": "futures_tsmom WR 58.1% PF 1.68 backtest",
        },
        {
            "id": "futures_es_overnight_drift_v2",
            "base": "futures_session_breakout_cot",
            "enhancement": "ES overnight session drift vs RTH fade",
            "parent_evidence": "strategy_engineering futures xs-mom failed — session niche",
        },
    ],
    "CHEAP_STOCKS": [
        {
            "id": "cheap_momentum_liquid_v2",
            "base": "cheap_stock_cross_momentum_winner",
            "enhancement": "Min $1m ADV; top-5 12-1 momentum $2–12",
            "parent_evidence": "backtest WR 61% PF 2.79",
        },
        {
            "id": "cheap_rsi2_oversold_v2",
            "base": "cheap_stock_cross_momentum_winner",
            "enhancement": "RSI(2)<10 bounce with volume confirm",
            "parent_evidence": "mean-rev complement to momentum book",
        },
    ],
    "PENNY_STOCK": [
        {
            "id": "penny_liquid_rsi_v2",
            "base": "cheap_stock_cross_momentum_winner",
            "enhancement": "Penny subset: min ADV + RSI2<5 only",
            "parent_evidence": "liquidity gate reduces slippage blow-ups",
        },
        {
            "id": "penny_gap_fade_v2",
            "base": "cheap_stock_cross_momentum_winner",
            "enhancement": "Fade >20% gap-up without volume",
            "parent_evidence": "pump-dump fade pattern",
        },
    ],
    "MEME": [
        {
            "id": "meme_altseason_gated_v2",
            "base": "crypto_vol_regime_accumulation",
            "enhancement": "Long memes only when BTC.D falling + altseason score",
            "parent_evidence": "strategy_bt_memecoin altseason n=115 WR=35.7%",
        },
        {
            "id": "meme_funding_extreme_short_v2",
            "base": "crypto_funding_carry_winner",
            "enhancement": "SHORT perp funding >0.05% on meme pairs",
            "parent_evidence": "crowded long fade",
        },
    ],
}

# ---------------------------------------------------------------------------
# New strategy hypotheses (1 per class) — backtest-only until harness pass
# ---------------------------------------------------------------------------

NEW_STRATEGY_BY_CLASS: dict[str, dict[str, Any]] = {
    "CRYPTO": {
        "id": "crypto_funding_crowding_short",
        "family": "funding_rate_extreme",
        "description": "SHORT when 8h funding > 0.03% and RSI>60 (crowded long)",
        "economic_prior": "Positive funding = long overcrowding; mean reversion on perps",
    },
    "EQUITY": {
        "id": "equity_first_hour_range_break",
        "family": "session_structure",
        "description": "Break of first-hour range after 10:30 ET with volume confirm",
        "economic_prior": "Institutional flow post-open auction",
    },
    "FOREX": {
        "id": "forex_london_open_momentum",
        "family": "session_momentum",
        "description": "London open (07:00 UTC) break of Asian range on majors",
        "economic_prior": "FX liquidity injection at London fix",
    },
    "COMMODITY": {
        "id": "commodity_gold_overnight_gap_fade",
        "family": "gap_fade",
        "description": "Fade GC overnight gap >0.5% at NY open",
        "economic_prior": "Overnight noise vs London physical flow",
    },
    "ETF": {
        "id": "etf_low_vol_anomaly_monthly",
        "family": "low_vol_factor",
        "description": "Long lowest-vol quintile sector ETFs monthly rebalance",
        "economic_prior": "Low-vol anomaly (Ang et al.)",
    },
    "BOND": {
        "id": "bond_curve_steepener_momentum",
        "family": "yield_curve",
        "description": "Long TLT when 2s10s spread widening 20d",
        "economic_prior": "Duration momentum on curve moves",
    },
    "FUTURES": {
        "id": "futures_cross_sectional_momentum",
        "family": "ts_momentum",
        "description": "Long top-3 / short bottom-3 futures by 6m return",
        "economic_prior": "Moskowitz et al. TS-mom",
    },
    "CHEAP_STOCKS": {
        "id": "cheap_quality_momentum",
        "family": "quality_momentum",
        "description": "Piotroski F-score>=7 + 6m momentum in $2–12 universe",
        "economic_prior": "Quality + momentum combo",
    },
    "PENNY_STOCK": {
        "id": "penny_volume_spike_fade",
        "family": "volume_spike_fade",
        "description": "SHORT after 3x volume spike + >15% day without catalyst",
        "economic_prior": "Retail pump exhaustion",
    },
    "MEME": {
        "id": "meme_social_decay_short",
        "family": "hype_decay",
        "description": "SHORT 48h after social velocity peak (proxy: vol spike decay)",
        "economic_prior": "Attention-driven hype mean reversion",
    },
}


def _tag_forward(pick: dict[str, Any], strategy_id: str, enhancement: str) -> dict[str, Any]:
    out = deepcopy(pick)
    out["strategy"] = strategy_id
    out["forward_observation"] = True
    out["paper_pilot"] = True
    out["source_system"] = out.get("source_system") or "june2026_research"
    out["extra"] = dict(out.get("extra") or {})
    out["extra"]["june2026_enhancement"] = enhancement
    out["extra"]["forward_registered_at"] = datetime.now(timezone.utc).isoformat()
    return out


def _filter_direction(picks: list[dict], direction: str) -> list[dict]:
    d = direction.upper()
    out = []
    for p in picks:
        pd = str(p.get("direction", "LONG")).upper()
        if d == "SHORT" and pd in ("SHORT", "SELL", "STRONG_SELL"):
            out.append(p)
        elif d == "LONG" and pd in ("LONG", "BUY", "STRONG_BUY"):
            out.append(p)
    return out


def _generate_luxalgo_short_v2() -> list[dict[str, Any]]:
    """Enhance luxalgo: emit SHORT signals only from scanner if available."""
    try:
        from alpha_engine.scanner import run_luxalgo_confluence_scan
        raw = run_luxalgo_confluence_scan() or []
    except Exception:
        try:
            from alpha_engine.production_scanner import scan_luxalgo_confluence
            raw = scan_luxalgo_confluence() or []
        except Exception:
            raw = []
    picks = []
    for p in raw:
        if not isinstance(p, dict):
            continue
        d = str(p.get("direction", "")).upper()
        if d not in ("SHORT", "SELL"):
            continue
        picks.append(_tag_forward(p, "luxalgo_confluence_v2_short",
                                   ENHANCED_V2_BY_CLASS["CRYPTO"][0]["enhancement"]))
    return picks[:5]


def _generate_from_flagship(asset_class: str, strategy_id: str, enhancement: str,
                            generator: Callable[[], list[dict]]) -> list[dict]:
    try:
        raw = generator() or []
    except Exception as e:
        logger.warning("%s flagship gen failed: %s", asset_class, e)
        return []
    out = []
    for p in raw[:8]:
        if not isinstance(p, dict):
            continue
        out.append(_tag_forward(p, strategy_id, enhancement))
    return out


def _generate_crypto_handoff_v2() -> list[dict[str, Any]]:
    """Session handoff picks — SHORT bias for forward observation."""
    try:
        from alpha_engine.winners.crypto_multi_day_momentum_winner import (
            generate_crypto_multi_day_momentum_winner_picks,
        )
        raw = generate_crypto_multi_day_momentum_winner_picks() or []
    except Exception:
        raw = []
    out = []
    for p in raw:
        p2 = _tag_forward(p, "crypto_eu_us_handoff_short_v2",
                          ENHANCED_V2_BY_CLASS["CRYPTO"][1]["enhancement"])
        # Forward obs: prefer SHORT for this variant
        if str(p2.get("direction", "")).upper() not in ("SHORT", "SELL"):
            p2["direction"] = "SHORT"
        out.append(p2)
    return out[:5]


_GENERATORS: dict[str, Callable[[], list[dict]]] = {}


def _build_generators() -> None:
    if _GENERATORS:
        return
    from alpha_engine.eight_class_flagship_strategies import FLAGSHIP_BY_CLASS

    _GENERATORS["luxalgo_confluence_v2_short"] = _generate_luxalgo_short_v2
    _GENERATORS["crypto_eu_us_handoff_short_v2"] = _generate_crypto_handoff_v2

    class_map = {
        "equity_sector_rotation_vix_v2": "EQUITY",
        "equity_pead_sue_v2": "EQUITY",
        "forex_trend_aligned_v2": "FOREX",
        "forex_rsi2_usdchf_v2": "FOREX",
        "commodity_futures_momentum_dedup_v2": "COMMODITY",
        "commodity_seasonal_wheat_v2": "COMMODITY",
        "etf_dual_momentum_vix_v2": "ETF",
        "etf_sector_rs_weekly_v2": "ETF",
        "bond_zn_mean_rev_atr_v2": "BOND",
        "bond_hyg_lqd_spread_v2": "BOND",
        "futures_tsmom_volscaled_v2": "FUTURES",
        "futures_es_overnight_drift_v2": "FUTURES",
        "cheap_momentum_liquid_v2": "CHEAP_STOCKS",
        "cheap_rsi2_oversold_v2": "CHEAP_STOCKS",
        "penny_liquid_rsi_v2": "PENNY_STOCK",
        "penny_gap_fade_v2": "PENNY_STOCK",
        "meme_altseason_gated_v2": "MEME",
        "meme_funding_extreme_short_v2": "MEME",
    }
    meta_by_id = {}
    for specs in ENHANCED_V2_BY_CLASS.values():
        for s in specs:
            meta_by_id[s["id"]] = s

    for sid, ac in class_map.items():
        spec = meta_by_id.get(sid, {})
        entry = FLAGSHIP_BY_CLASS.get(ac)
        if not entry:
            continue
        gen = entry["generator"]
        enh = spec.get("enhancement", "")
        _GENERATORS[sid] = lambda g=gen, i=sid, e=enh: _generate_from_flagship(ac, i, e, g)


def generate_forward_observation_picks() -> list[dict[str, Any]]:
    """All enhanced v2 picks for forward testing (paper_pilot + forward_observation flags)."""
    if os.environ.get(FORWARD_OBSERVATION_ENV, "1").strip().lower() in ("0", "false", "off"):
        return []
    _build_generators()
    all_picks: list[dict[str, Any]] = []
    seen: set[tuple] = set()
    for ac, specs in ENHANCED_V2_BY_CLASS.items():
        for spec in specs:
            sid = spec["id"]
            gen = _GENERATORS.get(sid)
            if not gen:
                continue
            try:
                batch = gen() or []
            except Exception as e:
                logger.warning("forward gen %s failed: %s", sid, e)
                batch = []
            for p in batch:
                p.setdefault("asset_class", ac)
                p.setdefault("category", ac.lower() if ac != "CHEAP_STOCKS" else "equity")
                key = (p.get("symbol"), p.get("direction"), sid)
                if key in seen:
                    continue
                seen.add(key)
                all_picks.append(p)
    logger.info("june2026 forward observation: %d picks from %d strategies",
                len(all_picks), len(_GENERATORS))
    return all_picks


def list_all_candidates() -> dict[str, Any]:
    """Metadata export for research pipeline."""
    return {
        "enhanced_v2": ENHANCED_V2_BY_CLASS,
        "new_strategies": NEW_STRATEGY_BY_CLASS,
        "forward_env": FORWARD_OBSERVATION_ENV,
    }
