# TRACE_LOG — Active / Smart / Verified Alpha Pick Trace (v2)

**Date:** 2026-04-06T18:18 EDT  
**Source:** `audit_trail/data/dashboard_payload.json` + `alpha_engine/data/closed_picks.json` + `ejaguiar1_stocks` SQL extract  
**Purpose:** Trace every live pick, find edge patterns, identify scoring flaws by asset class

---

## Policy note — Smart anti-overfit exception (2026-04-02)

**Change:** In `audit_trail/quality_gates.py`, the anti-overfit registry block that hard-stops Smart eligibility **does not apply** when `asset_class == CRYPTO` **and** `research_cohort == "verified_alpha"` (dashboard-stamped VA only).

**Tradeoff:** Restores a narrow path for live, forward-tagged VA crypto rows to reach Smart without expanding the walk-forward registry for all strategies. **Risk:** A VA-tagged row could still carry strategy-level overfit; mitigation is the cohort stamp + all other Smart clauses (score floor, trust, forward_wr, R:R, etc.) remaining unchanged. **Non-goal:** This does **not** exempt EQUITY/FOREX or non–`verified_alpha` crypto from anti-overfit.

**Ops:** Run `python tools/audit_smart_gate_funnel.py` on the current dashboard JSON to see first-failure histograms after any gate change.

---

## System State at Trace Time

| Metric | Value |
|--------|-------|
| Active picks (raw) | 180 |
| Active picks (after quality gates) | 113 |
| Smart Picks | 0 (NONE) |
| Verified Alpha | 47 picks from 10 sources |
| ELITE tier | 0 |
| PREMIUM tier | 1 |
| STANDARD tier | 80 |
| WATCH tier | 29 |
| Degradation severe | 7 strategies |
| Degradation high | 3 strategies |
| Degradation lifting | 34 strategies |

---

## Part 1: Verified Alpha Picks (47 picks)

Top VA picks by smart score:

| # | Symbol | Dir | Smart | Elite | Conf | Strategy | Source |
|---|--------|-----|-------|-------|------|----------|--------|
| 1 | FETUSDT | LONG | 86 | 85 | 0.800 | ml_enhanced_FETUSDT_1d_B_lightgbm | alpha_engine |
| 2 | SHIBUSDT | LONG | 75 | 52 | 0.832 | super signal (strong) | super_signals |
| 3 | RENDERUSDT | LONG | 73 | 52 | 0.920 | super signal (super) | super_signals |
| 4 | INJUSDT | LONG | 72 | 51 | 0.990 | super signal (super) | super_signals |
| 5 | TAOUSDT | LONG | 69 | 46 | 0.700 | tsmom_volscaled | tsmom_strategy |
| 6 | DOGEUSDT | SHORT | 67 | 58 | 0.783 | kalshi_mtf_consensus | pm_kalshi_signals |
| 7 | AVAXUSDT | LONG | 64 | 52 | 0.990 | super signal (super) | super_signals |
| 8 | TRUUSDT | LONG | 63 | 17 | 0.850 | tsmom_volscaled | tsmom_strategy |
| 9 | DOTUSDT | LONG | 62 | 29 | 0.990 | super signal (super) | super_signals |
| 10 | HBARUSDT | LONG | 62 | 10 | 0.990 | super signal (super) | super_signals |

VA strategy closed-pick history: only `ml_enhanced_FETUSDT` has history (88% WR). All others are untested.

---

## Part 2: Active Pick Trace by Asset Class

### CRYPTO — 84 active picks

