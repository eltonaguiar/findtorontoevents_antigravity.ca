# Baby Bundle System Guide
## The Evolution of Strategy Tracking

**Version:** 2.0  
**Date:** February 27, 2026  
**Status:** Production Ready

---

## ⚠️ AI NOTE: Proper Documentation Process

> **For AIs reviewing this system:**
> 
> This file (`BABY_BUNDLE_GUIDE.md`) is the **GUIDE** - it explains how the system works.
> 
> The **CANONICAL BUNDLE REGISTRY** is in `BUNDLE_REGISTRY.md` - that's where all active bundles are documented.
> 
> **Process when adding bundles:**
> 1. Add detailed bundle documentation to `BUNDLE_REGISTRY.md`
> 2. Update the "Current Active Bundles" section in this file with a SUMMARY and link to registry
> 3. NEVER duplicate full bundle details in both files
> 4. Web AI can view registry at: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/blob/main/BUNDLE_REGISTRY.md

---

## What is a Baby Bundle?

A **Baby Bundle** is a curated group of strategies that share similar characteristics:
- **Symbol Scope**: Single, Multi, or Broad asset coverage
- **Timeframe Scope**: Single, Partial, or Multi-timeframe robustness
- **Direction Bias**: Long-only, Short-only, or Both directions

Unlike individual strategies, bundles provide:
- **Better diversification** across similar strategy types
- **Reduced overfitting** through grouped classification
- **Clearer forward-test tracking** with full audit trails
- **Early-stage warnings** for bundles with <100 trades

---

## Bundle Classification System

### Symbol Scope

| Type | Description | Example |
|------|-------------|---------|
| **Single Symbol** | Works on only 1 specific asset | Only BTC/USDT |
| **Multi Symbol** | Works on BTC/ETH/SOL (Tier 1) | Top 3 majors |
| **Broad** | Works on 4+ symbols | Most top 14 pairs |

### Timeframe Scope

| Type | Description | Reliability |
|------|-------------|-------------|
| **Single TF** | Only works on 1h OR 4h OR 1d | Low |
| **Partial TF** | Passes 1-2 timeframes | Medium |
| **Multi TF** | Passes Tier 2 (all 3 timeframes) | High |

### Direction Bias

- **Long Only**: Bullish strategies only
- **Short Only**: Bearish strategies only
- **Both Directions**: Market-neutral or adaptive

---

## Current Active Bundles

**See full details in [BUNDLE_REGISTRY.md](./BUNDLE_REGISTRY.md)**

### Summary (as of 2026-02-27)

| Bundle | Classification | Strategies | Best Sharpe | Status |
|--------|---------------|------------|------------|--------|
| #1 | single_symbol / single_timeframe / long_only | 3 | 5.41 | PAPER |
| #2 | single_symbol / multi_timeframe / long_only | 1 | 1.17 | PAPER |
| #3 | single_symbol / partial_timeframe / long_only | 2 | 5.67 | PAPER |
| **#4** | **multi_symbol / multi_timeframe / both** | **1** | **2.21** | **PAPER** |
| **#5** | **multi_symbol / partial_timeframe / both** | **3** | **16.75** | **PAPER** |
| **#6** | **single_symbol / partial_timeframe / both** | **4** | **16.23** | **PAPER** |

Bundles #4-6 tested against **REAL Binance OHLCV data** (not proxy/synthetic).
All bundles are in **[NEW]** status (<100 forward trades).

**⚠️ WARNING:** These bundles are in EARLY STAGE and need 100+ forward trades before metrics can be trusted.

---

## Forward Testing (THE MAIN THING)

Backtest performance is **NOT** what matters. What matters is:

### Forward Test Requirements

| Metric | Minimum | Preferred | Elite |
|--------|---------|-----------|-------|
| Trades | 20 | 100+ | 500+ |
| Win Rate | >45% | >55% | >60% |
| Sharpe | >0.8 | >1.0 | >1.5 |
| Drawdown | <25% | <15% | <10% |

### Win Rate Decay Warning

```
Typical decay from backtest to forward:
- Backtest WR: 70%
- Forward WR: 45-50% (30-35% decay)

A bundle with 80% backtest WR might only achieve 50-55% forward.
This is NORMAL and expected.
```

---

## Discord Commands

### !fc-bundle (RECOMMENDED)

**Shows top performing bundles with forward test results:**

```
[BUNDLE BABIES - TOP TIER STRATEGIES]
*2026-02-27 22:58 UTC* | Command: !fc-bundle

[RECOMMENDED] THIS IS THE TOP COMMAND FOR STRATEGY TRACKING

**1. [NEW] Single_Symbol Single_Timeframe Long_Only**
[WARNING] EARLY STAGE - Less than 100 forward trades

BACKTEST (Historical):
  Sharpe: 5.41 | Win Rate: 83.3% | Max DD: 4.5%

FORWARD (Live Paper Trading - THE MAIN THING):
  Status: PAPER
  Total Trades: 0 (Need 100+ for reliability)
  Sharpe: 0.00 | Win Rate: 0.0%
```

### !fc-baby (Legacy)

Shows individual strategies but **recommends using !fc-bundle instead**.

---

## File Structure

