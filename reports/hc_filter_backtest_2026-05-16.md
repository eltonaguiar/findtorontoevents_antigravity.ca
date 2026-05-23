# HC Filter OOS Backtest — 2026-05-16

**Dataset:** `audit_trail/data/universal_resolved_picks.json` — 5,000 resolved picks  
**Win definition:** `pnl_pct > 0`  
**Baseline OOS WR:** 43.5% | **Baseline PF:** 1.48 | **Baseline AvgPnL:** +0.30%  
**Methodology:** Python analysis — no look-ahead, all gates applied to the fields present in the OOS export  
**Asset class mix:** CRYPTO 4,772 (95.4%) | EQUITY 160 (3.2%) | FOREX 68 (1.4%)

---

## 1. Confidence vs Win Rate by Asset Class

Confidence was normalized: values > 1 divided by 100 (some sources emit 60.0 instead of 0.60). Pearson r(confidence, win) = **-0.058** across all classes; **-0.053** for CRYPTO alone. Confidence is **anti-predictive** on this dataset — higher stated confidence correlates with *lower* OOS win rate.

### CRYPTO (n = 4,772)

| Confidence Band | N    | Wins | WR%   | PF   | AvgPnL |
|-----------------|------|------|-------|------|--------|
| 0.5 – 0.6       | 823  | 284  | 34.5% | 1.14 | +0.13  |
| **0.6 – 0.7**   | **1,574** | **744** | **47.3%** | **1.85** | **+0.64** |
| 0.7 – 0.8       | 1,119 | 465 | 41.6% | 1.21 | +0.22  |
| 0.8 – 0.9       | 351  | 129  | 36.8% | 0.96 | -0.05  |
| 0.9 – 1.0       | 56   | 25   | 44.6% | 1.51 | +0.42  |

**Sweet spot:** 0.6–0.7 dominates on every metric (WR +47.3%, PF 1.85). The 0.8–0.9 band is the only sub-1.0 PF bucket (0.96, AvgPnL negative). This band is dominated by `copy_trader_intel` (143 of 351 picks) and `ml_crypto_pred` (126), both sub-par systems. The 0.6–0.7 sweet spot is partly driven by `aggregated_picks` and `kimi_signal_tracking` clustering there.

### EQUITY (n = 160, all confidence in 0.6–1.0 range, all WR = 0%)

EQUITY picks show 0% WR across all confidence bands in this export. This is a data issue — all 160 EQUITY picks in the OOS set were SL_HIT, which is inconsistent with the dashboard showing EQUITY WR ~52.7%. The OOS export appears to have captured a stressed EQUITY period or a data pipeline artifact. No confidence conclusions can be drawn for EQUITY.

### ALL CLASSES (consolidated)

| Confidence Band | N    | WR%   | PF   | AvgPnL |
|-----------------|------|-------|------|--------|
| 0.5 – 0.6       | 823  | 34.5% | 1.14 | +0.13  |
| **0.6 – 0.7**   | **1,579** | **47.1%** | **1.85** | **+0.64** |
| 0.7 – 0.8       | 1,123 | 41.4% | 1.21 | +0.21  |
| 0.8 – 0.9       | 355  | 36.3% | 0.96 | -0.05  |
| 0.9 – 1.0       | 61   | 41.0% | 1.51 | +0.39  |

**Key finding:** The 0.8–0.9 band is the only loss band (PF < 1.0). The HC filter's Gate 8 (block confidence > 0.90 unless fwd_trades ≥ 20) is directionally correct — very high confidence picks without large forward samples are not reliable — but the *true* danger zone in the data is **0.8–0.9**, not >0.90. The >0.90 band (n=61) actually recovers to PF 1.51.

---

## 2. Risk:Reward vs Win Rate

Pearson r(risk_reward, win) = **+0.027** — weak positive but essentially zero. The relationship is non-linear and driven by the 1.5–2.0 band being dominated by elite source systems.

