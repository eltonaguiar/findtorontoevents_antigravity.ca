# 2026-10-20 — Dashboard Display-Honesty Rules (Operator Verdict #10)

## What was requested

Operator verdict instruction #4:
> **Doc: hide WR when n<20, show PF/MDD with every WR, no READY/ENTER wording.**

This is a display-honesty change for the `/audit` dashboard: win-rate must not be
shown on statistically trivial samples, PF/MDD must always accompany any shown WR,
and over-promising "READY"/"ENTER" labels must be neutralized.

## What was changed

### 1. `audit_dashboard/ueps_section_renderer.py` — `render_aggregate_stat_block`

The per-strategy aggregate stats block (WR/PF/MDD/Sharpe, each with `(n=…)`)
previously rendered every non-`None` stat independently. Now:

- **Hide WR when n<20.** Added `MIN_WR_N = 20`. WR is only rendered when
  `wr is not None` AND (`n` is unknown OR `n >= 20`). When `n < 20`, the WR span
  is suppressed (PF/MDD/Sharpe still shown independently).
- **PF/MDD ride along with WR.** `pf_visible = pf is not None or wr_visible` and
  `mdd_visible = mdd is not None or wr_visible`. So whenever WR is shown, PF and
  MDD are forced to render too — falling back to `n/a` placeholders if the raw
  value is missing. This prevents a display where WR appears without its
  risk/quality context.
- The "no useful fields" empty-state branch now keys off the visibility flags.

### 2. `audit_dashboard/paper_pilot.html` — `gateBadge`

The badge label for `READY_FOR_LIVE` was plain `READY`. Changed to `GATE PASSED`
(neutral status, no "READY" wording). The internal machine verdict constant is
unchanged.

### 3. `audit_dashboard/funds.html` — verdict vocabulary

The top-picks card engine used an actionable `ENTER NOW` verdict headline and
advertised an `ENTER / WAIT / AVOID` framing:

- `ENTER NOW` verdict string → `STRONG SETUP` (both occurrence sites). CSS class
  `verdict-enter` and icon unchanged, so styling/rendering is unaffected.
- Header comment and the intro copy "honest verdict (ENTER / WAIT / AVOID)" →
  "neutral status (SETUP / MONITOR / AVOID)".
- `SET LIMIT` / `WAIT` / `AVOID` verdict strings left intact (not READY/ENTER wording).

## Scope notes

- The asset-class health block in `audit_trail/dashboard_generator.py` already
  suppresses *all* stats below its documented `min_display_n = 10`
  ("insufficient_data"). That threshold was intentionally NOT bumped to 20: the
  operator rule is specifically WR-scoped, and raising the aggregate gate would
  also hide PF/MDD — contradicting "show PF/MDD with every WR".
- READY/ENTER mentions inside prose/state-machine descriptions (e.g. `OOS_READY`,
  `MONEY_READY`, `READY_TO_PROMOTE`, `FILTER_READY_SMALL_SIZE`) remain for now;
  they describe named state-machine states, not actionable trade instructions. The
  actionable English badges (READY, ENTER NOW) are the ones neutralized here.

## Verification

- Added 4 tests to `tests/test_ueps_section_renderer.py`:
  - WR hidden at `n=19`, PF/MDD still shown.
  - WR shown at `n=20` (boundary).
  - PF/MDD forced to render (with `n/a` placeholders) whenever WR is shown.
  - Unknown `n` keeps WR visible (cannot prove `n<20`).
- `python3 -m pytest tests/test_ueps_section_renderer.py -q` → **23 passed**.
- `grep` confirms no remaining `'ENTER NOW'` verdict strings in `funds.html`.
