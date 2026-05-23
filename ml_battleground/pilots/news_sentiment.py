"""
News Sentiment ML Pilot -- Headline scraping + sentiment scoring + trade signals
Part of ml_battleground/pilots/

Modes:
  scan      -- Fetch headlines, score sentiment, generate signals
  history   -- Show sentiment history over past N days

Usage:
  python news_sentiment.py scan
  python news_sentiment.py history
"""

import sys, os, json, re, time, logging
from pathlib import Path
from datetime import datetime, timezone, timedelta
from collections import defaultdict

import requests

# -- Constants --
DATA_DIR = Path(__file__).parent / "data" / "news_sentiment"
HISTORY_PATH = DATA_DIR / "sentiment_history.json"
PICKS_PATH = DATA_DIR / "picks.json"

CRYPTO_TICKERS = {
    "bitcoin": "BTCUSDT", "btc": "BTCUSDT",
    "ethereum": "ETHUSDT", "eth": "ETHUSDT", "ether": "ETHUSDT",
    "solana": "SOLUSDT", "sol": "SOLUSDT",
    "bnb": "BNBUSDT", "binance coin": "BNBUSDT",
    "xrp": "XRPUSDT", "ripple": "XRPUSDT",
    "cardano": "ADAUSDT", "ada": "ADAUSDT",
    "dogecoin": "DOGEUSDT", "doge": "DOGEUSDT",
    "avalanche": "AVAXUSDT", "avax": "AVAXUSDT",
    "bittensor": "TAOUSDT", "tao": "TAOUSDT",
    "render": "RENDERUSDT", "rndr": "RENDERUSDT",
    "chainlink": "LINKUSDT", "link": "LINKUSDT",
}

BULLISH_WORDS = [
    "rally", "surge", "soar", "breakout", "bullish", "moon", "pump",
    "all-time high", "ath", "record", "adoption", "institutional",
    "etf approved", "upgrade", "partnership", "integration", "milestone",
    "accumulation", "whale buying", "inflow", "recovery", "rebound",
    "golden cross", "breaks above", "support holds", "demand",
]

BEARISH_WORDS = [
    "crash", "plunge", "dump", "bearish", "collapse", "hack", "exploit",
    "rugpull", "rug pull", "scam", "fraud", "sec lawsuit", "ban",
    "regulation", "crackdown", "sell-off", "selloff", "liquidation",
    "outflow", "death cross", "breaks below", "resistance", "fear",
    "capitulation", "bankruptcy", "insolvency", "delisting",
]

logger = logging.getLogger("news_sentiment")


# -- RSS Parsing (no feedparser dependency) --
def _parse_rss_items(xml_text: str) -> list:
    """Simple RSS XML parser - extracts title + pubDate from items."""
    items = []
    # Split by <item> tags
    item_blocks = re.findall(r'<item>(.*?)</item>', xml_text, re.DOTALL)
    for block in item_blocks:
        title_match = re.search(
            r'<title><!\[CDATA\[(.*?)\]\]></title>|<title>(.*?)</title>', block
        )
        date_match = re.search(r'<pubDate>(.*?)</pubDate>', block)

        title = ""
        if title_match:
            title = title_match.group(1) or title_match.group(2) or ""
            title = title.strip()

        pub_date = ""
        if date_match:
            pub_date = date_match.group(1).strip()

        if title:
            items.append({"title": title, "published": pub_date})

    return items


# -- Data fetching --
def fetch_coindesk_headlines() -> list:
    """Fetch from CoinDesk RSS."""
    try:
        resp = requests.get(
            "https://www.coindesk.com/arc/outboundfeeds/rss/",
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0 (compatible; SentimentBot/1.0)"},
        )
        if resp.status_code == 200:
            items = _parse_rss_items(resp.text)
            return [{"source": "coindesk", **item} for item in items[:30]]
    except Exception as e:
        logger.warning("CoinDesk RSS failed: %s", e)
    return []


def fetch_cointelegraph_headlines() -> list:
    """Fetch from CoinTelegraph RSS."""
    try:
        resp = requests.get(
            "https://cointelegraph.com/rss",
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0 (compatible; SentimentBot/1.0)"},
        )
        if resp.status_code == 200:
            items = _parse_rss_items(resp.text)
            return [{"source": "cointelegraph", **item} for item in items[:30]]
    except Exception as e:
        logger.warning("CoinTelegraph RSS failed: %s", e)
    return []


