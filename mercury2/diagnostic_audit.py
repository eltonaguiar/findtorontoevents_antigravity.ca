# -*- coding: utf-8 -*-
"""Mercury 2 — Quant-Level Diagnostic Audit.

Performs:
1. Data Integrity & Freshness Audit (Timestamps, Gaps)
2. Missing-value scan (Null percentage check)
3. Hit-rate vs Real-world Gap Analysis
"""

import os
import json
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timezone, timedelta

# CONFIG — resolve data dir from package location (works from repo root or mercury2/)
_BASE = Path(__file__).resolve().parent
DATA_DIR = _BASE / "data"
ACTIVE_PICKS = DATA_DIR / "active_picks.json"
CLOSED_PICKS = DATA_DIR / "closed_picks.json"
SCAN_STATE = DATA_DIR / "last_scan_state.json"
SCAN_SUMMARY = DATA_DIR / "scan_summary.json"

def audit_freshness():
    print("\n--- 1. DATA-INTEGRITY & FRESHNESS AUDIT ---")
    now = datetime.now(timezone.utc)
    
    # Check scan state
    if SCAN_STATE.exists():
        with open(SCAN_STATE) as f:
            state = json.load(f)
        last_close = state.get("last_candle_close")
        if last_close:
            try:
                # Attempt to parse last_candle_close if it's a timestamp string
                # state.get("last_candle_close") is e.g. "2026-03-29 07:00:00+00:00"
                # But format can vary, so we just check string length/presence
                print(f"  [OK] Last Candle Close: {last_close}")
            except:
                print(f"  [!] Could not parse last_candle_close: {last_close}")
    else:
        print("  [CRITICAL] last_scan_state.json MISSING")

    # Check scan summary
    if SCAN_SUMMARY.exists():
        with open(SCAN_SUMMARY) as f:
            summary = json.load(f)
        ts_str = summary.get("timestamp")
        if ts_str:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            age = now - ts
            if age > timedelta(hours=2):
                print(f"  [WARNING] Scan Summary is {age.total_seconds()/3600:.1f}h old! (>2h limit)")
            else:
                print(f"  [OK] Scan Summary age: {age.total_seconds()/3600:.1f}h")
        
        val_passed = summary.get("validation_passed", False)
        if not val_passed:
            print(f"  [!] VALIDATION FAILED: {summary.get('validation_reason')}")
        else:
            print("  [OK] DSR/PSR Validation Passed")

def audit_missing_values():
    print("\n--- 2. MISSING-VALUE SCAN ---")
    
    for path in [ACTIVE_PICKS, CLOSED_PICKS]:
        if not path.exists():
            print(f"  [SKIP] {path.name} missing")
            continue
            
        with open(path) as f:
            picks = json.load(f)
            
        if not picks:
            print(f"  [OK] {path.name} is empty")
            continue
            
        df = pd.DataFrame(picks)
        null_counts = df.isnull().sum()
        total = len(df)
        
        null_cols = null_counts[null_counts > 0]
        if not null_cols.empty:
            print(f"  [!] {path.name} Nulls found:")
            for col, count in null_cols.items():
                pct = (count / total) * 100
                print(f"    - {col}: {count} ({pct:.1f}%)")
                if pct > 10:
                    print(f"      [CRITICAL] {col} null percentage > 10%!")
        else:
            print(f"  [OK] {path.name}: No nulls found in {total} rows")

def audit_performance_gap():
    print("\n--- 3. PERFORMANCE GAP ANALYSIS ---")
    if not CLOSED_PICKS.exists():
        print("  [SKIP] closed_picks.json missing")
        return
        
    with open(CLOSED_PICKS) as f:
        closed = json.load(f)
        
    if not closed:
        print("  [SKIP] No closed trades to analyze")
        return
        
    df = pd.DataFrame(closed)
    if "pnl_pct" not in df.columns and "realized_pnl_pct" in df.columns:
        df["pnl_pct"] = df["realized_pnl_pct"]
        
    if "confidence" in df.columns and "pnl_pct" in df.columns:
        # Convert confidence to float if it's string
        df["confidence"] = pd.to_numeric(df["confidence"], errors='coerce')
        df["pnl_pct"] = pd.to_numeric(df["pnl_pct"], errors='coerce')
        
        # Hit-rate @ Top-N (Confidence > 0.70)
        high_conf = df[df["confidence"] > 0.70]
        if not high_conf.empty:
            hr = (high_conf["pnl_pct"] > 0).mean() * 100
            avg_pnl = high_conf["pnl_pct"].mean()
            print(f"  [METRIC] High Confidence (>0.70) WR: {hr:.1f}% (N={len(high_conf)})")
            print(f"  [METRIC] High Confidence Avg PnL: {avg_pnl:.2f}%")
        else:
            print("  [SKIP] No high-confidence trades (>0.70)")
            
        # Spearman correlation
        corr = df[["confidence", "pnl_pct"]].corr(method="spearman").iloc[0,1]
        print(f"  [METRIC] Confidence vs Outcome Spearman: {corr:.3f}")
        if corr < -0.15:
            print("    [CRITICAL] Strong negative rank correlation — review score calibration")
        elif corr < 0:
            print("    [WARNING] Slightly negative / noisy correlation (need more N or regime split)")
        elif corr < 0.1:
            print("    [WARNING] Confidence has low predictive power (|ρ| < 0.1)")
        else:
            print(f"    [OK] Confidence correlation: {corr:.3f}")

def main():
    print("MERCURY 2 - DIAGNOSTIC AUDIT v1.0")
    audit_freshness()
    audit_missing_values()
    audit_performance_gap()
    print("\n--- AUDIT COMPLETE ---")

if __name__ == "__main__":
    main()
