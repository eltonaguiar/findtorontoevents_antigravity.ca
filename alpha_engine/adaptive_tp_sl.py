#!/usr/bin/env python3
"""
ALPHA ENGINE -- Adaptive TP/SL Optimizer (MFE/MAE-driven)
==========================================================
Uses actual Maximum Favorable Excursion (MFE) and Maximum Adverse Excursion
(MAE) data from closed picks to set optimal take-profit and stop-loss levels.

Problem: Static TP/SL produces R:R 2.0+ which has only 28.4% WR because TPs
are unreachable. R:R 1.0-1.5 has 52.5% WR (best). This module sets data-driven
TP/SL per-strategy and per-symbol instead of static percentages.

Algorithm:
  - TP = TP_PERCENTILE (default 60) of MFE for winning trades. Lowered from
    p75 in W1-T5 because winners reached p75 only ~25% of the time before
    reversing, decaying into TIME_EXIT. p60 is far more triggerable while
    still on the winner side of the distribution.
  - SL = SL_PERCENTILE (default 90) of MAE for losing trades.
  - If TP/SL ratio < 1.0, fall back to defaults (no edge)
  - Minimum 10 trades per bucket to compute adaptive levels
  - Per-symbol ATR normalization for volatility differences

Stdlib + json only -- no scipy/pandas. numpy allowed but not required.

Usage:
    from adaptive_tp_sl import get_optimal_tp_sl, refresh_adaptive_levels
    tp, sl = get_optimal_tp_sl("ema_crossover", "BTCUSDT", 87000.0)
    refresh_adaptive_levels()  # recompute from latest closed_picks.json
"""

from __future__ import annotations

import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from alpha_engine.tpsl_policy import TP_SL_POLICY, get_tpsl_policy

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_THIS_DIR = Path(__file__).resolve().parent
DATA_DIR = _THIS_DIR / "data"
CLOSED_PICKS_PATH = DATA_DIR / "closed_picks.json"
OUTPUT_PATH = DATA_DIR / "adaptive_tp_sl.json"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MIN_TRADES_STRATEGY = 10      # Minimum closed trades per strategy
MIN_TRADES_SYMBOL = 8         # Minimum closed trades per symbol
MIN_TP_SL_RATIO = 1.0         # If adaptive TP/SL < 1.0, no edge -- use defaults

# W1-T5 (Kimi audit 2026-04-25): drop TP target percentile from 75 -> 60.
# Rationale from the audit: at p75(winner_MFE) the price reaches the level
# only ~25% of the time before reversing, leaving the remaining winners to
# decay into TIME_EXIT. p60 is "median of the upper half" -- still on the
# winner side of the distribution but far more triggerable. Expected
# effect: TIME_EXIT share drops 3-5pp, mean R per pick stays >= 0.0.
# The diagnostic dump in _compute_strategy_levels still records the raw
# p75 stat for visibility (see `p75_winner_mfe_pct` field).
TP_PERCENTILE = 60.0
SL_PERCENTILE = 90.0          # Loser MAE percentile -- unchanged from prior

# Hard floors/caps (as fractions, e.g. 0.02 = 2%)
MIN_TP_PCT = 0.005            # 0.5% floor
MAX_TP_PCT = 0.15             # 15% cap
MIN_SL_PCT = 0.003            # 0.3% floor
MAX_SL_PCT = 0.10             # 10% cap

# Default TP/SL by asset class (fractions), derived from ATR-based policy.
DEFAULTS = {
    category: {
        "tp_pct": round(get_tpsl_policy(category)["tp_pct"], 6),
        "sl_pct": round(get_tpsl_policy(category)["sl_pct"], 6),
    }
    for category in TP_SL_POLICY
}

# Default ATR % by category (for normalization fallback)
DEFAULT_ATR_PCT = {
    category: float(policy["default_atr_pct"])
    for category, policy in TP_SL_POLICY.items()
}

# In-memory cache of adaptive levels (loaded from JSON or computed)
_CACHE: dict = {}
_CACHE_LOADED = False


# ---------------------------------------------------------------------------
# Math helpers (no numpy/scipy)
# ---------------------------------------------------------------------------

def _percentile(values: list, pct: float) -> float:
    """Compute pct-th percentile (0-100 scale) with linear interpolation."""
    if not values:
        return 0.0
    s = sorted(values)
    k = (pct / 100.0) * (len(s) - 1)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return s[int(k)]
    return s[f] * (c - k) + s[c] * (k - f)


def _median(values: list) -> float:
    return _percentile(values, 50.0)


