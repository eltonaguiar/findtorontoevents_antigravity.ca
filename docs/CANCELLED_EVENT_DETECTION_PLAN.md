# Cancelled Event Detection Plan

**Status:** Plan only — no implementation yet.
**Author:** Investigation 2026-04-24
**Trigger:** User flagged that "Markham Community Matched Speed Dating"
(`https://www.meetup.com/club-happy-local-singles-speed-dating/events/314158106/`,
date 2026-04-26) is cancelled on Meetup but still shows `status="UPCOMING"` in
our `events.json`. None of our 30 scrapers in `tools/scrapers/` have any
cancellation-detection logic today (`grep -i 'cancel' tools/scrapers/` → 0 hits).

## 1. Source-specific cancellation signals

| Source | Where the signal lives | Detection |
|---|---|---|
| **Meetup** | Event page renders a red banner with text **"This event has been cancelled"** plus a `data-event-label="event-cancelled-banner"`-style element. JSON-LD on the same page has `"eventStatus":"https://schema.org/EventCancelled"`. | Prefer JSON-LD; fall back to banner text. |
| **Eventbrite** | API/JSON returns `"status": "canceled"` (single-l). Cancelled detail pages often 404 or 410. | Treat 404 as soft signal (ambiguous — could just be deleted). Status field is ground truth. |
| **Fatsoma** (and `Thursday/Fatsoma`) | JSON-LD `"eventStatus":"EventCancelled"`. Page often hides date/time and adds a "Cancelled" pill in the hero. | JSON-LD only. |
| **Ticketmaster** | API status JSON returns `"status":{"code":"cancelled"}`. | API. |
| **NOW Toronto / ToDoCanada / Narcity** | Editorial sites — they typically *delete* the listing rather than mark it cancelled. | Drop `404 → status=CANCELLED` after 2 retries. |
| **City venues** (ROM, AGO, Harbourfront, Sankofa, Nathan Phillips, etc.) | Vary widely; most just remove the listing. | Same `404 → CANCELLED` heuristic. |

Each scraper-side check belongs in a `_check_cancelled(html_or_json)` static
method in `BaseScraper`, with per-source overrides where needed.

## 2. Two-tier strategy

### Tier A — at scrape time
Today scrapers silently *drop* cancelled events. Change behaviour to emit them
with `status="CANCELLED"` so users see the history. Plumbing:

1. Each `*_scraper.py` adds a `cancelled` check after detail-page fetch.
2. `ScrapedEvent.status` already exists in `tools/scrapers/base_scraper.py:296`
   — no schema change needed.
3. `unified_scraper.py` must merge by `(title, date, source)` and prefer the
   newest `status` (cancelled overrides upcoming).

### Tier B — revalidation pass (more important)
Many cancellations happen *after* scrape. New cron job:

- File: **`tools/scrapers/cancellation_revalidator.py`** (new).
- Schedule: `*/30 * * * *` via a new GitHub Actions workflow
  `.github/workflows/cancellation-revalidator.yml`.
- Reads `events.json`, filters to `status=="UPCOMING"` AND
  `date <= today + 14 days` (only revalidate near-term events to keep request
  budget bounded — full corpus has 4381 events; near-term subset ≪ 500).
- For each event, dispatches to a per-source handler that hits its `url`
  with a strict `requests.get(..., timeout=10)`, looks for the cancellation
  signal from the table above, and returns `True | False | "unknown"`.
- Writes back `events.json` with `status="CANCELLED"` only for confirmed hits.

## 3. Markham example walkthrough

Revalidator picks up the event because `date=2026-04-26` and `status=UPCOMING`.
Source is `Meetup`, so it routes to `_check_cancelled_meetup(url)`:

1. `GET https://www.meetup.com/club-happy-local-singles-speed-dating/events/314158106/`
2. Parse `<script type="application/ld+json">` for `eventStatus`.
3. If `eventStatus.endsWith("EventCancelled")` → return `True`.
4. Else search HTML for `event-cancelled-banner` or
   `class*="cancelled"` / phrase `"this event has been cancelled"`.
5. On `True`, set `status="CANCELLED"` and stamp `cancelled_detected_at`.

## 4. UI behaviour (no scraper change needed)

`TORONTOEVENTS_ANTIGRAVITY/index.html` (template at
`audit_dashboard/template.html`) `applyFilters()` already has a TBD toggle
(`showTBDEvents`, line ~3370). Add a sibling:

```js
let showCancelledEvents = false;          // default: hide
if (eventData && eventData.status === 'CANCELLED' && !showCancelledEvents) {
  shouldShow = false;
}
```

Plus a small toggle next to the existing TBD toggle, and a red **CANCELLED**
badge on the card when shown (mirrors the existing TBD badge pattern at line
3387). Default-hide preserves the user's expectation that the grid only shows
attendable events; the toggle gives power users an audit trail.

## 5. Risk + mitigation

| Risk | Mitigation |
|---|---|
| Network blips flip a live event to CANCELLED | Require **2 consecutive runs** with cancellation signal AND no successful "UPCOMING" verification in between. Track in `cancellation_revalidator_state.json`. |
| Meetup rate-limits us (HTTP 429) | Per-source 1-req-per-2-seconds rate limit; exponential backoff; skip event on 429 (do not flip status). |
| Source-page redesign breaks parser | Each `_check_cancelled_*` returns `"unknown"` on parse failure (≠ False) → no status change. Log to `audit_trail/`. |
| False positive marks attendable event CANCELLED | Status flip is logged + Slack-pingable; manual override via `events.json` re-edit + commit (idempotent — next scrape will re-confirm). |

## 6. One concrete next-step PR

**Title:** `feat(scrapers): add _check_cancelled hook to BaseScraper + Meetup`

Scope:
1. `tools/scrapers/base_scraper.py` — add `@staticmethod _check_cancelled(url, source) -> Optional[bool]` returning `True/False/None`. Default impl returns `None` (unknown).
2. `tools/scrapers/meetup_scraper.py` — override with the JSON-LD + banner check from §3 above.
3. Unit test `tests/test_cancellation_detection.py` with two fixtures: the
   live Markham event HTML (cancelled) and one known-upcoming Meetup event.
4. **Not yet wired into production.** Per the repo's wire-up rule
   (`CLAUDE.md` § "Wire-Up Rule"), this PR is **opt-in / sidecar** with the
   following Wiring Plan:

> ## Wiring Plan
> Caller will be `tools/scrapers/cancellation_revalidator.py`,
> functions `revalidate_event()` and `revalidate_all()`, expected in the
> follow-up PR `feat(scrapers): cancellation revalidator workflow` no later
> than 2026-05-08.

## 7. File summary

- New: `tools/scrapers/cancellation_revalidator.py`
- New: `.github/workflows/cancellation-revalidator.yml` (cron `*/30 * * * *`)
- New: `tests/test_cancellation_detection.py`
- Modified: `tools/scrapers/base_scraper.py` (+1 method)
- Modified: `tools/scrapers/meetup_scraper.py` (+1 override)
- Modified: `tools/scrapers/eventbrite_scraper.py` (+1 override, follow-up)
- Modified: `tools/scrapers/fatsoma_scraper.py` (+1 override, follow-up)
- Modified: `audit_dashboard/template.html` (UI toggle + badge — separate PR)
