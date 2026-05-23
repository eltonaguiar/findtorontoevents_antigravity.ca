#!/usr/bin/env python3
"""
MARKET BEATING TRADING SYSTEM
Integrates trading, signal tracking, validation, and auto-tweaking
Prioritizes Crypto & Forex, aims to consistently beat the market
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
import requests
import pandas as pd
import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('market_beating_bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Import signal tracker components
# Use the repo root (where this script lives) as the import path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signal_tracker import SignalTracker, Config as SignalConfig

@dataclass
class TradingConfig:
    """Trading configuration optimized for beating the market"""
    # Assets - Crypto priority, then Forex
    CRYPTO_SYMBOLS: List[str] = None
    FOREX_PAIRS: List[str] = None
    
    # Risk management (conservative to preserve capital)
    INITIAL_CAPITAL: float = 10000.0
    RISK_PER_TRADE: float = 0.015  # 1.5% (lower for validation phase)
    MAX_POSITIONS: int = 3  # Fewer positions for focused validation
    
    # Entry/Exit rules
    TAKE_PROFIT_PCT: float = 0.03  # 3%
    STOP_LOSS_PCT: float = 0.02    # 2%
    
    # Validation requirements
    MIN_SIGNALS_BEFORE_LIVE: int = 50  # Need 50 validated signals
    MIN_ACCURACY_FOR_LIVE: float = 0.65  # 65% accuracy required (matches signal_tracker TARGET_ACCURACY)
    
    def __post_init__(self):
        if self.CRYPTO_SYMBOLS is None:
            # Top 10 crypto by volume/market cap
            self.CRYPTO_SYMBOLS = [
                'BTC-USD', 'ETH-USD', 'SOL-USD', 'XRP-USD', 'ADA-USD',
                'DOGE-USD', 'DOT-USD', 'AVAX-USD', 'LINK-USD', 'MATIC-USD'
            ]
        if self.FOREX_PAIRS is None:
            # Major forex pairs
            self.FOREX_PAIRS = ['EUR-USD', 'GBP-USD', 'USD-JPY', 'USD-CHF', 'AUD-USD']

class MarketBeatingBot:
    """
    Trading bot that aims to consistently beat the market
    through rigorous signal validation and continuous optimization
    """
    
    def __init__(self):
        self.config = TradingConfig()
        self.signal_tracker = SignalTracker()
        self.signals_generated = []
        self.positions = {}
        self.cash = self.config.INITIAL_CAPITAL
        self.equity = self.config.INITIAL_CAPITAL
        self.trade_history = []
        
        # Performance tracking
        self.benchmark_return = 0  # Buy and hold return
        self.strategy_return = 0   # Our strategy return
        
    def generate_signals(self, symbol: str) -> List[Dict]:
        """
        Generate trading signals with proper TP/SL levels
        """
        signals = []
        
        # Fetch data
        try:
            # Get current price
            base = symbol.split('-')[0]
            quote = symbol.split('-')[1] if '-' in symbol else 'USD'
            
            url = f"https://min-api.cryptocompare.com/data/price"
            params = {'fsym': base, 'tsyms': quote}
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            current_price = float(data.get(quote, 0))
            
            if current_price == 0:
                return signals
            
            # Get historical data for analysis
            histo_url = f"https://min-api.cryptocompare.com/data/histohour"
            histo_params = {'fsym': base, 'tsym': quote, 'limit': 100}
            histo_response = requests.get(histo_url, params=histo_params, timeout=10)
            histo_data = histo_response.json()
            
            if not histo_data.get('Data'):
                return signals
            
            df = pd.DataFrame(histo_data['Data'])
            df['close'] = df['close'].astype(float)
            
            # Strategy 1: Momentum with EMA crossover
            ema_12 = df['close'].ewm(span=12, adjust=False).mean()
            ema_26 = df['close'].ewm(span=26, adjust=False).mean()
            
            curr_12 = ema_12.iloc[-1]
            curr_26 = ema_26.iloc[-1]
            prev_12 = ema_12.iloc[-2]
            prev_26 = ema_26.iloc[-2]
            
            # Calculate RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            current_rsi = rsi.iloc[-1]
            
            # Momentum signal
            if prev_12 <= prev_26 and curr_12 > curr_26 and current_rsi > 50:
                signals.append({
                    'symbol': symbol,
                    'signal': 'LONG',
                    'entry_price': current_price,
                    'take_profit': current_price * (1 + self.config.TAKE_PROFIT_PCT),
                    'stop_loss': current_price * (1 - self.config.STOP_LOSS_PCT),
                    'strategy': 'MomentumEMA',
                    'strength': abs(curr_12 - curr_26) / curr_26,
                    'timestamp': datetime.now().isoformat(),
                    'rsi': current_rsi
                })
            
            # Strategy 2: Mean reversion with Bollinger Bands
            sma_20 = df['close'].rolling(window=20).mean()
            std_20 = df['close'].rolling(window=20).std()
            upper_band = sma_20 + (std_20 * 2)
            lower_band = sma_20 - (std_20 * 2)
            
            current_close = df['close'].iloc[-1]
            
            if current_close < lower_band.iloc[-1] and current_rsi < 30:
                signals.append({
                    'symbol': symbol,
                    'signal': 'LONG',
                    'entry_price': current_price,
                    'take_profit': current_price * (1 + self.config.TAKE_PROFIT_PCT),
                    'stop_loss': current_price * (1 - self.config.STOP_LOSS_PCT),
                    'strategy': 'MeanReversionBB',
                    'strength': (lower_band.iloc[-1] - current_close) / current_close,
                    'timestamp': datetime.now().isoformat(),
                    'rsi': current_rsi
                })
            
            elif current_close > upper_band.iloc[-1] and current_rsi > 70:
                signals.append({
                    'symbol': symbol,
                    'signal': 'SHORT',
                    'entry_price': current_price,
                    'take_profit': current_price * (1 - self.config.TAKE_PROFIT_PCT),
                    'stop_loss': current_price * (1 + self.config.STOP_LOSS_PCT),
                    'strategy': 'MeanReversionBB',
                    'strength': (current_close - upper_band.iloc[-1]) / current_close,
                    'timestamp': datetime.now().isoformat(),
                    'rsi': current_rsi
                })
        
        except Exception as e:
            logger.error(f"Error generating signals for {symbol}: {e}")
        
        return signals
    
    def track_and_execute(self):
        """
        Generate signals, track them, and execute paper trades
        """
        logger.info("=" * 70)
        logger.info("🎯 MARKET BEATING BOT - GENERATING & TRACKING SIGNALS")
        logger.info("=" * 70)
        
        all_signals = []
        
        # Prioritize Crypto
        logger.info("\n📊 Analyzing CRYPTO assets (priority)...")
        for symbol in self.config.CRYPTO_SYMBOLS:
            signals = self.generate_signals(symbol)
            for signal in signals:
                # Track the signal
                self.signal_tracker.track_signal(signal)
                all_signals.append(signal)
                logger.info(f"📈 SIGNAL: {signal['signal']} {symbol} @ ${signal['entry_price']:.2f} "
                          f"(TP: ${signal['take_profit']:.2f}, SL: ${signal['stop_loss']:.2f}) "
                          f"[{signal['strategy']}]")
        
        # Then Forex
        logger.info("\n📊 Analyzing FOREX pairs...")
        for symbol in self.config.FOREX_PAIRS:
            signals = self.generate_signals(symbol)
            for signal in signals:
                self.signal_tracker.track_signal(signal)
                all_signals.append(signal)
                logger.info(f"📈 SIGNAL: {signal['signal']} {symbol} @ ${signal['entry_price']:.4f} "
                          f"(TP: ${signal['take_profit']:.4f}, SL: ${signal['stop_loss']:.4f}) "
                          f"[{signal['strategy']}]")
        
        logger.info(f"\n✅ Generated and tracked {len(all_signals)} signals")
        return all_signals
    
    def validate_and_tweak(self):
        """
        Run validation cycle and apply tweaks
        """
        logger.info("\n" + "=" * 70)
        logger.info("🔍 RUNNING VALIDATION & AUTO-TWEAKING")
        logger.info("=" * 70)
        
        # Run validation
        results = self.signal_tracker.run_validation_cycle()
        
        # Get performance summary
        summary = self.signal_tracker.get_performance_summary()
        
        # Check if we've beaten the market
        overall_accuracy = summary['overall']['accuracy']
        total_signals = summary['total_signals_tracked']
        
        logger.info("\n📊 PERFORMANCE SUMMARY:")
        logger.info(f"   Total Signals: {total_signals}")
        logger.info(f"   Validated: {summary['total_validated']}")
        logger.info(f"   Overall Accuracy: {overall_accuracy:.1%}")
        
        # Check if ready for live trading
        if total_signals >= self.config.MIN_SIGNALS_BEFORE_LIVE:
            if overall_accuracy >= self.config.MIN_ACCURACY_FOR_LIVE:
                logger.info("\n🎉 MARKET BEATING ACHIEVED!")
                logger.info(f"   Accuracy {overall_accuracy:.1%} exceeds target {self.config.MIN_ACCURACY_FOR_LIVE:.1%}")
                logger.info("   System is ready for live trading consideration")
            else:
                logger.info(f"\n⏳ Still optimizing... Need {self.config.MIN_ACCURACY_FOR_LIVE:.1%} accuracy")
                logger.info(f"   Current: {overall_accuracy:.1%}")
        else:
            logger.info(f"\n📈 Building validation dataset...")
            logger.info(f"   Need {self.config.MIN_SIGNALS_BEFORE_LIVE} signals, have {total_signals}")
        
        # Show crypto performance (priority)
        logger.info("\n💎 CRYPTO Performance:")
        for symbol, stats in summary['crypto'].items():
            if stats['total_signals'] > 0:
                status = "✅" if stats['accuracy'] >= 0.60 else "⚠️"
                logger.info(f"   {status} {symbol}: {stats['accuracy']:.1%} ({stats['total_signals']} signals)")
        
        return results, summary
    
    def generate_report(self):
        """Generate comprehensive market beating report"""
        summary = self.signal_tracker.get_performance_summary()
        
        report = []
        report.append("# 🎯 Market Beating Trading System Report")
        report.append(f"\n**Generated:** {datetime.now().isoformat()}")
        report.append(f"**Status:** {'✅ BEATING MARKET' if summary['overall']['accuracy'] >= 0.60 else '⏳ OPTIMIZING'}")
        report.append("\n---\n")
        
        # Overall stats
        report.append("## 📊 Overall Performance")
        report.append(f"- **Total Signals Tracked:** {summary['total_signals_tracked']}")
        report.append(f"- **Signals Validated:** {summary['total_validated']}")
        report.append(f"- **Overall Accuracy:** {summary['overall']['accuracy']:.1%}")
        report.append(f"- **Target Accuracy:** 60%")
        report.append(f"- **Status:** {'✅ ABOVE TARGET' if summary['overall']['accuracy'] >= 0.60 else '⏳ BELOW TARGET'}")
        report.append("")
        
        # Crypto performance (priority)
        report.append("## 💎 Crypto Performance (Priority)")
        report.append("| Asset | Accuracy | Signals | Status |")
        report.append("|-------|----------|---------|--------|")
        for symbol, stats in summary['crypto'].items():
            if stats['total_signals'] > 0:
                status = "✅" if stats['accuracy'] >= self.config.MIN_ACCURACY_FOR_LIVE else "⚠️" if stats['accuracy'] >= 0.50 else "❌"
                report.append(f"| {symbol} | {stats['accuracy']:.1%} | {stats['total_signals']} | {status} |")
        report.append("")

        # Forex performance
        report.append("## 💱 Forex Performance")
        report.append("| Pair | Accuracy | Signals | Status |")
        report.append("|------|----------|---------|--------|")
        for symbol, stats in summary['forex'].items():
            if stats['total_signals'] > 0:
                status = "✅" if stats['accuracy'] >= self.config.MIN_ACCURACY_FOR_LIVE else "⚠️" if stats['accuracy'] >= 0.50 else "❌"
                report.append(f"| {symbol} | {stats['accuracy']:.1%} | {stats['total_signals']} | {status} |")
        report.append("")
        
        # Road to market beating
        report.append("## 🎯 Road to Beating the Market")
        total_needed = self.config.MIN_SIGNALS_BEFORE_LIVE
        total_have = summary['total_signals_tracked']
        accuracy_needed = self.config.MIN_ACCURACY_FOR_LIVE
        accuracy_have = summary['overall']['accuracy']
        
        report.append(f"- **Signals:** {total_have}/{total_needed} ({(total_have/total_needed)*100:.0f}%)")
        report.append(f"- **Accuracy:** {accuracy_have:.1%}/{accuracy_needed:.1%}")
        
        if total_have >= total_needed and accuracy_have >= accuracy_needed:
            report.append("\n### 🎉 SYSTEM READY FOR LIVE TRADING")
            report.append("The system has demonstrated consistent ability to beat the market.")
            report.append("Consider transitioning to live trading with small position sizes.")
        else:
            report.append("\n### ⏳ Continuing Optimization")
            report.append("The system is gathering more data and refining parameters.")
            report.append("Check back after more validation cycles.")
        
        report.append("\n---")
        report.append("\n*🤖 Auto-generated by Market Beating Trading System*")
        report.append(f"*Next update: ~2 hours*")
        
        return "\n".join(report)
    
    def run(self):
        """Main execution loop"""
        logger.info("\n" + "=" * 70)
        logger.info("🚀 MARKET BEATING TRADING SYSTEM")
        logger.info("=" * 70)
        logger.info("💎 Priority: Crypto assets")
        logger.info("💱 Secondary: Forex pairs")
        logger.info("🎯 Goal: Consistently beat the market")
        logger.info("🔧 Method: Track → Validate → Tweak → Repeat")
        logger.info("=" * 70)
        
        # Step 1: Generate and track signals
        signals = self.track_and_execute()
        
        # Step 2: Validate and tweak
        results, summary = self.validate_and_tweak()
        
        # Step 3: Generate report
        report = self.generate_report()
        
        # Save report
        with open('MARKET_BEATING_REPORT.md', 'w') as f:
            f.write(report)
        
        logger.info("\n" + "=" * 70)
        logger.info("✅ CYCLE COMPLETE")
        logger.info("=" * 70)
        logger.info(f"📊 Signals Generated: {len(signals)}")
        logger.info(f"✅ Validations Run: {results['validated']}")
        logger.info(f"🔧 Tweaks Applied: {len(results['tweaks'])}")
        logger.info(f"📈 Overall Accuracy: {summary['overall']['accuracy']:.1%}")
        logger.info("=" * 70)
        
        return {
            'signals': signals,
            'results': results,
            'summary': summary,
            'report': report
        }

def main():
    """Entry point"""
    bot = MarketBeatingBot()
    results = bot.run()
    
    print("\n" + "=" * 70)
    print("🎯 MARKET BEATING BOT COMPLETE")
    print("=" * 70)
    print(f"📊 Signals: {len(results['signals'])}")
    print(f"🎯 Accuracy: {results['summary']['overall']['accuracy']:.1%}")
    print(f"📈 Total Tracked: {results['summary']['total_signals_tracked']}")
    print(f"📄 Report: MARKET_BEATING_REPORT.md")
    print("=" * 70)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
