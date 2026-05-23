#!/usr/bin/env python3
"""
OKX Futures Leaderboard Scraper & Pick Generator
==================================================
Scrapes OKX public market data APIs to generate picks based on
elite trader positioning, funding rates, and open interest.

This is DIFFERENT from the OKX copy trading scraper (okx_scraper.py).
That one uses /api/v5/copytrading/ endpoints for individual trader positions.
This one uses /api/v5/rubik/stat/ and /api/v5/public/ endpoints to read
aggregate futures market sentiment from the OKX Futures Leaderboard
(https://www.okx.com/trade-market/position/swap).

NO API KEY NEEDED - All endpoints are public.

Working endpoints (verified 2026-03-19):
  Long/Short Ratio:  GET /api/v5/rubik/stat/contracts/long-short-account-ratio
  Open Interest:     GET /api/v5/rubik/stat/contracts/open-interest-volume
  Taker Volume:      GET /api/v5/rubik/stat/taker-volume
  Funding Rate:      GET /api/v5/public/funding-rate
  Funding History:   GET /api/v5/public/funding-rate-history
  Mark Price:        GET /api/v5/public/mark-price

Strategy:
  1. Fetch long/short ratio for top coins (>1.0 = more longs, <1.0 = more shorts)
  2. Fetch funding rate (negative = shorts paying longs = bullish squeeze potential)
  3. Fetch taker buy/sell volume (buy > sell = bullish momentum)
  4. Combine signals: when 2+ indicators agree on direction, generate pick

API Failover: 3 mirrors (okx.com, aws.okx.com, okx.com fallback).
Rate limit: 200ms between calls.
"""

import json
import time
import sys
import os
from datetime import datetime, timezone
from pathlib import Path

import requests

# -- Windows UTF-8 fix --
if sys.platform == "win32":
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')
    sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')

# -- API Mirrors (failover chain per project rules) --
OKX_API_MIRRORS = [
    "https://www.okx.com",
    "https://aws.okx.com",
    "https://okx.com",
]

# Endpoints
LONG_SHORT_RATIO = "/api/v5/rubik/stat/contracts/long-short-account-ratio"
OI_VOLUME = "/api/v5/rubik/stat/contracts/open-interest-volume"
TAKER_VOLUME = "/api/v5/rubik/stat/taker-volume"
FUNDING_RATE = "/api/v5/public/funding-rate"
FUNDING_HISTORY = "/api/v5/public/funding-rate-history"
MARK_PRICE = "/api/v5/public/mark-price"
OPEN_INTEREST = "/api/v5/public/open-interest"

# Top coins to scan
SCAN_COINS = [
    "BTC", "ETH", "SOL", "XRP", "DOGE",
    "BNB", "ADA", "AVAX", "LINK", "DOT",
    "MATIC", "UNI", "NEAR", "FIL", "APT",
    "ARB", "OP", "PEPE", "WIF", "SUI",
]

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

RATE_LIMIT_SEC = 0.2

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}


def okx_get(path: str, params: dict = None, retries: int = 3) -> dict:
    """GET request to OKX API with mirror failover. Returns parsed JSON or empty dict."""
    for mirror in OKX_API_MIRRORS:
        url = f"{mirror}{path}"
        for attempt in range(retries):
            try:
                resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("code") in ("0", 0):
                        return data
                elif resp.status_code == 429:
                    time.sleep(2)
                    continue
            except requests.exceptions.RequestException:
                if attempt < retries - 1:
                    time.sleep(1)
                continue
        time.sleep(0.3)
    return {}


def fetch_long_short_ratio(ccy: str) -> dict:
    """
    Fetch long/short account ratio for a currency.
    Returns latest data point: {ts, ratio} where ratio > 1.0 means more longs.
    Data format: [timestamp_ms, ratio_string]
    """
    data = okx_get(LONG_SHORT_RATIO, params={"ccy": ccy, "period": "5m"})
    items = data.get("data", [])
    if not items:
        return {}

    # Get latest and recent history for trend detection
    latest = items[0]  # Most recent (sorted desc)
    try:
        ratio = float(latest[1])
        ts = int(latest[0])
    except (IndexError, ValueError, TypeError):
        return {}

    # Calculate trend: compare latest vs 1h ago (12 x 5min = 1h)
    trend = 0.0
    if len(items) >= 12:
        try:
            ratio_1h_ago = float(items[11][1])
            trend = ratio - ratio_1h_ago
        except (IndexError, ValueError, TypeError):
            pass

    return {
        "ratio": ratio,
        "ts": ts,
        "trend_1h": round(trend, 4),
        "bias": "LONG" if ratio > 1.05 else "SHORT" if ratio < 0.95 else "NEUTRAL",
    }


