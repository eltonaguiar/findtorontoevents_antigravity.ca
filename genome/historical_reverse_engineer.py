#!/usr/bin/env python3
"""
Historical Reverse Engineer - Multi-Timeframe Analysis
======================================================

Comprehensive analysis of what would've worked across multiple time periods:
- Today (last 24h)
- Yesterday (24-48h ago)
- Last week (7 days)
- Last month (30 days)

For each period, calculates:
- Win rate and profit factor
- Average holding period
- Sharpe ratio (risk-adjusted returns)
- Max drawdown and recovery
- Optimal entry/exit timing
- Pattern consistency across time

Usage:
    python historical_reverse_engineer.py --today       # Analyze today
    python historical_reverse_engineer.py --yesterday   # Analyze yesterday
    python historical_reverse_engineer.py --week        # Analyze last week
    python historical_reverse_engineer.py --all         # Analyze all periods
    python historical_reverse_engineer.py --compare     # Compare patterns across time
"""

import json
import requests
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field, asdict
from pathlib import Path
import logging
from collections import defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('HistoricalReverseEngineer')


# Top 30 liquid crypto pairs
SYMBOLS = [
    'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'ADAUSDT', 'DOTUSDT',
    'LINKUSDT', 'MATICUSDT', 'AVAXUSDT', 'UNIUSDT', 'ATOMUSDT',
    'LTCUSDT', 'BCHUSDT', 'ALGOUSDT', 'VETUSDT', 'FILUSDT',
    'TRXUSDT', 'ETCUSDT', 'XLMUSDT', 'NEARUSDT', 'ARBUSDT',
    'OPUSDT', 'APTUSDT', 'GRTUSDT', 'STXUSDT', 'IMXUSDT',
    'RUNEUSDT', 'INJUSDT', 'RENDERUSDT', 'TIAUSDT', 'SEIUSDT'
]


@dataclass
class HistoricalTrade:
    """A completed trade with full metrics."""
    symbol: str
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    direction: str
    pnl_pct: float
    pnl_usd: float
    
    # Risk metrics
    max_profit_pct: float  # Max unrealized profit
    max_drawdown_pct: float  # Max unrealized loss
    
    # Time metrics
    duration_minutes: int
    bars_held: int
    
    # Entry/exit quality
    entry_quality: float  # 0-1, how close to optimal entry
    exit_quality: float  # 0-1, how close to optimal exit
    
    # Market conditions at entry
    market_regime: str  # trending_up, trending_down, ranging, volatile
    volume_profile: str  # high, normal, low
    volatility_regime: str  # high, normal, low
    
    # DNA signature that caught this
    dna_signature: Dict = field(default_factory=dict)


@dataclass
class PatternPerformance:
    """Performance metrics for a pattern over a time period."""
    pattern_name: str
    dna_genes: Dict
    period: str  # today, yesterday, week, month
    
    # Core metrics
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    
    # PnL metrics
    total_pnl_pct: float
    avg_trade_pct: float
    avg_winner_pct: float
    avg_loser_pct: float
    profit_factor: float
    expectancy: float
    
    # Risk metrics
    max_drawdown_pct: float
    max_consecutive_losses: int
    recovery_factor: float
    
    # Time metrics
    avg_holding_minutes: float
    median_holding_minutes: float
    shortest_trade_minutes: int
    longest_trade_minutes: int
    
    # Sharpe/Sortino
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    
    # Consistency
    daily_pnl_std: float
    consistency_score: float  # 0-1, low variance = high score
    
    # Symbol performance
    symbol_stats: Dict[str, Dict] = field(default_factory=dict)
    
    # Time-based performance
    hourly_performance: Dict[int, float] = field(default_factory=dict)  # Hour of day
    daily_performance: Dict[str, float] = field(default_factory=dict)  # Day of week


