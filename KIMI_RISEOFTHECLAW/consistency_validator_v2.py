#!/usr/bin/env python3
"""
ANTIGRAVITY CONSISTENCY VALIDATOR v2
=====================================
5-CHECK VALIDATION SYSTEM (inspired by institutional standards + Kimi's approach)

CHECK 1: Sample Size ≥ 10 trades
CHECK 2: Win Rate ≥ 40%
CHECK 3: One-Hit Wonder Score ≤ 0.30 (outlier detection)
CHECK 4: P-Value ≤ 0.05 (t-test statistical significance)
CHECK 5: Sharpe Ratio ≥ 0.5 (risk-adjusted returns)

PLUS: Rolling window consistency (our original innovation)
  - Tests across 12 rolling 6-month windows
  - Reports % of windows profitable

Evidence Strength:
  5/5 = VERY STRONG ✅ PROVEN WINNER
  4/5 = STRONG (likely winner)
  3/5 = MODERATE (needs more data)
  <3  = WEAK ❌ NOT PROVEN
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

# ═══════════════════════════════════════════════════════════════════════════
# INDICATORS
# ═══════════════════════════════════════════════════════════════════════════
def rsi(close, period=14):
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0).rolling(window=period, min_periods=period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window=period, min_periods=period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def ema(s, period):
    return s.ewm(span=period, adjust=False).mean()

def sma(s, period):
    return s.rolling(period).mean()

def bb(close, period=20, num_std=2):
    mid = close.rolling(period).mean()
    std = close.rolling(period).std()
    return mid, mid + num_std * std, mid - num_std * std

# ═══════════════════════════════════════════════════════════════════════════
# STRATEGIES
# ═══════════════════════════════════════════════════════════════════════════

def trend_ema_crossover(df, direction="long"):
    if len(df) < 30: return []
    c = df["Close"].copy()
    e9 = ema(c, 9); e21 = ema(c, 21)
    trades = []
    in_trade = False; entry_price = 0; entry_idx = 0
    for i in range(22, len(df)):
        if np.isnan(e9.iloc[i]) or np.isnan(e21.iloc[i]): continue
        price = float(c.iloc[i])
        v9 = float(e9.iloc[i]); v21 = float(e21.iloc[i])
        v9p = float(e9.iloc[i-1]); v21p = float(e21.iloc[i-1])
        if not in_trade:
            if direction == "long" and v9 > v21 and v9p <= v21p:
                in_trade = True; entry_price = price; entry_idx = i
            elif direction == "short" and v9 < v21 and v9p >= v21p:
                in_trade = True; entry_price = price; entry_idx = i
        else:
            held = i - entry_idx
            pnl = ((price - entry_price) / entry_price * 100) if direction == "long" else ((entry_price - price) / entry_price * 100)
            if pnl >= 2.0 or pnl <= -1.0 or held >= 20:
                trades.append(pnl); in_trade = False
    return trades

def momentum_roc(df, direction="long"):
    if len(df) < 20: return []
    c = df["Close"].copy()
    trades = []
    in_trade = False; entry_price = 0; entry_idx = 0
    for i in range(14, len(df)):
        price = float(c.iloc[i])
        roc3 = (price - float(c.iloc[i-3])) / float(c.iloc[i-3]) * 100
        roc6 = (price - float(c.iloc[i-6])) / float(c.iloc[i-6]) * 100 if i >= 6 else 0
        if not in_trade:
            if direction == "long" and roc3 > 0.5 and roc3 > roc6:
                in_trade = True; entry_price = price; entry_idx = i
            elif direction == "short" and roc3 < -0.5 and roc3 < roc6:
                in_trade = True; entry_price = price; entry_idx = i
        else:
            held = i - entry_idx
            pnl = ((price - entry_price) / entry_price * 100) if direction == "long" else ((entry_price - price) / entry_price * 100)
            if pnl >= 2.0 or pnl <= -1.0 or held >= 15:
                trades.append(pnl); in_trade = False
    return trades

def bb_mean_reversion(df, direction="long"):
    if len(df) < 25: return []
    c = df["Close"].copy()
    mid, upper, lower = bb(c, 20, 2)
    trades = []
    in_trade = False; entry_price = 0; entry_idx = 0
    for i in range(21, len(df)):
        if any(np.isnan(x.iloc[i]) for x in [mid, upper, lower]): continue
        price = float(c.iloc[i])
        u, l = float(upper.iloc[i]), float(lower.iloc[i])
        bb_pos = (price - l) / (u - l) if (u - l) > 0 else 0.5
        if not in_trade:
            if direction == "long" and bb_pos < 0.1:
                in_trade = True; entry_price = price; entry_idx = i
            elif direction == "short" and bb_pos > 0.9:
                in_trade = True; entry_price = price; entry_idx = i
        else:
            held = i - entry_idx
            pnl = ((price - entry_price) / entry_price * 100) if direction == "long" else ((entry_price - price) / entry_price * 100)
            if pnl >= 1.5 or pnl <= -1.0 or held >= 15 or (direction == "long" and bb_pos > 0.5) or (direction == "short" and bb_pos < 0.5):
                trades.append(pnl); in_trade = False
    return trades

# ═══════════════════════════════════════════════════════════════════════════
# 5-CHECK VALIDATION ENGINE
# ═══════════════════════════════════════════════════════════════════════════

def one_hit_wonder_score(pnls):
    """Detect if results are driven by a single outlier."""
    if len(pnls) < 3: return 1.0
    arr = np.array(pnls)
    
    # Check 1: Single outlier > 3x average of others
    sorted_pnls = sorted(arr, reverse=True)
    if len(sorted_pnls) >= 2:
        top = sorted_pnls[0]
        others_avg = np.mean(sorted_pnls[1:]) if len(sorted_pnls) > 1 else 0
        if others_avg > 0 and top > 3 * others_avg:
            return 1.0
    
    # Check 2: Single run accounts for >50% of total gains
    total_gains = sum(p for p in arr if p > 0)
    if total_gains > 0:
        max_gain = max(arr)
        if max_gain / total_gains > 0.5:
            return min(1.0, max_gain / total_gains)
    
    # Check 3: Coefficient of variation
    if np.mean(arr) != 0:
        cv = np.std(arr) / abs(np.mean(arr))
        if cv > 2.0:
            return min(1.0, cv / 3.0)
    
    # Low score = good (not a one-hit wonder)
    return round(max(0, 1.0 - len([p for p in arr if p > 0]) / len(arr)), 2)


def validate_5checks(pnls, name):
    """Run the 5-check validation system."""
    checks = {}
    arr = np.array(pnls) if pnls else np.array([0])
    n = len(pnls)
    
    # CHECK 1: Sample Size ≥ 10
    checks["sample_size"] = {"value": n, "threshold": 10, "pass": n >= 10}
    
    # CHECK 2: Win Rate ≥ 40%
    wins = sum(1 for p in pnls if p > 0) if pnls else 0
    wr = wins / n * 100 if n > 0 else 0
    checks["win_rate"] = {"value": round(wr, 1), "threshold": 40, "pass": wr >= 40}
    
    # CHECK 3: One-Hit Wonder Score ≤ 0.30
    ohs = one_hit_wonder_score(pnls) if pnls else 1.0
    checks["one_hit_score"] = {"value": round(ohs, 2), "threshold": 0.30, "pass": ohs <= 0.30}
    
    # CHECK 4: P-Value ≤ 0.05 (one-sample t-test: is mean > 0?)
    if n >= 3 and np.std(arr) > 0:
        t_stat, p_val = scipy_stats.ttest_1samp(arr, 0)
        # One-sided: we want mean > 0
        p_one_sided = p_val / 2 if t_stat > 0 else 1 - p_val / 2
    else:
        p_one_sided = 1.0
    checks["p_value"] = {"value": round(p_one_sided, 4), "threshold": 0.05, "pass": p_one_sided <= 0.05}
    
    # CHECK 5: Sharpe Ratio ≥ 0.5
    if n >= 2 and np.std(arr) > 0:
        sharpe = np.mean(arr) / np.std(arr) * np.sqrt(252 / max(1, n))  # Annualized
    else:
        sharpe = 0
    checks["sharpe_ratio"] = {"value": round(sharpe, 2), "threshold": 0.5, "pass": sharpe >= 0.5}
    
    passed = sum(1 for c in checks.values() if c["pass"])
    
    if passed == 5: strength = "VERY STRONG"; verdict = "✅ PROVEN WINNER"
    elif passed == 4: strength = "STRONG"; verdict = "✅ Likely Winner"
    elif passed == 3: strength = "MODERATE"; verdict = "⚠️ Needs More Data"
    else: strength = "WEAK"; verdict = "❌ NOT PROVEN"
    
    return {
        "name": name,
        "trades": n,
        "wins": wins,
        "avg_pnl": round(float(np.mean(arr)), 3) if n > 0 else 0,
        "total_pnl": round(float(np.sum(arr)), 2) if n > 0 else 0,
        "checks": checks,
        "checks_passed": passed,
        "strength": strength,
        "verdict": verdict,
    }


# ═══════════════════════════════════════════════════════════════════════════
# ROLLING WINDOW ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════

def rolling_window_analysis(df_full, strategy_fn, direction, window_size=126, step=63):
    """Test strategy across rolling windows."""
    total = len(df_full)
    window_results = []
    start = 0
    while start + window_size <= total:
        df_w = df_full.iloc[start:start + window_size].copy().reset_index(drop=True)
        trades = strategy_fn(df_w, direction)
        if trades:
            w_pnl = sum(trades)
            w_wr = sum(1 for t in trades if t > 0) / len(trades) * 100
        else:
            w_pnl = 0; w_wr = 0
        window_results.append({"pnl": round(w_pnl, 2), "trades": len(trades), "wr": round(w_wr, 1)})
        start += step
    
    profitable_windows = sum(1 for w in window_results if w["pnl"] > 0)
    total_windows = len(window_results)
    
    return {
        "total_windows": total_windows,
        "profitable_windows": profitable_windows,
        "pct_profitable": round(profitable_windows / total_windows * 100, 1) if total_windows > 0 else 0,
        "windows": window_results,
    }


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

STRATEGIES = {
    "trend_ema_cross": trend_ema_crossover,
    "momentum_roc": momentum_roc,
    "bb_mean_reversion": bb_mean_reversion,
}

SYMBOLS = {
    "crypto": ["BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD", "DOGE-USD"],
    "forex": ["EURUSD=X", "GBPUSD=X", "AUDUSD=X"],
}

def main():
    print("=" * 80)
    print("ANTIGRAVITY CONSISTENCY VALIDATOR v2")
    print("5-Check System: Sample Size | Win Rate | One-Hit Score | P-Value | Sharpe")
    print("=" * 80)
    
    results = {"generated_at": datetime.now(timezone.utc).isoformat(), "version": "v2", "validations": []}
    
    all_syms = []
    for syms in SYMBOLS.values():
        all_syms.extend(syms)
    
    print(f"\n📥 Downloading 2 years of daily data for {len(all_syms)} symbols...")
    batch = yf.download(all_syms, period="2y", interval="1d",
                        group_by="ticker", auto_adjust=True,
                        progress=True, threads=True)
    
    # Test each strategy × direction × symbol
    all_validations = []
    
    for strat_name, strat_fn in STRATEGIES.items():
        for direction in ["long", "short"]:
            for asset_class, syms in SYMBOLS.items():
                for sym in syms:
                    try:
                        df = batch[sym].dropna() if len(all_syms) > 1 else batch.dropna()
                        if len(df) < 100: continue
                    except: continue
                    
                    key = f"{strat_name}_{direction}_{sym}"
                    
                    # Full backtest
                    all_trades = strat_fn(df, direction)
                    
                    # 5-check validation
                    validation = validate_5checks(all_trades, key)
                    
                    # Rolling window analysis
                    rolling = rolling_window_analysis(df, strat_fn, direction)
                    validation["rolling_windows"] = rolling
                    validation["asset_class"] = asset_class
                    validation["symbol"] = sym
                    validation["strategy"] = strat_name
                    validation["direction"] = direction
                    
                    all_validations.append(validation)
    
    # Sort by checks passed (then by total P&L)
    all_validations.sort(key=lambda x: (x["checks_passed"], x["total_pnl"]), reverse=True)
    
    results["validations"] = all_validations
    
    # Print results
    print(f"\n{'='*90}")
    print(f"{'Strategy + Symbol':<40s} {'Trades':>6s} {'WR':>6s} {'P&L':>8s} {'Sharpe':>7s} {'P-val':>7s} {'OHS':>5s} {'Chk':>4s} {'Verdict':<20s}")
    print("-" * 90)
    
    proven = []
    strong = []
    not_proven = []
    
    for v in all_validations:
        tag = ""
        if v["checks_passed"] >= 4:
            if v["checks_passed"] == 5: proven.append(v)
            else: strong.append(v)
        else:
            not_proven.append(v)
        
        p_val_str = f"{v['checks']['p_value']['value']:.4f}" if v['checks']['p_value']['value'] < 1 else "1.000"
        sharpe_str = f"{v['checks']['sharpe_ratio']['value']:+.2f}"
        ohs_str = f"{v['checks']['one_hit_score']['value']:.2f}"
        
        print(f"{v['name']:<40s} {v['trades']:>6d} {v['checks']['win_rate']['value']:>5.1f}% "
              f"{v['total_pnl']:>+7.1f}% {sharpe_str:>7s} {p_val_str:>7s} {ohs_str:>5s} "
              f"{v['checks_passed']:>3d}/5 {v['verdict']}")
    
    # Summary
    print(f"\n{'='*90}")
    print(f"SUMMARY: {len(all_validations)} strategy/symbol pairs tested")
    print(f"  ✅ PROVEN WINNERS (5/5): {len(proven)}")
    print(f"  ✅ STRONG (4/5): {len(strong)}")
    print(f"  ❌ NOT PROVEN (<4/5): {len(not_proven)}")
    
    if proven:
        print(f"\n{'='*90}")
        print("✅ PROVEN WINNERS (passed ALL 5 checks — NOT one-hit wonders):")
        for v in proven:
            rw = v["rolling_windows"]
            print(f"\n  📊 {v['name']}")
            print(f"     Trades: {v['trades']} | WR: {v['checks']['win_rate']['value']}% | Avg P&L: {v['avg_pnl']:+.3f}% | Total: {v['total_pnl']:+.1f}%")
            print(f"     Sharpe: {v['checks']['sharpe_ratio']['value']:+.2f} | P-value: {v['checks']['p_value']['value']:.4f} | One-Hit: {v['checks']['one_hit_score']['value']:.2f}")
            print(f"     Rolling: {rw['profitable_windows']}/{rw['total_windows']} windows profitable ({rw['pct_profitable']}%)")
    
    if strong:
        print(f"\n{'='*90}")
        print("✅ STRONG CANDIDATES (4/5 checks):")
        for v in strong:
            rw = v["rolling_windows"]
            failed = [k for k, c in v["checks"].items() if not c["pass"]]
            print(f"  📊 {v['name']} — Failed: {', '.join(failed)}")
            print(f"     Trades: {v['trades']} | WR: {v['checks']['win_rate']['value']}% | Total: {v['total_pnl']:+.1f}% | Sharpe: {v['checks']['sharpe_ratio']['value']:+.2f}")
    
    # Save
    outfile = DATA_DIR / "consistency_v2_results.json"
    with open(outfile, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n📁 Full results: {outfile}")

if __name__ == "__main__":
    main()
