# Peer-Claude Reconcile — Kilo Truth-Layer Worktree vs Today's Shipped Work

**Date:** 2026-05-31
**Worktree:** `/tmp/truth-layer-audit`
**Kilo branch (commit-tracked):** `audit-truth-layer-20260531` (2 net-new commits ahead of origin/main)
**Kilo branch (worktree-only, uncommitted):** modified `tools/edge/edge_stability.py`, new `audit_dashboard/dashboard_freshness.js`, new `.github/workflows/edge-stability-daily.yml`

## Already shipped today on `main` (recap)

PR #285 (edge-stability-refresh.yml daily 00:30 UTC cron), #287 (Truth-Layer Validation Swarm),
#291 (CORRIGENDUM), #304 (7/7 winners synthesis), #305 (Force synth), #306 (Priority shadow pilots),
#314 (Expanded hunt synthesis 60 strategies), #315 (Wilson LB correction).

## Per-agent verdict

| Agent | Report | Verdict | Notes |
|------:|--------|---------|-------|
| 1 | `agent1_dashboard_validation.md` | **NEEDS_VERIFICATION** | Detailed DB-vs-dashboard cross-check (5278/1877/WR 45.1/PF 1.16). Internally consistent; cross-validates today's PR #287/#291 numbers. Useful as redundant audit. |
| 2 | `agent2_edge_stability.md` | **NET_NEW_VALUE** | Surfaces n-discrepancy between `edge_stability.html` (1873 CRYPTO) vs `money_ready_verdict` (341 CRYPTO) — flags STABLE_EDGE labels for COMMODITY/EQUITY as polluted by backtest+sim data. Not covered by PR #285 (#285 only added cron, not source-quality audit). |
| 3 | `agent3_rolling100_audit.md` | **DUPLICATE_OF_PR_#287/#291 + minor NET_NEW** | Confirms +313.43% does NOT exist in current code (dashboard shows -41.63% rolling-100 compound, -92.95% EW compound, +571.66 raw sum). Matches today's summary exactly. NET_NEW: documents the exact formula at `dashboard_generator.py:4834-4861` and the ±10% cap reasoning. Also has supporting `rolling_100_auditor.py` script + JSON breakdown showing -0.15% recomputed + 6.8pp survivorship bias. |
| 4 | `agent4_active_picks_trust.md` | **DUPLICATE_OF_PR_#287** + opinion overlay | Reaches same DO_NOT_TRUST verdict as PR #287/#306. Adds expected-outcome dollar math but no new data. |
| 5 | `agent5_automation.md` | **NET_NEW_VALUE (uncommitted)** | Claims +133 lines added to `tools/edge/edge_stability.py` adding MySQL-direct mode (`_load_all_picks_mysql`, `--mysql`, `--max-age-days`). **VERIFIED on disk** — the worktree has the modification (+117 actual lines), but it is **not committed to the kilo branch**. Also new uncommitted workflow `.github/workflows/edge-stability-daily.yml` that uses `--mysql` flag with `MYSQL_PASSWORD` secret. **This is a real fix for the transitive-staleness bug PR #285 inherited** (PR #285 still depends on `dashboard_payload.json` curl from the live site). |
| 6 | `agent6_ml_calibration.md` | **NET_NEW_VALUE** | Confidence-inversion claim PARTIALLY VALIDATED — CRYPTO inversion has reversed since 2026-05-17 calibrator was fitted; EQUITY/FOREX inversions persist; `_calibrate_confidence()` is largely inert because most picks sit in the 0.60-0.80 dead zone. Complements [project-confidence-trust-edges-2026-05-31](memory) — does not duplicate it but adds the inertness finding. |
| 7 | `agent7_mercury_tiles.md` | **NEEDS_VERIFICATION** | Per-class tile pipeline mapping (5 distinct pipelines feeding per-class data). Useful documentation; needs cross-check before promoting. |
| 8 | `agent8_timestamps.md` | **NET_NEW_VALUE (uncommitted)** | New file `audit_dashboard/dashboard_freshness.js` (22,710 bytes on disk) — color-coded freshness panel (green<24h / yellow 24-72h / red>72h), stale-data banner, per-section inline EST badges. Not on any branch. Genuine UI feature; PR #285 only refreshes data, doesn't expose freshness to users. |

## Kilo branch committed work (only 2 commits ahead of origin/main)

1. **c5f3c1cf3** `docs(rolling-100-audit)` — `rolling_100_audit.json`, `rolling_100_auditor.py`, `updates/2026-05-31-rolling-100-verification.md` (audit deliverables, ~519 lines, supports agent3)
2. **768ded8d7** `feat(audit): M-106 Active Picks Truth Filter` — `tools/active_picks_truth_filter.py` (514 lines), `money_ready_verdict_truth_filtered.json` (168k lines), `updates/2026-05-31-active-picks-truth-filter.md`

## Top 2 net-new items to surface to operator

1. **MySQL-direct mode for edge_stability.py + matching workflow** (agent5, uncommitted). PR #285's workflow still curls `dashboard_payload.json` from the live site — if the audit-dashboard pipeline lags, edge_stability also goes stale. Kilo's `_load_all_picks_mysql()` + `--mysql` flag + `edge-stability-daily.yml` w/ `MYSQL_PASSWORD` secret breaks that dependency. Worth a small follow-up PR.
2. **`dashboard_freshness.js` per-section EST timestamps** (agent8, uncommitted). Net-new UI surfacing "how stale is this card?" — color-coded badges. Complements but does not duplicate any 2026-05-31 PR.

## Items that are duplicates / superseded

- Agent3's +313.43% finding ≡ today's session note + PR #287/#291 corrigendum.
- Agent4's DO_NOT_TRUST verdict ≡ PR #287/#306 outputs.
- Kilo's `audit-truth-layer-20260531` does NOT contain the `edge-stability-refresh.yml` shipped in PR #285 (branch was forked before #285 merged).
- Agent5's claim of "+133 lines" matches the worktree but **not** the kilo branch — file is uncommitted there.

## Recommendation

**docs-only tracking PR** + **operator decision pending** on whether to cherry-pick the 3 net-new artifacts:

- `tools/edge/edge_stability.py` MySQL-direct mode (small surgical patch, easy to validate)
- `.github/workflows/edge-stability-daily.yml` (new daily MySQL workflow — would replace or sit beside PR #285's `edge-stability-refresh.yml`)
- `audit_dashboard/dashboard_freshness.js` + template.html hooks (UI feature, larger review surface)

A full merge of the kilo branch into main is **not** recommended without first committing the 3 uncommitted files (agent5/agent8 work) and adding a PR description that distinguishes the M-106 truth-filter (168k-line JSON) from the docs-only outputs.

## Re-affirm bulletproof state

- 8 NO_EDGE sources still under verification.
- freebuff's 6 winner claims still being checked (wiha77fnj subagent in flight).
- Only CRYPTO `volatility_breakout` borderline (Wilson LB 0.5057).
- EQUITY downgraded to noise per PR #315.
- Kilo's findings do NOT contradict the bulletproof state — they add 3 new pieces of plumbing (MySQL-direct, daily yml, freshness UI) and 3 new audit reports (agent2 n-discrepancy, agent3 formula doc, agent6 inversion-inertness) that COMPLEMENT today's PRs.

## Return summary

`RECONCILE:kilo_branch_exists=true:net_new_agents=[2,3,5,6,8]:duplicates=[3,4]:tracking_PR=<pending>:operator_decision=docs-only`
