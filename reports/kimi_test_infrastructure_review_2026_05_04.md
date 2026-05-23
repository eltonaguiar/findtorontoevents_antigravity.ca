# Kimi Playwright Test Infrastructure — Deep Review

**Date:** 2026-05-04
**Reviewer:** Claude (Opus 4.7, 1M ctx)
**Source archive:** `reports/kimi_swarm_archive_2026_05_04/findtorontoevents_swarm/`
**Cross-checked against:** `TORONTOEVENTS_ANTIGRAVITY/index.html`, `audit_dashboard/template.html`, `live-monitor/sports-betting.html`
**Prior context:** `reports/hermes_code_diff_review_2026_05_04.md` (Hermes used `aria-pressed='true'` on chip filters — wrong; live page uses Tailwind `from-[var(--pk-600)]`)

---

## 0. Summary verdict

Kimi's test infrastructure is **substantially better than Hermes's** for this codebase. Critically, Kimi did **NOT** repeat Hermes's chip-filter selector mistake: a repo-wide grep across `tests/*.spec.ts` for `aria-pressed` returns **zero matches**. Kimi targets chips and category pills via `text=...` locators (e.g. `text=Today`, `text=This Week`, `text=Music`), which actually work against the React-injected chips in the live homepage.

Recommend cherry-picking ~70% of the package: the entire `console-error-utils.ts`, the `playwright.config.ts` (lightly tweaked), and **events.spec.ts + sports-betting-advanced.spec.ts as templates** (selectors mostly correct, screenshot path needs change). Reject blind adoption of `audit.spec.ts` (selectors generic, doesn't know our actual `.sp-asset-btn` / `data-sp-asset` schema) and the basic `sports-betting.spec.ts` (largely superseded by `-advanced`).

---

## 1. Salvageable as-is (verbatim or one-line tweak)

### 1a. `tests/console-error-utils.ts` — **COPY VERBATIM**
- **Path target:** `tests/console-error-utils.ts` (new file)
- **Why:** Self-contained, zero project-specific assumptions, framework-agnostic. The `KNOWN_BAD_PATTERNS` array (lines 70–87) is genuinely useful; the `counter\s*oscillation` regex at **line 71** is real and matches what Kimi's MASTER_REPORT.md claims. Tracker covers `console`, `pageerror`, and `requestfailed` events with severity grouping, ISO timestamps, and a clean `getReport()` formatter. The `assertNoConsoleErrors` + `logConsoleErrors` (hard vs. soft) split is the right ergonomic.
- **Tweak:** None required. Optional — strip the two emoji glyphs in `getReport()` (lines 153, 157, 187) since CLAUDE.md says no emojis in files unless requested.

### 1b. `playwright.config.ts` — **COPY WITH 3 ONE-LINE TWEAKS**
- **Tweak 1:** Change `BASE_URL` default (line 17) from `https://findtorontoevents.ca` to use both `BASE_URL` and a fallback for the audit subdomain — we have multiple surfaces.
- **Tweak 2:** Drop `--disable-web-security` (line 70). We don't need it; it's a foot-gun on CI.
- **Tweak 3:** Drop the unused `declare module` block (lines 23–27) — it references `_consoleTracker` but the config doesn't actually attach it via fixtures. Dead code.
- **Keep:** the 3-project matrix (Desktop Chrome / Firefox / Mobile Safari iPhone 12), `retain-on-failure` traces, `only-on-failure` screenshots, `IS_CI ? 4 : undefined` worker model, and the JSON reporter for CI artifact diffing.

### 1c. `package.json` test scripts — **MERGE ENTIRELY**
- The `test:events / test:audit / test:sports / test:ui / test:debug` script names are sensible. Merge into our existing `package.json` if any (we don't have one at repo root currently). If creating new, take the whole `scripts` block and `devDependencies`.

---

## 2. Salvageable with rewrite (selectors need fixing)

### 2a. `tests/events.spec.ts` — **ADAPT, DON'T COPY**
- **Verdict:** structure is correct (DATE_FILTERS / CATEGORIES / TOGGLES driven loops), but several locators target a generic Next.js shell that isn't quite our hand-coded page.
- **Rewrites needed:**
  - **Line 71** `[data-testid='event-grid'], .event-grid, [class*='grid'], text='No events found'` — our live page uses `[class*="glass-panel"]:not(.animate-pulse), [class*="event-card"], [class*="EventCard"]` (see `index.html:2339, 3469, 4223`). Replace.
  - **Line 82** `screenshot path` — hardcoded `/mnt/agents/output/...` (Kimi sandbox path). Replace with `test-results/screenshots/events-${name}.png` (Playwright-native).
  - **Lines 56–60 TOGGLES** — labels like "Sold Out Hidden" / "Expensive Hidden" / "Ongoing Hidden" are guesses. Verify against our actual toggle labels in `index.html` before adopting; the mega-menu chip text on the live page uses different wording.
  - **Lines 27–34 DATE_FILTERS** — text labels (`Today`, `Tomorrow`, `This Week`, `This Month`, `Next Month`, `All Dates`) DO match the live React chips (confirmed via `index.html:3478-3479` showing `_findReactChipByText('This Week')`). Keep as-is.
  - **Lines 36–53 CATEGORIES** — list is reasonable but should be derived from data, not hardcoded.

### 2b. `tests/sports-betting-advanced.spec.ts` — **ADAPT, HIGH VALUE**
- **Verdict:** This is the most interesting file in the bundle. The `wilsonScoreInterval` helper (line 24), `mockTheOddsApiResponse` (line 42), `mockArbitrageOddsResponse` (line 127), `mockSteamMoveOddsHistory` (line 168), and `setupMockTheOddsApi` (line 203) are reusable utilities even if the test bodies need rewrite.
- **Rewrites needed:**
  - The `.bet-card` selector (lines 351, 416, 433, 447, 983, 993) does **not** exist in our `live-monitor/sports-betting.html` — our class is `.pick-card` / `.pick-card-enhanced` (confirmed `sports-betting.html:158, 211, 376, 2207`). Global rename `.bet-card` → `.pick-card-enhanced` and audit each assertion.
  - `button:has-text("Today's Picks")` / `button:has-text("My Bets")` / `button:has-text("Settled")` — verify these tab labels exist on our page.
  - `text=/API Credits/i`, `text=/Bankroll/i`, `text=/Last refresh/i`, `text=/Stale picks/i` — these all DO exist (`sports-betting.html:419, 522, 524, 551`). Keep.
  - `.finished-toggle-btn[aria-pressed="true"]` is correct against live page (line 388) — Kimi happens to skip this selector but it's the one place where `aria-pressed` is actually live.

### 2c. Useful helper patterns to extract regardless of test
- `waitForEventGridStable(page)` pattern (events.spec.ts:66) — adapt with our real grid selector.
- `setupMockTheOddsApi(context, body, status)` route-stub pattern (sports-betting-advanced.spec.ts:203) — clean, reusable.

---

## 3. Reject (do not adopt)

### 3a. `tests/audit.spec.ts` — **REJECT AS-IS**
- Selectors are generic shell-shots: `.asset-card, [data-testid='asset-card'], table, canvas, .audit-table` (line 92). Our actual asset filter buttons are `.sp-asset-btn[data-sp-asset="CRYPTO|EQUITY|FOREX|...]` per `template.html:1368-1374`. Kimi never discovers this.
- Tests like `getByRole("button", { name: /export.*active/i })` (line 317) are fishing — our export button has a specific `id` we should target.
- The audit dashboard is 17,628 lines of bespoke markup; a 645-line "best-effort generic" suite is anti-value. Better to write fresh tests from `template.html` IDs. **Salvage only:** the `KNOWN_BAD_PATTERNS` integration pattern and the `tracker.getReport()` console-print idiom — both are in `console-error-utils.ts` already.

### 3b. `tests/sports-betting.spec.ts` — **REJECT (use -advanced instead)**
- Largely a subset of `sports-betting-advanced.spec.ts` with the same `.bet-card` selector bug, fewer mocks, and no Wilson CI. Adopting both is duplication. Pick `-advanced` and drop the basic file.

---

## 4. package.json + playwright.config.ts decision

**Adopt both, with the tweaks in §1b/1c.** We do not currently have a Playwright config at repo root (verified via Glob — search `playwright.config*` returns archive-only). Bringing Kimi's config in gives us the 3-browser matrix and reporter setup for free. The `package.json` is 31 lines and only declares `@playwright/test`, `typescript`, `ts-node` — minimal blast radius. Don't blanket adopt the `name`, `description`, or `directories` fields if a root `package.json` already exists; just merge `scripts` + `devDependencies`.

---

## 5. Top 5 specific cherry-picks (file:line → why)

1. **`console-error-utils.ts:70-87`** — `KNOWN_BAD_PATTERNS` regex array. Battle-tested coverage for React/Next/network/hydration errors. The `counter\s*oscillation` line 71 regex is the load-bearing assertion for our chip-injection bug class. Confirmed present (Kimi's MASTER_REPORT claim was accurate).
2. **`console-error-utils.ts:93-208`** — entire `createConsoleErrorTracker(page)` factory. Triple-event subscription (`console` / `pageerror` / `requestfailed`) with severity-keyed grouping and a deterministic `getReport()`. Drop in as-is.
3. **`sports-betting-advanced.spec.ts:24-39`** — `wilsonScoreInterval(wins, total, confidence)` pure function. 15 lines, no deps, unit-testable. Reusable in audit dashboard win-rate badges, sports-pick gates, and any place we display `n` wins of `m`.
4. **`sports-betting-advanced.spec.ts:203-220`** — `setupMockTheOddsApi(context, responseBody, status)` `context.route` stub. Clean idiom for fault-injection in CI without touching live `findtorontoevents.ca/api/sports/*`.
5. **`playwright.config.ts:75-95`** — the 3-project matrix definition (Desktop Chrome 1280x720, Desktop Firefox 1280x720, iPhone 12 Mobile Safari). Matches what `sports-smoke-and-e2e.yml` already implies; codifies it.

---

## Cross-reference: Hermes vs. Kimi selector accuracy

| Selector axis              | Hermes              | Kimi                            | Live page ground truth                          |
|----------------------------|---------------------|----------------------------------|-------------------------------------------------|
| Chip active state          | `aria-pressed=true` (WRONG) | `text=Today` etc. (CORRECT) | Tailwind `from-[var(--pk-600)]` class          |
| Event card selector        | n/a                 | `[data-testid='event-grid'], .event-grid` (PARTIAL) | `[class*="glass-panel"], [class*="event-card"]` |
| Pick card (sports)         | n/a                 | `.bet-card` (WRONG)             | `.pick-card`, `.pick-card-enhanced`             |
| Finished-toggle button     | n/a                 | not tested                      | `.finished-toggle-btn[aria-pressed]` (real)     |

Kimi's chip-filter selectors are **right by accident** — they target visible text rather than active-state CSS, sidestepping the Tailwind variable issue. This is portable across React, vanilla, and any future rewrite. Recommend codifying "prefer text-based locators for chips/pills" as a project test convention.

---

## Suggested adoption order (3 PRs)

1. **PR A (low-risk):** Add `tests/console-error-utils.ts` verbatim + minimal `playwright.config.ts` (Chrome only) + root `package.json` scripts. Wire one smoke test that just loads the homepage and asserts no `KNOWN_BAD_PATTERNS` matches. Validates infra without touching selectors.
2. **PR B (medium):** Adopt `events.spec.ts` with §2a rewrites. Add the Firefox + Mobile Safari projects.
3. **PR C (medium):** Adopt `sports-betting-advanced.spec.ts` with §2b `.bet-card → .pick-card-enhanced` rename. Pull in `wilsonScoreInterval` as `tests/utils/stats.ts`. Skip `audit.spec.ts` and basic `sports-betting.spec.ts` entirely.

End of review.