def _mean(values: list) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _std(values: list) -> float:
    if len(values) < 2:
        return 0.0
    m = _mean(values)
    return math.sqrt(sum((v - m) ** 2 for v in values) / (len(values) - 1))


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _load_closed_picks() -> list:
    """Load closed picks with merge-conflict handling."""
    if not CLOSED_PICKS_PATH.exists():
        return []
    try:
        with open(CLOSED_PICKS_PATH, "r", encoding="utf-8", errors="replace") as f:
            raw = f.read()
        # Strip git merge conflict markers
        clean_lines = []
        in_theirs = False
        for line in raw.splitlines():
            stripped = line.strip()
            if stripped.startswith("<<<<<<"):
                continue
            if stripped.startswith("======"):
                in_theirs = True
                continue
            if stripped.startswith(">>>>>>"):
                in_theirs = False
                continue
            if in_theirs:
                continue
            clean_lines.append(line)
        cleaned = "\n".join(clean_lines)
        data = json.loads(cleaned)
        if isinstance(data, list):
            return [p for p in data if isinstance(p, dict)]
        return []
    except (json.JSONDecodeError, OSError) as e:
        print(f"  [ADAPTIVE_TP_SL] Warning: could not load closed_picks.json: {e}")
        return []


def _normalize_category(cat: str) -> str:
    """Normalize a category string to one of the known buckets.

    NOTE: an empty/unknown input is returned as an empty string rather than
    silently defaulting to "crypto". Callers that need a fallback must supply
    it explicitly (typically via _infer_asset_class_from_symbol). The old
    default-to-crypto behaviour caused forex/equity/commodity picks to be
    treated and tagged as crypto downstream (see PR #159 investigation).
    """
    cat = (cat or "").lower().strip()
    if not cat or cat in ("unknown", "none", "null"):
        return ""
    # Pass-through mapping — do NOT collapse non-crypto classes into crypto.
    # (Historical bug: "etf"/"bond"/"futures" were coerced to equity/commodity
    # which was fine here, but "onchain" was coerced to crypto which is still
    # correct because on-chain signals are always crypto assets.)
    mapping = {
        "onchain": "crypto",
        "on-chain": "crypto",
        "on_chain": "crypto",
        "stock": "equity",
        "stocks": "equity",
        "fx": "forex",
        "fiat": "forex",
        "metal": "commodity",
        "metals": "commodity",
        "energy": "commodity",
        "ag": "commodity",
        "future": "futures",
        "bond": "equity",
        "bonds": "equity",
    }
    return mapping.get(cat, cat)


# ---------------------------------------------------------------------------
# Asset-class inference from symbol
# ---------------------------------------------------------------------------
# Mirrors the rules used by tools/data_integrity/_common.classify_asset()
# (PR #145) extended to the full 6-class taxonomy. Inlined here rather than
# imported so this module stays self-contained and free of cross-package
# cycles. Covers: CRYPTO, FOREX, EQUITY, COMMODITY, FUTURES, ETF.

# Canonical class → category mapping (upper → lower)
_CLASS_TO_CATEGORY = {
    "CRYPTO": "crypto",
    "FOREX": "forex",
    "EQUITY": "equity",
    "COMMODITY": "commodity",
    "FUTURES": "futures",
    "ETF": "etf",
}

# Explicit ETF ticker set (top-traded US ETFs). Kept small and extensible.
_ETF_TICKERS = {
    "SPY", "QQQ", "IWM", "DIA", "VTI", "VOO", "VEA", "VWO", "EEM", "EFA",
    "XLF", "XLE", "XLK", "XLV", "XLI", "XLY", "XLP", "XLU", "XLB", "XLRE",
    "TLT", "IEF", "SHY", "LQD", "HYG", "AGG", "BND", "GLD", "SLV", "USO",
    "UNG", "ARKK", "ARKG", "ARKW", "SQQQ", "TQQQ", "UVXY", "VXX",
}

# Yahoo-style / Barchart-style futures suffix markers (=F and ! root codes)
# and common commodity futures root symbols.
_COMMODITY_ROOTS = {
    "GC", "SI", "HG", "PL", "PA",          # metals
    "CL", "BZ", "NG", "HO", "RB", "XRB",  # energy
    "ZC", "ZS", "ZW", "ZM", "ZL", "KC",    # grains / softs
    "CC", "CT", "SB", "OJ", "LE", "HE", "GF",  # softs / livestock
}
_EQUITY_INDEX_FUTURES_ROOTS = {
    "ES", "NQ", "YM", "RTY", "MES", "MNQ", "MYM", "M2K",
    "EMD", "VX",
}
_INTEREST_RATE_FUTURES_ROOTS = {
    "ZB", "ZN", "ZF", "ZT", "UB", "TN", "GE", "SR3", "SR1",
}

# Common major/minor FX pairs (6-char). USDT/USDC are crypto stables, not FX.
_FX_QUOTE_CCYS = {
    "USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD",
    "SEK", "NOK", "DKK", "SGD", "HKD", "MXN", "ZAR", "TRY",
    "PLN", "CZK", "HUF", "CNH",
}


