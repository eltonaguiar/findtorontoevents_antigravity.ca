#!/usr/bin/env python3
"""
Backfill ml_features_at_entry for existing active picks that don't have it.

ONE-TIME operation to bridge the gap until CI naturally populates features
via scanner.py's compute_ml_features_at_entry().
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure alpha_engine is on the path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import DATA_DIR


def backfill_active_picks():
    """Backfill ml_features_at_entry for active picks that don't have it.

    For each active pick missing ml_features_at_entry:
    1. Fetch current OHLCV data for the symbol via yfinance (with try/except)
    2. Compute features using the same logic as scanner.py's compute_ml_features_at_entry()
    3. Attach to the pick
    4. Save updated active_picks.json

    This is a ONE-TIME operation to bridge the gap until CI naturally populates features.
    """
    import os
    fast_mode = bool(os.environ.get("ALPHA_FAST_MODE"))
    suffix = "_fast" if fast_mode else ""
    active_path = DATA_DIR / f"active_picks{suffix}.json"

    if not active_path.exists():
        print(f"[BACKFILL] No active picks file at {active_path}")
        return

    with open(active_path, encoding="utf-8") as f:
        active = json.load(f)

    if not isinstance(active, list):
        print("[BACKFILL] active_picks.json is not a list")
        return

    # Find picks missing ml_features_at_entry
    missing = [p for p in active if not p.get("ml_features_at_entry")]
    print(f"[BACKFILL] {len(missing)}/{len(active)} active picks missing ml_features_at_entry")

    if not missing:
        print("[BACKFILL] Nothing to backfill.")
        return

    # Import the compute function from scanner.py
    from scanner import compute_ml_features_at_entry

    # Group symbols to avoid duplicate downloads
    symbols = list(set(p.get("symbol", "") for p in missing if p.get("symbol")))
    print(f"[BACKFILL] Fetching OHLCV data for {len(symbols)} unique symbols...")

    # Fetch data via yfinance
    symbol_data = {}
    try:
        import yfinance as yf
        import pandas as pd
    except ImportError:
        print("[BACKFILL] yfinance/pandas not installed, cannot backfill")
        return

    for sym in symbols:
        try:
            ticker = yf.Ticker(sym)
            df = ticker.history(period="1y", interval="1d")
            if df is not None and not df.empty:
                symbol_data[sym] = df
                print(f"  Fetched {sym}: {len(df)} bars")
            else:
                print(f"  WARNING: No data for {sym}")
        except Exception as e:
            print(f"  ERROR fetching {sym}: {e}")

    # Backfill features
    backfilled = 0
    for pick in active:
        if pick.get("ml_features_at_entry"):
            continue  # Already has features

        sym = pick.get("symbol", "")
        if sym not in symbol_data:
            print(f"  SKIP {sym} (no OHLCV data available)")
            continue

        try:
            data_dict = {sym: symbol_data[sym]}
            features = compute_ml_features_at_entry(sym, data_dict, pick)
            if features:
                pick["ml_features_at_entry"] = features
                backfilled += 1
                n_features = len(features)
                print(f"  Backfilled {sym} ({pick.get('strategy', '?')}): {n_features} features")
            else:
                print(f"  WARNING: compute_ml_features_at_entry returned empty for {sym}")
        except Exception as e:
            print(f"  ERROR computing features for {sym}: {e}")

    # Save
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(active_path, "w", encoding="utf-8") as f:
        json.dump(active, f, indent=2, default=str, ensure_ascii=False)

    print(f"\n[BACKFILL] Done. Backfilled {backfilled}/{len(missing)} picks.")
    print(f"[BACKFILL] Saved to {active_path}")


if __name__ == "__main__":
    backfill_active_picks()