def fetch_fear_greed() -> dict:
    """Fetch Fear & Greed Index from Alternative.me with retry."""
    import time as _time
    for attempt in range(3):
        try:
            resp = requests.get("https://api.alternative.me/fng/?limit=7", timeout=10)
            data = resp.json().get("data", [])
            if data:
                current = int(data[0]["value"])
                prev = int(data[1]["value"]) if len(data) > 1 else current
                week_ago = int(data[-1]["value"]) if len(data) >= 7 else current
                return {
                    "current": current,
                    "previous": prev,
                    "week_ago": week_ago,
                    "classification": data[0].get("value_classification", ""),
                    "trend": "improving" if current > prev else "declining",
                }
        except Exception as e:
            if attempt == 2:
                logger.warning("Fear & Greed fetch failed after 3 attempts: %s", e)
            else:
                _time.sleep(2 * (attempt + 1))
    return {
        "current": 50,
        "previous": 50,
        "week_ago": 50,
        "classification": "Neutral",
        "trend": "flat",
    }


# -- Sentiment scoring --
def score_headline(title: str) -> dict:
    """Score a single headline for sentiment."""
    title_lower = title.lower()

    bull_score = 0
    bear_score = 0
    bull_matches = []
    bear_matches = []

    for word in BULLISH_WORDS:
        if word in title_lower:
            bull_score += 1
            bull_matches.append(word)

    for word in BEARISH_WORDS:
        if word in title_lower:
            bear_score += 1
            bear_matches.append(word)

    # Net sentiment: -1 to +1
    total = bull_score + bear_score
    if total == 0:
        net = 0.0
    else:
        net = (bull_score - bear_score) / total

    # Detect mentioned coins
    coins = []
    for keyword, ticker in CRYPTO_TICKERS.items():
        if keyword in title_lower and ticker not in coins:
            coins.append(ticker)

    return {
        "title": title,
        "sentiment": round(net, 3),
        "bull_score": bull_score,
        "bear_score": bear_score,
        "bull_matches": bull_matches,
        "bear_matches": bear_matches,
        "coins": coins,
    }


def aggregate_sentiment(scored_headlines: list) -> dict:
    """Aggregate sentiment per coin and overall."""
    coin_sentiments = defaultdict(list)
    all_sentiments = []

    for item in scored_headlines:
        s = item["sentiment"]
        all_sentiments.append(s)
        for coin in item["coins"]:
            coin_sentiments[coin].append(s)

    # Overall
    overall = {
        "mean": round(sum(all_sentiments) / len(all_sentiments), 3)
        if all_sentiments
        else 0,
        "positive_pct": round(
            sum(1 for s in all_sentiments if s > 0) / max(len(all_sentiments), 1), 3
        ),
        "negative_pct": round(
            sum(1 for s in all_sentiments if s < 0) / max(len(all_sentiments), 1), 3
        ),
        "neutral_pct": round(
            sum(1 for s in all_sentiments if s == 0) / max(len(all_sentiments), 1), 3
        ),
        "count": len(all_sentiments),
    }

    # Per coin
    per_coin = {}
    for coin, sentiments in coin_sentiments.items():
        per_coin[coin] = {
            "mean": round(sum(sentiments) / len(sentiments), 3),
            "count": len(sentiments),
            "positive": sum(1 for s in sentiments if s > 0),
            "negative": sum(1 for s in sentiments if s < 0),
        }

    return {"overall": overall, "per_coin": per_coin}


# -- Signal generation --
def generate_signals(sentiment: dict, fear_greed: dict) -> list:
    """Generate trade signals from sentiment + fear/greed."""
    signals = []
    fg = fear_greed["current"]
    fg_trend = fear_greed["trend"]

    for coin, stats in sentiment["per_coin"].items():
        if stats["count"] < 2:
            continue  # Need at least 2 mentions

        mean_sent = stats["mean"]
        signal = None
        reasons = []
        confidence = 0.50

        # Contrarian: extreme fear + positive headlines = BUY
        if fg < 20 and mean_sent > 0.2:
            signal = "long"
            reasons.append(
                f"Contrarian: F&G={fg} (extreme fear) but headlines positive ({mean_sent:.2f})"
            )
            confidence = 0.60 + min(0.15, (0.2 - fg / 100) * 0.5)

        # Contrarian: extreme fear + improving trend = BUY
        elif fg < 25 and fg_trend == "improving" and mean_sent >= 0:
            signal = "long"
            reasons.append(
                f"Fear recovery: F&G={fg} improving, headlines neutral-positive ({mean_sent:.2f})"
            )
            confidence = 0.55 + min(0.10, mean_sent * 0.2)

        # Momentum: strong positive sentiment + recovering fear = BUY
        elif mean_sent > 0.5 and fg > 25 and fg < 60:
            signal = "long"
            reasons.append(
                f"Positive momentum: strong headlines ({mean_sent:.2f}), F&G={fg} recovering"
            )
            confidence = 0.55 + min(0.10, mean_sent * 0.15)

        # Warning: euphoria = potential short or avoid
        elif fg > 80 and mean_sent > 0.5:
            signal = "warning"
            reasons.append(
                f"Euphoria warning: F&G={fg}, headlines very positive ({mean_sent:.2f}) - potential top"
            )
            confidence = 0.50

        if signal and signal != "warning":
            signals.append(
                {
                    "pair": coin,
                    "direction": signal,
                    "confidence": round(min(confidence, 0.85), 3),
                    "strategy": "news_sentiment",
                    "signal_time": datetime.now(timezone.utc).isoformat(),
                    "reasons": reasons,
                    "sentiment_stats": stats,
                    "fear_greed": fg,
                    "fear_greed_trend": fg_trend,
                    "headline_count": stats["count"],
                }
            )

    # Sort by confidence
    signals.sort(key=lambda x: x["confidence"], reverse=True)
    return signals


