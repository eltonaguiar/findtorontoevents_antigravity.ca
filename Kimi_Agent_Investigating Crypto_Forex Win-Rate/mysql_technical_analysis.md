# TECHNICAL ANALYSIS: MySQL Database Data Integrity

This document provides specific SQL queries and technical details for investigating the ejaguiar1_stocks database.

---

## 1. RECOMMENDED SQL QUERIES FOR DATABASE INVESTIGATION

### 1.1 Check row counts in all tables
```sql
SELECT 
    'at_audit_events' as table_name, COUNT(*) as row_count FROM at_audit_events
UNION ALL
SELECT 'at_discord_notifications', COUNT(*) FROM at_discord_notifications
UNION ALL
SELECT 'at_discord_gate_log', COUNT(*) FROM at_discord_gate_log
UNION ALL
SELECT 'at_filter_log', COUNT(*) FROM at_filter_log
UNION ALL
SELECT 'at_local_picks', COUNT(*) FROM at_local_picks
UNION ALL
SELECT 'at_signal_outcomes', COUNT(*) FROM at_signal_outcomes
UNION ALL
SELECT 'strategy_registry', COUNT(*) FROM strategy_registry;
```

### 1.2 Check at_signal_outcomes for missing outcome data
```sql
SELECT 
    COUNT(*) as total_records,
    SUM(CASE WHEN outcome IS NULL OR outcome = '' THEN 1 ELSE 0 END) as missing_outcome,
    SUM(CASE WHEN pnl_percent IS NULL THEN 1 ELSE 0 END) as missing_pnl,
    SUM(CASE WHEN exit_price IS NULL THEN 1 ELSE 0 END) as missing_exit_price
FROM at_signal_outcomes;
```

### 1.3 Check copy trader related records
```sql
SELECT 
    strategy_name,
    COUNT(*) as total_picks,
    SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END) as wins,
    SUM(CASE WHEN outcome = 'LOSS' THEN 1 ELSE 0 END) as losses,
    AVG(pnl_percent) as avg_pnl
FROM at_signal_outcomes
WHERE strategy_name LIKE '%copy%' OR strategy_name LIKE '%trader%'
GROUP BY strategy_name;
```

### 1.4 Check for recent records (last 7 days)
```sql
SELECT 
    DATE(created_at) as date,
    COUNT(*) as records
FROM at_signal_outcomes
WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
GROUP BY DATE(created_at)
ORDER BY date DESC;
```

### 1.5 Check at_local_picks for copy trader data
```sql
SELECT 
    source_system,
    COUNT(*) as pick_count,
    MAX(created_at) as last_update
FROM at_local_picks
GROUP BY source_system
ORDER BY pick_count DESC;
```

### 1.6 Check discord notifications for copy trader alerts
```sql
SELECT 
    notification_type,
    COUNT(*) as count,
    MAX(sent_at) as last_sent
FROM at_discord_notifications
WHERE message LIKE '%copy%' OR message LIKE '%trader%'
GROUP BY notification_type;
```

### 1.7 Check strategy_registry for copy trader entries
```sql
SELECT 
    strategy_name,
    status,
    win_rate,
    total_trades,
    last_updated
FROM strategy_registry
WHERE strategy_name LIKE '%copy%' OR strategy_name LIKE '%trader%'
ORDER BY last_updated DESC;
```

---

## 2. TABLE SCHEMA EXPECTATIONS

### at_signal_outcomes
| Column | Type | Description |
|--------|------|-------------|
| id | INT (PK, AI) | Primary key |
| pick_id | VARCHAR | Unique identifier for the pick |
| symbol | VARCHAR | Trading pair (e.g., BTCUSDT) |
| strategy_name | VARCHAR | Name of the strategy |
| entry_price | DECIMAL | Entry price |
| exit_price | DECIMAL | Exit price (NULL if still open) |
| take_profit | DECIMAL | Target price |
| stop_loss | DECIMAL | Stop loss price |
| outcome | ENUM | 'WIN', 'LOSS', 'OPEN', 'CANCELLED' |
| pnl_amount | DECIMAL | P&L in quote currency |
| pnl_percent | DECIMAL | P&L percentage |
| exit_reason | ENUM | 'TP_HIT', 'SL_HIT', 'MANUAL', 'TIMEOUT' |
| opened_at | TIMESTAMP | When pick was created |
| closed_at | TIMESTAMP | When pick was closed |
| created_at | TIMESTAMP | Record creation time |
| updated_at | TIMESTAMP | Record update time |

### at_local_picks
| Column | Type | Description |
|--------|------|-------------|
| id | INT (PK, AI) | Primary key |
| pick_id | VARCHAR | Unique identifier |
| source_system | VARCHAR | e.g., 'copy_trader_intel' |
| symbol | VARCHAR | Trading pair |
| direction | ENUM | 'BUY', 'SELL' |
| entry_price | DECIMAL | Entry price |
| take_profit | DECIMAL | Target price |
| stop_loss | DECIMAL | Stop loss price |
| confidence | DECIMAL | Confidence score |
| score | INT | Pick score |
| raw_data | JSON | Full pick data as JSON |
| created_at | TIMESTAMP | Record creation time |
| updated_at | TIMESTAMP | Record update time |

---

## 3. DATA INTEGRITY CHECK QUERIES

### 3.1 Find picks with entry_price but no outcome (orphaned picks)
```sql
SELECT 
    COUNT(*) as orphaned_picks
FROM at_signal_outcomes
WHERE entry_price IS NOT NULL 
  AND (outcome IS NULL OR outcome = 'OPEN')
  AND opened_at < DATE_SUB(NOW(), INTERVAL 7 DAY);
```

