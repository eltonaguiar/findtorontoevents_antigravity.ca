#!/usr/bin/env python3
"""
Paper Trading System - Live Simulation Without Real Money
===========================================================

Simulates live trading with real-time market data:
- Fetches live prices from Binance
- Generates signals based on validated strategies
- Tracks paper portfolio performance
- Records all trades for analysis
- Prepares for transition to live trading

Usage:
    python paper_trading_system.py --start      # Start paper trading
    python paper_trading_system.py --status     # Check current status
    python paper_trading_system.py --stop       # Stop and save results
    python paper_trading_system.py --report     # Generate performance report
"""

import json
import requests
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field, asdict
import logging
import threading

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('PaperTrading')


# Top symbols to trade
SYMBOLS = [
    'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'ADAUSDT', 'DOTUSDT',
    'AVAXUSDT', 'APTUSDT', 'ARBUSDT', 'TIAUSDT', 'GRTUSDT'
]


@dataclass
class PaperTrade:
    """A paper trade record."""
    trade_id: str
    symbol: str
    direction: str
    entry_price: float
    exit_price: float = 0
    position_size_usd: float = 0
    entry_time: datetime = field(default_factory=datetime.now)
    exit_time: datetime = None
    pnl_pct: float = 0
    pnl_usd: float = 0
    exit_reason: str = ""
    strategy: str = ""
    status: str = "open"  # open, closed


@dataclass
class PaperPortfolio:
    """Paper portfolio state."""
    initial_capital: float = 10000.0
    current_equity: float = 10000.0
    open_positions: List[PaperTrade] = field(default_factory=list)
    closed_trades: List[PaperTrade] = field(default_factory=list)
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    max_drawdown: float = 0
    peak_equity: float = 10000.0


class LiveDataFeed:
    """Fetches live market data from Binance."""
    
    _SPOT_BASES = [
        "https://api.binance.com", "https://api1.binance.com",
        "https://data-api.binance.vision", "https://api.binance.us",
    ]

    def __init__(self):
        self.prices = {}
        self.klines = {}

    def fetch_current_prices(self) -> Dict[str, float]:
        """Fetch current prices for all symbols (with endpoint failover)."""
        for base in self._SPOT_BASES:
            try:
                url = f"{base}/api/v3/ticker/price"
                response = requests.get(url, timeout=10)
                if response.status_code in (451, 403):
                    continue
                if response.status_code == 200:
                    for item in response.json():
                        if item['symbol'] in SYMBOLS:
                            self.prices[item['symbol']] = float(item['price'])
                    return self.prices
            except Exception as e:
                logger.error(f"Failed to fetch prices from {base}: {e}")
        return {}

    def fetch_klines(self, symbol: str, interval: str = '15m', limit: int = 100) -> List[Dict]:
        """Fetch recent kline data (with endpoint failover)."""
        for base in self._SPOT_BASES:
            try:
                url = f"{base}/api/v3/klines"
                params = {
                    'symbol': symbol,
                    'interval': interval,
                    'limit': limit
                }
                response = requests.get(url, params=params, timeout=10)
                if response.status_code in (451, 403):
                    continue

                if response.status_code == 200:
                    klines = []
                    for k in response.json():
                        klines.append({
                            'timestamp': int(k[0]),
                            'open': float(k[1]),
                            'high': float(k[2]),
                            'low': float(k[3]),
                            'close': float(k[4]),
                            'volume': float(k[5])
                        })
                    return klines

            except Exception as e:
                logger.error(f"Failed to fetch klines for {symbol} from {base}: {e}")

        return []
    
    def calculate_rsi(self, closes: List[float], period: int = 14) -> float:
        """Calculate RSI for a series of closes."""
        if len(closes) < period + 1:
            return 50.0
        
        deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        gains = [d if d > 0 else 0 for d in deltas[-period:]]
        losses = [-d if d < 0 else 0 for d in deltas[-period:]]
        
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    def calculate_indicators(self, symbol: str) -> Dict:
        """Calculate technical indicators for a symbol."""
        klines = self.fetch_klines(symbol, '15m', 50)
        
        if not klines or len(klines) < 20:
            return {}
        
        closes = [k['close'] for k in klines]
        highs = [k['high'] for k in klines]
        lows = [k['low'] for k in klines]
        
        # RSI
        rsi_14 = self.calculate_rsi(closes, 14)
        rsi_6 = self.calculate_rsi(closes, 6)
        
        # EMAs
        ema_12 = sum(closes[-12:]) / 12
        ema_26 = sum(closes[-26:]) / 26 if len(closes) >= 26 else sum(closes) / len(closes)
        
        # Price vs EMA
        price = closes[-1]
        
        # Volatility (ATR simplified)
        tr_list = []
        for i in range(1, min(15, len(klines))):
            tr1 = highs[-i] - lows[-i]
            tr2 = abs(highs[-i] - closes[-i-1])
            tr3 = abs(lows[-i] - closes[-i-1])
            tr_list.append(max(tr1, tr2, tr3))
        atr = sum(tr_list) / len(tr_list) if tr_list else 0
        
        return {
            'price': price,
            'rsi_14': rsi_14,
            'rsi_6': rsi_6,
            'ema_12': ema_12,
            'ema_26': ema_26,
            'atr': atr,
            'trend': 'up' if ema_12 > ema_26 else 'down',
            'volatility': atr / price * 100 if price > 0 else 0
        }


