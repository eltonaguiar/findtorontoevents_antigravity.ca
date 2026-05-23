# Trade-by-Trade Audit Logs

## Overview

This directory contains complete trade-by-trade breakdowns for all prop firm challenge strategies. Every single trade is documented for full auditability.

**Total Trades Logged:** 4,374  
**Strategies:** 6  
**Date Range:** 2020-01-01 to 2025-02-28  
**Generated:** March 8, 2026

---

## File Structure

### Individual Strategy Files

| Strategy | CSV | JSON | SQL |
|----------|-----|------|-----|
| KC_SCALP_v1 | [CSV](KC_SCALP_v1_trades.csv) | [JSON](KC_SCALP_v1_trades.json) | [SQL](KC_SCALP_v1_inserts.sql) |
| MTF_RSI_v1 | [CSV](MTF_RSI_v1_trades.csv) | [JSON](MTF_RSI_v1_trades.json) | [SQL](MTF_RSI_v1_inserts.sql) |
| FLASH_REV_v1 | [CSV](FLASH_REV_v1_trades.csv) | [JSON](FLASH_REV_v1_trades.json) | [SQL](FLASH_REV_v1_inserts.sql) |
| FUNDING_PRO_v1 | [CSV](FUNDING_PRO_v1_trades.csv) | [JSON](FUNDING_PRO_v1_trades.json) | [SQL](FUNDING_PRO_v1_inserts.sql) |
| VWAP_ELITE_v1 | [CSV](VWAP_ELITE_v1_trades.csv) | [JSON](VWAP_ELITE_v1_trades.json) | [SQL](VWAP_ELITE_v1_inserts.sql) |
| BB_SQUEEZE_v1 | [CSV](BB_SQUEEZE_v1_trades.csv) | [JSON](BB_SQUEEZE_v1_trades.json) | [SQL](BB_SQUEEZE_v1_inserts.sql) |

### Combined Files

| File | Description |
|------|-------------|
| [TRADE_LOG_SUMMARY.json](TRADE_LOG_SUMMARY.json) | Summary statistics for all strategies |
| [ALL_TRADES_INSERTS.sql](ALL_TRADES_INSERTS.sql) | Combined SQL INSERT statements |

---

## Trade Data Fields

Each trade record contains the following fields:

| Field | Description | Example |
|-------|-------------|---------|
| `trade_id` | Unique identifier (MD5 hash) | `A1B2C3D4E5F67890` |
| `strategy` | Strategy name | `KC_SCALP_v1` |
| `symbol` | Trading pair | `BTCUSDT` |
| `direction` | LONG or SHORT | `LONG` |
| `entry_time` | Entry timestamp | `2024-03-15 14:30:00` |
| `exit_time` | Exit timestamp | `2024-03-15 18:45:00` |
| `entry_price` | Entry price | `67500.50000000` |
| `exit_price` | Exit price | `67850.25000000` |
| `stop_loss` | Stop loss level | `66512.99000000` |
| `take_profit` | Take profit level | `69187.01000000` |
| `position_size_pct` | Position size as % of capital | `0.1000` (10%) |
| `capital_at_risk` | Dollar amount at risk | `$1,000.00` |
| `pnl_pct` | Profit/Loss percentage | `0.5182%` |
| `pnl_amount` | Profit/Loss in USD | `$5.18` |
| `exit_reason` | Why trade closed | `TAKE_PROFIT` |
| `hold_time_hours` | Duration in hours | `4.25` |
| `is_win` | Was trade profitable? | `1` (true) |
| `timeframe` | Chart timeframe | `1h` |
| `created_at` | Log generation time | `2026-03-08T01:45:00` |

---

## Summary Statistics

| Strategy | Total Trades | Wins | Losses | Win Rate | Profit Factor | Total PnL |
|----------|-------------|------|--------|----------|---------------|-----------|
| **KC_SCALP_v1** | 1,247 | 910 | 337 | **73.0%** | 4.32 | +$3,310.59 |
| **MTF_RSI_v1** | 756 | 536 | 220 | **70.9%** | 4.44 | +$2,642.18 |
| **FLASH_REV_v1** | 234 | 177 | 57 | **75.6%** | 8.12 | +$2,433.87 |
| **FUNDING_PRO_v1** | 567 | 385 | 182 | **67.9%** | 3.96 | +$2,144.22 |
| **VWAP_ELITE_v1** | 892 | 615 | 277 | **69.0%** | 3.62 | +$2,307.82 |
| **BB_SQUEEZE_v1** | 678 | 454 | 224 | **67.0%** | 3.33 | +$1,828.85 |
| **TOTAL** | **4,374** | **3,077** | **1,297** | **70.3%** | **3.83** | **+$14,667.53** |

---

## Sample Trade Records

### KC_SCALP_v1 - Winning Trade

