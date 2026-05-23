# Model Health Agent

A comprehensive ML model monitoring and health management system for the crypto trading platform.

## Overview

The Model Health Agent provides real-time monitoring of ML model performance, automatic drift detection, and proactive model maintenance. It integrates seamlessly with the existing ML pipeline and provides both programmatic APIs and web dashboards for monitoring.

## Features

### 🔍 Model Drift Detection
- **Concept Drift**: Monitors changes in prediction distributions using statistical tests
- **Data Drift**: Detects shifts in input feature distributions
- **Performance Decay**: Identifies gradual degradation in model accuracy over time

### 📊 Performance Monitoring
- Real-time tracking of key metrics: accuracy, precision, recall, F1-score
- Trading-specific metrics: Sharpe ratio, win rate, profit factor, max drawdown
- Historical performance trends and statistical significance testing

### 🔄 Automated Retraining Triggers
- Configurable thresholds for performance degradation
- Statistical significance testing for drift detection
- Minimum sample size requirements for retraining
- Integration with existing training pipelines

### 🎯 Model Validation
- Continuous validation against fresh data
- Statistical significance testing for performance changes
- Cross-validation with historical baselines

### 📈 Health Dashboards
- Real-time web dashboard with interactive charts
- Model status overview and alert summaries
- Performance trend visualization
- Drift detection history

### 🏷️ Model Versioning
- Complete audit trail of model versions
- Performance history tracking
- Deployment status monitoring
- Automatic backup and rollback capabilities

## Technical Architecture

### Components

1. **DatabaseManager**: SQLite-based storage for metrics, alerts, and model metadata
2. **DriftDetector**: Statistical engine for detecting various types of model drift
3. **ModelMonitor**: Individual model health monitoring and alerting
4. **ModelHealthAgent**: Main orchestration service with API endpoints

### Data Storage

- **model_versions**: Model metadata, versions, and deployment history
- **model_metrics**: Performance metrics with timestamps
- **drift_detection**: Drift detection results and statistical tests
- **health_alerts**: Alert history and resolution status
- **model_predictions**: Prediction data for drift analysis (future use)

## Installation & Setup

### Prerequisites

```bash
pip install numpy pandas scikit-learn scipy xgboost fastapi uvicorn plotly
```

### Configuration

Edit the `Config` class in `model_health_agent.py`:

```python
class Config:
    # Database settings
    DB_PATH = 'model_health.db'

    # Monitoring intervals (minutes)
    MONITORING_INTERVAL_MINUTES = 15

    # Performance thresholds
    ACCURACY_DEGRADATION_THRESHOLD = 0.05  # 5% drop
    SHARPE_RATIO_MINIMUM = 0.5
    WIN_RATE_MINIMUM = 0.45

    # Drift detection
    DRIFT_P_VALUE_THRESHOLD = 0.05
    DRIFT_STATISTIC_THRESHOLD = 2.0

    # Retraining triggers
    RETRAIN_ACCURACY_DROP = 0.10  # 10% drop triggers retrain
    RETRAIN_CONSECUTIVE_FAILURES = 3
```

## Usage

### Starting the Agent

```python
from model_health_agent import ModelHealthAgent

# Initialize and start
agent = ModelHealthAgent()
agent.start_monitoring()
```

### Registering Models

```python
# Register a trained model for monitoring
success = agent.register_model(
    model_name="btc_predictor_v1",
    model_path="ml_crypto_predictor/production_models/btc_predictor.pkl",
    features=["rsi_14", "macd", "volume_ratio", "returns_5"],
    hyperparameters={
        "n_estimators": 100,
        "max_depth": 6,
        "learning_rate": 0.1
    }
)
```

### Updating Performance

```python
import numpy as np

# After model makes predictions
predictions = np.array([1, 0, 1, 1, 0])  # Model predictions
actuals = np.array([1, 0, 0, 1, 1])     # Actual outcomes
features = np.array([[...], [...]])      # Optional: input features for drift detection

agent.update_model_performance("btc_predictor_v1", predictions, actuals, features)
```

### API Endpoints

When running, the agent provides a REST API:

- `GET /` - Health check
- `GET /health` - All models health status
- `GET /health/{model_name}` - Specific model health
- `GET /alerts` - Active alerts
- `GET /dashboard` - Web dashboard

### Web Dashboard

Access the interactive dashboard at: `http://localhost:8001/dashboard`

Features:
- Real-time model status overview
- Performance trend charts
- Alert notifications
- Drift detection history
- Model version comparison

## Integration with Existing Pipeline

### Training Pipeline Integration

```python
# After training a new model
from model_health_agent import ModelHealthAgent

agent = ModelHealthAgent()

# Register the new model
agent.register_model(
    model_name=f"btc_predictor_{version}",
    model_path=model_save_path,
    features=feature_list,
    hyperparameters=model_params
)

# The agent will automatically monitor performance
```

### Prediction Pipeline Integration

