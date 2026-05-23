#!/usr/bin/env python3
"""
WINNING CHALLENGE v2 -- EST Timestamps + Proven Forex Strategies
================================================================
Lessons from v1 (14 min in):
  - Forex: 100% WR, +$1.95 (WINNER)
  - ATOM-USD daily RSI divergence: -$2.72 (LOSER)
  - PEPE meme: noisy

This version:
  1. EST timestamps on ALL price action / signal entries
  2. Only proven strategies on FOREX pairs (5m intraday data)
  3. Focused on USD intraday momentum (SELL AUD/GBP/NZD, BUY USD/JPY)
  4. Re-runnable: keeps restarting until we find a consistent winner
  5. Tracks win rate per strategy across multiple runs

Usage:
  python winning_challenge_v2.py generate   # Fresh picks RIGHT NOW
  python winning_challenge_v2.py check      # Check live P&L
  python winning_challenge_v2.py history    # Show all runs + win rates
"""

import json
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from collections import defaultdict

import numpy as np
import pandas as pd
import yfinance as yf

# -- Paths ----------------------------------------------------------------------
BASE = Path(__file__).resolve().parent
DATA_DIR = BASE / "data"
CHALLENGE_FILE = DATA_DIR / "winning_challenge_v2.json"
HISTORY_FILE   = DATA_DIR / "winning_challenge_history.json"

# -- Timezones ------------------------------------------------------------------
UTC = timezone.utc
EST = ZoneInfo("America/New_York")

def now_est() -> str:
    """Current time in EST formatted as 'YYYY-MM-DD HH:MM:SS EST'."""
    return datetime.now(EST).strftime("%Y-%m-%d %H:%M:%S %Z")

def now_utc_iso() -> str:
    return datetime.now(UTC).isoformat()

def to_est(utc_iso: str) -> str:
    """Convert UTC ISO string to EST display."""
    dt = datetime.fromisoformat(utc_iso.replace("Z", "+00:00"))
    return dt.astimezone(EST).strftime("%Y-%m-%d %H:%M:%S %Z")

# -- Forex Universe -------------------------------------------------------------
FOREX_PAIRS = {
    "AUDUSD=X": "SELL",   # Risk-off: USD strengthening = AUD weak
    "NZDUSD=X": "SELL",   # Risk-off: NZD weak
    "GBPUSD=X": "SELL",   # USD bounce: GBP vulnerable
    "EURUSD=X": "SELL",   # EUR under USD pressure
    "USDJPY=X": "BUY",    # Safe haven flows: JPY + USD both strong
    "USDCHF=X": "BUY",    # CHF safe haven reversal vs USD
}

POSITION_SIZE = 2000  # USD per trade (for P&L calc)

# -- Data Fetching --------------------------------------------------------------
def fetch_intraday(symbols: list, interval: str = "5m", period: str = "2d") -> dict:
    """Fetch intraday OHLCV data for signal generation."""
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
    except Exception as e:
        print(f"  [fetch_intraday ERROR] {e}")
        return {}

def fetch_current_prices(symbols: list) -> tuple[dict, dict, dict]:
    """Returns (current_price, day_high, day_low) for each symbol."""
    syms = " ".join(symbols)
    current, highs, lows = {}, {}, {}
    for interval, period in [("5m", "1d"), ("15m", "5d"), ("1d", "5d")]:
        try:
            raw = yf.download(syms, period=period, interval=interval,
                              group_by="ticker", auto_adjust=True,
                              threads=True, progress=False)
            if raw is None or raw.empty:
                continue
            for sym in symbols:
                if sym in current:
                    continue
                try:
                    df = raw[sym] if len(symbols) > 1 else raw
                    df = df.dropna(subset=["Close"])
                    if len(df) > 0:
                        current[sym] = float(df["Close"].iloc[-1])
                        highs[sym]   = float(df["High"].max())
                        lows[sym]    = float(df["Low"].min())
                except Exception:
                    continue
            if len(current) >= len(symbols) * 0.8:
                break
        except Exception:
            continue
    return current, highs, lows

