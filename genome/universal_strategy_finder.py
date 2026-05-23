#!/usr/bin/env python3
"""
Universal Strategy Finder - Multi-Symbol Pattern Discovery
===========================================================

Finds trading strategies that work across ALL crypto symbols simultaneously,
rather than being optimized for specific coins.

Key Innovation:
- Tests each DNA pattern against 20+ symbols
- Scores based on consistency across all symbols
- Finds universal market inefficiencies, not coin-specific patterns

Usage:
    python universal_strategy_finder.py --run      # Full analysis
    python universal_strategy_finder.py --today    # What would work today
    python universal_strategy_finder.py --live     # Generate live signals
"""

import json
import random
import numpy as np
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('UniversalFinder')


# Top 30 liquid crypto pairs
UNIVERSE = [
    'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'ADAUSDT', 'DOTUSDT', 
    'LINKUSDT', 'MATICUSDT', 'AVAXUSDT', 'UNIUSDT', 'ATOMUSDT',
    'LTCUSDT', 'BCHUSDT', 'ALGOUSDT', 'VETUSDT', 'FILUSDT',
    'TRXUSDT', 'ETCUSDT', 'XLMUSDT', 'NEARUSDT', 'ARBUSDT',
    'OPUSDT', 'APTUSDT', 'GRTUSDT', 'STXUSDT', 'IMXUSDT',
    'RUNEUSDT', 'INJUSDT', 'RENDERUSDT', 'TIAUSDT', 'SEIUSDT'
]


@dataclass
class UniversalDNA:
    """DNA that works across all symbols."""
    name: str
    genes: Dict
    symbol_performance: Dict[str, Dict] = field(default_factory=dict)
    universal_score: float = 0.0
    consistency_score: float = 0.0  # Low variance across symbols
    robustness_score: float = 0.0   # Works in different regimes
    
    def calculate_scores(self):
        """Calculate universal applicability scores."""
        if not self.symbol_performance:
            return
        
        win_rates = [p['win_rate'] for p in self.symbol_performance.values()]
        sharpes = [p.get('sharpe', 0) for p in self.symbol_performance.values()]
        
        # Universal score: high avg WR with low variance
        avg_wr = np.mean(win_rates)
        wr_std = np.std(win_rates)
        self.universal_score = avg_wr * (1 - wr_std)  # Penalize high variance
        
        # Consistency: all symbols profitable
        profitable = sum(1 for wr in win_rates if wr > 0.5)
        self.consistency_score = profitable / len(win_rates)
        
        # Robustness: works in different market conditions
        avg_sharpe = np.mean(sharpes)
        self.robustness_score = min(avg_sharpe / 2, 1.0)  # Cap at 1.0


class DataFetcher:
    """Fetch price data for all symbols."""
    
    def __init__(self):
        self.cache = {}
        self.cache_time = None
    
    _SPOT_BASES = [
        "https://api.binance.com", "https://api1.binance.com",
        "https://data-api.binance.vision", "https://api.binance.us",
    ]
    _FAPI_BASES = [
        "https://fapi.binance.com", "https://fapi1.binance.com",
        "https://fapi2.binance.com",
    ]

    def fetch_all_symbols(self, timeframe: str = '1h', limit: int = 500) -> Dict[str, List]:
        """Fetch OHLCV data for all symbols in universe (with endpoint failover)."""
        data = {}

        for symbol in UNIVERSE:
            for base in self._SPOT_BASES:
                try:
                    url = f"{base}/api/v3/klines"
                    params = {
                        'symbol': symbol,
                        'interval': timeframe,
                        'limit': limit
                    }
                    response = requests.get(url, params=params, timeout=10)
                    if response.status_code in (451, 403):
                        continue  # geo-blocked, try next
                    if response.status_code == 200:
                        klines = response.json()
                        parsed = [{
                            'timestamp': int(k[0]),
                            'open': float(k[1]),
                            'high': float(k[2]),
                            'low': float(k[3]),
                            'close': float(k[4]),
                            'volume': float(k[5])
                        } for k in klines]
                        data[symbol] = parsed
                        break  # success
                except Exception as e:
                    logger.warning(f"Failed to fetch {symbol} from {base}: {e}")

        self.cache = data
        self.cache_time = datetime.now()
        return data

    def fetch_current_prices(self) -> Dict[str, float]:
        """Fetch current prices for all symbols (with endpoint failover)."""
        prices = {}

        for base in self._SPOT_BASES:
            try:
                url = f"{base}/api/v3/ticker/price"
                response = requests.get(url, timeout=10)
                if response.status_code in (451, 403):
                    continue
                if response.status_code == 200:
                    for item in response.json():
                        if item['symbol'] in UNIVERSE:
                            prices[item['symbol']] = float(item['price'])
                    return prices  # success
            except Exception as e:
                logger.error(f"Failed to fetch prices from {base}: {e}")

        return prices

    def fetch_funding_rates(self) -> Dict[str, float]:
        """Fetch funding rates for all symbols (with endpoint failover)."""
        funding = {}

        for base in self._FAPI_BASES:
            try:
                url = f"{base}/fapi/v1/premiumIndex"
                response = requests.get(url, timeout=10)
                if response.status_code in (451, 403):
                    continue
                if response.status_code == 200:
                    for item in response.json():
                        if item['symbol'] in UNIVERSE:
                            funding[item['symbol']] = float(item['lastFundingRate'])
                    return funding  # success
            except Exception as e:
                logger.error(f"Failed to fetch funding from {base}: {e}")

        return funding


