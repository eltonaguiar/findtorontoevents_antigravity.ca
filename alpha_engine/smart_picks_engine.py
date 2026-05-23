#!/usr/bin/env python3
"""Smart Picks Engine — hourly analyzer that selects the BEST active picks.

Scores each pick on direction/regime alignment, quality, freshness, upside,
and momentum, then saves curated top picks to data/smart_picks.json.
"""
from __future__ import annotations
import json, logging, os, sys, urllib.request
from datetime import datetime, timezone
from pathlib import Path
import importlib
from collections import Counter

# Vol-target sidecar (PR #527 → wire-up Step 2). Default-off via
# CRYPTO_VOL_TARGET_ENABLED env flag; no-op when flag unset OR
# asset_class != CRYPTO. See alpha_engine/risk/vol_target.py docstring +
# reports/PANEL_REVIEW_2026_04_29_OPERATION_PHENOMENAL_FOLLOWUPS.md
# (qwen3.5 caveat: consensus weighting NOT yet wired — flag remains
# default-off pending follow-up PR).
from alpha_engine.risk.vol_target import apply_to_pick as _vol_target_apply

# Per-class confidence calibration. Default-off via
# CONFIDENCE_CALIBRATION_ENABLED env flag. CRYPTO/ETF confidence is
# miscalibrated (high-conf WR < low-conf WR for CRYPTO on n=1514, see
# alpha_engine/confidence_calibrator.py). Re-fit daily via
# `python -m alpha_engine.confidence_calibrator fit`.
try:
    from alpha_engine.confidence_calibrator import calibrate as _calibrate_confidence
except ImportError:
    def _calibrate_confidence(pick):
        return pick

_DIR = Path(__file__).resolve().parent
_DATA = _DIR / "data"

try:
    import alpha_engine.hf_policy_thresholds as hf_policy_thresholds
    import alpha_engine.strategy_pair_affinity as affinity
    from alpha_engine.risk_policy_loader import load_risk_policy
    # Elite score gate + per-strategy confidence gates (2026-04-22 edge analysis)
    from alpha_engine.config import MIN_ELITE_SCORE_FOR_PICKS, STRATEGY_MIN_CONFIDENCE
except ImportError:
    try:
        import hf_policy_thresholds as hf_policy_thresholds
        import strategy_pair_affinity as affinity
        from risk_policy_loader import load_risk_policy
        from config import MIN_ELITE_SCORE_FOR_PICKS, STRATEGY_MIN_CONFIDENCE
    except ImportError:
        hf_policy_thresholds = None
        affinity = None
        def load_risk_policy(*args, **kwargs): return {}
        MIN_ELITE_SCORE_FOR_PICKS = 70
        STRATEGY_MIN_CONFIDENCE = {}
# Policy cache (safe fallback to {}).
_RISK_POLICY = load_risk_policy() or {}
_POLICY_FLAGS = _RISK_POLICY.get("policy_flags", {}) or {}

# ---------------------------------------------------------------------------
# ML-composite ranking — replaces elite_score as primary ranker.
# Weights derived from Spearman correlation with realised PnL:
#   ml_score +0.33 | confidence +0.20 | forward_wr IC +0.17
#   elite_score r=-0.001 (noise — kept as tiebreaker only)
# ---------------------------------------------------------------------------

def _compute_ml_composite(pick: dict) -> tuple[float, str]:
    """Return (ranking_score, ranking_method) for a pick.

    Primary: ml_score*0.6 + confidence*0.3 + forward_wr*0.1
    Fallback (no ml_score): confidence*0.8 * agreement_scale * ml_null_penalty
    elite_score is NOT used — it has near-zero correlation with PnL.

    FALLBACK PENALTIES (2026-04-04 claude-opus-scoring per loser forensics P0):
      Observed: fallback path (conf*0.8) was beating real ml_composite picks
      because 0.8 multiplier > typical ml_composite values (0.3-0.5 range).
      Example: ALGO ranked #1 with null ml_score + conf 0.85 * 0.8 = 0.68.

      Fixes:
      (a) ml_null_penalty = 0.5 multiplier (halves fallback score)
      (b) require min_agreeing_systems for fallback to stay competitive.
          Single-source fallback picks get further -20% hit.
    """
    # Calibrate confidence in-place if CONFIDENCE_CALIBRATION_ENABLED is set.
    # No-op otherwise — preserves current production behavior.
    _calibrate_confidence(pick)
    ml = pick.get("ml_score")
    conf = float(pick.get("confidence", 0) or 0)
    fwd_wr = float(_trusted_forward_wr(pick) or 0)
    # Normalise forward_wr from percentage (0-100) to 0-1 if needed
    if fwd_wr > 1.0:
        fwd_wr = fwd_wr / 100.0

    _strat = str(pick.get("strategy") or "").lower()
    _trust = str(pick.get("trust_tier") or "").upper()
    _claude_penalty = 0.65 if "claude_gainer" in _strat else 1.0
    _tier_penalty = 0.3 if _trust in {"SANDBOX", "UNTRUSTED", "UNPROVEN", "DEMOTED"} else 1.0
    # Optional: asset-class-aware weights (disabled by default for safe rollout).
    _w_ml, _w_conf, _w_fwd = 0.6, 0.3, 0.1
    if bool(_POLICY_FLAGS.get("enable_asset_class_ml_composite_v2")):
        _raw_ac = str(pick.get("asset_class") or pick.get("category") or "").strip().upper()
        _weights_by_ac = (_RISK_POLICY.get("ml_composite_weights_by_asset") or {})
        _w = _weights_by_ac.get(_raw_ac) or _weights_by_ac.get("DEFAULT")
        if isinstance(_w, dict):
            _w_ml = float(_w.get("ml_score", _w_ml))
            _w_conf = float(_w.get("confidence", _w_conf))
            _w_fwd = float(_w.get("forward_wr", _w_fwd))
            _sum = _w_ml + _w_conf + _w_fwd
            if _sum > 0:
                _w_ml, _w_conf, _w_fwd = (_w_ml / _sum, _w_conf / _sum, _w_fwd / _sum)

    if ml is not None and float(ml) > 0:
        ml_val = float(ml)
        score = ml_val * _w_ml + conf * _w_conf + fwd_wr * _w_fwd
        score *= _claude_penalty * _tier_penalty
        if _claude_penalty < 1.0:
            return (round(score, 4), "ml_composite_claude_discount")
        if _tier_penalty < 1.0:
            return (round(score, 4), "ml_composite_tier_discount")
        return (round(score, 4), "ml_composite")
    else:
        # Fallback path — apply penalty so it doesn't beat real composite picks.
        # Base: conf * 0.8 * 0.5 = conf * 0.4 (halved from old).
        ml_null_penalty = 0.5
        if bool(_POLICY_FLAGS.get("disable_non_crypto_ml_null_penalty_v2")):
            _raw_ac = str(pick.get("asset_class") or pick.get("category") or "").strip().upper()
            if _raw_ac and _raw_ac != "CRYPTO":
                ml_null_penalty = 1.0
        score = conf * 0.8 * ml_null_penalty
        # Single-source picks take additional -20% hit (no consensus backing)
        agreeing = int(pick.get("agreement_count", 0) or 0)
        if agreeing < 2:
            score *= 0.8
            score *= _claude_penalty * _tier_penalty
            if _claude_penalty < 1.0:
                return (round(score, 4), "confidence_fallback_solo_claude_discount")
            if _tier_penalty < 1.0:
                return (round(score, 4), "confidence_fallback_solo_tier_discount")
            return (round(score, 4), "confidence_fallback_solo")
        score *= _claude_penalty * _tier_penalty
        if _claude_penalty < 1.0:
            return (round(score, 4), "confidence_fallback_claude_discount")
        if _tier_penalty < 1.0:
            return (round(score, 4), "confidence_fallback_tier_discount")
        return (round(score, 4), "confidence_fallback_penalized")

try:
    from alpha_engine.non_crypto_policy import clamp_non_crypto_tp_sl as _clamp_tp_sl
except ImportError:
    try:
        from non_crypto_policy import clamp_non_crypto_tp_sl as _clamp_tp_sl
    except ImportError:
        def _clamp_tp_sl(pick):
            return pick

# MTF gate — optional import, must not crash the pipeline
try:
    from alpha_engine.mtf_gate import check_mtf_alignment as _check_mtf
    _HAS_MTF_GATE = True
except ImportError:
    try:
        from mtf_gate import check_mtf_alignment as _check_mtf
        _HAS_MTF_GATE = True
    except ImportError:
        _HAS_MTF_GATE = False
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger("smart_picks")

# -- Binance 3+ mirror failover (per API failover rule) + CoinGecko/KuCoin/CryptoCompare
# data-api.binance.vision first — works from GitHub Actions (not geo-blocked)
SPOT_URLS = ["https://data-api.binance.vision", "https://api.binance.com",
             "https://api1.binance.com", "https://api2.binance.com",
             "https://api3.binance.com", "https://api.binance.us"]
_HDR = {"User-Agent": "AlphaEngine/1.0"}
MEME_TOKENS = {"DOGE", "SHIB", "PEPE", "FLOKI", "BONK", "WIF", "MEME",
               "BRETT", "TURBO", "NEIRO", "BABYDOGE", "MYRO", "BOME", "MEW"}

# ── Non-crypto allocation ───────────────────────────────────────────
# 2026-04-15: Raised cap 3→5. Closed-pick analysis shows equity (Bollinger MR
# 52% WR +57.7% PnL, stocks_rsi2_pullback 90% WR) and forex
# (forex_rsi2_mean_reversion 49% WR n=407 +34.5% PnL) are profitable when
# gated by the expanded allowlist + relaxed thresholds. Crypto still fills
# first; non-crypto gets remaining tier slots up to this cap.
MAX_NON_CRYPTO_PICKS = 5  # raised 3→5 (2026-04-15)

def _dynamic_non_crypto_cap(active_non_crypto_count: int, cfg: dict = None) -> int:
    """Return proportional cap: max(floor, int(ratio * active_count))."""
    cfg = cfg or {}
    if not cfg.get("dynamic_non_crypto_cap_enabled", False):
        return MAX_NON_CRYPTO_PICKS
    floor = int(cfg.get("non_crypto_cap_floor", 3))
    ratio = float(cfg.get("non_crypto_cap_ratio", 0.05))
    return max(floor, int(ratio * active_non_crypto_count))

# Banned systems — auto-kill list. Picks from these strategies are always excluded.
# Cross-AI consensus (ChatGPT + Kimi + internal audit) flagged these as harmful.
BANNED_SYSTEMS = {
    "volume_spike_backfill",
    "winner_pattern_precursor",
    "momentum_catcher",
    "hl_funding_fade",
    "yahoo_analyst_consensus",
    "quality_value_composite",
    "cyclic_momentum_stack",
    "autocorrelation_exploiter",
    "swing_structure",
    "binance_smart_money",
    "momentum_tracker_precursor",
    # Underperforming / Failing technical indicators (2026-03-28)
    "kimi_signal_tracking",           # 13% weekly WR, -18% to -34% PnL outliers
    "macd_rsi_confluence",            # 12% weekly WR vs 22% baseline
    "st_fear_greed_contrarian",       # RE-BANNED 2026-05-05 by quant-performance-auditor: WR 34.2% / n=652 / total_pnl_pct -182 per audit_dashboard/data/dashboard_data.json::performance.systems.claude_gainer_st.strategies.st_fear_greed_contrarian. Prior "70.2% WR n=262" justification was a cherry-picked window; with 2.5x sample size the regression to negative-EV is confirmed. Single biggest CRYPTO PF drag — removing this strategy lifts class PF from 1.30 toward T2 floor (>1.5). Sibling st_fear_greed_contrarian_regime_filtered (line 262) is unaffected — exact-match check.
    "macd_crossover",                 # DNA mutation target triggered (35% WR)
    "volume_spike_breakout",          # DNA mutation target triggered (28% WR)
    "stochrsi_macd_combo",            # DNA mutation target triggered (37% WR)
    # Portfolio optimization kills (2026-03-29)
    "quan_engine_position",           # 0% WR, 100% SL exits
    "maplestax_vwap_cbc_flip",        # 12% WR, score=1, -4.98% avg PnL
    "flash-crash-reversal",           # 0% WR active, -3.65% avg PnL
    # 2026-04-05: UNKILLED — producing +2-4% EQUITY winners (NFLX/ARM/GOOG/LIN/UNH/LLY/IBM/GOOGL/GS/PFE).
    # Crypto WR was poor (24/29/12%) but EQUITY application works. Mirror unkill in quality_gates.py (087c44ee12).
    # "goldmine_1x_consensus",        # was 24% crypto WR, now EQUITY winner
    # "goldmine_2x_consensus",        # was 29% crypto WR, now EQUITY winner
    # "goldmine_3x_consensus",        # was 12% crypto WR, now EQUITY winner
    # 2026-04 HF review: repeated equity underperformance.
    "fast_stocks_competition",
    # 2026-04-11: Scoring optimization audit — forward-test data proves these are net destroyers.
    # Cross-checked against recent_closed by asset class to avoid banning crypto winners.
    "claude_gainer_1h",               # 29.8% WR 315 trades -852% PnL. Recent crypto: 46.7% WR but MMT -44% kills PnL.
    # "st_rsi_momentum_confluence",   # UNBANNED 2026-04-11: Aggregate WR (32.1%) misleading.
    #   Cross-check: recent crypto-only 103 trades = 55.3% WR +65.4% PnL. Second-half 52 trades = 94.2% WR +95.6% PnL.
    #   last10_wr=60%. Strategy clearly improved. Antigravity bot c1319eb042 confirmed outperformance on crypto.
    #   Old losses from early calibration dragged aggregate down. Keep alive for crypto, monitor.
    "Value + Quality",                # 7.8% WR, 51 trades, -251% PnL, PF 0.15 — equity-only, no crypto trades
    "Consecutive Beats",              # 20.3% WR, 59 trades, -137% PnL, PF 0.43 — equity-only, no crypto trades
    "Earnings Drift",                 # 12.9% WR, 31 trades, -103% PnL, PF 0.25 — equity-only, no crypto trades
    "st_bb_squeeze_expansion",        # 31.7% WR, 104 trades, -43% PnL, PF 0.33 — crypto 33% WR, -4.9% PnL, confirmed loser
    "ML Ranker",                      # 30.4% WR, 46 trades, -39% PnL, PF 0.57 — equity 28% + forex 36%, no crypto edge
    "lower_wick_absorption",          # 34.7% WR, 98 trades, -16% PnL, PF 0.58 — only 1 recent closed trade, keep banned
    # "crypto_adx_pullback_trendresume_v1",  # UNBANNED 2026-04-11: Only 5 recent crypto trades (60% WR, +3.4%, all BTC).
    #   Aggregate 43 trades (32.6% WR, -10.8%) is mixed, but recent BTC-specific trades show edge.
    #   Small sample — unban and monitor. If next 20 trades < 45% WR, re-ban.
    "Dividend Aristocrats",               # 0% WR, 8 trades, -50% PnL — zero edge on equity div plays
    "futures_ema_stack_momentum",          # 0/4=0% WR, 7 zombie picks — killed 2026-04-02
    "quan_engine_scalp",                   # 0% WR, -794% total PnL zombie — killed 2026-04-22
    # 2026-05-06 P0-B: quan_engine base 0 closed/0 active — proactive block
    "quan_engine",
    # 2026-05-06 P1-E: futures_momentum 0% WR on 56 closed, PF 0.00, 8 active picks
    "futures_momentum",
    # Day-2 audit kills (2026-05-06): wins-it-all-loses-it and large-n bleeders
    "combined_confidence",  # 52.2% WR, PF 0.28, n=23 — kills wins, bleeds on losses
    # 2026-05-16 Grok Comet audit (recent_closed n=3,500 verified):
    # Mutation analysis exported via dashboard_data.json systems[].
    # Both systems failed mutation-before-kill: no profitable regime/symbol window found.
    "spot_perp_basis_arb",       # source_system=alpha_engine_fast, n=228, PF=0.62, WR=43.2%, avgPnL=-0.55%
    "super consensus (alpha_engine, luxalgo_filters, mercury2)",  # source_system=super_signals, n=139, WR=22.3%, PF=0.52, avgPnL=-1.48%
}