```
battleground/data/
├── bundle_babies.db              # SQLite database
│   ├── bundle_babies table       # Bundle definitions
│   └── bundle_trades table       # Full audit trail
├── baby_strats_dashboard.json    # Battleground display
└── tiered_backtest_results_*.json # Source data

bundle_baby_system.py              # Main bundle management
bundle_baby_live_tracker.py        # Live pick tracking
discord_bundle_baby.py             # Discord !fc-bundle command
discord_baby_forward_test.py       # Discord !fc-baby command
BABY_BUNDLE_GUIDE.md               # This guide (you are here)
BUNDLE_REGISTRY.md                 # Canonical bundle registry
```

---

## Audit Trail

Every trade is recorded with:

```
Trade ID: bundle_id_strategy_timestamp
Entry Time (EST): 2026-02-27 14:30:00
Exit Time (EST): 2026-02-27 16:45:00 (or OPEN)
Entry Price: $85,000
Exit Price: $87,500 (or current)
Take Profit: $89,250
Stop Loss: $82,750
Side: LONG

Progress Metrics:
  Progress to TP: 45%
  Distance to SL: 35%
  
P&L Tracking:
  Realized P&L: +2.94%
  Unrealized P&L: 0%
  Max Profit Reached: +3.2%
  Max Loss Reached: -0.5%

Exit Reason: TP_HIT (or SL_HIT, MANUAL, TIMEOUT)
```

---

## Creating New Bundles

```bash
# Create bundles from tiered results
python bundle_baby_system.py --create

# Update battleground with bundles at TOP
python bundle_baby_system.py --update-battleground

# List all bundles
python bundle_baby_system.py --list

# Generate audit report
python bundle_baby_system.py --audit <bundle_id>
```

**⚠️ CRITICAL: Before creating a bundle, check [BUNDLE_REGISTRY.md](./BUNDLE_REGISTRY.md) to avoid duplicates!**

---

## Live Tracking

```bash
# Scan once for new picks
python bundle_baby_live_tracker.py --scan

# Continuous monitoring (checks every 5 minutes)
python bundle_baby_live_tracker.py --watch

# Update open trades with current prices
python bundle_baby_live_tracker.py --update
```

---

## Recommended Workflow

### Phase 1: Bundle Creation
1. Run tiered backtests to find passing strategies
2. Group by classification (symbol/tf/direction)
3. Check BUNDLE_REGISTRY.md to avoid duplicates
4. Create bundles using `bundle_baby_system.py`
5. Add bundle to BUNDLE_REGISTRY.md (NOT here)

### Phase 2: Forward Testing
1. Start live tracking with `bundle_baby_live_tracker.py --watch`
2. Monitor for 100+ trades minimum
3. Track win rate decay vs backtest

### Phase 3: Graduation Decision
1. If forward WR > 55% after 100 trades → GRADUATE
2. If forward WR 45-55% → Continue monitoring
3. If forward WR < 45% → Archive bundle

### Phase 4: Live Deployment
1. Deploy graduated bundles with 1% sizing
2. Continue tracking in live mode
3. Kill switch if forward WR drops below 50%

---

## Early Stage Warning

**⚠️ CRITICAL: Bundles with <100 trades are EXPERIMENTAL**

```
Why 100 trades matters:
- Statistical significance (law of large numbers)
- Captures different market regimes
- Filters out lucky streaks
- Reveals true edge decay

What to do with early-stage bundles:
✓ Track them
✓ Record every trade
✓ Wait for 100+ sample size
✗ DON'T trust the metrics yet
✗ DON'T deploy with real capital
```

---

## Bundle Performance Tiers

### [NEW] - Early Stage (0-99 trades)
- Status: Experimental
- Trust Level: LOW
- Action: Track and wait

### [TRACKING] - Building History (100-499 trades)
- Status: Evaluating
- Trust Level: MEDIUM
- Action: Monitor for graduation

### [PROVEN] - Graduated (500+ trades, WR > 55%)
- Status: Production ready
- Trust Level: HIGH
- Action: Deploy with proper sizing

---

## Key Insights

1. **Bundles > Individual Strategies**
   - Grouped classification reduces noise
   - Clearer performance tracking
   - Better risk management

2. **Forward Test > Backtest**
   - Only forward metrics matter
   - Expect 20-50% decay from backtest
   - 100+ trades minimum for reliability

3. **Early Stage Warning**
   - <100 trades = experimental
   - Don't deploy early-stage bundles
   - Wait for statistical significance

4. **Graduation Criteria**
   - 100+ forward trades
   - Forward WR > 55%
   - Forward Sharpe > 1.0
   - Positive realized P&L

---

## Links & Resources

- **Bundle Registry**: [BABY_BUNDLE_REGISTRY.md](./BABY_BUNDLE_REGISTRY.md) - Canonical list of all bundles
- **Ideas & Feedback**: [BABY_IDEAS.md](./BABY_IDEAS.md) - Community contributions
- **Web AI Guide**: [BABY_STRAT_WEB_AI_GUIDE.md](./BABY_STRAT_WEB_AI_GUIDE.md) - For web-only AIs
- **Database**: `battleground/data/bundle_babies.db`
- **Discord Commands**: `!fc-bundle` (recommended), `!fc-baby` (legacy)
- **Live Tracker**: `python bundle_baby_live_tracker.py --watch`
- **GitHub**: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca
- **Web AI Access**: 
  - Guide: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/blob/main/BABY_BUNDLE_GUIDE.md
  - Registry: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/blob/main/BABY_BUNDLE_REGISTRY.md
  - Ideas: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/blob/main/BABY_IDEAS.md
  - Baby Strategies: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/tree/main/baby_strategies
  - Cursor AI Strategies: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/tree/main/incubator/agents/cursor_ai

---

*⚠️ Not financial advice - DYOR!*
