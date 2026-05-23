# Bundle Registry
## Canonical Record of All Baby Bundles

**Last Updated:** 2026-02-27  
**Purpose:** Prevent duplicate bundle creation by maintaining official registry

---

## ⚠️ AI NOTE: This is the CANONICAL Registry

> **For AIs reviewing this system:**
> 
> This file (`BABY_BUNDLE_REGISTRY.md`) is the **CANONICAL BUNDLE REGISTRY** - the single source of truth for all active bundles.
> 
> The **GUIDE** is in `BABY_BUNDLE_GUIDE.md` - that's where system documentation lives.
> 
> **Process when adding bundles:**
> 1. Add detailed bundle documentation to THIS file (BUNDLE_REGISTRY.md)
> 2. Update the summary in BABY_BUNDLE_GUIDE.md with link to this registry
> 3. NEVER duplicate full bundle details in both files
> 
> **Web Access URLs:**
> - This Registry: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/blob/main/BABY_BUNDLE_REGISTRY.md
> - Guide: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/blob/main/BABY_BUNDLE_GUIDE.md
> - Baby Strategies: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/tree/main/baby_strategies
> - Cursor AI Strategies: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/tree/main/incubator/agents/cursor_ai
> - Database: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/blob/main/battleground/data/bundle_babies.db

---

---

## Active Bundles

### Bundle #1: Single_Symbol Single_Timeframe Long_Only
```yaml
Bundle ID: bundle_single_symbol_single_timeframe_long_only_20260227
Status: ACTIVE
Classification:
  Symbol Scope: single_symbol
  Timeframe Scope: single_timeframe
  Direction Bias: long_only
Created: 2026-02-27

Strategies (3):
  1. crypto_multiframe_breakout_pulse_v1 (cursor)
     - Best: SOL/USDT 1h
     - Backtest: Sharpe 5.41, WR 83.3%, DD 4.5%
     
  2. nylondon_flow_session_momentum_v1 (cursor)
     - Best: SOL/USDT 1h
     - Backtest: Sharpe 4.47, WR 78.6%, DD 5.7%
     
  3. crypto_multiframe_regime_router_v1 (cursor)
     - Best: ETH/USDT 1h
     - Backtest: Sharpe 4.41, WR 66.7%, DD 1.1%

Forward Performance:
  Status: PAPER (Early Stage)
  Total Trades: 0
  Realized PnL: 0.0%
  Warning: <100 trades - metrics unreliable
```

### Bundle #2: Single_Symbol Multi_Timeframe Long_Only
```yaml
Bundle ID: bundle_single_symbol_multi_timeframe_long_only_20260227
Status: ACTIVE
Classification:
  Symbol Scope: single_symbol
  Timeframe Scope: multi_timeframe
  Direction Bias: long_only
Created: 2026-02-27

Strategies (1):
  1. crypto_long_only_drift_capture_v1 (cursor)
     - Best Pair: ETH/USDT
     - Direction: LONG
     - Tier 1: PASS (ETH pass; BTC/SOL fail)
     - Tier 2: 3/3 PASS on ETH (1h, 4h, 1d)
     - Backtest snapshot:
       1h: Sharpe 1.17, WR 63.33%, DD 3.53%, Trades 30
       4h: Sharpe 1.01, WR 55.17%, DD 7.89%, Trades 29
       1d: Sharpe 1.25, WR 66.67%, DD 20.86%, Trades 12

Forward Performance:
  Status: PAPER (Early Stage)
  Total Trades: 0
  Realized PnL: 0.0%
  Warning: <100 trades - metrics unreliable
```

### Bundle #3: Single_Symbol Partial_Timeframe Long_Only
```yaml
Bundle ID: bundle_single_symbol_partial_timeframe_long_only_20260227
Status: ACTIVE
Classification:
  Symbol Scope: single_symbol
  Timeframe Scope: partial_timeframe
  Direction Bias: long_only
Created: 2026-02-27

Strategies (2):
  1. crypto_multiframe_breakout_pulse_v1 (cursor)
     - Best Pair: ETH/USDT
     - Tier 1: PASS
     - Tier 2: 2/3 PASS (1h, 4h pass; 1d fail)
     - Backtest snapshot: Sharpe 2.28, WR 60.0%, DD 2.71%, Trades 15
  2. crypto_multiframe_regime_router_v1 (cursor)
     - Best Pair: ETH/USDT
     - Tier 1: PASS
     - Tier 2: 1/3 PASS (1h pass; 4h/1d fail)
     - Backtest snapshot: Sharpe 5.67, WR 76.92%, DD 1.66%, Trades 13

Forward Performance:
  Status: PAPER (Early Stage)
  Total Trades: 0
  Realized PnL: 0.0%
  Warning: <100 trades - metrics unreliable
```

