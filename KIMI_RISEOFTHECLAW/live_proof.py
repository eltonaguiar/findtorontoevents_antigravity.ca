#!/usr/bin/env python3
"""
LIVE PROOF ENGINE
=================
No more backtests. Real data. Right now.

This engine:
  1. Pulls LIVE market data (current minute)
  2. Shows what every signal says RIGHT NOW
  3. Runs TRUE out-of-sample validation on last 90 days
  4. Shows individual trades with dates, entry, exit, P&L
  5. Compares predictions vs actual outcomes

If it doesn't work on live data, it's worthless.
"""

import json
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timezone, timedelta
from pathlib import Path
from scipy import stats as scipy_stats
import urllib.request
import time

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

NOW = datetime.now(timezone.utc)
NOW_EST = datetime.now()

def fetch_json(url, retries=3):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            if attempt == retries - 1:
                print(f"  ❌ Failed: {e}")
                return None
            time.sleep(1)


def print_header(title):
    print(f"\n{'='*100}")
    print(f"  {title}")
    print(f"{'='*100}")


def print_section(title):
    print(f"\n{'─'*80}")
    print(f"  {title}")
    print(f"{'─'*80}")


# ═══════════════════════════════════════════════════════════════════════════
# PROOF 1: LIVE FEAR & GREED — WHAT DOES IT SAY RIGHT NOW?
# ═══════════════════════════════════════════════════════════════════════════

