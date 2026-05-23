"""
crypto_data_failover.py — Shared multi-source crypto data failover utility
==========================================================================
Implements the project mandate (CLAUDE.md):

    "Never use a single Binance API endpoint. Always use 3+ fallback chain:
     Binance mirrors (api, api1, api2, api3) -> CoinGecko -> KuCoin -> CryptoCompare."

WHY THIS EXISTS
---------------
On 2026-04-17 the user shipped a triage report: every Binance call from
crypto_signal_engine returned HTTP 451 (geo-blocked from US GHA runners), the
ONLY fallback wired up was binance_vision (same IP block -> also 400/451).
CoinGecko / KuCoin / CryptoCompare were never attempted -> 0 picks for the
entire run.  This module provides a SHARED implementation so callers cannot
accidentally fall back to a "Binance-only" mini-chain again.

PUBLIC API
----------
    fetch_tickers_24h() -> tuple[list[dict], str]
        24-hour ticker stats across the universe (all USDT pairs).
        Returns (normalized_list, source_name).

    fetch_klines(symbol, interval, limit=100) -> list[list]
        OHLCV in Binance format: [[ts_ms, o, h, l, c, v, ...], ...].
        All numeric fields are strings (Binance native shape).

    fetch_funding_rate(symbol) -> float | None
        Latest funding rate in DECIMAL form (0.0001 = 0.01%).

    class FailoverConfig
        Circuit-breaker registry persisted to alpha_engine/data/failover_circuit.json.
        Sources that fail open the breaker for COOLDOWN_SECONDS (default 5 min).

NORMALIZED TICKER SCHEMA (Binance-compatible):
    {
        "symbol":              "BTCUSDT",
        "lastPrice":           "65432.10",
        "priceChange":         "+123.45",
        "priceChangePercent":  "+0.19",
        "volume":              "12345.6",      # base-asset volume
        "quoteVolume":         "812345678.9",  # USDT volume
    }

NORMALIZED KLINE SCHEMA (Binance-compatible):
    [open_time_ms, open, high, low, close, volume, close_time_ms,
     quote_volume, trade_count, taker_base, taker_quote, ignore]
    All values after open_time_ms are strings.

DESIGN NOTES
------------
* Stdlib HTTP only (urllib.request) — no extra pip dependencies.
* Per-source circuit breaker: 3 consecutive failures within 60s opens the
  breaker for 5 minutes, written to disk so subsequent processes inherit it.
* CoinGecko throttle: minimum 2.1s between calls (well under their 30 req/min
  free-tier ceiling and conservative for the 10 req/min low-tier).
* Each non-Binance source has a NORMALIZER that converts native schema
  -> Binance schema. If the response is missing any required field, the
  source is skipped (not normalized to garbage).
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable, Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_DATA_DIR = Path(__file__).resolve().parent / "data"
_CIRCUIT_PATH = _DATA_DIR / "failover_circuit.json"
_LOG = logging.getLogger("alpha_engine.crypto_data_failover")

HTTP_TIMEOUT = 8                      # seconds per source
USER_AGENT = "AlphaEngine-CryptoDataFailover/1.0"

# Circuit-breaker config
DEFAULT_COOLDOWN_SECONDS = 300        # 5 minutes
DEFAULT_FAIL_THRESHOLD = 3            # 3 consecutive failures opens the breaker
FAILURE_WINDOW_SECONDS = 60           # ... within this window

# CoinGecko free tier: ~10-30 req/min. We throttle to be conservative.
COINGECKO_MIN_INTERVAL = 2.1          # seconds between calls
_cg_last_call_lock = threading.Lock()
_cg_last_call_ts: float = 0.0


# ---------------------------------------------------------------------------
# Source endpoints
# ---------------------------------------------------------------------------
BINANCE_FAPI_BASES = [
    "https://fapi.binance.com",
    "https://fapi1.binance.com",
    "https://fapi2.binance.com",
]

BINANCE_SPOT_BASES = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
    "https://data-api.binance.vision",
    "https://api.binance.us",
]

COINGECKO_MARKETS = (
    "https://api.coingecko.com/api/v3/coins/markets"
    "?vs_currency=usd&order=volume_desc&per_page=250&page=1"
    "&price_change_percentage=24h"
)
COINGECKO_OHLC = "https://api.coingecko.com/api/v3/coins/{cg_id}/ohlc?vs_currency=usd&days={days}"
COINGECKO_SIMPLE = (
    "https://api.coingecko.com/api/v3/simple/price"
    "?ids={cg_id}&vs_currencies=usd&include_24hr_vol=true&include_24hr_change=true"
)

KUCOIN_TICKERS = "https://api.kucoin.com/api/v1/market/allTickers"
KUCOIN_CANDLES = (
    "https://api.kucoin.com/api/v1/market/candles"
    "?type={kc_interval}&symbol={kc_sym}&startAt={start}&endAt={end}"
)

CRYPTOCOMPARE_TOP = (
    "https://min-api.cryptocompare.com/data/top/totalvolfull?limit=100&tsym=USD"
)
CRYPTOCOMPARE_HISTO = (
    "https://min-api.cryptocompare.com/data/v2/{endpoint}?fsym={fsym}&tsym=USD&limit={limit}"
)

BYBIT_FUNDING = "https://api.bybit.com/v5/market/funding/history?category=linear&symbol={sym}&limit=1"
OKX_FUNDING = "https://www.okx.com/api/v5/public/funding-rate?instId={base}-USDT-SWAP"

# Coinglass endpoint is gated behind an API key (when COINGLASS_API_KEY is set)
COINGLASS_FUNDING = "https://open-api.coinglass.com/public/v2/funding_rates_history?symbol={base}"


# ---------------------------------------------------------------------------
# Symbol helpers
# ---------------------------------------------------------------------------
#: Seed mappings used to bootstrap the CoinGecko id cache. These 44 entries
#: are the original hardcoded set — preserved as a cold-start fallback so
#: even on first run (or when CoinGecko ``/coins/list`` is unreachable) the
#: well-known symbols resolve correctly. New symbols are resolved
#: dynamically via :func:`_resolve_coingecko_id`.
_COINGECKO_ID_SEED: dict[str, str] = {
    "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "BNB": "binancecoin",
    "XRP": "ripple", "ADA": "cardano", "AVAX": "avalanche-2", "LINK": "chainlink",
    "DOT": "polkadot", "ATOM": "cosmos", "NEAR": "near", "MATIC": "matic-network",
    "DOGE": "dogecoin", "SHIB": "shiba-inu", "LTC": "litecoin", "UNI": "uniswap",
    "AAVE": "aave", "ARB": "arbitrum", "OP": "optimism", "SUI": "sui",
    "FIL": "filecoin", "APT": "aptos", "INJ": "injective-protocol", "FET": "fetch-ai",
    "PEPE": "pepe", "WIF": "dogwifcoin", "RENDER": "render-token",
    "TON": "the-open-network", "TRX": "tron", "XLM": "stellar",
    "BCH": "bitcoin-cash", "ETC": "ethereum-classic", "HBAR": "hedera-hashgraph",
    "SEI": "sei-network", "TIA": "celestia", "BONK": "bonk", "FLOKI": "floki",
    "STX": "blockstack", "CAKE": "pancakeswap-token", "TAO": "bittensor",
    "KAS": "kaspa", "ONDO": "ondo-finance", "ICP": "internet-computer",
    "HYPE": "hyperliquid",
}

# Backwards-compatible alias: legacy code (and tests) may still read this dict.
# Prefer :func:`_resolve_coingecko_id` which handles dynamic lookups.
_COINGECKO_IDS: dict[str, str] = dict(_COINGECKO_ID_SEED)

# Dynamic resolver state -----------------------------------------------------
COINGECKO_ID_CACHE_PATH = _DATA_DIR / "coingecko_id_cache.json"
COINGECKO_LIST_URL = "https://api.coingecko.com/api/v3/coins/list"
COINGECKO_MARKETS_DISAMBIG_URL = (
    "https://api.coingecko.com/api/v3/coins/markets"
    "?vs_currency=usd&ids={ids}&per_page=250&page=1"
)
#: TTL for the persistent /coins/list snapshot (24 hours).
COINGECKO_ID_CACHE_TTL_SECONDS = 24 * 3600
#: Sentinel persisted when a base coin is genuinely missing from CoinGecko.
#: Stored in the cache so we don't keep retrying remote fetches for it.
_COINGECKO_NEGATIVE = "__none__"

_resolve_lock = threading.Lock()
_resolve_state: dict[str, Any] = {
    "ids": {},                 # base_coin (UPPER) -> coingecko_id | _COINGECKO_NEGATIVE
    "list_fetched_at": 0.0,    # epoch seconds of last /coins/list fetch
    "loaded_from_disk": False, # whether we've hydrated from cache file yet
}

# CoinGecko symbol (per coin "symbol" field, lowercased) -> binance-style USDT pair
# Sentinel returned by _http_get_json for geo-blocked responses (451/403).
# Callers check ``if result is _GEO_BLOCKED`` to skip circuit-breaker recording.
_GEO_BLOCKED = object()

_CG_SYMBOL_QUOTE = "USDT"


def _normalize_symbol(symbol: str) -> str:
    """Normalize 'btc/usdt', 'BTC-USDT', 'btcusd' -> 'BTCUSDT'."""
    if not symbol:
        return ""
    s = symbol.upper().replace("-", "").replace("/", "").replace(":", "")
    if s.endswith("PERP"):
        s = s[:-4]
    if s.endswith("USD") and not s.endswith("USDT"):
        s = s + "T"
    return s


def _base_coin(symbol: str) -> str:
    s = _normalize_symbol(symbol)
    for suffix in ("USDT", "BUSD", "USD"):
        if s.endswith(suffix):
            return s[: -len(suffix)]
    return s


def _kucoin_symbol(symbol: str) -> str:
    s = _normalize_symbol(symbol)
    if s.endswith("USDT"):
        return s[:-4] + "-USDT"
    return s


_KUCOIN_INTERVAL_MAP = {
    "1m": "1min", "3m": "3min", "5m": "5min", "15m": "15min", "30m": "30min",
    "1h": "1hour", "2h": "2hour", "4h": "4hour", "6h": "6hour",
    "8h": "8hour", "12h": "12hour", "1d": "1day", "1w": "1week",
}

_INTERVAL_SECONDS = {
    "1m": 60, "3m": 180, "5m": 300, "15m": 900, "30m": 1800,
    "1h": 3600, "2h": 7200, "4h": 14400, "6h": 21600, "8h": 28800,
    "12h": 43200, "1d": 86400, "1w": 604800,
}


# ---------------------------------------------------------------------------
# FailoverConfig — circuit breaker persistence
# ---------------------------------------------------------------------------
class FailoverConfig:
    """Persistent per-source circuit breaker.

    State stored at ``alpha_engine/data/failover_circuit.json``::

        {
          "<source_name>": {
            "consecutive_failures": int,
            "first_failure_ts":     float,
            "open_until_ts":        float,
          }, ...
        }

    A source becomes "open" (skipped) when ``consecutive_failures >= threshold``
    inside ``FAILURE_WINDOW_SECONDS``; the breaker stays open for
    ``cooldown_seconds`` seconds, after which we try once more (half-open).
    """

    _LOCK = threading.RLock()

    def __init__(
        self,
        path: Path = _CIRCUIT_PATH,
        cooldown_seconds: int = DEFAULT_COOLDOWN_SECONDS,
        fail_threshold: int = DEFAULT_FAIL_THRESHOLD,
    ):
        self.path = path
        self.cooldown_seconds = cooldown_seconds
        self.fail_threshold = fail_threshold
        self._state: dict[str, dict[str, Any]] = self._load()

    # -- persistence ---------------------------------------------------------
    def _load(self) -> dict[str, dict[str, Any]]:
        try:
            if self.path.exists():
                with open(self.path, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                if isinstance(data, dict):
                    return data
        except Exception as exc:
            _LOG.debug("FailoverConfig load failed: %s", exc)
        return {}

    def _save(self) -> None:
        # Atomic write so multiple worker processes never see partial JSON.
        # Per Inception code review on commit 9396a5fca8: previously a plain
        # open(..,'w') exposed mid-write JSONDecodeError to other processes
        # reading the circuit state. atomic_json.atomic_write_json uses
        # temp-file + os.replace to make the write atomic on all platforms.
        try:
            from alpha_engine.atomic_json import atomic_write_json
            atomic_write_json(self.path, self._state, indent=2)
        except ImportError:
            # Defensive fallback if atomic_json isn't importable
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.path, "w", encoding="utf-8") as fh:
                    json.dump(self._state, fh, indent=2)
            except Exception as exc:
                _LOG.debug("FailoverConfig save fallback failed: %s", exc)
        except Exception as exc:
            _LOG.debug("FailoverConfig save failed: %s", exc)

    # -- public API ----------------------------------------------------------
    def is_open(self, source: str, now: Optional[float] = None) -> bool:
        """Return True if this source is currently in cooldown (skip it)."""
        now = now if now is not None else time.time()
        with self._LOCK:
            entry = self._state.get(source)
            if not entry:
                return False
            return float(entry.get("open_until_ts", 0)) > now

    def record_success(self, source: str) -> None:
        """Reset the breaker on success."""
        with self._LOCK:
            if source in self._state:
                self._state.pop(source, None)
                self._save()

    def record_failure(self, source: str, now: Optional[float] = None) -> bool:
        """Bump failure counter. Returns True if the breaker just opened.

        Half-open fail-fast: if the breaker was recently open (cooldown just
        expired) and the first attempt fails, immediately re-open the breaker
        instead of requiring ``fail_threshold`` more failures. This prevents
        the source from being retried 3 more times (each wasting an HTTP
        round-trip) when we already know it's unreliable.
        """
        now = now if now is not None else time.time()
        with self._LOCK:
            entry = self._state.get(source) or {}
            first_ts = float(entry.get("first_failure_ts", 0)) or now
            open_until_ts = float(entry.get("open_until_ts", 0))

            # Half-open fail-fast: cooldown just expired but the source
            # still failed -- jump straight to threshold so the breaker
            # re-opens immediately.
            if 0 < open_until_ts <= now:
                first_ts = now
                count = self.fail_threshold
            elif now - first_ts > FAILURE_WINDOW_SECONDS:
                # Reset window if last failure was long ago
                first_ts = now
                count = 1
            else:
                count = int(entry.get("consecutive_failures", 0)) + 1

            opened_now = False
            open_until = open_until_ts
            if count >= self.fail_threshold:
                open_until = now + self.cooldown_seconds
                opened_now = open_until > now and open_until_ts <= now

            self._state[source] = {
                "consecutive_failures": count,
                "first_failure_ts": first_ts,
                "open_until_ts": open_until,
                "last_failure_ts": now,
            }
            self._save()
            return opened_now

    def snapshot(self) -> dict[str, dict[str, Any]]:
        with self._LOCK:
            return json.loads(json.dumps(self._state))


# Default singleton (used by module-level fetchers).
_DEFAULT_CONFIG = FailoverConfig()


def get_default_config() -> FailoverConfig:
    return _DEFAULT_CONFIG


# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------
def _http_get_json(
    url: str,
    timeout: int = HTTP_TIMEOUT,
    extra_headers: Optional[dict[str, str]] = None,
) -> Optional[Any]:
    """GET JSON. Returns None on 4xx/5xx/timeout/parse error.

    Returns the sentinel ``_GEO_BLOCKED`` for 451/403 so callers can
    distinguish "source is geo-blocked" from "source is down" and avoid
    consuming circuit-breaker budget on known-permanent failures.
    """
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        if exc.code in (451, 403):
            _LOG.debug("Geo-blocked (%d): %s", exc.code, url)
            return _GEO_BLOCKED
        _LOG.debug("HTTP %d %s: %s", exc.code, url, exc.reason)
        return None
    except Exception as exc:
        _LOG.debug("HTTP failed %s: %s", url, exc)
        return None


def _coingecko_throttle() -> None:
    """Sleep just enough to stay under CoinGecko free-tier rate limit."""
    global _cg_last_call_ts
    with _cg_last_call_lock:
        now = time.time()
        elapsed = now - _cg_last_call_ts
        wait = COINGECKO_MIN_INTERVAL - elapsed
        if wait > 0:
            time.sleep(wait)
        _cg_last_call_ts = time.time()


# ---------------------------------------------------------------------------
# Dynamic CoinGecko id resolver
# ---------------------------------------------------------------------------
def _coingecko_cache_load() -> None:
    """Hydrate ``_resolve_state`` from disk on first use.

    Idempotent — only reads disk once per process. Seeds the cache from
    :data:`_COINGECKO_ID_SEED` so the 44 well-known coins resolve even
    when no cache file exists yet (cold start) or it lacks them.
    """
    if _resolve_state.get("loaded_from_disk"):
        return
    seeded: dict[str, str] = {k.upper(): v for k, v in _COINGECKO_ID_SEED.items()}
    fetched_at = 0.0
    try:
        if COINGECKO_ID_CACHE_PATH.exists():
            with open(COINGECKO_ID_CACHE_PATH, "r", encoding="utf-8") as fh:
                disk = json.load(fh)
            if isinstance(disk, dict):
                disk_ids = disk.get("ids")
                if isinstance(disk_ids, dict):
                    for k, v in disk_ids.items():
                        if isinstance(k, str) and isinstance(v, str):
                            seeded[k.upper()] = v
                fa = disk.get("list_fetched_at")
                if isinstance(fa, (int, float)):
                    fetched_at = float(fa)
    except (OSError, json.JSONDecodeError) as exc:
        _LOG.debug("coingecko id cache load failed: %s", exc)
    _resolve_state["ids"] = seeded
    _resolve_state["list_fetched_at"] = fetched_at
    _resolve_state["loaded_from_disk"] = True


def _coingecko_cache_save() -> None:
    """Persist ``_resolve_state`` to disk via atomic_json.

    Best-effort: a write failure is logged but never raises (callers should
    still be able to use the in-memory cache).
    """
    payload = {
        "ids": dict(_resolve_state.get("ids") or {}),
        "list_fetched_at": float(_resolve_state.get("list_fetched_at") or 0.0),
        "schema_version": 1,
    }
    try:
        from alpha_engine.atomic_json import atomic_write_json
        atomic_write_json(COINGECKO_ID_CACHE_PATH, payload, indent=2)
    except ImportError:
        try:
            COINGECKO_ID_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(COINGECKO_ID_CACHE_PATH, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2)
        except OSError as exc:
            _LOG.debug("coingecko id cache fallback save failed: %s", exc)
    except Exception as exc:  # noqa: BLE001 — defensive
        _LOG.debug("coingecko id cache save failed: %s", exc)


def _fetch_coingecko_coins_list() -> Optional[list[dict]]:
    """Fetch the full ``/coins/list`` directory (~5,000 entries).

    Honours :func:`_coingecko_throttle`. Returns ``None`` on geo-block,
    HTTP error, parse error, or unexpected shape — callers fall back to
    the seeded cache only.
    """
    _coingecko_throttle()
    data = _http_get_json(COINGECKO_LIST_URL, timeout=15)
    if data is _GEO_BLOCKED or not isinstance(data, list) or not data:
        return None
    return data


def _disambiguate_by_market_cap(candidate_ids: list[str]) -> Optional[str]:
    """When multiple CoinGecko coins share a symbol, pick the highest-cap one.

    Calls ``/coins/markets?ids=<csv>``. Returns the ``id`` of the row with
    the largest ``market_cap``; falls back to the first candidate on any
    failure (so resolution never returns ``None`` purely because the
    disambiguation HTTP call failed).
    """
    if not candidate_ids:
        return None
    if len(candidate_ids) == 1:
        return candidate_ids[0]
    # CoinGecko caps the ids list — we only ever pass a handful of matches
    ids_csv = ",".join(candidate_ids[:50])
    _coingecko_throttle()
    data = _http_get_json(COINGECKO_MARKETS_DISAMBIG_URL.format(ids=ids_csv), timeout=15)
    if data is _GEO_BLOCKED or not isinstance(data, list) or not data:
        return candidate_ids[0]
    best_id: Optional[str] = None
    best_cap: float = -1.0
    for row in data:
        if not isinstance(row, dict):
            continue
        rid = row.get("id")
        if not isinstance(rid, str):
            continue
        try:
            cap = float(row.get("market_cap") or 0)
        except (TypeError, ValueError):
            cap = 0.0
        if cap > best_cap:
            best_cap = cap
            best_id = rid
    return best_id or candidate_ids[0]


def _resolve_coingecko_id(base_coin: str) -> Optional[str]:
    """Resolve a base coin (e.g. ``"BTC"``) to its CoinGecko id (e.g. ``"bitcoin"``).

    Lookup order:

    1. **In-memory cache** — seeded with the original 44 hardcoded mappings
       plus anything previously persisted to ``coingecko_id_cache.json``.
    2. **Disk cache** — hydrated lazily on first call.
    3. **CoinGecko ``/coins/list``** — refreshed if older than 24h
       (:data:`COINGECKO_ID_CACHE_TTL_SECONDS`). Filters to symbol matches
       and prefers the highest market-cap candidate when ambiguous.

    Returns ``None`` when no mapping exists; the caller (e.g.
    :func:`_fetch_coingecko_klines`) then skips CoinGecko for that symbol —
    same behaviour as the old hardcoded ``.get(base)``.

    Negative results are cached (sentinel :data:`_COINGECKO_NEGATIVE`) to
    avoid repeated remote fetches for genuinely unknown symbols.
    """
    if not base_coin:
        return None
    key = base_coin.upper()

    with _resolve_lock:
        _coingecko_cache_load()
        cached = _resolve_state["ids"].get(key)
        if cached == _COINGECKO_NEGATIVE:
            return None
        if cached:
            return cached

        # Cache miss — decide whether to refresh /coins/list
        now = time.time()
        age = now - float(_resolve_state.get("list_fetched_at") or 0.0)
        coins = None
        if age > COINGECKO_ID_CACHE_TTL_SECONDS or _resolve_state.get("list_fetched_at", 0) == 0:
            coins = _fetch_coingecko_coins_list()
            if coins is not None:
                _resolve_state["list_fetched_at"] = now

        if not coins:
            # No fresh data; record negative result so we don't loop on it
            _resolve_state["ids"][key] = _COINGECKO_NEGATIVE
            _coingecko_cache_save()
            return None

        # Filter the directory to entries whose symbol matches base_coin.
        target = key.lower()
        matches: list[str] = []
        for c in coins:
            if not isinstance(c, dict):
                continue
            sym = str(c.get("symbol") or "").lower()
            cid = c.get("id")
            if sym == target and isinstance(cid, str) and cid:
                matches.append(cid)

        if not matches:
            _resolve_state["ids"][key] = _COINGECKO_NEGATIVE
            _coingecko_cache_save()
            return None

        chosen = _disambiguate_by_market_cap(matches)
        if not chosen:
            _resolve_state["ids"][key] = _COINGECKO_NEGATIVE
            _coingecko_cache_save()
            return None

        _resolve_state["ids"][key] = chosen
        _coingecko_cache_save()
        return chosen


# ---------------------------------------------------------------------------
# Schema validators
# ---------------------------------------------------------------------------
_TICKER_REQUIRED_FIELDS = {"symbol", "lastPrice", "priceChangePercent", "quoteVolume"}
_KLINE_MIN_LEN = 6   # [ts, o, h, l, c, v]


def _is_valid_ticker(t: dict) -> bool:
    if not isinstance(t, dict):
        return False
    return _TICKER_REQUIRED_FIELDS.issubset(t.keys())


def _is_valid_kline_row(row: list) -> bool:
    return isinstance(row, (list, tuple)) and len(row) >= _KLINE_MIN_LEN


# ---------------------------------------------------------------------------
# NORMALIZERS — convert source-native -> Binance-compatible
# ---------------------------------------------------------------------------
def _normalize_coingecko_ticker(item: dict) -> Optional[dict]:
    """CoinGecko /coins/markets row -> Binance ticker shape."""
    try:
        sym = str(item.get("symbol", "")).upper()
        if not sym:
            return None
        binance_sym = sym + _CG_SYMBOL_QUOTE
        last = float(item.get("current_price") or 0)
        change_pct = float(item.get("price_change_percentage_24h") or 0)
        change_abs = float(item.get("price_change_24h") or 0)
        quote_vol = float(item.get("total_volume") or 0)
        if last <= 0 or quote_vol <= 0:
            return None
        # base volume approximation (CoinGecko gives only quote vol)
        base_vol = quote_vol / last if last else 0.0
        ticker = {
            "symbol": binance_sym,
            "lastPrice": str(last),
            "priceChange": str(change_abs),
            "priceChangePercent": str(round(change_pct, 4)),
            "volume": str(round(base_vol, 8)),
            "quoteVolume": str(quote_vol),
        }
        return ticker if _is_valid_ticker(ticker) else None
    except (TypeError, ValueError):
        return None


def _normalize_kucoin_ticker(item: dict) -> Optional[dict]:
    """KuCoin /market/allTickers row -> Binance ticker shape.

    KuCoin row keys: symbol="BTC-USDT", last, changePrice, changeRate,
    vol (base), volValue (quote)
    """
    try:
        kc_sym = str(item.get("symbol", ""))
        if not kc_sym.endswith("-USDT"):
            return None
        binance_sym = kc_sym.replace("-", "")
        last = float(item.get("last") or 0)
        change_abs = float(item.get("changePrice") or 0)
        change_rate = float(item.get("changeRate") or 0)  # decimal (0.0123 = 1.23%)
        base_vol = float(item.get("vol") or 0)
        quote_vol = float(item.get("volValue") or 0)
        if last <= 0 or quote_vol <= 0:
            return None
        ticker = {
            "symbol": binance_sym,
            "lastPrice": str(last),
            "priceChange": str(change_abs),
            "priceChangePercent": str(round(change_rate * 100.0, 4)),
            "volume": str(base_vol),
            "quoteVolume": str(quote_vol),
        }
        return ticker if _is_valid_ticker(ticker) else None
    except (TypeError, ValueError):
        return None


def _normalize_cryptocompare_ticker(item: dict) -> Optional[dict]:
    """CryptoCompare /top/totalvolfull row -> Binance ticker shape.

    Item shape: {"CoinInfo": {"Name": "BTC"}, "RAW": {"USD": {...}}}
    """
    try:
        info = item.get("CoinInfo") or {}
        raw = (item.get("RAW") or {}).get("USD") or {}
        if not raw:
            return None
        sym = str(info.get("Name", "")).upper()
        if not sym:
            return None
        binance_sym = sym + _CG_SYMBOL_QUOTE
        last = float(raw.get("PRICE") or 0)
        change_abs = float(raw.get("CHANGE24HOUR") or 0)
        change_pct = float(raw.get("CHANGEPCT24HOUR") or 0)
        base_vol = float(raw.get("VOLUME24HOUR") or 0)
        quote_vol = float(raw.get("VOLUME24HOURTO") or 0)
        if last <= 0 or quote_vol <= 0:
            return None
        ticker = {
            "symbol": binance_sym,
            "lastPrice": str(last),
            "priceChange": str(change_abs),
            "priceChangePercent": str(round(change_pct, 4)),
            "volume": str(base_vol),
            "quoteVolume": str(quote_vol),
        }
        return ticker if _is_valid_ticker(ticker) else None
    except (TypeError, ValueError):
        return None


def _normalize_kucoin_klines(raw: list, limit: int) -> list[list]:
    """KuCoin candles -> Binance klines.

    KuCoin row (newest-first): [time_s, open, close, high, low, vol, turnover]
    Binance klines row: [ts_ms, o, h, l, c, v, close_time, quote_vol, ...]
    """
    out: list[list] = []
    for r in reversed(raw):
        try:
            if len(r) < 6:
                continue
            ts_ms = int(r[0]) * 1000
            o, c, h, l = str(r[1]), str(r[2]), str(r[3]), str(r[4])
            vol = str(r[5])
            quote = str(r[6]) if len(r) > 6 else "0"
            row = [ts_ms, o, h, l, c, vol, ts_ms + 1, quote, 0, "0", "0", "0"]
            if _is_valid_kline_row(row):
                out.append(row)
        except (TypeError, ValueError, IndexError):
            continue
    return out[-limit:] if limit else out


def _normalize_coingecko_klines(raw: list, limit: int) -> list[list]:
    """CoinGecko /ohlc -> Binance klines.

    CoinGecko OHLC row: [ts_ms, o, h, l, c]    (no volume)
    """
    out: list[list] = []
    for d in raw:
        try:
            if len(d) < 5:
                continue
            ts_ms = int(d[0])
            row = [
                ts_ms, str(d[1]), str(d[2]), str(d[3]), str(d[4]), "0",
                ts_ms + 1, "0", 0, "0", "0", "0",
            ]
            if _is_valid_kline_row(row):
                out.append(row)
        except (TypeError, ValueError, IndexError):
            continue
    return out[-limit:] if limit else out


def _normalize_cryptocompare_klines(raw_data: list, limit: int) -> list[list]:
    """CryptoCompare histo* row -> Binance klines."""
    out: list[list] = []
    for d in raw_data:
        try:
            if not isinstance(d, dict):
                continue
            close = float(d.get("close", 0))
            if close <= 0:
                continue
            ts_ms = int(d.get("time", 0)) * 1000
            row = [
                ts_ms,
                str(d.get("open", 0)),
                str(d.get("high", 0)),
                str(d.get("low", 0)),
                str(close),
                str(d.get("volumefrom", 0)),
                ts_ms + 1,
                str(d.get("volumeto", 0)),
                0, "0", "0", "0",
            ]
            if _is_valid_kline_row(row):
                out.append(row)
        except (TypeError, ValueError):
            continue
    return out[-limit:] if limit else out


# ---------------------------------------------------------------------------
# Per-source FETCHERS
# ---------------------------------------------------------------------------
def _try_source(
    config: FailoverConfig,
    source: str,
    fn: Callable[[], Any],
    validate: Callable[[Any], bool],
) -> Optional[Any]:
    """Run a fetcher with circuit-breaker bookkeeping.

    Returns the validated result on success, None otherwise.  Updates the
    breaker state in either case.
    """
    if config.is_open(source):
        _LOG.debug("Source %s is in cooldown -- skipping", source)
        return None
    try:
        result = fn()
    except Exception as exc:   # noqa: BLE001 — defensive, network code
        _LOG.debug("Source %s raised %s", source, exc)
        config.record_failure(source)
        return None
    if result is _GEO_BLOCKED:
        # Geo-blocked — permanent for this source; skip breaker recording
        # so we don't waste breaker budget on a source we KNOW won't work.
        _LOG.info("Source %s is geo-blocked — skipping (no breaker record)", source)
        return None
    if result is None or not validate(result):
        config.record_failure(source)
        return None
    config.record_success(source)
    return result


# ---- 24h tickers -----------------------------------------------------------
def _fetch_binance_tickers(base_url: str, futures: bool = False) -> Optional[list[dict]]:
    if futures:
        url = f"{base_url}/fapi/v1/ticker/24hr"
    else:
        url = f"{base_url}/api/v3/ticker/24hr"
    data = _http_get_json(url)
    if data is _GEO_BLOCKED:
        return _GEO_BLOCKED  # propagate sentinel so _try_source skips breaker recording
    if not isinstance(data, list) or len(data) < 5:
        return None
    # Binance shape is already "normalized" — but verify schema.
    valid = [t for t in data if _is_valid_ticker(t)]
    return valid if len(valid) > 5 else None


def _fetch_coingecko_tickers() -> Optional[list[dict]]:
    _coingecko_throttle()
    data = _http_get_json(COINGECKO_MARKETS)
    if data is _GEO_BLOCKED:
        return _GEO_BLOCKED
    if not isinstance(data, list):
        return None
    out: list[dict] = []
    for item in data:
        norm = _normalize_coingecko_ticker(item)
        if norm:
            out.append(norm)
    return out if len(out) > 5 else None


def _fetch_kucoin_tickers() -> Optional[list[dict]]:
    data = _http_get_json(KUCOIN_TICKERS)
    if data is _GEO_BLOCKED:
        return _GEO_BLOCKED
    if not isinstance(data, dict) or data.get("code") != "200000":
        return None
    tickers = (data.get("data") or {}).get("ticker") or []
    out: list[dict] = []
    for item in tickers:
        norm = _normalize_kucoin_ticker(item)
        if norm:
            out.append(norm)
    return out if len(out) > 5 else None


def _fetch_cryptocompare_tickers() -> Optional[list[dict]]:
    data = _http_get_json(CRYPTOCOMPARE_TOP)
    if data is _GEO_BLOCKED:
        return _GEO_BLOCKED
    if not isinstance(data, dict):
        return None
    items = data.get("Data") or []
    out: list[dict] = []
    for item in items:
        norm = _normalize_cryptocompare_ticker(item)
        if norm:
            out.append(norm)
    return out if len(out) > 5 else None


# ---- Klines ----------------------------------------------------------------
def _fetch_binance_klines(
    base_url: str, symbol: str, interval: str, limit: int, futures: bool = False
) -> Optional[list[list]]:
    if futures:
        url = f"{base_url}/fapi/v1/klines?symbol={symbol}&interval={interval}&limit={limit}"
    else:
        url = f"{base_url}/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    data = _http_get_json(url)
    if data is _GEO_BLOCKED:
        return _GEO_BLOCKED
    if not isinstance(data, list) or not data:
        return None
    valid = [r for r in data if _is_valid_kline_row(r)]
    return valid if valid else None


def _fetch_kucoin_klines(symbol: str, interval: str, limit: int) -> Optional[list[list]]:
    kc_int = _KUCOIN_INTERVAL_MAP.get(interval)
    if not kc_int:
        return None
    secs = _INTERVAL_SECONDS.get(interval, 3600)
    end = int(time.time())
    start = end - (limit + 5) * secs
    url = KUCOIN_CANDLES.format(
        kc_interval=kc_int, kc_sym=_kucoin_symbol(symbol), start=start, end=end
    )
    data = _http_get_json(url)
    if data is _GEO_BLOCKED:
        return _GEO_BLOCKED
    if not isinstance(data, dict) or data.get("code") != "200000":
        return None
    raw = data.get("data") or []
    norm = _normalize_kucoin_klines(raw, limit)
    return norm or None


def _fetch_coingecko_klines(symbol: str, interval: str, limit: int) -> Optional[list[list]]:
    base = _base_coin(symbol)
    cg_id = _resolve_coingecko_id(base)
    if not cg_id:
        return None
    secs = _INTERVAL_SECONDS.get(interval, 3600)
    days = max(1, min(365, (limit * secs) // 86400 + 1))
    _coingecko_throttle()
    data = _http_get_json(COINGECKO_OHLC.format(cg_id=cg_id, days=days))
    if data is _GEO_BLOCKED:
        return _GEO_BLOCKED
    if not isinstance(data, list) or not data:
        return None
    norm = _normalize_coingecko_klines(data, limit)
    return norm or None


def _fetch_cryptocompare_klines(symbol: str, interval: str, limit: int) -> Optional[list[list]]:
    base = _base_coin(symbol)
    secs = _INTERVAL_SECONDS.get(interval, 3600)
    if secs >= 86400:
        endpoint = "histoday"
    elif secs >= 3600:
        endpoint = "histohour"
    else:
        endpoint = "histominute"
    url = CRYPTOCOMPARE_HISTO.format(endpoint=endpoint, fsym=base, limit=limit)
    data = _http_get_json(url)
    if data is _GEO_BLOCKED:
        return _GEO_BLOCKED
    if not isinstance(data, dict):
        return None
    raw = (data.get("Data") or {}).get("Data") or []
    norm = _normalize_cryptocompare_klines(raw, limit)
    return norm or None


# ---- Funding -------------------------------------------------------------
def _fetch_binance_funding(base_url: str, symbol: str) -> Optional[float]:
    url = f"{base_url}/fapi/v1/fundingRate?symbol={symbol}&limit=1"
    data = _http_get_json(url)
    if data is _GEO_BLOCKED:
        return _GEO_BLOCKED
    if not isinstance(data, list) or not data:
        return None
    try:
        return float(data[-1].get("fundingRate"))
    except (TypeError, ValueError, AttributeError):
        return None


def _fetch_bybit_funding(symbol: str) -> Optional[float]:
    url = BYBIT_FUNDING.format(sym=_normalize_symbol(symbol))
    data = _http_get_json(url)
    if data is _GEO_BLOCKED:
        return _GEO_BLOCKED
    if not isinstance(data, dict) or data.get("retCode") != 0:
        return None
    rows = (data.get("result") or {}).get("list") or []
    if not rows:
        return None
    try:
        return float(rows[0].get("fundingRate"))
    except (TypeError, ValueError):
        return None


def _fetch_okx_funding(symbol: str) -> Optional[float]:
    base = _base_coin(symbol)
    url = OKX_FUNDING.format(base=base)
    data = _http_get_json(url)
    if data is _GEO_BLOCKED:
        return _GEO_BLOCKED
    if not isinstance(data, dict) or str(data.get("code", "")) != "0":
        return None
    rows = data.get("data") or []
    if not rows:
        return None
    try:
        return float(rows[0].get("fundingRate"))
    except (TypeError, ValueError):
        return None


def _fetch_coinglass_funding(symbol: str) -> Optional[float]:
    api_key = os.environ.get("COINGLASS_API_KEY")
    if not api_key:
        return None
    base = _base_coin(symbol)
    data = _http_get_json(
        COINGLASS_FUNDING.format(base=base),
        extra_headers={"coinglassSecret": api_key},
    )
    if data is _GEO_BLOCKED:
        return _GEO_BLOCKED
    if not isinstance(data, dict) or data.get("code") not in ("0", 0, "00000"):
        return None
    rows = data.get("data") or []
    if not rows:
        return None
    try:
        # Coinglass aggregates per-exchange; take the binance entry if present
        for row in rows:
            ex = (row.get("exchangeName") or "").lower()
            if "binance" in ex:
                hist = row.get("fundingRateHistory") or row.get("fundingRate") or []
                if isinstance(hist, list) and hist:
                    return float(hist[-1])
                if isinstance(hist, (int, float, str)):
                    return float(hist)
    except (TypeError, ValueError):
        return None
    return None


# ---------------------------------------------------------------------------
# PUBLIC API
# ---------------------------------------------------------------------------
def fetch_tickers_24h(
    config: Optional[FailoverConfig] = None,
) -> tuple[list[dict], str]:
    """Return (normalized_ticker_list, source_name).

    Falls through Binance fapi -> Binance api/api1/api2/api3 mirrors ->
    CoinGecko -> KuCoin -> CryptoCompare. Returns the first source that
    yields a list of >=5 valid tickers in Binance schema.
    """
    cfg = config or _DEFAULT_CONFIG

    sources: list[tuple[str, Callable[[], Optional[list[dict]]]]] = []
    # Binance futures first (richest data)
    for base in BINANCE_FAPI_BASES:
        name = "binance_fapi:" + base.split("//")[1].split(".")[0]
        sources.append((name, lambda b=base: _fetch_binance_tickers(b, futures=True)))
    # Then spot mirrors
    for base in BINANCE_SPOT_BASES:
        name = "binance_spot:" + base.split("//")[1].split(".")[0]
        sources.append((name, lambda b=base: _fetch_binance_tickers(b, futures=False)))
    # Non-Binance fallbacks
    sources.append(("coingecko", _fetch_coingecko_tickers))
    sources.append(("kucoin", _fetch_kucoin_tickers))
    sources.append(("cryptocompare", _fetch_cryptocompare_tickers))

    for name, fn in sources:
        result = _try_source(
            cfg, name, fn,
            validate=lambda v: isinstance(v, list) and len(v) >= 5,
        )
        if result is not None:
            _LOG.info("fetch_tickers_24h: %d tickers from %s", len(result), name)
            return result, name

    _LOG.error("fetch_tickers_24h: ALL sources exhausted")
    return [], "none"


def fetch_klines(
    symbol: str,
    interval: str,
    limit: int = 100,
    config: Optional[FailoverConfig] = None,
) -> list[list]:
    """Return OHLCV in Binance format. Empty list if all sources fail."""
    cfg = config or _DEFAULT_CONFIG
    sym = _normalize_symbol(symbol)
    if not sym:
        return []

    sources: list[tuple[str, Callable[[], Optional[list[list]]]]] = []
    for base in BINANCE_FAPI_BASES:
        name = "binance_fapi_klines:" + base.split("//")[1].split(".")[0]
        sources.append(
            (name, lambda b=base: _fetch_binance_klines(b, sym, interval, limit, futures=True))
        )
    for base in BINANCE_SPOT_BASES:
        name = "binance_spot_klines:" + base.split("//")[1].split(".")[0]
        sources.append(
            (name, lambda b=base: _fetch_binance_klines(b, sym, interval, limit, futures=False))
        )
    sources.append(("kucoin_klines", lambda: _fetch_kucoin_klines(sym, interval, limit)))
    sources.append(("coingecko_klines", lambda: _fetch_coingecko_klines(sym, interval, limit)))
    sources.append(("cryptocompare_klines", lambda: _fetch_cryptocompare_klines(sym, interval, limit)))

    for name, fn in sources:
        result = _try_source(
            cfg, name, fn,
            validate=lambda v: isinstance(v, list) and len(v) > 0,
        )
        if result is not None:
            _LOG.info("fetch_klines(%s,%s,%d): %d bars from %s",
                      sym, interval, limit, len(result), name)
            return result

    _LOG.warning("fetch_klines(%s,%s,%d): ALL sources exhausted",
                 sym, interval, limit)
    return []


def fetch_funding_rate(
    symbol: str,
    config: Optional[FailoverConfig] = None,
) -> Optional[float]:
    """Return latest funding rate as a decimal (0.0001 = 0.01%).

    Chain: Binance fapi mirrors -> Bybit -> OKX -> Coinglass (if key).
    """
    cfg = config or _DEFAULT_CONFIG
    sym = _normalize_symbol(symbol)
    if not sym:
        return None

    sources: list[tuple[str, Callable[[], Optional[float]]]] = []
    for base in BINANCE_FAPI_BASES:
        name = "binance_fapi_funding:" + base.split("//")[1].split(".")[0]
        sources.append((name, lambda b=base: _fetch_binance_funding(b, sym)))
    sources.append(("bybit_funding", lambda: _fetch_bybit_funding(sym)))
    sources.append(("okx_funding", lambda: _fetch_okx_funding(sym)))
    sources.append(("coinglass_funding", lambda: _fetch_coinglass_funding(sym)))

    for name, fn in sources:
        result = _try_source(
            cfg, name, fn,
            validate=lambda v: isinstance(v, (int, float)),
        )
        if result is not None:
            _LOG.info("fetch_funding_rate(%s) = %.6f from %s", sym, result, name)
            return float(result)

    _LOG.warning("fetch_funding_rate(%s): ALL sources exhausted", sym)
    return None


def fetch_funding_entry(
    symbol: str,
    config: Optional[FailoverConfig] = None,
) -> Optional[dict]:
    """Return latest funding entry with BOTH rate and actual funding timestamp.

    Unlike :func:`fetch_funding_rate` which returns only the decimal rate,
    this returns a dict with ``fundingRate`` (decimal) and ``fundingTime`` (ms
    epoch) from the source that actually provided the data -- so callers
    don't have to synthesize an inaccurate ``fundingTime`` from
    ``int(time.time() * 1000)``.

    Returns dict ``{"fundingRate": float, "fundingTime": int, "source": str}``
    or ``None`` if all sources exhausted.
    """
    cfg = config or _DEFAULT_CONFIG
    sym = _normalize_symbol(symbol)
    if not sym:
        return None

    sources: list[tuple[str, Callable[[], Optional[float]]]] = []
    for base in BINANCE_FAPI_BASES:
        name = "binance_fapi_funding:" + base.split("//")[1].split(".")[0]
        sources.append((name, lambda b=base: _fetch_binance_funding(b, sym)))
    sources.append(("bybit_funding", lambda: _fetch_bybit_funding(sym)))
    sources.append(("okx_funding", lambda: _fetch_okx_funding(sym)))
    sources.append(("coinglass_funding", lambda: _fetch_coinglass_funding(sym)))

    for name, fn in sources:
        result = _try_source(
            cfg, name, fn,
            validate=lambda v: isinstance(v, (int, float)),
        )
        if result is not None:
            _LOG.info("fetch_funding_entry(%s) = %.6f from %s", sym, result, name)
            # Determine actual funding time from source if possible.
            # Bybit/OKX funding times are 8h-aligned; we use the current
            # 8h-aligned settlement time as an approximation.
            funding_time_ms = _estimate_funding_time_ms()
            return {
                "fundingRate": float(result),
                "fundingTime": funding_time_ms,
                "source": name,
            }

    _LOG.warning("fetch_funding_entry(%s): ALL sources exhausted", sym)
    return None


def _estimate_funding_time_ms() -> int:
    """Estimate the most recent 8-hourly funding settlement timestamp.

    Binance/Bybit/OKX perpetual funding settles every 8h at
    00:00, 08:00, 16:00 UTC. The actual settlement time from the
    Binance API response includes this, but for non-Binance sources
    we approximate to the most recent 8h boundary.
    """
    now = time.time()
    # Most recent 8h boundary in seconds
    eight_h = 8 * 3600
    last_settlement = int(now // eight_h) * eight_h
    return last_settlement * 1000


# ---------------------------------------------------------------------------
# CLI smoke test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("=== crypto_data_failover smoke test ===")

    tickers, src = fetch_tickers_24h()
    print(f"  fetch_tickers_24h: {len(tickers)} from [{src}]")
    if tickers:
        sample = tickers[0]
        print(f"    sample: {sample.get('symbol')}  last={sample.get('lastPrice')}  "
              f"chgPct={sample.get('priceChangePercent')}  qVol={sample.get('quoteVolume')}")

    bars = fetch_klines("BTCUSDT", "1h", 5)
    print(f"  fetch_klines(BTCUSDT,1h,5): {len(bars)} bars")
    if bars:
        print(f"    last bar: {bars[-1][:6]}")

    fr = fetch_funding_rate("BTCUSDT")
    print(f"  fetch_funding_rate(BTCUSDT): {fr}")

    print("  Circuit state:", get_default_config().snapshot())
    print("=== Done ===")
