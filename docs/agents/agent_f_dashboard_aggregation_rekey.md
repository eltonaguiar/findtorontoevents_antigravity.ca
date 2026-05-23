# Agent F — Dashboard Aggregation Re-Key on (source_system, strategy)

## Task

Re-key `collect_strategy_leaderboard` in `audit_trail/dashboard_generator.py`
to aggregate closed-picks forward stats on `(source_system, strategy)` tuples
so that distinct feeder systems emitting picks with the same strategy tag no
longer get silently summed into one leaderboard row.

## PR

`fix/dashboard-aggregation-rekey` — "fix(dashboard): re-key leaderboard
aggregation on (source_system, strategy) tuple". Follow-up to PR #160.

## Files modified

- `audit_trail/dashboard_generator.py` — re-key forward-closed aggregation
  inside `collect_strategy_leaderboard`; add per-(source_system, strategy)
  rows to the leaderboard; update pick enrichment at `_fwd_by_sys_strat`
  call-site to prefer composite `source_system::strategy` lookup before
  falling back to the legacy name-keyed lookup.
- `audit_dashboard/template.html` — update `buildStratLookup` and
  `resolveLeaderboardRow` to index and prefer a parallel `__bySysStrat__`
  lookup keyed on `source_system::strategy`, so the per-pick tooltip
  resolves to the correct per-system row instead of the contaminated
  by-name aggregate.
- `tests/test_dashboard_aggregation_collision.py` — new regression test
  that synthesizes two picks (SYS_A/X/+1%, SYS_B/X/-1%) and asserts the
  leaderboard emits two independent rows instead of one summed row.
- `docs/agents/agent_f_dashboard_aggregation_rekey.md` — this file.

## Why (root cause + fear_greed example)

