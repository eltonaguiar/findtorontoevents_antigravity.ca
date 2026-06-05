#!/usr/bin/env python3
"""
Crypto-specific risk and quality gates.

Applies funding rate, regime, concentration, staleness, and portfolio heat
checks to filter out bad picks before they enter the active portfolio.

Binance API failover per CLAUDE.md: api, api1, api2, api3 mirrors.
stdlib only -- uses urllib for HTTP.
"""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.request
import urllib.error
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# LOW_CONFIDENCE_STRATEGIES -- auto-detected from closed_picks.json analysis
# Strategies with 0% WR on 2+ closed trades, or known poor performers.
# These get an automatic 0.4x confidence multiplier.
# ---------------------------------------------------------------------------
LOW_CONFIDENCE_STRATEGIES: dict[str, str] = {
    # 0% WR on 10 closed picks
    "ml_enhanced_BTCUSDT_15m_D_ensemble_stack": "0% WR on 10 closed picks",
    "ml_enhanced_ADAUSDT_15m_D_ensemble_stack": "0% WR on 10 closed picks",
    # 0% WR on 5 closed picks
    "yahoo_analyst_consensus": "0% WR on 5 closed picks",
    # 0% WR on 3 closed picks
    "quality_value_composite": "0% WR on 3 closed picks",
    "cyclic_momentum_stack": "0% WR on 3 closed picks",
    # 0% WR on 2 closed picks
    "autocorrelation_exploiter": "0% WR on 2 closed picks",
    "markov_zone_transition": "0% WR on 2 closed picks",
    "swing_structure": "0% WR on 2 closed picks",
    "sr_breakout_retest": "0% WR on 2 closed picks",
    "fast_rsi2_extended": "0% WR on 2 closed picks",
    "futures_ema_stack_momentum": "0% WR on 2 closed picks",
    # 16% WR on 96 picks -- statistically confirmed poor performer
    "winner_pattern_precursor": "16% WR on 96 closed picks",
}

# ---------------------------------------------------------------------------
# HARD_KILL_STRATEGIES -- confirmed 0% or near-0% WR with enough sample size.
# These strategies are force-closed immediately and blocked from generating.
# ---------------------------------------------------------------------------
HARD_KILL_STRATEGIES: set = {
    "binance_smart_money",
    "yahoo_analyst_consensus",
    "winner_pattern_precursor",
    "ml_enhanced_BTCUSDT_15m_D_ensemble_stack",
    "ml_enhanced_ADAUSDT_15m_D_ensemble_stack",
    "futures_momentum",  # 0% WR on 4 trades — pure loser
    "forex_rsi2_mean_reversion",  # 0% WR on 2 trades — broken
}

# Funding rate cache: {symbol: (rate, timestamp)}
_funding_cache: dict[str, tuple[float, float]] = {}
_FUNDING_CACHE_TTL = 3600  # 1 hour


# ---------------------------------------------------------------------------
# Binance Futures API mirrors (per CLAUDE.md failover rule)
# ---------------------------------------------------------------------------
BINANCE_FAPI_MIRRORS = [
    "https://fapi.binance.com",
    "https://fapi1.binance.com",
    "https://fapi2.binance.com",
    "https://fapi3.binance.com",
]


def get_funding_rate(symbol: str) -> float | None:
    """Fetch latest funding rate from Binance Futures with mirror failover.

    Caches results for 1 hour per symbol.

    Args:
        symbol: Trading pair (e.g. 'BTCUSDT').

    Returns:
        Funding rate as float (e.g. 0.0001 = 0.01%), or None on failure.
    """
    now = time.time()

    # Check cache
    if symbol in _funding_cache:
        cached_rate, cached_ts = _funding_cache[symbol]
        if now - cached_ts < _FUNDING_CACHE_TTL:
            return cached_rate

    # Try each Binance mirror
    for mirror in BINANCE_FAPI_MIRRORS:
        url = f"{mirror}/fapi/v1/premiumIndex?symbol={symbol}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine/2.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                rate = float(data.get("lastFundingRate", 0))
                _funding_cache[symbol] = (rate, now)
                return rate
        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError,
                ValueError, KeyError, OSError):
            continue

    logger.warning("Failed to fetch funding rate for %s from all Binance mirrors", symbol)
    return None


