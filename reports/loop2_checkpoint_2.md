# Loop 2 Checkpoint 2 — T+~60m (2026-05-08 21:45 UTC)

Three independent audits converged in this checkpoint window:
1. Long-term picks integration audit (subagent)
2. /audit metrics accuracy swarm (deepseek + cerebras)
3. Freebuff's `docs/ANALYSIS_MAY82026_FREEBUFF.MD` (just landed, 18KB)

## Meta-finding: hardcoded vs live (final classification)

| section | status | source |
|---|---|---|
| Summary cards (WR, PnL, PF, etc.) | ✅ LIVE | `dashboard_generator.py` |
| Active/Closed pick tables | ✅ LIVE | 30+ JSON/DB sources |
| Per-asset-class health | ✅ LIVE | `asset_class_health` block |
| Walk-forward by class | ✅ LIVE | `walk_forward_by_class()` |
| Strategy warnings | ✅ LIVE | `performance_alerts.py` |
| **DB health cards (just shipped)** | ✅ LIVE | our new `db_health.json` |
| Strategy leaderboard | ✅ LIVE | backtest DB |
| Tier-2 PROVEN | ✅ LIVE | `_compute_tier2_proven_strategies()` |
| **MAJOR GOAL banner** | ❌ HARDCODED | `template.html:832-870` (May 5 snapshot, never updates) |
| **Tier definitions T1/T2/T3** | ❌ HARDCODED | static text in MAJOR GOAL banner |
| **"How to Find Edge" guide overlay** | ❌ HARDCODED | `template.html` static (n=4,618 analysis frozen) |
| **Asset class descriptions** | ❌ HARDCODED | static "EQUITY — T2 candidate", etc. |
| **PF contradiction disclosure** | ❌ HARDCODED | static warning text |

## Triple-confirmed math/data bugs

### Math
| metric | verdict | root cause |
|---|---|---|
| Total PnL +1374.45% | misleading sum-of-pct | NOT wrong arithmetic; just inappropriate metric. Should accompany w/ tooltip explaining it's a sum |
| **EW compound +20,311,796.96%** | mathematical artifact | (1.05)^1508 = 4.6e31; ±500 cap doesn't tame it across 1,508 sequential trades. Display should disclaim or remove |
| Net Sharpe 0.1233 → 1.96 ann. | conceptually wrong | uses sqrt(252) trading-days NOT sqrt(N_trades). Swarm consensus: should be 0.1233 × sqrt(N) ≈ 7.08 |
| OOS Sharpe ETF 11.4 | overfit | n=88 over 4 folds; statistically meaningless |

### Data
| issue | scope | source |
|---|---|---|
| Phantom EXPIRED non-crypto | **FOREX 5,412 + EQUITY 3,936 + FUTURES 4,920 + ETF 984 + PENNY 492 = 15,744** all 100% phantom | resolver not closing properly |
| signal_tier_writer 100% NULL | 4,940 last 7d | writer never populated |
| lm_signals_resolver 96.21% unresolved | 32,209 / 33,479 | resolver throughput gap |
| WON-with-negative-PnL | 1,247 trading_picks rows | `multi_asset/scanner.py:2232` missing pnl-sign guard (already located) |
| Concept taxonomy 2-layer bug | 38 UEPS picks tagged `standard` not `long_term_value` | `_normalize_pick()` drops `pick_type` + `concept_registry.py:186` only matches `ueps_` prefix |

## Hyrotrader inventory (read-only scan)

5 main tables on `/audit/hyrotrader`:
- Short-term entry radar
- QuanEngine Edge Tracker
- Table 2 — Live playbook signals (1h)
- Table 3 — Pick List (THE MAIN EVENT)
- Table 4 — Signal Strength + Pick Performance
- Table 5 — ML Edge Optimizer (top 10 highest-edge / best-strategy-per-symbol / bottom 5 avoid)

Plus: account snapshot, drawdown check, position size, budget snapshot, trade journal.

## Top-12 highest-leverage fixes (consolidated, prioritized by ROI)

