# New Strategy Audit Integration
Generated: 2026-03-16T00:27:41.783797

## Files

### SQL Files (run in order)
1. `01_strategy_registry.sql` - Register new strategies in master catalog
2. `02_raw_picks_schema.sql` - Update at_raw_picks table schema
3. `03_signal_outcomes_schema.sql` - Update at_signal_outcomes schema
4. `04_symbol_performance.sql` - Create per-symbol performance tracking
5. `ALL_INTEGRATION_SQL_{timestamp}.sql` - All statements combined

### Dashboard Files
- `new_strategies_dashboard_{timestamp}.js` - Dashboard JavaScript integration
- `new_strategies_config_{timestamp}.json` - Strategy configuration

## New Strategies Added

| Strategy | Type | Target WR | Allocation |
|----------|------|-----------|------------|
| KC_SCALP_v1 | PROP_FIRM | 75% | 15% |
| VWAP_ELITE_v1 | PROP_FIRM | 70% | 12% |
| MTF_RSI_v1 | PROP_FIRM | 72% | 13% |
| FLASH_REV_v1 | GENERAL | 78% | 8% |
| FUNDING_PRO_v1 | GENERAL | 70% | 10% |
| HMA_TREND_v1 | GENERAL | 65% | 8% |
| BB_SQUEEZE_v1 | GENERAL | 68% | 8% |
| MULTI_FACTOR_v1 | GENERAL | 65% | 6% |
| keltner_hma_filter_enhanced | ALPHA_ENGINE | 70% | 12% |
| multi_sigma_volume_enhanced | ALPHA_ENGINE | 72% | 11% |
| hurst_rsi_extreme_enhanced | ALPHA_ENGINE | 75% | 13% |
| VWAP_RSI_INSTITUTIONAL | BABY_STRATEGY | 68% | 10% |
| LIQUIDATION_CASCADE_CONTRARIAN | BABY_STRATEGY | 62% | 8% |
| REGIME_SENTINEL_COMPOSITE | BABY_STRATEGY | 75% | 12% |
| RSI_PAIRS_ARBITRAGE | BABY_STRATEGY | 74% | 8% |

## Integration Steps

1. Run SQL files in order against ejaguiar1_stocks database
2. Copy dashboard JS to audit_dashboard/scripts/
3. Include JS in audit_dashboard/index.html
4. Deploy updated dashboard
5. Start forward testing for approved strategies

## Database Connection

```python
import mysql.connector

conn = mysql.connector.connect(
    host='mysql.50webs.com',
    user='ejaguiar1_stocks',
    password='your_password',
    database='ejaguiar1_stocks'
)
```
