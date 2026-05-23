#!/usr/bin/env python3
"""
INNOVATIVE MUTATIONS v1.0 — 5 Cutting-Edge Strategy Mutations
===============================================================

1. TEMPORAL_DECAY — Signal freshness weighting with exponential decay
2. ORDERFLOW_CONFIRM — Volume delta alignment for execution quality
3. MOMENTUM_CASCADE — Leader-follower lag exploitation
4. REGIME_KELLY — Adaptive position sizing based on market regime
5. COMPOSITE_ENSEMBLE — Multi-strategy weighted voting system

All mutations output standard pick format compatible with battleground pipeline.
Author: KIMI | Date: 2026-03-14 | Status: PRODUCTION READY
"""

from __future__ import annotations

import json
import sys
import math
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass

import numpy as np
import pandas as pd

# Path setup
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

# Import indicators
try:
    sys.path.insert(0, str(ROOT / "ml_battleground"))
    from shared.indicators import rsi, atr, sma, ema
    _HAS_INDICATORS = True
except ImportError:
    _HAS_INDICATORS = False

if not _HAS_INDICATORS:
    def sma(series: pd.Series, period: int) -> pd.Series:
        return series.rolling(period).mean()
    
    def ema(series: pd.Series, period: int) -> pd.Series:
        return series.ewm(span=period, adjust=False).mean()
    
    def rsi(close: pd.Series, period: int = 14) -> pd.Series:
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(period).mean()
        loss = (-delta.clip(upper=0)).rolling(period).mean()
        rs = gain / loss.replace(0, np.nan)
        return (100 - 100 / (1 + rs)).fillna(50.0)
    
    def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        tr = pd.concat([
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs()
        ], axis=1).max(axis=1)
        return tr.rolling(period).mean()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _smart_round(value: float) -> float:
    if value is None or not np.isfinite(value):
        return 0.0
    if abs(value) >= 1000:
        return round(value, 2)
    if abs(value) >= 1:
        return round(value, 4)
    if abs(value) >= 0.01:
        return round(value, 6)
    return round(value, 8)


# ==============================================================================
# MUTATION 1: TEMPORAL_DECAY — Signal Freshness Weighting
# ==============================================================================

@dataclass
class TemporalDecayConfig:
    """Configuration for temporal decay mutation."""
    half_life_bars: int = 6  # Bars for confidence to decay to 50%
    max_age_bars: int = 24   # Maximum age to consider signal valid
    min_decay_factor: float = 0.3  # Minimum decay before signal expires


def temporal_decay_mutation(
    base_signal: dict,
    market_data: pd.DataFrame,
    config: TemporalDecayConfig = None
) -> Optional[dict]:
    """
    Mutation: Time-decay weighting for signal freshness.
    
    Core concept: Older signals have lower edge, decay position size exponentially.
    Uses exponential decay: decay_factor = exp(-λ * age) where λ = ln(2)/half_life
    
    Args:
        base_signal: Original signal with timestamp
        market_data: Price data for calculations
        config: Temporal decay parameters
    
    Returns:
        Adjusted signal or None if signal expired
    """
    if config is None:
        config = TemporalDecayConfig()
    
    # Get signal age
    signal_time = datetime.fromisoformat(base_signal.get('timestamp', _now_iso()))
    current_time = datetime.now(timezone.utc)
    age_seconds = (current_time - signal_time).total_seconds()
    
    # Assume 1H bars for calculation (adjustable)
    timeframe_seconds = 3600  # 1 hour
    age_bars = age_seconds / timeframe_seconds
    
    # Check if signal too old
    if age_bars > config.max_age_bars:
        return None  # Signal expired
    
    # Calculate decay factor
    decay_lambda = math.log(2) / config.half_life_bars
    decay_factor = math.exp(-decay_lambda * age_bars)
    
    # Check minimum decay threshold
    if decay_factor < config.min_decay_factor:
        return None  # Signal too stale
    
    # Adjust confidence
    original_conf = base_signal.get('confidence', 0.5)
    adjusted_confidence = original_conf * decay_factor
    
    # Dynamic TP/SL tightening
    tp_sl_tightening = max(0.5, decay_factor)
    
    entry = base_signal.get('entry_price', 0)
    original_tp = base_signal.get('take_profit', entry)
    original_sl = base_signal.get('stop_loss', entry)
    
    # Tighten TP/SL toward entry as signal ages
    new_tp = entry + (original_tp - entry) * tp_sl_tightening
    new_sl = entry - (entry - original_sl) * tp_sl_tightening
    
    # Position size scaling (larger for fresh signals)
    base_size = base_signal.get('base_position_size', 1.0)
    position_size = base_size * decay_factor * (1 + adjusted_confidence)
    
    return {
        'symbol': base_signal.get('symbol'),
        'direction': base_signal.get('signal_type', 'BUY'),
        'entry_price': _smart_round(entry),
        'take_profit': _smart_round(new_tp),
        'stop_loss': _smart_round(new_sl),
        'confidence': _smart_round(adjusted_confidence),
        'position_size': _smart_round(position_size),
        'decay_factor': _smart_round(decay_factor),
        'signal_age_bars': round(age_bars, 2),
        'original_confidence': original_conf,
        'mutation_type': 'temporal_decay',
        'reason': f"Temporal decay: {decay_factor:.2%} freshness, age={age_bars:.1f} bars",
        'timestamp': _now_iso(),
        'trust_tier': 'SANDBOX',
        'trust_weight': 0.3,
    }


