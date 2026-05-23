"""
SSK_Claude v0.05 vs v0.06 A/B Backtester
=========================================
Replicates the 7-indicator regime-adaptive consensus logic from the Pine Script.
Downloads 1H Binance data (3 years), runs both parameter sets, compares statistically.

Proposed v0.06 changes to test:
  A) Reclassify tiers: POL→MHIGH, INJ/ARB/APE→EXTR, BNB/LTC→MHIGH
  B) Raise minSigLvl to 4 for EXTR tier (reduce false signals)
  C) Add MR distance filter (RSI/WT only fire within 5% of EMA50)
  D) Tighten EXTR volAdj from 1.7 to 1.4
  E) Add trend bias filter (counter-trend buys in downtrend need +1 extra score)
"""

import pandas as pd
import numpy as np
import requests
import json
import time
import sys
from datetime import datetime, timedelta

# ══════════════════════════════════════════════════════════════════════════════
# DATA DOWNLOAD
# ══════════════════════════════════════════════════════════════════════════════

def download_binance_klines(symbol, interval='1h', days=1095):
    """Download OHLCV from Binance public API (no key needed)."""
    url = 'https://api.binance.com/api/v3/klines'
    end_ms = int(time.time() * 1000)
    start_ms = end_ms - (days * 24 * 3600 * 1000)
    all_data = []
    chunk_ms = 1000 * 3600 * 1000  # 1000 hourly bars

    while start_ms < end_ms:
        params = {
            'symbol': symbol, 'interval': interval,
            'startTime': start_ms, 'endTime': min(start_ms + chunk_ms, end_ms),
            'limit': 1000
        }
        try:
            r = requests.get(url, params=params, timeout=15)
            data = r.json()
            if not isinstance(data, list) or len(data) == 0:
                break
            all_data.extend(data)
            start_ms = data[-1][0] + 1
            time.sleep(0.15)  # rate limit
        except Exception as e:
            print(f"  Error downloading {symbol}: {e}")
            break

    if not all_data:
        return None

    df = pd.DataFrame(all_data, columns=[
        'time','open','high','low','close','volume',
        'close_time','quote_vol','trades','taker_buy_vol','taker_buy_quote','ignore'
    ])
    for c in ['open','high','low','close','volume']:
        df[c] = df[c].astype(float)
    df['time'] = pd.to_datetime(df['time'], unit='ms')
    df = df.set_index('time')
    return df[['open','high','low','close','volume']]

# ══════════════════════════════════════════════════════════════════════════════
# INDICATOR CALCULATIONS
# ══════════════════════════════════════════════════════════════════════════════

def calc_rsi(close, period=14):
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1/period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def calc_ema(close, period):
    return close.ewm(span=period, adjust=False).mean()

def calc_sma(close, period):
    return close.rolling(period).mean()

def calc_macd(close, fast=12, slow=26, signal=9):
    ema_fast = calc_ema(close, fast)
    ema_slow = calc_ema(close, slow)
    macd_line = ema_fast - ema_slow
    signal_line = calc_ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def calc_atr(high, low, close, period=14):
    tr = pd.DataFrame({
        'hl': high - low,
        'hc': (high - close.shift(1)).abs(),
        'lc': (low - close.shift(1)).abs()
    }).max(axis=1)
    return tr.ewm(alpha=1/period, min_periods=period).mean()

def calc_supertrend(high, low, close, factor=3.0, period=10):
    atr = calc_atr(high, low, close, period)
    hl2 = (high + low) / 2
    upper = hl2 + factor * atr
    lower = hl2 - factor * atr

    st = pd.Series(np.nan, index=close.index)
    direction = pd.Series(1, index=close.index)  # 1=bearish, -1=bullish

    for i in range(1, len(close)):
        if close.iloc[i] > upper.iloc[i-1]:
            direction.iloc[i] = -1
        elif close.iloc[i] < lower.iloc[i-1]:
            direction.iloc[i] = 1
        else:
            direction.iloc[i] = direction.iloc[i-1]
            if direction.iloc[i] == -1 and lower.iloc[i] < lower.iloc[i-1]:
                lower.iloc[i] = lower.iloc[i-1]
            if direction.iloc[i] == 1 and upper.iloc[i] > upper.iloc[i-1]:
                upper.iloc[i] = upper.iloc[i-1]

        st.iloc[i] = lower.iloc[i] if direction.iloc[i] == -1 else upper.iloc[i]

    return st, direction

