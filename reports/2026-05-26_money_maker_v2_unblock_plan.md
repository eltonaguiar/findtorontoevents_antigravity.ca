---
title: Money-Maker-Ready v2 — Unblock Plan
date: 2026-05-26
author: Claude Opus 4.7 (1M)
status: v2 — swarm-reviewed (deepseek + kilo, 2026-05-26 14:59 UTC)
swarm_review: swarm_runs/second-opinion-20260526T145100Z/
related:
  - reports/money_ready_verdict_2026-05-17.json
  - audit_dashboard/data/money_ready_verdict.json (2026-05-24 07:24 UTC, ~46h stale)
  - https://findtorontoevents.ca/audit/incidents.html (13 P0 + 8 P1 open)
  - CLAUDE.md "MAJOR GOAL #1"
---

# Money-Maker-Ready v2 — Unblock Plan

## TL;DR

`/money-maker-readyv2` cannot produce a real-money filter today. Two hard blockers:

1. **Canonical data missing.** `audit_dashboard/data/dashboard_data.json` does not exist at the path the skill requires. Only stale copies under `signal_aggregator/`, `tmp/`, `trading/`, `KIMI_CLAW_RESEARCH_FEB162026/`.
2. **Verdict stale.** `money_ready_verdict.json` is from 2026-05-24 07:24 UTC (~46h). Skill threshold is 2h.

Plus 13 P0 + 8 P1 open incidents whose nature (PnL mismatch on 38.97% of closed picks, trust_score NULL on 99.99%, signal_outcomes 82d stale, validator pathway frozen 270h) means any number the filter would consume is unreliable.

This plan unblocks the audit in **three serial phases** (data trust → dashboard regen → filter run), each with a hard exit criterion.

## Why each blocker matters to v2

| v2 input | Blocked by | Effect if we ignore |
|---|---|---|
| `asset_class_health.{n,WR,PF}` | P0 #4 PnL mismatch on 38.97%, P0 #5 WON rows avg pnl_pct = -41.1%, P0 #6 56,559 ghost rows | WR/PF wrong on ~4/10 rows + n inflated → false Tier-2 PASS possible |
| `walkforward.by_class.oos_*` | P0 #10 signal_outcomes 82d stale, P0 #7 validator path frozen 270h | OOS is not actually OOS; backtest leakage indistinguishable |
| `elite_score≥60` filter step | P0 #8 trust_score NULL on 99.99% closed | Filter is undefined |
| Recency panels (14d/48h) | P1 #2 "Signal Time" is file-age, not pick-age | "0 closed in 48h" claim may be a labelling artefact |
| DSR/SPA gates | P1 #4 CRYPTO ML DSR≥0.9995 on n=25–34 | Overfit-on-tiny-n is being rubber-stamped |

## Phase 1 — Restore data trust (P0 #4, #5, #6, #7, #8, #10)

**Exit criterion:** `signal_outcomes` table written within the last 2h; `trust_score` populated on ≥80% of closed picks in the last 7d; WON rows have avg `pnl_pct > 0`.

### 1.1 Diagnose the "frozen 270h" claim
- `alpha-engine-live.yml` is green every ~2h (last run `26450458490` at 2026-05-26 13:19 UTC). So the freeze is **inside** the validator job, not at the scheduler.
- Action: pull last 5 runs' logs, grep for `signal_outcomes`, `trust_score`, and the section that writes per-pick outcomes. Identify whether the freeze is (a) MySQL writeback, (b) a silently-caught exception, or (c) a code path that was removed.
- File: `alpha_engine/forward_validator.py` + the workflow's `--full-cycle` invocation.
- Output: `reports/2026-05-26_forward_validator_freeze_diagnosis.md`.

### 1.2 PnL integrity (P0 #4, #5)
- Run a one-shot recompute over `at_signal_outcomes` (MySQL mirror landed in `cc4159888`) joined against `trading_picks`, flag rows where `sign(pnl_pct)` disagrees with `status`.
- Do **not** mass-mutate. Write the diff to `reports/2026-05-26_pnl_status_disagreement.csv`, sample 20 by hand to determine root cause (resolver bug vs. label bug vs. data import).
- Patch the resolver only after the sample confirms a single deterministic cause.

