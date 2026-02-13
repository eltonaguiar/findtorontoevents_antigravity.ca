# Meme Coin XGBoost Prediction Model

This directory contains the machine learning training pipeline for meme coin price prediction.

## Overview

The XGBoost model predicts whether a meme coin will hit take-profit (15% gain) before stop-loss (10% loss) within a 72-hour window.

## Directory Structure

```
ml/
├── train_meme_model.py      # Main training script
├── requirements.txt         # Python dependencies
├── README.md               # This file
└── models/                 # Generated model files (created on first run)
    ├── meme_model_v1.0.0_YYYYMMDD.json       # Trained model
    ├── meme_model_v1.0.0_YYYYMMDD_metadata.json  # Training metadata
    ├── feature_importance.json               # Feature rankings
    ├── threshold_config.json                 # Optimal thresholds
    ├── model_config.json                     # PHP-readable config
    └── training_report.txt                   # Human-readable report
```

## Installation

```bash
cd findcryptopairs/ml
pip install -r requirements.txt
```

## Usage

### Basic Training

```bash
python train_meme_model.py
```

### Custom Hyperparameters

```bash
python train_meme_model.py --n-estimators 300 --max-depth 6 --learning-rate 0.03
```

### Evaluate Existing Model

```bash
python train_meme_model.py --evaluate-only
python train_meme_model.py --evaluate-only --model-path models/meme_model_v1.0.0_20260216.json
```

### Full Options

```bash
python train_meme_model.py --help
```

## Data Format

The training script expects a CSV file at `data/training/meme_training_data.csv` with the following columns:

### Features (16 total)

| Feature | Description |
|---------|-------------|
| `return_5m` | 5-minute price return |
| `return_15m` | 15-minute price return |
| `return_1h` | 1-hour price return |
| `return_4h` | 4-hour price return |
| `return_24h` | 24-hour price return |
| `volatility_24h` | 24-hour price volatility |
| `volume_ratio` | Current volume vs average ratio |
| `reddit_velocity` | Reddit mention growth rate |
| `trends_velocity` | Google Trends growth rate |
| `sentiment_score` | Overall sentiment (-1 to 1) |
| `sentiment_volatility` | Sentiment variance |
| `btc_trend_4h` | Bitcoin 4-hour trend |
| `btc_trend_24h` | Bitcoin 24-hour trend |
| `hour_of_day` | Hour (0-23) |
| `day_of_week` | Day (0-6) |
| `is_weekend` | Weekend flag (0/1) |

### Target

| Column | Description |
|--------|-------------|
| `target` | 1 = hit take-profit first, 0 = hit stop-loss first |

## Model Architecture

- **Algorithm**: XGBoost Classifier
- **Objective**: Binary classification (win/loss)
- **Evaluation**: AUC-ROC
- **Validation**: 5-fold Time-Series Split (prevents lookahead bias)
- **Class Imbalance Handling**: scale_pos_weight

## Output Files

### 1. Model File (`meme_model_v*.json`)
Standard XGBoost JSON format, loadable with `XGBClassifier.load_model()`.

### 2. Metadata (`meme_model_v*_metadata.json`)
Contains training parameters, CV results, and performance metrics.

### 3. Feature Importance (`feature_importance.json`)
Ranked list of features by importance score.

### 4. Threshold Config (`threshold_config.json`)
Optimal probability thresholds for tier classification:
- Lean Buy: >= threshold - 0.1
- Moderate Buy: >= threshold
- Strong Buy: >= threshold + 0.1

### 5. PHP Config (`model_config.json`)
Consolidated config for PHP prediction API integration.

### 6. Training Report (`training_report.txt`)
Human-readable summary of training results.

## Expected Performance

| Metric | Baseline (Rule-Based) | XGBoost Target |
|--------|----------------------|----------------|
| Win Rate | 3-5% | 40%+ |
| AUC | ~0.5 (random) | 0.75+ |
| Precision | ~5% | 60%+ |

## Troubleshooting

### "Training data not found"
Run `export_training_data.php` first to generate the CSV file.

### "Missing required columns"
Ensure the CSV includes all 16 feature columns plus the target column.

### Poor CV performance
- Increase dataset size (need 200+ samples minimum)
- Check for data leakage (temporal ordering)
- Review feature engineering

## Integration with PHP

The `model_config.json` file can be read by PHP for real-time predictions:

```php
$config = json_decode(file_get_contents('ml/models/model_config.json'), true);
$features = $config['features'];
$thresholds = $config['thresholds'];
```

For full PHP XGBoost inference, consider using the `php-xgboost` extension or calling Python via shell_exec.

## Development

### Running Tests

```bash
# Validate installation
python -c "import xgboost; print(xgboost.__version__)"

# Test data loading
python train_meme_model.py --data-path test_data.csv
```

### Hyperparameter Tuning

Edit the training script or use command-line arguments:

```bash
python train_meme_model.py \
    --n-estimators 500 \
    --max-depth 7 \
    --learning-rate 0.01 \
    --subsample 0.9
```

## References

- [XGBoost Documentation](https://xgboost.readthedocs.io/)
- [Time Series Cross-Validation](https://scikit-learn.org/stable/modules/cross_validation.html#time-series-split)
- [Classification Metrics Guide](https://scikit-learn.org/stable/modules/model_evaluation.html#classification-metrics)
