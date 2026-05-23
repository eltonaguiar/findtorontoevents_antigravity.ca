"""
Shared multi-asset symbol extraction and normalization module.

Extracts and normalizes trading symbols from natural language text
across crypto, equity/ETF, forex, and futures asset classes.
"""

import re
from typing import Dict, List, Set, Tuple

# ---------------------------------------------------------------------------
# Denylist — common English words / acronyms that look like tickers
# ---------------------------------------------------------------------------
DENYLIST: Set[str] = {
    "A", "I", "AI", "CEO", "IPO", "SEC", "ETF", "USD", "THE", "FOR", "ARE",
    "ALL", "NEW", "NOW", "TOP", "BIG", "LOW", "HIGH", "UP", "AN", "AT", "BY",
    "DO", "GO", "IF", "IN", "IS", "IT", "NO", "OF", "OK", "ON", "OR", "SO",
    "TO", "US", "WE", "BE", "HE", "ME", "MY", "TV", "UK", "VS", "PM", "AM",
    "CTO", "CFO", "COO", "API", "FAQ", "FYI", "IMO", "TBH", "ATH", "ATL",
}

# ---------------------------------------------------------------------------
# Known symbol maps
# ---------------------------------------------------------------------------
CRYPTO_ALIASES: Dict[str, str] = {
    "bitcoin": "BTCUSDT", "btc": "BTCUSDT",
    "ethereum": "ETHUSDT", "eth": "ETHUSDT", "ether": "ETHUSDT",
    "solana": "SOLUSDT", "sol": "SOLUSDT",
    "bnb": "BNBUSDT", "binance": "BNBUSDT",
    "dogecoin": "DOGEUSDT", "doge": "DOGEUSDT",
    "cardano": "ADAUSDT", "ada": "ADAUSDT",
    "xrp": "XRPUSDT", "ripple": "XRPUSDT",
    "polkadot": "DOTUSDT", "dot": "DOTUSDT",
    "avalanche": "AVAXUSDT", "avax": "AVAXUSDT",
    "chainlink": "LINKUSDT", "link": "LINKUSDT",
    "sui": "SUIUSDT", "near": "NEARUSDT",
    "pepe": "PEPEUSDT", "shib": "SHIBUSDT",
    "arb": "ARBUSDT", "op": "OPUSDT",
    "apt": "APTUSDT", "sei": "SEIUSDT",
    "inj": "INJUSDT", "fil": "FILUSDT",
    "tia": "TIAUSDT", "wif": "WIFUSDT",
    "bonk": "BONKUSDT", "render": "RENDERUSDT",
    "ton": "TONUSDT", "atom": "ATOMUSDT",
    "ftm": "FTMUSDT", "matic": "MATICUSDT",
}

KNOWN_EQUITIES: Set[str] = {
    "AAPL", "MSFT", "GOOG", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
    "AMD", "INTC", "NFLX", "COIN", "MSTR", "PLTR", "SOFI",
    "SPY", "QQQ", "IWM", "DIA", "ARKK", "XLF", "XLE", "GLD", "SLV",
    "TQQQ", "SQQQ", "UVXY", "VIX",
}

# ETF subset for finer asset_class identification
_KNOWN_ETFS: Set[str] = {
    "SPY", "QQQ", "IWM", "DIA", "ARKK", "XLF", "XLE", "GLD", "SLV",
    "TQQQ", "SQQQ", "UVXY",
}

KNOWN_FOREX: Set[str] = {
    "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD",
    "NZDUSD", "EURGBP", "EURJPY", "GBPJPY",
}

KNOWN_FUTURES: Set[str] = {
    "ES", "NQ", "YM", "RTY", "CL", "GC", "SI", "ZB", "ZN",
}

# Build a set of all crypto base symbols (uppercase) for quick lookup
_CRYPTO_BASES: Set[str] = {v.replace("USDT", "") for v in CRYPTO_ALIASES.values()}

# ---------------------------------------------------------------------------
# Compiled regex patterns (module-level for performance)
# ---------------------------------------------------------------------------

# $TICKER cashtags — e.g. $BTC, $AAPL
RE_CASHTAG = re.compile(r"\$([A-Za-z]{1,10})\b")

# Crypto USDT pairs — e.g. BTCUSDT, ETHUSDT
RE_CRYPTO_USDT = re.compile(r"\b([A-Z]{2,10}USDT)\b")

