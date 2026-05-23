"""
ETF Sector Rotation + Relative Strength Strategy
==================================================
Asset Class: ETFs (Sector SPDRs, Bond ETFs, Commodity ETFs)

PROBLEM: ETF picks are too few and generic. Need sector rotation edge.
EDGE:   Relative strength momentum: when one sector outperforms by >5%
        over 63 days, it tends to continue for another 20-30 days (momentum
        persistence). Combining with mean-reversion timing (RSI2 < 10 on
        pullbacks within outperforming sectors) creates a hybrid approach.

LOGIC:
  1. Rank sectors by 63-day relative strength vs SPY
  2. Top 3 sectors = "leaders"
  3. Within leaders, enter on RSI(2) < 10 pullback (buy the dip in leaders)
  4. Exit when sector drops out of top 5 OR RSI(2) > 90 OR 20-bar hold

SECTORS: XLK (Tech), XLF (Financials), XLV (Health), XLE (Energy),
         XLI (Industrials), XLP (Staples), XLY (Discretionary),
         XLU (Utilities), XLRE (Real Estate), XLC (Comm Services),
         XLB (Materials), TLT (Bonds), GLD (Gold), USO (Oil)

Target: WR 60-68%, PF > 1.5, weekly rebalance
"""

import pandas as pd
import numpy as np
from typing import Dict, List
from dataclasses import dataclass, field


@dataclass
class ETFSectorConfig:
    rs_lookback: int = 63
    rsi_period: int = 2
    rsi_oversold: float = 10.0
    rsi_overbought: float = 90.0
    atr_period: int = 14
    atr_stop_mult: float = 2.0
    max_hold: int = 20
    top_n: int = 3  # trade top N sectors by RS

    sectors: List[str] = field(default_factory=lambda: [
        "XLK", "XLF", "XLV", "XLE", "XLI", "XLP", "XLY", "XLU", "XLRE", "XLC", "XLB"
    ])
    benchmark: str = "SPY"


def rsi(prices, period=2):
    d = prices.diff()
    g = d.where(d > 0, 0.0)
    l = (-d).where(d < 0, 0.0)
    ag = g.ewm(alpha=1/period, min_periods=period).mean()
    al = l.ewm(alpha=1/period, min_periods=period).mean()
    return (100 - 100 / (1 + ag / al.replace(0, np.nan))).fillna(50)


