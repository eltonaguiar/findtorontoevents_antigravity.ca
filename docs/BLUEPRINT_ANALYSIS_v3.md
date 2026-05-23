# BLUEPRINT ANALYSIS v3 — Full System Review & Post-Overhaul Status
## 12 Trading Systems + Cross-System Aggregator

**Date:** Feb 26, 2026 21:00 UTC
**Analyst:** Claude Opus 4.6
**Market Condition:** F&G = 11 (Extreme Fear) | BTC ~$67,400 | ETH ~$2,028 | Health: PANIC
**Previous:** [BLUEPRINT v2](BLUEPRINT_ANALYSIS_v2.md) (Feb 25, 2026)

---

## EXECUTIVE SUMMARY

| Metric | v2 (Feb 25) | v3 (Feb 26) | Change |
|--------|-------------|-------------|--------|
| Total Systems | 12 active | 12 active (3 dormant) | Classified dormant |
| Active Picks | ~55 | ~55 (30 Alpha + 10 Mercury + 3 Claws + 2 Edge) | Similar |
| Closed Picks | ~99 | ~193 (141 Alpha + 25 Mercury + 2 Claws + 6 Edge + 3 BG-A + rest) | +94 |
| Systems Producing Picks | 7 | 5 active, 2 scanning, 3 dormant | Clarified |
| **Best Performer** | Mercury2 100% WR | Mercury2 40% WR (25 closed) — was 100% at 9 | Regression |
| **Best New System** | Claws of Doom 100% | Claws of Doom 100% (2 closed) — now 10 symbols | Expanded |
| **Worst Performer** | ML BG C Sharpe -71.20 | Alpha Engine 34.8% WR, -$5,751 PnL | 11 strategies killed |

**Key Changes Since v2:**
1. Alpha Engine overhauled: 11 dead strategies killed, direction-aware restrictions, SL widened 1.5x→2.25x ATR
2. Battleground health gate unblocked: `min()` → `max()` for confidence, lower thresholds
3. Claws of Doom expanded: 3 → 10 crypto symbols + smart rounding for sub-$1 coins
4. KIMI table alignment fixed (7 phantom header columns removed)
5. Mercury 2 regression: WR dropped from 100% (9 trades) to 40% (25 trades)

---

## SYSTEM STATUS MATRIX

| # | System | Open | Closed | WR | Sharpe | Last Pick (EST) | Status |
|---|--------|------|--------|-----|--------|-----------------|--------|
| 1 | **Alpha Engine** | 30 | 141 | 34.8% | -3.85 | Feb 26, 2:59pm | Overhauled |
| 2 | **Mercury 2** | 10 | 25 | 40.0% | -1.23 | Feb 26, 3:09pm | LONG-only (by design) |
| 3 | **Claws of Doom** | 3 | 2 | 100% | — | Feb 25, 11:49am | Active, expanded to 10 symbols |
| 4 | **Crypto ML Edge** | 2 | 6 | 0% | -5.80 | Feb 25, 11:33am | Retraining |
| 5 | Battleground A | 0 | 3 | 0% | — | Feb 25 | Dormant (3 losses, all SL) |
| 6 | Battleground B | 0 | 0 | n/a | — | Feb 26, 3:11pm | Fixed (extreme fear mode) |
| 7 | Battleground C | 0 | 0 | n/a | — | Feb 26, 2:47pm | Heuristic mode |
| 8 | Battleground D | 0 | 0 | n/a | — | Feb 26, 3:13pm | Fixed (API retries) |
| 9 | Battleground E | 0 | 0 | n/a | — | Feb 26, 1:32pm | Fixed (PANIC/BUY) |
| 10 | KIMI Rise of the Claw | — | — | — | — | Running 15min | Active (81 algorithms) |
| 11 | Cross Aggregator | — | — | — | — | Running 5min | Active |
| 12 | Breakout Arena (A/B/C) | 0 | 0 | n/a | — | — | Dormant |

---

