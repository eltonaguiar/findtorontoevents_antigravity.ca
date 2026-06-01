#!/usr/bin/env python3
"""
tools/pre_alter_backfill_validation.py

Minimal, read-only pre-ALTER validation script for the dedup harmonization backfill.

Purpose (directly implementing the top recommendation from the 2026-06-01 TON review
of reports/2026-06-01_backfill_strategy_dedup_harmonization.md):

- Simulate the effect of the required schema ALTER (CHAR(36) -> VARCHAR(255) for pick_id).
- Take a sample of "untagged" historical rows (pre-v1: keys).
- Generate the would-be canonical IDs using legacy_fallback=True.
- Check for collisions against a provided set of existing canonical (v1:) keys.
- Report potential issues (collisions, high legacy_fallback usage, missing stable fields)
  before any production ALTER or backfill is attempted.

This is a safety / dry-run tool only. No DB writes, no mutation of live data.

Usage examples:
  python3 tools/pre_alter_backfill_validation.py --help
  python3 tools/pre_alter_backfill_validation.py --sample-file samples/untagged_rows.json
  python3 tools/pre_alter_backfill_validation.py --inline-sample  # uses built-in example

Part of the P0 §15 pipeline hygiene work. Paper-pilot only. 0/9 honesty.

References:
- Backfill strategy: reports/2026-06-01_backfill_strategy_dedup_harmonization.md
- Helper: alpha_engine/dedup.py (build_canonical_outcomes_pick_id with legacy_fallback)
- TON review: /tmp/ton_backfill_review_20260601_050558/groq__qwen_qwen3-32b.md
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Import the canonical helper (must be on PYTHONPATH or installed)
try:
    from alpha_engine.dedup import build_canonical_outcomes_pick_id
except ImportError:
    print("ERROR: Could not import alpha_engine.dedup. Run from repo root.", file=sys.stderr)
    sys.exit(1)


# --- Small inline versions of the OLD divergent logic (for writer_key_parity check) ---
# These are the exact pre-harmonization behaviors the dedup fix eliminated.
# Used only for validation / telemetry in this pre-ALTER / canary tool.

def _old_universal_at_pick_outcomes_hash(pick):
    """Exact narrow hash previously used in universal_pick_resolver.py _write_outcomes_to_mysql."""
    import hashlib
    symbol = str(pick.get("symbol", pick.get("ticker", "")))[:50]
    strategy = str(pick.get("strategy", pick.get("algorithm_name", "")))[:100]
    resolved_at = None
    for ts_key in ("resolved_at", "closed_at", "exit_date", "timestamp"):
        if pick.get(ts_key):
            resolved_at = str(pick[ts_key]).replace("T", " ").replace("Z", "")[:19]
            break
    asset_class = str(pick.get("asset_class", "CRYPTO"))[:20]
    _seed = f"{symbol}|{strategy}|{resolved_at or ''}|{asset_class}"
    return hashlib.md5(_seed.encode("utf-8")).hexdigest()[:36]


def _old_alpha_at_pick_outcomes_raw(pick):
    """Exact raw-id logic previously used in alpha_engine/outcome_resolver.py _write_outcomes_to_mysql."""
    return str(pick.get("id", "") or "").strip()


def load_untagged_sample(path: Path | None) -> list[dict[str, Any]]:
    """Load a JSON list of untagged row dicts, or return a built-in example."""
    if path and path.exists():
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            raise ValueError("Sample file must contain a JSON array of row objects")

    # Built-in minimal example for quick local testing (real data would come from discovery query)
    return [
        {
            "pick_id": "a1b2c3d4e5f6...",  # old md5-style or raw
            "symbol": "BTCUSDT",
            "direction": "LONG",
            "strategy": "momentum_v2",
            "resolved_at": "2026-04-15T10:22:00",
            "opened_at": "2026-04-15T09:15:00",
            "asset_class": "CRYPTO",
            "source_system": "priority_picks",
        },
        {
            "pick_id": "legacy_no_time",
            "symbol": "ETHUSDT",
            "direction": "SHORT",
            "strategy": "mean_reversion",
            "opened_at": None,
            "resolved_at": None,
            "asset_class": "CRYPTO",
        },
    ]


def load_existing_canonical_keys(path: Path | None) -> set[str]:
    """Load existing v1: keys (one per line or JSON array)."""
    if path and path.exists():
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            try:
                data = json.loads(content)
                if isinstance(data, list):
                    return {str(x) for x in data if str(x).startswith("v1:")}
            except Exception:
                pass
            # Fallback: one key per line
            return {line.strip() for line in content.splitlines() if line.strip().startswith("v1:")}
    # Small synthetic set for the built-in example
    return {
        "v1::priority_picks_emitter_v1::some-real-key-123",
        "v1::fallback::ETHUSDT::LONG::mean_reversion::2026-04-10 12:00:00::CRYPTO",
    }


def run_validation(untagged_rows: list[dict], existing_keys: set[str]) -> dict[str, Any]:
    """Core simulation: generate canonical IDs with legacy_fallback and check collisions.

    Enhanced for Canary Telemetry readiness (per 2026-06-01 Canary Telemetry + Rollback Plan):
    - Tracks legacy_collision_suffix usage (new param in dedup helper).
    - Adds basic emitter / source_system concentration in the sample.
    - Includes purged workflow awareness stub (to be wired to actual purged dates later).
    This output can feed future canary monitoring and the pre-ALTER checklist.
    """
    results = {
        "total_untagged": len(untagged_rows),
        "would_be_generated": 0,
        "collisions_with_existing": [],
        "high_legacy_usage_rows": [],
        "missing_stable_time": 0,
        "legacy_collision_suffix_used": 0,
        "emitter_concentration": {},
        "purged_workflow_warning": "STUB: Add actual purged workflow date ranges from TESTING_PROTOCOL.MD and filter sample here.",
        "writer_key_parity_mismatches": [],  # direct TON rec: real-time parity check vs old divergent paths
        "recommendations": [],
    }

    generated = set()
    emitter_counts = {}

    for idx, row in enumerate(untagged_rows):
        # Demonstrate the new legacy_collision_suffix capability (swarm rec from TON review).
        # In real backfill the operator / script would compute a disambiguation suffix when risk is high.
        suffix = row.get("_legacy_collision_suffix")  # allow sample rows to carry it for testing
        new_id = build_canonical_outcomes_pick_id(
            row, legacy_fallback=True, legacy_collision_suffix=suffix
        )
        results["would_be_generated"] += 1

        if suffix:
            results["legacy_collision_suffix_used"] += 1

        # Basic concentration (source_system / emitter) for canary telemetry
        emitter = row.get("source_system") or row.get("emitter") or "unknown"
        emitter_counts[emitter] = emitter_counts.get(emitter, 0) + 1

        # --- writer_key_parity check (direct implementation of latest TON recommendation) ---
        # Compare the new canonical ID against the two OLD divergent paths that the harmonization fixed.
        old_alpha = _old_alpha_at_pick_outcomes_raw(row)
        old_universal = _old_universal_at_pick_outcomes_hash(row)

        parity_entry = {
            "row_index": idx,
            "symbol": row.get("symbol"),
            "new_canonical": new_id,
            "old_alpha_raw": old_alpha,
            "old_universal_md5": old_universal,
            "differs_from_alpha": new_id != old_alpha if old_alpha else False,
            "differs_from_universal": new_id != old_universal if old_universal else False,
        }

        # Only record if there is a meaningful difference (this is the whole point of the harmonization)
        if parity_entry["differs_from_alpha"] or parity_entry["differs_from_universal"]:
            if "writer_key_parity_mismatches" not in results:
                results["writer_key_parity_mismatches"] = []
            results["writer_key_parity_mismatches"].append(parity_entry)

        # Collision against already-canonical keys in the table
        if new_id in existing_keys:
            results["collisions_with_existing"].append({
                "row_index": idx,
                "symbol": row.get("symbol"),
                "old_pick_id": row.get("pick_id"),
                "generated_id": new_id,
            })

        # Track potential internal collisions within the backfill batch itself
        if new_id in generated:
            # This would be a collision within the untagged set
            results["collisions_with_existing"].append({
                "row_index": idx,
                "symbol": row.get("symbol"),
                "note": "Potential intra-batch collision with another legacy row",
                "generated_id": new_id,
            })
        generated.add(new_id)

        # Heuristic: rows that heavily rely on legacy_fallback (missing time fields)
        stable_time = None
        for k in ("resolved_at", "closed_at", "opened_at"):
            if row.get(k):
                stable_time = row[k]
                break
        if not stable_time:
            results["missing_stable_time"] += 1
            results["high_legacy_usage_rows"].append({
                "row_index": idx,
                "symbol": row.get("symbol"),
                "strategy": row.get("strategy"),
            })

    # Finalize concentration (canary telemetry surface)
    total = max(1, len(untagged_rows))
    for emitter, count in emitter_counts.items():
        pct = round(count / total * 100, 1)
        results["emitter_concentration"][emitter] = {"count": count, "pct": pct}
        if pct > 25:
            results["hard_fail_emitter_concentration"] = True
            results["recommendations"].append(
                f"CRITICAL (hard-fail): {emitter} accounts for {pct}% of untagged sample. "
                "Exceeds 25% threshold for sub-T2 classes. Blocking per swarm recommendation and concentration gates before DSR/SPA (TESTING_PROTOCOL.MD §16)."
            )

    # Recommendations (simple heuristics) — now includes canary surfaces
    if results["collisions_with_existing"]:
        results["recommendations"].append(
            "CRITICAL: Collisions detected. Do NOT run ALTER + backfill until root cause investigated. "
            "Consider adding more fields (e.g., emitter, entry_ts) to the legacy reconstruction logic."
        )
    if results["missing_stable_time"] > len(untagged_rows) * 0.2:
        results["recommendations"].append(
            "WARNING: >20% of legacy rows lack stable time fields. Backfill will be low-confidence for these. "
            "Consider enriching from source systems before bulk update."
        )
    if results["legacy_collision_suffix_used"] > 0:
        results["recommendations"].append(
            f"INFO: {results['legacy_collision_suffix_used']} rows used legacy_collision_suffix for disambiguation "
            "(see alpha_engine/dedup.py enhancement). Review usage in production backfill."
        )
    parity_mismatches = len(results.get("writer_key_parity_mismatches", []))
    total_for_parity = max(1, len(untagged_rows))
    parity_pct = round(parity_mismatches / total_for_parity * 100, 1)

    # Canary-specific writer_key_parity surface (direct implementation of latest fast4 TON rec on the fleshed Canary plan)
    # Provides real-time alerting telemetry for pipeline symmetry during canary deployment.
    results["writer_key_parity_canary"] = {
        "mismatches": parity_mismatches,
        "pct_of_sample": parity_pct,
        "status": "PASS (no legacy divergence in this sample)" if parity_mismatches == 0 else "INFO (expected divergence on pre-v1 legacy rows)",
        "canary_alert": "During live canary on fresh post-backfill data: any non-zero mismatches on newly written rows indicates writer asymmetry (canonical vs legacy paths). Investigate resolver wiring immediately. Threshold for escalation: >5% mismatches on post-v1 cohort.",
    }

    if parity_mismatches > 0:
        results["recommendations"].append(
            f"INFO (writer_key_parity): {parity_mismatches} rows ({parity_pct}%) in sample would have produced different keys under the old divergent logic (raw id vs narrow md5). "
            "This is expected on legacy data and validates the harmonization. The canary 'writer_key_parity_canary' field above provides the real-time alerting surface for future asymmetry detection."
        )
    if results.get("hard_fail_emitter_concentration"):
        results["recommendations"].append(
            "CRITICAL (hard-fail): Emitter concentration exceeds 25% threshold. This blocks the backfill/canary for sub-T2 classes per swarm recommendation."
        )
    if not results["recommendations"]:
        results["recommendations"].append(
            "No obvious collisions in this sample. Still recommended: run on full discovery output + staging replica before prod ALTER."
        )

    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Pre-ALTER backfill validation (dry-run collision & legacy check)")
    parser.add_argument("--sample-file", type=Path, help="JSON file with list of untagged row dicts")
    parser.add_argument("--existing-keys-file", type=Path, help="File with existing v1: keys (one per line or JSON array)")
    parser.add_argument("--inline-sample", action="store_true", help="Use built-in example data (for quick local test)")
    args = parser.parse_args()

    if not args.inline_sample and not args.sample_file:
        parser.print_help()
        print("\nERROR: Provide --sample-file or --inline-sample", file=sys.stderr)
        return 2

    untagged = load_untagged_sample(args.sample_file if not args.inline_sample else None)
    existing = load_existing_canonical_keys(args.existing_keys_file)

    report = run_validation(untagged, existing)

    print(json.dumps(report, indent=2, default=str))
    print("\n=== Summary (Canary Telemetry Ready) ===")
    print(f"Untagged rows analyzed: {report['total_untagged']}")
    print(f"Would generate new canonical IDs: {report['would_be_generated']}")
    print(f"Collisions with existing v1: keys: {len(report['collisions_with_existing'])}")
    print(f"Rows heavily dependent on legacy_fallback (missing time): {report['missing_stable_time']}")
    print(f"Rows using legacy_collision_suffix: {report.get('legacy_collision_suffix_used', 0)}")
    print(f"Emitter concentration (top): {dict(list(report.get('emitter_concentration', {}).items())[:3])}")
    print(f"Writer key parity mismatches (old divergent paths vs new canonical): {len(report.get('writer_key_parity_mismatches', []))}")
    print("Purged workflow note:", report.get("purged_workflow_warning", ""))
    if report.get("hard_fail_emitter_concentration"):
        print("HARD FAIL: Emitter concentration exceeds 25% threshold for sub-T2 class (swarm rec).")
    print("Recommendations:")
    for rec in report["recommendations"]:
        print(f"  - {rec}")

    # Non-zero exit if collisions or hard-fail concentration (CI / operator friendly)
    if report.get("collisions_with_existing") or report.get("hard_fail_emitter_concentration"):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