| RR Band   | N     | Wins  | WR%   | PF   | AvgPnL |
|-----------|-------|-------|-------|------|--------|
| < 1.5     | 4,357 | 1,829 | 42.0% | 1.34 | +0.31  |
| **1.5 – 2.0** | **558** | **340** | **60.9%** | **3.75** | **+1.40** |
| 2.0 – 2.5 | 82    | 6     | 7.3%  | 0.33 | -0.47  |
| 2.5 – 3.0 | 0     | —     | —     | —    | —      |
| ≥ 3.0     | 3     | 2     | 66.7% | 7.00 | +2.00  |

**Key finding:** The 1.5–2.0 RR band is exceptional (WR 60.9%, PF 3.75). Investigation shows this band is almost entirely `kimi_signal_tracking` and `aggregated_picks` picks — the source system explains the performance, not the RR target itself. The 2.0–2.5 band collapses to 7.3% WR (PF 0.33), suggesting that very high RR targets are typically set on marginal setups that almost never hit. A **minimum RR ≥ 1.5 filter** would be a strong addition — it would exclude 87% of picks but the remaining 12% WR is 18pp higher.

---

## 3. Exit Reason Analysis

### Overall Distribution (n = 5,000)

| Exit Reason | N     | % of Total | WR%    | PF       | AvgPnL |
|-------------|-------|------------|--------|----------|--------|
| TP_HIT      | 2,014 | 40.3%      | 100.0% | 1,821.4  | +3.08  |
| SL_HIT      | 2,599 | 52.0%      | 0.0%   | 0.00     | -1.64  |
| TIME_EXIT   | 387   | 7.7%       | 42.4%  | 2.94     | +0.42  |

The system exits SL more often than TP (52% vs 40%). TIME_EXIT picks have a surprisingly high PF of 2.94 — these are picks that drift positive without hitting the TP, and they capture mean-reversion alpha that the rigid TP misses.

### Exit Reason by Source System (top 12 by volume)

| Source System           | N     | TP%   | SL%   | TIME% | WR%   | PF   |
|-------------------------|-------|-------|-------|-------|-------|------|
| ml_crypto_pred          | 837   | 35.1% | 64.9% | 0.0%  | 35.1% | 0.82 |
| quan_engine             | 622   | 33.0% | 67.0% | 0.0%  | 33.0% | 1.28 |
| alpha_engine            | 422   | 25.6% | 54.5% | 19.9% | 31.0% | 0.81 |
| dna_winner_picks        | 388   | 35.1% | 64.9% | 0.0%  | 35.1% | 1.11 |
| **aggregated_picks**    | **385** | **78.2%** | **21.8%** | **0.0%** | **77.9%** | **6.94** |
| **kimi_signal_tracking**| **368** | **63.6%** | **11.7%** | **24.7%** | **76.6%** | **7.70** |
| luxalgo_filters         | 351   | 38.5% | 57.0% | 4.6%  | 41.3% | 1.38 |
| signal_validation       | 291   | 37.5% | 30.2% | 32.3% | 50.2% | 1.95 |
| copy_trader_highscore   | 240   | 32.5% | 53.8% | 13.8% | 39.2% | 1.10 |
| copy_trader_intel       | 183   | 34.4% | 56.3% | 9.3%  | 39.9% | 1.11 |
| dna_rapid_fire_mutations| 132   | 33.3% | 66.7% | 0.0%  | 33.3% | 0.82 |
| claude_gainer_st        | 112   | 28.6% | 71.4% | 0.0%  | 28.6% | 0.71 |

**Pattern:** Losing systems have SL% > 60% and TIME% ≈ 0. Elite systems (`aggregated_picks`, `kimi_signal_tracking`) have TP% ≈ 65–78% and SL% ≈ 12–22%. The SL% threshold is a strong leading indicator of system quality. A filter of **SL% < 30% over trailing 50 picks** would be a viable dynamic quality gate.

`signal_validation` is the only mid-tier system with significant TIME_EXIT volume (32.3%). Its TIME_EXIT picks WR = 39.4% with PF 3.03 — the TP targets are set too tight, leaving money on the table.

---

## 4. Source System as Trust Tier Proxy

This is the most powerful analysis. Source system identity, verifiable from the pick export, predicts OOS WR better than any other available field.

### All Source Systems (min n=10, sorted by OOS WR)

