# Edge Addendum — Finding Consistent TP/SL Profit

**Date:** 2026-04-06  
**Context:** Smart Picks / Active Picks have been "on and off" with no consistent edge for simple TP/SL trades  
**Root cause:** Three-layer disconnect between scoring and execution

---

## Part 1: The Diagnosis — Why We Can't Find Consistent Edge

### The -0.91 Correlation (The Smoking Gun)

Backtest WR vs Forward WR across strategies: **Pearson r = -0.91**. This means 84% of the variance in forward performance is explained by the INVERSE of backtest performance. Higher backtest WR = worse forward results.

| Strategy | Backtest WR | Forward WR | Drop |
|----------|-------------|-----------|------|
| `drawdown_recovery_rsi` | 100% | 16.7% | -83.3pp |
| `keltner_compression_expansion_xrp` | 86.7% | 21.4% | -65.3pp |
| `keltner_compression_expansion_eth` | 87.5% | 37.5% | -50.0pp |
| `st_rsi_momentum_confluence` | 65.1% | 65.1% | **0pp (ROBUST)** |

The system is optimized to select the most overfit strategies. The more "perfect" a backtest looks, the more catastrophically it fails forward.

### Three Fatal Disconnects

**Disconnect 1: Synthetic Data Optimization**
`comprehensive_backtest.py` generates strategies on synthetic price data (`seed=42`). 635+ strategies are grid-searched against a toy regime-switching model. Zero correlation with real market dynamics. These strategies are memorizing random noise.

**Disconnect 2: elite_score is Noise (ρ = +0.012)**
The 25+ component elite_score has near-zero predictive power because:
- 4 predictive components (ml_score, regime, forward_wr, technical) are diluted by 21 noise components
- `ml_crypto_predictor` system was toxic (PF 0.15, 365 picks at score=60 with -8% to -10% PnL)
- 94% of picks have NO forward data for the most heavily-weighted component (forward_wr)

**Disconnect 3: TP/SL Levels Are Wrong (78.9% Hit SL)**
Even when direction is correct, the TP/SL levels don't account for:
- Current volatility regime (ATR)
- Support/resistance proximity
- Volume profile / liquidity zones

Result: 78.9% of trades hit SL — not because direction was wrong, but because SL was too tight for the noise.

### The DNA Mutation System — Sophisticated Infrastructure, Zero Edge

| Metric | Value |
|--------|-------|
| Live mega mutation WR | 14.3% (1W, 6L) |
| Tournament backtest claims | 75-87% |
| Super mutation (combining parents) | -9.71% combined PnL |
| Parents' individual PnL | +50-150% |
| All 7 closed picks outcome | All hit stop-loss |
| Forward test variants | 0 picks generated |

Combining good strategies makes them worse. The mutation system's only value is identifying which SYMBOLS are most predictable (JUPUSDT, AAVEUSDT, ONDOUSDT), not which strategy combinations work.

### What Actually Survives Walk-Forward Validation

Out of 260 strategies analyzed:
- **1 ROBUST** (0.4%): `st_rsi_momentum_confluence` — 65.1% WR, PF 2.53, 258 trades, no edge decay
- **8 FRAGILE** (3.1%): Work in some windows, fail in others
- **251 INSUFFICIENT** (96.5%): Not enough data or failing OOS

---

## Part 2: What Backtesting Actually Works

### The Current Methodology is Fundamentally Broken

| Problem | Impact |
|---------|--------|
| Synthetic data (seed=42) | Strategies memorize random noise |
| 635+ grid search with no multiple-testing correction | Random noise produces 60%+ WR by chance |
| No walk-forward gate before promotion | Overfit strategies go live |
| Transaction costs underestimated (0.15% vs real 0.25%) | Thin-margin strategies show false profits |
| No embargo/purge gap in train/test split | Information leakage at boundaries |
| Small samples (<20 forward trades) | Statistically meaningless |

### What Works — The Anti-Overfit Pipeline

The `quan_engine/backtest/anti_overfit.py` has a well-designed 8-check suite that's **never enforced**. The correct pipeline:

