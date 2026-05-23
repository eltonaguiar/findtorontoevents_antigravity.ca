#!/usr/bin/env python3
"""
Forward Test Engine - LIVE PICKS

Unlike the backtester (run_competition.py) which simulates trades on historical data,
this script generates REAL forward-facing picks:

  1. GENERATE: Downloads TODAY's market data, computes indicators, runs all 12 algorithms
     to produce BUY signals with entry price, TP, SL, and expiry date. Saves to forward_picks.json.
  2. RESOLVE: Checks all open picks against CURRENT prices. Marks as WON (TP hit),
     LOST (SL hit), or EXPIRED (max hold exceeded). Saves results.

Every pick has a full audit trail:
  - Timestamp (EST) when the pick was generated
  - Entry price at signal time
  - Which algorithm, which indicators triggered, what values they had
  - Resolution: when/how it closed, at what price, P&L

Usage:
  python forward_test.py generate   # Generate today's picks
  python forward_test.py resolve    # Resolve open picks against current prices
  python forward_test.py status     # Print summary of all picks
"""
import json
import os
import sys
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

SCRIPT_DIR = Path(__file__).parent
PICKS_FILE = SCRIPT_DIR / "forward_picks.json"

ASSET_CLASSES = {
    "stocks": {
        "label": "S&P 500 Stocks",
        "tickers": [
            "AAPL","MSFT","GOOGL","AMZN","NVDA","META","TSLA","JPM","V","UNH",
            "HD","JNJ","PG","MA","XOM","CVX","ABBV","MRK","PEP","KO",
            "COST","AVGO","TMO","CRM","MCD","AMD","NFLX","LIN","ADBE","ACN",
        ],
        "benchmark": "SPY",
    },
    "crypto": {
        "label": "Cryptocurrency",
        "tickers": [
            "BTC-USD","ETH-USD","BNB-USD","SOL-USD","XRP-USD","ADA-USD",
            "DOGE-USD","DOT-USD","AVAX-USD","LINK-USD","MATIC-USD","UNI-USD",
        ],
        "benchmark": "BTC-USD",
    },
    "forex": {
        "label": "Forex (Major Pairs via ETFs)",
        "tickers": ["FXE","FXB","FXY","FXA","FXC","FXF","UUP","UDN","CYB","CEW"],
        "benchmark": "UUP",
    },
    "penny_stocks": {
        "label": "Penny / Small-Cap Stocks",
        "tickers": [
            "SOFI","PLTR","NIO","RIVN","LCID","MARA","RIOT","PATH","IONQ","JOBY",
            "DNA","OPEN","CLOV",
        ],
        "benchmark": "IWM",
    },
    "meme_coins": {
        "label": "Meme Coins",
        "tickers": ["DOGE-USD","SHIB-USD","PEPE24478-USD","FLOKI-USD","BONK-USD","WIF-USD","MEME-USD"],
        "benchmark": "DOGE-USD",
    },
}

# ── Indicator helpers (same as backtest) ──────────────────────────

