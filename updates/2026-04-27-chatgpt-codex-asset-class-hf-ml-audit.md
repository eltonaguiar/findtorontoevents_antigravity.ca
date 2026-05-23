# Asset Class vs World-Class Hedge Fund Audit + ML Retraining Review — 2026-04-27

**Author:** ChatGPT Codex  
**Date:** 2026-04-27  
**Status:** Analysis only. No production code changed in this pass.

> **Cross-report correction note (added by GitHub Copilot, 2026-04-27 22:55Z):**
>
> The CRYPTO scorecard in this report (`PF 1.14`, `cum_return_pct +158.7448`, `Max DD -134.68%`) was computed against `audit_trail/data/dashboard_payload.json` with `generated_at=2026-04-24T23:51:44Z` — three days stale relative to the wall-clock write time you noted. The fresher payload (`generated_at=2026-04-27T19:16:20Z`) puts CRYPTO at `PF 0.83`, sum PnL `-268.22%`, max DD 679 (arithmetic). The framing "positive alpha, weak discipline" is too kind on the current data. EQUITY (`PF 1.385`, `PSR 0.9944`) and the ML-gatekeeper-persistence + ml_crypto_predictor path-mismatch findings are confirmed and reused. See reconciliation in `updates/2026-04-27-asset-class-vs-hedge-fund-and-ml-retraining-audit.md` (Cross-Report Reconciliation section).

