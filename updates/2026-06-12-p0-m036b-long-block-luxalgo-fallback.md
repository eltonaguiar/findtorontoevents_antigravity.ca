# P0 stop-bleed: M-036b CRYPTO LONG block + luxalgo SHORT fallback

**Date:** 2026-06-12  
**PR branch:** `feat/p0-m036b-long-block-luxalgo`

## What changed

### M-036b — Sized-lane CRYPTO LONG block
- `alpha_engine/config.py`: added `CRYPTO_BLOCKED_DIRECTIONS_SIZED` (`BUY`, `LONG`, `STRONG_BUY`).
- `audit_trail/quality_gates.py`: blocks sized CRYPTO longs; **exempts** `forward_test_only` / june2026 shadow picks (`forward_observation`, `paper_pilot`).
- Kill-switch: `CRYPTO_SIZED_LONG_BLOCK=0`.

### P0-4 — Fear-greed kill
- `alpha_engine/emitter_discipline.py`: `st_fear_greed_contrarian` + `crypto_fear_greed_contrarian` added to `HARD_KILL_STRATEGIES`.

### P0-1 — luxalgo SHORT emission
- New `alpha_engine/june2026_research_candidates.py`: forward observation v2 picks; **luxalgo SHORT fallback** when scanner empty (NEAR/SOL/AVAX probation symbols).
- `alpha_engine/priority_picks_emitter.py`: wires june2026 forward observation batch (`JUNE2026_FORWARD_OBSERVATION=1` default).

### Tests
- `tests/test_crypto_gates_p0.py`: `TestM036bCryptoSizedLongBlock` (4 cases).

## Verification

```bash
cd .worktrees/p0-stop-bleed
python3 -m pytest tests/test_crypto_gates_p0.py::TestM036bCryptoSizedLongBlock -q
python3 -c "from alpha_engine.june2026_research_candidates import _generate_luxalgo_short_v2; print(len(_generate_luxalgo_short_v2()))"
python3 -m alpha_engine.priority_picks_emitter --dry-run | head -20
```

## Expected impact

- Stops sized CRYPTO LONG bleed (intrabar WR ~30% on LONG n=1050).
- Keeps forward measurement lane open for luxalgo SHORT probation (n→100 target).
- Removes fear-greed contrarian from emitter discipline pass-through.