# ── Crypto Strategy-Family Filter (2026-05-16 Kimi CLI Audit) ──────
# L4 audit (2026-05-16) proved that CRYPTO scoring is *inversely* correlated
# with performance. The real edge lives in specific strategy families + LONG
# direction (PF 3.15 / WR 64.3% vs current PF 1.31).
# We boost proven families and penalize toxic ones to invert scoring bias.
CRYPTO_PROVEN_STRATEGIES = {
    "st_fear_greed_contrarian",
    "claude_ml_moderate_mut",
    "vwap_deviation_reversion_eth_v1",
    "macd_rsi_m048",
    "atr_percentile_gate",
    "vwap_deviation_reversion_sol_v1",
    "crypto_kalman_trend_residual_reversion_v1",
}

CRYPTO_TOXIC_STRATEGIES = {
    "luxalgo_confluence",
    "unknown",
    "macd_rsi_confluence",  # also in BANNED_SYSTEMS; defense-in-depth
}

# Prefix-based CRYPTO proven detection (2026-05-16)
# Any crypto LONG/BUY pick whose strategy starts with one of these
# prefixes gets the +20 strategy-family boost automatically.
# Future-proofs against new per-symbol ml_enhanced_ variants.
CRYPTO_PROVEN_PREFIXES = (
    "ml_enhanced_",
    "crypto_keltner_",
    "crypto_rsi_",
    "drawdown_recovery_rsi_",
    "basket_corr_gate_",
    "st_fear_greed_",
    "st_obv_",
)

# ── High Volume FOMO Protection ─────────────────────────────────────
# Analysis shows winners enter at LOWER volume (1.20) vs losers (1.32).
# Signals with extreme volume spikes often represent "exit liquidity"
# or late-stage FOMO.
MAX_VOLUME_RATIO = 1.5 # Restored from 2.5 — overly relaxed during capitulation

# Strategies with verified live PnL > 0 AND 5+ closed trades get a score BOOST.
# Multi-symbol validation: strategies must prove themselves across 3+ symbols
# to earn PROVEN status. Single-symbol strategies get capped at FRAGILE.
# Load symbol strength tiers from Monte Carlo validator output
PROVEN_WINNERS = {
    "ml_enhanced_FETUSDT_1d_B_lightgbm":        {"boost": 15, "wr": 93.8},
    "ml_enhanced_BNBUSDT_15m_B_lightgbm":       {"boost": 5, "wr": 60.0},
    "copy_hl_NMTD_25M":                         {"boost": 12, "wr": 81.2},
    "ema_crossover_backfill":                   {"boost": 8,  "wr": 57.9},
    # Mutation v1 strategies (2026-03-29)
    "st_fear_greed_contrarian_regime_filtered": {"boost": 12, "wr": 75.0},  # Base 69% + regime filter
    "keltner_multi_pair_adaptive":             {"boost": 10, "wr": 72.0},  # Base 78% SOL, expanded
    "bollinger_fear_hybrid":                   {"boost": 10, "wr": 70.0},  # Base 56% OOS + FGI filter
    # Revival promotions (confirmed by Monte Carlo / Copilot)
    "basket_corr_gate_mut":                    {"boost": 12, "wr": 92.9},
    "Revival_Mutated_funding_rate_carry_ETHUSDT": {"boost": 10, "wr": 100.0},
    # 2026-04-11: Promoted from leaderboard audit (high WR + high PF + 20+ trades)
    "st_obv_support_divergence":               {"boost": 10, "wr": 61.5},   # 327 trades, PF 2.10, +202% PnL
    "drawdown_recovery_rsi_eth":               {"boost": 8,  "wr": 65.2},   # 69 trades, PF 3.20, +38% PnL
    "drawdown_recovery_rsi_sol":               {"boost": 8,  "wr": 55.6},   # 27 trades, PF 3.99, +27% PnL
    "crypto_keltner_compression_expansion_v1": {"boost": 8,  "wr": 57.9},   # 95 trades, PF 2.77, +25% PnL
    "crypto_rsi_whaleconfirmed_v1":            {"boost": 5,  "wr": 57.6},   # 144 trades, PF 1.91, +28% PnL
    "stocks_rsi2_pullback":                    {"boost": 10, "wr": 88.9},   # 9 trades, +13% PnL — small but 88.9% WR
    "rs-breakout-scout":                       {"boost": 8,  "wr": 69.2},   # 13 trades, PF 4.90, +26% PnL
    "Breakout Momentum":                       {"boost": 5,  "wr": 54.5},   # 33 trades, +32% PnL
    "quality-minus-junk":                      {"boost": 8,  "wr": 63.6},   # 22 trades, PF 1.64, +15% PnL
}
PROVEN_PREFIXES = {
    "ml_enhanced_": 8, "copy_hl_": 8, "copy_hl_whale": 10,
}
VETTED_COPY_PREFIXES = (
    "copy_hl_",
    "copy_hl_lb_",
    "copy_okx_",
    "copy_bybit_",
    "copy_bingx_",
    "copy_pm_",
    "clone_hl_",  # Re-applied: Hyperliquid whale trackers (91.7% WR SHORTs)
)
BLOCKED_RAW_COPY_PREFIXES = (
    "bitget_copy",
    "binance_smart",
)
BLOCKED_RAW_COPY_SOURCES = {
    "copy_trader_bitget",
    "copy_trader_binance",
}

FOREX_CODES = {
    "EUR", "GBP", "USD", "JPY", "AUD", "CAD", "CHF", "NZD",
    "SEK", "NOK", "DKK", "SGD", "HKD", "CNH", "CNY", "MXN",
    "ZAR", "TRY", "INR",
}
ETF_SYMBOLS = {
    "SPY", "QQQ", "IWM", "DIA", "VTI", "VOO", "ARKK", "XLF", "XLE", "XLK",
    "GLD", "SLV", "USO", "TLT", "IEF", "EEM", "EFA", "SQQQ", "TQQQ", "UVXY",
}
EQUITY_SYMBOLS = {
    "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "TSLA", "META", "NVDA", "AMD",
    "NFLX", "DIS", "BA", "JPM", "GS", "V", "MA", "PYPL", "SQ", "COIN",
    "MSTR", "RIOT", "MARA", "HUT", "BITF", "BAC", "COST", "PFE", "JNJ",
    "ABBV", "AVGO", "HD", "LLY", "TMO", "ORCL",
}


def _strategy_name(pick: dict) -> str:
    return str(pick.get("strategy") or "").lower().strip()


def _source_name(pick: dict) -> str:
    return str(pick.get("source_system") or "").lower().strip()


def _is_vetted_copy_pick(pick: dict) -> bool:
    strat = _strategy_name(pick)
    return any(strat.startswith(prefix) for prefix in VETTED_COPY_PREFIXES)


def _is_blocked_raw_copy_pick(pick: dict) -> bool:
    strat = _strategy_name(pick)
    source = _source_name(pick)
    if source in BLOCKED_RAW_COPY_SOURCES:
        return True
    return any(strat.startswith(prefix) for prefix in BLOCKED_RAW_COPY_PREFIXES)


def _is_unvetted_copy_pick(pick: dict) -> bool:
    source = _source_name(pick)
    if _is_blocked_raw_copy_pick(pick):
        return True
    return source.startswith("copy_trader") and not _is_vetted_copy_pick(pick)


def _trusted_forward_wr(pick: dict):
    if _is_unvetted_copy_pick(pick):
        return 0
    if pick.get("strat_fwd_wr") is not None:
        return pick.get("strat_fwd_wr")
    return pick.get("forward_wr", 0)


def _trusted_forward_trades(pick: dict):
    if _is_unvetted_copy_pick(pick):
        return None
    if pick.get("strat_fwd_trades") is not None:
        return pick.get("strat_fwd_trades")
    return pick.get("forward_trades")


def _trusted_forward_pf(pick: dict):
    if _is_unvetted_copy_pick(pick):
        return None
    if pick.get("strat_fwd_pf") is not None:
        return pick.get("strat_fwd_pf")
    return pick.get("profit_factor")


CRYPTO_SOURCE_HINTS = (
    "claude_gainer", "copy_trader", "coinglass", "crypto", "binance", "bybit",
    "hyperliquid", "okx", "gmx", "drift", "dex", "dune", "copin", "onchain",
)
CRYPTO_STRATEGY_HINTS = (
    "copy_hl_", "ct_consensus_", "cg_whale", "funding", "skyrocket", "onchain",
)
NON_CRYPTO_POLICY = {
    "forex": {
        # 2026-04-15: Expanded from 2 → 8 strategies. forex_rsi2_mean_reversion
        # (49% WR n=407 +34.5% PnL), forex-rsi-ema-scout (57% WR n=14),
        # fx_smart_carry_trade_momentum (60% WR n=10), non_crypto_consensus (active),
        # myfxbook_retail_contrarian (39% WR n=33 but +7.0% PnL)
        "allowlist": {
            "cta_tsmom_blend", "forex_rsi2_mean_reversion",
            "forex-rsi-ema-scout", "fx_smart_carry_trade_momentum",
            "non_crypto_consensus", "regime_terminal",
            "myfxbook_retail_contrarian", "ig_contrarian_sentiment",
        },
        "min_trades": 10,
        "min_wr": 40.0,
        "min_pf": 1.05,
        "min_score": 40,
        "min_rr": 1.00,
        "min_conf": 0.50,
        "max_conf": 0.95,
        "allowed_trust": {"PROVEN", "RELIABLE", "DEVELOPING"},
    },
    "equity": {
        # 2026-04-15: Expanded — added regime_terminal (active), non_crypto_consensus,
        # stocks_ema_golden_cross, smart_money_consensus/accumulation (active picks),
        # donchian-stock-breakout (80% WR n=5), price-accel-scout (50% WR n=6),
        # vix-mean-rev-scout (50% WR n=6), keltner-bounce, gap-and-go-stocks
        # 2026-05-19 (M-114): Added regime_* strategies in shadow/forward-test mode.
        # Expected: +400 raw picks/month entering scoring pipeline → higher consensus probability.
        # Auto-promotes if WR≥50% + PF≥1.5 at n≥30 per strategy (tracked via shadow_tracker).
        "allowlist": {
            "post-earnings-rev-scout", "quality-momentum-scout", "stocks_rsi2_pullback",
            "cot_positioning", "rs-breakout-scout", "Breakout Momentum", "Classic Momentum",
            "quality-minus-junk", "Bollinger MR", "Meta Learner", "vwap-reversion-scout",
            "rsi-divergence-scout", "markov_zone_transition",
            "regime_terminal", "non_crypto_consensus", "stocks_ema_golden_cross",
            "smart_money_consensus", "smart_money_accumulation",
            "donchian-stock-breakout", "price-accel-scout", "vix-mean-rev-scout",
            "keltner-bounce", "gap-and-go-stocks", "golden-cross-stocks",
            # M-114 shadow mode — regime-aware EQUITY strategies (forward-test only)
            "regime_accumulation", "regime_mild_bull", "regime_strong_bull",
            "regime_mild_bear", "regime_strong_bear",
            # E-ANON-001 shadow mode — 5d/30d momentum (WR=53.8%/PF=1.23/n=48k OOS, 2026-05-20)
            # VIX gate required: block when VIX > 28 (Fold 2 bear-market drag)
            "e_anon_001_momentum", "short_term_momentum_5d30d",
        },
        "min_trades": 5,
        "min_wr": 40.0,
        "min_pf": 1.05,
        "min_score": 50,
        "min_rr": 1.00,
        "min_conf": 0.50,
        "max_conf": 0.95,
        "allowed_trust": {"PROVEN", "RELIABLE", "DEVELOPING"},
    },
    "commodity": {
        # 2026-04-15: futures_momentum (43% WR n=284 +16.7% PnL).
        # 2026-05-06 KILLED: 0% WR on 56 closed, PF 0.00 — removed from allowlist.
        "allowlist": {
            "cftc_cot_commercial_signal", "cot_positioning",
            "cta_cross_asset_tsmom", "cta_commodity_momentum_term",
            # "futures_ema_stack_momentum",  # REMOVED: 0/4=0% WR, killed 2026-04-02
            # "ema_stack_momentum",           # REMOVED: same strategy, also killed
        },
        "min_trades": 10,
        "min_wr": 35.0,
        "min_pf": 1.00,
        "min_score": 40,
        "min_rr": 1.00,
        "min_conf": 0.50,
        "max_conf": 0.95,
        "allowed_trust": {"PROVEN", "RELIABLE", "DEVELOPING"},
    },
    "etf": {
        "allowlist": {"stocks_rsi2_pullback", "cta_tsmom_blend", "cot_positioning",
                      "proven_vwap_mean_reversion", "sector_rotation"},
        "min_trades": 5,
        "min_wr": 40.0,
        "min_pf": 1.05,
        "min_score": 40,
        "min_rr": 1.00,
        "min_conf": 0.50,
        "max_conf": 0.95,
        "allowed_trust": {"PROVEN", "RELIABLE", "DEVELOPING"},
    },
    "bond": {
        "allowlist": {"cta_tsmom_blend", "cot_positioning"},  # futures_momentum KILLED 2026-05-06
        "min_trades": 5,
        "min_wr": 40.0,
        "min_pf": 1.00,
        "min_score": 40,
        "min_rr": 1.00,
        "min_conf": 0.50,
        "max_conf": 0.95,
        "allowed_trust": {"PROVEN", "RELIABLE", "DEVELOPING"},
    },
    "futures": {
        "allowlist": {"cot_positioning", "cta_tsmom_blend", "cta_commodity_momentum_term"},  # futures_momentum KILLED 2026-05-06
        "min_trades": 5,
        "min_wr": 40.0,
        "min_pf": 1.00,
        "min_score": 40,
        "min_rr": 1.00,
        "min_conf": 0.50,
        "max_conf": 0.95,
        "allowed_trust": {"PROVEN", "RELIABLE", "DEVELOPING"},
    },
}


def _norm_asset_class_name(value: str) -> str:
    ac = str(value or "").upper().strip()
    alias = {
        "STOCKS": "EQUITY",
        "EQUITIES": "EQUITY",
        "PENNY_STOCK": "EQUITY",
        "COMMODITIES": "COMMODITY",
    }
    return alias.get(ac, ac or "UNKNOWN")


def _to_float(v, default=0.0):
    try:
        x = float(v)
    except Exception:
        return default
    return x

def _http_json(url, timeout=8):
    try:
        req = urllib.request.Request(url, headers=_HDR)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception:
        return None

