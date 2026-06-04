#!/usr/bin/env python3
"""
SELF-OPTIMIZING AUTONOMOUS TRADING BOT
Validates performance and auto-tweaks strategies on the fly

Features:
- Real-time performance validation
- Automatic strategy parameter optimization
- Dynamic position sizing based on win rate
- Strategy rotation based on market conditions
- Self-healing (switches data sources if one fails)
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# SELF-OPTIMIZING CONFIGURATION
# ============================================================================

@dataclass
class Config:
    """Self-optimizing configuration"""
    PRIMARY_EXCHANGE: str = os.getenv('PRIMARY_EXCHANGE', 'FREE_DATA')
    
    # FREE Data Source API Keys
    COINGECKO_API_KEY: str = os.getenv('COINGECKO_API_KEY', '')
    CRYPTOCOMPARE_API_KEY: str = os.getenv('CRYPTOCOMPARE_API_KEY', '')
    
    # Adaptive parameters (auto-tuned)
    INITIAL_CAPITAL: float = float(os.getenv('INITIAL_CAPITAL', '10000'))
    RISK_PER_TRADE: float = float(os.getenv('RISK_PER_TRADE', '0.02'))
    MAX_POSITIONS: int = int(os.getenv('MAX_POSITIONS', '5'))
    
    # Self-optimization settings
    MIN_WIN_RATE_THRESHOLD: float = 0.45  # Below this, reduce position size
    HIGH_WIN_RATE_THRESHOLD: float = 0.65  # Above this, increase position size
    PERFORMANCE_LOOKBACK: int = 20  # Number of trades to evaluate
    
    # Strategy weights (auto-adjusted)
    MOMENTUM_WEIGHT: float = 1.0
    MEAN_REVERSION_WEIGHT: float = 1.0
    ORDER_BOOK_WEIGHT: float = 1.0
    
    CRYPTO_SYMBOLS: List[str] = None
    
    def __post_init__(self):
        if self.CRYPTO_SYMBOLS is None:
            self.CRYPTO_SYMBOLS = ['BTC-USD', 'ETH-USD', 'SOL-USD', 'ADA-USD', 'DOT-USD']

# ============================================================================
# PERFORMANCE VALIDATOR
# ============================================================================

class PerformanceValidator:
    """Validates strategy performance and suggests optimizations"""
    
    def __init__(self, config: Config):
        self.config = config
        self.performance_history = []
        self.load_history()
    
    def load_history(self):
        """Load historical performance"""
        try:
            if os.path.exists('performance_history.json'):
                with open('performance_history.json', 'r') as f:
                    self.performance_history = json.load(f)
                logger.info(f"📊 Loaded {len(self.performance_history)} historical performance records")
        except Exception as e:
            logger.warning(f"Could not load history: {e}")
    
    def save_history(self):
        """Save performance history"""
        try:
            with open('performance_history.json', 'w') as f:
                json.dump(self.performance_history, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Could not save history: {e}")
    
    def validate_performance(self, trade_history: List[Dict]) -> Dict:
        """
        Validate current performance and return optimization suggestions
        """
        if len(trade_history) < 5:
            return {
                'status': 'INSUFFICIENT_DATA',
                'message': 'Need at least 5 trades for validation',
                'recommendations': {}
            }
        
        # Calculate metrics
        recent_trades = trade_history[-self.config.PERFORMANCE_LOOKBACK:]
        wins = sum(1 for t in recent_trades if t['pnl'] > 0)
        total = len(recent_trades)
        win_rate = wins / total if total > 0 else 0
        
        total_pnl = sum(t['pnl'] for t in recent_trades)
        avg_pnl = total_pnl / total if total > 0 else 0
        
        # Calculate by strategy
        strategy_performance = {}
        for trade in recent_trades:
            strategy = trade.get('strategy', 'Unknown')
            if strategy not in strategy_performance:
                strategy_performance[strategy] = {'wins': 0, 'total': 0, 'pnl': 0}
            strategy_performance[strategy]['total'] += 1
            strategy_performance[strategy]['pnl'] += trade['pnl']
            if trade['pnl'] > 0:
                strategy_performance[strategy]['wins'] += 1
        
        # Calculate win rates by strategy
        for strategy, stats in strategy_performance.items():
            stats['win_rate'] = stats['wins'] / stats['total'] if stats['total'] > 0 else 0
        
        # Generate recommendations
        recommendations = {}
        
        # Overall performance check
        if win_rate < self.config.MIN_WIN_RATE_THRESHOLD:
            recommendations['risk_adjustment'] = 'DECREASE'
            recommendations['new_risk'] = self.config.RISK_PER_TRADE * 0.7
            recommendations['message'] = f"Win rate {win_rate:.1%} below threshold. Reducing risk."
        elif win_rate > self.config.HIGH_WIN_RATE_THRESHOLD:
            recommendations['risk_adjustment'] = 'INCREASE'
            recommendations['new_risk'] = min(self.config.RISK_PER_TRADE * 1.2, 0.05)
            recommendations['message'] = f"Win rate {win_rate:.1%} excellent. Increasing risk slightly."
        else:
            recommendations['risk_adjustment'] = 'MAINTAIN'
            recommendations['message'] = f"Win rate {win_rate:.1%} within normal range."
        
        # Strategy-specific adjustments
        for strategy, stats in strategy_performance.items():
            if stats['win_rate'] < 0.4 and stats['total'] >= 5:
                recommendations[f'{strategy}_weight'] = 0.7
                recommendations[f'{strategy}_message'] = f"Reducing {strategy} weight due to poor performance"
            elif stats['win_rate'] > 0.7 and stats['total'] >= 5:
                recommendations[f'{strategy}_weight'] = 1.3
                recommendations[f'{strategy}_message'] = f"Increasing {strategy} weight due to strong performance"
        
        # Record performance
        performance_record = {
            'timestamp': datetime.now().isoformat(),
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'avg_pnl': avg_pnl,
            'trades_evaluated': total,
            'strategy_performance': strategy_performance,
            'recommendations': recommendations
        }
        self.performance_history.append(performance_record)
        self.save_history()
        
        return {
            'status': 'VALIDATED',
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'avg_pnl': avg_pnl,
            'strategy_performance': strategy_performance,
            'recommendations': recommendations
        }

# ============================================================================
# FREE DATA FETCHER WITH FAILOVER
# ============================================================================

class FreeDataFetcher:
    """Fetch market data from FREE sources with automatic failover"""
    
    def __init__(self, config: Config):
        self.config = config
        self.coingecko_key = config.COINGECKO_API_KEY
        self.cryptocompare_key = config.CRYPTOCOMPARE_API_KEY
        
        self.coingecko_url = "https://api.coingecko.com/api/v3"
        self.cryptocompare_url = "https://min-api.cryptocompare.com/data"
        
        self.symbol_to_id = {
            'BTC-USD': 'bitcoin', 'ETH-USD': 'ethereum', 'SOL-USD': 'solana',
            'ADA-USD': 'cardano', 'DOT-USD': 'polkadot', 'XRP-USD': 'ripple',
            'DOGE-USD': 'dogecoin', 'AVAX-USD': 'avalanche-2',
            'MATIC-USD': 'matic-network', 'LINK-USD': 'chainlink'
        }
        
        # Track API health
        self.api_health = {'coingecko': True, 'cryptocompare': True}
    
    def _get_coin_id(self, symbol: str) -> str:
        return self.symbol_to_id.get(symbol, symbol.lower().replace('-', ''))
    
    def get_ticker(self, symbol: str) -> Dict:
        """Get ticker with automatic failover between APIs"""
        
        # Try CoinGecko first if healthy
        if self.api_health['coingecko']:
            try:
                result = self._get_coingecko_ticker(symbol)
                if result:
                    return result
            except Exception as e:
                logger.warning(f"CoinGecko failed, marking unhealthy: {e}")
                self.api_health['coingecko'] = False
        
        # Fallback to CryptoCompare
        if self.api_health['cryptocompare']:
            try:
                result = self._get_cryptocompare_ticker(symbol)
                if result:
                    return result
            except Exception as e:
                logger.warning(f"CryptoCompare failed, marking unhealthy: {e}")
                self.api_health['cryptocompare'] = False
        
        # Try to recover CoinGecko after some time
        if not self.api_health['coingecko']:
            logger.info("Attempting to recover CoinGecko...")
            self.api_health['coingecko'] = True
        
        return None
    
    def _get_coingecko_ticker(self, symbol: str) -> Dict:
        coin_id = self._get_coin_id(symbol)
        url = f"{self.coingecko_url}/coins/markets"
        params = {
            'vs_currency': 'usd',
            'ids': coin_id,
            'order': 'market_cap_desc',
            'sparkline': 'false',
            'price_change_percentage': '24h'
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if data and len(data) > 0:
            coin = data[0]
            return {
                'symbol': symbol,
                'price': float(coin['current_price']),
                'price_change': float(coin.get('price_change_percentage_24h', 0)),
                'volume_24h': float(coin['total_volume']),
                'market_cap': float(coin['market_cap']),
                'high_24h': float(coin.get('high_24h', coin['current_price'])),
                'low_24h': float(coin.get('low_24h', coin['current_price'])),
                'timestamp': datetime.now().isoformat(),
                'source': 'coingecko'
            }
        return None
    
    def _get_cryptocompare_ticker(self, symbol: str) -> Dict:
        symbol_base = symbol.split('-')[0]
        url = f"{self.cryptocompare_url}/price"
        params = {'fsym': symbol_base, 'tsyms': 'USD', 'api_key': self.cryptocompare_key}
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if 'USD' in data:
            price = float(data['USD'])
            
            # Get 24h stats
            histo_url = f"{self.cryptocompare_url}/histoday"
            histo_params = {'fsym': symbol_base, 'tsym': 'USD', 'limit': 1, 'api_key': self.cryptocompare_key}
            histo_response = requests.get(histo_url, params=histo_params, timeout=10)
            histo_data = histo_response.json()
            
            change_pct = 0
            volume = 0
            if histo_data.get('Data') and len(histo_data['Data']) > 1:
                today = histo_data['Data'][-1]
                yesterday = histo_data['Data'][-2]
                change_pct = ((today['close'] - yesterday['close']) / yesterday['close']) * 100
                volume = float(today['volumeto'])
            
            return {
                'symbol': symbol,
                'price': price,
                'price_change': change_pct,
                'volume_24h': volume,
                'timestamp': datetime.now().isoformat(),
                'source': 'cryptocompare'
            }
        return None
    
    def get_klines(self, symbol: str, days: int = 30) -> pd.DataFrame:
        """Get historical data with failover"""
        
        # Try CoinGecko first
        if self.api_health['coingecko']:
            try:
                df = self._get_coingecko_history(symbol, days)
                if not df.empty:
                    return df
            except Exception as e:
                logger.warning(f"CoinGecko history failed: {e}")
        
        # Fallback to CryptoCompare
        try:
            return self._get_cryptocompare_history(symbol, days)
        except Exception as e:
            logger.error(f"Both APIs failed for history: {e}")
        
        return pd.DataFrame()
    
    def _get_coingecko_history(self, symbol: str, days: int) -> pd.DataFrame:
        coin_id = self._get_coin_id(symbol)
        url = f"{self.coingecko_url}/coins/{coin_id}/market_chart"
        params = {'vs_currency': 'usd', 'days': str(days), 'interval': 'daily'}
        
        response = requests.get(url, params=params, timeout=15)
        data = response.json()
        
        if 'prices' in data and len(data['prices']) > 0:
            prices_df = pd.DataFrame(data['prices'], columns=['timestamp', 'close'])
            prices_df['timestamp'] = pd.to_datetime(prices_df['timestamp'], unit='ms')
            
            if 'total_volumes' in data:
                vol_df = pd.DataFrame(data['total_volumes'], columns=['timestamp', 'volume'])
                prices_df = prices_df.merge(vol_df, on='timestamp', how='left')
            
            # Estimate OHLC
            prices_df['open'] = prices_df['close'].shift(1)
            prices_df['high'] = prices_df[['open', 'close']].max(axis=1) * 1.01
            prices_df['low'] = prices_df[['open', 'close']].min(axis=1) * 0.99
            prices_df.loc[0, 'open'] = prices_df.loc[0, 'close']
            prices_df.loc[0, 'high'] = prices_df.loc[0, 'close'] * 1.01
            prices_df.loc[0, 'low'] = prices_df.loc[0, 'close'] * 0.99
            
            return prices_df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].dropna()
        return pd.DataFrame()
    
    def _get_cryptocompare_history(self, symbol: str, days: int) -> pd.DataFrame:
        symbol_base = symbol.split('-')[0]
        url = f"{self.cryptocompare_url}/histoday"
        params = {'fsym': symbol_base, 'tsym': 'USD', 'limit': days, 'api_key': self.cryptocompare_key}
        
        response = requests.get(url, params=params, timeout=15)
        data = response.json()
        
        if data.get('Data'):
            df = pd.DataFrame(data['Data'])
            df['timestamp'] = pd.to_datetime(df['time'], unit='s')
            df = df.rename(columns={'open': 'open', 'high': 'high', 'low': 'low', 'close': 'close', 'volumeto': 'volume'})
            return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        return pd.DataFrame()

# ============================================================================
# ADAPTIVE STRATEGIES
# ============================================================================

class AdaptiveMomentumStrategy:
    """Momentum strategy with adaptive parameters"""
    
    def __init__(self, weight: float = 1.0):
        self.name = "AdaptiveMomentum"
        self.weight = weight
        self.fast_ema = 12
        self.slow_ema = 26
        self.rsi_threshold = 50
    
    def adapt_parameters(self, market_volatility: float):
        """Adapt parameters based on market conditions"""
        if market_volatility > 0.05:  # High volatility
            self.fast_ema = 8
            self.slow_ema = 21
            logger.info("High volatility detected - using faster EMAs")
        else:  # Low volatility
            self.fast_ema = 12
            self.slow_ema = 26
    
    def generate_signal(self, df: pd.DataFrame) -> Optional[Dict]:
        if df.empty or len(df) < 30:
            return None
        
        prices = df['close']
        
        # Calculate volatility for adaptation
        volatility = prices.pct_change().std()
        self.adapt_parameters(volatility)
        
        # Calculate EMAs with adaptive periods
        ema_fast = prices.ewm(span=self.fast_ema, adjust=False).mean()
        ema_slow = prices.ewm(span=self.slow_ema, adjust=False).mean()
        
        # RSI
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[-1]
        
        curr_fast = ema_fast.iloc[-1]
        curr_slow = ema_slow.iloc[-1]
        prev_fast = ema_fast.iloc[-2]
        prev_slow = ema_slow.iloc[-2]
        
        # Bullish crossover
        if prev_fast <= prev_slow and curr_fast > curr_slow and current_rsi > self.rsi_threshold:
            return {
                'signal': 'LONG',
                'strength': abs(curr_fast - curr_slow) / curr_slow * self.weight,
                'reason': f'EMA {self.fast_ema}/{self.slow_ema} bullish crossover, RSI {current_rsi:.1f}',
                'strategy': self.name
            }
        
        # Bearish crossover
        if prev_fast >= prev_slow and curr_fast < curr_slow and current_rsi < (100 - self.rsi_threshold):
            return {
                'signal': 'SHORT',
                'strength': abs(curr_fast - curr_slow) / curr_slow * self.weight,
                'reason': f'EMA {self.fast_ema}/{self.slow_ema} bearish crossover, RSI {current_rsi:.1f}',
                'strategy': self.name
            }
        
        return None

class AdaptiveMeanReversion:
    """Mean reversion with adaptive Bollinger Bands"""
    
    def __init__(self, weight: float = 1.0):
        self.name = "AdaptiveMeanReversion"
        self.weight = weight
        self.std_dev = 2.0
    
    def adapt_parameters(self, market_volatility: float):
        """Widen bands in high volatility, tighten in low"""
        if market_volatility > 0.05:
            self.std_dev = 2.5
        elif market_volatility < 0.02:
            self.std_dev = 1.5
        else:
            self.std_dev = 2.0
    
    def generate_signal(self, df: pd.DataFrame) -> Optional[Dict]:
        if df.empty or len(df) < 20:
            return None
        
        prices = df['close']
        
        # Calculate volatility and adapt
        volatility = prices.pct_change().std()
        self.adapt_parameters(volatility)
        
        # Bollinger Bands
        middle = prices.rolling(window=20).mean().iloc[-1]
        std = prices.rolling(window=20).std().iloc[-1]
        upper = middle + (std * self.std_dev)
        lower = middle - (std * self.std_dev)
        current_price = prices.iloc[-1]
        
        # RSI
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[-1]
        
        # Overbought
        if current_price > upper and current_rsi > 70:
            return {
                'signal': 'SHORT',
                'strength': (current_price - upper) / upper * self.weight,
                'reason': f'Price above {self.std_dev}σ BB, RSI {current_rsi:.1f}',
                'strategy': self.name
            }
        
        # Oversold
        if current_price < lower and current_rsi < 30:
            return {
                'signal': 'LONG',
                'strength': (lower - current_price) / lower * self.weight,
                'reason': f'Price below {self.std_dev}σ BB, RSI {current_rsi:.1f}',
                'strategy': self.name
            }
        
        return None

# ============================================================================
# ADAPTIVE PORTFOLIO MANAGER
# ============================================================================

class AdaptivePortfolioManager:
    """Portfolio manager with truly adaptive risk adjustment based on real performance metrics."""

    # Optimization constants
    POSITION_SIZE_FLOOR = 0.005   # Never risk less than 0.5% per trade
    POSITION_SIZE_CAP   = 0.04    # Never risk more than 4% per trade
    DRAWDOWN_HALT_PCT   = 0.15    # Halt new positions if drawdown > 15%
    DEFENSIVE_SHARPE    = 0.5     # Switch to defensive mode below this Sharpe
    DEFENSIVE_CONFIDENCE_MIN = 75 # Only high-confidence signals in defensive mode

    def __init__(self, config: Config, validator: PerformanceValidator):
        self.config = config
        self.validator = validator
        self.positions = {}
        self.cash = config.INITIAL_CAPITAL
        self.equity = config.INITIAL_CAPITAL
        self.trade_history = []
        self.current_risk = config.RISK_PER_TRADE
        self.peak_equity = config.INITIAL_CAPITAL
        self.halted = False          # True when drawdown > 15%
        self.defensive_mode = False  # True when Sharpe < 0.5
        self.equity_curve = [config.INITIAL_CAPITAL]

    def _compute_win_rate(self, trades: list) -> float:
        """Compute win rate from a list of trade dicts."""
        if not trades:
            return 0.0
        wins = sum(1 for t in trades if (t.get('pnl') or 0) > 0)
        return wins / len(trades)

    def _compute_sharpe(self, trades: list, annualize_factor: float = 252) -> float:
        """Compute Sharpe ratio from trade P&L percentages (annualized)."""
        if len(trades) < 5:
            return 0.0
        pnl_pcts = [t.get('pnl_pct', 0) for t in trades]
        mean_pnl = np.mean(pnl_pcts)
        std_pnl = np.std(pnl_pcts)
        if std_pnl == 0:
            return 0.0
        return float((mean_pnl / std_pnl) * np.sqrt(min(annualize_factor, len(trades))))

    def _compute_max_drawdown(self) -> float:
        """Compute current drawdown from peak equity."""
        if self.peak_equity <= 0:
            return 0.0
        return (self.peak_equity - self.equity) / self.peak_equity

    def adjust_risk_based_on_performance(self):
        """
        Truly adaptive risk management based on real performance metrics:
          a. Track last N trades and compute win rate
          b. If win_rate < 45% over last 20: reduce position size by 30%
          c. If win_rate > 60% over last 20: increase position size by 20% (capped)
          d. If max drawdown > 15%: halt new positions until recovery
          e. If Sharpe < 0.5 over recent trades: switch to defensive mode
        """
        # Update peak equity for drawdown tracking
        if self.equity > self.peak_equity:
            self.peak_equity = self.equity

        # (d) Check drawdown halt
        current_drawdown = self._compute_max_drawdown()
        if current_drawdown > self.DRAWDOWN_HALT_PCT:
            if not self.halted:
                logger.warning(
                    f"HALT: Drawdown {current_drawdown:.1%} exceeds {self.DRAWDOWN_HALT_PCT:.0%}. "
                    f"No new positions until equity recovers above ${self.peak_equity * 0.90:,.2f}"
                )
                self.halted = True
        elif self.halted:
            # Resume if drawdown recovers to < 10%
            if current_drawdown < 0.10:
                logger.info(
                    f"RESUME: Drawdown recovered to {current_drawdown:.1%}. "
                    f"Resuming trading with reduced risk."
                )
                self.halted = False
                # Come back with reduced risk after halt
                self.current_risk = max(self.POSITION_SIZE_FLOOR,
                                        self.config.RISK_PER_TRADE * 0.7)

        # Need enough trades for meaningful analysis
        recent_20 = self.trade_history[-20:] if len(self.trade_history) >= 5 else []
        recent_30 = self.trade_history[-30:] if len(self.trade_history) >= 10 else []

        if not recent_20:
            logger.info(f"Insufficient trades ({len(self.trade_history)}) for risk adjustment")
            return

        win_rate = self._compute_win_rate(recent_20)
        sharpe = self._compute_sharpe(recent_30) if recent_30 else 0.0

        # (e) Defensive mode check (Sharpe-based)
        if sharpe < self.DEFENSIVE_SHARPE and len(recent_30) >= 10:
            if not self.defensive_mode:
                logger.warning(
                    f"DEFENSIVE MODE: Sharpe {sharpe:.2f} < {self.DEFENSIVE_SHARPE}. "
                    f"Only accepting high-confidence signals (>={self.DEFENSIVE_CONFIDENCE_MIN}%)."
                )
                self.defensive_mode = True
        elif sharpe >= self.DEFENSIVE_SHARPE * 1.5:
            if self.defensive_mode:
                logger.info(f"Normal mode restored: Sharpe {sharpe:.2f}")
                self.defensive_mode = False

        # (b) Win rate < 45% -> reduce by 30%
        if win_rate < self.config.MIN_WIN_RATE_THRESHOLD:
            new_risk = max(self.POSITION_SIZE_FLOOR, self.current_risk * 0.70)
            logger.warning(
                f"Reducing risk: win rate {win_rate:.1%} < {self.config.MIN_WIN_RATE_THRESHOLD:.0%} "
                f"over last {len(recent_20)} trades. "
                f"Risk {self.current_risk:.2%} -> {new_risk:.2%}"
            )
            self.current_risk = new_risk

        # (c) Win rate > 60% -> increase by 20% (capped)
        elif win_rate > self.config.HIGH_WIN_RATE_THRESHOLD:
            new_risk = min(self.POSITION_SIZE_CAP, self.current_risk * 1.20)
            logger.info(
                f"Increasing risk: win rate {win_rate:.1%} > {self.config.HIGH_WIN_RATE_THRESHOLD:.0%} "
                f"over last {len(recent_20)} trades. "
                f"Risk {self.current_risk:.2%} -> {new_risk:.2%}"
            )
            self.current_risk = new_risk
        else:
            logger.info(
                f"Risk maintained at {self.current_risk:.2%} "
                f"(WR: {win_rate:.1%}, Sharpe: {sharpe:.2f}, DD: {current_drawdown:.1%})"
            )

        # Run full validation for strategy-level insights
        self.validator.validate_performance(self.trade_history)
    
    def calculate_position_size(self, signal: Dict, current_price: float) -> float:
        """Calculate position size with dynamic risk"""
        risk_amount = self.equity * self.current_risk
        stop_loss_pct = 0.02
        position_size = risk_amount / (current_price * stop_loss_pct)
        
        max_position_value = self.equity / self.config.MAX_POSITIONS
        max_size = max_position_value / current_price
        
        return min(position_size, max_size)
    
    def can_open_position(self, symbol: str, signal: Optional[Dict] = None) -> bool:
        """Check whether a new position is allowed given current risk state."""
        if len(self.positions) >= self.config.MAX_POSITIONS:
            return False
        if symbol in self.positions:
            return False
        # Drawdown halt: no new positions until recovery
        if self.halted:
            logger.info(f"Position blocked for {symbol}: trading halted (drawdown > {self.DRAWDOWN_HALT_PCT:.0%})")
            return False
        # Defensive mode: only high-confidence signals
        if self.defensive_mode and signal:
            confidence = signal.get('confidence', signal.get('strength', 0))
            # Normalize: if strength is 0-1 range, convert to percentage
            if isinstance(confidence, (int, float)) and confidence <= 1.0:
                confidence = confidence * 100
            if confidence < self.DEFENSIVE_CONFIDENCE_MIN:
                logger.info(
                    f"Position blocked for {symbol}: defensive mode "
                    f"(confidence {confidence:.0f}% < {self.DEFENSIVE_CONFIDENCE_MIN}%)"
                )
                return False
        return True

    def open_position(self, signal: Dict, price: float, timestamp: str, symbol: str):
        """Open a new position"""
        direction = signal['signal']
        size = self.calculate_position_size(signal, price)
        
        cost = size * price
        if cost > self.cash:
            logger.warning(f"Insufficient cash for {symbol}")
            return False
        
        self.positions[symbol] = {
            'symbol': symbol,
            'direction': direction,
            'entry_price': price,
            'size': size,
            'entry_time': timestamp,
            'strategy': signal['strategy'],
            'stop_loss': price * 0.98 if direction == 'LONG' else price * 1.02,
            'take_profit': price * 1.06 if direction == 'LONG' else price * 0.94
        }
        
        self.cash -= cost
        logger.info(f"OPENED {direction} {symbol}: {size:.6f} @ ${price:.2f}")
        return True
    
    def check_exits(self, current_prices: Dict) -> List[Dict]:
        """Check if any positions should be closed"""
        closed = []
        
        for symbol, pos in list(self.positions.items()):
            if symbol not in current_prices:
                continue
            
            current_price = current_prices[symbol]
            direction = pos['direction']
            
            # Check stop loss
            if direction == 'LONG' and current_price <= pos['stop_loss']:
                self.close_position(symbol, current_price, 'STOP_LOSS')
                closed.append({'symbol': symbol, 'reason': 'STOP_LOSS'})
            elif direction == 'SHORT' and current_price >= pos['stop_loss']:
                self.close_position(symbol, current_price, 'STOP_LOSS')
                closed.append({'symbol': symbol, 'reason': 'STOP_LOSS'})
            
            # Check take profit
            elif direction == 'LONG' and current_price >= pos['take_profit']:
                self.close_position(symbol, current_price, 'TAKE_PROFIT')
                closed.append({'symbol': symbol, 'reason': 'TAKE_PROFIT'})
            elif direction == 'SHORT' and current_price <= pos['take_profit']:
                self.close_position(symbol, current_price, 'TAKE_PROFIT')
                closed.append({'symbol': symbol, 'reason': 'TAKE_PROFIT'})
        
        return closed
    
    def close_position(self, symbol: str, exit_price: float, reason: str):
        """Close a position"""
        if symbol not in self.positions:
            return
        
        pos = self.positions.pop(symbol)
        
        if pos['direction'] == 'LONG':
            pnl = (exit_price - pos['entry_price']) * pos['size']
        else:
            pnl = (pos['entry_price'] - exit_price) * pos['size']
        
        self.cash += (pos['size'] * exit_price)
        
        trade_record = {
            'symbol': symbol,
            'direction': pos['direction'],
            'entry_price': pos['entry_price'],
            'exit_price': exit_price,
            'size': pos['size'],
            'pnl': pnl,
            'pnl_pct': (pnl / (pos['entry_price'] * pos['size'])) * 100,
            'entry_time': pos['entry_time'],
            'exit_time': datetime.now().isoformat(),
            'strategy': pos['strategy'],
            'exit_reason': reason
        }
        
        self.trade_history.append(trade_record)
        logger.info(f"CLOSED {symbol}: ${pnl:+.2f} ({reason})")
    
    def update_equity(self, current_prices: Dict):
        """Update portfolio equity and track equity curve for drawdown calculations."""
        position_value = 0
        for symbol, pos in self.positions.items():
            if symbol in current_prices:
                position_value += pos['size'] * current_prices[symbol]

        self.equity = self.cash + position_value
        self.equity_curve.append(self.equity)

        # Update peak for drawdown calculation
        if self.equity > self.peak_equity:
            self.peak_equity = self.equity
    
    def get_stats(self) -> Dict:
        """Get portfolio statistics including adaptive optimization metrics."""
        base = {
            'total_trades': 0,
            'win_rate': 0,
            'total_pnl': 0,
            'avg_trade': 0,
            'current_risk': self.current_risk,
            'current_equity': self.equity,
            'return_pct': ((self.equity - self.config.INITIAL_CAPITAL) / self.config.INITIAL_CAPITAL) * 100,
            'max_drawdown_pct': self._compute_max_drawdown() * 100,
            'halted': self.halted,
            'defensive_mode': self.defensive_mode,
            'peak_equity': self.peak_equity,
        }

        if not self.trade_history:
            return base

        wins = sum(1 for t in self.trade_history if t['pnl'] > 0)
        total_pnl = sum(t['pnl'] for t in self.trade_history)
        sharpe = self._compute_sharpe(self.trade_history[-30:]) if len(self.trade_history) >= 5 else 0.0

        base.update({
            'total_trades': len(self.trade_history),
            'winning_trades': wins,
            'losing_trades': len(self.trade_history) - wins,
            'win_rate': (wins / len(self.trade_history)) * 100,
            'total_pnl': total_pnl,
            'avg_trade': total_pnl / len(self.trade_history),
            'sharpe_ratio': round(sharpe, 2),
        })

        return base

# ============================================================================
# MAIN SELF-OPTIMIZING BOT
# ============================================================================

class SelfOptimizingBot:
    """Main bot with self-validation and auto-tweaking"""
    
    def __init__(self, config: Config):
        self.config = config
        self.data_fetcher = FreeDataFetcher(config)
        self.validator = PerformanceValidator(config)
        self.portfolio = AdaptivePortfolioManager(config, self.validator)
        
        # Initialize adaptive strategies
        self.strategies = [
            AdaptiveMomentumStrategy(weight=config.MOMENTUM_WEIGHT),
            AdaptiveMeanReversion(weight=config.MEAN_REVERSION_WEIGHT)
        ]
    
    def run_cycle(self):
        """Run one self-optimizing trading cycle"""
        logger.info("=" * 70)
        logger.info(f"🤖 SELF-OPTIMIZING BOT - {datetime.now().isoformat()}")
        logger.info("=" * 70)
        
        # Adjust risk based on performance BEFORE trading
        self.portfolio.adjust_risk_based_on_performance()
        
        signals_generated = []
        
        for symbol in self.config.CRYPTO_SYMBOLS:
            logger.info(f"\n--- Analyzing {symbol} ---")
            
            # Fetch data with failover
            ticker_data = self.data_fetcher.get_ticker(symbol)
            klines_df = self.data_fetcher.get_klines(symbol, days=30)
            
            if klines_df.empty:
                logger.warning(f"No data for {symbol}, skipping...")
                continue
            
            # Generate signals from adaptive strategies
            for strategy in self.strategies:
                signal = strategy.generate_signal(klines_df)
                
                if signal:
                    signal['symbol'] = symbol
                    signals_generated.append(signal)
                    logger.info(f"📊 SIGNAL: {signal['signal']} {symbol} - {signal['reason']}")
        
        # Get current prices
        current_prices = {}
        for symbol in self.config.CRYPTO_SYMBOLS:
            ticker = self.data_fetcher.get_ticker(symbol)
            if ticker:
                current_prices[symbol] = ticker['price']
        
        # Check exits first
        exits = self.portfolio.check_exits(current_prices)
        
        # Then check entries
        for signal in signals_generated:
            symbol = signal['symbol']
            if symbol in current_prices and self.portfolio.can_open_position(symbol, signal):
                self.portfolio.open_position(signal, current_prices[symbol], datetime.now().isoformat(), symbol)
        
        # Update equity
        self.portfolio.update_equity(current_prices)
        
        # Log stats
        stats = self.portfolio.get_stats()
        logger.info("\n" + "=" * 70)
        logger.info("📊 PORTFOLIO STATS")
        logger.info("=" * 70)
        logger.info(f"💰 Equity: ${self.portfolio.equity:,.2f}")
        logger.info(f"💵 Cash: ${self.portfolio.cash:,.2f}")
        logger.info(f"📈 Open Positions: {len(self.portfolio.positions)}")
        logger.info(f"🔄 Total Trades: {stats['total_trades']}")
        logger.info(f"🎯 Win Rate: {stats['win_rate']:.1f}%")
        logger.info(f"📉 Current Risk: {stats['current_risk']:.1%}")
        logger.info(f"💵 Total P&L: ${stats['total_pnl']:+.2f}")
        logger.info(f"📊 Return: {stats['return_pct']:+.2f}%")
        
        # Validate and log recommendations
        validation = self.validator.validate_performance(self.portfolio.trade_history)
        if validation['status'] == 'VALIDATED':
            logger.info("\n🎛️ OPTIMIZATION RECOMMENDATIONS:")
            for key, value in validation.get('recommendations', {}).items():
                if 'message' in key:
                    logger.info(f"   • {value}")
        
        return stats
    
    def run(self):
        """Main loop"""
        logger.info("\n" + "=" * 70)
        logger.info("🚀 SELF-OPTIMIZING TRADING BOT - STARTING")
        logger.info("=" * 70)
        logger.info(f"💰 Initial Capital: ${self.config.INITIAL_CAPITAL:,.2f}")
        logger.info(f"📊 Max Positions: {self.config.MAX_POSITIONS}")
        logger.info(f"📉 Base Risk: {self.config.RISK_PER_TRADE:.1%}")
        logger.info(f"🎛️ Adaptive Risk: ENABLED")
        logger.info(f"🔄 Strategies: {[s.name for s in self.strategies]}")
        logger.info(f"📈 Symbols: {self.config.CRYPTO_SYMBOLS}")
        logger.info("=" * 70)
        
        stats = self.run_cycle()
        self.save_results()
        
        return stats
    
    def save_results(self):
        """Save comprehensive results"""
        validation = self.validator.validate_performance(self.portfolio.trade_history)
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'config': {
                'initial_capital': self.config.INITIAL_CAPITAL,
                'current_risk': self.portfolio.current_risk,
                'max_positions': self.config.MAX_POSITIONS
            },
            'portfolio': {
                'cash': self.portfolio.cash,
                'equity': self.portfolio.equity,
                'positions': self.portfolio.positions,
                'return_pct': ((self.portfolio.equity - self.config.INITIAL_CAPITAL) / self.config.INITIAL_CAPITAL) * 100
            },
            'performance': validation if validation['status'] == 'VALIDATED' else {},
            'trade_history': self.portfolio.trade_history,
            'stats': self.portfolio.get_stats()
        }
        
        with open('trading_results.json', 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info("\n💾 Results saved to trading_results.json")

# ============================================================================
# ENTRY POINT
# ============================================================================

def main():
    """Main entry point"""
    config = Config()
    
    bot = SelfOptimizingBot(config)
    stats = bot.run()
    
    print("\n" + "=" * 70)
    print("🤖 SELF-OPTIMIZING BOT COMPLETE")
    print("=" * 70)
    print(f"💰 Final Equity: ${bot.portfolio.equity:,.2f}")
    print(f"📊 Total Return: {stats['return_pct']:+.2f}%")
    print(f"🔄 Total Trades: {stats['total_trades']}")
    print(f"🎯 Win Rate: {stats['win_rate']:.1f}%")
    print(f"📉 Current Risk Level: {stats['current_risk']:.1%}")
    print("=" * 70)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
