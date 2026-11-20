#!/usr/bin/env python3
"""forward_observations.py — the forward-evidence contract that makes "winning" measurable.

Why this exists
---------------
External review §5.8 (agreed, deferred twice): without a first-class forward ledger,
audit3 can never mint a PROVEN verdict **from live data** — it can only re-score the
past. The `FWD` fields exist piecemeal across the dashboard; nothing owns the row
shape, the cost arithmetic, or the promotion rule.

This module owns those three things and nothing else:

1. **Row shape** — the review's schema, validated:
   ``id, hypothesis_id, opened_at, closed_at, symbol, asset_class, side, entry_px,
   exit_px, qty, fees, funding, slippage_bps, resolver_version,
   intrabar_first_touch, benchmark_leg_ret, regime_ok, created_at``
2. **Cost arithmetic** — one definition of net return, so "net" means the same thing
   in every consumer (see `net_returns`).
3. **Promotion rule** — ``PROVEN_T2`` requires ≥100 forward rows AND a net PF CI-LB
   above breakeven AND honest-intrabar first-touch on every row.

Deliberately **not** here: ingestion. Reading the cohort out of MySQL needs the
RSI/session stampers and a DB connection, so this module ships the contract, the
verifier, the clock and the promotion rule, and reports an empty ledger honestly
rather than inventing rows. A ledger with zero rows cannot promote anything, which is
the correct state until an adapter fills it.

Promotion rule (all required)
-----------------------------
* ``n_forward >= 100`` (``PROMOTION_MIN_N``) — rows closed forward of registration.
* ``net PF CI-LB > 1.0`` (symbol-day clustered bootstrap) **or** per-trade ``IR >= 0.5``.
  The review wrote "net CI-LB>0 (or IR≥0.5)"; PF's breakeven is 1.0, so both readings
  are implemented and either clears.
* ``intrabar_first_touch is True`` on **100%** of rows — the daily-resolution inflation
  that refuted H-118 (2.88 → 1.02) and generalised in H-120 is exactly what a
  daily-resolved forward row would reintroduce.
* ``benchmark_leg_ret`` present on ≥90% of rows, so "beat holding" stays computable.

These are verdict-gating numbers, so they live in one place with tests rather than in
whichever script happens to compute them.

Usage::

    python3 -m alpha_engine.forward_observations --verify
    python3 -m alpha_engine.forward_observations --clock H-119
    python3 -m alpha_engine.forward_observations --promotion H-119 --json
    python3 -m alpha_engine.forward_observations --append new_rows.jsonl
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:  # allow `python3 alpha_engine/forward_observations.py`
    sys.path.insert(0, str(REPO))

DEFAULT_LEDGER = REPO / "reports" / "forward_observations.jsonl"
REGISTRY = REPO / "reports" / "hypothesis_registry.json"

SCHEMA = "forward_observations.v1"
PROMOTION_MIN_N = 100
PROMOTION_PF_CI_LB = 1.0
PROMOTION_IR = 0.5
BENCHMARK_COVERAGE_MIN = 0.90
CLOCK_WINDOW_DAYS = 30

#: Required columns, in the review's order. `asset_class` is the review's `class`.
FIELDS = (
    "id", "hypothesis_id", "opened_at", "closed_at", "symbol", "asset_class", "side",
    "entry_px", "exit_px", "qty", "fees", "funding", "slippage_bps",
    "resolver_version", "intrabar_first_touch", "benchmark_leg_ret", "regime_ok",
    "created_at",
)
SIDES = {"LONG", "SHORT"}
_NUMERIC = ("entry_px", "exit_px", "qty", "fees", "funding", "slippage_bps")
_TIMESTAMPS = ("opened_at", "closed_at", "created_at")
_REGISTRY_IDS: list[str] | None = None


# --------------------------------------------------------------------------- helpers
def _parse(ts: Any) -> datetime | None:
    if not isinstance(ts, str) or not ts.strip():
        return None
    v = ts.strip()
    v = v[:-1] + "+00:00" if v.endswith("Z") else v
    try:
        dt = datetime.fromisoformat(v)
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _num(value: Any) -> float | None:
    """None for absent, NaN-free float. Booleans are not numbers here."""
    if isinstance(value, bool) or value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) or math.isinf(f) else f


def hypothesis_ids(path: Path | str = REGISTRY) -> set[str]:
    """Every registered hypothesis id, discovered structurally.

    The registry is an author-maintained document whose nesting has changed before, so
    walk it for ``{"id": "H-xxx"}`` dicts instead of assuming a top-level list.
    """
    global _REGISTRY_IDS
    if _REGISTRY_IDS is not None:
        return set(_REGISTRY_IDS)
    found: set[str] = set()

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            ident = node.get("id")
            if isinstance(ident, str) and ident.strip():
                found.add(ident.strip().upper())
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    try:
        walk(json.loads(Path(path).read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return set()
    _REGISTRY_IDS = sorted(found)
    return found


def _natural_key(row: dict) -> tuple:
    return (str(row.get("hypothesis_id") or "").upper(),
            str(row.get("symbol") or "").upper(),
            str(row.get("side") or "").upper(),
            str(row.get("opened_at") or ""))


# ------------------------------------------------------------------------ validation
def validate(row: Any, known_hypotheses: Iterable[str] | None = None) -> list[str]:
    """Return every problem with one row; empty list means admissible."""
    if not isinstance(row, dict):
        return ["row is not an object"]
    errors: list[str] = []
    missing = [f for f in FIELDS if f not in row]
    if missing:
        errors.append(f"missing fields: {', '.join(missing)}")
        return errors

    if not isinstance(row["id"], str) or not row["id"].strip():
        errors.append("id must be a non-empty string")
    if not isinstance(row["symbol"], str) or not row["symbol"].strip():
        errors.append("symbol must be a non-empty string")
    if not isinstance(row["resolver_version"], str) or not row["resolver_version"].strip():
        errors.append("resolver_version must be a non-empty string")

    ac = row["asset_class"]
    if not isinstance(ac, str) or not ac.strip():
        errors.append("asset_class must be a non-empty string")

    side = str(row["side"] or "").upper()
    if side not in SIDES:
        errors.append(f"side must be one of {sorted(SIDES)} (got {row['side']!r})")

    hid = str(row["hypothesis_id"] or "").strip().upper()
    if not hid:
        errors.append("hypothesis_id must be a non-empty string")
    elif known_hypotheses is not None and hid not in {h.upper() for h in known_hypotheses}:
        errors.append(f"hypothesis_id {hid!r} is not in the registry (dangling FK)")

    parsed: dict[str, datetime] = {}
    for field in _TIMESTAMPS:
        dt = _parse(row[field])
        if dt is None:
            errors.append(f"{field} must be an ISO-8601 timestamp")
        else:
            parsed[field] = dt
    if "opened_at" in parsed and "closed_at" in parsed and parsed["closed_at"] < parsed["opened_at"]:
        errors.append("closed_at precedes opened_at")

    for field in _NUMERIC:
        value = _num(row[field])
        if value is None:
            errors.append(f"{field} must be a finite number")
            continue
        if field in ("entry_px", "qty") and value <= 0:
            errors.append(f"{field} must be > 0 to compute a return")
        if field in ("slippage_bps",):
            if value < 0:
                errors.append("slippage_bps must be >= 0")

    if row["intrabar_first_touch"] is not True:
        errors.append("intrabar_first_touch must be true (daily-resolved rows are not forward evidence)")
    if not isinstance(row["regime_ok"], bool):
        errors.append("regime_ok must be a boolean")
    if row["benchmark_leg_ret"] is not None and _num(row["benchmark_leg_ret"]) is None:
        errors.append("benchmark_leg_ret must be a number or null")
    return errors


# ------------------------------------------------------------------- cost arithmetic
def net_returns(rows: Iterable[dict]) -> list[float]:
    """One definition of net return, in return space.

    ``gross = side_sign * (exit_px - entry_px) / entry_px``
    ``cost  = (fees + funding) / (qty * entry_px) + slippage_bps / 1e4``
    ``net   = gross - cost``

    ``fees`` and ``funding`` are **absolute account currency** amounts (negative funding
    is a payment received). Rows that cannot produce a number are skipped, never
    zero-filled: a missing cost is not a free trade.
    """
    out: list[float] = []
    for row in rows:
        entry, exit_px, qty = (_num(row.get(k)) for k in ("entry_px", "exit_px", "qty"))
        if not entry or entry <= 0 or exit_px is None or not qty or qty <= 0:
            continue
        side = str(row.get("side") or "").upper()
        sign = 1.0 if side == "LONG" else -1.0 if side == "SHORT" else 0.0
        if sign == 0.0:
            continue
        gross = sign * (exit_px - entry) / entry
        cost = ((_num(row.get("fees")) or 0.0) + (_num(row.get("funding")) or 0.0)) / (qty * entry)
        cost += (_num(row.get("slippage_bps")) or 0.0) / 10_000.0
        out.append(gross - cost)
    return out


def _pf_ci(net: list[float], rows: list[dict]) -> dict:
    """Clustered-bootstrap PF CI-LB via the repo's canonical implementation."""
    from tools.pf_ci_lower import pf_ci_lower  # stdlib-only, no DB

    clusters = [f"{str(r.get('symbol') or '')}|{str(r.get('closed_at') or '')[:10]}" for r in rows]
    return pf_ci_lower(net, clusters=clusters or None)


