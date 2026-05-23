#!/usr/bin/env python3
"""
Signal Debugger Agent
=====================

Diagnoses why strategies aren't generating signals.
Analyzes strategy conditions and data characteristics to identify mismatches.

Usage:
    python signal_debugger.py --strategy <name>
    python signal_debugger.py --all
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any
import numpy as np
import pandas as pd
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))


class SignalDebugger:
    """Debugs signal generation issues."""
    
    def __init__(self):
        self.incubator_path = Path(__file__).parent.parent
        self.agents_path = self.incubator_path / "agents"
        
    def load_strategy(self, strategy_name: str):
        """Load a strategy by name."""
        for agent_dir in self.agents_path.iterdir():
            if not agent_dir.is_dir():
                continue
            for py_file in agent_dir.glob("*.py"):
                if strategy_name in py_file.name:
                    meta_file = Path(str(py_file) + ".meta.json")
                    if meta_file.exists():
                        with open(meta_file) as f:
                            meta = json.load(f)
                        
                        # Import strategy
                        import importlib.util
                        spec = importlib.util.spec_from_file_location(f"strat_{strategy_name}", py_file)
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        
                        # Find strategy class
                        for attr_name in dir(module):
                            attr = getattr(module, attr_name)
                            if isinstance(attr, type) and attr_name.endswith('Strategy') and attr_name != 'Strategy':
                                return attr, meta, py_file
        return None, None, None
    
    def generate_test_data(self, days: int = 200, regime: str = 'mixed') -> pd.DataFrame:
        """Generate test data with specific characteristics."""
        rng = np.random.default_rng(42)
        n = days
        
        # Create synthetic returns with realistic properties
        returns = rng.normal(0.0005, 0.03, n)
        
        # Add some trend periods
        for i in range(50, 70):
            returns[i] += 0.02  # Bull run
        for i in range(120, 140):
            returns[i] -= 0.02  # Bear dip
        
        # Mean reversion periods
        for i in range(30, 40):
            returns[i] = -returns[i-1] * 0.5  # Mean reverting
        
        prices = 50000 * np.exp(np.cumsum(returns))
        
        dates = pd.date_range(end=datetime.now(), periods=n, freq='D')
        
        data = pd.DataFrame({
            'open': prices * (1 + rng.normal(0, 0.002, n)),
            'high': prices * (1 + abs(rng.normal(0, 0.015, n))),
            'low': prices * (1 - abs(rng.normal(0, 0.015, n))),
            'close': prices,
            'volume': rng.uniform(1000, 10000, n)
        }, index=dates)
        
        return data
    
    def debug_strategy(self, strategy_name: str) -> Dict:
        """Debug a single strategy."""
        print(f"\n{'='*60}")
        print(f"DEBUGGING: {strategy_name}")
        print('='*60)
        
        strategy_class, meta, py_file = self.load_strategy(strategy_name)
        if not strategy_class:
            print(f"ERROR: Could not load strategy {strategy_name}")
            return {"error": "not_found"}
        
        print(f"Loaded from: {py_file}")
        print(f"Strategy type: {meta.get('strategy_type', 'unknown')}")
        print(f"Expected indicators: {meta.get('indicators', [])}")
        
        # Generate test data
        data = self.generate_test_data(days=200)
        print(f"\nTest data: {len(data)} bars")
        print(f"  Price range: ${data['close'].min():,.0f} - ${data['close'].max():,.0f}")
        print(f"  Avg volume: {data['volume'].mean():,.0f}")
        
        # Initialize strategy
        strategy = strategy_class()
        
        # Track signal generation
        signals_log = []
        indicator_snapshots = []
        
        min_bars = 50
        
        for end_idx in range(min_bars, len(data)):
            window = data.iloc[:end_idx + 1]
            
            try:
                signals = strategy.generate_signals(window, symbol="BTCUSDT")
                
                if signals:
                    for sig in signals:
                        signals_log.append({
                            'bar': end_idx,
                            'date': window.index[-1],
                            'price': window['close'].iloc[-1],
                            'signal': sig
                        })
                
                # Capture indicator values every 20 bars for analysis
                if end_idx % 20 == 0:
                    snapshot = self._capture_indicators(strategy, window)
                    if snapshot:
                        indicator_snapshots.append({
                            'bar': end_idx,
                            'date': window.index[-1],
                            'values': snapshot
                        })
                        
            except Exception as e:
                print(f"  Error at bar {end_idx}: {e}")
        
        # Analysis
        print(f"\n{'='*60}")
        print("ANALYSIS")
        print('='*60)
        
        print(f"\nTotal signals generated: {len(signals_log)}")
        
        if signals_log:
            for log in signals_log[:5]:
                sig = log['signal']
                print(f"\n  Signal at bar {log['bar']} ({log['date'].strftime('%Y-%m-%d')}):")
                print(f"    Direction: {sig.direction}")
                print(f"    Confidence: {getattr(sig, 'confidence', 'N/A')}")
                print(f"    Entry: ${sig.entry_price:,.2f}")
                print(f"    Reason: {sig.reason[:100]}...")
        else:
            print("\n  NO SIGNALS GENERATED!")
            print("\n  Possible causes:")
            print("    1. Indicator thresholds too strict")
            print("    2. Missing required data (e.g., whale data, SPX data)")
            print("    3. Signal conditions never met in test data")
            
            # Show indicator ranges
            if indicator_snapshots:
                print("\n  Indicator values from test data:")
                last_snapshot = indicator_snapshots[-1]['values']
                for key, value in last_snapshot.items():
                    print(f"    {key}: {value}")
        
        # Show data characteristics
        print(f"\nData characteristics:")
        print(f"  Volatility (std): {data['close'].pct_change().std():.4f}")
        print(f"  Max single-day move: {data['close'].pct_change().abs().max():.2%}")
        
        return {
            "strategy": strategy_name,
            "signals_count": len(signals_log),
            "signals": signals_log[:10],
            "indicator_snapshots": indicator_snapshots[-3:]
        }
    
    def _capture_indicators(self, strategy, window: pd.DataFrame) -> Dict:
        """Try to extract indicator values from strategy."""
        snapshot = {}
        
        # Common indicator checks
        try:
            # RSI
            if hasattr(strategy, '_calculate_rsi') or hasattr(strategy, 'rsi_period'):
                delta = window['close'].diff()
                gains = delta.where(delta > 0, 0)
                losses = -delta.where(delta < 0, 0)
                avg_gains = gains.rolling(window=14).mean()
                avg_losses = losses.rolling(window=14).mean()
                rs = avg_gains / avg_losses
                rsi = 100 - (100 / (1 + rs))
                snapshot['RSI'] = round(rsi.iloc[-1], 2)
            
            # ATR
            if hasattr(strategy, '_calculate_atr') or hasattr(strategy, 'atr_period'):
                high, low, close = window['high'], window['low'], window['close']
                tr1 = high - low
                tr2 = abs(high - close.shift())
                tr3 = abs(low - close.shift())
                tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
                atr = tr.rolling(window=14).mean()
                snapshot['ATR'] = round(atr.iloc[-1], 2)
            
            # Price vs EMAs
            ema20 = window['close'].ewm(span=20).mean()
            ema50 = window['close'].ewm(span=50).mean()
            snapshot['Price/EMA20'] = round(window['close'].iloc[-1] / ema20.iloc[-1], 4)
            snapshot['Price/EMA50'] = round(window['close'].iloc[-1] / ema50.iloc[-1], 4)
            
            # Volume
            vol_sma = window['volume'].rolling(window=20).mean()
            snapshot['Volume/SMA20'] = round(window['volume'].iloc[-1] / vol_sma.iloc[-1], 2)
            
        except Exception:
            pass
        
        return snapshot
    
    def debug_all(self) -> List[Dict]:
        """Debug all strategies."""
        strategies = []
        
        for agent_dir in self.agents_path.iterdir():
            if not agent_dir.is_dir():
                continue
            for py_file in agent_dir.glob("*.py"):
                meta_file = Path(str(py_file) + ".meta.json")
                if meta_file.exists():
                    with open(meta_file) as f:
                        meta = json.load(f)
                    strategies.append(meta.get('strategy_name'))
        
        results = []
        for name in strategies:
            result = self.debug_strategy(name)
            results.append(result)
        
        return results


def main():
    parser = argparse.ArgumentParser(description="Signal Debugger Agent")
    parser.add_argument("--strategy", help="Specific strategy to debug")
    parser.add_argument("--all", action="store_true", help="Debug all strategies")
    args = parser.parse_args()
    
    debugger = SignalDebugger()
    
    if args.strategy:
        debugger.debug_strategy(args.strategy)
    elif args.all:
        debugger.debug_all()
    else:
        # Debug the two main Baby Strats
        print("\nDebugging Baby Strat #1 and #2...")
        debugger.debug_strategy("crypto_rsi_whaleconfirmed_v1")
        debugger.debug_strategy("crossasset_btcspx_corrbreakdown_v1")


if __name__ == "__main__":
    main()
