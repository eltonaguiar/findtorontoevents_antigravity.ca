# B18 — Shadow Probation Template Panel (2026-05-03)

## What changed

Added the missing UI panel for the B18 Shadow Probation feature in
`audit_dashboard/template.html`.

The B18 backend (quality_gates logic, dashboard_generator emission, HC
exclusion rule, and 15 unit tests) was already on main. This PR adds the
only remaining gap: a collapsible "Shadow Probation" panel on the /audit
Overview tab that renders the `D.shadow_probation` payload key.

## Panel behavior

| State | What renders |
|---|---|
| `SHADOW_MODE_AUTO_PROMOTE_ENABLED=0` (default) | Collapsed header with "OFF" badge; expanded view explains the feature and the chicken-and-egg problem it solves |
| Flag `=1`, 0 candidates | "No zero-history strategies currently qualify" message |
| Flag `=1`, candidates present | Table: Strategy / Raw Emits / Closed n / Promoted? + promoted shadow picks list |

## Files changed

- `audit_dashboard/template.html` — added Shadow Probation collapsible panel
  (IIFE pattern, ~70 lines, inserted between the B2 Coverage Lane Grid and
  the System Leaderboard)
- `reports/feedback/B18-self-review-claude-2026-05-03.md` — self-review
- `reports/feedback/B18-codebuff-review-2026-05-03.md` — codebuff-style review

## Tests

Existing `tests/test_shadow_promote.py` (15/15 pass) covers all backend
logic. The template panel has no new unit tests — it is pure rendering
of the already-validated `shadow_probation` payload key. Playwright
smoke tests (`.github/workflows/sports-smoke-and-e2e.yml`) cover the
template render path.

## Risk

LOW. Additive panel only. Feature flag default=0; zero behavior change
to pick generation, scoring, or HC gating.

## Wire-Up Rule

Satisfied. Production caller is `dashboard_generator.py:14229`
(`_apply_shadow_promotion` invocation). Template panel is a read-only
renderer of the already-wired payload key. No new integration module.