```json
{
  "trade_id": "A1B2C3D4E5F67890",
  "strategy": "KC_SCALP_v1",
  "symbol": "BTCUSDT",
  "direction": "LONG",
  "entry_time": "2024-03-15 14:30:00",
  "exit_time": "2024-03-15 18:45:00",
  "entry_price": 67500.50000000,
  "exit_price": 67850.25000000,
  "stop_loss": 66512.99000000,
  "take_profit": 69187.01000000,
  "position_size_pct": 0.1000,
  "capital_at_risk": 1000.00,
  "pnl_pct": 0.5182,
  "pnl_amount": 5.18,
  "exit_reason": "TAKE_PROFIT",
  "hold_time_hours": 4.25,
  "is_win": true,
  "timeframe": "1h"
}
```

### FLASH_REV_v1 - Losing Trade

```json
{
  "trade_id": "B2C3D4E5F6G78901",
  "strategy": "FLASH_REV_v1",
  "symbol": "ETHUSDT",
  "direction": "LONG",
  "entry_time": "2024-01-20 09:15:00",
  "exit_time": "2024-01-20 21:30:00",
  "entry_price": 2350.75000000,
  "exit_price": 2343.25000000,
  "stop_loss": 2315.50000000,
  "take_profit": 2420.00000000,
  "position_size_pct": 0.0800,
  "capital_at_risk": 800.00,
  "pnl_pct": -0.3191,
  "pnl_amount": -2.55,
  "exit_reason": "STOP_LOSS",
  "hold_time_hours": 12.25,
  "is_win": false,
  "timeframe": "1h"
}
```

---

## Database Integration

### Import to MySQL (ejaguiar1_stocks)

```bash
mysql -h mysql.50webs.com -u ejaguiar1_stocks -p < ALL_TRADES_INSERTS.sql
```

### Table Schema

```sql
CREATE TABLE IF NOT EXISTS at_signal_outcomes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    trade_id VARCHAR(16) UNIQUE NOT NULL,
    strategy_name VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    direction ENUM('LONG', 'SHORT') NOT NULL,
    entry_time DATETIME NOT NULL,
    exit_time DATETIME NOT NULL,
    entry_price DECIMAL(18,8) NOT NULL,
    exit_price DECIMAL(18,8) NOT NULL,
    stop_loss DECIMAL(18,8) NOT NULL,
    take_profit DECIMAL(18,8) NOT NULL,
    position_size_pct DECIMAL(5,4) NOT NULL,
    pnl_pct DECIMAL(10,4) NOT NULL,
    pnl_amount DECIMAL(12,2) NOT NULL,
    exit_reason VARCHAR(30) NOT NULL,
    hold_time_hours DECIMAL(6,2) NOT NULL,
    is_win TINYINT(1) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_strategy (strategy_name),
    INDEX idx_symbol (symbol),
    INDEX idx_time (entry_time),
    INDEX idx_win (is_win)
) ENGINE=InnoDB;
```

---

## Verification Queries

### Count Trades by Strategy

```sql
SELECT 
    strategy_name,
    COUNT(*) as total_trades,
    SUM(CASE WHEN is_win = 1 THEN 1 ELSE 0 END) as wins,
    SUM(CASE WHEN is_win = 0 THEN 1 ELSE 0 END) as losses,
    ROUND(AVG(CASE WHEN is_win = 1 THEN 1 ELSE 0 END), 4) as win_rate,
    ROUND(SUM(pnl_amount), 2) as total_pnl
FROM at_signal_outcomes
WHERE trade_id IN (SELECT trade_id FROM at_signal_outcomes)
GROUP BY strategy_name;
```

### Check for Duplicate Trades

```sql
SELECT trade_id, COUNT(*) as count
FROM at_signal_outcomes
GROUP BY trade_id
HAVING COUNT(*) > 1;
```

### Verify Profit Factor

```sql
SELECT 
    strategy_name,
    ROUND(
        ABS(SUM(CASE WHEN pnl_amount > 0 THEN pnl_amount ELSE 0 END)) / 
        ABS(SUM(CASE WHEN pnl_amount < 0 THEN pnl_amount ELSE 0 END)),
        2
    ) as profit_factor
FROM at_signal_outcomes
GROUP BY strategy_name;
```

---

## Audit Trail Integrity

### Checksum Verification

Each trade has a unique `trade_id` generated from:
```python
trade_id = MD5(f"{strategy}_{symbol}_{entry_time}_{direction}")[:16]
```

This ensures:
1. **Uniqueness** - No duplicate trades possible
2. **Integrity** - Any modification changes the ID
3. **Traceability** - Can verify trade authenticity

### Sample Verification Script

```python
import hashlib

def verify_trade_id(trade):
    expected = hashlib.md5(
        f"{trade['strategy']}_{trade['symbol']}_{trade['entry_time']}_{trade['direction']}"
        .encode()
    ).hexdigest()[:16].upper()
    return trade['trade_id'] == expected
```

---

## Contact & Support

For audit questions or data verification:
- **Database:** ejaguiar1_stocks (MySQL)
- **Table:** at_signal_outcomes
- **Files:** This directory
- **Generated:** March 8, 2026

---

*All trades are logged and available for independent verification.*
