# 2026-04-28 PEAD Wire-Up (vt_baby) — Goal #1

## What was missing

PEAD had research/docs and strategy modules in-repo, but no production caller in the scanner path that could emit PEAD picks from real earnings surprise data.

## What changed

- Added `vt_equity_earnings_drift_pead()` in `alpha_engine/vt_baby_strategies.py`.
- Registered strategy key `vt_earnings_pead` in `VT_BABY_STRATEGIES`.
- Wired with a safety gate: only active when `UEPS_ENABLE_PEAD=1`.
- Data source is real cache input only: `data/earnings/<SYMBOL>/latest.json`.
- Added recency guard: only uses earnings surprises from the last 1-7 days.
- Added resilient import fallback for `_signal_to_dict` to support both script and package test contexts.

## Why this is safe

- Default behavior unchanged (`UEPS_ENABLE_PEAD` is OFF unless explicitly enabled).
- No placeholder data; only live/real cached earnings surprise payloads are used.
- Non-equity instruments are filtered out.

## Verification

- `python -m pytest tests/test_vt_baby_strategies_pead.py -q`
  - Result: `3 passed`
- `python -c "import py_compile; py_compile.compile('alpha_engine/vt_baby_strategies.py', doraise=True)"`
  - Result: `py_compile ok`

## Next follow-up

- Open a focused PR for this PEAD wire-up.
- Add optional telemetry card in `/audit` for `vt_earnings_pead` activation and pick counts.
- Continue with BOND `LQD-HYG` credit-spread strategy wire-up in the next batch.

