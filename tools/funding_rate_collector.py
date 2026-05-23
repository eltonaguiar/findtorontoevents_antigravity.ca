#!/usr/bin/env python3
"""Perpetual funding-rate passive-archive collector — OPT-IN RESEARCH SIDECAR.

OPT-IN PASSIVE ARCHIVE feeding hypothesis H-006 (CRYPTO perpetual funding-rate
z-score x basis). This module is run DAILY VIA CRON
(`.github/workflows/funding-rate-collector.yml`) and does nothing but fetch
recent perp funding rates and append them to a per-symbol JSONL archive.

HARD RULE — this is NOT wired into any production pick/score/gate path. It has
no caller in `quality_gates.py`, `dashboard_generator.py`, `production_scanner`,
or any pick-generation / scoring code. It only fetches market data and writes
JSONL files under `data/funding_rate_archive/`. Per the repo Wire-Up Rule it is
an explicit opt-in research sidecar — its sole consumer is the H-006 backtest
in `tools/new_signal_research.py`, which reads the archive offline.

The archive accumulates the dense funding-rate history that free Binance API
calls (capped ~1000 rows) cannot deliver in a single shot — over many daily
runs it builds the longer history H-006 needs to clear `edge_stability_harness`.

API Failover Rule (MANDATORY — NEVER a single Binance endpoint). Per symbol the
chain is tried in order until one source returns usable rows:
  1. Binance USD-M mirrors  fapi -> fapi1 -> fapi2 -> fapi3   /fapi/v1/fundingRate
  2. Bybit v5                /v5/market/funding/history (category=linear)
  3. OKX                     /api/v5/public/funding-rate-history (BASE-USDT-SWAP)

Zero third-party dependencies — stdlib urllib only.

    python tools/funding_rate_collector.py
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARCHIVE_DIR = ROOT / "data" / "funding_rate_archive"

# Windows UTF-8
if sys.platform == "win32":
    for _s in (sys.stdout, sys.stderr):
        if hasattr(_s, "reconfigure"):
            try:
                _s.reconfigure(encoding="utf-8", errors="replace")
            except Exception:  # noqa: BLE001
                pass

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"]
INTERVAL_LIMIT = 200          # funding intervals fetched per call

# Failover chains — NEVER a single Binance endpoint.
BINANCE_FAPI_BASES = [
    "https://fapi.binance.com",
    "https://fapi1.binance.com",
    "https://fapi2.binance.com",
    "https://fapi3.binance.com",
]
BYBIT_BASE = "https://api.bybit.com"
OKX_BASE = "https://www.okx.com"

_UA = {"User-Agent": "funding-rate-collector/1.0 (research-sidecar)"}


# ===========================================================================
# HTTP — stdlib urllib only
# ===========================================================================
def _http_get_json(url: str, timeout: int = 25):
    """GET a URL and parse JSON. Returns parsed object or None on any failure."""
    try:
        req = urllib.request.Request(url, headers=_UA)
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            raw = resp.read().decode("utf-8", "replace")
        return json.loads(raw)
    except (urllib.error.URLError, urllib.error.HTTPError,
            ValueError, TimeoutError, OSError):
        return None


# ===========================================================================
# Per-source fetchers — each returns [(funding_time_ms:int, rate:float), ...]
# ===========================================================================
def _fetch_binance(symbol: str) -> list[tuple[int, float]]:
    """Binance USD-M funding rate via fapi -> fapi1 -> fapi2 -> fapi3 mirrors."""
    for base in BINANCE_FAPI_BASES:
        data = _http_get_json(
            f"{base}/fapi/v1/fundingRate?symbol={symbol}&limit={INTERVAL_LIMIT}")
        if isinstance(data, list) and data:
            out = []
            for row in data:
                try:
                    out.append((int(row["fundingTime"]), float(row["fundingRate"])))
                except (KeyError, TypeError, ValueError):
                    continue
            if out:
                return out
    return []


def _fetch_bybit(symbol: str) -> list[tuple[int, float]]:
    """Bybit v5 linear-perp funding history."""
    data = _http_get_json(
        f"{BYBIT_BASE}/v5/market/funding/history"
        f"?category=linear&symbol={symbol}&limit={INTERVAL_LIMIT}")
    if isinstance(data, dict) and data.get("retCode") == 0:
        out = []
        for row in data.get("result", {}).get("list", []):
            try:
                out.append((int(row["fundingRateTimestamp"]),
                            float(row["fundingRate"])))
            except (KeyError, TypeError, ValueError):
                continue
        if out:
            return out
    return []


def _fetch_okx(symbol: str) -> list[tuple[int, float]]:
    """OKX swap funding-rate history. instId normalized to BASE-USDT-SWAP."""
    base_coin = symbol.replace("USDT", "")
    inst = f"{base_coin}-USDT-SWAP"
    data = _http_get_json(
        f"{OKX_BASE}/api/v5/public/funding-rate-history"
        f"?instId={inst}&limit=100")
    if isinstance(data, dict) and data.get("code") == "0":
        out = []
        for row in data.get("data", []):
            try:
                out.append((int(row["fundingTime"]), float(row["fundingRate"])))
            except (KeyError, TypeError, ValueError):
                continue
        if out:
            return out
    return []


# (label, fetcher) — order IS the failover priority.
_SOURCES = (
    ("binance", _fetch_binance),
    ("bybit", _fetch_bybit),
    ("okx", _fetch_okx),
)


def fetch_funding(symbol: str) -> tuple[str, list[tuple[int, float]]]:
    """Return (source_label, rows) for the first source that yields usable rows."""
    for label, fn in _SOURCES:
        try:
            rows = fn(symbol)
        except Exception:  # noqa: BLE001  — never let one source kill the run
            rows = []
        if rows:
            return label, sorted(rows)
    return "", []


# ===========================================================================
# JSONL archive — idempotent, atomic, corruption-tolerant
# ===========================================================================
def _archive_path(symbol: str) -> Path:
    return ARCHIVE_DIR / f"{symbol}.jsonl"


def load_archive(symbol: str) -> list[dict]:
    """Load existing archive rows. Skips corrupt lines. [] if no file."""
    path = _archive_path(symbol)
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except ValueError:
            continue  # skip corrupt line
        if isinstance(obj, dict) and obj.get("funding_time_ms") is not None:
            out.append(obj)
    return out


def write_archive(symbol: str, rows: list[dict]) -> None:
    """Atomically rewrite the archive: sorted ascending, deduped, .tmp + os.replace."""
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    path = _archive_path(symbol)
    tmp = path.with_suffix(path.suffix + ".tmp")
    body = "\n".join(json.dumps(r, separators=(",", ":")) for r in rows)
    tmp.write_text(body + ("\n" if body else ""), encoding="utf-8")
    os.replace(tmp, path)


def merge_rows(existing: list[dict], symbol: str, source: str,
               fetched: list[tuple[int, float]]) -> tuple[list[dict], int]:
    """Merge fetched rows into existing archive. Dedupe on funding_time_ms.

    Returns (merged_sorted_rows, rows_added).
    """
    by_ts: dict[int, dict] = {}
    for r in existing:
        try:
            by_ts[int(r["funding_time_ms"])] = r
        except (KeyError, TypeError, ValueError):
            continue
    before = len(by_ts)
    for ts, rate in fetched:
        if ts in by_ts:
            continue  # idempotent — never duplicate an interval
        by_ts[ts] = {
            "symbol": symbol,
            "funding_time_ms": ts,
            "funding_rate": rate,
            "source": source,
        }
    merged = [by_ts[k] for k in sorted(by_ts)]
    return merged, len(by_ts) - before


def _span(rows: list[dict]) -> str:
    """Human ISO-date span of an archive."""
    ts = [int(r["funding_time_ms"]) for r in rows if r.get("funding_time_ms")]
    if not ts:
        return "(empty)"
    lo = datetime.fromtimestamp(min(ts) / 1000, timezone.utc).date().isoformat()
    hi = datetime.fromtimestamp(max(ts) / 1000, timezone.utc).date().isoformat()
    return f"{lo} .. {hi}"


# ===========================================================================
# main
# ===========================================================================
def collect() -> int:
    """Fetch + archive every symbol. Returns count of symbols that succeeded."""
    ok = 0
    total_added = 0
    print(f"# funding-rate collector — {datetime.now(timezone.utc).isoformat(timespec='seconds')}")
    print(f"# archive dir: {ARCHIVE_DIR}")
    for sym in SYMBOLS:
        source, fetched = fetch_funding(sym)
        if not fetched:
            print(f"  {sym:<9} FAIL  — all sources (binance/bybit/okx) returned no rows")
            continue
        existing = load_archive(sym)
        merged, added = merge_rows(existing, sym, source, fetched)
        write_archive(sym, merged)
        total_added += added
        ok += 1
        print(f"  {sym:<9} OK    source={source:<8} "
              f"+{added:<4} rows  total={len(merged):<6} span={_span(merged)}")
        time.sleep(0.4)  # gentle on the public endpoints
    print(f"# done — {ok}/{len(SYMBOLS)} symbols succeeded, "
          f"{total_added} new funding intervals archived")
    return ok


def main() -> int:
    ok = collect()
    # Exit non-zero ONLY if every symbol failed all sources.
    return 0 if ok > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
