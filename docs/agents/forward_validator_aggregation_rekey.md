# Forward Validator Aggregation Re-Key (Issue #173)

## Task summary

Mirror PR #171 (dashboard-side fix) inside
`alpha_engine/forward_validator.compute_all_strategy_stats` so that
forward-test picks sharing a `strategy` tag across different
`source_system` feeders no longer cross-contaminate each other's
metrics in `alpha_engine/data/strategy_performance.json`.

## PR number

`fix/forward-validator-aggregation-rekey` — see GitHub PR opened from
this branch. Closes issue #173.

## Files modified

| Path | Reason |
|---|---|
| `alpha_engine/forward_validator.py` | Factored stats computation into `_compute_stats_from_picks` helper; added collision-safe per-`(source_system, strategy)` breakdown on every entry under `by_source_system`; taught `annotate_picks_with_forward_gate` to prefer the per-feeder row when it knows the pick's `source_system`. |
| `tests/test_forward_validator_aggregation_collision.py` | New regression test — two synthetic picks with the same `strategy` tag but different `source_system` and opposite PnL. Fails against pre-fix code; passes after. Also covers the single-feeder backward-compat case. |
| `docs/agents/forward_validator_aggregation_rekey.md` | This file. |

## Why (the 6-audit contamination story)

PR #160 identified a tag-aliasing bug in which `fear_greed_contrarian`
appeared as "80.9% WR / 584 wins" on the audit dashboard despite the
real paper-trading `fear_greed_strat` feeder only emitting ~60 picks.
Forensic revealed the 584-win inflation came from `claude_gainer_st`
picks being emitted with the same `strategy` tag and getting silently
summed into the same leaderboard row.

PR #171 fixed the dashboard side (`collect_strategy_leaderboard` in
`audit_trail/dashboard_generator.py`) by re-keying aggregation on
`(source_system, strategy)` with a legacy shim. That agent flagged a
sibling bug in `alpha_engine/forward_validator.compute_all_strategy_stats`
but kept its scope tight to the dashboard.

That sibling bug is more dangerous because `forward_validator` writes
`strategy_performance.json`, which is consumed by:

- `alpha_engine/ml_strategy_reviver.py:666` (`perf.get(strategy_name, {})`)
- `alpha_engine/auto_tuner.py:884` (`for strat_name, stats in performance_data.items():`)
- `alpha_engine/forward_validator.annotate_picks_with_forward_gate`
  itself, which stamps `forward_validated` / `forward_wr` onto every
  active pick — i.e., the gate that feeds the live ML scorer.

Between 2026-04-13 and this PR, six independent audits (DeepSeek,
Grok, Mercury, Antigravity, Cursor, Claude main) produced contradictory
"findings" from the same session because they each read from intermediate
aggregated JSONs (`strategy_performance.json` / `dashboard_data.json`)
written by this bug. Cursor self-corrected at 2026-04-13 21:44 EDT:
"Until issue #173 is resolved, every agent reading intermediate
aggregated JSONs will produce contaminated numbers." That's the
whiplash this PR eliminates at the source.

## Before / after aggregation key shape

**Before** — single bare-name aggregation:

```python
by_strategy = {}
for pick in closed_picks:
    by_strategy.setdefault(pick["strategy"], []).append(pick)
# -> one merged row per strategy name, silently summing feeders
```

**After** — dual aggregation, legacy shape preserved at top level:

```python
by_strategy[strat]                       # legacy merged aggregate
by_sys_strat[(source_system, strategy)]  # collision-safe per-feeder

# Emitted shape:
{
  "shared_tag": {
     # legacy by-name aggregate (unchanged schema)
     "closed_picks": 2, "wins": 1, "losses": 1, ...,
     # NEW fields:
     "source_systems": ["SYS_A", "SYS_B"],   # audit trail for collisions
     "by_source_system": {                   # collision-safe drill-down
        "SYS_A": {"closed_picks": 1, "wins": 1, "losses": 0, ...},
        "SYS_B": {"closed_picks": 1, "wins": 0, "losses": 1, ...},
     }
  }
}
```

The top-level dict is still keyed on bare strategy name with the same
legacy schema, so every existing consumer (see below) works without
modification. The collision-safe data is nested one level deeper and
is opt-in.

## Downstream consumer compatibility notes

