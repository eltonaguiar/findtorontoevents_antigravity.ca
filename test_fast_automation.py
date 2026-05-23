#!/usr/bin/env python3
"""
Fast Variants Automation Test
Tests that the fast trading variants work correctly for automation.
"""

import subprocess
import sys
import json
from pathlib import Path

def test_fast_stocks():
    """Test fast stocks competition."""
    print("🧪 Testing Fast Stocks Competition...")

    # Run the script
    result = subprocess.run([
        sys.executable,
        "STOCKS/competition/run_fast_competition.py"
    ], capture_output=True, text=True, cwd=Path(__file__).parent)

    if result.returncode != 0:
        print(f"❌ Fast stocks failed: {result.stderr}")
        return False

    print("✅ Fast stocks completed successfully")
    return True

def test_mercury2_fast():
    """Test mercury2 fast scanner."""
    print("🧪 Testing Mercury2 Fast...")

    # Run the script
    result = subprocess.run([
        sys.executable,
        "mercury2/mercury2_fast.py"
    ], capture_output=True, text=True, cwd=Path(__file__).parent)

    if result.returncode != 0:
        print(f"❌ Mercury2 fast failed: {result.stderr}")
        return False

    print("✅ Mercury2 fast completed successfully")
    return True

def test_dashboard_generation():
    """Test dashboard regeneration."""
    print("🧪 Testing Dashboard Generation...")

    # Run dashboard generator
    result = subprocess.run([
        sys.executable, "-m", "audit_trail.dashboard_generator"
    ], capture_output=True, text=True, cwd=Path(__file__).parent)

    if result.returncode != 0:
        print(f"❌ Dashboard generation failed: {result.stderr}")
        return False

    print("✅ Dashboard generation completed successfully")
    return True

def check_system_counts():
    """Check that fast variants appear in dashboard."""
    print("🧪 Checking System Counts...")

    try:
        with open("audit_trail/data/dashboard_payload.json", 'r') as f:
            data = json.load(f)

        systems = {s['name']: s for s in data.get('systems', [])}
        fast_stocks = systems.get('fast_stocks_competition', {})
        mercury_fast = systems.get('mercury2_fast', {})

        stocks_picks = fast_stocks.get('active_picks', 0)
        crypto_picks = mercury_fast.get('active_picks', 0)

        print(f"📊 Fast Stocks Competition: {stocks_picks} active picks")
        print(f"📊 Mercury2 Fast: {crypto_picks} active picks")

        if stocks_picks > 0 and crypto_picks > 0:
            print("✅ Both fast variants have active picks")
            return True
        else:
            print("❌ Missing active picks in fast variants")
            return False

    except Exception as e:
        print(f"❌ Failed to check system counts: {e}")
        return False

def main():
    """Run all automation tests."""
    print("🚀 Fast Variants Automation Test Suite")
    print("=" * 50)

    tests = [
        test_fast_stocks,
        test_mercury2_fast,
        test_dashboard_generation,
        check_system_counts
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1
        print()

    print("=" * 50)
    print(f"📊 Test Results: {passed}/{total} passed")

    if passed == total:
        print("🎉 All automation tests passed! Fast variants are ready for production.")
        return 0
    else:
        print("❌ Some tests failed. Check the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())