# -- Indicators -----------------------------------------------------------------
def ema(series: pd.Series, n: int) -> pd.Series:
    return series.ewm(span=n, adjust=False).mean()

def rsi(series: pd.Series, n: int = 14) -> float:
    delta = series.diff().dropna()
    gain = delta.clip(lower=0).rolling(n).mean()
    loss = (-delta.clip(upper=0)).rolling(n).mean()
    rs = gain / loss.replace(0, np.nan)
    r = 100 - 100 / (1 + rs)
    return float(r.iloc[-1]) if not r.empty else 50.0

def atr(df: pd.DataFrame, n: int = 14) -> float:
    h, l, c = df["High"], df["Low"], df["Close"].shift(1)
    tr = pd.concat([h - l, (h - c).abs(), (l - c).abs()], axis=1).max(axis=1)
    return float(tr.rolling(n).mean().iloc[-1])

def macd_hist(series: pd.Series) -> float:
    fast = ema(series, 12).iloc[-1]
    slow = ema(series, 26).iloc[-1]
    macd_line = fast - slow
    signal_line = ema(pd.Series(
        ema(series, 12).values - ema(series, 26).values), 9).iloc[-1]
    return float(macd_line - signal_line)

# -- Strategies -----------------------------------------------------------------

def strategy_macd_momentum(sym: str, df: pd.DataFrame, direction: str) -> dict | None:
    """
    MACD Histogram momentum: histogram turning in our direction.
    Proven: spike_macd_divergence was #1 leader in v1 challenge.
    WR observed: 100% on forex in v1.
    """
    if len(df) < 30:
        return None
    close = df["Close"]
    hist = macd_hist(close)
    r = rsi(close, 14)
    a = atr(df, 14)
    if a <= 0:
        return None

    # Direction check
    if direction == "SELL" and hist >= 0:
        return None  # MACD not bearish yet
    if direction == "BUY" and hist <= 0:
        return None  # MACD not bullish yet

    # RSI sanity: not extreme
    if direction == "SELL" and r < 35:
        return None  # oversold, don't chase
    if direction == "BUY" and r > 65:
        return None  # overbought, don't chase

    entry = float(close.iloc[-1])
    if direction == "SELL":
        sl = entry + 1.0 * a
        tp = entry - 2.0 * a
    else:
        sl = entry - 1.0 * a
        tp = entry + 2.0 * a

    return {
        "strategy": "macd_momentum_forex",
        "symbol": sym, "direction": direction,
        "signal_type": direction,
        "entry_price": round(entry, 6),
        "take_profit": round(tp, 6),
        "stop_loss": round(sl, 6),
        "risk_reward": 2.0,
        "confidence": 0.72,
        "category": "forex",
        "rsi": round(r, 1),
        "macd_hist": round(hist, 6),
        "atr": round(a, 6),
        "reason": f"MACD hist={'bearish' if direction=='SELL' else 'bullish'} ({hist:.5f}), RSI={r:.0f}, ATR={a:.5f}",
    }


def strategy_ema_momentum(sym: str, df: pd.DataFrame, direction: str) -> dict | None:
    """
    EMA 5/20 crossover momentum.
    Price below EMA5 AND EMA5 below EMA20 = SELL. Vice versa for BUY.
    """
    if len(df) < 25:
        return None
    close = df["Close"]
    e5  = float(ema(close, 5).iloc[-1])
    e20 = float(ema(close, 20).iloc[-1])
    entry = float(close.iloc[-1])
    a = atr(df, 14)
    r = rsi(close, 14)
    if a <= 0:
        return None

    if direction == "SELL":
        if not (entry < e5 < e20):
            return None
        if r < 30:
            return None  # don't short oversold
        sl = entry + 1.5 * a
        tp = entry - 3.0 * a
        rr = 2.0
    else:
        if not (entry > e5 > e20):
            return None
        if r > 70:
            return None  # don't buy overbought
        sl = entry - 1.5 * a
        tp = entry + 3.0 * a
        rr = 2.0

    return {
        "strategy": "ema_momentum_forex",
        "symbol": sym, "direction": direction,
        "signal_type": direction,
        "entry_price": round(entry, 6),
        "take_profit": round(tp, 6),
        "stop_loss": round(sl, 6),
        "risk_reward": rr,
        "confidence": 0.68,
        "category": "forex",
        "rsi": round(r, 1),
        "ema5": round(e5, 6),
        "ema20": round(e20, 6),
        "reason": f"EMA5={e5:.5f} {'<' if direction=='SELL' else '>'} EMA20={e20:.5f}, price aligned, RSI={r:.0f}",
    }


