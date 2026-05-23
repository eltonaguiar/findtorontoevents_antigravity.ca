#!/usr/bin/env python3
"""
Binance Futures Smart Money Scraper & Pick Generator
=====================================================
Uses Binance's official public futures data API to generate smart money
picks based on top trader positioning, open interest, funding rates,
and taker buy/sell volume.

NO API KEY NEEDED - All endpoints are public.

API Research (2026-03-19):
  - The old /bapi/futures/v1/public/future/leaderboard/ endpoints return 404
  - The copy-trade /bapi/ gateway requires auth/CSRF tokens
  - However, fapi.binance.com has fully public endpoints:
    * Top Trader Long/Short Position Ratio (per symbol)
    * Top Trader Long/Short Account Ratio (per symbol)
    * Global Long/Short Account Ratio
    * Open Interest + OI Statistics (historical)
    * Taker Buy/Sell Volume ratio
    * Funding Rate + Premium Index
    * 24hr Ticker (all futures pairs)

Strategy: Analyze top trader positioning across all major futures pairs.
When top traders are heavily long (L/S ratio > 1.3) or short (< 0.75),
combined with confirming OI and funding signals, generate picks.

API Failover Rule: 3+ fallback chain (fapi.binance.com → fapi1 → fapi2).
Rate limit: 200ms between calls.
"""

import json
import time
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
import requests

# Fix Windows charmap encoding
if sys.platform == "win32":
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')
    sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')

# -- API Mirrors (failover chain per project rules) --
BINANCE_FAPI_MIRRORS = [
    "https://fapi.binance.com",
    "https://fapi1.binance.com",
    "https://fapi2.binance.com",
]

# Futures data endpoints (appended to mirror base)
ENDPOINTS = {
    "ticker_24hr": "/fapi/v1/ticker/24hr",
    "top_trader_position_ratio": "/futures/data/topLongShortPositionRatio",
    "top_trader_account_ratio": "/futures/data/topLongShortAccountRatio",
    "global_ls_ratio": "/futures/data/globalLongShortAccountRatio",
    "open_interest": "/fapi/v1/openInterest",
    "oi_hist": "/futures/data/openInterestHist",
    "taker_volume": "/futures/data/takerlongshortRatio",
    "funding_rate": "/fapi/v1/fundingRate",
    "premium_index": "/fapi/v1/premiumIndex",
    "klines": "/fapi/v1/klines",
}

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# Rate limit
RATE_LIMIT_SEC = 0.2

# Top symbols to analyze (high volume majors + popular alts)
# We'll dynamically select the top N by volume at runtime
MAX_SYMBOLS_ANALYZE = 40

# Signal thresholds
STRONG_LONG_THRESHOLD = 1.35   # Top traders heavily long
STRONG_SHORT_THRESHOLD = 0.72  # Top traders heavily short
MODERATE_LONG_THRESHOLD = 1.20
MODERATE_SHORT_THRESHOLD = 0.82
MIN_VOLUME_USD = 20_000_000    # Minimum 24h volume to consider

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}


def binance_get(path: str, params: dict = None, retries: int = 3) -> any:
    """
    GET request to Binance Futures API with mirror failover.
    Returns parsed JSON or None.
    """
    for mirror in BINANCE_FAPI_MIRRORS:
        url = f"{mirror}{path}"
        for attempt in range(retries):
            try:
                resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
                if resp.status_code == 200:
                    return resp.json()
                elif resp.status_code == 429:
                    time.sleep(2)
                    continue
                elif resp.status_code == 418:
                    # IP banned temporarily
                    time.sleep(5)
                    continue
                else:
                    break  # Try next mirror
            except requests.exceptions.RequestException:
                if attempt < retries - 1:
                    time.sleep(1)
                continue
    return None


def get_top_volume_symbols(min_volume: float = MIN_VOLUME_USD, max_count: int = MAX_SYMBOLS_ANALYZE) -> list:
    """
    Fetch all futures tickers, filter USDT pairs by volume, return top N.
    Returns list of dicts with symbol, volume, priceChange info.
    """
    data = binance_get(ENDPOINTS["ticker_24hr"])
    if not data:
        return []

    usdt_pairs = []
    for t in data:
        sym = t.get("symbol", "")
        if not sym.endswith("USDT"):
            continue
        try:
            vol = float(t.get("quoteVolume", 0))
            price = float(t.get("lastPrice", 0))
            change_pct = float(t.get("priceChangePercent", 0))
        except (ValueError, TypeError):
            continue
        if vol < min_volume or price <= 0:
            continue
        usdt_pairs.append({
            "symbol": sym,
            "volume_24h": vol,
            "last_price": price,
            "price_change_pct": change_pct,
            "high_price": float(t.get("highPrice", price)),
            "low_price": float(t.get("lowPrice", price)),
            "weighted_avg_price": float(t.get("weightedAvgPrice", price)),
        })

    usdt_pairs.sort(key=lambda x: x["volume_24h"], reverse=True)
    return usdt_pairs[:max_count]


