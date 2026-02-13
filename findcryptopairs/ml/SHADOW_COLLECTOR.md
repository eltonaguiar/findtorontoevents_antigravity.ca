# Shadow Mode Signal Collection System

Collect 350+ resolved signals to validate the XGBoost meme coin model with statistical significance (95% CI at 40% target win rate).

## Overview

Shadow mode means we generate signals but don't act on them - we just track outcomes to compare ML model performance vs rule-based scoring.

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Meme Scanner   │────▶│  Shadow Collector │────▶│  mc_shadow_     │
│  (rule-based)   │     │                  │     │  signals table  │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │
                               │ ML predictions
                               ▼
                        ┌──────────────────┐
                        │  XGBoost Model   │
                        │  (predict.php)   │
                        └──────────────────┘
```

## Quick Start

### 1. Initialize Database Tables

```bash
curl -X POST "https://findtorontoevents.ca/findcryptopairs/ml/shadow_collector.php?action=init&key=shadow2026"
```

Or run the SQL directly:
```bash
mysql -h mysql.50webs.com -u ejaguiar1_memecoin -p ejaguiar1_memecoin < shadow_schema.sql
```

### 2. Manual Test Collection

```bash
# Collect signals
curl -X POST "https://findtorontoevents.ca/findcryptopairs/ml/shadow_collector.php?action=collect&key=shadow2026"

# Resolve outcomes
curl -X POST "https://findtorontoevents.ca/findcryptopairs/ml/shadow_collector.php?action=resolve&key=shadow2026"

# Full cycle
curl -X POST "https://findtorontoevents.ca/findcryptopairs/ml/shadow_collector.php?action=full_cycle&key=shadow2026"
```

### 3. Check Progress

```bash
# Get progress to 350 target
curl "https://findtorontoevents.ca/findcryptopairs/ml/shadow_collector.php?action=progress"

# Get full comparison report
curl "https://findtorontoevents.ca/findcryptopairs/ml/shadow_collector.php?action=report"
```

## API Endpoints

### Public Endpoints (No Key Required)

| Endpoint | Description |
|----------|-------------|
| `?action=report` | Get ML vs rule-based comparison report |
| `?action=progress` | Get progress to 350 signal target |
| `?action=list&status=open&limit=100` | List shadow signals |
| `?action=chart&days=30` | Get chart data for visualization |

### Protected Endpoints (Requires `key=shadow2026`)

| Endpoint | Description |
|----------|-------------|
| `POST ?action=collect` | Force signal collection |
| `POST ?action=resolve` | Force outcome resolution |
| `POST ?action=init` | Initialize database tables |
| `POST ?action=full_cycle` | Run collect + resolve |

## Database Schema

### mc_shadow_signals

| Column | Type | Description |
|--------|------|-------------|
| id | INT | Primary key |
| symbol | VARCHAR(20) | Coin symbol (DOGE, SHIB, etc) |
| timestamp | INT | Unix timestamp when signal created |
| entry_price | DECIMAL(18,8) | Price at signal time |
| ml_score | DECIMAL(5,4) | XGBoost probability (0-1) |
| ml_prediction | VARCHAR(10) | buy/hold/sell/avoid |
| ml_tier | VARCHAR(20) | strong_buy/moderate_buy/lean_buy |
| rule_based_score | INT | Scanner score (0-100) |
| rule_based_tier | VARCHAR(20) | Strong Buy/Buy/Lean Buy |
| features | JSON | All 16 features snapshot |
| status | VARCHAR(20) | open/closed |
| tp_price | DECIMAL(18,8) | Take profit price (+8%) |
| sl_price | DECIMAL(18,8) | Stop loss price (-4%) |
| exit_price | DECIMAL(18,8) | Price when closed |
| exit_time | INT | Unix timestamp when closed |
| exit_reason | VARCHAR(20) | tp_hit/sl_hit/max_hold |
| return_pct | DECIMAL(8,4) | Actual return % |
| ml_was_correct | BOOLEAN | Did ML match outcome? |
| rule_based_was_correct | BOOLEAN | Did rule-based match outcome? |

### mc_shadow_summary

Daily aggregated statistics for trend analysis.

## Signal Flow

1. **Collection** (every 30 min via GitHub Actions)
   - Query meme scanner for candidates
   - Get ML prediction from XGBoost model
   - Store in mc_shadow_signals with status='open'

2. **Resolution** (every 30 min via GitHub Actions)
   - Check all open signals against current prices
   - Mark as closed if TP hit (+8%), SL hit (-4%), or max hold (24h)
   - Calculate if predictions were correct

3. **Reporting** (on-demand)
   - Compare ML vs rule-based win rates
   - Track progress to 350 target
   - Wilson score CI for statistical validity

## Target Calculation

**Goal:** 350 signals for 95% confidence interval at 40% target win rate

Using Wilson score interval:
```
CI_lower = (p + z²/(2n) - z*√((p(1-p)+z²/(4n))/n)) / (1+z²/n)
CI_upper = (p + z²/(2n) + z*√((p(1-p)+z²/(4n))/n)) / (1+z²/n)
```

Where:
- p = observed win rate
- n = sample size (350)
- z = 1.96 (95% CI)

At n=350, p=0.40:
- Wilson CI: [35.2%, 45.1%]
- Margin of error: ±4.9%

## Exit Rules

| Condition | Action | Classification |
|-----------|--------|----------------|
| Price ≥ TP (+8%) | Close signal | Win |
| Price ≤ SL (-4%) | Close signal | Loss |
| Age ≥ 24 hours | Close signal | Win if price > entry |

## Comparison Methodology

### ML Model Prediction
- **Strong Buy**: probability ≥ 0.75 (distance from 0.5)
- **Moderate Buy**: probability ≥ 0.60
- **Lean Buy**: probability ≥ 0.50
- **Correct** if: buy → win, sell/avoid → loss, hold → any

### Rule-Based Prediction
- **Strong Buy**: score ≥ 88
- **Buy**: score ≥ 82
- **Lean Buy**: score ≥ 78
- **Correct** if: buy tier → win, skip → loss

## GitHub Actions Automation

The `.github/workflows/shadow-collector.yml` runs every 30 minutes:

```yaml
schedule:
  - cron: '*/30 * * * *'  # Every 30 minutes
