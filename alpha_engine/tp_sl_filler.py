"""
TP/SL Filler - Retroactively adds or fixes TP/SL for picks missing them or with R:R < 0.5.

For crypto symbols: fetches ATR(14) from Binance klines (with mirror failover).
For non-crypto: uses default ATR percentages (forex 0.3%, equity 1.5%, commodity 2%).

Only modifies picks that are MISSING TP/SL or have extremely poor R:R (< 0.5).
Never overwrites picks that already have reasonable TP/SL.

Usage:
    python tp_sl_filler.py                          # fix active_picks.json
    python tp_sl_filler.py --dry-run                # preview changes only
    python tp_sl_filler.py --path data/picks.json   # custom path
"""

import json
import os
import sys
import time
import math
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

MIN_RR_THRESHOLD = 0.5       # below this, TP/SL are considered broken
ATR_TP_MULTIPLIER = 2.5      # TP = entry +/- 2.5 * ATR
ATR_SL_MULTIPLIER = 1.5      # SL = entry +/- 1.5 * ATR
USE_ADAPTIVE_TP_SL = True    # try MFE/MAE-derived TP/SL first, fall back to ATR

# Asset class caps (max TP distance %, max SL distance %)
ASSET_CAPS = {
    "crypto":    (15.0, 10.0),
    "forex":     (1.0, 0.5),
    "equity":    (5.0, 3.0),
    "commodity": (5.0, 3.0),
}

# Default ATR % for non-crypto assets (when we can't fetch klines)
DEFAULT_ATR_PCT = {
    "forex":     0.5,   # ~0.5% daily ATR for major pairs (was 0.3% -- too tight for multi-day holds)
    "equity":    2.0,   # ~2% for swing trades (was 1.5% -- TP too close for 2-week holds)
    "commodity": 2.5,   # ~2.5% for commodities (was 2.0%)
    "crypto":    3.0,   # fallback if Binance fails
}

# Binance mirror failover chain (per CLAUDE.md)
BINANCE_MIRRORS = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
]

# ---------------------------------------------------------------------------
# Binance kline fetcher with mirror failover
# ---------------------------------------------------------------------------

def _fetch_url(url, timeout=10):
    """Fetch URL with timeout, return bytes or None."""
    try:
        req = Request(url, headers={"User-Agent": "AlphaEngine/2.0"})
        resp = urlopen(req, timeout=timeout)
        return resp.read()
    except (URLError, HTTPError, OSError, TimeoutError):
        return None


def fetch_binance_klines(symbol, interval="1h", limit=20):
    """Fetch klines from Binance with mirror failover. Returns list of OHLCV."""
    for mirror in BINANCE_MIRRORS:
        url = f"{mirror}/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        data = _fetch_url(url)
        if data:
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                continue
    return None


def compute_atr_from_klines(klines, period=14):
    """Compute ATR from Binance klines. Each kline: [open_time, open, high, low, close, ...]"""
    if not klines or len(klines) < period + 1:
        return None

    true_ranges = []
    for i in range(1, len(klines)):
        high = float(klines[i][2])
        low = float(klines[i][3])
        prev_close = float(klines[i - 1][4])
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        true_ranges.append(tr)

    if len(true_ranges) < period:
        return None

    # Simple moving average of last `period` true ranges
    return sum(true_ranges[-period:]) / period


# ---------------------------------------------------------------------------
# Symbol helpers
# ---------------------------------------------------------------------------

def normalize_binance_symbol(symbol):
    """Convert symbol to Binance format (e.g., BTCUSDT stays, BTC-USD -> BTCUSDT)."""
    s = symbol.upper().replace("-", "").replace("/", "")
    # Strip trailing forex/equity suffixes
    for suffix in ("=X", "=F"):
        s = s.replace(suffix, "")
    # Ensure USDT suffix for crypto
    if not s.endswith("USDT") and not s.endswith("BUSD") and not s.endswith("USD"):
        s = s + "USDT"
    # Convert xUSD to xUSDT
    if s.endswith("USD") and not s.endswith("USDT"):
        s = s + "T"
    return s


