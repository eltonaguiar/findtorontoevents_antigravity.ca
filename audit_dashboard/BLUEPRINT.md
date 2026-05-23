# Trading System Blueprint — Full Architecture & Status

> **Last Updated:** Mar 11, 2026 (v3: Consensus findings + Scalping strategies + Genome integration)
> **Status:** GOING-LIVE PREP — Risk engine deployed, confidence calibrated, genome wired, KIMI restarted
> **Related Docs:** [LEARNINGS.md](LEARNINGS.md) | [Live Dashboard](claudes_test.html) | [Cross-Aggregation](../cross_aggregation/SYSTEM_ARCHITECTURE.md) | [Giga Potato Feedback](../BLUEPRINT_FEEDBACK_20260311_GIGAPOTATO.MD)

---

## Purpose

Multi-portfolio, multi-system trading architecture **preparing for live deployment within days**:
1. Forward-test which strategies actually work in live market conditions
2. Compare methodologies (signal-based vs deep-value vs prop firm vs genetic evolution)
3. Identify the minimum viable set of strategies worth deploying with real capital
4. Beat GIC (3.4-3.85%) and mutual fund (~13%) benchmarks

**Current reality:** Persistent negative expectancy is being addressed with statistical risk management (ATR, z-score, Kelly sizing, VaR-lite risk budgets). Going-live readiness gates now enforce minimum statistical significance before strategies can trade real money.

---

## System Architecture Overview

```
                         ┌──────────────────────────────────────────┐
                         │           12+ TRADING SYSTEMS            │
                         ├──────────────────────────────────────────┤
                         │ Alpha Engine (100 strats, 30min cycle)   │
                         │ KIMI Rise of the Claw (81 algos) [DEAD] │
                         │ ML Battleground (Systems A/B/C/D/E/F)   │
                         │ Mercury2 Scanner [DEGRADED]              │
                         │ Coinglass Strategies                     │
                         │ Breakout Systems (B/C)                   │
                         │ ML Crypto Predictions                    │
                         │ RL Agent (PPO)                           │
                         │ Genome DNA Evolution                     │
                         └─────────────┬────────────────────────────┘
                                       │ active_picks.json (per system)
                                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    CROSS-SYSTEM AGGREGATOR                          │
│  aggregator.py → regime_router.py → pick_classifier.py             │
│  ┌───────────────┐  ┌──────────────┐  ┌─────────────────────────┐  │
│  │ Regime Router  │  │ Consensus    │  │ Pick Classifier         │  │
│  │ F&G, ADX, EMA │  │ ≥2 systems   │  │ ELITE / PROVEN / EXPER  │  │
│  │ Blocks mismatc │  │ agree on dir │  │ Routes to Discord tier  │  │
│  └───────────────┘  └──────────────┘  └─────────────────────────┘  │
└─────────────────────────┬───────────────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
┌─────────────────┐ ┌────────────┐ ┌─────────────────┐
│ Consensus       │ │ Super      │ │ 22 Portfolio     │
│ Outcome Tracker │ │ Signal     │ │ Manager          │
│ (46 tracked)    │ │ Engine     │ │ (claudes_test)   │
│ 51.9% WR       │ │ 8-sys max  │ │ $10K-$200K each  │
└─────────────────┘ └────────────┘ └─────────────────┘
          │                               │
          ▼                               ▼
┌─────────────────┐              ┌─────────────────┐
│ Discord Alerts  │              │ Portfolio State  │
│ Tiered channels │              │ claudes_test_    │
│ 30min cooldown  │              │ state.json       │
└─────────────────┘              └─────────────────┘
```

---

## Active Trading Systems — Health Status

| System | File | Status | WR | Trades | Notes |
|--------|------|--------|-----|--------|-------|
| **Alpha Engine** | `alpha_engine/scanner.py` | Active (30min) | 35.9% | 156 | 100 strategies, negative expectancy |
| **Battleground** | `audit_trail/` | Active | 64.1% | 334 | **Best performer**, +1357% cum PnL |
| **KIMI v11.2** | `KIMI_RISEOFTHECLAW/live_scanner.py` | RESTARTED | 40% (consensus) | 67 algos | Workflow fixed Mar 11 (.db blocking git push) |
| **Mercury2** | `mercury2/` | DEGRADED | ~0% | 46 losses | Model validation failed |
| **ML Battleground** | `ml_battleground/` | Mixed | Varies | — | Systems A/B/C at 0% WR |
| **Coinglass** | `coinglass/` | Active | — | — | OI/funding data feed |
| **Genome DNA** | `genome/` | INTEGRATED | 68% avg backtest | 102 picks | 3 engines wired to aggregator (Mar 11) |
| **Cross-Aggregator** | `cross_aggregation/` | Active (5min) | 51.9% | 46 | Confidence calibrated, genome added |

---

## The 22 Portfolios

### Signal-Based (12 portfolios, $10K each)

