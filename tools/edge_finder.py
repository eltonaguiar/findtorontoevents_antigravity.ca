#!/usr/bin/env python3
"""edge_finder.py — simulate filters and FIND edge over closed picks.

Reads `at_pick_surface_eval` when it has rows (the frozen gate-input snapshot
table populated by tools/pick_surface_snapshot.py); ELSE falls back to
`trading_picks` so it delivers value TODAY, before the writer is wired. The
data source actually used is printed at the top of every run.

USAGE
  python tools/edge_finder.py --baseline
  python tools/edge_finder.py --filter "elite_score>=60,confidence<=0.8,asset_class=CRYPTO"
  python tools/edge_finder.py --surface high_conviction          # needs at_pick_surface_eval
  python tools/edge_finder.py --search                           # the edge finder

DB: host mysql.50webs.com, db ejaguiar1_stocks. Honors env AUDIT_DB_HOST /
AUDIT_DB_USER / AUDIT_DB_PASS. No network for the unit-testable core — the
PF/WR math and the filter parser are pure functions; run with --selftest.

CAVEAT: --search results are IN-SAMPLE. A combo that maxes PF here is a
hypothesis, not an edge. Confirm out-of-sample / via the edge_stability_harness
before sizing anything up.
"""
from __future__ import annotations

import argparse
import itertools
import os
import sys
from typing import Any, Callable, Iterable

# ── terminal statuses that count as CLOSED (case-insensitive) ────────────────
TERMINAL_STATUSES = {
    "closed", "closed_tp", "closed_sl", "won", "win", "lost", "loss",
    "expired", "sl_hit", "tp_hit", "time_exit", "flat", "stale",
}

NUMERIC_SEARCH_FIELDS = (
    "elite_score", "trust_score", "confidence", "forward_wr", "risk_reward",
)

_OPS: dict[str, Callable[[float, float], bool]] = {
    ">=": lambda a, b: a >= b,
    "<=": lambda a, b: a <= b,
    "!=": lambda a, b: a != b,
    ">": lambda a, b: a > b,
    "<": lambda a, b: a < b,
    "=": lambda a, b: a == b,
}
# longest ops first so ">=" is matched before ">"
_OP_ORDER = (">=", "<=", "!=", ">", "<", "=")


# ════════════════════════════════════════════════════════════════════════════
# PURE FUNCTIONS  (network-free, unit-testable)
# ════════════════════════════════════════════════════════════════════════════
def parse_filter(spec: str) -> list[tuple[str, str, Any]]:
    """Parse 'elite_score>=60,confidence<=0.8,asset_class=CRYPTO' into
    [(field, op, value), ...]. Numeric-looking values become floats."""
    clauses: list[tuple[str, str, Any]] = []
    if not spec:
        return clauses
    for raw in spec.split(","):
        part = raw.strip()
        if not part:
            continue
        for op in _OP_ORDER:
            if op in part:
                field, _, val = part.partition(op)
                field = field.strip()
                val = val.strip()
                if not field:
                    raise ValueError(f"empty field in clause: {raw!r}")
                cast: Any
                try:
                    cast = float(val)
                except ValueError:
                    cast = val
                clauses.append((field, op, cast))
                break
        else:
            raise ValueError(f"no operator in clause: {raw!r} (use >= <= > < = !=)")
    return clauses


def _coerce(a: Any, b: Any) -> tuple[Any, Any]:
    """Best-effort align types of a (row value) and b (filter value)."""
    if isinstance(b, float):
        try:
            return float(a), b
        except (TypeError, ValueError):
            return None, b
    # string comparison — case-insensitive
    return (str(a).strip().lower() if a is not None else None,
            str(b).strip().lower())


def row_matches(row: dict, clauses: Iterable[tuple[str, str, Any]]) -> bool:
    """True if `row` satisfies every clause. Missing/None field => no match."""
    for field, op, val in clauses:
        if field not in row:
            return False
        a, b = _coerce(row.get(field), val)
        if a is None:
            return False
        try:
            if not _OPS[op](a, b):
                return False
        except TypeError:
            return False
    return True


def is_closed(row: dict) -> bool:
    """Terminal status AND pnl_pct present."""
    status = str(row.get("status") or "").strip().lower()
    return status in TERMINAL_STATUSES and row.get("pnl_pct") is not None


def compute_stats(pnls: list[float]) -> dict:
    """n / win-rate / profit-factor / avg-pnl from a list of closed pnl_pct."""
    n = len(pnls)
    if n == 0:
        return {"n": 0, "wr": 0.0, "pf": 0.0, "avg": 0.0}
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    gross_win = sum(wins)
    gross_loss = abs(sum(losses))
    if gross_loss == 0:
        pf = float("inf") if gross_win > 0 else 0.0
    else:
        pf = gross_win / gross_loss
    return {
        "n": n,
        "wr": 100.0 * len(wins) / n,
        "pf": pf,
        "avg": sum(pnls) / n,
    }


