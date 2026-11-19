#!/usr/bin/env python3
"""Per-class cost gate — block picks from classes that cannot clear their costs.

Why this exists (2026-11-14 audit, final_v2/quant-audit-2026-11-14, idea #2):

  The system's own slippage validator already flags CRYPTO (39.7% of average PnL),
  FUTURES (72%), and CRITICAL for ETF (267%) and COMMODITY (422%) — meaning for
  those classes the modelled round-trip cost is larger than the entire average
  trade result. Emitting them is guaranteed loss with extra steps.

  Yet ``readiness.by_class.sizing_allowed`` was already false for all nine
  classes while the scanner kept emitting ~390 picks/month. Nothing enforced it
  at emit time.

The rule (pre-registered in the audit, stated before this was built):

  A class may emit only while its **average PnL per closed trade** is at least
  **3x** the modelled round-trip cost for that class. 3x is the margin that
  survives an optimistic cost model being wrong by half and still leaves room
  for a real edge; anything thinner is indistinguishable from noise once the
  estimator drifts.

  After-cost net is also stamped (mean_pnl - cost) so consumers can use it
  directly: that is the value of the existing ``after_cost_net_per_trade`` field.

Costs come from ``tools/data/transaction_costs.json`` (the same file
``tools/forward_edge_audit.py`` uses) — no new cost model invented here.

Policy (changed 2026-11-19 — external review v2/v3): this gate used to fail OPEN,
so a missing index, a stale index, or an unmeasured class all emitted freely. The
review's complaint is that a gate whose off-switch is "the bookkeeping broke" is
not a gate. Strict mode is now the DEFAULT:

  * missing / stale / empty index        -> BLOCK (reason `gate_index_missing_strict`)
  * class present in no index row        -> BLOCK (reason `no_class_evidence_strict`)
  * class measured but n < min_n         -> BLOCK (reason `insufficient_sample`)

Set PER_CLASS_COST_GATE_STRICT=0 to restore the old fail-open behaviour (for a
backfill run whose index has not been rebuilt yet). The escape hatch is explicit
and logged by callers via the returned `strict` field, because the failure mode
we are avoiding is a gate that is quietly off.

Usage:
    python3 tools/per_class_cost_gate.py --build --input audit_dashboard/data/dashboard_data.json
    python3 tools/per_class_cost_gate.py --build --input /tmp/peercheck/dashboard_payload.json \
        --out config/per_class_cost_gate.json
    python3 tools/per_class_cost_gate.py --report
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

COSTS_FILE = REPO_ROOT / "tools" / "data" / "transaction_costs.json"
DEFAULT_OUT = REPO_ROOT / "config" / "per_class_cost_gate.json"

#: A class must earn at least this multiple of its round-trip cost on average.
REQUIRED_COST_MULTIPLE = 3.0
#: Fail-closed by default (2026-11-19). See the policy note in the module docstring.
STRICT_DEFAULT = True


def _strict() -> bool:
    """Strict (fail-closed) mode; env override for backfill runs."""
    raw = os.environ.get("PER_CLASS_COST_GATE_STRICT")
    if raw is None:
        return STRICT_DEFAULT
    return raw.strip().lower() in ("1", "true", "yes", "on")
#: Below this many closed trades a class mean is not usable — fail open.
MIN_SAMPLE = 30
#: Index older than this is not trusted for a blocking decision.
MAX_INDEX_AGE_HOURS = 25.0


def load_costs() -> Dict[str, float]:
    """{CLASS: cost_pct} from the shared transaction-cost file."""
    if not COSTS_FILE.exists():
        return {}
    with open(COSTS_FILE, encoding="utf-8") as fh:
        data = json.load(fh)
    return {str(k).upper(): float(v["cost_pct"]) for k, v in data.get("costs", {}).items()}


def _f(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        out = float(v)
    except (TypeError, ValueError):
        return None
    return out if out == out else None


def load_closed_rows(path: str) -> List[Dict[str, Any]]:
    """Load closed rows from a dashboard payload or dashboard_data.json."""
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, dict):
        picks = data.get("picks")
        if isinstance(picks, dict) and isinstance(picks.get("recent_closed"), list):
            return [r for r in picks["recent_closed"] if isinstance(r, dict)]
        for key in ("recent_closed", "closed_picks"):
            if isinstance(data.get(key), list):
                return [r for r in data[key] if isinstance(r, dict)]
    if isinstance(data, list):
        return [r for r in data if isinstance(r, dict)]
    return []


def build_index(rows: Iterable[Dict[str, Any]], costs: Dict[str, float]) -> Dict[str, Any]:
    """Compute the per-class gate index from closed rows."""
    acc: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        pnl = _f(row.get("pnl_pct"))
        if pnl is None:
            continue  # unmeasured (None) rows must not move a class mean
        ac = str(row.get("asset_class") or "UNKNOWN").upper()
        a = acc.setdefault(ac, {"n": 0, "sum": 0.0})
        a["n"] += 1
        a["sum"] += pnl

    classes: Dict[str, Any] = {}
    for ac, a in sorted(acc.items()):
        n = a["n"]
        if n == 0:
            continue
        mean_pnl = a["sum"] / n
        cost = costs.get(ac, costs.get("UNKNOWN", 0.20))
        required = REQUIRED_COST_MULTIPLE * cost
        ratio = (mean_pnl / cost) if cost else None
        enough = n >= MIN_SAMPLE
        # allowed only when the sample is big enough AND the 3x test is met
        allowed = bool(enough and mean_pnl >= required)
        classes[ac] = {
            "n": n,
            "mean_pnl_pct": round(mean_pnl, 4),
            "cost_pct": round(cost, 4),
            "required_mean_pnl_pct": round(required, 4),
            "cost_multiple": None if ratio is None else round(ratio, 3),
            "after_cost_net_per_trade": round(mean_pnl - cost, 4),
            "sample_sufficient": enough,
            "allowed": allowed,
            "reason": (
                "passes_3x_cost" if allowed
                else "insufficient_sample" if not enough
                else "below_3x_cost"
            ),
        }
    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rule": f"class mean pnl_pct >= {REQUIRED_COST_MULTIPLE}x round-trip cost",
        "required_cost_multiple": REQUIRED_COST_MULTIPLE,
        "min_sample": MIN_SAMPLE,
        "classes": classes,
    }


_INDEX_CACHE: Dict[str, Any] = {"path": None, "mtime": None, "data": {}}


def load_index(path: Optional[str] = None) -> Dict[str, Any]:
    """Load the gate index; returns {} when missing or stale (callers fail open).

    Cached on (path, mtime): dashboard_generator stamps this per pick, so an
    uncached re-read would mean tens of thousands of file opens per build.
    """
    p = Path(path) if path else DEFAULT_OUT
    if not p.exists():
        return {}
    try:
        mtime = p.stat().st_mtime
    except OSError:
        return {}
    if _INDEX_CACHE["path"] == str(p) and _INDEX_CACHE["mtime"] == mtime:
        return _INDEX_CACHE["data"]
    try:
        with open(p, encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception:
        return {}
    if not isinstance(data, dict) or not isinstance(data.get("classes"), dict):
        return {}
    gen = data.get("generated_at", "")
    if gen:
        try:
            dt = datetime.fromisoformat(str(gen).replace("Z", "+00:00"))
            age_h = (datetime.now(timezone.utc) - dt).total_seconds() / 3600.0
            if age_h > MAX_INDEX_AGE_HOURS:
                return {}  # stale — fail open
        except (ValueError, TypeError):
            pass
    _INDEX_CACHE.update({"path": str(p), "mtime": mtime, "data": data})
    return data


def gate_pick(pick: Dict[str, Any], index: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Decide whether one pick may be emitted.

    Returns ``{"allowed": bool, "class": str, "reason": str, ...}``.
    Unknown class / missing index / thin sample → allowed (fail open).
    """
    idx = index if index is not None else load_index()
    ac = str((pick or {}).get("asset_class") or "UNKNOWN").upper()
    classes = (idx or {}).get("classes") or {}
    strict = _strict()
    row = classes.get(ac)
    if not row:
        if strict:
            # No evidence is not permission. A missing index means the gate never
            # ran; allowing the pick would make the gate's absence undetectable.
            reason = ("gate_index_missing_strict" if not classes
                      else "no_class_evidence_strict")
            return {"allowed": False, "class": ac, "reason": reason,
                    "strict": True}
        return {"allowed": True, "class": ac, "reason": "no_class_evidence",
                "strict": False}
    return {
        "allowed": bool(row.get("allowed")),
        "strict": strict,
        "class": ac,
        "reason": row.get("reason"),
        "mean_pnl_pct": row.get("mean_pnl_pct"),
        "cost_pct": row.get("cost_pct"),
        "required_mean_pnl_pct": row.get("required_mean_pnl_pct"),
        "after_cost_net_per_trade": row.get("after_cost_net_per_trade"),
    }


