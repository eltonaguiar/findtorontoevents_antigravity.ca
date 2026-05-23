#!/usr/bin/env python3
"""
FIRING 9 - One-time Tagging Hygiene Backfill Script
==================================================
Date: 2026-05-21 (Firing 9 of continual 6-gate research loop, job 019e490182df)
Priority: P0 — prerequisite for any credible EQUITY/ETF 6/8-gate work and public /audit integrity.

Purpose:
  Re-classify historically polluted rows (~198+ identified in prior audits, 90.8% of "EQUITY" actually native CRYPTO)
  using the production-grade _infer_asset_class() logic from the Firing 6-8 patches.

Sources cited:
  - audit_trail/dashboard_generator.py:8254 and :8282 (the two hardcoded defaults: "FOREX" for CFTC, "EQUITY" for penny)
  - FIRING7_TAGGING_HYGIENE_PR_SCOPE_2026-05-21.md (full PR scope)
  - FIRING8_DASHBOARD_GENERATOR_PATCHED_REFERENCE_2026-05-21.py (the exact helper this script mirrors)
  - hypothesis_registry.json:416-462 (H-037 blocked by pollution)
  - 6GATES_2026-05-21_V1_FREEBUFF.MD + tools/validate_resolved_picks.py + quality_gates.py:5598 (the +10 EQUITY bonus site)
  - alpha_engine/config.py (CRYPTO_SYMBOLS, EQUITY_SYMBOLS, FUTURES_SYMBOLS etc. for pattern reference)

Safety:
  - Default mode is DRY-RUN (prints report, never mutates).
  - --apply flag required for any write.
  - Always writes a full audit log of every change.
  - Supports both JSON exports (dashboard_data.json slices, universal_resolved_picks.json, closed_picks exports) and SQL patch output for the ejaguiar1_* DB tables.

Usage examples:
  python FIRING9_TAGGING_BACKFILL_SCRIPT_2026-05-21.py --input dashboard_data.json --dry-run
  python FIRING9_TAGGING_BACKFILL_SCRIPT_2026-05-21.py --input resolved_picks_export.json --output corrected.json --apply
  python FIRING9_TAGGING_BACKFILL_SCRIPT_2026-05-21.py --sql-mode --table at_raw_picks --apply   # emits UPDATE statements

Verification after run (post-merge of the real patch):
  python tools/validate_resolved_picks.py --by-asset-class --min-trades 10 --output-dir reports/continual_research/6gate_validation/
  # Expect: sharp drop in EQUITY count, rise in CRYPTO and ETF, zero -USD symbols in EQUITY bucket.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

# =============================================================================
# ROBUST _infer_asset_class (production version, expanded from Firing 8 reference + config.py patterns)
# =============================================================================
def _infer_asset_class(symbol: str) -> str:
    """Fail-loud, symbol-based asset class inference.
    Mirrors (and slightly extends) the helper in the Firing 8 patched reference.
    Prevents 90.8% pollution and the two hardcoded defaults.
    """
    if not symbol:
        return "UNKNOWN"
    s = str(symbol).upper().strip()

    # CRYPTO native pairs (highest priority — the main pollution source)
    crypto_markers = ("-USD", "USDT", "USDC", "BTC", "ETH", "SOL", "DOGE", "AVAX", "LINK", "ADA", "XRP", "HBAR", "NEAR")
    equity_exempt = ("AAPL", "TSLA", "NVDA", "GOOGL", "MSFT", "AMZN", "META", "NFLX")
    if any(x in s for x in crypto_markers) and not any(x in s for x in equity_exempt):
        return "CRYPTO"

    # FOREX (Yahoo =X suffix or major pair tokens)
    if s.endswith("=X") or any(x in s for x in ("EUR", "GBP", "USDJPY", "AUDUSD", "USDCHF", "USDCAD", "NZDUSD", "EURUSD")):
        return "FOREX"

    # COMMODITY / FUTURES (explicit contracts from config + common aliases)
    commodity_markers = ("GC=F", "SI=F", "HG=F", "NG=F", "CL=F", "CT=F", "OJ=F", "KC=F", "ZB=F", "ZN=F", "ES=F", "NQ=F", "YM=F")
    if any(m in s for m in commodity_markers) or s in ("GC", "CL", "NG", "SI", "HG"):
        return "COMMODITY"

    # ETF (sector SPDRs, broad market, bonds, real estate — distinct from pure EQUITY)
    etf_markers = ("SPY", "QQQ", "XLK", "XLV", "XLF", "XLE", "XLY", "XLB", "XLP", "XLU", "XLRE", "XLC", "TLT", "BND", "VNQ", "IWM", "DIA", "EFA", "EEM", "VTI", "VOO")
    if any(m in s for m in etf_markers):
        return "ETF"

    # EQUITY broad (penny, large-cap, sector stocks not caught above)
    # In backfill we are conservative: if it looks like a stock ticker and not caught by above, we can tag EQUITY
    # but for the initial hygiene sweep we prefer UNKNOWN on anything ambiguous so it fails loud and gets human review.
    # For this script we return "EQUITY" only for obvious tickers; otherwise UNKNOWN.
    # (In the real dashboard_generator patch the full config-driven list can be used for EQUITY.)
    if len(s) <= 5 and s.isalpha() and not any(c in s for c in ("=", "-", "/")):
        # Likely equity ticker (penny or otherwise)
        return "EQUITY"

    return "UNKNOWN"


def process_picks(picks: List[Dict[str, Any]], source_name: str = "unknown") -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Apply inference to every pick that is missing asset_class or has suspicious value.
    Returns (corrected_picks, change_log).
    """
    corrected = []
    change_log = []

    for idx, p in enumerate(picks):
        orig_ac = (p.get("asset_class") or "").upper().strip() or None
        symbol = p.get("symbol") or p.get("ticker") or p.get("symbol_name") or ""
        new_ac = _infer_asset_class(symbol)

        changed = False
        reason = ""

        if orig_ac is None or orig_ac == "UNKNOWN" or (orig_ac == "EQUITY" and new_ac == "CRYPTO"):
            if new_ac != (orig_ac or "UNKNOWN"):
                changed = True
                reason = f"was={orig_ac or 'MISSING'} -> inferred={new_ac} (symbol={symbol})"

        if changed:
            p = dict(p)  # shallow copy
            p["asset_class"] = new_ac
            p["_backfill_source"] = source_name
            p["_backfill_ts"] = datetime.now(timezone.utc).isoformat()
            change_log.append({
                "index": idx,
                "symbol": symbol,
                "old_asset_class": orig_ac,
                "new_asset_class": new_ac,
                "reason": reason
            })

        corrected.append(p)

    return corrected, change_log


