# WIN RATE INVESTIGATION REPORT - ACTUAL PERFORMANCE BY ASSET CLASS

**Generated:** 2026-03-25  
**Investigation Scope:** All available data sources (493+ tracked trades, 1,541+ untracked picks)

---

## EXECUTIVE SUMMARY

### The Brutal Truth
- **Overall System WR: 34.9%** (172 wins / 321 losses across 493 trades)
- **Statistically significant edge? NO** (p=1.0 vs 50% random chance)
- **The system is currently WORSE than coin-flipping**

### Where the Edge Actually Exists
Only **6 strategies** show statistically significant edge (p < 0.05):
1. ml_enhanced_BNBUSDT: **94.1% WR** (17 trades, p=0.0001)
2. ml_enhanced_FETUSDT: **93.8% WR** (16 trades, p=0.0003)
3. ml_enhanced_RENDERUSDT: **87.5% WR** (16 trades, p=0.002)
4. copy_hl_NMTD_25M: **81.3% WR** (16 trades, p=0.011)
5. High confidence (80+): **59.2% WR** (120 trades, p=0.027)
6. 5+ source consensus: **82-100% WR** (25 trades)

**ALL profitable edge is in CRYPTO-ONLY strategies.**

---

## 1. TRUE WIN RATES BY ASSET CLASS

| Asset Class | Trades | Wins | WR% | Raw PnL% | Capped PnL% | PF | p-value | Edge? |
|-------------|--------|------|-----|----------|-------------|-----|---------|-------|
| crypto | 385 | 160 | 41.56% | 599.84% | 13.06% | 1.558 | 0.999626 | NO |
| equity | 65 | 3 | 4.62% | -12.39% | -12.39% | 0.0 | 1.0 | NO |
| commodity | 21 | 3 | 14.29% | -9.3% | -9.3% | 0.0 | 0.999889 | NO |
| forex | 18 | 6 | 33.33% | -7.55% | -7.55% | 0.022 | 0.951874 | NO |
| bond | 4 | 0 | 0.0% | 0.0% | 0.0% | 0 | 1.0 | NO |

### Key Findings:
- **Crypto is the ONLY viable asset class** (41.6% WR)
- **Non-crypto is catastrophic** (6.8% WR combined)
- **Equity is the worst performer** (4.6% WR, -12.4% PnL)
- **Even crypto fails statistical significance** (p=0.9996 vs 50%)

---

## 2. SYSTEMS WITH REAL WIN RATE TRACKING

| System | Active | Closed | WR% | Avg PnL% | Status |
|--------|--------|--------|-----|----------|--------|
| battleground | 3 | 100 | 59.0% | +0.31% | ✅ Working |
| ml_crypto_predictor | 3 | 985 | 57.4% | +5.18% | ✅ Working |
| ml_bg_system_f | 0 | 98 | 50.5% | +0.54% | ✅ Working |
| mercury2 | 0 | 71 | 49.3% | +0.78% | ✅ Working |
| claude_gainer_st | 2 | 2,000 | 44.6% | +0.14% | ✅ Working |
| alpha_engine_fast | 0 | 313 | 44.4% | -0.34% | ✅ Working |
| baby_strats_forward | 0 | 5,755 | 43.3% | +0.01% | ✅ Working |
| alpha_engine | 1 | 504 | 42.3% | +2.16% | ✅ Working |
| claude_gainer | 6 | 188 | 42.3% | +0.20% | ✅ Working |
| kimi_riseoftheclaw | 22 | 427 | 37.4% | -0.78% | ✅ Working |
| luxalgo_filters | 3 | 312 | 35.4% | -0.09% | ✅ Working |
| super_signals | 21 | 80 | 32.1% | +0.33% | ✅ Working |
| multi_asset | 72 | 105 | 24.1% | -0.57% | ✅ Working |

**Total tracked closed picks: 10,938**
**Weighted average WR (tracked systems): 44.3%**

---

## 3. SYSTEMS WITH 0% WR - NO PRICE VALIDATION

