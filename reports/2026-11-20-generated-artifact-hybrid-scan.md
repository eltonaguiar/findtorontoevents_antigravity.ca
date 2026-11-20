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

## Verified against the artifacts the last run actually produced

`--rev-range` run over the refresh commit the 21:14Z job pushed
(`8d8ffa8f`, 48 files changed): **42 JSON artifacts inspected, 0 hybridised**. One
(`audit_dashboard/data/pf_registry.json`, 15.9 MB) was skipped by the tool's 12 MB
cap. So the gate has been checked against real hourly output, not only a HEAD
snapshot.

## Why HTML and JSONL are deliberately out of scope

The commit loop also stages `audit_dashboard/index.html`,
`audit_dashboard/trading_blueprint.html` and `ml_gatekeeper/data/ab_history.jsonl`.
A duplicate-row rule does not survive contact with them -- measured on the clean
files at HEAD:

* `audit_dashboard/index.html` (1,438,559 bytes, 443 rows): 5 distinct duplicated
  rows, including a `<th>Quarter</th>...` header repeated **22 times** (once per
  table) and `<tr class="pass">...AltmanZDoublePrime...` repeated 22 times.
* `audit_dashboard/trading_blueprint.html` (119,642 bytes, 199 rows): 9 duplicated
  rows, including identical `SHORT` rows for SOL, BTC and ETH repeated **4 times**
  across per-portfolio tables.
* `ab_history.jsonl` is append-only: a repeated record is the log working as designed.

Duplicated markup is how these pages are built, so gating on it would be red on
every healthy run -- the same trap as the subset tallies in the JSON rule. Conflict
markers in staged HTML are already covered by
`.github/scripts/assert_no_conflict_markers.sh`, which runs in the same step.

## What this means

* No other generated artifact was hybridised by this merge or is inconsistent at HEAD.
* The check is safe as a blocking gate, which is what the workflow now does.
* A hybridised payload anywhere else in those directories will now stop the run
  instead of being pushed.
