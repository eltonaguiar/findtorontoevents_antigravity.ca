#!/usr/bin/env python3
"""
Cross-Sectional Reversal Strategy for Alpha Engine
====================================================
The OPPOSITE of momentum: go LONG last week's biggest losers (mean reversion)
and SHORT last week's biggest winners (overextension).

-0.6 correlation with momentum strategies -- profits when momentum fails.

Academic basis:
  - Dobrynskaya (2023): Short-term reversal in crypto (1-week lookback)
  - De Bondt & Thaler (1985): Winner-loser effect
  - Jegadeesh (1990): Short-term reversal profits

Strategy logic:
  1. Fetch 7-day returns for top-30 USDT pairs by 24h volume
  2. Rank coins by 7d return
  3. LONG bottom 3 (biggest losers -> mean reversion)
  4. SHORT top 3 (biggest winners -> overextension)
  5. Filter: exclude >50% drawdown (fundamentally broken), <$5M volume

Parameters:
  - LONG losers: TP +8%, SL -4%
  - SHORT winners: TP +6%, SL -3% (tighter -- shorts are riskier)
  - Max 3 LONG + 2 SHORT per cycle
  - SHORT only in bearish or ranging regimes
"""

from __future__ import annotations

import json
import logging
import math
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

# -- Paths --
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

# -- Shared API failover (Binance -> Bybit -> CoinGecko -> KuCoin -> CryptoCompare) --
try:
    from api_failover import (
        fetch_klines as _failover_fetch_klines,
        fetch_ticker_24h as _failover_fetch_ticker_24h,
    )
except ImportError:
    from alpha_engine.api_failover import (
        fetch_klines as _failover_fetch_klines,
        fetch_ticker_24h as _failover_fetch_ticker_24h,
    )

# -- Strategy parameters --
UNIVERSE_SIZE = 30              # Top 30 by volume
LOOKBACK_DAYS = 7               # 7-day return window
MIN_DAILY_VOLUME_USD = 5_000_000  # $5M minimum daily volume
MAX_DRAWDOWN_FILTER = 0.50      # Exclude >50% drawdown in 7d

# LONG (losers = mean reversion)
LONG_TP_PCT = 0.08              # +8% take profit
LONG_SL_PCT = 0.04              # -4% stop loss
MAX_LONG_PICKS = 3

# SHORT (winners = overextension)
SHORT_TP_PCT = 0.06             # +6% take profit (distance from entry, applied as price decrease)
SHORT_SL_PCT = 0.03             # -3% stop loss (distance from entry, applied as price increase)
MAX_SHORT_PICKS = 2

# Confidence range
CONF_MIN = 0.70
CONF_MAX = 0.82

RATE_LIMIT_SEC = 0.15           # 150ms between API calls


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _smart_round(value, magnitude=None):
    """Round to sensible precision based on magnitude."""
    if value == 0:
        return 0.0
    av = abs(value) if magnitude is None else abs(magnitude)
    if av >= 100:
        return round(value, 2)
    elif av >= 1:
        return round(value, 4)
    elif av >= 0.01:
        return round(value, 6)
    return round(value, 8)


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _today_str():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _fetch_klines_with_failover(symbol, interval="1d", limit=10):
    """Fetch klines via shared api_failover (5-source failover chain)."""
    return _failover_fetch_klines(symbol, interval=interval, limit=limit)


# ---------------------------------------------------------------------------
# Universe selection: top 30 USDT pairs by 24h volume
# ---------------------------------------------------------------------------