| System | Active | Closed | Total | Issue |
|--------|--------|--------|-------|-------|
| rapid_fire | 79 | 334 | 413 | No outcome resolution |
| predictions | 0 | 324 | 324 | No outcome resolution |
| kimi_signal_tracking | 11 | 169 | 180 | No PnL calculation |
| revival_* (7 systems) | 0 | 284 | 284 | No outcome resolution |
| quan_engine | 5 | 47 | 52 | No TP/SL validation |
| copy_trader_intel | 10 | 49 | 59 | No outcome resolution |
| copy_trader_clones | 0 | 40 | 40 | No outcome resolution |
| copy_trader_highscore | 0 | 19 | 19 | No outcome resolution |
| copy_trader_consensus | 4 | 13 | 17 | No outcome resolution |
| genetic_programmer | 0 | 50 | 50 | No outcome resolution |
| ensemble_evolver | 0 | 25 | 25 | No outcome resolution |
| mape_evolver | 0 | 27 | 27 | No outcome resolution |
| goldmine_stocks | 37 | 14 | 51 | No outcome resolution |

**Total untracked picks: 1,541**
**These picks show 0% WR but may have real outcomes!**

---

## 4. CONSENSUS OUTCOMES - WHEN SOURCES AGREE

| Sources Agree | Win Rate % | Sample Size | Avg PnL% |
|---------------|------------|-------------|----------|
| 2 | 45% | 94 | +2.17% |
| 3 | 69% | 13 | +1.80% |
| 4 | 55% | 11 | +1.26% |
| 5 | **82%** | 11 | +1.94% |
| 6 | **86%** | 7 | -0.03% |
| 7 | **100%** | 4 | +1.14% |
| 8 | **100%** | 3 | +1.57% |

**KEY FINDING: 5+ source agreement = 82-100% WR on 25 closed picks**

### Consensus WR by Source System (in 5+ agreement):
| System | Consensus WR% | Picks |
|--------|---------------|-------|
| genome | 100% | 28 |
| incubator_fwd | 100% | 23 |
| ml_crypto_pred | 100% | 20 |
| coinglass_strategies | 100% | 15 |
| claude_gainer_st | 97% | 30 |
| mercury2 | 89% | 9 |
| luxalgo_filters | 88% | 16 |
| battleground | 87% | 15 |

---

## 5. SYSTEMS DRAGGING DOWN PERFORMANCE

| Strategy | Asset Class | Trades | WR% | Total PnL% | Impact |
|----------|-------------|--------|-----|------------|--------|
| yahoo_analyst_consensus | equity | 55 | 0.0% | -12.39% | MASSIVE |
| ml_enhanced_BTCUSDT_15m_D_ensemble_stack | crypto | 10 | 0.0% | -85.27% | HIGH |
| ml_enhanced_ADAUSDT_15m_D_ensemble_stack | crypto | 10 | 0.0% | -116.97% | HIGH |
| winner_pattern_precursor | crypto | 96 | 17.7% | -91.90% | MASSIVE |
| cta_tsmom_blend | forex | 18 | 16.7% | -3.10% | MEDIUM |
| hl_funding_fade | crypto | 16 | 25.0% | -28.57% | HIGH |
| binance_smart_money | crypto | 24 | 45.8% | -20.70% | MEDIUM |

**These 7 strategies account for:**
- 229 losing trades
- -358.9% total PnL destruction

---

## 6. PROJECTED WIN RATES IF FIXED

### Current State
- Overall WR: 34.9%
- Crypto WR: 41.6% (385 trades)
- Non-crypto WR: 6.8% (176 trades)
- Untracked picks: ~1,541

### Scenario Analysis

| Scenario | Projected WR | Effort |
|----------|--------------|--------|
| Fix untracked (35% conservative) | 36.3% | 12h |
| Fix untracked (50% optimistic) | 48.3% | 12h |
| Kill non-crypto only | 41.6% | 1h |
| Concentrate on top 4 ML strategies | 89.2% | 2h |
| High confidence (80+) gate only | 59.2% | 30min |
| **Fix top 5 issues** | **52-58%** | **16h** |

