# Ring-2.6-1T Session Review — CX2 Final (2026-05-19)

You are a senior quantitative researcher at a hedge fund. Review the following session deliverables and flag any issues or missed opportunities.

## Session Summary

**Session:** CX2 Final, 2026-05-19T00:00–09:00Z

**Commits pushed to main:**
1. `feat(equity)`: `alpha_engine/validation/run_equity_edge_test.py` — EQUITY validation using correct Bailey & Lopez de Prado 2014 DSR (norm.cdf(z), NOT sr*norm.cdf(z)). `alpha_engine/strategies/equity_momentum_regime.py` — point-in-time regime signal using rolling(252).std().shift(1) benchmark.
2. `feat(quant)`: `tools/h035_funding_settlement_pressure.py` — H-035 TESTED_KILL (8h funding-settlement, sign-flip both legs). `tools/h036_inventory_direction_gate.py` — H-036 TESTED_KILL (EIA inventory direction, WR=46.1%). `tools/mysql_dedup_fix.py` + GHA workflow. `docs/STRATEGY_PERFORMANCE_BLUEPRINT.md`.
3. `docs(ideas)`: DAILY_IDEAS.MD updated with audit prompts, Grok feedback verdicts, DSR/PBO/CPCV definitions.

**Key Decisions:**
- H-035: SHORT effs [0.547, -0.496, 0.07, 0.066] + LONG effs [-0.626, 0.138, -0.231, 0.321] → both sign-flip across 14-day windows → TESTED_KILL
- H-036: WR=46.1% on USO crude oil, EIA weekly inventory signal, 0/7 walk-forward windows pass WR≥56% threshold → TESTED_KILL
- `_normalize_confidence` extended: val>10 → /100 (handles 0-100 format from kimi_inverse/cot_signals)
- Grok DSR formula confirmed WRONG across 8 rounds: `sr * norm.cdf(...)` not valid. Our `statistical_gates.py` has correct formula: `norm.cdf((SR - E[maxSR]) / sr_std)`
- Grok PBO `1-WR²` has no theoretical basis. Real PBO needs CPCV combinatorial paths.
- EQUITY validation: n=69, WR=46.4%, PF=1.23, SR=1.487. DSR PASS but NW t-stat FAIL (p=0.563). Blocker: n<100.

**Grok code issues found:**
- Rounds 1-8: DSR formula `sr * norm.cdf(...)` wrong (corrected in round 9)
- All rounds: PBO `1-WR²` wrong (never corrected)
- Round 9 new bug: `vol.mean()` on a scalar always = 0 (deactivates vol scaling regime factor)
- Round 9 `MISSED_GAINERS` (AMD, NVDA): both BLOCKED in our system (WR=33.3%, PF=0.77)

**Open items:**
- MySQL dedup: needs admin to trigger GHA workflow (IP-restricted from desktop)
- H-021 COT small-spec: re-run 2026-05-26 (2/3 windows pass, need window 3)
- H-027 CO-1: DBA (USDA FAS PSD) and DBB (LME) parsers still synthetic
- EQUITY needs n≥100 for NW t-stat significance (currently n=69)
- Ban protocol has 147 entries with no review cadence

## Questions for You

1. **Walk-forward harness:** With 0/14 hypotheses passing the sign-stability gate (eff≥0.30 same sign in ≥3/5 windows), the swarm consensus is: (a) try an equal-weight ensemble of all 14 signals (variance reduces √14 = 3.7×), or (b) switch to intraday data (14-day window daily = only 14 observations; 5-min gives ~1,092). Which do you recommend as the priority fix, and why?

2. **Ban protocol:** We have 147 entries (blocked symbols/strategies/sources) with no automatic review cadence. Overdue reviews: TRXUSDT, CVX, XOM (11 days past review_date). Is there a better architecture for managing blocked items at scale than our current hardcoded dict in quality_gates.py?

3. **Grok code quality:** After 8+ rounds of iteration, Grok's DSR formula (`sr * norm.cdf(...)`) was wrong and PBO (`1-WR²`) was never fixed. What systemic prompting change would prevent this pattern in future AI consultations?

4. **H-035 kill:** The funding-settlement pressure hypothesis sign-flips on both legs. Is this likely a regime-dependent signal that could be profitable in ONLY high-funding-rate environments? Or is the sign-flip evidence against any edge?

5. **EQUITY validation:** n=69 resolved picks, WR=46.4%, PF=1.23, NW t-stat p=0.563. Primary blocker is n<100. What's the fastest path to n≥100 EQUITY picks without overfitting (i.e., not just adding noise symbols)?

Please respond with structured answers to each question. Be direct and concise — this is for real capital deployment decisions.
