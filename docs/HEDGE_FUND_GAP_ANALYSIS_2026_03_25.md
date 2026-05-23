# Hedge Fund Gap Analysis — 2026-03-25
**Generated from 3 parallel subagent analyses + 8 document reviews**

---

## Current Performance (367 closed trades)

| Metric | Our System | Hedge Fund Target | Gap |
|--------|-----------|-------------------|-----|
| Win Rate | 46.0% | >55% | -9pp |
| Profit Factor | 1.52 | >2.0 | -0.48 |
| Sharpe Ratio | ~0.3 | >1.0 | -0.7 |
| Score-PnL Correlation | 0.14 (elite) / -0.34 (recent 24h) | >0.30 | Scoring inverted |
| Copy Trader WR | 53.7% (all) / 85% (top 2 only) | >70% | Dilution problem |

**Last 24h:** 128 closed, 10W/14L = 42% WR, -0.15% PnL
**Crypto only:** 76.9% WR on closures (the edge IS there)

---

## The 6 Root Causes

### 1. binance_smart_money is NOT copy trading (44% of copy volume)
It reads aggregate Binance L/S ratios — sentiment indicator, not trader copying.
24 picks at 45.8% WR, picking illiquid alts (JCTUSDT -17.4%, LIGHTUSDT -16.9%).
**Fix: Kill or reclassify. Not a copy trader strategy.**

### 2. Bitget traders game their stats
Claimed 91%+ WR with profit_factor=99.99 and copy_trade_days=2-3.
They grid-trade tiny sizes, only close winners, leave losers open.
Every Bitget copy pick we made LOST.
**Fix: Require verified closed-trade history. Distrust PF>10.**

### 3. TP/SL is wrong for whale trades
Whales use 10-40x leverage with wide stops. Our 2-3% SL triggers on normal noise.
35% of picks (19/54) exited via SL_HIT with avg -4.66% loss.
**Fix: Widen to 8% TP / 4% SL for whale copies.**

### 4. Scoring is anti-predictive
Recent 24h: score 40-59 has 6.2% WR vs score 20-39 at 50% WR.
ml_score (+0.337 correlation) was incorrectly zeroed based on flawed IC analysis.
**Fix: Restore ml_score as primary weight.**

### 5. Best strategies were invisible
ml_enhanced_FETUSDT (93.8% WR) hidden for 89h due to stale timestamps.
OUTLIER_SYMBOLS exclusion erased FET/RENDER from per-strategy stats.
**Fix: Both traps fixed today (timestamp refresh + outlier exclusion fix).**

### 6. 62% of ML features dead since March 8
Kill switch shows health_score=0.38. ML models trading on partial data.
ml_crypto_predictor production engine appears dead for 17 days.
**Fix: Restart ml_crypto_predictor, restore dead features.**

---

## The Path: 46% → 58-62% WR

| Action | Expected Impact | Effort |
|--------|----------------|--------|
| Kill/reclassify binance_smart_money | +5pp system WR | 30 min |
| Concentrate copy on NMTD + whale_123M only | CT WR: 53% → 85% | 1h |
| Restore ml_score as primary weight | +10pp scoring | 1h |
| Block equity/commodity (0-19% WR) | Remove guaranteed losers | 30 min |
| Widen whale copy TP/SL (3%/2% → 8%/4%) | Fewer premature SL hits | 1h |
| Fix ML feature pipeline | ML strategies recover | 4h |
| **Combined** | **46% → 58-62% WR** | **~8h** |

---

## Only 2 Copy Traders Are Profitable

| Trader | Picks | WR | Avg PnL | Verdict |
|--------|-------|-----|---------|---------|
| NMTD_25M (Hyperliquid) | 16 | 81.2% | +0.020 | KEEP — primary allocation |
| whale_123M_87roi (HL) | 4 | 100% | +0.030 | KEEP — expand cautiously |
| binance_smart_money | 24 | 45.8% | -0.009 | KILL — not copy trading |
| All Bitget traders | 5 | 0% | -0.032 | KILL — gamed stats |
| All others (1 pick each) | 8 | 0% | -0.019 | PAPER ONLY until proven |

---

## Missed Optimizations (from 8 document review)

### Critical Contradiction Found
- `ml_score` was zeroed (IC=-0.19 per ic_weighted_selector analysis)
- BUT SCORE_VALIDATION proves ml_score is the STRONGEST predictor (+0.337)
- The IC analysis was run on a biased sample. ml_score should be RESTORED.

### Top 10 Priority Items for Next Session
1. Restore ml_score as primary weight (+0.337 correlation, was incorrectly zeroed)
2. Kill binance_smart_money (fake copy trader, 44% of volume, losing)
3. Hard-kill enforcement at generator level (160+ picks from killed strategies)
4. Block equity/commodity cold (0-19% WR)
5. Fix ml_crypto_predictor engine (dead since March 8)
6. Widen whale copy TP/SL
7. Add score minimum threshold (55)
8. FETUSDT concentration cap (30%)
9. Calibrate gate cascade (only 2/68 picks pass currently)
10. Fix PnL unit inconsistency in active_picks.json

---

## What IS Working (Protect These)

1. **Crypto-only picks**: 48% WR, +7.99% PnL — the real edge
2. **ml_enhanced_BNBUSDT/FETUSDT/RENDERUSDT**: 85-94% WR
3. **copy_hl_NMTD_25M**: 81.2% WR — most reliable non-ML signal
4. **Polymarket integration**: Correctly showing bearish on BTC, picks aligned
5. **Alpha engine**: Fixed and running 3+ consecutive successes

---

*Analysis based on: 367 closed trades, 83 active picks, 54 copy trader picks,
8 documentation reviews, 3 parallel subagent analyses, 4 peer consultations.*
