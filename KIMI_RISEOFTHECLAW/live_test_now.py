#!/usr/bin/env python3
"""
ANTIGRAVITY_FEB172026 — LIVE MARKET TEST (Run NOW)
===================================================
Real-time crypto + forex signal generation using:
  - Binance public API (orderbook, trades, futures klines, funding rates)
  - CoinGecko Pro API (trending, global market data)
  - CryptoCompare API (multi-exchange price, social stats)
  - CurrencyLayer API (live forex rates)
  - yfinance daily OHLCV

Generates BUY signals with TP/SL levels for immediate forward testing.
Run: python live_test_now.py
"""

import json
import time
import sys
import os
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# API KEYS
# ---------------------------------------------------------------------------
COINGECKO_KEY = os.getenv('COINGECKO_API_KEY', '')
CRYPTOCOMPARE_KEY = os.getenv('CRYPTOCOMPARE_API_KEY', '')
COINDESK_KEY = os.getenv('COINDESK_API_KEY', '')
CRYPTOSCAN_KEY = os.getenv('CRYPTOSCAN_API_KEY', '')
CURRENCYLAYER_KEY = os.getenv('CURRENCY_LAYER_API_KEY', '')

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"

# ---------------------------------------------------------------------------
# API Fetchers with real keys
# ---------------------------------------------------------------------------

import requests
import warnings
warnings.filterwarnings("ignore")

BINANCE_BASE = "https://api.binance.com"
BINANCE_FUTURES = "https://fapi.binance.com"

YF_TO_BINANCE = {
    "BTC-USD": "BTCUSDT",  "ETH-USD": "ETHUSDT",  "SOL-USD": "SOLUSDT",
    "BNB-USD": "BNBUSDT",  "AVAX-USD": "AVAXUSDT", "XRP-USD": "XRPUSDT",
    "ADA-USD": "ADAUSDT",  "DOGE-USD": "DOGEUSDT", "SHIB-USD": "SHIBUSDT",
    "MATIC-USD": "MATICUSDT", "LINK-USD": "LINKUSDT", "DOT-USD": "DOTUSDT",
    "ATOM-USD": "ATOMUSDT", "NEAR-USD": "NEARUSDT", "LTC-USD": "LTCUSDT",
    "BCH-USD": "BCHUSDT",  "PEPE-USD": "PEPEUSDT", "INJ-USD": "INJUSDT",
    "TIA-USD": "TIAUSDT",  "OP-USD":   "OPUSDT",   "ARB11841-USD": "ARBUSDT",
    "SUI20947-USD": "SUIUSDT", "SEI-USD": "SEIUSDT", "FIL-USD": "FILUSDT",
    "APT21794-USD": "APTUSDT", "BONK-USD": "BONKUSDT", "FLOKI-USD": "FLOKIUSDT",
    "WIF-USD": "WIFUSDT",
}

# Forex pairs
FOREX_PAIRS = {
    "EURUSD": "EUR/USD", "GBPUSD": "GBP/USD", "USDJPY": "USD/JPY",
    "AUDUSD": "AUD/USD", "USDCAD": "USD/CAD", "NZDUSD": "NZD/USD",
    "USDCHF": "USD/CHF", "EURGBP": "EUR/GBP",
}

# All crypto symbols to scan
CRYPTO_SYMBOLS = [
    "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD",
    "ADA-USD", "AVAX-USD", "DOT-USD", "LINK-USD", "MATIC-USD",
    "DOGE-USD", "SHIB-USD", "ATOM-USD", "NEAR-USD", "LTC-USD",
    "BCH-USD", "INJ-USD", "OP-USD", "ARB11841-USD", "SUI20947-USD",
    "PEPE-USD", "BONK-USD", "FLOKI-USD", "WIF-USD", "TIA-USD",
    "FIL-USD", "SEI-USD", "APT21794-USD",
]