| Portfolio | Methodology | Selection Logic | Current Status |
|-----------|-------------|-----------------|----------------|
| Score Leaders | Composite score | Top by Kelly + expectancy + R:R | Only consistent winner (+$34) |
| Proven Only | Quality filter | WR >= 45%, closed >= 5 | Dormant (few strategies qualify) |
| Momentum Riders | Trend following | Highest unrealized PnL picks | Dormant |
| Contrarian | Counter-trend | SHORT in bull, LONG in bear | Empty by design (rare signals) |
| Regime Aligned | Regime match | Direction matches market regime | Active |
| High Conviction | Multi-asset filter | CRYPTO: conf>=0.75+score>=60 or trust>=6+fwdWR>=55% | EQUITY: score>=65 or trust>=4+fwdWR>=40% or winning strats/symbols | FOREX: Bollinger strats or trust>=4+fwdWR>=35% or score>=70 | ETF: score>=65 or trust>=5+fwdWR>=45% | COMMODITY: GLD/SLV/USO symbols or trust>=6+fwdWR>=50%+score>=75 | FUTURES: very strict (trust>=7+fwdWR>=60%+score>=80) | Active |
| R:R Kings | Risk/reward | R:R >= 1.8 (fallback 1.5) | Active |
| Consensus Plays | Agreement | Highest multi-system agreement | Active |
| Fresh Signals | Recency | Age < 4 hours, WR >= 45% | Active |
| Sector Rotation | Diversification | Max 3 crypto + 2 equity + 1 forex | Active |
| Anti-Meme | Quality filter | Exclude DOGE, SHIB, PEPE, etc. | Active |
| Claude's Best | Hybrid | Proven + regime + R:R >= 1.2 + no meme | Active |

### Deep-Value "Buy the Blood" (4 portfolios, $10K each)

| Portfolio | Entry Signal | TP | SL |
|-----------|-------------|----|----|
| Deep Drawdown DCA | Drawdown > 25% from 90d high | 50% recovery | 10% below entry |
| RSI Capitulation Sniper | RSI(14) < 35 + 3% bounce | 15% up | 8% down |
| Fear & Greed Contrarian | F&G <= 25 + top-10 cap | 10% up | 7% down |
| Relative Strength Recovery | Weakest 30d + bounce confirm | Mean reversion | 8% down |

### Hoffman + Higher Timeframe (3 portfolios, $10K each)

| Portfolio | Methodology | Backtest WR |
|-----------|-------------|-------------|
| Hoffman Elite Combo | IRB + RSI(2) + Volume + daily uptrend | 78.9% (19 trades) |
| HTF Trend Follower | Weekly + daily EMA alignment | ~55-60% |
| HTF Weekly Momentum | EMA 9>21>50 stack, buy pullbacks | ~58-65% |

### Prop Firm Challenge (3 portfolios, $100K-$200K)

| Portfolio | Capital | Daily Loss Limit | Max DD | Profit Target | Status |
|-----------|---------|-----------------|--------|--------------|--------|
| Conservative | $100K | 4% | 8% | 8% | Losing (-$50) |
| Aggressive | $100K | 6% | 10% | 10% | Losing (-$33), 6.97% DD |
| Swing Trader | $200K | 5% | 10% | 8% | Active |

---

## Performance Reality Check — The Struggle

### Headline Numbers (Honest Assessment)

| Metric | Alpha Engine | Battleground | KIMI | Consensus Tracker |
|--------|-------------|--------------|------|-------------------|
| Win Rate | 35.9% | 64.1% | 23.1% | 51.9% |
| Profit Factor | 0.71 | >1.5 | <1.0 | ~1.3 |
| Expectancy | **-3.24%** | Positive | Negative | +1.12%/trade |
| Cum PnL | +12.2% per win but net negative | +1357% | Negative | +30.32% |
| Status | Losing money | **Only real winner** | Dead | Promising but small sample |

### Why We're Losing (Root Cause Analysis)

#### Problem 1: Signal Noise (81-100 strategies competing)
- **Symptom:** 1,540 picks from 81 systems in Alpha Engine, most are garbage
- **Impact:** Good signals drowned by bad ones; same bad strategy appears in 10+ portfolios
- **Evidence:** Only 5 strategies have forward-validated WR > 60%
- **Proposed fix:** Filter to top 5-10 proven strategies only (see `portfolio_survival_improvements.md`)

#### Problem 2: Asymmetric Losses
- **Symptom:** Avg win +17.73% vs avg loss -19.85%
- **Impact:** Even at 50% WR, you lose money (winners are smaller than losers)
- **Evidence:** Fixed TP/SL creates ceiling on winners but no floor on losers
- **Proposed fix:** Trailing stops after +5% profit; ATR-based dynamic SL

#### Problem 3: No Volatility/Regime Awareness
- **Symptom:** Running breakout strategies in choppy/ranging markets
- **Impact:** False breakouts trigger SL hits repeatedly
- **Evidence:** KIMI research (Feb 26): "The single change that would most improve WR: strict regime-strategy router"
- **Proposed fix:** ADX < 20 → only allow mean-reversion strategies

#### Problem 4: Strategy-Asset Mismatch
- **Symptom:** Same strategy has 72% WR on BTC but 33% on ETH
- **Impact:** Blended WR masks that strategy only works on specific assets
- **Evidence:** Keltner Compression: BTC +490% PnL vs ETH -458% PnL
- **Proposed fix:** Symbol-locking (partially implemented)

#### Problem 5: KIMI System Died
- **Symptom:** Scanner stopped Mar 1, 2026 — 10 days of no picks
- **Impact:** 94 zombie positions stuck open, no TP/SL validation
- **Evidence:** GitHub Actions workflow not executing
- **Proposed fix:** Needs restart investigation; may need complete rebuild

#### Problem 6: Database Fragmentation
- **Symptom:** 35 SQLite databases across the project
- **Impact:** Cannot trace a live trade back to the strategy formula that generated it
- **Evidence:** Same strategies exist with different IDs across DBs
- **Proposed fix:** Consolidate to single MySQL `ejaguiar1_stocks` or unified SQLite

