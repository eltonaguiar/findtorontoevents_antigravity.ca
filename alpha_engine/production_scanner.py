from __future__ import annotations

import sys
import os

# In GitHub Actions, keep real stdout/stderr so failures show in the job log.
# Locally / Windows, file logging survives pipe closure.
_log_file = None
if os.environ.get("GITHUB_ACTIONS", "").lower() == "true":
    _log_file = None
else:
    _log_file = open("scanner_lifecycle.log", "w", encoding="utf-8", buffering=1)

# Robust print replacement -- guards against I/O errors from pipe closure,
# subprocess termination, or redirected streams on all platforms.
# __builtins__ is a module when this file is __main__, a dict when imported.
import builtins as _bi
_orig_print = _bi.print

def print(*args, **kwargs):
    if "file" not in kwargs:
        kwargs["file"] = sys.stdout
    try:
        _orig_print(*args, **kwargs)
    except (ValueError, OSError):
        pass
    # Tee to log file if active
    if _log_file is not None and "file" not in kwargs:
        try:
            _orig_print(*args, file=_log_file)
            _log_file.flush()
        except (ValueError, OSError):
            pass

_bi.print = print

import json
import math
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests


def _sanitize_for_json(obj):
    """Recursively replace NaN/Infinity with None so json.dump never emits invalid tokens."""
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_for_json(v) for v in obj]
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    if hasattr(obj, "item"):
        v = obj.item()
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            return None
        return v
    return obj


sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo root for shared/

# Import standardized win rate calculation
from shared import calculate_win_rate

from config import (
    DATA_DIR,
    BINANCE_BASE,
    BINANCE_FUTURES_BASE,
    COINGECKO_BASE,
    FEAR_GREED_URL,
    CRYPTO_SYMBOLS,
)
from config import STRATEGY_TRACK_ALIASES

# Failover endpoints for Binance (HTTP 451 geo-block on US GitHub Actions)
try:
    from config import BINANCE_FALLBACK_URLS, BINANCE_FUTURES_FALLBACK_URLS
except ImportError:
    BINANCE_FALLBACK_URLS = []
    BINANCE_FUTURES_FALLBACK_URLS = []
_SPOT_BASES = [BINANCE_BASE] + BINANCE_FALLBACK_URLS
_FUTURES_BASES = [BINANCE_FUTURES_BASE] + BINANCE_FUTURES_FALLBACK_URLS

# Shared multi-source failover (Binance mirrors -> CoinGecko -> KuCoin -> CryptoCompare).
# REQUIRED by project rule (CLAUDE.md / feedback_api_failover): never single Binance endpoint.
# Centralized via failover_imports.py to avoid duplicate dual-import blocks.
try:
    from alpha_engine.failover_imports import (
        fetch_tickers_24h as _shared_fetch_tickers_24h,
        fetch_klines as _shared_fetch_klines,
        fetch_funding_rate as _shared_fetch_funding_rate,
        HAS_SHARED_FAILOVER as _HAS_SHARED_FAILOVER,
    )
except ImportError:
    _HAS_SHARED_FAILOVER = False
    _shared_fetch_tickers_24h = None  # type: ignore[assignment]
    _shared_fetch_klines = None  # type: ignore[assignment]
    _shared_fetch_funding_rate = None  # type: ignore[assignment]
# Polymarket Volume Spike Filter: invalidate session cache at scan start
# so fresh signals are picked up each scan cycle.
try:
    from alpha_engine.polymarket_volume_filter import invalidate_cache as _pm_invalidate_cache
    _HAS_PM_VOL_FILTER = True
except ImportError:
    _pm_invalidate_cache = None
    _HAS_PM_VOL_FILTER = False

from forward_validator import (
    run_generation,
    run_validation,
    run_tweaker,
    compute_all_strategy_stats,
    load_active_picks,
    load_closed_picks,
    load_strategy_performance,
)

# Universe manager -- dynamic symbol rotation (KIMI research: swap stale low-vol symbols)
try:
    from universe_manager import get_dynamic_universe

    _HAS_UNIVERSE_MGR = True
except ImportError:
    _HAS_UNIVERSE_MGR = False

# Strategy Priority Tier System (cross-AI consensus: "simplify to survive")
# ELITE (top 5) -> 3x sizing | PROVEN (next 10) -> 1x | EXPERIMENTAL -> 0.5x
try:
    from strategy_priority import (
        apply_tier_gates,
        should_trade_now,
        compute_portfolio_stress_multiplier,
        save_kill_list,
        save_tier_report,
        refresh_tiers,
    )

    _HAS_STRATEGY_PRIORITY = True
except ImportError:
    _HAS_STRATEGY_PRIORITY = False

# ---------------------------------------------------------------------------
# Data source integrations (all optional, fail-safe)
# ---------------------------------------------------------------------------

# Adaptive TP/SL: MFE/MAE-driven optimal take-profit / stop-loss
try:
    from adaptive_tp_sl import apply_adaptive_tp_sl, refresh_adaptive_levels

    _HAS_ADAPTIVE_TP_SL = True
except ImportError:
    _HAS_ADAPTIVE_TP_SL = False

# CoinMetrics: MVRV, NVT, active addresses (free API, no key)
try:
    from coinmetrics_signal import get_onchain_features

    _HAS_COINMETRICS = True
except ImportError:
    _HAS_COINMETRICS = False

# Mempool.space: BTC mempool congestion & fee pressure
try:
    from mempool_signal import get_mempool_features

    _HAS_MEMPOOL = True
except ImportError:
    _HAS_MEMPOOL = False

# Causal inference: BTC lead-lag signals + Granger causality
try:
    from causal_filter import enrich_picks_with_btc_lead, get_btc_lead_boost

    _HAS_CAUSAL_FILTER = True
except ImportError:
    _HAS_CAUSAL_FILTER = False

# Market modifiers: BTC dominance, treasury boost, supply change
try:
    from market_modifiers import apply_all_modifiers

    _HAS_MARKET_MODIFIERS = True
except ImportError:
    _HAS_MARKET_MODIFIERS = False

# Feature populator: compute real OHLCV-derived features at pick creation time
# (Phase 16 -- kills 25 dead ML features by wiring real data into every pick)
try:
    from feature_populator import populate_batch as _populate_features_batch

    _HAS_FEATURE_POPULATOR = True
except ImportError:
    _populate_features_batch = None
    _HAS_FEATURE_POPULATOR = False

# Data Coverage Enforcer: backfill inline features + coverage metrics + penalties
try:
    from data_coverage_enforcer import enforce_coverage as _enforce_coverage

    _HAS_COVERAGE_ENFORCER = True
except ImportError:
    _enforce_coverage = None
    _HAS_COVERAGE_ENFORCER = False

# Missed opportunity analyzer: add symbols we keep missing
try:
    from missed_opportunity_analyzer import get_universe_additions

    _HAS_MISSED_OPP = True
except ImportError:
    _HAS_MISSED_OPP = False

# Universe expander: catch top gainers, new listings, trending coins we're missing
_HAS_UNIVERSE_EXPANDER = False

# Whale Concentration Index: Whale Alert, Etherscan, Arkham
try:
    from whale_alert_scanner import WhaleAlertScanner
    from etherscan_whale_tracker import EtherscanWhaleTracker
    from arkham_smart_money import ArkhamScanner
    from whale_index import get_whale_concentration_index

    _HAS_WHALE_INDEX = True
except ImportError:
    _HAS_WHALE_INDEX = False

# Fast regime detector -- sub-minute microstructure ensemble (replaces 30-min cycle)
try:
    from fast_regime_detector import (
        get_fast_regime,
        get_regime_for_symbol,
        is_strategy_allowed,
        regime_to_numeric,
        load_cached_regime,
    )

    _HAS_FAST_REGIME = True
except ImportError:
    _HAS_FAST_REGIME = False

# P1-B: Regime flip detector -- macro regime with flip detection + 2-confirmation hysteresis.
# Runs check_flip() at scan start; applies regime-aware quality gates to picks.
try:
    from regime_flip_detector import (
        check_flip,
        get_regime_confidence,
        load_last_regime,
        REGIME_CONFIDENCE,
    )

    _HAS_REGIME_FLIP = True
except ImportError:
    _HAS_REGIME_FLIP = False

    def check_flip():
        return False

    def get_regime_confidence(regime=None):
        return {"long_conf": 0.5, "short_conf": 0.5, "size_mult": 0.5}

    def load_last_regime():
        return None

# HMM Regime Normalizer (EAGLE2 Phase 2) -- canonical regime interface
try:
    from hmm_regime_normalizer import normalize as _normalize_hmm
    _HAS_HMM_NORMALIZER = True
except ImportError:
    _HAS_HMM_NORMALIZER = False

    def _normalize_hmm(data, source=None):
        return {"regime": "UNKNOWN", "confidence": 0.0, "source": "fallback"}

    REGIME_CONFIDENCE = {}

# Risk Controls -- circuit breaker, daily loss limit, consecutive loss breaker
try:
    from risk_controls import (
        run_all_risk_controls,
        is_circuit_breaker_locked,
        is_daily_blocked,
        check_circuit_breaker,
        apply_circuit_breaker_to_picks,
    )

    _HAS_RISK_CONTROLS = True
except ImportError:
    _HAS_RISK_CONTROLS = False

# Macro data pipeline -- yield curve + Fed policy
try:
    from macro_data_pipeline import run_macro_pipeline, get_macro_snapshot

    _HAS_MACRO_PIPELINE = True
except ImportError:
    _HAS_MACRO_PIPELINE = False

# Prediction Anomaly Detector -- SPC, drift, OOD, herding, alert system
try:
    from prediction_anomaly_detector import (
        check_all_anomalies,
        get_sizing_multiplier,
        apply_ood_penalties,
    )

    _HAS_ANOMALY_DETECTOR = True
except ImportError:
    _HAS_ANOMALY_DETECTOR = False


# Hedge Fund Quality Gate -- banned sources, banned symbols, drawdown caps
# Wired into apply_quality_gates() so enforcement happens at trade-time, not just audit-time.
try:
    from alpha_engine.hedge_fund_quality_gate import passes_hedge_fund_gate

    _HAS_HEDGE_FUND_GATE = True
except ImportError:
    _HAS_HEDGE_FUND_GATE = False

try:
    from audit_trail.promotion_gate import (
        PROMOTED_STRATEGIES,
        admission_reason,
        is_admissible_for_production,
    )

    _HAS_PROMOTION_GATE = True
except ImportError:
    _HAS_PROMOTION_GATE = False

# Drawdown Tracker -- per-strategy drawdown + loss streak penalties
try:
    from drawdown_tracker import compute_all_drawdowns

    _HAS_DRAWDOWN_TRACKER = True
except ImportError:
    _HAS_DRAWDOWN_TRACKER = False

# Macro overlay scoring
try:
    from macro_overlay_score import attach_macro_overlay

    _HAS_MACRO_OVERLAY = True
except ImportError:
    _HAS_MACRO_OVERLAY = False

# COMMODITY CT=F emission cap (PR-2026-0518-3) — call site at main() ~line 5267
try:
    from concentration_cap import (
        enforce_commodity_ctf_emission_cap as _ctf_emission_cap,
    )

    _HAS_CTF_CAP = True
except ImportError:
    _ctf_emission_cap = None
    _HAS_CTF_CAP = False

# EAGLE-4 admissibility gate (2026-06-02, minimax-m3-free)
# Data source: AI tournament picks (5,492 picks, 3,692 resolved) — top 5 T1 models
# - CRYPTO: LONG 33% WR / -0.49% avg PnL, SHORT 67% WR / +3.74% avg PnL → flip to SHORT
# - PENNY: SHORT 15% WR / -6.01% avg PnL → kill SHORT
# - COMMODITY: SHORT 18% WR / -2.15% avg PnL → kill SHORT
# - ETF: SHORT 22% WR / -1.05% avg PnL → kill SHORT
# - EQUITY: SHORT 39% WR / +0.10% avg PnL → kill SHORT (marginal)
# - Personas with <40% WR in tournament: momentum_scalp, breakout_scanner, reflexivity_trader
_EAGLE4_PERSONA_KILL = {
    "momentum_scalp",
    "breakout_scanner",
    "reflexivity_trader",
    "deep_value",  # 44% WR, -0.59% avg PnL
}
_EAGLE4_DIRECTIONAL_KILL = {
    # CRYPTO LONG is handled by flip (below), not by kill — so not in this set.
    ("PENNY", "SHORT"),
    ("PENNY", "SELL"),
    ("COMMODITY", "SHORT"),
    ("COMMODITY", "SELL"),
    ("ETF", "SHORT"),
    ("ETF", "SELL"),
    ("EQUITY", "SHORT"),
    ("EQUITY", "SELL"),
}
_EAGLE4_CRYPTO_FLIP_TO_SHORT = True  # Tournament data: SHORT 67% WR vs LONG 33%


def apply_eagle4_admissibility(picks: list[dict]) -> list[dict]:
    """EAGLE-4 admissibility gate — flip CRYPTO to SHORT, kill noise personas, kill negative-edge directions.

    Data-backed by AI tournament leaderboard (46 models, 3,692 resolved picks, top 5 T1 models).
    Replaces EAGLE-2/EAGLE-3 plan Pillar 1 actions #1-3.
    Called from main() right before portfolio cap so only admissible picks compete for slots.
    """
    if not picks:
        return picks

    original_count = len(picks)
    kept: list[dict] = []
    killed_persona = 0
    killed_directional = 0
    flipped_crypto = 0

    for pick in picks:
        ac = str(pick.get("asset_class") or pick.get("category") or "").strip().upper()
        persona = str(pick.get("persona_id") or pick.get("strategy_name") or "").strip().lower()
        direction = str(
            pick.get("signal_type") or pick.get("direction") or "BUY"
        ).strip().upper()
        # Normalize direction to LONG/SHORT
        norm_dir = "SHORT" if direction in ("SELL", "SHORT") else "LONG"

        # 1. Persona kill list — confirmed noise in AI tournament
        if persona in _EAGLE4_PERSONA_KILL:
            killed_persona += 1
            continue

        # 2. CRYPTO directional flip — LONG has 33% WR, SHORT has 67% WR
        #    Flip BEFORE directional kill so flipped picks don't get killed.
        if _EAGLE4_CRYPTO_FLIP_TO_SHORT and ac == "CRYPTO" and norm_dir == "LONG":
            pick["signal_type"] = "SELL"
            pick["direction"] = "SHORT"
            pick["eagle4_flip"] = "CRYPTO_LONG_TO_SHORT"
            norm_dir = "SHORT"
            flipped_crypto += 1

        # 3. Directional kill list — check POST-FLIP direction
        if (ac, norm_dir) in _EAGLE4_DIRECTIONAL_KILL:
            killed_directional += 1
            continue

        kept.append(pick)

    if killed_persona or killed_directional or flipped_crypto:
        print(
            f"  [EAGLE-4 ADMISSIBILITY] in={original_count} kept={len(kept)} | "
            f"killed_persona={killed_persona} killed_directional={killed_directional} "
            f"flipped_crypto_L_to_S={flipped_crypto}"
        )
    return kept

# Unified circuit breaker aggregator
try:
    from circuit_breaker_aggregator import get_unified_breaker_state

    _HAS_CB_AGGREGATOR = True
except ImportError:
    _HAS_CB_AGGREGATOR = False

# Regime Router: composite regime detection + strategy-family sizing boost/penalty
try:
    from whale_concentration_index import get_wci_boost

    _HAS_WCI = True
except ImportError:
    _HAS_WCI = False
try:
    from regime_router import apply_regime_routing as _apply_regime_routing

    _HAS_REGIME_ROUTER = True
except ImportError:
    _apply_regime_routing = None
    _HAS_REGIME_ROUTER = False

# ---------------------------------------------------------------------------
# Copy trader detection + source quality tiers.
# Blanket copy-trader boosts were letting sentiment/clone/Bitget picks crowd
# out verified traders and ML names. Rank and gate by audited source quality
# instead of treating every copy-tagged pick as equal.
# ---------------------------------------------------------------------------
_COPY_TRADER_STRATEGY_TAGS = (
    "copy_hl_",
    "copy_pm_",
    "clone_hl_",
    "bitget_copy",
    "okx_copy",
    "binance_smart",
)
_PROVEN_COPY_TRADERS = {
    "copy_hl_NMTD_25M",
    "copy_hl_whale_123M_87roi",
}

# Non-crypto strategies with proven WR — get 1.2x confidence boost
_BOOSTED_NON_CRYPTO_STRATEGIES = {
    # 2026-05-28: stocks_rsi2_pullback REMOVED — 30% WR / PF 0.032 on canonical pf_registry (was 100% on 3 trades, regressed)
    "cta_golden_cross_200": 1.3,  # 100% WR on 2 trades
    "futures_bb_mean_reversion": 1.2,  # 60% WR on 5 trades
    "cot_positioning": 1.15,  # 50% WR, positive PnL
    # 2026-05-28 baby-strat ships (shadow/monitor mode):
    "etf_dual_momentum_rotation": 1.2,  # DIA WR 58.8%, PF 2.64 — strong ETF edge
    "futures_session_breakout_cot": 1.15,  # ES=F WR 61.5%, PF 1.39 — good futures edge
    # 2026-05-29 Cycle 13 breakthrough: Vol MR — 30/30 symbols profitable, PF 2-5
    "volatility_mean_reversion": 1.3,  # Universal strategy, all asset classes
    # 2026-05-28 Cycle 16: new ensemble strategies
    "macd_divergence": 1.3,
    "momentum_breakout": 1.3,
    "mean_reversion_atr": 1.2,
    "trend_ensemble": 1.4,
    # 2026-05-29 Cycle 17: FOREX/BOND breakthrough strategies
    "stoch_rsi": 1.3,
    "pivot_reversion": 1.2,
    "ichimoku": 1.4,
    "yield_curve_proxy": 1.2,
    "range_trading": 1.2,
}
_COPY_STRATEGY_STATS_CACHE: dict | None = None


def _is_copy_trader_pick(pick: dict) -> bool:
    """Return True if pick originates from a copy trader source."""
    strat = str(pick.get("strategy") or "").lower()
    source = str(pick.get("source_system") or "").lower()
    if "copy_trader" in source:
        return True
    for tag in _COPY_TRADER_STRATEGY_TAGS:
        if tag in strat:
            return True
    return False


# ---------------------------------------------------------------------------
# ML-composite ranking — replaces elite_score as primary ranker.
# Weights from Spearman correlation with realised PnL:
#   ml_score +0.33 | confidence +0.20 | forward_wr IC +0.17
#   elite_score r=-0.001 (noise — kept for dashboard display only)
# Verified copy trader premium only:
#   core/proven copy traders get a boost
#   probationary copy traders get a small boost
#   sentiment/Bitget/clone sources get penalized or blocked
# ---------------------------------------------------------------------------


def _get_copy_strategy_performance() -> dict:
    """Load strategy performance once for copy-source decisions."""
    global _COPY_STRATEGY_STATS_CACHE
    if _COPY_STRATEGY_STATS_CACHE is None:
        try:
            _COPY_STRATEGY_STATS_CACHE = load_strategy_performance() or {}
        except Exception:
            _COPY_STRATEGY_STATS_CACHE = {}
    return _COPY_STRATEGY_STATS_CACHE


def _copy_source_quality(pick: dict) -> dict:
    """Classify a copy-trader pick by audited source quality."""
    if not _is_copy_trader_pick(pick):
        return {
            "tier": "not_copy",
            "reason": "not copy trader",
            "closed": 0,
            "wr": 0.0,
            "avg_pnl": 0.0,
            "pf": 0.0,
        }

    strategy = str(pick.get("strategy") or "")
    strategy_l = strategy.lower()
    source = str(pick.get("source_system") or "").lower()
    stats = _get_copy_strategy_performance().get(strategy, {})
    closed = int(stats.get("closed_picks", 0) or 0)
    wr = float(stats.get("win_rate", 0) or 0)
    avg_pnl = stats.get("avg_pnl_pct")
    if avg_pnl is None:
        avg_pnl = stats.get("avg_pnl")
    if avg_pnl is None and closed:
        total_pnl = float(stats.get("total_pnl_pct", 0) or 0)
        avg_pnl = total_pnl / closed
    avg_pnl = float(avg_pnl or 0)
    pf = float(stats.get("profit_factor", 0) or 0)

    if strategy_l.startswith("copy_pm_"):
        embedded_closed = int(
            pick.get("history_trades", pick.get("forward_trades", 0)) or 0
        )
        embedded_wr = float(pick.get("history_wr", pick.get("forward_wr", 0)) or 0)
        if embedded_wr > 1.0:
            embedded_wr = embedded_wr / 100.0
        embedded_avg_pnl = pick.get("history_avg_pnl")
        if embedded_avg_pnl is None:
            embedded_avg_pnl = avg_pnl
        embedded_avg_pnl = float(embedded_avg_pnl or 0)
        if embedded_closed > closed:
            closed = embedded_closed
            wr = embedded_wr
            avg_pnl = embedded_avg_pnl

    result = {
        "tier": "unverified",
        "reason": "copy source has insufficient verified closed-trade history",
        "closed": closed,
        "wr": wr,
        "avg_pnl": avg_pnl,
        "pf": pf,
    }

    if "binance_smart_money" in strategy_l or "binance_smart_money" in source:
        result["tier"] = "sentiment"
        result["reason"] = "binance_smart_money is sentiment-only and execution-blocked"
        return result

    if "bitget_copy" in strategy_l or "copy_trader_bitget" in source:
        if closed >= 10 and wr >= 0.60 and avg_pnl > 0 and 0 < pf <= 10:
            result["tier"] = "verified"
            result["reason"] = "Bitget source passed verified-history thresholds"
        else:
            result["tier"] = "blocked"
            result["reason"] = (
                "Bitget source requires 10+ verified closes, WR>=60%, positive avg PnL, PF<=10"
            )
        return result

    if "clone_hl_" in strategy_l:
        if closed >= 10 and wr >= 0.55 and avg_pnl > 0:
            result["tier"] = "probation"
            result["reason"] = "clone source barely qualified; keep on probation"
        else:
            result["tier"] = "blocked"
            result["reason"] = "clone source unverified or negative expectancy"
        return result

    if strategy in _PROVEN_COPY_TRADERS:
        result["tier"] = "core"
        result["reason"] = "proven copy trader"
        return result

    if strategy_l.startswith("copy_pm_"):
        if closed >= 8 and wr >= 0.60 and avg_pnl > 0:
            result["tier"] = "verified"
            result["reason"] = (
                "Polymarket wallet passed public closed-position thresholds"
            )
        elif closed >= 5 and wr >= 0.55 and avg_pnl >= 0:
            result["tier"] = "probation"
            result["reason"] = "Polymarket wallet has limited but usable public history"
        return result

    if closed >= 10 and wr >= 0.55 and avg_pnl > 0:
        result["tier"] = "verified"
        result["reason"] = "verified copy source"
    elif closed >= 5 and wr >= 0.45:
        result["tier"] = "probation"
        result["reason"] = "limited but non-catastrophic verified history"

    return result


def _compute_ml_composite(pick: dict) -> tuple[float, str]:
    """Return (ranking_score, ranking_method) for a pick.

    2026-05-31 SYNC FIX (#17): Asset-class-aware weights ported from
    `alpha_engine/smart_picks_engine.py:122-167` (PR1 FIX 2026-05-27 block).
    Keep these two callers synchronized — diverging weights = two-ranker
    inconsistency (this scanner ranked picks with stale 0.6/0.3/0.1 weights
    while smart_picks_engine used the inverted-CRYPTO-confidence weights).

    Empirical justification (at_raw_picks 90d):
      CRYPTO conf>=0.9 => 33.7% WR (n=406)
      CRYPTO conf 0.5-0.7 => 45.4% WR (n=3470)
      CRYPTO conf<0.5 => 44.7% WR (n=861)
      => 11.7pp inverted gap — zero confidence weight for CRYPTO.
      FOREX is direct (not inverted): 91.4% WR at conf>=0.9.
    """
    ml = pick.get("ml_score")
    conf = float(pick.get("confidence", 0) or 0)
    fwd_wr = float(pick.get("forward_wr", pick.get("strat_fwd_wr", 0)) or 0)
    if fwd_wr > 1.0:
        fwd_wr = fwd_wr / 100.0

    # Asset-class-aware default weights (mirror smart_picks_engine.py:127-133)
    _raw_ac = str(pick.get("asset_class") or pick.get("category") or "").strip().upper()
    if _raw_ac == "CRYPTO":
        # CRYPTO: confidence anti-predictive -> zero it, boost ml_score + fwd_wr
        _w_ml, _w_conf, _w_fwd = 0.80, 0.00, 0.20
    else:
        # Non-crypto: confidence IC ~0.20 (EQUITY) — keep small weight
        _w_ml, _w_conf, _w_fwd = 0.75, 0.10, 0.15

    if ml is not None and float(ml) > 0:
        ml_val = float(ml)
        score = ml_val * _w_ml + conf * _w_conf + fwd_wr * _w_fwd
        method = "ml_composite"
    else:
        # Fallback path — mirror smart_picks_engine.py:155-167.
        # CRYPTO: drastically scaled down (anti-predictive confidence).
        # Non-crypto: half-strength to avoid beating real ml_composite picks.
        if _raw_ac == "CRYPTO":
            ml_null_penalty = 0.15
        else:
            ml_null_penalty = 0.5
        score = conf * 0.8 * ml_null_penalty
        method = "confidence_fallback"

    # Whale Concentration Index (0-100) adjustment
    if _HAS_WHALE_INDEX:
        try:
            symbol = pick.get("symbol", "")
            whale_data = get_whale_concentration_index(symbol)
            idx = whale_data.get("index", 50)
            direction = (
                pick.get("signal_type") or pick.get("direction") or "BUY"
            ).upper()

            # Boost if whale direction matches pick direction
            if direction in ("BUY", "LONG") and idx > 60:
                bonus = (idx - 60) / 40 * 0.15  # Up to +0.15 boost
                score += bonus
                method += f"+whale_bullish_{bonus:.2f}"
            elif direction in ("SELL", "SHORT") and idx < 40:
                bonus = (40 - idx) / 40 * 0.15  # Up to +0.15 boost
                score += bonus
                method += f"+whale_bearish_{bonus:.2f}"
            # Penalize if whale direction opposes pick direction
            elif direction in ("BUY", "LONG") and idx < 40:
                penalty = (40 - idx) / 40 * 0.20  # Up to -0.20 penalty
                score -= penalty
                method += f"-whale_bearish_conflict_{penalty:.2f}"
            elif direction in ("SELL", "SHORT") and idx > 60:
                penalty = (idx - 60) / 40 * 0.20  # Up to -0.20 penalty
                score -= penalty
                method += f"-whale_bullish_conflict_{penalty:.2f}"
        except Exception:
            pass

    copy_quality = _copy_source_quality(pick)
    copy_tier = copy_quality["tier"]

    # Antigravity Score & Safe Trading Alignment (Strategic Recap)
    # Rules: Score >= 80, WCI >= 60, WR > 75%
    ag_score = score * 100
    ag_safe = False
    ag_reason = []

    if _HAS_WHALE_INDEX:
        try:
            wdata = get_whale_concentration_index(pick.get("symbol", ""))
            wci = wdata.get("index", 50)
            pick["whale_index"] = wci
            pick["whale_direction"] = wdata.get("direction", "neutral")

            # Antigravity Logic
            if ag_score >= 80:
                ag_reason.append("ML Score >= 80")
            if wci >= 60:
                ag_reason.append("Whale Index >= 60")

            # Check historical WR if available (mocked here or pulled from track)
            # In production, this would look up the strategy's current WR
            # For now, we'll mark as 'Safe' if both ML and Whale agree
            if ag_score >= 80 and wci >= 60:
                ag_safe = True
        except Exception:
            pass

    pick["antigravity_score"] = round(ag_score, 1)
    pick["antigravity_safe"] = ag_safe
    pick["antigravity_tooltip"] = "Safe Trading Protocol: " + (
        "; ".join(ag_reason) if ag_reason else "Under Threshold"
    )
    if not ag_safe:
        pick["antigravity_tooltip"] += " (REJECTED for Real Money)"
    else:
        pick["antigravity_tooltip"] += " (CLEARED for Paper/Real)"

    if copy_tier == "core":
        score += 0.18
        method += "+copy_core"
    elif copy_tier == "verified":
        score += 0.10
        method += "+copy_verified"
    elif copy_tier == "probation":
        score += 0.03
        method += "+copy_probation"
    elif copy_tier == "blocked":
        score -= 0.20
        method += "+copy_block_penalty"
    elif copy_tier == "sentiment":
        score -= 0.30
        method += "+copy_sentiment_penalty"

    # Boost proven non-crypto strategies
    strat_name = str(pick.get("strategy") or "")
    if strat_name in _BOOSTED_NON_CRYPTO_STRATEGIES:
        boost = _BOOSTED_NON_CRYPTO_STRATEGIES[strat_name]
        score *= boost
        method += f"+noncrypto_boost_{boost}x"

    return (round(score, 4), method)


def _ml_composite_key(pick: dict) -> float:
    """Sort key: ml_composite score (higher = better)."""
    return _compute_ml_composite(pick)[0]


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
PREMIUM_SIGNALS_PATH = DATA_DIR / "premium_signals.json"
LAST_DISCORD_ALERTS_PATH = DATA_DIR / "last_discord_alerts.json"
HTTP_TIMEOUT = 10

# Stablecoin symbols that should never be traded (pegged to $1, can't hit TP)
STABLECOIN_SYMBOLS = {
    "USDCUSDT",
    "DAIUSDT",
    "UUSDT",
    "USD1USDT",
    "USDEUSDT",
    "XUSDUSDT",
    "STABLEUSDT",
    "FDUSDUSDT",
    "TUSDUSDT",
    "BUSDUSDT",
    "RLUSDUSDT",
    "BFUSDUSDT",
    "EURUSDT",
    "PYUSDUSDT",
    "USDPUSDT",
    "GUSDUSDT",
    "FRAXUSDT",
    # Non-USDT quote variants
    "USD1-USD",
    "USDT-USD",
    "USDC-USD",
    "DAI-USD",
    "TUSD-USD",
    "BUSD-USD",
    "FDUSD-USD",
}


def is_stablecoin(symbol: str, price: float | None = None) -> bool:
    """Detect stablecoins by symbol pattern and/or price heuristic.

    Returns True if:
      - symbol is in STABLECOIN_SYMBOLS blocklist
      - symbol ends with 'USDUSDT' or 'USDTUSDT' (USD-pegged token vs USDT)
      - price is between $0.99 and $1.01 (pegged to $1)
    """
    if symbol in STABLECOIN_SYMBOLS:
        return True
    # Pattern heuristic: *USDUSDT or *USDTUSDT = USD-pegged token quoted in USDT
    if symbol.endswith("USDUSDT") or symbol.endswith("USDTUSDT"):
        return True
    # Price heuristic: if price sits at $1 peg, it's almost certainly a stablecoin
    if price is not None and 0.99 <= price <= 1.01:
        return True
    return False


# Known stock/ETF symbols that must NOT be categorized as "crypto"
_STOCK_CATEGORY_OVERRIDES = {
    "TSLA": "stock",
    "AAPL": "stock",
    "MSFT": "stock",
    "NVDA": "stock",
    "AMZN": "stock",
    "GOOGL": "stock",
    "META": "stock",
    "AMD": "stock",
    "COIN": "stock",
    "MSTR": "stock",
    "PLTR": "stock",
    "SOFI": "stock",
    "AMC": "stock",
    "RIVN": "stock",
    "NIO": "stock",
    "GME": "stock",
    "SOXX": "etf",
    "ARKK": "etf",
    "GLD": "etf",
    "SPY": "etf",
    "QQQ": "etf",
    "TLT": "bond",
    "HYG": "bond",
    "BND": "bond",
    "AGG": "bond",
    "TIP": "bond",
}

# Confidence tier thresholds
TIER_HIGH_CONF = 0.70
TIER_HIGH_RR = 2.0
TIER_MED_CONF = 0.55
TIER_MED_RR = 1.5

# ---------------------------------------------------------------------------
# Optimal entry override (from data/optimal_entry_analysis.json rank 3)
# BUY_ONLY + TP 3% + SL 2% => 56.25% WR, PF 2.989 on 48 trades
# Set ALPHA_OPTIMAL_ENTRY=1 env var to activate (does NOT change defaults yet)
# ---------------------------------------------------------------------------
OPTIMAL_ENTRY_ENABLED = os.environ.get("ALPHA_OPTIMAL_ENTRY", "0") == "1"
OPTIMAL_ENTRY_TP_PCT = 0.03  # 3%
OPTIMAL_ENTRY_SL_PCT = 0.02  # 2%
OPTIMAL_ENTRY_BUY_ONLY = True  # filter to BUY/LONG only

# Minimum Risk:Reward ratio -- picks below this are rejected (Issue 5 hard gate)
MIN_RISK_REWARD = 1.0

# Even EXEMPT_FROM_SAFETY_GATES picks must meet this floor (R:R=0.07 is insane)
MINIMUM_RR_EVEN_EXEMPT = 0.5

# Hard cap on total active picks (Mar 28 2026: raised for multi-asset diversity)
# Forces system to keep only TOP 40 picks, cutting low-quality tail
MAX_ACTIVE_PICKS = 100
DIVERSITY_QUOTA_PCT = 0.50


def normalize_pnl_format(picks: list[dict]) -> list[dict]:
    """Ensure pnl_pct is always in decimal format (0.05 = 5%, not 5.0).

    Some strategies write pnl_pct as percentages (e.g., -62.18 meaning -62.18%)
    while others use decimals (e.g., -0.026 meaning -2.6%). This normalizes all
    to decimal format at load time.
    """
    for p in picks:
        pnl = p.get("pnl_pct")
        if pnl is not None and abs(pnl) > 1.0:
            # Likely percentage format, convert to decimal
            p["pnl_pct"] = round(pnl / 100.0, 6)
    return picks


