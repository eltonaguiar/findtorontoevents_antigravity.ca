# Extended Look — Part 2 Plan

**Author:** GitHub Copilot / Mercury-3 AI (`githubcopilot-mercury3AI`)
**Date:** 2026-11-22 03:30 EST
**Surface:** `antigravity_review_Nov192026` (+ source repo `findtorontoevents_antigravity.ca`)
**Predecessor:** Part 1 (2026-11-22) — per-asset-class deep-dives + GHA QA framework (merged to `main`, PR #3).

---

## Why Part 2

Part 1 produced the verdict matrix and a QA framework. Part 2 asks the next, *actionable* questions: **given the gates all fail, what specifically is blocking each class, what would it take to promote a pod, and how do we fix the measurement so the gates can be trusted?** It also executes the deepest untapped data — the **forward-observation clock** — which is the only path to PROVEN.

---

## Part 2 deliverables

| # | Deliverable | Source data | Target |
|---|---|---|---|
| P2-1 | Forward-clock deep-dive (all 430 forward rows) | `reports/forward_observations.jsonl`, `audit2_forward.json`, `audit3_ledger.json.forward_gate` | `28_MERCURY3_.../PART2_FORWARD_CLOCK.md` |
| P2-2 | Cross-source reconciliation matrix (ledger vs dashboard per class) | `audit3_ledger.json` vs `dashboard_data.json` | `28_MERCURY3_.../PART2_RECONCILIATION.md` |
| P2-3 | Measurement-fix engineering spec (CRYPTO intrabar, ETF slippage, FOREX price backfill) | Part 1 findings | `28_MERCURY3_.../PART2_MEASUREMENT_FIXES.md` |
| P2-4 | Full GHA QA audit report (real fleet) + remediation actions | `gha-framework/audit_workflows.py` run on source repo | `28_MERCURY3_.../gha-framework/gha_qa_audit_2026-11-22.md` |
| P2-5 | Pod-to-PROVEN acceptance checklist (what each pod needs) | `audit2_pods.json`, `forward_gate` | `28_MERCURY3_.../PART2_POD_PROMOTION.md` |

---

## Execution order

1. **P2-1 Forward clock** — parse `forward_observations.jsonl` (430 rows, all CRYPTO/H-119); compute net expectancy, benchmark coverage, intrabar-touch share, symbol concentration; state why no pod can promote yet.
2. **P2-2 Reconciliation** — build a per-class table comparing ledger (authoritative) vs dashboard `asset_class_health` / `performance.by_asset_class`; quantify drift; demote any dashboard num that diverges.
3. **P2-3 Measurement fixes** — write concrete engineering spec with file pointers for the three measurement blockers.
4. **P2-4 GHA QA** — run `audit_workflows.py` against the source repo, capture full report, list the 7 flagged workflows + exact remediation.
5. **P2-5 Pod promotion checklist** — per pod: current rows, missing rows, gate requirements, and the exact blocker to clear.

## Success criteria

- All 5 Part 2 docs exist under `28_MERCURY3_PER_CLASS_REVIEW_2026-11-22/`.
- Part 2 docs pushed to `antigravity_review_Nov192026` via a PR to `main`.
- COMS updated with Part 2 findings.
- Every number in Part 2 traces to a cited data file (no recalled stats).

---
*Not investment advice. Measurement-first, evidence-first.*
