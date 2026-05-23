"""
ALPHA_ENGINE -- Binance Futures Sentiment Module
=================================================
Fetches FREE Binance Futures sentiment data (no API key required) and
exposes it as signal overlays for the scanner.

Endpoints used (all public, no auth):
  - Top Trader Long/Short Account Ratio
  - Taker Buy/Sell Volume Ratio
  - Open Interest History

Strategy:
  - binance_sentiment_contrarian: Contrarian positioning against crowded trades
    L/S ratio > 2.5 AND taker sell > 55% → SHORT (crowd overleveraged long)
    L/S ratio < 0.4 AND taker buy > 55% → LONG  (crowd overleveraged short)
    Based on: Cont & Bouchaud (2000) herding model, Garman (1976) microstructure

References:
  - Binance Futures Data API docs (public endpoints)
  - Cont, R. & Bouchaud, J.-P. (2000). Herd Behavior and Aggregate Fluctuations
  - Garman, M.B. (1976). Market Microstructure. J. Financial Economics 3(3)
"""

import json
import logging
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_FAPI_BASES = [
    "https://fapi.binance.com",
    "https://fapi1.binance.com",
    "https://fapi2.binance.com",
]
_BASE_URL = "https://fapi.binance.com/futures/data"
_TIMEOUT = 5  # seconds
_RATE_LIMIT_DELAY = 0.05  # 50ms between requests (safe for 1200 req/min)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fetch_json(url: str) -> list:
    """Fetch JSON from a URL with timeout and fapi failover. Returns [] on any failure.

    When all Binance endpoints fail (geo-block on GitHub Actions), tries Bybit
    as a fallback for long/short ratio and open interest data.
    """
    # If the URL is on fapi.binance.com, try all fapi endpoints
    urls_to_try = [url]
    for fapi_base in _FAPI_BASES:
        if "fapi.binance.com" in url and fapi_base != "https://fapi.binance.com":
            urls_to_try.append(url.replace("https://fapi.binance.com", fapi_base))

    for try_url in urls_to_try:
        try:
            req = urllib.request.Request(try_url, headers={"User-Agent": "AlphaEngine/1.0"})
            with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data if isinstance(data, list) else []
        except urllib.error.HTTPError as e:
            if e.code in (451, 403):
                logger.debug("HTTP %d from %s, trying next endpoint", e.code, try_url)
                continue
            logger.warning("HTTP %d fetching %s", e.code, try_url)
            continue
        except urllib.error.URLError as e:
            logger.debug("URL error fetching %s: %s, trying next", try_url, e.reason)
            continue
        except Exception as e:
            logger.debug("Failed to fetch %s: %s, trying next", try_url, e)
            continue

    # All Binance endpoints failed -- try Bybit fallback
    bybit_result = _bybit_sentiment_fallback(url)
    if bybit_result:
        return bybit_result

    logger.warning("All endpoints (Binance + Bybit) failed for %s", url)
    return []


def _bybit_sentiment_fallback(original_url: str) -> list | None:
    """Bybit fallback for Binance futures sentiment data endpoints."""
    import re
    _bybit_base = "https://api.bybit.com"

    # Extract symbol and limit from original URL
    sym_m = re.search(r"symbol=([A-Z0-9]+)", original_url)
    lim_m = re.search(r"limit=(\d+)", original_url)
    symbol = sym_m.group(1) if sym_m else None
    limit = int(lim_m.group(1)) if lim_m else 30
    if not symbol:
        return None

    try:
        # Open Interest History → Bybit v5 open-interest
        if "openInterestHist" in original_url:
            url = f"{_bybit_base}/v5/market/open-interest?category=linear&symbol={symbol}&intervalTime=4h&limit={limit}"
            req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine/1.0"})
            with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if data.get("retCode") == 0 and data.get("result", {}).get("list"):
                result = []
                for item in data["result"]["list"]:
                    result.append({
                        "timestamp": int(item.get("timestamp", 0)),
                        "sumOpenInterest": item.get("openInterest", "0"),
                        "sumOpenInterestValue": "0",  # Bybit doesn't provide USD value directly
                    })
                logger.info("Bybit fallback OK for %s OI history (%d entries)", symbol, len(result))
                return result

        # Long/Short Ratio → Bybit v5 account-ratio
        if "topLongShortAccountRatio" in original_url:
            url = f"{_bybit_base}/v5/market/account-ratio?category=linear&symbol={symbol}&period=4h&limit={limit}"
            req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine/1.0"})
            with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if data.get("retCode") == 0 and data.get("result", {}).get("list"):
                result = []
                for item in data["result"]["list"]:
                    buy_ratio = float(item.get("buyRatio", 0.5))
                    sell_ratio = float(item.get("sellRatio", 0.5))
                    ls_ratio = buy_ratio / sell_ratio if sell_ratio > 0 else 1.0
                    result.append({
                        "timestamp": int(item.get("timestamp", 0)),
                        "longShortRatio": str(ls_ratio),
                        "longAccount": str(buy_ratio),
                        "shortAccount": str(sell_ratio),
                    })
                logger.info("Bybit fallback OK for %s L/S ratio (%d entries)", symbol, len(result))
                return result

        # Taker Buy/Sell Ratio -- no direct Bybit equivalent, skip
        if "takerlongshortRatio" in original_url:
            logger.debug("No Bybit fallback available for taker ratio")
            return None

    except Exception as e:
        logger.debug("Bybit sentiment fallback failed for %s: %s", symbol, e)

    return None


