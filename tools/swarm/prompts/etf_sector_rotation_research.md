# ETF Sector Rotation — Edge Research

## Context

You are a quantitative researcher for findtorontoevents.ca/audit trading system.

Current ETF stats (from audit dashboard, 2026-05-16): PF=1.24, WR=55.2%, n=107.
Target: PF≥1.5 via sector-rotation overlay. The system uses `alpha_engine/config.py` for strategy config and `audit_trail/quality_gates.py` for scoring gates.

## Your Task

1. **Read** these files:
   - `audit_trail/quality_gates.py` — search for "ETF" (grep lines around SMART_PICKS_MIN_SCORE_ETF)
   - `alpha_engine/config.py` — find ETF strategy families
   - `audit_dashboard/data/dashboard_data.json` — ETF stats by strategy family
   - `tools/weekly_filter_picks.py` — current ETF filter criteria

2. **Evaluate two approaches** for ETF sector rotation to lift PF 1.24→1.5:

   **Approach A — Relative-Strength (RS) overlay:**
   - Rank ETF picks by 20d momentum vs SPY
   - Only pass picks from ETFs in the top-3 RS quartile
   - Estimated effort: M (1 day in quality_gates.py)
   - Estimated lift: +0.15 PF based on RS literature (WR 55%→60% at n≥100)

   **Approach B — Macro-regime overlay:**
   - Use VIX + yield-curve state already in quality_gates.py
   - Block sector ETFs that historically underperform in current regime
   - Estimated effort: S (4h, reuse existing regime data)
   - Estimated lift: +0.10 PF, lower risk

   **Approach C — Combined RS + Macro:**
   - RS filter primary, regime as veto
   - Estimated effort: L (2 days)
   - Estimated lift: +0.25 PF (synergistic)

3. **Recommend** which approach to implement first:
   - Consider n=107 (relatively small — RS ranks need n≥50 per bucket)
   - Consider existing infrastructure (VIX/YC overlay already in `passes_smart_gate`)
   - Cite specific functions in quality_gates.py that would need modification

4. **Draft the implementation spec** for the recommended approach:
   - Input signals needed
   - Gate logic (pseudocode)
   - Test cases (3 examples)
   - Expected WR/PF improvement

## Output Format (JSON)

```json
{
  "recommended_approach": "A | B | C",
  "rationale": "paragraph",
  "estimated_pf_lift": 0.0,
  "implementation_spec": {
    "gate_function": "passes_smart_gate | passes_active_gate",
    "new_logic_pseudocode": "...",
    "input_signals": ["signal1", "signal2"],
    "files_to_modify": ["path1", "path2"],
    "effort_hours": 0,
    "test_cases": [
      {"symbol": "XLK", "regime": "risk-on", "rs_rank": 1, "expected": "PASS"},
      {"symbol": "XLU", "regime": "risk-off", "rs_rank": 4, "expected": "FAIL"}
    ]
  },
  "risk_register": ["risk1", "risk2"],
  "success_criteria": "PF≥X / WR≥Y% at n≥Z"
}
```
