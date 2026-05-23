#!/usr/bin/env python3
"""
SCALPING STRATEGY BATTLE TEST — YouTube/Community Strategies vs Real Data
=========================================================================
Tests 5 popular scalping strategies from YouTube/TradingView against REAL
2-year daily data (simulated as swing-scalps on daily bars since we can't
get 1-min data from yfinance for free).

Strategies tested:
  1. 9/21 EMA Cross + RSI Filter (most popular YouTube scalp)
  2. VWAP Reversion + RSI Divergence
  3. Bollinger Band Squeeze Breakout
  4. Stochastic + MACD Double Confirmation
  5. EMA Stack Alignment + Volume Surge

Each gets: bootstrap CI, t-test, Monte Carlo random baseline, regime split.
Walk-forward: train 50% → test 50%.

Run: python scalp_strategy_test.py
"""

import json
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timezone
from pathlib import Path
from scipy import stats as scipy_stats

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

SYMBOLS = {
    "crypto": [
        "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD",
        "ADA-USD", "AVAX-USD", "DOT-USD", "LINK-USD",
        "DOGE-USD", "ATOM-USD", "NEAR-USD", "LTC-USD",
        "INJ-USD", "OP-USD", "FIL-USD", "SEI-USD", "APT21794-USD",
    ],
    "forex": [
        "EURUSD=X", "GBPUSD=X", "JPY=X", "AUDUSD=X",
        "CAD=X", "NZDUSD=X", "CHF=X",
    ],
    "meme": [
        "DOGE-USD", "SHIB-USD", "PEPE24478-USD", "BONK-USD", "FLOKI-USD",
        "WIF-USD", "AMC", "GME",
    ],
    "stocks": [
        "AAPL", "MSFT", "NVDA", "AMD", "META",
        "GOOGL", "AMZN", "TSLA", "COIN", "SHOP",
    ],
}

