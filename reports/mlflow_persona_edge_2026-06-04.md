# MLflow + Statsmodels: Persona-Edge Scan Findings (2026-06-04)

Operator asked how to apply mlflow + statsmodels more deeply, including to persona picks (the personas behind `/audit/ai-tournament.html`).

## What was shipped this turn

**`tools/mlflow_persona_edge_scan.py`** — scans every persona × asset_class cell in tournament_picks with n>=10 closed; computes WR/PF/avg/cum/MDD + Augmented Dickey-Fuller test on cumulative pnl curve; logs to mlflow.db.

## Standout edges discovered (persona × class, n>=15, WR>=60%, avg>=+0.5%)

| Rank | Persona | Class | n | WR | PF | avg pnl | cum pnl | MDD | ADF verdict |
|---|---|---|---:|---:|---:|---:|---:|---:|---|
| 1 | **cta_trend** | COMMODITY | 15 | **86.7%** | **12.0** | **+7.15%** | **+107%** | **-7.2%** | TRENDING_UP |
| 2 | **macro_hedge** | COMMODITY | 18 | 77.8% | 5.0 | +5.21% | +94% | -7.6% | TRENDING_UP |
| 3 | gamma_raid | PENNY | 18 | 61.1% | 1.89 | +4.57% | +82% | -50.7% | TRENDING_UP |
| 4 | **trend_continuation** | ETF | 25 | 76.0% | 3.76 | +1.80% | +45% | -6.0% | TRENDING_UP |
| 5 | momentum_breakout | CRYPTO | 25 | 60.0% | 2.00 | +2.07% | +52% | -11.9% | TRENDING_UP |
| 6 | deep_value | ETF | 26 | 61.5% | 1.68 | +0.57% | +15% | -7.8% | TRENDING_UP |

**Bonus (n<15 cutoff but extreme)**: `momentum_momentum × EQUITY` — n=12, WR **91.7%**, PF 22.4, avg +9.5%, cum +114%, MDD -5.3%.

## Anti-edges (operator should avoid)

| Persona | Class | n | WR | avg | Verdict |
|---|---|---:|---:|---:|---|
| flight_to_safety | BOND | 19 | 10.5% | -3.03% | MEAN_REVERT (ADF p=0.000) — anti-edge |
| microcap_momentum | PENNY | 19 | 31.6% | -4.40% | TRENDING_DOWN |
| momentum_scalp | CRYPTO | 11 | 36.4% | -6.43% | MEAN_REVERT — volatile loser |

## Why this is high-leverage

1. **Persona-level signals beat model-level signals** because they isolate the *prompting style*, not the underlying model. The same model + different persona = different edge.
2. **mlflow lets the operator query/filter every cell** — e.g., "show me all personas with WR>=70% on COMMODITY since 2026-05-01" — in the local UI at `:5000`.
3. **statsmodels ADF reveals durability** — TRENDING_UP at ADF p>0.5 means the persona's winning streak hasn't reverted (durable edge); MEAN_REVERT (p<0.05) means streaks reverse (size up after losses).
4. **No cloud** — local SQLite, 1 MB, version-controlled by git ignore (mlflow.db gitignored).

## Three concrete deeper mlflow applications going forward

1. **Auto-log every tournament submission** — when `tools/ai_tournament/ingest_to_db.py` writes a new tournament_pick row, also log a one-line snapshot to mlflow with (model_id, persona, asset_class, predicted direction). Enables full provenance lookup later.

2. **Per-strategy ARIMA forecast bands** — extend `tools/forecast_consensus_picks.py` to run ARIMA(1,1,1) on every active alpha_engine strategy's cumulative pnl curve. Surface "strategies at <30d 95% CI lower bound" as kill candidates.

3. **DSR / PSR via statsmodels** — implement Deflated Sharpe Ratio (Lopez de Prado AFML eq 14.5) using statsmodels for the moments, log to mlflow per strategy. Closes the institutional-readiness gap noted in CLAUDE.md (need DSR>=0.95).

## Current mlflow.db state

- **persona_edge_scan_2026-06-04**: 55 runs
- **forecast_consensus_picks_2026-06-04**: 9 runs
- **verified_strategies_post_incident_94**: 6 runs
- **Default**: 0 runs
- **Total**: 70 runs, mlflow.db = ~1069056B local SQLite
