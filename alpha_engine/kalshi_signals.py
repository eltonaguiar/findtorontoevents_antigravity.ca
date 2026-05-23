"""
Kalshi Prediction Market Signals for Crypto Trading

Kalshi is a CFTC-regulated US prediction exchange with extensive crypto series:
  - BTC, ETH, SOL, DOGE, XRP, AVAX, DOT, LINK, LTC, BCH, XLM, SHIB, BNB, ADA, HYPE
  - Timeframes: 15-minute, hourly, daily, weekly, monthly, annual

Strategy:
  1. Multi-Timeframe Consensus: When 15m, hourly, daily all agree → strong signal
  2. Timeframe Divergence: Short-term vs long-term disagreement → mean reversion
  3. Implied Distribution: Extract expected price range from binary options ladder

API Base: https://api.elections.kalshi.com/trade-api/v2
No API key required for read-only market data.

Output: alpha_engine/data/kalshi_signals.json
"""

import json
import logging
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "kalshi_signals.json")

KALSHI_API_BASE = "https://api.elections.kalshi.com/trade-api/v2"
REQUEST_TIMEOUT = 15

# ---------------------------------------------------------------------------
# Crypto series on Kalshi — ticker prefix maps to (symbol, timeframe_label)
# ---------------------------------------------------------------------------
KALSHI_CRYPTO_SERIES = {
    # BTC series
    "KXBTC15M":   ("BTCUSDT", "15m"),
    "KXBTC":      ("BTCUSDT", "1h"),
    "KXBTCD":     ("BTCUSDT", "1d"),
    "BTCD":       ("BTCUSDT", "1d"),
    "KXBTCMAXW":  ("BTCUSDT", "1w"),
    "KXBTCMAXM":  ("BTCUSDT", "1M"),
    "BTCMAXM":    ("BTCUSDT", "1M"),
    "KXBTCMAXY":  ("BTCUSDT", "1y"),
    "KXBTCMINY":  ("BTCUSDT", "1y"),
    "KXBTCATH":   ("BTCUSDT", "event"),
    # ETH series
    "KXETH15M":   ("ETHUSDT", "15m"),
    "KXETH":      ("ETHUSDT", "1h"),
    "KXETHD":     ("ETHUSDT", "1d"),
    "ETHD":       ("ETHUSDT", "1d"),
    # SOL series
    "KXSOL15M":   ("SOLUSDT", "15m"),
    "KXSOL":      ("SOLUSDT", "1h"),
    "KXSOLD":     ("SOLUSDT", "1d"),
    # DOGE series
    "KXDOGE15M":  ("DOGEUSDT", "15m"),
    "KXDOGE":     ("DOGEUSDT", "1h"),
    "KXDOGED":    ("DOGEUSDT", "1d"),
    # XRP series
    "KXXRP15M":   ("XRPUSDT", "15m"),
    "KXXRP":      ("XRPUSDT", "1h"),
    "KXXRPD":     ("XRPUSDT", "1d"),
    # AVAX series
    "KXAVAX":     ("AVAXUSDT", "1h"),
    "KXAVAXD":    ("AVAXUSDT", "1d"),
    # Others
    "KXLINK":     ("LINKUSDT", "1h"),
    "KXLINKD":    ("LINKUSDT", "1d"),
    "KXDOT":      ("DOTUSDT", "1h"),
    "KXDOTD":     ("DOTUSDT", "1d"),
    "KXLTC":      ("LTCUSDT", "1h"),
    "KXLTCD":     ("LTCUSDT", "1d"),
    "KXBNB15M":   ("BNBUSDT", "15m"),
    "KXADA15M":   ("ADAUSDT", "15m"),
    "KXHYPE15M":  ("HYPEUSDT", "15m"),
    "KXSHIBA":    ("SHIBUSDT", "1h"),
    "KXSHIBAD":   ("SHIBUSDT", "1d"),
}