def compute_rsi(series, window=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/window, min_periods=window).mean()
    avg_loss = loss.ewm(alpha=1/window, min_periods=window).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def compute_indicators(close_df):
    indicators = {}
    returns = close_df.pct_change()
    for w in [20, 50, 200]:
        indicators[f'ma{w}'] = close_df.rolling(w).mean()
        indicators[f'price_vs_ma{w}'] = (close_df - indicators[f'ma{w}']) / indicators[f'ma{w}']
    for w in [5, 10, 21, 63, 126]:
        indicators[f'ret_{w}d'] = close_df.pct_change(w)
    for w in [20]:
        ma = close_df.rolling(w).mean()
        std = close_df.rolling(w).std()
        indicators[f'bb_zscore_{w}d'] = (close_df - ma) / std.replace(0, np.nan)
    indicators['rsi_14'] = close_df.apply(lambda x: compute_rsi(x, 14))
    ema12 = close_df.ewm(span=12).mean()
    ema26 = close_df.ewm(span=26).mean()
    indicators['macd_hist'] = (ema12 - ema26 - (ema12 - ema26).ewm(span=9).mean()) / close_df
    daily_ret = close_df.pct_change()
    for w in [21, 63]:
        ret_w = close_df.pct_change(w)
        vol_w = daily_ret.rolling(w).std() * np.sqrt(w)
        indicators[f'trend_strength_{w}d'] = ret_w / vol_w.replace(0, np.nan)
    for w in [21, 63]:
        indicators[f'rvol_{w}d'] = daily_ret.rolling(w).std() * np.sqrt(252)
    for w in [252]:
        indicators[f'dist_{w}d_high'] = (close_df - close_df.rolling(w).max()) / close_df.rolling(w).max()
    for w in [1, 3, 5]:
        indicators[f'reversal_{w}d'] = -returns.rolling(w).sum()
    var_1 = daily_ret.rolling(63).var()
    ret_5 = daily_ret.rolling(5).sum()
    var_5 = ret_5.rolling(63).var()
    vr = var_5 / (5 * var_1).replace(0, np.nan)
    indicators['hurst_63d'] = np.log(vr.clip(lower=0.01)) / (2 * np.log(5)) + 0.5
    indicators['mom_accel'] = close_df.pct_change(21) - close_df.pct_change(21).shift(21)
    rolling_max = close_df.rolling(63, min_periods=1).max()
    indicators['drawdown_63d'] = (close_df - rolling_max) / rolling_max
    return indicators


# ── Algorithm signal generators (return list of picks) ────────────

ALGO_CONFIGS = {
    "Classic Momentum":     {"type": "Momentum",       "hold_days": 21, "tp": 0.08, "sl": 0.04},
    "Trend Following":      {"type": "Trend",          "hold_days": 21, "tp": 0.06, "sl": 0.03},
    "Breakout Momentum":    {"type": "Breakout",       "hold_days": 10, "tp": 0.07, "sl": 0.04},
    "Bollinger MR":         {"type": "Mean Reversion", "hold_days": 5,  "tp": 0.05, "sl": 0.03},
    "Short-Term Reversal":  {"type": "Reversal",       "hold_days": 3,  "tp": 0.04, "sl": 0.02},
    "Quality Compounders":  {"type": "Quality",        "hold_days": 63, "tp": 0.12, "sl": 0.06},
    "Value + Quality":      {"type": "Value",          "hold_days": 42, "tp": 0.10, "sl": 0.05},
    "Dividend Aristocrats": {"type": "Dividend",       "hold_days": 63, "tp": 0.10, "sl": 0.06},
    "Earnings Drift":       {"type": "Anomaly",        "hold_days": 42, "tp": 0.08, "sl": 0.04},
    "Consecutive Beats":    {"type": "Earnings",       "hold_days": 42, "tp": 0.08, "sl": 0.04},
    "ML Ranker":            {"type": "ML",             "hold_days": 14, "tp": 0.06, "sl": 0.03},
    "Meta Learner":         {"type": "Ensemble",       "hold_days": 21, "tp": 0.08, "sl": 0.04},
}


