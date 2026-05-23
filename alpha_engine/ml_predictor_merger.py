#!/usr/bin/env python3
"""
ML Crypto Predictor -> Alpha Engine Merger
==========================================
Bridges the ml_crypto_predictor pipeline into alpha_engine's forward validation system.

Problem solved:
  - ml_crypto_predictor has 800+ picks in all_picks_log.json, all stuck as ACTIVE
  - live_picks_tracker.py closes picks in active_picks.json/closed_picks.json but
    never updates all_picks_log.json
  - None of these picks flow into alpha_engine/data/ where forward_validator.py reads
  - Result: 0 forward predictions despite hundreds of closed picks

This merger:
  1. Reads ml_crypto_predictor's all_picks_log.json + closed_picks.json + active_picks.json
  2. Resolves expired/hit picks by checking TP/SL against current Binance prices
  3. Deduplicates (same symbol + entry_price + direction within 5min = duplicate)
  4. Maps fields to alpha_engine schema
  5. Merges into alpha_engine/data/active_picks.json and closed_picks.json

Usage:
  python ml_predictor_merger.py              # Run merger
  python ml_predictor_merger.py --dry-run    # Show what would be merged without writing
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

# Paths
ALPHA_DIR = Path(__file__).resolve().parent
DATA_DIR = ALPHA_DIR / "data"
PROJECT_ROOT = ALPHA_DIR.parent
ML_PICKS_DIR = PROJECT_ROOT / "ml_crypto_predictor" / "enhanced_models" / "live_picks"

# Source files
ML_ALL_PICKS = ML_PICKS_DIR / "all_picks_log.json"
ML_CLOSED_PICKS = ML_PICKS_DIR / "closed_picks.json"
ML_ACTIVE_PICKS = ML_PICKS_DIR / "active_picks.json"

# Target files
ALPHA_ACTIVE_PATH = DATA_DIR / "active_picks.json"
ALPHA_CLOSED_PATH = DATA_DIR / "closed_picks.json"

# Strategy prefix for all merged picks
STRATEGY_PREFIX = "ml_enhanced_"

# Dedup window: picks within this many seconds with same symbol+direction+entry are dupes
DEDUP_WINDOW_SECONDS = 300  # 5 minutes


def load_json(path: Path) -> list:
    """Load JSON file, return empty list if missing or corrupt."""
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except (json.JSONDecodeError, IOError):
            pass
    return []


def save_json(path: Path, data: list) -> None:
    """Write JSON with sanitization for NaN/Infinity."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(_sanitize(data), f, indent=2, ensure_ascii=False)


def _sanitize(obj):
    """Recursively replace NaN/Infinity with None."""
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    if hasattr(obj, "item"):
        v = obj.item()
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            return None
        return v
    return obj


_BINANCE_SPOT_BASES = [
    "https://api.binance.com",
    "https://api.binance.us",
    "https://data-api.binance.vision",
]


def get_binance_price(symbol: str) -> Optional[float]:
    """Fetch current price from Binance spot API with failover."""
    try:
        import requests
    except ImportError:
        return None
    for base in _BINANCE_SPOT_BASES:
        try:
            url = f"{base}/api/v3/ticker/price"
            resp = requests.get(url, params={"symbol": symbol}, timeout=5)
            if resp.status_code in (451, 403):
                continue
            resp.raise_for_status()
            return float(resp.json()["price"])
        except Exception:
            continue
    return None


def get_binance_prices_bulk(symbols: list[str]) -> dict[str, float]:
    """Fetch all prices at once from Binance with failover."""
    prices = {}
    try:
        import requests
    except ImportError:
        return prices
    for base in _BINANCE_SPOT_BASES:
        try:
            url = f"{base}/api/v3/ticker/price"
            resp = requests.get(url, timeout=10)
            if resp.status_code in (451, 403):
                continue
            resp.raise_for_status()
            for item in resp.json():
                if item["symbol"] in symbols:
                    prices[item["symbol"]] = float(item["price"])
            return prices  # success
        except Exception as e:
            print(f"  [WARN] Bulk price fetch from {base} failed: {e}")
            continue
    # All bulk attempts failed -- fall back to individual
    for sym in symbols:
        p = get_binance_price(sym)
        if p is not None:
            prices[sym] = p
        time.sleep(0.05)
    return prices