class PatternSimulator:
    """Simulate strategy patterns on historical data."""
    
    def __init__(self, data: Dict[str, List]):
        self.data = data
    
    def calculate_indicators(self, ohlcv: List) -> Dict:
        """Calculate technical indicators."""
        closes = [c['close'] for c in ohlcv]
        highs = [c['high'] for c in ohlcv]
        lows = [c['low'] for c in ohlcv]
        volumes = [c['volume'] for c in ohlcv]
        
        indicators = {}
        
        # EMAs
        indicators['ema_12'] = self._ema(closes, 12)
        indicators['ema_26'] = self._ema(closes, 26)
        indicators['ema_50'] = self._ema(closes, 50)
        indicators['ema_200'] = self._ema(closes, 200)
        
        # RSI
        indicators['rsi'] = self._rsi(closes, 14)
        
        # MACD
        indicators['macd'], indicators['macd_signal'] = self._macd(closes)
        
        # Bollinger Bands
        indicators['bb_upper'], indicators['bb_middle'], indicators['bb_lower'] = self._bollinger(closes)
        
        # ATR
        indicators['atr'] = self._atr(highs, lows, closes)
        
        # Volume MA
        indicators['volume_ma'] = self._sma(volumes, 20)
        
        # Returns
        indicators['returns'] = [(closes[i] - closes[i-1]) / closes[i-1] 
                                  for i in range(1, len(closes))]
        
        return indicators
    
    def _ema(self, data: List, period: int) -> List:
        """Calculate EMA."""
        if len(data) < period:
            return data
        multiplier = 2 / (period + 1)
        ema = [sum(data[:period]) / period]
        for price in data[period:]:
            ema.append((price - ema[-1]) * multiplier + ema[-1])
        return [ema[0]] * (period - 1) + ema
    
    def _sma(self, data: List, period: int) -> List:
        """Calculate SMA."""
        result = []
        for i in range(len(data)):
            if i < period - 1:
                result.append(sum(data[:i+1]) / (i+1))
            else:
                result.append(sum(data[i-period+1:i+1]) / period)
        return result
    
    def _rsi(self, closes: List, period: int = 14) -> List:
        """Calculate RSI."""
        deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]
        
        rsi = [50] * (period + 1)  # Default
        
        for i in range(period, len(gains)):
            avg_gain = sum(gains[i-period:i]) / period
            avg_loss = sum(losses[i-period:i]) / period
            
            if avg_loss == 0:
                rsi.append(100)
            else:
                rs = avg_gain / avg_loss
                rsi.append(100 - (100 / (1 + rs)))
        
        return [50] + rsi
    
    def _macd(self, closes: List) -> Tuple[List, List]:
        """Calculate MACD."""
        ema_12 = self._ema(closes, 12)
        ema_26 = self._ema(closes, 26)
        macd = [ema_12[i] - ema_26[i] for i in range(len(closes))]
        signal = self._ema(macd, 9)
        return macd, signal
    
    def _bollinger(self, closes: List, period: int = 20, std_dev: float = 2) -> Tuple[List, List, List]:
        """Calculate Bollinger Bands."""
        middle = self._sma(closes, period)
        upper = []
        lower = []
        
        for i in range(len(closes)):
            if i < period - 1:
                upper.append(closes[i])
                lower.append(closes[i])
            else:
                std = np.std(closes[i-period+1:i+1])
                upper.append(middle[i] + std_dev * std)
                lower.append(middle[i] - std_dev * std)
        
        return upper, middle, lower
    
    def _atr(self, highs: List, lows: List, closes: List, period: int = 14) -> List:
        """Calculate Average True Range."""
        tr = [highs[0] - lows[0]]
        for i in range(1, len(highs)):
            tr1 = highs[i] - lows[i]
            tr2 = abs(highs[i] - closes[i-1])
            tr3 = abs(lows[i] - closes[i-1])
            tr.append(max(tr1, tr2, tr3))
        
        return self._ema(tr, period)
    
    def simulate_strategy(self, symbol: str, dna: Dict) -> Dict:
        """Simulate a DNA strategy on symbol data."""
        if symbol not in self.data:
            return {'win_rate': 0, 'profit_factor': 0, 'sharpe': 0}
        
        ohlcv = self.data[symbol]
        if len(ohlcv) < 50:
            return {'win_rate': 0, 'profit_factor': 0, 'sharpe': 0}
        
        indicators = self.calculate_indicators(ohlcv)
        
        # Extract gene parameters
        tf = dna.get('timeframe', '1h')
        entry_logic = dna.get('entry_logic', 'rsi_oversold')
        exit_logic = dna.get('exit_logic', 'rsi_overbought')
        
        trades = []
        in_position = False
        entry_price = 0
        
        for i in range(50, len(ohlcv)):
            price = ohlcv[i]['close']
            rsi = indicators['rsi'][i]
            ema_12 = indicators['ema_12'][i]
            ema_26 = indicators['ema_26'][i]
            bb_lower = indicators['bb_lower'][i]
            bb_upper = indicators['bb_upper'][i]
            
            # Entry conditions
            if not in_position:
                long_signal = False
                
                if entry_logic == 'rsi_oversold' and rsi < 30:
                    long_signal = True
                elif entry_logic == 'golden_cross' and ema_12 > ema_26 and indicators['ema_12'][i-1] <= indicators['ema_26'][i-1]:
                    long_signal = True
                elif entry_logic == 'bb_bounce' and price < bb_lower:
                    long_signal = True
                elif entry_logic == 'mean_reversion' and rsi < 40 and price < indicators['ema_50'][i]:
                    long_signal = True
                
                if long_signal:
                    in_position = True
                    entry_price = price
            
            # Exit conditions
            elif in_position:
                exit_signal = False
                pnl = (price - entry_price) / entry_price
                
                if exit_logic == 'rsi_overbought' and rsi > 70:
                    exit_signal = True
                elif exit_logic == 'death_cross' and ema_12 < ema_26:
                    exit_signal = True
                elif exit_logic == 'bb_upper' and price > bb_upper:
                    exit_signal = True
                elif exit_logic == 'take_profit' and pnl > 0.05:
                    exit_signal = True
                elif exit_logic == 'stop_loss' and pnl < -0.03:
                    exit_signal = True
                
                if exit_signal:
                    trades.append(pnl)
                    in_position = False
        
        # Calculate metrics
        if not trades:
            return {'win_rate': 0, 'profit_factor': 0, 'sharpe': 0, 'total_return': 0}
        
        wins = sum(1 for t in trades if t > 0)
        win_rate = wins / len(trades)
        
        avg_win = np.mean([t for t in trades if t > 0]) if wins > 0 else 0
        avg_loss = np.mean([t for t in trades if t <= 0]) if wins < len(trades) else 1
        profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else 0
        
        total_return = sum(trades)
        sharpe = np.mean(trades) / np.std(trades) if np.std(trades) > 0 else 0
        
        return {
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'sharpe': sharpe,
            'total_return': total_return,
            'trades': len(trades)
        }


