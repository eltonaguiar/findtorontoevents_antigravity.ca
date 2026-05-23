# Root Origin of Top Strategies & Dashboard Feed Audit

**Generated:** 2026-03-29 00:15 UTC by Claude Opus 4.6
**Enhanced:** Cross-referenced with Cursor analysis (ROOT_ORIGIN_CURSOR.MD) and Mercury 2 recommendations
**Scope:** All strategies with closed trades, unrealized PnL leaders, and 90+ data sources feeding findtorontoevents.ca/audit

---

## Top 20 Strategies by Closed-Trade Performance

Ranked by WR * PF (minimum 10 trades). Each traced to its root implementation, scanner, and workflow.

### Tier 1: Elite Edge (WR*PF > 2.0)

| # | Strategy | WR | PF | Trades | PnL | Origin |
|---|----------|----|----|--------|-----|--------|
| 1 | **copy_hl_lb_None** | 60.0% | 50.88 | 10 | +399.0% | `alpha_engine/copy_trader_bridge.py` — follows unidentified Hyperliquid trader via `copy_trader_intel/trusted_trader_tracker.py`. Scanner: `copy-trader-intelligence.yml`. **0 active picks.** |
| 2 | **st_atr_vol_breakout** | 88.9% | 12.92 | 18 | +25.9% | Strategy 8 inside `claude_gainer_ml/short_term_scanner.py` (line 661). Requires ATR% > 3%, momentum > +1%, volume > 2x. Scanner: `claude-gainer-short-term.yml` (every 30 min). **0 active — signal condition very restrictive.** |
| 3 | **drawdown_recovery_rsi_xrp** | 81.8% | 9.79 | 11 | +20.3% | `incubator/agents/web_ai/drawdown_recovery_rsi_xrp.py` — RSI-based mean reversion on XRPUSDT drawdowns. Scanner: `baby-strat-forward-paper.yml` (hourly). **0 active.** |
| 4 | **drawdown_recovery_rsi_sol** | 64.3% | 7.57 | 14 | +19.1% | `incubator/agents/web_ai/drawdown_recovery_rsi_sol.py` — SOL variant. Same scanner pipeline. **0 active.** |
| 5 | **quality-minus-junk** | 75.0% | 3.39 | 16 | +24.2% | `KIMI_RISEOFTHECLAW/live_scanner.py` — equity value strategy (XOM, CVX, XLE). Scanner: `torontoevent-backtest-and-deploy.yml`. **3 active picks.** |
| 6 | **drawdown_recovery_rsi_eth** | 67.2% | 3.52 | 64 | +35.9% | `incubator/agents/web_ai/drawdown_recovery_rsi_eth.py` — ETH variant with 64 trades. Scanner: `baby-strat-forward-paper.yml`. **0 active.** |
| 7 | **enhanced_ml_A_xgboost** | 67.4% | 3.48 | 43 | +61.9% | `ml_crypto_predictor/enhanced_models/config.py` + `live_predictor.py` — XGBoost ensemble model. **27 active picks.** No dedicated workflow found. |
| 8 | **keltner_compression_expansion_eth_v1** | 58.0% | 4.04 | 81 | +58.0% | `alpha_engine/keltner_evolved.py` — Keltner band compression/expansion with HMA trend on ETHUSDT 4h bars. Scanner: `baby-strat-forward-paper.yml`. **1 active pick.** |
| 9 | **copy_hl_whale_24.5M** | 68.8% | 3.30 | 16 | +23.0% | `alpha_engine/copy_trader_bridge.py` — follows wallet `0xe86b...7664` ($24.5M PnL, 103% ROI). Scanner: `copy-trader-intelligence.yml` -> `alpha-engine-live.yml`. **0 active.** |
| 10 | **crypto_keltner_compression_expansion_v1** | 67.3% | 3.18 | 104 | +42.5% | `alpha_engine/keltner_evolved.py` — core Keltner strategy on BTCUSDT 4h. Needs 120 bars minimum, ATR volatility gate. Scanner: `baby-strat-forward-paper.yml`. **1 active pick.** |

