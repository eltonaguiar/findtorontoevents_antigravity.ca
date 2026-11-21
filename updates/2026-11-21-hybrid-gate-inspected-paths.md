# Hybrid gate report: newest entry keeps its inspected paths

**Date:** 2026-11-21
**Files:** `tools/detect_merge_hybrid.py`, `tests/test_detect_merge_hybrid.py`,
`audit_dashboard/anti_overfit.html`

## What was missing

#1036 made the gate commit `audit_dashboard/data/hybrid_gate_report.json`, but an
entry only carried the *count* of artifacts inspected. `inspected: 43` says how much
was gated, not *what*: a file silently absent from the sweep (renamed, moved out of
`--under`, skipped by the cap) left no trace, and the job log is gone after an hour.

## What changed

1. **Schema 2, `inspected_paths` on the newest entry.** `record()` takes the list of
   paths actually parsed and stores it on the entry it writes. `REPORT_MAX_PATHS = 500`
   bounds it; anything beyond is reported as `inspected_paths_truncated`, so a
   truncation is visible rather than silent (43 real paths ≈ 2.8 KB).
2. **Older entries rotate down to counts.** Before appending, `record()` removes
   `inspected_paths`/`inspected_paths_truncated` from *all* existing entries. Stripping
   every entry (not just `entries[0]`) keeps the operation idempotent: writing the same
   entry twice still produces identical bytes, so the workflow's `git diff --quiet`
   guard cannot manufacture a commit per retry. A test pins this.
3. **`anti_overfit.html` shows it.** A "Merge-hybrid gate coverage" panel reads the
   sidecar client-side and shows the newest run's gated count, phase and verdict, the
   last *clean* entry's count, the skipped-over-cap list, findings, and a collapsible
   list of the inspected paths. If the sidecar is not deployed yet the panel says so
   instead of failing.

## Verification

- `python3 -m pytest tests/test_detect_merge_hybrid.py -q` → **23 passed** (4 new:
  newest keeps paths, older rotate to counts, rotation is retry-byte-identical, path
  cap counts the excess).
- Live run over `8f01ba22ce7c^..8f01ba22ce7c` with the workflow's directory set:
  `schema 2 | inspected 43 | paths 43 | verdict clean`, report **2,814 bytes**.
- `node --check` on the extracted `<script>` of `anti_overfit.html` → parses.

## Limits

- Paths describe one run only; history is counts. That is the point — the file stays
  small enough to commit every hour.
- Paths are as given to the tool (repo-relative when the workflow invokes it).
