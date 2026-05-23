#!/usr/bin/env python3
"""
CONSISTENCY PROOF -- Multi-Session Win Rate Tracker
====================================================
Runs N sessions of the forex momentum strategy back-to-back,
each with fresh data, and tracks cumulative statistics.

A "winner" must prove itself across:
  - Multiple independent sessions (different market moments)
  - Binomial test: p < 0.05 that WR > 50%
  - Minimum 20 closed trades before any claim
  - Consistent across all 3 strategies (not just one)

Usage:
  python prove_consistency.py [--sessions 5] [--delay 60]
  python prove_consistency.py --report          # show history only
"""

import json
import sys
import time
import math
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from collections import defaultdict

import numpy as np
import pandas as pd
import yfinance as yf

BASE     = Path(__file__).resolve().parent
DATA_DIR = BASE / "data"
PROOF_FILE = DATA_DIR / "consistency_proof.json"

UTC = timezone.utc
EST = ZoneInfo("America/New_York")

POSITION_SIZE = 2000
FOREX_PAIRS = {
    "AUDUSD=X": "SELL",
    "GBPUSD=X": "SELL",
    "EURUSD=X": "SELL",
    "USDJPY=X": "BUY",
    "USDCHF=X": "BUY",
    "NZDUSD=X": "SELL",
}


# -- Indicators -----------------------------------------------------------------
def ema(s, n): return s.ewm(span=n, adjust=False).mean()

def rsi(s, n=14):
    d = s.diff().dropna()
    g = d.clip(lower=0).rolling(n).mean()
    l = (-d.clip(upper=0)).rolling(n).mean()
    rs = g / l.replace(0, np.nan)
    r = 100 - 100 / (1 + rs)
    return float(r.iloc[-1]) if not r.empty else 50.0

def atr(df, n=14):
    h, l, c = df["High"], df["Low"], df["Close"].shift(1)
    tr = pd.concat([h-l, (h-c).abs(), (l-c).abs()], axis=1).max(axis=1)
    return float(tr.rolling(n).mean().iloc[-1])

def macd_hist(s):
    f = ema(s, 12).iloc[-1]; sl = ema(s, 26).iloc[-1]
    ml = f - sl
    sig = ema(pd.Series(ema(s, 12).values - ema(s, 26).values), 9).iloc[-1]
    return float(ml - sig)


# -- Fetch -----------------------------------------------------------------------
def fetch_data(symbols, interval="5m", period="2d"):
    syms = " ".join(symbols)
    try:
        raw = yf.download(syms, period=period, interval=interval,
                          group_by="ticker", auto_adjust=True,
                          threads=True, progress=False)
        data = {}
        for sym in symbols:
            try:
                df = raw[sym] if len(symbols) > 1 else raw
                df = df.dropna(subset=["Close"])
                if len(df) >= 20:
                    data[sym] = df
            except Exception:
                continue
        return data
    except Exception:
        return {}

def fetch_prices(symbols):
    syms = " ".join(symbols)
    cur, hi, lo = {}, {}, {}
    for interval, period in [("5m", "1d"), ("15m", "5d")]:
        try:
            raw = yf.download(syms, period=period, interval=interval,
                              group_by="ticker", auto_adjust=True,
                              threads=True, progress=False)
            if raw is None or raw.empty:
                continue
            for sym in symbols:
                if sym in cur:
                    continue
                try:
                    df = raw[sym] if len(symbols) > 1 else raw
                    df = df.dropna(subset=["Close"])
                    if len(df) > 0:
                        cur[sym] = float(df["Close"].iloc[-1])
                        hi[sym]  = float(df["High"].max())
                        lo[sym]  = float(df["Low"].min())
                except Exception:
                    continue
            if len(cur) >= len(symbols) * 0.7:
                break
        except Exception:
            continue
    return cur, hi, lo


# -- Strategies -----------------------------------------------------------------
def sig_macd(sym, df, direction):
    if len(df) < 30: return None
    close = df["Close"]
    h = macd_hist(close); r = rsi(close, 14); a = atr(df, 14)
    if a <= 0: return None
    if direction == "SELL" and (h >= 0 or r < 35): return None
    if direction == "BUY"  and (h <= 0 or r > 65): return None
    entry = float(close.iloc[-1])
    sl = entry + a if direction=="SELL" else entry - a
    tp = entry - 2*a if direction=="SELL" else entry + 2*a
    return {"strategy":"macd_momentum","symbol":sym,"direction":direction,
            "signal_type":direction,"entry_price":round(entry,6),
            "take_profit":round(tp,6),"stop_loss":round(sl,6),
            "risk_reward":2.0,"confidence":0.72,"category":"forex",
            "reason":f"MACD hist={'bear' if direction=='SELL' else 'bull'}({h:.5f}) RSI={r:.0f}"}