def calc_adx(high, low, close, period=14):
    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)
    atr = calc_atr(high, low, close, period)
    plus_di = 100 * (plus_dm.ewm(alpha=1/period, min_periods=period).mean() / atr)
    minus_di = 100 * (minus_dm.ewm(alpha=1/period, min_periods=period).mean() / atr)
    dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan))
    adx = dx.ewm(alpha=1/period, min_periods=period).mean()
    return plus_di, minus_di, adx

def calc_wavetrend(hlc3, channel=10, avg=21):
    esa = calc_ema(hlc3, channel)
    d = calc_ema((hlc3 - esa).abs(), channel)
    ci = (hlc3 - esa) / (0.015 * d)
    wt1 = calc_ema(ci, avg)
    wt2 = calc_sma(wt1, 4)
    return wt1, wt2

def calc_stochrsi(close, period=14, k_smooth=3, d_smooth=3):
    rsi = calc_rsi(close, period)
    stoch = (rsi - rsi.rolling(period).min()) / (rsi.rolling(period).max() - rsi.rolling(period).min()).replace(0, np.nan) * 100
    k = calc_sma(stoch, k_smooth)
    d = calc_sma(k, d_smooth)
    return k, d

# ══════════════════════════════════════════════════════════════════════════════
# TIER PROFILES
# ══════════════════════════════════════════════════════════════════════════════

def get_v05_tier(base):
    """Original v0.05 tier classification."""
    tiers = {
        'TRX': 'LOW',
        'BTC': 'MED', 'BNB': 'MED', 'ALGO': 'MED', 'LTC': 'MED',
        'ETH': 'MHIGH', 'DOT': 'MHIGH', 'LINK': 'MHIGH', 'BCH': 'MHIGH', 'TON': 'MHIGH', 'HBAR': 'MHIGH',
        'DOGE': 'EXTR', 'SHIB': 'EXTR', 'FET': 'EXTR', 'SUI': 'EXTR', 'SEI': 'EXTR',
        'TIA': 'EXTR', 'DYDX': 'EXTR', 'STRK': 'EXTR', 'ZK': 'EXTR',
    }
    return tiers.get(base, 'HIGH')

def get_v06_tier(base):
    """v0.06 reclassified tiers based on KC05 performance data."""
    tiers = {
        'TRX': 'LOW',
        'BTC': 'MED', 'ALGO': 'MED',
        'BNB': 'MHIGH', 'LTC': 'MHIGH',  # RECLASSIFIED from MED
        'ETH': 'MHIGH', 'DOT': 'MHIGH', 'LINK': 'MHIGH', 'BCH': 'MHIGH', 'TON': 'MHIGH', 'HBAR': 'MHIGH',
        'POL': 'MHIGH',  # RECLASSIFIED from HIGH
        'DOGE': 'EXTR', 'SHIB': 'EXTR', 'FET': 'EXTR', 'SUI': 'EXTR', 'SEI': 'EXTR',
        'TIA': 'EXTR', 'DYDX': 'EXTR', 'STRK': 'EXTR', 'ZK': 'EXTR',
        'INJ': 'EXTR', 'ARB': 'EXTR', 'APE': 'EXTR',  # RECLASSIFIED from HIGH
    }
    return tiers.get(base, 'HIGH')

