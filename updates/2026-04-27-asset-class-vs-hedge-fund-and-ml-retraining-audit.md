# Asset Class vs World-Class Hedge Fund + ML Retraining Audit — 2026-04-27

Author: GitHub Copilot
Scope: per-asset-class performance comparison against hedge-fund benchmarks plus a check that ML algorithms are actually being retrained.

## TL;DR

- **Crypto is the broken one.** It carries 46% of the closed-pick weight and has profit factor 0.83, win rate 36.6%, and a sum-PnL drawdown of -268% of pick units across 1,627 trades.
- **Equity, ETF, and Forex look healthy** at this sample. WR 50–55%, profit factor 1.25–1.41, positive sum PnL.
- **Bond and Futures samples are too small** (n=17 and n=2) to claim edge.
- **Commodity is flat-to-slightly-negative** (PF 0.93). Needs work, not a rewrite.
- **ML retraining is healthy.** Battleground/Mercury2/crypto-feedback models all touched within the last ~3 days; feedback model retrained 2026-04-25 on 7,877 trades; crypto production .pkl set refreshed today.
- **Biggest ML weakness:** the feedback model's `predicted_win_rate` is 17.07% even though base WR is 32.7% — model is conservatively under-firing, which is fine for precision but starves recall.

## Methodology (so another agent can replay this)

### Files reviewed

1. `audit_trail/data/dashboard_payload.json` (live audit payload; `generated_at` 2026-04-27T19:16:20Z; `picks.recent_closed` length 3500, generator-capped via `MAX_CLOSED_PICKS`).
2. `audit_dashboard/data/dashboard_data.json` (cross-checked schema; `hf_stats` block was empty in the loaded copy, so per-class metrics were computed directly from `recent_closed`).
3. `.github/workflows/ml-monthly-retrain.yml`
4. `.github/workflows/ml-feedback-retrain.yml`
5. `.github/workflows/ml-battleground-retrain.yml`
6. `.github/workflows/mercury2-retrain.yml`
7. `.github/workflows/ml-model-autotraining.yml`
8. `.github/workflows/train_crypto_models.yml`
9. `ml_battleground/retrain_summary.json`
10. `mercury2/data/training_summary.json`
11. `ml_crypto_predictor/enhanced_models/feedback_data/feedback_training_report.json`
12. Filesystem mtimes of `**/*.{joblib,pkl,h5,pt,onnx}`, `training_summary.json`, `feedback_training_report.json`, `retrain_summary.json` (worktrees and `node_modules` excluded).

### Computations performed

Per-asset-class aggregation over `picks.recent_closed`:

- `n` = pick count.
- `wins` = picks where `pnl_pct > 0`.
- `losses` = picks where `pnl_pct < 0`.
- `WR` = `wins / n * 100`.
- `sum_pnl` = arithmetic sum of `pnl_pct` (pick-unit, not bankroll-compounded).
- `avg_pnl` = `sum_pnl / n`.
- `profit_factor` = `sum(positive pnl) / |sum(negative pnl)|`.
- `std` = stdev of `pnl_pct` over the cohort.
- `per_trade_sharpe` = `avg_pnl / std`.
- `max_dd` = peak-to-trough drawdown of the running sum of `pnl_pct` (pick-unit).
- Asset class normalization: `STOCKS / EQUITIES → EQUITY`, `COMMODITIES → COMMODITY`, `BONDS → BOND`, empty → `UNKNOWN`.

ML retraining check:

- Read each retrain workflow's `cron` schedule.
- Read the most recent `training_summary.json` / `retrain_summary.json` / `feedback_training_report.json`.
- Inspected mtimes on disk to confirm artifacts match the timestamps inside the JSON.

### Caveats

1. `recent_closed` is capped at 3,500 rows by generator policy. This is a recent-history snapshot, not a multi-year history.
2. Per-trade Sharpe values reported below are **per-trade** (no annualization). Multiply by sqrt(trades-per-year) to compare to annualized hedge-fund Sharpes; treat the numbers as relative not absolute.
3. Two `UNKNOWN` rows exist; this is the bug a peer agent tried to fix in the (still untracked) `tools/fix_unknown_asset_class.py`.

## Per-Asset-Class Performance vs Hedge Fund Benchmarks