# ---------------------------------------------------------------------------
# Non-crypto / macro series on Kalshi — (symbol, timeframe, asset_class)
# These cover S&P 500, NASDAQ, gold, oil, and Fed/macro event markets.
# Kalshi's API may not list all of these at any given time — the scanner
# handles missing series gracefully (zero signals, no crash).
# ---------------------------------------------------------------------------
KALSHI_MACRO_SERIES: dict[str, tuple[str, str, str]] = {
    # S&P 500 (SPY proxy)
    "INXD":       ("SPY", "1d", "index"),
    "INXW":       ("SPY", "1w", "index"),
    "INXM":       ("SPY", "1M", "index"),
    "INXY":       ("SPY", "1y", "index"),
    "KXSPXD":     ("SPY", "1d", "index"),
    "KXSPY":      ("SPY", "1d", "index"),
    # NASDAQ-100 (QQQ proxy)
    "NASD":       ("QQQ", "1d", "index"),
    "NASW":       ("QQQ", "1w", "index"),
    "NASM":       ("QQQ", "1M", "index"),
    "KXNAS":      ("QQQ", "1d", "index"),
    # Gold
    "KXGOLD":     ("XAUUSD", "1d", "commodity"),
    "KXGOLDD":    ("XAUUSD", "1d", "commodity"),
    "KXGOLDW":    ("XAUUSD", "1w", "commodity"),
    # Oil (WTI Crude)
    "KXOIL":      ("CLUSD", "1d", "commodity"),
    "KXOILD":     ("CLUSD", "1d", "commodity"),
    # Fed Funds / Interest Rate (proxy: TLT for bond direction)
    "KXFED":      ("TLT", "event", "macro"),
    "KXRATE":     ("TLT", "event", "macro"),
    "FEDRATE":    ("TLT", "event", "macro"),
    # Inflation / CPI (proxy: TIP for inflation direction)
    "KXCPI":      ("TIP", "event", "macro"),
    "KXINFLATION":("TIP", "event", "macro"),
    # FOMC decision (proxy: SPY — rate decisions move equities)
    "KXFOMC":     ("SPY", "event", "macro"),
    # Individual stocks (if Kalshi lists them)
    "KXAAPL":     ("AAPL", "1d", "equity"),
    "KXTSLA":     ("TSLA", "1d", "equity"),
    "KXNVDA":     ("NVDA", "1d", "equity"),
    "KXAMZN":     ("AMZN", "1d", "equity"),
    "KXMETA":     ("META", "1d", "equity"),
    "KXGOOGL":    ("GOOGL", "1d", "equity"),
    "KXMSFT":     ("MSFT", "1d", "equity"),
}

# Timeframe priority for consensus weighting (longer timeframes = more weight)
TF_WEIGHT = {"15m": 1, "1h": 2, "1d": 3, "1w": 4, "1M": 5, "1y": 6, "event": 2}

# Import shared asset class detection
try:
    from alpha_engine.config import detect_asset_class as _detect_asset_class, get_risk_params as _get_risk_params
except Exception:
    try:
        from config import detect_asset_class as _detect_asset_class, get_risk_params as _get_risk_params
    except Exception:
        def _detect_asset_class(symbol: str) -> str:
            return "crypto" if str(symbol).upper().endswith("USDT") else "equity"
        def _get_risk_params(asset_class: str):
            return (-0.03, 0.05, 14) if asset_class != "crypto" else (-0.08, 0.15, 7)

# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _fetch_json(url, params=None):
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "User-Agent": "AlphaEngine-KalshiScanner/1.0",
        "Accept": "application/json",
    })
    
    # Rate limit Kalshi API to prevent 429 errors
    import time
    time.sleep(0.35)

    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        logger.warning("HTTP %s fetching %s: %s", e.code, url, e.reason)
        return None
    except urllib.error.URLError as e:
        logger.warning("URL error fetching %s: %s", url, e.reason)
        return None
    except Exception as e:
        logger.warning("Unexpected error fetching %s: %s", url, e)
        return None


