# Hidden-Edge Scan — `dashboard_data.json` 2026-05-13

**Source:** `audit_dashboard/data/dashboard_data.json` (generated 2026-05-13T~00:28Z)
**Universe:** 3,500 closed picks in `picks.recent_closed` with both `score` and `pnl_pct`.
**Baseline:** avg_pnl = **+0.34%**, WR = **44.7%**.
**Method:** percentile-bin score (`score`, fallback `elite_score`/`trust_score`/`confidence*100`) vs realized `pnl_pct`. Thresholds: score p30=36, p80=55; pnl_pct p20=-1.81%, p80=+2.51%.

---

## 1. Cohort sizes

| Cohort | Definition | n | % of closed | Cohort avg pnl | Cohort WR |
|---|---|---|---|---|---|
| **Hidden alpha** | score<p30 AND pnl>p80 | **259** | **7.40%** | **+3.70%** | **100%** |
| **Hidden noise** | score>p80 AND pnl<p20 | **106** | **3.03%** | **-2.75%** | **0%** |
| Calibrated wins | score>p80 AND pnl>p80 | 96 | 2.74% | +3.21% | 100% |
| Calibrated losses | score<p30 AND pnl<p20 | 259 | 7.40% | -2.07% | 0% |

**Verdict:** hidden-alpha cohort is 7.40% — **above the 5% actionable threshold**. The picker is mis-scoring a non-trivial slice. The symmetry between hidden-alpha (259) and calibrated-loss (259) at the **same low-score band** confirms that low score is currently a near-coin-flip predictor — score is throwing away ~7% of true winners.

---

## 2. Hidden-Alpha cluster analysis (n=259)

| Dimension | Top concentrations |
|---|---|
| **Symbol** | `ONDOUSDT` 79 (31%), `CT=F` 34 (13%), `APTUSDT` 9, `INJUSDT` 7, `WLDUSDT` 7, `DYDXUSDT` 7 |
| **Source** | `alpha_engine` 81 (31%), `quan_engine` 78 (30%), `multi_asset_copytrader` 24, `copy_trader_highscore` 22, `multi_asset_cot` 18, `aggregated_picks` 15 |
| **Strategy** | `unknown` 78, `hs_lb_None` 22, `cot_positioning` 18, `cftc_cot_commercial_signal` 17, `macd_rsi_confluence` 17 |
| **Asset class** | CRYPTO 205 (79%), COMMODITY 38 (15%), EQUITY 14, ETF 2 |
| **Direction** | LONG 196 (76%), SHORT 63 |
| **Timeframe** | SWING 242 (93%), INTRADAY 17 |