class SignalGenerator:
    """Generates trading signals based on validated strategies."""
    
    def __init__(self):
        self.validated_strategies = [
            'RSI_Oversold',
            'RSI_Overbought',
            'Connors_RSI2'
        ]
    
    def generate_signals(self, indicators: Dict, symbol: str) -> List[Dict]:
        """Generate signals based on indicators."""
        signals = []
        
        if not indicators:
            return signals
        
        price = indicators['price']
        rsi = indicators['rsi_14']
        rsi_6 = indicators['rsi_6']
        atr = indicators['atr']
        
        # Strategy 1: RSI Oversold (Long)
        if rsi < 35:
            tp = price + (atr * 2.5)
            sl = price - (atr * 1.5)
            r_r = (tp - price) / (price - sl) if price > sl else 2
            
            signals.append({
                'symbol': symbol,
                'direction': 'LONG',
                'entry': price,
                'tp': tp,
                'sl': sl,
                'r_r': r_r,
                'confidence': (40 - rsi) / 40,
                'strategy': 'RSI_Oversold',
                'reason': f'RSI oversold ({rsi:.1f})'
            })
        
        # Strategy 2: RSI Overbought (Short)
        if rsi > 65:
            tp = price - (atr * 2.5)
            sl = price + (atr * 1.5)
            r_r = (price - tp) / (sl - price) if sl > price else 2
            
            signals.append({
                'symbol': symbol,
                'direction': 'SHORT',
                'entry': price,
                'tp': tp,
                'sl': sl,
                'r_r': r_r,
                'confidence': (rsi - 60) / 40,
                'strategy': 'RSI_Overbought',
                'reason': f'RSI overbought ({rsi:.1f})'
            })
        
        # Strategy 3: Connors RSI-2 (Mean Reversion)
        if rsi_6 < 20 and rsi < 40:
            tp = price + (atr * 2)
            sl = price - (atr * 1.2)
            
            signals.append({
                'symbol': symbol,
                'direction': 'LONG',
                'entry': price,
                'tp': tp,
                'sl': sl,
                'r_r': 1.7,
                'confidence': (25 - rsi_6) / 25,
                'strategy': 'Connors_RSI2',
                'reason': f'Connors RSI-2 ({rsi_6:.1f})'
            })
        
        return signals


