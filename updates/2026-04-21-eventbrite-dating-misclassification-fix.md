# Eventbrite Dating Misclassification Fix (2026-04-21)

## What Was Broken
An Eventbrite listing for:
- Create Social Media Graphics - 1 Day Beginner Course in Toronto
- https://www.eventbrite.ca/e/create-social-media-graphics-1-day-beginner-course-in-toronto-tickets-1975274209333

was appearing under the Dating category on findtorontoevents.ca.

Root cause:
- The dating-specific scraper (`tools/scrapers/dating_events_scraper.py`) force-added `Dating` and `Singles` for JSON-LD events fetched from Eventbrite dating browse pages.
- Eventbrite browse pages can include unrelated promoted events, so non-dating events were incorrectly labeled as Dating.

## What I Changed
1. Added a guardrail in `tools/scrapers/dating_events_scraper.py`:
- In `_jsonld_to_event`, events are now skipped unless `_is_dating_event(title, description)` is true.
- This prevents unrelated promoted events from being force-tagged as Dating.

2. Corrected current feed data for the affected event:
- `events.json`
- `next/events.json`
- `events_backup.json`

For the specific event, categories/tags were updated from:
- Categories: `Dating`, `Business`
- Tags: `Professional`, `Singles`

to:
- Categories: `Business`
- Tags: `Professional`

## Verification
- Python syntax check passed:
  - `python -c "import py_compile; py_compile.compile('tools/scrapers/dating_events_scraper.py', doraise=True); print('py_compile ok')"`
- Verified the affected event record now shows only `Business` category in:
  - `events.json`
  - `next/events.json`
  - `events_backup.json`

## Notes
- An unrelated modified file exists in the working tree: `alpha_engine/non_crypto_policy.py` (not changed by this fix).
