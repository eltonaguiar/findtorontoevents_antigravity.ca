#!/usr/bin/env python3
"""
Fast Stocks Competition - Real Market Data Scanner (Pandas-Free)
Fetches real price data from Yahoo Finance v8 API.
Scans 20 S&P 500 stocks with 4 short-term strategies.
"""

import json
import math
import sys
import time
import requests
from datetime import datetime, timedelta, timezone
from pathlib import Path

# 20 S&P 500 stocks to scan
TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "JPM", "V", "UNH",
    "HD", "JNJ", "PG", "MA", "XOM", "CVX", "ABBV", "MRK", "PEP", "KO",
]

MAX_ACTIVE_PICKS = 8

# Algorithm configurations
ALGO_CONFIGS = {
    "Breakout Momentum": {
        "strategy": "20d high breakout + volume",
        "hold_days": 10,
        "tp_pct": 0.05,
        "sl_pct": 0.04,
    },
    "Bollinger Mean Reversion": {
        "strategy": "Lower BB touch + RSI<35",
        "hold_days": 5,
        "tp_pct": 0.04,
        "sl_pct": 0.03,
    },
    "Short-Term Reversal": {
        "strategy": "3+ down days + RSI<30 bounce",
        "hold_days": 3,
        "tp_pct": 0.03,
        "sl_pct": 0.02,
    },
    "ML Ranker": {
        "strategy": "Composite RSI + momentum + volume score",
        "hold_days": 7,
        "tp_pct": 0.05,
        "sl_pct": 0.03,
    },
}

YAHOO_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=60d&interval=1d"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
REQUEST_DELAY = 0.5  # seconds between Yahoo requests


def utcnow():
    """Current UTC datetime."""
    return datetime.now(timezone.utc)


def fetch_yahoo_data(symbol):
    """Fetch OHLCV data from Yahoo Finance v8 API. Returns list of dicts or None."""
    url = YAHOO_URL.format(symbol=symbol)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        result = data["chart"]["result"][0]
        timestamps = result["timestamp"]
        quote = result["indicators"]["quote"][0]

        bars = []
        for i, ts in enumerate(timestamps):
            o = quote["open"][i]
            h = quote["high"][i]
            l = quote["low"][i]
            c = quote["close"][i]
            v = quote["volume"][i]
            if c is None or v is None:
                continue
            bars.append({
                "date": datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d"),
                "open": round(o, 4) if o else None,
                "high": round(h, 4) if h else None,
                "low": round(l, 4) if l else None,
                "close": round(c, 4),
                "volume": int(v) if v else 0,
            })
        return bars if len(bars) >= 20 else None
    except Exception as e:
        print(f"  [WARN] Failed to fetch {symbol}: {e}")
        return None


def compute_indicators(bars):
    """Compute RSI-14, SMA-20, Bollinger Bands, volume averages from bar list."""
    closes = [b["close"] for b in bars]
    volumes = [b["volume"] for b in bars]
    highs = [b["high"] for b in bars if b["high"] is not None]

    n = len(closes)
    if n < 20:
        return None

    # Current price
    price = closes[-1]

    # SMA-20
    sma20 = sum(closes[-20:]) / 20.0

    # 20-day high
    high_20d = max(highs[-20:]) if len(highs) >= 20 else max(highs)

    # Bollinger Bands (20-period, 2 std)
    mean20 = sma20
    variance = sum((x - mean20) ** 2 for x in closes[-20:]) / 20.0
    std20 = math.sqrt(variance)
    bb_upper = mean20 + 2 * std20
    bb_lower = mean20 - 2 * std20

    # RSI-14
    rsi = _compute_rsi(closes, 14)

    # Volume average (20d)
    vol_avg_20 = sum(volumes[-20:]) / 20.0 if len(volumes) >= 20 else sum(volumes) / len(volumes)
    vol_current = volumes[-1]
    vol_ratio = vol_current / vol_avg_20 if vol_avg_20 > 0 else 1.0

    # Consecutive down days
    down_days = 0
    for i in range(len(closes) - 1, 0, -1):
        if closes[i] < closes[i - 1]:
            down_days += 1
        else:
            break

    # 5-day momentum (percent)
    mom_5d = (closes[-1] / closes[-6] - 1) * 100 if n >= 6 else 0.0

    # 10-day momentum
    mom_10d = (closes[-1] / closes[-11] - 1) * 100 if n >= 11 else 0.0

    return {
        "price": price,
        "sma20": sma20,
        "high_20d": high_20d,
        "bb_upper": bb_upper,
        "bb_lower": bb_lower,
        "bb_mid": mean20,
        "std20": std20,
        "rsi": rsi,
        "vol_ratio": vol_ratio,
        "vol_avg_20": vol_avg_20,
        "down_days": down_days,
        "mom_5d": mom_5d,
        "mom_10d": mom_10d,
    }


