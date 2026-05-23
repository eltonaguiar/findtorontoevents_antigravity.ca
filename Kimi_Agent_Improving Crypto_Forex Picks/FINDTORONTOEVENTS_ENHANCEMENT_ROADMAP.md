# FINDTORONTOEVENTS.CA/AUDIT - ENHANCEMENT ROADMAP
## Based on Complete System Analysis (March 26, 2026)

---

## EXECUTIVE SUMMARY

After reviewing 20+ system files, TODOs, logs, and performance reports, I've identified **7 critical enhancement areas** that will transform findtorontoevents.ca/audit from a 46% WR system to a 58-62%+ hedge-fund-grade platform across all asset classes.

### Current Performance Snapshot
| Asset Class | Current WR | Target WR | Gap |
|-------------|-----------|-----------|-----|
| Crypto | 44.6% | 60%+ | -15.4pp |
| Forex | 35.7% | 50%+ | -14.3pp |
| Equity | 4.6% | 45%+ | -40.4pp |
| Commodity | 14.3% | 40%+ | -25.7pp |
| **Overall** | **46.0%** | **58-62%** | **-12-16pp** |

---

## PART 1: CRITICAL FIXES (Immediate - 24-48 Hours)

### 1.1 Fix Win Rate Calculation Inconsistency (CRITICAL)

**Problem:** The dashboard uses **4 different WR formulas** depending on which component renders it:
- `template.html`: `wins(pnl>0) / (wins+losses)` - Zero-PnL EXCLUDED
- `portfolio_manager.py`: `net_pnl>0 ? win++ : loss++` - Zero-PnL counts as LOSS
- Smart Picks tab: `pnl > 0` - Zero-PnL counts as LOSS
- Strategy Leaderboard: `wins / all_trades` - Includes OPEN trades in denominator

**Impact:** Same strategy shows 42% to 58% WR depending on where you look. This destroys credibility.

**Fix:**
```python
# Standardized WR Formula (apply EVERYWHERE)
def calculate_win_rate(wins, losses, flat=0):
    total_resolved = wins + losses + flat
    if total_resolved == 0:
        return 0.0
    # Flat trades count in denominator but not numerator
    return wins / total_resolved

# For display: show wins/losses/flat separately
# "WR: 52% (47W/38L/5F)" - transparent and consistent
```

**Files to modify:**
- `audit_trail/dashboard_generator.py` (lines 1450-1520)
- `alpha_engine/portfolio_manager.py` (lines 380-420)
- `templates/template.html` (lines 890-950)
- `alpha_engine/strategy_leaderboard.py` (lines 55-90)

---

### 1.2 Fix MySQL ENUM - FUTURES & ETF Data Being Lost (CRITICAL)

**Problem:** `at_raw_picks.asset_class` ENUM is missing `'FUTURES'` and `'ETF'` values:
```sql
ENUM('CRYPTO','FOREX','EQUITY','PENNY_STOCK','MEMECOIN','SPORTS','UNKNOWN')
```

When `derive_asset_class()` returns `'FUTURES'` or `'ETF'`, MySQL strict mode fails silently. All ETF picks (SPY, QQQ, GLD, TLT) and futures picks (ES=F, NQ=F) are lost or stored as `UNKNOWN`.

**Fix:**
```sql
-- Run this migration immediately
ALTER TABLE at_raw_picks 
MODIFY COLUMN asset_class ENUM(
    'CRYPTO','FOREX','EQUITY','PENNY_STOCK','MEMECOIN','SPORTS',
    'FUTURES','ETF','BOND','COMMODITY','INDEX','UNKNOWN'
) NOT NULL DEFAULT 'UNKNOWN';
```

**Migration file:** `audit_trail/migration_add_futures_etf.sql` (already exists, needs execution)

**Impact:** Recover 50+ lost ETF/futures picks currently invisible to dashboard.

---

### 1.3 Wire Orphaned Data Sources to Dashboard (CRITICAL)

**Problem:** 43 data sources with 713+ picks are NOT wired to `dashboard_generator.py`:

