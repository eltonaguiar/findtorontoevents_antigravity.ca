#!/usr/bin/env python3
"""
Hourly Smart Picks Performance Monitor

Runs smart_picks_engine, logs results, and tracks PnL over time.
Designed to run via cron/task scheduler or manually.

Output: alpha_engine/data/smart_picks_monitor.json (append-mode log)
"""
import json, sys, os
from datetime import datetime, timezone
from pathlib import Path

DATA = Path(__file__).resolve().parent / "alpha_engine" / "data"
LOG_PATH = DATA / "smart_picks_monitor.json"

def load_log():
    if LOG_PATH.exists():
        try:
            return json.loads(LOG_PATH.read_text(encoding="utf-8"))
        except:
            return {"snapshots": []}
    return {"snapshots": []}

def run_monitor():
    now = datetime.now(timezone.utc)
    now_str = now.isoformat()
    
    # Run the smart picks engine
    print(f"[{now_str[:19]}] Running smart_picks_engine...")
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    
    try:
        from alpha_engine.smart_picks_engine import run as sp_run
        result = sp_run()
    except Exception as e:
        print(f"  ERROR: {e}")
        return
    
    if not result:
        print("  No result from smart_picks_engine")
        return
    
    picks = result.get("picks", [])
    regime = result.get("regime", "?")
    fgi = result.get("fear_greed", 0)
    btc = result.get("btc_price", 0)
    excluded = result.get("excluded_reasons", {})
    
    # Compute stats
    wins = sum(1 for p in picks if (p.get("pnl_pct") or 0) > 0)
    losses = sum(1 for p in picks if (p.get("pnl_pct") or 0) < 0)
    flat = sum(1 for p in picks if p.get("pnl_pct", 0) == 0)
    total_pnl = sum(p.get("pnl_pct", 0) for p in picks)
    avg_score = sum(p.get("smart_score", 0) for p in picks) / len(picks) if picks else 0
    
    directions = {}
    for p in picks:
        d = p.get("direction", "?")
        directions[d] = directions.get(d, 0) + 1
    
    snapshot = {
        "timestamp": now_str,
        "regime": regime,
        "fgi": fgi,
        "btc_price": btc,
        "total_picks": len(picks),
        "wins": wins,
        "losses": losses,
        "flat": flat,
        "total_pnl": round(total_pnl, 4),
        "avg_score": round(avg_score, 1),
        "directions": directions,
        "excluded": excluded,
        "picks": [
            {
                "symbol": p.get("symbol"),
                "direction": p.get("direction"),
                "score": p.get("smart_score"),
                "pnl_pct": p.get("pnl_pct"),
                "strategy": p.get("strategy", "")[:40],
                "tier": p.get("tier", "?"),
                "rr": p.get("rr", 0),
            }
            for p in picks
        ],
    }
    
    # Load existing log and append
    log = load_log()
    log["snapshots"].append(snapshot)
    
    # Keep only last 168 snapshots (7 days hourly)
    if len(log["snapshots"]) > 168:
        log["snapshots"] = log["snapshots"][-168:]
    
    # Compute rolling stats
    recent = log["snapshots"][-24:]  # last 24h
    all_picks_pnl = []
    for s in recent:
        for p in s.get("picks", []):
            all_picks_pnl.append(p.get("pnl_pct", 0))
    
    if all_picks_pnl:
        log["rolling_24h"] = {
            "total_picks_seen": len(all_picks_pnl),
            "avg_pnl": round(sum(all_picks_pnl) / len(all_picks_pnl), 4),
            "total_pnl": round(sum(all_picks_pnl), 4),
            "wins": sum(1 for p in all_picks_pnl if p > 0),
            "losses": sum(1 for p in all_picks_pnl if p < 0),
        }
    
    log["last_updated"] = now_str
    LOG_PATH.write_text(json.dumps(log, indent=2), encoding="utf-8")
    
    # Print summary
    print(f"\n{'=' * 60}")
    print(f"SMART PICKS MONITOR | {now_str[:19]} UTC")
    print(f"{'=' * 60}")
    print(f"Regime: {regime} | FGI: {fgi} | BTC: ${btc:,.0f}")
    print(f"Picks: {len(picks)} | W/L/F: {wins}/{losses}/{flat} | PnL: {total_pnl:+.2f}%")
    print(f"Avg Score: {avg_score:.0f} | Dirs: {directions}")
    print(f"Excluded: {sum(excluded.values())} total")
    
    for key in ["hard_block_long_in_fear", "hard_block_short_in_greed", "wrong_direction", "banned_system"]:
        if excluded.get(key, 0) > 0:
            print(f"  {key}: {excluded[key]}")
    
    print(f"\nPicks:")
    for p in picks:
        pnl = p.get("pnl_pct", 0)
        status = "WIN" if pnl > 0 else "LOSS" if pnl < 0 else "FLAT"
        print(f"  {status:>4} {p['symbol']:<14} {p['direction']:<6} Sc:{p['smart_score']:>3} PnL:{pnl:+.2f}% {p['strategy'][:30]}")
    
    if log.get("rolling_24h"):
        r = log["rolling_24h"]
        print(f"\n24h Rolling: {r['total_picks_seen']} picks seen | {r['wins']}W/{r['losses']}L | Avg PnL: {r['avg_pnl']:+.4f}%")
    
    # Compare with previous snapshot
    if len(log["snapshots"]) >= 2:
        prev = log["snapshots"][-2]
        pnl_delta = snapshot["total_pnl"] - prev["total_pnl"]
        print(f"\nΔ vs last check: PnL {pnl_delta:+.2f}% | Picks {snapshot['total_picks']} (was {prev['total_picks']})")
    
    print(f"\nLog saved to {LOG_PATH}")
    return snapshot

if __name__ == "__main__":
    run_monitor()
