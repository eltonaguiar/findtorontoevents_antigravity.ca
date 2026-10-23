# Audit prediction integrity and candidate verification

## What was broken

The live `vt_equity_two_day_rsi_reversal` adapter emitted every historical
research signal on each scan. Its shared converter discarded the signal's
original timestamp and labeled this daily strategy as `1h`. Old entry
opportunities could therefore be presented as new predictions.

The Hyro performance validator mixed Alpha fractional returns with candle-replay
percentage-point returns. It also awarded TP before SL on ambiguous candles,
could inspect a candle before entry or before its close, prematurely expired
incomplete holding windows, and valued expiry using a bar beyond the hold limit.

## Changes

- The equity adapter emits only signals on the latest input bar and preserves
  its timestamp, daily timeframe, bar index and research holding-period metadata.
  The research strategy still returns historical signals for its research callers.
- Hyro converts Alpha `closed_picks.json` fractional `pnl_pct` values to
  percentage points at ingestion. Explicit `pnl_percent` and the separate
  dashboard-payload path are not multiplied.
- Candle replay excludes pre-entry and unclosed candles, applies SL first on
  ambiguous bars, keeps incomplete horizons pending, and stops exactly at the
  configured bar limit.

These are measurement and signal-integrity repairs, not newly proven trading
strategies. Historical DB rows have not been rewritten.

## Verification

Before the fixes: six equity-adapter regression cases failed; seven Hyro
integrity cases failed. After the fixes, the combined focused suite passed:

```sh
python3 -m pytest tests/test_vt_equity_reversal_live.py tests/test_vt_baby_strategies_pead.py tests/test_hyro_performance_integrity.py tests/test_copytrader_active_lifecycle.py -q --tb=short
# 89 passed
python3 -m py_compile alpha_engine/vt_baby_strategies.py tools/hyro_pick_performance_validator.py
# passed
```

The suite includes a real historical equity-strategy calculation, not only
mocked signals; long/short unambiguous exits; ambiguous exits; entry and candle
boundaries; holding-window boundaries; and separate ingestion unit contracts.

## Production wiring and limits

Existing callers already invoke both repaired functions:
`alpha_engine/scanner.py` includes `VT_BABY_STRATEGIES`, and
`.github/workflows/audit-dashboard.yml` invokes the Hyro validator before its
ML optimizer. No new orphan integration was introduced.

The local test run does not establish deployment. These fixes must reach
production main and complete their existing scanner/dashboard workflows before
the live outputs reflect them. A local FTP upload of Python cannot update the
GitHub Actions checkout. No dashboard generator or scanner was run locally.

The live Hyro actual-fill journal is empty. Its performance JSON also imports
Alpha closed records; those are not independent Hyro fills. MFE/MAE estimates,
expired-trade accounting in aggregate scores, anonymous strategy attribution,
and historical outcome provenance still need separate validation before any
money-ready promotion.

See [candidate-verification evidence](../reports/prediction_integrity_edge_check_2026-10-22.md).

*Not financial advice. Research/educational only. Past performance does not guarantee future results.*
