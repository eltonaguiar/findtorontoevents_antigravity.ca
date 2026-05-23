"""
Polymarket Signal Generator — Multi-Asset

Converts Polymarket prediction markets into directional signals across
crypto, equities, commodities, forex, and macro events.

Conservative filter chain:
- Only explicit asset references (regex-matched) are allowed.
- Only clear directional market types are allowed.
- No sports, politics, weather, or ambiguous event contamination.
"""

from __future__ import annotations

import json
import logging
import math
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "polymarket_signals.json")

GAMMA_API_BASE = "https://gamma-api.polymarket.com"
DATA_API_BASE = "https://data-api.polymarket.com"
CLOB_API_BASE = "https://clob.polymarket.com"

REQUEST_TIMEOUT = 20
ACTIVE_MARKET_LIMIT = 500
MOMENTUM_MARKET_LIMIT = 20
MIN_MARKET_VOLUME_USD = 1_000.0

YES_NO_BULLISH_THRESHOLD = 0.70
YES_NO_BEARISH_THRESHOLD = 0.30
UPDOWN_BULLISH_THRESHOLD = 0.60
UPDOWN_BEARISH_THRESHOLD = 0.40
MOMENTUM_THRESHOLD_4H = 0.05

REJECT_KEYWORDS: tuple[str, ...] = (
    "nba", "nfl", "mlb", "nhl", "fifa", "world cup", "super bowl",
    "election", "president", "congress",
    "gta", "rihanna", "album", "movie", "oscar", "grammy", "emmy",
    "tennis", "f1", "formula", "ufc", "boxing", "olympics", "medal",
    "hurricane", "earthquake", "war", "invasion",
)

PRICE_TARGET_RE = re.compile(
    r"(\$\s*[\d,]+[kK]?|\babove\s+\$|\bbelow\s+\$|\breach\s+\$|\bdip\s+to\b|\bfall\s+to\b)", re.I,
)

