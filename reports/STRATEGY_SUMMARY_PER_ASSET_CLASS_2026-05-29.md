# Strategy Summary — Comprehensive Audit Report

- **Generated:** 2026-05-29 01:53:37 EDT
- **Database:** ejaguiar1_stocks (mysql.50webs.com)
- **Scope:** All strategies per asset class with tracked performance metrics
- **Tables:** 6 tracking tables populated from 3000 resolved picks

---

## 1. Database Schema Overview

| Table | Rows | Purpose |
|---|---|---|
| `strategy_summary` | 81 | Canonical strategy catalog per asset class with viability badges + performance |
| `metric_dimensions` | 41 | Dimension dictionary (Score/Trust/AGV/Regime/Edge/Strategy badges) |
| `pick_dimension_snapshot` | 3000 | Per-pick dimension capture (every Score/Trust/AGV sub-tag per pick) |
| `pick_funnel_views` | 7 | Performance by nav-surface/button (Smart Picks, High Conviction, etc.) |
| `edge_discovery` | 23 | Pre-computed edge significance per dimension combination |
| `view_definition_catalog` | 10 | Human-readable catalog of every dashboard view/button |

### Strategy Summary Columns (with traceability)
- **Core:** strategy_name, display_name, asset_class, source_module, timeframes
- **Viability Badges:** fwd_validated, viable_pct, probation_pct, recovery_pct, eliminated_pct, kimi_solo, multi_agree
- **Score Dimensions:** avg_elite_score, has_surfer_badge, has_safe_badge, avg_composite_ref
- **Performance (all-time):** n_total, n_resolved, n_active, wr_all_time, pf_all_time, dsr, pbo, wfe
- **Performance (7d/14d/30d/48h):** window_Xd_wr, window_Xd_pf per timeframe
- **Traceability:** file_path, source_file_lines, job_name, job_schedule, last_run_at, last_run_status, last_run_log, is_enabled, is_disabled_reason
- **Rankings:** rank_overall, rank_7d, rank_30d (by PF across all strategies)
- **Sample Picks:** sample_pick_ids (JSON array of 5 representative pick IDs for review)

---

## 2. Strategy Distribution by Sizing Status

| Status | Count | Avg PF | Avg WR | Total Picks |
|---|---|---|---|---|
| unknown | 24 | 225.904 | 100.0% | 1,044 |
| shadow | 57 | 597.988 | 100.0% | 239 |

---

## 3. Top Strategies Per Asset Class

### CRYPTO (10 strategies tracked)
| Rank | Strategy | Source | PF | WR | n | Status | Badges |
|---|---|---|---|---|---|---|---|
| 1 | ml_enhanced_ARBUSDT | ml_crypto_predictor | 14904.720 | 100.0% | 6 | shadow | — |
| 2 | ml_enhanced_TONUSDT | ml_crypto_predictor | 5209.101 | 100.0% | 23 |  | — |
| 3 | combined_confidence | combined_confidence_strategy, multi_asset_copytrader | 105.300 | 100.0% | 3 | shadow | — |
| 4 | rapid_momentum_filter_mut | genome | 49.838 | 100.0% | 5 | shadow | — |
| 5 | ml_enhanced_CHZUSDT | ml_crypto_predictor | 33.667 | 100.0% | 7 | shadow | — |
| 6 | ml_enhanced_ADAUSDT_15m_B_lightgbm | alpha_engine | 33.035 | 100.0% | 21 |  | — |
| 7 | ml_enhanced_BNBUSDT_15m_B_lightgbm | alpha_engine | 25.446 | 100.0% | 10 |  | — |
| 8 | ml_enhanced_AVAXUSDT_15m_D_ensemble_stack | alpha_engine | 19.331 | 100.0% | 25 |  | — |
| 9 | ml_enhanced_FETUSDT_15m_B_lightgbm | alpha_engine | 19.083 | 100.0% | 23 |  | — |
| 10 | clone_hl_copy_PensionFund_24M | copy_trader_intel | 17.318 | 100.0% | 7 | shadow | — |