def _safe_float(val):
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# 1. Fetch Kalshi markets
# ---------------------------------------------------------------------------

def fetch_kalshi_events(series_ticker):
    """Fetch open events for a Kalshi series ticker."""
    result = _fetch_json(
        f"{KALSHI_API_BASE}/events",
        params={"status": "open", "series_ticker": series_ticker, "limit": "100"}
    )
    if not result:
        return []
    events = result.get("events") or []
    return events


def fetch_kalshi_markets_for_event(event_ticker):
    """Fetch all markets (price ranges) within a Kalshi event."""
    result = _fetch_json(
        f"{KALSHI_API_BASE}/markets",
        params={"event_ticker": event_ticker, "limit": "200"}
    )
    if not result:
        return []
    return result.get("markets") or []


def _extract_kalshi_probability(market):
    """Extract YES probability from a Kalshi market object.

    Kalshi API v2 (2026) changed field names:
      yes_ask -> yes_ask_dollars (string, 0-1 dollar range)
      yes_bid -> yes_bid_dollars, last_price -> last_price_dollars
    """
    # Try new dollar fields first (already 0-1 range)
    for key in ("yes_ask_dollars", "yes_bid_dollars", "last_price_dollars"):
        val = market.get(key)
        if val is not None:
            p = _safe_float(val)
            if p is not None:
                return round(p, 4)
    # Legacy cents format fallback
    for key in ("yes_ask", "last_price", "yes_bid"):
        val = market.get(key)
        if val is not None:
            p = _safe_float(val)
            if p is not None:
                return round(p / 100.0, 4)
    return None


def _parse_kalshi_strike(market):
    """
    Extract the price strike from a Kalshi market.

    Kalshi API v2 (2026) provides structured fields:
      floor_strike: float (e.g., 61399.99)
      strike_type: "greater" or "less"
      subtitle: "$61,400 or above"

    Falls back to ticker pattern and text parsing.
    Returns (float strike, bool is_above) or (None, None)
    """
    # Prefer structured fields (new API format)
    floor_strike = market.get("floor_strike")
    strike_type = market.get("strike_type")
    if floor_strike is not None and strike_type:
        strike = _safe_float(floor_strike)
        if strike is not None:
            is_above = (strike_type == "greater")
            return strike, is_above

    # Ticker pattern: T<price> or B<price> (may include decimals now)
    ticker = market.get("ticker") or ""
    t_match = re.search(r"-t([\d.]+)", ticker, re.IGNORECASE)
    b_match = re.search(r"-b([\d.]+)", ticker, re.IGNORECASE)
    if t_match:
        return _safe_float(t_match.group(1)), True
    if b_match:
        return _safe_float(b_match.group(1)), False

    # Text fallback: check subtitle first (has strike info), then title
    subtitle = market.get("subtitle") or ""
    title = market.get("title") or market.get("question") or ""
    text = (subtitle + " " + title).lower()

    above_match = re.search(r"(above|over|reach|>\s*)\$?\s*([\d,]+)", text)
    below_match = re.search(r"(below|under|<\s*)\$?\s*([\d,]+)", text)
    if above_match:
        return _safe_float(above_match.group(2).replace(",", "")), True
    if below_match:
        return _safe_float(below_match.group(2).replace(",", "")), False

    return None, None


# ---------------------------------------------------------------------------
# 2. Analyze Kalshi series for directional signals
# ---------------------------------------------------------------------------