#### Problem 7: Genome/DNA Evolution Not Integrated
- **Symptom:** 100+ evolved GP strategies, 35 MAP-Elites cells — but 0 forward trades
- **Impact:** Best backtest results (68% WR, 1.59 Sharpe) never deployed to production
- **Evidence:** Forward test database is EMPTY; no linkage to live pick generation
- **Proposed fix:** Wire genome output into Alpha Engine scanner pipeline

---

## Proven Strategies (Forward-Tested with Real Data)

### Tier 1 — 4-AI Consensus Validated
| Strategy | FWD Trades | FWD WR | PF | Asset Lock |
|----------|-----------|--------|-----|------------|
| `crypto_rsi_whaleconfirmed_v1` | 106 | 67.9% | 2.1+ | — |
| `funding_momentum` | 329 | 53.8% | — | — (+2168% PnL) |
| `crypto_keltner_compression_expansion` | 96 | 72.9% | — | **BTC ONLY** |
| `crypto_vwap_deviation_reversion_vol` | 58 | 62.1% | — | **BTC ONLY** |
| `crypto_kalman_trend_residual_reversion` | 90 | 55.6% | — | — |

### Tier 2 — Gold Standard (50+ trades, PF > 1.5)
| Strategy | FWD Trades | FWD WR | PF | Asset Lock |
|----------|-----------|--------|-----|------------|
| `multi_period_rsi_confluence` | 76/50 | 60.5%/64% | 2.54/3.27 | **ETH+XRP** |
| `drawdown_recovery_rsi` | 52 | 61.5% | 1.69 | ETH+BTC |
| `crypto_soc_orderflow_absorption` | 58 | 60.3% | 1.82 | **BTC ONLY** |
| `extreme_fear` | 4 | 100%* | — | BTC (*small sample) |

### DNA Evolution Winners (Backtest Only — NOT forward-tested)
| Combo | WR | Sharpe | Trades | Status |
|-------|-----|--------|--------|--------|
| Fear-Greed Contrarian | 75% | 2.06 | 203 | Needs forward test |
| Triple Mean Reversion | 72% | 1.87 | 156 | Needs forward test |
| Connors-Keltner Fusion | 68% | 1.53 | 124 | Needs forward test |
| Volume-Bollinger Squeeze | 64% | 1.31 | 98 | Needs forward test |

---

## Firewall Architecture

### Stage 1 — Hard Pass/Fail
```
1. BLOCKED_PATTERNS: ['revival_mutated', 'rapid_fire', 'ml_crypto_predictor']
2. BLOCKED_SYSTEMS: {'ml_bg_system_f'} (PF 0.95, 56 trades)
3. KELTNER_BLOCK: All non-BTC Keltner variants + bollinger_keltner_squeeze
4. SYMBOL_LOCK: Substring match — reject if strategy matches lock but wrong asset
5. KILL_CRITERIA: WR < 45% OR PF < 1.0 after 20+ trades → auto-block
6. MIN_QUALITY: sys_closed >= 5, sys_wr >= 45%
7. MIN_RR: >= 1.2
8. REGIME_FILTER: Block breakout in CHOPPY/BEARISH markets
```

### Stage 2 — Kelly-Enhanced Scoring (v2 with Statistical & Volatility Multipliers)
```python
raw_score = (
    max(0, expectancy) * 3.0 +     # expectancy is king
    kelly_score * 50 +               # kelly edge (half-kelly, capped 8%)
    rr_score * 15 +                  # R:R (capped at 5x)
    agree_score * 25 +               # consensus (agreement is strongest alpha)
    fresh_score * 8 +                # freshness (decay over 48h)
    confidence * 5                   # signal confidence
) * (uncertainty_adj * proven_bonus * pf_bonus * conflict_mult
     * tier_mult * super_bonus
     * stat_bonus          # NEW: z-score statistical significance (0.6x to 1.5x)
     * vol_score_mult      # NEW: volatility regime penalty (0.5x EXTREME to 1.1x LOW)
     * live_ready_bonus)   # NEW: 1.3x for going-live qualified strategies
```

**New v2 Multipliers (Giga Potato Integration):**
- `stat_bonus`: z-score ≥ 1.96 (95% confidence) → 1.5x; z-score ≥ 1.28 (90%) → 1.25x; 20+ trades without significance → 0.6x PENALTY
- `vol_score_mult`: EXTREME vol → 0.5x; HIGH → 0.8x; NORMAL → 1.0x; LOW → 1.1x
- `live_ready_bonus`: Strategies meeting going-live criteria (30+ trades, WR>52%, statistically significant) → 1.3x

---

## Statistical Risk Management Engine (NEW — Giga Potato v1)

Deployed in `portfolio_manager.py` as of Mar 11, 2026. Six interconnected components:

### 1. Volatility Metrics (`compute_volatility_metrics`)
Per-symbol, per-cycle computation of:
- **ATR(14):** Average True Range in price units and as % of price
- **Daily Std Dev:** Standard deviation of daily returns (%)
- **Z-Score:** How many std devs today's move is from mean
- **Vol Regime:** LOW (<2%), NORMAL (2-5%), HIGH (5-8%), EXTREME (>8%)
- **Median ATR %:** Baseline for vol-adjustment scaling

### 2. Statistical Quality Gate (`strategy_z_score_test`)
Hypothesis test: "Is this strategy's WR significantly better than random (50%)?"
- Uses one-tailed z-test of proportions
- Returns z-stat, approximate p-value, significance flag
- **Going-live threshold:** z > 1.28 (90% confidence), WR > 52%, 30+ trades
- Strategies with 20+ trades that FAIL the z-test get a 0.6x scoring penalty (likely noise)

