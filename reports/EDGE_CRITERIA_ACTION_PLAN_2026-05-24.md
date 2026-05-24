# Swarm Synthesis — Edge Criteria Action Plan (2 engines)

**Date:** 2026-05-24 | **Engines:** DeepSeek (deepseek-v4-flash), Cerebras (gpt-oss-120b)
**OpenRouter returned empty — excluded from synthesis.**

---

## Consensus Rankings

| Rank | Item | DeepSeek | Cerebras | Consensus |
|------|------|----------|----------|-----------|
| 1 | P1 — Persona_WR confidence proxy | 2 | 3 | **P1** (both agree it's foundational) |
| 2 | P0 — Regime label leakage audit | 1 | 4 | **P0** (disagreement on urgency, agree on importance) |
| 3 | Additional — FOREX exclusion | 5 | 2 | **FOREX** (both agree it's low-effort) |
| 4 | P2 — Whale consensus boost | 3 | 1 | **P2 Whale** (disagreement on preconditions) |
| 5 | P2 — Dashboard migration | 4 | 5 | **P2 Dashboard** (both agree it's maintenance) |
| 6 | P3 — Position sizing rules | 6 | 6 | **P3** (both agree it's last, depends on P1+P0) |

## Key Disagreements

### 1. P0 vs P1 ordering
- **DeepSeek:** P0 first — "data integrity issue, not an optimization. If labels leak forward data, all regime-based strategies are invalidated."
- **Cerebras:** P1 first — "without a confidence signal the Kelly formula collapses to zero exposure. Restoring it unlocks all risk-budget logic."
- **Resolution:** Both are independent and can be parallelized. Do both in Sprint 1.

### 2. Whale boost preconditions
- **DeepSeek:** Implement now — "2 whales can still provide consensus. Still worth implementing."
- **Cerebras:** Defer until ≥2 whale profiles have real addresses — "boosting confidence on speculative whale signals could introduce hidden bias."
- **Resolution:** Implement now with a guard: only apply boost if ≥2 whales with verified addresses agree. If <2 verified whales exist, log a warning and skip.

### 3. FOREX: zero-allocate vs faded signal
- **Both agree:** Zero allocation is the right first step.
- **Cerebras:** "Kill the inverse signal idea — the statistical evidence strongly suggests the signal is bad, not merely mis-scaled."
- **Resolution:** Zero-allocate FOREX immediately. Kill the faded signal experiment.

## Final Action Plan

### Sprint 1 (now) — Foundation fixes (parallelizable)

| # | Item | File(s) | Lines | Verification |
|---|------|---------|-------|-------------|
| 1 | **P1 — Persona_WR → confidence** | `alpha_engine/score_booster.py` ~line 45, `alpha_engine/scanner.py` | ~5 | `SELECT confidence FROM tournament_picks LIMIT 10` → non-zero |
| 2 | **P0 — Regime label timestamp audit** | `alpha_engine/regime_flip_detector.py`, `alpha_engine/regime_position_sizer.py` | ~25 | Assertion: no label timestamp > pick timestamp |
| 3 | **FOREX — Zero allocation** | `alpha_engine/scanner.py` filter stage | ~8 | `SELECT COUNT(*) WHERE asset_class='FOREX'` → 0 |
| 4 | **P2 Dashboard — picks → tournament_picks** | `audit_dashboard/template.html`, `audit_trail/dashboard_generator.py` | ~30 | Dashboard shows 3,149 rows |

### Sprint 2 (after P1) — Confidence enhancements

| # | Item | File(s) | Lines | Verification |
|---|------|---------|-------|-------------|
| 5 | **P2 Whale — consensus boost** | `alpha_engine/score_booster.py` ~line 210 | ~15 | Unit test: 0/1/2 whales → 0.00/0.00/0.10 boost |
| 6 | **P3 — Position sizing rules** | `alpha_engine/regime_position_sizer.py`, `alpha_engine/scanner.py` | ~80 | Unit tests for all 5 rules |

## Dependency Graph

```
Sprint 1 (parallel):
  P1 ─────────────────────┐
  P0 ─────────────────────┤
  FOREX exclusion ────────┤ (all independent)
  P2 Dashboard migration ─┘

Sprint 2 (sequential on P1):
  P1 ──→ P2 Whale boost ──→ P3 Position sizing
  P0 ──→ P3 (needs clean regime labels)
```

## Deferred / Killed

| Item | Decision | Rationale |
|------|----------|-----------|
| FOREX faded signal | **Killed** | Both engines agree: signal is bad, not mis-scaled. Inverting would amplify losses. |
| Full regime-flip detector rewrite | **Deferred** | Timestamp assertion mitigates the worst leakage. Re-architect only if audit finds actual leakage. |
| Whale boost (if 0 verified addresses) | **Deferred** | Guard clause: skip if <2 verified whale profiles exist. |

## Risk Flags

1. **P0 is the only item that could kill a strategy.** If regime labels leak forward data, `regime_adaptive` must be frozen immediately.
2. **P1 is a band-aid.** Using persona_WR as confidence is temporary. Long-term: proper calibration layer.
3. **P3 depends on both P1 and P0 being correct.** Don't implement Kelly sizing on broken confidence or leaked labels.
