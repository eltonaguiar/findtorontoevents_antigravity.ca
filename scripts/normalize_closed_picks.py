#!/usr/bin/env python3
"""
Data Quality Normalizer — Standardize Closed Picks
====================================================
Mercury AI / Inception Labs Recommendation §3.4:
  1. Normalize PnL units to single base currency (USDT)
  2. Add "status" field (closed, canceled, stale) to closed_picks.json
  3. Standardize exit reasons across all systems

Scans all closed_picks.json files, normalizes them in-place, and
generates a data_quality_report.json with findings.

Created: 2026-03-03 18:27 EST
Source: Mercury AI Feedback (ANTIGRAVITY_PLAN_MERCURYFEEDBACK.MD)
"""

import json
import logging
import pathlib
import copy
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("normalize_closed_picks")

# ── Paths ──────────────────────────────────────────────────
BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
REPORT_PATH = BASE_DIR / "data" / "data_quality_report.json"

# ── Systems to scan ───────────────────────────────────────
CLOSED_PICK_FILES = [
    BASE_DIR / "mercury2" / "data" / "closed_picks.json",
    BASE_DIR / "alpha_engine" / "data" / "closed_picks.json",
    BASE_DIR / "battleground" / "data" / "closed_picks.json",
    BASE_DIR / "KIMI_RISEOFTHECLAW" / "data" / "closed_picks.json",
    BASE_DIR / "crypto_signal_engine" / "data" / "closed_picks.json",
    BASE_DIR / "breakout_arena" / "approach_a_sr_breakout" / "data" / "closed_picks.json",
    BASE_DIR / "breakout_arena" / "approach_b_vol_breakout" / "data" / "closed_picks.json",
    BASE_DIR / "ml_battleground" / "data" / "closed_picks.json",
    BASE_DIR / "baby_strategies" / "data" / "closed_picks.json",
]

# ── Standardized Exit Reasons ─────────────────────────────
EXIT_REASON_MAP = {
    # TP-related
    "tp_hit": "TP_HIT",
    "tp": "TP_HIT",
    "take_profit": "TP_HIT",
    "take-profit": "TP_HIT",
    "target_reached": "TP_HIT",
    "target": "TP_HIT",
    "profit_target": "TP_HIT",
    "profit": "TP_HIT",

    # SL-related
    "sl_hit": "SL_HIT",
    "sl": "SL_HIT",
    "stop_loss": "SL_HIT",
    "stop-loss": "SL_HIT",
    "stopped_out": "SL_HIT",
    "stop": "SL_HIT",

    # Time-based
    "expired": "EXPIRED",
    "timeout": "EXPIRED",
    "time_exit": "EXPIRED",
    "time_expiry": "EXPIRED",

    # Manual
    "manual": "MANUAL_CLOSE",
    "manual_close": "MANUAL_CLOSE",

    # Partial
    "partial": "PARTIAL_CLOSE",
    "partial_close": "PARTIAL_CLOSE",
    "partial_tp": "PARTIAL_TP",

    # Trailing
    "trailing_stop": "TRAILING_STOP",
    "trail": "TRAILING_STOP",

    # Liquidation
    "liquidated": "LIQUIDATED",
    "liquidation": "LIQUIDATED",

    # Canceled
    "canceled": "CANCELED",
    "cancelled": "CANCELED",
    "not_filled": "CANCELED",
}

# ── Standardized Status Values ────────────────────────────
VALID_STATUSES = {"closed", "canceled", "stale", "expired", "active"}


def _load_json(path: pathlib.Path):
    """Load JSON file safely."""
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log.warning("Failed to load %s: %s", path, e)
        return None


def _extract_picks_and_key(data) -> tuple[list, str | None]:
    """Extract picks list and the key used to find them."""
    if isinstance(data, list):
        return data, None
    if isinstance(data, dict):
        for key in ("picks", "closed_picks", "trades", "results", "signals"):
            if key in data and isinstance(data[key], list):
                return data[key], key
        # If dict has nested dicts, might be keyed by symbol
        if all(isinstance(v, dict) for v in data.values()):
            # Flatten
            all_picks = []
            for symbol, picks_or_pick in data.items():
                if isinstance(picks_or_pick, list):
                    all_picks.extend(picks_or_pick)
                elif isinstance(picks_or_pick, dict):
                    all_picks.append(picks_or_pick)
            return all_picks, None
    return [], None


def _normalize_exit_reason(raw: str | None) -> str:
    """Normalize exit reason to standard value."""
    if not raw:
        return "UNKNOWN"
    raw_lower = str(raw).lower().strip()
    return EXIT_REASON_MAP.get(raw_lower, raw.upper().replace(" ", "_"))


def _determine_status(pick: dict) -> str:
    """Determine status from pick data."""
    existing = str(pick.get("status", "")).lower()
    if existing in VALID_STATUSES:
        return existing

    exit_reason = _normalize_exit_reason(
        pick.get("exit_reason", pick.get("close_reason", ""))
    )

    if exit_reason == "CANCELED":
        return "canceled"
    if exit_reason == "EXPIRED":
        return "expired"
    if exit_reason in ("TP_HIT", "SL_HIT", "MANUAL_CLOSE", "TRAILING_STOP", "LIQUIDATED"):
        return "closed"

    # Check for PnL or exit price
    if pick.get("exit_price") or pick.get("pnl") is not None:
        return "closed"

    return "closed"  # Default to closed for items in closed_picks.json