# ---------------------------------------------------------------------- clock/ledger
def load(path: Path | str = DEFAULT_LEDGER) -> tuple[list[dict], list[str]]:
    """Read the JSONL ledger. A missing file is an empty ledger, not an error."""
    p = Path(path)
    rows: list[dict] = []
    errors: list[str] = []
    if not p.exists():
        return rows, errors
    for lineno, line in enumerate(p.read_text(encoding="utf-8").splitlines(), start=1):
        text = line.strip()
        if not text:
            continue
        try:
            obj = json.loads(text)
        except ValueError as exc:
            errors.append(f"line {lineno}: invalid JSON ({exc})")
            continue
        if not isinstance(obj, dict):
            errors.append(f"line {lineno}: not an object")
            continue
        rows.append(obj)
    return rows, errors


def append(rows: Iterable[dict], path: Path | str = DEFAULT_LEDGER,
           known_hypotheses: Iterable[str] | None = None) -> dict:
    """Append admissible rows, skipping exact duplicates. Never rewrites history."""
    p = Path(path)
    existing, read_errors = load(p)
    seen_ids = {str(r.get("id") or "") for r in existing}
    seen_keys = {_natural_key(r) for r in existing}
    ids = known_hypotheses if known_hypotheses is not None else hypothesis_ids()
    added: list[dict] = []
    rejected: list[dict] = []
    duplicates = 0
    for row in rows:
        problems = validate(row, ids)
        if problems:
            rejected.append({"row": row.get("id") if isinstance(row, dict) else None,
                             "errors": problems})
            continue
        ident = str(row["id"])
        key = _natural_key(row)
        if ident in seen_ids or key in seen_keys:
            duplicates += 1
            continue
        seen_ids.add(ident)
        seen_keys.add(key)
        added.append(row)
    if added:
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as fh:
            for row in added:
                fh.write(json.dumps(row, sort_keys=True) + "\n")
    return {"path": str(p), "added": len(added), "duplicates": duplicates,
            "rejected": rejected, "read_errors": read_errors}


