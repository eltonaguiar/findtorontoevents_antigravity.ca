#!/usr/bin/env python3
"""
Model Health Agent Integration Example
======================================
Example showing how to integrate the Model Health Agent
with the existing crypto ML prediction pipeline.
"""

import os
import sys
import numpy as np
import pandas as pd
from datetime import datetime
import logging

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from model_health_agent import ModelHealthAgent
from crypto_fusion_predictor import CryptoFusionPredictor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HealthMonitoredPredictor:
    """Wrapper for CryptoFusionPredictor with health monitoring"""

    def __init__(self, symbol='BTC/USDT', use_health_monitoring=True):
        self.symbol = symbol
        self.predictor = CryptoFusionPredictor(symbol=symbol)
        self.health_agent = None

        if use_health_monitoring:
            self._init_health_monitoring()

    def _init_health_monitoring(self):
        """Initialize health monitoring for the predictor"""
        try:
            self.health_agent = ModelHealthAgent()

            # Register the model with health agent
            model_name = f"crypto_fusion_{self.symbol.lower().replace('/', '_')}"

            # For demonstration, we'll create a mock model path
            # In production, this would be the actual saved model path
            model_path = f"ml_crypto_predictor/production_models/{model_name}.pkl"

            # Basic feature list (would be extracted from actual model in production)
            features = [
                'rsi_7', 'rsi_14', 'rsi_21', 'ema_9', 'ema_21', 'ema_50',
                'sma_20', 'sma_50', 'macd_line', 'macd_signal', 'macd_hist',
                'bb_upper', 'bb_lower', 'bb_width', 'volume_sma_20',
                'return_1', 'return_5', 'volatility_10', 'roc_5'
            ]

            # Register with health agent
            success = self.health_agent.register_model(
                model_name=model_name,
                model_path=model_path,
                features=features,
                hyperparameters={
                    'n_estimators': 100,
                    'random_state': 42,
                    'regime_components': 4
                }
            )

            if success:
                logger.info(f"✅ Health monitoring enabled for {model_name}")
                self.model_name = model_name
            else:
                logger.warning(f"⚠️ Failed to enable health monitoring for {model_name}")
                self.health_agent = None

        except Exception as e:
            logger.error(f"Failed to initialize health monitoring: {e}")
            self.health_agent = None

    def predict_with_monitoring(self, data_dict):
        """
        Make predictions with health monitoring

        Args:
            data_dict: Dictionary containing market data and predictions
                      Expected keys: 'predictions', 'actuals', 'features'
        """
        try:
            predictions = data_dict.get('predictions')
            actuals = data_dict.get('actuals')
            features = data_dict.get('features')

            if predictions is not None and actuals is not None and self.health_agent:
                # Convert to numpy arrays if needed
                if isinstance(predictions, list):
                    predictions = np.array(predictions)
                if isinstance(actuals, list):
                    actuals = np.array(actuals)
                if isinstance(features, list):
                    features = np.array(features)

                # Update health monitoring
                self.health_agent.update_model_performance(
                    self.model_name,
                    predictions,
                    actuals,
                    features
                )

                logger.info(f"📊 Updated health metrics for {self.model_name}")

            return data_dict

        except Exception as e:
            logger.error(f"Health monitoring update failed: {e}")
            return data_dict

    def get_health_status(self):
        """Get current health status"""
        if self.health_agent and hasattr(self, 'model_name'):
            return self.health_agent.get_health_report(self.model_name)
        return None

    def get_active_alerts(self):
        """Get active health alerts"""
        if self.health_agent and hasattr(self, 'model_name'):
            alerts = self.health_agent.db.get_active_alerts(self.model_name)
            return [alert.to_dict() for alert in alerts]
        return []


