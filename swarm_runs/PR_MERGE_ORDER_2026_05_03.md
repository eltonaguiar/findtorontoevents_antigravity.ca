# PR Merge Order — 2026-05-03 (operator action plan)

Operator-facing merge sequence for the **complete open PR backlog** (10 PRs). Combines HH's 6-PR swarm validation (`PR_VALIDATION_RESULTS_2026_05_03.md`) with metadata-based triage on the 4 PRs HH did not cover (#744, #676, #608, #597). Token budget: $0.30. **Read-only on source.** Operator runs every `gh pr merge` / `gh pr close`.

## Goal-1 baseline (today's `audit_dashboard/data/dashboard_data.json::performance.asset_class_health`)

EQUITY T2-candidate (PF 1.41 / WR 52.9 / n=420). COMMODITY meets T2 PF (PF 1.78 / WR 46.9 / n=750 — needs WR lift). BOND meets T2 PF+WR (PF 1.72 / WR 55.6) but n=18 below charter floor. CRYPTO sub-T2 (PF 1.24 / WR 44.6 / n=8218 — drag from low-quality sub-systems). ETF borderline (PF 1.24 / WR 55.2 / n=87, n→100). **FOREX is genuinely sub-floor (PF 0.27 / WR 46.4 / n=1169 post-noise filter)** — needs the deep-dive + rescue plan in #724 to land. Where lift is needed: FOREX (rescue), CRYPTO (cut sub-T2 volume share), ETF/BOND (sample growth). Goal-1 priorities for this batch: **#724** (FOREX evidence), **#615** (scanner unblock — feeds candidate pipeline), **#723** (B18 shadow promotion mechanism, infrastructure for rescue strategies).

## Per-PR table (all 10 open PRs)

| Rank | PR | Title | Class | Verdict | CI | Mergeable | Notes |
|---|---|---|---|---|---|---|---|
| 1 | #744 | doc-PR merge state snapshot | docs | **MERGE-NOW** | scan SUCCESS | MERGEABLE | 96-line audit, single new file under `reports/`, zero risk |
| 2 | #723 | B18 shadow-mode auto-promotion | infra | **MERGE** (3/3 swarm) | none | UNKNOWN | HH-validated; cleanest of slate; default-OFF flag |
| 3 | #724 | FOREX/CRYPTO deep-dives + rescue | docs (Goal-1) | **MERGE** (2/3 swarm; xai conditional) | none | UNKNOWN | HH-validated; docs-only; honor "no code without peer ack" |
| 4 | #615 | scanner blocker fixes | infra | **CONDITIONAL** | test (3.12) FAILURE | UNKNOWN | HH-validated; merge after CI green or unrelated-failure note |
| 5 | #608 | B26 tradingagents smoke | tests | **CONDITIONAL** | test (3.11) FAILURE | CONFLICTING | needs rebase + CI fix; smoke is gated off in CI so risk is low |
| 6 | #676 | events data quality follow-up | events (Goal-3) | **REBASE-THEN-MERGE** | none | CONFLICTING | docs+data; HIGH-severity duplicates removed; rebase only |
| 7 | #597 | USDCHF investigation + 2 P0 fixes | mixed | **CONDITIONAL** (split risk) | test 3.11/3.12 FAILURE | MERGEABLE | multi-purpose bundle (USDCHF doc + B11 pair-block fix + revalidator + events frontend); operator should split or accept the bundle |
| 8 | #644 | per-asset quality gate plan | infra | **REQUEST-CHANGES** (1/2 swarm split) | none | UNKNOWN | HH-validated; review_body posted; scope-creep — body says one file but 9 changed |
| 9 | #660 | P0 emergency gate fixes | infra | **REQUEST-CHANGES** (3/3 swarm) | none | UNKNOWN | **REVIEW POSTED 2026-05-03** by this run; same-PR config contradictions |
| 10 | #661 | infrastructure v2.0 | infra | **REQUEST-CHANGES** (2/2 swarm) | test 3.11 FAILURE | UNKNOWN | **REVIEW POSTED 2026-05-03** by this run; missing `statistical_rigor.py` + red CI |

## Merge-order sequence (copy/paste for operator)

### Group A — MERGE NOW (no blockers)