class PaperTradingEngine:
    """Main paper trading engine."""
    
    def __init__(self):
        self.portfolio = PaperPortfolio()
        self.data_feed = LiveDataFeed()
        self.signal_generator = SignalGenerator()
        self.running = False
        self.trade_history = []
        
        # Risk parameters
        self.max_positions = 999  # TESTING SPRINT: was 5, uncapped
        self.position_size_pct = 0.10  # 10% per trade
        self.max_daily_loss = 0.03  # 3% daily loss limit
        
        self.load_state()
    
    def load_state(self):
        """Load previous paper trading state."""
        state_file = Path('genome/results/paper_trading_state.json')
        if state_file.exists():
            with open(state_file) as f:
                state = json.load(f)
                self.portfolio.initial_capital = state.get('initial_capital', 10000)
                self.portfolio.current_equity = state.get('current_equity', 10000)
                self.portfolio.total_trades = state.get('total_trades', 0)
                self.portfolio.winning_trades = state.get('winning_trades', 0)
                self.portfolio.losing_trades = state.get('losing_trades', 0)
                self.trade_history = state.get('trade_history', [])
            logger.info(f"Loaded previous state: ${self.portfolio.current_equity:.2f}")
    
    def save_state(self):
        """Save current paper trading state."""
        state = {
            'timestamp': datetime.now().isoformat(),
            'initial_capital': self.portfolio.initial_capital,
            'current_equity': self.portfolio.current_equity,
            'total_trades': self.portfolio.total_trades,
            'winning_trades': self.portfolio.winning_trades,
            'losing_trades': self.portfolio.losing_trades,
            'open_positions': [asdict(t) for t in self.portfolio.open_positions],
            'trade_history': self.trade_history
        }
        
        output_path = Path('genome/results/paper_trading_state.json')
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(state, f, indent=2, default=str)
    
    def check_exit_conditions(self, trade: PaperTrade, indicators: Dict):
        """Check if trade should be exited."""
        price = indicators['price']
        
        # Check TP
        if trade.direction == 'LONG' and price >= trade.exit_price * 0.995:
            return True, 'TP_HIT', price
        if trade.direction == 'SHORT' and price <= trade.exit_price * 1.005:
            return True, 'TP_HIT', price
        
        # Check SL
        if trade.direction == 'LONG' and price <= trade.entry_price * 0.985:
            return True, 'SL_HIT', price
        if trade.direction == 'SHORT' and price >= trade.entry_price * 1.015:
            return True, 'SL_HIT', price
        
        # Time-based exit (90 minutes)
        hold_time = (datetime.now() - trade.entry_time).total_seconds() / 60
        if hold_time > 90:
            return True, 'TIME_EXIT', price
        
        return False, None, price
    
    def execute_trade(self, signal: Dict):
        """Execute a paper trade."""
        # Check if we have capacity
        if len(self.portfolio.open_positions) >= self.max_positions:
            return
        
        # Check if symbol already in portfolio
        if any(t.symbol == signal['symbol'] and t.status == 'open' for t in self.portfolio.open_positions):
            return
        
        # Calculate position size
        position_size = self.portfolio.current_equity * self.position_size_pct
        
        trade = PaperTrade(
            trade_id=f"PT_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{signal['symbol']}",
            symbol=signal['symbol'],
            direction=signal['direction'],
            entry_price=signal['entry'],
            exit_price=signal['tp'],
            position_size_usd=position_size,
            strategy=signal['strategy']
        )
        
        self.portfolio.open_positions.append(trade)
        self.portfolio.total_trades += 1
        
        logger.info(f"[ENTRY] {trade.direction} {trade.symbol} @ ${trade.entry_price:.4f}")
        logger.info(f"        TP: ${trade.exit_price:.4f} | Strategy: {trade.strategy}")
        
        self.save_state()
    
    def close_trade(self, trade: PaperTrade, exit_price: float, reason: str):
        """Close a paper trade."""
        trade.exit_time = datetime.now()
        trade.exit_price = exit_price
        trade.exit_reason = reason
        trade.status = 'closed'
        
        # Calculate PnL
        if trade.direction == 'LONG':
            trade.pnl_pct = (exit_price - trade.entry_price) / trade.entry_price * 100
        else:
            trade.pnl_pct = (trade.entry_price - exit_price) / trade.entry_price * 100
        
        trade.pnl_usd = trade.position_size_usd * (trade.pnl_pct / 100)
        
        # Update portfolio
        self.portfolio.current_equity += trade.pnl_usd
        self.portfolio.closed_trades.append(trade)
        self.portfolio.open_positions.remove(trade)
        
        if trade.pnl_usd > 0:
            self.portfolio.winning_trades += 1
        else:
            self.portfolio.losing_trades += 1
        
        # Update max drawdown
        if self.portfolio.current_equity > self.portfolio.peak_equity:
            self.portfolio.peak_equity = self.portfolio.current_equity
        else:
            dd = (self.portfolio.peak_equity - self.portfolio.current_equity) / self.portfolio.peak_equity
            self.portfolio.max_drawdown = max(self.portfolio.max_drawdown, dd)
        
        # Record trade
        self.trade_history.append({
            'time': datetime.now().isoformat(),
            'symbol': trade.symbol,
            'direction': trade.direction,
            'pnl_pct': trade.pnl_pct,
            'pnl_usd': trade.pnl_usd,
            'reason': reason
        })
        
        emoji = "PROFIT" if trade.pnl_usd > 0 else "LOSS"
        logger.info(f"[{emoji}] {trade.direction} {trade.symbol}: {trade.pnl_pct:+.2f}% (${trade.pnl_usd:+.2f}) | {reason}")
        
        self.save_state()
    
    def run_cycle(self):
        """Run one trading cycle."""
        logger.info(f"\n{'='*60}")
        logger.info(f"Paper Trading Cycle - {datetime.now().strftime('%H:%M:%S')}")
        logger.info(f"Equity: ${self.portfolio.current_equity:.2f} | Open: {len(self.portfolio.open_positions)}")
        logger.info('='*60)
        
        # Update open positions
        for trade in list(self.portfolio.open_positions):
            indicators = self.data_feed.calculate_indicators(trade.symbol)
            should_exit, reason, price = self.check_exit_conditions(trade, indicators)
            
            if should_exit:
                self.close_trade(trade, price, reason)
        
        # Look for new signals
        prices = self.data_feed.fetch_current_prices()
        
        for symbol in SYMBOLS:
            if len(self.portfolio.open_positions) >= self.max_positions:
                break
            
            indicators = self.data_feed.calculate_indicators(symbol)
            signals = self.signal_generator.generate_signals(indicators, symbol)
            
            # Take the highest confidence signal
            if signals:
                best_signal = max(signals, key=lambda x: x['confidence'])
                if best_signal['confidence'] >= 0.6:
                    self.execute_trade(best_signal)
        
        self.save_state()
    
    def generate_report(self):
        """Generate paper trading performance report."""
        total_return = (self.portfolio.current_equity - self.portfolio.initial_capital) / self.portfolio.initial_capital * 100
        win_rate = self.portfolio.winning_trades / self.portfolio.total_trades if self.portfolio.total_trades > 0 else 0
        
        print("\n" + "="*70)
        print("  PAPER TRADING PERFORMANCE REPORT")
        print("="*70)
        print(f"\nPeriod: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"\n[PORTFOLIO SUMMARY]")
        print(f"  Initial Capital: ${self.portfolio.initial_capital:.2f}")
        print(f"  Current Equity: ${self.portfolio.current_equity:.2f}")
        print(f"  Total Return: {total_return:+.2f}%")
        print(f"  Max Drawdown: {self.portfolio.max_drawdown:.2%}")
        
        print(f"\n[TRADE STATISTICS]")
        print(f"  Total Trades: {self.portfolio.total_trades}")
        print(f"  Winning: {self.portfolio.winning_trades}")
        print(f"  Losing: {self.portfolio.losing_trades}")
        print(f"  Win Rate: {win_rate:.1%}")
        
        if self.portfolio.total_trades > 0:
            total_pnl = sum(t['pnl_usd'] for t in self.trade_history)
            avg_trade = total_pnl / self.portfolio.total_trades
            print(f"  Total PnL: ${total_pnl:.2f}")
            print(f"  Avg Trade: ${avg_trade:.2f}")
        
        print(f"\n[OPEN POSITIONS]")
        if self.portfolio.open_positions:
            for trade in self.portfolio.open_positions:
                hold_time = (datetime.now() - trade.entry_time).total_seconds() / 60
                print(f"  {trade.direction} {trade.symbol} @ ${trade.entry_price:.4f} ({hold_time:.0f} min)")
        else:
            print("  No open positions")
        
        print(f"\n[RECENT TRADES]")
        for trade in self.trade_history[-5:]:
            emoji = "+" if trade['pnl_usd'] > 0 else "-"
            print(f"  {emoji} {trade['direction']} {trade['symbol']}: {trade['pnl_pct']:+.2f}% ({trade['reason']})")
        
        print("\n" + "="*70 + "\n")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Paper Trading System')
    parser.add_argument('--start', action='store_true', help='Start paper trading')
    parser.add_argument('--status', action='store_true', help='Check status')
    parser.add_argument('--report', action='store_true', help='Generate report')
    parser.add_argument('--cycles', type=int, default=10, help='Number of cycles to run')
    
    args = parser.parse_args()
    
    engine = PaperTradingEngine()
    
    if args.start:
        print(f"\nStarting Paper Trading System...")
        print(f"Initial Capital: ${engine.portfolio.initial_capital:.2f}")
        print(f"Position Size: {engine.position_size_pct*100}% per trade")
        print(f"Max Positions: {engine.max_positions}")
        print(f"\nRunning {args.cycles} cycles (approx {args.cycles * 2} minutes)...\n")
        
        for i in range(args.cycles):
            engine.run_cycle()
            if i < args.cycles - 1:
                time.sleep(120)  # Wait 2 minutes between cycles
        
        engine.generate_report()
    
    elif args.status:
        engine.generate_report()
    
    elif args.report:
        engine.generate_report()
    
    else:
        print("Paper Trading System")
        print("\nUsage:")
        print("  --start        Start paper trading (default 10 cycles)")
        print("  --status       Check current status")
        print("  --report       Generate full report")
        print("  --cycles N     Run N cycles (each ~2 min apart)")
        print("\nExample:")
        print("  python paper_trading_system.py --start --cycles 20")


if __name__ == "__main__":
    main()