### 3. Volatility-Adjusted Position Sizing (`volatility_adjusted_size`)
Replaces fixed % sizing with Kelly + ATR scaling:
```
f_kelly = WR - (1-WR) / (avg_win/avg_loss)
size = (capital * f_half_kelly * vol_adj * base_risk * regime_cap) / risk_distance
```
- **Half-Kelly:** Conservative (50% of full Kelly fraction)
- **Vol adjustment:** `median_atr / current_atr` — shrinks in high vol, grows in low vol
- **Regime caps:** EXTREME → 30% of normal size, HIGH → 60%, NORMAL → 100%, LOW → 120%
- **Hard caps:** Min $10, max 12% of capital per position

### 4. ATR-Based Trailing Stops (`enhanced_trailing_stop`)
Replaces fixed 5% activation / 50% trail with dynamic levels:
- **Activation:** After +1x ATR profit (volatility-aware, not fixed %)
- **Trail distance:** 1.5x ATR (institutional standard)
- **Dual trail:** Uses tighter of ATR trail vs 50%-of-peak trail
- **One-way ratchet:** Stop only tightens, never widens
- **Short protection:** Same logic in reverse

### 5. Portfolio Risk Budget (`portfolio_risk_budget`)
VaR-lite check before each new position:
- **Max portfolio risk:** 15% of equity at risk simultaneously
- **Direction cap:** Max 60% exposure in one direction (LONG or SHORT)
- **Per-position risk:** Computed from entry-to-SL distance × size
- Rejects positions that would breach the budget

### 6. Going-Live Constants
```python
GOING_LIVE_MIN_TRADES = 30       # Need 30+ forward trades
GOING_LIVE_MIN_WR = 52           # Must beat random after costs
GOING_LIVE_MIN_PF = 1.15         # Must be profitable after costs
GOING_LIVE_MAX_DAILY_RISK = 3.0  # Max 3% daily loss before halt
GOING_LIVE_Z_THRESHOLD = 1.28    # 90% confidence the edge is real
```

---

## Risk Management Parameters (Updated)

| Parameter | Old Value | New Value | Method |
|-----------|-----------|-----------|--------|
| Position size | Fixed 10-20% | **Kelly + ATR scaled** (0.5-12%) | `volatility_adjusted_size()` |
| Trailing stop activation | Fixed +5% | **+1x ATR** (dynamic per asset) | `enhanced_trailing_stop()` |
| Trail distance | 50% of peak | **1.5x ATR** (or 50% of peak, whichever is tighter) | ATR-based |
| Max portfolio risk | Implicit | **15% of equity** at risk at any time | `portfolio_risk_budget()` |
| Max directional exposure | 50% LONG / 40% SHORT | **60% max** either direction | Risk budget check |
| Strategy quality gate | WR ≥ 45%, 5+ trades | **z-score significant, WR ≥ 52%, 30+ trades** (going-live) | `strategy_z_score_test()` |
| Max positions | 4-10 per portfolio | Unchanged | Per portfolio config |
| Max per strategy family | 2 | Unchanged | Concentration limit |
| Stale loss exit | 7 days | Unchanged | Cut losers |
| Max hold time | 14 days | Unchanged | Prevent capital lock-up |
| Round-trip cost (crypto) | 0.40% | Unchanged | 0.15% commission + 0.05% slippage |

---

## 10 Priority Actions (Giga Potato Roadmap — Compressed for Going-Live)

### DONE (Implemented Mar 11, 2026)

| # | Change | Expected Impact | Status |
|---|--------|----------------|--------|
| 1 | **Statistical quality gate** (z-score test for strategy WR significance) | Kill noise strategies | DEPLOYED |
| 2 | **Volatility-adjusted sizing** (Kelly + ATR scaling) | +12% PF, reduce DD | DEPLOYED |
| 3 | **ATR-based trailing stops** (dynamic 1.5x ATR trail) | +8% expectancy | DEPLOYED |
| 4 | **Portfolio risk budget** (15% VaR-lite cap) | Prevent blowup | DEPLOYED |
| 5 | **Volatility regime scoring** (penalize EXTREME vol picks) | Avoid whipsaws | DEPLOYED |
| 6 | **Going-live readiness flag** (1.3x bonus for qualified strategies) | Prioritize quality | DEPLOYED |

### DONE (Implemented Mar 11, 2026 — Round 2)

| # | Change | Expected Impact | Status |
|---|--------|----------------|--------|
| 7 | **Restart KIMI system** — fixed .db blocking git push in deploy workflow | Recover system diversity | DEPLOYED |
| 8 | **Wire genome DNA evolution** — 3 engines (GENESIS/LEGION/ATLAS) into aggregator | 102 new picks in consensus | DEPLOYED |
| 9 | **Confidence calibration** — WR-anchored, 95% cap, uncertainty discount | Honest signals | DEPLOYED |
| 10 | **Per-system leaderboard** — dashboard shows W/L, WR%, PnL per system | Transparency for audit | DEPLOYED |
| 11 | **System architecture docs** — full AI-audit reference for cross-aggregation | Auditability | DEPLOYED |

### STILL NEEDED (Next 1-3 Days)

