# AUDIT_PAGE_SECTIONS_2026-11-18

**Target:** `/home/eaguiar2015/findtorontoevents_antigravity.ca/audit_page.html`  
**Audit date:** 2026-11-18  
**File size / mtime:** 15,540 B, May 25 20:29 (stale ~6 months)  
**Method:** static read of HTML + referenced JSON feeds (`data/grok_top_picks.json`, `audit_dashboard/data/*.json`)

---

## 1. Page Structure (Observed)

- **Tab bar:** Exactly **2 tabs** declared:
  - `Overview` → `onclick="switchTab('overview')"` (active by default)
  - `🧠 GROK Top Picks` → `onclick="switchTab('grok')"`
- **No other tabs** (US equity picks, per-asset-class GitHub Actions checks, data-quality tabs) are present in the DOM or JS.

### 1.1 `Overview` tab (`#overview`)
- Declared: `<div id="overview" class="tab-content active">`
- **Content:** completely empty — only a single HTML comment:
  ```
  <!-- Existing overview/summary here -->
  ```
- No table, no summary metrics, no data bindings.

### 1.2 `GROK Top Picks` tab (`#grok`)
- Timestamp container: `#grok-ts`
- Loading indicator: `#grok-loading` (shown until fetch completes)
- Main table: `#grok-table` (initially `display:none`)
  - Columns: Strategy / Symbol / Dir / Entry / TP / SL / Conf / Unrealized
  - Row renderer pulls `pick.extra_json` → `JSON.parse(...).signal_basis` **with no try/catch** — will throw on malformed/empty `extra_json` and abort the entire table render.
  - `Unrealized` column is a permanent `⏳` placeholder (`pnl-zero` class) — never populated by any code path.
- Historical sub-section: `#grok-historical`
  - Header: "Realized P/L History" with badge `#grok-hist-count`
  - Table: `#grok-hist-table` (columns: Symbol / Entry / Exit / P/L % / Closed At)
  - Empty state: `#grok-hist-empty` → "No closed trades yet. Tracking starts now."
- Data source: single fetch `fetch('data/grok_top_picks.json?' + Date.now())`
- Auto-refresh: `setInterval(loadGrokPicks, 5*60*1000)` (hardcoded 5 min poll regardless of staleness)
- `switchTab()` uses global `event.target` — will fail if invoked without a live event (fragile, non-standard).

### 1.3 Summary row (hardcoded)
- `<div class="subtitle">Generated at 2026-03-13T20:53:44.610Z</div>` (line 259)
- `Total Picks` value = `1234` (placeholder/fake)

---

## 2. Data Feeds (Referenced vs Live)

### 2.1 `data/grok_top_picks.json` (page actually loads this)
- Size / mtime: 1,339 B, May 25 20:29
- `timestamp`: `2026-03-14T04:35:00.000Z`
- Picks: 3 (BTCUSDT/ETHUSDT/BNBUSDT, all crypto SHORT, conf 0.94/0.92/0.90)
- `historical_realized`: `[]` (0 rows)
- Keys: `timestamp, grok_top_picks, historical_realized, historical_unrealized, total_historical`

### 2.2 `audit_dashboard/data/grok_top_picks.json` (live copy, different schema)
- Size / mtime: 1,686 B, Nov 12 20:19
- `timestamp`: `2026-03-14T03:43:37.334455+00:00`
- Picks: 3 (BTCUSDT/ETHUSDT/SOLUSDT)
- Keys: includes `lifetime_stats` instead of `historical_unrealized`/`total_historical`
- **Schema divergence** between the two copies.