def verify(path: Path | str = DEFAULT_LEDGER) -> dict:
    """Integrity report: schema violations, duplicates, dangling hypotheses."""
    rows, read_errors = load(path)
    ids = hypothesis_ids()
    violations: list[dict] = []
    for row in rows:
        problems = validate(row, ids)
        if problems:
            violations.append({"id": row.get("id"), "errors": problems})
    by_id: dict[str, int] = {}
    by_key: dict[tuple, int] = {}
    for row in rows:
        by_id[str(row.get("id") or "")] = by_id.get(str(row.get("id") or ""), 0) + 1
        by_key[_natural_key(row)] = by_key.get(_natural_key(row), 0) + 1
    per_hypothesis: dict[str, int] = {}
    for row in rows:
        hid = str(row.get("hypothesis_id") or "").upper()
        per_hypothesis[hid] = per_hypothesis.get(hid, 0) + 1
    return {
        "schema": SCHEMA,
        "path": str(Path(path)),
        "n_rows": len(rows),
        "read_errors": read_errors,
        "violations": violations,
        "duplicate_ids": sorted(k for k, v in by_id.items() if v > 1),
        "duplicate_rows": sum(v - 1 for v in by_key.values() if v > 1),
        "n_by_hypothesis": dict(sorted(per_hypothesis.items())),
        "registry_hypotheses": len(ids),
        "ok": not (read_errors or violations or any(v > 1 for v in by_id.values())),
    }