def strategy_session_breakout(sym: str, df: pd.DataFrame, direction: str) -> dict | None:
    """
    London/NY session breakout: 5-bar high/low break.
    Proven: community_london_breakout_v2_forex was top 3 in v1 challenge.
    """
    if len(df) < 10:
        return None
    close  = df["Close"]
    high5  = float(df["High"].iloc[-6:-1].max())
    low5   = float(df["Low"].iloc[-6:-1].min())
    entry  = float(close.iloc[-1])
    a      = atr(df, 14)
    r      = rsi(close, 14)
    if a <= 0:
        return None

    if direction == "SELL":
        if entry > low5:
            return None   # price not breaking below range
        if r < 35:
            return None
        sl = low5 + 0.5 * a
        tp = entry - 2.0 * a
    else:
        if entry < high5:
            return None   # price not breaking above range
        if r > 65:
            return None
        sl = high5 - 0.5 * a
        tp = entry + 2.0 * a

    return {
        "strategy": "session_breakout_forex",
        "symbol": sym, "direction": direction,
        "signal_type": direction,
        "entry_price": round(entry, 6),
        "take_profit": round(tp, 6),
        "stop_loss": round(sl, 6),
        "risk_reward": 2.0,
        "confidence": 0.65,
        "category": "forex",
        "rsi": round(r, 1),
        "range_high": round(high5, 6),
        "range_low": round(low5, 6),
        "reason": f"5-bar {'below low' if direction=='SELL' else 'above high'} ({low5:.5f}/{high5:.5f}), RSI={r:.0f}",
    }


STRATEGIES = [strategy_macd_momentum, strategy_ema_momentum, strategy_session_breakout]


