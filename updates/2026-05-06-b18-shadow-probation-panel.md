# B18 — Shadow Probation Panel Added to /audit Overview

**Date:** 2026-05-06
**PR:** feat/b18-shadow-probation-panel-2026-05-06
**Queue item:** B18 from `reports/REMAINING_ACTION_ITEMS_2026_04_30.md`

## What shipped

Added the missing **Shadow Probation** collapsible panel to the `/audit` Overview tab.

The core B18 logic was already on main (`audit_trail/quality_gates.py::should_shadow_promote`,
`audit_trail/dashboard_generator.py::_apply_shadow_promotion`, 15 unit tests in
`tests/test_shadow_promote.py`). The dashboard payload already carried a `shadow_probation`
key but nothing rendered it. This PR adds the rendering panel.

## Panel behaviour

| State | Display |
|-------|---------|
| `SHADOW_MODE_AUTO_PROMOTE_ENABLED=0` (default) | Panel visible, collapsed, "FLAG OFF" badge, shows candidate list |
| `SHADOW_MODE_AUTO_PROMOTE_ENABLED=1`, no candidates | Panel shows "No strategies qualify yet" |
| `SHADOW_MODE_AUTO_PROMOTE_ENABLED=1`, candidates exist | Table: strategy × raw-emit-count × status (promoted / queued) |

- Panel starts **collapsed** (▶) to avoid visual clutter when flag is off.
- Promoted picks are tagged `shadow_mode=true`, sized at 10% of normal, and excluded from HC.
- Global cap: 5 concurrent shadow picks system-wide.

## Files changed

- `audit_dashboard/template.html` — new `${(function() { ... })()}` block in `renderOverview()` between Asset-Class Health and Coverage Lane Grid panels.

## Wire-Up Rule

Template-only change (read-only rendering). `_apply_shadow_promotion()` is already wired into `generate()` at `dashboard_generator.py:14456`. No new production caller needed.

## Enabling shadow promotion

Set `SHADOW_MODE_AUTO_PROMOTE_ENABLED=1` in the environment where the dashboard generator runs. Earliest recommended: after 14-day soak of the core logic (landed on main ~2026-05-01). Earliest operator enable: **2026-05-15**.

## References

- Core logic: `audit_trail/quality_gates.py:1640` (`should_shadow_promote`)
- Dashboard injection: `audit_trail/dashboard_generator.py:12035` (`_apply_shadow_promotion`)
- Tests: `tests/test_shadow_promote.py` (15 tests, all pass)
- Feedback: `reports/feedback/B18-panel-self-review-2026-05-06.md`
