# Plan: Comprehensive Hedge-Fund-Grade Audit + PR Creation

## Stage 1 — Methodology Correction + Re-Audit (in_progress)
Load: none (custom orchestration)

Claude caught two critical errors:
1. `pnl_pct` is DECIMAL (0.0036 = 0.36%), not percent. My 0.01 threshold = 1% was WRONG.
   - This misclassified real wins/losses as FLAT for FOREX
   - Must re-run all calculations with correct threshold
2. `non_crypto_consensus` is FLAT (resolver/holding-window issue), not a kill candidate
3. `stocks_rsi2_pullback` is borderline, mutation territory — not immediate kill

Action: Re-run full per-asset audit with CORRECT pnl_pct interpretation (0.01 = 1%, so 0.0001 = 0.01% is the actual 1bp threshold)

## Stage 2 — Deep Repo Inspection + Module Mapping (pending)
Deploy subagents to:
- Clone and map all prediction modules
- Map data sources per asset class
- Map model/strategy files
- Map gate/risk control files
- Map performance evaluation scripts

## Stage 3 — Per-Asset-Class Performance Audit (pending)
After methodology fix, re-run:
- CRYPTO: 24h/72h/7d/30d with correct thresholds
- EQUITY: same
- FOREX: same (will change significantly due to threshold fix)
- COMMODITY: same
- BOND: check if any data exists
- ETF: check if any data exists

## Stage 4 — Gate Framework + Risk Controls Review (pending)
- Audit all hard-coded blocked lists
- Propose unified gate framework per Mercury prompt
- Review JPY-cross, strategy-pair, direction, volatility targeting

## Stage 5 — Performance Gap Analysis (pending)
Compare against tiers:
- Tier 1: PF>2.0, WR>55%, MDD<10%
- Tier 2: PF>1.5, WR>50%, MDD<20%
- Tier 3: PF>1.2, WR>48%, MDD<30%

## Stage 6 — Open PR Review + Action Plan (pending)
Review all open PRs and create merge action plan

## Stage 7 — Create New PRs with Fixes (pending)
- PR 1: Methodology fix + threshold correction
- PR 2: Unified gate framework config
- PR 3: Strategy mutation framework (not kill) for borderline strategies
- PR 4: Per-asset-class quality monitor script

## Stage 8 — Integration + Testing Plan + Timeline (pending)
Write deliverables:
- Markdown report (max 2 pages)
- Revised config with new gate rules
- `run_audit.py` script
- Timeline for expected improvements per asset class

## Deliverables
1. `/mnt/agents/output/HEDGE_FUND_AUDIT_REPORT_2026_05_02.md`
2. `/mnt/agents/output/config_revised.yaml`
3. `/mnt/agents/output/run_audit.py`
4. `/mnt/agents/output/PR_ACTION_PLAN.md`
5. `/mnt/agents/output/INTEGRATION_TESTING_PLAN.md`
