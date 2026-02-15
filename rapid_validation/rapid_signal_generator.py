#!/usr/bin/env python3
"""
RAPID SIGNAL GENERATOR - High-Frequency Testing Engine
========================================================
Generates 100+ signals per day across 10 strategies on 5min candles
Compresses 3 months of testing into 2-3 weeks

Usage:
    python rapid_signal_generator.py --mode live
    python rapid_signal_generator.py --mode backtest --days 7
"""

import ccxt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
import json
import os
import sys
import time
import argparse
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict

# Import existing strategies
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'crypto_signals'))
from strategies import (
    rsi, atr, bollinger_bands, macd, ema, supertrend,
    strategy_rsi_momentum, strategy_macd_crossover, strategy_supertrend,
    strategy_triple_ema, strategy_adx_ema, strategy_bb_squeeze_breakout,
    strategy_donchian_breakout, strategy_volume_momentum
)

@dataclass
class RapidSignal:
    """Lightweight signal for rapid testing"""
    strategy: str
    pair: str
    timeframe: str
    signal_type: str  # 'long' or 'short'
    entry_price: float
    tp_scalp: float   # 0.5% TP
    sl_scalp: float   # 0.3% SL
    tp_swing: float   # 2.0% TP
    sl_swing: float   # 1.0% SL
    tp_position: float  # 5.0% TP
    sl_position: float  # 2.5% SL
    confidence: int   # 0-100
    indicators: Dict
    timestamp: datetime
    signal_id: str

    def to_dict(self):
        d = asdict(self)
        d['timestamp'] = self.timestamp.isoformat()
        return d


