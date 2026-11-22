#!/usr/bin/env python3
"""Per-class price-table freshness SLA — fails CI when a class is about to go unmeasured.

Why this exists
---------------
`alpha_engine/audit3_selection_alpha.py` maps every asset class to a price table and
declares a per-class staleness tolerance (`TABLE_FOR`, `TOLERANCE_MS`). Those numbers
are load-bearing: if a table goes stale, the class silently reverts to "unmeasured"
and its selection-alpha gate can never be evaluated — however fresh the others are.

Before this tool, the only check was an inline block in `.github/workflows/audit3-ledger.yml`
that *printed* a warning at a hardcoded 5-day threshold. Two problems:

  1. It was advisory. A stale equity table printed `::warning` and the job went green.
  2. It re-hardcoded 5 days instead of reading TOLERANCE_MS, so the alarm and the gate
     could disagree — and the gate is the one that decides whether a class is measured.

So this tool reads the thresholds from the gate itself (one source of truth), checks
every distinct table, and exits non-zero on breach.

Semantics
---------
- `date` tables (equity/etf/futures/fx): age from MAX(trade_date), tolerated in calendar
  days. The 5-day tolerance already absorbs weekends and holidays — do not add a
  trading-calendar notion here, it would only make the gate more permissive.
- `ms` tables (crypto_ohlcv): age from MAX(timestamp), an epoch-milliseconds value.
- A table shared by two classes (etf_daily_ohlcv serves ETF and BOND) is checked once,
  at the *tightest* tolerance among its classes, and the report names every class it
  gates. Checking it twice would just print the same number twice.

Exit codes
----------
  0 = every table within SLA
  1 = at least one breach (CI failure)
  2 = could not check (no DB credentials / driver) — distinct from a breach, because
      "I could not look" must never be reported as "it is fine", nor as "it is stale".
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from alpha_engine.audit3_selection_alpha import TABLE_FOR, TOLERANCE_MS
except ImportError as exc:  # pragma: no cover - only on a broken tree
    print(f"cannot import the canonical table/tolerance map: {exc}", file=sys.stderr)
    raise SystemExit(2)

DAY_MS = 86_400_000


def table_requirements() -> dict[str, dict[str, Any]]:
    """Collapse TABLE_FOR into one requirement per physical table.

    Returns {table: {"kind": "date"|"ms", "tolerance_ms": int, "classes": [..]}}.
    Shared tables take the tightest tolerance and list every class they gate.
    """
    req: dict[str, dict[str, Any]] = {}
    for klass, (table, kind) in TABLE_FOR.items():
        tol = TOLERANCE_MS.get(klass)
        if tol is None:
            continue  # a class with no declared tolerance is not silently assumed fresh
        cur = req.get(table)
        if cur is None:
            req[table] = {"kind": kind, "tolerance_ms": int(tol), "classes": [klass]}
        else:
            cur["classes"].append(klass)
            cur["tolerance_ms"] = min(cur["tolerance_ms"], int(tol))
    for rec in req.values():
        rec["classes"].sort()
    return req


def _to_ms(value: Any, kind: str) -> int | None:
    """Convert a MAX(...) result into epoch milliseconds, or None if empty."""
    if value is None:
        return None
    if kind == "ms":
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
    # a DATE / DATETIME column: treat it as the end of that UTC day so a bar dated
    # today is 0 days old, not 1.
    if isinstance(value, datetime):
        d = value.date()
    elif isinstance(value, date):
        d = value
    else:
        try:
            d = datetime.fromisoformat(str(value)[:10]).date()
        except ValueError:
            return None
    return int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp() * 1000) + DAY_MS


def evaluate(last_values: dict[str, Any], now_ms: int | None = None) -> list[dict[str, Any]]:
    """Pure check: {table: MAX(...)} -> per-table verdicts. No DB, so it is testable."""
    now_ms = int(time.time() * 1000) if now_ms is None else int(now_ms)
    req = table_requirements()
    out: list[dict[str, Any]] = []
    for table, spec in sorted(req.items()):
        last_ms = _to_ms(last_values.get(table), spec["kind"])
        tol = spec["tolerance_ms"]
        if last_ms is None:
            out.append({
                "table": table, "classes": spec["classes"], "kind": spec["kind"],
                "last": None, "age_ms": None, "tolerance_ms": tol,
                "status": "EMPTY", "ok": False,
                "reason": "no rows — the class is structurally unmeasurable",
            })
            continue
        age_ms = now_ms - last_ms
        ok = age_ms <= tol
        out.append({
            "table": table, "classes": spec["classes"], "kind": spec["kind"],
            "last": last_values.get(table), "age_ms": age_ms, "tolerance_ms": tol,
            "status": "OK" if ok else "STALE", "ok": ok,
            "reason": "" if ok else (
                f"{age_ms / DAY_MS:.1f}d old, tolerance {tol / DAY_MS:.1f}d — "
                f"{'/'.join(spec['classes'])} will go unmeasured"
            ),
        })
    return out


def render(verdicts: list[dict[str, Any]]) -> str:
    lines = []
    for v in verdicts:
        age = "—" if v["age_ms"] is None else f"{v['age_ms'] / DAY_MS:.1f}d"
        tol = f"{v['tolerance_ms'] / DAY_MS:.1f}d"
        classes = "/".join(v["classes"])
        lines.append(
            f"  {v['table']:22s} {classes:20s} last={str(v['last']):20s} "
            f"age={age:>7s} tol={tol:>5s} {v['status']}"
            + (f"  ({v['reason']})" if v["reason"] else "")
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Per-class price-table freshness SLA")
    ap.add_argument("--warn-only", action="store_true",
                    help="report breaches but exit 0 (for local runs)")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of text")
    args = ap.parse_args(argv)

    try:
        import pymysql  # noqa: F401
        from tools.db_env import get_stocks_creds
    except ImportError as exc:
        print(f"cannot check freshness ({exc}) — install pymysql / configure db_env",
              file=sys.stderr)
        return 2

    try:
        import pymysql
        keep = ("host", "user", "password", "database", "port", "connect_timeout")
        conn = pymysql.connect(read_timeout=60,
                               **{k: v for k, v in get_stocks_creds().items() if k in keep})
    except Exception as exc:  # noqa: BLE001 - any connection failure is the same answer
        print(f"cannot connect to the stocks DB: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    req = table_requirements()
    last_values: dict[str, Any] = {}
    try:
        cur = conn.cursor()
        for table, spec in req.items():
            col = "timestamp" if spec["kind"] == "ms" else "trade_date"
            try:
                cur.execute(f"SELECT MAX(`{col}`) FROM `{table}`")
                last_values[table] = cur.fetchone()[0]
            except Exception as exc:  # noqa: BLE001 - a missing table is EMPTY, not fresh
                print(f"  {table}: query failed ({type(exc).__name__}) — treated as EMPTY",
                      file=sys.stderr)
                last_values[table] = None
    finally:
        conn.close()

    verdicts = evaluate(last_values)
    if args.json:
        import json
        print(json.dumps(verdicts, indent=2, default=str))
    else:
        print("price-table freshness per class:")
        print(render(verdicts))

    bad = [v for v in verdicts if not v["ok"]]
    if not bad:
        return 0
    for v in bad:
        print(f"::error title=price_freshness::{v['table']} {v['status']} — {v['reason']}")
    return 0 if args.warn_only else 1


if __name__ == "__main__":
    raise SystemExit(main())
