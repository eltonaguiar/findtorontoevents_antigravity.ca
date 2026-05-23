#!/usr/bin/env python3
"""Asset class performance vs hedge fund benchmarks + ML training audit."""
import json
from collections import defaultdict
import statistics

# Load data
print("Loading closed_picks.json...")
with open('alpha_engine/data/closed_picks.json', 'r') as f:
    picks = json.load(f)
print(f"Loaded {len(picks)} total picks\n")

# Filter for meaningful sample (last 500 closed picks with PnL)
recent = [p for p in picks 
          if 'pnl_pct' in p and p['pnl_pct'] is not None 
          and 'resolved_at' in p][:500]

print(f"Analyzing {len(recent)} recent closed picks\n")

# Hedge fund benchmarks (annualized)
benchmarks = {
    'EQUITY_LS': {'return': 10, 'wr': 62, 'desc': 'Equity Long/Short'},
    'GLOBAL_MACRO': {'return': 12, 'wr': 58, 'desc': 'Global Macro'},
    'CTA_FUTURES': {'return': 15, 'wr': 55, 'desc': 'CTA/Futures'},
    'CRYPTO_HEDGE': {'return': 35, 'wr': 60, 'desc': 'Crypto Hedge (high vol)'},
}

# Asset class performance
stats = defaultdict(lambda: {'pnls': [], 'wins': 0, 'losses': 0, 'count': 0})

for p in recent:
    ac = (p.get('asset_class') or 'UNKNOWN').strip().upper()
    if not ac or ac == '':
        ac = 'UNKNOWN'
    pnl = p.get('pnl_pct', 0)
    stats[ac]['pnls'].append(pnl)
    stats[ac]['count'] += 1
    if pnl > 0:
        stats[ac]['wins'] += 1
    elif pnl < 0:
        stats[ac]['losses'] += 1

print("=" * 60)
print("ASSET CLASS PERFORMANCE (vs Hedge Fund Benchmarks)")
print("=" * 60)

for ac in sorted(stats.keys()):
    s = stats[ac]
    if s['count'] < 5:
        continue
    avg = statistics.mean(s['pnls']) if s['pnls'] else 0
    wr = (s['wins'] / s['count']) * 100 if s['count'] > 0 else 0
    ann_return = avg * (365/7) if avg != 0 else 0
    
    # Grade
    if ann_return > 20 and wr > 60:
        grade = '[EXCELLENT] Top-tier hedge fund'
    elif ann_return > 10 and wr > 55:
        grade = '[GOOD] Solid hedge fund performance'
    elif ann_return > 0 and wr > 50:
        grade = '[MARGINAL] Below hedge fund standards'
    elif ann_return > 0:
        grade = '[POOR] Needs major fixes'
    else:
        grade = '[LOSING] Must fix immediately'
    
    print(f'\n{ac} ({s["count"]} picks):')
    print(f"  Avg PnL: {avg:.2f}%, WR: {wr:.1f}%")
    print(f"  Annualized return: {ann_return:.1f}% (hedge fund range: 8-20%)")
    print(f"  Grade: {grade}")

print("\n" + "=" * 60)
print("ML ALGORITHM AUDIT")
print("=" * 60)

# Check ML model files
import os
ml_files = {
    'alpha_engine/ml_reviver_picks.json': 'ML Reviver (XGBoost/LightGBM)',
    'alpha_engine/enhanced_models/models/outcome_feedback_model.joblib': 'Outcome Feedback Model',
    'alpha_engine/hedge_fund_quality_gate.py': 'Hedge Fund Quality Gate',
    'alpha_engine/score_booster.py': 'Score Booster',
    'alpha_engine/forward_validator.py': 'Forward Validator',
}

print("\nML Model Files Status:")
for path, desc in ml_files.items():
    if os.path.exists(path):
        size = os.path.getsize(path)
        mtime = os.path.getmtime(path)
        import datetime
        dt = datetime.datetime.fromtimestamp(mtime)
        print(f"  ✅ {desc}")
        print(f"     Path: {path}")
        print(f"     Size: {size:,} bytes, Modified: {dt.strftime('%Y-%m-%d %H:%M')}")
    else:
        print(f"  ❌ {desc} - NOT FOUND: {path}")

# Check training scripts
print("\nML Training Scripts:")
train_scripts = [
    'alpha_engine/ml_reviver_workflow.py',
    'alpha_engine/train_ensemble.py',
    'alpha_engine/adaptive_trust_tuner.py',
    'alpha_engine/regime_flip_detector.py',
]

for script in train_scripts:
    if os.path.exists(script):
        print(f"  ✅ {script}")
    else:
        print(f"  ❌ {script} - NOT FOUND")

# Check forward validation (is ML being tested?)
print("\nForward Validation Status:")
forward_dir = 'alpha_engine/data/forward_tests'
if os.path.exists(forward_dir):
    files = os.listdir(forward_dir)
    print(f"  ✅ Forward test directory exists: {len(files)} files")
else:
    print(f"  ❌ Forward test directory not found")

# Check if models are being loaded/used
print("\nModel Loading Check (in production_scanner.py):")
with open('alpha_engine/production_scanner.py', 'r') as f:
    content = f.read()
    if 'ml_reviver' in content.lower() or 'ml_reviver_picks' in content:
        print("  ✅ ML Reviver picks are loaded in production")
    else:
        print("  ❌ ML Reviver picks NOT found in production_scanner.py")
    
    if 'forward_validator' in content:
        print("  ✅ Forward validator referenced")
    else:
        print("  ❌ Forward validator NOT referenced")

print("\n" + "=" * 60)
print("RECOMMENDATIONS")
print("=" * 60)
print("""
1. CRYPTO (if >25% WR): KEEP - marginal but positive
2. FOREX (if >50% WR): KEEP - decent performance
3. COMMODITY (0% WR): FIX IMMEDIATELY - exclude from HC
4. UNKNOWN (84.9% of picks): CRITICAL FIX - normalize asset_class
5. ML Models: Check if training is running (joblib files exist)
6. HC Filter: Lower threshold for crypto (30) vs forex (40)
""")
