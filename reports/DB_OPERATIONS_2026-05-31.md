# DB Operations Log — 2026-05-31

## Databases
| Database | User | Host | Purpose |
|----------|------|------|---------|
| ejaguiar1_stocks | ejaguiar1_stocks | mysql.50webs.com | Trading picks |
| ejaguiar1_backups | ejaguiar1_backups | mysql.50webs.com | Backup storage |

## Operations

### READ — Per-strategy performance
- Table: trading_picks, GROUP BY category/source_system/strategy/direction
- Result: 35 positive-EV combos identified

### READ — Monte Carlo validation  
- Table: trading_picks, SELECT pnl_pct for 12 top candidates
- Method: 10K bootstrap sims per candidate

### WRITE — Backup snapshot
- Created: trading_picks_snapshot_20260531_2156 (42,665 rows)
- Method: CREATE TABLE AS SELECT * FROM trading_picks

### Schema
- Status values: TIME_EXIT (26,026), OPEN (4,444), TP_HIT (3,613), ACTIVE (3,599), LOST (2,854), SL_HIT (1,508), EXPIRED (621)
- Cross-DB access restricted between ejaguiar1_stocks and ejaguiar1_backups