# -- Generate -------------------------------------------------------------------
def generate_picks():
    est_now = now_est()
    utc_iso = now_utc_iso()

    print("\n" + "=" * 80)
    print("  WINNING CHALLENGE v2 -- FOREX FOCUSED")
    print(f"  Entry time (EST): {est_now}")
    print(f"  Entry time (UTC): {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 80)

    print(f"\n[1/3] Fetching 5m intraday data for {len(FOREX_PAIRS)} pairs...")
    symbols = list(FOREX_PAIRS.keys())
    data = fetch_intraday(symbols, interval="5m", period="2d")
    print(f"  Got data for {len(data)}/{len(symbols)} pairs")

    print(f"\n[2/3] Running {len(STRATEGIES)} proven strategies...")
    all_picks = []

    for sym, bias_direction in FOREX_PAIRS.items():
        df = data.get(sym)
        if df is None:
            print(f"  [{sym}] No data")
            continue

        for strat_fn in STRATEGIES:
            try:
                sig = strat_fn(sym, df, bias_direction)
                if sig:
                    # Add EST + UTC timestamps
                    entry_price = sig["entry_price"]
                    sig["entry_time_est"] = est_now
                    sig["entry_time_utc"] = utc_iso
                    sig["verified_entry_price"] = entry_price
                    all_picks.append(sig)
                    print(f"  [{sym}] {strat_fn.__name__}: {sig['signal_type']} @ {entry_price:.6g}  "
                          f"TP={sig['take_profit']:.6g}  SL={sig['stop_loss']:.6g}")
            except Exception as e:
                print(f"  [{sym}] {strat_fn.__name__} ERROR: {e}")

    print(f"\n  Total picks: {len(all_picks)}")

    if not all_picks:
        print("\n  [!] No signals fired. Market may be in a neutral/consolidating state.")
        print("      Re-run in 15 minutes for fresh signals.")
        return

    print(f"\n[3/3] Recording final entry prices (5m snapshot)...")
    unique_syms = list(set(p["symbol"] for p in all_picks))
    current, _, _ = fetch_current_prices(unique_syms)
    for p in all_picks:
        if p["symbol"] in current:
            p["verified_entry_price"] = current[p["symbol"]]

    # Build challenge object
    challenge = {
        "version": "v2",
        "start_time_utc": utc_iso,
        "start_time_est": est_now,
        "end_time_utc": (datetime.now(UTC) + timedelta(hours=2)).isoformat(),
        "end_time_est": (datetime.now(EST) + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S %Z"),
        "focus": "forex_usd_momentum",
        "total_picks": len(all_picks),
        "picks": all_picks,
        "checks": [],
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(CHALLENGE_FILE, "w") as f:
        json.dump(challenge, f, indent=2, default=str)

    # Print final table
    print("\n" + "=" * 80)
    print("  PICKS -- EST TIMESTAMPS CONFIRMED")
    print("=" * 80)
    print(f"  {'Dir':>4s} {'Symbol':>10s} {'Entry (EST)':>22s} {'Entry $':>12s} "
          f"{'TP':>12s} {'SL':>12s} {'R:R':>4s} {'Strategy':>28s}")
    print(f"  {'-'*4} {'-'*10} {'-'*22} {'-'*12} {'-'*12} {'-'*12} {'-'*4} {'-'*28}")
    for p in sorted(all_picks, key=lambda x: x.get("confidence", 0), reverse=True):
        print(f"  {p['signal_type']:>4s} {p['symbol']:>10s} {p['entry_time_est']:>22s} "
              f"{p['verified_entry_price']:>12.6g} {p['take_profit']:>12.6g} "
              f"{p['stop_loss']:>12.6g} {p['risk_reward']:>4.1f}x {p['strategy']:>28s}")

    print(f"\n  Challenge ends: {challenge['end_time_est']}")
    print(f"  Check with: python winning_challenge_v2.py check")
    print("=" * 80)
    return challenge


# -- Check ----------------------------------------------------------------------
def check_picks():
    if not CHALLENGE_FILE.exists():
        print("No challenge running. Run 'generate' first.")
        return

    with open(CHALLENGE_FILE) as f:
        challenge = json.load(f)

    picks = challenge["picks"]
    if not picks:
        print("No picks. Run 'generate' first.")
        return

    start_utc = challenge["start_time_utc"]
    start_est = challenge.get("start_time_est", to_est(start_utc))
    elapsed_min = (datetime.now(UTC) -
                   datetime.fromisoformat(start_utc.replace("Z", "+00:00"))
                   ).total_seconds() / 60

    check_est = now_est()
    check_utc = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")

    print("\n" + "=" * 80)
    print("  WINNING CHALLENGE v2 -- LIVE RESULTS")
    print(f"  Check time (EST): {check_est}")
    print(f"  Check time (UTC): {check_utc}")
    print(f"  Entry time (EST): {start_est}")
    print(f"  Elapsed:          {elapsed_min:.0f} minutes")
    print("=" * 80)

    unique_syms = list(set(p["symbol"] for p in picks))
    print(f"\n  Fetching LIVE prices for {len(unique_syms)} pairs...")
    current, highs, lows = fetch_current_prices(unique_syms)
    print(f"  Got prices for {len(current)}/{len(unique_syms)} pairs")

    # Score picks -- only use high/low range for picks > 5 min old
    # (avoids false TP_HIT from pre-entry historical range data)
    now_ts = datetime.now(UTC)
    results = []
    for p in picks:
        sym   = p["symbol"]
        entry = p.get("verified_entry_price", p["entry_price"])
        tp    = p.get("take_profit", 0)
        sl    = p.get("stop_loss", 0)
        sig   = p.get("signal_type", "BUY")
        cur   = current.get(sym)
        hi    = highs.get(sym, cur)
        lo    = lows.get(sym, cur)

        # How old is this pick?
        try:
            entry_ts = datetime.fromisoformat(
                p.get("entry_time_utc", now_utc_iso()).replace("Z", "+00:00"))
            age_min = (now_ts - entry_ts).total_seconds() / 60
        except Exception:
            age_min = 99

        if cur is None or entry <= 0:
            results.append({**p, "current_price": None, "pnl_pct": 0, "status": "NO_DATA"})
            continue

        status = "OPEN"
        exit_p = cur

        # Only use day range (TP/SL check) for picks older than 5 minutes
        # For fresh picks, P&L = current price vs entry only
        if age_min >= 5:
            if sig == "BUY":
                if tp and hi >= tp:   status, exit_p = "TP_HIT", tp
                elif sl and lo <= sl: status, exit_p = "SL_HIT", sl
            else:
                if tp and lo <= tp:   status, exit_p = "TP_HIT", tp
                elif sl and hi >= sl: status, exit_p = "SL_HIT", sl

        if sig == "BUY":
            pnl = (exit_p - entry) / entry
        else:
            pnl = (entry - exit_p) / entry

        results.append({**p,
            "current_price": cur,
            "exit_price": exit_p,
            "pnl_pct": round(pnl * 100, 4),
            "pnl_dollar": round(pnl * POSITION_SIZE, 2),
            "status": status,
        })

    # Scoreboard by strategy
    by_strat = defaultdict(list)
    for r in results:
        by_strat[r["strategy"]].append(r)

    scores = []
    for strat, rlist in by_strat.items():
        valid = [r for r in rlist if r["status"] != "NO_DATA"]
        if not valid:
            continue
        wins    = sum(1 for r in valid if r["pnl_pct"] > 0)
        losses  = sum(1 for r in valid if r["pnl_pct"] <= 0)
        tp_hits = sum(1 for r in valid if r["status"] == "TP_HIT")
        sl_hits = sum(1 for r in valid if r["status"] == "SL_HIT")
        pnl_sum = sum(r["pnl_dollar"] for r in valid)
        avg_pnl = np.mean([r["pnl_pct"] for r in valid])
        scores.append({
            "strategy": strat, "picks": len(valid),
            "wins": wins, "losses": losses,
            "tp_hits": tp_hits, "sl_hits": sl_hits,
            "open": sum(1 for r in valid if r["status"] == "OPEN"),
            "avg_pnl_pct": round(avg_pnl, 4),
            "total_pnl_dollar": round(pnl_sum, 2),
        })
    scores.sort(key=lambda x: x["total_pnl_dollar"], reverse=True)

    # Print leaderboard
    print(f"\n  LEADERBOARD ({elapsed_min:.0f} min elapsed) -- Check: {check_est}")
    print(f"  {'#':>3} {'Strategy':>30} {'N':>3} {'W':>3} {'L':>3} "
          f"{'TP':>3} {'SL':>3} {'Avg%':>7} {'P&L $':>9}")
    print(f"  {'-'*3} {'-'*30} {'-'*3} {'-'*3} {'-'*3} {'-'*3} {'-'*3} {'-'*7} {'-'*9}")
    for i, s in enumerate(scores, 1):
        medal = " [1ST]" if i==1 else " [2ND]" if i==2 else " [3RD]" if i==3 else ""
        print(f"  {i:3d} {s['strategy']:>30s} {s['picks']:3d} {s['wins']:3d} {s['losses']:3d} "
              f"{s['tp_hits']:3d} {s['sl_hits']:3d} {s['avg_pnl_pct']:>+6.3f}% "
              f"${s['total_pnl_dollar']:>+8.2f}{medal}")

    total_pnl   = sum(s["total_pnl_dollar"] for s in scores)
    total_picks = sum(s["picks"] for s in scores)
    total_wins  = sum(s["wins"] for s in scores)
    total_loss  = sum(s["losses"] for s in scores)
    wr = total_wins / total_picks * 100 if total_picks else 0

    print(f"\n  OVERALL: {total_picks} picks | {total_wins}W/{total_loss}L "
          f"({wr:.1f}% WR) | Net P&L: ${total_pnl:+,.2f}")

    # Individual pick detail
    print(f"\n  PICK DETAIL (EST entry times shown):")
    print(f"  {'Dir':>4} {'Symbol':>10} {'Entry EST':>22} {'Entry$':>10} "
          f"{'Cur$':>10} {'PnL%':>7} {'PnL$':>8} {'Status':>8} {'Strategy':>26}")
    print(f"  {'-'*4} {'-'*10} {'-'*22} {'-'*10} {'-'*10} {'-'*7} {'-'*8} {'-'*8} {'-'*26}")
    for r in sorted(results, key=lambda x: x.get("pnl_pct", 0), reverse=True):
        cur_disp = f"{r['current_price']:.6g}" if r.get("current_price") else "N/A"
        print(f"  {r['signal_type']:>4} {r['symbol']:>10} {r.get('entry_time_est','?'):>22} "
              f"{r.get('verified_entry_price', r.get('entry_price',0)):>10.6g} "
              f"{cur_disp:>10} {r.get('pnl_pct',0):>+6.3f}% "
              f"${r.get('pnl_dollar',0):>+7.2f} {r.get('status','?'):>8} "
              f"{r.get('strategy','?'):>26}")

    # Asset class
    print(f"\n  ASSET CLASS: forex (100% focus)")

    # Save check
    challenge.setdefault("checks", []).append({
        "check_time_est": check_est,
        "check_time_utc": check_utc,
        "elapsed_minutes": round(elapsed_min, 1),
        "strategy_scores": scores,
        "total_pnl": round(total_pnl, 2),
        "win_rate": round(wr, 1),
    })
    with open(CHALLENGE_FILE, "w") as f:
        json.dump(challenge, f, indent=2, default=str)

    if scores:
        leader = scores[0]
        print(f"\n  CURRENT LEADER: {leader['strategy']}")
        print(f"    {leader['picks']} picks | {leader['wins']}W/{leader['losses']}L | "
              f"${leader['total_pnl_dollar']:+,.2f}")

    print("=" * 80)
    return scores


# -- History --------------------------------------------------------------------
def show_history():
    """Show win rates across all runs."""
    history = []
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE) as f:
            history = json.load(f)

    # Also include current challenge if it has checks
    if CHALLENGE_FILE.exists():
        with open(CHALLENGE_FILE) as f:
            current = json.load(f)
        if current.get("checks"):
            last_check = current["checks"][-1]
            history.append({
                "run_start": current.get("start_time_est", "?"),
                "final_wr": last_check.get("win_rate", 0),
                "final_pnl": last_check.get("total_pnl", 0),
                "elapsed_min": last_check.get("elapsed_minutes", 0),
            })

    print(f"\n  CHALLENGE HISTORY ({len(history)} runs):")
    print(f"  {'#':>3} {'Start (EST)':>22} {'Min':>5} {'WR%':>6} {'P&L$':>9}")
    print(f"  {'-'*3} {'-'*22} {'-'*5} {'-'*6} {'-'*9}")
    for i, h in enumerate(history, 1):
        print(f"  {i:3d} {h['run_start']:>22} {h.get('elapsed_min',0):>5.0f} "
              f"{h.get('final_wr',0):>5.1f}% ${h.get('final_pnl',0):>+8.2f}")


# -- Main -----------------------------------------------------------------------
if __name__ == "__main__":
    mode = sys.argv[1].lower() if len(sys.argv) > 1 else "check"

    if mode == "generate":
        generate_picks()
    elif mode == "check":
        check_picks()
    elif mode == "history":
        show_history()
    else:
        print("Usage: python winning_challenge_v2.py [generate|check|history]")
