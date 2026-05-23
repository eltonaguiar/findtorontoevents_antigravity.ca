#!/usr/bin/env python3
"""
Reverse Engineer Today's Winners
=================================

Analyzes today's price action to find:
1. What patterns WOULD have won if traded today
2. Which DNA combinations produced the best risk-adjusted returns
3. Entry/exit timing that maximized profit
4. Which symbols were most predictable

This is NOT prediction - it's post-hoc analysis to learn patterns.

Usage:
    python reverse_engineer_today.py --analyze      # Full analysis
    python reverse_engineer_today.py --report       # Generate report
    python reverse_engineer_today.py --discord      # Send to Discord
"""

import json
import requests
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('ReverseEngineerToday')


# Symbols to analyze
SYMBOLS = [
    'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'ADAUSDT', 'DOTUSDT',
    'LINKUSDT', 'MATICUSDT', 'AVAXUSDT', 'UNIUSDT', 'ATOMUSDT',
    'LTCUSDT', 'BCHUSDT', 'ALGOUSDT', 'VETUSDT', 'FILUSDT',
    'TRXUSDT', 'ETCUSDT', 'XLMUSDT', 'NEARUSDT', 'ARBUSDT'
]


@dataclass
class HypotheticalTrade:
    """A trade that would have happened with perfect foresight."""
    symbol: str
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    direction: str
    pnl_pct: float
    pnl_usd: float  # Assuming $1000 position
    max_profit: float  # Max unrealized profit
    max_drawdown: float  # Max unrealized loss
    duration_hours: float
    dna_signature: Dict  # What genes would have caught this


@dataclass
class WinningPattern:
    """A pattern that produced winning trades today."""
    name: str
    dna_genes: Dict
    trades: List[HypotheticalTrade]
    total_pnl: float
    win_rate: float
    avg_trade: float
    profit_factor: float
    best_symbols: List[str]
    
    def calculate_metrics(self):
        """Calculate aggregate metrics."""
        if not self.trades:
            return
        
        wins = sum(1 for t in self.trades if t.pnl_pct > 0)
        self.win_rate = wins / len(self.trades)
        self.total_pnl = sum(t.pnl_pct for t in self.trades)
        self.avg_trade = self.total_pnl / len(self.trades)
        
        gross_profit = sum(t.pnl_pct for t in self.trades if t.pnl_pct > 0)
        gross_loss = abs(sum(t.pnl_pct for t in self.trades if t.pnl_pct < 0))
        self.profit_factor = gross_profit / gross_loss if gross_loss > 0 else 999
        
        # Best symbols for this pattern
        symbol_pnl = {}
        for t in self.trades:
            symbol_pnl[t.symbol] = symbol_pnl.get(t.symbol, 0) + t.pnl_pct
        self.best_symbols = sorted(symbol_pnl.keys(), key=lambda x: symbol_pnl[x], reverse=True)[:5]


class DataLoader:
    """Load today's price data."""
    
    def __init__(self):
        self.data = {}
    
    _SPOT_BASES = [
        "https://api.binance.com", "https://api1.binance.com",
        "https://data-api.binance.vision", "https://api.binance.us",
    ]

    def fetch_today_data(self, timeframe: str = '15m') -> Dict[str, List]:
        """Fetch today's OHLCV data for all symbols (with endpoint failover)."""
        logger.info(f"Fetching today's {timeframe} data...")

        for symbol in SYMBOLS:
            for _base in self._SPOT_BASES:
                try:
                    url = f"{_base}/api/v3/klines"
                    params = {
                        'symbol': symbol,
                        'interval': timeframe,
                        'limit': 100
                    }
                    response = requests.get(url, params=params, timeout=10)
                    if response.status_code in (451, 403):
                        continue
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
                        self.data[symbol] = parsed
                        break  # success
                except Exception as e:
                    logger.warning(f"Failed to fetch {symbol} from {_base}: {e}")

        logger.info(f"Loaded data for {len(self.data)} symbols")
        return self.data

    def fetch_current_prices(self) -> Dict[str, float]:
        """Get current prices (with endpoint failover)."""
        prices = {}
        for _base in self._SPOT_BASES:
            try:
                url = f"{_base}/api/v3/ticker/price"
                response = requests.get(url, timeout=10)
                if response.status_code in (451, 403):
                    continue
                if response.status_code == 200:
                    for item in response.json():
                        if item['symbol'] in SYMBOLS:
                            prices[item['symbol']] = float(item['price'])
                    return prices
            except Exception as e:
                logger.error(f"Failed to fetch prices from {_base}: {e}")
        return prices