class DataFetcher:
    """Fetch historical price data."""
    
    def __init__(self):
        self.cache = {}
    
    _SPOT_BASES = [
        "https://api.binance.com", "https://api1.binance.com",
        "https://data-api.binance.vision", "https://api.binance.us",
    ]

    def fetch_range(self, symbol: str, start_time: datetime, end_time: datetime,
                    timeframe: str = '15m') -> List[Dict]:
        """Fetch data for a specific time range (with endpoint failover)."""
        # Convert to milliseconds
        start_ms = int(start_time.timestamp() * 1000)
        end_ms = int(end_time.timestamp() * 1000)

        for _base in self._SPOT_BASES:
            try:
                url = f"{_base}/api/v3/klines"
                params = {
                    'symbol': symbol,
                    'interval': timeframe,
                    'startTime': start_ms,
                    'endTime': end_ms,
                    'limit': 1000
                }
                response = requests.get(url, params=params, timeout=15)
                if response.status_code in (451, 403):
                    continue
                if response.status_code == 200:
                    klines = response.json()
                    return [{
                        'timestamp': int(k[0]),
                        'open': float(k[1]),
                        'high': float(k[2]),
                        'low': float(k[3]),
                        'close': float(k[4]),
                        'volume': float(k[5])
                    } for k in klines]
            except Exception as e:
                logger.warning(f"Failed to fetch {symbol} from {_base}: {e}")

        return []
    
    def fetch_period(self, period: str) -> Dict[str, List]:
        """Fetch data for a named period."""
        now = datetime.utcnow()
        
        if period == 'today':
            start = now - timedelta(hours=24)
        elif period == 'yesterday':
            start = now - timedelta(hours=48)
            now = now - timedelta(hours=24)
        elif period == 'week':
            start = now - timedelta(days=7)
        elif period == 'month':
            start = now - timedelta(days=30)
        else:
            start = now - timedelta(hours=24)
        
        data = {}
        logger.info(f"Fetching {period} data ({start} to {now})...")
        
        for symbol in SYMBOLS:
            symbol_data = self.fetch_range(symbol, start, now, '15m')
            if len(symbol_data) > 50:
                data[symbol] = symbol_data
            
        logger.info(f"Loaded {len(data)} symbols for {period}")
        return data


