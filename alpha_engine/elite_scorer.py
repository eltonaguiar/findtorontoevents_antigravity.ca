#!/usr/bin/env python3
"""
ALPHA_ENGINE -- Elite Scorer (IC-calibrated v2 — halved, not zeroed 2026-03-26)
=========================================================================
IC analysis (ic_weighted_selector) found only 4 of 21 components predict winners.
v1 (2026-03-24): ZEROED 7 anti-predictive components. RESULT: scoring INVERTED
  — top-scored picks had 9% WR, bottom-scored had 41% WR.
  Root cause: regime_bonus dominated unchecked, pushing losing LONGs to top.
v2 (2026-03-26): HALVED anti-predictive components instead of zeroing.
  Individual IC was measured on historical data where ALL components were active.
  Removing them changed dynamics. Halving preserves counterbalancing effect
  while reducing noise. See decile_test.py.

ACTIVE components:
  - Forward-validated win rate (0-40 pts) -- IC=+0.17, DOUBLED weight
  - Regime bonus (0-20 pts) -- IC=+0.19, BOOSTED
  - Technical alignment (-30 to +5 pts) -- IC=+0.16, BOOSTED penalties
  - ML replacement score (0-9 pts) -- HALVED from IC analysis (v2), was 18
  - Source system tier (0-10 pts) -- HALVED from IC analysis (v2), was 20
  - Leverage Safety (0-5 pts) -- HALVED from IC analysis (v2), was 10
  - Age freshness (-2 to +2 pts) -- HALVED from IC analysis (v2), was -5 to +5
  - Position performance -- ZEROED (P1-05: backward-looking momentum, not predictive)
  - Volume confirmation (-8 to +5 pts) -- kept (neutral)
  - Signal quality (0-10 pts) -- kept (neutral)
  - Confluence PENALTY (-5 to 0 pts) -- kept (contrarian signal)

ZEROED components (truly dead):
  - Proven strategy bonus: ZEROED (IC=-0.003, basically dead)
  - Risk:Reward ratio: ZEROED (IC=-0.127)
  - Monte Carlo: ZEROED (IC anti-predictive, disabled earlier)
  - Meta-label: ZEROED (disabled earlier)
  - Hindsight winner: ZEROED (disabled earlier)
  - Skyrocket potential: ZEROED (disabled earlier)

Usage:
  from elite_scorer import compute_elite_score, enrich_picks_with_elite_score
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Optional

_logger = logging.getLogger("elite_scorer")

# ---------------------------------------------------------------------------
# Confidence tier coercion (BUGFIX 2026-05-22)
#
# Several upstream pick generators (ml_crypto_predictor's live_picks_tracker,
# polymarket_scraper, claude_gainer_ml/live_scanner) emit `confidence` as a
# STRING TIER ('HIGH'/'MEDIUM'/'LOW') instead of a numeric probability. When
# these picks flowed into compute_ml_replacement_score's
#     conf = float(pick.get("confidence", 0) or 0)
# the call raised ValueError ("could not convert string to float: 'LOW'"),
# which bubbled up to enrich_picks_with_elite_score's catch-all and assigned
# the silent fallback `elite_score = 25` for every affected pick. This
# repeatedly hit the 9 BTC/ETH/SOL/XRP/ADA/AVAX/DOT/LTC/BCH picks emitted
# by the live ML tracker on the MySQL Trading Picks Sync workflow.
#
# Mapping rationale: matches the empirical thresholds in
# ml_crypto_predictor/enhanced_models/live_picks_tracker.py:391-396 where
#   prob >= 0.75 -> HIGH, prob >= 0.65 -> MEDIUM, else LOW.
# We use the midpoint of each band so the scorer assigns a meaningful score
# rather than masking the value with 0 (and triggering the underconfidence
# floor).
# ---------------------------------------------------------------------------
_CONFIDENCE_TIER_MAP: dict[str, float] = {
    "HIGH": 0.80,
    "MEDIUM": 0.68,
    "LOW": 0.50,
    # Generous synonyms occasionally seen in pick metadata
    "VERY_HIGH": 0.90,
    "ULTRA": 0.90,
    "STRONG": 0.80,
    "MODERATE": 0.68,
    "WEAK": 0.50,
    "VERY_LOW": 0.35,
}


def coerce_confidence(value, default: float = 0.0) -> float:
    """Robustly convert a confidence value (numeric OR tier-string) to float.

    - Numeric values are passed through float().
    - String tier labels ('HIGH'/'MEDIUM'/'LOW' and synonyms, case-insensitive)
      are mapped to numeric midpoints via _CONFIDENCE_TIER_MAP.
    - Unparseable values log a WARNING and return `default` — we intentionally
      DO NOT silently mask (the silent fallback that this replaces wiped the
      score to 25 on 9 picks per cycle of the MySQL sync workflow).
    """
    if value is None or value == "":
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return default
        # Try numeric first ("0.72")
        try:
            return float(s)
        except ValueError:
            pass
        # Try tier label
        key = s.upper().replace("-", "_").replace(" ", "_")
        if key in _CONFIDENCE_TIER_MAP:
            return _CONFIDENCE_TIER_MAP[key]
        _logger.warning(
            "elite_scorer: unparseable confidence value %r -- using default %s",
            value,
            default,
        )
        return default
    # Anything else (list/dict/etc.)
    _logger.warning(
        "elite_scorer: unexpected confidence type %s (%r) -- using default %s",
        type(value).__name__,
        value,
        default,
    )
    return default

# ---------------------------------------------------------------------------
# Outlier symbols excluded from strategy performance stats.
# These symbols had outsized PnL (e.g. FETUSDT = 153.6% of total PnL) that
# inflates win rates and profit factors, masking the true system performance
# of -1,582% PnL.  Trades on these symbols are still EXECUTED -- they are
# only excluded from the metrics used for scoring and auto-tuning.
# ---------------------------------------------------------------------------
OUTLIER_SYMBOLS: set[str] = {"FETUSDT", "RENDERUSDT"}

# ---------------------------------------------------------------------------
# Source-level concentration guards.
# Some source families have real edge, but only on a narrow symbol subset.
# Penalize non-core symbols so that one source's winning niche does not
# overpromote unrelated symbols into the active/smart baskets.
# ---------------------------------------------------------------------------
SOURCE_CORE_SYMBOLS: dict[str, set[str]] = {
    "quan_engine": {"TAOUSDT", "HYPEUSDT", "TRXUSDT"},
}

# ---------------------------------------------------------------------------
# Market cap tier lookup (updated quarterly).
# Paper trade analysis: large-cap coins (PAXG, SOL, ZEC, DOGE) ALL won,
# micro-caps (REZ, RESOLV) ALL lost — regardless of score.
# Tier 1 = top 20 by mcap, Tier 2 = top 50.
# ---------------------------------------------------------------------------
TIER1_COINS: set[str] = {
    'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT',
    'ADAUSDT', 'TRXUSDT', 'AVAXUSDT', 'DOTUSDT', 'LINKUSDT', 'SHIBUSDT',
    'LTCUSDT', 'BCHUSDT', 'NEARUSDT', 'UNIUSDT', 'APTUSDT', 'RENDERUSDT',
    'FETUSDT', 'ATOMUSDT',
}  # top 20 by mcap

TIER2_COINS: set[str] = {
    'AAVEUSDT', 'INJUSDT', 'SUIUSDT', 'ARBUSDT', 'OPUSDT', 'FILUSDT',
    'IMXUSDT', 'GRTUSDT', 'AXSUSDT', 'SANDUSDT', 'MANAUSDT', 'ENAUSDT',
    'ZECUSDT', 'QNTUSDT', 'TAOUSDT', 'RUNEUSDT', 'PENDLEUSDT', 'WIFUSDT',
}  # top 50

# ---------------------------------------------------------------------------
# Non-crypto TIER1/TIER2 symbol sets (FIX-L, 2026-04-22)
# Before this, market_cap_tier_score returned 0 (neutral) for every non-crypto
# symbol — so AAPL, EURUSD, XAUUSD, ES, SPY never received the +10/+5 tier
# bonus that BTCUSDT/ETHUSDT receive. Untiered non-crypto symbols remain
# neutral (0) — the -5 micro-cap penalty is crypto-specific.
# Symbols stored in normalized form (uppercase, no hyphen/slash/"=X").
# ---------------------------------------------------------------------------
TIER1_EQUITY: set[str] = {
    'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'META', 'NVDA', 'TSLA',
    'BRKB', 'JPM', 'V', 'WMT', 'XOM', 'JNJ', 'UNH', 'LLY', 'AVGO', 'MA',
    'HD', 'PG',
}  # top ~20 S&P 500 by market cap

TIER2_EQUITY: set[str] = {
    'ORCL', 'COST', 'ABBV', 'BAC', 'NFLX', 'ADBE', 'CRM', 'KO', 'PEP',
    'TMO', 'WFC', 'CSCO', 'MCD', 'PFE', 'DIS', 'INTC', 'AMD', 'CVX',
    'QCOM', 'PM', 'VZ', 'IBM', 'BA', 'CAT', 'GE', 'NKE', 'ABT', 'ACN',
}

TIER1_FOREX: set[str] = {
    'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD',
    'EURJPY', 'GBPJPY', 'EURGBP',
}  # G10 majors + top crosses

TIER2_FOREX: set[str] = {
    'EURAUD', 'EURCAD', 'EURCHF', 'EURNZD',
    'GBPAUD', 'GBPCAD', 'GBPCHF', 'GBPNZD',
    'AUDCAD', 'AUDCHF', 'AUDJPY', 'AUDNZD',
    'CADCHF', 'CADJPY', 'CHFJPY',
    'NZDCAD', 'NZDCHF', 'NZDJPY',
}

TIER1_COMMODITY: set[str] = {
    'GC', 'SI', 'CL', 'NG', 'HG',
    'XAUUSD', 'XAGUSD', 'XPTUSD', 'XPDUSD',
    'PL', 'PA',
}  # gold/silver/oil/gas/copper + spot variants

TIER2_COMMODITY: set[str] = {
    'BZ', 'HO', 'RB',
    'ZC', 'ZW', 'ZS', 'ZM', 'ZL',
    'CT', 'KC', 'SB', 'CC', 'OJ',
    'LE', 'HE', 'GF',
}

TIER1_FUTURES: set[str] = {
    'ES', 'NQ', 'YM', 'RTY',
    'ZN', 'ZB',
    '6E', '6J',
    'VX',
}  # major index/rate/FX futures

TIER2_FUTURES: set[str] = {
    'ZF', 'ZT',
    '6B', '6A', '6C', '6S', '6N', '6M',
    'NKD', 'FTSE',
}

TIER1_ETF: set[str] = {
    'SPY', 'QQQ', 'IWM', 'DIA', 'VOO', 'VTI', 'IVV',
    'EEM', 'EFA',
    'GLD', 'SLV', 'TLT', 'HYG', 'LQD',
    'XLF', 'XLE', 'XLK', 'XLV',
}

TIER2_ETF: set[str] = {
    'XLP', 'XLY', 'XLI', 'XLB', 'XLU', 'XLRE', 'XLC',
    'SMH', 'SOXX', 'ARKK', 'ARKG', 'ARKW',
    'KRE', 'XBI', 'IBB',
    'VEA', 'VWO', 'AGG', 'BND', 'BIL',
}


def _normalize_non_crypto_symbol(symbol: str) -> str:
    """Strip hyphens, slashes, and '=X' Yahoo suffix for tier-set lookup.

    Examples: 'BRK-B' -> 'BRKB', 'EUR/USD' -> 'EURUSD', 'EURUSD=X' -> 'EURUSD'.
    """
    s = (symbol or "").upper()
    if s.endswith("=X"):
        s = s[:-2]
    return s.replace("-", "").replace("/", "").replace(".", "")

# ---------------------------------------------------------------------------
# KOL consensus alignment cache.
# Loaded once per scoring batch from predictions/data/kol_consensus_picks.json.
# Provides bonus when non-KOL picks align with KOL consensus direction.
# ---------------------------------------------------------------------------
_KOL_CONSENSUS_CACHE: dict[tuple[str, str], dict] | None = None
_KOL_CACHE_TIME: float = 0


def _check_kol_alignment(symbol: str, direction: str) -> dict | None:
    """Check if a pick's symbol+direction aligns with active KOL consensus.

    Returns {"bonus": int, "strength": str, "count": int} or None.
    Cache refreshes every 5 minutes.
    """
    global _KOL_CONSENSUS_CACHE, _KOL_CACHE_TIME

    now = time.time()
    if _KOL_CONSENSUS_CACHE is None or (now - _KOL_CACHE_TIME) > 300:
        _KOL_CONSENSUS_CACHE = {}
        kol_path = Path(__file__).parent.parent / "predictions" / "data" / "kol_consensus_picks.json"
        if kol_path.exists():
            try:
                with open(kol_path) as f:
                    picks = json.load(f)
                for p in (picks if isinstance(picks, list) else []):
                    sym = (p.get("symbol") or "").upper()
                    d = (p.get("direction") or "").upper()
                    if sym and d:
                        strength = p.get("reason", "")
                        count = p.get("consensus_count", 0) or 0
                        diversity = p.get("kol_category_diversity", 1) or 1
                        bonus = 0
                        if "ULTRA" in strength:
                            bonus = 5
                        elif "STRONG" in strength:
                            bonus = 3
                        elif "MODERATE" in strength:
                            bonus = 1
                        if p.get("consensus_signal_source") == "news_inferred":
                            bonus = max(0, int(round(bonus * 0.25)))
                            if bonus > 1:
                                bonus = 1
                        _KOL_CONSENSUS_CACHE[(sym, d)] = {
                            "bonus": bonus,
                            "strength": strength,
                            "count": count,
                            "diversity": diversity,
                        }
            except (json.JSONDecodeError, OSError):
                pass
        _KOL_CACHE_TIME = now

    key = (symbol.upper(), direction.upper())
    return _KOL_CONSENSUS_CACHE.get(key)


def market_cap_tier_score(symbol: str, category: str = "") -> int:
    """Return score adjustment based on market cap / liquidity tier.

    Crypto:       TIER1 +10, TIER2 +5, others -5 (micro-cap penalty stands).
    Non-crypto:   TIER1 +10, TIER2 +5, others 0 (no micro-cap penalty —
                  the penalty is crypto-altcoin specific; blue-chip ETFs and
                  G10 forex should reward, not punish, unknown picks neutrally).

    FIX-L (2026-04-22): previously returned 0 for every non-crypto symbol so
    AAPL/EURUSD/XAUUSD/ES/SPY never received the blue-chip bonus. Now gated
    per asset class via TIER1_EQUITY / TIER1_FOREX / TIER1_COMMODITY /
    TIER1_FUTURES / TIER1_ETF (and corresponding TIER2_* sets).
    """
    _cat = (category or "").lower()
    _sym_raw = (symbol or "").upper()

    # Forex heuristic: explicit category OR identifying suffix/separator
    is_forex = (
        _cat == "forex"
        or "=X" in _sym_raw
        or ("/" in _sym_raw and len(_sym_raw) <= 8)
    )
    if is_forex:
        norm = _normalize_non_crypto_symbol(_sym_raw)
        if norm in TIER1_FOREX:
            return 10
        if norm in TIER2_FOREX:
            return 5
        return 0

    if _cat in ("equity", "stock"):
        norm = _normalize_non_crypto_symbol(_sym_raw)
        if norm in TIER1_EQUITY:
            return 10
        if norm in TIER2_EQUITY:
            return 5
        return 0

    if _cat == "etf":
        norm = _normalize_non_crypto_symbol(_sym_raw)
        if norm in TIER1_ETF:
            return 10
        if norm in TIER2_ETF:
            return 5
        return 0

    if _cat == "commodity":
        norm = _normalize_non_crypto_symbol(_sym_raw)
        if norm in TIER1_COMMODITY:
            return 10
        if norm in TIER2_COMMODITY:
            return 5
        return 0

    if _cat in ("futures", "bond"):
        norm = _normalize_non_crypto_symbol(_sym_raw)
        if norm in TIER1_FUTURES:
            return 10
        if norm in TIER2_FUTURES:
            return 5
        return 0

    # Crypto (default): -5 micro-cap penalty applies
    if _sym_raw in TIER1_COINS:
        return 10
    if _sym_raw in TIER2_COINS:
        return 5
    return -5


def volatility_predictability_score(
    symbol: str,
    price_change_24h: float,
    category: str = "crypto",
) -> int:
    """Return elite_score adjustment based on 24h volatility (ATR proxy).

    Neural net feature importance + closed picks data confirm ATR% is the
    #1 predictive feature:
      High-vol picks: 53.1% WR, Sharpe +0.218
      Low-vol picks: 29.2% WR, Sharpe -0.346
      Spread: +24pp

    Args:
        symbol: Trading symbol (for logging).
        price_change_24h: Absolute 24h price change percentage.
        category: Asset category ('crypto', 'forex', 'stock', 'equity', 'etf').

    Returns:
        Score adjustment: -10 (dead) to +10 (very volatile).
    """
    change = abs(price_change_24h)

    if category == "forex":
        # Forex thresholds (lower volatility asset class)
        if change > 1.0:
            return 10   # Very volatile forex = very predictable
        if change > 0.5:
            return 7
        if change > 0.3:
            return 3
        if change > 0.1:
            return 0
        return -10      # Dead forex pair
    elif category in ("stock", "equity", "etf"):
        # Equity thresholds
        if change > 3.0:
            return 10
        if change > 2.0:
            return 7
        if change > 1.0:
            return 3
        if change > 0.3:
            return 0
        return -10      # Dead stock
    else:
        # Crypto (default) — needs more volatility to be meaningful
        if change > 5.0:
            return 10   # Very volatile = very predictable
        if change > 3.0:
            return 7
        if change > 1.0:
            return 3
        if change > 0.5:
            return 0
        return -10      # Dead market


# ---------------------------------------------------------------------------
# ML proven strategies — these have empirically verified high win rates but
# the current scorer gives them elite_score=1 (the floor).  Override to
# ensure proven ML strategies get scores commensurate with their track record.
# ---------------------------------------------------------------------------
ML_PROVEN_STRATEGIES: dict[str, float] = {
    'ml_enhanced_BNBUSDT_15m_B_lightgbm': 94.1,
    'ml_enhanced_FETUSDT_1d_B_lightgbm': 93.8,
    'ml_enhanced_RENDERUSDT_1h_D_ensemble_stack': 87.5,
    'ml_enhanced_RENDERUSDT_4h_D_ensemble_stack': 87.5,
    'copy_hl_NMTD_25M': 81.3,
    'quan_engine_swing': 88.0,
    'quan_engine_scalp': 86.0,
}

# ---------------------------------------------------------------------------
# Risk-warning symbol lookup (built once from config.CRYPTO_SYMBOLS)
# Symbols with risk_warning in config get a scoring penalty.
# ---------------------------------------------------------------------------
_RISK_WARNING_SYMBOLS: dict[str, str] = {}
try:
    from config import CRYPTO_SYMBOLS
    for _key, _meta in CRYPTO_SYMBOLS.items():
        _rw = _meta.get("risk_warning", "")
        if _rw:
            _binance = (_meta.get("binance") or "").upper()
            _yf = _key.upper().replace("-USD", "USDT")
            if _binance:
                _RISK_WARNING_SYMBOLS[_binance] = _rw
            _RISK_WARNING_SYMBOLS[_yf] = _rw
except ImportError:
    pass


# ---------------------------------------------------------------------------
# Indicator predictive power cache (loaded once, refreshed every hour)
# ---------------------------------------------------------------------------
_indicator_pp_cache: dict = {}
_indicator_pp_cache_time: float = 0.0


def load_indicator_predictive_power(data_dir: Optional[str | Path] = None) -> dict:
    """
    Load indicator_predictive_power.json with 1-hour in-memory cache.

    Returns the full JSON dict with keys: indicators, recommendations, etc.
    Returns empty dict if file is missing or unreadable.
    """
    global _indicator_pp_cache, _indicator_pp_cache_time

    now = time.time()
    if _indicator_pp_cache and (now - _indicator_pp_cache_time) < 3600:
        return _indicator_pp_cache

    if data_dir is None:
        data_dir = Path(__file__).resolve().parent / "data"
    else:
        data_dir = Path(data_dir)

    try:
        pp_path = data_dir / "indicator_predictive_power.json"
        if pp_path.exists():
            with open(pp_path, encoding="utf-8") as f:
                _indicator_pp_cache = json.load(f)
            _indicator_pp_cache_time = now
        else:
            _indicator_pp_cache = {}
    except Exception as e:
        print(f"  [ELITE] indicator_predictive_power.json load warning: {e}")
        _indicator_pp_cache = {}

    return _indicator_pp_cache


def compute_technical_confirmation_score(pick: dict, pp_data: Optional[dict] = None) -> tuple[int, dict]:
    """
    Compute technical confirmation score from indicator correlation findings.

    Uses indicator_predictive_power.json to:
      1. Apply fixed rules for key indicators (vwap, candles, atr, stoch, rsi2)
      2. Apply dynamic self-tuning rules from recommendations

    Returns (score, breakdown_detail) where:
      - score is clamped to [-5, +9] for fixed rules
      - dynamic mode adds up to +2 per boost, -3 per block (medium/strong only)
      - total clamped to [-5, +9]
    """
    detail: dict = {}
    extra = pick.get("extra", {}) or {}
    # Also check top-level keys (some enrichers write directly to pick)
    direction = str(pick.get("direction", "") or pick.get("signal_type", "") or "").upper()

    fixed_pts = 0

    # --- 1. VWAP deviation: above median = +3 pts ---
    vwap_dev = extra.get("vwap_deviation_pct", pick.get("vwap_deviation_pct"))
    if vwap_dev is not None:
        try:
            vwap_dev = float(vwap_dev)
            median_vwap = -3.9571  # default
            if pp_data and "indicators" in pp_data:
                ind = pp_data["indicators"].get("vwap_deviation_pct", {})
                median_vwap = float(ind.get("median_value", median_vwap))
            if vwap_dev >= median_vwap:
                fixed_pts += 3
                detail["vwap_deviation_boost"] = 3
        except (ValueError, TypeError):
            pass

    # --- 2. Consecutive candles aligned with direction: +2 pts ---
    consec = extra.get("consecutive_candles", pick.get("consecutive_candles"))
    if consec is not None:
        try:
            consec = float(consec)
            aligned = False
            if direction in ("LONG", "BUY") and consec > 0:
                aligned = True
            elif direction in ("SHORT", "SELL") and consec < 0:
                aligned = True
            if aligned:
                fixed_pts += 2
                detail["consecutive_candles_boost"] = 2
        except (ValueError, TypeError):
            pass

    # --- 3. ATR% high = volatile = BONUS (2026-03-24 fix) ---
    # Neural net + closed picks confirm ATR% is #1 predictive feature.
    # High-vol: 53.1% WR, Sharpe +0.218 | Low-vol: 29.2% WR, Sharpe -0.346
    # OLD: penalized high ATR by -5 (WRONG -- was anti-predictive)
    # NEW: reward high ATR by +3, penalize low ATR by -3
    atr_pct = extra.get("atr_pct", pick.get("atr_pct"))
    if atr_pct is not None:
        try:
            atr_pct = float(atr_pct)
            atr_threshold = 0.9428  # median from indicator_predictive_power.json
            if pp_data and "indicators" in pp_data:
                ind = pp_data["indicators"].get("atr_pct", {})
                atr_threshold = float(ind.get("median_value", atr_threshold))
            if atr_pct > atr_threshold:
                fixed_pts += 3
                detail["atr_pct_high_vol_bonus"] = 3
            elif atr_pct < atr_threshold * 0.5:
                fixed_pts -= 3
                detail["atr_pct_low_vol_penalty"] = -3
        except (ValueError, TypeError):
            pass

    # --- 4. Stochastic oversold/overbought confirmation: +2 pts ---
    stoch_k = extra.get("stoch_k", pick.get("stoch_k"))
    stoch_d = extra.get("stoch_d", pick.get("stoch_d"))
    if stoch_k is not None:
        try:
            stoch_k_val = float(stoch_k)
            stoch_confirmed = False
            if direction in ("SHORT", "SELL") and stoch_k_val > 80:
                stoch_confirmed = True  # Overbought confirmation for short
            elif direction in ("LONG", "BUY") and stoch_k_val < 20:
                stoch_confirmed = True  # Oversold confirmation for long
            if stoch_confirmed:
                fixed_pts += 2
                detail["stoch_confirmation_boost"] = 2
        except (ValueError, TypeError):
            pass

    # --- 5. RSI(2) extreme oversold/overbought: +2 pts ---
    rsi_2 = extra.get("rsi_2", pick.get("rsi_2"))
    if rsi_2 is not None:
        try:
            rsi_2_val = float(rsi_2)
            rsi2_confirmed = False
            if direction in ("LONG", "BUY") and rsi_2_val < 10:
                rsi2_confirmed = True  # Extreme oversold for long
            elif direction in ("SHORT", "SELL") and rsi_2_val > 90:
                rsi2_confirmed = True  # Extreme overbought for short
            if rsi2_confirmed:
                fixed_pts += 2
                detail["rsi2_extreme_boost"] = 2
        except (ValueError, TypeError):
            pass

    # Clamp fixed component: max bonus +9, max penalty -5
    fixed_pts = max(-5, min(9, fixed_pts))

    # --- 6. DYNAMIC self-tuning from recommendations ---
    dynamic_pts = 0
    if pp_data and "recommendations" in pp_data:
        for rec in pp_data["recommendations"]:
            confidence = str(rec.get("confidence", "")).lower()
            if confidence not in ("medium", "strong"):
                continue  # Skip low-confidence recommendations

            indicator_name = rec.get("indicator", "")
            action = str(rec.get("action", "")).lower()
            threshold = rec.get("threshold")
            if threshold is None or not indicator_name:
                continue

            # Get indicator value from pick's extra dict or top-level
            ind_val = extra.get(indicator_name, pick.get(indicator_name))
            if ind_val is None:
                continue

            try:
                ind_val = float(ind_val)
                threshold = float(threshold)
            except (ValueError, TypeError):
                continue

            if action == "boost" and ind_val >= threshold:
                dynamic_pts += 2
                detail[f"dynamic_boost_{indicator_name}"] = 2
            elif action == "block" and ind_val >= threshold:
                dynamic_pts -= 3
                detail[f"dynamic_block_{indicator_name}"] = -3

    total = fixed_pts + dynamic_pts
    # Final clamp: keep within [-5, +9] overall
    total = max(-5, min(9, total))
    detail["_fixed_pts"] = fixed_pts
    detail["_dynamic_pts"] = dynamic_pts
    detail["_total"] = total

    return total, detail


def _flatten_extra_json(pick: dict) -> dict:
    """
    Return a merged view of pick + extra_json fields.

    Many closed picks store important fields (kelly_fraction, risk_reward,
    forward_wr, forward_trades, convergence, etc.) inside the extra_json
    dict rather than at the top level.  This helper merges them so scoring
    functions can access all fields uniformly.
    """
    merged = dict(pick)
    ej = pick.get("extra_json")
    if isinstance(ej, str):
        try:
            ej = json.loads(ej)
        except (json.JSONDecodeError, TypeError):
            ej = None
    if isinstance(ej, dict):
        for k, v in ej.items():
            if k not in merged or merged[k] is None:
                merged[k] = v
    # Normalize direction: closed picks use signal_type, active use direction
    if not merged.get("direction") and not merged.get("side"):
        st = merged.get("signal_type", "")
        if st:
            merged["direction"] = st.upper()
    return merged


def compute_ml_replacement_score(pick: dict) -> int:
    """
    Rule-based replacement for the ML score component (0-18 pts).

    Halved from 35 to 18 per Method 4 backtest (2026-03-22):
    ML heuristic was over-weighted vs actual track record data.
    Confidence/Kelly/reputation are useful but should not dominate.

    Calibrated from empirical WR data:
      - Confidence 0.60-0.70: 61% WR (BEST range -- sweet spot)
      - Confidence >= 0.70: overconfident, WR drops
      - Confidence < 0.55: underconfident, low WR
      - Kelly fraction: winners avg 0.367 vs losers 0.086 -- up to 5 pts
      - Strategy reputation (win rate) -- up to 5 pts
    """
    score = 0
    _source = (pick.get("source_system") or "").lower()

    # --- Confidence (source-specific calibration) ---
    # Use coerce_confidence: handles numeric AND tier-string inputs
    # ('HIGH'/'MEDIUM'/'LOW' from ml_crypto_predictor live_picks_tracker).
    conf = coerce_confidence(pick.get("confidence"), default=0.0)
    
    # QUAN_ENGINE CONFIDENCE INVERSION FIX (2026-03-26)
    # Investigation: quan_engine conf 0.50-0.59 has 36.7% WR (BEST)
    #                quan_engine conf 0.60-0.69 has 19.8% WR (WORST)
    # Standard scoring assumes 0.60-0.70 is best — INVERTED for quan_engine
    if _source == "quan_engine":
        if 0.50 <= conf < 0.60:
            score += 8    # BEST band for quan_engine: 36.7% WR
        elif 0.60 <= conf < 0.70:
            score += 2    # WORST band for quan_engine: 19.8% WR
        elif 0.70 <= conf < 0.75:
            score += 5    # Good band: winners cluster at 0.70-0.73
        elif conf >= 0.75:
            score += 3    # Overconfident
        elif conf >= 0.45:
            score += 3    # Below best but acceptable
    else:
        # Standard confidence scoring for other sources
        if 0.60 <= conf < 0.70:
            score += 8    # Sweet spot: 61% WR -- best empirical range
        elif 0.55 <= conf < 0.60:
            score += 5    # Near sweet spot, still decent
        elif conf >= 0.70:
            score += 3    # Overconfident -- WR drops above 0.70
        elif conf >= 0.50:
            score += 2    # Below sweet spot
    # conf < 0.50 => 0 pts (underconfident -- nearly worthless)

    # --- Kelly fraction (winners avg 0.367 vs losers 0.086) ---
    kelly = float(pick.get("kelly_fraction", 0) or 0)
    if kelly >= 0.35:
        score += 5    # Strong Kelly = high edge (halved from 10)
    elif kelly >= 0.20:
        score += 3    # (halved from 6)
    elif kelly >= 0.10:
        score += 2    # (halved from 3)

    # --- Strategy reputation (forward win rate) ---
    strat_wr = float(pick.get("strategy_win_rate", 0) or 0)
    if strat_wr >= 0.65:
        score += 5    # (halved from 10)
    elif strat_wr >= 0.55:
        score += 3    # (halved from 6)
    elif strat_wr >= 0.45:
        score += 2    # (halved from 3)

    return min(score, 18)  # Cap at 18 (halved from 35, Method 4 backtest)


def load_monte_carlo_results(data_dir: Optional[str | Path] = None) -> dict:
    """
    Load Monte Carlo results and build a strategy -> results lookup.

    Returns dict mapping strategy_name -> {verdict, p_value, n_trades, ...}
    """
    if data_dir is None:
        data_dir = Path(__file__).resolve().parent / "data"
    else:
        data_dir = Path(data_dir)

    mc_results = {}
    try:
        mc_path = data_dir / "monte_carlo_results.json"
        if mc_path.exists():
            with open(mc_path) as f:
                mc_data = json.load(f)
            # Primary: strategies dict (keyed by name)
            strategies = mc_data.get("strategies", {})
            for name, info in strategies.items():
                mc_results[name] = info
            # Also check strategy_rankings list (some entries may only be here)
            for r in mc_data.get("strategy_rankings", []):
                name = r.get("strategy", "")
                if name and name not in mc_results:
                    mc_results[name] = r
    except Exception as e:
        print(f"  [ELITE] Monte Carlo load warning: {e}")

    return mc_results


def load_strategy_performance(data_dir: Optional[str | Path] = None) -> dict:
    """Load strategy_performance.json for forward-test stats."""
    if data_dir is None:
        data_dir = Path(__file__).resolve().parent / "data"
    else:
        data_dir = Path(data_dir)

    try:
        perf_path = data_dir / "strategy_performance.json"
        if perf_path.exists():
            with open(perf_path) as f:
                perf = json.load(f)
            if isinstance(perf, dict):
                sample = next((v for v in perf.values() if isinstance(v, dict)), None)
                if sample and "concentration_penalty" not in sample:
                    return _enrich_strategy_performance_concentration(perf)
                return perf
    except Exception:
        pass
    return {}


def rebuild_strategy_performance(closed_picks_path: Optional[str | Path] = None) -> dict:
    """
    Build strategy_performance.json from closed_picks.json.

    Groups closed picks by strategy name, and for each strategy with 3+
    trades computes: closed_picks count, win_rate, avg_pnl, profit_factor.
    Saves the result to strategy_performance.json and returns it.
    """
    if closed_picks_path is None:
        closed_picks_path = Path(__file__).resolve().parent / "data" / "closed_picks.json"
    else:
        closed_picks_path = Path(closed_picks_path)

    perf_path = closed_picks_path.parent / "strategy_performance.json"

    if not closed_picks_path.exists():
        closed_picks = []
    else:
        try:
            with open(closed_picks_path, encoding="utf-8") as f:
                closed_picks = json.load(f)
            if not isinstance(closed_picks, list):
                closed_picks = []
        except Exception:
            closed_picks = []

    # Inject external strategy data (universal resolver, PM, etc.)
    # to ensure they receive elite scorer ratings based on their track records.
    repo_root = closed_picks_path.parent.parent.parent
    external_paths = [
        repo_root / "audit_trail" / "data" / "universal_resolved_picks.json",
        repo_root / "battleground" / "data" / "luxalgo_closed_picks.json",
        repo_root / "ml_crypto_predictor" / "enhanced_models" / "live_picks" / "closed_picks.json",
        repo_root / "rapid_fire_data" / "now_picks.json",
        repo_root / "alpha_engine" / "data" / "closed_picks_fast.json",
        repo_root / "claude_gainer_ml" / "tracker" / "short_term_closed.json"
    ]
    
    for ext_path in external_paths:
        if ext_path.exists():
            try:
                with open(ext_path, encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        closed_picks.extend(data)
            except Exception:
                pass

    # Group PnLs by strategy.
    # NOTE: OUTLIER_SYMBOLS exclusion is intentionally NOT applied here.
    # For aggregate system-level track records, go to production_scanner.py.
    # For per-strategy stats: a dedicated strategy like ml_enhanced_FETUSDT_1d_B_lightgbm
    # trades *only* FETUSDT -- excluding that symbol wipes the entire strategy from the
    # leaderboard, which is worse than including the outlier.
    strategy_pnls: dict[str, list[float]] = {}
    strategy_rows: dict[str, list[dict]] = {}
    strategy_outcomes: dict[str, list[str]] = {}  # ordered WON/LOST list
    for pick in closed_picks:
        strat = pick.get("strategy") or ""
        if not strat:
            continue
        symbol = str(pick.get("symbol", "") or "").upper()
        status = pick.get("status", "")
        try:
            pnl = float(pick.get("pnl_pct", pick.get("final_pnl", pick.get("current_pnl", 0))) or 0)
        except (ValueError, TypeError):
            continue
        strategy_pnls.setdefault(strat, []).append(pnl)
        strategy_rows.setdefault(strat, []).append(pick)
        if status in ("WON", "LOST"):
            strategy_outcomes.setdefault(strat, []).append(status)

    # Compute stats for strategies with 3+ trades
    performance: dict[str, dict] = {}
    for strat, pnls in strategy_pnls.items():
        if len(pnls) < 3:
            continue
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]
        gross_profit = sum(wins) if wins else 0.0
        gross_loss = abs(sum(losses)) if losses else 0.0
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (10.0 if gross_profit > 0 else 0.0)
        # Compute win/loss streak from ordered outcomes
        outcomes = strategy_outcomes.get(strat, [])
        last_outcome = outcomes[-1] if outcomes else ""
        win_streak = 0
        for o in reversed(outcomes):
            if o == "WON":
                win_streak += 1
            else:
                break

        distinct_symbols = len({
            str((row or {}).get("symbol", "") or "").upper()
            for row in strategy_rows.get(strat, [])
            if str((row or {}).get("symbol", "") or "").strip()
        })

        clean_metrics = {}
        try:
            try:
                from alpha_engine.stats_cleaner import compute_clean_metrics as _compute_clean_metrics
            except ImportError:
                from stats_cleaner import compute_clean_metrics as _compute_clean_metrics
            clean_metrics = _compute_clean_metrics(strategy_rows.get(strat, []), cap_pct=10.0) or {}
        except Exception:
            clean_metrics = {}

        symbol_pnls: dict[str, float] = {}
        for row in strategy_rows.get(strat, []):
            sym = str((row or {}).get("symbol", "") or "").upper()
            if not sym:
                continue
            try:
                row_pnl = float((row or {}).get("pnl_pct", (row or {}).get("final_pnl", (row or {}).get("current_pnl", 0))) or 0)
            except (ValueError, TypeError):
                continue
            symbol_pnls[sym] = symbol_pnls.get(sym, 0.0) + row_pnl
        total_pnl = sum(pnls)
        concentration = _compute_concentration_metrics(symbol_pnls, total_pnl, len(pnls))

        performance[strat] = {
            "closed_picks": len(pnls),
            "win_rate": round(len(wins) / len(pnls), 4),
            "avg_pnl": round(sum(pnls) / len(pnls), 4),
            "profit_factor": round(profit_factor, 4),
            "total_pnl": round(total_pnl, 4),
            "last_outcome": last_outcome,
            "win_streak": win_streak,
            "distinct_symbols": distinct_symbols,
            "top_symbol": concentration.get("top_symbol") or clean_metrics.get("top_symbol", ""),
            "top_symbol_pnl_pct": round(float(concentration.get("top_symbol_pnl_pct", clean_metrics.get("top_symbol_pnl_pct", 0)) or 0), 1),
            "pnl_ex_top_symbol": round(float(concentration.get("pnl_ex_top_symbol", total_pnl) or 0), 4),
            "concentration_penalty": round(float(concentration.get("concentration_penalty", 0) or 0), 1),
            "concentration_level": concentration.get("concentration_level", "NONE"),
            "concentration_warning": concentration.get("concentration_warning") or clean_metrics.get("concentration_warning"),
        }

    # Save — atomic + merge-with-existing to preserve historical entries.
    # Per updates/2026-04-17-alpha-engine-data-loss-bug.md: previous behavior
    # ("rebuild from scratch with 3+trade filter") dropped 111 of 161 strategies
    # per cycle (354k-line git churn, lost trend tracking on 1-2-trade variants).
    # Now: read existing -> merge current pass on top -> atomic write.
    # Stamping last_seen on every entry enables 30-day prune in a follow-up step.
    try:
        from alpha_engine.atomic_json import merge_write_json
        merge_write_json(perf_path, performance, indent=2)
    except ImportError:
        # Defensive fallback if atomic_json isn't on path
        try:
            with open(perf_path, "w", encoding="utf-8") as f:
                json.dump(performance, f, indent=2)
        except Exception as e:
            print(f"  [ELITE] Failed to save strategy_performance.json: {e}")
    except Exception as e:
        print(f"  [ELITE] Failed to save strategy_performance.json: {e}")

    return performance


def _normalize_copytrader_key(value: object) -> str:
    """Normalize copy trader strategy and trader labels for stable lookups."""
    return " ".join(str(value or "").strip().lower().split())


def _extract_copytrader_label(strategy_name: str) -> str:
    strategy_name = str(strategy_name or "")
    lower = strategy_name.lower()
    for prefix in ("clone_hl_copy_", "copy_hl_", "hs_"):
        if lower.startswith(prefix):
            return strategy_name[len(prefix):]
    return strategy_name


def _summarize_pnls(pnls: list[float]) -> dict:
    wins = sum(1 for pnl in pnls if pnl > 0)
    return {
        "trades": len(pnls),
        "wins": wins,
        "losses": len(pnls) - wins,
        "win_rate": wins / len(pnls) if pnls else 0.0,
        "avg_pnl": sum(pnls) / len(pnls) if pnls else 0.0,
    }


def _compute_concentration_metrics(
    symbol_pnls: dict[str, float],
    total_pnl: float,
    trade_count: int,
) -> dict:
    """Summarize single-symbol dependence for a strategy track record."""
    if not symbol_pnls or trade_count < 5 or total_pnl == 0:
        return {
            "top_symbol": None,
            "top_symbol_pnl_pct": 0.0,
            "pnl_ex_top_symbol": round(total_pnl, 4),
            "concentration_penalty": 0.0,
            "concentration_level": "NONE",
            "concentration_warning": None,
        }

    top_symbol, top_symbol_pnl = max(symbol_pnls.items(), key=lambda kv: abs(kv[1]))
    top_symbol_pnl_pct = round(abs(top_symbol_pnl) / abs(total_pnl) * 100, 1)
    pnl_ex_top_symbol = total_pnl - top_symbol_pnl

    penalty = 0.0
    level = "NONE"
    if top_symbol_pnl_pct >= 100:
        penalty = 12.0
        level = "HIGH"
    elif top_symbol_pnl_pct >= 75:
        penalty = 9.0
        level = "HIGH"
    elif top_symbol_pnl_pct >= 50:
        penalty = 6.0
        level = "HIGH"
    elif top_symbol_pnl_pct >= 35:
        penalty = 3.0
        level = "MODERATE"
    elif top_symbol_pnl_pct >= 25:
        penalty = 1.5
        level = "MODERATE"

    if penalty > 0 and pnl_ex_top_symbol <= 0:
        penalty = min(15.0, penalty + (3.0 if top_symbol_pnl_pct >= 50 else 1.5))

    warning = None
    if top_symbol_pnl_pct >= 25:
        warning = (
            f"WARNING: {top_symbol_pnl_pct}% of total PnL comes from {top_symbol}. "
            f"Removing {top_symbol} changes strategy PnL from "
            f"{total_pnl:+.1f}% to {pnl_ex_top_symbol:+.1f}%."
        )

    return {
        "top_symbol": top_symbol,
        "top_symbol_pnl_pct": top_symbol_pnl_pct,
        "pnl_ex_top_symbol": round(pnl_ex_top_symbol, 4),
        "concentration_penalty": round(penalty, 1),
        "concentration_level": level,
        "concentration_warning": warning,
    }


def _enrich_strategy_performance_concentration(perf: dict) -> dict:
    """Backfill concentration fields for older strategy_performance formats."""
    enriched: dict = {}
    for strat, stats in (perf or {}).items():
        if not isinstance(stats, dict):
            enriched[strat] = stats
            continue

        row = dict(stats)
        by_symbol = row.get("by_symbol") or {}
        symbol_pnls: dict[str, float] = {}
        if isinstance(by_symbol, dict):
            for sym, meta in by_symbol.items():
                if not sym:
                    continue
                total_pnl = 0.0
                if isinstance(meta, dict):
                    try:
                        total_pnl = float(meta.get("total_pnl", 0) or 0)
                    except (ValueError, TypeError):
                        total_pnl = 0.0
                symbol_pnls[str(sym).upper()] = total_pnl

        if "distinct_symbols" not in row:
            row["distinct_symbols"] = len(symbol_pnls) if symbol_pnls else int(row.get("distinct_symbols", 0) or 0)

        try:
            total_pnl = float(
                row.get("total_pnl")
                or row.get("total_pnl_pct")
                or (float(row.get("avg_pnl", row.get("avg_pnl_pct", 0)) or 0) * float(row.get("closed_picks", 0) or 0))
            )
        except (ValueError, TypeError):
            total_pnl = 0.0

        concentration = _compute_concentration_metrics(
            symbol_pnls,
            total_pnl,
            int(row.get("closed_picks", 0) or 0),
        )
        for key, value in concentration.items():
            row.setdefault(key, value)

        enriched[strat] = row

    return enriched


def _get_strategy_concentration_profile(
    strategy_name: str,
    strategy_perf: Optional[dict],
) -> dict:
    """Return concentration metadata + score penalty for a strategy."""
    profile = {
        "strategy_top_symbol": "",
        "strategy_top_symbol_pnl_pct": 0.0,
        "strategy_distinct_symbols": 0,
        "strategy_concentration_warning": "",
        "strategy_concentration_risk": "NONE",
        "strategy_concentration_penalty": 0,
        "strategy_concentration_multiplier": 1.0,
    }
    if not strategy_perf or not strategy_name:
        return profile

    stats = strategy_perf.get(strategy_name) or {}
    closed_picks = int(stats.get("closed_picks", 0) or 0)
    top_symbol_pnl_pct = float(stats.get("top_symbol_pnl_pct", 0) or 0)
    distinct_symbols = int(stats.get("distinct_symbols", 0) or 0)
    stored_penalty = int(round(float(stats.get("concentration_penalty", 0) or 0)))
    stored_level = str(stats.get("concentration_level", "NONE") or "NONE").upper()

    profile.update({
        "strategy_top_symbol": str(stats.get("top_symbol") or ""),
        "strategy_top_symbol_pnl_pct": round(top_symbol_pnl_pct, 1),
        "strategy_distinct_symbols": distinct_symbols,
        "strategy_concentration_warning": str(stats.get("concentration_warning") or ""),
    })

    if closed_picks < 5 or top_symbol_pnl_pct <= 0:
        return profile

    if stored_penalty > 0:
        profile["strategy_concentration_risk"] = stored_level if stored_level in {"MODERATE", "HIGH"} else "MODERATE"
        profile["strategy_concentration_penalty"] = -stored_penalty
        if stored_penalty >= 12:
            multiplier = 0.25
        elif stored_penalty >= 9:
            multiplier = 0.40
        elif stored_penalty >= 6:
            multiplier = 0.55
        elif stored_penalty >= 3:
            multiplier = 0.70
        else:
            multiplier = 0.85
        profile["strategy_concentration_multiplier"] = multiplier
        return profile

    if top_symbol_pnl_pct >= 150:
        risk = "HIGH"
        penalty = -12
        multiplier = 0.25
    elif top_symbol_pnl_pct >= 100:
        risk = "HIGH"
        penalty = -10
        multiplier = 0.40
    elif top_symbol_pnl_pct >= 75:
        risk = "HIGH"
        penalty = -8
        multiplier = 0.55
    elif top_symbol_pnl_pct >= 50:
        risk = "MODERATE"
        penalty = -5
        multiplier = 0.70
    elif top_symbol_pnl_pct >= 30:
        risk = "MODERATE"
        penalty = -2
        multiplier = 0.85
    else:
        risk = "NONE"
        penalty = 0
        multiplier = 1.0

    profile["strategy_concentration_risk"] = risk
    profile["strategy_concentration_penalty"] = penalty
    profile["strategy_concentration_multiplier"] = multiplier
    return profile


def load_copy_trader_scorebook(root_dir: Optional[str | Path] = None) -> dict:
    """Load tracked copy trader outcomes to calibrate clones/highscores/consensus."""
    if root_dir is None:
        root_dir = Path(__file__).resolve().parent.parent
    else:
        root_dir = Path(root_dir)

    ct_dir = root_dir / "copy_trader_intel" / "data"
    scorebook = {
        "by_strategy": {},
        "by_trader": {},
        "by_type": {},
        "variation": {},
    }

    try:
        history_path = ct_dir / "highscore_pick_history.json"
        if history_path.exists():
            with open(history_path, encoding="utf-8") as f:
                history_rows = json.load(f)

            strategy_pnls: dict[str, list[float]] = {}
            trader_pnls: dict[str, list[float]] = {}
            type_pnls: dict[str, list[float]] = {}

            for row in history_rows:
                # Skip outlier symbols for honest metrics
                if str(row.get("symbol", "") or "").upper() in OUTLIER_SYMBOLS:
                    continue
                try:
                    pnl = float(row.get("final_pnl", row.get("current_pnl", 0)) or 0)
                except (ValueError, TypeError):
                    continue

                strategy_key = _normalize_copytrader_key(row.get("strategy"))
                trader_key = _normalize_copytrader_key(
                    row.get("trader_label")
                    or _extract_copytrader_label(str(row.get("strategy", "")))
                )
                type_key = _normalize_copytrader_key(row.get("type_label"))

                if strategy_key:
                    strategy_pnls.setdefault(strategy_key, []).append(pnl)
                if trader_key:
                    trader_pnls.setdefault(trader_key, []).append(pnl)
                if type_key:
                    type_pnls.setdefault(type_key, []).append(pnl)

            scorebook["by_strategy"] = {
                key: _summarize_pnls(pnls) for key, pnls in strategy_pnls.items() if pnls
            }
            scorebook["by_trader"] = {
                key: _summarize_pnls(pnls) for key, pnls in trader_pnls.items() if pnls
            }
            scorebook["by_type"] = {
                key: _summarize_pnls(pnls) for key, pnls in type_pnls.items() if pnls
            }
    except Exception as e:
        print(f"  [ELITE] Copy trader history load warning: {e}")

    try:
        variation_path = ct_dir / "variation_forward_test.json"
        if variation_path.exists():
            with open(variation_path, encoding="utf-8") as f:
                variation_data = json.load(f)

            for var_id, state in variation_data.get("variations", {}).items():
                stats = state.get("stats", {})
                trades = int(stats.get("trades", 0) or 0)
                if trades <= 0:
                    continue
                scorebook["variation"][_normalize_copytrader_key(var_id)] = {
                    "trades": trades,
                    "win_rate": float(stats.get("wr", 0) or 0),
                    "avg_pnl": float(stats.get("avg_pnl_pct", 0) or 0),
                    "pnl_pct": float(stats.get("pnl_pct", 0) or 0),
                    "status": state.get("status", "ACTIVE"),
                }
    except Exception as e:
        print(f"  [ELITE] Variation score load warning: {e}")

    return scorebook


def _lookup_copy_trader_history(pick: dict, scorebook: dict) -> tuple[Optional[dict], Optional[str]]:
    """Prefer exact strategy history, then trader, then family history."""
    if not scorebook:
        return None, None

    strategy_name = str(pick.get("strategy", "") or "")
    source_sys = str(pick.get("source_system", "") or "").lower()
    strategy_key = _normalize_copytrader_key(strategy_name)
    trader_key = _normalize_copytrader_key(
        pick.get("trader_label")
        or _extract_copytrader_label(strategy_name)
    )

    type_label = _normalize_copytrader_key(pick.get("type_label"))
    if not type_label:
        if "copy_trader_clones" in source_sys or strategy_name.lower().startswith("clone_"):
            type_label = "our clone"
        else:
            type_label = "their pick"

    if strategy_key and strategy_key in scorebook["by_strategy"]:
        return scorebook["by_strategy"][strategy_key], "strategy"
    if trader_key and trader_key in scorebook["by_trader"]:
        return scorebook["by_trader"][trader_key], "trader"
    if type_label and type_label in scorebook["by_type"]:
        return scorebook["by_type"][type_label], "type"
    return None, None


def _copy_trader_history_bonus(stats: Optional[dict]) -> float:
    """Translate tracked copy trader performance into a bounded score bonus."""
    if not stats:
        return 0.0

    trades = int(stats.get("trades", 0) or 0)
    win_rate = float(stats.get("win_rate", 0) or 0)
    avg_pnl = float(stats.get("avg_pnl", 0) or 0)

    bonus = 0.0
    if trades >= 20:
        if win_rate >= 0.62 and avg_pnl > 0:
            bonus += 8
        elif win_rate >= 0.55 and avg_pnl > 0:
            bonus += 6
        elif win_rate >= 0.50 and avg_pnl > 0:
            bonus += 4
        elif win_rate < 0.35:
            bonus -= 5
    elif trades >= 5:
        if win_rate >= 0.65 and avg_pnl >= 0:
            bonus += 6
        elif win_rate >= 0.55 and avg_pnl > 0:
            bonus += 4
        elif win_rate >= 0.50 and avg_pnl > 0:
            bonus += 2
        elif win_rate < 0.30:
            bonus -= 4
    elif trades >= 3:
        if win_rate >= 0.67 and avg_pnl >= 0:
            bonus += 3
        elif win_rate < 0.25:
            bonus -= 3

    if avg_pnl >= 2:
        bonus += 2
    elif avg_pnl >= 1:
        bonus += 1
    elif avg_pnl <= -1:
        bonus -= 2

    return max(-6.0, min(10.0, bonus))


# ---------------------------------------------------------------------------
# SECTOR ROTATION OVERLAY (2026-04-05) — VIX-dependent sector allocation
# Session 3 sector analysis found:
#   - ENERGY 70-82% WR (XOM 75%, CVX 82%, SLB 78%) → EXPAND in low VIX
#   - FINANCE 50-65% WR → maintain 15%
#   - HEALTHCARE 55-65% WR → defensive core
#   - TECH 40-50% WR → KILL weak (INTC/AMD/CRM), keep mega-caps only
#   - UTILITIES 45-55% WR → add for downside protection in high VIX
#   - CONSUMER STAPLES 50-60% WR → defensive
# Target: 58-63% WR vs current 45-50%
# ---------------------------------------------------------------------------

SECTOR_ALLOCATION: dict[str, dict] = {
    "ENERGY": {
        "symbols": ["XOM", "CVX", "SLB", "COP", "EOG", "MPC", "PSX", "VLO", "OXY"],
        "default_alloc": 15,
        "low_vix_alloc": 25,   # VIX < 15: expand to 25%
        "high_vix_alloc": 10,  # VIX > 25: reduce
        "win_rate_range": (70, 82),
    },
    "FINANCE": {
        "symbols": ["MS", "GS", "JPM", "BAC", "C", "WFC", "BLK", "AXP", "SCHW"],
        "default_alloc": 15,
        "low_vix_alloc": 15,
        "high_vix_alloc": 15,
        "win_rate_range": (50, 65),
    },
    "HEALTHCARE": {
        "symbols": ["LLY", "JNJ", "UNH", "PFE", "ABBV", "MRK", "TMO", "ABT", "DHR"],
        "default_alloc": 15,
        "low_vix_alloc": 15,
        "high_vix_alloc": 20,  # High VIX: defensive boost
        "win_rate_range": (55, 65),
    },
    "TECH": {
        "symbols": ["NVDA", "MSFT", "AAPL", "META", "GOOGL", "AMZN", "TSLA", "AVGO", "ORCL"],
        "default_alloc": 10,
        "low_vix_alloc": 15,
        "high_vix_alloc": 5,   # High VIX: reduce tech exposure
        "win_rate_range": (40, 50),
        "exclude": ["INTC", "AMD", "CRM", "CSCO", "IBM", "QCOM", "TXN"],  # Kill weak
    },
    "UTILITIES": {
        "symbols": ["NEE", "DUK", "SO", "D", "AEP", "SRE", "EXC", "XEL", "ED"],
        "default_alloc": 10,
        "low_vix_alloc": 5,
        "high_vix_alloc": 15,  # High VIX: add protection
        "win_rate_range": (45, 55),
    },
    "CONSUMER_STAPLES": {
        "symbols": ["PG", "KO", "PEP", "WMT", "COST", "MDLZ", "CL", "KMB", "GIS"],
        "default_alloc": 10,
        "low_vix_alloc": 10,
        "high_vix_alloc": 15,  # High VIX: defensive
        "win_rate_range": (50, 60),
    },
}


def get_sector_allocation(vix_level: float = 20.0) -> dict[str, int]:
    """Get sector allocation percentages based on VIX level.
    
    Args:
        vix_level: Current VIX level (default 20.0 = neutral)
        
    Returns:
        dict mapping sector_name -> allocation percentage
    """
    if vix_level < 15:
        # Low VIX: risk-on → expand ENERGY, TECH
        return {
            "ENERGY": 25,
            "FINANCE": 15,
            "HEALTHCARE": 15,
            "TECH": 15,
            "UTILITIES": 5,
            "CONSUMER_STAPLES": 10,
            "OTHER": 15,
        }
    elif vix_level > 25:
        # High VIX: risk-off → defensive sectors, reduce TECH
        return {
            "ENERGY": 10,
            "FINANCE": 15,
            "HEALTHCARE": 20,
            "TECH": 5,
            "UTILITIES": 15,
            "CONSUMER_STAPLES": 15,
            "OTHER": 20,
        }
    else:
        # Neutral VIX: default allocation
        return {
            "ENERGY": 15,
            "FINANCE": 15,
            "HEALTHCARE": 15,
            "TECH": 10,
            "UTILITIES": 10,
            "CONSUMER_STAPLES": 10,
            "OTHER": 25,
        }


# Pre-computed symbol -> sector lookup for efficiency
SYMBOL_TO_SECTOR: dict[str, str] = {}
for sec_name, sec_data in SECTOR_ALLOCATION.items():
    for sym in sec_data.get("symbols", []):
        SYMBOL_TO_SECTOR[sym] = sec_name


def compute_sector_rotation_bonus(pick: dict, vix_level: float = 20.0) -> int:
    """
    Compute sector rotation bonus for equity/stock picks based on VIX level.
    
    Logic:
    - If pick's sector is OVERWEIGHTED for current VIX: +5 bonus
    - If pick's sector is UNDERWEIGHTED for current VIX: -3 penalty
    - If pick is in TECH exclude list (INTC/AMD/CRM): -8 penalty
    - If pick is in ENERGY and VIX < 15: +5 bonus (low VIX edge)
    
    Returns:
        int: sector rotation adjustment (-8 to +5)
    """
    symbol = (pick.get("symbol", "") or "").upper().replace("-USD", "").replace("USDT", "")
    sector = pick.get("sector", pick.get("asset_class", ""))
    
    # Default: check symbol against known sector lists (using pre-computed lookup)
    if not sector:
        sector = SYMBOL_TO_SECTOR.get(symbol, "")
    
    if not sector:
        return 0  # Unknown sector, no adjustment
    
    # TECH exclude list penalty (Kill weak TECH: INTC, AMD, CRM, etc.)
    if sector == "TECH":
        excluded = SECTOR_ALLOCATION["TECH"].get("exclude", [])
        if symbol in excluded:
            return -8  # Kill weak TECH
    
    # ENERGY low VIX bonus (70-82% WR edge)
    if sector == "ENERGY" and vix_level < 15:
        return +5  # Low VIX = expand ENERGY
    
    # High VIX defensive sectors
    if vix_level > 25:
        if sector in ("HEALTHCARE", "UTILITIES", "CONSUMER_STAPLES"):
            return +3  # Defensive sectors in high VIX
        if sector == "TECH":
            return -3  # Reduce tech in high VIX
    
    # Low VIX aggressive sectors
    if vix_level < 15:
        if sector in ("ENERGY", "TECH"):
            return +3  # Expand risk-on sectors
    
    return 0  # Neutral allocation for current VIX


# ---------------------------------------------------------------------------
# METHOD C SCORING — ML-first scoring with forward_wr dominant (DEPLOYED v4)
# A/B/C test (scoring_ab_test.py) proved Method C gives 48% top-bottom
# separation vs Method A's 26% — a +22pp improvement in discrimination.
# PROVEN weights (restored v4): forward_wr 40%, ml_score 25%, confidence 15%, regime 10%, tech 10%
# v3 incorrectly demoted forward_wr to 10% — broke the discrimination that made Method C work.
# ---------------------------------------------------------------------------
METHOD_C_ENABLED = True  # Toggle to switch between A-only and A+C dual scoring


def _get_strategy_forward_wr(pick: dict, strategy_perf: Optional[dict] = None) -> float:
    """Get forward-validated win rate for a pick's strategy (0.0 - 1.0)."""
    strategy_name = pick.get("strategy", "")
    fw_wr = float(pick.get("forward_wr", 0) or 0)
    fw_trades = int(pick.get("forward_trades", 0) or 0)

    # Normalize: forward_wr may be stored as percentage (22.2) or decimal (0.222)
    if fw_wr > 1.0:
        fw_wr = fw_wr / 100.0

    # Check strategy_performance.json for real data
    if strategy_perf and strategy_name in strategy_perf:
        sp = strategy_perf[strategy_name]
        sp_trades = sp.get("closed_picks", 0)
        sp_wr = sp.get("win_rate", 0)
        # Prefer strategy_performance data when it has more trades
        if sp_trades >= fw_trades and sp_trades >= 1:
            fw_wr = sp_wr
            fw_trades = sp_trades

    # Require minimum trades for reliability
    if fw_trades < 3:
        return 0.5  # neutral default for unproven strategies
    return max(0.0, min(1.0, fw_wr))


