# Asset-Class Independent Recompute — 2026-04-27 (mercury-2 / Copilot Opus 4.7)

> **Note:** A peer also wrote `reports/asset_class_independent_recompute_2026_04_27.md`. This file is the GitHub-Copilot-Opus-4.7 independent recompute, written without overwriting the peer file. Differences between the two should be reconciled in the next round.

**Author:** mercury-2 (GitHub Copilot, Claude Opus 4.7)
**Date:** 2026-04-27
**Primary source:** `audit_trail/data/dashboard_payload.json`, `metadata.generated_at = 2026-04-27T22:08:21.106Z` (1.55 h old at compute time)
**Secondary source:** `audit_dashboard/data/dashboard_data.json`, same `generated_at`, n=3,500 rows, `hf_stats` present (7 keys) ✅
**Decision:** **PROCEED** — payload age 1.55 h ≤ 12 h.
**Reproducibility:** [tools/_mercury2_recompute.js](../tools/_mercury2_recompute.js); raw stdout in [tools/_mercury2_recompute.out](../tools/_mercury2_recompute.out). Run: `node tools/_mercury2_recompute.js`.

---

## 1. Per-Asset-Class Scorecard (n=3,500 from `picks.recent_closed`)

| Asset Class | n | WR % | Sum PnL % | PF | Avg PnL % | StdDev | Sharpe/trade | MaxDD % | Verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| BOND | 17 | 47.06 | +2.84 | 1.601 | 0.1673 | 1.3430 | 0.1246 | 3.47 | insufficient data (n<50) |
| COMMODITY | 622 | 42.60 | -9.82 | 0.896 | -0.0158 | 0.8632 | -0.0183 | 39.79 | **Below Tier 3** |
| CRYPTO | 1,598 | 42.18 | +158.74 | 1.140 | 0.0993 | 2.1352 | 0.0465 | 178.64 | **Below Tier 3** (PF<1.2, MaxDD>30%) |
| EQUITY | 381 | 51.97 | +232.13 | 1.385 | 0.6093 | 4.8182 | 0.1265 | 70.95 | Tier 3 (DD blocks Tier 2) |
| ETF | 83 | 54.22 | +20.25 | 1.220 | 0.2440 | 2.9913 | 0.0816 | 48.86 | Tier 3 borderline (n<100) |
| FOREX | 794 | 50.38 | +29.63 | 1.349 | 0.0373 | 1.7367 | 0.0215 | 38.06 | Tier 3 (see §2 caveat) |
| FUTURES | 2 | 100.00 | 0.00 | inf | 0.0005 | 0.0001 | n/a | 0.00 | insufficient data (n<50) |
| UNKNOWN | 3 | 100.00 | +0.23 | inf | 0.0751 | 0.0001 | n/a | 0.00 | insufficient (per spec, ignored) |

Tier definitions: T1 PF>2 WR>55 DD<10; T2 PF>1.5 WR>50 DD<20; T3 PF>1.2 WR>48 DD<30. **No class meets Tier 2** on the DD criterion.

Distribution: CRYPTO 45.7 %, FOREX 22.7 %, COMMODITY 17.8 %, EQUITY 10.9 %, ETF 2.4 %, BOND 0.5 %, UNKNOWN 0.09 %, FUTURES 0.06 %.

## 2. Resolver-Noise Share — Non-Crypto Only

Per [audit_trail/outcome_resolver.py](../audit_trail/outcome_resolver.py) (`WIN_THRESHOLD≈1bp` near line 97; live yfinance close at 384–405), every non-crypto pick closes at spot every run. Wins where `|pnl_pct| < 0.05 %` are **not edge** — they are resolver flicker.

| Asset Class | n | wins | wins with `|pnl|<0.05%` | share % | flag |
|---|---:|---:|---:|---:|---|
| FOREX | 794 | 400 | 253 | **63.25** | **UNRELIABLE — WR is meaningless** |
| COMMODITY | 622 | 265 | 177 | **66.79** | **UNRELIABLE — WR is meaningless** |
| EQUITY | 381 | 198 | 18 | 9.09 | ok |
| ETF | 83 | 45 | 3 | 6.67 | ok |
| BOND | 17 | 8 | 1 | 12.50 | ok (n too small anyway) |

**Implication:** the FOREX "Tier 3 / promising" verdict and COMMODITY "Below Tier 3" verdict cannot be relied on. Two-thirds of FOREX/COMMODITY "wins" are sub-bp resolver flicker. EQUITY / ETF / BOND verdicts are intact.

## 3. ML Retraining Audit

Mtimes captured 2026-04-27 ~23:42 UTC. "Persists?" = a workflow YAML actually runs `git add` on a directory matching the artifact path.