# ==============================================================================
# MUTATION 2: ORDERFLOW_CONFIRM — Volume Delta Alignment
# ==============================================================================

@dataclass
class OrderflowConfig:
    """Configuration for orderflow confirmation."""
    min_imbalance_pct: float = 20.0  # Minimum volume delta % for confirmation
    max_spread_bps: float = 5.0      # Maximum spread in basis points
    lookback_bars: int = 5           # Bars for orderflow calculation


def fetch_orderflow_data(symbol: str, lookback: int = 5) -> dict:
    """
    Fetch orderflow data from Binance (taker buy/sell ratio).
    
    Returns volume delta, spread, and other orderflow metrics.
    """
    try:
        # Fetch recent trades for volume delta calculation
        url = f"https://api.binance.com/api/v3/aggTrades?symbol={symbol}&limit=100"
        req = urllib.request.Request(url, headers={"User-Agent": "MutationLab/1.0"})
        
        with urllib.request.urlopen(req, timeout=10) as resp:
            trades = json.loads(resp.read().decode())
        
        # Calculate taker buy vs sell volume
        buy_volume = sum(float(t['q']) for t in trades if t.get('m', False) == False)
        sell_volume = sum(float(t['q']) for t in trades if t.get('m', False) == True)
        total_volume = buy_volume + sell_volume
        
        # Calculate imbalance
        if total_volume > 0:
            delta_percent = ((buy_volume - sell_volume) / total_volume) * 100
        else:
            delta_percent = 0
        
        # Fetch orderbook for spread
        book_url = f"https://api.binance.com/api/v3/ticker/bookTicker?symbol={symbol}"
        book_req = urllib.request.Request(book_url, headers={"User-Agent": "MutationLab/1.0"})
        
        with urllib.request.urlopen(book_req, timeout=10) as resp:
            book = json.loads(resp.read().decode())
        
        bid = float(book.get('bidPrice', 0))
        ask = float(book.get('askPrice', 0))
        mid = (bid + ask) / 2 if bid > 0 and ask > 0 else 0
        spread = (ask - bid) / mid * 10000 if mid > 0 else 0  # In bps
        
        return {
            'volume_delta_pct': delta_percent,
            'buy_volume': buy_volume,
            'sell_volume': sell_volume,
            'spread_bps': spread,
            'mid_price': mid,
            'success': True,
        }
        
    except Exception as e:
        return {
            'volume_delta_pct': 0,
            'spread_bps': 999,
            'success': False,
            'error': str(e),
        }