def fetch_funding_rate(inst_id: str) -> dict:
    """
    Fetch current funding rate for a swap instrument.
    Negative funding = shorts paying longs (bullish pressure).
    Positive funding = longs paying shorts (bearish pressure).
    """
    data = okx_get(FUNDING_RATE, params={"instId": inst_id})
    items = data.get("data", [])
    if not items:
        return {}

    item = items[0]
    try:
        rate = float(item.get("fundingRate", 0))
    except (ValueError, TypeError):
        rate = 0.0

    # Also get historical rates for trend
    hist_data = okx_get(FUNDING_HISTORY, params={"instId": inst_id, "limit": "10"})
    hist_items = hist_data.get("data", [])

    avg_rate = rate
    if hist_items:
        try:
            rates = [float(h.get("fundingRate", 0)) for h in hist_items[:5]]
            avg_rate = sum(rates) / len(rates) if rates else rate
        except (ValueError, TypeError):
            pass

    # Extreme funding signals
    extreme_long = rate > 0.0005   # longs paying a lot = potential long squeeze
    extreme_short = rate < -0.0005  # shorts paying a lot = potential short squeeze

    return {
        "rate": rate,
        "rate_pct": round(rate * 100, 4),
        "avg_5_period": round(avg_rate, 8),
        "extreme_long": extreme_long,
        "extreme_short": extreme_short,
        "bias": "SHORT" if rate > 0.0003 else "LONG" if rate < -0.0003 else "NEUTRAL",
    }


def fetch_taker_volume(ccy: str) -> dict:
    """
    Fetch taker buy/sell volume ratio.
    Data format: [timestamp_ms, buy_volume, sell_volume]
    buy > sell = bullish momentum.
    """
    data = okx_get(TAKER_VOLUME, params={"ccy": ccy, "instType": "CONTRACTS", "period": "5m"})
    items = data.get("data", [])
    if not items:
        return {}

    # Latest datapoint
    latest = items[0]
    try:
        buy_vol = float(latest[1])
        sell_vol = float(latest[2])
    except (IndexError, ValueError, TypeError):
        return {}

    total = buy_vol + sell_vol
    if total <= 0:
        return {}

    buy_pct = buy_vol / total
    sell_pct = sell_vol / total

    # Average over last hour for trend
    recent = items[:12]
    avg_buy_pct = buy_pct
    if len(recent) >= 3:
        try:
            buys = [float(r[1]) for r in recent]
            sells = [float(r[2]) for r in recent]
            total_buy = sum(buys)
            total_sell = sum(sells)
            total_all = total_buy + total_sell
            avg_buy_pct = total_buy / total_all if total_all > 0 else 0.5
        except (IndexError, ValueError, TypeError):
            pass

    return {
        "buy_vol": buy_vol,
        "sell_vol": sell_vol,
        "buy_pct": round(buy_pct, 4),
        "sell_pct": round(sell_pct, 4),
        "avg_buy_pct_1h": round(avg_buy_pct, 4),
        "bias": "LONG" if avg_buy_pct > 0.52 else "SHORT" if avg_buy_pct < 0.48 else "NEUTRAL",
    }


def fetch_mark_price(inst_id: str) -> float:
    """Fetch current mark price for an instrument."""
    data = okx_get(MARK_PRICE, params={"instType": "SWAP", "instId": inst_id})
    items = data.get("data", [])
    if not items:
        return 0.0
    try:
        return float(items[0].get("markPx", 0))
    except (ValueError, TypeError):
        return 0.0


def fetch_open_interest_data(ccy: str) -> dict:
    """
    Fetch open interest + volume history.
    Data format: [timestamp_ms, oi_usd, volume_usd]
    Rising OI + rising price = strong trend. Rising OI + falling price = bearish.
    """
    data = okx_get(OI_VOLUME, params={"ccy": ccy, "period": "5m"})
    items = data.get("data", [])
    if not items or len(items) < 2:
        return {}

    latest = items[0]
    prev = items[min(11, len(items) - 1)]  # ~1h ago

    try:
        oi_now = float(latest[1])
        oi_prev = float(prev[1])
    except (IndexError, ValueError, TypeError):
        return {}

    oi_change_pct = ((oi_now - oi_prev) / oi_prev * 100) if oi_prev > 0 else 0

    return {
        "oi_usd": oi_now,
        "oi_change_1h_pct": round(oi_change_pct, 2),
        "oi_rising": oi_change_pct > 1.0,
        "oi_falling": oi_change_pct < -1.0,
    }