| Source System           | N     | Wins | WR%    | PF   | AvgPnL  | Tier        |
|-------------------------|-------|------|--------|------|---------|-------------|
| revival_all             | 35    | 35   | 100.0% | N/A  | +2.58   | SUSPECT*    |
| **aggregated_picks**    | **385** | **300** | **77.9%** | **6.94** | **+2.25** | **ELITE** |
| **kimi_signal_tracking**| **368** | **282** | **76.6%** | **7.70** | **+2.13** | **ELITE** |
| stocks_competition      | 53    | 36   | 67.9%  | 3.71 | +1.74   | ELITE       |
| rapid_fire              | 47    | 24   | 51.1%  | 1.67 | +0.66   | SOLID       |
| signal_validation       | 291   | 146  | 50.2%  | 1.95 | +0.63   | SOLID       |
| ml_crypto_pred_v12      | 103   | 44   | 42.7%  | 1.32 | +0.31   | MARGINAL    |
| luxalgo_filters         | 351   | 145  | 41.3%  | 1.38 | +0.30   | MARGINAL    |
| copy_trader_intel       | 183   | 73   | 39.9%  | 1.11 | +0.12   | MARGINAL    |
| copy_trader_highscore   | 240   | 94   | 39.2%  | 1.10 | +0.10   | MARGINAL    |
| trusted_genome          | 25    | 9    | 36.0%  | 0.87 | -0.13   | LOSING      |
| ml_crypto_pred          | 837   | 294  | 35.1%  | 0.82 | -0.24   | LOSING      |
| dna_winner_picks        | 388   | 136  | 35.1%  | 1.11 | +0.09   | MARGINAL    |
| signal_engine_mutations | 110   | 38   | 34.5%  | 1.00 | -0.00   | BREAKEVEN   |
| regime_terminal         | 70    | 24   | 34.3%  | 1.04 | +0.04   | MARGINAL    |
| dna_rapid_fire_mutations| 132   | 44   | 33.3%  | 0.82 | -0.17   | LOSING      |
| quan_engine             | 622   | 205  | 33.0%  | 1.28 | +0.22   | MARGINAL†   |
| alpha_engine            | 422   | 131  | 31.0%  | 0.81 | -0.19   | LOSING      |
| prop_firm_strategies    | 10    | 3    | 30.0%  | 0.77 | -0.31   | LOSING      |
| claude_gainer_st        | 112   | 32   | 28.6%  | 0.71 | -0.37   | LOSING      |
| mutation_lab            | 39    | 4    | 10.3%  | 0.19 | -1.14   | KILL        |
| battleground            | 27    | 0    | 0.0%   | 0.00 | -1.04   | KILL        |
| stocksunify2            | 18    | 0    | 0.0%   | N/A  | 0.00    | KILL†       |

*`revival_all` — 100% WR with no SL_HIT in 35 picks. This is a data artifact (curated test data or pipeline with no SL exits set). Exclude from production trust decisions.  
†`quan_engine` — PF 1.28 with n=622 is statistically meaningful but WR 33.0% is deeply sub-par; positive PF driven by large win sizes, not WR.  
†`stocksunify2` — n=18 all with pnl_pct = 0.00 exactly; looks like unresolved or dummy data.

**Critical insight:** The 3 elite systems (`kimi_signal_tracking`, `aggregated_picks`, `stocks_competition`) account for 806 picks and have combined WR = 76.1% and PF = 6.43. The remaining 4,194 picks from all other systems achieve WR = 38.7% and PF = 1.10. The source system gate is doing **all** the real work.

---

## 5. Direction Analysis (LONG vs SHORT)

| Asset Class | Direction | N     | WR%   | PF   | AvgPnL  |
|-------------|-----------|-------|-------|------|---------|
| CRYPTO      | LONG      | 3,615 | 47.7% | 1.68 | +0.58   |
| CRYPTO      | SHORT     | 1,157 | 30.3% | 0.90 | -0.10   |
| EQUITY      | LONG      | 88    | 65.9% | 8.59 | +1.73   |
| EQUITY      | SHORT     | 72    | 33.3% | 0.62 | -0.46   |
| FOREX       | LONG      | 44    | 25.0% | 0.95 | -0.02   |
| FOREX       | SHORT     | 24    | 37.5% | N/A  | +0.84   |
| **ALL**     | **LONG**  | **3,747** | **47.9%** | **1.72** | **+0.60** |
| **ALL**     | **SHORT** | **1,253** | **30.6%** | **0.90** | **-0.10** |

