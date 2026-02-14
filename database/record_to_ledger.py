#!/usr/bin/env python3
"""
Record predictions from any system to unified ledger
Called by GitHub Actions after each system runs
"""

import argparse
import json
import sys
from datetime import datetime
from typing import Dict

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unified_prediction_ledger import UnifiedPredictionLedger, PredictionRecord
from mysql_core import MySQLDatabase


def load_predictions(input_file: str) -> list:
    """Load predictions from JSON file"""
    with open(input_file, 'r') as f:
        return json.load(f)


def transform_v2_ledger(data: dict) -> PredictionRecord:
    """Transform V2 Ledger output to unified format"""
    return PredictionRecord(
        prediction_id=f"v2_{data['timestamp']}_{data['symbol']}",
        system='v2_scientific_ledger',
        system_version=data.get('version', '1.0'),
        asset_class='stock',
        symbol=data['symbol'],
        direction='buy',
        entry_price=data['price'],
        target_price=data['price'] * 1.06,  # 6% target typical
        stop_price=data['price'] * 0.97,    # 3% stop typical
        confidence=data['score'] / 100,
        score=data['score'],
        factors=data.get('factors', {}),
        prediction_time=datetime.fromisoformat(data['timestamp']),
        expected_duration_hours=data.get('timeframe_hours', 168),
        status='active'
    )


def transform_cryptoalpha(data: dict) -> PredictionRecord:
    """Transform CryptoAlpha output to unified format"""
    return PredictionRecord(
        prediction_id=f"ca_{data['timestamp']}_{data['symbol']}",
        system='cryptoalpha_pro',
        system_version='2.0',
        asset_class='crypto',
        symbol=data['symbol'],
        direction=data['signal'].lower(),
        entry_price=data['price'],
        target_price=data.get('target'),
        stop_price=data.get('stop'),
        confidence=data.get('confidence', 0.5),
        score=data.get('score'),
        factors={'regime': data.get('regime'), 'rr_ratio': data.get('rr_ratio')},
        prediction_time=datetime.fromisoformat(data['timestamp']),
        expected_duration_hours=48,
        status='active'
    )


def transform_meme_v2(data: dict) -> PredictionRecord:
    """Transform Meme Strategy V2 output to unified format"""
    return PredictionRecord(
        prediction_id=data['signal_id'],
        system='meme_coin_v2',
        system_version='2.0',
        asset_class='crypto',
        symbol=data['symbol'],
        direction='buy',
        entry_price=data['entry'],
        target_price=data['target'],
        stop_price=data['stop'],
        confidence=data['confidence'],
        score=data['score'],
        factors=data.get('factors', {}),
        prediction_time=datetime.fromisoformat(data['timestamp']),
        expected_duration_hours=data.get('time_exit', 24),
        status='active'
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--system', required=True, help='System name')
    parser.add_argument('--input', required=True, help='Input JSON file')
    parser.add_argument('--db-host', required=True)
    parser.add_argument('--db-user', required=True)
    parser.add_argument('--db-pass', required=True)
    parser.add_argument('--db-name', default='ejaguiar1_memecoin')
    
    args = parser.parse_args()
    
    # Connect to database
    db = MySQLDatabase()
    db.config['host'] = args.db_host
    db.config['user'] = args.db_user
    db.config['password'] = args.db_pass
    db.config['database'] = args.db_name
    
    # Create ledger
    ledger = UnifiedPredictionLedger(db)
    
    # Load predictions
    predictions = load_predictions(args.input)
    
    # Transform and record each prediction
    transformers = {
        'v2_scientific_ledger': transform_v2_ledger,
        'cryptoalpha_pro': transform_cryptoalpha,
        'meme_coin_v2': transform_meme_v2,
    }
    
    transformer = transformers.get(args.system)
    if not transformer:
        print(f"Unknown system: {args.system}")
        sys.exit(1)
    
    success_count = 0
    for pred_data in predictions:
        try:
            record = transformer(pred_data)
            if ledger.record_prediction(record):
                success_count += 1
        except Exception as e:
            print(f"Error recording prediction: {e}")
    
    print(f"Recorded {success_count}/{len(predictions)} predictions for {args.system}")


if __name__ == '__main__':
    main()