### 2.3 `audit_dashboard/data/db_health.json` (fresh, unreferenced by page)
- Size / mtime: 6,566 B, Nov 18 00:27
- `generated_at`: `2026-11-17T21:37:22.068121+00:00` (~4 h old at audit time)
- Host: `mysql.50webs.com`, db: `ejaguiar1_stocks`, engine: MySQL 8.4.7
- Checks (all `ok=true` unless noted):
  - `pnl_integrity`: sampled 24,158 rows (id range 16262086–16462086); sign_mismatch 130 (0.54%); naive_magnitude_mismatch 6,535 (27.05%)
  - `won_pnl_contradiction`: TP_HIT n=7026 avg_pnl +3.4068 (0 negative); SL_HIT n=3873 avg −3.1987 (3871 negative); LOST n=5598 avg −1.7633 (5571 negative)
  - `status_standardization`: 0 non-canonical
  - `ghost_rows`: **total_ghost_rows 22,947**, 10 cohorts; top cohorts: MEMECOIN/meta_strategy/DOGEUSDT LONG (n=3569 with pnl 1.3226; n=3160 with pnl 5.0)
  - `open_bloat`: trading_picks open_count **92,985** vs info_schema_estimate 46,150; active_count 21; total 145,801; `last_terminal_write: 2026-11-17 17:49:29`; `hours_since_last_close: 3`; bt_backtest_trades open 29,247,197 / total 32,441,049
- **Not surfaced** on `audit_page.html` — the page has no data-quality tab and does not read this file.

### 2.4 `audit_dashboard/data/picks_now.json` (fresh, unreferenced by page)
- Size / mtime: 152,548 B, Nov 18 00:27
- `generated_at`: `2026-11-17T18:32:55.213317+00:00`
- Keys: `generated_at, generated_at_est, date, market_regime, risk_off_explanation, n_scored, picks, trending, all, safest`
- Lists: `picks` 29, `trending` 5, `all` 50, `safest` 5
- **Not surfaced** on `audit_page.html`.

---

## 3. Missing Sections (Explicit)

Per the GO request, the following sections **do not exist** in `audit_page.html`:

| Section requested | Status | Evidence |
|-------------------|--------|----------|
| US equity picks | **ABSENT** | No tab, no table, no equity symbols in any feed referenced by the page |
| per-asset-class GitHub Actions checks | **ABSENT** | No CI badges, no workflow status, no per-asset tables |
| data-quality tabs | **ABSENT** | Only 2 tabs; `db_health.json` (fresh, 22,947 ghost rows, 92,985 open picks) exists but is never read or rendered |

---

## 4. Freshness Summary

| Artifact | mtime | `generated_at` / `timestamp` | Gap |
|----------|-------|------------------------------|-----|
| `audit_page.html` | May 25 20:29 | 2026-03-13T20:53:44Z (hardcoded) | ~6 months |
| `data/grok_top_picks.json` | May 25 20:29 | 2026-03-14T04:35:00Z | ~8 months |
| `audit_dashboard/data/grok_top_picks.json` | Nov 12 20:19 | 2026-03-14T03:43:37Z | ~8 months |
| `audit_dashboard/data/db_health.json` | Nov 18 00:27 | 2026-11-17T21:37:22Z | ~4 hours |
| `audit_dashboard/data/picks_now.json` | Nov 18 00:27 | 2026-11-17T18:32:55Z | ~6 hours |

---

## 5. Defects & Gaps (Actionable)

1. **Empty Overview pane** — the only declared "overview" is a comment placeholder.
2. **Hardcoded fake metrics** — "Total Picks 1234" and March 2026 subtitle.
3. **Unguarded `JSON.parse(extra_json)`** in row renderer — throws on bad/missing `extra_json`.
4. **Permanent `⏳` Unrealized column** — never populated.
5. **Fragile `switchTab()`** — relies on global `event.target`.
6. **Single stale feed** — page only reads `data/grok_top_picks.json`; ignores fresh `audit_dashboard/data/*.json`.
7. **No data-quality surface** — 22,947 ghost rows, 92,985 open picks, 27.05% PnL magnitude mismatch are invisible on the page.
8. **Schema drift** — two `grok_top_picks.json` copies with incompatible key sets.

---

## 6. Conclusion

`audit_page.html` is a **severely degraded artifact**: 2 tabs, empty overview, hardcoded placeholders, stale crypto-only feed, and zero wiring to the live data-quality or picks feeds that exist under `audit_dashboard/data/`. The three sections requested in the GO (US equity picks, per-asset-class GitHub Actions checks, data-quality tabs) are **absent**. Real, quantified gaps (ghost rows, open bloat, PnL mismatches) are available in `db_health.json` but are not surfaced.

**Deliverable complete.** File written to repo root as required. No commit/push performed.