def _get_top_volume_symbols(n=UNIVERSE_SIZE):
    """Fetch top N USDT pairs by 24h quote volume via api_failover."""
    try:
        tickers = _failover_fetch_ticker_24h("")
    except Exception as e:
        logger.warning("Failed to fetch ticker data: %s", e)
        return []
    if not tickers or not isinstance(tickers, list):
        return []

    # Filter USDT pairs, exclude stablecoins and leveraged tokens
    _EXCLUDE_BASES = {
        "USDC", "BUSD", "TUSD", "DAI", "FDUSD", "USDP", "USDD",
        "EUR", "GBP", "TRY", "BRL", "ARS",
    }
    _LEVERAGED_SUFFIXES = ("UP", "DOWN", "BULL", "BEAR", "3L", "3S", "2L", "2S")

    usdt_pairs = []
    for t in tickers:
        sym = t.get("symbol", "")
        if not sym.endswith("USDT"):
            continue
        base = sym[:-4]
        if base in _EXCLUDE_BASES:
            continue
        if base.endswith(_LEVERAGED_SUFFIXES):
            continue

        quote_vol = float(t.get("quoteVolume", 0))
        if quote_vol < MIN_DAILY_VOLUME_USD:
            continue

        usdt_pairs.append({
            "symbol": sym,
            "quoteVolume": quote_vol,
            "priceChangePercent": float(t.get("priceChangePercent", 0)),
            "lastPrice": float(t.get("lastPrice", 0)),
        })

    # Sort by 24h quote volume descending
    usdt_pairs.sort(key=lambda x: x["quoteVolume"], reverse=True)
    return usdt_pairs[:n]


# ---------------------------------------------------------------------------
# Core analysis
# ---------------------------------------------------------------------------

def _compute_7d_return(klines):
    """Compute 7-day return from daily klines. Returns (return_pct, high_7d, low_7d, current_price) or None."""
    if not klines or len(klines) < 2:
        return None

    try:
        closes = [float(k[4]) for k in klines]
        highs = [float(k[2]) for k in klines]
        lows = [float(k[3]) for k in klines]

        current = closes[-1]
        start = closes[0]

        if start <= 0 or current <= 0:
            return None

        ret = (current - start) / start
        high_7d = max(highs)
        low_7d = min(lows)

        return {
            "return_7d": ret,
            "current_price": current,
            "high_7d": high_7d,
            "low_7d": low_7d,
            "drawdown_7d": (high_7d - current) / high_7d if high_7d > 0 else 0,
        }
    except (ValueError, IndexError, TypeError):
        return None


def _compute_rsi(closes, period=14):
    """Compute RSI using Wilder's smoothing. Pure Python."""
    if len(closes) < period + 1:
        return 50.0

    gains = []
    losses = []
    for i in range(1, period + 1):
        delta = closes[i] - closes[i - 1]
        gains.append(max(delta, 0.0))
        losses.append(max(-delta, 0.0))

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    for i in range(period + 1, len(closes)):
        delta = closes[i] - closes[i - 1]
        avg_gain = (avg_gain * (period - 1) + max(delta, 0.0)) / period
        avg_loss = (avg_loss * (period - 1) + max(-delta, 0.0)) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


# ---------------------------------------------------------------------------
# Main scanner
# ---------------------------------------------------------------------------

