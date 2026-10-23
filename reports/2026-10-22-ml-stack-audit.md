# ML Stack Audit — 2026-10-22

**Author:** ML-systems audit subagent
**Scope:** Assessment of all ML/machine-learning algorithms in the trading codebase — validated & leverageable ("true winners") vs research-only/broken/stale.
**Constraint honored:** no production code modified; report-only.
**Filesystem evidence:** mtimes, git log, and artifact contents cited inline (relative paths, per repo root).

---

## 1. Executive Summary

The codebase contains **11 distinct ML modules** (plus the meta-model scorer and an ML-enrichment layer in the audit dashboard). Only **two systems show forward, statistically-grounded edge evidence** with artifacts present on disk today:

| Rank | Module | Verdict | Hard evidence |
|------|--------|---------|---------------|
| 1 | `ml_gatekeeper/` | **VALIDATED-LEVERAGEABLE** | 12-fold walk-forward mean lift **+4.31pp** (bootstrap 95% CI [2.68, 5.83], p=0.0004); true holdout (n=500) passed-WR **60.82% vs baseline 52.4% (+8.42pp)**, PF **2.206**. Fresh models (`.joblib`) trained **2026-10-22** on real closed trades. |
| 2 | `ml_consensus/` | **VALIDATED-LEVERAGEABLE** (n modest) | Consensus-WR **56.46% vs single-pick 45.75% (+10.71pp)** on real closed picks (n=147 consensus). Report generated **2026-10-22**. |
| 3 | `ml_enhanced_*` family (via alpha-engine / ML-reviver ledger) | **PROMISING-NEEDS-VALIDATION** (per-strategy) | Forward MC-edge audit shows specific combos with PF CIs entirely above 1.0 (e.g. `ml_enhanced_DYDXUSDT_15m_D_ensemble_stack` LONG PF=10.36, CI [3.18, ∞]; `ml_enhanced_INJUSDT_1d_B_lightgbm` LONG PF=35.6, CI [9.64, ∞]). Whole family is mixed — most combos are DESTROYERs. |
| 4 | Meta-model scorer (`audit_dashboard/data/meta_model_weights.json` + `meta_model_scorer.js`) | **STALE** | ROC AUC 0.7358 but trained **2026-03-16** (~7 mo). `ml_enhanced_ag_picks.json` = `[]` (producing nothing). |

**The ML layer, where validated, does improve expectancy** — it is not uniform across modules (see §6). The largest *proven* lift is the Gatekeeper's per-pick filter (+8.4pp WR, PF 2.2 on holdout) and the consensus selector (+10.7pp WR).

---

## 2. Inventory & Div Status