def proof_fear_greed():
    print_header("PROOF 1: FEAR & GREED INDEX — LIVE RIGHT NOW")
    
    # Get current value
    data = fetch_json("https://api.alternative.me/fng/?limit=90&format=json")
    if not data or "data" not in data:
        print("  ❌ Could not fetch Fear & Greed data")
        return None
    
    fg_data = data["data"]
    current = fg_data[0]
    current_value = int(current["value"])
    current_class = current["value_classification"]
    
    print(f"\n  📡 LIVE Fear & Greed Index: {current_value} ({current_class})")
    print(f"  📅 Timestamp: {datetime.fromtimestamp(int(current['timestamp']))}")
    
    # What does our strategy say?
    if current_value <= 20:
        signal = "🟢 STRONG BUY — Extreme Fear (our strategy: buy and hold 14-30 days)"
        action = "BUY"
    elif current_value <= 35:
        signal = "🟡 MILD BUY — Fear zone (historically favorable for entry)"
        action = "MILD_BUY"
    elif current_value >= 85:
        signal = "🔴 STRONG SELL — Extreme Greed (exit all positions)"
        action = "SELL"
    elif current_value >= 70:
        signal = "🟠 CAUTION — Greed zone (reduce exposure)"
        action = "CAUTION"
    else:
        signal = "⚪ NEUTRAL — No extreme (wait for fear <20 or greed >85)"
        action = "WAIT"
    
    print(f"  🎯 SIGNAL: {signal}")
    
    # Now prove with RECENT data: last 90 days of actual trades
    print_section("OUT-OF-SAMPLE PROOF: Last 90 days of Fear & Greed trades")
    
    fg_data.reverse()  # Oldest first
    
    # Get BTC price for same period
    btc = yf.download("BTC-USD", period="6mo", interval="1d", auto_adjust=True, progress=False)
    if btc.empty:
        print("  ❌ No BTC data")
        return None
    
    btc_close = btc["Close"]
    if isinstance(btc_close, pd.DataFrame):
        btc_close = btc_close.iloc[:, 0]
    
    # Create aligned data
    fg_df = pd.DataFrame(fg_data)
    fg_df["date"] = pd.to_datetime(fg_df["timestamp"].astype(int), unit="s").dt.normalize()
    fg_df["value"] = fg_df["value"].astype(int)
    fg_df = fg_df.set_index("date").sort_index()
    
    btc_close.index = btc_close.index.normalize()
    
    # Only use last 90 days
    cutoff = pd.Timestamp.now() - pd.Timedelta(days=90)
    fg_recent = fg_df[fg_df.index >= cutoff]
    
    print(f"\n  Data range: {fg_recent.index[0].date()} → {fg_recent.index[-1].date()} ({len(fg_recent)} days)")
    
    # Show recent extremes and what happened
    trades_14d = []
    trade_details = []
    
    for i in range(len(fg_recent)):
        fg_val = int(fg_recent["value"].iloc[i])
        date = fg_recent.index[i]
        
        if fg_val <= 25:  # Fear zone
            if date in btc_close.index:
                entry_price = float(btc_close.loc[date])
                
                # Check what happened 14 days later
                exit_date = date + pd.Timedelta(days=14)
                # Find closest trading day
                future_prices = btc_close[btc_close.index > date]
                if len(future_prices) >= 10:
                    exit_idx = min(13, len(future_prices) - 1)
                    exit_price = float(future_prices.iloc[exit_idx])
                    actual_exit_date = future_prices.index[exit_idx]
                    pnl = (exit_price - entry_price) / entry_price * 100
                    trades_14d.append(pnl)
                    
                    outcome = "✅ WIN" if pnl > 0 else "❌ LOSS"
                    trade_details.append({
                        "date": str(date.date()),
                        "fg": fg_val,
                        "entry": round(entry_price, 2),
                        "exit": round(exit_price, 2),
                        "exit_date": str(actual_exit_date.date()),
                        "pnl_pct": round(pnl, 2),
                        "outcome": outcome,
                    })
    
    if trade_details:
        print(f"\n  {'DATE':<12} {'F&G':>4} {'ENTRY':>10} {'EXIT':>10} {'EXIT DATE':<12} {'P&L':>8}  RESULT")
        print(f"  {'-'*75}")
        for t in trade_details:
            sign = "+" if t["pnl_pct"] >= 0 else ""
            print(f"  {t['date']:<12} {t['fg']:>4} ${t['entry']:>9,.2f} ${t['exit']:>9,.2f} {t['exit_date']:<12} {sign}{t['pnl_pct']:>6.2f}%  {t['outcome']}")
        
        # Summary
        if trades_14d:
            arr = np.array(trades_14d)
            wins = sum(1 for t in trades_14d if t > 0)
            print(f"\n  📊 LAST 90 DAYS SUMMARY:")
            print(f"     Trades: {len(trades_14d)}")
            print(f"     Wins: {wins}/{len(trades_14d)} ({wins/len(trades_14d)*100:.1f}%)")
            print(f"     Total P&L: {sum(trades_14d):+.2f}%")
            print(f"     Avg P&L: {np.mean(arr):+.2f}%")
            print(f"     Best: {max(trades_14d):+.2f}% | Worst: {min(trades_14d):+.2f}%")
            
            if wins/len(trades_14d) >= 0.5 and sum(trades_14d) > 0:
                print(f"     ✅ CONFIRMED: Fear & Greed strategy WORKS on live recent data")
            else:
                print(f"     ⚠️ Mixed results on recent data — needs more validation")
    else:
        print(f"\n  ℹ️ No extreme fear signals (<25) in last 90 days — strategy is WAITING")
        print(f"  Current F&G: {current_value} — signal only fires in extreme fear")
    
    return {
        "current_value": current_value,
        "current_class": current_class,
        "signal": action,
        "recent_trades": trade_details,
        "recent_stats": {
            "trades": len(trades_14d),
            "win_rate": round(sum(1 for t in trades_14d if t > 0) / len(trades_14d) * 100, 1) if trades_14d else 0,
            "total_pnl": round(sum(trades_14d), 2) if trades_14d else 0,
        }
    }


# ═══════════════════════════════════════════════════════════════════════════
# PROOF 2: CONNORS RSI(2) — LIVE SIGNAL + RECENT VERIFICATION
# ═══════════════════════════════════════════════════════════════════════════