| System | Code | Cron | Latest artifact (mtime) | Age | Persists to main? | Status |
|---|---|---|---|---:|---|---|
| `alpha_engine/auto_tuner.py` | yes | `alpha-engine-live.yml`: `python -m auto_tuner` per scan, `\|\| echo "non-fatal"` | `alpha_engine/data/rf_model.pkl` 2026-04-15T11:53 | **12.3 d** | yes (`git add -f alpha_engine/data/rf_model.pkl`) | **STALE** |
| `alpha_engine/crypto_ml_tuner.py` | yes | scanner cycle | shares `rf_model.pkl` | **12.3 d** | yes | **STALE** |
| `alpha_engine/ml_ranker.py` | yes | scanner cycle | `ml_challenger.joblib` 2026-04-15T11:53 | **12.3 d** | yes | **STALE** |
| `alpha_engine/meta_labeler.py` | yes | n/a | shares above | 12.3 d | shared | **STALE** |
| `ml_battleground/retrain_on_live.py` | yes | `ml-battleground-retrain.yml` `0 4 * * *` | `system_c_deeplearn/models/gru_attention.pt` 2026-04-27T18:49 | 0.04 d | yes | fresh ✅ |
| `ml_gatekeeper/gatekeeper.py` | yes | invoked by `audit-dashboard.yml` | `models/gatekeeper_model.joblib` 2026-04-15T14:06 | **12.2 d** | **NO** — no `git add ml_gatekeeper/models/` in any workflow; `git log --oneline -- ml_gatekeeper/models/` returns 2 commits, neither a retrain | **STALE + NON-PERSISTING (Codex finding confirmed)** |
| `ml_crypto_predictor/enhanced_models/feedback_trainer.py` | yes | `ml-feedback-retrain.yml` `23 */12 * * *` | `outcome_feedback_model.joblib` 2026-04-27T18:49 | 0.04 d | yes | fresh ✅ |
| `ml_crypto_predictor/self_improvement.py` | yes | n/a | line 9 reads `results/v4_training_summary.json` — **does not exist anywhere in repo** (file_search 0 hits; `ml_crypto_predictor/results/` directory missing) | n/a | n/a | **BROKEN PATH (Codex finding confirmed)** |
| `mercury2/trainer.py` | yes | `mercury2-retrain.yml` `0 2 * * 0` | `mercury2/models/top_gainer.joblib` 2026-04-27T18:49 | 0.04 d | yes (`git add mercury2/models/`) | fresh ✅ |
| `claude_gainer_ml/trigger_retraining.py` | yes | `claude-gainer-tracker.yml` `15 */4 * * *` + Sun `0 6 * * 0` | `claude_xgb.joblib` 2026-04-27T18:49 | 0.04 d | yes | fresh ✅ |
| `model_health_agent.py` | yes | n/a (drift checker, not trainer) | n/a | n/a | n/a | could not verify wiring this pass |

**Caveat on mtimes clustered at 2026-04-27T18:49:** that's the last `audit-dashboard.yml` run touching files via git checkout, **not** necessarily `trained_at`. Internal `trained_at` of joblibs not extracted (would require loading binaries). Treat fresh mtimes as upper bound on freshness.

## 4. HC Filter Validation (3-day what-if, Apr 25–27)

Command: `node tools/audit_what_if_entry_day.js --dates 2026-04-25,2026-04-26,2026-04-27`. Baseline (all closed in window): **n=668, sum PnL -51.85 %, WR 35.78 %**. HC strict: **n=5, sum PnL +22.74 %, WR 100 %**. Pass rate: **5/668 = 0.75 %** — below the 2 % over-filtering threshold. HC strict fired 0 picks on Apr 27 despite 154 closed picks that day. HC strict is currently filtering out a losing baseline correctly, but volume is too low to drive PnL — relaxation should be CRYPTO/EQUITY-only (FOREX/COMMODITY thresholds cannot be tuned on §2 noise wins). Gate-level fail-reason breakdown not numerically reproduced here.

## 5. Divergence Table (peer reports read AFTER independent compute)

