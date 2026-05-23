# Quant Rescue Playbook Review — Mercury2 + Grok vs Repo Reality — 2026-05-19

**Scope:** Review the two external-AI "quant rescue playbooks" against what this
repo already has. Operator's prompt to the AIs: *"You are a quant fixing a
failing prediction company — what stats + methodology do you run through their
GitHub Actions + MySQL DB?"*

**Headline:** ~85% of what Mercury2 + Grok proposed is **already built and
running** in this repo. Both playbooks are competent generic quant-rescue
advice, but they were written largely *blind to* (Mercury2) or only *shallowly
aware of* (Grok) the fact that this repo has already completed an exhaustive,
rigorous edge hunt and reached a documented **no-edge verdict** (11/11
pre-registered hypotheses killed — `reports/EDGE_HUNT_EXHAUSTED_2026-05-18.md`).
The playbooks treat the problem as "you haven't measured properly yet." The repo
has measured properly, and the answer is in.

---

## 1. ALREADY HAVE — mapped to existing artifacts

| Playbook recommendation | Source | Existing repo artifact |
|---|---|---|
| Sharpe / Sortino / Calmar | Mercury2 | `audit_trail/advanced_risk_metrics.py` (confirmed; `alpha_engine/` mirror) |
| Profit factor, expectancy, win/loss | Grok SQL | `audit_dashboard/data/pf_registry.json` — canonical **deduped** PF ledger; `tools/ci_gate_money_ready_vs_registry.py` |
| Walk-forward cross-validation | Mercury2 | `tools/edge_stability_harness.py` — 5-window walk-forward, same-sign ≥3/5 gate; `alpha_engine/walkforward_validator.py`; `.github/workflows/walkforward-gate.yml` |
| Purged K-Fold / Combinatorial Purged CV | Grok | `tools/purged_kfold.py`, `tools/cpcv_overfit_detector.py` |
| Deflated Sharpe Ratio | Grok | `tools/deflated_sharpe.py`, `tools/deflated_sharpe_per_feed.py`, `alpha_engine/deflated_sharpe.py` |
| Bootstrap CI on Sharpe (resampling) | Grok | `tools/block_bootstrap.py`, `tools/block_bootstrap_ci.py`, `audit_trail/edge_filter_bootstrap.py`, `mc_strategy_validator.py` (bootstrap WR/mean CI) |
| Permutation test for hit-rate | Grok | `tools/mc_strategy_validator.py::permutation_test()` — direction-flip null, p-value vs observed mean |
| Transaction-cost simulation | Mercury2 | `audit_trail/transaction_cost_model.py`; every harness kill is cost-adjusted (5–30 bps round-trip applied in `EDGE_HUNT_EXHAUSTED`) |
| Regime detection (vol / weekday) | Grok | ~30 regime modules — `hmm_regime.py`, `fast_regime_detector.py`, `regime_router.py`, `tools/regime_performance.py`, `tools/regime_stratified_posterior.py` |
| Kelly / optimal-f sizing | Grok | `alpha_engine/kelly_position_sizer.py`, `tools/dynamic_kelly_sizer.py` |
| Expected Shortfall / CVaR | Grok | `audit_trail/advanced_risk_metrics.py` (CVaR/ES present); `tools/cot_step7_risk_of_ruin_mc.py` |
| Signal decay monitoring | Grok | `alpha_engine/decay_tracker.py` (rolling-Sharpe auto-demotion GREEN/YELLOW/RED/BLACK), `tools/alpha_decay_monitor.py`, `tools/edge_decay_monitor.py`, `tools/edge_decay_heatmap.py`, `audit_trail/forward_degradation_tracker.py`; `.github/workflows/edge-decay-check.yml` |
| `quant-audit.yml` GitHub Actions workflow | Mercury2 | Already exists in multiple forms: `quant-auditor-fast-pr.yml` (PR-time, hard 60s, red on INSUFFICIENT_DATA), `quant-auditor-deep-nightly.yml`, `alpha-quant-stack.yml`, `audit-dashboard.yml` |
| Gatekeeper that kills bad strategies | Grok | `alpha_engine/decay_tracker.py` BLACK tier = halt; `audit_trail/quality_gates.py`; `BLOCKED_SOURCE_SYSTEMS`; ML gatekeeper (`ml-gatekeeper-ab-bootstrap.yml`, `tools/retrain_gatekeeper_clean.py`) |
| Hypothesis pre-registration | (neither — repo exceeds them) | `reports/hypothesis_registry.json` (M-107) — 11 hypotheses pre-registered before testing, the gold-standard practice both playbooks omit |
| Monte Carlo robustness | Mercury2/Grok | `alpha_engine/intensive_monte_carlo.py`, `monte_carlo_validator.py`, `tools/data_integrity/monte_carlo_baseline.py` |
| Scoring composite (mercury2_scoring) | — | Note: no `mercury2_scoring.py` file found; scoring lives in `score_booster.py` / `smart_picks_engine.py`. The 7 pipeline scores were all run through the harness (`elite_score` eff 0.06 = noise). |

