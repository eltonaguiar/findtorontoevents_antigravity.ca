# ML Algorithms Usage Audit — 2026-06-12

**Scope:** every machine-learning algorithm/model in the repo — wired vs active vs stale/orphaned.
**Method:** READ-ONLY. Repo-wide import greps (`sklearn|lightgbm|xgboost|torch|catboost`), caller-graph greps per the Wire-Up Rule, model-artifact mtimes (main tree + `origin/main` git evidence), `.github/workflows/` crons + `gh run list` freshness, and live MySQL SELECTs against `ejaguiar1_stocks` (`trading_picks`, `at_signal_outcomes`) including the honest **intrabar** slices (`intrabar_status` ∈ TP_HIT/SL_HIT/TIME_EXIT, SL-wins-ties). No edits, commits, or DB writes. Worktree copies (`.worktrees/`) excluded.

**Honest-performance convention:** "WR-ib / PF-ib" = intrabar first-touch replay numbers; nominal WR/PF from `outcome`/`pnl_pct` are known-inflated (snapshot-resolver artifact, see memory `project-ai-tournament-wr-artifact-2026-06-03`).

**Context:** the audit-wide honest baseline (`audit_dashboard/data/intrabar_truth_by_class.json`, 2026-06-10) is CRYPTO 32.4% WR / PF 0.73 (n=1154), EQUITY 34.6% / 0.47 (n=107) — i.e., **everything** is under water; ML systems are judged against that.

---

## 1. Ranked inventory (worst offenders first)

