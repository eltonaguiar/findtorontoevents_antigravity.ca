#!/usr/bin/env python3
"""
Register Crypto Hybrid Bundle in Forward Signal Scanner
Run this to add bundle strategies to production scanner
"""

import re
from pathlib import Path
from datetime import datetime

SCANNER_FILE = Path("incubator/backtest_team/forward_signal_scanner.py")

BUNDLE_REGISTRATION = '''
# ============================================
# CRYPTO HYBRID BUNDLE - AUTO-REGISTERED
# Date: {date}
# ============================================

# Import bundle strategies
try:
    from baby_strategies.williams_pr_trend_mr import WilliamsPRTrendMRStrategy
    WILLIAMS_AVAILABLE = True
except ImportError:
    WILLIAMS_AVAILABLE = False
    print("[WARN] Williams %R strategy not available")

try:
    from baby_strategies.connors_rsi2 import ConnorsRSI2Strategy
    CONNORS_AVAILABLE = True
except ImportError:
    CONNORS_AVAILABLE = False

try:
    from baby_strategies.bollinger_mean_reversion import BollingerMeanReversionStrategy
    BOLLINGER_AVAILABLE = True
except ImportError:
    BOLLINGER_AVAILABLE = False

try:
    from baby_strategies.orb_breakout import ORBBreakoutStrategy
    ORB_AVAILABLE = True
except ImportError:
    ORB_AVAILABLE = False

# Register bundle strategies
CRYPTO_HYBRID_BUNDLE = {{}}

if WILLIAMS_AVAILABLE:
    CRYPTO_HYBRID_BUNDLE["williams_pr_trend_mr"] = WilliamsPRTrendMRStrategy
if CONNORS_AVAILABLE:
    CRYPTO_HYBRID_BUNDLE["connors_rsi2"] = ConnorsRSI2Strategy
if BOLLINGER_AVAILABLE:
    CRYPTO_HYBRID_BUNDLE["bollinger_mean_rev"] = BollingerMeanReversionStrategy
if ORB_AVAILABLE:
    CRYPTO_HYBRID_BUNDLE["orb_breakout"] = ORBBreakoutStrategy

# Merge with existing TIER1 strategies
if CRYPTO_HYBRID_BUNDLE:
    TIER1_STRATEGIES.update(CRYPTO_HYBRID_BUNDLE)
    print(f"[OK] Crypto Hybrid Bundle registered: {{list(CRYPTO_HYBRID_BUNDLE.keys())}}")

# ============================================
'''.format(date=datetime.now().isoformat())

def register_bundle():
    print("=" * 80)
    print("REGISTERING CRYPTO HYBRID BUNDLE")
    print("=" * 80)
    
    if not SCANNER_FILE.exists():
        print(f"[ERROR] Scanner file not found: {SCANNER_FILE}")
        print("Creating new scanner file...")
        SCANNER_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SCANNER_FILE, 'w') as f:
            f.write("# Forward Signal Scanner\\n")
            f.write("TIER1_STRATEGIES = {}\\n")
    
    # Read current content
    with open(SCANNER_FILE, 'r') as f:
        content = f.read()
    
    # Check if already registered
    if "CRYPTO_HYBRID_BUNDLE" in content:
        print("[WARN] Bundle already registered. Updating...")
        # Remove old registration
        pattern = r'# =+\n# CRYPTO HYBRID BUNDLE.*?(?=\n# =+|\Z)'
        content = re.sub(pattern, '', content, flags=re.DOTALL)
    
    # Add registration at end of file
    content = content.rstrip() + "\\n\\n" + BUNDLE_REGISTRATION
    
    # Write back
    with open(SCANNER_FILE, 'w') as f:
        f.write(content)
    
    print(f"[OK] Bundle registered in: {SCANNER_FILE}")
    print("\\nRegistered strategies:")
    for strategy in ["williams_pr_trend_mr", "connors_rsi2", "bollinger_mean_rev", "orb_breakout"]:
        print(f"  - {strategy}")
    
    print("\\n[IMPORTANT] Restart forward signal scanner service to activate")

if __name__ == "__main__":
    register_bundle()
