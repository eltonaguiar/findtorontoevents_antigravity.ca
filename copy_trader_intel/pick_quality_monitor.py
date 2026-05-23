#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pick Quality Monitor: Validates non-crypto picks and computes quality metrics.

Checks:
  - entry_price > 0
  - TP on correct side (LONG: TP > entry, SHORT: TP < entry)
  - SL on correct side (LONG: SL < entry, SHORT: SL > entry)
  - risk_reward >= 1.0
  - confidence >= 0.50
  - Forex: TP < 5% of entry, SL < 3%
  - Commodity: TP < 15%, SL < 10%
  - Stock/Equity: TP < 30%, SL < 20%

Outputs: copy_trader_intel/data/pick_quality_report.json

Run: python copy_trader_intel/pick_quality_monitor.py
"""

import json
import os
import sys
from datetime import datetime, timezone

# Windows UTF-8 fix
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)

ACTIVE_PICKS_FILE = os.path.join(REPO_ROOT, "alpha_engine", "data", "active_picks.json")
MULTI_ASSET_MIRROR_FILE = os.path.join(REPO_ROOT, "multi_asset", "data", "active_picks.json")
QUALITY_REPORT_FILE = os.path.join(SCRIPT_DIR, "data", "pick_quality_report.json")

# Distance thresholds by category (max TP distance %, max SL distance %)
DISTANCE_LIMITS = {
    "forex":     {"tp_max_pct": 5.0,  "sl_max_pct": 3.0},
    "commodity": {"tp_max_pct": 15.0, "sl_max_pct": 10.0},
    "equity":    {"tp_max_pct": 30.0, "sl_max_pct": 20.0},
    "stock":     {"tp_max_pct": 30.0, "sl_max_pct": 20.0},
    "bond":      {"tp_max_pct": 10.0, "sl_max_pct": 5.0},
    "futures":   {"tp_max_pct": 20.0, "sl_max_pct": 15.0},
}


def load_json(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"  WARNING: Failed to load {path}: {e}")
        return None


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def pct_distance(a, b):
    """Percentage distance from a to b: abs(b - a) / a * 100."""
    if not a or a == 0:
        return 999.0
    return abs(b - a) / abs(a) * 100.0


def validate_pick(pick):
    """
    Validate a single non-crypto pick. Returns list of issue strings (empty = valid).
    """
    issues = []
    category = (pick.get("category") or "").lower()
    direction = (pick.get("direction") or "LONG").upper()
    entry = pick.get("entry_price", 0)
    tp = pick.get("take_profit")
    sl = pick.get("stop_loss")
    rr = pick.get("risk_reward", 0) or 0
    conf = pick.get("confidence", 0) or 0

    # Basic checks
    if not entry or entry <= 0:
        issues.append("entry_price <= 0 or missing")
        return issues  # Can't validate further

    # TP side check
    if tp is not None and tp > 0:
        if direction == "LONG" and tp <= entry:
            issues.append(f"LONG but TP ({tp}) <= entry ({entry})")
        elif direction == "SHORT" and tp >= entry:
            issues.append(f"SHORT but TP ({tp}) >= entry ({entry})")
    else:
        issues.append("take_profit missing or zero")

    # SL side check
    if sl is not None and sl > 0:
        if direction == "LONG" and sl >= entry:
            issues.append(f"LONG but SL ({sl}) >= entry ({entry})")
        elif direction == "SHORT" and sl <= entry:
            issues.append(f"SHORT but SL ({sl}) <= entry ({entry})")
    else:
        issues.append("stop_loss missing or zero")

    # Risk/reward minimum
    if rr < 1.0:
        issues.append(f"risk_reward {rr:.2f} < 1.0 minimum")

    # Confidence minimum
    if conf < 0.50:
        issues.append(f"confidence {conf:.2f} < 0.50 minimum")

    # Category-specific distance checks
    limits = DISTANCE_LIMITS.get(category)
    if limits and tp is not None and tp > 0:
        tp_dist = pct_distance(entry, tp)
        if tp_dist > limits["tp_max_pct"]:
            issues.append(f"TP distance {tp_dist:.1f}% exceeds {category} max {limits['tp_max_pct']}%")

    if limits and sl is not None and sl > 0:
        sl_dist = pct_distance(entry, sl)
        if sl_dist > limits["sl_max_pct"]:
            issues.append(f"SL distance {sl_dist:.1f}% exceeds {category} max {limits['sl_max_pct']}%")

    return issues


def _mirror_commodity_summary():
    """Counts commodity-class rows on multi_asset mirror (dashboard-style hints)."""
    data = load_json(MULTI_ASSET_MIRROR_FILE)
    if not isinstance(data, list):
        return None
    n_commod = 0
    for p in data:
        if not isinstance(p, dict):
            continue
        ac = (p.get("asset_class") or "").upper()
        cat = (p.get("category") or "").upper()
        sym = (p.get("symbol") or "").upper()
        if (
            ac == "COMMODITY"
            or cat == "COMMODITY"
            or cat == "COMMODITIES"
            or sym.startswith("XAG")
            or sym.startswith("XAU")
        ):
            n_commod += 1
    return {
        "path": MULTI_ASSET_MIRROR_FILE,
        "total_picks": len(data),
        "commodity_class_count": n_commod,
    }


def compute_quality_metrics(all_picks, flagged_picks):
    """Compute aggregate quality metrics."""
    non_crypto = [p for p in all_picks if isinstance(p, dict)
                  and p.get("category") not in ("crypto", None)]

    if not non_crypto:
        return {
            "total_non_crypto": 0,
            "flagged_count": 0,
            "pass_rate": 0,
            "avg_confidence": 0,
            "avg_risk_reward": 0,
            "direction_balance": {},
            "freshness_hours": None,
            "coverage": {},
        }

    # Confidence and RR averages
    confs = [p.get("confidence", 0) for p in non_crypto if p.get("confidence")]
    rrs = [p.get("risk_reward", 0) for p in non_crypto if p.get("risk_reward")]
    avg_conf = sum(confs) / len(confs) if confs else 0
    avg_rr = sum(rrs) / len(rrs) if rrs else 0

    # Direction balance
    longs = sum(1 for p in non_crypto if (p.get("direction") or "").upper() == "LONG")
    shorts = sum(1 for p in non_crypto if (p.get("direction") or "").upper() == "SHORT")
    direction_balance = {
        "long": longs,
        "short": shorts,
        "ratio": f"{longs}L/{shorts}S",
        "pct_long": round(longs / len(non_crypto) * 100, 1) if non_crypto else 0,
    }

    # Freshness: hours since most recent pick
    timestamps = []
    for p in non_crypto:
        ts = p.get("timestamp")
        if ts:
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                timestamps.append(dt)
            except (ValueError, TypeError):
                pass

    freshness_hours = None
    if timestamps:
        latest = max(timestamps)
        delta = datetime.now(timezone.utc) - latest
        freshness_hours = round(delta.total_seconds() / 3600, 1)

    # Coverage: which asset classes have picks
    categories = {}
    for p in non_crypto:
        cat = p.get("category", "unknown")
        categories[cat] = categories.get(cat, 0) + 1

    flagged_ids = {f["id"] for f in flagged_picks}
    pass_count = sum(1 for p in non_crypto if p.get("id") not in flagged_ids)

    return {
        "total_non_crypto": len(non_crypto),
        "flagged_count": len(flagged_picks),
        "pass_count": pass_count,
        "pass_rate": round(pass_count / len(non_crypto) * 100, 1) if non_crypto else 0,
        "avg_confidence": round(avg_conf, 3),
        "avg_risk_reward": round(avg_rr, 2),
        "direction_balance": direction_balance,
        "freshness_hours": freshness_hours,
        "coverage": categories,
    }


def run_quality_monitor():
    """Main quality monitoring execution."""
    print("=" * 60)
    print("Pick Quality Monitor: Validating non-crypto picks")
    print("=" * 60)

    # Load picks
    all_picks = load_json(ACTIVE_PICKS_FILE)
    if not isinstance(all_picks, list):
        print("  ERROR: Cannot load active_picks.json")
        return

    non_crypto = [p for p in all_picks if isinstance(p, dict)
                  and p.get("category") not in ("crypto", None)]
    crypto_count = len(all_picks) - len(non_crypto)

    print(f"\n  Total picks: {len(all_picks)}")
    print(f"  Crypto: {crypto_count}")
    print(f"  Non-crypto to validate: {len(non_crypto)}")

    # Validate each non-crypto pick
    flagged = []
    for pick in non_crypto:
        issues = validate_pick(pick)
        if issues:
            flagged.append({
                "id": pick.get("id", "unknown"),
                "symbol": pick.get("symbol", "?"),
                "category": pick.get("category", "?"),
                "strategy": pick.get("strategy", "?"),
                "direction": pick.get("direction", "?"),
                "issues": issues,
            })

    # Compute metrics
    metrics = compute_quality_metrics(all_picks, flagged)

    # Build report
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "metrics": metrics,
        "flagged_picks": flagged,
        "thresholds_used": DISTANCE_LIMITS,
        "multi_asset_mirror": _mirror_commodity_summary(),
    }

    save_json(QUALITY_REPORT_FILE, report)

    # Console summary
    print(f"\n  Quality Metrics:")
    print(f"    Pass rate: {metrics['pass_rate']}% ({metrics['pass_count']}/{metrics['total_non_crypto']})")
    print(f"    Avg confidence: {metrics['avg_confidence']}")
    print(f"    Avg risk/reward: {metrics['avg_risk_reward']}")
    print(f"    Direction balance: {metrics['direction_balance'].get('ratio', 'N/A')}")
    print(f"    Freshness: {metrics['freshness_hours']}h since last pick")
    print(f"    Asset coverage: {metrics['coverage']}")

    if flagged:
        print(f"\n  Flagged picks ({len(flagged)}):")
        for f in flagged[:10]:  # Show first 10
            print(f"    {f['symbol']} ({f['category']}/{f['direction']}): {'; '.join(f['issues'][:2])}")
        if len(flagged) > 10:
            print(f"    ... and {len(flagged) - 10} more")
    else:
        print(f"\n  All {metrics['total_non_crypto']} non-crypto picks passed validation!")

    print(f"\n  Report saved: {QUALITY_REPORT_FILE}")
    print("=" * 60)

    return report


if __name__ == "__main__":
    run_quality_monitor()