def _infer_asset_class_from_symbol(symbol: str) -> str:
    """Infer asset class ("CRYPTO"/"FOREX"/"EQUITY"/"COMMODITY"/"FUTURES"/"ETF")
    from a raw symbol string. Returns "CRYPTO" only for real crypto patterns
    (quote in USDT/USDC/BUSD, or BTC/ETH base) — NOT as a silent catch-all.

    Unknown symbols fall through to "EQUITY" (the safest non-crypto default),
    because the ledgers' biggest historical data-quality problem was the
    opposite — everything being smeared to CRYPTO. An EQUITY misclassification
    is loud (wrong TP/SL scale, obvious in dashboards) whereas a CRYPTO
    misclassification was silent.
    """
    if not symbol:
        return "EQUITY"
    s = str(symbol).strip().upper()
    if not s:
        return "EQUITY"

    # --- Explicit ETF list (checked before equity) ---
    if s in _ETF_TICKERS:
        return "ETF"

    # --- Futures: Yahoo "=F" suffix or TradingView "!" suffix ---
    # Examples: GC=F, ES=F, CL1!, NQ1!, ESM2024
    if s.endswith("=F") or s.endswith("!"):
        root = s.split("=", 1)[0].rstrip("!")
        # Strip trailing digits / month codes (ES1, ESM24, CL202412)
        base = "".join(ch for ch in root if ch.isalpha())
        if base in _EQUITY_INDEX_FUTURES_ROOTS or base in _INTEREST_RATE_FUTURES_ROOTS:
            return "FUTURES"
        if base in _COMMODITY_ROOTS:
            return "COMMODITY"
        # Unknown futures root: treat as FUTURES (generic)
        return "FUTURES"

    # --- Crypto: stablecoin or major-base suffixes ---
    #   BTCUSDT, ETHUSDC, SOLBUSD, 1000PEPEUSDT, …
    for stable in ("USDT", "USDC", "BUSD", "TUSD", "DAI", "FDUSD"):
        if s.endswith(stable) and len(s) > len(stable):
            return "CRYPTO"
    # Bare BTC/ETH bases (e.g. "BTC", "ETH", "BTC/USD" normalised earlier)
    if s in ("BTC", "ETH", "SOL", "XRP", "ADA", "DOGE", "BNB", "LTC", "DOT"):
        return "CRYPTO"
    # Crypto "/" pairs like BTC/USDT
    if "/" in s:
        base, _, quote = s.partition("/")
        if quote in ("USDT", "USDC", "BUSD") or base in ("BTC", "ETH"):
            return "CRYPTO"
        if quote in _FX_QUOTE_CCYS and base in _FX_QUOTE_CCYS:
            return "FOREX"

    # --- Forex: 6-char ccy/ccy pair (EURUSD, GBPJPY, …) ---
    if len(s) == 6 and s[:3] in _FX_QUOTE_CCYS and s[3:] in _FX_QUOTE_CCYS:
        return "FOREX"
    # "EUR=X" Yahoo FX convention
    if s.endswith("=X") and len(s) >= 5:
        return "FOREX"

    # --- Equity (default non-crypto) ---
    return "EQUITY"


def _ensure_asset_class(pick: dict) -> tuple[str, str]:
    """Return (asset_class_upper, category_lower) for a pick, filling in the
    pick in place if either tag is missing/unknown. Honors existing tags.
    """
    ac_raw = pick.get("asset_class")
    ac = str(ac_raw).strip().upper() if ac_raw else ""
    if ac and ac != "UNKNOWN":
        cat = _normalize_category(pick.get("category") or "") or _CLASS_TO_CATEGORY.get(ac, "")
        if not cat:
            cat = ac.lower()
        # Backfill category if missing
        if not pick.get("category"):
            pick["category"] = cat
        return ac, cat

    # No (or UNKNOWN) asset_class — try category first, then symbol
    cat_norm = _normalize_category(pick.get("category") or "")
    if cat_norm:
        inv = {v: k for k, v in _CLASS_TO_CATEGORY.items()}
        ac = inv.get(cat_norm, cat_norm.upper())
    else:
        ac = _infer_asset_class_from_symbol(pick.get("symbol", ""))
        cat_norm = _CLASS_TO_CATEGORY.get(ac, ac.lower())

    pick["asset_class"] = ac
    pick["category"] = cat_norm
    return ac, cat_norm


def _infer_direction(pick: dict) -> str:
    d = (pick.get("direction") or "").upper()
    if d in ("LONG", "SHORT"):
        return d
    sig = (pick.get("signal_type") or "BUY").upper()
    return "SHORT" if sig == "SELL" else "LONG"


# ---------------------------------------------------------------------------
# MFE/MAE extraction per pick
# ---------------------------------------------------------------------------

