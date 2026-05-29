"""Price + indicator layer for the AI-model paper portfolios (Phase 3).

Provides daily-close, moving-average, history and ATR helpers backed by a
MULTI-SOURCE FAILOVER chain (CLAUDE.md "API Failover Rule" — never a single
endpoint):

    CRYPTO              : Binance mirrors (api, api1, api2, api3)
                          -> CoinGecko -> KuCoin -> CryptoCompare
    EQUITY/ETF/FX/etc.  : yfinance -> stooq -> AlphaVantage (if ALPHAVANTAGE_API_KEY)

Design contract (see docs/DESIGN_AI_MODEL_HEDGE_FUND_PORTFOLIOS_2026-05-29.md §5):
    get_close(symbol, asset_class)            -> float | None
    get_ma(symbol, asset_class, days)         -> float | None
    get_history(symbol, asset_class, lookback)-> list[float]   (oldest -> newest)
    get_atr(symbol, asset_class, period)      -> float | None

Everything degrades gracefully: each function returns ``None`` / ``[]`` rather
than raising, and emits a single ``::warning`` log line per failed source so the
daily job's masking-policy linter stays happy (no SILENT maskers).

No DB writes here. ``requests`` / ``yfinance`` are imported lazily inside the
fetchers so this module imports cleanly even when those deps are absent (the
dry-run path tolerates missing prices).
"""
from __future__ import annotations

import sys
import time

# Asset classes routed through the equity-style (yfinance/stooq) chain.
_EQUITY_LIKE = {"EQUITY", "ETF", "FOREX", "FX", "COMMODITY", "BOND",
                "FUTURES", "INDEX", "PENNY"}

# Simple per-process cache so a single run never hits the same symbol twice.
_HISTORY_CACHE: dict[tuple, list[float]] = {}


def _warn(source: str, symbol: str, err: object) -> None:
    """Emit a GH-Actions ``::warning`` line for a failed source (never silent)."""
    msg = str(err).replace("\n", " ")[:200]
    print(f"::warning title=prices::{source} failed for {symbol}: {msg}",
          file=sys.stderr, flush=True)


def _is_crypto(asset_class: str) -> bool:
    return (asset_class or "").strip().upper() in ("CRYPTO", "MEME", "MEMECOIN")


# --------------------------------------------------------------------------- #
# Symbol normalization
# --------------------------------------------------------------------------- #
def _crypto_base(symbol: str) -> str:
    """Strip common quote/suffix decorations -> bare base asset (e.g. BTC)."""
    s = (symbol or "").strip().upper()
    for sep in ("-", "/"):
        if sep in s:
            s = s.split(sep, 1)[0]
    for suffix in ("USDT", "USDC", "USD", "PERP"):
        if s.endswith(suffix) and len(s) > len(suffix):
            s = s[: -len(suffix)]
    return s


def _binance_pair(symbol: str) -> str:
    return _crypto_base(symbol) + "USDT"


def _coingecko_id(symbol: str) -> str | None:
    base = _crypto_base(symbol)
    table = {
        "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "BNB": "binancecoin",
        "XRP": "ripple", "ADA": "cardano", "DOGE": "dogecoin", "AVAX": "avalanche-2",
        "DOT": "polkadot", "MATIC": "matic-network", "LINK": "chainlink",
        "LTC": "litecoin", "SHIB": "shiba-inu", "TRX": "tron", "UNI": "uniswap",
        "ATOM": "cosmos", "XLM": "stellar", "NEAR": "near", "APT": "aptos",
        "ARB": "arbitrum", "OP": "optimism", "PEPE": "pepe", "SUI": "sui",
    }
    return table.get(base)


# --------------------------------------------------------------------------- #
# CRYPTO history fetchers (failover chain)
# --------------------------------------------------------------------------- #
def _crypto_history(symbol: str, lookback: int) -> list[float]:
    """Daily closes oldest->newest for a crypto symbol via the failover chain."""
    for fetch in (_binance_history, _coingecko_history, _kucoin_history,
                  _cryptocompare_history):
        try:
            closes = fetch(symbol, lookback)
        except Exception as exc:  # noqa: BLE001 — degrade per source
            _warn(fetch.__name__, symbol, exc)
            continue
        if closes:
            return closes[-lookback:]
    return []


