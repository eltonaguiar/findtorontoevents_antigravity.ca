# Pre-Registered Experiment Plan — Crypto (`C1_Crypto_Funding_And_Trend`)

- **Trial ID:** `C1` (`Plan/crypto/PLAN.md`)
- **Gap Filled (citing `00_inventory.csv` / `harvested_ideas/crypto.md`):** Prior crypto systems (`CRYPTO n=1,966` closed picks in `live_dashboard_payload.json`; `TESTING_PROTOCOL.MD` canonical `PF=0.879, MDD=100%`; `112+` ML variants quarantined; intrabar SL collisions hiding `-67.5pp` in `tools/stop_fill_replay.py`; `FET` `237%` PnL concentration) relied on short `1h–4h` scalp/swing indicators with unmodeled taker slippage/funding drag and optimistically resolved `TP/SL` bars.
- **Hypothesis:** A causal higher-timeframe BTC trend-following strategy (`EMA(24) > EMA(168)` + `48h` Donchian breakout + inverse-ATR volatility position sizing + intrabar `Low<=SL` conservative stop-first exit ordering) improves risk-adjusted return over `CRYPTO` short-timeframe `/audit` picks, **but** after realistic `20 bps` round-trip taker+slippage fees, OKX funding drag (`data/funding_rate_archive/`), `DSR(N=646)`, and a 3-month single-regime sample window (`2,161` 1h bars), neither `C1` bar-level nor the `/audit` crypto cohort passes all 10 Proof Standard gates for live real-money deployment.
- **Data Sources (3 verified local datasets):**
  1. Primary hourly bar backtest (`C1`): `data/cache/BTCUSDT_3mo_1h.csv` (`2,161` hourly OHLCV bars, `2025-12-08 01:00 UTC` → `2026-03-08 01:00 UTC`).
  2. Live funding carry audit: `data/funding_rate_archive/{BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,XRPUSDT}.jsonl` (`154` 8-hour OKX funding prints per symbol, `2026-04-16` → `2026-06-06`).
  3. Live closed cohort audit (`C1_live_cohort`): `live_dashboard_payload.json` (`CRYPTO` closed picks, `n=1,966`, chronological OOS split).
- **Timeframe & Signal Construction (`C1` Hourly Causal Trend):**
  - Strictly causal indicators shifted by `1` bar (`t-1` decides entry at `Open[t]`): Long only when `Close[t-1] > max(High[t-L:t-1])` and `EMA_fast(t-1) > EMA_slow(t-1)`.
  - Pre-registered grid: Donchian lookback `L in {24, 48, 72}` hours; ATR stop multiple `k_sl in {1.5, 2.0, 2.5}` (TP = `2.0 * k_sl`, time-stop `72h`). Intrabar rule: if both `Low <= SL` and `High >= TP` occur in the same bar, fill `SL` first (conservative parity with `tools/stop_fill_replay.py`).
- **Cost & Canadian Tax Model:** `10 bps` one-way (`20 bps` round-trip taker fee + slippage; breakeven sensitivity `0 -> 50 bps`) plus 8-hour perp funding cost/yield sensitivity (`~0.16 bps/8h` empirical BTC mean); Canadian CRA crypto taxation (`26.76%` Ontario top cap gains for investor vs. `53.53%` business income for active high-turnover trading).
- **Benchmark:** `BTCUSDT` Buy-and-Hold over matched `2025-12-08` → `2026-03-08` window (and `0%` zero-alpha null on per-trade returns).
- **Proof Standard Tests Targeted (§6):** All 10 steps (`Temporal`, `WFO`, `DSR N=9 & N=646`, `Plain + Block MC`, `Friction + Breakeven`, `Bootstrap CI & t-stat`, `Regime Split`, `200-run Shuffle Control`, `Tracker Registration`, `Seed=42 Reproducibility`).

