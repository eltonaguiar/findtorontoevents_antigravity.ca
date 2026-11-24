# Peer review — auditpage plans — 2026-11-16T06:30Z

Reviewer: `.kilo/worktrees/auditpage-v4`. Read-only. No code changes.

Plans on `origin/main`:

| Plan | Commit | Role |
|---|---|---|
| `ACTIONPLAN_AUDITPAGE/2026-11-16T0625Z_kilo_auditpage/00_KILO_AUDIT_ACTIONPLAN_2026-11-16.md` | `3ff92974407` | kilo/auditpage. Cleanest single-author plan. |
| `ACTIONPLAN_AUDITPAGE_2026-11-16T06-23-31Z/ACTIONPLAN_AUDITPAGE.md` | `7d45e7f5be1` | Merge of that plan plus an earlier 06:23 draft. |
| `ACTIONPLAN_AUDITPAGE/2026-11-16T0626Z_auditpage-v4/ACTIONPLAN.md` | `9f93695f022` | v4 corrections. This review. |

`auditpage-v2` and `auditpage-v3` have no unique commits and no plan files. The 06:23 header that says all four worktrees were consolidated overclaims. Only auditpage, the 06:23 consolidator, and v4 wrote anything.

---

## Keep (agreed, and checked)

- **0/9 money-ready.** Do not size. `money_ready_count=0`.
- **Ghost rows are 22,947**, all MEMECOIN `meta_strategy` constant-`pnl_pct` cohorts. Page prose is false: `audit_dashboard/template.html:857` and `index.html:857` still say "Ghost rows: 0 (was 22,947)".
- **WON-vs-PnL sign contradiction: none.** Non-canonical statuses: 0.
- **WIRED_IN:** only `childlike-airport` is registered. Paper-only, sizing 0, frozen snapshot. Other folders are specs. `scratch-hippodraco` 85–100% WR vs PBO 0.603 must not be promoted.
- **Kalshi spot symbols** (BTC/ETH/SOL) are a series→spot map, not a second crypto book. Still a display bug if PF renders `∞` at 0 closed trades.
- **`strategy_ic_analysis.json` is missing.** Remove the panel or generate the file.
- **Do not mass-delete workflows.** GHA work stays in `GHACTIONS_2026-11-16/`. The "235 stale" figure stays rejected.

## Reject or downgrade before the final plan

1. **Reject P4 item 18 and TL;DR line 20 of the 06:23 plan** ("6 failing runs, start with `actions-failure-guardian`"). Rechecked 2026-11-16T06:32Z with `gh run view`. Every resolvable id **succeeded**. None of these is a broken workflow.
   - `43812995439` Deploy Rise of the Claw Dashboard — success 05:52:02Z (latest).
   - `43812993445` Deploy Rise of the Claw — success 05:52:01Z; later successes `43814271618` (06:04Z) and `43816313118` (06:22Z).
   - `438129705` — **404**. Not a run id. Latest `actions-failure-guardian` on main is success `43812910225` at 05:51:13Z (last 8 all success).
   - `43812864701` DARWIN ENGINE — success 05:50:47Z (latest).
   - `43812822128` Claude's Test - Portfolio Manager — success 05:50:24Z (latest).
   - `43812803756` Portfolio Trackers — success 05:50:15Z (latest).
   - `forward-validator.yml` does not exist. Do not open fix PRs from that table.

2. **Do not treat "PnL integrity 99.5%" as confirmed data quality.** The 06:23 table marks it CONFIRMED. The metric is sign consistency: 130/24,158. Naive magnitude mismatch in the same object is **6,535 / 24,158 (27.05%)**. The final plan must print both.

3. **The ghost-row check currently passes.** `ok=true`, `threshold_pass=true`, `tier=yellow`, `banner_should_show=false`, `generated_at` 2026-11-16T01:29:16Z. Fixing the prose at line 857 without failing the check leaves the health strip green. v4 P0.2 is the missing step. The 06:23 plan does not have it.

4. **Do not describe compound −94% vs Σ +311% as a proven "portfolio-construction bug destroying a positive-expectancy stream."** That sentence is in the 06:23 plan §2. It is a hypothesis. A positive sum of percents is not expectancy, and one panel's PF 1.15 does not license that wording. Investigate after the ghost-row cleanup, not before.

5. **Do not merge the class table as one cohort.** The 06:23 file's first draft had MEME n=10 / WR 10% / PF 0.02 from `audit_surface_truth.json`. The merge replaced it with MEME n=102 / WR 29.4% / PF 0.66 from intrabar truth, in the same row as policy-clean columns from a different ledger. ETF raw PF 0.02 vs policy-clean PF 1.79 (n=19) is the same trap. Final table needs a `source` column. Prefer v4: nothing is money-ready; do not pick the prettier number.