| # | fix | file | LoC | impact |
|---|---|---|---|---|
| 1 | Make MAJOR GOAL banner data-driven (read from `asset_class_health` block) | `template.html:832-870` + JS | ~20 | Banner reflects today's PF/WR not May-5 snapshot |
| 2 | Add `pick_type`+`holding_horizon` to `_normalize_pick()` | `audit_trail/dashboard_generator.py:6961` | 2 | LONG_TERM filter shows 38+ picks (was 0) |
| 3 | Match bare `"ueps"` in concept_registry | `concept_registry.py:186` | 1 | UEPS picks tag `long_term_value` correctly |
| 4 | Apply `multi_asset/scanner.py:2232` pnl-sign guard | `multi_asset/scanner.py:2232` | 4 | Cleans 1,247 WON-mislabel + warning baselines |
| 5 | Drop `and picks` guard + apply safe_commit_push.sh | `skyrocket_detector.py:382` + `penny-skyrocket-runner.yml` | 2 | Restarts 5-day-broken EQUITY skyrocket pipeline |
| 6 | Fix EW compound: clip cap correctly OR drop metric | `dashboard_generator.py` (~line 245) | ~5 | 20M% number stops embarrassing dashboard |
| 7 | Annualize Sharpe by sqrt(N_trades) not sqrt(252) | `dashboard_generator.py` (~line 200) | 1 | Net Sharpe accurate |
| 8 | Pass ghost-row filter to strategy_alerts | `performance_alerts.py:128` | ~5 | warnings stop flagging polluted strategies |
| 9 | Fix non-crypto phantom EXPIRED resolver | universal pick resolver path | medium | unblocks 15,744 closed-pick truth |
| 10 | Wire `assign_concept_fields()` into closed-pick adapter | `dashboard_generator.py` recent_closed builder | ~3 | concept-perf aggregation works historically |
| 11 | Replace 9 stale concept-dropdown options w/ 8 real families | `template.html` | ~10 | UI not stale |
| 12 | Add Total PnL tooltip ("sum of trade pcts; not portfolio return") | `template.html` | ~3 | reduces misinterpretation |

Fixes #2+#3 alone close the long-term EQUITY UI gap (visible to user).
Fix #4 alone cleans 1,247 polluted rows.
Fix #5 alone restarts the EQUITY skyrocket emitter.
Fix #1 alone makes the banner stop showing 3-day-stale numbers.

## Cross-asset transfer candidates (from Hermes daily)

Hermes Daily Accomplishment file flagged these strategies as transferable from CRYPTO → EQUITY/FOREX:
- Hurst exponent pairs / autocorrelation reversion
- Adaptive Bollinger Momentum + VIX term structure
- Turn-of-month, put/call ratio contrarian, liquidity imbalance
- chatgpt_combined (high historical WR)

Cross-asset deficit: 48h sample shows CRYPTO 114 / EQUITY 2 / FOREX 0 picks — equity/forex severely under-served despite STOCKSUNIFY2 separate repo (110 commits, daily-stocks.json + STOCK_ALGORITHMS.md).

**STOCKSUNIFY2** is a separate sibling repo with scientific audit pipeline for long-term equity. **Worth integration into main /audit feed** per Hermes recommendation.

## Done since checkpoint 1

- ✅ Read freebuff `docs/ANALYSIS_MAY82026_FREEBUFF.MD` (18KB, 320 lines)
- ✅ Read Hermes daily file (`docs/HERMES_DAILYACCOMPLISHMENT.MD`)
- ✅ Inventoried `/audit/hyrotrader` (5 tables + supporting sections)
- ✅ Triple-converged on hardcoded-vs-live classification
- ✅ Identified STOCKSUNIFY2 sibling repo as Goal #1 EQUITY integration target
- ✅ Built 12-item consolidated fix queue

## Up next (T+90m)

- Investigate STOCKSUNIFY2 repo accessibility/integration plan
- Check whether `mercury2_fast_picks.json` 2-month staleness has been investigated
- Schedule next wakeup at T+30m
- Continue subagent dispatch for /audit/hyrotrader specific gaps

## Files

- `reports/loop2_checkpoint_1.md`, `loop2_checkpoint_2.md` (this)
- `reports/long_term_picks_integration_audit_2026-05-08.md`
- `swarm_runs/audit_metrics_20260508T192423Z/` (deepseek + cerebras)
- `docs/ANALYSIS_MAY82026_FREEBUFF.MD`
- `docs/HERMES_DAILYACCOMPLISHMENT.MD`
