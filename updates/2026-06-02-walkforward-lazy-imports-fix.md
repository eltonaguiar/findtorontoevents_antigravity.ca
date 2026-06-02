# Walk-forward suite lazy-import fix (2026-06-02)

## Broken
After PR #438 merged, `python3 verified_strategies/walkforward_suite.py` crashed with `ModuleNotFoundError` for `connors_rsi2`, `faber_taa`, `etf_dual_momentum`, `crypto_donchian_breakout`, and `equity_momentum_12_1` — those strategy modules were never committed; only five crypto sleeves exist under `verified_strategies/strategies/`.

## Changed
`verified_strategies/walkforward_suite.py` — lazy imports inside each `run_*` sleeve; missing modules return `verdict: SKIP` with a note instead of aborting the whole run. Hyro sleeves (vwap, bollinger, dual_momentum crypto) still execute. Writes `dual_momentum_etf` alias when `etf_dual_momentum` row is present.

## Verified
```bash
python3 -c "import py_compile; py_compile.compile('verified_strategies/walkforward_suite.py', doraise=True)"
python3 verified_strategies/walkforward_suite.py --only hyro
python3 tools/run_verified_pilots_daily.py
```

## Follow-up
Restore missing strategy modules from lab branch or re-implement `etf_dual_momentum.py` so `--only pilot` can refresh OOS without relying on cached `WALKFORWARD_REPORT.json`.