| Module | What it does | Wired into prod/dashboard? | Model artifacts present? | Validation/backtest output? |
|--------|--------------|----------------------------|--------------------------|------------------------------|
| `ml_consensus/` | Builds multi-system consensus picks (reads `audit_dashboard/data/dashboard_data.json`); writes `data/active_picks.json` + `closed_picks.json`. | Dashboard reads both files (`audit_trail/dashboard_generator.py` lines 4091-4094); **files are currently empty/missing**, so feed is dormant until consensus writer populates them. | `models/consensus_report.json` (fresh). | Backtest in report: +10.71pp WR lift. |
| `ml_gatekeeper/` | Per-pick quality gatekeeper (classifier); A/B two-sleeve (old/new) router; drift baseline. | Dashboard declares `data/active_picks.json`+`closed_picks.json` (lines 4086-4089) — **files do not exist yet**; A/B `ab_summary.json` = `INSUFFICIENT_DATA` (OLD=0, NEW=0). Not yet emitting tagged live picks. | `models/gatekeeper_new.joblib` (3.0 MB), `gatekeeper_old.joblib` (3.0 MB), `strategy_router.json`, `drift_baseline.json`, `training_report.json` — all 2026-10-22 21:57. | JSON 12-fold walk-forward + true holdout (below). |
| `ml_crypto_predictor/` | Crypto direction models (GB/RF, ensemble, scalping/swing, v2/v4/v5). | Dashboard consumes `enhanced_models/live_picks/active_picks.json` (lines 3806-3808, 3937-3939) and `all_picks_log.json`; also source of many `ml_enhanced_*` picks in ledger. | v5 `results/training_summary.json` fresh (2026-10-22) but **`total_models: 0`** (training ran, produced 0 models). Legacy `models/*.pkl` reference `/home/runner/...` CI paths. | Legacy `models/training_results.json` F1 0.1-0.27 (weak). v5 produced nothing. |
| `crypto_ml_edge/` | Per-pair edge models (1h/4h, 10 pairs), stationarity + DSR validation, SHAP. | Dashboard reads `data/active_picks.json` (line 3748) — last updated **2026-05-31** (stale ~5 mo). | **No `.joblib` present** under `models/` (only `*_edge_meta.json`); training report references `E:\...` Windows paths that do not exist on this host. | `results/training_report.json` (2026-02-25) reports absurd net-Sharpe ~40, DSR prob 1.0 → overfit artifact, no forward proof. |
| `ml_battleground/` | Arena of 6 systems (A filter, B regime, C deeplearn, D carry, E momentum, F clawsofdoom) + ensemble + bootstrap + ABC forward test. | Dashboard ingests systems A-F, ensemble, ABC (`dashboard_generator.py` lines 3692-3726, 3814-3826); freshness cap 72h. | `system_c_deeplearn/models/arch_config.json`; `retrain_summary.json` fresh (2026-10-22 04:16) all success; `baseline_metrics.json` (2026-10-18): **WR 28.3%, PF 0.426, Sharpe −0.069**. | No per-system edge/CI proof; baseline itself losing. |
| `crypto_gainer_ml/` | Live gainer-predictor with feedback loop, scorecard, learned weights. | Dashboard reads scorecard/performance (`claude_gainer_ml_perf` handler, line 9458). | `tracker/learned_weights.json`, `performance_summary.json` (fresh 2026-10-22 21:17). | Scorecard (n=143): WR **32.2%**, PF **0.63**, total PnL **−205.9%**, avg −1.44%/pick → **negative expectancy**. |
| `claude_gainer_ml/` | Gainer ML (RF+XGB) with self-improve, token sniffer, live/short-term scanner. | Dashboard `claude_gainer_ml_perf` reads its closed-pick correlations (line 9459). | `models/training_meta.json` (2026-05-25). | metrics: precision/recall/F1 = **0.0**, ROC-AUC 0.688, PR-AUC **0.0646** (threshold 0.75 → zero recall). Essentially no usable discriminative power. |
| `ml_battleground/` (ensemble/agreement) | Agreement-alpha + ensemble coordination across systems. | Dashboard `agreement_alpha` source (lines 3922-3925). | `ensemble_data/` files. | No validated edge numbers. |
| `local_gpu_trainer/` | GRU crypto direction predictor for Alpha Engine. | Not referenced in dashboard source list (no JSON_PICK_SOURCES entry). | `models/` **contains only `__init__.py`** (no weights). | `train_gru.py` imports torch, usage `py -3.14` (Windows-specific), no artifacts → not runnable/leveraged here. |
| `meta_model_scorer.js` + `meta_model_weights.json` | Logistic meta-model scoring pick win-prob (grading A-F). | `audit_dashboard/data/` artifacts; consumer is meta-scorer path (leak-free, excludes LivePnL). | Weights + JS present. | AUC 0.7358 (2026-03-16). Many feature coeffs =0.0 with mean 0/std 1 (failed standardization/dropout) → partially depopulated. `ml_enhanced_ag_picks.json` = `[]` → not emitting. |
| `ml_gatekeeper_ab_decision.json` | A/B verdict for gatekeeper two-sleeve. | Audit dashboard consumes it (report freshness registry references it). | Present (2026-10-22 20:32). | **PENDING** — OLD=0, NEW=0 sleeves; no A/B edge measured yet. |

---

## 3. State (Freshness / Broken / Research)

| Module | Last meaningful update | State |
|--------|------------------------|-------|
| `ml_gatekeeper/` | 2026-10-22 21:57 (models) | **Active & fresh** (validated; A/B not yet sampled) |
| `ml_consensus/` | 2026-10-22 20:34 (report) | **Fresh report, dormant feed** (output pick files empty) |
| `ml_crypto_predictor/` | 2026-10-22 20:30 (v5) | **Broken** — `total_models:0`; legacy artifacts CI-path-bound |
| `crypto_ml_edge/` | 2026-05-31 (active picks); 2026-02-25 (training) | **Stale + broken** (no joblib; Windows paths) |
| `ml_battleground/` | 2026-10-22 04:16 (retrain) | **Active but unproven** (baseline losing) |
| `crypto_gainer_ml/` | 2026-10-22 21:17 (scorecard) | **Active, negative edge** |
| `claude_gainer_ml/` | 2026-05-25 (training_meta) | **Stale**, weak F1 |
| `local_gpu_trainer/` | 2026-05-25 | **Broken/research-only** (no weights) |
| Meta-model | 2026-03-16 | **Stale**, not emitting |
| A/B decision | 2026-10-22 | **Pending/no samples** |

