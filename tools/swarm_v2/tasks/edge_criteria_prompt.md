You are a Quant Systems Architect reviewing a trading system's edge criteria audit.

## Context

A 3-agent swarm audit ran on 2026-05-24 against the tournament_picks dataset (3,149 rows, 34 models). The synthesis is at reports/EDGE_CRITERIA_SWARM_SYNTHESIS_2026-05-24.md.

Three quick wins already done:
1. FRED sidecar api_key → env var (done)
2. Copy Trader → tournament adapter (done: tools/ai_tournament/copy_trader_adapter.py)
3. 5-gate edge significance script (done: tools/ai_tournament/edge_significance_gate.py)

## Open Action Items

### P0 — Audit regime_adaptive label generation for temporal leakage
- regime_adaptive shows 84.6% WR on n=13 (CI: [54.6%, 98.1%])
- Cross-asset consistency at implausible levels suggests regime labels use forward data
- Files to audit: alpha_engine/regime_flip_detector.py, alpha_engine/regime_position_sizer.py
- Need: timestamp alignment check between regime labels and pick submission times

### P1 — Persona_WR as confidence proxy
- The confidence field in tournament_picks is 0.00 across all rows — pipeline broken
- Immediate fix: use persona_WR as a confidence proxy for Kelly sizing
- Long-term: float 0-1 encoding, calibration layer, backfill legacy picks
- Files: alpha_engine/score_booster.py, alpha_engine/scanner.py

### P2 — Whale consensus → direction confidence boost
- 8 whale profiles defined in alpha_engine/prediction_market_whales.py:114
- Orchestrator already outputs whale signals JSON
- Add ~15-line load-and-check in alpha_engine/score_booster.py: if 2+ whales agree on direction for a symbol, boost confidence by 0.10
- Caveat: 6 of 8 whale profiles have "address" field with TODO to fill from Dune Analytics

### P2 — Audit dashboard migration from picks → tournament_picks
- Audit dashboard components still read from the old picks table
- Need to port to read from tournament_picks instead
- Files: audit_dashboard/template.html, audit_trail/dashboard_generator.py

### P3 — Position sizing rules implementation
- Rules documented but not implemented:
  - Total risk budget: 2% of portfolio
  - Per-position risk: 1.5% of NAV
  - Max concurrent: 10 positions
  - Class concentration: 5% per class
  - Sizing method: Equal-weight until n≥20, then fractional Kelly
- Files: alpha_engine/regime_position_sizer.py, alpha_engine/scanner.py

### Additional — FOREX statistical trap
- 57.3% WR but -0.39% avg PnL, Sharpe -0.22
- Many small wins, occasional large losers (3.2:1 loss-to-win ratio)
- Recommendation: zero allocation OR test faded signal (inverse picks)

## Your Task

Produce a ranked action plan with these requirements:
1. Rank all items by impact/complexity ratio (highest ROI first)
2. For each item: specific file to edit, approximate lines changed, verification method
3. Identify dependencies between items (what must be done before what)
4. Estimate which items can be parallelized
5. Flag any items that should be deferred or killed

Output format: structured markdown with clear sections. Be opinionated — "it depends" is not useful here.
