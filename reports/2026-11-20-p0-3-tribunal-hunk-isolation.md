# P0-3 — Isolating my hunks in `alpha_engine/audit3_tribunal.py` (2026-11-20)

## 1. The working copy was not touched

The file is the most dangerous one in the repo right now: it carries uncommitted
changes from at least two authors. Its hash was recorded before and after this
task, and no write was made to it at any point.

| | sha256 |
|---|---|
| pre  | `f5b0446e5252332f5f3a934443038e73e765f7def2583e5da4e2c68072211674` |
| post | `f5b0446e5252332f5f3a934443038e73e765f7def2583e5da4e2c68072211674` |

**Identical.** Working copy size: 2,284 lines, `git status --porcelain` → ` M`.
No `checkout`, `restore`, `stash`, `clean`, `reset`, `revert` or `apply` was run
against it.

## 2. Hunk inventory — 12 hunks, 2 MINE / 10 NOT MINE

From `git diff -- alpha_engine/audit3_tribunal.py` (461 lines, 12 hunks):

| # | Hunk header | ± | Description | Owner |
|---|---|---|---|---|
| 1 | `@@ -95,6 +95,63 @@` | +57 | Import block: `is_performance_scored_row` from `resolved_closed_view` as `_is_scored_row`, with a `RuntimeWarning`-emitting local fallback of identical logic | **MINE** |
| 2 | `@@ -102,6 +159,8 @@` | +2 | `POWER_Z = 2.8` — z for sizing a study at 80% power, two-sided 5% | NOT MINE |
| 3 | `@@ -532,8 +591,11 @@` | +6/−1(−2 net) | `load_rows()` routes rows through `_is_scored_row(r)` instead of the 3-value status deny-list | **MINE** |
| 4 | `@@ -553,6 +615,63 @@` | +57 | New `exclusion_bias_bound()` — sensitivity bound on headline mean if unscored rows are not neutral | NOT MINE |
| 5 | `@@ -670,8 +789,18 @@` | +14 | Wires `exclusion_bias_bound()` into `payload_coverage()`, adds `exclusion_bias` to payload, non-neutrality sentence | NOT MINE |
| 6 | `@@ -978,11 +1107,18 @@` | +14/−3 | `mde_pct`/`required_n` in `evaluate_cell()`: size from the declared floor, not the observed mean | NOT MINE |
| 7 | `@@ -1137,61 +1273,112 @@` | +108/−57 | Gate rework: `ALPHA_MIN_N`, `ALPHA_MIN_COVERAGE`, `demote_proven_without_alpha()`, `apply_selection_alpha_gate()` returning `dict` with scoped `_entry_lo_n()`/`_lookup()` | NOT MINE |
| 8 | `@@ -1476,10 +1663,40 @@` | +37/−3 | `ALPHA_PASSTHROUGH_KEYS` expansion + new `registry_trial_count()` | NOT MINE |
| 9 | `@@ -1517,6 +1734,14 @@` | +8 | Cumulative-DSR trial counts in `build_report()` (`n_trials_cumulative`) | NOT MINE |
| 10 | `@@ -1526,6 +1751,12 @@` | +6 | Per-cell `dsr_cumulative` / `dsr_cumulative_n_trials` / `dsr_survives_cumulative` | NOT MINE |
| 11 | `@@ -1647,6 +1878,17 @@` | +11 | `require_alpha` capping when alpha has `n` but no CI | NOT MINE |
| 12 | `@@ -1932,11 +2174,21 @@` | +15/−5 | Registry counters in the output payload + `registry_note` text | NOT MINE |

Count: **2 MINE, 10 NOT MINE** — as expected.

## 3. Attribution verdict

**UNATTRIBUTED — no evidence found.**

What was checked (read-only):

- `git log --follow` on the file: recent history is a mix of `eltonaguiar`,
  `Kilo`, and `github-actions[bot]` — but that is *committed* history, not the
  author of the uncommitted hunks.
- `git status --porcelain` — only ` M`, no index markers, no author metadata.
- `git reflog` — no entry names the working-tree edit.
- Corroborating artifacts found for the non-mine work (they describe it, none
  names an agent):
  - `updates/2026-11-20-publish-mde-per-class.md` (`POWER_Z`, per-class MDE)
  - `updates/2026-11-20-exclusion-bias-bound.md` (`exclusion_bias_bound`)
  - `updates/2026-11-20-dsr-cumulative-trial-count.md` (`registry_trial_count`, `dsr_cumulative`)
  - `tests/test_exclusion_bias_bound.py`
  - `reports/2026-11-20-self-audit.md` discusses entanglement with "another agent's work" but does not name it.
  - `plans/2026-11-20-remediation-plan.md` references all of the above symbols.

Confidence that these 10 hunks are *not* mine: **high**. Confidence in *who*
they are: **zero — not guessed.** The repo has no CODEOWNERS, and uncommitted
hunks carry no authorship field; the docs prove the work happened, not who did it.

## 4. What I must do next

- Commit **only** `reports/patches/2026-11-20-phase-a-tribunal-hunks.patch` on a
  branch built from `HEAD`, applying it to the pristine file — or integrate it
  through the normal P0-4 commit process, after the other agent's work is
  resolved.
- Validate the patch by line counts and a clean `git apply --stat` (done:
  `62 insertions(+), 2 deletions(-)`), then let P0-4 own the commit.

## 5. What I must NOT do

- Never commit the working-copy file — it would include 10 hunks from another author.
- Never `git checkout --`, `restore`, `stash`, `clean`, or `reset` this file.

## 6. What would be lost if someone ran `git checkout -- alpha_engine/audit3_tribunal.py` right now

All 10 uncommitted non-mine hunks, i.e. unrecoverable working-tree work:

1. `POWER_Z = 2.8` and the power-correct `mde_pct`/`required_n` sizing in `evaluate_cell()` (non-circular study sizing).
2. `exclusion_bias_bound()` (~57 lines) — the bound on how far the headline moves if the ~41% unscored book is non-neutral — plus its wiring into `payload_coverage()` and its `exclusion_bias` payload key.
3. The G8 gate rework (~165 lines): `ALPHA_MIN_N=20`, `ALPHA_MIN_COVERAGE=0.50`, `demote_proven_without_alpha()`, and `apply_selection_alpha_gate()` now returning a summary `dict` with scope-aware `_entry_lo_n()`/`_lookup()` (strategy vs class-proxy vs class) and coverage checks.
4. `ALPHA_PASSTHROUGH_KEYS` expansion and `registry_trial_count()` (~40 lines) — cumulative DSR trial counting from the pre-registered registry.
5. Cumulative-DSR fields (`dsr_cumulative`, `dsr_cumulative_n_trials`, `dsr_survives_cumulative`) per cell, the `require_alpha` capping for alpha without CI, the registry counters in the payload, and the `registry_note` documentation.

None of it is committed, so a single checkout would silently restore the file
to `HEAD` and nothing on disk would remember this work. (My own 2 hunks would
also vanish — but they are replayable from the patch above; the 10 are not.)
