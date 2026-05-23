# Wire-up validation — per_asset_class_predictor + concentration_cap

## Context

Both sidecars are ready w/ 38/38 passing tests:
- `alpha_engine/per_asset_class_predictor.py` (env flag `PER_ASSET_CLASS_SCORING_ENABLED`, default-OFF)
- `alpha_engine/concentration_cap.py` (no env flag yet; needs caller in `passes_active_gate`)

Wire-up sites confirmed:
- `audit_trail/quality_gates.py:5885` `calculate_smart_score` — returns at line 6146 after clamp + optional `drift_aware_scoring` wrapper (line 6153-6157)
- `audit_trail/quality_gates.py:4424` `passes_active_gate` — early-return pattern, returns True/False per check

## Question

Validate the proposed wire-up:

```python
# In calculate_smart_score, after the drift_aware_scoring wrapper (line ~6157):
try:
    from alpha_engine.per_asset_class_predictor import (
        is_enabled as _pacp_enabled,
        is_shadow_mode as _pacp_shadow,
        per_asset_class_smart_score as _pacp_score,
    )
    if _pacp_enabled():
        adjusted = _pacp_score(pick, base_smart_score=clamped, blend_with_base=0.4)
        if _pacp_shadow():
            pick["_per_class_smart_score_shadow"] = round(adjusted, 1)
            return clamped  # shadow: return legacy, log new
        return round(adjusted, 1)
except Exception:
    pass
return clamped
```

```python
# In passes_active_gate, after is_corrupted_outcome_row check:
import os as _os
if _os.environ.get("CONCENTRATION_CAP_ENABLED", "0") == "1":
    try:
        from alpha_engine.concentration_cap import passes_concentration_cap as _pcc
        from json import load as _json_load
        from pathlib import Path as _Path
        _ap_path = _Path(__file__).resolve().parent.parent / "alpha_engine" / "data" / "active_picks.json"
        if _ap_path.exists():
            with open(_ap_path, "r", encoding="utf-8") as _f:
                _active = _json_load(_f)
                if isinstance(_active, dict):
                    _active = _active.get("picks") or _active.get("active") or []
            ok, reason = _pcc(pick.get("asset_class") or "", pick.get("symbol") or "", _active)
            if not ok:
                logger.debug("concentration_cap_rejected: %s", reason)
                return False
    except Exception:
        pass  # never let cap fail the gate
```

Return STRICT JSON:

```json
{
  "calculate_smart_score_wireup_verdict": "<APPROVE|REQUEST_CHANGES|REJECT>",
  "calculate_smart_score_concerns": ["<one line each>"],
  "passes_active_gate_wireup_verdict": "<APPROVE|REQUEST_CHANGES|REJECT>",
  "passes_active_gate_concerns": ["<...>"],
  "io_cost_concern_on_active_gate": "<LOW|MEDIUM|HIGH — every gate call reading active_picks.json from disk>",
  "recommended_cache_pattern_for_active_picks": "<e.g. module-level lru_cache w/ 30s TTL>",
  "blend_ratio_0_4_vs_0_5_vs_other": "<pick one + reason>",
  "shadow_logging_field_name": "<should it be _per_class_smart_score_shadow or another canonical name like smart_score_v2_shadow?>",
  "must_clear_shadow_field_on_pick_save": "<true|false — does the field leak into downstream consumers?>",
  "single_biggest_risk_of_this_wireup": "<one sentence>"
}
```

## Constraints

- Active gate runs on every pick on every dashboard build. I/O cost matters.
- Drift-aware-scoring at line 6153-6157 already uses try/import/return pattern — match it.
- Wire-Up Rule (CLAUDE.md): a try/import that no-ops on ImportError still counts as wired as long as the import path exists.
