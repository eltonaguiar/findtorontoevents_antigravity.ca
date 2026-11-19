#!/usr/bin/env python3
"""crypto_bars — OHLCV klines with the repo's mandatory API failover chain.

Per AGENTS.md "API Failover Rule": never a single Binance endpoint. Chain:
Binance mirrors (api, api1, api2, api3) -> KuCoin -> CryptoCompare.
(CoinGecko is skipped for *klines* specifically: its /ohlc endpoint needs a
symbol->coin-id mapping and serves fixed granularities, so it cannot honour an
arbitrary interval/window request without resampling, which would fabricate
bar boundaries. The chain above still has 6 endpoints across 3 providers.)

Returns bars as dicts {"timestamp": epoch_ms, "open", "high", "low", "close",
"volume"}, oldest first — the exact shape alpha_engine.intrabar_resolver and
forward_observations_ingest helpers consume.
"""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request

BINANCE_MIRRORS = (
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
)

_INTERVAL_SECONDS = {
    "1m": 60, "5m": 300, "15m": 900, "30m": 1800,
    "1h": 3600, "4h": 14400, "1d": 86400,
}
_KUCOIN_INTERVAL = {
    "1m": "1min", "5m": "5min", "15m": "15min", "30m": "30min",
    "1h": "1hour", "4h": "4hour", "1d": "1day",
}


def _get_json(url: str, timeout: float = 10.0):
    req = urllib.request.Request(url, headers={"User-Agent": "fte-crypto-bars/1"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _from_binance(base: str, symbol: str, interval: str,
                  start_ms: int, end_ms: int, limit: int) -> list[dict]:
    qs = urllib.parse.urlencode({
        "symbol": symbol.upper(), "interval": interval,
        "startTime": start_ms, "endTime": end_ms, "limit": limit,
    })
    raw = _get_json(f"{base}/api/v3/klines?{qs}")
    return [{
        "timestamp": int(k[0]), "open": float(k[1]), "high": float(k[2]),
        "low": float(k[3]), "close": float(k[4]), "volume": float(k[5]),
    } for k in raw]


def _from_kucoin(symbol: str, interval: str,
                 start_ms: int, end_ms: int) -> list[dict]:
    # KuCoin wants BTC-USDT and unix seconds; returns newest-first.
    sym = symbol.upper().replace("USDT", "-USDT").replace("--", "-")
    qs = urllib.parse.urlencode({
        "symbol": sym, "type": _KUCOIN_INTERVAL[interval],
        "startAt": start_ms // 1000, "endAt": end_ms // 1000,
    })
    raw = _get_json(f"https://api.kucoin.com/api/v1/market/candles?{qs}")
    out = [{
        "timestamp": int(k[0]) * 1000, "open": float(k[1]), "close": float(k[2]),
        "high": float(k[3]), "low": float(k[4]), "volume": float(k[5]),
    } for k in (raw.get("data") or [])]
    return sorted(out, key=lambda b: b["timestamp"])


def _from_cryptocompare(symbol: str, interval: str,
                        start_ms: int, end_ms: int) -> list[dict]:
    fsym = symbol.upper().replace("USDT", "")
    step = _INTERVAL_SECONDS[interval]
    if interval == "1d":
        endpoint, aggregate = "histoday", 1
    elif step >= 3600:
        endpoint, aggregate = "histohour", step // 3600
    else:
        endpoint, aggregate = "histominute", step // 60
    limit = min(2000, max(1, (end_ms - start_ms) // (step * 1000) + 1))
    qs = urllib.parse.urlencode({
        "fsym": fsym, "tsym": "USDT", "limit": limit,
        "aggregate": aggregate, "toTs": end_ms // 1000,
    })
    raw = _get_json(f"https://min-api.cryptocompare.com/data/v2/{endpoint}?{qs}")
    data = ((raw.get("Data") or {}).get("Data")) or []
    out = [{
        "timestamp": int(k["time"]) * 1000, "open": float(k["open"]),
        "high": float(k["high"]), "low": float(k["low"]),
        "close": float(k["close"]), "volume": float(k.get("volumefrom") or 0),
    } for k in data if float(k.get("close") or 0) > 0]
    return [b for b in out if start_ms <= b["timestamp"] <= end_ms]


def fetch_klines(symbol: str, interval: str, start_ms: int, end_ms: int,
                 limit: int = 1000) -> list[dict]:
    """OHLCV bars for ``symbol`` over [start_ms, end_ms], oldest first.

    Tries every endpoint in the failover chain; returns [] only when the whole
    chain fails (callers must treat [] as "no evidence", never as flat price).
    """
    if interval not in _INTERVAL_SECONDS:
        raise ValueError(f"unsupported interval {interval!r}")
    errors: list[str] = []
    for base in BINANCE_MIRRORS:
        try:
            bars = _from_binance(base, symbol, interval, start_ms, end_ms, limit)
            if bars:
                return bars
        except Exception as exc:  # noqa: BLE001 — each mirror may fail independently
            errors.append(f"{base}: {exc}")
        time.sleep(0.2)
    for fn in (_from_kucoin, _from_cryptocompare):
        try:
            bars = fn(symbol, interval, start_ms, end_ms)
            if bars:
                return bars
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{fn.__name__}: {exc}")
        time.sleep(0.2)
    if errors:
        print(f"crypto_bars: all endpoints failed for {symbol}: {errors[-3:]}")
    return []