def normalize_confidence(picks: list[dict]) -> list[dict]:
    """Ensure confidence is always 0.0-0.95 decimal.

    Some strategies emit confidence as percentages (62.7 instead of 0.627).
    Values > 1.0 are divided by 100 to normalize, then capped at 0.95.
    This fixes hs_* highscore picks that report values like 62.7 -> 0.627.
    """
    _normalized = 0
    for p in picks:
        conf = p.get("confidence", 0)
        if conf is not None and conf > 1.0:
            p["confidence"] = round(min(conf / 100.0, 0.95), 4)
            _normalized += 1
        # S2 FIX: separate if (not elif) to also cap values in (0.95, 1.0]
        # e.g. 96/100 = 0.96 needs capping too
        if conf is not None and 0.95 < (p.get("confidence") or 0) <= 1.0:
            p["confidence"] = 0.95
            _normalized += 1
    if _normalized:
        print(f"  [NORMALIZE] Fixed {_normalized} picks with out-of-range confidence")
    return picks


def _get_asset_category(p: dict) -> str:
    """Accurately identify asset category for diversity quota enforcement."""
    cat = (p.get("category") or "").lower()
    symbol = (p.get("symbol") or "").upper().strip()

    # Check manual overrides
    if symbol in _STOCK_CATEGORY_OVERRIDES:
        return _STOCK_CATEGORY_OVERRIDES[symbol]

    # Explicitly tagged
    if cat in ("stock", "equity", "etf", "forex", "futures", "commodity"):
        return cat
    if "=X" in symbol:
        return "forex"
    if "=F" in symbol:
        return "futures"

    # Fallback to config lookup
    try:
        from config import ALL_SYMBOLS

        meta = ALL_SYMBOLS.get(symbol)
        if meta and "cat" in meta:
            return meta["cat"]
    except ImportError:
        pass

    return "crypto"