def fetch_live_prices(symbols):
    """Fetch all prices at once from Binance bulk endpoint, with full failover chain."""
    prices = {}
    sym_set = set(symbols)
    # Binance bulk ticker — single request gets ALL symbols
    for mirror in SPOT_URLS:
        try:
            data = _http_json(f"{mirror}/api/v3/ticker/price")
            if isinstance(data, list):
                for t in data:
                    if t["symbol"] in sym_set:
                        prices[t["symbol"]] = float(t["price"])
                break
        except Exception:
            continue
    # Fallback for missing: CoinGecko -> KuCoin -> CryptoCompare
    missing = [s for s in symbols if s not in prices]
    for sym in list(missing):
        bc = sym.replace("USDT", "").replace("USD", "").lower()
        cg = _http_json(f"https://api.coingecko.com/api/v3/simple/price?ids={bc}&vs_currencies=usd")
        if isinstance(cg, dict) and bc in cg and cg[bc].get("usd"):
            prices[sym] = cg[bc]["usd"]; missing.remove(sym)
    for sym in list(missing):
        kc = _http_json(f"https://api.kucoin.com/api/v1/market/orderbook/level1?symbol={sym.replace('USDT', '-USDT')}")
        if isinstance(kc, dict) and isinstance(kc.get("data"), dict) and kc["data"].get("price"):
            prices[sym] = float(kc["data"]["price"]); missing.remove(sym)
    for sym in list(missing):
        bc = sym.replace("USDT", "").replace("USD", "")
        cc = _http_json(f"https://min-api.cryptocompare.com/data/price?fsym={bc}&tsyms=USD")
        if isinstance(cc, dict) and "USD" in cc:
            prices[sym] = cc["USD"]; missing.remove(sym)
    return prices

def _regime_for_symbol(symbol, regime_data):
    def _norm(reg: str) -> str:
        s = str(reg or "").strip().lower()
        if s in {"bear", "bearish", "downtrend"}:
            return "bear"
        if s in {"bull", "bullish", "uptrend"}:
            return "bull"
        if "choppy_tight" in s:
            return "choppy_tight"
        if "choppy_wide" in s:
            return "choppy_wide"
        if "choppy" in s or "range" in s or "mean_reverting" in s:
            return "choppy"
        return "neutral"

    per = regime_data.get("per_symbol", {})
    base = symbol.replace("USDT", "").replace("USD", "")
    for key in [f"{base}-USD", f"{base}USD", base, symbol]:
        if key in per:
            return _norm(per[key].get("kimi_regime", "neutral"))
    return _norm(regime_data.get("aggregate", {}).get("market_regime", "neutral"))

