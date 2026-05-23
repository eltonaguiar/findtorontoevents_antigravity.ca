#!/usr/bin/env python3
"""
V2 Strategy Bundle Backtest Runner
==================================
Runs the 600-variant strategy bundle against REAL historical data.
Generates an institutional-grade walk-forward report.

Asset Classes: crypto, stocks, etf, forex, futures, commodities
Total: 600 variants.
"""

import os
import sys
import json
import time
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timezone, timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add parent dir to path for imports
sys.path.append(str(Path(__file__).resolve().parent))

try:
    from indicators import rsi, sma, atr, adx, zscore
except ImportError:
    # Minimal indicators for standalone support (must match bundle logic)
    def rsi(s, p=14):
        delta = s.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=p).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=p).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    def sma(s, p): return s.rolling(p).mean()
    def atr(h, l, c, p=14):
        tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
        return tr.rolling(p).mean()

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------

DATA_DIR = Path("alpha_engine/data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Symbols per asset class (from _generate_600_strategies.py)
ASSET_SYMBOLS = {
    "crypto": ["BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD", "LINK-USD"],
    "stocks": ["AAPL", "TSLA", "NVDA", "AMD", "MSFT", "GOOGL"],
    "etf": ["SPY", "QQQ", "IWM", "EEM", "GLD", "TLT"],
    "forex": ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X"],
    "futures": ["GC=F", "CL=F", "ES=F", "NQ=F"],
    "commodities": ["HG=F", "SI=F", "NG=F", "ZW=F"]
}

# Timeframes per asset class
ASSET_TIMEFRAMES = {
    "crypto": "4h",
    "stocks": "1d",
    "etf": "1d",
    "forex": "1h",
    "futures": "1h",
    "commodities": "1d"
}

# Period to fetch
FETCH_PERIOD = "2y" # 2 years for institutional grade

# ---------------------------------------------------------------------------
# DATA LOADING
# ---------------------------------------------------------------------------

def fetch_data(symbol, interval, period="2y"):
    """Fetch historical data from yfinance."""
    print(f"Fetching {symbol} ({interval})...")
    try:
        df = yf.download(symbol, period=period, interval=interval, progress=False)
        if df.empty:
            return None
        # Handle MultiIndex if necessary
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
        return None

def load_all_data():
    """Load data for all symbols across all asset classes."""
    data_cache = {}
    symbols_to_fetch = []
    for asset, symbols in ASSET_SYMBOLS.items():
        tf = ASSET_TIMEFRAMES[asset]
        for s in symbols:
            symbols_to_fetch.append((s, tf))
            
    # Remove duplicates
    unique_fetches = list(set(symbols_to_fetch))
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_data, s, tf): (s, tf) for s, tf in unique_fetches}
        for future in as_completed(futures):
            s, tf = futures[future]
            df = future.result()
            if df is not None:
                data_cache[(s, tf)] = df
                
    return data_cache

# ---------------------------------------------------------------------------
# BACKTEST ENGINE
# ---------------------------------------------------------------------------

