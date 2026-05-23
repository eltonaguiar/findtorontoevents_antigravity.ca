# ASSET_CLASS_VALIDATION_AND_EDGE_IMPROVEMENT_PLAN.md

**Date:** 2026-05-16  
**Scope:** All asset classes in `ejaguiar1_stocks` + `ejaguiar1_backtests` (MySQL on mysql.50webs.com) and live production on findtorontoevents.ca/audit  
**Goal:** Medical-grade validation of statistical edge per asset class, database integrity, error remediation, strategy invention via Ruflo/swarm_v2, and clear next-step decision tree.  
**Philosophy:** Never kill — rehabilitate first (per MEMORY.md Institutional Strategy Policy). All changes documented, tested, non-destructive.

---

## 1. Pre-Validation Checklist (MANDATORY — Every Session)

Before touching any asset class:

1. Read [`SOUL.md`](SOUL.md:1) (personality & work mode)
2. Read [`USER.md`](USER.md:1) (context on human)
3. Read [`MEMORY.md`](MEMORY.md:1) (long-term decisions)
4. Read today's + yesterday's `memory/YYYY-MM-DD.md` (raw logs)
5. Run `git status && git log --oneline -5` (verify clean working tree)
6. Confirm no active terminals running heavy scripts (`check_active_picks.py` or `alpha_engine/smart_picks_engine.py` — NEVER auto-run)
7. Set `AUDIT_PICK_SANITY_GATE=1` only for dry-run validation passes

**Output:** Create `memory/2026-05-16-validation-start.md` with timestamp and "Pre-checks passed".

---

## 2. Per-Asset-Class Validation Protocol

Run the following **sequentially** for each asset class. Use `tools/analyze_asset_classes.py` and `audit_trail/edge_filters.py` as entry points.

### 2.1 Data Integrity & Error Detection (MySQL Layer)

**Target Tables:**
- `ejaguiar1_stocks.*` (OHLCV + asset_class column)
- `ejaguiar1_backtests.bt_backtest_trades`, `bt_backtest_runs`, `strategy_registry`

**Validation Script (run via `python tools/db_freshness_check.py --asset-class <AC>`):**

```sql
-- 1. Phantom / ghost rows (NULL pnl on CLOSED)
SELECT asset_class, COUNT(*) AS ghosts
FROM bt_backtest_trades
WHERE status = 'CLOSED' AND (pnl_pct IS NULL OR exit_price IS NULL)
GROUP BY asset_class;

-- 2. Future-dated entries (look-ahead bias)
SELECT asset_class, COUNT(*) AS future_rows
FROM bt_backtest_trades
WHERE entry_date > NOW() OR exit_date > NOW();

-- 3. Inconsistent asset_class tagging
SELECT symbol, COUNT(DISTINCT asset_class) AS class_variants
FROM bt_backtest_trades
GROUP BY symbol
HAVING class_variants > 1;

-- 4. Volume / price outliers (MAD > 5x)
-- (Python side in `tools/data_quality_issues.py`)
```

**Error Remediation Steps:**
- If ghosts > 0.1% → run `audit_trail/universal_pick_resolver.py --dry-run --fix-nulls`
- If future dates → quarantine to `failed_strategies/` + document in `updates/`
- If class mismatch → enforce `audit_trail/asset_classification.py:resolve_asset_class()` as single source of truth

**Success Gate:** 0 critical errors + <0.5% warning rows.

### 2.2 Statistical Edge Measurement

