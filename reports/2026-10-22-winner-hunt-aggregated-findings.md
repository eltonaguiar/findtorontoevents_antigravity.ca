# Winner-Hunt Aggregated Findings & Action Plan

- **Date:** 2026-10-22 (UTC)
- **Owner:** Zoo (code agent) — synthesized from three parallel investigation subagents
- **Status:** Findings/plan only — no production code modified by this doc.

## 1. What was investigated

Per user directive ("get us some top winners… expand symbols lists… pull top-10 performers today and reverse engineer… check ML algorithms state, leverage for true winners"), three parallel subagents ran:

| Track | Report | Core question |
|-------|--------|---------------|
| WIN-T1 | [`reports/2026-10-22-top10-winners-reverse-engineered.md`](reports/2026-10-22-top10-winners-reverse-engineered.md) | Who won today and why? |
| WIN-T2 | [`reports/2026-10-22-ml-stack-audit.md`](reports/2026-10-22-ml-stack-audit.md) | Which ML algorithms are validated/leverage-able? |
| WIN-T3 | [`reports/2026-10-22-community-plans-winner-leads-synthesis.md`](reports/2026-10-22-community-plans-winner-leads-synthesis.md) | What have other agents/community already found? |

## 2. Top-10 genuine winners today (WIN-T1)

From `/tmp/prod_dashboard_data.json` (generated 2026-10-22T22:14:47Z), `recent_closed` = 3,500 rows; window `closed_at >= 2026-10-19` = 376 resolved, 172 WON.

| # | Symbol | Direction | pnl_pct | Notes |
|---|--------|-----------|----------|-------|
| 1 | BNBUSDT | LONG | +21.42% | liquid major |
| 2 | RNDR-USD | LONG | +14.47% | alt |
| 3 | MSTR | LONG | +10.71% | equity |
| 4 | AVAXUSDT | LONG | +10.69% | liquid major |
| 5 | LINK-USD | LONG | +9.10% | alt |
| 6 | NEARUSDT | LONG | +7.62% | alt |
| 7 | XRP-USD | LONG | +6.98% | liquid major |
| 8 | STXUSDT | SHORT | +5.55% | two-sided |
| 9 | NEARUSDT | SHORT | +5.53% | two-sided |
| 10 | STXUSDT | LONG | +5.15% | |

### Hygiene (important)
17 rows excluded as **not genuine** — `super_signals` "strong consensus" `FORCE_CLOSED` rows close 30–70s after entry at synthetic exits (ARBUSDT +100%, LINKUSDT +48.5%/+34.3%, LTCUSDT +31.3%) and `mega_mutation` same-second TP fills (ADAUSDT SHORT +8.36% ×3). Freeze these from P&L ranking.

## 3. Common winner features (WIN-T1, n=155)

- **Direction:** LONG 65.8% (WR 42.5% vs SHORT 39.0%).
- **Asset class:** CRYPTO 78.1% + FX crosses 14.8%.
- **Source leaders:** `signal_validation` 27.1%, `alpha_engine`/`luxalgo_filters` 21.3% each, `multi_asset_copytrader` 14.8% (WR 82.1% — **but see contradiction below**).
- **Strategy families:** MomentumEMA, luxalgo_confluence, forex_rsi2_mean_reversion ≈77% of wins.
- **Top symbols:** BTC/ETH/SOL/NEAR/LINK/STX/AVAX + CADJPY=A/AUDJPY=X.
- **Close windows:** winners cluster at 14:00Z & 21:00Z.
- **Distribution:** mean +2.85%, median +2.60%.

## 4. ML-stack verdict (WIN-T2)

### VALIDATED-LEVERAGEABLE
- **`ml_gatekeeper/`** — 12-fold walk-forward lift **+4.31pp** (bootstrap CI [2.68, 5.83], p=0.0004); true holdout n=500 passed-WR **60.82% vs 52.4% (+8.42pp)**, PF **2.206**. Fresh `.joblib` (2026-10-22) on real closed trades.
- **`ml_consensus/`** — consensus-WR **56.46% vs single 45.75% (+10.71pp)** on real picks (n=147), report fresh 2026-10-22.