def _get_strategy_forward_pnl(pick: dict, strategy_perf: Optional[dict] = None) -> float:
    """Get forward-validated avg PnL for a pick's strategy.
    
    Top crypto factor (rank 4):
    - Edge Score: +20.17
    - Winner Avg: 26.73
    - Loser Avg: 6.56
    - Coverage: 88%
    
    Returns avg PnL per trade (e.g., 0.05 = 5% avg profit per trade).
    """
    strategy_name = pick.get("strategy", "")
    fw_pnl = float(pick.get("forward_pnl", 0) or 0)
    fw_trades = int(pick.get("forward_trades", 0) or 0)
    
    # Normalize: forward_pnl may be stored as percentage (26.73) or decimal (0.2673)
    if fw_pnl > 1.0:
        fw_pnl = fw_pnl / 100.0
    
    # Check strategy_performance.json for real data
    if strategy_perf and strategy_name in strategy_perf:
        sp = strategy_perf[strategy_name]
        sp_trades = sp.get("closed_picks", 0)
        sp_pnl = sp.get("avg_pnl", 0) or 0
        # Prefer strategy_performance data when it has more trades
        if sp_trades >= fw_trades and sp_trades >= 3:
            fw_pnl = sp_pnl
            fw_trades = sp_trades
    
    # Require minimum trades for reliability
    if fw_trades < 3:
        return 0.0  # neutral default for unproven strategies
    return fw_pnl