### Path to Hedge Fund Level (55%+ WR)
1. Kill yahoo_analyst_consensus: +2-3pp
2. Kill winner_pattern_precursor: +4-5pp
3. Kill 0% WR ML strategies: +2-3pp
4. Add price validation to copy_trader_intel: +3-5pp
5. Add price validation to rapid_fire: +5-8pp
6. Restore ml_score weighting: +10pp
7. Add confidence >= 80 gate: +8-12pp

**Combined: 34.9% → 52-58% WR**

---

## 7. PRIORITIZED FIX LIST BY IMPACT

| Priority | Fix | Expected WR Gain | Effort |
|----------|-----|------------------|--------|
| P0-CRITICAL | Kill yahoo_analyst_consensus (equity) | +2-3pp | 30 min |
| P0-CRITICAL | Kill winner_pattern_precursor | +4-5pp | 30 min |
| P0-CRITICAL | Kill ml_enhanced_BTC/ADA (0% WR) | +2-3pp | 30 min |
| P1-HIGH | Add price validation to copy_trader_intel | +3-5pp | 4h |
| P1-HIGH | Add price validation to rapid_fire | +5-8pp | 4h |
| P1-HIGH | Add price validation to predictions | +4-6pp | 4h |
| P2-MEDIUM | Block all non-crypto strategies | +3-5pp | 1h |
| P2-MEDIUM | Restore ml_score weighting | +10pp | 1h |
| P2-MEDIUM | Add confidence >= 80 gate | +8-12pp | 30 min |
| P3-LOW | Fix timestamp refresh for ML strategies | +2-3pp | 2h |

---

## 8. ROOT CAUSE ANALYSIS

### Why Win Rates Are Underperforming

1. **Dilution Problem**: 130+ strategies, but only ~7 actually work
2. **Non-Crypto Bleed**: Equity/commodity/forex at 0-33% WR dragging down crypto at 41.6%
3. **Data Integrity Gap**: 1,541+ picks with no tracking showing 0% WR
4. **Scoring Inversion**: ml_score was zeroed despite +0.337 correlation
5. **Missing Validation**: copy_trader_intel, rapid_fire, predictions have no outcome resolution
6. **Bad Actors**: binance_smart_money (45.8% WR), Bitget traders (0% WR)

### The Real Edge
- **Crypto-only**: 41.6% WR, +7.99% PnL
- **ML-enhanced symbols**: 85-94% WR (FET, RENDER, BNB)
- **Copy trader NMTD_25M**: 81% WR
- **5+ consensus**: 82-100% WR

---

## 9. ACTIONABLE RECOMMENDATIONS

### Immediate (Today - <2 hours)
1. ✅ Kill yahoo_analyst_consensus (0% WR on 55 trades)
2. ✅ Kill winner_pattern_precursor (17.7% WR on 96 trades)
3. ✅ Kill ml_enhanced_BTC/ADA (0% WR)
4. ✅ Block all equity/commodity strategies

### Short-term (This Week - 8 hours)
5. Add price validation to copy_trader_intel
6. Add price validation to rapid_fire
7. Restore ml_score as primary weight
8. Add confidence >= 80 gate

### Medium-term (This Month)
9. Concentrate capital on top 4 ML strategies
10. Create consensus_5plus virtual system
11. Fix ML pipeline (62% features offline)
12. Add position sizing based on confidence

---

## CONCLUSION

**The edge EXISTS but is being drowned in noise.**

- **True crypto win rate (validated)**: 41.6%
- **True forex win rate**: 33.3% (insufficient sample)
- **Projected WR if all systems fixed**: 52-58%
- **Impact of fixing 1,400+ untracked picks**: +3-12pp WR
- **Only profitable asset class**: CRYPTO

**The system doesn't need more signals. It needs ruthless elimination of what doesn't work.**

---

*Report generated from analysis of DEFINITIVE_EDGE_REPORT.md, WORKFLOW_DATA_AUDIT.md, CHATWITHIT.md, and mysql_database_forensics_report.md*
