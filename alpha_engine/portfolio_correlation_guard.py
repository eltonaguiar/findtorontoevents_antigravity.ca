#!/usr/bin/env python3
"""
Portfolio Correlation Guard
===========================
Blocks new picks that are too correlated with existing portfolio positions.

Prevents concentration risk: e.g. 5 simultaneous LONG picks on BTC-correlated
assets (BTC, ETH, SOL, AVAX, LINK) that all lose when BTC drops.

Uses predefined correlation groups + optional dynamic Pearson correlation
of daily returns. Stdlib-only (no pandas/numpy required).

Integration: call filter_picks_by_correlation() in scanner.py AFTER strategy
signals are generated but BEFORE open_new_picks().
"""

from __future__ import annotations

import math
from typing import Any


# ---------------------------------------------------------------------------
# 1. Compute return correlation between two symbols
# ---------------------------------------------------------------------------

def compute_return_correlation(
    symbol_a: str,
    symbol_b: str,
    ohlcv_cache: dict[str, list[float]],
    lookback: int = 30,
) -> float:
    """Compute Pearson correlation of daily returns over last `lookback` bars.

    Parameters
    ----------
    symbol_a, symbol_b : str
        Trading pair symbols (e.g. "BTCUSDT").
    ohlcv_cache : dict
        Mapping of symbol -> list of close prices (oldest first).
    lookback : int
        Number of return bars to use (default 30 -> needs 31 close prices).

    Returns
    -------
    float
        Pearson r in [-1, 1].  Returns 0.0 if data is insufficient or
        if standard deviation is zero (constant prices).
    """
    closes_a = ohlcv_cache.get(symbol_a)
    closes_b = ohlcv_cache.get(symbol_b)

    if not closes_a or not closes_b:
        return 0.0

    # Use last (lookback+1) prices to get `lookback` returns
    ca = closes_a[-(lookback + 1):]
    cb = closes_b[-(lookback + 1):]
    n = min(len(ca), len(cb))
    if n < 3:  # need at least 2 returns
        return 0.0

    # Daily log returns
    ret_a = []
    ret_b = []
    for i in range(1, n):
        if ca[i - 1] > 0 and cb[i - 1] > 0:
            ret_a.append(math.log(ca[i] / ca[i - 1]))
            ret_b.append(math.log(cb[i] / cb[i - 1]))

    if len(ret_a) < 2:
        return 0.0

    # Pearson correlation (stdlib only)
    m = len(ret_a)
    mean_a = sum(ret_a) / m
    mean_b = sum(ret_b) / m

    cov = 0.0
    var_a = 0.0
    var_b = 0.0
    for i in range(m):
        da = ret_a[i] - mean_a
        db = ret_b[i] - mean_b
        cov += da * db
        var_a += da * da
        var_b += db * db

    if var_a == 0.0 or var_b == 0.0:
        return 0.0

    r = cov / (math.sqrt(var_a) * math.sqrt(var_b))
    # Clamp to [-1, 1] for numerical safety
    return max(-1.0, min(1.0, r))


# ---------------------------------------------------------------------------
# 2. Predefined correlation groups
# ---------------------------------------------------------------------------

