# Hermes Code Diff Review — 2026-05-04

Scope: branches `pr1-events-page-tests`, `pr2-audit-pages-gap-analysis`, `pr3-sports-betting-tests`.
Reference fix already on `main`: `d85e6fd6b6e` (`fix/today-tomorrow-week-zero-events-2026-05-04`).

## TL;DR per branch

| Branch | Verdict |
|---|---|
| `pr1-events-page-tests` | **DUPLICATE-DROP** for index.html; **REWRITE-NEEDED** for tests |
| `pr2-audit-pages-gap-analysis` | **DUPLICATE-DROP** for template.html (line-ending churn only); **REWRITE-NEEDED** for tests; KEEP gap-analysis docs |
| `pr3-sports-betting-tests` | **DUPLICATE-DROP** (identical index.html + chips spec to PR1) |

## 1. PR1 — `TORONTOEVENTS_ANTIGRAVITY/index.html` (+100 lines)

The +100 lines are **byte-for-byte the same fix** already merged in `d85e6fd6b6e`:
- Adds `window.__todayOverrideActive__` flag.
- Replaces strict gate at line ~3781 to prefer `eventData.date`/`end_date` YMD over `__parseCardDisplayedDate__`, with overlap semantics for multi-day.
- Adds Today click-override handler mirroring Tomorrow/This Week.
- Same `console.debug('[FILTER] rejected ...')` lines and same comment block ("2026-05-04 P0 fix (BUG-1, surface1_events_audit_2026_05_04.md)").

Recommendation: **drop the index.html change** from PR1/PR3. It will rebase to empty against current `main`.

## 2. PR2 — `audit_dashboard/template.html` (35,172 lines changed)

Diff is **pure CRLF→LF line-ending churn** (file goes 17,592 → 17,580 lines, every line removed and re-added). No semantic changes. `--ignore-cr-at-eol` collapses the diff to near-zero. **This is NOT the HTML nested-comment fix** — Hermes never touched the actual `<!-- ... -->` blocks; the entire file was just re-stamped by an editor with different line endings.

Recommendation: **DUPLICATE-DROP** the template.html change. Do not merge — it will fight every other in-flight edit and trigger conflicts repo-wide.

The supporting docs (`prs/PR2-audit-pages-gap-analysis.md`, `updates/SWARM-ANALYSIS-task2-audit-pages.md`, `updates/kimi-audit-gap-analysis.md`) are KEEPable as analysis artifacts.

## 3. Test selectors — aspirational, will not pass on production

Live `TORONTOEVENTS_ANTIGRAVITY/index.html` confirmed:
- `aria-pressed` — **0 occurrences** anywhere in the file.
- `data-testid="event-card"` — **0 occurrences**.
- Active chip marker is the Tailwind className `from-[var(--pk-600)]` (7 occurrences) — Hermes's own chip spec even declares `const ACTIVE_MARKER = 'from-[var(--pk-600)]';` but never uses it.

### `tests/events-page.spec.ts` (PR1) — predicted failures

| Line | Hermes assertion | Will fail because | Correct selector |
|---|---|---|---|
| 38 | `await expect(filterBtn).toHaveAttribute('aria-pressed', 'true')` | attribute is never emitted | `await expect(filterBtn).toHaveClass(/from-\[var\(--pk-600\)\]/)` |
| 31 | `page.getByText(filter, { exact: true })` for `'today'` | live label is `'🔥 Today'` (emoji + capital T) | use `/Today/i` regex or exact `'🔥 Today'` |
| 53 | `page.getByRole('button', { name: /settings|gear/i })` | gear is an `<a>` / icon, not a labeled button (no `aria-label`) | locate by class/svg or add a testid first |
| 58 | `page.getByRole('dialog', { name: /settings/i })` | settings panel is not a `role="dialog"` | rewrite to actual panel selector |
| 86 | `page.getByTestId('event-card')` | testid does not exist | use `[class*="glass-panel"]:not(.animate-pulse)` (matches what the chips spec uses) |
| 25 | `expect(consoleErrors.length).toBe(0)` on initial load | live page emits non-zero console errors (3rd-party widgets, image 404s) under normal operation | filter to errors from same-origin only |
| 24 | `await new AxeBuilder({ page }).analyze(); ... toHaveLength(0)` | the hand-coded site has known a11y violations (mega-menu, custom controls) | scope axe to a specific region or whitelist known issues |

Net: every parametrized date-filter test will fail at line 38 on the `aria-pressed` assertion.

### `tests/audit-pages.spec.ts` (PR2)

- `[data-testid="rr-filter"]`, `[data-testid="trust-score-filter"]`, `[data-testid="win-rate"]`, `[data-testid="profit-factor"]` — none of these testids are emitted by `audit_dashboard/template.html`. The fallback selectors (`input[placeholder*="R:R"]`, `:has-text("%")`) are guarded by `if (await ... .isVisible())` so the tests will silently no-op rather than fail, giving false-green coverage.
- The "HTML comment bug fixed" assertion (`expect(pageText).not.toMatch(/-->/)`) is a reasonable smoke check and can be kept.
- "Forex tab hidden or marked under review" — current dashboard does not gate Forex this way; assertion will fail or silently skip.

### `tests/test_event_filters_chips.spec.ts` (86 lines, PR1/PR3)

Does **NOT** exist on `fix/today-tomorrow-week-zero-events-2026-05-04` (`git show` returns "exists on disk, but not in 'fix/...'"). So this is genuinely net-new test coverage and is the **one piece worth keeping** from Hermes's work.

It uses the correct selectors:
- `document.querySelector('.glow-text.tabular-nums')` for the counter.
- `[class*="glass-panel"]:not(.animate-pulse)` for visible cards.
- Chip lookup by exact `textContent` including the `'🔥 Today'` emoji form.

This file is **KEEP-AS-IS** and should be cherry-picked onto a fresh branch off current `main` (after dropping the duplicate index.html edit).

## Recommended action

1. Close PR1 and PR3 as duplicates of `d85e6fd6b6e`.
2. Cherry-pick only `tests/test_event_filters_chips.spec.ts` from PR1 onto a fresh branch.
3. Close PR2's template.html change (line-ending churn). Salvage the gap-analysis markdown into `updates/`.
4. Rewrite `tests/events-page.spec.ts` and `tests/audit-pages.spec.ts` with real selectors before merging — current versions are aspirational and will either red-fail on `aria-pressed` or false-green via `isVisible()` guards.

File paths referenced:
- C:\findtorontoevents_antigravity.ca\TORONTOEVENTS_ANTIGRAVITY\index.html
- C:\findtorontoevents_antigravity.ca\audit_dashboard\template.html
- C:\findtorontoevents_antigravity.ca\tests\events-page.spec.ts
- C:\findtorontoevents_antigravity.ca\tests\audit-pages.spec.ts
- C:\findtorontoevents_antigravity.ca\tests\test_event_filters_chips.spec.ts