| Metric | mercury-2 (n=) | Roocode | Copilot peer | Codex | opencode/big-pickle | Likely cause |
|---|---|---|---|---|---|---|
| CRYPTO n | 1,598 | 611 | 1,627 | 1,598 | 611 | `4-day window vs full-history` (RC/BP); fresh-payload drift Copilot vs me |
| CRYPTO WR % | 42.18 | 37.0 | 36.57 | 42.18 | 37.0 | `4-day window` (RC/BP); `stale payload` (Copilot, n drift 1,627→1,598) |
| CRYPTO PF | 1.140 | n/a | 0.83 | 1.140 | n/a | `stale payload` (Copilot 19:16Z vs my 22:08Z; Codex matches me from 04-24 payload) |
| CRYPTO Sum PnL % | +158.74 | -32.10 | -268.22 | +158.7448 | -32.10 | `4-day window`; `stale payload` (Copilot) |
| FOREX n | 794 | 40 | 787 | 794 | 40 | `4-day window`; minor payload drift Copilot |
| FOREX WR % | 50.38 | 50.0 | 50.06 | 50.38 | 50.0 | aligned within rounding; **but see §2 — 63.25 % of FOREX wins are noise** |
| FOREX PF | 1.349 | n/a | 1.31 | 1.349 | n/a | minor payload drift |
| EQUITY n | 381 | 11 | 370 | 381 | 11 | `4-day window` (RC/BP) |
| EQUITY WR % | 51.97 | 0.0 | 52.16 | 51.97 | 0.0 | `4-day window` (RC/BP) |
| EQUITY PF | 1.385 | n/a | 1.41 | 1.385 | n/a | minor payload drift |
| COMMODITY n | 622 | 39 | 610 | 622 | 39 | `4-day window` (RC/BP) |
| COMMODITY PF | 0.896 | n/a | 0.93 | 0.896 | n/a | minor payload drift; **§2: 66.79 % wins are noise** |
| ETF n | 83 | 10 | n/a | 83 | 10 | `4-day window` |
| BOND n | 17 | 0 | 17 | 17 | 0 | `4-day window` |
| UNKNOWN share | 3 / 3,500 = 0.09 % | claims 84.9 % | 0.09 % equiv | n/a | claims 84.9 % | `deprecated source file` (RC/BP read `closed_picks.json`, NULL asset_class) |
| FOREX/COMMODITY resolver-noise wins | 63.25 % / 66.79 % | not measured | not measured | not measured | not measured | `resolver-noise wins counted` |
| HC strict 3-day n | 5 / 668 = 0.75 % | "ZERO Apr 27" qualitative | "75% WR" qualitative | "fragile" qualitative | "25% WR vs 66% baseline" | RC/BP: deprecated source |
| ml_gatekeeper persistence | NOT persisted (2 commits ever) | flagged | flagged | flagged | not flagged | confirmed |
| `results/v4_training_summary.json` | does not exist | flagged | flagged | flagged | not flagged | confirmed |

## 6. P0 / P1 Recommendations (data-supported only)

- **P0 — Resolver bug invalidates two largest non-crypto verdicts.** FOREX (n=794) and COMMODITY (n=622) win-rates are 63–67 % resolver-noise via `outcome_resolver.py:384–405`. Until that resolver closes only at TP/SL/time-exit (or filters `|pnl_pct|<0.05 %` as no-trade), no non-crypto recommendation can be trusted. Tracking: `feedback_noncrypto_resolver_live_close_bug.md`.
- **P0 — `ml_gatekeeper/gatekeeper.py` is non-persisting.** Workflow runs it but no `git add ml_gatekeeper/models/` exists; `git log --oneline -- ml_gatekeeper/models/` shows 2 commits ever. Add a persistence step to `audit-dashboard.yml`, or accept that gatekeeper scores compute against a 12-day-old `gatekeeper_model.joblib`.
- **P0 — `ml_crypto_predictor/self_improvement.py` reads non-existent file.** Line 9 → `results/v4_training_summary.json`; directory missing. Fix path or remove from production graph.
- **P1 — `alpha_engine/data/rf_model.pkl` is 12.3 days stale despite per-scan retrain.** Persisted (`alpha-engine-live.yml:683`) but trainer is failing silently — `|| echo "Auto-tuner run failed (non-fatal)"` at line 592 swallows the error. Add a separate failure-counter step.
- **P1 — HC strict pass rate 0.75 % over 3 days** (5/668). Below the 2 % over-filtering threshold. Per-class threshold tuning is the right next investigation, but FOREX/COMMODITY tuning is blocked by §2 until resolver fixed.
- **P1 — CRYPTO MaxDD 178.6 % (n=1,598).** Even with PF 1.140 and net +158.74 %, drawdown exceeds Tier 3 (DD<30 %). Highest-leverage fix from this data: per-symbol gates on the n>10 / WR<30 % poison set surfaced in [tools/_mercury2_recompute.out](../tools/_mercury2_recompute.out): ONDOUSDT (12.5 %, n=24), LTCUSDT (27.16 %, n=81), HYPEUSDT (26.09 %, n=46), OPUSDT (27.27 %, n=22), TIAUSDT (25.00 %, n=16), TONUSDT (9.09 %, n=11). For COMMODITY: CT=F (8.33 %, n=12), KC=F (8.33 %, n=12).

## Could not verify (do not borrow peer numbers)

- Per-trade annualized Sharpe — needs `trades_per_year` per class which is not in payload metadata.
- HC strict gate-level fail reasons — requires re-running `evaluateHcGates1to9()` on the full set.
- `model_health_agent.py` drift integration status — needs deeper trace.
- `outcome_feedback_model.joblib` internal `trained_at` — requires loading binary; skipped.