**Broken/unsatisfied dependencies/errors observed**
- `crypto_ml_edge/models/*` training report records `model_path: E:\findtorontoevents_antigravity.ca\crypto_ml_edge\models\*.joblib` (Windows drive) and no `.joblib` exists on this host → cannot load/run.
- `ml_crypto_predictor/models/*.pkl` reference `/home/runner/work/...` GitHub-Actions CI paths → not resolvable locally.
- `ml_crypto_predictor` v5 `enhanced_models` trained 10 pairs × 3 timeframes in 22.5s and produced **0 models** (pipeline regressed/empty).
- `local_gpu_trainer/train_gru.py` runs only under `py -3.14` (Windows) + torch; no exported weights → GPU "trainer" currently non-functional on this host.

---

## 4. Does the ML layer improve win-rate / expectancy vs baseline? (evidence)

### 4.1 `ml_gatekeeper` — the strongest validated ML edge
Source: `ml_gatekeeper/models/training_report.json` (2026-10-22).

- Training set: 3,500 real closed outcomes, 32 features, base WR 44.91%. Data is REAL closed trades (no synthetic).
- **12-fold walk-forward** (12 folds, rolling train / 230 test each):
  - mean WR lift **+4.31pp**;
  - bootstrap 95% CI **[+2.68, +5.83]** pp;
  - t = 5.081, p = 0.0004 → **statistically significant**;
  - AUC per fold ranges 0.37-0.70 (mid-fold) but positive-lift folds dominate; the aggregate test is decisive.
- **True holdout** (n=500, never seen in training):
  - baseline WR 52.4% → **passed WR 60.82%** (lift **+8.42pp**), rejected WR 37.57% (i.e. the model cleanly separates);
  - passed cumulative PnL +304.62 vs rejected +5.27; **PF 2.206**;
  - by asset class: CRYPTO +23.82pp lift (n=153 passed), FOREX +38.1pp, EQUITY +13.7pp.
- Top features: `strat_fwd_wr`, `age_hours`, `forward_wr`, `ml_composite_score`, `strat_fwd_pf` — i.e. it is re-ranking on proven forward stats + freshness.

**Verdict:** The gatekeeper filter genuinely improves win-rate and profit factor on out-of-sample holdout. This is the clearest "proven edge" ML in the repo.

### 4.2 `ml_consensus` — validated lift, modest n
Source: `ml_consensus/models/consensus_report.json` (2026-10-22).

- Consensus picks n=147 → WR **56.46%**, cumulative PnL +233.82.
- Single picks n=2,988 → WR **45.75%**, cumulative PnL +646.85.
- **WR lift = +10.71pp** (directional + per-group mean). Data source: real closed picks + live active picks (no synthetic).
- Caveat: n=147 is moderate; report does not publish a CI. Still materially above the 45.75% base.

### 4.3 Meta-model (stale)
Source: `audit_dashboard/data/meta_model_weights.json` — ROC AUC 0.7358 (logistic) / 0.734 (GBM), optimal threshold 0.517, trained 2026-03-16.
- No forward/backtest PnL evidence; `ml_enhanced_ag_picks.json` = `[]` → it is not currently generating/leveraged picks.

### 4.4 `ml_enhanced_*` family — per-strategy forward evidence
Source: `audit_dashboard/data/mc_edge_audit_fresh.json` (generated 2026-05-31, bootstrap n=10,000, min_n=20, per-combo).

- **Genuine edge (CI entirely above 1.0):**
  | strategy | dir | n | WR | PF | PF 95% CI |
  |---|---|---|---|---|---|
  | `ml_enhanced_INJUSDT_1d_B_lightgbm` | LONG | 26 | 92.3% | **35.6** | [9.64, ∞] |
  | `ml_enhanced_DYDXUSDT_15m_D_ensemble_stack` | LONG | 34 | 94.1% | **10.36** | [3.18, ∞] |
  | `ml_enhanced_FETUSDT_1d_B_lightgbm` | LONG | 29 | 48.3% | **6.02** | [2.04, 16.7] |
  | `ml_enhanced_RENDERUSDT_1h_D_ensemble_stack` | LONG | 39 | 64.1% | **4.34** | [1.61, 11.9] |
  | `ml_enhanced_RENDERUSDT_4h_D_ensemble_stack` | LONG | 34 | 58.8% | 2.33 | [0.93, 6.3] |