| Orphaned Source | Picks | Status |
|-----------------|-------|--------|
| `copy_trader_intel/` | 135 | REAL picks, 0% WR displayed |
| `prediction_market_agents/` | 15 | PM signals not visible |
| `battleground/luxalgo_closed_picks.json` | 312 | Closed picks invisible |
| `multi_asset/multi_asset_closed.json` | 105 | Closed picks invisible |
| `genome/revival_*` | 284 | Mutation results not tracked |
| `smart_money/active_picks.json` | 37 | Equity picks missing |

**Fix:** Add to `JSON_PICK_SOURCES` in `audit_trail/dashboard_generator.py`:

```python
# Add these tuples (source_name, file_path, weight)
('copy_trader_intel', 'copy_trader_intel/data/active_picks.json', 1.0),
('copy_trader_consensus', 'copy_trader_intel/data/consensus_picks.json', 1.0),
('pm_momentum', 'prediction_market_agents/data/momentum_signals.json', 1.2),
('pm_whale', 'prediction_market_agents/data/whale_signals.json', 1.2),
('pm_kalshi', 'prediction_market_agents/data/kalshi_signals.json', 1.0),
('pm_consensus', 'prediction_market_agents/data/consensus_signals.json', 1.5),
('luxalgo_closed', 'battleground/luxalgo_closed_picks.json', 1.0),
('multi_asset_closed', 'multi_asset/multi_asset_closed.json', 1.0),
('smart_money', 'smart_money/data/active_picks.json', 0.8),
```

**Impact:** Immediate +400-500 visible picks, proper WR calculation for copy traders.

---

### 1.4 Fix TP/SL Outcome Resolution for 1,400+ Picks (CRITICAL)

**Problem:** These systems have closed picks but NO price validation - showing 0% WR:
- `copy_trader_intel`: 49 closed, 0% WR (NO RESOLVER)
- `rapid_fire`: 334 closed, 0% WR (NO RESOLVER)
- `predictions`: 324 closed, 0% WR (NO RESOLVER)
- `quan_engine`: 47 closed, 0% WR (NO RESOLVER)
- `goldmine_stocks`: 14 closed, 0% WR (NO RESOLVER)

**Root Cause:** No workflow compares exit price to stored TP/SL levels.

**Fix:** Create `universal_outcome_resolver.py`:

```python
def resolve_outcomes_for_source(source_json_path):
    picks = load_json(source_json_path)
    for pick in picks:
        if pick['status'] == 'CLOSED' and 'exit_price' in pick:
            entry = pick['entry_price']
            exit_p = pick['exit_price']
            tp = pick.get('take_profit', 0)
            sl = pick.get('stop_loss', 0)
            
            # Determine outcome
            if tp and exit_p >= tp * 0.995:  # Within 0.5% of TP
                pick['outcome'] = 'TP_HIT'
                pick['pnl_pct'] = (exit_p - entry) / entry * 100
            elif sl and exit_p <= sl * 1.005:  # Within 0.5% of SL
                pick['outcome'] = 'SL_HIT'
                pick['pnl_pct'] = (exit_p - entry) / entry * 100
            else:
                pick['outcome'] = 'PRICE_RESOLVED'
                pick['pnl_pct'] = (exit_p - entry) / entry * 100
                
            # Set WON/LOST status
            pick['status'] = 'WON' if pick['pnl_pct'] > 0 else 'LOST'
    
    save_json(source_json_path, picks)
```

**Schedule:** Run every 15 minutes via GitHub Actions workflow.

**Impact:** 1,400+ picks get proper WR, system WR jumps 5-10pp immediately.

---

## PART 2: ASSET CLASS-SPECIFIC ENHANCEMENTS

### 2.1 CRYPTO ENHANCEMENTS (Target: 60%+ WR)

#### A. Deploy QuantumFusion Engine (PROVEN 65-75% WR)