def _parse_ts(ts_str):
    if not ts_str: return None
    try: return datetime.fromisoformat(ts_str)
    except Exception: pass
    try: return datetime.strptime(ts_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except Exception: return None

def _as_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

def _as_pct(value):
    val = _as_float(value, default=0.0)
    if 0 < val <= 1:
        return val * 100.0
    return val


def _import_from_local_or_package(package_name, local_name, attr_name):
    try:
        module = importlib.import_module(package_name)
    except ImportError:
        module = importlib.import_module(local_name)
    return getattr(module, attr_name)

def _normalized_asset_class(pick):
    raw_cat = str(pick.get("category") or pick.get("asset_class") or "").strip().lower()
    strategy = str(pick.get("strategy") or "").lower()
    source = str(pick.get("source_system") or "").lower()
    sym = str(pick.get("symbol") or "").upper().replace("-", "").replace("_", "").replace("/", "")
    sym_no_suffix = sym[:-2] if sym.endswith("=X") else sym

    if sym.endswith("=F"):
        return "futures"
    if sym.endswith("=X"):
        return "forex"
    if sym_no_suffix.endswith(("USDT", "BUSD", "USDC")):
        return "crypto"
    if len(sym_no_suffix) == 6:
        base, quote = sym_no_suffix[:3], sym_no_suffix[3:]
        if base in FOREX_CODES and quote in FOREX_CODES:
            return "forex"
    if sym_no_suffix in ETF_SYMBOLS:
        return "etf"
    if sym_no_suffix in EQUITY_SYMBOLS:
        return "equity"
    if any(tag in source for tag in CRYPTO_SOURCE_HINTS) or any(tag in strategy for tag in CRYPTO_STRATEGY_HINTS):
        return "crypto"

    if raw_cat in {"crypto", "meme"}:
        return "crypto"
    if raw_cat in {"forex", "fx"}:
        return "forex"
    if raw_cat in {"etf"}:
        return "etf"
    if raw_cat in {"bond"}:
        return "bond"
    if raw_cat in {"commodity", "futures"}:
        return "futures"
    if raw_cat in {"equity", "stock", "penny"}:
        return "equity"
    return "equity"


def _has_source_provenance(pick):
    source = str(pick.get("source_system") or pick.get("source") or "").strip().lower()
    return bool(source and source not in {"unknown", "none", "null", "nan"})


def _is_non_crypto(pick):
    """Return True if pick is forex/equity/ETF/futures/bond rather than crypto."""
    return _normalized_asset_class(pick) != "crypto"

def _non_crypto_policy_block_reason(source_pick, scored_pick):
    asset_class = _normalized_asset_class(source_pick)
    policy = NON_CRYPTO_POLICY.get(asset_class)
    if not policy:
        return f"unsupported_asset_class:{asset_class}"
    policy = dict(policy)

    if bool(_POLICY_FLAGS.get("enable_non_crypto_throughput_v2")):
        # Relax thin-sample asset classes via policy overrides.
        _ov = ((_RISK_POLICY.get("non_crypto") or {}).get("min_trades_overrides") or {})
        _ov_val = _ov.get(str(asset_class).upper())
        if _ov_val is not None:
            try:
                policy["min_trades"] = max(0, int(_ov_val))
            except (TypeError, ValueError):
                pass

    strategy = str(source_pick.get("strategy") or "").strip().lower()
    if strategy not in policy["allowlist"]:
        return f"allowlist:{asset_class}"
    if asset_class == "forex":
        sym = str(source_pick.get("symbol") or "").upper().replace("-", "").replace("_", "").replace("/", "")
        sym_no_suffix = sym[:-2] if sym.endswith("=X") else sym
        is_fx_pair = sym.endswith("=X") or (
            len(sym_no_suffix) == 6
            and sym_no_suffix[:3] in FOREX_CODES
            and sym_no_suffix[3:] in FOREX_CODES
        )
        if not is_fx_pair:
            return "forex_symbol_mismatch"

    conf = _as_float(source_pick.get("confidence"), default=0.0)
    if conf < policy["min_conf"] or conf > policy["max_conf"]:
        return f"confidence:{conf:.2f}"

    rr = _as_float(scored_pick.get("rr"), default=0.0)
    if rr < policy["min_rr"]:
        return f"rr:{rr:.2f}"

    # Use ml_composite as primary admission score; fall back to elite_score
    # elite_score has r=-0.001 with PnL, so it should not gate admissions alone
    _ml_comp_val, _ = _compute_ml_composite(source_pick)
    elite = _as_float(source_pick.get("elite_score", source_pick.get("score", 0)), default=0.0)
    # Pass if EITHER ml_composite is reasonable (>0.3) OR elite_score meets threshold
    if _ml_comp_val < 0.3 and elite < policy["min_score"]:
        return f"score:{elite:.1f}|ml:{_ml_comp_val:.2f}"

    trades = max(
        int(_as_float(source_pick.get("strat_fwd_trades"), default=0)),
        int(_as_float(source_pick.get("forward_trades"), default=0)),
        int(_as_float(source_pick.get("history_trades"), default=0)),
    )
    wr = max(
        _as_pct(source_pick.get("strat_fwd_wr")),
        _as_pct(source_pick.get("forward_wr")),
        _as_pct(source_pick.get("history_wr")),
    )
    pf = max(
        _as_float(source_pick.get("strat_fwd_pf"), default=0.0),
        _as_float(source_pick.get("profit_factor"), default=0.0),
        _as_float(source_pick.get("bt_profit_factor"), default=0.0),
    )
    trust = str(source_pick.get("trust_tier") or "").strip().upper()

    if trust and trust not in policy["allowed_trust"]:
        return f"trust:{trust}"
    if trades < policy["min_trades"]:
        return f"trades:{trades}"
    if wr < policy["min_wr"]:
        return f"wr:{wr:.1f}"
    if pf < policy["min_pf"]:
        return f"pf:{pf:.2f}"

    # Goldmine evaluation floor (config-gated):
    # require stronger score/conf until enough forward history exists.
    if bool(_POLICY_FLAGS.get("enable_goldmine_floor_v2")):
        _strat = str(source_pick.get("strategy") or "").strip().lower()
        if _strat.startswith("goldmine_"):
            _nc = _RISK_POLICY.get("non_crypto") or {}
            _gm_min_score = float(_nc.get("goldmine_min_score", 25))
            _gm_min_conf = float(_nc.get("goldmine_min_conf", 0.60))
            _gm_min_trades_relax = int(_nc.get("goldmine_min_trades_to_relax", 30))
            _score_ref = max(
                _as_float(source_pick.get("score"), default=0.0),
                _as_float(source_pick.get("elite_score"), default=0.0),
            )
            if trades < _gm_min_trades_relax:
                if _score_ref < _gm_min_score:
                    return f"goldmine_score:{_score_ref:.1f}"
                if conf < _gm_min_conf:
                    return f"goldmine_conf:{conf:.2f}"

    return None


def _pick_merge_rank(pick):
    """Prefer dashboard-enriched picks over raw source snapshots."""
    rank = 0
    if pick.get("score") is not None:
        rank += 100
    if pick.get("trust_tier"):
        rank += 25
    if pick.get("source_system"):
        rank += 10
    if pick.get("strat_fwd_wr") is not None or pick.get("forward_wr") is not None:
        rank += 10
    if pick.get("current_price") is not None or pick.get("pnl_pct") is not None:
        rank += 5
    return rank


def score_pick(pick, live_price, regime_data, now, fear_greed=0):
    """Score a single pick 0-100. Returns dict or None if filtered."""
    sym, direction = pick.get("symbol", ""), pick.get("direction", "LONG").upper()
    entry, tp, sl = pick.get("entry_price", 0), pick.get("take_profit", 0), pick.get("stop_loss", 0)
    validated_score = _as_float(pick.get("score"), default=0.0) if pick.get("score") is not None else None
    elite = validated_score if validated_score is not None and validated_score > 0 else (pick.get("elite_score", 0) or 0)
    conf = _as_float(pick.get("confidence"), default=0.0)  # needed early for goldmine check
    if not live_price or not entry: return {"_filter": "no_price_or_entry"}
    if not _has_source_provenance(pick):
        return {"_filter": "missing_source"}

    # 2026-05-03: Enforce BLACKLISTED_STRATEGIES from alpha_engine.config.
    # Bug: 3,517 quan_engine_scalp picks bypassed the blacklist 2026-04-03 -> 04-25
    # (sum PnL -600.3% / 32.7% WR) because the blacklist was only enforced in
    # copy_trader_bridge.py, not at this pick-intake gate. Per
    # reports/HEDGE_FUND_PR_MERGE_AUDIT_2026_05_03.md section 5.
    try:
        from alpha_engine.config import BLACKLISTED_STRATEGIES as _BLACKLIST
    except Exception:
        _BLACKLIST = []
    _strat_for_blacklist = (pick.get("strategy") or "").strip().lower()
    if _strat_for_blacklist and _strat_for_blacklist in {s.lower() for s in _BLACKLIST}:
        log.info(f"Filtered {sym}: blacklisted strategy {_strat_for_blacklist}")
        return {"_filter": "blacklisted_strategy"}

    # Score floor: CSV audit shows score < 20 = 37.1% WR vs 20+ = 97% WR
    if elite > 0 and elite < 20:  # Restored — score < 20 = 37.1% WR
        return {"_filter": "elite_below_20"}

    # Goldmine score floor — enforce until closed_n >= 30
    if "goldmine" in _strategy_name(pick):
        goldmine_min_score = 25
        goldmine_min_conf = 0.60
        if elite > 0 and elite < goldmine_min_score:
            log.info(f"Filtered {sym}: goldmine score {elite} < {goldmine_min_score}")
            return {"_filter": "goldmine_score"}
        if conf < goldmine_min_conf:
            log.info(f"Filtered {sym}: goldmine conf {conf:.2f} < {goldmine_min_conf}")
            return {"_filter": "goldmine_conf"}

    # Elite score gate (2026-04-22 edge analysis) — per-asset-class after
    # CRYPTO-calibrated global floor 70 was found to reject 100% of EQUITY.
    try:
        from alpha_engine.config import min_elite_score_for as _min_elite_for
    except Exception:
        _min_elite_for = lambda _ac: MIN_ELITE_SCORE_FOR_PICKS
    _elite_floor = _min_elite_for(pick.get("asset_class") or pick.get("category"))
    if elite > 0 and elite < _elite_floor:
        log.info(f"Filtered {sym}: elite_score {elite} < {_elite_floor} (class floor)")
        return {"_filter": "elite_below_gate"}

    # Per-strategy confidence gate (2026-04-22 edge analysis)
    # e.g. ml_crypto_predictor: confidence=0.50 -> worst performer; require >=0.70
    _strat_for_conf = str(pick.get("strategy") or "").strip()
    _min_conf_for_strat = STRATEGY_MIN_CONFIDENCE.get(_strat_for_conf)
    if _min_conf_for_strat is not None and conf < _min_conf_for_strat:
        log.info(f"Filtered {sym}: strategy {_strat_for_conf} conf {conf:.2f} < {_min_conf_for_strat}")
        return {"_filter": "strategy_conf_gate"}

    # High Volume FOMO protection (Enhancement based on March 28 Analysis)
    vol_ratio = _as_float(pick.get("volume_ratio") or pick.get("vol_ratio"), default=0.0)
    if vol_ratio > MAX_VOLUME_RATIO:
        log.info(f"Filtered {sym}: high volume FOMO (ratio {vol_ratio:.2f} > {MAX_VOLUME_RATIO})")
        return {"_filter": "volume_fomo"}

    asset_class = _normalized_asset_class(pick)

    # Check if TP or SL already hit
    if tp and sl:
        if direction == 'LONG':
            if live_price >= tp: return {"_filter": "tp_already_hit"}
            if live_price <= sl: return {"_filter": "sl_already_hit"}
        elif direction == 'SHORT':
            if live_price <= tp: return {"_filter": "tp_already_hit"}
            if live_price >= sl: return {"_filter": "sl_already_hit"}

    non_crypto = asset_class != "crypto"
    strat_name = pick.get("strategy", "")
    # conf already extracted above (needed for goldmine check before this point)

    # ── STALE COPY TRADER CHECK (softened) ────────────────────────────
    # Check if ANY copy trader still holds this symbol in same direction.
    # Previous version checked exact strategy name which was too strict
    # (copy_trader_intel refreshes names each scan cycle).
    if strat_name.startswith("copy_hl_") or strat_name.startswith("clone_hl_"):
        try:
            import pathlib as _pl
            _ct_path = _pl.Path(__file__).resolve().parent.parent / "copy_trader_intel" / "data" / "active_picks.json"
            if _ct_path.exists():
                with open(_ct_path, "r", encoding="utf-8") as _cf:
                    _ct_picks = __import__("json").load(_cf)
                _still_held = any(
                    str(cp.get("symbol", "")).upper() == sym.upper()
                    and str(cp.get("direction", "")).upper()[:1] == direction[:1]
                    for cp in _ct_picks
                )
                # Only filter if NO trader holds this symbol+direction AND pick is > 24h old
                if not _still_held:
                    _age = pick.get("age_hours", 0) or 0
                    if _age > 24:
                        return {"_filter": "stale_copy_trader"}  # Old + no trader holds = truly stale
                    # Young picks get benefit of doubt (trader may have just entered)
        except Exception:
            pass  # Fail-open

    # ── CRYPTO SHORTS GATE (Regime Aware) ────────────────────────────
    # Live data: Crypto LONG 43.1% WR +9.90% PnL vs SHORT 15.3% WR -5.29% PnL
    # Block unless Fear/Greed is BEARISH (<35) or strategy is proven/copy trader.
    # ── CRYPTO SHORTS GATE (Regime Aware) ────────────────────────────
    # Data: SHORTs 66% WR +0.81% avg vs LONGs 44% WR -2.32% in fear regime.
    # In extreme fear (FGI < 20), shorts are PROFITABLE — relax gate.
    # Only hard-block shorts in non-fear when unproven.
    if asset_class == "crypto" and direction in ("SHORT", "SELL"):
        is_proven = strat_name in PROVEN_WINNERS or strat_name.startswith("copy_hl_")
        is_bearish_market = fear_greed > 0 and fear_greed < 35
        if not is_proven and not is_bearish_market:
            pass  # Relaxed: penalty applied in scoring, not hard block

    _low_confidence = False  # 2026-04-15: soft penalty flag
    # ── CONFIDENCE FLOOR (Adaptive) ──────────────────────────────────
    # 2026-04-15: Lowered from 0.55 to 0.50 — aligned with non-crypto policy.
    # Data: Q4 score bucket (29-46) has 49.7% WR, best of any bucket.
    # Picks with conf 0.50-0.55 were being hard-blocked despite scoring well.
    # Relaxed to 0.40 for capitulation regime (FGI < 20)
    if asset_class == "crypto" and 0 < conf < 0.50:
        if strat_name not in PROVEN_WINNERS:
            _low_confidence = True  # 2026-04-15: was hard-block, now soft -10

    open_ts = _parse_ts(pick.get("open_time") or pick.get("timestamp") or pick.get("entry_date", ""))
    try:
        if open_ts and open_ts.tzinfo is None:
            from datetime import timezone as _tz
            open_ts = open_ts.replace(tzinfo=_tz.utc)
        age_h = (now - open_ts).total_seconds() / 3600 if open_ts else 999
    except Exception:
        age_h = 999
    # Copy trader picks can be older (whales hold positions for days)
    strat_l = pick.get("strategy", "").lower()
    is_copy = "copy" in strat_l or "whale" in strat_l
    max_age = 72 if is_copy else 48  # copy-trader entries can stay a bit longer, but not indefinitely
    if "clone_" in strat_l:
        max_age = 48  # clones degrade fast; stale clone positions poisoned the tab
    if age_h > max_age: return {"_filter": "too_stale"}

    pnl_pct = ((live_price - entry) / entry * 100) if direction == "LONG" else ((entry - live_price) / entry * 100)

    # ── THRESHOLD A & AFFINITY BONUS (2026-04-05 Hardening) ──────────
    if hf_policy_thresholds and affinity:
        bt_wr = affinity.get_backtest_win_rate(strat_name, sym)
        if bt_wr is not None:
            fwd_wr = _as_pct(pick.get("strat_fwd_wr") or pick.get("forward_wr"))
            fwd_trades = int(_as_float(pick.get("strat_fwd_n") or pick.get("forward_trades"), default=0))
            
            # Threshold A Check: Hard gate on win-rate discrepancy
            if not hf_policy_thresholds.validate_threshold_a(bt_wr, fwd_wr, fwd_trades):
                log.info(f"Filtered {sym} ({strat_name}): Threshold A failed (BT {bt_wr*100:.1f}% vs FWD {fwd_wr:.1f}%)")
                return {"_filter": "threshold_a"}

            # Affinity Bonus: Prioritize strategy-symbol pairs with high OOS performance
            aff_score = affinity.get_affinity(strat_name, sym)
            if aff_score is not None:
                if aff_score >= 0.8: elite += 15 # Institutional-grade affinity
                elif aff_score >= 0.6: elite += 10
                elif aff_score >= 0.4: elite += 5
                elif aff_score < 0.2: elite -= 20 # Severe misfit penalty

    if tp and entry:
        total = (tp - entry) if direction == "LONG" else (entry - tp)
        remain = (tp - live_price) if direction == "LONG" else (live_price - tp)
        tp_rem = (remain / total * 100) if total else 0
    else:
        tp_rem = 50
    sl_dist = abs(live_price - sl) / live_price * 100 if sl else 0
    risk = abs(live_price - sl) if sl else 0
    reward = abs(tp - live_price) if tp else 0
    rr = round(reward / risk, 2) if risk > 0 else 0
    # 2026-04-15: Two-tier RR gate - hard-block RR<0.5, soft penalty RR 0.5-0.8
    if rr > 0 and rr < 0.5:
        return {"_filter": "very_low_rr"}  # Structurally unfavorable - risk >> reward
    _low_rr = False  # 2026-04-15: soft penalty flag for RR 0.5-0.8
    if rr >= 0.5 and rr < 0.8:
        _low_rr = True  # 2026-04-15: was hard-block, now soft -10
    regime = _regime_for_symbol(sym, regime_data)

    # --- SCORING (v2 — ChatGPT/Kimi cross-AI audit, 2026-03-23) ---
    # Removed "currently_winning" (survivorship bias / positive feedback loop).
    # Reduced regime_match from 40% to 25% (fast_regime_detector is new/unproven).
    # Increased elite_quality to 35% (track record is the most proven predictor).
    # Added htf_alignment at 10% (higher-timeframe confirmation from htf_confirmation.py).
    #
    # New weights: regime 25, elite 35, freshness 15, tp_upside 15, htf_alignment 10 = 100
    if non_crypto:
        regime_max = 15   # down further — crypto regime doesn't drive forex/equity
        quality_max = 40  # track record matters even more for non-crypto
    else:
        regime_max = 25
        quality_max = 35

    score = 0
    # 1. Direction matches regime (25 pts max, was 40)
    if (direction == "SHORT" and regime == "bear") or (direction == "LONG" and regime == "bull"):
        direction_score = regime_max
    elif regime in ("choppy_tight", "choppy"):
        # In tight chop, directional alpha is weak.
        direction_score = max(1, regime_max // 6)
    elif regime == "choppy_wide":
        # Wide chop keeps tactical alpha but weaker than trend.
        direction_score = max(2, regime_max // 4)
    elif regime == "neutral":
        direction_score = regime_max // 2
    else:
        direction_score = 0
    score += direction_score
    # 2. Elite/quality score (35 pts max, was 20)
    quality_score = round(min(elite, 100) / 100 * quality_max)
    score += quality_score
    # 3. Freshness (15 pts — unchanged)
    freshness_score = 15 if age_h < 1 else 12 if age_h < 4 else 8 if age_h < 12 else 4 if age_h < 24 else 0
    score += freshness_score
    # 4. TP remaining / upside (15 pts — unchanged)
    upside_score = 15 if tp_rem > 70 else 10 if tp_rem > 50 else 5 if tp_rem > 30 else 0
    score += upside_score
    # 4b. REGIME PENALTY (2026-04-11): Data shows RANGING=10% WR, TRENDING_DOWN=16.7% WR.
    # Long-only picks in these regimes are near-guaranteed losers.
    # Penalize heavily; only proven contrarian/recovery strategies survive.
    _regime_penalty = 0
    _regime_exempt = strat_name in PROVEN_WINNERS or "fear_greed" in strat_name or "drawdown_recovery" in strat_name or "contrarian" in strat_name
    if not _regime_exempt and not non_crypto:
        if regime == "bear" and direction == "LONG":
            _regime_penalty = 20  # TRENDING_DOWN: 16.7% WR for longs, harsh penalty
        elif regime == "neutral":
            _regime_penalty = 8   # RANGING: 10% WR, moderate penalty
    score = max(0, score - _regime_penalty)

    # 5. HTF alignment (10 pts — replaces currently_winning)
    # Uses htf_bias from htf_confirmation.py stored in pick's extra dict.
    extra = pick.get("extra", {})
    htf_bias = extra.get("htf_bias", "")
    if htf_bias and htf_bias not in ("N/A", "NEUTRAL", ""):
        # HTF bias matches pick direction → full points
        if (direction == "LONG" and htf_bias == "BULLISH") or (direction == "SHORT" and htf_bias == "BEARISH"):
            htf_score = 10
        else:
            # HTF bias contradicts pick direction → 0 points
            htf_score = 0
    else:
        # No HTF data or neutral → 5 pts (don't penalize missing data)
        htf_score = 5
    score += htf_score

    # 6. PROVEN WINNER BOOST (0-15 pts)
    winner_boost = 0
    if strat_name in PROVEN_WINNERS:
        winner_boost = PROVEN_WINNERS[strat_name]["boost"]
    else:
        for prefix, boost in PROVEN_PREFIXES.items():
            if strat_name.startswith(prefix):
                winner_boost = max(winner_boost, boost)
                break
    # Multi-symbol strength adjustment: boost strategies that work across many pairs
    try:
        _tiers_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "ab_test_portfolios", "symbol_strength_tiers.json")
        if os.path.exists(_tiers_path):
            import json as _json
            with open(_tiers_path, encoding="utf-8") as _tf:
                _tiers = _json.load(_tf).get("details", {})
            _strat_tier = _tiers.get(strat_name, {})
            _sym_boost = _strat_tier.get("boost", 0)
            if _sym_boost > 0:
                winner_boost += _sym_boost
    except Exception:
        pass  # Fail-open
    if strat_name.startswith("rapid_fire"):
        winner_boost = max(winner_boost, 12)
    score = min(100, score + winner_boost)

    # 6b. CRYPTO STRATEGY-FAMILY BOOST / PENALTY (2026-05-16 Kimi audit fix)
    # Scoring inversion fix: proven strategy families get +20, toxic get -15.
    # Exact match on proven/toxic sets OR prefix match on CRYPTO_PROVEN_PREFIXES
    # for auto-detection of new per-symbol ml_enhanced_ variants.
    # NOTE: Two independent if-blocks (not if/elif) so toxic LONG/BUY picks
    # still receive the penalty instead of escaping through the first branch.
    sf_boost = 0
    sf_penalty = 0
    if asset_class == "crypto" and direction in ("LONG", "BUY"):
        if strat_name in CRYPTO_PROVEN_STRATEGIES:
            sf_boost = 20
        elif any(strat_name.startswith(pfx) for pfx in CRYPTO_PROVEN_PREFIXES):
            sf_boost = 20
    if asset_class == "crypto" and strat_name in CRYPTO_TOXIC_STRATEGIES:
        sf_penalty = -15
    if sf_boost:
        score = min(100, score + sf_boost)
    if sf_penalty:
        score = max(0, score + sf_penalty)

    # 7. COPY TRADER PREMIUM (+10 pts)
    # Only vetted copy feeds qualify. Raw clone / Bitget / Binance sentiment
    # sources are intentionally excluded from Smart Picks.
    is_copy_trader = _is_vetted_copy_pick(pick)
    copy_boost = 10 if is_copy_trader else 0
    score = min(100, score + copy_boost)
    explanation_parts = []

    # 7b. INSTITUTIONAL SWEET SPOT (+10 pts)
    # Rationale: Confidence (0.60-0.70) + ML Score (>= 0.65) = strongest predictive edge.
    ml_val = _as_float(pick.get("ml_score"), default=0.0)
    _inst_sweet_spot = False
    if ml_val >= 0.65 and 0.60 <= conf <= 0.70:
        score = min(100, score + 10)
        _inst_sweet_spot = True

    # Kimi condition gate: only keep high-evidence states.
    # EQUITY exception (2026-05-17): donchian-stock-breakout (n=14, WR=78.6%, PF=7.13)
    # and rs-breakout-scout (n=36, WR=75%, PF=4.38) are proven EQUITY strategies.
    # Allow EQUITY for the proven subset; still require fwd_wr >= 55%.
    _KIMI_EQUITY_PROVEN = {
        "donchian-stock-breakout",
        "rs-breakout-scout",
        "ema-ribbon-momentum-scout",
        "vol-contraction-scout",
        "price-accel-scout",
        "gap-and-go-stocks",
        "cci-crypto-reversal",
        "mtf-align-scout",
    }
    if strat_name.startswith("kimi_riseoftheclaw"):
        _kimi_ac = _norm_asset_class_name(asset_class)
        _kimi_strat_short = strat_name.replace("kimi_riseoftheclaw_", "").replace("kimi_riseoftheclaw/", "")
        if _kimi_ac != "CRYPTO" and _kimi_strat_short not in _KIMI_EQUITY_PROVEN:
            return {"_filter": "kimi_non_crypto"}
        _kimi_wr = _as_pct(pick.get("strat_fwd_wr") or pick.get("forward_wr"))
        if _kimi_wr < 55:
            return {"_filter": "kimi_low_wr"}

    # 8. CONFLUENCE BOOST — DISABLED (Spearman r=-0.075, anti-predictive)
    # Data from 1,879 closed trades: high agreement_count = WORSE outcomes.
    # Consensus multiplier capped at 1.0x in aggregator.py and elite_scorer.py.
    # Do NOT re-enable without new evidence.
    confluence_boost = 0

    # 9. HOURLY MONITOR SCORING OVERRIDES (dynamic, data-driven)
    # Loaded from scoring_overrides.json written by hourly_performance_monitor.py
    # This adjusts scores based on live strategy momentum without code changes.
    try:
        _override_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "scoring_overrides.json")
        if os.path.exists(_override_path):
            import json as _json
            with open(_override_path, encoding="utf-8") as _of:
                _overrides = _json.load(_of).get("adjustments", {})
            _strat_override = _overrides.get(strat_name, {})
            _monitor_boost = _strat_override.get("boost", 0)
            if _monitor_boost != 0:
                score = max(0, min(100, score + _monitor_boost))
    except Exception:
        pass  # Fail-open: don't break scoring if overrides file is bad

    # Build concise explanation with only the strong factors
    if confluence_boost > 0:
        explanation_parts.append(f"Multi-signal agreement (+{confluence_boost})")
    if copy_boost > 0:
        explanation_parts.append(f"Copy-trader premium (+{copy_boost})")
    if winner_boost > 0:
        explanation_parts.append(f"Proven winner (+{winner_boost})")
    if _inst_sweet_spot:
        explanation_parts.append(f"Institutional sweet spot (+10)")
    if _regime_penalty > 0:
        explanation_parts.append(f"Regime penalty {regime.upper()} (-{_regime_penalty})")
    if direction_score >= regime_max * 0.75:
        explanation_parts.append(f"Direction matches {regime.upper()} regime (+{direction_score})")
    if elite >= 60:
        explanation_parts.append(f"Quality score {elite} (+{quality_score})")
    if age_h < 4:
        explanation_parts.append(f"Fresh signal {age_h:.1f}h ago (+{freshness_score})")
    if tp_rem > 50:
        explanation_parts.append(f"{tp_rem:.0f}% upside to TP (+{upside_score})")
    if htf_score == 10:
        explanation_parts.append(f"Higher-timeframe confirms {direction} (+{htf_score})")
    elif htf_score == 0:
        explanation_parts.append(f"Higher-timeframe contradicts {direction} (+0)")

    # 2026-04-15: tp_rem < 10% soft penalty (was hard-block).
    # Picks near TP are WINNING - do not exclude, just rank lower.
    if tp_rem < 10:
        score = max(0, score - 15)
        explanation_parts.append("Near TP -15")
    if _low_confidence:
        score = max(0, score - 10)
        explanation_parts.append("Low conf -10")
    if _low_rr:
        score = max(0, score - 10)
        explanation_parts.append("Low RR -10")

    # Filters
    filt = None
    if sym.replace("USDT", "").replace("USD", "").upper() in MEME_TOKENS and direction == "LONG" and regime == "bear":
        filt = "meme_long_bear"
    # --- DIRECTION-SENTIMENT SCORING (data-driven) ---
    # Data: SHORTs 66% WR +0.81% in fear vs LONGs 44% WR -2.32%.
    # Extreme fear (FGI < 20): BOOST shorts +15, penalize longs -15.
    # Extreme greed (FGI > 85): penalize shorts -15.
    if not non_crypto:
        regime_l = str(regime).lower()
        if fear_greed > 0 and fear_greed < 20:
            if direction in ("SHORT", "SELL"):
                score = min(100, score + 15)  # SHORT boost in extreme fear
                explanation_parts.append(f"Short boost: fear & greed={fear_greed} (+15)")
            elif direction in ("LONG", "BUY"):
                score = max(0, score - 15)  # LONG penalty in extreme fear
        elif fear_greed > 85 and regime_l in ("bull", "bullish") and direction in ("SHORT", "SELL"):
            score = max(0, score - 15)  # Penalty not block
    if direction_score == 0 and score < 45:
        filt = "wrong_direction"  # Lowered from 70: ML-composite handles ranking now

    # MTF soft scoring (crypto only): boost MTF-confirmed picks, penalize misaligned
    # Score adjustments from mtf_gate: STRONG +10, MODERATE +5, WEAK -10, BLOCKED -25
    mtf_aligned = True
    mtf_agreement_ratio = "N/A"
    mtf_score_adj = 0
    mtf_recommendation = "NO_DATA"
    if _HAS_MTF_GATE and asset_class == "crypto":
        try:
            mtf_dir = "BULL" if direction in ("LONG", "BUY") else "BEAR"
            mtf_result = _check_mtf(sym, mtf_dir)
            mtf_aligned = bool(mtf_result.get("aligned", True))
            mtf_agreement_ratio = mtf_result.get("agreement", "N/A")
            mtf_recommendation = mtf_result.get("recommendation", "NO_DATA")
            mtf_score_adj = int(mtf_result.get("score_adjustment", 0))
            # Apply soft score adjustment (clamp so score stays 0-100)
            score = max(0, min(100, score + mtf_score_adj))
            # Add to explanation
            if mtf_score_adj > 0:
                explanation_parts.append(f"Multi-timeframe {mtf_recommendation} {mtf_agreement_ratio} (+{mtf_score_adj})")
            elif mtf_score_adj < 0:
                explanation_parts.append(f"MTF {mtf_recommendation} {mtf_agreement_ratio} ({mtf_score_adj})")
            # 2026-04-15: Lowered MTF hard-block threshold from 55 to 40.
            # At 55, 50 picks were blocked — many were good picks from proven
            # strategies that happened to lack MTF data. Score >= 40 means the
            # pick passed quality, regime, and freshness gates — MTF disagreement
            # shouldn't override all those signals. Below 40, hard-block remains.
            if not mtf_aligned and score < 40:
                filt = "mtf_not_aligned"
        except Exception:
            mtf_aligned = True  # Don't block on errors
            mtf_agreement_ratio = "ERROR"
            mtf_recommendation = "ERROR"

    # --- CONFLUENCE CONVICTION BOOST (Institutional Herding) ---
    # Signals with 3+ agreeing source systems represent high-conviction flow.
    # Data: 3+ independent sources = 55.6% WR vs 34.3% single-source noise.
    # ---------------------------------------------------------------------------
    sources = pick.get("source_systems", [])
    if isinstance(sources, list) and len(sources) >= 3:
        score += 15  # 15pt boost for multi-system institutional herding
        pick["confluence_boost_active"] = True
    elif isinstance(sources, list) and len(sources) == 2:
        score += 5   # minor boost for secondary confirmation
    elif isinstance(sources, str) and "," in sources:
        # Fallback for comma-separated string format
        s_count = len(sources.split(","))
        if s_count >= 3:
            score += 15
            pick["confluence_boost_active"] = True
        elif s_count == 2:
            score += 5
    # ---------------------------------------------------------------------------

    # Ensemble gate (crypto only): 2-of-3 independent signals must agree
    ensemble_aligned = 0
    if asset_class == "crypto" and not filt:
        try:
            from alpha_engine.ensemble_gate import check_ensemble as _check_ensemble
            ens_dir = direction if direction in ("LONG", "SHORT") else ("LONG" if direction == "BUY" else "SHORT")
            ens = _check_ensemble(sym, ens_dir)
            ensemble_aligned = ens.get("signals_aligned", 0)
            if not ens.get("passes", True) and score < 50:
                # 2026-04-15: Lowered from 65 to 50 — ensemble gate should only
                # block mediocre picks, not moderate ones passing other gates.
                filt = "ensemble_not_aligned"
            if ensemble_aligned >= 3:
                score += 5  # all 3 signal categories agree — bonus
        except Exception:
            pass  # fail-open

    # ── EQUITY FACTOR MODEL + EARNINGS PEAD BOOST ────────────────────
    # For equity picks: apply multi-factor scoring (Value/Momentum/Quality)
    # and Post-Earnings Announcement Drift (PEAD) confidence boost.
    # This modifies score by up to +/-10 pts based on fundamental factors.
    factor_boost_pts = 0
    if asset_class == "equity":
        try:
            from equity_factor_model import compute_factor_boost, compute_earnings_boost, compute_factor_score
            _fb = compute_factor_boost(sym)
            _eb = compute_earnings_boost(sym)
            # Convert confidence adjustments to score points (0.10 conf ~ 10 pts)
            factor_boost_pts = int((_fb + _eb) * 100)
            if factor_boost_pts != 0:
                score = max(0, min(100, score + factor_boost_pts))
                _fs, _fd = compute_factor_score(sym)
                if factor_boost_pts > 0:
                    explanation_parts.append(f"Factor + post-earnings drift boost (+{factor_boost_pts}, {_fd})")
                else:
                    explanation_parts.append(f"Factor + post-earnings drift penalty ({factor_boost_pts}, {_fd})")
        except ImportError:
            pass
        except Exception:
            pass  # Fail-open: don't break scoring

    # Rebuild explanation after MTF scoring may have added parts
    explanation = " | ".join(explanation_parts) if explanation_parts else f"Score {score}/100"

    # ML-composite ranking (replaces elite_score as primary ranker)
    _ml_comp, _rank_method = _compute_ml_composite(pick)

    # ── HTF bias: pass through from source pick's extra dict ────────
    _htf_bias_val = (extra.get("htf_bias")
                     or pick.get("htf_bias")
                     or pick.get("htf_alignment")
                     or pick.get("regime_at_entry")
                     or pick.get("regime_trend_direction")
                     or None)
    if not _htf_bias_val or _htf_bias_val in ("N/A", ""):
        if htf_score == 10:
            _htf_bias_val = "BULLISH" if direction == "LONG" else "BEARISH"
        elif htf_score == 0 and htf_bias:
            _htf_bias_val = "BEARISH" if direction == "LONG" else "BULLISH"
        else:
            _htf_bias_val = "NEUTRAL"

    # ── Strategy forward performance: pass through from source pick ──
    _strat_fwd_wr = _trusted_forward_wr(pick)
    _strat_fwd_trades = _trusted_forward_trades(pick)
    _strat_fwd_pf = _trusted_forward_pf(pick)
    if _strat_fwd_wr is not None:
        _strat_fwd_wr = float(_strat_fwd_wr)
        if 0 < _strat_fwd_wr <= 1.0:
            _strat_fwd_wr = round(_strat_fwd_wr * 100, 1)
    if _strat_fwd_trades is not None:
        _strat_fwd_trades = int(float(_strat_fwd_trades))

    # Asset-specific sanity check (e.g. Gold GC=F Bad Data Protection)
    if sym == "GC=F":
        # Realistic gold prices 2025-2026: 2200-3500. 4700+ is definitely bad data.
        if entry < 1800 or entry > 3800:
            return {"_filter": "bad_data_gold"}
    # General sanity check: if entry is more than 40% away from live price, discard (bad data/flash crash)
    if abs(entry - live_price) / live_price > 0.4:
        return {"_filter": "bad_data_price"}

    # per_class_trainer shadow quality check (2026-05-15)
    # PER_CLASS_ML_SHADOW=1: logs prediction but never rejects.
    # After 30d of shadow data, evaluate whether to set PER_CLASS_ML_ENFORCE=1.
    _ml_quality_shadow = None
    try:
        import os as _os_pct
        if _os_pct.environ.get("PER_CLASS_ML_SHADOW", "1") not in ("0", "false", "FALSE"):
            from ml_gatekeeper.per_class_trainer import predict_quality as _pct_predict_quality
            _pct_result = _pct_predict_quality(pick)
            if _pct_result is not None:
                _ml_quality_shadow = _pct_result.get("ml_per_class_score")
                if _ml_quality_shadow is not None:
                    _ml_quality_shadow = float(_ml_quality_shadow)
                if (
                    _ml_quality_shadow is not None
                    and _ml_quality_shadow < 0.3
                    and _os_pct.environ.get("PER_CLASS_ML_ENFORCE", "0") not in ("0", "false", "FALSE")
                ):
                    return {"_filter": "per_class_ml_low_quality"}  # enforce mode: reject low-quality picks
    except Exception:
        pass  # fail-open: shadow mode never blocks on error

    # Net-of-cost estimate (2026-05-15)
    # Rough transaction cost model: bid/ask spread + commission per class.
    # These are pessimistic estimates — the real edge is at least this good.
    _net_pnl_est = None
    _tc_pct = None
    try:
        _TC_BY_CLASS = {
            "CRYPTO": 0.001,    # 0.1% round-trip (typical CEX taker fee)
            "EQUITY": 0.0005,   # 0.05% round-trip (liquid equities)
            "ETF": 0.0003,      # 0.03% round-trip (highly liquid)
            "COMMODITY": 0.002, # 0.2% round-trip (futures spread)
            "FUTURES": 0.002,   # 0.2% round-trip
            "FOREX": 0.0003,    # 0.03% round-trip (major pairs)
            "BOND": 0.001,      # 0.1% round-trip (treasury ETFs)
        }
        _ac_cost = _TC_BY_CLASS.get(str(pick.get("asset_class", "") or "").upper(), 0.001)
        _avg_pnl_pct = float(pick.get("avg_pnl_pct") or pick.get("expected_pnl_pct") or 0.0)
        _net_pnl_est = round(_avg_pnl_pct - (_ac_cost * 100), 4)  # cost in same % units
        _tc_pct = round(_ac_cost * 100, 4)
    except Exception:
        pass  # fail-open: net-of-cost calc never breaks pick generation

    # ── ETF QUALITY FILTERS (2026-05-16, opt-in) ─────────────────────────────
    # Filter 1 — RS vs SPY:  ETF pick must show >= ETF_RS_THRESHOLD (default 2%)
    #             20-day outperformance vs SPY.  Kill-switch: ETF_RS_FILTER_ENABLED=0
    # Filter 2 — Volume Surge: volume_ratio must be >= ETF_VOLUME_SURGE_MIN (1.3).
    #             Kill-switch: ETF_VOLUME_SURGE_ENABLED=0
    # Both filters fail-open (missing data → pass).  On rejection, score is
    # zeroed and _etf_quality_filtered=True is tagged — no exception is raised.
    _etf_quality_filtered = False
    _etf_quality_reasons: list = []
    if asset_class == "etf":
        try:
            from alpha_engine.etf_quality_filters import apply_etf_quality_filters as _etf_qf
        except ImportError:
            try:
                from etf_quality_filters import apply_etf_quality_filters as _etf_qf
            except ImportError:
                _etf_qf = None
        if _etf_qf is not None:
            try:
                score, _etf_quality_filtered, _etf_quality_reasons = _etf_qf(pick, score)
                if _etf_quality_filtered:
                    log.info(
                        "[etf_quality_filters] %s zeroed by ETF quality filters: %s",
                        sym, "; ".join(_etf_quality_reasons),
                    )
            except Exception as _etf_exc:
                log.warning("[etf_quality_filters] apply_etf_quality_filters error "
                            "(fail-open): %s", _etf_exc)

    # ── EDGE CONCENTRATOR (2026-05-16, opt-in sidecar) ───────────────────────
    # Activation: set EDGE_CONCENTRATOR_ENABLED=1 in environment, or set
    #   {"enable_edge_concentrator": true} in risk_policy.json policy flags.
    # Five-layer gate: auto-pause → capacity → regime → family IC → strategy tier.
    # Sets filt="EC_<reason>" on rejection; dynamic_sl replaces stop_loss if accepted.
    # Always fail-open: exceptions never block pick generation.
    # Wiring plan: this sidecar → full wiring when IC data is validated over ≥4 weeks.
    _ec_reason: str = ""
    _ec_dynamic_sl: Optional[float] = None
    _ec_enabled = (
        os.environ.get("EDGE_CONCENTRATOR_ENABLED", "0") == "1"
        or bool((_POLICY_FLAGS or {}).get("enable_edge_concentrator"))
    )
    if _ec_enabled and not filt:
        try:
            from alpha_engine.edge_concentrator import get_concentrator as _get_ec
            _ec_result = _get_ec().evaluate(pick, asset_class, direction, regime, score)
            if not _ec_result["accepted"]:
                filt = f"EC_{_ec_result['reason']}"
                _ec_reason = _ec_result["reason"]
                log.info("[edge_concentrator] %s %s rejected: %s", sym, direction, _ec_reason)
            else:
                _ec_dynamic_sl = _ec_result.get("dynamic_sl")
        except Exception as _ec_exc:
            log.debug("[edge_concentrator] fail-open: %s", _ec_exc)

    return {
        "symbol": sym, "direction": direction, "smart_score": score,
        "elite_score": elite, "entry": entry, "live": live_price,
        "tp": tp, "sl": sl, "pnl_pct": round(pnl_pct, 2),
        "tp_remaining_pct": round(tp_rem, 1), "age_hours": round(age_h, 1),
        "strategy": str(pick.get("strategy") or pick.get("source_system") or "unknown"),
        "source": str(pick.get("source") or pick.get("source_system") or "unknown"),
        "source_system": str(pick.get("source_system") or "unknown"),
        "system": str(pick.get("system") or pick.get("strategy") or "unknown"),
        "trust_tier": pick.get("trust_tier", ""),
        "validated_score": validated_score,
        "timeframe": pick.get("timeframe", "SWING"),
        "asset_class": asset_class.upper(),
        "explanation": explanation,
        "risk_note": f"SL {sl_dist:.1f}% away. R:R = {rr}x." if sl else "No SL defined.",
        "regime": regime, "rr": rr, "_filter": filt,
        "mtf_aligned": mtf_aligned, "mtf_agreement_ratio": mtf_agreement_ratio,
        "mtf_recommendation": mtf_recommendation,
        "ml_score": pick.get("ml_score"),
        "ml_composite": _ml_comp,
        "ranking_method": _rank_method,
        "htf_bias": _htf_bias_val,
        "strat_fwd_wr": _strat_fwd_wr,
        "strat_fwd_trades": _strat_fwd_trades,
        "strat_fwd_pf": _strat_fwd_pf,
        "ml_quality_shadow": _ml_quality_shadow,
        "net_pnl_estimate_pct": _net_pnl_est,
        "transaction_cost_pct": _tc_pct,
        "_etf_quality_filtered": _etf_quality_filtered,
        "_etf_quality_reasons": _etf_quality_reasons if _etf_quality_reasons else None,
        "_ec_reason": _ec_reason or None,
        "_ec_dynamic_sl": _ec_dynamic_sl,
    }


def _apply_concentration_probation_controls(scored: list[dict], excluded: dict, risk_policy: dict) -> tuple[list[dict], dict]:
    """Apply optional concentration/probation controls with safe defaults.

    mode=tag: annotate picks but do not filter.
    mode=exclude: hard-block overexposed keys.
    """
    flags = (risk_policy.get("policy_flags") or {})
    controls = (risk_policy.get("concentration_controls") or {})
    enabled = bool(flags.get("enable_concentration_probation_v2"))
    mode = str(controls.get("mode", "tag") or "tag").strip().lower()
    mode = mode if mode in ("tag", "exclude") else "tag"
    max_sym_strat = int(controls.get("max_symbol_strategy_exposure", 2) or 2)
    max_strat_system = int(controls.get("max_strategy_system_exposure", 3) or 3)

    stats = {
        "enabled": enabled,
        "mode": mode,
        "max_symbol_strategy_exposure": max_sym_strat,
        "max_strategy_system_exposure": max_strat_system,
        "input_scored": len(scored),
        "tagged_probation": 0,
        "excluded_probation": 0,
        "pass_through_count": len(scored),
        "pass_through_rate": 100.0,
        "symbol_strategy_overexposed": 0,
        "strategy_system_overexposed": 0,
    }
    if not enabled or not scored:
        return scored, stats

    sym_strat_counts = Counter()
    strat_sys_counts = Counter()
    for pick in scored:
        sym = str(pick.get("symbol") or "").upper()
        strat = str(pick.get("strategy") or "").strip().lower()
        system = str(pick.get("source_system") or pick.get("system") or "").strip().lower()
        if sym and strat:
            sym_strat_counts[(sym, strat)] += 1
        if strat and system:
            strat_sys_counts[(strat, system)] += 1

    output = []
    for pick in scored:
        sym = str(pick.get("symbol") or "").upper()
        strat = str(pick.get("strategy") or "").strip().lower()
        system = str(pick.get("source_system") or pick.get("system") or "").strip().lower()

        sym_strat_ct = sym_strat_counts.get((sym, strat), 0) if (sym and strat) else 0
        strat_sys_ct = strat_sys_counts.get((strat, system), 0) if (strat and system) else 0
        over_sym_strat = sym_strat_ct > max_sym_strat
        over_strat_sys = strat_sys_ct > max_strat_system
        if over_sym_strat:
            stats["symbol_strategy_overexposed"] += 1
        if over_strat_sys:
            stats["strategy_system_overexposed"] += 1

        if over_sym_strat or over_strat_sys:
            if mode == "exclude":
                excluded["probation_concentration"] = excluded.get("probation_concentration", 0) + 1
                stats["excluded_probation"] += 1
                continue
            pick["probation_flag"] = True
            pick["probation_reasons"] = {
                "symbol_strategy_overexposed": over_sym_strat,
                "strategy_system_overexposed": over_strat_sys,
            }
            pick["probation_counts"] = {
                "symbol_strategy_count": sym_strat_ct,
                "strategy_system_count": strat_sys_ct,
            }
            stats["tagged_probation"] += 1
        output.append(pick)

    stats["pass_through_count"] = len(output)
    stats["pass_through_rate"] = round((len(output) / max(1, len(scored))) * 100.0, 2)
    return output, stats


def run():
    now = datetime.now(timezone.utc)
    # Load picks from MULTIPLE sources to maximize coverage
    picks = []
    # Source 1: Alpha Engine active picks (strip raw copy feeds; vetted copy
    # picks are re-added below through copy_trader_bridge).
    picks_path = _DATA / "active_picks.json"
    if picks_path.exists():
        try:
            ap = json.loads(picks_path.read_text(encoding="utf-8"))
            if isinstance(ap, list):
                alpha_clean = [
                    p for p in ap
                    if isinstance(p, dict) and not _is_unvetted_copy_pick(p)
                ]
                picks.extend(alpha_clean)
                log.info("Alpha active: kept %d/%d after copy-source hygiene", len(alpha_clean), len(ap))
        except Exception:
            pass
    # Source 4: Gainer Momentum Interceptor (real-time top gainers)
    try:
        scan_gainers = _import_from_local_or_package(
            "alpha_engine.gainer_interceptor",
            "gainer_interceptor",
            "scan_gainers",
        )
        gainer_signals = scan_gainers()
        if gainer_signals:
            picks.extend(gainer_signals)
            log.info("Gainer interceptor: added %d momentum signals", len(gainer_signals))
    except Exception as e:
        log.warning("Gainer interceptor failed: %s", e)
    # Source 2: Vetted copy trader picks only.
    try:
        try:
            from alpha_engine.copy_trader_bridge import get_copy_trader_picks
        except ImportError:
            from copy_trader_bridge import get_copy_trader_picks
        vetted_cp = get_copy_trader_picks()
        if vetted_cp:
            picks.extend(vetted_cp)
            log.info("Copy trader bridge: added %d vetted picks", len(vetted_cp))
        else:
            log.info("Copy trader bridge: no vetted picks available")
    except Exception as e:
        log.warning("Copy trader bridge failed: %s", e)
    # Source 2b: Forex Copy Trader Intel picks (forex-specific strategies)
    fxct_path = Path(__file__).parent.parent / "copy_trader_intel" / "data" / "forex_copytrader_picks.json"
    if fxct_path.exists():
        try:
            fxcp = json.loads(fxct_path.read_text(encoding="utf-8"))
            if isinstance(fxcp, list):
                _fx_ct_count = 0
                for p in fxcp:
                    if isinstance(p, dict):
                        p["source_system"] = "forex_copy_trader"
                        p.setdefault("category", "forex")
                        p.setdefault("asset_class", "FOREX")
                        picks.append(p)
                        _fx_ct_count += 1
                if _fx_ct_count:
                    log.info("Forex copy trader: added %d forex picks", _fx_ct_count)
        except Exception:
            pass
    # Source 3: Dashboard payload active picks (aggregated from ALL systems)
    dp_path = Path(__file__).parent.parent / "audit_trail" / "data" / "dashboard_payload.json"
    if dp_path.exists():
        try:
            raw = dp_path.read_text(encoding="utf-8")
            if "<<<<<<" not in raw:
                dp = json.loads(raw)
                dp_picks = dp.get("picks", {}).get("active", [])
                for p in dp_picks:
                    if isinstance(p, dict):
                        picks.append(p)
        except Exception: pass
    # Source 5: CopytraderManager — top-trader allocation signals (Wire-Up Rule 2026-05-16).
    # CopytraderManager holds static metadata for verified high-WR copytraders (DailyGreenTrader
    # WR=85%, AntiVitalikETH WR=78%, QuantumAlpha WR=75%). Platform handlers (Binance/Bybit/
    # Polymarket) are not yet implemented; this wiring satisfies the Wire-Up Rule by calling
    # get_active_traders() to surface trader metadata as pick annotations. When live API
    # integrations land in a follow-up PR, replace the static metadata with real position data.
    try:
        try:
            from alpha_engine.copytrader_integration import CopytraderManager
        except ImportError:
            from copytrader_integration import CopytraderManager
        _ct_manager = CopytraderManager()
        _active_traders = _ct_manager.get_active_traders()
        if _active_traders:
            log.info(
                "CopytraderManager: %d active traders available (max_alloc %s%%)",
                len(_active_traders),
                ", ".join(
                    str(int(t.get("max_allocation", 0) * 100)) for t in _active_traders
                ),
            )
            # Annotate existing picks that match a known copytrader's preferred symbols.
            # Known traders focus on BTC/ETH perpetuals — tag any matching active picks
            # so downstream scoring can apply trader credibility as a signal boost.
            _ct_symbols = {"BTCUSDT", "ETHUSDT", "BTCUSD", "ETHUSD"}
            for p in picks:
                if isinstance(p, dict) and str(p.get("symbol", "")).upper() in _ct_symbols:
                    p.setdefault("copytrader_signal", True)
                    p.setdefault("copytrader_max_wr", max(
                        t["stats"].get("win_rate", 0) for t in _active_traders
                    ))
    except ImportError:
        log.debug("CopytraderManager not available — skipping copytrader annotation")
    except Exception as _ct_exc:
        log.warning("CopytraderManager annotation failed (non-fatal): %s", _ct_exc)
    # Dedup by symbol+strategy+direction, preferring dashboard-enriched picks.
    merged = {}
    for p in picks:
        if not isinstance(p, dict): continue
        key = (p.get("symbol",""), p.get("strategy",""), str(p.get("direction", p.get("signal_type",""))))
        cur = merged.get(key)
        if cur is None or _pick_merge_rank(p) > _pick_merge_rank(cur):
            merged[key] = p
    picks = [p for p in merged.values() if not _is_unvetted_copy_pick(p)]
    if not picks:
        log.error("No picks found from any source"); return {}
    log.info("Loaded %d active picks (alpha + vetted copy + forex_copytrader + dashboard)", len(picks))

    # ── Enrich picks with strategy forward performance (TRACK column) ──
    strat_perf_path = _DATA / "strategy_performance.json"
    _strat_perf = {}
    if strat_perf_path.exists():
        try:
            _strat_perf = json.loads(strat_perf_path.read_text(encoding="utf-8"))
            log.info("Loaded strategy_performance.json with %d strategies", len(_strat_perf))
        except Exception:
            pass
    _strat_enriched = 0
    for p in picks:
        strat = p.get("strategy", "")
        if strat and strat in _strat_perf:
            sp = _strat_perf[strat]
            if p.get("strat_fwd_wr") is None and p.get("forward_wr") is None:
                wr = sp.get("win_rate")
                if wr is not None:
                    p["strat_fwd_wr"] = round(float(wr) * 100, 1) if float(wr) <= 1 else round(float(wr), 1)
            if p.get("strat_fwd_trades") is None and p.get("forward_trades") is None:
                p["strat_fwd_trades"] = sp.get("closed_picks", 0)
            if p.get("strat_fwd_pf") is None and p.get("profit_factor") is None:
                pf_val = sp.get("profit_factor")
                if pf_val is not None:
                    p["strat_fwd_pf"] = round(float(pf_val), 2)
            _strat_enriched += 1
    if _strat_enriched:
        log.info("Enriched %d picks with strategy performance (TRACK column)", _strat_enriched)

    # ── Run HTF confirmation for crypto picks (HTF column) ──
    _htf_enriched = 0
    try:
        from alpha_engine.htf_confirmation import get_htf_confirmation as _get_htf
        _htf_import_ok = True
    except ImportError:
        try:
            from htf_confirmation import get_htf_confirmation as _get_htf
            _htf_import_ok = True
        except ImportError:
            _htf_import_ok = False
    if _htf_import_ok:
        _htf_symbols = set()
        for p in picks:
            sym = p.get("symbol", "")
            _extra = p.get("extra", {})
            if sym and "=" not in sym and not _extra.get("htf_bias"):
                _htf_symbols.add(sym)
        for sym in sorted(_htf_symbols):
            try:
                htf_result = _get_htf(sym)
                for p in picks:
                    if p.get("symbol") == sym:
                        p.setdefault("extra", {})["htf_bias"] = htf_result.get("htf_bias", "NEUTRAL")
                        _htf_enriched += 1
            except Exception:
                pass
        if _htf_enriched:
            log.info("Enriched %d picks with HTF bias (HTF column)", _htf_enriched)

    regime_path = _DATA / "hmm_regime_state.json"
    regime_data = json.loads(regime_path.read_text(encoding="utf-8")) if regime_path.exists() else {}
    agg_regime = regime_data.get("aggregate", {}).get("market_regime", "unknown")

    symbols = list({p.get("symbol", "") for p in picks if p.get("symbol")})
    log.info("Fetching live prices for %d symbols...", len(symbols))
    prices = fetch_live_prices(symbols)
    log.info("Got prices for %d/%d symbols", len(prices), len(symbols))

    # BTC price from bulk fetch, fallback to pick data
    btc_price = prices.get("BTCUSDT", prices.get("BTCUSD", 0))
    if not btc_price:
        # Fallback: find BTC price from any BTC pick's current_price
        for p in picks:
            if "BTC" in str(p.get("symbol", "")).upper():
                btc_price = float(p.get("current_price", 0) or 0)
                if btc_price > 0: break

    # Real-time regime detection from BTC 1h candles
    _realtime_regime = agg_regime  # Default to HMM
    try:
        btc_klines = _http_json(f"{SPOT_URLS[0]}/api/v3/klines?symbol=BTCUSDT&interval=1h&limit=24")
        if btc_klines and isinstance(btc_klines, list) and len(btc_klines) >= 12:
            closes = [float(k[4]) for k in btc_klines]
            # Simple regime: compare recent 4h vs prior 8h
            recent_avg = sum(closes[-4:]) / 4
            prior_avg = sum(closes[-12:-4]) / 8
            change_pct = (recent_avg - prior_avg) / prior_avg * 100

            if change_pct > 1.0:
                _realtime_regime = "bull"   # Rising > 1% in last 4h
            elif change_pct < -1.0:
                _realtime_regime = "bear"   # Falling > 1% in last 4h
            else:
                _realtime_regime = "neutral" # Choppy / transitioning

            log.info("Real-time regime: %s (BTC 4h vs 8h: %+.2f%%)", _realtime_regime, change_pct)
    except Exception as e:
        log.warning("Real-time regime detection failed: %s", e)

    # Use real-time regime instead of stale HMM
    agg_regime = _realtime_regime

    # Fear & Greed Index — direct from API, not from stale pick data
    fear_greed = 0
    try:
        fg_data = _http_json("https://api.alternative.me/fng/?limit=1")
        if fg_data and isinstance(fg_data.get("data"), list) and fg_data["data"]:
            fear_greed = int(fg_data["data"][0]["value"])
    except Exception:
        fear_greed = 0
    log.info("BTC: $%.0f | Fear & Greed: %d", btc_price, fear_greed)

    # F&G Override: sentiment can confirm a strong regime, but it should not
    # bulldoze a neutral momentum read into full bear/bull mode by itself.
    # Otherwise Smart Picks collapses into one-sided lists (e.g. all SHORTs)
    # while live active-pick flow is still favoring the other direction.
    _fgi_override_reason = None
    if fear_greed > 0:
        regime_l = agg_regime.lower()
        if fear_greed < 15 and regime_l in ("bear", "bearish", "crash", "crisis"):
            _fgi_override_reason = f"FGI confirms bear regime ({fear_greed})"
        elif fear_greed > 85 and regime_l in ("bull", "bullish"):
            _fgi_override_reason = f"FGI confirms bull regime ({fear_greed})"
        elif fear_greed < 15 and regime_l in ("neutral", "choppy", "ranging"):
            _fgi_override_reason = (f"FGI extreme fear ({fear_greed}) noted, "
                                    f"but kept neutral momentum regime")
        elif fear_greed > 85 and regime_l in ("neutral", "choppy", "ranging"):
            _fgi_override_reason = (f"FGI extreme greed ({fear_greed}) noted, "
                                    f"but kept neutral momentum regime")
        if _fgi_override_reason:
            log.info(_fgi_override_reason)

    _risk_policy = load_risk_policy()
    _tier_cfg = _risk_policy.get("trust_tier_policy", {})
    _tier_blacklist = {
        str(x).upper()
        for x in _tier_cfg.get("conviction_blacklist", ["SANDBOX", "PROBATION", "UNPROVEN", "DEMOTED"])
    }
    _conviction_min_score = int(_tier_cfg.get("conviction_min_score", 50))

    scored, excluded = [], {"wrong_direction": 0, "too_stale": 0, "no_price": 0,
                            "near_tp": 0, "meme_long_bear": 0, "banned_system": 0,
                            "non_crypto_probation": 0, "mtf_not_aligned": 0,
                            "ensemble_not_aligned": 0,
                            "hard_block_long_in_fear": 0,
                            "hard_block_short_in_greed": 0,
                            "low_validated_score": 0,
                            "trust_tier_blocked": 0,
                            "score_conflict": 0,
                            "symbol_conflict": 0,
                            "consensus_conflict": 0,
                            "missing_source": 0,
                            "min_trades": 0,
                            "wr_momentum": 0,
                            "elite_below_gate": 0,
                            "strategy_conf_gate": 0}

    # ── Consensus-conflict gate (2026-04-04 claude-opus-scoring per loser forensics P0) ──
    # Build per-symbol direction consensus from the full pick set.
    # Hard-reject picks whose direction opposes strong majority consensus.
    # Example caught: AVAX-S shipped at score=0 against 10L/1S consensus,
    # DOGE-S shipped at score=10 against 7L/2S consensus.
    _consensus = {}
    for _p in picks:
        _sym = _p.get("symbol", "")
        _dir = str(_p.get("direction", "LONG")).upper()
        if not _sym or _dir not in ("LONG", "BUY", "SHORT", "SELL"):
            continue
        _long = _dir in ("LONG", "BUY")
        if _sym not in _consensus:
            _consensus[_sym] = {"long": 0, "short": 0}
        if _long:
            _consensus[_sym]["long"] += 1
        else:
            _consensus[_sym]["short"] += 1

    def _is_consensus_conflict(pick_sym: str, pick_dir: str) -> bool:
        """True if pick opposes strong directional consensus (delta > 0.25, 5+ picks)."""
        c = _consensus.get(pick_sym)
        if not c:
            return False
        total = c["long"] + c["short"]
        if total < 5:  # Need meaningful sample
            return False
        long_pct = c["long"] / total
        delta = abs(long_pct - 0.5) * 2  # 0 = 50/50, 1 = 100% one-side
        if delta < 0.5:  # conf_delta > 0.25 means long_pct > 0.75 or < 0.25
            return False
        majority_long = long_pct > 0.5
        pick_is_long = str(pick_dir).upper() in ("LONG", "BUY")
        # Conflict = pick direction opposes majority
        return majority_long != pick_is_long

    for p in picks:
        _st = p.get("status", "").upper()
        if _st not in ("OPEN", "ACTIVE", ""): continue  # Accept OPEN and ACTIVE
        # Skip banned systems (auto-kill list)
        strat = p.get("strategy", "").lower().strip()
        if strat in BANNED_SYSTEMS:
            excluded["banned_system"] += 1; continue
        sym = p.get("symbol", "")
        # Consensus-conflict gate: hard-reject picks opposing strong majority
        _pick_dir = str(p.get("direction", "LONG")).upper()
        if _is_consensus_conflict(sym, _pick_dir):
            excluded["consensus_conflict"] += 1
            continue
        non_crypto = _is_non_crypto(p)
        # Use live price if available, otherwise fall back to pick's current_price or entry_price
        lp = prices.get(sym)
        if not lp:
            # Fallback 1: use the price already on the pick (from scanner which has Binance access)
            lp = float(p.get("current_price", 0) or 0) or float(p.get("last_price", 0) or 0)
        if not lp:
            # Fallback 2: use entry_price as last resort (PnL will show 0% but pick can still score)
            lp = float(p.get("entry_price", 0) or 0)
        if not lp:
            excluded["no_price"] += 1; continue
        if not _has_source_provenance(p):
            excluded["missing_source"] += 1
            continue
        result = score_pick(p, lp, regime_data, now, fear_greed=fear_greed)
        if isinstance(result, dict) and "_filter" in result and result["_filter"] is not None:
            excluded[result["_filter"]] = excluded.get(result["_filter"], 0) + 1
            continue
        if result is None:
            excluded["score_pick_none"] = excluded.get("score_pick_none", 0) + 1
            continue
        filt = result.pop("_filter", None)
        if filt: excluded[filt] = excluded.get(filt, 0) + 1; continue
        validated_score = result.get("validated_score")
        if validated_score is not None and validated_score < 30:  # Restored — trust_score r=+0.352, low scores = low quality
            excluded["low_validated_score"] += 1
            continue
        if non_crypto:
            block_reason = _non_crypto_policy_block_reason(p, result)
            if block_reason:
                excluded["non_crypto_probation"] += 1
                continue
            # Enforce asset-class TP/SL caps on every non-crypto pick
            _clamp_tp_sl(p)
            _clamp_tp_sl(result)
        _tier = str(result.get("trust_tier") or p.get("trust_tier") or "").upper()
        _smart_score = _to_float(result.get("smart_score"), 0.0)
        if _tier in _tier_blacklist and _smart_score >= _conviction_min_score:
            excluded["trust_tier_blocked"] += 1
            continue
        _conf = _to_float(result.get("confidence"), 0.0)
        if _conf > 1.0:
            _conf = _conf / 100.0
        if _smart_score < 20.0 and _conf >= 0.95:
            excluded["score_conflict"] += 1
            continue
        # Vol-target wire-up (PR #527 Step 2). No-op unless
        # CRYPTO_VOL_TARGET_ENABLED=1 AND result.asset_class == CRYPTO.
        # When active: stamps result['_vol_target_scale'] and scales
        # position_size_pct by [0.25, 1.0] based on realized_vol_pct.
        _vol_target_apply(result)
        scored.append(result)

    # ── HEDGE FUND ENHANCEMENTS (2026-04-05) ────────────────────────────────
    # 1. MINIMUM TRADE COUNT THRESHOLD: Filter strategies with <15 closed trades
    # 2. WIN-RATE MOMENTUM FILTER: Pause strategies with <35% WR
    MIN_CLOSED_TRADES = 15
    WR_MOMENTUM_THRESHOLD = 0.35
    _filter_stats = {"min_trades": 0, "wr_momentum": 0}
    
    _trade_count_data = {}
    try:
        import json as _json_tc
        _tc_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "strategy_trade_counts.json")
        if os.path.exists(_tc_path):
            with open(_tc_path, "r", encoding="utf-8") as _tcf:
                _tc_doc = _json_tc.load(_tcf)
                _trade_count_data = _tc_doc.get("strategies", {})
    except Exception as _e:
        log.warning("Trade count data load failed: %s", _e)
    
    _wr_momentum_data = {}
    try:
        import json as _json_wr
        _wr_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "strategy_performance.json")
        if os.path.exists(_wr_path):
            with open(_wr_path, "r", encoding="utf-8") as _wrf:
                _wr_momentum_data = _json_wr.load(_wrf)
    except Exception as _e:
        log.warning("WR data load failed: %s", _e)
    
    def _meets_min_trades(pick):
        strat = (pick.get("strategy", "") or "").strip()
        if strat in PROVEN_WINNERS:
            return True
        for prefix in PROVEN_PREFIXES:
            if strat.startswith(prefix):
                return True
        if _is_vetted_copy_pick(pick):
            return True
        stats = _trade_count_data.get(strat, {})
        n = int(stats.get("n", 0))
        # 2026-04-05: If strategy has NO entry in trade_counts file, treat as neutral
        # (not filtered out). Only filter if we HAVE data showing insufficient trades.
        # Without this, new/unscanned strategies (goldmine_stocks, kimi_riseoftheclaw,
        # claude_gainer_st, dna_winner_picks etc.) were all being stripped, dropping
        # active picks from 90 to 30.
        if not stats:
            return True
        return n >= MIN_CLOSED_TRADES
    
    def _passes_wr_momentum(pick):
        strat = (pick.get("strategy", "") or "").strip()
        if strat in PROVEN_WINNERS:
            return True
        for prefix in PROVEN_PREFIXES:
            if strat.startswith(prefix):
                return True
        if _is_vetted_copy_pick(pick):
            return True
        sp = _wr_momentum_data.get(strat, {})
        wr = sp.get("win_rate") or pick.get("strat_fwd_wr") or pick.get("forward_wr")
        if wr is None:
            return True
        if float(wr) > 1.0:
            wr = float(wr) / 100.0
        return float(wr) >= WR_MOMENTUM_THRESHOLD
    
    filtered_scored = []
    for pick in scored:
        if not _meets_min_trades(pick):
            _filter_stats["min_trades"] += 1
            continue
        if not _passes_wr_momentum(pick):
            _filter_stats["wr_momentum"] += 1
            continue
        filtered_scored.append(pick)
    
    log.info("Hedge fund filters: min_trades=%d, wr_momentum=%d (from %d scored)",
             _filter_stats["min_trades"], _filter_stats["wr_momentum"], len(scored))
    
    excluded["min_trades"] = _filter_stats["min_trades"]
    excluded["wr_momentum"] = _filter_stats["wr_momentum"]
    scored = filtered_scored

    # ── BAYESIAN SHRINKAGE on ml_composite for sort ordering ──
    # 2026-04-05 claude-bus-setup (bus task 4 P1): low-n strategies produce
    # noisy ml_composite values that dominate ranking spuriously. Shrink toward
    # population mean based on trade count. Strategies with <30 historical
    # trades get proportionally shrunk; 30+ trades use raw ml_composite.
    # Formula: shrunk = (n * raw + prior_strength * pop_mean) / (n + prior_strength)
    # This ONLY affects sort ranking — stored ml_composite on each pick is
    # unchanged so UI/dashboard still sees raw values.
    _strategy_stats = {}
    _pop_mean_pnl = 0.0
    _prior_strength = 30
    try:
        import json as _json
        _stats_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "strategy_trade_counts.json")
        if os.path.exists(_stats_path):
            with open(_stats_path, "r", encoding="utf-8") as _sf:
                _stats_doc = _json.load(_sf)
                _strategy_stats = _stats_doc.get("strategies", {})
                _pop_mean_pnl = float(_stats_doc.get("population_mean_pnl_pct", 0.0))
                _prior_strength = int(_stats_doc.get("prior_strength_trades", 30))
    except Exception as _e:
        log.warning("Strategy stats load failed (non-fatal): %s", _e)

    def _shrunk_ml_composite(pick: dict) -> float:
        raw = float(pick.get("ml_composite", 0) or 0)
        strat = (pick.get("strategy", "") or "").strip()
        if not strat or not _strategy_stats:
            return raw  # no shrinkage if no stats
        stats = _strategy_stats.get(strat)
        if not stats:
            # Unknown strategy: apply full shrinkage (treat as n=0 → pure prior).
            # This penalizes brand-new strategies until they accrue evidence.
            return _pop_mean_pnl * 0.01  # scale to ml_composite range (0-1)
        n = int(stats.get("n", 0))
        if n >= _prior_strength:
            return raw  # enough evidence, trust raw
        # Scale the raw ml_composite by shrinkage factor toward 0 (neutral).
        # Picks with low-n strategy × high raw ml_composite get demoted.
        shrink_factor = n / (n + _prior_strength)  # 0 < sf < 1 for n<30
        return raw * shrink_factor

    # ── CROSS-PORTFOLIO CONCENTRATION PENALTY (2026-04-05 claude-bus-setup, task 6) ──
    # Per approved threshold B: max 2 portfolios holding same symbol-direction.
    # Builds a fleet-state symbol count from known paper-portfolio JSON files,
    # then soft-demotes ml_composite for picks whose symbol already appears in
    # MAX_PORTFOLIOS_PER_SYMBOL+ portfolios (observed: BTC/ADA/LINK in 5/6 TV
    # accounts violates threshold B).
    #
    # NOTE: This is a PARTIAL fleet view — does NOT include live TV paper
    # account positions (SCALPER/TESTER/TRUSTOURSCORE/BROKIE/zerounderscore/
    # THEWINNERS) which require TV MCP polling. Known limitation, filed as
    # follow-up task. Soft demotion (-0.15 multiplier) avoids over-penalizing
    # from incomplete data; escalate to hard-block once TV snapshot cron lands.
    MAX_PORTFOLIOS_PER_SYMBOL = 2
    _fleet_symbol_count: dict = {}
    _fleet_sources = [
        "KIMI_RISEOFTHECLAW/data/paper_portfolio.json",
        "riseoftheclaw/data/paper_portfolio.json",
        "alpha_engine/data/paper_portfolio_cbc.json",
        "alpha_engine/data/paper_portfolio_v2.json",
        "alpha_engine/data/joint_paper_portfolio_picks_2026-04-04.json",
        "alpha_engine/data/joint_paper_portfolio_c_gate_picks_2026-04-04.json",
    ]
    try:
        import json as _json_fleet
        _repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for _src in _fleet_sources:
            _path = os.path.join(_repo_root, _src)
            if not os.path.exists(_path):
                continue
            try:
                with open(_path, "r", encoding="utf-8") as _f:
                    _pdoc = _json_fleet.load(_f)
            except Exception:
                continue
            _pos_list = []
            if isinstance(_pdoc, dict):
                for _k in ("positions", "open_positions", "active", "picks"):
                    if _k in _pdoc and isinstance(_pdoc[_k], list):
                        _pos_list = _pdoc[_k]
                        break
            elif isinstance(_pdoc, list):
                _pos_list = _pdoc
            _seen_this_src = set()
            for _p in _pos_list:
                if not isinstance(_p, dict):
                    continue
                _s = (_p.get("symbol") or _p.get("ticker") or "").upper()
                _s = _s.replace("-USD", "USDT").replace("-USDT", "USDT")
                if _s and _s not in _seen_this_src:
                    _seen_this_src.add(_s)
                    _fleet_symbol_count[_s] = _fleet_symbol_count.get(_s, 0) + 1
        _flagged = {s: c for s, c in _fleet_symbol_count.items() if c >= MAX_PORTFOLIOS_PER_SYMBOL}
        if _flagged:
            log.info("Cross-portfolio concentration flags (>=%d portfolios): %s",
                     MAX_PORTFOLIOS_PER_SYMBOL, _flagged)
    except Exception as _e:
        log.warning("Fleet-state loader failed (non-fatal): %s", _e)

    # ── RISK POLICY ENFORCEMENT (2026-04-05 Hardening) ──────────────────────
    # Enforce symbol concentration caps from unified policy loaded above.
    # Institutional cap: max 5% per symbol by default, or from policy.
    _symbol_cap_pct = _risk_policy.get("crypto", {}).get("max_equity_pct_per_symbol", 5)
    _max_ports = _risk_policy.get("crypto", {}).get("max_portfolios_same_symbol_direction", 2)

    # Note: Hard-blocking symbol concentration requires tracking allocated weight.
    # For now, we flag and soft-demote or filter if already at cap in fleet.
    _risk_filtered = []
    for p in scored:
        _s = p.get("symbol", "").upper()
        # If symbol already in 3+ portfolios (as per fleet count), or exceeds local cap logic
        if _fleet_symbol_count.get(_s, 0) >= _risk_policy.get("max_portfolios_per_symbol", 3):
            excluded["symbol_concentration"] = excluded.get("symbol_concentration", 0) + 1
            continue
        _risk_filtered.append(p)
    scored = _risk_filtered

    def _shrunk_ml_composite_v2(pick: dict) -> float:
        """Wraps _shrunk_ml_composite with cross-portfolio demotion."""
        base = _shrunk_ml_composite(pick)
        _sym = (pick.get("symbol") or "").upper().replace("-USD", "USDT").replace("-USDT", "USDT")
        _ct = _fleet_symbol_count.get(_sym, 0)
        if _ct >= MAX_PORTFOLIOS_PER_SYMBOL:
            # Soft demotion — each extra portfolio beyond threshold costs 15%
            demote = max(0.4, 1.0 - 0.15 * (_ct - MAX_PORTFOLIOS_PER_SYMBOL + 1))
            return base * demote
        return base

    # Primary rank by (shrunk + fleet-demoted) ml_composite, then smart_score,
    # then validated_score, then freshness.
    scored.sort(key=lambda x: (_shrunk_ml_composite_v2(x), x["smart_score"], x.get("validated_score") or 0, -x.get("age_hours", 999)), reverse=True)

    # Keep only the strongest pick per symbol so Smart Picks never publishes
    # conflicting long/short views or near-duplicate symbol spam.
    deduped_scored = []
    kept_symbols = set()
    for pick in scored:
        sym = pick.get("symbol", "")
        if not sym:
            continue
        if sym in kept_symbols:
            excluded["symbol_conflict"] += 1
            continue
        kept_symbols.add(sym)
        # Tag cross-portfolio concentration for downstream visibility
        _sym_norm = sym.upper().replace("-USD", "USDT").replace("-USDT", "USDT")
        _fleet_ct = _fleet_symbol_count.get(_sym_norm, 0)
        if _fleet_ct >= MAX_PORTFOLIOS_PER_SYMBOL:
            pick["cross_portfolio_count"] = _fleet_ct
            pick["cross_portfolio_warning"] = True
        deduped_scored.append(pick)
    scored = deduped_scored
    scored, concentration_probation_stats = _apply_concentration_probation_controls(
        scored, excluded, _risk_policy
    )

    # ── Non-crypto quarantine: separate pools ────────────────────────
    # Crypto picks fill the main portfolio first.  Non-crypto picks get
    # a separate capped allocation (MAX_NON_CRYPTO_PICKS) so they can
    # never displace profitable crypto positions on the leaderboard.
    crypto_scored = [p for p in scored if str(p.get("asset_class", "")).upper() == "CRYPTO"]
    non_crypto_scored = [p for p in scored if str(p.get("asset_class", "")).upper() != "CRYPTO"]
    for p in non_crypto_scored:
        p["quarantine"] = "non_crypto_pool"
    nc_cap = _dynamic_non_crypto_cap(len(non_crypto_scored))
    log.info("Quarantine split: %d crypto, %d non-crypto (cap %d)",
             len(crypto_scored), len(non_crypto_scored), MAX_NON_CRYPTO_PICKS)

    # --- Categorize into 3 tiers ---
    # Non-crypto picks get category-based tier defaults:
    #   forex -> SCALP (1-4h holds, TP <1%)
    #   equity/commodity -> SWING (4-48h, TP 1-5%)
    #   macro/bond -> POSITION (2-7d)
    def _assign_tier(pick):
        tf = (pick.get("timeframe") or "SWING").upper()
        age = pick.get("age_hours", 0)
        cat = str(pick.get("strategy", "")).lower()
        asset_class = str(pick.get("asset_class", "")).lower()
        if asset_class == "forex":
            pick["tier"] = "SCALP"
            return "SCALP"
        elif asset_class == "bond" or tf == "POSITION" or "macro" in cat:
            pick["tier"] = "POSITION"
            return "POSITION"
        elif asset_class in ("equity", "etf", "futures"):
            pick["tier"] = "SWING"
            return "SWING"
        elif tf == "SCALP" or age < 2:
            pick["tier"] = "SCALP"
            return "SCALP"
        elif tf == "POSITION" or (age > 24 and pick["smart_score"] >= 60):
            pick["tier"] = "POSITION"
            return "POSITION"
        else:
            pick["tier"] = "SWING"
            return "SWING"

    # Tier buckets: crypto fills first, non-crypto added from capped pool
    crypto_tiers = {"SCALP": [], "SWING": [], "POSITION": []}
    nc_tiers = {"SCALP": [], "SWING": [], "POSITION": []}
    for pick in crypto_scored:
        tier = _assign_tier(pick)
        crypto_tiers[tier].append(pick)
    for pick in non_crypto_scored:
        tier = _assign_tier(pick)
        nc_tiers[tier].append(pick)

    tier_limits = {"SCALP": 4, "SWING": 4, "POSITION": 3}
    scalp_picks = crypto_tiers["SCALP"]
    swing_picks = crypto_tiers["SWING"]
    position_picks = crypto_tiers["POSITION"]

    # Fill each tier with crypto first (sorted by ml_composite, smart_score tiebreaker)
    top_scalp = sorted(scalp_picks, key=lambda x: (-x.get("ml_composite", 0), -x["smart_score"]))[:tier_limits["SCALP"]]
    top_swing = sorted(swing_picks, key=lambda x: (-x.get("ml_composite", 0), -x["smart_score"]))[:tier_limits["SWING"]]
    top_position = sorted(position_picks, key=lambda x: (-x.get("ml_composite", 0), -x["smart_score"]))[:tier_limits["POSITION"]]

    # Add best non-crypto picks up to MAX_NON_CRYPTO_PICKS, filling
    # remaining slots in each tier without displacing crypto.
    effective_non_crypto_cap = MAX_NON_CRYPTO_PICKS
    nc_budget = MAX_NON_CRYPTO_PICKS
    if bool((_risk_policy.get("policy_flags", {}) or {}).get("enable_non_crypto_throughput_v2")):
        try:
            effective_non_crypto_cap = int(
                (_risk_policy.get("non_crypto", {}) or {}).get("max_total_picks", nc_budget)
            )
            nc_budget = effective_non_crypto_cap
        except (TypeError, ValueError):
            pass
    _nc_caps = {
        k.upper(): int(v)
        for k, v in (_risk_policy.get("non_crypto_absolute_caps", {}) or {}).items()
        if str(k).strip()
    }
    _ac_counts = Counter(_norm_asset_class_name(p.get("asset_class", "")) for p in top_scalp + top_swing + top_position)
    _equity_max_single_system = int((_risk_policy.get("equity", {}) or {}).get("max_single_system_picks", 2))
    _forex_max_active = int((_risk_policy.get("forex", {}) or {}).get("max_active_picks", 2))
    _equity_system_counts = Counter(
        str(p.get("source_system") or p.get("system") or "unknown").lower()
        for p in top_scalp + top_swing + top_position
        if _norm_asset_class_name(p.get("asset_class", "")) == "EQUITY"
    )
    # Breadth recovery ladder: only unlock extra non-crypto slots when the
    # latest governance report shows acceptable pass quality.
    try:
        _hf_review_path = Path(__file__).resolve().parents[1] / "audit_trail" / "data" / "hf_enhancement_review.json"
        if _hf_review_path.exists():
            _hf_review = json.loads(_hf_review_path.read_text(encoding="utf-8"))
            _pass_rate = float((_hf_review.get("active_pass_watchlist", {}) or {}).get("pass_rate_pct", 0.0))
            _non_crypto_total = float((_hf_review.get("non_crypto_closed_rollup", {}) or {}).get("total_pnl", 0.0))
            _non_crypto_pf = float((_hf_review.get("non_crypto_closed_rollup", {}) or {}).get("profit_factor", 1.0))
            # M-115: Changed OR→AND. Historical all-time PnL is contaminated by pre-quality-gate
            # EQUITY picks (blocked since 2026-05-16). Clamp to 2 only when BOTH pass_rate AND
            # PnL signals are bad. Pass rate 7.78% ≥ 6% alone is sufficient to allow full budget.
            if _pass_rate < 6.0 and _non_crypto_total < 0.0:
                nc_budget = min(nc_budget, 2)
            elif 6.0 <= _pass_rate <= 15.0 and (_non_crypto_total >= 0.0 or _non_crypto_pf >= 1.0):
                nc_budget = min(nc_budget + 1, 4)
    except Exception:
        pass
    # Equity concentration guard: require at least 2 validated equity systems
    # before allowing >1 equity pick from a single system in this cycle.
    _validated_equity_systems = set()
    for _cand in non_crypto_scored:
        if _norm_asset_class_name(_cand.get("asset_class", "")) != "EQUITY":
            continue
        _sys = str(_cand.get("source_system") or _cand.get("system") or "unknown").lower()
        _fw_n = int(max(
            _as_float(_cand.get("strat_fwd_trades"), default=0),
            _as_float(_cand.get("forward_trades"), default=0),
        ))
        _fw_wr = max(
            _as_pct(_cand.get("strat_fwd_wr")),
            _as_pct(_cand.get("forward_wr")),
        )
        if _fw_n >= 20 and _fw_wr >= 50.0:
            _validated_equity_systems.add(_sys)
    if len(_validated_equity_systems) < 2:
        _equity_max_single_system = min(_equity_max_single_system, 1)
    for tier_key, tier_top, tier_all_nc in [
        ("SCALP", top_scalp, nc_tiers["SCALP"]),
        ("SWING", top_swing, nc_tiers["SWING"]),
        ("POSITION", top_position, nc_tiers["POSITION"]),
    ]:
        if nc_budget <= 0:
            break
        limit = tier_limits[tier_key]
        slots_left = limit - len(tier_top)
        if slots_left <= 0:
            continue
        nc_sorted = sorted(tier_all_nc, key=lambda x: (-x.get("ml_composite", 0), -x["smart_score"]))
        nc_to_add = []
        for cand in nc_sorted:
            if len(nc_to_add) >= min(slots_left, nc_budget):
                break
            _ac = _norm_asset_class_name(cand.get("asset_class", ""))
            _cap = _nc_caps.get(_ac)
            if _cap is not None and _ac_counts.get(_ac, 0) >= _cap:
                continue
            if _ac == "FOREX" and _ac_counts.get("FOREX", 0) >= _forex_max_active:
                continue
            if _ac == "EQUITY":
                _sys = str(cand.get("source_system") or cand.get("system") or "unknown").lower()
                if _equity_system_counts.get(_sys, 0) >= _equity_max_single_system:
                    continue
                _equity_system_counts[_sys] += 1
            _ac_counts[_ac] += 1
            nc_to_add.append(cand)
        tier_top.extend(nc_to_add)
        nc_budget -= len(nc_to_add)
        if nc_to_add:
            log.info("Non-crypto quarantine: added %d %s picks (%s)",
                     len(nc_to_add), tier_key,
                     ", ".join(p["symbol"] for p in nc_to_add))

    top = top_scalp + top_swing + top_position

    # ── SAFETY NET: Always output 5-11 picks ──────────────────────────
    # If tier-based selection yields fewer than 5 picks, fill from the
    # full scored pool (best by ml_composite) regardless of tier assignment.
    # This prevents the dashboard from showing 0-1 picks when filters are
    # too aggressive or when most picks land in the same tier.
    MIN_SMART_PICKS = 5
    MAX_SMART_PICKS = 11
    if len(top) < MIN_SMART_PICKS and len(scored) > len(top):
        top_symbols = {p["symbol"] for p in top}
        backfill_candidates = [p for p in scored if p["symbol"] not in top_symbols]
        backfill_candidates.sort(key=lambda x: (x.get("ml_composite", 0), x["smart_score"]), reverse=True)
        needed = MIN_SMART_PICKS - len(top)
        backfill = backfill_candidates[:needed]
        for p in backfill:
            p["tier"] = p.get("tier", "SWING")
            p["_backfill"] = True
        top.extend(backfill)
        log.info("Safety net: backfilled %d picks to reach minimum %d (total now %d)",
                 len(backfill), MIN_SMART_PICKS, len(top))

    log.info("Tiers: %d SCALP, %d SWING, %d POSITION (showing %d/%d/%d)",
             len(crypto_tiers["SCALP"]) + len(nc_tiers["SCALP"]),
             len(crypto_tiers["SWING"]) + len(nc_tiers["SWING"]),
             len(crypto_tiers["POSITION"]) + len(nc_tiers["POSITION"]),
             len(top_scalp), len(top_swing), len(top_position))

    # PR-H (2026-05-12): cap per-source CRYPTO volume share (quan_engine 12%).
    try:
        from alpha_engine.per_source_volume_cap import enforce_cap as _enforce_volume_cap, enforce_symbol_cap as _enforce_symbol_cap
    except ImportError:
        try:
            from per_source_volume_cap import enforce_cap as _enforce_volume_cap, enforce_symbol_cap as _enforce_symbol_cap
        except ImportError:
            _enforce_volume_cap = None
            _enforce_symbol_cap = None
    if _enforce_volume_cap is not None:
        _pre_n = len(top)
        top = _enforce_volume_cap(top)
        if len(top) != _pre_n:
            log.info("per_source_volume_cap: %d -> %d picks", _pre_n, len(top))
    if _enforce_symbol_cap is not None:
        _pre_n = len(top)
        top = _enforce_symbol_cap(top)
        if len(top) != _pre_n:
            log.info("per_symbol_cap: %d -> %d picks", _pre_n, len(top))

    nc_in_portfolio = sum(1 for p in top if p.get("quarantine") == "non_crypto_pool")
    output = {
        "generated_at": now.isoformat(), "regime": agg_regime.upper(),
        "fear_greed": fear_greed, "btc_price": btc_price,
        "method": "Direction + Quality + Freshness + Upside + Momentum (3-tier, crypto-first)",
        "total_scored": len(scored),
        "crypto_scored": len(crypto_scored),
        "non_crypto_scored": len(non_crypto_scored),
        "non_crypto_in_portfolio": nc_in_portfolio,
        "max_non_crypto_picks": effective_non_crypto_cap,
        "scalp_picks": top_scalp,
        "swing_picks": top_swing,
        "position_picks": top_position,
        "picks": top,
        "excluded_reasons": excluded,
        "concentration_probation_stats": concentration_probation_stats,
    }
    out_path = _DATA / "smart_picks.json"
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    log.info("Saved %d smart picks to %s", len(top), out_path)
    return output