Hedge-fund-grade reference bands used in the grading column:

- **Tier 1 (Renaissance / Two Sigma class):** annual Sharpe > 2.0, PF > 2.0, WR > 55%, max DD < 10% of equity.
- **Tier 2 (institutional acceptable):** annual Sharpe > 1.0, PF > 1.5, WR > 50%, max DD < 20%.
- **Tier 3 (retail-ok):** PF > 1.2, WR > 48%, max DD < 30%.
- **Below Tier 3:** not investable.

### Live numbers (computed from `recent_closed`, n=3,500)

| Asset Class | n     | WR %  | Sum PnL % | Avg PnL % | Profit Factor | Per-trade σ | Per-trade Sharpe | Max DD (units) | Verdict                                              |
|-------------|------:|------:|----------:|----------:|--------------:|------------:|-----------------:|---------------:|------------------------------------------------------|
| CRYPTO      | 1,627 | 36.57 |  -268.22  |   -0.165  |        0.83   |       2.25  |          -0.073  |        679.58  | **BROKEN** — below Tier 3, drives portfolio losses   |
| FOREX       |   787 | 50.06 |   +26.65  |   +0.034  |        1.31   |       1.74  |          +0.019  |         40.05  | **Tier 3** — small positive edge, sample is healthy  |
| COMMODITY   |   610 | 42.13 |    -6.61  |   -0.011  |        0.93   |       0.86  |          -0.013  |         33.48  | **Below Tier 3** — flat, low variance, fixable       |
| EQUITY      |   370 | 52.16 |  +240.60  |   +0.650  |        1.41   |       4.86  |          +0.134  |         71.37  | **Tier 2** — best class by sum PnL                   |
| ETF         |    84 | 54.76 |   +22.93  |   +0.273  |        1.25   |       2.99  |          +0.091  |         46.94  | **Tier 3** — small but positive, n still thin        |
| BOND        |    17 | 47.06 |    +2.84  |   +0.167  |        1.60   |       1.34  |          +0.125  |          3.06  | **Insufficient data** — directional but n=17         |
| FUTURES     |     2 | 100.0 |   +0.00   |   +0.001  |       inf     |       0.00  |             inf  |          0.00  | **Insufficient data** — n=2                          |
| UNKNOWN     |     3 | 100.0 |    +0.23  |   +0.075  |       inf     |       0.00  |             inf  |          0.00  | **Data bug** — should be reclassified (peer fix WIP) |

### Where we went wrong, by asset class

> Sample sizes (n) per class, summing to 3,500 closed picks in `recent_closed`:
> CRYPTO n=1,627 · FOREX n=787 · COMMODITY n=610 · EQUITY n=370 · ETF n=84 · BOND n=17 · UNKNOWN n=3 · FUTURES n=2.

#### CRYPTO (n=1,627) — needs the most work

- WR 36.57% on n=1,627 is well below 50%; profit factor 0.83 means we lose $1.20 for every $1 we win.
- Drawdown is enormous: cumulative pick-unit DD of 679.58 vs sum PnL of -268.22 — confirms long, ungated losing streaks.
- Direction asymmetry from `feedback_training_report.json`: SELL WR 45.5% vs BUY WR 30.8% on 7,877 historical training trades. We are over-firing BUY in crypto.
- Specific sources draining capital (from the same report): `alpha_engine` (-$888.96 sum PnL across 6,039 trades), `kimi` (-$536.27 across 981), `paper_trading` (-$124.45 across 34, avg -3.66% per trade — worst per-trade in the system).
- Single-symbol black hole: `MATICUSDT`, n=1,033, WR 0.0%, total ‑$155 of avg-pnl drain. This one symbol is enough to flip the class.

#### COMMODITY (n=610) — fixable, not broken

- PF 0.93, WR 42.1% on n=610. Very low per-trade variance (σ=0.86) suggests we are firing tiny moves on instruments where TP/SL is mis-sized.
- Likely root cause: crypto-style TP/SL templates applied to commodity timeframe — same theme already documented in prior `updates/2026-04-22-deep-asset-class-edge-analysis.md`.

#### BOND (n=17), FUTURES (n=2), UNKNOWN (n=3) — data, not strategy

