# HC Gate Placeholder Clone Feedback

**Date:** 2026-04-22  
**Scope:** Review of the proposed `HIGHFWWRABV55_SCOREABOVE50`-style routing logic against current repo data and gate code.  
**Status:** Blocker confirmed.

## What I checked

- `audit_dashboard/hc_filter.js`
- `audit_dashboard/data/edge_report.md`
- `updates/2026-04-17-edge-deepscan-5-filter-catalog.md`
- `alpha_engine/data/active_picks.json`
- `copy_trader_intel/strategy_reverse_engineer.py`
- `docs/ACCOUNT_TRADING_PERFORMANCE_ANALYSIS_2026-04-05.md`
- `updates/2026-04-21-deep-strategy-investigation-by-asset-class.md`
- `updates/perf_review_2026-04-21_cycle10.md`

## Feedback

The core claim is correct: the gate-passing copy-trader picks do not read like validated edge. They read like placeholder or mechanically propagated stats, and the current snapshot is even less tradeable than the original note suggests.

Three things make this a hard blocker:

1. The **real HC filter** is stricter than the account label semantics.  
   `audit_dashboard/hc_filter.js` requires score/trust/forward-WR/regime/consensus/walk-forward conditions. In the current `alpha_engine/data/active_picks.json` snapshot, running the exported `filterHighConvictionOrdered()` returns **0 passes on 169 active rows**. Separately, `audit_dashboard/data/edge_report.md` reports **1 / 31 active picks pass HC now (3.2%)** on its 2026-04-20 dashboard snapshot. Either way, the current live book does **not** support a broad HC-style routing claim.

2. The copy-trader clone rows show a repeated placeholder pattern across unrelated symbols.  
   Current examples from `active_picks.json`:
   - `clone_hl_copy_PensionFund_24M` LONG: `elite_score=100`, `forward_trades=100`, `forward_wr=100%` on BTC, BNB, AVAX, LINK, NEAR, SUI, RENDER, HYPE, ONDO
   - `clone_hl_copy_lb_None` LONG: `elite_score=100`, `forward_trades=100`, `forward_wr=100%` on the same 9-symbol cluster
   - `clone_hl_copy_lb_None` SHORT: `elite_score=80`, `forward_trades=80`, `forward_wr=80%` on BTC, ADA, XRP, SOL, DOGE, AVAX, LINK, NEAR, SUI, FET
   - `clone_hl_copy_Auros_66M` LONG: `elite_score=71`, `forward_trades=71.43`, `forward_wr=71.43%` on 11 symbols
   - `clone_hl_copy_whale_433roi` SHORT: `elite_score=85`, `forward_trades=85.71`, `forward_wr=85.71%` on RENDER and ONDO

   `elite_score ~= forward_trades ~= forward_wr_pct` across dissimilar symbols is not a believable computed edge signal. It is a scoring artifact until proven otherwise.

3. The same clone cohort is explicitly marked as bypassing safety gates.  
   `copy_trader_intel/strategy_reverse_engineer.py` assigns:
   - `EXEMPT_FROM_SAFETY_GATES` when `total_wr > 0.65` and `pf > 2.0`
   - `REDUCED_SAFETY_GATES` when `total_wr > 0.55` and `pf > 1.5`

   The active clone rows carry those flags directly in `clone_safety_mode`. Routing safety-exempt clone picks into an account whose name implies strict HC validation is internally inconsistent.

## Additional integrity problems

- The clone rows I inspected do **not** carry stable HC inputs like `trust_tier` or `trust_score`, even though HC gating depends on them.
- The 2026-04-17 catalog already concluded that `HIGHFWWRABV55_SCOREABOVE50_V3` has **no programmatic backing** in repo code or config. It is a manual label, not an audited filter contract.
- Repo evidence continues to point in the opposite direction of "confidence-like labels imply edge":
  - `updates/2026-04-21-deep-strategy-investigation-by-asset-class.md` shows **confidence is anti-predictive on crypto**
  - `updates/perf_review_2026-04-21_cycle10.md` records system-wide performance around **31.1% WR / PF 0.72**
  - `docs/ACCOUNT_TRADING_PERFORMANCE_ANALYSIS_2026-04-05.md` documents severe **LONG source bias** in the live stack

## Practical conclusion

I would not trade the `clone_hl_copy_*` cohort into an HC-branded account without an explicit override.

The cleanest next move is still:

1. **Fix the placeholder-stat / clone-stamping pipeline first.**
2. **Define account filters explicitly in code/config** instead of inferring them from portfolio names.
3. **Audit candidate cohorts against closed-book edge** before routing them into paper accounts.

If trading must continue before the pipeline is fixed, the only defensible options are:

- trade the single verified HC pass from the audited dashboard snapshot, or
- use a different account label that does not claim `fwd_wr >= 55` / `score > 50` semantics, or
- record an explicit override that acknowledges the clone rows are placeholder-shaped and safety-exempt.

## What changed

- Added this review note to `updates/` to document the blocker and the current evidence.
- No code paths were changed in this update.

## Verification

Verified by direct inspection plus local read-only queries over current repo data:

- inspected HC gate defaults and exports in `audit_dashboard/hc_filter.js`
- read current automated audit in `audit_dashboard/data/edge_report.md`
- read prior filter-catalog findings in `updates/2026-04-17-edge-deepscan-5-filter-catalog.md`
- queried `alpha_engine/data/active_picks.json` to enumerate clone row patterns and current HC pass count
- inspected clone safety-mode generation in `copy_trader_intel/strategy_reverse_engineer.py`
