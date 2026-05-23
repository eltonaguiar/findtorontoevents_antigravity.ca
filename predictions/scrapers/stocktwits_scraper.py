"""StockTwits scraper - extracts crypto predictions and sentiment.

Uses cloudscraper to bypass Cloudflare protection.
"""
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import cloudscraper
    HAS_CLOUDSCRAPER = True
except ImportError:
    HAS_CLOUDSCRAPER = False

from db import get_db, insert_prediction

# Import shared symbol extractor for multi-asset text analysis
try:
    from symbol_extractor import extract_symbols as _extract_symbols_multi
    HAS_SYMBOL_EXTRACTOR = True
except ImportError:
    HAS_SYMBOL_EXTRACTOR = False

# StockTwits API
STOCKTWITS_API = "https://api.stocktwits.com/api/2"

# StockTwits uses .X suffix for many crypto symbols
STOCKTWITS_SYMBOLS = {
    # Crypto symbols
    "BTC": "BTC.X",
    "ETH": "ETH.X",
    "SOL": "SOL",
    "BNB": "BNB.X",
    "DOGE": "DOGE.X",
    "LINK": "LINK",
    "AVAX": "AVAX.X",
    "XRP": "XRP",
    "ADA": "ADA.X",
    "DOT": "DOT.X",
    "SUI": "SUI",
    "MATIC": "MATIC.X",
    "ARB": "ARB",
    "OP": "OP.X",
    "SHIB": "SHIB.X",
    "PEPE": "PEPE.X",
    "UNI": "UNI",
    "AAVE": "AAVE",
    "COMP": "COMP",
    "MKR": "MKR",
    # Equity/ETF symbols (StockTwits uses plain tickers for stocks)
    "SPY": "SPY",
    "QQQ": "QQQ",
    "AAPL": "AAPL",
    "NVDA": "NVDA",
    "TSLA": "TSLA",
    "MSFT": "MSFT",
    "AMZN": "AMZN",
    "META": "META",
    "GOOG": "GOOG",
    "AMD": "AMD",
    "COIN": "COIN",
    "MSTR": "MSTR",
    "PLTR": "PLTR",
    "NFLX": "NFLX",
    "ARKK": "ARKK",
    "GLD": "GLD",
    "SLV": "SLV",
}

# Map to our internal symbol format
SYMBOL_MAP = {
    # Crypto → USDT pairs
    "BTC": "BTCUSDT", "ETH": "ETHUSDT", "SOL": "SOLUSDT",
    "BNB": "BNBUSDT", "DOGE": "DOGEUSDT", "LINK": "LINKUSDT",
    "AVAX": "AVAXUSDT", "XRP": "XRPUSDT", "ADA": "ADAUSDT",
    "DOT": "DOTUSDT", "SUI": "SUIUSDT", "MATIC": "MATICUSDT",
    "ARB": "ARBUSDT", "OP": "OPUSDT", "SHIB": "SHIBUSDT",
    "PEPE": "PEPEUSDT", "UNI": "UNIUSDT", "AAVE": "AAVEUSDT",
    "COMP": "COMPUSDT", "MKR": "MKRUSDT",
    # Equities/ETFs → plain ticker (outcome_resolver uses Yahoo-style)
    "SPY": "SPY", "QQQ": "QQQ", "AAPL": "AAPL", "NVDA": "NVDA",
    "TSLA": "TSLA", "MSFT": "MSFT", "AMZN": "AMZN", "META": "META",
    "GOOG": "GOOG", "AMD": "AMD", "COIN": "COIN", "MSTR": "MSTR",
    "PLTR": "PLTR", "NFLX": "NFLX", "ARKK": "ARKK",
    "GLD": "GLD", "SLV": "SLV",
}

# Regex patterns for extracting trading signals
ENTRY_RE = re.compile(r'(?:entry|buy|long)\s*[:@=\s]+\$?([\d,]+\.?\d*)', re.I)
TP_RE = re.compile(r'(?:tp|target|take.?profit)\s*[:@=\s]+\$?([\d,]+\.?\d*)', re.I)
SL_RE = re.compile(r'(?:sl|stop.?loss)\s*[:@=\s]+\$?([\d,]+\.?\d*)', re.I)

# Sentiment keywords
BULLISH_WORDS = ['long', 'buy', 'bullish', 'pump', 'moon', 'accumulate', 'hodl', 'hold']
BEARISH_WORDS = ['short', 'sell', 'bearish', 'dump', 'crash', 'panic', 'exit']
NEGATION_WORDS = ["don't", "dont", "not", "never", "avoid", "wouldn't", "shouldnt", "shouldn't", "cant", "can't"]
# Note: "stop" removed — conflicts with "stop loss", "stop order", etc.


def fetch_stocktwits_data(st_symbol: str) -> tuple[list[dict], str]:
    """Fetch StockTwits messages using cloudscraper."""
    if not HAS_CLOUDSCRAPER:
        print("  Error: cloudscraper not installed. Run: pip install cloudscraper")
        return [], "cloudscraper_not_available"
    
    url = f"{STOCKTWITS_API}/streams/symbol/{st_symbol}.json"
    
    try:
        scraper = cloudscraper.create_scraper()
        resp = scraper.get(url, timeout=20)
        
        if resp.status_code == 200:
            data = resp.json()
            messages = data.get("messages", [])
            return messages, "cloudscraper"
        else:
            return [], f"http_{resp.status_code}"
            
    except Exception as e:
        return [], f"error: {e}"


