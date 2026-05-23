# B18 Codebuff-Style Review — Shadow Probation Template Panel

**Item:** B18 template panel (the only remaining gap in B18)
**Reviewer:** Codebuff-style code architecture review (synthesized)
**Date:** 2026-05-03

## A. Confirmed Assumptions

1. **Correct insertion point.** After line 10449 (end of B2 grid panel `})()`), before
   line 10451 (System Leaderboard). This section is the Overview tab's aggregation zone.
   No overlap with B17 (which adds Honest Readout panel in a different location).

2. **Pattern reuse.** The B2 grid panel at line 10382–10449 uses the IIFE pattern
   `${(function() { ... })()}` which is the correct template-JS approach for this
   dashboard. Shadow Probation panel should follow identical structure.

3. **No new payload fields needed.** `D.shadow_probation.enabled` / `.shadow_picks` /
   `.candidate_strategies` are already in the payload from `dashboard_generator.py:14234`.

4. **Collapse-by-default.** Given the feature is OFF by default, the panel should
   default to collapsed to avoid visual noise. Use a toggle div with localStorage
   persistence (as other collapsible panels do).

## B. Surfaced Contradictions / Blockers

1. **No `py_compile`-equivalent test for template JS.** The template uses embedded
   template-literal JS that isn't statically typechecked. Review carefully for syntax.

2. **Shadow candidates visible even when `enabled=true` but 0 promotions.** The
   `candidate_strategies` list could have entries without any shadow_picks if cap=5 is
   already reached. Distinguish "qualified but capped" from "qualified and promoted."

3. **Shadow badge style.** Active picks table already renders rows without a shadow-mode
   badge. The pick rows don't have a "shadow indicator" either. Consider whether the
   template panel alone is sufficient or if the active picks table also needs a shadow
   badge. Scope: panel-only for this PR; pick-row badge can be follow-up.

## C. Recommended Deltas

1. Use `collapsed` as default state (feature is OFF most of the time).
2. Table for `candidate_strategies` with columns: Strategy | Raw Emits | Closed n | Promoted?
3. List for `shadow_picks` (promoted candidates): Strategy | Symbol | Direction.
4. Orange/amber color for shadow badge (distinct from green=live, red=blocked).
5. Add `data-tip` tooltips explaining the 14-day window and 10-emit threshold.

## D. Net Verdict

**Ready to ship.** Template-only change. The design is clean and additive. No risk to
production behavior (flag=0 by default). Proceed with ~60 lines of template JS.
