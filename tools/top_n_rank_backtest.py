#!/usr/bin/env python3
"""Top-N Rank Backtest — answers "If I bought the top-10 ranked picks T days
ago, would I have been profitable?" for US Equity + Swing Plays.

Method (hindsight replay, not forward backtest):
  1. Pull EQUITY closed picks from trading_picks WHERE status IS terminal.
  2. Bucket by created_at day.
  3. Per day: rank picks by `score` DESC, take top-N (default 10).
  4. Mean pnl_pct across the top-N = the "would I have been profitable" answer
     for that day.
  5. Aggregate by window: today (T=0), yesterday (T=1), week (T=1-7),
     month (T=1-30), all-time (the full closed-pick history available).

Output JSON sidecar at audit_dashboard/data/top_n_rank_backtest.json.

NFA — this is hindsight performance of the existing `score` field as a
ranker. It does NOT prove forward edge. Use alongside DSR + walk-forward.

Usage:
  python tools/top_n_rank_backtest.py                           # default n=10
  python tools/top_n_rank_backtest.py --n 5 --asset-class ETF
  python tools/top_n_rank_backtest.py --dry-run                 # stdout only
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone, date, timedelta
from pathlib import Path
from collections import defaultdict

pymysql = None
try:
    import pymysql
except ImportError:
    pymysql = None

ROOT = Path(__file__).resolve().parent.parent

TERMINAL_STATUSES = ("WON", "LOST", "WIN", "LOSS", "TP_HIT", "SL_HIT", "EXPIRED",
                     "closed_win", "closed_loss")


def _write_graceful_payload(out_arg: str, asset_class: str, n: int, lookback_days: int, error: str) -> None:
    """Always emit a valid, current-timestamped JSON even on DB/import/compute errors.
    Prevents the workflow placeholder writer from creating generated_at:null.
    """
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "asset_class": asset_class,
        "top_n": n,
        "lookback_days": lookback_days,
        "error": error,
        "windows": {},
        "per_day_detail": {},
        "_note": "Non-fatal: DB unavailable, pymysql missing, or no qualifying closed picks this cycle. Dashboard shows last known good or empty state.",
    }
    out_path = ROOT / out_arg if not str(out_arg).startswith(("/", ".")) else Path(out_arg)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(f"# wrote graceful payload ({out_path.stat().st_size} bytes) — {error[:80]}", file=sys.stderr)


def connect():
    return pymysql.connect(
        host=os.environ.get("DB_STOCKS_HOST", "mysql.50webs.com"),
        user=os.environ.get("DB_STOCKS_USER", "ejaguiar1_stocks"),
        password=os.environ.get("DB_STOCKS_PASSWORD", "stocks"),
        database=os.environ.get("DB_STOCKS_NAME", "ejaguiar1_stocks"),
        port=int(os.environ.get("DB_STOCKS_PORT", "3306")),
        connect_timeout=30,
        read_timeout=120,
    )


def fetch_picks(cur, asset_class: str, lookback_days: int):
    """Pull closed picks of the given asset_class with score, created_at, pnl_pct."""
    placeholders = ",".join(["%s"] * len(TERMINAL_STATUSES))
    sql = f"""
        SELECT id, strategy, symbol, direction, score, pnl_pct,
               created_at, closed_at, status
        FROM trading_picks
        WHERE asset_class = %s
          AND status IN ({placeholders})
          AND created_at >= NOW() - INTERVAL %s DAY
          AND pnl_pct IS NOT NULL
          AND score IS NOT NULL
        ORDER BY created_at DESC
    """
    params = (asset_class,) + TERMINAL_STATUSES + (lookback_days,)
    cur.execute(sql, params)
    return cur.fetchall()


def bucket_by_day(rows):
    """Return dict[date] -> list[row]."""
    buckets = defaultdict(list)
    for r in rows:
        created = r.get("created_at")
        if isinstance(created, datetime):
            d = created.date()
        elif isinstance(created, str):
            try:
                d = datetime.fromisoformat(created.replace("Z", "+00:00")).date()
            except Exception:
                continue
        else:
            continue
        buckets[d].append(r)
    return buckets


def topn_stats(picks, n: int):
    """Rank by score DESC, take top-N, compute summary."""
    if not picks:
        return None
    ranked = sorted(picks, key=lambda r: float(r.get("score") or 0), reverse=True)[:n]
    pnls = [float(r.get("pnl_pct") or 0) for r in ranked]
    if not pnls:
        return None
    wins = sum(1 for p in pnls if p > 0)
    losses = sum(1 for p in pnls if p < 0)
    mean_pnl = sum(pnls) / len(pnls)
    cum_pnl = sum(pnls)
    wr = (wins * 100.0 / len(pnls)) if pnls else 0.0
    # Simple profit factor
    gross_win = sum(p for p in pnls if p > 0) or 0.0
    gross_loss = abs(sum(p for p in pnls if p < 0)) or 0.0
    pf = (gross_win / gross_loss) if gross_loss > 0 else (float('inf') if gross_win > 0 else 0.0)
    return {
        "n_picked": len(ranked),
        "n_wins": wins,
        "n_losses": losses,
        "wr_pct": round(wr, 2),
        "mean_pnl_pct": round(mean_pnl, 3),
        "cum_pnl_pct": round(cum_pnl, 3),
        "profit_factor": round(pf, 3) if pf != float('inf') else None,
        "picks": [
            {
                "symbol": r.get("symbol"),
                "strategy": r.get("strategy"),
                "direction": r.get("direction"),
                "score": float(r.get("score") or 0),
                "pnl_pct": float(r.get("pnl_pct") or 0),
                "status": r.get("status"),
                "id": str(r.get("id") or "")[:80],
            }
            for r in ranked
        ],
    }


def aggregate_window(buckets, n: int, day_predicate):
    """Aggregate top-N across days matching the predicate."""
    days = [d for d in buckets.keys() if day_predicate(d)]
    if not days:
        return {"days": 0, "n_total_picks": 0}
    per_day_pnls = []
    n_total_picks = 0
    n_total_wins = 0
    for d in days:
        s = topn_stats(buckets[d], n)
        if not s:
            continue
        per_day_pnls.append(s["mean_pnl_pct"])
        n_total_picks += s["n_picked"]
        n_total_wins += s["n_wins"]
    if not per_day_pnls:
        return {"days": len(days), "n_total_picks": 0}
    mean_of_days = sum(per_day_pnls) / len(per_day_pnls)
    cum_pnl = sum(per_day_pnls)
    wr = (n_total_wins * 100.0 / n_total_picks) if n_total_picks else 0.0
    return {
        "days": len(per_day_pnls),
        "n_total_picks": n_total_picks,
        "mean_daily_pnl_pct": round(mean_of_days, 3),
        "cum_pnl_pct_if_held_daily_topn": round(cum_pnl, 3),
        "wr_pct_across_topn_picks": round(wr, 2),
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--n", type=int, default=10, help="Top-N picks per day (default 10)")
    p.add_argument("--asset-class", default="EQUITY",
                   help="Asset class to backtest (default EQUITY; also try ETF, COMMODITY)")
    p.add_argument("--lookback-days", type=int, default=90,
                   help="DB lookback window (default 90d)")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--out", default="audit_dashboard/data/top_n_rank_backtest.json")
    args = p.parse_args()

    print(f"# Top-N Rank Backtest — {args.asset_class} top-{args.n} per day, lookback {args.lookback_days}d",
          file=sys.stderr)

    if pymysql is None:
        _write_graceful_payload(args.out, args.asset_class, args.n, args.lookback_days,
                                "pymysql not importable in this environment")
        if args.dry_run:
            print(json.dumps({"error": "pymysql missing", "_note": "graceful"}, indent=2))
        return

    try:
        conn = connect()
    except Exception as e:
        print(f"DB connect failed: {e}", file=sys.stderr)
        _write_graceful_payload(args.out, args.asset_class, args.n, args.lookback_days,
                                f"DB connect failed: {e}")
        return

    cur = conn.cursor(pymysql.cursors.DictCursor)
    rows = fetch_picks(cur, args.asset_class, args.lookback_days)
    cur.close()
    conn.close()
    print(f"# rows={len(rows)}", file=sys.stderr)

    buckets = bucket_by_day(rows)
    print(f"# days_with_picks={len(buckets)}", file=sys.stderr)

    try:
        today = date.today()
        yesterday = today - timedelta(days=1)
        day_before = today - timedelta(days=2)
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)

        windows = {
            "today": aggregate_window(buckets, args.n, lambda d: d == today),
            "yesterday": aggregate_window(buckets, args.n, lambda d: d == yesterday),
            "day_before_yesterday": aggregate_window(buckets, args.n, lambda d: d == day_before),
            "last_7d": aggregate_window(buckets, args.n, lambda d: d >= week_ago),
            "last_30d": aggregate_window(buckets, args.n, lambda d: d >= month_ago),
            "all_lookback": aggregate_window(buckets, args.n, lambda d: True),
        }

        # Single-day detail for today / yesterday / day_before (which symbols)
        detail = {}
        for label, d in [("today", today), ("yesterday", yesterday),
                         ("day_before_yesterday", day_before)]:
            s = topn_stats(buckets.get(d, []), args.n)
            if s:
                detail[label] = {"date": d.isoformat(), **s}
            else:
                detail[label] = {"date": d.isoformat(), "n_picked": 0,
                                 "note": "no closed picks created on this day"}

        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "asset_class": args.asset_class,
            "top_n": args.n,
            "lookback_days": args.lookback_days,
            "method": "hindsight replay: rank each day's closed picks by score, "
                      "take top-N, measure mean realized pnl_pct. Answers 'if I "
                      "bought top-N T days ago by score, would I have been "
                      "profitable?' on REALIZED outcomes only.",
            "windows": windows,
            "per_day_detail": detail,
            "nfa": "NFA — hindsight replay of the score field as a ranker. Does "
                   "NOT prove forward edge. Use alongside DSR + walk-forward.",
        }

        if args.dry_run:
            print(json.dumps(payload, indent=2, default=str))
            return

        out_path = ROOT / args.out
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        size = out_path.stat().st_size
        print(f"# wrote {out_path} ({size:,} bytes)", file=sys.stderr)
        # Highlight key answers to stderr for cron log readability
        for label in ("today", "yesterday", "day_before_yesterday", "last_7d", "last_30d"):
            w = windows.get(label, {})
            if w.get("n_total_picks"):
                print(f"#   {label}: days={w['days']} picks={w['n_total_picks']} "
                      f"mean_daily_pnl={w.get('mean_daily_pnl_pct')}% "
                      f"cum_pnl={w.get('cum_pnl_pct_if_held_daily_topn')}% "
                      f"wr={w.get('wr_pct_across_topn_picks')}%",
                      file=sys.stderr)
            else:
                print(f"#   {label}: no picks", file=sys.stderr)
    except Exception as e:
        print(f"# computation error after connect: {e}", file=sys.stderr)
        _write_graceful_payload(args.out, args.asset_class, args.n, args.lookback_days,
                                f"post-connect error: {e}")
        return


if __name__ == "__main__":
    main()
