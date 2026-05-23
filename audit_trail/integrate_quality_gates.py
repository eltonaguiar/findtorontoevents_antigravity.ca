"""
Integration Guide: Adding Quality Gates to Dashboard Generator

This script shows the minimal changes needed to integrate quality gates
into the existing dashboard_generator.py

Usage: Apply these changes to audit_trail/dashboard_generator.py
"""

# STEP 1: Add import at top of dashboard_generator.py
# Add after existing imports (around line 30):
QUALITY_GATES_IMPORT = """
# Quality gates for high-quality picks filtering
from audit_trail.quality_gates import (
    passes_active_gate, 
    passes_smart_gate, 
    calculate_smart_score,
    classify_pick_quality
)
"""

# STEP 2: Modify the pick aggregation section
# Find where picks are added to payload and wrap with quality gates

ACTIVE_PICKS_FILTER = """
# Filter active picks through quality gate
if passes_active_gate(pick):
    payload["active"].append(enriched)
    
    # Also check if it qualifies for Smart Picks
    if passes_smart_gate(pick):
        smart_pick = enriched.copy()
        smart_pick["smart_score"] = calculate_smart_score(pick)
        payload["smart_picks"].append(smart_pick)
"""

# STEP 3: Add smart_picks array to payload initialization
PAYLOAD_INIT = """
payload = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "active": [],
    "closed": [],
    "smart_picks": [],  # NEW: Premium quality picks
    "stats": {},
    # ... rest of payload
}
"""

# STEP 4: Add stats for quality metrics
QUALITY_STATS = """
# Quality gate statistics
payload["quality_stats"] = {
    "active_picks_total": len(all_active_picks),
    "active_picks_passed": len(payload["active"]),
    "active_picks_filtered": len(all_active_picks) - len(payload["active"]),
    "smart_picks_count": len(payload["smart_picks"]),
    "smart_picks_percentage": round(len(payload["smart_picks"]) / len(payload["active"]) * 100, 1) if payload["active"] else 0,
    "avg_smart_score": round(sum(p.get("smart_score", 0) for p in payload["smart_picks"]) / len(payload["smart_picks"]), 1) if payload["smart_picks"] else 0,
}
"""


def generate_patch_instructions():
    """Print step-by-step integration instructions."""
    print("=" * 70)
    print("QUALITY GATES INTEGRATION GUIDE")
    print("=" * 70)
    print()
    print("File to modify: audit_trail/dashboard_generator.py")
    print()
    print("-" * 70)
    print("STEP 1: Add Import")
    print("-" * 70)
    print("Add this import near line 30 (after existing imports):")
    print()
    print(QUALITY_GATES_IMPORT)
    print()
    print("-" * 70)
    print("STEP 2: Modify Pick Processing Loop")
    print("-" * 70)
    print("Find the section where picks are added to payload['active']")
    print("Replace or wrap with:")
    print()
    print(ACTIVE_PICKS_FILTER)
    print()
    print("-" * 70)
    print("STEP 3: Initialize Smart Picks Array")
    print("-" * 70)
    print("In payload initialization, add 'smart_picks': []:")
    print()
    print(PAYLOAD_INIT)
    print()
    print("-" * 70)
    print("STEP 4: Add Quality Stats")
    print("-" * 70)
    print("Before writing payload to JSON, add quality stats:")
    print()
    print(QUALITY_STATS)
    print()
    print("-" * 70)
    print("STEP 5: Test the Integration")
    print("-" * 70)
    print("1. Run dashboard_generator.py locally")
    print("2. Check dashboard_payload.json has 'smart_picks' array")
    print("3. Verify quality_stats are populated")
    print("4. Check that entry_price=0 picks are filtered out")
    print("5. Verify PERMANENTLY_KILLED strategies are excluded")
    print()
    print("=" * 70)


if __name__ == "__main__":
    generate_patch_instructions()