def _smart_round(value, decimals=2):
    """Round price smartly based on magnitude."""
    try:
        v = float(value)
        if v >= 1000:
            return round(v, 2)
        elif v >= 1:
            return round(v, 4)
        else:
            return round(v, 6)
    except (ValueError, TypeError):
        return value


def _get_category(symbol: str) -> str:
    """Determine asset category from symbol."""
    sym = symbol.upper().replace("USDT", "").replace("USD", "")
    if sym == "BTC":
        return "crypto-major"
    elif sym in ("ETH", "BNB", "SOL", "XRP", "ADA", "AVAX", "DOT", "MATIC"):
        return "crypto-large"
    else:
        return "crypto-alt"


# ---------------------------------------------------------------------------
# Data Fetchers
# ---------------------------------------------------------------------------

def fetch_long_short_ratio(symbol: str, period: str = "4h", limit: int = 30) -> list:
    """
    Fetch top trader long/short account ratio from Binance Futures.

    Returns list of dicts:
        {timestamp, longShortRatio, longAccount, shortAccount}
    """
    url = (
        f"{_BASE_URL}/topLongShortAccountRatio"
        f"?symbol={symbol.upper()}&period={period}&limit={limit}"
    )
    raw = _fetch_json(url)
    results = []
    for entry in raw:
        try:
            results.append({
                "timestamp": int(entry.get("timestamp", 0)),
                "longShortRatio": float(entry.get("longShortRatio", 1.0)),
                "longAccount": float(entry.get("longAccount", 0.5)),
                "shortAccount": float(entry.get("shortAccount", 0.5)),
            })
        except (ValueError, TypeError):
            continue
    return results


def fetch_taker_ratio(symbol: str, period: str = "4h", limit: int = 30) -> list:
    """
    Fetch taker buy/sell volume ratio from Binance Futures.

    Returns list of dicts:
        {timestamp, buySellRatio, buyVol, sellVol}
    """
    url = (
        f"{_BASE_URL}/takerlongshortRatio"
        f"?symbol={symbol.upper()}&period={period}&limit={limit}"
    )
    raw = _fetch_json(url)
    results = []
    for entry in raw:
        try:
            results.append({
                "timestamp": int(entry.get("timestamp", 0)),
                "buySellRatio": float(entry.get("buySellRatio", 1.0)),
                "buyVol": float(entry.get("buyVol", 0)),
                "sellVol": float(entry.get("sellVol", 0)),
            })
        except (ValueError, TypeError):
            continue
    return results


def fetch_oi_history(symbol: str, period: str = "4h", limit: int = 30) -> list:
    """
    Fetch open interest history from Binance Futures.

    Returns list of dicts:
        {timestamp, sumOpenInterest, sumOpenInterestValue}
    """
    url = (
        f"{_BASE_URL}/openInterestHist"
        f"?symbol={symbol.upper()}&period={period}&limit={limit}"
    )
    raw = _fetch_json(url)
    results = []
    for entry in raw:
        try:
            results.append({
                "timestamp": int(entry.get("timestamp", 0)),
                "sumOpenInterest": float(entry.get("sumOpenInterest", 0)),
                "sumOpenInterestValue": float(entry.get("sumOpenInterestValue", 0)),
            })
        except (ValueError, TypeError):
            continue
    return results