ASSET_RULES: tuple[tuple[str, tuple[re.Pattern[str], ...]], ...] = (
    # --- Crypto ---
    ("BTCUSDT", (re.compile(r"\bbitcoin\b", re.I), re.compile(r"\bbtc\b", re.I))),
    ("ETHUSDT", (re.compile(r"\bethereum\b", re.I), re.compile(r"\beth\b", re.I))),
    ("SOLUSDT", (re.compile(r"\bsolana\b", re.I), re.compile(r"\bsol\b", re.I))),
    ("XRPUSDT", (re.compile(r"\bxrp\b", re.I), re.compile(r"\bripple\b", re.I))),
    ("DOGEUSDT", (re.compile(r"\bdogecoin\b", re.I), re.compile(r"\bdoge\b", re.I))),
    ("ADAUSDT", (re.compile(r"\bcardano\b", re.I), re.compile(r"\bada\b", re.I))),
    ("BNBUSDT", (re.compile(r"\bbinance coin\b", re.I), re.compile(r"\bbnb\b", re.I))),
    ("AVAXUSDT", (re.compile(r"\bavax\b", re.I),)),
    ("LINKUSDT", (re.compile(r"\bchainlink\b", re.I), re.compile(r"\blink\b", re.I))),
    ("DOTUSDT", (re.compile(r"\bpolkadot\b", re.I), re.compile(r"\bdot\b", re.I))),
    ("LTCUSDT", (re.compile(r"\blitecoin\b", re.I), re.compile(r"\bltc\b", re.I))),
    ("SUIUSDT", (re.compile(r"\bsui\b", re.I),)),
    # --- Equities / Indices ---
    ("SPY",  (re.compile(r"\bs&p\s*500\b", re.I), re.compile(r"\bspy\b", re.I), re.compile(r"\bspx\b", re.I))),
    ("QQQ",  (re.compile(r"\bnasdaq\b", re.I), re.compile(r"\bqqq\b", re.I))),
    ("AAPL", (re.compile(r"\bapple\b", re.I), re.compile(r"\baapl\b", re.I))),
    ("TSLA", (re.compile(r"\btesla\b", re.I), re.compile(r"\btsla\b", re.I))),
    ("NVDA", (re.compile(r"\bnvidia\b", re.I), re.compile(r"\bnvda\b", re.I))),
    ("AMZN", (re.compile(r"\bamazon\b", re.I), re.compile(r"\bamzn\b", re.I))),
    ("META", (re.compile(r"\bmeta\b", re.I), re.compile(r"\bfacebook\b", re.I))),
    ("GOOGL",(re.compile(r"\bgoogle\b", re.I), re.compile(r"\bgoogl\b", re.I), re.compile(r"\balphabet\b", re.I))),
    ("MSFT", (re.compile(r"\bmicrosoft\b", re.I), re.compile(r"\bmsft\b", re.I))),
    # --- Commodities ---
    ("XAUUSD", (re.compile(r"\bgold\b", re.I), re.compile(r"\bxau\b", re.I))),
    ("XAGUSD", (re.compile(r"\bsilver\b", re.I), re.compile(r"\bxag\b", re.I))),
    ("CLUSD",  (re.compile(r"\bcrude\s*oil\b", re.I), re.compile(r"\bwti\b", re.I), re.compile(r"\boil\s*price\b", re.I))),
    # --- Macro / Interest Rates ---
    ("TLT",  (re.compile(r"\bfed\s*(funds|rate)\b", re.I), re.compile(r"\binterest\s*rate\b", re.I), re.compile(r"\brate\s*cut\b", re.I), re.compile(r"\brate\s*hike\b", re.I))),
    ("TIP",  (re.compile(r"\binflation\b", re.I), re.compile(r"\bcpi\b", re.I))),
    # --- Forex ---
    ("EURUSD", (re.compile(r"\beur/?usd\b", re.I), re.compile(r"\beuro\s*(vs|against)\s*(the\s*)?dollar\b", re.I))),
    ("GBPUSD", (re.compile(r"\bgbp/?usd\b", re.I), re.compile(r"\bpound\b", re.I))),
    ("USDJPY", (re.compile(r"\busd/?jpy\b", re.I), re.compile(r"\byen\b", re.I))),
)


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


def _fetch_price(symbol: str) -> float | None:
    """Fetch current price. Uses Binance failover for crypto, yfinance for
    equities/commodities/forex.
    """
    asset_class = _detect_asset_class(symbol)

    if asset_class == "crypto":
        if _fetch_price_resilient is not None:
            try:
                price = _fetch_price_resilient(symbol)
                if price and float(price) > 0:
                    return float(price)
            except Exception:
                logger.warning("fetch_price_resilient(%s) raised, trying inline fallback", symbol)

        for base in ("https://api.binance.com", "https://data-api.binance.vision"):
            try:
                data = _fetch_json(f"{base}/api/v3/ticker/price?symbol={symbol}")
                if isinstance(data, dict) and "price" in data:
                    p = float(data["price"])
                    if p > 0:
                        return p
            except Exception:
                continue
    else:
        # Non-crypto: yfinance
        yf_map = {
            "XAUUSD": "GC=F", "XAGUSD": "SI=F", "CLUSD": "CL=F",
            "NGUSD": "NG=F", "TLT": "TLT", "TIP": "TIP",
        }
        yf_symbol = yf_map.get(symbol, symbol)
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


def _snapshot_trade_levels(symbol: str, direction: str) -> tuple[float | None, float | None, float | None]:
    entry_price = _fetch_price(symbol)
    if not entry_price:
        return (None, None, None)

    entry_price = round(float(entry_price), 8)
    asset_class = _detect_asset_class(symbol)
    risk = _get_risk_params(asset_class)

    if risk:
        sl_floor, tp_ceil, _ = risk
        sl_pct = abs(sl_floor)
        tp_pct = min(tp_ceil, sl_pct * 1.67)
    else:
        tp_pct = 0.025
        sl_pct = 0.015

    if direction == "SHORT":
        take_profit = round(entry_price * (1 - tp_pct), 8)
        stop_loss = round(entry_price * (1 + sl_pct), 8)
    else:
        take_profit = round(entry_price * (1 + tp_pct), 8)
        stop_loss = round(entry_price * (1 - sl_pct), 8)
    return (entry_price, take_profit, stop_loss)