def example_integration():
    """Example of integrating health monitoring with prediction workflow"""
    print("🚀 Model Health Agent Integration Example")
    print("=" * 50)

    # Initialize health-monitored predictor
    predictor = HealthMonitoredPredictor(symbol='BTC/USDT')

    # Simulate prediction workflow
    print("\n📈 Simulating prediction workflow...")

    # Generate mock data for demonstration
    np.random.seed(42)
    n_samples = 100

    # Mock predictions (trading signals: 1=buy, 0=hold/sell)
    predictions = np.random.choice([0, 1], size=n_samples, p=[0.6, 0.4])

    # Mock actual outcomes (with some correlation to predictions for realism)
    actuals = np.random.choice([0, 1], size=n_samples, p=[0.55, 0.45])

    # Mock features
    n_features = 19
    features = np.random.randn(n_samples, n_features)

    # Create data dict
    prediction_data = {
        'predictions': predictions,
        'actuals': actuals,
        'features': features,
        'symbol': 'BTC/USDT',
        'timestamp': datetime.now()
    }

    # Make "prediction" with health monitoring
    result = predictor.predict_with_monitoring(prediction_data)

    print("✅ Prediction completed with health monitoring")

    # Check health status
    print("\n🏥 Checking model health status...")
    health_status = predictor.get_health_status()

    if health_status:
        model_data = health_status.get('models', {}).get(predictor.model_name, {})
        print(f"Model Status: {model_data.get('status', 'unknown')}")
        print(f"Active Alerts: {model_data.get('active_alerts', 0)}")
        print(f"Consecutive Failures: {model_data.get('consecutive_failures', 0)}")

        last_metrics = model_data.get('last_metrics')
        if last_metrics:
            print(".3f"            print(".3f"            print(".3f"
    # Check for alerts
    alerts = predictor.get_active_alerts()
    if alerts:
        print(f"\n🚨 Active Alerts: {len(alerts)}")
        for alert in alerts[:3]:  # Show first 3 alerts
            print(f"  {alert['level'].upper()}: {alert['message']}")
    else:
        print("\n✅ No active alerts")

    print("\n📊 Health monitoring integration example completed!")


def production_integration_template():
    """Template for production integration"""
    print("\n🔧 Production Integration Template")
    print("=" * 40)

    template_code = '''
# In your production prediction service (e.g., live_trading_bot.py)

from model_health_agent import ModelHealthAgent

class ProductionPredictor:
    def __init__(self):
        self.health_agent = ModelHealthAgent()
        self.models = {}

        # Register all production models
        self._register_production_models()

        # Start health monitoring
        self.health_agent.start_monitoring()

    def _register_production_models(self):
        """Register all models with health monitoring"""
        import os
        from pathlib import Path

        models_dir = Path("ml_crypto_predictor/production_models")
        if models_dir.exists():
            for model_file in models_dir.glob("*.pkl"):
                model_name = model_file.stem
                try:
                    # Load model metadata (you'd store this with the model)
                    metadata = self._load_model_metadata(model_name)

                    self.health_agent.register_model(
                        model_name=model_name,
                        model_path=str(model_file),
                        features=metadata.get('features', []),
                        hyperparameters=metadata.get('hyperparameters', {})
                    )

                    self.models[model_name] = model_file
                    logger.info(f"Registered {model_name} for health monitoring")

                except Exception as e:
                    logger.error(f"Failed to register {model_name}: {e}")

    def make_prediction(self, model_name, features, actual_outcome=None):
        """Make prediction with health monitoring"""
        try:
            # Load and use model
            if model_name in self.models:
                model = joblib.load(self.models[model_name])
                prediction = model.predict(features.reshape(1, -1))[0]

                # If we have actual outcome (e.g., from completed trade)
                if actual_outcome is not None:
                    self.health_agent.update_model_performance(
                        model_name,
                        np.array([prediction]),
                        np.array([actual_outcome]),
                        features.reshape(1, -1)
                    )

                return prediction

        except Exception as e:
            logger.error(f"Prediction failed for {model_name}: {e}")
            return None

    def get_model_health(self, model_name=None):
        """Get health status for monitoring dashboard"""
        return self.health_agent.get_health_report(model_name)

    def check_alerts(self):
        """Check for critical alerts that need immediate action"""
        alerts = self.health_agent.db.get_active_alerts()
        critical_alerts = [a for a in alerts if a.level == "CRITICAL"]

        if critical_alerts:
            # Send notifications, trigger retraining, etc.
            self._handle_critical_alerts(critical_alerts)

        return critical_alerts
'''

    print(template_code)


def monitoring_dashboard_example():
    """Example of using the monitoring dashboard"""
    print("\n📊 Monitoring Dashboard Example")
    print("=" * 35)

    dashboard_code = '''
# Start the health agent with API server
from model_health_agent import ModelHealthAgent, Config

# Enable API server
Config.ENABLE_API = True
Config.API_HOST = '0.0.0.0'
Config.API_PORT = 8001

agent = ModelHealthAgent()
agent.start_monitoring()

print("🚀 Model Health Dashboard available at: http://localhost:8001/dashboard")

# API Endpoints:
# GET / - Health check
# GET /health - All models status
# GET /health/{model_name} - Specific model health
# GET /alerts - Active alerts
# GET /dashboard - Interactive web dashboard

# Example API usage:
import requests

# Get all models health
response = requests.get("http://localhost:8001/health")
health_data = response.json()

# Get specific model alerts
response = requests.get("http://localhost:8001/alerts?model_name=btc_predictor")
alerts = response.json()
'''

    print(dashboard_code)


if __name__ == "__main__":
    # Run integration example
    example_integration()

    # Show production template
    production_integration_template()

    # Show dashboard example
    monitoring_dashboard_example()

    print("\n🎯 Integration examples completed!")
    print("\nNext steps:")
    print("1. Add model_health_agent.py to your requirements.txt")
    print("2. Integrate HealthMonitoredPredictor into your prediction pipeline")
    print("3. Set up monitoring dashboard for real-time health tracking")
    print("4. Configure alerts for automated retraining triggers")