- **But the family is heterogeneous:** of the 22 `ml_enhanced_*` combos evaluated, 10 are PROFITABLE/TIER-1/2 and 12 are DESTROYER (PF 0.004-0.73). Several destroyers are the *short-side* or different-asset variants of the same ML family (e.g. `ml_enhanced_APEUSDT_1d_D_ensemble_stack` SHORT PF=0.06, n=25; `ml_enhanced_TRXUSDT_1d_B_lightgbm` LONG PF=0.004, n=26).
- No `ml_enhanced_*.py` generator files exist anywhere in the repo today (0 matches) → this is a **historical/ledger family**, not a live regenerating system; the audit dashboard groups it as `ml_enhanced_group` for aggregate stats.

### 4.5 Modules with NEGATIVE / unproven edge (do not leverage)
- `crypto_gainer_ml/tracker/performance_summary.json` — WR 32.2%, **PF 0.63**, total PnL **−205.9%**.
- `claude_gainer_ml/models/training_meta.json` — F1 =0.0, PR-AUC 0.0646.
- `ml_crypto_predictor` legacy — F1 0.1-0.27; v5 produced 0 models.
- `ml_battleground/baseline_metrics.json` — WR 28.3%, PF 0.426, Sharpe −0.069.
- `crypto_ml_edge` — no runnable artifacts; reported metrics are overfit backtest artifacts (net-Sharpe ~40, DSR=1.0) with no forward/CI proof.

---

## 5. Per-Module Verdicts

| Module | Verdict | One-line justification |
|--------|---------|------------------------|
| `ml_gatekeeper/` | **VALIDATED-LEVERAGEABLE** | Holdout +8.42pp WR, PF 2.206, p=0.0004; fresh models present. |
| `ml_consensus/` | **VALIDATED-LEVERAGEABLE** (n modest) | +10.71pp WR lift vs single; real data; fresh report. Feed output files currently dormant. |
| `ml_enhanced_*` (top combos) | **PROMISING-NEEDS-VALIDATION** | 4-5 combos with PF CIs >1.0; family mixed; no live generator. |
| `ml_enhanced_*` (other combos) | **RESEARCH-ONLY / DESTROYER** | 12/22 combos PF<1.0; should be excluded. |
| Meta-model (`meta_model_*.json/js`) | **STALE** | Trained 2026-03-16; not emitting (`ml_enhanced_ag_picks.json`=[]). |
| `ml_gatekeeper_ab_decision.json` | **PENDING (no A/B data)** | OLD=0, NEW=0 sleeves. |
| `ml_crypto_predictor/` | **BROKEN** | v5 total_models=0; legacy artifacts CI-path-bound; weak F1. |
| `crypto_ml_edge/` | **BROKEN/STALE** | No joblib; Windows paths; overfit validation numbers. |
| `local_gpu_trainer/` | **BROKEN/RESEARCH-ONLY** | No weights; Windows-only launcher; not in dashboard. |
| `ml_battleground/` | **RESEARCH-ONLY** | Active retrains but baseline PF<0.5; no per-system edge CI. |
| `crypto_gainer_ml/` | **STALE/NEGATIVE-EDGE (not leverageable)** | PF 0.63, −205.9% PnL. |
| `claude_gainer_ml/` | **STALE/NOT-USABLE** | F1=0, PR-AUC 0.065. |

---

## 6. Recommendations

### Leverage right now (true-winner candidates)
1. **Promote `ml_gatekeeper` into an active pick-gating stage.** It has the strongest evidence (holdout PF 2.2, +8.4pp WR). Today it is validated but not emitting live `active_picks.json`/`closed_picks.json` and its A/B has zero samples. Work items:
   - Persist gatekeeper output picks (`ml_gatekeeper/data/active_picks.json`, `closed_picks.json`) so the dashboard source listed in `dashboard_generator.py` (lines 4086-4089) begins consuming them.
   - Enable/retain the two-sleeve A/B tagging so `ml_gatekeeper_ab_decision.json` accumulates ≥30/sleeve and produces a real verdict (currently PENDING).
   - Apply the trained gate as a **filter on top of already-profitable base strategies** (esp. CRYPTO/EQUITY where holdout lift was +23.8pp/+13.7pp).
