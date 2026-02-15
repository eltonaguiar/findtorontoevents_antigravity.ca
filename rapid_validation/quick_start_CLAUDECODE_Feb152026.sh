#!/bin/bash
# Quick Start Script for Rapid Validation Engine
# CLAUDECODE_Feb152026

echo "========================================"
echo "RAPID VALIDATION ENGINE - Quick Start"
echo "CLAUDECODE_Feb152026"
echo "========================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.8+"
    exit 1
fi

echo "✅ Python found: $(python3 --version)"

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install -q ccxt pandas numpy mysql-connector-python

echo "✅ Dependencies installed"

# Create rapid_validation directory if needed
mkdir -p rapid_validation
cd rapid_validation

echo ""
echo "========================================"
echo "STEP 1: Generate Initial Signals"
echo "========================================"
python ../rapid_signal_generator.py --mode live --timeframe 5m

echo ""
echo "========================================"
echo "STEP 2: Validate Signals"
echo "========================================"
python ../fast_validator_CLAUDECODE_Feb152026.py

echo ""
echo "========================================"
echo "STEP 3: Generate Rankings"
echo "========================================"
python ../strategy_ranker_CLAUDECODE_Feb152026.py

echo ""
echo "========================================"
echo "STEP 4: Open Dashboard"
echo "========================================"
echo "Dashboard ready at:"
echo "  file://$(pwd)/dashboard_CLAUDECODE_Feb152026.html"
echo ""
echo "Opening in default browser..."

# Try to open in browser (cross-platform)
if [[ "$OSTYPE" == "darwin"* ]]; then
    open dashboard_CLAUDECODE_Feb152026.html
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    xdg-open dashboard_CLAUDECODE_Feb152026.html
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
    start dashboard_CLAUDECODE_Feb152026.html
fi

echo ""
echo "========================================"
echo "✅ Rapid Validation Engine Started!"
echo "========================================"
echo ""
echo "Next steps:"
echo "  1. Let it run for 1 week to collect data"
echo "  2. Check dashboard every day"
echo "  3. Watch for promoted strategies (60%+ WR)"
echo "  4. Paper trade winners before real money"
echo ""
echo "Auto-run schedule (GitHub Actions):"
echo "  - Signals: Every hour"
echo "  - Validation: Every 15 minutes"
echo "  - Rankings: Every 15 minutes"
echo ""
echo "========================================"
