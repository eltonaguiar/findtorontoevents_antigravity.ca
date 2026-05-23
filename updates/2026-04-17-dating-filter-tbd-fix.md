# Fix: Dating Category + TBD Filter Bugs — 2026-04-17

## Files Changed

### 1. `TORONTOEVENTS_ANTIGRAVITY/index.html`
The live page served at **findtorontoevents.ca**.

#### Bug 1 — TBD events visible after clicking "Dating" (or any category)
**Root cause:** The custom filter script uses a `MutationObserver` to detect new event cards and re-run `applyFilters()`. However, the Next.js app filters categories by **toggling CSS visibility** on existing DOM nodes — it never adds or removes nodes. The observer only watches `addedNodes`, so it never fired after a category click. TBD events that were already in the DOM remained visible.

**Fix:** Added a capture-phase `document.addEventListener('click', ...)` listener. On any button/tab click outside our own `#custom-filter-controls`, it schedules `applyFilters()` after 400 ms — enough time for Next.js to finish its own DOM updates.

```diff
+    document.addEventListener('click', function(e) {
+      var btn = e.target && (e.target.closest ? e.target.closest('button, [role="tab"], [data-category], [data-filter]') : null);
+      if (!btn) return;
+      if (btn.closest('#custom-filter-controls')) return;
+      clearTimeout(window._categoryClickTimeout);
+      window._categoryClickTimeout = setTimeout(function() {
+        safeApply();
+      }, 400);
+    }, true);
```

#### Bug 2 — `__todayStart` computed once at page load
**Root cause:** `__todayStart` was a module-level variable set when the script first ran. If the browser tab was left open past midnight, the "past events" filter used a stale date.

**Fix:** `__todayStart` is now recomputed at the top of every `applyFilters()` call.

```diff
  function applyFilters() {
+   __todayStart = (function() { var d = new Date(); d.setHours(0,0,0,0); return d; })();
```

---

## Deployment

- Commit `ac2eb5a35` pushed to `main`
- The `fix-ghost-cards.yml` or site mirror workflow will pick up `TORONTOEVENTS_ANTIGRAVITY/index.html` and push to the 50webs FTP server (findtorontoevents.ca root)
- `scrape-events.yml` manually triggered to pull fresh dating events now that `dating_events_scraper.py` (PR #247) is on main

## Related

- **PR #247** — Added `tools/scrapers/dating_events_scraper.py` which scrapes Eventbrite dating-category pages + 25dates.com for real-dated events. The daily scraper ran before PR #247 merged; manual trigger above will pick it up.
- The "today shows April 18" display issue is a timezone rendering artefact in the Next.js layer (UTC midnight → local evening). The custom filter correctly keeps those events visible (they are today's evening events in EDT); the date label mismatch is in the compiled Next.js bundle and cannot be patched without the source.
