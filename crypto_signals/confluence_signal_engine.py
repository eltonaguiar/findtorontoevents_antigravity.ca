"""
CONFLUENCE SIGNAL ENGINE — High-Confidence BUY Signals with TP/SL
=================================================================
Philosophy: Don't predict all the time. Only fire when MULTIPLE proven
strategies agree simultaneously. Each signal comes with:
  - Entry price
  - Take Profit (ATR-based + structure)
  - Stop Loss (ATR-based)
  - Confidence score (how many strategies agree)
  - Risk:Reward ratio

Backtested on AVAXUSDT, BTCUSDT, ETHUSDT, BNBUSDT (2020-2025)
"""

import ccxt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import os
import time
from strategies import (
    ema, sma, rsi, atr, bollinger_bands, macd, adx, supertrend,
    ichimoku, obv, stochastic,
    strategy_ema_crossover, strategy_rsi_momentum, strategy_macd_crossover,
    strategy_supertrend, strategy_triple_ema, strategy_adx_ema,
    strategy_ichimoku, strategy_volume_momentum, strategy_mtf_momentum,
    strategy_donchian_breakout, strategy_momentum_rotation,
    strategy_bb_squeeze_breakout
)


# =============================================================================
# DATA FETCHING (reuse from backtest_engine)
# =============================================================================