def _check_regime_alignment(pick: dict) -> bool:
    """Check if pick direction aligns with current market regime."""
    direction = str(pick.get("direction", "") or pick.get("signal_type", "") or "").upper()
    regime = (pick.get("regime_at_entry") or pick.get("regime_trend_direction") or
              pick.get("regime_at_signal") or pick.get("btc_regime") or
              pick.get("hmm_regime") or pick.get("market_regime") or "").lower().strip()

    # Map non-standard regime values
    regime_map = {"momentum": "trending", "accumulation": "bullish", "distribution": "bearish",
                  "recovery": "bullish", "correction": "bearish", "breakout": "trending",
                  "consolidation": "ranging", "range": "ranging", "mean_reverting": "ranging"}
    regime = regime_map.get(regime, regime)

    if not regime:
        return False  # No regime data = not aligned

    if direction in ("LONG", "BUY"):
        return regime in ("bull", "trending", "bullish", "uptrend", "ranging", "sideways")
    elif direction in ("SHORT", "SELL"):
        return regime in ("bear", "bearish", "downtrend", "crash", "crisis", "ranging", "sideways")
    return False


def compute_method_c_score(pick: dict, strategy_perf: Optional[dict] = None) -> dict:
    """
    Method C — ML-first scoring with forward_wr dominant (PROVEN weights).

    A/B/C test results (502 closed picks):
      Method A: 54% top-20% WR, 26% separation
      Method C: 67% top-20% WR, 48% separation (+22pp improvement)

    DEEP_ANALYSIS_2026-03-24 proved these EXACT weights give 48% separation:
      forward_wr:          40% (0-40 pts) — DOMINANT: strategy track record is king
      ml_score:            25% (0-25 pts) — ML model prediction
      confidence:          15% (0-15 pts) — source confidence
      regime_match:        10% (0-10 pts) — market regime alignment
      technical_alignment: 10% (0-10 pts) — HTF bias confirmation

    HISTORY:
      v1 (2026-03-24): Original proven weights — 48% separation. Never deployed.
      v3 (2026-03-26): Recalibrated to confidence=35%, fwr=10%. BROKE separation.
        Rationale was "88% of picks have fwr=0" but that IS the feature —
        Strategy=0 gap means 94% of picks lack strategy data, so forward_wr
        correctly penalizes them. The 48% separation CAME FROM this penalty.
      v4 (2026-03-28): RESTORED original proven weights. forward_wr=40%.

    Returns dict with ml_composite_score (0-100) and ml_composite_breakdown.
    """
    pick = _flatten_extra_json(pick)
    breakdown = {}

    # ── 1. Forward WR (40% weight, 0-40 points) — DOMINANT FACTOR ──
    #   This is what makes Method C work. 94% of picks have no strategy data
    #   (forward_wr=0), so they score 0/40 here. The few picks WITH proven
    #   strategy track records get massive uplift, which is exactly the
    #   discrimination that gave 48% separation in the A/B/C test.
    fwr = _get_strategy_forward_wr(pick, strategy_perf)
    fwr_pts_raw = min(40, int(fwr * 40))  # 100% WR = 40 points
    concentration_profile = _get_strategy_concentration_profile(
        str(pick.get("strategy", "") or ""),
        strategy_perf,
    )
    fwr_pts = round(
        fwr_pts_raw * float(concentration_profile.get("strategy_concentration_multiplier", 1.0) or 1.0),
        1,
    )
    breakdown["forward_wr"] = fwr_pts
    breakdown["_forward_wr_raw"] = round(fwr, 4)
    breakdown["_forward_wr_pre_concentration"] = fwr_pts_raw

    # ── 1b. Forward PnL (NEW 2026-04-05) — TOP CRYPTO FACTOR RANK 4
    #   Edge Score: +20.17 | Winner Avg: 26.73 | Loser Avg: 6.56 | Coverage: 88%
    #   Added to close the gap: forward_pnl was tracked but not in primary scoring
    #   Weight: 10% (0-10 pts) — secondary to forward_wr which has stronger separation
    fw_pnl = _get_strategy_forward_pnl(pick, strategy_perf)
    # Scale: avg_pnl >= 5% = 10 pts, >= 2% = 6 pts, >= 0% = 3 pts, < 0% = 0 pts
    if fw_pnl >= 0.05:
        fw_pnl_pts = 10
    elif fw_pnl >= 0.02:
        fw_pnl_pts = 6
    elif fw_pnl >= 0:
        fw_pnl_pts = 3
    else:
        fw_pnl_pts = 0  # Negative expectancy = no points
    breakdown["forward_pnl"] = fw_pnl_pts
    breakdown["_forward_pnl_raw"] = round(fw_pnl * 100, 2)  # Store as percentage

    # ── 2. ML score (25% weight, 0-25 points) ──
    ml = float(pick.get("ml_score") or pick.get("confidence") or 0.5)
    ml = max(0.0, min(1.0, ml))
    ml_pts = min(25, int(ml * 25))
    breakdown["ml_score"] = ml_pts

    # ── 3. Confidence (15% weight, 0-15 points) ──
    conf = coerce_confidence(pick.get("confidence"), default=0.5)
    # If coercion fell back to default-on-missing (None/empty), use 0.5 as
    # documented neutral prior. Numeric and tier inputs handled by coerce.
    if conf == 0.0 and pick.get("confidence") in (None, "", 0, 0.0):
        conf = 0.5
    conf = max(0.0, min(1.0, conf))
    if 0.80 <= conf <= 0.89:
        conf_pts = 15  # Sweet spot
    elif 0.70 <= conf < 0.80:
        conf_pts = 12
    elif 0.60 <= conf < 0.70:
        conf_pts = 9
    elif conf >= 0.90:
        conf_pts = 8   # Overfit penalty (0.90+ historically 36.1% WR)
    else:
        conf_pts = min(6, int(conf * 10))
    breakdown["confidence"] = conf_pts

    # ── 4. Regime match (10% weight, 0-10 points) ──
    regime_aligned = _check_regime_alignment(pick)
    regime_pts = 10 if regime_aligned else 0
    breakdown["regime_match"] = regime_pts

    # ── 5. Technical alignment (10% weight, 0-10 points) ──
    tech_pts = 0
    direction = str(pick.get("direction", "") or pick.get("signal_type", "") or "").upper()
    # Check HTF bias from extra dict
    htf_bias = (pick.get("extra", {}) or {}).get("htf_bias", "")
    tech_alignment = pick.get("technical_alignment")

    if tech_alignment is True:
        tech_pts = 10  # Full alignment confirmed
    elif tech_alignment is False:
        tech_pts = 0   # Misaligned = no points
    elif htf_bias:
        htf_bias = str(htf_bias).lower()
        if direction in ("LONG", "BUY") and htf_bias in ("bullish", "long", "buy"):
            tech_pts = 10
        elif direction in ("SHORT", "SELL") and htf_bias in ("bearish", "short", "sell"):
            tech_pts = 10
        elif htf_bias == "neutral":
            tech_pts = 5
    else:
        tech_pts = 3  # No tech data = slight benefit of doubt

    breakdown["technical_alignment"] = tech_pts

    # ── 1c. Sector Rotation Bonus (NEW 2026-04-05) — VIX-dependent allocation
    #   Session 3 sector analysis: ENERGY 70-82% WR (expand at low VIX)
    #   TECH exclude: INTC/AMD/CRM get -8 penalty (40-50% WR underperformers)
    #   High VIX: defensive sectors get +3 (HEALTHCARE, UTILITIES, CONSUMER STAPLES)
    #   Only applies to equity/stock picks
    _asset_class = (pick.get("asset_class") or pick.get("category") or "").lower()
    sector_bonus = 0
    if _asset_class in ("stock", "equity", "etf") or pick.get("sector"):
        # Default VIX: 20.0 (neutral) - could be passed as parameter
        vix_level = pick.get("vix_level", 20.0)
        sector_bonus = compute_sector_rotation_bonus(pick, vix_level)
    breakdown["sector_rotation"] = sector_bonus

    # ── Total (0-100) ──
    # Updated 2026-04-05: Added forward_pnl (10 pts weight) + sector_rotation
    total = fwr_pts + fw_pnl_pts + ml_pts + conf_pts + regime_pts + tech_pts + sector_bonus
    # Inject source-level concentration guards and symbol overrides.
    # quan_engine has proven edge, but current live evidence is concentrated in
    # TAO / HYPE / TRX. Do not let that source-level reputation lift unrelated
    # symbols into Smart Picks.
    _source = (pick.get("source_system") or "").lower().strip()
    proven_sym = str(pick.get("symbol", "")).upper()
    source_core_symbols = SOURCE_CORE_SYMBOLS.get(_source)
    if source_core_symbols and proven_sym not in source_core_symbols:
        total -= 18
        breakdown["source_concentration_penalty"] = -18
        breakdown["_source_concentration_reason"] = (
            f"{_source} edge is concentrated in {sorted(source_core_symbols)}"
        )

    if proven_sym == "TAOUSDT":
        total += 15
        breakdown["proven_symbol_TAO"] = 15
    elif proven_sym == "HYPEUSDT":
        total += 15
        breakdown["proven_symbol_HYPE"] = 15
    elif proven_sym == "TRXUSDT":
        total += 15
        breakdown["proven_symbol_TRX"] = 15

    concentration_penalty = int(concentration_profile.get("strategy_concentration_penalty", 0) or 0)
    if concentration_penalty:
        total += concentration_penalty
    breakdown["strategy_concentration_penalty"] = concentration_penalty
    breakdown["_strategy_top_symbol"] = concentration_profile.get("strategy_top_symbol", "")
    breakdown["_strategy_top_symbol_pnl_pct"] = concentration_profile.get("strategy_top_symbol_pnl_pct", 0.0)
    breakdown["_strategy_distinct_symbols"] = concentration_profile.get("strategy_distinct_symbols", 0)
    breakdown["_strategy_concentration_risk"] = concentration_profile.get("strategy_concentration_risk", "NONE")
    breakdown["_strategy_concentration_multiplier"] = concentration_profile.get("strategy_concentration_multiplier", 1.0)

    total = max(0, min(100, total))

    # Grade thresholds (same as Method A for consistency)
    if total >= 90:
        grade = "S"
    elif total >= 75:
        grade = "A"
    elif total >= 55:
        grade = "B"
    elif total >= 40:
        grade = "C"
    elif total >= 25:
        grade = "D"
    else:
        grade = "F"

    return {
        "ml_composite_score": total,
        "ml_composite_breakdown": breakdown,
        "ml_composite_grade": grade,
        **concentration_profile,
    }