### EQUITY (5 strategies tracked)
| Rank | Strategy | Source | PF | WR | n | Status | Badges |
|---|---|---|---|---|---|---|---|
| 1 | stocks_rsi2_pullback | multi_asset_copytrader | 21.508 | 100.0% | 64 |  | — |
| 2 | bond_yield_curve_slope | — | 0.000 | 0.0% | 1 | shadow | — |
| 3 | bond_yield_momentum | — | 0.000 | 0.0% | 3 | shadow | — |
| 4 | stocks_ema_golden_cross | multi_asset_copytrader | 0.000 | 0.0% | 2 | shadow | — |
| 5 | smart_money_accumulation | multi_asset_copytrader | 0.000 | 0.0% | 1 | shadow | — |

### FOREX (8 strategies tracked)
| Rank | Strategy | Source | PF | WR | n | Status | Badges |
|---|---|---|---|---|---|---|---|
| 1 | fx_smart_forex_rsi2_mean_reversion | alpha_engine | 15.742 | 100.0% | 12 |  | — |
| 2 | fx_smart_carry_trade_momentum | alpha_engine | 6.213 | 100.0% | 53 |  | — |
| 3 | unknown | kimi_signal_tracking | 1.392 | 100.0% | 22 |  | — |
| 4 | forex_rsi2_mean_reversion | forex_copy_trader | 0.000 | 0.0% | 2 | shadow | — |
| 5 | myfxbook_retail_contrarian | forex_copy_trader | 0.000 | 0.0% | 8 | shadow | — |
| 6 | forex_carry_momentum | multi_asset_copytrader | 0.000 | 0.0% | 4 | shadow | — |
| 7 | ig_contrarian_sentiment | multi_asset_copytrader | 0.000 | 0.0% | 6 | shadow | — |
| 8 | combined_confidence | combined_confidence_strategy | 0.000 | 0.0% | 1 | shadow | — |

### ETF
*No strategies with resolved picks yet.*

### COMMODITY (8 strategies tracked)
| Rank | Strategy | Source | PF | WR | n | Status | Badges |
|---|---|---|---|---|---|---|---|
| 1 | commodity_tsmom_12m | — | 0.000 | 0.0% | 3 | shadow | — |
| 2 | cftc_cot_commercial_signal | cftc_socrata | 0.000 | 0.0% | 1 | shadow | — |
| 3 | futures_momentum | multi_asset_copytrader | 0.000 | 0.0% | 3 | shadow | — |
| 4 | cta_commodity_momentum_term | cta_replicator | 0.000 | 0.0% | 5 | shadow | — |
| 5 | cot_positioning | multi_asset_cot | 0.000 | 0.0% | 1 | shadow | — |
| 6 | cta_cross_asset_tsmom | cta_replicator | 0.000 | 0.0% | 3 | shadow | — |
| 7 | cta_golden_cross_200 | cta_replicator | 0.000 | 0.0% | 1 | shadow | — |
| 8 | futures_bb_mean_reversion | multi_asset_copytrader | 0.000 | 0.0% | 1 | shadow | — |

### FUTURES (4 strategies tracked)
| Rank | Strategy | Source | PF | WR | n | Status | Badges |
|---|---|---|---|---|---|---|---|
| 1 | proven_futures_term_structure_proxy | — | 0.000 | 0.0% | 1 | shadow | — |
| 2 | turn_of_month_scanner | — | 0.000 | 0.0% | 1 | shadow | — |
| 3 | tv_community_consensus | multi_asset_copytrader | 0.000 | 0.0% | 1 | shadow | — |
| 4 | futures_cross_asset_momentum | — | 0.000 | 0.0% | 1 | shadow | — |

### BOND (1 strategies tracked)
| Rank | Strategy | Source | PF | WR | n | Status | Badges |
|---|---|---|---|---|---|---|---|
| 1 | futures_momentum | multi_asset_copytrader | 362.631 | 100.0% | 4 | shadow | — |

---

## 4. Top 20 Strategies Overall (by Profit Factor)