```
1. Backtest on REAL data (2+ years, 10+ symbols)
2. Walk-forward validation (rolling windows, 1-2 week embargo)
3. Anti-overfit 8-check suite (ALL must pass):
   - OOS Sharpe ≥ 70% of IS Sharpe
   - OOS WR within 10pp of IS WR
   - Profit factor > 1.5 in ALL OOS windows
   - KS test p > 0.05 (distributions similar)
   - Profitable in ≥ 67% of OOS windows
4. Deflated Sharpe Ratio > 0.5 (corrects for 635 strategies tested)
5. Minimum 100 OOS trades (ML strategies: 1,000+)
6. Realistic transaction costs (0.25% round-trip, not 0.15%)
7. Only THEN allow live deployment
```

### What the Academic Literature Says Works

From `QUANTITATIVE_VALIDATION_REPORT.md`, the 23 strategies with mathematically demonstrable edge all share:
1. **Decades of academic validation** (30-90 years of data)
2. **Thousands of trades** (1,000-50,000+)
3. **Economic rationale** (risk premium, behavioral bias, structural friction)
4. **Low decay rates** (risk premium λ=0.05, meaning 95% edge retention after 1 year)

The strategies that work in our system match this pattern:
- Connors RSI-2: p=0.000006, cross-asset validated (SPY 75.7%, QQQ 75%, BTC 62%)
- VIX Spike Reversal: p=0.022, 10-year backtest
- `st_rsi_momentum_confluence`: 258 forward trades, consistent across 4/5 windows

---

## Part 3: Non-Crypto Asset Class Analysis

### Overall Non-Crypto Performance

| Asset Class | Trades | Win Rate | Profit Factor | PnL | Verdict |
|-------------|--------|----------|---------------|-----|---------|
| **CRYPTO** | 1000+ | 42.8% | 1.26 | **+3,818%** | PROVEN EDGE |
| **EQUITY** | 762 | 31.8% | 0.63 | **-617%** | CATASTROPHIC |
| **FOREX** | 146 | 30.1% | 0.53 | **-41%** | CATASTROPHIC |
| **COMMODITY** | 155 | 47.7% | ~0.9 | **-10%** | MARGINAL LOSER |
| **FUTURES** | 3 | 0.0% | 0.0 | **-1.35%** | TOO SMALL |
| **ETF** | 12 | 42% | 0.34 | **-11%** | LOSER (raw) / 75% WR (filtered) |

### Forex — What Works and What's Broken

**Working (backtest only, not forward-validated):**
| Strategy | WR | PF | Trades | Status |
|----------|-----|-----|--------|--------|
| Portfolio C (Multi-TF) | 45.9% | 1.30 | 244 | Best portfolio, Sharpe 2.06 |
| Bollinger bounce (OOS) | 65.3% | 999 | 501 | Statistically significant — should be promoted |
| RSI reversal (OOS) | 60.6% | 43.4 | 165 | Statistically significant — should be promoted |
| carry_trade_momentum | 43.3% | 1.15 | 215 | PROBATION |

**Killed/Broken:**
| Strategy | Issue |
|----------|-------|
| `forex_logistic_direction` | 0W, 100% SL rate — anti-predictive |
| `community_london_breakout_v2_forex` | 0W/6L — needs tick data, daily bars kill it |
| `cta_tsmom_blend` | 31% WR, PF 0.71 — losing money |
| `forex_tsmom_12m` | 34% WR, PF 0.80 — losing money |

**Critical bug:** `session_momentum_continuation` still has `tp_mult=2.5` (should be 1.2x) — same root cause that gave forex 0% WR originally.

### Equity/Stocks — What Works and What's Broken

**Working:**
| Strategy | WR | Trades | Notes |
|----------|-----|--------|-------|
| Connors RSI-2 (SPY) | 75.7% | p=6e-6 | Sharpe 4.84, 5yr backtest — BEST non-crypto signal |
| VIX Spike Reversal | 72% | 10yr backtest | Sharpe 6.20, p=0.022 |
| Triple RSI (SPY) | 75% | 12 trades | Published 90% WR over 20yr |
| `momentum_relative_strength` | 49.7% | PF 1.37 | Best variation (165 trades) |