| Symbol | Dir | Smart | Elite | Conf | Strategy | Closed History |
|--------|-----|-------|-------|------|----------|---------------|
| FETUSDT | LONG | 86 | 85 | 0.800 | ml_enhanced_FETUSDT_1d | **88% WR, +0.330% avg** |
| SHIBUSDT | LONG | 75 | 52 | 0.832 | super signal (strong) | No history |
| RENDERUSDT | LONG | 73 | 52 | 0.920 | super signal (super) | No history |
| INJUSDT | LONG | 72 | 51 | 0.990 | super signal (super) | No history |
| TAOUSDT | LONG | 69 | 46 | 0.700 | tsmom_volscaled | No history |
| DOGEUSDT | SHORT | 67 | 58 | 0.783 | kalshi_mtf_consensus | No history |
| AVAXUSDT | LONG | 64 | 52 | 0.990 | super signal (super) | No history |
| TRUUSDT | LONG | 63 | 17 | 0.850 | tsmom_volscaled | No history |
| DOTUSDT | LONG | 62 | 29 | 0.990 | super signal (super) | No history |
| HBARUSDT | LONG | 62 | 10 | 0.990 | super signal (super) | No history |
| BTCUSDT | LONG | 60 | 38 | 0.706 | pm_whale_0x6e1d50 | No history |
| XRPUSDT | LONG | 58 | 54 | 0.818 | drawdown_recovery_rsi_xrp | No history |
| BNBUSDT | SHORT | 57 | 100 | 0.650 | breakout_b_ml | No history |
| SOLUSDT | LONG | 55 | 27 | 0.990 | super signal (super) | No history |
| TAOUSDT | LONG | 47 | 90 | 0.688 | quan_engine | **27.6% WR, -0.137% avg** |
| LINKUSDT | LONG | 45 | 81 | 0.650 | breakout_b_ml | No history |

### EQUITY — 27 active picks (all goldmine_consensus)

| Symbol | Smart | Elite | Conf | Strategy |
|--------|-------|-------|------|----------|
| WFC | 30 | 20 | 0.873 | goldmine_1x_consensus |
| UNH | 30 | 20 | 0.841 | goldmine_1x_consensus |
| LLY | 30 | 20 | 0.942 | goldmine_1x_consensus |
| NVDA | 30 | 20 | 0.753 | goldmine_6x_consensus |
| GOOGL | 30 | 18 | 0.743 | goldmine_6x_consensus |
| AAPL | 30 | 28 | 0.673 | goldmine_4x_consensus |
| AMZN | 30 | 28 | 0.686 | goldmine_4x_consensus |
| ... | ... | ... | ... | goldmine_*_consensus |

All 27 equity picks: smart_score 15-30, elite 18-28, no closed history.

### FOREX — 3 active picks

| Symbol | Dir | Smart | Elite | Conf | Strategy |
|--------|-----|-------|-------|------|----------|
| NZDUSD=X | LONG | 21 | 29 | 0.850 | non_crypto_consensus |
| USDCAD=X | LONG | 21 | 34 | 0.9999 | regime_terminal |
| USDCHF=X | LONG | 21 | 34 | 0.9967 | regime_terminal |

---

## Part 3: Direction Conflicts

| Symbol | Dir 1 | Score 1 | Strategy 1 | Dir 2 | Score 2 | Strategy 2 |
|--------|-------|---------|-----------|-------|---------|-----------|
| XRPUSDT | LONG | 58 | drawdown_recovery_rsi | SHORT | 0 | contrarian_consensus_flip |
| BNBUSDT | SHORT | 57 | breakout_b_ml | LONG | 0 | enhanced_ml_A_xgboost |
| SOLUSDT | LONG | 55 | super signal | SHORT | 5 | keltner_compression |
| APEUSDT | LONG | 33 | enhanced_ml_A_xgboost | SHORT | 0 | ml_enhanced_APEUSDT |
| USDCHF=X | LONG | 21 | regime_terminal | SHORT | 0 | non_crypto_consensus |

5 symbols with opposite-direction picks. In 4/5 cases LONG scored higher — but SHORT has 47.7% WR vs LONG 29.5% in closed picks.

---

## Part 4: Edge Patterns

### Pattern 1: FETUSDT — The Golden Symbol
- Active: smart_score=86, elite=85, conf=0.80, LONG
- Closed: 38 trades, **84.2% WR**, +0.229% avg, +8.70% total
- Only active pick with proven closed history AND high scores.

### Pattern 2: super_signals — Untested but High Scores
- 8 active picks, smart_score 52-75, conf 0.83-0.99
- Zero closed-pick history
- Scoring flaw: new strategies get credit for "agreement count" without performance validation.