def get_top_trader_ratio(symbol: str, period: str = "1h", limit: int = 3) -> list:
    """
    Get top trader long/short position ratio for a symbol.
    Returns list of {longShortRatio, longAccount, shortAccount, timestamp}.
    """
    data = binance_get(ENDPOINTS["top_trader_position_ratio"], params={
        "symbol": symbol, "period": period, "limit": limit,
    })
    return data if isinstance(data, list) else []


def get_top_trader_account_ratio(symbol: str, period: str = "1h", limit: int = 3) -> list:
    """Get top trader long/short account ratio."""
    data = binance_get(ENDPOINTS["top_trader_account_ratio"], params={
        "symbol": symbol, "period": period, "limit": limit,
    })
    return data if isinstance(data, list) else []


def get_global_ls_ratio(symbol: str, period: str = "1h", limit: int = 3) -> list:
    """Get global long/short account ratio."""
    data = binance_get(ENDPOINTS["global_ls_ratio"], params={
        "symbol": symbol, "period": period, "limit": limit,
    })
    return data if isinstance(data, list) else []


def get_open_interest(symbol: str) -> dict:
    """Get current open interest for a symbol."""
    data = binance_get(ENDPOINTS["open_interest"], params={"symbol": symbol})
    return data if isinstance(data, dict) else {}


def get_oi_history(symbol: str, period: str = "1h", limit: int = 5) -> list:
    """Get historical OI for trend analysis."""
    data = binance_get(ENDPOINTS["oi_hist"], params={
        "symbol": symbol, "period": period, "limit": limit,
    })
    return data if isinstance(data, list) else []


def get_taker_volume(symbol: str, period: str = "1h", limit: int = 3) -> list:
    """Get taker buy/sell volume ratio."""
    data = binance_get(ENDPOINTS["taker_volume"], params={
        "symbol": symbol, "period": period, "limit": limit,
    })
    return data if isinstance(data, list) else []


def get_funding_rate(symbol: str, limit: int = 3) -> list:
    """Get recent funding rates."""
    data = binance_get(ENDPOINTS["funding_rate"], params={
        "symbol": symbol, "limit": limit,
    })
    return data if isinstance(data, list) else []


def get_premium_index(symbol: str) -> dict:
    """Get premium index (mark price, funding rate, next funding time)."""
    data = binance_get(ENDPOINTS["premium_index"], params={"symbol": symbol})
    return data if isinstance(data, dict) else {}