def generate_signals(algo_name, date, close_df, indicators, universe):
    """Generate BUY signals for a given algorithm on today's data."""
    cfg = ALGO_CONFIGS[algo_name]
    signals = []
    today = close_df.index[-1]

    for ticker in universe:
        try:
            price = float(close_df.loc[today, ticker])
            if price <= 0 or np.isnan(price):
                continue

            score = 0
            reasons = {}

            if algo_name == "Classic Momentum":
                r126 = _safe_get(indicators, 'ret_126d', today, ticker) if 'ret_126d' in indicators else _safe_get(indicators, 'ret_63d', today, ticker)
                r21 = _safe_get(indicators, 'ret_21d', today, ticker)
                if r126 is not None and r21 is not None and r126 > 0.05:
                    score = r126 - r21
                    reasons = {"6m_ret": round(r126*100, 2), "1m_ret": round(r21*100, 2)}

            elif algo_name == "Trend Following":
                pvm50 = _safe_get(indicators, 'price_vs_ma50', today, ticker)
                pvm200 = _safe_get(indicators, 'price_vs_ma200', today, ticker)
                ts = _safe_get(indicators, 'trend_strength_21d', today, ticker)
                if pvm50 is not None and pvm200 is not None and pvm50 > 0 and pvm200 > 0:
                    score = 0.3 * min(pvm50, 0.3)/0.3 + 0.3 * min(pvm200, 0.3)/0.3 + 0.4 * max(min(ts or 0, 2), 0)/2
                    reasons = {"above_ma50": round(pvm50*100, 2), "above_ma200": round(pvm200*100, 2)}

            elif algo_name == "Breakout Momentum":
                dh = _safe_get(indicators, 'dist_252d_high', today, ticker)
                if dh is not None and dh > -0.05:
                    score = 1 + dh
                    reasons = {"dist_52w_high_pct": round(dh*100, 2)}

            elif algo_name == "Bollinger MR":
                bbz = _safe_get(indicators, 'bb_zscore_20d', today, ticker)
                h = _safe_get(indicators, 'hurst_63d', today, ticker)
                if bbz is not None and bbz < -1.5 and (h is None or h < 0.55):
                    score = min(abs(bbz) / 3, 1.0)
                    reasons = {"bb_zscore": round(bbz, 3), "hurst": round(h or 0.5, 3)}

            elif algo_name == "Short-Term Reversal":
                rev = _safe_get(indicators, 'reversal_5d', today, ticker)
                if rev is not None and rev > 0.02:
                    score = min(rev * 5, 0.8)
                    reasons = {"reversal_5d_pct": round(rev*100, 2)}

            elif algo_name == "Quality Compounders":
                rvol = _safe_get(indicators, 'rvol_63d', today, ticker)
                ts = _safe_get(indicators, 'trend_strength_63d', today, ticker)
                dd = _safe_get(indicators, 'drawdown_63d', today, ticker)
                if rvol is not None:
                    vol_s = max(0, 1 - rvol / 0.5)
                    trend_s = max(0, min((ts or 0) / 2, 1))
                    dd_s = max(0, 1 + (dd or 0) / 0.2)
                    score = vol_s * 0.3 + trend_s * 0.4 + dd_s * 0.3
                    reasons = {"vol": round(rvol*100, 1), "trend": round(ts or 0, 3)}

            elif algo_name == "Value + Quality":
                pvm200 = _safe_get(indicators, 'price_vs_ma200', today, ticker)
                rvol = _safe_get(indicators, 'rvol_63d', today, ticker)
                if pvm200 is not None and pvm200 < 0 and (rvol is None or rvol < 0.5):
                    score = min(abs(pvm200) / 0.2, 1.0) * 0.6 + max(0, 1 - (rvol or 0.3) / 0.4) * 0.4
                    reasons = {"vs_ma200_pct": round(pvm200*100, 2)}

            elif algo_name == "Dividend Aristocrats":
                aristos = {"JNJ","PG","KO","PEP","MMM","ABBV","MCD","WMT","HD","LOW","TXN","COST","XOM","CVX","HON"}
                if ticker in aristos:
                    score = 0.6
                    reasons = {"is_aristocrat": True}

            elif algo_name == "Earnings Drift":
                r21 = _safe_get(indicators, 'ret_21d', today, ticker)
                mh = _safe_get(indicators, 'macd_hist', today, ticker)
                r5 = _safe_get(indicators, 'ret_5d', today, ticker)
                if r21 is not None and r21 > 0.05 and (mh or 0) > 0 and (r5 or 0) > 0:
                    score = min(r21 * 3, 0.6) + min((mh or 0) * 20, 0.2)
                    reasons = {"21d_ret_pct": round(r21*100, 2), "macd_hist": round((mh or 0)*100, 4)}

            elif algo_name == "Consecutive Beats":
                beats = 0
                for period in ['ret_5d', 'ret_10d', 'ret_21d', 'ret_63d']:
                    v = _safe_get(indicators, period, today, ticker)
                    if v is not None and v > 0.02:
                        beats += 1
                rsi = _safe_get(indicators, 'rsi_14', today, ticker)
                if beats >= 3 and (rsi is None or rsi < 75):
                    score = beats / 5.0
                    reasons = {"positive_periods": beats, "rsi": round(rsi or 50, 1)}

            elif algo_name == "ML Ranker":
                feats = {}
                for key in ['ret_21d', 'ret_63d', 'bb_zscore_20d', 'trend_strength_21d', 'rvol_21d', 'macd_hist']:
                    v = _safe_get(indicators, key, today, ticker)
                    if v is not None:
                        feats[key] = v
                if len(feats) >= 3:
                    score = feats.get('ret_21d', 0) * 2.0 + feats.get('ret_63d', 0) * 1.5
                    score += max(0, -feats.get('bb_zscore_20d', 0)) * 0.3
                    score += max(0, feats.get('trend_strength_21d', 0)) * 0.5
                    score -= feats.get('rvol_21d', 0.2) * 0.3
                    score = max(0, min(1, (score + 0.2) / 0.8))
                    reasons = {k: round(v, 4) for k, v in feats.items()}

            elif algo_name == "Meta Learner":
                composite = 0
                n = 0
                for other_algo in ALGO_CONFIGS:
                    if other_algo == "Meta Learner":
                        continue
                    other_sigs = generate_signals(other_algo, date, close_df, indicators, [ticker])
                    if other_sigs:
                        composite += other_sigs[0]['score']
                        n += 1
                if n >= 3:
                    score = composite / n
                    reasons = {"n_agreeing_algos": n, "avg_score": round(score, 4)}

            if score > 0.3:
                tp_price = round(price * (1 + cfg['tp']), 4)
                sl_price = round(price * (1 - cfg['sl']), 4)
                expiry = (datetime.now() + timedelta(days=cfg['hold_days'])).strftime('%Y-%m-%d')
                signals.append({
                    "ticker": ticker,
                    "score": round(float(score), 4),
                    "entry_price": round(price, 4),
                    "tp_price": tp_price,
                    "sl_price": sl_price,
                    "tp_pct": cfg['tp'] * 100,
                    "sl_pct": cfg['sl'] * 100,
                    "expiry_date": expiry,
                    "hold_days": cfg['hold_days'],
                    "reasons": _sanitize(reasons),
                })
        except Exception:
            continue

    signals.sort(key=lambda x: x['score'], reverse=True)
    return signals[:5]