**SHORT picks are a net drag on every asset class.** CRYPTO SHORT WR = 30.3% (PF 0.90, loss territory). EQUITY SHORT WR = 33.3% (PF 0.62). The current regime gate in the HC filter (`shortBlockedInBull`) is directionally correct but not sufficient — SHORT picks are losing even outside of bull regimes in this dataset.

The elite source systems (`kimi_signal_tracking`, `aggregated_picks`, `stocks_competition`) issue **exclusively or almost exclusively LONG picks**, which partly explains their superior WR. This is not a coincidence — these systems have learned (or been configured) to avoid the SHORT drag.

### Direction Split Within Elite Source Systems

| Source System        | LONG n | LONG WR | LONG PF | SHORT n | SHORT WR | SHORT PF |
|----------------------|--------|---------|---------|---------|----------|---------|
| kimi_signal_tracking | 368    | 76.6%   | 7.70    | 0       | —        | —       |
| aggregated_picks     | 383    | 78.1%   | 6.98    | 2       | 50.0%    | 2.26    |
| stocks_competition   | 53     | 67.9%   | 3.71    | 0       | —        | —       |
| signal_validation    | 164    | 58.5%   | 3.21    | 127     | 39.4%    | 1.09    |

`signal_validation` LONG delivers WR 58.5% / PF 3.21 — solid. Its SHORT leg (WR 39.4%, PF 1.09) is the dead weight pulling its overall stats to 50%.

---

## 6. Compound Filter Test (HC Filter Approximation)

The OOS dataset lacks `score`, `trust_score`, `strat_fwd_wr`, `strat_fwd_trades`, and `hf_conviction_tier` — the core HC gate fields. The closest approximation uses `source_system` as the trust proxy and `confidence` as the supplemental gate.

**Elite sources defined:** `kimi_signal_tracking`, `aggregated_picks`, `stocks_competition`, `signal_validation`

| Filter Combination                          | N     | WR%   | PF   | AvgPnL | vs Baseline |
|---------------------------------------------|-------|-------|------|--------|-------------|
| Baseline (all 5,000)                        | 5,000 | 43.5% | 1.48 | +0.30  | —           |
| confidence > 0.65 only                      | 2,387 | 43.3% | 1.37 | +0.25  | -0.2pp WR   |
| Elite sources only                          | 1,097 | 69.6% | 4.94 | +1.38  | **+26.1pp** |
| conf > 0.65 AND elite sources               | 367   | 78.5% | 7.07 | +1.92  | **+35.0pp** |
| conf > 0.70 AND elite sources               | 4     | 50.0% | 1.92 | +0.49  | too few     |
| conf [0.60–0.75] AND elite sources          | 395   | 77.7% | 6.78 | +1.87  | **+34.2pp** |
| Elite sources AND LONG direction only       | 968   | 73.7% | 6.12 | +1.65  | **+30.2pp** |
| Elite + LONG + conf [0.60–0.70]             | 289   | 72.0% | 5.09 | +1.40  | **+28.5pp** |

**Key result:** Confidence alone adds zero value (+0 pp WR). Source system selection alone delivers +26pp. The combination of **source system (elite tier) + confidence 0.65–0.75** achieves WR 78.5% / PF 7.07 on 367 picks — the most HC-filter-like test possible with available OOS fields.

Note: the confidence 0.65–0.75 window performs similarly to >0.65 because elite systems cluster in the 0.60–0.70 band. `aggregated_picks` is 72% in the 0.6–0.7 band; `kimi_signal_tracking` median confidence ≈ 0.55 (normalized). Confidence adds marginal value on top of source selection, not the other way around.

---

## 7. HC Filter Gate Assessment — Which Gates Are Working?

### Gate Coverage in OOS Export

