#!/usr/bin/env python3
"""
Antigravity Forward-Test Tracker — Pipeline Integration
=========================================================
1. Loads mega_scan_results.json picks
2. Creates tracked_forward_test.json with exact entry timestamps
3. Provides an outcome checker that fetches candle data to verify TP/SL hits
4. Generates CHATWITHIT.md-ready markdown output

Run modes:
  python ag_forward_tracker.py create   -- Create tracked picks from latest scan
  python ag_forward_tracker.py check    -- Check outcomes of existing picks
  python ag_forward_tracker.py report   -- Generate CHATWITHIT markdown report
"""

import json
import sys
import requests
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

DATA_DIR = Path(r"e:\findtorontoevents_antigravity.ca\genome\data")
TRACKED_FILE = DATA_DIR / "ag_forward_test_tracked.json"
SCAN_FILE = DATA_DIR / "mega_scan_results.json"
REPORT_FILE = DATA_DIR / "ag_forward_test_report.md"

# Max hold = 24 hours (24 x 1h bars)
MAX_HOLD_BARS = 24
TIMEFRAME = "1h"


def create_tracked_picks():
    """Create tracked picks from latest mega scan results."""
    if not SCAN_FILE.exists():
        print("ERROR: No mega_scan_results.json found. Run mega_scan.py first.")
        return

    scan = json.load(open(SCAN_FILE))
    signals = scan.get("signals", [])

    if not signals:
        print("No signals found in scan results.")
        return

    # Dedupe: keep best signal per symbol
    best = {}
    for s in signals:
        sym = s["symbol"]
        if sym not in best or s["confidence"] > best[sym]["confidence"]:
            best[sym] = s

    # Create tracked entries with exact timestamps
    now_utc = datetime.now(timezone.utc)
    now_est = now_utc - timedelta(hours=4)
    entry_time_utc = now_utc.strftime("%Y-%m-%d %H:%M:%S UTC")
    entry_time_est = now_est.strftime("%Y-%m-%d %H:%M:%S EST")

    tracked = {
        "version": "1.0.0",
        "created_at_utc": entry_time_utc,
        "created_at_est": entry_time_est,
        "expires_at_utc": (now_utc + timedelta(hours=MAX_HOLD_BARS)).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "expires_at_est": (now_est + timedelta(hours=MAX_HOLD_BARS)).strftime("%Y-%m-%d %H:%M:%S EST"),
        "max_hold_hours": MAX_HOLD_BARS,
        "timeframe": TIMEFRAME,
        "total_picks": len(best),
        "status": "ACTIVE",
        "picks": [],
    }

    # Sort by confidence descending
    sorted_picks = sorted(best.values(), key=lambda x: x["confidence"], reverse=True)

    for i, s in enumerate(sorted_picks, 1):
        pick = {
            "id": i,
            "symbol": s["symbol"],
            "direction": s["direction"],
            "entry_price": s["entry"],
            "take_profit": s["tp"],
            "stop_loss": s["sl"],
            "risk_reward": s["rr"],
            "confidence": s["confidence"],
            "signal_type": s["type"],
            "discovered_via": s.get("discovered_via", "unknown"),
            "change_24h": s.get("change_24h", 0),
            "quote_volume_24h": s.get("quote_volume_24h", 0),
            "reason": s["reason"],
            "backtest_ref": s.get("backtest", ""),
            "entry_time_utc": entry_time_utc,
            "entry_time_est": entry_time_est,
            "outcome": "PENDING",
            "outcome_price": None,
            "outcome_time": None,
            "outcome_pnl_pct": None,
            "bars_held": None,
        }
        tracked["picks"].append(pick)

    with open(TRACKED_FILE, "w") as f:
        json.dump(tracked, f, indent=2, default=str)

    print(f"Created {len(tracked['picks'])} tracked picks")
    print(f"Entry time: {entry_time_est}")
    print(f"Expires at: {tracked['expires_at_est']}")
    print(f"Saved to: {TRACKED_FILE}")

    # Generate the CHATWITHIT markdown
    generate_chatwithit_entry(tracked)

    return tracked