def get_tier_params(tier, version='v05'):
    """Get parameters for a volatility tier."""
    params = {
        'LOW':   {'rsi_ob': 68, 'rsi_os': 32, 'st_fact': 2.5, 'st_per': 10, 'adx_trend': 20, 'adx_range': 12, 'vol_adj': 0.75},
        'MED':   {'rsi_ob': 70, 'rsi_os': 35, 'st_fact': 3.0, 'st_per': 10, 'adx_trend': 25, 'adx_range': 15, 'vol_adj': 1.0},
        'MHIGH': {'rsi_ob': 72, 'rsi_os': 30, 'st_fact': 3.2, 'st_per': 10, 'adx_trend': 25, 'adx_range': 16, 'vol_adj': 1.15},
        'HIGH':  {'rsi_ob': 75, 'rsi_os': 28, 'st_fact': 3.5, 'st_per': 10, 'adx_trend': 28, 'adx_range': 20, 'vol_adj': 1.4},
        'EXTR':  {'rsi_ob': 80, 'rsi_os': 24, 'st_fact': 4.5, 'st_per': 10, 'adx_trend': 30, 'adx_range': 20, 'vol_adj': 1.7 if version == 'v05' else 1.4},
    }
    return params.get(tier, params['HIGH'])

def get_special_overrides(base, p):
    """Apply per-pair special overrides."""
    if base == 'DOGE':
        p['macd_f'], p['macd_s'], p['macd_sig'] = 6, 13, 5
    if base == 'SHIB':
        p['rsi_len'] = 21; p['st_fact'] = 5.0; p['st_per'] = 14
    if base == 'SEI':
        p['rsi_len'] = 11; p['st_fact'] = 5.0; p['st_per'] = 12
    if base == 'DYDX':
        p['rsi_len'] = 11; p['st_fact'] = 5.0; p['st_per'] = 14
    if base == 'STRK':
        p['st_fact'] = 4.0; p['st_per'] = 7; p['rsi_ob'] = 65
    if base == 'ZK':
        p['st_fact'] = 4.0; p['st_per'] = 7; p['rsi_ob'] = 63; p['rsi_os'] = 25
    if base == 'SUI':
        p['st_per'] = 12
    return p

# ══════════════════════════════════════════════════════════════════════════════
# BACKTESTER
# ══════════════════════════════════════════════════════════════════════════════