def stamp_class_after_cost(pick: Dict[str, Any], index: Optional[Dict[str, Any]] = None) -> bool:
    """Populate ``after_cost_net_per_trade`` / ``is_ac_survivor`` from the class index.

    Fallback for when the strategy-level B16 index has no row — which is the
    normal case: all 3,500 closed rows in the live payload carried
    ``after_cost_net_per_trade: null`` because the strategy index was absent.
    Returns True when it stamped something.
    """
    idx = index if index is not None else load_index()
    ac = str((pick or {}).get("asset_class") or "UNKNOWN").upper()
    row = ((idx or {}).get("classes") or {}).get(ac)
    if not row:
        return False
    pick["after_cost_net_per_trade"] = row.get("after_cost_net_per_trade")
    if pick.get("wilson_lb_wr") is None:
        pick["wilson_lb_wr"] = None  # class level cannot supply a strategy WR bound
    pick["is_ac_survivor"] = bool(row.get("allowed"))
    pick["class_cost_gate_reason"] = row.get("reason")
    return True


def _print_report(index: Dict[str, Any]) -> None:
    classes = index.get("classes") or {}
    if not classes:
        print("No index (missing or stale) — gate fails open, nothing blocked.")
        return
    print(f"rule: {index.get('rule')}  (min sample {index.get('min_sample')})")
    print(f"generated: {index.get('generated_at')}\n")
    hdr = f"{'class':<11}{'n':>6}{'mean%':>9}{'cost%':>8}{'3x_cost%':>10}{'mult':>7}{'net%':>9}  verdict"
    print(hdr)
    print("-" * (len(hdr) + 9))
    for ac, r in sorted(classes.items()):
        mult = r.get("cost_multiple")
        print(
            f"{ac:<11}{r['n']:>6}{r['mean_pnl_pct']:>9.3f}{r['cost_pct']:>8.3f}"
            f"{r['required_mean_pnl_pct']:>10.3f}{(mult if mult is not None else 0):>7.2f}"
            f"{r['after_cost_net_per_trade']:>9.3f}  "
            f"{'ALLOW' if r['allowed'] else 'BLOCK'} ({r['reason']})"
        )
    blocked = [a for a, r in classes.items() if not r["allowed"] and r["sample_sufficient"]]
    print(f"\nblocked by 3x-cost rule: {', '.join(blocked) if blocked else 'none'}")


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--build", action="store_true", help="build the index from closed rows")
    ap.add_argument("--input", help="dashboard payload JSON or dashboard_data.json")
    ap.add_argument("--out", default=str(DEFAULT_OUT), help="index output path")
    ap.add_argument("--report", action="store_true", help="print the current index")
    ap.add_argument("--check", help="JSON pick (inline) to test against the gate")
    args = ap.parse_args(argv)

    if args.build:
        if not args.input:
            print("--build requires --input", file=sys.stderr)
            return 2
        rows = load_closed_rows(args.input)
        if not rows:
            print(f"No closed rows in {args.input}", file=sys.stderr)
            return 2
        index = build_index(rows, load_costs())
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(index, fh, indent=2, sort_keys=True)
        _print_report(index)
        print(f"\nwrote {out} (from {len(rows)} closed rows)")
        return 0

    if args.check:
        try:
            pick = json.loads(args.check)
        except json.JSONDecodeError as e:
            print(f"bad --check JSON: {e}", file=sys.stderr)
            return 2
        print(json.dumps(gate_pick(pick), indent=2, sort_keys=True))
        return 0

    _print_report(load_index())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