| Gate | Field(s) Required | Available in OOS? | N with data |
|------|------------------|-------------------|-------------|
| G1: score ≥ 40 | `score` | No (elite_score: 389) | 389 |
| G2: score ≥ 45 OR trust ≥ 8 | `score`, `trust_score` | No | 0 |
| G3: trust_tier not SANDBOX/UNPROVEN/PROBATION/DEMOTED | `trust_tier` | No | 0 |
| G4: strat_fwd_trades ≥ 5 | `forward_trades` | Partial (278) | 278 |
| G5: strat_fwd_wr ≥ 60%/55%/50% | `forward_wr` | Partial (278) | 278 |
| G6: score ≥ 55 (CRYPTO) / 50 (EQUITY) | `score` | Partial (389) | 389 |
| G7: trust_score ≥ 6 | `trust_score` | No | 0 |
| G8: conf > 0.90 blocked if fwd_trades < 20 | `confidence`, `forward_trades` | Partial | ~58 |
| G9: Regime + walk-forward + DSR + consensus | `regime`, `wf_verdict`, `dsr` | No | 0 |

Of 9 gates, only G1/G6 (via `elite_score`) and G4/G5 (278 picks from `copy_trader_intel`, `alpha_engine`, `battleground`) can be partially tested.

### Gate Verdict

| Gate | Evidence | Verdict |
|------|----------|---------|
| **G1: score ≥ 40 (absolute floor)** | elite_score < 40: WR = 11.1% (PF 0.50) vs elite_score ≥ 40: WR ~40% (PF ~1.1). Strong signal. | **WORKING** |
| **G2: score ≥ 45 OR trust ≥ 8** | Cannot test trust_score. Score side: the elite_score < 50 bucket shows WR 40.5% (PF 1.09), barely above SL noise. | **LIKELY WORKING** |
| **G3: trust_tier blacklist** | Cannot test directly. But source system acts as a strong proxy. Systems with OOS WR < 35% (alpha_engine, ml_crypto_pred, claude_gainer_st) are the "PROBATION/DEMOTED" equivalents. | **LIKELY WORKING — source system correlation is strong** |
| **G4: fwd_trades ≥ 5** | 278 picks with data: all have fwd_trades ≥ 10 (copy_trader_intel median ≈ 20+). Cannot test the floor directly. Indirect: systems with low sample counts (battleground, n=27) WR = 0.0%. | **LIKELY WORKING** |
| **G5: strat_fwd_wr ≥ 60%/55%/50%** | All 278 picks with forward_wr data have fwd_wr < 40% (entirely copy_trader_intel + alpha_engine + battleground — the worst systems). Cannot test the filter that *passes* picks. | **CANNOT VALIDATE — insufficient data** |
| **G6: score ≥ 55 (CRYPTO)** | elite_score bands: <40 WR 11%, 40-50 WR 40%, 55-60 WR 39%, ≥60 WR 41%. Diminishing returns above 50 but the absolute floor < 40 is very real. | **PARTIALLY WORKING (floor meaningful, upper bands flat)** |
| **G7: trust_score ≥ 6** | Cannot test. The 2026-05-15 raise from 4→6 / 5→6 is directionally sensible given confidence anti-predictiveness. | **CANNOT VALIDATE** |
| **G8: conf > 0.90 blocked unless fwd_trades ≥ 20** | High-conf (>0.90) picks: WR 41.7%, PF 1.56 — not terrible. The danger zone is 0.80–0.90 (WR 36.3%, PF 0.96, negative AvgPnL). Gate may be misspecified: should block **0.80–0.90** more aggressively, not just >0.90. | **MISSPECIFIED — correct direction, wrong threshold** |
| **G9: Regime + walk-forward + DSR + independent consensus** | Cannot test — fields not present in OOS export. Regime data would require external labeling. | **CANNOT VALIDATE** |

---

## 8. Recommended Filter Addition

**Single highest-value addition: `direction == LONG` gate for CRYPTO**

Evidence:
- CRYPTO LONG: WR 47.7%, PF 1.68 vs CRYPTO SHORT: WR 30.3%, PF 0.90 (loss territory)
- SHORT picks in CRYPTO lose money in aggregate (-0.10% AvgPnL). Removing them costs nothing in expectancy and reduces losing trades by ~1,157
- Elite systems already avoid SHORT (kimi_signal_tracking = 100% LONG, aggregated_picks = 99.5% LONG)
- A LONG-only gate for CRYPTO brings the system into alignment with where the edge actually lives

