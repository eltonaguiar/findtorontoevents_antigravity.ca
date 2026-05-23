#!/usr/bin/env python3
"""
ANTIGRAVITY PAPER TRADER — LIVE SIMULATION
============================================
Opens positions on our top consensus picks RIGHT NOW.
Tracks live P&L, checks TP/SL hits, declares winners/losers.

This is the PROOF. Real prices. Real entries. Real results.
"""

import json
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

NOW = datetime.now()
PORTFOLIO_FILE = DATA_DIR / "paper_portfolio.json"

# ═══════════════════════════════════════════════════════════════════════════
# OUR PICKS — Based on consensus from 10 strategies on Feb 17, 2026
# ═══════════════════════════════════════════════════════════════════════════

def get_live_price(symbol):
    """Get the most recent price"""
    try:
        df = yf.download(symbol, period="5d", interval="1d", auto_adjust=True, progress=False)
        if df.empty:
            return None
        close = df["Close"]
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
        return float(close.iloc[-1])
    except:
        return None


def open_positions():
    """Open paper positions on our top picks"""
    
    # These are our consensus STRONG signals from the 10-strategy scan
    trades = [
        {
            "symbol": "AVAX-USD",
            "name": "Avalanche",
            "direction": "LONG",
            "reason": "3/3 strategies BULLISH | RSI2=0.0 EXTREME oversold | MACD expanding | Ensemble +1",
            "strategies_agreeing": ["RSI2_MEAN_REVERSION (70%)", "MACD_CROSSOVER (50%)", "MULTI_FACTOR_ENSEMBLE (45%)"],
            "tp_pct": 19.0,   # ~$10.87 from $9.14
            "sl_pct": 13.0,   # ~$7.95 from $9.14
        },
        {
            "symbol": "BTC-USD",
            "name": "Bitcoin",
            "direction": "LONG",
            "reason": "5/6 strategies BULLISH | RSI2=3.4 | F&G=8 Extreme Fear | MACD expanding | BTC Dom rising",
            "strategies_agreeing": ["RSI2 (70%)", "FEAR_GREED (60%)", "BTC_DOMINANCE (50%)", "MACD (50%)", "ENSEMBLE (45%)"],
            "tp_pct": 25.0,
            "sl_pct": 13.0,
        },
        {
            "symbol": "TSLA",
            "name": "Tesla",
            "direction": "LONG",
            "reason": "4/4 strategies BULLISH (ZERO sells) | Ensemble STRONG BUY 75% | RSI2=5.2 | OBV accumulation",
            "strategies_agreeing": ["ENSEMBLE (75%)", "RSI2 (60%)", "GOLDEN_CROSS (45%)", "OBV_DIVERGENCE (45%)"],
            "tp_pct": 9.5,
            "sl_pct": 8.5,
        },
        {
            "symbol": "QQQ",
            "name": "Nasdaq 100",
            "direction": "LONG",
            "reason": "3/3 strategies BULLISH | Stochastic bullish crossover in oversold | Golden Cross | Ensemble",
            "strategies_agreeing": ["STOCHASTIC (70%)", "GOLDEN_CROSS (45%)", "ENSEMBLE (45%)"],
            "tp_pct": 5.0,
            "sl_pct": 3.0,
        },
        {
            "symbol": "DOGE-USD",
            "name": "Dogecoin",
            "direction": "LONG",
            "reason": "2/2 strategies BULLISH | RSI2=0.0 EXTREME oversold | Ensemble MILD_BUY",
            "strategies_agreeing": ["RSI2 (70%)", "ENSEMBLE (45%)"],
            "tp_pct": 20.0,
            "sl_pct": 15.0,
        },
    ]
    
    portfolio = {
        "opened_at": NOW.strftime("%Y-%m-%d %H:%M:%S EST"),
        "status": "ACTIVE",
        "starting_capital": 10000,
        "allocation": "equal_weight",  # $2000 per trade
        "per_trade": 2000,
        "positions": [],
        "closed_positions": [],
        "pnl_history": [],
    }
    
    print("=" * 100)
    print(f"  ANTIGRAVITY PAPER TRADER — OPENING POSITIONS")
    print(f"  {NOW.strftime('%B %d, %Y %I:%M %p EST')}")
    print(f"  Starting Capital: $10,000 | 5 positions × $2,000 each")
    print("=" * 100)
    
    total_invested = 0
    
    for trade in trades:
        price = get_live_price(trade["symbol"])
        if not price:
            print(f"  ⚠️  Could not get price for {trade['symbol']}, skipping")
            continue
        
        qty = 2000 / price
        tp = round(price * (1 + trade["tp_pct"] / 100), 6)
        sl = round(price * (1 - trade["sl_pct"] / 100), 6)
        
        position = {
            "symbol": trade["symbol"],
            "name": trade["name"],
            "direction": trade["direction"],
            "reason": trade["reason"],
            "strategies": trade["strategies_agreeing"],
            "entry_price": price,
            "quantity": round(qty, 6),
            "invested": 2000,
            "tp": tp,
            "sl": sl,
            "tp_pct": trade["tp_pct"],
            "sl_pct": trade["sl_pct"],
            "entry_time": NOW.strftime("%Y-%m-%d %H:%M:%S EST"),
            "status": "OPEN",
            "max_hold_days": 14,
            "exit_by": (NOW + timedelta(days=14)).strftime("%Y-%m-%d"),
        }
        
        portfolio["positions"].append(position)
        total_invested += 2000
        
        risk = price - sl
        reward = tp - price
        rr = reward / risk if risk > 0 else 0
        
        print(f"\n  🟢 OPENED: {trade['name']} ({trade['symbol']})")
        print(f"     Entry:  ${price:,.6f}")
        print(f"     Qty:    {qty:,.6f}")
        print(f"     TP:     ${tp:,.6f} (+{trade['tp_pct']}%)")
        print(f"     SL:     ${sl:,.6f} (-{trade['sl_pct']}%)")
        print(f"     R:R:    {rr:.2f}")
        print(f"     Why:    {trade['reason']}")
        print(f"     Exit by: {position['exit_by']}")
    
    portfolio["total_invested"] = total_invested
    
    # Save portfolio
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(portfolio, f, indent=2, default=str)
    
    print(f"\n{'='*100}")
    print(f"  ✅ {len(portfolio['positions'])} positions opened | ${total_invested:,.0f} deployed")
    print(f"  📁 Portfolio saved: {PORTFOLIO_FILE}")
    print(f"  ⏰ Max hold: 14 days (exit by {(NOW + timedelta(days=14)).strftime('%Y-%m-%d')})")
    print(f"{'='*100}")
    
    return portfolio


