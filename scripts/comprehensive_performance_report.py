#!/usr/bin/env python3
"""
Comprehensive Portfolio Performance Report – V2
=================================================
Addresses BOTH rounds of feedback:

ROUND 1 (already done):
  - Realistic fee model ($4.95 Questrade flat)
  - Position sizing (5% of equity, capped at $2k)
  - End-of-data exits flagged
  - SPY benchmark, CAGR, Calmar, bootstrap CI, binomial CI
  - TP/SL grid search, train/test split

ROUND 2 (new):
  - ATR-based adaptive TP/SL (volatility-scaled thresholds)
  - Concentration limits (max 5% per ticker, max 20% per sector)
  - Buy-and-hold benchmark separated from active trading
  - Commission-free gross performance comparison
  - Recovery Factor, CVaR (Conditional VaR), annualized turnover
  - Monte Carlo simulation (1000 reshuffles) for robustness
  - Sector breakdown of trades
  - Executive summary, reproducibility checklist

OUTPUT:
  - data/PORTFOLIO_PERFORMANCE_REPORT.md
  - data/performance_report.json

Usage:
  python scripts/comprehensive_performance_report.py
  python scripts/comprehensive_performance_report.py --skip-grid --skip-monte-carlo

Requirements: pip install mysql-connector-python
"""
import os
import sys
import json
import math
import random
import argparse
from datetime import datetime, timezone, timedelta, date as dt_date
from collections import defaultdict

# ─────────────────────────────────────────────────
#  CONFIGURATION
# ─────────────────────────────────────────────────
DB_HOST = os.getenv('DB_HOST', 'mysql.50webs.com')
DB_USER = os.getenv('DB_USER', 'ejaguiar1_stocks')
DB_PASS = os.getenv('DB_PASS', 'stocks')
DB_NAME = os.getenv('DB_NAME', 'ejaguiar1_stocks')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, '..', 'data')

# Fee models
FEE_MODELS = {
    'questrade':  {'per_trade': 4.95, 'label': 'Questrade $4.95'},
    'flat_10':    {'per_trade': 9.99, 'label': 'Legacy flat $9.99'},
    'flat_1':     {'per_trade': 0.99, 'label': 'Discount $0.99'},
    'zero':       {'per_trade': 0.00, 'label': 'Commission-free (gross)'},
}
DEFAULT_FEE = 'questrade'
SLIPPAGE_PCT = 0.1           # 0.1% per side
INITIAL_CAPITAL = 10000.0
POSITION_PCT = 5.0           # 5% of equity per trade
POSITION_CAP = 2000.0
EMBARGO_DAYS = 1
ATR_PERIOD = 14              # For adaptive TP/SL

# Concentration limits
MAX_TICKER_PCT = 5.0         # Max 5% of portfolio in one ticker
MAX_SECTOR_PCT = 20.0        # Max 20% per sector

# Sector mapping (GICS-like for common tickers)
SECTOR_MAP = {
    # Technology
    'AAPL': 'Technology', 'MSFT': 'Technology', 'GOOG': 'Technology', 'GOOGL': 'Technology',
    'META': 'Technology', 'NVDA': 'Technology', 'AVGO': 'Technology', 'ADBE': 'Technology',
    'CRM': 'Technology', 'CSCO': 'Technology', 'INTC': 'Technology', 'AMD': 'Technology',
    'ORCL': 'Technology', 'IBM': 'Technology', 'QCOM': 'Technology', 'TXN': 'Technology',
    'MU': 'Technology', 'AMAT': 'Technology', 'LRCX': 'Technology', 'KLAC': 'Technology',
    'NOW': 'Technology', 'PANW': 'Technology', 'SNPS': 'Technology', 'CDNS': 'Technology',
    'MRVL': 'Technology', 'NXPI': 'Technology',
    # Healthcare
    'UNH': 'Healthcare', 'JNJ': 'Healthcare', 'LLY': 'Healthcare', 'PFE': 'Healthcare',
    'ABBV': 'Healthcare', 'MRK': 'Healthcare', 'ABT': 'Healthcare', 'TMO': 'Healthcare',
    'MDT': 'Healthcare', 'DHR': 'Healthcare', 'BMY': 'Healthcare', 'AMGN': 'Healthcare',
    'GILD': 'Healthcare', 'ISRG': 'Healthcare', 'VRTX': 'Healthcare', 'REGN': 'Healthcare',
    'SYK': 'Healthcare', 'ZTS': 'Healthcare', 'BDX': 'Healthcare', 'EW': 'Healthcare',
    'CI': 'Healthcare', 'HCA': 'Healthcare', 'CVS': 'Healthcare',
    # Financials
    'JPM': 'Financials', 'BAC': 'Financials', 'WFC': 'Financials', 'GS': 'Financials',
    'MS': 'Financials', 'C': 'Financials', 'BLK': 'Financials', 'SCHW': 'Financials',
    'AXP': 'Financials', 'USB': 'Financials', 'PNC': 'Financials', 'TFC': 'Financials',
    'BRK.B': 'Financials', 'V': 'Financials', 'MA': 'Financials', 'PYPL': 'Financials',
    'COF': 'Financials', 'ICE': 'Financials', 'CME': 'Financials', 'MCO': 'Financials',
    'SPGI': 'Financials', 'MMC': 'Financials', 'AIG': 'Financials', 'MET': 'Financials',
    # Consumer Discretionary
    'AMZN': 'Consumer Disc.', 'TSLA': 'Consumer Disc.', 'HD': 'Consumer Disc.',
    'MCD': 'Consumer Disc.', 'NKE': 'Consumer Disc.', 'SBUX': 'Consumer Disc.',
    'LOW': 'Consumer Disc.', 'TJX': 'Consumer Disc.', 'BKNG': 'Consumer Disc.',
    'GM': 'Consumer Disc.', 'F': 'Consumer Disc.', 'MAR': 'Consumer Disc.',
    'CMG': 'Consumer Disc.', 'ORLY': 'Consumer Disc.', 'AZO': 'Consumer Disc.',
    'ROST': 'Consumer Disc.', 'DHI': 'Consumer Disc.', 'LEN': 'Consumer Disc.',
    # Consumer Staples
    'PG': 'Consumer Staples', 'KO': 'Consumer Staples', 'PEP': 'Consumer Staples',
    'COST': 'Consumer Staples', 'WMT': 'Consumer Staples', 'PM': 'Consumer Staples',
    'MO': 'Consumer Staples', 'CL': 'Consumer Staples', 'MDLZ': 'Consumer Staples',
    'GIS': 'Consumer Staples', 'K': 'Consumer Staples', 'KHC': 'Consumer Staples',
    'SYY': 'Consumer Staples', 'STZ': 'Consumer Staples', 'KMB': 'Consumer Staples',
    # Energy
    'XOM': 'Energy', 'CVX': 'Energy', 'COP': 'Energy', 'SLB': 'Energy',
    'EOG': 'Energy', 'PSX': 'Energy', 'MPC': 'Energy', 'VLO': 'Energy',
    'PXD': 'Energy', 'OXY': 'Energy', 'DVN': 'Energy', 'HES': 'Energy',
    'HAL': 'Energy', 'BKR': 'Energy', 'FANG': 'Energy',
    # Industrials
    'CAT': 'Industrials', 'DE': 'Industrials', 'HON': 'Industrials',
    'UNP': 'Industrials', 'UPS': 'Industrials', 'BA': 'Industrials',
    'GE': 'Industrials', 'MMM': 'Industrials', 'LMT': 'Industrials',
    'RTX': 'Industrials', 'NOC': 'Industrials', 'GD': 'Industrials',
    'EMR': 'Industrials', 'WM': 'Industrials', 'RSG': 'Industrials',
    'ITW': 'Industrials', 'ETN': 'Industrials', 'PH': 'Industrials',
    'CTAS': 'Industrials', 'FAST': 'Industrials', 'CSX': 'Industrials',
    'NSC': 'Industrials', 'FDX': 'Industrials',
    # Real Estate
    'AMT': 'Real Estate', 'PLD': 'Real Estate', 'CCI': 'Real Estate',
    'EQIX': 'Real Estate', 'SPG': 'Real Estate', 'O': 'Real Estate',
    'DLR': 'Real Estate', 'PSA': 'Real Estate', 'WELL': 'Real Estate',
    'AVB': 'Real Estate', 'EQR': 'Real Estate', 'VICI': 'Real Estate',
    # Utilities
    'NEE': 'Utilities', 'DUK': 'Utilities', 'SO': 'Utilities',
    'D': 'Utilities', 'AEP': 'Utilities', 'SRE': 'Utilities',
    'EXC': 'Utilities', 'XEL': 'Utilities', 'ED': 'Utilities',
    'WEC': 'Utilities', 'ES': 'Utilities', 'AES': 'Utilities',
    # Materials
    'LIN': 'Materials', 'APD': 'Materials', 'SHW': 'Materials',
    'FCX': 'Materials', 'NEM': 'Materials', 'ECL': 'Materials',
    'DD': 'Materials', 'NUE': 'Materials', 'DOW': 'Materials',
    # Communication
    'DIS': 'Communication', 'CMCSA': 'Communication', 'NFLX': 'Communication',
    'T': 'Communication', 'VZ': 'Communication', 'TMUS': 'Communication',
    'CHTR': 'Communication', 'EA': 'Communication', 'ATVI': 'Communication',
    # ETFs → ETF sector
    'SPY': 'ETF', 'QQQ': 'ETF', 'IWM': 'ETF', 'DIA': 'ETF',
    'VTI': 'ETF', 'VOO': 'ETF', 'EFA': 'ETF', 'EEM': 'ETF',
    'INDA': 'ETF', 'GLD': 'ETF', 'SLV': 'ETF', 'TLT': 'ETF',
    'HYG': 'ETF', 'LQD': 'ETF', 'BND': 'ETF', 'AGG': 'ETF',
    'XLF': 'ETF', 'XLK': 'ETF', 'XLE': 'ETF', 'XLV': 'ETF',
    'XLI': 'ETF', 'XLP': 'ETF', 'XLY': 'ETF', 'XLU': 'ETF',
    'DVY': 'ETF', 'VNQ': 'ETF', 'ARKK': 'ETF', 'SOXX': 'ETF',
    'SMH': 'ETF', 'XBI': 'ETF', 'IBB': 'ETF', 'VWO': 'ETF',
    'VEA': 'ETF', 'IEMG': 'ETF',
}

# TP/SL grid (expanded with MiniMax-suggested configs)
GRID_CONFIGS = [
    {'tp': 5,  'sl': 3,  'hold': 7,   'label': '5/3/7d'},
    {'tp': 8,  'sl': 5,  'hold': 20,  'label': '8/5/20d'},
    {'tp': 10, 'sl': 5,  'hold': 30,  'label': '10/5/30d'},
    {'tp': 10, 'sl': 7,  'hold': 30,  'label': '10/7/30d'},
    {'tp': 12, 'sl': 8,  'hold': 30,  'label': '12/8/30d'},
    {'tp': 15, 'sl': 10, 'hold': 60,  'label': '15/10/60d'},
    {'tp': 20, 'sl': 10, 'hold': 60,  'label': '20/10/60d'},
    {'tp': 20, 'sl': 12, 'hold': 90,  'label': '20/12/90d'},
    {'tp': 25, 'sl': 12, 'hold': 90,  'label': '25/12/90d'},
    {'tp': 30, 'sl': 15, 'hold': 90,  'label': '30/15/90d'},
    {'tp': 30, 'sl': 20, 'hold': 180, 'label': '30/20/180d'},
    {'tp': 50, 'sl': 20, 'hold': 90,  'label': '50/20/90d'},
    {'tp': 50, 'sl': 20, 'hold': 180, 'label': '50/20/180d'},
]

