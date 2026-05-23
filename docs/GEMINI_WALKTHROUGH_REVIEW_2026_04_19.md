# Review — Gemini Advanced Analytics Walkthrough (2026-04-19)

**Source:** `~/.gemini/antigravity/brain/ac32b466-.../artifacts/walkthrough.md.resolved` + companion `implementation_plan.md.resolved` and `performance_deep_dive_report.md.resolved`.

**Reviewer:** Claude Opus 4.7 (1M context), findtorontoevents.ca/audit repo.

## Quick verdict per section

| Gemini section | Verdict | Caveat |
|---|---|---|
| §1 Golden Combo (cta_cross_asset_tsmom + futures_momentum, PF 13.55) | ⚠️ Needs n disclosure and FDR correction | Small-n combos can look spectacular; Mercury's Round-2 FDR on 45 parallel tests showed zero clearing 5% BH |
| §1 Toxic Overlap (retired strategies 0-20% WR when they agree) | ✅ Directionally correct | Reinforces existing retirement decisions; not actionable new info |
| §2 Strategy decay (11 flagged strategies, st_fear_greed_contrarian 10.5% / 390 trades) | ✅ Confirmed | st_fear_greed_contrarian is already retired; cross-check the others against `_RETIRED_STRATEGIES` / `_PAPER_ONLY_STRATEGIES` before re-flagging |
| §3 "<3 pair closes" fallback | ✅ Correct explanation | Not a bug; intended fallback to strategy-wide WR |
| §4 Near-miss MFE/MAE missing | ✅ Accurate | Proposal to log MFE/MAE live in `alpha_engine` is sound medium-effort work |

## Reconciliation with independently-run numbers

Independent run: [TRACK_PERCENT_VS_SMART_VS_VERIFIED_2026_04_19.md](TRACK_PERCENT_VS_SMART_VS_VERIFIED_2026_04_19.md).

| Claim | Gemini | Claude verification | Note |
|---|---|---|---|
| Track% this-week WR / PF | 54.2% / 1.99 | 52.3% / 1.96 | Close match (strat_fwd_wr field) |
| Track% last-week WR / PF | 64.9% / 3.92 | 64.9% / 3.92 | Exact match |
| Track% this-month WR / PF | 54.0% / 2.13 | 52.5% / 2.12 | Close |
| Smart Picks 30d PF | 3.01 | **11.04** (at-issue eval) | **Gemini under-states**: evaluating `passes_smart_gate` on closed-status picks rejects them via `passes_active_gate`. Must clone pick with `status='ACTIVE'` to evaluate at-issue quality |
| Verified Alpha 30d trade count | 2,145 | 498 | **3x discrepancy**. Possible cause: different PROVEN-tier definition (Gemini may be counting `trust_score` thresholds rather than strict `trust_tier=='PROVEN'`) |
| Missing Track% picks | 11/3,529 (0.3%) | 1/3,313 (0.03%) | Gemini's cold-start claim (`tsmom_volscaled`, `kalshi_mtf_consensus`) doesn't match current snapshot. Likely stale data or different denominator |
| "+16,264% Net PnL" this-week | headline | +163% ΣPnL% scaled to bp | Unit confusion; display on dashboard should clarify |

## Additional findings Gemini missed

1. **Verified Alpha bleed likely = registry tagging regression.** 498 PROVEN picks in last 7 days, WR 14.5%, PF 0.17 is not consistent with historical PROVEN badge meaning. Either (a) the registry is backfilling PROVEN onto already-closed losers, or (b) demotion logic isn't firing when strategies drift. Phase D of the enhancement plan should investigate before Phase A.

2. **`forward_win_rate` field is DEAD.** 0/3500+ picks have it populated. Everything on the dashboard is using `strat_fwd_wr` (strategy-level). Any downstream code expecting `forward_win_rate` is silently getting zeros. Search for references and fix.

3. **Picks with `forward_wr` ≠ `strat_fwd_wr` by >10pp = 386 picks.** Not a bug — it's symbol specialization. But it means the two "Track %" definitions diverge for ~12% of picks. The dashboard should clarify which it's showing.

## Recommendations

**Ship immediately:**
- Fix `forward_win_rate` field name if any code path still references it (1-line grep)
- Add sample-size (n) and BH-FDR q-value columns beside any consensus-combo UI to prevent small-n mirage claims
- Cross-check the 11 decaying strategies against current `_RETIRED_STRATEGIES` and `_PAPER_ONLY_STRATEGIES` — any not already there should be paper-flagged

**Investigate before acting:**
- The PROVEN tier bleed (Phase D of enhancement plan)
- Golden Combo with n-disclosure: if n < 30 on (cta_cross_asset_tsmom + futures_momentum), treat as a hypothesis, not an edge

**Defer:**
- MFE/MAE watermark logging — nice-to-have, medium effort (alpha_engine active-pick loop modification + schema bump). Only justified after Phase A/B scoring fixes ship, since those have higher calibration leverage

## Gemini's open question on retroactive near-miss backfill

> "Do you want me to write a script to retroactively check historical price data for near misses, or should I just focus on the consensus edge and strategy decay analysis for now?"

**Recommendation:** decline the retroactive backfill. Cost (external API calls × 3500 trades) vs value (one-time diagnostic) doesn't justify it. Instead, add MFE/MAE logging to the forward path so future closed picks carry it natively. Use the decay analysis time for Phase A scoring fixes — higher leverage.