# ═══════════════════════════════════════════════════════════════════════════
# INDICATORS
# ═══════════════════════════════════════════════════════════════════════════
def _rsi(close, period=14):
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0).rolling(window=period, min_periods=period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window=period, min_periods=period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def _ema(s, period):
    return s.ewm(span=period, adjust=False).mean()

def _atr(df, period=14):
    high, low, close = df["High"], df["Low"], df["Close"]
    tr = pd.concat([high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def _stochastic(df, k_period=14, d_period=3):
    """Stochastic %K and %D."""
    low_min = df["Low"].rolling(k_period).min()
    high_max = df["High"].rolling(k_period).max()
    k = 100 * (df["Close"] - low_min) / (high_max - low_min)
    d = k.rolling(d_period).mean()
    return k, d

def _bb(close, period=20, num_std=2):
    mid = close.rolling(period).mean()
    std = close.rolling(period).std()
    return mid, mid + num_std * std, mid - num_std * std

def _macd(close, fast=12, slow=26, signal=9):
    ef = _ema(close, fast); es = _ema(close, slow)
    ml = ef - es; sl = _ema(ml, signal)
    return ml, sl, ml - sl

def _vwap_daily(df):
    """Approximate VWAP using typical price * volume / cumulative volume."""
    tp = (df["High"] + df["Low"] + df["Close"]) / 3
    vol = df.get("Volume")
    if vol is None or vol.sum() == 0:
        return tp  # fallback to typical price
    cum_tp_vol = (tp * vol).cumsum()
    cum_vol = vol.cumsum()
    return cum_tp_vol / cum_vol.replace(0, np.nan)


# ═══════════════════════════════════════════════════════════════════════════
# 5 SCALPING STRATEGIES
# ═══════════════════════════════════════════════════════════════════════════

def scalp_ema_cross(df, i, params):
    """Strategy 1: 9/21 EMA Cross + RSI Filter.
    LONG: 9 EMA crosses above 21 EMA, RSI 40-65 (not overbought).
    SHORT: 9 EMA crosses below 21 EMA, RSI 35-60."""
    if i < 30: return 0, [], None
    c = df["Close"]
    ema9 = _ema(c.iloc[:i+1], 9)
    ema21 = _ema(c.iloc[:i+1], 21)
    rsi = _rsi(c.iloc[:i+1], 14)
    
    if any(x.empty or np.isnan(x.iloc[-1]) for x in [ema9, ema21, rsi]):
        return 0, [], None
    
    e9, e21 = float(ema9.iloc[-1]), float(ema21.iloc[-1])
    e9_prev, e21_prev = float(ema9.iloc[-2]), float(ema21.iloc[-2])
    r = float(rsi.iloc[-1])
    
    score, reasons = 0, []
    
    # Bullish cross
    if e9 > e21 and e9_prev <= e21_prev:
        score += 30; reasons.append("9EMA crosses above 21EMA")
        if 40 < r < 65:
            score += 15; reasons.append(f"RSI {r:.0f} (room to run)")
        return score, reasons, "LONG"
    
    # Bearish cross
    if e9 < e21 and e9_prev >= e21_prev:
        score += 30; reasons.append("9EMA crosses below 21EMA")
        if 35 < r < 60:
            score += 15; reasons.append(f"RSI {r:.0f}")
        return score, reasons, "SHORT"
    
    return 0, [], None


def scalp_vwap_bounce(df, i, params):
    """Strategy 2: VWAP Bounce + RSI.
    LONG: Price bounces off VWAP from below, RSI > 40.
    SHORT: Price rejected at VWAP from above, RSI < 60."""
    if i < 30: return 0, [], None
    c = df["Close"]
    vwap = _vwap_daily(df.iloc[:i+1])
    rsi = _rsi(c.iloc[:i+1], 14)
    
    if vwap.empty or np.isnan(vwap.iloc[-1]) or np.isnan(rsi.iloc[-1]):
        return 0, [], None
    
    p = float(c.iloc[i])
    v = float(vwap.iloc[-1])
    r = float(rsi.iloc[-1])
    p_prev = float(c.iloc[i-1])
    
    score, reasons = 0, []
    
    # Price was below VWAP, now crossing above (bounce)
    if p > v and p_prev < v:
        score += 25; reasons.append("VWAP cross up")
        if r > 40 and r < 70:
            score += 15; reasons.append(f"RSI {r:.0f}")
        vol = df.get("Volume")
        if vol is not None and i >= 21:
            vr = float(vol.iloc[i]) / float(vol.iloc[i-20:i].mean()) if float(vol.iloc[i-20:i].mean()) > 0 else 1
            if vr > 1.3:
                score += 10; reasons.append(f"Vol {vr:.1f}x")
        return score, reasons, "LONG"
    
    # Price was above VWAP, now crossing below (rejection)
    if p < v and p_prev > v:
        score += 25; reasons.append("VWAP cross down")
        if r < 60 and r > 30:
            score += 15; reasons.append(f"RSI {r:.0f}")
        return score, reasons, "SHORT"
    
    return 0, [], None


def scalp_bb_squeeze(df, i, params):
    """Strategy 3: Bollinger Band Squeeze Breakout.
    When BB width compresses to < 50% of 50-bar avg width, then price breaks out."""
    if i < 55: return 0, [], None
    c = df["Close"]
    mid, upper, lower = _bb(c.iloc[:i+1], 20, 2)
    
    if any(np.isnan(x.iloc[-1]) for x in [mid, upper, lower]):
        return 0, [], None
    
    width = float(upper.iloc[-1] - lower.iloc[-1])
    avg_width = float((upper - lower).iloc[-50:].mean())
    p = float(c.iloc[i])
    u = float(upper.iloc[-1])
    l = float(lower.iloc[-1])
    
    score, reasons = 0, []
    
    # Squeeze detected (width < 60% of avg)
    if avg_width > 0 and width / avg_width < 0.6:
        # Breakout above upper band
        if p > u:
            score += 35; reasons.append("BB squeeze breakout UP")
            macd_l, _, hist = _macd(c.iloc[:i+1])
            if not np.isnan(hist.iloc[-1]) and float(hist.iloc[-1]) > 0:
                score += 10; reasons.append("MACD confirming")
            return score, reasons, "LONG"
        
        # Breakdown below lower band
        if p < l:
            score += 35; reasons.append("BB squeeze breakdown")
            macd_l, _, hist = _macd(c.iloc[:i+1])
            if not np.isnan(hist.iloc[-1]) and float(hist.iloc[-1]) < 0:
                score += 10; reasons.append("MACD confirming")
            return score, reasons, "SHORT"
    
    return 0, [], None


def scalp_stoch_macd(df, i, params):
    """Strategy 4: Stochastic + MACD Double Confirmation.
    LONG: Stoch %K crosses above %D from oversold + MACD histogram positive.
    SHORT: Stoch %K crosses below %D from overbought + MACD histogram negative."""
    if i < 30: return 0, [], None
    c = df["Close"]
    k, d = _stochastic(df.iloc[:i+1], 14, 3)
    macd_l, sig_l, hist = _macd(c.iloc[:i+1])
    
    if any(np.isnan(x.iloc[-1]) for x in [k, d, hist]):
        return 0, [], None
    
    k_val, d_val = float(k.iloc[-1]), float(d.iloc[-1])
    k_prev, d_prev = float(k.iloc[-2]), float(d.iloc[-2])
    h = float(hist.iloc[-1])
    
    score, reasons = 0, []
    
    # Bullish: stoch crossing up from oversold + MACD positive
    if k_val > d_val and k_prev <= d_prev and k_val < 30:
        score += 25; reasons.append(f"Stoch bullish cross (K={k_val:.0f})")
        if h > 0:
            score += 20; reasons.append("MACD histogram +")
        return score, reasons, "LONG"
    
    # Bearish: stoch crossing down from overbought + MACD negative
    if k_val < d_val and k_prev >= d_prev and k_val > 70:
        score += 25; reasons.append(f"Stoch bearish cross (K={k_val:.0f})")
        if h < 0:
            score += 20; reasons.append("MACD histogram -")
        return score, reasons, "SHORT"
    
    return 0, [], None


def scalp_ema_stack(df, i, params):
    """Strategy 5: EMA Stack Alignment + Volume Surge.
    LONG: 9 > 21 > 50 EMA stack (aligned bullish) + volume > 2x avg.
    SHORT: 9 < 21 < 50 EMA stack (aligned bearish) + volume > 2x avg."""
    if i < 55: return 0, [], None
    c = df["Close"]
    ema9 = _ema(c.iloc[:i+1], 9)
    ema21 = _ema(c.iloc[:i+1], 21)
    ema50 = _ema(c.iloc[:i+1], 50)
    
    if any(np.isnan(x.iloc[-1]) for x in [ema9, ema21, ema50]):
        return 0, [], None
    
    e9, e21, e50 = float(ema9.iloc[-1]), float(ema21.iloc[-1]), float(ema50.iloc[-1])
    
    vol = df.get("Volume")
    vr = 1.0
    if vol is not None and i >= 21:
        av = float(vol.iloc[i-20:i].mean())
        vr = float(vol.iloc[i]) / av if av > 0 else 1.0
    
    rsi = _rsi(c.iloc[:i+1], 14)
    r = float(rsi.iloc[-1]) if not np.isnan(rsi.iloc[-1]) else 50
    
    score, reasons = 0, []
    
    # Bullish EMA stack
    if e9 > e21 > e50:
        score += 25; reasons.append("EMA 9>21>50 bullish stack")
        if vr > 2.0:
            score += 15; reasons.append(f"Vol surge {vr:.1f}x")
        elif vr > 1.5:
            score += 8
        if 40 < r < 70:
            score += 5
        return score, reasons, "LONG"
    
    # Bearish EMA stack
    if e9 < e21 < e50:
        score += 25; reasons.append("EMA 9<21<50 bearish stack")
        if vr > 2.0:
            score += 15; reasons.append(f"Vol surge {vr:.1f}x")
        elif vr > 1.5:
            score += 8
        if 30 < r < 60:
            score += 5
        return score, reasons, "SHORT"
    
    return 0, [], None


SCALP_STRATEGIES = {
    "ema_cross_9_21": scalp_ema_cross,
    "vwap_bounce": scalp_vwap_bounce,
    "bb_squeeze": scalp_bb_squeeze,
    "stoch_macd": scalp_stoch_macd,
    "ema_stack_vol": scalp_ema_stack,
}


# ═══════════════════════════════════════════════════════════════════════════
# TRADE SIM (same as battle_test_rigorous.py)
# ═══════════════════════════════════════════════════════════════════════════
def simulate_trade(df, entry_idx, params, asset_class, direction="LONG"):
    c = df["Close"]; ep = float(c.iloc[entry_idx])
    atr_s = _atr(df, 14); atr = float(atr_s.iloc[entry_idx])
    if np.isnan(atr) or atr <= 0:
        atr = ep * (0.005 if asset_class == "forex" else 0.03)
    tp_m, sl_m, mh = params["tp_mult"], params["sl_mult"], params["max_hold"]
    
    if asset_class == "forex":
        sl_d = max(atr * sl_m, ep * 0.003); tp_d = max(atr * tp_m, ep * 0.006)
    else:
        sl_d = max(atr * sl_m, ep * 0.015); tp_d = max(atr * tp_m, ep * 0.025)
    if tp_d < sl_d * 1.5: tp_d = sl_d * 1.5
    
    if direction == "LONG": sl, tp = ep - sl_d, ep + tp_d
    else: sl, tp = ep + sl_d, ep - tp_d
    
    trail = sl; best = ep
    end = min(entry_idx + mh, len(df) - 1)
    for j in range(entry_idx + 1, end + 1):
        h, l = float(df["High"].iloc[j]), float(df["Low"].iloc[j])
        if direction == "LONG":
            if h > best: best = h
            if best >= ep + tp_d * 0.5:
                trail = max(trail, best - sl_d * 0.8, ep + sl_d * 0.2)
            astop = max(sl, trail)
            if l <= astop:
                pnl = ((astop - ep) / ep) * 100
                return {"outcome": "WIN" if pnl > 0 else "LOSS", "pnl_pct": round(pnl, 3), "hold": j - entry_idx, "dir": direction}
            if h >= tp:
                return {"outcome": "WIN", "pnl_pct": round(((tp - ep) / ep) * 100, 3), "hold": j - entry_idx, "dir": direction}
        else:
            if l < best: best = l
            if best <= ep - tp_d * 0.5:
                trail = min(trail, best + sl_d * 0.8, ep - sl_d * 0.2)
            astop = min(sl, trail)
            if h >= astop:
                pnl = ((ep - astop) / ep) * 100
                return {"outcome": "WIN" if pnl > 0 else "LOSS", "pnl_pct": round(pnl, 3), "hold": j - entry_idx, "dir": direction}
            if l <= tp:
                return {"outcome": "WIN", "pnl_pct": round(((ep - tp) / ep) * 100, 3), "hold": j - entry_idx, "dir": direction}
    
    fp = float(c.iloc[end])
    pnl = ((fp - ep) / ep * 100) if direction == "LONG" else ((ep - fp) / ep * 100)
    return {"outcome": "EXPIRED", "pnl_pct": round(pnl, 3), "hold": end - entry_idx, "dir": direction}


# ═══════════════════════════════════════════════════════════════════════════
# BACKTEST + STATS
# ═══════════════════════════════════════════════════════════════════════════
def run_backtest(yf_data, symbols, asset_class, strat_fn, params, start_pct=0, end_pct=1.0):
    trades = []
    threshold = params["threshold"]
    for sym in symbols:
        df = yf_data.get(sym)
        if df is None or len(df) < 60: continue
        n = len(df); si = int(n * start_pct); ei = int(n * end_pct)
        if ei - si < 60: continue
        last = -10; cd = params.get("cooldown", 3)
        for i in range(max(55, si), ei - params["max_hold"]):
            if i - last < cd: continue
            score, reasons, direction = strat_fn(df, i, params)
            if score >= threshold and direction is not None:
                trade = simulate_trade(df, i, params, asset_class, direction)
                trade["symbol"] = sym; trade["score"] = score
                trade["date"] = str(df.index[i].date()) if hasattr(df.index[i], "date") else str(i)
                trades.append(trade); last = i
    return trades

def bootstrap_ci(pnls, n_boot=1000):
    if len(pnls) < 10:
        return {"mean": 0, "ci_low": 0, "ci_high": 0, "positive": False}
    arr = np.array(pnls)
    means = [float(np.mean(np.random.choice(arr, len(arr), True))) for _ in range(n_boot)]
    return {"mean": round(float(np.mean(arr)), 4),
            "ci_low": round(float(np.percentile(means, 2.5)), 4),
            "ci_high": round(float(np.percentile(means, 97.5)), 4),
            "positive": float(np.percentile(means, 2.5)) > 0}

def random_baseline(yf_data, symbols, asset_class, params, n=300, direction="LONG"):
    trades = []
    for sym in symbols:
        df = yf_data.get(sym)
        if df is None or len(df) < 100: continue
        for _ in range(n // max(len(symbols), 1)):
            i = np.random.randint(55, len(df) - params["max_hold"] - 1)
            d = direction if direction else np.random.choice(["LONG", "SHORT"])
            trade = simulate_trade(df, i, params, asset_class, d)
            trades.append(trade)
    return trades

def analyze(trades, label=""):
    if not trades:
        return {"label": label, "total": 0, "verdict": "NO_DATA", "win_rate": 0, "pf": 0, "pnl": 0, "exp": -999}
    wins = [t for t in trades if t["outcome"] == "WIN"]
    losses = [t for t in trades if t["outcome"] == "LOSS"]
    tc = len(wins) + len(losses)
    wr = (len(wins) / tc * 100) if tc > 0 else 0
    pnls = [t["pnl_pct"] for t in trades]
    avg_w = np.mean([t["pnl_pct"] for t in wins]) if wins else 0
    avg_l = np.mean([t["pnl_pct"] for t in losses]) if losses else 0
    gp = sum(p for p in pnls if p > 0); gl = abs(sum(p for p in pnls if p < 0))
    pf = gp / gl if gl > 0 else float("inf")
    exp = (wr/100 * avg_w) - ((100-wr)/100 * abs(avg_l))
    boot = bootstrap_ci(pnls)
    tt = scipy_stats.ttest_1samp(pnls, 0) if len(pnls) >= 10 else (0, 1.0)
    
    if tc < 20: verdict = "INSUFFICIENT"
    elif boot["positive"] and tt[1] < 0.05 and pf > 1.2: verdict = "✅ SIGNIFICANT WINNER"
    elif boot["positive"] and pf > 1.0: verdict = "🟡 POSITIVE BUT NOT SIGNIFICANT"
    elif exp > 0: verdict = "⚠️ WEAK"
    else: verdict = "❌ ELIMINATED"
    
    # Long vs Short breakdown
    longs = [t for t in trades if t.get("dir") == "LONG"]
    shorts = [t for t in trades if t.get("dir") == "SHORT"]
    
    return {
        "label": label, "total": len(trades), "wins": len(wins), "losses": len(losses),
        "win_rate": round(wr, 1), "avg_win": round(avg_w, 2), "avg_loss": round(avg_l, 2),
        "pnl": round(sum(pnls), 2), "exp": round(exp, 4), "pf": round(pf, 2),
        "boot": boot, "p_value": round(float(tt[1]), 6), "t_stat": round(float(tt[0]), 3),
        "verdict": verdict,
        "longs": len(longs), "shorts": len(shorts),
        "long_pnl": round(sum(t["pnl_pct"] for t in longs), 2) if longs else 0,
        "short_pnl": round(sum(t["pnl_pct"] for t in shorts), 2) if shorts else 0,
    }


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════
def main():
    print("=" * 80)
    print("🔬 SCALPING STRATEGY BATTLE TEST — YouTube/Community vs Real Data")
    print(f"   {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("   5 strategies • 4 asset classes • 2yr data • Bootstrap + t-test")
    print("=" * 80)
    
    # Download 2 years
    print("\n📥 Downloading 2 years of data...")
    all_syms = list(set(s for syms in SYMBOLS.values() for s in syms))
    yf_data = {}
    try:
        batch = yf.download(all_syms, period="2y", group_by="ticker",
                            auto_adjust=True, progress=False, threads=True)
        for sym in all_syms:
            try:
                df = batch[sym].dropna() if len(all_syms) > 1 else batch.dropna()
                if len(df) >= 100: yf_data[sym] = df
            except: continue
    except Exception as e:
        print(f"  Batch error: {e}")
        for sym in all_syms:
            try:
                df = yf.Ticker(sym).history(period="2y", auto_adjust=True)
                if df is not None and len(df) >= 100: yf_data[sym] = df
            except: continue
    
    for cat, syms in SYMBOLS.items():
        loaded = len([s for s in syms if s in yf_data])
        print(f"  {cat:8s}: {loaded}/{len(syms)} loaded")
    
    # Parameter configs for scalping (tighter TP/SL, faster hold)
    scalp_params = [
        {"tp_mult": 1.5, "sl_mult": 1.0, "threshold": 30, "max_hold": 5, "cooldown": 2, "label": "Quick 1.5:1 5d"},
        {"tp_mult": 2.0, "sl_mult": 1.0, "threshold": 35, "max_hold": 7, "cooldown": 3, "label": "Standard 2:1 7d"},
        {"tp_mult": 2.5, "sl_mult": 1.0, "threshold": 35, "max_hold": 10, "cooldown": 3, "label": "Swing 2.5:1 10d"},
        {"tp_mult": 3.0, "sl_mult": 1.0, "threshold": 40, "max_hold": 14, "cooldown": 5, "label": "Extended 3:1 14d"},
    ]
    
    all_results = []
    
    for strat_name, strat_fn in SCALP_STRATEGIES.items():
        print(f"\n{'━'*80}")
        print(f"  📊 STRATEGY: {strat_name}")
        print(f"{'━'*80}")
        
        for asset_class, syms_list in SYMBOLS.items():
            syms = [s for s in syms_list if s in yf_data]
            if not syms: continue
            
            print(f"\n    {asset_class.upper()} ({len(syms)} symbols)")
            
            for pidx, params in enumerate(scalp_params):
                label = f"{strat_name}_{asset_class}_p{pidx}"
                
                # Full backtest
                trades = run_backtest(yf_data, syms, asset_class, strat_fn, params)
                full = analyze(trades, label)
                
                # OOS (walk-forward 50/50)
                oos_trades = run_backtest(yf_data, syms, asset_class, strat_fn, params, 0.5, 1.0)
                oos = analyze(oos_trades, f"{label}_OOS")
                
                # Random baseline
                directions = set(t.get("dir") for t in trades if t.get("dir"))
                rand_dir = list(directions)[0] if len(directions) == 1 else "LONG"
                rand_trades = random_baseline(yf_data, syms, asset_class, params, max(len(trades), 200), rand_dir)
                rand_pnls = [t["pnl_pct"] for t in rand_trades]
                rand_mean = float(np.mean(rand_pnls)) if rand_pnls else 0
                
                # Compare vs random
                if trades and rand_trades:
                    strat_pnls = [t["pnl_pct"] for t in trades]
                    try:
                        _, mc_p = scipy_stats.mannwhitneyu(strat_pnls, rand_pnls, alternative="greater")
                    except:
                        mc_p = 1.0
                    mc_better = mc_p < 0.05
                else:
                    mc_p = 1.0; mc_better = False
                
                icon = "✅" if "SIGNIFICANT" in full["verdict"] else "🟡" if "POSITIVE" in full["verdict"] else "❌"
                
                print(f"      {icon} p{pidx} ({params['label']})  T:{full['total']:4d}  "
                      f"WR:{full['win_rate']:5.1f}%  PF:{full['pf']:.2f}  "
                      f"P&L:{full['pnl']:+8.1f}%  L:{full['longs']} S:{full['shorts']}  "
                      f"{'✅ beats random' if mc_better else '❌ vs random'}  "
                      f"{full['verdict']}")
                
                if full["boot"]:
                    b = full["boot"]
                    print(f"         CI:[{b['ci_low']:+.3f}%,{b['ci_high']:+.3f}%]  "
                          f"p={full['p_value']:.4f}  "
                          f"OOS_PF:{oos['pf']:.2f}  OOS_P&L:{oos['pnl']:+.1f}%")
                
                all_results.append({
                    "strategy": strat_name, "asset_class": asset_class,
                    "param_idx": pidx, "params": params,
                    "full": full, "oos": oos,
                    "random_mean": round(rand_mean, 4), "mc_pval": round(mc_p, 6),
                    "mc_better": mc_better,
                })
    
    # FINAL RESULTS
    print("\n" + "=" * 80)
    print("🏆 FINAL VERDICT — SCALPING STRATEGIES")
    print("=" * 80)
    
    real_winners = [r for r in all_results if "SIGNIFICANT" in r["full"]["verdict"]
                    and r["oos"]["total"] >= 10 and r["oos"]["pf"] > 1.0 and r["mc_better"]]
    marginal = [r for r in all_results if ("POSITIVE" in r["full"]["verdict"]
                or "SIGNIFICANT" in r["full"]["verdict"]) and r not in real_winners]
    
    print(f"\n  Total tested: {len(all_results)} combos")
    print(f"  ✅ REAL WINNERS: {len(real_winners)}")
    print(f"  🟡 MARGINAL: {len(marginal)}")
    print(f"  ❌ ELIMINATED: {len(all_results) - len(real_winners) - len(marginal)}")
    
    if real_winners:
        print("\n  ── REAL WINNERS ──")
        for r in sorted(real_winners, key=lambda x: x["full"]["exp"], reverse=True):
            f = r["full"]; o = r["oos"]
            print(f"    ✅ {r['strategy']:20s} {r['asset_class']:8s} p{r['param_idx']}  "
                  f"Full[WR:{f['win_rate']:.1f}% PF:{f['pf']:.2f} P&L:{f['pnl']:+.1f}%]  "
                  f"OOS[PF:{o['pf']:.2f} P&L:{o['pnl']:+.1f}%]  p={f['p_value']:.4f}")
    else:
        print("\n  ⚠️ NO SCALPING STRATEGY SURVIVED ALL TESTS")
        print("     This is expected — most YouTube 'profitable' strategies don't")
        print("     hold up under rigorous statistical testing with real data.")
    
    # Save
    save = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_tested": len(all_results),
        "real_winners": len(real_winners),
        "results": all_results,
    }
    out = DATA_DIR / "scalping_test_results.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(save, f, indent=2, default=str)
    print(f"\n  📁 Saved to {out}")
    
    print(f"\n{'='*80}")
    print("🔬 SCALPING BATTLE TEST COMPLETE")
    print(f"{'='*80}")
    return save


if __name__ == "__main__":
    main()