def proof_connors_rsi2():
    print_header("PROOF 2: CONNORS RSI(2) — LIVE SIGNAL + RECENT TRADE-BY-TRADE")
    
    symbols = {
        "SPY": "S&P 500 ETF",
        "QQQ": "Nasdaq 100 ETF", 
        "BTC-USD": "Bitcoin",
        "ETH-USD": "Ethereum",
        "SOL-USD": "Solana",
    }
    
    all_results = {}
    
    for sym, name in symbols.items():
        print_section(f"{sym} ({name})")
        
        df = yf.download(sym, period="1y", interval="1d", auto_adjust=True, progress=False)
        if df.empty or len(df) < 30:
            print(f"  ❌ Insufficient data")
            continue
        
        close = df["Close"]
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
        
        # Calculate RSI(2)
        delta = close.diff()
        gain = delta.where(delta > 0, 0.0).rolling(2, min_periods=2).mean()
        loss = (-delta.where(delta < 0, 0.0)).rolling(2, min_periods=2).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        
        # Current signal
        current_rsi = float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50
        current_price = float(close.iloc[-1])
        
        if current_rsi < 10:
            signal = "🟢 STRONG BUY (RSI2 < 10: extreme oversold)"
            signal_code = "BUY"
        elif current_rsi < 20:
            signal = "🟡 BUY (RSI2 < 20: oversold)"
            signal_code = "BUY"
        elif current_rsi > 90:
            signal = "🔴 SELL (RSI2 > 90: overbought, exit longs)"
            signal_code = "SELL"
        elif current_rsi > 80:
            signal = "🟠 CAUTION (RSI2 > 80: getting hot)"
            signal_code = "CAUTION"
        else:
            signal = "⚪ NEUTRAL (no extreme)"
            signal_code = "WAIT"
        
        print(f"  📡 LIVE: {sym} = ${current_price:,.2f} | RSI(2) = {current_rsi:.1f}")
        print(f"  🎯 SIGNAL: {signal}")
        
        # Out-of-sample: last 90 days trades
        cutoff_idx = len(close) - 90
        if cutoff_idx < 10:
            cutoff_idx = 10
        
        trades = []
        trade_details = []
        
        for i in range(cutoff_idx, len(close) - 5):
            rsi_val = float(rsi.iloc[i]) if not pd.isna(rsi.iloc[i]) else 50
            
            if rsi_val < 10:  # Buy signal
                entry = float(close.iloc[i])
                entry_date = close.index[i]
                
                # Exit when RSI > 65 (mean reversion target) or after 5 days max
                exit_price = None
                exit_date = None
                for j in range(i+1, min(i+6, len(close))):
                    rsi_j = float(rsi.iloc[j]) if not pd.isna(rsi.iloc[j]) else 50
                    if rsi_j > 65 or j == min(i+5, len(close)-1):
                        exit_price = float(close.iloc[j])
                        exit_date = close.index[j]
                        break
                
                if exit_price:
                    pnl = (exit_price - entry) / entry * 100
                    trades.append(pnl)
                    outcome = "✅ WIN" if pnl > 0 else "❌ LOSS"
                    
                    entry_d = entry_date.date() if hasattr(entry_date, 'date') else entry_date
                    exit_d = exit_date.date() if hasattr(exit_date, 'date') else exit_date
                    
                    trade_details.append({
                        "entry_date": str(entry_d),
                        "exit_date": str(exit_d),
                        "rsi": round(rsi_val, 1),
                        "entry": round(entry, 2),
                        "exit": round(exit_price, 2),
                        "pnl_pct": round(pnl, 2),
                        "outcome": outcome,
                    })
        
        if trade_details:
            print(f"\n  LAST 90 DAYS — RSI(2) < 10 TRADES ON {sym}:")
            print(f"  {'ENTRY DATE':<12} {'RSI':>5} {'ENTRY':>10} {'EXIT DATE':<12} {'EXIT':>10} {'P&L':>8}  RESULT")
            print(f"  {'-'*70}")
            for t in trade_details:
                sign = "+" if t["pnl_pct"] >= 0 else ""
                print(f"  {t['entry_date']:<12} {t['rsi']:>5.1f} ${t['entry']:>9,.2f} {t['exit_date']:<12} ${t['exit']:>9,.2f} {sign}{t['pnl_pct']:>6.2f}%  {t['outcome']}")
            
            arr = np.array(trades)
            wins = sum(1 for t in trades if t > 0)
            print(f"\n  📊 {sym} LAST 90 DAYS:")
            print(f"     Trades: {len(trades)} | Wins: {wins}/{len(trades)} ({wins/len(trades)*100:.1f}%)")
            print(f"     Total P&L: {sum(trades):+.2f}% | Avg: {np.mean(arr):+.2f}%")
            
            status = "✅ CONFIRMED" if wins/len(trades) >= 0.55 and sum(trades) > 0 else "⚠️ MIXED"
            print(f"     {status}")
        else:
            print(f"\n  ℹ️ No RSI(2) < 10 signals in last 90 days on {sym} — strategy is WAITING")
        
        all_results[sym] = {
            "current_price": current_price,
            "current_rsi2": round(current_rsi, 1),
            "signal": signal_code,
            "recent_trades": trade_details,
        }
    
    return all_results