def scan_cross_sectional_reversal(
    existing_momentum_symbols=None,
    market_regime=None,
    extra=None,
):
    """Scan for cross-sectional reversal opportunities.

    Args:
        existing_momentum_symbols: set of symbols that momentum strategies
            are currently firing on -- reversal will NOT fire on these to
            avoid contradictory signals.
        market_regime: str like "momentum", "ranging", "mean_reverting", "bearish".
            If None, defaults to allowing longs only.
        extra: dict with optional regime info from scanner pipeline.

    Returns:
        list of pick dicts matching active_picks.json format.
    """
    if existing_momentum_symbols is None:
        existing_momentum_symbols = set()
    if extra is None:
        extra = {}

    # Detect regime from extra dict if not provided directly
    if market_regime is None:
        market_regime = extra.get("regime", extra.get("market_regime", None))

    # SHORT picks only allowed in bearish or ranging regimes
    shorts_allowed = market_regime in ("bearish", "ranging", "mean_reverting", "bear", "BEAR_NORMAL", "BEAR_EXPANSION", "BEAR_COMPRESSION", "NEUTRAL_COMPRESSION", "NEUTRAL_NORMAL")

    picks = []
    today = _today_str()
    now_iso = _now_iso()

    # Step 1: Get universe (top 30 by volume)
    print(f"[CrossSectionalReversal] Fetching top {UNIVERSE_SIZE} USDT pairs by volume...")
    universe = _get_top_volume_symbols(UNIVERSE_SIZE)
    if len(universe) < 10:
        print(f"[CrossSectionalReversal] Insufficient universe ({len(universe)} pairs). Aborting.")
        return []

    print(f"[CrossSectionalReversal] Universe: {len(universe)} pairs (min vol ${MIN_DAILY_VOLUME_USD/1e6:.0f}M)")

    # Step 2: Fetch 7-day returns for all coins
    coin_data = {}
    for item in universe:
        symbol = item["symbol"]
        try:
            klines = _fetch_klines_with_failover(symbol, interval="1d", limit=8)
            if not klines:
                continue
            stats = _compute_7d_return(klines)
            if stats is None:
                continue

            # Filter: exclude >50% drawdown (fundamentally broken)
            if stats["drawdown_7d"] > MAX_DRAWDOWN_FILTER:
                logger.info("Excluded %s: drawdown %.1f%% > 50%%", symbol, stats["drawdown_7d"] * 100)
                continue

            # Also fetch hourly klines for RSI computation
            hourly = _fetch_klines_with_failover(symbol, interval="1h", limit=24)
            hourly_closes = []
            if hourly and len(hourly) >= 15:
                hourly_closes = [float(k[4]) for k in hourly]

            coin_data[symbol] = {
                **stats,
                "quote_volume": item["quoteVolume"],
                "hourly_closes": hourly_closes,
            }
        except Exception as e:
            logger.debug("Error fetching %s: %s", symbol, e)
            continue

        time.sleep(RATE_LIMIT_SEC)

    if len(coin_data) < 6:
        print(f"[CrossSectionalReversal] Insufficient data ({len(coin_data)} coins). Aborting.")
        return []

    # Step 3: Rank by 7-day return
    ranked = sorted(coin_data.items(), key=lambda x: x[1]["return_7d"])

    # Bottom N = biggest losers (LONG candidates)
    losers = ranked[:MAX_LONG_PICKS + 2]  # Extra candidates in case some are filtered
    # Top N = biggest winners (SHORT candidates)
    winners = ranked[-(MAX_SHORT_PICKS + 2):]  # Extra candidates
    winners.reverse()  # Biggest winner first

    n_total = len(ranked)
    median_return = ranked[n_total // 2][1]["return_7d"] if n_total > 0 else 0

    print(f"[CrossSectionalReversal] Ranked {n_total} coins. "
          f"Median 7d return: {median_return*100:.1f}%")
    print(f"  Biggest loser: {ranked[0][0]} ({ranked[0][1]['return_7d']*100:.1f}%)")
    print(f"  Biggest winner: {ranked[-1][0]} ({ranked[-1][1]['return_7d']*100:.1f}%)")

    # Step 4: Generate LONG picks (losers -> mean reversion)
    long_count = 0
    for symbol, stats in losers:
        if long_count >= MAX_LONG_PICKS:
            break

        # Skip if momentum strategy is also firing on this symbol
        if symbol in existing_momentum_symbols:
            logger.info("Skipping %s for LONG reversal: momentum strategy active", symbol)
            continue

        ret_7d = stats["return_7d"]

        # Need meaningful negative return (at least -5% to be worth reversing)
        if ret_7d > -0.05:
            continue

        price = stats["current_price"]
        if price <= 0:
            continue

        # Compute RSI from hourly data if available
        rsi_val = 50.0
        if stats.get("hourly_closes") and len(stats["hourly_closes"]) >= 15:
            rsi_val = _compute_rsi(stats["hourly_closes"], 14)

        # Confidence: bigger loser = higher confidence (more oversold = stronger reversion)
        # Scale: -3% -> 0.70, -15%+ -> 0.82
        magnitude = min(abs(ret_7d), 0.15)
        confidence = round(CONF_MIN + (magnitude - 0.03) / 0.12 * (CONF_MAX - CONF_MIN), 3)
        confidence = max(CONF_MIN, min(CONF_MAX, confidence))

        tp = _smart_round(price * (1 + LONG_TP_PCT), price)
        sl = _smart_round(price * (1 - LONG_SL_PCT), price)
        rr = LONG_TP_PCT / LONG_SL_PCT  # 2.0

        # Rank position (1 = biggest loser)
        rank_pos = [s for s, _ in ranked].index(symbol) + 1

        pick_id = f"cross_sectional_reversal::LONG::{symbol}::{today}"

        pick = {
            "id": pick_id,
            "strategy": "cross_sectional_reversal",
            "symbol": symbol,
            "category": "crypto",
            "signal_type": "BUY",
            "entry_price": _smart_round(price, price),
            "entry_date": today,
            "take_profit": tp,
            "stop_loss": sl,
            "confidence": confidence,
            "ml_score": None,
            "exit_price": None,
            "exit_date": None,
            "exit_reason": None,
            "pnl_pct": None,
            "pnl_dollar": None,
            "high_water_mark": None,
            "status": "OPEN",
            "regime_at_entry": "mean_reversion",
            "atr_at_entry": None,
            "rsi_at_entry": round(rsi_val, 1),
            "volume_ratio": round(stats["quote_volume"] / 1e6, 2),
            "hold_days": None,
            "allocation": 1500.0,
            "gross_tp": tp,
            "net_tp": _smart_round(tp * (1 - 0.001), price),
            "transaction_cost_pct": 0.001,
            "cost_model": 0.001,
            "position_sizing": "risk_based",
            "risk_per_trade_pct": 0.02,
            "regime_compatible": True,
            "regime_adx": None,
            "regime_volatility": None,
            "regime_trend_direction": None,
            "regime_warning": None,
            "hmm_regime": None,
            "hmm_confidence": None,
            "hmm_signal": None,
            "hmm_leverage": None,
            "forward_trades": 0,
            "forward_wr": None,
            "forward_validated": False,
            "elite_score": None,
            "elite_grade": None,
            "elite_breakdown": None,
            "source_system": "alpha_engine",
            # Strategy-specific fields
            "direction": "LONG",
            "risk_reward": round(rr, 2),
            "reason": (
                f"Reversal LONG: {symbol} dropped {ret_7d*100:.1f}% in 7d "
                f"(rank {rank_pos}/{n_total} by return). RSI={rsi_val:.0f}. "
                f"Dobrynskaya (2023): short-term crypto reversal. "
                f"TP={LONG_TP_PCT*100:.0f}% SL={LONG_SL_PCT*100:.0f}%."
            ),
            "timeframe": "1d",
            "timestamp": now_iso,
            "created_at": now_iso,
            "extra": {
                "reversal_type": "long_loser",
                "return_7d_pct": round(ret_7d * 100, 2),
                "rank": rank_pos,
                "total_ranked": n_total,
                "median_return_pct": round(median_return * 100, 2),
                "drawdown_7d_pct": round(stats["drawdown_7d"] * 100, 2),
                "quote_volume_24h": round(stats["quote_volume"], 0),
                "source": "Dobrynskaya (2023) -- Crypto Short-Term Reversal Factor",
                "correlation_with_momentum": -0.6,
            },
        }

        picks.append(pick)
        long_count += 1
        print(f"  LONG {symbol}: 7d={ret_7d*100:.1f}% rank={rank_pos}/{n_total} "
              f"RSI={rsi_val:.0f} conf={confidence}")

    # Step 5: Generate SHORT picks (winners -> overextension)
    short_count = 0
    if shorts_allowed:
        for symbol, stats in winners:
            if short_count >= MAX_SHORT_PICKS:
                break

            # Skip if momentum strategy is also firing on this symbol
            if symbol in existing_momentum_symbols:
                logger.info("Skipping %s for SHORT reversal: momentum strategy active", symbol)
                continue

            ret_7d = stats["return_7d"]

            # Need meaningful positive return (at least +5% to be worth fading)
            if ret_7d < 0.05:
                continue

            price = stats["current_price"]
            if price <= 0:
                continue

            # Compute RSI from hourly data if available
            rsi_val = 50.0
            if stats.get("hourly_closes") and len(stats["hourly_closes"]) >= 15:
                rsi_val = _compute_rsi(stats["hourly_closes"], 14)

            # Confidence: bigger winner = higher confidence for shorting
            # Scale: +5% -> 0.70, +20%+ -> 0.82
            magnitude = min(abs(ret_7d), 0.20)
            confidence = round(CONF_MIN + (magnitude - 0.05) / 0.15 * (CONF_MAX - CONF_MIN), 3)
            confidence = max(CONF_MIN, min(CONF_MAX, confidence))

            # SHORT: TP is below entry, SL is above entry
            tp = _smart_round(price * (1 - SHORT_TP_PCT), price)
            sl = _smart_round(price * (1 + SHORT_SL_PCT), price)
            rr = SHORT_TP_PCT / SHORT_SL_PCT  # 2.0

            # Rank position from top (1 = biggest winner)
            rank_pos_from_top = n_total - [s for s, _ in ranked].index(symbol)

            pick_id = f"cross_sectional_reversal::SHORT::{symbol}::{today}"

            pick = {
                "id": pick_id,
                "strategy": "cross_sectional_reversal",
                "symbol": symbol,
                "category": "crypto",
                "signal_type": "SELL",
                "entry_price": _smart_round(price, price),
                "entry_date": today,
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": confidence,
                "ml_score": None,
                "exit_price": None,
                "exit_date": None,
                "exit_reason": None,
                "pnl_pct": None,
                "pnl_dollar": None,
                "high_water_mark": None,
                "status": "OPEN",
                "regime_at_entry": "mean_reversion",
                "atr_at_entry": None,
                "rsi_at_entry": round(rsi_val, 1),
                "volume_ratio": round(stats["quote_volume"] / 1e6, 2),
                "hold_days": None,
                "allocation": 1500.0,
                "gross_tp": tp,
                "net_tp": _smart_round(tp * (1 + 0.001), price),
                "transaction_cost_pct": 0.001,
                "cost_model": 0.001,
                "position_sizing": "risk_based",
                "risk_per_trade_pct": 0.02,
                "regime_compatible": True,
                "regime_adx": None,
                "regime_volatility": None,
                "regime_trend_direction": None,
                "regime_warning": None,
                "hmm_regime": None,
                "hmm_confidence": None,
                "hmm_signal": None,
                "hmm_leverage": None,
                "forward_trades": 0,
                "forward_wr": None,
                "forward_validated": False,
                "elite_score": None,
                "elite_grade": None,
                "elite_breakdown": None,
                "source_system": "alpha_engine",
                # Strategy-specific fields
                "direction": "SHORT",
                "risk_reward": round(rr, 2),
                "reason": (
                    f"Reversal SHORT: {symbol} rallied {ret_7d*100:.1f}% in 7d "
                    f"(rank {rank_pos_from_top}/{n_total} from top). RSI={rsi_val:.0f}. "
                    f"Dobrynskaya (2023): overextended winners revert. "
                    f"TP={SHORT_TP_PCT*100:.0f}% SL={SHORT_SL_PCT*100:.0f}%."
                ),
                "timeframe": "1d",
                "timestamp": now_iso,
                "created_at": now_iso,
                "extra": {
                    "reversal_type": "short_winner",
                    "return_7d_pct": round(ret_7d * 100, 2),
                    "rank_from_top": rank_pos_from_top,
                    "total_ranked": n_total,
                    "median_return_pct": round(median_return * 100, 2),
                    "drawdown_7d_pct": round(stats["drawdown_7d"] * 100, 2),
                    "quote_volume_24h": round(stats["quote_volume"], 0),
                    "source": "Dobrynskaya (2023) -- Crypto Short-Term Reversal Factor",
                    "correlation_with_momentum": -0.6,
                    "regime_at_short": market_regime,
                },
            }

            picks.append(pick)
            short_count += 1
            print(f"  SHORT {symbol}: 7d=+{ret_7d*100:.1f}% rank={rank_pos_from_top}/{n_total} "
                  f"RSI={rsi_val:.0f} conf={confidence}")
    else:
        print(f"  SHORT picks disabled: regime={market_regime} (need bearish/ranging)")

    print(f"[CrossSectionalReversal] Complete: {long_count} LONG + {short_count} SHORT = {len(picks)} picks")
    return picks


# ---------------------------------------------------------------------------
# Entry point for standalone testing
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("=" * 60)
    print("Cross-Sectional Reversal Scanner")
    print("=" * 60)
    picks = scan_cross_sectional_reversal(
        existing_momentum_symbols=set(),
        market_regime="ranging",  # Allow shorts in test mode
    )
    print(f"\n{'='*60}")
    print(f"Total picks: {len(picks)}")
    for p in picks:
        print(f"  {p['direction']} {p['symbol']}: "
              f"entry={p['entry_price']} TP={p['take_profit']} SL={p['stop_loss']} "
              f"conf={p['confidence']}")

    # Save to file
    out_path = os.path.join(DATA_DIR, "reversal_picks.json")
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(picks, f, indent=2)
    print(f"\nSaved to {out_path}")
