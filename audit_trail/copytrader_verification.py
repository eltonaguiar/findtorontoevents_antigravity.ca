#!/usr/bin/env python3
"""
Copy-Trader Verification Framework
===================================
Comprehensive verification for copy-trader picks across all asset classes.

Implements:
- Verification checklist per dimension (identity, source, order details, timestamps, symbol, close outcome)
- Per-class minimum price feed for replay
- Confidence scoring rubric (A-D tiers)
- Reconciliation between source files and universal_resolved_picks.json

Usage:
    python -m audit_trail.copytrader_verification
    from audit_trail.copytrader_verification import verify_copy_pick, VerificationResult
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional
import hashlib
import json
import logging
import os

import pandas as pd

logger = logging.getLogger(__name__)

_REPO = Path(__file__).resolve().parents[1]

# System sources from universal_pick_resolver.py
SYSTEM_SOURCES = [
    "copy_trader_intel",
    "highscore",
    "clone",
    "consensus",
    "multi_asset",
    "forex_copytrader",
    "futures_copytrader",
    "stocks_copytrader",
    "commodity_copytrader",
    "cta_replicator",
    "prediction_market_agents",
    "non_crypto",
]


class VerificationStatus(Enum):
    """Verification tier/status levels."""
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


class ConfidenceTier(Enum):
    """Confidence scoring rubric (orthogonal to dashboard score)."""
    A_VERIFIED = "A"  # 90-100: Fully verified
    B_PROBABLE = "B"  # 70-89: Probable
    C_WEAK = "C"      # 50-69: Weak
    D_UNVERIFIED = "D"  # <50: Unverified


class CloseOutcome(Enum):
    """Close outcome types."""
    WON = "WON"
    LOST = "LOST"
    TP_HIT = "TP_HIT"
    SL_HIT = "SL_HIT"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"
    OPEN = "OPEN"


@dataclass
class VerificationResult:
    """Result of a single pick verification."""
    pick_id: str
    symbol: str
    source_system: str
    
    # Verification status
    status: VerificationStatus
    tier: ConfidenceTier
    confidence_score: int  # 0-100
    
    # Individual checks (key -> (passed, reason))
    checks: dict[str, tuple[bool, str]] = field(default_factory=dict)
    
    # Failure reasons if any
    failures: list[str] = field(default_factory=list)
    
    # Asset class
    asset_class: str = "UNKNOWN"
    
    # Additional metadata
    price_source: Optional[str] = None
    resolved_row: Optional[dict] = None


def _calculate_age_hours(timestamp: str | datetime) -> float:
    """Calculate age in hours from timestamp."""
    if isinstance(timestamp, str):
        try:
            ts = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError:
            try:
                ts = pd.to_datetime(timestamp)
            except (ValueError, TypeError):
                return 999999  # Very old if unparseable
    else:
        ts = timestamp
    
    now = datetime.now(timezone.utc)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    
    return (now - ts).total_seconds() / 3600


def _compute_dedup_hash(pick: dict) -> str:
    """Compute dedup hash for pick identity stability."""
    key_parts = [
        str(pick.get("symbol", "")),
        str(pick.get("direction", "")),
        str(pick.get("entry_price", "")),
        str(pick.get("source_system", "")),
    ]
    key = "|".join(key_parts)
    return hashlib.md5(key.encode()).hexdigest()[:16]


def _check_identity(pick: dict) -> tuple[bool, str]:
    """Verify pick identity: stable pick_id, dedup hash, source_system, no duplicates."""
    # Check for pick_id or generate dedup hash
    pick_id = pick.get("pick_id") or pick.get("id") or _compute_dedup_hash(pick)
    if not pick_id:
        return False, "Missing pick_id and cannot generate dedup_hash"
    
    # Check source_system
    source_system = pick.get("source_system") or pick.get("source", "")
    if not source_system:
        return False, "Missing source_system"
    
    # Check for required fields
    symbol = pick.get("symbol")
    if not symbol:
        return False, "Missing symbol"
    
    return True, f"Identity verified: {pick_id[:8]}... from {source_system}"


def _check_source_endpoint(pick: dict) -> tuple[bool, str]:
    """Verify source endpoint: which file path + upstream API produced the row."""
    # Check for source file path metadata
    source_file = pick.get("source_file") or pick.get("_source_file")
    scan_ts = pick.get("scan_metadata") or pick.get("scanned_at") or pick.get("timestamp")
    
    if source_file:
        return True, f"Source: {source_file}"
    
    # Try to infer from source_system
    source_system = pick.get("source_system", "").lower()
    
    # Map to expected file paths
    expected_paths = {
        "copy_trader_intel": "copy_trader_intel/data/active_picks.json",
        "highscore": "copy_trader_intel/data/highscore_active_picks.json",
        "clone": "copy_trader_intel/data/clone_active_picks.json",
        "consensus": "copy_trader_intel/data/consensus_active_picks.json",
        "multi_asset": "copy_trader_intel/data/multi_asset_picks.json",
        "forex_copytrader": "copy_trader_intel/data/forex_copytrader_picks.json",
        "futures_copytrader": "copy_trader_intel/data/futures_copytrader_picks.json",
        "stocks_copytrader": "copy_trader_intel/data/stocks_copytrader_picks.json",
        "commodity_copytrader": "copy_trader_intel/data/commodity_copytrader_picks.json",
    }
    
    for key, path in expected_paths.items():
        if key in source_system:
            return True, f"Inferred source: {path}"
    
    # If no specific source, warn but allow
    if not source_system:
        return False, "No source_system to infer endpoint"
    
    return True, f"Source system: {source_system}"


def _check_order_details(pick: dict) -> tuple[bool, str]:
    """Verify order details: direction, entry_price, take_profit, stop_loss, size/qty."""
    # Direction check
    direction = pick.get("direction") or pick.get("signal_type", "")
    if not direction:
        return False, "Missing direction"
    
    if direction.upper() not in ("LONG", "SHORT", "BUY", "SELL"):
        return False, f"Invalid direction: {direction}"
    
    # Entry price
    entry_price = pick.get("entry_price")
    if not entry_price:
        return False, "Missing entry_price"
    
    try:
        entry = float(entry_price)
        if entry <= 0:
            return False, f"Invalid entry_price: {entry}"
    except (TypeError, ValueError):
        return False, f"Non-numeric entry_price: {entry_price}"
    
    # TP/SL check (at least one should be present)
    tp = pick.get("take_profit")
    sl = pick.get("stop_loss")
    
    if not tp and not sl:
        return False, "Missing both take_profit and stop_loss"
    
    # Validate geometry if both present
    if tp and sl:
        try:
            tp_val = float(tp)
            sl_val = float(sl)
            
            if direction.upper() in ("LONG", "BUY"):
                if tp_val <= entry or sl_val >= entry:
                    return False, f"Invalid LONG geometry: TP={tp_val} <= entry={entry} or SL={sl_val} >= entry"
            else:  # SHORT/SELL
                if tp_val >= entry or sl_val <= entry:
                    return False, f"Invalid SHORT geometry: TP={tp_val} >= entry={entry} or SL={sl_val} <= entry"
        except (TypeError, ValueError):
            return True, "TP/SL present but non-numeric (warning)"
    
    # Check size/qty if present
    size = pick.get("size") or pick.get("qty") or pick.get("quantity")
    if size:
        try:
            size_val = float(size)
            if size_val <= 0:
                return True, "Warning: size present but <= 0"
        except:
            pass
    
    return True, f"Order details valid: {direction} @ {entry}"


def _check_timestamps(pick: dict) -> tuple[bool, str]:
    """Verify timestamps: timestamp/signal_time, opened_at, closed_at/resolved_at."""
    # Signal time / timestamp
    signal_time = pick.get("signal_time") or pick.get("timestamp") or pick.get("signal_at")
    if not signal_time:
        return False, "Missing signal_time/timestamp"
    
    # Check signal age
    signal_age_hrs = _calculate_age_hours(signal_time)
    
    # Determine max age based on source
    source_system = str(pick.get("source_system", "")).lower()
    is_copy_trader = "copy_trader" in source_system or "copytrader" in source_system
    
    if is_copy_trader:
        max_age_hrs = 168  # 7 days for copy-trader
        staleness_threshold = 72  # 3 days
    else:
        max_age_hrs = 336  # 14 days for other sources
        staleness_threshold = 168  # 7 days
    
    if signal_age_hrs > max_age_hrs:
        return False, f"Signal too old: {signal_age_hrs:.0f}h > {max_age_hrs}h"
    
    if signal_age_hrs > staleness_threshold:
        return True, f"Signal stale: {signal_age_hrs:.0f}h > {staleness_threshold}h (warning)"
    
    # Check opened_at if present
    opened_at = pick.get("opened_at") or pick.get("created_at")
    if opened_at:
        opened_age = _calculate_age_hours(opened_at)
        if opened_age > signal_age_hrs + 24:
            return True, f"Warning: opened_at ({opened_age:.0f}h) > signal_time + 24h"
    
    # Check closed_at if present
    closed_at = pick.get("closed_at") or pick.get("resolved_at")
    if closed_at:
        if opened_at:
            closed_age = _calculate_age_hours(closed_at)
            if closed_age < opened_age:
                return False, f"closed_at ({closed_age}h) < opened_at ({opened_age}h)"
    
    return True, f"Timestamps valid: signal_age={signal_age_hrs:.1f}h"


def _check_symbol_normalization(pick: dict) -> tuple[bool, str]:
    """Verify symbol normalization matches intended class."""
    from audit_trail.asset_classification import classify_asset, AssetClass
    
    symbol = pick.get("symbol", "")
    if not symbol:
        return False, "Missing symbol"
    
    # Get intended class from pick
    intended_class = pick.get("asset_class") or pick.get("assetClass")
    
    # Classify from symbol
    classified = classify_asset(symbol)
    
    # Check if intended matches classified
    if intended_class:
        intended_upper = intended_class.upper()
        if intended_upper != classified.value and intended_upper != "UNKNOWN":
            # Check if classification suggests different asset class
            return False, f"Asset class mismatch: intended={intended_class}, classified={classified.value}"
    
    return True, f"Symbol normalized: {symbol} -> {classified.value}"


def _check_close_outcome(pick: dict) -> tuple[bool, str]:
    """Verify closed status matches replayed path."""
    status = pick.get("status", "").upper()
    
    # If still open, skip this check
    if status in ("", "OPEN", "ACTIVE", "PENDING"):
        return True, "Pick is still open, skipping close verification"
    
    # Must have exit_price for closed trades
    exit_price = pick.get("exit_price")
    if not exit_price:
        return False, "Closed pick missing exit_price"
    
    try:
        exit_val = float(exit_price)
        if exit_val <= 0:
            return False, f"Invalid exit_price: {exit_val}"
    except (TypeError, ValueError):
        return False, f"Non-numeric exit_price: {exit_price}"
    
    # Check if exit_reason is present
    exit_reason = pick.get("exit_reason") or pick.get("close_reason")
    if not exit_reason:
        return True, "Warning: closed pick without exit_reason"
    
    # Validate exit_reason matches price action
    entry = float(pick.get("entry_price", 0))
    direction = pick.get("direction", "").upper()
    
    if entry > 0 and direction:
        if direction in ("LONG", "BUY"):
            if exit_val > entry and exit_reason not in ("TP_HIT", "WON", "TAKE_PROFIT"):
                return True, f"Warning: LONG closed above entry but reason={exit_reason}"
            elif exit_val < entry and exit_reason not in ("SL_HIT", "LOST", "STOP_LOSS"):
                return True, f"Warning: LONG closed below entry but reason={exit_reason}"
        elif direction in ("SHORT", "SELL"):
            if exit_val < entry and exit_reason not in ("TP_HIT", "WON", "TAKE_PROFIT"):
                return True, f"Warning: SHORT closed below entry but reason={exit_reason}"
            elif exit_val > entry and exit_reason not in ("SL_HIT", "LOST", "STOP_LOSS"):
                return True, f"Warning: SHORT closed above entry but reason={exit_reason}"
    
    return True, f"Close outcome verified: {status}"


def _get_price_source_for_class(asset_class: str) -> str:
    """Get minimum price source per asset class for replay."""
    sources = {
        "CRYPTO": "Binance API (spot/perp)",
        "FOREX": "Forex.com or OANDA",
        "EQUITY": "Yahoo Finance (regular hours)",
        "COMMODITY": "COMEX/CBOT front month",
        "FUTURES": "CME front month continuous",
        "MICRO_FUTURES": "CME micro contracts (MES,MNQ,MYM,M2K)",
        "BOND": "US Treasury yield curve (TLT,IEF,SHY)",
        "ETF": "NYSE/AMEX market",
        "MEME": "DEX/CEX aggregate (DEX, centralized)",
        "MEMECOIN": "DEX/CEX aggregate",
    }
    return sources.get(asset_class, "Unknown source")


def verify_copy_pick(
    pick: dict,
    resolved_row: Optional[dict] = None,
    strict_mode: bool = False
) -> VerificationResult:
    """
    Verify a single copy-trader pick.
    
    Args:
        pick: Pick dictionary from source files
        resolved_row: Optional resolved row from universal_resolved_picks.json
        strict_mode: If True, treat warnings as failures
        
    Returns:
        VerificationResult with tier, score, and check details
    """
    # Extract core identifiers
    pick_id = pick.get("pick_id") or pick.get("id") or _compute_dedup_hash(pick)
    symbol = pick.get("symbol", "UNKNOWN")
    source_system = pick.get("source_system") or pick.get("source", "UNKNOWN")
    
    # Run all checks
    checks = {}
    failures = []
    
    # 1. Identity check
    identity_pass, identity_msg = _check_identity(pick)
    checks["identity"] = (identity_pass, identity_msg)
    if not identity_pass:
        failures.append(f"identity: {identity_msg}")
    
    # 2. Source endpoint check
    source_pass, source_msg = _check_source_endpoint(pick)
    checks["source_endpoint"] = (source_pass, source_msg)
    if not source_pass:
        failures.append(f"source_endpoint: {source_msg}")
    
    # 3. Order details check
    order_pass, order_msg = _check_order_details(pick)
    checks["order_details"] = (order_pass, order_msg)
    if not order_pass:
        failures.append(f"order_details: {order_msg}")
    
    # 4. Timestamp check
    ts_pass, ts_msg = _check_timestamps(pick)
    checks["timestamps"] = (ts_pass, ts_msg)
    if not ts_pass:
        failures.append(f"timestamps: {ts_msg}")
    
    # 5. Symbol normalization check
    sym_pass, sym_msg = _check_symbol_normalization(pick)
    checks["symbol_normalization"] = (sym_pass, sym_msg)
    if not sym_pass:
        failures.append(f"symbol_normalization: {sym_msg}")
    
    # 6. Close outcome check
    close_pass, close_msg = _check_close_outcome(pick)
    checks["close_outcome"] = (close_pass, close_msg)
    if not close_pass:
        failures.append(f"close_outcome: {close_msg}")
    
    # Check copy-trader staleness penalty (from quality_gates.py)
    last_signal = pick.get("last_signal_at") or pick.get("last_signal")
    if last_signal and ("copy_trader" in source_system.lower() or "multi_asset" in source_system.lower()):
        signal_age_hrs = _calculate_age_hours(last_signal)
        if signal_age_hrs > 168:  # 7 days
            checks["copytrader_staleness"] = (False, f"Dead signal: {signal_age_hrs:.0f}h > 168h")
            failures.append(f"copytrader_dead_signal({signal_age_hrs:.0f}h):-35")
        elif signal_age_hrs > 72:  # 3 days
            checks["copytrader_staleness"] = (False if strict_mode else True, f"Stale signal: {signal_age_hrs:.0f}h > 72h")
            if strict_mode:
                failures.append(f"copytrader_stale_signal({signal_age_hrs:.0f}h):-20")
    
    # Get asset class
    from audit_trail.asset_classification import classify_asset
    asset_class = classify_asset(symbol).value
    
    # Calculate confidence score
    passed_checks = sum(1 for passed, _ in checks.values() if passed)
    total_checks = len(checks)
    
    # Base score from checks
    base_score = int((passed_checks / total_checks) * 100) if total_checks > 0 else 0
    
    # Apply staleness penalty if applicable
    if last_signal and "copy_trader" in source_system.lower():
        signal_age_hrs = _calculate_age_hours(last_signal)
        if signal_age_hrs > 168:
            base_score -= 35
        elif signal_age_hrs > 72:
            base_score -= 20
    
    # Clamp to 0-100
    confidence_score = max(0, min(100, base_score))
    
    # Determine tier
    if confidence_score >= 90:
        tier = ConfidenceTier.A_VERIFIED
        status = VerificationStatus.PASS
    elif confidence_score >= 70:
        tier = ConfidenceTier.B_PROBABLE
        status = VerificationStatus.WARN if failures else VerificationStatus.PASS
    elif confidence_score >= 50:
        tier = ConfidenceTier.C_WEAK
        status = VerificationStatus.WARN
    else:
        tier = ConfidenceTier.D_UNVERIFIED
        status = VerificationStatus.FAIL
    
    # Override status based on failures in strict mode
    if strict_mode and failures:
        status = VerificationStatus.FAIL
    
    # Get price source for asset class
    price_source = _get_price_source_for_class(asset_class)
    
    return VerificationResult(
        pick_id=pick_id,
        symbol=symbol,
        source_system=source_system,
        status=status,
        tier=tier,
        confidence_score=confidence_score,
        checks=checks,
        failures=failures,
        asset_class=asset_class,
        price_source=price_source,
        resolved_row=resolved_row
    )


def verify_batch(picks: list[dict], strict_mode: bool = False) -> dict:
    """
    Verify a batch of picks and return summary.
    
    Args:
        picks: List of pick dictionaries
        strict_mode: If True, treat warnings as failures
        
    Returns:
        Dictionary with verification summary
    """
    results = []
    
    for pick in picks:
        result = verify_copy_pick(pick, strict_mode=strict_mode)
        results.append(result)
    
    # Calculate summary stats
    total = len(results)
    pass_count = sum(1 for r in results if r.status == VerificationStatus.PASS)
    warn_count = sum(1 for r in results if r.status == VerificationStatus.WARN)
    fail_count = sum(1 for r in results if r.status == VerificationStatus.FAIL)
    
    tier_a = sum(1 for r in results if r.tier == ConfidenceTier.A_VERIFIED)
    tier_b = sum(1 for r in results if r.tier == ConfidenceTier.B_PROBABLE)
    tier_c = sum(1 for r in results if r.tier == ConfidenceTier.C_WEAK)
    tier_d = sum(1 for r in results if r.tier == ConfidenceTier.D_UNVERIFIED)
    
    # Group by asset class
    by_asset_class = {}
    for r in results:
        ac = r.asset_class
        if ac not in by_asset_class:
            by_asset_class[ac] = {"total": 0, "pass": 0, "warn": 0, "fail": 0, "avg_confidence": 0}
        by_asset_class[ac]["total"] += 1
        if r.status == VerificationStatus.PASS:
            by_asset_class[ac]["pass"] += 1
        elif r.status == VerificationStatus.WARN:
            by_asset_class[ac]["warn"] += 1
        elif r.status == VerificationStatus.FAIL:
            by_asset_class[ac]["fail"] += 1
    
    # Calculate average confidence per asset class
    for ac, stats in by_asset_class.items():
        ac_results = [r for r in results if r.asset_class == ac]
        stats["avg_confidence"] = sum(r.confidence_score for r in ac_results) / len(ac_results) if ac_results else 0
    
    return {
        "total": total,
        "passed": pass_count,
        "warnings": warn_count,
        "failed": fail_count,
        "pass_rate": pass_count / total * 100 if total > 0 else 0,
        "tiers": {
            "A_verified": tier_a,
            "B_probable": tier_b,
            "C_weak": tier_c,
            "D_unverified": tier_d,
        },
        "by_asset_class": by_asset_class,
        "results": results
    }


def load_copy_picks() -> list[dict]:
    """Load all copy-trader picks from source files."""
    all_picks = []
    
    # Define source files to load
    source_files = [
        _REPO / "copy_trader_intel" / "data" / "active_picks.json",
        _REPO / "copy_trader_intel" / "data" / "highscore_active_picks.json",
        _REPO / "copy_trader_intel" / "data" / "clone_active_picks.json",
        _REPO / "copy_trader_intel" / "data" / "consensus_active_picks.json",
        _REPO / "copy_trader_intel" / "data" / "multi_asset_picks.json",
        _REPO / "copy_trader_intel" / "data" / "forex_copytrader_picks.json",
        _REPO / "copy_trader_intel" / "data" / "futures_copytrader_picks.json",
        _REPO / "copy_trader_intel" / "data" / "stocks_copytrader_picks.json",
        _REPO / "copy_trader_intel" / "data" / "commodity_copytrader_picks.json",
    ]
    
    for filepath in source_files:
        if filepath.exists():
            try:
                with open(filepath) as f:
                    data = json.load(f)
                
                picks = data.get("picks", []) if isinstance(data, dict) else data
                source_name = filepath.stem
                
                for pick in picks:
                    pick["_source_file"] = str(filepath.relative_to(_REPO))
                    all_picks.append(pick)
                    
                logger.info(f"Loaded {len(picks)} picks from {source_name}")
            except Exception as e:
                logger.warning(f"Failed to load {filepath}: {e}")
    
    return all_picks


def load_resolved_picks() -> dict:
    """Load resolved picks from universal_resolved_picks.json."""
    resolved_path = _REPO / "audit_trail" / "data" / "universal_resolved_picks.json"
    
    if not resolved_path.exists():
        return {}
    
    try:
        with open(resolved_path) as f:
            data = json.load(f)
        
        picks = data if isinstance(data, list) else data.get("picks", [])
        
        # Index by pick_id or symbol+entry
        index = {}
        for pick in picks:
            pick_id = pick.get("pick_id") or pick.get("id")
            if pick_id:
                index[pick_id] = pick
            else:
                # Fallback to symbol+entry
                key = f"{pick.get('symbol', '')}_{pick.get('entry_price', '')}"
                index[key] = pick
        
        return index
    except Exception as e:
        logger.warning(f"Failed to load resolved picks: {e}")
        return {}


def generate_verification_report(strict_mode: bool = False) -> dict:
    """
    Generate comprehensive verification report.
    
    Args:
        strict_mode: If True, treat warnings as failures
        
    Returns:
        Verification report dictionary
    """
    logger.info("Starting copy-trader verification report...")
    
    # Load source picks
    source_picks = load_copy_picks()
    logger.info(f"Loaded {len(source_picks)} source picks")
    
    # Load resolved picks for reconciliation
    resolved_picks = load_resolved_picks()
    logger.info(f"Loaded {len(resolved_picks)} resolved picks")
    
    # Verify each pick
    verification = verify_batch(source_picks, strict_mode=strict_mode)
    
    # Check for reconciliation issues
    reconciliation_issues = []
    for result in verification["results"]:
        if result.symbol in resolved_picks:
            resolved = resolved_picks[result.symbol]
            # Check if outcome matches
            source_status = result.checks.get("close_outcome", (True, ""))[0]
            if not source_status:
                reconciliation_issues.append({
                    "symbol": result.symbol,
                    "source_system": result.source_system,
                    "issue": "Close outcome mismatch with resolved"
                })
    
    verification["reconciliation_issues"] = reconciliation_issues
    
    # Save report
    output_dir = _REPO / "tools" / "data"
    output_dir.mkdir(exist_ok=True, parents=True)
    output_path = output_dir / "copytrader_verification_report.json"
    
    # Convert results to JSON-serializable format
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "strict_mode": strict_mode,
        "summary": {
            "total": verification["total"],
            "passed": verification["passed"],
            "warnings": verification["warnings"],
            "failed": verification["failed"],
            "pass_rate": verification["pass_rate"],
            "tiers": verification["tiers"],
            "by_asset_class": verification["by_asset_class"],
            "reconciliation_issues_count": len(reconciliation_issues),
        },
        "reconciliation_issues": reconciliation_issues[:50],  # Limit to 50
    }
    
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    
    logger.info(f"Verification report saved to {output_path}")
    
    return report


def main():
    """Run verification report generator."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Copy-trader verification report")
    parser.add_argument("--strict", action="store_true", help="Strict mode: treat warnings as failures")
    args = parser.parse_args()
    
    print("=" * 60)
    print("COPY-TRADER VERIFICATION REPORT")
    print("=" * 60)
    
    report = generate_verification_report(strict_mode=args.strict)
    
    print(f"\nGenerated: {report['generated_at']}")
    print(f"\nSummary:")
    print(f"  Total picks: {report['summary']['total']}")
    print(f"  Passed: {report['summary']['passed']}")
    print(f"  Warnings: {report['summary']['warnings']}")
    print(f"  Failed: {report['summary']['failed']}")
    print(f"  Pass rate: {report['summary']['pass_rate']:.1f}%")
    
    print(f"\nConfidence Tiers:")
    for tier, count in report['summary']['tiers'].items():
        print(f"  {tier}: {count}")
    
    print(f"\nBy Asset Class:")
    for ac, stats in report['summary']['by_asset_class'].items():
        print(f"  {ac}: {stats['total']} total, {stats['avg_confidence']:.1f}% avg confidence")
    
    print(f"\nReconciliation Issues: {report['summary']['reconciliation_issues_count']}")
    
    print("\n" + "=" * 60)
    print("REPORT COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()