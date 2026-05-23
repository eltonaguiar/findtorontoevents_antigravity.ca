# Loop 2 — 3-Hour Final Summary 2026-05-08

**Window**: T+0 (~17:00 UTC) → T+180 (~20:00 UTC)
**Mandate**: Find /audit + /audit/hyrotrader enhancements toward Goal #1 (top-notch picks per asset class), check long-term stock picks integration, deploy subagents as needed, progress every 30 min.

## Headline outcomes (5 progress reports + 6 commits)

### Triple-source audit convergence (mine + Kimi + Freebuff + Hermes daily)

Three independent audits this session + Hermes daily file all converged on the same critical issues. Final consolidated finding set is now triple-confirmed.

### What's hardcoded vs live on /audit (definitive classification)

| section | status |
|---|---|
| Summary cards (WR, PnL, PF) | ✅ LIVE (hourly cron) |
| Active/Closed pick tables | ✅ LIVE |
| Per-asset-class health | ✅ LIVE |
| Walk-forward by class | ✅ LIVE |
| Strategy warnings | ✅ LIVE |
| **DB health cards** (just shipped this session in loop 1) | ✅ LIVE |
| Strategy leaderboard | ✅ LIVE |
| Tier-2 PROVEN | ✅ LIVE |
| **MAJOR GOAL banner** | ❌ HARDCODED (May 5 snapshot, never updates) |
| **Tier T1/T2/T3 definitions** | ❌ HARDCODED |
| **"How to Find Edge" guide overlay** | ❌ HARDCODED (n=4,618 frozen analysis) |
| **Asset class descriptions** | ❌ HARDCODED |

### Math accuracy verdicts (3-engine swarm + freebuff)

| metric | verdict |
|---|---|
| Total PnL +1374.45% | misleading sum-of-pct (NOT wrong, just wrong meaning) |
| **EW compound +20,311,796.96%** | **math correct; ±500% per-trade cap too generous** — `_compound_equal_weight_capped_sequence` at `dashboard_generator.py:4577` works as written but produces absurd numbers when even a few trades cap |
| **Net Sharpe 0.1233 → 1.96 ann.** | **conceptually wrong** — uses sqrt(252) trading-days NOT sqrt(N_trades). Should be 0.1233 × sqrt(3301) ≈ 7.08 |
| W/L Ratio 1.60, Profit Factor 1.56 | ✅ CORRECT |
| OOS Sharpe ETF 11.4 | SUSPECT (n=88, 4 folds, overfit) |

### Long-term picks 2-layer concept-taxonomy bug (smoking gun)

UEPS pipeline emits 38 long-term EQUITY picks every 4h via active cron. But:
- `_normalize_pick()` at `dashboard_generator.py:6961-7184` drops `pick_type`
- `concept_registry.py:186` only matches `ueps_` prefix not bare `"ueps"`

Result: ALL 38 UEPS picks tagged `concept_family="standard"` instead of `"long_term_value"`. The `LONG_TERM` filter on /audit returns **0 of 287 active rows** despite picks being live.

**2 lines of code fix the visible LONG_TERM gap on /audit.**

### HyroTrader page 80% stale

Of 10 hyro_*.json data sources, only 1 is fresh:

| status | files |
|---|---|
| Fresh (1h) | `hyro_ml_pick_rankings.json` |
| 19-32 days stale | 7 files |
| Orphan (no writer in repo) | `hyro_playbook_combined.json`, `hyro_backtest_12m_new_strategies.json` |

Root cause for `hyro_quan_bridge.json` 20-day staleness: `hyro-bridge-regen.yml` failing 3+ days with `ModuleNotFoundError: No module named 'numpy'` at `tools/hyro_quan_bridge.py:32`. **1-line workflow fix** (add numpy to install step).

### STOCKSUNIFY2 sibling repo — integration target identified

Active sibling repo `eltonaguiar/STOCKSUNIFY2`:
- 9.9MB, last update 2026-05-07 (yesterday)
- `data/daily-stocks.json` (13.6KB) — direct integration target
- 5 algorithm catalog docs (CAN SLIM Growth Screener, Skyrocket, Replicator)
- Cross-AI consensus (Gemini + Comet + ChatGPT) on stack ordering: Watchlist → Entry → Risk → Sentiment → Holding

**Integration**: 1 new workflow (curl + safe_commit_push) + 1 line in `JSON_PICK_SOURCES` registers it. Unlocks ~1k EQUITY picks/day from a separate active repo to /audit.

## Final 16-item fix queue (priority order)