def check_outcomes():
    """Check if TP or SL was hit for each tracked pick."""
    if not TRACKED_FILE.exists():
        print("No tracked picks file. Run 'create' first.")
        return

    tracked = json.load(open(TRACKED_FILE))
    picks = tracked["picks"]

    if tracked["status"] == "COMPLETED":
        print("All picks already checked. Run 'report' to see results.")
        return tracked

    now_utc = datetime.now(timezone.utc)
    created = datetime.strptime(tracked["created_at_utc"], "%Y-%m-%d %H:%M:%S UTC").replace(tzinfo=timezone.utc)
    hours_elapsed = (now_utc - created).total_seconds() / 3600

    print(f"Checking outcomes... ({hours_elapsed:.1f}h since entry)")
    print(f"Entry time: {tracked['created_at_est']}")
    print()

    wins = 0
    losses = 0
    timeouts = 0
    pending = 0
    checked = 0

    for pick in picks:
        if pick["outcome"] != "PENDING":
            if pick["outcome"] == "WIN": wins += 1
            elif pick["outcome"] == "LOSS": losses += 1
            elif pick["outcome"] == "TIMEOUT": timeouts += 1
            continue

        sym = pick["symbol"]
        entry = pick["entry_price"]
        tp = pick["take_profit"]
        sl = pick["stop_loss"]
        direction = pick["direction"]

        # Fetch candle data since entry
        try:
            url = "https://api.binance.com/api/v3/klines"
            resp = requests.get(url, params={
                "symbol": sym, "interval": "1h",
                "limit": min(MAX_HOLD_BARS + 5, 100)
            }, timeout=10)
            if resp.status_code != 200:
                print(f"  {sym}: API error ({resp.status_code})")
                pending += 1
                continue

            candles = resp.json()
            current_price = float(candles[-1][4])  # Latest close

            # Check each candle for TP/SL hit
            hit_tp = False
            hit_sl = False
            bars_checked = 0

            for candle in candles:
                c_high = float(candle[2])
                c_low = float(candle[3])
                c_close = float(candle[4])

                if direction == "BUY":
                    if c_high >= tp:
                        hit_tp = True
                        break
                    if c_low <= sl:
                        hit_sl = True
                        break
                else:  # SHORT
                    if c_low <= tp:
                        hit_tp = True
                        break
                    if c_high >= sl:
                        hit_sl = True
                        break
                bars_checked += 1

            if hit_tp:
                pick["outcome"] = "WIN"
                pick["outcome_price"] = tp
                pick["outcome_pnl_pct"] = round((tp / entry - 1) * 100, 2) if direction == "BUY" else round((entry / tp - 1) * 100, 2)
                pick["bars_held"] = bars_checked
                wins += 1
                print(f"  ✅ {sym}: WIN (TP hit at ${tp}, PnL: {pick['outcome_pnl_pct']:+.2f}%)")
            elif hit_sl:
                pick["outcome"] = "LOSS"
                pick["outcome_price"] = sl
                pick["outcome_pnl_pct"] = round((sl / entry - 1) * 100, 2) if direction == "BUY" else round((entry / sl - 1) * 100, 2)
                pick["bars_held"] = bars_checked
                losses += 1
                print(f"  ❌ {sym}: LOSS (SL hit at ${sl}, PnL: {pick['outcome_pnl_pct']:+.2f}%)")
            elif hours_elapsed >= MAX_HOLD_BARS:
                pick["outcome"] = "TIMEOUT"
                pick["outcome_price"] = current_price
                pick["outcome_pnl_pct"] = round((current_price / entry - 1) * 100, 2) if direction == "BUY" else round((entry / current_price - 1) * 100, 2)
                pick["bars_held"] = MAX_HOLD_BARS
                timeouts += 1
                tag = "WIN" if pick["outcome_pnl_pct"] > 0 else "LOSS"
                print(f"  ⏰ {sym}: TIMEOUT at ${current_price} (PnL: {pick['outcome_pnl_pct']:+.2f}% = {tag})")
            else:
                # Still active
                unrealized = round((current_price / entry - 1) * 100, 2) if direction == "BUY" else round((entry / current_price - 1) * 100, 2)
                pending += 1
                print(f"  ⏳ {sym}: PENDING at ${current_price} (unrealized: {unrealized:+.2f}%)")

            checked += 1
            time.sleep(0.08)
        except Exception as e:
            print(f"  {sym}: Error - {e}")
            pending += 1

    # Update status
    if pending == 0:
        tracked["status"] = "COMPLETED"

    total_resolved = wins + losses + timeouts
    wr = (wins / total_resolved * 100) if total_resolved > 0 else 0

    tracked["results"] = {
        "wins": wins,
        "losses": losses,
        "timeouts": timeouts,
        "pending": pending,
        "win_rate": round(wr, 1),
        "checked_at_utc": now_utc.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "checked_at_est": (now_utc - timedelta(hours=4)).strftime("%Y-%m-%d %H:%M:%S EST"),
        "hours_elapsed": round(hours_elapsed, 1),
    }

    with open(TRACKED_FILE, "w") as f:
        json.dump(tracked, f, indent=2, default=str)

    print(f"\n{'='*60}")
    print(f"  RESULTS: {wins}W / {losses}L / {timeouts}T / {pending} pending")
    print(f"  Win Rate: {wr:.1f}% ({total_resolved} resolved)")
    print(f"  Hours elapsed: {hours_elapsed:.1f}h / {MAX_HOLD_BARS}h max")
    print(f"{'='*60}")

    return tracked


