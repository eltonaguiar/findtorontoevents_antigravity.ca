"""
Pick What-If Query CLI (Kimi R2 PR-05).

Answers: "If gate X had NOT filtered pick Y, what would have happened?"

Uses:
  - audit_trail/audit_trail.db  (filter_event_log + pick_lifecycle_log)
  - alpha_engine/data/closed_picks.json  (historical analog outcomes)

Usage:
  python tools/pick_whatif_query.py --gate asset_strategy_pairs
  python tools/pick_whatif_query.py --pick-id <uuid>
  python tools/pick_whatif_query.py --gate symbol_blocklist --asset-class CRYPTO --limit 20
  python tools/pick_whatif_query.py --list-gates
  python tools/pick_whatif_query.py --summary

Analog matching: picks with the same (symbol, strategy) in closed_picks.json.
PnL projection is based on historical analog mean ± std (not simulation).
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean, stdev
from typing import Optional

_REPO = Path(__file__).resolve().parent.parent
_DB = _REPO / "audit_trail" / "audit_trail.db"
_CLOSED_PICKS = _REPO / "alpha_engine" / "data" / "closed_picks.json"


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _load_closed_picks() -> dict[tuple[str, str], list[dict]]:
    """Return closed picks indexed by (symbol, strategy)."""
    if not _CLOSED_PICKS.exists():
        return {}
    picks = json.loads(_CLOSED_PICKS.read_text())
    idx: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for p in picks:
        sym = p.get("symbol") or ""
        strat = p.get("strategy") or ""
        if sym and strat:
            idx[(sym, strat)].append(p)
    return dict(idx)


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(str(_DB))
    c.row_factory = sqlite3.Row
    return c


# ---------------------------------------------------------------------------
# Analog projection
# ---------------------------------------------------------------------------

def _analog_stats(analogs: list[dict]) -> dict:
    """Summarise analog PnL outcomes."""
    pnls = [p["pnl_pct"] for p in analogs if p.get("pnl_pct") is not None]
    if not pnls:
        return {"n": 0, "mean_pnl": None, "stdev_pnl": None, "win_rate": None}
    wins = [x for x in pnls if x > 0]
    return {
        "n": len(pnls),
        "mean_pnl": round(mean(pnls) * 100, 3),  # as %
        "stdev_pnl": round(stdev(pnls) * 100, 3) if len(pnls) > 1 else 0.0,
        "win_rate": round(len(wins) / len(pnls) * 100, 1),
    }


def _verdict(stats: dict) -> str:
    if stats["n"] == 0:
        return "NO_ANALOG"
    m = stats["mean_pnl"]
    wr = stats["win_rate"]
    if m is None:
        return "NO_ANALOG"
    if m > 0 and wr >= 50:
        return "LIKELY_PROFITABLE"
    if m < 0 or wr < 40:
        return "LIKELY_LOSS"
    return "MARGINAL"


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

def _fetch_filtered_picks(
    conn: sqlite3.Connection,
    gate: Optional[str] = None,
    pick_id: Optional[str] = None,
    asset_class: Optional[str] = None,
    limit: int = 50,
) -> list[sqlite3.Row]:
    where_clauses = ["1=1"]
    params: list = []

    if pick_id:
        where_clauses.append("f.pick_id = ?")
        params.append(pick_id)
    if gate:
        where_clauses.append("f.gate_name = ?")
        params.append(gate)
    if asset_class:
        where_clauses.append("p.asset_class = ?")
        params.append(asset_class)

    sql = f"""
        SELECT f.filter_event_id, f.pick_id, f.gate_name, f.filter_reason,
               f.filter_timestamp,
               p.symbol, p.asset_class, p.strategy, p.source_system,
               p.direction, p.confidence, p.entry_price
        FROM filter_event_log f
        JOIN pick_lifecycle_log p ON p.pick_id = f.pick_id
        WHERE {" AND ".join(where_clauses)}
        ORDER BY f.filter_timestamp DESC
        LIMIT ?
    """
    params.append(limit)
    return conn.execute(sql, params).fetchall()


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

def _fmt_pct(v: Optional[float]) -> str:
    if v is None:
        return "—"
    return f"{v:+.2f}%"


def _print_what_if_table(rows: list[sqlite3.Row], closed_idx: dict) -> None:
    if not rows:
        print("No filtered picks found.")
        return

    print(f"\n{'pick_id':36s}  {'gate':22s}  {'symbol':10s}  {'strategy':30s}  "
          f"{'analogs':>7}  {'mean_pnl':>9}  {'wr':>6}  {'verdict'}")
    print("-" * 140)

    for r in rows:
        key = (r["symbol"] or "", r["strategy"] or "")
        analogs = closed_idx.get(key, [])
        stats = _analog_stats(analogs)
        verdict = _verdict(stats)

        mean_str = _fmt_pct(stats["mean_pnl"])
        wr_str = f"{stats['win_rate']:.0f}%" if stats["win_rate"] is not None else "—"

        print(f"{r['pick_id']:36s}  {r['gate_name']:22s}  {r['symbol'] or '':10s}  "
              f"{(r['strategy'] or '')[:30]:30s}  {stats['n']:>7}  {mean_str:>9}  "
              f"{wr_str:>6}  {verdict}")

    print()


def _print_summary(conn: sqlite3.Connection, closed_idx: dict) -> None:
    print("\n=== What-If Summary by Gate ===\n")
    gates = conn.execute(
        "SELECT gate_name, COUNT(*) as n FROM filter_event_log GROUP BY gate_name ORDER BY n DESC"
    ).fetchall()

    for g in gates:
        gate = g["gate_name"]
        rows = _fetch_filtered_picks(conn, gate=gate, limit=500)
        if not rows:
            continue

        total = len(rows)
        profitable = marginal = loss = no_analog = 0
        for r in rows:
            key = (r["symbol"] or "", r["strategy"] or "")
            analogs = closed_idx.get(key, [])
            stats = _analog_stats(analogs)
            v = _verdict(stats)
            if v == "LIKELY_PROFITABLE":
                profitable += 1
            elif v == "LIKELY_LOSS":
                loss += 1
            elif v == "MARGINAL":
                marginal += 1
            else:
                no_analog += 1

        print(f"  Gate: {gate}")
        print(f"    Total filtered: {total}")
        print(f"    LIKELY_PROFITABLE: {profitable}  ({100*profitable//total}%)")
        print(f"    LIKELY_LOSS:       {loss}  ({100*loss//total}%)")
        print(f"    MARGINAL:          {marginal}  ({100*marginal//total}%)")
        print(f"    NO_ANALOG:         {no_analog}  ({100*no_analog//total}%)")
        print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="What-if query: simulate outcomes of filtered picks using historical analogs."
    )
    parser.add_argument("--gate", help="Filter by gate name (e.g. symbol_blocklist)")
    parser.add_argument("--pick-id", dest="pick_id", help="Query specific pick UUID")
    parser.add_argument("--asset-class", dest="asset_class",
                        help="Filter by asset class (CRYPTO, EQUITY, ...)")
    parser.add_argument("--limit", type=int, default=50, help="Max rows (default 50)")
    parser.add_argument("--list-gates", dest="list_gates", action="store_true",
                        help="List all gate names with counts")
    parser.add_argument("--summary", action="store_true",
                        help="Print what-if summary across all gates")

    args = parser.parse_args()

    if not _DB.exists():
        print(f"ERROR: DB not found at {_DB}", file=sys.stderr)
        sys.exit(1)

    conn = _conn()

    if args.list_gates:
        print("\nGate filter counts:")
        rows = conn.execute(
            "SELECT gate_name, COUNT(*) as n FROM filter_event_log "
            "GROUP BY gate_name ORDER BY n DESC"
        ).fetchall()
        for r in rows:
            print(f"  {r['gate_name']:30s}  {r['n']:>5} picks filtered")
        conn.close()
        return

    if args.summary:
        closed_idx = _load_closed_picks()
        _print_summary(conn, closed_idx)
        conn.close()
        return

    if not args.gate and not args.pick_id:
        parser.print_help()
        conn.close()
        sys.exit(0)

    closed_idx = _load_closed_picks()
    rows = _fetch_filtered_picks(
        conn,
        gate=args.gate,
        pick_id=args.pick_id,
        asset_class=args.asset_class,
        limit=args.limit,
    )

    if args.gate or args.pick_id:
        label = f"gate={args.gate}" if args.gate else f"pick_id={args.pick_id}"
        if args.asset_class:
            label += f" asset_class={args.asset_class}"
        print(f"\nWhat-if query: {label} (showing {len(rows)} of {args.limit} max)")

    _print_what_if_table(rows, closed_idx)
    conn.close()


if __name__ == "__main__":
    main()