**Core Query (from DAILY_IDEAS_PROMPTS.MD Prompt #2 — adapted to real columns):**

```sql
WITH per_class AS (
  SELECT 
    asset_class,
    AVG(pnl_pct) AS mean_pnl,
    STDDEV_POP(sharpe) AS sharpe_std,
    COUNT(*) AS n,
    AVG(win_rate) AS mean_wr,
    AVG(max_dd) AS mean_mdd
  FROM bt_backtest_runs
  WHERE n >= 30
  GROUP BY asset_class
)
SELECT 
  asset_class,
  mean_pnl,
  mean_wr,
  mean_mdd,
  (mean_wr * (1 - mean_mdd)) / NULLIF(sharpe_std, 0) AS edge_score,
  -- 95% CI for Sharpe
  mean_sharpe - 1.96 * sharpe_std / SQRT(n) AS sharpe_ci_lower
FROM per_class
ORDER BY edge_score DESC;
```

**Python Companion:** `python tools/analyze_asset_classes.py --target audit_dashboard/data/dashboard_data.json`

**Edge Thresholds (Medical-Grade):**
- Tier 1 (Promote): PF ≥ 1.5, WR ≥ 55%, MDD ≤ 15%, n ≥ 100, edge_score > 0.8
- Tier 2 (Paper-Only): PF ≥ 1.15, WR ≥ 50%, n ≥ 30
- Tier 3 (Rehab): Anything below → enter 6-stage Rehabilitation Pipeline

**Current Snapshot (2026-05-16):**  
- EQUITY: Tier 2 candidate (PF 1.41, WR 52.7%)  
- CRYPTO: Sub-Tier 2 (PF 1.25, WR 44.6%)  
- FOREX: Critical (PF 0.27)  
- Others: Data-starved or negative

### 2.3 Strategy Inventory & Performance Audit

For each class:

1. `python audit_dashboard/build_strategy_registry.py --asset-class <AC>`
2. Cross-reference against [`docs/ALL_STRATEGIES.md`](docs/ALL_STRATEGIES.md:8)
3. Identify top-5 & bottom-5 by edge_score
4. Run `alpha_engine/forward_validator.py --class <AC> --window 90d`

**Blocked / Retired Check:**  
`python -c "from alpha_engine.strategy_blocklist import is_blocked_strategy; print([s for s in get_all_strategies() if is_blocked_strategy(s)])"`

---

## 3. Rehabilitation & Strategy Invention Workflow

If class fails Tier 2:

### 3.1 6-Stage Rehabilitation Pipeline (per MEMORY.md)

1. **Cross-symbol** → `tools/hyro_pick_performance_validator.py`
2. **Cross-asset** → `audit_trail/cross_asset_correlation.py`
3. **Inverse** → `alpha_engine/commodity_kill_switch.py` + inversion prompts
4. **DNA Mutation** → `alpha_engine/strategy_mutation_engine.py` (Gaussian ±5% on thresholds)
5. **Regime Filter** → `alpha_engine/regime_flip_detector.py`
6. **Crossover** → `ml_consensus/consensus.py`

### 3.2 Swarm Research (Ruflo / swarm_v2)

**Launch Command (NEVER auto-run — explicit user request only):**

```bash
# Ruflo swarm (per-asset-class research agents)
hermes chat -q "Run Ruflo swarm on EQUITY edge discovery using prompts from DAILY_IDEAS_PROMPTS.MD #2 and #3" --model grok-4

# swarm_v2 (multi-agent)
python tools/swarm_v2/orchestrator.py --asset-class FOREX --prompts DAILY_IDEAS_PROMPTS.MD --mode research
```

**Agent Roles (from Prompt #5):**
- Edge-Detector Agent → daily SQL edge script
- Strategy-Generator Agent → inversion + DNA mutation → backtest on 6-month rolling window
- Meta-Optimizer Agent → Optuna hyper-parameter sweep on stagnant classes
- Deployment Agent → Docker + GitHub Actions deploy only after Tier-2 gate

**Output Artifact:** `research/<AC>_swarm_results_YYYYMMDD.json` + `.MD` summary in `updates/`

---

## 4. Decision Tree — Next Steps per Asset Class

```
Start
  │
  ├── Data Integrity Pass? ──No──> Fix errors → Re-run 2.1
  │
  ├── Edge ≥ Tier 2? ──Yes──> Promote to live (update portfolio_manager.py _asset_filter)
  │                │
  │                No
  │                │
  ├── n ≥ 30? ──No──> Run swarm_v2 data-collection subagent (increase sample)
  │
  ├── Negative EV proven? ──Yes──> Enter 6-stage Rehab (document in updates/)
  │
  └── Still failing after Rehab? ──Yes──> PAPER-ONLY flag + continue monitoring
```

**Unblock Symbol Criteria (from prior analysis):**
- n ≥ 30 resolved trades post-block
- WR ≥ 52% (Wilson LB ≥ 45%)
- PF ≥ 1.15 (bootstrap CI lower)
- 7-day PnL slope > 0
- No regime conflict
- Passes all current gates
- `updates/YYYY-MM-DD-symbol-rehab-<SYMBOL>.md` written

---

## 5. Tools & Commands Reference

| Task | Command / File | Notes |
|------|----------------|-------|
| Edge SQL | `tools/db_freshness_check.py` | Dry-run first |
| Asset analysis | `tools/analyze_asset_classes.py` | Produces JSON + MD |
| Quality gates | `audit_trail/quality_gates.py:passes_smart_gate` | Per-class floors |
| Swarm research | `tools/swarm_v2/` + Ruflo | Explicit user approval |
| Mutation | `alpha_engine/strategy_mutation_engine.py` | ±5% Gaussian |
| Forward test | `alpha_engine/forward_validator.py` | 90d window |
| Dashboard regen | `python -m audit_trail.dashboard_generator` | After any change |

---

## 6. Success Criteria & Sign-off

**Per Class Sign-off Requires:**
- [ ] Data integrity report (0 critical errors)
- [ ] Edge metrics table (Tier verdict)
- [ ] Strategy registry diff vs `docs/ALL_STRATEGIES.md`
- [ ] If rehab: 6-stage log + before/after metrics
- [ ] If swarm: `research/<AC>_results.md` + PR with only your changes
- [ ] `updates/2026-05-16-<AC>-validation.md` committed

**Global Gate:** Aggregate portfolio PF ≥ 1.10 after all class updates (blocklist leakage test).

---

## 7. Appendices

- **Prompt Library:** Copy from [`DAILY_IDEAS_PROMPTS.MD`](DAILY_IDEAS_PROMPTS.MD:28) (Prompts 1-10)
- **SQL Edge Script:** Full version in Prompt #2
- **Rehab Evidence:** `winner_pattern_precursor_inverse` (81.2% WR) example in MEMORY.md

**End of Plan.** Execute one asset class at a time. Update this file with results after each validation cycle.

---
*Medical-grade rule: Document every fix. No undocumented changes. Test before any live exposure.*