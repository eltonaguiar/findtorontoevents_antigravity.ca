# Audit enhancement deep-dig — find concrete wire-up paths + verify IC claims

## Context

Two third-party agents (mimo + edge-stability agent) have proposed major audit dashboard / scoring enhancements. A first-pass review (caveman synthesis 2026-05-13) flagged these blockers before merge:

1. **5 new modules, 0 production callers** (Wire-Up Rule violation per CLAUDE.md). Need concrete caller files + functions.
2. **IC values unverified** (claimed: elite_score IC=+0.012, regime_bonus IC=+0.19, ML_Replacement IC=-0.19, Source_System_Tier IC=-0.18). Memory says `project_performance_reality.md` has trust_score ρ=+0.196 strongest, elite_score ρ=+0.082 post-ghost-cleanup. **Mimo numbers may be pre-ghost-cleanup (i.e. polluted by MATIC ghost rows).**
3. **"CRYPTO MaxDD 178%" claim** — field not in `asset_class_health`. Source unknown.
4. **drift_circuit_breaker proposal would write to `circuit_breaker_state.json`** which already had a documented stale-state leak (memory `feedback_circuit_breaker_stale_state_leak`, ~115h leak on alpha_engine_fast in 2026-04-27). Namespace fix needed.
5. **Two scoring changes inbound same week**: PR #942 anti-overfit default-ON + mimo per-class scoring reweight. Need clean attribution.

## Question to engines

For EACH of these, return strict JSON. Be specific — name files, functions, line ranges where possible. If you cannot find evidence in the repo for a claim, say so explicitly.

```json
{
  "wire_up_targets": {
    "per_asset_class_predictor": {
      "best_call_site_file": "<path>",
      "best_call_site_function": "<func>",
      "rationale": "<why this is the canonical scoring entry>",
      "downside": "<one-line risk of wiring there>"
    },
    "concentration_enhancer": {
      "best_call_site_file": "<path>",
      "best_call_site_function": "<func>",
      "rationale": "<...>",
      "downside": "<...>"
    },
    "drift_circuit_breaker": {
      "best_call_site_file": "<path>",
      "best_call_site_function": "<func>",
      "rationale": "<...>",
      "downside": "<...>"
    },
    "risk_adjusted_metrics": {
      "best_call_site_file": "<path>",
      "best_call_site_function": "<func>",
      "is_truly_sidecar": "<true|false — does it need a caller at all, or is it dashboard-only?>"
    },
    "edge_decay_heatmap": {
      "best_call_site_file": "<path>",
      "best_call_site_function": "<func>",
      "is_truly_sidecar": "<true|false>"
    }
  },
  "circuit_breaker_namespace_plan": {
    "current_state_file_path": "<probable path>",
    "current_top_level_keys": ["<list of top-level keys you expect or know>"],
    "recommended_new_key_name_for_drift_breaker": "<key>",
    "stale_state_leak_prevention_rule": "<one rule, e.g. 'ttl_seconds=3600 on each top-level namespace, expiry → ignored'>"
  },
  "ic_reproducer_plan": {
    "closed_pick_dataset_path": "<canonical path, e.g. audit_trail/data/dashboard_payload.json :: recent_closed[]>",
    "ghost_cleanup_required": "<true|false — is MATIC 660-row ghost still in the data?>",
    "minimum_python_snippet_to_compute_ic": "<3-8 line numpy/pandas snippet>",
    "feature_names_to_compute_ic_for": ["elite_score", "regime_bonus", "trust_score", "confidence", "ml_replacement_score", "source_system_tier"]
  },
  "scoring_change_attribution_plan": {
    "merge_order_recommendation": "<list PR numbers in order: e.g. #961, #942, then mimo's PR>",
    "minimum_quarantine_period_days": <int>,
    "rollback_criterion": "<one-line condition>"
  },
  "highest_risk_one_thing_if_we_ship_as_proposed": "<one sentence>",
  "smallest_safe_pilot_action": "<one sentence — what to do FIRST, smallest reversible change>"
}
```

## Constraints

- Be concrete on file paths. Guessing without evidence is worse than admitting absence.
- Do not invent function names. If `passes_smart_gate` is the canonical entry but the file path is unclear, say so.
- Reject the proposal if the wire-up creates a circular import or contradicts an existing investigation-before-kill gate.
- One-sentence "highest_risk" must name the specific failure mode (not "drift" — say what drifts to what).
