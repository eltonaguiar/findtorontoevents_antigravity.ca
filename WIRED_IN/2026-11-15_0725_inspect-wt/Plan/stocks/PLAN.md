# Pre-Registered Experiment Plan — Stocks / Equities (`S1_Equity_Active_Picks_Cohort`)

- **Trial ID:** `S1` (`Plan/stocks/PLAN.md`)
- **Gap Filled (citing `00_inventory.csv` / `harvested_ideas/stocks.md`):** PR `#773` established `NO_ALPHA_BETA` ($t = 1.05$, median `-0.57%` vs `SPY`), and `2026-11-15_AM_profitability_plan` showed `RSI(2)` collapsed over 2020–2025. Yet the live `/audit` equity cohort (`live_dashboard_payload.json`) has never been tested as a clean **chronological walk-forward + block-bootstrap + shuffle-control + Canadian tax/commission** cohort against matched-date `SPY` / risk-free benchmarks.
- **Hypothesis:** Current live active equity pick generation (`EQUITY` closed rows in `live_dashboard_payload.json`) fails to clear statistical significance (`95%` bootstrap CI includes zero), multiple-testing (`DSR` at `N=646`), and matched `SPY` excess return once realistic `10 bps` round-trip friction + Canadian short-term ordinary/cap-gains tax is applied—unless restricted to a pre-registered regime-filtered sub-cohort.
- **Data Source:** `.inspect-wt/_audit_tmp/live_dashboard_payload.json` (`EQUITY` closed picks, excluding `pnl=0` unresolved artifacts if zero-backfill, tested both raw and clean).
- **Timeframe & Universe:** Swing (`1–14` days) across US/CA liquid equities emitted by `alpha_engine` (`rs-breakout-scout`, `donchian-stock-breakout`, `vwap-reversion-scout`, `regime_terminal`).
- **Cost & Canadian Tax Model:** `10 bps` round-trip (`0.10%` spread+slippage+SEC/ECN fees; Questrade/IBKR Canada sensitivity `0.20%`) + `26.76%` cap gains / `53.53%` active trading income sensitivity.
- **Benchmark:** `SPY` matched holding-period return proxy / `0%` excess null.
- **Proof Standard Tests Targeted (§6):** All 10 steps (`Temporal`, `WFO`, `DSR`, `MC`, `Friction`, `Significance`, `Regime`, `Shuffle`, `Tracker`, `Reproducibility`).