---

### Bundle #4: Multi_Symbol Partial_Timeframe Both
```yaml
Bundle ID: bundle_multi_symbol_partial_timeframe_both_20260227
Status: ACTIVE
Classification:
  Symbol Scope: multi_symbol
  Timeframe Scope: partial_timeframe
  Direction Bias: both
Created: 2026-02-27
Origin: antigravity

Strategies (2):
  1. 053_HeikinAshiTrend (antigravity)
     - T1: PASS on ALL 3 pairs (BTC/ETH/SOL) ← only strategy to achieve this
     - T2: T2-PART (1h pass, 4h/1d fail on DD)
     - Direction: BOTH (long + short)
     - Backtest snapshots:
       BTCUSDT/1h: Sharpe 2.02, WR 67.6%, DD 11.9%, Trades 37, PF 1.69
       ETHUSDT/1h: Sharpe 1.72, WR 62.2%, DD 20.6%, Trades 45, PF 1.50
       SOLUSDT/1h: Sharpe 2.45, WR 69.4%, DD 16.7%, Trades 36, PF 1.83
     - Logic: Heikin-Ashi candles + trend persistence filter + ATR-based TP/SL
       
  2. 059_VWMomentum (antigravity)
     - T1: PASS on 2/3 pairs (BTC + SOL)
     - T2: T2-PART (1h pass)
     - Direction: BOTH
     - Backtest snapshots:
       BTCUSDT/1h: Sharpe 1.11, WR 48.0%, DD 4.4%, Trades 25, PF 1.40
       SOLUSDT/1h: Sharpe 2.05, WR 45.2%, DD 12.3%, Trades 31, PF 1.73
     - Logic: Volume-weighted momentum custom indicator. Complementary to HeikinAshi.

Bundle Summary:
  Avg Sharpe (passing pairs): 1.87
  Avg Win Rate: 58.5%
  Max Drawdown: 20.6%
  Combined Trades: 174
  Covers: BTC, ETH, SOL (all 3 majors)

Forward Performance:
  Status: PAPER (Early Stage)
  Total Trades: 0
  Realized PnL: 0.0%
  Warning: <100 trades - metrics unreliable
```

### Bundle #5: Single_Symbol Multi_Timeframe Both 🏆
```yaml
Bundle ID: bundle_single_symbol_multi_timeframe_both_20260227
Status: ACTIVE
Classification:
  Symbol Scope: single_symbol
  Timeframe Scope: multi_timeframe
  Direction Bias: both
Created: 2026-02-27
Origin: antigravity

Strategies (1):
  1. 052_EMARibbon (antigravity) ← 🏆 T2-FULL (only strategy in system)
     - Best Pair: SOLUSDT
     - T1: PASS on SOL (Sharpe 2.24, WR 66.7%)
     - T2: FULL PASS — ALL 3 timeframes on SOLUSDT
     - Direction: BOTH (long + short)
     - Backtest snapshots:
       SOLUSDT/1h: Sharpe 2.24, WR 66.7%, DD 5.6%, Trades 18, PF 2.15
       SOLUSDT/4h: Sharpe 2.26, WR 61.9%, DD 7.2%, Trades 21, PF 2.05
       SOLUSDT/1d: Sharpe 3.56, WR 73.3%, DD 17.4%, Trades 15, PF 2.52
     - Logic: 5-EMA ribbon (8/13/21/34/55) squeeze detection → expansion
       breakout with full alignment. Ultra-robust multi-timeframe strategy.

Bundle Summary:
  Avg Sharpe: 2.69 (across all 3 timeframes)
  Avg Win Rate: 67.3%
  Max Drawdown: 17.4%
  Combined Trades: 54
  Notes: HIGHEST priority bundle. Only T2-FULL in entire ecosystem.
         Differentiates from Bundle #2 (long_only) via both-direction support.

Forward Performance:
  Status: PAPER (Early Stage)
  Total Trades: 0
  Realized PnL: 0.0%
  Warning: <100 trades - metrics unreliable
```