From `quantum_fusion_report.json` - this algorithm achieves:
- **65.8% average WR** across 720 pair/timeframe combinations
- **1.52 Sharpe Ratio**
- **2.05 Profit Factor**
- **-20.3% max drawdown**

**Per-pair performance highlights:**
| Pair | WR | Sharpe |
|------|-----|--------|
| AVAX | 74.8% | 1.81 |
| BNB | 69.8% | 1.92 |
| XRP | 70.3% | 1.51 |
| LINK | 69.0% | 1.97 |
| INJ | 74.4% | 1.54 |

**Implementation:**
- Create `alpha_engine/quantum_fusion_engine.py` (from report)
- Create `alpha_engine/quantum_fusion_features.py` (17 features)
- Create `.github/workflows/quantum-fusion-scan.yml` (every 15 min)

**Expected Impact:** +10-15pp crypto WR, brings overall to 55-60%.

---

#### B. Fix ML Feature Pipeline (62% Features DEAD)

**Problem from TODO2:** "24/32 features dead (75%), health_score=0.25. ML models trading on noise."

**Dead Features (need revival):**
- `rsi_at_entry` - 0% coverage (was 96% blank)
- `volume_ratio` - 0% coverage
- `fear_greed` - 0% coverage
- `risk_reward` - 0% coverage
- `hour_of_day` - 0% coverage
- `btc_24h_change` - 0% coverage

**Fix:** Wire enrichment into `alpha-engine-live.yml` as persistent step.

**Expected Impact:** ML strategies recover from 47% to 85-94% WR.

---

#### C. Implement Regime-Aware TP/SL

**Problem:** Static TP/SL doesn't match market conditions.

**Fix from TODO2:**
- Tighter in CHOP (TP 1.5x, SL 0.8x)
- Wider in TREND (TP 2.5x, SL 1.2x)

**Expected Impact:** +3-5pp WR by matching exits to market conditions.

---

### 2.2 FOREX ENHANCEMENTS (Target: 50%+ WR)

#### A. Calibrate TP/SL to Forex Volatility (FIXED - Validate)

**Problem from TODO1:** "TP targets (0.8-1.7%) unreachable for forex volatility (0.1-0.5%/day)"

**Fix Applied (11 files):**
- TP cap: 0.8% → 0.3% (achievable in 1-2 days)
- SL cap: 0.5-0.6% → 0.2% (1.5:1 R:R)
- Min hold: 5d → 2d

**Validation Needed:** Monitor next 20 forex picks for TP hit rate.

**Expected Impact:** Forex WR from 35.7% → 50%+.

---

#### B. Integrate Top Forex Copy Trader (OlivierDanvel)

**From TODO2:** "OlivierDanvel from Myfxbook — 84% forex allocation, 65% WR, 33 consecutive profitable months"

**Implementation:** Add to `copy_trader_intel/forex_traders.json` with 30% allocation.

**Expected Impact:** +10-15pp forex WR from proven trader.

---

#### C. Add DXY Regime Filter for Forex

**Problem from TODO4:** "elite_scorer penalizes forex as 'micro-cap' (-5 pts) and applies BTC regime"

**Fix:** Exempt forex from BTC regime, use DXY trend instead.

**Expected Impact:** +5pp WR by proper regime alignment.

---

### 2.3 EQUITY ENHANCEMENTS (Target: 45%+ WR)

#### A. Kill yahoo_analyst_consensus (PERMANENTLY_KILLED)

**Problem from TODO1:** "yahoo_analyst_consensus used 12-month analyst targets as swing TP"

**Status:** Already killed in TODO3

**Impact:** Remove 0% WR equity strategy.

---

#### B. Implement Quality Minus Junk (QMJ) for Equities

**From battle_test_results.json:** "Quality Minus Junk (QMJ)" is a survivor (Grade B+, Score 75)

**Implementation:** Long quality (high ROE, growth, safety), short junk.

**Expected Impact:** +15-20pp equity WR (QMJ is proven factor).

---

#### C. Add Sector Rotation Detection

**From GAINER_PATTERN_ANALYSIS.md:** "AI + Privacy sectors pump together most frequently"