def _extract_mfe_mae_pct(pick: dict) -> tuple:
    """
    Extract MFE and MAE as positive percentages (0-100 scale) from a closed pick.
    Returns (mfe_pct, mae_pct) or (None, None) if unusable.

    Priority:
      1. Explicit mfe_pct/mae_pct in extra_json
      2. Explicit mfe/mae fields on pick
      3. Derived from entry/exit/TP/SL/high_water_mark
      4. pnl_pct as last-resort proxy
    """
    entry = pick.get("entry_price", 0)
    if not entry or entry <= 0:
        return (None, None)

    direction = _infer_direction(pick)
    status = str(pick.get("status", "")).upper()
    exit_reason = str(pick.get("exit_reason", "")).upper()
    is_winner = status == "WON" or (pick.get("pnl_pct") or 0) > 0

    # --- Priority 1: extra_json fields ---
    extra = {}
    ej = pick.get("extra_json")
    if isinstance(ej, str):
        try:
            extra = json.loads(ej)
        except (json.JSONDecodeError, TypeError):
            pass
    elif isinstance(ej, dict):
        extra = ej

    for src in [extra, pick.get("extra") or {}, pick]:
        mfe_raw = src.get("mfe_pct") or src.get("mfe")
        mae_raw = src.get("mae_pct") or src.get("mae")
        if mfe_raw is not None and mae_raw is not None:
            try:
                mfe_v = abs(float(mfe_raw))
                mae_v = abs(float(mae_raw))
                # Convert to percentage if stored as fraction (< 1.0 likely fraction)
                if mfe_v < 1.0 and mfe_v > 0:
                    mfe_v *= 100.0
                if mae_v < 1.0 and mae_v > 0:
                    mae_v *= 100.0
                if mfe_v > 0 or mae_v > 0:
                    return (mfe_v, mae_v)
            except (TypeError, ValueError):
                pass

    # --- Priority 2: Derive from prices ---
    exit_price = pick.get("exit_price", 0)
    tp = pick.get("take_profit", 0)
    sl = pick.get("stop_loss", 0)
    hwm = pick.get("high_water_mark", 0)
    atr = pick.get("atr_at_entry", 0)
    hold_days = pick.get("hold_days", 0) or 0

    # ATR as pct for approximation
    if atr and atr > 0:
        atr_pct = (atr / entry) * 100.0
    else:
        norm_cat = _normalize_category(pick.get("category") or "")
        if not norm_cat:
            inferred = _infer_asset_class_from_symbol(pick.get("symbol", ""))
            norm_cat = _CLASS_TO_CATEGORY.get(inferred, "equity")
        atr_pct = DEFAULT_ATR_PCT.get(norm_cat, 3.0)

    if exit_price and exit_price > 0:
        realized_pct = abs(exit_price - entry) / entry * 100.0

        if is_winner:
            # MFE: at least the TP distance or realized gain
            if "TP" in exit_reason and tp and tp > 0:
                tp_dist_pct = abs(tp - entry) / entry * 100.0
                mfe_pct = max(tp_dist_pct, realized_pct)
            else:
                # Non-TP exit (trailing, time) -- MFE exceeded realized
                extra_move = atr_pct * max(hold_days, 0.5) * 0.2
                mfe_pct = realized_pct + extra_move

            # MAE for winners: small drawdown before recovery
            if hwm and hwm > 0 and hwm != entry:
                mae_pct = atr_pct * max(hold_days, 0.5) * 0.25
            else:
                mae_pct = atr_pct * max(hold_days, 0.5) * 0.3
            return (max(mfe_pct, 0.0), max(mae_pct, 0.0))

        else:
            # Loser: MAE >= SL distance or realized loss
            if "SL" in exit_reason and sl and sl > 0:
                sl_dist_pct = abs(sl - entry) / entry * 100.0
                mae_pct = max(sl_dist_pct, realized_pct)
            else:
                mae_pct = realized_pct

            # MFE for losers: some favorable move before reversal
            if hwm and hwm > 0 and abs(hwm - entry) > 0:
                mfe_pct = abs(hwm - entry) / entry * 100.0
            else:
                mfe_pct = atr_pct * max(hold_days, 0.5) * 0.2
            return (max(mfe_pct, 0.0), max(mae_pct, 0.0))

    # --- Priority 3: pnl_pct proxy ---
    pnl = pick.get("pnl_pct")
    if pnl is not None:
        pnl_f = abs(float(pnl)) * 100.0  # convert to pct
        if pnl_f > 0:
            if is_winner:
                return (pnl_f, pnl_f * 0.3)
            else:
                return (pnl_f * 0.2, pnl_f)

    return (None, None)


# ---------------------------------------------------------------------------
# Core computation: per-strategy and per-symbol optimal TP/SL
# ---------------------------------------------------------------------------