def _compute_rsi(closes, period=14):
    """Wilder RSI."""
    if len(closes) < period + 1:
        return 50.0  # neutral default
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [max(d, 0) for d in deltas]
    losses = [max(-d, 0) for d in deltas]

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100.0 - 100.0 / (1.0 + rs), 2)


# ---------------------------------------------------------------------------
# Strategy signal generators
# ---------------------------------------------------------------------------

def signal_breakout_momentum(ticker, ind):
    """Breakout Momentum: price breaks 20d high with volume confirmation."""
    price = ind["price"]
    high_20d = ind["high_20d"]
    vol_ratio = ind["vol_ratio"]
    rsi = ind["rsi"]

    score = 0
    reasons = []

    # Primary: price broke or is within 1% of 20d high
    if price >= high_20d:
        score += 35
        reasons.append("Price broke 20d high")
    elif price >= high_20d * 0.99:
        score += 20
        reasons.append("Price within 1% of 20d high")

    # Volume confirmation
    if vol_ratio >= 1.5:
        score += 25
        reasons.append(f"Volume {vol_ratio:.1f}x average")
    elif vol_ratio >= 1.2:
        score += 15
        reasons.append(f"Volume {vol_ratio:.1f}x average")

    # Trend filter: price above SMA-20
    if price > ind["sma20"]:
        score += 10
        reasons.append("Above 20-SMA")

    # RSI not overbought filter
    if 50 < rsi < 75:
        score += 10
        reasons.append(f"RSI {rsi:.0f} — bullish but not overbought")

    return score, reasons


def signal_bollinger_mean_reversion(ticker, ind):
    """Bollinger Mean Reversion: price near lower BB with RSI<35."""
    price = ind["price"]
    bb_lower = ind["bb_lower"]
    rsi = ind["rsi"]

    score = 0
    reasons = []

    # Price at or below lower BB
    if price <= bb_lower:
        score += 35
        reasons.append(f"Price below lower Bollinger Band (${bb_lower:.2f})")
    elif price <= bb_lower * 1.01:
        score += 25
        reasons.append(f"Price within 1% of lower BB (${bb_lower:.2f})")

    # RSI oversold
    if rsi < 30:
        score += 30
        reasons.append(f"RSI {rsi:.0f} — deeply oversold")
    elif rsi < 35:
        score += 20
        reasons.append(f"RSI {rsi:.0f} — oversold")

    # Volume spike (capitulation sign)
    if ind["vol_ratio"] >= 1.3:
        score += 10
        reasons.append(f"Volume spike {ind['vol_ratio']:.1f}x avg")

    return score, reasons


def signal_short_term_reversal(ticker, ind):
    """Short-Term Reversal: 3+ consecutive down days with RSI<30."""
    down_days = ind["down_days"]
    rsi = ind["rsi"]
    price = ind["price"]

    score = 0
    reasons = []

    # Consecutive down days
    if down_days >= 5:
        score += 35
        reasons.append(f"{down_days} consecutive down days — extreme selling")
    elif down_days >= 4:
        score += 30
        reasons.append(f"{down_days} consecutive down days")
    elif down_days >= 3:
        score += 25
        reasons.append(f"{down_days} consecutive down days")

    # RSI deeply oversold
    if rsi < 25:
        score += 30
        reasons.append(f"RSI {rsi:.0f} — extreme oversold")
    elif rsi < 30:
        score += 25
        reasons.append(f"RSI {rsi:.0f} — oversold")

    # Near lower BB adds confluence
    if price <= ind["bb_lower"] * 1.02:
        score += 10
        reasons.append("Near lower Bollinger Band")

    return score, reasons


