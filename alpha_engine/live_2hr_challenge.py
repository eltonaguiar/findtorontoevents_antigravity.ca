#!/usr/bin/env python3
"""
ALPHA ENGINE â€” 2-HOUR LIVE CHALLENGE
======================================
Every strategy generates picks RIGHT NOW against live market data.
Then we check real prices at intervals to see who's winning.

This is the real deal:
1. Fetch live data for all 51 symbols
2. Run ALL strategies (original + community + spike)
3. Record every signal with entry price, TP, SL
4. Save to JSON and print scoreboard
5. Re-run this script to CHECK results against current prices

Usage:
  python live_2hr_challenge.py generate    # Generate all picks NOW
  python live_2hr_challenge.py check       # Check picks vs current prices
"""

import json
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import defaultdict

import numpy as np
import pandas as pd
import yfinance as yf

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import ALL_SYMBOLS, CRYPTO_SYMBOLS, FOREX_SYMBOLS, EQUITY_SYMBOLS, DATA_DIR

CHALLENGE_FILE = DATA_DIR / "live_2hr_challenge.json"


def fetch_live_data():
    """Fetch latest daily data for all symbols."""
    symbols = list(ALL_SYMBOLS.keys())
    tickers = " ".join(symbols)
    print(f"  Fetching {len(symbols)} symbols...")

    raw = yf.download(tickers, period="1y", interval="1d",
                      group_by="ticker", auto_adjust=True,
                      threads=True, progress=False)
    data = {}
    for sym in symbols:
        try:
            if len(symbols) == 1:
                df = raw
            else:
                df = raw[sym] if sym in raw.columns.get_level_values(0) else None
            if df is not None and not df.empty:
                df = df.dropna(subset=["Close"])
                if len(df) >= 20:
                    data[sym] = df
        except Exception:
            continue
    print(f"  Got {len(data)}/{len(symbols)} symbols")
    return data


