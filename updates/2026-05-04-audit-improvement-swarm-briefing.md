# Audit Improvement Swarm Briefing - 2026-05-04

## Mission

Advance Goal #1: get `/audit` closer to institutional-grade performance across all asset classes. The current swarm evidence says the highest ROI work is not adding more strategy breadth; it is stopping known leakage, fixing closed-pick data integrity, and only then mutating weak asset-class systems.

Primary sources:
- `reports/audit_swarm_analysis_20260505T005402Z.md`
- `updates/2026-05-05-round-2-execution.md`
- `reports/fix_CRYPTO_20260505T005402Z.md`
- `reports/fix_FOREX_20260505T005402Z.md`
- `reports/fix_COMMODITY_20260505T005402Z.md`
- `reports/fix_EQUITY_20260505T005402Z.md`
- `reports/fix_ETF_20260505T005402Z.md`
- `reports/fix_FUTURES_20260505T005402Z.md`

## Current Read

CRYPTO is below the T2 bar mostly because `quan_engine` drag is too large. The old blanket recommendation was to cap `quan_engine` volume, but the asset note sharpens that into a more specific finding: `quan_engine` confidence calibration is inverted, and `quan_engine_swing` may still be emitting.

FOREX is the genuine emergency: PF 0.27 on n=1169 is not sample noise. Follow `docs/MUTATION_THREE_AXIS_PROTOCOL.md` before any kill-list expansion. The likely failure mode is bad trade geometry and bad session/pair selection, not just a weak signal.

COMMODITY is closer than it looks. PF 1.78 is already T2-quality, while WR 46.9% may be acceptable for trend-following if max drawdown qualifies. Verify MDD before adding complexity.

EQUITY is a near-T2 scale candidate. PF 1.41 needs a small lift to cross 1.5, while WR and sample size are already usable. Do not expand low-quality equity systems; concentrate allocation into proven winners and verify existing loser blocks.

ETF is watchlist, not an urgency. PF 1.24 and WR 55.2% are T3-shaped, but n=87 is below the charter floor. Wait for n=100; separately locate and mutate the `extreme_oversold_bounce` family if it still exists under another name.

FUTURES must be quarantined. A 6.3% WR at n=17 is too small for diagnosis but too bad to allow fresh live flow. Treat it as investigation-only until at least a futures-specific gate, universe restriction, and gap-risk review exist.

## P0 Execution Order

1. Fix closed-pick data integrity. `score`, `trust_score`, `smart_score`, `grade`, `strat_fwd_wr`, and `trust_tier` are 0% populated in 7,645 closed records, which makes score-band claims unverifiable. The close path must persist the issue-time scoring fields into closed records.

2. Stop using weak positive labels as if they are edge. `Smart Picks` currently tests at 54% WR / PF 0.56 and should not be treated as a positive gate until revalidated. The real high-conviction signal is `strat_fwd_wr >= 70` combined with trust tier or trust score, with a point-in-time bias warning.

3. Patch crypto leakage. Verify `quan_engine_scalp` and `quan_engine_position` are blocked, audit `quan_engine_swing`, fix the inverted `quan_engine` confidence calibration in `alpha_engine/elite_scorer.py`, and verify crypto shorts are truly blocked.

4. Quarantine FUTURES. Add an explicit futures gate so new futures picks cannot reach execution while n is below the investigation threshold and gap-risk controls are absent.

5. Verify COMMODITY and EQUITY MDD. If COMMODITY MDD is under 20%, document it as T2-quality on PF with WR caveat. If EQUITY MDD is under 20%, the remaining job is a small PF lift, not a redesign.

## P1 Research And Mutation Queue

FOREX deep dive comes first. Export closed FOREX trades, run mutation analysis, and produce `reports/deep_dive_FOREX_2026-05.md` with signal, filter, and universe autopsy. Candidate fixes are ATR-based stops, R:R floor of 1.0, majors-only or tight-spread universe, and London/NY session filtering.

ETF mutation is second. Locate the actual code path behind `extreme_oversold_bounce` or its renamed equivalent. Replace falling-knife oversold entries with breakout confirmation: oversold setup, close above 20-day average, and volume confirmation.

LightGBM schema drift is third. The runtime feature introspection prevents crashes, but the active model appears stale relative to the current feature config. Retrain with the current full feature set after the P0 gates are stable.

## Guardrails For Agents

Do not silently kill FOREX. Use the mutation protocol first.

Do not promote any asset class or filter on n < 100 unless the dashboard explicitly marks it as exploratory.

Do not rely on score-band dashboard claims until closed-pick score persistence is fixed and backfilled or the analysis is restricted to records with issue-time scores.

Do not add new broad integration modules unless they are wired into production scoring or clearly marked opt-in with a wiring plan.

Do not force ETF volume to hit n=100. Wait for organic closes.

## Success Criteria

The next swarm pass should be able to verify:
- Closed picks carry issue-time scoring and trust fields.
- `Smart Picks` is no longer treated as a positive high-conviction signal without fresh proof.
- `quan_engine` live leakage is blocked or calibrated by source and confidence band.
- FUTURES cannot emit execution-ready picks while under quarantine.
- COMMODITY and EQUITY have verified max drawdown values attached to their tier status.
- FOREX has a completed deep dive before any kill-list or mutation decision.
