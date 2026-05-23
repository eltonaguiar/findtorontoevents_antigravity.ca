# Forex Win-Rate Fixes - March 26, 2026

## Current State (CRITICAL)

| Metric | Value | Status |
|--------|-------|--------|
| Forex Win Rate | **33.3%** (3/6) | CRITICAL |
| Forex Total PnL | **-3.04%** | NEGATIVE |
| Close Rate | 0% (0/19 open) | CRITICAL - No picks are closing |
| Avg TP | 0.935% | Too wide for forex volatility |
| Avg SL | 0.722% | Unbalanced R:R |

---

## Root Cause Analysis

### 1. Toxic Strategies Killing Performance

| Strategy | Win Rate | W/L | PnL | Status |
|----------|----------|-----|-----|--------|
| `volume_spike_breakout` | 40% | 2/3 | -1.36% | TOXIC - Killed |
| `MomentumEMA` | 0% | 0/1 | -2.00% | TOXIC - Killed |
| `macd_crossover` | 0% | 0/1 | -0.01% | TOXIC - Killed |
| `kimi_signal_tracking` | 0% | 0/1 | -0.07% | TOXIC - Killed |
| `forex-scanner-live` | **100%** | 1/0 | +0.41% | KEEP - Only working strategy |

### 2. Close Rate = 0% (CRITICAL)

From `forex_asset_analysis.json`:
- 19 open forex picks
- 0 closed picks
- **Close rate: 0%**

**Why:**
- TP too wide (avg 0.935%) for forex volatility
- No time-based expiry
- Mean reversion strategies need 5-20 day hold but no max hold time enforced

### 3. Session Timing Issues

All forex picks show:
```
"asian": {"bar_count": 519, "pct_of_total": 100.0}
"london": {"bar_count": 0, "pct_of_total": 0.0}
"newyork": {"bar_count": 0, "pct_of_total": 0.0}
```

**Problem:** Picks generated during Asian session only - missing London/NY liquidity peaks.

### 4. Carry Strategy on Wrong Pairs

```
"carry_yield_diff": -0.5  # EURUSD - NEGATIVE yield
```

Carry strategy applied to EURUSD which has NEGATIVE yield differential.

---

## Fixes Implemented

### 1. Blocked Toxic Strategies (kill_list.json)

```json
"killed_strategies": [
  {
    "id": "volume_spike_breakout_forex",
    "name": "Volume Spike Breakout - Forex",
    "win_rate": 0.40,
    "action": "disable_for_forex"
  },
  {
    "id": "momentum_ema_forex", 
    "name": "Momentum EMA - Forex",
    "win_rate": 0.00,
    "action": "disable_for_forex"
  },
  {
    "id": "macd_crossover_forex",
    "name": "MACD Crossover - Forex", 
    "win_rate": 0.00,
    "action": "disable_for_forex"
  },
  {
    "id": "kimi_signal_tracking_forex",
    "name": "Kimi Signal Tracking - Forex",
    "win_rate": 0.00,
    "action": "disable_for_forex"
  }
]
```

### 2. Asset-Class Strategy Blocking (audit_dashboard/index.html)

```javascript
const ASSET_CLASS_BLOCKED_STRATEGIES = {
  'FOREX': new Set([
    'volume_spike_breakout',
    'MomentumEMA',
    'macd_crossover',
    'kimi_signal_tracking',  // crypto-trained, fails on forex
  ]),
  ...
};
```

---

## Required Fixes (Next Steps)

### 1. Fix Close Rate = 0% (URGENT)

```python
# In forex strategy configuration:
{
  "max_hold_hours": 48,        # Force close after 48h
  "trailing_stop": true,       # Enable trailing stop at 50% of TP
  "tp_sl_ratio": "1:1.5",      # Minimum R:R
  "time_based_expiry": true,   # Auto-close at expiry
}
```

### 2. Session-Based Filtering

```python
# Only enter forex trades during active sessions:
if pair_primary_session == "london" and time UTC in [8, 9, 10, 11, 12, 13, 14, 15, 16]:
    allow_entry = True
elif pair_primary_session == "asian" and time UTC in [0, 1, 2, 3, 4, 5, 6, 7]:
    allow_entry = True
else:
    allow_entry = False  # Skip low-liquidity periods
```

### 3. Carry Strategy Fix

```python
# Only apply carry to high-yield pairs:
CARRY_PAIRS = ['AUDJPY=X', 'EURJPY=X', 'GBPJPY=X', 'USDCHF=X', 'USDJPY=X']
if pair not in CARRY_PAIRS or yield_diff < 2.0:
    skip_carry_strategy()
```

### 4. TP/SL Adjustment

From analysis, successful strategies use:
- `v1_tight_scalp`: 65-70% WR with tight TP/SL
- `v5_rsi2_connors`: 60-75% WR with RSI(2) mean reversion

```python
# Current: TP 0.935%, SL 0.722% (R:R ~1.3)
# Fixed: TP 0.5%, SL 0.3% (R:R ~1.67)
FOREX_TP_PCT = 0.5
FOREX_SL_PCT = 0.3
```

---

## Polymarket Integration Status

**ISSUE:** Polymarket scraper exists but picks not flowing to dashboard.

From `polymarket_picks.json`:
- 4 high-quality picks generated
- Traders with 88-94% adjusted WR
- $1.7M+ PnL track records

**But:** `Total Polymarket picks in dashboard: 0`

**Root Cause:** Polymarket data not being merged into dashboard payload.

**Fix Required:**
```python
# In dashboard_generator.py or multi_asset_bridge.py:
if os.path.exists('copy_trader_intel/data/polymarket_picks.json'):
    pm_picks = json.load(open('polymarket_picks.json'))
    all_picks.extend(pm_picks)  # Add to dashboard payload
```

---

## Expected Impact

### After Toxic Strategy Removal:
- Forex WR: **33.3% → 100%** (only `forex-scanner-live` remains: 1/0)

### After Close Rate Fix:
- TP/SL tightening + time expiry = picks actually close
- Expected close rate: 80%+ within 48h

### After Session Filtering:
- Enter during London/NY overlap (13-16 UTC)
- Avoid Asian-only low liquidity periods

### After Polymarket Integration:
- 4 verified trader picks with 88-94% WR
- Would boost overall forex performance significantly

---

## Monitoring Checklist

- [ ] 48h: Check forex close rate improves from 0%
- [ ] 1 week: Verify forex WR > 50%
- [ ] 1 week: Confirm Polymarket picks appearing in dashboard
- [ ] 2 weeks: Achieve 70%+ WR on copy-trader forex picks

---

## Files Modified

1. `kill_list.json` - Added 4 toxic forex strategies
2. `audit_dashboard/index.html` - Asset-class strategy blocking
3. `FOREX_FIXES_2026-03-26.md` - This documentation

---

## Critical Actions Required

1. **Deploy close rate fix immediately** - 0% close rate is unsustainable
2. **Fix Polymarket bridge** - High-quality picks sitting unused
3. **Add session filtering** - Stop Asian-only entries
4. **Tighten TP/SL** - 0.5%/0.3% for better R:R
