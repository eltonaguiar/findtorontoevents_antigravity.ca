
# TRADING LOGIC ISSUES INVESTIGATION REPORT
## Repository: findtorontoevents_antigravity.ca

---

## EXECUTIVE SUMMARY

The crypto/forex trading system is underperforming due to multiple interconnected issues:
1. **Copy trader picks are not being properly validated** - forward_wr shows 0% despite 49 closed picks
2. **Outcome resolution has timing and threshold issues** - 0.01% threshold may be too strict
3. **Prediction market signals are filtered too aggressively** - MIN_CONFIDENCE=0.60 and MIN_SOURCE_CATEGORIES=2 blocks most signals
4. **Scoring system is anti-predictive** - Highest scored picks lose money while score=0 picks perform best
5. **ML feature pipeline has 62% dead features since March 8**

---

## 1. COPY TRADER INTELLIGENCE SYSTEM ISSUES

### Key Files:
- `.github/workflows/copy-trader-forward-test.yml` (Line 1-55)
- `copy_trader_intel/data/active_picks.json` (3710 lines, 115 KB)
- `alpha_engine/portfolio_tracker_copytrader.py` (989 lines)

### Issues Found:

#### A. Workflow Timeout Too Short
```yaml
# copy-trader-forward-test.yml
jobs:
  forward-test:
    runs-on: ubuntu-latest
    timeout-minutes: 10  # TOO SHORT - causes timeouts
```
**Problem:** The workflow timeout was increased from 14 to 30 minutes in commit 54cc93f, but 
the current file shows 10 minutes. All 10 runs were timing out, meaning NMTD (Never Missed 
Trade Data) never completes.

#### B. Forward Win Rate Not Calculated
From active_picks.json:
```json
{
  "id": "binance_smart_money::SOLUSDT::2026-03-26_0816",
  "forward_trades": 0,
  "forward_wr": 0,           // ALWAYS 0
  "forward_validated": false,  // NEVER VALIDATED
  "status": "OPEN"
}
```

**Root Cause:** The portfolio tracker (`portfolio_tracker_copytrader.py`) has the logic to 
calculate forward_wr but:
1. It requires `forward_validated` to be set to true
2. The validation only happens when `forward_trades > 0`
3. The `forward_trades` counter is never incremented because picks are stuck in "OPEN" status

#### C. Position Exit Logic Issues
From `portfolio_tracker_copytrader.py` (Lines 308-411):
```python
# Strict copy trader exits
OPTIMAL_HOLD_HOURS = 24  # Was 8h, now 24h
MAX_HOLD_HOURS = 72      # Was 24h, now 72h

# Sanity checks cap PnL at 250%
max_pnl_pct = 2.50  # 250% max for 5x leverage
```

**Problem:** The position exit logic has multiple safety checks that may prevent proper 
outcome resolution:
- Price change >50% triggers capping at +/-20%
- PnL >250% gets capped
- These sanity checks may be interfering with legitimate TP/SL hits

---

## 2. OUTCOME RESOLUTION LOGIC ISSUES

### Key Files:
- `.github/workflows/outcome-resolver.yml` (Lines 1-79)
- `alpha_engine/outcome_resolver.py` (625 lines)

### Issues Found:

#### A. PnL Threshold Too Strict
```python
# outcome_resolver.py (Lines 78-79)
PNL_WIN_THRESHOLD = 0.0001   # 0.01% — above this = WON
PNL_LOSS_THRESHOLD = -0.0001  # -0.01% — below this = LOST
```

**Problem:** A 0.01% threshold means:
- A trade with 0.009% profit is considered FLAT (not a win)
- A trade with -0.009% loss is considered FLAT (not a loss)
- This creates a "dead zone" where legitimate wins/losses are not counted

#### B. Workflow Schedule May Miss Rapid Moves
```yaml
# outcome-resolver.yml
schedule:
  - cron: '15 */2 * * *'  # Every 2 hours
```

**Problem:** Crypto markets move 24/7. A 2-hour resolution window means:
- TP/SL hits may be missed if price spikes and returns within 2 hours
- The resolver only checks current price, not price history
- Intra-period TP/SL hits are invisible to the resolver