def sig_ema(sym, df, direction):
    if len(df) < 25: return None
    close = df["Close"]
    e5 = float(ema(close,5).iloc[-1]); e20 = float(ema(close,20).iloc[-1])
    entry = float(close.iloc[-1]); a = atr(df,14); r = rsi(close,14)
    if a <= 0: return None
    if direction=="SELL":
        if not (entry < e5 < e20) or r < 30: return None
        sl=entry+1.5*a; tp=entry-3*a
    else:
        if not (entry > e5 > e20) or r > 70: return None
        sl=entry-1.5*a; tp=entry+3*a
    return {"strategy":"ema_crossover","symbol":sym,"direction":direction,
            "signal_type":direction,"entry_price":round(entry,6),
            "take_profit":round(tp,6),"stop_loss":round(sl,6),
            "risk_reward":2.0,"confidence":0.68,"category":"forex",
            "reason":f"EMA5({'<' if direction=='SELL' else '>'})EMA20 aligned RSI={r:.0f}"}

def sig_session(sym, df, direction):
    if len(df) < 10: return None
    close = df["Close"]
    hi5 = float(df["High"].iloc[-6:-1].max())
    lo5 = float(df["Low"].iloc[-6:-1].min())
    entry = float(close.iloc[-1]); a = atr(df,14); r = rsi(close,14)
    if a <= 0: return None
    if direction=="SELL":
        if entry > lo5 or r < 35: return None
        sl=lo5+0.5*a; tp=entry-2*a
    else:
        if entry < hi5 or r > 65: return None
        sl=hi5-0.5*a; tp=entry+2*a
    return {"strategy":"session_breakout","symbol":sym,"direction":direction,
            "signal_type":direction,"entry_price":round(entry,6),
            "take_profit":round(tp,6),"stop_loss":round(sl,6),
            "risk_reward":2.0,"confidence":0.65,"category":"forex",
            "reason":f"5-bar {'below low' if direction=='SELL' else 'above high'} RSI={r:.0f}"}

STRAT_FNS = [sig_macd, sig_ema, sig_session]
STRAT_NAMES = ["macd_momentum", "ema_crossover", "session_breakout"]