# -- Scanner --
def scan():
    """Full scan: fetch headlines, score, generate signals."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("Fetching headlines...")
    headlines = []
    headlines.extend(fetch_coindesk_headlines())
    time.sleep(1)
    headlines.extend(fetch_cointelegraph_headlines())

    logger.info("Fetched %d headlines total", len(headlines))

    if not headlines:
        logger.warning("No headlines fetched - check internet connection")
        return []

    # Score all headlines
    scored = [score_headline(h["title"]) for h in headlines]
    scored = [
        {**s, "source": h.get("source", "unknown"), "published": h.get("published", "")}
        for s, h in zip(scored, headlines)
    ]

    # Aggregate
    sentiment = aggregate_sentiment(scored)

    # Fear & Greed
    fear_greed = fetch_fear_greed()

    # Generate signals
    signals = generate_signals(sentiment, fear_greed)

    # Log summary
    logger.info(
        "Overall sentiment: mean=%.3f | bullish=%.0f%% | bearish=%.0f%%",
        sentiment["overall"]["mean"],
        sentiment["overall"]["positive_pct"] * 100,
        sentiment["overall"]["negative_pct"] * 100,
    )
    logger.info(
        "Fear & Greed: %d (%s) trend=%s",
        fear_greed["current"],
        fear_greed["classification"],
        fear_greed["trend"],
    )

    for sig in signals:
        logger.info(
            "SIGNAL: %s %s (conf=%.3f) - %s",
            sig["pair"],
            sig["direction"],
            sig["confidence"],
            sig["reasons"][0],
        )

    # Save results
    output = {
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "strategy": "news_sentiment",
        "headlines_analyzed": len(scored),
        "fear_greed": fear_greed,
        "sentiment_summary": sentiment,
        "signals": signals,
        "top_headlines": [
            {
                "title": s["title"],
                "sentiment": s["sentiment"],
                "coins": s["coins"],
                "source": s["source"],
            }
            for s in sorted(scored, key=lambda x: abs(x["sentiment"]), reverse=True)[
                :15
            ]
        ],
    }
    PICKS_PATH.write_text(json.dumps(output, indent=2))

    # Append to history
    _append_history(sentiment, fear_greed, signals)

    logger.info("Scan complete: %d signals", len(signals))
    return signals


def _append_history(sentiment, fear_greed, signals):
    """Append current scan to history file."""
    history = []
    if HISTORY_PATH.exists():
        try:
            history = json.loads(HISTORY_PATH.read_text())
        except Exception:
            history = []

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "fear_greed": fear_greed["current"],
        "overall_sentiment": sentiment["overall"]["mean"],
        "headline_count": sentiment["overall"]["count"],
        "signal_count": len(signals),
        "signals": [
            {"pair": s["pair"], "direction": s["direction"], "confidence": s["confidence"]}
            for s in signals
        ],
    }
    history.append(entry)

    # Keep last 500 entries
    history = history[-500:]
    HISTORY_PATH.write_text(json.dumps(history, indent=2))


def show_history():
    """Display sentiment history."""
    if not HISTORY_PATH.exists():
        print("No history yet. Run 'scan' first.")
        return

    history = json.loads(HISTORY_PATH.read_text())
    print(
        f"\n{'Timestamp':<25} {'F&G':>4} {'Sentiment':>10} {'Headlines':>10} {'Signals':>8}"
    )
    print("-" * 65)
    for entry in history[-20:]:
        ts = entry["timestamp"][:19]
        print(
            f"{ts:<25} {entry['fear_greed']:>4} {entry['overall_sentiment']:>10.3f} "
            f"{entry['headline_count']:>10} {entry['signal_count']:>8}"
        )


# -- Main --
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    mode = sys.argv[1] if len(sys.argv) > 1 else "scan"

    if mode == "scan":
        signals = scan()
        if signals:
            print(json.dumps(signals, indent=2))
        else:
            print("No signals generated")
    elif mode == "history":
        show_history()
    else:
        print(f"Usage: {sys.argv[0]} [scan|history]")