| Rank | Strategy | Class | PF | WR | n | Status |
|---|---|---|---|---|---|---|
| 1 | ml_enhanced_ARBUSDT | CRYPTO | 14904.720 | 100.0% | 6 | shadow |
| 2 | ml_enhanced_TONUSDT | CRYPTO | 5209.101 | 100.0% | 23 |  |
| 3 | futures_momentum | BOND | 362.631 | 100.0% | 4 | shadow |
| 4 | combined_confidence | CRYPTO | 105.300 | 100.0% | 3 | shadow |
| 5 | rapid_momentum_filter_mut | CRYPTO | 49.838 | 100.0% | 5 | shadow |
| 6 | ml_enhanced_CHZUSDT | CRYPTO | 33.667 | 100.0% | 7 | shadow |
| 7 | ml_enhanced_ADAUSDT_15m_B_lightgbm | CRYPTO | 33.035 | 100.0% | 21 |  |
| 8 | ml_enhanced_BNBUSDT_15m_B_lightgbm | CRYPTO | 25.446 | 100.0% | 10 |  |
| 9 | stocks_rsi2_pullback | EQUITY | 21.508 | 100.0% | 64 |  |
| 10 | ml_enhanced_AVAXUSDT_15m_D_ensemble_stack | CRYPTO | 19.331 | 100.0% | 25 |  |
| 11 | ml_enhanced_FETUSDT_15m_B_lightgbm | CRYPTO | 19.083 | 100.0% | 23 |  |
| 12 | clone_hl_copy_PensionFund_24M | CRYPTO | 17.318 | 100.0% | 7 | shadow |
| 13 | pump_fear_greed_filter_v2 | CRYPTO | 16.929 | 100.0% | 6 | shadow |
| 14 | ml_enhanced_INJUSDT | CRYPTO | 16.112 | 100.0% | 18 |  |
| 15 | fx_smart_forex_rsi2_mean_reversion | FOREX | 15.742 | 100.0% | 12 |  |
| 16 | ml_enhanced_ALGOUSDT_15m_B_lightgbm | CRYPTO | 11.764 | 100.0% | 23 |  |
| 17 | ml_enhanced_ADAUSDT | CRYPTO | 11.450 | 100.0% | 6 | shadow |
| 18 | ml_enhanced_DYDXUSDT_15m_D_ensemble_stack | CRYPTO | 10.417 | 100.0% | 34 |  |
| 19 | hurst_mean_reversion | CRYPTO | 9.261 | 100.0% | 5 | shadow |
| 20 | ml_enhanced_RENDERUSDT_1h_D_ensemble_stack | CRYPTO | 6.833 | 100.0% | 30 |  |

---

## 5. Edge Discovery Results (Bonferroni-Corrected)

| Asset Class | Dimension Combo | WR | PF | n | Verdict | Survived Bonferroni | Recommendation |
|---|---|---|---|---|---|---|---|
| CRYPTO | score_lt60+trust_lt5 | 45.4% | 1.284 | 1902 | NONE | ✅ | AVOID |
| CRYPTO | score_lt60+trust_lt5 | 45.4% | 1.284 | 1902 | NONE | ✅ | AVOID |
| CRYPTO | score_lt60+trust_lt5 | 46.7% | 1.034 | 2921 | NONE | ✅ | AVOID |
| CRYPTO | score_gte60+trust_lt5 | 54.1% | 0.887 | 183 | WEAK | ❌ | AVOID |
| CRYPTO | score_gte60+trust_lt5 | 54.3% | 0.816 | 140 | WEAK | ❌ | AVOID |
| CRYPTO | score_gte60+trust_lt5 | 54.3% | 0.816 | 140 | WEAK | ❌ | AVOID |
| COMMODITY | score_lt60+trust_lt5 | 43.7% | 0.735 | 506 | INVERTED | ❌ | AVOID |
|  | score_lt60+trust_lt5 | 37.5% | 0.516 | 32 | INVERTED | ❌ | AVOID |
|  | score_lt60+trust_lt5 | 37.5% | 0.516 | 32 | INVERTED | ❌ | AVOID |
| UNKNOWN | score_lt60+trust_lt5 | 37.5% | 0.516 | 32 | INVERTED | ❌ | AVOID |
| COMMODITY | score_lt60+trust_lt5 | 48.0% | 0.370 | 281 | NONE | ❌ | AVOID |
| COMMODITY | score_lt60+trust_lt5 | 48.0% | 0.370 | 281 | NONE | ❌ | AVOID |
| FOREX | score_lt60+trust_lt5 | 48.6% | 0.214 | 1236 | NONE | ❌ | AVOID |
| FOREX | score_lt60+trust_lt5 | 48.2% | 0.092 | 602 | NONE | ❌ | AVOID |
| FOREX | score_lt60+trust_lt5 | 48.2% | 0.092 | 602 | NONE | ❌ | AVOID |

