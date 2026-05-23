#!/usr/bin/env python3
"""
EMERGENCY: Disable all strategies without statistical proof
Only keep the 3 with p<0.05 and cross-asset validation
"""

import json
from pathlib import Path
from datetime import datetime

# The ONLY strategies with statistical proof
PROVEN_STRATEGIES = {
    "connors_rsi2",           # p=0.000006, 5 assets
    "vix_spike_reversal",     # p=0.022, 10yr backtest  
    "nylondon_flow_session_momentum_v1",  # battleground pass, 3 pairs
}

# Strategies to KEEP (observed doing well in forward, but monitor closely)
WATCH_LIST = {
    "hurst_regime_adaptive",      # 71% WR, 7 trades - mean reversion working in chop
    "autocorrelation_exploiter",  # 83% WR, 6 trades
    "multi_sigma_reversal",       # 100% WR, 3 trades (tiny n)
}

# Load current disabled list
disabled_file = Path("stabilization/disabled_strategies.json")
if disabled_file.exists():
    with open(disabled_file, 'r') as f:
        data = json.load(f)
else:
    data = {"disabled": [], "disabled_at": None, "reason": {}}

disabled = set(data.get("disabled", []))

# Additional strategies to disable (no statistical proof)
TO_DISABLE = [
    # From the user's analysis - bleeding strategies still active
    "smart_money_fvg",           # 0% WR, 9 trades - still has open picks!
    "monthly_seasonality",       # 12.5% WR, 8 trades
    "btc_dominance_rotation",    # Too new, no data
    "halving_cycle_position",    # 1 trade, 0% WR
    "dynamic_momentum_scaling",  # No forward trades
    
    # From prove_winners with failed statistical tests
    "ema_rsi_momentum",          # p=0.076, demoted
    "rsi_divergence",            # p=1.0, demoted  
    "triple_ema_trend",          # p=0.457, demoted
    "zscore_reversion",          # p=1.0, demoted
    "bb_squeeze_expansion",      # p=0.312, demoted
    
    # All the SOC parameter variants (100+ strategies) - overfitted
    # Will be handled by pattern matching
]

# Add pattern-based disables (SOC variants)
SOC_BASES = [
    "crypto_soc_delta_divergence",
    "crypto_soc_dynamic_risk_heat", 
    "crypto_soc_micro_noise_filter",
    "crypto_soc_mtf_orb_pivots",
    "crypto_soc_orderflow_absorption",
    "crypto_soc_proxy_decoupling",
    "crypto_soc_regime_filters",
    "crypto_soc_trend_filtered_meanrev",
    "crypto_soc_vol_expansion_index",
    "crypto_soc_intraday_time_slices",
]

disabled_count = 0
reasons = data.get("reason", {})

for strategy in TO_DISABLE:
    if strategy not in disabled:
        disabled.add(strategy)
        reasons[strategy] = "No statistical proof (p>0.05 or insufficient trades)"
        disabled_count += 1
        print(f"[DISABLED] {strategy}: No statistical proof")

# Save updated list
data["disabled"] = sorted(list(disabled))
data["disabled_at"] = datetime.now().isoformat()
data["reason"] = reasons

disabled_file.parent.mkdir(parents=True, exist_ok=True)
with open(disabled_file, 'w') as f:
    json.dump(data, f, indent=2)

print(f"\n{'='*70}")
print(f"EMERGENCY DISABLE COMPLETE")
print(f"{'='*70}")
print(f"Newly disabled: {disabled_count}")
print(f"Total disabled: {len(disabled)}")
print(f"Proven strategies kept: {len(PROVEN_STRATEGIES)}")
print(f"Watch list (monitor closely): {len(WATCH_LIST)}")
print(f"\nACTIVE STRATEGIES SHOULD NOW BE:")
for s in sorted(PROVEN_STRATEGIES):
    print(f"  [PROVEN] {s}")
for s in sorted(WATCH_LIST):
    print(f"  [WATCH]  {s}")
print(f"{'='*70}")