### 1.3 Ghost rows (P0 #6)
- `select count(*) from trading_picks where ...` query to characterise the 56,559 rows (which strategy, which date range, NULL on which key cols).
- If they are pre-2026 stragglers from a migration, mark them `archived=1` rather than delete — preserves audit history.

### 1.4 trust_score backfill (P0 #8)
- Identify the writer that was supposed to populate `trust_score`. Likely `audit_trail/quality_gates.py` or `smart_picks_engine.py`.
- Re-run it against the last 30d of closed picks as a backfill job (not in the live cycle).

### 1.5 signal_outcomes 82d staleness (P0 #10)
- This is the same root cause as 1.1. Resolution of 1.1 likely fixes this. Verify after 1.1 lands.

## Phase 2 — Regenerate the canonical dashboard data (skill prerequisite)

**Exit criterion:** `audit_dashboard/data/dashboard_data.json` exists, `generated_at` within 2h, `asset_class_health.n == n_resolved` (post-M-067 invariant), drift report shows no class moved >5% WR between this regen and the 2026-05-24 baseline (or, if it did, the move is explained by Phase 1 fixes).

- Identify the generator that writes the canonical file. CLAUDE.md says **do not run dashboard generators locally**. So this must run in CI.
- Workflow: `.github/workflows/audit-dashboard.yml`. Force a manual `workflow_dispatch` after Phase 1 lands.
- Verify the output:
  ```bash
  python3 -c "import json; from pathlib import Path; from datetime import datetime, timezone; d=json.loads(Path('audit_dashboard/data/dashboard_data.json').read_text()); age=(datetime.now(timezone.utc)-datetime.fromisoformat(d['generated_at'].rstrip('Z')).replace(tzinfo=timezone.utc)).total_seconds()/3600; print(f'age_h={age:.2f}'); assert age<2"
  ```
- If the generator no longer writes to `audit_dashboard/data/dashboard_data.json` (path drift since the skill was written): file a follow-up to update the skill instead of "fixing" by symlinking a stale copy.

## Phase 3 — Run the v2 filter

**Exit criterion:** `reports/weekly_filter_<UTC>.md` produced with each per-class section either (a) meeting the v2 success criterion or (b) explicitly marked "INSUFF / FAIL — no filter recommended for real money this week" with the specific blocking metric.

Honest expectation given current state: **0/6 classes will pass**. The deliverable is the per-class failure narrative + the Kelly sizer ready to consume the next clean cycle. That is still useful — it sets the watermark and proves the gating works.

Steps:
1. Re-read `asset_class_health` from the fresh dashboard_data.json.
2. Per class with `resolved_n ≥ 50`: derive top filter (strategy × direction × confidence bucket).
3. Run `alpha_engine/kelly_position_sizer.py::compute_position_size()` for each surviving filter.
4. Write `reports/weekly_filter_2026-05-26.md` with per-class status + DO-NOT-SIZE banner where applicable.
5. Cross-check current OPEN picks against each surviving filter.

## Phase 1.5 — Swarm-merged additions (2026-05-26 review)

The two-engine swarm review (deepseek + kilo) flagged seven gaps. Merging them in as explicit work-items rather than free-text:

