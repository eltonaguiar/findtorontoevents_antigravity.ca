# Quant audit v2 — calibration sources & guardrails

## Paper trading data must not drive calibration

Trades under `paper_trading/data/` may lack real TP/SL discipline (e.g. `tp:0`, `sl:0`) and are **not** representative for confidence calibration, threshold fitting, or walk-forward labels.

**Use only:**

- `antigravity_closed_picks_*.csv` (full book with real TP/SL where recorded), and/or  
- `audit_dashboard/data/dashboard_data.json` → `picks.recent_closed`, and/or  
- `alpha_engine/data/closed_picks.json` for engine-local backtests.

Do **not** use `paper_trading/data/` rows as the primary population for Platt scaling, isotonic calibration, or gate threshold selection.

## HC filter backtests before deploy

Run:

```bash
python tools/backtest_hc_filter.py
python tools/hc_filter_backtest.py
node tools/hc_csv_backtest.js tools/fixtures/sample_hc_picks.csv
```

## Portfolio mandates

See `config/portfolio_mandate.json`: which named portfolios are **full-gate**, **relaxed consensus test**, or **cash/sidelined**. Enforce at **placement** / bus routing, not inside `passesHighConvictionPick`.

## Correlation

Pre-placement correlation checks live in `tools/portfolio_correlation_gate.js` (portfolio-level), not in the HC filter.

## Time-of-day (v2)

Optional UTC “dead zones” belong in a future gate or scoring layer; document thresholds before enabling in production.
