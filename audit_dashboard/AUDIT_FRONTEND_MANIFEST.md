# Audit Dashboard Frontend Manifest

**Surface:** `findtorontoevents.ca/audit` — the audit dashboard.
**Auto-generated companion:** `audit_dashboard/audit_frontend_manifest.json`
**Generator:** `tools/audit_frontend_manifest.py` (static parser — never runs a dashboard generator).
**CI refresh:** `.github/workflows/audit-frontend-manifest.yml` (daily cron, commits with `[skip ci]` on change).

> Do **not** hand-edit the JSON. It is regenerated from `template.html` / `hc_filter.js` /
> `money_ready_filter.js`. To change a control, edit the source HTML/JS and re-run the script.
> Line numbers in this doc are a snapshot — the JSON is the fresh source of truth.

---

## Summary counts (snapshot)

| Category | Count | Orphaned |
|---|---|---|
| Buttons | 47 | **1** (`btn-money-ready`) |
| Tabs | 17 (13 in-page + 4 external-page links) | 0 |
| Filters / controls | 31 | 0 |
| ?Guide / help / glossary concepts | 10 | 0 |

**WIRED** = a render path actually applies the control (handler exists + a render
function reads the state it sets). **ORPHANED** = the control fires a handler but no
render path consumes its effect.

---

## PART 1 — Inventory

### A. Toolbar preset buttons (the headline "feed" buttons)

| Button | id | line | handler | defined at | what it does | WIRED? |
|---|---|---|---|---|---|---|
| 🧠 SMART PICKS | `btn-smart-picks` | ~1306 | `applySmartPicks()` (inline onclick) | `template.html` ~12216 | Resets pick filters, loads the embedded `smart_picks_feed`, resolves live curated picks, sets `f-sort=smart_score_desc`, re-renders Active Picks to only the curated feed rows. | **WIRED** |
| 🔥 HIGH CONVICTION ⭐ | `btn-conviction-picks-hero` | ~1308 | `applyHighConvictionPreset()` (addEventListener) | `template.html` ~12960 (listener ~12998) | Sets `window._convictionOnlyFilter` + `_hcEdgeStrict`, shows the HC explainer, switches to Active tab, re-renders. Picks are filtered through `hc_filter.js` `passesHighConvictionPick()` shared gates + per-asset S/A/B tier path. | **WIRED** |
| 💰 MONEY READY 👑 | `btn-money-ready` | ~1309 | `applyMoneyReady()` (inline onclick) | `money_ready_filter.js` ~174 | Toggles `window._moneyReadyActive`, restyles the button, inserts a banner, calls `renderActive`/`onFilterChange`. | **ORPHANED** — see below |
| Best Score | `btn-best-fresh` | ~1289 | addEventListener | `template.html` ~12740 | Dashboard-score preset; sorts active picks by score. Exploration only — not the Smart Picks backend. | **WIRED** |
| Proven Only | `btn-proven-picks` | ~1290 | addEventListener | `template.html` ~12779 | Filters active picks by the manual trust registry (`_TRUST_PROVEN_STRATEGIES` / `_TRUST_PROVEN_SYSTEMS`) — name-match, not a live closed-pick query. | **WIRED** |
| In Profit | `btn-strong-picks` | ~1291 | addEventListener | `template.html` ~12757 | Shows currently-profitable picks moving toward target. | **WIRED** |
| Verified Alpha | `btn-verified-alpha` | ~1307 | addEventListener | `template.html` ~12811 | Filters Active Picks to verified prediction-market + auditable pro-trader rows. | **WIRED** |

#### ⚠ ORPHANED: `btn-money-ready`

`applyMoneyReady()` (in `money_ready_filter.js`) flips `window._moneyReadyActive`,
restyles the button and inserts a `#money-ready-banner` — then calls `renderActive()`
/ `onFilterChange()`. **However, no render path in `template.html` reads
`window._moneyReadyActive` or calls `window.filterMoneyReady()`.** The picks grid is
therefore never actually filtered when the button is clicked — only the banner appears.

To wire it: a pick-render function (e.g. `renderPicks` / `matchFilter`) must check
`window._moneyReadyActive` and, when true, run candidates through
`window.filterMoneyReady(picks)` (exported by `money_ready_filter.js`). This mirrors
how `applyHighConvictionPreset()` sets `_convictionOnlyFilter` which the render path
*does* consult.

### B. Filter-bar utility buttons

