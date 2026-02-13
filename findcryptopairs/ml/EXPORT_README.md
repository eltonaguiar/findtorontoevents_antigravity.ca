# ML Training Data Export Script

## Overview
The `export_training_data.php` script exports historical meme coin training data from the `mc_winners` table for XGBoost model training.

## Features

- **Feature Engineering**: Calculates returns, volatility, volume ratios, and temporal features
- **Data Quality Checks**: Removes NULLs, outliers (>1000% or <-90% returns)
- **Time-Series Aware Split**: Chronological train/test split (last 30 days for test)
- **Binary Classification Target**: 1 = Hit TP before SL (win), 0 = Loss
- **CLI & Web Support**: Can be run from command line or via HTTP

## API Endpoints

### 1. Data Summary
```bash
curl "https://yourdomain.com/findcryptopairs/ml/export_training_data.php?action=summary"
```
Returns:
- Total signals count
- Resolved/pending breakdown
- Win rate statistics
- Breakdown by tier and verdict

### 2. Export Training Data
```bash
curl "https://yourdomain.com/findcryptopairs/ml/export_training_data.php?action=export"
```
Returns:
- Train/test CSV file paths
- Record counts
- Win rate
- Data quality metrics

### 3. Validate Data Quality
```bash
curl "https://yourdomain.com/findcryptopairs/ml/export_training_data.php?action=validate"
```
Returns:
- Quality score (0-100)
- List of data issues
- Recommendations

### 4. Download CSV
```bash
curl "https://yourdomain.com/findcryptopairs/ml/export_training_data.php?action=download_csv&dataset=all"
```
Downloads CSV file directly for use in Python/XGBoost.

## CLI Usage

```bash
# Data summary
php export_training_data.php --cli --action=summary

# Export data
php export_training_data.php --cli --action=export

# Validate quality
php export_training_data.php --cli --action=validate

# Custom output directory
php export_training_data.php --cli --action=export --output-dir=/path/to/data
```

## CSV Output Format

```csv
symbol,return_5m,return_15m,return_1h,return_4h,return_24h,volatility_24h,volume_ratio,reddit_velocity,trends_velocity,sentiment_score,sentiment_volatility,btc_trend_4h,btc_trend_24h,hour_of_day,day_of_week,is_weekend,score,tier_encoded,target
DOGE,0.0025,0.0125,0.0250,0.0500,2.3500,3.4500,1.8500,8.5000,1.3200,0.4500,1.7250,0.4500,1.2000,14,2,0,88,1,1
SHIB,0.0018,0.0085,0.0170,0.0340,-1.2500,2.8000,1.4200,6.2000,1.1800,0.3200,1.4000,-0.2500,-0.8000,9,1,0,72,1,0
```

## Features Description

| Feature | Description | Range |
|---------|-------------|-------|
| `symbol` | Token symbol (e.g., DOGE, SHIB) | string |
| `return_5m` | Estimated 5-minute return | decimal |
| `return_15m` | Estimated 15-minute return | decimal |
| `return_1h` | Estimated 1-hour return | decimal |
| `return_4h` | Estimated 4-hour return | decimal |
| `return_24h` | 24-hour price change | decimal |
| `volatility_24h` | 24-hour volatility (ATR-based) | decimal |
| `volume_ratio` | Volume surge ratio | 0-∞ |
| `reddit_velocity` | Social momentum proxy | 0-25 |
| `trends_velocity` | Trends indicator | decimal |
| `sentiment_score` | Normalized sentiment | 0-10 |
| `sentiment_volatility` | Sentiment variability | decimal |
| `btc_trend_4h` | BTC 4-hour trend | decimal |
| `btc_trend_24h` | BTC 24-hour trend | decimal |
| `hour_of_day` | Signal hour (0-23) | 0-23 |
| `day_of_week` | Day (0=Sunday) | 0-6 |
| `is_weekend` | Weekend flag | 0 or 1 |
| `score` | Scanner score (0-100) | 0-100 |
| `tier_encoded` | Tier (1=tier1, 0=tier2) | 0 or 1 |
| `target` | Win=1, Loss=0 | 0 or 1 |

## Data Flow

1. Query `mc_winners` table for resolved signals
2. Extract features from `factors_json` and price data
3. Calculate derived features (returns, volatility, time features)
4. Apply data quality filters
5. Split chronologically (train: before cutoff, test: last 30 days)
6. Export to CSV files

## File Outputs

Files are saved to `findcryptopairs/ml/data/training/`:
- `meme_training_all_YYYY_MM_DD_HHMMSS.csv` - All data
- `meme_training_train_YYYY_MM_DD_HHMMSS.csv` - Training set
- `meme_training_test_YYYY_MM_DD_HHMMSS.csv` - Test set

## Python Usage Example

```python
import pandas as pd
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, classification_report

# Load data
df = pd.read_csv('meme_training_train_2025_02_12_120000.csv')

# Features and target
feature_cols = [c for c in df.columns if c not in ['symbol', 'target']]
X_train = df[feature_cols]
y_train = df['target']

# Train model
model = XGBClassifier(
    n_estimators=100,
    max_depth=6,
    learning_rate=0.1,
    eval_metric='logloss'
)
model.fit(X_train, y_train)

# Evaluate
X_test = pd.read_csv('meme_training_test_2025_02_12_120000.csv')[feature_cols]
y_test = pd.read_csv('meme_training_test_2025_02_12_120000.csv')['target']
predictions = model.predict(X_test)
print(classification_report(y_test, predictions))
```

## Data Quality Checks

The script performs the following validations:

1. **NULL Check**: Removes rows with NULL features
2. **Outlier Detection**: Removes returns > 1000% or < -90%
3. **Chronology**: Verifies chronological order (prevents data leakage)
4. **Duplicates**: Detects duplicate signals
5. **Sample Size**: Recommends 500+ samples for training

## Troubleshooting

### No Data Exported
- Check that `mc_winners` table has resolved signals (`outcome IS NOT NULL`)
- Run scanner resolve action to update pending signals

### Low Win Rate
- Check data quality with `action=validate`
- Verify scanner algorithm is working correctly

### Large Number of Skipped Rows
- Check for NULL values in factors_json
- Verify extreme PnL values are legitimate
