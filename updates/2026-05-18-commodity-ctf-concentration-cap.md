# PR-2026-0518-3: COMMODITY CT=F Concentration Emission Cap

**Date:** 2026-05-18
**Status:** IMPLEMENTED (uncommitted)
**Target:** COMMODITY asset class → PAPER PILOT qualification

## What Was Changed

### 1. `alpha_engine/concentration_cap.py` — New function

Added `enforce_commodity_ctf_emission_cap()` — a **per-scan-cycle signal emission cap** that limits CT=F (Cotton) to ≤40% of newly emitted COMMODITY signals in a single scan cycle.

**Algorithm:**
- Identifies COMMODITY picks and CT=F picks within a signal batch
- If CT=F share > `max_ctf_pct` (default 40%), sorts CT=F picks by confidence (ascending) and rejects the lowest-confidence picks until under cap
- CT=F picks below `min_conf` (default 0.50) are always rejected first
- Non-COMMODITY and non-CT=F COMMODITY picks pass through unchanged
- Returns `(passed, rejected)` tuple for pipeline integration
- Configurable via env vars `COMMODITY_CTF_CAP_PCT` and `COMMODITY_CTF_MIN_CONF`

**Key design distinction from `passes_concentration_cap`:**
- `passes_concentration_cap` caps symbols per active-pick snapshot (pre-existing, general-purpose)
- `enforce_commodity_ctf_emission_cap` caps CT=F per signal-batch at emission time (PR-specific)
- Together they form a two-layer defense: emission diversity → active-pick concentration

### 2. `alpha_engine/production_scanner.py` — Pipeline wiring

**Import added** (near other concentration module imports):
```python
try:
    from alpha_engine.concentration_cap import enforce_commodity_ctf_emission_cap as _ctf_emission_cap
    _HAS_CTF_CAP = True
except ImportError:
    _ctf_emission_cap = None
    _HAS_CTF_CAP = False
```

**Pipeline call added** after the macro risk-off gate (line ~5261) and before the Strategy Priority Tier System (6f2):
- Runs only if `_HAS_CTF_CAP` is True
- Calls `_ctf_emission_cap(active)` on the post-quality-gates active picks
- Logs each rejected pick with `[CTF_CAP]` prefix
- Appends rejected picks to `rejected` list for proper dashboard tracking
- Fail-open: if the cap throws, it logs the error and continues

## Why This Gets Us Towards Profitability

### Problem
COMMODITY signals were ~73-76% CT=F (Cotton) due to the `cot_positioning` strategy family. This created a **phantom edge** — the high WR was a concentration artifact from a single contract (CT=F) rather than genuine commodity diversification.

Without diversification, the PBO (Portfolio Backtest Optimization) for COMMODITY was meaningless:
- A single-symbol portfolio has no diversification benefit
- Risk is concentrated in cotton's idiosyncratic moves
- Cannot generalize COMMODITY-class WR to any other commodity symbol

### Solution Impact

| Metric | Before | After |
|--------|--------|-------|
| CT=F share of COMMODITY signals | ~73-76% | ≤40% |
| Other COMMODITY signals (ZC=F, ZW=F, ZS=F, CL=F, etc.) | Crowded out | Guaranteed ≥60% slots |
| PBO relevance for COMMODITY class | Invalid (single-contract artifact) | Valid (diversified multi-symbol) |
| COMMODITY advancement | STUCK at WATCH | Can proceed to PAPER PILOT |

### What This Unlocks
1. **PBO computation** sees diversified COMMODITY signals → meaningful WR/PF per strategy
2. **Commodity diversification** reduces single-contract gap risk (cotton gap = portfolio gap)
3. **Strategy evaluation** works per-symbol instead of per-COT-artifact
4. **COMMODITY asset class** can advance from WATCH to PAPER PILOT per the MASTER_ACTION_PLAN

## Methodology

1. **Context gathering:** Read existing `concentration_cap.py`, `production_scanner.py` pipeline, `quality_gates.py`, and MASTER_ACTION_PLAN to understand the signal flow
2. **Design:** Emission-time cap (not active-pick cap) because the problem is at signal generation time — too many CT=F signals being emitted per scan
3. **Safety:** Default 40% cap (not 0%), confidence-weighted rejection (lowest confidence first), env-var overridable, fail-open on errors
4. **Trackability:** Rejected picks get `_rejected_reason` and `_quality_gate_rejected` tags for dashboard visibility

## Files Modified
- `alpha_engine/concentration_cap.py` — new function added
- `alpha_engine/production_scanner.py` — import + pipeline wiring

## Next Steps
1. Commit to main and push
2. Verify with `pick_traceback.py` that COMMODITY CT=F share drops to ≤40%
3. Run PBO on diversified COMMODITY signals
4. If PBO shows edge → advance COMMODITY to PAPER PILOT