def analyze_kalshi_series(series_ticker, symbol, timeframe):
    """
    Analyze one Kalshi series (e.g., KXBTC15M) for directional bias.

    Returns dict with:
        symbol, timeframe, direction, confidence, signal_strength,
        bullish_weight, bearish_weight, markets_analyzed, reason
    """
    events = fetch_kalshi_events(series_ticker)
    if not events:
        return None

    bullish_weight = 0.0
    bearish_weight = 0.0
    markets_analyzed = 0
    market_details = []

    for event in events[:5]:  # Process up to 5 recent events per series
        event_ticker = event.get("event_ticker") or event.get("ticker") or ""
        if not event_ticker:
            continue

        markets = fetch_kalshi_markets_for_event(event_ticker)

        for market in markets:
            prob = _extract_kalshi_probability(market)
            if prob is None:
                continue

            strike, is_above = _parse_kalshi_strike(market)

            if is_above is True:
                # "above $X" market: YES prob contributes to bullish weight
                volume = _safe_float(market.get("volume_fp") or market.get("volume") or 0) or 0
                weight = max(volume / 100_000, 0.01) * prob  # volume-weighted, floor to avoid zero
                bullish_weight += weight
                markets_analyzed += 1
                market_details.append(f"above ${strike:,.0f}: {prob:.0%}")
            elif is_above is False:
                # "below $X" market: YES prob contributes to bearish weight
                volume = _safe_float(market.get("volume_fp") or market.get("volume") or 0) or 0
                weight = max(volume / 100_000, 0.01) * prob  # volume-weighted, floor to avoid zero
                bearish_weight += weight
                markets_analyzed += 1
                market_details.append(f"below ${strike:,.0f}: {prob:.0%}")

    if markets_analyzed == 0:
        return None

    total_weight = bullish_weight + bearish_weight
    if total_weight == 0:
        return None

    bull_ratio = bullish_weight / total_weight
    bear_ratio = bearish_weight / total_weight

    # Signal strength: how decisive is the consensus
    signal_strength = abs(bull_ratio - bear_ratio)

    if bull_ratio > 0.60:
        direction = "LONG"
        confidence = round(0.50 + signal_strength * 0.35, 3)
    elif bear_ratio > 0.60:
        direction = "SHORT"
        confidence = round(0.50 + signal_strength * 0.35, 3)
    else:
        direction = "NEUTRAL"
        confidence = 0.30

    confidence = max(0.30, min(confidence, 0.82))

    tf_label = {"15m": "15-min", "1h": "hourly", "1d": "daily", "1w": "weekly",
                "1M": "monthly", "1y": "annual", "event": "event"}.get(timeframe, timeframe)

    sample_details = ", ".join(market_details[:3])
    reason = (
        f"Kalshi {tf_label} [{series_ticker}]: "
        f"bull_w={bullish_weight:.2f} bear_w={bearish_weight:.2f} | "
        f"{sample_details}"
    )

    return {
        "series": series_ticker,
        "symbol": symbol,
        "timeframe": timeframe,
        "direction": direction,
        "confidence": confidence,
        "signal_strength": round(signal_strength, 4),
        "bull_ratio": round(bull_ratio, 4),
        "bear_ratio": round(bear_ratio, 4),
        "markets_analyzed": markets_analyzed,
        "reason": reason,
    }


# ---------------------------------------------------------------------------
# 3. Multi-Timeframe Consensus
# ---------------------------------------------------------------------------