| # | Change | Expected Impact | Priority |
|---|--------|----------------|----------|
| 12 | **Demote weak consensus systems** (kimi 40%, battleground 38%, crypto_ml_edge 36%) | +15-20% consensus WR | CRITICAL |
| 13 | **Integrate scalping strategies** — wire KIMI scalping bundle + baby scalpers into live scanner | Backup system for swing failures | HIGH |
| 14 | **Full regime filter** (ADX<20 → mean-reversion only) | +10% WR | HIGH |
| 15 | **Database consolidation** (35 SQLite → unified store) | Traceability | MEDIUM |

**Target outcome:** WR ~55-60%, PF ~1.3+, Expectancy > +1.0% per trade

---

## Cross-Aggregation Consensus — Deep Findings (Mar 11)

> **Dashboard:** https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/cross_aggregation/
> **Architecture docs:** [`cross_aggregation/SYSTEM_ARCHITECTURE.md`](../cross_aggregation/SYSTEM_ARCHITECTURE.md)

### Per-System Performance in Consensus Picks

| System | W | L | WR | Cum PnL | Status | Action |
|--------|---|---|-----|---------|--------|--------|
| predictions | 5 | 0 | **100%** | +25.0% | Strong | Keep |
| breakout_b | 3 | 0 | **100%** | +15.0% | Strong | Keep |
| rl_agent_ppo | 1 | 0 | 100% | +5.0% | Strong (low n) | Keep, need more data |
| alpha_engine | 1 | 0 | 100% | +5.0% | Strong (low n) | Keep, need more data |
| ml_crypto_pred | 6 | 2 | **75%** | +24.7% | Strong | Keep — best overall |
| coinglass_strategies | 6 | 7 | 46% | +13.3% | Neutral | Monitor |
| kimi | 8 | 12 | **40%** | +3.6% | REVIEW | Dragging consensus down |
| battleground | 5 | 8 | **38%** | -0.5% | REVIEW | Dragging consensus down |
| crypto_ml_edge | 4 | 7 | **36%** | +3.3% | REVIEW | Consider demotion |
| mercury2 | 0 | 1 | 0% | -1.3% | REVIEW | Already nearly demoted |

**Key insight:** kimi (40% WR), battleground (38% WR), and crypto_ml_edge (36% WR) are ACTIVELY HURTING consensus quality. When these systems vote, they pull the consensus toward losing trades. If we excluded them, the remaining systems would have ~70%+ WR in consensus. This is the single highest-impact change available.

### Confidence Calibration Fix (Mar 11)

**Problem:** Everything showed 99% confidence — meaningless.
- Old: `raw_conf (80%) + playbook (+5%) + consensus (+8%) = 99% always`
- **New:** `0.6 × raw_conf + 0.4 × actual_system_WR + scaled_consensus_boost`, capped at 95%
- Unknown WR systems get 30% uncertainty discount
- Example: ml_crypto_pred (75% WR, 0.80 raw) → **84%** confidence (was 99%)

### SUPER Tier (≥3 systems + ≥60% cross-pair alignment)
- Historical: 4W/0L = 100% WR (extremely small sample, NOT statistically significant)
- Now dynamically computed from closed trades instead of hardcoded
- Dashboard shows per-system leaderboard with color-coded W/L stats

### Genome DNA Integration (Mar 11)

3 new voting sources wired into aggregator:
- **GENESIS** (genetic_programmer.py): 50 evolved formula strategies
- **LEGION** (ensemble_evolver.py): 25 coevolved voting teams
- **ATLAS** (mape_evolver.py): 27 MAP-Elites quality-diversity strategies

Each counts as 1 independent vote. Normalization layer converts genome-specific fields (tp_pct/sl_pct → absolute prices).

---

## Scalping Strategy Module (NEW — Backup Systems)

The system currently runs swing/position trades (4h-14d hold). We need SHORT-TIMEFRAME backup systems for:
1. Quick capital recovery when swing positions are underwater
2. Market conditions where swing trades fail (choppy, no trend)
3. Funding rate exploitation on perpetuals (8h cycle)

### Existing Scalping Code (Already in Codebase, Not Yet Integrated)

| Strategy | File | TF | Method | Status |
|----------|------|----|--------|--------|
| VWAP Deviation Scalp | `KIMI_RISEOFTHECLAW/scalping_strategies.py` | 5m | VWAP z-score < -1.0 reversion | Ready |
| EMA Ribbon Scalp | `KIMI_RISEOFTHECLAW/scalping_strategies.py` | 1m/5m | EMA 9/21 cross + volume | Ready |
| BB Squeeze Breakout | `KIMI_RISEOFTHECLAW/scalping_strategies.py` | 5m | TTM squeeze + Keltner break | Ready |
| Funding Rate Reversal | `KIMI_RISEOFTHECLAW/scalping_strategies.py` | 8h | Extreme funding → counter-trade | Ready |
| RSI Divergence Scalp | `KIMI_RISEOFTHECLAW/scalping_strategies.py` | 5m | RSI div + confirmation candle | Ready |
| VWAP Reversion | `baby_strategies/prop_scalper_vwap_reversion.py` | 15m | Z-score mean reversion | Ready |
| BB Squeeze | `baby_strategies/prop_scalper_bb_squeeze.py` | 15m | John Carter TTM method | Ready |
| Order Flow Wick | `baby_strategies/prop_scalper_orderflow.py` | 15m | Wick imbalance + CLV | Ready |
| RSI Divergence | `baby_strategies/rsi_div_scalper.py` | 15m | RSI div with ATR stops | Ready |
| ROC Quick Scalp | `baby_strategies/price_roc_quick_scalp_strategy.py` | 15m | Rate of change, 3-bar hold | Ready |
| Momentum Scalp | `momentum_scalping.py` | 1m/5m | EMA cross + RSI slope | Ready |