UPDOWN_RE = re.compile(r"\bup or down\b", re.I)
ABOVE_RE = re.compile(r"\b(above|over|reach|hit|at least|exceed|surpass)\b", re.I)
BELOW_RE = re.compile(r"\b(below|under|dip|drop|fall|crash)\b", re.I)
RANGE_RE = re.compile(r"\bbetween\b", re.I)
PRICE_RE = re.compile(r"\$\s*[\d,]+")


def _fetch_json(url: str, params: dict[str, Any] | None = None) -> Any:
    """Fetch JSON using stdlib only."""
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "AlphaEngine-PolymarketSignals/2.0",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        logger.warning("HTTP %s fetching %s: %s", exc.code, url, exc.reason)
    except urllib.error.URLError as exc:
        logger.warning("URL error fetching %s: %s", url, exc.reason)
    except Exception as exc:
        logger.warning("Unexpected error fetching %s: %s", url, exc)
    return None


def _safe_float(value: Any, default: float | None = None) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_json_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else []
        except (json.JSONDecodeError, TypeError, ValueError):
            return []
    return []


def _parse_end_date(raw_date: Any) -> datetime | None:
    if not raw_date:
        return None
    text = str(raw_date).strip().replace("Z", "+00:00")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        # Date-only Polymarket fields should remain active through the trading day.
        text = f"{text}T23:59:59+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _is_expired(market: dict[str, Any]) -> bool:
    end_dt = _parse_end_date(market.get("endDate"))
    if end_dt is None:
        return False
    return end_dt <= datetime.now(timezone.utc)


def _market_text(market: dict[str, Any]) -> str:
    return " ".join(
        str(market.get(key, "") or "")
        for key in ("question", "title", "description", "slug", "eventSlug", "groupItemTitle")
    )


def _extract_symbol(market: dict[str, Any]) -> str | None:
    text = _market_text(market)
    for symbol, patterns in ASSET_RULES:
        if any(pattern.search(text) for pattern in patterns):
            return symbol
    return None


def _classify_market(question: str) -> str | None:
    """Return one of updown / price_above / price_below."""
    if not question:
        return None
    if RANGE_RE.search(question):
        return None
    if UPDOWN_RE.search(question):
        return "updown"
    if not PRICE_RE.search(question):
        return None
    if ABOVE_RE.search(question):
        return "price_above"
    if BELOW_RE.search(question):
        return "price_below"
    return None


def _extract_probability(market: dict[str, Any], market_type: str) -> float | None:
    """Extract the directional probability relevant to the market type."""
    outcomes = [str(x) for x in _parse_json_list(market.get("outcomes"))]
    prices_raw = _parse_json_list(market.get("outcomePrices"))
    prices = [_safe_float(x) for x in prices_raw]
    if outcomes and prices and len(outcomes) == len(prices):
        pairs = {
            outcome.strip().lower(): price
            for outcome, price in zip(outcomes, prices)
            if price is not None
        }
        if market_type == "updown":
            return pairs.get("up")
        return pairs.get("yes")

    for key in ("probability", "bestAsk", "lastTradePrice", "price"):
        value = _safe_float(market.get(key))
        if value is not None:
            return value
    return None


def _extract_volume(market: dict[str, Any]) -> float:
    for key in ("volumeNum", "volume", "volume24hr", "liquidityNum"):
        value = _safe_float(market.get(key))
        if value is not None:
            return value
    return 0.0