# ═══════════════════════════════════════════════════════════════════════════
# PROOF 3: BTC DOMINANCE ROTATION — LIVE SIGNAL + RECENT VERIFICATION
# ═══════════════════════════════════════════════════════════════════════════

def proof_btc_dominance():
    print_header("PROOF 3: BTC DOMINANCE ROTATION — LIVE SIGNAL")
    
    syms = ["BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD"]
    batch = yf.download(syms, period="1y", interval="1d", auto_adjust=True,
                         group_by="ticker", progress=False, threads=True)
    
    dfs = {}
    for sym in syms:
        try:
            close = batch[sym]["Close"].dropna()
            if isinstance(close, pd.DataFrame):
                close = close.iloc[:, 0]
            if len(close) > 50:
                dfs[sym] = close
        except:
            pass
    
    if "BTC-USD" not in dfs or "ETH-USD" not in dfs:
        print("  ❌ Insufficient data")
        return None
    
    btc = dfs["BTC-USD"]
    
    # Build alt basket
    alt_basket = None
    for sym in ["ETH-USD", "SOL-USD", "XRP-USD"]:
        if sym in dfs:
            alt = dfs[sym]
            common = btc.index.intersection(alt.index)
            norm = alt.loc[common] / alt.loc[common].iloc[0]
            if alt_basket is None:
                alt_basket = norm
            else:
                alt_basket = alt_basket + norm
    
    btc_norm = btc.loc[alt_basket.index] / btc.loc[alt_basket.index].iloc[0]
    btc_strength = btc_norm / alt_basket
    strength_sma = btc_strength.rolling(20).mean()
    strength_change = strength_sma.pct_change(20)
    
    # Current signal
    current_sc = float(strength_change.iloc[-1]) if not pd.isna(strength_change.iloc[-1]) else 0
    
    if current_sc > 0.05:
        signal = "🟢 BTC SEASON — BTC dominance rising, hold BTC"
        action = "LONG_BTC"
    elif current_sc < -0.05:
        signal = "🟣 ALT SEASON — BTC dominance falling, rotate into alts"
        action = "LONG_ALTS"
    else:
        signal = "⚪ NEUTRAL — No clear trend"
        action = "WAIT"
    
    print(f"\n  📡 LIVE BTC Dominance Strength Change (20d): {current_sc*100:+.2f}%")
    print(f"  📡 Current BTC: ${float(btc.iloc[-1]):,.2f}")
    print(f"  📡 Current ETH: ${float(dfs['ETH-USD'].iloc[-1]):,.2f}")
    print(f"  🎯 SIGNAL: {signal}")
    
    # Out-of-sample: last 90 days
    print_section("LAST 90 DAYS — BTC DOMINANCE ROTATION TRADES")
    
    trades = []
    trade_details = []
    
    cutoff_idx = len(strength_change) - 90
    if cutoff_idx < 40:
        cutoff_idx = 40
    
    hold_period = 14
    i = cutoff_idx
    while i + hold_period < len(strength_change):
        sc = float(strength_change.iloc[i]) if not pd.isna(strength_change.iloc[i]) else 0
        date_i = strength_change.index[i]
        
        if abs(sc) > 0.03:  # Signal threshold
            if sc < -0.03:  # Alt season → long ETH
                sym_trade = "ETH-USD"
                direction = "ALT SEASON"
            else:  # BTC season → long BTC
                sym_trade = "BTC-USD"
                direction = "BTC SEASON"
            
            if sym_trade in dfs:
                asset = dfs[sym_trade]
                date_exit = strength_change.index[min(i + hold_period, len(strength_change) - 1)]
                
                if date_i in asset.index and date_exit in asset.index:
                    entry = float(asset.loc[date_i])
                    exit_p = float(asset.loc[date_exit])
                    pnl = (exit_p - entry) / entry * 100
                    trades.append(pnl)
                    outcome = "✅ WIN" if pnl > 0 else "❌ LOSS"
                    
                    trade_details.append({
                        "date": str(date_i.date()),
                        "exit_date": str(date_exit.date()),
                        "direction": direction,
                        "asset": sym_trade,
                        "entry": round(entry, 2),
                        "exit": round(exit_p, 2),
                        "pnl_pct": round(pnl, 2),
                        "outcome": outcome,
                    })
            
            i += hold_period  # Skip ahead
        else:
            i += 1
    
    if trade_details:
        print(f"\n  {'DATE':<12} {'REGIME':<12} {'ASSET':<10} {'ENTRY':>10} {'EXIT DATE':<12} {'EXIT':>10} {'P&L':>8}  RESULT")
        print(f"  {'-'*85}")
        for t in trade_details:
            sign = "+" if t["pnl_pct"] >= 0 else ""
            print(f"  {t['date']:<12} {t['direction']:<12} {t['asset']:<10} ${t['entry']:>9,.2f} {t['exit_date']:<12} ${t['exit']:>9,.2f} {sign}{t['pnl_pct']:>6.2f}%  {t['outcome']}")
        
        arr = np.array(trades)
        wins = sum(1 for t in trades if t > 0)
        print(f"\n  📊 LAST 90 DAYS:")
        print(f"     Trades: {len(trades)} | Wins: {wins}/{len(trades)} ({wins/len(trades)*100:.1f}%)")
        print(f"     Total P&L: {sum(trades):+.2f}% | Avg: {np.mean(arr):+.2f}%")
    
    return {
        "current_signal": action,
        "strength_change": round(current_sc * 100, 2),
        "recent_trades": trade_details,
    }