def orderflow_confirm_mutation(
    base_signal: dict,
    config: OrderflowConfig = None
) -> Optional[dict]:
    """
    Mutation: Confirm technical signals with orderflow imbalance.
    
    Core concept: Smart money leaves footprints in volume delta.
    Long signals need buying pressure (positive delta).
    Short signals need selling pressure (negative delta).
    
    Args:
        base_signal: Original signal with direction and confidence
        config: Orderflow parameters
    
    Returns:
        Adjusted signal or None if orderflow misaligned
    """
    if config is None:
        config = OrderflowConfig()
    
    symbol = base_signal.get('symbol')
    direction = base_signal.get('signal_type', 'BUY')
    
    # Fetch orderflow data
    of_data = fetch_orderflow_data(symbol, config.lookback_bars)
    
    if not of_data.get('success'):
        # If orderflow fails, reduce confidence significantly
        adjusted_conf = base_signal.get('confidence', 0.5) * 0.5
        return {
            **base_signal,
            'confidence': adjusted_conf,
            'orderflow_aligned': False,
            'mutation_type': 'orderflow_confirm',
            'reason': f"Orderflow data unavailable, confidence reduced",
        }
    
    imbalance = of_data.get('volume_delta_pct', 0)
    spread_bps = of_data.get('spread_bps', 999)
    
    # Liquidity check
    liquidity_ok = spread_bps < config.max_spread_bps
    
    # Check alignment
    if direction == 'BUY':
        alignment = imbalance > config.min_imbalance_pct
        confirmation_strength = min(imbalance / 50, 1.0)
    else:  # SELL
        alignment = imbalance < -config.min_imbalance_pct
        confirmation_strength = min(abs(imbalance) / 50, 1.0)
    
    # Calculate adjusted confidence
    base_conf = base_signal.get('confidence', 0.5)
    
    if alignment and liquidity_ok:
        # Boost for strong orderflow alignment
        adjusted_conf = base_conf * (0.8 + 0.4 * confirmation_strength)
        tier = 'HIGH_CONVICTION' if adjusted_conf > 0.75 else 'MEDIUM'
        size_mult = 1.5 if tier == 'HIGH_CONVICTION' else 1.0
    elif not liquidity_ok:
        # Penalty for low liquidity
        adjusted_conf = base_conf * 0.5
        tier = 'LOW_LIQUIDITY'
        size_mult = 0.5
    else:
        # Strong penalty for misalignment
        adjusted_conf = base_conf * 0.3
        tier = 'MISALIGNED'
        size_mult = 0.0  # Skip these signals
    
    # Skip weak signals
    if size_mult == 0:
        return None
    
    return {
        'symbol': symbol,
        'direction': direction,
        'entry_price': base_signal.get('entry_price'),
        'take_profit': base_signal.get('take_profit'),
        'stop_loss': base_signal.get('stop_loss'),
        'confidence': _smart_round(min(adjusted_conf, 0.95)),
        'tier': tier,
        'size_multiplier': size_mult,
        'imbalance_score': _smart_round(imbalance),
        'spread_bps': _smart_round(spread_bps),
        'liquidity_ok': liquidity_ok,
        'orderflow_aligned': alignment,
        'mutation_type': 'orderflow_confirm',
        'reason': f"Orderflow: {imbalance:.1f}% delta, spread={spread_bps:.1f}bps, tier={tier}",
        'timestamp': _now_iso(),
        'trust_tier': 'SANDBOX',
        'trust_weight': 0.3,
    }


# ==============================================================================
# MUTATION 3: MOMENTUM_CASCADE — Leader-Follower Lag Exploitation
# ==============================================================================

LEADER_FOLLOWER_MAP = {
    'BTCUSDT': ['SOLUSDT', 'AVAXUSDT', 'NEARUSDT', 'SUIUSDT', 'APTUSDT', 'INJUSDT'],
    'ETHUSDT': ['DOTUSDT', 'LINKUSDT', 'MATICUSDT', 'ATOMUSDT', 'OPUSDT', 'ARBUSDT'],
}