class PatternAnalyzer:
    """Analyze price data to find winning patterns."""
    
    def __init__(self, data: Dict[str, List]):
        self.data = data
    
    def calculate_indicators(self, ohlcv: List) -> Dict:
        """Calculate technical indicators."""
        closes = [c['close'] for c in ohlcv]
        highs = [c['high'] for c in ohlcv]
        lows = [c['low'] for c in ohlcv]
        
        indicators = {}
        
        # EMAs
        for period in [9, 12, 21, 26, 50, 200]:
            indicators[f'ema_{period}'] = self._ema(closes, period)
        
        # RSI
        indicators['rsi'] = self._rsi(closes, 14)
        indicators['rsi_6'] = self._rsi(closes, 6)  # RSI-2 equivalent
        
        # MACD
        indicators['macd'], indicators['macd_signal'] = self._macd(closes)
        
        # Bollinger
        indicators['bb_upper'], indicators['bb_middle'], indicators['bb_lower'] = self._bollinger(closes)
        
        # ATR
        indicators['atr'] = self._atr(highs, lows, closes)
        
        # Volume
        volumes = [c['volume'] for c in ohlcv]
        indicators['volume_sma'] = self._sma(volumes, 20)
        
        # VWAP
        indicators['vwap'] = self._vwap(ohlcv)
        
        # Support/Resistance levels
        indicators['pivot_highs'], indicators['pivot_lows'] = self._find_pivots(highs, lows)
        
        return indicators
    
    def _ema(self, data: List, period: int) -> List:
        if len(data) < period:
            return data
        multiplier = 2 / (period + 1)
        ema = [sum(data[:period]) / period]
        for price in data[period:]:
            ema.append((price - ema[-1]) * multiplier + ema[-1])
        return [ema[0]] * (period - 1) + ema
    
    def _sma(self, data: List, period: int) -> List:
        result = []
        for i in range(len(data)):
            if i < period - 1:
                result.append(sum(data[:i+1]) / (i+1))
            else:
                result.append(sum(data[i-period+1:i+1]) / period)
        return result
    
    def _rsi(self, closes: List, period: int) -> List:
        deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]
        
        rsi = [50] * (period + 1)
        
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
        ema_12 = self._ema(closes, 12)
        ema_26 = self._ema(closes, 26)
        macd = [ema_12[i] - ema_26[i] for i in range(len(closes))]
        signal = self._ema(macd, 9)
        return macd, signal
    
    def _bollinger(self, closes: List, period: int = 20) -> Tuple[List, List, List]:
        middle = self._sma(closes, period)
        upper, lower = [], []
        
        for i in range(len(closes)):
            if i < period - 1:
                upper.append(closes[i])
                lower.append(closes[i])
            else:
                std = np.std(closes[i-period+1:i+1])
                upper.append(middle[i] + 2 * std)
                lower.append(middle[i] - 2 * std)
        
        return upper, middle, lower
    
    def _atr(self, highs: List, lows: List, closes: List, period: int = 14) -> List:
        tr = [highs[0] - lows[0]]
        for i in range(1, len(highs)):
            tr1 = highs[i] - lows[i]
            tr2 = abs(highs[i] - closes[i-1])
            tr3 = abs(lows[i] - closes[i-1])
            tr.append(max(tr1, tr2, tr3))
        
        return self._ema(tr, period)
    
    def _vwap(self, ohlcv: List) -> List:
        """Volume Weighted Average Price."""
        typical_prices = [(c['high'] + c['low'] + c['close']) / 3 for c in ohlcv]
        volumes = [c['volume'] for c in ohlcv]
        
        vwap = []
        cum_vol = 0
        cum_pv = 0
        
        for i in range(len(ohlcv)):
            cum_vol += volumes[i]
            cum_pv += typical_prices[i] * volumes[i]
            vwap.append(cum_pv / cum_vol if cum_vol > 0 else typical_prices[i])
        
        return vwap
    
    def _find_pivots(self, highs: List, lows: List, window: int = 5) -> Tuple[List, List]:
        """Find pivot highs and lows."""
        pivot_highs = [None] * len(highs)
        pivot_lows = [None] * len(lows)
        
        for i in range(window, len(highs) - window):
            # Pivot high
            if all(highs[i] > highs[i-j] for j in range(1, window+1)) and \
               all(highs[i] > highs[i+j] for j in range(1, window+1)):
                pivot_highs[i] = highs[i]
            
            # Pivot low
            if all(lows[i] < lows[i-j] for j in range(1, window+1)) and \
               all(lows[i] < lows[i+j] for j in range(1, window+1)):
                pivot_lows[i] = lows[i]
        
        return pivot_highs, pivot_lows
    
    def find_would_have_won_trades(self, symbol: str) -> List[HypotheticalTrade]:
        """
        Find all trades that would have been profitable today.
        This is reverse engineering - we look at what happened and find optimal entries/exits.
        """
        if symbol not in self.data:
            return []
        
        ohlcv = self.data[symbol]
        if len(ohlcv) < 50:
            return []
        
        indicators = self.calculate_indicators(ohlcv)
        trades = []
        
        # Look for local minima that preceded rallies (would have been good longs)
        for i in range(20, len(ohlcv) - 10):
            # Current bar
            low = ohlcv[i]['low']
            close = ohlcv[i]['close']
            
            # Look ahead 10 bars for max price
            future_highs = [ohlcv[j]['high'] for j in range(i+1, min(i+11, len(ohlcv)))]
            future_lows = [ohlcv[j]['low'] for j in range(i+1, min(i+11, len(ohlcv)))]
            
            if not future_highs:
                continue
            
            max_future = max(future_highs)
            min_future = min(future_lows)
            
            # Potential long: if future high > 2% above current and drawdown < 1%
            if max_future > close * 1.02 and min_future > close * 0.99:
                # Find optimal exit
                for j in range(i+1, min(i+11, len(ohlcv))):
                    if ohlcv[j]['high'] == max_future:
                        exit_price = ohlcv[j]['close']
                        exit_time = datetime.fromtimestamp(ohlcv[j]['timestamp'] / 1000)
                        break
                else:
                    exit_price = ohlcv[i+10]['close']
                    exit_time = datetime.fromtimestamp(ohlcv[i+10]['timestamp'] / 1000)
                
                pnl = (exit_price - close) / close
                
                # Determine what DNA signature would have caught this
                dna_signature = self._determine_dna_signature(indicators, i, 'LONG')
                
                trade = HypotheticalTrade(
                    symbol=symbol,
                    entry_time=datetime.fromtimestamp(ohlcv[i]['timestamp'] / 1000),
                    exit_time=exit_time,
                    entry_price=close,
                    exit_price=exit_price,
                    direction='LONG',
                    pnl_pct=pnl * 100,
                    pnl_usd=pnl * 1000,
                    max_profit=(max_future - close) / close * 100,
                    max_drawdown=(close - min_future) / close * 100,
                    duration_hours=(exit_time - datetime.fromtimestamp(ohlcv[i]['timestamp'] / 1000)).total_seconds() / 3600,
                    dna_signature=dna_signature
                )
                trades.append(trade)
            
            # Potential short: if future low > 2% below current and rally < 1%
            if min_future < close * 0.98 and max_future < close * 1.01:
                for j in range(i+1, min(i+11, len(ohlcv))):
                    if ohlcv[j]['low'] == min_future:
                        exit_price = ohlcv[j]['close']
                        exit_time = datetime.fromtimestamp(ohlcv[j]['timestamp'] / 1000)
                        break
                else:
                    exit_price = ohlcv[i+10]['close']
                    exit_time = datetime.fromtimestamp(ohlcv[i+10]['timestamp'] / 1000)
                
                pnl = (close - exit_price) / close
                
                dna_signature = self._determine_dna_signature(indicators, i, 'SHORT')
                
                trade = HypotheticalTrade(
                    symbol=symbol,
                    entry_time=datetime.fromtimestamp(ohlcv[i]['timestamp'] / 1000),
                    exit_time=exit_time,
                    entry_price=close,
                    exit_price=exit_price,
                    direction='SHORT',
                    pnl_pct=pnl * 100,
                    pnl_usd=pnl * 1000,
                    max_profit=(close - min_future) / close * 100,
                    max_drawdown=(max_future - close) / close * 100,
                    duration_hours=(exit_time - datetime.fromtimestamp(ohlcv[i]['timestamp'] / 1000)).total_seconds() / 3600,
                    dna_signature=dna_signature
                )
                trades.append(trade)
        
        return trades
    
    def _determine_dna_signature(self, indicators: Dict, index: int, direction: str) -> Dict:
        """Determine what DNA genes would have triggered this trade."""
        signature = {}
        
        rsi = indicators['rsi'][index]
        rsi_6 = indicators['rsi_6'][index]
        ema_12 = indicators['ema_12'][index]
        ema_26 = indicators['ema_26'][index]
        ema_50 = indicators['ema_50'][index]
        bb_lower = indicators['bb_lower'][index]
        bb_upper = indicators['bb_upper'][index]
        price = indicators['ema_12'][index]  # Using as proxy for price
        
        # RSI conditions
        if rsi < 30:
            signature['rsi_oversold'] = True
            signature['rsi_threshold'] = int(rsi)
        elif rsi < 40:
            signature['rsi_weak'] = True
        
        # RSI-2 (Connors style)
        if rsi_6 < 20:
            signature['connors_rsi'] = True
        
        # EMA conditions
        if ema_12 > ema_26:
            signature['ema_bullish'] = True
        else:
            signature['ema_bearish'] = True
        
        if price < ema_50:
            signature['below_50ema'] = True
        
        # Bollinger conditions
        if price < bb_lower:
            signature['bb_lower_touch'] = True
        if price > bb_upper:
            signature['bb_upper_touch'] = True
        
        # MACD
        macd = indicators['macd'][index]
        macd_signal = indicators['macd_signal'][index]
        if macd > macd_signal:
            signature['macd_bullish'] = True
        else:
            signature['macd_bearish'] = True
        
        # Volume (simplified)
        signature['volume_confirm'] = True
        
        return signature