def detect_category(pick):
    """Detect asset category from pick data."""
    cat = pick.get("category", "").lower()
    if cat in ("crypto", "forex", "equity", "commodity"):
        return cat
    symbol = pick.get("symbol", "")
    if "=X" in symbol or symbol.endswith("USD") and len(symbol) == 6:
        return "forex"
    if "=F" in symbol:
        return "commodity"
    if symbol.endswith("USDT") or symbol.endswith("BUSD"):
        return "crypto"
    return "crypto"  # default


# ---------------------------------------------------------------------------
# MFE/MAE adaptive TP/SL integration
# ---------------------------------------------------------------------------

def _try_adaptive_tp_sl(pick):
    """
    Try to get MFE/MAE-derived adaptive TP/SL for this pick.
    Returns (take_profit, stop_loss, risk_reward, method) or None.
    """
    if not USE_ADAPTIVE_TP_SL:
        return None

    try:
        from alpha_engine.mfe_mae_analyzer import get_adaptive_tp_sl
    except ImportError:
        try:
            from mfe_mae_analyzer import get_adaptive_tp_sl
        except ImportError:
            return None

    strategy = pick.get("strategy", "")
    direction = pick.get("direction", "LONG").upper()
    if direction not in ("LONG", "SHORT"):
        sig = pick.get("signal_type", "BUY").upper()
        direction = "SHORT" if sig == "SELL" else "LONG"

    category = detect_category(pick)
    adaptive = get_adaptive_tp_sl(strategy, direction, category)
    if adaptive is None:
        return None

    tp_pct, sl_pct, rr_ratio = adaptive
    entry = pick.get("entry_price", 0)
    if not entry or entry <= 0:
        return None

    if direction == "LONG":
        tp = entry * (1.0 + tp_pct / 100.0)
        sl = entry * (1.0 - sl_pct / 100.0)
    else:
        tp = entry * (1.0 - tp_pct / 100.0)
        sl = entry * (1.0 + sl_pct / 100.0)

    # SL must not be zero or negative
    if sl <= 0:
        sl = entry * 0.01

    # Round to appropriate precision
    if entry < 0.001:
        decimals = 8
    elif entry < 0.1:
        decimals = 6
    elif entry < 10:
        decimals = 4
    elif entry < 1000:
        decimals = 2
    else:
        decimals = 2

    tp = round(tp, decimals)
    sl = round(sl, decimals)

    return tp, sl, rr_ratio, f"adaptive_mfe_mae_{category}"


# ---------------------------------------------------------------------------
# Core: compute TP/SL for a single pick
# ---------------------------------------------------------------------------

