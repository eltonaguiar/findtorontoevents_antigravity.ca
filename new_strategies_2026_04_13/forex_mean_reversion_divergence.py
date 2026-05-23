"""
STAGED — NOT WIRED INTO LIVE DISPATCH — RED FLAG: see review report
====================================================================
This file lives under `new_strategies_2026_04_13/` and is NOT registered in
any strategy dispatch path. Importing it has zero effect on live picks.

CRITICAL CONTEXT before any promotion: this strategy uses BB(20,2) + RSI(2)
mean reversion with session filter on forex pairs. PR #123 (merged this session)
KILLED `connors_rsi2_forex` — the exact same setup class — for posting
PF 0.68, -20.6% return on 995 trades despite 61.75% WR. The high-WR low-PF
pattern is a documented failure mode.

Before this strategy is promoted to a live registry, REQUIRE:
  1. Head-to-head walk-forward backtest vs. `connors_rsi2_forex` killed-PR data
  2. PF >= 1.5 confirmed on n >= 100 forex trades after costs
  3. Wilson 95% CI lower bound on WR > 50% across at least 2 forex pairs
  4. Verify it doesn't recreate the high-WR-but-negative-economics trap
See `docs/strategy_reviews/2026_04_13_inbound_strategies.md` for the full
integration checklist.

Forex Mean Reversion + Momentum Divergence Strategy
====================================================
Asset Class: FOREX (EURUSD, GBPUSD, USDJPY, AUDUSD, NZDUSD, USDCHF, USDCAD)

PROBLEM: 28.6% WR on only 7 picks — needs massive scale-up and quality.
EDGE:   Forex markets mean-revert intraday but trend inter-day.
        Session-based filtering (London/NY overlap) + Bollinger squeeze
        + RSI divergence captures this edge.

LOGIC:
  LONG:  Price < lower Bollinger(20,2) AND RSI(2) < 10 AND volume spike
         AND London/NY session (liquidity filter)
  SHORT: Price > upper Bollinger(20,2) AND RSI(2) > 90 AND volume spike
         AND London/NY session
  EXIT:  RSI(2) crosses 50 OR ATR trailing stop OR 4-bar time stop

ENTRY FILTERS:
  - ADX(14) < 25 (mean-reversion works in ranging markets only)
  - Session filter: only trade 08:00-17:00 UTC (London+NY overlap)
  - ATR-based position sizing (volatility-scaled)

Target: WR 58-65%, PF > 1.5, picks/day 3-8
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class ForexMeanReversionConfig:
    # Bollinger
    bb_period: int = 20
    bb_std: float = 2.0

    # RSI Connors (ultra-short)
    rsi_period: int = 2
    rsi_oversold: float = 10.0
    rsi_overbought: float = 90.0

    # ATR / risk
    atr_period: int = 14
    atr_stop_mult: float = 1.5
    atr_tp_mult: float = 2.5

    # ADX filter (skip trends)
    adx_period: int = 14
    adx_max: float = 25.0

    # Volume filter
    volume_sma: int = 20
    volume_spike_mult: float = 1.3

    # Time exit
    max_holding_bars: int = 16  # ~4 hours on 15m bars

    symbols: List[str] = field(default_factory=lambda: [
        "EURUSD", "GBPUSD", "USDJPY", "AUDUSD",
        "NZDUSD", "USDCHF", "USDCAD", "EURJPY", "GBPJPY"
    ])


def compute_rsi(prices: pd.Series, period: int = 2) -> pd.Series:
    delta = prices.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1/period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(50)


def compute_atr(high, low, close, period=14):
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()


def compute_adx(high, low, close, period=14):
    """Average Directional Index — filters trending markets."""
    plus_dm = high.diff().clip(lower=0)
    minus_dm = (-low.diff()).clip(lower=0)
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    atr = tr.rolling(window=period).mean()
    plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx = dx.rolling(window=period).mean()
    return adx.fillna(20)


def is_session_valid(index, session_start=8, session_end=17):
    """Check if timestamp is within London+NY overlap (UTC)."""
    if hasattr(index, 'hour'):
        return (index.hour >= session_start) & (index.hour < session_end)
    return pd.Series(True, index=index)


def generate_signals(df: pd.DataFrame, config: ForexMeanReversionConfig) -> pd.DataFrame:
    """
    Generate mean-reversion signals for forex pairs.
    df must have: open, high, low, close, volume (with DatetimeIndex)
    """
    df = df.copy()

    # Compute indicators
    df['rsi2'] = compute_rsi(df['close'], config.rsi_period)
    df['atr'] = compute_atr(df['high'], df['low'], df['close'], config.atr_period)
    df['adx'] = compute_adx(df['high'], df['low'], df['close'], config.adx_period)

    # Bollinger Bands
    sma = df['close'].rolling(window=config.bb_period).mean()
    std = df['close'].rolling(window=config.bb_period).std()
    df['bb_upper'] = sma + config.bb_std * std
    df['bb_lower'] = sma - config.bb_std * std

    # Volume filter
    df['vol_sma'] = df['volume'].rolling(window=config.volume_sma).mean()
    df['vol_spike'] = df['volume'] > df['vol_sma'] * config.volume_spike_mult

    # Session filter
    df['session_ok'] = is_session_valid(df.index)

    # ADX filter (ranging only)
    df['adx_ok'] = df['adx'] < config.adx_max

    # Initialize signal columns
    df['signal'] = 0
    df['stop_loss'] = np.nan
    df['take_profit'] = np.nan
    df['max_hold'] = config.max_holding_bars

    # LONG: price at/below lower BB + RSI2 oversold + vol spike + session + ADX
    long_cond = (
        (df['close'] <= df['bb_lower']) &
        (df['rsi2'] < config.rsi_oversold) &
        df['vol_spike'] &
        df['session_ok'] &
        df['adx_ok']
    )
    df.loc[long_cond, 'signal'] = 1
    df.loc[long_cond, 'stop_loss'] = df['close'] - df['atr'] * config.atr_stop_mult
    df.loc[long_cond, 'take_profit'] = df['close'] + df['atr'] * config.atr_tp_mult

    # SHORT: price at/above upper BB + RSI2 overbought + vol spike + session + ADX
    short_cond = (
        (df['close'] >= df['bb_upper']) &
        (df['rsi2'] > config.rsi_overbought) &
        df['vol_spike'] &
        df['session_ok'] &
        df['adx_ok']
    )
    df.loc[short_cond, 'signal'] = -1
    df.loc[short_cond, 'stop_loss'] = df['close'] + df['atr'] * config.atr_stop_mult
    df.loc[short_cond, 'take_profit'] = df['close'] - df['atr'] * config.atr_tp_mult

    return df[['signal', 'stop_loss', 'take_profit', 'max_hold',
               'rsi2', 'adx', 'bb_upper', 'bb_lower', 'atr']]


def backtest(df: pd.DataFrame, config: ForexMeanReversionConfig = None,
             commission_pips: float = 1.0) -> Dict:
    """
    Simple event-driven backtest.
    Returns performance metrics.
    """
    if config is None:
        config = ForexMeanReversionConfig()

    signals = generate_signals(df, config)
    trades = []
    position = None

    for i in range(1, len(signals)):
        row = signals.iloc[i]
        price = df['close'].iloc[i]

        # Check open position
        if position is not None:
            bars_held = i - position['entry_idx']
            if position['direction'] == 'long':
                if price <= position['sl'] or price >= position['tp'] or bars_held >= config.max_holding_bars:
                    exit_price = min(price, position['sl']) if price <= position['sl'] else \
                                 max(price, position['tp']) if price >= position['tp'] else price
                    pnl = (exit_price - position['entry_price'] - commission_pips * 0.0001)
                    trades.append({**position, 'exit_price': exit_price, 'pnl': pnl, 'bars_held': bars_held})
                    position = None
            else:  # short
                if price >= position['sl'] or price <= position['tp'] or bars_held >= config.max_holding_bars:
                    exit_price = max(price, position['sl']) if price >= position['sl'] else \
                                 min(price, position['tp']) if price <= position['tp'] else price
                    pnl = (position['entry_price'] - exit_price - commission_pips * 0.0001)
                    trades.append({**position, 'exit_price': exit_price, 'pnl': pnl, 'bars_held': bars_held})
                    position = None

        # Enter new position
        if position is None and row['signal'] != 0:
            direction = 'long' if row['signal'] == 1 else 'short'
            position = {
                'direction': direction,
                'entry_price': price,
                'sl': row['stop_loss'],
                'tp': row['take_profit'],
                'entry_idx': i,
                'symbol': df.get('symbol', pd.Series(['UNKNOWN'])).iloc[0] if 'symbol' in df.columns else 'UNKNOWN'
            }

    # Compute metrics
    if not trades:
        return {'total_trades': 0, 'win_rate': 0, 'profit_factor': 0, 'sharpe': 0, 'max_dd': 0}

    pnls = [t['pnl'] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]

    gross_profit = sum(wins) if wins else 0
    gross_loss = abs(sum(losses)) if losses else 1e-10
    profit_factor = gross_profit / gross_loss

    # Equity curve
    equity = np.cumsum(pnls)
    max_dd = 0
    peak = equity[0]
    for val in equity:
        peak = max(peak, val)
        dd = peak - val
        max_dd = max(max_dd, dd)

    sharpe = np.mean(pnls) / (np.std(pnls) + 1e-10) * np.sqrt(252 * 6.5)  # annualize

    return {
        'total_trades': len(trades),
        'win_rate': len(wins) / len(trades) * 100,
        'profit_factor': round(profit_factor, 3),
        'sharpe': round(sharpe, 3),
        'max_dd': round(max_dd, 5),
        'avg_pnl': round(np.mean(pnls), 6),
        'avg_win': round(np.mean(wins), 6) if wins else 0,
        'avg_loss': round(np.mean(losses), 6) if losses else 0,
        'best_trade': round(max(pnls), 6),
        'worst_trade': round(min(pnls), 6),
        'equity_curve': equity.tolist(),
    }


def monte_carlo_test(df: pd.DataFrame, config: ForexMeanReversionConfig = None,
                     n_simulations: int = 1000, confidence: float = 0.95) -> Dict:
    """
    Monte Carlo sign-shuffle test for forex mean-reversion strategy.

    Bug fix on inbound version: the original used np.random.permutation on
    the per-trade PnL array, which preserves both mean and std — every
    simulated Sharpe equals the actual Sharpe and the test is meaningless.
    This version uses sign-shuffle (each trade flips sign with p=0.5),
    which is the proper null hypothesis "the system has no directional
    edge over the same payoff magnitude distribution." Aligns with
    `tools/data_integrity/monte_carlo_baseline.py` (PR #157).
    """
    if config is None:
        config = ForexMeanReversionConfig()

    actual = backtest(df, config)
    if actual['total_trades'] < 10:
        return {'status': 'INSUFFICIENT_TRADES', 'trades': actual['total_trades']}

    pnls = actual.get('equity_curve', [])
    if not pnls:
        return {'status': 'NO_EQUITY'}

    per_trade_pnl = np.diff([0] + pnls)
    magnitudes = np.abs(per_trade_pnl)
    n = len(magnitudes)
    actual_sharpe = actual['sharpe']

    rng = np.random.default_rng(42)
    simulated_sharpes = np.empty(n_simulations, dtype=float)
    for i in range(n_simulations):
        signs = rng.choice([-1.0, 1.0], size=n)
        sim = magnitudes * signs
        std_pnl = sim.std() + 1e-10
        simulated_sharpes[i] = sim.mean() / std_pnl * np.sqrt(252 * 6.5)

    threshold = float(np.percentile(simulated_sharpes, confidence * 100))
    p_value = float(np.mean(simulated_sharpes >= actual_sharpe))

    return {
        'status': 'PASS' if actual_sharpe > threshold else 'FAIL',
        'actual_sharpe': actual_sharpe,
        'threshold_95': round(threshold, 3),
        'p_value': round(p_value, 4),
        'simulated_mean_sharpe': round(float(np.mean(simulated_sharpes)), 3),
        'simulated_std_sharpe': round(float(np.std(simulated_sharpes)), 3),
        'n_simulations': n_simulations,
        'method': 'sign_shuffle_v2',
    }


if __name__ == '__main__':
    print("Forex Mean Reversion + Momentum Divergence Strategy")
    print("=" * 50)
    print("Usage:")
    print("  from forex_mean_reversion_divergence import generate_signals, backtest, monte_carlo_test")
    print("  config = ForexMeanReversionConfig()")
    print("  signals = generate_signals(df, config)")
    print("  results = backtest(df, config)")
    print("  mc = monte_carlo_test(df, config, n_simulations=1000)")
