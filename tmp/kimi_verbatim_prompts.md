# Kimi's verbatim subagent prompts (captured 2026-05-04)

These are the EXACT prompts Kimi used for 3 specialist subagents that found the synthetic-click swallow bug. Saved here for the persona-extraction subagent to mirror.

## Workflow Kimi followed (5 explicit todos):
1. Create plan.md for code review
2. Clone/download repo and locate filtering code
3. Read and analyze index.html filter logic (lines 3236-4555) using Read tool, multi-pass
4. Create and dispatch 3 PARALLEL specialist review subagents (named "Adam", "Ricardo", "K")
5. Synthesize all 3 reports into FINDINGS.md

## Critical observation: each specialist RAN LIVE TESTS

The RaceCondition Reviewer ("Adam") didn't just static-analyze — they ran actual jsdom + real-browser HTML tests to verify hypotheses:
- Wrote `test_click_real.html`, `test_click_timeout.html`, `test_click4.html`, `test_click5.html`
- Verified empirically that `stopImmediatePropagation()` in capture phase + same-element programmatic `click()` swallows the event
- That's how they found the synthetic-click bug — by RUNNING IT, not reading it

Methodological difference from our static-only swarm: live verification with permission to scaffold throwaway tests.

## Specialist 1 — "Adam" (RaceCondition Reviewer)

VERBATIM PROMPT:

You are reviewing the event filtering logic in /mnt/agents/repos/index.html for race conditions and state management bugs.

### Background
This is a single-page app where imperative vanilla JS overrides/manipulates a Next.js React app's date-filter chip row. The reported bug is that "This Week" and "Next Month" filters can BOTH be active at once, possibly due to lag or the user clicking too quickly.

### Your Mission
Read /mnt/agents/repos/index.html and specifically analyze these sections:
- Lines 4381-4445: _wireThisMonthOverride() — capture-phase click handler for "This Month"
- Lines 4245-4301: _activateNextMonth(), _deactivateNextMonth(), _injectNextMonthChip()
- Lines 4448-4464: _wireSiblingChipDeactivation() — turns off Next Month when siblings clicked
- Lines 4467-4555: init() — MutationObserver setup, debouncing, re-apply timing
- Lines 3416-3807: applyFilters() — the main filter function with many global flags

### Specific Questions
1. Trace the EXACT sequence when a user clicks "Next Month" then immediately clicks "This Week" (within <120ms). Could both __nextMonthFilterActive__ and React's internal "This Week" filter end up simultaneously active? Why?

2. Both _wireThisMonthOverride and _wireSiblingChipDeactivation use useCapture=true (the true param). What is the exact fire order when the user clicks a React chip? Could capture-phase listeners on document race with each other or with the synthetic thisMonthBtn.click() inside _activateNextMonth?

3. _activateNextMonth does thisMonthBtn.click() then setTimeout(applyFilters, 120). What happens if the user clicks "This Week" DURING that 120ms window, BEFORE applyFilters runs?

4. init() starts a chipObserver (MutationObserver) for 30 seconds, AND an observer (MutationObserver) for re-applying filters, AND a capture-phase click listener with 800ms debounce. Could multiple overlapping setTimeout calls from these different sources cause applyFilters to run against a partially-updated DOM, leaving stale global flags?

5. In applyFilters() line 3730-3744, visibility is toggled via CSS classes AND gridItem.style.display. If applyFilters runs twice in rapid succession (e.g., 120ms timeout + 800ms timeout), could the second pass compute shownCount/hiddenCount against a DOM already mutated by the first pass, causing the loop-guard (lines 3756-3806) to bail incorrectly?

6. Look for ANY place where a global flag (__nextMonthFilterActive__, __thisMonthOverrideActive__, __thisMonthHideStreak__) is read and written by multiple async code paths without atomic guards. Flag every such occurrence with severity.

### Output Format
For each finding, provide:
- Severity: CRITICAL / HIGH / MEDIUM / LOW
- Location: Line number(s)
- Root Cause: 2-3 sentence technical explanation
- Fix Recommendation: Specific code change
- Bug Reproduction Steps: Exact user interaction sequence that triggers it