def _rsi(close, period=14):
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0).rolling(window=period, min_periods=period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window=period, min_periods=period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


# ═══════════════════════════════════════════════════════════════════════════
# 1. BINANCE: Order Book Imbalance
# ═══════════════════════════════════════════════════════════════════════════

def fetch_order_books():
    """Fetch order book depth for all crypto pairs."""
    print("\n📊 Fetching Binance order books...")
    results = {}
    for yf_sym, bn_sym in YF_TO_BINANCE.items():
        try:
            data = None
            for base in [BINANCE_BASE] + BINANCE_FALLBACK_URLS:
                try:
                    resp = requests.get(f"{base}/api/v3/depth",
                                        params={"symbol": bn_sym, "limit": 20}, timeout=5)
                    if resp.status_code == 200:
                        data = resp.json()
                        break
                except Exception:
                    continue
            if data is None:
                continue
            bid_vol = sum(float(b[1]) * float(b[0]) for b in data.get("bids", []))
            ask_vol = sum(float(a[1]) * float(a[0]) for a in data.get("asks", []))
            ratio = bid_vol / ask_vol if ask_vol > 0 else 1.0
            results[yf_sym] = {
                "bid_usd": round(bid_vol),
                "ask_usd": round(ask_vol),
                "ratio": round(ratio, 3),
                "signal": "🟢 BULLISH" if ratio > 2.0 else ("🔴 BEARISH" if ratio < 0.5 else "⚪ neutral"),
            }
        except Exception:
            continue
        time.sleep(0.1)  # Rate limit
    return results


# ═══════════════════════════════════════════════════════════════════════════
# 2. BINANCE: Real-time Prices + 24h Ticker
# ═══════════════════════════════════════════════════════════════════════════

def fetch_binance_tickers():
    """Fetch 24h ticker stats for all crypto pairs."""
    print("📈 Fetching Binance 24h tickers...")
    results = {}
    # Binance with fallback URLs for 24h ticker
    for base in [BINANCE_BASE] + BINANCE_FALLBACK_URLS:
        try:
            resp = requests.get(f"{base}/api/v3/ticker/24hr", timeout=10)
            if resp.status_code == 200:
                all_tickers = resp.json()
                bn_to_yf = {v: k for k, v in YF_TO_BINANCE.items()}
                for t in all_tickers:
                    sym = t["symbol"]
                    yf_sym = bn_to_yf.get(sym)
                    if yf_sym:
                        results[yf_sym] = {
                            "price": float(t["lastPrice"]),
                            "change_24h_pct": float(t["priceChangePercent"]),
                            "volume_usd": float(t["quoteVolume"]),
                            "high_24h": float(t["highPrice"]),
                            "low_24h": float(t["lowPrice"]),
                            "trades": int(t["count"]),
                        }
                break
        except Exception as e:
            print(f"  ❌ Binance ticker error: {e}")
    return results


# ═══════════════════════════════════════════════════════════════════════════
# 3. BINANCE: Whale Detection (Large Trades)
# ═══════════════════════════════════════════════════════════════════════════

def fetch_whale_trades(yf_sym, min_usd=100_000):
    """Detect large trades for a specific pair."""
    bn_sym = YF_TO_BINANCE.get(yf_sym)
    if not bn_sym:
        return {}
    try:
        # Binance with fallback URLs for trades
        data = None
        for base in [BINANCE_BASE] + BINANCE_FALLBACK_URLS:
            try:
                resp = requests.get(f"{base}/api/v3/trades",
                                    params={"symbol": bn_sym, "limit": 500}, timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    break
            except Exception:
                continue
        if data is None:
            return {}
        trades = data
        buy_usd = sell_usd = 0.0
        whale_count = 0
        for t in trades:
            usd = float(t["price"]) * float(t["qty"])
            if usd >= min_usd:
                whale_count += 1
                if not t.get("isBuyerMaker", True):
                    buy_usd += usd
                else:
                    sell_usd += usd
        total = buy_usd + sell_usd
        net = (buy_usd - sell_usd) / total if total > 0 else 0
        return {
            "whale_trades": whale_count,
            "buy_usd": round(buy_usd),
            "sell_usd": round(sell_usd),
            "net_direction": round(net, 3),
            "signal": "🐋 ACCUMULATION" if net > 0.3 else ("📉 DISTRIBUTION" if net < -0.3 else "mixed"),
        }
    except Exception:
        return {}


# ═══════════════════════════════════════════════════════════════════════════
# 4. BINANCE: Funding Rates (Futures)
# ═══════════════════════════════════════════════════════════════════════════

def fetch_all_funding_rates():
    """Fetch funding rates for all tracked crypto pairs."""
    print("💰 Fetching Binance funding rates...")
    results = {}
    for yf_sym, bn_sym in YF_TO_BINANCE.items():
        try:
            resp = requests.get(f"{BINANCE_FUTURES}/fapi/v1/fundingRate",
                                params={"symbol": bn_sym, "limit": 3}, timeout=5)
            if resp.status_code != 200:
                continue
            rates = [float(r["fundingRate"]) for r in resp.json()]
            latest = rates[-1] if rates else 0
            prev = rates[-2] if len(rates) >= 2 else latest
            results[yf_sym] = {
                "current_rate": round(latest * 100, 4),
                "prev_rate": round(prev * 100, 4),
                "direction": "negative→positive" if prev < 0 and latest >= 0 else
                             "positive→negative" if prev >= 0 and latest < 0 else "stable",
                "signal": "🟢 CONTRARIAN BUY" if latest < -0.01 else
                          ("🔴 OVERHEATED" if latest > 0.05 else "neutral"),
            }
        except Exception:
            continue
        time.sleep(0.05)
    return results


# ═══════════════════════════════════════════════════════════════════════════
# 5. COINGECKO PRO: Trending + Global Market Data
# ═══════════════════════════════════════════════════════════════════════════

def fetch_coingecko_data():
    """Fetch trending coins and global market data using Pro API key."""
    print("🦎 Fetching CoinGecko Pro data...")
    headers = {"x-cg-pro-api-key": COINGECKO_KEY}
    cg_base = "https://pro-api.coingecko.com/api/v3"

    trending = []
    global_data = {}

    for _attempt in range(3):
        try:
            resp = requests.get(f"{cg_base}/search/trending", headers=headers, timeout=10)
            if resp.status_code == 200:
                raw = resp.json()
                # Handle both dict {"coins": [...]} and unexpected list format
                if isinstance(raw, dict):
                    coins = raw.get("coins", [])
                elif isinstance(raw, list):
                    coins = raw
                else:
                    coins = []
                for c in coins:
                    item = c.get("item", {}) if isinstance(c, dict) else {}
                    trending.append({
                        "name": item.get("name", ""),
                        "symbol": item.get("symbol", "").upper(),
                        "market_cap_rank": item.get("market_cap_rank"),
                        "price_btc": item.get("price_btc", 0),
                    })
                break
            if _attempt < 2:
                time.sleep(2 * (_attempt + 1))
        except Exception as e:
            if _attempt == 2:
                print(f"  CoinGecko trending error after 3 attempts: {e}")
            else:
                time.sleep(2 * (_attempt + 1))

    for _attempt in range(3):
        try:
            resp = requests.get(f"{cg_base}/global", headers=headers, timeout=10)
            if resp.status_code == 200:
                gd = resp.json().get("data", {})
                global_data = {
                    "total_market_cap_usd": round(gd.get("total_market_cap", {}).get("usd", 0) / 1e9, 1),
                    "total_volume_24h_usd": round(gd.get("total_volume", {}).get("usd", 0) / 1e9, 1),
                    "btc_dominance": round(gd.get("market_cap_percentage", {}).get("btc", 0), 1),
                    "eth_dominance": round(gd.get("market_cap_percentage", {}).get("eth", 0), 1),
                    "market_cap_change_24h": round(gd.get("market_cap_change_percentage_24h_usd", 0), 2),
                    "active_cryptocurrencies": gd.get("active_cryptocurrencies", 0),
                }
                break
            if _attempt < 2:
                time.sleep(2 * (_attempt + 1))
        except Exception as e:
            if _attempt == 2:
                print(f"  CoinGecko global error after 3 attempts: {e}")
            else:
                time.sleep(2 * (_attempt + 1))

    return trending, global_data


# ═══════════════════════════════════════════════════════════════════════════
# 6. CRYPTOCOMPARE: Multi-Exchange Prices + Social Stats
# ═══════════════════════════════════════════════════════════════════════════

def fetch_cryptocompare_data():
    """Fetch cross-exchange price data and social stats."""
    print("🔄 Fetching CryptoCompare data...")
    headers = {"Authorization": f"Apikey {CRYPTOCOMPARE_KEY}"}
    results = {}

    symbols_to_check = ["BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "AVAX",
                         "DOGE", "LINK", "DOT", "ATOM", "NEAR", "LTC", "INJ"]

    # Multi-exchange price comparison
    try:
        for sym in symbols_to_check:
            resp = requests.get("https://min-api.cryptocompare.com/data/generateAvg",
                                params={"fsym": sym, "tsym": "USD",
                                         "e": "Binance,Coinbase,Kraken,Bitfinex,Bybit"},
                                headers=headers, timeout=5)
            if resp.status_code == 200:
                data = resp.json().get("RAW", {})
                if data:
                    results[f"{sym}-USD"] = {
                        "avg_price": round(float(data.get("PRICE", 0)), 4),
                        "volume_24h": round(float(data.get("VOLUME24HOUR", 0)), 2),
                        "change_24h_pct": round(float(data.get("CHANGEPCT24HOUR", 0)), 2),
                        "high_24h": round(float(data.get("HIGH24HOUR", 0)), 4),
                        "low_24h": round(float(data.get("LOW24HOUR", 0)), 4),
                        "open": round(float(data.get("OPEN24HOUR", 0)), 4),
                    }
            time.sleep(0.1)
    except Exception as e:
        print(f"  CryptoCompare price error: {e}")

    # Social stats for top coins
    try:
        for sym in symbols_to_check[:5]:
            resp = requests.get("https://min-api.cryptocompare.com/data/social/coin/latest",
                                params={"coinId": sym},
                                headers=headers, timeout=5)
            if resp.status_code == 200:
                sdata = resp.json().get("Data", {})
                twitter = sdata.get("Twitter", {})
                reddit = sdata.get("Reddit", {})
                key = f"{sym}-USD"
                if key in results:
                    results[key]["twitter_followers"] = twitter.get("followers", 0)
                    results[key]["reddit_subscribers"] = reddit.get("subscribers", 0)
                    results[key]["reddit_active_users"] = reddit.get("active_users", 0)
    except Exception as e:
        print(f"  CryptoCompare social error: {e}")

    return results


# ═══════════════════════════════════════════════════════════════════════════
# 7. CURRENCYLAYER: Live Forex Rates
# ═══════════════════════════════════════════════════════════════════════════

def fetch_forex_rates():
    """Fetch live forex rates from CurrencyLayer."""
    print("💱 Fetching CurrencyLayer forex rates...")
    results = {}
    try:
        resp = requests.get("http://api.currencylayer.com/live",
                            params={
                                "access_key": CURRENCYLAYER_KEY,
                                "currencies": "EUR,GBP,JPY,AUD,CAD,NZD,CHF",
                                "format": 1,
                            }, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("success"):
                quotes = data.get("quotes", {})
                for pair_key, rate in quotes.items():
                    # CurrencyLayer format: USDEUR, USDGBP, etc.
                    base_ccy = pair_key[3:]  # EUR, GBP, etc.
                    if base_ccy == "EUR":
                        results["EURUSD"] = {"rate": round(1 / rate, 5), "raw_rate": rate}
                    elif base_ccy == "GBP":
                        results["GBPUSD"] = {"rate": round(1 / rate, 5), "raw_rate": rate}
                    elif base_ccy == "JPY":
                        results["USDJPY"] = {"rate": round(rate, 3), "raw_rate": rate}
                    elif base_ccy == "AUD":
                        results["AUDUSD"] = {"rate": round(1 / rate, 5), "raw_rate": rate}
                    elif base_ccy == "CAD":
                        results["USDCAD"] = {"rate": round(rate, 5), "raw_rate": rate}
                    elif base_ccy == "NZD":
                        results["NZDUSD"] = {"rate": round(1 / rate, 5), "raw_rate": rate}
                    elif base_ccy == "CHF":
                        results["USDCHF"] = {"rate": round(rate, 5), "raw_rate": rate}
            else:
                print(f"  CurrencyLayer error: {data.get('error', {}).get('info', 'unknown')}")
    except Exception as e:
        print(f"  CurrencyLayer error: {e}")
    return results


# ═══════════════════════════════════════════════════════════════════════════
# 8. YFINANCE: Daily OHLCV for Technical Analysis
# ═══════════════════════════════════════════════════════════════════════════

def fetch_yfinance_data(symbols):
    """Fetch daily OHLCV from yfinance for technical analysis."""
    print(f"📉 Fetching yfinance data for {len(symbols)} symbols...")
    import yfinance as yf
    data = {}
    # Batch download
    try:
        batch = yf.download(symbols, period="6mo", group_by="ticker",
                            auto_adjust=True, progress=False, threads=True)
        for sym in symbols:
            try:
                if len(symbols) > 1:
                    df = batch[sym].dropna()
                else:
                    df = batch.dropna()
                if len(df) >= 20:
                    data[sym] = df
            except Exception:
                continue
    except Exception as e:
        print(f"  yfinance batch error: {e}")
        # Fallback: individual downloads
        for sym in symbols:
            try:
                df = yf.Ticker(sym).history(period="6mo", auto_adjust=True)
                if df is not None and len(df) >= 20:
                    data[sym] = df
            except Exception:
                continue
    print(f"  Loaded {len(data)}/{len(symbols)} symbols")
    return data


# ═══════════════════════════════════════════════════════════════════════════
# SIGNAL GENERATION ENGINE
# ═══════════════════════════════════════════════════════════════════════════

def generate_signals(yf_data, tickers, order_books, funding_rates, cc_data, cg_trending):
    """Generate BUY signals with TP/SL for all crypto + forex."""
    signals = []
    now = datetime.now(timezone.utc)

    for sym in CRYPTO_SYMBOLS:
        df = yf_data.get(sym)
        if df is None or len(df) < 20:
            continue

        close = df["Close"]
        vol = df["Volume"]
        price = float(close.iloc[-1])

        # --- Technical Indicators ---
        rsi = _rsi(close, 14)
        rsi_val = float(rsi.iloc[-1]) if not np.isnan(rsi.iloc[-1]) else 50

        sma_20 = close.rolling(20).mean().iloc[-1]
        sma_50 = close.rolling(50).mean().iloc[-1] if len(close) >= 50 else sma_20
        sma_200 = close.rolling(200).mean().iloc[-1] if len(close) >= 200 else sma_50

        avg_vol_20 = float(vol.iloc[-21:-1].mean()) if len(vol) >= 21 else float(vol.mean())
        last_vol = float(vol.iloc[-1])
        vol_ratio = last_vol / avg_vol_20 if avg_vol_20 > 0 else 1.0

        # Momentum
        ret_1d = (close.iloc[-1] - close.iloc[-2]) / close.iloc[-2] if len(close) >= 2 else 0
        ret_7d = (close.iloc[-1] - close.iloc[-6]) / close.iloc[-6] if len(close) >= 6 else 0
        ret_30d = (close.iloc[-1] - close.iloc[-21]) / close.iloc[-21] if len(close) >= 21 else 0

        # Bollinger Bands
        bb_mid = close.rolling(20).mean().iloc[-1]
        bb_std = close.rolling(20).std().iloc[-1]
        bb_lower = bb_mid - 2 * bb_std
        bb_upper = bb_mid + 2 * bb_std

        # ATR for stop loss
        if "High" in df.columns and "Low" in df.columns:
            high = df["High"]
            low = df["Low"]
            tr = pd.concat([
                high - low,
                (high - close.shift(1)).abs(),
                (low - close.shift(1)).abs()
            ], axis=1).max(axis=1)
            atr_14 = float(tr.rolling(14).mean().iloc[-1])
        else:
            atr_14 = price * 0.03  # fallback 3%

        # 2nd derivative (jerk)
        d1 = close.pct_change()
        d2 = d1.diff()
        jerk = float(d2.iloc[-1]) if not np.isnan(d2.iloc[-1]) else 0

        # --- Collect all data sources ---
        ticker_data = tickers.get(sym, {})
        ob_data = order_books.get(sym, {})
        fund_data = funding_rates.get(sym, {})
        cc_entry = cc_data.get(sym, {})

        # Compute composite score (0-100)
        score = 50  # baseline
        reasons = []

        # 1. RSI Oversold (mean reversion)
        if rsi_val < 30:
            score += 15
            reasons.append(f"RSI oversold {rsi_val:.0f}")
        elif rsi_val < 40:
            score += 8
            reasons.append(f"RSI low {rsi_val:.0f}")
        elif rsi_val > 70:
            score -= 10

        # 2. Price below Bollinger lower band
        if price < bb_lower:
            score += 12
            reasons.append(f"Below BB lower (${bb_lower:.2f})")

        # 3. Volume spike
        if vol_ratio > 3.0:
            score += 10
            reasons.append(f"Volume {vol_ratio:.1f}x avg")
        elif vol_ratio > 2.0:
            score += 5
            reasons.append(f"Volume {vol_ratio:.1f}x avg")

        # 4. Order book imbalance (Binance real-time)
        ob_ratio = ob_data.get("ratio", 1.0)
        if ob_ratio > 2.5:
            score += 12
            reasons.append(f"Order book bullish {ob_ratio:.1f}x")
        elif ob_ratio > 2.0:
            score += 7
            reasons.append(f"Order book tilted {ob_ratio:.1f}x")
        elif ob_ratio < 0.5:
            score -= 10

        # 5. Funding rate (contrarian: negative = bullish)
        fund_rate = fund_data.get("current_rate", 0)
        if fund_rate < -0.01:
            score += 10
            reasons.append(f"Negative funding {fund_rate:.3f}%")
        elif fund_rate > 0.05:
            score -= 8
            reasons.append(f"⚠ High funding {fund_rate:.3f}%")

        # 6. Funding rate reversal (negative→positive transition)
        if fund_data.get("direction") == "negative→positive":
            score += 8
            reasons.append("Funding reversal neg→pos")

        # 7. Momentum jerk (acceleration)
        if jerk > 0.002 and d2.iloc[-2] > 0:
            score += 7
            reasons.append(f"Momentum accelerating (jerk={jerk*100:.2f}%)")

        # 8. Above key SMAs (trend confirmation)
        if price > sma_50:
            score += 5
            reasons.append("Above SMA50")
        if price > sma_200:
            score += 5
            reasons.append("Above SMA200")

        # 9. CoinGecko trending bonus
        sym_short = sym.replace("-USD", "")
        if any(t["symbol"] == sym_short for t in cg_trending):
            score += 10
            reasons.append("🔥 Trending on CoinGecko")

        # 10. 24h momentum context
        change_24h = ticker_data.get("change_24h_pct", 0)
        if -5 < change_24h < -1:
            score += 5  # Healthy pullback
            reasons.append(f"Pullback {change_24h:.1f}% (opportunity)")
        elif change_24h < -8:
            score -= 5
            reasons.append(f"Dump {change_24h:.1f}%")

        # --- Calculate TP / SL ---
        # Risk-based: SL = 1.5 * ATR below, TP = 2.5 * ATR above (1.67:1 R:R)
        sl_distance = max(atr_14 * 1.5, price * 0.02)  # Minimum 2% SL
        tp_distance = max(atr_14 * 2.5, price * 0.04)  # Minimum 4% TP

        stop_price = round(price - sl_distance, 6)
        target_price = round(price + tp_distance, 6)
        risk_reward = round(tp_distance / sl_distance, 2) if sl_distance > 0 else 1.0

        # --- Determine signal type ---
        if score >= 70:
            signal_type = "🟢 STRONG BUY"
            confidence = min(score, 95)
        elif score >= 60:
            signal_type = "🟡 BUY"
            confidence = score
        elif score >= 55:
            signal_type = "⚪ WATCH"
            confidence = score
        else:
            continue  # Skip weak signals

        signals.append({
            "symbol": sym,
            "price": price,
            "signal": signal_type,
            "confidence": confidence,
            "stop_loss": stop_price,
            "take_profit": target_price,
            "risk_reward": risk_reward,
            "rsi": round(rsi_val, 1),
            "vol_ratio": round(vol_ratio, 1),
            "ob_ratio": ob_ratio,
            "funding_rate": fund_rate,
            "change_24h": change_24h,
            "ret_7d": round(ret_7d * 100, 1),
            "reasons": reasons,
            "timestamp": now.isoformat(),
        })

    return sorted(signals, key=lambda x: -x["confidence"])


# ═══════════════════════════════════════════════════════════════════════════
# FOREX SIGNAL GENERATION
# ═══════════════════════════════════════════════════════════════════════════

def generate_forex_signals(yf_data, forex_rates):
    """Generate forex signals using yfinance data + CurrencyLayer rates."""
    signals = []
    now = datetime.now(timezone.utc)

    forex_yf_symbols = ["EURUSD=X", "GBPUSD=X", "JPY=X", "AUDUSD=X",
                         "CAD=X", "NZDUSD=X", "CHF=X"]

    for sym in forex_yf_symbols:
        df = yf_data.get(sym)
        if df is None or len(df) < 20:
            continue

        close = df["Close"]
        price = float(close.iloc[-1])
        rsi = _rsi(close, 14)
        rsi_val = float(rsi.iloc[-1]) if not np.isnan(rsi.iloc[-1]) else 50

        sma_20 = float(close.rolling(20).mean().iloc[-1])
        sma_50 = float(close.rolling(50).mean().iloc[-1]) if len(close) >= 50 else sma_20

        vol = df["Volume"] if "Volume" in df.columns else pd.Series([0] * len(df))
        avg_vol = float(vol.iloc[-21:-1].mean()) if len(vol) >= 21 else 1
        vol_ratio = float(vol.iloc[-1]) / avg_vol if avg_vol > 0 else 1.0

        # ATR
        if "High" in df.columns and "Low" in df.columns:
            high = df["High"]
            low = df["Low"]
            tr = pd.concat([
                high - low,
                (high - close.shift(1)).abs(),
                (low - close.shift(1)).abs()
            ], axis=1).max(axis=1)
            atr_14 = float(tr.rolling(14).mean().iloc[-1])
        else:
            atr_14 = price * 0.005  # Forex default ~0.5%

        # Score
        score = 50
        reasons = []

        if rsi_val < 30:
            score += 15
            reasons.append(f"RSI oversold {rsi_val:.0f}")
        elif rsi_val < 40:
            score += 8
            reasons.append(f"RSI low {rsi_val:.0f}")

        if price > sma_20:
            score += 5
            reasons.append("Above SMA20")
        elif price < sma_20 * 0.995:
            score += 8
            reasons.append(f"Below SMA20 (mean-rev)")

        if price > sma_50:
            score += 5
            reasons.append("Above SMA50")

        # Bollinger bands
        bb_mid = close.rolling(20).mean().iloc[-1]
        bb_std = close.rolling(20).std().iloc[-1]
        if price < bb_mid - 2 * bb_std:
            score += 12
            reasons.append("Below BB lower")

        if score < 55:
            continue

        sl_dist = max(atr_14 * 2, price * 0.005)
        tp_dist = max(atr_14 * 3, price * 0.01)

        signal_type = "🟢 STRONG BUY" if score >= 70 else ("🟡 BUY" if score >= 60 else "⚪ WATCH")

        signals.append({
            "symbol": sym,
            "price": price,
            "signal": signal_type,
            "confidence": min(score, 95),
            "stop_loss": round(price - sl_dist, 5),
            "take_profit": round(price + tp_dist, 5),
            "risk_reward": round(tp_dist / sl_dist, 2) if sl_dist > 0 else 1.0,
            "rsi": round(rsi_val, 1),
            "reasons": reasons,
            "timestamp": now.isoformat(),
        })

    return sorted(signals, key=lambda x: -x["confidence"])


# ═══════════════════════════════════════════════════════════════════════════
# ELIMINATION ENGINE — Run against current tournament data
# ═══════════════════════════════════════════════════════════════════════════

def run_elimination_check():
    """Run elimination engine against live tournament data."""
    print("\n⚔️  Running Elimination Engine...")
    try:
        from elimination_engine import EliminationEngine
        engine = EliminationEngine()
        tourn_path = DATA_DIR / "tournament.json"
        if not tourn_path.exists():
            print("  No tournament.json found — skipping")
            return

        with open(tourn_path) as f:
            tournament = json.load(f)

        eliminated = engine.check_eliminations(tournament)
        state = engine.get_state()
        print(f"  Danger zone: {state['danger_zone']}")
        print(f"  Probation: {state['probation']}")
        print(f"  Eliminated: {state['eliminated']}")
        print(f"  Promoted: {state['promoted']}")
        print(f"  Challenger pool remaining: {state['challenger_pool_remaining']}")

        if eliminated:
            n = engine.should_inject(len(eliminated))
            if n > 0:
                injected = engine.inject_challengers(n)
                print(f"  🔄 Injected {len(injected)} challengers: {[c['id'] for c in injected]}")
    except Exception as e:
        print(f"  Elimination error: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    now = datetime.now(timezone.utc)
    print("=" * 72)
    print("🚀 ANTIGRAVITY_FEB172026 — LIVE MARKET SIGNAL SCAN")
    print(f"   {now.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 72)

    # 1. Fetch all real-time data
    tickers = fetch_binance_tickers()
    order_books = fetch_order_books()
    funding_rates = fetch_all_funding_rates()
    cg_trending, cg_global = fetch_coingecko_data()
    cc_data = fetch_cryptocompare_data()
    forex_rates = fetch_forex_rates()

    # 2. Show market overview
    print("\n" + "=" * 72)
    print("📊 MARKET OVERVIEW")
    print("=" * 72)

    if cg_global:
        print(f"  Total Market Cap: ${cg_global.get('total_market_cap_usd', 0):.1f}B")
        print(f"  24h Volume: ${cg_global.get('total_volume_24h_usd', 0):.1f}B")
        print(f"  BTC Dominance: {cg_global.get('btc_dominance', 0):.1f}%")
        print(f"  ETH Dominance: {cg_global.get('eth_dominance', 0):.1f}%")
        print(f"  Market Cap Change 24h: {cg_global.get('market_cap_change_24h', 0):+.2f}%")

    if cg_trending:
        print(f"\n  🔥 CoinGecko Trending: {', '.join(t['symbol'] for t in cg_trending[:7])}")

    # 3. Key Binance stats
    print("\n  📈 Top Movers (Binance 24h):")
    sorted_tickers = sorted(tickers.items(), key=lambda x: x[1].get("change_24h_pct", 0), reverse=True)
    for sym, data in sorted_tickers[:5]:
        print(f"    🟢 {sym:15s} ${data['price']:>12,.4f}  {data['change_24h_pct']:+6.1f}%  vol=${data['volume_usd']/1e6:.0f}M")
    print("    ---")
    for sym, data in sorted_tickers[-3:]:
        print(f"    🔴 {sym:15s} ${data['price']:>12,.4f}  {data['change_24h_pct']:+6.1f}%  vol=${data['volume_usd']/1e6:.0f}M")

    # 4. Funding rates
    print("\n  💰 Funding Rates (contrarian signals):")
    neg_funding = [(s, d) for s, d in funding_rates.items() if d.get("current_rate", 0) < -0.005]
    high_funding = [(s, d) for s, d in funding_rates.items() if d.get("current_rate", 0) > 0.03]
    if neg_funding:
        neg_str = ', '.join(f"{s}({d['current_rate']:.3f}%)" for s, d in neg_funding)
        print(f"    🟢 Negative funding (contrarian BUY): {neg_str}")
    if high_funding:
        hi_str = ', '.join(f"{s}({d['current_rate']:.3f}%)" for s, d in high_funding)
        print(f"    🔴 High funding (overheated): {hi_str}")

    # 5. Order book highlights
    print("\n  📊 Order Book Imbalance (top bullish):")
    bullish_books = [(s, d) for s, d in order_books.items() if d.get("ratio", 1) > 1.5]
    bullish_books.sort(key=lambda x: -x[1]["ratio"])
    for sym, data in bullish_books[:5]:
        print(f"    {sym:15s} bid/ask={data['ratio']:.2f}x  bids=${data['bid_usd']:,.0f}")

    # 6. Forex rates
    if forex_rates:
        print("\n  💱 Live Forex Rates:")
        for pair, data in sorted(forex_rates.items()):
            print(f"    {pair}: {data['rate']}")

    # 7. Whale detection for top coins
    print("\n  🐋 Whale Detection (last 500 trades):")
    for sym in ["BTC-USD", "ETH-USD", "SOL-USD"]:
        whales = fetch_whale_trades(sym)
        if whales and whales.get("whale_trades", 0) > 0:
            print(f"    {sym}: {whales['whale_trades']} whale trades, "
                  f"buy=${whales['buy_usd']:,.0f} sell=${whales['sell_usd']:,.0f} "
                  f"net={whales['net_direction']:+.3f} [{whales['signal']}]")
        time.sleep(0.1)

    # 8. Fetch yfinance data for TA
    all_yf_symbols = CRYPTO_SYMBOLS + ["EURUSD=X", "GBPUSD=X", "JPY=X",
                                         "AUDUSD=X", "CAD=X", "NZDUSD=X", "CHF=X"]
    yf_data = fetch_yfinance_data(all_yf_symbols)

    # 9. Generate crypto signals
    print("\n" + "=" * 72)
    print("🎯 CRYPTO BUY SIGNALS")
    print("=" * 72)
    crypto_signals = generate_signals(yf_data, tickers, order_books,
                                       funding_rates, cc_data, cg_trending)
    if crypto_signals:
        for i, sig in enumerate(crypto_signals, 1):
            print(f"\n  #{i} {sig['signal']}  {sig['symbol']}")
            print(f"      Price:  ${sig['price']:,.4f}")
            print(f"      TP:     ${sig['take_profit']:,.4f}  ({((sig['take_profit']-sig['price'])/sig['price'])*100:+.1f}%)")
            print(f"      SL:     ${sig['stop_loss']:,.4f}  ({((sig['stop_loss']-sig['price'])/sig['price'])*100:+.1f}%)")
            print(f"      R:R:    {sig['risk_reward']:.2f}")
            print(f"      Conf:   {sig['confidence']}%  |  RSI: {sig['rsi']}  |  Vol: {sig['vol_ratio']}x")
            print(f"      24h:    {sig['change_24h']:+.1f}%  |  7d: {sig['ret_7d']:+.1f}%")
            print(f"      OB:     {sig['ob_ratio']:.2f}x  |  Fund: {sig['funding_rate']:.3f}%")
            print(f"      Why:    {' | '.join(sig['reasons'])}")
    else:
        print("  No crypto signals above threshold")

    # 10. Generate forex signals
    print("\n" + "=" * 72)
    print("💱 FOREX BUY SIGNALS")
    print("=" * 72)
    forex_signals = generate_forex_signals(yf_data, forex_rates)
    if forex_signals:
        for i, sig in enumerate(forex_signals, 1):
            print(f"\n  #{i} {sig['signal']}  {sig['symbol']}")
            print(f"      Price:  {sig['price']:.5f}")
            print(f"      TP:     {sig['take_profit']:.5f}  ({((sig['take_profit']-sig['price'])/sig['price'])*100:+.2f}%)")
            print(f"      SL:     {sig['stop_loss']:.5f}  ({((sig['stop_loss']-sig['price'])/sig['price'])*100:+.2f}%)")
            print(f"      R:R:    {sig['risk_reward']:.2f}")
            print(f"      Conf:   {sig['confidence']}%  |  RSI: {sig['rsi']}")
            print(f"      Why:    {' | '.join(sig['reasons'])}")
    else:
        print("  No forex signals above threshold")

    # 11. Run elimination engine
    run_elimination_check()

    # 12. Save all signals to JSON
    all_signals = {
        "generated_at": now.isoformat(),
        "market_overview": cg_global,
        "trending": cg_trending,
        "crypto_signals": crypto_signals,
        "forex_signals": forex_signals,
        "forex_rates": forex_rates,
        "order_book_summary": {s: d for s, d in order_books.items() if d.get("ratio", 1) > 1.5},
        "funding_rates_summary": {s: d for s, d in funding_rates.items()
                                   if abs(d.get("current_rate", 0)) > 0.005},
    }
    output_path = DATA_DIR / "live_signals_now.json"
    DATA_DIR.mkdir(exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_signals, f, indent=2, default=str)
    print(f"\n💾 Signals saved to {output_path}")

    # Summary
    total_signals = len(crypto_signals) + len(forex_signals)
    strong = len([s for s in crypto_signals + forex_signals if "STRONG" in s["signal"]])
    print(f"\n{'=' * 72}")
    print(f"📊 SCAN COMPLETE: {total_signals} signals ({strong} strong buys)")
    print(f"{'=' * 72}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