## DETAILED SYSTEM ANALYSIS

### 1. Alpha Engine — OVERHAULED (100 Strategies → 89 Active)

**Performance Crisis (Root Cause):**
- 34.8% WR across 141 closed picks, -$5,751 total PnL
- 79 of 89 losses were SL_HIT (stop-hunted by crypto wicks)
- 11 strategies at 0% WR bleeding money

**Fixes Applied (Feb 26):**

| Fix | Detail | Expected Impact |
|-----|--------|-----------------|
| Kill 11 dead strategies | `double_top_bottom_detector`, `smart_money_fvg`, `halloween_effect`, etc. | Stop bleeding ~$500/week |
| Direction restrictions | 6 strategies restricted to their strong direction (SELL-only or BUY-only) | +10-15% WR for restricted strategies |
| Widen SL | 1.5x → 2.25x ATR (maintains 1.33 R:R with 3.0x TP) | Reduce SL_HIT from 89% to ~60% |
| Proven strategy boost | Top 7 strategies get 2-4x confidence boost | More capital to winners |
| ML patience | ML strategies get 12+ picks before evaluation (was 8) | Don't kill learning strategies |

**Top 5 Strategies (by Win Rate, min 2 trades):**

| # | Strategy | Record | WR | Avg PnL | Sharpe | Direction |
|---|----------|--------|-----|---------|--------|-----------|
| 1 | `community_london_breakout_v2_forex` | 2/2 | 100% | +0.50% | 114.86 | SELL-only |
| 2 | `multi_sigma_reversal` | 3/3 | 100% | +10.93% | 40.32 | SELL-only (3x boost) |
| 3 | `spike_macd_divergence` | 3/3 | 100% | +1.01% | 25.36 | BUY-only (2x boost) |
| 4 | `autocorrelation_exploiter` | 5/6 | 83% | +12.16% | 26.23 | SELL-only (4x boost) |
| 5 | `hurst_regime_adaptive` | 5/6 | 83% | +8.03% | high | BUY-only (4x boost) |

**Dashboard:** https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/alpha/

---

### 2. Mercury 2 — WR REGRESSION (100% → 40%)

| Metric | v2 (Feb 25) | v3 (Feb 26) |
|--------|-------------|-------------|
| Win Rate | 100% (9/9) | 40% (10/25) |
| Active | 3 | 10 |
| Closed | 9 | 25 |

**What happened:** The first 9 trades were all winners (+32.55% total). Then 16 more closed — 15 of which were LOSSES. The win rate collapsed from 100% to 40%. The system is LONG-only by design (SHORT requires RSI>70 + below SMA200, which conflicts with oversold guard at RSI<20 in extreme fear).

**Recommendation:** Retrain with latest data. Consider adding SHORT capacity or at minimum hedging with inverse signals during F&G < 20.

**Dashboard:** https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/mercury2/

---

### 3. Claws of Doom — EXPANDED (v3.2.1)

| Metric | v2 | v3 |
|--------|-----|-----|
| Symbols | 3 (BTC, ETH, SOL) | **10** (+BNB, XRP, DOGE, ADA, AVAX, LINK, DOT) |
| Closed | 1 | 2 |
| Win Rate | 100% (1/1) | 100% (2/2) |
| Version | 3.1.0 | 3.2.1 |

**Changes:**
- 10 symbols across all 5 price APIs + funding rates
- Smart rounding: `round(price, 2)` killed DOGE/ADA precision. New `smart_round()` adapts decimals to price magnitude
- Top 8 picks by confidence selected per scan

**Current Positions:**

| Symbol | Direction | Entry | TP | SL | P&L |
|--------|-----------|-------|----|----|-----|
| BTC | LONG | $65,383 | $69,306 | $62,114 | **+3.13%** |
| ETH | LONG | $2,019 | $2,140 | $1,918 | **+0.47%** |
| SOL | LONG | $87.36 | $92.60 | $82.99 | -1.42% |