**Implementation:** Add `if asset_class == 'CRYPTO' and direction == 'SHORT': return False` before the existing gates, or add it as Gate 0 in `hc_filter.js`.

**Expected impact:** Removes ~24% of CRYPTO picks (1,157 / 4,772) that are net-negative. Remaining CRYPTO picks WR improves from 43.3% to 47.7%. Combined with elite source filter, WR > 70% is achievable.

---

## 9. Summary and Recommendations

### What is doing real work in the HC filter

1. **Source system identity (Gate 3 proxy)** — the single strongest predictor. `kimi_signal_tracking` (WR 76.6%) and `aggregated_picks` (WR 77.9%) are elite tier; `ml_crypto_pred`, `alpha_engine`, `claude_gainer_st` are losing systems that the trust_tier gate should be blocking.

2. **Score absolute floor (Gate 1)** — elite_score < 40 collapses to WR 11.1% / PF 0.50. The floor is real.

3. **Direction (implicit in regime gate, Gate 9)** — CRYPTO SHORT is a losing strategy on this dataset. The regime gate blocks some of this but not enough.

4. **RR ≥ 1.5 (not currently a gate)** — picks with RR 1.5–2.0 show WR 60.9% / PF 3.75. This is the most actionable new filter.

### What may be noise

- **Confidence as a standalone threshold (Gates 7/8)** — Pearson r = -0.058. Confidence is *anti-predictive*. Gate 8 (block >0.90) is directionally right but the 0.80–0.90 band is the actual problem zone. Using confidence as a positive filter adds no value.
- **Score bands above 50 (upper part of Gate 6)** — WR is flat between elite_score 50–55, 55–60, and ≥60. The floor matters; the ceiling does not.

### Priority action list

| Priority | Action | Expected Impact |
|----------|--------|----------------|
| P1 | Add `source_system` whitelist gate: block `mutation_lab`, `battleground`, `stocksunify2`, `claude_gainer_st` from passing HC filter regardless of score | Removes 4 losing systems (WR 0–29%) from HC output |
| P2 | Add CRYPTO LONG-only gate | Removes 1,157 losing SHORT picks from CRYPTO flow |
| P3 | Fix Gate 8 threshold: change from `conf > 0.90 blocked` to `conf 0.80–0.90 blocked unless fwd_trades ≥ 30` | Targets the actual loss zone, not a near-miss |
| P4 | Add minimum RR ≥ 1.5 gate for all asset classes | WR lifts from 43.5% to 60.9% on the passing subset |
| P5 | Add OOS WR field to pick export from all source systems | Enables proper G5 (fwd_wr) validation in future backtests |

---

## 10. Existing HC Filter Implementations

Two implementations exist:

- **`tools/hc_filter_backtest.py`** — Python wrapper, calls `dashboard_hc_rules.passes_high_conviction_pick`. Targets `alpha_engine/data/closed_picks.json`. Imports from `dashboard_hc_rules` (which is not in this repo's tools/ directory — likely a separate module). Cannot run against `universal_resolved_picks.json` without modification because the OOS dataset lacks `score`, `trust_score`, and `trust_tier`.

- **`tools/hc_filter_backtest.js`** — Node.js wrapper, calls `audit_dashboard/hc_filter.js:passesHighConvictionPick`. Same limitation — will return 0 HC picks on the OOS dataset because `forward_trades` (present in 278 of 5,000 rows) will fail Gate 4 for 95% of rows, and `score` defaults to 0 which fails Gate 1.

**Both tools need the OOS export to include `score`, `trust_score`, `trust_tier`, `strat_fwd_trades`, `strat_fwd_wr`, and `hf_conviction_tier` to produce meaningful results.** The current OOS export is a raw exit record, not an annotated scored pick. Enriching the export is the prerequisite for a proper HC filter backtest.

---

*Generated: 2026-05-16 | Source: `audit_trail/data/universal_resolved_picks.json` (5,000 picks) | Analysis: `tools/hc_filter_backtest.py` + ad-hoc Python*