def build_mtf_consensus(symbol, series_results):
    """
    Build a multi-timeframe consensus signal for a symbol.

    Rules:
      - If all timeframes agree → STRONG signal (confidence boost)
      - If majority agree → MODERATE signal
      - Divergence (short vs long term disagree) → skip or flag
      - Longer timeframes get more weight

    Returns consensus dict or None if no clear signal.
    """
    if not series_results:
        return None

    # Only keep signals with actual direction
    directional = [r for r in series_results if r["direction"] in ("LONG", "SHORT")]
    if not directional:
        return None

    # Weighted vote
    long_weight = 0.0
    short_weight = 0.0
    for r in directional:
        tf = r["timeframe"]
        weight = TF_WEIGHT.get(tf, 1) * r["confidence"]
        if r["direction"] == "LONG":
            long_weight += weight
        else:
            short_weight += weight

    total = long_weight + short_weight
    if total == 0:
        return None

    long_pct = long_weight / total
    short_pct = short_weight / total

    # Count timeframes agreeing vs disagreeing
    long_tfs = [r["timeframe"] for r in directional if r["direction"] == "LONG"]
    short_tfs = [r["timeframe"] for r in directional if r["direction"] == "SHORT"]

    # All-timeframe agreement = strongest signal
    all_agree = len(long_tfs) == len(directional) or len(short_tfs) == len(directional)

    if long_pct >= 0.65:
        consensus_dir = "LONG"
        base_conf = long_pct * 0.82
    elif short_pct >= 0.65:
        consensus_dir = "SHORT"
        base_conf = short_pct * 0.82
    else:
        return None  # No clear consensus

    # Bonus for full agreement
    if all_agree and len(directional) >= 2:
        base_conf = min(base_conf * 1.10, 0.88)

    timeframes_used = [r["timeframe"] for r in directional]
    agreeing_count = len(long_tfs) if consensus_dir == "LONG" else len(short_tfs)
    total_tfs = len(directional)

    reasons = [r["reason"][:80] for r in directional[:3]]

    return {
        "symbol": symbol,
        "direction": consensus_dir,
        "confidence": round(base_conf, 3),
        "all_agree": all_agree,
        "timeframes_used": timeframes_used,
        "agreeing_tfs": agreeing_count,
        "total_tfs": total_tfs,
        "long_weight": round(long_weight, 3),
        "short_weight": round(short_weight, 3),
        "reason": (
            f"Kalshi MTF consensus [{agreeing_count}/{total_tfs} TFs agree]: "
            + " | ".join(timeframes_used)
        ),
        "sub_reasons": reasons,
    }


# ---------------------------------------------------------------------------
# 4. Main signal generation
# ---------------------------------------------------------------------------

def get_kalshi_signals(symbols=None, asset_classes=None):
    """
    Generate trading signals from Kalshi prediction markets.

    Fetches all available Kalshi series (crypto + macro/equity), runs MTF
    consensus, and returns a list of high-confidence signal dicts.

    Args:
        symbols: Optional list of symbols to filter (e.g., ['BTCUSDT', 'ETHUSDT'])
                 If None, fetches all available.
        asset_classes: Optional set of asset classes to scan (e.g., {'crypto', 'index'}).
                       If None, scans all asset classes.
    """
    # Group crypto series by symbol
    symbol_series = {}
    symbol_asset_class = {}  # track asset class per symbol
    for series_ticker, (sym, tf) in KALSHI_CRYPTO_SERIES.items():
        if symbols and sym not in symbols:
            continue
        if asset_classes and "crypto" not in asset_classes:
            continue
        if sym not in symbol_series:
            symbol_series[sym] = []
            symbol_asset_class[sym] = "crypto"
        symbol_series[sym].append((series_ticker, tf))

    # Group macro/equity series by symbol
    for series_ticker, (sym, tf, ac) in KALSHI_MACRO_SERIES.items():
        if symbols and sym not in symbols:
            continue
        if asset_classes and ac not in asset_classes:
            continue
        if sym not in symbol_series:
            symbol_series[sym] = []
            symbol_asset_class[sym] = ac
        symbol_series[sym].append((series_ticker, tf))

    all_signals = []

    for symbol, series_list in symbol_series.items():
        symbol_results = []

        for series_ticker, timeframe in series_list:
            logger.info("Analyzing Kalshi series %s (%s %s)...", series_ticker, symbol, timeframe)
            result = analyze_kalshi_series(series_ticker, symbol, timeframe)
            if result:
                symbol_results.append(result)

        if not symbol_results:
            continue

        # Build MTF consensus for this symbol
        consensus = build_mtf_consensus(symbol, symbol_results)
        if consensus:
            consensus["asset_class"] = symbol_asset_class.get(symbol, "crypto")
            all_signals.append(consensus)
            logger.info(
                "Kalshi %s (%s): %s (conf=%.2f, %d/%d TFs)",
                symbol, consensus["asset_class"], consensus["direction"],
                consensus["confidence"], consensus["agreeing_tfs"], consensus["total_tfs"]
            )

    logger.info("Kalshi: generated %d consensus signals from %d symbols", len(all_signals), len(symbol_series))
    return all_signals


