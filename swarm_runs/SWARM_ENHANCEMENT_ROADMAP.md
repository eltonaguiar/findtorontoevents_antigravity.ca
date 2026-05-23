# Swarm Enhancement Roadmap — CRYPTO_ML_WORLDCLASS_RESEARCH integration

**Date:** 2026-05-03
**Author:** Subagent (cataloging task)
**Source:** `e:\findtorontoevents_antigravity.ca\CRYPTO_ML_WORLDCLASS_RESEARCH\researchers_001_030\` (30 personas + 30 findings; only `_001_030/` exists, no 031+ batches)
**Last research-corpus touch:** Feb 2026 (commit `fcce5f9268b` "fix(ml): 4 critical bugs from 28-agent research audit"). ~3 months stale relative to current swarm methodology, but signal is largely topic-knowledge (durable), not state-data (perishable).
**Comparison target:** `tools/swarm/agent_personas/*.md` (6 asset-class personas) + `.claude/agents/*.md` (5 process subagents).

---

## Inventory

30 researcher persona files (`researcher_NN_<topic>.md`). Note: researchers 002, 003, 019, 020 ship a "research scope" stub instead of a profile — those files only declare topic + methodology, not a full persona — and 003/019 show `Status: Pending`. The rest are full reports.

| # | Topic | One-line role |
|---|---|---|
| 001 | hedge_fund_quant | Renaissance/Two Sigma/Citadel/Jump literature review; transferable institutional patterns. |
| 002 | lstm_attention | Crypto LSTM/GRU/TFT/Helformer SOTA architectures; diagnoses System C 0% WR. |
| 003 | feature_engineering | Stub (template only) — RSI/MACD/MVRV/SOPR feature catalog. |
| 004 | ensemble_methods | Stacking, regime-conditioned weighting, GBM/NN heterogeneous ensembles. |
| 005 | risk_management | Kelly/half-Kelly, ATR stops, drawdown brakes, vol targeting, MC validation. |
| 006 | backtest_validation | DSR/PSR/MinTRL/CPCV/permutation-test rigor; small-sample diagnostics. |
| 007 | onchain_analytics | MVRV/NVT/SOPR/exchange-flow honest assessment + proxy quality scores. |
| 008 | social_sentiment | Twitter/Reddit/Telegram volume-vs-polarity analysis; CryptoBERT. |
| 009 | market_microstructure | OBI/VPIN/Kyle's-lambda; HFT-vs-hourly cost-benefit. |
| 010 | alpha_decay | Half-life modeling, factor-rotation, retraining cadence. |
| 011 | hyperparameter_optimization | Optuna TPE vs Hyperband vs random; sample efficiency. |
| 012 | reinforcement_learning | DQN/PPO/SAC honest verdict ("rarely survive contact with live"). |
| 013 | transformer_models | TFT/Informer/PatchTST/Helformer benchmarks on crypto. |
| 014 | generative_models | TimeGAN/diffusion synthetic data, regime-conditional augmentation. |
| 015 | explainable_ai | SHAP/LIME/integrated-gradients for trading model audit. |
| 016 | data_quality | Exchange outages, OHLCV gaps, point-in-time, survivorship. |
| 017 | model_deployment | MLOps CI/CD on GitHub Actions; canary, monitoring, drift. |
| 018 | feature_store | Feast/Tecton/Hopsworks; training-serving skew prevention. |
| 019 | quant_connect | Stub — Backtrader/VectorBT/QuantConnect comparison template. |
| 020 | benchmark_datasets | BTC/ETH/SOL standard datasets; survivorship-bias notes. |
| 021 | competition_winners | Codebase audit of internal stacking; Kaggle G-Research patterns. |
| 022 | github_opensource | Codebase comparison vs Freqtrade/TensorTrade. |
| 023 | cloud_services | Codebase audit: 107 GHA workflows on CPU; cloud-migration ROI. |
| 024 | high_frequency_trading | Codebase audit of L2 order-book agent; latency-budget reality check. |
| 025 | portfolio_optimization | 5 internal position sizers cataloged; HRP/CVaR gaps. |
| 026 | cross_exchange_arbitrage | Multi-exchange failover audit; funding-rate arb. |
| 027 | defi_yield_optimization | DeFi token tracking vs protocol integration (none). |
| 028 | mev_extraction | Mempool/Flashbots audit (none — system is signal-only). |
| 029 | regime_detection | HMM/BOCPD/Markov-switching; diagnoses "range_bound everywhere" bug. |
| 030 | governance_token_models | Token unlocks (DeFiLlama API), DAO governance metrics. |

---

## Quality difference vs existing personas

The existing `tools/swarm/agent_personas/*.md` are **terse, evidence-grounded, production-ready** — YAML frontmatter, ~50 lines, cite live numbers from `dashboard_data.json::performance.asset_class_health`, name explicit kill rules with thresholds, list blocked-pattern artifacts (e.g., `quan_engine × MATIC` ghost rows). Existing `.claude/agents/*.md` are similarly tight process specs.

The CRYPTO_ML researcher files are the **opposite shape**: 200-1500-line essays that mix academic literature reviews, codebase audits (some), implementation playbooks, and citations. Most are 5-20× the length of a swarm persona. They contain genuine signal (hard test methodologies, specific paper citations, concrete code patterns), but the format and density are wrong for swarm dispatch.

**Verdict on substance:** mostly real. Personas with codebase audits (021, 022, 023, 024, 025, 026, 027, 028, 029, 030) cite specific files and line numbers — verifiable. Pure-literature personas (001, 002, 004, 005, 006, 010, 011, 013) cite real journals (JoF, BIS WP1087, NeurIPS, arXiv ids) consistent with my own knowledge. **Three concerns:** (a) status-Pending stubs (003, 019) and template-only fragments (002 in part) — fluff; (b) 002 (lstm_attention) and 029 (regime_detection) reference internal files (`ml_battleground/system_c_deeplearn/`, `hmm_regime_gate.py`) that I did not verify exist in current repo state; (c) RL persona (012) is honest about RL's poor live performance — this is signal, not noise.

**Verdict on format:** none of them are drop-in swarm personas. All require re-shaping into the frontmatter + Edge sources / Statistical tests / Kill rules / External benchmarks / Blocked patterns layout.

---

## Overlap vs gap-fill analysis

### Overlap with existing personas
- `crypto_specialist.md` already covers what a generic "crypto ML" persona would. Researchers 001/007/008/009 are deeper in specific sub-domains (institutional patterns, on-chain, sentiment, microstructure) — not duplicates, but adjacent.
- `commodity_specialist.md` / `etf_specialist.md` / etc. cover non-crypto classes. None of the 30 researchers cover non-crypto, so **zero overlap there.**

### Gap-fills (genuinely new capability)
The strongest swarm-relevant gaps the researchers fill:
1. **ML rigor / backtest validation** — 005 (risk), 006 (DSR/PSR/MinTRL/CPCV), 011 (HPO), 014 (synthetic data). Nothing in the swarm currently dispatches a "validation specialist" persona. `quant-performance-auditor.md` is the closest existing role.
2. **Architecture-specific reviewers** — 002 (LSTM/GRU), 004 (ensembles), 013 (transformers), 029 (regime/HMM). Asset-class personas don't speak this language.
3. **Infra reviewers** — 016 (data quality), 017 (deployment), 018 (feature store), 023 (cloud), 024 (HFT/latency).
4. **Edge/strategy-type reviewers** — 010 (alpha decay), 026 (arb), 027 (DeFi), 028 (MEV), 030 (token unlocks).
5. **Codebase-aware reviewers** (021, 022, 023, 024, 025, 026, 027, 028, 030) — these did real audits in Feb 2026; valuable as "repo cartographer" snapshots, but they're closer to `reports/` material than swarm personas.

---

## Tier classification

**Tier A — adopt as-is (1:1 fit, ready to drop in):** zero researchers. None ship the swarm-persona format (frontmatter, kill rules, blocked patterns, current-state numbers from `dashboard_data.json`). Even the highest-quality (006 backtest validation) is a 1500-line essay, not a 50-line agent spec.

**Tier B — adapt (extract substance into swarm-persona format):** 12 candidates, ranked.
| # | Topic | Why B | Tier-B value |
|---|---|---|---|
| 006 | backtest_validation | Has explicit thresholds (DSR>0.95, PSR>0.95, MinTRL formula, MC permutation p<0.05). Convertible into an `ml-validation-specialist` persona with hard kill rules. | HIGH |
| 005 | risk_management | Concrete formulas (Kelly fractions, ATR-mult tables by TF, drawdown tier table). Maps to existing risk discipline; could augment `quant-performance-auditor.md`. | HIGH |
| 029 | regime_detection | Cites our own `hmm_regime_gate.py` and `RegimeDetector`. Diagnoses real bug (rule-based label "range_bound everywhere"). Convertible into a regime-specialist subagent. | HIGH |
| 010 | alpha_decay | Half-life, retraining cadence, decay-watchlist patterns. Plugs directly into our existing `_compute_hf_decay_watchlist` work. | MEDIUM-HIGH |
| 004 | ensemble_methods | Concrete patterns (regime-conditioned stacking, Ridge meta-learner, "agreement alpha"). Convertible into ensemble-architect persona. | MEDIUM-HIGH |
| 002 | lstm_attention | Has concrete bug diagnoses + sequence-length / data-volume / parameter-ratio rules. Useful as `nn-architecture-reviewer` if our system retains GRU/LSTM modules. | MEDIUM (depends on whether System C still alive) |
| 009 | market_microstructure | OBI/VPIN/Kyle's-lambda formulas + honest "edge decays at hourly+" verdict. | MEDIUM |
| 011 | hyperparameter_optimization | Optuna TPE vs random, pruning. Convertible into HPO discipline subagent. | MEDIUM |
| 015 | explainable_ai | SHAP-for-trading specifics; useful when reviewing ML feature importance. | MEDIUM |
| 016 | data_quality | Exchange-outage catalog, gap detection. Convertible into data-quality auditor. | MEDIUM |
| 007 | onchain_analytics | Honest proxy-quality scores. Convertible if we ever wire real on-chain. Today low priority because we don't trade on-chain. | LOWER-MEDIUM |
| 008 | social_sentiment | "Volume > polarity" finding is durable signal. | LOWER-MEDIUM |

**Tier C — discard / sidecar (low swarm-fit):** 18 candidates.
- **003 feature_engineering** — Pending stub; nothing to convert.
- **019 quant_connect** — Pending stub; covered by existing `vibe-trading::backtest`.
- **020 benchmark_datasets** — fine as a `reports/` doc; not a dispatchable persona.
- **001 hedge_fund_quant** — overlaps `crypto_specialist.md` "edge sources" section; cherry-pick BIS funding-rate carry, Liu-Tsyvinski 3-factor, VPIN refs into existing crypto persona instead of new file.
- **012 reinforcement_learning** — honest verdict is "RL backtests rarely survive live"; useful blocked-pattern note ("don't deploy RL agents standalone") to fold into `crypto_specialist.md`, not a persona.
- **013 transformer_models** — adjacent to 002; pick one, not both.
- **014 generative_models** — synthetic-data augmentation; tooling, not a persona.
- **017 model_deployment** — MLOps; covered by repo's existing GHA structure and `dashboard-contract-reviewer.md`.
- **018 feature_store** — infrastructure proposal we don't have on roadmap.
- **021 competition_winners** — codebase audit, fits `reports/`, not a persona.
- **022 github_opensource** — same.
- **023 cloud_services** — same; cloud migration not a current goal per CLAUDE.md.
- **024 high_frequency_trading** — concludes we're "retail-grade WebSocket, not HFT-grade"; this is correct and means we don't need an HFT persona.
- **025 portfolio_optimization** — codebase audit; fold into `reports/`.
- **026 cross_exchange_arbitrage** — codebase audit; not on current goal-list.
- **027 defi_yield_optimization** — confirms we don't trade DeFi protocols.
- **028 mev_extraction** — confirms we don't do MEV.
- **030 governance_token_models** — narrow strategy detail; if needed, fold into `crypto_specialist.md` blocked/edge patterns.

**Tier split: A=0, B=12, C=18.**

---

## Concrete adoption playbook (one worked example)

**Target: convert `researcher_006_backtest_validation.md` → `tools/swarm/agent_personas/ml-validation-specialist.md`** (Tier B, highest-value).

### Why this one first
- Maps to a real swarm gap: today the audit dashboard, hedge-fund report, and resolver-v2 changes all cite Wilson LB / PSR / DSR / Bonferroni informally. No persona owns the "did we actually meet statistical significance" question. `quant-performance-auditor.md` is process-y; this one is statistical.
- Has clear thresholds (DSR>0.95, PSR>0.95, MinTRL table by Sharpe, Bonferroni adjustment for N strategies tested). Convert directly.
- Forces hard-kill rule: any strategy claim with n below MinTRL gets re-labeled `thin_sample`. Already aligns with existing BOND `thin_sample` charter floor.

### Diff sketch (raw → swarm format)

**Drop:** persona narrative ("Dr. Sarah Kim, PhD Stanford..."), 11 of 12 sections, all Python code blocks (kept inline as `Cmd:` references), all formulas (kept as one-line summaries with citations).

**Keep + restructure into the 6-block layout:**

```
---
name: ml-validation-specialist
description: When invoked, this agent decides whether a strategy's reported Sharpe / WR / PF survives multiple-testing correction and meets minimum-track-record-length under crypto's heavy tails. Use whenever a request claims a strategy is "promotable", "production-ready", or "T1/T2-grade" before n exceeds charter floor. Mandatory before any size-up of a strategy newer than 100 trades.
tools: [Bash, Read, Grep, Glob]
model: sonnet
---

You are the ML validation gatekeeper. Your job is to reject false positives.

## Edge sources
- Bailey & Lopez de Prado (2014) Deflated Sharpe Ratio — selection-bias correction across N tested strategies.
- Lopez de Prado (2012) Probabilistic Sharpe Ratio — confidence the true SR > benchmark under crypto skew/kurtosis.
- Lopez de Prado (2018) Advances in Financial ML, ch. 7 — purged + embargo CV; CPCV.
- Holm-Bonferroni (1979) — step-down family-wise error rate.

## Statistical tests
- DSR ≥ 0.95 (using N = total strategies tested, gamma_3 = -0.5, gamma_4 = 8 for crypto).
- PSR(SR*=0) ≥ 0.95.
- MinTRL met (table: SR=2 → n≥306; SR=3 → n≥140; SR=4 → n≥81 for crypto returns; double these vs equity).
- Bonferroni-adjusted p < 0.05 / N_strategies; OR Holm-Bonferroni step-down; OR Benjamini-Hochberg FDR if claim explicitly accepts ~5% false discoveries.
- Monte Carlo permutation p < 0.05, n_permutations ≥ 10000.
- PBO (Probability of Backtest Overfitting) < 0.50; degradation ratio (OOS Sharpe / IS Sharpe) > 0.5.

## Kill rules
- Any "Tier 1/2 promotion" request where DSR < 0.95 OR PSR < 0.95 → REJECT, mark `thin_sample` regardless of point-estimate Sharpe.
- Any "consensus stack" claim with k base models on identical data → reject unless prediction correlation < 0.7 demonstrated.
- Any backtest with `train_test_split(random=True)` on time-series → reject (data leakage).
- Any TP/SL "optimization" using future-known max/min → reject (look-ahead).

## External benchmarks
- Bailey-Prado False Strategy Theorem: with N=15 tested, expected max Sharpe ≈ 1.5 by chance alone.
- 95% rule: ~95% of backtested strategies fail live (industry consensus).
- Crypto kurtosis ≈ 8 → MinTRL ~2× equity baseline.

## Blocked patterns
- "Sharpe 4-8 on n=5-20 trades, 15 strategies tested" → meaningless: P(at least one false positive) = 53.7%.
- Triple-barrier labels with overlapping label horizons used without sample-uniqueness weighting (Lopez de Prado overfitting warning).
- Bootstrapped Sharpe CI lower bound ≤ 0 → not deployable regardless of point estimate.
```

That's a 50-line spec. The 1500-line researcher file becomes a `reports/researcher_006_backtest_validation_archive.md` reference for deep-dive consumption.

### Wire-up
- Add to `tools/swarm/agent_personas/INDEX.md`: a 7th row, "ml-validation-specialist | when ML claims Sharpe/WR/PF promotable".
- Optionally: copy spec to `.claude/agents/ml-validation-specialist.md` (with same frontmatter) so Claude Code's `Task` tool can dispatch it.
- New prompt template `tools/swarm/prompts/ml_validation_review.md` so swarm runs can target this persona directly.

---

## Action items

- [ACTION] Convert researcher_006_backtest_validation.md → `tools/swarm/agent_personas/ml-validation-specialist.md` (Tier B, highest priority). Cmd: `python tools/swarm/convert_researcher.py --in CRYPTO_ML_WORLDCLASS_RESEARCH/researchers_001_030/researcher_006_backtest_validation.md --out tools/swarm/agent_personas/ml-validation-specialist.md` (script does not exist yet — first conversion can be hand-edited following the diff sketch above).
- [ACTION] Convert researcher_005_risk_management.md → augment `quant-performance-auditor.md` with explicit Kelly/ATR/drawdown thresholds (Tier B, second priority). Cmd: append a "Risk thresholds" section citing Kelly fraction = 0.25, ATR mult by TF table, drawdown tiers 5/10/15/20%.
- [ACTION] Convert researcher_029_regime_detection.md → `tools/swarm/agent_personas/regime-detection-specialist.md` (Tier B, third priority). Cmd: hand-edit; ensure `hmm_regime_gate.py` references match current repo (verify with `Grep regex "hmm_regime"`).
- [ACTION] Convert researcher_010_alpha_decay.md → augment existing `_compute_hf_decay_watchlist` doc + add half-life-aware kill rules to `crypto_specialist.md`. Cmd: edit `audit_dashboard/template.html` decay-watchlist section to surface half-life column.
- [ACTION] Convert researcher_004_ensemble_methods.md → `tools/swarm/agent_personas/ensemble-architect.md` (Tier B). Mandate: never approve a "consensus stack" without diversity proof + agreement-alpha test. Cmd: hand-edit per playbook above.
- [ACTION] Cherry-pick from researcher_001_hedge_fund_quant.md (Tier C as standalone, but useful as injection): add BIS funding-rate carry + Liu-Tsyvinski 3-factor as edge sources to `crypto_specialist.md`. Cmd: 5-line edit to existing file.
- [ACTION] Add `tools/swarm/prompts/ml_validation_review.md` so the swarm can dispatch the validation specialist on any claim like "promote strategy X". Cmd: copy structure from `tools/swarm/prompts/pr_review.md`.
- [ACTION] Move all 30 raw researcher files to `reports/archive/researcher_001_030/` so they live alongside other deep-dive docs and are excluded from active-persona space. Cmd: `git mv CRYPTO_ML_WORLDCLASS_RESEARCH/researchers_001_030/* reports/archive/researcher_001_030/` (verify no other code imports the path first via `Grep "CRYPTO_ML_WORLDCLASS_RESEARCH"`).
- [ACTION] Run swarm against the converted ml-validation-specialist persona on a real claim (e.g., "is `st_fear_greed_contrarian` PF 4.22 / WR 75% / n=96 promotable to T1?") to confirm output is useful before converting more. Cmd: `python tools/swarm/run.py --persona ml-validation-specialist --prompt prompts/ml_validation_review.md --target st_fear_greed_contrarian` (verify exact CLI in `tools/swarm/README.md`).

---

## Open questions / risks

1. **Staleness:** Researcher files were last touched in Feb 2026 (commit `fcce5f9268b`, "28-agent research audit"). System state has moved (resolver-v2, asset-class health rewrite, 13 sports PRs, Pinnacle scrape, etc.). Specifically: 002 references `ml_battleground/system_c_deeplearn/` and 029 references `hmm_regime_gate.py` — both must be re-verified to exist in current state before converting (do not adopt a persona that lectures about a file that has been deleted).
2. **Source verification:** Pure-literature personas (001, 005, 006, 010, 011, 013) cite real journals/papers (JoF, BIS WP 1087, arXiv ids matching real preprints, NeurIPS proceedings). Codebase-audit personas (021-030) cite specific files+lines. Spot-checks of citation plausibility passed; full audit not done. **Risk: no LLM-fabrication detector applied.** Before promoting any researcher to a persona, the converter must verify citations exist (dois, arXiv ids, GitHub repos).
3. **Overlap with `reports/`:** Several researchers replicate work that probably already lives under `reports/HEDGE_FUND_AUDIT_REPORT_2026_05_02.md`, `reports/SYNTHESIS_2026_04_21.md`, `reports/forward_edge_audit_2026-05-02.md`. Did not cross-reference. **Risk: re-importing duplicate guidance.** Pre-conversion check: `Grep -l <topic> reports/` for every Tier B candidate.
4. **Persona format vs. essay format:** every Tier B conversion is a substantial information-density compression (10-30× shrink). The converter (human or AI) MUST preserve the kill-rule + threshold backbone and discard the academic narrative — getting the trade-off wrong produces either a useless 800-line "persona" or a hollow 20-line stub.
5. **Stub fluff (003, 019):** mark as Tier C-discard explicitly so future swarm work doesn't mistake the templates for substantive personas.
6. **Worktree replicas:** Glob hit only the canonical path (no `*.worktrees/*` results), so no dedup work needed.

---

## Bottom line

30 personas. Tier A=0, Tier B=12, Tier C=18.

**Top 3 worth adopting (Tier B):** 006 (backtest_validation → ml-validation-specialist), 029 (regime_detection → regime-detection-specialist), 005 (risk_management → augment quant-performance-auditor).

**Top 3 worth discarding (Tier C):** 003 (feature_engineering — Pending stub), 019 (quant_connect — Pending stub), 028 (mev_extraction — confirms we don't do MEV; nothing to operate on).

**One-liner to start the conversion:**

```
python -c "import pathlib; print(pathlib.Path('CRYPTO_ML_WORLDCLASS_RESEARCH/researchers_001_030/researcher_006_backtest_validation.md').read_text(encoding='utf-8')[:5000])" > /tmp/researcher_006_head.txt && code tools/swarm/agent_personas/ml-validation-specialist.md
```

(Open the source head + new persona file side-by-side; hand-edit per the diff sketch in section "Concrete adoption playbook".)