| Consumer | Lookup pattern | Status |
|---|---|---|
| `alpha_engine/ml_strategy_reviver.py:666` | `perf.get(strategy_name, {})` — bare-name lookup | **Safe via shim.** Gets the merged by-name row (identical to pre-fix behavior). Can opt in to the collision-safe row later by reading `row["by_source_system"][src]`. |
| `alpha_engine/auto_tuner.py:884` | `for strat_name, stats in performance_data.items():` — iterator | **Safe.** Top-level shape unchanged; iterates the same by-name rows as before. The new `by_source_system` subkey rides along inside each `stats` dict and is ignored unless read explicitly. |
| `alpha_engine/forward_validator.py::annotate_picks_with_forward_gate` | bare-name `perf.get(strategy, {})` | **Updated.** Now prefers the collision-safe `row["by_source_system"][pick["source_system"]]` when the pick carries a `source_system`, falls back to the legacy by-name row otherwise (handles picks with no `source_system` and old on-disk `strategy_performance.json` files that pre-date the schema bump). |
| `alpha_engine/forward_validator.py::print_performance_report` | `perf.values()`, `perf.items()` (4 sites) | **Safe.** Iterates the unchanged top-level by-name rows. |
| `audit_trail/quality_gates.py` | does not touch `strategy_performance.json` | Not affected. |
| `tools/adaptive/strategy_trust.py` (PR #161) | does not touch `strategy_performance.json` | Not affected. |
| `tools/data_integrity/win_rate_wilson_ci.py` (PR #145) | does not touch `strategy_performance.json` | Not affected. |

## Verification

```
$ python -m py_compile alpha_engine/forward_validator.py \
                        tests/test_forward_validator_aggregation_collision.py
py_compile OK

$ python -m pytest tests/test_forward_validator_aggregation_collision.py -q
..                                                                       [100%]
2 passed in 1.77s

$ python -m pytest tests/test_quality_gates.py \
                    tests/test_forward_validator_aggregation_collision.py -q
................                                                         [100%]
16 passed in 1.69s
```

The new test fails against pre-fix code (confirmed before applying the
fix — it catches the missing `by_source_system` subkey) and passes
after. No adjacent quality-gate tests regressed.

## Scope guardrails honored

- Only `alpha_engine/forward_validator.py` was touched in the load-bearing
  ML scorer path. Dashboard-side code (`audit_trail/dashboard_generator.py`,
  already fixed by PR #171) was not re-touched.
- No data files were regenerated. `alpha_engine/data/strategy_performance.json`
  will be rewritten under the new schema by the next scheduled forward
  validator run — intentionally deferred to a separate data migration.
- No `BLOCKED_SOURCE_SYSTEMS` changes; no strategy kill/unblock decisions
  (those require `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` per CLAUDE.md).
- `alpha_engine/ml_strategy_reviver.py` dedup logic was NOT modified
  (that's a separate bug from PR #172 forensic — out of scope).
- Only one aggregation site was touched (the single
  `compute_all_strategy_stats` call site in `forward_validator.py`).
  No sibling aggregation functions exist in that file that need the
  same treatment.

## Follow-ups

1. **Data migration** — regenerate `alpha_engine/data/strategy_performance.json`
   under the new schema. The next scheduled forward validator run will
   do this automatically; no manual intervention required.
2. **Opt-in migration for ml_strategy_reviver.py** — teach the lookup
   at line 666 to prefer `row["by_source_system"][src]` when the pick
   has a `source_system`. Low priority — the legacy shim is already
   correct-enough for the reviver's use case, and the collision-safe
   path is already protecting `annotate_picks_with_forward_gate` which
   is the gate that actually feeds the live scorer.
3. **Wilson CI per (source_system, strategy)** — `tools/data_integrity/
   win_rate_wilson_ci.py` (PR #145) could consume `by_source_system`
   directly instead of re-deriving it from closed picks. Nice-to-have.
4. **Audit the 6 contaminated reports** from the 2026-04-13 session
   once the first re-keyed `strategy_performance.json` lands. Most of
   the whiplash between audits should resolve automatically.

## Related

- Issue #173
- PR #171 (dashboard fix, same pattern)
- PR #160 (fear_greed_contrarian forensic)
- PR #161 (adaptive strategy trust scorer)
- PR #145 (data integrity Wilson CI)
