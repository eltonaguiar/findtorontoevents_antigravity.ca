#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multi-Asset Bridge: Merges forex/futures/commodity/stock picks into alpha_engine active_picks.json

Problem: Multi-asset and CTA picks are generated but NEVER flow into the audit dashboard.
         active_picks.json has 66 crypto picks and ZERO non-crypto picks.

Solution: This bridge script:
  1. Loads picks from multi_asset_picks.json (multi-asset copytrader scanner)
  2. Loads picks from cta_picks.json (CTA strategy replicator)
  3. Loads picks from copytrader_test_portfolios.json (DNA clone positions)
  4. Normalizes ALL picks to alpha_engine active_picks format
  5. Removes stale multi-asset/CTA picks from active_picks.json (refresh each run)
  6. Appends fresh normalized picks
  7. Updates audit_dashboard/data/forex_futures_picks.json with non-crypto picks

Run: python copy_trader_intel/multi_asset_bridge.py
"""

import json
import os
import sys
from datetime import datetime, timezone

# Windows UTF-8 fix
if sys.platform == "win32":
    import locale
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Resolve paths relative to repo root
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)

DATA_DIR = os.path.join(SCRIPT_DIR, "data")
MULTI_ASSET_FILE = os.path.join(DATA_DIR, "multi_asset_picks.json")
CTA_FILE = os.path.join(DATA_DIR, "cta_picks.json")
TEST_PORTFOLIOS_FILE = os.path.join(DATA_DIR, "copytrader_test_portfolios.json")
ACTIVE_PICKS_FILE = os.path.join(REPO_ROOT, "alpha_engine", "data", "active_picks.json")
AUDIT_FOREX_FILE = os.path.join(REPO_ROOT, "audit_dashboard", "data", "forex_futures_picks.json")
# Mirror non-crypto picks to multi_asset/data/ so dashboard_generator's multi_asset source stays fresh
MULTI_ASSET_MIRROR_FILE = os.path.join(REPO_ROOT, "multi_asset", "data", "active_picks.json")
MULTI_ASSET_PICKS_MIRROR = os.path.join(REPO_ROOT, "multi_asset", "data", "multi_asset_picks.json")

# Source system prefixes we manage (used for stale-pick removal)
MANAGED_SOURCES = ("multi_asset_", "cta_", "copytrader_dna")

# Import confidence multiplier from auto_tuner (applies 0.4x to LOW_CONFIDENCE strategies)
try:
    sys.path.insert(0, os.path.join(REPO_ROOT, "alpha_engine"))
    from auto_tuner import (
        PERMANENTLY_KILLED as _PERMANENTLY_KILLED,
        get_strategy_confidence_multiplier as _get_conf_mult,
    )
    sys.path.pop(0)
except Exception:
    _PERMANENTLY_KILLED = set()
    def _get_conf_mult(strategy_name):
        return 1.0

# Import elite scorer to score non-crypto picks immediately after bridge runs
try:
    sys.path.insert(0, os.path.join(REPO_ROOT, "alpha_engine"))
    from elite_scorer import enrich_picks_with_elite_score as _enrich_elite
    sys.path.pop(0)
    _ELITE_SCORER_AVAILABLE = True
except Exception as _elite_err:
    _ELITE_SCORER_AVAILABLE = False
    def _enrich_elite(picks):  # noqa: E301
        return picks


def load_json(path):
    """Load JSON file, return None if missing or invalid."""
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"  WARNING: Failed to load {path}: {e}")
        return None


def save_json(path, data):
    """Save JSON with UTF-8 encoding."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def normalize_pick(raw, source_system):
    """
    Normalize a pick dict to match the alpha_engine active_picks format exactly.

    Required fields:
      id, strategy, symbol, category, signal_type, direction,
      entry_price, entry_date, timestamp,
      take_profit, stop_loss, confidence,
      risk_reward, reason, status,
      source_system, forward_test_only, ml_score,
      exit_price, exit_date, pnl_pct, hold_days
    """
    if not isinstance(raw, dict):
        return None

    entry_price = raw.get("entry_price", 0)
    if not entry_price or entry_price <= 0:
        return None

    now_iso = datetime.now(timezone.utc).isoformat()

    # Determine category - normalize to lowercase
    category = (raw.get("category") or raw.get("asset_class") or "unknown").lower()
    # Map common variants
    cat_map = {"equities": "equity", "stocks": "equity", "stock": "equity",
               "bonds": "bond", "commodities": "commodity"}
    category = cat_map.get(category, category)

    confidence = raw.get("confidence", 0.5)
    if confidence is None:
        confidence = 0.5

    # Apply auto_tuner confidence multiplier (0.4x for LOW_CONFIDENCE strategies)
    strategy_name = raw.get("strategy", "unknown")
    if strategy_name in _PERMANENTLY_KILLED:
        return None

    multiplier = _get_conf_mult(strategy_name)
    confidence = float(confidence) * multiplier

    pick = {
        "id": raw.get("id", f"{source_system}::{raw.get('symbol', 'UNK')}::{datetime.now(timezone.utc).strftime('%Y-%m-%d_%H%M')}"),
        "strategy": strategy_name,
        "symbol": raw.get("symbol", ""),
        "category": category,
        "signal_type": raw.get("signal_type", "BUY"),
        "direction": raw.get("direction", "LONG"),
        "entry_price": float(entry_price),
        "entry_date": raw.get("entry_date", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
        "timestamp": raw.get("timestamp", now_iso),
        "take_profit": raw.get("take_profit"),
        "stop_loss": raw.get("stop_loss"),
        "confidence": round(confidence, 3),
        "ml_score": round(float(raw.get("ml_score", confidence)) * multiplier, 3),
        "risk_reward": float(raw.get("risk_reward", 0) or 0),
        "reason": raw.get("reason", ""),
        "status": raw.get("status", "OPEN"),
        "source_system": raw.get("source_system", source_system),
        "forward_test_only": raw.get("forward_test_only", True),
        "exit_price": raw.get("exit_price"),
        "exit_date": raw.get("exit_date"),
        "closed_at": raw.get("closed_at") or raw.get("exit_date"),  # Required for dashboard export
        "pnl_pct": raw.get("pnl_pct"),
        "hold_days": raw.get("hold_days"),
    }

    # Preserve extra fields that exist in the source
    for extra_key in ("asset_class", "forward_trades", "forward_wr", "forward_validated",
                      "source_strategy_type", "extra", "pnl_dollar"):
        if extra_key in raw:
            pick[extra_key] = raw[extra_key]

    return pick


def load_multi_asset_picks():
    """Load picks from multi_asset_picks.json."""
    data = load_json(MULTI_ASSET_FILE)
    if not data:
        return []
    picks = data.get("picks", [])
    print(f"  Multi-asset scraper: {len(picks)} picks")
    return [normalize_pick(p, "multi_asset_copytrader") for p in picks if p]


def load_cta_picks():
    """Load picks from cta_picks.json."""
    data = load_json(CTA_FILE)
    if not data:
        return []
    picks = data.get("picks", [])
    print(f"  CTA replicator: {len(picks)} picks")
    return [normalize_pick(p, "cta_replicator") for p in picks if p]


def load_dna_clone_picks():
    """
    Load OPEN positions from copytrader_test_portfolios.json.
    These are DNA-cloned trader positions.
    """
    data = load_json(TEST_PORTFOLIOS_FILE)
    if not data:
        return []

    portfolios = data.get("portfolios", {})
    picks = []
    for trader_id, portfolio in portfolios.items():
        positions = portfolio.get("test_positions", [])
        strategy_name = portfolio.get("strategy_name", f"dna_clone_{trader_id[:8]}")
        platform = portfolio.get("platform", "unknown")

        for pos in positions:
            if pos.get("status") != "OPEN":
                continue
            # Convert DNA clone position to pick format
            instrument = pos.get("instrument", "")
            symbol = instrument.replace("-SWAP", "").replace("-", "")
            direction = (pos.get("direction") or "long").upper()

            raw = {
                "id": f"copytrader_dna::{symbol}::{trader_id[:8]}::{datetime.now(timezone.utc).strftime('%Y-%m-%d_%H%M')}",
                "strategy": strategy_name,
                "symbol": symbol,
                "category": "crypto",  # DNA clones are currently crypto only
                "signal_type": "BUY" if direction == "LONG" else "SELL",
                "direction": direction,
                "entry_price": pos.get("entry_price", 0),
                "entry_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "take_profit": pos.get("tp_price"),
                "stop_loss": pos.get("sl_price"),
                "confidence": 0.6,
                "risk_reward": 1.5,
                "reason": f"DNA clone of {platform} trader {trader_id[:8]} | {instrument}",
                "status": "OPEN",
                "source_system": "copytrader_dna",
                "forward_test_only": True,
            }
            picks.append(normalize_pick(raw, "copytrader_dna"))

    open_count = len(picks)
    if open_count > 0:
        print(f"  DNA clones: {open_count} open positions")
    else:
        print(f"  DNA clones: no open positions")
    return picks


def merge_into_active_picks(new_picks):
    """
    Load active_picks.json, remove stale managed picks, append new ones.
    Returns (merged_list, stats_dict).
    """
    existing = load_json(ACTIVE_PICKS_FILE)
    if not isinstance(existing, list):
        existing = []

    # Count existing by source before removal
    existing_crypto = sum(1 for p in existing if isinstance(p, dict)
                         and not any(p.get("source_system", "").startswith(s) for s in MANAGED_SOURCES))
    stale_count = len(existing) - existing_crypto

    # Remove stale managed picks
    kept = [p for p in existing if isinstance(p, dict)
            and not any(p.get("source_system", "").startswith(s) for s in MANAGED_SOURCES)]

    # Filter out None from normalization failures
    valid_new = [p for p in new_picks if p is not None]

    # Deduplicate new picks by ID
    seen_ids = {p.get("id") for p in kept if p.get("id")}
    deduped_new = []
    for p in valid_new:
        pid = p.get("id", "")
        if pid and pid not in seen_ids:
            seen_ids.add(pid)
            deduped_new.append(p)

    merged = kept + deduped_new

    stats = {
        "existing_before": len(existing),
        "stale_removed": stale_count,
        "crypto_kept": existing_crypto,
        "new_added": len(deduped_new),
        "total_after": len(merged),
    }

    return merged, stats


def update_audit_dashboard(all_picks):
    """
    Write non-crypto picks to audit_dashboard/data/forex_futures_picks.json.
    """
    non_crypto = [p for p in all_picks if isinstance(p, dict)
                  and p.get("category") not in ("crypto", None)]

    # Deduplicate by ID
    seen = set()
    unique = []
    for p in non_crypto:
        pid = p.get("id", "")
        if pid and pid not in seen:
            seen.add(pid)
            unique.append(p)

    by_category = {}
    for p in unique:
        cat = p.get("category", "other")
        by_category[cat] = by_category.get(cat, 0) + 1

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_picks": len(unique),
        "forex_count": by_category.get("forex", 0),
        "futures_count": by_category.get("futures", 0),
        "commodity_count": by_category.get("commodity", 0),
        "stock_count": by_category.get("equity", 0) + by_category.get("stock", 0),
        "bond_count": by_category.get("bond", 0),
        "by_category": by_category,
        "picks": unique,
    }

    save_json(AUDIT_FOREX_FILE, output)
    return output