def signal_ml_ranker(ticker, ind):
    """ML Ranker: composite score of RSI + momentum + volume."""
    rsi = ind["rsi"]
    mom_5d = ind["mom_5d"]
    mom_10d = ind["mom_10d"]
    vol_ratio = ind["vol_ratio"]
    price = ind["price"]
    sma20 = ind["sma20"]

    score = 0
    reasons = []

    # RSI component (favor mild oversold or neutral-bullish)
    if 30 <= rsi <= 45:
        score += 20
        reasons.append(f"RSI {rsi:.0f} — recovery zone")
    elif 45 < rsi < 65:
        score += 15
        reasons.append(f"RSI {rsi:.0f} — neutral-bullish")
    elif rsi < 30:
        score += 25
        reasons.append(f"RSI {rsi:.0f} — oversold bounce candidate")

    # Momentum component
    if mom_5d > 2:
        score += 15
        reasons.append(f"5d momentum +{mom_5d:.1f}%")
    elif mom_5d > 0:
        score += 10
        reasons.append(f"5d momentum +{mom_5d:.1f}%")

    if mom_10d > 0 and price > sma20:
        score += 10
        reasons.append("10d uptrend + above SMA-20")

    # Volume component
    if vol_ratio > 1.5:
        score += 15
        reasons.append(f"High volume ({vol_ratio:.1f}x avg)")
    elif vol_ratio > 1.1:
        score += 10
        reasons.append(f"Above-avg volume ({vol_ratio:.1f}x)")

    # Bollinger position (buy near mid-to-lower)
    bb_pos = (price - ind["bb_lower"]) / (ind["bb_upper"] - ind["bb_lower"]) if ind["bb_upper"] != ind["bb_lower"] else 0.5
    if 0.2 <= bb_pos <= 0.5:
        score += 10
        reasons.append(f"BB position {bb_pos:.0%} — value zone")

    return score, reasons


SIGNAL_FUNCS = {
    "Breakout Momentum": signal_breakout_momentum,
    "Bollinger Mean Reversion": signal_bollinger_mean_reversion,
    "Short-Term Reversal": signal_short_term_reversal,
    "ML Ranker": signal_ml_ranker,
}


# ---------------------------------------------------------------------------
# Pick resolution
# ---------------------------------------------------------------------------