# ═══════════════════════════════════════════════════════════════════════════
# PROOF 4: LIVE BINANCE FUNDING RATES — RIGHT NOW
# ═══════════════════════════════════════════════════════════════════════════

def proof_funding_rates():
    print_header("PROOF 4: LIVE BINANCE FUNDING RATES — CURRENT VALUES")
    
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT", "XRPUSDT", 
               "AVAXUSDT", "ADAUSDT", "LINKUSDT", "DOTUSDT", "MATICUSDT"]
    
    print(f"\n  {'SYMBOL':<12} {'FUNDING RATE':>14} {'ANNUAL':>10}  SIGNAL")
    print(f"  {'-'*60}")
    
    results = []
    
    for sym in symbols:
        url = f"https://fapi.binance.com/fapi/v1/premiumIndex?symbol={sym}"
        data = fetch_json(url)
        
        if not data or "lastFundingRate" not in data:
            continue
        
        rate = float(data["lastFundingRate"]) * 100  # Convert to percentage
        annual = rate * 3 * 365  # 3 periods per day, 365 days
        mark_price = float(data.get("markPrice", 0))
        
        if rate < -0.01:
            signal = "🟢 BUY (shorts paying, oversold)"
        elif rate > 0.05:
            signal = "🔴 CAUTION (longs paying heavily)"
        elif rate > 0.02:
            signal = "🟡 Elevated (longs dominant)"
        else:
            signal = "⚪ Normal"
        
        print(f"  {sym:<12} {rate:>+12.4f}% {annual:>+8.1f}%  {signal}")
        
        results.append({
            "symbol": sym,
            "funding_rate": round(rate, 4),
            "annual_rate": round(annual, 1),
            "mark_price": mark_price,
            "signal": signal,
        })
    
    # Check if any extreme signals exist
    extreme_neg = [r for r in results if r["funding_rate"] < -0.01]
    extreme_pos = [r for r in results if r["funding_rate"] > 0.05]
    
    if extreme_neg:
        print(f"\n  🟢 ACTIONABLE: {len(extreme_neg)} symbols with negative funding (buy signal)")
        for r in extreme_neg:
            print(f"     → {r['symbol']} at {r['funding_rate']:+.4f}% — shorts are paying longs, sentiment oversold")
    elif extreme_pos:
        print(f"\n  🔴 CAUTION: {len(extreme_pos)} symbols with high positive funding")
    else:
        print(f"\n  ⚪ No extreme funding rates right now — strategy is WAITING for signal")
    
    return results


