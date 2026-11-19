#!/usr/bin/env python3
"""pilot_forward_bridge — resolve paper-pilot CLOSE rows into forward observations.

The paper pilots under verified_strategies/paper_pilot/ accrue closed trades in
their own paper_log.jsonl files, but nothing moved those closes into
reports/forward_observations.jsonl — so their pods' forward clocks sat at zero
(POD-FABER-TAA n_forward=0 while the faber pilot had real closes). This bridge
is the missing adapter, and it refuses to invent evidence:

* Every emitted row is re-resolved from real bars (yfinance daily bars for
  ETF/EQUITY, the tools.crypto_bars failover chain for CRYPTO) through
  alpha_engine.intrabar_resolver.stamp_pick — a row that cannot be resolved
  intrabar-honestly is reported UNRESOLVED and skipped, never emitted.
* benchmark_leg_ret is computed from a matched benchmark leg (SPY for
  ETF/EQUITY, BTCUSDT for CRYPTO) over the same window, via the same
  forward_observations_ingest.benchmark_leg helper the DB ingest uses.
* Appending goes through alpha_engine.forward_observations.append, which
  validates the row shape against the ledger contract and skips duplicates,
  so re-running the bridge is idempotent.

Usage::

    python3 tools/pilot_forward_bridge.py              # dry run
    python3 tools/pilot_forward_bridge.py --apply      # append to the ledger
    python3 tools/pilot_forward_bridge.py --bars bars.json --apply  # offline bars
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from alpha_engine import forward_observations as FO  # noqa: E402
from alpha_engine.forward_observations_ingest import (  # noqa: E402
    benchmark_leg, gross_pct, row_id, side_of, slippage_bps,
)
from alpha_engine.intrabar_resolver import stamp_pick  # noqa: E402

PILOT_DIR = REPO / "verified_strategies" / "paper_pilot"

#: pilot log -> forward pod. A log row may carry its own hypothesis_id (the
#: crypto intraday sim does); the mapping here is the fallback for pilots that
#: predate the forward ledger. Strategy ids are asserted so a foreign row in a
#: shared log can never leak into the wrong pod.
SOURCES: list[dict] = [
    {
        "log": PILOT_DIR / "etf_dual_momentum_paper_log.jsonl",
        "strategies": {"etf_verified_dual_momentum"},
        "hypothesis_id": "H-2026-11-19-06",
        "asset_class": "ETF",
        "benchmark": "SPY",
    },
    {
        "log": PILOT_DIR / "faber_taa_paper_log.jsonl",
        "strategies": {"faber_taa_paper_pilot", "faber_taa"},
        "hypothesis_id": "H-2026-11-19-03",
        "asset_class": "ETF",
        "benchmark": "SPY",
    },
    {
        "log": PILOT_DIR / "crypto_intraday_sim_paper_log.jsonl",
        "strategies": None,  # rows carry their own hypothesis_id
        "hypothesis_id": None,
        "asset_class": "CRYPTO",
        "benchmark": "BTCUSDT",
    },
]

#: Pods are registered on 2026-11-19; rows closed before any registration date
#: can never promote, so the bridge does not bother emitting them.
MIN_CLOSED_DATE = "2026-11-19"


def _iso_from_date(value: str | None) -> str | None:
    """Pilot logs store dates (YYYY-MM-DD) or full ISO timestamps; normalise."""
    v = str(value or "").strip()
    if not v:
        return None
    if len(v) == 10:
        return f"{v}T00:00:00+00:00"
    parsed = FO._parse(v)
    return parsed.isoformat() if parsed else None


def _ms(iso: str | None) -> int | None:
    parsed = FO._parse(iso)
    return int(parsed.timestamp() * 1000) if parsed else None


def _yf_daily_bars(symbol: str, start_ms: int, end_ms: int) -> list[dict]:
    import yfinance as yf

    start = datetime.fromtimestamp(start_ms / 1000, tz=timezone.utc)
    end = datetime.fromtimestamp(end_ms / 1000, tz=timezone.utc)
    px = yf.download(
        symbol,
        start=start.strftime("%Y-%m-%d"),
        end=None,  # through today; the window filter below trims
        progress=False,
        auto_adjust=True,
    )
    if px is None or px.empty:
        return []
    if hasattr(px.columns, "nlevels") and px.columns.nlevels > 1:
        px.columns = px.columns.get_level_values(0)
    bars = []
    for ts, row in px.iterrows():
        t_ms = int(ts.timestamp() * 1000)
        if t_ms > end_ms + 86_400_000:
            continue
        try:
            bars.append({
                "timestamp": t_ms,
                "open": float(row["Open"]), "high": float(row["High"]),
                "low": float(row["Low"]), "close": float(row["Close"]),
            })
        except (KeyError, TypeError, ValueError):
            continue
    return bars


def _fetch_bars(asset_class: str, symbol: str,
                start_ms: int, end_ms: int) -> list[dict]:
    if asset_class.upper() == "CRYPTO":
        from tools.crypto_bars import fetch_klines

        return fetch_klines(symbol, "4h", start_ms, end_ms)
    return _yf_daily_bars(symbol, start_ms, end_ms)


def _close_rows(log_path: Path) -> list[dict]:
    if not log_path.exists():
        return []
    rows = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except ValueError:
            continue
        if isinstance(obj, dict) and obj.get("event") == "CLOSE":
            rows.append(obj)
    return rows


def build_rows(bars_map: dict[str, list[dict]] | None = None,
               now: datetime | None = None) -> tuple[list[dict], list[tuple]]:
    """(emitted_rows, unresolved) across every configured pilot log.

    bars_map: optional {"<CLASS>:<SYMBOL>": bars} override; when a key is
    missing the bridge fetches from the real APIs. Tests pass a full map so no
    network is touched.
    """
    created = (now or datetime.now(timezone.utc)).isoformat()
    emitted: list[dict] = []
    unresolved: list[tuple] = []
    bench_cache: dict[str, list[dict]] = {}

    for src in SOURCES:
        for row in _close_rows(src["log"]):
            strategy = str(row.get("strategy") or "")
            hid = str(row.get("hypothesis_id") or src["hypothesis_id"] or "")
            if src["strategies"] is not None and strategy not in src["strategies"]:
                unresolved.append((strategy, "strategy not claimed by this pod"))
                continue
            if not hid:
                unresolved.append((strategy, "no hypothesis_id"))
                continue
            ac = str(row.get("asset_class") or src["asset_class"]).upper()
            symbol = str(row.get("symbol") or "").upper()
            side = side_of(row) or "LONG"
            opened_at = _iso_from_date(row.get("entry_ts") or row.get("entry_date"))
            closed_at = _iso_from_date(
                row.get("exit_ts") or row.get("exit_date") or row.get("date"))
            entry_px = float(row.get("entry_price") or 0)
            if not (symbol and opened_at and closed_at and entry_px > 0):
                unresolved.append((symbol or strategy, "incomplete CLOSE row"))
                continue
            if str(closed_at)[:10] < MIN_CLOSED_DATE:
                continue
            o_ms, c_ms = _ms(opened_at), _ms(closed_at)
            if o_ms is None or c_ms is None or c_ms <= o_ms:
                unresolved.append((symbol, "bad timestamps"))
                continue

            key = f"{ac}:{symbol}"
            bars = (bars_map or {}).get(key)
            if bars is None:
                bars = _fetch_bars(ac, symbol, o_ms, c_ms)
            window = [b for b in bars
                      if o_ms <= int(b.get("timestamp") or 0) <= c_ms + 86_400_000]
            if not window:
                unresolved.append((symbol, "no bars for window"))
                continue

            pick = {
                "direction": side,
                "entry_price": entry_px,
                "stop_loss": row.get("stop_loss"),
                "take_profit": row.get("take_profit"),
            }
            stamped = stamp_pick(pick, window)
            if not stamped.get("intrabar_first_touch"):
                unresolved.append((symbol, "could not resolve a first touch"))
                continue
            exit_px = float(stamped.get("resolved_price") or 0)
            if exit_px <= 0:
                unresolved.append((symbol, "resolver produced no exit price"))
                continue

            bkey = f"{ac}:{src['benchmark']}"
            if bkey not in bench_cache:
                b_bars = (bars_map or {}).get(bkey)
                if b_bars is None:
                    b_bars = _fetch_bars(ac, src["benchmark"], o_ms, c_ms)
                bench_cache[bkey] = b_bars
            bench_ret = benchmark_leg(bench_cache[bkey], o_ms, c_ms, side)

            pilot_exit = float(row.get("exit_price") or 0)
            mismatch = (abs(gross_pct(entry_px, exit_px, side)
                            - gross_pct(entry_px, pilot_exit, side))
                        if pilot_exit > 0 else None)
            emitted.append({
                "id": row_id(hid, symbol, side, opened_at),
                "hypothesis_id": hid,
                "opened_at": opened_at,
                "closed_at": closed_at,
                "symbol": symbol,
                "asset_class": ac,
                "side": side,
                "entry_px": entry_px,
                "exit_px": exit_px,
                "qty": 1.0,
                "fees": 0.0,
                "funding": 0.0,
                "slippage_bps": slippage_bps(ac),
                "resolver_version": stamped.get("resolver_version"),
                "intrabar_first_touch": True,
                "benchmark_leg_ret": bench_ret,
                "regime_ok": True,
                "created_at": created,
                "pilot_exit_px": pilot_exit or None,
                "gross_mismatch_pp": round(mismatch, 4) if mismatch is not None else None,
                "pilot_strategy": strategy,
            })
    return emitted, unresolved


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true",
                    help="append admissible rows to the forward ledger")
    ap.add_argument("--bars", help="optional JSON map '<CLASS>:<SYMBOL>' -> bars "
                                   "(skips all network fetches)")
    ap.add_argument("--json", action="store_true", help="machine-readable summary")
    args = ap.parse_args(argv)

    bars_map = None
    if args.bars:
        bars_map = json.loads(Path(args.bars).read_text(encoding="utf-8"))
    rows, unresolved = build_rows(bars_map)
    summary: dict = {"resolved": len(rows), "unresolved": len(unresolved)}
    if args.apply and rows:
        summary["write"] = FO.append(rows)
    if args.json:
        print(json.dumps(summary, indent=2, default=str))
    else:
        print(f"resolved={len(rows)} unresolved={len(unresolved)}")
        for sym, why in unresolved:
            print(f"  UNRESOLVED {sym}: {why}")
        if args.apply and rows:
            w = summary["write"]
            print(f"appended {w['added']} (duplicates={w['duplicates']}, "
                  f"rejected={len(w.get('rejected') or [])})")
        elif rows:
            print("dry-run: pass --apply to append")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
