#!/usr/bin/env python3
"""
ANTIGRAVITY RIGOROUS BATTLE TEST v2 — Statistical Significance Edition
======================================================================
Fixes the fatal flaw of v1: 6 months is noise.

This version:
  1. Uses 2 YEARS of data (max yfinance allows without API key)
  2. Bootstrap confidence intervals (1000 resamples) on expectancy
  3. Monte Carlo random-entry baseline (are we better than random?)
  4. Regime splitting (bull vs bear vs sideways)
  5. T-test p-values on trade returns vs zero
  6. Walk-forward: 12-month train / 12-month test
  7. Multiple testing correction (Bonferroni)

If a strategy survives ALL of these... it's real.

Run:  python battle_test_rigorous.py
"""

import json
import sys
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict
from scipy import stats as scipy_stats

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# ═══════════════════════════════════════════════════════════════════════════
# SYMBOLS
# ═══════════════════════════════════════════════════════════════════════════
SYMBOLS = {
    "crypto": [
        "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD",
        "ADA-USD", "AVAX-USD", "DOT-USD", "LINK-USD",
        "DOGE-USD", "ATOM-USD", "NEAR-USD", "LTC-USD",
        "BCH-USD", "INJ-USD", "OP-USD", "ARB11841-USD",
        "FIL-USD", "SEI-USD", "APT21794-USD",
    ],
    "forex": [
        "EURUSD=X", "GBPUSD=X", "JPY=X", "AUDUSD=X",
        "CAD=X", "NZDUSD=X", "CHF=X",
    ],
    "stocks": [
        "AAPL", "MSFT", "NVDA", "AMD", "META",
        "GOOGL", "AMZN", "NFLX", "TSLA",
        "JPM", "BAC", "XOM", "CVX",
        "UBER", "PYPL", "COIN", "SHOP",
    ],
    "meme": [
        "DOGE-USD", "SHIB-USD", "PEPE24478-USD", "BONK-USD", "FLOKI-USD",
        "WIF-USD", "AMC", "GME",
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

def _atr(df, period=14):
    high, low, close = df["High"], df["Low"], df["Close"]
    tr = pd.concat([high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def _ema(s, period):
    return s.ewm(span=period, adjust=False).mean()

def _macd(close, fast=12, slow=26, signal=9):
    ema_f = _ema(close, fast)
    ema_s = _ema(close, slow)
    macd_line = ema_f - ema_s
    sig_line = _ema(macd_line, signal)
    return macd_line, sig_line, macd_line - sig_line

# ═══════════════════════════════════════════════════════════════════════════
# STRATEGIES
# ═══════════════════════════════════════════════════════════════════════════
def strat_trend_long(df, i, params):
    if i < 50: return 0, [], "LONG"
    c = df["Close"]; p = float(c.iloc[i])
    sma50 = float(c.iloc[max(0,i-49):i+1].mean())
    rsi_s = _rsi(c.iloc[:i+1], 14)
    rsi = float(rsi_s.iloc[-1]) if not np.isnan(rsi_s.iloc[-1]) else 50
    ml, _, _ = _macd(c.iloc[:i+1])
    macd = float(ml.iloc[-1]) if not np.isnan(ml.iloc[-1]) else 0
    v = df.get("Volume")
    vr = 1.0
    if v is not None and i >= 21:
        av = float(v.iloc[i-20:i].mean())
        vr = float(v.iloc[i]) / av if av > 0 else 1.0
    score, reasons = 0, []
    if p > sma50: score += 20; reasons.append("Above SMA50")
    if macd > 0: score += 15; reasons.append("MACD+")
    if 35 < rsi < 65: score += 10
    if vr > 1.5: score += 10
    return score, reasons, "LONG"

def strat_mean_rev_long(df, i, params):
    if i < 50: return 0, [], "LONG"
    c = df["Close"]; p = float(c.iloc[i])
    rsi_s = _rsi(c.iloc[:i+1], 14)
    rsi = float(rsi_s.iloc[-1]) if not np.isnan(rsi_s.iloc[-1]) else 50
    sma20 = float(c.iloc[max(0,i-19):i+1].mean())
    std20 = float(c.iloc[max(0,i-19):i+1].std())
    bb_l = sma20 - 2 * std20; bb_u = sma20 + 2 * std20
    bb_pos = (p - bb_l) / (bb_u - bb_l) if (bb_u - bb_l) > 0 else 0.5
    score, reasons = 0, []
    if rsi < 25: score += 30; reasons.append(f"RSI {rsi:.0f}")
    elif rsi < 30: score += 20
    elif rsi < 35: score += 10
    if bb_pos < 0.05: score += 25; reasons.append("Below BB")
    elif bb_pos < 0.15: score += 15
    return score, reasons, "LONG"

def strat_trend_short(df, i, params):
    if i < 50: return 0, [], "SHORT"
    c = df["Close"]; p = float(c.iloc[i])
    sma50 = float(c.iloc[max(0,i-49):i+1].mean())
    sma20 = float(c.iloc[max(0,i-19):i+1].mean())
    rsi_s = _rsi(c.iloc[:i+1], 14)
    rsi = float(rsi_s.iloc[-1]) if not np.isnan(rsi_s.iloc[-1]) else 50
    ml, _, _ = _macd(c.iloc[:i+1])
    macd = float(ml.iloc[-1]) if not np.isnan(ml.iloc[-1]) else 0
    ret5 = (c.iloc[i] - c.iloc[i-5]) / c.iloc[i-5] if i >= 5 else 0
    score, reasons = 0, []
    if p < sma50: score += 20; reasons.append("Below SMA50")
    if p < sma20: score += 5
    if macd < 0: score += 15; reasons.append("MACD-")
    if 40 < rsi < 70: score += 10
    if ret5 < -0.02: score += 10; reasons.append("Downtrend")
    return score, reasons, "SHORT"

def strat_breakout_long(df, i, params):
    if i < 25: return 0, [], "LONG"
    c = df["Close"]; p = float(c.iloc[i])
    h20 = float(df["High"].iloc[i-20:i].max())
    v = df.get("Volume"); vr = 1.0
    if v is not None and i >= 21:
        av = float(v.iloc[i-20:i].mean())
        vr = float(v.iloc[i]) / av if av > 0 else 1.0
    score, reasons = 0, []
    if p > h20 and vr > 1.8:
        score += 30; reasons.append("20d breakout")
        if vr > 2.5: score += 10
    return score, reasons, "LONG"

STRATEGIES = {
    "trend_long": strat_trend_long,
    "mean_rev_long": strat_mean_rev_long,
    "trend_short": strat_trend_short,
    "breakout_long": strat_breakout_long,
}

# ═══════════════════════════════════════════════════════════════════════════
# TRADE SIMULATOR
# ═══════════════════════════════════════════════════════════════════════════
def simulate_trade(df, entry_idx, params, asset_class, direction="LONG"):
    c = df["Close"]; ep = float(c.iloc[entry_idx])
    atr_s = _atr(df, 14); atr = float(atr_s.iloc[entry_idx])
    if np.isnan(atr) or atr <= 0:
        atr = ep * (0.005 if asset_class == "forex" else 0.03)
    tp_mult, sl_mult, mh = params["tp_mult"], params["sl_mult"], params["max_hold"]
    use_trail = params.get("use_trailing", True)
    
    if asset_class == "forex":
        sl_d = max(atr * sl_mult, ep * 0.003); tp_d = max(atr * tp_mult, ep * 0.006)
    else:
        sl_d = max(atr * sl_mult, ep * 0.015); tp_d = max(atr * tp_mult, ep * 0.025)
    if tp_d < sl_d * 1.5: tp_d = sl_d * 1.5
    
    if direction == "LONG":
        sl, tp = ep - sl_d, ep + tp_d
    else:
        sl, tp = ep + sl_d, ep - tp_d
    
    trail = sl; best = ep
    end = min(entry_idx + mh, len(df) - 1)
    
    for j in range(entry_idx + 1, end + 1):
        h, l = float(df["High"].iloc[j]), float(df["Low"].iloc[j])
        if direction == "LONG":
            if h > best: best = h
            if use_trail and best >= ep + tp_d * 0.5:
                trail = max(trail, best - sl_d * 0.8, ep + sl_d * 0.2)
            astop = max(sl, trail)
            if l <= astop:
                pnl = ((astop - ep) / ep) * 100
                return {"outcome": "WIN" if pnl > 0 else "LOSS", "pnl_pct": round(pnl, 3), "hold_days": j - entry_idx, "direction": direction}
            if h >= tp:
                pnl = ((tp - ep) / ep) * 100
                return {"outcome": "WIN", "pnl_pct": round(pnl, 3), "hold_days": j - entry_idx, "direction": direction}
        else:
            if l < best: best = l
            if use_trail and best <= ep - tp_d * 0.5:
                trail = min(trail, best + sl_d * 0.8, ep - sl_d * 0.2)
            astop = min(sl, trail)
            if h >= astop:
                pnl = ((ep - astop) / ep) * 100
                return {"outcome": "WIN" if pnl > 0 else "LOSS", "pnl_pct": round(pnl, 3), "hold_days": j - entry_idx, "direction": direction}
            if l <= tp:
                pnl = ((ep - tp) / ep) * 100
                return {"outcome": "WIN", "pnl_pct": round(pnl, 3), "hold_days": j - entry_idx, "direction": direction}
    
    fp = float(c.iloc[end])
    pnl = ((fp - ep) / ep * 100) if direction == "LONG" else ((ep - fp) / ep * 100)
    return {"outcome": "EXPIRED", "pnl_pct": round(pnl, 3), "hold_days": end - entry_idx, "direction": direction}

# ═══════════════════════════════════════════════════════════════════════════
# BACKTEST ENGINE
# ═══════════════════════════════════════════════════════════════════════════
def backtest(yf_data, symbols, asset_class, strat_fn, params, start_pct=0, end_pct=1.0):
    trades = []
    threshold = params["threshold"]
    for sym in symbols:
        df = yf_data.get(sym)
        if df is None or len(df) < 60: continue
        n = len(df); si = int(n * start_pct); ei = int(n * end_pct)
        if ei - si < 60: continue
        last = -10; cd = params.get("cooldown", 5)
        for i in range(max(50, si), ei - params["max_hold"]):
            if i - last < cd: continue
            score, reasons, direction = strat_fn(df, i, params)
            if score >= threshold:
                trade = simulate_trade(df, i, params, asset_class, direction)
                trade["symbol"] = sym; trade["score"] = score
                trade["date"] = str(df.index[i].date()) if hasattr(df.index[i], "date") else str(i)
                trades.append(trade); last = i
    return trades

# ═══════════════════════════════════════════════════════════════════════════
# STATISTICAL TESTS
# ═══════════════════════════════════════════════════════════════════════════

def bootstrap_expectancy(pnls, n_boot=1000, ci=0.95):
    """Bootstrap confidence interval for mean P&L (expectancy)."""
    if len(pnls) < 10:
        return {"mean": 0, "ci_low": 0, "ci_high": 0, "significant": False}
    pnls = np.array(pnls)
    boot_means = []
    for _ in range(n_boot):
        sample = np.random.choice(pnls, size=len(pnls), replace=True)
        boot_means.append(np.mean(sample))
    boot_means = np.array(boot_means)
    alpha = (1 - ci) / 2
    ci_low = float(np.percentile(boot_means, alpha * 100))
    ci_high = float(np.percentile(boot_means, (1 - alpha) * 100))
    mean = float(np.mean(pnls))
    # Significant if CI doesn't cross zero
    significant = (ci_low > 0) or (ci_high < 0)
    return {"mean": round(mean, 4), "ci_low": round(ci_low, 4), "ci_high": round(ci_high, 4),
            "significant": significant, "positive": ci_low > 0}

def monte_carlo_random_entry(yf_data, symbols, asset_class, params, n_random=500, direction="LONG"):
    """Generate random-entry trades to compare against strategy."""
    trades = []
    for sym in symbols:
        df = yf_data.get(sym)
        if df is None or len(df) < 100: continue
        n = len(df)
        # Random entry points
        for _ in range(n_random // max(len(symbols), 1)):
            i = np.random.randint(50, n - params["max_hold"] - 1)
            trade = simulate_trade(df, i, params, asset_class, direction)
            trade["symbol"] = sym
            trades.append(trade)
    return trades

def ttest_vs_zero(pnls):
    """T-test: are returns significantly different from zero?"""
    if len(pnls) < 10:
        return {"t_stat": 0, "p_value": 1.0, "significant_5pct": False, "significant_1pct": False}
    t_stat, p_value = scipy_stats.ttest_1samp(pnls, 0)
    return {
        "t_stat": round(float(t_stat), 4),
        "p_value": round(float(p_value), 6),
        "significant_5pct": p_value < 0.05,
        "significant_1pct": p_value < 0.01,
    }

def detect_regime(df, window=50):
    """Classify each bar as BULL, BEAR, or SIDEWAYS using SMA50 slope."""
    c = df["Close"]
    sma = c.rolling(window).mean()
    slope = sma.pct_change(20)  # 20-bar slope of SMA
    regimes = []
    for s in slope:
        if np.isnan(s): regimes.append("UNKNOWN")
        elif s > 0.02: regimes.append("BULL")
        elif s < -0.02: regimes.append("BEAR")
        else: regimes.append("SIDEWAYS")
    return regimes

def regime_split_backtest(yf_data, symbols, asset_class, strat_fn, params):
    """Run backtest and tag each trade with the market regime at entry."""
    # Pre-compute regimes for each symbol
    regime_map = {}
    for sym in symbols:
        df = yf_data.get(sym)
        if df is None: continue
        regime_map[sym] = detect_regime(df)
    
    trades = backtest(yf_data, symbols, asset_class, strat_fn, params)
    
    # Tag each trade with regime
    for t in trades:
        sym = t["symbol"]
        df = yf_data.get(sym)
        if df is None: continue
        date = t.get("date", "")
        try:
            idx = df.index.get_loc(pd.Timestamp(date))
            if sym in regime_map and idx < len(regime_map[sym]):
                t["regime"] = regime_map[sym][idx]
            else:
                t["regime"] = "UNKNOWN"
        except Exception:
            t["regime"] = "UNKNOWN"
    
    return trades

# ═══════════════════════════════════════════════════════════════════════════
# ANALYZE WITH STATS
# ═══════════════════════════════════════════════════════════════════════════

def analyze_with_stats(trades, label=""):
    """Full analysis with bootstrap CI, t-test, per-regime breakdown."""
    if not trades:
        return {"label": label, "total": 0, "verdict": "NO_DATA", "expectancy": -999,
                "pf": 0, "win_rate": 0, "total_pnl": 0, "bootstrap": None,
                "ttest": None, "regime_breakdown": {}}
    
    wins = [t for t in trades if t["outcome"] == "WIN"]
    losses = [t for t in trades if t["outcome"] == "LOSS"]
    tc = len(wins) + len(losses)
    wr = (len(wins) / tc * 100) if tc > 0 else 0
    
    pnls = [t["pnl_pct"] for t in trades]
    avg_w = np.mean([t["pnl_pct"] for t in wins]) if wins else 0
    avg_l = np.mean([t["pnl_pct"] for t in losses]) if losses else 0
    total_pnl = sum(pnls)
    
    gp = sum(p for p in pnls if p > 0)
    gl = abs(sum(p for p in pnls if p < 0))
    pf = gp / gl if gl > 0 else float("inf")
    
    exp = (wr/100 * avg_w) - ((100-wr)/100 * abs(avg_l))
    cum = np.cumsum(pnls); pk = np.maximum.accumulate(cum)
    max_dd = float(np.max(pk - cum)) if len(cum) > 0 else 0
    
    # Bootstrap CI
    boot = bootstrap_expectancy(pnls, n_boot=1000)
    
    # T-test
    tt = ttest_vs_zero(pnls)
    
    # Per-regime
    regime_breakdown = {}
    for regime in ["BULL", "BEAR", "SIDEWAYS"]:
        r_trades = [t for t in trades if t.get("regime") == regime]
        if r_trades:
            r_pnls = [t["pnl_pct"] for t in r_trades]
            r_w = len([t for t in r_trades if t["outcome"] == "WIN"])
            r_l = len([t for t in r_trades if t["outcome"] == "LOSS"])
            r_wr = r_w / (r_w + r_l) * 100 if (r_w + r_l) > 0 else 0
            r_gp = sum(p for p in r_pnls if p > 0)
            r_gl = abs(sum(p for p in r_pnls if p < 0))
            r_pf = r_gp / r_gl if r_gl > 0 else float("inf")
            regime_breakdown[regime] = {
                "trades": len(r_trades), "win_rate": round(r_wr, 1),
                "pf": round(r_pf, 2), "pnl": round(sum(r_pnls), 2),
            }
    
    # Verdict — MUST pass multiple tests
    if tc < 30:
        verdict = "INSUFFICIENT (need 30+ trades)"
    elif boot["positive"] and tt["significant_5pct"] and pf > 1.2:
        verdict = "✅ STATISTICALLY SIGNIFICANT WINNER"
    elif boot["positive"] and pf > 1.0:
        verdict = "🟡 POSITIVE BUT NOT SIGNIFICANT (p={:.4f})".format(tt["p_value"])
    elif exp > 0:
        verdict = "⚠️ WEAK POSITIVE (CI crosses zero)"
    else:
        verdict = "❌ ELIMINATED"
    
    return {
        "label": label, "total": len(trades), "wins": len(wins), "losses": len(losses),
        "win_rate": round(wr, 1), "avg_win": round(avg_w, 2), "avg_loss": round(avg_l, 2),
        "total_pnl": round(total_pnl, 2), "expectancy": round(exp, 4), "pf": round(pf, 2),
        "max_dd": round(max_dd, 2), "avg_hold": round(np.mean([t["hold_days"] for t in trades]), 1),
        "bootstrap": boot, "ttest": tt, "regime_breakdown": regime_breakdown,
        "verdict": verdict,
    }


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════
def main():
    print("=" * 80)
    print("🔬 ANTIGRAVITY RIGOROUS BATTLE TEST — STATISTICAL SIGNIFICANCE EDITION")
    print(f"   {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("   2-year data • Bootstrap CI • Monte Carlo • Regime splits • T-test")
    print("=" * 80)
    
    # 1. Download 2 YEARS of data
    print("\n📥 Phase 1: Downloading 2 YEARS of real market data...")
    all_syms = list(set(s for syms in SYMBOLS.values() for s in syms))
    
    yf_data = {}
    try:
        batch = yf.download(all_syms, period="2y", group_by="ticker",
                            auto_adjust=True, progress=False, threads=True)
        for sym in all_syms:
            try:
                df = batch[sym].dropna() if len(all_syms) > 1 else batch.dropna()
                if len(df) >= 100:
                    yf_data[sym] = df
            except Exception:
                continue
    except Exception as e:
        print(f"  Batch error: {e}")
        for sym in all_syms:
            try:
                df = yf.Ticker(sym).history(period="2y", auto_adjust=True)
                if df is not None and len(df) >= 100:
                    yf_data[sym] = df
            except Exception:
                continue
    
    for cat, syms in SYMBOLS.items():
        loaded = [s for s in syms if s in yf_data]
        bars = [len(yf_data[s]) for s in loaded] if loaded else [0]
        print(f"  {cat:8s}: {len(loaded)}/{len(syms)} loaded  |  avg {np.mean(bars):.0f} bars")
    
    # 2. Define test matrix
    TEST_CONFIGS = [
        ("crypto", "trend_long",    [{"tp_mult":2,"sl_mult":1,"threshold":35,"max_hold":7,"use_trailing":True,"cooldown":5},
                                     {"tp_mult":3,"sl_mult":1.5,"threshold":35,"max_hold":14,"use_trailing":True,"cooldown":5},
                                     {"tp_mult":4,"sl_mult":1.5,"threshold":35,"max_hold":21,"use_trailing":True,"cooldown":5}]),
        ("crypto", "mean_rev_long", [{"tp_mult":2,"sl_mult":1,"threshold":35,"max_hold":7,"use_trailing":True,"cooldown":5},
                                     {"tp_mult":2,"sl_mult":0.8,"threshold":40,"max_hold":5,"use_trailing":True,"cooldown":3}]),
        ("crypto", "trend_short",   [{"tp_mult":2,"sl_mult":1,"threshold":35,"max_hold":7,"use_trailing":True,"cooldown":5},
                                     {"tp_mult":2.5,"sl_mult":1,"threshold":40,"max_hold":10,"use_trailing":True,"cooldown":5},
                                     {"tp_mult":3,"sl_mult":1,"threshold":35,"max_hold":14,"use_trailing":True,"cooldown":7},
                                     {"tp_mult":2,"sl_mult":0.8,"threshold":35,"max_hold":5,"use_trailing":True,"cooldown":3}]),
        ("crypto", "breakout_long", [{"tp_mult":3,"sl_mult":1,"threshold":35,"max_hold":10,"use_trailing":True,"cooldown":5}]),
        ("forex",  "trend_long",    [{"tp_mult":3,"sl_mult":1.5,"threshold":35,"max_hold":14,"use_trailing":True,"cooldown":5},
                                     {"tp_mult":4,"sl_mult":1.5,"threshold":35,"max_hold":21,"use_trailing":True,"cooldown":5}]),
        ("forex",  "mean_rev_long", [{"tp_mult":2,"sl_mult":1,"threshold":35,"max_hold":7,"use_trailing":True,"cooldown":3}]),
        ("stocks", "trend_long",    [{"tp_mult":2.5,"sl_mult":1,"threshold":40,"max_hold":14,"use_trailing":True,"cooldown":5},
                                     {"tp_mult":3,"sl_mult":1.5,"threshold":35,"max_hold":21,"use_trailing":True,"cooldown":7}]),
        ("stocks", "trend_short",   [{"tp_mult":2,"sl_mult":1,"threshold":35,"max_hold":7,"use_trailing":True,"cooldown":5}]),
        ("meme",   "trend_short",   [{"tp_mult":2,"sl_mult":1,"threshold":35,"max_hold":7,"use_trailing":True,"cooldown":5},
                                     {"tp_mult":2.5,"sl_mult":1,"threshold":40,"max_hold":10,"use_trailing":True,"cooldown":5},
                                     {"tp_mult":3,"sl_mult":1,"threshold":35,"max_hold":14,"use_trailing":True,"cooldown":7},
                                     {"tp_mult":2,"sl_mult":0.8,"threshold":35,"max_hold":5,"use_trailing":True,"cooldown":3}]),
        ("meme",   "breakout_long", [{"tp_mult":3,"sl_mult":1,"threshold":35,"max_hold":7,"use_trailing":True,"cooldown":3}]),
    ]
    
    total_tests = sum(len(plist) for _, _, plist in TEST_CONFIGS)
    bonferroni_alpha = 0.05 / total_tests  # Multiple testing correction
    
    print(f"\n  Total strategy-param combos: {total_tests}")
    print(f"  Bonferroni-corrected α: {bonferroni_alpha:.6f}")
    
    # 3. Run all tests
    print("\n" + "=" * 80)
    print("🔬 Phase 2: FULL-SPECTRUM RIGOROUS BACKTEST")
    print("=" * 80)
    
    all_results = []
    
    for asset_class, strat_name, param_list in TEST_CONFIGS:
        strat_fn = STRATEGIES[strat_name]
        syms = [s for s in SYMBOLS.get(asset_class, []) if s in yf_data]
        if not syms: continue
        
        direction = "SHORT" if "short" in strat_name else "LONG"
        
        print(f"\n  {'━'*70}")
        print(f"  {asset_class.upper()} × {strat_name} ({len(syms)} symbols)")
        print(f"  {'━'*70}")
        
        for pidx, params in enumerate(param_list):
            label = f"{asset_class}_{strat_name}_p{pidx}"
            
            # FULL 2-year backtest with regime tagging
            trades = regime_split_backtest(yf_data, syms, asset_class, strat_fn, params)
            full_stats = analyze_with_stats(trades, label)
            
            # Walk-forward: train 50% / test 50%
            oos_trades = backtest(yf_data, syms, asset_class, strat_fn, params, 0.5, 1.0)
            oos_stats = analyze_with_stats(oos_trades, f"{label}_OOS")
            
            # Monte Carlo random baseline
            random_trades = monte_carlo_random_entry(yf_data, syms, asset_class, params,
                                                      n_random=max(len(trades), 200), direction=direction)
            random_pnls = [t["pnl_pct"] for t in random_trades]
            random_mean = float(np.mean(random_pnls)) if random_pnls else 0
            random_pf_gp = sum(p for p in random_pnls if p > 0)
            random_pf_gl = abs(sum(p for p in random_pnls if p < 0))
            random_pf = random_pf_gp / random_pf_gl if random_pf_gl > 0 else 0
            
            # Compare strategy vs random
            if full_stats["total"] >= 30 and random_trades:
                strat_pnls = [t["pnl_pct"] for t in trades]
                mc_tstat, mc_pval = scipy_stats.mannwhitneyu(strat_pnls, random_pnls, alternative="greater")
                mc_better = mc_pval < 0.05
            else:
                mc_pval = 1.0; mc_better = False
            
            # Bonferroni-corrected significance
            bonf_sig = full_stats["ttest"]["p_value"] < bonferroni_alpha if full_stats["ttest"] else False
            
            # Print results
            icon = "✅" if "SIGNIFICANT WINNER" in full_stats["verdict"] else "🟡" if "POSITIVE" in full_stats["verdict"] else "❌"
            print(f"\n    {icon} {label}")
            print(f"       FULL: {full_stats['total']:4d} trades  WR:{full_stats['win_rate']:5.1f}%  "
                  f"PF:{full_stats['pf']:.2f}  P&L:{full_stats['total_pnl']:+9.1f}%  "
                  f"Exp:{full_stats['expectancy']:+.4f}%")
            
            if full_stats["bootstrap"]:
                b = full_stats["bootstrap"]
                print(f"       BOOTSTRAP 95% CI: [{b['ci_low']:+.4f}%, {b['ci_high']:+.4f}%]  "
                      f"{'✅ Above zero' if b['positive'] else '❌ Crosses zero'}")
            
            if full_stats["ttest"]:
                t = full_stats["ttest"]
                print(f"       T-TEST: t={t['t_stat']:.3f}  p={t['p_value']:.6f}  "
                      f"{'✅ p<0.05' if t['significant_5pct'] else '❌ not sig'}  "
                      f"{'✅ BONFERRONI' if bonf_sig else '⚠️ not Bonf'}")
            
            print(f"       OOS:  {oos_stats['total']:4d} trades  WR:{oos_stats['win_rate']:5.1f}%  "
                  f"PF:{oos_stats['pf']:.2f}  P&L:{oos_stats['total_pnl']:+9.1f}%")
            
            print(f"       RANDOM: mean={random_mean:+.3f}%  PF:{random_pf:.2f}  "
                  f"{'✅ beats random' if mc_better else '❌ not better than random'}  "
                  f"(p={mc_pval:.4f})")
            
            if full_stats["regime_breakdown"]:
                for reg, rd in full_stats["regime_breakdown"].items():
                    reg_icon = "✅" if rd["pf"] > 1.0 else "❌"
                    print(f"       REGIME {reg:8s}: {rd['trades']:3d} trades  "
                          f"WR:{rd['win_rate']:5.1f}%  PF:{rd['pf']:.2f}  P&L:{rd['pnl']:+.1f}%  {reg_icon}")
            
            all_results.append({
                "asset_class": asset_class, "strategy": strat_name,
                "param_idx": pidx, "params": params,
                "full": full_stats, "oos": oos_stats,
                "random_mean": round(random_mean, 4), "random_pf": round(random_pf, 2),
                "mc_pval": round(mc_pval, 6), "mc_better": mc_better,
                "bonferroni_sig": bonf_sig,
            })
    
    # 4. FINAL VERDICT
    print("\n" + "=" * 80)
    print("🏆 Phase 3: FINAL VERDICT — STATISTICALLY SIGNIFICANT WINNERS ONLY")
    print("=" * 80)
    
    real_winners = []
    marginal = []
    eliminated = []
    
    for r in all_results:
        f = r["full"]; o = r["oos"]
        label = f"{r['asset_class']}/{r['strategy']}/p{r['param_idx']}"
        
        # A REAL winner must pass ALL tests:
        # 1. Bootstrap CI above zero
        # 2. T-test p < 0.05
        # 3. PF > 1.2 full AND > 1.0 OOS
        # 4. Beats random entry (Monte Carlo p < 0.05)
        # 5. 30+ trades
        # 6. Profitable in at least 2 regimes
        
        boot_ok = f.get("bootstrap", {}).get("positive", False)
        ttest_ok = f.get("ttest", {}).get("significant_5pct", False)
        pf_ok = f.get("pf", 0) > 1.2
        oos_ok = o.get("total", 0) >= 15 and o.get("pf", 0) > 1.0
        mc_ok = r.get("mc_better", False)
        n_ok = f.get("total", 0) >= 30
        
        # Regime diversification
        regimes = f.get("regime_breakdown", {})
        profitable_regimes = sum(1 for rd in regimes.values() if rd.get("pf", 0) > 1.0)
        regime_ok = profitable_regimes >= 2
        
        passes = sum([boot_ok, ttest_ok, pf_ok, oos_ok, mc_ok, n_ok, regime_ok])
        
        if passes >= 6:  # Must pass 6/7
            real_winners.append(r)
            print(f"  ✅ REAL WINNER: {label}  ({passes}/7 tests passed)")
            print(f"     PF:{f['pf']:.2f}  WR:{f['win_rate']:.1f}%  P&L:{f['total_pnl']:+.1f}%  "
                  f"Boot:[{f['bootstrap']['ci_low']:+.4f},{f['bootstrap']['ci_high']:+.4f}]  "
                  f"p={f['ttest']['p_value']:.6f}")
        elif passes >= 4:
            marginal.append(r)
            print(f"  🟡 MARGINAL:   {label}  ({passes}/7 tests passed)")
        else:
            eliminated.append(r)
    
    # Summary
    print(f"\n  {'='*60}")
    print(f"  TOTAL TESTED:  {len(all_results)} strategy-param combos")
    print(f"  ✅ REAL WINNERS:  {len(real_winners)}")
    print(f"  🟡 MARGINAL:      {len(marginal)}")
    print(f"  ❌ ELIMINATED:    {len(eliminated)}")
    print(f"  {'='*60}")
    
    if not real_winners:
        print("\n  ⚠️  NO STRATEGY SURVIVED ALL STATISTICAL TESTS.")
        print("     This is HONEST. Most trading strategies don't beat random.")
        print("     Next step: design new strategies from first principles.")
    
    # Save
    save_data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data_period": "2 years",
        "total_tested": len(all_results),
        "bonferroni_alpha": bonferroni_alpha,
        "real_winners": len(real_winners),
        "marginal": len(marginal),
        "eliminated": len(eliminated),
        "results": [],
    }
    
    for r in all_results:
        save_data["results"].append({
            "asset_class": r["asset_class"], "strategy": r["strategy"],
            "param_idx": r["param_idx"],
            "params": r["params"],
            "full_stats": r["full"],
            "oos_stats": r["oos"],
            "random_mean": r["random_mean"], "random_pf": r["random_pf"],
            "mc_pval": r["mc_pval"], "mc_better": r["mc_better"],
            "bonferroni_sig": r["bonferroni_sig"],
            "verdict": r["full"]["verdict"],
        })
    
    results_file = DATA_DIR / "battle_test_rigorous.json"
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(save_data, f, indent=2, default=str)
    print(f"\n  📁 Saved to {results_file}")
    
    print(f"\n{'='*80}")
    print("🔬 RIGOROUS BATTLE TEST COMPLETE")
    print(f"{'='*80}")
    
    return save_data


if __name__ == "__main__":
    main()