def _compute_strategy_levels(picks: list) -> dict:
    """
    Compute optimal TP/SL per strategy using MFE/MAE percentiles.

    TP = TP_PERCENTILE (default 60) of MFE for winning trades.
    SL = SL_PERCENTILE (default 90) of MAE for losing trades.
    """
    terminal = {"WON", "LOST", "CLOSED", "EXPIRED"}

    # Group by strategy
    by_strategy: dict = {}
    for p in picks:
        strat = p.get("strategy", "unknown")
        if str(p.get("status", "")).upper() not in terminal:
            continue
        by_strategy.setdefault(strat, []).append(p)

    results = {}
    for strat, strat_picks in by_strategy.items():
        if len(strat_picks) < MIN_TRADES_STRATEGY:
            continue

        winner_mfes = []
        winner_maes = []
        loser_maes = []
        loser_mfes = []
        all_mfes = []
        all_maes = []

        for p in strat_picks:
            mfe, mae = _extract_mfe_mae_pct(p)
            if mfe is None or mae is None:
                continue
            all_mfes.append(mfe)
            all_maes.append(mae)
            is_winner = str(p.get("status", "")).upper() == "WON" or (p.get("pnl_pct") or 0) > 0
            if is_winner:
                winner_mfes.append(mfe)
                winner_maes.append(mae)
            else:
                loser_maes.append(mae)
                loser_mfes.append(mfe)

        if len(all_mfes) < MIN_TRADES_STRATEGY:
            continue

        # TP = TP_PERCENTILE of winner MFE (where price actually goes before
        # reversing). W1-T5 lowered this from p75 to p60 -- see TP_PERCENTILE
        # docstring for rationale. Fallback to all-MFE when few winners.
        if len(winner_mfes) >= 5:
            optimal_tp_pct = _percentile(winner_mfes, TP_PERCENTILE) / 100.0
        else:
            optimal_tp_pct = _percentile(all_mfes, TP_PERCENTILE) / 100.0

        # SL = SL_PERCENTILE of loser MAE (how far price goes before stopping
        # out). Fallback to all-MAE when few losers.
        if len(loser_maes) >= 5:
            optimal_sl_pct = _percentile(loser_maes, SL_PERCENTILE) / 100.0
        else:
            optimal_sl_pct = _percentile(all_maes, SL_PERCENTILE) / 100.0

        # Clamp to floors/caps
        optimal_tp_pct = max(MIN_TP_PCT, min(optimal_tp_pct, MAX_TP_PCT))
        optimal_sl_pct = max(MIN_SL_PCT, min(optimal_sl_pct, MAX_SL_PCT))

        # Check if strategy has an edge (TP/SL ratio >= 1.0)
        tp_sl_ratio = optimal_tp_pct / optimal_sl_pct if optimal_sl_pct > 0 else 0.0
        has_edge = tp_sl_ratio >= MIN_TP_SL_RATIO

        # Win rate
        wins = sum(1 for p in strat_picks if str(p.get("status", "")).upper() == "WON"
                   or (p.get("pnl_pct") or 0) > 0)
        win_rate = wins / len(strat_picks) if strat_picks else 0.0

        # Category for this strategy (majority vote). When the pick has no
        # category, infer from its symbol rather than silently defaulting to
        # crypto (the historical bug — see PR fix/adaptive-tp-sl-asset-class).
        cats: list[str] = []
        for p in strat_picks:
            c = _normalize_category(p.get("category") or "")
            if not c:
                inferred = _infer_asset_class_from_symbol(p.get("symbol", ""))
                c = _CLASS_TO_CATEGORY.get(inferred, "equity")
            cats.append(c)
        category = max(set(cats), key=cats.count) if cats else "equity"

        results[strat] = {
            "optimal_tp_pct": round(optimal_tp_pct, 6),
            "optimal_sl_pct": round(optimal_sl_pct, 6),
            "tp_sl_ratio": round(tp_sl_ratio, 4),
            "has_edge": has_edge,
            "sample_size": len(all_mfes),
            "total_trades": len(strat_picks),
            "wins": wins,
            "win_rate": round(win_rate, 4),
            "category": category,
            "median_mfe_pct": round(_median(all_mfes), 4),
            "median_mae_pct": round(_median(all_maes), 4),
            "p75_winner_mfe_pct": round(_percentile(winner_mfes, 75.0), 4) if winner_mfes else None,
            "p90_loser_mae_pct": round(_percentile(loser_maes, 90.0), 4) if loser_maes else None,
            "edge_ratio": round(
                (_median(all_mfes) / _median(all_maes)) if _median(all_maes) > 0 else 0.0, 4
            ),
        }

    return results


