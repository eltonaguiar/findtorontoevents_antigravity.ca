import json
import sys
import os
import math
from pathlib import Path
import numpy as np
import pandas as pd
from arch.bootstrap import CircularBlockBootstrap

# Portability: derive ROOT from the script location rather than hardcoding
# a Windows path. Lets the tool run on Linux CI and macOS dev boxes.
ROOT = str(Path(__file__).resolve().parents[1])
sys.path.insert(0, ROOT)

DATA = os.path.join(ROOT, "audit_dashboard", "data", "dashboard_data.json")

def compute_sharpe(pnls):
    if len(pnls) < 2:
        return 0.0
    s = np.std(pnls, ddof=1)
    if s == 0:
        return 0.0
    return (np.mean(pnls) / s) * math.sqrt(252)

def main():
    with open(DATA, "r", encoding="utf-8") as f:
        d = json.load(f)
    
    recent_closed = d.get("picks", {}).get("recent_closed", [])
    
    # We will block bootstrap by strategy
    # A block bootstrap normally takes a time series. If we use CircularBlockBootstrap on a time series of PnLs:
    # First, let's group pnls by asset class.
    
    assets = ["CRYPTO", "EQUITY", "FOREX", "COMMODITY"]
    results = {}
    
    for asset in assets:
        picks = [p for p in recent_closed if (p.get("asset_class") or "").upper() == asset and p.get("pnl_pct") is not None]
        pnls = np.array([float(p.get("pnl_pct")) for p in picks])
        
        if len(pnls) < 10:
            results[asset] = {"error": "Not enough data"}
            continue
            
        bs = CircularBlockBootstrap(block_size=10, x=pnls)
        
        def sr_func(x):
            return compute_sharpe(x)
            
        try:
            ci = bs.conf_int(sr_func, reps=1000, method="percentile", size=0.95)
            
            results[asset] = {
                "n": len(pnls),
                "sharpe_raw": compute_sharpe(pnls),
                "ci_lower_95": float(np.squeeze(ci)[0]),
                "ci_upper_95": float(np.squeeze(ci)[1])
            }
        except Exception as e:
            results[asset] = {"error": str(e)}

    out_dir = os.path.join(ROOT, "tools", "data")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "block_bootstrap_results_2026_04_20.json")
    
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
        
    print("Block bootstrap complete.")
    for k, v in results.items():
        if "error" not in v:
            print(f"{k}: SR={v['sharpe_raw']:.2f}, 95% CI=[{v['ci_lower_95']:.2f}, {v['ci_upper_95']:.2f}]")

if __name__ == "__main__":
    main()