Return your complete analysis as a structured report.

## Specialist 2 — "Ricardo" (DateLogic Reviewer)

VERBATIM PROMPT:

You are reviewing the event filtering logic in /mnt/agents/repos/index.html for date arithmetic and timezone bugs.

### Background
This is a single-page app where imperative vanilla JS overrides/manipulates a Next.js React app's date-filter chip row. The reported bugs:
1. User clicked "Next Month" but didn't see next-month events
2. User clicked "This Month" and saw events from 2025 (already partially fixed per code comments, but may still have edge cases)

### Your Mission
Read /mnt/agents/repos/index.html and specifically analyze these sections:
- Lines 4000-4073: __eventInNextMonth__() — determines if an event falls in next month
- Lines 4090-4239: _renderNextMonthDateBadges() and _removeNextMonthDateBadges()
- Lines 4245-4263: _activateNextMonth() — how the Next Month filter is activated
- Lines 3648-3702: This Month override logic in applyFilters()
- Lines 4321-4337: __parseCardDisplayedDate__() — parses "APR 30" text into YYYY-MM-DD
- Lines 3574-3633: Past events filter in applyFilters()
- Lines 3236-3251: isMultiDayEvent()

### Specific Questions
1. In __eventInNextMonth__ line 4006: var nextM = now.getMonth() + 1; then line 4008: String(nextM + 1).padStart(2, '0'). Trace this carefully. If now is May (month index 4), nextM becomes 5, then nextM + 1 becomes 6, giving month "06" (June). Is this correct? If now is December (month index 11), nextM becomes 12 (which is >11), so it wraps to nextM = 0, nextY++. Then nextM + 1 becomes 1, giving "01" (January of next year). Is this correct? Are there any off-by-one or year-wrap bugs?

2. In __parseCardDisplayedDate__ (line 4333-4336): if (idx < now.getMonth()) year += 1;. If today is May 4 and the card shows "JAN 15", it wraps to next year (2027). But what if the card shows "DEC 25" and today is January 2? idx (11) is NOT < now.getMonth() (0), so year stays at current year (2026). That would parse "DEC 25" as 2026-12-25, but if we're in early January 2027, December 2026 is in the past! Is this a bug? What about November→January wrap?

3. The past-events filter (lines 3595-3633) now ALWAYS runs. It falls back to __parseCardDisplayedDate__ when eventData is unavailable. Given the wrap-around bug in #2, could a card displaying "DEC 25" in January 2027 be parsed as 2026-12-25 and then filtered as "past" (since 2026-12-25 < 2027-01-02)? That would HIDE a legitimate future December 2027 event. Is this a false-positive bug?

4. In _renderNextMonthDateBadges (lines 4138-4140), the title matching uses cardTitle.length >= 8 instead of the _MIN_PARTIAL_NM = 20 used elsewhere. Could this weaker match cause wrong badges to be applied to cards with similar 8-character prefixes?

5. In isMultiDayEvent() (lines 3236-3251), new Date(event.date).toDateString() is used. If event.date is an ISO string like "2026-05-04T00:00:00Z", new Date() parses it as UTC, then toDateString() converts to local time. In Toronto (EDT, UTC-4), this becomes May 3 8pm, so the date string is "Mon May 03 2026". If the event's actual local start is May 4, this causes an off-by-one. Could this make single-day events appear as multi-day or vice versa?

6. Look for ANY place where new Date(string) is called without explicitly handling the UTC↔local timezone shift. The code comments acknowledge this risk (e.g., line 3576-3578) but check whether all instances are actually safe.

### Output Format
For each finding, provide:
- Severity: CRITICAL / HIGH / MEDIUM / LOW
- Location: Line number(s)
- Root Cause: 2-3 sentence technical explanation
- Fix Recommendation: Specific code change
- Affected Scenario: Which user action / date combination triggers this

Return your complete analysis as a structured report.

## Specialist 3 — "K" (DOM React Reviewer)

VERBATIM PROMPT:

You are reviewing the event filtering logic in /mnt/agents/repos/index.html for React DOM integration and mutation observer bugs.

