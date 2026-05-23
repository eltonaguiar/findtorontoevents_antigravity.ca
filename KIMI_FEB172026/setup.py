"""
KIMI_FEB172026 - Setup Script
Initializes the trading system database and validates installation
"""

import sys
import subprocess
from pathlib import Path

def check_dependencies():
    """Check if required packages are installed"""
    required = ['numpy', 'pandas', 'sklearn', 'aiohttp']
    missing = []
    
    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    
    if missing:
        print(f"Missing dependencies: {', '.join(missing)}")
        print("Install with: pip install -r requirements.txt")
        return False
    
    print("✓ All dependencies installed")
    return True

def init_database():
    """Initialize SQLite database"""
    try:
        from sqlite_store import SQLiteStore
        store = SQLiteStore()
        print("✓ Database initialized")
        return True
    except Exception as e:
        print(f"✗ Database initialization failed: {e}")
        return False

def test_modules():
    """Test core modules"""
    modules = [
        'crypto_acceleration_engine',
        'ml_signal_ranker',
        'sqlite_store',
        'elimination_engine',
        'live_scanner'
    ]
    
    failed = []
    for mod in modules:
        try:
            __import__(mod)
            print(f"✓ {mod}")
        except Exception as e:
            print(f"✗ {mod}: {e}")
            failed.append(mod)
    
    return len(failed) == 0

def main():
    print("=" * 80)
    print("KIMI_FEB172026 - Trading System Setup")
    print("=" * 80)
    print()
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("✗ Python 3.8+ required")
        return 1
    print(f"✓ Python {sys.version_info.major}.{sys.version_info.minor}")
    
    # Check dependencies
    print("\nChecking dependencies...")
    if not check_dependencies():
        return 1
    
    # Test modules
    print("\nTesting modules...")
    if not test_modules():
        print("\nSome modules failed to load. Check errors above.")
        return 1
    
    # Initialize database
    print("\nInitializing database...")
    if not init_database():
        return 1
    
    # Create directories
    print("\nCreating directories...")
    dirs = ['data', 'config', 'templates', 'static/css', 'static/js']
    for d in dirs:
        Path(f"KIMI_FEB172026/{d}").mkdir(parents=True, exist_ok=True)
        print(f"  ✓ {d}")
    
    print("\n" + "=" * 80)
    print("Setup complete!")
    print("=" * 80)
    print("\nTo run the system:")
    print("  1. CLI mode:    python KIMI_FEB172026/live_scanner.py")
    print("  2. Web mode:    python -m uvicorn KIMI_FEB172026.live_scanner:create_app --reload")
    print()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
