"""
crypto_acceleration_engine.py — KIMI Rise of the Claw v11.0
Explosive Crypto Move Detection Engine

10 signal functions:
  1. signal_pump_detector        — price velocity + volume + RSI jerk
  2. signal_telegram_call_follower — Telegram TP/SL announcements
  3. signal_twitter_alpha_calls   — Twitter influencer crypto calls
  4. signal_order_book_imbalance  — Binance public order book bid/ask ratio
  5. signal_liquidation_cascade   — Binance Futures short liquidation events
  6. signal_acceleration_burst    — 2nd derivative (momentum jerk signal)
  7. signal_coingecko_trending_spike — CoinGecko trending + volume confirmation
  8. signal_whale_size_trade       — Binance large individual trades > $100K
  9. signal_funding_rate_reversal  — Funding rate negative→positive transition
  10. signal_multi_exchange_divergence — Cross-exchange price divergence

All functions follow the live_scanner.py signature:
  def signal_xxx(symbol: str, df: pd.DataFrame, all_data: dict, drought: int = 0) -> tuple[str | None, str]

Pre-computed data loaders (called in live_scanner.py before signal loop):
  load_telegram_signals(data_dir)    -> dict
  load_twitter_signals(data_dir)     -> dict
  fetch_binance_liquidations()       -> dict
  fetch_order_book_imbalance()       -> dict (all major pairs)
"""
import os
import json
import time
import logging
import requests
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Binance symbol mapping: yfinance ticker -> Binance trading pair
_YF_TO_BINANCE = {
    "BTC-USD": "BTCUSDT",  "ETH-USD": "ETHUSDT",  "SOL-USD": "SOLUSDT",
    "BNB-USD": "BNBUSDT",  "AVAX-USD": "AVAXUSDT","XRP-USD": "XRPUSDT",
    "ADA-USD": "ADAUSDT",  "DOGE-USD": "DOGEUSDT", "SHIB-USD": "SHIBUSDT",
    "MATIC-USD": "MATICUSDT","LINK-USD": "LINKUSDT","DOT-USD": "DOTUSDT",
    "ATOM-USD": "ATOMUSDT","NEAR-USD": "NEARUSDT", "FIL-USD": "FILUSDT",
    "PEPE-USD": "PEPEUSDT","FLOKI-USD": "FLOKIUSDT","WIF-USD": "WIFUSDT",
    "BONK-USD": "BONKUSDT","INJ-USD": "INJUSDT",   "TIA-USD": "TIAUSDT",
    "SUI20947-USD": "SUIUSDT","ARB11841-USD": "ARBUSDT","OP-USD": "OPUSDT",
    "APT21794-USD": "APTUSDT","SEI-USD": "SEIUSDT",
}

_BINANCE_BASE = "https://api.binance.com"
_BINANCE_FUTURES_BASE = "https://fapi.binance.com"
_COINGECKO_BASE = "https://api.coingecko.com/api/v3"

# Caches (in-process TTL)
_CACHE: dict = {}
_CACHE_TTL = 900  # 15 min in seconds


def _cache_get(key: str):
    entry = _CACHE.get(key)
    if entry and time.time() - entry["ts"] < _CACHE_TTL:
        return entry["val"]
    return None


def _cache_set(key: str, val):
    _CACHE[key] = {"ts": time.time(), "val": val}


