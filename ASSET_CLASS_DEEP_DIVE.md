# Asset Class Deep Dive — Edge & Scoring Flaws by Asset Type

**Date:** 2026-04-06
**Data:** 3,223 closed picks from `alpha_engine/data/closed_picks.json`
**Goal:** Find edge and scoring flaws per asset class (crypto/scalp/swing/position/forex/commodity/futures)

---

## Part 1: Mode-Based Performance Summary

| Mode | Trades | WR% | Avg PnL | Total PnL | TP% | SL% | Time% | Verdict |
|------|--------|-----|---------|-----------|-----|-----|-------|---------|
| **CRYPTO** | 3,214 | 30.5% | -0.140% | -449.77% | 23.2 | 46.5 | 25.0 | LOSING (but has edge in specific symbols) |
| **SCALP** | 2,626 | 27.5% | -0.162% | -425.51% | 22.4 | 47.2 | 30.4 | CATASTROPHIC — dominant mode, worst WR |
| **SWING** | 78 | 38.5% | **+0.874%** | **+68.18%** | 38.5 | 55.1 | 6.4 | **PROFITABLE** — only winning mode |
| **POSITION** | 13 | 0.0% | -1.178% | -15.31% | 0.0 | 100.0 | 0.0 | CATASTROPHIC — all TAOUSDT, all SL |
| **FOREX** | 5 | 60.0% | 0.000% | 0.00% | 0.0 | 0.0 | 0.0 | Too small to evaluate |
| **COMMODITY** | 4 | 0.0% | -0.004% | -0.01% | 0.0 | 0.0 | 0.0 | Too small to evaluate |

### The Critical Finding

**SWING mode is the ONLY profitable mode** — +68.18% total PnL, 38.5% WR, +0.874% avg PnL per trade. SCALP mode (2,626 trades) loses -425% at 27.5% WR. The system is 81.5% SCALP and only 2.4% SWING — it's loading up on the worst mode and barely using the best one.

---

## Part 2: CRYPTO — Where Edge Hides in the Noise

### Overall: 3,214 trades, 30.5% WR, -449.77% total

### LONG vs SHORT — The Directional Edge

| Direction | Trades | WR% | Avg PnL |
|-----------|--------|-----|---------|
| LONG | 3,024 | 29.5% | negative |
| **SHORT** | **176** | **47.7%** | **positive** |

**SHORT has 18.2pp higher WR than LONG.** Yet only 5.5% of crypto trades are SHORT. The system is almost entirely LONG-biased despite SHORT performing dramatically better.

### Confidence Bucket Flaw

| Confidence | Trades | WR% | Avg PnL | Issue |
|------------|--------|-----|---------|-------|
| 0.0-0.3 | 82 | 31.7% | -0.887% | Low confidence = catastrophe |
| 0.4-0.5 | 245 | 40.0% | -0.055% | Near break-even |
| **0.5-0.6** | **755** | **38.4%** | **-0.092%** | **Best non-0.8 bucket** |
| **0.6-0.7** | **1,861** | **23.3%** | **-0.155%** | **WORST — bulk of trades** |
| 0.7-0.8 | 189 | 36.0% | -0.086% | Moderate |
| **0.8+** | **82** | **79.3%** | **+0.133%** | **ONLY profitable bucket** |

**The 0.6-0.7 confidence band has 1,861 trades (58% of all crypto) at 23.3% WR.** This is the system's default confidence range, and it's the WORST performing. The scoring flaw: confidence 0.6-0.7 is anti-predictive — it should trigger a penalty, not pass as "moderate confidence."

### Symbol-Level Edge

| Symbol | Trades | WR% | Avg PnL | Total PnL | Verdict |
|--------|--------|-----|---------|-----------|---------|
| **FETUSDT** | 38 | **84.2%** | **+0.229%** | **+8.70%** | STAR |
| **RENDERUSDT** | 188 | **45.2%** | +0.014% | +2.61% | GOOD |
| **XRPUSDT** | 50 | **50.0%** | +0.010% | +0.52% | GOOD |
| MATICUSDT | 553 | **0.0%** | -0.150% | -82.95% | **TOXIC — kill** |
| KASUSDT | 230 | 32.2% | -0.312% | -71.70% | TOXIC |
| TAOUSDT | 161 | 31.1% | -0.301% | -48.53% | TOXIC in SCALP mode |
| ICPUSDT | 148 | 29.1% | -0.231% | -34.18% | TOXIC |
| BTCUSDT | 271 | 35.8% | -0.109% | -29.55% | SURPRISING — BTC loses |