### 7 Scalping Strategies for Live Deployment

#### 1. VWAP Bounce Scalp (Highest conviction for current market)
- **Entry:** VWAP z-score < -1.0 (oversold below VWAP) + RSI(14) < 30 + volume > 1.5x avg
- **Exit:** TP at VWAP (0.3-0.8%), SL at 0.4 ATR below entry
- **Expected WR:** 55-65% | **Best in:** Ranging markets (ADX < 25)
- **At 20x leverage:** Risk 0.5% account per trade, SL ~0.4% = 8% account risk

#### 2. Funding Rate Scalp (Structural edge — exploit perp market mechanics)
- **Entry:** Funding rate < -0.03%/8h (shorts overleveraged) + OI declining → LONG 30-60min before settlement
- **Exit:** TP 0.5-1.0%, SL 0.5% below entry, time stop 2h after settlement
- **Expected WR:** 55-65% | **Best in:** Extreme funding divergence
- **At 20x leverage:** Risk 1% account per trade (higher conviction structural setup)

#### 3. Bollinger Band Squeeze Scalp (Volatility expansion capture)
- **Entry:** BB width < threshold for 4+ bars (squeeze) + breakout above upper BB + RSI > 50 + volume spike
- **Exit:** TP 1.5x BB width, SL at BB midline
- **Expected WR:** 48-55% with 1.5:1 R:R | **Best in:** After consolidation periods
- **At 20x leverage:** Risk 0.5% account per trade

#### 4. EMA 9/21 Cross Scalp (Trend-following scalp)
- **Entry:** EMA(9) crosses EMA(21) + EMA(21) > EMA(50) trend filter + volume > 1.5x + RSI 40-70
- **Exit:** TP 0.3-0.5%, SL below EMA(21) or 0.2%, trail to breakeven at +0.15%
- **Expected WR:** 50-58% | **Best in:** Trending (ADX > 25)
- **WARNING:** If market is bearish (all longs losing), only take SELL crosses

#### 5. Liquidation Cascade Fade (Counter-trend after exhaustion)
- **Entry:** Volume > 3x avg + long wick/hammer after cascade + wait for confirmation close
- **Exit:** TP 50% retracement of cascade (0.5-1%), SL beyond cascade extreme
- **Expected WR:** 55-62% | **Best in:** High OI, high leverage environments
- **At 20x leverage:** Risk 0.5% account (high risk, wide SL potential)

#### 6. RSI Divergence Scalp (Mean reversion confirmation)
- **Entry:** Price lower low + RSI higher low (bullish div) over 10 bars + RSI < 42 + green confirm candle
- **Exit:** TP 0.7 ATR, SL 0.3% below swing low, time stop 10 bars
- **Expected WR:** 50-60% | **Best in:** Pullbacks in uptrend or corrective wave end
- **At 20x leverage:** Risk 0.75% account per trade

#### 7. Order Flow Imbalance Scalp (Microstructure edge)
- **Entry:** CLV > 0.7 (buying pressure) or < 0.3 (selling) + volume > 2x avg + wick rejection > 2x body
- **Exit:** TP 0.3-0.5%, SL 0.2-0.3%, time stop 5 bars on 5m
- **Expected WR:** 52-58% | **Best in:** High-volume US/EU overlap sessions
- **At 20x leverage:** Risk 1% account per trade

### Risk Rules for 20x Leverage Scalping

```
MAX_RISK_PER_SCALP = 0.5-1.0%     # of total account
MAX_CONCURRENT_SCALPS = 2-3        # correlated crypto = amplified risk
MAX_DAILY_LOSS = 3%                # hard stop, walk away for 24h
DRAWDOWN_HALVING = 10%             # halve position size after 10% DD
LEVERAGE_CAP = 20x                 # reduce to 10x until confirmed regime change
```

| SL Distance | Account Risk at 20x | Max Position Size (1% risk) |
|-------------|---------------------|----------------------------|
| 0.15% | 3.0% | 33% of account |
| 0.25% | 5.0% | 20% of account |
| 0.50% | 10.0% | 10% of account |
| 1.00% | 20.0% | 5% of account |

### Integration Priority
1. **KIMI scalping bundle** — most production-ready, 5 strategies with Binance API
2. **Baby strategy scalpers** — correct signal format, need 5m data feed
3. **Funding Rate** — highest structural edge in bearish regime
4. **Momentum Scalping** — full EMA cross system already built for 1m

---

## Research Questions for IDE Agents

These are open questions where we need deeper analysis or external insight. Any IDE agent picking up this blueprint should consider investigating:

### Strategy Selection & Filtering
1. **Which of our 100+ strategies actually have statistically significant edge?** Run proper hypothesis testing (t-test or bootstrap) on each strategy's closed trades. Many "60% WR" strategies may have p-value > 0.1 with only 20 trades. What's the minimum trade count per strategy before we trust the WR number?

2. **Is the Battleground system's 64.1% WR sustainable, or is it curve-fit to recent BTC bull conditions?** The Battleground is our only real winner — but is it robust across regimes (bear, chop, crash)? What happens to its WR during F&G < 20 or BTC drawdowns > 15%?

3. **Why do DNA evolution backtests (68% WR, 1.59 Sharpe) never survive forward testing?** The genome system produces impressive backtest numbers but has ZERO forward trades. Is this overfitting? Lookahead bias? Or just a deployment gap?

