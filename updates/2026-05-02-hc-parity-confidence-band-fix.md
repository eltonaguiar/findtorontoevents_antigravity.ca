# fix(hc-parity): remove Gate 7b from hc_gates_python.py — matches JS 2026-04-23 removal

**Date:** 2026-05-02  
**Branch:** fix/hc-parity-confidence-band-2026-05-02

## Root cause

`tools/hc_gates_python.py` (the Python mirror of `audit_dashboard/hc_filter.js`) still had
Gate 7b active:

```python
if not forex_auto_relax:
    if cf_lo <= cf <= cf_hi and fwd_n < cf_lo_fwd_min:
        return False  # confidence 0.85–0.95 + low sample
```

`hc_filter.js` removed Gate 7b on 2026-04-23 with the comment:
> "Gate 7b: REMOVED 2026-04-23 per whatif-analysis (confidence is anti-predictive on crypto).
> Previous evidence: PF 0.61 on n=126 picks — but larger analysis shows flat/non-predictive."

The JS removal was not mirrored to Python, causing 4 divergences in the `hc-parity` CI job
for `proven_vwap_mean_reversion::HYG/IWM` picks (confidence=0.9, strat_fwd_trades=8):
- JS: `passesHighConvictionPick → True` (grade-a)
- Python: `passes_high_conviction_pick → False` (Gate 7b rejects)

## What changed

`tools/hc_gates_python.py` lines 370–375: confidence band check commented out with a
reference to the matching JS change.

## What did NOT change

- `tools/dashboard_hc_rules.py` — the "server-side" implementation intentionally keeps Gate 7b
  per `test_gate7b_applies_to_non_forex` contract. This is a different codebase path.
- All 24 existing `test_dashboard_hc_rules.py` tests still pass.
- Zero new test files (the `hc-parity` workflow is the authoritative test).

## Verification

```bash
python tools/hc_parity_test.py   # divergent=0 (was 4)
python -m pytest tests/test_dashboard_hc_rules.py  # 24 passed
```