def clock(hypothesis_id: str | None = None, rows: list[dict] | None = None,
          path: Path | str = DEFAULT_LEDGER, now: datetime | None = None) -> dict:
    """How fast is forward evidence accruing, and when does the n gate close?

    A date-based ETA is only reported when there are rows to extrapolate from. The
    H-119 card spent months advertising "~2026-06-25" against a receding count; this
    reports the rate it actually observed instead of a promise.
    """
    if rows is None:
        rows, _ = load(path)
    hid = (hypothesis_id or "").strip().upper()
    subset = [r for r in rows if not hid or str(r.get("hypothesis_id") or "").upper() == hid]
    now = now or datetime.now(timezone.utc)
    closed = [_parse(r.get("closed_at")) for r in subset]
    closed = [c for c in closed if c is not None]
    n = len(subset)
    window_start = now - timedelta(days=CLOCK_WINDOW_DAYS)
    n_window = sum(1 for c in closed if c >= window_start)
    rate_day = n_window / CLOCK_WINDOW_DAYS
    source = f"closed rows in last {CLOCK_WINDOW_DAYS}d"
    if rate_day <= 0 and closed:
        opened = [_parse(r.get("opened_at")) for r in subset]
        opened = [o for o in opened if o is not None]
        if opened:
            elapsed = max((now - min(opened)).total_seconds() / 86400.0, 1.0)
            rate_day = n / elapsed
            source = "all rows over elapsed time"
    remaining = max(PROMOTION_MIN_N - n, 0)
    eta_days = math.ceil(remaining / rate_day) if rate_day > 0 and remaining else (0 if remaining == 0 else None)
    return {
        "hypothesis_id": hid or None,
        "n_forward": n,
        "n_needed": PROMOTION_MIN_N,
        "remaining": remaining,
        "n_last_30d": n_window,
        "rate_per_day": round(rate_day, 3),
        "rate_source": source,
        "eta_days": eta_days,
        "eta_at": (now + timedelta(days=eta_days)).date().isoformat() if eta_days else None,
        "status": "N_GATE_MET" if remaining == 0 else ("ACCRUING" if rate_day > 0 else "NO_FORWARD_ROWS"),
    }


def _finite_pf(v, ceiling: float = 99.0):
    """JSON-safe profit factor.

    A pod with **no losing trades** produces ``inf``. ``json.dumps(...,
    allow_nan=False)`` then refuses the whole ledger ("Out of range float
    values"), which is how the first Faber forward rows took the build down on
    2026-11-20. A perfect record is genuinely excellent, so cap it at a finite
    ceiling instead of turning it into None (which would fail the gate).
    """
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if math.isnan(f):
        return None
    if f == float("inf"):
        return ceiling
    if f == float("-inf"):
        return 0.0
    return f


