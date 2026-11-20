# Root cause: the refresh merged the labels away, then pushed the hybrid

**Date:** 2026-11-20
**Artifact:** `audit_dashboard/data/anti_overfit_audit.json` (`/audit/anti_overfit.html`)
**Commit that shipped the damage:** `c4a0acd` — *"Merge branch 'main' of …"*, author `github-actions[bot]`, 20:46:41Z

## What was seen

Six minutes after the PROBATION labels were published (`publication_labelled_at` 20:24:23Z), the artifact on `main` held:

| | value |
|---|---|
| rows | 81 |
| rows carrying a label | 77 |
| `n_strategies_audited` | 80 |
| `publication_label_counts` (stated) | `PUBLISHABLE 6 / PROBATION 74` |
| unlabelled rows | `commodity_rsi_divergence`, `luxalgo_confluence`, `regime_mild_bear`, `metals_mean_reversion` |
| duplicated row | `regime_mild_bear` (two byte-identical copies) |

`n` and `dsr` were byte-identical between the labelled and unlabelled copies, so nothing had been recomputed. My first reading — "some writer re-emits rows without labels" — was half right and pointed at the wrong layer.

## The writer is `git merge`, not Python

`c4a0acd` has two parents:

- `e303b41` — the refresh commit: 80 rows, **0** labelled, generated 20:30:43Z
- `6ca0bb7` — `main`: 80 rows, **80** labelled, labelled 20:24:23Z

The workflow does not rebase; it commits first and then merges, deliberately:

```yaml
# .github/workflows/audit-dashboard.yml (PHASE 2)
git pull --no-rebase --no-recurse-submodules -X ours --no-edit origin main
```

That is a **line-based three-way text merge** over a generated JSON file. Git does not know the `strategies` array is a list of records; it merges hunks. Reconstructing the merge reproduces the damage exactly:

```
$ git merge-file --stdout parent1 base parent2     # 7 conflicting hunks
$ …resolve each conflict with "ours" (-X ours)…
SIMULATED -X ours: rows=81 labelled=77 gen=2026-11-20T20:30:43.318454+00:00
ACTUAL   c4a0acd:  rows=81 labelled=77 gen=2026-11-20T20:30:43.318454+00:00
simulated unlabelled rows: ['commodity_rsi_divergence', 'luxalgo_confluence',
                            'metals_mean_reversion', 'regime_mild_bear']
simulated duplicate names: ['regime_mild_bear']
```

Same rows, same four unlabelled names, same duplicate, same timestamp. The four rows are precisely where the labelled side's hunk no longer applied (their `n`/`pf` lines had changed in the refresh, so the label insertions could not land), and `regime_mild_bear` is where both sides' hunks overlapped and `-X ours` kept both copies. The header fields came from *their* side (`publication_labelled_at`, counts `6/74`) while `generated_at` came from ours — which is why the payload claimed 74 PROBATION over rows that no longer all carried labels.

## Why the check did not catch it

The verification I added ran *before* the commit and merge:

- sidecar (`--min-n 20`) → `apply_dsr_probation_labels.py --apply` → `--check`, at workflow lines 283-284
- commit at line 969
- `git pull -X ours` at line 1006
- push at line 1038

So the labels were correct, then a merge damaged them, and the damaged file was pushed with no verification in between. A check that runs upstream of the write is not a check on the published artifact.

## Fix

1. **Verify after the merge** (`.github/workflows/audit-dashboard.yml`, inside the retry loop, immediately before the push): re-run `--apply`, then `--check`, then commit the repair as part of the same push. `--check` failing exits the step, so a hybrid cannot be pushed silently again.
2. **Make the hybrid visible to the checker** (`tools/apply_dsr_probation_labels.py`):
   - `--check` now reports any strategy name that appears more than once, and whether the copies are identical (a merge artefact) or contradictory (a real conflict);
   - `--check` now reports a payload whose row count disagrees with `n_strategies_audited` — the exact `81 vs 80` signature;
   - `--apply` collapses only *byte-identical* copies, leaving the surviving row and its `n` untouched, and **refuses** when two same-name rows disagree, because choosing between two contradictory claims is a human decision.
3. The artifact is healed in this commit: 81 rows → 80, all labelled, `n_strategies_audited` matching the row count.

Deduplication is not the demotion this pipeline forbids. A PROBATION strategy keeps its row, its `n` and its place; the collapse only removes a second *copy of the same row* that the merge duplicated, so the payload stops counting that strategy twice.

## Verification

- `tools/apply_dsr_probation_labels.py --check` exits 0 on the healed artifact (`80 rows, {'PUBLISHABLE': 6, 'PROBATION': 74}`).
- `--check` exits 1 on the pre-fix artifact (`c4a0acd`), naming the duplicate and the `81 vs 80` mismatch.
- `tests/test_publication_labels_consistency.py` gains four cases: duplicate reported, row-count mismatch reported, exact copy collapsed with `n` intact, disagreeing copies refused.
- The merge reproduction above (`git merge-file` + `-X ours` resolution) is the evidence that the writer is the pull, not a Python emitter.

## Lesson

For a generated artifact that several runs rewrite, a **textual** merge is a writer. It can invent rows, drop fields and splice two versions together while every script that touched the file did the right thing — and the only place to catch it is after the merge and immediately before the push. "The file is generated, so it must be consistent" is exactly the assumption a line-based merge breaks.