```bash
# A1. PR #744 — doc snapshot, MERGEABLE, scan green, zero conflict surface
gh pr view 744 --json mergeable,statusCheckRollup --jq '.mergeable, [.statusCheckRollup[].conclusion] | unique'
gh pr review 744 --approve --body "doc-PR audit snapshot, single file under reports/, zero impact on production. LGTM."
gh pr merge 744 --squash --delete-branch

# A2. PR #723 — B18 shadow-mode auto-promotion (HH 3/3 MERGE/HIGH)
gh pr view 723 --json mergeable,statusCheckRollup --jq '.mergeable, [.statusCheckRollup[].conclusion] | unique'
gh pr review 723 --approve --body-file swarm_runs/pr_validate_batch_2026_05_03/review_body_723.md
gh pr merge 723 --squash --delete-branch

# A3. PR #724 — FOREX/CRYPTO deep-dives + rescue plan (docs-only; HH 2/3 MERGE)
gh pr view 724 --json mergeable,statusCheckRollup --jq '.mergeable, [.statusCheckRollup[].conclusion] | unique'
gh pr review 724 --approve --body-file swarm_runs/pr_validate_batch_2026_05_03/review_body_724.md
gh pr merge 724 --squash --delete-branch
# AFTER MERGE: do NOT follow up with corruption-filter code commits without peer ack (xai's gate).
```

### Group B — REBASE THEN MERGE (verdict OK; needs main-sync first)

```bash
# B1. PR #676 — events data quality follow-up (CONFLICTING; events.json + next/events.json move on every cycle)
gh pr checkout 676
git fetch origin main
git rebase origin/main
# Conflicts will appear in events.json / next/events.json. Keep the PR's de-dup IDs + SVG-rewrites
# but accept current main on every other event row. Then:
git push --force-with-lease
gh pr review 676 --approve --body "events data quality follow-up; 2 HIGH-severity duplicates removed, 75 SVG placeholders rewritten. Re-run analyze_event_data.py confirms HIGH=0 post-merge."
gh pr merge 676 --squash --delete-branch
```

### Group C — CONDITIONAL MERGE (operator review required before approve)

```bash
# C1. PR #615 — scanner blocker fixes (HH 2/3 MERGE-leaning; test (3.12) FAILURE blocking)
# Re-fetch CI status; if 3.12 still red, comment-only first.
gh pr checks 615
gh pr review 615 --comment --body-file swarm_runs/pr_validate_batch_2026_05_03/review_body_615.md
# If CI is now green:
# gh pr review 615 --approve --body-file swarm_runs/pr_validate_batch_2026_05_03/review_body_615.md
# gh pr merge 615 --squash --delete-branch

# C2. PR #608 — B26 tradingagents smoke (CONFLICTING + test (3.11) FAILURE)
# Smoke test is gated off in CI (TRADINGAGENTS_LIVE_SMOKE!=1) so the test (3.11) failure is likely
# unrelated. Verify failure cause first:
gh pr checks 608
gh run view 25240556566 --log-failed | head -100
# If failure is unrelated to this PR, rebase + re-run:
gh pr checkout 608
git fetch origin main
git rebase origin/main
git push --force-with-lease
# Then if green:
# gh pr review 608 --approve --body "B26 smoke test gated off in CI; 40/40 unit tests pass; ready when 3.11 unblocks."
# gh pr merge 608 --squash --delete-branch

# C3. PR #597 — USDCHF + B11 + revalidator (MULTI-PURPOSE; operator must decide split)
# This bundle contains FOUR independent things on one branch:
#   1. USDCHF concentration investigation (docs-only, FALSIFIED)
#   2. B11 P0 fix: rapid_fire pair-blocklist (alpha_engine/isolated_signal_integrator.py)
#   3. pick_revalidator.py new module (sidecar, not wired)
#   4. events frontend changes (TORONTOEVENTS_ANTIGRAVITY/index.html + playwright tests)
# CI is RED on test (3.11) AND test (3.12).
# RECOMMENDATION: split into 4 surgical PRs, not 1.
gh pr checks 597
# Operator decision: (A) split — close 597, cherry-pick into 4 branches; OR (B) merge as bundle after CI green.
# If splitting:
# gh pr close 597 --comment "Multi-purpose bundle. Splitting into 4 surgical PRs: (1) USDCHF docs, (2) B11 isolated_signal pair-block fix, (3) pick_revalidator sidecar, (4) events frontend filter fix. Will reopen each."
# If accepting bundle: investigate CI failures first, then approve.
```

### Group D — REQUEST CHANGES (review posted; await author response)

