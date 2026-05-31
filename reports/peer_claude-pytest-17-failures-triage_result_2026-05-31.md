# Result — INCIDENT_OVERALL #34 (P1) pytest 17 failures triage

**Date:** 2026-05-31
**Status:** DONE (docs-only PR; no test/production fixes shipped)

## What I did

1. Verified live failures via `gh run view 26703676949 --log-failed` (full log saved to `/tmp/ci_failures.txt`, 6,288 lines). Confirmed exactly 17 FAILED in the short-summary block. No `test_confluence.py` failures despite incident note — already fixed by PR #115 (commit `fa2be8f6d`).
2. Built failure inventory across 6 test files, captured test-fixture context for each cluster.
3. Sent Mimo `mimo-v2.5-pro` (Xiaomi token-plan endpoint) a structured prompt asking for P/T/F/M classification + per-failure operator-review flagging. Response ID `06a678782f9549f2a3aff5e7c4df5794`. Full verbatim consult saved.
4. Independently verified Mimo's load-bearing claims:
   - `ml_gatekeeper/ab_router.py:38` default IS flipped to `"1"` (Mimo correct, Cluster C is real).
   - `hyrotrader_closed_picks.json` has both writer (`tools/hyrotrader_closed_picks_emitter.py:42`) AND reader (`tools/build_pf_registry.py:593-619`) — Cluster E safe-fix is validated.
   - Suspect rogue gate for Cluster A is the source-concentration gate added in commit `a043dc575` (Tier-0 P0 2026-05-17).
5. Shipped docs-only PR via server-side `gh api` (no local commits).

## Files in PR

- `reports/peer_claude-pytest-17-failures-triage_2026-05-31.md` — deliverable: classification table, verification of Mimo's claims, recommended order-of-fix with operator gates, reproducer commands.
- `reports/peer_claude-pytest-17-failures-triage_plan_2026-05-31.md` — pre-work plan.
- `reports/peer_claude-pytest-17-failures-triage_mimo_consult_2026-05-31.md` — full verbatim Mimo prompt + response.

## Before / after

- **Before:** 17 pytest failures on main; no consolidated triage; risk of any agent shipping a "fix" that flips ab_router or outcome resolver behavior without sign-off.
- **After:** Documented 5-cluster root-cause map. Cluster E (1 test) flagged SAFE; Clusters A/B/C/D (16 tests) flagged NEEDS-OPERATOR-REVIEW with specific git-diff investigation commands. Critically, `ab_router.AB_ENABLED` default flip (Cluster C) is now visible — silent ML A/B production enablement was previously buried in a CI red-line.

## AI-consult MD path

`reports/peer_claude-pytest-17-failures-triage_mimo_consult_2026-05-31.md`

## PR

Server-side branch `docs/pytest-17-failures-triage-mimo-2026-05-31` off origin/main, 3 files added under `reports/`. PR URL in shell output.

## DONE
