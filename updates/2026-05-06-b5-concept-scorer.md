# B5 — Cursor Phase 3: Concept-Aware Scoring (shadow mode)

**Date:** 2026-05-06  
**PR:** feat/b5-concept-scorer-2026-05-06  
**Status:** open — awaiting human merge

## What shipped

- **`alpha_engine/concept_scorer.py`** (new) — `compute_concept_modifier(pick, strategy_perf)`
  returns `{pts, family, shadow_on, gated, reason}`. Default: `CONCEPT_SCORING_SHADOW=0` →
  always returns `pts=0`, zero production impact.
- **`alpha_engine/elite_scorer.py`** — added section 13 hook (lines ~2744–2760) that calls
  `compute_concept_modifier` and merges `concept_modifier` into the score/breakdown.
  Wrapped in `except Exception` so any import failure is silent.
- **`audit_trail/quality_gates.py`** — appended `concept_gate_shadow_audit(pick)` helper
  (read-only; explainability only; never changes `passes_active_gate`).
- **`tests/test_concept_scorer.py`** — 25 tests; all using `unittest.mock.patch` (no
  `sys.modules` poisoning); covers shadow-off, ungated families, skyrocket/tradingagents
  gates, `fwd_wr=0.0` vs `None` edge case, `concept_gate_shadow_audit` integration.

## Modifier table

| Family | pts (shadow ON) | Gate |
|---|---:|---|
| `skyrocket` | +3 | n_closed ≥ 30 AND fwd_wr ≥ 50% |
| `tradingagents` | +2 | n_closed ≥ 30 AND fwd_wr ≥ 55% |
| `long_term_value` | +1 | unconditional |
| `penny_stock` | -1 | unconditional |
| `reverse_engineer` | -1 | unconditional |
| `meme_coin` | -2 | unconditional |
| `standard` / `mercury2` | 0 | n/a |

All pts bounded to [-3, +3].

## What changed vs PR #764 (closed without merge)

Four blockers from the PR review were fixed:
1. **`elite_scorer.py` section 13 hook now committed** (was only in PR description prose).
2. **`concept_gate_shadow_audit` now committed** to `quality_gates.py` (was missing).
3. **No `sys.modules` poisoning** — tests use `importlib.reload` + `unittest.mock.patch`.
4. **`fwd_wr=None` vs `0.0` handled correctly** — fallback only applies when `None`,
   not when the caller passes an explicit `0.0`.

## Enabling the shadow run

```
CONCEPT_SCORING_SHADOW=1
```

Earliest safe enable: 2026-05-13 (≥7 days from merge).

## Wire-Up Rule

**Wired:** production caller is `alpha_engine/elite_scorer.py::compute_elite_score` section 13.
No opt-in flag needed — the wiring is in the diff.

## References

- Action item: `reports/REMAINING_ACTION_ITEMS_2026_04_30.md` §4 B5
- Prior attempt: PR #764 (closed without merge 2026-05-05)