def generate_picks(duration_hours=2):
    """Generate picks from ALL strategies and save them."""
    print("\n" + "=" * 80)
    print(f"  {duration_hours}-HOUR LIVE CHALLENGE - GENERATING PICKS")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 80)

    print("\n[1/3] Fetching live market data...")
    data = fetch_live_data()

    print("\n[2/3] Running ALL strategies...")

    # Import everything
    from crypto_strategies import CRYPTO_STRATEGIES
    from forex_strategies import FOREX_STRATEGIES
    from equity_strategies import EQUITY_STRATEGIES
    from strategy_guard import filter_strategies, log_filtered_strategies

    all_strategies = {
        **CRYPTO_STRATEGIES,
        **FOREX_STRATEGIES,
        **EQUITY_STRATEGIES,
    }

    # Filter out disabled strategies (emergency triage)
    all_strategies, removed = filter_strategies(all_strategies)
    log_filtered_strategies(removed)

    # De-duplicate (spike strategies are in crypto already)
    print(f"  Total strategies loaded: {len(all_strategies)}")

    all_picks = []
    import inspect

    for name, func in all_strategies.items():
        try:
            sig = inspect.signature(func)
            if "context" in sig.parameters:
                signals = func(data, context={})
            else:
                signals = func(data)
        except Exception as e:
            print(f"  [{name}] ERROR: {e}")
            continue

        if signals:
            for s in signals:
                s["strategy"] = name
                s["challenge_entry_time"] = datetime.now(timezone.utc).isoformat()
            all_picks.extend(signals)
            print(f"  [{name}] -> {len(signals)} signal(s)")

    print(f"\n  Total signals generated: {len(all_picks)}")

    # Also fetch current real-time prices for entry verification
    print("\n[3/3] Recording entry prices...")
    unique_syms = list(set(p["symbol"] for p in all_picks))
    if unique_syms:
        tickers = " ".join(unique_syms)
        try:
            snap = yf.download(tickers, period="1d", interval="1d",
                               group_by="ticker", auto_adjust=True,
                               threads=True, progress=False)
            for p in all_picks:
                sym = p["symbol"]
                try:
                    if len(unique_syms) == 1:
                        cur = float(snap["Close"].iloc[-1])
                    else:
                        cur = float(snap[sym]["Close"].iloc[-1]) if sym in snap.columns.get_level_values(0) else p["entry_price"]
                    p["verified_entry_price"] = cur
                except Exception:
                    p["verified_entry_price"] = p["entry_price"]
        except Exception:
            for p in all_picks:
                p["verified_entry_price"] = p["entry_price"]

    # Save
    challenge = {
        "start_time": datetime.now(timezone.utc).isoformat(),
        "end_time": (datetime.now(timezone.utc) + timedelta(hours=duration_hours)).isoformat(),
        "duration_hours": duration_hours,
        "total_picks": len(all_picks),
        "strategies_count": len(set(p["strategy"] for p in all_picks)),
        "symbols_count": len(set(p["symbol"] for p in all_picks)),
        "picks": all_picks,
        "checks": [],
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(CHALLENGE_FILE, "w") as f:
        json.dump(challenge, f, indent=2, default=str)

    # Print scoreboard
    print("\n" + "=" * 80)
    print("  CHALLENGE PICKS â€” LIVE SCOREBOARD")
    print("=" * 80)

    by_strat = defaultdict(list)
    for p in all_picks:
        by_strat[p["strategy"]].append(p)

    print(f"\n  {'Strategy':35s} {'Picks':>5s} {'Types':>12s} {'Symbols':>20s}")
    print(f"  {'-'*35} {'-'*5} {'-'*12} {'-'*20}")
    for strat in sorted(by_strat.keys()):
        picks = by_strat[strat]
        types = set(p.get("signal_type", "?") for p in picks)
        syms = [p["symbol"].replace("-USD", "").replace("=X", "") for p in picks]
        sym_str = ", ".join(syms[:4])
        if len(syms) > 4:
            sym_str += f" +{len(syms)-4}"
        print(f"  {strat:35s} {len(picks):4d} {'/'.join(types):>12s} {sym_str:>20s}")

    # Print all picks detail
    print(f"\n  ALL PICKS DETAIL ({len(all_picks)} total):")
    print(f"  {'Signal':>5s} {'Symbol':>16s} {'Entry':>12s} {'TP':>12s} {'SL':>12s} "
          f"{'R:R':>5s} {'Strategy':>30s}")
    print(f"  {'-'*5} {'-'*16} {'-'*12} {'-'*12} {'-'*12} {'-'*5} {'-'*30}")
    for p in sorted(all_picks, key=lambda x: x.get("confidence", 0), reverse=True):
        sig = p.get("signal_type", "BUY")
        sym = p["symbol"]
        entry = p.get("verified_entry_price", p["entry_price"])
        tp = p.get("take_profit", 0)
        sl = p.get("stop_loss", 0)
        rr = p.get("risk_reward", 0)
        strat = p["strategy"]
        print(f"  {sig:>5s} {sym:>16s} {entry:>12.6g} {tp:>12.6g} {sl:>12.6g} "
              f"{rr:>4.1f}x {strat:>30s}")

    print(f"\n  Challenge started! Check back with: python live_2hr_challenge.py check")
    print(f"  End time: {challenge['end_time']}")
    print("=" * 80)

    return challenge


def check_picks():
    """Check all challenge picks against current prices."""
    if not CHALLENGE_FILE.exists():
        print("No challenge running. Run 'generate' first.")
        return

    with open(CHALLENGE_FILE) as f:
        challenge = json.load(f)

    picks = challenge["picks"]
    if not picks:
        print("No picks in challenge.")
        return

    start_time = challenge["start_time"]
    elapsed_min = (datetime.now(timezone.utc) -
                   datetime.fromisoformat(start_time.replace("Z", "+00:00"))).total_seconds() / 60

    print("\n" + "=" * 80)
    print("  2-HOUR LIVE CHALLENGE â€” RESULTS CHECK")
    print(f"  Started: {start_time}")
    print(f"  Elapsed: {elapsed_min:.0f} minutes")
    print("=" * 80)

    # Fetch current prices using INTRADAY data for real-time movement
    unique_syms = list(set(p["symbol"] for p in picks))
    tickers = " ".join(unique_syms)

    print(f"\n  Fetching REAL-TIME prices for {len(unique_syms)} symbols...")
    current_prices = {}
    highs = {}
    lows = {}

    # Try 5-minute intraday first (most granular), fall back to daily
    for interval, period in [("5m", "1d"), ("15m", "5d"), ("1d", "5d")]:
        try:
            raw = yf.download(tickers, period=period, interval=interval,
                              group_by="ticker", auto_adjust=True,
                              threads=True, progress=False)
            if raw is not None and not raw.empty:
                for sym in unique_syms:
                    if sym in current_prices:
                        continue
                    try:
                        if len(unique_syms) == 1:
                            df = raw
                        else:
                            df = raw[sym] if sym in raw.columns.get_level_values(0) else None
                        if df is not None and not df.empty:
                            df = df.dropna(subset=["Close"])
                            if len(df) > 0:
                                current_prices[sym] = float(df["Close"].iloc[-1])
                                # For TP/SL tracking, use the MAX high and MIN low
                                # since the challenge started
                                highs[sym] = float(df["High"].max())
                                lows[sym] = float(df["Low"].min())
                    except Exception:
                        continue
                if len(current_prices) >= len(unique_syms) * 0.8:
                    print(f"  Got prices via {interval} interval")
                    break
        except Exception:
            continue

    print(f"  Got prices for {len(current_prices)}/{len(unique_syms)} symbols")

    # Score each pick
    results = []
    for p in picks:
        sym = p["symbol"]
        entry = p.get("verified_entry_price", p["entry_price"])
        tp = p.get("take_profit", 0)
        sl = p.get("stop_loss", 0)
        sig_type = p.get("signal_type", "BUY")
        strat = p["strategy"]
        current = current_prices.get(sym)
        day_high = highs.get(sym, current)
        day_low = lows.get(sym, current)

        if current is None or not np.isfinite(entry) or entry <= 0:
            results.append({**p, "current_price": current, "pnl_pct": float('nan'), "status": "NO_DATA"})
            continue

        # Check TP/SL hit
        status = "OPEN"
        exit_price = current

        if sig_type == "BUY":
            if tp and day_high >= tp:
                status = "TP_HIT"
                exit_price = tp
            elif sl and day_low <= sl:
                status = "SL_HIT"
                exit_price = sl
            pnl = (exit_price - entry) / entry
        else:
            if tp and day_low <= tp:
                status = "TP_HIT"
                exit_price = tp
            elif sl and day_high >= sl:
                status = "SL_HIT"
                exit_price = sl
            pnl = (entry - exit_price) / entry

        results.append({
            **p,
            "current_price": current,
            "day_high": day_high,
            "day_low": day_low,
            "exit_price": exit_price,
            "pnl_pct": round(pnl * 100, 3),
            "pnl_dollar": round(pnl * 2000, 2),
            "status": status,
        })

    # Strategy scoreboard
    by_strat = defaultdict(list)
    for r in results:
        by_strat[r["strategy"]].append(r)

    strat_scores = []
    for strat, strat_results in by_strat.items():
        valid = [r for r in strat_results if r["status"] != "NO_DATA"]
        if not valid:
            continue
        pnls = [r["pnl_pct"] for r in valid]
        wins = sum(1 for p in pnls if p > 0)
        losses = sum(1 for p in pnls if p <= 0)
        total_pnl = sum(r["pnl_dollar"] for r in valid)
        tp_hits = sum(1 for r in valid if r["status"] == "TP_HIT")
        sl_hits = sum(1 for r in valid if r["status"] == "SL_HIT")
        still_open = sum(1 for r in valid if r["status"] == "OPEN")
        avg_pnl = np.mean(pnls) if pnls else 0

        strat_scores.append({
            "strategy": strat,
            "picks": len(valid),
            "winning": wins,
            "losing": losses,
            "tp_hits": tp_hits,
            "sl_hits": sl_hits,
            "open": still_open,
            "avg_pnl_pct": round(avg_pnl, 3),
            "total_pnl_dollar": round(total_pnl, 2),
        })

    # Sort by total P&L
    strat_scores.sort(key=lambda x: x["total_pnl_dollar"], reverse=True)

    # Print scoreboard
    print(f"\n  STRATEGY LEADERBOARD ({elapsed_min:.0f} min elapsed):")
    print(f"  {'#':>3s} {'Strategy':>35s} {'Picks':>5s} {'W':>3s} {'L':>3s} "
          f"{'TP':>3s} {'SL':>3s} {'Open':>4s} {'AvgPnL%':>8s} {'P&L$':>10s}")
    print(f"  {'-'*3} {'-'*35} {'-'*5} {'-'*3} {'-'*3} "
          f"{'-'*3} {'-'*3} {'-'*4} {'-'*8} {'-'*10}")

    for i, s in enumerate(strat_scores, 1):
        medal = ""
        if i == 1:
            medal = " [1ST]"
        elif i == 2:
            medal = " [2ND]"
        elif i == 3:
            medal = " [3RD]"
        print(f"  {i:>3d} {s['strategy']:>35s} {s['picks']:>4d} {s['winning']:>3d} {s['losing']:>3d} "
              f"{s['tp_hits']:>3d} {s['sl_hits']:>3d} {s['open']:>4d} "
              f"{s['avg_pnl_pct']:>+7.2f}% ${s['total_pnl_dollar']:>+9.2f}{medal}")

    # Overall
    all_pnl = sum(s["total_pnl_dollar"] for s in strat_scores if np.isfinite(s["total_pnl_dollar"]))
    all_picks = sum(s["picks"] for s in strat_scores)
    all_wins = sum(s["winning"] for s in strat_scores)
    all_losses = sum(s["losing"] for s in strat_scores)
    wr = all_wins / all_picks * 100 if all_picks > 0 else 0

    nan_count = sum(1 for r in results if r.get("status") == "NO_DATA")
    nan_note = f" (excl. {nan_count} NaN)" if nan_count > 0 else ""
    print(f"\n  OVERALL: {all_picks} picks | {all_wins}W/{all_losses}L ({wr:.1f}% WR) | "
          f"P&L: ${all_pnl:+,.2f}{nan_note} (each pick = $2,000 ALLOCATION_PER_PICK)")

    # Top individual picks
    top_winners = sorted(results, key=lambda x: x["pnl_pct"], reverse=True)[:5]
    top_losers = sorted(results, key=lambda x: x["pnl_pct"])[:5]

    print(f"\n  TOP 5 WINNERS:")
    for r in top_winners:
        if r["pnl_pct"] > 0:
            print(f"    {r['signal_type']:>4s} {r['symbol']:>16s} {r['pnl_pct']:>+7.2f}% "
                  f"${r['pnl_dollar']:>+8.2f} [{r['strategy']}] {r['status']}")

    print(f"\n  TOP 5 LOSERS:")
    for r in top_losers:
        if r["pnl_pct"] < 0:
            print(f"    {r['signal_type']:>4s} {r['symbol']:>16s} {r['pnl_pct']:>+7.2f}% "
                  f"${r['pnl_dollar']:>+8.2f} [{r['strategy']}] {r['status']}")

    # Asset class breakdown
    print(f"\n  ASSET CLASS:")
    by_cat = defaultdict(lambda: {"pnl": 0, "n": 0, "w": 0})
    for r in results:
        cat = r.get("category", "?")
        by_cat[cat]["n"] += 1
        by_cat[cat]["pnl"] += r.get("pnl_dollar", 0)
        if r.get("pnl_pct", 0) > 0:
            by_cat[cat]["w"] += 1
    for cat in sorted(by_cat.keys()):
        d = by_cat[cat]
        wr_val = d["w"] / d["n"] * 100 if d["n"] > 0 else 0
        print(f"    {cat:>10s}: {d['n']:>3d} picks, {wr_val:>5.1f}% WR, ${d['pnl']:>+10.2f}")

    # Save check results
    check_entry = {
        "check_time": datetime.now(timezone.utc).isoformat(),
        "elapsed_minutes": round(elapsed_min, 1),
        "strategy_scores": strat_scores,
        "total_pnl": round(all_pnl, 2),
        "win_rate": round(wr, 1),
    }
    challenge["checks"].append(check_entry)
    with open(CHALLENGE_FILE, "w") as f:
        json.dump(challenge, f, indent=2, default=str)

    # Winner declaration
    if strat_scores:
        winner = strat_scores[0]
        print(f"\n  CURRENT LEADER: {winner['strategy']}")
        print(f"    {winner['picks']} picks, {winner['winning']}W/{winner['losing']}L, "
              f"${winner['total_pnl_dollar']:+,.2f}")

    print("=" * 80)
    return strat_scores


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python live_2hr_challenge.py [generate|check] [--duration N]")
        sys.exit(1)

    mode = sys.argv[1].lower()

    # Parse optional --duration N flag (default 2 hours)
    duration_hours = 2
    if "--duration" in sys.argv:
        idx = sys.argv.index("--duration")
        if idx + 1 < len(sys.argv):
            try:
                duration_hours = int(sys.argv[idx + 1])
            except ValueError:
                print("--duration must be an integer")
                sys.exit(1)

    if mode == "generate":
        generate_picks(duration_hours=duration_hours)
    elif mode == "check":
        check_picks()
    else:
        print(f"Unknown mode: {mode}")
