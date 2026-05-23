# Loop 2 Checkpoint 1 — T+~30m (2026-05-08 21:15 UTC)

## Two big audits landed in parallel

### A. Long-term picks integration audit

`reports/long_term_picks_integration_audit_2026-05-08.md` — 300-word summary:

**PRs status (all 5 merged 2026-04-30 to active repo)**:
- ✅ #545 merged (classifier maps `time_horizon_days` → POSITION)
- ✅ #546 merged (penny skyrocket wireup)
- ✅ #547 merged (UEPS active-sync)
- ✅ #548 merged (Concept Taxonomy Phase 1)
- ✅ #549 (template.html long-term dropdown alias) — shipped under different commit

**Pipeline emit status**:
- ✅ UEPS: 22 longs at 17:08Z, 4-hourly cron green 5/5
- ✅ Mercury2: 6 active + 382 closed, hourly cron green
- ❌ **Penny Skyrocket EQUITY**: 5 consecutive failures. **NEW root cause**: `skyrocket_detector.py:382` `if save and picks:` skips file write on empty-scan days. (Different bug than my earlier git-push-race finding — both contribute.)
- ❌ TradingAgents emitter: zero scheduled workflow (orphan)
- ❌ mercury2_fast_picks.json: 2 months stale

**🔴 TWO-LAYER concept-taxonomy bug** (smoking gun):
1. `_normalize_pick()` in `dashboard_generator.py:6961-7184` drops `pick_type` from raw rows
2. `concept_registry.py:186` only matches `ueps_` prefix, NOT bare `"ueps"`

Result: All 38 UEPS picks tagged `concept_family="standard"` instead of `"long_term_value"`. The `LONG_TERM` filter on /audit returns **0 of 287 active rows** despite picks being live.

Plus: Concept dropdown lists 9 outdated families (breakout_momentum, etc.) that don't match the 8 registry actually emits. recent_closed (3500 rows) bypasses `assign_concept_fields()`, so historical perf-by-concept aggregation is broken.

**Top 5 ROI fixes** (from agent):
1. Add `pick_type` + `holding_horizon` to `_normalize_pick()` dict literal (2 lines)
2. Patch `concept_registry.py:186` to match bare `"ueps"` (1 line)
3. Apply already-drafted penny-skyrocket safe-write patch (commit `0b6fcf7e8db`) + add `if save:` (drop `and picks` guard)
4. Replace 9 stale concept-dropdown options with 8 real families (~10 HTML lines)
5. Wire `assign_concept_fields()` into closed-pick adapter so `recent_closed` gets stamped

Fixes #1+#2 alone make the long-term lane visible on /audit.

### B. /audit metrics accuracy swarm (3 engines)

DeepSeek + Cerebras converged (Kilo failed; 120-byte raw output):

**Pass 1 — freshness**: All metrics live/hourly except `Sig-to-Trade` (BROKEN placeholder). No hardcoded values found.

**Pass 2 — math accuracy**:

| metric | verdict | issue |
|---|---|---|
| Total PnL +1374.45% | conceptually WRONG | sum-of-pct meaningless on long horizons; should be cumulative compound or annualized |
| **EW compound +20,311,796.96%** | **mathematically IMPOSSIBLE** | even at ±5x cap, (5)^1508 still doesn't hit 20M%. Likely cap not applied to compounding base, or formula uses sum-of-pct as exponent |
| W/L Ratio 1.60 | ✅ CORRECT | 2.57/1.60 = 1.606 |
| Profit Factor 1.56 | ✅ CORRECT | (1488×2.57)/(1523×1.60) = 1.569 |
| **Net Sharpe 0.1233 (1.96 ann.)** | **conceptually WRONG** | 0.1233 × sqrt(252) = 1.96. Uses **trading-days** annualizer not **N_trades**. With N=3301 trades, correct annualization = 0.1233 × 57.45 = 7.08 |
| OOS Sharpe ETF 11.414 | SUSPECT | n=88 / 4 folds, implausibly high — likely overfitted |

**Pass 3 — strategy warnings**:
- Warnings ARE live (computed hourly from `dashboard_data.json::strategy_alerts`)
- **Warnings DO NOT filter ghost rows**. Pollution from `multi_asset_copytrader` 1,247 WON-mislabel rows + 96.21% `lm_signals` exit_price=0 + 43.22% PnL recompute mismatch all flow through into warning baseline calculations.
- Specific warnings to **disregard until ghost-filter lands**:
  - `myfxbook_retail_contrarian` (5% vs 50%) — multi_asset_copytrader ghosts
  - `ig_contrarian_sentiment` (5% vs 50%) — same source
  - `futures_momentum` (0% vs 43%) — likely lm_signals expired-no-resolve pollution
  - `claude_ml_moderate_mut` (43% vs 65%) — partial pollution

## Combined top-7 highest-leverage fixes (this checkpoint)

| # | fix | file | LoC | impact |
|---|---|---|---|---|
| 1 | Add `pick_type`+`holding_horizon` to `_normalize_pick()` | `audit_trail/dashboard_generator.py:6961` | 2 | unlocks LONG_TERM filter (0→38+ picks visible) |
| 2 | Match bare `"ueps"` in concept_registry | `concept_registry.py:186` | 1 | tags 38 picks `long_term_value` instead of `standard` |
| 3 | Apply scanner.py:2232 pnl-sign guard (drafted) | `multi_asset/scanner.py:2232` | 4 | flips 1,247 WON→LOST + cleans warnings |
| 4 | Apply safe_commit_push.sh + drop `and picks` | `penny-skyrocket-runner.yml` + `skyrocket_detector.py:382` | 2 | restarts 5-day-broken EQUITY skyrocket pipeline |
| 5 | Fix EW compound formula (cap clip + compound math) | `audit_trail/dashboard_generator.py` (~line 245) | ~5 | Total PnL card stops showing 20M% |
| 6 | Annualize Sharpe by N_trades not 252 | `audit_trail/dashboard_generator.py` (~line 200) | 1 | Net Sharpe 1.96→7.08 (or recompute correctly) |
| 7 | Pass closed-trade ghost-filter to strategy_alerts | `audit_trail/dashboard_generator.py` strategy_alerts builder | ~5 | warnings stop flagging polluted strategies |

## Open / pending

- Freebuff `docs/ANALYSIS_MAY82026_FREEBUFF.MD` not yet landed
- Kilo swarm engine failed (120 bytes only) — no impact since deepseek+cerebras converged
- `Sig-to-Trade` placeholder needs computation (low priority)

## Up next (T+60m)

- Read freebuff analysis if landed
- Inventory /audit/hyrotrader sections + identify gaps
- Cross-reference with the 7 fixes above for /hyrotrader analogs
- Schedule next wakeup at T+30m
