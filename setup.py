#!/usr/bin/env python3
"""
================================================================================
CryptoAlpha Pro - Setup Script
================================================================================
One-command setup for the entire system.

Usage:
    python setup.py
================================================================================
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """Run a shell command"""
    print(f"\n{'='*60}")
    print(f"{description}...")
    print(f"{'='*60}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"❌ Failed: {description}")
        return False
    print(f"✅ {description} complete")
    return True


def main():
    print("""
╔══════════════════════════════════════════════════════════════════╗
║              CRYPTOALPHA PRO - SETUP WIZARD                      ║
╚══════════════════════════════════════════════════════════════════╝

This script will set up the entire system:
  1. Install Python dependencies
  2. Create required directories
  3. Run initial backtests
  4. Start the web interface

Press Ctrl+C to cancel, or wait 3 seconds to continue...
""")
    
    try:
        import time
        time.sleep(3)
    except KeyboardInterrupt:
        print("\n❌ Setup cancelled")
        return
    
    # Step 1: Install dependencies
    if not run_command("pip install -r requirements.txt", "Installing Python dependencies"):
        return
    
    # Step 2: Create directories
    print("\nCreating directories...")
    dirs = ['data', 'backtest_results', 'logs', 'web_app/static']
    for d in dirs:
        Path(d).mkdir(exist_ok=True)
    print("✅ Directories created")
    
    # Step 3: Test imports
    print("\nTesting imports...")
    try:
        import numpy, pandas, fastapi
        print("✅ All imports successful")
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return
    
    # Step 4: Run quick test
    print("\nRunning quick war test...")
    run_command("python quick_war_test.py", "Quick war test")
    
    print("""
╔══════════════════════════════════════════════════════════════════╗
║                    SETUP COMPLETE!                               ║
╚══════════════════════════════════════════════════════════════════╝

Next steps:
  1. Start web interface:
     uvicorn web_app.main:app --reload

  2. Or run war room:
     python war_room_v2.py

  3. Access dashboard at:
     http://localhost:8000/dashboard

  4. View API docs at:
     http://localhost:8000/docs

For Docker deployment:
  docker-compose up -d

Good luck, commander! ⚔️
""")


if __name__ == '__main__':
    main()