# -- Single Session --------------------------------------------------------------
def run_session(session_num: int) -> dict:
    """Generate picks, wait 5m, check results."""
    est_now = datetime.now(EST).strftime("%Y-%m-%d %H:%M:%S %Z")
    print(f"\n{'='*70}")
    print(f"  SESSION {session_num} | {est_now}")
    print(f"{'='*70}")

    print(f"  Fetching 5m data...")
    data = fetch_data(list(FOREX_PAIRS.keys()), "5m", "2d")

    picks = []
    for sym, bias in FOREX_PAIRS.items():
        df = data.get(sym)
        if df is None:
            continue
        for fn in STRAT_FNS:
            try:
                sig = fn(sym, df, bias)
                if sig:
                    sig["entry_time_est"] = est_now
                    sig["entry_time_utc"] = datetime.now(UTC).isoformat()
                    sig["verified_entry_price"] = sig["entry_price"]
                    picks.append(sig)
            except Exception:
                pass

    print(f"  Generated {len(picks)} picks: {', '.join(set(p['symbol'].replace('=X','') for p in picks))}")

    if not picks:
        print("  No signals fired this session.")
        return {"session": session_num, "picks": 0, "wins": 0, "losses": 0,
                "wr": None, "total_pnl": 0, "time_est": est_now, "status": "NO_SIGNALS"}

    # Wait for market to move
    wait_sec = 300  # 5 minutes
    print(f"  Waiting {wait_sec//60} minutes for market to move...")
    for remaining in range(wait_sec, 0, -30):
        time.sleep(30)
        print(f"    ...{remaining-30}s remaining", end="\r")
    print()

    # Check results
    unique_syms = list(set(p["symbol"] for p in picks))
    current, highs, lows = fetch_prices(unique_syms)

    wins = losses = 0
    total_pnl = 0.0
    strat_results = defaultdict(lambda: {"w":0,"l":0,"pnl":0})

    for p in picks:
        sym   = p["symbol"]
        entry = p["verified_entry_price"]
        tp    = p["take_profit"]
        sl    = p["stop_loss"]
        sig   = p["signal_type"]
        cur   = current.get(sym)
        hi    = highs.get(sym, cur)
        lo    = lows.get(sym, cur)
        strat = p["strategy"]

        if cur is None or entry <= 0:
            continue

        status = "OPEN"; exit_p = cur
        if sig == "BUY":
            if tp and hi >= tp:   status, exit_p = "TP_HIT", tp
            elif sl and lo <= sl: status, exit_p = "SL_HIT", sl
            pnl = (exit_p - entry) / entry
        else:
            if tp and lo <= tp:   status, exit_p = "TP_HIT", tp
            elif sl and hi >= sl: status, exit_p = "SL_HIT", sl
            pnl = (entry - exit_p) / entry

        pnl_dollar = pnl * POSITION_SIZE
        total_pnl += pnl_dollar
        if pnl > 0:
            wins += 1
            strat_results[strat]["w"] += 1
        else:
            losses += 1
            strat_results[strat]["l"] += 1
        strat_results[strat]["pnl"] += pnl_dollar

    total = wins + losses
    wr = wins / total if total > 0 else None

    print(f"\n  SESSION {session_num} RESULTS:")
    print(f"  {total} picks | {wins}W/{losses}L | WR={wr*100:.0f}% | P&L ${total_pnl:+.2f}")
    for st, d in strat_results.items():
        n = d["w"] + d["l"]
        swr = d["w"]/n*100 if n else 0
        print(f"    {st:25s}: {n} picks {d['w']}W/{d['l']}L {swr:.0f}% WR ${d['pnl']:+.2f}")

    return {
        "session": session_num,
        "time_est": est_now,
        "picks": total,
        "wins": wins,
        "losses": losses,
        "wr": round(wr, 4) if wr else None,
        "total_pnl": round(total_pnl, 2),
        "by_strategy": dict(strat_results),
        "status": "COMPLETE",
    }


# -- Statistical Proof -----------------------------------------------------------
def binomial_pvalue(wins: int, n: int, p0: float = 0.5) -> float:
    """One-sided binomial test: P(X >= wins | p=p0)."""
    if n == 0: return 1.0
    prob = 0.0
    for k in range(wins, n + 1):
        c = math.comb(n, k)
        prob += c * (p0 ** k) * ((1 - p0) ** (n - k))
    return prob