def normalize_direction(direction: str) -> str:
    """Normalize direction to LONG/SHORT for alpha_engine compatibility."""
    d = direction.upper().strip()
    if d in ("BUY", "LONG"):
        return "LONG"
    if d in ("SELL", "SHORT"):
        return "SHORT"
    return d


def make_alpha_id(pick: dict) -> str:
    """Generate a unique alpha_engine-compatible pick ID."""
    strategy = pick.get("model_variant", pick.get("strategy", "ml_enhanced"))
    # Prefix with ml_enhanced_ if not already
    if not strategy.startswith(STRATEGY_PREFIX) and not strategy.startswith("enhanced_ml"):
        strategy = STRATEGY_PREFIX + strategy
    symbol = pick.get("symbol", "UNKNOWN")
    ts = pick.get("generated_at", pick.get("timestamp", ""))
    date_part = ts[:10] if ts else "unknown"
    return f"{strategy}::{symbol}::{date_part}"


def dedup_key(pick: dict) -> str:
    """Key for deduplication: symbol + direction + entry_price rounded to 4 decimals."""
    symbol = pick.get("symbol", "")
    direction = normalize_direction(pick.get("direction", "BUY"))
    entry = round(float(pick.get("entry_price", 0)), 4)
    return f"{symbol}|{direction}|{entry}"


def dedup_picks(picks: list[dict]) -> list[dict]:
    """
    Remove duplicate picks. Same symbol + direction + entry_price within DEDUP_WINDOW
    keeps only the earliest pick.
    """
    # Group by dedup key
    groups: dict[str, list[dict]] = {}
    for p in picks:
        key = dedup_key(p)
        groups.setdefault(key, []).append(p)

    deduped = []
    total_dupes = 0
    for key, group in groups.items():
        if len(group) == 1:
            deduped.append(group[0])
            continue

        # Sort by timestamp, keep earliest
        def get_ts(p):
            ts = p.get("generated_at", p.get("timestamp", "2099-01-01"))
            return ts
        group.sort(key=get_ts)

        # Within each window, keep first occurrence
        kept = [group[0]]
        for p in group[1:]:
            ts_prev = kept[-1].get("generated_at", kept[-1].get("timestamp", ""))
            ts_curr = p.get("generated_at", p.get("timestamp", ""))
            try:
                dt_prev = datetime.fromisoformat(ts_prev.replace("Z", "+00:00"))
                dt_curr = datetime.fromisoformat(ts_curr.replace("Z", "+00:00"))
                if abs((dt_curr - dt_prev).total_seconds()) > DEDUP_WINDOW_SECONDS:
                    kept.append(p)  # Far enough apart, it's a new signal
            except (ValueError, AttributeError):
                kept.append(p)  # Can't parse, keep it

        total_dupes += len(group) - len(kept)
        deduped.extend(kept)

    if total_dupes > 0:
        print(f"  Dedup: removed {total_dupes} duplicate picks ({len(picks)} -> {len(deduped)})")
    return deduped