**Dashboard:** https://eltonaguiar.github.io/CLAWSOFDOOM/

---

### 4. Crypto ML Edge — RETRAINING

| Metric | Value |
|--------|-------|
| Active | 2 (IWM, GLD) |
| Closed | 6 (all losses) |
| Win Rate | 0% |
| Sharpe | -5.80 |
| Total Return | -8.47% |
| Models | 10 LightGBM (7 DSR pass, 3 fail) |

**Strategy:** Connors RSI-2 (proven 75.7% WR on SPY) applied to ETFs. Two active picks showing small green (+0.71% IWM, +0.32% GLD).

**Issue:** CORS errors on Yahoo Finance proxy (allorigins.win) cause slow dashboard loading but don't affect trading.

**Dashboard:** https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/edge/

---

### 5-9. ML Battleground A-E — HEALTH GATE FIXED

**Root Cause of Zero Picks:**
All 5 systems were producing zero picks because the shared health gate used `min(ml_score, confidence)` for the threshold check. When ml_score defaults to 0.5 (no model trained), a 0.65 confidence signal becomes 0.50 and gets rejected.

**Fix:** Changed to `max(ml_score, confidence)` — use the better estimate. Position sizing (50% for BUYs, 35% for SELLs at F&G<15) is the real safety net.

| System | Specialty | Status | Notes |
|--------|-----------|--------|-------|
| A (The Filter) | Meta-learning filter | Dormant | 3 closed, all SL losses (-12%, -10%, -14%) |
| B (The Regime) | Regime classifier | Fixed | Confidence reduced 90%→55% at F&G<15 |
| C (The Neural Net) | GRU-Attention | Heuristic mode | No actual model trained yet |
| D (The Carry) | Funding rate carry | Fixed | API retries + 1h cache |
| E (The Momentum) | Momentum scanner | Fixed | PANIC/BUY contradiction resolved |

---

### 10. KIMI Rise of the Claw (v11.0)

- 81 algorithms running every 15 min
- Table alignment fixed (7 phantom columns removed)
- Provides consensus signals to cross-aggregator

**Dashboard:** https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/riseoftheclaw.html

---

## ALL DASHBOARD LINKS

| Dashboard | URL | Features |
|-----------|-----|----------|
| Trading Systems Hub | [hub/](https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/hub/) | All systems, LONG/SHORT filter |
| Alpha Engine | [alpha/](https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/alpha/) | 89 active strategies, strategy P&L |
| Mercury 2 | [mercury2/](https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/mercury2/) | XGBoost ensemble, direction stats |
| KIMI | [riseoftheclaw.html](https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/riseoftheclaw.html) | 81 algorithms |
| Battleground Arena | [battleground/](https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/battleground/) | 5 systems |
| Claws of Doom | [CLAWSOFDOOM](https://eltonaguiar.github.io/CLAWSOFDOOM/) | 6 strategies, 10 symbols |
| Cross Aggregator | [monitor/](https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/monitor/) | Consensus picks |
| Crypto ML Edge | [edge/](https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/edge/) | LightGBM, DSR-gated |

---

## CHANGES LOG (Feb 26, 2026)

### Round 1 — Performance Overhaul
- Alpha Engine: killed 11 dead strategies, direction restrictions, SL widened, ML patience
- System B: regime confidence 90% → 55% at F&G<15
- System D: funding rate API retries + cache
- System E: PANIC/BUY contradiction fix

### Round 2 — System Fixes
- Health gate: `min()` → `max()` for confidence calc, lower thresholds
- Claws of Doom: 3 → 10 symbols, smart rounding for sub-$1 coins (v3.2.1)
- KIMI table: removed 7 unused header columns
- System C dashboard: "MODEL TRAINED" → "HEURISTIC MODE"
- Mercury 2: added SHORT explanation note
- Updates page: corrected Claws/Edge/Mercury stats

---

*Previous blueprint: [v2 (Feb 25)](BLUEPRINT_ANALYSIS_v2.md)*