### Market Regime & Timing
4. **What is the optimal regime detection method for our portfolio?** We use ADX + F&G + EMA, but are there better regime classifiers? Should we use Hidden Markov Models, or is simple ADX threshold sufficient? How much WR improvement does regime filtering actually provide in crypto specifically?

5. **Should we stop trading entirely in certain market conditions?** Rather than filtering strategies per-regime, would a binary "risk-on / risk-off" switch (e.g., go 100% cash when F&G < 15 AND ADX < 20) outperform continuous trading?

6. **Is there a time-of-day or day-of-week effect we're ignoring?** Our strategies run 24/7 on 30-min cycles. Are we losing money during specific sessions (Asian, European) where liquidity/patterns differ?

### Position Sizing & Risk
7. **Is our 0.40% round-trip cost estimate accurate?** We assume 0.15% commission + 0.05% slippage per side on IBKR crypto. In practice, are we experiencing worse fills? Should we be using limit orders instead of market orders, and how would that change signal freshness requirements?

8. **Why is our avg loss (19.85%) larger than our avg win (17.73%)?** Is this a TP/SL asymmetry problem (TP too tight, SL too wide)? Or are we holding losers too long? What's the optimal TP:SL ratio for crypto mean-reversion vs trend-following?

9. **Would a simple equal-weight portfolio of ONLY Tier 1 strategies beat our complex 22-portfolio system?** All the portfolio diversification, scoring, and routing may be adding complexity without adding returns. Test: what if we just ran the 5 Tier 1 strategies with equal allocation?

### System Health & Integration
10. **Why did KIMI die on March 1 and can we prevent it?** The scanner stopped executing — was it a GitHub Actions failure, a code error, or an API rate limit? What monitoring/alerting should we add to detect system death within hours, not days?

11. **Should we consolidate our 35 SQLite databases?** Is the fragmentation actually causing data quality issues (duplicate IDs, orphaned records), or is it just messy but functional? What's the cost/benefit of a migration to unified MySQL?

12. **Is the cross-aggregator consensus (51.9% WR, +30.32% PnL) our best path forward?** The consensus tracker on 46 picks shows marginal edge. Should we double down on consensus-only trading (requiring 3+ system agreement) and abandon single-system picks entirely?

### Deeper Research Needed
13. **Correlation analysis across our portfolios:** How correlated are the 22 portfolios' returns? If they're all 90%+ correlated (because they draw from the same signal pool), the "diversification" is illusory. What's the actual effective number of independent bets?

14. **Survivorship bias in our strategy stats:** When we kill a strategy (WR < 45% after 20 trades), do we remove its historical losses from our aggregate stats? If so, our reported numbers are biased upward.

15. **Is 14-day max hold optimal for crypto?** Some of our best setups (deep-value, weekly momentum) need 30+ days. Are we cutting winners short with a 14-day limit? What's the PnL distribution by hold duration?

16. **Walk-forward optimization:** Are any of our strategies re-optimized periodically, or are we using static parameters from initial backtest? Crypto market structure changes fast — a strategy that worked in Q4 2025 may be dead by Q1 2026.

17. **What would a Monte Carlo simulation of our portfolio system show?** Given our actual trade distribution (wins, losses, sizes), what are the 95th percentile drawdown scenarios? Are we sized appropriately for the tail risks?

---

## Key Files Reference

| File | Purpose |
|------|---------|
| `audit_dashboard/portfolio_manager.py` | Main 22-portfolio manager (~2500 lines) |
| `audit_dashboard/data/claudes_test_state.json` | Portfolio state (positions, equity, history) |
| `audit_dashboard/data/claudes_test_dashboard.json` | Dashboard data (generated each cycle) |
| `audit_dashboard/claudes_test.html` | Live dashboard |
| `audit_dashboard/BLUEPRINT.md` | This file |
| `audit_dashboard/LEARNINGS.md` | Mistakes and lessons learned |
| `alpha_engine/scanner.py` | Alpha Engine main scanner (100 strategies) |
| `alpha_engine/config.py` | Alpha Engine configuration |
| `alpha_engine/crypto_strategies.py` | 73 crypto strategy implementations |
| `alpha_engine/forex_strategies.py` | 11 forex strategies |
| `alpha_engine/equity_strategies.py` | 14 equity strategies |
| `alpha_engine/portfolio_survival_improvements.md` | 5 changes to flip expectancy |
| `alpha_engine/data/active_picks.json` | Current open trades |
| `alpha_engine/data/closed_picks.json` | Historical trade results |
| `alpha_engine/data/strategy_performance.json` | Per-strategy stats |
| `KIMI_RISEOFTHECLAW/live_scanner.py` | KIMI scanner v11.2 (DEAD) |
| `KIMI_RISEOFTHECLAW/data/kimi_trading.db` | KIMI picks database |
| `cross_aggregation/aggregator.py` | Cross-system pick aggregator |
| `cross_aggregation/consensus_outcome_tracker.py` | Consensus TP/SL validator |
| `cross_aggregation/regime_router.py` | Market regime filter |
| `cross_aggregation/pick_classifier.py` | ELITE/PROVEN/EXPERIMENTAL routing |
| `cross_aggregation/super_signal.py` | Super signal (multi-system) engine |
| `cross_aggregation/discord_notify.py` | Discord alert system |
| `cross_aggregation/dna_master_tracker.py` | Elite-tier pick tracker |
| `genome/dna_engine.py` | Genetic algorithm DNA system |
| `genome/evolve_strategies.py` | Strategy evolution runner |
| `genome/quality_engine.py` | 6-dimension quality scoring |
| `audit_trail/data/dashboard_payload.json` | Battleground system data source |