| # | System | What it is | Wired? | Active? | Honest perf (intrabar unless noted) | VERDICT |
|---|--------|-----------|--------|---------|--------------------------------------|---------|
| 1 | **kimi_riseoftheclaw ingestion** (`audit_trail/backfill_local_sources.py:424,449-450` ← `outcome-resolver.yml:165`) | TA "claw" signals + RandomForest ranker (`KIMI_RISEOFTHECLAW/ml_signal_ranker.py:77,341`) | YES | YES (hourly) | nominal 28.4% WR / PF 0.69 on 141,388 rows; **140,120 rows written in last 7d, only 866 distinct (99.4% duplicates)**; all `strategy='unknown'`, `opened_at/closed_at NULL` | **ACTIVE-HARMFUL (data layer)** |
| 2 | **ml_strategy_reviver** (`alpha_engine/ml_strategy_reviver.py:863`) | Bridges ml_crypto_predictor picks + RSI/EMA fallback for 13 "proven" `ml_enhanced_*` strategies | YES (`ml-strategy-reviver.yml` every 2h, green) | YES — 53 picks/7d, last 2026-06-12 06:01 | **WR-ib 32.0% / PF-ib 0.83 (n=470)** | **ACTIVE-HARMFUL** |
| 3 | **ml_strategy_reviver_inverse** (`ml_strategy_reviver.py:941`, 4 INVERSE_STRATEGIES) | Literal direction-flip arm of #2 | YES | YES — 23 picks/7d | **WR-ib 34.3% / PF-ib 0.69 (n=221)** — *both* arms lose ⇒ costs/SL-geometry dominate, not direction | **ACTIVE-HARMFUL** |
| 4 | **ml_crypto_predictor** ("Antigravity ML v3.1", 1,746 joblibs: XGB+LGBM+RF+stackers per symbol×TF) | 48h direction + TP/SL, regime + F&G features | YES (`enhanced-ml-crypto.yml` daily train + 2h predict; bridge at line 158 → ml_strategy_reviver; `ml-forward-test.yml` 4h) | YES — 145 picks/7d, biggest live ML emitter | **WR-ib 40.5% / PF-ib 1.07 (n=1805)** — gross ≈ breakeven, net negative after fees. `ml_enhanced_*` family (3,295 picks; 198/7d): trimmed PF-ib 1.07 / WR 39.3 (n=3016) | **ACTIVE-MARGINAL→HARMFUL net** |
| 5 | **ml_gatekeeper A/B router** | GB+RF ensemble (60/40) + isotonic calibration predicting pick win-prob; OLD/NEW leakage A/B | PARTIAL | Trains daily (`ml-gatekeeper-train-ab.yml` 19:12 UTC, green; bundles ON origin/main: commits `f7e038d6ed`/`5bcfabe289`) but **n_ab_tagged=0** (ab_summary.json 2026-06-11) | n/a — never routed a measured pick | **WIRED-BUT-NOT-ROUTING** |
| 6 | **regime_terminal** (GaussianHMM 7-state, `regime_terminal/hmm_engine.py`) | Per-symbol regime classification → signals | YES (`regime-terminal.yml` every 30min; normalized in `alpha_engine/isolated_signal_integrator.py:84,475`) | YES — 93 picks/7d | WR-ib 22.7% / PF-ib 0.85 — **small n=23**, watch | **ACTIVE-SUSPECT (small-n bad)** |
| 7 | **ml-model-autotraining.yml** (every 6h) | Trains "Consensus/Quality/Risk" models into `signal_aggregator/models/`, `forward_testing/models/`, `risk_management/models/` | **NO** — none of those dirs exist in the repo; outputs only 30-day CI artifacts; zero consumers found | Cron green (2026-06-12 01:23) | n/a | **ZOMBIE WORKFLOW (CI waste)** |
| 8 | **ml_battleground A/B/C/ensemble** (XGB filter, XGB regime, PyTorch GRU) | Signal filter / regime / deep-learn arms | Emission RETIRED (workflows `.retired`) — but `ml-battleground-retrain.yml` **still retrains A/B/C daily 04:00** (`retrain_on_live.py:37-47`), green 2026-06-12 | Last picks Mar 2026 | Catastrophic: system_a 5.6% WR (n=18), system_b 5.3% (n=19, PF 0.02), system_c & ensemble 0% | **DEAD-BUT-RETRAINING (CI waste)** |
| 9 | **ml_battleground system_f_clawsofdoom** | Hourly sync of external CLAWSOFDOOM repo (NOT local ML) — `ml-battleground-f.yml:33-46` | YES | YES (hourly :47) | **25,669 rows in at_signal_outcomes, 0 resolved (no WON/LOST)** | **ACTIVE-UNMEASURED + row bloat** |
| 10 | **mercury2** (3× XGBoost ensemble joblibs) | Crypto LONG/SHORT/HOLD for 34 pairs | YES (`mercury2-scan.yml` hourly + weekly retrain, green) | **No trading_picks since 2026-03-28**; `mercury2/data/last_scan_state.json` mtime 2026-05-29 | at_signal_outcomes: PF-ib 1.04 (n=437); trading_picks slice WR-ib 25.3 / PF-ib 0.65 (n=79) | **WIRED-BUT-DORMANT** |
| 11 | **claude_gainer_ml** (claude_rf/xgb/scaler.joblib, 2026-06-03) | Pump-probability top-gainer scanner | YES (`claude-gainer-ml-live.yml` every 30min, green; hard `sys.exit(1)` if models missing — live_scanner.py:185-205) | Runs but ~0 active picks; DB source `claude_gainer_st` dead since 2026-03-28 (10 rows ever — the disputed 78.9% smart-picks concentration source) | unmeasurable live; JSON tracker only (1 active / 31 resolved) | **WIRED-LOW-OUTPUT** |
| 12 | **crypto_signal_engine** ("SignalEngine": 3× XGB cls + LGBM reg) | Next-day top-gainer day-trades | YES (`signal-engine.yml` every 30min + daily retrain, green) | "0 active picks" in latest runs; models last trained 2026-05-25 (17d, despite daily retrain cron) | unmeasured recently | **WIRED-LOW-OUTPUT / STALE MODELS** |
| 13 | **skyrocket_detector** (LightGBM w/ sklearn fallback) | Pump/skyrocket binary classifier | YES (`skyrocket-detector.yml` hourly, green) | **1 pick in 30d**; model joblib 2026-05-29 (14d), no retrain workflow | n/a | **WIRED-DORMANT** |
| 14 | **meta_strategy meta-learner** (XGB/LGBM `meta_learner.joblib` 2026-06-10) | Ranks winning strategy-combo permutations; feeds genome | YES (`meta-strategy.yml` 15min/6h, green; feeds `evolved_genomes.json`) | YES — artifacts fresh | not pick-emitting directly | **ACTIVE-USEFUL (plumbing)**; note `meta_label_model.joblib` frozen since init (2026-05-25) |
| 15 | **parallel_agent quick_guess** (sklearn GradientBoosting, 57 sym × 8 horizons) | UP/DOWN probability grid | Workflow only (`quick-guess-ml.yml` hourly, green); **no DB writes, no downstream consumer found**; `guess_models.pkl` mtime 2026-06-02 | runs hourly | n/a | **ACTIVE-ISOLATED (CI cost, no sink)** |
| 16 | **genome family** (GA + NEAT + rule mutations — hybrid, no sklearn joblibs in genome/data) | Strategy evolution; emits `genome`, `genome_mutations`, `genome_mutation_lab` via `isolated_signal_integrator.py` | YES (`genome-daily-pipeline.yml` every 3h, green) | YES — 17+10+3 picks/7d | genome **PF-ib 0.66** (n=107, bad); genome_mutations PF-ib 1.09 (n=92); **genome_mutation_lab WR-ib 73.7 / PF-ib 4.43 (n=57)** ← only positive honest ML-adjacent slice, still sub-100-n | **MIXED: kill `genome`, watch `genome_mutation_lab`** |
| 17 | **KIMI_FEB172026** (`ml_signal_ranker.py` RF+GB, wired at `live_scanner.py:16,40`) | Signal win-prob ranking (24 features) | YES (`kimi-feb172026-live.yml` 2-4h, green) | YES (internal JSON; no clean DB source_system) | unmeasured in DB | **ACTIVE-UNMEASURED** |
| 18 | **ml_consensus** (`consensus.py`, combination-learning over closed picks) | Multi-system agreement grading | YES (`audit-dashboard.yml`, continue-on-error) | Report 2026-05-22 (21d stale); 0 active consensus groups; **backtested lift −0.02 WR** | negative lift | **WIRED-DORMANT, no edge** |
| 19 | **ML health gate** (`alpha_engine/ml_health_monitor.py` → `data/ml_health_status.json`) | Halts ML position sizing on feature/freshness failure | YES (`production_scanner.py:2867-2870`) | Current state: `ml_trading_enabled=false`, health 0.06, predictions 906-min stale → **HALT** | n/a | **ACTIVE-USEFUL (and currently halting the ML stack)** |
| 20 | **ml_gatekeeper per-class shadow** (`per_class_trainer.predict_quality`) | Per-class quality score, shadow | YES — `audit_trail/quality_gates.py:97`, `alpha_engine/smart_picks_engine.py:1489` (PER_CLASS_ML_SHADOW=1, ENFORCE off) | shadow only | n/a | **WIRED-SHADOW** |
| 21 | **hierarchical-bayes** (PyMC Sharpe validation, `alpha_engine/validation/hierarchical_sharpe`) | Bayesian strategy-Sharpe validation, 4 hardcoded strategies | Workflow daily 02:30 | runs; **no persisted output, no downstream consumer** | n/a | **WIRED-DORMANT** |
| 22 | **Orphaned code (no callers, no workflows)** | `alpha_engine/ml_engine_v2.py` (+ `data/rf_model.pkl`, `ml_challenger.joblib`, May 25), `l1_logistic_hft.py`, `ppo_micro_strategy.py` (rl-agent-ppo.yml.retired), root `crypto_fusion_predictor.py` / `ml_ranker_fixed.py` / `multi_symbol_crypto_beater.py`, `scripts/{ensemble_stacker,gnn_regime,meta_label,sports_ml,xgboost_stacker,feature_selector}.py`, `tools/retrain_lgb_top_gainer.py`, `audit_dashboard/meta_model_trainer.py` + `meta_model_chatgpt.py`, `crypto_ml_edge/trainer.py`, `alpha_engine/data/hyro_ml_optimizer_model.pkl` (only `tools/hyro_ml_pick_optimizer.py`) | NO | NO | n/a | **ORPHANED / STALE-ARTIFACTS** |
| 23 | **AI tournament personas** | LLM-API driven; grep confirms **zero local sklearn/xgboost** in tournament agents | n/a | n/a | (73-91% WR is a known snapshot artifact, PR #500 banner) | **NOT LOCAL ML** |
| 24 | **risk_management/regime_detector.py + factor_model.py** | hmmlearn HMM + IsotonicRegression, imported as library by several strategies (quantum_fusion, sentinel_fund, baby_strategies) | library-wired | no dedicated workflow | n/a | **WIRED-DORMANT (library)** |

Dead DB sources (no rows ≥30d, kept for history): `mercury2`, `claude_gainer_st`, `battleground` (trading_picks), `ml_bg_system_a/b/c`, `ml_bg_ensemble`, `breakout_b_ml` (WR-ib 6.3%, PF-ib 0.14), `prediction_market_consensus` (PF-ib **0.01**, n=313), `dna_winner_picks`, `auto_dna_mutation`, `neat_neural_evolver`, `hyperparameter_dna_evolver`, all `genome_revival_*`, `ml_crypto_pred`, `kimi_signal_tracker`.

---

## 2. Key evidence details

### 2.1 kimi_riseoftheclaw firehose (worst offender)
- `at_signal_outcomes` rows/day (created_at): 17,278 / 24,876 / 23,640 / 18,723 / 19,242 / 16,267 / 17,553 for 06-05→06-11; 140,120 in 7d across only **42 symbols**, all `strategy='unknown'`, `opened_at`/`closed_at` NULL.
- Distinct `(symbol,direction,entry_price,pnl_pct)` in those 140k rows: **866** → 99.4% duplicate ingestion.
- Writer: `audit_trail/backfill_local_sources.py:424` (`KIMI_RISEOFTHECLAW/data/kimi_trading.db`), `:449-450` (active/closed JSON), invoked hourly by `.github/workflows/outcome-resolver.yml:165`. The comment at line 148 claims "INSERT IGNORE so re-running is idempotent" — empirically false (no covering unique key for these NULL-keyed rows).
- Impact: contaminates every per-class WR/PF derived from `at_signal_outcomes` (the audit dashboard's honest layer) and adds ~600k junk rows/month.

### 2.2 ml_gatekeeper A/B: why n_ab_tagged = 0
- Bundles exist on `origin/main` (`git ls-tree`: `gatekeeper_old.joblib`, `gatekeeper_new.joblib`; commits `f7e038d6ed`, `5bcfabe289`), trainer cron green (last success 2026-06-11 20:02).
- `ml_gatekeeper/gatekeeper.py:843` stamps `_ab_sleeve` and `:1001` writes NEW-sleeve picks to `ml_gatekeeper/data/active_picks_ab_new.json` — **that file does not exist on origin/main**, and nothing in `alpha_engine/` merges the stamp back into the pick lifecycle. `ab_analysis.py:95` filters `alpha_engine/data/closed_picks.json` for `_ab_sleeve` → finds 0, forever.
- Secondary inconsistency: routing path stamps `pick["_ab_arm"]` (`gatekeeper.py:637`) while analysis reads `_ab_sleeve` only.
- `audit-dashboard.yml:434` does run `python ml_gatekeeper/gatekeeper.py` (non-fatal) and `:326` runs `tools/ml_gatekeeper_ab_decision.py` — Phase D analysis machinery is all wired to data that never arrives.
- The per-class shadow path (`per_class_trainer.predict_quality`) IS live in `smart_picks_engine.py:1489` and `quality_gates.py:97` (shadow, non-blocking).

### 2.3 Intrabar data-quality bug found
- One `ml_enhanced_*` pick carries `intrabar_pnl_pct = +1,706,212%` (max), inflating the family PF to a nonsense 385.29. Trimmed at |pnl|<50%: PF 1.07 / WR 39.3 / n=3016. Any consumer of intrabar PF aggregates must winsorize or fix the scale bug at the resolver.

### 2.4 The reviver pair is the cleanest kill candidate
- `ml_strategy_reviver` PF-ib 0.83 (n=470) and its inverse PF-ib 0.69 (n=221): when both a strategy and its inversion lose intrabar, the loss is structural (TP/SL geometry + fees + first-touch SL bias), not directional. Mutating direction won't fix it; only geometry/holding-period mutation could (per `docs/MUTATION_THREE_AXIS_PROTOCOL.md`).
- M-105 quarantine for the `ml_enhanced` family exists but is **opt-in and OFF by default**: `alpha_engine/money_ready_verdict.py:84-85` (`ML_ENHANCED_CRYPTO_QUARANTINE`, default "0"). Open since 2026-05-18 (`reports/cloud_agent_audit_optimizer_prompt_2026-05-18.md:403`).

### 2.5 CI burn with no sink
Workflows green-but-pointless as of 2026-06-12 (`gh run list` all success):
- `ml-model-autotraining.yml` (4×/day) → trains into `signal_aggregator/models/`, `forward_testing/models/`, `risk_management/models/` — **directories absent from the repo**, artifacts expire in 30 days, no loader anywhere.
- `ml-battleground-retrain.yml` (daily) → warm-starts XGB/PyTorch for systems A/B/C whose emission workflows are `.retired` and whose last picks are March 2026 at ≤5.6% honest WR.
- `mercury2-scan.yml` (hourly) → no `trading_picks` row since 2026-03-28; `last_scan_state.json` 2026-05-29.
- `quick-guess-ml.yml` (hourly) → predictions to repo JSON, zero consumers.
- `hierarchical-bayes.yml` (daily) → ephemeral PyMC output, nothing persisted.

---

## 3. Top-5 recommended actions

1. **Fix the kimi_riseoftheclaw duplicate ingestion (P0, data integrity).** Add a covering unique key / content-hash dedup in `audit_trail/backfill_local_sources.py` (rows have NULL `opened_at`/`closed_at` and `strategy='unknown'`, so the current INSERT IGNORE dedups nothing), then quarantine-or-collapse the existing ~140k/wk duplicates (866 distinct outcomes). Evidence: §2.1. Until fixed, any per-class stats from `at_signal_outcomes` that don't exclude this source are poisoned.
2. **Kill or geometry-mutate the `ml_strategy_reviver` pair and default-enable M-105.** Both arms honestly lose (PF-ib 0.83 / 0.69, combined n=691 ≥ the n>100 bar); flip `ML_ENHANCED_CRYPTO_QUARANTINE` default to "1" in `alpha_engine/money_ready_verdict.py:85`, and route the reviver through the investigation-before-kill protocol with a geometry axis (not direction — the inverse arm already refutes that). This is the highest-volume *currently emitting* honest loser in the ML stack.
3. **Close the ml_gatekeeper A/B last mile (cheap, high info).** Merge `_ab_sleeve` stamps into `alpha_engine/data/active_picks.json` lifecycle (or point `ab_analysis.py` at the sleeve sidecar and make gatekeeper commit `active_picks_ab_new.json`), and unify `_ab_arm` vs `_ab_sleeve`. Today: models trained nightly since ~Jun 10, decision tooling runs daily, measured routed picks = 0. Evidence: §2.2.
4. **Retire zombie CI (≈40+ runs/day for nothing).** Disable or archive `ml-model-autotraining.yml`, `ml-battleground-retrain.yml` (+ resolve/expire the 25,669 perpetually-OPEN `ml_battleground_system_f_clawsofdoom` rows), `mercury2-scan.yml`/`mercury2-retrain.yml`, `hierarchical-bayes.yml`, and decide a sink-or-kill for `quick-guess-ml.yml`. None currently changes a production pick. Evidence: §2.5.
5. **Re-baseline ml_crypto_predictor honestly and fix the intrabar scale outlier.** Repair the 1.7M%-pnl intrabar row (resolver scale bug, §2.3), winsorize PF aggregation, then judge the engine on its trimmed truth: WR-ib 40.5 / PF-ib 1.07 gross (n=1805) ⇒ net-negative after fees. Either raise its emission gate (confidence floor / per-class throttle) or cut its 145 picks/wk until a trained variant clears PF-ib ≥ 1.3 net on n≥300. Honorable mention to **watch, not size**: `genome_mutation_lab` (WR-ib 73.7 / PF-ib 4.43, n=57 — sub-100-n, do not promote yet).

---

## 4. Caveats
- Local file mtimes in this checkout partly reflect checkout time (branch `intrabar-resolve-signal-outcomes-2026-06-09`); where it mattered (gatekeeper bundles) git history on `origin/main` was used instead.
- Nominal WR/PF columns from `trading_picks.status` read ~0% WR because the live pipeline uses other status labels; intrabar columns were used as the honest measure throughout.
- `battleground` (14,027 rows, nominal 72.1% WR in `at_signal_outcomes`) has 0 intrabar coverage and mixed outcome labels (`WON`/`TP_HIT`/`SL_HIT`/`LOST` in the same column) — treat its WR as unverified until intrabar-replayed.
- Sub-100-n slices (regime_terminal n=23, genome_mutation_lab n=57) are flagged per the dashboard's own INSUFFICIENT_N rule; no sizing decisions should be made on them.

*Generated read-only on 2026-06-12 by ML usage audit session. DB: ejaguiar1_stocks @ mysql.50webs.com (SELECT only).*