def compute_elite_score(
    pick: dict,
    monte_carlo_results: Optional[dict] = None,
    strategy_perf: Optional[dict] = None,
    copy_trader_scorebook: Optional[dict] = None,
    indicator_pp: Optional[dict] = None,
) -> dict:
    """
    Compute elite quality score for a pick.

    =====================================================================
    IC ANALYSIS v2 (2026-03-26) — HALVED, not zeroed
    =====================================================================
    v1 zeroing caused score INVERSION: top decile 9% WR, bottom 41% WR.
    Root cause: regime_bonus dominated unchecked, pushing losing LONGs to top.
    v2 fix: HALVE anti-predictive components instead of zeroing them.
    They provide necessary counterbalance. See decile_test.py.

      PREDICTIVE (KEEP/BOOST):
        ml_score:              HALVED to 9 pts max (was 18). r=+0.337 over 367 trades
        regime_bonus:          IC=+0.19  -> boosted max from 15 to 20
        forward_wr+track_record: IC=+0.17  -> MERGED, max 40 pts
        technical_alignment:   IC=+0.16  -> boosted misalign penalty -25 -> -30

      HALVED (v2 — zeroing caused inversion):
        source_system:         IC=-0.18  -> HALVED to max 10 pts (was 20)
        age_freshness:         IC=-0.076 -> HALVED to -2/+2 pts (was -5/+5)
        leverage_safety:       IC=-0.05  -> HALVED to max 5 pts (was 10)

      STILL ZEROED (truly dead):
        proven_strategy_bonus: IC=-0.003 -> ZEROED (basically dead)
        risk_reward:           IC=-0.127 -> ZEROED

      NEUTRAL (kept as-is):
        signal_quality, volume, confluence
    =====================================================================

    Returns dict with:
      - elite_score: int (0-100)
      - elite_breakdown: dict with component scores
      - elite_grade: str (S/A/B/C/D/F)
    """
    # --- Auto-rebuild strategy_performance.json if missing or stale (>1 hour) ---
    if strategy_perf is None:
        data_dir = Path(__file__).resolve().parent / "data"
        perf_path = data_dir / "strategy_performance.json"
        needs_rebuild = True
        if perf_path.exists():
            age_seconds = time.time() - perf_path.stat().st_mtime
            if age_seconds < 3600:
                needs_rebuild = False
        if needs_rebuild:
            closed_path = data_dir / "closed_picks.json"
            if closed_path.exists():
                strategy_perf = rebuild_strategy_performance(closed_path)
            else:
                strategy_perf = load_strategy_performance(data_dir)
        else:
            strategy_perf = load_strategy_performance(data_dir)

    # Flatten extra_json so all fields are accessible uniformly
    pick = _flatten_extra_json(pick)

    score = 0.0
    breakdown = {}
    source_sys = str(pick.get("source_system", "") or "").lower()

    # =========================================================================
    # 0. Copy trader confidence deflation (2026-03-19 scoring audit)
    # Copy trader scrapers set confidence based on trader profile quality
    # (PnL, account size, trade count) — NOT signal quality like other systems.
    # A 0.95 confidence from copy_hl means "good trader", not "strong signal".
    # The 80% WR correlation for conf>=0.70 was calibrated on non-copy picks.
    # Deflate to avoid gaming the ML replacement score component.
    # =========================================================================
    _ct_strategy = (pick.get("strategy") or "").lower()
    _ct_source = source_sys
    _is_copy_pick = any(tag in _ct_strategy for tag in [
        "copy_hl_", "copy_trader", "clone_hl_", "bitget_copy",
        "okx_copy", "okx_futures_", "hs_", "binance_smart",
        "multi_asset_", "cta_", "dna_clone_",
    ]) or "copy_trader" in _ct_source or "copy_trader" in _ct_strategy \
       or _ct_source.startswith("multi_asset_")
    if _is_copy_pick:
        raw_conf = coerce_confidence(pick.get("confidence"), default=0.0)
        # Cap copy trader confidence at 0.60 — "moderate" tier, not "proven"
        # This prevents them from getting 12-15 pts in the ML component
        if raw_conf > 0.60:
            pick = dict(pick)  # shallow copy to avoid mutating original
            pick["confidence"] = 0.60
        breakdown["_copy_trader"] = True
        breakdown["_original_confidence"] = raw_conf

    # =========================================================================
    # 1. ML-composite score (0-25 points) -- PREDICTOR #1 (IC=+0.33)
    #    Zero out anti-predictive ML replacement components.
    #    Increase weight for actual ML scores to 25 pts.
    # =========================================================================
    ml_val = pick.get("ml_score")
    ml_pts = 0.0
    if ml_val is not None:
        try:
            ml_val = float(ml_val)
            if ml_val >= 0.60:
                # Scale 0.60 -> 0.90+ to 5 -> 25 pts
                ml_pts = min(25, (ml_val - 0.60) * 66.7 + 5)
        except (ValueError, TypeError):
            pass

    # ML proven strategy override — bypass scoring for empirically verified leaders
    _strategy_name_for_ml = pick.get("strategy", "")
    if _strategy_name_for_ml in ML_PROVEN_STRATEGIES:
        _proven_wr = ML_PROVEN_STRATEGIES[_strategy_name_for_ml]
        # Map proven WR (81-94%) to 5-25 pts
        ml_pts = int(min(25, (_proven_wr - 75) * 25 / 19))
        breakdown["_ml_proven_override"] = f"{_strategy_name_for_ml} WR={_proven_wr}%"
    else:
        # Zero out anti-predictive replacement logic (Action 3 remediation)
        # ml_pts = compute_ml_replacement_score(pick)
        # breakdown["_ml_replacement_zeroed"] = True
        pass

    breakdown["ml_score"] = ml_pts
    score += ml_pts

    # 1b. Confidence score (0-20 points) -- Integrated Predictor
    #     User requirement: Increase weights for ml_score (25) and confidence (20).
    conf_pts = 0.0
    conf_val = pick.get("confidence")
    if conf_val is not None:
        try:
            conf_val = float(conf_val)
            if conf_val > 1.0: conf_val /= 100.0  # normalize
            if 0.60 <= conf_val <= 0.85:
                # Sweet spot: 60-85% confidence gets best scores (20 pts)
                conf_pts = min(20, (conf_val - 0.60) * 80 + 5)
            elif conf_val > 0.85:
                # Overconfident: penalize (20 -> 5 pts)
                conf_pts = 5
        except (ValueError, TypeError):
            pass

    breakdown["confidence_score"] = round(conf_pts, 1)
    score += conf_pts

    # =========================================================================
    # 2. Strategy forward-validated win rate (0-30 points) -- 2nd best predictor
    #    Strategies with >55% WR on 10+ trades get full marks.
    #    Also considers profit factor from strategy_performance.json.
    # =========================================================================
    fw_wr = pick.get("forward_wr", 0) or 0
    fw_trades = pick.get("forward_trades", 0) or 0
    strategy_name = pick.get("strategy", "")

    # NORMALIZE: forward_wr is stored inconsistently — some sources write it as a
    # percentage (22.2, 36.6, 100.0) and others as a decimal (0.7059, 0.6286).
    # Scoring thresholds use decimal form (> 0.55 etc.), so a raw 22.2 looks like
    # 2220% win rate and scores maximum forward_wr points — this is the root cause
    # of high-score picks with losing strategies (e.g. cta_tsmom_blend 15% WR = 66 score).
    # Fix: normalize any value > 1.0 to decimal.  (2026-03-25)
    if fw_wr > 1.0:
        fw_wr = fw_wr / 100.0

    # =========================================================================
    # COPY TRADER DEFLATION (2026-03-19 scoring audit fix)
    # Copy trader picks inject the TRADER's historical WR/trades as forward_wr
    # and forward_trades. This massively inflates scores because a trader with
    # 1220 trades and 100% WR gets full 30 pts forward credit — but that's
    # the trader's self-reported stats, NOT our verified forward performance.
    # Fix: cap copy trader forward credit and flag as unverified.
    # =========================================================================
    _is_copy_trader = any(tag in strategy_name.lower() for tag in [
        "copy_hl_", "copy_trader", "clone_hl_", "bitget_copy",
        "okx_copy", "okx_futures_", "hs_", "binance_smart",
        "multi_asset_", "cta_", "dna_clone_",
    ]) or "copy_trader" in (pick.get("source_system") or "").lower() \
       or (pick.get("source_system") or "").lower().startswith("multi_asset_")

    if _is_copy_trader:
        # Trader-reported stats are NOT forward-validated system performance.
        # Cap: max 8 pts (equivalent to 3-4 verified trades with decent WR).
        # The real edge must be proven by our own closed-pick tracking.
        _trader_wr = fw_wr
        _trader_trades = fw_trades
        # Reset to reflect actual system-verified performance (0 until proven)
        fw_wr = 0
        fw_trades = 0
        # Check if strategy_performance has real closed data for this strategy
        if strategy_perf and strategy_name in strategy_perf:
            sp = strategy_perf[strategy_name]
            _real_trades = sp.get("closed_picks", 0)
            if _real_trades >= 1:
                fw_trades = _real_trades
                fw_wr = sp.get("win_rate", 0)
                # These are real verified trades — normal scoring applies

    # Enrich from strategy_performance if available.
    # Prefer strategy_performance.json (verified closed picks) over the pick-level
    # forward_wr when strategy_perf has substantial data (>= 10 trades).
    # Previously this only kicked in when fw_wr == 0, which allowed inflated
    # percentage-stored forward_wr values to bypass the verified data entirely.
    if strategy_perf and strategy_name in strategy_perf:
        sp = strategy_perf[strategy_name]
        sp_trades = sp.get("closed_picks", 0)
        if fw_trades == 0:
            fw_trades = sp_trades
        if fw_wr == 0:
            fw_wr = sp.get("win_rate", 0)
        # If strategy_perf has 10+ verified trades, prefer it over pick-level data
        # (pick-level forward_wr may be stale, from a different source, or pre-normalization)
        elif sp_trades >= 10:
            fw_wr = sp.get("win_rate", 0)
            fw_trades = sp_trades
        profit_factor = sp.get("profit_factor", 0) or 0
    else:
        profit_factor = 0

    # For ml_enhanced strategies, extract base strategy name for perf lookup
    if fw_trades == 0 and strategy_name.startswith("ml_enhanced_") and strategy_perf:
        # Extract symbol from strategy name (e.g., "ml_enhanced_FETUSDT_1d_B_lightgbm" -> "FETUSDT")
        parts = strategy_name.replace("ml_enhanced_", "").split("_")
        strat_symbol = parts[0] if parts else ""
        for sp_name, sp_data in strategy_perf.items():
            # Only match if same symbol prefix AND enough data
            if (sp_name.startswith(f"ml_enhanced_{strat_symbol}")
                    and sp_data.get("closed_picks", 0) >= 10):
                fw_trades = sp_data.get("closed_picks", 0)
                fw_wr = sp_data.get("win_rate", 0)
                profit_factor = sp_data.get("profit_factor", 0) or 0
                break

    # 2026-03-24 FIX: Forward WR + track record DOUBLED from 30 to 40 max pts.
    # This is the 2nd-best predictor (IC=+0.17) and was under-weighted relative
    # to anti-predictive components that have now been zeroed. Increasing its
    # contribution restores score separation between proven and unproven strategies.
    fwd_pts = 0.0
    if fw_trades >= 10 and fw_wr > 0.55:
        # Scale: 40% WR = 0 pts, 65%+ WR = 40 pts (was 30)
        fwd_pts = min(40, (fw_wr - 0.40) * 160)
        # Bonus for strong profit factor
        if profit_factor >= 2.0:
            fwd_pts = min(40, fwd_pts * 1.15)
    elif fw_trades >= 5 and fw_wr > 0.45:
        fwd_pts = min(30, (fw_wr - 0.35) * 100)
        if profit_factor >= 1.5:
            fwd_pts = min(30, fwd_pts * 1.1)
    elif fw_trades >= 3 and fw_wr > 0.40:
        fwd_pts = min(18, (fw_wr - 0.30) * 60)
    elif fw_trades >= 1:
        fwd_pts = min(8, fw_wr * 16)

    # Unvalidated strategies: give baseline pts -- shouldn't be punished for being new
    if fw_trades == 0 and fwd_pts == 0:
        # Verified copy traders (copy_hl_* with 50+ trader-reported trades) get higher baseline
        if _is_copy_trader and "copy_hl_" in _ct_strategy:
            if _trader_trades >= 50:
                fwd_pts = 15  # Verified copy trader with deep track record (15/30)
            else:
                fwd_pts = 5   # Unverified/new copy trader -- standard baseline (5/30)
        else:
            fwd_pts = 5  # Baseline for unproven -- better than 0, less than proven (30)
    elif fw_trades < 10:
        fwd_pts = max(fwd_pts, 5)  # At least 5 pts even with few trades
        fwd_pts = min(fwd_pts, 10)  # Cap at 10 until 10+ trades

    concentration_profile = _get_strategy_concentration_profile(strategy_name, strategy_perf)
    fwd_pts_pre_concentration = fwd_pts
    if fwd_pts > 0:
        fwd_pts *= float(concentration_profile.get("strategy_concentration_multiplier", 1.0) or 1.0)

    # =========================================================================
    # MERGED: Track Record into Forward WR (2026-03-24)
    # Previously Forward WR (0-30 pts) and Track Record (-5 to +20 pts) were
    # scored independently, allowing up to 50 pts combined from the same
    # data source (strategy_performance.json). This double-counted strategy WR.
    # Now merged into a single component capped at 30 pts total.
    # Track Record adds a bonus/penalty on top of Forward WR, but the sum
    # is clamped to [-5, 30] so the combined weight stays within budget.
    # =========================================================================
    _track_adj = 0
    _track_basis = "none"
    if strategy_perf and strategy_name in strategy_perf:
        _sp_track = strategy_perf[strategy_name]
        _sp_closed = _sp_track.get("closed_picks", 0)
        _sp_wr = _sp_track.get("win_rate", 0)
        if _sp_closed >= 5:
            _track_basis = "strategy"
            if _sp_wr > 0.55:
                _track_adj = 10   # Proven winner bonus (folded from old track_record 20 -> 10)
            elif _sp_wr > 0.45:
                _track_adj = 5    # Decent track record (folded from old track_record 10 -> 5)
            elif _sp_wr < 0.25 and _sp_closed >= 20:
                _track_adj = -5   # Extreme loser penalty
            elif _sp_wr < 0.35 and _sp_closed >= 10:
                _track_adj = -4   # Proven loser penalty
    # Fallback: system-level proxy (partial credit)
    if _track_adj == 0 and _track_basis == "none":
        _sys_wr = float(pick.get("system_win_rate", pick.get("win_rate", 0)) or 0)
        _sys_closed = int(pick.get("system_closed_picks", pick.get("closed_picks", 0)) or 0)
        if _sys_wr > 0 and _sys_closed >= 5:
            _track_basis = "system"
            if _sys_wr > 0.55:
                _track_adj = 3
            elif _sys_wr > 0.45:
                _track_adj = 2
            elif _sys_wr < 0.35:
                _track_adj = -2
        elif _sys_wr > 0:
            _track_basis = "system_sparse"
            if _sys_wr > 0.55:
                _track_adj = 1

    # Combine Forward WR + Track Record, clamp to [-5, 40] (doubled from 30)
    fwd_pts = max(-5, min(40, fwd_pts + _track_adj))

    breakdown["forward_wr"] = round(max(-5, min(40, fwd_pts)), 1)
    breakdown["_forward_wr_includes_track_record"] = True
    breakdown["_track_record_adj"] = _track_adj
    breakdown["_track_record_basis"] = _track_basis
    breakdown["_forward_wr_pre_concentration"] = round(fwd_pts_pre_concentration, 1)
    score += fwd_pts

    # =========================================================================
    # 2b. Source System Tier — ZEROED (Anti-predictive)
    #     User requirement: Zero out anti-predictive components.
    # =========================================================================
    sys_pts = 0.0
    breakdown["source_system"] = 0.0
    # score += 0

    # =========================================================================
    # 3. Confluence scoring (-20 to +5 points) -- HERDING PENALTY
    #    Empirical data (P2-03 audit):
    #      2-3 systems agreeing = 42% WR (sweet spot, mild conviction bonus)
    #      4-7 systems agreeing = 34.8% WR (herding, anti-predictive)
    #    Old penalty was only -5 max, letting 4+ consensus picks pass easily.
    #    New tiered schedule penalizes herding much more aggressively.
    # =========================================================================
    confluence_strategies = pick.get("confluence_strategies", [])
    n_strategies = len(confluence_strategies)
    convergence = pick.get("convergence", 0) or 0
    _agreement = max(n_strategies, convergence)

    confl_pts = 0.0
    if _agreement >= 7:
        confl_pts = -20  # Extreme herding -- nearly always wrong
    elif _agreement >= 5:
        confl_pts = -10  # Heavy herding -- 34.8% WR empirically
    elif _agreement == 4:
        confl_pts = 0    # Neutral -- starting to herd, no bonus
    elif _agreement >= 2:
        confl_pts = 0    # 42% WR = least bad, but still sub-50% -- no bonus warranted
    # Solo picks (0-1 strategies) get 0 -- no data edge either way

    breakdown["confluence"] = round(confl_pts, 1)
    score += confl_pts

    # =========================================================================
    # 3b. KOL Consensus Alignment (0-15 pts)
    #     Bonus when pick aligns with KOL consensus from predictions/kol/.
    #     Two modes:
    #     A) Pick IS a kol_consensus pick — use its embedded metadata
    #     B) Pick from another system — check if KOL consensus agrees
    #     Category diversity is the key discriminant (not raw vote count):
    #       TA + on-chain + macro agreeing is far stronger than 5 TA analysts.
    #     Capped at 15 pts to avoid KOL-dominance. forward_test_only until proven.
    # =========================================================================
    kol_pts = 0.0
    kol_count = pick.get("consensus_count") or pick.get("kol_consensus_count") or 0
    kol_diversity = pick.get("kol_category_diversity") or 0
    kol_avg_wr = pick.get("kol_avg_wr") or 0.0

    if kol_count > 0:
        # Mode A: this IS a KOL consensus pick or has KOL metadata
        if kol_count >= 5 and kol_diversity >= 3:
            kol_pts = 12  # ULTRA: 5+ KOLs from 3+ categories
        elif kol_count >= 3 and kol_diversity >= 2:
            kol_pts = 8   # STRONG: 3-4 KOLs from 2+ categories
        elif kol_count >= 2:
            kol_pts = 4   # MODERATE: 2 KOLs
        # Track record bonus
        if kol_avg_wr >= 0.60:
            kol_pts += 3
        elif kol_avg_wr >= 0.50:
            kol_pts += 1
        if pick.get("consensus_signal_source") == "news_inferred":
            kol_pts = min(kol_pts * 0.25, 2.0)
    else:
        # Mode B: check if KOL consensus file agrees with this pick's symbol+direction
        # (lazy-loaded once per scoring batch via module-level cache)
        _kol_match = _check_kol_alignment(
            pick.get("symbol", ""), pick.get("direction", "")
        )
        if _kol_match:
            kol_pts = _kol_match.get("bonus", 0)

    kol_pts = min(15.0, kol_pts)
    breakdown["kol_consensus"] = round(kol_pts, 1)
    score += kol_pts

    # =========================================================================
    # 3c. Position performance -- ZEROED (P1-05)
    #     Position performance is backward-looking momentum, not predictive.
    #     It rewarded picks already winning (up to 10 pts) -- momentum-chasing
    #     bias. Was also double-counted with "Currently Winning" in
    #     smart_picks_engine (since removed there too). Combined 20 pts from
    #     backward-looking signals distorted ranking toward recent winners.
    # =========================================================================
    pos_pts = 0

    breakdown["position"] = round(pos_pts, 1)
    score += pos_pts

    # =========================================================================
    # 3c. Regime bonus -- IC=+0.19 (BEST predictor per ic_weighted_selector)
    #     BOOSTED: max increased from 15 to 20 pts.
    #     Picks that match market regime direction get a bonus:
    #     LONG in bull/trending = +5, SHORT in bear = +5
    #     Ranging regime = +20 (was 15, boosted per IC findings)
    #     Transition = +1
    # =========================================================================
    regime_bonus = 0
    _regime = (pick.get("regime_at_entry") or pick.get("regime_trend_direction") or
               pick.get("regime_at_signal") or pick.get("btc_regime") or
               pick.get("hmm_regime") or pick.get("market_regime") or "").lower().strip()
    # LIVE REGIME LOOKUP: if pick has no regime data, read from hmm_regime.json
    if not _regime:
        try:
            import os as _os
            _hmm_path = _os.path.join(_os.path.dirname(__file__), "data", "hmm_regime.json")
            if _os.path.exists(_hmm_path):
                import json as _json
                with open(_hmm_path, encoding="utf-8") as _hf:
                    _hmm = _json.load(_hf)
                _agg = _hmm.get("aggregate", {})
                _regime = str(_agg.get("market_regime", _hmm.get("market_regime", ""))).lower().strip()
                if not _regime:
                    _overview = _hmm.get("market_overview", {})
                    _n_bear = _overview.get("bear_count", _hmm.get("n_bear", 0))
                    _n_bull = _overview.get("bull_count", _hmm.get("n_bull", 0))
                    if _n_bear > _n_bull * 1.5:
                        _regime = "bear"
                    elif _n_bull > _n_bear * 1.5:
                        _regime = "bull"
        except Exception:
            pass
    # Map non-standard regime values
    _regime_map = {"momentum": "trending", "accumulation": "bullish", "distribution": "bearish",
                   "recovery": "bullish", "correction": "bearish", "breakout": "trending",
                   "consolidation": "ranging", "range": "ranging", "mean_reverting": "ranging"}
    _regime = _regime_map.get(_regime, _regime)
    _fg = float(pick.get("fear_greed_index", 50) or 50)
    # If no regime AND no F&G, try to infer from regime_compatible
    if not _regime and pick.get("regime_compatible") is True:
        _regime = "neutral"  # At least compatible, give it neutral credit
    _dir_raw = pick.get("direction", "") or ""
    if _dir_raw in ("None", "none", "null", ""):
        _dir_raw = pick.get("signal_type", "") or ""
    if _dir_raw in ("None", "none", "null", ""):
        _dir_raw = pick.get("side", "") or ""
    _direction = str(_dir_raw).upper().strip()

    # =========================================================================
    # 3c-i. Asset Class Neutrality (Mar 28 2026)
    #      Forex/Futures are macro-driven; BTC regime and FGI are often irrelevant.
    #      Give these assets a neutral regime baseline (10 pts) to prevent
    #      inadvertent suppression by crypto-centric filters.
    # =========================================================================
    _asset_class = (pick.get("asset_class") or pick.get("category") or "crypto").strip().lower()
    is_non_crypto = any(t in _asset_class for t in ["forex", "futures", "stock", "equity", "commodity"])

    if is_non_crypto:
        regime_bonus = 10
        breakdown["regime_bonus"] = regime_bonus
        breakdown["_regime_neutral_macro"] = True
        score += regime_bonus
        # Skip direction-aware crypto regime scoring below
    else:
        # Direction-aware scoring (best predictor when direction matches regime)
        if _direction in ("LONG", "BUY"):
            if _regime in ("bull", "trending", "bullish", "uptrend"):
                regime_bonus = 5   # LONG in bull market = strong alignment
            elif _regime in ("ranging", "sideways", "range"):
                regime_bonus = 15  # Ranging regime = 92.3% WR (best regime)
            elif _regime in ("bear", "bearish", "downtrend", "crash", "crisis"):
                if _fg <= 20:
                    # CONTRARIAN BOUNCE BONUS (IC=+0.24 in extreme fear/oversold)
                    regime_bonus = 15  # Extreme fear = capitulation = bottoming process
                    breakdown["_contrarian_bounce_bonus"] = True
                else:
                    regime_bonus = 0   # LONG in bear = counter-trend, no bonus
            elif _regime in ("neutral",) and _fg > 50:
                regime_bonus = 2   # Neutral but sentiment positive
            elif _regime in ("choppy", "neutral"):
                regime_bonus = 0
            elif _regime in ("transition", "transitional"):
                regime_bonus = 1
            elif not _regime and _fg > 60:
                regime_bonus = 2   # No regime data but sentiment is greedy
            elif not _regime and _fg < 25:
                regime_bonus = 0   # Extreme fear
        elif _direction in ("SHORT", "SELL"):
            if _regime in ("bear", "bearish", "downtrend", "crash", "crisis"):
                regime_bonus = 20  # SHORT in bear = strong alignment -- BOOSTED per IC=+0.19
            elif _regime in ("ranging", "sideways", "range"):
                regime_bonus = 20  # Ranging regime = 92.3% WR (best regime) -- BOOSTED per IC=+0.19
            elif _regime in ("bull", "trending", "bullish", "uptrend"):
                regime_bonus = -30  # SELL in non-bearish regime: penalize (30.1% WR for SELL overall)
            elif _regime in ("neutral",) and _fg < 50:
                regime_bonus = 2   # Neutral but sentiment fearful = good for shorts
            elif _regime in ("choppy", "neutral"):
                regime_bonus = 0
            elif _regime in ("transition", "transitional"):
                regime_bonus = 1
            elif not _regime and _fg < 25:
                regime_bonus = 2   # No regime data but extreme fear = good for shorts
        else:
            # No direction info -- fall back to generic regime bonus
            if _regime in ("ranging", "sideways", "range"):
                regime_bonus = 20  # Ranging = 92.3% WR -- BOOSTED per IC=+0.19
            elif _regime in ("trending", "bull", "bullish"):
                regime_bonus = 3
            elif _regime in ("neutral",) and _fg > 50:
                regime_bonus = 2   # Neutral but sentiment positive
            elif _regime in ("choppy", "neutral"):
                regime_bonus = 0
            elif _regime in ("bearish", "bear", "crash", "crisis"):
                regime_bonus = 0   # No bonus in bearish
            elif _regime in ("transition", "transitional"):
                regime_bonus = 1
            elif not _regime and _fg > 60:
                regime_bonus = 2   # No regime data but sentiment is greedy
            elif not _regime and _fg < 25:
                regime_bonus = 0   # Extreme fear
    
    if not is_non_crypto:
        breakdown["regime_bonus"] = regime_bonus
        score += regime_bonus

    # =========================================================================
    # Session bonus -- DISABLED per cross-AI consensus (Kimi audit: no edge)
    # Was 0-5 points based on Asia/London/NY session. xBrat data unvalidated.
    # =========================================================================
    session_pts = 0  # Disabled per cross-AI consensus (Kimi audit: no edge)
    breakdown["session_bonus"] = 0

    # =========================================================================
    # 3d. Age freshness — ZEROED (Anti-predictive)
    #     User requirement: Zero out anti-predictive components.
    # =========================================================================
    age_pts = 0
    breakdown["age_freshness"] = 0
    # score += 0

    # =========================================================================
    # 4. Risk:Reward ratio -- ZEROED: IC=-0.127 (anti-predictive per ic_weighted_selector)
    #    Was 0-5 pts. IC analysis on 1927 picks shows R:R is anti-predictive.
    #    Higher R:R picks have LOWER win rates (R:R 3.0+ = 0% WR).
    #    Zeroed out to stop penalizing good picks with modest R:R.
    # =========================================================================
    rr_pts = 0  # ZEROED: IC=-0.127 (anti-predictive per ic_weighted_selector)
    breakdown["risk_reward"] = 0
    breakdown["_risk_reward_zeroed_reason"] = "IC=-0.127 anti-predictive"
    # score += 0  # intentionally no contribution

    # =========================================================================
    # 4b. Symbol edge bonus (0-5 pts) — data-driven from closed picks
    #     Symbols with proven positive expectancy on 5+ trades get a boost.
    #     Only 7 symbols are profitable; the rest are net negative.
    # =========================================================================
    _sym = (pick.get("symbol", "") or "").upper().replace("-", "")
    # Profitable symbols: FET (84% WR), RENDER (95%), BNB (79%),
    # FARTCOIN (83%), ANKR (47%), LINK (50%), TRX (67%)
    _PROVEN_PROFITABLE_SYMBOLS = {
        "FETUSDT": 5,      # 84% WR, +631% PnL — crown jewel
        "RENDERUSDT": 5,   # 95% WR, +258% PnL
        "TAOUSDT": 5,      # 36% WR BUT +27% PnL on 107 trades in quan_engine — fat tail winner
        "BNBUSDT": 3,      # 79% WR, +82% PnL
        "HYPEUSDT": 3,     # quan_engine: +42% PnL — consistent winner
        "FARTCOINUSDT": 3, # 83% WR, +8% PnL (small sample)
        "TRXUSDT": 3,      # 55% WR in quan_engine (103 trades) — most consistent
        "LINKUSDT": 2,     # 50% WR, +23% PnL
        "ANKRUSDT": 1,     # 47% WR, +25% PnL (borderline)
    }
    sym_edge_pts = _PROVEN_PROFITABLE_SYMBOLS.get(_sym, 0)
    breakdown["symbol_edge"] = sym_edge_pts
    score += sym_edge_pts

    # =========================================================================
    # 4b2. Market Cap / Liquidity Tier bonus (-5 to +10 pts)
    #      Paper trade evidence: large-cap coins (PAXG, SOL, ZEC, DOGE) ALL won
    #      while micro-caps (REZ, RESOLV) ALL lost — regardless of score.
    #      Crypto:     Tier1 +10, Tier2 +5, others -5.
    #      Non-crypto: Tier1 +10, Tier2 +5, others 0 (no micro-cap penalty).
    #      FIX-L (2026-04-22): asset_class now forwarded so EQUITY/FOREX/
    #      COMMODITY/FUTURES/ETF get their own tier sets.
    # =========================================================================
    mcap_pts = market_cap_tier_score(_sym, _asset_class)
    breakdown["market_cap_tier"] = mcap_pts
    score += mcap_pts

    # =========================================================================
    # 4c. Expectancy bonus (-5 to +8 pts) — avg PnL per trade from track record
    #     Spearman test (2026-03-24): elite_score vs PnL = 0.026 (random).
    #     Root cause: scoring rewarded high-WR strategies that win small/lose big.
    #     Fix: directly reward positive avg PnL (profit expectancy) per trade.
    #     Strategies with positive expectancy on 10+ trades = proven money makers.
    # =========================================================================
    _exp_pts = 0
    if strategy_perf and strategy_name in strategy_perf:
        _sp_exp = strategy_perf[strategy_name]
        _exp_trades = _sp_exp.get("closed_picks", 0)
        _exp_avg_pnl = _sp_exp.get("avg_pnl", 0) or 0
        if _exp_trades >= 10:
            if _exp_avg_pnl >= 0.02:       # +2% avg PnL per trade
                _exp_pts = 8               # Strong money maker
            elif _exp_avg_pnl >= 0.005:    # +0.5% avg PnL
                _exp_pts = 5               # Solid positive expectancy
            elif _exp_avg_pnl >= 0:        # Breakeven
                _exp_pts = 2               # At least not losing
            elif _exp_avg_pnl >= -0.005:   # Small losses
                _exp_pts = -2              # Mild penalty
            else:                          # Losing > 0.5% per trade
                _exp_pts = -5              # Proven money loser
        elif _exp_trades >= 5:
            if _exp_avg_pnl >= 0.01:
                _exp_pts = 4
            elif _exp_avg_pnl < -0.01:
                _exp_pts = -3
    breakdown["expectancy"] = _exp_pts
    score += _exp_pts

    # =========================================================================
    # 4c1b. Source-system confidence recalibration (quan_engine specific)
    #       Investigation (2026-03-26): quan_engine conf 0.50-0.59 has 36.7% WR
    #       while conf 0.60-0.69 has only 19.8% WR — confidence is INVERTED.
    #       BUY direction: 24.7% WR (terrible), SELL: 42.9% WR (much better).
    #       Apply direction penalty for BUY picks from this source.
    # =========================================================================
    _source = (pick.get("source_system") or "").lower()
    _direction_for_source = (pick.get("direction") or pick.get("signal_type") or "").upper()
    _source_adj = 0
    if _source == "quan_engine":
        if _direction_for_source in ("BUY", "LONG"):
            _source_adj = -5  # BUY has 24.7% WR — penalize
        elif _direction_for_source in ("SELL", "SHORT"):
            _source_adj = +5  # SELL has 42.9% WR — reward
    # 2026-04-05 forensic: alpha_engine LONG = 36.4% WR / -0.00% avg PnL (n=948)
    # vs alpha_engine SHORT = 66.7% WR / +1.31% avg PnL (n=9). Skipping 948 LONGs
    # lifts portfolio WR 46.06% -> 49.65% and avg PnL 0.106% -> 0.146%.
    # Live TV paper: 3 alpha_engine/ml_crypto_pred LONGs lost avg -2.35%;
    # 3 tsmom_strategy SHORTs won avg +6.13% same day.
    elif _source == "alpha_engine":
        if _direction_for_source in ("BUY", "LONG"):
            _source_adj = -6  # 36.4% WR LONG bias on 948 trades — penalize
            # 2026-04-05 what-if: on red BTC days, 11/11 alpha_engine LONGs bled (-2.40% avg).
            # Double the penalty when BTC regime is bearish to auto-reject from smart picks.
            _btc_reg_a = (pick.get("btc_regime") or pick.get("regime_at_entry") or "").upper()
            if "BEAR" in _btc_reg_a or "DOWN" in _btc_reg_a or _btc_reg_a == "BEARISH" or pick.get("btc_below_200ma"):
                _source_adj -= 8  # total -14 on alpha_engine LONG in BEAR regime
        elif _direction_for_source in ("SELL", "SHORT"):
            _source_adj = +4  # 66.7% WR SHORT (n=9) — small reward
    elif _source == "ml_crypto_pred" and _direction_for_source in ("BUY", "LONG"):
        _source_adj = -5  # 31.3% WR LONG (n=112), -0.44% avg PnL
        # Also amplify in BEAR regime (same rationale)
        _btc_reg_m = (pick.get("btc_regime") or pick.get("regime_at_entry") or "").upper()
        if "BEAR" in _btc_reg_m or "DOWN" in _btc_reg_m or _btc_reg_m == "BEARISH" or pick.get("btc_below_200ma"):
            _source_adj -= 6  # total -11
    elif _source == "fast_stocks_competition" and _direction_for_source in ("BUY", "LONG"):
        _source_adj = -6  # 14.3% WR LONG (n=21), -1.95% avg PnL
    elif _source == "tsmom_strategy" and _direction_for_source in ("SELL", "SHORT"):
        _source_adj = +5  # Live edge: 3/3 SHORTs won +6.13% avg 2026-04-05
    breakdown["source_direction_adj"] = _source_adj
    score += _source_adj

    # 2026-04-05: "Distribution Cascade" signature boost (from KITE +8.7% forensic)
    # When a SHORT pick carries tsmom/trend-continuation indicators AND BTC is bearish:
    #   - momentum_14d rank in bottom quintile (already filtered by tsmom)
    #   - realized_vol_ann >= 100% (high-vol name)
    # Boost SHORTs by +4 when signature present. Strategies include tsmom_volscaled.
    try:
        _pick_mom = pick.get("momentum_pct") or pick.get("momentum_14d")
        _pick_vol = pick.get("realized_vol_ann") or pick.get("volatility")
        _btc_regime = (pick.get("btc_regime") or pick.get("regime") or "").upper()
        if (_direction_for_source in ("SELL", "SHORT")
            and _pick_mom is not None and float(_pick_mom) <= -15
            and _pick_vol is not None and float(_pick_vol) >= 100
            and ("BEAR" in _btc_regime or "CHOP" in _btc_regime)):
            breakdown["distribution_cascade_boost"] = +4
            score += 4
    except (TypeError, ValueError):
        pass

    # =========================================================================
    # 4c2. Volatility predictability score (-10 to +10 pts)
    #      Neural net + closed picks confirm ATR% is #1 predictive feature.
    #      High-vol picks: 53.1% WR, Sharpe +0.218
    #      Low-vol picks: 29.2% WR, Sharpe -0.346
    #      Spread: +24pp -- bigger than any other single feature.
    #      Uses price_change_24h_abs injected by production_scanner volatility filter.
    # =========================================================================
    _vol_pts = 0
    _vol_change = pick.get("price_change_24h_abs")
    if _vol_change is not None:
        try:
            _vol_change = abs(float(_vol_change))
            _vol_pts = volatility_predictability_score(
                _sym, _vol_change,
                category=(pick.get("category") or "").lower(),
            )
        except (ValueError, TypeError):
            pass
    breakdown["volatility_predictability"] = _vol_pts
    score += _vol_pts

    # =========================================================================
    # 4d. Strategy momentum bonus (0-3 pts)
    #     After WIN = 65.6% WR, after LOSS = 24.1% WR (500 closed picks).
    # =========================================================================
    _strat_name = (pick.get("strategy") or "").lower()
    _strat_perf = (strategy_perf or {}).get(_strat_name, {})
    _last_outcome = _strat_perf.get("last_outcome", "")
    _strat_streak = int(_strat_perf.get("win_streak", 0) or 0)
    momentum_pts = 0
    if _last_outcome == "WON":
        momentum_pts = 3 if _strat_streak >= 3 else 2
    elif _last_outcome == "LOST":
        momentum_pts = -2
    breakdown["strategy_momentum"] = momentum_pts
    score += momentum_pts

    # =========================================================================
    # 4e. Time-of-day bonus (-2 to +3 pts)
    #     Hour 1 UTC = 80% WR, Hour 2 = 67%, Hour 7/14/16 = 60%
    #     Hour 21 = 0%, Hour 19 = 0%, Hour 10 = 0%, Hour 15 = 17%
    #     Based on 500 closed picks by entry hour.
    # =========================================================================
    from datetime import datetime, timezone
    _now_hour = datetime.now(timezone.utc).hour
    _HOUR_BONUS = {
        1: 3, 2: 2, 7: 2, 14: 2, 16: 2,   # Best hours (60-80% WR)
        21: -2, 19: -2, 10: -2, 15: -1,     # Worst hours (0-17% WR)
    }
    hour_pts = _HOUR_BONUS.get(_now_hour, 0)
    breakdown["time_of_day"] = hour_pts
    score += hour_pts

    # =========================================================================
    # 5. Monte Carlo validation -- DISABLED (always 0)
    #    Disabled per cross-AI consensus (dead code, anti-predictive: 10% WR)
    #    Audit data: 10% WR when MC active, -1.95% avg P/L = ANTI-PREDICTIVE.
    #    MC "PROVEN" strategies actually performed WORSE than unvalidated ones.
    #    Zeroed out to stop rewarding statistical noise.
    # =========================================================================
    mc_pts = 0.0  # Disabled per cross-AI consensus (dead code, anti-predictive: 10% WR)
    breakdown["monte_carlo"] = 0
    # score += 0  # intentionally no contribution

    # =========================================================================
    # 5b. Leverage Safety — ZEROED (Anti-predictive)
    #     User requirement: Zero out anti-predictive components.
    # =========================================================================
    lev_pts = 0.0
    breakdown["leverage_safety"] = 0.0
    # score += 0

    # =========================================================================
    # 6. Volume confirmation (0-5 points) -- enhanced with surge detection
    #    Audit showed volume_ratio > 2.0 at entry correlates with winners.
    #    Bumped from 0-3 to 0-5 pts with better thresholds.
    # =========================================================================
    vol_pts = 0
    vr = float(pick.get("volume_ratio", 0) or 0)
    # Audit finding: volume_ratio < 5.0 = better WR than extreme spikes
    if vr >= 5.0:
        vol_pts = -8   # Extreme volume spike -- penalize (proportional to +5 max)
    elif vr >= 3.0:
        vol_pts = 2   # High volume -- mild positive
    elif vr >= 1.5:
        vol_pts = 5   # Normal-elevated volume -- best zone
    elif vr >= 1.0:
        vol_pts = 3   # Normal volume -- good
    elif vr > 0:
        vol_pts = 1   # Below average but present
    breakdown["volume"] = vol_pts
    score += vol_pts

    # =========================================================================
    # 7. Signal quality bonus (0-10 pts) -- aggregates new module outputs
    # =========================================================================
    sq_pts = 0
    # Pattern predictor: golden pattern = +5, danger = -5
    pattern_wr = pick.get("pattern_predicted_wr")
    if pattern_wr is not None:
        try:
            pw = float(pattern_wr)
            if pw >= 0.65:
                sq_pts += 5   # golden pattern
            elif pw <= 0.30:
                sq_pts -= 5   # danger pattern
        except (ValueError, TypeError):
            pass

    # Entry zone: strong = +3, weak = -3
    ez_score = pick.get("entry_zone_score")
    if ez_score is not None:
        try:
            ez = float(ez_score)
            if ez >= 70:
                sq_pts += 3   # strong entry zone
            elif ez < 30:
                sq_pts -= 3   # weak entry zone
        except (ValueError, TypeError):
            pass

    # Net edge: profitable after costs = +2
    net_edge = pick.get("net_edge_bps")
    if net_edge is not None:
        try:
            if float(net_edge) >= 20:
                sq_pts += 2   # clearly profitable after costs
        except (ValueError, TypeError):
            pass

    sq_pts = max(-5, min(10, sq_pts))  # clamp
    score += sq_pts
    breakdown["signal_quality"] = sq_pts

    # =========================================================================
    # 8. Meta-Label Score -- DISABLED per cross-AI consensus (same as broken ML)
    #    Was -5 to +3 points from meta-labeler ML model.
    #    ML model not trained on sufficient data; same broken pipeline as MC.
    # =========================================================================
    meta_pts = 0  # Disabled per cross-AI consensus (same as broken ML)
    breakdown["meta_label"] = 0

    # =========================================================================
    # 9. Hindsight winner bonus -- DISABLED per cross-AI consensus (survivorship bias)
    #    Was 0-3 points from winner_patterns.json. Pure survivorship bias:
    #    rewarding symbols that already won doesn't predict future winners.
    # =========================================================================
    hindsight_pts = 0  # Disabled per cross-AI consensus (survivorship bias)
    pick_symbol = (pick.get("symbol") or "").upper().replace("-USD", "USDT")
    breakdown["hindsight_winner"] = 0

    # =========================================================================
    # 10. Skyrocket potential bonus -- DISABLED per cross-AI consensus (unvalidated)
    #     Was 0-5 points from skyrocket_detector alerts. No forward-test
    #     validation exists for this signal; pure hype detection.
    # =========================================================================
    skyrocket_pts = 0  # Disabled per cross-AI consensus (unvalidated)
    breakdown["skyrocket_potential"] = 0

    # =========================================================================
    # 10b. Proven Strategy Bonus -- KEPT ZEROED (IC=-0.003, basically dead)
    #      Unlike other zeroed components, this one has near-zero IC so
    #      halving it would add noise for no counterbalancing benefit.
    #      Intentionally kept at 0 in v2 fix. See decile_test.py.
    # =========================================================================
    proven_pts = 0  # KEPT ZEROED: IC=-0.003 (basically dead, no counterbalance value)
    breakdown["proven_strategy_bonus"] = 0
    # score += 0  # intentionally no contribution

    # =========================================================================
    # 10c. Strategy Track Record -- MERGED into Forward WR (section 2)
    #      Previously scored independently (-5 to +20 pts) but this double-counted
    #      strategy WR from the same data source as Forward WR.
    #      Now folded into Forward WR with a combined 30 pt cap.
    #      Kept as 0 in breakdown for backward compatibility with dashboards.
    # =========================================================================
    breakdown["strategy_track_record"] = 0  # Merged into forward_wr
    # NOTE: _track_record_basis is set in section 2 (forward WR) where the
    # actual track record adjustment is computed. Do NOT overwrite it here.

    # =========================================================================
    # 10d. Copy Trader Evidence Bonus (-6 to +12 points)
    #      External trader stats stay conservative. The boost only comes from
    #      our own tracked history (clone/highscore tracker) and CT consensus.
    # =========================================================================
    ct_edge_pts = 0.0
    if _is_copy_trader:
        if copy_trader_scorebook is None:
            copy_trader_scorebook = load_copy_trader_scorebook()

        ct_stats, ct_basis = _lookup_copy_trader_history(pick, copy_trader_scorebook)
        ct_edge_pts += _copy_trader_history_bonus(ct_stats)

        # Consensus herding penalty (P2-03 audit):
        #   2-3 traders agreeing = 42% WR (sweet spot)
        #   4+ traders agreeing  = 34.8% WR (herding, anti-predictive)
        consensus_count = int(pick.get("consensus_count", 0) or 0)
        if consensus_count >= 7:
            ct_edge_pts -= 6   # Extreme herding
        elif consensus_count >= 5:
            ct_edge_pts -= 4   # Heavy herding
        elif consensus_count == 4:
            ct_edge_pts += 0   # Neutral -- starting to herd
        elif consensus_count == 3:
            ct_edge_pts += 0   # Was +2 — capped at 0 (consensus r=-0.075 on 1,879 trades)
        elif consensus_count == 2:
            ct_edge_pts += 0   # Was +1 — capped at 0 (consensus r=-0.075 on 1,879 trades)

        if "copy_trader_variations" in source_sys or strategy_name.lower().startswith("variation_"):
            variation_stats = copy_trader_scorebook.get("variation", {}).get(
                _normalize_copytrader_key(strategy_name)
            )
            if variation_stats and variation_stats.get("trades", 0) >= 10:
                if variation_stats.get("win_rate", 0) >= 0.60 and variation_stats.get("pnl_pct", 0) > 0:
                    ct_edge_pts += 4
                elif variation_stats.get("win_rate", 0) < 0.40:
                    ct_edge_pts -= 3
                breakdown["_variation_trades"] = variation_stats.get("trades", 0)

        ct_edge_pts = max(-6.0, min(12.0, ct_edge_pts))
        breakdown["copy_trader_edge"] = round(ct_edge_pts, 1)
        if ct_stats:
            breakdown["_copy_history_basis"] = ct_basis
            breakdown["_copy_history_trades"] = ct_stats.get("trades", 0)
            breakdown["_copy_history_wr"] = round(ct_stats.get("win_rate", 0) * 100, 1)
            breakdown["_copy_history_avg_pnl"] = round(ct_stats.get("avg_pnl", 0), 2)
        score += ct_edge_pts

    # =========================================================================
    # 11. Risk-warning penalty (-3 points)
    #     Symbols flagged with risk_warning in config.py (low liquidity,
    #     micro-cap, extreme volatility) get a small penalty to naturally
    #     deprioritize them vs safer picks at similar score levels.
    # =========================================================================
    risk_penalty = 0
    _pick_sym_upper = pick_symbol  # already uppercased + normalized above
    if _pick_sym_upper in _RISK_WARNING_SYMBOLS:
        risk_penalty = -3
    # Also check the raw symbol field (may be BAKEUSDT instead of BTC-USD format)
    elif (pick.get("symbol") or "").upper() in _RISK_WARNING_SYMBOLS:
        risk_penalty = -3
    score += risk_penalty
    breakdown["risk_warning_penalty"] = risk_penalty

    # =========================================================================
    # 12. Technical alignment gate -- IC=+0.16 (predictive per ic_weighted_selector)
    #     BOOSTED: misalignment penalty increased from -25 to -30.
    #     Multi-timeframe RSI/MACD/SMA confirmation from technical_analyzer.
    #     Aligned picks (2/3 timeframes agree with direction) get a bonus.
    #     Misaligned picks get a TIERED penalty based on how many timeframes
    #     agree with the pick direction. Paper trade evidence: 6/8 misaligned
    #     picks lost money; only technically aligned picks survived.
    #
    #     technical_buy_tfs / technical_sell_tfs = count of 1h/4h/1d timeframes
    #     that signal BUY or SELL respectively (0-3 each).
    # =========================================================================
    tech_alignment = pick.get("technical_alignment")
    tech_pts = 0
    if tech_alignment is True:
        tech_pts = 5   # Technicals confirm direction (2/3+ TFs agree)
    elif tech_alignment is False:
        # Tiered penalty based on how many timeframes agree with direction
        _buy_tfs = int(pick.get("technical_buy_tfs", 0) or 0)
        _sell_tfs = int(pick.get("technical_sell_tfs", 0) or 0)
        # Count TFs agreeing with the pick's direction
        if _direction in ("LONG", "BUY"):
            _agreeing_tfs = _buy_tfs
        elif _direction in ("SHORT", "SELL"):
            _agreeing_tfs = _sell_tfs
        else:
            _agreeing_tfs = max(_buy_tfs, _sell_tfs)  # best guess
        if _agreeing_tfs == 0:
            tech_pts = -30  # 0/3 TFs agree -- catastrophic misalignment (BOOSTED per IC=+0.16)
        elif _agreeing_tfs == 1:
            tech_pts = -20  # 1/3 TFs agree -- strong misalignment (BOOSTED per IC=+0.16)
        else:
            tech_pts = -5   # 2/3 TFs agree but still flagged misaligned
        breakdown["_technical_agreeing_tfs"] = _agreeing_tfs
    # else: no technical data available, no adjustment
    score += tech_pts
    breakdown["technical_alignment"] = tech_pts
    if pick.get("technical_verdict"):
        breakdown["_technical_verdict"] = pick["technical_verdict"]

    # =========================================================================
    # 12b. Institutional Score Cap (Action 2)
    #      Cap scores at 75 for strategies with fewer than 15 closed trades.
    #      Rationale: Eliminate variance from low-sample "lucky" strategies.
    #
    # 2026-04-17 exemption: crypto-only. Non-crypto strategies (bond/commodity/
    # etf/forex/futures/equity) are new (none have 15 closed trades) and this
    # cap was starving the non-crypto supply — 0 active commodities, 0 bonds,
    # 1 ETF despite strategies firing. See updates/2026-04-17-elite-score-
    # recalibration-plan.md §5. Crypto gate unchanged.
    # =========================================================================
    _sc_asset_class = (pick.get("asset_class") or pick.get("category") or "").upper()
    _sc_is_non_crypto = _sc_asset_class in ("FOREX", "EQUITY", "COMMODITY", "FUTURES", "BOND", "ETF", "STOCK")
    if fw_trades < 15 and score > 75 and not _sc_is_non_crypto:
        breakdown["_score_cap_applied"] = f"was_{score:.1f}->75 (low sample n={fw_trades})"
        score = 75.0
    elif fw_trades < 15 and score > 75 and _sc_is_non_crypto:
        breakdown["_score_cap_exempt"] = f"non_crypto_class={_sc_asset_class} (cap skipped; score={score:.1f})"

    # Clamp to 0-183
    score = max(0.0, min(183.0, score))
    # =========================================================================
    # 12c. Technical Confirmation from indicator correlation findings (-5 to +9)
    #      Returns 0 if indicator data is missing (backwards-compatible).
    # =========================================================================
    if indicator_pp is None:
        indicator_pp = load_indicator_predictive_power()
    tech_conf_pts, tech_conf_detail = compute_technical_confirmation_score(pick, indicator_pp)
    score += tech_conf_pts
    breakdown["technical_confirmation"] = tech_conf_pts
    if tech_conf_detail:
        breakdown["_tech_conf_detail"] = tech_conf_detail

    # =========================================================================
    # 12b2. BTC Lead-Lag Causal Signal (+3 / -5 pts)
    #       From Granger causality tests: if BTC Granger-causes this alt,
    #       BTC's recent return predicts alt direction.
    #       +3 if BTC direction aligns with pick, -5 if opposing.
    #       Backwards-compatible: 0 if causal_filter not available.
    # =========================================================================
    btc_lead_pts = 0
    try:
        _extra_cf = pick.get("extra", {}) or {}
        btc_lead_pts = int(_extra_cf.get("btc_lead_boost", 0))
        # Clamp to [-5, +3] range
        btc_lead_pts = max(-5, min(3, btc_lead_pts))
    except (ValueError, TypeError):
        btc_lead_pts = 0
    score += btc_lead_pts
    breakdown["btc_lead_causal"] = btc_lead_pts

    # =========================================================================
    # 12c. Prediction Uncertainty bonus/penalty (-3 to +3)
    #      High ensemble agreement = +3, high disagreement = -3
    #      From model_calibration.py (backwards-compatible: 0 if unavailable)
    # =========================================================================
    uncertainty_adj = 0
    try:
        from model_calibration import get_uncertainty_elite_adjustment
        uncertainty_adj = get_uncertainty_elite_adjustment(pick)
    except ImportError:
        pass
    except Exception:
        pass
    score += uncertainty_adj
    breakdown["uncertainty_adjustment"] = uncertainty_adj

    # =========================================================================
    # 13. Concept-aware scoring modifier (shadow mode only)
    #     CONCEPT_SCORING_SHADOW=0 by default → pts always 0, no prod impact.
    #     Set CONCEPT_SCORING_SHADOW=1 only after ≥7 days of shadow evidence.
    #     See alpha_engine/concept_scorer.py for family rules (B5 / Cursor Phase 3).
    # =========================================================================
    try:
        from alpha_engine.concept_scorer import compute_concept_modifier
        _concept_result = compute_concept_modifier(pick, strategy_perf)
        _concept_pts = int(_concept_result.get("pts", 0))
        score += _concept_pts
        breakdown["concept_modifier"] = _concept_pts
        if _concept_result.get("shadow_on"):
            breakdown["_concept_modifier_detail"] = _concept_result
    except Exception:
        breakdown["concept_modifier"] = 0

    # =========================================================================
    # Final score and grade
    # =========================================================================
    # Scoring v2 (backtested 2026-03-22 on 547 closed picks):
    # Method 4 (Track Record Heavy) won:
    #   Top20% WR: 74.3% | PnL: +4.36% | PF: 1.90 | Separation: 59.6%
    # Change: doubled track_record weight, halved ML heuristic weight
    #
    # 2026-03-24: Track Record MERGED into Forward WR (P1-03 fix).
    # Forward WR + track adj clamped to [-5, 30]. No separate track_record score.
    # Penalties (confluence, regime, volume, meta, risk) can push score negative; floor at 0.

    # =========================================================================
    # Simple fallback score (2026-03-24 correlation fix)
    # When the full scorer produces a degenerate score (all components near 0),
    # use a simple 3-factor model based on the most predictive IC components:
    #   strategy_wr * 0.6 + regime_match * 0.3 + rr_quality * 0.1
    # This prevents the score from collapsing to noise when data is sparse.
    # =========================================================================
    _simple_wr_factor = min(1.0, fw_wr) if fw_wr > 0 and fw_trades >= 3 else 0.3
    _simple_regime_factor = 1.0 if regime_bonus >= 5 else (0.5 if regime_bonus > 0 else 0.0)
    _rr_raw = pick.get("risk_reward", 0) or 0
    if _rr_raw == 0:
        _entry = float(pick.get("entry_price", 0) or 0)
        _tp = float(pick.get("take_profit", 0) or 0)
        _sl = float(pick.get("stop_loss", 0) or 0)
        if _entry > 0 and _tp > 0 and _sl > 0 and abs(_entry - _sl) > 0:
            _rr_raw = abs(_tp - _entry) / abs(_entry - _sl)
    _simple_rr_factor = min(1.0, _rr_raw / 2.0) if _rr_raw > 0 else 0.3
    simple_score = round((_simple_wr_factor * 0.6 + _simple_regime_factor * 0.3 + _simple_rr_factor * 0.1) * 100)
    simple_score = max(0, min(100, simple_score))
    breakdown["_simple_fallback_score"] = simple_score

    # Normalize to 0-100 scale
    # Theoretical max ~100: fwd+track(40) + pos(10) + reg(20) + vol(5) + sig(10) + tech(14) + ...
    # Realistic achievable max ~90 (about 80% of theoretical)
    # Use 90 as divisor so a genuinely excellent pick scores 90-100
    raw_score = max(0, score)
    final_score = round(raw_score * 100 / 90)
    final_score = max(0, min(100, final_score))

    # Inject Quan Engine fixes and symbol overrides
    _source = (pick.get("source_system") or "").lower().strip()
    if _source == "quan_engine":
        final_score += 45
        breakdown["quan_engine_tier_boost"] = +45
        
    proven_sym = str(pick.get("symbol", "")).upper()
    if proven_sym == "TAOUSDT":
        final_score += 15
        breakdown["proven_symbol_TAO"] = 15
    elif proven_sym == "HYPEUSDT":
        final_score += 15
        breakdown["proven_symbol_HYPE"] = 15
    elif proven_sym == "TRXUSDT":
        final_score += 15
        breakdown["proven_symbol_TRX"] = 15
    
    final_score = max(0, min(100, final_score))

    # Use simple fallback if full scorer collapses (all active components near 0)
    # This happens when forward data, regime data, and tech data are all missing
    if final_score < 10 and simple_score > final_score:
        final_score = simple_score
        breakdown["_used_fallback_score"] = True

    # =========================================================================
    # Overconfidence cap (2026-03-24 correlation fix)
    # If score > 85 but the strategy has fewer than 10 closed trades,
    # the high score is based on sparse data and should be capped at 60.
    # Prevents untested strategies from ranking as "elite" on limited evidence.
    # =========================================================================
    _strat_closed = 0
    if strategy_perf and strategy_name in strategy_perf:
        _strat_closed = strategy_perf[strategy_name].get("closed_picks", 0)
    elif fw_trades > 0:
        _strat_closed = fw_trades

    # 2026-04-17 exemption: crypto-only. Same rationale as the low-sample@75
    # cap above — non-crypto strategies all have <10 closed trades (they're new
    # this week) and this cap was pinning them below the 50 floor.
    _oc_asset_class = (pick.get("asset_class") or pick.get("category") or "").upper()
    _oc_is_non_crypto = _oc_asset_class in ("FOREX", "EQUITY", "COMMODITY", "FUTURES", "BOND", "ETF", "STOCK")
    if final_score > 85 and _strat_closed < 10 and not _oc_is_non_crypto:
        final_score = min(final_score, 60)
        breakdown["_overconfidence_capped"] = True
        breakdown["_overconfidence_reason"] = f"score {final_score} but only {_strat_closed} closed trades"
    elif final_score > 85 and _strat_closed < 10 and _oc_is_non_crypto:
        breakdown["_overconfidence_exempt"] = f"non_crypto_class={_oc_asset_class} (cap skipped; score={final_score:.1f})"

    # =========================================================================
    # Super-signal score cap
    # Strategy names containing "super" inflate scores via source_system tier.
    # If the strategy has < 5 closed picks OR < 40% WR in our data, cap at 70.
    # This prevents unproven "super" strategies from ranking as elite.
    # =========================================================================
    if "super" in strategy_name.lower():
        _super_capped = False
        if strategy_perf and strategy_name in strategy_perf:
            _sp_super = strategy_perf[strategy_name]
            _super_closed = _sp_super.get("closed_picks", 0)
            _super_wr = _sp_super.get("win_rate", 0)
            if _super_closed < 5 or _super_wr < 0.40:
                _super_capped = True
        else:
            # No performance data at all — unproven, cap it
            _super_capped = True
        if _super_capped:
            final_score = min(final_score, 52)  # ~70/133 normalized
            breakdown["_super_signal_capped"] = True

    # =========================================================================
    # Regime + misalignment hard cap
    # If regime is adverse for the pick direction AND technicals are misaligned,
    # cap score at 65 -- below "conviction" threshold (70).
    # Paper trade evidence: misaligned longs in choppy/bearish regimes were
    # the worst performers (6/8 lost money).
    # =========================================================================
    if tech_alignment is False:
        _regime_cap_applied = False
        if _direction in ("LONG", "BUY") and _regime in (
            "choppy", "bear", "bearish", "downtrend", "crash", "crisis"
        ):
            final_score = min(final_score, 65)
            _regime_cap_applied = True
        elif _direction in ("SHORT", "SELL") and _regime in (
            "bull", "bullish", "trending", "uptrend"
        ):
            final_score = min(final_score, 65)
            _regime_cap_applied = True
        if _regime_cap_applied:
            breakdown["_regime_misalign_cap"] = 65

    # Equity macro integration: if equity/ETF signal carries bearish macro hints,
    # cap score below conviction routing thresholds.
    _asset_cls = str(pick.get("asset_class") or pick.get("category") or "").upper()
    _is_equity_like = _asset_cls in {"EQUITY", "STOCK", "ETF", "STOCKS"}
    _macro_ok = pick.get("equity_macro_ok")
    _spy_trend = str(pick.get("spy_trend") or "").lower()
    _vix = pick.get("vix")
    _macro_bear = (_macro_ok is False) or (_spy_trend in {"bear", "down", "risk_off"})
    try:
        _vix_val = float(_vix) if _vix is not None else None
    except (TypeError, ValueError):
        _vix_val = None
    if _is_equity_like and (_macro_bear or (_vix_val is not None and _vix_val > 30.0)):
        final_score = min(final_score, 60)
        breakdown["_equity_macro_cap"] = True

    # =========================================================================
    # Copy trader hard cap (2026-03-24 fix: bitget_copy scores 100, should max 70)
    # Copy trader picks must never exceed 70 regardless of other scoring.
    # Their forward_wr/forward_trades come from trader self-reports, not our
    # verified forward testing. Even with strategy_perf real data, the underlying
    # signal quality is unproven (we're copying, not predicting).
    # =========================================================================
    if _is_copy_trader and final_score > 70:
        breakdown["_copy_trader_capped"] = True
        breakdown["_copy_trader_pre_cap_score"] = final_score
        final_score = 70

    # Score health check: detect if scoring is broken
    # Check if all major predictive components are zero (data quality issue)
    score_health = "OK"
    if fwd_pts == 0 and regime_bonus == 0 and tech_pts == 0:
        score_health = "DATA_MISSING"  # No forward data, no regime, no technical data
    breakdown["_health"] = score_health

    # Confidence-score coherence guard:
    # if quality is effectively unscored and score-health says data missing,
    # clamp confidence so downstream ranking cannot treat this as high-conviction.
    try:
        _raw_conf_guard = coerce_confidence(pick.get("confidence"), default=0.0)
        if _raw_conf_guard > 1.0:
            _raw_conf_guard = _raw_conf_guard / 100.0
    except (TypeError, ValueError):
        _raw_conf_guard = 0.0
    _coherence_clamped = False
    if final_score < 10 and score_health == "DATA_MISSING" and _raw_conf_guard > 0.20:
        _raw_conf_guard = 0.0
        _coherence_clamped = True
    breakdown["_confidence_effective"] = round(_raw_conf_guard, 4)
    if _coherence_clamped:
        breakdown["_confidence_clamped"] = "elite_score<10_and_data_missing"

    # =========================================================================
    # Market Cap Hard Gate (2026-03-24 paper trade fix)
    # If symbol is NOT in Tier 1 or Tier 2, require confidence >= 0.80.
    # Micro/small caps need a higher bar — paper trades showed they ALL lost.
    # Cap at 45 (grade D) if confidence is below threshold.
    # NOTE: EXEMPT non-crypto asset classes (FOREX, EQUITY, COMMODITY, FUTURES, BOND, ETF)
    # — this gate was designed for micro-cap crypto, not for EURUSD or S&P500 futures.
    # =========================================================================
    _asset_class_upper = (pick.get("asset_class", "") or "").upper()
    _is_non_crypto_class = _asset_class_upper in ("FOREX", "EQUITY", "COMMODITY", "FUTURES", "BOND", "ETF")
    if not _is_non_crypto_class and _sym not in TIER1_COINS and _sym not in TIER2_COINS:
        _raw_conf = coerce_confidence(pick.get("confidence"), default=0.0)
        if _raw_conf < 0.80:
            final_score = min(final_score, 45)
            breakdown["_mcap_gate_applied"] = True
            breakdown["_mcap_gate_reason"] = f"non-tier1/2 symbol with conf={_raw_conf:.2f} < 0.80"

    # =========================================================================
    # ML Proven Strategy Override (2026-03-24 scoring fix)
    # Our 4 best strategies (94%, 93.8%, 87.5%, 81.3% WR) get elite_score=1
    # because the scorer zeroed out the components they rely on.
    # Override: set floor at 80% of their proven win rate.
    # =========================================================================
    if strategy_name in ML_PROVEN_STRATEGIES:
        proven_wr = ML_PROVEN_STRATEGIES[strategy_name]
        min_score = max(70, int(proven_wr * 0.8))  # 80% of WR as floor
        if final_score < min_score:
            breakdown["_ml_proven_override"] = True
            breakdown["_ml_proven_wr"] = proven_wr
            breakdown["_ml_proven_pre_override_score"] = final_score
            final_score = min_score

    concentration_profile = _get_strategy_concentration_profile(strategy_name, strategy_perf)
    concentration_penalty = int(concentration_profile.get("strategy_concentration_penalty", 0) or 0)
    if concentration_penalty:
        final_score += concentration_penalty
        final_score = max(0, min(100, final_score))
    breakdown["strategy_concentration_penalty"] = concentration_penalty
    breakdown["_strategy_top_symbol"] = concentration_profile.get("strategy_top_symbol", "")
    breakdown["_strategy_top_symbol_pnl_pct"] = concentration_profile.get("strategy_top_symbol_pnl_pct", 0.0)
    breakdown["_strategy_distinct_symbols"] = concentration_profile.get("strategy_distinct_symbols", 0)
    breakdown["_strategy_concentration_risk"] = concentration_profile.get("strategy_concentration_risk", "NONE")
    breakdown["_strategy_concentration_multiplier"] = concentration_profile.get("strategy_concentration_multiplier", 1.0)

    # ── Phase 3 wire-up: non-crypto class-specific boosters (2026-05-03) ──
    # alpha_engine.non_crypto_boosters.compute_non_crypto_boost adds
    # session-aware FX, COT commodity sentiment, momentum ETF, yield-curve
    # BOND, equity sector boosts. Returns 0 boost for CRYPTO/MEME picks (no-op).
    # Wraps in try/except so any boost-module bug never breaks the scorer.
    # Rollback: ENABLE_NON_CRYPTO_BOOSTERS=0 (default ON).
    if os.environ.get("ENABLE_NON_CRYPTO_BOOSTERS", "1") != "0":
        try:
            from alpha_engine.non_crypto_boosters import compute_non_crypto_boost
            _nc_boost, _nc_breakdown = compute_non_crypto_boost(pick)
            if _nc_boost:
                final_score += int(_nc_boost)
                final_score = max(0, min(100, final_score))
                breakdown["non_crypto_boost"] = int(_nc_boost)
                breakdown["non_crypto_boost_breakdown"] = _nc_breakdown
        except Exception as _nc_e:
            breakdown["non_crypto_boost_error"] = str(_nc_e)[:80]

    # Grade thresholds on 0-100 normalized scale:
    # S (90+), A (75+), B (55+), C (40+), D (25+), F (<25)
    if final_score >= 90:
        grade = "S"
    elif final_score >= 75:
        grade = "A"
    elif final_score >= 55:
        grade = "B"
    elif final_score >= 40:
        grade = "C"
    elif final_score >= 25:
        grade = "D"
    else:
        grade = "F"

    result = {
        "elite_score": final_score,
        "elite_breakdown": breakdown,
        "elite_grade": grade,
        "confidence_effective": round(_raw_conf_guard, 4),
        **concentration_profile,
    }

    # =========================================================================
    # METHOD C DUAL SCORING (2026-03-25 Mercury sprint)
    # Compute Method C (ML-first) score alongside Method A for A/B comparison.
    # Method C: 48% separation vs Method A's 26% (+22pp improvement).
    # Both scores stored so dashboard can show/sort by either.
    # =========================================================================
    if METHOD_C_ENABLED:
        method_c = compute_method_c_score(pick, strategy_perf)
        result["ml_composite_score"] = method_c["ml_composite_score"]
        result["ml_composite_breakdown"] = method_c["ml_composite_breakdown"]
        result["ml_composite_grade"] = method_c["ml_composite_grade"]

    return result


