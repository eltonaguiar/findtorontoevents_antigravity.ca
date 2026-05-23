#!/bin/bash
#
# World-Class Crypto Prediction System — Production Runner
# =========================================================
#
# This script provides convenient commands for running the system.
# Usage: ./run_worldclass.sh [COMMAND] [OPTIONS]
#
# Commands:
#   train [--quick]           Train models (quick or full)
#   predict [--all]           Generate predictions
#   research [--all] [--quick] Run research framework
#   validate [--all]          Validate models
#   serve [--port PORT]       Start API server
#   status                    Show system status
#   dashboard [--output PATH] Export dashboard data
#   deploy [--version TAG]   Package for deployment
#   shell                     Start Python shell with environment
#
# Examples:
#   ./run_worldclass.sh train --quick
#   ./run_worldclass.sh predict --all
#   ./run_worldclass.sh research --all --quick
#   ./run_worldclass.sh serve --port 8000
#

set -e  # Exit on error

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check Python
check_python() {
    if ! command -v python &> /dev/null; then
        log_error "Python not found. Install Python 3.11+ and try again."
        exit 1
    fi

    PYTHON_VERSION=$(python -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    log_info "Python version: $PYTHON_VERSION"
}

# Install dependencies if needed
ensure_deps() {
    if [ ! -d "ml_crypto_predictor/venv" ]; then
        log_warn "Virtual environment not found. Using system Python."
        log_info "To create venv: python -m venv ml_crypto_predictor/venv"
    fi

    # Check for key packages
    if ! python -c "import torch" 2>/dev/null; then
        log_warn "PyTorch not installed. Install with: pip install torch"
    fi

    if ! python -c "import xgboost" 2>/dev/null; then
        log_warn "XGBoost not installed. Install with: pip install xgboost"
    fi
}

# Train
cmd_train() {
    log_info "Starting training..."
    shift  # Remove 'train' argument

    if [[ "$@" == *"--quick"* ]]; then
        python -m ml_crypto_predictor train --quick
    else
        python -m ml_crypto_predictor train --full
    fi

    log_success "Training complete"
}

# Predict
cmd_predict() {
    log_info "Generating predictions..."
    shift

    ARGS=""

    if [[ "$@" == *"--all"* ]]; then
        ARGS="$ARGS --all"
    fi

    if [[ "$@" == *"--pair"* ]]; then
        # Extract pair argument
        for arg in "$@"; do
            if [[ "$arg" == --*=* ]]; then
                ARGS="$ARGS $arg"
            fi
        done
    fi

    python -m ml_crypto_predictor predict $ARGS
    log_success "Predictions generated"
}

# Research
cmd_research() {
    log_info "Starting research pipeline..."
    shift

    ARGS=""

    if [[ "$@" == *"--all"* ]]; then
        ARGS="$ARGS --all"
    fi
    if [[ "$@" == *"--quick"* ]]; then
        ARGS="$ARGS --quick"
    fi

    python -m ml_crypto_predictor research $ARGS
    log_success "Research complete"
}

# Validate
cmd_validate() {
    log_info "Running validation..."
    shift

    ARGS=""

    if [[ "$@" == *"--all"* ]]; then
        ARGS="$ARGS --all"
    fi

    python -m ml_crypto_predictor validate $ARGS
    log_success "Validation complete"
}

# Serve
cmd_serve() {
    log_info "Starting inference API server..."
    shift

    ARGS=""

    if [[ "$@" == *"--port"* ]]; then
        for arg in "$@"; do
            if [[ "$arg" == --port=* ]]; then
                ARGS="$ARGS $arg"
            fi
        done
    fi

    python -m ml_crypto_predictor serve $ARGS
}

# Status
cmd_status() {
    log_info "System status:"
    python -m ml_crypto_predictor status
}

# Dashboard
cmd_dashboard() {
    log_info "Exporting dashboard data..."
    shift
    python -m ml_crypto_predictor dashboard "$@"
    log_success "Dashboard data exported"
}

# Deploy
cmd_deploy() {
    log_info "Packaging for deployment..."
    shift
    python -m ml_crypto_predictor deploy "$@"
    log_success "Deployment package created"
}

# Shell
cmd_shell() {
    log_info "Starting Python shell with environment..."
    python -i -c "
import sys
sys.path.insert(0, '$SCRIPT_DIR')
from ml_crypto_predictor.inference.predictor import WorldClassPredictor
print('\\nWorldClassPredictor available as: predictor = WorldClassPredictor()')
print('Try: predictor.predict_all([\"BTCUSDT\", \"ETHUSDT\"])')
"
}

# Main
main() {
    if [ $# -eq 0 ]; then
        echo "Usage: $0 [COMMAND] [OPTIONS]"
        echo ""
        echo "Commands:"
        echo "  train [--quick]           Train models"
        echo "  predict [--all]           Generate predictions"
        echo "  research [--all] [--quick] Run research framework"
        echo "  validate [--all]          Validate models"
        echo "  serve [--port PORT]       Start API server"
        echo "  status                    Show system status"
        echo "  dashboard [--output PATH] Export dashboard data"
        echo "  deploy [--version TAG]    Package for deployment"
        echo "  shell                     Start Python shell"
        echo ""
        echo "Examples:"
        echo "  $0 train --quick"
        echo "  $0 predict --all"
        echo "  $0 research --all --quick"
        echo "  $0 serve --port 8000"
        exit 1
    fi

    COMMAND="$1"
    shift

    check_python
    ensure_deps

    case "$COMMAND" in
        train)
            cmd_train "$@"
            ;;
        predict)
            cmd_predict "$@"
            ;;
        research)
            cmd_research "$@"
            ;;
        validate)
            cmd_validate "$@"
            ;;
        serve)
            cmd_serve "$@"
            ;;
        status)
            cmd_status
            ;;
        dashboard)
            cmd_dashboard "$@"
            ;;
        deploy)
            cmd_deploy "$@"
            ;;
        shell)
            cmd_shell
            ;;
        *)
            log_error "Unknown command: $COMMAND"
            echo "Use: train, predict, research, validate, serve, status, dashboard, deploy, shell"
            exit 1
            ;;
    esac
}

main "$@"