def stats_by_class(rows: list[dict]) -> dict[str, dict]:
    """Group CLOSED rows by asset_class and compute per-class stats."""
    buckets: dict[str, list[float]] = {}
    for r in rows:
        if not is_closed(r):
            continue
        cls = str(r.get("asset_class") or "UNKNOWN").upper()
        try:
            buckets.setdefault(cls, []).append(float(r["pnl_pct"]))
        except (TypeError, ValueError):
            continue
    return {cls: compute_stats(pnls) for cls, pnls in sorted(buckets.items())}


def _fmt_pf(pf: float) -> str:
    return "inf" if pf == float("inf") else f"{pf:.2f}"


# ════════════════════════════════════════════════════════════════════════════
# DB LAYER
# ════════════════════════════════════════════════════════════════════════════
def _connect():
    import pymysql  # local import keeps the pure core network-free
    host = os.environ.get("AUDIT_DB_HOST", "mysql.50webs.com")
    user = os.environ.get("AUDIT_DB_USER", "ejaguiar1_stocks")
    pwd = os.environ.get("AUDIT_DB_PASS", os.environ.get("DB_PASS_STOCKS", ""))
    return pymysql.connect(
        host=host, user=user, password=pwd, database="ejaguiar1_stocks",
        connect_timeout=20, cursorclass=pymysql.cursors.DictCursor,
    )


def load_rows() -> tuple[list[dict], str]:
    """Return (rows, source_name). Prefers at_pick_surface_eval; falls back
    to trading_picks. Every row is normalized to have keys: symbol, strategy,
    asset_class, elite_score, trust_score, smart_score, confidence, forward_wr,
    risk_reward, status, pnl_pct, closed_at, and the in_* flags when present."""
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS n FROM at_pick_surface_eval")
            apse_n = int(cur.fetchone()["n"])
            if apse_n > 0:
                cur.execute(
                    "SELECT symbol, asset_class, strategy, elite_score, "
                    "smart_score, trust_score, trust_tier, confidence, "
                    "forward_wr, risk_reward, regime, consensus_count, "
                    "in_active, in_smart_picks, in_high_conviction, "
                    "in_money_ready, status, pnl_pct, closed_at "
                    "FROM at_pick_surface_eval"
                )
                rows = [dict(r) for r in cur.fetchall()]
                for r in rows:
                    r["asset_class"] = str(r.get("asset_class") or "UNKNOWN").upper()
                return rows, "at_pick_surface_eval"

            # ── fallback ────────────────────────────────────────────────────
            cur.execute(
                "SELECT symbol, strategy, elite_score, trust_score, category, "
                "confidence, status, pnl_pct, closed_at FROM trading_picks"
            )
            rows = []
            for r in cur.fetchall():
                d = dict(r)
                d["asset_class"] = str(d.pop("category", "") or "UNKNOWN").upper()
                d["smart_score"] = None      # not persisted in trading_picks
                d["forward_wr"] = None       # not persisted
                d["risk_reward"] = None      # not persisted
                rows.append(d)
            return rows, "trading_picks (fallback — surface flags unavailable)"
    finally:
        conn.close()


# ════════════════════════════════════════════════════════════════════════════
# REPORTING
# ════════════════════════════════════════════════════════════════════════════
def _print_class_table(title: str, by_class: dict[str, dict]) -> None:
    print(f"\n{title}")
    print(f"  {'CLASS':<12} {'N':>7} {'WR%':>8} {'PF':>8} {'AVG_PNL':>10}")
    print(f"  {'-'*12} {'-'*7} {'-'*8} {'-'*8} {'-'*10}")
    if not by_class:
        print("  (no closed picks match)")
        return
    for cls, s in by_class.items():
        print(f"  {cls:<12} {s['n']:>7} {s['wr']:>8.1f} "
              f"{_fmt_pf(s['pf']):>8} {s['avg']:>10.3f}")


def run_baseline(rows: list[dict]) -> None:
    _print_class_table("=== BASELINE (no filter) — per asset class ===",
                        stats_by_class(rows))


def run_filter(rows: list[dict], spec: str) -> None:
    clauses = parse_filter(spec)
    print(f"\nFilter clauses: {clauses}")
    matched = [r for r in rows if row_matches(r, clauses)]
    _print_class_table(f"=== FILTERED: {spec} ===", stats_by_class(matched))


