# Edge-Delivery Investigation — Cross-AI Validation Prompt

**Context:** A live trading system has 10 high-edge strategies (PF>1.5, WR>50%, n>=10 on 30d) emitting ZERO active picks. Investigation found root causes across 4 categories (A=cron, B=downstream filter, C=universe, D=kill-list, E=regime).

## Locally-derived diagnosis table

| # | Strategy | Class | n | WR | PF | Cause | Evidence |
|---|---|---|---|---|---|---|---|
| 1 | mega_mutation_macd_rsi_m048 | CRYPTO | 11 | 90.9% | 15.93 | E (regime + naming) | mega_mutation cron green; only 1 current open_pick has strategy=None; no current setups labelled m048 |
| 2 | claude_ml_moderate_mut | CRYPTO | 41 | 63.4% | 2.65 | D (kill_list) | Listed verbatim in `alpha_engine/data/core_whitelist.json` kill_list (last_kill_run=2026-03-26, 5 weeks stale); dashboard_generator filters at line ~7721 |
| 3 | hs_lb_None | CRYPTO | 10 | 70.0% | 6.08 | B (staleness filter) | 92 OPEN picks at copy_trader_intel/data/highscore_active_picks.json with timestamp=2026-04-19 (10+ days old); auto-expired at line 7232 (CRYPTO_MAX_AGE_HOURS=168) |
| 4 | stocks_rsi2_pullback | EQUITY | 19 | 73.7% | 5.06 | B (anti-test filter) | 8 fresh OPEN picks (2026-04-28) at copy_trader_intel/data/multi_asset_picks.json. Dropped at `_is_valid_pick` line 7355: any non-crypto pick with `"rsi2" in strategy.lower()` is rejected as test harness |
| 5 | MeanReversionBB | CRYPTO | 18 | 55.6% | 1.82 | D (kill_list) — CONTRADICTORY: also in core_strategies | `MeanReversionBB` exact match in kill_list; dashboard_generator kills it but quality_gates.py marks it REHABBED 2026-04-05 with 77.8% WR. 153 emissions in signals_database.json; explicit `signal_validation::MeanReversionBB` namespace also in kill_list |
| 6 | multi_period_rsi_confluence_et[h] | CRYPTO | 11 | 81.8% | 5.24 | D (kill_list) + string truncation | Baseline used `_et` (truncation); real name is `_eth`. Killed via `baby_strats_forward::multi_period_rsi_confluence_eth` and `battleground::multi_period_rsi_confluence_eth` |
| 7 | atr_percentile_gate | CRYPTO | 25 | 84.0% | 3.51 | D (kill_list) | Killed via `baby_strats_forward::atr_percentile_gate` namespaced entry; namespace strip pulls bare into kill_set (line 7715-7719) |
| 8 | forex-rsi-ema-scout | FOREX | 11 | 72.7% | 4.43 | E (regime / no current setups) | KIMI_RISEOFTHECLAW workflow GREEN; last closed 2026-04-15 (14d old); 0 in any current active_picks file; whitelisted in smart_picks_engine.py:362 but no setups firing |
| 9 | fx_smart_carry_trade_momentum | FOREX | 11 | 63.6% | 166.14 | A (cron data stale) | 2 OPEN picks at ml_gatekeeper/data/active_picks.json with timestamp 2026-04-15. ml_gatekeeper file mtime=337h, exceeds 72h freshness gate → ENTIRE source dropped at line 6564 |
| 10 | cta_fx_multifactor | FOREX | 11 | 63.6% | 5.89 | E (regime / no current setups) | cta_replicator wired in JSON_PICK_SOURCES; cta_bridge.py exists; last closed 2026-04-17; 0 current emissions; FX market in low-vol regime per recent reports |

## Cause distribution (counts)
- **A (Cron / source-data stale)**: 1 — fx_smart_carry_trade_momentum
- **B (Downstream filter blocked)**: 2 — stocks_rsi2_pullback (anti-test rsi2 substring), hs_lb_None (auto-expire timestamp)
- **C (Universe mismatch)**: 0
- **D (Kill-list / retired)**: 4 — claude_ml_moderate_mut, MeanReversionBB, multi_period_rsi_confluence_eth, atr_percentile_gate
- **E (Regime shift, no current setups)**: 3 — mega_mutation_macd_rsi_m048, forex-rsi-ema-scout, cta_fx_multifactor
- **F (Other)**: 0

## Special notes / contradictions found
1. **`MeanReversionBB` is in BOTH kill_list AND core_strategies** in `core_whitelist.json` — kill_list wins at filter time (line 7721). quality_gates.py line 624 says "REHABBED 2026-04-05 77.8% WR" but kill list never updated. Sample of internal contradiction.
2. **`core_whitelist.json` kill_list is 5 weeks stale** (last_kill_run = 2026-03-26). Strategies that built up edge in April are still being killed by March's verdicts.
3. **Dashboard's anti-test filter is over-broad**: line 7344-7357 drops any non-crypto pick with strategy substring `"rsi2"` — kills legit equity strategies that use RSI(2) (Connors RSI2 pullback is a legitimate, well-known equity edge with WR 70%+ historically).
4. **String-truncation in baseline doc**: `multi_period_rsi_confluence_et` is missing the trailing `h` — should be `_eth`. Verify in baseline reproducer.

## Questions for AI panel

1. Validate cause-attribution per strategy — any I have miscategorized?
2. For each strategy, recommend a specific fix (revive/edit kill_list, broaden filter, fix cron, etc.) and risk level (LOW/MED/HIGH for unkilling)?
3. Which 3 fixes have highest expected pick-volume × edge × low-risk?
4. Special: should `MeanReversionBB` and `claude_ml_moderate_mut` be unkilled given their April performance, OR is the kill still justified by older data?
5. The `_is_valid_pick` rsi2 substring filter — is it a defensible safety net or over-broad?
