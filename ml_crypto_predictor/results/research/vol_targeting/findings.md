# vol_targeting_researcher — vol-targeting on losing series doesn't help

_Generated: 2026-05-02T04:02:15.958373+00:00_

**Question:** vt_001 — Does HAR-RV vol-targeting reduce CRYPTO MDD?

**Result on forward-test ensemble (n=6884):** PF 0.409 → 0.373, MDD 100.0% → 100.0%. **Worse.**

**Reason:** vol-targeting is a risk-shaping tool, not an alpha generator. Apply to active-promoted subset only.

**Wire-up:** `alpha_engine/vol_targeted_sizer.py` already exists; caller `regime_position_sizer.py` must source from active-promoted picks, not forward-test universe.

