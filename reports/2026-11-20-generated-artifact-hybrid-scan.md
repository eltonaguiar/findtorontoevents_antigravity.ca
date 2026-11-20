# Did the `-X ours` merge hybridise anything else?

Date: 2026-11-20. Follows `updates/2026-11-20-label-drift-root-cause.md`, which
established that the writer behind the PROBATION-label drift was the audit-dashboard
workflow's own `git pull --no-rebase -X ours` -- a line-based three-way merge over
generated JSON -- not any Python emitter.

## Scope

The hourly job commits a fixed list of generated artifacts (`for f in ...; do git
add "$f"; done` in `audit-dashboard.yml`). Expanded against `origin/main` that list
is **262 JSON files**. 251 were inspected; 1 was skipped for exceeding the 4 MB read
cap of this scan.

## Method

`tools/detect_merge_hybrid.py`. A payload is called hybridised when it contradicts
itself:

* a count field **that names its array** (`n_strategies_audited` for `strategies`)
  disagrees with the array's length by 1-5 rows, or
* a row appears byte-identically twice.

## Result

| revision | inspected | hybridised |
|---|---|---|
| `origin/main` (HEAD) | 251 | **0** |
| `c4a0acd` (the merge behind the drift) | 251 | **1** |

At HEAD nothing trips at all. At `c4a0acd` exactly one artifact does, and it is the one
we already knew about:

```
audit_dashboard/data/anti_overfit_audit.json
  strategies: declares n_strategies_audited=80 but holds 81 rows
  strategies: 'regime_mild_bear' appears 2 times with differing values
```

So the merge damaged one artifact, not a class of them.

## The per-strategy artifacts, individually

* `audit_dashboard/data/ma_strategy_leaderboard.json` -- clean
* `audit_dashboard/data/ma_strategy_signals.json` -- absent
* `audit_dashboard/data/strategy_tribunal_latest.json` -- absent
* `alpha_engine/data/walkforward_results.json` -- clean
* `audit_dashboard/data/hyro_backtest_results.json` -- clean
* `audit_dashboard/data/hyro_live_strategies.json` -- clean
* `audit_dashboard/data/pf_registry.json` -- clean
* `audit_dashboard/data/effective_n_report.json` -- clean

## Why the gate had to be narrowed before it could block anything

The first cut compared *every* `n*` field to the nearest array's length. On a clean
HEAD it flagged **172 of 251** artifacts -- a gate that would have failed the hourly
job on every run. The false positives were all the same mistake, treating a **subset
tally** as a **row count**:

* `audit_dashboard/data/money_ready_archive/*.json` -- `classes.CRYPTO.top_sleeves`
  holds 5 rows while `n_fdr_pass=4` and `n_spa_pass=2` say how many of those 5
  cleared a test.
* `audit_dashboard/data/pick_summary_stats_48h.json` -- `by_class.FUTURES.picks`
  repeats `commodity_momentum` 8 times legitimately, once per setup; a repeated name
  is only a hybrid signal when a count also disagrees.

The rule now: a count is only compared with an array whose name it carries, and a
repeated name only fails when a count problem exists too or the copies are verbatim.
That took clean HEAD to 0 findings while still catching the merge.

## What this means

* No other generated artifact was hybridised by this merge or is inconsistent at HEAD.
* The check is safe as a blocking gate, which is what the workflow now does.
* A hybridised payload anywhere else in those directories will now stop the run
  instead of being pushed.