def analyze_symbol(symbol_info: dict) -> dict:
    """
    Analyze a single symbol using multiple Binance data sources.
    Returns analysis dict with signal and confidence.
    """
    symbol = symbol_info["symbol"]
    price = symbol_info["last_price"]

    analysis = {
        "symbol": symbol,
        "price": price,
        "volume_24h": symbol_info["volume_24h"],
        "price_change_pct": symbol_info["price_change_pct"],
        "signals": [],
        "direction": None,
        "confidence": 0,
        "signal_strength": 0,
    }

    bullish_score = 0
    bearish_score = 0

    # 1. Top Trader Position Ratio
    time.sleep(RATE_LIMIT_SEC)
    pos_ratios = get_top_trader_ratio(symbol, period="1h", limit=3)
    if pos_ratios:
        latest = pos_ratios[-1]
        try:
            ls_ratio = float(latest["longShortRatio"])
            long_pct = float(latest["longAccount"])
        except (ValueError, TypeError, KeyError):
            ls_ratio = 1.0
            long_pct = 0.5

        analysis["top_trader_ls_ratio"] = ls_ratio
        analysis["top_trader_long_pct"] = round(long_pct * 100, 1)

        if ls_ratio >= STRONG_LONG_THRESHOLD:
            bullish_score += 3
            analysis["signals"].append(f"Top traders HEAVILY LONG (L/S={ls_ratio:.2f})")
        elif ls_ratio >= MODERATE_LONG_THRESHOLD:
            bullish_score += 2
            analysis["signals"].append(f"Top traders lean LONG (L/S={ls_ratio:.2f})")
        elif ls_ratio <= STRONG_SHORT_THRESHOLD:
            bearish_score += 3
            analysis["signals"].append(f"Top traders HEAVILY SHORT (L/S={ls_ratio:.2f})")
        elif ls_ratio <= MODERATE_SHORT_THRESHOLD:
            bearish_score += 2
            analysis["signals"].append(f"Top traders lean SHORT (L/S={ls_ratio:.2f})")

        # Check trend: is L/S ratio increasing?
        if len(pos_ratios) >= 2:
            try:
                prev_ratio = float(pos_ratios[-2]["longShortRatio"])
                if ls_ratio > prev_ratio * 1.05:
                    bullish_score += 1
                    analysis["signals"].append("L/S ratio INCREASING")
                elif ls_ratio < prev_ratio * 0.95:
                    bearish_score += 1
                    analysis["signals"].append("L/S ratio DECREASING")
            except (ValueError, TypeError, KeyError):
                pass

    # 2. Top Trader Account Ratio (different from position ratio)
    time.sleep(RATE_LIMIT_SEC)
    acct_ratios = get_top_trader_account_ratio(symbol, period="1h", limit=1)
    if acct_ratios:
        try:
            acct_ls = float(acct_ratios[-1]["longShortRatio"])
            analysis["top_trader_acct_ls"] = acct_ls
            if acct_ls >= 1.4:
                bullish_score += 1
                analysis["signals"].append(f"Account ratio bullish ({acct_ls:.2f})")
            elif acct_ls <= 0.7:
                bearish_score += 1
                analysis["signals"].append(f"Account ratio bearish ({acct_ls:.2f})")
        except (ValueError, TypeError, KeyError):
            pass

    # 3. Taker Buy/Sell Volume
    time.sleep(RATE_LIMIT_SEC)
    taker = get_taker_volume(symbol, period="1h", limit=3)
    if taker:
        try:
            bs_ratio = float(taker[-1]["buySellRatio"])
            analysis["taker_buy_sell_ratio"] = bs_ratio
            if bs_ratio >= 1.15:
                bullish_score += 2
                analysis["signals"].append(f"Taker volume BULLISH (B/S={bs_ratio:.2f})")
            elif bs_ratio <= 0.85:
                bearish_score += 2
                analysis["signals"].append(f"Taker volume BEARISH (B/S={bs_ratio:.2f})")
        except (ValueError, TypeError, KeyError):
            pass

    # 4. Funding Rate
    time.sleep(RATE_LIMIT_SEC)
    premium = get_premium_index(symbol)
    if premium:
        try:
            funding = float(premium.get("lastFundingRate", 0))
            analysis["funding_rate"] = funding
            analysis["mark_price"] = float(premium.get("markPrice", price))
            # Negative funding = shorts paying longs = potential squeeze up
            if funding < -0.0003:
                bullish_score += 2
                analysis["signals"].append(f"Negative funding ({funding:.6f}) - short squeeze risk")
            elif funding > 0.001:
                bearish_score += 1
                analysis["signals"].append(f"High funding ({funding:.6f}) - overleveraged longs")
        except (ValueError, TypeError):
            pass

    # 5. OI Change
    time.sleep(RATE_LIMIT_SEC)
    oi_hist = get_oi_history(symbol, period="1h", limit=5)
    if len(oi_hist) >= 2:
        try:
            oi_now = float(oi_hist[-1]["sumOpenInterestValue"])
            oi_prev = float(oi_hist[-2]["sumOpenInterestValue"])
            oi_change = (oi_now - oi_prev) / oi_prev if oi_prev > 0 else 0
            analysis["oi_value"] = oi_now
            analysis["oi_change_pct"] = round(oi_change * 100, 2)
            if oi_change > 0.05:
                # OI increasing significantly
                if bullish_score > bearish_score:
                    bullish_score += 1
                    analysis["signals"].append(f"OI surging +{oi_change*100:.1f}% (confirms long bias)")
                elif bearish_score > bullish_score:
                    bearish_score += 1
                    analysis["signals"].append(f"OI surging +{oi_change*100:.1f}% (confirms short bias)")
            elif oi_change < -0.05:
                analysis["signals"].append(f"OI dropping {oi_change*100:.1f}% (positions closing)")
        except (ValueError, TypeError, KeyError):
            pass

    # Calculate final direction and confidence
    total_score = bullish_score + bearish_score
    if total_score == 0:
        return analysis

    if bullish_score > bearish_score and bullish_score >= 3:
        analysis["direction"] = "LONG"
        analysis["signal_strength"] = bullish_score
        analysis["confidence"] = round(min(0.95, 0.55 + bullish_score * 0.05), 3)
    elif bearish_score > bullish_score and bearish_score >= 3:
        analysis["direction"] = "SHORT"
        analysis["signal_strength"] = bearish_score
        analysis["confidence"] = round(min(0.95, 0.55 + bearish_score * 0.05), 3)

    return analysis