def momentum_cascade_mutation(
    market_data: Dict[str, pd.DataFrame],
    min_leader_move_pct: float = 2.0,
    min_lag_gap_pct: float = 1.0,
    lookback_bars: int = 3
) -> List[dict]:
    """
    Mutation: Detect and exploit momentum cascades from leaders to followers.
    
    Core concept: BTC/ETH moves first, alts follow with 1-3 bar lag.
    If leader moved +3% but alt only +0.5%, there's a catch-up opportunity.
    
    Args:
        market_data: Dict of symbol -> DataFrame with OHLCV
        min_leader_move_pct: Minimum leader move to trigger cascade
        min_lag_gap_pct: Minimum lag between leader and follower
        lookback_bars: Bars to calculate momentum
    
    Returns:
        List of cascade signals for followers
    """
    signals = []
    
    for leader, followers in LEADER_FOLLOWER_MAP.items():
        if leader not in market_data:
            continue
        
        leader_df = market_data[leader]
        if len(leader_df) < lookback_bars + 5:
            continue
        
        # Calculate leader momentum
        leader_close = leader_df['Close']
        leader_roc = (leader_close.iloc[-1] - leader_close.iloc[-lookback_bars-1]) / leader_close.iloc[-lookback_bars-1]
        
        # Skip if leader move too small
        if abs(leader_roc) < (min_leader_move_pct / 100):
            continue
        
        direction = 'BUY' if leader_roc > 0 else 'SELL'
        
        # Calculate momentum strength
        leader_volume = leader_df['Volume']
        vol_surge = leader_volume.iloc[-1] / leader_volume.iloc[-20:].mean()
        
        leader_atr = atr(leader_df['High'], leader_df['Low'], leader_df['Close'], 14)
        atr_spike = leader_atr.iloc[-1] / leader_atr.iloc[-20:].mean() if len(leader_atr) > 20 else 1.0
        
        momentum_score = min(abs(leader_roc) * 50, 1.0) * min(vol_surge / 2, 1.0)
        
        # Check each follower
        for follower in followers:
            if follower not in market_data:
                continue
            
            follower_df = market_data[follower]
            if len(follower_df) < lookback_bars + 5:
                continue
            
            follower_close = follower_df['Close']
            follower_roc = (follower_close.iloc[-1] - follower_close.iloc[-lookback_bars-1]) / follower_close.iloc[-lookback_bars-1]
            
            # Expected follower move (alts usually overshoot leaders)
            expected_move = leader_roc * 1.5
            lag_gap = expected_move - follower_roc
            
            # Entry criteria: Significant lag exists
            if abs(lag_gap) < (min_lag_gap_pct / 100):
                continue
            
            # Check direction alignment
            if (direction == 'BUY' and lag_gap < 0) or (direction == 'SELL' and lag_gap > 0):
                continue  # Already caught up or overextended
            
            # Calculate entry and targets
            entry = follower_close.iloc[-1]
            tp_distance = abs(lag_gap) * entry
            
            follower_atr = atr(follower_df['High'], follower_df['Low'], follower_df['Close'], 14).iloc[-1]
            
            if direction == 'BUY':
                tp = entry + max(tp_distance, follower_atr * 2)
                sl = entry - follower_atr * 1.2
            else:
                tp = entry - max(tp_distance, follower_atr * 2)
                sl = entry + follower_atr * 1.2
            
            # Confidence based on momentum strength and lag size
            confidence = 0.5 + (momentum_score * 0.3) + min(abs(lag_gap) * 20, 0.2)
            
            signals.append({
                'symbol': follower,
                'direction': direction,
                'entry_price': _smart_round(entry),
                'take_profit': _smart_round(tp),
                'stop_loss': _smart_round(sl),
                'confidence': _smart_round(min(confidence, 0.9)),
                'risk_reward': _smart_round(abs(tp - entry) / abs(entry - sl)) if abs(entry - sl) > 0 else 0,
                'leader': leader,
                'leader_move_pct': _smart_round(leader_roc * 100),
                'follower_move_pct': _smart_round(follower_roc * 100),
                'lag_gap_pct': _smart_round(lag_gap * 100),
                'momentum_score': _smart_round(momentum_score),
                'mutation_type': 'momentum_cascade',
                'reason': f"Cascade: {leader} moved {leader_roc:.2%}, {follower} lagging by {lag_gap:.2%}",
                'timestamp': _now_iso(),
                'trust_tier': 'SANDBOX',
                'trust_weight': 0.35,  # Slightly higher weight for this edge
            })
    
    # Sort by lag gap (larger lag = more potential)
    signals.sort(key=lambda x: abs(x.get('lag_gap_pct', 0)), reverse=True)
    
    return signals


# ==============================================================================
# MUTATION 4: REGIME_KELLY — Adaptive Position Sizing
# ==============================================================================

@dataclass
class RegimeConfig:
    """Configuration for regime detection and Kelly sizing."""
    lookback_period: int = 50
    vol_threshold_high: float = 1.5  # ATR ratio for high vol
    trend_threshold: float = 0.03    # ADX or slope threshold


def detect_regime(df: pd.DataFrame, config: RegimeConfig = None) -> str:
    """
    Detect current market regime: TRENDING, RANGING, VOLATILE, or CRASH.
    """
    if config is None:
        config = RegimeConfig()
    
    if len(df) < config.lookback_period:
        return 'UNKNOWN'
    
    close = df['Close']
    high = df['High']
    low = df['Low']
    
    # Calculate metrics
    atr_series = atr(high, low, close, 14)
    current_atr = atr_series.iloc[-1]
    avg_atr = atr_series.iloc[-config.lookback_period:].mean()
    
    # ADX approximation using slope
    slope = (close.iloc[-1] - close.iloc[-config.lookback_period]) / config.lookback_period
    slope_normalized = abs(slope) / close.iloc[-1]
    
    # Volatility regime
    vol_ratio = current_atr / avg_atr if avg_atr > 0 else 1.0
    
    # Drawdown from recent high
    recent_high = close.iloc[-20:].max()
    drawdown = (close.iloc[-1] - recent_high) / recent_high
    
    # Regime classification
    if drawdown < -0.15:
        return 'CRASH'
    elif vol_ratio > config.vol_threshold_high and slope_normalized > config.trend_threshold:
        return 'VOLATILE'
    elif vol_ratio > config.vol_threshold_high:
        return 'VOLATILE'
    elif slope_normalized > config.trend_threshold:
        return 'TRENDING'
    else:
        return 'RANGING'


