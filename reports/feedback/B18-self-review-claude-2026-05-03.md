# B18 Self-Review — Shadow-Mode Auto-Promotion for Zero-History Strategies

**Item:** B18 from `reports/REMAINING_ACTION_ITEMS_2026_04_30.md`
**Reviewer:** Claude (self-review in absence of external AI access)
**Date:** 2026-05-03

## A. Confirmed Assumptions

1. **File paths correct.** `audit_trail/quality_gates.py:1623` contains `should_shadow_promote()`;
   `audit_trail/dashboard_generator.py:11813` contains `_apply_shadow_promotion()`;
   `tools/dashboard_hc_rules.py:374` excludes shadow picks from HC. All confirmed on main.

2. **Tests pass.** `tests/test_shadow_promote.py` — 15/15 pass locally.

3. **Payload key present.** `audit_dashboard/data/dashboard_data.json` contains
   `"shadow_probation": {"enabled": false, "shadow_picks": [], "candidate_strategies": []}`.
   The generator already emits the data.

4. **Missing piece is template UI only.** `audit_dashboard/template.html` (17,537 lines)
   has zero references to `shadow_probation`. The backend emits the data but the dashboard
   doesn't render it.

5. **Wire-Up Rule satisfied.** B18 is purely informational when flag=0 (no behavior
   change). When flag=1 it adds shadow picks to the active list — the generator call site
   at `dashboard_generator.py:14229` is the production caller. Rule satisfied.

6. **Risk is LOW for template-only addition** (additive panel, no logic change, flag=0 by default).

## B. Surfaced Contradictions / Blockers

1. **Template panel missing is the only gap.** All other B18 acceptance criteria are met.

2. **B17 (PR #665, open) also touches `template.html`.** Potential merge conflict if
   B17 lands before B18. The Shadow Probation panel should go in a distinct section
   (after the Asset-Class × TF grid, before the leaderboard) that B17 doesn't touch.

3. **`candidate_strategies` only populated when flag=1.** The panel should render gracefully
   when `enabled=false` — show a collapsed note explaining the feature is OFF.

## C. Recommended Deltas

1. Add a collapsible Shadow Probation panel after the B2 grid panel (line ~10449).
2. When `shadow_probation.enabled = false`: show collapsed panel with "Feature OFF — flip
   SHADOW_MODE_AUTO_PROMOTE_ENABLED=1 to activate" + explanation of the chicken-and-egg
   problem it solves.
3. When `enabled = true`: show candidate strategies table + active shadow picks with
   `🕵 Shadow` badge.
4. No need to add new tests — template JS is covered by Playwright (existing smoke test
   would detect a JS crash).

## D. Net Verdict

**Ready to ship.** The template-only gap is small (~50 lines of JS template). No code
logic change. Prereq (B16 on main) satisfied. Low risk. Proceed.
