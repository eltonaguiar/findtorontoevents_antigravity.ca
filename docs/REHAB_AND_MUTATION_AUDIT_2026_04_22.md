# Rehab and Mutation Audit — 2026-04-22

Audit of blocked strategy rehabilitation discipline per `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` and `docs/MUTATION_THREE_AXIS_PROTOCOL.md`.

---

## Blocklist × Mutation-Testing Matrix

| Strategy | Tier | Inverse Tested? | DNA Mutated? | Rehab-Tracked? | Notes |
|----------|------|-----------------|--------------|----------------|-------|
| fear_greed_contrarian | RETIRED | NO | NO | NO | n=3525, WR 28.3%; never mutation-tested |
| proven_propfirm_cons_prop | RETIRED | NO | NO | NO | n=1832, WR 19.5%; never mutation-tested |
| proven_triple_ema_prop | RETIRED | NO | NO | NO | n=1616, WR 17.2%; never mutation-tested |
| copy_hl_lb_None | RETIRED | **YES** | **YES** | **YES** | inverse shows 68% WR (backtest), now retired |
| st_fear_greed_contrarian | RETIRED | **YES** | **YES** | **YES** | promoted from paper; inverse 75.4% WR |
| non_crypto_consensus | RETIRED | NO | NO | NO | n=87, WR 0%; deterministic loser, no rehab attempt |
| st_obv_support_divergence | RETIRED | NO | NO | NO | n=53, WR 17%; promoted from paper, never inversed |
| ARE_LONG | PAPER-ONLY | NO | NO | NO | PR#256; no S1-S4 validation |
| RC_LONG | PAPER-ONLY | NO | NO | NO | PR#256; no S1-S4 validation |
| SWEEP_SHORT | PAPER-ONLY | NO | NO | NO | PR#256; no S1-S4 validation |
| bollinger_squeeze_stochastic_breakout | PAPER-ONLY | NO | NO | NO | commit 90c88b5; no backtest data |
| macd_obv_momentum | PAPER-ONLY | NO | NO | NO | commit 90c88b5; no backtest data |
| fibonacci_rsi_mean_reversion | PAPER-ONLY | NO | NO | NO | commit 90c88b5; no backtest data |
| intermarket-flow-scout | PAPER-ONLY | NO | NO | NO | flagged by DeepSeek-v3.1; red flag overfit |
| bond_credit_spread | PAPER-ONLY | NO | NO | NO | PR#256 batch; no v1.1 gate validation |
| ... (20 bond/forex/futures strategies) | PAPER-ONLY | NO | NO | NO | PR#256; all lack S1-S4 |
| copy_hl_whale | PAPER-ONLY | NO | NO | NO | same lineage as copy_hl_lb_None; defensive flag |
| luxalgo_confluence | PAPER-ONLY | NO | NO | NO | appears in toxic combos; no mutation attempt |
| golden_combo_* (5 strategies) | PAPER-ONLY | NO | NO | NO | PF=inf/100% WR claims; BH-FDR failed |
| (kimi_signal_tracking, default) | COMPOSITE | NO | NO | **YES** | Forex toxic pair; tracked in dashboard |
| (copy_trader_intel, copy_hl_lb_None) | COMPOSITE | NO | NO | **YES** | composite block added 2026-04-20 |
| (alpha_engine, copy_hl_lb_None) | COMPOSITE | NO | NO | **YES** | defense-in-depth pair |

**Finding:** 9 of 15 retired strategies (60%) have never been inverse-tested or DNA-mutated despite meeting criteria (n>50, WR<35%).

---

## Top 5 Inverse-Promotion Candidates

Backtested via `alpha_engine/data/inverse_loser_report.json`:

| Rank | Strategy | Original WR | Inverted WR | n | Status |
|------|----------|-------------|-------------|---|--------|
| 1 | copy_hl_lb_None | 32.0% | **68.0%** | 278 | RETIRED — promote inverse to baby_strategies/ |
| 2 | st_fear_greed_contrarian | 24.6% | **75.4%** | 627 | RETIRED — strong inverse candidate |
| 3 | st_atr_vol_breakout | 22.2% | **77.8%** | 27 | Active — immediate inverse promotion candidate |
| 4 | extreme_fear | 30.0% | **70.0%** | 10 | Active — inverse shows +21.79% PnL |
| 5 | macd_rsi_confluence | 36.4% | **63.6%** | 66 | Active — +53.16% PnL inverse backtest |

**Recommended action:** Create `baby_strategies/inverse_<name>.py` for #3-5 immediately; #1-2 are already blocked but inverse variants should be registered in `dna_mutation_tracker.json` for tracking.

---

## Top 5 DNA-Mutation Candidates (Paper-Only, Needs Exploration)

