# ACTIONPLAN_AUDITPAGE — 2026-11-16T06:23:31Z

Worktrees consolidated: `auditpage`, `auditpage-v2`, `auditpage-v3`, `auditpage-v4`.
All four were at the same commit (`db4cc06ed82`) with clean status; no peer plan files existed yet at audit time.
Audit method: four parallel subagents over (1) PnL integrity/data quality, (2) asset-class performance, (3) prediction markets + WIRED_IN, (4) GitHub Actions.

---

## 1. PnL integrity & data quality

| Dashboard claim | Verdict | Evidence |
|---|---|---|
| PnL Integrity 99.5%, 130/24,158 mismatch >1pp | **CONFIRMED** | `audit_dashboard/data/db_health.json` pnl_integrity: sampled 24,158, gt1pct_mismatch 130, mismatch_pct 0.54 |
| Ghost Rows 22,947 / 10 cohorts | **CONFIRMED and STILL PRESENT** | `db_health.json.ghost_rows.total_ghost_rows = 22947`, 10 cohorts, all MEMECOIN `meta_strategy` (DOGEUSDT LONG 3,569 @1.3226%, DOGEUSDT LONG 3,160 @5.0%, WIFUSDT SHORT 2,763 @-3.0%, PEPEUSDT LONG 2,052, FLOKIUSDT LONG 2,043) |
| Page banner "Ghost rows: 0 (was 22,947)" | **FALSIFIED** | Same `db_health.json` still reports 22,947; no deletion evidence |
| WON-vs-PnL contradiction: no | **CONFIRMED** | `db_health.json.won_pnl_contradiction.contradiction_detected = false`; TP_HIT avg +3.41%, SL_HIT avg -3.20% |
| Status-PnL mismatches: 0 / non-canonical statuses: 0 | **CONFIRMED** (status layer) | `status_standardization.n_non_canonical = 0` |
| Forward Validator Freshness 1h, last WON/LOST 2026-11-16 02:26:30 | **UNVERIFIABLE / STALE** | `db_freshness.json` last write 2026-05-23; no artifact supports the 02:26 timestamp |
| at_raw_picks UNKNOWN: 3 | **UNVERIFIED** | Needs live-DB count; not in repo artifacts |

**Defects (severity):**
1. **HIGH** — 22,947 ghost rows remain and are aggregated into per-class/per-strategy PF. They are 100% MEMECOIN `meta_strategy` constant-`pnl_pct` cohorts.
2. **HIGH** — `strategy_perf_by_class.json` contains impossible PF values caused by those ghosts: `GainerPredictor1hStrategy` n=49 WR 97.96% PF 120.0; `ADX Trend Confirmation` n=213 WR 97.18% PF 60.375; `CorrKamaAdaptiveStrategy` n=142 WR 95.77% PF 39.67; `mega_mut_macd_rsi_m084` n=124 WR 90.32% PF 10.32. WR ≥90% at n>100 is not credible; these are re-emission/ghost artifacts.
3. **MEDIUM** — 29-row `MeanReversionBB` batch (source `signal_validation`) at 0% WR in `cohort_reconciliation.json`; batch dedup missing.
4. **MEDIUM** — PnL=0% rows: `dashboard_generator.py` zero-pnl artifact filter only covers part of the terminal statuses.
5. **LOW** — `at_raw_picks` UNKNOWN count not surfaced in `db_health.json`.

## 2. Asset-class performance (verified)

Source: `audit_dashboard/data/audit_surface_truth.json` (generated 2026-11-15T04:52:54Z), `strategy_perf_by_class.json`.

| Class | n_resolved | WR% | PF | policy_clean_n | policy_clean_WR% | policy_clean_PF | Verdict |
|---|---|---|---|---|---|---|---|
| CRYPTO | 3705 | 35.9 | 0.9196 | 22101 | 41.82 | 0.2572 | NOT_READY |
| FOREX | 612 | 32.2 | 0.6596 | 432 | 35.88 | 0.8385 | NOT_READY |
| EQUITY | 250 | 59.2 | 0.9392 | 472 | 38.98 | 0.6333 | NOT_READY |
| COMMODITY | 229 | 40.2 | 1.0256 | 14 | 14.29 | 0.1718 | WATCH |
| FUTURES | 52 | 42.3 | 1.0936 | 13 | 30.77 | 1.0093 | INSUFFICIENT_DATA |
| ETF | 45 | 2.2 | 0.0216 | 19 | 68.42 | 1.7877 | INSUFFICIENT_DATA |
| MEME | 10 | 10.0 | 0.0234 | 10 | 10.0 | 0.0234 | INSUFFICIENT_DATA |
| PENNY_STOCK | 4 | 50.0 | 0.1779 | 4 | 50.0 | 0.1779 | INSUFFICIENT_DATA |
| BOND | 1 | 0.0 | 0.0 | 1 | — | 0.0 | INSUFFICIENT_DATA |

- `money_ready_classes = []`, `money_ready_count = 0`. **"0/6 money-ready" is directionally right but understated: it is 0/9.**
- **FALSIFIED / STALE headline claims** on the page: CRYPTO "32.9% PF 0.74", EQUITY "60% PF 2.13 n=72", COMMODITY "PF 1.77". Actual policy-clean: CRYPTO PF 0.92 (n=3705), EQUITY PF 0.94 (n=250), COMMODITY PF 1.03 (n=229). The intrabar-truth and policy-clean surfaces disagree by design; the page mixes them without labelling.
- **Genuinely profitable (PF>1, positive net, n≥100, after excluding ghost rows):** only **COMMODITY** (PF 1.03, n=229) is positive but fails WR≥50% and PF≥1.5. **FUTURES** PF 1.09 but n=52. No class meets the money-ready bar.
- **Forward sleeves** (`forward_track`) are all `promotion_ready=false`; best is `bootstrap_inverse_ml_ada_15m` n=38 WR 57.9% PF 2.38 — still below promotion bar and n<100.
- **Arithmetic inconsistency:** `audit_surface_truth.json` CRYPTO row is used both for "headline PF 1.25" and intrabar PF 0.92; `strategy_perf_by_class.json` PF values >10 are ghost-driven.