def fetch_ohlcv(symbol, timeframe='1d', exchange_id='binance', limit=1000):
    exchange_class = getattr(ccxt, exchange_id)
    exchange = exchange_class({'enableRateLimit': True})
    all_data = []
    since = exchange.parse8601('2020-01-01T00:00:00Z')
    print(f"  Fetching {symbol} {timeframe} from {exchange_id}...")
    while True:
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=limit)
            if not ohlcv:
                break
            all_data.extend(ohlcv)
            since = ohlcv[-1][0] + 1
            if len(ohlcv) < limit:
                break
            time.sleep(exchange.rateLimit / 1000)
        except Exception as e:
            print(f"  Warning: {e}")
            break
    if not all_data:
        return None
    df = pd.DataFrame(all_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    df = df[~df.index.duplicated(keep='first')]
    df.sort_index(inplace=True)
    print(f"  Got {len(df)} candles from {df.index[0].date()} to {df.index[-1].date()}")
    return df


def load_or_fetch(symbol, timeframe='1d', exchange_id='binance', cache_dir='data_cache'):
    os.makedirs(cache_dir, exist_ok=True)
    safe = symbol.replace('/', '_')
    cache_file = os.path.join(cache_dir, f"{safe}_{timeframe}_{exchange_id}.csv")
    if os.path.exists(cache_file):
        mtime = os.path.getmtime(cache_file)
        if time.time() - mtime < 43200:
            df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
            print(f"  Loaded {symbol} {timeframe} from cache ({len(df)} candles)")
            return df
    df = fetch_ohlcv(symbol, timeframe, exchange_id)
    if df is not None:
        df.to_csv(cache_file)
    return df


# =============================================================================
# CONFLUENCE SIGNAL GENERATOR
# =============================================================================

# The strategies that SURVIVED our backtests with positive Sharpe on crypto
CONFLUENCE_STRATEGIES = {
    'RSI_Momentum': {
        'fn': strategy_rsi_momentum,
        'weight': 2.0,       # Highest weight — best Sharpe on BTC
        'category': 'momentum'
    },
    'MTF_Momentum': {
        'fn': strategy_mtf_momentum,
        'weight': 2.0,       # Best overall on AVAX
        'category': 'momentum'
    },
    'Donchian_Breakout': {
        'fn': strategy_donchian_breakout,
        'weight': 1.5,       # Best category avg Sharpe
        'category': 'breakout'
    },
    'EMA_Cross': {
        'fn': strategy_ema_crossover,
        'weight': 1.0,
        'category': 'trend'
    },
    'Supertrend': {
        'fn': strategy_supertrend,
        'weight': 1.5,
        'category': 'trend'
    },
    'Triple_EMA': {
        'fn': strategy_triple_ema,
        'weight': 1.0,
        'category': 'trend'
    },
    'MACD_Cross': {
        'fn': strategy_macd_crossover,
        'weight': 1.0,
        'category': 'trend'
    },
    'ADX_EMA': {
        'fn': strategy_adx_ema,
        'weight': 1.5,       # Good filter — only trades strong trends
        'category': 'strength'
    },
    'Ichimoku': {
        'fn': strategy_ichimoku,
        'weight': 1.0,
        'category': 'trend'
    },
    'Volume_Momentum': {
        'fn': strategy_volume_momentum,
        'weight': 1.0,
        'category': 'volume'
    },
    'Momentum_Rotation': {
        'fn': strategy_momentum_rotation,
        'weight': 1.5,       # Good on BTC
        'category': 'momentum'
    },
    'BB_Squeeze': {
        'fn': strategy_bb_squeeze_breakout,
        'weight': 1.0,
        'category': 'volatility'
    },
}

# Maximum possible weighted score
MAX_SCORE = sum(s['weight'] for s in CONFLUENCE_STRATEGIES.values())


def compute_regime(df, lookback=60):
    """Detect market regime: bull, bear, sideways."""
    ret = df['close'].pct_change(lookback).fillna(0)
    vol = df['close'].pct_change().rolling(lookback).std().fillna(0) * np.sqrt(365)
    regime = pd.Series('sideways', index=df.index)
    regime[ret > 0.15] = 'bull'
    regime[ret < -0.15] = 'bear'
    return regime


def compute_support_resistance(df, lookback=50):
    """Find recent support and resistance levels."""
    support = df['low'].rolling(lookback).min()
    resistance = df['high'].rolling(lookback).max()
    return support, resistance


def generate_confluence_signals(df, min_score_pct=0.45, min_strategies=3):
    """
    Generate high-confidence BUY signals with TP/SL.
    
    A signal fires when:
    1. Weighted score >= min_score_pct of max possible score
    2. At least min_strategies individual strategies agree (BUY)
    3. Signal was NOT active on the previous bar (new entry only)
    
    TP/SL calculated using:
    - ATR(14) for dynamic volatility-based levels
    - Recent support for SL floor
    - Risk:Reward minimum 1.5:1
    """
    # Run all strategies
    strategy_signals = {}
    for name, info in CONFLUENCE_STRATEGIES.items():
        try:
            sig = info['fn'](df)
            strategy_signals[name] = sig
        except Exception as e:
            print(f"  Warning: {name} failed: {e}")
            strategy_signals[name] = pd.Series(0, index=df.index)
    
    # Compute weighted confluence score
    score = pd.Series(0.0, index=df.index)
    n_agree = pd.Series(0, index=df.index)
    agreeing_strategies = pd.Series('', index=df.index, dtype=str)
    
    for name, info in CONFLUENCE_STRATEGIES.items():
        sig = strategy_signals[name]
        is_long = (sig == 1).astype(float)
        score += is_long * info['weight']
        n_agree += is_long.astype(int)
        # Track which strategies agree
        for idx in df.index[is_long == 1]:
            if agreeing_strategies[idx]:
                agreeing_strategies[idx] += f",{name}"
            else:
                agreeing_strategies[idx] = name
    
    score_pct = score / MAX_SCORE
    
    # ATR for TP/SL
    atr_val = atr(df['high'], df['low'], df['close'], period=14)
    atr_20 = atr(df['high'], df['low'], df['close'], period=20)
    
    # Support/Resistance
    support, resistance = compute_support_resistance(df, lookback=50)
    
    # Regime
    regime = compute_regime(df)
    
    # RSI for overbought filter
    rsi_val = rsi(df['close'], 14)
    
    # Generate signals
    signals = []
    
    # Track if we're already in a position to avoid duplicate signals
    in_position = False
    last_signal_idx = None
    cooldown_bars = 5  # Minimum bars between signals
    
    for i in range(50, len(df)):  # Start after warmup
        idx = df.index[i]
        
        # Check cooldown
        if last_signal_idx is not None:
            bars_since = i - last_signal_idx
            if bars_since < cooldown_bars:
                continue
        
        # Core confluence check
        if score_pct.iloc[i] < min_score_pct:
            continue
        if n_agree.iloc[i] < min_strategies:
            continue
        
        # Must be a NEW signal (not just continuation)
        if i > 0 and score_pct.iloc[i-1] >= min_score_pct and n_agree.iloc[i-1] >= min_strategies:
            # Already signaled — skip unless score increased significantly
            if score_pct.iloc[i] <= score_pct.iloc[i-1] * 1.1:
                continue
        
        # Overbought filter: don't buy when RSI(14) > 80
        if pd.notna(rsi_val.iloc[i]) and rsi_val.iloc[i] > 80:
            continue
        
        entry_price = df['close'].iloc[i]
        current_atr = atr_val.iloc[i]
        current_atr_20 = atr_20.iloc[i]
        
        if pd.isna(current_atr) or current_atr <= 0:
            continue
        
        # === STOP LOSS ===
        # Base: 2x ATR below entry
        sl_atr = entry_price - 2.0 * current_atr
        # Floor: recent support (don't set SL above support)
        sl_support = support.iloc[i] * 0.995  # Slightly below support
        # Use the tighter of the two (but not too tight)
        sl_price = max(sl_atr, sl_support)
        # Ensure SL is at least 0.5% below entry
        sl_price = min(sl_price, entry_price * 0.995)
        # Ensure SL is not more than 8% below entry (cap risk)
        sl_price = max(sl_price, entry_price * 0.92)
        
        sl_pct = (entry_price - sl_price) / entry_price * 100
        
        # === TAKE PROFIT ===
        # Adaptive based on confidence and regime
        current_regime = regime.iloc[i]
        conf_score = score_pct.iloc[i]
        
        if current_regime == 'bull':
            tp_mult = 4.0  # Let winners run in bull
        elif current_regime == 'bear':
            tp_mult = 2.0  # Quick profits in bear
        else:
            tp_mult = 3.0  # Standard
        
        # Scale TP by confidence
        tp_mult *= (0.8 + 0.4 * conf_score)  # Higher confidence = wider TP
        
        tp_price = entry_price + tp_mult * current_atr
        # Also consider resistance as a TP target
        tp_resistance = resistance.iloc[i] * 0.995
        # Use the closer target (more realistic)
        if tp_resistance > entry_price * 1.005:
            tp_price = min(tp_price, tp_resistance)
        # Ensure TP is at least 1% above entry
        tp_price = max(tp_price, entry_price * 1.01)
        
        tp_pct = (tp_price - entry_price) / entry_price * 100
        
        # Risk:Reward ratio
        risk = entry_price - sl_price
        reward = tp_price - entry_price
        rr_ratio = reward / risk if risk > 0 else 0
        
        # Skip if R:R is below 1.5
        if rr_ratio < 1.5:
            continue
        
        # Confidence level
        n_strats = n_agree.iloc[i]
        if conf_score >= 0.70 and n_strats >= 6:
            confidence = 'VERY_HIGH'
        elif conf_score >= 0.55 and n_strats >= 5:
            confidence = 'HIGH'
        elif conf_score >= 0.45 and n_strats >= 4:
            confidence = 'MEDIUM_HIGH'
        else:
            confidence = 'MEDIUM'
        
        signal = {
            'date': idx.strftime('%Y-%m-%d') if hasattr(idx, 'strftime') else str(idx),
            'entry_price': round(entry_price, 4),
            'take_profit': round(tp_price, 4),
            'stop_loss': round(sl_price, 4),
            'tp_pct': round(tp_pct, 2),
            'sl_pct': round(sl_pct, 2),
            'rr_ratio': round(rr_ratio, 2),
            'confidence': confidence,
            'confluence_score': round(conf_score * 100, 1),
            'n_strategies': int(n_strats),
            'strategies_agreeing': agreeing_strategies.iloc[i],
            'regime': current_regime,
            'rsi_14': round(rsi_val.iloc[i], 1) if pd.notna(rsi_val.iloc[i]) else None,
            'atr_14': round(current_atr, 4),
        }
        
        signals.append(signal)
        last_signal_idx = i
    
    return signals, strategy_signals, score_pct


# =============================================================================
# SIGNAL OUTCOME TRACKER — Did the signal hit TP or SL?
# =============================================================================

def evaluate_signals(signals, df, max_hold_days=30):
    """
    For each signal, track forward price action to determine:
    - Did it hit TP first? (WIN)
    - Did it hit SL first? (LOSS)
    - Did it expire without hitting either? (EXPIRED)
    - What was the max favorable excursion (MFE)?
    - What was the max adverse excursion (MAE)?
    """
    results = []
    
    for sig in signals:
        date = pd.Timestamp(sig['date'])
        if date not in df.index:
            # Find nearest date
            mask = df.index >= date
            if not mask.any():
                continue
            start_idx = df.index.get_loc(df.index[mask][0])
        else:
            start_idx = df.index.get_loc(date)
        
        entry = sig['entry_price']
        tp = sig['take_profit']
        sl = sig['stop_loss']
        
        # Track forward
        end_idx = min(start_idx + max_hold_days, len(df))
        
        outcome = 'EXPIRED'
        exit_price = None
        exit_date = None
        bars_held = 0
        max_price = entry
        min_price = entry
        
        for j in range(start_idx + 1, end_idx):
            high = df['high'].iloc[j]
            low = df['low'].iloc[j]
            close = df['close'].iloc[j]
            bars_held = j - start_idx
            
            max_price = max(max_price, high)
            min_price = min(min_price, low)
            
            # Check SL hit first (conservative — assume worst case intrabar)
            if low <= sl:
                outcome = 'SL_HIT'
                exit_price = sl
                exit_date = df.index[j].strftime('%Y-%m-%d')
                break
            
            # Check TP hit
            if high >= tp:
                outcome = 'TP_HIT'
                exit_price = tp
                exit_date = df.index[j].strftime('%Y-%m-%d')
                break
        
        if outcome == 'EXPIRED':
            # Close at last available price
            exit_idx = min(end_idx - 1, len(df) - 1)
            exit_price = df['close'].iloc[exit_idx]
            exit_date = df.index[exit_idx].strftime('%Y-%m-%d')
            bars_held = exit_idx - start_idx
        
        pnl_pct = (exit_price - entry) / entry * 100
        mfe_pct = (max_price - entry) / entry * 100  # Max favorable
        mae_pct = (min_price - entry) / entry * 100  # Max adverse (negative)
        
        result = {
            **sig,
            'outcome': outcome,
            'exit_price': round(exit_price, 4),
            'exit_date': exit_date,
            'pnl_pct': round(pnl_pct, 2),
            'bars_held': bars_held,
            'mfe_pct': round(mfe_pct, 2),
            'mae_pct': round(mae_pct, 2),
        }
        results.append(result)
    
    return results


# =============================================================================
# PERFORMANCE ANALYTICS
# =============================================================================

def analyze_performance(results, symbol):
    """Compute comprehensive performance metrics for a symbol's signals."""
    if not results:
        return None
    
    df = pd.DataFrame(results)
    
    total = len(df)
    tp_hits = len(df[df['outcome'] == 'TP_HIT'])
    sl_hits = len(df[df['outcome'] == 'SL_HIT'])
    expired = len(df[df['outcome'] == 'EXPIRED'])
    
    win_rate = tp_hits / total * 100 if total > 0 else 0
    
    # PnL
    avg_pnl = df['pnl_pct'].mean()
    median_pnl = df['pnl_pct'].median()
    total_pnl = df['pnl_pct'].sum()
    
    # Winners vs losers
    winners = df[df['pnl_pct'] > 0]
    losers = df[df['pnl_pct'] <= 0]
    avg_win = winners['pnl_pct'].mean() if len(winners) > 0 else 0
    avg_loss = losers['pnl_pct'].mean() if len(losers) > 0 else 0
    
    # Profit factor
    gross_profit = winners['pnl_pct'].sum() if len(winners) > 0 else 0
    gross_loss = abs(losers['pnl_pct'].sum()) if len(losers) > 0 else 0.001
    profit_factor = gross_profit / gross_loss
    
    # Expectancy per trade
    expectancy = avg_pnl
    
    # By confidence level
    conf_stats = {}
    for conf in ['VERY_HIGH', 'HIGH', 'MEDIUM_HIGH', 'MEDIUM']:
        subset = df[df['confidence'] == conf]
        if len(subset) > 0:
            conf_tp = len(subset[subset['outcome'] == 'TP_HIT'])
            conf_stats[conf] = {
                'count': len(subset),
                'win_rate': round(conf_tp / len(subset) * 100, 1),
                'avg_pnl': round(subset['pnl_pct'].mean(), 2),
                'avg_rr': round(subset['rr_ratio'].mean(), 2),
            }
    
    # By regime
    regime_stats = {}
    for reg in ['bull', 'bear', 'sideways']:
        subset = df[df['regime'] == reg]
        if len(subset) > 0:
            reg_tp = len(subset[subset['outcome'] == 'TP_HIT'])
            regime_stats[reg] = {
                'count': len(subset),
                'win_rate': round(reg_tp / len(subset) * 100, 1),
                'avg_pnl': round(subset['pnl_pct'].mean(), 2),
            }
    
    # Monthly breakdown
    df['month'] = pd.to_datetime(df['date']).dt.to_period('M')
    monthly = df.groupby('month').agg(
        signals=('pnl_pct', 'count'),
        avg_pnl=('pnl_pct', 'mean'),
        total_pnl=('pnl_pct', 'sum'),
        win_rate=('outcome', lambda x: (x == 'TP_HIT').sum() / len(x) * 100)
    ).round(2)
    
    # Consecutive wins/losses
    outcomes = df['outcome'].values
    max_consec_wins = 0
    max_consec_losses = 0
    curr_wins = 0
    curr_losses = 0
    for o in outcomes:
        if o == 'TP_HIT':
            curr_wins += 1
            curr_losses = 0
            max_consec_wins = max(max_consec_wins, curr_wins)
        elif o == 'SL_HIT':
            curr_losses += 1
            curr_wins = 0
            max_consec_losses = max(max_consec_losses, curr_losses)
        else:
            curr_wins = 0
            curr_losses = 0
    
    # Equity curve (compounding)
    equity = [10000]  # Start with $10,000
    for pnl in df['pnl_pct'].values:
        equity.append(equity[-1] * (1 + pnl / 100))
    
    peak = pd.Series(equity).cummax()
    dd = (pd.Series(equity) - peak) / peak
    max_dd = dd.min() * 100
    
    return {
        'symbol': symbol,
        'total_signals': total,
        'tp_hits': tp_hits,
        'sl_hits': sl_hits,
        'expired': expired,
        'win_rate': round(win_rate, 1),
        'avg_pnl_per_trade': round(avg_pnl, 2),
        'median_pnl': round(median_pnl, 2),
        'total_pnl_pct': round(total_pnl, 2),
        'avg_win': round(avg_win, 2),
        'avg_loss': round(avg_loss, 2),
        'profit_factor': round(profit_factor, 2),
        'expectancy': round(expectancy, 2),
        'max_consecutive_wins': max_consec_wins,
        'max_consecutive_losses': max_consec_losses,
        'max_drawdown_pct': round(max_dd, 2),
        'final_equity': round(equity[-1], 2),
        'total_return_pct': round((equity[-1] / 10000 - 1) * 100, 2),
        'confidence_breakdown': conf_stats,
        'regime_breakdown': regime_stats,
        'avg_bars_held': round(df['bars_held'].mean(), 1),
        'avg_rr_ratio': round(df['rr_ratio'].mean(), 2),
    }


# =============================================================================
# REPORT GENERATOR
# =============================================================================

def generate_signal_report(all_perf, all_results, all_signals):
    """Generate comprehensive markdown report."""
    lines = []
    lines.append("# CONFLUENCE SIGNAL ENGINE — BACKTEST RESULTS")
    lines.append(f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**Engine:** Multi-strategy confluence with ATR-based TP/SL")
    lines.append(f"**Data:** Binance daily candles, Jan 2020 — present")
    lines.append(f"**Strategies in confluence:** {len(CONFLUENCE_STRATEGIES)}")
    lines.append(f"**Min confluence:** 45% weighted score + 3 strategies agreeing")
    lines.append(f"**Min R:R ratio:** 1.5:1")
    lines.append(f"**Max hold:** 30 days per signal")
    lines.append(f"**Cooldown:** 5 bars between signals")
    
    lines.append("\n---\n## EXECUTIVE SUMMARY\n")
    
    # Summary table
    lines.append("| Pair | Signals | Win Rate | Avg PnL | Total PnL | Profit Factor | Max DD | Final Equity ($10k start) |")
    lines.append("|------|---------|----------|---------|-----------|---------------|--------|--------------------------|")
    for perf in all_perf:
        if perf:
            lines.append(f"| {perf['symbol']} | {perf['total_signals']} | "
                        f"{perf['win_rate']}% | {perf['avg_pnl_per_trade']}% | "
                        f"{perf['total_pnl_pct']}% | {perf['profit_factor']} | "
                        f"{perf['max_drawdown_pct']}% | ${perf['final_equity']:,.0f} |")
    
    # Per-symbol detail
    for perf in all_perf:
        if not perf:
            continue
        sym = perf['symbol']
        lines.append(f"\n---\n## {sym}\n")
        lines.append(f"- **Total Signals:** {perf['total_signals']}")
        lines.append(f"- **TP Hits:** {perf['tp_hits']} | **SL Hits:** {perf['sl_hits']} | **Expired:** {perf['expired']}")
        lines.append(f"- **Win Rate:** {perf['win_rate']}%")
        lines.append(f"- **Avg PnL per Trade:** {perf['avg_pnl_per_trade']}%")
        lines.append(f"- **Avg Win:** +{perf['avg_win']}% | **Avg Loss:** {perf['avg_loss']}%")
        lines.append(f"- **Profit Factor:** {perf['profit_factor']}")
        lines.append(f"- **Max Drawdown:** {perf['max_drawdown_pct']}%")
        lines.append(f"- **Final Equity ($10k):** ${perf['final_equity']:,.0f}")
        lines.append(f"- **Total Return:** {perf['total_return_pct']}%")
        lines.append(f"- **Avg R:R Ratio:** {perf['avg_rr_ratio']}")
        lines.append(f"- **Avg Bars Held:** {perf['avg_bars_held']} days")
        lines.append(f"- **Max Consecutive Wins:** {perf['max_consecutive_wins']}")
        lines.append(f"- **Max Consecutive Losses:** {perf['max_consecutive_losses']}")
        
        # Confidence breakdown
        if perf['confidence_breakdown']:
            lines.append(f"\n### {sym} — Performance by Confidence Level\n")
            lines.append("| Confidence | Signals | Win Rate | Avg PnL | Avg R:R |")
            lines.append("|------------|---------|----------|---------|---------|")
            for conf, stats in perf['confidence_breakdown'].items():
                lines.append(f"| {conf} | {stats['count']} | {stats['win_rate']}% | "
                            f"{stats['avg_pnl']}% | {stats['avg_rr']} |")
        
        # Regime breakdown
        if perf['regime_breakdown']:
            lines.append(f"\n### {sym} — Performance by Market Regime\n")
            lines.append("| Regime | Signals | Win Rate | Avg PnL |")
            lines.append("|--------|---------|----------|---------|")
            for reg, stats in perf['regime_breakdown'].items():
                lines.append(f"| {reg} | {stats['count']} | {stats['win_rate']}% | {stats['avg_pnl']}% |")
    
    # Signal-by-signal log (last 20 per symbol)
    lines.append("\n---\n## RECENT SIGNAL LOG (Last 20 per pair)\n")
    for sym, results in all_results.items():
        lines.append(f"\n### {sym}\n")
        lines.append("| Date | Entry | TP | SL | R:R | Conf | #Strats | Outcome | PnL | Bars |")
        lines.append("|------|-------|----|----|-----|------|---------|---------|-----|------|")
        for r in results[-20:]:
            outcome_emoji = "W" if r['outcome'] == 'TP_HIT' else ("L" if r['outcome'] == 'SL_HIT' else "E")
            lines.append(f"| {r['date']} | {r['entry_price']} | {r['take_profit']} | "
                        f"{r['stop_loss']} | {r['rr_ratio']} | {r['confidence']} | "
                        f"{r['n_strategies']} | {outcome_emoji} | {r['pnl_pct']}% | {r['bars_held']}d |")
    
    # Methodology
    lines.append("\n---\n## METHODOLOGY\n")
    lines.append("### How the Confluence Engine Works\n")
    lines.append("1. **12 proven strategies** run independently on each bar")
    lines.append("2. Each strategy has a **weight** based on backtest performance (momentum/breakout weighted higher)")
    lines.append("3. A **BUY signal fires** when:")
    lines.append("   - Weighted confluence score >= 45% of maximum possible")
    lines.append("   - At least 3 individual strategies agree")
    lines.append("   - RSI(14) < 80 (not overbought)")
    lines.append("   - 5-bar cooldown since last signal")
    lines.append("   - Risk:Reward >= 1.5:1")
    lines.append("4. **Stop Loss** = max(2x ATR below entry, recent support - 0.5%)")
    lines.append("   - Capped at 8% max risk per trade")
    lines.append("5. **Take Profit** = ATR-based, regime-adjusted:")
    lines.append("   - Bull: 4x ATR | Sideways: 3x ATR | Bear: 2x ATR")
    lines.append("   - Scaled by confidence score")
    lines.append("   - Capped at nearest resistance")
    lines.append("6. **Max hold:** 30 days — if neither TP nor SL hit, close at market")
    
    lines.append("\n### Strategies in the Confluence\n")
    for name, info in CONFLUENCE_STRATEGIES.items():
        lines.append(f"- **{name}** (weight: {info['weight']}, category: {info['category']})")
    
    lines.append("\n### Honest Limitations\n")
    lines.append("- Daily timeframe only — misses intraday moves")
    lines.append("- No commission modeled on TP/SL exits (would reduce PnL by ~0.1-0.2% per trade)")
    lines.append("- SL assumes execution at exact SL price (slippage could worsen losses)")
    lines.append("- Backtested on historical data — future regimes may differ")
    lines.append("- Confluence signals are INFREQUENT by design — patience required")
    lines.append("- Max drawdown can still be significant during extended bear markets")
    
    return "\n".join(lines)


# =============================================================================
# MAIN
# =============================================================================

def main():
    print("=" * 70)
    print("  CONFLUENCE SIGNAL ENGINE — High-Confidence BUY Signals")
    print("  12 Strategies × 4 Pairs | TP/SL on every signal")
    print("=" * 70)
    
    pairs = ['BTC/USDT', 'ETH/USDT', 'AVAX/USDT', 'BNB/USDT']
    
    all_perf = []
    all_results = {}
    all_signals = {}
    
    for symbol in pairs:
        print(f"\n{'='*50}")
        print(f"  Processing {symbol}")
        print(f"{'='*50}")
        
        df = load_or_fetch(symbol, '1d', 'binance')
        if df is None or len(df) < 200:
            print(f"  Skipping {symbol} — insufficient data")
            continue
        
        # Generate signals
        print(f"  Generating confluence signals...")
        signals, strat_signals, score_pct = generate_confluence_signals(df)
        print(f"  Generated {len(signals)} raw signals")
        
        # Evaluate outcomes
        print(f"  Evaluating signal outcomes (forward-testing)...")
        results = evaluate_signals(signals, df, max_hold_days=30)
        print(f"  Evaluated {len(results)} signals")
        
        # Analyze performance
        perf = analyze_performance(results, symbol)
        if perf:
            all_perf.append(perf)
            all_results[symbol] = results
            all_signals[symbol] = signals
            
            print(f"\n  === {symbol} RESULTS ===")
            print(f"  Signals: {perf['total_signals']} | Win Rate: {perf['win_rate']}%")
            print(f"  Avg PnL: {perf['avg_pnl_per_trade']}% | PF: {perf['profit_factor']}")
            print(f"  TP Hits: {perf['tp_hits']} | SL Hits: {perf['sl_hits']} | Expired: {perf['expired']}")
            print(f"  $10k → ${perf['final_equity']:,.0f} ({perf['total_return_pct']}%)")
            
            if perf['confidence_breakdown']:
                print(f"  --- By Confidence ---")
                for conf, stats in perf['confidence_breakdown'].items():
                    print(f"    {conf}: {stats['count']} signals, {stats['win_rate']}% WR, {stats['avg_pnl']}% avg")
    
    if not all_perf:
        print("\nNo results generated. Check data availability.")
        return
    
    # Generate report
    print(f"\n{'='*70}")
    print("  GENERATING REPORT")
    print(f"{'='*70}")
    
    report = generate_signal_report(all_perf, all_results, all_signals)
    
    output_dir = os.path.dirname(os.path.abspath(__file__))
    
    report_path = os.path.join(output_dir, 'CONFLUENCE_SIGNAL_REPORT.md')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"  Report saved: {report_path}")
    
    # Save all signal data as JSON
    json_path = os.path.join(output_dir, 'confluence_signals.json')
    output = {
        'performance': all_perf,
        'signals': {sym: results for sym, results in all_results.items()},
        'generated': datetime.now().isoformat(),
        'engine_config': {
            'min_score_pct': 0.45,
            'min_strategies': 3,
            'min_rr_ratio': 1.5,
            'max_hold_days': 30,
            'cooldown_bars': 5,
            'sl_method': '2x ATR or support, capped at 8%',
            'tp_method': 'ATR-based regime-adjusted, capped at resistance',
        }
    }
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, default=str)
    print(f"  Signal data saved: {json_path}")
    
    # Print final summary
    print(f"\n{'='*70}")
    print("  FINAL SUMMARY")
    print(f"{'='*70}")
    print(f"\n  {'Pair':<14} {'Signals':>8} {'WinRate':>8} {'AvgPnL':>8} {'TotalPnL':>10} {'PF':>6} {'MaxDD':>8} {'$10k→':>10}")
    print(f"  {'-'*14} {'-'*8} {'-'*8} {'-'*8} {'-'*10} {'-'*6} {'-'*8} {'-'*10}")
    for p in all_perf:
        print(f"  {p['symbol']:<14} {p['total_signals']:>8} {p['win_rate']:>7.1f}% "
              f"{p['avg_pnl_per_trade']:>7.2f}% {p['total_pnl_pct']:>9.1f}% "
              f"{p['profit_factor']:>6.2f} {p['max_drawdown_pct']:>7.1f}% "
              f"${p['final_equity']:>9,.0f}")
    
    print(f"\n  DONE! Check CONFLUENCE_SIGNAL_REPORT.md for full analysis.")


if __name__ == '__main__':
    main()