---

## 6. Pick Funnel Views (Performance by Nav Surface)

| View | Class | WR | PF | Resolved | Active |
|---|---|---|---|---|---|

---

## 7. Strategy Source Modules

| Source Module | Strategy Count |
|---|---|
| alpha_engine | 14 |
| ml_crypto_predictor | 11 |
| multi_asset_copytrader | 9 |
| regime_terminal | 3 |
| cta_replicator | 3 |
| alpha_engine_fast | 3 |
| genome | 3 |
| alpha_engine, alpha_engine_fast | 3 |
| forex_copy_trader | 2 |
| battleground | 2 |
| genome_mutations | 1 |
| quan_engine | 1 |
| cftc_socrata | 1 |
| battleground_luxalgo | 1 |
| ml_strategy_reviver_inverse | 1 |

---

## 8. How to Query the Data

### Top strategies for a given asset class and timeframe
```sql
SELECT strategy_name, pf_all_time, wr_all_time, pick_count_all_time, sizing_status
FROM strategy_summary 
WHERE asset_class = 'CRYPTO' AND pf_all_time IS NOT NULL
ORDER BY pf_all_time DESC LIMIT 10;
```

### Strategies with viability badges
```sql
SELECT strategy_name, asset_class, fwd_validated, viable_pct, kimi_solo, multi_agree
FROM strategy_summary 
WHERE fwd_validated = 1 OR viable_pct > 50 OR multi_agree = 1;
```

### Edge discovery for a specific dimension combo
```sql
SELECT * FROM edge_discovery 
WHERE asset_class = 'CRYPTO' AND edge_key LIKE '%gte60%'
ORDER BY profit_factor DESC;
```

### Pick dimension snapshots for a strategy
```sql
SELECT symbol, status, pnl_pct, elite_score, trust_score, regime_label
FROM pick_dimension_snapshot 
WHERE strategy = 'crypto_altcoin_dip' AND status IN ('WON','LOST')
ORDER BY resolved_at DESC LIMIT 100;
```

### View performance comparison (Smart Picks button vs tab)
```sql
SELECT view_key, asset_class, win_rate, profit_factor, n_resolved
FROM pick_funnel_views
WHERE view_key IN ('smart_picks_button', 'smart_picks_tab')
ORDER BY view_key, asset_class;
```

---

## 9. Known Gaps & Next Steps

1. **file_path / source_file_lines** — Not yet populated; needs codebase scan to map strategies to Python files
2. **job_name / job_schedule / last_run_at** — Needs GHA workflow parsing to map cron triggers to strategies
3. **is_enabled / is_disabled_reason** — Partially populated (blacklisted strategies marked); needs kill_gate/config cross-reference
4. **pick_count_7d / pick_count_30d / wr_7d / wr_30d** — Needs time-windowed aggregation from pick_dimension_snapshot
5. **rank_overall / rank_7d / rank_30d** — Needs ranking computation after all PF data is populated
6. **sample_pick_ids** — Not yet populated; needs query to grab 5 recent pick IDs per strategy

---

*Report generated from ejaguiar1_stocks database. All metrics computed from resolved picks with pnl_pct IS NOT NULL.
Data populated from 3,000 resolved trading_picks + 93 active picks from alpha_engine/data/active_picks.json.*