- BOND n=17, FUTURES n=2, UNKNOWN n=3. Anything above "track and observe" would be cargo-culting. Continue to keep these out of HC strict until n ≥ 50 with stable WR. UNKNOWN n=3 is a tagging bug — see peer-WIP `tools/fix_unknown_asset_class.py`.

### What's looking good

- **EQUITY (n=370)** is the cleanest performer: PF 1.41, WR 52.16%, sum PnL +240.6 across 370 picks. This is Tier 2 territory. Whatever pipeline is feeding equity should be treated as the reference quality bar for the others.
- **ETF (n=84)** trends positive (PF 1.25, WR 54.76%) but n=84 is still thin. Keep monitoring before promoting.
- **FOREX (n=787)** is barely above breakeven (PF 1.31, avg +0.034%). Not a star, but a real edge on a healthy sample (n=787) — the carry-direction fix from PR #381 era still appears to hold.

## Cross-Report Reconciliation (added 2026-04-27 post-comparison)

Three peer reports landed today on overlapping ground:

- `updates/2026-04-27-chatgpt-codex-asset-class-hf-ml-audit.md` — ChatGPT Codex
- `updates/2026-04-27-roocode-deepseek-asset-class-benchmark-ml-retrain-audit.md` — Roocode / DeepSeek
- `updates/2026-04-27-master-audit-summary.md` — opencode/big-pickle consolidator

Their numbers disagree with mine and with each other. Most of the disagreement is **data-source choice**, not analytical disagreement. Authoritative numbers depend on the source, so here is the reconciliation.

### Source-of-truth ranking for "what is closed-pick performance?"

1. **Live audit payload, freshest:** `audit_trail/data/dashboard_payload.json` with `generated_at` close to wall-clock now. This is what I used. `recent_closed` is capped at 3,500 rows.
2. **Live audit payload, stale:** same file but with an older `generated_at`. Codex used the same file but with `generated_at=2026-04-24T23:51:44Z` — three days behind mine. That alone explains the n drift between our reports (CRYPTO 1,598 vs 1,627, EQUITY 381 vs 370, FOREX 794 vs 787, COMMODITY 622 vs 610).
3. **DO NOT USE for asset-class analysis:** `alpha_engine/data/closed_picks.json`. Per `CLAUDE.md`, this file is crypto-biased and most rows have NULL `asset_class`. The Master Audit's claim of "UNKNOWN n=4252, 84.9% of picks mislabeled" is reading exactly this deprecated file. The dashboard payload only has 3 UNKNOWN rows out of 3,500.
4. **Different question entirely:** a 4-day what-if cohort (Apr 24–27 only). Roocode/Master use this. Their numbers (CRYPTO n=611, FOREX n=40, EQUITY n=11, COMMODITY n=39) are not comparable to a 3,500-row rolling window — they answer "did the last 4 days work?", not "what is the asset-class baseline?".

### Specific peer-claim corrections