def atr(h, l, c, period=14):
    tr = pd.concat([h - l, (h - c.shift(1)).abs(), (l - c.shift(1)).abs()], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def compute_relative_strength(sector_close, benchmark_close, lookback=63):
    """RS = sector return - benchmark return over lookback period."""
    sector_ret = sector_close.pct_change(lookback)
    bench_ret = benchmark_close.pct_change(lookback)
    return (sector_ret - bench_ret) * 100


def generate_signals(sector_dfs: Dict[str, pd.DataFrame],
                     benchmark_df: pd.DataFrame,
                     config: ETFSectorConfig = None) -> Dict[str, pd.DataFrame]:
    """
    Generate rotation signals for multiple sector ETFs.
    sector_dfs: dict of symbol -> DataFrame (OHLCV)
    benchmark_df: SPY DataFrame
    """
    if config is None:
        config = ETFSectorConfig()

    # Compute relative strength for all sectors
    rs_scores = {}
    for sym, df in sector_dfs.items():
        rs = compute_relative_strength(df['close'], benchmark_df['close'], config.rs_lookback)
        rs_scores[sym] = rs

    rs_df = pd.DataFrame(rs_scores)

    # Identify top N sectors at each bar
    results = {}
    for sym, df in sector_dfs.items():
        df = df.copy()
        df['rs'] = rs_scores[sym]
        df['rsi2'] = rsi(df['close'], config.rsi_period)
        df['atr'] = atr(df['high'], df['low'], df['close'], config.atr_period)

        # Is this sector in top N?
        df['rank'] = rs_df.rank(axis=1, ascending=False)[sym]
        df['is_leader'] = df['rank'] <= config.top_n

        df['signal'] = 0
        df['stop_loss'] = np.nan
        df['take_profit'] = np.nan
        df['max_hold'] = config.max_hold

        # LONG: Leader sector + RSI2 oversold pullback
        long_cond = df['is_leader'] & (df['rsi2'] < config.rsi_oversold)
        df.loc[long_cond, 'signal'] = 1
        df.loc[long_cond, 'stop_loss'] = df['close'] - df['atr'] * config.atr_stop_mult
        df.loc[long_cond, 'take_profit'] = df['close'] + df['atr'] * config.atr_stop_mult * 1.5

        results[sym] = df[['signal', 'stop_loss', 'take_profit', 'max_hold', 'rs', 'rank']]

    return results


def backtest_portfolio(sector_dfs: Dict[str, pd.DataFrame],
                       benchmark_df: pd.DataFrame,
                       config: ETFSectorConfig = None,
                       commission_bps: float = 3.0) -> Dict:
    """Backtest the full sector rotation portfolio."""
    if config is None:
        config = ETFSectorConfig()

    all_signals = generate_signals(sector_dfs, benchmark_df, config)
    all_trades = []
    positions = {}  # sym -> position dict

    # Use the benchmark index as timeline
    for i in range(200, len(benchmark_df)):  # start after warmup
        idx = benchmark_df.index[i]

        # Check exits
        for sym in list(positions.keys()):
            pos = positions[sym]
            if sym not in sector_dfs or idx not in sector_dfs[sym].index:
                continue
            price = sector_dfs[sym]['close'].loc[idx]
            bh = i - pos['entry_bar']
            if price <= pos['sl'] or price >= pos['tp'] or bh >= config.max_hold:
                ex = min(price, pos['sl']) if price <= pos['sl'] else max(price, pos['tp']) if price >= pos['tp'] else price
                pnl = (ex - pos['ep']) - commission_bps / 10000 * pos['ep']
                all_trades.append({'symbol': sym, 'pnl': pnl, 'bars_held': bh})
                del positions[sym]

        # Check entries (max 3 concurrent)
        if len(positions) < 3:
            for sym, sig_df in all_signals.items():
                if sym in positions or idx not in sig_df.index:
                    continue
                row = sig_df.loc[idx]
                if row['signal'] == 1:
                    price = sector_dfs[sym]['close'].loc[idx]
                    positions[sym] = {
                        'ep': price,
                        'sl': row['stop_loss'],
                        'tp': row['take_profit'],
                        'entry_bar': i,
                    }
                    if len(positions) >= 3:
                        break

    if not all_trades:
        return {'total_trades': 0, 'win_rate': 0, 'profit_factor': 0}

    pnls = [t['pnl'] for t in all_trades]
    w = [p for p in pnls if p > 0]
    l = [p for p in pnls if p <= 0]
    gp, gl = sum(w) if w else 0, abs(sum(l)) if l else 1e-10
    eq = np.cumsum(pnls)
    mdd, pk = 0, eq[0]
    for v in eq:
        pk = max(pk, v)
        mdd = max(mdd, pk - v)
    sharpe = np.mean(pnls) / (np.std(pnls) + 1e-10) * np.sqrt(252)

    # Per-sector breakdown
    sector_stats = {}
    for t in all_trades:
        s = t['symbol']
        if s not in sector_stats:
            sector_stats[s] = {'trades': 0, 'wins': 0, 'pnl': 0}
        sector_stats[s]['trades'] += 1
        if t['pnl'] > 0:
            sector_stats[s]['wins'] += 1
        sector_stats[s]['pnl'] += t['pnl']

    return {
        'total_trades': len(all_trades),
        'win_rate': round(len(w) / len(all_trades) * 100, 1),
        'profit_factor': round(gp / gl, 3),
        'sharpe': round(sharpe, 3),
        'max_dd': round(mdd, 6),
        'avg_pnl': round(np.mean(pnls), 6),
        'sector_breakdown': {k: {**v, 'wr': round(v['wins']/v['trades']*100, 1)} for k, v in sector_stats.items()},
    }
