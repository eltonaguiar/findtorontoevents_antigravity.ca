# ML Pipeline Quick Start

## 1. Initialize the System

```bash
cd findcryptopairs/ml
php init.php
```

This will:
- Create necessary directories
- Check PHP/Python requirements
- Generate sample training data
- Test the features API

## 2. Train the Model

```bash
# Train with sample data
python train_model.py --all-symbols --days 90

# Or train for specific symbol
python train_model.py --symbol DOGE --days 90
```

Expected output:
- Model saved to: `models/meme_xgb_v1.0.0_TIMESTAMP.json`
- Report saved to: `models/meme_xgb_v1.0.0_TIMESTAMP_report.txt`

Target: 70%+ accuracy on cross-validation

## 3. Make Predictions

### Single Prediction
```bash
curl "https://yourdomain.com/findcryptopairs/ml/predict.php?action=predict&symbol=DOGE&entry=0.15&tp=0.18&sl=0.13"
```

Response:
```json
{
  "ok": true,
  "symbol": "DOGE",
  "prediction": "buy",
  "probability": 0.73,
  "confidence_tier": "strong",
  "expected_return": 0.15,
  "risk_reward": 2.5
}
```

### Batch Prediction
```bash
curl "https://yourdomain.com/findcryptopairs/ml/predict.php?action=batch&symbols=DOGE,SHIB,PEPE,FLOKI,BONK"
```

## 4. API Endpoints Reference

### Features API (`features.php`)
| Action | Parameters | Description |
|--------|------------|-------------|
| `features` | `symbol` | Get features for symbol |
| `batch` | `symbols` (comma-separated) | Get features for multiple |
| `history` | `symbol`, `days` | Get historical features |

### Prediction API (`predict.php`)
| Action | Parameters | Description |
|--------|------------|-------------|
| `predict` | `symbol`, `entry`, `tp`, `sl` | Single prediction |
| `batch` | `symbols` | Batch predictions |
| `health` | - | Check model health |
| `models` | - | List available models |

## 5. File Structure

```
findcryptopairs/ml/
├── features.php           # Feature extraction
├── train_model.py         # Training pipeline
├── predict.php            # Prediction API
├── predict_bridge.py      # Python bridge
├── export_training_data.php  # Export from DB
├── init.php               # Initialization
├── requirements.txt       # Python deps
├── README.md              # Full documentation
├── QUICKSTART.md          # This file
├── models/                # Saved models
│   ├── meme_xgb_v1.0.0_*.json
│   └── latest_model.txt
└── data/                  # Training data
    ├── training_data_*.csv
    └── cache/
```

## 6. Cron Jobs

```bash
# Daily retraining at 2 AM
0 2 * * * cd /path/to/findcryptopairs/ml && python train_model.py --all-symbols --model-version auto-$(date +\%Y\%m\%d)

# Weekly full retrain on Sundays
0 3 * * 0 cd /path/to/findcryptopairs/ml && python train_model.py --all-symbols --days 180 --model-version weekly-$(date +\%Y\%m\%d)
```

## 7. Troubleshooting

### "No trained model found"
```bash
# Train first
python train_model.py --symbol DOGE
```

### "XGBoost not installed"
```bash
pip install xgboost scikit-learn pandas numpy
```

### Features returning zeros
- Check Kraken API connectivity
- Verify Reddit/Trends API access
- Check cache directory permissions

### Low accuracy (< 70%)
- Increase training data: `--days 180`
- Check data quality in CSV files
- Verify labels are correct
- Try feature engineering in `train_model.py`

## 8. Feature List

| Feature | Description | Range |
|---------|-------------|-------|
| `return_5m` | 5-minute return | -∞ to +∞ |
| `return_15m` | 15-minute return | -∞ to +∞ |
| `return_1h` | 1-hour return | -∞ to +∞ |
| `return_4h` | 4-hour return | -∞ to +∞ |
| `return_24h` | 24-hour return | -∞ to +∞ |
| `volatility_24h` | Return std dev | 0 to 1 |
| `volume_ratio` | Current/avg volume | 0 to ∞ |
| `reddit_velocity` | Comments per hour | 0 to ∞ |
| `trends_velocity` | Search trend ratio | 0 to ∞ |
| `sentiment_correlation` | Cross-platform | 0 to 1 |
| `btc_trend_4h` | BTC 4h return | -∞ to +∞ |
| `btc_trend_24h` | BTC 24h return | -∞ to +∞ |
| `hour` | Hour of day | 0-23 |
| `day_of_week` | Day of week | 0-6 |
| `is_weekend` | Weekend flag | 0 or 1 |

## 9. Prediction Thresholds

| Action | Probability | R/R Ratio |
|--------|-------------|-----------|
| Buy | ≥ 70% | ≥ 1.5 |
| Buy | ≥ 60% | ≥ 2.0 |
| Avoid | < 45% | - |
| Sell | ≤ 30% | < 1.0 |

## 10. A/B Testing

```bash
# Test specific model version
curl ".../predict.php?action=predict&symbol=DOGE&model_version=v1.0.0"

# Compare with latest
curl ".../predict.php?action=predict&symbol=DOGE&model_version=v1.1.0"

# List all models
curl ".../predict.php?action=models"
```