---

## Trust Level Assessment (Updated Mar 11 with Risk Engine)

| Metric | Before Risk Engine | After Risk Engine (Expected) | Target for Live | Gap |
|--------|-------------------|------------------------------|----------------|-----|
| Position sizing | Fixed 10-20% | Kelly + ATR scaled (0.5-12%) | Dynamic | CLOSED |
| Trailing stops | Fixed 5% trigger | ATR-based 1.5x dynamic | Dynamic | CLOSED |
| Quality gate | WR≥45%, 5 trades | z-score significant, 30+ trades | Statistical | CLOSED |
| Portfolio risk cap | None | 15% VaR-lite | Bounded | CLOSED |
| Win rate (Battleground) | 64.1% | 64.1%+ (better exits) | > 55% sustained | OK |
| Win rate (Alpha Engine) | 35.9% | ~50%+ (noise filtered, vol-adjusted) | > 50% | Monitoring |
| Profit factor (Alpha) | 0.71 | ~1.2+ (smaller losers via ATR trail) | > 1.3 | Improving |
| Expectancy per trade | -3.24% | ~+0.5-1.5% (statistical filtering) | > +1.0% | Improving |
| Max drawdown risk | Unbounded | 15% portfolio cap | < 10% | BOUNDED |
| Consensus tracker | 51.9% WR, +30.32% | Focus on 3+ system picks | > 55% | Close |
| KIMI system | DEAD (10+ days) | Needs restart | Operational | CRITICAL |
| Genome integration | 0 forward trades | Needs deployment | Producing picks | HIGH |
| Database integrity | 35 fragmented DBs | Unified store | Major cleanup needed |
| Strategy count deployed | 100+ | 5-10 proven only | Reduce noise |

**Assessment (Mar 11 update):** The statistical risk management engine is now deployed. Position sizing, trailing stops, and quality gates are all volatility-aware and statistically grounded. The system will now:
- **Shrink positions** in high-volatility environments (EXTREME vol → 30% normal size)
- **Penalize noise strategies** that can't pass z-score significance tests (0.6x scoring penalty)
- **Reward proven winners** with live-ready flags (1.3x scoring bonus + Kelly-optimal sizing)
- **Cap portfolio risk** at 15% of equity at any time (prevents blowup scenarios)
- **Trail dynamically** using ATR instead of fixed percentages (adapts to each asset's volatility)

**Remaining blockers for going live:**
1. ~~KIMI system restart~~ DONE — workflow fixed, data refreshed
2. ~~Genome DNA integration~~ DONE — 3 engines wired into aggregator
3. ~~Confidence calibration~~ DONE — WR-anchored, no more fake 99%
4. 48-72h observation of new risk engine in simulation (validate the math works in practice)
5. Demote weak consensus systems (kimi/battleground/crypto_ml_edge dragging WR down)
6. Deploy scalping strategies as backup systems for quick capital recovery
7. Human review of first 50 trades under new system before committing additional capital

**Estimated time to real-money deployment:** 1-3 days — major blockers cleared, need observation period.

**LIVE TRADE WARNING (Mar 11):** User has 6 live positions on BTCC at 20x leverage, all LONG, most losing (LINK -9.59%, BTC -5.42%). This is EXACTLY the scenario our risk engine is designed to prevent:
- 100% directional exposure (all LONG) — our system caps at 60%
- No stop losses set — our system would enforce ATR-based trailing stops
- 20x fixed leverage — our system would use Kelly-sized positions (typically 3-8% of capital)
- All correlated crypto — our system caps at 3 high-beta-crypto longs

---

## Giga Potato Feedback Integration Log

| Feedback Item | Action Taken | Implementation |
|---------------|-------------|----------------|
| Negative expectancy across portfolios | Deployed statistical quality gates + noise penalty | `strategy_z_score_test()` in firewall |
| Signal noise (100+ strategies) | z-score filter: 20+ trades without significance → 0.6x penalty | `score_pick()` stat_bonus |
| Asymmetric losses (avg loss > avg win) | ATR-based trailing stops: lock gains dynamically | `enhanced_trailing_stop()` |
| No volatility awareness | Full vol engine: ATR, std dev, z-score, vol regime per symbol | `compute_volatility_metrics()` |
| Fixed position sizing | Kelly + ATR-scaled sizing with regime caps | `volatility_adjusted_size()` |
| No portfolio risk cap | 15% VaR-lite budget, 60% directional cap | `portfolio_risk_budget()` |
| Restart KIMI | **FIXED** — .db files were blocking git push in workflow | `deploy-riseoftheclaw.yml` patched |
| Genome DNA integration | **DONE** — 3 engines (GENESIS/LEGION/ATLAS) wired as voting sources | `aggregator.py` DATA_SOURCES + normalizer |
| Confidence inflation (99% on everything) | **FIXED** — WR-anchored calculation, 95% cap | `aggregator.py` confidence logic rewrite |
| Per-system accountability | **DONE** — leaderboard in dashboard with W/L per system | `index.html` + consensus_outcomes.json |
| Walk-forward optimization | Added to research questions | Future work |
| Binary risk-on/off switch | Partially addressed by vol regime caps | EXTREME vol → 0.3x size |
| Scalping backup systems | 11 existing strategies identified, 7 documented for deployment | Blueprint updated, needs integration |