**Catastrophic (must kill):**
| Strategy | WR | Trades | PnL |
|----------|-----|--------|-----|
| Alpha Factor Low Vol | 3.37% | 326 | CATASTROPHIC |
| Alpha Factor Safe Bets | 3.82% | 314 | CATASTROPHIC |
| Alpha Factor Composite | 4.15% | 313 | CATASTROPHIC |
| Alpha Factor Value | 4.51% | 266 | CATASTROPHIC |
| `quan_engine_scalp` | 25% | — | -353% (worst total loss) |

### ETFs — The Hidden Edge

**Leveraged ETF Decay Shorts are the best non-crypto edge after Connors RSI-2:**
| Strategy | WR | PF | Trades |
|----------|-----|-----|--------|
| Leveraged ETF Decay (LABD SHORT) | 76.9% | 2.94 | 39 |
| Leveraged ETF Decay (JDST SHORT) | 69.0% | 1.86 | 29 |
| Leveraged ETF Decay (SOXS SHORT) | 65.6% | 1.61 | 32 |

The structural decay of 3x leveraged bear ETFs in non-trending markets creates a mechanical edge — similar to funding rate contrarian in crypto. This is NOT pattern-based; it's a structural market mechanic.

### Commodities/Futures — Near Break-Even

- COMMODITY: 47.7% WR, SL:TP ratio 0.99 — well calibrated but no edge
- COT positioning: theoretically sound but CFTC API unreliable
- `futures_momentum`: 48.7% WR on 158 trades — only futures strategy with real track record

---

## Part 4: The Concrete Edge Plan — 7 Actions to Consistent Profit

### Action 1: Kill the Noise — Keep Only Validated Strategies

**Immediate purge:** Remove 150+ unvalidated strategies from live scoring. Keep ONLY:
- Crypto: `st_rsi_momentum_confluence` (65.1% WR, 258 trades), VWAP Mean Reversion (64.1% WR, 741 trades), `st_fear_greed_contrarian` (87.7% WR)
- Equity: Connors RSI-2 on SPY/QQQ only, VIX Spike Reversal
- ETF: Leveraged ETF Decay Shorts (JDST, LABD, SOXS)
- Forex: Bollinger bounce and RSI reversal (once forward-validated with 50+ trades)

Everything else is overfit noise degrading the signal.

### Action 2: Implement ATR-Based Dynamic TP/SL

The fixed TP/SL approach is the single biggest mechanical failure (78.9% SL hit rate). Replace with:

```
TP = entry ± (ATR_14 × tp_multiplier)
SL = entry ± (ATR_14 × sl_multiplier)
```

Where `tp_multiplier` and `sl_multiplier` are calibrated per symbol from recent volatility:
- High-vol symbols (DOGE, PEPE): wider SL (2.5x ATR), wider TP (4x ATR)
- Low-vol symbols (BTC, ETH): tighter SL (1.5x ATR), tighter TP (2.5x ATR)

This has been identified since Feb 18 and **still hasn't been implemented** (7 weeks).

### Action 3: Deploy Structural Edges

These exploit market mechanics, not patterns — inherently more robust:

| Edge | Forward Grade | Why It Works |
|------|---------------|--------------|
| **Funding Rate Arbitrage** | Grade A (FW expectancy 1.02, correlation 0.92) | Funding rates mean-revert; extreme funding = contrarian signal |
| **Pairs Trading (Cointegration)** | Grade A- (correlation 0.85) | Statistical arbitrage on correlated pairs |
| **Leveraged ETF Decay** | Grade A (55-77% WR) | Structural decay of 3x bear ETFs |
| **Connors RSI-2** | Grade A (p=6e-6) | Academic validation, cross-asset |

### Action 4: Fix the Forward Validation Gate

No strategy should go live without:
- Minimum 30 forward test trades (or 50 for non-crypto)
- Walk-forward consistency score ≥ 60/100
- DSR > 0.5 after multiple-testing correction