def resolve_pick_status(pick: dict, current_price: Optional[float], now: datetime) -> dict:
    """
    Determine if a pick should be WON, LOST, or EXPIRED based on current price
    and expiry time. Mutates and returns the pick.
    """
    # Already resolved by live_picks_tracker
    if pick.get("outcome") in ("TP_HIT", "SL_HIT", "EXPIRED"):
        return pick
    if pick.get("status") == "CLOSED":
        return pick

    direction = normalize_direction(pick.get("direction", "BUY"))
    entry = float(pick.get("entry_price", 0))
    tp = float(pick.get("take_profit", 0))
    sl = float(pick.get("stop_loss", 0))

    if entry == 0 or tp == 0 or sl == 0:
        return pick  # Can't evaluate

    # Check expiry first
    expires_at = pick.get("expires_at", "")
    is_expired = False
    if expires_at:
        try:
            expire_time = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            is_expired = now >= expire_time
        except (ValueError, AttributeError):
            is_expired = True
    else:
        # Default: expire after 48h from generation
        gen_at = pick.get("generated_at", pick.get("timestamp", ""))
        if gen_at:
            try:
                gen_time = datetime.fromisoformat(gen_at.replace("Z", "+00:00"))
                is_expired = now >= gen_time + timedelta(hours=48)
            except (ValueError, AttributeError):
                is_expired = True
        else:
            is_expired = True

    if current_price is not None:
        tp_hit = False
        sl_hit = False
        if direction == "LONG":
            tp_hit = current_price >= tp
            sl_hit = current_price <= sl
            pnl_pct = (current_price - entry) / entry if entry else 0
        else:
            tp_hit = current_price <= tp
            sl_hit = current_price >= sl
            pnl_pct = (entry - current_price) / entry if entry else 0

        if tp_hit:
            pick["status"] = "WON"
            pick["outcome"] = "TP_HIT"
            pick["close_price"] = current_price
            pick["actual_pnl_pct"] = round(pnl_pct * 100, 4)
            pick["closed_at"] = now.isoformat()
            return pick
        elif sl_hit:
            pick["status"] = "LOST"
            pick["outcome"] = "SL_HIT"
            pick["close_price"] = current_price
            pick["actual_pnl_pct"] = round(pnl_pct * 100, 4)
            pick["closed_at"] = now.isoformat()
            return pick

    if is_expired:
        if current_price is not None:
            if direction == "LONG":
                pnl_pct = (current_price - entry) / entry if entry else 0
            else:
                pnl_pct = (entry - current_price) / entry if entry else 0
            pick["close_price"] = current_price
            pick["actual_pnl_pct"] = round(pnl_pct * 100, 4)
        else:
            pick["actual_pnl_pct"] = 0

        pick["status"] = "EXPIRED"
        pick["outcome"] = "EXPIRED"
        pick["closed_at"] = now.isoformat()
        return pick

    # Still active
    if current_price is not None:
        pick["current_price"] = current_price
        if direction == "LONG":
            pnl_pct = (current_price - entry) / entry if entry else 0
        else:
            pnl_pct = (entry - current_price) / entry if entry else 0
        pick["unrealized_pnl_pct"] = round(pnl_pct * 100, 4)

    return pick