def promotion(rows: list[dict], min_n: int = PROMOTION_MIN_N) -> dict:
    """Apply the forward promotion rule to rows already filtered to one hypothesis."""
    # Pair each row with its own net return so the bootstrap clusters can never
    # drift out of alignment with the series being tested.
    pairs = [(row, vals[0]) for row in rows if (vals := net_returns([row]))]
    net = [value for _, value in pairs]
    n = len(net)
    result: dict[str, Any] = {"n_forward": n, "min_n": min_n}
    if n == 0:
        result.update({"eligible": False,
                       "reason": "no forward rows — nothing can promote",
                       "reasons": ["no forward rows — nothing can promote"],
                       "pf_ci_lb": None, "ir": None})
        return result

    ci = _pf_ci(net, [row for row, _ in pairs])
    mean = sum(net) / n
    var = sum((x - mean) ** 2 for x in net) / (n - 1) if n > 1 else 0.0
    sd = math.sqrt(var)
    ir = (mean / sd) if sd > 0 else None
    intrabar_all = all(r.get("intrabar_first_touch") is True for r in rows)
    bench_cov = (sum(1 for r in rows if _num(r.get("benchmark_leg_ret")) is not None) / len(rows)) if rows else 0.0
    excess = [r for r in rows if _num(r.get("benchmark_leg_ret")) is not None]
    excess_mean = (sum(net_returns(excess)) / len(excess)) if excess else None
    bench_mean = (sum(_num(r.get("benchmark_leg_ret")) or 0.0 for r in excess) / len(excess)) if excess else None

    pf_lb = _finite_pf(ci.get("pf_ci_lower"))
    reasons: list[str] = []
    if n < min_n:
        reasons.append(f"n_forward {n} < {min_n}")
    if not (pf_lb is not None and pf_lb > PROMOTION_PF_CI_LB) and not (ir is not None and ir >= PROMOTION_IR):
        reasons.append(f"net PF CI-LB {pf_lb} <= {PROMOTION_PF_CI_LB} and IR {None if ir is None else round(ir, 3)} < {PROMOTION_IR}")
    if not intrabar_all:
        reasons.append("some rows are not honest intrabar first-touch")
    if bench_cov < BENCHMARK_COVERAGE_MIN:
        reasons.append(f"benchmark_leg_ret coverage {bench_cov:.0%} < {BENCHMARK_COVERAGE_MIN:.0%}")

    result.update({
        "eligible": not reasons,
        "reasons": reasons,
        "net_mean_pct": round(mean * 100, 4),
        "net_pf": _finite_pf(ci.get("pf")),
        "pf_ci_lb": pf_lb,
        "ir": None if ir is None else round(ir, 4),
        "intrabar_first_touch_all": intrabar_all,
        "benchmark_coverage": round(bench_cov, 3),
        "excess_vs_benchmark_pct": (None if excess_mean is None or bench_mean is None
                                    else round((excess_mean - bench_mean) * 100, 4)),
        "note": "descriptor only: excess vs benchmark is reported, not gated",
    })
    return result


def ledger_fingerprint(path: Path | str = DEFAULT_LEDGER) -> str:
    """Stable digest so a payload can pin the exact ledger it scored."""
    p = Path(path)
    if not p.exists():
        return "absent"
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Forward-observations ledger: verify, clock, promotion")
    ap.add_argument("--ledger", default=str(DEFAULT_LEDGER))
    ap.add_argument("--append", help="JSON (list or JSONL) of rows to append")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--clock", metavar="HYPOTHESIS_ID")
    ap.add_argument("--promotion", metavar="HYPOTHESIS_ID")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.append:
        payload = json.loads(Path(args.append).read_text(encoding="utf-8")) \
            if args.append.endswith(".json") else [json.loads(l) for l in Path(args.append).read_text(encoding="utf-8").splitlines() if l.strip()]
        report = append(payload, args.ledger)
        print(json.dumps(report, indent=2) if args.json
              else f"added {report['added']}, duplicates {report['duplicates']}, rejected {len(report['rejected'])}")
        return 0 if not report["rejected"] else 1

    rows, read_errors = load(args.ledger)
    if args.clock:
        out = clock(args.clock, rows=rows)
        out["ledger_fingerprint"] = ledger_fingerprint(args.ledger)
        print(json.dumps(out, indent=2) if args.json
              else f"{out['hypothesis_id']}: {out['n_forward']}/{out['n_needed']} forward rows, "
                   f"{out['rate_per_day']}/day ({out['rate_source']}), status {out['status']}"
                   + (f", eta {out['eta_at']} ({out['eta_days']}d)" if out["eta_at"] else ""))
        return 0
    if args.promotion:
        hid = args.promotion.upper()
        subset = [r for r in rows if str(r.get("hypothesis_id") or "").upper() == hid]
        out = promotion(subset)
        out["hypothesis_id"] = hid
        print(json.dumps(out, indent=2) if args.json
              else f"{hid}: eligible={out['eligible']} n={out['n_forward']}"
                   + ("" if out["eligible"] else f" — {'; '.join(out.get('reasons') or [])}"))
        return 0
    out = verify(args.ledger)
    if read_errors:
        out["read_errors"] = read_errors
    print(json.dumps(out, indent=2) if args.json
          else f"{out['path']}: {out['n_rows']} rows, ok={out['ok']}, "
               f"violations={len(out['violations'])}, duplicate_rows={out['duplicate_rows']}")
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