The forward validation gate has been broken for 7 weeks. `live_forward_test_picks.json` has 0 picks.

### Action 5: Add Regime Gating

| Regime | Best Strategy Type | Our Data |
|--------|-------------------|----------|
| **Ranging** | Mean-reversion | 92.3% WR — strongest regime signal |
| **Bull/Trending** | Momentum continuation | Crypto LONG 43% WR |
| **Bear** | Contrarian shorts | SHORT 66% WR in fear regime |
| **Crisis (VIX > 30)** | VIX reversal only | VIX-exempt strategies only |

Don't run breakout strategies in ranging markets. Don't run mean-reversion in trending markets. The regime IC (+0.19) is the second strongest predictor — use it as a strategy router, not just a score component.

### Action 6: Symbol Tier Hard Filter

Paper trade analysis showed:
- **Tier 1 (BTC, ETH, SOL, BNB, DOGE):** All profitable
- **Micro-caps (REZ, RESOLV, KITE):** All lost, regardless of score

Hard-filter to Tier 1/2 coins only. Micro-caps lose regardless of how high the score is.

### Action 7: Fix Non-Crypto Scoring (from NON_CRYPTO_SCORING_ERRORS.md)

10 bugs identified — priority fixes:
1. Unify asset-class classifier (commodity/ETF misclassification)
2. Apply VIX confidence in Smart Picks (never called)
3. Sort non-crypto by smart_score (not crypto-trained ml_composite)
4. Lower non-crypto raw score bypass threshold (88% WR is unreachable)

---

## Part 5: The Mean-Reversion Thesis — Our Actual Edge

### What Crypto Data Proves

100% of surviving strategies are mean-reversion based:
- VWAP Mean Reversion: 64.1% WR (741 trades)
- RSI-2: 62% WR on BTC (Connors adaptation)
- Bollinger/Keltner compression: 75% WR on BTC
- `st_fear_greed_contrarian`: 87.7% WR (buy extreme fear)

**Why:** Crypto is dominated by retail overreaction → prices overshoot → mean-revert. This is a structural, persistent edge — not a pattern that decays.

### Non-Crypto Analogs

| Crypto Edge | Non-Crypto Equivalent | Status |
|-------------|----------------------|--------|
| RSI-2 mean reversion | Connors RSI-2 on SPY/QQQ | 75.7% WR, p=6e-6 — READY |
| Fear/Greed contrarian | VIX Spike Reversal | 72% WR, p=0.022 — READY |
| Funding rate contrarian | Leveraged ETF Decay Shorts | 77% WR — READY |
| Keltner compression | Bollinger bounce (forex) | 65.3% WR OOS — NEEDS 50+ FWD TRADES |

### The Unifying Principle

**Trade the overreaction, not the trend.** Every successful strategy in the system exploits overshooting:
- Crypto: retail panic/frenzy → mean-reversion
- Equity: VIX spikes → contrarian buy
- ETF: leveraged decay → short bear ETFs
- Forex: Bollinger overshoot → bounce

The system has been trying to be a trend-follower AND a mean-reverter simultaneously. Pick one: **we're a mean-reversion shop**. Build the entire pipeline around that identity.

---

## Summary: The Path to Consistent TP/SL Profit

| Priority | Action | Expected Impact |
|----------|--------|-----------------|
| 1 | Kill 150+ unvalidated strategies, keep 5-8 proven | Remove noise, signal clarity |
| 2 | ATR-based dynamic TP/SL | Fix 78.9% SL hit rate |
| 3 | Deploy structural edges (funding arb, ETF decay, Connors RSI-2) | Add 3-4 Grade A edges |
| 4 | Fix forward validation gate | Prevent overfit strategies going live |
| 5 | Regime-gate strategy selection | Route to best strategy per regime |
| 6 | Symbol tier hard filter | Remove micro-cap losers |
| 7 | Fix non-crypto scoring bugs | Correct classification/caps |
| 8 | Embrace mean-reversion identity | Coherent system design |