### Background
This is a single-page app where imperative vanilla JS overrides/manipulates a Next.js React app's date-filter chip row and event grid. The vanilla JS injects custom chips, toggles CSS classes on React-rendered cards, hides/shows parent grid items, and overlays date badges.

### Your Mission
Read /mnt/agents/repos/index.html and specifically analyze these sections:
- Lines 4467-4555: init() — hydration detection, MutationObserver setup, debouncing
- Lines 4275-4302: _injectNextMonthChip() — injecting a custom chip into React's chip row
- Lines 4090-4239: _renderNextMonthDateBadges() — overlaying badges on React cards
- Lines 3416-3807: applyFilters() — mutating React card visibility
- Lines 4556-4600: __whenReactHydrated__ — hydration detection

### Specific Questions
1. The chipObserver (line 4483) watches document.body with {childList: true, subtree: true} for 30 seconds. If React re-renders the chip row (common when user clicks a date filter), the observer fires and _injectNextMonthChip() runs. But _injectNextMonthChip removes and re-inserts the Next Month chip into the DOM. Could this removal+insertion itself trigger the MutationObserver again, causing an infinite loop or double-injection before the 250ms debounce kicks in?

2. _injectNextMonthChip checks existing && existing.previousElementSibling === thisMonthBtn (line 4279). If React re-renders and the chip row structure changes (e.g., "This Month" is no longer the immediate previous sibling because React added an "Ongoing" toggle between them), would the Next Month chip be incorrectly removed and never re-injected correctly?

3. In _renderNextMonthDateBadges (lines 4207-4226), the code walks card leaf elements and hides React's intrinsic date label by setting style.visibility = 'hidden'. React may later reconcile the card and reset inline styles. Could React's reconciliation wipe out the visibility: hidden on the date label, causing both the original date and the badge to show simultaneously?

4. applyFilters() (lines 3738-3742) sets gridItem.style.display = 'none' on the parent .group wrapper. React's reconciliation might not expect this inline style mutation. If React later updates the card's props/state and re-renders, could it reset the display property, causing hidden cards to reappear while still having the event-card-hidden class?

5. The capture-phase click listener at line 4539-4552 has an 800ms timeout before calling safeApply(). But the _wireThisMonthOverride handler (line 4373) also calls applyFilters() after 200ms. If a user clicks a React chip, which of these fires first? Could they fire in the wrong order (e.g., 800ms listener runs against a stale DOM because the 200ms handler already mutated it)?

6. __whenReactHydrated__ uses a polling loop with requestAnimationFrame. If the tab is backgrounded, rAF is throttled or paused. The 5-second hard fallback (line 4598) uses setTimeout. Could init() run before React has actually hydrated the chip row, causing _injectNextMonthChip to fail because thisMonthBtn doesn't exist yet?

7. Look for any scenario where React's lazy-loaded cards (fetched on scroll) arrive AFTER a filter is active, but the MutationObserver fires safeApply() too early (at 500ms debounce) before React has finished inserting ALL cards in the new batch. Could this cause the loop-guard to trigger prematurely because only a few cards have been inserted?

### Output Format
For each finding, provide:
- Severity: CRITICAL / HIGH / MEDIUM / LOW
- Location: Line number(s)
- Root Cause: 2-3 sentence technical explanation
- Fix Recommendation: Specific code change
- Affected Scenario: Which user interaction / React lifecycle state triggers this

Return your complete analysis as a structured report.

## Pattern recognition

What every Kimi prompt has in common:

1. Background section with reported user-visible symptoms
2. Mission section with EXACT line ranges per code section to read (no "find the relevant code" — they pre-located it)
3. Specific Questions section — numbered, scenario-based, with concrete trace-this-exactly tasks (not open-ended "review the code")
4. Output Format section — strict template with severity / location / root cause / fix / scenario
5. Permission to run live tests — Adam ran browser/jsdom tests to verify hypotheses

CRITICAL difference from our previous prompts: ours said "review this diff" (static). Kimi's said "trace the EXACT sequence when user clicks X then Y within 120ms" (dynamic, scenario-driven, with permission to verify in a browser).