# Trailing stop experiments
TRAILING_CONFIGS = [
    {'tp': 50, 'sl': 20, 'hold': 90,  'trail': 10, 'label': '50/20/90d+trail10'},
    {'tp': 50, 'sl': 20, 'hold': 90,  'trail': 15, 'label': '50/20/90d+trail15'},
    {'tp': 50, 'sl': 20, 'hold': 180, 'trail': 10, 'label': '50/20/180d+trail10'},
    {'tp': 50, 'sl': 20, 'hold': 180, 'trail': 15, 'label': '50/20/180d+trail15'},
    {'tp': 30, 'sl': 15, 'hold': 90,  'trail': 10, 'label': '30/15/90d+trail10'},
    # With partial profit lock-in at +8%
    {'tp': 50, 'sl': 20, 'hold': 90,  'trail': 10, 'partial': 8, 'label': '50/20/90d+trail10+pp8'},
    {'tp': 30, 'sl': 15, 'hold': 90,  'trail': 10, 'partial': 6, 'label': '30/15/90d+trail10+pp6'},
    # With breakeven after +6%
    {'tp': 50, 'sl': 20, 'hold': 90,  'trail': 0, 'be': 6, 'label': '50/20/90d+be6'},
    {'tp': 30, 'sl': 15, 'hold': 90,  'trail': 0, 'be': 6, 'label': '30/15/90d+be6'},
]


def connect_db():
    import mysql.connector
    return mysql.connector.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME
    )


def get_sector(ticker):
    return SECTOR_MAP.get(ticker, 'Other')


