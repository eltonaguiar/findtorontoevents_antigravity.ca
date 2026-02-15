# Rapid Validation Engine 🚀
## CLAUDECODE_Feb152026

**Compress 3 months of strategy testing into 2-3 weeks**

---

## Overview

The Rapid Validation Engine is a high-frequency signal testing system that:
- Generates **100+ signals per day** across multiple strategies
- Resolves signals every **15 minutes** (vs traditional 24hr)
- Tests on **5min/15min/1hr candles** for quick validation
- **Auto-promotes winners** and **eliminates losers** based on statistical thresholds
- Provides **real-time dashboard** with live performance metrics

### Key Innovation
Instead of waiting 3 months for daily signals to resolve, we:
1. Test strategies on **5-minute candles** (288 candles/day vs 1)
2. Check outcomes **every 15 minutes** (96x per day vs 1x)
3. Run **multiple exit strategies** simultaneously (scalp, swing, position)
4. **Eliminate failures faster** (72 hours vs 3 months)

**Result: 6 months → 3 weeks (8x compression)**

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ RAPID VALIDATION ENGINE                                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────┐      ┌──────────────────┐            │
│  │ Signal Generator │─────>│  Fast Validator  │            │
│  │  (Every Hour)    │      │  (Every 15min)   │            │
│  └──────────────────┘      └──────────────────┘            │
│           │                          │                       │
│           v                          v                       │
│  ┌──────────────────────────────────────────┐               │
│  │       MySQL Database                      │               │
│  │  - rapid_signals                          │               │
│  │  - rapid_outcomes                         │               │
│  │  - rapid_strategy_stats                   │               │
│  └──────────────────────────────────────────┘               │
│           │                                                   │
│           v                                                   │
│  ┌──────────────────┐      ┌──────────────────┐            │
│  │ Strategy Ranker  │─────>│  Live Dashboard  │            │
│  │  (Every 15min)   │      │  (Auto-refresh)  │            │
│  └──────────────────┘      └──────────────────┘            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Components

### 1. **Rapid Signal Generator** (`rapid_signal_generator.py`)
- Generates signals on 5-minute candles
- Tests 6 strategies across 12 crypto pairs
- Outputs TP/SL for 3 exit strategies (scalp, swing, position)
- **Run frequency**: Every hour (GitHub Actions)

**Strategies tested:**
- RSI Momentum (5m)
- MACD Crossover (5m)
- Supertrend (5m)
- Bollinger Band Squeeze (5m)
- Volume Momentum (5m)
- Mean Reversion (RSI < 40) (5m)

**Pairs tested:**
- BTC/USDT, ETH/USDT, SOL/USDT, BNB/USDT
- DOGE/USDT, PEPE/USDT, WIF/USDT, BONK/USDT
- AVAX/USDT, MATIC/USDT, LINK/USDT, UNI/USDT

### 2. **Fast Validator** (`fast_validator_CLAUDECODE_Feb152026.py`)
- Checks signals every 15 minutes
- Resolves based on TP/SL hits or time expiry
- Tracks high/low prices during hold period
- **Run frequency**: Every 15 minutes (GitHub Actions)

**Exit strategies:**
- **Scalp**: 0.5% TP / 0.3% SL / 15min time limit
- **Swing**: 2.0% TP / 1.0% SL / 4hr time limit
- **Position**: 5.0% TP / 2.5% SL / 24hr time limit

### 3. **Strategy Ranker** (`strategy_ranker_CLAUDECODE_Feb152026.py`)
- Calculates win rate, profit factor, Sharpe ratio
- Auto-promotes winners (60%+ WR, 1.5+ PF, 1.2+ Sharpe)
- Auto-eliminates losers (< 40% WR or < 0.8 PF)
- **Run frequency**: Every 15 minutes (GitHub Actions)

**Promotion criteria (100+ trades required):**
```python
{
    'min_win_rate': 60.0,        # 60%+ wins
    'min_profit_factor': 1.5,    # $1.50 profit per $1 loss
    'min_sharpe_ratio': 1.2,     # Risk-adjusted returns
    'max_drawdown': -15.0        # Max -15% drawdown
}
```

**Elimination criteria (50+ trades):**
```python
{
    'max_win_rate': 40.0,        # Below 40% = eliminate
    'max_profit_factor': 0.8,    # Losing money = eliminate
    'max_consecutive_losses': 15 # 15 losses in row = eliminate
}
```

### 4. **Live Dashboard** (`dashboard_CLAUDECODE_Feb152026.html`)
- Real-time metrics (auto-refresh every 15min)
- Leaderboard with promoted/testing/eliminated sections
- Visual performance indicators
- **Access**: `https://findtorontoevents.ca/rapid-validation/dashboard_CLAUDECODE_Feb152026.html`

---

## Quick Start

### Local Testing (Immediate)

1. **Generate signals:**
```bash
cd rapid_validation
python rapid_signal_generator.py --mode live --timeframe 5m
```

2. **Validate signals:**
```bash
python fast_validator_CLAUDECODE_Feb152026.py
```

3. **View rankings:**
```bash
python strategy_ranker_CLAUDECODE_Feb152026.py
```

4. **Open dashboard:**
```bash
# Open in browser:
file:///path/to/rapid_validation/dashboard_CLAUDECODE_Feb152026.html
```

### Automated Testing (Production)

GitHub Actions runs automatically:
- **Signal generation**: Every hour (0 * * * *)
- **Validation**: Every 15 minutes (*/15 * * * *)
- **Ranking**: Every 15 minutes (*/15 * * * *)

No manual intervention required!

---

## Database Schema