def run_surface(rows: list[dict], surface: str, source: str) -> None:
    flag = {
        "active": "in_active", "smart_picks": "in_smart_picks",
        "high_conviction": "in_high_conviction", "money_ready": "in_money_ready",
    }[surface]
    if "at_pick_surface_eval" not in source:
        print(f"\n[!] --surface {surface} requires at_pick_surface_eval, but the "
              f"data source is '{source}'.\n    The in_* surface flags are not "
              f"available in trading_picks — wire tools/pick_surface_snapshot.py "
              f"first.")
        return
    matched = [r for r in rows if r.get(flag) in (1, True, "1")]
    _print_class_table(f"=== SURFACE: {surface} ({flag}=1) ===",
                        stats_by_class(matched))


def run_search(rows: list[dict], min_n: int = 30, top: int = 5) -> None:
    """Greedy/grid search over numeric-field thresholds maximizing per-class PF.

    For each numeric field we try a small grid of percentile-derived
    thresholds with both >= and <=. We then grid-combine up to 2 fields and,
    per asset class, report the top `top` combos by PF at n>=min_n."""
    closed = [r for r in rows if is_closed(r)]
    print(f"\n=== EDGE SEARCH ===  closed picks: {len(closed)}  min_n={min_n}")

    # which numeric fields actually have data
    usable: list[str] = []
    for f in NUMERIC_SEARCH_FIELDS:
        vals = [r[f] for r in closed
                if r.get(f) is not None and _is_num(r.get(f))]
        if len(vals) >= min_n:
            usable.append(f)
    if not usable:
        print("  No numeric fields with enough non-null data to search.")
        return
    print(f"  Searchable fields: {', '.join(usable)}")

    # build candidate single-field cuts: (field, op, threshold)
    candidates: list[tuple[str, str, float]] = []
    for f in usable:
        vals = sorted(float(r[f]) for r in closed
                      if r.get(f) is not None and _is_num(r.get(f)))
        thresholds = _grid(vals)
        for t in thresholds:
            candidates.append((f, ">=", t))
            candidates.append((f, "<=", t))

    classes = sorted({str(r.get("asset_class") or "UNKNOWN").upper()
                      for r in closed})

    for cls in classes:
        cls_rows = [r for r in closed
                    if str(r.get("asset_class") or "UNKNOWN").upper() == cls]
        if len(cls_rows) < min_n:
            continue
        results: list[tuple[float, str, dict]] = []

        # 1-field cuts
        for (f, op, t) in candidates:
            sub = [r for r in cls_rows
                   if _is_num(r.get(f)) and _OPS[op](float(r[f]), t)]
            s = compute_stats([float(r["pnl_pct"]) for r in sub])
            if s["n"] >= min_n:
                label = f"{f}{op}{_short(t)}"
                results.append((s["pf"], label, s))

        # 2-field combos (different fields)
        for (c1, c2) in itertools.combinations(candidates, 2):
            if c1[0] == c2[0]:
                continue
            sub = [r for r in cls_rows
                   if _is_num(r.get(c1[0])) and _is_num(r.get(c2[0]))
                   and _OPS[c1[1]](float(r[c1[0]]), c1[2])
                   and _OPS[c2[1]](float(r[c2[0]]), c2[2])]
            s = compute_stats([float(r["pnl_pct"]) for r in sub])
            if s["n"] >= min_n:
                label = (f"{c1[0]}{c1[1]}{_short(c1[2])} & "
                         f"{c2[0]}{c2[1]}{_short(c2[2])}")
                results.append((s["pf"], label, s))

        # dedup by label keeping best, sort by PF then n
        best: dict[str, tuple[float, str, dict]] = {}
        for item in results:
            lbl = item[1]
            if lbl not in best or item[0] > best[lbl][0]:
                best[lbl] = item
        ranked = sorted(best.values(),
                        key=lambda x: (x[0], x[2]["n"]), reverse=True)[:top]

        base = compute_stats([float(r["pnl_pct"]) for r in cls_rows])
        print(f"\n  [{cls}]  baseline: n={base['n']} "
              f"WR={base['wr']:.1f}% PF={_fmt_pf(base['pf'])}")
        if not ranked:
            print(f"    (no combo reaches n>={min_n})")
            continue
        for rank, (pf, label, s) in enumerate(ranked, 1):
            print(f"    {rank}. PF={_fmt_pf(pf):>6}  n={s['n']:>5}  "
                  f"WR={s['wr']:>5.1f}%  avg={s['avg']:>7.3f}   {label}")

    print("\n  [!] IN-SAMPLE WARNING: these combos were selected to maximize")
    print("      PF on the SAME closed picks they are scored on. This is")
    print("      data-snooping by construction. Treat each combo as a")
    print("      HYPOTHESIS — confirm out-of-sample (time-split holdout) and")
    print("      via the edge_stability_harness before sizing anything up.")