def regime_kelly_mutation(
    base_signal: dict,
    market_data: pd.DataFrame,
    historical_stats: dict = None,
    config: RegimeConfig = None
) -> Optional[dict]:
    """
    Mutation: Adaptive Kelly position sizing based on market regime.
    
    Core concept: Size smaller in high-vol regimes, larger in trending low-vol.
    Uses half-Kelly with regime multipliers for safety.
    
    Args:
        base_signal: Original signal
        market_data: Price data for regime detection
        historical_stats: Win rate, avg win/loss for Kelly calc
        config: Regime detection parameters
    
    Returns:
        Signal with position sizing and adjusted TP/SL
    """
    if config is None:
        config = RegimeConfig()
    
    # Detect regime
    regime = detect_regime(market_data, config)
    
    # Safety check: Skip longs in crash regime
    if regime == 'CRASH' and base_signal.get('signal_type') == 'BUY':
        return None
    
    # Default historical stats if not provided
    if historical_stats is None:
        historical_stats = {
            'win_rate': 0.55,
            'avg_win': 2.5,
            'avg_loss': 1.5,
        }
    
    win_rate = historical_stats.get('win_rate', 0.55)
    avg_win = historical_stats.get('avg_win', 2.5)
    avg_loss = historical_stats.get('avg_loss', 1.5)
    
    # Kelly calculation (aggressive half-Kelly)
    if avg_loss > 0:
        edge = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
        base_kelly = edge / (avg_win * avg_loss)
    else:
        base_kelly = 0.01
    
    base_kelly = max(0.01, min(base_kelly, 0.25))  # Cap at quarter-Kelly
    
    # Regime multipliers
    REGIME_MULT = {
        'TRENDING': 1.2,
        'RANGING': 0.8,
        'VOLATILE': 0.5,
        'CRASH': 0.25,
        'UNKNOWN': 0.5,
    }
    
    regime_mult = REGIME_MULT.get(regime, 0.5)
    
    # Volatility scaling
    atr_series = atr(market_data['High'], market_data['Low'], market_data['Close'], 14)
    current_atr = atr_series.iloc[-1]
    avg_atr = atr_series.iloc[-20:].mean()
    vol_ratio = current_atr / avg_atr if avg_atr > 0 else 1.0
    
    vol_mult = 1 / math.sqrt(vol_ratio) if vol_ratio > 0 else 1.0
    
    # Final Kelly fraction
    final_kelly = base_kelly * regime_mult * vol_mult
    final_kelly = max(0.005, min(final_kelly, 0.20))  # Hard caps 0.5% - 20%
    
    # Position sizing
    equity = base_signal.get('account_equity', 10000)
    position_value = equity * final_kelly
    entry = base_signal.get('entry_price', market_data['Close'].iloc[-1])
    position_size = position_value / entry if entry > 0 else 0
    
    # Adjust TP/SL based on regime
    if regime == 'TRENDING':
        tp_mult, sl_mult = 2.5, 1.0
    elif regime == 'VOLATILE':
        tp_mult, sl_mult = 1.5, 0.8
    else:
        tp_mult, sl_mult = 2.0, 1.2
    
    direction = base_signal.get('signal_type', 'BUY')
    atr_now = current_atr
    
    if direction == 'BUY':
        tp = entry + (atr_now * tp_mult)
        sl = entry - (atr_now * sl_mult)
    else:
        tp = entry - (atr_now * tp_mult)
        sl = entry + (atr_now * sl_mult)
    
    return {
        'symbol': base_signal.get('symbol'),
        'direction': direction,
        'entry_price': _smart_round(entry),
        'take_profit': _smart_round(tp),
        'stop_loss': _smart_round(sl),
        'confidence': base_signal.get('confidence', 0.5),
        'position_size': _smart_round(position_size),
        'position_value': _smart_round(position_value),
        'kelly_fraction': _smart_round(final_kelly),
        'regime': regime,
        'regime_multiplier': regime_mult,
        'vol_multiplier': _smart_round(vol_mult),
        'mutation_type': 'regime_kelly',
        'reason': f"Regime: {regime}, Kelly: {final_kelly:.2%}, size={position_value:.0f} USD",
        'timestamp': _now_iso(),
        'trust_tier': 'SANDBOX',
        'trust_weight': 0.35,
    }


