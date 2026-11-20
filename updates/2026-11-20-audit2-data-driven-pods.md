# audit2's pod registry is now data-driven (2026-11-20)

**Scope:** `tools/build_audit2_pods.py` (new),
`tests/test_build_audit2_pods.py` (new), `audit_dashboard/audit2.js`,
`.github/workflows/audit3-ledger.yml`.

## Why

`audit2.js` carried a hand-maintained copy of the pod registry. Every manifest
change needed a matching JavaScript edit, so the page could silently disagree
with `reports/audit3_confirmatory.json` — the exact "two sources of truth"
problem the review flagged.

## What

- `tools/build_audit2_pods.py` projects the manifest into
  `audit_dashboard/data/audit2_pods.json` (id, status, hypothesis, classes,
  directions, strategies, thesis, gate, observe_reason).
- `audit2.js` fetches that sidecar first and **replaces** its bundled copy; the
  bundled array remains a fallback for a missing sidecar, so the page never
  breaks.
- `audit3-ledger.yml` builds the sidecar before the forward summary and deploys
  it with the page.

Adding a pod to the manifest now updates the page automatically, with no
JavaScript edit.

## Verification

- `pytest tests/test_build_audit2_pods.py -q` → **1 passed** (projection shape,
  joined classes/directions, empty-strategy pod).
- `python3 tools/build_audit2_pods.py` → "11 pods" against the live manifest.
- `node --check audit_dashboard/audit2.js` passes; workflow YAML validates
  (11 steps).
