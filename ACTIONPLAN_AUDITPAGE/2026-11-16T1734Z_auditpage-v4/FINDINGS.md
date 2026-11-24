# Audit quant review — auditpage-v4 — 2026-11-16T17:34Z

Repo: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca
Live page checked: https://findtorontoevents.ca/audit/ (fetched 2026-11-16T17:34Z, 1.4 MB).
Seat: `inbox/gx10-c9b9/auditpage-v4/grok-4-7`

## Live page vs main

PR 843 is on main (`9842be43e982`, merged 17:31Z) but not on the live page. The 15:25Z `audit-dashboard.yml` run started before that merge. Live HTML still contains `5/5 checks pass` and does not contain `ghost-row check fails` or `Prediction markets stay shadow`. It does already warn that ghost rows are not cleared (22,947) and that June PF 2.6 / 2.4 sleeves must not be forward-tracked.

Do not treat the live page as the post-843 text until the next successful dashboard deploy.

## Per-class performance

Source: `audit_dashboard/data/audit_surface_truth.json` generated 2026-11-16T04:58:21Z. Money-ready count is 0. `money_ready_verdict.json` (2026-11-16T13:04:35Z) watch list is COMMODITY only, `n_classes` 10.

| Class | n | PF | policy-clean n | policy-clean PF | Call |
|---|---:|---:|---:|---:|---|
| CRYPTO | 3716 | 0.92 | 22199 | 0.26 | not ready |
| FOREX | 612 | 0.66 | 427 | 0.83 | not ready |
| EQUITY | 250 | 0.94 | 472 | 0.63 | high WR is not edge |
| COMMODITY | 229 | 1.03 | 15 | 0.19 | watch only; policy-clean fails |
| FUTURES | 52 | 1.09 | 13 | 1.01 | n too small |
| ETF | 45 | 0.02 | 19 | 1.79 | do not quote the prettier PF; n=19 |
| MEME | 10 | 0.02 | 10 | 0.02 | insufficient |
| BOND | 1 | — | 1 | 0 | insufficient |
| PENNY / CHEAP | 4 / 1 | — | — | — | insufficient |

Nothing clears n≥100, WR≥50%, and PF≥1.5 together. No class should be sized.

## Best-practice gaps

- Ghost-row verdict on current main already fails a non-zero count (`tools/db_health_check.py` `ghost_row_verdict`, tests in `tests/test_ghost_row_verdict.py`). The published `db_health.json` and the live footer still describe the old pass until the checker reruns and the page redeploys. The workflow step is non-fatal (`|| echo`), so a red ghost tier does not stop deploy.
- Headline profit factor still rendered `∞` when losses were zero, and colored that as positive. That is not a profit factor. Fixed on this branch: show `n/a`.
- Walk-forward Sharpe of −65.632 is `alpha_engine/data/walkforward_results.json` `by_class.BOND.oos_sharpe`. The table only flagged a subset of small-fold cases. `|Sharpe| > 5` now displays `n/a`. A Sharpe above 5 on this sample is not a tradable result.
- ML calibration text on the live page is explicitly a static 2026-05-15 measurement (CRYPTO conf≥0.90 → 14.4% WR vs 0.50–0.60 → 60.3% WR). Do not size off raw confidence. Recalibrating the model is research, not a display patch.
- Prediction markets stay shadow. `alpha_engine/config.py` kill list still names `prediction_market_consensus`. Live copy still says Verified Alpha until #843 deploys.
- PF 999 in `strategy_perf_by_class.json` is a zero-loss sentinel. Do not quote it.
- Compound return and the sum of per-trade percents are different objects. A positive sum is not expectancy and is not a portfolio-construction edge.

## ML and badge check

`_calibrate_confidence` in `alpha_engine/score_booster.py` is a hardcoded score penalty, not a probability calibrator. It does not rewrite `confidence`. The live ML Health age is the gainer model trained 2026-05-25 (about 175 days). `ml_trading_enabled` is false in `alpha_engine/data/ml_health_status.json`.

PR 843 changed the legend to shadow, but `isVerifiedAlphaPick` and `_is_verified_alpha_pick` still returned true for Polymarket/Kalshi sources, and `copy_pm_` prefixes did too. This branch returns false for those. Copy-trader rows that are not prediction-market copy stay in the badge. The +16 score bonus in `quality_gates.py` is unchanged; that is ranking, not this display fix.

Deflated Sharpe, PBO, and walk-forward efficiency exist as tools. They are not gates on the summary cards. Do not read a card Sharpe as a deflated Sharpe.

## What this branch changes

Display only, in `audit_dashboard/template.html`:

- zero-loss profit factor and win/loss ratio are null, rendered `n/a`
- walk-forward `|oos_sharpe| > 5` renders `n/a`

No emitter changes. No sizing. No ghost-row deletion. No prediction-market promotion.

## Addendum — intrabar ledger 2026-11-16T13:00Z

Checked after the PR opened. Source: `intrabar_truth_by_class.json`, `money_ready_verdict.json` (13:04Z), `strategy_perf_by_class.json` (13:46Z), `db_health.json` (12:48Z).

- Still 0 classes money-ready. EQUITY WR 59.2% with PF 0.94 and average −0.074% per trade. COMMODITY average +0.031% does not survive policy-clean (about n=17, PF 0.17).
- `strategy_perf_by_class.json`: 356 cells have PF≥999 and zero losses. 14 cells pass n≥100, PF>1.5, WR≥50; 2 of those 14 are the 999 sentinel. Do not quote sleeve PFs (ADX 60, equity RSI-reversal 57) as class edge.
- `pf_ok=true` on CHEAP_STOCKS is an empty/infinite sentinel, not a pass.
- Some class `wr_ok` flags use a 40% floor, not 50%. A green WR flag is not the money-ready bar.
- DSR is not ≥0.95 on any class. Walk-forward efficiency is not stored. `wf_oos_ok` can pass when both in-sample and out-of-sample PF are below 1.
- AI leaderboard 93.8% is marked illustrative, n=301, not Tier-2. Tournament rows are not a book: a majority are `MISPRICED_ENTRY`.
- `db_health.json` at 12:48Z already records 22,947 ghost rows, an unhealthy harness, 278 null resolved pnl, and a 27% magnitude mismatch. The live page footer that still says 5/5 is stale relative to that file.

## Left

1. Let `audit-dashboard.yml` deploy #843 and this display fix. Then run `python3 tools/audit_honesty_live_check.py`.
2. Rerun `tools/db_health_check.py` so `db_health.json` matches `ghost_row_verdict` (22,947 must not pass).
3. Do not clean ghost rows without a dry-run and an explicit go-ahead.
4. Do not un-blacklist prediction-market copy trading.