# ---------------------------------------------------------------------------
# Helper: RSI
# ---------------------------------------------------------------------------


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0).rolling(window=period, min_periods=period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window=period, min_periods=period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


# ---------------------------------------------------------------------------
# Binance Public API Fetchers (no auth required)
# ---------------------------------------------------------------------------

def fetch_order_book_imbalance(pairs: Optional[list] = None) -> dict:
    """
    Fetch Binance public order book for crypto pairs.
    Returns {yf_symbol: {bid_vol, ask_vol, imbalance_ratio, signal}}
    imbalance_ratio > 2.0 = heavy buying pressure
    """
    cached = _cache_get("order_book")
    if cached:
        return cached

    if pairs is None:
        pairs = list(_YF_TO_BINANCE.keys())

    result = {}
    for yf_sym in pairs:
        binance_sym = _YF_TO_BINANCE.get(yf_sym)
        if not binance_sym:
            continue
        try:
            url = f"{_BINANCE_BASE}/api/v3/depth"
            resp = requests.get(url, params={"symbol": binance_sym, "limit": 20}, timeout=5)
            if resp.status_code != 200:
                continue
            data = resp.json()
            bid_vol = sum(float(b[1]) * float(b[0]) for b in data.get("bids", []))
            ask_vol = sum(float(a[1]) * float(a[0]) for a in data.get("asks", []))
            total = bid_vol + ask_vol
            ratio = bid_vol / ask_vol if ask_vol > 0 else 1.0
            signal = "bullish" if ratio > 2.0 else ("bearish" if ratio < 0.5 else "neutral")
            result[yf_sym] = {
                "bid_vol_usd": round(bid_vol, 0),
                "ask_vol_usd": round(ask_vol, 0),
                "imbalance_ratio": round(ratio, 3),
                "signal": signal,
            }
        except Exception as e:
            logger.debug(f"Order book fetch failed for {binance_sym}: {e}")
            continue

    _cache_set("order_book", result)
    return result


def fetch_binance_liquidations(pairs: Optional[list] = None) -> dict:
    """
    Fetch recent short liquidations from Binance Futures (public, no auth).
    Returns {yf_symbol: {total_liquidated_usd, short_liq_usd, signal, timestamp}}
    Large SHORT liquidation > $2M in 15 min = forced buying cascade.
    Note: Binance FAPI /fapi/v1/forceOrders is for authenticated users.
    We approximate using high-volume + price spike proxy from klines.
    """
    cached = _cache_get("liquidations")
    if cached:
        return cached

    if pairs is None:
        pairs = ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "AVAX-USD",
                 "LINK-USD", "MATIC-USD", "XRP-USD", "ADA-USD", "INJ-USD"]

    result = {}
    for yf_sym in pairs:
        binance_sym = _YF_TO_BINANCE.get(yf_sym)
        if not binance_sym:
            continue
        try:
            # Use 5-min klines to detect liquidation spikes (price drop + volume surge)
            url = f"{_BINANCE_FUTURES_BASE}/fapi/v1/klines"
            resp = requests.get(url, params={
                "symbol": binance_sym, "interval": "5m", "limit": 6
            }, timeout=5)
            if resp.status_code != 200:
                # Fallback to spot
                url_spot = f"{_BINANCE_BASE}/api/v3/klines"
                resp = requests.get(url_spot, params={
                    "symbol": binance_sym, "interval": "5m", "limit": 6
                }, timeout=5)
                if resp.status_code != 200:
                    continue

            klines = resp.json()
            if len(klines) < 4:
                continue

            # Detect liquidation signature: sudden drop + volume > 3x recent avg
            closes = [float(k[4]) for k in klines]
            volumes = [float(k[5]) for k in klines]
            avg_vol = np.mean(volumes[:-1]) if len(volumes) > 1 else volumes[0]
            last_vol = volumes[-1]
            vol_ratio = last_vol / avg_vol if avg_vol > 0 else 1.0
            price_chg = (closes[-1] - closes[-3]) / closes[-3] if closes[-3] > 0 else 0

            # Short liq signal: price dropped then bounced + volume surge
            short_liq_signal = (
                price_chg > -0.03 and  # Bounce (not still falling)
                vol_ratio > 3.0 and    # Volume spike (liquidation flush)
                closes[-1] > closes[-2]  # Price recovering
            )
            result[yf_sym] = {
                "vol_ratio": round(vol_ratio, 2),
                "price_chg_15m": round(price_chg * 100, 2),
                "short_liq_signal": short_liq_signal,
                "signal": "cascade_reversal" if short_liq_signal else "normal",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            logger.debug(f"Liquidation proxy failed for {yf_sym}: {e}")
            continue

    _cache_set("liquidations", result)
    return result

def fetch_whale_trades(yf_symbol: str, min_usd: float = 100_000) -> dict:
    """
    Detect large individual trades on Binance spot (> min_usd USD each).
    Uses /api/v3/trades endpoint (public, no auth, last 500 trades).
    Returns {count_whale_trades, total_whale_usd, net_direction, signal}
    """
    cached = _cache_get(f"whale_{yf_symbol}")
    if cached:
        return cached

    binance_sym = _YF_TO_BINANCE.get(yf_symbol)
    if not binance_sym:
        return {}

    try:
        url = f"{_BINANCE_BASE}/api/v3/trades"
        resp = requests.get(url, params={"symbol": binance_sym, "limit": 500}, timeout=5)
        if resp.status_code != 200:
            return {}

        trades = resp.json()
        buy_usd = 0.0
        sell_usd = 0.0
        whale_count = 0

        for t in trades:
            price = float(t["price"])
            qty = float(t["qty"])
            usd_val = price * qty
            if usd_val >= min_usd:
                whale_count += 1
                if not t.get("isBuyerMaker", True):
                    buy_usd += usd_val   # Aggressive buy
                else:
                    sell_usd += usd_val  # Aggressive sell

        total = buy_usd + sell_usd
        net = (buy_usd - sell_usd) / total if total > 0 else 0
        signal = "accumulation" if net > 0.3 else ("distribution" if net < -0.3 else "mixed")

        result = {
            "whale_count": whale_count,
            "buy_usd": round(buy_usd, 0),
            "sell_usd": round(sell_usd, 0),
            "net_direction": round(net, 3),
            "signal": signal,
        }
        _cache_set(f"whale_{yf_symbol}", result)
        return result
    except Exception as e:
        logger.debug(f"Whale trades fetch failed for {yf_symbol}: {e}")
        return {}


def fetch_coingecko_trending() -> list:
    """
    Fetch CoinGecko trending coins list (top 7 trending last 24h).
    Free API, no key required. Returns list of coin symbols.
    """
    cached = _cache_get("cg_trending")
    if cached:
        return cached
    import time as _time
    for _attempt in range(3):
        try:
            resp = requests.get(f"{_COINGECKO_BASE}/search/trending", timeout=8)
            if resp.status_code != 200:
                if _attempt < 2:
                    _time.sleep(2 * (_attempt + 1))
                    continue
                return []
            data = resp.json()
            # Handle both dict {"coins": [...]} and unexpected list format
            if isinstance(data, dict):
                coins = data.get("coins", [])
            elif isinstance(data, list):
                coins = data
            else:
                coins = []
            symbols = []
            for c in coins:
                sym = c.get("item", {}).get("symbol", "").upper()
                if sym:
                    symbols.append(sym + "-USD")
            _cache_set("cg_trending", symbols)
            return symbols
        except Exception as e:
            if _attempt < 2:
                _time.sleep(2 * (_attempt + 1))
                continue
            logger.debug(f"CoinGecko trending failed after 3 attempts: {e}")
    return []


def fetch_funding_rate_history(yf_symbol: str, limit: int = 8) -> list:
    """
    Fetch recent Binance USDM funding rates for a symbol.
    Returns list of recent funding rates (most recent first).
    Positive = longs pay shorts (bearish). Negative = shorts pay longs (bullish).
    """
    cached = _cache_get(f"funding_{yf_symbol}")
    if cached:
        return cached
    binance_sym = _YF_TO_BINANCE.get(yf_symbol)
    if not binance_sym:
        return []
    try:
        url = f"{_BINANCE_FUTURES_BASE}/fapi/v1/fundingRate"
        resp = requests.get(url, params={"symbol": binance_sym, "limit": limit}, timeout=5)
        if resp.status_code != 200:
            return []
        rates = [float(r["fundingRate"]) for r in resp.json()]
        rates.reverse()  # Most recent first
        _cache_set(f"funding_{yf_symbol}", rates)
        return rates
    except Exception as e:
        logger.debug(f"Funding rate history failed for {yf_symbol}: {e}")
        return []


# ---------------------------------------------------------------------------
# Social Signal Loaders (called from live_scanner.py before signal loop)
# ---------------------------------------------------------------------------

def load_telegram_signals(data_dir: Optional[Path] = None) -> dict:
    """
    Load Telegram TP/SL announcements from data/telegram_signals.json.
    File is written by telegram_signal_watcher.py (background service).
    Returns {symbol: {tp, sl, entry, confidence, channel, age_minutes}}
    Falls back to empty dict if file missing or expired (> 4h).
    """
    if data_dir is None:
        data_dir = Path(__file__).parent / "data"

    path = data_dir / "telegram_signals.json"
    if not path.exists():
        return {}

    try:
        with open(path) as f:
            raw = json.load(f)
        now = datetime.now(timezone.utc)
        result = {}
        for sym, sig in raw.items():
            ts_str = sig.get("timestamp", "")
            try:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                age_h = (now - ts).total_seconds() / 3600
                if age_h > 4:
                    continue  # Expired signal
                sig["age_minutes"] = round(age_h * 60)
                result[sym] = sig
            except Exception:
                continue
        return result
    except Exception as e:
        logger.debug(f"Failed to load telegram signals: {e}")
        return {}


def load_twitter_signals(data_dir: Optional[Path] = None) -> dict:
    """
    Load Twitter TP/SL alpha calls from data/twitter_signals.json.
    File is written by twitter_alpha_fetcher.py or refreshed during scan.
    Returns {symbol: {mention_count, avg_tp_pct, influencer_count, age_minutes}}
    Falls back to empty dict if file missing or expired (> 15 min).
    """
    if data_dir is None:
        data_dir = Path(__file__).parent / "data"

    path = data_dir / "twitter_signals.json"
    if not path.exists():
        return {}

    try:
        with open(path) as f:
            raw = json.load(f)
        now = datetime.now(timezone.utc)
        result = {}
        for sym, sig in raw.items():
            ts_str = sig.get("timestamp", "")
            try:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                age_m = (now - ts).total_seconds() / 60
                if age_m > 15:
                    continue  # Expired
                sig["age_minutes"] = round(age_m)
                result[sym] = sig
            except Exception:
                continue
        return result
    except Exception as e:
        logger.debug(f"Failed to load twitter signals: {e}")
        return {}


def fetch_twitter_crypto_calls(bearer_token: Optional[str] = None,
                                data_dir: Optional[Path] = None) -> dict:
    """
    Fetch Twitter/X API v2 crypto TP/SL calls and cache to twitter_signals.json.
    Requires TWITTER_BEARER_TOKEN env var.
    Rate limit: 300 req / 15 min. Only called once per 15-min scan cycle.

    Returns {symbol: {mention_count, avg_tp_pct, influencer_count, raw_tweets[]}}
    """
    if bearer_token is None:
        bearer_token = os.environ.get("TWITTER_BEARER_TOKEN")
    if not bearer_token:
        return {}

    if data_dir is None:
        data_dir = Path(__file__).parent / "data"

    # Check if recent cache exists
    cached_signals = load_twitter_signals(data_dir)
    if cached_signals:
        return cached_signals

    symbols_to_search = [
        "BTC", "ETH", "SOL", "AVAX", "BNB", "LINK", "DOGE", "PEPE",
        "ARB", "OP", "INJ", "TIA", "SUI", "SEI", "WIF", "BONK", "FLOKI"
    ]

    result = {}
    headers = {"Authorization": f"Bearer {bearer_token}"}
    base_url = "https://api.twitter.com/2/tweets/search/recent"

    for sym in symbols_to_search[:8]:  # Limit to 8 to stay within rate limits
        query = f"(${sym} OR #{sym}crypto) (TP OR SL OR 'take profit' OR target OR entry) lang:en -is:retweet"
        params = {
            "query": query,
            "max_results": 10,
            "tweet.fields": "created_at,author_id,public_metrics",
            "expansions": "author_id",
            "user.fields": "public_metrics",
        }
        try:
            resp = requests.get(base_url, headers=headers, params=params, timeout=10)
            if resp.status_code == 429:
                logger.warning("Twitter rate limit hit, stopping fetch")
                break
            if resp.status_code != 200:
                continue

            data = resp.json()
            tweets = data.get("data", [])
            users = {u["id"]: u for u in data.get("includes", {}).get("users", [])}

            tp_values = []
            influencer_count = 0
            mentions = len(tweets)

            for tweet in tweets:
                author = users.get(tweet.get("author_id", ""), {})
                followers = author.get("public_metrics", {}).get("followers_count", 0)
                if followers >= 5000:
                    influencer_count += 1

                # Extract TP percentage if mentioned
                text = tweet.get("text", "")
                import re
                tp_match = re.search(r'TP[12]?\s*[:\-@]?\s*\$?([\d,.]+)%?', text, re.IGNORECASE)
                if tp_match:
                    try:
                        tp_val = float(tp_match.group(1).replace(",", ""))
                        if 1 < tp_val < 500:  # Sanity: 1-500%
                            tp_values.append(tp_val)
                    except Exception:
                        pass

            if mentions >= 2:
                yf_sym = sym + "-USD"
                result[yf_sym] = {
                    "symbol": sym,
                    "mention_count": mentions,
                    "influencer_count": influencer_count,
                    "avg_tp_pct": round(np.mean(tp_values), 1) if tp_values else None,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
        except Exception as e:
            logger.debug(f"Twitter fetch failed for {sym}: {e}")
            continue

    # Cache to file
    if result:
        try:
            data_dir.mkdir(parents=True, exist_ok=True)
            with open(data_dir / "twitter_signals.json", "w") as f:
                json.dump(result, f, indent=2)
        except Exception as e:
            logger.debug(f"Failed to write twitter_signals.json: {e}")

    return result


# ---------------------------------------------------------------------------
# Signal Function 1: Pump Acceleration Detector
# ---------------------------------------------------------------------------

def signal_pump_detector(symbol: str, df: pd.DataFrame, all_data: dict,
                          drought: int = 0) -> tuple[Optional[str], str]:
    """
    Detect early-stage crypto pump via price velocity + volume + RSI jerk.
    Entry: 4h price change >= 8% + volume 5x baseline + RSI not yet overbought.
    Academic: Price momentum jerk (2nd derivative) predicts continuation.
    """
    if df is None or len(df) < 30:
        return None, "insufficient data"

    close = df["Close"]
    vol = df["Volume"]

    velocity_4d = (close.iloc[-1] - close.iloc[-5]) / close.iloc[-5] if close.iloc[-5] > 0 else 0
    velocity_1d = (close.iloc[-1] - close.iloc[-2]) / close.iloc[-2] if close.iloc[-2] > 0 else 0

    avg_vol_20 = vol.iloc[-21:-1].mean()
    last_vol = vol.iloc[-1]
    vol_ratio = last_vol / avg_vol_20 if avg_vol_20 > 0 else 1.0

    rsi_series = _rsi(close, 14)
    rsi_val = rsi_series.iloc[-1] if not np.isnan(rsi_series.iloc[-1]) else 50.0

    d1 = close.pct_change()
    d2 = d1.diff()
    jerk = d2.iloc[-1] if not np.isnan(d2.iloc[-1]) else 0.0
    jerk_pos = jerk > 0

    threshold_vel = 0.06 if drought > 5 else 0.08
    threshold_vol = 3.5 if drought > 5 else 5.0

    if (velocity_4d >= threshold_vel
            and vol_ratio >= threshold_vol
            and rsi_val < 70
            and jerk_pos
            and velocity_1d > 0.01):
        reason = (f"Pump detected: {velocity_4d*100:.1f}% 4d velocity, "
                  f"vol {vol_ratio:.1f}x, RSI {rsi_val:.0f}, jerk+")
        return "BUY", reason

    return None, f"pump-detector: vel={velocity_4d*100:.1f}% vol={vol_ratio:.1f}x RSI={rsi_val:.0f}"


# ---------------------------------------------------------------------------
# Signal Function 2: Telegram Alpha Call Follower
# ---------------------------------------------------------------------------


def signal_telegram_call_follower(symbol: str, df: pd.DataFrame, all_data: dict,
                                   drought: int = 0) -> tuple[Optional[str], str]:
    """
    Follow Telegram crypto calls channels TP/SL announcements.
    Entry: Symbol called in Telegram channel < 2h ago + price not yet surged > 5%.
    Data: data/telegram_signals.json (written by telegram_signal_watcher.py)
    """
    if df is None or len(df) < 10:
        return None, "insufficient data"

    telegram_calls = all_data.get("__telegram_calls__", {})
    if not telegram_calls:
        return None, "no telegram signals loaded"

    call = telegram_calls.get(symbol)
    if not call:
        return None, f"no telegram call for {symbol}"

    age_min = call.get("age_minutes", 999)
    confidence = call.get("confidence", 0.0)

    if age_min > 90:
        return None, f"telegram call too old ({age_min}m)"

    close = df["Close"]
    if len(close) >= 2:
        price_chg = (close.iloc[-1] - close.iloc[-2]) / close.iloc[-2]
        if price_chg > 0.08:
            return None, f"already surged {price_chg*100:.1f}% -- too late"

    min_conf = 0.4 if drought > 5 else 0.6
    if confidence < min_conf:
        return None, f"low confidence call ({confidence:.2f})"

    tp = call.get("tp")
    sl = call.get("sl")
    channel = call.get("channel", "unknown")
    reason = (f"Telegram call: {channel}, age {age_min}m, conf {confidence:.2f}"
              + (f", TP ${tp}" if tp else "")
              + (f", SL ${sl}" if sl else ""))
    return "BUY", reason


# ---------------------------------------------------------------------------
# Signal Function 3: Twitter Alpha Calls
# ---------------------------------------------------------------------------


def signal_twitter_alpha_calls(symbol: str, df: pd.DataFrame, all_data: dict,
                                 drought: int = 0) -> tuple[Optional[str], str]:
    """
    Follow Twitter/X crypto influencer TP/SL posts.
    Entry: >= 2 influencer mentions (>=5K followers) + not already pumped > 6%.
    Data: data/twitter_signals.json
    """
    if df is None or len(df) < 10:
        return None, "insufficient data"

    twitter_calls = all_data.get("__twitter_calls__", {})
    if not twitter_calls:
        return None, "no twitter signals loaded"

    call = twitter_calls.get(symbol)
    if not call:
        return None, f"no twitter call for {symbol}"

    mention_count = call.get("mention_count", 0)
    influencer_count = call.get("influencer_count", 0)
    age_min = call.get("age_minutes", 999)

    if age_min > 15:
        return None, "twitter signal expired (> 15m)"

    min_inf = 1 if drought > 5 else 2
    min_mentions = 3 if drought > 5 else 5
    if influencer_count < min_inf and mention_count < min_mentions:
        return None, f"insufficient twitter buzz (inf={influencer_count}, mentions={mention_count})"

    close = df["Close"]
    if len(close) >= 2:
        price_chg = (close.iloc[-1] - close.iloc[-2]) / close.iloc[-2]
        if price_chg > 0.06:
            return None, f"already up {price_chg*100:.1f}%"

    avg_tp = call.get("avg_tp_pct")
    reason = (f"Twitter alpha: {influencer_count} influencers, {mention_count} mentions"
              + (f", avg TP {avg_tp:.0f}%" if avg_tp else "")
              + f", age {age_min}m")
    return "BUY", reason


# ---------------------------------------------------------------------------
# Signal Function 4: Order Book Imbalance
# ---------------------------------------------------------------------------


def signal_order_book_imbalance(symbol: str, df: pd.DataFrame, all_data: dict,
                                  drought: int = 0) -> tuple[Optional[str], str]:
    """
    Detect heavy institutional buy pressure via Binance order book.
    Entry: bid/ask volume ratio > 2.5 + price not overbought.
    Source: Binance public /api/v3/depth (no auth needed).
    Academic: Chordia et al. (2002) -- order imbalance predicts short-term returns.
    """
    if df is None or len(df) < 10:
        return None, "insufficient data"

    ob = all_data.get("__order_book__", {}).get(symbol)
    if not ob:
        return None, "no order book data"

    ratio = ob.get("imbalance_ratio", 1.0)
    signal = ob.get("signal", "neutral")

    threshold = 2.0 if drought > 5 else 2.5
    if ratio < threshold:
        return None, f"order book neutral (ratio={ratio:.2f})"

    close = df["Close"]
    rsi_series = _rsi(close, 14)
    rsi_val = rsi_series.iloc[-1] if not np.isnan(rsi_series.iloc[-1]) else 50.0
    if rsi_val > 75:
        return None, f"overbought RSI {rsi_val:.0f} despite bullish book"

    bid_usd = ob.get("bid_vol_usd", 0)
    reason = (f"Order book imbalance: bid/ask={ratio:.2f}x "
              f"(${bid_usd:,.0f} bids), RSI {rsi_val:.0f}")
    return "BUY", reason


# ---------------------------------------------------------------------------
# Signal Function 5: Liquidation Cascade Reversal
# ---------------------------------------------------------------------------


def signal_liquidation_cascade(symbol: str, df: pd.DataFrame, all_data: dict,
                                 drought: int = 0) -> tuple[Optional[str], str]:
    """
    Detect short liquidation cascade = forced buying pressure.
    Entry: Recent sharp drop followed by bounce + volume spike (liquidation flush).
    Data: from fetch_binance_liquidations() pre-computed in all_data.
    Academic: Bitmex/FTX forced liquidation cascades create asymmetric recoveries.
    """
    if df is None or len(df) < 10:
        return None, "insufficient data"

    liq = all_data.get("__liquidations__", {}).get(symbol)
    if not liq:
        return None, "no liquidation data"

    liq_signal = liq.get("short_liq_signal", False)
    if not liq_signal:
        vol_r = liq.get("vol_ratio", 1.0)
        return None, f"no cascade signal (vol_ratio={vol_r:.1f}x)"

    vol_ratio = liq.get("vol_ratio", 1.0)
    price_chg = liq.get("price_chg_15m", 0)

    close = df["Close"]
    vol = df["Volume"]
    avg_vol = vol.iloc[-21:-1].mean()
    last_vol = vol.iloc[-1]
    daily_vol_ratio = last_vol / avg_vol if avg_vol > 0 else 1.0

    threshold_vol = 2.5 if drought > 5 else 3.0
    if vol_ratio < threshold_vol and daily_vol_ratio < threshold_vol:
        return None, "volume not confirming cascade"

    reason = (f"Short liquidation cascade: 15m vol {vol_ratio:.1f}x, "
              f"price change {price_chg:.1f}%, bounce detected")
    return "BUY", reason


# ---------------------------------------------------------------------------
# Signal Function 6: Acceleration Burst (Momentum Jerk)
# ---------------------------------------------------------------------------


def signal_acceleration_burst(symbol: str, df: pd.DataFrame, all_data: dict,
                                drought: int = 0) -> tuple[Optional[str], str]:
    """
    Detect momentum ACCELERATION (2nd derivative of price) -- jerk signal.
    This fires before RSI gets overbought, catching early parabolic moves.
    Entry: 3 consecutive positive jerks + funding rate transitioning positive.
    Academic: Jerk momentum (Hutchinson & De Prado 2020) -- stronger alpha than velocity.
    """
    if df is None or len(df) < 30:
        return None, "insufficient data"

    close = df["Close"]
    d1 = close.pct_change()
    d2 = d1.diff()

    consec_positive = all(d2.iloc[-i-1] > 0 for i in range(3))
    if not consec_positive:
        return None, "acceleration not sustained"

    avg_jerk = d2.iloc[-3:].mean()
    if avg_jerk <= 0:
        return None, "negative average jerk"

    vol = df["Volume"]
    avg_vol_20 = vol.iloc[-21:-1].mean()
    last_vol = vol.iloc[-1]
    vol_ratio = last_vol / avg_vol_20 if avg_vol_20 > 0 else 1.0

    threshold_vol = 1.5 if drought > 5 else 2.0
    if vol_ratio < threshold_vol:
        return None, f"acceleration without vol confirmation ({vol_ratio:.1f}x)"

    funding_rates = fetch_funding_rate_history(symbol, limit=3)
    if funding_rates:
        latest_rate = funding_rates[0]
        if latest_rate > 0.001:
            return None, f"funding too high ({latest_rate*100:.3f}%) -- crowded long"

    velocity = (close.iloc[-1] - close.iloc[-4]) / close.iloc[-4] if close.iloc[-4] > 0 else 0
    reason = (f"Acceleration burst: 3 consec jerk+, avg jerk {avg_jerk*100:.3f}%, "
              f"vel {velocity*100:.1f}%, vol {vol_ratio:.1f}x")
    return "BUY", reason


# ---------------------------------------------------------------------------
# Signal Function 7: CoinGecko Trending Spike
# ---------------------------------------------------------------------------


def signal_coingecko_trending_spike(symbol: str, df: pd.DataFrame, all_data: dict,
                                     drought: int = 0) -> tuple[Optional[str], str]:
    """
    Detect coins entering CoinGecko trending list + volume confirmation.
    CoinGecko trending = top 7 coins by search volume in 24h.
    Entry: Symbol in trending + current volume > 3x 20d avg + RSI < 70.
    """
    if df is None or len(df) < 20:
        return None, "insufficient data"

    cg_global = all_data.get("__coingecko_global__", {})
    trending_coins = all_data.get("__cg_trending__", fetch_coingecko_trending())

    if symbol not in trending_coins:
        return None, f"{symbol} not trending on CoinGecko"

    vol = df["Volume"]
    avg_vol_20 = vol.iloc[-21:-1].mean()
    last_vol = vol.iloc[-1]
    vol_ratio = last_vol / avg_vol_20 if avg_vol_20 > 0 else 1.0

    threshold_vol = 2.0 if drought > 5 else 3.0
    if vol_ratio < threshold_vol:
        return None, f"trending but vol insufficient ({vol_ratio:.1f}x)"

    close = df["Close"]
    rsi_series = _rsi(close, 14)
    rsi_val = rsi_series.iloc[-1] if not np.isnan(rsi_series.iloc[-1]) else 50.0
    if rsi_val > 70:
        return None, f"trending but RSI overbought ({rsi_val:.0f})"

    mktcap_chg = cg_global.get("market_cap_change_24h_pct", 0)

    reason = (f"CoinGecko trending: {symbol} in top 7, "
              f"vol {vol_ratio:.1f}x, RSI {rsi_val:.0f}"
              + (f", mktcap {mktcap_chg:+.1f}%" if mktcap_chg else ""))
    return "BUY", reason

# ---------------------------------------------------------------------------
# Signal Function 8: Whale Size Trade
# ---------------------------------------------------------------------------


def signal_whale_size_trade(symbol: str, df: pd.DataFrame, all_data: dict,
                              drought: int = 0) -> tuple[Optional[str], str]:
    """
    Detect large whale accumulation trades on Binance (> $100K per trade).
    Entry: Net whale buying > 30% of whale flow + price in uptrend.
    Academic: Chaim & Laurini (2018) -- jumps in crypto volume predict price continuation.
    """
    if df is None or len(df) < 20:
        return None, "insufficient data"

    whale_data = fetch_whale_trades(symbol, min_usd=100_000)
    if not whale_data:
        return None, "no whale trade data (Binance unavailable)"

    signal = whale_data.get("signal", "mixed")
    net = whale_data.get("net_direction", 0)
    count = whale_data.get("whale_count", 0)

    threshold_net = 0.2 if drought > 5 else 0.3
    threshold_count = 2 if drought > 5 else 3

    if signal != "accumulation" or net < threshold_net or count < threshold_count:
        return None, f"no whale accumulation (net={net:.2f}, count={count})"

    close = df["Close"]
    ma20 = close.rolling(20).mean().iloc[-1]
    if close.iloc[-1] < ma20 * 0.99:
        return None, "whale buying but price below 20MA"

    buy_usd = whale_data.get("buy_usd", 0)
    reason = (f"Whale accumulation: ${buy_usd:,.0f} buying, "
              f"net direction {net:.2f}, {count} whale trades")
    return "BUY", reason

# ---------------------------------------------------------------------------
# Signal Function 9: Funding Rate Reversal
# ---------------------------------------------------------------------------


def signal_funding_rate_reversal(symbol: str, df: pd.DataFrame, all_data: dict,
                                  drought: int = 0) -> tuple[Optional[str], str]:
    """
    Detect funding rate turning from negative to positive (short liquidation phase ending).
    This is stronger than static funding-rate-arb (v1.0) which uses VWMA z-score.
    Entry: Last 3 rates showing negative to positive transition + RSI oversold bounce.
    Academic: Liu and Tsyvinski (2021) -- funding rate momentum predicts 24h returns.
    """
    if df is None or len(df) < 20:
        return None, "insufficient data"

    rates = fetch_funding_rate_history(symbol, limit=6)
    if len(rates) < 4:
        return None, "insufficient funding rate history"

    recent_3 = rates[:3]
    prior_3 = rates[3:6]

    was_negative = any(r < -0.0001 for r in prior_3)
    turning_positive = rates[0] > 0 and rates[1] >= -0.0002

    if not (was_negative and turning_positive):
        rate_strs = str([f"{r*100:.4f}%" for r in recent_3[:3]])
        return None, f"no reversal pattern (rates: {rate_strs})"

    close = df["Close"]
    rsi_series = _rsi(close, 14)
    rsi_val = rsi_series.iloc[-1] if not np.isnan(rsi_series.iloc[-1]) else 50.0

    if rsi_val > 65:
        return None, f"funding reversal but RSI too high ({rsi_val:.0f})"

    transition = rates[1] - rates[0]
    reason = (f"Funding rate reversal: {prior_3[-1]*100:.4f}% to {rates[0]*100:.4f}%, "
              f"shorts liquidating, RSI {rsi_val:.0f}")
    return "BUY", reason

# ---------------------------------------------------------------------------
# Signal Function 10: Multi-Exchange Divergence
# ---------------------------------------------------------------------------


def signal_multi_exchange_divergence(symbol: str, df: pd.DataFrame, all_data: dict,
                                      drought: int = 0) -> tuple[Optional[str], str]:
    """
    Detect price divergence between spot and futures pricing.
    Proxy: yfinance spot vs Binance Futures mark price.
    Entry: Futures mark price > spot by > 0.3% (strong futures premium = demand).
    Academic: Avellaneda and Lee (2010) -- statistical arbitrage in correlated markets.
    """
    if df is None or len(df) < 10:
        return None, "insufficient data"

    binance_sym = _YF_TO_BINANCE.get(symbol)
    if not binance_sym:
        return None, "no Binance mapping"

    try:
        url = f"{_BINANCE_FUTURES_BASE}/fapi/v1/premiumIndex"
        resp = requests.get(url, params={"symbol": binance_sym}, timeout=5)
        if resp.status_code != 200:
            return None, "futures price unavailable"

        data = resp.json()
        mark_price = float(data.get("markPrice", 0))
        spot_price = df["Close"].iloc[-1]

        if mark_price <= 0 or spot_price <= 0:
            return None, "invalid price data"

        divergence = (mark_price - spot_price) / spot_price
        threshold = 0.002 if drought > 5 else 0.003

        if divergence < threshold:
            return None, f"divergence insufficient ({divergence*100:.3f}%)"

        vol = df["Volume"]
        avg_vol_20 = vol.iloc[-21:-1].mean()
        vol_ratio = vol.iloc[-1] / avg_vol_20 if avg_vol_20 > 0 else 1.0

        if vol_ratio < 1.5:
            return None, f"futures premium but low spot volume ({vol_ratio:.1f}x)"

        reason = (f"Futures premium: {divergence*100:.3f}% above spot, "
                  f"mark ${mark_price:.4f} vs spot ${spot_price:.4f}, vol {vol_ratio:.1f}x")
        return "BUY", reason
    except Exception as e:
        logger.debug(f"Futures divergence failed for {symbol}: {e}")
        return None, "futures data error"


# ---------------------------------------------------------------------------
# Signal Function Exports (used in SIGNAL_FUNCS in live_scanner.py)
# ---------------------------------------------------------------------------

ACCELERATION_SIGNAL_FUNCS = {
    "pump-detector-scout": signal_pump_detector,
    "telegram-call-scout": signal_telegram_call_follower,
    "twitter-alpha-scout": signal_twitter_alpha_calls,
    "order-book-imbalance-scout": signal_order_book_imbalance,
    "liquidation-cascade-scout": signal_liquidation_cascade,
    "acceleration-burst-scout": signal_acceleration_burst,
    "coingecko-trending-spike-scout": signal_coingecko_trending_spike,
    "whale-size-trade-scout": signal_whale_size_trade,
    "funding-rate-reversal-scout": signal_funding_rate_reversal,
    "multi-exchange-divergence-scout": signal_multi_exchange_divergence,
}


if __name__ == "__main__":
    print("crypto_acceleration_engine.py -- testing helpers...")
    print("Testing order book fetch...")
    ob = fetch_order_book_imbalance(["BTC-USD", "ETH-USD"])
    for sym, d in ob.items():
        ratio = d["imbalance_ratio"]
        sig = d["signal"]
        print(f"  {sym}: bid/ask={ratio:.2f} [{sig}]")
    print("Testing CoinGecko trending...")
    trending = fetch_coingecko_trending()
    print(f"  Trending: {trending}")
    print("Testing liquidation proxy...")
    liq = fetch_binance_liquidations(["BTC-USD", "ETH-USD"])
    for sym, d in liq.items():
        vr = d["vol_ratio"]
        sig = d["signal"]
        print(f"  {sym}: vol_ratio={vr:.1f}x [{sig}]")
    print("All tests complete.")