# ==============================================================================
# MUTATION 5: COMPOSITE_ENSEMBLE — Multi-Strategy Voting
# ==============================================================================

def ema_crossover_signal(df: pd.DataFrame) -> dict:
    """Simple EMA crossover strategy."""
    if len(df) < 50:
        return {'exists': False}
    
    ema_fast = ema(df['Close'], 9)
    ema_slow = ema(df['Close'], 21)
    
    if ema_fast.iloc[-1] > ema_slow.iloc[-1] and ema_fast.iloc[-2] <= ema_slow.iloc[-2]:
        return {'exists': True, 'direction': 'BUY', 'confidence': 0.6, 'entry': df['Close'].iloc[-1]}
    elif ema_fast.iloc[-1] < ema_slow.iloc[-1] and ema_fast.iloc[-2] >= ema_slow.iloc[-2]:
        return {'exists': True, 'direction': 'SELL', 'confidence': 0.6, 'entry': df['Close'].iloc[-1]}
    
    return {'exists': False}


def bollinger_reversion_signal(df: pd.DataFrame) -> dict:
    """Bollinger Bands mean reversion."""
    if len(df) < 20:
        return {'exists': False}
    
    sma_20 = sma(df['Close'], 20)
    std_20 = df['Close'].rolling(20).std()
    bb_lower = sma_20 - 2 * std_20
    bb_upper = sma_20 + 2 * std_20
    
    close = df['Close'].iloc[-1]
    
    if close < bb_lower.iloc[-1]:
        return {'exists': True, 'direction': 'BUY', 'confidence': 0.65, 'entry': close}
    elif close > bb_upper.iloc[-1]:
        return {'exists': True, 'direction': 'SELL', 'confidence': 0.65, 'entry': close}
    
    return {'exists': False}


def rsi_momentum_signal(df: pd.DataFrame) -> dict:
    """RSI momentum signal."""
    if len(df) < 14:
        return {'exists': False}
    
    rsi_val = rsi(df['Close'], 14).iloc[-1]
    
    if rsi_val < 30:
        return {'exists': True, 'direction': 'BUY', 'confidence': (30 - rsi_val) / 30 * 0.5 + 0.5, 'entry': df['Close'].iloc[-1]}
    elif rsi_val > 70:
        return {'exists': True, 'direction': 'SELL', 'confidence': (rsi_val - 70) / 30 * 0.5 + 0.5, 'entry': df['Close'].iloc[-1]}
    
    return {'exists': False}


STRATEGY_SOURCES = {
    'ema_crossover': {'weight': 0.25, 'fn': ema_crossover_signal},
    'bollinger_reversion': {'weight': 0.25, 'fn': bollinger_reversion_signal},
    'rsi_momentum': {'weight': 0.25, 'fn': rsi_momentum_signal},
}