```

It:
1. Collects new signals
2. Resolves open signals
3. Updates progress metrics
4. Comments on PRs if triggered that way
5. Notifies when 350 target reached

## Environment Variables

Add to GitHub Secrets:
- `SHADOW_COLLECTOR_KEY` - Admin key for protected endpoints (default: "shadow2026")

## Monitoring

### Check Collection Status
```bash
curl -s "https://findtorontoevents.ca/findcryptopairs/ml/shadow_collector.php?action=progress" | jq
```

Expected output:
```json
{
  "ok": true,
  "progress": {
    "current_signals": 127,
    "target_signals": 350,
    "percent_complete": 36.3,
    "current_win_rate": 42.5,
    "wilson_ci_95": {
      "lower": 34.8,
      "upper": 50.7
    },
    "is_statistically_valid": false,
    "estimated_completion": {
      "reached": false,
      "date": "2026-03-15",
      "days_remaining": 28,
      "signals_per_day": 8.2
    }
  }
}
```

### View Recent Signals
```bash
curl -s "https://findtorontoevents.ca/findcryptopairs/ml/shadow_collector.php?action=list&status=open&limit=10" | jq
```

### Get Comparison Report
```bash
curl -s "https://findtorontoevents.ca/findcryptopairs/ml/shadow_collector.php?action=report" | jq '.report | {ml_stats, rule_based_stats, by_tier}'
```

## Analysis Queries

### Overall Comparison
```sql
SELECT 
    'ML Model' as method,
    SUM(CASE WHEN ml_was_correct = 1 THEN 1 ELSE 0 END) as wins,
    SUM(CASE WHEN ml_was_correct = 0 THEN 1 ELSE 0 END) as losses,
    ROUND(SUM(CASE WHEN ml_was_correct = 1 THEN 1 ELSE 0 END) / COUNT(*) * 100, 2) as win_rate
FROM mc_shadow_signals WHERE status = 'closed'
UNION ALL
SELECT 
    'Rule-Based' as method,
    SUM(CASE WHEN rule_based_was_correct = 1 THEN 1 ELSE 0 END) as wins,
    SUM(CASE WHEN rule_based_was_correct = 0 THEN 1 ELSE 0 END) as losses,
    ROUND(SUM(CASE WHEN rule_based_was_correct = 1 THEN 1 ELSE 0 END) / COUNT(*) * 100, 2) as win_rate
FROM mc_shadow_signals WHERE status = 'closed';
```

### By ML Tier
```sql
SELECT 
    ml_tier,
    COUNT(*) as signals,
    SUM(CASE WHEN ml_was_correct = 1 THEN 1 ELSE 0 END) as wins,
    ROUND(AVG(CASE WHEN ml_was_correct = 1 THEN 1 ELSE 0 END) * 100, 2) as win_rate
FROM mc_shadow_signals 
WHERE status = 'closed' 
GROUP BY ml_tier;
```

### Exit Reason Distribution
```sql
SELECT 
    exit_reason,
    COUNT(*) as count,
    ROUND(AVG(return_pct), 2) as avg_return
FROM mc_shadow_signals 
WHERE status = 'closed'
GROUP BY exit_reason;
```

## Troubleshooting

### No signals being collected
1. Check if tables exist: `?action=init`
2. Verify ML model is loaded: `predict.php?action=health`
3. Check meme scanner is working: `meme_scanner.php?action=winners`

### All signals showing null for ML correctness
- Signals need to be resolved first: `?action=resolve`
- Check if Kraken API is responding (for price data)

### Progress not updating
- Daily summary updates automatically on collect/resolve
- Manual update: `?action=full_cycle`

## Files

| File | Description |
|------|-------------|
| `shadow_collector.php` | Main API endpoint |
| `shadow_schema.sql` | Database schema |
| `SHADOW_COLLECTOR.md` | This documentation |
| `../../.github/workflows/shadow-collector.yml` | GitHub Actions automation |

## Next Steps After 350 Signals

Once 350+ signals are collected and statistically validated:

1. Compare ML vs rule-based win rates
2. If ML significantly outperforms (>5% improvement):
   - Gradually increase ML weight in live system
   - Consider A/B testing with 10% traffic
3. If ML underperforms:
   - Analyze feature importance
   - Retrain with more recent data
   - Adjust confidence thresholds
4. Document findings in `ML_VALIDATION_REPORT.md`

## Support

For issues or questions:
1. Check the comparison report: `?action=report`
2. Review GitHub Actions logs
3. Query database directly for detailed analysis
