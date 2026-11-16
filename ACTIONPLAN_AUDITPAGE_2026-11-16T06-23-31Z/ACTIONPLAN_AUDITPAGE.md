# ACTIONPLAN_AUDITPAGE — 2026-11-16T06:23:31Z

Worktrees consolidated: `auditpage`, `auditpage-v2`, `auditpage-v3`, `auditpage-v4`.
All four were at the same commit (`db4cc06ed82`) with clean status at audit start.
Audit method: four parallel subagents over (1) PnL integrity/data quality, (2) asset-class performance, (3) prediction markets + WIRED_IN, (4) GitHub Actions; plus peer plan `ACTIONPLAN_AUDITPAGE/2026-11-16T0625Z_kilo_auditpage/00_KILO_AUDIT_ACTIONPLAN_2026-11-16.md` (kilo/auditpage, 2026-11-16T06:25Z), merged below.

---

## 0. TL;DR

| Area | Verdict |
|---|---|
| Money-ready classes | **0 / 9** — nothing passes n≥100, WR≥50%, PF≥1.5 |
| Honest intrabar WR/PF | CRYPTO 35.8%/0.92 · FOREX 32.2%/0.66 · EQUITY 59.2%/0.94 · COMMODITY 40.2%/1.03 · FUTURES 42.3%/1.09 · ETF 2.2%/0.02 · BOND 7.7%/0.39 · MEME 29.4%/0.66 |
| Best real lead | `crypto_rsi5070_us` shadow: net PF 1.11, CI-LB 0.92 (bar 1.15) — below promotion bar |
| Ghost rows | **Real: 22,947** in 10 MEMECOIN cohorts; page prose claiming "0" is **stale/wrong** |
| Profitable after costs | **None** at money-ready bar. COMMODITY PF 1.03 and FUTURES PF 1.09 are positive but thin/not policy-clean |
| WIRED_IN | Only `childlike-airport` is actually wired; paper-only, static snapshot |
| Prediction markets | Plumbing broken: 3 registered data files missing; dual-write path mismatch; 4 redundant workflows; kill-list contradiction |
| GH Actions | 6 failing runs with no later success; `.disabled` files and `|| echo` masking remain |

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
1. **HIGH** — 22,947 ghost rows remain and are aggregated into per-class/per-strategy PF. 100% are MEMECOIN `meta_strategy` constant-`pnl_pct` cohorts. Producer `tools/db_health_check.py:172-240`; renderer `audit_dashboard/dashboard_enhancements.js:750-755` shows the real number while the TRUTH LAYER prose hard-codes "0".
2. **HIGH** — `strategy_perf_by_class.json` contains impossible PF values caused by those ghosts: `GainerPredictor1hStrategy` n=49 WR 97.96% PF 120.0; `ADX Trend Confirmation` n=213 WR 97.18% PF 60.375; `CorrKamaAdaptiveStrategy` n=142 WR 95.77% PF 39.67; `mega_mut_macd_rsi_m084` n=124 WR 90.32% PF 10.32. WR ≥90% at n>100 is not credible.
3. **MED** — Zero-PnL / FLAT rows are intentional (`audit_trail/universal_pick_resolver.py:301-313, 1148-1159`) but silently dilute WR; no per-class `resolution_method` breakdown is published.
4. **MED** — Round-number closed PnL (BTCUSDT/ETHUSDT/SOLUSDT/NEARUSDT exactly -2.00%, JUPUSDT +3.50%) is SL/TP template output; needs a hygiene check for synthetic/prefill rows.
5. **MED** — 29-row `MeanReversionBB` batch (source `signal_validation`) at 0% WR in `cohort_reconciliation.json`; batch dedup missing.
6. **MED** — Walk-forward Sharpe mis-scaled: BOND -65.632, FOREX +10.7 on n=3; `n<30`/zero-std not clamped. WF cohort (FOREX n=3, BOND n=31) differs from headline cohort (FOREX n=612, BOND n=1) with no label.
7. **LOW** — `strategy_ic_analysis.json` missing; page shows "Failed to load IC analysis data".
8. **LOW** — `at_raw_picks` UNKNOWN count not surfaced in `db_health.json`.

## 2. Asset-class performance (verified)

Source: `audit_dashboard/data/audit_surface_truth.json` (generated 2026-11-15T04:52:54Z), `intrabar_truth_by_class.json`, `strategy_perf_by_class.json`.