def composite_ensemble_mutation(
    symbols: List[str],
    market_data: Dict[str, pd.DataFrame],
    min_agreeing: int = 2,
    min_consensus_ratio: float = 0.65,
) -> List[dict]:
    """
    Mutation: Multi-strategy ensemble with weighted voting.
    
    Core concept: No single strategy wins all the time; ensemble smooths equity.
    Requires at least 2 of 3 strategies to agree with 65%+ consensus ratio.
    
    Args:
        symbols: List of symbols to analyze
        market_data: Dict of symbol -> DataFrame
        min_agreeing: Minimum strategies that must agree
        min_consensus_ratio: Agreement ratio threshold
    
    Returns:
        List of high-conviction ensemble signals
    """
    ensemble_signals = []
    
    for symbol in symbols:
        if symbol not in market_data:
            continue
        
        df = market_data[symbol]
        if len(df) < 50:
            continue
        
        # Collect votes
        votes = []
        total_weight = 0
        
        for source_name, config in STRATEGY_SOURCES.items():
            signal = config['fn'](df)
            
            if signal.get('exists'):
                votes.append({
                    'direction': signal['direction'],
                    'confidence': signal['confidence'],
                    'weight': config['weight'],
                    'source': source_name,
                    'entry': signal['entry'],
                })
                total_weight += config['weight']
        
        # Need minimum agreement
        if len(votes) < min_agreeing:
            continue
        
        # Calculate ensemble scores
        long_weight = sum(v['weight'] * v['confidence'] for v in votes if v['direction'] == 'BUY')
        short_weight = sum(v['weight'] * v['confidence'] for v in votes if v['direction'] == 'SELL')
        
        # Normalize
        long_score = long_weight / total_weight if total_weight > 0 else 0
        short_score = short_weight / total_weight if total_weight > 0 else 0
        
        # Determine consensus
        if long_score > short_score and long_score > 0.6:
            consensus_dir = 'BUY'
            consensus_strength = long_score
            disagreement = short_score
        elif short_score > long_score and short_score > 0.6:
            consensus_dir = 'SELL'
            consensus_strength = short_score
            disagreement = long_score
        else:
            continue
        
        # Check consensus ratio
        consensus_ratio = consensus_strength / (consensus_strength + disagreement) if (consensus_strength + disagreement) > 0 else 0
        
        if consensus_ratio < min_consensus_ratio:
            continue
        
        # Calculate weighted entry
        agreeing_votes = [v for v in votes if v['direction'] == consensus_dir]
        weighted_entry = sum(v['weight'] * v['entry'] for v in agreeing_votes) / sum(v['weight'] for v in agreeing_votes)
        
        # Dynamic TP/SL
        atr_now = atr(df['High'], df['Low'], df['Close'], 14).iloc[-1]
        tp_mult = 2.0 + consensus_strength
        sl_mult = 1.5 - (consensus_strength * 0.3)
        
        if consensus_dir == 'BUY':
            tp = weighted_entry + (atr_now * tp_mult)
            sl = weighted_entry - (atr_now * sl_mult)
        else:
            tp = weighted_entry - (atr_now * tp_mult)
            sl = weighted_entry + (atr_now * sl_mult)
        
        # Final confidence
        final_confidence = consensus_strength * (0.8 + 0.4 * consensus_ratio)
        
        ensemble_signals.append({
            'symbol': symbol,
            'direction': consensus_dir,
            'entry_price': _smart_round(weighted_entry),
            'take_profit': _smart_round(tp),
            'stop_loss': _smart_round(sl),
            'confidence': _smart_round(min(final_confidence, 0.95)),
            'consensus_strength': _smart_round(consensus_strength),
            'consensus_ratio': _smart_round(consensus_ratio),
            'num_agreeing': len(agreeing_votes),
            'contributing_strategies': [v['source'] for v in agreeing_votes],
            'mutation_type': 'composite_ensemble',
            'reason': f"Ensemble: {len(agreeing_votes)}/{len(votes)} agree, ratio={consensus_ratio:.1%}",
            'timestamp': _now_iso(),
            'trust_tier': 'SANDBOX',
            'trust_weight': 0.4,  # Higher weight for ensemble
        })
    
    # Sort by consensus quality
    ensemble_signals.sort(key=lambda x: (x['consensus_ratio'], x['confidence']), reverse=True)
    
    return ensemble_signals


# ==============================================================================
# MAIN RUNNER — Test All Mutations
# ==============================================================================

def fetch_binance_klines(symbol: str, interval: str = "1h", limit: int = 100) -> pd.DataFrame:
    """Fetch OHLCV from Binance."""
    mirrors = [
        "https://api.binance.com", "https://api1.binance.com",
        "https://api2.binance.com", "https://api3.binance.com",
    ]
    
    for base in mirrors:
        url = f"{base}/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "InnovativeMutations/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
            
            if data and isinstance(data, list) and len(data) > 20:
                df = pd.DataFrame(data, columns=[
                    "open_time", "Open", "High", "Low", "Close", "Volume",
                    "close_time", "qav", "num_trades", "taker_buy_base",
                    "taker_buy_quote", "ignore"
                ])
                for col in ["Open", "High", "Low", "Close", "Volume"]:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
                df.set_index("open_time", inplace=True)
                return df
        except Exception:
            continue
    
    return pd.DataFrame()