class UniversalFinder:
    """Find strategies that work across all symbols."""
    
    def __init__(self):
        self.fetcher = DataFetcher()
        self.data = {}
        self.simulator = None
    
    def load_data(self, timeframe: str = '1h'):
        """Load data for all symbols."""
        logger.info(f"Loading data for {len(UNIVERSE)} symbols...")
        self.data = self.fetcher.fetch_all_symbols(timeframe)
        self.simulator = PatternSimulator(self.data)
        logger.info(f"Loaded data for {len(self.data)} symbols")
    
    def find_universal_patterns(self, num_candidates: int = 1000) -> List[UniversalDNA]:
        """Find patterns that work across all symbols."""
        if not self.data:
            self.load_data()
        
        logger.info(f"Testing {num_candidates} DNA patterns...")
        
        # Generate candidates
        candidates = []
        entry_logics = ['rsi_oversold', 'golden_cross', 'bb_bounce', 'mean_reversion']
        exit_logics = ['rsi_overbought', 'death_cross', 'bb_upper', 'take_profit', 'stop_loss']
        
        for _ in range(num_candidates):
            genes = {
                'timeframe': random.choice(['1h', '4h', '1d']),
                'entry_logic': random.choice(entry_logics),
                'exit_logic': random.choice(exit_logics),
                'rsi_threshold': random.choice([20, 25, 30, 35]),
                'atr_mult': random.choice([1.5, 2.0, 2.5, 3.0]),
                'position_size': random.choice([0.05, 0.1, 0.15])
            }
            candidates.append(UniversalDNA(name=f"Universal_{_}", genes=genes))
        
        # Test each candidate on all symbols
        for dna in candidates:
            for symbol in self.data.keys():
                perf = self.simulator.simulate_strategy(symbol, dna.genes)
                dna.symbol_performance[symbol] = perf
            
            dna.calculate_scores()
        
        # Filter for universal patterns
        universal = [
            dna for dna in candidates 
            if dna.universal_score > 0.4 and dna.consistency_score > 0.7
        ]
        
        # Sort by universal score
        universal.sort(key=lambda x: x.universal_score, reverse=True)
        
        return universal
    
    def find_todays_opportunities(self) -> List[Dict]:
        """Find what would work TODAY based on current market conditions."""
        logger.info("Analyzing today's market conditions...")
        
        # Fetch current data
        prices = self.fetcher.fetch_current_prices()
        funding = self.fetcher.fetch_funding_rates()
        
        # Load recent data
        self.load_data('1h')
        
        # Find universal patterns
        patterns = self.find_universal_patterns(500)
        
        opportunities = []
        
        for pattern in patterns[:20]:  # Top 20 patterns
            # Find symbols where pattern has high win rate
            best_symbols = [
                sym for sym, perf in pattern.symbol_performance.items()
                if perf['win_rate'] > 0.6 and perf['profit_factor'] > 1.5
            ]
            
            if len(best_symbols) >= 5:  # At least 5 symbols
                # Calculate current signals for these symbols
                signals = []
                for symbol in best_symbols[:10]:
                    if symbol in prices:
                        signal = self._generate_signal(symbol, pattern.genes, prices[symbol])
                        if signal:
                            signals.append(signal)
                
                opportunities.append({
                    'pattern': pattern,
                    'signals': signals,
                    'symbols': best_symbols,
                    'avg_win_rate': np.mean([pattern.symbol_performance[s]['win_rate'] for s in best_symbols]),
                    'avg_profit_factor': np.mean([pattern.symbol_performance[s]['profit_factor'] for s in best_symbols])
                })
        
        return opportunities
    
    def _generate_signal(self, symbol: str, genes: Dict, current_price: float) -> Optional[Dict]:
        """Generate a trading signal for a symbol."""
        if symbol not in self.data:
            return None
        
        ohlcv = self.data[symbol]
        indicators = self.simulator.calculate_indicators(ohlcv)
        
        i = len(ohlcv) - 1
        rsi = indicators['rsi'][i]
        price = current_price
        ema_12 = indicators['ema_12'][i]
        ema_26 = indicators['ema_26'][i]
        bb_lower = indicators['bb_lower'][i]
        bb_upper = indicators['bb_upper'][i]
        atr = indicators['atr'][i]
        
        entry_logic = genes.get('entry_logic', 'rsi_oversold')
        signal = None
        
        if entry_logic == 'rsi_oversold' and rsi < 35:
            signal = {
                'symbol': symbol,
                'direction': 'LONG',
                'entry': price,
                'tp': price + (atr * genes.get('atr_mult', 2)),
                'sl': price - (atr * genes.get('atr_mult', 1.5)),
                'confidence': (40 - rsi) / 40,  # Higher confidence at lower RSI
                'reason': f"RSI oversold ({rsi:.1f}) + Universal pattern"
            }
        elif entry_logic == 'golden_cross' and ema_12 > ema_26:
            signal = {
                'symbol': symbol,
                'direction': 'LONG',
                'entry': price,
                'tp': price * 1.05,
                'sl': price * 0.97,
                'confidence': 0.7,
                'reason': f"Golden Cross EMA + Universal pattern"
            }
        elif entry_logic == 'bb_bounce' and price < bb_lower * 1.02:
            signal = {
                'symbol': symbol,
                'direction': 'LONG',
                'entry': price,
                'tp': bb_upper,
                'sl': price - (atr * 2),
                'confidence': 0.75,
                'reason': f"BB Lower bounce + Universal pattern"
            }
        elif entry_logic == 'mean_reversion' and rsi < 40:
            signal = {
                'symbol': symbol,
                'direction': 'LONG',
                'entry': price,
                'tp': price + (atr * 2.5),
                'sl': price - (atr * 1.5),
                'confidence': (45 - rsi) / 45,
                'reason': f"Mean reversion setup + Universal pattern"
            }
        
        return signal