def _compute_symbol_levels(picks: list) -> dict:
    """
    Compute per-symbol optimal TP/SL, ATR-normalized.

    Some symbols are far more volatile (micro-cap crypto vs EUR/USD),
    so per-symbol calibration captures this.
    """
    terminal = {"WON", "LOST", "CLOSED", "EXPIRED"}

    by_symbol: dict = {}
    for p in picks:
        sym = p.get("symbol", "UNKNOWN")
        if str(p.get("status", "")).upper() not in terminal:
            continue
        by_symbol.setdefault(sym, []).append(p)

    results = {}
    for sym, sym_picks in by_symbol.items():
        if len(sym_picks) < MIN_TRADES_SYMBOL:
            continue

        mfes = []
        maes = []
        atrs = []

        for p in sym_picks:
            mfe, mae = _extract_mfe_mae_pct(p)
            if mfe is not None and mae is not None:
                mfes.append(mfe)
                maes.append(mae)
            atr = p.get("atr_at_entry")
            entry = p.get("entry_price", 0)
            if atr and atr > 0 and entry and entry > 0:
                atrs.append((atr / entry) * 100.0)

        if len(mfes) < MIN_TRADES_SYMBOL:
            continue

        # Optimal levels (per-symbol). Same TP_PERCENTILE/SL_PERCENTILE as
        # _compute_strategy_levels -- single source of truth for the
        # winner-MFE / loser-MAE percentile choice.
        optimal_tp_pct = _percentile(mfes, TP_PERCENTILE) / 100.0
        optimal_sl_pct = _percentile(maes, SL_PERCENTILE) / 100.0

        optimal_tp_pct = max(MIN_TP_PCT, min(optimal_tp_pct, MAX_TP_PCT))
        optimal_sl_pct = max(MIN_SL_PCT, min(optimal_sl_pct, MAX_SL_PCT))

        tp_sl_ratio = optimal_tp_pct / optimal_sl_pct if optimal_sl_pct > 0 else 0.0

        category = _normalize_category(sym_picks[0].get("category") or "")
        if not category:
            inferred = _infer_asset_class_from_symbol(sym)
            category = _CLASS_TO_CATEGORY.get(inferred, "equity")
        avg_atr_pct = _mean(atrs) if atrs else DEFAULT_ATR_PCT.get(category, 3.0)

        results[sym] = {
            "optimal_tp_pct": round(optimal_tp_pct, 6),
            "optimal_sl_pct": round(optimal_sl_pct, 6),
            "tp_sl_ratio": round(tp_sl_ratio, 4),
            "sample_size": len(mfes),
            "category": category,
            "avg_atr_pct": round(avg_atr_pct, 4),
            "median_mfe_pct": round(_median(mfes), 4),
            "median_mae_pct": round(_median(maes), 4),
        }

    return results


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def refresh_adaptive_levels(closed_picks: Optional[list] = None) -> dict:
    """
    Recompute adaptive TP/SL from closed picks and save to JSON.

    Args:
        closed_picks: Pre-loaded list, or None to load from disk.

    Returns:
        Full analysis dict with per_strategy, per_symbol, and metadata.
    """
    global _CACHE, _CACHE_LOADED

    if closed_picks is None:
        closed_picks = _load_closed_picks()

    strategy_levels = _compute_strategy_levels(closed_picks)
    symbol_levels = _compute_symbol_levels(closed_picks)

    # Summary stats
    total_strategies = len(strategy_levels)
    strategies_with_edge = sum(1 for v in strategy_levels.values() if v["has_edge"])
    avg_tp = _mean([v["optimal_tp_pct"] for v in strategy_levels.values()]) if strategy_levels else 0.0
    avg_sl = _mean([v["optimal_sl_pct"] for v in strategy_levels.values()]) if strategy_levels else 0.0

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_closed_picks": len(closed_picks),
        "strategies_analyzed": total_strategies,
        "strategies_with_edge": strategies_with_edge,
        "symbols_analyzed": len(symbol_levels),
        "avg_optimal_tp_pct": round(avg_tp, 6),
        "avg_optimal_sl_pct": round(avg_sl, 6),
        "defaults": DEFAULTS,
        "per_strategy": strategy_levels,
        "per_symbol": symbol_levels,
    }

    # Save to disk
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, default=str)
        print(f"  [ADAPTIVE_TP_SL] Saved analysis to {OUTPUT_PATH.name}: "
              f"{total_strategies} strategies ({strategies_with_edge} with edge), "
              f"{len(symbol_levels)} symbols")
    except OSError as e:
        print(f"  [ADAPTIVE_TP_SL] Warning: could not save: {e}")

    _CACHE = result
    _CACHE_LOADED = True
    return result


def _ensure_cache() -> dict:
    """Load cache from disk if not yet loaded."""
    global _CACHE, _CACHE_LOADED
    if _CACHE_LOADED:
        return _CACHE

    # Try loading from saved JSON first (faster than recomputing)
    if OUTPUT_PATH.exists():
        try:
            with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
                _CACHE = json.load(f)
            _CACHE_LOADED = True
            return _CACHE
        except (json.JSONDecodeError, OSError):
            pass

    # Fall back to full recomputation
    return refresh_adaptive_levels()