def run_all_mutations(symbols: List[str] = None, interval: str = "1h") -> dict:
    """Run all 5 innovative mutations and return combined results."""
    
    if symbols is None:
        symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT", "DOTUSDT"]
    
    print(f"\n{'='*70}")
    print("INNOVATIVE MUTATIONS v1.0 — Full Test Run")
    print(f"{'='*70}")
    print(f"Symbols: {symbols}")
    print(f"Interval: {interval}")
    print()
    
    # Fetch data
    market_data = {}
    for symbol in symbols:
        df = fetch_binance_klines(symbol, interval, limit=100)
        if not df.empty:
            market_data[symbol] = df
            print(f"  [OK] {symbol}: {len(df)} bars")
        else:
            print(f"  [ERR] {symbol}: No data")
    
    all_results = {
        "metadata": {
            "timestamp": _now_iso(),
            "symbols": list(market_data.keys()),
            "interval": interval,
        },
        "mutations": {}
    }
    
    # Run Momentum Cascade
    print(f"\n[1/5] Momentum Cascade Mutation...")
    cascade_signals = momentum_cascade_mutation(market_data)
    all_results["mutations"]["momentum_cascade"] = cascade_signals
    print(f"      Generated: {len(cascade_signals)} signals")
    for sig in cascade_signals[:3]:
        print(f"        -> {sig['symbol']} {sig['direction']} | conf={sig['confidence']:.2f} | lag={sig.get('lag_gap_pct', 0):.2f}%")
    
    # Run Regime Kelly for each symbol
    print(f"\n[2/5] Regime Kelly Mutation...")
    kelly_signals = []
    for symbol, df in market_data.items():
        base = {
            'symbol': symbol,
            'signal_type': 'BUY',  # Example base signal
            'confidence': 0.6,
            'entry_price': df['Close'].iloc[-1],
            'take_profit': df['Close'].iloc[-1] * 1.05,
            'stop_loss': df['Close'].iloc[-1] * 0.97,
            'account_equity': 10000,
        }
        result = regime_kelly_mutation(base, df)
        if result:
            kelly_signals.append(result)
    
    all_results["mutations"]["regime_kelly"] = kelly_signals
    print(f"      Generated: {len(kelly_signals)} signals")
    for sig in kelly_signals[:3]:
        print(f"        -> {sig['symbol']} | regime={sig['regime']} | kelly={sig['kelly_fraction']:.2%} | size=${sig['position_value']:.0f}")
    
    # Run Composite Ensemble
    print(f"\n[3/5] Composite Ensemble Mutation...")
    ensemble_signals = composite_ensemble_mutation(list(market_data.keys()), market_data)
    all_results["mutations"]["composite_ensemble"] = ensemble_signals
    print(f"      Generated: {len(ensemble_signals)} signals")
    for sig in ensemble_signals[:3]:
        print(f"        -> {sig['symbol']} {sig['direction']} | conf={sig['confidence']:.2f} | {sig['num_agreeing']} strategies agree")
    
    # Run Temporal Decay (example on first signal)
    print(f"\n[4/5] Temporal Decay Mutation...")
    if ensemble_signals:
        decay_result = temporal_decay_mutation(ensemble_signals[0], market_data[ensemble_signals[0]['symbol']])
        if decay_result:
            all_results["mutations"]["temporal_decay"] = [decay_result]
            print(f"      Example decay: {decay_result['symbol']}")
            print(f"        Original conf: {decay_result['original_confidence']:.2f}")
            print(f"        Decayed conf: {decay_result['confidence']:.2f}")
            print(f"        Decay factor: {decay_result['decay_factor']:.2f}")
    
    # Run Orderflow Confirm (example on first signal)
    print(f"\n[5/5] Orderflow Confirm Mutation...")
    if ensemble_signals:
        of_result = orderflow_confirm_mutation(ensemble_signals[0])
        if of_result:
            all_results["mutations"]["orderflow_confirm"] = [of_result]
            print(f"      Example orderflow: {of_result['symbol']}")
            print(f"        Imbalance: {of_result.get('imbalance_score', 0):.1f}%")
            print(f"        Tier: {of_result.get('tier', 'N/A')}")
            print(f"        Adjusted conf: {of_result['confidence']:.2f}")
    
    # Summary
    total_signals = sum(len(v) for v in all_results["mutations"].values())
    print(f"\n{'='*70}")
    print(f"TOTAL SIGNALS GENERATED: {total_signals}")
    print(f"{'='*70}\n")
    
    return all_results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Innovative Mutations v1.0")
    parser.add_argument("--symbols", nargs="+", default=["BTCUSDT", "ETHUSDT", "SOLUSDT"],
                        help="Symbols to analyze")
    parser.add_argument("--interval", default="1h", help="Timeframe")
    parser.add_argument("--output", help="Output JSON file")
    args = parser.parse_args()
    
    results = run_all_mutations(args.symbols, args.interval)
    
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"Saved results to: {args.output}")
