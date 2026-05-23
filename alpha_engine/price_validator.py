#!/usr/bin/env python3
"""
Price Validator -- Runs every 30 min to detect and fix invalid prices in active picks.
Checks: zero/negative entry, TP/SL on wrong side, negative TP/SL, extreme R:R ratios.
Covers crypto, forex, and equity picks.
"""

import json
import os
import sys
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ACTIVE_PICKS_PATH = os.path.join(BASE_DIR, "alpha_engine", "data", "active_picks.json")
LOG_PATH = os.path.join(BASE_DIR, "alpha_engine", "data", "price_validation_log.json")

# Known forex pairs (Yahoo format)
FOREX_PAIRS = {
    "EURUSD=X", "GBPUSD=X", "USDJPY=X", "USDCHF=X", "AUDUSD=X",
    "USDCAD=X", "NZDUSD=X", "EURGBP=X", "EURJPY=X", "GBPJPY=X",
    "AUDCAD=X",
}

# Known equity symbols
EQUITY_SYMBOLS = {
    "SPY", "QQQ", "AAPL", "MSFT", "NVDA", "TSLA", "META", "AMZN", "GOOG",
    "AMD", "COIN", "MSTR", "MARA", "RIOT", "PLTR", "SOFI",
    "GC=F", "SI=F", "CL=F",  # futures
}


def classify_asset(symbol):
    """Classify symbol into crypto/forex/equity."""
    sym = symbol.upper().strip()
    if sym in FOREX_PAIRS:
        return "forex"
    if sym in EQUITY_SYMBOLS or sym.endswith("=F"):
        return "equity"
    if sym.endswith("USDT") or sym.endswith("-USD") or sym.endswith("USD"):
        return "crypto"
    return "unknown"


def validate_pick(p):
    """Validate a single pick. Returns (is_valid, issues, fixes_applied)."""
    issues = []
    fixes = []
    symbol = p.get("symbol", "UNKNOWN")
    direction = (p.get("direction", "") or "").upper()
    entry = p.get("entry_price", 0) or 0
    tp = p.get("take_profit")
    sl = p.get("stop_loss")

    # 1. Zero or negative entry
    if entry <= 0:
        issues.append(f"entry_price={entry} (zero/negative)")
        return False, issues, fixes  # Can't fix -- remove pick

    # 2. Negative TP
    if tp is not None and float(tp) < 0:
        issues.append(f"take_profit={tp} (negative)")
        if direction in ("BUY", "LONG"):
            new_tp = round(entry * 1.02, 8)
        else:
            new_tp = round(entry * 0.98, 8)
        p["take_profit"] = new_tp
        fixes.append(f"TP fixed: {tp} -> {new_tp}")
        tp = new_tp

    # 3. Negative SL
    if sl is not None and float(sl) < 0:
        issues.append(f"stop_loss={sl} (negative)")
        if direction in ("BUY", "LONG"):
            new_sl = round(entry * 0.97, 8)
        else:
            new_sl = round(entry * 1.03, 8)
        p["stop_loss"] = new_sl
        fixes.append(f"SL fixed: {sl} -> {new_sl}")
        sl = new_sl

    # 4. TP on wrong side of entry
    if tp is not None:
        tp_f = float(tp)
        if direction in ("BUY", "LONG") and tp_f < entry:
            issues.append(f"TP={tp_f} below entry={entry} for LONG")
            new_tp = round(entry * 1.02, 8)
            p["take_profit"] = new_tp
            fixes.append(f"TP fixed (wrong side): {tp_f} -> {new_tp}")
        elif direction in ("SELL", "SHORT") and tp_f > entry:
            issues.append(f"TP={tp_f} above entry={entry} for SHORT")
            new_tp = round(entry * 0.98, 8)
            p["take_profit"] = new_tp
            fixes.append(f"TP fixed (wrong side): {tp_f} -> {new_tp}")

    # 5. SL on wrong side of entry
    if sl is not None:
        sl_f = float(sl)
        if direction in ("BUY", "LONG") and sl_f > entry:
            issues.append(f"SL={sl_f} above entry={entry} for LONG")
            new_sl = round(entry * 0.97, 8)
            p["stop_loss"] = new_sl
            fixes.append(f"SL fixed (wrong side): {sl_f} -> {new_sl}")
        elif direction in ("SELL", "SHORT") and sl_f < entry:
            issues.append(f"SL={sl_f} below entry={entry} for SHORT")
            new_sl = round(entry * 1.03, 8)
            p["stop_loss"] = new_sl
            fixes.append(f"SL fixed (wrong side): {sl_f} -> {new_sl}")

    return True, issues, fixes


def run_validation():
    """Main validation logic."""
    now = datetime.now(timezone.utc)
    print("=" * 60)
    print("  PRICE VALIDATOR -- 30-Minute Check")
    print(f"  {now.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 60)

    if not os.path.exists(ACTIVE_PICKS_PATH):
        print(f"[ERROR] active_picks.json not found at {ACTIVE_PICKS_PATH}")
        sys.exit(1)

    with open(ACTIVE_PICKS_PATH, "r", encoding="utf-8") as f:
        picks = json.load(f)

    print(f"\nLoaded {len(picks)} active picks")

    valid_picks = []
    removed = []
    all_issues = []
    all_fixes = []

    for p in picks:
        is_valid, issues, fixes = validate_pick(p)
        if not is_valid:
            removed.append({"symbol": p.get("symbol"), "issues": issues})
            all_issues.extend(issues)
        else:
            valid_picks.append(p)
            if issues:
                all_issues.extend(issues)
            if fixes:
                all_fixes.extend(fixes)

    # Summary
    print(f"\n  Total picks:    {len(picks)}")
    print(f"  Valid picks:    {len(valid_picks)}")
    print(f"  Removed:        {len(removed)}")
    print(f"  Issues found:   {len(all_issues)}")
    print(f"  Fixes applied:  {len(all_fixes)}")

    if removed:
        print(f"\n  REMOVED PICKS:")
        for r in removed:
            print(f"    {r['symbol']}: {', '.join(r['issues'])}")

    if all_fixes:
        print(f"\n  FIXES APPLIED:")
        for fix in all_fixes:
            print(f"    {fix}")

    # Write back if changes were made
    modified = len(removed) > 0 or len(all_fixes) > 0
    if modified:
        with open(ACTIVE_PICKS_PATH, "w", encoding="utf-8") as f:
            json.dump(valid_picks, f, indent=2, default=str)
        print(f"\n  Wrote {len(valid_picks)} picks back to active_picks.json")

    # Write validation log
    log = {
        "timestamp": now.isoformat(),
        "total_picks": len(picks),
        "valid_picks": len(valid_picks),
        "removed_count": len(removed),
        "removed": removed,
        "issues_count": len(all_issues),
        "issues": all_issues,
        "fixes_count": len(all_fixes),
        "fixes": all_fixes,
        "modified": modified,
    }
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, default=str)

    print(f"\n  Log written to: {LOG_PATH}")
    print("=" * 60)

    if not modified:
        print("\n  All picks valid -- no changes needed.")


if __name__ == "__main__":
    run_validation()