def _binance_history(symbol: str, lookback: int) -> list[float]:
    import requests

    pair = _binance_pair(symbol)
    limit = max(2, min(1000, lookback + 5))
    last_err = None
    for host in ("api", "api1", "api2", "api3"):
        url = f"https://{host}.binance.com/api/v3/klines"
        try:
            r = requests.get(url, params={"symbol": pair, "interval": "1d",
                                          "limit": limit}, timeout=8)
            r.raise_for_status()
            rows = r.json()
            closes = [float(k[4]) for k in rows if k and k[4] is not None]
            if closes:
                return closes
        except Exception as exc:  # noqa: BLE001 — try next mirror
            last_err = exc
            continue
    if last_err is not None:
        raise last_err
    return []


def _coingecko_history(symbol: str, lookback: int) -> list[float]:
    import requests

    cid = _coingecko_id(symbol)
    if not cid:
        raise ValueError(f"no coingecko id for {symbol}")
    url = f"https://api.coingecko.com/api/v3/coins/{cid}/market_chart"
    r = requests.get(url, params={"vs_currency": "usd",
                                  "days": max(1, lookback)}, timeout=10)
    r.raise_for_status()
    prices = r.json().get("prices") or []
    return [float(p[1]) for p in prices if p and p[1] is not None]


def _kucoin_history(symbol: str, lookback: int) -> list[float]:
    import requests

    base = _crypto_base(symbol)
    sym = f"{base}-USDT"
    end = int(time.time())
    start = end - (lookback + 5) * 86400
    url = "https://api.kucoin.com/api/v1/market/candles"
    r = requests.get(url, params={"type": "1day", "symbol": sym,
                                  "startAt": start, "endAt": end}, timeout=10)
    r.raise_for_status()
    rows = r.json().get("data") or []
    # KuCoin returns newest-first; candle = [time, open, close, high, low, ...]
    closes = [float(c[2]) for c in reversed(rows) if c and c[2] is not None]
    return closes


def _cryptocompare_history(symbol: str, lookback: int) -> list[float]:
    import requests

    base = _crypto_base(symbol)
    url = "https://min-api.cryptocompare.com/data/v2/histoday"
    r = requests.get(url, params={"fsym": base, "tsym": "USD",
                                  "limit": max(1, lookback)}, timeout=10)
    r.raise_for_status()
    payload = r.json()
    rows = (payload.get("Data") or {}).get("Data") or []
    return [float(d["close"]) for d in rows if d.get("close")]


# --------------------------------------------------------------------------- #
# EQUITY/ETF/FX/COMMODITY history fetchers (failover chain)
# --------------------------------------------------------------------------- #
def _equity_history(symbol: str, lookback: int) -> list[float]:
    for fetch in (_yfinance_history, _stooq_history, _alphavantage_history):
        try:
            closes = fetch(symbol, lookback)
        except Exception as exc:  # noqa: BLE001 — degrade per source
            _warn(fetch.__name__, symbol, exc)
            continue
        if closes:
            return closes[-lookback:]
    return []


def _yfinance_history(symbol: str, lookback: int) -> list[float]:
    import yfinance as yf

    period_days = max(7, lookback + 10)
    period = f"{period_days}d" if period_days <= 729 else "5y"
    tkr = yf.Ticker(symbol)
    hist = tkr.history(period=period, interval="1d", auto_adjust=False)
    if hist is None or hist.empty or "Close" not in hist:
        return []
    closes = [float(c) for c in hist["Close"].tolist()
              if c is not None and c == c]  # drop NaN
    return closes