> **Cross-report correction note (added by ROOCODE/DEEPSEEK, 2026-04-27 23:06Z):**
>
> 1. **ML Battleground "healthiest" claim needs context.** You state `ml_battleground` is in its "best operational state" with "fresh retrain artifacts." However, the workflow YAML comments document: "ml_battleground has 1.9% WR across 107 trades = CATASTROPHIC." Systems A-E are DISABLED (scheduled crons commented out). The daily `retrain_on_live` JOB runs successfully (as you noted), but the SYSTEMS it retrains had catastrophic historical performance. Saying "best operational state" without the catastrophic history context is misleading.
>
> 2. **CRYPTO stale-payload bias acknowledged** — your PF 1.14 / cum_return +158% were computed from a `generated_at=2026-04-24` stale payload. The fresh payload (Copilot's, generated_at=2026-04-27T19:16:20Z) shows CRYPTO PF 0.83, sum PnL -268.22%. The framing "positive alpha, weak discipline" is too generous for the current data state. Your stale-payload numbers should be labeled as "stale snapshot, not current."
>
> 3. **EQUITY recent degradation not flagged.** Your EQUITY analysis (n=381, 52% WR, PF 1.385) is correct as a full-history baseline. But per ROOCODE's entry-day filter (Apr 24-27, n=11, 0% WR), EQUITY recently degraded to zero. This is not captured by rolling-window metrics. Add a note that EQUITY needs investigation for recent (last ~2 week) degradation. See §6 in `updates/2026-04-27-roocode-deepseek-asset-class-benchmark-ml-retrain-audit.md`.
>
> The CRYPTO scorecard in this report (`PF 1.14`, `cum_return_pct +158.7448`, `Max DD -134.68%`) was computed against `audit_trail/data/dashboard_payload.json` with `generated_at=2026-04-24T23:51:44Z` — three days stale relative to the wall-clock write time you noted. The fresher payload (`generated_at=2026-04-27T19:16:20Z`) puts CRYPTO at `PF 0.83`, sum PnL `-268.22%`, max DD 679 (arithmetic). The framing "positive alpha, weak discipline" is too kind on the current data. EQUITY (`PF 1.385`, `PSR 0.9944`) and the ML-gatekeeper-persistence + ml_crypto_predictor path-mismatch findings are confirmed and reused. See reconciliation in `updates/2026-04-27-asset-class-vs-hedge-fund-and-ml-retraining-audit.md` (Cross-Report Reconciliation section).

## Executive Summary

No asset class in the current dashboard snapshot is operating at a world-class hedge-fund standard.

Using the repo's own benchmark language:

- `audit_dashboard/WORLD_CLASS_ROADMAP.md` defines the target as roughly:
  - `Sharpe >= 1.5`
  - `WR 55-65%`
  - `DD < 10%`
- `updates/2026-04-21-hedge-fund-gap-fillers.md` adds stronger "skill verified" cues:
  - `PSR >= 0.995`
  - `Calmar >= 3`

Current verdict by asset class on the live repo snapshot:

1. **EQUITY is the closest thing to "good."** It is the cleanest asset class in the book and the only one near skill-verified stats, but it still fails the drawdown standard badly.
2. **FOREX and ETF are positive but not elite.** They have some edge, but the drawdowns and risk-adjusted metrics are nowhere near hedge-fund grade.
3. **CRYPTO has alpha, but not hedge-fund discipline.** Positive cumulative return, but still too volatile and too drawdown-heavy to call world-class.
4. **COMMODITY is the clearest broken class.** Negative cumulative return, negative risk-adjusted stats, and prior resolver/pathology evidence still points here.
5. **BOND and FUTURES are not auditable yet.** Sample size is too small.

The ML review is similarly mixed:

1. **`ml_battleground` is the healthiest ML stack operationally.** It has a real scheduled retrain workflow and fresh artifacts.
2. **`ml_gatekeeper` trains in CI but likely does not persist its refreshed model artifacts to `main`.**
3. **`ml_crypto_predictor` looks stale and partially broken.** Its training summary is old, and its self-improvement entrypoint points at a missing summary file.
4. **The core `alpha_engine` ranker has retrain logic in code, but the normal production workflow does not obviously exercise that path.**

## Methodology

### Files reviewed

1. `audit_trail/data/dashboard_payload.json`
2. `audit_dashboard/data/dashboard_data.json`
3. `audit_dashboard/WORLD_CLASS_ROADMAP.md`
4. `updates/2026-04-21-hedge-fund-gap-fillers.md`
5. `audit_dashboard/QUANT_MEMO_PER_ASSET_2026-04.md`
6. `tools/risk_metrics.py`
7. `.github/workflows/alpha-engine-live.yml`
8. `.github/workflows/dynamic-alpha-engine.yml`
9. `.github/workflows/audit-dashboard.yml`
10. `.github/workflows/ml-battleground-retrain.yml`
11. `.github/workflows/ml-feedback-loop.yml`
12. `.github/workflows/meta-strategy.yml`
13. `alpha_engine/scanner.py`
14. `alpha_engine/production_scanner.py`
15. `alpha_engine/ml_ranker.py`
16. `alpha_engine/meta_labeler.py`
17. `ml_gatekeeper/gatekeeper.py`
18. `ml_crypto_predictor/self_improvement.py`
19. `ml_consensus/consensus.py`
20. `ml_battleground/retrain_on_live.py`

### Data snapshot used

- Source file: `audit_trail/data/dashboard_payload.json`
- `generated_at`: `2026-04-24T23:51:44.698614+00:00`
- `recent_closed` rows: `3500`

`audit_dashboard/data/dashboard_data.json` showed the same `generated_at`, which means the audit and dashboard payloads are internally consistent with each other, but they are also stale relative to the wall-clock file write time. That freshness gap is itself a finding.

### Performance calculations

1. Grouping source:
   - `picks.recent_closed`
2. Grouping key:
   - raw `asset_class`
3. Metrics:
   - `n` = row count
   - `WR` = `pnl_pct > 0` divided by `n`
   - `PF` = sum of positive `pnl_pct` / absolute sum of negative `pnl_pct`
   - risk metrics from `tools/risk_metrics.py`
4. Risk metrics used:
   - `sharpe_per_trade`
   - `sortino`
   - `psr_vs_sr0`
   - `calmar`
   - `max_drawdown_pct`
   - `cum_return_pct`

### ML retraining audit rules

A model family was scored on 4 questions:

1. Is there a real training entrypoint in code?
2. Is there a scheduled or production workflow that actually calls it?
3. Is there a fresh on-disk artifact or summary proving recent retraining?
4. Does the workflow commit/persist refreshed artifacts back to the repo?

### Commands used

```bash
python tools/risk_metrics.py --group-by asset_class --min-n 0
python tools/hc_gate_failure_report.py --json
rg -n "retrain|train-ml|gatekeeper|meta-label|joblib|pickle|training_summary" .github/workflows alpha_engine ml_*
```

Additional grouping and artifact-age checks were run directly against the files above in the workspace shell.

## Asset Class Scorecard

| Asset Class | n | WR % | PF | PSR | Calmar | Max DD % | Cum Return % | Verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| EQUITY | 381 | 51.97 | 1.385 | 0.9944 | 3.2525 | -71.3697 | 232.1271 | Best-looking class, but still not world-class |
| CRYPTO | 1598 | 42.18 | 1.140 | 0.9685 | 1.1787 | -134.6799 | 158.7448 | Positive alpha, weak discipline |
| FOREX | 794 | 50.38 | 1.349 | 0.7592 | 0.7397 | -40.0515 | 29.6273 | Positive but mid-tier |
| ETF | 83 | 54.22 | 1.220 | 0.7719 | 0.4315 | -46.9382 | 20.2545 | Positive but too fragile |
| COMMODITY | 622 | 42.60 | 0.896 | 0.3266 | -0.2933 | -33.4891 | -9.8209 | Needs fixes now |
| BOND | 17 | 47.06 | 1.601 | 0.7136 | 0.9285 | -3.0629 | 2.8440 | Insufficient data |
| FUTURES | 2 | 100.00 | — | 0.0000 | 0.0000 | 0.0000 | 0.0010 | Insufficient data |
| UNKNOWN | 3 | 100.00 | — | 0.0000 | 0.0000 | 0.0000 | 0.2253 | Data-quality leak |

### What looks good

#### EQUITY

This is the healthiest asset class in the current book (`n=381`).

- `PSR 0.9944` is essentially at the repo's skill-verified bar.
- `Calmar 3.25` is the only clearly strong cross-asset risk-adjusted number.
- `PF 1.385` and positive cumulative return are real, not random noise.

What keeps it from world-class:

- `WR 51.97%` is still below the target `55-65%`.
- `Max DD -71.37%` is far outside any serious hedge-fund tolerance.

Verdict:

- **Looking good**
- **Needs risk-control hardening, not a full rewrite**

#### CRYPTO

Crypto (`n=1598`) is better than the older "crypto is hopeless" narrative, but it is still not hedge-fund quality.

- `cum_return_pct +158.7448`
- `PF 1.14`
- `PSR 0.9685`

What went wrong:

- `WR 42.18%` is too low.
- `Calmar 1.18` is mediocre.
- `Max DD -134.68%` is catastrophic by hedge-fund standards.

Verdict:

- **There is alpha here**
- **The implementation is too loose, too volatile, and over-exposed**

#### FOREX

Forex (`n=794`) is quietly positive but not impressive.

- `WR 50.38%`
- `PF 1.349`
- `cum_return_pct +29.6273`

What went wrong:

- `PSR 0.7592` is nowhere near skill-verified.
- `Calmar 0.7397` is too weak.
- `Max DD -40.05%` is still far too deep.

Verdict:

- **Promising enough to keep**
- **Not strong enough to trust without tighter routing and exits**

#### ETF

ETF (`n=83`) is positive but still weak as a hedge-fund candidate.

- `WR 54.22%` is the closest to the roadmap win-rate band.
- `PF 1.22` is acceptable, not elite.

What went wrong:

- `n=83` is still relatively small.
- `PSR 0.7719` and `Calmar 0.4315` are not convincing.
- `Max DD -46.94%` is too large.

Verdict:

- **Looking better than commodity**
- **Still a development-stage class, not a capital-allocation winner**

### What needs fixes

#### COMMODITY

Commodity (`n=622`) is the clearest problem class.

- `cum_return_pct -9.8209`
- `PF 0.896`
- negative Sharpe / Sortino / Calmar

This lines up with earlier repo findings:

- flat-close / resolver pathology in CTA-style strategies
- concentration in a narrow strategy family
- prior non-crypto pipeline issues

Verdict:

- **Needs fixes now**
- **Do not allocate like this class is healthy**

### What is not ready to judge

#### BOND / FUTURES / UNKNOWN

This bucket is too small to benchmark seriously:

- BOND: `n=17`
- FUTURES: `n=2`
- UNKNOWN: `n=3`

These rows are not enough to benchmark against a world-class fund. `UNKNOWN` is also a classification error bucket, not a real asset class.

Verdict:

- **Insufficient data**

## Where We Went Wrong

### 1. We are not allocating toward the cleanest classes

At read time during this audit, the active board was effectively **CRYPTO + COMMODITY only**, with no meaningful live representation from FOREX / ETF / BOND / FUTURES despite better or at least cleaner closed-book stats in several of those classes.

That is a routing problem.

The system is still spending most of its live attention on the noisiest classes instead of the best-behaved ones.

### 2. Drawdown control is not hedge-fund grade anywhere

Even the best class, EQUITY, had `Max DD -71.37%`.

That means the current system can produce positive cumulative return without being operationally investable. This is the classic "good gross edge, bad risk packaging" failure mode.

### 3. Commodity and CTA-style flows still look mechanically broken

This was already hinted in prior repo audits, and the current metrics do not contradict it. Commodity remains the weakest liquid class by combined return quality and risk-adjusted stats.

### 4. Data freshness is suspect

Both:

- `audit_trail/data/dashboard_payload.json`
- `audit_dashboard/data/dashboard_data.json`

were last written on `2026-04-27`, but their internal `generated_at` was still `2026-04-24T23:51:44.698614+00:00`.

That means the site may be republishing stale payloads. Any asset-class benchmarking built on stale snapshots can lag reality by multiple days.

### 5. We still leak bad bookkeeping states

The presence of `UNKNOWN` asset class rows means upstream classification is still imperfect. That pollutes per-class metrics and weakens any class-aware gating or allocation logic.

## Machine Learning Retraining Audit

| ML System | Evidence of Training Code | Evidence of Scheduled / Production Retrain | Artifact Freshness | Verdict |
|---|---|---|---|---|
| `ml_battleground` | Yes | Yes | Fresh | Best operational state |
| `ml_gatekeeper` | Yes | Yes | Stale-ish / persistence unclear | Wired, but artifact persistence likely broken |
| `alpha_engine/ml_ranker` | Yes | Partial | Stale | Train logic exists, production path unclear |
| `ml_crypto_predictor` | Yes | Weak | Stale | Stale / partially broken |
| `alpha_engine/meta_labeler` | Yes | Partial | Missing artifact | Unproven persistence |
| `ml_consensus` | No real learner | N/A | N/A | Rule-based scorer, not retrainable ML |

### 1. `ml_battleground` — healthiest ML stack

Evidence:

- `.github/workflows/ml-battleground-retrain.yml`
- scheduled daily retrain at `0 4 * * *`
- `ml_battleground/retrain_summary.json` present
- retrain summary shows:
  - `System A: success`
  - `System B: success`
  - `System C: success`

Verdict:

- **This is the only ML stack with clear, fresh retraining evidence**

### 2. `ml_gatekeeper` — real model, but refreshed weights may not persist

Evidence:

- training entrypoint exists in `ml_gatekeeper/gatekeeper.py`
- `audit-dashboard.yml` runs `python ml_gatekeeper/gatekeeper.py`
- local artifacts exist:
  - `ml_gatekeeper/models/training_report.json`
  - `ml_gatekeeper/models/gatekeeper_model.joblib`
- artifact age at audit time: about `293h`
- training report says:
  - `trained_at: 2026-04-15T17:19:24.783380+00:00`
  - `n_samples: 3500`
  - average walk-forward fold AUC about `0.615`
  - average walk-forward WR lift about `7.11pp`

Problem:

- the `audit-dashboard.yml` commit block stages payload files, but does **not** stage `ml_gatekeeper/models/`
- so the workflow can retrain in CI without persisting the new model to `main`

Verdict:

- **Model is useful**
- **Retraining persistence is likely broken**

### 3. `alpha_engine/ml_ranker` — good code, weak operational guarantee

Evidence:

- training code exists in `alpha_engine/ml_ranker.py`
- `smart_train()` supports:
  - full retrain on drift or large sample delta
  - incremental retrain on 5-100 new picks
- model artifact exists:
  - `alpha_engine/data/rf_model.pkl`
- artifact age at audit time: about `295h`

Important nuance:

- `alpha_engine/scanner.py` does contain an auto-retrain path if the model is older than `24h`
- but the main production workflow's full cycle runs `alpha_engine/production_scanner.py`, not `scanner.py --train-ml`
- the explicit workflow training step only runs when mode is manually set to `train-ml`

Verdict:

- **The retrain logic exists**
- **It is not obvious that the standard production path is exercising it consistently**
- **Operationally, this model looks stale**

### 4. `ml_crypto_predictor` — stale and partially broken

Evidence:

- training scripts exist:
  - `train_base_models.py`
  - `train_ensemble.py`
  - `train_scalping_models.py`
  - `train_swing_models.py`
- summary exists:
  - `ml_crypto_predictor/enhanced_models/results/training_summary.json`
- summary timestamp:
  - `trained_at: 2026-03-26T16:22:23.888149+00:00`
- artifact age at audit time: about `718h`

Concrete bug:

- `ml_crypto_predictor/self_improvement.py` reads `results/v4_training_summary.json`
- that file is missing in the current repo snapshot
- current summary lives under `enhanced_models/results/training_summary.json`

Verdict:

- **This stack is stale**
- **Its self-improvement path appears broken by a path mismatch**
- **I see no convincing evidence of current automatic retraining**

### 5. `alpha_engine/meta_labeler` — code present, artifact missing

Evidence:

- train/save/load logic exists in `alpha_engine/meta_labeler.py`
- workflows reference it:
  - `.github/workflows/regime-detector.yml`
  - `.github/workflows/worldclass-pipeline.yml`
- expected artifact:
  - `alpha_engine/meta_labeler_model.pkl`
- current repo snapshot:
  - artifact missing

Verdict:

- **Training code exists**
- **Persistence is not proven in the current repo snapshot**

### 6. `ml_consensus` — not actually a retrainable model

`ml_consensus/consensus.py` is a historical-agreement scorer with hard-coded quality weights and backtest logic, but no real fit/save/load training loop.

Verdict:

- **Do not treat this as a retraining failure**
- **It is a rules engine dressed as ML**

## What Needs Fixes vs What Looks Good

### Looking good

1. **EQUITY**
   - Keep
   - Prioritize for cleaner capital deployment
   - Needs drawdown reduction, not wholesale replacement
2. **FOREX**
   - Keep
   - Improve exits and class-aware routing
3. **ETF**
   - Keep in development
   - Needs more sample and tighter DD control

### Mixed / harden

1. **CRYPTO**
   - Keep
   - This is not "broken alpha"
   - It is "badly packaged alpha"
   - Fix risk, concentration, and class-specific allocation

### Needs fixes now

1. **COMMODITY**
   - Audit CTA / momentum resolver path again
   - Reduce live emphasis until PF > 1 and DD stabilizes
2. **ML retraining persistence**
   - Especially `ml_gatekeeper`
3. **`ml_crypto_predictor` self-improvement path**
   - Fix the broken summary-file reference
4. **Payload freshness**
   - Stop republishing stale JSONs
5. **UNKNOWN asset class leakage**
   - Fix at source before downstream class analytics

### Insufficient data

1. **BOND**
2. **FUTURES**

Do not claim world-class or even stable class-level edge here yet.

## Recommended Fix Order

### P0

1. Fix stale dashboard payload publishing so `generated_at` matches real regeneration time.
2. Fix `ml_gatekeeper` persistence by staging `ml_gatekeeper/models/` in the workflow commit path or moving it to a dedicated retrain workflow.
3. Fix `ml_crypto_predictor/self_improvement.py` to read the actual summary path and add a real retrain workflow if the project still intends to use that stack.

### P1

1. Re-route class exposure toward EQUITY / FOREX / ETF and away from COMMODITY when class metrics are worse.
2. Add class-aware drawdown caps. Right now every class fails the hedge-fund DD test.
3. Reduce crypto concentration unless the risk-adjusted metrics improve materially.

### P2

1. Re-audit commodity strategy families for resolver / flat-close pathology.
2. Remove or repair `UNKNOWN` asset-class rows upstream.
3. Prove whether `alpha_engine` ranker retraining is actually happening in the production full-cycle path. If not, wire it explicitly.

## Bottom Line

If the question is:

> Which asset classes are closest to a world-class hedge fund?

The answer is:

1. **EQUITY**
2. **FOREX**
3. **ETF**
4. **CRYPTO**
5. **COMMODITY**

If the question is:

> Which asset classes need the most fixing?

The answer is:

1. **COMMODITY**
2. **CRYPTO risk packaging**
3. **BOND / FUTURES data coverage**

If the question is:

> Are our ML algorithms being retrained?

The answer is:

- **`ml_battleground`: yes**
- **`ml_gatekeeper`: retrain runs, persistence likely broken**
- **`alpha_engine/ml_ranker`: stale artifact, production retrain path unclear**
- **`ml_crypto_predictor`: stale and likely broken**
- **`alpha_engine/meta_labeler`: code exists, persisted artifact missing**