### Bundle #6: Multi_Symbol Single_Timeframe Both
```yaml
Bundle ID: bundle_multi_symbol_single_timeframe_both_20260227
Status: ACTIVE
Classification:
  Symbol Scope: multi_symbol
  Timeframe Scope: single_timeframe
  Direction Bias: both
Created: 2026-02-27
Origin: antigravity

Strategies (2):
  1. 058_VolContraction (antigravity)
     - T1: PASS on 2/3 pairs (BTC + SOL)
     - T2: T2-PART (1h pass)
     - Direction: BOTH
     - Backtest snapshots:
       BTCUSDT/1h: Sharpe 1.70, WR 58.0%, DD 5.8%, Trades 50, PF 1.43
       SOLUSDT/1h: Sharpe 3.27, WR 57.8%, DD 9.7%, Trades 45, PF 2.11
     - Logic: ATR percentile contraction detection → expansion breakout
       with EMA trend alignment. Volatility regime strategy.
       
  2. 060_DualTFMomentum (antigravity)
     - T1: PASS on ETH
     - T2: T2-PART (1h + 4h pass = 2/3 timeframes)
     - Direction: BOTH
     - Backtest snapshots:
       ETHUSDT/1h: Sharpe 2.06, WR 50.0%, DD 10.0%, Trades 22, PF 1.94
       ETHUSDT/4h: Sharpe 1.20, WR 56.2%, DD 10.0%, Trades 16, PF 1.52
     - Logic: Simulated dual-timeframe within single feed using extended
       lookback EMAs + RSI. Covers ETH (complementary to VolContraction).

Bundle Summary:
  Avg Sharpe: 2.06
  Avg Win Rate: 55.5%
  Max Drawdown: 10.0%
  Combined Trades: 133
  Covers: BTC, ETH, SOL (via combined strategies)

Forward Performance:
  Status: PAPER (Early Stage)
  Total Trades: 0
  Realized PnL: 0.0%
  Warning: <100 trades - metrics unreliable
```

### Bundle #7: Single_Symbol Partial_Timeframe Both
```yaml
Bundle ID: bundle_single_symbol_partial_timeframe_both_20260227
Status: ACTIVE
Classification:
  Symbol Scope: single_symbol
  Timeframe Scope: partial_timeframe
  Direction Bias: both
Created: 2026-02-27
Origin: antigravity

Strategies (2):
  1. 051_Supertrend (antigravity)
     - Best Pair: SOLUSDT
     - T1: PASS on SOL (Sharpe 2.89, WR 68.0%)
     - T2: T2-PART (1h pass)
     - Direction: BOTH
     - Backtest snapshot:
       SOLUSDT/1h: Sharpe 2.89, WR 68.0%, DD 4.2%, Trades 25, PF 2.50
     - Logic: Dual-period ATR Supertrend (10/3 + 20/4) with trend agreement.
       Ultra-low drawdown specialist (4.2%).
       
  2. 055_OBVTrend (antigravity)
     - Best Pair: SOLUSDT
     - T1: PASS on SOL (Sharpe 1.94, WR 50.0%)
     - T2: T2-PART (1h pass)
     - Direction: BOTH
     - Backtest snapshot:
       SOLUSDT/1h: Sharpe 1.94, WR 50.0%, DD 12.6%, Trades 68, PF 1.41
     - Logic: OBV EMA crossover with trend confirmation.
       Higher trade count = faster statistical significance.
       Volume + price agreement strengthens signals.

Bundle Summary:
  Avg Sharpe: 2.42
  Avg Win Rate: 59.0%
  Max Drawdown: 12.6%
  Combined Trades: 93
  Both strategies focused on SOLUSDT - SOL specialist bundle.

Forward Performance:
  Status: PAPER (Early Stage)
  Total Trades: 0
  Realized PnL: 0.0%
  Warning: <100 trades - metrics unreliable
```

---

## Reserved Bundle Slots

The following bundle classifications are RESERVED but not yet created:

| Classification | Symbol Scope | Timeframe | Direction | Status |
|----------------|--------------|-----------|-----------|--------|
| Multi_Symbol Multi_Timeframe Both | multi_symbol | multi_timeframe | both | RESERVED |
| Broad Single_Timeframe Both | broad | single_timeframe | both | RESERVED |
| Multi_Symbol Single_Timeframe Short_Only | multi_symbol | single_timeframe | short_only | RESERVED |
| Multi_Symbol Partial_Timeframe Long_Only | multi_symbol | partial_timeframe | long_only | RESERVED |
| Single_Symbol Single_Timeframe Both | single_symbol | single_timeframe | both | RESERVED |

---

## Before Creating a New Bundle

**CHECKLIST:**
- [ ] Search this file for existing bundle with same classification
- [ ] Verify no bundle exists with identical (symbol × timeframe × direction) combo
- [ ] Query database: `SELECT * FROM bundle_babies WHERE symbol_scope='X' AND timeframe_scope='Y' AND direction_bias='Z'`
- [ ] If bundle exists with same classification, ADD strategies to existing bundle instead
- [ ] Only create new bundle if classification combination is unique

---