## 3. Prediction markets / WIRED_IN

- PM data **is wired**: `prediction_market_picks.json` has 2 picks with `source_system=prediction_market_consensus` (BNBUSDT_S, BTCUSDT_L); `copytrade_pm_consensus.json` has 1 PM-linked pick. Total 3 PM-linked picks.
- `WIRED_IN/` submissions (2026-11-15_*) follow the README 4-question convention and ship artifacts (JSON/CSV/scripts).
- **Contradiction with recorded decision** `prediction_market_copy_trading_rejected`: `WIRED_IN/2026-11-15_0700_scratch-hippodraco/STRATEGY_SHORTLIST.md` still cites PBO 0.603 (60.3% overfitting) and "zero resolved forward trades" while claiming 85–100% WR. PBO 0.603 also fails the recorded shadow gate (PBO 0.603) and any promotion bar.
- Work items: (a) enforce the rejection in code/docs or formally rescind it; (b) remove PBO 0.603 claims from promotion surfaces; (c) add timestamp validation to `WIRED_IN/.../ELIMINATION_LOG.md`; (d) add reproducible artifact for `finpredict-v4` subQ usage.

## 4. GitHub Actions

- 355 workflow files; 4 worktrees all at same commit.
- Failing runs with **no later success** observed at audit time: `Deploy Rise of the Claw Dashboard` (43812995439), `Deploy Rise of the Claw` (43812993445), `actions-failure-guardian` (438129705), `DARWIN ENGINE - DNA Evolution Pipeline` (43812864701), `Claude's Test - Portfolio Manager` (43812822128), `Portfolio Trackers (Real Money + Theory)` (43812803756).
- Repo already carries GHA audit deliverables on main (`GHACTIONS_2026-11-16/ACTION_PLAN.md`, `reports/gha_queue_and_failures_2026-11-16.md`, `reports/gha_run_matrix_2026-11-16.json`). Treat those as the canonical GHA source; do not mass-delete.
- Known correction to respect: the "235 stale workflows" figure is a sampling artifact; trigger-aware history puts real stale/never-run at ~20 + 12.

---

## Final suggestions (priority order)

**P0 — stop the numbers from lying**
1. Re-run `tools/cleanup_ghost_rows.py` against live `bt_backtest_trades`; commit the deletion; make `db_health.json.ghost_rows.total_ghost_rows` the single source and gate the dashboard banner on `total_ghost_rows == 0` (add `ghost_rows_verified_at`).
2. Add ghost-row filter to `strategy_perf_by_class` aggregation before PF/WR; recompute and delete impossible PF values (>10 at n>30 is a red flag). Add an `n_eff`/`distinct_entries` column.
3. Reconcile the three surfaces (intrabar-truth, policy-clean net, forward-track) into one labelled table; remove CRYPTO PF 1.25 / EQUITY PF 2.13 / COMMODITY PF 1.77 headline claims or mark them with their window and filter.

**P1 — make money-ready verdicts reproducible**
4. `money_ready_verdict.json`: recompute on policy-clean closed picks with ghost rows removed; publish the per-gate pass/fail table (DSR, PBO, WFE, live-Sharpe, n, WR, PF) so "0/9" is auditable.
5. Forward-validator freshness gate: enforce `last_terminal_write < 26h` in `tools/db_freshness_check.py`; wire into `real_money.html` Lopez gate; stop showing "1h / 02:26" unless the artifact supports it.

**P2 — data hygiene**
6. Extend zero-pnl artifact filter to all terminal statuses in `dashboard_generator.py`; backfill via `tools/repair_data_integrity.py`.
7. Batch dedup for `signal_validation`/`MeanReversionBB`-style re-emissions in `cohort_reconciliation.json`.
8. Surface `at_raw_picks` UNKNOWN count in `db_health.json` and the dashboard.

**P3 — prediction markets**
9. Resolve the copy-trading contradiction: either enforce `prediction_market_copy_trading_rejected` in code and delete live PM copy paths, or rescind the decision with a new evidence pack. Do not leave both.
10. Add PBO 0.603 to the promotion gate blocklist; strip "85–100% WR" claims that have zero resolved forward trades.

**P4 — GitHub Actions**
11. Fix the 6 failing-no-success workflows above (start with `actions-failure-guardian` — it is the meta-guardian and its failure blinds the rest).
12. Apply the existing `GHACTIONS_2026-11-16/ACTION_PLAN.md`; do not duplicate or mass-delete workflows.
13. Scan `.github/workflows/*.yml` for `python <script>` targets that do not exist; disable or fix.

## Suggested owner split (for the final plan agent)
- Data quality / PnL: owner A (ghost rows + PF recompute).
- Money-ready / forward validator: owner B.
- Prediction markets / WIRED_IN contradiction: owner C.
- GHA: owner D (consume existing GHA action plan).

## Verification hooks
- `python3 tools/db_health_check.py` → `ghost_rows.total_ghost_rows == 0`.
- `audit_dashboard/data/audit_surface_truth.json` regenerated; `money_ready_count` unchanged but per-gate table present.
- `strategy_perf_by_class.json`: no PF > 10 with n > 30 and WR > 80%.
- `gh run list` for the 6 named workflows shows a success after the fix commit.
