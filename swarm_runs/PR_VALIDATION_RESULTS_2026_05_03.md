# PR Validation Results — 2026-05-03

Validates the 6-PR triage from `swarm_runs/PR_TRIAGE_2026_05_03_MANUAL.md` using the FIXED inline-diff swarm pipeline (`tools/swarm/prompts/pr_review_inline.md` + `tools/swarm/_pr_capture.py`). Engines selected per task spec: kimi (OAuth, lowest fabrication rate), deepseek + xai (proven reliable on inline-diff PR review).

Run dirs:
- `swarm_runs/pr_validate_batch_2026_05_03/` — deepseek+xai for all 6 PRs (12 outputs, all HEALTHY per `swarm_inspect.py`)
- `swarm_runs/pr_validate_kimi_660/` — kimi for #660 (HEALTHY)
- `swarm_runs/new_engine_audit_20260503T175428Z/kimi/pr_723.json` — kimi for #723 (re-used from earlier today's hallucination audit; HEALTHY MERGE/HIGH)

The earlier `swarm_runs/pr_review_20260503T170445Z/` run was the **legacy non-inline pipeline** — its outputs for #723/#724/#661 were **fabricated** (described "Events Near Me" / "Event Details page" content for what are actually backend HC-gate / config / infrastructure PRs). Disregarded. The fresh fixed-pipeline run produces correctly-grounded reviews citing real `audit_trail/`, `alpha_engine/`, `config/` paths.

## Per-PR verdict table

| PR | Title | X's triage | Swarm verdict (k/d/x) | Confidence | Action |
|---|---|---|---|---|---|
| #723 | B18 shadow-mode auto-promotion | priority-merge | **MERGE / MERGE / MERGE** | HIGH | approve + merge |
| #724 | FOREX/CRYPTO deep-dives + rescue | priority-merge | (skipped) / MERGE / HOLD | MEDIUM-HIGH | approve + merge (docs-only) |
| #615 | scanner blocker fixes | priority-merge | (skipped) / MERGE / HOLD | MEDIUM | comment only; merge after CI green |
| #660 | emergency gate fixes | close-replace | **REQUEST_CHANGES / HOLD / HOLD** | HIGH | request changes |
| #661 | infrastructure modules v2.0 | close-replace | (skipped) / REQUEST_CHANGES / HOLD | HIGH | request changes |
| #644 | per-asset quality gate plan | split into 3 | (skipped) / MERGE / HOLD | MEDIUM | request changes (xai confirms scope-creep) |

`(skipped)` = kimi prompt exceeded Windows ~32K argv ceiling. The deepseek+xai pair carried consensus on those PRs.

## Disagreements with X's manual triage

### Confirmed exactly
- **#723 priority-merge** — 3/3 MERGE/HIGH. Cleanest of the slate. All concerns minor.
- **#660 close-replace** — 3/3 NOT-MERGE. All three engines independently surfaced the same three blocking config contradictions (`min_ml_score` 0.82 vs 0.90, `min_risk_reward` 1.25 vs 1.50, `max_risk_reward` 3.0 vs 2.00). Cite paths verified.
- **#661 close-replace** — 2/2 NOT-MERGE. Deepseek confirmed the missing `alpha_engine/statistical_rigor.py` (referenced by `__init__.py` + body but not in changed-files list). Plus `test (3.11)` FAILURE + `test (3.12)` CANCELLED. Stale hardcoded timestamp finding (`alpha_engine/track_calculator.py` `"generated_at": "2026-05-02T00:00:00Z"`) is a bonus catch.

### Confirmed conditionally
- **#724 priority-merge → CONDITIONAL APPROVE.** Deepseek MERGE/HIGH endorses; xai HOLD/HIGH only because the PR body explicitly says no code/gate ships without peer ack on the corruption-filter fix. Both are correct simultaneously — the PR is docs-only and merging the docs honors xai's gate. Recommendation: approve + merge but DO NOT follow with corruption-filter code commits without peer ack.

### Downgraded
- **#615 priority-merge → CONDITIONAL.** Both engines agree the work is good (5 scanner fixes, Windows-safe yfinance timeout). But `test (3.12)` is FAILURE on the head ref (xai blocking) and xai also flagged scope-creep at `alpha_engine/outcome_resolver.py:151` (v2.1 retry-cap may extend beyond stated PR scope). Recommendation: hold until CI green or failure documented as pre-existing-unrelated.

### Partial agreement
- **#644 split-into-3 → REQUEST CHANGES (1/2 splitter consensus).** xai confirmed X's exact claim: PR body states "Confirm PR only contains one file: updates/2026-05-02-per-asset-quality-gate-implementation-plan.md" but multiple files are modified. Direct scope-creep evidence. Deepseek disagreed and treated the multi-file scope as MERGE-worthy because the active-gate strictness is opt-in (`PER_ASSET_QUALITY_ACTIVE_PERMISSIVE=1` default). Operator can choose: (A) honor X's split, or (B) merge as-is after a body update + penalty-delta evidence cite.

## Notable findings (worth flagging)

1. **The legacy `pr_review_20260503T170445Z` run was 100% fabricated for these PRs.** All 5 deepseek+xai outputs in that dir described event-listing UI features ("Events Near Me", "Event Details page") for PRs that are actually backend HC-gate / config / FOREX-investigation work. This validates the task's note that "the legacy `pr_review.md` caused 100% fabrication earlier today" and confirms the FIXED inline-diff pipeline (`pr_review_inline.md` + `_pr_capture.py`) is necessary, not optional.

2. **Kimi has a hard wall on Windows for prompts >~32KB.** The kimi CLI uses `-p <prompt>` argv (per `tools/swarm/worker_runner.py:610`), and Windows enforces a ~32K argv ceiling. Prompts in this run ranged 20-66KB; only #660 (20KB) and #723 (40KB previously captured at a smaller cap) passed. Mitigation paths exist (smaller `--max-diff` for kimi-only runs; wire kimi to stdin with `--input-format text`) but are not currently in the dispatcher.

3. **All 6 PRs have `mergeStateStatus: UNKNOWN` / `mergeable: UNKNOWN`.** GitHub hasn't computed merge state for any of them; operator should re-fetch right before any `gh pr merge` to avoid surprise conflicts.

## Cost

| Engine | PRs | Tokens (approx) | $ |
|---|---|---|---|
| deepseek | 6 | ~95K | ~$0.06 |
| xai | 6 | ~76K | ~$0.04 |
| kimi | 2 | OAuth-bundled | $0 |
| **Total** | | | **~$0.10** |

Well under the $0.20 cap.

## Open questions

- Should we wire kimi to `--input-format text` + stdin so it can review larger PRs? Worth a small plumbing PR but not blocking on this run.
- The `pr_NNN_capture` files showing `flags=ZERO` in `swarm_inspect.py` are false-positive flags (those are capture sidecars, not engine outputs — they have empty raw-stdout by design). Worth a swarm_inspect.py filter update to suppress them.

## Files produced

- `swarm_runs/PR_ACTION_COMMANDS_2026_05_03.md` — operator approval queue (this is the actionable file)
- `swarm_runs/PR_VALIDATION_RESULTS_2026_05_03.md` — this file
- `swarm_runs/pr_validate_batch_2026_05_03/review_body_{615,644,660,661,723,724}.md` — per-PR review body files for `gh pr review --body-file`
- `swarm_runs/pr_validate_batch_2026_05_03/pr_{615,644,660,661,723,724}.{deepseek,xai}.json` — raw engine outputs
- `swarm_runs/pr_validate_kimi_660/pr_660.kimi.json` — kimi output for #660