def get_correlation_groups() -> dict[str, list[str]]:
    """Return predefined correlation clusters.

    These are static groupings based on empirical beta/correlation to
    major assets.  Dynamic correlation (compute_return_correlation) can
    supplement these but the groups provide a fast O(1) lookup fallback
    when OHLCV data is unavailable.
    """
    return {
        # High-beta to BTC (>0.7 rolling 30d correlation)
        "BTC_GROUP": [
            "BTCUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT",
            "DOTUSDT", "LINKUSDT", "NEARUSDT",
        ],
        # DeFi blue-chips -- correlated to each other + ETH
        "ALT_DEFI": [
            "UNIUSDT", "AAVEUSDT", "MKRUSDT", "COMPUSDT", "SUSHIUSDT",
        ],
        # Meme tokens -- move together on social sentiment
        "MEME": [
            "DOGEUSDT", "SHIBUSDT", "PEPEUSDT", "FLOKIUSDT", "BONKUSDT",
        ],
        # Layer-2 scaling tokens
        "LAYER2": [
            "MATICUSDT", "ARBUSDT", "OPUSDT",
        ],
        # AI / compute narrative tokens
        "AI_COMPUTE": [
            "FETUSDT", "RENDERUSDT", "TAOUSDT", "AKTUSD",
        ],
        # Gaming / metaverse
        "GAMING": [
            "AXSUSDT", "SANDUSDT", "MANAUSDT", "IMXUSDT",
        ],
        # --- Forex: each major pair is its own group (low cross-corr) ---
        "FOREX_EURUSD": ["EURUSD=X"],
        "FOREX_GBPUSD": ["GBPUSD=X"],
        "FOREX_USDJPY": ["USDJPY=X"],
        "FOREX_AUDUSD": ["AUDUSD=X"],
        "FOREX_USDCAD": ["USDCAD=X"],
        "FOREX_USDCHF": ["USDCHF=X"],
        "FOREX_NZDUSD": ["NZDUSD=X"],
        "FOREX_EURGBP": ["EURGBP=X"],
        "FOREX_EURJPY": ["EURJPY=X"],
        "FOREX_GBPJPY": ["GBPJPY=X"],
        "FOREX_XAUUSD": ["XAUUSD", "GC=F"],
        # --- Equities: sector-based ---
        "EQUITY_TECH": ["AAPL", "NVDA", "MSFT", "GOOGL", "META", "AMZN", "TSM"],
        "EQUITY_HEALTH": ["LLY", "JNJ", "UNH", "PFE", "MRK", "ABBV"],
        "EQUITY_FINANCE": ["JPM", "BAC", "GS", "MS", "V", "MA"],
        "EQUITY_ENERGY": ["XOM", "CVX", "COP", "SLB"],
        "EQUITY_CONSUMER": ["WMT", "COST", "PG", "KO", "PEP"],
        "EQUITY_INDUSTRIAL": ["CAT", "DE", "HON", "UNP"],
    }


def _symbol_to_group(symbol: str, groups: dict[str, list[str]]) -> str | None:
    """Return the group name a symbol belongs to, or None."""
    for group_name, members in groups.items():
        if symbol in members:
            return group_name
    return None


# ---------------------------------------------------------------------------
# 3. Check correlation limit for a single pick
# ---------------------------------------------------------------------------

def check_correlation_limit(
    new_pick: dict[str, Any],
    active_picks: list[dict[str, Any]],
    max_per_group: int = 3,
    max_corr: float = 0.7,
    ohlcv_cache: dict[str, list[float]] | None = None,
) -> tuple[bool, str]:
    """Check whether adding *new_pick* would exceed correlation limits.

    Parameters
    ----------
    new_pick : dict
        Candidate pick with at least ``symbol`` key.
    active_picks : list[dict]
        Currently open positions.
    max_per_group : int
        Maximum concurrent positions in the same correlation group.
    max_corr : float
        Pearson correlation threshold for dynamic blocking.
    ohlcv_cache : dict | None
        Optional symbol -> close-prices list for dynamic correlation.

    Returns
    -------
    (allowed, reason) : tuple[bool, str]
    """
    symbol = new_pick.get("symbol", "")

    # --- Duplicate check: same symbol already open ---
    active_symbols = {p.get("symbol", "") for p in active_picks}
    if symbol in active_symbols:
        return False, f"Duplicate: {symbol} already has an open position"

    # --- Static group check ---
    groups = get_correlation_groups()
    new_group = _symbol_to_group(symbol, groups)

    if new_group is not None:
        group_count = sum(
            1 for p in active_picks
            if _symbol_to_group(p.get("symbol", ""), groups) == new_group
        )
        if group_count >= max_per_group:
            return (
                False,
                f"Group limit: {new_group} already has {group_count}/{max_per_group} positions",
            )

    # --- Dynamic correlation check (if OHLCV data available) ---
    if ohlcv_cache:
        for p in active_picks:
            p_sym = p.get("symbol", "")
            if p_sym == symbol:
                continue
            corr = compute_return_correlation(symbol, p_sym, ohlcv_cache)
            if abs(corr) >= max_corr:
                return (
                    False,
                    f"High correlation ({corr:.2f}) with active position {p_sym}",
                )

    return True, "OK"


