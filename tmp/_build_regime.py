# Generator script for regime_detector.py
import os

target = r'e:/findtorontoevents_antigravity.ca/ml_crypto_predictor/enhanced_models/regime_detector.py'

# Read old file to extract _compute_features
old = open(target, encoding='utf-8').read()
cf_start = old.index('    def _compute_features')
cf_end = old.index('    def train(', cf_start)
compute_features = old[cf_start:cf_end]

print(f"Extracted _compute_features: {len(compute_features)} chars")
print("Building new file...")