Agent C's forensic report `docs/forensics/fear_greed_contrarian_collapse_2026-04-13.md`
(PR #160) showed that the dashboard's "st_fear_greed_contrarian 80.9% WR /
584 wins / +1042.91 PnL" headline was NOT produced by the real paper-trading
strategy `paper_trading/strategies/fear_greed_contrarian.py` (which has only
ever fired ~62 picks on its BTC/ETH/SOL/BNB/XRP whitelist, 25.8% WR lifetime,
PF 0.605). The headline came from `claude_gainer_st` picks on APT/UNI/DOT/SOL/OP,
emitted under the same `strategy` tag, and aggregated alongside the real
picks in `collect_strategy_leaderboard` because the aggregation bucketed on
`strategy` alone (`strats[name]`, `audit_trail/dashboard_generator.py:8019`).

Same-tag / different-system collisions are a systemic bug class: any two
feeder systems that happen to emit the same strategy string silently feed
into one WR/PnL/PF row. The fix is to aggregate on the tuple
`(source_system, strategy)` so each feeder's performance is reported
independently.

## Before / after aggregation key

**Before** (Source 2 of `collect_strategy_leaderboard`):

```python
for pick in _filter_valid_resolved_picks(closed):
    name = pick.get("strategy", "")
    if not name:
        continue
    if name not in strats:
        strats[name] = { ... }          # <-- keyed on strategy alone
    s = strats[name]
    s["fwd_trades"] += 1
    s["fwd_total_pnl"] += pnl
    # wins/losses accumulated across all source_systems for this strategy
    s["systems"].add(pick.get("source_system", ""))
```

**After**:

```python
# Legacy by-name row kept for display/lookup compat (external BT /
# baby-strat / coinglass / KIMI sources merge into it).
if name not in strats:
    strats[name] = _blank_row(name)
s = strats[name]
s["fwd_trades"] += 1
# ... (unchanged legacy update)

# NEW: collision-safe (source_system, strategy) aggregation.
if sys_name:
    sys_key = (sys_name, name)
    if sys_key not in sys_strat_rows:
        sys_strat_rows[sys_key] = _blank_row(name, sys_name)
    ss = sys_strat_rows[sys_key]
    ss["fwd_trades"] += 1
    # wins/losses accumulated ONLY within this feeder system
```

The final `result` list is produced by finalizing BOTH dicts via
`_finalize_row`, so the emitted leaderboard now contains:

1. One legacy name-keyed row per strategy (carries BT + merged external
   data, `source_system=""`), plus
2. One collision-safe row per `(source_system, strategy)` pair seen in
   the closed-picks ledger (carries per-system forward stats, explicit
   `source_system` field).

Pick enrichment at the `strat_lookup` call site prefers the composite
`"{sys}::{strat}"` key when the pick has a `source_system`, so
`strat_fwd_wr`/`strat_fwd_pf`/`strat_fwd_trades` reflect the picks-own
feeder-system reality, not the cross-contaminated by-name aggregate.

## Compatibility impact

- `audit_dashboard/template.html` — `buildStratLookup` and
  `resolveLeaderboardRow` updated to carry a parallel `__bySysStrat__`
  lookup and prefer the composite key when `pick.source_system` is
  present. Legacy name-keyed tooltip lookups still work (used for
  backward-compat when a pick has no source_system).
- `dashboard_data.json` schema — NO schema changes for existing fields.
  A new `source_system` field is added to each leaderboard row (empty
  string for legacy by-name rows). All existing fields retain their
  meanings and types. Downstream readers that iterate `D.leaderboard`
  and `.find(s => s.strategy === name)` continue to work — the
  legacy by-name row is still there.
- No strategy function, filter gate, curation path, or HTML output
  schema was touched.
- No changes to `cross_aggregation/`, `alpha_engine/`, or
  `audit_dashboard/*.py` were required — none of them read the leaderboard
  payload and key on strategy name in a way that would be affected.

## Verification

`py_compile`:

```
python -m py_compile audit_trail/dashboard_generator.py
# OK
```

`pytest` (dashboard-focused):

```
python -m pytest tests/test_dashboard_aggregation_collision.py \
                 tests/test_dashboard_generator.py \
                 tests/test_dashboard_generator_regressions.py \
                 tests/test_dashboard_hc_rules.py \
                 tests/test_aggregator_quality_gate.py -q
# 40 passed
```

`pytest` (full suite):

```
python -m pytest tests/ -q
# 666 passed, 8 failed, 1 deselected (8 failures are pre-existing on
# origin/main and unrelated to this PR — verified by stashing this PR's
# diff and rerunning; same 8 tests fail on main).
```

Pre-existing failures (unchanged by this PR):

- `tests/test_hf_action_plan_tools.py::test_hf_quality_gates_config_has_action_plan_thresholds`
- `tests/test_hf_conviction_tier.py` (4 tests)
- `tests/test_regime_direction_gate.py` (2 tests, ImportError)
- `tests/test_strategy_symbol_edge_scorer.py::test_fear_greed_dot_beats_uni_elite_with_registry`
- `tests/test_tier_lifecycle.py::test_demote_low_wr`

## Scope guardrails honored

- Surgical edits only: `audit_trail/dashboard_generator.py` is ~12k
  lines; only ~80 lines changed, all contained within
  `collect_strategy_leaderboard` and one call site that builds the
  per-pick `strat_lookup`.
- No rewrite of the file.
- No touch to strategy functions, filter gates, or curation paths.
- No change to existing JSON/HTML field names. One new field
  (`source_system`) added per leaderboard row, default `""` for legacy
  rows.
- Added a NEW aggregation path (`sys_strat_rows`) alongside the old
  path (`strats`) rather than rewriting in place — per the "Special
  warning" in the dispatch, we preferred additive changes since this
  file runs every 30 minutes in production.
- Regression test written FIRST and confirmed to fail before the fix,
  then pass after.
- No other tests regressed (pre-existing failures on main remain
  unchanged).

## Follow-ups

- Audit the remaining dashboard metrics in `dashboard_generator.py` for
  the same collision pattern. `collect_system_stats` is already per-
  system, but other aggregators (`hf_decay_watchlist`, `consensus`,
  `predictions_leaderboard`, various `defaultdict(...)` buckets keyed
  by `pick["strategy"]` alone) should be reviewed with the same lens.
  `grep -n 'pick.get("strategy"' audit_trail/dashboard_generator.py`
  lists 7 other call sites worth a second pass.
- Consider propagating the `(source_system, strategy)` key through the
  upstream `alpha_engine/forward_validator.py::compute_all_strategy_stats`
  which also buckets on strategy alone (line 1199). That function writes
  `strategy_performance.json`, which is loaded as the `_sp` in
  `dashboard_generator.py:11331` and stamps `strat_fwd_wr`/
  `strat_fwd_pf`/`strat_fwd_trades` onto picks via a separate path. Out
  of scope here because it lives in a different module and has its own
  downstream consumers (meta_ensemble, elite_scorer, strong_signals,
  scoring_feedback), but it should be audited next.
- Rename the paper-trading strategy's emitted tag to an unambiguous
  namespace (e.g. `pt_fng_contrarian_v1`) and stop `claude_gainer_st`
  from reusing `st_fear_greed_contrarian` as a conviction label — per
  Agent C's recommendation #1 in the forensic report.
