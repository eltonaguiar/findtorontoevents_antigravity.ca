# G8/DSR/family gates: already on main, so the "port" is a no-op (with a lock)

Requested: hand-port the G8/DSR/family gates from `fix/audit3-alpha-scope` onto a
fresh branch off main, `require_alpha` default-off.

**Conclusion: there is nothing to port.** Main already implements every gate that
branch exists to add, in a stricter form, and copying the branch over regresses the
suite. What the request asked to be true is true and is now pinned by tests.

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

Do not merge or cherry-pick `fix/audit3-alpha-scope`. Its gate work is superseded by
main; the two additive helpers above are the only salvageable parts. If its author
wants the DSR/alpha work reviewed, the useful comparison is branch *tests* vs main
*behaviour*, which is what the table above records.