def _stooq_history(symbol: str, lookback: int) -> list[float]:
    import csv
    import io

    import requests

    sym = symbol.strip().lower()
    # Stooq US equities/ETFs commonly need a ".us" suffix; forex like eurusd is bare.
    candidates = [sym]
    if "." not in sym and "=" not in sym and "^" not in sym and len(sym) <= 5:
        candidates.append(sym + ".us")
    last_err = None
    for cand in candidates:
        url = f"https://stooq.com/q/d/l/?s={cand}&i=d"
        try:
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            text = r.text.strip()
            if not text or text.lower().startswith("<"):
                continue
            reader = csv.DictReader(io.StringIO(text))
            closes = []
            for row in reader:
                c = row.get("Close")
                if c not in (None, "", "N/D"):
                    try:
                        closes.append(float(c))
                    except ValueError:
                        pass
            if closes:
                return closes
        except Exception as exc:  # noqa: BLE001 — try next candidate
            last_err = exc
            continue
    if last_err is not None:
        raise last_err
    return []


def _alphavantage_history(symbol: str, lookback: int) -> list[float]:
    import os

    import requests

    key = os.environ.get("ALPHAVANTAGE_API_KEY") or os.environ.get("ALPHA_VANTAGE_API_KEY")
    if not key:
        raise RuntimeError("ALPHAVANTAGE_API_KEY not set")
    url = "https://www.alphavantage.co/query"
    r = requests.get(url, params={"function": "TIME_SERIES_DAILY",
                                  "symbol": symbol, "outputsize": "compact",
                                  "apikey": key}, timeout=15)
    r.raise_for_status()
    series = r.json().get("Time Series (Daily)") or {}
    if not series:
        raise RuntimeError("AlphaVantage returned no series")
    # keys are dates; sort ascending (oldest -> newest)
    closes = [float(series[d]["4. close"]) for d in sorted(series)]
    return closes


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def get_history(symbol: str, asset_class: str, lookback: int = 60) -> list[float]:
    """Return up to ``lookback`` daily closes oldest->newest, or [] on failure."""
    if not symbol:
        return []
    lookback = max(2, int(lookback or 2))
    key = ((symbol or "").upper(), (asset_class or "").upper(), lookback)
    if key in _HISTORY_CACHE:
        return _HISTORY_CACHE[key]

    if _is_crypto(asset_class):
        closes = _crypto_history(symbol, lookback)
    else:
        closes = _equity_history(symbol, lookback)

    if not closes:
        print(f"::warning title=prices::no price history for {symbol} "
              f"({asset_class}) after all sources", file=sys.stderr, flush=True)
    _HISTORY_CACHE[key] = closes
    return closes


def get_close(symbol: str, asset_class: str) -> float | None:
    """Most-recent daily close, or None if every source failed."""
    hist = get_history(symbol, asset_class, lookback=5)
    if hist:
        return hist[-1]
    return None


def get_ma(symbol: str, asset_class: str, days: int) -> float | None:
    """Simple moving average of the last ``days`` daily closes, or None."""
    if not days or days < 1:
        return None
    # fetch a touch more than `days` so a partial tail still yields a clean MA
    hist = get_history(symbol, asset_class, lookback=days + 5)
    if len(hist) < days:
        if hist:
            print(f"::warning title=prices::insufficient history for {symbol} "
                  f"MA{days} (have {len(hist)})", file=sys.stderr, flush=True)
        return None
    window = hist[-days:]
    return sum(window) / len(window)


def get_atr(symbol: str, asset_class: str, period: int = 14) -> float | None:
    """Average True Range over ``period`` days.

    We only have daily closes (not OHLC), so True Range is approximated as the
    absolute close-to-close change — a standard fallback when intraday H/L are
    unavailable. Returns None if there is insufficient history.
    """
    period = max(1, int(period or 14))
    hist = get_history(symbol, asset_class, lookback=period + 5)
    if len(hist) < period + 1:
        return None
    diffs = [abs(hist[i] - hist[i - 1]) for i in range(1, len(hist))]
    window = diffs[-period:]
    if not window:
        return None
    return sum(window) / len(window)


if __name__ == "__main__":  # tiny manual smoke (no asserts on network)
    for sym, cls in (("BTC", "CRYPTO"), ("AAPL", "EQUITY"), ("SPY", "ETF")):
        c = get_close(sym, cls)
        print(f"{sym} ({cls}): close={c} ma20={get_ma(sym, cls, 20)} "
              f"atr14={get_atr(sym, cls, 14)}")
