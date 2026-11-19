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
OUT = REPO / "audit_dashboard" / "data" / "audit2_forward.json"


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
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {OUT}: rows={n} hypotheses={len(by)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