6. **"PM data is wired" is only half true.** `alpha_engine/data/prediction_market_picks.json` exists (2 picks, `prediction_market_consensus`). `audit_dashboard/data/prediction_market_picks.json` does not. `kalshi_signals.json` is absent at both `alpha_engine/data/` and `prediction_market_agents/data/`. Keep the path-split fix. Do not say the feed is live.

7. **Dashboard staleness is not the 60-minute string.** `template.html:17878` warns at `mins > 60`. Freshness panel goes red at 72h. Last **scheduled** Unified Audit Dashboard success was 2026-11-16T03:21:42Z (`43797722088`). No 04:10 or 05:10 schedule run in the last 8. Dispatches at 05:16 and 06:04 were cancelled; `43815224263` (06:12Z) was still in progress at 06:32Z. Concurrency group `dashboard-publish`, `cancel-in-progress: false`. The 06:23 plan never mentions this. Keep v4 §2.3–2.4. Do not re-add `push:`.

## Unsafe if executed as written

- `tools/cleanup_ghost_rows.py --execute` against live `bt_backtest_trades` needs a dry-run diff and an explicit go-ahead. The plan is right to say dry-run first. The finalizer must not skip that.
- "Consolidate the 4 PM workflows into one" undercounts. Eight workflow files mention polymarket/kalshi/prediction_market: `alpha-engine-live.yml` (8 `|| echo`), `audit-dashboard.yml` (5), `polymarket-signals.yml` (3), `sports-betting-refresh.yml` (1), plus `copy-trader-intelligence.yml`, `prediction-market-agents.yml`, `social-prediction-tracker.yml`, `sports-prediction-market-sync.yml`. Do not delete four files and call it done. `audit-dashboard.yml` must stay.
- Adding `PREDICTION_MARKETS_SHADOW_ONLY` is the right direction (recorded decision: stay shadow, copy-trading rejected). Do not rescind that decision in the same PR that "makes PM wired".

## What the finalizer should assemble

Use **kilo/auditpage (0625Z)** as the spine. Overlay **v4** for: sign-vs-magnitude, ghost check still green, stale-banner threshold, cron queue, PF `n/a` not `∞`, and this review's rejections. Use **06:23** only for the owner split and the evidence index. Drop its GHA failure table and the "positive-expectancy stream" sentence.

Order stays: prose + check thresholds, then ghost cleanup (dry-run), then PM path reconcile (shadow only), then publish-queue. No sizing.

## Claim check added 2026-11-16T06:33Z

Independent read of the files the 0625Z and 06:23 plans cite. Passes are omitted. These change the final plan:

8. **Do not forward-track `futures_momentum` n=57 / 63% / PF 2.6 or `forex_rsi2` n=19 / 63% / PF 2.4.** Those figures are not in current JSON. Nearest hit is prose in `reports/wsg_shadow_track_decision_2026-06-09.md` (PF 2.68 and 2.43). `strategy_perf_by_class.json` now says COMMODITY `futures_momentum` n=681 WR 37.3% PF 0.2488, and FOREX `forex_rsi2_mean_reversion` n=1091 WR 39.78% PF 0.3754. The June sleeve is stale. Drop P3 items that size a research queue off it.

9. **PF>10 rows are real, and worse than the peer examples.** `strategy_perf_by_class.json` uses `win_rate_pct` / `profit_factor`. Top CRYPTO cells are PF **999** (zero-loss sentinel), not a measured factor: HoffmanStripTrendStrategy n=146, Calendar Effect Crypto n=105, VolumeWeightedMedianZScoreStrategy n=50, BTCSPXCorrBreakdownStrategy n=44. GainerPredictor1hStrategy n=49 PF 120 is the one the 06:23 plan named. Cap or blank PF when losses are 0. Do not quote 999 as edge.

10. **Do not kill `signal_validation` for "PF 0.12 / MDD 123%".** Those literals are not on that name. PF 0.12 is hard-coded for COMMODITY COT at `audit_dashboard/template.html:13543`. `signal_validation` is on `_TIER2_PROMOTION_TARGETS` at `audit_trail/dashboard_generator.py:11708` and on a blocked-list string at `template.html:9503` ("10 trades, 0% WR, -18.4% PnL"). Card numbers are computed at `dashboard_generator.py:12037-12040`. Remove it from the promotion-target tuple. Separately delete the COT hard-coded PF.

11. **BOND Sharpe -65.632 is real, but not in `audit_dashboard/data/`.** It is `alpha_engine/data/walkforward_results.json` `by_class.BOND.oos_sharpe`. Clamp there. A nearby -65.6365 in `institutional_metrics.json` is a different series. Do not "fix" the wrong file.

12. **Kill-list line is exact.** `alpha_engine/config.py:294` `'prediction_market_consensus',  # WR 26%, -29% intrabar` inside `BLACKLISTED_STRATEGIES`. Shadow pin stays. Do not un-blacklist it to make the dashboard card look wired.