**Coverage: ~85% already built.** Every headline metric, every CV method, every
risk stat, the CI workflow, the gatekeeper, and even hypothesis pre-registration
(which neither playbook proposed) already exist and have *already been used to
reach a verdict*.

---

## 2. GENUINELY NEW — not in the repo, worth considering

Slim list — and most are marginal given the verdict.

1. **Hit-rate–specific permutation test as a first-class, per-class CI artifact.**
   `mc_strategy_validator.py::permutation_test()` exists but operates on a
   *direction-flip null over a return series*, not a clean label-shuffle on the
   binary hit-rate per asset class, and it is not wired as a standalone CI gate
   output. A thin `permutation_pvalue_by_class` emitted into `pf_registry.json`
   would make the "29% WR is statistically indistinguishable from noise" claim
   machine-checkable rather than narrative. **Low effort, real value.**

2. **Signal-decay-*by-age* bucketing.** The repo has rolling-Sharpe decay
   (`decay_tracker.py`) and forward-degradation tracking, but no analysis that
   buckets each pick by *age of the signal at entry* (days between signal
   emission and trade) and computes hit-rate per bucket. Grok's
   `signal-decay-by-age` SQL is genuinely absent. Useful as a leakage/latency
   diagnostic — would quantify whether stale-signal entries drag the book.
   **Medium value, medium effort.**

3. **Information Ratio / ROC-AUC on the score vs realized outcome, per class,
   in CI.** The repo computes score-vs-WR Spearman ρ (`project_performance_reality`)
   but not a formal IR or a calibration/ROC curve as a recurring artifact.
   ROC-AUC is *near-useless on a noise signal* (see §3) but a **calibration
   curve** of `elite_score` deciles vs realized WR would visually confirm the
   eff-0.06 finding for non-quant stakeholders. **Communication value only.**

4. **Flip the `money-ready-registry-gate` from warn-mode to hard-blocking.**
   The workflow exists but ships `continue-on-error: true` with a
   `TODO(flip-to-blocking)`. This is the single concrete "CI gatekeeper that
   fails the build on bad metrics" item both playbooks pushed — and it is a
   one-line change once the CRYPTO PF-source divergence is reconciled. The repo
   *planned* this; it is not done. **High value, low effort.**

5. **Latency / signal-to-fill audit SQL.** Mercury2's signal-to-trade and
   latency queries have no direct equivalent — the repo audits *outcomes*, not
   *execution timing*. Marginal given the system is paper-only, but it is a true
   gap if the strategic fork ever goes to new live signals.

---

## 3. WRONG / NAIVE FOR THIS REPO

1. **Both assume a clean `trades` table.** Mercury2's `extract_sql.py` and
   Grok's expectancy SQL implicitly query a tidy single trades ledger. Reality:
   `at_raw_picks` / `at_consensus_picks` / `bt_*` with documented dedup,
   COT-row-duplication, and ghost-row corruption (`reports/DB_PICK_TRACEBACK_2026-05-18.md`,
   MEMORY: MATIC 660-ghost-row artifact, `quan_engine` 100%-WR artifact). Running
   their SQL as-written re-derives the *inflated* numbers. The repo already
   solved this with `pf_registry.json` as the canonical deduped view — their
   playbooks would regress to the un-deduped source.