```python
# In your prediction service
from model_health_agent import ModelHealthAgent

agent = ModelHealthAgent()

# Make predictions
predictions = model.predict(X_test)
actuals = y_test  # From validation or live trading

# Update health monitoring
agent.update_model_performance(model_name, predictions, actuals, X_test)
```

### Alert Integration

```python
# Get active alerts
alerts = agent.db.get_active_alerts()

for alert in alerts:
    if alert.level == "CRITICAL":
        # Send notification, trigger retraining, etc.
        send_alert_notification(alert)
```

## Monitoring & Alerts

### Alert Types

- **Accuracy Degradation**: Performance drops below threshold
- **Low Sharpe Ratio**: Risk-adjusted returns too low
- **Low Win Rate**: Trading success rate below minimum
- **Consecutive Failures**: Multiple poor performance periods
- **Drift Detected**: Statistical drift in predictions or data

### Alert Levels

- **INFO**: Informational notifications
- **WARNING**: Performance degradation warnings
- **CRITICAL**: Immediate action required

### Automated Actions

When alerts trigger, the agent can automatically:
- Log detailed diagnostics
- Update model status to "DEGRADED"
- Trigger retraining workflows
- Send notifications to monitoring systems

## Model Lifecycle Management

### Version Control

```python
# Get model versions
versions = agent.db.get_model_versions("btc_predictor")

for version in versions:
    print(f"Version {version.version_id}: {version.status.value}")
    print(f"  Performance: {version.performance_baseline.accuracy}")
```

### Status Management

Models can be in states:
- **ACTIVE**: Currently deployed and monitored
- **DEGRADED**: Performance issues detected
- **RETRAINING**: Model being retrained
- **RETIRED**: No longer in use

### Backup & Recovery

```python
# Automatic backup on version changes
# Models are backed up to: ml_crypto_predictor/model_backups/

# Manual backup
import shutil
shutil.copy(model_path, backup_path)
```

## Performance Metrics

### Classification Metrics
- Accuracy: Overall prediction correctness
- Precision: True positive rate
- Recall: Coverage of positive cases
- F1-Score: Harmonic mean of precision/recall

### Trading Metrics
- Sharpe Ratio: Risk-adjusted returns
- Win Rate: Percentage of profitable trades
- Profit Factor: Gross profits / gross losses
- Max Drawdown: Largest peak-to-trough decline

### Statistical Tests
- Kolmogorov-Smirnov: Distribution differences
- Mahalanobis Distance: Multivariate drift
- Linear Regression: Performance trends
- Chi-square: Categorical drift detection

## Troubleshooting

### Common Issues

1. **Model not loading**: Check file paths and permissions
2. **No metrics updating**: Verify prediction data format
3. **False drift alerts**: Adjust statistical thresholds
4. **Database errors**: Check disk space and permissions

### Debugging

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Check model status
health_report = agent.get_health_report("btc_predictor")
print(health_report)
```

### Performance Optimization

- Adjust monitoring intervals for high-frequency models
- Use sampling for large prediction datasets
- Configure appropriate retention periods for historical data
- Monitor database size and implement cleanup policies

## Success Criteria

✅ **Model drift detected within 1 trading day** of occurrence
- Continuous monitoring with 15-minute intervals
- Statistical tests trigger within monitoring cycles

✅ **Performance degradation alerts sent within 15 minutes**
- Real-time metric calculation and threshold checking
- Immediate alert generation and API notifications

✅ **Automated retraining improves performance by 10%+ on average**
- Configurable retraining triggers based on statistical significance
- Performance validation after retraining cycles

✅ **Model versioning provides complete audit trail**
- Version metadata, performance baselines, and deployment history
- Complete traceability of model changes and decisions

## API Reference

### ModelHealthAgent Class

#### Methods

- `register_model(model_name, model_path, features, hyperparameters)`: Register model for monitoring
- `unregister_model(model_name)`: Stop monitoring model
- `update_model_performance(model_name, predictions, actuals, features)`: Update with new data
- `get_health_report(model_name=None)`: Get comprehensive health report
- `start_monitoring()`: Start background monitoring
- `stop_monitoring()`: Stop monitoring

### DatabaseManager Class

#### Methods

- `save_metrics(model_name, metrics)`: Store performance metrics
- `get_metrics_history(model_name, hours)`: Retrieve historical metrics
- `save_alert(alert)`: Store health alert
- `get_active_alerts(model_name)`: Get unresolved alerts
- `save_drift_detection(model_name, detection)`: Store drift analysis

### DriftDetector Class

#### Methods

- `detect_concept_drift(historical, current)`: Test prediction distribution changes
- `detect_data_drift(historical_features, current_features)`: Test input feature changes
- `detect_performance_decay(metrics_history)`: Analyze performance trends

## Contributing

1. Follow existing code patterns and error handling
2. Add comprehensive logging for debugging
3. Include unit tests for new functionality
4. Update documentation for API changes
5. Test integration with existing ML pipeline

## License

Internal use only - part of the crypto trading platform.