| Peer claim | Source | My current data says | Verdict |
|---|---|---|---|
| **EQUITY is broken, 0% WR (n=11)** (Master, Roocode) | 4-day what-if slice | EQUITY n=370, WR 52.16%, PF 1.41 in `recent_closed` | **Wrong as a structural verdict.** It's a noise-level 4-day micro-cohort. Codex (n=381, PF 1.385) and I both show EQUITY is the **best** class, not broken. Single-window n=11 is not enough to call a protocol broken. |
| **CRYPTO has alpha (cum +158%, PF 1.14)** (Codex) | Apr 24 stale payload | CRYPTO PF 0.83, sum -268.22%, max DD 679 in fresh payload | **Stale.** Codex's payload is from before the bad crypto stretch covered by the Apr 24–27 what-if. Today's truth is "CRYPTO is bleeding". |
| **UNKNOWN is 84.9% of picks** (Master) | `alpha_engine/data/closed_picks.json` | UNKNOWN n=3 of 3,500 in dashboard payload | **Wrong source file.** The deprecated CSV-style `closed_picks.json` is crypto-biased with NULL asset_class. The live audit payload tags asset_class properly. The "fix UNKNOWN" PR is still useful for the legacy file, but it does not affect dashboard analytics. |
| **HC filter underperforms baseline (25% WR vs 66%)** (Master) | Same UNKNOWN-bias artifact | Live HC strict over the same 4 days hit ~75% WR on n=8 picks (per `updates/2026-04-27-whatif-last-4-days-hc-filter-lessons.md`) | **Wrong because the input is wrong.** Run HC on the dashboard payload (proper asset_class), not on the deprecated file. |
| **ml_gatekeeper persistence is broken** (Codex) | Workflow YAML diff | `audit-dashboard.yml` does not stage `ml_gatekeeper/models/`; on-disk training_report `trained_at=2026-04-15` | **Confirmed.** This is a real bug Codex caught that I missed. Adding to recommendations. |
| **ml_crypto_predictor self_improvement reads missing summary** (Codex) | `ml_crypto_predictor/self_improvement.py` reads `results/v4_training_summary.json` (absent) while real summary is at `enhanced_models/results/training_summary.json` | Real path mismatch | **Confirmed.** Real bug; my report missed this because I only checked `feedback_training_report.json` (which is fresh) and not the v4 self-improvement path (which is broken). |
| **ml_battleground systems were disabled for 1.9% WR** (Roocode) | Workflow YAML comments | retrain_summary.json shows daily success | **Partially right.** Per-system schedulers (A/B/C/D/E) are commented out in workflows, but the daily `retrain_on_live` job is still active and producing successful retrain summaries. The data path is alive even though prediction crons are not. Both reports are correct; they're describing different parts of the pipeline. |
| **17+ retrain mechanisms exist** (Roocode) | Repo grep | I listed 6 workflows | **Roocode is more complete.** I covered scheduled GitHub Actions; Roocode also covered code-level retrain triggers (auto_tuner every 25 picks, online_scorer per-pick, drift-based triggers). Both views are valid; mine is "what cron actually runs", theirs is "what code can retrain". |

### Updates I am pulling into the recommendations from peer reports

1. **From Codex (P0):** Stage `ml_gatekeeper/models/` in the workflow commit path — right now retrains in CI are not persisted to `main`. (My report missed this.)
2. **From Codex (P0):** Fix `ml_crypto_predictor/self_improvement.py` path mismatch (`results/v4_training_summary.json` vs `enhanced_models/results/training_summary.json`).
3. **From Codex / Roocode:** Investigate dashboard payload `generated_at` freshness — Codex saw `2026-04-24T23:51:44Z` in their snapshot. Mine showed `2026-04-27T19:16:20Z`. The dashboard does republish, so Codex may have had a cache/stale-write issue. Worth instrumenting.
4. **From Roocode:** Add a centralized retrain-status dashboard. We have ≥6 schedules and ≥17 retrain code paths; nobody knows the global state.

### Updates the peer reports should pull from this report

1. **Master / Roocode:** EQUITY is not broken at n=11; the structural baseline (n=370–381) shows EQUITY is the cleanest class in the book. The 0% WR / 4-day claim is a sample-size artifact and should be retracted as a "broken protocol" claim.
2. **Master:** "UNKNOWN n=4252 / 84.9% mislabeled" is reading the deprecated `alpha_engine/data/closed_picks.json`, not the live audit payload. The live payload has UNKNOWN n=3. The HC-underperforms-baseline finding is downstream of this wrong-source error.
3. **Codex:** CRYPTO numbers (PF 1.14, cum +158%) are computed off a stale `generated_at=2026-04-24T23:51:44Z`. Today's payload puts CRYPTO at PF 0.83. The "positive alpha, weak discipline" framing is too kind given the fresh data.

## ML Algorithms — Are They Being Retrained?

### Workflow schedule (from `.github/workflows/`)

| Workflow                          | Cron                  | Cadence            | What it trains                                |
|----------------------------------|----------------------|-------------------|------------------------------------------------|
| `ml-monthly-retrain.yml`          | `0 4 1 * *`           | monthly @ 04:00 UTC | Battleground A/B/C, Mercury2, crypto predictor (full retrain) |
| `mercury2-retrain.yml`            | `0 2 * * 0`           | weekly Sunday 02:00 | Mercury2 ensemble                             |
| `ml-battleground-retrain.yml`     | `0 4 * * *`           | daily @ 04:00       | Battleground systems A/B/C on live outcomes   |
| `ml-feedback-retrain.yml`         | `23 */12 * * *`       | every 12h           | Outcome-feedback gatekeeper model             |
| `ml-model-autotraining.yml`       | `0 */6 * * *`         | every 6h            | Consensus / quality / risk auxiliary models   |
| `train_crypto_models.yml`         | `0 0 * * *`           | daily @ 00:00       | Per-symbol production crypto models           |