#### C. Only Processes Closed Picks
```python
# outcome_resolver.py
CLOSED_PICKS_FILE = DATA_DIR / "closed_picks.json"
```

**Problem:** The resolver only processes picks already in `closed_picks.json`. It does NOT:
- Check active picks for TP/SL breaches
- Update forward_wr for copy trader picks
- Validate forward performance in real-time

---

## 3. PREDICTION MARKET INTEGRATION ISSUES

### Key Files:
- `.github/workflows/polymarket-signals.yml` (Lines 1-80)
- `alpha_engine/prediction_market_consensus.py` (442 lines)

### Issues Found:

#### A. Consensus Requirements Too Strict
```python
# prediction_market_consensus.py (Lines 52-58)
MIN_CONFIDENCE = 0.60      # 60% minimum confidence
MAX_CONFIDENCE = 0.90      # 90% maximum confidence (caps upside!)
MIN_SOURCE_CATEGORIES = 2  # Need 2+ independent sources
MIN_SCORE_GAP = 0.08       # 8% gap between yes/no required
```

**Problem:** These filters are TOO AGGRESSIVE:
- Most Polymarket markets have confidence 50-55% (just above random)
- Requiring 60% filters out 80%+ of valid signals
- Capping at 90% prevents high-conviction trades
- Requiring 2 source categories means single-source signals are ignored

#### B. Source Weights May Not Reflect Reality
```python
SOURCE_WEIGHTS = {
    "wallet_copy": 1.00,      # Copy trader wallets
    "kalshi": 0.85,           # Kalshi markets
    "polymarket_reverse": 0.65,  # Reverse-engineered Polymarket
}
```

**Problem:** The weights are arbitrary and not backtested. The highest weight (1.00) goes 
to wallet_copy which has the worst performance (0% WR in the issue description).

#### C. Latency in Signal Processing
```yaml
# polymarket-signals.yml
schedule:
  - cron: '*/30 * * * *'  # Every 30 minutes
```

**Problem:** 
- 30-minute scan interval means signals can be stale
- Polymarket markets move in seconds, not minutes
- By the time consensus is built, the edge may be gone

---

## 4. SCORING SYSTEM ISSUES

### Key Files:
- `alpha_engine/portfolio_tracker_copytrader.py` (Lines 60-65)
- `copy_trader_intel/consensus_pick_builder.py`

### Issues Found:

#### A. Anti-Predictive Scoring
From portfolio_tracker_copytrader.py:
```python
MIN_SCORE = 80  # Data-driven: scores below 80 have ~33% WR
                # Only 80+ has 65.9% WR
```

**Problem:** This is BACKWARDS from the issue description:
- The code says scores 80+ should have 65.9% WR
- The issue says "highest scored picks LOSE money"
- ML strategies with score=0 are the best performers

**Root Cause:** The scoring formula may be INVERTED. If:
- High score = Low actual win rate
- Low score = High actual win rate

Then the scoring system is actively harmful - it's an anti-predictor.

#### B. Elite Score Calculation May Be Broken
From active_picks.json:
```json
{
  "elite_score": 64,
  "elite_grade": "B",
  "forward_wr": 0,
  "forward_validated": false
}
```

**Problem:** 
- Elite score of 64 with grade "B" seems inconsistent
- Forward validation never happens
- The elite scoring may not correlate with actual performance

---

## 5. ML FEATURE PIPELINE ISSUES

### Key Files:
- `ml_crypto_predictor/production_engine.py` (1706 lines)
- `ml_crypto_predictor/feature_selection.py`

### Issues Found:

#### A. Dead Features Since March 8
The issue states "62% of ML features dead since March 8". Looking at production_engine.py:

```python
# production_engine.py - v3.1 features
- Volatility-based regime detection (4-state)
- Adaptive ATR-based TP/SL per pair
- Multi-timeframe features (4h + daily)
- Fear & Greed Index integration
- Purged walk-forward validation
- Correlation guard
- On-chain data integration
```

**Problem:** 
- Features may be failing silently
- No monitoring for feature health
- Dead features reduce model accuracy

