# Ring 2.6 1T — Dashboard Stat Validation Consultation
## 2026-05-22 ~23:40 UTC

**Context:** Second-opinion review of Claude Code's stat-validation audit and fixes on `findtorontoevents.ca/audit`. Full audit details in `reports/AUDIT_STAT_VALIDATION_2026-05-22.md`.

---

## 1. Card-Math Fix (Compound Return vs Σ Trade %)

**Ring's verdict:** ✅ Keeping the sum row is correct — provides transparency and educational value about the gap between naive arithmetic sums and compound returns (which reflect volatility and position-sizing).

**Enhancement recommended:** Add trade count (N) next to both figures to give context for evaluating return percentages.

## 2. Leaky `sym_track_wr` Column vs PIT Shadow Column

**Ring's verdict:** ✅ Maintaining both columns is a sound intermediate strategy for validation and backward compatibility.

**Requirements:**
- Explicitly label the leaky column (e.g., `_LEAKY_DO_NOT_USE`)
- Document semantic differences clearly
- Establish a firm deprecation/cutover date for removal

## 3. Regression Test Coverage

**Ring's assessment:** Good foundation, but gaps exist.

**Prioritized:**
1. ✅ Verify `pnl_pct × position_size ≈ dollar_pnl` invariant
2. ✅ Add automated assertion that `_GHOST_SYSTEMS` rows are excluded from aggregates
3. ✅ Implement temporal ordering invariants
4. ✅ Include edge cases (low-N groups, all-win/loss groups, zero-pnl groups)
5. ✅ Add cross-layer reconciliation (SQL vs Dashboard code)

## 4. `meta_strategy` Ghost Row Exclusion

**Ring's verdict:** ✅ Logic is sound — the cohort is already excluded from dashboard aggregates via `_GHOST_SYSTEMS` and skipped at three collection callsites.

**Defensive measure recommended:** Add a runtime assertion to `quality_gates.py` or test suite ensuring the sum of `_GHOST_SYSTEMS` row counts in aggregate results is zero.

## 5. Single Most Important Next Step

**Ring's recommendation:** **Validated cutover of `sym_track_wr` to PIT shadow column.**

Procedure:
1. Independent validation of PIT column against hand-computed reference for a sample of groups
2. Shadow-run period in production to monitor divergences
3. Final cutover to display the PIT metric
4. Deprecation and scheduled removal of the leaky column

**Final note:** While automated testing is strong, human spot-checks against a spreadsheet or notebook are essential to verify math aligns with intended domain logic.

---

*Consultation via OpenRouter: `inclusionai/ring-2.6-1t`, max_tokens=4000, temperature=0.3*
*Time: ~30s response time*
