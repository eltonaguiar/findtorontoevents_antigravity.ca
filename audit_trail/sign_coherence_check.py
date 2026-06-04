"""Sign-coherence integrity check for trading_picks + at_pick_outcomes.

Discovered 2026-06-01 by the forward-edge audit: the prior
PRICE_MISMATCH detector regex `'SL_HIT%'` is case-sensitive and missed
80 kimi_signal_tracking rows whose exit_reason was lowercase 'SL hit at $X'.
True corruption was ~5x larger than the prior 170-row estimate.

The decisive new check: **recompute pnl_pct directly from
entry_price/exit_price/direction** and compare against stored pnl_pct.
If sign disagrees, the resolver has corrupted the row — almost always by
writing `status='TP_HIT'` + `pnl_pct=+abs(magnitude)` regardless of
whether the trade actually won or lost.

This module is READ-ONLY by default. It enumerates suspect rows + writes
a report. No DB mutations. A separate purge script (operator-approved)
must apply any fixes.

Usage:
    python3 -m audit_trail.sign_coherence_check                 # full report
    python3 -m audit_trail.sign_coherence_check --source kimi   # filter
    python3 -m audit_trail.sign_coherence_check --json out.json # machine-readable

Exit codes:
    0 — no sign-flips found (clean)
    1 — sign-flips found (operator should review the report)
    2 — DB unreachable / malformed query
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from typing import Any


# Reasonable cap so a large universe doesn't OOM the runner. The audit
# query is selective (only closed picks with non-null entry+exit), so
# 200k is well above the current ~37,884 row total.
MAX_ROWS = 200_000


def _connect():
    import mysql.connector  # local import — keeps module import-light
    return mysql.connector.connect(
        host=os.environ.get("DB_HOST", "mysql.50webs.com"),
        user=os.environ.get("DB_USER", "ejaguiar1_stocks"),
        password=os.environ.get("DB_PASS") or os.environ.get("AUDIT_DB_PASS") or "",  # 2026-06-04 INCIDENT #89 scrub: removed convention literal fallback
        database=os.environ.get("DB_NAME", "ejaguiar1_stocks"),
        connection_timeout=15,
    )


def _expected_pnl_pct(entry: float, exit_: float, direction: str) -> float | None:
    """Recompute pnl_pct from prices + direction. Returns None if inputs missing/zero."""
    if entry is None or exit_ is None:
        return None
    try:
        e = float(entry)
        x = float(exit_)
    except (TypeError, ValueError):
        return None
    if e <= 0:
        return None
    sign = -1.0 if str(direction or "LONG").upper().strip() in ("SHORT", "SELL") else 1.0
    return sign * (x - e) / e * 100.0


def scan(source_filter: str | None = None, max_rows: int = MAX_ROWS) -> dict[str, Any]:
    """Return sign-coherence report. Read-only. No DB writes."""
    conn = _connect()
    cur = conn.cursor()

    where_source = ""
    params: list[Any] = []
    if source_filter:
        where_source = " AND tp.source_system LIKE %s"
        params.append(f"%{source_filter}%")

    cur.execute(
        f"""
        SELECT tp.id, tp.source_system, tp.strategy, tp.symbol, tp.direction,
               tp.entry_price, tp.exit_price, tp.exit_reason,
               apo.status, apo.pnl_pct
        FROM at_pick_outcomes apo
        INNER JOIN trading_picks tp ON apo.pick_id = tp.id
        WHERE tp.entry_price IS NOT NULL
          AND tp.exit_price IS NOT NULL
          AND tp.entry_price > 0
          AND apo.pnl_pct IS NOT NULL
          {where_source}
        LIMIT %s
        """,
        (*params, max_rows),
    )
    rows = cur.fetchall()
    conn.close()

    n_scanned = len(rows)
    flips: list[dict[str, Any]] = []
    by_source: Counter[str] = Counter()
    by_status_misroute: Counter[str] = Counter()
    sl_exit_tp_status: list[dict[str, Any]] = []

    for r in rows:
        (pick_id, source_system, strategy, symbol, direction,
         entry, exit_, exit_reason, status, stored_pnl) = r
        try:
            stored = float(stored_pnl)
        except (TypeError, ValueError):
            continue

        expected = _expected_pnl_pct(entry, exit_, direction)
        if expected is None:
            continue

        # Sign-flip: signs disagree AND magnitude > 0.1% (skip floating noise)
        if abs(expected) > 0.1 and abs(stored) > 0.1 and (expected * stored < 0):
            flip = {
                "pick_id": pick_id,
                "source_system": source_system,
                "strategy": strategy,
                "symbol": symbol,
                "direction": direction,
                "entry": float(entry),
                "exit": float(exit_),
                "exit_reason": exit_reason,
                "status": status,
                "stored_pnl_pct": stored,
                "recomputed_pnl_pct": round(expected, 4),
                "flip_kind": "stored_positive_actual_negative" if stored > 0 else "stored_negative_actual_positive",
            }
            flips.append(flip)
            by_source[source_system or "(null)"] += 1
            by_status_misroute[status or "(null)"] += 1

        # Concurrent secondary detector: exit_reason claims SL but status claims TP.
        # Uses a regex-tolerant string match to catch 'SL_HIT', 'SL hit at $X',
        # 'SL hit', 'stop loss', 'stop_loss', etc.
        er_low = (exit_reason or "").lower()
        if (("sl" in er_low and "hit" in er_low) or "stop" in er_low) and status == "TP_HIT":
            sl_exit_tp_status.append({
                "pick_id": pick_id,
                "source_system": source_system,
                "exit_reason": exit_reason,
                "stored_pnl_pct": stored,
            })

    return {
        "n_scanned": n_scanned,
        "n_sign_flips": len(flips),
        "n_sl_exit_tp_status": len(sl_exit_tp_status),
        "by_source": dict(by_source),
        "by_status_misroute": dict(by_status_misroute),
        "top_offenders": by_source.most_common(10),
        "flip_samples": flips[:20],
        "sl_exit_tp_status_samples": sl_exit_tp_status[:20],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Sign-coherence integrity check")
    parser.add_argument("--source", default=None, help="Filter to source_system substring (e.g. 'kimi')")
    parser.add_argument("--json", default=None, help="Write full report to this JSON path")
    parser.add_argument("--max-rows", type=int, default=MAX_ROWS)
    args = parser.parse_args()

    try:
        report = scan(source_filter=args.source, max_rows=args.max_rows)
    except Exception as e:
        print(f"[ERR] scan failed: {e}", file=sys.stderr)
        return 2

    print(f"Scanned: {report['n_scanned']} rows (closed picks with valid entry+exit+pnl_pct)")
    print(f"Sign-flips found: {report['n_sign_flips']}")
    print(f"SL-exit-with-TP-status: {report['n_sl_exit_tp_status']} (resolver methodology bug)")
    print()
    if report['top_offenders']:
        print("Top offenders by source_system:")
        for src, n in report['top_offenders']:
            print(f"  {n:>5d}  {src}")
        print()
    if report['flip_samples']:
        print(f"Sample flips ({min(len(report['flip_samples']), 5)} of {report['n_sign_flips']}):")
        for f in report['flip_samples'][:5]:
            print(
                f"  {f['source_system']:<30s} {f['symbol']:<12s} {f['direction']:<5s} "
                f"entry={f['entry']:.4g} exit={f['exit']:.4g} "
                f"stored={f['stored_pnl_pct']:+.2f}% recomputed={f['recomputed_pnl_pct']:+.2f}% "
                f"status={f['status']}"
            )

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2, default=str)
        print(f"\nFull report written to {args.json}")

    return 1 if report['n_sign_flips'] > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