2. **Operationalize `ml_consensus` output.** The +10.71pp lift is worth taking; the report reads `dashboard_data.json` but writes empty output files. Wire the consensus writer to populate `ml_consensus/data/active_picks.json` (freshness cap already 72h) and let the dashboard resolve it. Consider enforcing direction-aware consensus (long/short) as the report implies.
3. **Selectively re-surface the proven `ml_enhanced_*` ledger combos** (the 4-5 with PF CIs above 1.0): `INJUSDT_1d_B_lightgbm` LONG, `DYDXUSDT_15m_D_ensemble_stack` LONG, `FETUSDT_1d_B_lightgbm` LONG, `RENDERUSDT_1h_D_ensemble_stack` LONG, `RENDERUSDT_4h_D_ensemble_stack` LONG. Do **not** promote the family broadly — quarantine/exclude the 12 destroyers (including all short-side variants that lose). Any promotion must regenerate from a real live generator (none exists today).

### Activation steps for promising-but-unproven
4. **`meta_model`:** retrain on current data (weights are 7 months old; many coeffs zeroed). Only re-enable once `ml_enhanced_ag_picks.json` produces non-empty output and a holdout AUC/PnL is re-derived. Gate any re-activation on the existing `_SIDECAR_PROMOTION_GATES`-style n/WR/PF thresholds.
5. **A/B discipline:** until `ml_gatekeeper_ab_decision.json` collects ≥30 per sleeve, treat both sleeves as experimental; keep real-money sizing gated (the file itself states "Real-money sizing remains gated on the 10-step AFML readiness pipeline regardless of A/B outcome").

### Retire / do-not-leverage
6. **Retire** `crypto_gainer_ml` (PF 0.63), `claude_gainer_ml` (F1=0), and negative-edge `ml_enhanced_*` combos from any "winners" promotion.
7. **Do not build on** `crypto_ml_edge` (missing joblib, Windows paths, overfit claims), `local_gpu_trainer` (no weights, Windows-only), or `ml_crypto_predictor` v5 until its `total_models:0` regression is fixed and validated — currently broken.

### Governance/hygiene
8. Add CI-gated evidence for any ML promotion: require a true holdout (as `ml_gatekeeper` already does) with reported WR-lift, PF, and CI before any system is promoted to "winners".
9. Treat `ml_battleground` as an experiment sandbox until a system demonstrates PF CI >1.0 on ≥30 forward closed picks (currently baseline PF 0.426).

---

## 7. Evidence file index
- `ml_gatekeeper/models/training_report.json` — §4.1 (holdout + walk-forward stats).
- `ml_gatekeeper/models/gatekeeper_new.joblib`, `gatekeeper_old.joblib` — trained artifacts (2026-10-22).
- `ml_gatekeeper/data/ab_summary.json`, `audit_dashboard/data/ml_gatekeeper_ab_decision.json` — A/B insufficient-data (OLD=0, NEW=0).
- `ml_consensus/models/consensus_report.json` — §4.2 (consensus vs single lift).
- `audit_dashboard/data/meta_model_weights.json`, `meta_model_scorer.js`, `ml_enhanced_ag_picks.json` — §4.3 (stale; empty output).
- `audit_dashboard/data/mc_edge_audit_fresh.json` — §4.4 (per-combo PF CIs for `ml_enhanced_*`).
- `crypto_gainer_ml/tracker/performance_summary.json` — §4.5 (PF 0.63).
- `claude_gainer_ml/models/training_meta.json` — F1=0.
- `ml_crypto_predictor/enhanced_models/results/training_summary.json` — v5 `total_models:0`.
- `ml_crypto_predictor/models/training_results.json` — legacy weak F1.
- `crypto_ml_edge/results/training_report.json` — overfit / Windows paths.
- `ml_battleground/baseline_metrics.json`, `retrain_summary.json` — PF 0.426 / active retrains.
- `audit_trail/dashboard_generator.py` — wiring lines cited in §2 (JSON_PICK_SOURCES, ML enrichment, freshness caps 72h).

*Not financial advice. Research/educational only. Past performance does not guarantee future results.*
