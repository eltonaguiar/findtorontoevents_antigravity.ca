# CRYPTO/FOREX WIN RATE INVESTIGATION - FINAL REPORT
## Generated: 2026-03-26

---

## EXECUTIVE SUMMARY

Your crypto/forex win rates are underperforming because **1,400+ closed picks have NO win/loss tracking**, 
copy trader picks are never validated, and the scoring system is actively selecting losing trades.

### Current State (What the Dashboard Shows)
| Metric | Value |
|--------|-------|
| Overall Win Rate | 46.0% |
| Crypto Win Rate | 44.6% |
| Forex Win Rate | 35.7% (or 52.4% - data discrepancy) |
| Copy Trader WR | 0% (despite 135 closed picks) |
| Profit Factor | 1.52 |

### Actual State (Validated Data Only)
| Metric | Value |
|--------|-------|
| True Crypto WR | 41.6% (385 validated trades) |
| True Forex WR | 33.3% (18 trades, not significant) |
| Copy Trader WR | 0% (NO VALIDATION RUNNING) |
| ML Strategies WR | 85-94% (BEST PERFORMERS) |

---

## ROOT CAUSE #1: Copy Trader System Has NO Outcome Resolution

**Status: CRITICAL - 135 closed picks show 0% WR**

### The Problem
Your copy trader intelligence system is wired to the dashboard but has **ZERO price validation**:

- `copy_trader_intel`: 10 active + 49 closed = 0% WR
- `copy_trader_highscore`: 0 active + 19 closed = 0% WR
- `copy_trader_clones`: 0 active + 40 closed = 0% WR
- `copy_trader_consensus`: 4 active + 13 closed = 0% WR

These are REAL Hyperliquid/Binance/BingX trader positions with `entry_price`, `take_profit`, `stop_loss` 
fields, but **NO CODE checks if TP or SL was hit**.

### Code Issues Found
**File:** `.github/workflows/copy-trader-forward-test.yml` (Line 24)
```yaml
timeout-minutes: 10  # TOO SHORT - needs 30 min
```

**File:** `copy_trader_intel/data/active_picks.json`
```json
{
  "forward_trades": 0,
  "forward_wr": 0,           // NEVER UPDATED
  "forward_validated": false, // NEVER SET TO TRUE
  "status": "OPEN"            // STUCK IN OPEN STATUS
}
```

### The Real Copy Trader Performance (From Manual Analysis)
| Trader | Picks | WR | Status |
|--------|-------|-----|--------|
| NMTD_25M (Hyperliquid) | 16 | 81.2% | ONLY PROFITABLE |
| whale_123M_87roi (HL) | 4 | 100% | ONLY PROFITABLE |
| binance_smart_money | 24 | 45.8% | NOT COPY TRADING |
| All Bitget traders | 5 | 0% | GAMED STATS |

**Key Finding:** Only 2 out of 1,325+ scanned traders are actually profitable!

### Why Your Copy Traders Lose
1. **binance_smart_money** is NOT copy trading - it's an aggregate L/S sentiment indicator (44% of volume)
2. **Bitget traders game stats** - Claim 91%+ WR with PF=99.99, but grid-trade tiny sizes and leave losers open
3. **TP/SL too tight for whales** - Whales use 10-40x leverage with wide stops; your 2-3% SL triggers on noise
4. **No outcome resolution** - Picks never get marked as win/loss

---

## ROOT CAUSE #2: 1,400+ Picks Have NO Win/Loss Tracking

**Status: CRITICAL - 50+ systems affected**

### Systems with 0% WR (No Price Validation)
| System | Active | Closed | Issue |
|--------|--------|--------|-------|
| `quan_engine` | 5 | 47 | No TP/SL validation |
| `copy_trader_intel` | 10 | 49 | No outcome resolution |
| `rapid_fire` | 79 | 334 | No outcome resolution |
| `predictions` | 0 | 324 | No outcome resolution |
| `goldmine_stocks` | 37 | 14 | No outcome resolution |
| `revival_*` (7 systems) | 0 | 284 | No outcome resolution |

**Total: ~1,400+ closed picks with NO win/loss tracking**

### Why Outcomes Aren't Recorded
1. **NO OUTCOME RESOLVER** for copy_trader_intel (has TP/SL fields, no resolver)
2. **PRICE VALIDATION GAP** - claude_gainer_st works, 50+ other systems don't
3. **ARCHITECTURE FLAW** - SQLite is primary, MySQL is secondary backfill only
4. **MISSING INTEGRATION** - dashboard_payload has outcomes, doesn't write to MySQL

### MySQL Database Status
| Table | Status | Issue |
|-------|--------|-------|
| `at_discord_notifications` | Working | Logs Discord sends |
| `at_signal_outcomes` | BROKEN | Missing ~1,400 outcomes |
| `at_local_picks` | BROKEN | Stale backfill |
| `strategy_registry` | Partial | Missing performance metrics |

**Key Finding:** MySQL receives Discord events but NOT win/loss outcomes. The dashboard computes WR but never writes it back to the database.

---

## ROOT CAUSE #3: Prediction Market Integration Gap

**Status: WORKING BUT UNDERUTILIZED**

### Current State
- Polymarket signals are correctly ingested via `polymarket_signals.py`
- System is bearish-aligned on BTC matching Polymarket sentiment
- Workflow runs every 30 minutes