def generate_pick(ccy: str, analysis: dict) -> dict:
    """
    Generate a pick from OKX futures market analysis.
    Requires 2+ signals agreeing on direction to generate a pick.
    """
    ls = analysis.get("long_short", {})
    fr = analysis.get("funding", {})
    tv = analysis.get("taker_vol", {})
    oi = analysis.get("oi", {})
    mark_price = analysis.get("mark_price", 0)

    if mark_price <= 0:
        return None

    # Count directional signals
    long_signals = 0
    short_signals = 0
    reasons = []

    # 1. Long/short ratio
    ls_bias = ls.get("bias", "NEUTRAL")
    if ls_bias == "LONG":
        long_signals += 1
        reasons.append(f"L/S ratio {ls.get('ratio', 0):.2f} (bullish)")
    elif ls_bias == "SHORT":
        short_signals += 1
        reasons.append(f"L/S ratio {ls.get('ratio', 0):.2f} (bearish)")

    # 2. Funding rate (contrarian: extreme funding = fade the crowd)
    fr_bias = fr.get("bias", "NEUTRAL")
    if fr_bias == "LONG":  # Negative funding = shorts paying = go long
        long_signals += 1
        reasons.append(f"Funding {fr.get('rate_pct', 0):.4f}% (shorts paying)")
    elif fr_bias == "SHORT":  # Positive funding = longs paying = go short
        short_signals += 1
        reasons.append(f"Funding {fr.get('rate_pct', 0):.4f}% (longs paying)")

    # Extreme funding = stronger signal (potential squeeze)
    if fr.get("extreme_short"):
        long_signals += 1
        reasons.append("EXTREME negative funding (short squeeze risk)")
    elif fr.get("extreme_long"):
        short_signals += 1
        reasons.append("EXTREME positive funding (long squeeze risk)")

    # 3. Taker volume momentum
    tv_bias = tv.get("bias", "NEUTRAL")
    if tv_bias == "LONG":
        long_signals += 1
        reasons.append(f"Taker buy {tv.get('avg_buy_pct_1h', 0)*100:.1f}% (momentum)")
    elif tv_bias == "SHORT":
        short_signals += 1
        reasons.append(f"Taker buy {tv.get('avg_buy_pct_1h', 0)*100:.1f}% (selling)")

    # 4. OI trend (confirming signal only)
    if oi.get("oi_rising"):
        reasons.append(f"OI rising +{oi.get('oi_change_1h_pct', 0):.1f}%")
    elif oi.get("oi_falling"):
        reasons.append(f"OI falling {oi.get('oi_change_1h_pct', 0):.1f}%")

    # Need 2+ signals in same direction
    if long_signals < 2 and short_signals < 2:
        return None

    # Determine direction
    if long_signals > short_signals:
        direction = "LONG"
        signal_strength = long_signals
    elif short_signals > long_signals:
        direction = "SHORT"
        signal_strength = short_signals
    else:
        return None  # Conflicting signals

    # Confidence based on signal count
    confidence = round(min(0.90, 0.55 + signal_strength * 0.08), 3)

    # TP/SL based on direction
    if direction == "LONG":
        tp = round(mark_price * 1.035, 8)
        sl = round(mark_price * 0.975, 8)
    else:
        tp = round(mark_price * 0.965, 8)
        sl = round(mark_price * 1.025, 8)

    symbol = f"{ccy}USDT"
    now = datetime.now(timezone.utc)
    pick_id = f"okx_futures_{ccy}::{now.strftime('%Y-%m-%d_%H%M')}"

    return {
        "id": pick_id,
        "strategy": f"okx_futures_{ccy.lower()}",
        "symbol": symbol,
        "category": "crypto",
        "signal_type": "BUY" if direction == "LONG" else "SELL",
        "direction": direction,
        "entry_price": mark_price,
        "entry_date": now.strftime("%Y-%m-%d"),
        "take_profit": tp,
        "stop_loss": sl,
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
        "position_sizing": "sentiment_based",
        "risk_per_trade_pct": 0.025,
        "max_safe_leverage": 5.0,
        "forward_trades": 0,
        "forward_wr": 0.0,
        "forward_validated": False,
        "elite_score": min(100, signal_strength * 25),
        "elite_grade": "A" if signal_strength >= 4 else "B" if signal_strength >= 3 else "C",
        "reason": f"OKX Futures Sentiment ({signal_strength} signals) | " + " | ".join(reasons),
        "source_system": "okx_futures_leaderboard",
        "signal_count": signal_strength,
        "long_short_ratio": ls.get("ratio"),
        "long_short_trend": ls.get("trend_1h"),
        "funding_rate": fr.get("rate"),
        "funding_rate_pct": fr.get("rate_pct"),
        "taker_buy_pct": tv.get("avg_buy_pct_1h"),
        "oi_change_1h_pct": oi.get("oi_change_1h_pct"),
        "mark_price": mark_price,
        "timestamp": now.isoformat(),
    }