def run_backtest(df, base, version='v05', verbose=False):
    """
    Run the SSK_Claude backtester on OHLCV data.
    Returns dict with performance metrics.
    """
    # Get tier and parameters
    tier = get_v05_tier(base) if version == 'v05' else get_v06_tier(base)
    p = get_tier_params(tier, version)
    p.setdefault('rsi_len', 14)
    p.setdefault('macd_f', 12)
    p.setdefault('macd_s', 26)
    p.setdefault('macd_sig', 9)
    p = get_special_overrides(base, p)

    # v0.06 specific settings
    use_mr_distance = (version == 'v06')
    use_trend_bias = (version == 'v06')
    min_sig = 4 if (version == 'v06' and tier == 'EXTR') else 3
    mr_max_dist = 5.0  # max % distance from EMA50 for MR signals

    # Calculate indicators
    close = df['close']
    high = df['high']
    low = df['low']
    hlc3 = (high + low + close) / 3

    rsi = calc_rsi(close, p['rsi_len'])
    macd_l, sig_l, macd_h = calc_macd(close, p['macd_f'], p['macd_s'], p['macd_sig'])
    st_val, st_dir = calc_supertrend(high, low, close, p['st_fact'], p['st_per'])
    ema_f = calc_ema(close, 9)
    ema_m = calc_ema(close, 21)
    ema_s = calc_ema(close, 50)
    wt1, wt2 = calc_wavetrend(hlc3, 10, 21)
    srsi_k, srsi_d = calc_stochrsi(close, 14, 3, 3)
    di_plus, di_minus, adx = calc_adx(high, low, close, 14)
    atr = calc_atr(high, low, close, 14)

    # EMA50 for MR distance filter
    ema50 = calc_ema(close, 50)

    # TF auto-scaling for 1H: TP=2.0, SL=1.0 (base), adjusted by volAdj
    tp_base = 2.0
    sl_base = 1.0
    tp_mult = tp_base * p['vol_adj']
    sl_mult = sl_base * p['vol_adj']

    # Build signal arrays
    n = len(df)
    trades = []
    in_trade = False
    pending = False
    entry_price = 0.0
    entry_bar = 0
    tp_level = 0.0
    sl_level = 0.0
    max_hold = 15

    for i in range(max(60, p.get('rsi_len', 14) + 5), n):
        if np.isnan(adx.iloc[i]) or np.isnan(rsi.iloc[i]):
            continue

        # Regime
        adx_v = adx.iloc[i]
        regime = 'TREND' if adx_v >= p['adx_trend'] else ('MIXED' if adx_v >= p['adx_range'] else 'RANGE')
        is_trend = regime == 'TREND'
        is_range = regime == 'RANGE'

        # Signal conditions
        rsi_buy_raw = rsi.iloc[i] < p['rsi_os']
        rsi_sell_raw = rsi.iloc[i] > p['rsi_ob']

        macd_buy = macd_l.iloc[i] > sig_l.iloc[i] and macd_h.iloc[i] > 0
        macd_sell = macd_l.iloc[i] < sig_l.iloc[i] and macd_h.iloc[i] < 0

        st_buy_raw = st_dir.iloc[i] < 0
        st_sell_raw = st_dir.iloc[i] > 0

        ema_bull_raw = ema_f.iloc[i] > ema_m.iloc[i] and ema_m.iloc[i] > ema_s.iloc[i]
        ema_bear_raw = ema_f.iloc[i] < ema_m.iloc[i] and ema_m.iloc[i] < ema_s.iloc[i]

        # WaveTrend crossover
        wt_buy_raw = (wt1.iloc[i] > wt2.iloc[i] and wt1.iloc[i-1] <= wt2.iloc[i-1] and wt1.iloc[i] < -60)
        wt_sell_raw = (wt1.iloc[i] < wt2.iloc[i] and wt1.iloc[i-1] >= wt2.iloc[i-1] and wt1.iloc[i] > 60)

        # StochRSI crossover
        sr_buy = (not np.isnan(srsi_k.iloc[i]) and not np.isnan(srsi_d.iloc[i]) and
                  srsi_k.iloc[i] > srsi_d.iloc[i] and srsi_k.iloc[i-1] <= srsi_d.iloc[i-1] and srsi_k.iloc[i] < 20)
        sr_sell = (not np.isnan(srsi_k.iloc[i]) and not np.isnan(srsi_d.iloc[i]) and
                   srsi_k.iloc[i] < srsi_d.iloc[i] and srsi_k.iloc[i-1] >= srsi_d.iloc[i-1] and srsi_k.iloc[i] > 80)

        adx_bull = di_plus.iloc[i] > di_minus.iloc[i]
        adx_bear = di_minus.iloc[i] > di_plus.iloc[i]

        # Regime gating
        rsi_buy = False if is_trend else rsi_buy_raw
        rsi_sell = False if is_trend else rsi_sell_raw
        st_buy = False if is_range else st_buy_raw
        st_sell = False if is_range else st_sell_raw
        ema_bull = False if is_range else ema_bull_raw
        ema_bear = False if is_range else ema_bear_raw
        wt_buy = False if is_trend else wt_buy_raw
        wt_sell = False if is_trend else wt_sell_raw

        # v0.06: MR distance filter — don't fire RSI/WT when price is far from EMA50
        if use_mr_distance and not np.isnan(ema50.iloc[i]) and ema50.iloc[i] > 0:
            dist_pct = abs(close.iloc[i] - ema50.iloc[i]) / ema50.iloc[i] * 100
            if dist_pct > mr_max_dist:
                rsi_buy = False
                rsi_sell = False
                wt_buy = False
                wt_sell = False

        # Weighted consensus scoring
        b_score = 0
        b_score += (2 if is_range else 1) if rsi_buy else 0
        b_score += (2 if is_trend else 1) if macd_buy else 0
        b_score += (2 if is_trend else 1) if st_buy else 0
        b_score += (2 if is_trend else 1) if ema_bull else 0
        b_score += (2 if is_range else 1) if wt_buy else 0
        b_score += 1 if sr_buy else 0
        b_score += 1 if adx_bull else 0

        s_score = 0
        s_score += (2 if is_range else 1) if rsi_sell else 0
        s_score += (2 if is_trend else 1) if macd_sell else 0
        s_score += (2 if is_trend else 1) if st_sell else 0
        s_score += (2 if is_trend else 1) if ema_bear else 0
        s_score += (2 if is_range else 1) if wt_sell else 0
        s_score += 1 if sr_sell else 0
        s_score += 1 if adx_bear else 0

        # v0.06: Trend bias filter — counter-trend needs +1 extra
        if use_trend_bias:
            # If price below EMA50 (bearish), buying needs +1 extra
            if not np.isnan(ema50.iloc[i]) and close.iloc[i] < ema50.iloc[i]:
                b_score = max(0, b_score - 1)
            # If price above EMA50 (bullish), selling needs +1 extra
            if not np.isnan(ema50.iloc[i]) and close.iloc[i] > ema50.iloc[i]:
                s_score = max(0, s_score - 1)

        is_buy = b_score >= min_sig and b_score > s_score
        is_sell = s_score >= min_sig and s_score > b_score

        # Trade management (long-only backtester, next-bar-open entry)
        if pending and not in_trade:
            entry_price = df['open'].iloc[i]
            entry_bar = i
            tp_dist = atr.iloc[i] * tp_mult if not np.isnan(atr.iloc[i]) else entry_price * 0.02
            sl_dist = atr.iloc[i] * sl_mult if not np.isnan(atr.iloc[i]) else entry_price * 0.01
            tp_level = entry_price + tp_dist
            sl_level = entry_price - sl_dist
            in_trade = True
            pending = False

        if in_trade:
            tp_hit = high.iloc[i] >= tp_level
            sl_hit = low.iloc[i] <= sl_level
            bars_held = i - entry_bar

            if tp_hit and sl_hit:
                pnl = -(abs(entry_price - sl_level) / entry_price * 100)
                trades.append({'pnl': pnl, 'bars': bars_held, 'result': 'loss'})
                in_trade = False
            elif tp_hit:
                pnl = (tp_level - entry_price) / entry_price * 100
                trades.append({'pnl': pnl, 'bars': bars_held, 'result': 'win'})
                in_trade = False
            elif sl_hit:
                pnl = -(abs(entry_price - sl_level) / entry_price * 100)
                trades.append({'pnl': pnl, 'bars': bars_held, 'result': 'loss'})
                in_trade = False
            elif bars_held >= max_hold:
                pnl = (close.iloc[i] - entry_price) / entry_price * 100
                result = 'win' if pnl > 0.1 else ('loss' if pnl < -0.1 else 'flat')
                trades.append({'pnl': pnl, 'bars': bars_held, 'result': result})
                in_trade = False

        if not in_trade and not pending and is_buy:
            pending = True

    # Calculate metrics
    if not trades:
        return {'symbol': base, 'tier': tier, 'version': version,
                'trades': 0, 'wins': 0, 'losses': 0, 'wr': 0, 'pf': 0,
                'net_pnl': 0, 'avg_win': 0, 'avg_loss': 0, 'expectancy': 0,
                'max_dd_pct': 0, 'sharpe': 0}

    wins = [t for t in trades if t['result'] == 'win']
    losses = [t for t in trades if t['result'] == 'loss']
    total = len(wins) + len(losses)
    wr = len(wins) / total * 100 if total > 0 else 0
    sum_win = sum(t['pnl'] for t in wins)
    sum_loss = sum(abs(t['pnl']) for t in losses)
    pf = sum_win / sum_loss if sum_loss > 0 else (99.9 if sum_win > 0 else 0)
    avg_win = sum_win / len(wins) if wins else 0
    avg_loss = sum_loss / len(losses) if losses else 0
    net_pnl = sum(t['pnl'] for t in trades)
    expectancy = (wr/100 * avg_win) - ((100-wr)/100 * avg_loss) if total > 0 else 0

    # Equity curve for max DD and Sharpe
    equity = [0]
    for t in trades:
        equity.append(equity[-1] + t['pnl'])
    equity = np.array(equity)
    peak = np.maximum.accumulate(equity)
    dd = equity - peak
    max_dd = dd.min()

    # Sharpe (annualized, assuming ~8760 1H bars/year, avg ~290 trades/year)
    pnl_arr = np.array([t['pnl'] for t in trades])
    sharpe = np.mean(pnl_arr) / np.std(pnl_arr) * np.sqrt(min(total, 365)) if np.std(pnl_arr) > 0 else 0

    return {
        'symbol': base, 'tier': tier, 'version': version,
        'trades': total, 'wins': len(wins), 'losses': len(losses),
        'wr': round(wr, 2), 'pf': round(pf, 3),
        'net_pnl': round(net_pnl, 2), 'avg_win': round(avg_win, 3),
        'avg_loss': round(avg_loss, 3), 'expectancy': round(expectancy, 4),
        'max_dd_pct': round(max_dd, 2), 'sharpe': round(sharpe, 3)
    }

# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

# Test representative pairs from each tier
TEST_PAIRS = [
    # LOW
    ('TRXUSDT', 'TRX'),
    # MED
    ('BTCUSDT', 'BTC'), ('ALGOUSDT', 'ALGO'),
    # MHIGH
    ('ETHUSDT', 'ETH'), ('DOTUSDT', 'DOT'),
    # HIGH
    ('SOLUSDT', 'SOL'), ('XRPUSDT', 'XRP'), ('POLUSDT', 'POL'),
    ('INJUSDT', 'INJ'), ('ARBUSDT', 'ARB'), ('APEUSDT', 'APE'),
    # EXTR
    ('DOGEUSDT', 'DOGE'), ('SEIUSDT', 'SEI'), ('FETUSDT', 'FET'),
    ('DYDXUSDT', 'DYDX'), ('SHIBUSDT', 'SHIB'),
]

def main():
    results = []
    cache = {}

    for symbol, base in TEST_PAIRS:
        print(f"\n{'='*60}")
        print(f"  {symbol} ({base})")
        print(f"{'='*60}")

        # Download data (cached)
        if symbol not in cache:
            print(f"  Downloading 1H data...")
            df = download_binance_klines(symbol, '1h', 1095)
            if df is None or len(df) < 500:
                print(f"  SKIP: insufficient data ({0 if df is None else len(df)} bars)")
                continue
            cache[symbol] = df
            print(f"  Got {len(df)} bars ({df.index[0]} to {df.index[-1]})")
        else:
            df = cache[symbol]

        # Run v0.05 baseline
        print(f"  Running v0.05...")
        r05 = run_backtest(df, base, 'v05')
        results.append(r05)
        print(f"    Tier={r05['tier']} Trades={r05['trades']} WR={r05['wr']}% PF={r05['pf']} Net={r05['net_pnl']}% DD={r05['max_dd_pct']}%")

        # Run v0.06
        print(f"  Running v0.06...")
        r06 = run_backtest(df, base, 'v06')
        results.append(r06)
        print(f"    Tier={r06['tier']} Trades={r06['trades']} WR={r06['wr']}% PF={r06['pf']} Net={r06['net_pnl']}% DD={r06['max_dd_pct']}%")

        # Delta
        d_pnl = r06['net_pnl'] - r05['net_pnl']
        d_pf = r06['pf'] - r05['pf']
        d_wr = r06['wr'] - r05['wr']
        d_dd = r06['max_dd_pct'] - r05['max_dd_pct']
        print(f"    DELTA: PnL {d_pnl:+.2f}% | PF {d_pf:+.3f} | WR {d_wr:+.2f}% | DD {d_dd:+.2f}%")

    # ══════════════════════════════════════════════════════════════════════════
    # AGGREGATE ANALYSIS
    # ══════════════════════════════════════════════════════════════════════════
    print("\n" + "="*80)
    print("  AGGREGATE COMPARISON: v0.05 vs v0.06")
    print("="*80)

    v05 = [r for r in results if r['version'] == 'v05' and r['trades'] > 0]
    v06 = [r for r in results if r['version'] == 'v06' and r['trades'] > 0]

    if v05 and v06:
        # Match pairs
        pairs_tested = set(r['symbol'] for r in v05) & set(r['symbol'] for r in v06)
        v05_map = {r['symbol']: r for r in v05}
        v06_map = {r['symbol']: r for r in v06}

        print(f"\n{'Symbol':<8} {'v05 Tier':<7} {'v06 Tier':<7} {'v05 PnL':>8} {'v06 PnL':>8} {'Delta':>8} {'v05 PF':>7} {'v06 PF':>7} {'v05 WR':>7} {'v06 WR':>7} {'v05 Tr':>6} {'v06 Tr':>6}")
        print("-" * 105)

        total_d_pnl = 0
        improved = 0
        worsened = 0

        for sym in sorted(pairs_tested):
            a = v05_map[sym]
            b = v06_map[sym]
            d = b['net_pnl'] - a['net_pnl']
            total_d_pnl += d
            if d > 0.5: improved += 1
            elif d < -0.5: worsened += 1
            marker = '+' if d > 0.5 else ('-' if d < -0.5 else '=')
            print(f"{sym:<8} {a['tier']:<7} {b['tier']:<7} {a['net_pnl']:>7.2f}% {b['net_pnl']:>7.2f}% {d:>+7.2f}% {a['pf']:>7.3f} {b['pf']:>7.3f} {a['wr']:>6.1f}% {b['wr']:>6.1f}% {a['trades']:>6} {b['trades']:>6} {marker}")

        n_tested = len(pairs_tested)
        avg_v05_pnl = np.mean([v05_map[s]['net_pnl'] for s in pairs_tested])
        avg_v06_pnl = np.mean([v06_map[s]['net_pnl'] for s in pairs_tested])
        avg_v05_pf = np.mean([v05_map[s]['pf'] for s in pairs_tested])
        avg_v06_pf = np.mean([v06_map[s]['pf'] for s in pairs_tested])
        avg_v05_wr = np.mean([v05_map[s]['wr'] for s in pairs_tested])
        avg_v06_wr = np.mean([v06_map[s]['wr'] for s in pairs_tested])

        print(f"\n{'AVERAGE':<8} {'':7} {'':7} {avg_v05_pnl:>7.2f}% {avg_v06_pnl:>7.2f}% {avg_v06_pnl-avg_v05_pnl:>+7.2f}% {avg_v05_pf:>7.3f} {avg_v06_pf:>7.3f} {avg_v05_wr:>6.1f}% {avg_v06_wr:>6.1f}%")
        print(f"\nPairs tested: {n_tested}")
        print(f"Improved (>0.5% better): {improved}/{n_tested}")
        print(f"Worsened (>0.5% worse): {worsened}/{n_tested}")
        print(f"Neutral: {n_tested - improved - worsened}/{n_tested}")

        # Statistical test: paired t-test on PnL difference
        v05_pnls = [v05_map[s]['net_pnl'] for s in sorted(pairs_tested)]
        v06_pnls = [v06_map[s]['net_pnl'] for s in sorted(pairs_tested)]
        diffs = np.array(v06_pnls) - np.array(v05_pnls)
        mean_d = np.mean(diffs)
        std_d = np.std(diffs, ddof=1)
        t_stat = mean_d / (std_d / np.sqrt(len(diffs))) if std_d > 0 else 0
        # Simple p-value approximation (two-tailed)
        from math import erfc, sqrt
        p_value = erfc(abs(t_stat) / sqrt(2))

        print(f"\n--- Statistical Significance (Paired t-test) ---")
        print(f"Mean PnL improvement: {mean_d:+.3f}%")
        print(f"Std of differences: {std_d:.3f}%")
        print(f"t-statistic: {t_stat:.3f}")
        print(f"p-value (two-tailed): {p_value:.6f}")
        if p_value < 0.05:
            print(f">>> STATISTICALLY SIGNIFICANT at 95% confidence (p < 0.05)")
        elif p_value < 0.10:
            print(f">>> MARGINALLY SIGNIFICANT (p < 0.10)")
        else:
            print(f">>> NOT significant (p >= 0.10)")

    # Save results
    output_path = 'backtest_results/v05_vs_v06_comparison.json'
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {output_path}")

if __name__ == '__main__':
    main()
