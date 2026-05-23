# Events Homepage Playwright Swarm Findings

Date: 2026-05-04  
Scope: `https://findtorontoevents.ca/` event surface, filter chips, runtime JS/console reliability, and UX enhancement opportunities.

## Objective

Create a thorough testing gameplan for homepage event filtering and identify practical feature improvements, with special attention to race conditions and console errors previously observed in swarm runs.

## Swarm Conclusions

- The homepage should be tested with a layered Playwright strategy: smoke, deep filter semantics, UX/persistence, and optional a11y/responsive coverage.
- Existing test assets provide a strong baseline:
  - `tests/playwright/test_event_date_filters.spec.ts`
  - `tests/no_js_errors.spec.ts`
- The most fragile areas remain:
  - filter chip state transitions under rapid interaction,
  - counter/card synchronization (oscillation risk),
  - re-render timing around lazy-loaded cards.

## Recommended Test Architecture

- `tests/homepage/events-home.smoke.spec.ts`
- `tests/homepage/events-home.filters.deep.spec.ts`
- `tests/homepage/events-home.ux-persistence.spec.ts`
- `tests/homepage/events-home.a11y-responsive.spec.ts`

Shared helper modules:

- `tests/homepage/helpers/console-network.ts`
- `tests/homepage/helpers/chips.ts`
- `tests/homepage/helpers/cards.ts`
- `tests/homepage/helpers/counters.ts`
- `tests/homepage/helpers/navigate.ts`

## Core Validation Matrix

- Chips and windows:
  - All Dates
  - Today
  - Tomorrow
  - This Week
  - This Month
  - Next Month
- Cross-chip behavior:
  - no dual-active chips,
  - no stale hidden-state leftovers,
  - stable counter after settle window.
- Runtime reliability:
  - capture `pageerror`,
  - capture `console.error`,
  - capture `requestfailed` for critical data/chunk URLs.
- Accessibility/responsive:
  - keyboard chip activation,
  - mobile + desktop viewport sanity,
  - visible focus and no broken controls.

## Enhancement Feature (Requested)

### Max 3 Events/Day/Provider (Eventbrite Exempt)

Design summary:

- Add a setting under bottom gear:
  - "Limit to 3 events/day/provider (Eventbrite exempt)"
- Grouping key:
  - EST date bucket + normalized provider key.
- Enforcement:
  - cap all providers at 3/day,
  - never cap Eventbrite.
- Persistence:
  - logged-in user: server-side preference,
  - guest: localStorage fallback.

## Additional UX Improvements (Swarm Suggestions)

- Per-provider visibility toggles.
- Strong dedupe mode (title/date/venue merge).
- Saved filter presets per user.
- Calendar export (ICS/Google).
- "Hide recurring" and "only free events" toggles.
- Source freshness indicator chips.

## Toronto Source Expansion Candidates

Prioritized shortlist:

1. City of Toronto open-data events feeds
2. Ticketmaster/TicketWeb
3. Meetup
4. Harbourfront Centre
5. TPL programming feeds
6. BlogTO/Toronto.com/NowToronto
7. Songkick/Bandsintown (music vertical)
8. Venue-specific calendars (TIFF/AGO/ROM where allowed)

## Risks and Mitigation

- Hydration/race timing: use stability polling before assertions.
- Live-data volatility: assert invariants over exact titles where possible.
- ModSecurity/chunk issues: keep chunk preflight checks and explicit triage.
- Timezone edge cases: add deterministic EST boundary tests around midnight.

## Outcome

The homepage testing plan is implementation-ready and can be executed incrementally:

- quick smoke + error harness first,
- deep filter matrix second,
- persistence/a11y hardening third.