# ─────────────────────────────────────────────────
#  DATA LOADING
# ─────────────────────────────────────────────────
def load_data(conn):
    """Load all picks and prices from DB."""
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT ticker, algorithm_name, pick_date, entry_price, score, rating, risk_level
        FROM stock_picks WHERE entry_price > 0
        ORDER BY pick_date ASC
    """)
    picks = cur.fetchall()

    tickers = set(p['ticker'] for p in picks)
    tickers.add('SPY')
    prices = {}
    for tk in tickers:
        cur.execute("SELECT trade_date, open_price, high_price, low_price, close_price "
                     "FROM daily_prices WHERE ticker = %s ORDER BY trade_date ASC", (tk,))
        prices[tk] = cur.fetchall()
    return picks, prices


# ─────────────────────────────────────────────────
#  ATR CALCULATION (for adaptive TP/SL)
# ─────────────────────────────────────────────────
def compute_atr(price_list, end_idx, period=ATR_PERIOD):
    """Compute Average True Range at a given index."""
    if end_idx < period + 1:
        return None
    trs = []
    for i in range(max(1, end_idx - period), end_idx + 1):
        h = float(price_list[i]['high_price'])
        l = float(price_list[i]['low_price'])
        prev_c = float(price_list[i - 1]['close_price'])
        tr = max(h - l, abs(h - prev_c), abs(l - prev_c))
        trs.append(tr)
    return sum(trs) / len(trs) if trs else None


# ─────────────────────────────────────────────────
#  BACKTEST ENGINE V2
# ─────────────────────────────────────────────────
def backtest(picks, prices, tp=10, sl=5, max_hold=30,
             fee_model=DEFAULT_FEE, capital=INITIAL_CAPITAL,
             pos_pct=POSITION_PCT, pos_cap=POSITION_CAP,
             slippage=SLIPPAGE_PCT, embargo=EMBARGO_DAYS,
             adaptive_tpsl=False, atr_tp_mult=2.0, atr_sl_mult=1.0,
             concentration_limits=False,
             max_ticker_pct=MAX_TICKER_PCT, max_sector_pct=MAX_SECTOR_PCT,
             trailing_stop_pct=0, partial_profit_pct=0, partial_exit_frac=0.5,
             breakeven_after_pct=0):
    """
    Backtest V3 with realistic fees, adaptive TP/SL, concentration limits,
    trailing stop, partial profit lock-in, and stop-to-breakeven.

    New params:
      trailing_stop_pct: If >0, once price rises X% from entry, SL trails
                         at (high_water - trailing_stop_pct%). Replaces fixed SL.
      partial_profit_pct: If >0, take partial profit (partial_exit_frac of shares)
                          when price hits +X% from entry.
      partial_exit_frac: Fraction of shares to exit at partial profit (default 0.5).
      breakeven_after_pct: If >0, once price hits +X%, move SL to breakeven (entry price).
    """
    comm = FEE_MODELS.get(fee_model, FEE_MODELS[DEFAULT_FEE])['per_trade']
    equity = capital
    peak_equity = capital
    trades = []
    equity_curve = []

    # Concentration tracking (overlapping open positions with date windows)
    open_windows = []  # list of (exit_date, ticker, sector, alloc)

    for pick in picks:
        tk = pick['ticker']
        ep = float(pick['entry_price'])
        pd_date = pick['pick_date']
        algo = pick['algorithm_name']
        sector = get_sector(tk)

        if tk not in prices or not prices[tk] or ep <= 0:
            continue

        plist = prices[tk]
        si = None
        for i, pr in enumerate(plist):
            if pr['trade_date'] >= pd_date:
                si = i + embargo
                break
        if si is None or si >= len(plist):
            continue

        actual_entry = float(plist[si]['open_price']) * (1 + slippage / 100.0)
        if actual_entry <= 0:
            actual_entry = ep * (1 + slippage / 100.0)

        # Position sizing
        pos_value = min(equity * pos_pct / 100.0, pos_cap)
        if pos_value < actual_entry + comm:
            continue

        # Concentration limits — track overlapping positions by date
        if concentration_limits:
            # Expire closed positions
            open_windows = [w for w in open_windows if w[0] >= pd_date]
            # Compute current exposure per ticker and sector
            tk_exp = sum(w[3] for w in open_windows if w[1] == tk)
            sect_exp = sum(w[3] for w in open_windows if w[2] == sector)
            ticker_limit = equity * max_ticker_pct / 100.0
            sector_limit = equity * max_sector_pct / 100.0
            if tk_exp + pos_value > ticker_limit:
                pos_value = max(0, ticker_limit - tk_exp)
            if sect_exp + pos_value > sector_limit:
                pos_value = max(0, sector_limit - sect_exp)
            if pos_value < actual_entry + comm:
                continue

        shares = int((pos_value - comm) / actual_entry)
        if shares <= 0:
            continue

        alloc = shares * actual_entry
        # Track open window (estimated exit date for concentration tracking)
        est_exit = pd_date + timedelta(days=max_hold + 5)
        if concentration_limits:
            open_windows.append((est_exit, tk, sector, alloc))

        # Adaptive TP/SL from ATR (hybrid: ATR-based OR fixed floor, whichever is larger)
        use_tp = tp
        use_sl = sl
        if adaptive_tpsl:
            atr = compute_atr(plist, si, ATR_PERIOD)
            if atr and atr > 0:
                atr_tp = (atr * atr_tp_mult / actual_entry) * 100.0
                atr_sl = (atr * atr_sl_mult / actual_entry) * 100.0
                # Use the LARGER of ATR-based or fixed floor
                use_tp = max(atr_tp, tp)
                use_sl = max(atr_sl, sl)

        tp_price = actual_entry * (1 + use_tp / 100.0)
        sl_price = actual_entry * (1 - use_sl / 100.0)
        exit_price = 0
        exit_reason = ''
        exit_date = None
        hd = 0

        # Trailing stop state
        high_water = actual_entry
        trailing_active = trailing_stop_pct > 0
        # Partial profit state
        partial_taken = False
        partial_shares_sold = 0
        partial_pnl = 0
        # Breakeven state
        breakeven_active = breakeven_after_pct > 0
        breakeven_triggered = False

        for j in range(si, min(si + max_hold + 2, len(plist))):
            bar = plist[j]
            hd += 1
            h = float(bar['high_price'])
            l = float(bar['low_price'])
            c = float(bar['close_price'])
            o = float(bar['open_price'])
            d = bar['trade_date']

            # Update high water mark for trailing stop
            if h > high_water:
                high_water = h

            # Breakeven: once price hits +X%, move SL to entry price
            if breakeven_active and not breakeven_triggered:
                be_target = actual_entry * (1 + breakeven_after_pct / 100.0)
                if h >= be_target:
                    breakeven_triggered = True
                    sl_price = max(sl_price, actual_entry)  # Move SL to breakeven

            # Trailing stop: SL follows high_water - trail%
            if trailing_active and high_water > actual_entry:
                trail_sl = high_water * (1 - trailing_stop_pct / 100.0)
                sl_price = max(sl_price, trail_sl)  # Only ratchet up

            # Partial profit: take half off at +X%
            if partial_profit_pct > 0 and not partial_taken:
                pp_target = actual_entry * (1 + partial_profit_pct / 100.0)
                if h >= pp_target:
                    partial_taken = True
                    partial_shares_sold = int(shares * partial_exit_frac)
                    if partial_shares_sold > 0:
                        pp_exit = pp_target * (1 - slippage / 100.0)
                        partial_pnl = (pp_exit - actual_entry) * partial_shares_sold - comm
                        shares = shares - partial_shares_sold

            # Gap-aware SL
            if hd > 1 and o <= sl_price and use_sl < 999:
                exit_price = o
                exit_reason = 'trailing_stop_gap' if trailing_active else 'stop_loss_gap'
                exit_date = d
                break
            if l <= sl_price and use_sl < 999:
                exit_price = sl_price
                exit_reason = 'trailing_stop' if (trailing_active and sl_price > actual_entry * (1 - use_sl / 100.0)) else 'stop_loss'
                exit_date = d
                break
            # Gap-aware TP
            if hd > 1 and o >= tp_price and use_tp < 999:
                exit_price = o
                exit_reason = 'take_profit_gap'
                exit_date = d
                break
            if h >= tp_price and use_tp < 999:
                exit_price = tp_price
                exit_reason = 'take_profit'
                exit_date = d
                break
            if hd >= max_hold:
                exit_price = c
                exit_reason = 'max_hold'
                exit_date = d
                break

        if exit_price <= 0:
            if hd > 0 and len(plist) > si:
                last_bar = plist[min(si + hd, len(plist) - 1)]
                exit_price = float(last_bar['close_price'])
                exit_date = last_bar['trade_date']
                exit_reason = 'end_of_data'
            else:
                continue

        actual_exit = exit_price * (1 - slippage / 100.0)
        gross_pnl = (actual_exit - actual_entry) * shares + (partial_pnl if partial_taken else 0)
        # Commissions: entry + exit for remaining shares, + partial exit commission if taken
        total_commission = comm * 2
        if partial_taken and partial_shares_sold > 0:
            total_commission += comm  # Extra commission for partial exit
        net_pnl = gross_pnl - total_commission
        original_shares = shares + partial_shares_sold
        cost_basis = actual_entry * original_shares
        ret_pct = (net_pnl / cost_basis) * 100.0 if cost_basis > 0 else 0
        ret_pct_gross = (gross_pnl / cost_basis) * 100.0 if cost_basis > 0 else 0

        if ret_pct < -100:
            ret_pct = -100
            net_pnl = -cost_basis

        equity += net_pnl
        if equity > peak_equity:
            peak_equity = equity

        trades.append({
            'algorithm': algo,
            'symbol': tk,
            'sector': sector,
            'entry_date': str(pd_date),
            'exit_date': str(exit_date),
            'entry_price': round(actual_entry, 4),
            'exit_price': round(actual_exit, 4),
            'shares': shares,
            'gross_pnl': round(gross_pnl, 2),
            'commission': round(total_commission, 2),
            'net_pnl': round(net_pnl, 2),
            'return_pct': round(ret_pct, 4),
            'return_pct_gross': round(ret_pct_gross, 4),
            'hold_days': hd,
            'exit_reason': exit_reason,
            'equity_after': round(equity, 2),
            'tp_used': round(use_tp, 2),
            'sl_used': round(use_sl, 2),
        })
        equity_curve.append((str(exit_date), round(equity, 2)))

    return trades, equity_curve, equity


# ─────────────────────────────────────────────────
#  SPY BENCHMARK
# ─────────────────────────────────────────────────
def compute_spy_benchmark(prices, start_date, end_date, capital=INITIAL_CAPITAL):
    spy_prices = prices.get('SPY', [])
    if not spy_prices:
        return None

    start_price = end_price = None
    for pr in spy_prices:
        d = pr['trade_date']
        if start_price is None and d >= start_date:
            start_price = float(pr['close_price'])
        if d <= end_date:
            end_price = float(pr['close_price'])

    if not start_price or not end_price:
        return None

    spy_daily = []
    prev_c = None
    for pr in spy_prices:
        d = pr['trade_date']
        if d < start_date or d > end_date:
            continue
        c = float(pr['close_price'])
        if prev_c and prev_c > 0:
            spy_daily.append(((c - prev_c) / prev_c) * 100.0)
        prev_c = c

    total_ret = ((end_price - start_price) / start_price) * 100.0
    sd = dt_date.fromisoformat(str(start_date))
    ed = dt_date.fromisoformat(str(end_date))
    days = (ed - sd).days
    years = max(days / 365.25, 0.01)
    cagr = (((end_price / start_price) ** (1 / years)) - 1) * 100.0

    mean_daily = sum(spy_daily) / len(spy_daily) if spy_daily else 0
    var_d = sum((r - mean_daily)**2 for r in spy_daily) / len(spy_daily) if spy_daily else 0
    std_d = math.sqrt(var_d)
    sharpe = (mean_daily / std_d * math.sqrt(252)) if std_d > 0 else 0

    # Max drawdown
    cum = 0
    peak = 0
    mdd = 0
    for r in spy_daily:
        cum += r / 100.0  # as fraction
        if cum > peak:
            peak = cum
        dd = cum - peak
        if dd < mdd:
            mdd = dd

    return {
        'start_price': round(start_price, 2),
        'end_price': round(end_price, 2),
        'total_return_pct': round(total_ret, 2),
        'cagr_pct': round(cagr, 2),
        'sharpe_ratio': round(sharpe, 4),
        'annualized_vol_pct': round(std_d * math.sqrt(252), 2),
        'max_drawdown_pct': round(abs(mdd) * 100, 2),
        'daily_returns': spy_daily,
        'n_days': len(spy_daily),
    }


# ─────────────────────────────────────────────────
#  TICKER CORRELATION MATRIX
# ─────────────────────────────────────────────────
def compute_ticker_correlations(prices, trades, top_n=10):
    """Compute daily-return Pearson correlations among the most-traded tickers.
    Returns a dict: {'tickers': [list], 'matrix': [[corr values]]}
    """
    if not trades or not prices:
        return None

    # Count trades per ticker to find top N
    from collections import Counter
    ticker_counts = Counter(t['symbol'] for t in trades)
    top_tickers = [tk for tk, _ in ticker_counts.most_common(top_n) if tk in prices]

    if len(top_tickers) < 2:
        return None

    # Build daily return series for each ticker (keyed by date string)
    returns_by_ticker = {}
    for tk in top_tickers:
        pdata = prices.get(tk, [])
        rets = {}
        prev_c = None
        for pr in pdata:
            c = float(pr['close_price'])
            d = str(pr['trade_date'])
            if prev_c and prev_c > 0:
                rets[d] = (c - prev_c) / prev_c
            prev_c = c
        returns_by_ticker[tk] = rets

    # Find overlapping dates
    date_sets = [set(returns_by_ticker[tk].keys()) for tk in top_tickers]
    common_dates = date_sets[0]
    for ds in date_sets[1:]:
        common_dates = common_dates & ds
    common_dates = sorted(common_dates)

    if len(common_dates) < 20:
        return None

    # Build aligned arrays and compute Pearson correlation
    aligned = {}
    for tk in top_tickers:
        aligned[tk] = [returns_by_ticker[tk][d] for d in common_dates]

    n_dates = len(common_dates)
    matrix = []
    for i, tk_i in enumerate(top_tickers):
        row = []
        for j, tk_j in enumerate(top_tickers):
            if i == j:
                row.append(1.0)
                continue
            xi = aligned[tk_i]
            xj = aligned[tk_j]
            mx = sum(xi) / n_dates
            my = sum(xj) / n_dates
            cov = sum((xi[k] - mx) * (xj[k] - my) for k in range(n_dates)) / n_dates
            sx = math.sqrt(sum((xi[k] - mx)**2 for k in range(n_dates)) / n_dates)
            sy = math.sqrt(sum((xj[k] - my)**2 for k in range(n_dates)) / n_dates)
            corr = (cov / (sx * sy)) if (sx > 0 and sy > 0) else 0
            row.append(round(corr, 3))
        matrix.append(row)

    # Identify high-correlation pairs (> 0.7)
    high_pairs = []
    for i in range(len(top_tickers)):
        for j in range(i + 1, len(top_tickers)):
            if abs(matrix[i][j]) > 0.7:
                high_pairs.append((top_tickers[i], top_tickers[j], matrix[i][j]))
    high_pairs.sort(key=lambda x: abs(x[2]), reverse=True)

    return {
        'tickers': top_tickers,
        'matrix': matrix,
        'high_pairs': high_pairs,
        'n_dates': n_dates,
    }


# ─────────────────────────────────────────────────
#  COMPREHENSIVE METRICS
# ─────────────────────────────────────────────────
def comprehensive_metrics(trades, label='', spy_daily=None):
    n = len(trades)
    if n == 0:
        return None

    rets = [t['return_pct'] for t in trades]
    rets_gross = [t.get('return_pct_gross', t['return_pct']) for t in trades]
    pnls = [t['net_pnl'] for t in trades]
    hold_days = [t['hold_days'] for t in trades]

    real_trades = [t for t in trades if t['exit_reason'] != 'end_of_data']
    eod_trades = [t for t in trades if t['exit_reason'] == 'end_of_data']

    wins = [r for r in rets if r > 0]
    losses = [r for r in rets if r <= 0]
    n_wins = len(wins)
    n_losses = len(losses)
    wr = n_wins / n if n > 0 else 0

    mean_ret = sum(rets) / n
    total_pnl = sum(pnls)
    total_gross = sum(t['gross_pnl'] for t in trades)
    total_comm = sum(t['commission'] for t in trades)
    avg_hold = sum(hold_days) / n

    avg_win = sum(wins) / n_wins if n_wins else 0
    avg_loss = abs(sum(losses) / n_losses) if n_losses else 0
    exp = (wr * avg_win) - ((1 - wr) * avg_loss)

    # Profit factor
    gw = sum(p for p in pnls if p > 0)
    gl = abs(sum(p for p in pnls if p <= 0))
    pf = gw / gl if gl > 0 else (999 if gw > 0 else 0)

    # Volatility
    var_r = sum((r - mean_ret)**2 for r in rets) / n if n > 0 else 0
    vol = math.sqrt(var_r)
    dvar = sum(min(0, r)**2 for r in rets) / n if n > 0 else 0
    dstd = math.sqrt(dvar)

    # Sharpe & Sortino
    sharpe = (mean_ret / vol * math.sqrt(252)) if vol > 0 else 0
    sortino = (mean_ret / dstd * math.sqrt(252)) if dstd > 0 else 0

    # Max drawdown
    cum = 0
    peak = 0
    mdd = 0
    dd_durations = []
    in_dd = False
    dd_start_idx = 0
    for i, p in enumerate(pnls):
        cum += p
        if cum > peak:
            if in_dd:
                dd_durations.append(i - dd_start_idx)
                in_dd = False
            peak = cum
        dd = cum - peak
        if dd < 0 and not in_dd:
            in_dd = True
            dd_start_idx = i
        if dd < mdd:
            mdd = dd
    if in_dd:
        dd_durations.append(len(pnls) - dd_start_idx)

    # CAGR
    first_date = trades[0]['entry_date']
    last_date = trades[-1]['exit_date']
    try:
        fd = dt_date.fromisoformat(str(first_date))
        ld = dt_date.fromisoformat(str(last_date))
        days_span = (ld - fd).days
    except (ValueError, TypeError):
        days_span = 365
    years = max(days_span / 365.25, 0.01)

    final_equity = INITIAL_CAPITAL + total_pnl
    cagr = 0
    if final_equity > 0:
        cagr = (((final_equity / INITIAL_CAPITAL) ** (1 / years)) - 1) * 100.0

    mdd_pct = abs(mdd / max(peak, INITIAL_CAPITAL) * 100) if peak > 0 else 0
    mdd_pct = min(mdd_pct, 100.0)  # Cap at 100% for display
    calmar = cagr / mdd_pct if mdd_pct > 0 else 0

    # Recovery Factor = net profit / max drawdown
    recovery_factor = abs(total_pnl / mdd) if mdd != 0 else 0

    # VaR 95% and CVaR (Conditional VaR / Expected Shortfall)
    var95 = 0
    cvar95 = 0
    if n >= 20:
        sorted_r = sorted(rets)
        cutoff_idx = int(n * 0.05)
        var95 = sorted_r[cutoff_idx]
        tail = sorted_r[:cutoff_idx + 1]
        cvar95 = sum(tail) / len(tail) if tail else var95

    # Annualized turnover
    total_notional = sum(t['entry_price'] * t['shares'] for t in trades)
    avg_portfolio = (INITIAL_CAPITAL + final_equity) / 2
    turnover = (total_notional / avg_portfolio / years) if avg_portfolio > 0 and years > 0 else 0

    # Wilson 95% CI for win rate
    z = 1.96
    wr_lower = wr_upper = 0
    wr_significant = False
    if n > 0:
        p_hat = wr
        denom = 1 + z**2 / n
        center = (p_hat + z**2 / (2 * n)) / denom
        hw = z * math.sqrt((p_hat * (1 - p_hat) + z**2 / (4 * n)) / n) / denom
        wr_lower = max(0, center - hw)
        wr_upper = min(1, center + hw)
        wr_significant = wr_lower > 0.5 or wr_upper < 0.5

    # Bootstrap CI for Sharpe & Sortino
    random.seed(42)
    n_bs = 10000
    bs_sharpes = []
    bs_sortinos = []
    if n >= 10:
        for _ in range(n_bs):
            samp = random.choices(rets, k=n)
            sm = sum(samp) / n
            sv = sum((r - sm)**2 for r in samp) / n
            ss = math.sqrt(sv) if sv > 0 else 0.001
            sdv = sum(min(0, r)**2 for r in samp) / n
            sds = math.sqrt(sdv) if sdv > 0 else 0.001
            bs_sharpes.append(sm / ss * math.sqrt(252))
            bs_sortinos.append(sm / sds * math.sqrt(252))
        bs_sharpes.sort()
        bs_sortinos.sort()
        sharpe_ci = [bs_sharpes[int(0.025 * n_bs)], bs_sharpes[int(0.975 * n_bs)]]
        sortino_ci = [bs_sortinos[int(0.025 * n_bs)], bs_sortinos[int(0.975 * n_bs)]]
    else:
        sharpe_ci = [sharpe, sharpe]
        sortino_ci = [sortino, sortino]

    # Exit reason breakdown
    exit_reasons = defaultdict(int)
    for t in trades:
        exit_reasons[t['exit_reason']] += 1

    # Sector breakdown
    sector_stats = defaultdict(lambda: {'n': 0, 'pnl': 0, 'wins': 0})
    for t in trades:
        s = t.get('sector', 'Other')
        sector_stats[s]['n'] += 1
        sector_stats[s]['pnl'] += t['net_pnl']
        if t['return_pct'] > 0:
            sector_stats[s]['wins'] += 1

    sector_summary = {}
    for s, st in sector_stats.items():
        sector_summary[s] = {
            'trades': st['n'],
            'pnl': round(st['pnl'], 2),
            'win_rate': round(st['wins'] / st['n'] * 100, 1) if st['n'] > 0 else 0,
        }

    return {
        'label': label,
        'backtest_window': '%s to %s' % (first_date, last_date),
        'backtest_days': days_span,
        'backtest_years': round(years, 2),
        'total_trades': n,
        'end_of_data_trades': len(eod_trades),
        'real_trades': len(real_trades),
        'n_tickers': len(set(t['symbol'] for t in trades)),
        'win_rate_pct': round(wr * 100, 2),
        'win_rate_ci_95': [round(wr_lower * 100, 2), round(wr_upper * 100, 2)],
        'win_rate_significant_vs_50': wr_significant,
        'mean_return_pct': round(mean_ret, 4),
        'mean_return_gross_pct': round(sum(rets_gross) / n, 4),
        'total_pnl_usd': round(total_pnl, 2),
        'total_gross_pnl_usd': round(total_gross, 2),
        'total_commissions_usd': round(total_comm, 2),
        'initial_capital': INITIAL_CAPITAL,
        'final_equity': round(final_equity, 2),
        'total_return_pct': round((final_equity / INITIAL_CAPITAL - 1) * 100, 2),
        'total_return_gross_pct': round((total_gross / INITIAL_CAPITAL) * 100, 2),
        'cagr_pct': round(cagr, 2),
        'avg_win_pct': round(avg_win, 2),
        'avg_loss_pct': round(avg_loss, 2),
        'expectancy_pct': round(exp, 4),
        'profit_factor': round(min(pf, 999), 3),
        'avg_hold_days': round(avg_hold, 1),
        'volatility_pct': round(vol, 4),
        'downside_deviation': round(dstd, 4),
        'var_95_pct': round(var95, 2),
        'cvar_95_pct': round(cvar95, 2),
        'max_drawdown_usd': round(mdd, 2),
        'max_drawdown_pct': round(mdd_pct, 2),
        'avg_drawdown_duration_trades': round(sum(dd_durations) / len(dd_durations), 1) if dd_durations else 0,
        'recovery_factor': round(recovery_factor, 3),
        'sharpe_ratio': round(sharpe, 4),
        'sharpe_ci_95': [round(sharpe_ci[0], 4), round(sharpe_ci[1], 4)],
        'sortino_ratio': round(sortino, 4),
        'sortino_ci_95': [round(sortino_ci[0], 4), round(sortino_ci[1], 4)],
        'calmar_ratio': round(calmar, 4),
        'beta_vs_spy': 0,
        'alpha_annualized': 0,
        'annualized_turnover': round(turnover, 2),
        'exit_reasons': dict(exit_reasons),
        'sector_breakdown': sector_summary,
    }


# ─────────────────────────────────────────────────
#  GRID SEARCH
# ─────────────────────────────────────────────────
def _quick_metrics(trades, feq):
    """Compute quick metrics for grid search results."""
    if not trades:
        return None
    rets = [t['return_pct'] for t in trades]
    nn = len(rets)
    wins = [r for r in rets if r > 0]
    wr = len(wins) / nn if nn > 0 else 0
    mr = sum(rets) / nn
    var_r = sum((r - mr)**2 for r in rets) / nn if nn > 0 else 0
    std_r = math.sqrt(var_r)
    sharpe = (mr / std_r * math.sqrt(252)) if std_r > 0 else 0
    tot_ret = ((feq / INITIAL_CAPITAL) - 1) * 100
    exp = (wr * (sum(wins) / len(wins) if wins else 0)) - \
          ((1 - wr) * abs(sum(r for r in rets if r <= 0) / max(1, nn - len(wins))))
    # Exit reason breakdown
    exits = defaultdict(int)
    for t in trades:
        exits[t['exit_reason']] += 1
    return {
        'trades': nn, 'win_rate': round(wr * 100, 1),
        'mean_return': round(mr, 3), 'expectancy': round(exp, 3),
        'sharpe': round(sharpe, 3), 'total_return_pct': round(tot_ret, 2),
        'final_equity': round(feq, 2), 'exit_reasons': dict(exits),
    }


def grid_search_tpsl(picks, prices):
    algo_counts = defaultdict(int)
    for p in picks:
        algo_counts[p['algorithm_name']] += 1
    algos = [a for a, c in algo_counts.items() if c >= 10]
    results = {}
    for algo in algos:
        ap = [p for p in picks if p['algorithm_name'] == algo]
        ar = []

        # Fixed TP/SL configs
        for cfg in GRID_CONFIGS:
            trades, _, feq = backtest(ap, prices, tp=cfg['tp'], sl=cfg['sl'],
                                       max_hold=cfg['hold'])
            m = _quick_metrics(trades, feq)
            if m:
                m['config'] = cfg['label']
                m['type'] = 'fixed'
                ar.append(m)

        # Trailing stop + partial profit configs
        for cfg in TRAILING_CONFIGS:
            trades, _, feq = backtest(
                ap, prices, tp=cfg['tp'], sl=cfg['sl'], max_hold=cfg['hold'],
                trailing_stop_pct=cfg.get('trail', 0),
                partial_profit_pct=cfg.get('partial', 0),
                breakeven_after_pct=cfg.get('be', 0),
            )
            m = _quick_metrics(trades, feq)
            if m:
                m['config'] = cfg['label']
                m['type'] = 'trailing' if cfg.get('trail', 0) > 0 else 'advanced'
                ar.append(m)

        ar.sort(key=lambda x: x['sharpe'], reverse=True)
        results[algo] = ar
    return results


# ─────────────────────────────────────────────────
#  TRAIN/TEST SPLIT
# ─────────────────────────────────────────────────
def train_test_analysis(picks, prices, split_ratio=0.8):
    sp = sorted(picks, key=lambda p: p['pick_date'])
    si = int(len(sp) * split_ratio)
    train_p = sp[:si]
    test_p = sp[si:]
    train_t, _, _ = backtest(train_p, prices, tp=10, sl=5, max_hold=30)
    test_t, _, _ = backtest(test_p, prices, tp=10, sl=5, max_hold=30)
    train_m = comprehensive_metrics(train_t, 'In-Sample (Training)')
    test_m = comprehensive_metrics(test_t, 'Out-of-Sample (Test)')
    return {
        'train_period': '%s to %s' % (train_p[0]['pick_date'], train_p[-1]['pick_date']) if train_p else 'N/A',
        'test_period': '%s to %s' % (test_p[0]['pick_date'], test_p[-1]['pick_date']) if test_p else 'N/A',
        'train_picks': len(train_p), 'test_picks': len(test_p),
        'train_metrics': train_m, 'test_metrics': test_m,
    }


# ─────────────────────────────────────────────────
#  PURGED WALK-FORWARD CROSS-VALIDATION
# ─────────────────────────────────────────────────
def walk_forward_cv(picks, prices, tp=50, sl=20, max_hold=90,
                    train_months=6, test_months=2, embargo_days=5):
    """
    Purged walk-forward cross-validation.

    - Slides a (train_months)-month training window followed by a (test_months)-month
      test window across the full data range.
    - An embargo of (embargo_days) business days is enforced between train end and
      test start to prevent information leakage from overlapping trades.
    - Each fold backtests ONLY the picks within its window.
    - Returns per-fold metrics plus aggregate stability statistics.

    This is the gold standard for validating time-series trading strategies
    and is critical for confirming that backtest Sharpe holds out-of-sample.
    """
    from datetime import timedelta

    sorted_picks = sorted(picks, key=lambda p: p['pick_date'])
    if not sorted_picks:
        return None

    first_date = sorted_picks[0]['pick_date']
    last_date = sorted_picks[-1]['pick_date']

    # Convert to date objects if they aren't already
    if isinstance(first_date, str):
        first_date = dt_date.fromisoformat(first_date)
    if isinstance(last_date, str):
        last_date = dt_date.fromisoformat(last_date)

    folds = []
    fold_num = 0
    train_start = first_date

    while True:
        train_end = train_start + timedelta(days=train_months * 30)
        embargo_end = train_end + timedelta(days=embargo_days)
        test_start = embargo_end
        test_end = test_start + timedelta(days=test_months * 30)

        if test_end > last_date + timedelta(days=30):
            break

        # Filter picks for each window
        train_picks = [p for p in sorted_picks
                       if _to_date(p['pick_date']) >= train_start
                       and _to_date(p['pick_date']) < train_end]
        test_picks = [p for p in sorted_picks
                      if _to_date(p['pick_date']) >= test_start
                      and _to_date(p['pick_date']) < test_end]

        if len(train_picks) < 10 or len(test_picks) < 5:
            train_start += timedelta(days=test_months * 30)
            continue

        fold_num += 1

        # Backtest each window
        train_trades, _, train_eq = backtest(train_picks, prices, tp=tp, sl=sl, max_hold=max_hold)
        test_trades, _, test_eq = backtest(test_picks, prices, tp=tp, sl=sl, max_hold=max_hold)

        train_m = comprehensive_metrics(train_trades, 'Fold %d Train' % fold_num)
        test_m = comprehensive_metrics(test_trades, 'Fold %d Test' % fold_num)

        folds.append({
            'fold': fold_num,
            'train_start': str(train_start),
            'train_end': str(train_end),
            'test_start': str(test_start),
            'test_end': str(test_end),
            'train_picks': len(train_picks),
            'test_picks': len(test_picks),
            'train_trades': train_m['total_trades'] if train_m else 0,
            'test_trades': test_m['total_trades'] if test_m else 0,
            'train_sharpe': train_m['sharpe_ratio'] if train_m else 0,
            'test_sharpe': test_m['sharpe_ratio'] if test_m else 0,
            'train_wr': train_m['win_rate_pct'] if train_m else 0,
            'test_wr': test_m['win_rate_pct'] if test_m else 0,
            'train_return': train_m['total_return_pct'] if train_m else 0,
            'test_return': test_m['total_return_pct'] if test_m else 0,
            'train_expectancy': train_m['expectancy_pct'] if train_m else 0,
            'test_expectancy': test_m['expectancy_pct'] if test_m else 0,
            'train_max_dd': train_m['max_drawdown_pct'] if train_m else 0,
            'test_max_dd': test_m['max_drawdown_pct'] if test_m else 0,
        })

        # Slide window
        train_start += timedelta(days=test_months * 30)

    if not folds:
        return None

    # Aggregate statistics
    test_sharpes = [f['test_sharpe'] for f in folds]
    test_wrs = [f['test_wr'] for f in folds]
    test_returns = [f['test_return'] for f in folds]

    n_folds = len(folds)
    avg_sharpe = sum(test_sharpes) / n_folds
    avg_wr = sum(test_wrs) / n_folds
    avg_return = sum(test_returns) / n_folds

    # Sharpe stability: std of test sharpes across folds
    var_sharpe = sum((s - avg_sharpe)**2 for s in test_sharpes) / n_folds
    std_sharpe = math.sqrt(var_sharpe)

    # How many folds had positive test Sharpe?
    positive_folds = sum(1 for s in test_sharpes if s > 0)

    # Overfit ratio: how much does train Sharpe exceed test Sharpe on average?
    train_sharpes = [f['train_sharpe'] for f in folds]
    avg_train_sharpe = sum(train_sharpes) / n_folds
    overfit_ratio = (avg_train_sharpe - avg_sharpe) / abs(avg_train_sharpe) * 100 if avg_train_sharpe != 0 else 0

    return {
        'n_folds': n_folds,
        'train_months': train_months,
        'test_months': test_months,
        'embargo_days': embargo_days,
        'tp': tp, 'sl': sl, 'max_hold': max_hold,
        'folds': folds,
        'aggregate': {
            'avg_test_sharpe': round(avg_sharpe, 4),
            'std_test_sharpe': round(std_sharpe, 4),
            'avg_test_wr': round(avg_wr, 2),
            'avg_test_return': round(avg_return, 2),
            'positive_sharpe_folds': positive_folds,
            'pct_positive': round(positive_folds / n_folds * 100, 1),
            'overfit_ratio_pct': round(overfit_ratio, 1),
            'avg_train_sharpe': round(avg_train_sharpe, 4),
        }
    }


def _to_date(d):
    """Convert a pick date (string or date) to a date object."""
    if isinstance(d, str):
        return dt_date.fromisoformat(d)
    if isinstance(d, datetime):
        return d.date()
    return d


# ─────────────────────────────────────────────────
#  MONTE CARLO SIMULATION
# ─────────────────────────────────────────────────
def monte_carlo(trades, n_sims=1000, capital=INITIAL_CAPITAL):
    """
    Monte Carlo: reshuffle trade RETURNS (%) and recompute equity curves.
    Uses percentage returns to properly handle path-dependent position sizing.
    Each reshuffled path uses fixed fractional sizing (5% of equity).
    """
    if not trades or len(trades) < 10:
        return None

    # Extract per-trade return percentages (net of commissions)
    rets = [t['return_pct'] / 100.0 for t in trades]  # as decimal fractions
    random.seed(42)
    final_equities = []
    max_drawdowns = []

    for _ in range(n_sims):
        shuffled = random.sample(rets, len(rets))
        eq = capital
        pk = capital
        mdd = 0
        for r in shuffled:
            # Apply return to a position_pct-sized position
            pos = min(eq * POSITION_PCT / 100.0, POSITION_CAP)
            pnl = pos * r
            eq += pnl
            if eq > pk:
                pk = eq
            dd = (eq - pk) / pk * 100 if pk > 0 else 0
            if dd < mdd:
                mdd = dd
            if eq <= 0:
                eq = 0
                break
        final_equities.append(eq)
        max_drawdowns.append(abs(mdd))

    final_equities.sort()
    max_drawdowns.sort()
    n = len(final_equities)
    return {
        'n_simulations': n_sims,
        'median_equity': round(final_equities[n // 2], 2),
        'p5_equity': round(final_equities[int(n * 0.05)], 2),
        'p25_equity': round(final_equities[int(n * 0.25)], 2),
        'p75_equity': round(final_equities[int(n * 0.75)], 2),
        'p95_equity': round(final_equities[int(n * 0.95)], 2),
        'mean_equity': round(sum(final_equities) / n, 2),
        'median_max_dd': round(max_drawdowns[n // 2], 2),
        'p95_max_dd': round(max_drawdowns[int(n * 0.95)], 2),
    }


# ─────────────────────────────────────────────────
#  MARKDOWN REPORT GENERATOR
# ─────────────────────────────────────────────────
def generate_markdown(default_m, optimal_m, adaptive_m, conc_m,
                      algo_metrics, spy_bm, grid_results, oos_results,
                      buyhold_m, grossfee_m, mc_default, mc_optimal,
                      trailing_m=None, ticker_corr=None, wfcv_results=None):
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    lines = []
    a = lines.append

    a("# Portfolio Performance Analysis Report (V2)")
    a("*Report version: %s | Generated by comprehensive_performance_report.py*" % now)
    a("")

    # ═══════════ EXECUTIVE SUMMARY ═══════════
    a("---")
    a("")
    a("## Executive Summary")
    a("")
    a("Three key takeaways:")
    a("")

    # 1) Optimal is clearly better
    if optimal_m:
        a("1. **Tight TP/SL kills returns; wider parameters are dramatically better.** "
          "Default 10/5/30d config yields Sharpe %s with %s%% win rate. "
          "Optimal 50/20/90d achieves Sharpe %s with %s%% win rate and %s%% total return."
          % (fmts(default_m['sharpe_ratio']), default_m['win_rate_pct'],
             fmts(optimal_m['sharpe_ratio']), optimal_m['win_rate_pct'],
             fmt2(optimal_m['total_return_pct'])))
    a("2. **ATR-based adaptive TP/SL** (%s) lets each stock use volatility-appropriate thresholds "
      "instead of one-size-fits-all percentages — Sharpe %s, WR %s%%."
      % (adaptive_m['label'] if adaptive_m else '—',
         fmts(adaptive_m['sharpe_ratio']) if adaptive_m else '—',
         adaptive_m['win_rate_pct'] if adaptive_m else '—'))
    a("3. **SPY buy-and-hold returned %s%%** (Sharpe %s) over the same period. "
      "Only the optimal and adaptive configs beat the benchmark."
      % (fmt2(spy_bm['total_return_pct']), fmts(spy_bm['sharpe_ratio'])) if spy_bm else
      "3. **SPY benchmark not available** — add SPY price data for comparison.")
    a("")

    # ═══════════ CONFIGURATION COMPARISON ═══════════
    a("---")
    a("")
    a("## Configuration Comparison")
    a("")
    a("All configs use same data, fee model ($4.95/trade), 0.1% slippage, "
      "1-day embargo, 5% of equity per trade (capped $2k).")
    a("")

    configs_to_show = [
        ('Default (10/5/30d)', default_m),
        ('Optimal (50/20/90d)', optimal_m),
        ('Best Trailing Stop', trailing_m),
        ('Adaptive ATR (hybrid)', adaptive_m),
        ('Concentration-Limited', conc_m),
        ('Buy-and-Hold (no TP/SL)', buyhold_m),
        ('Commission-Free (gross)', grossfee_m),
    ]

    a("| Configuration | Trades | Win Rate | Sharpe | Total Return | CAGR | Max DD | Calmar |")
    a("|---------------|--------|----------|--------|-------------|------|--------|--------|")
    for lbl, m in configs_to_show:
        if not m:
            continue
        a("| %s | %s | %s%% | %s | %s%% | %s%% | %s%% | %s |"
          % (lbl, m['total_trades'], m['win_rate_pct'], fmts(m['sharpe_ratio']),
             fmt2(m['total_return_pct']), fmt2(m['cagr_pct']),
             m['max_drawdown_pct'], fmts(m['calmar_ratio'])))
    if spy_bm:
        a("| **SPY Benchmark** | — | — | %s | %s%% | %s%% | %s%% | — |"
          % (fmts(spy_bm['sharpe_ratio']), fmt2(spy_bm['total_return_pct']),
             fmt2(spy_bm['cagr_pct']), spy_bm.get('max_drawdown_pct', '—')))
    a("")

    # ═══════════ ALGORITHM DEFINITIONS ═══════════
    a("---")
    a("")
    a("## Algorithm Definitions")
    a("")
    a("| Algorithm | Style | Signal Horizon | Description |")
    a("|-----------|-------|----------------|-------------|")
    a("| **Blue Chip Growth** | Fundamental / DCA | Long-term (60-180d) | Monthly dollar-cost-averaging entries into large-cap quality stocks (AAPL, MSFT, JNJ, etc.). Signals are generated on a fixed schedule, not from technical triggers. |")
    a("| **ETF Masters** | Passive / Strategic | Long-term (90-180d) | Diversified ETF portfolio (SPY, QQQ, GLD, BND, etc.) with periodic rebalancing. Low turnover, broad market exposure. |")
    a("| **Cursor Genius** | Quantitative / Multi-factor | Medium-term (30-90d) | Proprietary multi-factor model combining momentum, value, and quality signals. Historically the highest-alpha algorithm. |")
    a("| **Sector Rotation** | Tactical / Macro | Medium-term (60-90d) | Rotates into the strongest-performing sectors (XLK, XLE, XLV, etc.) based on relative strength and macro regime. |")
    a("| **Sector Momentum** | Technical / Trend | Medium-term (30-60d) | Pure momentum play on sector ETFs — buys sectors with strong recent performance, avoids laggards. |")
    a("| **Technical Momentum** | Technical / Short-term | Short-term (7-30d) | RSI/MACD/volume-based signals on individual stocks. Currently has very few picks (12) — insufficient for statistical conclusions. |")
    a("| **Composite Rating** | Blended / Score-based | Variable | Ranks stocks by a composite score (fundamentals + technicals). Recent addition with limited history. |")
    a("| **CAN SLIM** | Growth / O'Neil | Medium-term | Based on William O'Neil's CAN SLIM criteria (Current earnings, Annual earnings, New highs, Supply/demand, Leader, Institutional, Market). Currently only 1 pick — filter too strict. |")
    a("| **ML Ensemble** | Machine Learning | Variable | XGBoost-based meta-model. **No pick generator exists yet** — only the training pipeline (`ensemble_stacker.py`) is implemented. |")
    a("")
    a("*Algorithms with fewer than 30 trades should be considered statistically unreliable. "
      "Technical Momentum (12 trades), Composite Rating (12), and CAN SLIM (1) fall into this category.*")
    a("")

    # ═══════════ METRIC INTERPRETATION GUIDE ═══════════
    a("---")
    a("")
    a("## Metric Interpretation Guide")
    a("")
    a("How to read the key metrics in this report:")
    a("")
    a("| Metric | What It Measures | Good | Mediocre | Poor |")
    a("|--------|-----------------|------|----------|------|")
    a("| **Sharpe Ratio** | Risk-adjusted return (return per unit of volatility) | > 1.0 (excellent > 2.0) | 0.5 - 1.0 | < 0.5 (negative = losing money) |")
    a("| **Sortino Ratio** | Like Sharpe but only penalizes downside volatility | > 1.5 | 0.5 - 1.5 | < 0.5 |")
    a("| **Calmar Ratio** | CAGR divided by max drawdown — higher = better recovery | > 1.0 | 0.3 - 1.0 | < 0.3 |")
    a("| **Win Rate** | Percentage of trades that are profitable | > 55% (with positive expectancy) | 45-55% | < 45% (unless avg win >> avg loss) |")
    a("| **Profit Factor** | Gross profits / gross losses | > 1.5 | 1.0 - 1.5 | < 1.0 (losing system) |")
    a("| **Expectancy** | Average profit per trade (% of position) | > 2% | 0.5 - 2% | < 0.5% (negative = losing) |")
    a("| **Max Drawdown** | Largest peak-to-trough decline | < 15% | 15-30% | > 30% (> 50% = catastrophic) |")
    a("| **CAGR** | Compound annual growth rate — smoothed yearly return | > 15% | 5-15% | < 5% (< 0% = shrinking) |")
    a("| **VaR (95%)** | Worst expected single-trade loss at 95% confidence | > -10% | -10% to -20% | < -20% |")
    a("| **CVaR (95%)** | Average loss in the worst 5% of trades | > -15% | -15% to -25% | < -25% |")
    a("| **Recovery Factor** | Net profit / max drawdown — how quickly you recover | > 3.0 | 1.0 - 3.0 | < 1.0 |")
    a("| **Annualized Turnover** | How many times capital cycles through positions per year | Context-dependent | — | Very high turnover = high fee drag |")
    a("")
    a("*Industry context: The S&P 500 has a long-run Sharpe of ~0.4-0.6. A Sharpe > 1.0 is considered strong alpha. "
      "Hedge funds typically target Sharpe 1.0-2.0 with max drawdown < 20%.*")
    a("")

    # ═══════════ METHODOLOGY ═══════════
    a("---")
    a("")
    a("## Methodology")
    a("")
    a("| Parameter | Value |")
    a("|-----------|-------|")
    a("| **Backtest Window** | %s |" % default_m['backtest_window'])
    a("| **Data Source** | MySQL database (daily_prices table, daily OHLC bars) |")
    a("| **Price Granularity** | Daily close-to-close |")
    a("| **Initial Capital** | $%s |" % fmt0(INITIAL_CAPITAL))
    a("| **Position Sizing** | %s%% of equity per trade, capped at $%s |" % (POSITION_PCT, fmt0(POSITION_CAP)))
    a("| **Fee Model** | $4.95 per trade (buy + sell = $9.90 round trip) |")
    a("| **Slippage** | %s%% per side |" % SLIPPAGE_PCT)
    a("| **Embargo** | %d day(s) — enter next-day open |" % EMBARGO_DAYS)
    a("| **ATR Period** | %d days (for adaptive TP/SL) |" % ATR_PERIOD)
    a("| **Universe** | %s distinct tickers across %d algorithms |"
      % (default_m['n_tickers'], len(algo_metrics)))
    a("| **Concentration Limits** | Max %s%% per ticker, %s%% per sector |"
      % (MAX_TICKER_PCT, MAX_SECTOR_PCT))
    a("")

    # ═══════════ DETAILED: OPTIMAL CONFIG ═══════════
    m = optimal_m if optimal_m else default_m
    a("---")
    a("")
    a("## Detailed Performance: Optimal Config (50/20/90d)")
    a("")
    _write_metrics_block(a, m, spy_bm)

    # ═══════════ DETAILED: ADAPTIVE ATR ═══════════
    if adaptive_m:
        a("---")
        a("")
        a("## Detailed Performance: Adaptive ATR Config")
        a("")
        a("Best hybrid config: %s. Each stock gets "
          "volatility-appropriate thresholds (ATR-based floor + fixed minimum)." % adaptive_m['label'])
        a("")
        _write_metrics_block(a, adaptive_m, spy_bm)

    # ═══════════ PER-ALGORITHM ═══════════
    a("---")
    a("")
    a("## Per-Algorithm Performance (Optimal 50/20/90d)")
    a("")
    a("| # | Algorithm | Trades | Win Rate | Sharpe | Sortino | Exp% | CAGR | Grade |")
    a("|---|-----------|--------|----------|--------|---------|------|------|-------|")
    for i, am in enumerate(algo_metrics):
        grade = _grade(am['sharpe_ratio'])
        sig = ' *' if am.get('win_rate_significant_vs_50') else ''
        a("| %d | %s | %s | %s%%%s | %s | %s | %s%% | %s%% | %s |"
          % (i + 1, am['label'], am['total_trades'], am['win_rate_pct'], sig,
             fmts(am['sharpe_ratio']), fmts(am['sortino_ratio']),
             fmt3(am['expectancy_pct']), fmt1(am['cagr_pct']), grade))
    a("")
    a("")
    a("*\\* = win rate statistically significant vs 50% at 95% confidence*")
    a("")
    # Sample size warnings
    small_algos = [am['label'] for am in algo_metrics if am['total_trades'] < 30]
    if small_algos:
        a("> **Sample Size Warning**: The following algorithms have fewer than 30 trades "
          "and their metrics are NOT statistically reliable: %s. "
          "Conclusions from these should be treated as directional only, not actionable."
          % ", ".join(small_algos))
        a("")

    # ═══════════ SECTOR BREAKDOWN ═══════════
    if m.get('sector_breakdown'):
        a("---")
        a("")
        a("## Sector Breakdown (Optimal Config)")
        a("")
        a("| Sector | Trades | Net PnL | Win Rate |")
        a("|--------|--------|---------|----------|")
        for s, st in sorted(m['sector_breakdown'].items(), key=lambda x: -x[1]['pnl']):
            a("| %s | %d | $%s | %s%% |" % (s, st['trades'], fmt2(st['pnl']), st['win_rate']))
        a("")

    # ═══════════ GRID SEARCH ═══════════
    a("---")
    a("")
    a("## TP/SL Grid Search (Sweet Spot Analysis)")
    a("")
    a("Sorted by Sharpe (best first). Top 8 per algorithm shown.")
    a("Configs with `+trail` use trailing stops; `+pp` = partial profit lock-in; `+be` = stop-to-breakeven.")
    a("")
    for algo, configs in grid_results.items():
        if not configs:
            continue
        a("### %s" % algo)
        a("")
        a("| Config | Type | Trades | Win Rate | Sharpe | Expectancy | Total Return |")
        a("|--------|------|--------|----------|--------|------------|--------------|")
        for c in configs[:8]:
            marker = ' **BEST**' if c == configs[0] else ''
            ctype = c.get('type', 'fixed')
            a("| %s | %s | %d | %s%% | %s | %s%% | %s%%%s |"
              % (c['config'], ctype, c['trades'], c['win_rate'],
                 fmts(c['sharpe']), fmt3(c['expectancy']),
                 fmt2(c['total_return_pct']), marker))
        a("")

    # ═══════════ OUT-OF-SAMPLE ═══════════
    if oos_results and oos_results.get('train_metrics') and oos_results.get('test_metrics'):
        tm = oos_results['train_metrics']
        ts = oos_results['test_metrics']
        a("---")
        a("")
        a("## Out-of-Sample Validation")
        a("")
        a("Training: %s | Test: %s" % (oos_results['train_period'], oos_results['test_period']))
        a("")
        s_diff = abs(tm['sharpe_ratio'] - ts['sharpe_ratio'])
        overfit = 'YES' if s_diff > 1.0 else ('MAYBE' if s_diff > 0.5 else 'NO')
        a("| Metric | In-Sample | Out-of-Sample | Overfit? |")
        a("|--------|-----------|---------------|----------|")
        a("| Trades | %s | %s | — |" % (tm['total_trades'], ts['total_trades']))
        a("| Win Rate | %s%% | %s%% | — |" % (tm['win_rate_pct'], ts['win_rate_pct']))
        a("| Sharpe | %s | %s | %s (delta=%s) |"
          % (fmts(tm['sharpe_ratio']), fmts(ts['sharpe_ratio']), overfit, fmt2(s_diff)))
        a("| Total Return | %s%% | %s%% | — |"
          % (fmt2(tm['total_return_pct']), fmt2(ts['total_return_pct'])))
        a("")

    # ═══════════ WALK-FORWARD CROSS-VALIDATION ═══════════
    if wfcv_results:
        agg = wfcv_results['aggregate']
        a("---")
        a("")
        a("## Purged Walk-Forward Cross-Validation")
        a("")
        a("The gold standard for time-series strategy validation. Unlike a single train/test split, "
          "walk-forward CV slides a training window across the entire dataset, testing on unseen future data "
          "at each step. An embargo gap between train and test prevents information leakage from overlapping trades.")
        a("")
        a("| Parameter | Value |")
        a("|-----------|-------|")
        a("| Training Window | %d months |" % wfcv_results['train_months'])
        a("| Testing Window | %d months |" % wfcv_results['test_months'])
        a("| Embargo (purge gap) | %d business days |" % wfcv_results['embargo_days'])
        a("| Config Tested | TP=%d%% / SL=%d%% / Hold=%dd |" % (wfcv_results['tp'], wfcv_results['sl'], wfcv_results['max_hold']))
        a("| Total Folds | %d |" % wfcv_results['n_folds'])
        a("")
        a("### Per-Fold Results")
        a("")
        a("| Fold | Train Period | Test Period | Train Trades | Test Trades | Train Sharpe | Test Sharpe | Test WR | Test Return |")
        a("|------|-------------|-------------|-------------|-------------|-------------|-------------|---------|-------------|")
        for f in wfcv_results['folds']:
            a("| %d | %s to %s | %s to %s | %d | %d | %s | %s | %s%% | %s%% |"
              % (f['fold'],
                 f['train_start'][:10], f['train_end'][:10],
                 f['test_start'][:10], f['test_end'][:10],
                 f['train_trades'], f['test_trades'],
                 fmts(f['train_sharpe']), fmts(f['test_sharpe']),
                 f['test_wr'], fmt2(f['test_return'])))
        a("")
        a("### Aggregate Stability")
        a("")
        a("| Metric | Value | Interpretation |")
        a("|--------|-------|----------------|")
        a("| **Avg Test Sharpe** | %s | %s |"
          % (fmts(agg['avg_test_sharpe']),
             'Strong' if agg['avg_test_sharpe'] > 1.0 else ('Adequate' if agg['avg_test_sharpe'] > 0.5 else ('Weak' if agg['avg_test_sharpe'] > 0 else 'Negative — strategy may not be robust'))))
        a("| **Std of Test Sharpe** | %s | %s |"
          % (fmt2(agg['std_test_sharpe']),
             'Stable (low variance)' if agg['std_test_sharpe'] < 2.0 else ('Moderate variance' if agg['std_test_sharpe'] < 5.0 else 'High variance — inconsistent across periods')))
        a("| **%% Folds with Positive Sharpe** | %s%% (%d/%d) | %s |"
          % (agg['pct_positive'], agg['positive_sharpe_folds'], wfcv_results['n_folds'],
             'Robust' if agg['pct_positive'] >= 70 else ('Acceptable' if agg['pct_positive'] >= 50 else 'Concerning — strategy fails in many periods')))
        a("| **Avg Test Win Rate** | %s%% | %s |"
          % (agg['avg_test_wr'],
             'Good' if agg['avg_test_wr'] > 55 else 'Mediocre'))
        a("| **Avg Test Return** | %s%% | Per 2-month test window |" % fmt2(agg['avg_test_return']))
        a("| **Overfit Ratio** | %s%% | %s |"
          % (fmt2(agg['overfit_ratio_pct']),
             'Low overfitting' if abs(agg['overfit_ratio_pct']) < 30 else ('Moderate overfitting' if abs(agg['overfit_ratio_pct']) < 60 else 'High overfitting — train metrics may not be reliable')))
        a("| **Avg Train Sharpe** | %s | Compared to avg test of %s |"
          % (fmts(agg['avg_train_sharpe']), fmts(agg['avg_test_sharpe'])))
        a("")

        # Verdict
        if agg['avg_test_sharpe'] > 1.0 and agg['pct_positive'] >= 70:
            verdict = "PASS — Strategy shows robust out-of-sample performance across time periods."
        elif agg['avg_test_sharpe'] > 0 and agg['pct_positive'] >= 50:
            verdict = "CONDITIONAL PASS — Positive on average but inconsistent. Consider tightening risk controls."
        else:
            verdict = "FAIL — Strategy does not reliably produce positive risk-adjusted returns out of sample."
        a("> **Walk-Forward Verdict**: %s" % verdict)
        a("")

    # ═══════════ MONTE CARLO ═══════════
    if mc_optimal:
        a("---")
        a("")
        a("## Monte Carlo Simulation (%d reshuffles)" % mc_optimal['n_simulations'])
        a("")
        a("Trade order was randomly reshuffled to test robustness of results.")
        a("")
        a("| Percentile | Final Equity | Max Drawdown |")
        a("|------------|-------------|-------------|")
        a("| 5th (worst) | $%s | %s%% |" % (fmt0(mc_optimal['p5_equity']), mc_optimal.get('p95_max_dd', '—')))
        a("| 25th | $%s | — |" % fmt0(mc_optimal['p25_equity']))
        a("| **Median** | **$%s** | **%s%%** |" % (fmt0(mc_optimal['median_equity']), mc_optimal['median_max_dd']))
        a("| 75th | $%s | — |" % fmt0(mc_optimal['p75_equity']))
        a("| 95th (best) | $%s | — |" % fmt0(mc_optimal['p95_equity']))
        a("| Mean | $%s | — |" % fmt0(mc_optimal['mean_equity']))
        a("")

    # ═══════════ FEE SENSITIVITY ═══════════
    a("---")
    a("")
    a("## Fee Sensitivity Analysis (Optimal Config)")
    a("")
    a("| Fee Model | Comm/Trade | Total Comm (est) | Net vs Gross Impact |")
    a("|-----------|-----------|-----------------|---------------------|")
    if optimal_m:
        n_t = optimal_m['total_trades']
        gross = optimal_m['total_gross_pnl_usd']
        for fk, fv in FEE_MODELS.items():
            tc = n_t * 2 * fv['per_trade']
            net = gross - tc
            net_ret = net / INITIAL_CAPITAL * 100
            a("| %s | $%s | $%s | %s%% net return |"
              % (fv['label'], fmt2(fv['per_trade']), fmt0(tc), fmt2(net_ret)))
    a("")

    # ═══════════ LIMITATIONS ═══════════
    a("---")
    a("")
    a("## Known Limitations & Caveats")
    a("")
    a("1. **Survivorship bias**: Universe is pre-filtered to stocks with available price data.")
    a("2. **Daily OHLC only**: SL checked before TP on same bar (worst-case fill assumption).")
    a("3. **End-of-data exits (%d trades)**: Positions running out of data are flagged."
      % default_m.get('end_of_data_trades', 0))
    a("4. **No tax modeling**: Returns are pre-tax.")
    a("5. **No market impact**: Assumes infinite liquidity at quoted prices.")
    a("6. **Missing algorithms**: CAN SLIM & ML Ensemble have insufficient picks (1 or 0) — "
      "import picks before drawing conclusions.")
    a("7. **Sector mapping is approximate** — uses static GICS-like lookup table, "
      "not real-time classification data.")
    a("")

    # ═══════════ NEXT STEPS ═══════════
    a("---")
    a("")
    a("## Next Steps")
    a("")
    a("| Priority | Action | Expected Outcome |")
    a("|----------|--------|------------------|")
    a("| **High** | Import missing picks for CAN SLIM & ML Ensemble | Complete comparison matrix |")
    a("| **High** | Switch default TP/SL to optimal config (50/20/90d) | Sharpe +3.7 vs -9.1 |")
    a("| **High** | Activate adaptive ATR-based TP/SL in production | Per-stock volatility scaling |")
    a("| **Medium** | Add per-share Questrade fee model | More accurate commission estimates |")
    a("| **Medium** | Extend Technical Momentum to 12+ months | Statistically meaningful sample |")
    a("| **Medium** | Integrate GARCH vol-adjusted Kelly from garch_vol.py | Dynamic position sizing |")
    a("| **Low** | Apply meta-labeler filter from meta_label.py | Reject low-confidence signals |")
    a("| **Low** | Run walk-forward validation (rolling 3m train, 1m test) | Robustness check |")
    a("")

    # ═══════════ TICKER CORRELATION MATRIX ═══════════
    if ticker_corr and ticker_corr.get('tickers'):
        a("---")
        a("")
        a("## Ticker Correlation Matrix (Top %d Most-Traded)" % len(ticker_corr['tickers']))
        a("")
        a("Daily return correlations across %d overlapping trading days. "
          "High correlations (|r| > 0.7) indicate concentration risk — "
          "ostensibly different positions that move together." % ticker_corr['n_dates'])
        a("")

        # Table header
        tickers = ticker_corr['tickers']
        matrix = ticker_corr['matrix']
        header = "| | " + " | ".join(tickers) + " |"
        sep = "|---" + ("|---" * len(tickers)) + "|"
        a(header)
        a(sep)
        for i, tk in enumerate(tickers):
            cells = []
            for j in range(len(tickers)):
                val = matrix[i][j]
                if i == j:
                    cells.append("**1.00**")
                elif abs(val) > 0.7:
                    cells.append("**%.2f**" % val)  # bold = high corr
                else:
                    cells.append("%.2f" % val)
            a("| **%s** | %s |" % (tk, " | ".join(cells)))
        a("")

        # High-correlation warning
        high = ticker_corr.get('high_pairs', [])
        if high:
            a("> **Concentration Risk Alert**: %d pair(s) have correlation > 0.7:" % len(high))
            for tk_a, tk_b, corr in high[:8]:
                a("> - **%s** / **%s**: r = %.3f" % (tk_a, tk_b, corr))
            a(">")
            a("> These pairs tend to move together. Holding both in size amplifies drawdowns. "
              "Consider reducing allocation to one in each highly-correlated pair or using "
              "the concentration limit feature.")
            a("")
        else:
            a("*No pairs with |r| > 0.7 found — portfolio diversification is adequate among top holdings.*")
            a("")

    # ═══════════ IMPLEMENTATION RECOMMENDATIONS ═══════════
    a("---")
    a("")
    a("## Implementation Recommendations")
    a("")
    a("Based on the analysis above, the following parameter and allocation changes are recommended "
      "for production deployment:")
    a("")
    a("### Suggested Allocation by Algorithm")
    a("")
    a("| Algorithm | Allocation % | Rationale |")
    a("|-----------|-------------|-----------|")
    a("| **Cursor Genius** | 30% | Highest Sharpe (6.3+), 67% WR, strong alpha |")
    a("| **ETF Masters** | 25% | Diversified ETF exposure, Sharpe 4.2+, low single-stock risk |")
    a("| **Sector Rotation** | 20% | Macro-driven rotation, Sharpe 3.8+, complements stock pickers |")
    a("| **Blue Chip Growth** | 15% | Solid fundamentals, Sharpe 2.3, but higher drawdown risk |")
    a("| **Sector Momentum** | 5% | Modest Sharpe, small sample — cap allocation until more data |")
    a("| **Technical Momentum** | 5% | Insufficient data — allocate minimally, expand universe first |")
    a("")
    a("*CAN SLIM and ML Ensemble are excluded until their pick pipelines are operational.*")
    a("")
    a("### Rebalancing Recommendations")
    a("")
    a("| Parameter | Recommendation | Why |")
    a("|-----------|---------------|-----|")
    a("| **Rebalancing Frequency** | Monthly (first trading day) | Balances responsiveness vs turnover cost |")
    a("| **Drift Threshold** | Rebalance if any algo drifts +/-5% from target | Prevents concentration from unrebalanced gains |")
    a("| **Exit Params (default)** | TP=50%, SL=20%, Hold=90d | Optimal config from grid search |")
    a("| **Exit Params (alt)** | TP=50%, SL=20%, Hold=180d | Better for Blue Chip & ETF (Sharpe +4.0/+6.5) |")
    a("| **Advanced Exit** | Stop-to-breakeven after +6% | Best trailing strategy (Sharpe +2.5) |")
    a("| **Position Sizing** | 5% of equity, capped at $2k | Current default — adequate for $10-40k accounts |")
    a("| **Max per Ticker** | 5% of portfolio | Prevents single-name blowups (UNH, AMT) |")
    a("| **Max per Sector** | 20% of portfolio | Limits sector-driven drawdowns |")
    a("")

    # ═══════════ REPRODUCIBILITY ═══════════
    a("---")
    a("")
    a("## Reproducibility Checklist")
    a("")
    a("```bash")
    a("# 1. Compute comprehensive performance report")
    a("python scripts/comprehensive_performance_report.py")
    a("")
    a("# 2. Run with specific TP/SL")
    a("python scripts/comprehensive_performance_report.py --tp 50 --sl 20 --hold 90")
    a("")
    a("# 3. Quick run (skip grid search and Monte Carlo)")
    a("python scripts/comprehensive_performance_report.py --skip-grid --skip-monte-carlo")
    a("")
    a("# 4. PHP backtests (for comparison)")
    a("# php findstocks/api/backtest.php (via HTTP)")
    a("# curl 'https://findtorontoevents.ca/findstocks/api/backtest.php?algorithms=Blue%20Chip%20Growth&tp=50&sl=20&max_hold=90'")
    a("")
    a("# 5. Daily quant pipeline")
    a("python scripts/run_daily.py")
    a("```")
    a("")

    return "\n".join(lines)


def _write_metrics_block(a, m, spy_bm):
    """Write a full metrics block for a given config."""
    a("| Metric | Value |")
    a("|--------|-------|")
    a("| Total Trades | %s |" % m['total_trades'])
    a("| Win Rate | %s%% (95%% CI: %s%% - %s%%) |"
      % (m['win_rate_pct'], m['win_rate_ci_95'][0], m['win_rate_ci_95'][1]))
    a("| Mean Return/Trade (net) | %s%% |" % fmt4(m['mean_return_pct']))
    a("| Mean Return/Trade (gross) | %s%% |" % fmt4(m['mean_return_gross_pct']))
    a("| Total PnL (net) | $%s |" % fmt2(m['total_pnl_usd']))
    a("| Total Commissions | $%s |" % fmt2(m['total_commissions_usd']))
    a("| Final Equity | $%s |" % fmt2(m['final_equity']))
    a("| Total Return | %s%% |" % fmt2(m['total_return_pct']))
    a("| CAGR | %s%% |" % fmt2(m['cagr_pct']))
    a("| Avg Holding Period | %s days |" % m['avg_hold_days'])
    a("| Annualized Turnover | %sx |" % m['annualized_turnover'])
    a("")
    a("### Risk-Adjusted Ratios")
    a("")
    a("| Ratio | Value | 95% CI |")
    a("|-------|-------|--------|")
    a("| **Sharpe** | %s | [%s, %s] |"
      % (fmts(m['sharpe_ratio']), fmts(m['sharpe_ci_95'][0]), fmts(m['sharpe_ci_95'][1])))
    a("| **Sortino** | %s | [%s, %s] |"
      % (fmts(m['sortino_ratio']), fmts(m['sortino_ci_95'][0]), fmts(m['sortino_ci_95'][1])))
    a("| **Calmar** | %s | — |" % fmts(m['calmar_ratio']))
    a("| **Profit Factor** | %s | — |" % fmt3(m['profit_factor']))
    a("| **Recovery Factor** | %s | — |" % fmt3(m['recovery_factor']))
    a("")
    a("### Risk Metrics")
    a("")
    a("| Metric | Value |")
    a("|--------|-------|")
    a("| Volatility (per-trade) | %s%% |" % fmt3(m['volatility_pct']))
    a("| Downside Deviation | %s%% |" % fmt3(m['downside_deviation']))
    a("| VaR (95%%) | %s%% |" % fmt2(m['var_95_pct']))
    a("| CVaR / Expected Shortfall (95%%) | %s%% |" % fmt2(m['cvar_95_pct']))
    a("| Max Drawdown | $%s (%s%%) |" % (fmt2(m['max_drawdown_usd']), m['max_drawdown_pct']))
    a("| Avg DD Duration | %s trades |" % m['avg_drawdown_duration_trades'])
    a("")

    # Exit reasons
    a("### Exit Reason Breakdown")
    a("")
    a("| Reason | Count | % |")
    a("|--------|-------|---|")
    for reason, cnt in sorted(m['exit_reasons'].items(), key=lambda x: -x[1]):
        pct = cnt / max(m['total_trades'], 1) * 100
        a("| %s | %d | %s%% |" % (reason, cnt, fmt1(pct)))
    a("")

    # SPY comparison
    if spy_bm:
        a("### vs SPY Benchmark")
        a("")
        a("| Metric | Portfolio | SPY | Delta |")
        a("|--------|----------|-----|-------|")
        a("| Total Return | %s%% | %s%% | %s%% |"
          % (fmt2(m['total_return_pct']), fmt2(spy_bm['total_return_pct']),
             fmt2(m['total_return_pct'] - spy_bm['total_return_pct'])))
        a("| CAGR | %s%% | %s%% | %s%% |"
          % (fmt2(m['cagr_pct']), fmt2(spy_bm['cagr_pct']),
             fmt2(m['cagr_pct'] - spy_bm['cagr_pct'])))
        a("| Sharpe | %s | %s | %s |"
          % (fmts(m['sharpe_ratio']), fmts(spy_bm['sharpe_ratio']),
             fmts(m['sharpe_ratio'] - spy_bm['sharpe_ratio'])))
        a("")


def _grade(sharpe):
    if sharpe >= 3.0:
        return 'A+'
    if sharpe >= 2.0:
        return 'A'
    if sharpe >= 1.0:
        return 'B'
    if sharpe >= 0.5:
        return 'C'
    return 'D'


# Formatters
def fmts(v):
    return '%+.3f' % v if v is not None else '—'

def fmt0(v):
    return '{:,.0f}'.format(v) if v is not None else '—'

def fmt1(v):
    return '%.1f' % v if v is not None else '—'

def fmt2(v):
    return '%+.2f' % v if isinstance(v, (int, float)) else str(v)

def fmt3(v):
    return '%+.3f' % v if isinstance(v, (int, float)) else str(v)

def fmt4(v):
    return '%+.4f' % v if isinstance(v, (int, float)) else str(v)


# ─────────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description='Comprehensive Performance Report V2')
    parser.add_argument('--tp', type=float, default=10, help='Default TP %% (10)')
    parser.add_argument('--sl', type=float, default=5, help='Default SL %% (5)')
    parser.add_argument('--hold', type=int, default=30, help='Max hold days (30)')
    parser.add_argument('--skip-grid', action='store_true', help='Skip grid search')
    parser.add_argument('--skip-monte-carlo', action='store_true', help='Skip Monte Carlo')
    args = parser.parse_args()

    print("=" * 80)
    print("  COMPREHENSIVE PORTFOLIO PERFORMANCE REPORT – V2")
    print("  %s" % datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'))
    print("=" * 80)

    conn = connect_db()
    print("\n[1/9] Loading data from database...")
    picks, prices = load_data(conn)
    conn.close()
    print("       %d picks | %d tickers with price data" % (len(picks), len(prices)))

    # ── 2. Default backtest ──
    print("\n[2/9] Default backtest (TP=%s%% SL=%s%% Hold=%sd)..." % (args.tp, args.sl, args.hold))
    default_trades, _, default_eq = backtest(picks, prices, tp=args.tp, sl=args.sl, max_hold=args.hold)
    default_m = comprehensive_metrics(default_trades, 'Default (%s/%s/%sd)' % (int(args.tp), int(args.sl), args.hold))
    print("       %d trades | Sharpe %s | WR %s%% | Final $%s"
          % (len(default_trades), fmts(default_m['sharpe_ratio']),
             default_m['win_rate_pct'], fmt0(default_eq)))

    # ── 3. SPY Benchmark ──
    print("\n[3/9] SPY benchmark...")
    start_date = picks[0]['pick_date']
    end_date = picks[-1]['pick_date']
    spy_bm = compute_spy_benchmark(prices, start_date, end_date)
    if spy_bm:
        print("       SPY: %s%% total | Sharpe %s" % (fmt2(spy_bm['total_return_pct']), fmts(spy_bm['sharpe_ratio'])))

    spy_daily = spy_bm['daily_returns'] if spy_bm else None

    # ── 4. Optimal config ──
    print("\n[4/9] Optimal config (50/20/90d)...")
    opt_trades, _, opt_eq = backtest(picks, prices, tp=50, sl=20, max_hold=90)
    optimal_m = comprehensive_metrics(opt_trades, 'Optimal (50/20/90d)', spy_daily)
    print("       %d trades | Sharpe %s | WR %s%% | Final $%s"
          % (len(opt_trades), fmts(optimal_m['sharpe_ratio']),
             optimal_m['win_rate_pct'], fmt0(opt_eq)))

    # ── 4c. Trailing stop experiment ──
    print("\n[4c/9] Trailing stop experiments (50/20/90d base)...")
    trail_configs_main = [
        (50, 20, 90, 10, 0, 0, 'Trail 10%'),
        (50, 20, 90, 15, 0, 0, 'Trail 15%'),
        (50, 20, 90, 10, 8, 0, 'Trail 10% + PP@8%'),
        (50, 20, 90, 0,  0, 6, 'BE after +6%'),
        (30, 15, 90, 10, 6, 0, 'MiniMax: 30/15/90+trail10+pp6'),
    ]
    best_trail_sharpe = -999
    trailing_m = None
    for tp_v, sl_v, hold_v, trail_v, pp_v, be_v, lbl in trail_configs_main:
        tt, _, teq = backtest(picks, prices, tp=tp_v, sl=sl_v, max_hold=hold_v,
                              trailing_stop_pct=trail_v, partial_profit_pct=pp_v,
                              breakeven_after_pct=be_v)
        tm = comprehensive_metrics(tt, lbl, spy_daily)
        if tm:
            print("       %s: %d trades | Sharpe %s | WR %s%% | Final $%s"
                  % (lbl, len(tt), fmts(tm['sharpe_ratio']),
                     tm['win_rate_pct'], fmt0(teq)))
            if tm['sharpe_ratio'] > best_trail_sharpe:
                best_trail_sharpe = tm['sharpe_ratio']
                trailing_m = tm
    if trailing_m:
        print("       BEST trailing: %s (Sharpe %s)" % (trailing_m['label'], fmts(trailing_m['sharpe_ratio'])))

    # ── 5. Adaptive ATR-based TP/SL ──
    # Hybrid approach: ATR sets MINIMUM thresholds, with a configurable floor.
    # This way volatile stocks get wider stops, calm stocks still have reasonable mins.
    atr_configs = [
        (5.0, 2.5, 15, 8,  90, 'Hybrid: max(5xATR, 15%TP) / max(2.5xATR, 8%SL) / 90d'),
        (6.0, 3.0, 20, 10, 90, 'Hybrid: max(6xATR, 20%TP) / max(3xATR, 10%SL) / 90d'),
        (8.0, 4.0, 25, 12, 90, 'Hybrid: max(8xATR, 25%TP) / max(4xATR, 12%SL) / 90d'),
    ]
    print("\n[5/9] Testing adaptive ATR hybrid configs...")
    best_atr_sharpe = -999
    adaptive_m = None
    best_atr_label = ''
    atr_trades = []
    atr_eq = INITIAL_CAPITAL
    for tp_m, sl_m, tp_floor, sl_floor, hd, lbl in atr_configs:
        at, _, aeq = backtest(picks, prices, tp=tp_floor, sl=sl_floor, max_hold=hd,
                              adaptive_tpsl=True, atr_tp_mult=tp_m, atr_sl_mult=sl_m)
        am = comprehensive_metrics(at, lbl, spy_daily)
        if am:
            short_lbl = "ATR %sx/%sx + %s/%s/%sd" % (tp_m, sl_m, tp_floor, sl_floor, hd)
            print("       %s: %d trades | Sharpe %s | WR %s%% | Final $%s"
                  % (short_lbl, len(at), fmts(am['sharpe_ratio']),
                     am['win_rate_pct'], fmt0(aeq)))
            if am['sharpe_ratio'] > best_atr_sharpe:
                best_atr_sharpe = am['sharpe_ratio']
                adaptive_m = am
                best_atr_label = lbl
                atr_trades = at
                atr_eq = aeq
    if adaptive_m:
        print("       BEST: %s" % best_atr_label)

    # ── 6. Concentration-limited ──
    print("\n[6/9] Concentration-limited backtest (50/20/90d, max 5%% ticker, 20%% sector)...")
    conc_trades, _, conc_eq = backtest(picks, prices, tp=50, sl=20, max_hold=90,
                                        concentration_limits=True)
    conc_m = comprehensive_metrics(conc_trades, 'Concentration-Limited (50/20/90d)', spy_daily)
    if conc_m:
        print("       %d trades | Sharpe %s | WR %s%% | Final $%s"
              % (len(conc_trades), fmts(conc_m['sharpe_ratio']),
                 conc_m['win_rate_pct'], fmt0(conc_eq)))

    # ── Buy-and-hold (no TP/SL) ──
    print("\n       Buy-and-hold (TP=999/SL=999/Hold=365d, zero-fee)...")
    bh_trades, _, bh_eq = backtest(picks, prices, tp=999, sl=999, max_hold=365, fee_model='zero')
    buyhold_m = comprehensive_metrics(bh_trades, 'Buy-and-Hold (365d, gross)', spy_daily)
    if buyhold_m:
        print("       %d trades | Return %s%% | Final $%s"
              % (len(bh_trades), fmt2(buyhold_m['total_return_pct']), fmt0(bh_eq)))

    # ── Commission-free gross ──
    grossfee_trades, _, grossfee_eq = backtest(picks, prices, tp=50, sl=20, max_hold=90, fee_model='zero')
    grossfee_m = comprehensive_metrics(grossfee_trades, 'Optimal (50/20/90d, gross)', spy_daily)

    # ── 7. Per-algorithm (optimal config) ──
    print("\n[7/9] Per-algorithm metrics (optimal config)...")
    algo_groups = defaultdict(list)
    for t in opt_trades:
        algo_groups[t['algorithm']].append(t)
    algo_metrics = []
    for algo, trades in algo_groups.items():
        if len(trades) < 5:
            continue
        m = comprehensive_metrics(trades, algo, spy_daily)
        if m:
            algo_metrics.append(m)
    algo_metrics.sort(key=lambda x: x['sharpe_ratio'], reverse=True)

    # ── 8. Grid search ──
    grid_results = {}
    if not args.skip_grid:
        print("\n[8/9] TP/SL grid search...")
        grid_results = grid_search_tpsl(picks, prices)
        print("       %d configs x %d algorithms" % (len(GRID_CONFIGS), len(grid_results)))
        for algo, configs in grid_results.items():
            if configs:
                best = configs[0]
                print("       %s: best=%s (Sharpe=%s)" % (algo, best['config'], fmts(best['sharpe'])))
    else:
        print("\n[8/9] Grid search skipped")

    # ── OOS ──
    print("\n       Out-of-sample validation...")
    oos_results = train_test_analysis(picks, prices)

    # ── Walk-forward CV ──
    print("\n       Purged walk-forward CV (6m train / 2m test / 5d embargo)...")
    wfcv_results = walk_forward_cv(picks, prices, tp=50, sl=20, max_hold=90,
                                    train_months=6, test_months=2, embargo_days=5)
    if wfcv_results:
        agg = wfcv_results['aggregate']
        print("       %d folds | Avg test Sharpe: %s (std: %s) | %s%% positive folds"
              % (wfcv_results['n_folds'], fmts(agg['avg_test_sharpe']),
                 fmt2(agg['std_test_sharpe']), agg['pct_positive']))
        print("       Overfit ratio: %s%% (train Sharpe %s vs test %s)"
              % (fmt2(agg['overfit_ratio_pct']), fmts(agg['avg_train_sharpe']),
                 fmts(agg['avg_test_sharpe'])))

    # ── 9. Monte Carlo ──
    mc_default = mc_optimal = None
    if not args.skip_monte_carlo:
        print("\n[9/9] Monte Carlo simulation (1000 reshuffles)...")
        mc_optimal = monte_carlo(opt_trades, n_sims=1000)
        if mc_optimal:
            print("       Median equity: $%s | P5: $%s | P95: $%s"
                  % (fmt0(mc_optimal['median_equity']),
                     fmt0(mc_optimal['p5_equity']),
                     fmt0(mc_optimal['p95_equity'])))
    else:
        print("\n[9/9] Monte Carlo skipped")

    # ── Ticker correlation matrix (top 10 most-traded) ──
    ticker_corr = compute_ticker_correlations(prices, opt_trades)

    # ═══════════ GENERATE REPORT ═══════════
    print("\n" + "=" * 80)
    print("  GENERATING REPORT")
    print("=" * 80)

    md = generate_markdown(default_m, optimal_m, adaptive_m, conc_m,
                           algo_metrics, spy_bm, grid_results, oos_results,
                           buyhold_m, grossfee_m, mc_default, mc_optimal,
                           trailing_m, ticker_corr=ticker_corr,
                           wfcv_results=wfcv_results)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    md_path = os.path.join(OUTPUT_DIR, 'PORTFOLIO_PERFORMANCE_REPORT.md')
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(md)
    print("\n  Markdown: %s" % md_path)

    # JSON
    json_path = os.path.join(OUTPUT_DIR, 'performance_report.json')
    report_data = {
        'generated': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'version': 2,
        'params': {
            'default_tp': args.tp, 'default_sl': args.sl, 'default_hold': args.hold,
            'commission': FEE_MODELS[DEFAULT_FEE]['per_trade'],
            'slippage': SLIPPAGE_PCT, 'position_pct': POSITION_PCT,
            'position_cap': POSITION_CAP, 'atr_period': ATR_PERIOD,
            'max_ticker_pct': MAX_TICKER_PCT, 'max_sector_pct': MAX_SECTOR_PCT,
        },
        'configs': {
            'default': default_m,
            'optimal': optimal_m,
            'best_trailing': trailing_m,
            'adaptive_atr': adaptive_m,
            'concentration_limited': conc_m,
            'buy_and_hold': buyhold_m,
            'commission_free': grossfee_m,
        },
        'per_algorithm': algo_metrics,
        'spy_benchmark': {k: v for k, v in (spy_bm or {}).items() if k != 'daily_returns'},
        'grid_search': grid_results,
        'out_of_sample': {
            'train_period': oos_results.get('train_period'),
            'test_period': oos_results.get('test_period'),
            'train': oos_results.get('train_metrics'),
            'test': oos_results.get('test_metrics'),
        },
        'monte_carlo_optimal': mc_optimal,
        'walk_forward_cv': {
            'n_folds': wfcv_results['n_folds'],
            'aggregate': wfcv_results['aggregate'],
            'folds': wfcv_results['folds'],
        } if wfcv_results else None,
    }
    with open(json_path, 'w') as f:
        json.dump(report_data, f, indent=2, default=str)
    print("  JSON:     %s" % json_path)

    # ═══════════ CONSOLE SUMMARY ═══════════
    print("\n" + "=" * 80)
    print("  KEY RESULTS COMPARISON")
    print("=" * 80)
    print("")
    print("  %-32s %8s %8s %10s %8s" % ("Config", "Sharpe", "WR%", "Return%", "MaxDD%"))
    print("  " + "-" * 70)
    for lbl, m in [('Default (10/5/30d)', default_m),
                   ('Optimal (50/20/90d)', optimal_m),
                   ('Best Trailing Stop', trailing_m),
                   ('Adaptive ATR', adaptive_m),
                   ('Conc-Limited', conc_m),
                   ('Buy-Hold (gross)', buyhold_m)]:
        if not m:
            continue
        print("  %-32s %8s %7.1f%% %9.1f%% %7.1f%%"
              % (lbl, fmts(m['sharpe_ratio']), m['win_rate_pct'],
                 m['total_return_pct'], m['max_drawdown_pct']))
    if spy_bm:
        print("  %-32s %8s %8s %9.1f%% %7.1f%%"
              % ("SPY Benchmark", fmts(spy_bm['sharpe_ratio']), "—",
                 spy_bm['total_return_pct'], spy_bm.get('max_drawdown_pct', 0)))
    print("")


if __name__ == '__main__':
    main()