def analysis_to_pick(analysis: dict) -> dict:
    """Convert a symbol analysis into an active_picks.json compatible pick."""
    if not analysis.get("direction") or analysis["confidence"] < 0.60:
        return None

    symbol = analysis["symbol"]
    direction = analysis["direction"]
    price = analysis["price"]
    confidence = analysis["confidence"]

    now = datetime.now(timezone.utc)

    # TP/SL based on direction and confidence
    if direction == "LONG":
        tp_mult = 1.04 + confidence * 0.02  # 1.06-1.059
        sl_mult = 0.97
        tp_price = round(price * tp_mult, 8)
        sl_price = round(price * sl_mult, 8)
    else:
        tp_mult = 0.96 - confidence * 0.02  # 0.94-0.941
        sl_mult = 1.03
        tp_price = round(price * tp_mult, 8)
        sl_price = round(price * sl_mult, 8)

    signals_text = " | ".join(analysis.get("signals", [])[:3])
    ls_ratio = analysis.get("top_trader_ls_ratio", 0)
    funding = analysis.get("funding_rate", 0)

    pick_id = f"binance_ls_ratio::{symbol}::{now.strftime('%Y-%m-%d_%H%M')}"

    return {
        "id": pick_id,
        "strategy": "binance_ls_ratio",
        "symbol": symbol,
        "category": "crypto",
        "signal_type": "BUY" if direction == "LONG" else "SELL",
        "direction": direction,
        "entry_price": price,
        "entry_date": now.strftime("%Y-%m-%d"),
        "take_profit": tp_price,
        "stop_loss": sl_price,
        "confidence": confidence,
        "ml_score": confidence,
        "exit_price": None,
        "exit_date": None,
        "exit_reason": None,
        "pnl_pct": None,
        "pnl_dollar": None,
        "status": "OPEN",
        "hold_days": None,
        "allocation": 200.0,
        "position_sizing": "smart_money",
        "risk_per_trade_pct": 0.03,
        "max_safe_leverage": 5.0,
        "forward_trades": 0,
        "forward_wr": 0,
        "forward_validated": False,
        "elite_score": min(100, int(analysis["signal_strength"] * 12 + confidence * 40)),
        "elite_grade": "A" if confidence >= 0.80 else "B" if confidence >= 0.70 else "C",
        "reason": (f"Binance Smart Money | {signals_text} | "
                   f"L/S:{ls_ratio:.2f} Fund:{funding:.6f}"),
        "source_system": "copy_trader_binance",
        "trader_name": "binance_top_traders",
        "trader_roi": 0,
        "trader_aum": 0,
        "trader_win_rate": 0,
        "leverage": 5.0,
        "unrealized_pnl": 0,
        "open_time": now.isoformat(),
        "top_trader_ls_ratio": analysis.get("top_trader_ls_ratio", 0),
        "top_trader_long_pct": analysis.get("top_trader_long_pct", 0),
        "taker_buy_sell_ratio": analysis.get("taker_buy_sell_ratio", 0),
        "funding_rate": funding,
        "oi_value": analysis.get("oi_value", 0),
        "oi_change_pct": analysis.get("oi_change_pct", 0),
        "price_change_24h_pct": analysis.get("price_change_pct", 0),
        "volume_24h_usd": analysis.get("volume_24h", 0),
        "signal_count": len(analysis.get("signals", [])),
        "all_signals": analysis.get("signals", []),
        "timestamp": now.isoformat(),
    }