2. **Grok's "hit-rate > 50% sanity check" ignores the verdict.** A >50% WR
   threshold as a green-light is exactly the trap the repo already escaped: six
   of seven "edges" in `EDGE_VERDICT` showed >50% in-sample WR and **all
   inverted out-of-sample**. The harness's same-sign-≥3/5-windows test, not raw
   WR, is the real gate. Treating WR as a pass criterion would re-admit killed
   strategies.

3. **ROC-AUC on the pipeline score is measuring noise.** `elite_score` has
   harness eff 0.06 — statistically indistinguishable from random. Computing
   ROC-AUC on it produces a number near 0.50 that *looks* like a metric but
   carries no decision content. Grok recommends it generically; here it is
   busywork.

4. **Treating dashboard numbers as truth.** Both playbooks would ingest
   whatever the DB/dashboard reports. The repo has a *documented* dashboard-vs-
   reality disconnect (gaudy PFs are CT=F leakage + `quan_engine_scalp` craters;
   `project_pf_registry_canonical_2026_05_17`). Grok *noticed* this in its repo
   browse — to its credit — but its concrete SQL still pulls raw aggregates.

5. **"Rescue" framing is stale.** Both playbooks frame the job as *diagnose then
   rescue*. The repo has finished diagnosis: `EDGE_HUNT_EXHAUSTED` concludes the
   free-data / daily-bar / retail-accessible edge space is **empirically empty**
   across 4 asset classes and 11 hypotheses. The remaining decision is a
   *strategic fork* (new paid signal sources vs paper-only research sandbox) —
   an operator choice, not a stats problem. Re-running their audit suite would
   burn the exact hours `EDGE_VERDICT` was written to prevent (it explicitly is
   the "stop-sign so a fifth agent does not burn the same hours").

6. **Bootstrap CI on Sharpe with 10k iid resamples (Grok).** Naive iid bootstrap
   on autocorrelated daily returns understates the CI. The repo correctly uses
   *block* bootstrap (`tools/block_bootstrap.py`) for this reason. Grok's 10k-
   resample spec, taken literally, is methodologically weaker than what exists.

---

## 4. NET VERDICT — Top 5 genuinely-actionable, ranked

Of everything Mercury2 + Grok proposed, after subtracting what's already done:

1. **Flip `money-ready-registry-gate.yml` to hard-blocking.** Remove
   `continue-on-error: true` once the CRYPTO PF-source divergence is reconciled.
   This is the one real "CI fails on bad metrics" gatekeeper item — already
   scaffolded, one TODO away. *Low effort, high value.*

2. **Emit a per-asset-class permutation p-value into `pf_registry.json`.**
   Wrap a clean label-shuffle hit-rate permutation (extending
   `mc_strategy_validator.py`) so every class carries a machine-checkable
   "indistinguishable from noise" flag. Makes the no-edge verdict auditable in
   CI, not just narrative. *Low effort, real value.*

3. **Signal-decay-by-age bucketing.** Build Grok's genuinely-absent
   `signal_age` analysis — hit-rate per (days-from-emission-to-entry) bucket. A
   true gap and a useful latency/leakage diagnostic if the strategic fork picks
   "new signals." *Medium effort.*

4. **Calibration curve of `elite_score` deciles vs realized WR.** Not a new
   discovery — a *communication* artifact that visually proves the eff-0.06
   noise finding to non-quant stakeholders / the operator making the fork
   decision. *Low effort, communication-only value.*

5. **Latency / signal-to-fill audit (deferred).** Mercury2's execution-timing
   SQL — only worth building *after* the strategic fork chooses live new
   signals; meaningless for a paper-only sandbox. *Park until fork decision.*

**Bottom line:** the playbooks are solid generic advice that this repo
*already implemented and already executed to completion*. Do not re-run the
audit suite — the verdict is in (`EDGE_HUNT_EXHAUSTED_2026-05-18.md`). Items
1–2 are worth doing this week (cheap, harden what exists); 3–4 are nice-to-have;
5 waits on the operator's strategic fork.
