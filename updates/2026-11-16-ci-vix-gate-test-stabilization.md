# CI test stabilization: VIX gate masked the wf_verdict and Phase-1 tests

Date: 2026-11-16 evening. Seat `inbox/gx10-c9b9/auditpage/grok-4-7`.

## Symptom

CI on `main` and on every audit PR showed **22 failures**, always the same ones:

- `tests/test_wf_verdict_failing_gate.py` — 8
- `tests/test_wf_verdict_null_block.py` — 12
- `tests/test_phase1_active_gates.py` — 2 (`test_non_crypto_not_gated` in the dead-zone and TOD classes)

`main` run 43949645139: `22 failed, 6738 passed`. PR 856 run 43949904751: `22 failed, 6739 passed`.

## Root cause

Not the wf_verdict logic and not Phase-1. `audit_trail/quality_gates.py` `passes_vix_regime_active_gate` added per-class VIX gates after these fixtures were written:

- EQUITY rejected when live VIX > 22 (`EQUITY_VIX_GATE_ENABLED`, default ON)
- ETF rejected when live VIX > 25 (`ETF_VIX_GATE_ENABLED`, default ON)

Both test files use an EQUITY `AAPL` base pick (chosen in 2026-06-13 to dodge the CRYPTO gates). Live VIX was above 22, so `passes_active_gate` returned False for the *unrelated* reason `equity_vix_gate_high_vix` and the assertion under test never ran. The result therefore depended on the market, not on the code.

## Change

Test-only. No production gate was weakened and no threshold moved.

- `tests/test_wf_verdict_failing_gate.py` and `tests/test_wf_verdict_null_block.py`: module-level autouse fixture sets `VIX_REGIME_ACTIVE_GATE_ENABLED=0`, `EQUITY_VIX_GATE_ENABLED=0`, `ETF_VIX_GATE_ENABLED=0` via `monkeypatch`.
- `tests/test_phase1_active_gates.py`: same three keys added to the `_ClearPhase1Env` save/neutralize list, matching the existing pattern used for `CRYPTO_PRODUCTION_BLOCK_LONG`, `CONCENTRATION_CAP_ENABLED`, etc.

Production behaviour is unchanged: the VIX gates stay ON by default. The kill-switches are the documented ones in `quality_gates.py`.

## Verification

```
python3 -m pytest tests/test_wf_verdict_failing_gate.py \
  tests/test_wf_verdict_null_block.py tests/test_phase1_active_gates.py -q
# 61 passed, 10 subtests passed
```

Broad local run: `1044 passed, 22 skipped` before hitting `tests/test_combined_book_reproduction.py::test_research_dataset_reproducible_subset`, which fails **locally only** because `combined_book/data/kfrench/Portfolios_Formed_on_OP.txt` is absent from this worktree. It is not one of CI's 22 and was not in the CI failure list.

## Unrelated state at the same time

- Live https://findtorontoevents.ca/audit/ now passes `tools/audit_honesty_live_check.py` (`LIVE_OK`). The honesty text is deployed.
- PR 843 (banner honesty) and PR 848 (fail-closed money-ready) are merged.
- PR 856 (dashboard `new_picks` int crash) is still open. With a green CI it can merge; the crash still breaks a future generator run.