def scan_binance_traders(max_symbols: int = MAX_SYMBOLS_ANALYZE) -> tuple:
    """
    Main Binance scan: fetch top volume symbols, analyze each using
    top trader positioning + OI + funding + taker volume.
    Returns (trader_profiles, picks).
    """
    print("=" * 70)
    print("  BINANCE FUTURES SMART MONEY SCRAPER")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  Data sources: Top Trader L/S | Taker Volume | Funding | OI")
    print("=" * 70)

    # Step 1: Get top volume symbols
    print("\n  Fetching top futures pairs by volume...")
    symbols = get_top_volume_symbols(min_volume=MIN_VOLUME_USD, max_count=max_symbols)
    if not symbols:
        print("  [ERROR] Could not fetch ticker data")
        return [], []
    print(f"  Found {len(symbols)} USDT futures pairs with >${MIN_VOLUME_USD/1e6:.0f}M volume")

    # Step 2: Analyze each symbol
    all_analyses = []
    all_picks = []
    all_profiles = []

    for i, sym_info in enumerate(symbols):
        symbol = sym_info["symbol"]
        print(f"  [{i+1}/{len(symbols)}] {symbol:15s} ", end="", flush=True)

        analysis = analyze_symbol(sym_info)
        all_analyses.append(analysis)

        direction = analysis.get("direction")
        confidence = analysis.get("confidence", 0)
        signals = analysis.get("signals", [])

        # Build profile entry
        profile = {
            "symbol": symbol,
            "price": sym_info["last_price"],
            "volume_24h": sym_info["volume_24h"],
            "price_change_pct": sym_info["price_change_pct"],
            "top_trader_ls_ratio": analysis.get("top_trader_ls_ratio", 0),
            "top_trader_long_pct": analysis.get("top_trader_long_pct", 0),
            "taker_bs_ratio": analysis.get("taker_buy_sell_ratio", 0),
            "funding_rate": analysis.get("funding_rate", 0),
            "oi_change_pct": analysis.get("oi_change_pct", 0),
            "direction": direction,
            "confidence": confidence,
            "signal_count": len(signals),
            "signals": signals,
            "analysis_time": datetime.now(timezone.utc).isoformat(),
        }
        all_profiles.append(profile)

        if direction and confidence >= 0.60:
            pick = analysis_to_pick(analysis)
            if pick:
                all_picks.append(pick)
                print(f"{direction:5s} conf={confidence:.2f} "
                      f"signals={len(signals)} | {'; '.join(signals[:2])}")
            else:
                print(f"({direction} conf={confidence:.2f} - below threshold)")
        else:
            print(f"NEUTRAL (bull={analysis.get('signal_strength', 0)} "
                  f"signals={len(signals)})")

    print(f"\n  Binance scan complete: {len(all_profiles)} symbols analyzed, "
          f"{len(all_picks)} picks generated")

    return all_profiles, all_picks


def save_binance_results(profiles: list, picks: list):
    """Save Binance results to data files."""
    now_iso = datetime.now(timezone.utc).isoformat()

    # Save symbol profiles
    profiles_path = DATA_DIR / "binance_trader_profiles.json"
    with open(profiles_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": now_iso,
            "source": "binance_futures_smart_money",
            "api_note": "Uses fapi.binance.com public endpoints (no auth needed)",
            "endpoints_used": [
                "topLongShortPositionRatio",
                "topLongShortAccountRatio",
                "takerlongshortRatio",
                "fundingRate",
                "openInterestHist",
                "premiumIndex",
                "ticker/24hr",
            ],
            "symbol_count": len(profiles),
            "profiles": profiles,
        }, f, indent=2, default=str)
    print(f"  Saved {len(profiles)} symbol profiles to {profiles_path}")

    # Save picks
    picks_path = DATA_DIR / "binance_picks.json"
    with open(picks_path, "w", encoding="utf-8") as f:
        json.dump(picks, f, indent=2, default=str)
    print(f"  Saved {len(picks)} picks to {picks_path}")

    return profiles_path, picks_path


if __name__ == "__main__":
    profiles, picks = scan_binance_traders(max_symbols=30)
    save_binance_results(profiles, picks)

    if picks:
        print(f"\nDone. {len(picks)} Binance smart money picks generated.")
        print("\nTop picks:")
        picks.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        for p in picks[:10]:
            print(f"  {p['symbol']:15s} {p['direction']:5s} "
                  f"conf={p['confidence']:.2f} "
                  f"entry={p['entry_price']:.4f} "
                  f"TP={p['take_profit']:.4f} SL={p['stop_loss']:.4f}")
    else:
        print("\nDone. No strong signals detected at this time.")