def force_close_toxic_picks(active_picks_path=None, closed_picks_path=None):
    """Move all picks from HARD_KILL strategies to closed_picks.

    Sets exit_price = entry_price (flat close) to avoid phantom PnL.
    Returns number of force-closed picks.
    """
    data_dir = Path(__file__).resolve().parent / "data"
    if active_picks_path is None:
        active_picks_path = data_dir / "active_picks.json"
    else:
        active_picks_path = Path(active_picks_path)
    if closed_picks_path is None:
        closed_picks_path = data_dir / "closed_picks.json"
    else:
        closed_picks_path = Path(closed_picks_path)

    if not active_picks_path.exists():
        logger.info("No active_picks.json found -- nothing to force-close")
        return 0

    try:
        active_picks = json.loads(active_picks_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("Failed to load active_picks.json: %s", exc)
        return 0

    toxic_picks = []
    clean_picks = []
    for pick in active_picks:
        if pick.get("strategy", "") in HARD_KILL_STRATEGIES:
            toxic_picks.append(pick)
        else:
            clean_picks.append(pick)

    if not toxic_picks:
        logger.info("No toxic picks found in active_picks.json")
        return 0

    now_str = datetime.now(timezone.utc).isoformat()
    for pick in toxic_picks:
        pick["exit_price"] = pick.get("entry_price", 0)
        pick["exit_date"] = now_str
        pick["closed_at"] = now_str  # Required for dashboard export
        pick["exit_reason"] = "FORCE_CLOSED_TOXIC"
        pick["pnl_pct"] = 0.0
        pick["pnl_dollar"] = 0.0
        pick["status"] = "CLOSED"
        # 2026-06-04 (INCIDENT #95): admin force-close of a killed strategy's open
        # pick at break-even — NOT a real trade outcome. Stamp an explicit canonical
        # flag so every WR/PF aggregator can exclude it (dashboard already filters by
        # exit_reason per PR #521; money_ready_verdict excludes via the WON/LOST
        # status gate). Prevents these flat rows being miscounted as losses.
        pick["_wr_excluded"] = True
        pick["_wr_excluded_reason"] = "force_closed_toxic_admin"

    closed_picks = []
    if closed_picks_path.exists():
        try:
            closed_picks = json.loads(closed_picks_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            closed_picks = []

    closed_picks.extend(toxic_picks)

    active_picks_path.write_text(
        json.dumps(clean_picks, indent=2, default=str), encoding="utf-8"
    )
    closed_picks_path.write_text(
        json.dumps(closed_picks, indent=2, default=str), encoding="utf-8"
    )

    strategy_counts = Counter(p.get("strategy", "unknown") for p in toxic_picks)
    for strat, count in strategy_counts.most_common():
        logger.warning("FORCE_CLOSED %d picks from toxic strategy: %s", count, strat)
        print("  [FORCE_CLOSE] %d picks closed from %s" % (count, strat))

    total = len(toxic_picks)
    print("  [FORCE_CLOSE] Total: %d toxic picks force-closed, "
          "%d clean picks remain" % (total, len(clean_picks)))
    return total


def apply_crypto_gates(
    pick: dict,
    regime_data: dict | None = None,
    funding_data: dict | None = None,
    active_picks: list[dict] | None = None,
    strategy_stats: dict | None = None,
) -> dict | None:
    """Apply crypto-specific risk gates to a pick.

    Returns the modified pick (possibly with reduced confidence) or None if blocked.

    Gates applied in order:
    1. Funding rate gate (overleveraged crowd)
    2. Unknown regime + low confidence gate
    3. Low-confidence strategy penalty (< 10 closed trades)
    4. Counter-regime penalty
    5. High-confidence boost (good WR + regime-aligned)
    6. Over-concentration gate (> 3 active picks per symbol)
    7. LOW_CONFIDENCE_STRATEGIES penalty

    Args:
        pick: Signal dict with strategy, symbol, signal_type, confidence, category.
        regime_data: Dict with 'regime' key (e.g. 'bull', 'bear', 'unknown').
        funding_data: Dict with 'funding_rate' key, or None to auto-fetch.
        active_picks: List of currently active pick dicts.
        strategy_stats: Dict with 'closed_count', 'win_rate' per strategy.

    Returns:
        Modified pick dict, or None if blocked.
    """
    if not pick:
        return None

    # Only apply to crypto picks
    category = pick.get("category", "stock")
    if category not in ("crypto", "meme"):
        return pick

    symbol = pick.get("symbol", "")
    direction = pick.get("signal_type", "BUY").upper()
    confidence = pick.get("confidence", 0.5)
    strategy = pick.get("strategy", "")
    regime = (regime_data or {}).get("regime", "neutral")
    gate_notes = []

    # --- Gate 0: Extreme Fear + low-confidence LONG block ---
    # When FGI < 20 and direction is LONG with confidence < 0.65, block.
    # Prevents low-conviction LONGs during extreme fear regimes.
    _fgi_value = (regime_data or {}).get("fgi", None)
    if _fgi_value is None:
        _fg_cache_path = Path(__file__).resolve().parent / "data" / "feargreed_cache.json"
        try:
            if _fg_cache_path.exists():
                _fg_raw = json.loads(_fg_cache_path.read_text(encoding="utf-8"))
                _fgi_value = int(_fg_raw.get("current", 50))
            else:
                _fgi_value = 50
        except Exception:
            _fgi_value = 50

    if _fgi_value < 20 and direction == "BUY" and confidence < 0.65:
        logger.info(
            "BLOCKED %s %s: FGI=%d (Extreme Fear) + confidence %.2f < 0.65 "
            "(low-conviction LONG)",
            strategy, symbol, _fgi_value, confidence,
        )
        return None

    # --- Gate 1: Funding rate ---
    funding_rate = None
    if funding_data and "funding_rate" in funding_data:
        funding_rate = funding_data["funding_rate"]
    else:
        funding_rate = get_funding_rate(symbol)

    if funding_rate is not None:
        # 0.0001 = 0.01%
        if funding_rate > 0.0001 and direction == "BUY":
            logger.info("BLOCKED %s %s: funding rate %.4f%% > 0.01%% (overleveraged longs)",
                        strategy, symbol, funding_rate * 100)
            return None
        if funding_rate < -0.0001 and direction == "SELL":
            logger.info("BLOCKED %s %s: funding rate %.4f%% < -0.01%% (overleveraged shorts)",
                        strategy, symbol, funding_rate * 100)
            return None

    # --- Gate 2: Unknown regime + low confidence ---
    if regime.lower() in ("unknown", "") and confidence < 0.6:
        logger.info("BLOCKED %s %s: unknown regime + confidence %.2f < 0.6",
                     strategy, symbol, confidence)
        return None

    # --- Gate 3: Low trade count penalty ---
    stats = (strategy_stats or {}).get(strategy, {})
    closed_count = stats.get("closed_count", 0)
    win_rate = stats.get("win_rate", 0.0)

    if closed_count < 10:
        confidence *= 0.4
        gate_notes.append(f"low_trade_count ({closed_count} closed, conf *0.4)")

    # --- Gate 4: Counter-regime penalty ---
    is_counter_regime = False
    if regime.lower() in ("bear", "bearish") and direction == "BUY":
        is_counter_regime = True
    elif regime.lower() in ("bull", "bullish") and direction == "SELL":
        is_counter_regime = True

    if is_counter_regime:
        confidence *= 0.5
        gate_notes.append(f"counter_regime ({direction} in {regime}, conf *0.5)")

    # --- Gate 5: High-confidence boost ---
    if (closed_count >= 20 and win_rate > 0.55
            and not is_counter_regime):
        confidence *= 1.2
        gate_notes.append(f"high_conf_boost (WR {win_rate:.0%} on {closed_count} trades, conf *1.2)")

    # --- Gate 6: Over-concentration ---
    if active_picks:
        symbol_count = sum(1 for p in active_picks if p.get("symbol") == symbol)
        if symbol_count > 3:
            logger.info("BLOCKED %s %s: %d active picks on symbol (max 3)",
                         strategy, symbol, symbol_count)
            return None

    # --- Gate 7: LOW_CONFIDENCE_STRATEGIES penalty ---
    if strategy in LOW_CONFIDENCE_STRATEGIES:
        confidence *= 0.4
        reason = LOW_CONFIDENCE_STRATEGIES[strategy]
        gate_notes.append(f"low_conf_strategy ({reason}, conf *0.4)")

    # Also check dynamic low-confidence: any strategy with <5 closed and WR <30%
    if closed_count > 0 and closed_count < 5 and win_rate < 0.30:
        if strategy not in LOW_CONFIDENCE_STRATEGIES:
            confidence *= 0.4
            gate_notes.append(f"dynamic_low_conf ({closed_count} picks, {win_rate:.0%} WR, conf *0.4)")

    # Cap confidence at [0.01, 1.0]
    confidence = max(0.01, min(1.0, confidence))

    pick["confidence"] = round(confidence, 4)
    if gate_notes:
        pick["crypto_gate_notes"] = gate_notes
    pick["crypto_gates_applied"] = True

    # Network snapshot for fundamental_macro_gates / money_ready HC scoring
    _extra = pick.setdefault("extra", {})
    if not isinstance(_extra, dict):
        _extra = {}
        pick["extra"] = _extra
    _onchain_path = Path(__file__).resolve().parent / "genome" / "data" / "onchain_cache.json"
    if _onchain_path.exists():
        try:
            _oc = json.loads(_onchain_path.read_text(encoding="utf-8"))
            _sym_key = symbol.replace("=X", "").upper()
            _extra.setdefault("network_metrics", {})
            _extra["network_metrics"].update(
                {
                    "funding_rate": funding_rate,
                    "fear_greed": _oc.get("fear_greed") or _fgi_value,
                    "ssr": _oc.get("ssr"),
                    "btc_dominance": _oc.get("btc_dominance"),
                    "funding_rate_symbol": _oc.get(f"funding_rate_{_sym_key}"),
                }
            )
        except Exception:
            pass
    if funding_rate is not None:
        pick["funding_rate"] = funding_rate

    return pick


def check_pick_staleness(pick: dict) -> bool:
    """Check if a pick's entry price is stale (> 2% away from current price).

    Args:
        pick: Pick dict with 'symbol' and 'entry_price'.

    Returns:
        True if entry price is stale (> 2% deviation from current price).
    """
    symbol = pick.get("symbol", "")
    entry_price = pick.get("entry_price", 0)

    if not symbol or not entry_price:
        return False

    # Fetch current price from Binance with failover
    current_price = _fetch_current_price(symbol)
    if current_price is None or current_price <= 0:
        return False  # Can't determine staleness without price

    deviation = abs(current_price - entry_price) / entry_price
    return deviation > 0.02


def _fetch_current_price(symbol: str) -> float | None:
    """Fetch current price from Binance API with mirror failover."""
    mirrors = [
        "https://api.binance.com",
        "https://api1.binance.com",
        "https://api2.binance.com",
        "https://api3.binance.com",
    ]
    for mirror in mirrors:
        url = f"{mirror}/api/v3/ticker/price?symbol={symbol}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine/2.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                return float(data.get("price", 0))
        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError,
                ValueError, KeyError, OSError):
            continue
    return None


def compute_portfolio_heat(active_picks: list[dict]) -> float:
    """Compute portfolio heat as sum of all position risk.

    Heat = sum of (entry-to-SL distance as %) for each active pick.
    If heat > 15%, new picks should be blocked until existing ones resolve.

    Args:
        active_picks: List of active pick dicts with 'entry_price' and 'stop_loss'.

    Returns:
        Portfolio heat as a percentage (e.g. 12.5 means 12.5%).
    """
    if not active_picks:
        return 0.0

    total_heat = 0.0
    for pick in active_picks:
        entry = pick.get("entry_price", 0)
        sl = pick.get("stop_loss", 0)
        if entry and sl and entry > 0:
            risk_pct = abs(entry - sl) / entry * 100
            total_heat += risk_pct

    return round(total_heat, 2)


def is_portfolio_overheated(active_picks: list[dict], max_heat: float = 15.0) -> bool:
    """Check if portfolio heat exceeds the maximum threshold.

    Args:
        active_picks: List of active pick dicts.
        max_heat: Maximum allowed heat percentage (default 15%).

    Returns:
        True if portfolio heat exceeds max_heat.
    """
    heat = compute_portfolio_heat(active_picks)
    if heat > max_heat:
        logger.warning("Portfolio heat %.1f%% exceeds max %.1f%% -- blocking new picks",
                        heat, max_heat)
        return True
    return False


def build_low_confidence_from_closed(closed_picks: list[dict],
                                      min_trades: int = 2,
                                      max_wr: float = 0.0) -> dict[str, tuple[float, str]]:
    """Dynamically build LOW_CONFIDENCE_STRATEGIES from closed picks data.

    Identifies strategies with poor WR and at least ``min_trades`` closed picks.
    Strategies with 10+ trades and <25% WR get a 0.0 multiplier (hard kill).
    Others get a 0.4 multiplier (soft penalty).

    Args:
        closed_picks: List of closed pick dicts with 'strategy' and 'status'.
        min_trades: Minimum closed trades to consider (default 2).
        max_wr: Maximum win rate to flag (default 0.0 = only 0% WR).

    Returns:
        Dict mapping strategy name to (multiplier, reason) tuple.
    """
    from collections import defaultdict
    stats: dict[str, dict[str, int]] = defaultdict(lambda: {"won": 0, "total": 0})

    for pick in closed_picks:
        strategy = pick.get("strategy", "")
        if not strategy:
            continue
        stats[strategy]["total"] += 1
        if pick.get("status") == "WON":
            stats[strategy]["won"] += 1

    result: dict[str, tuple[float, str]] = {}
    for name, st in stats.items():
        if st["total"] >= min_trades:
            wr = st["won"] / st["total"]
            if wr <= max_wr:
                reason = f"{wr:.0%} WR on {st['total']} closed picks"
                # Hard kill if enough sample size confirms no edge
                multiplier = 0.0 if st["total"] >= 10 and wr < 0.25 else 0.4
                result[name] = (multiplier, reason)

    return result