| Button | id | line | handler defined at | what it does |
|---|---|---|---|---|
| Clear All | `btn-clear-filters` | ~1337 | `template.html` ~13495 | Resets every filter control; also clears HC/preset state. |
| ⚙ (column settings) | `btn-col-settings` | ~1339 | `template.html` ~14337 | Opens `#col-settings-panel` to toggle visible columns. |
| Apply (columns) | `col-apply` | ~1344 | `template.html` | Applies the selected visible-column set. |
| Reset (columns) | `col-reset` | ~1345 | `template.html` | Resets visible columns to default. |
| ↻ Reload Page | `btn-refresh` | ~1348 | `template.html` ~12732 | Reloads the page to pick up the latest CI-regenerated data. |
| Full Refresh | `btn-full-refresh` | ~1349 | `template.html` ~14375 | Triggers the GitHub Actions pipeline to regenerate all data (needs auth token). |
| ⚡ Refresh Picks | `btn-refresh-picks` | ~1350 | `template.html` ~14409 | Runs the Momentum Scalp Scanner + Tracked Picks Generator. |
| Export Active (CSV) | `btn-export-excel` | ~1303 | `template.html` ~14083 | Exports filtered active picks to CSV. |
| Export Closed (CSV) | `btn-export-closed` | ~1304 | `template.html` ~14170 | Exports filtered closed/resolved picks to CSV. |
| Export All (CSV) | `btn-export-all` | ~1305 | `template.html` ~14233 | Exports all picks (active + closed) to CSV. |

### C. In-render toggle / action buttons (dynamically created)

These are emitted inside render functions; their listeners are attached at render
time via `getElementById(...).addEventListener(...)`.

| Button | id | line | what it does |
|---|---|---|---|
| TP-Hit toggle | `btn-tp-hit-toggle` | ~10178 | Show/hide picks that already hit Take Profit. |
| Show All Picks toggle | `btn-show-all-picks` | ~10187 | Toggle quality-gated view vs full candidate pool. |
| Show/hide killed (non-crypto) | `nc-toggle-killed` | ~6066 | Toggles killed strategies in the non-crypto panel. |
| Score-tracker Clear History | `st-clear` | ~1466 | Clears the Score Tracker history. |
| Score-tracker Export CSV | `st-export` | ~1467 | Exports the Score Tracker history. |
| Permutations pick-filter Apply | `pf-apply` | ~15967 | Applies the Permutations-tab pick filters. |
| Permutations pick-filter Reset | `pf-reset` | ~15968 | Resets the Permutations-tab pick filters. |
| HC explainer close | `hc-explainer-close` | ~1412 | Hides the HC explainer + clears `_hcEdgeStrict` / `_convictionOnlyFilter`. |
| Swarm panel toggle | `swarm-panel-toggle` | ~18120 | Collapse/expand the swarm-pick-tracking panel. |
| Smart Picks asset chips (All/Crypto/Equity/Forex/Commodity/Futures/ETF) | (`.sp-asset-btn`) | ~1543-1549 | `filterSmartPicksByAsset()` — sub-filters the Smart Picks tab by asset class. |

Plus modal close `&times;` buttons (no id) and "Load more" / "Load All Picks"
pagination buttons — all WIRED to inline handlers.

### D. Tabs (`data-tab=` panels + their tab buttons)

| Tab | data-tab | tab-button line | panel id | panel line | WIRED? |
|---|---|---|---|---|---|
| Overview | `overview` | ~1355 | `tab-overview` | ~1404 | WIRED |
| ⭐ Active Picks | `active` | ~1356 (`btn-jump-active`) | `tab-active` | ~1432 | WIRED |
| Verified Alpha | `verifiedalpha` | ~1357 | `tab-verifiedalpha` | ~1433 | WIRED |
| 🧠 Smart Picks | `smartpicks` | ~1358 | `tab-smartpicks` | ~1476 | WIRED |
| 📈 US Equity Picks | `ueps` | ~1359 | `tab-ueps` | ~1939 | WIRED |
| Closed Picks | `closed` | ~1361 | `tab-closed` | ~1435 | WIRED |
| Dashboards | `dashboards` | ~1366 | `tab-dashboards` | ~1437 | WIRED |
| Strat. Leaderboard | `leaderboard` | ~1368 | `tab-leaderboard` | ~1440 | WIRED |
| Permutations | `permutations` | ~1369 | `tab-permutations` | ~1442 | WIRED |
| Performance | `performance` | ~1370 | `tab-performance` | ~1443 | WIRED |
| Score Tracker | `scoretracker` | ~1371 | `tab-scoretracker` | ~1461 | WIRED |
| ML Health | `mlhealth` | ~1372 | `tab-mlhealth` | ~1931 | WIRED |
| Links | `links` | ~1373 | `tab-links` | ~2242 | WIRED |