| # | fix | LoC | impact | repo target |
|---|---|---|---|---|
| 1 | `_normalize_pick()` add pick_type + holding_horizon | 2 | LONG_TERM filter 0→38 picks visible | dashboard_generator.py:6961 |
| 2 | `concept_registry.py:186` match bare "ueps" | 1 | UEPS tagged long_term_value | concept_registry.py |
| 3 | `multi_asset/scanner.py:2232` pnl-sign guard | 4 | cleans 1,247 WON-mislabel | multi_asset/scanner.py |
| 4 | `skyrocket_detector.py:382` drop `and picks` + safe_commit_push | 2 | restarts 5d-broken EQUITY skyrocket | tools + .github/workflows |
| 5 | EW compound cap 500→10 OR drop metric | 1 | dashboard stops showing +20M% | dashboard_generator.py:4577 |
| 6 | Sharpe annualize sqrt(N_trades) not sqrt(252) | 1 | Sharpe accurate | dashboard_generator.py |
| 7 | strategy_alerts ghost-row filter | ~5 | warnings stop flagging polluted strats | performance_alerts.py:128 |
| 8 | non-crypto resolver fix (15,744 phantom EXPIRED) | medium | EQUITY/FUTURES/ETF/PENNY/FOREX truth | universal_pick_resolver |
| 9 | `assign_concept_fields()` on closed-pick adapter | ~3 | concept-perf historical aggregation | dashboard_generator.py |
| 10 | replace 9 stale concept dropdown options | ~10 | UI not stale | template.html |
| 11 | MAJOR GOAL banner data-driven (read asset_class_health) | ~20 | banner = today not May 5 | template.html:832-870 + JS |
| 12 | Total PnL tooltip ("sum not portfolio return") | ~3 | reduces misinterpretation | template.html |
| 13 | STOCKSUNIFY2 daily-stocks.json pull workflow + JSON_PICK_SOURCES line | 1 wf + 1 line | unlocks ~1k EQUITY/day | new .github/workflows + dashboard_generator.py |
| 14 | `hyro-bridge-regen.yml` install step add numpy + pandas | 1 | restores 20d-stale hyro_quan_bridge | .github/workflows/hyro-bridge-regen.yml |
| 15 | Schedule manual hyro_backtest_*.py on cron | new workflows | restores 32d-stale backtest tables | .github/workflows |
| 16 | Drop or backfill orphan hyro_playbook_combined + hyro_backtest_12m_new_strategies | minor | dead-data cleanup | dashboard_generator.py |

### Top-3 fastest wins (each <5 min ship)

1. **#1 + #2** (3 lines): LONG_TERM filter shows 38 UEPS picks on /audit
2. **#14** (1 line): hyro_quan_bridge.json refreshes daily
3. **#5** (1 line): EW compound shows realistic numbers

### Highest-impact (each ~1 day)

- **#3 multi_asset/scanner.py:2232**: 1,247 polluted rows + cleans warnings
- **#13 STOCKSUNIFY2 pull**: ~1k EQUITY picks/day
- **#8 non-crypto resolver fix**: unblocks 5 asset classes' truth metrics

## Cross-asset transfer candidates (Hermes + ChatGPT consensus)

Strategies flagged for porting from CRYPTO → EQUITY/FOREX:
- Hurst exponent pairs / autocorrelation reversion
- Adaptive Bollinger Momentum + VIX term structure
- Turn-of-month, put/call ratio contrarian, liquidity imbalance
- chatgpt_combined (high historical WR)

Recommended pipeline: STOCKSUNIFY2's `aggregate-performance.ts` for backtesting, then port to alpha_engine if WR>50% on EQUITY universe.

## What didn't get done

- Apply any of the 16 fixes (this loop was investigation-only; user gates code changes)
- Fix-code patch generation for full set (only #3, #4, #14 had concrete patches drafted across both loops)
- Live re-test of `won_pnl_contradiction` after #3 fix (gated on user)
- Ship `tools/db_health_check.py` next hourly cron run (will auto-fire 16:10 UTC)

## Cadence verification

30-min checkpoints kept:
- T+30: checkpoint 1 ✅
- T+60: checkpoint 2 ✅
- T+90: checkpoint 3 ✅
- T+120: checkpoint 4 ✅
- T+150: checkpoint 5 ✅
- T+180: this final summary ✅

## Files added this loop

### Reports (`reports/`)
- `loop2_checkpoint_{1..5}.md` (5)
- `loop2_3hour_summary.md` (this)
- `long_term_picks_integration_audit_2026-05-08.md`

### Subagent outputs absorbed
- `docs/ANALYSIS_MAY82026_FREEBUFF.MD` (peer)
- `docs/HERMES_DAILYACCOMPLISHMENT.MD` (peer)

### Swarm runs
- `swarm_runs/audit_metrics_20260508T192423Z/` (deepseek + cerebras + kilo)

## Combined loops 1+2 — fixes ranked by ROI

If user has limited time, ship in this order:

1. **#1 + #2** (long-term filter restored) — 3 LoC
2. **#14** (hyro_quan_bridge numpy fix) — 1 LoC
3. **#3** (multi_asset scanner pnl guard) — 4 LoC
4. **#4** (skyrocket scanner drop empty-skip + safe_commit_push) — 2 LoC
5. **#5** (EW compound cap 500→10) — 1 LoC
6. **#7** (strategy_alerts ghost filter) — 5 LoC
7. **#13** (STOCKSUNIFY2 pull) — 1 workflow + 1 line
8. **#11** (MAJOR GOAL banner data-driven) — 20 LoC
9. **#6** (Sharpe annualization fix) — 1 LoC
10. **#8** (non-crypto resolver fix) — medium effort, unblocks 5 classes

Plus the 5 already-drafted patches from loop 1 (`reports/loop_checkpoint_7.md` + `reports/loop_3hour_summary.md`).