def compute_tp_sl(pick, atr_cache=None):
    """
    Compute TP/SL for a pick using ATR-based calculation.

    Returns (take_profit, stop_loss, risk_reward, method) or None if can't compute.
    """
    if atr_cache is None:
        atr_cache = {}

    # Try MFE/MAE adaptive TP/SL first
    adaptive = _try_adaptive_tp_sl(pick)
    if adaptive is not None:
        return adaptive

    entry = pick.get("entry_price", 0)
    if not entry or entry <= 0:
        return None

    direction = pick.get("direction", "LONG").upper()
    if direction not in ("LONG", "SHORT"):
        # Infer from signal_type
        sig = pick.get("signal_type", "BUY").upper()
        direction = "SHORT" if sig == "SELL" else "LONG"

    category = detect_category(pick)
    symbol = pick.get("symbol", "")
    binance_sym = normalize_binance_symbol(symbol)

    # Try to get ATR from Binance for crypto
    atr = None
    method = "default_pct"
    if category == "crypto":
        if binance_sym in atr_cache:
            atr = atr_cache[binance_sym]
        else:
            klines = fetch_binance_klines(binance_sym, interval="1h", limit=20)
            if klines:
                atr = compute_atr_from_klines(klines)
                atr_cache[binance_sym] = atr
            else:
                atr_cache[binance_sym] = None

        if atr and atr > 0:
            method = "atr_binance"

    # Fallback: use default ATR percentage
    if atr is None or atr <= 0:
        default_pct = DEFAULT_ATR_PCT.get(category, 3.0)
        atr = entry * (default_pct / 100.0)
        method = f"default_{category}_{default_pct}pct"

    # Compute raw TP/SL
    if direction == "LONG":
        tp = entry + ATR_TP_MULTIPLIER * atr
        sl = entry - ATR_SL_MULTIPLIER * atr
    else:
        tp = entry - ATR_TP_MULTIPLIER * atr
        sl = entry + ATR_SL_MULTIPLIER * atr

    # Apply asset class caps
    tp_cap_pct, sl_cap_pct = ASSET_CAPS.get(category, (15.0, 8.0))
    max_tp_dist = entry * (tp_cap_pct / 100.0)
    max_sl_dist = entry * (sl_cap_pct / 100.0)

    if direction == "LONG":
        tp = min(tp, entry + max_tp_dist)
        sl = max(sl, entry - max_sl_dist)
    else:
        tp = max(tp, entry - max_tp_dist)
        sl = min(sl, entry + max_sl_dist)

    # SL must not be zero or negative
    if sl <= 0:
        sl = entry * 0.01  # 1% of entry as absolute floor

    # Compute risk_reward
    tp_dist = abs(tp - entry)
    sl_dist = abs(entry - sl)
    risk_reward = round(tp_dist / sl_dist, 2) if sl_dist > 0 else 0

    # Round to appropriate precision
    if entry < 0.001:
        decimals = 8
    elif entry < 0.1:
        decimals = 6
    elif entry < 10:
        decimals = 4
    elif entry < 1000:
        decimals = 2
    else:
        decimals = 2

    tp = round(tp, decimals)
    sl = round(sl, decimals)

    return tp, sl, risk_reward, method


# ---------------------------------------------------------------------------
# Main: fill missing TP/SL in active_picks.json
# ---------------------------------------------------------------------------

def pick_needs_fix(pick):
    """Check if a pick needs TP/SL fix."""
    tp = pick.get("take_profit")
    sl = pick.get("stop_loss")
    entry = pick.get("entry_price", 0)
    rr = pick.get("risk_reward")

    # Missing TP or SL entirely
    if tp is None or tp == 0 or sl is None or sl == 0:
        return True, "missing_tp_sl"

    # risk_reward field missing
    if rr is None and "risk_reward" not in pick:
        # Check if existing TP/SL are reasonable
        if entry > 0:
            tp_dist = abs(tp - entry) / entry
            sl_dist = abs(sl - entry) / entry
            computed_rr = tp_dist / sl_dist if sl_dist > 0 else 0
            if computed_rr < MIN_RR_THRESHOLD:
                return True, f"poor_rr_{computed_rr:.2f}"
            # TP/SL are fine, just need risk_reward field added
            return True, "add_rr_field_only"

    # R:R explicitly zero
    if rr == 0:
        return True, "rr_zero"

    return False, ""


