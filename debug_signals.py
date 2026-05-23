#!/usr/bin/env python3
"""
Debug script to check why strategies are generating 0 signals.
"""

import sys
from pathlib import Path
import pandas as pd
import yfinance as yf

# Add alpha_engine to path
sys.path.append(str(Path(__file__).parent / "alpha_engine"))

from alpha_engine.indicators import rsi, bollinger_bands
from alpha_engine.equity_rsi_divergence_mr import equity_rsi_divergence_mr
from alpha_engine.equity_bb_zscore_mr import equity_bb_zscore_mr
from alpha_engine.forex_carry_ppp import forex_carry_ppp


def fetch_equity_data(symbol: str, period: str = "2y") -> pd.DataFrame:
    """Download equity OHLCV data via yfinance."""
    df = yf.download(
        symbol, period=period, interval="1d", auto_adjust=True, progress=False
    )
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.dropna()
    return df


def main():
    # Test equity strategies
    print("Testing equity_rsi_divergence_mr on SPY...")
    data = {"SPY": fetch_equity_data("SPY", "2y")}
    df = data["SPY"]
    print(f"Data length: {len(df)}")

    if len(df) > 50:
        # Compute RSI
        rsi_14 = rsi(df["Close"], 14)
        print(f"Last 5 close prices: {df['Close'].tail().values}")
        print(f"Last 5 RSI values: {rsi_14.tail().values}")
        print(f"Current RSI: {rsi_14.iloc[-1]:.1f}")

        # Check basic conditions
        current_rsi = float(rsi_14.iloc[-1])
        print(f"RSI < 35 (bullish condition): {current_rsi < 35}")
        print(f"RSI > 65 (bearish condition): {current_rsi > 65}")

    signals = equity_rsi_divergence_mr(data)
    print(f"Generated {len(signals)} signals")
    if signals:
        print("Sample signal:", signals[0])
    else:
        print("No signals - divergence conditions not met")

    print("\nTesting equity_bb_zscore_mr on SPY...")
    if len(df) > 50:
        bb_data = bollinger_bands(df["Close"], 20, 2.0)
        current_close = float(df["Close"].iloc[-1])
        current_sma = float(bb_data["middle"].iloc[-1])
        rolling_std = df["Close"].rolling(20).std()
        current_std = float(rolling_std.iloc[-1])

        if current_std > 0:
            z_score = (current_close - current_sma) / current_std
            print(f"Current Z-score: {z_score:.2f}")
            print(f"Z-score < -1.2 (buy condition): {z_score < -1.2}")
            print(f"Z-score > 1.2 (sell condition): {z_score > 1.2}")

    signals = equity_bb_zscore_mr(data)
    print(f"Generated {len(signals)} signals")
    if signals:
        print("Sample signal:", signals[0])

    print("\nTesting forex_carry_ppp on EURUSD...")
    # For forex, need to handle the ticker format
    df_fx = yf.download("EURUSD=X", period="2y", interval="1d", progress=False)
    if isinstance(df_fx.columns, pd.MultiIndex):
        df_fx.columns = df_fx.columns.get_level_values(0)
    df_fx = df_fx.dropna()
    data_forex = {"EURUSD": df_fx}
    print(f"EURUSD data length: {len(df_fx)}")

    signals = forex_carry_ppp(data_forex)
    print(f"Generated {len(signals)} signals")
    if signals:
        print("Sample signal:", signals[0])


if __name__ == "__main__":
    main()
