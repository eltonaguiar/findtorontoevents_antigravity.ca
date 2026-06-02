# EAGLE Swarm Synthesis — 2026-06-02

> Multi-model review of all EAGLE*.MD files (72h) + AI tournament data + live dashboard state.
> Sources: EAGLE2_2026-06-02_MIMO_FINAL.MD, EAGLE_JUNE2_MIMO_V2_5_PRO.MD, EAGLE3_2026-06-02_minimax-m3-free.MD, EAGLE4_2026-06-02_minimax-m3-free.MD, EAGLE_JUNE2_CLAUDE_OPUS_4_7.MD, DAILY_IDEAS.MD, ASSET_CLASS_EDGE_ANALYSIS.json

---

## 1. Current State per Asset Class

| Asset Class | Live PF | Live WR | n (live) | AI Tournament PF | AI Tournament WR | Status |
|---|---|---|---|---|---|---|
| **PENNY** | — | — | — | **6.80** | **75.0%** | **STRONGEST EDGE** |
| **ETF** | 1.18 | 54.0% | 161 | **4.32** | **67.6%** | STRONG EDGE |
| **EQUITY** | 1.19 | 53.9% | 269 | **3.77** | **63.6%** | STRONG EDGE (LONG-only) |
| **CRYPTO** | 0.98 | 49.5% | 1,085 | 1.22 | 41.7% | MASKED by directional bug |
| **COMMODITY** | 0.23 | 18.8% | 16 | 2.02 | 58.6% | MODERATE (small n) |
| **FOREX** | 0.56 | 31.1% | 74 | 1.47 | 70.6% | TOXIC / FROZEN |
| **BOND** | 0.67 | 36.4% | 11 | 1.11 | 61.5% | INSUFFICIENT DATA |
| **FUTURES** | — | — | 2 | 5.14 | 65.0% | INSUFFICIENT DATA |

**Critical finding**: The AI tournament (top 5 T1 models, 3,692 resolved picks) shows a **completely different edge profile** than the live production book. Production emits from the wrong personas, wrong directions, and wrong symbols.

---

## 2. Top 5 Root Causes of Poor Performance