def main():
    parser = argparse.ArgumentParser(description="Firing 9 Tagging Hygiene One-Time Backfill")
    parser.add_argument("--input", type=str, help="Path to JSON file containing list of picks (or dashboard_data.json slice)")
    parser.add_argument("--output", type=str, default=None, help="Path to write corrected JSON (default: stdout or .corrected.json)")
    parser.add_argument("--apply", action="store_true", help="Actually write corrected data (default is dry-run report only)")
    parser.add_argument("--sql-mode", action="store_true", help="Emit SQL UPDATE statements instead of JSON (for DB tables)")
    parser.add_argument("--table", type=str, default="at_raw_picks", help="Target table name for SQL mode")
    parser.add_argument("--dry-run", action="store_true", help="Force dry-run even if --apply present (safety)")
    args = parser.parse_args()

    print("=" * 80)
    print("FIRING 9 TAGGING HYGIENE BACKFILL — 2026-05-21")
    print("Citations: dashboard_generator.py:8254/8282, FIRING7_PR_SCOPE, FIRING8_PATCHED_REFERENCE, hypothesis_registry H-037")
    print("=" * 80)

    if not args.input:
        print("ERROR: --input is required (path to a JSON export of resolved picks).")
        print("Example: python ... --input /path/to/universal_resolved_picks_export.json --dry-run")
        sys.exit(2)

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}")
        sys.exit(1)

    print(f"\n[1/4] Loading {input_path} ...")
    try:
        with open(input_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except Exception as e:
        print(f"ERROR loading JSON: {e}")
        sys.exit(1)

    # Normalize to list of picks (handle common dashboard_data shapes)
    if isinstance(raw, dict):
        # Common shapes: {"picks": [...]}, {"data": [...]}, or the whole dashboard payload
        if "picks" in raw and isinstance(raw["picks"], list):
            picks = raw["picks"]
        elif "data" in raw and isinstance(raw["data"], list):
            picks = raw["data"]
        elif "resolved_picks" in raw:
            picks = raw["resolved_picks"]
        else:
            # Try to find any top-level list of dicts that look like picks
            for k, v in raw.items():
                if isinstance(v, list) and v and isinstance(v[0], dict) and ("symbol" in v[0] or "ticker" in v[0]):
                    picks = v
                    break
            else:
                print("ERROR: Could not locate a list of picks inside the JSON. Provide a direct list or 'picks' key.")
                sys.exit(1)
    elif isinstance(raw, list):
        picks = raw
    else:
        print("ERROR: Unsupported JSON root type.")
        sys.exit(1)

    print(f"Loaded {len(picks)} records.")

    print("\n[2/4] Running inference pass (using production _infer_asset_class from Firing 8 reference)...")
    corrected, change_log = process_picks(picks, source_name=str(input_path.name))

    # Summary stats
    from collections import Counter
    old_counts = Counter((p.get("asset_class") or "MISSING").upper() for p in picks)
    new_counts = Counter((p.get("asset_class") or "MISSING").upper() for p in corrected)

    print("\n[3/4] Change summary (top deltas):")
    print(f"  Before: {dict(old_counts.most_common(6))}")
    print(f"  After : {dict(new_counts.most_common(6))}")

    crypto_pollution_fixed = sum(1 for c in change_log if c["new_asset_class"] == "CRYPTO")
    print(f"\n  ** Critical hygiene wins: {crypto_pollution_fixed} rows moved from EQUITY/MISSING -> CRYPTO **")
    print(f"  Total rows that would change: {len(change_log)}")

    if args.sql_mode:
        print("\n[SQL MODE] Emitting UPDATE statements for table", args.table)
        for c in change_log[:50]:  # safety cap in output
            print(f"UPDATE {args.table} SET asset_class = '{c['new_asset_class']}' WHERE symbol = '{c['symbol']}' AND (asset_class IS NULL OR asset_class = 'EQUITY');")
        if len(change_log) > 50:
            print(f"... ({len(change_log)-50} more statements truncated in console; full list in log)")

    # Always write a machine-readable change log
    log_path = Path(f"FIRING9_backfill_changes_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.jsonl")
    with open(log_path, "w", encoding="utf-8") as lf:
        for entry in change_log:
            lf.write(json.dumps(entry) + "\n")
    print(f"\n  Detailed change log written to: {log_path}")

    if args.apply and not args.dry_run:
        print("\n[4/4] APPLYING corrections...")
        if args.output:
            out_path = Path(args.output)
        else:
            out_path = input_path.with_suffix(".corrected.json")

        # Write corrected payload (preserve original shape where possible)
        if isinstance(raw, dict) and "picks" in raw:
            raw["picks"] = corrected
            payload = raw
        else:
            payload = corrected

        with open(out_path, "w", encoding="utf-8") as of:
            json.dump(payload, of, indent=2, ensure_ascii=False)

        print(f"  Corrected data written to: {out_path}")
        print("  REMINDER: After real patch merge, run the verification command from the PR scope:")
        print("    python tools/validate_resolved_picks.py --by-asset-class --min-trades 10")
    else:
        print("\n[4/4] DRY-RUN complete. No data written. Re-run with --apply to persist.")

    print("\n" + "=" * 80)
    print("Next engineering steps (from FIRING7_PR_SCOPE + FIRING8 reference):")
    print("  1. Merge the _infer_asset_class helper + caller sites into dashboard_generator.py (and emitters/quality_gates).")
    print("  2. Execute this backfill (or equivalent DB migration) against prod data.")
    print("  3. Re-run validate_resolved_picks.py --by-asset-class and move H-037 / equity_vix candidates from B_failed/pending into A_passed if they clear gates on clean data.")
    print("  4. Update public /audit banner + this continual research tree.")
    print("=" * 80)


if __name__ == "__main__":
    main()