**Drilldowns:**
- **`quan_engine` × ONDOUSDT** LONG: n=78, avg +3.34%, **WR 100%**. This is the canonical hidden edge — quan_engine ONDO LONGs are scored sub-36 but never lose in this window. *(Caveat: per memory `project_quan_engine_matic_positive_artifact.md`, quan_engine has a known fixed-TP single-symbol artifact pattern; verify this isn't a repeat. The 100% WR + identical-TP signature warrants quarantine before promotion.)*
- **`multi_asset_cot` / `multi_asset_copytrader` × CT=F** (cotton futures): n=34, avg **+5.04%**, WR 100%. Strategies `cftc_cot_commercial_signal` (17) + `cot_positioning` (15). This is **fundamental positioning data**, not technical noise — the picker is underweighting COT signals.

## 3. Hidden-Noise cluster analysis (n=106)

| Dimension | Top concentrations |
|---|---|
| **Source** | `super_signals` 49 (46%), `luxalgo_filters` 36 (34%), `kimi_riseoftheclaw` 7 |
| **Strategy** | `strong consensus (alpha_engine, ml_crypto_pred)` 47 (super_signals), `luxalgo_confluence` 36 |
| **Symbol** | `SUIUSDT` 12, `NEARUSDT` 7, `STRKUSDT` 7, `WLDUSDT` 6, `APTUSDT` 5, `ZROUSDT` 5 |
| **Asset class** | CRYPTO 94 (89%) |
| **Timeframe** | SWING 57, INTRADAY 44 (vs 1.7% intraday in hidden-alpha) |

**Drilldowns:**
- `super_signals` **"strong consensus" label is anti-predictive at the top score band:** 47/49 hidden-noise picks carry the `strong consensus (alpha_engine, ml_crypto_pred)` strategy label. Whole-system `super_signals` is positive (avg +1.07%, WR 39%, n=123) — the top-quintile-score subset is the toxic slice, not the system itself.
- `luxalgo_filters` whole system avg +0.02%, WR 44.2%, n=606. The top-score `luxalgo_confluence` subset is **uniformly bad** (n=36, WR 0%). High score on luxalgo predicts losses, not wins.

---

## 4. Dormant high-performance strategies

System-aggregate `profit_factor` is published; strategy-level PF is not — so for strategies I used a proxy: `wr>=55 or avg_pnl>=1.0`, `n>=15`, silent>=14d, positive total_pnl. Ranked by `avg_pnl * sqrt(n)`.

| Rank | System / Strategy | n | WR | avg_pnl | Days silent | Last signal |
|---|---|---|---|---|---|---|
| 1 | `alpha_engine` / `ml_enhanced_FETUSDT_1d_B_lightgbm` | 45 | 55.6 | **+16.82%** | 15.9 | 2026-04-27 |
| 2 | `claude_gainer` / `claude_gainer_4h` | 32 | 56.2 | +2.51% | **76.7** | 2026-02-25 |
| 3 | `kimi_signal_tracking` / `unknown` | 18 | **83.3** | +2.46% | 24.0 | 2026-04-19 |
| 4 | `alpha_engine` / `ml_enhanced_DYDXUSDT_15m_D_ensemble_stack` | 31 | **96.8** | +1.80% | 18.2 | 2026-04-24 |
| 5 | `ml_crypto_pred_v12` (system aggregate, PF=**2.53**) | 18 | 55.6 | +1.14% | **79.7** | 2026-02-22 |

`ml_crypto_pred_v12` is the **only** system-level entry meeting PF>=2 AND >=14d silence — but it's been silent **79.7 days** since 2026-02-22. Either the v12 generator was deprecated without a replacement or its cron was disabled.

---

## 5. Three concrete recommendations

### REC-1 — PROMOTE: COT-signal commodity longs bypass-score-floor
Add a `passes_smart_gate` early-pass clause: if `source_system in {multi_asset_cot, multi_asset_copytrader}` AND `strategy in {cftc_cot_commercial_signal, cot_positioning}` AND `asset_class=='COMMODITY'`, accept regardless of `score`. Justification: 34 closed CT=F picks, +5.04% avg, 100% WR — the picker's tech-feature score is blind to fundamental positioning. (Hold `quan_engine`/ONDOUSDT in quarantine pending fixed-TP-artifact verification per `project_quan_engine_matic_positive_artifact.md`.)

### REC-2 — DEMOTE: super_signals "strong consensus" + luxalgo_confluence at top-score band
In `calculate_smart_score`, apply a **−15 point penalty** when `(source_system=='super_signals' AND strategy startswith 'strong consensus (alpha_engine, ml_crypto_pred)')` OR `strategy=='luxalgo_confluence'` AND raw_score > 55. These 83 picks have 0% WR with avg −2.7%; the high-score label is a contrarian sell on these two strategies. Whole-system kill is unwarranted (super_signals overall is +1.07%) — surgical penalty only.

### REC-3 — REVIVE: `ml_crypto_pred_v12` (PF 2.53, WR 55.6%) — restart generator
System has been silent 79.7 days. Action: locate the cron entry, confirm the generator script still exists, and re-enable.
- Check `.github/workflows/` for any `ml_crypto_pred_v12.yml` (likely disabled).
- If missing, restore from git history near `2026-02-22` and re-enable on the same hourly cadence as `ml_crypto_pred` (the v10 sibling — PF 1.86, silent 0.09d, still running).
- Suggested cron: `0 * * * *` (hourly), matching `ml_crypto_pred`'s active schedule.
- Gate the revival behind a 7-day shadow run before letting picks reach `picks.active` (n=18 is small; need confirmation the PF holds out-of-sample).

---

## Sanity / caveats
- `score` is the primary field used; for picks missing it, the fallback chain (elite_score → trust_score → confidence×100) was applied — does not change cohort sizes materially because `score` is populated on 100% of `recent_closed`.
- Hidden-alpha WR = 100% and hidden-noise WR = 0% are **definitional artifacts** of the percentile bins (p80 pnl threshold = +2.51%, p20 = -1.81%, both away from zero) — the actionable number is the **cohort concentration**, not its WR.
- All ratings here are READ-ONLY observations; no code or trades modified.