def resolve_existing_picks(picks, current_prices):
    """Check TP/SL/expiry for open picks using current prices."""
    now = utcnow()
    today = now.date()
    resolved_count = 0

    for pick in picks:
        if pick.get("status") != "OPEN":
            continue

        ticker = pick.get("symbol") or pick.get("ticker")
        current = current_prices.get(ticker)
        if current is None:
            continue

        tp = pick.get("tp_price")
        sl = pick.get("sl_price")
        expiry_str = pick.get("expiry_date", "")

        # Parse expiry
        try:
            if "T" in expiry_str:
                expiry_date = datetime.fromisoformat(expiry_str.replace("Z", "+00:00")).date()
            else:
                expiry_date = datetime.strptime(expiry_str[:10], "%Y-%m-%d").date()
        except Exception:
            expiry_date = today + timedelta(days=30)

        reason = None
        pnl = None
        entry = pick.get("entry_price", 0)

        if tp and current >= tp:
            reason = "TP_HIT"
            pnl = round((tp / entry - 1) * 100, 2) if entry else None
        elif sl and current <= sl:
            reason = "SL_HIT"
            pnl = round((sl / entry - 1) * 100, 2) if entry else None
        elif expiry_date <= today:
            reason = "EXPIRED"
            pnl = round((current / entry - 1) * 100, 2) if entry else None

        if reason:
            pick["status"] = reason
            pick["resolved_at"] = now.isoformat()
            pick["pnl_pct"] = pnl
            resolved_count += 1

    return resolved_count


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_fast_competition():
    now = utcnow()
    now_iso = now.isoformat()
    today_str = now.strftime("%Y%m%d")
    hour_str = now.strftime("%H%M")

    print(f"Fast Stocks Competition - Real Market Data")
    print(f"Time: {now_iso}")
    print(f"Tickers: {len(TICKERS)} | Algorithms: {len(ALGO_CONFIGS)}")
    print()

    # ------------------------------------------------------------------
    # 1. Fetch real market data from Yahoo Finance
    # ------------------------------------------------------------------
    print("Fetching real market data from Yahoo Finance...")
    market_data = {}  # ticker -> list of bars
    indicators = {}   # ticker -> indicator dict
    current_prices = {}

    for i, ticker in enumerate(TICKERS):
        if i > 0:
            time.sleep(REQUEST_DELAY)
        bars = fetch_yahoo_data(ticker)
        if bars is None:
            print(f"  {ticker}: SKIP (no data)")
            continue
        market_data[ticker] = bars
        ind = compute_indicators(bars)
        if ind is None:
            print(f"  {ticker}: SKIP (insufficient bars)")
            continue
        indicators[ticker] = ind
        current_prices[ticker] = ind["price"]
        print(f"  {ticker}: ${ind['price']:.2f}  RSI={ind['rsi']:.0f}  Vol={ind['vol_ratio']:.1f}x")

    print(f"\nGot data for {len(indicators)}/{len(TICKERS)} tickers")

    # ------------------------------------------------------------------
    # 2. Load existing picks and resolve TP/SL/expiry
    # ------------------------------------------------------------------
    picks_file = Path(__file__).parent / "fast_forward_picks.json"
    existing_picks = []
    if picks_file.exists():
        try:
            with open(picks_file, "r") as f:
                data = json.load(f)
                existing_picks = data.get("picks", [])
        except Exception:
            existing_picks = []

    resolved = resolve_existing_picks(existing_picks, current_prices)
    if resolved:
        print(f"Resolved {resolved} existing pick(s) (TP/SL/expiry)")

    # Count currently open picks
    open_picks = [p for p in existing_picks if p.get("status") == "OPEN"]
    slots_available = MAX_ACTIVE_PICKS - len(open_picks)
    print(f"Open picks: {len(open_picks)} / {MAX_ACTIVE_PICKS} max  |  Slots available: {max(0, slots_available)}")

    # ------------------------------------------------------------------
    # 3. Generate new signals
    # ------------------------------------------------------------------
    print("\nGenerating signals...")
    candidates = []

    for algo_name, algo_cfg in ALGO_CONFIGS.items():
        func = SIGNAL_FUNCS[algo_name]
        for ticker in indicators:
            # Skip if we already have an open pick for same algo+ticker
            dup = any(
                p.get("status") == "OPEN"
                and (p.get("symbol") or p.get("ticker")) == ticker
                and p.get("algorithm") == algo_name
                for p in existing_picks
            )
            if dup:
                continue

            score, reasons = func(ticker, indicators[ticker])
            if score >= 50:  # minimum threshold
                candidates.append((score, algo_name, ticker, reasons))

    # Sort by score descending, take top N to fill available slots
    candidates.sort(key=lambda x: x[0], reverse=True)
    new_picks = []

    for score, algo_name, ticker, reasons in candidates:
        if len(new_picks) >= max(0, slots_available):
            break

        cfg = ALGO_CONFIGS[algo_name]
        price = indicators[ticker]["price"]
        tp_price = round(price * (1 + cfg["tp_pct"]), 2)
        sl_price = round(price * (1 - cfg["sl_pct"]), 2)
        expiry = now + timedelta(days=cfg["hold_days"])
        confidence = round(min(score / 100.0, 0.95), 2)

        pick = {
            "id": f"fast_stock_{ticker}_{today_str}_{hour_str}",
            "system": "fast_stocks_competition",
            "algorithm": algo_name,
            "strategy": cfg["strategy"],
            "asset_class": "EQUITY",
            "ticker": ticker,
            "symbol": ticker,
            "action": "BUY",
            "direction": "LONG",
            "entry_price": round(price, 2),
            "tp_price": tp_price,
            "sl_price": sl_price,
            "confidence": confidence,
            "score": score,
            "reasons": reasons,
            "timestamp": now_iso,
            "generated_at": now_iso,
            "expiry_date": expiry.isoformat(),
            "hold_days_max": cfg["hold_days"],
            "status": "OPEN",
            "resolved_at": None,
            "pnl_pct": None,
        }
        new_picks.append(pick)
        print(f"  NEW: {algo_name} | {ticker} @ ${price:.2f} | score={score} | TP=${tp_price:.2f} SL=${sl_price:.2f}")

    # ------------------------------------------------------------------
    # 4. Merge and save
    # ------------------------------------------------------------------
    all_picks = existing_picks + new_picks

    output = {
        "generated_at": now_iso,
        "system": "fast_stocks_competition",
        "picks": all_picks,
    }

    with open(picks_file, "w") as f:
        json.dump(output, f, indent=2)

    # Summary
    final_open = sum(1 for p in all_picks if p.get("status") == "OPEN")
    final_resolved = sum(1 for p in all_picks if p.get("status") != "OPEN")
    print(f"\nSummary:")
    print(f"  New picks generated: {len(new_picks)}")
    print(f"  Total open: {final_open}")
    print(f"  Total resolved: {final_resolved}")
    print(f"  Saved to: {picks_file}")


if __name__ == "__main__":
    run_fast_competition()