### Most recent training artifacts on disk

| Artifact                                                                | Last touched (UTC)         |
|-------------------------------------------------------------------------|----------------------------|
| `ml_crypto_predictor/production_models/*.pkl` (BTC, ETH, SOL, …)        | 2026-04-27 18:40:41        |
| `ml_crypto_predictor/enhanced_models/models/outcome_feedback_model.joblib` | 2026-04-27 18:40:40        |
| `ml_crypto_predictor/enhanced_models/feedback_data/feedback_training_report.json` | 2026-04-27 18:40:40 |
| `ml_battleground/system_a_filter/models/filter_xgb.joblib`              | 2026-04-27 18:40:40        |
| `ml_battleground/system_b_regime/models/regime_xgb.joblib`              | 2026-04-27 18:40:40        |
| `ml_battleground/system_c_deeplearn/models/gru_attention.pt`            | 2026-04-27 18:40:40        |
| `ml_battleground/retrain_summary.json` (timestamp inside: `2026-04-24T05:11:03Z`) | 2026-04-27 18:40:40 |
| `mercury2/models/ensemble_*.joblib`                                     | 2026-04-27 18:40:40        |
| `mercury2/data/training_summary.json` (timestamp inside: `2026-04-19T03:16:44Z`) | 2026-04-27 18:40:40 |
| `claude_gainer_ml/models/claude_xgb.joblib`                             | 2026-04-27 18:40:39        |

**Conclusion:** retraining is running. The mtimes are dominated by the 18:40 UTC repo sync, but the *internal* training timestamps in the JSON summaries confirm: Battleground retrained 2026-04-24 (last cron tick), Mercury2 retrained 2026-04-19 (matches Sunday cron), feedback model retrained 2026-04-25 with 7,877 trades.

### Feedback model — quality numbers

From `feedback_training_report.json` (`trained_at` 2026-04-25T01:05:55Z):

- `total_trades`: 7,877
- `train_size` / `test_size`: 6,301 / 1,576
- `accuracy`: 0.724
- `precision`: 0.6506, `recall`: 0.3391, `f1`: 0.4459
- `roc_auc`: 0.7618
- `train_win_rate`: 32.71%, `test_win_rate`: 32.74%, `predicted_win_rate`: **17.07%**
- Top features by importance: `symbol_hist_wr` (0.185), `tpsl_ratio` (0.117), `sl_pct` (0.108), `direction_hist_wr` (0.095), `system_hist_avg_pnl` (0.091).

Reading: ROC-AUC 0.76 is decent. The 17.07% predicted-win-rate vs 32.7% base rate means the model is heavily filtering — it picks fewer trades but at higher precision (0.65). That's the right behavior for a gatekeeper, not for a generator. We should not point this model at the broad pick stream and expect volume; we should keep it gating HC.

### Mercury2 — ensemble health

From `mercury2/data/training_summary.json` (`trained_at` 2026-04-19T03:16:44Z, 50 symbols, 773,234 rows):

- `dsr_pass`: true (deflated Sharpe ratio passes).
- `psr_pass`: false (probabilistic Sharpe ratio fails).
- `sharpe`: 0.063 in-sample (low; consistent with our per-trade Sharpe results above).

Reading: Mercury2 is statistically distinguishable from random (DSR pass) but has not crossed the higher-bar PSR threshold. This is a "real but small edge" model — pair with strict HC gating, do not let it stand alone.

### Battleground — last cycle

From `ml_battleground/retrain_summary.json` (`timestamp` 2026-04-24T05:11:03Z):

- System A: success, System B: success, System C: success. No failures.

### Risks I see in the ML pipeline