def _safe_get(indicators, key, date, ticker):
    ind = indicators.get(key)
    if ind is None or date not in ind.index or ticker not in ind.columns:
        return None
    v = ind.loc[date, ticker]
    if isinstance(v, (float, np.floating)) and (np.isnan(v) or np.isinf(v)):
        return None
    return float(v)


def _sanitize(obj):
    if isinstance(obj, float):
        return None if (math.isnan(obj) or math.isinf(obj)) else obj
    elif isinstance(obj, (np.floating, np.integer)):
        v = float(obj)
        return None if (math.isnan(v) or math.isinf(v)) else v
    elif isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    return obj


# ── Load / Save picks ─────────────────────────────────────────────

def load_picks():
    if PICKS_FILE.exists():
        with open(PICKS_FILE) as f:
            return json.load(f)
    return {"picks": [], "summary": {}, "last_generate": None, "last_resolve": None}


def save_picks(data):
    data = _sanitize(data)
    with open(PICKS_FILE, 'w') as f:
        json.dump(data, f, indent=2, default=str)


def _normalize_open_pick_for_resolve(p: dict) -> None:
    """Merge alternate pick schemas (e.g. penny / momentum imports) into forward_test shape."""
    if p.get('ticker'):
        return
    sym = (p.get('symbol') or '').strip()
    if not sym:
        return
    p['ticker'] = sym
    if p.get('tp_price') is None and p.get('take_profit') is not None:
        p['tp_price'] = float(p['take_profit'])
    if p.get('sl_price') is None and p.get('stop_loss') is not None:
        p['sl_price'] = float(p['stop_loss'])
    if not p.get('expiry_date') and p.get('timestamp'):
        try:
            ts = str(p['timestamp']).replace('Z', '+00:00')
            base = datetime.fromisoformat(ts)
            if base.tzinfo:
                base = base.astimezone(timezone.utc).replace(tzinfo=None)
            hold = int(p.get('hold_days') or 5)
            p['expiry_date'] = (base + timedelta(days=max(1, hold))).strftime('%Y-%m-%d')
        except Exception:
            p['expiry_date'] = (datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d')
    if not p.get('id'):
        p['id'] = f"imported_{sym}_{p.get('timestamp', 'na')}"


# ── GENERATE: produce today's forward picks ───────────────────────

def cmd_generate():
    now_est = datetime.now().strftime('%Y-%m-%d %H:%M:%S EST')
    print(f"=== FORWARD TEST: Generating picks at {now_est} ===")

    data = load_picks()
    new_picks = []

    for ac_key, ac_cfg in ASSET_CLASSES.items():
        tickers = ac_cfg['tickers']
        print(f"\n  {ac_cfg['label']} ({len(tickers)} tickers)...")

        try:
            raw = yf.download(tickers, period="1y", auto_adjust=True, progress=False, threads=True)
        except Exception as e:
            print(f"    Download failed: {e}")
            continue

        if raw.empty:
            print("    No data")
            continue

        if isinstance(raw.columns, pd.MultiIndex):
            close_df = raw['Close'].dropna(how='all')
        else:
            close_df = raw[['Close']].dropna(how='all')
            close_df.columns = [tickers[0]]

        available = [t for t in tickers if t in close_df.columns]
        if not available or len(close_df) < 200:
            print(f"    Insufficient data ({len(available)} tickers, {len(close_df)} days)")
            continue

        close_df = close_df[available].dropna(how='all')
        indicators = compute_indicators(close_df)
        # Use actual today's date, not last data date (to avoid retroactive picks)
        today = datetime.now()
        today_str = today.strftime('%Y-%m-%d')

        for algo_name in ALGO_CONFIGS:
            try:
                signals = generate_signals(algo_name, today, close_df, indicators, available)
                for sig in signals[:3]:  # Top 3 per algo per asset class
                    pick = {
                        "id": f"{algo_name}_{ac_key}_{sig['ticker']}_{today_str}",
                        "algorithm": algo_name,
                        "algo_type": ALGO_CONFIGS[algo_name]['type'],
                        "asset_class": ac_key,
                        "asset_label": ac_cfg['label'],
                        "ticker": sig['ticker'],
                        "action": "BUY",
                        "entry_price": sig['entry_price'],
                        "tp_price": sig['tp_price'],
                        "sl_price": sig['sl_price'],
                        "tp_pct": sig['tp_pct'],
                        "sl_pct": sig['sl_pct'],
                        "score": sig['score'],
                        "reasons": sig['reasons'],
                        "generated_at": now_est,
                        "generated_date": today_str,
                        "expiry_date": sig['expiry_date'],
                        "hold_days_max": sig['hold_days'],
                        "status": "OPEN",
                        "resolved_at": None,
                        "resolved_price": None,
                        "resolved_reason": None,
                        "pnl_pct": None,
                        "pnl_dollar": None,
                    }
                    # Avoid duplicate picks
                    existing_ids = {p['id'] for p in data['picks']}
                    if pick['id'] not in existing_ids:
                        new_picks.append(pick)
            except Exception as e:
                print(f"    {algo_name} error: {e}")

    data['picks'].extend(new_picks)
    data['last_generate'] = now_est
    _update_summary(data)
    save_picks(data)
    print(f"\n=== Generated {len(new_picks)} new forward picks ===")
    print(f"    Total picks: {len(data['picks'])} ({sum(1 for p in data['picks'] if p['status']=='OPEN')} open)")


# ── RESOLVE: check open picks against current prices ──────────────

def cmd_resolve():
    now_est = datetime.now().strftime('%Y-%m-%d %H:%M:%S EST')
    print(f"=== FORWARD TEST: Resolving picks at {now_est} ===")

    data = load_picks()
    for p in data['picks']:
        if p.get('status') == 'OPEN':
            _normalize_open_pick_for_resolve(p)

    open_picks = [p for p in data['picks'] if p['status'] == 'OPEN']
    for p in open_picks:
        if not p.get('ticker'):
            print(f"  WARNING: open pick missing ticker/symbol — closing as MISSING_TICKER ({p.get('id', 'no-id')})")
            p['status'] = 'LOST'
            p['resolved_at'] = now_est
            p['resolved_reason'] = 'MISSING_TICKER'
            p['resolved_price'] = None
            p['pnl_pct'] = 0.0
            p['pnl_dollar'] = 0.0

    open_picks = [p for p in data['picks'] if p['status'] == 'OPEN']

    if not open_picks:
        print("  No open picks to resolve.")
        data['last_resolve'] = now_est
        save_picks(data)
        return

    # Gather all tickers we need prices for
    tickers_needed = list(set(p.get('ticker', '') for p in open_picks if p.get('ticker')))
    print(f"  Fetching current prices for {len(tickers_needed)} tickers...")

    try:
        raw = yf.download(tickers_needed, period="5d", auto_adjust=True, progress=False, threads=True)
    except Exception as e:
        print(f"  Download failed: {e}")
        return

    if raw.empty:
        print("  No price data returned")
        return

    if isinstance(raw.columns, pd.MultiIndex):
        close_df = raw['Close'].dropna(how='all')
    else:
        close_df = pd.DataFrame({'Close': raw['Close']})
        close_df.columns = [tickers_needed[0]]

    resolved_count = 0
    today_str = datetime.now().strftime('%Y-%m-%d')

    for pick in open_picks:
        ticker = pick.get('ticker', '')
        if ticker not in close_df.columns:
            continue

        try:
            current_price = float(close_df[ticker].dropna().iloc[-1])
        except (IndexError, KeyError):
            continue

        entry = pick['entry_price']
        tp = pick['tp_price']
        sl = pick['sl_price']
        expiry = pick['expiry_date']
        if entry <= 0:
            pick['status'] = 'LOST'
            pick['resolved_at'] = now_est
            pick['resolved_reason'] = 'INVALID_ENTRY'
            pick['resolved_price'] = 0
            pick['pnl_pct'] = 0
            pick['pnl_dollar'] = 0
            resolved_count += 1
            continue
        change_pct = (current_price - entry) / entry

        resolved = False
        if current_price >= tp:
            pick['status'] = 'WON'
            pick['resolved_reason'] = 'TP_HIT'
            resolved = True
        elif current_price <= sl:
            pick['status'] = 'LOST'
            pick['resolved_reason'] = 'SL_HIT'
            resolved = True
        elif today_str >= expiry:
            pick['status'] = 'WON' if change_pct > 0 else 'LOST'
            pick['resolved_reason'] = 'EXPIRED'
            resolved = True

        if resolved:
            pick['resolved_at'] = now_est
            pick['resolved_price'] = round(current_price, 4)
            pick['pnl_pct'] = round(change_pct * 100, 2)
            pick['pnl_dollar'] = round(change_pct * 1000, 2)  # Per $1000 invested
            resolved_count += 1

    data['last_resolve'] = now_est
    _update_summary(data)
    save_picks(data)

    open_remaining = sum(1 for p in data['picks'] if p['status'] == 'OPEN')
    won = sum(1 for p in data['picks'] if p['status'] == 'WON')
    lost = sum(1 for p in data['picks'] if p['status'] == 'LOST')
    print(f"\n=== Resolved {resolved_count} picks ===")
    print(f"    Open: {open_remaining} | Won: {won} | Lost: {lost}")
    if won + lost > 0:
        print(f"    Win rate: {won/(won+lost)*100:.1f}%")


# ── STATUS: print summary ─────────────────────────────────────────

def cmd_status():
    data = load_picks()
    picks = data['picks']
    print(f"=== FORWARD TEST STATUS ===")
    print(f"  Last generate: {data.get('last_generate', 'Never')}")
    print(f"  Last resolve:  {data.get('last_resolve', 'Never')}")
    print(f"  Total picks:   {len(picks)}")
    print(f"  Open:          {sum(1 for p in picks if p['status']=='OPEN')}")
    print(f"  Won:           {sum(1 for p in picks if p['status']=='WON')}")
    print(f"  Lost:          {sum(1 for p in picks if p['status']=='LOST')}")
    won = sum(1 for p in picks if p['status'] == 'WON')
    lost = sum(1 for p in picks if p['status'] == 'LOST')
    if won + lost > 0:
        print(f"  Win Rate:      {won/(won+lost)*100:.1f}%")
        pnls = [p['pnl_pct'] for p in picks if p.get('pnl_pct') is not None]
        if pnls:
            print(f"  Avg P&L:       {sum(pnls)/len(pnls):+.2f}%")

    # Per algorithm
    if picks:
        print(f"\n  Per Algorithm:")
        by_algo = {}
        for p in picks:
            a = p.get('algorithm', p.get('strategy', 'unknown'))
            if a not in by_algo:
                by_algo[a] = {'open': 0, 'won': 0, 'lost': 0, 'pnls': []}
            if p['status'] == 'OPEN': by_algo[a]['open'] += 1
            elif p['status'] == 'WON': by_algo[a]['won'] += 1
            elif p['status'] == 'LOST': by_algo[a]['lost'] += 1
            if p.get('pnl_pct') is not None:
                by_algo[a]['pnls'].append(p['pnl_pct'])
        for algo, stats in sorted(by_algo.items(), key=lambda x: -(x[1]['won'])):
            total = stats['won'] + stats['lost']
            wr = f"{stats['won']/total*100:.0f}%" if total > 0 else "N/A"
            avg = f"{sum(stats['pnls'])/len(stats['pnls']):+.2f}%" if stats['pnls'] else "N/A"
            print(f"    {algo:25s} Open:{stats['open']:3d} W:{stats['won']:3d} L:{stats['lost']:3d} WR:{wr:>5s} Avg:{avg}")


def _update_summary(data):
    picks = data['picks']
    won = sum(1 for p in picks if p['status'] == 'WON')
    lost = sum(1 for p in picks if p['status'] == 'LOST')
    open_count = sum(1 for p in picks if p['status'] == 'OPEN')
    pnls = [p['pnl_pct'] for p in picks if p.get('pnl_pct') is not None]
    data['summary'] = {
        'total_picks': len(picks),
        'open': open_count,
        'won': won,
        'lost': lost,
        'win_rate': round(won / (won + lost) * 100, 1) if (won + lost) > 0 else None,
        'avg_pnl_pct': round(sum(pnls) / len(pnls), 2) if pnls else None,
        'total_pnl_pct': round(sum(pnls), 2) if pnls else None,
        'last_generate': data.get('last_generate'),
        'last_resolve': data.get('last_resolve'),
    }


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "generate":
        cmd_generate()
    elif cmd == "resolve":
        cmd_resolve()
    elif cmd == "status":
        cmd_status()
    else:
        print(f"Usage: {sys.argv[0]} [generate|resolve|status]")
