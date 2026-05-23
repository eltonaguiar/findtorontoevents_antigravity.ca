# Swarm review: NS-C UTC filter correction (8,9) → 6

## Context

Branch `fix/ns-c-utc-filter-correction-2026-05-13` updates the CRYPTO UTC-hour death-zone filter in `audit_trail/quality_gates.py::passes_active_gate`.

**Prior state (production main):**
```python
if _hr is not None and _hr in (8, 9):
    pick["_hf_quality_gate_reason"] = f"ns_c_crypto_utc_death_zone_hr{_hr}"
    return False  # reject CRYPTO entries at 8-9 UTC
```

**Source of (8,9) threshold:** memory `project_clean_data_symbol_wr` claiming "22 UTC = 61.2% WR peak / 08-09 UTC = death zone".

**This session, falsified the memory claim** via `tools/backtest_btc_utc_hour_filter.py`:
- 22 UTC actual = 42.9% WR (NOT 61.2%)
- Real death zone = 6 UTC at 23.1% WR / PF 0.06
- Estimated lift from filter: only +1.11pp WR (vs original +14pp claim)

**4/4 non-opus-4 swarm engines (xai/deepseek/groq/cerebras) independently recommended:** update filter from (8,9) to 6.

## Proposed diff

```python
# OLD
if _hr is not None and _hr in (8, 9):

# NEW
if _hr is not None and _hr == 6:
```

Plus comment block updated to cite the backtest + swarm consensus. Test file updated to assert `_hr == 6` instead of `in (8, 9)`.

13/13 unit tests pass on new branch.

## Question to engines

Review this surgical 1-tuple change against:
1. Is the underlying backtest evidence (single-engine backtest on N=? CRYPTO terminal picks bucketed by entry-hour UTC) sufficient to ship a production gate change?
2. Are there confounders I'm missing — e.g., does 6 UTC correlate with weekend-edge or low-liquidity sessions?
3. Should the filter be ADDED to (i.e., reject `6, 8, 9`) rather than REPLACED (reject only `6`)?
4. Is the default-ON behavior still right after the threshold flip?

Return strict JSON ONLY:

```json
{
  "verdict": "APPROVE | APPROVE_WITH_CAVEATS | REQUEST_CHANGES | REJECT",
  "evidence_quality": "<sufficient | thin | needs more data>",
  "confounders_identified": ["<list>"],
  "recommendation_on_filter_scope": "REPLACE_(8,9)_WITH_6 | ADD_6_TO_(8,9) | KEEP_(8,9)_REVERT | OTHER",
  "default_behavior_recommendation": "DEFAULT_ON | DEFAULT_OFF",
  "additional_test_cases_needed": ["<list>"],
  "merge_decision": "MERGE | HOLD | REJECT"
}
```

## Constraints

- This is a production exec-gate change; production safety > academic purity
- Reversibility: change is one line; reverting takes 30 seconds
- Default-ON: filter was previously rejecting picks; flipping default-OFF would re-enable bleed at 6 UTC
- "Add to" vs "Replace": user explicitly asked for surgical change, but if (8,9) really do have edge defect, keep them