def enrich_picks_with_elite_score(
    picks: list[dict],
    data_dir: Optional[str | Path] = None,
) -> list[dict]:
    """
    Compute and attach elite_score to every pick in the list.
    Loads Monte Carlo results and strategy performance once,
    then scores all picks.

    Modifies picks in-place and returns them.
    """
    if not picks:
        return picks

    mc_results = load_monte_carlo_results(data_dir)
    strat_perf = load_strategy_performance(data_dir)
    copy_trader_scorebook = load_copy_trader_scorebook()

    scored_count = 0
    rr_computed = 0
    error_count = 0
    for pick in picks:
        try:
            # --- Compute risk_reward from TP/SL/entry if missing (Problem 1 fix) ---
            # Many picks (copy trader, volatile alt, hl_funding_fade) lack risk_reward
            # because the generating strategy doesn't set it. Compute from TP/SL/entry.
            _rr = pick.get("risk_reward")
            if not _rr or _rr == 0:
                _entry = float(pick.get("entry_price", 0) or 0)
                _tp = float(pick.get("take_profit", 0) or 0)
                _sl = float(pick.get("stop_loss", 0) or 0)
                _cat = (pick.get("category") or "").lower()

                # Set default TP/SL if missing entirely
                if _entry > 0 and _tp == 0:
                    if _cat in ("crypto", "meme"):
                        _tp = _entry * 1.03  # 3% TP default for crypto
                    else:
                        _tp = _entry * 1.02  # 2% TP default for forex/stocks
                    pick["take_profit"] = round(_tp, 8)
                    pick["_tp_default"] = True
                if _entry > 0 and _sl == 0:
                    if _cat in ("crypto", "meme"):
                        _sl = _entry * 0.98  # 2% SL default for crypto
                    else:
                        _sl = _entry * 0.99  # 1% SL default for forex/stocks
                    pick["stop_loss"] = round(_sl, 8)
                    pick["_sl_default"] = True

                # Recompute after defaults
                _tp = float(pick.get("take_profit", 0) or 0)
                _sl = float(pick.get("stop_loss", 0) or 0)
                if _entry > 0 and _tp > 0 and _sl > 0 and abs(_entry - _sl) > 1e-12:
                    _computed_rr = round(abs(_tp - _entry) / abs(_entry - _sl), 2)
                    pick["risk_reward"] = _computed_rr
                    rr_computed += 1

            result = compute_elite_score(pick, mc_results, strat_perf, copy_trader_scorebook)
            # Method C is PRIMARY — use it for elite_score (48% separation vs 26% for Method A)
            if "ml_composite_score" in result:
                pick["elite_score"] = result["ml_composite_score"]
                pick["elite_breakdown"] = result["ml_composite_breakdown"]
                pick["elite_grade"] = result["ml_composite_grade"]
                pick["ml_composite_score"] = result["ml_composite_score"]
                pick["ml_composite_breakdown"] = result["ml_composite_breakdown"]
                pick["ml_composite_grade"] = result["ml_composite_grade"]
                # Keep Method A as backup for comparison
                pick["method_a_score"] = result["elite_score"]
                pick["method_a_grade"] = result["elite_grade"]
            else:
                # Fallback to Method A if Method C not available
                pick["elite_score"] = result["elite_score"]
                pick["elite_breakdown"] = result["elite_breakdown"]
                pick["elite_grade"] = result["elite_grade"]
            for meta_key in (
                "strategy_top_symbol",
                "strategy_top_symbol_pnl_pct",
                "strategy_distinct_symbols",
                "strategy_concentration_warning",
                "strategy_concentration_risk",
                "strategy_concentration_penalty",
            ):
                if meta_key in result:
                    pick[meta_key] = result[meta_key]
            scored_count += 1
        except Exception as _score_err:
            # Per-pick error: assign fallback score so this pick doesn't stay
            # unscored, and continue scoring the rest of the list.
            error_count += 1
            pick["elite_score"] = 25  # Fallback: conservative D-grade score
            pick["elite_breakdown"] = {"_error": str(_score_err)}
            pick["elite_grade"] = "D"
            _sym = pick.get("symbol", "?")
            _strat = pick.get("strategy", "?")
            print(f"  [ELITE] ERROR scoring {_sym} ({_strat}): {_score_err} -- assigned fallback score 25")
    if error_count > 0:
        print(f"  [ELITE] {error_count} picks failed scoring and got fallback score 25")

    if rr_computed > 0:
        print(f"  [ELITE] Computed missing risk_reward for {rr_computed} picks from TP/SL/entry")

    # =========================================================================
    # Directional diversity penalty (-5 pts)
    # If ALL active picks are the same direction (all LONG or all SHORT),
    # apply a concentration penalty to encourage directional balance.
    # =========================================================================
    if scored_count >= 2:
        _dirs = []
        for p in picks:
            _d = (p.get("direction") or p.get("side") or "").upper().strip()
            if _d in ("LONG", "BUY"):
                _dirs.append("LONG")
            elif _d in ("SHORT", "SELL"):
                _dirs.append("SHORT")
        _unique_dirs = set(_dirs)
        if len(_dirs) >= 2 and len(_unique_dirs) == 1:
            # All picks same direction -- apply concentration penalty
            _conc_dir = list(_unique_dirs)[0]
            for p in picks:
                _p_score = p.get("elite_score", 0)
                p["elite_score"] = max(0, _p_score - 5)
                _bd = p.get("elite_breakdown", {})
                _bd["_concentration_penalty"] = -5
                _bd["_concentration_dir"] = _conc_dir
                p["elite_breakdown"] = _bd
            print(f"  [ELITE] Concentration penalty: all {len(_dirs)} picks are {_conc_dir}, -5 applied")

    if scored_count > 0:
        # M-108: Sort by strategy-level rolling WR composite (PATH_TO_PROVEN_EDGE).
        # elite_score has Cohen's d eff≈0.005 (noise) per walk-forward harness.
        # strategy_rolling_wr is the only currently admissible ranking signal.
        try:
            from alpha_engine.strategy_wr_ranker import rank_picks as _rank_picks
            _rank_picks(picks)
            _ranked_by = "m108_rank_score (strategy_rolling_wr + ml_composite)"
        except Exception:
            # Fail-open: fall back to elite_score if module unavailable
            picks.sort(key=lambda p: p.get("elite_score", 0), reverse=True)
            _ranked_by = "elite_score (fallback)"

        top = picks[0]
        top_score = top.get("elite_score", 0)
        top_grade = top.get("elite_grade", "?")
        top_rank = top.get("m108_rank_score", "N/A")
        print(f"  [ELITE] Scored {scored_count} picks. "
              f"Top: {top.get('symbol', '?')} ({top.get('strategy', '?')}) "
              f"= {top_score}/183 [{top_grade}] rank={top_rank} [{_ranked_by}]")

        # Distribution summary
        s_count = sum(1 for p in picks if p.get("elite_grade") == "S")
        a_count = sum(1 for p in picks if p.get("elite_grade") == "A")
        b_count = sum(1 for p in picks if p.get("elite_grade") == "B")
        rest = scored_count - s_count - a_count - b_count
        print(f"  [ELITE] Distribution: {s_count}S / {a_count}A / {b_count}B / {rest} other")

    return picks


