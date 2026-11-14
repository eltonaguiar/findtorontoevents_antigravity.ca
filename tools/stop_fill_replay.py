#!/usr/bin/env python3
"""Replay SL_HIT rows against real intrabar candles and score three fill models.

This measures the algorithm fix from idea #1 instead of asserting it. For each
stopped pick it fetches 1h candles from the pick's entry timestamp and asks:

  1. Was the declared stop ever touched inside the max-hold window?
  2. If yes, would a RESTING stop have filled at the stop, or gapped through it?
  3. How does that compare with the exit price the ledger recorded?

Three PnL models per trade:
    recorded   what the ledger says happened (whatever the exit writer did)
    at_stop    fill exactly at the declared stop (optimistic ceiling)
    gap_aware  fill at the stop, or at the bar open when the bar gapped through
               (the model implemented in audit_trail/stop_fill.py)

The gap_aware number is the honest one; at_stop is an upper bound. A pick whose
stop was never touched is reported separately: it cannot be a stop-out at all,
regardless of what ``exit_reason`` says.

Usage:
    python3 tools/stop_fill_replay.py --payload /tmp/peercheck/dashboard_payload.json \
        --source kimi_riseoftheclaw --limit 40
    python3 tools/stop_fill_replay.py --payload X --class CRYPTO --limit 80 --json out.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from audit_trail.stop_fill import find_stop_fill  # noqa: E402

_HOSTS = ("api.binance.com", "data-api.binance.vision", "api1.binance.com")
_STOP_REASONS = {"SL_HIT", "STOP_LOSS", "SL", "LOST"}


def _f(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        out = float(v)
    except (TypeError, ValueError):
        return None
    return out if out == out else None


def _parse_ms(ts: Any) -> Optional[int]:
    if not ts:
        return None
    s = str(ts).strip()
    try:
        iso = (s[:-1] + "+00:00") if s.endswith("Z") else s
        dt = datetime.fromisoformat(iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp() * 1000)
    except (ValueError, TypeError):
        return None


_FIAT = {"USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "NZD"}


def normalize_symbol(sym: Any) -> str:
    """Map a ledger symbol to a Binance spot pair.

    Trackers write ``ETH-USD`` / ``BTC/USDT`` / ``SOL_USD``; Binance wants
    ``ETHUSDT``. The first replay run returned no_candles for all 30 rows purely
    because of this — worth remembering: a data-shaped null is usually a join
    bug, not a market fact.
    """
    s = str(sym or "").strip().upper().replace("/", "").replace("_", "")
    if not s or s.endswith("=X") or s.endswith("=F"):
        return s
    s = s.replace("-", "")
    if s.endswith("USD") and not s.endswith(("USDT", "BUSD")):
        s += "T"
    return s


def fetch_bars_yfinance(symbol: str, entry_ms: int, days: int = 5) -> Optional[List[Dict[str, Any]]]:
    """1h bars for a non-crypto symbol (equity/ETF), from the entry day onward.

    Binance only covers crypto: running the crypto fetcher over EQUITY rows
    returns no_candles for every row, which looks like a finding and is not.
    """
    try:
        import yfinance as yf
    except ImportError:
        return None
    dt = datetime.fromtimestamp(entry_ms / 1000, tz=timezone.utc)
    try:
        hist = yf.Ticker(symbol).history(
            start=(dt - timedelta(days=1)).date(),
            end=(dt + timedelta(days=days)).date(),
            interval="1h",
            auto_adjust=False,
        )
    except Exception:
        return None
    if hist is None or hist.empty:
        return None
    bars: List[Dict[str, Any]] = []
    for idx, row in hist.iterrows():
        try:
            bdt = idx.to_pydatetime()
            if bdt.tzinfo is None:
                bdt = bdt.replace(tzinfo=timezone.utc)
            bars.append({
                "timestamp": int(bdt.timestamp() * 1000),
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
            })
        except (TypeError, ValueError, KeyError):
            continue
    return bars or None


def fetch_bars(symbol: str, start_ms: int, limit: int = 48) -> Optional[List[Dict[str, Any]]]:
    """1h candles from start_ms. None = symbol not available on any host."""
    for host in _HOSTS:
        url = (
            f"https://{host}/api/v3/klines?symbol={symbol}"
            f"&interval=1h&startTime={start_ms}&limit={limit}"
        )
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "StopFillReplay/1.0"})
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code in (400, 451):
                return None  # bad symbol / geo-block on this host — try next? no: same everywhere
            continue
        except Exception:
            continue
        if not isinstance(data, list) or not data:
            return None
        return [
            {
                "timestamp": int(k[0]),
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
            }
            for k in data
            if len(k) >= 5
        ]
    return None


def pnl_at(entry: float, price: float, direction: str) -> float:
    mult = -1.0 if str(direction).upper() == "SHORT" else 1.0
    return (price - entry) / entry * 100.0 * mult


def replay_one(row: Dict[str, Any]) -> Dict[str, Any]:
    entry = _f(row.get("entry_price"))
    stop = _f(row.get("stop_loss"))
    recorded = _f(row.get("pnl_pct"))
    direction = str(row.get("direction") or "LONG").upper()
    out = {
        "symbol": row.get("symbol"),
        "direction": direction,
        "entry": entry,
        "stop": stop,
        "recorded_pnl": recorded,
        "status": None,
        "at_stop_pnl": None,
        "gap_aware_pnl": None,
        "gapped": None,
    }
    ms = _parse_ms(row.get("timestamp"))
    if not entry or not stop or ms is None or not row.get("symbol"):
        out["status"] = "unmeasurable"
        return out

    sym = normalize_symbol(row.get("symbol"))
    out["symbol_norm"] = sym
    crypto = bool(sym) and sym.endswith("USDT")
    if not crypto:
        # equity / ETF / non-USDT pair -> daily-side provider. A crypto-only
        # fetcher silently returns no_candles for every one of these rows.
        out["provider"] = "yfinance"
        bars = fetch_bars_yfinance(str(row.get("symbol")), ms)
    else:
        out["provider"] = "binance"
        bars = fetch_bars(sym, ms)
    if bars is None:
        out["status"] = "no_candles"
        return out
    if not bars:
        out["status"] = "no_candles"
        return out

    hit = find_stop_fill(direction, stop, bars)
    out["at_stop_pnl"] = round(pnl_at(entry, stop, direction), 4)
    if hit is None:
        out["status"] = "stop_never_touched"
        return out
    out["status"] = "touched"
    out["gapped"] = hit["basis"] == "gap_through"
    out["gap_aware_pnl"] = round(pnl_at(entry, hit["price"], direction), 4)
    return out


def summarize(results: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    def agg(rows, key):
        vals = [r[key] for r in rows if r.get(key) is not None]
        if not vals:
            return None
        return round(sum(vals) / len(vals), 4)

    measured = [r for r in results if r.get("status") in ("touched", "stop_never_touched")]
    touched = [r for r in results if r.get("status") == "touched"]
    never = [r for r in results if r.get("status") == "stop_never_touched"]
    statuses = defaultdict(int)
    for r in results:
        statuses[r.get("status") or "unknown"] += 1

    def block(rows):
        return {
            "n": len(rows),
            "recorded_sum": round(sum(r["recorded_pnl"] for r in rows if r.get("recorded_pnl") is not None), 2),
            "at_stop_sum": round(sum(r["at_stop_pnl"] for r in rows if r.get("at_stop_pnl") is not None), 2),
            "gap_aware_sum": round(sum(r["gap_aware_pnl"] for r in rows if r.get("gap_aware_pnl") is not None), 2),
            "mean_recorded": agg(rows, "recorded_pnl"),
            "mean_at_stop": agg(rows, "at_stop_pnl"),
            "mean_gap_aware": agg(rows, "gap_aware_pnl"),
        }

    return {
        "n_requested": len(results),
        "status_counts": dict(statuses),
        "touched": block(touched),
        "never_touched": block(never),
        "gapped_count": sum(1 for r in touched if r.get("gapped")),
        "gap_rate_pct": round(100 * sum(1 for r in touched if r.get("gapped")) / len(touched), 1) if touched else None,
        "measured_n": len(measured),
    }


def load_rows(path: str) -> List[Dict[str, Any]]:
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, dict):
        picks = data.get("picks")
        if isinstance(picks, dict) and isinstance(picks.get("recent_closed"), list):
            return [r for r in picks["recent_closed"] if isinstance(r, dict)]
        for k in ("recent_closed", "closed_picks"):
            if isinstance(data.get(k), list):
                return [r for r in data[k] if isinstance(r, dict)]
    if isinstance(data, list):
        return [r for r in data if isinstance(r, dict)]
    return []


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--payload", required=True)
    ap.add_argument("--class", dest="cls", default="CRYPTO")
    ap.add_argument("--source", help="restrict to one source_system")
    ap.add_argument("--limit", type=int, default=40)
    ap.add_argument("--json", help="write full results here")
    args = ap.parse_args(argv)

    rows = [
        r for r in load_rows(args.payload)
        if str(r.get("asset_class", "")).upper() == args.cls.upper()
        and str(r.get("exit_reason", "")).upper() in _STOP_REASONS
        and (not args.source or str(r.get("source_system")) == args.source)
    ]
    if not rows:
        print("no matching stopped rows", file=sys.stderr)
        return 2
    # Deterministic sample: evenly spaced across the filtered set.
    step = max(1, len(rows) // args.limit)
    sample = rows[::step][: args.limit]
    print(f"{len(rows)} stopped {args.cls} rows"
          f"{f' from {args.source}' if args.source else ''}; replaying {len(sample)}")
    print(f"window: 48 x 1h candles from each pick's entry timestamp\n")

    results = []
    for i, row in enumerate(sample, 1):
        res = replay_one(row)
        results.append(res)
        if i % 10 == 0 or i == len(sample):
            print(f"  {i}/{len(sample)} …", flush=True)
        time.sleep(0.12)  # be polite to the public REST endpoint

    s = summarize(results)
    print("\n=== status ===")
    for k, v in s["status_counts"].items():
        print(f"  {k:<20} {v}")
    print(f"\nstop touched: {s['touched']['n']}   never touched: {s['never_touched']['n']}")
    print(f"gap-through rate among touched: {s['gap_rate_pct']}% ({s['gapped_count']} trades)\n")

    print("=== PnL by fill model (percentage points, sum over the replayed sample) ===")
    print(f"{'model':<12}{'n':>6}{'sum_pp':>12}{'mean_pp':>12}")
    for name, key_sum, key_mean in (
        ("recorded", "recorded_sum", "mean_recorded"),
        ("at_stop", "at_stop_sum", "mean_at_stop"),
        ("gap_aware", "gap_aware_sum", "mean_gap_aware"),
    ):
        b = s["touched"]
        print(f"{name:<12}{b['n']:>6}{b[ key_sum ]:>12.2f}{b[ key_mean ] if b[ key_mean ] is not None else 0:>12.4f}")
    print("\nat_stop is an upper bound; gap_aware is the model now implemented in the resolver.")
    print("A stop that was never touched cannot be a stop-out: those rows are mislabelled.")

    if args.json:
        p = Path(args.json)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            json.dump({"summary": s, "results": results}, fh, indent=2, sort_keys=True)
        print(f"\nwrote {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
