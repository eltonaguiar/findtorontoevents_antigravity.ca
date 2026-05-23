"""
Institutional Alpha Engine - HF Policy Thresholds
Defines quality gates and validation constants for strategy promotion and data integrity.
"""

# Threshold A: "Lying" Strategy Gate
# Hard gate for strategies where Forward Return (FWD) vs. Backtest (BT) performance deviates significantly.
BT_FWD_MAX_DELTA = 0.15  # 15 percentage points
MIN_SAMPLE_SIZE = 20     # Minimum number of trades for statistical significance

def validate_threshold_a(bt_wr: float, fwd_wr: float, n_trades: int) -> bool:
    """
    Validates if a strategy passes Threshold A gating.
    Returns True if passed, False if flagged as "lying" or insufficient data.
    """
    if n_trades < MIN_SAMPLE_SIZE:
        return False
        
    delta = abs(bt_wr - fwd_wr)
    if delta > BT_FWD_MAX_DELTA:
        return False
        
    return True

if __name__ == "__main__":
    # Internal Unit Tests
    test_cases = [
        {"bt": 0.80, "fwd": 0.70, "n": 25, "expected": True},   # 10pp delta, n=25 -> Pass
        {"bt": 0.80, "fwd": 0.60, "n": 25, "expected": False},  # 20pp delta, n=25 -> Fail
        {"bt": 0.80, "fwd": 0.60, "n": 10, "expected": False},  # 20pp delta, n=10 -> Fail (Sample Size)
        {"bt": 0.60, "fwd": 0.70, "n": 30, "expected": True},   # 10pp delta (fwd better), n=30 -> Pass
    ]
    
    for i, tc in enumerate(test_cases):
        res = validate_threshold_a(tc["bt"], tc["fwd"], tc["n"])
        assert res == tc["expected"], f"Test Case {i} failed: got {res}, expected {tc['expected']}"
        
    print("All Threshold A validation tests passed.")