def get_optimal_tp_sl(
    strategy: str,
    symbol: str,
    entry_price: float,
    category: str = "crypto",
    direction: str = "LONG",
) -> tuple:
    """
    Get optimal TP and SL prices for a new pick.

    Resolution order:
      1. Per-strategy level (if strategy has >= MIN_TRADES_STRATEGY and edge)
      2. Per-symbol level (if symbol has >= MIN_TRADES_SYMBOL)
      3. Asset-class defaults

    Args:
        strategy: Strategy name (e.g. "ema_crossover")
        symbol: Trading symbol (e.g. "BTCUSDT")
        entry_price: Entry price
        category: Asset category ("crypto", "forex", "equity", etc.)
        direction: "LONG" or "SHORT"

    Returns:
        (tp_price, sl_price) tuple
    """
    cache = _ensure_cache()
    # Never silently default an unknown category to crypto — fall back to
    # symbol-based inference instead (see PR fix/adaptive-tp-sl-asset-class).
    norm_cat = _normalize_category(category)
    if not norm_cat:
        inferred_class = _infer_asset_class_from_symbol(symbol)
        norm_cat = _CLASS_TO_CATEGORY.get(inferred_class, "equity")
    is_short = direction.upper() == "SHORT"

    tp_pct = None
    sl_pct = None
    source = "default"

    # 1. Per-strategy override
    strat_data = cache.get("per_strategy", {}).get(strategy)
    if strat_data and strat_data.get("has_edge") and strat_data.get("sample_size", 0) >= MIN_TRADES_STRATEGY:
        tp_pct = strat_data["optimal_tp_pct"]
        sl_pct = strat_data["optimal_sl_pct"]
        source = "strategy"

    # 2. Per-symbol override (blend with strategy if both available)
    sym_data = cache.get("per_symbol", {}).get(symbol)
    if sym_data and sym_data.get("sample_size", 0) >= MIN_TRADES_SYMBOL:
        sym_tp = sym_data["optimal_tp_pct"]
        sym_sl = sym_data["optimal_sl_pct"]

        if tp_pct is not None:
            # Blend: 60% strategy, 40% symbol (strategy is more specific)
            tp_pct = tp_pct * 0.6 + sym_tp * 0.4
            sl_pct = sl_pct * 0.6 + sym_sl * 0.4
            source = "strategy+symbol"
        else:
            tp_pct = sym_tp
            sl_pct = sym_sl
            source = "symbol"

    # 3. Defaults
    if tp_pct is None:
        defaults = get_tpsl_policy(norm_cat)
        tp_pct = defaults["tp_pct"]
        sl_pct = defaults["sl_pct"]
        source = "default"

    # Final clamp
    tp_pct = max(MIN_TP_PCT, min(tp_pct, MAX_TP_PCT))
    sl_pct = max(MIN_SL_PCT, min(sl_pct, MAX_SL_PCT))

    # Post-clamp R:R re-validation (Kimi audit 2026-04-25 finding #1).
    # Without this, the floor/cap clamp above can silently emit picks with
    # R:R as low as 0.05 (e.g. TP clamped to MIN_TP_PCT=0.005, SL clamped
    # to MAX_SL_PCT=0.10 -> R:R = 0.05). The pre-clamp `has_edge` check at
    # the per-strategy/symbol level (line ~521) is insufficient because
    # the floors/caps are applied AFTER it. Falling back to category
    # defaults preserves a sane R:R for the pick.
    _post_clamp_ratio = tp_pct / sl_pct if sl_pct > 0 else 0.0
    if _post_clamp_ratio < MIN_TP_SL_RATIO:
        defaults = get_tpsl_policy(norm_cat)
        tp_pct = max(MIN_TP_PCT, min(defaults["tp_pct"], MAX_TP_PCT))
        sl_pct = max(MIN_SL_PCT, min(defaults["sl_pct"], MAX_SL_PCT))
        source = f"{source}->default(post_clamp_rr={_post_clamp_ratio:.2f})"

    # Convert to prices
    if is_short:
        tp_price = round(entry_price * (1.0 - tp_pct), 8)
        sl_price = round(entry_price * (1.0 + sl_pct), 8)
    else:
        tp_price = round(entry_price * (1.0 + tp_pct), 8)
        sl_price = round(entry_price * (1.0 - sl_pct), 8)

    return (tp_price, sl_price)


