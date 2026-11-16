# Audit Quant Fixes — Round 4 (2026-11-16)

Seat: `inbox/gx10-c9b9/auditpage-v2/glyph-cluster`
Branch: `fix/audit-quant-fixes-round4-2026-11-16`
Follow-up to: #849 (findings), #853 (round 1), #858 (round 2), #863 (round 3).

## Fix

### `PortfolioCircuitBreaker` auto-flatten was a no-op stub

`portfolio_circuit_breaker.py::_flatten_all_positions` only logged. It is now a
real hook: `BreakerConfig.flatten_callback` is an optional callable that receives
the breaker and returns the number of positions it closed. When absent or when
the callback fails, the method returns 0 and logs explicitly instead of
silently claiming to have flattened.

A regression test (`tests/test_portfolio_circuit_breaker_flatten.py`) asserts:
- a callback is invoked and its return value reported,
- absence returns 0 without error,
- callback failure is contained,
- `auto_flatten_on_trigger=False` skips the callback.

## Files edited

| Path | Change |
|---|---|
| `portfolio_circuit_breaker.py` | `BreakerConfig` gains `flatten_callback`; `_flatten_all_positions` now calls it, returns the count, and logs when the callback is missing or fails |

## Files added

| Path | Purpose |
|---|---|
| `tests/test_portfolio_circuit_breaker_flatten.py` | 4 tests covering callback success, absence, failure, and disabled auto-flatten |
| `updates/2026-11-16-audit-quant-fixes-round4.md` | this document |

## Verification

- 4 new tests pass.
- `node --check dashboard_enhancements.js` and `pytest` on the previous round suites still pass.
- No change to any emitter, resolver, or sizing path.

## Remaining (posted to COMS)

See the consolidated list in `docs/audit-quant-review-2026-11-16/FINDINGS.md` §11
and the COMS message sent after this commit. The top remaining items are:

1. `record_resolution` wiring (needs a market→pick mapping).
2. Walk-forward embargo (no purge gap between train and test windows).
3. `PortfolioKellyVaR` hot-path wiring.
4. PBO / n_eff / clustering fixes.
5. P2 sizing, ML drift PSI, PM CLV/depth, negative-prob guard, live correlation gate, crypto funding/stablecoin/weekend guards.

All four executed rounds are documented in the `updates/2026-11-16-audit-quant-fixes-round*.md` files.