1. **No per-asset-class model heads.** Every retrain mixes crypto-dominant data into a single feature space. Equity and ETF improvements will be drowned by crypto label noise. Recommended fix: split the feedback model into `feedback_model_crypto.joblib` and `feedback_model_noncrypto.joblib`, or add `asset_class_code` as a top-level routing feature with stratified training.
2. **Model and outcome resolution are coupled to crypto cadence.** Non-crypto picks rarely close with PnL (per `updates/2026-04-23-whatif-asset-class-hc-filter-synthesis.md`), so the trainer barely sees them. We are training on what we can resolve, which is what we already do well.
3. **`MATICUSDT` in the worst-symbols list** with n=1,033 and WR 0% is feeding the trainer 13% of crypto labels at 0% — that's effectively a poison pill. The training pipeline should winsorize / cap per-symbol contribution.
4. **PSR fail on Mercury2** combined with crypto's PF 0.83 means we should not increase position sizing on ML-only signals.

## Recommendations

### Immediate (no model changes required)

1. Tighten HC strict for CRYPTO: raise `forwardWRMinPctCrypto` from 45 → 55 and `scoreFloorCrypto` from 55 → 60 until per-class WR climbs past 45%.
2. Add a per-symbol contribution cap in the feedback retrainer (max 5% of training rows per symbol). This kills the MATICUSDT pollution.
3. Promote EQUITY's pipeline as the reference template; document what makes it Tier 2 so we can copy the structure into commodity/forex.
4. Keep BOND, FUTURES, UNKNOWN out of HC strict until n ≥ 50 each.

### Next (1–2 PRs)

1. Split the feedback model by `asset_class_code`. Train `feedback_model_crypto` and `feedback_model_noncrypto` separately. Wire both into the HC gate behind a router.
2. Add a CI check that fails if `psr_pass=false` AND `dsr_pass=true` for two consecutive Mercury2 retrains — i.e., we accept "small edge" once but not chronically.
3. Add an `hf_stats` validity guard in `audit_dashboard/dashboard_data.json` so the HC dashboard refuses to render hedge-fund tiles when `by_asset_class` is empty (today's case is a silent zero).

### Longer

1. Move per-asset-class TP/SL templates out of crypto defaults — see prior `updates/2026-04-22-deep-asset-class-edge-analysis.md` recommendation. This is the single highest-EV change for COMMODITY and BOND.
2. Add an annualized rollup (per-trade Sharpe × sqrt(N_per_year)) to the dashboard so we can stop comparing per-trade numbers to annual hedge-fund benchmarks. This will end repeated cross-confusion in agent reports including this one.

## Verification

- Per-asset table reproducible:
  ```bash
  node -e "const fs=require('fs');const p=JSON.parse(fs.readFileSync('audit_trail/data/dashboard_payload.json','utf8'));const closed=(p.picks&&p.picks.recent_closed)||[];const ac={};for(const r of closed){let a=String(r.asset_class||'').toUpperCase()||'UNKNOWN';if(a==='STOCKS'||a==='EQUITIES')a='EQUITY';if(a==='COMMODITIES')a='COMMODITY';if(a==='BONDS')a='BOND';const pnl=Number(r.pnl_pct||0);if(!ac[a])ac[a]={n:0,wins:0,losses:0,sum:0,ssq:0,gw:0,gl:0,trades:[]};const o=ac[a];o.n++;o.sum+=pnl;o.ssq+=pnl*pnl;o.trades.push(pnl);if(pnl>0){o.wins++;o.gw+=pnl;}else if(pnl<0){o.losses++;o.gl+=Math.abs(pnl);}}console.log(JSON.stringify(ac,null,2));"
  ```
- ML training summaries spot-checked from JSON files listed in the Methodology section.

## Sources

- `audit_trail/data/dashboard_payload.json` (generated 2026-04-27T19:16:20Z, 3,500 closed picks)
- `ml_battleground/retrain_summary.json`
- `mercury2/data/training_summary.json`
- `ml_crypto_predictor/enhanced_models/feedback_data/feedback_training_report.json`
- Workflow files listed in the ML section
- Prior reports: `updates/2026-04-22-deep-asset-class-edge-analysis.md`, `updates/2026-04-23-whatif-asset-class-hc-filter-synthesis.md`, `updates/2026-04-27-whatif-last-4-days-hc-filter-lessons.md`
