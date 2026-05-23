# Event gap scan tool (2026-04-25)

## What was added

- [`tools/scan_event_gaps.py`](../tools/scan_event_gaps.py): loads the public live catalog (JSON array or `{ "events": [...] }` from `https://findtorontoevents.ca/events.json` with fallback to `/next/events.json`), runs [`UnifiedTorontoScraper`](../tools/scrapers/unified_scraper.py), and reports events that are **not** duplicates of the baseline using the same `is_duplicate()` / `normalize_title()` rules as the merge path. Optional `--include-experimental` merges [`tools/scrapers/experimental_supplement.py`](../tools/scrapers/experimental_supplement.py) (RSS + optional iCal via env). Writes `reports/event_gaps_<UTC>.json` and optional CSV.
- [`tests/test_scan_event_gaps.py`](../tests/test_scan_event_gaps.py): unit tests (no network) for parsing, gap classification, merge, RSS/iCal parsing helpers, mocked baseline fetch.
- [`docs/TORONTO_EVENT_DISCOVERY_PHASE2.md`](../docs/TORONTO_EVENT_DISCOVERY_PHASE2.md): scraper inventory and Phase 2 notes.

## Verification

- `python -m pytest tests/test_scan_event_gaps.py -v` — all passed.
- `python tools/scan_event_gaps.py --baseline-file events.json --skip-scrape --scraped-json next/events.json` — completed and wrote a report (gaps depend on data).

## Usage examples

```text
python tools/scan_event_gaps.py
python tools/scan_event_gaps.py --baseline-file events.json
python tools/scan_event_gaps.py --include-experimental
python tools/scan_event_gaps.py --skip-scrape --scraped-json path/to/scraped.json
```