### Tier 2: Consistent Edge (WR*PF 1.2-2.0)

| # | Strategy | WR | PF | Trades | PnL | Origin |
|---|----------|----|----|--------|-----|--------|
| 11 | **keltner_compression_expansion_xrp_v1** | 60.9% | 3.08 | 68 | +48.5% | `alpha_engine/keltner_evolved.py` — XRP variant. **0 active.** |
| 12 | **crypto_soc_micro_noise_filter_a02_v1** | 62.5% | 2.84 | 16 | +8.2% | `incubator/agents/web_ai/` — order flow noise filter. **0 active.** |
| 13 | **keltner_compression_expansion_sol_v1** | 62.7% | 2.57 | 83 | +41.2% | `alpha_engine/keltner_evolved.py` — SOL variant. **1 active pick.** |
| 14 | **drawdown_recovery_rsi** | 54.1% | 2.96 | 61 | +34.7% | `incubator/agents/web_ai/drawdown_recovery_rsi.py` — generic RSI recovery. **0 active.** |
| 15 | **Classic Momentum** | 50.0% | 2.65 | 14 | +45.8% | `STOCKS/competition/` framework — equity momentum. **0 active.** |
| 16 | **claude_gainer_4h** | 56.2% | 2.23 | 32 | +80.2% | `claude_gainer_ml/tracker/` — 4h ML gainer scan. Scanner: `sustained-gainer-scan.yml`. **0 active.** |
| 17 | **crypto_soc_regime_filters_a05_v1** | 58.3% | 2.13 | 24 | +8.3% | `incubator/agents/web_ai/` — regime-aware SOC filter. **0 active.** |
| 18 | **MomentumEMA** | 57.1% | 2.14 | 14 | +11.9% | `2hour_challenge.py` (MomentumEMAStrategy class). Scanner: `2hour_challenge.yml`. **1 active pick.** |
| 19 | **st_fear_greed_contrarian** | 70.2% | 1.82 | 262 | +100.7% | `claude_gainer_ml/short_term_scanner.py` — Fear & Greed Index contrarian entries. **Highest volume proven strategy.** Scanner: `claude-gainer-short-term.yml`. **0 active — on protected list.** |
| 20 | **funding_momentum** | 58.7% | 2.12 | 92 | +39.6% | `incubator/agents/cursor_ai/funding_momentum.py` — funding rate momentum on BTCUSDT. Forward WR degraded to 50.8% on 783 trades. **0 active — fails MIN_WIN_RATE gate.** |

### Origin Breakdown

