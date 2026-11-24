"""Project the confirmatory pod manifest into the audit2 page sidecar.

`audit2.js` carried a hand-maintained copy of the pod registry, so every
manifest change needed a matching edit in JavaScript and the two drifted. This
projects `reports/audit3_confirmatory.json` into
`audit_dashboard/data/audit2_pods.json`, which the page fetches first and falls
back from.

Read-only over the manifest; writes one JSON file. No DB, no network.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MANIFEST = REPO / "reports" / "audit3_confirmatory.json"
OUT = REPO / "audit_dashboard" / "data" / "audit2_pods.json"


def project(manifest: dict) -> dict:
    pods = []
    for pod in (manifest or {}).get("pods") or []:
        pods.append({
            "id": pod.get("id"),
            "status": pod.get("status"),
            "hypothesis": pod.get("hypothesis_id"),
            "klass": " / ".join(pod.get("asset_classes") or []),
            "dir": " / ".join(pod.get("directions") or []),
            "strategies": list(pod.get("strategies") or []),
            "thesis": pod.get("thesis") or "",
            "gate": pod.get("acceptance_criteria") or "",
            "observe_reason": pod.get("observe_reason"),
        })
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "reports/audit3_confirmatory.json",
        "n_pods": len(pods),
        "pods": pods,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", default=str(MANIFEST))
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args(argv)
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    payload = project(manifest)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {out}: {payload['n_pods']} pods")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