def run_bridge():
    """Main bridge execution."""
    print("=" * 60)
    print("Multi-Asset Bridge: Merging picks into alpha_engine")
    print("=" * 60)

    # Step 1: Load all source picks
    print("\n[1/4] Loading source picks...")
    all_new = []
    all_new.extend(load_multi_asset_picks())
    all_new.extend(load_cta_picks())
    all_new.extend(load_dna_clone_picks())

    valid_new = [p for p in all_new if p is not None]
    print(f"\n  Total normalized picks: {len(valid_new)}")

    if not valid_new:
        print("\n  WARNING: No picks to merge. Check source files.")
        return

    # Step 2: Merge into active_picks.json
    print("\n[2/4] Merging into active_picks.json...")
    merged, stats = merge_into_active_picks(valid_new)

    # Step 2b: Apply elite scoring to non-crypto picks so scores survive the
    # 30-min bridge refresh cycle (alpha-engine-live only runs on git push).
    if _ELITE_SCORER_AVAILABLE:
        print("  Applying elite scoring to non-crypto picks...")
        non_crypto_idx = [
            i for i, p in enumerate(merged)
            if str(p.get("asset_class", "") or p.get("category", "")).lower()
            not in ("crypto", "")
        ]
        non_crypto_subset = [merged[i] for i in non_crypto_idx]
        try:
            scored = _enrich_elite(non_crypto_subset)
            for idx, sp in zip(non_crypto_idx, scored):
                merged[idx] = sp
            n_scored = sum(1 for p in scored if p.get("elite_score") is not None)
            print(f"  Scored {n_scored}/{len(scored)} non-crypto picks")
        except Exception as _se:
            print(f"  WARNING: elite scoring failed: {_se}")

    save_json(ACTIVE_PICKS_FILE, merged)

    # Mirror non-crypto picks to multi_asset/data/ so dashboard_generator's 'multi_asset' source
    # stays fresh (the v1 scanner was disabled 2026-03-16; this bridge is the replacement)
    non_crypto_picks = [p for p in valid_new if str(p.get("asset_class", "") or p.get("category", "")).lower()
                        not in ("crypto", "")]
    save_json(MULTI_ASSET_MIRROR_FILE, non_crypto_picks)
    save_json(MULTI_ASSET_PICKS_MIRROR, non_crypto_picks)
    print(f"  Mirrored {len(non_crypto_picks)} non-crypto picks to multi_asset/data/")

    print(f"  Before: {stats['existing_before']} picks")
    print(f"  Stale removed: {stats['stale_removed']}")
    print(f"  Crypto kept: {stats['crypto_kept']}")
    print(f"  New added: {stats['new_added']}")
    print(f"  Total after: {stats['total_after']}")

    # Step 3: Update audit dashboard
    print("\n[3/4] Updating audit dashboard forex/futures picks...")
    audit_output = update_audit_dashboard(merged)
    print(f"  Total non-crypto picks: {audit_output['total_picks']}")
    print(f"    Forex: {audit_output['forex_count']}")
    print(f"    Futures: {audit_output['futures_count']}")
    print(f"    Commodity: {audit_output['commodity_count']}")
    print(f"    Stock/Equity: {audit_output['stock_count']}")
    print(f"    Bond: {audit_output.get('bond_count', 0)}")

    # Step 4: Summary
    print("\n[4/4] Summary")
    by_source = {}
    for p in merged:
        src = p.get("source_system", "unknown")
        by_source[src] = by_source.get(src, 0) + 1
    for src, count in sorted(by_source.items()):
        print(f"  {src}: {count} picks")

    by_cat = {}
    for p in merged:
        cat = p.get("category", "unknown")
        by_cat[cat] = by_cat.get(cat, 0) + 1
    print(f"\n  By category:")
    for cat, count in sorted(by_cat.items()):
        print(f"    {cat}: {count}")

    print(f"\n  Saved: {ACTIVE_PICKS_FILE}")
    print(f"  Saved: {AUDIT_FOREX_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    run_bridge()
