> **NOTE (2026-05-18):** credentials in the original Kimi deliverable were
> plaintext and have been **redacted**. All swarm modules read DB credentials
> from environment variables — set `DB_HOST`, `DB_USER`, `DB_PASS_STOCKS` /
> `DB_PASS_BACKTESTS` / `DB_PASS_BACKUPS`, `DB_NAME` (Windows env vars or a
> local `.env`, never committed). Never paste live passwords into repo files.

# Plan: Swarm Enhancement for Financial Edge Detection & Repo Analysis

## Objective
Enhance the existing swarm infrastructure (`tools/swarm/`, `tools/swarm_v2/`, `.ruflo/`) with industry-standard features for:
1. Statistical edge calculation per asset class (EV, Sharpe, Kelly, concentration)
2. MySQL DB integration for historical pick tracing
3. Dynamic asset gating & regime-switching filters
4. Repo-codebase analysis swarm
5. Self-improvement loop / meta-swarm

## Current State Assessment
- **tools/swarm/**: Has `swarm_pick_schema.py`, `outcome_resolver_swarm.py`, `weekly_review.py`, `pattern_miner.py` — JSON-based pick tracking, yfinance/CoinGecko resolution, (tier x class x regime) pattern mining, basic WR/PF stats.
- **tools/swarm_v2/**: Has hierarchical/ensemble/research swarms, ChromaDB memory, skill export, 6 engines, task management.
- **.ruflo/**: Has orchestrator.py with continuous swarm loops, multi-agent types (coder/reviewer/security/tester/architect), Hermes integration.
- **MySQL DB**: `ejaguiar1_stocks` (pw: `<env var — see below>`), `ejaguiar1_backtests` (pw: `<env var — see below>`), `ejaguiar1_backups` (pw: `<env var — see below>`) — not yet integrated into swarm pipeline.
- **GitHub PAT**: `<REDACTED — revoked PAT, do not use>`

## Missing Features (Industry-Standard Gaps)
1. No MySQL DB adapter in swarm for querying historical picks
2. No statistical edge engine (EV, Sharpe ratio, Kelly criterion, concentration index)
3. No dynamic asset gating controller
4. No regime-switching volatility filter
5. No Bayesian edge updating
6. No repo analysis swarm (code quality → prediction quality correlation)
7. No self-improvement / meta-swarm loop
8. No Herfindahl/Gini concentration metrics
9. No Monte Carlo simulation agent
10. No shared blackboard state architecture across agents

## Execution Stages

### Stage 1: Research & Schema Discovery
- Search industry-standard swarm patterns for financial prediction systems
- Identify the MySQL schema (tables for algorithms, picks, outcomes)

### Stage 2: Code Generation (Parallel PRs)
Create 5 PR branches with enhancements:

**PR-1: `feature/swarm-mysql-edge-engine`** (tools/swarm/)
- `mysql_pick_adapter.py` — MySQL DB connector for ejaguiar1_stocks
- `statistical_edge_engine.py` — EV, Sharpe, Kelly, concentration calculator
- `swarm_edge_auditor.py` — Hierarchical swarm (strategist → tacticians → reviewer)
- Update `config_loader.py` for DB env vars

**PR-2: `feature/swarm-risk-gating`** (tools/swarm/)
- `dynamic_asset_gating.py` — Dynamic position sizing/kill switch per asset class
- `regime_switching_filter.py` — Volatility/ATR-based signal filtering
- `concentration_analyzer.py` — Herfindahl/Gini index for pick distribution

**PR-3: `feature/swarm-v2-repo-analyzer`** (tools/swarm_v2/)
- `repo_analysis_swarm.py` — Codebase crawler, dependency mapper
- `prediction_quality_correlator.py` — Correlate code metrics with prediction performance
- `model_drift_detector.py` — Detect model drift via backtest comparison

**PR-4: `feature/swarm-meta-improvement`** (tools/swarm_v2/)
- `meta_swarm_orchestrator.py` — Self-review past outputs, A/B test prompts
- `skill_evolution_tracker.py` — Track skill effectiveness over time
- `bayesian_edge_updater.py` — Bayesian updating of per-asset-class edges

**PR-5: `feature/ruflo-db-sync`** (.ruflo/)
- Update `orchestrator.py` with DB-aware agent registration
- Add `db_sync_agent.py` for MySQL ↔ JSON store sync
- Add `edge_alert_agent.py` for notifications when edge degrades

### Stage 3: Validation
- Test all generated modules for syntax correctness
- Ensure DB credentials use env var pattern (no hardcoded secrets)
- Verify integration points between existing and new code

### Stage 4: Git Push
- Use GitHub PAT to push all 5 PR branches
- Create PR descriptions with feature summaries
