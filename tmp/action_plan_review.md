# Action Plan — Swarm Review Request

**Context:** Consolidating multi-agent MDs (opencode, freebuff, cursor, claude-opus-4-7) into a prioritized action plan. The agents largely converge on 4 P0 items. This plan asks: which is safest to ship first, and what QA gates are needed?

## P0 candidates (cross-agent convergent)

### A) closed_picks.json field backfill
- **Bug**: `score`, `trust_score`, `smart_score`, `grade`, `strat_fwd_wr`, `trust_tier` are 0/7645 populated in closed pick records (verified by opencode in `updates/2026-05-05-round-2-execution.md`).
- **Root cause**: pick-close path (likely `forward_validator.py` or `dashboard_generator.py` close-handler) writes only `exit_price/exit_date/status/pnl`, drops the active-pick fields.
- **Fix**: In close-handler, copy `score/trust_score/smart_score/grade/strat_fwd_wr/trust_tier` from the active pick into the closed record.
- **Risk**: LOW — data-integrity only, no strategy change.
- **Impact**: Unblocks every "Score >= X = Y% WR" tooltip claim; enables real backtest cohort analysis.

### B) quan_engine volume cap
- **Bug**: quan_engine ~18% of CRYPTO volume at PF 0.70 (confidence-band specifics: 0.50-0.59 = 36.7% WR but 0.60-0.69 = 19.8% WR — INVERTED calibration per opencode fix_CRYPTO MD).
- **Fix**: Cap volume share to 5-12% via mutation registry; OR fix the inverted confidence calibration in `elite_scorer.py:629-636`.
- **Risk**: MED — strategy change. CLAUDE.md mutate-before-kill protocol requires `reports/deep_dive_CRYPTO_*.md`.
- **Impact**: CRYPTO PF 1.25 → ~1.55 estimated.

### C) R:R "INVERTED" code comment vs live page
- **Conflict**: `quality_gates.py:2492-2511` says R:R 2.0-3.0 = 42.4% WR (worst). Live `/audit` page (verified 2026-04-17, n=1916) says R:R≥2.0 = 58% WR PF 3.06 (best).
- **Fix**: Re-run `tools/mutation_analysis.py` on current data; reconcile or update one source of truth.
- **Risk**: LOW (analysis-only, no code change until verified).
- **Impact**: Either prevents incorrect R:R hard gate (PR #149fbacd shadow) OR confirms code comment is correct and live page is stale.

### D) alpha_engine_fast strategy
- **Data**: n=358, PF 0.62, WR 39.7%, PnL -127.58%, status=monitoring (Cursor surfaced).
- **Options**: KILL (deepseek + cerebras vote in freebuff swarm) vs MUTATE_PARAMS (xAI vote in same swarm).
- **Risk**: MED — affects active strategy.
- **Impact**: Removes -127% drag.

## Proposed sequencing

1. **Ship A first** (today): pure data fix, no strategy change. Validate via post-merge run of dashboard_generator + close-path test.
2. **Verify C** (today, analysis only): re-run mutation_analysis, decide which side is right.
3. **Defer B and D** until per-class deep-dive docs exist per CLAUDE.md mutate-before-kill protocol.

## Required QA gates per action

- **Pre-merge**: pytest passes locally on touched files
- **Post-merge**: monitor next CI Tests run on main goes green
- **Post-merge**: check next scheduled run of the affected workflow (audit-dashboard.yml, etc.) succeeds
- **Spot-check**: for UI-affecting changes, Playwright or browser snapshot of `/audit` to confirm no regression
- **For strategy changes**: 14-day shadow period before going live (default-OFF env flag, observe metrics, then flip)

## Questions for swarm

1. Does P0-A actually unblock the tooltip claims, or are score values computed from other fields that ARE present?
2. Is it safe to land P0-A without also re-running dashboard_generator on existing closed_picks (backfill historic)?
3. Are there any auth gates on the close-path I'm missing (e.g., does the writer have access to the active-pick fields at close time, or is the active record gone by then)?
4. Which of the four is the single highest expected-value item to ship now?

Verdict requested: SHIP-A / SHIP-C / SHIP-OTHER / HOLD-ALL with one-paragraph reasoning.
