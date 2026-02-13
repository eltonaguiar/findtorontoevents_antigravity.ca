#!/usr/bin/env python3
"""
Python Bridge for PHP Prediction API
Loads XGBoost model and returns predictions

Usage:
    python predict_bridge.py <input_json_file> <output_json_file>
"""

import json
import sys
import warnings
import os

warnings.filterwarnings('ignore')

try:
    import xgboost as xgb
    import numpy as np
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    print(json.dumps({'error': 'XGBoost not installed'}))
    sys.exit(1)


def load_model(model_path):
    """Load XGBoost model from file"""
    if not os.path.exists(model_path):
        return None
    
    try:
        model = xgb.XGBClassifier()
        model.load_model(model_path)
        return model
    except Exception as e:
        return None


def predict(model, features):
    """Make prediction using loaded model"""
    try:
        # Convert features to numpy array
        X = np.array([features])
        
        # Get probability
        probability = model.predict_proba(X)[0][1]  # Probability of class 1 (hit TP)
        
        # Get prediction
        prediction = model.predict(X)[0]
        
        return {
            'probability': float(probability),
            'prediction': int(prediction),
            'ok': True
        }
    except Exception as e:
        return {
            'error': str(e),
            'ok': False
        }


def main():
    if len(sys.argv) < 3:
        print(json.dumps({'error': 'Usage: predict_bridge.py <input_file> <output_file>'}))
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    # Read input
    try:
        with open(input_file, 'r') as f:
            input_data = json.load(f)
    except Exception as e:
        with open(output_file, 'w') as f:
            json.dump({'error': f'Failed to read input: {str(e)}'}, f)
        sys.exit(1)
    
    # Extract parameters
    model_path = input_data.get('model_path')
    features = input_data.get('features', [])
    
    if not model_path or not features:
        with open(output_file, 'w') as f:
            json.dump({'error': 'Missing model_path or features'}, f)
        sys.exit(1)
    
    # Load model and predict
    model = load_model(model_path)
    if model is None:
        with open(output_file, 'w') as f:
            json.dump({'error': 'Failed to load model'}, f)
        sys.exit(1)
    
    result = predict(model, features)
    
    # Write output
    with open(output_file, 'w') as f:
        json.dump(result, f)
    
    sys.exit(0)


if __name__ == '__main__':
    main()
