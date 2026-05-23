#!/usr/bin/env python3
"""Backtest Edge #10 — CRYPTO UTC-hour seasonal filter.

Hypothesis (from memory project_clean_data_symbol_wr):
  22 UTC entry = 61.2% WR (peak)
  08-09 UTC entry = sub-30% (death zone)

Validates against actual alpha_engine/data/closed_picks.json. Produces
per-hour WR + PF + sample size for all CRYPTO picks.

Free statistical edge — no API keys needed.

Usage:
  python tools/backtest_btc_utc_hour_filter.py
  python tools/backtest_btc_utc_hour_filter.py --asset-class CRYPTO --min-n 100
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLOSED_PATH = ROOT / "alpha_engine" / "data" / "closed_picks.json"
TERMINAL_STATUSES = ("WON", "LOST", "WIN", "LOSS", "TP_HIT", "SL_HIT",
                     "EXPIRED", "closed_win", "closed_loss")


def _parse_ts(s) -> datetime | None:
    if not s:
        return None
    try:
        if isinstance(s, (int, float)):
            return datetime.fromtimestamp(float(s), tz=timezone.utc)
        ts = str(s).replace("Z", "+00:00").replace(" ", "T", 1)
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError, OSError):
        return None


def _is_terminal(status: str) -> bool:
    return str(status or "").upper().strip() in (s.upper() for s in TERMINAL_STATUSES)


def _is_crypto(p: dict) -> bool:
    ac = str(p.get("asset_class") or p.get("category") or "").upper()
    if ac in ("CRYPTO", "MEME"):
        return True
    sym = str(p.get("symbol") or "").upper()
    return any(sym.endswith(s) for s in ("USDT", "USDC", "BUSD"))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--asset-class", default="CRYPTO",
                   choices=["CRYPTO", "ALL"], help="Class filter (default CRYPTO)")
    p.add_argument("--min-n", type=int, default=50,
                   help="Skip hours with n<min-n (default 50)")
    p.add_argument("--out", default="audit_dashboard/data/btc_utc_hour_backtest.json")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    if not CLOSED_PATH.exists():
        print(f"ERROR: {CLOSED_PATH} not found", file=sys.stderr)
        sys.exit(1)

    print(f"# loading {CLOSED_PATH}", file=sys.stderr)
    picks = json.loads(CLOSED_PATH.read_text(encoding="utf-8"))
    print(f"# total picks: {len(picks)}", file=sys.stderr)

    # Per-hour bins: 0..23
    by_hour: dict[int, dict] = {
        h: {"wins": 0, "losses": 0, "zero": 0, "win_pnl": 0.0, "loss_pnl": 0.0}
        for h in range(24)
    }

    n_filtered = 0
    n_no_ts = 0
    for pick in picks:
        if not _is_terminal(pick.get("status")):
            continue
        if args.asset_class == "CRYPTO" and not _is_crypto(pick):
            continue
        # Try multiple time fields; schema varies between resolver outputs
        ts = (pick.get("entry_time") or pick.get("opened_at")
              or pick.get("created_at") or pick.get("entry_date")
              or pick.get("timestamp") or pick.get("signal_time"))
        dt = _parse_ts(ts)
        if dt is None:
            n_no_ts += 1
            continue
        hr = dt.hour
        try:
            pnl = float(pick.get("pnl_pct") or 0)
        except (TypeError, ValueError):
            continue
        b = by_hour[hr]
        if pnl > 0.01:
            b["wins"] += 1
            b["win_pnl"] += pnl
        elif pnl < -0.01:
            b["losses"] += 1
            b["loss_pnl"] += abs(pnl)
        else:
            b["zero"] += 1
        n_filtered += 1

    print(f"# filtered: n={n_filtered} (no_ts={n_no_ts})", file=sys.stderr)

    results = []
    for hr in range(24):
        b = by_hour[hr]
        n = b["wins"] + b["losses"]
        if n < args.min_n:
            results.append({
                "hour_utc": hr, "n": n,
                "status": "INSUFFICIENT_SAMPLE",
                "wr_pct": None, "pf": None, "avg_pnl_pct": None,
            })
            continue
        wr = b["wins"] / n * 100
        pf = (b["win_pnl"] / b["loss_pnl"]) if b["loss_pnl"] > 0 else None
        total_pnl = b["win_pnl"] - b["loss_pnl"]
        avg = total_pnl / n if n else 0
        # Classify
        if wr >= 55:
            classification = "GOLDEN_HOUR"
        elif wr <= 35:
            classification = "DEATH_ZONE"
        elif wr >= 50:
            classification = "ABOVE_COIN_FLIP"
        else:
            classification = "BELOW_COIN_FLIP"
        results.append({
            "hour_utc": hr,
            "n": n,
            "wins": b["wins"],
            "losses": b["losses"],
            "wr_pct": round(wr, 2),
            "pf": round(pf, 3) if pf is not None else None,
            "avg_pnl_pct": round(avg, 3),
            "total_pnl_pct": round(total_pnl, 2),
            "classification": classification,
        })

    # Sorted hot/cold
    valid = [r for r in results if r["wr_pct"] is not None]
    hot = sorted(valid, key=lambda r: r["wr_pct"], reverse=True)[:5]
    cold = sorted(valid, key=lambda r: r["wr_pct"])[:5]

    # Apply NS-C filter (skip hours 8-9) — what does class WR become?
    ns_c_skipped = [r for r in results if r["hour_utc"] in (8, 9) and r["wr_pct"]]
    ns_c_kept = [r for r in results if r["hour_utc"] not in (8, 9) and r["wr_pct"]]
    kept_total_wins = sum(r["wins"] for r in ns_c_kept if r.get("wins"))
    kept_total_n = sum(r["n"] for r in ns_c_kept if r.get("n"))
    kept_wr = (kept_total_wins / kept_total_n * 100) if kept_total_n else 0
    raw_total_wins = sum(r["wins"] for r in valid)
    raw_total_n = sum(r["n"] for r in valid)
    raw_wr = (raw_total_wins / raw_total_n * 100) if raw_total_n else 0

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "spec": "Edge #10 backtest — CRYPTO UTC-hour filter validation",
        "asset_class_filter": args.asset_class,
        "min_n_per_hour": args.min_n,
        "n_resolved_picks": n_filtered,
        "n_dropped_no_ts": n_no_ts,
        "per_hour": results,
        "top_5_hottest": hot,
        "bottom_5_coldest": cold,
        "ns_c_filter_effect": {
            "raw_class_wr_pct": round(raw_wr, 2),
            "post_filter_wr_pct": round(kept_wr, 2),
            "wr_lift_pp": round(kept_wr - raw_wr, 2),
            "n_skipped": sum(r["n"] for r in ns_c_skipped),
            "n_kept": kept_total_n,
            "skipped_hours_wr": [r for r in ns_c_skipped],
        },
        "memory_claim": {
            "22_utc": "61.2% WR per project_clean_data_symbol_wr memory",
            "08_09_utc": "sub-30% WR per same memory",
        },
        "nfa": "Backtest from live closed_picks.json (hindsight). No real-money sizing.",
    }

    if args.dry_run:
        print(json.dumps(payload, indent=2, default=str))
        return

    out_path = ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(f"# wrote {out_path} ({out_path.stat().st_size:,} bytes)",
          file=sys.stderr)
    print(f"# raw class WR: {raw_wr:.2f}% (n={raw_total_n})", file=sys.stderr)
    print(f"# post-filter WR: {kept_wr:.2f}% (n={kept_total_n}) "
          f"= {kept_wr-raw_wr:+.2f}pp lift", file=sys.stderr)
    print(f"# TOP 5 HOTTEST:", file=sys.stderr)
    for r in hot:
        print(f"#   {r['hour_utc']:>2}UTC  n={r['n']:>4}  WR={r['wr_pct']:>5.1f}%  "
              f"PF={r['pf']}  [{r['classification']}]", file=sys.stderr)
    print(f"# BOTTOM 5 COLDEST:", file=sys.stderr)
    for r in cold:
        print(f"#   {r['hour_utc']:>2}UTC  n={r['n']:>4}  WR={r['wr_pct']:>5.1f}%  "
              f"PF={r['pf']}  [{r['classification']}]", file=sys.stderr)


if __name__ == "__main__":
    main()
