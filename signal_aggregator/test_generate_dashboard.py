#!/usr/bin/env python3
"""
Test script to generate dashboard data for Hub page integration.
This creates a mock dashboard_data.json file for testing.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

# Create mock dashboard data
dashboard_data = {
    "last_update": datetime.now().isoformat(),
    "total_systems": 20,
    "active_systems": 15,
    "total_consensus_signals": 8,
    "high_quality_signals": 5,
    "top_signals": [
        {
            "symbol": "BTCUSDT",
            "direction": "long",
            "confidence": 0.85,
            "agreement": 5,
            "quality_score": 92,
            "entry_price": 63450.25,
            "take_profit": 65800.00,
            "stop_loss": 61500.00,
            "timeframe": "1h",
            "systems": ["ml_crypto_predictor", "crypto_ml_edge", "meta_strategy", "strategy_dna", "mercury2"]
        },
        {
            "symbol": "ETHUSDT",
            "direction": "long",
            "confidence": 0.78,
            "agreement": 4,
            "quality_score": 87,
            "entry_price": 3450.75,
            "take_profit": 3650.00,
            "stop_loss": 3320.00,
            "timeframe": "4h",
            "systems": ["ml_crypto_predictor", "crypto_ml_edge", "strategy_dna", "baby_strategies"]
        },
        {
            "symbol": "SOLUSDT",
            "direction": "short",
            "confidence": 0.72,
            "agreement": 3,
            "quality_score": 81,
            "entry_price": 142.30,
            "take_profit": 135.00,
            "stop_loss": 148.00,
            "timeframe": "15m",
            "systems": ["crypto_ml_edge", "meta_strategy", "signal_engine"]
        }
    ],
    "system_status": [
        {
            "name": "ml_crypto_predictor",
            "status": "active",
            "last_signal": (datetime.now().replace(minute=0, second=0, microsecond=0)).isoformat(),
            "reliability": 0.88,
            "weight": 1.2,
            "category": "ml_heavy"
        },
        {
            "name": "crypto_ml_edge",
            "status": "active",
            "last_signal": (datetime.now().replace(minute=15, second=0, microsecond=0)).isoformat(),
            "reliability": 0.85,
            "weight": 1.1,
            "category": "ml_heavy"
        },
        {
            "name": "meta_strategy",
            "status": "active",
            "last_signal": (datetime.now().replace(minute=30, second=0, microsecond=0)).isoformat(),
            "reliability": 0.82,
            "weight": 1.0,
            "category": "strategy_dna"
        },
        {
            "name": "strategy_dna",
            "status": "active",
            "last_signal": (datetime.now().replace(minute=45, second=0, microsecond=0)).isoformat(),
            "reliability": 0.79,
            "weight": 0.9,
            "category": "strategy_dna"
        },
        {
            "name": "mercury2",
            "status": "active",
            "last_signal": (datetime.now().replace(minute=10, second=0, microsecond=0)).isoformat(),
            "reliability": 0.75,
            "weight": 0.8,
            "category": "ml_heavy"
        },
        {
            "name": "baby_strategies",
            "status": "active",
            "last_signal": (datetime.now().replace(minute=20, second=0, microsecond=0)).isoformat(),
            "reliability": 0.70,
            "weight": 0.7,
            "category": "strategy_dna"
        },
        {
            "name": "alpha_engine",
            "status": "inactive",
            "last_signal": (datetime.now() - timedelta(hours=3)).isoformat(),
            "reliability": 0.65,
            "weight": 0.6,
            "category": "trading_systems"
        },
        {
            "name": "signal_engine",
            "status": "active",
            "last_signal": (datetime.now().replace(minute=5, second=0, microsecond=0)).isoformat(),
            "reliability": 0.68,
            "weight": 0.7,
            "category": "signal_engines"
        }
    ],
    "performance_metrics": {
        "portfolio_pnl": 12.5,
        "sharpe_ratio": 1.42,
        "win_rate": 63.2,
        "max_drawdown": 8.7,
        "total_trades": 245,
        "best_system": "ml_crypto_predictor",
        "best_system_win_rate": 67.8
    }
}

# Save to file
output_dir = Path(__file__).parent / 'data'
output_dir.mkdir(exist_ok=True)
output_path = output_dir / 'dashboard_data.json'

with open(output_path, 'w') as f:
    json.dump(dashboard_data, f, indent=2)

print(f"Dashboard data saved to: {output_path}")
print(f"Total systems: {dashboard_data['total_systems']}")
print(f"Active systems: {dashboard_data['active_systems']}")
print(f"Consensus signals: {dashboard_data['total_consensus_signals']}")
print(f"High quality signals: {dashboard_data['high_quality_signals']}")