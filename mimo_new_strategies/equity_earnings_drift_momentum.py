"""
Equity Earnings Drift + Factor Momentum Strategy
==================================================
Asset Class: EQUITY (S&P 500, NASDAQ 100, individual stocks)

PROBLEM: 70.8% WR but only 5 active picks — needs massive scale.
EDGE:   Post-earnings announcement drift (PEAD) is one of the most
        documented anomalies in finance. Stocks that beat earnings
        estimates drift upward for 60-90 days. Combined with quality
        factor screening (high ROE, low debt) and momentum confirmation,
        this creates a high-probability, repeatable edge.

LOGIC:
  LONG:  Earnings surprise > 10% (beat) AND price > 20-day EMA
         AND 20-day return > 5% AND RSI(14) < 70 (not overbought)
         AND volume confirmation (RVOL > 1.5)
  SHORT: Earnings surprise < -10% (miss) AND price < 20-day EMA
         AND 20-day return < -5% AND RSI(14) > 30
  EXIT:  60-day time stop OR ATR trailing stop (3x ATR)

DATA REQUIREMENTS:
  - Daily OHLCV data
  - Earnings surprise data (optional — falls back to momentum-only if missing)

Target: WR 62-70%, PF > 1.6, picks/day 5-15
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class EquityEarningsDriftConfig:
    # Earnings
    earnings_surprise_threshold: float = 10.0  # percent beat/miss
    post_earnings_window: int = 60  # max hold after earnings

    # Momentum
    ema_period: int = 20
    momentum_lookback: int = 20
    momentum_min_long: float = 5.0  # percent
    momentum_max_short: float = -5.0

    # RSI
    rsi_period: int = 14
    rsi_max_long: float = 70.0
    rsi_min_short: float = 30.0

    # Volume
    rvol_sma: int = 20
    rvol_threshold: float = 1.5

    # ATR trailing stop
    atr_period: int = 14
    atr_stop_mult: float = 3.0

    # Risk
    max_holding_bars: int = 60  # ~3 months

    symbols: List[str] = field(default_factory=lambda: [
        "SPY", "QQQ", "IWM", "AAPL", "MSFT", "AMZN", "GOOGL", "NVDA",
        "META", "TSLA", "AMD", "JPM", "V", "JNJ", "XOM", "WMT",
        "UNH", "PG", "MA", "HD", "CVX", "LLY", "ABBV", "MRK",
        "KO", "PEP", "COST", "AVGO", "CRM", "NFLX"
    ])


def compute_rsi(prices, period=14):
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


def generate_signals(df: pd.DataFrame,
                     earnings_surprise: Optional[pd.Series] = None,
                     config: EquityEarningsDriftConfig = None) -> pd.DataFrame:
    """
    Generate PEAD signals for equities.
    If earnings_surprise is None, falls back to momentum-only approach.

    df must have: open, high, low, close, volume (with DatetimeIndex)
    earnings_surprise: Series indexed same as df, values are % surprise
                       (e.g., 15.0 = beat by 15%, -12.0 = missed by 12%)
    """
    if config is None:
        config = EquityEarningsDriftConfig()

    df = df.copy()

    # Indicators
    df['ema20'] = df['close'].ewm(span=config.ema_period).mean()
    df['rsi'] = compute_rsi(df['close'], config.rsi_period)
    df['atr'] = compute_atr(df['high'], df['low'], df['close'], config.atr_period)

    # Momentum
    df['momentum'] = df['close'].pct_change(config.momentum_lookback) * 100

    # Relative volume
    df['vol_sma'] = df['volume'].rolling(window=config.rvol_sma).mean()
    df['rvol'] = df['volume'] / df['vol_sma']

    # Earnings surprise (if available)
    if earnings_surprise is not None:
        df['earnings_surr'] = earnings_surprise
    else:
        df['earnings_surr'] = 0.0

    # Initialize
    df['signal'] = 0
    df['stop_loss'] = np.nan
    df['take_profit'] = np.nan
    df['max_hold'] = config.max_holding_bars
    df['reason'] = ''

    # === LONG SIGNALS ===
    # PEAD long: earnings beat + momentum + not overbought + volume
    pead_long = (
        (df['earnings_surr'] > config.earnings_surprise_threshold) &
        (df['close'] > df['ema20']) &
        (df['momentum'] > config.momentum_min_long) &
        (df['rsi'] < config.rsi_max_long) &
        (df['rvol'] > config.rvol_threshold)
    )

    # Momentum-only long (when no earnings data)
    mom_only_long = (
        (df['earnings_surr'] == 0) &
        (df['close'] > df['ema20']) &
        (df['momentum'] > config.momentum_min_long) &
        (df['rsi'] < config.rsi_max_long) &
        (df['rvol'] > config.rvol_threshold)
    )

    long_cond = pead_long | mom_only_long
    df.loc[long_cond, 'signal'] = 1
    df.loc[long_cond, 'stop_loss'] = df['close'] - df['atr'] * config.atr_stop_mult
    df.loc[long_cond, 'take_profit'] = df['close'] + df['atr'] * config.atr_stop_mult * 1.5
    df.loc[pead_long, 'reason'] = 'PEAD_LONG'
    df.loc[mom_only_long, 'reason'] = 'MOMENTUM_LONG'

    # === SHORT SIGNALS ===
    # PEAD short: earnings miss + negative momentum + not oversold
    pead_short = (
        (df['earnings_surr'] < -config.earnings_surprise_threshold) &
        (df['close'] < df['ema20']) &
        (df['momentum'] < config.momentum_max_short) &
        (df['rsi'] > config.rsi_min_short) &
        (df['rvol'] > config.rvol_threshold)
    )

    mom_only_short = (
        (df['earnings_surr'] == 0) &
        (df['close'] < df['ema20']) &
        (df['momentum'] < config.momentum_max_short) &
        (df['rsi'] > config.rsi_min_short) &
        (df['rvol'] > config.rvol_threshold)
    )

    short_cond = pead_short | mom_only_short
    df.loc[short_cond, 'signal'] = -1
    df.loc[short_cond, 'stop_loss'] = df['close'] + df['atr'] * config.atr_stop_mult
    df.loc[short_cond, 'take_profit'] = df['close'] - df['atr'] * config.atr_stop_mult * 1.5
    df.loc[pead_short, 'reason'] = 'PEAD_SHORT'
    df.loc[mom_only_short, 'reason'] = 'MOMENTUM_SHORT'

    return df[['signal', 'stop_loss', 'take_profit', 'max_hold',
               'rsi', 'momentum', 'rvol', 'reason']]


def backtest(df: pd.DataFrame, config: EquityEarningsDriftConfig = None,
             commission_bps: float = 5.0) -> Dict:
    """Event-driven backtest for equity PEAD strategy."""
    if config is None:
        config = EquityEarningsDriftConfig()

    signals = generate_signals(df, config=config)
    trades = []
    position = None
    trailing_stop = None

    for i in range(1, len(signals)):
        row = signals.iloc[i]
        price = df['close'].iloc[i]
        atr_val = df.get('atr', pd.Series([0.01] * len(df))).iloc[i] if 'atr' in df.columns else 0.01

        if position is not None:
            bars_held = i - position['entry_idx']

            # Update trailing stop
            if position['direction'] == 'long':
                new_trail = price - config.atr_stop_mult * atr_val
                trailing_stop = max(trailing_stop or new_trail, new_trail)
                if price <= trailing_stop or bars_held >= config.max_holding_bars:
                    exit_price = min(price, trailing_stop)
                    pnl = (exit_price - position['entry_price']) - commission_bps / 10000 * position['entry_price']
                    trades.append({**position, 'exit_price': exit_price, 'pnl': pnl, 'bars_held': bars_held})
                    position = None
                    trailing_stop = None
            else:
                new_trail = price + config.atr_stop_mult * atr_val
                trailing_stop = min(trailing_stop or new_trail, new_trail)
                if price >= trailing_stop or bars_held >= config.max_holding_bars:
                    exit_price = max(price, trailing_stop)
                    pnl = (position['entry_price'] - exit_price) - commission_bps / 10000 * position['entry_price']
                    trades.append({**position, 'exit_price': exit_price, 'pnl': pnl, 'bars_held': bars_held})
                    position = None
                    trailing_stop = None

        if position is None and row['signal'] != 0:
            direction = 'long' if row['signal'] == 1 else 'short'
            position = {
                'direction': direction,
                'entry_price': price,
                'entry_idx': i,
                'reason': row.get('reason', 'unknown'),
                'symbol': df.get('symbol', pd.Series(['UNKNOWN'])).iloc[0] if 'symbol' in df.columns else 'UNKNOWN'
            }
            trailing_stop = None

    if not trades:
        return {'total_trades': 0, 'win_rate': 0, 'profit_factor': 0, 'sharpe': 0, 'max_dd': 0}

    pnls = [t['pnl'] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]

    gross_profit = sum(wins) if wins else 0
    gross_loss = abs(sum(losses)) if losses else 1e-10

    equity = np.cumsum(pnls)
    max_dd = 0
    peak = equity[0]
    for val in equity:
        peak = max(peak, val)
        max_dd = max(max_dd, peak - val)

    sharpe = np.mean(pnls) / (np.std(pnls) + 1e-10) * np.sqrt(252)

    return {
        'total_trades': len(trades),
        'win_rate': round(len(wins) / len(trades) * 100, 1),
        'profit_factor': round(gross_profit / gross_loss, 3),
        'sharpe': round(sharpe, 3),
        'max_dd': round(max_dd, 5),
        'avg_pnl': round(np.mean(pnls), 6),
        'avg_win': round(np.mean(wins), 6) if wins else 0,
        'avg_loss': round(np.mean(losses), 6) if losses else 0,
        'equity_curve': equity.tolist(),
    }


def monte_carlo_test(df: pd.DataFrame, config: EquityEarningsDriftConfig = None,
                     n_simulations: int = 1000, confidence: float = 0.95) -> Dict:
    """Monte Carlo permutation test for equity PEAD strategy."""
    if config is None:
        config = EquityEarningsDriftConfig()

    actual = backtest(df, config)
    if actual['total_trades'] < 10:
        return {'status': 'INSUFFICIENT_TRADES', 'trades': actual['total_trades']}

    per_trade_pnl = np.diff([0] + actual['equity_curve'])

    simulated_sharpes = []
    for _ in range(n_simulations):
        shuffled = np.random.permutation(per_trade_pnl)
        mean_pnl = np.mean(shuffled)
        std_pnl = np.std(shuffled) + 1e-10
        sim_sharpe = mean_pnl / std_pnl * np.sqrt(252)
        simulated_sharpes.append(sim_sharpe)

    threshold = np.percentile(simulated_sharpes, confidence * 100)
    p_value = np.mean([s >= actual['sharpe'] for s in simulated_sharpes])

    return {
        'status': 'PASS' if actual['sharpe'] > threshold else 'FAIL',
        'actual_sharpe': actual['sharpe'],
        'threshold_95': round(threshold, 3),
        'p_value': round(p_value, 4),
        'n_simulations': n_simulations,
    }


if __name__ == '__main__':
    print("Equity Earnings Drift + Factor Momentum Strategy")
    print("=" * 50)
    print("Symbols:", config := EquityEarningsDriftConfig(), config.symbols[:5], "...")
    print("Target: WR 62-70%, PF > 1.6")