1. **CRYPTO Directional Bug (#1 cause)**
   - Production emits CRYPTO as LONG (33% WR, -0.49% avg PnL)
   - Real edge is SHORT (67% WR, +3.74% avg PnL)
   - **Fix**: EAGLE-4 flip already shipped in `alpha_engine/production_scanner.py` + `eagle_gates.py`

2. **Broken MC Null Hypothesis**
   - `strategy_verification_engine.py:243` uses bootstrap-with-replacement on trade PnLs
   - Destroys serial structure → rejects real trend-following edge
   - VWAPReversion has OOS Sharpe **3.10** but gets stuck at "shadow" tier
   - **Fix**: switch to block bootstrap (preserves autocorrelation)

3. **Stop Losses Too Tight**
   - 626 SL hits at **0.5% WR**, -2,257.8% PnL
   - Fixed-percentage stops get hit by noise before trades work
   - **Fix**: ATR-based stops (2.5–3x ATR)

4. **Resolver & Label Contamination**
   - 53.3% of EXPIRED picks have positive PnL (mislabeled as losses)
   - 1,864 duplicate signal-ts groups in CRYPTO feed
   - 91.7% concentration in `claude_gainer_st` (only 3 closed rows in raw DB)
   - **Fix**: EXPIRED→WON mislabel audit + dedup enforcement

5. **Quality Gates Over-Filtering + No Replacement**
   - Gates filter **98.9%** of raw picks (2,253 → 25 active)
   - 92/127 systems have **zero** closed picks
   - 203 strategies permanently killed, no auto-respawn
   - **Fix**: recalibrate kill threshold to n≥100; add 30-trade protected runway for new strategies

---

## 3. Confirmed Edge — Systems, Personas, Symbols

### Live Systems with Verified Edge
| System | Asset | n | WR | PF | Sharpe | Status |
|---|---|---|---|---|---|---|
| `mega_mutation` | CRYPTO | 265 | 65.9% | 1.93 | — | WINNER |
| `rapid_fire` | CRYPTO | 457 | 61.9% | 2.17 | — | WINNER |
| `VWAPReversion` | CRYPTO | 516 | — | 1.32 | **3.10** | Shadow (methodology trap) |
| `multi_asset_copytrader` | Multi | 812 | 36.1% | **4.09** | — | Best risk-adjusted |
| `multi_asset_cot` | COMMODITY | 130 | **86.9%** | **19.19** | — | Small n, needs verification |

### AI Tournament Top Personas
| Persona | Asset | WR | PF | n | Verdict |
|---|---|---|---|---|---|
| `macro_hedge` | ETF | **97%** | 5.89 | 38 | **EDGE** |
| `microcap_momentum` | PENNY | **83%** | 6.20 | 46 | **EDGE** |
| `pivot_catcher` | — | 77% | 2.94 | 22 | EDGE |
| `momentum_momentum` | EQUITY | 72% | 2.51 | 40 | EDGE |
| `gamma_raid` | PENNY | 67% | 2.33 | 42 | EDGE |

### Top Symbols by Win Rate (AI Tournament, min 3 resolved)
| Asset | Symbol | WR |
|---|---|---|
| PENNY | KULR | **100%** (12/12) |
| PENNY | RGTI | **100%** (11/11) |
| PENNY | ASTS | **100%** (6/6) |
| EQUITY | BAC | **100%** (8/8) |
| EQUITY | JPM | **90%** (9/10) |
| EQUITY | MSFT | **88%** (7/8) |
| ETF | EEM | **93%** (13/14) |
| ETF | IWM | **75%** (9/12) |
| ETF | GLD | **68%** (23/34) |

---

## 4. Immediate Actions (This Week)

| # | Action | File | Expected Impact |
|---|---|---|---|
| 1 | **Fix MC null → block bootstrap** | `verified_strategies/strategy_verification_engine.py:243` | Unlocks VWAPReversion + 3+ strategies to Tier-2 |
| 2 | **Verify EAGLE-4 CRYPTO flip live** | `alpha_engine/production_scanner.py` + `/audit/` dashboard | CRYPTO WR 33% → ~67% |
| 3 | **Widen SL to 2.5x ATR** | Stop-loss config / position sizing | Saves ~500 noisy stop-outs |
| 4 | **Fix EXPIRED mislabeling** | Resolver / `outcome_resolver.py` | Cleaner WR/PF numbers |
| 5 | **Kill 4 noise personas** | `production_scanner.py` / `eagle_gates.py` | Removes 30% of losing emissions |
| 6 | **Start shadow paper for top 3 lab survivors** | VWAPReversion, BollingerMR, DualMomentumCrypto | Mandatory 30-day forward track |

---

## 5. Medium-Term Actions (Weeks 2–4)

| # | Action | Expected Impact |
|---|---|---|
| 7 | **Ship 10 inverted strategies** from mutation scan | betting-against-beta (PF 0.25 → 600+), unknown (PF 0.59 → 2.12), etc. |
| 8 | **Promote top personas to production** | macro_hedge (ETF), microcap_momentum (PENNY), momentum_momentum (EQUITY) |
| 9 | **Add symbol whitelist** | BAC/JPM/MSFT/EEM/GLD/KULR/RGTI — concentrate on proven symbols |
| 10 | **Wire full admissibility pipeline** | DSR ≥ 0.80, PBO ≤ 0.50, block bootstrap, purged walk-forward |
| 11 | **Cap source concentration** | HHI < 0.30, top source < 40% (curb `kimi_riseoftheclaw` at 43.6%) |
| 12 | **Depromote FOREX/COMMODITY/BOND** | Zero allocation until class-level PF > 1.0 with clean data |

---

## 6. Statistical Readiness — Are We "Real Money Ready"?

**Answer: NO — with one exception.**

No strategy on the live `/audit` dashboard currently passes full institutional Tier-2:
- PF ≥ 1.5, WR ≥ 50%, n ≥ 30, MDD ≤ 20%, DSR ≥ 0.95, PBO ≤ 0.05

**Closest candidates:**
- `mega_mutation`: PF 1.93, WR 65.9%, n=265 — passes all but needs DSR/PBO fix
- `rapid_fire`: PF 2.17, WR 61.9%, n=457 — same
- `multi_asset_copytrader`: PF 4.09, MDD 16.67% — best risk-adjusted, needs DSR
- `multi_asset_cot`: PF 19.19, WR 86.9% — but n=130, suspicious without rolling verification

**What a hedge fund would require before sizing:**
1. Block bootstrap (not replacement bootstrap) → preserves serial correlation
2. True DSR with N = actual hypotheses tested (~500–1000, not fixed 100)
3. Real PBO with purged k-fold combinatorial partitions (not sign-flips)
4. Purged + embargoed walk-forward (8-fold rolling, embargo = max hold)
5. Asset-class-specific cost curves (crypto taker fees, FX spreads, micro-futures slippage)
6. **Mandatory 30-day shadow paper** between lab pass and any capital
7. Forward-test: ≥ 30–50 distinct symbols per class, ≥ 2× longest lookback duration

---

## 7. Hidden Edge Opportunities

1. **PENNY microcap momentum** — systematically ignored, but AI tournament shows PF 6.80 / 75% WR. Symbols KULR, RGTI, ASTS at 100% WR.
2. **ETF macro hedges** — `macro_hedge` persona at 97% WR on EEM/GLD/IWM. Safe, liquid, clean data.
3. **FOREX inversion** — `kimi_signal_tracking` sign-flip dataset (142/367 rows = 38.7%) proves inverted edge exists under the decay.
4. **AI tournament itself** — the tournament is outperforming hard-coded strategies. Top 5 T1 models should be treated as alpha emitters, not just research.
5. **Mutation survivors** — 10 inversion mutations already passed walk-forward. Shipping them is zero net-new code.

---

## 8. Best Possible Picks RIGHT NOW

Based on current verified data (NOT forward-looking predictions):

| Pick | Direction | Asset | Rationale | Confidence |
|---|---|---|---|---|
| CRYPTO (BTC, ETH, SOL) | **SHORT** | CRYPTO | EAGLE-4 flip fixes directional bug; SHORT WR 67% vs LONG 33% | HIGH |
| KULR, RGTI, ASTS | LONG | PENNY | 100% WR in AI tournament; microcap_momentum persona | MEDIUM-HIGH |
| BAC, JPM, MSFT | LONG | EQUITY | 88–100% WR; momentum_momentum persona | MEDIUM |
| EEM, GLD, IWM | LONG | ETF | 68–93% WR; macro_hedge persona | MEDIUM-HIGH |
| CT=F (Cotton) | LONG | COMMODITY | Historical PF 10.94 on n=39; cta_trend persona | MEDIUM (small n) |

**Symbols to AVOID right now:**
- FOREX entirely (PF 0.56, 31% WR, resolver contamination)
- CRYPTO LONG (directional bug, 33% WR)
- Any pick from `momentum_scalp`, `breakout_scanner`, `reflexivity_trader` personas

---

## 9. LiteLLM / AI Model Swarm Status

**Proxy**: `http://localhost:4000/v1` — **ONLINE**
**Available modes tested:**
- `ollama-cloud` → responding ✅
- `ollama-cloud-local` → responding ✅
- `ollama-cloud-large` → empty response (may need retry / different prompt shape)

**Recommendation**: Use `ollama-cloud` and `ollama-cloud-local` for brainstorm fanouts. Both are functional. The proxy also has `nvidia-deepseek-v4-pro`, `openrouter-ring-1t`, `claude-haiku-direct`, `deepseek-chat-direct` available — use these for higher-quality reasoning on strategy design.

---

## 10. Database Strategy Inventory

| Database | Tables | Relevance |
|---|---|---|
| `ejaguiar1_stocks` | 322 tables | Primary audit + trading pipeline. Key: `at_raw_picks`, `at_signal_outcomes`, `bt_backtest_trades`, `alpha_picks` |
| `ejaguiar1_backtests` | 6 tables | Dedicated backtest archive: `backtest_results`, `backtest_trades`, `bt_backtest_runs` |

**Strategy documentation should be written to:**
- `ejaguiar1_stocks.at_strategy_stats` — per-strategy performance summaries
- `ejaguiar1_backtests.backtest_results` — formal backtest records with asset_class tagging
- `reports/` markdown for human-readable audit trail

---

*Prepared by: EAGLE Swarm Synthesis (multi-model review)*
*Date: 2026-06-02*
*Next review: 2026-06-09*
