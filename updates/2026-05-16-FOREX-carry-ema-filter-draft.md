# FOREX Carry + EMA Filter — Draft Design (2026-05-16)

## 1. Problem Statement

FOREX is the worst-performing asset class in the audit dashboard:

| Metric | Value |
|--------|-------|
| Profit Factor | **0.27** |
| Win Rate | **~27%** |
| LONG status | **Blocked until 2026-05-22** (PF 0.80 vs SHORT PF 8.11) |

The class suffers from a structural lack of edge: many picks trade *against* the interest-rate differential (negative carry) and/or fight the prevailing EMA trend. The `DAILY_IDEAS_PROMPTS.MD` prompt #8 (line 779) explicitly recommends a **carry-trade + trend-filter model** for FOREX.

## 2. Filter Logic

### 2.1 Helper Function

**Location:** `audit_trail/quality_gates.py` — `evaluate_forex_carry_ema_filter(pick)`

**Scope:** `asset_class == "FOREX"` only. All other classes return `(0, "")`.

**Checks:**

1. **Carry alignment**  
   Looks up `alpha_engine.config.FOREX_SYMBOLS[symbol]["carry_yield_diff"]` (annualized base - quote rate).  
   - LONG is valid only when `carry_yield_diff > 0` (long the high-yielder).  
   - SHORT is valid only when `carry_yield_diff < 0` (short the low-yielder).

2. **EMA trend alignment**  
   Extracts `ema_20` / `ema20` from the pick dict (top-level or `extra`).  
   - LONG is valid only when `price > ema20`.  
   - SHORT is valid only when `price < ema20`.

**Scoring output:**

| Condition | Score Delta | Penalty Label |
|-----------|-------------|---------------|
| Both carry AND EMA fail | **-20** | `forex_carry_ema_both_fail` |
| Carry only fails | **-10** | `forex_carry_against` |
| EMA only fails | **-10** | `forex_ema_misaligned` |
| Either passes, or data missing | **0** | *(none)* |

### 2.2 Data Sources

| Field | Source | Fallback |
|-------|--------|----------|
| `carry_yield_diff` | `alpha_engine.config.FOREX_SYMBOLS` | `None` → skip check |
| `ema20` | `pick["ema_20"]` → `pick["ema20"]` → `pick["extra"]["ema_20"]` | `None` → skip check |
| `price` | `pick["entry_price"]` → `pick["price"]` → `pick["close"]` | `0` → skip check |

## 3. Expected Impact

- **Target:** Lift FOREX PF from 0.27 → >1.0 and WR from ~27% → >45% on the *surviving* subset.
- **Mechanism:** Penalizes the worst trades (fighting both carry and trend) by -20, pushing them below the Smart-Picks threshold (60) and, in extreme cases, below the Active display floor (40).
- **Conservative estimate:** If 30-40% of current FOREX picks are carry+EMA misfits, removing or demoting them should at minimum halve the loser count, bringing the class PF into the 0.8-1.2 range.

## 4. Kill-Switch

```bash
# Disable the filter entirely (returns 0 penalty for all picks)
export FOREX_CARRY_EMA_FILTER_DISABLED=1
```

Default is **OFF** (`0`), meaning the helper computes penalties when called.  
Because the helper is **not yet wired into the scoring pipeline**, the kill-switch is currently a no-op safety measure for the integration phase.

## 5. Rollback Plan

1. **Immediate:** Set `FOREX_CARRY_EMA_FILTER_DISABLED=1` in the environment. No code change required.
2. **Short-term:** Comment out or remove the call site in `_apply_score_penalties` (one line).
3. **Long-term:** Revert the commit that added `evaluate_forex_carry_ema_filter` + `_get_forex_carry_yield` + `_get_pick_ema20`.

## 6. Integration Checklist (NOT YET DONE)

- [ ] Back-test the filter on the last 90 days of closed FOREX picks (target: PF>1.0, WR>45, n>30).
- [ ] Wire the helper into `_apply_score_penalties` (~line 3438, next to the existing FOREX short-bias logic).
- [ ] Add a mirrored hard-reject in `passes_active_gate` if the penalty drops the raw score below the non-crypto floor (optional).
- [ ] Verify EMA20 fields are populated by the upstream FOREX scanners; if not, back-fill or switch to a SMA/HTF bias proxy.
- [ ] Update `AGENTS.md` or skill docs if the filter becomes permanent.

## 7. References

- `DAILY_IDEAS_PROMPTS.MD` line 779 — “💱 Forex: carry‑trade + trend‑filter model”
- `alpha_engine/config.py` lines 552-600 — `FOREX_SYMBOLS` carry-yield table
- `audit_trail/quality_gates.py` lines 3421-3437 — existing FOREX short-bias penalty (precedent)
- `audit_trail/quality_gates.py` lines ~5182+ — `evaluate_forex_carry_ema_filter` draft function