| Class | n_resolved | WR% | PF | policy_clean_n | policy_clean_WR% | policy_clean_PF | Avg PnL/trade | Verdict |
|---|---|---|---|---|---|---|---|---|
| CRYPTO | 3705 | 35.9 | 0.9196 | 22101 | 41.82 | 0.2572 | -0.107% | NOT_READY |
| FOREX | 612 | 32.2 | 0.6596 | 432 | 35.88 | 0.8385 | -0.105% | NOT_READY |
| EQUITY | 250 | 59.2 | 0.9392 | 472 | 38.98 | 0.6333 | -0.074% | NOT_READY |
| COMMODITY | 229 | 40.2 | 1.0256 | 14 | 14.29 | 0.1718 | +0.027% | WATCH |
| FUTURES | 52 | 42.3 | 1.0936 | 13 | 30.77 | 1.0093 | +0.079% | INSUFFICIENT_DATA |
| ETF | 45 | 2.2 | 0.0216 | 19 | 68.42 | 1.7877 | -2.33% | BROKEN |
| MEME | 102 | 29.4 | 0.661 | — | — | — | -0.343% | FAIL |
| BOND | 26 | 7.7 | 0.391 | 1 | — | 0.0 | -0.334% | INSUFFICIENT_DATA |
| PENNY_STOCK | 4 | 50.0 | 0.1779 | 4 | 50.0 | 0.1779 | — | INSUFFICIENT_DATA |

- `money_ready_classes = []`, `money_ready_count = 0`. **"0/6" is understated: it is 0/9.**
- **FALSIFIED / STALE headline claims** on the page: CRYPTO "32.9% PF 0.74", EQUITY "60% PF 2.13 n=72", COMMODITY "PF 1.77". Actual policy-clean: CRYPTO PF 0.92 (n=3705), EQUITY PF 0.94 (n=250), COMMODITY PF 1.03 (n=229). The page mixes intrabar-truth and policy-clean surfaces without labelling.
- **EQUITY 59.2% WR with PF 0.94** shows WR is not edge (avg loss > avg win). **ETF PF 0.022 / -2.33% per trade** is a broken emitter, not a strategy.
- **COMMODITY is the only class with positive avg PnL (+0.027%)**; `futures_momentum` (n57, 63%, PF 2.6) is the best sub-sleeve but n<100 and not policy-clean (policy_clean_n=14, PF 0.17). Forward-track candidate only.
- **FOREX win/loss asymmetry**: wins ~0.62%, losses ~1.00%, WR 57.8%, PF 0.85 — tight-TP/wide-SL geometry. Symmetric ATR stops will stay net-negative at 60% WR.
- **All time buckets negative** (24h -5.69%, 7d -462%, 30d -957%, all-time Σ -1,335%). Aggregate compound -94.29% vs Σ per-trade +310.94% means position sizing on the compounding path is destroying a positive-expectancy trade stream — a portfolio-construction bug worth a separate investigation.
- **Arithmetic inconsistency:** `audit_surface_truth.json` CRYPTO row is used both for "headline PF 1.25" and intrabar PF 0.92; `strategy_perf_by_class.json` PF >10 values are ghost-driven.

## 3. WIRED_IN

- `WIRED_IN/` contains ~26 timestamped folders; only **one** ships a wired artifact: `2026-11-15T0150Z_childlike-airport` → `audit_dashboard/data/wired_in_childlike_active_picks.json`, 3 picks (XLV/LLY/SHY), `paper_only: true`, `sizing_allowed: false`, `trust_tier: UNPROVEN`.
- Registration is correct: `audit_trail/dashboard_generator.py:4289-4291` (`JSON_PICK_SOURCES`), `audit_trail/universal_pick_resolver.py:265` (`SYSTEM_SOURCES`), excluded from forward-tested wins at `dashboard_generator.py:4307`.
- Gap: the file is a frozen 2026-11-15T01:50Z snapshot; no cron regenerates it. Either add a re-scan job or label it "static snapshot — not live".
- Other folders are specs/prompts following the README 4-question convention; `WIRED_IN/2026-11-15_0700_scratch-hippodraco/STRATEGY_SHORTLIST.md` still cites PBO 0.603 and "zero resolved forward trades" while claiming 85–100% WR.
- Orphans: `WIRED_IN/final_v001/.../paper_scan.py`, `WIRED_IN/2026-11-15_0708/.../run.py` are not referenced by any workflow. Archive or wire.