# ---------------------------------------------------------------------------
# Sentiment Scoring
# ---------------------------------------------------------------------------

def get_sentiment_score(symbol: str) -> dict:
    """
    Combine L/S ratio, taker ratio, and OI into a single sentiment score.

    Returns dict:
        score:          float from -1 (extreme bearish) to +1 (extreme bullish)
        ls_ratio:       latest long/short ratio
        taker_ratio:    latest taker buy/sell ratio
        oi_change_pct:  OI percent change over the window
        signal:         "BULLISH" | "BEARISH" | "NEUTRAL"
        reason:         human-readable explanation
    """
    result = {
        "score": 0.0,
        "ls_ratio": 1.0,
        "taker_ratio": 1.0,
        "oi_change_pct": 0.0,
        "signal": "NEUTRAL",
        "reason": "insufficient data",
    }

    # Fetch all three data sources
    ls_data = fetch_long_short_ratio(symbol)
    time.sleep(_RATE_LIMIT_DELAY)
    taker_data = fetch_taker_ratio(symbol)
    time.sleep(_RATE_LIMIT_DELAY)
    oi_data = fetch_oi_history(symbol)

    if not ls_data or not taker_data or not oi_data:
        return result

    # --- Long/Short Ratio ---
    latest_ls = ls_data[-1]["longShortRatio"]
    result["ls_ratio"] = round(latest_ls, 4)

    # Contrarian logic: crowded longs = bearish signal, crowded shorts = bullish
    ls_score = 0.0
    if latest_ls > 2.0:
        # Crowded long -- contrarian bearish
        ls_score = -min(1.0, (latest_ls - 1.0) / 2.0)
    elif latest_ls < 0.5:
        # Crowded short -- contrarian bullish
        ls_score = min(1.0, (1.0 - latest_ls) / 1.0)
    else:
        # Mild scoring in the normal range
        ls_score = -(latest_ls - 1.0) * 0.3

    # --- Taker Buy/Sell Ratio ---
    latest_taker = taker_data[-1]["buySellRatio"]
    result["taker_ratio"] = round(latest_taker, 4)

    # Buy/sell ratio: >1 = more buying, <1 = more selling
    total_vol = taker_data[-1]["buyVol"] + taker_data[-1]["sellVol"]
    buy_pct = (taker_data[-1]["buyVol"] / total_vol * 100) if total_vol > 0 else 50.0

    taker_score = 0.0
    if buy_pct > 60:
        taker_score = min(0.5, (buy_pct - 50) / 20.0)
    elif buy_pct < 40:
        taker_score = -min(0.5, (50 - buy_pct) / 20.0)
    else:
        taker_score = (buy_pct - 50) / 50.0

    # --- Open Interest Change ---
    if len(oi_data) >= 2:
        oi_first = oi_data[0]["sumOpenInterestValue"]
        oi_last = oi_data[-1]["sumOpenInterestValue"]
        if oi_first > 0:
            oi_change = (oi_last - oi_first) / oi_first * 100
        else:
            oi_change = 0.0
    else:
        oi_change = 0.0

    result["oi_change_pct"] = round(oi_change, 2)

    # OI rising = more conviction in current direction
    # OI rising + bearish LS = stronger bearish signal
    # OI falling = positions closing, less conviction
    oi_score = 0.0
    if oi_change > 10:
        oi_score = 0.2 if ls_score > 0 else -0.2  # amplifies existing direction
    elif oi_change < -10:
        oi_score = 0.1  # deleveraging = slight bullish (cascade over)

    # --- Composite Score ---
    # Weights: L/S ratio is strongest contrarian signal
    composite = (ls_score * 0.5) + (taker_score * 0.3) + (oi_score * 0.2)
    composite = max(-1.0, min(1.0, composite))

    result["score"] = round(composite, 4)

    # Determine signal
    reasons = []
    if composite > 0.2:
        result["signal"] = "BULLISH"
        if latest_ls < 0.5:
            reasons.append(f"crowded short (L/S={latest_ls:.2f})")
        if buy_pct > 55:
            reasons.append(f"aggressive buying ({buy_pct:.1f}%)")
        if oi_change < -10:
            reasons.append(f"deleveraging (OI {oi_change:+.1f}%)")
    elif composite < -0.2:
        result["signal"] = "BEARISH"
        if latest_ls > 2.0:
            reasons.append(f"crowded long (L/S={latest_ls:.2f})")
        if buy_pct < 45:
            reasons.append(f"aggressive selling ({buy_pct:.1f}%)")
        if oi_change > 10:
            reasons.append(f"OI rising into bearish setup ({oi_change:+.1f}%)")
    else:
        result["signal"] = "NEUTRAL"
        reasons.append(f"mixed signals (L/S={latest_ls:.2f}, buy%={buy_pct:.1f}%)")

    result["reason"] = "; ".join(reasons) if reasons else "balanced sentiment"
    return result