1. **Incident causal graph (before Phase 1.2).** Build a dependency map of the 13 P0 + 8 P1 — does the 270h validator freeze (P0 #7) cascade into P0 #4/#5 (PnL mismatch), P0 #8 (trust_score NULL), and P0 #10 (signal_outcomes stale)? If yes, one fix resolves four. Output: `reports/2026-05-26_incident_causal_graph.md`.
2. **Per-phase wall-clock SLA.** Phase 1: 48h target. Phase 2: 6h after Phase 1 exit. Phase 3: 4h after Phase 2 exit. If Phase 1 slips past 72h, re-scope.
3. **Rollback owner + criteria for Phase 2.** If `audit-dashboard.yml` regen fails or produces drift >5% WR vs the 2026-05-24 baseline on any class, halt and re-diagnose; do not symlink stale data to pass the gate. Owner: this Claude session (or whichever instance is on the merge-captain seat at the time).
4. **Post-backfill validation gate.** Before Phase 2 starts: `trust_score IS NULL` on closed picks resolved in last 7d must drop below **1%** (was: ≥80% populated; now: ≤1% null — same idea, tighter wording per swarm).
5. **Blast-radius sweep beyond known P0s.** Sample 200 closed picks from the 270h freeze window across non-PnL fields (Sharpe, MDD, OOS_WR, walkforward.by_class) and diff against the same picks' pre-freeze snapshot. If divergence exists on fields other than PnL, expand Phase 1 scope.
6. **Stakeholder comm plan.** Single status post on `updates/index.html` framed as "Smart-Picks filter paused for data-integrity remediation; ETA 72h" — no per-incident table (`/audit/incidents.html` already exposes that). Insert ABOVE the `<!-- AUTO-INJECTED:INCIDENTS-ENHANCEMENTS:START -->` marker per CLAUDE.md, FTP-deploy via `python3 tools/deploy_audit_files.py --only updates`.
7. **Verify non-CRYPTO resolver coverage + verdict-UX state before Phase 3.** Kilo flagged these specifically. Likely overlap with `cc4159888` (at_signal_outcomes MySQL mirror) — verify and dedupe before doing new work.

## Phase 4 — Backlog (do not block Phase 3)

P1 #2 (Signal Time = file age), P1 #3 (Swarm Picks tab abandoned), P1 #5/6/7 (EQUITY scanner routing), P1 #8 (forex_carry allowlist), P0 #11 (COT over-emission), P0 #12 (FOREX LONG block — already enforced per CLAUDE.md), P0 #13 (COMMODITY 11.9% WR — needs deep-dive per CLAUDE.md MAJOR GOAL #1 process).

## What NOT to do

- ❌ Do **not** symlink one of the non-canonical `dashboard_data.json` copies to satisfy the freshness gate. Stale-but-renamed is worse than missing.
- ❌ Do **not** add to `BLOCKED_ASSET_STRATEGY_PAIRS` without `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` + `docs/MUTATION_THREE_AXIS_PROTOCOL.md` exports.
- ❌ Do **not** size up any class on historical numbers without verifying 14d/48h panels first (CLAUDE.md hard rule).
- ❌ Do **not** publish a "weekly filter" with non-blank sizing recommendations for any class while P0 #4, #5, #8 remain open.
- ❌ Do **not** push without `git pull --rebase` first; do **not** run dashboard generators locally.

## Rollback plan

Phase 1 patches (PnL recompute, trust_score backfill, ghost-row archive) must be feature-flagged or run as one-shot scripts that only **write** if a `--apply` flag is passed; default is dry-run that emits a diff CSV. If any phase widens the divergence in `fwd_vs_bt_divergence.rows` by >10%, revert and re-diagnose.

## Open questions for swarm review

1. Is the resolver freeze (P0 #7) likely upstream of the PnL mismatch (P0 #4/#5), or are they independent? Order matters — fixing the resolver while bad rows are present could amplify rather than fix.
2. Should `trust_score` backfill use the **historical** smart-score weights at pick-emission time, or recompute under the **current** weights? Former is honest; latter risks lookahead bias contaminating the elite_score filter.
3. Given P0 #2 says `smart_picks_engine` weights confidence at 35% and inverts the ranker — should Phase 1 include a ranker-weight audit before trust_score is repopulated? Otherwise we backfill against a known-broken weighting.
4. Is `audit_dashboard/data/dashboard_data.json` actually the canonical path, or has the generator's output path drifted? If drifted, where is the new path?
5. Is there a precedent for publishing a "no-filter-this-week" weekly report, or will that be read as a system failure rather than honest gating?

## Acceptance criteria (machine-checkable)

- [ ] `signal_outcomes` MAX(updated_at) within 2h of now
- [ ] `trust_score IS NOT NULL` on ≥80% of closed picks resolved in last 7d
- [ ] `audit_dashboard/data/dashboard_data.json` exists, `age_h < 2`, `asset_class_health.n == n_resolved` per class
- [ ] `reports/2026-05-26_pnl_status_disagreement.csv` < 5% of closed-pick rows
- [ ] `reports/weekly_filter_2026-05-26.md` exists and every class section has a status verdict line
- [ ] All Phase 1 commits land on `main` via PR (no direct pushes)
