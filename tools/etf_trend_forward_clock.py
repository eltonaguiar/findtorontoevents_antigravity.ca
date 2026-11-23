#!/usr/bin/env python3
"""ETF trend/tactical-allocation FORWARD CLOCK.

Pre-registration: docs/preregistration/ETF_TREND_FORWARD_2026-11-23.md
Row R4b of notes/per-asset-class-plan-copilot-2026-11-23.

WHAT THIS DOES
    At each month-end, computes the FROZEN signal (12-month return over a FROZEN
    20-ETF universe), selects the top 5 with positive momentum, and appends a
    hash-chained record of the DECISION -- before the outcome exists.

WHAT IT DELIBERATELY CANNOT DO
    * It cannot backfill. A record for a date before CLOCK_START is refused unless
      --allow-past is passed WITH --reason, and the reason is written into the
      record. Re-running the rule over history would turn trial count 1 into many
      and inherit the programme's 146-trial deflation debt, which is exactly what
      this design exists to avoid.
    * It cannot be revised. Each record chains to the previous via prev_sha256 and
      carries created_at stamped by this recorder, never by a caller.
    * It does not compute a verdict. Verdicts belong to the checkpoints in §7 of
      the pre-registration, most of which are years away.

Read-only with respect to prices. Writes only its own append-only ledger.

Usage:
    python3 tools/etf_trend_forward_clock.py --stats
    python3 tools/etf_trend_forward_clock.py --dry-run
    python3 tools/etf_trend_forward_clock.py                  # record latest month-end
    python3 tools/etf_trend_forward_clock.py --allow-past --reason "..." --asof 2026-10-31
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "cache" / "asset_class_review"
LEDGER = ROOT / "reports" / "etf_trend_forward" / "positions.jsonl"
GENESIS = "0" * 64

# ---- FROZEN by the pre-registration. Changing either is a NEW trial. ----
UNIVERSE = ["SPY", "QQQ", "IWM", "DIA", "EFA", "EEM", "TLT", "IEF", "SHY", "TIP",
            "TLH", "LQD", "HYG", "JNK", "GLD", "SLV", "XLE", "XLF", "XLK", "XLV"]
TOP_K = 5
LOOKBACK_DAYS = 252
CLOCK_START = "2026-11-23"      # no record may precede this without an explicit reason
HURDLE = 0.0432


def load_closes(sym: str) -> list[tuple[str, float]]:
    """Daily closes from the local cache. Returns [] if unavailable."""
    p = CACHE / f"{sym}_5y.csv"
    if not p.exists():
        return []
    out = []
    import csv
    with open(p, newline="") as fh:
        for r in csv.DictReader(fh):
            try:
                c = float(r["Close"])
            except (KeyError, TypeError, ValueError):
                continue
            if c > 0:
                out.append((str(r["Date"])[:10], c))
    return out


def signal_asof(series: list[tuple[str, float]], asof: str) -> float | None:
    """12-month return ending at `asof`, using only data on or before it."""
    upto = [(d, c) for d, c in series if d <= asof]
    if len(upto) < LOOKBACK_DAYS + 1:
        return None
    last = upto[-1][1]
    base = upto[-(LOOKBACK_DAYS + 1)][1]
    if base <= 0:
        return None
    r = last / base - 1.0
    return r if math.isfinite(r) else None


def last_trading_day_in_data() -> str | None:
    dates = []
    for s in UNIVERSE:
        ser = load_closes(s)
        if ser:
            dates.append(ser[-1][0])
    return max(dates) if dates else None


def read_ledger() -> list[dict]:
    if not LEDGER.exists():
        return []
    out = []
    for line in LEDGER.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def chain_head(records: list[dict]) -> str:
    return records[-1]["sha256"] if records else GENESIS


def canonical(rec: dict) -> str:
    """Hash input: the record WITHOUT its own sha256."""
    body = {k: v for k, v in rec.items() if k != "sha256"}
    return json.dumps(body, sort_keys=True, separators=(",", ":"))


def serialize(rec: dict) -> str:
    """On-disk form: MUST include sha256, or the chain can never be verified.

    Using canonical() here was a real bug -- it strips the hash, so every record
    was written without one and verification was impossible.
    """
    return json.dumps(rec, sort_keys=True, separators=(",", ":"))


def build_record(asof: str, prev: str, reason: str | None) -> dict:
    sig, missing = {}, []
    for s in UNIVERSE:
        ser = load_closes(s)
        v = signal_asof(ser, asof)
        if v is None:
            missing.append(s)
        else:
            sig[s] = v
    ranked = sorted(sig.items(), key=lambda kv: -kv[1])
    held = [s for s, v in ranked if v > 0][:TOP_K]
    cash = [s for s in UNIVERSE if s not in held]

    gross_ann = statistics.mean([sig[s] for s in held]) if held else 0.0
    rec = {
        "kind": "etf_trend_forward_position",
        "preregistration": "docs/preregistration/ETF_TREND_FORWARD_2026-11-23.md",
        "rebalance_date": asof,
        "created_at": datetime.now(timezone.utc).isoformat(),   # recorder-stamped
        "universe": UNIVERSE,
        "top_k": TOP_K,
        "lookback_days": LOOKBACK_DAYS,
        "signals": {k: round(v, 6) for k, v in ranked},
        "held": held,
        "to_cash": cash,
        "no_signal": missing,
        "held_signal_mean": round(gross_ann, 6),
        "hurdle": HURDLE,
        "verdict": "NONE_AT_RECORD_TIME",
        "prev_sha256": prev,
    }
    if reason:
        rec["backfill_reason"] = reason
    rec["sha256"] = hashlib.sha256(canonical(rec).encode()).hexdigest()
    return rec


def stats() -> int:
    recs = read_ledger()
    try:
        shown = LEDGER.relative_to(ROOT)
    except ValueError:          # ledger patched outside the repo (tests)
        shown = LEDGER
    print(f"ledger: {shown}")
    if not recs:
        print("  n_records: 0  (clock not started)")
        print(f"  clock start: {CLOCK_START}")
        return 0
    ok = 0
    prev = GENESIS
    broken = None
    for r in recs:
        if r.get("prev_sha256") != prev:
            broken = r.get("rebalance_date")
            break
        if hashlib.sha256(canonical(r).encode()).hexdigest() != r.get("sha256"):
            broken = r.get("rebalance_date")
            break
        prev = r["sha256"]
        ok += 1
    print(f"  n_records: {len(recs)}  chain_verified: {ok}/{len(recs)}")
    print(f"  chain status: {'INTACT' if not broken else f'BROKEN at {broken}'}")
    first, last = recs[0], recs[-1]
    print(f"  span: {first['rebalance_date']} -> {last['rebalance_date']}")
    print(f"  latest holdings: {', '.join(last['held']) or '(all cash)'}")
    months = len(recs)
    print(f"  months recorded: {months}  "
          f"(earliest CONFIRM needs ~60; verdicts are checkpoint-only)")
    return 0 if not broken else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--asof", default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--stats", action="store_true")
    ap.add_argument("--allow-past", action="store_true")
    ap.add_argument("--reason", default=None)
    a = ap.parse_args()

    if a.stats:
        return stats()

    asof = a.asof or last_trading_day_in_data()
    if not asof:
        print("::error:: no cached price data for the frozen universe")
        return 2

    # ---- enforce no-backfill mechanically ----
    if asof < CLOCK_START and not (a.allow_past and a.reason):
        print(f"::error:: refusing to record {asof} -- it precedes CLOCK_START "
              f"{CLOCK_START}. Backfilling converts trial count 1 into many and "
              f"inherits the 146-trial deflation debt. Use --allow-past --reason "
              f"if this is genuinely intended, and the reason will be recorded.")
        return 3

    recs = read_ledger()
    if any(r.get("rebalance_date") == asof for r in recs):
        print(f"already recorded for {asof} -- refusing to duplicate or revise")
        return 0

    rec = build_record(asof, chain_head(recs), a.reason if a.allow_past else None)
    if len(rec["held"]) == 0:
        print("note: no ETF had positive 12-month momentum -> 100% cash this month")

    if a.dry_run:
        print(json.dumps(rec, indent=2))
        return 0

    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a") as fh:
        fh.write(serialize(rec) + "\n")
    print(f"recorded {asof}: held {', '.join(rec['held']) or '(cash)'}")
    print(f"  prev_sha256 {rec['prev_sha256'][:16]}...  sha256 {rec['sha256'][:16]}...")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
