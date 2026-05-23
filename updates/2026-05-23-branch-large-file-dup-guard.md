# 2026-05-23 Branch Large File Duplicate Guard

## Goal

Flag and block risk patterns where large files are duplicated across multiple non-main branches.

## What was added

- New GitHub Actions workflow:
  - `.github/workflows/branch-large-file-dup-guard.yml`

## Policy behavior

- Runs on every push to non-main branches.
- Also supports manual `workflow_dispatch` with controls:
  - `min_size_mb` (default: 20)
  - `min_branch_copies` (default: 3)
  - `fail_on_findings` (default: true)
- Fetches branch refs and scans tree entries (does not require full blob download).
- Flags repeated large blobs when the same blob SHA appears in at least N non-main branches.
- Writes a run summary and uploads `branch_large_blob_findings.json` as an artifact.
- Fails the run by default when findings exist.

## Why this helps

- Detects the exact failure mode that caused historical repo bloat:
  repeated large artifacts spreading across branch history.
- Gives early branch-level feedback before those artifacts proliferate.
- Keeps branch hygiene enforceable with configurable thresholds.