class TechnicalAnalyzer:
    """Calculate technical indicators."""
    
    @staticmethod
    def calculate_all(ohlcv: List[Dict]) -> Dict:
        """Calculate comprehensive indicators."""
        if len(ohlcv) < 50:
            return {}
        
        df = pd.DataFrame(ohlcv)
        
        indicators = {}
        
        # Price data
        closes = df['close'].values
        highs = df['high'].values
        lows = df['low'].values
        volumes = df['volume'].values
        
        # Moving averages
        for period in [9, 12, 20, 26, 50, 200]:
            if len(closes) >= period:
                indicators[f'ema_{period}'] = TechnicalAnalyzer._ema(closes, period)
                indicators[f'sma_{period}'] = TechnicalAnalyzer._sma(closes, period)
        
        # RSI variants
        indicators['rsi_14'] = TechnicalAnalyzer._rsi(closes, 14)
        indicators['rsi_6'] = TechnicalAnalyzer._rsi(closes, 6)
        
        # MACD
        indicators['macd'], indicators['macd_signal'], indicators['macd_hist'] = \
            TechnicalAnalyzer._macd(closes)
        
        # Bollinger Bands
        indicators['bb_upper'], indicators['bb_middle'], indicators['bb_lower'], \
            indicators['bb_width'] = TechnicalAnalyzer._bollinger(closes)
        
        # ATR and volatility
        indicators['atr_14'] = TechnicalAnalyzer._atr(highs, lows, closes, 14)
        indicators['atr_7'] = TechnicalAnalyzer._atr(highs, lows, closes, 7)
        
        # Volatility regime
        indicators['volatility'] = TechnicalAnalyzer._volatility(closes, 20)
        
        # Volume analysis
        indicators['volume_sma_20'] = TechnicalAnalyzer._sma(volumes, 20)
        indicators['volume_ratio'] = volumes / indicators['volume_sma_20']
        
        # VWAP
        indicators['vwap'] = TechnicalAnalyzer._vwap(ohlcv)
        
        # Support/Resistance
        indicators['pivot_highs'], indicators['pivot_lows'] = \
            TechnicalAnalyzer._find_pivots(highs, lows)
        
        # Trend detection
        indicators['adx'] = TechnicalAnalyzer._adx(highs, lows, closes, 14)
        indicators['trend_direction'] = TechnicalAnalyzer._trend_direction(indicators)
        
        # Market regime
        indicators['regime'] = TechnicalAnalyzer._classify_regime(indicators)
        
        return indicators
    
    @staticmethod
    def _ema(data: np.ndarray, period: int) -> np.ndarray:
        """Exponential moving average."""
        multiplier = 2 / (period + 1)
        ema = np.zeros_like(data)
        ema[0] = data[0]
        for i in range(1, len(data)):
            ema[i] = (data[i] - ema[i-1]) * multiplier + ema[i-1]
        return ema
    
    @staticmethod
    def _sma(data: np.ndarray, period: int) -> np.ndarray:
        """Simple moving average."""
        sma = np.convolve(data, np.ones(period)/period, mode='valid')
        return np.concatenate([np.full(period-1, np.nan), sma])
    
    @staticmethod
    def _rsi(data: np.ndarray, period: int = 14) -> np.ndarray:
        """Relative Strength Index."""
        deltas = np.diff(data)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gains = np.convolve(gains, np.ones(period)/period, mode='valid')
        avg_losses = np.convolve(losses, np.ones(period)/period, mode='valid')
        
        rs = avg_gains / (avg_losses + 1e-10)
        rsi = 100 - (100 / (1 + rs))
        
        return np.concatenate([np.full(period, 50), rsi])
    
    @staticmethod
    def _macd(data: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9):
        """MACD indicator."""
        ema_fast = TechnicalAnalyzer._ema(data, fast)
        ema_slow = TechnicalAnalyzer._ema(data, slow)
        macd = ema_fast - ema_slow
        macd_signal = TechnicalAnalyzer._ema(macd, signal)
        macd_hist = macd - macd_signal
        return macd, macd_signal, macd_hist
    
    @staticmethod
    def _bollinger(data: np.ndarray, period: int = 20, std_dev: float = 2):
        """Bollinger Bands."""
        middle = TechnicalAnalyzer._sma(data, period)
        std = pd.Series(data).rolling(period).std().values
        upper = middle + std_dev * std
        lower = middle - std_dev * std
        width = (upper - lower) / middle
        return upper, middle, lower, width
    
    @staticmethod
    def _atr(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> np.ndarray:
        """Average True Range."""
        tr1 = highs - lows
        tr2 = np.abs(highs[1:] - closes[:-1])
        tr3 = np.abs(lows[1:] - closes[:-1])
        
        tr = np.zeros_like(highs)
        tr[0] = tr1[0]
        tr[1:] = np.maximum(np.maximum(tr1[1:], tr2), tr3)
        
        return TechnicalAnalyzer._ema(tr, period)
    
    @staticmethod
    def _volatility(data: np.ndarray, period: int = 20) -> np.ndarray:
        """Rolling volatility (annualized)."""
        returns = np.diff(data) / data[:-1]
        vol = pd.Series(returns).rolling(period).std().values * np.sqrt(365 * 24 * 4)  # 15m bars
        return np.concatenate([[0], vol])
    
    @staticmethod
    def _vwap(ohlcv: List[Dict]) -> np.ndarray:
        """Volume Weighted Average Price."""
        typical_prices = [(c['high'] + c['low'] + c['close']) / 3 for c in ohlcv]
        volumes = [c['volume'] for c in ohlcv]
        
        cum_vol = np.cumsum(volumes)
        cum_pv = np.cumsum([tp * vol for tp, vol in zip(typical_prices, volumes)])
        
        return cum_pv / (cum_vol + 1e-10)
    
    @staticmethod
    def _find_pivots(highs: np.ndarray, lows: np.ndarray, window: int = 5):
        """Find pivot highs and lows."""
        pivot_highs = np.zeros_like(highs)
        pivot_lows = np.zeros_like(lows)
        
        for i in range(window, len(highs) - window):
            if all(highs[i] > highs[i-j] for j in range(1, window+1)) and \
               all(highs[i] > highs[i+j] for j in range(1, window+1)):
                pivot_highs[i] = highs[i]
            
            if all(lows[i] < lows[i-j] for j in range(1, window+1)) and \
               all(lows[i] < lows[i+j] for j in range(1, window+1)):
                pivot_lows[i] = lows[i]
        
        return pivot_highs, pivot_lows
    
    @staticmethod
    def _adx(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> np.ndarray:
        """Average Directional Index."""
        plus_dm = np.zeros_like(highs)
        minus_dm = np.zeros_like(lows)
        
        for i in range(1, len(highs)):
            plus_dm[i] = max(highs[i] - highs[i-1], 0) if highs[i] - highs[i-1] > lows[i-1] - lows[i] else 0
            minus_dm[i] = max(lows[i-1] - lows[i], 0) if lows[i-1] - lows[i] > highs[i] - highs[i-1] else 0
        
        tr = np.zeros_like(highs)
        tr[0] = highs[0] - lows[0]
        for i in range(1, len(highs)):
            tr[i] = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
        
        atr = TechnicalAnalyzer._ema(tr, period)
        plus_di = 100 * TechnicalAnalyzer._ema(plus_dm, period) / (atr + 1e-10)
        minus_di = 100 * TechnicalAnalyzer._ema(minus_dm, period) / (atr + 1e-10)
        
        dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)
        adx = TechnicalAnalyzer._ema(dx, period)
        
        return adx
    
    @staticmethod
    def _trend_direction(indicators: Dict) -> np.ndarray:
        """Determine trend direction."""
        ema_12 = indicators.get('ema_9', indicators.get('ema_12'))
        ema_26 = indicators.get('ema_20', indicators.get('ema_26'))
        
        if ema_12 is not None and ema_26 is not None:
            return np.where(ema_12 > ema_26, 1, -1)
        return np.zeros(len(indicators.get('rsi_14', [])))
    
    @staticmethod
    def _classify_regime(indicators: Dict) -> np.ndarray:
        """Classify market regime."""
        volatility = indicators.get('volatility', np.zeros(100))
        adx = indicators.get('adx', np.zeros(100))
        trend = indicators.get('trend_direction', np.zeros(100))
        
        regimes = np.full(len(volatility), 'unknown', dtype=object)
        
        for i in range(len(volatility)):
            if volatility[i] > 0.8:
                regimes[i] = 'volatile'
            elif adx[i] > 30:
                regimes[i] = 'trending_up' if trend[i] > 0 else 'trending_down'
            elif adx[i] < 20:
                regimes[i] = 'ranging'
            else:
                regimes[i] = 'transition'
        
        return regimes


class TradeSimulator:
    """Simulate trades and calculate metrics."""
    
    def __init__(self, ohlcv: List[Dict], indicators: Dict):
        self.ohlcv = ohlcv
        self.indicators = indicators
        self.df = pd.DataFrame(ohlcv)
    
    def find_optimal_trades(self, min_risk_reward: float = 1.5, 
                           max_holding_bars: int = 20) -> List[HistoricalTrade]:
        """Find all trades that would've been profitable."""
        trades = []
        
        if len(self.ohlcv) < 50 or not self.indicators:
            return trades
        
        closes = self.df['close'].values
        highs = self.df['high'].values
        lows = self.df['low'].values
        timestamps = [datetime.fromtimestamp(c['timestamp'] / 1000) for c in self.ohlcv]
        
        # Get indicators
        rsi = self.indicators.get('rsi_14', np.zeros(len(closes)))
        rsi_6 = self.indicators.get('rsi_6', np.zeros(len(closes)))
        ema_12 = self.indicators.get('ema_12', closes)
        ema_26 = self.indicators.get('ema_26', closes)
        bb_lower = self.indicators.get('bb_lower', closes * 0.95)
        bb_upper = self.indicators.get('bb_upper', closes * 1.05)
        atr = self.indicators.get('atr_14', closes * 0.02)
        regime = self.indicators.get('regime', np.full(len(closes), 'unknown'))
        volume_ratio = self.indicators.get('volume_ratio', np.ones(len(closes)))
        
        # Scan for entry points
        for i in range(30, len(self.ohlcv) - max_holding_bars):
            price = closes[i]
            
            # Look ahead to find optimal exit
            future_prices = closes[i+1:i+max_holding_bars+1]
            future_highs = highs[i+1:i+max_holding_bars+1]
            future_lows = lows[i+1:i+max_holding_bars+1]
            
            if len(future_prices) < 5:
                continue
            
            # Simulate LONG entry
            if self._is_long_entry(i, price, rsi, rsi_6, ema_12, ema_26, bb_lower, atr):
                trade = self._simulate_long(i, price, future_prices, future_highs, future_lows,
                                           timestamps, regime, volume_ratio, min_risk_reward)
                if trade and trade.pnl_pct > 0.5:  # At least 0.5% profit
                    trades.append(trade)
            
            # Simulate SHORT entry
            if self._is_short_entry(i, price, rsi, rsi_6, ema_12, ema_26, bb_upper, atr):
                trade = self._simulate_short(i, price, future_prices, future_highs, future_lows,
                                            timestamps, regime, volume_ratio, min_risk_reward)
                if trade and trade.pnl_pct > 0.5:
                    trades.append(trade)
        
        return trades
    
    def _is_long_entry(self, i: int, price: float, rsi, rsi_6, ema_12, ema_26, bb_lower, atr) -> bool:
        """Check if conditions favor long entry."""
        # Multiple entry signals
        signals = 0
        
        # RSI oversold
        if rsi[i] < 35 or rsi_6[i] < 25:
            signals += 1
        
        # Price below lower band
        if price < bb_lower[i]:
            signals += 1
        
        # EMA alignment improving
        if i > 0 and ema_12[i] > ema_12[i-1]:
            signals += 1
        
        # Price near support (using ATR)
        if price < (bb_lower[i] + bb_lower[i-5:i].mean()) / 2:
            signals += 1
        
        return signals >= 2
    
    def _is_short_entry(self, i: int, price: float, rsi, rsi_6, ema_12, ema_26, bb_upper, atr) -> bool:
        """Check if conditions favor short entry."""
        signals = 0
        
        # RSI overbought
        if rsi[i] > 65 or rsi_6[i] > 75:
            signals += 1
        
        # Price above upper band
        if price > bb_upper[i]:
            signals += 1
        
        # EMA alignment deteriorating
        if i > 0 and ema_12[i] < ema_12[i-1]:
            signals += 1
        
        # Price near resistance
        if price > (bb_upper[i] + bb_upper[i-5:i].mean()) / 2:
            signals += 1
        
        return signals >= 2
    
    def _simulate_long(self, entry_idx: int, entry_price: float, 
                       future_prices, future_highs, future_lows,
                       timestamps, regime, volume_ratio, min_rr: float) -> Optional[HistoricalTrade]:
        """Simulate a long trade and return metrics."""
        
        # Set stop loss based on recent low
        stop_loss = min(future_lows[:3]) * 0.998
        
        # Look for optimal exit
        best_exit_idx = 0
        best_pnl = -999
        
        for j in range(1, len(future_prices)):
            pnl = (future_prices[j] - entry_price) / entry_price * 100
            
            # Exit on profit target or reversal
            if pnl > best_pnl:
                best_pnl = pnl
                best_exit_idx = j
            
            # Stop loss hit
            if future_lows[j] < stop_loss:
                if best_pnl > 0:
                    break
                else:
                    return None
            
            # Trailing stop - exit if we give back 30% of profits
            if best_pnl > 1 and pnl < best_pnl * 0.7:
                break
            
            # Time exit
            if j >= len(future_prices) - 1:
                break
        
        if best_pnl <= 0:
            return None
        
        exit_price = future_prices[best_exit_idx]
        
        # Calculate metrics
        max_profit = (max(future_highs[:best_exit_idx+1]) - entry_price) / entry_price * 100
        max_dd = (entry_price - min(future_lows[:best_exit_idx+1])) / entry_price * 100
        
        duration = (timestamps[entry_idx + best_exit_idx] - timestamps[entry_idx]).total_seconds() / 60
        
        return HistoricalTrade(
            symbol='',  # Set by caller
            entry_time=timestamps[entry_idx],
            exit_time=timestamps[entry_idx + best_exit_idx],
            entry_price=entry_price,
            exit_price=exit_price,
            direction='LONG',
            pnl_pct=best_pnl,
            pnl_usd=best_pnl * 10,  # Assuming $1000 position
            max_profit_pct=max_profit,
            max_drawdown_pct=max_dd,
            duration_minutes=int(duration),
            bars_held=best_exit_idx,
            entry_quality=0.8,  # Simplified
            exit_quality=0.7,
            market_regime=regime[entry_idx],
            volume_profile='high' if volume_ratio[entry_idx] > 1.5 else 'normal',
            volatility_regime='high' if max_dd > 2 else 'normal',
            dna_signature=self._get_dna_signature(entry_idx, 'LONG')
        )
    
    def _simulate_short(self, entry_idx: int, entry_price: float,
                        future_prices, future_highs, future_lows,
                        timestamps, regime, volume_ratio, min_rr: float) -> Optional[HistoricalTrade]:
        """Simulate a short trade and return metrics."""
        
        # Set stop loss based on recent high
        stop_loss = max(future_highs[:3]) * 1.002
        
        best_exit_idx = 0
        best_pnl = -999
        
        for j in range(1, len(future_prices)):
            pnl = (entry_price - future_prices[j]) / entry_price * 100
            
            if pnl > best_pnl:
                best_pnl = pnl
                best_exit_idx = j
            
            if future_highs[j] > stop_loss:
                if best_pnl > 0:
                    break
                else:
                    return None
            
            if best_pnl > 1 and pnl < best_pnl * 0.7:
                break
            
            if j >= len(future_prices) - 1:
                break
        
        if best_pnl <= 0:
            return None
        
        exit_price = future_prices[best_exit_idx]
        max_profit = (entry_price - min(future_lows[:best_exit_idx+1])) / entry_price * 100
        max_dd = (max(future_highs[:best_exit_idx+1]) - entry_price) / entry_price * 100
        
        duration = (timestamps[entry_idx + best_exit_idx] - timestamps[entry_idx]).total_seconds() / 60
        
        return HistoricalTrade(
            symbol='',
            entry_time=timestamps[entry_idx],
            exit_time=timestamps[entry_idx + best_exit_idx],
            entry_price=entry_price,
            exit_price=exit_price,
            direction='SHORT',
            pnl_pct=best_pnl,
            pnl_usd=best_pnl * 10,
            max_profit_pct=max_profit,
            max_drawdown_pct=max_dd,
            duration_minutes=int(duration),
            bars_held=best_exit_idx,
            entry_quality=0.8,
            exit_quality=0.7,
            market_regime=regime[entry_idx],
            volume_profile='high' if volume_ratio[entry_idx] > 1.5 else 'normal',
            volatility_regime='high' if max_dd > 2 else 'normal',
            dna_signature=self._get_dna_signature(entry_idx, 'SHORT')
        )
    
    def _get_dna_signature(self, idx: int, direction: str) -> Dict:
        """Extract DNA signature for entry."""
        sig = {'direction': direction}
        
        rsi = self.indicators.get('rsi_14', [50])[idx]
        rsi_6 = self.indicators.get('rsi_6', [50])[idx]
        
        if direction == 'LONG':
            if rsi < 30:
                sig['rsi_deep'] = True
            elif rsi < 40:
                sig['rsi_oversold'] = True
            
            if rsi_6 < 20:
                sig['connors_rsi'] = True
        else:
            if rsi > 70:
                sig['rsi_overbought'] = True
            elif rsi > 60:
                sig['rsi_high'] = True
            
            if rsi_6 > 80:
                sig['connors_short'] = True
        
        return sig


class PerformanceAnalyzer:
    """Analyze pattern performance across metrics."""
    
    @staticmethod
    def calculate_metrics(trades: List[HistoricalTrade], period: str) -> PatternPerformance:
        """Calculate comprehensive performance metrics."""
        
        if not trades:
            return PatternPerformance(
                pattern_name='unknown', dna_genes={}, period=period,
                total_trades=0, winning_trades=0, losing_trades=0, win_rate=0,
                total_pnl_pct=0, avg_trade_pct=0, avg_winner_pct=0, avg_loser_pct=0,
                profit_factor=0, expectancy=0, max_drawdown_pct=0,
                max_consecutive_losses=0, recovery_factor=0,
                avg_holding_minutes=0, median_holding_minutes=0,
                shortest_trade_minutes=0, longest_trade_minutes=0,
                sharpe_ratio=0, sortino_ratio=0, calmar_ratio=0,
                daily_pnl_std=0, consistency_score=0
            )
        
        # Basic counts
        total = len(trades)
        winners = [t for t in trades if t.pnl_pct > 0]
        losers = [t for t in trades if t.pnl_pct <= 0]
        
        win_rate = len(winners) / total
        
        # PnL metrics
        pnls = [t.pnl_pct for t in trades]
        total_pnl = sum(pnls)
        avg_pnl = total_pnl / total
        
        winner_pnls = [t.pnl_pct for t in winners]
        loser_pnls = [t.pnl_pct for t in losers]
        
        avg_winner = np.mean(winner_pnls) if winner_pnls else 0
        avg_loser = np.mean(loser_pnls) if loser_pnls else 0
        
        gross_profit = sum(winner_pnls)
        gross_loss = abs(sum(loser_pnls))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 999
        
        expectancy = (win_rate * avg_winner) - ((1 - win_rate) * abs(avg_loser))
        
        # Drawdown analysis
        max_dd = max(t.max_drawdown_pct for t in trades)
        
        # Consecutive losses
        consecutive_losses = 0
        max_consecutive = 0
        for t in trades:
            if t.pnl_pct <= 0:
                consecutive_losses += 1
                max_consecutive = max(max_consecutive, consecutive_losses)
            else:
                consecutive_losses = 0
        
        recovery_factor = total_pnl / max_dd if max_dd > 0 else 999
        
        # Holding period
        durations = [t.duration_minutes for t in trades]
        avg_duration = np.mean(durations)
        median_duration = np.median(durations)
        
        # Sharpe ratio (assuming daily returns)
        returns = np.array(pnls) / 100
        sharpe = np.mean(returns) / (np.std(returns) + 1e-10) * np.sqrt(365)
        
        # Sortino (downside deviation only)
        downside_returns = [r for r in returns if r < 0]
        downside_std = np.std(downside_returns) if downside_returns else 1e-10
        sortino = np.mean(returns) / downside_std * np.sqrt(365)
        
        # Calmar (return / max drawdown)
        calmar = (total_pnl / 100) / (max_dd / 100) if max_dd > 0 else 999
        
        # Consistency
        daily_std = np.std(pnls)
        consistency = 1 - (daily_std / (abs(avg_pnl) + 1e-10))
        
        return PatternPerformance(
            pattern_name='reverse_engineered',
            dna_genes={},
            period=period,
            total_trades=total,
            winning_trades=len(winners),
            losing_trades=len(losers),
            win_rate=win_rate,
            total_pnl_pct=total_pnl,
            avg_trade_pct=avg_pnl,
            avg_winner_pct=avg_winner,
            avg_loser_pct=avg_loser,
            profit_factor=profit_factor,
            expectancy=expectancy,
            max_drawdown_pct=max_dd,
            max_consecutive_losses=max_consecutive,
            recovery_factor=recovery_factor,
            avg_holding_minutes=avg_duration,
            median_holding_minutes=median_duration,
            shortest_trade_minutes=min(durations),
            longest_trade_minutes=max(durations),
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            calmar_ratio=calmar,
            daily_pnl_std=daily_std,
            consistency_score=max(0, consistency)
        )


class HistoricalReverseEngineer:
    """Main engine for historical reverse engineering."""
    
    def __init__(self):
        self.fetcher = DataFetcher()
        self.results = {}
    
    def analyze_period(self, period: str) -> Dict:
        """Analyze a specific time period."""
        logger.info(f"\n{'='*60}")
        logger.info(f"Analyzing: {period.upper()}")
        logger.info('='*60)
        
        # Fetch data
        data = self.fetcher.fetch_period(period)
        
        all_trades = []
        symbol_trades = {}
        
        # Analyze each symbol
        for symbol in data.keys():
            logger.info(f"Analyzing {symbol}...")
            
            ohlcv = data[symbol]
            indicators = TechnicalAnalyzer.calculate_all(ohlcv)
            
            if not indicators:
                continue
            
            simulator = TradeSimulator(ohlcv, indicators)
            trades = simulator.find_optimal_trades()
            
            # Add symbol to trades
            for t in trades:
                t.symbol = symbol
            
            symbol_trades[symbol] = trades
            all_trades.extend(trades)
            
            logger.info(f"  Found {len(trades)} winning trades")
        
        # Calculate metrics
        metrics = PerformanceAnalyzer.calculate_metrics(all_trades, period)
        
        # Group by pattern
        pattern_groups = defaultdict(list)
        for t in all_trades:
            pattern_key = self._pattern_key(t.dna_signature)
            pattern_groups[pattern_key].append(t)
        
        pattern_performances = []
        for pattern_name, trades in pattern_groups.items():
            perf = PerformanceAnalyzer.calculate_metrics(trades, period)
            perf.pattern_name = pattern_name
            pattern_performances.append(perf)
        
        # Sort by total PnL
        pattern_performances.sort(key=lambda x: x.total_pnl_pct, reverse=True)
        
        result = {
            'period': period,
            'total_trades': len(all_trades),
            'symbols_analyzed': len(data),
            'overall_metrics': asdict(metrics),
            'pattern_performance': [asdict(p) for p in pattern_performances[:10]],
            'symbol_breakdown': {sym: len(trades) for sym, trades in symbol_trades.items()},
            'best_trades': [
                {
                    'symbol': t.symbol,
                    'direction': t.direction,
                    'entry': t.entry_price,
                    'exit': t.exit_price,
                    'pnl_pct': t.pnl_pct,
                    'duration_min': t.duration_minutes,
                    'max_dd': t.max_drawdown_pct,
                    'regime': t.market_regime
                }
                for t in sorted(all_trades, key=lambda x: x.pnl_pct, reverse=True)[:20]
            ]
        }
        
        self.results[period] = result
        return result
    
    def _pattern_key(self, dna: Dict) -> str:
        """Generate pattern key from DNA."""
        parts = []
        if dna.get('rsi_deep'):
            parts.append('RSI_Deep')
        elif dna.get('rsi_oversold'):
            parts.append('RSI_Oversold')
        elif dna.get('connors_rsi'):
            parts.append('Connors_RSI2')
        
        if dna.get('rsi_overbought'):
            parts.append('RSI_Overbought')
        
        if not parts:
            parts.append('Mixed_Signals')
        
        return '+'.join(parts)
    
    def compare_periods(self) -> Dict:
        """Compare patterns across all analyzed periods."""
        if len(self.results) < 2:
            logger.error("Need at least 2 periods to compare")
            return {}
        
        comparison = {
            'periods': list(self.results.keys()),
            'consistent_patterns': [],
            'period_comparison': []
        }
        
        # Compare metrics across periods
        for period, result in self.results.items():
            metrics = result['overall_metrics']
            comparison['period_comparison'].append({
                'period': period,
                'trades': metrics['total_trades'],
                'win_rate': metrics['win_rate'],
                'total_pnl': metrics['total_pnl_pct'],
                'sharpe': metrics['sharpe_ratio'],
                'max_dd': metrics['max_drawdown_pct'],
                'avg_hold_time': metrics['avg_holding_minutes']
            })
        
        return comparison
    
    def print_report(self, result: Dict):
        """Print formatted report."""
        period = result['period']
        metrics = result['overall_metrics']
        
        print(f"\n{'='*80}")
        print(f"  HISTORICAL REVERSE ENGINEER - {period.upper()}")
        print('='*80)
        
        print(f"\n[OVERALL METRICS]")
        print(f"   Trades: {metrics['total_trades']}")
        print(f"   Symbols: {result['symbols_analyzed']}")
        print(f"   Win Rate: {metrics['win_rate']:.1%}")
        print(f"   Total PnL: {metrics['total_pnl_pct']:.1f}%")
        print(f"   Avg Trade: {metrics['avg_trade_pct']:.2f}%")
        print(f"   Profit Factor: {metrics['profit_factor']:.2f}")
        print(f"   Expectancy: {metrics['expectancy']:.2f}%")
        
        print(f"\n[HOLDING TIME ANALYSIS]")
        print(f"   Average: {metrics['avg_holding_minutes']:.0f} minutes ({metrics['avg_holding_minutes']/60:.1f} hours)")
        print(f"   Median: {metrics['median_holding_minutes']:.0f} minutes")
        print(f"   Range: {metrics['shortest_trade_minutes']}-{metrics['longest_trade_minutes']} minutes")
        
        print(f"\n[RISK METRICS]")
        print(f"   Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
        print(f"   Sortino Ratio: {metrics['sortino_ratio']:.2f}")
        print(f"   Calmar Ratio: {metrics['calmar_ratio']:.2f}")
        print(f"   Max Drawdown: {metrics['max_drawdown_pct']:.1f}%")
        print(f"   Recovery Factor: {metrics['recovery_factor']:.2f}")
        print(f"   Max Consecutive Losses: {metrics['max_consecutive_losses']}")
        
        print(f"\n[TOP PATTERNS]")
        for i, p in enumerate(result['pattern_performance'][:5], 1):
            print(f"\n   {i}. {p['pattern_name']}")
            print(f"      Trades: {p['total_trades']} | Win Rate: {p['win_rate']:.1%}")
            print(f"      Total PnL: {p['total_pnl_pct']:.1f}% | Profit Factor: {p['profit_factor']:.2f}")
            print(f"      Sharpe: {p['sharpe_ratio']:.2f} | Avg Hold: {p['avg_holding_minutes']:.0f}min")
        
        print(f"\n[BEST TRADES]")
        for i, t in enumerate(result['best_trades'][:5], 1):
            print(f"   {i}. {t['symbol']} {t['direction']}: +{t['pnl_pct']:.2f}% "
                  f"in {t['duration_min']}min | DD: {t['max_dd']:.1f}% | {t['regime']}")
        
        print('\n' + '='*80 + '\n')


# ==================== MAIN ====================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Historical Reverse Engineer')
    parser.add_argument('--today', action='store_true', help='Analyze today')
    parser.add_argument('--yesterday', action='store_true', help='Analyze yesterday')
    parser.add_argument('--week', action='store_true', help='Analyze last week')
    parser.add_argument('--month', action='store_true', help='Analyze last month')
    parser.add_argument('--all', action='store_true', help='Analyze all periods')
    parser.add_argument('--compare', action='store_true', help='Compare periods')
    
    args = parser.parse_args()
    
    engineer = HistoricalReverseEngineer()
    
    periods = []
    if args.today or args.all:
        periods.append('today')
    if args.yesterday or args.all:
        periods.append('yesterday')
    if args.week or args.all:
        periods.append('week')
    if args.month or args.all:
        periods.append('month')
    
    if not periods:
        print("Usage: python historical_reverse_engineer.py --today|--yesterday|--week|--month|--all")
        print("\nExamples:")
        print("  --today      Analyze last 24 hours")
        print("  --yesterday  Analyze 24-48 hours ago")
        print("  --week       Analyze last 7 days")
        print("  --month      Analyze last 30 days")
        print("  --all        Analyze all periods")
        print("  --compare    Compare patterns across periods")
        exit(0)
    
    # Analyze each period
    for period in periods:
        result = engineer.analyze_period(period)
        engineer.print_report(result)
        
        # Save results
        output_path = Path(f'genome/results/historical_{period}.json')
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        print(f"\n[SAVED] {output_path}")
    
    # Compare if multiple periods
    if len(periods) > 1 and args.compare:
        comparison = engineer.compare_periods()
        
        print(f"\n{'='*80}")
        print("  PERIOD COMPARISON")
        print('='*80 + '\n')
        
        for comp in comparison['period_comparison']:
            print(f"\n{comp['period'].upper()}:")
            print(f"  Trades: {comp['trades']} | Win Rate: {comp['win_rate']:.1%} | "
                  f"PnL: {comp['total_pnl']:.1f}%")
            print(f"  Sharpe: {comp['sharpe']:.2f} | Max DD: {comp['max_dd']:.1f}% | "
                  f"Avg Hold: {comp['avg_hold_time']:.0f}min")
        
        # Save comparison
        with open('genome/results/historical_comparison.json', 'w') as f:
            json.dump(comparison, f, indent=2)