**External-page tab links** (styled as `.tab-btn` but navigate to a separate HTML page):
Portfolios (`portfolio_history.html`), 🧪 Anti-Overfit DSR (`anti_overfit.html`),
💰 Paper Pilot COT (`paper_pilot.html`), 🏦 Real Money (`real_money.html`).

> Note on **Smart Picks button vs Smart Picks tab**: `#btn-smart-picks` (~1306) is a
> *filter preset* that re-renders the Active Picks grid; `data-tab="smartpicks"` →
> `#tab-smartpicks` (~1476) is a *separate panel* with its own curated render +
> asset chips. They are distinct surfaces. The same is true for **Money Ready
> button** (`#btn-money-ready`, orphaned) vs there being **no `tab-moneyready` panel**
> — Money Ready is button-only; the picks-grid wiring is missing.

### E. Filters / controls (31)

**Primary filter bar** (`#filter-bar`, ~1262): `f-asset`, `f-system`, `f-status`,
`f-dir`, `f-search`.

**Advanced filter bar** (`#filter-bar-advanced`, ~1274): `f-pnl`, `f-conf` (trust
score 0-10 — replaced confidence per M-006), `f-age`, `f-tp-rem`, `f-conflicts`,
`f-timeframe`, `f-concept` (strategy concept family), `f-sort` (10 sort modes),
`f-score-tier` (score-tier preset: noise / paper / trade / conviction),
`f-hide-no-price` (checkbox).

All of the above feed `onFilterChange()` → `matchFilter()` → the Active Picks render.

**Tab-local controls:** `bf-system` (BT-vs-FWD), `f-discord-channel`,
`lb-verdict` / `lb-type` / `lb-min-wr` / `lb-active-only` / `lb-sort` (Leaderboard),
`show-untracked-sys` (Permutations matrix), `pf-score` / `pf-conf` / `pf-dir` /
`pf-asset` / `pf-sys` (Permutations pick filter — applied by `pf-apply`),
`swarm-flt-account` / `swarm-flt-class` / `swarm-flt-tier` (swarm panel).

> The JSON enumerates every `<option>` value+label for each `<select>`. One known
> parser limitation: `f-score-tier`'s options span multiple source lines, so the JSON
> records the control but not its option list — see the select at `template.html` ~1294.

### F. ?Guide / help / glossary concepts (10)

| Concept surface | id | line | defines |
|---|---|---|---|
| ? Guide button (Performance) | `perf-help-btn` | ~1117 | Opens the edge-finding guide overlay. |
| Performance ?Guide overlay | `perf-help-overlay` | ~1121 | How to find edge: exact filters, definitions, anti-patterns (closed-pick analysis). |
| HIGH CONVICTION explainer panel | `hc-explainer-panel` | ~1409 | The `hc_filter.js` shared gates + per-asset-class validated-edge gate; which classes are DEAD / WEAK / NO DATA; Score/Trust/FWD-WR field mapping. |
| Smart Picks ? info icon | `sp-info-icon` | ~1479 | Hover/click target that reveals the Smart Picks explainer tooltip. |
| Smart Picks explainer tooltip | `sp-tooltip` | ~1481 | ML Score, Forward Walk-Forward WR, Confidence Calibration, Regime Alignment, Trust & Source Scoring, hard gates, forward-validated bypass. |
| Smart Picks ?Glossary button | `smart-picks-glossary-btn` | ~1517 | Toggles the scoring-factor glossary. |
| Smart Picks scoring-factor glossary | `smart-picks-glossary` | ~1518 | Plain-language meaning of each "Why"-column factor string. |
| US Equity Picks ?Glossary button | `ueps-glossary-btn` | ~1963 | Toggles the UEPS factor glossary. |
| US Equity Picks glossary panel | `ueps-glossary` | ~1968 | F-Score, Magic Rank, Acquirer M, Altman Z'', Beneish M, ROIC, FCF Yield. |
| Feed-stack legend | `tier-trust-legend` | ~1382 | How Verified Alpha / Smart Picks / High Conviction / Active Picks rank in strictness. |

---

## PART 3/4 — Regeneration & CI

- **Regenerate locally:** `python tools/audit_frontend_manifest.py`
- **Stale-check (CI-friendly):** `python tools/audit_frontend_manifest.py --check`
- **Daily refresh:** `.github/workflows/audit-frontend-manifest.yml` runs the script on
  an off-peak cron and commits `audit_frontend_manifest.json` with `[skip ci]` if it
  changed.

The generator is a pure static parser: it reads only the three source files and
writes only the JSON manifest. It never invokes a dashboard generator and never
touches `index.html`.