def fill_missing_tp_sl(active_picks_path=None, dry_run=False):
    """
    For each pick missing TP/SL or with R:R < 0.5:
    1. Fetch current price from Binance (with mirror failover)
    2. Compute ATR(14) from recent klines
    3. Set TP = entry +/- 2.5 * ATR
    4. Set SL = entry -/+ 1.5 * ATR
    5. Apply asset class caps
    6. Compute risk_reward
    7. Update the pick in-place
    """
    if active_picks_path is None:
        # Determine path relative to this script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        active_picks_path = os.path.join(script_dir, "data", "active_picks.json")

    if not os.path.exists(active_picks_path):
        print(f"[tp_sl_filler] File not found: {active_picks_path}")
        return {"fixed": 0, "skipped": 0, "errors": 0}

    with open(active_picks_path, "r") as f:
        picks = json.load(f)

    if not isinstance(picks, list):
        print("[tp_sl_filler] active_picks.json is not a list")
        return {"fixed": 0, "skipped": 0, "errors": 0}

    atr_cache = {}
    fixed = 0
    rr_only = 0
    skipped = 0
    errors = 0
    changes = []

    for pick in picks:
        needs_fix, reason = pick_needs_fix(pick)
        if not needs_fix:
            skipped += 1
            continue

        entry = pick.get("entry_price", 0)
        if not entry or entry <= 0:
            skipped += 1
            continue

        if reason == "add_rr_field_only":
            # TP/SL are fine, just compute and add risk_reward
            tp = pick["take_profit"]
            sl = pick["stop_loss"]
            tp_dist = abs(tp - entry) / entry
            sl_dist = abs(sl - entry) / entry
            rr = round(tp_dist / sl_dist, 2) if sl_dist > 0 else 0

            old_rr = pick.get("risk_reward")
            pick["risk_reward"] = rr
            rr_only += 1
            changes.append({
                "id": pick.get("id", "?"),
                "symbol": pick.get("symbol", "?"),
                "action": "add_rr_field",
                "risk_reward": rr,
                "method": "computed_from_existing_tp_sl"
            })
            continue

        # Need to replace TP/SL (poor R:R or missing)
        try:
            result = compute_tp_sl(pick, atr_cache)
            if result is None:
                errors += 1
                continue

            new_tp, new_sl, new_rr, method = result
            old_tp = pick.get("take_profit")
            old_sl = pick.get("stop_loss")
            old_rr = pick.get("risk_reward")

            pick["take_profit"] = new_tp
            pick["stop_loss"] = new_sl
            pick["risk_reward"] = new_rr

            # Tag the pick so we know it was auto-filled
            pick["tp_sl_method"] = method
            pick["tp_sl_filled_at"] = datetime.now(timezone.utc).isoformat()

            fixed += 1
            changes.append({
                "id": pick.get("id", "?"),
                "symbol": pick.get("symbol", "?"),
                "direction": pick.get("direction", "?"),
                "action": "replaced_tp_sl",
                "reason": reason,
                "old_tp": old_tp,
                "old_sl": old_sl,
                "old_rr": old_rr,
                "new_tp": new_tp,
                "new_sl": new_sl,
                "new_rr": new_rr,
                "method": method,
            })
        except Exception as e:
            errors += 1
            print(f"[tp_sl_filler] Error on {pick.get('symbol', '?')}: {e}")

    # Summary
    total = len(picks)
    print(f"[tp_sl_filler] Total: {total} picks")
    print(f"[tp_sl_filler] Fixed TP/SL: {fixed}")
    print(f"[tp_sl_filler] Added R:R only: {rr_only}")
    print(f"[tp_sl_filler] Skipped (already good): {skipped}")
    print(f"[tp_sl_filler] Errors: {errors}")

    if changes:
        print(f"\n[tp_sl_filler] Changes:")
        for c in changes:
            if c["action"] == "replaced_tp_sl":
                print(f"  {c['symbol']:16s} {c['direction']:5s} "
                      f"TP: {c['old_tp']} -> {c['new_tp']}  "
                      f"SL: {c['old_sl']} -> {c['new_sl']}  "
                      f"R:R: {c['old_rr']} -> {c['new_rr']}  "
                      f"({c['method']})")
            else:
                print(f"  {c['symbol']:16s} R:R = {c['risk_reward']} (computed from existing TP/SL)")

    # Write back
    if not dry_run and (fixed > 0 or rr_only > 0):
        with open(active_picks_path, "w") as f:
            json.dump(picks, f, indent=2)
        print(f"\n[tp_sl_filler] Saved {active_picks_path}")
    elif dry_run:
        print(f"\n[tp_sl_filler] DRY RUN - no changes written")

    return {
        "total": total,
        "fixed": fixed,
        "rr_only": rr_only,
        "skipped": skipped,
        "errors": errors,
        "changes": changes,
    }


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    path = None
    for i, arg in enumerate(sys.argv):
        if arg == "--path" and i + 1 < len(sys.argv):
            path = sys.argv[i + 1]

    result = fill_missing_tp_sl(active_picks_path=path, dry_run=dry_run)
    if result["fixed"] == 0 and result["rr_only"] == 0:
        print("\n[tp_sl_filler] Nothing to fix!")
    sys.exit(0)
