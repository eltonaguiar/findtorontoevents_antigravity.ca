"""Hard/soft CI gate for per-asset quality floors."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from audit_trail.quality_monitor import (
    QUALITY_GATE_MODE,
    build_summary,
    evaluate_violations,
    load_payload,
)


def main() -> int:
    payload_path = Path(
        os.getenv("ASSET_QUALITY_PAYLOAD", "audit_trail/data/dashboard_payload.json")
    )
    payload = load_payload(payload_path)
    summary = build_summary(payload)
    violations = evaluate_violations(summary)
    report = {
        "mode": QUALITY_GATE_MODE,
        "payload": str(payload_path),
        "violations": violations,
        "summary": summary,
    }
    out_path = Path("audit_trail/data/asset_quality_gate_report.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    if not violations:
        print("Asset quality gate: PASS (no violations)")
        return 0

    print("Asset quality gate violations:")
    for v in violations:
        print(f"- {v}")
    if QUALITY_GATE_MODE == "hard":
        print("QUALITY_GATE_MODE=hard -> failing job")
        return 1
    print(f"QUALITY_GATE_MODE={QUALITY_GATE_MODE} -> warnings only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
