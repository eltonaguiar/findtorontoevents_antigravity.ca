# PR Triage Merge-Success Tests — 2026-04-25

Companion to [`updates/2026-04-25-pr-triage-15-open-prs.md`](../updates/2026-04-25-pr-triage-15-open-prs.md). Test file:
[`tests/test_pr_triage_2026_04_25_merge_success.py`](../tests/test_pr_triage_2026_04_25_merge_success.py).

## Purpose

Each merged or processed PR from the 2026-04-25 triage round has a corresponding test that asserts its intended outcome is actually visible on `main`. The suite is designed to be:

- **Idempotent** — running it twice yields the same result.
- **Offline-tolerant** — tests that need GitHub API state (closed-PR checks) skip cleanly when `gh` is unavailable, so the suite can run in CI environments without GitHub credentials.
- **Surgical** — each test maps 1:1 to a PR, named `Test<NNN>_<intent>` so a failing test names the PR it represents.

## Run

```bash
pytest tests/test_pr_triage_2026_04_25_merge_success.py -v
```

To target a single PR's tests:
```bash
pytest tests/test_pr_triage_2026_04_25_merge_success.py::Test391_CIStashFix -v
```

## Coverage map

| PR | Outcome verified | Test class | Critical assertion |
|---|---|---|---|
| #391 | CI fix landed | `Test391_CIStashFix` | `git stash push` precedes the retry loop in both YAMLs |
| #391 | Caveat addressed | `Test391_CIStashFix` | `strategy_performance.json` is git-tracked (stash catches it) |
| #391 | Third pattern still safe | `Test391_CIStashFix` | `multi-asset-scanner.yml` still uses `git add -A` |
| #379 | Cancelled Markham gone | `Test379_EventsDataFix` | no event row matches `cancelled & markham` |
| #379 | Source labels unified | `Test379_EventsDataFix` | no `source: fatsoma` rows remain |
| #380 | Audit docs present | `Test380_EventDataQualityDocs` | 4 expected files exist; report >1KB |
| #387 | All 3 cap locations widened | `Test387_ForexCaps` | `0.015` / `0.008` (or `1.5%` / `0.8%`) appear in config.py; old `0.0075` not adjacent to `forex` keyword |
| #388 | MLS excluded | `Test388_MLSExclusion` | `soccer_usa_mls` in `sports_picks.php` near an exclusion keyword |
| #384 | #381 closure noted | `Test384_ReviewDoc` | doc text contains "PR #381 was subsequently closed" |
| #340 | Stayed closed, not merged | `TestClosedPRsStayClosed` | `mergedAt is None`, state is terminal |
| #363 | Stayed closed, not merged | `TestClosedPRsStayClosed` | `mergedAt is None`, state is terminal |
| #383 | Still open OR events.json restored | `TestBlockedPRsStillOpen` | if merged, both events.json files >100KB |
| #344 | Still open OR CI clean | `TestBlockedPRsStillOpen` | sanity state check |
| #382 / #378 / #348 / #314 / #372 | Owner-decision PRs | `TestPendingPRsNotPrematurelyMerged` | informational only — flags premature merges via stdout |

## Why these specific assertions

### #391 — three-line sanity
- Stash MUST be **before** the loop. If somebody puts it inside the loop or after, every retry stashes its own dirty tree and we silently start losing data.
- The contended file MUST be tracked. Copilot Cloud's primary review concern: stash-without-`-u` is a no-op for untracked/gitignored files, so the file's tracked status is the load-bearing assumption.
- The third workflow's `-A` was the basis for excluding it from the fix. If someone later refactors and drops the `-A`, that workflow inherits the same bug — the test catches that regression.

### #379 — row-level vs file-level
The PR diff was `+7 / -47` per file, not a column-level audit. The tests assert the two row-level facts the PR was actually about:
1. The cancelled Markham row is gone.
2. No event row carries `source: fatsoma` after the unification.

Both can be re-introduced by an upstream scraper later — that's a separate regression bug to catch elsewhere, not what this test covers.

### #387 — partial-widen regression detector
The historical bug pattern: TP/SL caps live in 3 places, and the **tightest** of the three silently dominates. If a future PR widens 2 of the 3, the third still pins the cap. The test asserts all 3 are widened together, and that the old `0.0075` value isn't lingering on a forex-related line.

### #388 — exclusion-not-inclusion
Naive substring match (`if 'soccer_usa_mls' in source`) doesn't tell us whether MLS is being excluded or included. The test scans for the token within 200 characters of any exclusion keyword (`exclud`, `skip`, `block`, `void`) — that's tolerant to refactors but catches an accidental flip from exclude-list to include-list.

### Closed PRs (#340, #363)
These should never merge. The test asserts `mergedAt is None`. If a future agent re-opens and merges either, the test goes red and the rationale is in the test docstring.

### Blocked PRs (#383, #344)
The dangerous case is `#383 merges`. The test handles that gracefully: if it did merge, it must have come with the events.json restoration we suggested in the blocker comment. The `>100KB` byte threshold catches "merged with the deletion still present" (the deletion would zero out the files).

## What the tests deliberately don't cover

- **CI workflow runs themselves.** Verifying that the next scheduled `Unified Audit Dashboard` run succeeds is the job of the 2026-04-26 followup agent (`trig_01X88Vr1eF1q5KZAwwUZ3czQ`), not a unit test.
- **Numerical sanity of the new forex caps.** The 1.5%/0.8% values were chosen by Ollama 2-model consensus on 1,558 closed picks — their correctness is a forward-looking question, not something a test can validate from main alone.
- **`#382` rebase status.** Once the dependency PR (#379) is on main, #382's events.json delta should disappear automatically. Verifying that is a `gh pr diff` check, deferred to the followup agent.

## Failure mode triage

| Test fails | Likely cause | Fix |
|---|---|---|
| `test_audit_dashboard_has_stash_before_retry_loop` | Someone refactored and dropped the stash | Re-apply per #391's commit, or use `git stash` differently with explicit comment |
| `test_strategy_performance_json_is_tracked` | File got `.gitignore`d or removed | Restore tracking; the stash fix breaks otherwise |
| `test_no_cancelled_markham_row` | A scraper re-introduced the cancelled row | Fix the scraper, not this PR's commit |
| `test_caps_widened_in_config` | Forex caps were narrowed again or moved | Look at recent forex-cap PRs; the historical 0.0075 default may be back |
| `test_383_still_open_or_fixed` (when merged) | Catastrophic: events.json wiped | Revert the merge commit immediately; restore from `origin/main^` |

## Independent reviewers

- GitHub Copilot Cloud (task `9a9bc21d-81df-4cf9-9f6d-0fb4fb6e5460`) — primary review, surfaced the file-tracked caveat for #391
- DeepSeek `deepseek-chat` ([`reports/consult_deepseek_20260425T064616Z_pr_triage.md`](../reports/consult_deepseek_20260425T064616Z_pr_triage.md)) — second opinion on contested calls, classified #383 as "100% accidental rebase contamination"
