"""Aggregate reports/forward_observations.jsonl into the audit2 page sidecar.

Output: audit_dashboard/data/audit2_forward.json
  {generated_at, n_rows, by_hypothesis: {hid: {n, benchmark_leg, intrabar, pods}}}
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "reports" / "forward_observations.jsonl"
LEDGER = REPO / "audit_dashboard" / "data" / "audit3_ledger.json"
OUT = REPO / "audit_dashboard" / "data" / "audit2_forward.json"


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
    by = {}
    n = 0
    if SRC.exists():
        for line in SRC.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            n += 1
            hid = str(r.get("hypothesis_id") or "?")
            b = by.setdefault(hid, {"n": 0, "benchmark_leg": 0,
                                    "intrabar": 0, "pods": set()})
            b["n"] += 1
            if r.get("benchmark_leg_ret") is not None:
                b["benchmark_leg"] += 1
            if r.get("intrabar_first_touch") is True:
                b["intrabar"] += 1
            if r.get("pod"):
                b["pods"].add(str(r["pod"]))
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "n_rows": n,
        "by_hypothesis": {k: {**v, "pods": sorted(v["pods"])} for k, v in by.items()},
    }
    ledger = None
    if LEDGER.exists():
        try:
            ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
        except ValueError:
            ledger = None
    payload = merge_gate(payload, ledger)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {OUT}: rows={n} hypotheses={len(by)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