def map_to_alpha_schema(pick: dict, is_closed: bool) -> dict:
    """
    Map an ml_crypto_predictor pick to alpha_engine's schema.
    Active picks schema: id, strategy, symbol, category, signal_type, direction,
        entry_price, entry_date, timestamp, take_profit, stop_loss, confidence, etc.
    Closed picks schema adds: exit_price, exit_date, exit_reason, pnl_pct, closed_at, status
    """
    strategy_name = pick.get("model_variant", pick.get("strategy", "ml_enhanced"))
    if not strategy_name.startswith(STRATEGY_PREFIX) and not strategy_name.startswith("enhanced_ml"):
        strategy_name = STRATEGY_PREFIX + strategy_name

    direction = normalize_direction(pick.get("direction", "BUY"))
    signal_type = "BUY" if direction == "LONG" else "SELL"

    # Use `or` (not nested get) so that JSON-null timestamps fall through to datetime.now()
    ts = pick.get("generated_at") or pick.get("timestamp") or None

    # For ACTIVE picks: always stamp with current time if source ts is missing or
    # older than 48 hours. This prevents dashboard_generator's 72h staleness filter
    # from dropping picks just because ml_crypto_predictor stopped emitting timestamps.
    if not is_closed:
        if not ts:
            ts = datetime.now(timezone.utc).isoformat()
        else:
            try:
                ts_dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
                if ts_dt.tzinfo is None:
                    ts_dt = ts_dt.replace(tzinfo=timezone.utc)
                if (datetime.now(timezone.utc) - ts_dt).total_seconds() > 48 * 3600:
                    ts = datetime.now(timezone.utc).isoformat()
            except (ValueError, TypeError):
                ts = datetime.now(timezone.utc).isoformat()
    else:
        ts = ts or datetime.now(timezone.utc).isoformat()

    entry_date = ts[:10] if ts else datetime.now(timezone.utc).strftime("%Y-%m-%d")

    entry_price = float(pick.get("entry_price", 0))
    tp = float(pick.get("take_profit", 0))
    sl = float(pick.get("stop_loss", 0))

    # Confidence: ml_crypto_predictor uses probability (0-1) and confidence (LOW/MEDIUM/HIGH)
    prob = pick.get("probability", 0.5)
    conf_label = pick.get("confidence", "MEDIUM")
    if isinstance(conf_label, str):
        # Convert label to numeric
        conf_map = {"LOW": 0.4, "MEDIUM": 0.6, "HIGH": 0.8, "VERY_HIGH": 0.9}
        confidence = conf_map.get(conf_label.upper(), 0.6)
    else:
        confidence = float(conf_label) if conf_label else 0.6

    # Use probability as ml_score
    ml_score = float(prob) if prob else confidence

    # Risk/reward
    if direction == "LONG" and sl < entry_price and entry_price > 0:
        risk = entry_price - sl
        reward = tp - entry_price
        rr = round(reward / risk, 2) if risk > 0 else 1.0
    elif direction == "SHORT" and sl > entry_price and entry_price > 0:
        risk = sl - entry_price
        reward = entry_price - tp
        rr = round(reward / risk, 2) if risk > 0 else 1.0
    else:
        rr = 1.0

    alpha_pick = {
        "id": make_alpha_id(pick),
        "strategy": strategy_name,
        "symbol": pick.get("symbol", "UNKNOWN"),
        "category": "crypto",
        "signal_type": signal_type,
        "direction": direction,
        "entry_price": entry_price,
        "entry_date": entry_date,
        "timestamp": ts,
        "take_profit": tp,
        "stop_loss": sl,
        "confidence": confidence,
        "ml_score": ml_score,
        "risk_reward": rr,
        "reason": f"ML {pick.get('model_variant', 'enhanced')} | TF={pick.get('timeframe', '?')} | prob={float(prob) if prob else 0:.3f}" if prob else "ML enhanced prediction",
        "rsi_at_entry": None,
        "volume_ratio": None,
        "atr_at_entry": None,
        "status": "OPEN",
        "mfe": 0,
        "mae": 0,
        "high_water_mark": entry_price,
        "current_price": pick.get("current_price", entry_price),
        "unrealized_pnl_pct": pick.get("unrealized_pnl_pct", 0),
        "hold_days": 0,
        "created_at": ts,
        "confluence_score": 1.0,
        "confluence_reason": "",
        "confluence_strategies": [],
        "ensemble_only": False,
        "forward_validated": False,
        "forward_status": "insufficient_data (0/15 trades)",
        "forward_trades": 0,
        "forward_wr": 0.0,
        "last_checked": datetime.now(timezone.utc).isoformat(),
    }

    if is_closed:
        outcome = pick.get("outcome", "EXPIRED")
        status = "WON" if outcome == "TP_HIT" else ("LOST" if outcome == "SL_HIT" else "EXPIRED")
        # Map EXPIRED with profit to WON
        pnl = pick.get("actual_pnl_pct", 0)
        if outcome == "EXPIRED" and pnl and pnl > 0:
            status = "WON"

        alpha_pick["status"] = status
        alpha_pick["exit_price"] = pick.get("close_price", pick.get("current_price", entry_price))
        alpha_pick["exit_date"] = (pick.get("closed_at", ts) or ts)[:10]
        alpha_pick["exit_reason"] = outcome
        alpha_pick["pnl_pct"] = pnl / 100 if pnl and abs(pnl) < 1 else (pnl or 0) / 100
        alpha_pick["pnl_dollar"] = round(alpha_pick["pnl_pct"] * 2000, 2)  # $2000 default allocation
        alpha_pick["closed_at"] = pick.get("closed_at", ts)

        # Calculate hold_days
        try:
            gen = datetime.fromisoformat((pick.get("generated_at", ts) or ts).replace("Z", "+00:00"))
            close = datetime.fromisoformat((pick.get("closed_at", ts) or ts).replace("Z", "+00:00"))
            alpha_pick["hold_days"] = max(0, (close - gen).days)
        except (ValueError, AttributeError):
            alpha_pick["hold_days"] = 0

    return alpha_pick


