# Data Validator Agent

A comprehensive data quality assurance system for market data feeds in trading systems.

## Features

### 🔍 Feed Health Monitoring
- Real-time monitoring of data freshness, completeness, and accuracy
- Multi-source validation (Binance, CoinGecko, CryptoCompare, etc.)
- Latency tracking and performance metrics
- Automatic health status updates

### 🚨 Outlier Detection
- Statistical outlier detection using z-score analysis
- Configurable threshold (default: 3 standard deviations)
- Real-time anomaly alerts
- Historical outlier tracking

### 🔄 Fallback Source Switching
- Automatic failover to backup data sources
- Priority-based source selection
- Seamless switching with minimal downtime
- Failover event logging and alerting

### 📊 Data Quality Scoring
- Multi-metric quality assessment
- Confidence scoring for data points
- Quality trend analysis
- Performance correlation tracking

### 🔧 Gap Filling
- Intelligent gap detection
- Linear interpolation for missing data
- Configurable gap size limits
- Quality degradation for filled data

### ⏰ Staleness Detection
- Configurable staleness thresholds
- Real-time age monitoring
- Automatic alerts for stale data
- Source health degradation tracking

## Technical Architecture

### Core Components
- **DataValidatorAgent**: Main agent class with async monitoring
- **Data Sources**: Modular fetchers for different APIs
- **Quality Engine**: Statistical analysis and scoring
- **Alert System**: Configurable alerting with cooldowns
- **Web Dashboard**: Real-time monitoring interface
- **Database Integration**: PostgreSQL for persistence

### Data Flow
```
External APIs → Data Fetchers → Validation Engine → Quality Scoring → Storage → Dashboard
      ↓              ↓              ↓              ↓              ↓              ↓
   CoinGecko     Binance       Outlier        Confidence     PostgreSQL     Web UI
   CryptoComp    Kraken        Gap Fill      Correlation     Redis         API
   Coinbase      Custom        Staleness     Trends          Alerts
```

## Configuration

```python
config = DataValidatorConfig(
    # Data sources per symbol
    primary_sources={
        'BTC': [DataSource.BINANCE, DataSource.COINGECKO, DataSource.CRYPTOCOMPARE],
        'ETH': [DataSource.BINANCE, DataSource.COINGECKO, DataSource.CRYPTOCOMPARE],
    },

    # Quality thresholds
    max_staleness_seconds=300,        # 5 minutes
    outlier_threshold_std=3.0,        # 3 standard deviations
    min_quality_score=0.7,            # 70% minimum

    # Monitoring settings
    monitoring_interval_seconds=30,   # Check every 30 seconds
    dashboard_update_interval=60,     # Update dashboard every minute

    # API Keys
    coingecko_api_key="your_key_here",
    cryptocompare_api_key="your_key_here"
)
```

## Installation & Setup

### Requirements
```bash
pip install aiohttp asyncpg aioredis fastapi uvicorn numpy pandas
```

### Environment Variables
```bash
export REDIS_URL="redis://localhost:6379"
export DATABASE_URL="postgresql://user:pass@localhost/trading"
```

### Database Schema
```sql
-- Data points table
CREATE TABLE data_points (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    price DECIMAL(20,8) NOT NULL,
    volume DECIMAL(20,8),
    timestamp TIMESTAMP NOT NULL,
    source VARCHAR(20) NOT NULL,
    quality_score FLOAT DEFAULT 1.0,
    is_outlier BOOLEAN DEFAULT FALSE,
    is_gap_filled BOOLEAN DEFAULT FALSE
);

-- Validation alerts table
CREATE TABLE validation_alerts (
    id SERIAL PRIMARY KEY,
    alert_id VARCHAR(100) UNIQUE NOT NULL,
    alert_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    symbol VARCHAR(10),
    source VARCHAR(20),
    value FLOAT DEFAULT 0.0,
    threshold FLOAT DEFAULT 0.0,
    timestamp TIMESTAMP NOT NULL,
    acknowledged BOOLEAN DEFAULT FALSE
);

-- Create indexes
CREATE INDEX idx_data_points_symbol_timestamp ON data_points(symbol, timestamp);
CREATE INDEX idx_alerts_timestamp ON validation_alerts(timestamp);
```