**Implementation:** Rotate into top 2 sectors by momentum.

**Expected Impact:** +5pp WR by sector tailwinds.

---

### 2.4 COMMODITY ENHANCEMENTS (Target: 40%+ WR)

#### A. Recalibrate TP/SL for Commodity Volatility

**Problem from TODO1:** "Commodity TP 5-19% on assets that move 1-3%/day"

**Fix:**
- TP cap: 3% max (was 19%)
- SL cap: 1.5% max
- Hold days: 7 max

**Expected Impact:** +10-15pp commodity WR by achievable targets.

---

#### B. Add Gold/Silver Momentum Strategy

**Implementation:** Gold/silver ratio mean reversion.

**Expected Impact:** +5pp WR from precious metals.

---

## PART 3: PREDICTION MARKET INTEGRATION (Target: 65%+ WR)

### 3.1 Fix Polymarket & Kalshi APIs (CRITICAL)

**Problem from TODO5:**
- Polymarket whale tracker: "scraper returns 0 wallets"
- Kalshi: "format mismatch"

**Fix:** Update to new APIs.

**Expected Impact:** +5-10pp WR from prediction market alpha.

---

### 3.2 Create PM-Only High-Conviction Tier

**From TODO5:** "PM High Conviction" tier already added with 🔮 emoji.

**Enhancement:** Boost confidence +0.08 for 2+ source agreement.

**Expected Impact:** +3-5pp WR from properly handled PM signals.

---

## PART 4: SCORING & QUALITY GATES

### 4.1 Restore ml_score Weight (CRITICAL)

**Problem from TODO2:** "ml_score was zeroed (IC=-0.19) but SCORE_VALIDATION proves it's the STRONGEST predictor (+0.337)"

**Fix:** Restore ml_score to 30% weight in elite_scorer.py

**Expected Impact:** +10pp scoring discrimination, +5pp WR.

---

### 4.2 Implement Confidence Band Filter

**From TODO3:** "only 80-90% band has 87.3% WR. Consider hard-gating to this range"

**Implementation:** Block <60% and >95% confidence (overconfidence penalty).

**Expected Impact:** +8-12pp WR by filtering to optimal confidence band.

---

### 4.3 Add R:R >= 1.5 Hard Gate

**From TODO3:** "data shows 1.5+ lifts WR from 39% to 68%"

**Implementation:** Block R:R < 1.0, penalize < 1.5.

**Expected Impact:** +5pp WR by filtering poor risk/reward.

---

## PART 5: RISK MANAGEMENT & PORTFOLIO CONSTRUCTION

### 5.1 Implement FETUSDT Concentration Cap (CRITICAL)

**Problem from TODO3:** "FETUSDT = 153.6% of total PnL, masking -1,582% real performance"

**Fix:** Max 30% single symbol exposure.

**Expected Impact:** Prevent single-symbol blowup risk.

---

### 5.2 Add Portfolio Heat Monitoring

**From TODO4:** "Kill switch triggers every run due to rolling 0/20 WR"

**Fix:** Smarter kill switch - only trigger on REAL SL hit streaks, not stale closes.

**Expected Impact:** Prevent false kill switch triggers.

---

### 5.3 Implement Adaptive Position Sizing (Kelly Criterion)

**From quantum_fusion_report.json:** "Kelly Criterion position sizing with 0.5 fraction"

**Implementation:** Position size = (edge * odds - (1-edge)) / odds * bankroll * 0.5

**Expected Impact:** +2-3pp WR by optimal position sizing.

---

## PART 6: MONITORING & TRANSPARENCY

### 6.1 Add Equity Curve Tracking

**From TODO4:** "Equity curve tracking — Still not implemented"

**Implementation:** Track daily equity, calculate real Sharpe/Sortino/max drawdown.

**Expected Impact:** Enable proper risk-adjusted metrics.

---

### 6.2 Create Real-Time Performance Dashboard

**New Page:** `findtorontoevents.ca/audit/performance.html`

