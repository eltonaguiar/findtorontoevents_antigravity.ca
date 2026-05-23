# Toxic system blocks — 2026-04-15 audit dashboard review

Cross-check: April 15, 2026 performance analysis on findtorontoevents.ca/audit (closed-book PF, source breakdown). The following sources showed profit factor near zero or sustained negative expectancy in the dominant crypto book and dilute headline metrics:

- `breakout_b_ml` — forward signals underperforming vs baseline
- `mega_mutation` / genome mutation lane — PF near 0.03 in audit slice
- `goldmine_stocks` — equity competition-style bleed (~19% WR in review)

**Action:** Added to `BLOCKED_SOURCE_SYSTEMS` in `audit_trail/quality_gates.py` so picks are hidden from dashboard aggregation paths that respect the block list.

**Reversal:** Remove from the block set only after closed-book rehab (n≥30, PF≥1.0, Wilson CI) and `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` mutation/DNA protocol sign-off.
