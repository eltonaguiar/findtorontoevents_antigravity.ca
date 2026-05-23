"""
STAGED — NOT WIRED INTO LIVE DISPATCH
=====================================
This file lives under `new_strategies_2026_04_13/` and is NOT registered in
any strategy dispatch path (`multi_asset.commodity_futures_strategies.COMMODITY_STRATEGIES`,
`alpha_engine/`, `cross_aggregation/`, etc.). Importing it has zero effect on
live picks. Before promotion to a strategy registry, see
`docs/strategy_reviews/2026_04_13_inbound_strategies.md` for the integration
checklist (signature wrap, seasonal-bias empirical validation, commodity-data
ingest verification, head-to-head backtest vs existing commodity strategies).

Commodity Seasonal + Momentum Breakout Strategy
=================================================
Asset Class: COMMODITIES (CL=F, GC=F, SI=F, NG=F, ZC=F, ZS=F, HG=F, PL=F)

PROBLEM: 43.6% WR, 4 active picks — underperforming significantly.
EDGE:   Commodities have strong seasonal patterns (e.g., NG in winter,
        grains in spring planting, gold in Q1). Combining seasonal bias
        with Donchian channel breakout captures both the seasonal drift
        and the momentum expansion.

LOGIC:
  LONG:  Price > Donchian(55) high AND seasonal_bias > 0 (bullish season)
         AND ADX(14) > 20 (trending) AND RSI(14) > 50
  SHORT: Price < Donchian(55) low AND seasonal_bias < 0 (bearish season)
         AND ADX(14) > 20 AND RSI(14) < 50
  EXIT:  ATR trailing stop (2.0x ATR) OR Donchian(20) opposite channel

SEASONAL BIAS MAP (month-based):
  GC: Jan-May bullish, Jun-Aug bearish, Sep-Dec bullish
  SI: Jan-Apr bullish, May-Jul neutral, Aug-Dec bullish
  CL: Nov-Feb bullish (winter demand), Mar-Apr bearish, May-Aug neutral
  NG: Oct-Mar bullish (heating), Apr-Sep bearish
  ZC: Mar-Jun bullish (planting), Jul-Sep bearish (harvest)
  ZS: Feb-May bullish, Jun-Aug bearish, Sep-Nov neutral

Target: WR 55-62%, PF > 1.5, picks/day 1-4
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass, field


# Seasonal bias by month (-1 to +1)
SEASONAL_BIAS = {
    'GC=F': {1: 0.7, 2: 0.6, 3: 0.4, 4: 0.3, 5: 0.1, 6: -0.3,
             7: -0.4, 8: 0.2, 9: 0.5, 10: 0.6, 11: 0.7, 12: 0.5},
    'SI=F': {1: 0.6, 2: 0.5, 3: 0.4, 4: 0.3, 5: 0.0, 6: -0.1,
             7: 0.0, 8: 0.3, 9: 0.5, 10: 0.5, 11: 0.6, 12: 0.5},
    'CL=F': {1: 0.5, 2: 0.4, 3: -0.2, 4: -0.3, 5: 0.0, 6: 0.1,
             7: 0.2, 8: 0.1, 9: 0.0, 10: -0.1, 11: 0.4, 12: 0.5},
    'NG=F': {1: 0.8, 2: 0.6, 3: 0.2, 4: -0.3, 5: -0.5, 6: -0.6,
             7: -0.5, 8: -0.3, 9: -0.1, 10: 0.3, 11: 0.6, 12: 0.8},
    'ZC=F': {1: 0.0, 2: 0.2, 3: 0.5, 4: 0.7, 5: 0.6, 6: 0.2,
             7: -0.3, 8: -0.5, 9: -0.2, 10: 0.0, 11: 0.1, 12: 0.0},
    'ZS=F': {1: 0.0, 2: 0.3, 3: 0.5, 4: 0.6, 5: 0.4, 6: -0.1,
             7: -0.3, 8: -0.4, 9: 0.0, 10: 0.1, 11: 0.1, 12: 0.0},
    'HG=F': {1: 0.3, 2: 0.4, 3: 0.5, 4: 0.5, 5: 0.3, 6: 0.0,
             7: -0.1, 8: 0.0, 9: 0.2, 10: 0.2, 11: 0.3, 12: 0.3},
    'PL=F': {1: 0.4, 2: 0.3, 3: 0.2, 4: 0.1, 5: 0.0, 6: -0.1,
             7: 0.0, 8: 0.1, 9: 0.2, 10: 0.3, 11: 0.4, 12: 0.4},
}


@dataclass
class CommoditySeasonalConfig:
    # Donchian channels
    donchian_long: int = 55
    donchian_exit: int = 20

    # ADX filter
    adx_period: int = 14
    adx_min: float = 20.0

    # RSI filter
    rsi_period: int = 14
    rsi_min_long: float = 50.0
    rsi_max_short: float = 50.0

    # ATR
    atr_period: int = 14
    atr_stop_mult: float = 2.0

    # Seasonal filter
    seasonal_threshold: float = 0.2  # minimum seasonal bias to trade

    # Time exit
    max_holding_bars: int = 40  # ~10 days on daily bars

    symbols: List[str] = field(default_factory=lambda: [
        'GC=F', 'SI=F', 'CL=F', 'NG=F', 'ZC=F', 'ZS=F', 'HG=F', 'PL=F'
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


def compute_adx(high, low, close, period=14):
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
    return dx.rolling(window=period).mean().fillna(20)


def get_seasonal_bias(symbol: str, month: int) -> float:
    """Get seasonal bias for a given symbol and month."""
    if symbol in SEASONAL_BIAS and month in SEASONAL_BIAS[symbol]:
        return SEASONAL_BIAS[symbol][month]
    return 0.0


def generate_signals(df: pd.DataFrame, symbol: str = 'GC=F',
                     config: CommoditySeasonalConfig = None) -> pd.DataFrame:
    """
    Generate seasonal momentum signals for commodities.
    df must have: open, high, low, close, volume (with DatetimeIndex)
    """
    if config is None:
        config = CommoditySeasonalConfig()

    df = df.copy()

    # Donchian channels
    df['donchian_high'] = df['high'].rolling(window=config.donchian_long).max()
    df['donchian_low'] = df['low'].rolling(window=config.donchian_long).min()
    df['donchian_exit_high'] = df['high'].rolling(window=config.donchian_exit).max()
    df['donchian_exit_low'] = df['low'].rolling(window=config.donchian_exit).min()

    # Indicators
    df['rsi'] = compute_rsi(df['close'], config.rsi_period)
    df['atr'] = compute_atr(df['high'], df['low'], df['close'], config.atr_period)
    df['adx'] = compute_adx(df['high'], df['low'], df['close'], config.adx_period)

    # Seasonal bias
    df['month'] = df.index.month if hasattr(df.index, 'month') else 1
    df['seasonal'] = df['month'].apply(lambda m: get_seasonal_bias(symbol, m))

    # Initialize
    df['signal'] = 0
    df['stop_loss'] = np.nan
    df['take_profit'] = np.nan
    df['max_hold'] = config.max_holding_bars

    # LONG: Donchian breakout + bullish seasonal + trending + RSI confirm
    long_cond = (
        (df['close'] > df['donchian_high'].shift(1)) &
        (df['seasonal'] >= config.seasonal_threshold) &
        (df['adx'] > config.adx_min) &
        (df['rsi'] > config.rsi_min_long)
    )
    df.loc[long_cond, 'signal'] = 1
    df.loc[long_cond, 'stop_loss'] = df['close'] - df['atr'] * config.atr_stop_mult
    df.loc[long_cond, 'take_profit'] = df['donchian_exit_high']

    # SHORT: Donchian breakdown + bearish seasonal + trending + RSI confirm
    short_cond = (
        (df['close'] < df['donchian_low'].shift(1)) &
        (df['seasonal'] <= -config.seasonal_threshold) &
        (df['adx'] > config.adx_min) &
        (df['rsi'] < config.rsi_max_short)
    )
    df.loc[short_cond, 'signal'] = -1
    df.loc[short_cond, 'stop_loss'] = df['close'] + df['atr'] * config.atr_stop_mult
    df.loc[short_cond, 'take_profit'] = df['donchian_exit_low']

    return df[['signal', 'stop_loss', 'take_profit', 'max_hold',
               'rsi', 'adx', 'seasonal', 'atr']]


def backtest(df: pd.DataFrame, symbol: str = 'GC=F',
             config: CommoditySeasonalConfig = None,
             commission_ticks: float = 0.01) -> Dict:
    """Simple event-driven backtest for commodities."""
    if config is None:
        config = CommoditySeasonalConfig()

    signals = generate_signals(df, symbol, config)
    trades = []
    position = None

    for i in range(1, len(signals)):
        row = signals.iloc[i]
        price = df['close'].iloc[i]

        if position is not None:
            bars_held = i - position['entry_idx']
            if position['direction'] == 'long':
                if price <= position['sl'] or bars_held >= config.max_holding_bars:
                    exit_price = min(price, position['sl']) if price <= position['sl'] else price
                    pnl = (exit_price - position['entry_price'] - commission_ticks)
                    trades.append({**position, 'exit_price': exit_price, 'pnl': pnl, 'bars_held': bars_held})
                    position = None
                elif row['signal'] == -1:  # opposite signal
                    pnl = (price - position['entry_price'] - commission_ticks)
                    trades.append({**position, 'exit_price': price, 'pnl': pnl, 'bars_held': bars_held})
                    position = None
            else:
                if price >= position['sl'] or bars_held >= config.max_holding_bars:
                    exit_price = max(price, position['sl']) if price >= position['sl'] else price
                    pnl = (position['entry_price'] - exit_price - commission_ticks)
                    trades.append({**position, 'exit_price': exit_price, 'pnl': pnl, 'bars_held': bars_held})
                    position = None
                elif row['signal'] == 1:
                    pnl = (position['entry_price'] - price - commission_ticks)
                    trades.append({**position, 'exit_price': price, 'pnl': pnl, 'bars_held': bars_held})
                    position = None

        if position is None and row['signal'] != 0:
            direction = 'long' if row['signal'] == 1 else 'short'
            position = {
                'direction': direction,
                'entry_price': price,
                'sl': row['stop_loss'],
                'tp': row['take_profit'],
                'entry_idx': i,
                'symbol': symbol
            }

    if not trades:
        return {'total_trades': 0, 'win_rate': 0, 'profit_factor': 0, 'sharpe': 0, 'max_dd': 0}

    pnls = [t['pnl'] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]

    gross_profit = sum(wins) if wins else 0
    gross_loss = abs(sum(losses)) if losses else 1e-10
    profit_factor = gross_profit / gross_loss

    equity = np.cumsum(pnls)
    max_dd = 0
    peak = equity[0]
    for val in equity:
        peak = max(peak, val)
        dd = peak - val
        max_dd = max(max_dd, dd)

    sharpe = np.mean(pnls) / (np.std(pnls) + 1e-10) * np.sqrt(252)

    return {
        'total_trades': len(trades),
        'win_rate': round(len(wins) / len(trades) * 100, 1),
        'profit_factor': round(profit_factor, 3),
        'sharpe': round(sharpe, 3),
        'max_dd': round(max_dd, 5),
        'avg_pnl': round(np.mean(pnls), 6),
        'equity_curve': equity.tolist(),
    }


def monte_carlo_test(df: pd.DataFrame, symbol: str = 'GC=F',
                     config: CommoditySeasonalConfig = None,
                     n_simulations: int = 1000, confidence: float = 0.95) -> Dict:
    """Monte Carlo sign-shuffle test for commodity seasonal strategy.

    Bug fix on inbound version: the original used np.random.permutation on the
    per-trade PnL array, which preserves both mean and std — every simulated
    Sharpe equals the actual Sharpe and the test is meaningless. This version
    uses sign-shuffle (each trade flips sign with p=0.5), which is the proper
    null hypothesis "the system has no directional edge over the same payoff
    magnitude distribution." Aligns with `tools/data_integrity/monte_carlo_baseline.py`
    (PR #157).
    """
    if config is None:
        config = CommoditySeasonalConfig()

    actual = backtest(df, symbol, config)
    if actual['total_trades'] < 10:
        return {'status': 'INSUFFICIENT_TRADES', 'trades': actual['total_trades']}

    per_trade_pnl = np.diff([0] + actual['equity_curve'])
    magnitudes = np.abs(per_trade_pnl)
    n = len(magnitudes)
    actual_sharpe = actual['sharpe']

    rng = np.random.default_rng(42)
    simulated_sharpes = np.empty(n_simulations, dtype=float)
    for i in range(n_simulations):
        signs = rng.choice([-1.0, 1.0], size=n)
        sim = magnitudes * signs
        std_pnl = sim.std() + 1e-10
        simulated_sharpes[i] = sim.mean() / std_pnl * np.sqrt(252)

    threshold = float(np.percentile(simulated_sharpes, confidence * 100))
    p_value = float(np.mean(simulated_sharpes >= actual_sharpe))

    return {
        'status': 'PASS' if actual_sharpe > threshold else 'FAIL',
        'actual_sharpe': actual_sharpe,
        'threshold_95': round(threshold, 3),
        'p_value': round(p_value, 4),
        'n_simulations': n_simulations,
        'method': 'sign_shuffle_v2',
    }


if __name__ == '__main__':
    print("Commodity Seasonal + Momentum Breakout Strategy")
    print("=" * 50)
    print("Symbols:", list(SEASONAL_BIAS.keys()))
    print("Target: WR 55-62%, PF > 1.5")
