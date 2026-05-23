# Cross-System & Cross-Strategy Permutation Testing System

**Date:** 2026-03-08  
**Version:** 1.0  
**Author:** AI Assistant

---

## Executive Summary

This document describes the implementation of a comprehensive permutation testing system that tracks which **trading system combinations** (cross-system) and **strategy combinations** (cross-strategy) can be trusted to generate profit in forward testing.

### Key Findings (Current)

| Metric | Value |
|--------|-------|
| System Permutations Tracked | 13 |
| Strategy Permutations Tracked | 15 |
| Highly Trusted System Combos | 2 (Battleground, Claude Gainer) |
| Highly Trusted Strategy Combos | 0 (insufficient data) |
| Active Picks Monitored | 838 |
| Total Systems | 56 |

### Top Performing System Permutations

| Rank | Permutation | Trust Score | Win Rate | Trades | Status |
|------|-------------|-------------|----------|--------|--------|
| 1 | Solo: Battleground | 84.1 | 60.2% | 669 | ⭐ Highly Trusted |
| 2 | Solo: Claude Gainer | 70.0 | 70.0% | 10 | ⭐ Highly Trusted |
| 3 | Solo: KIMI Signals | 60.6 | 64.0% | 1028 | ✅ Trusted |
| 4 | Solo: Alpha Engine | 35.7 | 39.2% | 204 | ⏳ Promising |
| 5 | Solo: Rapid Fire | 0.0 | 0.0% | 0 | ⏳ Unproven |

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Files Modified/Created](#files-modifiedcreated)
3. [System Permutation Tracking](#system-permutation-tracking)
4. [Strategy Permutation Tracking](#strategy-permutation-tracking)
5. [Trust Score Algorithm](#trust-score-algorithm)
6. [Dashboard UI Changes](#dashboard-ui-changes)
7. [How to Use](#how-to-use)
8. [Current Limitations](#current-limitations)
9. [Future Enhancements](#future-enhancements)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    DATA COLLECTION LAYER                         │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Active Picks │  │ Closed Picks │  │ System Stats │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         └─────────────────┼─────────────────┘                   │
│                           ▼                                      │
├─────────────────────────────────────────────────────────────────┤
│              PERMUTATION ANALYSIS ENGINE                         │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐    ┌─────────────────────┐             │
│  │ Cross-System Perm   │    │ Cross-Strategy Perm │             │
│  │ - Solo systems      │    │ - Solo strategies   │             │
│  │ - Pairs (2 agree)   │    │ - Pairs (2 agree)   │             │
│  │ - Triplets (3 agree)│    │ - Category mixes    │             │
│  │ - Flexible consensus│    │ - Confluence        │             │
│  └──────────┬──────────┘    └──────────┬──────────┘             │
│             └────────────┬─────────────┘                        │
│                          ▼                                       │
│  ┌─────────────────────────────────────────┐                    │
│  │        TRUST SCORE CALCULATOR           │                    │
│  │  - Win rate (40% weight)                │                    │
│  │  - PnL performance (30% weight)         │                    │
│  │  - Sample size (20% weight)             │                    │
│  │  - Drawdown penalty (10% weight)        │                    │
│  └──────────────┬──────────────────────────┘                    │
│                 ▼                                                │
├─────────────────────────────────────────────────────────────────┤
│                    DASHBOARD LAYER                               │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Cross-Sys Tab│  │ Cross-Strat  │  │ Picks Table  │          │
│  │ (13 perms)   │  │ Tab (15 perms)│ │ (agreement)  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Files Modified/Created

### New Files Created

| File | Path | Purpose |
|------|------|---------|
| `system_permutation_config.json` | `paper_trading/` | Configuration for 43 system portfolios |
| `strategy_combination_config.json` | `paper_trading/` | Configuration for 42 strategy portfolios |
| `permutation_portfolio_manager.py` | `paper_trading/` | Execution engine for paper trading |
| `permutation_analyzer.py` | `paper_trading/` | Analysis and reporting engine |
| `run_permutation_test.py` | `paper_trading/` | Quick-start script |
| `PERMUTATION_README.md` | `paper_trading/` | Full documentation |
| `CROSS_PERMUTATION_SYSTEM.md` | Root | This document |

### Modified Files

| File | Changes |
|------|---------|
| `audit_trail/dashboard_generator.py` | Added `collect_cross_system_permutations()` and `collect_cross_strategy_permutations()` functions; added source_systems to picks |
| `audit_dashboard/index.html` | Added "🔀 Cross-Sys" and "🎯 Cross-Strat" tabs; added agreement count column; added system involvement display |

---

## System Permutation Tracking

### Tracked Permutations (13 total)

#### Solo Systems (7)
- Solo: Alpha Engine
- Solo: Battleground
- Solo: Rapid Fire
- Solo: KIMI Signals
- Solo: Claude Gainer
- Solo: Crypto ML Edge
- Solo: Coinglass

#### Pairs (5)
- Pair: Alpha + Battleground
- Pair: Alpha + KIMI
- Pair: Battleground + KIMI
- Pair: Alpha + Claude
- Pair: Rapid Fire + Battleground

#### Triplets (1)
- Triple: Alpha + Battle + KIMI

### Data Collection Method

```python
def collect_cross_system_permutations(active, closed):
    PERMUTATIONS = {
        "solo_battleground": {
            "name": "Solo: Battleground",
            "systems": ["battleground"],
            "min_agree": 1
        },
        "pair_alpha_battle": {
            "name": "Pair: Alpha + Battleground",
            "systems": ["alpha_engine", "battleground"],
            "min_agree": 2
        },
        # ... more permutations
    }
    
    for pick in active + closed:
        # Count how many target systems are in this pick
        systems_present = set(pick.get("source_systems", []))
        agreement_count = len(systems_present.intersection(target_systems))
        
        if min_agreement <= agreement_count <= max_agreement:
            # This pick qualifies for this permutation
            track_performance(pick, permutation)
```

---

## Strategy Permutation Tracking

### Tracked Permutations (15 total)

#### Solo Strategies (6)
- Solo: EMA Stack
- Solo: MACD Crossover
- Solo: StochRSI MACD
- Solo: Volume Breakout
- Solo: Bollinger Squeeze
- Solo: IRB Hoffman

#### Pairs/Confluence (5)
- Pair: Trend + Momentum
- Pair: Breakout + Volatility
- Pair: Prop + Technical
- Confluence: Any 2 Strategies
- Confluence: 2 Trend Agree

#### Categories (3)
- Category: All Trend
- Category: All Mean Reversion
- Category: All Breakout

#### Hybrid (1)
- ML + Technical

### Strategy Agreement Logic

```python
# For solo strategies
if pick_strategy in target_strategies:
    track_for_permutation(pick, permutation)

# For confluence strategies
pick_strategies = pick.get("source_strategies", [pick_strategy])
agreement = len(set(pick_strategies).intersection(target_strategies))
if agreement >= min_agree:
    track_for_permutation(pick, permutation)
```

---

## Trust Score Algorithm

### Formula

```
Trust Score (0-100) = 
    min(40, win_rate * 0.4) +           # Win rate component
    min(30, max(0, total_pnl) * 1.5) +  # PnL component
    min(20, total_trades * 0.2) +       # Sample size component
    bonus(10 if profit_factor > 1)      # Consistency bonus
```

### Tier Classification

| Trust Score | Tier | Action |
|-------------|------|--------|
| 70-100 | ⭐ Highly Trusted | Allocate significant capital |
| 50-69 | ✅ Trusted | Allocate moderate capital |
| 30-49 | ⏳ Promising | Small allocation / monitor |
| < 30 with trades | ⚠️ Unproven | Paper trade only |
| < 30 no trades | ⏳ Insufficient Data | Wait for more data |

---

## Dashboard UI Changes

### New Tabs Added

#### 🔀 Cross-System Tab
- Summary cards (total tracked, highly trusted, trusted, with trades)
- Rankings table with sortable columns
- Trust tier badges
- Active picks grouped by permutation

#### 🎯 Cross-Strategy Tab
- Category-based grouping (Trend, Confluence, Category, Strict, Hybrid)
- Top 5 performers highlighted
- Trust score visualization with color coding
- Strategy agreement details

### Enhanced Picks Table

#### New Column: "Agree"
Shows system agreement level:
```
●●● = 3+ systems agree (green)
●● = 2 systems agree (blue)
● = 1 system (solo) (gray)
```

#### Enhanced "System" Column
Now shows multiple systems when they agree:
```
Before: rapid_fire
After:  rapid_fire
        battleground
        kimi_signal_tracking
```

---

## How to Use

### Running the System

```bash
# Regenerate dashboard with permutation data
cd audit_trail
python dashboard_generator.py

# Or full paper trading run
cd paper_trading
python run_permutation_test.py
```

### Viewing Results

1. Open `audit_dashboard/index.html`
2. Click **"🔀 Cross-Sys"** tab for system combinations
3. Click **"🎯 Cross-Strat"** tab for strategy combinations
4. View **"Agree"** column in picks tables

### Interpreting Results

#### High Trust Score (70+)
- System/strategy has proven track record
- Sufficient sample size (10+ trades)
- Positive PnL and win rate > 50%
- **Action:** Consider for live trading

#### Medium Trust Score (50-69)
- Good performance but limited data or lower win rate
- **Action:** Monitor and small allocation

#### Low Trust Score (< 50)
- Insufficient data or poor performance
- **Action:** Paper trade only or avoid

---

## Current Limitations

1. **Strategy Matching**: Strategy permutations rely on exact strategy name matching. Variations in naming (e.g., "ema_stack" vs "ema_stack_fast") may not be grouped correctly.

2. **Closed Trade Data**: Many strategy permutations show 0 trades because closed picks don't always have strategy metadata properly attached.

3. **System Identification**: Some systems may be under-reported if `source_system` field is not consistently populated across all data sources.

4. **Sample Size**: Most permutations need more time to accumulate sufficient trade history for reliable trust scores.

---

## Future Enhancements

### Planned Features

1. **Dynamic Position Sizing**
   - Allocate more capital to high-trust permutations
   - Reduce allocation to underperforming combinations

2. **Auto-Promotion**
   - Automatically move high-trust permutations to live trading
   - Alert when trust scores cross thresholds

3. **Correlation Analysis**
   - Detect which permutations are correlated
   - Avoid over-concentration in similar strategies

4. **Machine Learning**
   - Predict which permutations will work best
   - Identify optimal agreement levels dynamically

5. **Real-Time Alerts**
   - Discord notifications when high-trust combinations fire
   - Daily summary of permutation performance

### Technical Improvements

1. **Strategy Normalization**
   - Map similar strategies to canonical names
   - Better handling of strategy variations

2. **Historical Backfill**
   - Import historical data for more robust trust scores
   - Weight recent performance higher

3. **Multi-Timeframe Analysis**
   - Track permutations by timeframe (1h, 4h, 1d)
   - Identify best timeframe for each combination

---

## Detailed Findings

### System Permutation Analysis

| Permutation | Systems | Trust | WR | PnL | PF | Active | Assessment |
|-------------|---------|-------|-----|-----|-----|--------|------------|
| Solo: Battleground | battleground | 84.1 | 60.2% | + | 1.8 | 2 | ⭐ Best solo system |
| Solo: Claude Gainer | claude_gainer_ml_perf | 70.0 | 70.0% | + | 2.5 | 0 | ⭐ Strong but limited data |
| Solo: KIMI Signals | kimi_signal_tracking | 60.6 | 64.0% | + | 1.9 | 0 | ✅ Reliable |
| Solo: Alpha Engine | alpha_engine | 35.7 | 39.2% | - | 0.9 | 12 | ⚠️ Underperforming |
| Solo: Rapid Fire | rapid_fire | 0.0 | 0.0% | 0 | - | 528 | ⏳ Too new to evaluate |

### Strategy Permutation Analysis

| Permutation | Category | Active | Notes |
|-------------|----------|--------|-------|
| Solo: EMA Stack | Trend | 184 | Most active trend strategy |
| Pair: Trend + Momentum | Confluence | 416 | High activity, need closed data |
| ML + Technical | Hybrid | 352 | Popular hybrid approach |
| Pair: Prop + Technical | Confluence | 331 | Strong theoretical basis |
| Category: All Trend | Category | 325 | Broad trend exposure |

### Agreement Analysis

**Most Agreed Symbols (Active Picks):**
- BTCUSDT LONG: 18 systems agree (strong consensus)
- ETHUSDT LONG: 18 systems agree
- BNBUSDT LONG: 14 systems agree
- XRPUSDT LONG: 12 systems agree
- ADAUSDT LONG: 11 systems agree

**Interpretation:** Major cryptos (BTC, ETH) have highest system agreement, suggesting broad market consensus on direction.

---

## Technical Implementation Notes

### Database Schema

```sql
-- New table for permutation tracking
CREATE TABLE permutation_positions (
    id TEXT PRIMARY KEY,
    portfolio_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    direction TEXT NOT NULL,
    entry_price REAL NOT NULL,
    tp REAL NOT NULL,
    sl REAL NOT NULL,
    source_systems TEXT,  -- JSON array
    source_strategies TEXT,  -- JSON array
    agreement_count INTEGER DEFAULT 1,
    confidence REAL DEFAULT 0.5,
    status TEXT DEFAULT 'ACTIVE',
    pnl_pct REAL DEFAULT 0.0
);
```

### JSON Payload Structure

```json
{
  "cross_system_permutations": {
    "permutations": [
      {
        "id": "solo_battleground",
        "name": "Solo: Battleground",
        "systems": ["battleground"],
        "trust_score": 84.1,
        "trust_tier": "Highly Trusted",
        "win_rate": 60.2,
        "total_trades": 669,
        "total_pnl": 123.4,
        "profit_factor": 1.8,
        "active_picks": [...]
      }
    ],
    "summary": {
      "total_tracked": 13,
      "highly_trusted": 2,
      "trusted": 1
    }
  },
  "cross_strategy_permutations": {
    "permutations": [...],
    "by_category": {
      "trend": [...],
      "confluence": [...]
    }
  }
}
```

---

## Conclusion

The cross-permutation testing system is now operational and tracking both system and strategy combinations. Initial findings show:

1. **Battleground** is the most trusted individual system (84.1 trust score)
2. **Claude Gainer ML** shows promise but needs more trade history
3. **Rapid Fire** has high activity (528 picks) but no closed trades yet
4. **System agreement** is strongest on major cryptos (BTC, ETH)
5. **Strategy permutations** need more closed trade data for reliable scoring

### Recommended Actions

1. **Immediate:** Allocate capital to Battleground solo (high trust)
2. **Monitor:** Watch Claude Gainer for more trade confirmations
3. **Wait:** Allow Rapid Fire to accumulate more history
4. **Investigate:** Improve closed trade data capture for strategy permutations

---

## Appendix

### A. Trust Score Calculation Code

```python
def calculate_trust_score(stats):
    """Calculate trust score (0-100) for a permutation."""
    if stats["total_trades"] < 10:
        return 0  # Insufficient data
    
    score = 0
    # Win rate component (max 40)
    score += min(40, stats["win_rate"] * 0.4)
    
    # PnL component (max 30)
    score += min(30, max(0, stats["total_pnl"]) * 1.5)
    
    # Sample size component (max 20)
    score += min(20, stats["total_trades"] * 0.2)
    
    # Profit factor bonus (max 10)
    if stats["profit_factor"] and stats["profit_factor"] > 1:
        score += 10
    
    return round(score, 1)
```

### B. System Links Reference

```javascript
const sysLinks = {
  'battleground': '/battleground/',
  'alpha_engine': 'https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/alpha/',
  'kimi_signal_tracking': '/riseoftheclaw.html',
  'rapid_fire': '/findcryptopairs/now.html',
  'claude_gainer_ml_perf': '/updates/antigravity-ml-gainer.html',
  // ... more systems
};
```

### C. Paper Trading Integration

The permutation system integrates with existing paper trading:
- Uses same database (`paper.db`)
- Same position sizing (2% risk)
- Same TP/SL logic
- Separate tables to avoid conflicts

---

*End of Document*
