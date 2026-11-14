# Peer Review: finpredict-v4 — TradingView Contest Winner Research

**Date:** 2026-11-14
**Reviewer:** hilarious-seer
**Source:** `finpredict-v4/research/tradingview_contest_winner_research_2026-11-14.md`

---

## Summary

finpredict-v4 produced a high-quality research document analyzing TradingView "The Leap" contest winners (2024–2026). The research identifies two viable winner archetypes, common methodologies, timeframes, risk rules, and red flags. It connects external contest data to internal repo capabilities (`prove_winners.py`, `winner_reverse_engineer.py`, `multi_asset_copytrader`).

---

## Strengths

1. **Data-driven archetype model.** The two-archetype framework (High-WR Grinders vs High-R:R Snipers) is actionable and maps cleanly to our existing strategy families:
   - Grinders → `multi_asset_copytrader` (82.1% WR documented)
   - Snipers → `st_fear_greed_contrarian` (BNBUSDT +21.42%, AVAXUSDT +10.69%)

2. **Timeframe targeting insight.** The 14:00Z / 21:00Z UTC resolution windows where 76 of 155 genuine winners closed is a concrete, testable hypothesis we can add to the scanner scheduler.

3. **Cost-awareness.** Explicitly notes that paper-trading results are 60–70% of live results on average (LuneFi audit), and our validation pipeline already deducts Binance fees + slippage.

4. **Symbol expansion list.** The 8 missing proven-winner symbols (`AUDJPY=X`, `GBPJPY=X`, `BAT-USD`, `CRV-USD`, `ZECUSDT`, `WLD-USD`, `XTZ-USD`, `MINAUSDT`) are directly ingestible into `alpha_engine/config.py`.

5. **Repainting/lookahead bias warning.** Correctly flags the #1 contest killer and references our existing `prove_winners.py` demotion logic.

---

## Weaknesses / Gaps

1. **No statistical gates applied to the winner data.** The research lists winner percentages but does not compute z-scores, bootstrap CIs, or MC nulls on the contest data itself. We do not know if BenBernanke1's +5,220% is a 5-sigma outlier or a 2-sigma lucky streak among 59,187 contestants.

2. **Survivorship bias unquantified.** The research acknowledges over-leveraged survivorship bias but does not attempt to estimate how many traders using the same approach blew up. A simple Monte Carlo on the contest distribution would quantify this.

3. **ICT/SMC methodology is descriptive, not implementable.** "Liquidity sweeps, FVG retests, order blocks" are not encoded in any repo strategy. There is no Pine Script or Python implementation of ICT concepts in `alpha_engine/` or `baby_strategies/`.

4. **No connection to our actual closed-trade database.** The research references `winner_reverse_engineer.py` but does not show how many of our own closed trades match the winner patterns, or whether our `luxalgo_confluence` (the largest ledger, n=1211) shares any pattern features with contest winners.

5. **Position sizing recommendation is generic.** "Use Kelly Criterion fractional sizing (0.25x–0.5x full Kelly)" is standard textbook advice. It does not address our specific problem: the `MetaLearner` caps score multipliers at 1.5x, but the score-PnL correlation is r=+0.008, so the cap is irrelevant.

---

## Recommendations

1. **Quantify survivorship bias.** Run a simple simulation: if 59,187 contestants each use a strategy with PF=1.0 (coin-flip) and 10-20% position sizing, what is the expected top-decile return? Compare to actual winner returns. If the simulated top-decile is within 2x of actual, the "edge" may be purely leverage + variance.

2. **Implement ICT/SMC as a baby strategy.** The repo has 285 baby strategies; adding one ICT-based strategy (e.g., "FVG retest + order block invalidation SL") would allow us to test the methodology against our own validation gates. This is a medium-term research task.

3. **Cross-reference winner symbols with our resolver output.** For the 8 missing symbols, check `audit_trail/data/universal_resolved_picks.json` (when it exists) to see if we have any historical closed trades. If n<30, we cannot claim edge even if the symbol is on a winner's list.

4. **Add contest-grade gates to the research pipeline.** The document mentions DSR>0.95, cost-adjusted Sharpe>0, regime coverage, 200+ trades — these are already in `PROFITABLE_SCORING_FRAMEWORK.md`. The next step is to run `statistical_scoring_framework.py` on a cohort of trades that match the winner archetypes and report which pass Gate 4 (Money-Ready).

---

## Verdict

**ACCEPT with modifications.** The research is well-sourced and actionable, but it must be connected to our statistical gates and closed-trade data before it can guide real-money deployment. The archetype model and timeframe targeting are immediate wins. The ICT/SMC gap is a known research debt.
