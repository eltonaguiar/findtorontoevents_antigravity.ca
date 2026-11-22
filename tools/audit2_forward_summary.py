"""Aggregate reports/forward_observations.jsonl into the audit2 page sidecar.

Output: audit_dashboard/data/audit2_forward.json

2026-11-21 (collective review): the sidecar published bare counters, so the page
could not distinguish three different things:

  * ``benchmark_leg: 343`` of ``n: 430`` -- a 79.8% coverage shortfall (the
    ledger's actual disqualifier), not an independent count;
  * ``intrabar: 430`` -- every row was intrabar-resolved (a boolean), not 430
    intrabar events;
  * ``H-119`` -- owned by no registered pod, while all six registered pods had
    zero forward rows.

The join against ``audit2_pods.json`` and the audit3 ledger's ``forward_gate`` is
done here so the page renders labelled facts instead of raw counters. Legacy keys
(``n``, ``benchmark_leg``, ``intrabar``, ``pods``) are preserved for consumers.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "reports" / "forward_observations.jsonl"
PODS = REPO / "audit_dashboard" / "data" / "audit2_pods.json"
LEDGER = REPO / "audit_dashboard" / "data" / "audit3_ledger.json"
OUT = REPO / "audit_dashboard" / "data" / "audit2_forward.json"

MIN_N = 100
MIN_BENCHMARK_COVERAGE = 0.9


def _load(path: Path) -> dict | None:
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def _iter_rows(lines: Iterable[str]) -> list[dict]:
    rows: list[dict] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def summarize(rows: list[dict], pods: list[dict] | None = None,
              forward_gate: dict | None = None,
              *, generated_at: str | None = None) -> dict:
    """Pure aggregation. No file IO, so the page sidecar is testable offline."""
    pods = [p for p in (pods or []) if isinstance(p, dict)]
    gate_h = (forward_gate or {}).get("hypotheses") or {}
    gate_pods = (forward_gate or {}).get("pods") or {}

    by: dict[str, dict] = {}
    n_rows = 0
    for row in rows:
        n_rows += 1
        hid = str(row.get("hypothesis_id") or "?")
        b = by.setdefault(hid, {"n": 0, "benchmark_leg": 0, "intrabar": 0,
                                "pods": set()})
        b["n"] += 1
        if row.get("benchmark_leg_ret") is not None:
            b["benchmark_leg"] += 1
        if row.get("intrabar_first_touch") is True:
            b["intrabar"] += 1
        if row.get("pod"):
            b["pods"].add(str(row["pod"]))

    # Which registered pods claim each hypothesis? The registry is the only
    # place a pod -> hypothesis mapping exists.
    hyp_to_pods: dict[str, list[str]] = {}
    for pod in pods:
        hid = str(pod.get("hypothesis") or "")
        pid = str(pod.get("id") or "")
        if hid and pid:
            hyp_to_pods.setdefault(hid, []).append(pid)

    out: dict[str, dict] = {}
    orphans: list[str] = []
    for hid, b in by.items():
        n = b["n"]
        bench = b["benchmark_leg"]
        intra = b["intrabar"]
        coverage = (bench / n) if n else None
        gate = gate_h.get(hid) if isinstance(gate_h.get(hid), dict) else {}
        registered_owners = sorted(hyp_to_pods.get(hid, []))
        row_pods = sorted(b["pods"])
        owners = sorted(set(registered_owners) | set(row_pods))
        owned = bool(owners)

        reasons: list[str] = [str(r) for r in (gate.get("reasons") or [])]
        if not owned:
            reasons.append("no registered pod owns this hypothesis -- its rows "
                           "cannot promote anything")
        if n < MIN_N:
            reasons.append(f"n {n} < {MIN_N} forward rows")
        if coverage is not None and coverage < MIN_BENCHMARK_COVERAGE:
            reasons.append(f"benchmark_leg_ret coverage {coverage:.0%} < "
                           f"{MIN_BENCHMARK_COVERAGE:.0%}")
        if intra < n:
            reasons.append(f"{n - intra} of {n} rows are not intrabar-resolved")

        # `eligible` is the ledger's decision when it has one; otherwise this is
        # a descriptor ("gate_ready"), never a promotion.
        gate_ready = bool(gate.get("eligible")) if "eligible" in gate else (
            owned and n >= MIN_N and intra == n
            and (coverage or 0) >= MIN_BENCHMARK_COVERAGE)
        if not owned:
            orphans.append(hid)
        status = ("orphan — no pod owns this hypothesis" if not owned else
                  "gate-ready" if gate_ready else "accruing")

        out[hid] = {
            "n": n,
            "benchmark_leg": bench,
            "intrabar": intra,
            "pods": row_pods,
            "benchmark_coverage_pct": (round(100.0 * coverage, 1)
                                       if coverage is not None else None),
            "intrabar_all": bool(n and intra == n),
            "owned_by_pods": owned,
            "registered_owner_pods": registered_owners,
            "gate_ready": gate_ready,
            "status": status,
            "reasons": reasons,
            "net_pf": gate.get("net_pf"),
            "pf_ci_lb": gate.get("pf_ci_lb"),
        }

    registered_hypotheses = sorted(hyp_to_pods)
    pods_without_rows = sorted({pid for hid in registered_hypotheses
                                if hid not in by for pid in hyp_to_pods[hid]})
    return {
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "n_rows": n_rows,
        "min_n": MIN_N,
        "min_benchmark_coverage_pct": MIN_BENCHMARK_COVERAGE * 100,
        "by_hypothesis": out,
        "orphan_hypotheses": sorted(orphans),
        "pods_without_rows": pods_without_rows,
        "hypotheses_without_rows": [h for h in registered_hypotheses if h not in by],
        "sources": {
            "rows": "reports/forward_observations.jsonl",
            "pods": "audit_dashboard/data/audit2_pods.json",
            "gate": "audit_dashboard/data/audit3_ledger.json (forward_gate)",
        },
        "note": ("Forward rows are per hypothesis. A hypothesis with no "
                 "registered pod can never promote; a registered pod with no "
                 "rows has no forward evidence."),
    }


def merge_gate(payload: dict, ledger: dict | None) -> dict:
    """Fold the ledger's forward-gate verdict into each hypothesis row.

    The gate already computes exactly why a pod cannot promote (benchmark
    coverage, PF CI-LB, IR). Without this the page can only say "accruing",
    which tells a reader nothing about what is actually missing.
    """
    gate = ((ledger or {}).get("forward_gate") or {})
    hyps = gate.get("hypotheses") or {}
    pods = gate.get("pods") or {}
    rows = payload.get("by_hypothesis")
    if not isinstance(rows, dict):
        rows = payload["by_hypothesis"] = {}
    for hid, g in hyps.items():
        b = rows.setdefault(hid, {"n": 0, "benchmark_leg": 0, "intrabar": 0,
                                  "pods": []})
        b["gate"] = {
            "eligible": bool(g.get("eligible")),
            "reasons": list(g.get("reasons") or [])[:3],
            "benchmark_coverage": g.get("benchmark_coverage"),
            "pf_ci_lb": g.get("pf_ci_lb"),
            "ir": g.get("ir"),
            "n_forward": g.get("n_forward"),
        }
    for pid, g in pods.items():
        hid = g.get("hypothesis_id")
        if not hid:
            continue
        # A pod with 0 rows is exactly the case the page must name, so create
        # the row rather than only annotating hypotheses that already have rows.
        b = rows.setdefault(hid, {"n": 0, "benchmark_leg": 0, "intrabar": 0,
                                  "pods": [pid]})
        b.setdefault("gate", {
            "eligible": bool(g.get("eligible")),
            "reasons": list(g.get("reasons") or [])[:3],
            "pf_ci_lb": g.get("pf_ci_lb"),
            "ir": g.get("ir"),
            "n_forward": g.get("n_forward"),
        })
    payload["gate_enforced"] = bool(gate.get("enforced"))
    return payload


def main() -> int:
    rows: list[dict] = []
    if SRC.exists():
        rows = _iter_rows(SRC.read_text(encoding="utf-8").splitlines())
    pods_doc = _load(PODS) or {}
    ledger = _load(LEDGER) or {}
    payload = summarize(rows, pods_doc.get("pods") or [],
                        ledger.get("forward_gate") or {})
    payload = merge_gate(payload, ledger)
    payload["sources"]["pods_generated_at"] = pods_doc.get("generated_at")
    payload["sources"]["gate_generated_at"] = ledger.get("generated_at")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {OUT}: rows={payload['n_rows']} "
          f"hypotheses={len(payload['by_hypothesis'])} "
          f"orphans={payload['orphan_hypotheses']} "
          f"pods_without_rows={len(payload['pods_without_rows'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
