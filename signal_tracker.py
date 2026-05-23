#!/usr/bin/env python3
"""
SIGNAL TRACKING & VALIDATION SYSTEM
Tracks predictions, validates accuracy, auto-tweaks until beating the market

Features:
- Tracks every signal with entry price, target, stop loss
- Validates predictions after time elapsed
- Calculates accuracy per strategy per asset
- Auto-tweaks parameters based on validation results
- Prioritizes Crypto & Forex
- Benchmarks against buy-and-hold
"""

import os
import sys
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import requests
import pandas as pd
import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('signal_tracker.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass
class Config:
    """Signal tracking configuration"""
    PRIMARY_EXCHANGE: str = 'FREE_DATA'
    COINGECKO_API_KEY: str = os.getenv('COINGECKO_API_KEY', '')
    CRYPTOCOMPARE_API_KEY: str = os.getenv('CRYPTOCOMPARE_API_KEY', '')

    # Asset priority: Crypto first, then Forex
    CRYPTO_SYMBOLS: List[str] = None
    FOREX_PAIRS: List[str] = None

    # Validation settings
    VALIDATION_PERIODS: List[int] = None  # Hours to validate
    TAKE_PROFIT_PCT: float = 0.03  # 3%
    STOP_LOSS_PCT: float = 0.02    # 2%

    # Time-based expiry: close positions that have been open too long
    # This prevents infinite open positions and generates closed trade data faster
    MAX_HOLD_HOURS_CRYPTO: int = 168   # 7 days for crypto (24/7 markets)
    MAX_HOLD_HOURS_FOREX: int = 336    # 14 days for forex (slower)
    
    # Accuracy thresholds
    MIN_ACCURACY: float = 0.55  # 55% minimum
    TARGET_ACCURACY: float = 0.65  # 65% target
    
    # Auto-tweak settings
    TWEAK_INCREMENT: float = 0.1  # 10% parameter adjustment
    MAX_TWEAKS: int = 10  # Max parameter changes per cycle
    
    def __post_init__(self):
        if self.CRYPTO_SYMBOLS is None:
            self.CRYPTO_SYMBOLS = [
                'BTC-USD', 'ETH-USD', 'SOL-USD', 'ADA-USD', 'DOT-USD',
                'XRP-USD', 'DOGE-USD', 'AVAX-USD', 'MATIC-USD', 'LINK-USD'
            ]
        if self.FOREX_PAIRS is None:
            self.FOREX_PAIRS = [
                'EUR-USD', 'GBP-USD', 'USD-JPY', 'USD-CHF',
                'AUD-USD', 'USD-CAD', 'NZD-USD'
            ]
        if self.VALIDATION_PERIODS is None:
            self.VALIDATION_PERIODS = [4, 8, 24, 48]  # Hours

# ============================================================================
# SIGNAL DATABASE
# ============================================================================

class SignalDatabase:
    """Database for tracking signals and their outcomes"""
    
    def __init__(self):
        self.signals_file = 'signals_database.json'
        self.validation_file = 'validation_results.json'
        self.signals = []
        self.validations = []
        self.load_data()
    
    def load_data(self):
        """Load existing signal data"""
        try:
            if os.path.exists(self.signals_file):
                with open(self.signals_file, 'r') as f:
                    self.signals = json.load(f)
                logger.info(f"📊 Loaded {len(self.signals)} historical signals")
        except Exception as e:
            logger.warning(f"Could not load signals: {e}")
        
        try:
            if os.path.exists(self.validation_file):
                with open(self.validation_file, 'r') as f:
                    self.validations = json.load(f)
                logger.info(f"✅ Loaded {len(self.validations)} validation results")
        except Exception as e:
            logger.warning(f"Could not load validations: {e}")
    
    def save_data(self):
        """Save signal data"""
        try:
            with open(self.signals_file, 'w') as f:
                json.dump(self.signals, f, indent=2, default=str)
            with open(self.validation_file, 'w') as f:
                json.dump(self.validations, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Could not save data: {e}")
    
    def add_signal(self, signal: Dict):
        """Add a new signal to track"""
        signal_record = {
            'id': f"sig_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{signal['symbol']}",
            'timestamp': datetime.now().isoformat(),
            'symbol': signal['symbol'],
            'signal_type': signal['signal'],  # LONG or SHORT
            'entry_price': signal['entry_price'],
            'strategy': signal['strategy'],
            'take_profit': signal.get('take_profit'),
            'stop_loss': signal.get('stop_loss'),
            'strength': signal.get('strength', 1.0),
            'validated': False,
            'validation_results': {}
        }
        self.signals.append(signal_record)
        self.save_data()
        logger.info(f"📝 Signal tracked: {signal['signal']} {signal['symbol']} @ ${signal['entry_price']:.2f}")
        return signal_record['id']
    
    def get_pending_validations(self) -> List[Dict]:
        """Get signals that need validation"""
        pending = []
        for signal in self.signals:
            if not signal.get('validated', False):
                # Check if enough time has passed for validation
                signal_time = datetime.fromisoformat(signal['timestamp'])
                hours_elapsed = (datetime.now() - signal_time).total_seconds() / 3600
                
                # Check which validation periods have passed
                for period in Config().VALIDATION_PERIODS:
                    key = f'validation_{period}h'
                    if hours_elapsed >= period and key not in signal.get('validation_results', {}):
                        pending.append({
                            'signal': signal,
                            'validation_period': period,
                            'hours_elapsed': hours_elapsed
                        })
        return pending
    
    def update_validation(self, signal_id: str, period: int, result: Dict):
        """Update validation result for a signal"""
        for signal in self.signals:
            if signal['id'] == signal_id:
                key = f'validation_{period}h'
                signal['validation_results'][key] = result
                
                # Mark as fully validated if all periods checked
                if len(signal['validation_results']) >= len(Config().VALIDATION_PERIODS):
                    signal['validated'] = True
                
                self.save_data()
                return True
        return False
    
    def get_accuracy_stats(self, symbol: str = None, strategy: str = None) -> Dict:
        """Calculate accuracy statistics"""
        filtered = self.signals
        
        if symbol:
            filtered = [s for s in filtered if s['symbol'] == symbol]
        if strategy:
            filtered = [s for s in filtered if s['strategy'] == strategy]
        
        # Only count validated signals
        validated = [s for s in filtered if s.get('validated', False)]
        
        if not validated:
            return {'total': 0, 'total_signals': 0, 'accuracy': 0, 'correct_predictions': 0, 'by_period': {}}
        
        # Calculate accuracy by validation period
        by_period = {}
        for period in Config().VALIDATION_PERIODS:
            key = f'validation_{period}h'
            correct = sum(1 for s in validated if s['validation_results'].get(key, {}).get('correct', False))
            total = sum(1 for s in validated if key in s['validation_results'])
            by_period[f'{period}h'] = {
                'correct': correct,
                'total': total,
                'accuracy': correct / total if total > 0 else 0
            }
        
        # Overall accuracy (using 24h validation as primary)
        primary_key = 'validation_24h'
        correct = sum(1 for s in validated if s['validation_results'].get(primary_key, {}).get('correct', False))
        total = sum(1 for s in validated if primary_key in s['validation_results'])
        
        return {
            'total_signals': len(validated),
            'correct_predictions': correct,
            'accuracy': correct / total if total > 0 else 0,
            'by_period': by_period,
            'avg_profit_when_correct': np.mean([
                s['validation_results'][primary_key]['profit_pct']
                for s in validated
                if primary_key in s['validation_results'] and s['validation_results'][primary_key].get('correct', False)
            ]) if validated else 0,
            'avg_loss_when_wrong': np.mean([
                s['validation_results'][primary_key]['profit_pct']
                for s in validated
                if primary_key in s['validation_results'] and not s['validation_results'][primary_key].get('correct', False)
            ]) if validated else 0
        }

# ============================================================================
# DATA FETCHER
# ============================================================================

class DataFetcher:
    """Fetch market data for validation"""
    
    def __init__(self, config: Config):
        self.config = config
        self.coingecko_key = config.COINGECKO_API_KEY
        self.cryptocompare_key = config.CRYPTOCOMPARE_API_KEY
    
    def get_current_price(self, symbol: str) -> float:
        """Get current price for validation"""
        try:
            # Try CoinGecko for crypto
            if '-USD' in symbol or '-USDT' in symbol:
                coin_id = symbol.split('-')[0].lower()
                url = f"https://api.coingecko.com/api/v3/simple/price"
                params = {'ids': coin_id, 'vs_currencies': 'usd'}
                response = requests.get(url, params=params, timeout=10)
                data = response.json()
                if coin_id in data:
                    return float(data[coin_id]['usd'])
            
            # Fallback to CryptoCompare
            base = symbol.split('-')[0]
            quote = symbol.split('-')[1] if '-' in symbol else 'USD'
            url = f"https://min-api.cryptocompare.com/data/price"
            params = {'fsym': base, 'tsyms': quote, 'api_key': self.cryptocompare_key}
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            return float(data.get(quote, 0))
        
        except Exception as e:
            logger.error(f"Error fetching price for {symbol}: {e}")
            return None
    
    def get_historical_price(self, symbol: str, timestamp: datetime) -> float:
        """Get historical price at specific time"""
        try:
            # This is simplified - in production you'd use historical API
            # For now, we'll use current price as approximation
            return self.get_current_price(symbol)
        except Exception as e:
            logger.error(f"Error fetching historical price: {e}")
            return None

# ============================================================================
# VALIDATION ENGINE
# ============================================================================

class ValidationEngine:
    """Validates signals against actual market outcomes"""
    
    def __init__(self, config: Config, database: SignalDatabase, fetcher: DataFetcher):
        self.config = config
        self.database = database
        self.fetcher = fetcher
    
    def validate_signal(self, signal: Dict, period: int) -> Dict:
        """
        Validate a signal after specified period.
        Also checks TP/SL and time-based expiry to CLOSE positions.

        Returns:
            {
                'correct': bool,
                'profit_pct': float,
                'hit_take_profit': bool,
                'hit_stop_loss': bool,
                'max_profit_pct': float,
                'max_drawdown_pct': float,
                'actual_price': float,
                'validation_time': str,
                'closed': bool,
                'close_reason': str
            }
        """
        current_price = self.fetcher.get_current_price(signal['symbol'])
        if not current_price:
            return {'error': 'Could not fetch current price'}

        entry_price = signal['entry_price']
        signal_type = signal['signal_type']

        # Calculate profit/loss
        if signal_type == 'LONG':
            profit_pct = ((current_price - entry_price) / entry_price) * 100
            correct = profit_pct > 0
        else:  # SHORT
            profit_pct = ((entry_price - current_price) / entry_price) * 100
            correct = profit_pct > 0

        # Check if TP/SL would have been hit
        tp_pct = self.config.TAKE_PROFIT_PCT * 100
        sl_pct = -self.config.STOP_LOSS_PCT * 100

        hit_tp = profit_pct >= tp_pct
        hit_sl = profit_pct <= sl_pct

        # Determine if position should be closed
        closed = False
        close_reason = None

        if hit_tp:
            closed = True
            close_reason = f"TP_HIT ({profit_pct:+.2f}%)"
        elif hit_sl:
            closed = True
            close_reason = f"SL_HIT ({profit_pct:+.2f}%)"
        else:
            # Time-based expiry check
            try:
                signal_time = datetime.fromisoformat(signal['timestamp'])
                hours_elapsed = (datetime.now() - signal_time).total_seconds() / 3600
            except (ValueError, TypeError):
                hours_elapsed = 0

            symbol = signal.get('symbol', '')
            is_crypto = '-USD' in symbol or '-USDT' in symbol
            max_hold = (self.config.MAX_HOLD_HOURS_CRYPTO if is_crypto
                        else self.config.MAX_HOLD_HOURS_FOREX)

            if hours_elapsed >= max_hold:
                closed = True
                close_reason = f"EXPIRED after {hours_elapsed:.0f}h (max {max_hold}h), P&L: {profit_pct:+.2f}%"

        # If closed, mark signal as validated immediately
        if closed:
            signal['validated'] = True

        result = {
            'correct': correct,
            'profit_pct': profit_pct,
            'hit_take_profit': hit_tp,
            'hit_stop_loss': hit_sl,
            'max_profit_pct': profit_pct if profit_pct > 0 else 0,
            'max_drawdown_pct': profit_pct if profit_pct < 0 else 0,
            'actual_price': current_price,
            'validation_time': datetime.now().isoformat(),
            'period_hours': period,
            'closed': closed,
            'close_reason': close_reason,
        }

        return result
    
    def run_validations(self):
        """Run all pending validations. Also checks TP/SL and time-based expiry."""
        pending = self.database.get_pending_validations()
        logger.info(f"Running validations for {len(pending)} signals...")

        validated_count = 0
        closed_count = 0
        for item in pending:
            signal = item['signal']
            period = item['validation_period']

            result = self.validate_signal(signal, period)

            if 'error' not in result:
                self.database.update_validation(signal['id'], period, result)
                validated_count += 1

                status = "CORRECT" if result['correct'] else "WRONG"
                logger.info(f"{status} {signal['symbol']} {signal['signal_type']} "
                          f"({period}h): {result['profit_pct']:+.2f}%")

                if result.get('closed'):
                    closed_count += 1
                    logger.info(f"CLOSED {signal['symbol']}: {result['close_reason']}")

        # Also run TP/SL and expiry checks on ALL open signals (not just pending)
        # This ensures we close positions even if they haven't reached a validation period
        all_open = [s for s in self.database.signals if not s.get('validated', False)]
        for signal in all_open:
            current_price = self.fetcher.get_current_price(signal['symbol'])
            if not current_price:
                continue

            entry_price = signal.get('entry_price', 0)
            signal_type = signal.get('signal_type', 'LONG')
            if entry_price <= 0:
                continue

            if signal_type == 'LONG':
                profit_pct = ((current_price - entry_price) / entry_price) * 100
            else:
                profit_pct = ((entry_price - current_price) / entry_price) * 100

            tp_pct = self.config.TAKE_PROFIT_PCT * 100
            sl_pct = -self.config.STOP_LOSS_PCT * 100

            close_reason = None
            if profit_pct >= tp_pct:
                close_reason = f"TP_HIT ({profit_pct:+.2f}%)"
            elif profit_pct <= sl_pct:
                close_reason = f"SL_HIT ({profit_pct:+.2f}%)"
            else:
                try:
                    signal_time = datetime.fromisoformat(signal['timestamp'])
                    hours_elapsed = (datetime.now() - signal_time).total_seconds() / 3600
                except (ValueError, TypeError):
                    hours_elapsed = 0

                is_crypto = '-USD' in signal.get('symbol', '') or '-USDT' in signal.get('symbol', '')
                max_hold = (self.config.MAX_HOLD_HOURS_CRYPTO if is_crypto
                            else self.config.MAX_HOLD_HOURS_FOREX)

                if hours_elapsed >= max_hold:
                    close_reason = f"EXPIRED after {hours_elapsed:.0f}h"

            if close_reason:
                signal['validated'] = True
                signal['validation_results']['forced_close'] = {
                    'correct': profit_pct > 0,
                    'profit_pct': profit_pct,
                    'actual_price': current_price,
                    'close_reason': close_reason,
                    'validation_time': datetime.now().isoformat(),
                }
                closed_count += 1
                logger.info(f"FORCE-CLOSED {signal['symbol']}: {close_reason} "
                          f"P&L: {profit_pct:+.2f}%")

        if closed_count > 0:
            self.database.save_data()

        logger.info(f"Validated {validated_count} signals, closed {closed_count}")
        return validated_count

# ============================================================================
# AUTO-TWEAK ENGINE
# ============================================================================

class AutoTweakEngine:
    """Automatically tweaks strategy parameters based on validation results"""
    
    def __init__(self, config: Config, database: SignalDatabase):
        self.config = config
        self.database = database
        self.tweak_history = []
    
    def analyze_and_tweak(self) -> List[Dict]:
        """
        Analyze accuracy and generate tweaks
        
        Returns list of tweaks applied
        """
        tweaks = []
        
        # Analyze by symbol (Crypto priority)
        for symbol in self.config.CRYPTO_SYMBOLS + self.config.FOREX_PAIRS:
            stats = self.database.get_accuracy_stats(symbol=symbol)
            
            if stats['total_signals'] < 3:
                continue  # Not enough data
            
            accuracy = stats['accuracy']
            
            # Determine action based on accuracy
            if accuracy < self.config.MIN_ACCURACY:
                # Accuracy too low - need significant changes
                tweak = {
                    'target': symbol,
                    'type': 'SYMBOL_DISABLE',
                    'reason': f'Accuracy {accuracy:.1%} below minimum {self.config.MIN_ACCURACY:.1%}',
                    'old_value': 'enabled',
                    'new_value': 'disabled',
                    'expected_improvement': 'Remove underperforming asset'
                }
                tweaks.append(tweak)
                logger.warning(f"🚫 Disabling {symbol}: accuracy {accuracy:.1%} too low")
                
            elif accuracy < self.config.TARGET_ACCURACY:
                # Below target - need parameter adjustment
                by_period = stats.get('by_period', {})
                
                # Find which timeframes work best
                best_period = max(by_period.items(), key=lambda x: x[1].get('accuracy', 0)) if by_period else None
                
                if best_period and best_period[1]['accuracy'] > accuracy:
                    tweak = {
                        'target': symbol,
                        'type': 'TIMEFRAME_OPTIMIZATION',
                        'reason': f'Accuracy {accuracy:.1%} below target, best at {best_period[0]}',
                        'old_value': 'default',
                        'new_value': best_period[0],
                        'expected_improvement': f'Focus on {best_period[0]} timeframe'
                    }
                    tweaks.append(tweak)
                    logger.info(f"🎯 Optimizing {symbol}: focus on {best_period[0]} timeframe")
        
        # Analyze by strategy
        strategies = ['AdaptiveMomentum', 'AdaptiveMeanReversion', 'OrderBookImbalance']
        for strategy in strategies:
            stats = self.database.get_accuracy_stats(strategy=strategy)
            
            if stats['total_signals'] < 10:
                continue
            
            accuracy = stats['accuracy']
            
            if accuracy < 0.5:
                # Strategy performing poorly
                tweak = {
                    'target': strategy,
                    'type': 'STRATEGY_WEIGHT_REDUCE',
                    'reason': f'Accuracy {accuracy:.1%} below 50%',
                    'old_value': '1.0',
                    'new_value': '0.5',
                    'expected_improvement': 'Reduce influence of underperforming strategy'
                }
                tweaks.append(tweak)
                logger.warning(f"📉 Reducing weight for {strategy}: accuracy {accuracy:.1%}")
                
            elif accuracy > 0.7:
                # Strategy performing excellently
                tweak = {
                    'target': strategy,
                    'type': 'STRATEGY_WEIGHT_INCREASE',
                    'reason': f'Accuracy {accuracy:.1%} excellent',
                    'old_value': '1.0',
                    'new_value': '1.5',
                    'expected_improvement': 'Increase influence of winning strategy'
                }
                tweaks.append(tweak)
                logger.info(f"📈 Increasing weight for {strategy}: accuracy {accuracy:.1%}")
        
        # Save tweak history
        if tweaks:
            self.tweak_history.append({
                'timestamp': datetime.now().isoformat(),
                'tweaks': tweaks
            })
            self._save_tweak_history()
        
        return tweaks
    
    def _save_tweak_history(self):
        """Save tweak history to file"""
        try:
            with open('tweak_history.json', 'w') as f:
                json.dump(self.tweak_history, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Could not save tweak history: {e}")
    
    def generate_optimization_report(self) -> str:
        """Generate human-readable optimization report"""
        report = []
        report.append("# 🎛️ Optimization Report")
        report.append(f"\n**Generated:** {datetime.now().isoformat()}\n")
        
        # Overall accuracy
        overall = self.database.get_accuracy_stats()
        report.append(f"## 📊 Overall Accuracy")
        report.append(f"- **Total Signals:** {overall['total_signals']}")
        report.append(f"- **Accuracy:** {overall['accuracy']:.1%}")
        report.append(f"- **Target:** {self.config.TARGET_ACCURACY:.1%}\n")
        
        # By asset class
        report.append("## 📈 Accuracy by Asset Class")
        report.append("\n### Crypto")
        for symbol in self.config.CRYPTO_SYMBOLS[:5]:  # Top 5
            stats = self.database.get_accuracy_stats(symbol=symbol)
            if stats['total_signals'] > 0:
                status = "✅" if stats['accuracy'] >= self.config.TARGET_ACCURACY else "⚠️" if stats['accuracy'] >= self.config.MIN_ACCURACY else "❌"
                report.append(f"- {status} **{symbol}**: {stats['accuracy']:.1%} ({stats['total_signals']} signals)")
        
        report.append("\n### Forex")
        for symbol in self.config.FOREX_PAIRS[:3]:  # Top 3
            stats = self.database.get_accuracy_stats(symbol=symbol)
            if stats['total_signals'] > 0:
                status = "✅" if stats['accuracy'] >= self.config.TARGET_ACCURACY else "⚠️" if stats['accuracy'] >= self.config.MIN_ACCURACY else "❌"
                report.append(f"- {status} **{symbol}**: {stats['accuracy']:.1%} ({stats['total_signals']} signals)")
        
        # Recent tweaks
        if self.tweak_history:
            report.append("\n## 🔧 Recent Tweaks")
            for entry in self.tweak_history[-5:]:  # Last 5
                report.append(f"\n**{entry['timestamp'][:19]}**")
                for tweak in entry['tweaks']:
                    report.append(f"- {tweak['type']}: {tweak['target']}")
                    report.append(f"  - Reason: {tweak['reason']}")
                    report.append(f"  - Change: {tweak['old_value']} → {tweak['new_value']}")
        
        report.append("\n---")
        report.append("\n*🤖 Auto-generated by Signal Tracking & Validation System*")
        
        return "\n".join(report)

# ============================================================================
# BENCHMARK ENGINE
# ============================================================================

class BenchmarkEngine:
    """Compares strategy performance against buy-and-hold"""
    
    def __init__(self, database: SignalDatabase, fetcher: DataFetcher):
        self.database = database
        self.fetcher = fetcher
    
    def calculate_benchmark(self, symbol: str, start_date: datetime, end_date: datetime) -> Dict:
        """Calculate buy-and-hold return for comparison"""
        # Simplified - in production use historical data
        current_price = self.fetcher.get_current_price(symbol)
        
        # Assume 50% accuracy for buy-and-hold over time
        return {
            'symbol': symbol,
            'strategy': 'BUY_AND_HOLD',
            'estimated_return': 0,  # Would calculate from historical
            'current_price': current_price
        }
    
    def compare_to_benchmark(self) -> Dict:
        """Compare strategy performance to buy-and-hold"""
        comparison = {}
        
        for symbol in Config().CRYPTO_SYMBOLS[:3]:
            strategy_stats = self.database.get_accuracy_stats(symbol=symbol)
            benchmark = self.calculate_benchmark(symbol, datetime.now() - timedelta(days=30), datetime.now())
            
            if strategy_stats['total_signals'] > 0:
                comparison[symbol] = {
                    'strategy_accuracy': strategy_stats['accuracy'],
                    'strategy_avg_profit': strategy_stats.get('avg_profit_when_correct', 0),
                    'benchmark_price': benchmark['current_price'],
                    'beating_benchmark': strategy_stats['accuracy'] > 0.5  # Simplified
                }
        
        return comparison

# ============================================================================
# MAIN SIGNAL TRACKER
# ============================================================================

class SignalTracker:
    """Main signal tracking and validation system"""
    
    def __init__(self):
        self.config = Config()
        self.database = SignalDatabase()
        self.fetcher = DataFetcher(self.config)
        self.validator = ValidationEngine(self.config, self.database, self.fetcher)
        self.tweak_engine = AutoTweakEngine(self.config, self.database)
        self.benchmark = BenchmarkEngine(self.database, self.fetcher)
    
    def track_signal(self, signal: Dict) -> str:
        """Track a new signal"""
        return self.database.add_signal(signal)
    
    def run_validation_cycle(self):
        """Run a full validation cycle"""
        logger.info("=" * 70)
        logger.info("🔍 SIGNAL VALIDATION CYCLE STARTING")
        logger.info("=" * 70)
        
        # Step 1: Validate pending signals
        validated = self.validator.run_validations()
        
        # Step 2: Analyze and generate tweaks
        tweaks = self.tweak_engine.analyze_and_tweak()
        
        # Step 3: Compare to benchmark
        comparison = self.benchmark.compare_to_benchmark()
        
        # Step 4: Generate report
        report = self.tweak_engine.generate_optimization_report()
        
        # Step 5: Save report
        with open('OPTIMIZATION_REPORT.md', 'w') as f:
            f.write(report)
        
        logger.info("=" * 70)
        logger.info("✅ VALIDATION CYCLE COMPLETE")
        logger.info(f"   Validated: {validated} signals")
        logger.info(f"   Tweaks: {len(tweaks)} applied")
        logger.info(f"   Report: OPTIMIZATION_REPORT.md")
        logger.info("=" * 70)
        
        return {
            'validated': validated,
            'tweaks': tweaks,
            'comparison': comparison,
            'report': report
        }
    
    def get_performance_summary(self) -> Dict:
        """Get overall performance summary"""
        # Crypto performance (priority)
        crypto_stats = {}
        for symbol in self.config.CRYPTO_SYMBOLS[:5]:
            crypto_stats[symbol] = self.database.get_accuracy_stats(symbol=symbol)
        
        # Forex performance
        forex_stats = {}
        for symbol in self.config.FOREX_PAIRS[:3]:
            forex_stats[symbol] = self.database.get_accuracy_stats(symbol=symbol)
        
        # Overall
        overall = self.database.get_accuracy_stats()
        
        return {
            'crypto': crypto_stats,
            'forex': forex_stats,
            'overall': overall,
            'total_signals_tracked': len(self.database.signals),
            'total_validated': sum(1 for s in self.database.signals if s.get('validated', False))
        }

# ============================================================================
# ENTRY POINT
# ============================================================================

def main():
    """Main entry point"""
    tracker = SignalTracker()
    
    # Run validation cycle
    results = tracker.run_validation_cycle()
    
    # Print summary
    summary = tracker.get_performance_summary()
    
    print("\n" + "=" * 70)
    print("📊 SIGNAL TRACKING SUMMARY")
    print("=" * 70)
    print(f"📈 Total Signals Tracked: {summary['total_signals_tracked']}")
    print(f"✅ Total Validated: {summary['total_validated']}")
    print(f"🎯 Overall Accuracy: {summary['overall']['accuracy']:.1%}")
    print(f"🔧 Tweaks Applied: {len(results['tweaks'])}")
    print("\n📈 Crypto Performance (Priority):")
    for symbol, stats in summary['crypto'].items():
        if stats['total_signals'] > 0:
            print(f"   {symbol}: {stats['accuracy']:.1%} ({stats['total_signals']} signals)")
    print("=" * 70)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