def scan_okx_futures(coins: list = None) -> tuple:
    """
    Main scan: fetch market sentiment for top coins, generate picks.
    Returns (analysis_results, picks).
    """
    if coins is None:
        coins = SCAN_COINS

    print("=" * 70)
    print("  OKX FUTURES LEADERBOARD SENTIMENT SCRAPER")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  Scanning {len(coins)} coins: {', '.join(coins[:10])}...")
    print("=" * 70)

    all_analyses = []
    all_picks = []

    for i, ccy in enumerate(coins):
        inst_id = f"{ccy}-USDT-SWAP"
        print(f"  [{i+1}/{len(coins)}] {ccy:8s} ", end="", flush=True)

        # Fetch all data points
        ls_data = fetch_long_short_ratio(ccy)
        time.sleep(RATE_LIMIT_SEC)

        fr_data = fetch_funding_rate(inst_id)
        time.sleep(RATE_LIMIT_SEC)

        tv_data = fetch_taker_volume(ccy)
        time.sleep(RATE_LIMIT_SEC)

        mark_price = fetch_mark_price(inst_id)
        time.sleep(RATE_LIMIT_SEC)

        oi_data = fetch_open_interest_data(ccy)
        time.sleep(RATE_LIMIT_SEC)

        analysis = {
            "ccy": ccy,
            "inst_id": inst_id,
            "long_short": ls_data,
            "funding": fr_data,
            "taker_vol": tv_data,
            "oi": oi_data,
            "mark_price": mark_price,
        }
        all_analyses.append(analysis)

        # Summary line
        ls_str = f"L/S:{ls_data.get('ratio', '?')}" if ls_data else "L/S:N/A"
        fr_str = f"FR:{fr_data.get('rate_pct', '?')}%" if fr_data else "FR:N/A"
        tv_str = f"Buy:{tv_data.get('avg_buy_pct_1h', 0)*100:.0f}%" if tv_data else "TV:N/A"
        price_str = f"${mark_price:,.2f}" if mark_price > 0 else "N/A"

        # Generate pick if signals agree
        pick = generate_pick(ccy, analysis)
        if pick:
            all_picks.append(pick)
            dir_emoji = "LONG" if pick["direction"] == "LONG" else "SHORT"
            print(f"{price_str:>12s} {ls_str:>10s} {fr_str:>14s} {tv_str:>10s} -> {dir_emoji} (conf:{pick['confidence']:.2f})")
        else:
            print(f"{price_str:>12s} {ls_str:>10s} {fr_str:>14s} {tv_str:>10s} -> SKIP (no consensus)")

    print(f"\n  OKX Futures scan complete: {len(all_analyses)} coins analyzed, "
          f"{len(all_picks)} picks generated")
    return all_analyses, all_picks


def save_okx_futures_results(analyses: list, picks: list):
    """Save OKX futures results to data files."""
    now_iso = datetime.now(timezone.utc).isoformat()

    # Save analysis data
    analysis_path = DATA_DIR / "okx_futures_analysis.json"
    with open(analysis_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": now_iso,
            "source": "okx_futures_leaderboard",
            "coin_count": len(analyses),
            "analyses": analyses,
        }, f, indent=2, default=str)
    print(f"  Saved {len(analyses)} analyses to {analysis_path}")

    # Save picks
    picks_path = DATA_DIR / "okx_futures_picks.json"
    with open(picks_path, "w", encoding="utf-8") as f:
        json.dump(picks, f, indent=2, default=str)
    print(f"  Saved {len(picks)} picks to {picks_path}")

    return analysis_path, picks_path


if __name__ == "__main__":
    analyses, picks = scan_okx_futures()
    save_okx_futures_results(analyses, picks)
    print(f"\nDone. {len(picks)} OKX futures sentiment picks generated.")