**MATICUSDT: 553 trades, 0.0% WR.** Zero. Not one winner out of 553. This single symbol accounts for -82.95% of losses. It should have been killed after the first 50 trades showed 0% WR.

### Day-of-Week Edge Within Crypto SCALP

| Day | Trades | WR% | Verdict |
|-----|--------|-----|---------|
| **Tuesday** | 186 | **47.3%** | **BEST — 20pp above baseline** |
| Thursday | 140 | 30.0% | Average |
| Monday | 398 | 26.1% | Below average |
| Friday | 409 | 27.6% | Below average |
| Sunday | 471 | 25.3% | Below average |
| Saturday | 717 | 26.9% | Below average |
| **Wednesday** | 305 | **20.3%** | **WORST — 7pp below baseline** |

Tuesday SCALP entries are 2.3x more likely to win than Wednesday entries.

---

## Part 3: SWING Mode — The Only Winner

### 78 trades, 38.5% WR, +68.18% total PnL, +0.874% avg

| Metric | SWING | SCALP | Difference |
|--------|-------|-------|------------|
| WR | 38.5% | 27.5% | +11.0pp |
| Avg PnL | +0.874% | -0.162% | +1.036pp |
| TP Rate | 38.5% | 22.4% | +16.1pp |
| Avg Hold | 28.3 bars | 6.7 bars | 4.2x longer |
| Total PnL | +68.18% | -425.51% | +493.69pp |

**SWING makes money because:**
1. Longer hold time (28.3 bars vs 6.7) — gives trades room to breathe
2. Higher TP rate (38.5% vs 22.4%) — TP is actually reachable
3. Higher avg win (+0.874% vs -0.162%) — bigger winners

**But SWING only has 78 trades** — the system barely uses it. The scoring flaw: the system defaults everything to SCALP mode regardless of the strategy's natural timeframe.

### SWING Symbol Performance

| Symbol | Trades | WR% | Avg PnL | Total PnL |
|--------|--------|-----|---------|-----------|
| **TAOUSDT** | 61 | **45.9%** | **+1.490%** | **+90.91%** |
| HYPEUSDT | 6 | 33.3% | +0.377% | +2.26% |
| KASUSDT | 11 | 0.0% | -2.272% | -24.99% |

**TAOUSDT in SWING mode: 45.9% WR, +90.91% total PnL.** The same symbol in SCALP mode: 31.1% WR, -48.53% total PnL. **Mode assignment is the difference between +91% and -49% on the same symbol.**

### SWING Day-of-Week

| Day | Trades | WR% |
|-----|--------|-----|
| **Tuesday** | 10 | **100.0%** |
| **Monday** | 9 | **77.8%** |
| Thursday | 10 | 50.0% |
| Wednesday | 18 | 27.8% |
| Friday | 18 | 16.7% |
| Saturday | 8 | 0.0% |
| Sunday | 5 | 0.0% |

**SWING + Tuesday = 100% WR.** SWING + Monday = 77.8% WR. SWING + Weekend = 0% WR. The mode and day interaction is extreme.

---

## Part 4: POSITION Mode — Total Failure

### 13 trades, 0.0% WR, -15.31% total, ALL TAOUSDT, ALL SL

Every single POSITION trade was TAOUSDT, every single one hit stop-loss, every single one was entered on a Friday. This is not a mode — it's a graveyard. The scoring flaw: POSITION mode was assigned to TAOUSDT with zero evidence it works at that timeframe.

---

## Part 5: Scoring Flaws Identified

### Flaw 1: Confidence 0.6-0.7 is Anti-Predictive
- 58% of trades fall in this band
- 23.3% WR — the WORST of any confidence band above 0.3
- **Fix:** Apply a penalty multiplier (0.85x) to picks with confidence 0.6-0.7, OR require higher elite_score to compensate

### Flaw 2: Mode Assignment is Random
- TAOUSDT: +90.91% in SWING, -48.53% in SCALP, -15.31% in POSITION
- The same symbol gets wildly different results depending on mode
- **Fix:** Assign mode based on symbol's optimal historical mode, not strategy default

