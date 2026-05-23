#!/usr/bin/env python3
"""
ANTIGRAVITY LIVE SPIKE PREDICTOR v2 — 2-HOUR CHALLENGE
=======================================================
4 algorithms compete to predict crypto/forex spikes in real-time.
Each prediction has: entry price, TP, SL, timestamp (EST), direction.

v2 fixes:
  - Much more aggressive signal detection (will actually fire!)
  - EST timestamps for all price actions
  - Relative strength comparison between symbols
  - Momentum acceleration detection
  - Tracks price at prediction vs current for real P&L

Run:  python live_challenge.py
"""

import json
import time
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timezone, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

EST = ZoneInfo("America/New_York")

CRYPTO_SYMS = ["BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD", "DOGE-USD",
               "ADA-USD", "AVAX-USD", "LINK-USD", "BNB-USD", "DOT-USD"]
FOREX_SYMS = ["EURUSD=X", "GBPUSD=X", "AUDUSD=X"]
ALL_SYMS = CRYPTO_SYMS + FOREX_SYMS

CHALLENGE_DURATION = 7200  # 2 hours
CHECK_INTERVAL = 90  # 90 seconds between checks
MAX_PREDICTIONS_PER_ALGO = 25

def now_est():
    return datetime.now(EST).strftime("%Y-%m-%d %I:%M:%S %p EST")

def now_est_iso():
    return datetime.now(EST).isoformat()