def check_portfolio():
    """Check current P&L on all open positions"""
    
    if not PORTFOLIO_FILE.exists():
        print("  No portfolio found. Run with 'open' first.")
        return
    
    with open(PORTFOLIO_FILE) as f:
        portfolio = json.load(f)
    
    if not portfolio["positions"]:
        print("  No open positions.")
        return
    
    print("=" * 100)
    print(f"  ANTIGRAVITY PAPER TRADER — LIVE P&L CHECK")
    print(f"  {NOW.strftime('%B %d, %Y %I:%M %p EST')}")
    print(f"  Opened: {portfolio['opened_at']}")
    print("=" * 100)
    
    total_pnl = 0
    total_pnl_pct = 0
    wins = 0
    losses = 0
    active = 0
    
    results = []
    
    for pos in portfolio["positions"]:
        if pos["status"] != "OPEN":
            continue
        
        current = get_live_price(pos["symbol"])
        if not current:
            print(f"  ⚠️  Could not get price for {pos['symbol']}")
            continue
        
        entry = pos["entry_price"]
        pnl_pct = (current - entry) / entry * 100
        pnl_dollar = pos["invested"] * pnl_pct / 100
        
        total_pnl += pnl_dollar
        total_pnl_pct += pnl_pct
        
        # Check TP/SL
        hit_tp = current >= pos["tp"]
        hit_sl = current <= pos["sl"]
        
        if hit_tp:
            status = "🏆 TP HIT"
            wins += 1
            pos["status"] = "CLOSED_TP"
            pos["exit_price"] = current
            pos["exit_time"] = NOW.strftime("%Y-%m-%d %H:%M:%S EST")
            pos["pnl_pct"] = pnl_pct
            pos["pnl_dollar"] = pnl_dollar
            portfolio["closed_positions"].append(pos.copy())
        elif hit_sl:
            status = "💀 SL HIT"
            losses += 1
            pos["status"] = "CLOSED_SL"
            pos["exit_price"] = current
            pos["exit_time"] = NOW.strftime("%Y-%m-%d %H:%M:%S EST")
            pos["pnl_pct"] = pnl_pct
            pos["pnl_dollar"] = pnl_dollar
            portfolio["closed_positions"].append(pos.copy())
        elif pnl_pct > 0:
            status = "🟢 WINNING"
            active += 1
        elif pnl_pct < -5:
            status = "🔴 LOSING"
            active += 1
        else:
            status = "⚪ FLAT"
            active += 1
        
        icon = "🟢" if pnl_pct > 0 else "🔴"
        
        results.append({
            "symbol": pos["symbol"],
            "name": pos["name"],
            "entry": entry,
            "current": current,
            "pnl_pct": pnl_pct,
            "pnl_dollar": pnl_dollar,
            "tp": pos["tp"],
            "sl": pos["sl"],
            "status": status,
        })
        
        print(f"\n  {icon} {pos['name']} ({pos['symbol']})")
        print(f"     Entry:   ${entry:,.6f}")
        print(f"     Current: ${current:,.6f}")
        print(f"     P&L:     {pnl_pct:+.2f}% (${pnl_dollar:+,.2f})")
        print(f"     TP:      ${pos['tp']:,.6f} ({((pos['tp']-current)/current*100):+.1f}% away)")
        print(f"     SL:      ${pos['sl']:,.6f} ({((pos['sl']-current)/current*100):+.1f}% away)")
        print(f"     Status:  {status}")
    
    # Remove closed positions from active
    portfolio["positions"] = [p for p in portfolio["positions"] if p["status"] == "OPEN"]
    
    # Log P&L snapshot
    portfolio["pnl_history"].append({
        "timestamp": NOW.strftime("%Y-%m-%d %H:%M:%S EST"),
        "total_pnl_pct": round(total_pnl_pct, 2),
        "total_pnl_dollar": round(total_pnl, 2),
        "positions": len(results),
        "wins": wins,
        "losses": losses,
    })
    
    # Summary
    avg_pnl = total_pnl_pct / len(results) if results else 0
    portfolio_return = total_pnl / portfolio["starting_capital"] * 100
    
    print(f"\n{'='*100}")
    print(f"  📊 PORTFOLIO SUMMARY")
    print(f"{'='*100}")
    print(f"  Starting Capital: ${portfolio['starting_capital']:,.0f}")
    print(f"  Current P&L:      ${total_pnl:+,.2f} ({portfolio_return:+.2f}%)")
    print(f"  Active:           {active} positions")
    print(f"  TP Hits:          {wins}")
    print(f"  SL Hits:          {losses}")
    print(f"  Avg P&L/trade:    {avg_pnl:+.2f}%")
    
    if total_pnl > 0:
        print(f"\n  🏆 WE'RE WINNING. ${total_pnl:+,.2f} profit on ${portfolio['starting_capital']:,.0f}.")
    elif total_pnl < -200:
        print(f"\n  🔴 Drawdown of ${total_pnl:,.2f}. Positions still active — waiting for TP/SL.")
    else:
        print(f"\n  ⚪ Roughly flat. Positions in play.")
    
    print(f"\n  {'─'*80}")
    print(f"  TRADE SCOREBOARD")
    print(f"  {'─'*80}")
    print(f"  {'ASSET':<12} {'ENTRY':>10} {'CURRENT':>10} {'P&L':>8} {'$P&L':>10} {'STATUS'}")
    print(f"  {'-'*70}")
    for r in sorted(results, key=lambda x: x["pnl_pct"], reverse=True):
        print(f"  {r['symbol']:<12} ${r['entry']:>9,.2f} ${r['current']:>9,.2f} {r['pnl_pct']:>+7.2f}% ${r['pnl_dollar']:>+9,.2f} {r['status']}")
    
    # Save
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(portfolio, f, indent=2, default=str)
    
    print(f"\n  📁 Updated: {PORTFOLIO_FILE}")
    return portfolio


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        check_portfolio()
    else:
        # If portfolio exists, check it. Otherwise, open new positions.
        if PORTFOLIO_FILE.exists():
            print("  Portfolio exists. Checking P&L...")
            print()
            check_portfolio()
        else:
            open_positions()