# Crypto slash pairs — e.g. BTC/USD, ETH/USDT, BTC/USDC
RE_CRYPTO_SLASH = re.compile(r"\b([A-Z]{2,10})/(USD[TC]?)\b")

# Forex slash or dash pairs — e.g. EUR/USD, EUR-USD
RE_FOREX_SLASH = re.compile(r"\b([A-Z]{3})[/\-]([A-Z]{3})\b")

# Futures patterns — /ES, /NQ, ES_F, NQ_F
RE_FUTURES = re.compile(r"(?:/([A-Z]{1,4})\b)|(?:\b([A-Z]{1,4})_F\b)")

# Standalone uppercase words (potential tickers) — 2-5 chars
RE_UPPER_WORD = re.compile(r"\b([A-Z]{2,5})\b")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_symbols(text: str) -> List[Dict[str, str]]:
    """
    Extract and normalize trading symbols from text.

    Returns list of dicts, deduplicated by normalized symbol:
    [
        {"symbol": "BTCUSDT", "asset_class": "crypto", "raw": "$BTC"},
        {"symbol": "AAPL", "asset_class": "equity", "raw": "$AAPL"},
        {"symbol": "EURUSD=X", "asset_class": "forex", "raw": "EUR/USD"},
    ]

    Order of detection:
    1. $TICKER cashtag patterns
    2. Crypto USDT pairs (BTCUSDT etc)
    3. Crypto aliases (bitcoin, ethereum, etc)
    4. Forex pair patterns (EUR/USD, EURUSD)
    5. Known equities by exact uppercase match
    6. Futures patterns (/ES, ES_F)
    """
    results: List[Dict[str, str]] = []
    seen: Set[str] = set()

    def _add(symbol: str, asset_class: str, raw: str) -> None:
        if symbol not in seen:
            seen.add(symbol)
            results.append({
                "symbol": symbol,
                "asset_class": asset_class,
                "raw": raw,
            })

    # 1. $TICKER cashtags
    for m in RE_CASHTAG.finditer(text):
        raw = m.group(0)  # e.g. "$BTC"
        ticker = m.group(1).upper()
        if ticker in DENYLIST:
            continue
        sym, ac = _resolve_ticker(ticker)
        _add(sym, ac, raw)

    # 2. Crypto USDT pairs already in text (BTCUSDT, ETHUSDT, ...)
    for m in RE_CRYPTO_USDT.finditer(text):
        raw = m.group(0)
        _add(raw, "crypto", raw)

    # 3. Crypto slash pairs (BTC/USD, ETH/USDT)
    for m in RE_CRYPTO_SLASH.finditer(text):
        raw = m.group(0)
        base = m.group(1)
        if base in _CRYPTO_BASES:
            _add(base + "USDT", "crypto", raw)

    # 4. Crypto aliases by word (bitcoin, ethereum, solana, ...)
    text_lower = text.lower()
    for alias, norm in CRYPTO_ALIASES.items():
        # Only match whole words
        if re.search(r"\b" + re.escape(alias) + r"\b", text_lower):
            _add(norm, "crypto", alias)

    # 5. Forex patterns
    for m in RE_FOREX_SLASH.finditer(text):
        raw = m.group(0)
        pair = m.group(1) + m.group(2)
        if pair in KNOWN_FOREX:
            _add(pair + "=X", "forex", raw)

    # Also detect unseparated forex (EURUSD written as one word)
    for pair in KNOWN_FOREX:
        if pair in text:
            _add(pair + "=X", "forex", pair)

    # 6. Known equities by exact uppercase match (scan all uppercase words)
    for m in RE_UPPER_WORD.finditer(text):
        word = m.group(1)
        if word in DENYLIST:
            continue
        if word in KNOWN_EQUITIES:
            ac = "etf" if word in _KNOWN_ETFS else "equity"
            _add(word, ac, word)

    # 7. Futures patterns (/ES, ES_F)
    for m in RE_FUTURES.finditer(text):
        raw = m.group(0)
        base = m.group(1) or m.group(2)
        if base and base in KNOWN_FUTURES:
            _add(base + "=F", "futures", raw)

    # Also detect standalone known futures names (only if not already found)
    for m in RE_UPPER_WORD.finditer(text):
        word = m.group(1)
        if word in KNOWN_FUTURES and word not in DENYLIST:
            _add(word + "=F", "futures", word)

    return results


