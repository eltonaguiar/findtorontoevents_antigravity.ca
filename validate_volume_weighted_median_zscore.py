#!/usr/bin/env python3
"""
Quick validation for VolumeWeightedMedianZScoreStrategy.
This downloads real BTC-USD data and prints signal counts.
NOT a full 8-check validation — just sanity check that the code runs.
"""

import sys
import pandas as pd
import yfinance as yf
from baby_strategies.volume_weighted_median_zscore import (
    VolumeWeightedMedianZScoreStrategy,
    Signal,
)

def main():
    print("Downloading BTC-USD 5-year daily data...")
    df = yf.download("BTC-USD", period="5y", interval="1d")
    if df.empty:
        print("ERROR: No data downloaded")
        sys.exit(1)

    # yfinance returns MultiIndex columns (Price, Ticker). Drop the Ticker level.
    if isinstance(df.columns, pd.MultiIndex):
        df = df.droplevel('Ticker', axis=1)  # leaves columns: Close, High, Low, Open, Volume
    # Normalize to lowercase for strategy consumption
    df.columns = [c.lower() for c in df.columns]

    print(f"Downloaded {len(df)} days of data")
    strategy = VolumeWeightedMedianZScoreStrategy()
    signals = strategy.generate_signals(df, "BTCUSDT")

    print(f"\nTotal signals generated: {len(signals)}")
    longs = sum(1 for s in signals if s.direction == "BUY")
    shorts = sum(1 for s in signals if s.direction == "SELL")
    print(f"  Longs: {longs}")
    print(f"  Shorts: {shorts}")

    if len(signals) > 0:
        print("\nFirst 3 signals:")
        for i, sig in enumerate(signals[:3]):
            print(f"  {i+1}. {sig.direction} at {sig.entry_price:.2f} "
                  f"TP={sig.take_profit:.2f} SL={sig.stop_loss:.2f} "
                  f"reason: {sig.reason}")
    else:
        print("\nWARNING: No signals generated — check data/params?")

    # Simple sanity: expect >30 trades over 5 years for survival
    if len(signals) >= 30:
        print("\n[SANITY CHECK PASSED] >= 30 signals (min required)")
    else:
        print("\n[SANITY CHECK FAILED] < 30 signals — will not survive validation")

if __name__ == "__main__":
    main()