## Duplicate Detection Query

```sql
-- Run this before creating any bundle
SELECT bundle_id, name, strategy_names 
FROM bundle_babies 
WHERE symbol_scope = ? 
  AND timeframe_scope = ? 
  AND direction_bias = ?;
```

If returns 1+ rows → Bundle exists, add strategies to existing  
If returns 0 rows → Safe to create new bundle

---

## Classification Definitions

### Symbol Scope
| Value | Definition | Min Symbols |
|-------|------------|-------------|
| `single_symbol` | Works on exactly 1 symbol | 1 |
| `multi_symbol` | Passes on BTC/ETH/SOL (Tier 1) | 3 |
| `broad` | Passes on 4+ symbols | 4+ |

### Timeframe Scope
| Value | Definition | Pass Criteria |
|-------|------------|---------------|
| `single_timeframe` | Only passes 1 timeframe | 1 of 3 (1h/4h/1d) |
| `partial_timeframe` | Passes 2 timeframes | 2 of 3 |
| `multi_timeframe` | Passes all 3 (Tier 2) | 3 of 3 |

### Direction Bias
| Value | Definition |
|-------|------------|
| `long_only` | Only LONG signals |
| `short_only` | Only SHORT signals |
| `both` | LONG and SHORT signals |

---

## Bundle Naming Convention

```
bundle_{symbol_scope}_{timeframe_scope}_{direction_bias}_{YYYYMMDD}
```

Example: `bundle_single_symbol_single_timeframe_long_only_20260227`

---

## Database Schema Reference

```sql
CREATE TABLE bundle_babies (
    bundle_id TEXT PRIMARY KEY,
    name TEXT,
    symbol_scope TEXT,
    timeframe_scope TEXT,
    direction_bias TEXT,
    strategy_names TEXT,  -- JSON array
    best_symbol TEXT,
    best_timeframe TEXT,
    best_direction TEXT,
    backtest_sharpe REAL,
    backtest_win_rate REAL,
    backtest_max_dd REAL,
    backtest_trades INTEGER,
    backtest_total_return REAL,
    forward_status TEXT,
    forward_sharpe REAL,
    forward_win_rate REAL,
    forward_max_dd REAL,
    forward_trades INTEGER,
    forward_realized_pnl REAL,
    forward_unrealized_pnl REAL,
    max_concurrent_trades INTEGER,
    last_updated TEXT,
    created_at TEXT
);
```

---

## Unassigned Strategies (Pending Backtest)

### multitf_trendvol_confluence (web_ai)
```yaml
File: baby_strategies/multitf_trendvol_confluence.py
Origin: web_ai
Status: PENDING_BACKTEST
Direction: BOTH (long + short)
Created: 2026-02-27

Concept: 4h ADX trend filter + 1h breakout with volume surge confirmation.
  - Simulates 4h via 4x lookback on base feed
  - ADX > 25 (strong trend) required
  - Volume > 1.5x 20-period SMA required
  - Price must break recent 80-bar high/low
  - ATR filter: skip if ATR < 0.5% of price
  - TP = 2×ATR, SL = 1.5×ATR

Expected Bundle: Bundle #5 (single_symbol, multi_timeframe, both)
  - If T2-FULL: add to Bundle #5 alongside 052_EMARibbon
  - If T2-PART: create/join partial_timeframe bundle
  - If T1 only: single_timeframe bundle

Parameters:
  htf_mult: 4, adx_period: 14, adx_thresh: 25
  atr_period: 14, vol_sma_len: 20, vol_mult: 1.5
  tp_mul: 2.0, sl_mul: 1.5, breakout_lookback: 80
  min_atr_pct: 0.005
```

---

## Change Log

| Date | Action | Bundle ID |
|------|--------|-----------|
| 2026-02-27 | Created | bundle_single_symbol_single_timeframe_long_only_20260227 |
| 2026-02-27 | Created | bundle_single_symbol_multi_timeframe_long_only_20260227 |
| 2026-02-27 | Created | bundle_single_symbol_partial_timeframe_long_only_20260227 |
| 2026-02-27 | Created | bundle_multi_symbol_partial_timeframe_both_20260227 |
| 2026-02-27 | Created | bundle_single_symbol_multi_timeframe_both_20260227 |
| 2026-02-27 | Created | bundle_multi_symbol_single_timeframe_both_20260227 |
| 2026-02-27 | Created | bundle_single_symbol_partial_timeframe_both_20260227 |
| 2026-02-27 | Added unassigned | multitf_trendvol_confluence (pending backtest) |

---

*⚠️ CRITICAL: Always check this file before creating bundles to prevent duplicates!*