### `rapid_signals`
```sql
CREATE TABLE rapid_signals (
    id INT AUTO_INCREMENT PRIMARY KEY,
    signal_id VARCHAR(100) UNIQUE,
    strategy VARCHAR(100),
    pair VARCHAR(20),
    timeframe VARCHAR(10),
    signal_type VARCHAR(10),  -- 'long' or 'short'
    entry_price DECIMAL(20,8),
    tp_scalp DECIMAL(20,8),
    sl_scalp DECIMAL(20,8),
    tp_swing DECIMAL(20,8),
    sl_swing DECIMAL(20,8),
    tp_position DECIMAL(20,8),
    sl_position DECIMAL(20,8),
    confidence INT,
    indicators JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'ACTIVE'
);
```

### `rapid_outcomes`
```sql
CREATE TABLE rapid_outcomes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    signal_id VARCHAR(100),
    exit_strategy VARCHAR(20),  -- 'scalp', 'swing', 'position'
    outcome VARCHAR(20),         -- 'WIN', 'LOSS', 'EXPIRED'
    exit_price DECIMAL(20,8),
    pnl_pct DECIMAL(10,4),
    pnl_usd DECIMAL(10,2),
    duration_minutes INT,
    highest_price DECIMAL(20,8),
    lowest_price DECIMAL(20,8),
    resolved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (signal_id) REFERENCES rapid_signals(signal_id)
);
```

### `rapid_strategy_stats`
```sql
CREATE TABLE rapid_strategy_stats (
    id INT AUTO_INCREMENT PRIMARY KEY,
    strategy VARCHAR(100),
    timeframe VARCHAR(10),
    exit_strategy VARCHAR(20),
    total_trades INT DEFAULT 0,
    wins INT DEFAULT 0,
    losses INT DEFAULT 0,
    expired INT DEFAULT 0,
    win_rate DECIMAL(5,2),
    profit_factor DECIMAL(10,2),
    sharpe_ratio DECIMAL(10,2),
    total_pnl_pct DECIMAL(10,2),
    total_pnl_usd DECIMAL(10,2),
    avg_pnl_pct DECIMAL(10,4),
    max_drawdown_pct DECIMAL(10,2),
    consecutive_losses INT DEFAULT 0,
    max_consecutive_losses INT DEFAULT 0,
    avg_duration_minutes DECIMAL(10,2),
    status VARCHAR(20) DEFAULT 'TESTING',
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_strategy_tf_exit (strategy, timeframe, exit_strategy)
);
```

---

## Expected Timeline

### Week 1: Data Collection
- **Day 1-2**: System setup, first signals generated
- **Day 3-7**: Accumulate 500-1000 signals
- **Expected**: Some strategies reach 50 trades (elimination threshold)

### Week 2: Fast Elimination
- **Day 8-10**: Eliminate strategies with < 40% WR
- **Day 11-14**: Top strategies reach 100+ trades
- **Expected**: 2-3 strategies approach promotion threshold

### Week 3: Validation
- **Day 15-17**: Promote strategies with 60%+ WR
- **Day 18-21**: Paper trade promoted strategies live
- **Expected**: Deploy 1-3 proven strategies to real money

---

## Success Metrics

### Quantitative Goals
- [ ] Generate 1000+ signals in Week 1
- [ ] Identify 3-5 strategies with 100+ trades by Week 2
- [ ] Promote 1-3 strategies with 60%+ WR by Week 3
- [ ] Eliminate 50%+ of failing strategies by Week 2

### Qualitative Goals
- [ ] Faster confidence in strategy performance (weeks vs months)
- [ ] Lower risk (paper trading with rapid validation)
- [ ] Data-driven decisions (statistical significance faster)
- [ ] Parallel testing (multiple strategies simultaneously)

---

## Comparison: Traditional vs Rapid

| Metric | Traditional | Rapid Validation | Speedup |
|--------|-------------|------------------|---------|
| Signal frequency | 1/day | 100+/day | 100x |
| Resolution check | 24hr | 15min | 96x |
| Time to 100 trades | 100 days | 1-7 days | 14-100x |
| Elimination speed | 3 months | 3-7 days | 12-40x |
| Promotion speed | 6 months | 2-3 weeks | 8-12x |
| **Total time to proven strategy** | **6 months** | **3 weeks** | **8x faster** |

---

## Troubleshooting

### "No signals generated"
- Check if exchange API is accessible (`ccxt`)
- Verify pairs are trading on Binance
- Check cache directory permissions

### "Database connection failed"
- Verify MySQL credentials in `.env`
- Check database exists: `SHOW DATABASES LIKE 'rapid_validation'`
- Run `fast_validator_CLAUDECODE_Feb152026.py` to auto-create schema

### "Dashboard shows 0 strategies"
- Run `strategy_ranker_CLAUDECODE_Feb152026.py` to generate `rankings_CLAUDECODE_Feb152026.json`
- Check file exists in `rapid_validation/` directory
- Verify JSON is valid: `cat rankings_CLAUDECODE_Feb152026.json | jq`

---

## Next Steps

1. **Monitor for 1 week** - Let system collect data
2. **Review promoted strategies** - Check if any reach 60%+ WR
3. **Paper trade winners** - Test on live market with fake money
4. **Deploy to real money** - Start small ($100-500) with proven strategies
5. **Scale up** - Increase position size as confidence grows

---

## Support

Created by: Claude Code (Anthropic)
Date: February 15, 2026
Tag: CLAUDECODE_Feb152026

For issues or questions, check:
- `rapid_validation/rankings_CLAUDECODE_Feb152026.json` for latest results
- GitHub Actions workflow logs
- MySQL database directly: `SELECT * FROM rapid_strategy_stats ORDER BY sharpe_ratio DESC`