### 3.2 Find duplicate pick_ids
```sql
SELECT 
    pick_id,
    COUNT(*) as duplicate_count
FROM at_signal_outcomes
GROUP BY pick_id
HAVING COUNT(*) > 1;
```

### 3.3 Find records with invalid data
```sql
SELECT 
    'negative_pnl_wins' as issue,
    COUNT(*) as count
FROM at_signal_outcomes
WHERE outcome = 'WIN' AND pnl_percent < 0
UNION ALL
SELECT 
    'positive_pnl_losses',
    COUNT(*)
FROM at_signal_outcomes
WHERE outcome = 'LOSS' AND pnl_percent > 0;
```

### 3.4 Check for gaps in copy trader data
```sql
SELECT 
    'copy_trader_picks_in_local' as check_type,
    COUNT(*) as count
FROM at_local_picks
WHERE source_system LIKE '%copy%'
UNION ALL
SELECT 
    'copy_trader_outcomes_recorded',
    COUNT(*)
FROM at_signal_outcomes
WHERE strategy_name LIKE '%copy%';
```

---

## 4. COPY TRADER SPECIFIC INVESTIGATION

### 4.1 Find all copy trader related records
```sql
SELECT DISTINCT
    strategy_name
FROM at_signal_outcomes
WHERE strategy_name LIKE '%copy%' 
   OR strategy_name LIKE '%trader%'
   OR strategy_name LIKE '%hl_%'
   OR strategy_name LIKE '%NMTD%'
   OR strategy_name LIKE '%whale%'
ORDER BY strategy_name;
```

### 4.2 Check if NMTD_25M trader outcomes are recorded
```sql
SELECT 
    symbol,
    entry_price,
    exit_price,
    outcome,
    pnl_percent,
    exit_reason,
    closed_at
FROM at_signal_outcomes
WHERE strategy_name = 'copy_hl_NMTD_25M'
ORDER BY closed_at DESC;
```

### 4.3 Check binance_smart_money outcomes
```sql
SELECT 
    COUNT(*) as total_picks,
    SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END) as wins,
    SUM(CASE WHEN outcome = 'LOSS' THEN 1 ELSE 0 END) as losses,
    AVG(pnl_percent) as avg_pnl
FROM at_signal_outcomes
WHERE strategy_name = 'binance_smart_money';
```

### 4.4 Find copy trader picks with TP/SL but no outcome
```sql
SELECT 
    pick_id,
    symbol,
    strategy_name,
    entry_price,
    take_profit,
    stop_loss,
    opened_at,
    DATEDIFF(NOW(), opened_at) as days_open
FROM at_signal_outcomes
WHERE (strategy_name LIKE '%copy%' OR strategy_name LIKE '%trader%')
  AND entry_price IS NOT NULL
  AND take_profit IS NOT NULL
  AND stop_loss IS NOT NULL
  AND (outcome IS NULL OR outcome = 'OPEN')
  AND opened_at < DATE_SUB(NOW(), INTERVAL 3 DAY);
```

---

## 5. RECOMMENDED FIXES (SQL SCRIPTS)

### 5.1 Create index for faster copy trader queries
```sql
CREATE INDEX idx_strategy_name ON at_signal_outcomes(strategy_name);
CREATE INDEX idx_source_system ON at_local_picks(source_system);
CREATE INDEX idx_pick_id ON at_signal_outcomes(pick_id);
```

### 5.2 Add outcome resolution tracking table
```sql
CREATE TABLE IF NOT EXISTS at_outcome_resolution_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pick_id VARCHAR(255) NOT NULL,
    symbol VARCHAR(50),
    strategy_name VARCHAR(255),
    resolution_type ENUM('TP_HIT', 'SL_HIT', 'MANUAL', 'TIMEOUT'),
    resolved_price DECIMAL(18,8),
    expected_tp DECIMAL(18,8),
    expected_sl DECIMAL(18,8),
    resolved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_pick_id (pick_id),
    INDEX idx_strategy (strategy_name)
);
```

### 5.3 Add data sync tracking
```sql
CREATE TABLE IF NOT EXISTS at_sync_status (
    id INT AUTO_INCREMENT PRIMARY KEY,
    table_name VARCHAR(100),
    last_sync_at TIMESTAMP,
    records_synced INT,
    sync_type ENUM('full', 'incremental'),
    status ENUM('success', 'failed', 'in_progress')
);
```

---

## 6. DATA RECOVERY RECOMMENDATIONS

### STEP 1: Export current state
```bash
mysqldump -h mysql.50webs.com -u ejaguiar1 -p ejaguiar1_stocks > backup_$(date +%Y%m%d).sql
```

### STEP 2: Identify missing data from dashboard_payload.json
- Parse dashboard_payload.json to extract closed pick outcomes
- Compare with at_signal_outcomes to find gaps

### STEP 3: Backfill missing outcomes
Create script to:
1. Read dashboard_payload.json
2. Extract pick_id, symbol, outcome, pnl_percent, exit_reason
3. INSERT or UPDATE at_signal_outcomes table

### STEP 4: Set up real-time sync
Modify audit_trail/mysql_client.py to:
1. Write outcomes immediately when resolved
2. Update at_signal_outcomes in real-time
3. Log sync status to at_sync_status

### STEP 5: Add outcome resolver for copy traders
Create workflow similar to claude_gainer_st resolution:
1. Read copy_trader_intel/data/active_picks.json
2. Check current price vs entry/TP/SL
3. When TP or SL hit, record outcome
4. Write to at_signal_outcomes