### Flaw 3: SHORT Direction Ignored
- SHORT: 47.7% WR vs LONG: 29.5% WR
- Only 5.5% of trades are SHORT
- **Fix:** Increase SHORT signal generation, especially on Thursday (79.2% WR for SHORT)

### Flaw 4: MATICUSDT Never Killed
- 553 trades, 0.0% WR, -82.95% total PnL
- Should have been auto-killed after 50 trades with <10% WR
- **Fix:** Implement auto-kill: if symbol has 50+ trades and WR < 15%, block from new picks

### Flaw 5: Weekend SCALP Entries
- Saturday/Sunday SCALP: 25-27% WR
- Weekday SCALP: 26-47% WR (Tuesday best)
- **Fix:** Block SCALP entries on Saturday/Sunday, or apply 0.8x confidence penalty

### Flaw 6: R:R Default 2.0 is Toxic
- R:R 2.0 (system default): 28.3% WR, 84% of all trades
- R:R 1.0: 44.3% WR, +0.084% avg
- **Fix:** Default to R:R 1.0 for confidence >= 0.7, R:R 3.0 for confidence < 0.6

### Flaw 7: No Mode-Specific Scoring
- SWING mode: +0.874% avg (profitable)
- SCALP mode: -0.162% avg (losing)
- Both use the same scoring formula
- **Fix:** Mode-specific scoring: SWING gets 1.2x multiplier, SCALP gets 0.9x

---

## Part 6: Edge Sources — What Actually Works

### Confirmed Edge (Data + Academic Support)

| Edge | Evidence | Academic Support |
|------|----------|-----------------|
| SWING mode on TAOUSDT | 45.9% WR, +90.91% PnL | Longer hold = trend capture |
| FETUSDT via ML | 84.2% WR, 38 trades | Symbol-specific ML models |
| SHORT direction | 47.7% WR vs 29.5% LONG | Behavioral: retail over-buys |
| Tuesday entries | 50.6% WR overall, 47.3% SCALP | Caporale & Plastun (2019) |
| Confidence >= 0.8 | 79.3% WR, +0.133% avg | High conviction = real signal |
| R:R 1.0 (tight TP) | 44.3% WR vs 28.3% at R:R 2.0 | Achievable targets = more wins |
| Asia/Pre-Asia sessions | 35-36% WR | Retail-dominated = cleaner signals |

### Edge That's Being Wasted

| Wasted Edge | Current Usage | Optimal Usage |
|-------------|--------------|---------------|
| SWING mode | 2.4% of trades | Should be 15-20% |
| SHORT direction | 5.5% of trades | Should be 25-30% |
| Confidence >= 0.8 | 2.6% of trades | Filter harder, only pass 0.75+ |
| FETUSDT ML model | Shared with TRX/BTC/SOL (which fail) | Restrict ML to whitelisted symbols |
| Tuesday entries | 7.4% of trades | No day filter exists — add one |

---

## Part 7: Concrete Fixes (Ranked by Impact)

| # | Fix | Expected Impact | Effort |
|---|-----|----------------|--------|
| 1 | **Kill MATICUSDT** (0% WR, 553 trades, -83% PnL) | Remove single biggest drag | TRIVIAL |
| 2 | **Auto-kill symbols at 50+ trades with <15% WR** | Prevent future MATIC disasters | LOW |
| 3 | **Boost SWING mode allocation** (target 15-20% of picks) | +0.874% avg vs -0.162% | MEDIUM |
| 4 | **Penalize confidence 0.6-0.7** (0.85x multiplier) | Fix anti-predictive band | LOW |
| 5 | **Block weekend SCALP entries** | Remove 25-27% WR noise | LOW |
| 6 | **Increase SHORT signal generation** (especially Thursday) | Use 47.7% WR edge | MEDIUM |
| 7 | **Mode-specific scoring** (SWING 1.2x, SCALP 0.9x) | Align scoring with reality | LOW |
| 8 | **ML symbol whitelist** (FET/RENDER/BNB/DOGE only) | Stop ML on symbols where it fails | LOW |
| 9 | **Default R:R to 1.0** for high-confidence picks | 44.3% WR vs 28.3% at 2.0 | LOW |
| 10 | **Day-of-week scoring** (Tue 1.3x, Wed 0.7x) | +20pp WR on filtered subset | LOW |