def extract_sentiment(message: dict, symbol: str) -> dict | None:
    """Extract prediction from a StockTwits message."""
    body = message.get("body", "")
    if not body or len(body) < 10:
        return None
    
    text_lower = body.lower()
    
    # Get sentiment from entities
    direction = None
    entities = message.get("entities") or {}
    sentiment = entities.get("sentiment") or {}
    basic_sentiment = sentiment.get("basic")
    
    if basic_sentiment == "Bullish":
        direction = "LONG"
    elif basic_sentiment == "Bearish":
        direction = "SHORT"
    
    # Fallback to keyword analysis with negation detection
    if not direction:
        has_negation = any(neg in text_lower for neg in NEGATION_WORDS)
        has_bullish = any(word in text_lower for word in BULLISH_WORDS)
        has_bearish = any(word in text_lower for word in BEARISH_WORDS)
        
        # If both bullish and bearish keywords found, skip (ambiguous)
        if has_bullish and has_bearish:
            return None
        
        if has_negation:
            # Negation flips the signal: "don't buy" = bearish, "don't sell" = bullish
            if has_bullish and not has_bearish:
                direction = "SHORT"
            elif has_bearish and not has_bullish:
                direction = "LONG"
        else:
            if has_bullish and not has_bearish:
                direction = "LONG"
            elif has_bearish and not has_bullish:
                direction = "SHORT"
    
    if not direction:
        return None
    
    # Extract price levels
    entry_m = ENTRY_RE.search(body)
    tp_m = TP_RE.search(body)
    sl_m = SL_RE.search(body)
    
    entry = float(entry_m.group(1).replace(",", "")) if entry_m else None
    tp = float(tp_m.group(1).replace(",", "")) if tp_m else None
    sl = float(sl_m.group(1).replace(",", "")) if sl_m else None
    
    # Calculate sentiment score
    sentiment_score = 0.6 if direction == "LONG" else -0.6
    if basic_sentiment:
        sentiment_score = 0.8 if direction == "LONG" else -0.8
    
    # Get user info
    user = message.get("user") or {}
    username = user.get("username", "unknown")
    message_id = message.get("id", 0)
    
    return {
        "predictor_id": f"stocktwits:{username}",
        "platform": "stocktwits",
        "display_name": f"@{username}",
        "symbol": SYMBOL_MAP.get(symbol, f"{symbol}USDT"),
        "direction": direction,
        "entry_price": entry,
        "take_profit": tp,
        "stop_loss": sl,
        "sentiment_score": sentiment_score,
        "source_url": f"https://stocktwits.com/message/{message_id}",
        "source_text": body[:500],
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "is_known_analyst": 0,
        "analyst_category": "stocktwits_community",
    }


def scrape_stocktwits() -> int:
    """Scrape StockTwits for crypto predictions."""
    print("=" * 60)
    print("StockTwits Scraper (cloudscraper)")
    print("=" * 60)
    
    if not HAS_CLOUDSCRAPER:
        print("\nERROR: cloudscraper is not installed.")
        print("Install it with: pip install cloudscraper")
        return 0
    
    conn = get_db()
    total = 0
    total_messages = 0
    errors = []
    
    # Scrape top symbols
    symbols_to_scrape = list(STOCKTWITS_SYMBOLS.keys())[:10]
    
    for symbol in symbols_to_scrape:
        st_symbol = STOCKTWITS_SYMBOLS.get(symbol, symbol)
        print(f"\nScraping ${symbol} (StockTwits: ${st_symbol})...")
        
        messages, method = fetch_stocktwits_data(st_symbol)
        total_messages += len(messages)
        
        if not messages and not method.startswith("cloudscraper"):
            errors.append(f"{symbol}: {method}")
            print(f"  Failed: {method}")
            continue
            
        print(f"  Got {len(messages)} messages via {method}")
        
        extracted = 0
        for msg in messages[:30]:  # Process last 30 messages
            try:
                pred = extract_sentiment(msg, symbol)
                if pred:
                    pid = insert_prediction(conn, pred)
                    if pid:
                        total += 1
                        extracted += 1
                        print(f"    + {pred['symbol']} {pred['direction']} by {pred['display_name']}")
            except Exception as e:
                print(f"    Error: {e}")
        
        print(f"  Extracted {extracted} predictions")
        
        # Rate limiting
        import time
        time.sleep(1)
    
    # Log scrape
    conn.execute("""
        INSERT INTO scrape_log (platform, scraped_at, posts_found, predictions_extracted, errors)
        VALUES ('stocktwits', ?, ?, ?, ?)
    """, (
        datetime.now(timezone.utc).isoformat(),
        total_messages,
        total,
        "; ".join(errors) if errors else None
    ))
    conn.commit()
    conn.close()
    
    print(f"\n{'=' * 60}")
    print(f"StockTwits total: {total} predictions from {total_messages} messages")
    print(f"{'=' * 60}")
    return total


if __name__ == "__main__":
    scrape_stocktwits()