# ==================== MAIN ====================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Universal Strategy Finder')
    parser.add_argument('--run', action='store_true', help='Run full universal pattern search')
    parser.add_argument('--today', action='store_true', help='Find what works TODAY')
    parser.add_argument('--live', action='store_true', help='Generate live signals')
    
    args = parser.parse_args()
    
    finder = UniversalFinder()
    
    if args.run:
        print("🔍 Running Universal Pattern Discovery...")
        print(f"Testing across {len(UNIVERSE)} symbols...")
        
        finder.load_data()
        patterns = finder.find_universal_patterns(1000)
        
        print(f"\n✅ Found {len(patterns)} universal patterns:")
        print("\n" + "="*80)
        
        for i, p in enumerate(patterns[:10], 1):
            print(f"\n{i}. {p.name}")
            print(f"   Universal Score: {p.universal_score:.3f}")
            print(f"   Consistency: {p.consistency_score:.1%} of symbols profitable")
            print(f"   Robustness: {p.robustness_score:.3f}")
            print(f"   Entry: {p.genes['entry_logic']} | Exit: {p.genes['exit_logic']}")
            print(f"   Top Symbols: {list(p.symbol_performance.keys())[:5]}")
        
        # Save results
        output = {
            'timestamp': datetime.utcnow().isoformat(),
            'universe': UNIVERSE,
            'patterns': [
                {
                    'name': p.name,
                    'genes': p.genes,
                    'universal_score': p.universal_score,
                    'consistency_score': p.consistency_score,
                    'symbol_performance': p.symbol_performance
                }
                for p in patterns[:50]
            ]
        }
        
        output_path = Path('genome/results/universal_patterns.json')
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(output, f, indent=2)
        print(f"\n💾 Saved to {output_path}")
    
    elif args.today:
        print("🔍 Analyzing what would work TODAY...")
        
        opportunities = finder.find_todays_opportunities()
        
        print(f"\n✅ Found {len(opportunities)} high-probability opportunities:")
        print("\n" + "="*80)
        
        for i, opp in enumerate(opportunities[:5], 1):
            print(f"\n{i}. Pattern: {opp['pattern'].name}")
            print(f"   Universal Score: {opp['pattern'].universal_score:.3f}")
            print(f"   Avg Win Rate: {opp['avg_win_rate']:.1%}")
            print(f"   Works on: {len(opp['symbols'])} symbols")
            print(f"   Current Signals:")
            
            for sig in opp['signals'][:5]:
                print(f"      • {sig['symbol']} {sig['direction']}")
                print(f"        Entry: ${sig['entry']:.4f} | TP: ${sig['tp']:.4f} | SL: ${sig['sl']:.4f}")
                print(f"        Confidence: {sig['confidence']:.1%} | {sig['reason']}")
    
    elif args.live:
        print("📡 Generating LIVE signals...")
        
        opportunities = finder.find_todays_opportunities()
        
        signals = []
        for opp in opportunities:
            signals.extend(opp['signals'])
        
        # Sort by confidence
        signals.sort(key=lambda x: x['confidence'], reverse=True)
        
        print(f"\n🎯 TOP 10 LIVE SIGNALS:")
        print("="*80)
        
        for i, sig in enumerate(signals[:10], 1):
            r_r = abs(sig['tp'] - sig['entry']) / abs(sig['entry'] - sig['sl'])
            print(f"\n{i}. {sig['symbol']} {sig['direction']}")
            print(f"   Entry: ${sig['entry']:.4f}")
            print(f"   TP: ${sig['tp']:.4f} (+{((sig['tp']/sig['entry'])-1)*100:.1f}%)")
            print(f"   SL: ${sig['sl']:.4f} ({((sig['sl']/sig['entry'])-1)*100:.1f}%)")
            print(f"   R:R = {r_r:.2f}")
            print(f"   Confidence: {sig['confidence']:.1%}")
            print(f"   Setup: {sig['reason']}")
        
        # Save for Discord
        output = {
            'generated_at': datetime.utcnow().isoformat(),
            'signals': signals
        }
        
        with open('genome/results/live_signals_universal.json', 'w') as f:
            json.dump(output, f, indent=2)
    
    else:
        print("Universal Strategy Finder")
        print("\nCommands:")
        print("  --run      Find universal patterns across all symbols")
        print("  --today    Find what would work TODAY")
        print("  --live     Generate live trading signals")
        print("\nExample:")
        print("  python universal_strategy_finder.py --live")