# ---------------------------------------------------------------------------
# 4. Filter a batch of candidate picks
# ---------------------------------------------------------------------------

def filter_picks_by_correlation(
    candidate_picks: list[dict[str, Any]],
    active_picks: list[dict[str, Any]],
    max_per_group: int = 3,
    max_corr: float = 0.7,
    ohlcv_cache: dict[str, list[float]] | None = None,
) -> list[dict[str, Any]]:
    """Filter candidates through correlation guard.

    Higher-confidence picks are prioritised within each group: candidates
    are sorted by confidence descending so the best picks fill group slots
    first.

    Returns list of picks that passed the guard.
    """
    # Sort by confidence descending so best picks get group slots first
    sorted_candidates = sorted(
        candidate_picks,
        key=lambda p: float(p.get("confidence", 0) or 0),
        reverse=True,
    )

    passed: list[dict[str, Any]] = []
    # Build a running list that includes both existing active picks
    # and newly-accepted candidates (to enforce limits across the batch)
    effective_active = list(active_picks)

    for pick in sorted_candidates:
        allowed, reason = check_correlation_limit(
            pick, effective_active,
            max_per_group=max_per_group,
            max_corr=max_corr,
            ohlcv_cache=ohlcv_cache,
        )
        if allowed:
            passed.append(pick)
            effective_active.append(pick)

    # Restore original ordering among passed picks
    # (scanner expects signals in ranked order, not reshuffled)
    original_order = {id(p): i for i, p in enumerate(candidate_picks)}
    passed.sort(key=lambda p: original_order.get(id(p), float("inf")))

    return passed


# ---------------------------------------------------------------------------
# 5. Portfolio diversity score
# ---------------------------------------------------------------------------

def get_portfolio_diversity_score(
    active_picks: list[dict[str, Any]],
) -> tuple[float, dict[str, Any]]:
    """Compute a 0-100 diversity score for the current portfolio.

    Higher = more diversified across correlation groups.
    Penalises if >50% of positions are concentrated in a single group.

    Returns
    -------
    (score, breakdown) : tuple[float, dict]
        breakdown has keys: group_counts, total_groups, largest_group,
        concentration_pct, penalty_applied.
    """
    if not active_picks:
        return 100.0, {
            "group_counts": {},
            "total_groups": 0,
            "largest_group": None,
            "concentration_pct": 0.0,
            "penalty_applied": False,
        }

    groups = get_correlation_groups()
    group_counts: dict[str, int] = {}
    ungrouped = 0

    for pick in active_picks:
        sym = pick.get("symbol", "")
        grp = _symbol_to_group(sym, groups)
        if grp:
            group_counts[grp] = group_counts.get(grp, 0) + 1
        else:
            ungrouped += 1

    total_positions = len(active_picks)
    unique_groups = len(group_counts)
    # Ungrouped symbols each count as their own group for diversity
    effective_groups = unique_groups + ungrouped

    # Total possible groups (all defined groups)
    total_possible = len(groups)

    # Base score: what fraction of possible groups are represented
    if total_possible > 0:
        base_score = (effective_groups / total_possible) * 100.0
    else:
        base_score = 100.0

    # Cap at 100
    base_score = min(base_score, 100.0)

    # Concentration penalty: if any single group has >50% of positions
    largest_group = max(group_counts, key=group_counts.get) if group_counts else None
    largest_count = group_counts.get(largest_group, 0) if largest_group else 0
    concentration_pct = (largest_count / total_positions * 100.0) if total_positions > 0 else 0.0

    penalty_applied = False
    if concentration_pct > 50.0:
        # Penalty proportional to how far over 50% we are
        penalty = (concentration_pct - 50.0) * 0.8  # up to 40pt penalty at 100%
        base_score = max(0.0, base_score - penalty)
        penalty_applied = True

    return round(base_score, 1), {
        "group_counts": group_counts,
        "total_groups": effective_groups,
        "largest_group": largest_group,
        "concentration_pct": round(concentration_pct, 1),
        "penalty_applied": penalty_applied,
    }
