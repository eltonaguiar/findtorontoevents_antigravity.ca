# Swarm Task: EDGE_CRITERIA Action Plan — 2026-05-24

**Task ID:** edge-criteria-action-plan-20260524
**Priority:** P0
**Mode:** research + planning (no code changes — produce action plan only)

## Context

A 3-agent swarm audit (Quant Analyst, Systems Architect, Portfolio Manager) ran on 2026-05-24
against the full tournament_picks dataset (3,149 rows, 34 models). The synthesis is at
`reports/EDGE_CRITERIA_SWARM_SYNTHESIS_2026-05-24.md`.

Three quick wins were already implemented and committed (f9f626cb):
1. FRED sidecar api_key → env var (done)
2. Copy Trader → tournament adapter (done: `tools/ai_tournament/copy_trader_adapter.py`)
3. 5-gate edge significance script (done: `tools/ai_tournament/edge_significance_gate.py`)

## Open Action Items (from synthesis)

### P0 — Audit regime_adaptive label generation for temporal leakage
- regime_adaptive shows 84.6% WR on n=13 (CI: [54.6%, 98.1%])
- Cross-asset consistency at implausible levels suggests regime labels use forward data
- Files to audit: `alpha_engine/regime_flip_detector.py`, `alpha_engine/regime_position_sizer.py`
- Need: timestamp alignment check between regime labels and pick submission times

### P1 — Persona_WR as confidence proxy
- The `confidence` field in tournament_picks is 0.00 across all rows — pipeline broken
- Immediate fix: use persona_WR as a confidence proxy for Kelly sizing
- Long-term: float 0-1 encoding, calibration layer, backfill legacy picks
- Files: `alpha_engine/score_booster.py`, `alpha_engine/scanner.py`

### P2 — Whale consensus → direction confidence boost
- 8 whale profiles defined in `alpha_engine/prediction_market_whales.py:114`
- Orchestrator already outputs whale signals JSON
- Add ~15-line load-and-check in `alpha_engine/score_booster.py`: if 2+ whales agree on direction for a symbol, boost confidence by 0.10
- Caveat: 6 of 8 whale profiles have "address" field with TODO to fill from Dune Analytics — whale tracker relies on usernames/scraping, not on-chain verification

### P2 — Audit dashboard migration from picks → tournament_picks
- Audit dashboard components still read from the old `picks` table
- Need to port to read from `tournament_picks` instead
- Files: `audit_dashboard/template.html`, `audit_trail/dashboard_generator.py`
- Once all consumers cut over, `picks` table becomes archival

### P3 — Position sizing rules implementation
- Rules documented in synthesis but not implemented in code:
  - Total risk budget: 2% of portfolio
  - Per-position risk: 1.5% of NAV
  - Max concurrent: 10 positions
  - Class concentration: 5% per class
  - Sizing method: Equal-weight until n≥20, then fractional Kelly
- Files: `alpha_engine/regime_position_sizer.py`, `alpha_engine/scanner.py`

### Additional — FOREX statistical trap
- 57.3% WR but -0.39% avg PnL, Sharpe -0.22
- Many small wins, occasional large losers (3.2:1 loss-to-win ratio)
- Recommendation: zero allocation OR test faded signal (inverse picks)

## Research Questions

### Agent 1 — P0/P1 Priority & Approach
1. What's the fastest way to audit regime_adaptive for temporal leakage? What specific timestamp fields should be compared?
2. Is persona_WR a statistically valid confidence proxy? What's the correlation between persona_WR and actual pick outcomes?
3. Which of these two should be done first, and why?

### Agent 2 — P2 Items: Whale Consensus + Dashboard Migration
1. Is the whale consensus boost worth implementing given 6/8 profiles lack on-chain verification?
2. What's the migration path for audit dashboard picks → tournament_picks? Which components are affected?
3. Can these be parallelized or should they be sequenced?

### Agent 3 — P3 Position Sizing + FOREX Decision
1. What's the minimum viable implementation of the position sizing rules?
2. Should FOREX be zero-allocated immediately or tested with faded signals first?
3. What kill criteria should trigger a FOREX re-evaluation?

## Constraints
- NEVER run dashboard_generator.py
- NEVER invent numbers — all figures must come from actual files
- Output: 3 concise reports, one per agent, then a synthesized action plan with ranked priorities
- Each recommendation must include: specific file to edit, approximate lines changed, and verification method