# ═══════════════════════════════════════════════════════════════════════════
# PROOF 5: END-OF-MONTH EFFECT — IS IT ACTIVE RIGHT NOW?
# ═══════════════════════════════════════════════════════════════════════════

def proof_end_of_month():
    print_header("PROOF 5: END-OF-MONTH EFFECT — IS IT ACTIVE?")
    
    today = NOW_EST
    day = today.day
    import calendar
    _, last_day = calendar.monthrange(today.year, today.month)
    days_left = last_day - day
    
    print(f"\n  📅 Today: {today.strftime('%B %d, %Y')}")
    print(f"  📅 Days left in month: {days_left}")
    
    if days_left <= 3:
        signal = "🟢 ACTIVE — Last 3 days of month (historically bullish for crypto)"
        active = True
    elif day <= 2:
        signal = "🟢 ACTIVE — First 2 days of month (continuation of EoM effect)"
        active = True
    else:
        signal = f"⚪ INACTIVE — EoM effect fires in last 3 days ({last_day-2}-{last_day} {today.strftime('%B')})"
        active = False
    
    print(f"  🎯 SIGNAL: {signal}")
    
    # Verify with recent data
    print_section("RECENT EOM TRADES — Last 6 Months")
    
    for sym in ["BTC-USD", "SOL-USD", "ETH-USD"]:
        df = yf.download(sym, period="6mo", interval="1d", auto_adjust=True, progress=False)
        if df.empty:
            continue
        
        close = df["Close"]
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
        
        trades = []
        trade_details = []
        
        for i in range(1, len(close) - 5):
            date = close.index[i]
            d = date.date() if hasattr(date, 'date') else date
            
            _, ml = calendar.monthrange(d.year, d.month)
            days_remaining = ml - d.day
            
            if days_remaining == 3:  # Enter 3 days before month end
                entry = float(close.iloc[i])
                # Exit on day 2 of next month (approximately 5 trading days later)
                exit_idx = min(i + 5, len(close) - 1)
                exit_p = float(close.iloc[exit_idx])
                pnl = (exit_p - entry) / entry * 100
                trades.append(pnl)
                
                trade_details.append({
                    "entry_date": str(d),
                    "exit_date": str(close.index[exit_idx].date() if hasattr(close.index[exit_idx], 'date') else close.index[exit_idx]),
                    "entry": round(entry, 2),
                    "exit": round(exit_p, 2),
                    "pnl_pct": round(pnl, 2),
                })
        
        if trade_details:
            wins = sum(1 for t in trades if t > 0)
            total = sum(trades)
            print(f"\n  {sym} End-of-Month Trades:")
            for t in trade_details:
                sign = "+" if t["pnl_pct"] >= 0 else ""
                result = "✅" if t["pnl_pct"] > 0 else "❌"
                print(f"    {t['entry_date']} → {t['exit_date']}: ${t['entry']:,.2f} → ${t['exit']:,.2f} = {sign}{t['pnl_pct']:.2f}% {result}")
            print(f"    Summary: {wins}/{len(trades)} wins ({wins/len(trades)*100:.0f}%) | Total: {total:+.2f}%")
    
    return {"active": active, "days_left": days_left}


