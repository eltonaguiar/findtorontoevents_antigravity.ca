# Pod emission audit: strict against *new* phantoms (2026-11-20)

**Scope:** `tools/pod_emission_audit.py`,
`reports/pod_emission_baseline.json` (new), `.github/workflows/pod-emission-audit.yml`,
`tests/test_pod_emission_audit.py`.

## Why

The audit found 15 of 23 manifest strategies emit nothing. A warn-only guard
cannot prevent a 16th from being added, and a strict guard that fails on all 15
can never be enabled.

## What

- `reports/pod_emission_baseline.json` records the 15 known `(pod, strategy)`
  phantom pairs (measured in `docs/POD_EMISSION_AUDIT_2026-11-20.md`).
- `--strict` now fails **only** when a phantom is *not* in the baseline (or a
  class-mismatch appears), so the guard is enforceable immediately.
- `--write-baseline` regenerates the file from a live run.
- The workflow drops `|| true` and passes `--strict`.

## Verification

`pytest tests/test_pod_emission_audit.py -q` → **8 passed**, including:
known phantom is non-fatal, an unlisted phantom is reported, `baseline_from()`
round-trips to zero new phantoms, and an empty baseline treats every phantom as
new. Workflow YAML validates.
