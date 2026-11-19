# G8/DSR/family gates: already on main, so the "port" is a no-op (with a lock)

Requested: hand-port the G8/DSR/family gates from `fix/audit3-alpha-scope` onto a
fresh branch off main, `require_alpha` default-off.

**Conclusion: there is nothing to port.** Main already implements every gate that
branch exists to add, in a stricter form, and copying the branch over regresses the
suite. What the request asked to be true is true and is now pinned by tests.

**Attribution correction (2026-11-19T18:2x, after reading COMS).** Main did not
arrive at these mechanisms independently: kilo landed them as its own hand-port in
`6abfa22364e` (verified `git merge-base --is-ancestor` = YES) plus the explainer
`77718be66922`. So the branch `fix/audit3-alpha-scope` is superseded by *its own
author's port*, not by unrelated work, and the praise for the design belongs there.
This does not change the conclusion — nothing to port — but the earlier wording
("main independently arrived") was wrong and is corrected here.

## Evidence that main already has the gates

Branch: 4 commits, 1,176 insertions across 14 files
(`3dfa66e356e`, `b9dd4378e65`, `3844a4e34e2`, `7ba21e907cd`).

Checked symbol by symbol on `origin/main` (`ac0a8be3362` → later merges):

| mechanism | main |
|---|---|
| `GLOBAL_TRIAL_FLOOR` | `alpha_engine/audit3_tribunal.py:130` = 658 |
| `global_trial_count()` (floor at registry size) | `:139` |
| `n_trials_local` (bucket-width DSR) | `:841`, used `:1019-1025`, `dsr_local` published |
| `deflated_sharpe()` | present |
| `apply_selection_alpha_gate()` | `:1310` |
| scope rules: `by_strategy` → `strategy`, slice/class → `class_proxy` | `:1316-1361` |
| `by_strategy` published in the sidecar | `ALPHA_PASSTHROUGH_KEYS` `:1291` |
| `require_alpha` parameter | `:1533`, **default `False`** |
| published CLI path opts in | `:2017` passes `require_alpha=True` |
| G9 2x-cost stress as a *required* gate | `tests/test_audit3_expectancy_gates.py:118` |
| denylist watchdog workflow | `.github/workflows/audit3-denylist-watchdog.yml` present |
| forward-observations ingest | `.github/workflows/forward-observations-ingest.yml` + `alpha_engine/forward_observations_ingest.py` present |

Main's own audit3 suite: **196 passed, 8 skipped.**

## Evidence that porting it would be a regression

Three attempts, measured rather than assumed:

1. **Cherry-pick trial.** `git cherry-pick -n 3dfa66e356e` conflicts immediately on
   `alpha_engine/audit3_tribunal.py`, `alpha_engine/forward_observations_ingest.py`
   and `tests/test_audit3_expectancy_gates.py`. Aborted, nothing kept.
2. **Branch tests as contract.** Copying the branch's own test files onto main
   produced 3 failures — but they fail because the branch tests encode an *older*
   API (`alpha_gate["status"]` and `need_n` do not exist on the branch, while main
   has both), not because main lacks the behaviour.
3. **Hand-patch of the three "gaps".** I added the branch's `beta_dominant` flag on
   the fail-closed path, and its 2x-cost demotions for PROVEN_T2 and CANDIDATE.
   Result: **17 failed, 55 passed** against a **72 passed, 0 failed** baseline. The
   edits double-applied a gate main already enforces and changed publish-path
   semantics (`"beta_dominant" not in cell` is asserted for positive class alpha).
   Reverted; suite green again.

That last measurement is the whole argument: a port cannot be validated by and
makes things worse. So the correct outcome is no code change.

## What the branch has that main genuinely does not

Not part of the asked scope, listed so it is not lost:

* `alpha_engine/audit3_edge_hunt.py` — `required_n_mde()` and `power_analysis()`
  (per-class net-pnl SD and pre-declared-MDE sample size), plus `_dir_key`/`_strat`
  helpers.
* `copy_trader_intel/multi_asset_copytrader_scraper.py` — a `classify(feats, …)`
  regime classifier.

Both are additive analysis helpers rather than correctness gates; they should come
in as their own small PRs with tests, not smuggled in with the gate work.

## What was added here instead

`tests/test_audit3_g8_defaults.py` (4 tests), which pins the two properties that
make these gates honest and that a future refactor could quietly flip:

* `require_alpha` defaults to **False** for library callers (an audit helper must
  not be able to halt emitters);
* the published CLI path passes **`require_alpha=True`** (the published ledger must
  not call an unmeasured alpha "proven");
* a strategy cell proven only by class alpha demotes to CANDIDATE with
  `scope=class_proxy`;
* a same-scope strategy measurement still promotes.

Verified: 4 passed, and the full sweep `pytest tests/ -k "audit3 or selection_alpha
or expectancy"` remains 196 passed / 8 skipped plus these 4.

## How to proceed with the branch

Do not merge or cherry-pick `fix/audit3-alpha-scope` — kilo's own port at
`6abfa22364e` is the canonical version and is already on main. Peer review answered
on COMS (Q1 scope, Q2 the 658 floor, Q3 require_alpha signalling, Q4 ingest race).

### Q2 addendum — the DSR floor, measured (supersedes an earlier draft of this file)

An intermediate version of this doc claimed the "n=120 → DSR 0.83" figure did not
reproduce. That was wrong: it reproduces once the row set matches. Reproduced with
kilo's own `_rows` helper against main's `deflated_sharpe` (`DSR_THRESHOLD = 0.95`):

| row set | n | mean net % | `dsr(658)` | `dsr(bucket=3)` | PROVEN? |
|---|---|---|---|---|---|
| `_rows(40, 80, 3.0, -0.6)` | 120 | +0.600 | **0.800** | 1.000 | no |
| `_rows(50, 100, 3.0, -0.6)` | 150 | +0.600 | 0.994 | 1.000 | yes |
| `_rows(70, 140, 4.0, -0.6)` | 210 | +0.933 | 1.000 | 1.000 | yes |
| 4.0/−0.6 at 1/3 win | 120 | +0.933 | **0.968** | 1.000 | yes |

So the floor is doing exactly what it should — the *same* n can pass or fail
depending on the payoff shape — and "a 4.0/−0.6 cell needs n≥200" is true only for
the specific mean/SD of the tested rows. The implication for the tests is the
useful part: assert `deflated_sharpe(...)` directly at a known row set instead of
only resizing 120→210, because a resize silently changes what a verdict test is
about. The 658 floor itself and the PROVEN/CANDIDATE tier split are both correct. Its gate work is superseded by
main; the two additive helpers above are the only salvageable parts. If its author
wants the DSR/alpha work reviewed, the useful comparison is branch *tests* vs main
*behaviour*, which is what the table above records.