# ═══════════════════════════════════════════════════════════════════════════
# PROOF 6: MULTI-FACTOR ENSEMBLE — WHAT DOES IT SAY RIGHT NOW?
# ═══════════════════════════════════════════════════════════════════════════

def proof_ensemble_live():
    print_header("PROOF 6: MULTI-FACTOR ENSEMBLE — LIVE COMPOSITE SIGNAL")
    
    symbols = ["BTC-USD", "ETH-USD", "SOL-USD", "SPY", "QQQ", "MATIC-USD", "IWM"]
    
    for sym in symbols:
        df = yf.download(sym, period="1y", interval="1d", auto_adjust=True, progress=False)
        if df.empty or len(df) < 60:
            continue
        
        close = df["Close"]
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
        
        # Calculate all signals for latest bar
        # RSI(2)
        delta = close.diff()
        gain = delta.where(delta > 0, 0.0).rolling(2, min_periods=2).mean()
        loss = (-delta.where(delta < 0, 0.0)).rolling(2, min_periods=2).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi2 = 100 - (100 / (1 + rs))
        
        # BB Z-score
        mid = close.rolling(20).mean()
        std = close.rolling(20).std()
        bb_z = (close - mid) / std.replace(0, np.nan)
        
        # Momentum
        mom_1m = close.pct_change(21)
        roc_10 = close.pct_change(10)
        
        # Price vs SMA
        sma200 = close.rolling(200).mean()
        price_vs_sma = ((close / sma200) - 1) if len(close) >= 200 else pd.Series(0, index=close.index)
        
        # Vol compression
        vol_short = close.pct_change().rolling(5).std()
        vol_long = close.pct_change().rolling(30).std()
        vol_ratio = vol_short / vol_long.replace(0, np.nan)
        
        # Current values
        curr = {
            "price": float(close.iloc[-1]),
            "rsi2": float(rsi2.iloc[-1]) if not pd.isna(rsi2.iloc[-1]) else 50,
            "bb_z": float(bb_z.iloc[-1]) if not pd.isna(bb_z.iloc[-1]) else 0,
            "mom_1m": float(mom_1m.iloc[-1]) * 100 if not pd.isna(mom_1m.iloc[-1]) else 0,
            "roc_10": float(roc_10.iloc[-1]) * 100 if not pd.isna(roc_10.iloc[-1]) else 0,
            "vol_ratio": float(vol_ratio.iloc[-1]) if not pd.isna(vol_ratio.iloc[-1]) else 1,
        }
        
        if len(close) >= 200 and not pd.isna(sma200.iloc[-1]):
            curr["price_vs_sma"] = float(price_vs_sma.iloc[-1]) * 100
        else:
            curr["price_vs_sma"] = 0
        
        # Composite score
        mean_rev_score = 0
        if curr["rsi2"] < 10: mean_rev_score += 2
        elif curr["rsi2"] < 20: mean_rev_score += 1
        elif curr["rsi2"] > 90: mean_rev_score -= 2
        elif curr["rsi2"] > 80: mean_rev_score -= 1
        
        if curr["bb_z"] < -2: mean_rev_score += 2
        elif curr["bb_z"] < -1: mean_rev_score += 1
        elif curr["bb_z"] > 2: mean_rev_score -= 2
        elif curr["bb_z"] > 1: mean_rev_score -= 1
        
        mom_score = 0
        if curr["mom_1m"] > 10: mom_score += 1
        elif curr["mom_1m"] < -10: mom_score -= 1
        if curr["roc_10"] > 5: mom_score += 1
        elif curr["roc_10"] < -5: mom_score -= 1
        
        composite = mean_rev_score + mom_score * 0.5
        
        if composite >= 2:
            verdict = "🟢 STRONG BUY"
        elif composite >= 1:
            verdict = "🟡 MILD BUY"
        elif composite <= -2:
            verdict = "🔴 STRONG SELL"
        elif composite <= -1:
            verdict = "🟠 MILD SELL"
        else:
            verdict = "⚪ NEUTRAL"
        
        print(f"\n  {sym:<10} ${curr['price']:>10,.2f}  RSI2:{curr['rsi2']:>5.1f}  BB_Z:{curr['bb_z']:>+5.2f}  "
              f"Mom1m:{curr['mom_1m']:>+6.1f}%  ROC10:{curr['roc_10']:>+6.1f}%  "
              f"VolR:{curr['vol_ratio']:>.2f}  → {verdict}")
    
    return True


