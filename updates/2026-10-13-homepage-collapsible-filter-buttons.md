# 2026-10-13 — Homepage: collapsible filter buttons (extras hidden by default) + mobile viewport overflow

File changed: `TORONTOEVENTS_ANTIGRAVITY/index.html` (live on findtorontoevents.ca and tdotevent.ca)
Follow-up to [2026-10-13-homepage-fab-overlap-and-menu-load-latency.md](2026-10-13-homepage-fab-overlap-and-menu-load-latency.md).

## Request
Make the bottom filter buttons collapsible. Multi-Day, TBD and Thumbnails should be hidden by default; only Near Me stays visible.

## What changed
- `createFilterControls()` now builds a bottom row: `– · ⋯ · 📍 Near Me`. On mobile the row is mirrored and anchored at the left edge.
  - **`⋯` (`#filter-more-toggle`)** shows or hides `#filter-extras`, which holds Multi-Day, TBD and Thumbnails. The extras are **collapsed by default**.
    - When a non-default extra filter (Multi-Day or TBD) is switched on and the group is collapsed, the `⋯` button gets a highlight ring, so the active filter isn't invisible.
  - **`–` (`#filter-minimize-toggle`)** minimizes the whole stack into a single `🔎 Filters` pill; clicking the pill restores it. Minimizing also closes the Near Me panel.
  - The `localStorage` keys `fte-filter-extras-open` and `fte-filter-minimized` (`'1'`/`'0'`) remember both choices across visits.
  - The buttons carry `aria-expanded`, `aria-controls` and `aria-label`, and use the existing 48 px touch-target rule.
- **Mobile overflow fix (pre-existing bug found while testing):** the hidden tile info popovers (`absolute w-80`) stuck out past the right edge. On a 390 px phone this made the layout viewport 457×989, so every bottom-anchored fixed button was partly below the visible screen. On live, the 🤖 AI button sat at y 841–889 on an 844 px-tall screen.
  - Added `html, body { overflow-x: clip }` at ≤640 px. The layout viewport is now 390×844 and every button is fully on screen.

## Verification
Playwright ran against live assets with `/index.html` replaced by the patched file. Results at 1280×800 and 390×844 (touch/mobile):

| State | Visible | Overlaps with AI / bell / settings |
|---|---|---|
| Default (first visit) | Near Me, ⋯, – | none |
| ⋯ clicked | + Multi-Day, TBD, Thumbnails | none |
| Multi-Day on, then collapsed | ⋯ has the `has-active` ring | — |
| – clicked | only `🔎 Filters` | — |
| Reload | minimized state kept (`fte-filter-minimized=1`) | — |

There were no page errors apart from the pre-existing React #418.

## Backups and rollback
- git tag `backup/homepage-pre-collapse-20261013-212754`
- On FTP, one timestamped `index.html.bak-<UTC timestamp>` per site in `/findtorontoevents.ca/_backups/` and `/tdotevent.ca/_backups/`, taken just before deploy.