class RapidSignalGenerator:
    """
    Generates rapid-fire signals on 5min candles for quick validation
    """

    # High-volatility pairs for fastest signal resolution
    RAPID_TEST_PAIRS = [
        'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT',
        'DOGE/USDT', 'PEPE/USDT', 'WIF/USDT', 'BONK/USDT',
        'AVAX/USDT', 'MATIC/USDT', 'LINK/USDT', 'UNI/USDT'
    ]

    TIMEFRAMES = ['5m', '15m', '1h']  # Multiple timeframes for parallel testing

    def __init__(self, exchange_id='binance'):
        self.exchange_class = getattr(ccxt, exchange_id)
        self.exchange = self.exchange_class({'enableRateLimit': True})
        self.cache_dir = 'rapid_cache'
        os.makedirs(self.cache_dir, exist_ok=True)

    def fetch_recent_ohlcv(self, symbol: str, timeframe: str = '5m', limit: int = 500) -> pd.DataFrame:
        """Fetch recent OHLCV data with caching"""
        cache_file = os.path.join(
            self.cache_dir,
            f"{symbol.replace('/', '_')}_{timeframe}_recent.csv"
        )

        # Use cache if less than 5 minutes old
        if os.path.exists(cache_file):
            mtime = os.path.getmtime(cache_file)
            if time.time() - mtime < 300:  # 5 minutes
                df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
                return df

        # Fetch fresh data
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            df.to_csv(cache_file)
            return df
        except Exception as e:
            print(f"  Error fetching {symbol} {timeframe}: {e}")
            return None

    def calculate_tp_sl(self, entry_price: float, signal_type: str, atr_value: float) -> Dict:
        """Calculate TP/SL for scalp, swing, position strategies"""
        if signal_type == 'long':
            return {
                'tp_scalp': entry_price * 1.005,    # 0.5%
                'sl_scalp': entry_price * 0.997,    # 0.3%
                'tp_swing': entry_price * 1.020,    # 2.0%
                'sl_swing': entry_price * 0.990,    # 1.0%
                'tp_position': entry_price * 1.050, # 5.0%
                'sl_position': entry_price * 0.975  # 2.5%
            }
        else:  # short
            return {
                'tp_scalp': entry_price * 0.995,
                'sl_scalp': entry_price * 1.003,
                'tp_swing': entry_price * 0.980,
                'sl_swing': entry_price * 1.010,
                'tp_position': entry_price * 0.950,
                'sl_position': entry_price * 1.025
            }

    # ========================================================================
    # STRATEGY WRAPPERS (Run on 5min candles for rapid signals)
    # ========================================================================

    def strategy_rsi_momentum_5m(self, df: pd.DataFrame) -> Optional[RapidSignal]:
        """RSI Momentum on 5min candles"""
        if len(df) < 50:
            return None

        signal = strategy_rsi_momentum(df)
        if signal['action'] == 'hold':
            return None

        entry_price = df['close'].iloc[-1]
        atr_val = atr(df, 14).iloc[-1]
        tp_sl = self.calculate_tp_sl(entry_price, signal['action'], atr_val)

        return RapidSignal(
            strategy='RSI_Momentum_5m',
            pair=df.attrs.get('symbol', 'UNKNOWN'),
            timeframe='5m',
            signal_type=signal['action'],
            entry_price=entry_price,
            confidence=signal.get('confidence', 50),
            indicators={'rsi': signal['indicators']['rsi']},
            timestamp=datetime.now(timezone.utc),
            signal_id=f"RSI5m_{df.attrs.get('symbol', 'UNKNOWN')}_{int(time.time())}",
            **tp_sl
        )

    def strategy_macd_crossover_5m(self, df: pd.DataFrame) -> Optional[RapidSignal]:
        """MACD Crossover on 5min"""
        if len(df) < 50:
            return None

        signal = strategy_macd_crossover(df)
        if signal['action'] == 'hold':
            return None

        entry_price = df['close'].iloc[-1]
        atr_val = atr(df, 14).iloc[-1]
        tp_sl = self.calculate_tp_sl(entry_price, signal['action'], atr_val)

        return RapidSignal(
            strategy='MACD_Crossover_5m',
            pair=df.attrs.get('symbol', 'UNKNOWN'),
            timeframe='5m',
            signal_type=signal['action'],
            entry_price=entry_price,
            confidence=signal.get('confidence', 50),
            indicators={'macd': signal['indicators']['macd'], 'signal': signal['indicators']['signal']},
            timestamp=datetime.now(timezone.utc),
            signal_id=f"MACD5m_{df.attrs.get('symbol', 'UNKNOWN')}_{int(time.time())}",
            **tp_sl
        )

    def strategy_supertrend_5m(self, df: pd.DataFrame) -> Optional[RapidSignal]:
        """Supertrend on 5min"""
        if len(df) < 50:
            return None

        signal = strategy_supertrend(df)
        if signal['action'] == 'hold':
            return None

        entry_price = df['close'].iloc[-1]
        atr_val = atr(df, 14).iloc[-1]
        tp_sl = self.calculate_tp_sl(entry_price, signal['action'], atr_val)

        return RapidSignal(
            strategy='Supertrend_5m',
            pair=df.attrs.get('symbol', 'UNKNOWN'),
            timeframe='5m',
            signal_type=signal['action'],
            entry_price=entry_price,
            confidence=signal.get('confidence', 50),
            indicators={'supertrend': signal['indicators']['supertrend']},
            timestamp=datetime.now(timezone.utc),
            signal_id=f"ST5m_{df.attrs.get('symbol', 'UNKNOWN')}_{int(time.time())}",
            **tp_sl
        )

    def strategy_bb_squeeze_5m(self, df: pd.DataFrame) -> Optional[RapidSignal]:
        """Bollinger Band Squeeze on 5min"""
        if len(df) < 50:
            return None

        signal = strategy_bb_squeeze_breakout(df)
        if signal['action'] == 'hold':
            return None

        entry_price = df['close'].iloc[-1]
        atr_val = atr(df, 14).iloc[-1]
        tp_sl = self.calculate_tp_sl(entry_price, signal['action'], atr_val)

        return RapidSignal(
            strategy='BB_Squeeze_5m',
            pair=df.attrs.get('symbol', 'UNKNOWN'),
            timeframe='5m',
            signal_type=signal['action'],
            entry_price=entry_price,
            confidence=signal.get('confidence', 50),
            indicators={'bb_width': signal['indicators'].get('bb_width', 0)},
            timestamp=datetime.now(timezone.utc),
            signal_id=f"BB5m_{df.attrs.get('symbol', 'UNKNOWN')}_{int(time.time())}",
            **tp_sl
        )

    def strategy_volume_momentum_5m(self, df: pd.DataFrame) -> Optional[RapidSignal]:
        """Volume Momentum on 5min"""
        if len(df) < 50:
            return None

        signal = strategy_volume_momentum(df)
        if signal['action'] == 'hold':
            return None

        entry_price = df['close'].iloc[-1]
        atr_val = atr(df, 14).iloc[-1]
        tp_sl = self.calculate_tp_sl(entry_price, signal['action'], atr_val)

        return RapidSignal(
            strategy='Volume_Momentum_5m',
            pair=df.attrs.get('symbol', 'UNKNOWN'),
            timeframe='5m',
            signal_type=signal['action'],
            entry_price=entry_price,
            confidence=signal.get('confidence', 50),
            indicators={'volume_sma': signal['indicators'].get('volume_sma', 0)},
            timestamp=datetime.now(timezone.utc),
            signal_id=f"VOL5m_{df.attrs.get('symbol', 'UNKNOWN')}_{int(time.time())}",
            **tp_sl
        )

    def strategy_mean_reversion_5m(self, df: pd.DataFrame) -> Optional[RapidSignal]:
        """Mean Reversion (RSI < 40 oversold) on 5min"""
        if len(df) < 50:
            return None

        rsi_val = rsi(df, 14).iloc[-1]
        entry_price = df['close'].iloc[-1]

        # Only fire on oversold (RSI < 40)
        if rsi_val < 40:
            atr_val = atr(df, 14).iloc[-1]
            tp_sl = self.calculate_tp_sl(entry_price, 'long', atr_val)

            return RapidSignal(
                strategy='Mean_Reversion_5m',
                pair=df.attrs.get('symbol', 'UNKNOWN'),
                timeframe='5m',
                signal_type='long',
                entry_price=entry_price,
                confidence=int((40 - rsi_val) * 2.5),  # Lower RSI = higher confidence
                indicators={'rsi': rsi_val},
                timestamp=datetime.now(timezone.utc),
                signal_id=f"MR5m_{df.attrs.get('symbol', 'UNKNOWN')}_{int(time.time())}",
                **tp_sl
            )

        return None

    # ========================================================================
    # MAIN SIGNAL GENERATION LOOP
    # ========================================================================

    def generate_signals(self, pairs: List[str] = None, timeframe: str = '5m') -> List[RapidSignal]:
        """Generate signals for all strategies across all pairs"""
        if pairs is None:
            pairs = self.RAPID_TEST_PAIRS

        strategies = [
            self.strategy_rsi_momentum_5m,
            self.strategy_macd_crossover_5m,
            self.strategy_supertrend_5m,
            self.strategy_bb_squeeze_5m,
            self.strategy_volume_momentum_5m,
            self.strategy_mean_reversion_5m
        ]

        all_signals = []

        print(f"\n{'='*60}")
        print(f"RAPID SIGNAL GENERATION - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"{'='*60}")
        print(f"Pairs: {len(pairs)} | Strategies: {len(strategies)} | Timeframe: {timeframe}")
        print(f"{'='*60}\n")

        for pair in pairs:
            print(f"Analyzing {pair}...")

            # Fetch data
            df = self.fetch_recent_ohlcv(pair, timeframe)
            if df is None or len(df) < 50:
                print(f"  ⚠️  Insufficient data")
                continue

            df.attrs['symbol'] = pair

            # Run all strategies
            for strategy_fn in strategies:
                try:
                    signal = strategy_fn(df)
                    if signal:
                        all_signals.append(signal)
                        print(f"  ✅ {signal.strategy}: {signal.signal_type.upper()} @ ${signal.entry_price:.4f} (conf: {signal.confidence}%)")
                except Exception as e:
                    print(f"  ❌ {strategy_fn.__name__}: {e}")

            time.sleep(0.1)  # Rate limit protection

        print(f"\n{'='*60}")
        print(f"TOTAL SIGNALS GENERATED: {len(all_signals)}")
        print(f"{'='*60}\n")

        return all_signals

    def save_signals(self, signals: List[RapidSignal], output_file: str = 'rapid_signals.json'):
        """Save signals to JSON file"""
        output_path = os.path.join('rapid_validation', output_file)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        data = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'signal_count': len(signals),
            'signals': [s.to_dict() for s in signals]
        }

        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"✅ Saved {len(signals)} signals to {output_path}")


def main():
    parser = argparse.ArgumentParser(description='Rapid Signal Generator')
    parser.add_argument('--mode', choices=['live', 'backtest'], default='live')
    parser.add_argument('--timeframe', default='5m', help='Candle timeframe')
    parser.add_argument('--pairs', nargs='+', help='Specific pairs to test')
    args = parser.parse_args()

    generator = RapidSignalGenerator()
    signals = generator.generate_signals(pairs=args.pairs, timeframe=args.timeframe)
    generator.save_signals(signals)


if __name__ == '__main__':
    main()