def get_sentiment_batch(symbols: list) -> dict:
    """
    Batch sentiment scoring for multiple symbols. Rate-limit aware.

    Args:
        symbols: list of symbol strings (e.g., ["BTCUSDT", "ETHUSDT"])

    Returns:
        dict mapping symbol -> sentiment score dict
    """
    results = {}
    for i, symbol in enumerate(symbols):
        try:
            results[symbol] = get_sentiment_score(symbol)
        except Exception as e:
            logger.warning("Sentiment fetch failed for %s: %s", symbol, e)
            results[symbol] = {
                "score": 0.0,
                "ls_ratio": 1.0,
                "taker_ratio": 1.0,
                "oi_change_pct": 0.0,
                "signal": "NEUTRAL",
                "reason": f"fetch error: {e}",
            }
        # Rate limiting: 3 requests per symbol, keep well under 1200/min
        if i < len(symbols) - 1:
            time.sleep(0.2)
    return results


# ---------------------------------------------------------------------------
# Strategy: Binance Sentiment Contrarian
# ---------------------------------------------------------------------------

def binance_sentiment_contrarian(data: dict, symbol: str) -> list:
    """
    Contrarian strategy based on Binance Futures sentiment data.

    Logic:
      - L/S ratio > 2.5 AND taker sell > 55% → SHORT (crowd overleveraged long)
      - L/S ratio < 0.4 AND taker buy  > 55% → LONG  (crowd overleveraged short)
      - TP = 1.5%, SL = 2%

    Args:
        data: dict with price data (must have 'close' or 'price' key)
        symbol: trading pair (e.g., "BTCUSDT")

    Returns:
        list of signal dicts compatible with alpha_engine scanner
    """
    signals = []

    # Skip non-crypto symbols — Binance sentiment only applies to USDT pairs
    if not symbol.endswith("USDT"):
        return signals

    # Get current price from data
    price = None
    if isinstance(data, dict):
        price = data.get("close") or data.get("price") or data.get("last_price")
        if isinstance(price, (list, tuple)):
            price = price[-1] if price else None
    if price is None:
        logger.warning("No price data for %s, skipping sentiment contrarian", symbol)
        return signals

    try:
        price = float(price)
    except (ValueError, TypeError):
        return signals

    # Fetch sentiment
    sentiment = get_sentiment_score(symbol)
    ls_ratio = sentiment["ls_ratio"]
    taker_ratio = sentiment["taker_ratio"]

    # Calculate taker buy percentage from raw data
    taker_data = fetch_taker_ratio(symbol, period="4h", limit=5)
    if not taker_data:
        return signals

    latest_taker = taker_data[-1]
    total_vol = latest_taker["buyVol"] + latest_taker["sellVol"]
    if total_vol == 0:
        return signals

    buy_pct = latest_taker["buyVol"] / total_vol * 100
    sell_pct = 100 - buy_pct

    tp_pct = 0.015  # 1.5%
    sl_pct = 0.02   # 2.0%

    # --- SHORT signal: crowd overleveraged long ---
    if ls_ratio > 2.5 and sell_pct > 55:
        entry = _smart_round(price)
        tp = _smart_round(price * (1 - tp_pct))
        sl = _smart_round(price * (1 + sl_pct))
        rr = round(tp_pct / sl_pct, 2)
        conf = min(0.82, 0.55 + (ls_ratio - 2.5) * 0.05 + (sell_pct - 55) * 0.005)

        signals.append({
            "strategy": "binance_sentiment_contrarian",
            "symbol": symbol,
            "category": _get_category(symbol),
            "signal_type": "SELL",
            "entry_price": entry,
            "take_profit": tp,
            "stop_loss": sl,
            "confidence": round(conf, 2),
            "risk_reward": rr,
            "reason": (
                f"Contrarian SHORT: crowd overleveraged long "
                f"(L/S={ls_ratio:.2f} > 2.5, taker sell={sell_pct:.1f}% > 55%). "
                f"OI change={sentiment['oi_change_pct']:+.1f}%. "
                f"Cont & Bouchaud (2000): herding reversals."
            ),
            "timeframe": "4h",
            "extra": {
                "ls_ratio": ls_ratio,
                "taker_buy_pct": round(buy_pct, 2),
                "taker_sell_pct": round(sell_pct, 2),
                "oi_change_pct": sentiment["oi_change_pct"],
                "sentiment_score": sentiment["score"],
                "source": "Binance Futures public API (no auth)",
            },
            "timestamp": _now_iso(),
        })

    # --- LONG signal: crowd overleveraged short ---
    elif ls_ratio < 0.4 and buy_pct > 55:
        entry = _smart_round(price)
        tp = _smart_round(price * (1 + tp_pct))
        sl = _smart_round(price * (1 - sl_pct))
        rr = round(tp_pct / sl_pct, 2)
        conf = min(0.82, 0.55 + (0.4 - ls_ratio) * 0.1 + (buy_pct - 55) * 0.005)

        signals.append({
            "strategy": "binance_sentiment_contrarian",
            "symbol": symbol,
            "category": _get_category(symbol),
            "signal_type": "BUY",
            "entry_price": entry,
            "take_profit": tp,
            "stop_loss": sl,
            "confidence": round(conf, 2),
            "risk_reward": rr,
            "reason": (
                f"Contrarian LONG: crowd overleveraged short "
                f"(L/S={ls_ratio:.2f} < 0.4, taker buy={buy_pct:.1f}% > 55%). "
                f"OI change={sentiment['oi_change_pct']:+.1f}%. "
                f"Cont & Bouchaud (2000): herding reversals."
            ),
            "timeframe": "4h",
            "extra": {
                "ls_ratio": ls_ratio,
                "taker_buy_pct": round(buy_pct, 2),
                "taker_sell_pct": round(sell_pct, 2),
                "oi_change_pct": sentiment["oi_change_pct"],
                "sentiment_score": sentiment["score"],
                "source": "Binance Futures public API (no auth)",
            },
            "timestamp": _now_iso(),
        })

    return signals


