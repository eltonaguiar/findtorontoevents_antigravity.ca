# Fast Trading Variants — Autonomous Automation

## Overview

The fast trading variants provide high-frequency signal generation for systems that were previously stale (>4 days since last pick). These run completely autonomously via GitHub Actions.

## Systems

### Fast Stocks Competition
- **File**: `STOCKS/competition/run_fast_competition.py`
- **Schedule**: Monday-Friday at 14:00 UTC (9:00 AM EST - market open)
- **Frequency**: Daily during market hours
- **Hold Period**: 3-10 days
- **Algorithms**: Breakout Momentum, Bollinger MR, Short-Term Reversal, ML Ranker
- **Tickers**: Top 15 S&P 500 stocks

### Mercury2 Fast
- **File**: `mercury2/mercury2_fast.py`
- **Schedule**: Every 4 hours (00:00, 04:00, 08:00, 12:00, 16:00, 20:00 UTC)
- **Frequency**: 6 times daily
- **Hold Period**: 2-8 hours
- **Algorithms**: Fast Crypto ML with ATR-based stops
- **Tickers**: 10 major crypto pairs

## Automation Workflows

### Individual Workflows
- `fast-stocks-competition.yml` - Runs stocks competition daily
- `mercury2-fast-scan.yml` - Runs crypto scanner every 4 hours

### Master Scheduler
- `fast-variants-master.yml` - Coordinates both systems (Monday-Friday 13:00 UTC)
- Allows selective enabling/disabling of each variant
- Regenerates dashboard after both complete

## Key Features

### Pandas-Free Implementation
- No external dependencies beyond standard library + requests
- Uses mock data generation for testing (replace with real APIs when available)
- Lightweight and reliable deployment

### Smart Signal Management
- Automatic expiry of old picks
- Duplicate prevention
- Score-based filtering (minimum thresholds)
- Risk management with ATR-based stops

### Dashboard Integration
- Automatic dashboard regeneration after each run
- Real-time statistics tracking
- Separate unrealized vs realized PNL display

## Manual Triggers

All workflows support manual triggering via GitHub Actions UI:

```yaml
# Force refresh option clears existing picks and regenerates all signals
force_refresh: 'true'
```

## Monitoring

### Dashboard Statistics
- Check `audit_dashboard/index.html` for live system status
- Fast Stocks Competition: ~45 active picks
- Mercury2 Fast: ~6-13 active picks

### GitHub Actions Logs
- View run history in Actions tab
- Check for failures or timeouts
- Monitor signal generation frequency

## Addresses Original Issues

### Stale Systems Fixed
- **stocks_competition**: Was 20 days stale → Now has fast variant with daily signals
- **mercury2**: Was 6 days stale → Now has fast variant with 6x daily signals
- **kimi_signal_tracking**: Was 7 days stale → Can be addressed with similar fast variant
- **claude_gainer_ml_perf**: Fixed blank last pick display

### Quality Preservation
- Maintains proper risk management (TP/SL ratios)
- Uses proven algorithms with shorter timeframes
- Includes volume and volatility filters
- ATR-based position sizing

## Future Enhancements

### Real Data Integration
Replace mock data with real market data APIs:
- Alpha Vantage, Polygon.io, or similar for stocks
- Binance/Coinbase APIs for crypto

### Advanced Algorithms
- Add more sophisticated ML models
- Implement ensemble methods
- Add market regime detection

### Performance Optimization
- Parallel processing for multiple tickers
- Caching of indicator calculations
- Database storage for historical data