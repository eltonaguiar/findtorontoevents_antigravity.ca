#!/usr/bin/env python3
"""§3 Multi-exchange smart routing stub (Mercury / HEDGE_FUND plan).

Fetches **public** best bid/ask from **Binance, Kraken, Bybit, OKX** (no API keys),
applies configurable **taker fee** assumptions, and ranks venues by:

  * **effective_buy** = ask × (1 + fee)   — lower is better for taker buy
  * **effective_sell** = bid × (1 − fee) — higher is better for taker sell

Also records raw spread_pct per venue and **cross-venue** min-ask vs max-bid (rough
arbitrage dispersion proxy — not executable without transfer latency).

Symbols: unique ``*USDT`` spot pairs from dashboard **active** picks (same normalisation
as ``liquidity_score_stub``).

Output: ``tools/data/multi_exchange_router_report.json``

Usage:
  python tools/multi_exchange_router_stub.py
  python tools/multi_exchange_router_stub.py --max-symbols 8 --redis-alert
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPO = Path(__file__).resolve().parent.parent
DEFAULT_DASHBOARD = REPO / "audit_dashboard" / "data" / "dashboard_data.json"
OUT_JSON = REPO / "tools" / "data" / "multi_exchange_router_report.json"

# Default **taker** fee assumptions (spot, retail tier — tune from each exchange’s schedule).
DEFAULT_FEES = {
    "binance": 0.001,
    "kraken": 0.0026,
    "bybit": 0.001,
    "okx": 0.0008,
}

# Kraken REST pair names differ for some bases (see https://docs.kraken.com/rest/)
KRAKEN_PAIR_OVERRIDES = {
    "BTCUSDT": "XBTUSDT",
}

UA = "findtorontoevents-multi-exchange-router/1.0 (+https://findtorontoevents.ca)"


def _norm(sym: str) -> str:
    if not sym:
        return ""
    s = str(sym).upper().replace("-", "").replace("/", "")
    if s.endswith("USD") and not s.endswith("USDT"):
        s = s + "T"
    return s


def load_usdt_symbols(path: Path, cap: int) -> List[str]:
    with open(path, "r", encoding="utf-8") as f:
        doc = json.load(f)
    picks = (doc.get("picks") or {}).get("active") or []
    if not isinstance(picks, list):
        return []
    seen = set()
    out: List[str] = []
    for p in picks:
        if not isinstance(p, dict):
            continue
        s = _norm(p.get("symbol") or "")
        if not s.endswith("USDT") or len(s) < 6:
            continue
        if s in seen:
            continue
        seen.add(s)
        out.append(s)
        if len(out) >= cap:
            break
    return out


def _get(url: str, timeout: float = 12.0) -> Optional[Any]:
    req = Request(url, headers={"User-Agent": UA})
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return json.loads(raw)
    except (HTTPError, URLError, ValueError, OSError):
        return None


def okx_inst_id(usdt_sym: str) -> str:
    return usdt_sym.replace("USDT", "-USDT")


def kraken_pair(usdt_sym: str) -> str:
    if usdt_sym in KRAKEN_PAIR_OVERRIDES:
        return KRAKEN_PAIR_OVERRIDES[usdt_sym]
    return usdt_sym


def parse_binance(doc: Any) -> Optional[Tuple[float, float]]:
    if not isinstance(doc, dict):
        return None
    try:
        bid = float(doc.get("bidPrice") or doc.get("bid") or 0)
        ask = float(doc.get("askPrice") or doc.get("ask") or 0)
        if bid <= 0 or ask <= 0:
            return None
        return bid, ask
    except (TypeError, ValueError):
        return None


def parse_kraken(doc: Any) -> Optional[Tuple[float, float]]:
    if not isinstance(doc, dict):
        return None
    err = doc.get("error")
    if err and len(err) > 0:
        return None
    res = doc.get("result")
    if not isinstance(res, dict) or not res:
        return None
    first = next(iter(res.values()))
    if not isinstance(first, dict):
        return None
    try:
        b = first.get("b")
        a = first.get("a")
        bid = float(b[0]) if b else 0.0
        ask = float(a[0]) if a else 0.0
        if bid <= 0 or ask <= 0:
            return None
        return bid, ask
    except (TypeError, ValueError, IndexError):
        return None


def parse_bybit(doc: Any) -> Optional[Tuple[float, float]]:
    if not isinstance(doc, dict):
        return None
    if doc.get("retCode") not in (0, "0", None):
        return None
    result = doc.get("result") or {}
    lst = result.get("list")
    if not isinstance(lst, list) or not lst:
        return None
    row = lst[0]
    if not isinstance(row, dict):
        return None
    try:
        bid = float(row.get("bid1Price") or row.get("bidPrice") or 0)
        ask = float(row.get("ask1Price") or row.get("askPrice") or 0)
        if bid <= 0 or ask <= 0:
            return None
        return bid, ask
    except (TypeError, ValueError):
        return None


def parse_okx(doc: Any) -> Optional[Tuple[float, float]]:
    if not isinstance(doc, dict):
        return None
    if doc.get("code") not in ("0", 0, None):
        return None
    data = doc.get("data")
    if not isinstance(data, list) or not data:
        return None
    row = data[0]
    if not isinstance(row, dict):
        return None
    try:
        bid = float(row.get("bidPx") or 0)
        ask = float(row.get("askPx") or 0)
        if bid <= 0 or ask <= 0:
            return None
        return bid, ask
    except (TypeError, ValueError):
        return None


def venue_row(
    name: str,
    fee: float,
    bid: float,
    ask: float,
) -> Dict[str, Any]:
    mid = (bid + ask) / 2.0
    spread_pct = ((ask - bid) / mid * 100.0) if mid > 0 else 0.0
    eff_buy = ask * (1.0 + fee)
    eff_sell = bid * (1.0 - fee)
    return {
        "venue": name,
        "taker_fee_assumed": fee,
        "bid": round(bid, 8),
        "ask": round(ask, 8),
        "spread_pct": round(spread_pct, 6),
        "effective_buy": round(eff_buy, 8),
        "effective_sell": round(eff_sell, 8),
    }


def fetch_symbol_all(
    sym: str, fees: Dict[str, float]
) -> Dict[str, Any]:
    """Parallel HTTP fetches for one USDT symbol."""
    kpair = kraken_pair(sym)
    inst = okx_inst_id(sym)
    urls = {
        "binance": (
            "binance",
            "https://api.binance.com/api/v3/ticker/bookTicker?symbol=%s" % sym,
            parse_binance,
        ),
        "kraken": (
            "kraken",
            "https://api.kraken.com/0/public/Ticker?pair=%s" % kpair,
            parse_kraken,
        ),
        "bybit": (
            "bybit",
            "https://api.bybit.com/v5/market/tickers?category=spot&symbol=%s" % sym,
            parse_bybit,
        ),
        "okx": (
            "okx",
            "https://www.okx.com/api/v5/market/ticker?instId=%s" % inst,
            parse_okx,
        ),
    }

    def one(key: str) -> Optional[Dict[str, Any]]:
        vname, url, parser = urls[key]
        doc = _get(url)
        parsed = parser(doc) if doc is not None else None
        if parsed is None:
            return None
        bid, ask = parsed
        return venue_row(vname, fees.get(vname, 0.001), bid, ask)

    rows: List[Dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(one, k): k for k in urls}
        for fut in as_completed(futs):
            try:
                r = fut.result()
                if r:
                    rows.append(r)
            except Exception:
                pass

    if not rows:
        return {
            "symbol": sym,
            "venues": [],
            "best_buy_venue": None,
            "best_sell_venue": None,
            "cross_venue_dispersion_pct": None,
            "error": "no_venue_quotes",
        }

    best_buy = min(rows, key=lambda x: x["effective_buy"])
    best_sell = max(rows, key=lambda x: x["effective_sell"])
    asks = [x["ask"] for x in rows]
    bids = [x["bid"] for x in rows]
    disp = None
    if asks and bids:
        lo_ask = min(asks)
        hi_bid = max(bids)
        mid = (lo_ask + hi_bid) / 2.0
        if mid > 0:
            disp = round((lo_ask - hi_bid) / mid * 100.0, 6)

    return {
        "symbol": sym,
        "venues": sorted(rows, key=lambda x: x["effective_buy"]),
        "best_buy_venue": best_buy["venue"],
        "best_buy_effective": best_buy["effective_buy"],
        "best_sell_venue": best_sell["venue"],
        "best_sell_effective": best_sell["effective_sell"],
        "cross_venue_dispersion_pct": disp,
        "cross_venue_note": (
            "max_bid_exceeds_min_ask_across_venues (arb hint only; not net of transfer/latency)"
            if disp is not None and disp < 0
            else None
        ),
    }


def redis_broadcast(msg: str) -> None:
    bus = Path(r"C:\Users\zerou\redis-bus\agent_bus.py")
    if not bus.is_file():
        return
    try:
        subprocess.run(
            [sys.executable, str(bus), "broadcast", "cursor-composer", msg],
            check=False,
            timeout=20,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.SubprocessError):
        pass


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--dashboard", type=str, default=str(DEFAULT_DASHBOARD))
    ap.add_argument("--out", type=str, default=str(OUT_JSON))
    ap.add_argument("--max-symbols", type=int, default=12)
    ap.add_argument("--pause-ms", type=int, default=80, help="delay between symbols")
    ap.add_argument("--redis-alert", action="store_true")
    args = ap.parse_args()

    path = Path(args.dashboard)
    if not path.is_file():
        print("ERROR: dashboard not found: %s" % path, file=sys.stderr)
        return 1

    syms = load_usdt_symbols(path, args.max_symbols)
    if not syms:
        print("ERROR: no USDT symbols from active picks", file=sys.stderr)
        return 1

    fees = dict(DEFAULT_FEES)
    per_symbol: List[Dict[str, Any]] = []
    for i, sym in enumerate(syms):
        per_symbol.append(fetch_symbol_all(sym, fees))
        if i + 1 < len(syms) and args.pause_ms > 0:
            time.sleep(args.pause_ms / 1000.0)

    ok = sum(1 for x in per_symbol if x.get("venues"))
    report: Dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_dashboard": str(path).replace("\\", "/"),
        "config": {
            "max_symbols": args.max_symbols,
            "taker_fees_assumed": fees,
        },
        "summary": {
            "symbols_requested": len(syms),
            "symbols_with_quotes": ok,
        },
        "symbols": per_symbol,
        "disclaimer": "Public tickers only; fees are assumptions; latency, depth, and withdrawal risk not modeled.",
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print("symbols=%d with_quotes=%d -> %s" % (len(syms), ok, out_path))

    if args.redis_alert:
        redis_broadcast(
            "HEDGE_PLAN §3 multi-exchange router stub: %d/%d symbols quoted -> %s"
            % (ok, len(syms), str(out_path).replace("\\", "/"))
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
