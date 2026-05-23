#!/usr/bin/env python3
"""
Cohort + Disagreement Filter
Only admit picks from harness-passing cohorts AND >=3 source agreement.
Run after edge_stability_harness.
"""

import json
from collections import Counter

def load_admissible_cohorts(harness_json='/tmp/harness_result.json'):
    with open(harness_json) as f:
        data = json.load(f)
    return [c['strategy'] for c in data.get('admissible', [])]

def apply_filter(pick, admissible_strategies):
    if pick.get('strategy') not in admissible_strategies:
        return False, "not_admissible"
    sources = pick.get('source_systems', [])
    if isinstance(sources, str):
        sources = sources.split(',')
    if len(set(sources)) < 3:
        return False, "insufficient_disagreement"
    return True, "PASS"

if __name__ == "__main__":
    admissible = load_admissible_cohorts()
    print(f"Loaded {len(admissible)} admissible strategies")
    # Example usage
    example_pick = {"strategy": "ml_enhanced_DYDXUSDT_15m_D_ens", "source_systems": ["sys1","sys2","sys3"]}
    ok, reason = apply_filter(example_pick, admissible)
    print(f"Example: {ok} ({reason})")