def identify_asset_class(symbol: str) -> str:
    """
    Identify asset class from a normalized symbol.

    Returns: "crypto" | "equity" | "etf" | "forex" | "futures" | "unknown"
    """
    if not symbol:
        return "unknown"

    s = symbol.upper()

    # Futures: ends with =F
    if s.endswith("=F"):
        return "futures"

    # Forex: ends with =X
    if s.endswith("=X"):
        return "forex"

    # Crypto: ends with USDT / USDC / BUSD, or base in known crypto
    if s.endswith(("USDT", "USDC", "BUSD")):
        return "crypto"

    # Known equity / ETF
    if s in _KNOWN_ETFS:
        return "etf"
    if s in KNOWN_EQUITIES:
        return "equity"

    # Check if it is a known crypto base
    if s in _CRYPTO_BASES or s.lower() in CRYPTO_ALIASES:
        return "crypto"

    # Known forex without suffix
    if s in KNOWN_FOREX:
        return "forex"

    # Known futures without suffix
    if s in KNOWN_FUTURES:
        return "futures"

    return "unknown"


def normalize_symbol(raw: str) -> Tuple[str, str]:
    """
    Normalize a single raw symbol string.

    Returns: (normalized_symbol, asset_class)

    Examples:
        normalize_symbol("$BTC")    -> ("BTCUSDT", "crypto")
        normalize_symbol("bitcoin") -> ("BTCUSDT", "crypto")
        normalize_symbol("EUR/USD") -> ("EURUSD=X", "forex")
        normalize_symbol("/ES")     -> ("ES=F", "futures")
        normalize_symbol("AAPL")    -> ("AAPL", "equity")
    """
    if not raw:
        return ("", "unknown")

    stripped = raw.strip()

    # Strip leading $
    if stripped.startswith("$"):
        stripped = stripped[1:]

    # Check crypto alias (case-insensitive)
    lower = stripped.lower()
    if lower in CRYPTO_ALIASES:
        sym = CRYPTO_ALIASES[lower]
        return (sym, "crypto")

    upper = stripped.upper()

    # Already a USDT pair
    if re.match(r"^[A-Z]{2,10}USDT$", upper):
        return (upper, "crypto")

    # Crypto slash pair: BTC/USD, ETH/USDT
    m = re.match(r"^([A-Z]{2,10})/(USD[TC]?)$", upper)
    if m and m.group(1) in _CRYPTO_BASES:
        return (m.group(1) + "USDT", "crypto")

    # Forex slash/dash: EUR/USD, EUR-USD
    m = re.match(r"^([A-Z]{3})[/\-]([A-Z]{3})$", upper)
    if m:
        pair = m.group(1) + m.group(2)
        if pair in KNOWN_FOREX:
            return (pair + "=X", "forex")

    # Unseparated forex (EURUSD)
    if upper in KNOWN_FOREX:
        return (upper + "=X", "forex")

    # Futures: /ES or ES_F
    m = re.match(r"^/([A-Z]{1,4})$", upper)
    if m and m.group(1) in KNOWN_FUTURES:
        return (m.group(1) + "=F", "futures")

    m = re.match(r"^([A-Z]{1,4})_F$", upper)
    if m and m.group(1) in KNOWN_FUTURES:
        return (m.group(1) + "=F", "futures")

    # Standalone known futures
    if upper in KNOWN_FUTURES:
        return (upper + "=F", "futures")

    # Known equity/ETF
    if upper in KNOWN_EQUITIES:
        ac = "etf" if upper in _KNOWN_ETFS else "equity"
        return (upper, ac)

    # Known crypto base without USDT suffix
    if upper in _CRYPTO_BASES:
        return (upper + "USDT", "crypto")

    # Fallback: return uppercased, unknown
    return (upper, "unknown")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _resolve_ticker(ticker: str) -> Tuple[str, str]:
    """Resolve an uppercase ticker (from cashtag) to (symbol, asset_class)."""
    # Crypto alias
    lower = ticker.lower()
    if lower in CRYPTO_ALIASES:
        return (CRYPTO_ALIASES[lower], "crypto")

    # Known crypto base → append USDT
    if ticker in _CRYPTO_BASES:
        return (ticker + "USDT", "crypto")

    # Known equity / ETF
    if ticker in KNOWN_EQUITIES:
        ac = "etf" if ticker in _KNOWN_ETFS else "equity"
        return (ticker, ac)

    # Known forex
    if ticker in KNOWN_FOREX:
        return (ticker + "=X", "forex")

    # Known futures
    if ticker in KNOWN_FUTURES:
        return (ticker + "=F", "futures")

    # Unknown — return as-is
    return (ticker, "unknown")