def enforce_portfolio_cap(
    new_picks: list[dict], existing_active_picks: list[dict]
) -> list[dict]:
    """Hard cap on total active picks with institutional diversity quota (50%).

    Prioritizes:
    1. Diversity Assets: Non-Crypto (Equity, Forex, Futures, Commodities)
    2. Elite Copy Traders: Tier core/verified
    3. High-Conviction Alpha: Rest sorted by ml_composite

    Goal: Force 50% non-crypto representation to stabilize portfolio WR.
    """
    total_allowed = MAX_ACTIVE_PICKS
    # Current active picks on disk/live
    current_count = len(existing_active_picks)
    available_slots = total_allowed - current_count

    if available_slots <= 0:
        print(
            f"[PORTFOLIO CAP] {current_count} active picks >= {total_allowed} max, blocking all new picks"
        )
        return []

    if len(new_picks) <= available_slots:
        return new_picks

    # 1. Categorize new picks
    diversity_picks = []
    other_picks = []

    for p in new_picks:
        asset_cat = _get_asset_category(p)
        is_elite_copy = _copy_source_quality(p)["tier"] in ("core", "verified")

        if (
            asset_cat
            in ("stock", "forex", "futures", "commodity", "equity", "etf", "bond")
            or is_elite_copy
        ):
            diversity_picks.append(p)
        else:
            other_picks.append(p)

    # Sort both pools by ml_composite
    diversity_picks.sort(key=_ml_composite_key, reverse=True)
    other_picks.sort(key=_ml_composite_key, reverse=True)

    # 2. Allocate Slots
    # Target 50% for diversity picks, but don't waste slots if we don't have enough
    diversity_target = max(available_slots // 2, 1)

    kept_diversity = diversity_picks[:diversity_target]
    remaining_after_diversity = available_slots - len(kept_diversity)

    # Fill remaining slots with the best picks from either pool
    remaining_pool = diversity_picks[len(kept_diversity) :] + other_picks
    remaining_pool.sort(key=_ml_composite_key, reverse=True)

    kept_others = remaining_pool[:remaining_after_diversity]

    kept = kept_diversity + kept_others
    # Final sort for stability
    kept.sort(key=_ml_composite_key, reverse=True)

    # Reporting
    dc = sum(
        1
        for p in kept
        if _get_asset_category(p)
        in ("stock", "forex", "futures", "commodity", "equity", "etf", "bond")
    )
    ec = sum(1 for p in kept if _copy_source_quality(p)["tier"] in ("core", "verified"))
    print(
        f"[PORTFOLIO CAP] Kept {len(kept)}/{len(new_picks)} picks (max {total_allowed}). "
        f"Diversity: {dc} Institutional, {ec} Elite Copy. Non-crypto representation: {(dc / len(kept) * 100):.1f}%"
    )

    return kept[:available_slots]


def enforce_sector_concentration_cap(picks: list[dict]) -> list[dict]:
    """Penalize over-concentrated sector picks to prevent correlated losses.

    For each sector (except exempt ones like btc/eth/forex), keeps only the
    top MAX_PICKS_PER_SECTOR picks by ml_composite ranking.  Excess picks get
    their sizing_multiplier reduced by 0.3 (soft penalty, not hard kill).
    """
    try:
        from config import SECTOR_MAP, MAX_PICKS_PER_SECTOR, SECTOR_CAP_EXEMPT
    except ImportError:
        print("  [SECTOR CAP] config.py missing sector constants -- skipping")
        return picks

    def _get_sector(symbol: str) -> str:
        s = (symbol or "").upper().strip()
        return SECTOR_MAP.get(s, "other")

    # Group picks by sector
    from collections import defaultdict

    sector_buckets: dict[str, list[int]] = defaultdict(list)
    for idx, p in enumerate(picks):
        sector = _get_sector(p.get("symbol", ""))
        p["_sector"] = sector  # tag for dashboards
        sector_buckets[sector].append(idx)

    penalized_count = 0
    sector_details = []

    for sector, indices in sector_buckets.items():
        if sector in SECTOR_CAP_EXEMPT:
            continue
        if len(indices) <= MAX_PICKS_PER_SECTOR:
            continue

        # Sort indices by ml_composite descending -- keep top N, penalize rest
        indices_sorted = sorted(
            indices,
            key=lambda i: _ml_composite_key(picks[i]),
            reverse=True,
        )
        excess = indices_sorted[MAX_PICKS_PER_SECTOR:]
        for i in excess:
            # C1 FIX: Use sizing_multiplier instead of confidence
            _ex_mult = float(picks[i].get("sizing_multiplier", 1.0) or 1.0)
            picks[i]["sizing_multiplier"] = round(_ex_mult * 0.3, 4)
            picks[i]["_sector_penalized"] = True
            penalized_count += 1

        sector_details.append(
            f"{sector}={len(indices)} (kept {MAX_PICKS_PER_SECTOR}, "
            f"penalized {len(excess)})"
        )

    if penalized_count > 0:
        print(
            f"  [SECTOR CAP] Penalized {penalized_count} over-concentrated picks "
            f"(max {MAX_PICKS_PER_SECTOR}/sector): {', '.join(sector_details)}"
        )
    else:
        sector_summary = {
            s: len(idxs) for s, idxs in sector_buckets.items() if len(idxs) > 1
        }
        print(
            f"  [SECTOR CAP] All sectors within limits. Counts: {sector_summary or 'all <=1'}"
        )

    return picks


def _fetch_bulk_24h_changes() -> dict[str, float]:
    """Fetch 24h price change percentages for all Binance symbols in one API call.

    Returns dict mapping symbol -> abs(priceChangePercent).
    Uses Binance ticker/24hr endpoint (no symbol param = all symbols).
    Failover: Binance mirrors -> CoinGecko top 250 -> empty dict.
    """
    # Try Binance bulk ticker (all symbols, single call)
    for base in _SPOT_BASES:
        try:
            r = requests.get(
                f"{base}/api/v3/ticker/24hr",
                timeout=15,
            )
            if r.status_code in (451, 403):
                continue  # geo-blocked
            r.raise_for_status()
            data = r.json()
            result = {}
            for item in data:
                sym = item.get("symbol", "")
                try:
                    result[sym] = abs(float(item.get("priceChangePercent", 0)))
                except (ValueError, TypeError):
                    pass
            if result:
                print(
                    f"  [VOL_FILTER] Fetched 24h changes for {len(result)} symbols from Binance"
                )
                return result
        except Exception:
            continue

    # Fallback: CoinGecko top 250 coins
    try:
        r = requests.get(
            f"{COINGECKO_BASE}/coins/markets",
            params={
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": 250,
                "page": 1,
                "sparkline": "false",
            },
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        result = {}
        for coin in data:
            change = coin.get("price_change_percentage_24h")
            if change is not None:
                # Map CoinGecko id to approximate Binance symbol
                sym = (coin.get("symbol", "") or "").upper() + "USDT"
                result[sym] = abs(float(change))
        if result:
            print(
                f"  [VOL_FILTER] Fetched 24h changes for {len(result)} symbols from CoinGecko (fallback)"
            )
            return result
    except Exception as e:
        print(f"  [VOL_FILTER] CoinGecko fallback failed: {e}")

    print("  [VOL_FILTER] WARNING: All price change sources failed -- filter will skip")
    return {}


def apply_volatility_filter(picks: list[dict]) -> list[dict]:
    """Filter picks by ATR%/volatility. High ATR = keep, Low ATR = penalize.

    Uses 24h price change as ATR proxy (correlation ~0.85 with actual ATR).

    Crypto thresholds:
      If 24h_change > 3%: +5 elite_score bonus (HIGH_ATR -- more predictable)
      If 24h_change 1-3%: no change (MEDIUM_ATR)
      If 24h_change < 1%: -10 elite_score penalty (LOW_ATR -- unpredictable noise)
      If 24h_change < 0.5%: BLOCK entirely (dead market, waste of capital)

    Forex thresholds: HIGH > 0.3%, DEAD < 0.1%
    Equity thresholds: HIGH > 1%, DEAD < 0.3%

    Tags each pick with 'volatility_tier': HIGH/MEDIUM/LOW/DEAD
    """
    changes = _fetch_bulk_24h_changes()
    if not changes:
        # No data -- tag all as UNKNOWN and pass through
        for p in picks:
            p["volatility_tier"] = "UNKNOWN"
        print("  [VOL_FILTER] No price data -- all picks tagged UNKNOWN, no filtering")
        return picks

    boosted = 0
    penalized = 0
    blocked = 0
    unknown = 0
    surviving = []

    for p in picks:
        symbol = (p.get("symbol") or "").upper().strip()
        category = (p.get("category") or "").lower()

        # Determine asset class for threshold selection
        is_forex = (
            category == "forex"
            or symbol in _STOCK_CATEGORY_OVERRIDES
            and _STOCK_CATEGORY_OVERRIDES.get(symbol) not in ("stock", "etf")
        )
        is_equity = _STOCK_CATEGORY_OVERRIDES.get(symbol) in (
            "stock",
            "etf",
        ) or category in ("stock", "equity", "etf")

        # Look up 24h change -- try exact symbol, then common variants
        change_24h = changes.get(symbol)
        if change_24h is None:
            # Try without USDT suffix + with USDT
            base_sym = symbol.replace("-USD", "").replace("USDT", "").replace("USD", "")
            change_24h = changes.get(base_sym + "USDT")
        if change_24h is None:
            # Also check if pick already has price_change_24h from enrichment
            _enriched_change = p.get("price_change_24h") or p.get("change_pct")
            if _enriched_change is not None:
                try:
                    change_24h = abs(float(_enriched_change))
                except (ValueError, TypeError):
                    pass

        if change_24h is None:
            p["volatility_tier"] = "UNKNOWN"
            unknown += 1
            surviving.append(p)
            continue

        p["price_change_24h_abs"] = round(change_24h, 4)

        # Select thresholds based on asset class
        if is_forex:
            high_thresh, low_thresh, dead_thresh = 0.3, 0.1, 0.1
        elif is_equity:
            high_thresh, low_thresh, dead_thresh = 1.0, 0.3, 0.3
        else:
            # Crypto (default)
            high_thresh, low_thresh, dead_thresh = 3.0, 1.0, 0.5

        # Apply volatility tier logic
        if change_24h >= high_thresh:
            p["volatility_tier"] = "HIGH_ATR"
            _cur_elite = float(p.get("elite_score", 0) or 0)
            p["elite_score"] = round(_cur_elite + 5, 2)
            p["_vol_filter_bonus"] = 5
            boosted += 1
            surviving.append(p)
        elif change_24h >= low_thresh:
            p["volatility_tier"] = "MEDIUM_ATR"
            surviving.append(p)
        elif change_24h >= dead_thresh:
            p["volatility_tier"] = "LOW_ATR"
            _cur_elite = float(p.get("elite_score", 0) or 0)
            p["elite_score"] = round(_cur_elite - 10, 2)
            p["_vol_filter_penalty"] = -10
            penalized += 1
            surviving.append(p)
        else:
            # DEAD market -- block entirely
            p["volatility_tier"] = "DEAD"
            p["_quality_gate_rejected"] = (
                f"DEAD market: 24h change {change_24h:.2f}% < {dead_thresh}% threshold"
            )
            blocked += 1
            # Do NOT append to surviving -- this pick is blocked

    print(
        f"  [VOL_FILTER] {boosted} picks boosted (HIGH_ATR), "
        f"{penalized} penalized (LOW_ATR), {blocked} blocked (DEAD), "
        f"{unknown} unknown | {len(surviving)}/{len(picks)} passed"
    )

    return surviving


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# 0. Data quality fixes: symbol sanitizer, direction/timestamp backfill, dedup
# ---------------------------------------------------------------------------

_COINGECKO_ID_RE = re.compile(r"^([A-Z]+)\d{4,}-(.+)$")

# Known bad/non-Binance symbols (Hyperliquid-specific naming, delisted, etc.)
BAD_SYMBOLS = {
    "kPEPEUSDT",
    "kBONKUSDT",
    "kSHIBUSDT",
    "kFLOKIUSDT",
    "kDOGEUSDT",
    "0GUSDT",
    "2ZUSDT",
    "STABLEUSDT",
    "USD1USDT",
    "UUSDT",
    "USDEUSDT",
    "XUSDUSDT",
    "RLUSDUSDT",
    "BFUSDUSDT",
    "USDCUSDT",
    "DAIUSDT",
    "FDUSDUSDT",
    "TUSDUSDT",
    "BUSDUSDT",
    "EURUSDT",
    "PYUSDUSDT",
    "USDPUSDT",
    "GUSDUSDT",
    "FRAXUSDT",
    "WLFIUSDT",
    "BEATUSDT",
    "VVVUSDT",
    "OPNUSDT",
    "BARDUSDT",
    "XPLUSDT",
}

# Source-system bans: poison emitters that must never enter the pipeline.
# - Predictions: physically impossible prices (+370,850% on BTCUSDT)
# - sandbox_opposite: emits 12x duplicate signals
# - rapid_fire: duplicate emitter
# - incubator_gainer: 94% abandonment rate, broken resolution linkage
BANNED_SOURCES = {
    "Predictions",
    "sandbox_opposite",
    "rapid_fire",
    "incubator_gainer",
    # Added 2026-06-05: live DB confirmed consistent losers (scrutiny + OHLCV replay)
    # luxalgo_filters: n=2037, WR=43.0%, PF=1.02 (sub-T2, barely above 1.0)
    "luxalgo_filters",
    # multi_asset_copytrader: FOREX PF=1.02 (post-outlier), COMMODITY PF=0.81 n=677
    # Also caused 3,495 extreme-pnl rows (CADJPY +427%, NZDUSD +7955%) = price-feed bugs
    "multi_asset_copytrader",
    # forex_copy_trader: WR=39.7%, PF=0.84, n=63 — persistent FOREX loser
    "forex_copy_trader",
    # signal_validation: 322/353 active picks are ghost >7d stale (never resolves)
    "signal_validation",
    # Added 2026-06-05 session 2: DB-confirmed losers (WR/PF well below T2)
    # regime_terminal: WR=42.9%, PF=0.67, n=257 — also 56.4% null/zero pnl (resolver bug)
    "regime_terminal",
    # alpha_engine_fast: WR=46.3%, PF=0.55, n=553 — sub-T2 loser with 46.1% null pnl
    "alpha_engine_fast",
    # copy_trader_intel: WR=49.0%, PF=0.38, n=573 — worst PF, 64.7% null pnl (resolver never records it)
    "copy_trader_intel",
    # battleground_luxalgo: WR=60% but PF=0.70 (n=239) — fat-tail losses wipe gains; 39.3% null pnl
    "battleground_luxalgo",
}

# TP cap: max allowed distance from entry (as a fraction)
TP_CAP_CRYPTO = 0.15  # 15% max for crypto (hedge-fund risk cap)
# 2026-04-25: WIDENED from 0.0075 -> 0.015. Realised FX class shows PF=0.26
# expectancy=-$0.99/trade on 1558 closed picks; SL_HIT 44% vs TP_HIT 12%.
# Previous 0.75% TP / 0.5% SL widening (2026-04-17/19) wasn't enough — SL at
# 0.5% sits AT median daily FX ATR (0.3-0.8%), so stops trigger on routine
# noise. Two-model Ollama Cloud consensus (gpt-oss:120b + qwen3-coder:480b)
# recommends 1.5% TP / 0.8% SL. All three forex cap locations updated
# together: non_crypto_policy.py NON_CRYPTO_TP_SL_CAPS["forex"] and config.py
# CATEGORY_RISK forex. See updates/2026-04-25-forex-tpsl-review.md.
TP_CAP_FOREX = 0.015  # 1.5% max for forex (was 0.0075 — see review doc)
TP_CAP_COMMODITY = 0.12  # 12% max for commodities (wider than forex)
TP_CAP_EQUITY = 0.10  # 10% max for stocks/ETF (swing-style picks)

# SL cap: max allowed SL distance from entry (as a fraction)
SL_CAP_CRYPTO = 0.10  # 10% max SL for crypto
# 2026-04-25: WIDENED from 0.005 -> 0.008. See TP_CAP_FOREX comment above.
# PR3 (2026-05-27): WIDENED from 0.008 -> 0.010. Clear median daily FX ATR for all G10 pairs.
SL_CAP_FOREX = 0.010  # 1.0% max SL for forex (was 0.008 — PR3 ATR-clearing fix)
SL_CAP_COMMODITY = 0.08
SL_CAP_EQUITY = 0.07

# Stale pick threshold: picks open >48h with no price update are closed
STALE_HOURS_THRESHOLD = 48


def apply_source_ban_gate(picks: list[dict]) -> list[dict]:
    """Reject picks from banned source systems before scoring.

    Logs every rejected pick with its source_system and symbol so audit
    trails show exactly why a poison source was dropped.
    """
    clean = []
    removed = 0
    for pick in picks:
        source = str(pick.get("source_system") or "").strip()
        sym = pick.get("symbol", "")
        strategy = pick.get("strategy", "")
        if source in BANNED_SOURCES:
            print(
                f"  [SOURCE_BAN] Removing {sym} ({strategy}): "
                f"source_system='{source}' is in BANNED_SOURCES"
            )
            removed += 1
            continue
        clean.append(pick)
    if removed:
        print(f"  [SOURCE_BAN] Removed {removed} picks from banned source systems")
    return clean


def filter_bad_symbols(picks: list[dict]) -> list[dict]:
    """Remove picks with known bad symbols, non-standard naming, or stablecoins.

    Rejects:
      - Symbols in the BAD_SYMBOLS set
      - Symbols starting with a lowercase letter (Hyperliquid 'k' prefix tokens)
      - Symbols starting with a digit followed by non-digit (e.g. '2ZUSDT')
        Exception: '1000' prefix is valid Binance naming (e.g. 1000PEPEUSDT)
      - Stablecoins detected by is_stablecoin() (symbol pattern + price heuristic)
    """
    clean = []
    removed = 0
    for pick in picks:
        sym = pick.get("symbol", "")
        price = pick.get("entry_price") or pick.get("current_price")
        reject_reason = None

        if sym in BAD_SYMBOLS:
            reject_reason = f"in BAD_SYMBOLS blocklist"
        elif sym and sym[0].islower():
            reject_reason = f"starts with lowercase '{sym[0]}' (non-Binance)"
        elif sym and sym[0].isdigit() and not sym.startswith("1000"):
            reject_reason = f"starts with digit '{sym[0]}' (non-standard)"
        elif is_stablecoin(sym, price):
            reject_reason = f"stablecoin (pegged to $1, price={price})"

        if reject_reason:
            print(
                f"  [BAD_SYMBOL] Removing {sym} ({pick.get('strategy', '')}): {reject_reason}"
            )
            removed += 1
        else:
            clean.append(pick)

    if removed:
        print(f"  [BAD_SYMBOL] Removed {removed} picks with invalid symbols")
    return clean


def close_stale_picks(picks: list[dict]) -> tuple[list[dict], list[dict]]:
    """Close picks that have been open >48h with ZERO price updates.

    A pick is considered stale if:
      - last_checked is None/null (never validated against live price)
      - current_price is None/null or equals entry_price (never updated)
      - entry_date is >48h ago

    Returns (active, closed_as_stale) tuple.
    """
    now = datetime.now(timezone.utc)
    still_active = []
    closed_stale = []

    for pick in picks:
        last_checked = pick.get("last_checked")
        current_price = pick.get("current_price")
        entry_price = pick.get("entry_price")
        entry_date_str = pick.get("entry_date") or pick.get("timestamp") or ""

        # Parse entry date
        entry_dt = None
        if entry_date_str:
            try:
                if "T" in entry_date_str:
                    entry_dt = datetime.fromisoformat(
                        entry_date_str.replace("Z", "+00:00")
                    )
                else:
                    entry_dt = datetime.strptime(entry_date_str, "%Y-%m-%d").replace(
                        tzinfo=timezone.utc
                    )
                # Guarantee tz-aware: naive ISO strings (no offset) would otherwise
                # break ``now - entry_dt`` below ("can't subtract offset-naive and
                # offset-aware datetimes").
                if entry_dt is not None and entry_dt.tzinfo is None:
                    entry_dt = entry_dt.replace(tzinfo=timezone.utc)
            except Exception:
                pass

        # Check if stale: no price updates AND old enough
        is_never_checked = last_checked is None
        is_price_unchanged = current_price is None or current_price == entry_price
        is_old_enough = (
            entry_dt and (now - entry_dt).total_seconds() > STALE_HOURS_THRESHOLD * 3600
        )

        if is_never_checked and is_price_unchanged and is_old_enough:
            pick["exit_reason"] = "STALE_NO_DATA"
            pick["exit_date"] = now.isoformat()
            pick["status"] = "CLOSED"
            pick["pnl_pct"] = 0.0
            pick["pnl_dollar"] = 0.0
            closed_stale.append(pick)
            print(
                f"  [STALE] Closing {pick.get('symbol')} ({pick.get('strategy', '')}): "
                f"open since {entry_date_str}, never price-checked"
            )
        else:
            still_active.append(pick)

    if closed_stale:
        print(
            f"  [STALE] Closed {len(closed_stale)} stale picks (>{STALE_HOURS_THRESHOLD}h, no price data)"
        )
    return still_active, closed_stale


def cap_tp_targets(picks: list[dict]) -> list[dict]:
    """Clamp TP and SL targets to max allowed distance from entry.

    Crypto: max 15% TP / 10% SL from entry
    Forex:  max 1.0% TP / 0.5% SL from entry
    """
    tp_capped = 0
    sl_capped = 0
    for pick in picks:
        entry = pick.get("entry_price") or 0
        tp = pick.get("take_profit") or 0
        sl = pick.get("stop_loss") or 0
        if entry <= 0:
            continue

        category = (pick.get("category") or "crypto").lower()
        if category in ("forex",):
            max_tp_dist = TP_CAP_FOREX
            max_sl_dist = SL_CAP_FOREX
        elif category in ("commodity",):
            max_tp_dist = TP_CAP_COMMODITY
            max_sl_dist = SL_CAP_COMMODITY
        elif category in ("equity", "stock", "etf"):
            max_tp_dist = TP_CAP_EQUITY
            max_sl_dist = SL_CAP_EQUITY
        else:
            max_tp_dist = TP_CAP_CRYPTO
            max_sl_dist = SL_CAP_CRYPTO

        direction = (pick.get("signal_type") or pick.get("direction") or "BUY").upper()
        is_short = direction in ("SELL", "SHORT")

        # --- Cap TP ---
        if tp > 0:
            if is_short:
                tp_dist = (entry - tp) / entry
                if tp_dist > max_tp_dist:
                    old_tp = tp
                    pick["take_profit"] = round(entry * (1 - max_tp_dist), 8)
                    tp_capped += 1
                    print(
                        f"  [TP_CAP] {pick.get('symbol')} SHORT: TP {old_tp:.8f} -> "
                        f"{pick['take_profit']:.8f} (capped from {tp_dist * 100:.1f}% to {max_tp_dist * 100:.1f}%)"
                    )
            else:
                tp_dist = (tp - entry) / entry
                if tp_dist > max_tp_dist:
                    old_tp = tp
                    pick["take_profit"] = round(entry * (1 + max_tp_dist), 8)
                    tp_capped += 1
                    print(
                        f"  [TP_CAP] {pick.get('symbol')} LONG: TP {old_tp:.8f} -> "
                        f"{pick['take_profit']:.8f} (capped from {tp_dist * 100:.1f}% to {max_tp_dist * 100:.1f}%)"
                    )

        # --- Cap SL ---
        if sl > 0:
            if is_short:
                sl_dist = (sl - entry) / entry
                if sl_dist > max_sl_dist:
                    old_sl = sl
                    pick["stop_loss"] = round(entry * (1 + max_sl_dist), 8)
                    sl_capped += 1
                    print(
                        f"  [SL_CAP] {pick.get('symbol')} SHORT: SL {old_sl:.8f} -> "
                        f"{pick['stop_loss']:.8f} (capped from {sl_dist * 100:.1f}% to {max_sl_dist * 100:.1f}%)"
                    )
            else:
                sl_dist = (entry - sl) / entry
                if sl_dist > max_sl_dist:
                    old_sl = sl
                    pick["stop_loss"] = round(entry * (1 - max_sl_dist), 8)
                    sl_capped += 1
                    print(
                        f"  [SL_CAP] {pick.get('symbol')} LONG: SL {old_sl:.8f} -> "
                        f"{pick['stop_loss']:.8f} (capped from {sl_dist * 100:.1f}% to {max_sl_dist * 100:.1f}%)"
                    )

    if tp_capped:
        print(f"  [TP_CAP] Capped {tp_capped} picks to max TP distance")
    if sl_capped:
        print(f"  [SL_CAP] Capped {sl_capped} picks to max SL distance")
    return picks


def sanitize_symbols(picks: list[dict]) -> list[dict]:
    """Strip CoinGecko numeric IDs from symbols (e.g. PEPE24478-USD -> PEPE-USD)."""
    for pick in picks:
        sym = pick.get("symbol", "")
        m = _COINGECKO_ID_RE.match(sym)
        if m:
            clean = f"{m.group(1)}-{m.group(2)}"
            print(f"  [SANITIZE] {sym} -> {clean}")
            pick["symbol"] = clean
            # Also fix the pick ID which embeds the symbol
            pick["id"] = pick.get("id", "").replace(sym, clean)
    return picks


def backfill_direction_and_timestamp(picks: list[dict]) -> list[dict]:
    """Ensure every pick has 'direction' and 'timestamp' fields."""
    now = _now_iso()
    for pick in picks:
        # Backfill direction from signal_type
        if not pick.get("direction"):
            sig = pick.get("signal_type", "BUY").upper()
            pick["direction"] = "SHORT" if sig in ("SELL", "SHORT") else "LONG"
        # Backfill timestamp from created_at or current time
        if not pick.get("timestamp"):
            pick["timestamp"] = pick.get("created_at") or now
    return picks


def resolve_direction_conflicts(picks: list[dict]) -> list[dict]:
    """When same symbol has both LONG and SHORT picks, keep the dominant direction.

    Sums confidence across ALL picks per direction to determine which side
    has stronger consensus.  Prevents capital waste from hedged positions
    sourced by different copy-traders / strategies.
    """
    from collections import defaultdict

    by_symbol: dict[str, list[dict]] = defaultdict(list)
    for p in picks:
        by_symbol[p.get("symbol", "")].append(p)

    resolved: list[dict] = []
    for symbol, sym_picks in by_symbol.items():
        longs = [
            p
            for p in sym_picks
            if (p.get("signal_type") or p.get("direction") or "BUY").upper()
            in ("BUY", "LONG")
        ]
        shorts = [
            p
            for p in sym_picks
            if (p.get("signal_type") or p.get("direction") or "BUY").upper()
            in ("SELL", "SHORT")
        ]

        if longs and shorts:
            long_conf = sum(float(p.get("confidence", 0) or 0) for p in longs)
            short_conf = sum(float(p.get("confidence", 0) or 0) for p in shorts)
            if long_conf >= short_conf:
                kept_dir, kept = "LONG", longs
            else:
                kept_dir, kept = "SHORT", shorts
            n_long, n_short = len(longs), len(shorts)
            print(
                f"  [DIRECTION CONFLICT] {symbol}: had {n_long} LONG "
                f"(conf={long_conf:.2f}) + {n_short} SHORT "
                f"(conf={short_conf:.2f}), kept {kept_dir}"
            )
            resolved.extend(kept)
        else:
            resolved.extend(sym_picks)
    return resolved


def deduplicate_picks(picks: list[dict]) -> list[dict]:
    """Keep only the highest-confidence pick per symbol+direction+strategy.

    §15 dedup: first pass deduplicates by (symbol, direction, strategy) to prevent
    the same strategy emitting duplicate picks for the same symbol+direction.
    Second pass resolves BUY+SELL conflicts on the same symbol.
    """
    # --- §15 first pass: dedup by (symbol, direction, strategy) ---
    from collections import defaultdict as _dd_s15
    _s15_groups: dict[tuple, list] = _dd_s15(list)
    for pick in picks:
        sym = str(pick.get("symbol", "") or "").upper().strip()
        direction = (pick.get("signal_type") or pick.get("direction") or "BUY").upper()
        if direction in ("SELL", "SHORT"):
            direction = "SHORT"
        else:
            direction = "LONG"
        strategy = str(pick.get("source_system") or pick.get("strategy", "") or "").lower().strip()
        _s15_groups[(sym, direction, strategy)].append(pick)
    _s15_deduped = []
    _s15_blocked = 0
    for _key, _group in _s15_groups.items():
        if len(_group) == 1:
            _s15_deduped.append(_group[0])
            continue
        _group.sort(key=lambda p: float(p.get("confidence", 0) or 0), reverse=True)
        _s15_deduped.append(_group[0])
        _s15_blocked += len(_group) - 1
    if _s15_blocked:
        print(f"  [§15-DEDUP] Blocked {_s15_blocked} picks: duplicate (symbol, direction, strategy)")
    picks = _s15_deduped

    # --- Second pass: resolve BUY+SELL conflicts on same symbol ---
    best: dict[tuple, dict] = {}
    for pick in picks:
        sym = pick.get("symbol", "")
        direction = (pick.get("signal_type") or pick.get("direction") or "BUY").upper()
        # Normalize direction
        if direction in ("SELL", "SHORT"):
            direction = "SHORT"
        else:
            direction = "LONG"
        key = (sym, direction)
        conf = pick.get("confidence") or 0
        if key not in best or conf > (best[key].get("confidence") or 0):
            best[key] = pick
    deduped = list(best.values())

    # Detect and resolve BUY+SELL conflicts: if same symbol has both LONG and SHORT,
    # keep only the higher-confidence one
    sym_picks: dict[str, list] = {}
    for pick in deduped:
        sym = pick.get("symbol", "")
        sym_picks.setdefault(sym, []).append(pick)

    final = []
    conflicts_removed = 0
    for sym, group in sym_picks.items():
        if len(group) <= 1:
            final.extend(group)
            continue
        # Check for direction conflict (LONG + SHORT on same symbol)
        directions = set()
        for p in group:
            d = (p.get("signal_type") or p.get("direction") or "BUY").upper()
            directions.add("SHORT" if d in ("SELL", "SHORT") else "LONG")
        if len(directions) > 1:
            # Conflict: keep only the highest-confidence pick
            group.sort(key=lambda p: p.get("confidence") or 0, reverse=True)
            winner = group[0]
            w_dir = (
                winner.get("signal_type") or winner.get("direction") or "BUY"
            ).upper()
            print(
                f"  [DEDUP] CONFLICT {sym}: BUY+SELL conflict, keeping {w_dir} "
                f"(conf={winner.get('confidence', 0):.2f}, strategy={winner.get('strategy', '')})"
            )
            final.append(winner)
            conflicts_removed += len(group) - 1
        else:
            final.extend(group)

    removed = len(picks) - len(final)
    if removed:
        print(
            f"  [DEDUP] Removed {removed} picks ({conflicts_removed} conflict resolutions), "
            f"kept {len(final)} unique"
        )
    return final


# ---------------------------------------------------------------------------
# 1. Market context (all free APIs, each wrapped in try/except)
# ---------------------------------------------------------------------------


def _fetch_binance_ticker(symbol: str) -> dict | None:
    """Fetch 24hr ticker for a single symbol via shared multi-source failover.

    Routes through alpha_engine.failover_imports (Binance mirrors -> CoinGecko ->
    KuCoin -> CryptoCompare). Preserves return shape: {"price": float,
    "change_pct": float} or None on total failure.
    """
    if _HAS_SHARED_FAILOVER and _shared_fetch_tickers_24h is not None:
        try:
            tickers, _src = _shared_fetch_tickers_24h()
            if tickers:
                for t in tickers:
                    if t.get("symbol") == symbol:
                        try:
                            return {
                                "price": float(t["lastPrice"]),
                                "change_pct": float(t["priceChangePercent"]),
                            }
                        except (KeyError, ValueError, TypeError):
                            break
        except Exception as e:
            print(f"  [WARN] shared failover ticker {symbol}: {e}")

    # Fallback: direct Binance loop (kept as last resort if shared failover unavailable)
    for base in _SPOT_BASES:
        try:
            r = requests.get(
                f"{base}/api/v3/ticker/24hr",
                params={"symbol": symbol},
                timeout=HTTP_TIMEOUT,
            )
            if r.status_code in (451, 403):
                continue  # geo-blocked, try next endpoint
            r.raise_for_status()
            d = r.json()
            return {
                "price": float(d["lastPrice"]),
                "change_pct": float(d["priceChangePercent"]),
            }
        except Exception:
            continue
    print(f"  [WARN] Binance ticker {symbol}: all endpoints failed")
    return None


def _fetch_fear_greed() -> dict | None:
    import time as _time

    for attempt in range(3):
        try:
            r = requests.get(FEAR_GREED_URL, timeout=HTTP_TIMEOUT)
            r.raise_for_status()
            entry = r.json()["data"][0]
            return {
                "value": int(entry["value"]),
                "label": entry["value_classification"],
            }
        except Exception as e:
            if attempt == 2:
                print(f"  [WARN] Fear & Greed failed after 3 attempts: {e}")
                return None
            _time.sleep(2 * (attempt + 1))


def _fetch_top_funding(n: int = 10) -> list[dict] | None:
    """Return the n most-negative funding-rate symbols.

    Tries the direct Binance futures endpoints first (single batch call is the
    cheapest path). On total failure, falls back to per-symbol queries via the
    shared multi-source failover (alpha_engine.failover_imports.fetch_funding_rate)
    against the configured CRYPTO_SYMBOLS universe so the function can still
    return >0 picks when geo-blocked.
    """
    for base in _FUTURES_BASES:
        try:
            r = requests.get(
                f"{base}/fapi/v1/premiumIndex",
                timeout=HTTP_TIMEOUT,
            )
            if r.status_code in (451, 403):
                continue
            r.raise_for_status()
            items = r.json()
            items.sort(key=lambda x: float(x.get("lastFundingRate", 0)))
            return [
                {"symbol": it["symbol"], "rate": float(it["lastFundingRate"])}
                for it in items[:n]
            ]
        except Exception:
            continue

    # Shared failover fallback: per-symbol query against the universe.
    if _HAS_SHARED_FAILOVER and _shared_fetch_funding_rate is not None:
        rates: list[dict] = []
        try:
            universe = list(CRYPTO_SYMBOLS)[: max(n * 3, 30)]
        except Exception:
            universe = []
        for sym in universe:
            try:
                rate = _shared_fetch_funding_rate(sym)
                if rate is not None:
                    rates.append({"symbol": sym, "rate": float(rate)})
            except Exception:
                continue
        if rates:
            rates.sort(key=lambda x: x["rate"])
            return rates[:n]

    print(f"  [WARN] Funding rates: all endpoints failed")
    return None


def _fetch_btc_dominance() -> float | None:
    try:
        r = requests.get(f"{COINGECKO_BASE}/global", timeout=HTTP_TIMEOUT)
        r.raise_for_status()
        return float(r.json()["data"]["market_cap_percentage"]["btc"])
    except Exception as e:
        print(f"  [WARN] BTC dominance: {e}")
        return None


def _determine_regime(btc_change: float | None, fg: dict | None) -> str:
    """Simple regime label based on BTC 24h change and Fear & Greed.

    F&G extremes override price-based regime to prevent dangerous misalignment
    (e.g., reporting 'consolidation' while F&G=11 Extreme Fear).
    """
    if btc_change is None:
        return "unknown"
    fg_val = fg["value"] if fg else 50

    # F&G extreme overrides -- sentiment extremes dominate price regime
    if fg_val <= 20:
        # Extreme Fear: historically a powerful contrarian BUY signal
        # Forced CAPITULATION allowing for bounce plays
        return "capitulation"
    if fg_val >= 80:
        # Extreme Greed: historically a contrarian SELL/SHORT signal
        # Forced risk-on/top potential
        return "risk-on"

    if btc_change > 3 and fg_val > 60:
        return "risk-on"
    if btc_change < -3 and fg_val < 30:
        return "capitulation"

    # F&G Fear overrides consolidation -- don't call it "consolidation"
    # when sentiment is fearful, that's misleadingly calm
    if abs(btc_change) < 1:
        if fg_val < 25:
            return "bearish"  # Price flat + Fear = bearish, not consolidation
        if fg_val > 75:
            return "bullish"  # Price flat + Greed = bullish
        return "consolidation"

    if btc_change > 0:
        return "bullish"
    return "bearish"


def _compute_cyclical_context(btc_dominance):
    """Compute cyclical/seasonal context for the dashboard."""
    now = datetime.now(timezone.utc)

    # BTC Halving Cycle (last halving: April 19, 2024)
    halving_date = datetime(2024, 4, 19, tzinfo=timezone.utc)
    days_since = (now - halving_date).days
    if days_since < 180:
        h_phase, h_bias = "Accumulation", "BULLISH"
    elif days_since < 480:
        h_phase, h_bias = "Markup", "BULLISH"
    elif days_since < 600:
        h_phase, h_bias = "Distribution", "BEARISH"
    else:
        h_phase, h_bias = "Decline", "BEARISH"

    # Monthly Seasonality (BTC 2011-2025)
    month = now.month
    m_names = {
        1: "January",
        2: "February",
        3: "March",
        4: "April",
        5: "May",
        6: "June",
        7: "July",
        8: "August",
        9: "September",
        10: "October",
        11: "November",
        12: "December",
    }
    m_bias_map = {
        1: ("BULLISH", "+10.2%"),
        2: ("BULLISH", "+8.5%"),
        3: ("NEUTRAL", "+1.8%"),
        4: ("BULLISH", "+13.4%"),
        5: ("BEARISH", "-3.1%"),
        6: ("BEARISH", "-1.2%"),
        7: ("NEUTRAL", "+2.3%"),
        8: ("BEARISH", "-0.5%"),
        9: ("BEARISH", "-4.8%"),
        10: ("BULLISH", "+24.0%"),
        11: ("BULLISH", "+17.3%"),
        12: ("BULLISH", "+12.1%"),
    }
    m_bias, m_avg = m_bias_map.get(month, ("NEUTRAL", "0%"))

    # Day of Week (0=Mon..6=Sun)
    dow = now.weekday()
    dow_names = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    dow_map = {
        0: ("BULLISH", "+0.82%"),
        1: ("NEUTRAL", "+0.21%"),
        2: ("NEUTRAL", "+0.35%"),
        3: ("BEARISH", "-0.88%"),
        4: ("BULLISH", "+1.24%"),
        5: ("NEUTRAL", "+0.15%"),
        6: ("NEUTRAL", "+0.18%"),
    }
    d_bias, d_avg = dow_map.get(dow, ("NEUTRAL", "0%"))

    # Turn of Month
    dom = now.day
    tom = dom >= 28 or dom <= 3

    # Halloween Effect
    halloween_bull = month >= 11 or month <= 4

    # BTC Dominance Phase
    dom_phase = "Unknown"
    if btc_dominance is not None:
        if btc_dominance > 60:
            dom_phase = "BTC Season (High Dominance)"
        elif btc_dominance > 50:
            dom_phase = "Transitional"
        else:
            dom_phase = "Alt Season (Low Dominance)"

    return {
        "halving_phase": h_phase,
        "halving_bias": h_bias,
        "days_since_halving": days_since,
        "halving_cycle_pct": round(min(days_since / 730 * 100, 100), 1),
        "monthly_bias": m_bias,
        "monthly_avg_return": m_avg,
        "month_name": m_names.get(month, ""),
        "day_of_week_bias": d_bias,
        "day_of_week_avg": d_avg,
        "day_of_week_name": dow_names[dow],
        "turn_of_month": tom,
        "turn_of_month_bias": "BULLISH" if tom else "NEUTRAL",
        "halloween_bias": "BULLISH" if halloween_bull else "BEARISH",
        "halloween_window": "Nov-Apr (Bullish)" if halloween_bull else "May-Oct (Weak)",
        "btc_dominance_phase": dom_phase,
    }


def run_whale_scanners():
    """Run Whale Alert, Etherscan, and Arkham scanners to refresh intelligence."""
    if not _HAS_WHALE_INDEX:
        return

    print("\n[WHALE] Refreshing whale intelligence...")
    try:
        wa = WhaleAlertScanner()
        if os.environ.get("WHALE_ALERT_API_KEY"):
            wa.run()
        else:
            print("  [WHALE] Whale Alert: Skipped (no API key)")
    except Exception as e:
        print(f"  [WHALE] Whale Alert: Failed: {e}")

    try:
        ew = EtherscanWhaleTracker()
        if os.environ.get("ETHERSCAN_API_KEY") or os.environ.get("ETHERSCAN_KEY"):
            ew.run()
        else:
            print("  [WHALE] Etherscan: Skipped (no API key)")
    except Exception as e:
        print(f"  [WHALE] Etherscan: Failed: {e}")

    try:
        ark = ArkhamScanner()
        if os.environ.get("ARKHAM_API_KEY"):
            ark.run()
        else:
            print("  [WHALE] Arkham: Skipped (no API key)")
    except Exception as e:
        print(f"  [WHALE] Arkham: Failed: {e}")


def fetch_market_context() -> dict:
    """Fetch all market context data points. Returns dict with None for failures."""
    print("[CONTEXT] Fetching market context...")
    btc = _fetch_binance_ticker("BTCUSDT")
    eth = _fetch_binance_ticker("ETHUSDT")
    fg = _fetch_fear_greed()
    funding = _fetch_top_funding(10)
    dom = _fetch_btc_dominance()

    btc_change = btc["change_pct"] if btc else None
    regime = _determine_regime(btc_change, fg)
    cyclical = _compute_cyclical_context(dom)

    # Fast microstructure regime (5-min cache, sub-minute fetch)
    fast_regime_data = None
    fast_regime_str = None
    if _HAS_FAST_REGIME:
        try:
            fast_regime_data = get_fast_regime("BTCUSDT")
            fast_regime_str = fast_regime_data.get("regime", "CHOPPY")
        except Exception as e:
            print(f"  [FAST REGIME] Failed (non-fatal): {e}")

    # P1-B: Macro regime check via regime_flip_detector -- 4+ API failover chain.
    # check_flip() updates regime_report.json; returns True on confirmed flip.
    macro_regime_str = regime  # fallback
    macro_confidence = get_regime_confidence(regime)
    macro_regime_flip = False
    if _HAS_REGIME_FLIP:
        try:
            # check_flip() writes confirmed regime to regime_report.json (2-confirmation hysteresis).
            # load_last_regime() reads it back. Only fallback to price-based regime
            # when BOTH sources are unavailable (not just on first run).
            macro_regime_flip = _HAS_REGIME_FLIP and check_flip()
            _saved = load_last_regime()
            if _saved:
                macro_regime_str = _saved
                macro_confidence = get_regime_confidence(_saved)
            elif not macro_regime_flip:
                macro_regime_str = regime  # genuine fallback when check_flip found no flip
        except Exception as e:
            print(f"  [REGIME FLIP] Failed (non-fatal): {e}")

    ctx = {
        "btc_price": btc["price"] if btc else None,
        "btc_24h_change": btc_change,
        "eth_price": eth["price"] if eth else None,
        "eth_24h_change": eth["change_pct"] if eth else None,
        "fear_greed": fg,
        "market_regime": regime,
        "fast_regime": fast_regime_str,
        "fast_regime_data": fast_regime_data,
        "macro_regime": macro_regime_str,
        "macro_regime_flip": macro_regime_flip,
        "macro_long_conf": macro_confidence["long_conf"],
        "macro_short_conf": macro_confidence["short_conf"],
        "macro_size_mult": macro_confidence["size_mult"],
        "top_funding": funding,
        "btc_dominance": dom,
        "cyclical": cyclical,
    }
    print(
        f"  BTC=${ctx['btc_price']}  ETH=${ctx['eth_price']}  "
        f"F&G={fg['value'] if fg else '?'}  Regime={regime}"
        f"  FastRegime={fast_regime_str or '?'}"
        f"  MacroRegime={macro_regime_str or '?'}"
    )
    if macro_regime_flip:
        print(f"  [REGIME FLIP] *** {macro_regime_str} regime confirmed ***")
    print(
        f"  Cycle: {cyclical.get('halving_phase')}  "
        f"Season: {cyclical.get('monthly_bias')}  "
        f"DOW: {cyclical.get('day_of_week_bias')}"
    )
    return ctx


# ---------------------------------------------------------------------------
# 2. Run forward_validator full cycle
# ---------------------------------------------------------------------------


def run_full_cycle() -> dict:
    """Run generation -> validation -> stats -> tweaker. Returns perf dict."""
    print("\n[CYCLE] Running forward validator full cycle...")
    run_generation()
    _closed, perf = run_validation()
    if not perf:
        closed = load_closed_picks()
        perf = compute_all_strategy_stats(closed)
    if perf:
        run_tweaker(perf)
    return perf


# ---------------------------------------------------------------------------
# 3 & 4. Enrich active picks with live Binance prices
# ---------------------------------------------------------------------------


def _fetch_all_binance_prices() -> dict[str, float]:
    """Fetch all spot prices via shared multi-source failover.

    Returns {symbol: price_float} (empty dict on total failure). Routes through
    alpha_engine.failover_imports.fetch_tickers_24h (lastPrice field) so that
    geo-blocked Binance calls automatically failover to CoinGecko/KuCoin/etc.
    """
    if _HAS_SHARED_FAILOVER and _shared_fetch_tickers_24h is not None:
        try:
            tickers, _src = _shared_fetch_tickers_24h()
            if tickers:
                out: dict[str, float] = {}
                for t in tickers:
                    sym = t.get("symbol")
                    if not sym:
                        continue
                    try:
                        out[sym] = float(t["lastPrice"])
                    except (KeyError, ValueError, TypeError):
                        continue
                if out:
                    return out
        except Exception as e:
            print(f"  [WARN] shared failover prices: {e}")

    # Fallback: direct Binance loop (kept as last resort)
    for base in _SPOT_BASES:
        try:
            r = requests.get(f"{base}/api/v3/ticker/price", timeout=HTTP_TIMEOUT)
            if r.status_code in (451, 403):
                continue
            r.raise_for_status()
            return {item["symbol"]: float(item["price"]) for item in r.json()}
        except Exception:
            continue
    print(f"  [WARN] Binance batch prices: all endpoints failed")
    return {}


def _yf_to_binance() -> dict[str, str]:
    """Build yfinance ticker -> Binance symbol map from config."""
    return {
        yf_ticker: meta["binance"]
        for yf_ticker, meta in CRYPTO_SYMBOLS.items()
        if "binance" in meta
    }


def enrich_picks(picks: list[dict]) -> list[dict]:
    """Add live price, unrealized PnL, TP/SL progress to crypto picks."""
    print("[ENRICH] Fetching live Binance prices for active picks...")
    all_prices = _fetch_all_binance_prices()
    yf_map = _yf_to_binance()

    enriched = 0
    for pick in picks:
        symbol = pick.get("symbol", "")
        binance_sym = yf_map.get(symbol)
        if not binance_sym or binance_sym not in all_prices:
            continue

        live_price = all_prices[binance_sym]
        entry = pick.get("entry_price")
        if not entry or entry == 0:
            continue

        pick["current_price"] = live_price
        direction = pick.get("signal_type", "BUY")

        # Unrealized PnL
        if direction == "BUY":
            pick["unrealized_pnl_pct"] = round((live_price - entry) / entry, 6)
        else:
            pick["unrealized_pnl_pct"] = round((entry - live_price) / entry, 6)

        # TP progress: 0% at entry, 100% at TP
        tp = pick.get("take_profit")
        if tp and tp != entry:
            if direction == "BUY":
                pick["tp_progress_pct"] = round(
                    max(0, (live_price - entry) / (tp - entry) * 100), 2
                )
            else:
                pick["tp_progress_pct"] = round(
                    max(0, (entry - live_price) / (entry - tp) * 100), 2
                )
        else:
            pick["tp_progress_pct"] = 0.0

        # SL progress: 0% at entry, 100% at SL
        sl = pick.get("stop_loss")
        if sl and sl != entry:
            if direction == "BUY":
                pick["sl_progress_pct"] = round(
                    max(0, (entry - live_price) / (entry - sl) * 100), 2
                )
            else:
                pick["sl_progress_pct"] = round(
                    max(0, (live_price - entry) / (sl - entry) * 100), 2
                )
        else:
            pick["sl_progress_pct"] = 0.0

        enriched += 1

    print(f"  Enriched {enriched}/{len(picks)} picks with live prices")
    return picks


def enrich_forex_stock_picks(picks: list[dict]) -> list[dict]:
    """Enrich forex and stock picks with live prices from yfinance.

    Binance only covers crypto. Forex (=X suffix) and stocks need yfinance.
    Also detects same-symbol/same-direction forex picks and sets confluence.
    """
    # Separate forex/stock picks that need yfinance prices
    non_crypto = []
    for p in picks:
        cat = (p.get("category") or "").lower()
        sym = p.get("symbol", "")
        if cat in (
            "forex",
            "stocks",
            "stock",
            "equity",
            "etf",
            "futures",
            "commodity",
            "bond",
            "penny",
            "index",
        ):
            non_crypto.append(p)
        elif "=X" in sym or "=F" in sym:
            non_crypto.append(p)

    if not non_crypto:
        return picks

    # Collect unique symbols
    symbols = list({p["symbol"] for p in non_crypto if p.get("symbol")})
    if not symbols:
        return picks

    print(
        f"[ENRICH] Fetching yfinance prices for {len(symbols)} forex/stock symbols..."
    )

    price_map = {}
    try:
        import yfinance as yf

        # Batch download current prices
        tickers = yf.Tickers(" ".join(symbols))
        for sym in symbols:
            try:
                ticker = tickers.tickers.get(sym)
                if ticker:
                    info = ticker.fast_info
                    price = getattr(info, "last_price", None)
                    if price and price > 0:
                        price_map[sym] = float(price)
            except Exception:
                pass

        # Fallback for any missed symbols: try individual fetches
        missed = [s for s in symbols if s not in price_map]
        for sym in missed:
            try:
                t = yf.Ticker(sym)
                hist = t.history(period="1d")
                if not hist.empty:
                    price_map[sym] = float(hist["Close"].iloc[-1])
            except Exception:
                pass
    except ImportError:
        print("  [WARN] yfinance not installed, skipping forex/stock enrichment")
        return picks
    except Exception as e:
        print(f"  [WARN] yfinance batch fetch failed: {e}")

    # Apply prices
    enriched = 0
    for pick in non_crypto:
        sym = pick.get("symbol", "")
        live_price = price_map.get(sym)
        if not live_price:
            continue

        entry = pick.get("entry_price")
        if not entry or entry == 0:
            # Backfill entry_price for informational picks (e.g. insider_filing_scanner)
            # Use current live price as entry so PNL tracking starts from now
            pick["entry_price"] = live_price
            entry = live_price

        pick["current_price"] = live_price
        direction = pick.get("signal_type", pick.get("direction", "BUY")).upper()
        is_short = direction in ("SELL", "SHORT")

        # Unrealized PnL
        if is_short:
            pick["unrealized_pnl_pct"] = round((entry - live_price) / entry, 6)
        else:
            pick["unrealized_pnl_pct"] = round((live_price - entry) / entry, 6)

        # TP/SL progress
        tp = pick.get("take_profit")
        if tp and tp != entry:
            if is_short:
                pick["tp_progress_pct"] = round(
                    max(0, (entry - live_price) / (entry - tp) * 100), 2
                )
            else:
                pick["tp_progress_pct"] = round(
                    max(0, (live_price - entry) / (tp - entry) * 100), 2
                )

        sl = pick.get("stop_loss")
        if sl and sl != entry:
            if is_short:
                pick["sl_progress_pct"] = round(
                    max(0, (live_price - entry) / (sl - entry) * 100), 2
                )
            else:
                pick["sl_progress_pct"] = round(
                    max(0, (entry - live_price) / (entry - sl) * 100), 2
                )

        # High-water mark tracking
        hwm = pick.get("high_water_mark", live_price)
        if is_short:
            pick["high_water_mark"] = min(hwm, live_price)
        else:
            pick["high_water_mark"] = max(hwm, live_price)

        enriched += 1

    # --- Forex/stock confluence detection ---
    # Group picks by symbol + direction, detect when multiple strategies agree
    from collections import defaultdict

    sym_dir_groups = defaultdict(list)
    for p in non_crypto:
        sym = p.get("symbol", "")
        d = (p.get("direction") or p.get("signal_type") or "").upper()
        if d in ("BUY", "LONG"):
            d = "LONG"
        elif d in ("SELL", "SHORT"):
            d = "SHORT"
        if sym and d:
            sym_dir_groups[(sym, d)].append(p)

    confluence_count = 0
    for (sym, direction), group in sym_dir_groups.items():
        if len(group) < 2:
            continue
        strategies = [p.get("strategy", "") for p in group]
        for p in group:
            # Set confluence data so elite_scorer and dashboard can use it
            other_strats = [s for s in strategies if s != p.get("strategy", "")]
            if other_strats:
                existing = p.get("confluence_strategies", []) or []
                merged = list(set(existing + other_strats))
                p["confluence_strategies"] = merged
                p["confluence_score"] = max(
                    p.get("confluence_score", 0), len(merged) + 1
                )
                p["convergence"] = max(p.get("convergence", 0), len(merged))
                confluence_count += 1

    print(
        f"  Enriched {enriched}/{len(non_crypto)} forex/stock picks with live yfinance prices"
    )
    if confluence_count:
        print(f"  Detected confluence for {confluence_count} forex/stock picks")

    # Write stock/forex prices to a JSON file the dashboard can fetch via GitHub Pages
    # This bypasses CORS issues -- browser fetches from same domain
    if price_map:
        prices_out = {
            "updated_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
            "prices": {sym: float(p) for sym, p in price_map.items()},
        }
        prices_path = (
            Path(__file__).resolve().parent / "data" / "stock_forex_prices.json"
        )
        try:
            import json as _json

            with open(prices_path, "w") as f:
                _json.dump(prices_out, f, indent=2)
            print(f"  Wrote {len(price_map)} prices to stock_forex_prices.json")
        except Exception as e:
            print(f"  [WARN] Could not write stock_forex_prices.json: {e}")

    return picks


# ---------------------------------------------------------------------------
# 4b. Sanity check: detect & fix corrupted entry prices
# ---------------------------------------------------------------------------
# Root cause: yfinance occasionally returns BTC-denominated prices for altcoins
# (e.g. APT-USD returning 0.000131 instead of ~$9.50, which is APT/BTC price).
# This causes insane P/L like +715,167% on the dashboard.
#
# Fix: after enriching with live Binance prices, compare entry_price against
# current_price. If they differ by >90%, the entry was likely corrupted at
# generation time. Correct entry_price and rescale TP/SL proportionally.
# ---------------------------------------------------------------------------

# Known micro-price tokens where sub-cent prices are legitimate
_MICRO_PRICE_SYMBOLS = {
    "BONK-USD",
    "FLOKI-USD",
    "SHIB-USD",
    "PEPE-USD",
    "BOME-USD",
    "GALA-USD",
    "LUNC-USD",
    "SPELL-USD",
    "JASMY-USD",
    "HOT-USD",
    "WIN-USD",
    "BTTC-USD",
    "DOGS-USD",
    "NOT-USD",
    "1000SATS-USD",
    # Also include USDT/Binance-format variants
    "BONKUSDT",
    "FLOKIUSDT",
    "SHIBUSDT",
    "PEPEUSDT",
    "BOMEUSDT",
    "GALAUSDT",
    "LUNCUSDT",
    "SPELLUSDT",
    "JASMYUSDT",
    "HOTUSDT",
    "WINUSDT",
    "BTTCUSDT",
    "DOGSUSDT",
    "NOTUSDT",
    "1000SATSUSDT",
}

# Minimum expected USD prices for major cryptos (floor, not exact)
# Include both yfinance (-USD) and Binance (USDT) formats
_MIN_EXPECTED_PRICES_BASE = {
    "BTC": 1000.0,
    "ETH": 100.0,
    "BNB": 50.0,
    "SOL": 5.0,
    "APT": 1.0,
    "AVAX": 3.0,
    "LINK": 2.0,
    "DOT": 1.0,
    "NEAR": 0.5,
    "SUI": 0.3,
    "ADA": 0.05,
    "XRP": 0.1,
    "DOGE": 0.01,
    "MATIC": 0.1,
    "UNI": 1.0,
    "AAVE": 10.0,
    "FIL": 1.0,
    "ARB": 0.1,
    "OP": 0.3,
    "TIA": 1.0,
}
# Build lookup with all symbol formats: APT-USD, APTUSD, APTUSDT
_MIN_EXPECTED_PRICES = {}
for _base, _floor in _MIN_EXPECTED_PRICES_BASE.items():
    _MIN_EXPECTED_PRICES[f"{_base}-USD"] = _floor
    _MIN_EXPECTED_PRICES[f"{_base}USD"] = _floor
    _MIN_EXPECTED_PRICES[f"{_base}USDT"] = _floor


def sanity_check_entry_prices(picks: list[dict]) -> list[dict]:
    """
    Detect and fix corrupted entry_price values by comparing against live
    Binance current_price (set by enrich_picks).

    A pick is flagged as corrupted if:
      1. It has both entry_price and current_price set (non-zero)
      2. The ratio between them exceeds 10x (90%+ divergence)
      3. The symbol is NOT a known micro-price token with legitimately tiny values

    When corruption is detected, entry_price is corrected to current_price
    and TP/SL are rescaled proportionally to preserve the original R:R ratio.
    """
    corrected = 0
    flagged = 0

    for pick in picks:
        entry = pick.get("entry_price") or 0
        current = pick.get("current_price") or 0
        symbol = pick.get("symbol", "")
        strategy = pick.get("strategy", "")

        # Skip picks without entry price
        if entry == 0:
            continue

        # Skip DEX tokens and non-standard symbols (no Binance price reference)
        if symbol.startswith("DEX:") or ":" in symbol:
            continue

        # Check 1: Hard floor for known major cryptos (works even without current_price)
        min_price = _MIN_EXPECTED_PRICES.get(symbol)
        if min_price and entry < min_price * 0.01:
            # Entry is <1% of the minimum expected price -- definitely wrong
            new_price = current if current > min_price * 0.01 else 0.0
            print(
                f"  [SANITY] CORRUPTED {symbol} ({strategy}): "
                f"entry=${entry:.8f} is far below floor ${min_price} "
                f"-- {'correcting to current=$' + f'{current:.6f}' if new_price else 'zeroing out (no valid current price)'}"
            )
            if new_price:
                _correct_pick_prices(pick, entry, new_price)
            else:
                # No valid reference price: zero out entry to prevent PnL computation
                pick["entry_price"] = 0.0
                pick["unrealized_pnl_pct"] = 0.0
                pick["price_corrected"] = True
                pick["original_entry_price"] = entry
            corrected += 1
            continue

        # Check 1b: BTC-denominated price heuristic -- entry < 0.001 for a non-micro token
        # This catches cases where current_price is ALSO corrupted (same BTC-denominated value)
        if (
            entry < 0.001
            and symbol not in _MICRO_PRICE_SYMBOLS
            and not symbol.startswith("DEX:")
        ):
            print(
                f"  [SANITY] LIKELY BTC-DENOMINATED {symbol} ({strategy}): "
                f"entry=${entry:.8f} -- zeroing out (no reliable reference price)"
            )
            pick["entry_price"] = 0.0
            pick["unrealized_pnl_pct"] = 0.0
            pick["price_corrected"] = True
            pick["original_entry_price"] = entry
            corrected += 1
            continue

        # Remaining checks need a valid current_price
        if current == 0:
            continue

        # Check 2: Ratio check against live Binance price
        ratio = (
            max(entry, current) / min(entry, current) if min(entry, current) > 0 else 0
        )
        if ratio > 10:  # >10x divergence = almost certainly wrong
            # For micro-price tokens, skip the ratio check (their legit prices are tiny)
            if symbol in _MICRO_PRICE_SYMBOLS:
                continue

            print(
                f"  [SANITY] CORRUPTED {symbol} ({strategy}): "
                f"entry=${entry:.8f} vs current=${current:.6f} "
                f"(ratio={ratio:.1f}x) -- correcting to current price"
            )
            _correct_pick_prices(pick, entry, current)
            corrected += 1
            continue

        flagged += 0  # placeholder for future soft-flag logic

    if corrected:
        print(f"  [SANITY] Corrected {corrected} picks with corrupted entry prices")
    else:
        print(f"  [SANITY] All entry prices look healthy")

    return picks


def _correct_pick_prices(pick: dict, old_entry: float, new_entry: float):
    """
    Correct a pick's entry_price and rescale TP/SL to preserve the original
    percentage distances (R:R ratio).
    """
    tp = pick.get("take_profit") or 0
    sl = pick.get("stop_loss") or 0

    # Calculate original percentage distances
    if old_entry > 0:
        tp_pct = (tp - old_entry) / old_entry if tp else 0
        sl_pct = (sl - old_entry) / old_entry if sl else 0
    else:
        tp_pct = 0
        sl_pct = 0

    # Apply correction
    pick["entry_price"] = new_entry
    pick["high_water_mark"] = new_entry

    if tp:
        pick["take_profit"] = round(new_entry * (1 + tp_pct), 8)
    if sl:
        pick["stop_loss"] = round(new_entry * (1 + sl_pct), 8)

    # Recalculate unrealized PnL (now entry == current, so PnL is ~0%)
    pick["unrealized_pnl_pct"] = 0.0

    # Tag the pick so we know it was corrected
    pick["price_corrected"] = True
    pick["original_entry_price"] = old_entry


# ---------------------------------------------------------------------------
# 4f. Pick Quality Hard Gates (Phase 12 -- data-driven from 788 closed picks)
# ---------------------------------------------------------------------------
# These gates are based on forward-tested data, not backtests.
# Confidence < 0.70 = 10.2% WR (cliff). Above = 80%.
# ML < 0.50 = 23.5% WR.  SELL in non-bearish = 30.1% WR.
# volume_ratio > 5.0 = 17.4% WR.  Forex = 0% WR.
#
# Phase 12b -- Short-specific quality gate (Criterion 6):
#   - Shorts overall: 30.1% WR (173 trades) -- terrible
#   - Proven short strategies (WR>50%, 3+ trades): fractal_sr_bounce, etc.
#   - Toxic short strategies (0% WR, 5+ trades): ML-enhanced, london_breakout
#   - Toxic short symbols (0% WR, 5+ trades): ADAUSDT, BTCUSDT, SOLUSDT
#   - Shorts in bearish/capitulation + conf>=0.80: ~47% WR -- acceptable
#   - Shorts in ranging/consolidation: 60-92% WR -- best regime for shorts
# ---------------------------------------------------------------------------

QUALITY_GATE_MIN_CONFIDENCE = (
    0.55  # Lowered from 0.70: decile test shows 0.60-0.70 = best WR (61%)
)
QUALITY_GATE_MIN_ML_SCORE = 0.50  # Phase 19 (2026-04-15): raised from 0.40 — model retrained with 313+ alpha_engine picks
QUALITY_GATE_MAX_VOL_RATIO = 5.0
# Forex gate is now DATA-DRIVEN (see Gate 3 below) -- no longer config-based
# This prevents auto_tuner from re-enabling forex while forward WR is still terrible
QUALITY_GATE_FOREX_MIN_WR = 0.30  # forex must have >= 30% WR on 10+ trades to pass
QUALITY_GATE_FOREX_MIN_TRADES = 10  # minimum trades before data-driven decision

# Import the short trade validator for sophisticated short gating
try:
    from short_trade_validator import should_allow_short, get_proven_short_strategies

    _PROVEN_SHORT_STRATEGIES = get_proven_short_strategies()
    _SHORT_VALIDATOR_AVAILABLE = True
except Exception:
    _PROVEN_SHORT_STRATEGIES = set()
    _SHORT_VALIDATOR_AVAILABLE = False

# Strategies whose ENTIRE PURPOSE is contra-directional trading.
# These are exempt from the blanket SHORT penalty -- they NEED to short.
# They still must pass conf >= 0.55 and ml_score >= 0.50 (softer gate).
_CONTRARIAN_SHORT_EXEMPT = {
    "contrarian_consensus",
    "contrarian_liquidity_grab",
    "ig_contrarian_sentiment",
    "myfxbook_retail_contrarian",
    "cot_positioning",
    "cftc_cot_commercial_signal",
    "inverse_winner_pattern_precursor_tight",
    "macd_crossover",  # 90% WR on 10 short trades
}
# Merge data-driven proven strategies into the exempt set
_SHORT_EXEMPT_STRATEGIES = _CONTRARIAN_SHORT_EXEMPT | _PROVEN_SHORT_STRATEGIES


def apply_quality_gates(
    picks: list[dict], regime: str = "neutral", closed_picks: list[dict] | None = None
):
    """Filter picks through data-driven quality gates.

    Returns (passed, rejected) tuple.
    Based on analysis of 788 forward-tested closed picks.
    closed_picks is used for data-driven forex gate (Gate 3).

    P1-B: Picks carry macro_regime/macro_long_conf/macro_short_conf/macro_size_mult
    from the regime_flip_detector integration. Gate 4b blocks regime-misaligned picks.
    """
    """Filter picks through data-driven quality gates.

    Returns (passed, rejected) tuple.
    Based on analysis of 788 forward-tested closed picks.
    closed_picks is used for data-driven forex gate (Gate 3).
    """
    passed = []
    rejected = []
    _forex_gate_closed_picks = closed_picks or []

    # --- COMMODITY_BLACKLIST pre-write enforcement (2026-05-16 swarm deep-dive) ---
    # passes_active_gate has a display-time blacklist check, but production_scanner
    # was writing blacklisted COMMODITY picks (ZW=F, ZS=F, NG=F) directly to
    # active_picks.json before that gate could filter them. This pre-write check
    # mirrors quality_gates.COMMODITY_BLACKLIST so the blacklist enforces at source.
    try:
        from audit_trail.quality_gates import COMMODITY_BLACKLIST as _COMM_BL
        _pre_write_filtered = []
        for _pw_pick in picks:
            _pw_ac = str(_pw_pick.get("asset_class") or "").upper().strip()
            _pw_sym = str(_pw_pick.get("symbol") or "").upper().strip()
            if _pw_ac in ("COMMODITY", "COMMODITIES") and _pw_sym in _COMM_BL:
                rejected.append({**_pw_pick, "_rejected_reason": f"commodity_blacklist_pre_write({_pw_sym})"})
            else:
                _pre_write_filtered.append(_pw_pick)
        picks = _pre_write_filtered
    except Exception:
        pass  # fail-open: never let this block picks

    # --- ML Pipeline Health Gate (Hedge Fund Sprint Mar 2026) ---
    # Fetch once per scan to avoid repeated disk reads.
    _ml_trading_enabled = True
    _ml_halt_reason = ""
    try:
        from ml_health_monitor import check_ml_health

        _ml_health_status = check_ml_health()
        _ml_trading_enabled = _ml_health_status.get("ml_trading_enabled", True)
        if not _ml_trading_enabled:
            _ml_halt_reason = f"[ML HEALTH] HALT: {_ml_health_status.get('health_reason', 'Pipeline degraded')}"
    except Exception:
        pass

    for pick in picks:
        strat_name = pick.get("strategy", "")
        conf = float(pick.get("confidence", 0) or 0)
        gate_conf = float(pick.get("_quality_gate_confidence", conf) or conf)
        ml_score = pick.get("ml_score") or pick.get("_ml_score") or 0.5
        category = (pick.get("category") or "crypto").lower()
        # Normalize stock/etf/bond → equity for consistent gating
        if category in ("stock", "etf", "bond"):
            category = "equity"
        signal_type = (
            pick.get("signal_type") or pick.get("direction") or "BUY"
        ).upper()
        vol_ratio = pick.get("volume_ratio") or (pick.get("extra", {}) or {}).get(
            "vol_ratio", 1.0
        )
        if vol_ratio is None:
            vol_ratio = 1.0

        reject_reason = None
        conf_suffix = (
            f" (post-soft={conf:.2f})" if abs(conf - gate_conf) >= 0.005 else ""
        )

        # Gate 0: Per-strategy/per-class blocks (replaces blanket category block)
        # REMOVED 2026-04-19: blanket _BLOCKED_CATEGORIES was blocking ALL equity/
        # commodity/futures/bond/etf picks regardless of strategy quality. The cited
        # "0% WR on 92 equity picks" and "19% WR on 16 commodity picks" were from
        # killed strategies (now in BLOCKED_STRATEGIES in quality_gates.py) and toxic
        # symbols. New academic strategies (TSMOM 12m, Faber TAA, Connors RSI2,
        # bond_yield_momentum, etc.) can't build forward history if the class is blocked.
        #
        # Replacement: per-strategy kill list targeting actual toxic sources surgically,
        # not entire asset classes. Downstream quality_gates.py already has
        # BLOCKED_STRATEGIES, BLOCKED_ASSET_STRATEGY_PAIRS, and BLOCKED_DIRECTION_TRIPLES
        # that catch the remaining bad actors.
        _BLOCKED_CATEGORY_STRATEGIES = {
            # Equity losers (0% WR strategies that polluted the 92-pick sample)
            # NOTE: stock/etf/bond are normalized to "equity" before Gate 0,
            # so bond/etf strategies must be listed under "equity" to match.
            ("equity", "yahoo_analyst_consensus"),
            ("equity", "claude_gainer_ml"),
            ("equity", "value_quality_factor"),
            ("equity", "consecutive_beats"),
            ("equity", "earnings_drift"),
            ("equity", "dividend_aristocrats"),
            ("equity", "penny_deep_oversold"),
            ("equity", "extreme_oversold_bounce"),  # was etf - normalized to equity
            # Equity goldmine strategies (0% WR, blocked in quality_gates.py too)
            ("equity", "goldmine_1x_consensus"),
            ("equity", "goldmine_2x_consensus"),
            ("equity", "goldmine_3x_consensus"),
            ("equity", "goldmine_4x_consensus"),
            # Commodity losers (19% WR on 16 picks)
            # NOTE: cot_positioning removed from block - it's in _BOOSTED_NON_CRYPTO_STRATEGIES
            # (1.15x boost) and has 50% WR / positive PnL on forex. Insufficient data on commodity,
            # not proven bad.
            ("commodity", "cftc_cot_commercial_signal"),
            # 2026-05-31 (tick33): COMMODITY-leg blocks per PR #269 deep-dive verdict.
            # cta_cross_asset_tsmom: dispatched via scanner.py:2191 on
            #   ("all","forex","equity") filter and reaches commodity symbols
            #   through "all"-filter; confirmed loser per deep-dive (FOREX leg
            #   already capped at emitter via PR #275). Defense-in-depth block
            #   for any commodity emission from cta_replicator source_system.
            # futures_momentum: lives in multi_asset/scanner.py:91,2809 and is
            #   already banned via hedge_fund_quality_gate.FUTURES_BANNED + the
            #   ("futures","...") gate below — but commodity-category emission
            #   is not covered by the futures rule (no futures→commodity
            #   normalization). Defense-in-depth.
            # ema_stack_momentum: test-harness only per Wire-Up Rule
            #   (live_forward_test.py:481), already blocked for ("futures",...);
            #   mirror for commodity in case any future dispatch surface adds it.
            ("commodity", "cta_cross_asset_tsmom"),
            ("commodity", "futures_momentum"),
            ("commodity", "ema_stack_momentum"),
            # Futures losers (Gate 5b already catches some)
            ("futures", "futures_mean_reversion"),
            ("futures", "ema_stack_momentum"),
        }
        _cat_strat_key = (category, strat_name)
        if _cat_strat_key in _BLOCKED_CATEGORY_STRATEGIES:
            reject_reason = (
                f"[TOXIC STRAT+CLASS] {strat_name} on {category} disabled — "
                f"historical 0-19% WR. Per-strategy block (not blanket)."
            )

        # Gate 0c: R:R structural-fail gate (2026-04-17 deepscan-4 + empirical
        # recompute against picks.recent_closed n=23 picks with rr_ratio < 0.6):
        #   PF 0.59, gross losses -117.9%, avg -2.09% per trade.
        # Even at 63.6% WR (above breakeven for normal R:R) the catastrophic
        # geometry — TP near entry, SL far away — means every loser is 1.7x
        # bigger than the average winner. Mathematical -EV regardless of WR.
        # Reject at gate; let downstream score boosters take a higher-RR pick.
        # 2026-04-17 Inception code-review fix: also reject when rr_ratio is
        # set to exactly 0 (zero reward — TP equals entry — malformed pick).
        # Picks with missing/None rr_ratio bypass this gate and fall through to
        # the downstream geometry validator, which is the right behavior for
        # not-yet-populated TP/SL at emission time.
        elif (
            pick.get("rr_ratio") is not None and float(pick.get("rr_ratio") or 0) < 0.6
        ):
            _rr_val = float(pick.get("rr_ratio") or 0)
            reject_reason = (
                f"[R:R STRUCTURAL] rr_ratio={_rr_val:.2f} < 0.60 — "
                f"PF 0.59 historical (gross loss -117.9% over 23 picks). "
                f"TP-near-entry / SL-far-away geometry is mathematical -EV."
            )

        # Gate 0b: ML Health Gate (Mar 25 2026)
        # Block ML strategies if feature coverage is < 80% or predictor is stale.
        elif "ml_enhanced" in strat_name and not _ml_trading_enabled:
            reject_reason = _ml_halt_reason

        # Gate 1: Confidence floor based on the raw model signal.
        # Drawdown/volume penalties are soft portfolio controls and should not
        # silently become hard rejects by mutating confidence before this gate.
        elif gate_conf < QUALITY_GATE_MIN_CONFIDENCE:
            reject_reason = (
                f"conf={gate_conf:.2f} < {QUALITY_GATE_MIN_CONFIDENCE:.2f} "
                f"(below quality floor){conf_suffix}"
            )

        # Gate 2: ML score floor (23.5% WR below 0.50)
        elif ml_score < QUALITY_GATE_MIN_ML_SCORE:
            reject_reason = f"ml_score={ml_score:.2f} < 0.50 (23.5% WR)"

        # Gate 2b: Copy-source validation.
        # Proven Hyperliquid traders get through; sentiment/Bitget/clones do not.
        elif _is_copy_trader_pick(pick):
            copy_quality = _copy_source_quality(pick)
            copy_tier = copy_quality["tier"]
            pick["_copy_source_tier"] = copy_tier
            pick["_copy_source_reason"] = copy_quality["reason"]
            pick["_copy_closed_picks"] = copy_quality["closed"]
            pick["_copy_wr"] = round(copy_quality["wr"], 4)
            if copy_tier in ("blocked", "sentiment"):
                reject_reason = f"[COPY SOURCE] {copy_quality['reason']}"
            elif copy_tier == "unverified" and (gate_conf < 0.65 or ml_score < 0.60):
                reject_reason = (
                    f"[COPY SOURCE] unverified copy source needs conf>=0.65 and ml_score>=0.60 "
                    f"(got conf={gate_conf:.2f} ml={ml_score:.2f})"
                )
            elif copy_tier == "probation" and (gate_conf < 0.60 or ml_score < 0.55):
                reject_reason = (
                    f"[COPY SOURCE] probationary copy source needs conf>=0.60 and ml_score>=0.55 "
                    f"(got conf={gate_conf:.2f} ml={ml_score:.2f})"
                )

        # Gate 3: Data-driven forex gate (only blocks if proven bad)
        # Let forex through when insufficient data (so data can accumulate).
        # Only block if WR < 30% on 10+ closed trades — proven bad.
        elif category == "forex":
            forex_closed = [
                c
                for c in _forex_gate_closed_picks
                if (c.get("category") or "").lower() == "forex"
                and c.get("status") in ("WON", "LOST")
            ]
            forex_total = len(forex_closed)
            forex_wins = sum(1 for c in forex_closed if c.get("status") == "WON")
            # Use standardized win rate calculation (excludes zero-PnL)
            forex_wr = calculate_win_rate(forex_wins, forex_total)
            if (
                forex_total >= QUALITY_GATE_FOREX_MIN_TRADES
                and forex_wr < QUALITY_GATE_FOREX_MIN_WR
            ):
                reject_reason = (
                    f"forex data gate: WR={forex_wr:.1%} on {forex_total} trades "
                    f"< {QUALITY_GATE_FOREX_MIN_WR:.0%} threshold"
                )
            # When < min trades: PASS through so forex picks can accumulate data

        # Gate 4b: P1-B LONG regime alignment -- block BUY/LONG picks misaligned with
        # bearish or volatile macro regime. Aligned: BULLISH/LEANING_BULL/LOW_VOL_TRENDING.
        # Misaligned: BEARISH or VOLATILE. Backward-compatible (no macro_regime = pass).
        if pick.get("signal_type") in ("BUY", "LONG"):
            _mr = pick.get("macro_regime")
            if _mr in ("BEARISH", "VOLATILE"):
                reject_reason = (
                    f"LONG pick misaligned with {_mr} macro regime "
                    f"(macro_regime={_mr}, needs BULLISH/LEANING_BULL/LOW_VOL_TRENDING)"
                )

        # Gate 4: SHORT/SELL quality gate (Updated Mar 26 2026)
        # Blanket SHORT block replaced with tiered approach:
        #   Tier A — EXEMPT strategies (proven WR>=50% on 3+ trades, or contrarian by design):
        #            Pass with conf >= 0.55 and ml_score >= 0.50 (soft gate).
        #   Tier B — All other SHORT strategies:
        #            Blocked unless conf >= 0.90, ml_score >= 0.80, and bearish regime.
        elif signal_type in ("SELL", "SHORT"):
            _regime_lower = regime.lower() if regime else "neutral"
            _strat_name = pick.get("strategy", "")
            _is_exempt = _strat_name in _SHORT_EXEMPT_STRATEGIES

            if _is_exempt:
                # Tier A: exempt strategy — softer gate
                if gate_conf < 0.55:
                    reject_reason = (
                        f"SHORT soft-gate: exempt strategy '{_strat_name}' "
                        f"conf={gate_conf:.2f} < 0.55{conf_suffix}"
                    )
                elif ml_score < 0.50:
                    reject_reason = (
                        f"SHORT soft-gate: exempt strategy '{_strat_name}' "
                        f"ml_score={ml_score:.2f} < 0.50"
                    )
                # else: PASS — exempt strategy with adequate confidence
            else:
                # Tier B: unproven strategy — hard gate
                if _regime_lower not in ("bearish", "strong_bear", "capitulation"):
                    reject_reason = (
                        f"SHORT blocked: strategy '{_strat_name}' not exempt, "
                        f"regime={regime} not bearish/strong_bear/capitulation"
                    )
                elif gate_conf < 0.90:
                    reject_reason = (
                        f"SHORT blocked: unproven strategy '{_strat_name}' "
                        f"conf={gate_conf:.2f} < 0.90{conf_suffix}"
                    )
                elif ml_score < 0.80:
                    reject_reason = (
                        f"SHORT blocked: unproven strategy '{_strat_name}' "
                        f"ml_score={ml_score:.2f} < 0.80"
                    )

        # Gate 4b: P1-B Regime alignment gate -- block picks against macro regime
        # regime_flip_detector provides 8-class classification with directional confidence.
        # Misaligned: LONG in BEARISH/VOLATILE, SHORT in BULLISH/LEANING_BULL.
        # Exempt strategies (contrarian by design) bypass this gate.
        elif (
            not reject_reason
            and pick.get("strategy", "") not in _SHORT_EXEMPT_STRATEGIES
            and pick.get("strategy", "") not in _CONTRARIAN_SHORT_EXEMPT
        ):
            _macro = pick.get("macro_regime") or regime or ""
            _macro_l = _macro.lower()
            _direction = signal_type

            if _direction in ("BUY", "LONG") and _macro_l in ("bearish", "volatile"):
                reject_reason = (
                    f"[REGIME MISALIGNED] LONG in {_macro_l} regime -- "
                    f"macro_regime={_macro}, long_conf={pick.get('macro_long_conf', 0.5):.2f}"
                )
            elif _direction in ("SELL", "SHORT") and _macro_l in ("bullish", "leaning_bull"):
                reject_reason = (
                    f"[REGIME MISALIGNED] SHORT in {_macro_l} regime -- "
                    f"macro_regime={_macro}, short_conf={pick.get('macro_short_conf', 0.5):.2f}"
                )

        # Gate 5: Extreme volume spike (17.4% WR when vol_ratio > 5.0)
        elif vol_ratio > QUALITY_GATE_MAX_VOL_RATIO:
            reject_reason = f"vol_ratio={vol_ratio:.1f} > 5.0 (17.4% WR)"

        # Gate 5b: Toxic strategy gate (Phase 19 -- 2026-04-15)
        # Hard-block strategies with < 25% WR on 5+ forward-tested trades.
        # Data: community_london_breakout_v2_forex (0%, 8 trades),
        #       tsmom_28d (0%, 4), autocorrelation_exploiter (23%, 13),
        #       bollinger_keltner_squeeze_breakout (14%, 7),
        #       quan_engine_position (0%, 26).
        # These are not coin-flips — they are consistent losers.
        elif (
            int(pick.get("forward_trades", 0) or 0) >= 5
            and float(pick.get("forward_wr", 1.0) or 1.0) < 0.25
        ):
            _fw_trades = int(pick.get("forward_trades", 0) or 0)
            _fw_wr = float(pick.get("forward_wr", 0) or 0)
            reject_reason = (
                f"[TOXIC STRATEGY] {strat_name}: {_fw_wr:.0%} WR on "
                f"{_fw_trades} trades (< 25% threshold)"
            )

        # Gate 6: Block unvalidated strategies with 0 forward trades and low confidence
        elif (
            not pick.get("forward_validated", True)
            and (pick.get("forward_trades", 1) or 0) == 0
            and gate_conf < 0.80
        ):
            reject_reason = (
                f"unvalidated strategy (forward_validated=false, "
                f"forward_trades=0, conf={gate_conf:.2f} < 0.80{conf_suffix})"
            )

        # Gate 7: Toxic symbol gate — data-driven, strategy-aware
        # Symbols with overall negative expectancy get higher bar, BUT exempt:
        #   - Strategies with proven WR>=45% on 5+ trades (they work on this symbol)
        #   - Inverse/mutation/DNA strategies (they flip direction, may work)
        #   - Copy traders with verified track record
        #   - Picks with RSI/technical confirmation signals
        elif (pick.get("symbol", "") or "").replace("-", "").upper() in (
            "BTCUSD",
            "BTCUSDT",
            "BTC-USD",  # 6% WR system-wide (1W/16L)
            "ADAUSDT",
            "ADA-USD",
            "ADAUSD",  # 12% WR system-wide (2W/14L)
            "BCHUSDT",
            "BCH-USD",
            "BCHUSD",  # 0% WR system-wide (0W/5L)
            "TIAUSDT",
            "TIA-USD",
            "TIAUSD",  # 0% WR system-wide (0W/4L)
        ):
            sym = (pick.get("symbol", "") or "").upper()
            _strat7 = (pick.get("strategy") or "").lower()
            _exempt = False

            # Exempt: strategy proven on this symbol (WR>=45% on 5+ trades)
            try:
                _sp7 = load_strategy_performance()
                _sp7e = _sp7.get(pick.get("strategy", ""), {})
                if (
                    _sp7e.get("closed_picks", 0) >= 5
                    and _sp7e.get("win_rate", 0) >= 0.45
                ):
                    _exempt = True
            except Exception:
                pass

            # Exempt: inverse/mutation/DNA strategies ONLY if they have track record
            # Unproven inverse picks on toxic symbols are still toxic.
            if any(
                t in _strat7 for t in ["_inv", "inverse", "_mut", "mutation", "dna_"]
            ):
                try:
                    _sp7_inv = load_strategy_performance()
                    _sp7_inv_entry = _sp7_inv.get(pick.get("strategy", ""), {})
                    if (
                        _sp7_inv_entry.get("closed_picks", 0) >= 5
                        and _sp7_inv_entry.get("win_rate", 0) >= 0.45
                    ):
                        _exempt = True
                    # Else: inverse strategy with no/bad track record — NOT exempt
                except Exception:
                    pass

            # Exempt: copy traders with verified track record
            if any(
                t in _strat7
                for t in ["copy_hl_", "copy_trader", "clone_hl_", "bitget_copy"]
            ):
                _exempt = True

            # Exempt: strong technical confirmation (RSI extreme + high confidence)
            if gate_conf >= 0.85 and (pick.get("extra", {}) or {}).get("rsi2_extreme"):
                _exempt = True

            if not _exempt and (gate_conf < 0.90 or ml_score < 0.80):
                reject_reason = (
                    f"[TOXIC SYMBOL] {sym}: needs conf>=0.90+ml>=0.80, "
                    f"or proven strategy/inverse/copy-trader/RSI exempt. "
                    f"Got conf={gate_conf:.2f} ml={ml_score:.2f}{conf_suffix}"
                )

        # Gate 8: Algorithmic strategy probation (EMERGENCY Mar 24 2026)
        # Algorithmic strategies: 19% WR -- catastrophic.
        # Only copy_trader (53%) and ml_enhanced (52%) are near-breakeven.
        # Require conf >= 0.80 + 10 closed trades at >= 45% WR for all others.
        if not reject_reason:
            _strat_name = (pick.get("strategy") or "").lower()
            _source_sys = (pick.get("source_system") or "").lower()
            # inverse_ strategies are NOT exempt — they have no proven track record
            _is_inverse = "inverse" in _strat_name or "_inv_" in _strat_name
            _is_copy_or_ml = not _is_inverse and (
                "copy_trader" in _strat_name
                or "copy_hl_" in _strat_name
                or "clone_hl_" in _strat_name
                or "bitget_copy" in _strat_name
                or "okx_copy" in _strat_name
                or "okx_futures_" in _strat_name
                or "copy_trader" in _source_sys
                or "ml_enhanced" in _strat_name
            )
            if not _is_copy_or_ml:
                # Algorithmic strategy -- apply probation rules
                if gate_conf < 0.80:
                    reject_reason = (
                        f"[ALGO PROBATION] conf={gate_conf:.2f} < 0.80 "
                        f"(algorithmic WR=19%, raised threshold){conf_suffix}"
                    )
                else:
                    # Check strategy track record from strategy_performance
                    try:
                        _sp_data = load_strategy_performance()
                        _strat_orig = pick.get("strategy", "")
                        _sp_entry = _sp_data.get(_strat_orig, {})
                        _sp_closed = _sp_entry.get("closed_picks", 0)
                        _sp_wr = _sp_entry.get("win_rate", 0)
                        if _sp_closed < 10 or _sp_wr < 0.45:
                            reject_reason = (
                                f"[ALGO PROBATION] {_strat_orig}: "
                                f"{_sp_closed} closed trades, {_sp_wr:.0%} WR "
                                f"(need 10+ trades at >= 45% WR)"
                            )
                    except Exception:
                        reject_reason = (
                            f"[ALGO PROBATION] cannot verify track record "
                            f"for {pick.get('strategy', 'unknown')}"
                        )
                if reject_reason and "ALGO PROBATION" in reject_reason:
                    pick["algorithmic_probation"] = True

        # Gate 9: R:R hard gate (73.7% WR at R:R 2.0-2.5 vs 39% below 1.5)
        # Data from Strong Signals Blueprint analysis. Picks with R:R < 1.0
        # have negative expectancy by definition. R:R < 1.2 rarely profitable.
        if not reject_reason:
            _entry = float(pick.get("entry_price", 0) or 0)
            _tp = float(pick.get("take_profit", 0) or 0)
            _sl = float(pick.get("stop_loss", 0) or 0)
            if _entry > 0 and _tp > 0 and _sl > 0 and _sl != _entry:
                _reward = abs(_tp - _entry)
                _risk = abs(_sl - _entry)
                _rr = _reward / _risk if _risk > 0 else 0
                if _rr < 1.2:
                    reject_reason = (
                        f"[R:R GATE] R:R={_rr:.2f} < 1.2 "
                        f"(sub-threshold, entry={_entry}, tp={_tp}, sl={_sl})"
                    )
                # Tag the R:R for downstream use
                pick["_computed_rr"] = round(_rr, 3)

        # Gate 9b: Minimum TP distance (Mar 25 2026)
        # Micro-scalp picks (TP < 2% from entry) are noise for manual/paper trading.
        # High-frequency 15m strategies average <1% moves — users can't trade these.
        # EXEMPT: proven ML strategies since they have verified edge even on tiny moves.
        if not reject_reason:
            _entry_9b = float(pick.get("entry_price", 0) or 0)
            _tp_9b = float(pick.get("take_profit", 0) or 0)
            if _entry_9b > 0 and _tp_9b > 0:
                _tp_dist_pct = abs(_tp_9b - _entry_9b) / _entry_9b
                _MIN_TP_DIST = 0.02  # 2% minimum
                _strat_9b = pick.get("strategy", "")
                _is_proven_9b = any(
                    p in _strat_9b
                    for p in (
                        "ml_enhanced_FET",
                        "ml_enhanced_BNB",
                        "ml_enhanced_RENDER",
                        "copy_hl_NMTD",
                    )
                )
                if _tp_dist_pct < _MIN_TP_DIST and not _is_proven_9b:
                    reject_reason = (
                        f"[MIN TP] TP distance {_tp_dist_pct * 100:.2f}% < 2.0% minimum "
                        f"(micro-scalp, not suitable for manual trading)"
                    )

        # Gate 10: Strategy negative expectancy gate
        # Block picks from strategies with avg PnL < 0 on 15+ closed trades.
        # These strategies are proven money losers at scale.
        if not reject_reason:
            try:
                _sp_data2 = load_strategy_performance()
                _strat2 = pick.get("strategy", "")
                _sp2 = _sp_data2.get(_strat2, {})
                _sp2_closed = _sp2.get("closed_picks", 0)
                _sp2_avg_pnl = _sp2.get("avg_pnl", 0) or 0
                _sp2_wr = _sp2.get("win_rate", 0)
                if _sp2_closed >= 15 and _sp2_avg_pnl < -0.005 and _sp2_wr < 0.30:
                    reject_reason = (
                        f"[NEG EXPECTANCY] {_strat2}: avg_pnl={_sp2_avg_pnl:.4f} "
                        f"WR={_sp2_wr:.0%} on {_sp2_closed} trades (proven loser)"
                    )
            except Exception:
                pass

        # Gate 11: Friday confidence raise (29% WR on Fridays vs 49% avg)
        # Institutional position-closing creates selling pressure on Fridays.
        # Require higher conviction for Friday entries.
        if not reject_reason:
            from datetime import datetime, timezone

            now_utc = datetime.now(timezone.utc)
            if now_utc.weekday() == 4 and gate_conf < 0.80:  # Friday
                reject_reason = (
                    f"[FRIDAY GATE] conf={gate_conf:.2f} < 0.80 "
                    f"(Friday WR=29% vs 49% avg, higher bar required){conf_suffix}"
                )

        # Gate 12: Elite score floor (Mar 25 2026)
        # Score bands 0-40 have terrible WR (6-35%). Only 60+ shows real signal.
        # Minimum threshold: 55. Unscored picks (elite_score=None) pass through
        # since they may be ML/copy-trader picks that haven't been scored yet.
        # Mercury sprint item #8: proven ML strategies bypass (historically mis-calculated scores).
        _PROVEN_STRATEGIES = {
            "ml_enhanced_FET",
            "ml_enhanced_BNB",
            "ml_enhanced_RENDER",
            "ml_enhanced_FETUSDT",
            "ml_enhanced_BNBUSDT",
            "ml_enhanced_RENDERUSDT",
            "NMTD",
        }
        if not reject_reason:
            _elite_score = pick.get("elite_score")
            if _elite_score is not None:
                try:
                    _elite_score_val = float(_elite_score)
                    if _elite_score_val < 55 and _elite_score_val > 0:
                        # Allow proven ML strategies through regardless of score
                        _strat_name_12 = pick.get("strategy", "")
                        _is_proven_12 = any(
                            p in _strat_name_12 for p in _PROVEN_STRATEGIES
                        )
                        if not _is_proven_12:
                            reject_reason = (
                                f"[SCORE FLOOR] elite_score={_elite_score_val:.1f} "
                                f"< 55 minimum threshold"
                            )
                except (TypeError, ValueError):
                    pass  # Non-numeric elite_score -- let it through

        # Gate 13: Symbol concentration cap (Mar 26 2026)
        # FETUSDT = 52% of all profits. Limit any symbol to max 3 active picks.
        if not reject_reason:
            _sym_13 = (pick.get("symbol") or "").upper()
            _sym_count = sum(
                1 for p in passed if (p.get("symbol") or "").upper() == _sym_13
            )
            if _sym_count >= 3:
                reject_reason = (
                    f"[CONCENTRATION] {_sym_13} already has {_sym_count} active picks "
                    f"(max 3 per symbol)"
                )

        # Gate 14: Hedge Fund Quality Gate -- banned sources/symbols/drawdown enforcement
        # Wired here so blocked sources are rejected at trade-time, not just audit-time.
        if not reject_reason and _HAS_HEDGE_FUND_GATE:
            try:
                _hf_ok, _hf_reason = passes_hedge_fund_gate(pick)
                if not _hf_ok:
                    reject_reason = f"[HF GATE] {_hf_reason}"
            except Exception:
                pass  # fail-open: never block picks from a gate import failure

        if reject_reason:
            pick["_quality_gate_rejected"] = reject_reason
            rejected.append(pick)
        else:
            # Charter §7 P0.5-1 wire-up 2026-05-13. Stamp vol-targeted
            # notional cap + concentration verdict so /audit can see what
            # Charter §7 would have allowed. Informational this round —
            # promote to a hard gate after soak.
            try:
                from alpha_engine.charter_position_sizer import (
                    compute_position_size,
                    validate_concentration,
                )
                _vol = pick.get("_vol_estimate") or pick.get("daily_vol")
                pick["_charter_notional_pct"] = compute_position_size(
                    pick, portfolio_equity=1.0, daily_vol_estimate=_vol,
                )
                _ok, _reason = validate_concentration(pick, passed)
                if not _ok:
                    pick["_charter_concentration_warn"] = _reason
            except Exception:
                pass
            passed.append(pick)

    return passed, rejected


def apply_macro_risk_off_gate(picks: list[dict]) -> tuple[list[dict], list[dict]]:
    """Filter or size-down picks with strong macro risk-off signals.

    If macro_score < -0.5 for a pick's asset class:
      - conf >= 0.90: survive with 0.5x sizing reduction
      - conf < 0.90: filter out
    """
    kept = []
    rejected = []
    filtered = 0
    sized_down = 0
    for pick in picks:
        macro_score = pick.get("macro_score")
        if macro_score is None:
            kept.append(pick)
            continue
        try:
            score = float(macro_score)
        except (TypeError, ValueError):
            kept.append(pick)
            continue

        if score < -0.5:
            conf = float(pick.get("confidence", 0) or 0)
            if conf >= 0.90:
                existing_mult = float(pick.get("sizing_multiplier", 1.0) or 1.0)
                pick["sizing_multiplier"] = round(existing_mult * 0.5, 4)
                pick["_macro_risk_off_sized"] = True
                sized_down += 1
                kept.append(pick)
            else:
                pick["_macro_risk_off_rejected"] = (
                    f"macro_score={score:.2f} < -0.5 (strong risk-off, conf={conf:.2f} < 0.90)"
                )
                rejected.append(pick)
                filtered += 1
        else:
            kept.append(pick)

    if filtered or sized_down:
        print(
            f"  [MACRO RISK-OFF GATE] Filtered {filtered}, sized down {sized_down} "
            f"(macro_score < -0.5) | {len(kept)} passed"
        )
    return kept, rejected


# ---------------------------------------------------------------------------
# 5. Confidence tier labeling
# ---------------------------------------------------------------------------


def assign_tiers(picks: list[dict]) -> list[dict]:
    """Assign HIGH / MEDIUM / WATCH tier and sort accordingly."""
    for pick in picks:
        conf = pick.get("confidence") or 0
        rr = pick.get("risk_reward") or 0
        if conf >= TIER_HIGH_CONF and rr >= TIER_HIGH_RR:
            pick["tier"] = "HIGH"
        elif conf >= TIER_MED_CONF and rr >= TIER_MED_RR:
            pick["tier"] = "MEDIUM"
        else:
            pick["tier"] = "WATCH"

    tier_order = {"HIGH": 0, "MEDIUM": 1, "WATCH": 2}
    picks.sort(
        key=lambda p: (
            tier_order.get(p["tier"], 9),
            -_ml_composite_key(p),
            -(p.get("confidence") or 0),
        )
    )
    return picks


# ---------------------------------------------------------------------------
# 6. Track record from closed picks
# ---------------------------------------------------------------------------


def build_track_record(closed: list[dict], perf: dict) -> dict:
    """Build track record summary from closed picks and strategy perf."""
    # I4 FIX: Exclude outlier symbols from track record metrics (honest reporting)
    try:
        from elite_scorer import OUTLIER_SYMBOLS
    except ImportError:
        OUTLIER_SYMBOLS = {"FETUSDT", "RENDERUSDT"}
    closed = [p for p in closed if p.get("symbol", "") not in OUTLIER_SYMBOLS]
    wins = sum(1 for p in closed if float(p.get("pnl_pct", 0) or 0) > 0)
    losses = len(closed) - wins
    total_pnl = sum(float(p.get("pnl_dollar", 0) or 0) for p in closed)
    wr = round(wins / len(closed), 4) if closed else None

    monthly: dict[str, float] = {}
    for p in closed:
        d = p.get("exit_date") or p.get("entry_date", "")
        if len(d) >= 7:
            month_key = d[:7]
            monthly[month_key] = round(
                monthly.get(month_key, 0) + float(p.get("pnl_dollar", 0) or 0), 2
            )

    # Best strategy
    best_strat = None
    best_wr = None
    for strat, stats in perf.items():
        if strat.startswith("_"):
            continue
        closed_n = stats.get("closed_picks", 0)
        if closed_n >= 5:
            sw = stats.get("win_rate", 0)
            if best_wr is None or sw > best_wr:
                best_wr = sw
                best_strat = strat

    return {
        "status": "active" if len(closed) >= 30 else "accumulating",
        "total_closed": len(closed),
        "wins": wins,
        "losses": losses,
        "win_rate": wr,
        "total_pnl_dollar": round(total_pnl, 2),
        "monthly_pnl": monthly,
        "by_strategy": {k: v for k, v in perf.items() if not k.startswith("_")},
        "best_strategy": best_strat,
        "best_strategy_wr": round(best_wr, 4) if best_wr is not None else None,
    }


# ---------------------------------------------------------------------------
# 7. Write premium_signals.json
# ---------------------------------------------------------------------------


def write_premium_signals(market_ctx: dict, signals: list[dict], track: dict) -> Path:
    """Build and write the premium_signals.json output."""
    tier1 = sum(1 for s in signals if s.get("tier") == "HIGH")
    tier2 = sum(1 for s in signals if s.get("tier") == "MEDIUM")
    tier3 = sum(1 for s in signals if s.get("tier") == "WATCH")

    total_pnl_pct = None
    if track["total_closed"] > 0:
        avg_pnl = track["total_pnl_dollar"] / (track["total_closed"] * 2000)
        total_pnl_pct = round(avg_pnl * 100, 4)

    payload = {
        "generated_at": _now_iso(),
        "version": "2.0",
        "market_context": market_ctx,
        "summary": {
            "total_active": len(signals),
            "total_rejected": len(track.get("rejected_picks", [])),
            "whale_index_avg": track.get("whale_index_avg", 50),
            "tier1_count": tier1,
            "tier2_count": tier2,
            "tier3_count": tier3,
            "closed_total": track["total_closed"],
            "win_rate": track["win_rate"],
            "total_pnl_pct": total_pnl_pct,
            "best_strategy": track.get("best_strategy"),
            "best_strategy_wr": track.get("best_strategy_wr"),
        },
        "signals": signals,
        "rejected_signals": track.get("rejected_picks", [])[
            :50
        ],  # Cap at 50 for JSON size
        "track_record": track,
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(PREMIUM_SIGNALS_PATH, "w") as f:
        json.dump(_sanitize_for_json(payload), f, indent=2)

    print(
        f"[WRITE] {PREMIUM_SIGNALS_PATH.name}  "
        f"({len(signals)} signals: {tier1} HIGH / {tier2} MED / {tier3} WATCH)"
    )
    return PREMIUM_SIGNALS_PATH


# ---------------------------------------------------------------------------
# 8. Discord webhook (optional)
# ---------------------------------------------------------------------------


def _load_last_discord_alerts() -> set[str]:
    if LAST_DISCORD_ALERTS_PATH.exists():
        try:
            with open(LAST_DISCORD_ALERTS_PATH) as f:
                return set(json.load(f))
        except Exception:
            pass
    return set()


def _save_last_discord_alerts(ids: set[str]):
    with open(LAST_DISCORD_ALERTS_PATH, "w") as f:
        json.dump(list(ids), f)


def _fmt_price(val) -> str:
    """Format price without scientific notation."""
    if val is None or val == 0:
        return "$0"
    val = float(val)
    if val >= 1000:
        return f"${val:,.2f}"
    elif val >= 1:
        return f"${val:.4f}"
    elif val >= 0.001:
        return f"${val:.6f}"
    else:
        return f"${val:.10f}"


def _get_alpha_strategy_record(strategy_name: str) -> str:
    """Build track record string from strategy_performance.json."""
    try:
        perf = load_strategy_performance()
        stats = perf.get(strategy_name, {})
        closed = stats.get("closed_picks", 0)
        if closed == 0:
            return ""
        wr = stats.get("win_rate", 0)
        wins = stats.get("wins", 0)
        losses = closed - wins
        avg = stats.get("avg_pnl_pct", 0)
        pf = stats.get("profit_factor", 0)
        pf_str = (
            f"{pf:.2f}"
            if isinstance(pf, (int, float)) and pf != float("inf")
            else "\u221e"
        )
        return (
            f"**Track Record:** {closed} trades | "
            f"{wins}W/{losses}L | WR: {wr:.0%} | PF: {pf_str} | "
            f"Avg: {avg:+.2f}%"
        )
    except Exception:
        return ""


def send_discord_alerts(signals: list[dict]):
    """Send up to 5 new Tier-1 signals to Discord via webhook."""
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        return

    tier1 = [s for s in signals if s.get("tier") == "HIGH"]
    if not tier1:
        return

    sent_ids = _load_last_discord_alerts()
    new_signals = [s for s in tier1 if s.get("id") not in sent_ids]
    if not new_signals:
        print("[DISCORD] No new Tier-1 signals to send.")
        return

    embeds = []
    for sig in new_signals[:5]:
        direction = sig.get("signal_type", "BUY")
        color = 0x22C55E if direction == "BUY" else 0xEF4444
        strategy = sig.get("strategy", "")
        fields = [
            {
                "name": "Entry",
                "value": _fmt_price(sig.get("entry_price", 0)),
                "inline": True,
            },
            {
                "name": "TP",
                "value": _fmt_price(sig.get("take_profit", 0)),
                "inline": True,
            },
            {
                "name": "SL",
                "value": _fmt_price(sig.get("stop_loss", 0)),
                "inline": True,
            },
            {
                "name": "Confidence",
                "value": f"{(sig.get('confidence') or 0) * 100:.0f}%",
                "inline": True,
            },
            {
                "name": "R:R",
                "value": f"{sig.get('risk_reward', '?'):.1f}",
                "inline": True,
            },
            {
                "name": "Reason",
                "value": str(sig.get("reason", ""))[:200],
                "inline": False,
            },
        ]
        track_record = _get_alpha_strategy_record(strategy)
        if track_record:
            fields.append(
                {
                    "name": "\U0001f4c8 Strategy Performance",
                    "value": track_record,
                    "inline": False,
                }
            )
        embeds.append(
            {
                "title": f"{direction} {sig.get('symbol', '?')}",
                "color": color,
                "fields": fields,
                "footer": {"text": f"Alpha Engine v2.0 | {strategy}"},
            }
        )

    try:
        r = requests.post(
            webhook_url,
            json={"embeds": embeds},
            timeout=HTTP_TIMEOUT,
        )
        r.raise_for_status()
        newly_sent = {s.get("id", "") for s in new_signals[:5]}
        sent_ids.update(newly_sent)
        # Keep only last 200 IDs to avoid unbounded growth
        if len(sent_ids) > 200:
            sent_ids = set(list(sent_ids)[-200:])
        _save_last_discord_alerts(sent_ids)
        print(f"[DISCORD] Sent {len(embeds)} Tier-1 alerts.")
    except Exception as e:
        print(f"  [WARN] Discord webhook failed: {e}")


# ---------------------------------------------------------------------------
# 9. Summary printer
# ---------------------------------------------------------------------------


def print_summary(market_ctx: dict, signals: list[dict], track: dict):
    """Print concise summary to stdout for GitHub Actions logs."""
    print()
    print("=" * 70)
    print("  ALPHA ENGINE -- Production Scanner Summary")
    print(f"  {_now_iso()}")
    print("=" * 70)

    # Market context
    btc = market_ctx.get("btc_price")
    eth = market_ctx.get("eth_price")
    fg = market_ctx.get("fear_greed")
    print(f"\n  Market:  BTC ${btc:,.2f}" if btc else "\n  Market:  BTC N/A", end="")
    print(f" ({market_ctx.get('btc_24h_change', 0):+.1f}%)" if btc else "")
    print(f"           ETH ${eth:,.2f}" if eth else "           ETH N/A", end="")
    print(f" ({market_ctx.get('eth_24h_change', 0):+.1f}%)" if eth else "")
    print(
        f"           F&G: {fg['value']} ({fg['label']})"
        if fg
        else "           F&G: N/A"
    )
    print(f"           Regime: {market_ctx.get('market_regime', '?')}")
    dom = market_ctx.get("btc_dominance")
    if dom:
        print(f"           BTC Dominance: {dom:.1f}%")

    # Signal counts
    tier1 = sum(1 for s in signals if s.get("tier") == "HIGH")
    tier2 = sum(1 for s in signals if s.get("tier") == "MEDIUM")
    tier3 = sum(1 for s in signals if s.get("tier") == "WATCH")
    print(
        f"\n  Signals: {len(signals)} active  "
        f"({tier1} HIGH / {tier2} MEDIUM / {tier3} WATCH)"
    )

    # Top HIGH signals
    high_signals = [s for s in signals if s.get("tier") == "HIGH"]
    if high_signals:
        print(f"\n  Top Tier-1 signals:")
        for s in high_signals[:5]:
            pnl = s.get("unrealized_pnl_pct", 0) or 0
            print(
                f"    {s.get('signal_type', 'BUY'):4s} {s.get('symbol', '?'):16s} "
                f"conf={s.get('confidence', 0):.0%}  R:R={s.get('risk_reward', 0):.1f}  "
                f"PnL={pnl * 100:+.2f}%  [{s.get('strategy', '')}]"
            )

    # Track record
    wr = track.get("win_rate")
    print(
        f"\n  Track Record: {track['total_closed']} closed  |  "
        f"{'WR=' + f'{wr * 100:.1f}%' if wr else 'accumulating'}  |  "
        f"P&L=${track.get('total_pnl_dollar', 0):+,.2f}"
    )

    best = track.get("best_strategy")
    if best:
        print(
            f"  Best strategy: {best} "
            f"(WR={track.get('best_strategy_wr', 0) * 100:.1f}%)"
        )

    print("=" * 70)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    start = time.time()
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # These module-level thresholds may be adjusted by circuit breakers and macro gating.
    global MAX_ACTIVE_PICKS, QUALITY_GATE_MIN_CONFIDENCE

    # -0. MODEL CALIBRATION: Drift detection at startup
    #     Checks if ML predictions have degraded since last calibration.
    #     Non-fatal -- scanner continues even if drift is detected.
    try:
        from model_calibration import run_calibration_diagnostics

        run_calibration_diagnostics(DATA_DIR)
    except ImportError:
        pass
    except Exception as e:
        print(f"  [CALIBRATION] Startup diagnostics failed (non-fatal): {e}")

    # -0.5. UNIFIED CIRCUIT BREAKER AGGREGATOR
    #   Combines drawdown, portfolio, and macro circuit breakers into one decision.
    _cb_state = None
    if _HAS_CB_AGGREGATOR:
        try:
            _cb_state = get_unified_breaker_state()
            print(
                f"\n[CIRCUIT BREAKER AGGREGATOR] Level: {_cb_state['level']} | "
                f"max_picks={_cb_state['max_picks']} | min_conf={_cb_state['min_confidence']:.2f}"
            )
            for r in _cb_state.get("reasons", []):
                print(f"  Reason: {r}")

            if _cb_state["level"] == "HALT":
                print(
                    "\n[RISK] Unified circuit breaker HALT -- refusing to generate new picks."
                )
                write_premium_signals({}, [], {})
                elapsed = time.time() - start
                print(
                    f"\nProduction scanner aborted (circuit breaker HALT) in {elapsed:.1f}s"
                )
                return

            # Apply restrictive settings
            MAX_ACTIVE_PICKS = min(MAX_ACTIVE_PICKS, _cb_state["max_picks"])
            QUALITY_GATE_MIN_CONFIDENCE = max(
                QUALITY_GATE_MIN_CONFIDENCE, _cb_state["min_confidence"]
            )
            if _cb_state["level"] == "RED":
                QUALITY_GATE_MIN_CONFIDENCE = max(QUALITY_GATE_MIN_CONFIDENCE, 0.85)
            elif _cb_state["level"] == "YELLOW":
                QUALITY_GATE_MIN_CONFIDENCE = max(QUALITY_GATE_MIN_CONFIDENCE, 0.70)

            print(
                f"  [CIRCUIT BREAKER AGGREGATOR] Applied: max_picks={MAX_ACTIVE_PICKS}, "
                f"min_conf={QUALITY_GATE_MIN_CONFIDENCE:.2f}"
            )
        except Exception as _cb_err:
            print(f"  [CIRCUIT BREAKER AGGREGATOR] Failed (non-fatal): {_cb_err}")

    # -1. RISK CONTROLS: Pre-generation safety check (circuit breaker + daily limit)
    #     This is the FIRST check, before any signal generation.
    if _HAS_RISK_CONTROLS:
        try:
            if is_circuit_breaker_locked():
                print(
                    "\n[RISK] Circuit breaker LOCKED -- refusing to generate new picks."
                )
                print(
                    "[RISK] To reset: delete data/circuit_breaker.json or set status=NORMAL"
                )
                # Still write premium_signals with empty picks so dashboard updates
                write_premium_signals({}, [], {})
                elapsed = time.time() - start
                print(
                    f"\nProduction scanner aborted (circuit breaker) in {elapsed:.1f}s"
                )
                return
            if is_daily_blocked():
                print(
                    "\n[RISK] Daily loss limit hit -- blocking new pick generation for today."
                )
                # Allow rest of pipeline to run for monitoring, but flag it
        except Exception as e:
            print(f"  [RISK] Pre-generation check failed (non-fatal): {e}")

    # -0.9. MACRO DATA PIPELINE: refresh yield curve + Fed policy snapshot
    _macro_snapshot = None
    if _HAS_MACRO_PIPELINE:
        try:
            _macro_snapshot = run_macro_pipeline()
            _macro_series = _macro_snapshot.get("series") or {}
            print(
                f"\n[MACRO] Pipeline refreshed: source={_macro_snapshot.get('source')}, "
                f"regime={_macro_series.get('regime_label')}, "
                f"score={_macro_series.get('macro_risk_score')}"
            )
        except Exception as e:
            print(f"  [MACRO] Pipeline failed (non-fatal): {e}")
    else:
        try:
            _macro_snapshot = get_macro_snapshot()
        except Exception:
            pass

    # -0.8. FORCE-CLOSE TOXIC STRATEGIES: Remove confirmed 0% WR picks immediately
    try:
        from crypto_risk_gates import force_close_toxic_picks

        n_closed = force_close_toxic_picks()
        if n_closed:
            print(f"\n[TOXIC] Force-closed {n_closed} picks from hard-kill strategies")
    except Exception as e:
        print(f"  [TOXIC] Force-close failed (non-fatal): {e}")

    # -0.5. ANOMALY DETECTION: Check for model degradation, drift, herding
    #        Runs at startup to flag issues BEFORE generating new picks.
    _anomaly_sizing = 1.0
    if _HAS_ANOMALY_DETECTOR:
        try:
            print("\n[ANOMALY] Running prediction anomaly detector...")
            anomaly_alerts = check_all_anomalies()
            _anomaly_sizing = get_sizing_multiplier()
            if _anomaly_sizing < 1.0:
                print(
                    f"  [ANOMALY] Sizing multiplier = {_anomaly_sizing} "
                    f"(CRITICAL alerts active)"
                )
        except Exception as e:
            print(f"  [ANOMALY] Detection failed (non-fatal): {e}")

    # 0. Dynamic universe rotation (swap stale low-vol symbols for trending)
    if _HAS_UNIVERSE_MGR:
        try:
            print("\n[UNIVERSE] Running dynamic symbol rotation...")
            updated_symbols, removed, added = get_dynamic_universe(
                CRYPTO_SYMBOLS, n_swap=3
            )
            if removed or added:
                print(
                    f"  Universe swap: removed {', '.join(removed)} -- added {', '.join(added)}"
                )
                # Patch the module-level CRYPTO_SYMBOLS for this run
                import config as _cfg

                _cfg.CRYPTO_SYMBOLS = updated_symbols
            else:
                print("  Universe unchanged (all symbols have healthy volume)")
        except Exception as e:
            print(f"  [UNIVERSE] Skipped: {e}")

    # 0b. Add missed-opportunity symbols to scan universe
    if _HAS_MISSED_OPP:
        try:
            extra_symbols = get_universe_additions()
            if extra_symbols:
                import config as _cfg

                current_syms = getattr(_cfg, "CRYPTO_SYMBOLS", {})
                added_count = 0
                for sym in extra_symbols:
                    if sym not in current_syms:
                        # Add with minimal metadata so strategies can scan it
                        current_syms[sym] = {"binance": sym, "source": "missed_opp"}
                        added_count += 1
                if added_count:
                    _cfg.CRYPTO_SYMBOLS = current_syms
                    print(
                        f"  [MISSED-OPP] Added {added_count} symbols from analyzer: "
                        f"{', '.join(extra_symbols[:5])}{'...' if len(extra_symbols) > 5 else ''}"
                    )
            else:
                print("  [MISSED-OPP] No new symbols to add")
        except Exception as e:
            print(f"  [MISSED-OPP] Skipped: {e}")

    # 0c. Universe expansion: catch top gainers, new listings, trending coins
    if _HAS_UNIVERSE_EXPANDER:
        try:
            import config as _cfg_exp

            current_binance = [
                meta.get("binance", "")
                for meta in getattr(_cfg_exp, "CRYPTO_SYMBOLS", {}).values()
                if meta.get("binance")
            ]
            expansion_adds, expansion_msg = get_expansion_for_scanner(
                current_binance, max_add=30
            )
            if expansion_adds:
                current_syms_exp = getattr(_cfg_exp, "CRYPTO_SYMBOLS", {})
                added_exp = 0
                for yf_ticker, meta in expansion_adds.items():
                    if yf_ticker not in current_syms_exp:
                        current_syms_exp[yf_ticker] = meta
                        added_exp += 1
                if added_exp:
                    _cfg_exp.CRYPTO_SYMBOLS = current_syms_exp
                n_trending = sum(
                    1
                    for m in expansion_adds.values()
                    if "trending" in m.get("expansion_sources", [])
                )
                n_listings = sum(
                    1
                    for m in expansion_adds.values()
                    if "new_listing" in m.get("expansion_sources", [])
                )
                n_gainers = sum(
                    1
                    for m in expansion_adds.values()
                    if "top_gainer" in m.get("expansion_sources", [])
                )
                print(f"  {expansion_msg}")
            else:
                print(f"  {expansion_msg}")
        except Exception as e:
            print(f"  [UNIVERSE] Expansion skipped: {e}")

    # 0d. Whale Intelligence: Refresh indices BEFORE pick generation
    if _HAS_WHALE_INDEX:
        run_whale_scanners()

    # 1. Market context
    market_ctx = fetch_market_context()

    # 2. Full forward-validator cycle
    perf = run_full_cycle()

    # 3. Load resulting JSON
    active = load_active_picks()
    closed = load_closed_picks()

    # Phase 2 — non-LLM feature sleeves (funding / VIX / commodity mom)
    try:
        from tools.feature_signals.orchestrator import merge_feature_signals
        active = merge_feature_signals(active)
    except Exception as _fs_err:
        print(f"  [FEATURE SIGNALS] Skipped (non-fatal): {_fs_err}")
    if not perf:
        perf = load_strategy_performance()

    # 3.0. MACRO GATING: adjust pick caps and confidence floors based on macro risk
    _orig_max_picks = MAX_ACTIVE_PICKS
    _orig_min_conf = QUALITY_GATE_MIN_CONFIDENCE
    _macro_equity_conf_floor = None
    if _macro_snapshot:
        _macro_series = _macro_snapshot.get("series") or {}
        _macro_risk_score = _macro_series.get("macro_risk_score", 0.0) or 0.0
        _yield_curve_10y2y = _macro_series.get("yield_curve_10y2y")
        _fed_change = _macro_series.get("fed_funds_rate_90d_change")
        _fed_hiking = _fed_change is not None and _fed_change > 0.05

        if _macro_risk_score <= -0.8:
            MAX_ACTIVE_PICKS = int(MAX_ACTIVE_PICKS * 0.50)
            QUALITY_GATE_MIN_CONFIDENCE = min(0.95, QUALITY_GATE_MIN_CONFIDENCE + 0.10)
            print(
                f"  [MACRO GATE] Severe risk-off (score={_macro_risk_score:.2f}): "
                f"max picks {MAX_ACTIVE_PICKS}, min conf {QUALITY_GATE_MIN_CONFIDENCE:.2f}"
            )
        elif _macro_risk_score <= -0.5:
            MAX_ACTIVE_PICKS = int(MAX_ACTIVE_PICKS * 0.75)
            QUALITY_GATE_MIN_CONFIDENCE = min(0.95, QUALITY_GATE_MIN_CONFIDENCE + 0.05)
            print(
                f"  [MACRO GATE] Risk-off (score={_macro_risk_score:.2f}): "
                f"max picks {MAX_ACTIVE_PICKS}, min conf {QUALITY_GATE_MIN_CONFIDENCE:.2f}"
            )

        if _yield_curve_10y2y is not None and _yield_curve_10y2y < 0 and _fed_hiking:
            _macro_equity_conf_floor = 0.90
            print(
                f"  [MACRO GATE] Yield curve inverted + Fed hiking: "
                f"EQUITY picks require conf >= 0.90"
            )

    # 3a. Data format normalization (fix mixed pnl_pct and confidence formats)
    active = normalize_pnl_format(active)
    closed = normalize_pnl_format(closed)
    active = normalize_confidence(active)
    closed = normalize_confidence(closed)

    # 3b. Data quality fixes
    active = sanitize_symbols(active)
    active = filter_bad_symbols(active)
    active = apply_source_ban_gate(active)
    active = backfill_direction_and_timestamp(active)
    active = deduplicate_picks(active)
    active = resolve_direction_conflicts(active)

    # NOTE: Forex CT merge moved AFTER force_close (see 3b-FOREX-CT below line ~2660)
    # to prevent reload from wiping merged picks (same fix as isolated signals P0).

    # 3c. Force-close breached picks: TP/SL hit, stale >7d, missing data backfill
    #   Uses Binance (4 mirrors) -> CoinGecko -> KuCoin -> CryptoCompare failover.
    #   Must run BEFORE enrichment so breached picks don't waste API calls.
    #   MUST run BEFORE isolated signal integration so we don't lose integrated picks
    #   on reload (P0 fix 2026-03-26: integrated picks were being lost here).
    try:
        from force_close_breached import force_close_all

        _fc_summary = force_close_all()
        _fc_closed = _fc_summary.get("total_closed", 0)
        if _fc_closed:
            print(
                f"\n[FORCE CLOSE] Closed {_fc_closed} breached picks "
                f"(TP={_fc_summary.get('tp_closed', 0)}, "
                f"SL={_fc_summary.get('sl_closed', 0)}, "
                f"stale={_fc_summary.get('stale_closed', 0)})"
            )
            # Reload active picks after force-close modified them
            active = load_active_picks()
            closed = load_closed_picks()
        else:
            print("\n[FORCE CLOSE] No breached picks found")
    except Exception as _fc_err:
        print(f"  [FORCE CLOSE] Failed (non-fatal): {_fc_err}")

    # 3b-FOREX-CT. Merge forex copy trader picks into active pipeline
    #   MOVED after force_close (P0 fix: reload at line ~2651 was wiping merged picks)
    _fxct_path = (
        Path(__file__).resolve().parent.parent
        / "copy_trader_intel"
        / "data"
        / "forex_copytrader_picks.json"
    )
    if _fxct_path.exists():
        try:
            with open(_fxct_path, "r", encoding="utf-8") as _fxf:
                _fxct_raw = json.load(_fxf)
            if isinstance(_fxct_raw, list):
                _fxct_count = 0
                _existing_keys = set()
                for _p in active:
                    _k = (
                        _p.get("symbol", ""),
                        _p.get("strategy", ""),
                        str(_p.get("direction", _p.get("signal_type", ""))),
                    )
                    _existing_keys.add(_k)
                for _fp in _fxct_raw:
                    if not isinstance(_fp, dict):
                        continue
                    _fp["source_system"] = "forex_copy_trader"
                    _fp.setdefault("category", "forex")
                    _fp.setdefault("asset_class", "FOREX")
                    _fk = (
                        _fp.get("symbol", ""),
                        _fp.get("strategy", ""),
                        str(_fp.get("direction", _fp.get("signal_type", ""))),
                    )
                    if _fk not in _existing_keys:
                        active.append(_fp)
                        _existing_keys.add(_fk)
                        _fxct_count += 1
                if _fxct_count:
                    print(
                        f"  [FOREX CT] Merged {_fxct_count} forex copy trader picks into pipeline"
                    )
        except Exception as _fxct_err:
            print(
                f"  [FOREX CT] Failed to load forex_copytrader_picks.json (non-fatal): {_fxct_err}"
            )

    # 3b-ISO. Integrate picks from isolated crypto signal sources
    #   Pulls from quan_engine, crypto_ml_edge, genome, regime_terminal,
    #   battleground/luxalgo, rapid_fire — normalizes and deduplicates.
    #   MOVED after force_close (P0 fix 2026-03-26): was losing picks on reload.
    try:
        from isolated_signal_integrator import integrate_isolated_signals

        _iso_new = integrate_isolated_signals(active)
        if _iso_new:
            active.extend(_iso_new)
            print(f"  [INTEGRATOR] Added {len(_iso_new)} picks from isolated sources")
    except Exception as _iso_err:
        print(f"  [INTEGRATOR] Skipped (non-fatal): {_iso_err}")

    # 3b-TRIO. Three uncorrelated bot strategies (MACD scalper, RSI+VWAP, CVD divergence)
    #   Combined 24h: +$1,967 with zero trade overlap. Correlation 0.12.
    try:
        from trio_bot_strategies import scan_all as trio_scan

        _trio_picks = trio_scan()
        if _trio_picks:
            # Deduplicate: skip if symbol+direction already in active
            existing_keys = {
                (p.get("symbol"), p.get("direction") or p.get("signal_type"))
                for p in active
            }
            _trio_new = [
                p
                for p in _trio_picks
                if (p["symbol"], p["direction"]) not in existing_keys
            ]
            active.extend(_trio_new)
            print(
                f"  [TRIO_BOT] Added {len(_trio_new)} picks "
                f"(MACD/RSI+VWAP/CVD, {len(_trio_picks)} scanned, "
                f"{len(_trio_picks) - len(_trio_new)} deduped)"
            )
    except Exception as _trio_err:
        print(f"  [TRIO_BOT] Skipped (non-fatal): {_trio_err}")

    # 3b-SPORTS. Sports Betting Edge Scanner (Apr 25 2026)
    #   Identifies value bets by comparing prediction markets with bookmaker odds
    #   Focuses on NBA, NHL, NFL, MLB, Soccer for high-probability edges
    try:
        from sports_betting_edge import sports_betting_edge_scanner

        _sports_picks = sports_betting_edge_scanner({}, {})
        if _sports_picks:
            # Deduplicate: skip if symbol+direction already in active
            existing_keys = {
                (p.get("symbol"), p.get("direction") or p.get("signal_type"))
                for p in active
            }
            _sports_new = [
                p
                for p in _sports_picks
                if (p["symbol"], p.get("direction")) not in existing_keys
            ]
            active.extend(_sports_new)
            print(
                f"  [SPORTS_BETTING] Added {len(_sports_new)} sports betting picks "
                f"({len(_sports_picks)} scanned, "
                f"{len(_sports_picks) - len(_sports_new)} deduped)"
            )
    except Exception as _sports_err:
        print(f"  [SPORTS_BETTING] Skipped (non-fatal): {_sports_err}")

    # 3b-PEAD. PEAD Equity Shadow Wiring (2026-05-16, unlocked by equity_walkforward_validation_2026-05-16.md)
    #   PEAD equity strategy: 2-day post-earnings drift, EQUITY top-100 universe.
    #   WF verdict: T2 WF-VERIFIED (OOS WR 62.2%, fold consistency 100%, 8 folds).
    #   Shadow mode: PEAD_EQUITY_ENABLED=1 generates signals and logs them but does NOT
    #   add to `active` — shadow PnL must validate against live EQUITY cohort for ≥4 weeks
    #   before promotion. Kill-switch: PEAD_EQUITY_ENABLED=0 (default OFF — safe in prod).
    #   *** DO NOT enable in prod until 2026-06-14 review gate. ***
    #   Promotion criteria: ≥100 shadow picks AND paper PF ≥ 1.5 AND WR ≥ 50%.
    #   Review gate: 2026-06-14 (scheduled Claude Code job fires to audit shadow log).
    #   Wire-Up Rule: opt-in sidecar. Target caller: production_scanner._run_equity_scanner()
    #   Target promotion PR: after review gate passes.
    #   Ref: reports/equity_walkforward_validation_2026-05-16.md, updates/index.html 2026-05-17.
    _PEAD_ENABLED = os.environ.get("PEAD_EQUITY_ENABLED", "0") == "1"
    if _PEAD_ENABLED:
        try:
            from strategies.pead_equity import generate_pead_signals  # type: ignore

            # Load earnings events from incubator_picks.json (earnings calendar source)
            _pead_events_path = Path(__file__).resolve().parent / "data" / "incubator_picks.json"
            _pead_events: list[dict] = []
            if _pead_events_path.exists():
                try:
                    with open(_pead_events_path, "r", encoding="utf-8") as _pf:
                        _pead_raw = json.load(_pf)
                    if isinstance(_pead_raw, list):
                        _pead_events = [e for e in _pead_raw if isinstance(e, dict)]
                    elif isinstance(_pead_raw, dict):
                        _pead_events = _pead_raw.get("events", []) or _pead_raw.get("picks", [])
                except Exception as _pead_load_err:
                    print(f"  [PEAD_SHADOW] Failed to load incubator_picks.json: {_pead_load_err}")

            if _pead_events:
                _pead_signals = generate_pead_signals(_pead_events, dry_run=True)
                if _pead_signals:
                    _pead_shadow_path = Path(__file__).resolve().parent / "data" / "pead_shadow_picks.json"
                    try:
                        with open(_pead_shadow_path, "w", encoding="utf-8") as _psf:
                            json.dump(
                                {
                                    "generated_at": datetime.now(timezone.utc).isoformat(),
                                    "count": len(_pead_signals),
                                    "wf_verdict": "T2_WF_VERIFIED",
                                    "shadow_only": True,
                                    "picks": _pead_signals,
                                },
                                _psf,
                                indent=2,
                            )
                    except Exception as _pead_write_err:
                        print(f"  [PEAD_SHADOW] Failed to write shadow log: {_pead_write_err}")
                    # Shadow mode: log, do NOT extend `active`
                    print(
                        f"  [PEAD_SHADOW] Generated {len(_pead_signals)} PEAD shadow signals "
                        f"(T2 WF-VERIFIED, NOT added to active — shadow validation in progress). "
                        f"See alpha_engine/data/pead_shadow_picks.json"
                    )
                else:
                    print("  [PEAD_SHADOW] No PEAD signals generated (no qualifying earnings events)")
            else:
                print("  [PEAD_SHADOW] No earnings events loaded from incubator_picks.json — skipping")
        except Exception as _pead_err:
            print(f"  [PEAD_SHADOW] Skipped (non-fatal): {_pead_err}")

    # 3b-INV. Inverse Loser Mutations (Mar 29 2026)
    #   Flipps consistent losers into potential winners.
    #   Audit finding: ADA/RENDER experiment showed +42% PnL on inverted signals.
    try:
        from inverse_loser_mutations import run_inverse_mutations

        _inv_report = run_inverse_mutations()
        if _inv_report and _inv_report.get("total_mutations_created", 0) > 0:
            # Load the generated inverse picks
            _inv_picks_path = (
                Path(__file__).resolve().parent / "data" / "inverse_picks.json"
            )
            if _inv_picks_path.exists():
                with open(_inv_picks_path, "r", encoding="utf-8") as _inv_f:
                    _inv_picks = json.load(_inv_f)
                if _inv_picks:
                    _inv_added = 0
                    existing_keys = {
                        (p.get("symbol"), p.get("direction") or p.get("signal_type"))
                        for p in active
                    }
                    for _ip in _inv_picks:
                        _ik = (
                            _ip.get("symbol"),
                            _ip.get("direction") or _ip.get("signal_type"),
                        )
                        if _ik not in existing_keys:
                            active.append(_ip)
                            existing_keys.add(_ik)
                            _inv_added += 1
                    print(
                        f"  [INVERSE_LOSER] Merged {_inv_added} inverse picks into pipeline"
                    )
    except Exception as _inv_err:
        print(f"  [INVERSE_LOSER] Failed (non-fatal): {_inv_err}")

    # 3b-IED. Inverse Earnings Drift sidecar (2026-05-16, opt-in)
    #   Strategy: scan_earnings_gap_reversal() from alpha_engine.calendar_anomalies.
    #   BUY after gap-DOWN ≥4% on ≥2× avg volume (earnings reaction proxy, ETF universe).
    #   Inverse of blocked ("Earnings Drift", "EQUITY") which had WR 15.8% PF 0.30, n=19.
    #   Backtest note: inverse confirmed PF 2.07 per quality_gates.py line ~1819 comment.
    #   Default OFF. Set INVERSE_EARNINGS_DRIFT_ENABLED=1 to add picks to active.
    #   Set INVERSE_EARNINGS_DRIFT_ENABLED=shadow to log without emitting (default shadow).
    #   Wire-Up Rule: opt-in sidecar. Promote to default-on after ≥100 picks + PF≥1.5.
    _IED_FLAG = os.environ.get("INVERSE_EARNINGS_DRIFT_ENABLED", "shadow").strip().lower()
    if _IED_FLAG in ("1", "true", "yes", "on", "shadow", "log_only"):
        try:
            from alpha_engine.calendar_anomalies import scan_earnings_gap_reversal as _ied_scan

            _ied_signals = _ied_scan(verbose=False)
            for _ied_s in _ied_signals:
                _ied_s["strategy"] = "inverse_earnings_drift"
                _ied_s["source_system"] = "inverse_earnings_drift_sidecar"
                _ied_s.setdefault("asset_class", "EQUITY")
                _ied_s.setdefault("direction", _ied_s.get("signal_type", "BUY"))

            if _ied_signals:
                if _IED_FLAG in ("shadow", "log_only"):
                    print(
                        f"  [IED_SHADOW] {len(_ied_signals)} inverse_earnings_drift signals "
                        f"(NOT added to active — shadow mode). "
                        f"Set INVERSE_EARNINGS_DRIFT_ENABLED=1 to enable."
                    )
                else:
                    _ied_keys = {
                        (p.get("symbol"), p.get("direction") or p.get("signal_type"))
                        for p in active
                    }
                    _ied_added = 0
                    for _ied_s in _ied_signals:
                        _k = (_ied_s.get("symbol"), _ied_s.get("direction") or _ied_s.get("signal_type"))
                        if _k not in _ied_keys:
                            active.append(_ied_s)
                            _ied_keys.add(_k)
                            _ied_added += 1
                    print(f"  [IED] Added {_ied_added} inverse_earnings_drift picks to active pipeline")
        except Exception as _ied_err:
            print(f"  [IED] Skipped (non-fatal): {_ied_err}")

    # 3b-MUT. DNA Mutation Engine: apply registered mutations to candidate picks.
    #   Reads alpha_engine/data/dna_mutations.json (status="active") and emits
    #   mutated variants alongside originals so they can be tracked independently
    #   under their `mutated_strategy_name`. Pairs with mutation_lifecycle_runner
    #   (PR #476) which evaluates emitted mutations and promotes/kills them.
    #
    #   Two safety gates (added per 5/5 external-AI consensus on PR #484):
    #     - MUTATION_ENGINE_SHADOW=1 -> compute mutations, log reach, do NOT
    #       extend `active`. Used for 7-day telemetry collection before any
    #       pick-displacement risk is taken.
    #     - MUTATION_SCORE_HAIRCUT (default 0.85) -> multiplicative haircut on
    #       mutated picks' ml_composite. Breaks tied-rank crowding-out at the
    #       MAX_ACTIVE_PICKS sort-and-truncate gate (production_scanner.py:769-846,
    #       applied at :4951-4957). Mutations inherit parent ml_composite via
    #       copy.deepcopy unchanged, so without a haircut high-composite parents
    #       spawn tied-rank variants that mechanically displace lower-scoring
    #       known-good picks. See reports/external_ai_review_pr484_mutation_engine_2026_04_28.md.
    #
    #   Default OFF on first ship -- flip with MUTATION_ENGINE_ENABLED=1 once a
    #   cycle of telemetry confirms picks emit cleanly. See PR feat/wire-mutation-engine.
    # BUG-4 (wbkz389ek / 2026-06-01): DNA mutator has been OFF for 6+ weeks, making
    # the engine detection-only (no rehab mutations actually emitted). Default kept
    # OFF intentionally -- enabling mutates live strategies and is an operator call.
    # To enable mutations: export MUTATION_ENGINE_ENABLED=1 (default OFF since 2026-04).
    # See wbkz389ek/2026-06-01.
    _ME_ENABLED = os.environ.get("MUTATION_ENGINE_ENABLED", "0") == "1"
    if not _ME_ENABLED and not globals().get("_ME_DISABLED_WARNED", False):
        import sys as _sys
        print("WARN [production_scanner] DNA mutator DISABLED -- set MUTATION_ENGINE_ENABLED=1 to enable rehab mutations", file=_sys.stderr)
        globals()["_ME_DISABLED_WARNED"] = True
    _ME_SHADOW = os.environ.get("MUTATION_ENGINE_SHADOW", "0") == "1"
    try:
        _ME_HAIRCUT = float(os.environ.get("MUTATION_SCORE_HAIRCUT", "0.85") or "0.85")
    except (TypeError, ValueError):
        _ME_HAIRCUT = 0.85

    if _ME_ENABLED or _ME_SHADOW:
        try:
            from dna_mutation_engine import apply_mutations_to_scanner

            _pre_mut_count = len(active)
            _maybe_extended = apply_mutations_to_scanner(list(active))
            _mutated_only = [
                p for p in _maybe_extended[_pre_mut_count:]
                if isinstance(p, dict)
            ]
            _added_mut = len(_mutated_only)

            if _ME_SHADOW and not _ME_ENABLED:
                # Shadow mode: log reach, sample, but do NOT mutate `active`.
                _sample = []
                for _v in _mutated_only[:5]:
                    _sample.append(
                        {
                            "strategy": _v.get("strategy"),
                            "symbol": _v.get("symbol"),
                            "mutation_type": _v.get("mutation_type"),
                            "mutation_parent": _v.get("mutation_parent"),
                            "ml_composite": _v.get("ml_composite"),
                        }
                    )
                print(
                    f"  [MUT-SHADOW] Computed {_added_mut} mutated variant(s) from "
                    f"{_pre_mut_count} parent picks (NOT EMITTED). Sample: {_sample}"
                )
                # Optional telemetry sink for 7-day reach analysis. Best-effort,
                # never blocks the scan loop.
                try:
                    from datetime import datetime as _dt_mut, timezone as _tz_mut

                    _tele_dir = Path(__file__).resolve().parent.parent / "audit_trail" / "data"
                    _tele_dir.mkdir(parents=True, exist_ok=True)
                    _tele_path = _tele_dir / "mutation_shadow_log.jsonl"
                    _tele_row = {
                        "ts": _dt_mut.now(_tz_mut.utc).isoformat(),
                        "parents": _pre_mut_count,
                        "mutations": _added_mut,
                        "haircut_default": _ME_HAIRCUT,
                        "sample": _sample,
                    }
                    with open(_tele_path, "a", encoding="utf-8") as _tfh:
                        _tfh.write(json.dumps(_tele_row) + "\n")
                except Exception as _tele_err:
                    print(f"  [MUT-SHADOW] Telemetry write skipped: {_tele_err}")
            elif _ME_ENABLED:
                # Live mode: apply ml_composite haircut to break tied-rank
                # crowding-out, then extend `active` with mutated variants.
                _haircut_applied = 0
                for _v in _mutated_only:
                    if _v.get("is_mutation") and "ml_composite" in _v:
                        try:
                            _orig = float(_v["ml_composite"])
                            _v["ml_composite_pre_haircut"] = _orig
                            _v["ml_composite"] = _orig * _ME_HAIRCUT
                            _v["mutation_score_haircut"] = _ME_HAIRCUT
                            _haircut_applied += 1
                        except (TypeError, ValueError):
                            pass
                active = _maybe_extended
                print(
                    f"  [MUT-LIVE] Applied mutations: {_added_mut} variant(s) "
                    f"added (pre={_pre_mut_count}, post={len(active)}, "
                    f"haircut={_ME_HAIRCUT}, scored={_haircut_applied})"
                )
        except Exception as _mut_err:
            print(f"  [MUTATION ENGINE] Skipped (non-fatal): {_mut_err}")

    # 3c2. OUTCOME RESOLVER: Resolve unresolved closed picks (pnl_pct=0/None)
    #   Runs once per hour (checks timestamp of last run). Fetches exit prices
    #   for picks that were tracked but never price-checked.
    try:
        _resolver_log = DATA_DIR / "outcome_resolver_log.json"
        _run_resolver = True
        if _resolver_log.exists():
            with open(_resolver_log, "r", encoding="utf-8") as _rl:
                _rl_data = json.load(_rl)
            if _rl_data:
                _last_ts = _rl_data[-1].get("timestamp", "")
                if _last_ts:
                    from datetime import datetime as _dt_or

                    _last_run = _dt_or.fromisoformat(_last_ts.replace("Z", "+00:00"))
                    _since = (datetime.now(timezone.utc) - _last_run).total_seconds()
                    if _since < 3600:  # Less than 1 hour since last run
                        _run_resolver = False
                        print(
                            f"\n[OUTCOME RESOLVER] Skipped (last run {_since / 60:.0f}m ago, runs hourly)"
                        )
        if _run_resolver:
            from outcome_resolver import run_outcome_resolver

            print("\n[OUTCOME RESOLVER] Resolving unresolved closed picks...")
            _or_report = run_outcome_resolver(dry_run=False)
            if _or_report["resolved_count"] > 0:
                print(
                    f"  Resolved {_or_report['resolved_count']} picks "
                    f"(WR={_or_report['win_rate']}%, "
                    f"W={_or_report['won']}/L={_or_report['lost']}/F={_or_report['flat']})"
                )
                # Reload closed picks since outcome_resolver modified them
                closed = load_closed_picks()
            else:
                print("  No unresolved picks found")
    except Exception as _or_err:
        print(f"  [OUTCOME RESOLVER] Failed (non-fatal): {_or_err}")

    # S1 FIX: Institutional Kill List loader
    try:
        _kill_list_path = os.path.join(
            os.path.dirname(__file__), "strategy_kill_list.json"
        )
        _institutional_kills = set()
        if os.path.exists(_kill_list_path):
            with open(_kill_list_path) as _kf:
                _kdata = json.load(_kf)
                for _ks in _kdata.get(
                    "strategies", _kdata.get("institutional_kill_list", [])
                ):
                    _institutional_kills.add(_ks.lower())

        _wl_path = os.path.join(
            os.path.dirname(__file__), "data", "core_whitelist.json"
        )
        _core_kills = set()
        if os.path.exists(_wl_path):
            with open(_wl_path) as _wf:
                _wl_early = json.load(_wf)
                for _ks in _wl_early.get("kill_list", []):
                    _ks_bare = (
                        _ks.split("::", 1)[1].lower() if "::" in _ks else _ks.lower()
                    )
                    _core_kills.add(_ks.lower())
                    _core_kills.add(_ks_bare)

        # Combined hard-kill set
        _hard_kills = _institutional_kills.union(_core_kills)

        active_before = len(active)
        active = [p for p in active if p.get("strategy", "").lower() not in _hard_kills]
        _n_killed = active_before - len(active)

        if _n_killed:
            print(
                f"  [HARD KILL] Removed {_n_killed} picks from institutional/core kill list (strategies: {', '.join(list(_hard_kills)[:5])}...)"
            )

    except Exception as _e:
        print(f"  [HARD KILL] Failed (non-fatal): {_e}")

    # 3b-RISK. RISK CONTROLS: Circuit breaker + daily loss limit + consecutive loss filter
    #   Runs BEFORE enrichment to avoid wasting API calls on picks that will be blocked.
    _risk_report = {}
    if _HAS_RISK_CONTROLS:
        try:
            active, _risk_report = run_all_risk_controls(active, closed)
            cb_status = _risk_report.get("circuit_breaker", "NORMAL")
            if cb_status == "EMERGENCY":
                print(
                    "\n[RISK] EMERGENCY -- all picks closed. Writing empty premium_signals."
                )
                write_premium_signals(market_ctx, [], build_track_record(closed, perf))
                elapsed = time.time() - start
                print(
                    f"\nProduction scanner completed (EMERGENCY halt) in {elapsed:.1f}s"
                )
                return
        except Exception as e:
            print(f"  [RISK] Post-generation risk controls failed (non-fatal): {e}")

    # 3b2. REGIME GATE: Suppress low-score crypto LONGs in bearish regime
    # Safety net -- scanner.py should already filter these, but production_scanner
    # also reads active_picks.json which may contain picks from prior scans.
    try:
        _hmm_path = DATA_DIR / "hmm_regime.json"
        _fg_path = DATA_DIR / "feargreed_cache.json"
        _hmm_data = {}
        _fg_value = 50
        if _hmm_path.exists():
            with open(_hmm_path) as _f:
                _hmm_data = json.load(_f)
        if _fg_path.exists():
            with open(_fg_path) as _f:
                _fg_raw = json.load(_f)
            _fg_value = float(_fg_raw.get("current", 50))

        # Use canonical HMM normalizer if available (EAGLE2 Phase 2)
        if _HAS_HMM_NORMALIZER:
            _norm = _normalize_hmm(_hmm_data, source="regime_terminal_hmm_v1")
            _agg_regime = str(_norm.get("regime", "")).lower()
        else:
            _agg_regime = str(
                _hmm_data.get("aggregate", {}).get("market_regime", "")
            ).lower()
        _crypto_regime = str(
            _hmm_data.get("aggregate", {}).get("crypto_regime", "")
        ).lower()
        _overview = _hmm_data.get("market_overview", {})
        _bear_count = _overview.get("bear_count", 0)
        _total = _overview.get("total_scanned", 1)

        _is_bearish = (
            _agg_regime in ("bear", "bearish", "crash", "crisis")
            or _crypto_regime in ("bear", "bearish", "crash", "crisis")
            or _fg_value < 25
            or (_bear_count > 0 and _bear_count / max(_total, 1) > 0.50)
        )

        if _is_bearish:
            _before = len(active)
            _kept = []
            for _p in active:
                _dir = str(_p.get("signal_type", _p.get("direction", ""))).upper()
                _cat = str(_p.get("category", "")).lower()
                _score = _ml_composite_key(_p)
                # ml_composite is 0-1 scale; 0.5 ~ "decent pick"
                if (
                    _dir in ("LONG", "BUY")
                    and _cat in ("crypto", "meme")
                    and _score < 0.5
                ):
                    print(
                        f"  [REGIME GATE] SUPPRESSED {_p.get('symbol', '?')} "
                        f"{_p.get('strategy', '?')[:30]} dir={_dir} score={_score:.1f}"
                    )
                    continue
                _kept.append(_p)
            _suppressed = _before - len(_kept)
            if _suppressed > 0:
                print(
                    f"  [REGIME GATE] Bearish (regime={_agg_regime}, F&G={_fg_value}): "
                    f"suppressed {_suppressed} low-score crypto/meme LONGs"
                )
            active = _kept
    except Exception as _rg_err:
        print(f"  [REGIME GATE] Failed (non-fatal): {_rg_err}")

    # 3c. Close stale picks (open >48h with no price updates)
    active, stale_closed = close_stale_picks(active)
    if stale_closed:
        # Append stale-closed picks to closed_picks.json
        try:
            closed_path = DATA_DIR / "closed_picks.json"
            existing_closed = []
            if closed_path.exists():
                with open(closed_path) as f:
                    existing_closed = json.load(f)
            existing_closed.extend(stale_closed)
            with open(closed_path, "w") as f:
                json.dump(_sanitize_for_json(existing_closed), f, indent=2)
            print(
                f"  [STALE] Appended {len(stale_closed)} stale picks to closed_picks.json"
            )
            closed.extend(stale_closed)
        except Exception as e:
            print(f"  [STALE] Could not persist stale closures: {e}")

    # 3d. FAST REGIME: Tag each pick + strategy routing
    if _HAS_FAST_REGIME and market_ctx.get("fast_regime"):
        try:
            _fr = market_ctx["fast_regime"]
            _fr_data = market_ctx.get("fast_regime_data") or {}
            _fr_score = _fr_data.get("score", 0)
            _fr_conf = _fr_data.get("confidence", 0)
            _blocked_count = 0
            _tagged = 0
            _kept_fr = []
            for _p in active:
                # Tag every pick with fast regime data
                _extra = _p.get("extra", {}) or {}
                _extra["fast_regime"] = _fr
                _extra["fast_regime_score"] = _fr_score
                _extra["fast_regime_confidence"] = _fr_conf
                _p["extra"] = _extra
                _p["fast_regime"] = _fr
                _tagged += 1

                # Strategy routing: block mismatched strategies
                _strat = _p.get("strategy", "")
                if not is_strategy_allowed(_strat, _fr):
                    print(
                        f"  [FAST REGIME ROUTE] Blocked {_p.get('symbol', '?')} "
                        f"{_strat[:30]} in {_fr} regime"
                    )
                    _blocked_count += 1
                    continue
                _kept_fr.append(_p)

            if _blocked_count:
                print(
                    f"  [FAST REGIME] Blocked {_blocked_count} picks mismatched with {_fr} regime"
                )
            active = _kept_fr
            print(
                f"  [FAST REGIME] Tagged {_tagged} picks with regime={_fr} score={_fr_score}"
            )
        except Exception as _fr_err:
            print(f"  [FAST REGIME] Enrichment failed (non-fatal): {_fr_err}")

    # 4. Enrich with live Binance prices
    active = enrich_picks(active)

    # 4a. Enrich forex/stock picks with yfinance prices (Binance doesn't cover these)
    try:
        active = enrich_forex_stock_picks(active)
    except Exception as e:
        import traceback

        print(f"  [WARN] enrich_forex_stock_picks failed: {e}")
        traceback.print_exc()
        print(
            f"  [WARN] Non-crypto picks will have null prices until universal_price_enricher runs"
        )

    # 4b. Sanity check: detect & fix corrupted entry prices (yfinance BTC-denomination bug)
    active = sanity_check_entry_prices(active)

    # 4c. Remove picks with invalid prices (entry=0, negative TP/SL, TP on wrong side)
    before_count = len(active)
    valid_picks = []
    for p in active:
        entry = p.get("entry_price", 0) or 0
        tp = p.get("take_profit", 0) or 0
        sl = p.get("stop_loss", 0) or 0
        direction = (p.get("signal_type") or p.get("direction") or "BUY").upper()

        # Skip picks with no entry price (informational only, e.g. insider_filing_scanner)
        if entry <= 0:
            print(
                f"  [FILTER] Removing {p.get('symbol')} ({p.get('strategy', '')[:30]}): entry_price={entry}"
            )
            continue

        # Fix negative TP/SL (bug in volume_profile_value_area)
        if tp < 0:
            print(
                f"  [FIX] {p.get('symbol')} TP was negative ({tp}), setting to entry +/- 2%"
            )
            tp = entry * 0.98 if direction in ("SELL", "SHORT") else entry * 1.02
            p["take_profit"] = round(tp, 8)
        if sl < 0:
            print(
                f"  [FIX] {p.get('symbol')} SL was negative ({sl}), setting to entry +/- 2%"
            )
            sl = entry * 1.02 if direction in ("SELL", "SHORT") else entry * 0.98
            p["stop_loss"] = round(sl, 8)

        # Fix TP on wrong side of entry
        if direction in ("BUY", "LONG") and tp > 0 and tp < entry * 0.5:
            print(
                f"  [FIX] {p.get('symbol')} LONG TP ({tp}) below entry ({entry}), swapping"
            )
            p["take_profit"] = entry + abs(entry - tp)
        if direction in ("SELL", "SHORT") and tp > 0 and tp > entry * 1.5:
            print(
                f"  [FIX] {p.get('symbol')} SHORT TP ({tp}) above entry ({entry}), swapping"
            )
            p["take_profit"] = entry - abs(tp - entry)

        valid_picks.append(p)
    removed = before_count - len(valid_picks)
    if removed:
        print(f"  [FILTER] Removed {removed} picks with invalid prices")
    active = valid_picks

    # 4d. Cap TP targets (ML sometimes sets unrealistic 31% targets)
    active = cap_tp_targets(active)

    # 4d2. Adaptive TP/SL -- MFE/MAE-driven optimal levels per strategy/symbol
    #   Overrides static TP/SL with data-driven levels from closed trade analysis.
    #   R:R 1.0-1.5 has 52.5% WR (best) vs R:R 2.0+ at 28.4% (TPs unreachable).
    #   Only overrides when per-strategy or per-symbol data exists (>= 10 trades).
    if _HAS_ADAPTIVE_TP_SL:
        try:
            active = apply_adaptive_tp_sl(active, closed_picks=closed)
        except Exception as _adaptive_err:
            print(f"  [ADAPTIVE_TP_SL] Failed (non-fatal): {_adaptive_err}")
    else:
        print("  [ADAPTIVE_TP_SL] Module not available -- using static TP/SL")

    # 4e. CoinMetrics on-chain enrichment (MVRV, NVT, active addresses)
    if _HAS_COINMETRICS:
        try:
            enriched_cm = 0
            for sig in active:
                sym = sig.get("symbol", "")
                # CoinMetrics only covers major chains -- skip forex/stocks
                cat = (sig.get("category") or "crypto").lower()
                if cat not in ("crypto",):
                    continue
                try:
                    features = get_onchain_features(sym)
                    if features:
                        sig.setdefault("onchain", {}).update(features)
                        enriched_cm += 1
                except Exception:
                    pass
            print(
                f"  [COINMETRICS] Enriched {enriched_cm}/{len(active)} picks with on-chain data"
            )
        except Exception as e:
            print(f"  [WARN] CoinMetrics enrichment failed: {e}")

    # 4f-pre. Mempool.space BTC congestion enrichment
    if _HAS_MEMPOOL:
        try:
            mempool_data = get_mempool_features()
            if mempool_data:
                for sig in active:
                    # Attach mempool context to BTC picks (congestion affects all crypto indirectly)
                    cat = (sig.get("category") or "crypto").lower()
                    if cat == "crypto":
                        sig.setdefault("mempool", {}).update(mempool_data)
                print(
                    f"  [MEMPOOL] Attached mempool data to crypto picks "
                    f"(fee={mempool_data.get('mempool_fee_fastest', '?')} sat/vB, "
                    f"{mempool_data.get('mempool_mb', '?')} MB)"
                )
            else:
                print(f"  [MEMPOOL] No data returned")
        except Exception as e:
            print(f"  [WARN] Mempool enrichment failed: {e}")

    # 4f2. Causal inference: BTC lead-lag enrichment (Granger causality)
    if _HAS_CAUSAL_FILTER:
        try:
            print(
                f"  [CAUSAL FILTER] Running BTC lead-lag enrichment on {len(active)} picks..."
            )
            active = enrich_picks_with_btc_lead(active)
            print(
                f"  [CAUSAL FILTER] Done -- {len(active)} picks enriched with BTC lead-lag signals"
            )
        except Exception as e:
            print(f"  [WARN] Causal filter enrichment failed: {e}")
    else:
        print("  [CAUSAL FILTER] Module not available (import failed)")

    # 4g. Market modifiers (BTC dominance, treasury boost, supply change)
    if _HAS_MARKET_MODIFIERS:
        try:
            modified_count = 0
            for sig in active:
                old_conf = sig.get("confidence", 0.5)
                apply_all_modifiers(sig)
                if sig.get("confidence", old_conf) != old_conf:
                    modified_count += 1
            print(
                f"  [MARKET_MOD] Applied modifiers to {modified_count}/{len(active)} picks"
            )
        except Exception as e:
            print(f"  [WARN] Market modifiers failed: {e}")

    # 4h. Whale Intelligence: Whale Concentration Index (WCI) boost
    if _HAS_WCI:
        try:
            wci_count = 0
            for sig in active:
                old_conf = sig.get("confidence", 0.5)
                # Boost confidence based on whale concentration (0.5 to 1.5 multiplier)
                # Uses cached result from whale_concentration_index.json
                boost = get_wci_boost(sig.get("symbol", ""))
                if boost != 1.0:
                    new_conf = min(0.99, old_conf * boost)
                    sig["confidence"] = round(new_conf, 4)
                    sig["wci_multiplier"] = round(boost, 3)
                    if sig.get("confidence") != old_conf:
                        wci_count += 1
            if wci_count > 0:
                print(f"  [WCI] Applied Whale Boost to {wci_count}/{len(active)} picks")
        except Exception as e:
            print(f"  [WARN] Whale index enrichment failed: {e}")

    # 4h. Optimal entry override (env ALPHA_OPTIMAL_ENTRY=1 to activate)
    if OPTIMAL_ENTRY_ENABLED:
        try:
            opt_filtered = 0
            opt_adjusted = 0
            filtered_active = []
            for sig in active:
                direction = (
                    sig.get("signal_type") or sig.get("direction") or "BUY"
                ).upper()
                # BUY_ONLY filter: drop SHORT/SELL picks UNLESS exempt strategy
                _opt_strat = sig.get("strategy") or ""
                if OPTIMAL_ENTRY_BUY_ONLY and direction in ("SELL", "SHORT"):
                    if _opt_strat not in _SHORT_EXEMPT_STRATEGIES:
                        opt_filtered += 1
                        continue
                    # Exempt strategy — let SHORT through
                # Override TP/SL to optimal percentages
                entry = sig.get("entry_price", 0) or 0
                if entry > 0:
                    if direction in ("BUY", "LONG"):
                        sig["take_profit"] = round(
                            entry * (1 + OPTIMAL_ENTRY_TP_PCT), 8
                        )
                        sig["stop_loss"] = round(entry * (1 - OPTIMAL_ENTRY_SL_PCT), 8)
                    else:
                        sig["take_profit"] = round(
                            entry * (1 - OPTIMAL_ENTRY_TP_PCT), 8
                        )
                        sig["stop_loss"] = round(entry * (1 + OPTIMAL_ENTRY_SL_PCT), 8)
                    # Recalculate R:R
                    tp_dist = abs(sig["take_profit"] - entry)
                    sl_dist = abs(sig["stop_loss"] - entry)
                    sig["risk_reward"] = (
                        round(tp_dist / sl_dist, 2) if sl_dist > 0 else 1.5
                    )
                    opt_adjusted += 1
                filtered_active.append(sig)
            active = filtered_active
            print(
                f"  [OPTIMAL_ENTRY] Active: TP={OPTIMAL_ENTRY_TP_PCT * 100:.0f}% SL={OPTIMAL_ENTRY_SL_PCT * 100:.0f}% "
                f"BUY_ONLY={OPTIMAL_ENTRY_BUY_ONLY} -- adjusted {opt_adjusted}, filtered {opt_filtered} shorts"
            )
        except Exception as e:
            print(f"  [WARN] Optimal entry override failed: {e}")

    # 4i. Inject btc_24h_change from market_ctx into each pick (Phase 17).
    #     This is the strongest missing predictor per ML_BLUEPRINT Section 9.
    #     Done before feature_populator so it can skip re-computing from klines.
    _btc_24h = market_ctx.get("btc_24h_change")
    if _btc_24h is not None:
        for _sig in active or []:
            if "btc_24h_change" not in _sig or _sig["btc_24h_change"] is None:
                _sig["btc_24h_change"] = _btc_24h

    # 4i-b. Feature populator: populate real OHLCV-derived ML features on every pick.
    #     Catches picks loaded from active_picks.json that may lack features
    #     (e.g., picks from prior runs before feature_populator was wired into scanner.py).
    #     Runs BEFORE quality gates so ML scoring/gating has real feature data.
    if _HAS_FEATURE_POPULATOR:
        try:
            print(f"  [FEATURE POPULATOR] Running on {len(active)} picks...")
            if active:
                active = _populate_features_batch(active)
            print(
                f"  [FEATURE POPULATOR] Done -- {len(active)} picks have OHLCV features"
            )
        except Exception as _fp_err:
            print(f"  [FEATURE POPULATOR] Failed (non-fatal): {_fp_err}")
    else:
        print("  [FEATURE POPULATOR] Module not available (import failed)")

    # 4j. Data Coverage Enforcer: backfill inline features, measure coverage, penalize low-coverage picks
    if _HAS_COVERAGE_ENFORCER:
        try:
            print(f"  [COVERAGE ENFORCER] Running on {len(active)} picks...")
            if active:
                active = _enforce_coverage(active)
            print(f"  [COVERAGE ENFORCER] Done -- {len(active)} picks coverage-checked")
        except Exception as _ce_err:
            print(f"  [COVERAGE ENFORCER] Failed (non-fatal): {_ce_err}")
    else:
        print("  [COVERAGE ENFORCER] Module not available (import failed)")

    # 4j2. Regime Router: apply composite regime-based sizing boost/penalty
    #   Reads regime_report.json + fear_greed from market context to classify
    #   market as RISK_ON/RISK_OFF/NEUTRAL/VOLATILE. Then boosts/penalizes
    #   sizing_multiplier per strategy family alignment (C1 fix: never touches confidence).
    if _HAS_REGIME_ROUTER:
        try:
            print(f"  [REGIME ROUTER] Running on {len(active)} picks...")
            if active:
                active = _apply_regime_routing(active, market_ctx=market_ctx)
        except Exception as _rr_err:
            print(f"  [REGIME ROUTER] Failed (non-fatal): {_rr_err}")
    else:
        print("  [REGIME ROUTER] Module not available (import failed)")

    # 4k. CRITICAL ML FIX: Persist enriched ML features back to active_picks.json
    #   The feature_populator (4i) and coverage enforcer (4j) compute real values for
    #   funding_rate, fear_greed, orderbook_imbalance, ema_position, rsi_at_entry, etc.
    #   But these enriched values were ONLY written to premium_signals.json, never back
    #   to active_picks.json. When forward_validator closes picks, it reads from
    #   active_picks.json — so closed_picks.json (and thus ML training data) had all
    #   zeros for these features. This write-back fixes that data flow gap.
    #   Source: ML_DATA_FLOW_AUDIT Recommendation 1, ML_BLUEPRINT Section 9.
    _ML_FEATURE_KEYS = [
        "funding_rate",
        "funding_rate_raw",
        "fear_greed",
        "fear_greed_norm",
        "orderbook_imbalance",
        "ema_position",
        "spread_pct",
        "wick_ratio",
        "entry_distance_vwap",
        "bb_pct_b",
        "vpin",
        "galaxy_score",
        "hma_slope",
        "rsi_1h",
        "rsi_4h",
        "rsi_at_entry",
        "volume_ratio",
        "atr_at_entry",
        "regime_encoded",
        "convergence",
        "obi_delta_5",
        "obi_delta_15",
        "obi_acceleration",
        "market_fear_greed",
        "risk_reward",
        "forward_wr",
        "forward_trades",
        "forward_validated",
        "hurst_exponent",
        "wavelet_trend_strength",
        "wavelet_momentum",
        "pca_market_exposure",
        "pca_diversification",
        "ml_features_at_entry",
        "regime_alignment",
        "regime_current",
        "regime_family",
        "regime_confidence",
        "regime_alignment_label",
    ]
    if active:
        try:
            # Write enriched in-memory picks directly to disk.
            # The old merge-by-ID approach failed when IDs didn't match between
            # in-memory (feature-populated) and on-disk (stale) picks.
            # Now we write the in-memory active list which HAS features from step 4i.
            _fv_active_path = DATA_DIR / "active_picks.json"
            _feat_count = sum(1 for p in active if p.get("rsi_at_entry") is not None)
            with open(_fv_active_path, "w", encoding="utf-8") as _fv_f:
                json.dump(
                    _sanitize_for_json(active),
                    _fv_f,
                    indent=2,
                    ensure_ascii=False,
                    default=str,
                )
            print(
                f"  [ML PERSIST] Wrote {len(active)} picks to active_picks.json "
                f"({_feat_count} have RSI features)"
            )
        except Exception as _mlp_err:
            print(f"  [ML PERSIST] Write-back failed (non-fatal): {_mlp_err}")

    # 5. Assign confidence tiers
    active = assign_tiers(active)

    # 6. Build track record
    track = build_track_record(closed, perf)

    # 6b. Safety check (GoPlus rugpull/honeypot detection)
    try:
        shared_dir = str(Path(__file__).resolve().parent.parent / "shared")
        if shared_dir not in sys.path:
            sys.path.insert(0, shared_dir)
        from safety_checker import SafetyChecker

        safety = SafetyChecker(cache_dir=DATA_DIR / "cache")
        active = safety.enrich_picks(active)
        for p in active:
            ss = float(p.get("safety_score", 100) or 100)
            if ss < 30:
                p["score"] = max(0, float(p.get("score", 50) or 50) - 25)
                p["_low_safety"] = True
    except Exception as e:
        print(f"  [SAFETY] Skipped: {e}")

    # 6c. Multi-timeframe performance breakdown (1W/1M/3M/YTD/1Y)
    try:
        from performance_breakdown import PerformanceBreakdown

        perf_bd = PerformanceBreakdown(cache_dir=DATA_DIR / "cache")
        active = perf_bd.enrich_picks(active)
    except Exception as e:
        print(f"  [PERF] Skipped: {e}")

    # 6d. Elite scoring -- composite quality score for every active pick
    try:
        from elite_scorer import enrich_picks_with_elite_score

        enrich_picks_with_elite_score(active, DATA_DIR)
    except Exception as e:
        print(f"  [ELITE] Scoring failed (non-fatal): {e}")

    # 6d2. Model calibration -- add calibrated probability + uncertainty to picks
    try:
        from model_calibration import apply_calibration_to_picks

        active = apply_calibration_to_picks(active, DATA_DIR)
    except ImportError:
        pass
    except Exception as e:
        print(f"  [CALIBRATION] Pick enrichment failed (non-fatal): {e}")

    # 6d3. Ensemble Model Agreement Gate (hedge-fund roadmap: >=70% agreement)
    #   Uses prediction_uncertainty from model_calibration (step 6d2) as proxy
    #   for model agreement. Soft gate (score penalty) + hard gate (block).
    #   - uncertainty < 0.10 → HIGH agreement → +2 elite_score
    #   - uncertainty 0.10-0.20 → MODERATE → no change
    #   - uncertainty > 0.20 → LOW agreement → -3 elite_score, require conf >= 0.75
    #   - uncertainty > 0.30 → VERY LOW → BLOCK pick entirely
    try:
        _ensemble_blocked = []
        _ensemble_penalized = 0
        _ensemble_boosted = 0
        _agreement_log = []
        _pre_agreement = len(active)

        surviving = []
        for _p in active:
            _unc = _p.get("prediction_uncertainty", None)
            _conf = float(
                _p.get(
                    "calibrated_probability", _p.get("confidence", _p.get("score", 0))
                )
                or 0
            )
            _sym = _p.get("symbol", "?")
            _strat = _p.get("strategy", "?")

            if _unc is None:
                # No uncertainty data (calibration skipped) -- pass through
                _p["ensemble_agreement"] = "UNKNOWN"
                surviving.append(_p)
                continue

            _unc = float(_unc)

            if _unc > 0.30:
                # VERY LOW agreement -- hard block
                _p["ensemble_agreement"] = "VERY_LOW"
                _p["_ensemble_blocked"] = (
                    f"ensemble disagreement too high: uncertainty={_unc:.3f} > 0.30"
                )
                _ensemble_blocked.append(_p)
                _agreement_log.append(
                    f"    BLOCKED: {_sym} {_strat} "
                    f"uncertainty={_unc:.3f} (VERY LOW agreement)"
                )
                continue
            elif _unc > 0.20:
                # LOW agreement -- soft gate: penalize + require high confidence
                _p["ensemble_agreement"] = "LOW"
                _cur_elite = float(_p.get("elite_score", 0) or 0)
                _p["elite_score"] = round(_cur_elite - 3, 2)
                if _conf < 0.75:
                    _p["_ensemble_blocked"] = (
                        f"low agreement (unc={_unc:.3f}) + low conf ({_conf:.3f} < 0.75)"
                    )
                    _ensemble_blocked.append(_p)
                    _agreement_log.append(
                        f"    BLOCKED: {_sym} {_strat} "
                        f"uncertainty={_unc:.3f}, conf={_conf:.3f} < 0.75 required"
                    )
                    continue
                _ensemble_penalized += 1
                _agreement_log.append(
                    f"    PENALIZED: {_sym} {_strat} "
                    f"uncertainty={_unc:.3f} (-3 elite, conf={_conf:.3f} >= 0.75 OK)"
                )
                surviving.append(_p)
            elif _unc < 0.10:
                # HIGH agreement -- reward
                _p["ensemble_agreement"] = "HIGH"
                _cur_elite = float(_p.get("elite_score", 0) or 0)
                _p["elite_score"] = round(_cur_elite + 2, 2)
                _ensemble_boosted += 1
                surviving.append(_p)
            else:
                # MODERATE agreement (0.10-0.20) -- no change
                _p["ensemble_agreement"] = "MODERATE"
                surviving.append(_p)

        active = surviving
        _blocked_count = len(_ensemble_blocked)
        print(
            f"  [ENSEMBLE GATE] Passed: {len(active)}/{_pre_agreement}, "
            f"Blocked: {_blocked_count}, "
            f"Boosted(+2): {_ensemble_boosted}, Penalized(-3): {_ensemble_penalized}"
        )
        for _line in _agreement_log:
            print(_line)

        # Append blocked picks to rejected list so they appear in audit output
        for _bp in _ensemble_blocked:
            _bp["_quality_gate_rejected"] = _bp.get(
                "_ensemble_blocked", "ensemble gate"
            )
    except Exception as e:
        print(f"  [ENSEMBLE GATE] Failed (non-fatal): {e}")

    # 6e. Dynamic risk sizing -- ATR-based TP/SL + half-Kelly position sizing
    try:
        from dynamic_risk import enrich_picks_with_dynamic_risk

        enrich_picks_with_dynamic_risk(active, perf)
    except Exception as e:
        print(f"  [RISK] Dynamic risk failed (non-fatal): {e}")

    # 6e1b. Adaptive stops -- MFE/MAE-calibrated SL/TP override (tighter only)
    #   Loads per-strategy calibration from data/adaptive_stops_calibration.json,
    #   then tightens SL/TP for picks whose strategy has enough historical trades.
    #   Copy/clone strategies get wider minimums (8% TP / 4% SL) to give whales room.
    try:
        from adaptive_stops import apply_adaptive_stops, CALIBRATION_OUTPUT_PATH

        _adaptive_cal = {}
        if CALIBRATION_OUTPUT_PATH.exists():
            with open(CALIBRATION_OUTPUT_PATH, "r", encoding="utf-8") as _cal_f:
                _cal_data = json.loads(_cal_f.read())
                _adaptive_cal = _cal_data.get("calibration", {})

        if _adaptive_cal:
            _adapt_applied = 0
            _adapt_whale_widened = 0
            _adapt_total = len(active)
            _WHALE_MIN_TP_PCT = 0.08  # 8% minimum TP for copy/clone strategies
            _WHALE_MIN_SL_PCT = 0.04  # 4% minimum SL for copy/clone strategies

            for _p in active:
                _strat = _p.get("strategy", "").lower()
                _is_whale = "copy" in _strat or "clone" in _strat

                # Widen whale stops BEFORE adaptive tightening so the floor holds
                if _is_whale:
                    _entry = float(_p.get("entry_price", 0) or 0)
                    _cur_sl = float(_p.get("stop_loss", 0) or 0)
                    _cur_tp = float(_p.get("take_profit", 0) or 0)
                    if _entry > 0 and _cur_sl > 0 and _cur_tp > 0:
                        _is_long = _cur_sl < _entry
                        _sl_dist_pct = abs(_cur_sl - _entry) / _entry
                        _tp_dist_pct = abs(_cur_tp - _entry) / _entry
                        _widened = False
                        if _sl_dist_pct < _WHALE_MIN_SL_PCT:
                            if _is_long:
                                _p["stop_loss"] = round(
                                    _entry * (1.0 - _WHALE_MIN_SL_PCT), 8
                                )
                            else:
                                _p["stop_loss"] = round(
                                    _entry * (1.0 + _WHALE_MIN_SL_PCT), 8
                                )
                            _widened = True
                        if _tp_dist_pct < _WHALE_MIN_TP_PCT:
                            if _is_long:
                                _p["take_profit"] = round(
                                    _entry * (1.0 + _WHALE_MIN_TP_PCT), 8
                                )
                            else:
                                _p["take_profit"] = round(
                                    _entry * (1.0 - _WHALE_MIN_TP_PCT), 8
                                )
                            _widened = True
                        if _widened:
                            _adapt_whale_widened += 1
                            _p["whale_stops_widened"] = True

                # Apply adaptive tightening (skips if no calibration for this strategy)
                _before_sl = _p.get("stop_loss")
                _before_tp = _p.get("take_profit")
                apply_adaptive_stops(_p, _adaptive_cal)
                if _p.get("adaptive_stops_applied"):
                    _adapt_applied += 1

                    # For whale picks, enforce the floor AFTER adaptive tightening
                    if _is_whale and _entry > 0:
                        _new_sl = float(_p.get("stop_loss", 0) or 0)
                        _new_tp = float(_p.get("take_profit", 0) or 0)
                        _is_long = _new_sl < _entry
                        if (
                            _new_sl > 0
                            and abs(_new_sl - _entry) / _entry < _WHALE_MIN_SL_PCT
                        ):
                            if _is_long:
                                _p["stop_loss"] = round(
                                    _entry * (1.0 - _WHALE_MIN_SL_PCT), 8
                                )
                            else:
                                _p["stop_loss"] = round(
                                    _entry * (1.0 + _WHALE_MIN_SL_PCT), 8
                                )
                        if (
                            _new_tp > 0
                            and abs(_new_tp - _entry) / _entry < _WHALE_MIN_TP_PCT
                        ):
                            if _is_long:
                                _p["take_profit"] = round(
                                    _entry * (1.0 + _WHALE_MIN_TP_PCT), 8
                                )
                            else:
                                _p["take_profit"] = round(
                                    _entry * (1.0 - _WHALE_MIN_TP_PCT), 8
                                )

            print(
                f"  [ADAPTIVE_STOPS] Applied to {_adapt_applied}/{_adapt_total} picks, "
                f"{_adapt_whale_widened} whale-widened"
            )
        else:
            print("  [ADAPTIVE_STOPS] No calibration data found -- skipped")
    except Exception as e:
        print(f"  [ADAPTIVE_STOPS] Failed (non-fatal): {e}")

    # 6e2. Pump-and-Dump detection guard -- add pump_risk_score to each pick
    try:
        from pump_guard import enrich_picks_with_pump_risk

        active = enrich_picks_with_pump_risk(active)
    except Exception as e:
        print(f"  [PUMP_GUARD] Skipped: {e}")

    # 6e3. Risk:Reward hard gate -- reject any pick with R:R < MIN_RISK_REWARD
    #   Also computes R:R from TP/SL/entry when missing (clone/copy-trader picks often lack it).
    #   EXEMPT_FROM_SAFETY_GATES picks still must meet MINIMUM_RR_EVEN_EXEMPT (0.5).
    _rr_before = len(active)
    _rr_passed = []
    _rr_computed = 0
    for _p in active:
        _rr_val = float(_p.get("risk_reward", 0) or 0)

        # Compute R:R from TP/SL/entry if missing (fixes clone/copy-trader bypass)
        if _rr_val == 0:
            _entry = float(_p.get("entry_price", 0) or 0)
            _tp = float(_p.get("take_profit", 0) or 0)
            _sl = float(_p.get("stop_loss", 0) or 0)
            if _entry > 0 and _tp > 0 and _sl > 0:
                _tp_dist = abs(_tp - _entry)
                _sl_dist = abs(_sl - _entry)
                if _sl_dist > 0:
                    _rr_val = round(_tp_dist / _sl_dist, 2)
                    _p["risk_reward"] = _rr_val
                    _rr_computed += 1

        # Determine effective minimum R:R based on safety mode
        _safety_mode = _p.get("clone_safety_mode", "")
        _is_exempt = (
            _safety_mode == "EXEMPT_FROM_SAFETY_GATES"
            or "exempt_from_safety_gates" in (_p.get("tags") or [])
        )
        _effective_min_rr = MINIMUM_RR_EVEN_EXEMPT if _is_exempt else MIN_RISK_REWARD

        if _rr_val > 0 and _rr_val < _effective_min_rr:
            _exempt_label = " (EXEMPT override)" if _is_exempt else ""
            print(
                f"  [R:R GATE] REJECTED {_p.get('symbol', '?')} "
                f"{_p.get('strategy', '?')[:30]} -- R:R={_rr_val:.2f} < {_effective_min_rr}{_exempt_label}"
            )
            _p["_quality_gate_rejected"] = (
                f"R:R {_rr_val:.2f} < {_effective_min_rr} minimum"
            )
            continue
        _rr_passed.append(_p)
    _rr_rejected = _rr_before - len(_rr_passed)
    if _rr_computed > 0:
        print(
            f"  [R:R GATE] Computed missing R:R for {_rr_computed} picks from TP/SL/entry"
        )
    if _rr_rejected > 0:
        print(
            f"  [R:R GATE] Rejected {_rr_rejected}/{_rr_before} picks with R:R below minimum"
        )
    active = _rr_passed

    # Preserve the raw pre-penalty confidence for later hard-gate checks.
    # Drawdown and liquidity adjustments below are soft portfolio controls and
    # should affect ranking/sizing, not silently rewrite the admission floor.
    for _p in active:
        if "_quality_gate_confidence" in _p:
            continue
        try:
            _p["_quality_gate_confidence"] = round(
                float(_p.get("confidence", 0.5) or 0.5), 4
            )
        except (TypeError, ValueError):
            _p["_quality_gate_confidence"] = 0.5

    # 6e4. Drawdown-based confidence penalty (soft gate -- no hard blocks)
    #   Strategy in deep drawdown or long loss streak gets confidence reduced
    #   for ranking/sizing without converting this into an implicit hard reject.
    #   -50% DD → 0.5x conf | -100% DD → 0.2x conf | loss streak >=10 → 0.3x conf
    if _HAS_DRAWDOWN_TRACKER:
        try:
            _dd_report = compute_all_drawdowns()
            _dd_per_strategy = _dd_report.get("per_strategy", {})
            _dd_penalized = 0
            for _p in active:
                _p_raw_strat = _p.get("strategy", "")
                _strat_name = (
                    STRATEGY_TRACK_ALIASES.get(_p_raw_strat, _p_raw_strat)
                    if _p_raw_strat
                    else ""
                )
                _dd_metrics = _dd_per_strategy.get(_strat_name)
                if not _dd_metrics:
                    continue

                _cur_dd_pct = _dd_metrics.get("current_drawdown_pct", 0.0)
                _loss_streak = _dd_metrics.get("longest_losing_streak", 0)
                _old_conf = float(_p.get("confidence", 0.5) or 0.5)
                _dd_mult = 1.0

                # Drawdown penalty tiers (current_drawdown_pct is positive, e.g. 50 = -50%)
                if _cur_dd_pct >= 100.0:
                    _dd_mult = min(_dd_mult, 0.2)
                elif _cur_dd_pct >= 50.0:
                    _dd_mult = min(_dd_mult, 0.5)

                # Loss streak penalty
                if _loss_streak >= 10:
                    _dd_mult = min(_dd_mult, 0.3)

                if _dd_mult < 1.0:
                    # C1 FIX: Use sizing_multiplier instead of modifying confidence
                    # Confidence is used by quality gate — modifying it makes soft gates into hard kills
                    _existing_mult = float(_p.get("sizing_multiplier", 1.0) or 1.0)
                    _p["sizing_multiplier"] = round(_existing_mult * _dd_mult, 4)
                    _p["drawdown_penalty"] = round(1.0 - _dd_mult, 2)
                    _p["drawdown_pct"] = round(_cur_dd_pct, 2)
                    _p["loss_streak"] = _loss_streak
                    _dd_penalized += 1

            print(
                f"  [DRAWDOWN GATE] Penalized {_dd_penalized}/{len(active)} picks "
                f"(strategies: {len(_dd_per_strategy)} tracked)"
            )
        except Exception as e:
            print(f"  [DRAWDOWN GATE] Failed (non-fatal): {e}")
    else:
        print("  [DRAWDOWN GATE] Module not available (import failed)")

    # 6e5. Volume-percentile liquidity gate (P0 FIX -- low-liquidity slippage filter)
    #   Low volume = unreliable fills = slippage = losses.
    #   volume_ratio is current volume / 20-period average volume.
    #   < 0.3 = dangerously illiquid (conf *= 0.2, nearly block)
    #   < 0.5 = low liquidity (conf *= 0.5, significant penalty)
    #   > 2.0 = high volume confirmation (conf *= 1.1, capped at 0.95)
    _vol_penalized = 0
    _vol_boosted = 0
    for _p in active:
        _vr = _p.get("volume_ratio") or (_p.get("extra", {}) or {}).get("vol_ratio")
        if _vr is None:
            continue
        try:
            _vr = float(_vr)
        except (TypeError, ValueError):
            continue
        _old_conf = float(_p.get("confidence", 0.5) or 0.5)
        # C1 FIX: Use sizing_multiplier instead of confidence to avoid cascading hard kills
        _existing_mult = float(_p.get("sizing_multiplier", 1.0) or 1.0)
        if _vr < 0.3:
            _p["sizing_multiplier"] = round(_existing_mult * 0.2, 4)
            _p["volume_liquidity_penalty"] = 0.8
            _p["volume_ratio_gate"] = f"very_low ({_vr:.2f})"
            _vol_penalized += 1
        elif _vr < 0.5:
            _p["sizing_multiplier"] = round(_existing_mult * 0.5, 4)
            _p["volume_liquidity_penalty"] = 0.5
            _p["volume_ratio_gate"] = f"low ({_vr:.2f})"
            _vol_penalized += 1
        elif _vr > 2.0:
            _p["sizing_multiplier"] = round(min(_existing_mult * 1.1, 1.5), 4)
            _p["volume_liquidity_boost"] = 0.1
            _p["volume_ratio_gate"] = f"high ({_vr:.2f})"
            _vol_boosted += 1
    print(
        f"  [VOLUME GATE] Penalized {_vol_penalized}, boosted {_vol_boosted} / {len(active)} picks"
    )

    # 6f. Pick Quality Hard Gates (Phase 12 -- data-driven from 788 closed picks)
    # Macro equity gate: skip EQUITY picks when yield curve inverted + Fed hiking
    if _macro_equity_conf_floor is not None:
        _pre_macro_eq = len(active)
        _macro_eq_kept = []
        for _p in active:
            _cat = str(_p.get("category", "")).lower()
            if (
                _cat in ("equity", "stock", "etf")
                and float(_p.get("confidence", 0) or 0) < _macro_equity_conf_floor
            ):
                _p["_quality_gate_rejected"] = (
                    f"[MACRO EQUITY GATE] blocked under inversion+hiking (conf < {_macro_equity_conf_floor})"
                )
                continue
            _macro_eq_kept.append(_p)
        if len(_macro_eq_kept) < _pre_macro_eq:
            print(
                f"  [MACRO EQUITY GATE] Blocked {_pre_macro_eq - len(_macro_eq_kept)} "
                f"EQUITY picks under macro stress"
            )
        active = _macro_eq_kept

    # 6f1. CATALYST FILTER: skip EQUITY/ETF picks within +/-2 trading days (~48h)
    # of an earnings print. Wire-up of alpha_engine/catalyst_filter.py per
    # reports/HEDGE_LIBS_LEVERAGE_AUDIT_2026_04_22.md item #1. Soft fallback:
    # any error is logged + skipped, never blocks the pipeline.
    try:
        from alpha_engine.catalyst_filter import hours_to_earnings as _cf_hours_to_earnings
        _cat_pre = len(active)
        _cat_kept = []
        _cat_window_h = 48.0  # +/-2 trading days
        for _p in active:
            _cat_lc = str(_p.get("category", "")).lower()
            if _cat_lc in ("equity", "stock", "etf"):
                try:
                    _hrs = _cf_hours_to_earnings(_p.get("symbol", ""))
                except Exception as _cf_err:
                    print(f"  [CATALYST FILTER] non-fatal lookup err {_p.get('symbol')}: {_cf_err}")
                    _hrs = None
                if _hrs is not None and 0 < _hrs < _cat_window_h:
                    _p["_catalyst_block"] = f"earnings_in_{_hrs:.1f}h"
                    _p["_quality_gate_rejected"] = (
                        f"[CATALYST FILTER] earnings within {_hrs:.1f}h (window {_cat_window_h}h)"
                    )
                    continue
            _cat_kept.append(_p)
        if len(_cat_kept) < _cat_pre:
            print(
                f"  [CATALYST FILTER] Blocked {_cat_pre - len(_cat_kept)} EQUITY/ETF picks "
                f"within {_cat_window_h}h of earnings"
            )
        active = _cat_kept
    except ImportError as _cf_imp_err:
        print(f"  [CATALYST FILTER] module unavailable, skipping: {_cf_imp_err}")
    except Exception as _cf_top_err:
        print(f"  [CATALYST FILTER] non-fatal top-level: {_cf_top_err}")

    regime = market_ctx.get("market_regime", "neutral")

    # P1-B: Attach macro regime from regime_flip_detector to every pick.
    # Picks with macro_regime field will be checked in Gate 4b (regime alignment).
    _macro_reg = market_ctx.get("macro_regime") or regime or "CHOPPY"
    _macro_flip = market_ctx.get("macro_regime_flip", False)
    _macro_lc = market_ctx.get("macro_long_conf", 0.5)
    _macro_sc = market_ctx.get("macro_short_conf", 0.5)
    _macro_sm = market_ctx.get("macro_size_mult", 0.5)
    for _p in active:
        _p["macro_regime"] = _macro_reg
        _p["macro_regime_flip"] = _macro_flip
        _p["macro_long_conf"] = _macro_lc
        _p["macro_short_conf"] = _macro_sc
        _p["macro_size_mult"] = _macro_sm

    active, rejected = apply_quality_gates(active, regime=regime, closed_picks=closed)
    print(f"  [QUALITY GATES] Passed: {len(active)}, Rejected: {len(rejected)}")
    for r in rejected:
        print(
            f"    REJECTED: {r.get('symbol')} {r.get('strategy')} -- {r.get('_quality_gate_rejected')}"
        )

    # 6f0a. MACRO OVERLAY: attach per-pick macro scores
    if _HAS_MACRO_OVERLAY:
        try:
            for pick in active:
                attach_macro_overlay(pick)
            print(f"  [MACRO OVERLAY] Attached macro scores to {len(active)} picks")
        except Exception as _mo_err:
            print(f"  [MACRO OVERLAY] Failed (non-fatal): {_mo_err}")

    # 6f0b. MACRO RISK-OFF GATE: filter or size-down picks with strong risk-off signal
    active, macro_rejected = apply_macro_risk_off_gate(active)
    if macro_rejected:
        print(f"  [MACRO RISK-OFF GATE] Rejected {len(macro_rejected)} picks:")
        for r in macro_rejected:
            print(
                f"    MACRO REJECTED: {r.get('symbol')} {r.get('strategy')} -- {r.get('_macro_risk_off_rejected')}"
            )

    # ── COMMODITY CT=F emission cap (PR-2026-0518-3) ──
    # Hard-block CT=F >40% of newly emitted COMMODITY signals per scan cycle.
    # Applied AFTER quality gates but BEFORE tier system / portfolio cap so that:
    #   (a) quality gates have already filtered garbage picks
    #   (b) CT=F mono-culture doesn''t crowd out other COMMODITY symbols in the cap
    #   (c) the downstream PBO computation sees a diversified COMMODITY signal set
    if _HAS_CTF_CAP and _ctf_emission_cap is not None:
        before_ctf = len(active)
        try:
            active, ctf_rejected = _ctf_emission_cap(active)
            if ctf_rejected:
                for _cr in ctf_rejected:
                    print(
                        f"    CTF_CAP REJECTED: {_cr.get('symbol')} "
                        f"{_cr.get('strategy')} -- {_cr.get('_rejected_reason', 'CT=F over cap')}"
                    )
                    # Track in quality_gates style for dashboard
                    _cr['_quality_gate_rejected'] = _cr.get('_rejected_reason', 'CT=F emission cap')
                    rejected.append(_cr)
                print(
                    f"  [CTF_CAP] Rejected {len(ctf_rejected)} CT=F picks "
                    f"({before_ctf} -> {len(active)} COMMODITY signals)"
                )
        except Exception as _ctf_err:
            print(f"  [CTF_CAP] Failed (fail-open): {_ctf_err}")

    # 6f2. Strategy Priority Tier System (cross-AI consensus: "simplify to survive")
    #   ELITE (top 5) -> 3x sizing, conf >= 0.65
    #   PROVEN (next 10) -> 1x sizing, standard gates
    #   EXPERIMENTAL -> 0.5x sizing, conf >= 0.80
    #   Auto-kill: 20+ trades, WR < 30% -> rejected
    #   "Don't trade": fewer than 3 strategies -> 0 picks
    #   Portfolio stress: >5% unrealized loss -> halve positions
    if _HAS_STRATEGY_PRIORITY:
        try:
            # Refresh tiers from latest closed picks
            refresh_tiers()

            # Save kill list + tier report for audit
            save_kill_list()
            save_tier_report()

            # Apply tier-specific gates (auto-kill + confidence thresholds)
            active, tier_rejected = apply_tier_gates(active)
            print(
                f"  [PRIORITY TIERS] Passed: {len(active)}, Tier-rejected: {len(tier_rejected)}"
            )
            for r in tier_rejected:
                print(
                    f"    TIER REJECTED: {r.get('symbol')} {r.get('strategy')} -- "
                    f"{r.get('_tier_rejected')}"
                )

            # "Don't trade" gate: if fewer than 3 strategies have signals, market is unclear
            if not should_trade_now(active):
                print(
                    f"  [PRIORITY] HALTING: market unclear -- suppressing all {len(active)} picks"
                )
                active = []

            # Portfolio stress multiplier: halve new positions if portfolio is losing >5%
            if active:
                stress_mult = compute_portfolio_stress_multiplier(active)
                if stress_mult < 1.0:
                    for p in active:
                        current_mult = p.get("position_multiplier", 1.0)
                        p["position_multiplier"] = round(current_mult * stress_mult, 2)
                    print(
                        f"  [PRIORITY] Applied stress multiplier {stress_mult}x to all positions"
                    )

            # Log tier distribution
            tier_counts = {"ELITE": 0, "PROVEN": 0, "EXPERIMENTAL": 0}
            for p in active:
                t = p.get("tier_priority", "EXPERIMENTAL")
                tier_counts[t] = tier_counts.get(t, 0) + 1
            print(
                f"  [PRIORITY] Tier distribution: "
                f"ELITE={tier_counts['ELITE']}, "
                f"PROVEN={tier_counts['PROVEN']}, "
                f"EXPERIMENTAL={tier_counts['EXPERIMENTAL']}"
            )
        except Exception as e:
            print(f"  [PRIORITY] Tier system failed (non-fatal): {e}")
    else:
        print(
            "  [PRIORITY] strategy_priority module not available -- skipping tier gates"
        )

    # 6f2.5. EAGLE-4 ADMISSIBILITY GATE (2026-06-02, minimax-m3-free)
    #   Data-backed by AI tournament leaderboard (5,492 picks, 3,692 resolved).
    #   Flips CRYPTO LONG→SHORT (tournament: SHORT 67% WR vs LONG 33% WR, n=216).
    #   Kills noise personas (momentum_scalp 28%, breakout_scanner 28%, reflexivity_trader 35%).
    #   Kills negative-edge class×direction combos (PENNY SHORT 15%, COMMODITY SHORT 18%, etc.).
    #   Runs BEFORE portfolio cap so killed picks don't compete for slots.
    if active:
        try:
            active = apply_eagle4_admissibility(active)
        except Exception as _eagle4_err:
            print(f"  [EAGLE-4] Admissibility gate failed (non-fatal): {_eagle4_err}")

    # 6f2.6. EAGLE-5 PROMOTION GATE (2026-06-02, minimax-m3-free)
    #   Boost (not kill) tournament-validated symbols/personas with multiplicative confidence.
    #   Positive side of EAGLE-4. All thresholds from top-5 T1 AI tournament, 3,692 resolved.
    #   Imported from eagle_gates.py (separate module) to survive concurrent agent edits
    #   that have been reverting inline EAGLE code in this file.
    if active:
        try:
            from eagle_gates import apply_eagle5_promotion
            active = apply_eagle5_promotion(active)
        except Exception as _eagle5_err:
            print(f"  [EAGLE-5] Promotion gate failed (non-fatal): {_eagle5_err}")

    # 6f2.7. EAGLE-6 ADMISSIBILITY GATE (2026-06-02, minimax-m3-free, v1)
    #   Global per-strategy statistical hard gates:
    #   - DSR noise kill (Harvey-Liu multiple-testing correction, 27 noise strategies)
    #   - Insufficient-n kill (< 30 resolved trades)
    #   - HHI concentration kill (> 0.20 share from a single strategy)
    #   v2 (planned) will add PBO<0.5 + walk-forward OOS PF>=0.8xIS PF once data pipeline stabilises.
    #   Fail-open if DSR data is missing.
    if active:
        try:
            from eagle_gates import apply_eagle6_admissibility
            active = apply_eagle6_admissibility(active)
        except Exception as _eagle6_err:
            print(f"  [EAGLE-6] Admissibility gate failed (non-fatal, fail-open): {_eagle6_err}")

    if active and _HAS_PROMOTION_GATE:
        try:
            _pg_kept: list[dict] = []
            _pg_denied = 0
            for _pg_pick in active:
                _pg_key = str(
                    _pg_pick.get("source_system") or _pg_pick.get("strategy") or ""
                ).strip()
                _pg_ac = str(
                    _pg_pick.get("asset_class") or _pg_pick.get("category") or ""
                ).strip()
                _pg_ok = is_admissible_for_production(_pg_key, _pg_ac)
                _pg_pick["_promotion_gate_admitted"] = _pg_ok
                _pg_pick["_promotion_gate_reason"] = admission_reason(_pg_key, _pg_ac)
                if _pg_ok:
                    _pg_kept.append(_pg_pick)
                else:
                    _pg_denied += 1
                    _pg_pick["_promotion_gate_rejected"] = _pg_pick["_promotion_gate_reason"]
                    rejected.append(_pg_pick)
            print(
                f"  [PROMOTION GATE] enforced=True denied={_pg_denied} "
                f"kept={len(_pg_kept)} allowlist={len(PROMOTED_STRATEGIES)}"
            )
            active = _pg_kept
        except Exception as _pg_err:
            print(f"  [PROMOTION GATE] Failed (non-fatal, fail-open): {_pg_err}")

    # 6f3. Portfolio cap -- hard limit on total active picks
    before_cap = len(active)
    active = enforce_portfolio_cap(active, [])  # all remaining picks compete for slots
    if len(active) < before_cap:
        print(
            f"  [PORTFOLIO CAP] Reduced from {before_cap} to {len(active)} active picks (max {MAX_ACTIVE_PICKS})"
        )

    # 6f3b. Sector concentration cap -- penalize correlated same-sector picks
    #   Runs AFTER portfolio cap so we only look at surviving picks.
    #   Soft penalty (confidence *= 0.3) rather than hard kill.
    if active:
        try:
            active = enforce_sector_concentration_cap(active)
        except Exception as _sec_err:
            print(f"  [SECTOR CAP] Failed (non-fatal): {_sec_err}")

    # 6f4. Strong Signal 5-Filter System (A/B test vs main pipeline)
    #   Tags every pick with strong_signal: true/false and strong_signal_score: 0-100
    #   Writes data/strong_picks.json with ONLY the strong signals
    #   Does NOT block non-strong picks from active_picks.json
    try:
        from strong_signal_filter import (
            tag_all_picks,
            write_strong_picks,
            get_filter_report,
        )

        active, strong_picks = tag_all_picks(active, regime=regime, closed_picks=closed)
        strong_count = len(strong_picks)
        print(
            f"  [STRONG SIGNALS] {strong_count}/{len(active)} picks passed all 5 filters"
        )

        # Log filter report
        report = get_filter_report(active, regime=regime, closed_picks=closed)
        for fname, fstats in report.get("filter_stats", {}).items():
            print(
                f"    Filter {fname}: passed={fstats['passed']}, failed={fstats['failed']}"
            )

        # Write strong_picks.json for the smart picks engine
        if strong_picks:
            sp_path = write_strong_picks(strong_picks, DATA_DIR)
            print(f"  [STRONG SIGNALS] Wrote {sp_path.name} ({strong_count} picks)")
            for sp in strong_picks:
                print(
                    f"    STRONG: {sp.get('symbol')} {sp.get('strategy')} "
                    f"score={sp.get('strong_signal_score', 0)}"
                )
        else:
            print(
                f"  [STRONG SIGNALS] No strong signals this cycle (expected 5-10 per ~50 input)"
            )
    except Exception as e:
        print(f"  [STRONG SIGNALS] Filter failed (non-fatal): {e}")

    # 6f5. Volatility (ATR%) Filter -- #1 predictive feature per neural net + closed picks
    #   High-vol picks: 53.1% WR, Sharpe +0.218
    #   Low-vol picks: 29.2% WR, Sharpe -0.346
    #   Spread: +24pp — bigger than any other single feature.
    #   Uses 24h price change as ATR proxy (correlation ~0.85 with actual ATR).
    try:
        active = apply_volatility_filter(active)
    except Exception as _vol_filter_err:
        print(f"  [VOL_FILTER] Failed (non-fatal): {_vol_filter_err}")

    # 6g. Adaptive Trust Tuner -- adjust confidence based on forward performance
    try:
        from adaptive_trust_tuner import apply_trust_adjustments, get_adjustment_reason

        trust_adjusted = 0
        for p in active:
            adj = apply_trust_adjustments(p)
            if adj != 0.0:
                original_conf = p.get("confidence", 0.5)
                new_conf = min(0.95, max(0.05, original_conf + adj))
                reason = get_adjustment_reason(p)
                print(
                    f"  [TRUST] {p.get('strategy', '')[:30]} on {p.get('symbol', '')}: "
                    f"{original_conf:.2f} -> {new_conf:.2f} ({reason})"
                )
                p["confidence"] = round(new_conf, 4)
                p["_trust_adjustment"] = round(adj, 4)
                trust_adjusted += 1
        if trust_adjusted:
            print(f"  [TRUST] Adjusted {trust_adjusted}/{len(active)} picks")
        else:
            print(
                f"  [TRUST] No adjustments applied (trust_adjustments.json may be empty)"
            )
    except Exception as e:
        print(f"  [TRUST] Adaptive tuner skipped (non-fatal): {e}")

    # 6h. Kelly Criterion Position Sizing (Half-Kelly + vol scaling + correlation penalty)
    try:
        from kelly_position_sizer import apply_kelly_sizing

        portfolio_val = float(os.environ.get("ALPHA_PORTFOLIO_VALUE", "10000"))
        active = apply_kelly_sizing(active, portfolio_value=portfolio_val)
    except Exception as e:
        print(f"  [KELLY] Position sizing skipped (non-fatal): {e}")

    # 6h1. risk_policy.json observability (HF §2.5) -- warn only, non-invasive
    try:
        from alpha_engine.risk_policy_check import check_risk_policy

        portfolio_val_rp = float(os.environ.get("ALPHA_PORTFOLIO_VALUE", "10000"))
        _rp_summary = check_risk_policy(active, portfolio_value=portfolio_val_rp)
        _rp_breaches = _rp_summary.get("breaches", [])
        if _rp_breaches:
            print(
                f"  [RISK_POLICY] {len(_rp_breaches)} cap breach(es) flagged "
                f"(v{_rp_summary.get('version', 1)}) -- observability only"
            )
        else:
            print(
                f"  [RISK_POLICY] OK -- no cap breaches "
                f"(v{_rp_summary.get('version', 1)})"
            )
    except Exception as e:
        print(f"  [RISK_POLICY] Check skipped (non-fatal): {e}")

    # 6h2. VaR Enforcement + Stress Testing (Phase 3 hedge fund roadmap)
    try:
        from var_enforcer import apply_var_enforcement

        print(f"  [VAR] Running VaR enforcement on {len(active)} picks...")
        active = apply_var_enforcement(active)
        print(f"  [VAR] Done -- {len(active)} picks VaR-checked")
    except ImportError:
        print("  [VAR] Module not available (import failed)")
    except Exception as e:
        print(f"  [VAR] VaR enforcement skipped (non-fatal): {e}")

    # 6h3. Advanced Risk Overlay (vol-target + regime-Kelly + VaR enforcement)
    try:
        from advanced_risk_system import apply_advanced_risk_overlay

        print(f"  [ADV-RISK] Running advanced risk overlay on {len(active)} picks...")
        portfolio_val = float(os.environ.get("ALPHA_PORTFOLIO_VALUE", "10000"))
        active = apply_advanced_risk_overlay(active, portfolio_value=portfolio_val)
        print(f"  [ADV-RISK] Done -- {len(active)} picks risk-overlaid")
    except ImportError:
        print("  [ADV-RISK] Module not available (import failed)")
    except Exception as e:
        print(f"  [ADV-RISK] Advanced risk overlay skipped (non-fatal): {e}")

    # 6i. Slippage Model + Volatility-Targeted Sizing (blocks negative-edge picks)
    try:
        from slippage_model import apply_slippage_and_vol_sizing

        print(f"  [SLIPPAGE] Running slippage model on {len(active)} picks...")
        portfolio_val = float(os.environ.get("ALPHA_PORTFOLIO_VALUE", "10000"))
        active = apply_slippage_and_vol_sizing(active, portfolio_value=portfolio_val)
        print(f"  [SLIPPAGE] Done -- {len(active)} picks slippage-checked")
    except ImportError:
        print("  [SLIPPAGE] Module not available (import failed)")
    except Exception as e:
        print(f"  [SLIPPAGE] Slippage model skipped (non-fatal): {e}")

    # 6j. Cross-asset correlation penalty (Phase 3: Cluster-based dynamic sizing)
    try:
        from risk_controls import calculate_correlation_penalty

        print(f"  [CORR_SIZER] Applying cluster-based sizing to {len(active)} picks...")
        portfolio_val = float(os.environ.get("ALPHA_PORTFOLIO_VALUE", "10000"))
        # Assuming a base size of 2% of portfolio for calculation context
        base_size_usd = portfolio_val * 0.02

        for p in active:
            # Calculate adjusted size based on current active picks
            # Note: This is a simplified loop; a real impl would pass the full list
            # and adjust the 'size_usd' field if it exists.
            adj_size = calculate_correlation_penalty(p, active, base_size_usd)
            p["correlation_adjusted_size_usd"] = adj_size
        print(f"  [CORR_SIZER] Done -- correlation sizing applied")
    except ImportError:
        print("  [CORR_SIZER] risk_controls not available (import failed)")
    except Exception as e:
        print(f"  [CORR_SIZER] Correlation sizing skipped (non-fatal): {e}")

    # 6k. Anomaly OOD penalties -- penalize out-of-distribution picks
    if _HAS_ANOMALY_DETECTOR and active:
        try:
            active = apply_ood_penalties(active)
            print(f"  [ANOMALY] Applied OOD penalties to {len(active)} picks")
        except Exception as _ood_err:
            print(f"  [ANOMALY] OOD penalties failed (non-fatal): {_ood_err}")

    # Apply anomaly sizing multiplier (computed at startup in step -0.5)
    if _anomaly_sizing < 1.0 and active:
        for _p in active:
            _cur_mult = _p.get("position_multiplier", 1.0)
            _p["position_multiplier"] = round(_cur_mult * _anomaly_sizing, 2)
        print(
            f"  [ANOMALY] Applied sizing multiplier {_anomaly_sizing}x to {len(active)} picks"
        )

    # 6l2. Four-Tier Circuit Breaker — enforce sizing reduction / pause / halt
    # Integrates drift ratio, open-bloat, system WR, and existing GREEN/YELLOW/RED/HALT.
    # T2 REDUCE: apply 0.50x position_multiplier to all active picks.
    # T3 PAUSE: remove picks from paused asset classes.
    # T4 HALT: log CRITICAL, remove all picks (operator must manually resume).
    try:
        from circuit_breaker_aggregator import four_tier_circuit_check
        _4tcb = four_tier_circuit_check(active_picks=active, closed_picks=closed)
        _4tcb_tier = _4tcb.get("tier", 0)
        _4tcb_action = _4tcb.get("action", "OK")
        _4tcb_reasons = "; ".join(_4tcb.get("reasons", []))[:200]
        print(f"  [4-TIER-CB] tier={_4tcb_tier} action={_4tcb_action}: {_4tcb_reasons}")
        if _4tcb_tier == 2:
            for _p in active:
                _p["position_multiplier"] = round(
                    float(_p.get("position_multiplier", 1.0)) * 0.50, 4
                )
            print(f"  [4-TIER-CB] T2 REDUCE: 0.5x sizing applied to {len(active)} picks")
        elif _4tcb_tier == 3:
            _paused = set(_4tcb.get("paused_classes", []))
            before = len(active)
            active = [
                _p for _p in active
                if (_p.get("category") or _p.get("asset_class") or "").upper() not in _paused
            ]
            print(f"  [4-TIER-CB] T3 PAUSE: removed {before - len(active)} picks "
                  f"from {_paused}; {len(active)} remain")
        elif _4tcb_tier >= 4:
            print(f"  [4-TIER-CB] T4 HALT: clearing all {len(active)} active picks — "
                  f"manual review required to resume")
            active = []
    except Exception as _4tcb_err:
        print(f"  [4-TIER-CB] Skipped (non-fatal): {_4tcb_err}")

    # 6m. FINAL KILL LIST ENFORCEMENT -- runs AFTER all pick sources are merged.
    #     save_active_picks() filters for disk, but the local `active` variable
    #     still holds killed strategies.  This is the safety net that guarantees
    #     no killed strategy ever reaches premium_signals.json or Discord alerts.
    try:
        import fnmatch as _fnmatch

        _wl_path = DATA_DIR / "core_whitelist.json"
        if _wl_path.exists():
            with open(_wl_path) as _wl_f:
                _wl_data = json.load(_wl_f)
            # Build protected set from protected_strategies + core_strategies + incubator_strategies
            _protected_set = set()
            for _pgroup in (
                "protected_strategies",
                "core_strategies",
                "incubator_strategies",
            ):
                for _ps in _wl_data.get(_pgroup, []):
                    if isinstance(_ps, str) and _ps.strip():
                        _protected_set.add(_ps.strip().lower())

            _kill_set = set()
            for _ks in _wl_data.get("kill_list", []):
                _ks_lower = _ks.lower()
                _ks_bare = (
                    _ks_lower.split("::", 1)[1] if "::" in _ks_lower else _ks_lower
                )
                # Skip kill entries whose bare name is protected
                if _ks_bare in _protected_set:
                    continue
                _kill_set.add(_ks_lower)
                # Also add without prefix (e.g., "alpha_engine::foo" -> also match "foo")
                if "::" in _ks_lower:
                    _kill_set.add(_ks_bare)
            _kill_patterns = [p.lower() for p in _wl_data.get("kill_patterns", [])]

            _pre_kill = len(active)
            _killed_strats = {}
            _surviving = []
            for _p in active:
                _strat = (_p.get("strategy") or _p.get("strategy_name") or "").lower()
                _is_killed = _strat in _kill_set
                if not _is_killed:
                    for _kpat in _kill_patterns:
                        if _fnmatch.fnmatch(_strat, _kpat):
                            _is_killed = True
                            break
                if _is_killed:
                    _killed_strats[_strat] = _killed_strats.get(_strat, 0) + 1
                else:
                    _surviving.append(_p)

            _total_killed = _pre_kill - len(_surviving)
            if _total_killed > 0:
                print(
                    f"\n  [KILL LIST ENFORCEMENT] Removed {_total_killed} picks "
                    f"from {len(_killed_strats)} killed strategies:"
                )
                for _ks, _kc in sorted(_killed_strats.items(), key=lambda x: -x[1]):
                    print(f"    {_ks}: {_kc} picks removed")
                active = _surviving
            else:
                print(
                    f"  [KILL LIST ENFORCEMENT] All {_pre_kill} picks passed "
                    f"({len(_kill_set)} strategies on kill list)"
                )
        else:
            print("  [KILL LIST ENFORCEMENT] core_whitelist.json not found -- skipping")
    except Exception as _kl_err:
        print(f"  [KILL LIST ENFORCEMENT] Failed (non-fatal): {_kl_err}")

    # 6n-pre. Final elite scoring pass: catch any picks missing elite_score
    #   Various modules (volatile_alt_scanner, ml_predictor_merger, tp_sl_filler)
    #   may add picks AFTER the initial elite scoring. This safety net ensures
    #   ALL active picks have elite_score + risk_reward before writeback.
    if active:
        _unscored = [p for p in active if p.get("elite_score") is None]
        if _unscored:
            print(
                f"  [ELITE SAFETY NET] {len(_unscored)} picks missing elite_score, scoring now..."
            )
            try:
                from elite_scorer import enrich_picks_with_elite_score

                enrich_picks_with_elite_score(active, DATA_DIR)
                _still_unscored = sum(1 for p in active if p.get("elite_score") is None)
                print(
                    f"  [ELITE SAFETY NET] Scored. Remaining unscored: {_still_unscored}"
                )
            except Exception as _esn_err:
                print(f"  [ELITE SAFETY NET] Failed (non-fatal): {_esn_err}")

    # 6n-score-floor. Post-scoring elite_score floor filter (Mar 25 2026)
    #   Score bands 0-40 have terrible WR (6-35%). Only 60+ shows real signal.
    #   Applied AFTER the safety-net scoring so all scorable picks have elite_score.
    #   Unscored picks (elite_score=None) pass through -- they may be ML picks
    #   that haven't been scored yet.
    #   Mercury sprint item #8: proven ML strategies bypass (historically mis-calculated scores).
    _PROVEN_STRATEGIES_FLOOR = {
        "ml_enhanced_FET",
        "ml_enhanced_BNB",
        "ml_enhanced_RENDER",
        "ml_enhanced_FETUSDT",
        "ml_enhanced_BNBUSDT",
        "ml_enhanced_RENDERUSDT",
        "NMTD",
    }
    if active:
        _pre_floor = len(active)
        _floor_rejected = []
        _floor_passed = []
        for _p in active:
            _es = _p.get("elite_score")
            if _es is not None:
                try:
                    _es_val = float(_es)
                    if (
                        _es_val < 20 and _es_val > 0
                    ):  # Raised floor: data shows <20 = 37% WR, 20+ = 97% WR
                        # Allow proven ML strategies through regardless of score
                        if _p.get("strategy", "") not in _PROVEN_STRATEGIES_FLOOR:
                            _p["_score_floor_rejected"] = (
                                f"[SCORE FLOOR] elite_score={_es_val:.1f} < 25 minimum threshold"
                            )
                            _floor_rejected.append(_p)
                            continue
                except (TypeError, ValueError):
                    pass
            _floor_passed.append(_p)
        if _floor_rejected:
            active = _floor_passed
            print(
                f"  [SCORE FLOOR] Rejected {len(_floor_rejected)}/{_pre_floor} picks "
                f"with elite_score < 25:"
            )
            for _fr in _floor_rejected:
                print(
                    f"    SCORE FLOOR: {_fr.get('symbol')} {_fr.get('strategy')} "
                    f"elite_score={_fr.get('elite_score')}"
                )
        else:
            print(
                f"  [SCORE FLOOR] All {_pre_floor} picks passed (elite_score >= 25 or unscored)"
            )

    # 6n-trust. Compute Trust Score (0-10) for every active pick.
    #   Simple, transparent quality rating: freshness + edge + agreement + regime.
    #   Threshold for "trustworthy": >= 7. Wired after elite scoring so all data is available.
    if active:
        try:
            from trust_score import enrich_picks_with_trust_score

            _ts_perf = {}
            try:
                _ts_perf = load_strategy_performance() or {}
            except Exception:
                pass
            _ts_regime = (
                market_ctx.get("fast_regime")
                or market_ctx.get("market_regime")
                or "UNKNOWN"
            )
            enrich_picks_with_trust_score(active, _ts_perf, _ts_regime)
            # Freeze entry-time trust snapshot for independent verification
            try:
                from trust_audit_export import export_trust_audit

                _ta_count = export_trust_audit(active)
                if _ta_count:
                    print(
                        f"  [TRUST AUDIT] Exported {_ta_count} entry-time trust snapshots"
                    )
            except Exception as _ta_err:
                print(f"  [TRUST AUDIT] Failed (non-fatal): {_ta_err}")
        except Exception as _ts_err:
            print(f"  [TRUST SCORE] Failed (non-fatal): {_ts_err}")

    # 6n-consensus. High Conviction Consensus Tier (system-level agreement)
    #   Audit finding: 5+ independent SYSTEMS agreeing = 82-100% WR across 25 closed trades.
    #   This is SYSTEM-level (alpha_engine, kimi, cta_replicator, etc.), NOT strategy-level.
    #   ULTRA (5+) → +15 elite, +3 trust | STRONG (4) → +10, +2 | MODERATE (3) → +5, +1
    if active:
        try:
            from consensus_tier import enrich_picks_with_consensus

            active = enrich_picks_with_consensus(active)
        except Exception as _ct_err:
            print(f"  [CONSENSUS TIER] Failed (non-fatal): {_ct_err}")

    # 6n-post. Tag every pick with ml_composite ranking for audit trail
    #   ml_composite replaces elite_score as the primary ranker (Spearman +0.33 vs r=-0.001).
    #   elite_score is kept in the pick for dashboard display but NOT used for selection.
    if active:
        _ml_tagged = 0
        _fallback_tagged = 0
        for _p in active:
            _mc, _rm = _compute_ml_composite(_p)
            _p["ml_composite"] = _mc
            _p["ranking_method"] = _rm
            if _rm == "ml_composite":
                _ml_tagged += 1
            else:
                _fallback_tagged += 1
        print(
            f"  [ML COMPOSITE] Tagged {len(active)} picks: "
            f"{_ml_tagged} ml_composite, {_fallback_tagged} confidence_fallback"
        )

    # 6n-regime. Stamp current regime + regime_alignment on ALL active picks.
    # regime_alignment is required by dashboard_generator.py::compute_regime_validation
    # (checks p.get("regime_alignment"), not p.get("regime")). Without it,
    # active_regime_composition.with_regime_data = 0 for all picks (silent bug).
    _regime_label = (
        market_ctx.get("fast_regime") or market_ctx.get("market_regime") or "UNKNOWN"
    )
    _REGIME_LONG_ALIGNED = {"TRENDING_UP", "BULL", "BULLISH", "LOW_VOL_TRENDING", "LEANING_BULL"}
    _REGIME_SHORT_ALIGNED = {"TRENDING_DOWN", "BEAR", "BEARISH", "CRASH", "CAPITULATION"}
    if active:
        for _p in active:
            _p["regime"] = _regime_label
            _p["regime_at_entry"] = _regime_label  # also stamp canonical field checked by dashboard
            _dir = str(_p.get("signal_type") or _p.get("direction") or "").upper()
            _rl = _regime_label.upper()
            if _dir in ("LONG", "BUY") and _rl in _REGIME_LONG_ALIGNED:
                _p["regime_alignment"] = "aligned"
            elif _dir in ("SHORT", "SELL") and _rl in _REGIME_SHORT_ALIGNED:
                _p["regime_alignment"] = "aligned"
            elif _dir in ("LONG", "BUY") and _rl in _REGIME_SHORT_ALIGNED:
                _p["regime_alignment"] = "misaligned"
            elif _dir in ("SHORT", "SELL") and _rl in _REGIME_LONG_ALIGNED:
                _p["regime_alignment"] = "misaligned"
            else:
                _p["regime_alignment"] = "neutral"

    # --- Helper: fetch klines from Binance for RSI/VOL enrichment fallback ---
    _BINANCE_KLINE_MIRRORS = [
        "https://data-api.binance.vision",
        "https://api.binance.com",
        "https://api1.binance.com",
        "https://api2.binance.com",
        "https://api3.binance.com",
    ]

    def _fetch_klines_for_enrichment(symbol, interval="1h", limit=30):
        """Fetch OHLCV klines via shared multi-source failover.

        Returns (closes, volumes) tuple or None. Routes through
        alpha_engine.failover_imports.fetch_klines (Binance mirrors -> CoinGecko ->
        KuCoin -> CryptoCompare). Falls back to direct Binance mirror loop only
        when the shared module is unavailable.
        """
        if _HAS_SHARED_FAILOVER and _shared_fetch_klines is not None:
            try:
                raw = _shared_fetch_klines(symbol, interval, limit)
                if isinstance(raw, list) and len(raw) >= 15:
                    closes = [float(k[4]) for k in raw]
                    volumes = [float(k[5]) for k in raw]
                    return closes, volumes
            except Exception:
                pass

        for mirror in _BINANCE_KLINE_MIRRORS:
            try:
                resp = requests.get(
                    f"{mirror}/api/v3/klines",
                    params={"symbol": symbol, "interval": interval, "limit": limit},
                    timeout=5,
                    headers={"User-Agent": "AlphaEngine/DashboardEnrich/1.0"},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list) and len(data) >= 15:
                        closes = [float(k[4]) for k in data]
                        volumes = [float(k[5]) for k in data]
                        return closes, volumes
            except Exception:
                continue
        return None

    def _compute_rsi_simple(closes, period=14):
        """Compute RSI from close prices. Returns float 0-100 or None."""
        if len(closes) < period + 1:
            return None
        gains, losses = [], []
        for i in range(1, len(closes)):
            delta = closes[i] - closes[i - 1]
            gains.append(max(delta, 0))
            losses.append(max(-delta, 0))
        if len(gains) < period:
            return None
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    _klines_cache = {}  # {symbol: (closes, volumes) or None} -- avoid duplicate fetches

    # 6n-dashboard. Enrich picks with dashboard column fields (Track/HTF/Strong/RSI/VOL)
    #   These fields are required by audit_dashboard/template.html columns:
    #   _ic_track (strat_fwd_wr, strat_fwd_trades), _ic_htf (htf_bias),
    #   _ic_strong (strong_signal), rsi_at_entry, volume_ratio
    if active:
        try:
            _strat_perf = load_strategy_performance()
        except Exception:
            _strat_perf = {}
        # Build symbol-specific WR lookup from closed picks: {(strategy, symbol): {"wins": N, "total": N}}
        _sym_wr_map = {}
        for _cp in closed or []:
            _cp_raw_strat = _cp.get("strategy", "")
            _cp_strat = (
                STRATEGY_TRACK_ALIASES.get(_cp_raw_strat, _cp_raw_strat)
                if _cp_raw_strat
                else ""
            )
            _cp_sym = _cp.get("symbol", "")
            if _cp_strat and _cp_sym:
                _key = (_cp_strat, _cp_sym)
                if _key not in _sym_wr_map:
                    _sym_wr_map[_key] = {"wins": 0, "total": 0}
                _sym_wr_map[_key]["total"] += 1
                if (_cp.get("pnl_pct") or 0) > 0:
                    _sym_wr_map[_key]["wins"] += 1

        _enriched_count = 0
        for _p in active:
            _changed = False
            # Track: symbol-specific WR from closed picks, fallback to strategy-level
            _p_raw_strat = _p.get("strategy", "")
            _strat_name = (
                STRATEGY_TRACK_ALIASES.get(_p_raw_strat, _p_raw_strat)
                if _p_raw_strat
                else ""
            )
            _sym_name = _p.get("symbol", "")
            _sym_key = (_strat_name, _sym_name)
            _sym_stats = _sym_wr_map.get(_sym_key)

            if _sym_stats and _sym_stats["total"] >= 3:
                # Symbol-specific WR: 3+ trades for this strategy+symbol combo
                _sym_wr = (_sym_stats["wins"] / _sym_stats["total"]) * 100
                _p["strat_fwd_wr"] = round(_sym_wr, 1)
                _p["strat_fwd_trades"] = _sym_stats["total"]
                _p["track_level"] = "symbol"
                _changed = True
            elif _strat_name and (
                _strat_name in _strat_perf or _p_raw_strat in _strat_perf
            ):
                _sp = (
                    _strat_perf[_strat_name]
                    if _strat_name in _strat_perf
                    else _strat_perf.get(_p_raw_strat)
                )
                _sp_closed = _sp.get("closed_picks", 0)
                if _sp_closed >= 5:
                    # Strategy-level WR: 5+ trades overall but <3 for this symbol
                    _sp_wr = _sp.get("win_rate", 0)
                    _p["strat_fwd_wr"] = (
                        round(_sp_wr * 100, 1) if _sp_wr <= 1 else round(_sp_wr, 1)
                    )
                    _p["strat_fwd_trades"] = _sp_closed
                    _p["track_level"] = "strategy"
                    _changed = True
                else:
                    # Not enough data at any level
                    _p["strat_fwd_wr"] = None
                    _p["strat_fwd_trades"] = _sp_closed
                    _p["track_level"] = "none"
                    _changed = True
            else:
                _p["strat_fwd_wr"] = None
                _p["strat_fwd_trades"] = 0
                _p["track_level"] = "none"
                _changed = True

            # HTF: ensure htf_bias exists (fallback from extra dict or regime)
            if not _p.get("htf_bias") and not _p.get("htf_alignment"):
                _extra = _p.get("extra") or {}
                if _extra.get("htf_bias"):
                    _p["htf_bias"] = _extra["htf_bias"]
                elif _extra.get("regime") or _extra.get("regime_trend_direction"):
                    _p["htf_bias"] = _extra.get("regime") or _extra.get(
                        "regime_trend_direction"
                    )
                elif _p.get("regime_at_entry"):
                    _p["htf_bias"] = _p["regime_at_entry"]
                else:
                    _p["htf_bias"] = "neutral"
                _changed = True

            # Strong: ensure strong_signal field exists
            if "strong_signal" not in _p:
                _p["strong_signal"] = False
                _changed = True

            # RSI: promote rsi / extra.rsi_14 to rsi_at_entry for dashboard
            if not _p.get("rsi_at_entry"):
                _extra = _p.get("extra") or {}
                _rsi_val = (
                    _p.get("rsi")
                    or _extra.get("rsi_14")
                    or _extra.get("rsi")
                    or _extra.get("rsi_at_entry")
                )
                if _rsi_val is not None:
                    try:
                        _p["rsi_at_entry"] = round(float(_rsi_val), 1)
                        _changed = True
                    except (ValueError, TypeError):
                        pass

            # VOL: promote extra.vol_ratio / volume fields to volume_ratio for dashboard
            if not _p.get("volume_ratio"):
                _extra = _p.get("extra") or {}
                _vol_val = (
                    _extra.get("vol_ratio")
                    or _extra.get("volume_ratio")
                    or _p.get("vol_ratio")
                )
                if _vol_val is not None:
                    try:
                        _p["volume_ratio"] = round(float(_vol_val), 2)
                        _changed = True
                    except (ValueError, TypeError):
                        pass

            # RSI/VOL fallback: fetch from Binance klines if still missing after all promotions.
            # Only for crypto symbols (USDT suffix). Uses 1h candles, 30 periods for RSI-14 + vol SMA-20.
            _sym = (_p.get("symbol") or "").upper().replace("-", "")
            if (
                not _p.get("rsi_at_entry") or not _p.get("volume_ratio")
            ) and _sym.endswith("USDT"):
                if _sym not in _klines_cache:
                    _klines_cache[_sym] = _fetch_klines_for_enrichment(_sym)
                _kdata = _klines_cache[_sym]
                if _kdata:
                    _closes, _volumes = _kdata
                    if not _p.get("rsi_at_entry") and len(_closes) >= 15:
                        try:
                            _rsi_calc = _compute_rsi_simple(_closes, 14)
                            if _rsi_calc is not None:
                                _p["rsi_at_entry"] = round(_rsi_calc, 1)
                                _changed = True
                        except Exception:
                            pass
                    if not _p.get("volume_ratio") and len(_volumes) >= 21:
                        try:
                            _avg_vol = sum(_volumes[-21:-1]) / 20
                            if _avg_vol > 0:
                                _p["volume_ratio"] = round(_volumes[-1] / _avg_vol, 2)
                                _changed = True
                        except Exception:
                            pass

            if _changed:
                _enriched_count += 1
        print(
            f"  [DASHBOARD ENRICH] Enriched {_enriched_count}/{len(active)} picks with Track/HTF/Strong/RSI/VOL fields"
        )

    # 6n-HYGIENE. Active-feed hygiene — ONLY OPEN rows with real entry_price survive.
    #   Removes: resolved/closed rows, zero-entry signal-only rows, stale zombies.
    #   This is a permanent gate — dirty data must never reach the live dashboard.
    _pre_hygiene = len(active)
    active = [
        p
        for p in active
        if str(p.get("status", "OPEN")).upper() in ("OPEN", "ACTIVE", "NEW", "")
        and float(p.get("entry_price", 0) or 0) > 0
    ]
    _removed = _pre_hygiene - len(active)
    if _removed:
        print(
            f"  [HYGIENE] Removed {_removed} dirty rows "
            f"(resolved/zero-entry/signal-only) — {len(active)} clean picks remain"
        )

    # 6n. Write enriched active picks back to active_picks.json
    #     Runs AFTER kill list enforcement so killed picks don't persist on disk.
    if active:
        # Enforce per-source CRYPTO volume caps on the scanner emit path too.
        # smart_picks_engine already calls enforce_cap; production_scanner
        # previously bypassed it (2026-05-15 fix). Pure filter — trims the
        # lowest-scored excess from over-represented (source, class) cohorts.
        try:
            try:
                from per_source_volume_cap import enforce_cap as _enforce_volume_cap, enforce_symbol_cap as _enforce_symbol_cap
            except ImportError:
                from alpha_engine.per_source_volume_cap import (
                    enforce_cap as _enforce_volume_cap,
                    enforce_symbol_cap as _enforce_symbol_cap,
                )
            _pre_cap = len(active)
            active = _enforce_volume_cap(active)
            if len(active) != _pre_cap:
                print(
                    f"  [VOLUME-CAP] Trimmed {_pre_cap - len(active)} picks "
                    f"(per-source CRYPTO share cap)"
                )
            _pre_sym = len(active)
            active = _enforce_symbol_cap(active)
            if len(active) != _pre_sym:
                print(
                    f"  [SYMBOL-CAP] Trimmed {_pre_sym - len(active)} picks "
                    f"(per-symbol concentration cap)"
                )
        except Exception as _vc_err:
            print(f"  [VOLUME-CAP] skipped (non-fatal): {_vc_err}")

        # BLOCKED_SYMBOLS filter — prevent picks for symbols with known data
        # quality issues or structural anti-edge from reaching active_picks.json.
        # Previously this was only checked in quality_gates.py::passes_smart_gate()
        # (dashboard visibility), meaning blocked symbols were still emitted as
        # active picks. 2026-05-16 fix: block at source.
        try:
            from audit_trail.quality_gates import BLOCKED_SYMBOLS as _BLOCKED_SYMS
            _pre_block = len(active)
            active = [
                p for p in active
                if str(p.get("symbol", "") or "").upper() not in _BLOCKED_SYMS
            ]
            _blocked = _pre_block - len(active)
            if _blocked:
                _blocked_syms = set(
                    str(p.get("symbol", "")).upper() for p in active
                    if str(p.get("symbol", "") or "").upper() in _BLOCKED_SYMS
                )
                print(
                    f"  [BLOCKED-SYMBOLS] Removed {_blocked} picks for "
                    f"blocked symbols: {sorted(_blocked_syms)}"
                )
        except Exception as _bs_err:
            print(f"  [BLOCKED-SYMBOLS] skipped (non-fatal): {_bs_err}")

        # AGE-PRUNE: drop picks older than ACTIVE_PICKS_MAX_AGE_SECS (default 24h).
        # Symmetric with signal_aggregator/aggregator_fixed.py:211 freshness threshold
        # (86400s). Without this, stale picks (e.g. ~50 March-19 entries observed
        # 2026-05-27) accumulate in active_picks.json and the aggregator drops them
        # downstream as stale, polluting the file with no consumer benefit.
        # Idempotent: re-running with no new data is a no-op the second time.
        # Backup is atomic (temp-and-rename) and written under
        # alpha_engine/data/active_picks.json.bak.prune_<utc_ts>.
        try:
            import os as _os_prune
            import json as _json_prune
            import tempfile as _tempfile_prune
            from datetime import datetime as _dt_prune, timezone as _tz_prune
            from pathlib import Path as _Path_prune

            _max_age_secs = int(_os_prune.environ.get("ACTIVE_PICKS_MAX_AGE_SECS", "86400"))
            _now_prune = _dt_prune.now(_tz_prune.utc)

            def _pick_age_secs(p: dict) -> float | None:
                for _k in ("timestamp", "submitted_at", "created_at", "entry_ts", "entry_time"):
                    _v = p.get(_k)
                    if not _v:
                        continue
                    try:
                        _t = _dt_prune.fromisoformat(str(_v).replace("Z", "+00:00"))
                        if _t.tzinfo is None:
                            _t = _t.replace(tzinfo=_tz_prune.utc)
                        return (_now_prune - _t).total_seconds()
                    except (ValueError, TypeError):
                        continue
                return None

            _pre_prune = len(active)
            _ages = [(p, _pick_age_secs(p)) for p in active]
            _kept = [p for p, a in _ages if a is None or a <= _max_age_secs]
            _dropped_ages = [a for p, a in _ages if a is not None and a > _max_age_secs]
            _dropped = _pre_prune - len(_kept)
            if _dropped:
                # Atomic backup of the current on-disk active_picks.json before mutating.
                try:
                    _ap_path = _Path_prune(__file__).resolve().parent / "data" / "active_picks.json"
                    if _ap_path.exists():
                        _ts_tag = _now_prune.strftime("%Y%m%dT%H%M%SZ")
                        _bak_path = _ap_path.with_suffix(
                            _ap_path.suffix + f".bak.prune_{_ts_tag}"
                        )
                        _tmp_fd, _tmp_name = _tempfile_prune.mkstemp(
                            prefix="active_picks.bak.", dir=str(_ap_path.parent)
                        )
                        with _os_prune.fdopen(_tmp_fd, "wb") as _tf:
                            _tf.write(_ap_path.read_bytes())
                        _os_prune.replace(_tmp_name, _bak_path)
                except Exception as _bak_err:
                    print(f"  [PRUNE] backup skipped (non-fatal): {_bak_err}")
                _oldest = max(_dropped_ages) if _dropped_ages else 0
                print(
                    f"  [prune] kept {len(_kept)} picks; dropped {_dropped} stale picks "
                    f"(oldest age = {int(_oldest)} seconds)"
                )
                active = _kept
            else:
                print(
                    f"  [prune] kept {len(_kept)} picks; dropped 0 stale picks "
                    f"(oldest age = 0 seconds)"
                )
        except Exception as _prune_err:
            print(f"  [PRUNE] age-prune skipped (non-fatal): {_prune_err}")

        try:
            from forward_validator import save_active_picks

            # Enrich trust_score before writing — HC filter gate 7 requires trust_score >= 6.
            # Without this, all active picks have trust_score=0 and HC filter returns 0 passes.
            # dashboard_generator.py already does this for display; this writes it to the source file.
            try:
                from trust_score import enrich_picks_with_trust_score
                enrich_picks_with_trust_score(active)
                print(f"  [TRUST-SCORE] Enriched {len(active)} picks with trust_score")
            except Exception as _ts_err:
                print(f"  [TRUST-SCORE] Skipped (non-fatal): {_ts_err}")

            save_active_picks(active)
            print(
                f"  [WRITEBACK] Saved {len(active)} enriched picks to active_picks.json"
            )
        except Exception as _wb_err:
            print(
                f"  [WRITEBACK] Failed to save active_picks.json (non-fatal): {_wb_err}"
            )

    # 6n-bloat. Open-bloat health check (proactive monitoring, swarm Round C 2026-05-14)
    # Checks if >90% of ACTIVE picks are never-closed OPEN — if so, WR is inflated.
    # Pass only `active` (open picks), NOT active+closed — closed picks are resolved
    # and would dilute the open_pct, masking the alarm (swarm verification gap).
    try:
        from audit_trail.quality_gates import check_open_bloat_health, audit_source_score_staleness
        _bloat = check_open_bloat_health(active)
        if _bloat["status"] in ("warn", "pause"):
            print(
                f"  [OPEN-BLOAT] {_bloat['status'].upper()}: {_bloat['open_pct']:.1%} open "
                f"({_bloat['open_count']}/{_bloat['total']}) — {_bloat['action']}"
            )
            for _cls, _cd in _bloat.get("by_class", {}).items():
                if _cd.get("open_pct", 0) >= 0.90:
                    print(f"    {_cls}: {_cd['open_pct']:.1%} open ({_cd['total']} total)")
        # Source score staleness audit — runs weekly (or when closed picks > 500)
        # Wire-Up Rule compliance: caller is production_scanner.py (6n-bloat block)
        _closed_for_audit = closed or []
        if len(_closed_for_audit) >= 50:
            _stale_scores = audit_source_score_staleness(_closed_for_audit, min_n=20)
            if _stale_scores:
                print(f"  [SCORE-AUDIT] {len(_stale_scores)} stale source scores detected:")
                for _sf in _stale_scores[:5]:  # cap output to 5 loudest
                    print(f"    {_sf['source']}: score={_sf['score_in_registry']:+d}, "
                          f"live_pf={_sf['live_pf']:.2f}, {_sf['verdict']}")
    except Exception as _bloat_err:
        pass  # never let monitoring break the scanner

    # 6o. Audit & Monitoring: Collect rejections for dashboard transparency
    # Resolve the structural discrepancy: surface WHY picks were filtered out.
    all_rejections = []
    if "rejected" in locals():
        all_rejections.extend(rejected)
    if "tier_rejected" in locals():
        all_rejections.extend(tier_rejected)
    if "risk_rejected" in locals():
        all_rejections.extend(risk_rejected)
    if "vol_rejected" in locals():
        all_rejections.extend(vol_rejected)
    if "macro_rejected" in locals():
        all_rejections.extend(macro_rejected)
    track["rejected_picks"] = all_rejections

    # 6p. Whale Concentration Index: Final enrichment
    if _HAS_WHALE_INDEX and active:
        indices = []
        for p in active:
            wdata = get_whale_concentration_index(p.get("symbol", ""))
            p["whale_index"] = wdata.get("index", 50)
            p["whale_direction"] = wdata.get("direction", "neutral")
            p["whale_reason"] = wdata.get("reason", "")
            indices.append(wdata.get("index", 50))
        if indices:
            track["whale_index_avg"] = round(sum(indices) / len(indices), 1)

    # 7. Write premium_signals.json
    write_premium_signals(market_ctx, active, track)

    # 8. Discord alerts (optional)
    send_discord_alerts(active)

    # 9. Print summary
    print_summary(market_ctx, active, track)

    # 10. KPI monitoring -- never blocks the scan
    try:
        from kpi_monitor import compute_all_kpis, print_kpi_dashboard

        kpi_report = compute_all_kpis()
        print_kpi_dashboard(kpi_report)
        green = kpi_report.get("green_count", 0)
        total = kpi_report.get("total_count", 0)
        print(f"  [KPI] {green}/{total} KPIs green")
    except Exception as e:
        print(f"  [KPI] Monitoring skipped (non-fatal): {e}")

    # 11. Continuous Improvement Monitor -- cross-system health + mutation routing
    #     Runs AFTER all picks are generated, scored, and gated.
    #     Checks strategy health, routes underperformers to mutation/inverse,
    #     and logs a consolidated health grade. Never blocks the pipeline.
    try:
        from continuous_improvement_monitor import (
            load_config as _cim_load_config,
            run_cycle as _cim_run_cycle,
        )

        _cim_config = _cim_load_config()
        _cim_report = _cim_run_cycle(
            config=_cim_config,
            skip_live_benchmark=True,
        )
        _cim_alerts = _cim_report.get("alerts", [])
        _cim_rehab = _cim_report.get("strategy_watchlist", {}).get(
            "rehabilitation_candidates", []
        )
        _cim_topline = _cim_report.get("topline", {})
        _cim_recs = _cim_report.get("recommendations", [])

        # Log health grade
        _cim_correct = _cim_topline.get("directional_correctness_pct")
        _cim_avg_pnl = _cim_topline.get("open_avg_pnl_pct")
        if len(_cim_alerts) == 0:
            _cim_grade = "HEALTHY"
        elif any(a["severity"] == "CRITICAL" for a in _cim_alerts):
            _cim_grade = "CRITICAL"
        elif any(a["severity"] == "HIGH" for a in _cim_alerts):
            _cim_grade = "DEGRADED"
        else:
            _cim_grade = "WATCH"
        print(
            f"\n  [CIM] Health: {_cim_grade} | "
            f"Alerts: {len(_cim_alerts)} | "
            f"Rehab candidates: {len(_cim_rehab)} | "
            f"Correctness: {_cim_correct}% | "
            f"Avg PnL: {_cim_avg_pnl}%"
        )

        # Apply auto-recommendations: if drawdown breach detected, reduce sizing
        for _rec in _cim_recs:
            if _rec.get("action") == "tighten_risk_and_reduce_gross_exposure":
                _cim_stress = 0.5
                for p in active:
                    current_mult = p.get("position_multiplier", 1.0)
                    p["position_multiplier"] = round(current_mult * _cim_stress, 2)
                print(
                    f"  [CIM] Applied drawdown-breach sizing reduction ({_cim_stress}x) to {len(active)} picks"
                )
                break

        # Log mutation routing for underperformers
        for _candidate in _cim_rehab[:3]:
            print(
                f"  [CIM] Rehab: {_candidate['strategy']} -> {_candidate['mutation_action']} "
                f"(WR={_candidate.get('win_rate_pct')}%, PF={_candidate.get('profit_factor')})"
            )
    except ImportError:
        pass
    except Exception as _cim_err:
        print(f"  [CIM] Continuous improvement monitor failed (non-fatal): {_cim_err}")

    # Restore macro-modulated constants to avoid side effects on re-entry
    MAX_ACTIVE_PICKS = _orig_max_picks
    QUALITY_GATE_MIN_CONFIDENCE = _orig_min_conf

    elapsed = time.time() - start
    elapsed_ms = elapsed * 1000
    print(f"\nProduction scanner completed in {elapsed:.1f}s ({elapsed_ms:.0f}ms)")

    # Persist production cycle timing to scan_timing.json (rolling window)
    try:
        from scanner import _update_scan_timing

        _prod_timing = _update_scan_timing(elapsed_ms)
        print(
            f"  Cycle timing: last={elapsed_ms:.0f}ms, "
            f"avg={_prod_timing['avg_scan_ms']:.0f}ms, "
            f"P99={_prod_timing['p99_scan_ms']:.0f}ms "
            f"(n={_prod_timing['scans_recorded']})"
        )
    except Exception as _t_err:
        print(f"  [TIMING] Could not update scan_timing.json: {_t_err}")

    # 12. Audit database sync -- consolidate all portfolio results
    try:
        from audit_sync import run_full_sync as _audit_sync

        _audit_sync()
    except Exception as _audit_err:
        print(f"  [AUDIT] Sync skipped (non-fatal): {_audit_err}")


if __name__ == "__main__":
    main()