def _normalize_market(market: dict[str, Any]) -> dict[str, Any] | None:
    if bool(market.get("closed")) or not bool(market.get("active", True)):
        return None
    if _is_expired(market):
        return None

    # Reject non-crypto markets (sports, politics, entertainment, etc.)
    text_lower = _market_text(market).lower()
    if any(keyword in text_lower for keyword in REJECT_KEYWORDS):
        return None

    symbol = _extract_symbol(market)
    if not symbol:
        return None

    question = str(market.get("question") or market.get("title") or "").strip()

    # Require a specific price target or percentage to qualify as a crypto-price signal
    if not PRICE_TARGET_RE.search(question) and not PRICE_TARGET_RE.search(text_lower):
        return None

    market_type = _classify_market(question)
    if not market_type:
        return None

    probability = _extract_probability(market, market_type)
    if probability is None or probability < 0 or probability > 1:
        return None

    volume = _extract_volume(market)
    if volume < MIN_MARKET_VOLUME_USD:
        return None

    clob_ids = _parse_json_list(market.get("clobTokenIds"))

    return {
        "id": str(market.get("id") or market.get("conditionId") or market.get("slug") or ""),
        "question": question,
        "symbol": symbol,
        "market_type": market_type,
        "probability": probability,
        "volume": volume,
        "slug": str(market.get("slug") or ""),
        "event_slug": str(market.get("eventSlug") or ""),
        "end_date": str(market.get("endDate") or ""),
        "clob_token_ids": clob_ids,
    }


def fetch_crypto_markets(limit: int = ACTIVE_MARKET_LIMIT) -> list[dict[str, Any]]:
    """
    Fetch active Polymarket markets, then locally filter to strict crypto-only
    directional contracts.
    """
    result = _fetch_json(
        f"{GAMMA_API_BASE}/markets",
        {
            "active": "true",
            "closed": "false",
            "order": "volume",
            "ascending": "false",
            "limit": str(limit),
        },
    )
    if not isinstance(result, list):
        return []

    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for market in result:
        if not isinstance(market, dict):
            continue
        normalized_market = _normalize_market(market)
        if not normalized_market:
            continue
        market_id = normalized_market["id"]
        if not market_id or market_id in seen:
            continue
        seen.add(market_id)
        normalized.append(normalized_market)

    normalized.sort(key=lambda item: item["volume"], reverse=True)
    logger.info("Polymarket strict filter kept %d/%d markets", len(normalized), len(result))
    return normalized


def _probability_signal_direction(market: dict[str, Any]) -> tuple[str | None, str | None]:
    prob = float(market["probability"])
    market_type = market["market_type"]

    if market_type == "updown":
        if prob >= UPDOWN_BULLISH_THRESHOLD:
            return "LONG", "BULLISH"
        if prob <= UPDOWN_BEARISH_THRESHOLD:
            return "SHORT", "BEARISH"
        return None, None

    if market_type == "price_above":
        if prob >= YES_NO_BULLISH_THRESHOLD:
            return "LONG", "BULLISH"
        if prob <= YES_NO_BEARISH_THRESHOLD:
            return "SHORT", "BEARISH"
        return None, None

    if market_type == "price_below":
        if prob >= YES_NO_BULLISH_THRESHOLD:
            return "SHORT", "BEARISH"
        if prob <= YES_NO_BEARISH_THRESHOLD:
            return "LONG", "BULLISH"
        return None, None

    return None, None