def generate_chatwithit_entry(tracked):
    """Generate the CHATWITHIT.md formatted entry."""
    picks = tracked["picks"]
    entry_est = tracked["created_at_est"]
    expires_est = tracked["expires_at_est"]

    lines = []
    lines.append(f"### Antigravity Forward-Test Picks — TRACKED ({entry_est})")
    lines.append("")
    lines.append(f"**Entry time:** {entry_est}")
    lines.append(f"**Expires:** {expires_est} (24h max hold)")
    lines.append(f"**Total picks:** {len(picks)}")
    lines.append(f"**Status:** ACTIVE — check outcomes after 24h")
    lines.append("")
    lines.append("| # | Symbol | Dir | Entry | TP | SL | RR | Conf | Signal | 24h% | Reason |")
    lines.append("|---|--------|-----|-------|----|----|-----|------|--------|------|--------|")

    for p in picks[:30]:  # Top 30
        lines.append(
            f"| {p['id']} | {p['symbol']} | {p['direction']} | "
            f"${p['entry_price']} | ${p['take_profit']} | ${p['stop_loss']} | "
            f"{p['risk_reward']} | {p['confidence']:.0f}% | "
            f"`{p['signal_type']}` | {p['change_24h']:+.1f}% | "
            f"{p['reason'][:60]} |"
        )

    if len(picks) > 30:
        lines.append(f"| ... | +{len(picks)-30} more | | | | | | | | | See JSON |")

    lines.append("")
    lines.append(f"**Outcome check command:** `python genome/mutation_lab/ag_forward_tracker.py check`")
    lines.append(f"**Results file:** `genome/data/ag_forward_test_tracked.json`")
    lines.append("")

    report = "\n".join(lines)
    with open(REPORT_FILE, "w") as f:
        f.write(report)

    print(f"\nCHATWITHIT entry saved to: {REPORT_FILE}")
    return report


def generate_report():
    """Generate final report after checking outcomes."""
    if not TRACKED_FILE.exists():
        print("No tracked file found.")
        return

    tracked = json.load(open(TRACKED_FILE))
    results = tracked.get("results", {})

    print(f"\n{'='*60}")
    print(f"  FORWARD-TEST REPORT")
    print(f"{'='*60}")
    print(f"  Entry: {tracked['created_at_est']}")
    print(f"  Checked: {results.get('checked_at_est', 'N/A')}")
    print(f"  Hours: {results.get('hours_elapsed', 'N/A')}h")
    print(f"  Picks: {tracked['total_picks']}")
    print(f"  Results: {results.get('wins',0)}W / {results.get('losses',0)}L / {results.get('timeouts',0)}T")
    print(f"  Win Rate: {results.get('win_rate',0)}%")
    print(f"{'='*60}")

    # Detail
    for p in tracked["picks"]:
        outcome = p["outcome"]
        icon = "✅" if outcome == "WIN" else "❌" if outcome == "LOSS" else "⏰" if outcome == "TIMEOUT" else "⏳"
        pnl = f"{p['outcome_pnl_pct']:+.2f}%" if p['outcome_pnl_pct'] is not None else "pending"
        print(f"  {icon} {p['symbol']:<14} {p['direction']:<5} Entry:${p['entry_price']:<10} -> {outcome:<8} PnL:{pnl}")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "create"

    if mode == "create":
        create_tracked_picks()
    elif mode == "check":
        check_outcomes()
    elif mode == "report":
        generate_report()
    else:
        print(f"Usage: python {sys.argv[0]} [create|check|report]")