Paper-only strategies with no mutation attempt yet:

| Rank | Strategy | Est. n | Est. WR | Mutation Priority |
|------|----------|--------|---------|-------------------|
| 1 | intermarket-flow-scout | Unknown | ~52% (claimed) | HIGH — suspicious WR jump (85% recent vs 52% all-time) |
| 2 | luxalgo_confluence | 12 (combo) | 8.3% | HIGH — appears in toxic combos; needs param grid |
| 3 | copy_hl_whale | Unknown | Unknown | MEDIUM — same lineage as copy_hl_lb_None |
| 4 | golden_combo_crypto_quan_rsi | Unknown | 100% (claimed) | HIGH — broken math; needs complete rewrite |
| 5 | commodity_range_position_reversion | Unknown | Unknown | MEDIUM — PR#265, no S2/S3/S4 |

**Note:** `auto_dna_mutator.py` last ran 2026-04-21T17:07:20 UTC (per tracker). It identified 5 super losers and 4 super winners, but **none** of the paper-only strategies above have been evaluated.

---

## Composite-Pair Candidates from Closed-Picks Analysis

Per `audit_trail/data/dashboard_payload.json` (total closed=8199, WR=39.4%):

| System | Strategy | Symbol(s) | Pattern | Evidence |
|--------|----------|-----------|---------|----------|
| kimi_signal_tracking | default | USDCHF=X | 8W/27L = 22.9% WR, -441.77% PnL | Already in `_RETIRED_SYSTEM_STRATEGY_PAIRS` |
| kimi_signal_tracking | default | AUDJPY=X | 0W/18L = 0% WR, -208.60% PnL | Already in `_RETIRED_SYSTEM_STRATEGY_PAIRS` |
| kimi_signal_tracking | default | NZDJPY=X | 1W/16L = 5.9% WR, -204.47% PnL | Already in `_RETIRED_SYSTEM_STRATEGY_PAIRS` |
| forex_copy_trader | futures_momentum | HG=F, PL=F | Recent 0% WR (3 trades) | **NEW candidate** — same pattern as kimi/forex |

**Finding:** The forex/futures multi-asset scanner is replicating the deterministic-loser pattern on commodity futures (copper, platinum). Recommend adding `(forex_copy_trader, futures_momentum)` or `(multi_asset_copytrader, futures_momentum)` to `_RETIRED_SYSTEM_STRATEGY_PAIRS` pending 10-trade confirmation.

---

## Cron Schedule Review: auto_dna_mutator

| Aspect | Current State | Gap |
|--------|---------------|-----|
| Schedule | Every 2h via `alpha-engine-live.yml` (line 582-585) | OK |
| Last run | 2026-04-21T17:07:20 UTC | Recent |
| Loser threshold | WR<35%, PnL<-10%, n>=10 | Permissive; misses n>=50/WR<20% deterministic losers |
| Paper-only scan | NO | **GAP** — does not evaluate paper-only strategies until they have live trades |
| Inverse backtest | NO | **GAP** — only forward-tests; no pre-flight inverse backtest |
| hf_decay_watchlist | File missing | **GAP** — decay tracking not operational |

**Recommended cron updates:**

1. **Add paper-only scan:** Extend `auto_dna_mutator.py` to backtest paper-only strategies against historical closed picks (cross-asset transfer test).
2. **Add pre-flight inverse:** Run `tools/mutation_analysis.py --inverse-backtest` before emitting inverse picks to avoid `inverse_ml_enhanced_*` killed mutations (5 already killed per tracker).
3. **Create hf_decay_watchlist.json:** Populate with `_PAPER_ONLY_STRATEGIES` for rolling 7d WR monitoring per Gemini walkthrough protocol.

---

## Summary: Highest-Leverage Actions

1. **Immediate:** Create `baby_strategies/inverse_st_atr_vol_breakout.py` (77.8% WR inverse, n=27).
2. **This week:** DNA-mutation grid for `intermarket-flow-scout` and `luxalgo_confluence` — both show overfit/toxic patterns.
3. **Governance:** Require `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` completion + 3-axis autopsy (export closed CSV + run `tools/mutation_analysis.py`) before any strategy moves from PAPER-ONLY to RETIRED — currently `non_crypto_consensus` and `st_obv_support_divergence` were fast-pathed without mutation attempt.
4. **Tooling:** Fix `hf_decay_watchlist.json` — file referenced in protocol but does not exist; should track rolling 7d WR for all paper-only strategies.

---

*Audit generated: 2026-04-22*
*Sources: alpha_engine/strategy_blocklist.py, alpha_engine/data/dna_mutation_tracker.json, alpha_engine/data/inverse_loser_report.json, audit_trail/data/dashboard_payload.json*