| Root Codebase | Strategies | Best WR | Architecture |
|---|---|---|---|
| **incubator/agents/web_ai/** | 8 (drawdown_recovery, crypto_soc) | 81.8% | Python strategy files → baby-strat-forward-paper.yml → battleground |
| **alpha_engine/keltner_evolved.py** | 5 (all Keltner variants) | 67.3% | Core Keltner logic → baby-strat-forward-paper.yml → battleground |
| **claude_gainer_ml/** | 3 (st_atr_vol_breakout, st_fear_greed, claude_gainer_4h) | 88.9% | Short-term scanner → claude-gainer-short-term.yml |
| **alpha_engine/copy_trader_bridge.py** | 2 (lb_None, whale_24.5M) | 68.8% | Hyperliquid scraper → copy-trader-intelligence.yml → alpha-engine-live.yml |
| **KIMI_RISEOFTHECLAW/** | 1 (quality-minus-junk) | 75.0% | KIMI scanner → torontoevent-backtest-and-deploy.yml |
| **ml_crypto_predictor/** | 1 (enhanced_ml_A_xgboost) | 67.4% | XGBoost ensemble, no dedicated workflow |

---

## Top Unrealized PnL — Active Picks

| # | Symbol | uPnL% | Strategy | System | Source File |
|---|--------|-------|----------|--------|-------------|
| 1 | KATUSDT | +1046.6% | incubator_gainer_composite | incubator_gainer | `incubator/.../gainer_scores_latest.json` |
| 2 | KATUSDT | +1019.2% | rocket_scanner | rocket_scanner | `alpha_engine/data/rocket_picks.json` |
| 3 | BARDUSDT | +33.3% | winner_pattern_precursor_inverse | inverse_mutations | `alpha_engine/data/inverse_picks.json` |
| 4 | OPNUSDT | +33.2% | winner_pattern_precursor_inverse | inverse_mutations | Same |
| 5 | SIGNUSDT | +31.3% | winner_pattern_precursor_inverse | inverse_mutations | Same |
| 6 | KITEUSDT | +25.1% | contrarian_liquidity_grab | contrarian_consensus | `alpha_engine/data/contrarian_picks.json` |
| 7 | RDNTUSDT | +22.9% | contrarian_liquidity_grab | contrarian_consensus | Same |
| 8 | ETHFIUSDT | +18.0% | contrarian_liquidity_grab | contrarian_consensus | Same |

**Note:** KATUSDT +1046% entries are likely entry price errors (not real 10x gains). The contrarian and inverse systems are generating genuine alpha but their data is 5+ days stale.

---

## Dashboard Feed Audit — What Reaches findtorontoevents.ca/audit

The audit dashboard reads from **90+ JSON pick sources** via `dashboard_generator.py`. Every source listed below is WIRED into the pipeline via `JSON_PICK_SOURCES` or special handlers in `collect_all_picks()`.

### Healthy — Fresh Data, Feeding Properly

| System | Source File | Fresh | Active | Closed | Status |
|---|---|---|---|---|---|
| alpha_engine | `alpha_engine/data/active_picks.json` | YES | 78 | 1,222 | OK |
| battleground | `battleground/data/active_picks.json` | YES | 6 | 156 | OK (newly wired) |
| baby_strats | `battleground/data/baby_strats_dashboard.json` | YES | 269 strats | - | OK |
| luxalgo | `battleground/data/luxalgo_active_picks.json` | YES | 16 | - | OK |
| kimi_riseoftheclaw | `KIMI_RISEOFTHECLAW/data/active_picks.json` | YES | 18 | - | OK |
| claude_gainer_st | `claude_gainer_ml/tracker/short_term_active.json` | YES | 17 | - | OK — best system (51.9% WR, +604% PnL) |
| claude_gainer_ml | `claude_gainer_ml/tracker/claude_live_picks.json` | YES | 228 | - | OK |
| mercury2 | `mercury2/data/active_picks.json` | YES | 6 | - | OK |
| copy_trader_intel | `copy_trader_intel/data/active_picks.json` | YES | 1 | - | OK (unblocked this session) |
| quan_engine | `quan_engine/data/active_signals.json` | YES | 6 | - | OK |
| regime_terminal | `regime_terminal/data/active_signals.json` | YES | 3 | - | OK |
| goldmine_stocks | `data/goldmine/stock_picks.json` | YES | 52 | - | OK (non-crypto) |
| goldmine_unified | `data/goldmine/unified_picks.json` | YES | 2 | - | OK |
| goldmine_meme | `data/goldmine/meme_winners.json` | YES | 3 | - | OK |
| multi_asset | `multi_asset/data/active_picks.json` | YES | 51 | - | OK (forex/commodity) |
| incubator_gainer | `incubator/.../gainer_scores_latest.json` | YES | 20 | - | OK |
| pm_kalshi_signals | `prediction_market_agents/data/kalshi_signals.json` | YES | 4 | - | OK |
| pm_whale_signals | `prediction_market_agents/data/whale_signals.json` | YES | 5 | - | OK |
| smart_money | `smart_money/data/active_picks.json` | YES | 4 | - | OK |
| super_signals | `cross_aggregation/data/super_signals.json` | YES | 9 | - | OK |
| ml_bg_system_f | `ml_battleground/system_f_clawsofdoom/data/active_picks.json` | YES | 10 | - | OK |

### Stale — Wired But Data Not Fresh

| System | Source File | Last Updated | Active | Issue |
|---|---|---|---|---|
| contrarian_consensus | `alpha_engine/data/contrarian_picks.json` | **122h ago** | 56 | Scanner not running. Has best unrealized gains (+33% BARDUSDT). |
| genome | `genome/data/universal_picks.json` | **57h ago** | 4 | Genome evolution stalled. 13 sub-systems wired but empty. |
| alpha_engine_fast | `alpha_engine/data/active_picks_fast.json` | **118h ago** | 0 | Fast scanner not producing. |
| polymarket_signals | `copy_trader_intel/data/polymarket_picks.json` | **36h ago** | 0 | Scraper produces 0 picks. File contains `[]`. |
| paper_trading | `paper_trading/data/active_picks.json` | **446h ago** | 29 | Frozen for 18+ days. |
| predictions | `predictions/data/active_predictions.json` | **56h ago** | 0 | Not producing predictions. |
| ml_bg_system_a-e | Various | **372-675h ago** | 0 | All dead except system_f. |

### Empty/Disconnected — Wired But Never Produced Data

31 systems are wired in `JSON_PICK_SOURCES` but have 0 active and 0 closed picks:

`abc_forward_a/b/c`, `asterdex_paper`, `audit_ensemble`, `battleground_mutations`, `bbkc_squeeze`, `breakout_a_sr`, `btc_breakout`, `buy_now_analysis`, `contested_picks`, `conviction_picks`, `copy_trader_consensus`, `copy_trader_variations`, `crypto_gainer_ml`, `funding_rate_arb`, `incubator_battleground`, `incubator_pipeline`, `live_position_monitor`, `live_spike_trader`, `maplestax_cbc`, `meme_scanner`, `meta_strategy` (FILE MISSING), `ml_bg_system_d/e`, `momentum_scalp`, `overnight_mutations`, `pm_momentum_signals`, `polymarket_signals`, `pumpwatch_mutations`, `strategy_health`

---

## Pipeline Architecture

```
Individual System Workflows (30+)
  └── Generate picks into JSON files
        │
audit-dashboard.yml (hourly at :10)
  ├── Pre-scanners (regime, funding rate, BTC breakout)
  ├── universal_pick_resolver (resolve TP/SL/time exits)
  ├── score_booster (family/lesson score adjustments)
  ├── dashboard_generator (reads ALL 90+ JSON sources)
  │     ├── collect_all_picks() — merges active + closed
  │     ├── collect_strategy_leaderboard() — builds strategy metrics
  │     ├── elite_scorer — ML composite scoring
  │     ├── non-crypto quality gate (v100)
  │     └── writes dashboard_payload.json + index.html
  └── Deploys to findtorontoevents.ca/audit
```

---

## Key Findings

1. **All requested systems ARE wired** into the audit pipeline. No system is truly disconnected — the issue is stale data from workflows that stopped running.

2. **Top strategies are dominated by 3 codebases:** `incubator/agents/web_ai/` (drawdown recovery), `alpha_engine/keltner_evolved.py` (Keltner), and `claude_gainer_ml/short_term_scanner.py` (fear/greed, ATR breakout).

3. **16 of 20 top strategies have 0 active picks.** They're in monitoring/dormant mode because signal conditions are rare or they were erroneously killed (fixed this session).

4. **claude_gainer_st is the best overall system** (51.9% WR, +604.2% PnL, 1,860 closed trades) but its top strategies (st_fear_greed_contrarian, st_atr_vol_breakout) have 0 active picks due to restrictive signal conditions.

5. **contrarian_consensus has the best unrealized gains** but its data is 5 days stale. The scanner workflow needs to be restarted.

6. **31 systems are ghost systems** — wired but never produced data. These should either be activated or removed from the source list to reduce noise.

---

## Critical Risks (Mercury 2 Analysis)

| Risk | Severity | Detail | Mitigation |
|---|---|---|---|
| **Single-model dominance** | HIGH | ml_crypto_predictor accounts for >70% of closed profit. Regime shift would be catastrophic. | Add model-diversity score; cap max contribution at 40% of total PnL |
| **Concentrated unrealized exposure** | HIGH | winner_pattern_precursor_inverse (+316%) and contrarian_liquidity_grab (+182%) in low-cap alts. Liquidity risk. | Per-asset exposure limits (<=5% capital); dynamic trailing-stops when ATR > 2x average |
| **Copy trader data integrity** | MEDIUM | Only a few trades captured; HYPEUSDT $0.05 entry was phantom +500%. | Unit-test JSON schema; log all signals with timestamps; enforce max 5x leverage |
| **ML model drift** | MEDIUM | No drift monitoring visible. ml_crypto_predictor could degrade silently. | Track feature distributions weekly; trigger retraining when KL-divergence > 0.2; maintain shadow model |
| **Legacy system noise** | LOW | 31 ghost systems inflate "connected systems" count. | Mark RETIRED; remove from JSON_PICK_SOURCES; archive code |

## Improvements Applied This Session (2026-03-28)

| Area | What Changed | Impact |
|---|---|---|
| Score inflation | Trust floor 0.50→0.35, proven-loser tier, non-crypto quality gate | Unproven systems can't score 100 |
| Phantom PnL | Cap 500%→100%; 3 bad-entry trades eliminated | copy_trader_intel clean PnL: +16% not +2005% |
| Copy trader pipeline | Freshness 2h→24h, whitelist 2→6, SHORT conf 90%→75% | Picks can flow again |
| Dormant strategies | Battleground added to SOURCES, 14 kill entries removed, 10 protected | Keltner/ATR can produce picks |
| Dashboard loading | 15s fetch timeout on 20MB payload | No more infinite loading |
| Non-crypto panel | Dynamic dropdown, STOCK merged, asset-class TP/SL defaults | Honest scoring for equities/forex |

## 30-Day Prioritized Roadmap

| Days | Action | Owner |
|---|---|---|
| 1-5 | Restart contrarian_consensus scanner; fix genome stall; add feed health-check script | Ops |
| 6-10 | Implement `dna_group_id` tagging for DNA/Genome strategies; aggregate metrics on dashboard | Dashboard |
| 11-15 | Enforce per-asset exposure caps and dynamic trailing-stops for winner_pattern_precursor_inverse | Risk |
| 16-20 | Unit-test copy_trader_intel pipeline; enable signal logging; fix entry price validation | Data |
| 21-25 | Set up feature-drift monitoring for ML ensemble; schedule weekly retraining | ML |
| 26-30 | Retire 31 ghost systems; launch unified observability; publish Strategy-Origin Handbook | Platform |

## Action Items

- [ ] Restart contrarian_consensus scanner (122h stale, has +33% unrealized gains)
- [ ] Investigate genome stall (57h stale)
- [ ] Remove or archive 31 ghost systems from JSON_PICK_SOURCES
- [ ] Run walk-forward validation on top 10 strategies to fill Strategy=0 gap
- [ ] Add backtest data for st_fear_greed_contrarian (262 trades but no backtest metrics)
- [ ] Investigate why polymarket_signals produces 0 picks despite scraper running
- [ ] Add model-diversity score to prevent >70% PnL concentration in one model
- [ ] Implement per-asset exposure limits for low-cap alt positions
- [ ] Set up feature-drift monitoring for ml_crypto_predictor
- [ ] Create Strategy-Origin Handbook for team onboarding
- [ ] Deploy feed health-check script with Slack/Discord alerting