### PROMISING-NEEDS-VALIDATION (do NOT broadly promote)
- `ml_enhanced_*` ledger family — only 4–5 combos have PF 95% CI > 1.0 (INJUSDT_1d_lightgbm LONG PF=35.6 [9.6,∞]; DYDXUSDT_15m_ensemble LONG PF=10.4 [3.2,∞]; RENDERUSDT_1h_ensemble LONG PF=4.3; FETUSDT_1d_lightgbm LONG PF=6.0). 12/22 combos are DESTROYERs (PF<1). No live generator exists.

### STALE / BROKEN / NEGATIVE-EDGE
- Meta-model AUC 0.7358 trained 2026-03-16; `ml_enhanced_ag_picks.json` = `[]`; `ml_gatekeeper_ab_decision.json` = PENDING (no A/B data).
- `ml_crypto_predictor` v5 trained 2026-10-22 but `total_models:0` (broken).
- `crypto_ml_edge` no `.joblib`, Windows-only, overfit claims.
- `local_gpu_trainer` no weights, Windows-only.
- `crypto_gainer_ml` negative edge (PF 0.63, −205.9% PnL).
- `claude_gainer_ml` F1=0, PR-AUC 0.065.
- `ml_battleground` baseline PF 0.426 (unproven).

## 5. Community/plan synthesis (WIN-T3)

- **Corroborates** WIN-T1 & WIN-T2 exactly (top-10 one-for-one; ML lift; the 8 universe-gap symbols).
- **Key contradiction flagged:** `multi_asset_copytrader` high-WR (82.1%) is a **soft-resolution artifact** (88.9% WR with $0-loss rows) — must NOT be leaned on.
- **Consensus:** no directional asset class is PROVEN/MONEY-READY today (`money_ready` empty); scoreboard was corrupted by the frozen-exit resolver bug. Claims of proven winners (`high_trust_momentum`, `commodity_term_cot`) downgraded/rejected.
- **Best defensible product lead:** tactical-rotation allocator (Sharpe 1.48 vs SPY 1.37).

## 6. Aggregated action plan (prioritized)

### Pursue now (highest confidence)
1. **Operationalize `ml_gatekeeper` live output** — persist its pick file so dashboard sources consume it; let the A/B accumulate ≥30/sleeve. (Validated: +8.4pp WR, PF 2.206.)
2. **Wire `ml_consensus`** into the dashboard source chain. (Validated: +10.7pp WR.)
3. **Add the 8 missing proven-winner symbols to the universe:** `AUDJPY=X`, `GBPJPY=X`, `BAT-USD`, `CRV-USD`, `ZECUSDT`, `WLD-USD`, `XTZ-USD`, `MINAUSDT`.
4. **Hunt LONG in liquid crypto majors/alts** (BTC/ETH/SOL/LINK/NEAR/STX/AVAX/INJ/TIA/ARB/JUP/SUI) via `signal_validation`/`alpha_engine`/kimi; target 14:00Z/21:00Z close windows.

### Forward-cohort candidates (watch / selectively surface)
- `mega_mutation` (JUP/ENA/ADA/WIF) — but exclude instant-fill rows from P&L.
- Selective `ml_enhanced_*` LONG combos with PF CI > 1.0 (INJ, DYDX, RENDER, FET).
- AAPL RSI-reversal (10-ticker); FOREX (n=26).

### Explicit dead ends (do not pursue)
- `multi_asset_copytrader` high-WR (soft-resolution artifact), `high_trust_momentum`, `commodity_term_cot`.
- Broken/stale ML: `crypto_gainer_ml`, `claude_gainer_ml`, `crypto_ml_edge`, `local_gpu_trainer`, `ml_crypto_predictor` v5, meta-model (stale).

## 7. Caveats

- All numbers are from the prod payload snapshot as of 2026-10-22T22:14:47Z; the 3,500-row `recent_closed` cap truncates older history.
- The frozen-exit resolver bug (38 placeholder rows, now fixed) previously corrupted the scoreboard; treat any "proven" verdict from pre-fix data with skepticism.
- No production code was modified by this investigation; implementation requires a separate code task.

## 8. Sources

- `reports/2026-10-22-top10-winners-reverse-engineered.md`
- `reports/2026-10-22-ml-stack-audit.md`
- `reports/2026-10-22-community-plans-winner-leads-synthesis.md`

*Not financial advice. Research/educational only. Past performance does not guarantee future results.*