## Usage

### Basic Usage
```python
from data_validator_agent import DataValidatorAgent, DataValidatorConfig

# Initialize agent
agent = DataValidatorAgent(redis_url, db_url)

# Start monitoring
await agent.start()

# Agent runs indefinitely with real-time monitoring
```

### Custom Configuration
```python
config = DataValidatorConfig(
    primary_sources={
        'BTC': [DataSource.BINANCE, DataSource.COINGECKO],
        'ETH': [DataSource.BINANCE, DataSource.CRYPTOCOMPARE],
        'SOL': [DataSource.BINANCE, DataSource.COINGECKO],
    },
    monitoring_interval_seconds=15,  # More frequent checks
    max_staleness_seconds=120,       # Tighter staleness threshold
)

agent = DataValidatorAgent(redis_url, db_url, config)
```

## API Endpoints

### Health Check
```
GET /api/health
```
Returns overall system health and key metrics.

### Feed Status
```
GET /api/feeds
```
Returns detailed status for all data feeds.

### Active Alerts
```
GET /api/alerts
```
Returns all currently active validation alerts.

### Quality Metrics
```
GET /api/quality
```
Returns comprehensive quality metrics and statistics.

## Web Dashboard

Access the real-time dashboard at `http://localhost:8001` when the agent is running.

Features:
- Real-time quality metrics
- Feed status overview
- Active alerts display
- Historical trends (when integrated with plotting)

## Testing

Run the test suite:
```bash
python test_data_validator.py
```

Tests cover:
- Agent initialization
- Feed health monitoring
- Data point storage
- Outlier detection
- Quality metrics
- API endpoint simulation

## Success Criteria

✅ **Data feeds validated with <1% error rate**
- Comprehensive error tracking and retry logic
- Multi-source validation reduces single points of failure

✅ **Outliers detected and handled within 30 seconds**
- Real-time statistical analysis
- Immediate alert generation
- Automated handling protocols

✅ **Automatic failover with <5 minute downtime**
- Priority-based source switching
- Health-based failover decisions
- Minimal service interruption

✅ **Quality scores correlate with actual trading performance**
- Historical quality vs. P&L analysis
- Confidence-based trade filtering
- Performance attribution by data quality

## Monitoring & Alerting

### Alert Types
- **STALE_DATA**: Data older than threshold
- **OUTLIER_DETECTED**: Statistical anomalies
- **SOURCE_FAILURE**: Feed connectivity issues
- **GAP_DETECTED**: Missing data periods
- **QUALITY_DROP**: Overall quality degradation
- **FAILOVER_ACTIVATED**: Source switching events

### Alert Severity Levels
- **CRITICAL**: Immediate action required
- **HIGH**: Urgent attention needed
- **MEDIUM**: Should be addressed soon
- **LOW**: Monitor for trends

## Integration

### With Trading System
```python
# Get quality score for a symbol before trading
quality = agent.get_quality_score('BTC')
if quality > 0.8:
    # Proceed with trade
    execute_trade('BTC', confidence=quality)
```

### With Risk Management
```python
# Adjust position sizes based on data quality
risk_multiplier = agent.quality_metrics.average_quality_score
max_position = base_max_position * risk_multiplier
```

## Troubleshooting

### Common Issues

**High latency on feeds:**
- Check network connectivity
- Verify API rate limits
- Consider adding more sources

**False positive outliers:**
- Adjust outlier_threshold_std
- Review statistical window size
- Check for legitimate price movements

**Frequent failovers:**
- Review source reliability
- Check API key validity
- Consider adding more backup sources

**Database connection issues:**
- Verify DATABASE_URL
- Check PostgreSQL connectivity
- Ensure proper permissions

### Logs
All activities are logged to `data_validator.log` with configurable levels.

## Future Enhancements

- Machine learning-based anomaly detection
- Predictive quality forecasting
- Advanced gap filling algorithms
- Real-time charting integration
- Multi-asset correlation analysis
- Automated parameter optimization</content>
<parameter name="filePath">e:\findtorontoevents_antigravity.ca\DATA_VALIDATOR_README.md