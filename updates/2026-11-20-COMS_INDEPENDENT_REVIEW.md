# Independent Review of Audit2 & Audit3 — 2026-11-20

**Author:** Kilo
**Date:** 2026-11-20

## Executive Summary
This review evaluates the current state of the audit2 and audit3 systems based on the latest handoff and status reports. While the core logic for the gates (F1, F2, N1-N7) is correctly implemented on `origin/main`, there are several critical data integrity issues and deployment failures that must be addressed before further strategy development proceeds.

## Key Findings & Defects

### 1. Audit3 Coverage Inconsistency (P0)
- **Issue:** The ledger reports 8,605 scored rows but only 8,175 valid closed picks, resulting in an impossible 105.26% coverage.
- **Cause:** The denominator used for the percentage is not accounting for the 430-row forward gate bucket.
- **Action:** Implement `denominator_reconciliation` to ensure the headline is mathematically sound.

### 2. Audit2 Deployment Failure (P0)
- **Issue:** The CI pipeline is deploying files to `/audit/`, which results in a 404. The actual live site is at `/audit2/`.
- **Impact:** Stakeholders cannot access the audit2 methodology library.
- **Action:** Update `.github/workflows/audit-dashboard.yml` to point to the correct path.

### 3. Forward Benchmark Window (P1)
- **Issue:** Benchmark coverage is only 79.8%.
- **Cause:** A right-edge query window misses 63 of 87 null legs at each symbol's latest exit.
- **Action:** Pad the ingest query with `BENCHMARK_LOOKAHEAD_MS` and backfill the missing rows.

### 4. Candidate KPI Mismatch (P1)
- **Issue:** `n_candidate` is reported as 0 even though some symbol rows (like FOREX AUDJPY) are identified as `CANDIDATE`.
- **Action:** Introduce `n_candidate_symbols` and `n_candidate_segments` to provide more granular visibility.

### 5. Audit2 Pod Integration (P1)
- **Issue:** Six pods (H-2026-11-19-01..05) are hardcoded in the client-side JS.
- **Impact:** They are not reflected in the ledger and are not dynamic based on system state.
- **Action:** Move pod rendering to a web-served confirmatory sidecar driven by `ledger.forward_gate.pods`.

### 6. N5 Selection Alpha (P2)
- **Issue:** Alpha/hold fields exist in the code but are not published in the live ledger.
- **Action:** Enable these fields in the ledger output.

## Conclusion
The priority is to fix the coverage inconsistency and the audit2 deployment immediately. Once these are resolved, the system will be stable enough to proceed with the E3 pod rollout (equity breakout).
