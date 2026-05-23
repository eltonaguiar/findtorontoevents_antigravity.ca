# Session AX — Swarm Review Request
# Date: 2026-05-17
# Session: AX (following AW — APPROVE)

## Context

Session AX: Deep-dive on COMMODITY concentration cap math. Critical finding
that changes the options for advancing COMMODITY from WATCH to MONEY_READY.

## Critical New Finding — COMMODITY Concentration Cap Analysis

**Previous framing (Sessions AO/AW):**
Two pending user approval items were presented as independent alternatives:
1. Block `cta_cross_asset_tsmom` for COMMODITY (WR=12.7%, n=71)
2. Raise `CONCENTRATION_CAP_BY_CLASS = {"COMMODITY": 0.85}` (CT=F at 65.25%)

**New analysis shows they are NOT independent:**

```
Current state:
  Total COMMODITY resolved picks:  354
  CT=F picks:                      231 (65.3% — ABOVE 60% cap)
  
  cta_cross_asset_tsmom COMMODITY picks use: CL=F (n=47), NG=F (n=24)
  — NOT CT=F. These are crude oil + natural gas.

If we ONLY block cta_cross_asset_tsmom (remove 71 CL=F/NG=F picks):
  Remaining:  283 picks
  CT=F:       231 (81.6% — WORSE than current 65.3%)
  
  Result: COMMODITY concentration cap WORSENS. Still WATCH.
  
If we ONLY raise cap to 0.85:
  CT=F at 65.3% < 85% cap → concentration_capped = False
  COMMODITY meets: PF=2.15 ✓, WR=60.2% ✓, DSR=1.0 ✓, SPA_p=0.0 ✓
  Result: COMMODITY becomes MONEY_READY.

If we do BOTH (block strategy + raise cap):
  CT=F at 81.6% < 85% cap → still concentration_capped = False
  Result: COMMODITY becomes MONEY_READY, but with degraded concentration (81.6%).
```

**Conclusion:** Blocking `cta_cross_asset_tsmom` alone does NOT help COMMODITY
reach MONEY_READY. Only the cap raise (option 2) or natural accumulation of
non-CT=F COMMODITY picks can clear the concentration gate.

## Implementation Analysis

**`CONCENTRATION_CAP_BY_CLASS` does not exist in the codebase.** The code uses:
- `MAX_SYMBOL_CONCENTRATION = 0.60` (global constant in `alpha_engine/money_ready_verdict.py:67`)
- A single threshold used for all classes at `_verdict()` line 421

To implement per-class overrides, `_verdict()` at line 418-423 would need to become:
```python
class_cap = CONCENTRATION_CAP_BY_CLASS.get(asset_class.upper(), MAX_SYMBOL_CONCENTRATION)
if top_symbol_share > class_cap:
    return "WATCH"
```

This is ~3 lines of code + a new constant dict. No risk of production impact
outside the `money_ready_verdict()` return value (advisory only, not a pick gate).

**Can implement immediately pending user approval.**

## ab_analysis.yml Status

Dispatched in Session AW (run #25999062203), still in_progress at Session AX
start. Results will verify whether COMMODITY `multi_asset_cot` PF=7.71 is real
or artifact. Critical for sizing decision, but does not affect the concentration
cap analysis above.

## Current System State

| Class     | Verdict           | PF   | WR    | n   | Blocker |
|-----------|-------------------|------|-------|-----|---------|
| CRYPTO    | MONEY_READY       | 2.54 | 66.4% | 443 | — |
| COMMODITY | WATCH             | 2.15 | 60.2% | 354 | CT=F 65.3% > 60% cap |
| EQUITY    | WATCH             | 2.04 | 54.2% | 238 | No non-blocked strategy n≥20 |
| ETF       | WATCH             | 2.49 | 67.6% | 74  | No strategy n≥20 |
| BOND      | INSUFFICIENT_DATA | 0.66 | 50.0% | 12  | n=12 |
| FOREX     | NOT_READY         | 0.48 | 33.3% | 618 | Hard-blocked |

## Questions for Swarm

1. **COMMODITY path to MONEY_READY:** Given blocking `cta_cross_asset_tsmom` worsens
   CT=F concentration (65%→82%), should we recommend to the user that:
   (a) Only the cap raise to 0.85 makes sense (both options if they want to also clean
   the WR drag from cta_cross_asset_tsmom)
   (b) Or wait for natural accumulation of non-CT=F COMMODITY picks?

2. **Per-class concentration cap implementation:** Is `CONCENTRATION_CAP_BY_CLASS =
   {"COMMODITY": 0.85}` a reasonable threshold? CT=F at 65.3% is a single physical
   commodity with high fundamentals-based edge (multi_asset_cot PF=4.72, WR=75%).
   The 60% global cap was designed for crypto single-coin concentration. Is 85% too
   permissive for COMMODITY?

3. **Overall verdict:** Is Session AX APPROVE? The main contribution is the analysis
   (no code change needed immediately, pending user decisions).

## Verification

- Concentration math independently verified via `alpha_engine/data/closed_picks.json`
- `CONCENTRATION_CAP_BY_CLASS` confirmed absent from codebase (grep returns empty)
- CI: 0 stale failures
- Prior swarm verdicts: AR through AW all deepseek APPROVE