## 4. Prediction markets (Polymarket / Kalshi)

- `pm_kalshi_signals` showing SOLUSDT/ETHUSDT/BTCUSDT is **by design**: `alpha_engine/kalshi_signals.py:41-59` maps Kalshi crypto series (KXBTCD→BTCUSDT etc.) onto spot symbols; `dashboard_generator.py:5467` synthesizes spot entry/TP/SL. Comment this at `kalshi_signals.py:37` so it stops being reported as a bug.
- PM data **is wired**: `prediction_market_picks.json` has 2 picks with `source_system=prediction_market_consensus`; `copytrade_pm_consensus.json` has 1 PM-linked pick. Total 3 PM-linked picks.
- **Contradiction with recorded decision** `prediction_market_copy_trading_rejected`: PBO 0.603 fails the shadow gate and any promotion bar; live PM copy paths still exist.
- Real gaps:
  1. **Missing files.** `dashboard_generator.py:4090-4094` and `universal_pick_resolver.py:216-218, 322-325` register `prediction_market_agents/data/{kalshi,momentum,whale}_signals.json`; these files do not exist. Produce them in CI or drop the registration.
  2. **Path split.** `alpha_engine/kalshi_signals.py:31` writes `alpha_engine/data/kalshi_signals.json` while the resolver reads `prediction_market_agents/data/kalshi_signals.json`. Reconcile.
  3. **Redundant workflows.** `alpha-engine-live.yml`, `prediction-market-agents.yml`, `polymarket-signals.yml`, `audit-dashboard.yml` all run overlapping PM scripts; failures are masked by `|| echo ... non-fatal` (e.g. `alpha-engine-live.yml:159-170`).
  4. **Kill-list contradiction.** `alpha_engine/config.py:294` puts `prediction_market_consensus` on the kill list, yet it is invoked by 3 workflows and tagged as verified-alpha PM source in `dashboard_generator.py:5531`.
  5. **No hard shadow pin.** Memory says "prediction markets stay shadow (PBO 0.603)" but no code constant enforces it. Add `PREDICTION_MARKETS_SHADOW_ONLY = True` at the sizing decision in `admissibility_pipeline.py:~720` and a test.

## 5. GitHub Actions

- 355–373 workflow files; 4 auditpage worktrees all at same commit.
- Failing runs with **no later success** observed at audit time: `Deploy Rise of the Claw Dashboard` (43812995439), `Deploy Rise of the Claw` (43812993445), `actions-failure-guardian` (438129705), `DARWIN ENGINE - DNA Evolution Pipeline` (43812864701), `Claude's Test - Portfolio Manager` (43812822128), `Portfolio Trackers (Real Money + Theory)` (43812803756).
- Repo already carries GHA audit deliverables on main (`GHACTIONS_2026-11-16/ACTION_PLAN.md`, `reports/gha_queue_and_failures_2026-11-16.md`, `reports/gha_run_matrix_2026-11-16.json`). Treat those as canonical; do not mass-delete.
- Known correction to respect: the "235 stale workflows" figure is a sampling artifact; trigger-aware history puts real stale/never-run at ~20 + 12.
- Hygiene: `.disabled` workflow files remain in `.github/workflows/`; `|| echo ... non-fatal` masks real failures.

---

## 6. Final suggestions (priority order)

**P0 — truth and credibility (small diffs, do first)**
1. Fix the stale "Ghost rows: 0" prose — make it read `db_health.json.ghost_rows.total_ghost_rows` and gate the banner on `== 0`; add `ghost_rows_verified_at`.
2. Kill the `signal_validation` card from "TIER-2 PROVEN" (MDD 123.4%, n=102, 90d cum -118.4%).
3. Clamp walk-forward Sharpe rendering when `n < 30` or `std < 1e-6`; label which ledger each panel reads (headline vs WF vs policy-clean).
4. Add a plain-language banner: "0/9 asset classes money-ready; this is a research ledger, not a money book."