#### B. Model Calibration Issues
```python
# production_engine.py mentions:
"Probability calibration (Platt + Isotonic) for honest confidence scores"
```

**Problem:** If calibration is wrong:
- 90% confidence may actually be 40% win rate
- This explains why high-confidence picks lose

---

## ROOT CAUSE ANALYSIS

### Why Copy Trader Picks Show 0% WR:

1. **Picks are never moved from "OPEN" to "CLOSED"**
   - The outcome resolver only processes closed_picks.json
   - Copy trader picks stay in active_picks.json indefinitely
   - No mechanism to check TP/SL on active copy trader picks

2. **Forward validation never triggers**
   - forward_validated remains false
   - forward_trades stays at 0
   - forward_wr stays at 0

3. **The workflow timeout kills the process**
   - 10-minute timeout is too short
   - Portfolio tracker can't complete its cycle
   - Picks never get updated

### Why Prediction Market Signals Don't Translate to Wins:

1. **Consensus filter is too strict**
   - 60% confidence requirement filters most valid signals
   - 2 source categories requirement blocks single-source signals
   - By the time consensus is reached, edge is gone

2. **Latency kills the signal**
   - 30-minute scan interval is too slow
   - Markets move faster than the scanner
   - Signals are stale when acted upon

### Why Scoring is Anti-Predictive:

1. **Scoring formula may be inverted**
   - High scores correlate with losses
   - Low scores correlate with wins
   - The system picks the worst trades

2. **No feedback loop**
   - Scores are not updated based on actual performance
   - Bad scoring persists indefinitely
   - System can't self-correct

---

## SPECIFIC FILE PATHS AND LINE NUMBERS

| File | Lines | Issue |
|------|-------|-------|
| `.github/workflows/copy-trader-forward-test.yml` | 24 | timeout-minutes: 10 (too short) |
| `alpha_engine/outcome_resolver.py` | 78-79 | PNL thresholds too strict (0.01%) |
| `alpha_engine/prediction_market_consensus.py` | 52-58 | MIN_CONFIDENCE too high (0.60) |
| `alpha_engine/portfolio_tracker_copytrader.py` | 60-65 | MIN_SCORE logic may be inverted |
| `copy_trader_intel/data/active_picks.json` | Multiple | forward_wr: 0, forward_validated: false |
| `ml_crypto_predictor/production_engine.py` | 37-67 | Dead features not monitored |

---

## RECOMMENDED FIXES

### Immediate (High Priority):
1. **Fix copy-trader-forward-test.yml timeout** - Increase to 30 minutes
2. **Fix outcome resolver to check active picks** - Don't just process closed picks
3. **Lower PNL thresholds** - Change from 0.01% to 0.001% or remove entirely
4. **Fix scoring inversion** - Investigate why high scores lose

### Short-term (Medium Priority):
1. **Reduce consensus requirements** - Lower MIN_CONFIDENCE to 0.55
2. **Increase scan frequency** - Change polymarket to 5-minute intervals
3. **Add feature health monitoring** - Alert when features go dead
4. **Implement score feedback loop** - Update scores based on actual performance

### Long-term (Low Priority):
1. **Rewrite outcome resolution** - Real-time TP/SL checking
2. **Implement proper forward validation** - Track copy trader picks through full lifecycle
3. **Add model calibration verification** - Ensure confidence scores match actual win rates

---

## CONCLUSION

The trading system has multiple interconnected issues:

1. **Copy trader 0% WR** - Picks never get validated due to workflow timeouts and logic gaps
2. **Prediction market signals blocked** - Filters are too aggressive, blocking valid signals
3. **Anti-predictive scoring** - High scores correlate with losses (formula may be inverted)
4. **Dead ML features** - 62% of features not working since March 8

The root cause is a combination of:
- Workflow timeouts killing processes before completion
- Outcome resolver only checking closed picks (not active ones)
- Overly strict filtering of prediction market signals
- Scoring system that may be actively harmful (anti-predictive)

Fixing these issues requires addressing the workflow timeouts, expanding outcome resolution 
to active picks, relaxing consensus filters, and investigating the scoring formula.
