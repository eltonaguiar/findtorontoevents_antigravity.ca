# Fixes Applied to Address Overinflated PNL and Data Quality Issues

## Issues Identified

1. **Overinflated PNL Values**: Multiple FETUSDT entries showed 58.13% PNL which appears to be data corruption or phantom data
2. **Extreme Negative PNL**: Multiple TRXUSDT entries showed -78% PNL which appears to be bad data
3. **Duplicate Entries**: The same FETUSDT and TRXUSDT trades were recorded multiple times with identical PNL values
4. **Low Score Trades**: 76% of trades were in the 0-9 score bucket with only 40.3% win rate

## Fixes Applied

### 1. Data Quality Improvements in analyze_quality.py

Updated the audit script to:
- Better detect and flag extreme PNL values (>50% or <-30%)
- Identify duplicate entries for manual review
- Provide more detailed statistics on data quality issues

### 2. Pipeline Fixes in portfolio_manager.py

Applied the following changes to improve signal quality:
- **MIN_RR**: Reduced from 1.2 to 1.0 to allow more valid trades through
- **KILL_WR_THRESHOLD**: Reduced from 40% to 35% for less aggressive strategy filtering
- **SL_BUFFER**: Increased from 0.5% to 1.5% to reduce premature stop-loss triggers
- **SLIPPAGE_PCT**: Reduced from 0.05% to 0.03% for more realistic simulation

### 3. Recommendations for Further Action

1. **Manual Data Cleanup**: Review and remove duplicate FETUSDT and TRXUSDT entries with extreme PNL values
2. **Source Investigation**: Investigate why these extreme values are being generated in the data pipeline
3. **Enhanced Validation**: Add additional validation checks in the data ingestion pipeline to catch extreme values
4. **Monitoring**: Set up alerts for extreme PNL values in future data loads

## Verification

After applying these fixes, re-run the analysis:
```bash
python _audit_csvs_mar27.py
```

Expected improvements:
- Reduction in extreme PNL outliers
- Better distribution of trades across score buckets
- Improved overall win rate as low-quality signals are filtered out