# Thursday + Thursday/Fatsoma Source Unification Plan

**Author:** claude-code (opus-4.7)
**Date:** 2026-04-24
**Branch context:** `feat/sports-data-sources-integration` (investigation only)
**Status:** PLAN ONLY — no migrations, scraper edits, or commits performed.

---

## TL;DR

`events.json` on `origin/main` (commit `3c92e52068`) currently labels Thursday-branded
dating events with **two different `source` strings** that should be unified into
one canonical value: `Thursday`.

| `source` value      | Count | Date range                    | Origin                                                                 |
|---------------------|-------|-------------------------------|------------------------------------------------------------------------|
| `Thursday/Fatsoma`  | 6     | 2026-01-29 → 2026-02-26 (all past) | Historical one-time imports — **no current code path produces this label** (verified via `grep` over `tools/scrapers/`). |
| `Thursday` (stale)  | 4     | 2026-01-30                    | Earlier manual import; no current code path emits this date span.      |
| `Thursday` (fresh)  | 10    | 2026-04-25 → 2026-07-23       | New `GetThursdayScraper` (`tools/scrapers/thursday_scraper.py`, PR #373). |

The fresh rows (10) are correct and visible on the site once the CDN refreshes.
The 10 stale rows are noise.

## Producer audit

Grep over the repo for the literal label strings:

| Label             | Producer file:line                                  | Notes |
|-------------------|------------------------------------------------------|-------|
| `Thursday/Fatsoma` | **(none)** — does not appear in any `*.py` file on `main` or `feature/add-thursday-scraper` | Likely emitted by a now-deleted manual-import script in early 2026. The `FatsomaScraper` on `main` uses `SOURCE_NAME = "Fatsoma"` (single label). |
| `Thursday`         | `tools/scrapers/thursday_scraper.py:64` (`SOURCE_NAME = "Thursday"`)  ← only live emitter | Wired into `tools/scrapers/unified_scraper.py:50,165`. |
| `Fatsoma`          | `tools/scrapers/fatsoma_scraper.py:82` (`SOURCE_NAME = "Fatsoma"`)    | Currently emits **0 Toronto events** because Fatsoma's `/discover` is UK-only (verified in `docs/THURSDAY_FATSOMA_FIX_PLAN_2026_04_24.md`). |

Conclusion: no live code path will produce a new `Thursday/Fatsoma` row. The
6 rows in `events.json` are historical artifacts.

## Fatsoma is structurally dead for Toronto (sanity-check)

`tools/scrapers/fatsoma_scraper.py` filters discover-page cards by
`if "toronto" not in combined: continue` (line 284). The handoff doc
(`docs/THURSDAY_FATSOMA_FIX_PLAN_2026_04_24.md`) verified that Fatsoma's
`/discover` page returns 52 events from UK cities only (London, Bristol,
Manchester, Bath, York, Newcastle, Guildford, Tunbridge Wells, Belfast),
so the filter correctly drops everything → **0 Fatsoma rows currently
emitted**. Direct event pages (e.g. `/e/c41j6xsc/thursday-sunrise-forgives-toronto`)
still exist but are not discoverable from the public discover endpoint.

The new `GetThursdayScraper` covers the same Thursday-branded events via
`events.getthursday.com/toronto/`, so deprecating the Fatsoma path loses no
real Toronto coverage.

## Two-part fix

### Part A — One-time data migration (events.json cleanup)

Goals:
1. Rewrite `source = "Thursday/Fatsoma"` → `source = "Thursday"` (unify label).
2. Drop the 10 stale rows whose dates are in the past (Jan/Feb 2026), so the
   live site doesn't carry obsolete dating events forward.

Migration sketch (~25 lines, run once locally, commit the resulting
`events.json` via a tiny PR):

```python
# tools/migrations/unify_thursday_source.py  (one-shot)
import json, datetime, pathlib

PATH = pathlib.Path("events.json")
TODAY = datetime.date.today()  # 2026-04-24 at time of writing

with PATH.open(encoding="utf-8") as f:
    events = json.load(f)

kept, dropped = [], []
for e in events:
    src = (e.get("source") or "").strip()
    # 1) unify label
    if src == "Thursday/Fatsoma":
        e["source"] = "Thursday"
        src = "Thursday"
    # 2) drop past Thursday rows (stale historical imports)
    if src == "Thursday":
        d = (e.get("date") or "")[:10]
        try:
            event_date = datetime.date.fromisoformat(d)
        except Exception:
            kept.append(e); continue
        if event_date < TODAY:
            dropped.append(e); continue
    kept.append(e)

PATH.write_text(json.dumps(kept, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"unified+pruned: kept={len(kept)} dropped={len(dropped)}")
```

Expected result on current `main`: kept ≈ N − 10, dropped = 10
(6 `Thursday/Fatsoma` past + 4 stale `Thursday` past).

### Part B — Regression prevention

Two cheap, independent guards:

1. **Add a normalizer in `tools/scrapers/base_scraper.py`** (or
   `unified_scraper.py` post-merge step) that maps any `source` value
   matching `Thursday/Fatsoma` → `Thursday` before writing the event.
   ~3 lines; future-proofs against any reintroduction of the old label.

2. **In `tools/scrapers/fatsoma_scraper.py`**, when (if ever) Fatsoma's
   `/discover` exposes Toronto again, the scraper currently emits
   `source = "Fatsoma"` (line 82, 378). For Thursday-branded events
   (title starts with `Thursday |`), have it emit `source = "Thursday"`
   instead so dedupe lines up with `GetThursdayScraper`.

   Sketch (inside `_enrich_from_detail`):
   ```python
   src = self.SOURCE_NAME
   if title.lstrip().startswith("Thursday |"):
       src = "Thursday"
   ...
   eid = self.generate_event_id(title, date_iso, src)
   return ScrapedEvent(..., source=src, ...)
   ```

## Dedupe-collision analysis

`base_scraper.generate_event_id(title, date, source)` keys on all three. After
unification:

- Both scrapers emit the same `(title, date, source="Thursday")` triple for
  the same event → **same `id`** → second writer overwrites the first.
- `unified_scraper.py` aggregates with id-based dedupe, so duplicates are
  collapsed in-memory before write.
- **No dup rows in `events.json`** even if Fatsoma re-discovers Toronto
  events that Thursday already covers. Safe.

## Order of operations

1. PR-1 (this plan): merge plan doc only.
2. PR-2 (data only): run migration script locally, commit `events.json`. Tiny
   diff. Should follow at least one successful daily scrape so we don't blow
   away any in-flight unified rows.
3. PR-3 (code guard): add normalizer + Fatsoma-side label override. Independent
   of PR-2.

## Risks

| Risk | Mitigation |
|------|------------|
| Migration drops a row a user expected to see | Past-date rows only; nothing currently visible on site since site filters past events anyway. |
| Future Fatsoma rediscovery double-emits Thursday rows | Covered by Part B's dedupe (same id). |
| `Thursday/Fatsoma` label reappears from a third-party feed | Covered by Part B's normalizer. |

## Out of scope

- No changes to `FatsomaScraper`'s discovery logic (still 0 Toronto events).
- No deprecation of Fatsoma scraper itself — leave it wired in case Fatsoma
  changes its public surface.
- No edits to `next/events.json` or `events_backup.json` — those mirror the
  primary file and will refresh on next sync.

---

## References

- `docs/THURSDAY_FATSOMA_FIX_PLAN_2026_04_24.md` — Fatsoma `/discover` UK-only verification.
- `tools/scrapers/thursday_scraper.py:64` — current canonical Thursday source.
- `tools/scrapers/fatsoma_scraper.py:82,378` — current Fatsoma label & emit point.
- `tools/scrapers/unified_scraper.py:50,165` — Thursday scraper wired into pipeline.
- `tools/verify_thursday_visible.js` — Playwright verification of visibility post-deploy.