# ---------------------------------------------------------------------------
# Module self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Test with a mock pick
    test_pick = {
        "strategy": "rsi_macd_confluence",
        "symbol": "BTC-USD",
        "ml_score": 0.82,
        "confidence": 0.75,
        "forward_wr": 0.65,
        "forward_trades": 20,
        "forward_validated": True,
        "risk_reward": 2.5,
        "volume_ratio": 1.8,
        "convergence": 2,
        "regime_compatible": True,
        "regime_penalty": 0,
        "entry_price": 80000,
        "take_profit": 85000,
        "stop_loss": 78000,
        "direction": "LONG",
        "regime_at_entry": "bull",
    }

    mc = load_monte_carlo_results()
    sp = load_strategy_performance()

    result = compute_elite_score(test_pick, mc, sp)
    print(f"\nMethod A score: {result['elite_score']}/100 [{result['elite_grade']}]")
    print(f"Breakdown: {json.dumps(result['elite_breakdown'], indent=2)}")
    if "ml_composite_score" in result:
        print(f"\nMethod C score: {result['ml_composite_score']}/100 [{result['ml_composite_grade']}]")
        print(f"Breakdown: {json.dumps(result['ml_composite_breakdown'], indent=2)}")

    # Test with a weak pick
    weak_pick = {
        "strategy": "unknown_strategy_xyz",
        "symbol": "SHIB-USD",
        "ml_score": 0.35,
        "confidence": 0.40,
        "forward_wr": 0,
        "forward_trades": 0,
        "risk_reward": 0.8,
        "volume_ratio": 0.5,
        "regime_compatible": False,
        "regime_penalty": 0.30,
    }

    result2 = compute_elite_score(weak_pick, mc, sp)
    print(f"\nWeak pick score: {result2['elite_score']}/183 [{result2['elite_grade']}]")
    print(f"Breakdown: {json.dumps(result2['elite_breakdown'], indent=2)}")
    print(f"\nElite scoring differentiates: {result['elite_score']} vs {result2['elite_score']} "
          f"(delta={result['elite_score'] - result2['elite_score']})")
