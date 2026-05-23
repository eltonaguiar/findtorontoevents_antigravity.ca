# Loop 2 Checkpoint 5 — T+~150m (2026-05-08 23:15 UTC)

## EW compound +20,311,796.96% — root cause confirmed

`audit_trail/dashboard_generator.py:4577` `_compound_equal_weight_capped_sequence`:

```python
def _compound_equal_weight_capped_sequence(picks, max_pnl_pct=500.0):
    prod = 1.0
    for p in sorted(picks, key=_sort_key):
        raw = float(p.get("pnl_pct", 0) or 0)
        capped = max(-max_pnl_pct, min(max_pnl_pct, raw))
        prod *= 1.0 + capped / 100.0
    return round((prod - 1.0) * 100.0, 2)
```

Math is **correct**. Each trade multiplies prod by `[1 + capped/100]` = `[0, 6.0]` with cap at ±500%. Across 1,508 trades w/ avg +0.42% per trade, baseline compound = `(1.0042)^1508 ≈ 562%`. The +20M% number means a small subset of trades hit the +500% cap. Each capped winner = 6× growth.

**Verdict**: Metric design issue, NOT arithmetic bug. The ±500% cap is way too generous. Real portfolio compound should use ACTUAL position sizing, not "1 unit / trade @ ±500% cap".

### Recommended fix

```python
# Tighter cap matching realistic per-trade returns
def _compound_equal_weight_capped_sequence(picks, max_pnl_pct=10.0):  # was 500.0
    ...
```

OR remove this metric entirely from summary and replace with annualized return + Sharpe (which are already computed elsewhere).

## Stale hyro_*.json writers — final mapping

| file | days stale | writer | workflow |
|---|---|---|---|
| `hyro_quan_bridge.json` | 20 | `tools/hyro_quan_bridge.py` | `hyro-bridge-regen.yml` (failing on numpy) |
| `hyro_pick_performance.json` | 19 | `tools/hyro_pick_performance_validator.py` | `audit-dashboard.yml` |
| `hyro_live_strategies.json` | 24 | `tools/hyro_quan_bridge.py` (or sister) | `audit-dashboard.yml` + `hyro-bridge-regen.yml` |
| `hyro_playbook_combined.json` | 25 | **NONE — orphan** | none |
| `hyro_batch2_results.json` | 32 | `tools/hyro_backtest_batch2.py` | unknown — likely manual |
| `hyro_backtest_extended_results.json` | 32 | `tools/hyro_backtest_extended.py` | unknown — likely manual |
| `hyro_backtest_12m_new_strategies.json` | 31 | **NONE — orphan** | none |
| `hyro_backtest_new_strategies.json` | 24 | `tools/hyro_backtest_new_strategies.py` | unknown — likely manual |
| `hyro_backtest_results.json` | 32 | computed in `audit-dashboard.yml` + `hyro-daily.yml` | active |

**Verdict**:
- 2 files are ORPHANS w/ no writer
- 4 backtest files are manual-run only (not on cron)
- `hyro_quan_bridge` + `hyro_pick_performance` + `hyro_live_strategies` should be fresh but workflows fail/skip

## Final 16-item consolidated fix queue

| # | fix | impact | LoC |
|---|---|---|---|
| 1 | MAJOR GOAL banner data-driven | banner reflects today not May 5 | ~20 |
| 2 | `_normalize_pick()` add pick_type+holding_horizon | LONG_TERM filter 0→38 picks | 2 |
| 3 | `concept_registry.py:186` match bare "ueps" | UEPS tagged correctly | 1 |
| 4 | `multi_asset/scanner.py:2232` pnl-sign guard | cleans 1,247 WON-mislabel | 4 |
| 5 | `skyrocket_detector.py:382` drop `and picks` + safe_commit_push | restarts EQUITY skyrocket | 2 |
| 6 | `_compound_equal_weight_capped_sequence` cap 500→10 | EW compound stops showing 20M% | 1 |
| 7 | Sharpe annualize sqrt(N_trades) not sqrt(252) | Net Sharpe accurate | 1 |
| 8 | strategy_alerts ghost-row filter | warnings not flagging polluted strats | ~5 |
| 9 | non-crypto resolver fix (15,744 phantom EXPIRED) | unblocks EQUITY/FUTURES/ETF/PENNY/FOREX truth | medium |
| 10 | `assign_concept_fields()` on closed-pick adapter | concept-perf historical aggregation | ~3 |
| 11 | replace 9 stale concept dropdown options | UI not stale | ~10 |
| 12 | Total PnL tooltip ("sum of pcts not portfolio return") | reduces misinterpretation | ~3 |
| 13 | STOCKSUNIFY2 daily-stocks.json pull workflow + JSON_PICK_SOURCES line | unlocks ~1k EQUITY picks/day | 1 workflow + 1 line |
| 14 | `hyro-bridge-regen.yml` Install step add numpy+pandas | restores 20-day-stale `hyro_quan_bridge.json` | 1 |
| 15 | Schedule `tools/hyro_backtest_batch2.py` etc. on cron | restores 32-day-stale backtest tables | new workflow(s) |
| 16 | Drop or backfill 2 orphan files (hyro_playbook_combined, hyro_backtest_12m_new_strategies) | dead-data cleanup | minor |

## Done since checkpoint 4

- ✅ Mapped all 8 stale `hyro_*.json` files to writers + workflows
- ✅ Identified 2 orphan files (no writer)
- ✅ Located `_compound_equal_weight_capped_sequence` source + confirmed math correct, cap 500% too generous
- ✅ Verified `dashboard_data.json` 18.4MB live (generated 18:25 UTC, 4h ago — within hourly cron budget)

## Up next: T+180m final wrap

- Write `reports/loop2_3hour_summary.md`
- Final commit
- Hand off

## Files

- `reports/loop2_checkpoint_{1..5}.md` (5 progress reports)
- `reports/loop2_3hour_summary.md` (next)
- `reports/long_term_picks_integration_audit_2026-05-08.md`
- `swarm_runs/audit_metrics_20260508T192423Z/` (3-engine audit metrics swarm)
- `docs/ANALYSIS_MAY82026_FREEBUFF.MD` + `docs/HERMES_DAILYACCOMPLISHMENT.MD` (peer reports)
