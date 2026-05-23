# Asset-Class Active Gate Tightening

## What Was Broken

`passes_active_gate()` was still letting obviously weak large-sample cohorts
reach the main active book.

The clearest current examples were:

- CRYPTO `super_signals` rows with `strat_fwd_wr ≈ 34.5%` on `110` trades
- EQUITY `regime_terminal` rows with `strat_fwd_wr ≈ 41.9%` on `31` trades

Those cohorts had enough forward history to be meaningful, but the active gate
still treated them as displayable.

## What I Changed

- Added large-sample forward-WR floors in `audit_trail/quality_gates.py`:
  - CRYPTO active rows are rejected at `strat_fwd_wr < 40%` when
    `strat_fwd_trades >= 50`
  - non-crypto active rows are rejected at `strat_fwd_wr < 45%` when
    `strat_fwd_trades >= 20`
- Added regression coverage in `tests/test_quality_gates.py` for:
  - blocking weak large-sample crypto cohorts
  - blocking weak large-sample non-crypto cohorts
  - preserving stronger non-crypto cohorts above the floor

## Verification

- `python -m pytest tests\\test_quality_gates.py tests\\test_classify_pick_quality_v2.py -q`
  - `43 passed`
- Added regression tests:
  - `test_active_gate_blocks_large_sample_crypto_low_forward_wr`
  - `test_active_gate_blocks_large_sample_non_crypto_low_forward_wr`
  - `test_active_gate_keeps_large_sample_non_crypto_when_forward_wr_is_good`
- Live payload sanity check against current `audit_dashboard/data/dashboard_data.json`
  showed the active book tightening from `52` rows to `17` rows under the new
  gate, with weak `super_signals` crypto rows and `regime_terminal` equity rows
  among the dropped cohorts.
