#!/usr/bin/env python3
"""
HTX (Huobi) Elite Trader Sentiment Scraper & Pick Generator
=============================================================
Uses HTX's public futures API (api.hbdm.com) to read elite trader
positioning and generate picks based on aggregate sentiment.

HTX does NOT have a public copy trading API with individual trader positions.
The copy trading page (htx.com/en-us/copy-trading/) is a JS SPA with no
public API endpoints for trader listings or positions.

HOWEVER, HTX provides excellent public "elite trader" APIs that show:
  - Elite Account Ratio: % of top accounts that are long/short/locked
  - Elite Position Ratio: % of top positions that are long/short
  - Open Interest: total OI per contract
  - Funding Rate (via premium index)

These are the same data feeds visible on the OKX "Futures Leaderboard"
but from HTX's perspective, giving us cross-exchange confirmation.

NO API KEY NEEDED - All endpoints are public.

Working endpoints (verified 2026-03-19):
  Elite Account Ratio:  GET /linear-swap-api/v1/swap_elite_account_ratio
  Elite Position Ratio: GET /linear-swap-api/v1/swap_elite_position_ratio
  Open Interest:        GET /linear-swap-api/v1/swap_open_interest
  Funding Rate:         GET /linear-swap-api/v1/swap_cross_funding_rate (or batch)

Strategy:
  1. Fetch elite account ratio (buy_ratio, sell_ratio, locked_ratio)
  2. Fetch elite position ratio (buy_ratio, sell_ratio)
  3. When elite accounts AND positions both strongly lean one way,
     generate a pick in that direction
  4. Cross-reference with OI changes for confirmation

API base: https://api.hbdm.com (HTX Futures / formerly Huobi DM)
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
HTX_API_MIRRORS = [
    "https://api.hbdm.com",
    "https://api.hbdm.vn",
    "https://futures.htx.com",
]

# Endpoints (linear swap = USDT-margined perpetuals)
ELITE_ACCOUNT_RATIO = "/linear-swap-api/v1/swap_elite_account_ratio"
ELITE_POSITION_RATIO = "/linear-swap-api/v1/swap_elite_position_ratio"
OPEN_INTEREST = "/linear-swap-api/v1/swap_open_interest"
FUNDING_RATE = "/linear-swap-api/v1/swap_batch_funding_rate"

# Top coins to scan (contract_code format: COIN-USDT)
SCAN_COINS = [
    "BTC-USDT", "ETH-USDT", "SOL-USDT", "XRP-USDT", "DOGE-USDT",
    "BNB-USDT", "ADA-USDT", "AVAX-USDT", "LINK-USDT", "DOT-USDT",
    "MATIC-USDT", "UNI-USDT", "NEAR-USDT", "FIL-USDT", "APT-USDT",
    "ARB-USDT", "OP-USDT", "PEPE-USDT", "WIF-USDT", "SUI-USDT",
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


def htx_get(path: str, params: dict = None, retries: int = 3) -> dict:
    """GET request to HTX futures API with mirror failover."""
    for mirror in HTX_API_MIRRORS:
        url = f"{mirror}{path}"
        for attempt in range(retries):
            try:
                resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("status") == "ok":
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


def fetch_elite_account_ratio(contract_code: str) -> dict:
    """
    Fetch elite account long/short ratio.
    Returns latest: {buy_ratio, sell_ratio, locked_ratio, bias}
    buy_ratio = fraction of elite accounts that are net long
    sell_ratio = fraction that are net short
    locked_ratio = fraction hedged/neutral
    """
    data = htx_get(ELITE_ACCOUNT_RATIO, params={
        "contract_code": contract_code,
        "period": "60min",
    })
    items = data.get("data", {}).get("list", [])
    if not items:
        return {}

    latest = items[-1]  # Sorted ascending by timestamp
    buy = latest.get("buy_ratio", 0)
    sell = latest.get("sell_ratio", 0)
    locked = latest.get("locked_ratio", 0)

    # Trend: compare with 4h ago (4 items back)
    trend = 0.0
    if len(items) >= 5:
        prev = items[-5]
        trend = buy - prev.get("buy_ratio", buy)

    # Strong bias threshold: >55% on one side
    if buy > 0.55:
        bias = "LONG"
    elif sell > 0.55:
        bias = "SHORT"
    elif buy > sell + 0.10:
        bias = "LEAN_LONG"
    elif sell > buy + 0.10:
        bias = "LEAN_SHORT"
    else:
        bias = "NEUTRAL"

    return {
        "buy_ratio": buy,
        "sell_ratio": sell,
        "locked_ratio": locked,
        "trend_4h": round(trend, 4),
        "bias": bias,
    }


def fetch_elite_position_ratio(contract_code: str) -> dict:
    """
    Fetch elite position long/short ratio.
    Similar to account ratio but weighted by position size.
    buy_ratio + sell_ratio = 1.0 (no locked category).
    """
    data = htx_get(ELITE_POSITION_RATIO, params={
        "contract_code": contract_code,
        "period": "60min",
    })
    items = data.get("data", {}).get("list", [])
    if not items:
        return {}

    latest = items[-1]
    buy = latest.get("buy_ratio", 0)
    sell = latest.get("sell_ratio", 0)

    # Trend
    trend = 0.0
    if len(items) >= 5:
        prev = items[-5]
        trend = buy - prev.get("buy_ratio", buy)

    # Position ratio bias (tighter thresholds since no locked category)
    if buy > 0.55:
        bias = "LONG"
    elif sell > 0.55:
        bias = "SHORT"
    elif buy > 0.52:
        bias = "LEAN_LONG"
    elif sell > 0.52:
        bias = "LEAN_SHORT"
    else:
        bias = "NEUTRAL"

    return {
        "buy_ratio": buy,
        "sell_ratio": sell,
        "trend_4h": round(trend, 4),
        "bias": bias,
    }


def fetch_open_interest(contract_code: str) -> dict:
    """Fetch current open interest for a contract."""
    data = htx_get(OPEN_INTEREST, params={"contract_code": contract_code})
    items = data.get("data", [])
    if not items:
        return {}

    item = items[0]
    return {
        "volume": item.get("volume", 0),
        "amount": item.get("amount", 0),
        "value_usd": item.get("value", 0),
        "trade_volume": item.get("trade_volume", 0),
        "trade_turnover": item.get("trade_turnover", 0),
    }


def fetch_all_funding_rates() -> dict:
    """
    Fetch funding rates for all contracts in one batch call.
    Returns dict of contract_code -> funding_rate.
    """
    data = htx_get(FUNDING_RATE)
    items = data.get("data", [])
    if not items:
        return {}

    rates = {}
    for item in items:
        code = item.get("contract_code", "")
        try:
            rate = float(item.get("funding_rate", 0))
        except (ValueError, TypeError):
            rate = 0.0
        if code:
            rates[code] = {
                "rate": rate,
                "rate_pct": round(rate * 100, 4),
                "bias": "SHORT" if rate > 0.0003 else "LONG" if rate < -0.0003 else "NEUTRAL",
            }
    return rates


def get_mark_price_from_binance(symbol: str) -> float:
    """Fallback: get mark price from Binance API (per project failover rules)."""
    binance_mirrors = [
        "https://api.binance.com",
        "https://api1.binance.com",
        "https://api2.binance.com",
    ]
    for mirror in binance_mirrors:
        try:
            resp = requests.get(
                f"{mirror}/api/v3/ticker/price",
                params={"symbol": symbol},
                timeout=5,
            )
            if resp.status_code == 200:
                return float(resp.json().get("price", 0))
        except Exception:
            continue
    return 0.0


def generate_pick(contract_code: str, analysis: dict) -> dict:
    """
    Generate a pick from HTX elite trader analysis.
    Requires elite accounts AND elite positions to agree on direction.
    """
    acct = analysis.get("elite_account", {})
    pos = analysis.get("elite_position", {})
    fr = analysis.get("funding_rate", {})
    mark_price = analysis.get("mark_price", 0)

    if mark_price <= 0:
        return None

    long_signals = 0
    short_signals = 0
    reasons = []

    # 1. Elite Account Ratio (strongest signal)
    acct_bias = acct.get("bias", "NEUTRAL")
    if acct_bias in ("LONG", "LEAN_LONG"):
        long_signals += 1
        reasons.append(f"Elite Accounts {acct.get('buy_ratio', 0)*100:.0f}% long")
        if acct_bias == "LONG":
            long_signals += 1  # Strong conviction = double weight
    elif acct_bias in ("SHORT", "LEAN_SHORT"):
        short_signals += 1
        reasons.append(f"Elite Accounts {acct.get('sell_ratio', 0)*100:.0f}% short")
        if acct_bias == "SHORT":
            short_signals += 1

    # 2. Elite Position Ratio
    pos_bias = pos.get("bias", "NEUTRAL")
    if pos_bias in ("LONG", "LEAN_LONG"):
        long_signals += 1
        reasons.append(f"Elite Positions {pos.get('buy_ratio', 0)*100:.0f}% long")
    elif pos_bias in ("SHORT", "LEAN_SHORT"):
        short_signals += 1
        reasons.append(f"Elite Positions {pos.get('sell_ratio', 0)*100:.0f}% short")

    # 3. Funding rate (confirming/contrarian)
    fr_bias = fr.get("bias", "NEUTRAL")
    if fr_bias == "LONG":  # Negative funding = go long
        long_signals += 1
        reasons.append(f"Funding {fr.get('rate_pct', 0):.4f}% (neg=bullish)")
    elif fr_bias == "SHORT":  # Positive funding = go short
        short_signals += 1
        reasons.append(f"Funding {fr.get('rate_pct', 0):.4f}% (pos=bearish)")

    # 4. Trend confirmation (bonus signal)
    acct_trend = acct.get("trend_4h", 0)
    pos_trend = pos.get("trend_4h", 0)
    if acct_trend > 0.03 and pos_trend > 0.01:
        long_signals += 1
        reasons.append("Rising long trend (4h)")
    elif acct_trend < -0.03 and pos_trend < -0.01:
        short_signals += 1
        reasons.append("Rising short trend (4h)")

    # Need 2+ signals in same direction
    if long_signals < 2 and short_signals < 2:
        return None

    if long_signals > short_signals:
        direction = "LONG"
        signal_strength = long_signals
    elif short_signals > long_signals:
        direction = "SHORT"
        signal_strength = short_signals
    else:
        return None

    confidence = round(min(0.90, 0.55 + signal_strength * 0.07), 3)

    # TP/SL
    if direction == "LONG":
        tp = round(mark_price * 1.035, 8)
        sl = round(mark_price * 0.975, 8)
    else:
        tp = round(mark_price * 0.965, 8)
        sl = round(mark_price * 1.025, 8)

    # Convert contract_code to symbol
    ccy = contract_code.replace("-USDT", "")
    symbol = f"{ccy}USDT"
    now = datetime.now(timezone.utc)
    pick_id = f"htx_elite_{ccy}::{now.strftime('%Y-%m-%d_%H%M')}"

    return {
        "id": pick_id,
        "strategy": f"htx_elite_{ccy.lower()}",
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
        "reason": (
            f"HTX Elite Sentiment ({signal_strength} signals) | "
            + " | ".join(reasons)
        ),
        "source_system": "htx_elite_sentiment",
        "signal_count": signal_strength,
        "elite_account_buy": acct.get("buy_ratio"),
        "elite_account_sell": acct.get("sell_ratio"),
        "elite_position_buy": pos.get("buy_ratio"),
        "elite_position_sell": pos.get("sell_ratio"),
        "funding_rate": fr.get("rate"),
        "funding_rate_pct": fr.get("rate_pct"),
        "mark_price": mark_price,
        "timestamp": now.isoformat(),
    }


def scan_htx_elite(coins: list = None) -> tuple:
    """
    Main scan: fetch elite trader sentiment for top coins, generate picks.
    Returns (analysis_results, picks).
    """
    if coins is None:
        coins = SCAN_COINS

    print("=" * 70)
    print("  HTX (HUOBI) ELITE TRADER SENTIMENT SCRAPER")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  Scanning {len(coins)} coins via api.hbdm.com")
    print("=" * 70)

    # Batch fetch funding rates (one API call for all)
    print("  Fetching funding rates (batch)...")
    all_funding_rates = fetch_all_funding_rates()
    if all_funding_rates:
        print(f"  Got funding rates for {len(all_funding_rates)} contracts")
    else:
        print("  [WARN] Batch funding rate fetch failed, will skip funding signal")

    all_analyses = []
    all_picks = []

    for i, contract_code in enumerate(coins):
        ccy = contract_code.replace("-USDT", "")
        print(f"  [{i+1}/{len(coins)}] {ccy:8s} ", end="", flush=True)

        # Fetch elite account ratio
        acct_data = fetch_elite_account_ratio(contract_code)
        time.sleep(RATE_LIMIT_SEC)

        # Fetch elite position ratio
        pos_data = fetch_elite_position_ratio(contract_code)
        time.sleep(RATE_LIMIT_SEC)

        # Get OI data
        oi_data = fetch_open_interest(contract_code)
        time.sleep(RATE_LIMIT_SEC)

        # Get mark price from Binance (HTX doesn't expose mark price easily)
        symbol = f"{ccy}USDT"
        mark_price = get_mark_price_from_binance(symbol)

        # Funding rate from batch data
        fr_data = all_funding_rates.get(contract_code, {})

        analysis = {
            "contract_code": contract_code,
            "ccy": ccy,
            "elite_account": acct_data,
            "elite_position": pos_data,
            "funding_rate": fr_data,
            "open_interest": oi_data,
            "mark_price": mark_price,
        }
        all_analyses.append(analysis)

        # Summary line
        acct_str = (
            f"Acct:{acct_data.get('buy_ratio', 0)*100:.0f}L/{acct_data.get('sell_ratio', 0)*100:.0f}S"
            if acct_data else "Acct:N/A"
        )
        pos_str = (
            f"Pos:{pos_data.get('buy_ratio', 0)*100:.0f}L/{pos_data.get('sell_ratio', 0)*100:.0f}S"
            if pos_data else "Pos:N/A"
        )
        price_str = f"${mark_price:,.2f}" if mark_price > 0 else "N/A"

        pick = generate_pick(contract_code, analysis)
        if pick:
            all_picks.append(pick)
            print(f"{price_str:>12s} {acct_str:>14s} {pos_str:>12s} -> {pick['direction']} (conf:{pick['confidence']:.2f})")
        else:
            print(f"{price_str:>12s} {acct_str:>14s} {pos_str:>12s} -> SKIP (no consensus)")

    print(f"\n  HTX Elite scan complete: {len(all_analyses)} coins analyzed, "
          f"{len(all_picks)} picks generated")
    return all_analyses, all_picks


def save_htx_results(analyses: list, picks: list):
    """Save HTX results to data files."""
    now_iso = datetime.now(timezone.utc).isoformat()

    analysis_path = DATA_DIR / "htx_elite_analysis.json"
    with open(analysis_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": now_iso,
            "source": "htx_elite_sentiment",
            "api_base": HTX_API_MIRRORS[0],
            "coin_count": len(analyses),
            "analyses": analyses,
        }, f, indent=2, default=str)
    print(f"  Saved {len(analyses)} analyses to {analysis_path}")

    picks_path = DATA_DIR / "htx_picks.json"
    with open(picks_path, "w", encoding="utf-8") as f:
        json.dump(picks, f, indent=2, default=str)
    print(f"  Saved {len(picks)} picks to {picks_path}")

    return analysis_path, picks_path


if __name__ == "__main__":
    analyses, picks = scan_htx_elite()
    save_htx_results(analyses, picks)
    print(f"\nDone. {len(picks)} HTX elite sentiment picks generated.")
