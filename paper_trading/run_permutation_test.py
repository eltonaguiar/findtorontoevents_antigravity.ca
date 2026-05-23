#!/usr/bin/env python3
"""
Quick-start script for running permutation portfolio tests.

Usage:
    python run_permutation_test.py           # Full run
    python run_permutation_test.py --init    # Initialize portfolios only
    python run_permutation_test.py --analyze # Analyze only
    python run_permutation_test.py --report  # Generate report only
"""
import argparse
import subprocess
import sys
from pathlib import Path

def run_command(cmd: list, description: str):
    """Run a command and print status."""
    print(f"\n{'='*60}")
    print(f"📌 {description}")
    print(f"{'='*60}")
    
    result = subprocess.run(cmd, capture_output=False, text=True)
    if result.returncode != 0:
        print(f"❌ Failed: {description}")
        return False
    print(f"✅ Completed: {description}")
    return True

def main():
    parser = argparse.ArgumentParser(description="Run Permutation Portfolio Tests")
    parser.add_argument("--init", action="store_true", help="Initialize portfolios only")
    parser.add_argument("--analyze", action="store_true", help="Run analysis only")
    parser.add_argument("--report", action="store_true", help="Generate report only")
    parser.add_argument("--full", action="store_true", help="Full run (init + analyze + report)")
    
    args = parser.parse_args()
    
    # Default to full run if no args
    if not any([args.init, args.analyze, args.report, args.full]):
        args.full = True
    
    success = True
    
    if args.full or args.init:
        success &= run_command(
            [sys.executable, "-m", "permutation_portfolio_manager", "--mode", "all"],
            "Initializing and running system & strategy portfolios"
        )
    
    if args.full or args.analyze:
        success &= run_command(
            [sys.executable, "-m", "permutation_analyzer", "--report", "full", "--export-html"],
            "Analyzing portfolio performance"
        )
    
    if args.full or args.report:
        report_path = Path("data/permutation_report.html")
        if report_path.exists():
            print(f"\n{'='*60}")
            print("📊 REPORT GENERATED")
            print(f"{'='*60}")
            print(f"View report at: {report_path.absolute()}")
            print(f"\nOpen in browser:")
            print(f"  file://{report_path.absolute()}")
    
    print(f"\n{'='*60}")
    if success:
        print("✅ All tasks completed successfully!")
    else:
        print("❌ Some tasks failed. Check logs above.")
    print(f"{'='*60}\n")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