def _is_num(v: Any) -> bool:
    if v is None:
        return False
    try:
        float(v)
        return True
    except (TypeError, ValueError):
        return False


def _grid(sorted_vals: list[float], k: int = 6) -> list[float]:
    """k distinct percentile-spaced thresholds."""
    if not sorted_vals:
        return []
    out = []
    n = len(sorted_vals)
    for i in range(1, k):
        idx = min(n - 1, int(n * i / k))
        out.append(round(sorted_vals[idx], 4))
    return sorted(set(out))


def _short(t: float) -> str:
    return f"{t:g}"


# ════════════════════════════════════════════════════════════════════════════
# SELF-TEST  (network-free)
# ════════════════════════════════════════════════════════════════════════════
def _selftest() -> int:
    # filter parser
    cl = parse_filter("elite_score>=60,confidence<=0.8,asset_class=CRYPTO")
    assert cl == [("elite_score", ">=", 60.0), ("confidence", "<=", 0.8),
                  ("asset_class", "=", "CRYPTO")], cl
    assert parse_filter("trust_score!=0") == [("trust_score", "!=", 0.0)]
    try:
        parse_filter("badclause")
        assert False, "should have raised"
    except ValueError:
        pass

    # row_matches
    row = {"elite_score": 70, "confidence": 0.5, "asset_class": "crypto"}
    assert row_matches(row, cl) is True
    assert row_matches({"elite_score": 50, "confidence": 0.5,
                        "asset_class": "crypto"}, cl) is False
    assert row_matches({"elite_score": 70}, cl) is False  # missing field

    # is_closed
    assert is_closed({"status": "WON", "pnl_pct": 1.2}) is True
    assert is_closed({"status": "OPEN", "pnl_pct": 1.2}) is False
    assert is_closed({"status": "WON", "pnl_pct": None}) is False

    # compute_stats
    s = compute_stats([2.0, -1.0, 3.0, -1.0])
    assert s["n"] == 4
    assert abs(s["wr"] - 50.0) < 1e-9, s
    assert abs(s["pf"] - 2.5) < 1e-9, s          # (2+3)/(1+1)
    assert abs(s["avg"] - 0.75) < 1e-9, s
    assert compute_stats([])["n"] == 0
    assert compute_stats([1.0, 2.0])["pf"] == float("inf")

    # stats_by_class
    fixture = [
        {"asset_class": "CRYPTO", "status": "WON", "pnl_pct": 2.0},
        {"asset_class": "CRYPTO", "status": "LOST", "pnl_pct": -1.0},
        {"asset_class": "EQUITY", "status": "WON", "pnl_pct": 5.0},
        {"asset_class": "EQUITY", "status": "OPEN", "pnl_pct": 99.0},  # excluded
    ]
    bc = stats_by_class(fixture)
    assert bc["CRYPTO"]["n"] == 2 and bc["EQUITY"]["n"] == 1, bc
    assert abs(bc["CRYPTO"]["pf"] - 2.0) < 1e-9, bc

    print("edge_finder self-test: ALL PASS")
    return 0


# ════════════════════════════════════════════════════════════════════════════
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Simulate filters and find edge.")
    ap.add_argument("--filter", help="field/op/value list, comma-separated")
    ap.add_argument("--surface", choices=["smart_picks", "high_conviction",
                                          "money_ready", "active"],
                    help="shortcut filter on an in_* flag")
    ap.add_argument("--search", action="store_true",
                    help="grid-search threshold combos for max per-class PF")
    ap.add_argument("--baseline", action="store_true",
                    help="per-class stats with no filter")
    ap.add_argument("--min-n", type=int, default=30,
                    help="minimum sample size for --search combos (default 30)")
    ap.add_argument("--selftest", action="store_true",
                    help="run network-free unit self-test and exit")
    args = ap.parse_args(argv)

    if args.selftest:
        return _selftest()

    if not (args.filter or args.surface or args.search or args.baseline):
        ap.print_help()
        return 1

    rows, source = load_rows()
    print(f"[data source] {source}  —  {len(rows)} rows loaded")
    closed_n = sum(1 for r in rows if is_closed(r))
    print(f"[closed picks] {closed_n}")

    if args.baseline:
        run_baseline(rows)
    if args.filter:
        run_filter(rows, args.filter)
    if args.surface:
        run_surface(rows, args.surface, source)
    if args.search:
        run_search(rows, min_n=args.min_n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