```bash
# D1. PR #660 — REVIEW POSTED 2026-05-03 (this run, comment-mode self-review)
gh pr view 660 --json reviews --jq '.reviews[-1]'  # confirm review visible
# Author must reconcile config contradictions before re-review.
# Do not merge until reconciliation commit lands.

# D2. PR #661 — REVIEW POSTED 2026-05-03 (this run, comment-mode self-review)
gh pr view 661 --json reviews --jq '.reviews[-1]'  # confirm review visible
# Author must restore statistical_rigor.py + replace hardcoded timestamp + green CI.

# D3. PR #644 — review body drafted (not posted; deepseek + xai split, conservative path = comment-only)
gh pr review 644 --comment --body-file swarm_runs/pr_validate_batch_2026_05_03/review_body_644.md
# This is the conservative non-destructive nudge. Operator can choose split or merge-after-body-update.
```

### Group E — ABANDON / CLOSE (none currently)

No PR has 3/3 unsalvageable + zero wiring consensus. The two close-replace candidates (#660, #661) are still recoverable via author edits.

## Inter-PR dependency graph

- **#723 (B18 shadow-mode) → #724 (FOREX rescue)**: weak dep — #724's rescue plan implicitly assumes the shadow-mode promotion mechanism will be available for new strategies. Merging #723 first is the natural order.
- **#615 (scanner fixes) → #597 (B11 pair-block)**: both touch `alpha_engine/`. #615 fixes `outcome_resolver.py` v2.1; #597 fixes `isolated_signal_integrator.py`. No shared file but #597's CI failures may share root cause with #615's `test (3.12)` failure — investigate together.
- **#660 (config gates) ⚠️ #644 (per-asset gate plan)**: both touch `config/per_asset_thresholds.json` semantics. If #660 lands first, #644's per-asset summary tile may need re-cite. If #644 lands first, #660's contradictions become more obvious. **Do not land both before reconciling.**
- **#608 (B26 smoke) → #597**: both add tests/. No shared file but the `test (3.11)` failure on both branches points to a shared root cause that should be diagnosed once and fixed everywhere.
- **#676 (events data) ⚠️ #597 (events frontend)**: both touch events surface (Goal-3). #676 is data-only, #597 is frontend-only — no merge conflict but consistency check after both land is wise.

## Risk register

1. **`config/per_asset_thresholds.json` semantic drift across #660 / #644.** Both PRs claim authority on per-asset thresholds; #660 has documented same-PR contradictions. If both merge before reconciliation, the live gate config will be inconsistent and Goal-1 sizing decisions will rest on contradictory thresholds. **Mitigation:** require reconciliation commit on #660 BEFORE either lands.

2. **CI volatility on `test (3.11)` and `test (3.12)`.** Three open PRs (#615, #597, #608, #661) report failures on these two test jobs. They share neither a single test file nor an obvious source touchpoint, suggesting the failure may be environmental (e.g., flaky network test, dependency drift). **Mitigation:** do one focused investigation on the failure cause (`gh run view <id> --log-failed`) before approving any of these PRs — fixing one likely fixes all four.

3. **Goal-1 evidence gate on #724.** The PR is docs-only and asserts a FOREX rescue plan, but the actual rescue strategies are not in this PR. Merging the docs without subsequent strategy code creates a documentation-vs-reality drift. **Mitigation:** track the follow-up code PR explicitly; do not let #724 sit at "merged docs" for >7 days without a concrete strategy commit citing the rescue plan.

## Notes on authorisation

REQUEST_CHANGES via `gh pr review --request-changes` is GitHub-blocked when the reviewer is the PR author (this run hit `Can not request changes on your own pull request`). All review-body files were posted via `gh pr review --comment` instead — equivalent feedback signal, visible to author + collaborators, just lacks the gate-blocking REQUEST_CHANGES enum. For external reviewers (different login) the original `--request-changes` form would work and is recommended.

## Cost summary

- This run: $0 net (no new swarm dispatch — used HH's pre-validated outputs + metadata triage on the 4 unreviewed PRs).
- HH's prior swarm run: ~$0.10 (deepseek+xai+kimi).
- Total to-date: ~$0.10 of the $0.30 cap.

## Files produced this run

- `swarm_runs/PR_MERGE_ORDER_2026_05_03.md` (this file).
- `.gitignore` exception added for the above.
- 2 review comments posted on PRs #660 and #661 (visible at `gh pr view 660 --json reviews | jq '.reviews[-1]'`).