# ═══════════════════════════════════════════════════════════════════════════
# MAIN — RUN ALL PROOFS
# ═══════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 100)
    print(f"  LIVE PROOF ENGINE — {NOW_EST.strftime('%B %d, %Y %I:%M %p EST')}")
    print(f"  Every number below comes from LIVE market data pulled THIS MOMENT")
    print(f"  No optimization, no cherry-picking, no lookahead")
    print("=" * 100)
    
    results = {}
    
    # 1. Fear & Greed
    results["fear_greed"] = proof_fear_greed()
    
    # 2. Connors RSI(2)
    results["connors_rsi2"] = proof_connors_rsi2()
    
    # 3. BTC Dominance
    results["btc_dominance"] = proof_btc_dominance()
    
    # 4. Funding Rates
    results["funding_rates"] = proof_funding_rates()
    
    # 5. End of Month
    results["end_of_month"] = proof_end_of_month()
    
    # 6. Multi-factor ensemble
    results["ensemble"] = proof_ensemble_live()
    
    # ─── FINAL VERDICT ─────────────────────────────────────────────
    print_header("FINAL VERDICT — WHAT TO DO RIGHT NOW")
    
    print(f"\n  ┌────────────────────────────────────────────────────────────────────┐")
    print(f"  │  ANTIGRAVITY LIVE SIGNALS — {NOW_EST.strftime('%Y-%m-%d %H:%M EST'):>20}            │")
    print(f"  ├────────────────────────────────────────────────────────────────────┤")
    
    fg = results.get("fear_greed", {})
    if fg and isinstance(fg, dict):
        fg_val = fg.get("current_value", "?")
        fg_sig = fg.get("signal", "?")
        print(f"  │  Fear & Greed:  {str(fg_val):>4} → {fg_sig:<47}│")
    
    rsi = results.get("connors_rsi2", {})
    if rsi:
        for sym in ["SPY", "BTC-USD", "ETH-USD"]:
            if sym in rsi:
                r = rsi[sym]
                print(f"  │  RSI(2) {sym:<8}: {r['current_rsi2']:>5.1f} → {r['signal']:<40}│")
    
    dom = results.get("btc_dominance", {})
    if dom and isinstance(dom, dict):
        print(f"  │  BTC Dominance: {dom.get('strength_change', '?'):>+5.1f}% → {dom.get('current_signal', '?'):<40}│")
    
    eom = results.get("end_of_month", {})
    if eom and isinstance(eom, dict):
        eom_status = "ACTIVE" if eom.get("active") else f"WAIT ({eom.get('days_left', '?')} days)"
        print(f"  │  End of Month:         → {eom_status:<40}│")
    
    print(f"  └────────────────────────────────────────────────────────────────────┘")
    
    # Save
    outfile = DATA_DIR / "live_proof.json"
    with open(outfile, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n  📁 Full results: {outfile}")


if __name__ == "__main__":
    main()