**Features:**
- Live equity curve (15 min updates)
- Win rate by asset class (real-time)
- Strategy leaderboard (by Sharpe)
- Open positions heat map
- Recent trades table
- Alert feed

**Expected Impact:** Transparency, user trust, faster issue detection.

---

### 6.3 Add Slippage/Commission Modeling

**From TODO4:** "At 0.612% avg PnL, 0.1% round-trip friction eats 33% of edge"

**Implementation:** Apply 5 bps slippage + 10 bps commission to all picks.

**Expected Impact:** Realistic PnL expectations.

---

## PART 7: IMPLEMENTATION PRIORITY & TIMELINE

### Week 1: Critical Fixes (Days 1-7)
| Day | Task | Impact |
|-----|------|--------|
| 1 | Fix MySQL ENUM | +50 picks visible |
| 1 | Standardize WR formula | Credibility restore |
| 2-3 | Wire 43 orphaned sources | +400 picks, +5pp WR |
| 3-4 | Universal outcome resolver | +1,400 resolved, +8pp WR |
| 5-7 | Deploy QuantumFusion engine | +10pp crypto WR |

**Week 1 Target:** 46% → 55% WR

---

### Week 2: Asset Class Optimization (Days 8-14)
| Day | Task | Impact |
|-----|------|--------|
| 8-9 | Fix ML feature pipeline | ML strategies recover |
| 10 | Validate forex TP 0.3% | Forex WR 35% → 50% |
| 11-12 | Integrate OlivierDanvel | Forex +10pp |
| 13-14 | Deploy QMJ for equities | Equity WR 4% → 30% |

**Week 2 Target:** 55% → 58% WR

---

### Week 3: Advanced Features (Days 15-21)
| Day | Task | Impact |
|-----|------|--------|
| 15-16 | Fix Polymarket/Kalshi APIs | +3 quality signals/day |
| 17 | Regime-aware TP/SL | +3pp WR |
| 18-19 | Concentration caps | Risk reduction |
| 20-21 | Kelly position sizing | +2pp WR |

**Week 3 Target:** 58% → 60% WR

---

### Week 4: Polish & Monitoring (Days 22-30)
| Day | Task | Impact |
|-----|------|--------|
| 22-24 | Real-time performance dashboard | Transparency |
| 25-26 | Slippage/commission modeling | Realistic PnL |
| 27-28 | Equity curve tracking | Sharpe/Sortino calc |
| 29-30 | Full system audit | Hedge fund readiness |

**Week 4 Target:** 60% → 62% WR

---

## SUCCESS CRITERIA (Hedge Fund Grade)

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| **Overall WR** | 46% | >= 55% | In Progress |
| **Crypto WR** | 44.6% | >= 60% | In Progress |
| **Forex WR** | 35.7% | >= 50% | In Progress |
| **Sharpe Ratio** | ~0.3 | >= 1.0 | Not tracked |
| **Max Drawdown** | Unknown | < 15% | Not tracked |
| **Single Symbol Max** | 153.6% | < 30% | Fix in progress |
| **Walk-Forward Validated** | Partial | 3+ strategies | In progress |
| **Auditable Exits** | 60% | 100% | Resolver deploying |
| **Real-Time Enrichment** | 4% | 90%+ | 40% achieved |
| **Slippage Adjusted** | No | Yes | Not implemented |

---

## CONCLUSION

The findtorontoevents.ca/audit system has **strong foundations** but suffers from:
1. Data pipeline gaps (1,400+ picks unresolved)
2. Inconsistent metrics (4 WR formulas)
3. Missing asset-class optimization
4. No real risk management (concentration, drawdown)

By implementing this roadmap in 30 days, the system will achieve:
- **58-62% overall WR** (from 46%)
- **Hedge-fund-grade risk management**
- **Full transparency and auditability**
- **Multi-asset-class profitability**

**Estimated effort:** 4 weeks, 3-4 developers
**Expected return:** 12-16pp WR improvement = 25-35% more profitable trades
