#!/usr/bin/env python3
"""Quick verification that all new researchers are properly set up."""

import sys
from pathlib import Path

# Add base directory to path
base_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(base_dir))

print("Verifying new researcher framework...")
print("=" * 70)

try:
    from ml_crypto_predictor.researchers import (
        ExecutionResearcher,
        DataQualityResearcher,
        MomentumResearcher,
        MeanReversionResearcher,
        RiskResearcher,
        ValidationResearcher,
        AlternativeDataResearcher,
        RobustnessResearcher,
        GovernanceResearcher,
    )
    print("[OK] All imports successful")
except Exception as e:
    print(f"[ERROR] Import failed: {e}")
    sys.exit(1)

# Test instantiation and question generation
researchers_to_test = [
    ("ExecutionResearcher", "execution"),
    ("DataQualityResearcher", "data_quality"),
    ("MomentumResearcher", "momentum"),
    ("MeanReversionResearcher", "mean_reversion"),
    ("RiskResearcher", "risk_management"),
    ("ValidationResearcher", "validation"),
    ("AlternativeDataResearcher", "alternative_data"),
    ("RobustnessResearcher", "robustness"),
    ("GovernanceResearcher", "governance"),
]

total_questions = 0
all_ok = True

for class_name, expected_id in researchers_to_test:
    try:
        cls = globals()[class_name]
        instance = cls(config={"base_dir": base_dir})
        
        # Check ID
        if instance.researcher_id != expected_id:
            print(f"[ERROR] {class_name} ID mismatch: expected {expected_id}, got {instance.researcher_id}")
            all_ok = False
            continue
        
        # Get questions
        questions = instance.formulate_questions()
        total_questions += len(questions)
        
        print(f"[OK] {class_name}: {len(questions)} questions, ID={expected_id}")
        
    except Exception as e:
        print(f"[ERROR] {class_name} failed: {e}")
        all_ok = False

print("=" * 70)
print(f"Total research questions: {total_questions}")
print(f"Status: {'ALL OK' if all_ok else 'SOME FAILURES'}")
print("=" * 70)

sys.exit(0 if all_ok else 1)