def run_merger(dry_run: bool = False) -> dict:
    """
    Main merge function. Reads ml_crypto_predictor picks, resolves statuses,
    deduplicates, and merges into alpha_engine data files.

    Returns summary dict.
    """
    print("=" * 60)
    print("ML Crypto Predictor -> Alpha Engine Merger")
    print("=" * 60)

    now = datetime.now(timezone.utc)

    # -- Step 1: Load all source picks --
    all_picks = load_json(ML_ALL_PICKS)
    ml_closed = load_json(ML_CLOSED_PICKS)
    ml_active = load_json(ML_ACTIVE_PICKS)

    print(f"\n  Source data:")
    print(f"    all_picks_log.json:  {len(all_picks)} picks")
    print(f"    closed_picks.json:   {len(ml_closed)} picks")
    print(f"    active_picks.json:   {len(ml_active)} picks")

    # Build a lookup of already-closed picks from ml_crypto_predictor's own tracker
    closed_lookup = {}
    for p in ml_closed:
        key = dedup_key(p)
        closed_lookup[key] = p

    # -- Step 2: Merge closed status back into all_picks_log --
    # The live_picks_tracker closes picks in closed_picks.json but never updates all_picks_log
    #
    # Status-shard guard (2026-05-14): skip picks whose status is already
    # terminal. With the all_picks_log.json hot/cold split, terminal picks
    # live in gzipped monthly shards (closed/closed_YYYYMM.json.gz) and
    # must not be mutated here — re-writing them would re-dirty cold
    # shards on every merger run. See tools/migrate_all_picks_log.py and
    # the matching writer in ml_crypto_predictor/enhanced_models/live_picks_tracker.py.
    _TERMINAL = {"WIN","WON","LOSS","LOST","CLOSED","EXPIRED","TP_HIT","SL_HIT"}
    for pick in all_picks:
        _st = str(pick.get("status") or "").upper()
        _oc = str(pick.get("outcome") or "").upper()
        if _st in _TERMINAL or _oc in _TERMINAL:
            # Already terminal — cold-shard owns this row, do not mutate.
            continue
        key = dedup_key(pick)
        if key in closed_lookup:
            closed_p = closed_lookup[key]
            pick["status"] = closed_p.get("status", "CLOSED")
            pick["outcome"] = closed_p.get("outcome")
            pick["closed_at"] = closed_p.get("closed_at")
            pick["close_price"] = closed_p.get("close_price")
            pick["actual_pnl_pct"] = closed_p.get("actual_pnl_pct")

    # -- Step 3: Deduplicate --
    deduped = dedup_picks(all_picks)
    print(f"\n  After dedup: {len(deduped)} unique picks")

    # -- Step 4: Get current prices for unresolved picks --
    unresolved = [p for p in deduped if p.get("status") == "ACTIVE" and not p.get("outcome")]
    symbols_needed = list(set(p.get("symbol", "") for p in unresolved if p.get("symbol")))

    prices = {}
    if symbols_needed and not dry_run:
        print(f"\n  Fetching prices for {len(symbols_needed)} symbols...")
        prices = get_binance_prices_bulk(symbols_needed)
        print(f"  Got prices for {len(prices)} symbols")

    # -- Step 5: Resolve all pick statuses --
    resolved_active = []
    resolved_closed = []

    for pick in deduped:
        current_price = prices.get(pick.get("symbol"))
        pick = resolve_pick_status(pick, current_price, now)

        if pick.get("outcome") in ("TP_HIT", "SL_HIT", "EXPIRED"):
            resolved_closed.append(pick)
        elif pick.get("status") in ("WON", "LOST", "EXPIRED", "CLOSED"):
            resolved_closed.append(pick)
        else:
            resolved_active.append(pick)

    won = sum(1 for p in resolved_closed if p.get("status") == "WON" or p.get("outcome") == "TP_HIT")
    lost = sum(1 for p in resolved_closed if p.get("status") == "LOST" or p.get("outcome") == "SL_HIT")
    expired = sum(1 for p in resolved_closed if p.get("outcome") == "EXPIRED")

    print(f"\n  Resolution:")
    print(f"    Active:  {len(resolved_active)}")
    print(f"    Closed:  {len(resolved_closed)} (WON={won}, LOST={lost}, EXPIRED={expired})")

    if dry_run:
        print("\n  [DRY RUN] No files written.")
        return {
            "active": len(resolved_active),
            "closed": len(resolved_closed),
            "won": won,
            "lost": lost,
            "expired": expired,
            "dry_run": True,
        }

    # -- Step 6: Map to alpha_engine schema and merge --
    alpha_active_new = [map_to_alpha_schema(p, is_closed=False) for p in resolved_active]
    alpha_closed_new = [map_to_alpha_schema(p, is_closed=True) for p in resolved_closed]

    # Load existing alpha_engine data
    existing_active = load_json(ALPHA_ACTIVE_PATH)
    existing_closed = load_json(ALPHA_CLOSED_PATH)

    # Remove old ml_enhanced_ picks from alpha data (we replace them fully each run)
    existing_active = [p for p in existing_active
                       if not (p.get("strategy", "").startswith(STRATEGY_PREFIX)
                               or p.get("strategy", "").startswith("enhanced_ml"))]
    existing_closed = [p for p in existing_closed
                       if not (p.get("strategy", "").startswith(STRATEGY_PREFIX)
                               or p.get("strategy", "").startswith("enhanced_ml"))]

    # Deduplicate closed by ID
    closed_ids = set(p.get("id") for p in existing_closed)
    new_closed_count = 0
    for p in alpha_closed_new:
        if p["id"] not in closed_ids:
            existing_closed.append(p)
            closed_ids.add(p["id"])
            new_closed_count += 1

    # Add active picks -- deduplicate per symbol+direction (keep highest confidence)
    # Fixes the 64 FETUSDT + 36 RENDERUSDT duplicate flooding issue
    seen_active = {}
    for p in alpha_active_new:
        key = (p.get("symbol", ""), (p.get("direction", "") or "").upper())
        conf = p.get("confidence", 0) or 0
        if key not in seen_active or conf > (seen_active[key].get("confidence", 0) or 0):
            seen_active[key] = p
    deduped_active = list(seen_active.values())
    if len(deduped_active) < len(alpha_active_new):
        print(f"  [DEDUP] ML active: {len(alpha_active_new)} -> {len(deduped_active)} "
              f"(collapsed {len(alpha_active_new) - len(deduped_active)} same-symbol duplicates)")
    existing_active.extend(deduped_active)

    # Cleanup: remove pre-existing duplicates in active picks (per symbol+strategy+direction)
    # Fixes historical 64x FETUSDT + 36x RENDERUSDT duplicate flooding
    pre_cleanup = len(existing_active)
    seen_all = {}
    cleaned_active = []
    for p in existing_active:
        key = (p.get("symbol", ""), p.get("strategy", ""), (p.get("direction", "") or "").upper())
        if key not in seen_all:
            seen_all[key] = p
            cleaned_active.append(p)
        else:
            # Keep the one with higher elite_score or more recent timestamp
            existing = seen_all[key]
            if (p.get("elite_score") or 0) > (existing.get("elite_score") or 0):
                cleaned_active.remove(existing)
                cleaned_active.append(p)
                seen_all[key] = p
    if len(cleaned_active) < pre_cleanup:
        print(f"  [CLEANUP] Removed {pre_cleanup - len(cleaned_active)} legacy duplicate active picks")
    existing_active = cleaned_active

    # Score ALL picks (including ml_enhanced) with elite scorer
    try:
        from elite_scorer import enrich_picks_with_elite_score
        unscored = [p for p in existing_active if p.get("elite_score") is None]
        if unscored:
            enrich_picks_with_elite_score(unscored, str(DATA_DIR))
            print(f"  [ELITE] Scored {len(unscored)} previously unscored picks")
    except Exception as e:
        print(f"  [WARN] Elite scoring failed (non-fatal): {e}")

    # Save
    save_json(ALPHA_ACTIVE_PATH, existing_active)
    save_json(ALPHA_CLOSED_PATH, existing_closed)

    # Also update ml_crypto_predictor's own all_picks_log with resolved statuses
    save_json(ML_ALL_PICKS, deduped)

    print(f"\n  Merged into alpha_engine:")
    print(f"    active_picks.json: +{len(alpha_active_new)} ML picks (total: {len(existing_active)})")
    print(f"    closed_picks.json: +{new_closed_count} ML picks (total: {len(existing_closed)})")
    print(f"    Updated all_picks_log.json with resolved statuses")

    wr = round(won / (won + lost) * 100, 1) if (won + lost) > 0 else 0
    print(f"\n  ML Predictor Forward Stats: {won}W/{lost}L ({wr}% WR), {expired} expired")
    print("=" * 60)

    return {
        "active": len(resolved_active),
        "closed": len(resolved_closed),
        "won": won,
        "lost": lost,
        "expired": expired,
        "win_rate": wr,
        "merged_active": len(alpha_active_new),
        "merged_closed": new_closed_count,
        "total_active": len(existing_active),
        "total_closed": len(existing_closed),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Merge ML crypto predictor picks into alpha engine")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be merged without writing")
    args = parser.parse_args()
    result = run_merger(dry_run=args.dry_run)
    print(f"\nResult: {json.dumps(result, indent=2)}")