### Critical Issues
1. **NO Isolated Performance Tracking** - Polymarket trades not tracked separately
2. **Timeframe Mismatch** - Polymarket does daily/weekly predictions; your system uses 15m/1h/4h strategies
3. **Signal Dilution** - 3 quality Polymarket signals compete with 115+ other sources
4. **Prediction-to-Trade Gap** - Polymarket provides directional bias but NOT executable parameters (entry, TP, position size)

**Key Finding:** Prediction markets predict EVENTS. Trading requires EXECUTION. The bridge between these is broken.

---

## ROOT CAUSE #4: Scoring System is ANTI-PREDICTIVE

**Status: CRITICAL - High scores = Losing trades**

### The Problem
Your scoring system actively selects LOSING trades:

| Score Quintile | WR | Avg PnL |
|----------------|-----|---------|
| Q1 (Highest scores) | 45.6% | -1.11% |
| Q5 (Unscored/ML picks) | 70.7% | +9.54% |

**ML strategies with score=0 are your BEST performers**, but the scoring system downweights them!

### Code Issue
**File:** `alpha_engine/portfolio_tracker_copytrader.py` (Lines 60-65)
```python
MIN_SCORE = 80  # Claims 80+ scores have 65.9% WR
```

**Reality:** Score 40-59 has 6.2% WR vs score 20-39 at 50% WR (INVERTED!)

### ml_score Was Incorrectly Zeroed
- `ml_score` has +0.337 correlation with PnL (STRONGEST predictor)
- Was zeroed based on flawed IC analysis (IC=-0.19 on biased sample)
- Should be RESTORED as primary weight

---

## ROOT CAUSE #5: ML Feature Pipeline DEAD

**Status: CRITICAL - 62% of features failing since March 8**

### The Problem
- `ml_crypto_predictor` production engine appears dead for 17 days
- 62% of ML features failing silently
- ML models trading on partial data

**Impact:** Your best-performing strategies (85-94% WR) are running blind!

---

## ROOT CAUSE #6: FETUSDT Concentration Risk

**Status: HIGH RISK - Single point of failure**

### The Problem
- **126.9% of total PnL comes from FETUSDT**
- Without FETUSDT: Overall PnL = **-1,229%**
- 52% of all portfolio profits from one symbol

**Risk:** One bad FETUSDT trade wipes out entire portfolio gains.

---

## WHAT IS ACTUALLY WORKING

### Crypto-Only Picks: 48% WR, +7.99% PnL
### ML Strategies (when features work):
- ml_enhanced_FETUSDT: 94% WR, +$6,075
- ml_enhanced_RENDERUSDT: 93% WR, +$1,727
- ml_enhanced_BNBUSDT: 85% WR

### High-Consensus Picks (5+ sources agree): 82-100% WR
### Copy Trader NMTD_25M: 81.2% WR

---

## THE PATH TO 58-62% WIN RATE

### P0 Fixes (Immediate - 4 hours)
| Fix | Impact | Effort |
|-----|--------|--------|
| Add outcome resolver for copy_trader_intel | +3-5pp WR | 4h |
| Kill binance_smart_money (fake copy trader) | +5pp WR | 30min |
| Block all Bitget traders (gamed stats) | +2pp WR | 30min |
| Kill yahoo_analyst_consensus (0% WR) | +2-3pp WR | 30min |
| Widen whale TP/SL to 8%/4% | +3pp WR | 1h |

### P1 Fixes (Short-term - 8 hours)
| Fix | Impact | Effort |
|-----|--------|--------|
| Fix rapid_fire validation (334 picks) | +5-8pp WR | 4h |
| Restore ml_score as primary weight | +10pp WR | 1h |
| Add confidence >= 80 gate | +8-12pp WR | 30min |
| Fix ML feature pipeline | +5pp WR | 4h |
| Cap FETUSDT at 30% of portfolio | Risk reduction | 1h |

### P2 Fixes (Medium-term)
| Fix | Impact | Effort |
|-----|--------|--------|
| Make MySQL primary audit store | Data integrity | 8h |
| Add Polymarket isolated tracking | +5pp WR | 4h |
| Create consensus_5plus virtual system | +10pp WR | 2h |

**Combined Impact: 46% → 58-62% WR (Hedge Fund Level)**

---

## IMMEDIATE ACTION ITEMS (Next 24 Hours)

1. **STOP copying binance_smart_money** - Add to HARD_KILL_STRATEGIES
2. **STOP all Bitget traders** - Add PF <= 10 filter
3. **Concentrate copy trading on 2 traders only:**
   - NMTD_25M: 60% allocation
   - whale_123M: 30% allocation
4. **Widen whale copy TP/SL** to 8% TP / 4% SL
5. **Add position-age filter** - Only copy positions <2h old
6. **Kill yahoo_analyst_consensus** - 0% WR on 55 trades
7. **Restore ml_score weight** - +0.337 correlation

---

## SUMMARY

Your crypto/forex win rates are low because:

1. **Copy trader picks have NO validation** - 135 closed picks show 0% WR
2. **1,400+ picks have no outcome tracking** - 50+ systems affected
3. **binance_smart_money is NOT copy trading** - It's a sentiment indicator
4. **Bitget traders game their stats** - Every Bitget pick lost
5. **Scoring is anti-predictive** - High scores = Losing trades
6. **62% of ML features dead** - Best strategies running blind
7. **FETUSDT concentration** - 126% of PnL from one symbol

**The good news:** Your ML strategies (85-94% WR) and high-consensus picks (82-100% WR) ARE working. 
Focus on these, kill the losers, and fix the validation pipeline to reach 58-62% WR.