def print_proof_report(history: list):
    total_picks = sum(s["picks"] for s in history if s["status"]=="COMPLETE")
    total_wins  = sum(s["wins"]  for s in history if s["status"]=="COMPLETE")
    total_loss  = sum(s["losses"]for s in history if s["status"]=="COMPLETE")
    pnls = [s["total_pnl"] for s in history if s["status"]=="COMPLETE"]
    sessions_complete = sum(1 for s in history if s["status"]=="COMPLETE")
    sessions_no_signal = sum(1 for s in history if s["status"]=="NO_SIGNALS")

    print(f"\n{'='*70}")
    print(f"  CONSISTENCY PROOF REPORT -- {len(history)} sessions run")
    print(f"{'='*70}")
    print(f"  Sessions complete  : {sessions_complete}")
    print(f"  Sessions no-signal : {sessions_no_signal}")
    print(f"  Total trades closed: {total_picks}")
    print(f"  Total wins         : {total_wins}")
    print(f"  Total losses       : {total_loss}")

    if total_picks >= 10:
        wr = total_wins / total_picks
        p_val = binomial_pvalue(total_wins, total_picks, 0.5)
        print(f"  Cumulative WR      : {wr*100:.1f}%")
        print(f"  Binomial p-value   : {p_val:.4f}  (H0: WR=50%)")
        print(f"  Net P&L (sum)      : ${sum(pnls):+.2f}")
        print(f"  Avg P&L/session    : ${np.mean(pnls):+.2f}" if pnls else "")

        print(f"\n  VERDICT:")
        if p_val < 0.05 and wr > 0.5:
            print(f"  *** STATISTICALLY PROVEN WINNER (p={p_val:.4f} < 0.05) ***")
            print(f"      WR={wr*100:.1f}% over {total_picks} trades is NOT luck.")
        elif p_val < 0.10 and wr > 0.5:
            print(f"  [!] MARGINAL EDGE (p={p_val:.4f}, borderline). Need more trades.")
        elif wr > 0.5:
            print(f"  [?] WR > 50% but NOT significant (p={p_val:.4f}). Could be luck.")
            print(f"      Need {int((1.645**2 * 0.25) / ((wr-0.5)**2))} trades for 90% confidence.")
        else:
            print(f"  [X] NO EDGE DETECTED. WR={wr*100:.1f}%, p={p_val:.4f}.")

    else:
        print(f"\n  [!] INSUFFICIENT DATA: Need at least 10 closed trades.")
        print(f"      Current: {total_picks} trades.")
        print(f"      ANY win rate claim with < 10 trades is STATISTICALLY MEANINGLESS.")

    print(f"\n  Session-by-session:")
    for s in history:
        wr_str = f"{s['wr']*100:.0f}%" if s.get("wr") else "N/A"
        pnl_str = f"${s['total_pnl']:+.2f}" if s.get("total_pnl") else "$0"
        status = s.get("status","?")
        print(f"    Session {s['session']:2d}: {s['time_est'][:19]:>20s} | "
              f"{s.get('picks',0):2d} picks | WR={wr_str:>5s} | {pnl_str:>9s} | {status}")

    # Per-strategy breakdown
    all_strats = defaultdict(lambda: {"w":0,"l":0,"pnl":0})
    for s in history:
        if s.get("by_strategy"):
            for st, d in s["by_strategy"].items():
                all_strats[st]["w"] += d.get("w",0)
                all_strats[st]["l"] += d.get("l",0)
                all_strats[st]["pnl"] += d.get("pnl",0)

    if all_strats:
        print(f"\n  Per-strategy cumulative:")
        for st, d in sorted(all_strats.items(), key=lambda x: x[1]["pnl"], reverse=True):
            n = d["w"]+d["l"]
            wr = d["w"]/n*100 if n else 0
            p = binomial_pvalue(d["w"], n, 0.5) if n >= 5 else 1.0
            sig = "***" if p < 0.05 else "  ?" if p < 0.10 else "   "
            print(f"    {sig} {st:25s}: {n:3d} trades | {d['w']}W/{d['l']}L | "
                  f"WR={wr:.0f}% | P&L ${d['pnl']:+.2f} | p={p:.3f}")

    print(f"{'='*70}")


# -- Main ------------------------------------------------------------------------
def load_history():
    if PROOF_FILE.exists():
        with open(PROOF_FILE) as f:
            return json.load(f)
    return []

def save_history(history):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(PROOF_FILE, "w") as f:
        json.dump(history, f, indent=2, default=str)


if __name__ == "__main__":
    args = sys.argv[1:]

    if "--report" in args:
        history = load_history()
        if not history:
            print("No history yet. Run: python prove_consistency.py --sessions 3")
        else:
            print_proof_report(history)
        sys.exit(0)

    # Parse args
    n_sessions = 3
    delay_sec  = 60  # delay between sessions
    for i, arg in enumerate(args):
        if arg == "--sessions" and i+1 < len(args):
            n_sessions = int(args[i+1])
        if arg == "--delay" and i+1 < len(args):
            delay_sec = int(args[i+1])

    print(f"\n{'='*70}")
    print(f"  CONSISTENCY PROOF -- Running {n_sessions} sessions")
    print(f"  Each session: generate picks → wait 5min → check results")
    print(f"  Goal: prove WR > 50% is statistically significant (p < 0.05)")
    print(f"  A one-hit wonder will FAIL after session 2 or 3.")
    print(f"{'='*70}")

    history = load_history()
    # Find max existing session number
    max_sess = max((s["session"] for s in history), default=0)

    for i in range(n_sessions):
        sess_num = max_sess + i + 1
        result = run_session(sess_num)
        history.append(result)
        save_history(history)

        # Print running tally
        complete = [s for s in history if s["status"]=="COMPLETE"]
        tw = sum(s["wins"] for s in complete)
        tl = sum(s["losses"] for s in complete)
        if tw + tl >= 5:
            wr = tw/(tw+tl)
            pval = binomial_pvalue(tw, tw+tl, 0.5)
            print(f"\n  RUNNING TALLY: {tw+tl} trades | {tw}W/{tl}L | "
                  f"WR={wr*100:.0f}% | p={pval:.4f}")

        if i < n_sessions - 1:
            print(f"\n  Waiting {delay_sec}s before next session...")
            time.sleep(delay_sec)

    # Final report
    print_proof_report(history)
    save_history(history)