def get_adaptive_info(strategy: str, symbol: str) -> dict:
    """
    Get diagnostic info about what adaptive levels would be used for a pick.
    Useful for logging/debugging.
    """
    cache = _ensure_cache()
    strat_data = cache.get("per_strategy", {}).get(strategy, {})
    sym_data = cache.get("per_symbol", {}).get(symbol, {})

    source = "default"
    if strat_data and strat_data.get("has_edge"):
        source = "strategy"
        if sym_data and sym_data.get("sample_size", 0) >= MIN_TRADES_SYMBOL:
            source = "strategy+symbol"
    elif sym_data and sym_data.get("sample_size", 0) >= MIN_TRADES_SYMBOL:
        source = "symbol"

    return {
        "source": source,
        "strategy_data": strat_data if strat_data else None,
        "symbol_data": sym_data if sym_data else None,
    }


def apply_adaptive_tp_sl(picks: list, closed_picks: Optional[list] = None) -> list:
    """
    Apply adaptive TP/SL to a list of active picks (in-place mutation).

    This is the main integration point for production_scanner.py.
    Call after picks are generated but before quality gates.

    Args:
        picks: List of pick dicts with entry_price, take_profit, stop_loss.
        closed_picks: Pre-loaded closed picks, or None to use cached/disk data.

    Returns:
        Same list (mutated in place) with updated take_profit/stop_loss.
    """
    if closed_picks is not None:
        refresh_adaptive_levels(closed_picks)
    else:
        _ensure_cache()

    adapted = 0
    for pick in picks:
        entry = pick.get("entry_price", 0)
        if not entry or entry <= 0:
            continue

        strategy = pick.get("strategy", "unknown")
        symbol = pick.get("symbol", "UNKNOWN")
        # Backfill asset_class / category on the pick from symbol inference
        # when missing. This is the load-bearing fix — previously this line
        # read `pick.get("category", "crypto")` which silently mis-tagged
        # every forex/equity/commodity pick as crypto and propagated the bad
        # tag into closed_picks.json / universal_resolved_picks.json.
        _asset_class, category = _ensure_asset_class(pick)
        direction = _infer_direction(pick)

        tp_price, sl_price = get_optimal_tp_sl(
            strategy=strategy,
            symbol=symbol,
            entry_price=entry,
            category=category,
            direction=direction,
        )

        info = get_adaptive_info(strategy, symbol)
        source = info["source"]

        # Only override if we have data-driven levels (not defaults)
        if source == "default":
            continue

        old_tp = pick.get("take_profit", 0) or 0
        old_sl = pick.get("stop_loss", 0) or 0

        pick["take_profit"] = tp_price
        pick["stop_loss"] = sl_price
        pick["_adaptive_tp_sl_source"] = source
        pick["_adaptive_tp_sl_old_tp"] = old_tp
        pick["_adaptive_tp_sl_old_sl"] = old_sl

        adapted += 1

    print(f"  [ADAPTIVE_TP_SL] Overrode TP/SL on {adapted}/{len(picks)} picks "
          f"(strategy/symbol data-driven)")

    return picks


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 70)
    print("ADAPTIVE TP/SL OPTIMIZER -- MFE/MAE-driven")
    print("=" * 70)

    picks = _load_closed_picks()
    print(f"Loaded {len(picks)} closed picks")

    result = refresh_adaptive_levels(picks)

    print(f"\nStrategies analyzed: {result['strategies_analyzed']}")
    print(f"Strategies with edge: {result['strategies_with_edge']}")
    print(f"Symbols analyzed: {result['symbols_analyzed']}")
    print(f"Avg optimal TP: {result['avg_optimal_tp_pct']*100:.2f}%")
    print(f"Avg optimal SL: {result['avg_optimal_sl_pct']*100:.2f}%")

    print("\n--- Per-Strategy Optimal Levels ---")
    for strat, data in sorted(result["per_strategy"].items(),
                               key=lambda x: x[1].get("win_rate", 0), reverse=True):
        edge_marker = "+" if data["has_edge"] else "-"
        print(f"  [{edge_marker}] {strat:40s} | "
              f"TP={data['optimal_tp_pct']*100:5.2f}% | "
              f"SL={data['optimal_sl_pct']*100:5.2f}% | "
              f"R:R={data['tp_sl_ratio']:4.2f} | "
              f"WR={data['win_rate']*100:5.1f}% | "
              f"n={data['sample_size']}")

    print("\n--- Per-Symbol Optimal Levels (top 20) ---")
    for sym, data in sorted(result["per_symbol"].items(),
                             key=lambda x: x[1].get("sample_size", 0), reverse=True)[:20]:
        print(f"  {sym:15s} | "
              f"TP={data['optimal_tp_pct']*100:5.2f}% | "
              f"SL={data['optimal_sl_pct']*100:5.2f}% | "
              f"R:R={data['tp_sl_ratio']:4.2f} | "
              f"ATR={data['avg_atr_pct']:5.2f}% | "
              f"n={data['sample_size']}")

    print(f"\nResults saved to: {OUTPUT_PATH}")