def get_probability_signals(markets: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Convert strict crypto directional markets into probability signals."""
    if markets is None:
        markets = fetch_crypto_markets()

    signals: list[dict[str, Any]] = []
    for market in markets:
        direction, signal_type = _probability_signal_direction(market)
        if not direction:
            continue

        prob = float(market["probability"])
        prob_edge = abs(prob - 0.50) * 2.0
        volume_bonus = min(math.log10(market["volume"] + 1.0) / 6.0, 1.0) * 0.12
        confidence = round(min(0.85, 0.55 + prob_edge * 0.22 + volume_bonus), 3)

        signals.append(
            {
                "market_id": market["id"],
                "question": market["question"],
                "symbol": market["symbol"],
                "direction": direction,
                "signal_type": signal_type,
                "probability": prob,
                "confidence": confidence,
                "volume": market["volume"],
                "end_date": market["end_date"],
                "market_type": market["market_type"],
                "reason": (
                    f"Polymarket {market['market_type']}: "
                    f"\"{market['question']}\" at {prob:.0%} "
                    f"(vol=${market['volume']:,.0f})"
                ),
            }
        )

    logger.info("Generated %d Polymarket probability signals", len(signals))
    return signals


def fetch_clob_price_history(token_id: str, fidelity: int = 60) -> list[dict[str, Any]]:
    if not token_id:
        return []
    result = _fetch_json(
        f"{CLOB_API_BASE}/prices-history",
        {"market": str(token_id), "interval": "all", "fidelity": str(fidelity)},
    )
    if isinstance(result, dict):
        history = result.get("history")
        return history if isinstance(history, list) else []
    return result if isinstance(result, list) else []


def calculate_clob_momentum(history: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not history or len(history) < 2:
        return None

    sorted_history = sorted(history, key=lambda row: row.get("t", 0))
    now_ts = float(sorted_history[-1].get("t", 0) or 0)
    current_prob = _safe_float(sorted_history[-1].get("p"), 0.5)
    if current_prob is None:
        return None

    def _prob_at(hours_ago: int) -> float:
        cutoff = now_ts - (hours_ago * 3600)
        selected = sorted_history[0]
        for row in sorted_history:
            if float(row.get("t", 0) or 0) <= cutoff:
                selected = row
            else:
                break
        return _safe_float(selected.get("p"), current_prob) or current_prob

    prob_4h = _prob_at(4)
    prob_24h = _prob_at(24)
    momentum_4h = round(current_prob - prob_4h, 4)
    momentum_24h = round(current_prob - prob_24h, 4)
    velocity = round(momentum_4h / 4.0, 5)

    if momentum_4h >= MOMENTUM_THRESHOLD_4H:
        signal = "BULLISH"
    elif momentum_4h <= -MOMENTUM_THRESHOLD_4H:
        signal = "BEARISH"
    else:
        signal = "NEUTRAL"

    return {
        "current_prob": round(current_prob, 4),
        "momentum_4h": momentum_4h,
        "momentum_24h": momentum_24h,
        "velocity": velocity,
        "momentum_signal": signal,
        "data_points": len(sorted_history),
    }


def _momentum_trade_direction(market: dict[str, Any], momentum_signal: str) -> str | None:
    market_type = market["market_type"]
    if momentum_signal not in ("BULLISH", "BEARISH"):
        return None

    if market_type in ("updown", "price_above"):
        return "LONG" if momentum_signal == "BULLISH" else "SHORT"
    if market_type == "price_below":
        return "SHORT" if momentum_signal == "BULLISH" else "LONG"
    return None


def get_clob_momentum_signals(
    markets: list[dict[str, Any]],
    max_markets: int = MOMENTUM_MARKET_LIMIT,
) -> list[dict[str, Any]]:
    """Generate momentum signals from strict crypto markets with CLOB history."""
    candidates = [m for m in markets if m["clob_token_ids"] and m["volume"] >= MIN_MARKET_VOLUME_USD]
    candidates.sort(key=lambda item: item["volume"], reverse=True)
    candidates = candidates[:max_markets]

    signals: list[dict[str, Any]] = []
    for market in candidates:
        history = fetch_clob_price_history(str(market["clob_token_ids"][0]))
        momentum = calculate_clob_momentum(history)
        if not momentum:
            continue
        direction = _momentum_trade_direction(market, momentum["momentum_signal"])
        if not direction:
            continue

        vol_factor = min(math.log10(market["volume"] + 1.0) / 6.0, 1.0) * 0.10
        move_factor = min(abs(momentum["momentum_4h"]) / 0.20, 1.0) * 0.20
        confidence = round(min(0.82, 0.55 + move_factor + vol_factor), 3)

        signals.append(
            {
                "market_id": market["id"],
                "question": market["question"],
                "symbol": market["symbol"],
                "direction": direction,
                "signal_type": "MOMENTUM",
                "probability": momentum["current_prob"],
                "confidence": confidence,
                "volume": market["volume"],
                "end_date": market["end_date"],
                "market_type": market["market_type"],
                "momentum_4h": momentum["momentum_4h"],
                "momentum_24h": momentum["momentum_24h"],
                "velocity": momentum["velocity"],
                "reason": (
                    f"CLOB momentum {market['market_type']}: "
                    f"\"{market['question']}\" | "
                    f"4h={momentum['momentum_4h']:+.1%} "
                    f"24h={momentum['momentum_24h']:+.1%}"
                ),
            }
        )

    logger.info("Generated %d Polymarket momentum signals", len(signals))
    return signals


def get_top_predictors(limit: int = 20) -> list[dict[str, Any]]:
    """Return leaderboard rows from the official Polymarket data API."""
    result = _fetch_json(f"{DATA_API_BASE}/v1/leaderboard", {"limit": str(limit)})
    return result if isinstance(result, list) else []


def generate_polymarket_picks(markets: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """
    Generate Alpha Engine picks from strict Polymarket probability and momentum
    signals. One best signal per symbol+direction survives.
    """
    if markets is None:
        markets = fetch_crypto_markets()

    probability_signals = get_probability_signals(markets)
    momentum_signals = get_clob_momentum_signals(markets)

    by_symbol_direction: dict[str, dict[str, dict[str, Any]]] = {}
    for signal in probability_signals + momentum_signals:
        symbol = signal["symbol"]
        direction = signal["direction"]
        sym_bucket = by_symbol_direction.setdefault(symbol, {})
        dir_bucket = sym_bucket.setdefault(
            direction,
            {
                "signals": [],
                "best_signal": signal,
                "score": 0.0,
            },
        )
        dir_bucket["signals"].append(signal)
        dir_bucket["score"] += float(signal["confidence"])
        if float(signal["confidence"]) > float(dir_bucket["best_signal"]["confidence"]):
            dir_bucket["best_signal"] = signal

    now = datetime.now(timezone.utc)
    picks: list[dict[str, Any]] = []
    used_ids: set[str] = set()

    for symbol, direction_buckets in by_symbol_direction.items():
        if len(direction_buckets) == 1:
            chosen_direction = next(iter(direction_buckets))
            chosen_bucket = direction_buckets[chosen_direction]
            opposing_score = 0.0
        else:
            long_bucket = direction_buckets.get("LONG")
            short_bucket = direction_buckets.get("SHORT")
            long_score = float(long_bucket["score"]) if long_bucket else 0.0
            short_score = float(short_bucket["score"]) if short_bucket else 0.0
            if abs(long_score - short_score) < 0.05:
                logger.info("Skipping %s: reverse-engineered signal conflict too close", symbol)
                continue
            chosen_direction = "LONG" if long_score > short_score else "SHORT"
            chosen_bucket = direction_buckets[chosen_direction]
            opposing_score = short_score if chosen_direction == "LONG" else long_score

        signal = dict(chosen_bucket["best_signal"])
        support_count = len(chosen_bucket["signals"])
        signal["confidence"] = round(
            min(
                0.90,
                float(signal["confidence"])
                + min((support_count - 1) * 0.03, 0.09)
                + min(max(float(chosen_bucket["score"]) - opposing_score, 0.0) * 0.08, 0.05),
            ),
            3,
        )
        signal["support_count"] = support_count
        signal["aggregated_score"] = round(float(chosen_bucket["score"]), 4)
        signal["opposing_score"] = round(opposing_score, 4)

        symbol = signal["symbol"]
        direction = signal["direction"]
        strategy = "polymarket_momentum" if signal["signal_type"] == "MOMENTUM" else "polymarket_prediction"
        base_id = f"polymarket_{symbol}_{direction[:1]}_{now.strftime('%Y%m%d%H%M')}"
        pick_id = base_id
        suffix = 0
        while pick_id in used_ids:
            suffix += 1
            pick_id = f"{base_id}_{suffix}"
        used_ids.add(pick_id)

        data_block = {
            "market_id": signal["market_id"],
            "question": signal["question"],
            "probability": signal["probability"],
            "signal_type": signal["signal_type"],
            "volume": signal["volume"],
            "resolution_date": signal.get("end_date", ""),
            "market_type": signal.get("market_type", ""),
            "support_count": signal.get("support_count", 1),
            "aggregated_score": signal.get("aggregated_score"),
            "opposing_score": signal.get("opposing_score"),
            "reason": signal["reason"],
        }
        if signal["signal_type"] == "MOMENTUM":
            data_block["momentum_4h"] = signal.get("momentum_4h")
            data_block["momentum_24h"] = signal.get("momentum_24h")
            data_block["velocity"] = signal.get("velocity")

        entry_price, take_profit, stop_loss = _snapshot_trade_levels(symbol, direction)
        asset_class = _detect_asset_class(symbol)

        picks.append(
            {
                "id": pick_id,
                "strategy": strategy,
                "symbol": symbol,
                "category": asset_class,
                "signal_type": "BUY" if direction == "LONG" else "SELL",
                "direction": direction,
                "entry_price": entry_price,
                "entry_date": now.strftime("%Y-%m-%d"),
                "take_profit": take_profit,
                "stop_loss": stop_loss,
                "confidence": signal["confidence"],
                "ml_score": None,
                "status": "OPEN" if entry_price else "SIGNAL",
                "source_system": "polymarket",
                "type_label": "🔮 PM",
                "created_at": now.isoformat(),
                "polymarket_data": data_block,
            }
        )

    picks.sort(key=lambda item: float(item.get("confidence", 0) or 0), reverse=True)
    logger.info(
        "Generated %d Polymarket picks (%d probability + %d momentum)",
        len(picks),
        len(probability_signals),
        len(momentum_signals),
    )
    return picks


def save_signals(picks: list[dict[str, Any]] | None = None) -> str:
    if picks is None:
        picks = generate_polymarket_picks()

    os.makedirs(DATA_DIR, exist_ok=True)
    output = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source": "polymarket",
        "api_base": GAMMA_API_BASE,
        "pick_count": len(picks),
        "picks": picks,
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as fh:
        json.dump(output, fh, indent=2, default=str)
    logger.info("Saved %d picks to %s", len(picks), OUTPUT_FILE)
    return OUTPUT_FILE


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    print("=" * 70)
    print("  Polymarket Crypto Signal Generator")
    print("=" * 70)

    print("\n[1/4] Fetching strict crypto markets...")
    markets = fetch_crypto_markets()
    print(f"      {len(markets)} markets passed strict filtering")

    if markets:
        print("\n  Top markets:")
        for market in markets[:10]:
            print(
                f"    {market['symbol']:<10s} "
                f"{market['market_type']:<11s} "
                f"p={market['probability']:.0%} "
                f"vol=${market['volume']:>10,.0f}  "
                f"{market['question'][:70]}"
            )

    print("\n[2/4] Building probability signals...")
    probability_signals = get_probability_signals(markets)
    print(f"      {len(probability_signals)} probability signals")

    print("\n[3/4] Building momentum signals...")
    momentum_signals = get_clob_momentum_signals(markets)
    print(f"      {len(momentum_signals)} momentum signals")

    print("\n[4/4] Saving picks...")
    picks = generate_polymarket_picks(markets)
    output_path = save_signals(picks)
    print(f"      Saved {len(picks)} picks to {output_path}")

    print("\nDone.")


if __name__ == "__main__":
    main()