class ReverseEngineer:
    """Main reverse engineering engine."""
    
    def __init__(self):
        self.loader = DataLoader()
        self.analyzer = None
        self.all_trades = []
        self.patterns = []
    
    def run_analysis(self) -> Dict:
        """Run full reverse engineering analysis."""
        logger.info("Starting reverse engineering analysis...")
        
        # Load data
        data = self.loader.fetch_today_data('15m')
        self.analyzer = PatternAnalyzer(data)
        
        # Find all winning trades for each symbol
        logger.info("Finding hypothetical winning trades...")
        for symbol in data.keys():
            trades = self.analyzer.find_would_have_won_trades(symbol)
            self.all_trades.extend(trades)
            logger.info(f"  {symbol}: {len(trades)} winning trades")
        
        logger.info(f"Total hypothetical trades found: {len(self.all_trades)}")
        
        # Group trades by DNA signature patterns
        self.patterns = self._group_by_pattern()
        
        # Generate report
        return self._generate_report()
    
    def _group_by_pattern(self) -> List[WinningPattern]:
        """Group trades by their DNA signatures."""
        pattern_groups = {}
        
        for trade in self.all_trades:
            # Create a pattern key from signature
            sig = trade.dna_signature
            key_parts = []
            
            if sig.get('rsi_oversold'):
                key_parts.append(f"rsi<{sig.get('rsi_threshold', 30)}")
            if sig.get('connors_rsi'):
                key_parts.append("connors")
            if sig.get('bb_lower_touch'):
                key_parts.append("bb_lower")
            if sig.get('ema_bullish'):
                key_parts.append("ema_bull")
            if sig.get('macd_bullish'):
                key_parts.append("macd_bull")
            
            key = " + ".join(key_parts) if key_parts else "mixed"
            
            if key not in pattern_groups:
                pattern_groups[key] = []
            pattern_groups[key].append(trade)
        
        # Create WinningPattern objects
        patterns = []
        for name, trades in pattern_groups.items():
            # Infer DNA genes from pattern name
            genes = self._infer_genes_from_name(name)
            
            pattern = WinningPattern(
                name=name,
                dna_genes=genes,
                trades=trades,
                total_pnl=0,
                win_rate=0,
                avg_trade=0,
                profit_factor=0,
                best_symbols=[]
            )
            pattern.calculate_metrics()
            patterns.append(pattern)
        
        # Sort by total PnL
        patterns.sort(key=lambda x: x.total_pnl, reverse=True)
        return patterns
    
    def _infer_genes_from_name(self, name: str) -> Dict:
        """Infer DNA genes from pattern name."""
        genes = {}
        
        if 'rsi<' in name:
            genes['entry_logic'] = 'rsi_oversold'
            genes['rsi_period'] = 14
        elif 'connors' in name:
            genes['entry_logic'] = 'connors_rsi2'
            genes['rsi_period'] = 2
        
        if 'bb_lower' in name:
            genes['confirmation'] = 'bollinger_lower'
        
        if 'ema_bull' in name:
            genes['trend_filter'] = 'ema12>ema26'
        
        genes['exit_logic'] = 'rsi_overbought_or_time'
        
        return genes
    
    def _generate_report(self) -> Dict:
        """Generate comprehensive report."""
        total_trades = len(self.all_trades)
        total_pnl = sum(t.pnl_pct for t in self.all_trades)
        avg_pnl = total_pnl / total_trades if total_trades > 0 else 0
        
        winning_trades = [t for t in self.all_trades if t.pnl_pct > 0]
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0
        
        report = {
            'analysis_time': datetime.utcnow().isoformat(),
            'summary': {
                'total_opportunities': total_trades,
                'total_pnl_pct': round(total_pnl, 2),
                'avg_trade_pct': round(avg_pnl, 2),
                'win_rate': round(win_rate * 100, 1),
                'symbols_analyzed': len(self.data) if self.analyzer else 0
            },
            'top_patterns': [],
            'best_trades': [],
            'symbol_performance': {}
        }
        
        # Top patterns
        for p in self.patterns[:10]:
            report['top_patterns'].append({
                'name': p.name,
                'trade_count': len(p.trades),
                'total_pnl_pct': round(p.total_pnl, 2),
                'win_rate': round(p.win_rate * 100, 1),
                'profit_factor': round(p.profit_factor, 2),
                'best_symbols': p.best_symbols,
                'dna_genes': p.dna_genes
            })
        
        # Best individual trades
        sorted_trades = sorted(self.all_trades, key=lambda x: x.pnl_pct, reverse=True)
        for t in sorted_trades[:10]:
            report['best_trades'].append({
                'symbol': t.symbol,
                'direction': t.direction,
                'entry': round(t.entry_price, 4),
                'exit': round(t.exit_price, 4),
                'pnl_pct': round(t.pnl_pct, 2),
                'duration_hours': round(t.duration_hours, 1),
                'entry_time': t.entry_time.isoformat()
            })
        
        # Symbol performance
        symbol_pnl = {}
        for t in self.all_trades:
            symbol_pnl[t.symbol] = symbol_pnl.get(t.symbol, 0) + t.pnl_pct
        
        for symbol, pnl in sorted(symbol_pnl.items(), key=lambda x: x[1], reverse=True):
            symbol_trades = [t for t in self.all_trades if t.symbol == symbol]
            wins = sum(1 for t in symbol_trades if t.pnl_pct > 0)
            report['symbol_performance'][symbol] = {
                'total_pnl_pct': round(pnl, 2),
                'trade_count': len(symbol_trades),
                'win_rate': round(wins / len(symbol_trades) * 100, 1)
            }
        
        return report
    
    def print_report(self, report: Dict):
        """Print formatted report."""
        print("\n" + "="*80)
        print("  REVERSE ENGINEERED TODAY'S WINNERS")
        print("="*80)
        
        s = report['summary']
        print(f"\n📊 SUMMARY")
        print(f"   Analysis Time: {report['analysis_time']}")
        print(f"   Symbols Analyzed: {s['symbols_analyzed']}")
        print(f"   Total Opportunities: {s['total_opportunities']}")
        print(f"   Total PnL: {s['total_pnl_pct']:.1f}%")
        print(f"   Win Rate: {s['win_rate']:.1f}%")
        print(f"   Avg Trade: {s['avg_trade_pct']:.2f}%")
        
        print(f"\n🏆 TOP 10 PATTERNS (What Would Have Worked)")
        print("-"*80)
        for i, p in enumerate(report['top_patterns'], 1):
            print(f"\n{i}. {p['name']}")
            print(f"   Trades: {p['trade_count']} | PnL: {p['total_pnl_pct']:.1f}% | "
                  f"WR: {p['win_rate']:.0f}% | PF: {p['profit_factor']:.2f}")
            print(f"   Best on: {', '.join(p['best_symbols'][:3])}")
        
        print(f"\n💰 BEST INDIVIDUAL TRADES")
        print("-"*80)
        for i, t in enumerate(report['best_trades'][:5], 1):
            print(f"{i}. {t['symbol']} {t['direction']}: "
                  f"+{t['pnl_pct']:.2f}% in {t['duration_hours']:.1f}h "
                  f"(${t['entry']} → ${t['exit']})")
        
        print(f"\n📈 SYMBOL PERFORMANCE")
        print("-"*80)
        for symbol, perf in list(report['symbol_performance'].items())[:10]:
            print(f"{symbol:10} | PnL: {perf['total_pnl_pct']:+6.1f}% | "
                  f"Trades: {perf['trade_count']:2} | WR: {perf['win_rate']:4.1f}%")
        
        print("\n" + "="*80)
        print("💡 KEY INSIGHTS")
        print("="*80)
        
        top_pattern = report['top_patterns'][0] if report['top_patterns'] else None
        if top_pattern:
            print(f"\n1. Best Pattern: '{top_pattern['name']}'")
            print(f"   → Would have produced {top_pattern['trade_count']} winning trades")
            print(f"   → Total return: {top_pattern['total_pnl_pct']:.1f}%")
        
        best_symbol = max(report['symbol_performance'].items(), 
                         key=lambda x: x[1]['total_pnl_pct'])
        print(f"\n2. Most Predictable: {best_symbol[0]}")
        print(f"   → Generated {best_symbol[1]['total_pnl_pct']:.1f}% in opportunities")
        
        print(f"\n3. Tomorrow's Setup:")
        print(f"   → Focus on patterns with: {report['top_patterns'][0]['name'] if report['top_patterns'] else 'mixed signals'}")
        print(f"   → Target symbols: {', '.join([s['best_symbols'][0] for s in report['top_patterns'][:3] if s['best_symbols']])}")
        
        print("\n" + "="*80)


# ==================== MAIN ====================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Reverse Engineer Today\'s Winners')
    parser.add_argument('--analyze', action='store_true', help='Run full analysis')
    parser.add_argument('--report', action='store_true', help='Generate and print report')
    
    args = parser.parse_args()
    
    if args.analyze or args.report:
        engineer = ReverseEngineer()
        report = engineer.run_analysis()
        engineer.print_report(report)
        
        # Save report
        output_path = Path('genome/results/reverse_engineered_today.json')
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        print(f"\n💾 Full report saved to {output_path}")
    
    else:
        print("Reverse Engineer Today's Winners")
        print("\nCommands:")
        print("  --analyze    Run full reverse engineering analysis")
        print("  --report     Generate and display report")
        print("\nExample:")
        print("  python reverse_engineer_today.py --analyze")