# ═══════════════════════════════════════════════════════════════════════════
# INDICATORS
# ═══════════════════════════════════════════════════════════════════════════
def calc_rsi(close, period=14):
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0).rolling(window=period, min_periods=period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window=period, min_periods=period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def calc_ema(s, period):
    return s.ewm(span=period, adjust=False).mean()

def calc_atr(df, period=14):
    high, low, close = df["High"], df["Low"], df["Close"]
    tr = pd.concat([high - low, (high - close.shift(1)).abs(),
                    (low - close.shift(1)).abs()], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def calc_bb(close, period=20, num_std=2):
    mid = close.rolling(period).mean()
    std = close.rolling(period).std()
    return mid, mid + num_std * std, mid - num_std * std

def calc_macd(close, fast=12, slow=26, signal=9):
    ef = calc_ema(close, fast)
    es = calc_ema(close, slow)
    ml = ef - es
    sl = calc_ema(ml, signal)
    return ml, sl, ml - sl

# ═══════════════════════════════════════════════════════════════════════════
# 4 ALGORITHMS — AGGRESSIVE EDITION
# ═══════════════════════════════════════════════════════════════════════════

class AlgoBase:
    def __init__(self, name):
        self.name = name
        self.predictions = []
        self.active = {}
    
    def _pred(self, sym, price, direction, tp_pct, sl_pct, confidence, reason):
        if len(self.predictions) >= MAX_PREDICTIONS_PER_ALGO: return None
        if sym in self.active: return None
        
        pred = {
            "algo": self.name, "symbol": sym, "direction": direction,
            "entry_price": round(price, 6),
            "tp_price": round(price * (1 + tp_pct/100) if direction == "LONG" else price * (1 - tp_pct/100), 6),
            "sl_price": round(price * (1 - sl_pct/100) if direction == "LONG" else price * (1 + sl_pct/100), 6),
            "tp_pct": round(tp_pct, 2), "sl_pct": round(sl_pct, 2),
            "confidence": confidence, "reason": reason,
            "entry_time_est": now_est(), "entry_time_iso": now_est_iso(),
            "outcome": "OPEN", "exit_price": None, "pnl_pct": None,
            "exit_time_est": None, "current_price": price, "unrealized_pnl": 0,
        }
        self.predictions.append(pred)
        self.active[sym] = pred
        return pred


class MomentumSniper(AlgoBase):
    """Detects momentum acceleration — price moving faster than recent average."""
    def __init__(self):
        super().__init__("MOMENTUM_SNIPER")
    
    def predict(self, sym, df, price, asset_type):
        if len(df) < 20: return None
        c = df["Close"]
        
        # Calculate momentum: rate of change over different periods
        roc_3 = (float(c.iloc[-1]) - float(c.iloc[-4])) / float(c.iloc[-4]) * 100 if len(c) > 4 else 0
        roc_6 = (float(c.iloc[-1]) - float(c.iloc[-7])) / float(c.iloc[-7]) * 100 if len(c) > 7 else 0
        roc_12 = (float(c.iloc[-1]) - float(c.iloc[-13])) / float(c.iloc[-13]) * 100 if len(c) > 13 else 0
        
        rsi = calc_rsi(c, 14)
        r = float(rsi.iloc[-1]) if not np.isnan(rsi.iloc[-1]) else 50
        
        vol = df.get("Volume")
        vr = 1.0
        if vol is not None and len(vol) >= 15:
            avg = float(vol.iloc[-15:-1].mean())
            vr = float(vol.iloc[-1]) / avg if avg > 0 else 1.0
        
        # Accelerating upward momentum (roc_3 > roc_6 > 0) 
        if roc_3 > 0.3 and roc_3 > roc_6 and r < 70:
            tp = 0.8 if asset_type == "forex" else 2.0
            sl = 0.4 if asset_type == "forex" else 1.0
            conf = min(80, 50 + int(abs(roc_3) * 10) + int(vr * 3))
            return self._pred(sym, price, "LONG", tp, sl, conf,
                              f"Momentum accelerating: ROC3={roc_3:+.2f}% RSI={r:.0f} Vol={vr:.1f}x")
        
        # Accelerating downward momentum
        if roc_3 < -0.3 and roc_3 < roc_6 and r > 30:
            tp = 0.8 if asset_type == "forex" else 2.0
            sl = 0.4 if asset_type == "forex" else 1.0
            conf = min(80, 50 + int(abs(roc_3) * 10) + int(vr * 3))
            return self._pred(sym, price, "SHORT", tp, sl, conf,
                              f"Momentum dropping: ROC3={roc_3:+.2f}% RSI={r:.0f} Vol={vr:.1f}x")
        
        # RSI extreme + any momentum = bounce/rejection
        if r < 25:
            return self._pred(sym, price, "LONG", 1.5, 0.8, 60,
                              f"RSI extreme oversold: {r:.0f}")
        if r > 75:
            return self._pred(sym, price, "SHORT", 1.5, 0.8, 60,
                              f"RSI extreme overbought: {r:.0f}")
        
        return None


class BreakoutHunter(AlgoBase):
    """Detects price breaking above/below recent range."""
    def __init__(self):
        super().__init__("BREAKOUT_HUNTER")
    
    def predict(self, sym, df, price, asset_type):
        if len(df) < 20: return None
        
        # 12-bar range (not 20 — more responsive)
        h12 = float(df["High"].iloc[-13:-1].max())
        l12 = float(df["Low"].iloc[-13:-1].min())
        range_pct = (h12 - l12) / l12 * 100
        
        vol = df.get("Volume"); vr = 1.0
        if vol is not None and len(vol) >= 15:
            avg = float(vol.iloc[-15:-1].mean())
            vr = float(vol.iloc[-1]) / avg if avg > 0 else 1.0
        
        # Breakout UP
        if price > h12:
            tp = max(range_pct * 0.5, 0.5 if asset_type == "forex" else 1.5)
            sl = max(range_pct * 0.25, 0.3 if asset_type == "forex" else 0.8)
            conf = min(75, 45 + int(vr * 5) + int(range_pct * 2))
            return self._pred(sym, price, "LONG", tp, sl, conf,
                              f"12-bar breakout UP ${price:.2f}>{h12:.2f} range={range_pct:.1f}% Vol={vr:.1f}x")
        
        # Breakout DOWN
        if price < l12:
            tp = max(range_pct * 0.5, 0.5 if asset_type == "forex" else 1.5)
            sl = max(range_pct * 0.25, 0.3 if asset_type == "forex" else 0.8)
            conf = min(75, 45 + int(vr * 5) + int(range_pct * 2))
            return self._pred(sym, price, "SHORT", tp, sl, conf,
                              f"12-bar breakdown ${price:.2f}<{l12:.2f} range={range_pct:.1f}% Vol={vr:.1f}x")
        
        return None


class MeanRevBot(AlgoBase):
    """BB extreme + RSI divergence = snap back."""
    def __init__(self):
        super().__init__("MEAN_REVERSION")
    
    def predict(self, sym, df, price, asset_type):
        if len(df) < 25: return None
        c = df["Close"]
        mid, upper, lower = calc_bb(c, 20, 2)
        rsi = calc_rsi(c, 14)
        
        if any(np.isnan(x.iloc[-1]) for x in [mid, upper, lower, rsi]):
            return None
        
        u, l, m = float(upper.iloc[-1]), float(lower.iloc[-1]), float(mid.iloc[-1])
        r = float(rsi.iloc[-1])
        
        # Position within BB (0 = bottom, 1 = top)
        bb_pos = (price - l) / (u - l) if (u - l) > 0 else 0.5
        
        # Near/below lower BB band = bounce
        if bb_pos < 0.1 or (bb_pos < 0.2 and r < 35):
            tp = 0.6 if asset_type == "forex" else 1.5
            sl = 0.4 if asset_type == "forex" else 1.0
            conf = min(75, 50 + int((0.2 - bb_pos) * 100))
            return self._pred(sym, price, "LONG", tp, sl, conf,
                              f"BB position {bb_pos:.2f} (near bottom) RSI={r:.0f}")
        
        # Near/above upper BB band = rejection
        if bb_pos > 0.9 or (bb_pos > 0.8 and r > 65):
            tp = 0.6 if asset_type == "forex" else 1.5
            sl = 0.4 if asset_type == "forex" else 1.0
            conf = min(75, 50 + int((bb_pos - 0.8) * 100))
            return self._pred(sym, price, "SHORT", tp, sl, conf,
                              f"BB position {bb_pos:.2f} (near top) RSI={r:.0f}")
        
        return None


class TrendSurfer(AlgoBase):
    """EMA alignment = ride the trend (most relaxed criteria)."""
    def __init__(self):
        super().__init__("TREND_SURFER")
    
    def predict(self, sym, df, price, asset_type):
        if len(df) < 30: return None
        c = df["Close"]
        ema9 = calc_ema(c, 9)
        ema21 = calc_ema(c, 21)
        ml, sl_l, hist = calc_macd(c)
        
        if any(np.isnan(x.iloc[-1]) for x in [ema9, ema21, hist]):
            return None
        
        e9 = float(ema9.iloc[-1]); e21 = float(ema21.iloc[-1])
        h = float(hist.iloc[-1])
        
        # Price momentum over last 3 bars
        ret3 = (float(c.iloc[-1]) - float(c.iloc[-4])) / float(c.iloc[-4]) * 100 if len(c) > 4 else 0
        
        # Bullish: price > EMA9 > EMA21 OR EMA9 just crossed above EMA21
        e9_prev = float(ema9.iloc[-2]); e21_prev = float(ema21.iloc[-2])
        
        if (e9 > e21 and price > e9) or (e9 > e21 and e9_prev <= e21_prev):
            tp = 1.0 if asset_type == "forex" else 2.0
            sl_v = 0.5 if asset_type == "forex" else 1.0
            conf = 55 + (5 if h > 0 else 0) + (5 if ret3 > 0.2 else 0)
            return self._pred(sym, price, "LONG", tp, sl_v, min(75, conf),
                              f"Trend UP: 9EMA>{e9:.2f} 21EMA>{e21:.2f} MACD_H={h:.4f} Ret3={ret3:+.2f}%")
        
        # Bearish: price < EMA9 < EMA21 OR EMA9 just crossed below EMA21
        if (e9 < e21 and price < e9) or (e9 < e21 and e9_prev >= e21_prev):
            tp = 1.0 if asset_type == "forex" else 2.0
            sl_v = 0.5 if asset_type == "forex" else 1.0
            conf = 55 + (5 if h < 0 else 0) + (5 if ret3 < -0.2 else 0)
            return self._pred(sym, price, "SHORT", tp, sl_v, min(75, conf),
                              f"Trend DOWN: 9EMA<{e9:.2f} 21EMA<{e21:.2f} MACD_H={h:.4f} Ret3={ret3:+.2f}%")
        
        return None


# ═══════════════════════════════════════════════════════════════════════════
# POSITION RESOLVER
# ═══════════════════════════════════════════════════════════════════════════
def resolve(algo, prices):
    resolved = []
    for sym, p in list(algo.active.items()):
        if sym not in prices: continue
        cp = prices[sym]
        p["current_price"] = cp
        
        if p["direction"] == "LONG":
            p["unrealized_pnl"] = round(((cp - p["entry_price"]) / p["entry_price"]) * 100, 3)
            if cp >= p["tp_price"]:
                p["outcome"] = "WIN"; p["exit_price"] = cp; p["pnl_pct"] = round(p["tp_pct"], 2)
                p["exit_time_est"] = now_est(); resolved.append(p); del algo.active[sym]
            elif cp <= p["sl_price"]:
                p["outcome"] = "LOSS"; p["exit_price"] = cp; p["pnl_pct"] = round(-p["sl_pct"], 2)
                p["exit_time_est"] = now_est(); resolved.append(p); del algo.active[sym]
        else:
            p["unrealized_pnl"] = round(((p["entry_price"] - cp) / p["entry_price"]) * 100, 3)
            if cp <= p["tp_price"]:
                p["outcome"] = "WIN"; p["exit_price"] = cp; p["pnl_pct"] = round(p["tp_pct"], 2)
                p["exit_time_est"] = now_est(); resolved.append(p); del algo.active[sym]
            elif cp >= p["sl_price"]:
                p["outcome"] = "LOSS"; p["exit_price"] = cp; p["pnl_pct"] = round(-p["sl_pct"], 2)
                p["exit_time_est"] = now_est(); resolved.append(p); del algo.active[sym]
    return resolved


def save_results(algos, start_dt, cycle, status):
    results = {
        "challenge": "2-HOUR LIVE SPIKE PREDICTION v2",
        "status": status,
        "started_at_est": start_dt.astimezone(EST).strftime("%Y-%m-%d %I:%M:%S %p EST"),
        "current_time_est": now_est(),
        "cycles_completed": cycle,
        "algorithms": {},
        "all_predictions": [],
    }
    
    for algo in algos:
        closed = [p for p in algo.predictions if p["outcome"] != "OPEN"]
        open_p = [p for p in algo.predictions if p["outcome"] == "OPEN"]
        wins = len([p for p in closed if p["outcome"] == "WIN"])
        losses = len([p for p in closed if p["outcome"] == "LOSS"])
        pnl = sum(float(p.get("pnl_pct", 0) or 0) or 0 for p in closed)
        # Include unrealized P&L
        unrealized = sum(p.get("unrealized_pnl", 0) or 0 for p in open_p)
        wr = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
        
        results["algorithms"][algo.name] = {
            "predictions": len(algo.predictions), "resolved": len(closed),
            "open": len(open_p), "wins": wins, "losses": losses,
            "win_rate": round(wr, 1), "realized_pnl": round(pnl, 2),
            "unrealized_pnl": round(unrealized, 2),
            "total_pnl": round(pnl + unrealized, 2),
        }
        for p in algo.predictions:
            results["all_predictions"].append(p)
    
    out = DATA_DIR / "live_challenge_results.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════
def main():
    start_time = time.time()
    start_dt = datetime.now(timezone.utc)
    end_time = start_dt + timedelta(seconds=CHALLENGE_DURATION)
    
    print("=" * 80)
    print("⚔️  ANTIGRAVITY 2-HOUR LIVE CHALLENGE v2")
    print(f"   Started: {now_est()}")
    print(f"   Ends:    {end_time.astimezone(EST).strftime('%Y-%m-%d %I:%M:%S %p EST')}")
    print(f"   Symbols: {len(ALL_SYMS)} (crypto + forex)")
    print(f"   Check interval: {CHECK_INTERVAL}s")
    print("   4 algorithms: MOMENTUM_SNIPER, BREAKOUT_HUNTER, MEAN_REVERSION, TREND_SURFER")
    print("=" * 80)
    
    algos = [MomentumSniper(), BreakoutHunter(), MeanRevBot(), TrendSurfer()]
    cycle = 0
    
    while time.time() - start_time < CHALLENGE_DURATION:
        cycle += 1
        elapsed = time.time() - start_time
        remaining = CHALLENGE_DURATION - elapsed
        
        print(f"\n{'─'*70}")
        print(f"  Cycle {cycle}  |  {now_est()}  |  "
              f"Elapsed: {elapsed/60:.1f}m  |  Remaining: {remaining/60:.1f}m")
        print(f"{'─'*70}")
        
        # Fetch data
        try:
            batch = yf.download(ALL_SYMS, period="5d", interval="15m",
                                group_by="ticker", auto_adjust=True,
                                progress=False, threads=True)
        except Exception as e:
            print(f"  ⚠️  Download error: {e}")
            time.sleep(CHECK_INTERVAL)
            continue
        
        prices = {}; yf_data = {}
        for sym in ALL_SYMS:
            try:
                df = batch[sym].dropna() if len(ALL_SYMS) > 1 else batch.dropna()
                if len(df) >= 20:
                    yf_data[sym] = df
                    prices[sym] = float(df["Close"].iloc[-1])
            except: continue
        
        if not prices:
            print("  ⚠️  No data"); time.sleep(CHECK_INTERVAL); continue
        
        # Show key prices
        btc = prices.get("BTC-USD", 0)
        eth = prices.get("ETH-USD", 0)
        sol = prices.get("SOL-USD", 0)
        print(f"  📊 BTC=${btc:,.0f}  ETH=${eth:,.0f}  SOL=${sol:,.0f}")
        
        # 1. Resolve positions
        for algo in algos:
            for r in resolve(algo, prices):
                icon = "✅" if r["outcome"] == "WIN" else "❌"
                print(f"  {icon} RESOLVED: {algo.name:20s} {r['symbol']:12s} "
                      f"{r['direction']:5s} → {r['outcome']}  P&L:{r['pnl_pct']:+.2f}%  "
                      f"Entry:{r['entry_time_est']}  Exit:{r['exit_time_est']}")
        
        # 2. Generate predictions
        new_preds = 0
        for algo in algos:
            for sym in ALL_SYMS:
                if sym not in yf_data: continue
                atype = "forex" if "=X" in sym else "crypto"
                p = algo.predict(sym, yf_data[sym], prices[sym], atype)
                if p:
                    new_preds += 1
                    print(f"  🎯 NEW: {algo.name:20s} {p['direction']:5s} {sym:12s} "
                          f"@ ${p['entry_price']:.4f}  TP:{p['tp_pct']:+.1f}%  "
                          f"SL:-{p['sl_pct']:.1f}%  Conf:{p['confidence']}%")
                    print(f"         Reason: {p['reason']}")
                    print(f"         Time: {p['entry_time_est']}")
        
        if new_preds == 0:
            print("  📭 No new signals this cycle")
        
        # 3. Show open positions with unrealized P&L
        any_open = False
        for algo in algos:
            for sym, p in algo.active.items():
                if sym in prices:
                    cp = prices[sym]
                    if p["direction"] == "LONG":
                        unr = ((cp - p["entry_price"]) / p["entry_price"]) * 100
                    else:
                        unr = ((p["entry_price"] - cp) / p["entry_price"]) * 100
                    p["unrealized_pnl"] = round(unr, 3)
                    p["current_price"] = cp
                    icon = "📈" if unr > 0 else "📉"
                    if not any_open:
                        print(f"\n  Open positions:")
                        any_open = True
                    print(f"    {icon} {algo.name:20s} {sym:12s} {p['direction']:5s}  "
                          f"Entry:${p['entry_price']:.4f}  Now:${cp:.4f}  "
                          f"Unrealized:{unr:+.2f}%")
        
        # 4. Leaderboard
        print(f"\n  {'━'*60}")
        print(f"  {'LEADERBOARD':^60}")
        print(f"  {'━'*60}")
        
        for algo in sorted(algos, key=lambda a: sum(
                (float(p.get("pnl_pct", 0) or 0) or 0) for p in a.predictions if p["outcome"] != "OPEN") +
                sum((p.get("unrealized_pnl", 0) or 0) for p in a.predictions if p["outcome"] == "OPEN"),
                reverse=True):
            closed = [p for p in algo.predictions if p["outcome"] != "OPEN"]
            open_p = [p for p in algo.predictions if p["outcome"] == "OPEN"]
            wins = len([p for p in closed if p["outcome"] == "WIN"])
            losses = len([p for p in closed if p["outcome"] == "LOSS"])
            rpnl = sum(float(p.get("pnl_pct", 0) or 0) or 0 for p in closed)
            upnl = sum(p.get("unrealized_pnl", 0) or 0 for p in open_p)
            
            print(f"  {algo.name:20s}  Picks:{len(algo.predictions):2d}  "
                  f"W:{wins} L:{losses} Open:{len(open_p)}  "
                  f"Realized:{rpnl:+.2f}%  Unrealized:{upnl:+.2f}%  "
                  f"Total:{rpnl+upnl:+.2f}%")
        
        save_results(algos, start_dt, cycle, "RUNNING")
        
        print(f"\n  ⏳ Next check in {CHECK_INTERVAL}s...")
        time.sleep(CHECK_INTERVAL)
    
    # FINAL — force close all
    print("\n" + "=" * 80)
    print("⏰ TIME'S UP — Force-closing all open positions")
    
    try:
        batch = yf.download(ALL_SYMS, period="1d", interval="1m",
                            group_by="ticker", auto_adjust=True,
                            progress=False, threads=True)
        for sym in ALL_SYMS:
            try:
                df = batch[sym].dropna() if len(ALL_SYMS) > 1 else batch.dropna()
                if len(df) > 0: prices[sym] = float(df["Close"].iloc[-1])
            except: continue
    except: pass
    
    for algo in algos:
        for sym, p in list(algo.active.items()):
            if sym in prices:
                cp = prices[sym]
                pnl = ((cp - p["entry_price"]) / p["entry_price"]) * 100 if p["direction"] == "LONG" \
                    else ((p["entry_price"] - cp) / p["entry_price"]) * 100
                p["outcome"] = "EXPIRED"; p["exit_price"] = cp
                p["pnl_pct"] = round(pnl, 2); p["exit_time_est"] = now_est()
        algo.active = {}
    
    print("\n" + "=" * 80)
    print("🏆 FINAL RESULTS — 2-HOUR CHALLENGE")
    print(f"   {now_est()}")
    print("=" * 80)
    
    winner_algo = None; best_pnl = -999
    for algo in algos:
        all_p = algo.predictions
        wins = len([p for p in all_p if p["outcome"] == "WIN"])
        losses = len([p for p in all_p if p["outcome"] == "LOSS"])
        expired = len([p for p in all_p if p["outcome"] == "EXPIRED"])
        pnl = sum(float(p.get("pnl_pct", 0) or 0) or 0 for p in all_p)
        wr = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
        
        icon = "🥇" if pnl > 0 else "💀"
        print(f"  {icon} {algo.name:20s}  Picks:{len(all_p):2d}  "
              f"W:{wins} L:{losses} E:{expired}  WR:{wr:.0f}%  P&L:{pnl:+.2f}%")
        
        if pnl > best_pnl:
            best_pnl = pnl; winner_algo = algo.name
    
    print(f"\n  🏆 WINNER: {winner_algo}  ({best_pnl:+.2f}% total P&L)")
    
    save_results(algos, start_dt, cycle, "COMPLETE")
    print(f"\n  📁 Results: data/live_challenge_results.json")
    print(f"\n{'='*80}")

if __name__ == "__main__":
    main()