# ---------------------------------------------------------------------------
# Strategy Registry
# ---------------------------------------------------------------------------

SENTIMENT_STRATEGIES = {
    "binance_sentiment_contrarian": binance_sentiment_contrarian,
}


# ---------------------------------------------------------------------------
# CLI test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    test_symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    print("=" * 60)
    print("Binance Futures Sentiment Module -- Live Test")
    print("=" * 60)

    for sym in test_symbols:
        print(f"\n--- {sym} ---")
        score = get_sentiment_score(sym)
        print(f"  Score:      {score['score']:+.4f}")
        print(f"  Signal:     {score['signal']}")
        print(f"  L/S Ratio:  {score['ls_ratio']}")
        print(f"  Taker Ratio:{score['taker_ratio']}")
        print(f"  OI Change:  {score['oi_change_pct']:+.2f}%")
        print(f"  Reason:     {score['reason']}")

        # Test strategy with mock price
        mock_data = {"close": 83000 if sym == "BTCUSDT" else 3200 if sym == "ETHUSDT" else 130}
        sigs = binance_sentiment_contrarian(mock_data, sym)
        if sigs:
            for s in sigs:
                print(f"  ** SIGNAL: {s['signal_type']} @ {s['entry_price']} "
                      f"TP={s['take_profit']} SL={s['stop_loss']} "
                      f"conf={s['confidence']}")
        else:
            print("  No signal (thresholds not met)")

    print("\n" + "=" * 60)
    print("Batch test:")
    batch = get_sentiment_batch(test_symbols)
    for sym, s in batch.items():
        print(f"  {sym}: {s['signal']} ({s['score']:+.4f})")