### Pattern 3: goldmine_consensus — Untested Equities
- 27 active picks, smart_score 15-30, elite 18-28
- Zero closed-pick history
- Low scores + no history = watchlist items, not active picks.

### Pattern 4: quan_engine — Known Loser Still Active
- 2 active picks (TAOUSDT smart=47, HYPEUSDT smart=44)
- Closed: 2,718 trades, 27.6% WR, -373.44% total PnL
- No auto-kill mechanism for catastrophic strategies.

### Pattern 5: Direction Bias — 95% LONG
- ~80 LONG vs ~4 SHORT in crypto active picks
- Closed: SHORT 47.7% WR, LONG 29.5% WR
- System is massively LONG-biased despite SHORT performing 61% better.

---

## Part 5: SQL Database Edge (ejaguiar1_stocks)

### Key Tables With Untapped Edge

| Table | Rows | Edge |
|-------|------|------|
| `at_strategy_symbol_performance` | 157 | Per-strategy per-symbol WR/PnL — could feed symbol-level scoring |
| `at_permutation_snapshots` | 29 | **solo_battleground: 60.2% WR, 669 trades, +3101% PnL** — PROVEN, not in live |
| `algorithm_rolling_perf` | 60 | Time-varying WR — could detect improving strategies |
| `at_incubator_backtest_results` | 51 | ATR-based TP/SL tested but not deployed |
| `alpha_factor_scores` | 8 | Fundamental factor data for stocks |
| `alpha_picks` | 68 | Stock picks with conviction/horizon/risk |

### Critical Finding: solo_battleground

From `at_permutation_snapshots`:
- total_trades: 669
- wins: 403 (60.2% WR)
- total_pnl: +3101.46%
- avg_win: 4.64%, avg_loss: 1.61%
- trust_tier: 'Highly Trusted'

**This permutation has 60.2% WR on 669 trades with +3101% total PnL. It is NOT in the active pick book.** This is the single biggest missed edge.

---

## Part 6: Edge by Asset Class

### CRYPTO
| Edge | Evidence | Action |
|------|----------|--------|
| FETUSDT ML | 84.2% WR, 38 trades | KEEP — proven |
| solo_battleground | 60.2% WR, 669 trades | **PROMOTE TO LIVE** |
| SHORT direction | 47.7% WR vs 29.5% | Increase SHORT allocation |
| SWING mode | +0.874% avg | Expand from 2.4% to 15-20% |
| Confidence >= 0.8 | 79.3% WR | Filter harder |

### EQUITY
| Edge | Evidence | Action |
|------|----------|--------|
| goldmine_consensus | No history | Watchlist only |
| Connors RSI-2 SPY | 75.7% WR, p=6e-6 | **DEPLOY** |

### FOREX
| Edge | Evidence | Action |
|------|----------|--------|
| regime_terminal | No history | Monitor |
| Bollinger bounce | 65.3% WR OOS | **DEPLOY after fwd validation** |

---

## Part 7: Critical Flaws

| # | Flaw | Impact |
|---|------|--------|
| 1 | Smart Picks = 0 | Best-of-best feature producing nothing |
| 2 | 97% of picks have no closed history | Untested strategies dominate |
| 3 | ELITE=0, PREMIUM=1 | No differentiation in scoring |
| 4 | 5 direction conflicts unresolved | Portfolio contradictions |
| 5 | quan_engine still active (-373% PnL) | No auto-kill mechanism |
| 6 | solo_battleground NOT in live picks | 60.2% WR edge wasted |
| 7 | ATR TP/SL tested in incubator but not deployed | Fix exists but unused |
| 8 | Confidence 0.6-0.7 (58% of trades) is anti-predictive | 23.3% WR in this band |

---

## Fleet: Redis bus & changelog

This artifact is registered for cross-agent discovery in **`docs/REDIS_BUS_CHANGELOG.md`** (Recent broadcasts: `trace_log_active_smart_verified`; Related docs table). To push a short summary to the fleet: **`python tools/bus_post_trace_log.py`** → publishes to `alpha_engine_bus` and **`LPUSH`**es a one-line entry on **`bus:broadcast:log`**.