**P1 — data integrity**
5. Clean the 10 MEMECOIN ghost cohorts (`tools/cleanup_ghost_rows.py`, dry-run first); re-run `db_health_check.py`; re-generate dashboard. Add ghost-row filter to `strategy_perf_by_class` aggregation before PF/WR; delete impossible PF values; add `n_eff`/`distinct_entries`.
6. Reconcile the three performance surfaces (intrabar-truth, policy-clean net, forward-track) into one labelled table; remove CRYPTO PF 1.25 / EQUITY PF 2.13 / COMMODITY PF 1.77 headline claims or mark window+filter.
7. Emit `zero_pnl_breakdown` (resolution_method per class) and a `round_number_pnl` hygiene count into `dashboard_data.json`; extend zero-pnl artifact filter to all terminal statuses.
8. Batch dedup for `signal_validation`/`MeanReversionBB`-style re-emissions; surface `at_raw_picks` UNKNOWN count.
9. Forward-validator freshness gate: enforce `last_terminal_write < 26h` in `tools/db_freshness_check.py`; wire into `real_money.html` Lopez gate; stop showing "1h / 02:26" unless the artifact supports it.
10. `money_ready_verdict.json`: recompute on policy-clean closed picks with ghosts removed; publish per-gate pass/fail (DSR, PBO, WFE, live-Sharpe, n, WR, PF) so "0/9" is auditable.

**P2 — pipeline correctness**
11. Reconcile Kalshi/PM data paths; generate the 3 missing PM files in CI or drop their registration.
12. Consolidate the 4 PM workflows into one; replace `|| echo ... non-fatal` masking with real failure signals.
13. Resolve `prediction_market_consensus` kill-list vs verified-alpha contradiction; enforce `PREDICTION_MARKETS_SHADOW_ONLY` sizing pin + test.
14. Either enforce `prediction_market_copy_trading_rejected` in code and delete live PM copy paths, or rescind the decision with a new evidence pack.

**P3 — profitability investigation**
15. Investigate compound-vs-sum divergence (-94.29% compound vs +310.94% Σ per-trade): is sizing per-trade destroying a positive-expectancy stream? Only path to a real edge in current data.
16. Formalise forward tracking for COMMODITY `futures_momentum` (n57, 63%, PF 2.6) and FOREX `forex_rsi2` (n19, 63%, PF 2.4); track only, no sizing until n≥100 and policy-clean PF≥1.5.
17. Continue `crypto_rsi5070_us` shadow tracking to the n≥150 gate (~2026-12).

**P4 — hygiene**
18. Fix the 6 failing-no-success workflows (start with `actions-failure-guardian` — it is the meta-guardian and its failure blinds the rest).
19. Apply the existing `GHACTIONS_2026-11-16/ACTION_PLAN.md`; archive `.disabled` workflows; scan `.github/workflows/*.yml` for missing `python <script>` targets.
20. Generate `strategy_ic_analysis.json` or remove the dead panel; tidy orphaned WIRED_IN scripts; make the childlike-airport snapshot live or label it static.

## 7. Suggested owner split (for the final plan agent)
- Data quality / PnL / dashboards: owner A (ghost rows, PF recompute, truth-layer prose, WF clamp).
- Money-ready / forward validator / pipeline: owner B.
- Prediction markets / WIRED_IN contradiction: owner C.
- GHA: owner D (consume existing GHA action plan).

## 8. Verification hooks
- `python3 tools/db_health_check.py` → `ghost_rows.total_ghost_rows == 0`.
- `audit_dashboard/data/audit_surface_truth.json` regenerated; `money_ready_count` unchanged but per-gate table present.
- `strategy_perf_by_class.json`: no PF > 10 with n > 30 and WR > 80%.
- `gh run list` for the 6 named workflows shows a success after the fix commit.
- No `|| echo ... non-fatal` on PM-critical steps; PM data path single-sourced.

## 9. Evidence index
- `audit_dashboard/data/db_health.json` — ghost_rows 22,947; pnl_integrity 130/24,158; won_pnl_contradiction false
- `audit_dashboard/data/intrabar_truth_by_class.json` — per-class honest n/WR/PF
- `audit_dashboard/data/money_ready_verdict.json` — full gate dump
- `audit_dashboard/data/audit_surface_truth.json` — policy_clean vs n_resolved per class
- `audit_dashboard/data/strategy_perf_by_class.json` — suspect PF values
- `tools/db_health_check.py:120-169, 172-240`
- `audit_trail/universal_pick_resolver.py:216-218, 265, 301-313, 322-325, 1148-1159`
- `audit_trail/dashboard_generator.py:4090-4094, 4289-4291, 4307, 5467, 5527-5532`
- `audit_dashboard/dashboard_enhancements.js:750-755`
- `alpha_engine/kalshi_signals.py:31, 37, 41-59`
- `alpha_engine/config.py:294`
- `audit_dashboard/data/wired_in_childlike_active_picks.json`