# Resilient price fetch — import from shared api_failover module
# with fallback for when this module is run directly and alpha_engine
# is not on sys.path.
try:
    from alpha_engine.api_failover import fetch_price_resilient as _fetch_price_resilient
except Exception:
    try:
        from api_failover import fetch_price_resilient as _fetch_price_resilient
    except Exception:
        _fetch_price_resilient = None  # type: ignore[assignment]


def _fetch_price(symbol: str):
    """Fetch current price using the shared failover chain, with a minimal
    inline Binance fallback when api_failover cannot be imported at all.
    For non-crypto symbols, attempts yfinance as a fallback.
    Returns float price or None on failure.
    """
    asset_class = _detect_asset_class(symbol)

    # For crypto, use the shared failover chain (Binance mirrors + fallbacks)
    if asset_class == "crypto":
        if _fetch_price_resilient is not None:
            try:
                price = _fetch_price_resilient(symbol)
                if price and float(price) > 0:
                    return float(price)
            except Exception:
                logger.warning("fetch_price_resilient(%s) raised, trying inline fallback", symbol)

        # Last resort: minimal inline Binance spot fetch
        for base in ("https://api.binance.com", "https://data-api.binance.vision"):
            try:
                data = _fetch_json(f"{base}/api/v3/ticker/price?symbol={symbol}")
                if isinstance(data, dict) and "price" in data:
                    p = _safe_float(data["price"])
                    if p and p > 0:
                        return p
            except Exception:
                continue
    else:
        # Non-crypto: try yfinance first, then Alpha Vantage-style APIs
        yf_symbol = symbol
        # Map common prediction market symbols to yfinance tickers
        yf_map = {
            "XAUUSD": "GC=F", "XAGUSD": "SI=F", "CLUSD": "CL=F",
            "NGUSD": "NG=F", "TLT": "TLT", "TIP": "TIP",
        }
        if symbol in yf_map:
            yf_symbol = yf_map[symbol]

        try:
            import yfinance as yf
            ticker = yf.Ticker(yf_symbol)
            hist = ticker.history(period="1d")
            if not hist.empty:
                price = float(hist["Close"].iloc[-1])
                if price > 0:
                    return price
        except Exception:
            logger.warning("yfinance price fetch failed for %s", yf_symbol)

    logger.warning("All price sources failed for %s — entry_price/TP/SL will be null", symbol)
    return None


def _derive_trade_levels(entry_price: float, direction: str, confidence: float, asset_class: str = "crypto") -> tuple:
    """Derive TP/SL from entry price, direction, confidence, and asset class."""
    if not entry_price or entry_price <= 0:
        return (None, None)
    conf = max(0.30, min(0.82, float(confidence or 0.60)))

    # Use per-asset-class risk params from config when available
    risk = _get_risk_params(asset_class)
    if risk:
        sl_floor, tp_ceil, _ = risk
        sl_floor = abs(sl_floor)  # ensure positive
        tp_pct = max(0.015, min(tp_ceil, 0.014 + (conf - 0.55) * 0.04))
        sl_pct = max(sl_floor, tp_pct / 1.67)
    else:
        tp_pct = max(0.015, 0.014 + (conf - 0.55) * 0.04)
        sl_pct = max(0.009, tp_pct / 1.67)

    if direction == "SHORT":
        return (round(entry_price * (1 - tp_pct), 8), round(entry_price * (1 + sl_pct), 8))
    return (round(entry_price * (1 + tp_pct), 8), round(entry_price * (1 - sl_pct), 8))


