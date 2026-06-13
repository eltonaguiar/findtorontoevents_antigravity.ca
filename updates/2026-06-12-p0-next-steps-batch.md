# P0 next steps batch — P0-B completion + P1-2 tournament UI

**Date:** 2026-06-12  
**Branch:** `feat/p0-next-steps-batch`

## Changes

1. **Cherry-pick PR #565** — M-036b CRYPTO sized LONG block, luxalgo SHORT fallback, june2026 forward obs.
2. **P0-B completion** — `insert_pick()` in `backfill_local_sources.py` now calls `is_emission_allowed()` (was only on `insert_outcome`).
3. **Expanded HARD_KILL** — `futures_momentum`, `prediction_market_consensus`, `rsi_bounce`, etc.
4. **P1-2** — `ai-tournament.html` leaderboard shows **n excl** column (`n_excluded_untrustworthy`).

## Verification

```bash
pytest tests/test_crypto_gates_p0.py::TestM036bCryptoSizedLongBlock tests/test_emitter_discipline_p0b.py -q
node tools/check_syntax.js audit_dashboard/ai-tournament.html  # if available
```