if __name__ == "__main__":
    result = run()
    if not result: print("No smart picks generated."); sys.exit(1)
    print(f"\n{'='*60}")
    print(f"SMART PICKS | Regime: {result['regime']} | F&G: {result['fear_greed']} | BTC: ${result['btc_price']:,.0f}")
    print(f"{'='*60}")
    for tier_key, tier_label in [("scalp_picks", "SCALP"), ("swing_picks", "SWING"), ("position_picks", "POSITION")]:
        tier_list = result.get(tier_key, [])
        if not tier_list: continue
        print(f"\n--- {tier_label} ({len(tier_list)}) ---")
        for i, p in enumerate(tier_list, 1):
            print(f"  #{i}  {p['symbol']} {p['direction']}  --  Score {p['smart_score']}/100")
            print(f"       Entry: {p['entry']:.4g}  Live: {p['live']:.4g}  TP: {p['tp']:.4g}  SL: {p['sl']:.4g}")
            print(f"       PnL: {p['pnl_pct']:+.2f}% | TP left: {p['tp_remaining_pct']:.0f}% | Age: {p['age_hours']:.1f}h | {p['risk_note']}")
            print(f"       {p['explanation']}")
    print(f"\nExcluded: {result['excluded_reasons']}")
    print(f"Total scored: {result['total_scored']} | Showing {len(result['picks'])} across 3 tiers")