def generate_kalshi_picks(symbols=None, asset_classes=None):
    """
    Generate Kalshi picks in alpha_engine standard format.

    Returns list of pick dicts ready for merging into active_picks.json.
    Supports multi-asset: crypto, index, commodity, equity, macro.
    """
    signals = get_kalshi_signals(symbols, asset_classes=asset_classes)
    now = datetime.now(timezone.utc)
    picks = []
    used_ids: set = set()

    for sig in signals:
        symbol = sig["symbol"]
        direction = sig["direction"]
        confidence = sig["confidence"]
        asset_class = sig.get("asset_class", "crypto")

        base_id = f"kalshi_{symbol}_{direction[:1]}_{now.strftime('%Y%m%d%H%M')}"
        pick_id = base_id
        suffix = 0
        while pick_id in used_ids:
            suffix += 1
            pick_id = f"{base_id}_{suffix}"
        used_ids.add(pick_id)

        signal_type = "BUY" if direction == "LONG" else "SELL"

        # Fetch live price for entry/TP/SL
        entry_price = _fetch_price(symbol)
        take_profit, stop_loss = _derive_trade_levels(entry_price, direction, confidence, asset_class) if entry_price else (None, None)
        if entry_price:
            entry_price = round(entry_price, 8)
        status = "OPEN" if entry_price else "SIGNAL"

        picks.append({
            "id": pick_id,
            "strategy": "kalshi_mtf_consensus",
            "symbol": symbol,
            "category": asset_class,
            "signal_type": signal_type,
            "entry_price": entry_price,
            "entry_date": now.strftime("%Y-%m-%d"),
            "take_profit": take_profit,
            "stop_loss": stop_loss,
            "confidence": confidence,
            "ml_score": None,
            "status": status,
            "source_system": "kalshi",
            "created_at": now.isoformat(),
            "kalshi_data": {
                "timeframes": sig["timeframes_used"],
                "agreeing_tfs": sig["agreeing_tfs"],
                "total_tfs": sig["total_tfs"],
                "all_agree": sig["all_agree"],
                "long_weight": sig["long_weight"],
                "short_weight": sig["short_weight"],
                "reason": sig["reason"],
            },
        })

    logger.info("Generated %d Kalshi picks", len(picks))
    return picks


# ---------------------------------------------------------------------------
# 5. Save to JSON
# ---------------------------------------------------------------------------

def save_signals(picks=None):
    """Save picks to data/kalshi_signals.json."""
    if picks is None:
        picks = generate_kalshi_picks()

    os.makedirs(DATA_DIR, exist_ok=True)

    output = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source": "kalshi",
        "api_base": KALSHI_API_BASE,
        "pick_count": len(picks),
        "picks": picks,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)

    logger.info("Saved %d Kalshi picks to %s", len(picks), OUTPUT_FILE)
    return OUTPUT_FILE


# ---------------------------------------------------------------------------
# 6. CLI entry point
# ---------------------------------------------------------------------------

def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    print("=" * 70)
    print("  Kalshi Prediction Market Signals — Multi-Timeframe Consensus")
    print("  (Crypto + Equities + Commodities + Macro)")
    print("=" * 70)
    print()

    print("[1/3] Fetching Kalshi crypto + macro series...")
    signals = get_kalshi_signals()
    print(f"      Generated {len(signals)} consensus signals")
    print()

    for sig in signals:
        arr = "LONG " if sig["direction"] == "LONG" else "SHORT"
        agree = sig["agreeing_tfs"]
        total = sig["total_tfs"]
        ac = sig.get("asset_class", "crypto")
        print(f"  {arr} {sig['symbol']:<12s} [{ac:<9s}] conf={sig['confidence']:.2f}  "
              f"[{agree}/{total} TFs agree]  {sig['reason'][:50]}")
    print()

    print("[2/3] Generating picks...")
    picks = generate_kalshi_picks()
    print(f"      {len(picks)} picks generated")
    print()

    print("[3/3] Saving to kalshi_signals.json...")
    output_file = save_signals(picks)
    print(f"      Saved to {output_file}")
    print()

    print("=" * 70)
    print(f"  Done. {len(picks)} Kalshi signals saved.")
    print("=" * 70)


if __name__ == "__main__":
    main()