def _normalize_pnl_field(pick: dict) -> dict:
    """
    Ensure pick has a standardized pnl_usdt field.
    Does NOT modify other fields.
    """
    if "pnl_usdt" in pick:
        return pick

    # Try to compute from existing fields
    pnl = None

    # Direct PnL fields
    for key in ("pnl", "profit", "realized_pnl"):
        val = pick.get(key)
        if val is not None:
            try:
                pnl = float(val)
                break
            except (ValueError, TypeError):
                continue

    # Percentage → USDT conversion
    if pnl is None:
        for key in ("pnl_pct", "pnl_percent", "profit_pct", "return_pct"):
            pct = pick.get(key)
            if pct is not None:
                try:
                    pct = float(pct)
                    entry = float(pick.get("entry_price", 0))
                    size = float(pick.get("size", pick.get("quantity", 1)))
                    if entry > 0:
                        pnl = (pct / 100.0) * entry * size
                    break
                except (ValueError, TypeError):
                    continue

    # Compute from entry/exit
    if pnl is None:
        try:
            entry = float(pick.get("entry_price", 0))
            exit_p = float(pick.get("exit_price", 0))
            size = float(pick.get("size", pick.get("quantity", 1)))
            direction = str(pick.get("direction", "LONG")).upper()
            if entry > 0 and exit_p > 0:
                if direction in ("SHORT", "SELL"):
                    pnl = (entry - exit_p) * size
                else:
                    pnl = (exit_p - entry) * size
        except (ValueError, TypeError):
            pass

    if pnl is not None:
        pick["pnl_usdt"] = round(pnl, 4)

    return pick


def normalize_file(filepath: pathlib.Path) -> dict:
    """
    Normalize a single closed_picks.json file.

    Returns a report dict with statistics.
    """
    data = _load_json(filepath)
    if data is None:
        return {"file": str(filepath), "status": "not_found", "changes": 0}

    picks, key = _extract_picks_and_key(data)
    if not picks:
        return {"file": str(filepath), "status": "empty", "changes": 0}

    changes = 0
    issues = []

    for i, pick in enumerate(picks):
        if not isinstance(pick, dict):
            continue

        original = copy.deepcopy(pick)

        # 1. Normalize exit reason
        raw_exit = pick.get("exit_reason", pick.get("close_reason"))
        normalized_exit = _normalize_exit_reason(raw_exit)
        if raw_exit and normalized_exit != raw_exit:
            pick["exit_reason"] = normalized_exit
            changes += 1

        # 2. Add/normalize status field
        if "status" not in pick or pick["status"] not in VALID_STATUSES:
            pick["status"] = _determine_status(pick)
            changes += 1

        # 3. Normalize PnL to USDT
        if "pnl_usdt" not in pick:
            _normalize_pnl_field(pick)
            if "pnl_usdt" in pick:
                changes += 1

        # 4. Flag data quality issues
        if not pick.get("entry_price"):
            issues.append(f"Pick {i}: missing entry_price")
        if not pick.get("exit_price") and pick.get("status") == "closed":
            issues.append(f"Pick {i}: closed but missing exit_price")
        if pick.get("pnl_usdt") is None and pick.get("status") == "closed":
            issues.append(f"Pick {i}: closed but PnL could not be computed")

    # Save normalized data back
    if changes > 0:
        try:
            if key:
                data[key] = picks
            elif isinstance(data, list):
                data = picks

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
            log.info("Normalized %s — %d changes", filepath.name, changes)
        except Exception as e:
            log.error("Failed to save %s: %s", filepath, e)

    return {
        "file": str(filepath.relative_to(BASE_DIR)),
        "status": "normalized",
        "total_picks": len(picks),
        "changes": changes,
        "issues": issues[:20],  # Cap at 20 issues per file
        "issue_count": len(issues),
    }


def normalize_all():
    """Normalize all closed_picks.json files and generate quality report."""
    now = datetime.now(timezone.utc)
    log.info("Starting data quality normalization at %s", now.isoformat())

    results = []
    total_changes = 0
    total_issues = 0

    for filepath in CLOSED_PICK_FILES:
        result = normalize_file(filepath)
        results.append(result)
        total_changes += result.get("changes", 0)
        total_issues += result.get("issue_count", 0)

    # Generate quality report
    report = {
        "generated_at": now.isoformat(),
        "total_files_scanned": len(CLOSED_PICK_FILES),
        "total_files_found": sum(1 for r in results if r["status"] != "not_found"),
        "total_changes_made": total_changes,
        "total_data_issues": total_issues,
        "normalization_applied": [
            "exit_reason → standardized (TP_HIT, SL_HIT, EXPIRED, etc.)",
            "status field added (closed, canceled, stale, expired)",
            "pnl_usdt field computed from available data",
        ],
        "files": results,
    }

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    log.info("Quality report saved to %s", REPORT_PATH)

    # Print summary
    print("\n" + "=" * 60)
    print("  DATA QUALITY NORMALIZATION REPORT")
    print(f"  Generated: {now.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 60)
    print(f"  Files scanned:  {len(CLOSED_PICK_FILES)}")
    print(f"  Files found:    {sum(1 for r in results if r['status'] != 'not_found')}")
    print(f"  Total changes:  {total_changes}")
    print(f"  Data issues:    {total_issues}")
    print()

    for result in results:
        status_icon = "✅" if result["status"] == "normalized" else "⚪" if result["status"] == "not_found" else "📄"
        print(
            f"  {status_icon} {result['file']:60s} | "
            f"Changes: {result.get('changes', 0)} | "
            f"Issues: {result.get('issue_count', 0)}"
        )

    print("\n" + "=" * 60)
    return report


if __name__ == "__main__":
    normalize_all()