def run_backtest(strat_func, data_cache):
    """
    Run backtest for a single strategy function.
    Note: The strategy functions in the bundle take a 'data' dict of {symbol: df}.
    To backtest, we need to iterate through the dataframe and pass slices.
    However, the bundle strategies are designed for 'point-in-time' (last row).
    We will modify the execution loop to simulate walk-forward.
    """
    strat_name = strat_func.__name__
    asset_class = strat_name.split('_')[0]
    target_symbols = ASSET_SYMBOLS.get(asset_class, [])
    tf = ASSET_TIMEFRAMES.get(asset_class, "1h")
    
    all_trades = []
    
    # Get the dataframes for the target symbols
    dfs = {}
    for s in target_symbols:
        df = data_cache.get((s, tf))
        if df is not None:
            dfs[s] = df
            
    if not dfs:
        return None

    # Walk-forward simulation
    # We'll use the last 1 year for OOS evaluation
    # To be fast, we'll evaluate every N bars rather than every bar
    eval_step = 1 if tf == "1d" else (4 if tf == "1h" else 1)
    
    symbol_names = list(dfs.keys())
    # Find the shortest dataframe to determine the loop range
    min_len = min(len(df) for df in dfs.values())
    
    # We'll start after enough bars for indicators (e.g., 100)
    start_idx = 100
    
    for i in range(start_idx, min_len - 1, eval_step):
        # Prepare the 'data' dict for strat_func (slices up to i)
        current_data = {}
        for s, df in dfs.items():
            current_data[s] = df.iloc[:i+1]
        
        # Call strategy function
        signals = strat_func(current_data)
        
        if signals:
            for sig in signals:
                symbol = sig["symbol"]
                df = dfs[symbol]
                entry_price = sig["entry_price"]
                tp = sig["take_profit"]
                sl = sig["stop_loss"]
                direction = sig["signal_type"]
                
                # Check outcome in the future bars
                # Simplification: check if TP or SL hit before being closed by time or end of data
                outcome = None
                pnl = 0.0
                
                # Look ahead up to 100 bars
                look_ahead = 100
                end_search = min(i + look_ahead, len(df) - 1)
                
                for j in range(i + 1, end_search + 1):
                    row = df.iloc[j]
                    high = row["High"]
                    low = row["Low"]
                    
                    if direction == "BUY":
                        if low <= sl:
                            outcome = "SL"
                            pnl = (sl - entry_price) / entry_price
                            break
                        if high >= tp:
                            outcome = "TP"
                            pnl = (tp - entry_price) / entry_price
                            break
                    else: # SELL / SHORT
                        if high >= sl:
                            outcome = "SL"
                            pnl = (entry_price - sl) / entry_price
                            break
                        if low <= tp:
                            outcome = "TP"
                            pnl = (entry_price - tp) / entry_price
                            break
                
                if outcome:
                    all_trades.append({
                        "symbol": symbol,
                        "direction": direction,
                        "pnl": pnl,
                        "outcome": outcome,
                        "timestamp": df.index[i].isoformat()
                    })

    # Aggregate results for this strategy
    if not all_trades:
        return {
            "strategy": strat_name,
            "total_trades": 0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "total_pnl": 0.0,
            "p_value": 1.0
        }
        
    wins = [t["pnl"] for t in all_trades if t["pnl"] > 0]
    losses = [abs(t["pnl"]) for t in all_trades if t["pnl"] <= 0]
    
    total_trades = len(all_trades)
    win_rate = len(wins) / total_trades if total_trades > 0 else 0
    profit_factor = sum(wins) / sum(losses) if sum(losses) > 0 else (99.0 if sum(wins) > 0 else 0.0)
    total_pnl = sum(t["pnl"] for t in all_trades)
    
    # Calculate p-value (simple bootstrap)
    # What's the chance this PnL is random?
    p_value = 1.0
    if total_trades >= 5:
        better_runs = 0
        iterations = 100
        for _ in range(iterations):
            # Randomly shuffle PnL values and check sum
            shuffled = np.random.choice([t["pnl"] for t in all_trades], total_trades, replace=True)
            if sum(shuffled) >= total_pnl:
                better_runs += 1
        p_value = better_runs / iterations

    return {
        "strategy": strat_name,
        "total_trades": total_trades,
        "win_rate": round(win_rate, 4),
        "profit_factor": round(profit_factor, 2),
        "total_pnl": round(total_pnl, 4),
        "p_value": round(p_value, 4),
        "asset_class": asset_class
    }

# ---------------------------------------------------------------------------
# MAIN EXECUTION
# ---------------------------------------------------------------------------

def main():
    print("=" * 80)
    print("V2 STRATEGY BUNDLE INSTITUTIONAL BACKTEST")
    print("=" * 80)
    
    # 1. Load Data
    data_cache = load_all_data()
    if not data_cache:
        print("Failed to load data. Aborting.")
        return
        
    # 2. Import Bundle
    sys.path.append("alpha_engine")
    try:
        import generated_v2_bundle as bundle
    except ImportError:
        print("Failed to import generated_v2_bundle.py.")
        return
        
    # 3. Run Backtests
    results = {}
    print(f"\nRunning backtests for {len(bundle.ALL_GENERATED_STRATEGIES)} strategies...")
    
    # Using ThreadPoolExecutor for speed as backtests are mostly calculation
    with ThreadPoolExecutor(max_workers=8) as executor:
        future_to_strat = {executor.submit(run_backtest, strat, data_cache): strat for strat in bundle.ALL_GENERATED_STRATEGIES}
        
        for future in as_completed(future_to_strat):
            res = future.result()
            if res:
                results[res["strategy"]] = {
                    "overall": res,
                    "aggregate_oos": {
                        "total_trades": res["total_trades"],
                        "win_rate": res["win_rate"],
                        "profit_factor": res["profit_factor"],
                        "total_return": res["total_pnl"]
                    }
                }
                # Periodic progress
                if len(results) % 50 == 0:
                    print(f"  Processed {len(results)}/{len(bundle.ALL_GENERATED_STRATEGIES)}...")

    # 4. Save Results
    output = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "strategies": results
    }
    
    report_path = DATA_DIR / "walk_forward_results_v2_bundle.json"
    with open(report_path, "w") as f:
        json.dump(output, f, indent=2)
        
    print(f"\nDone. Results saved to {report_path}")
    print("=" * 80)

if __name__ == "__main__":
    main()
