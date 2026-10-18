# 2026-10-18 — Symbol→asset-class cache fallback + why new `updates/*.md` never reach the live site

**Session:** 2026-10-18 (continuation of `2026-10-18-legacy-status-backfill-assetclass-reclass-and-metric-freshness-plan.md`)
**Scope:** P1 #5 (classifier fix) + the deploy gap discovered while documenting it.
**No schema changes, no rows deleted, no destructive commands.**

---

## 1. What was broken

### 1.1 `resolve_asset_class()` returned `UNKNOWN` for ordinary US tickers
`audit_trail/asset_classification.py` classifies from small, hand-curated regex lists
(`_EQUITY_PATTERNS`, `_ETF_PATTERNS`, …). They cover roughly the Dow-30 + a few ETFs, so
perfectly ordinary symbols — **AMD, PLTR, SOFI, XBI, EFA, XLK, TXN, GS, AMC …** — fell through to
`AssetClass.UNKNOWN`.

Consequences:
- The 2026-10-18 backfill of `ejaguiar1_stocks.at_raw_picks` could classify **0 of 2,629** OPEN
  `UNKNOWN` rows from the in-repo logic alone; it took an external yfinance `quoteType` pass over
  the 33 distinct symbols to resolve 2,628 of them (2,623 rows moved out of `UNKNOWN`).
- The upstream `mysql_record_raw_pick()` INSERT path calls `resolve_asset_class()` — so **newly
  inserted** picks kept getting tagged `UNKNOWN` at write time and would have needed the same
  reclass every cycle.

### 1.2 The fix's own documentation never deployed (separate bug, found today)
`updates/2026-10-18-legacy-status-backfill-assetclass-reclass-and-metric-freshness-plan.md` was
linked from the headline entry on the live updates page but returned **HTTP 404** on
`https://findtorontoevents.ca/updates/` (verified with a browser UA; default UA gets a misleading
`412 Precondition Failed` from 50webs Apache).

Root cause: two different upload paths, only one of which is complete for `.md`:

| Path | What it uploads | Used by |
|---|---|---|
| `tools/deploy_to_ftp.py --updates-only` | the **whole `updates/` tree** (809 `.md` + `.html`) | manual / full deploy |
| `tools/deploy_audit_files.py --only updates` | a **hard-coded `UPLOADS` list** last extended 2026-06-03 (index.html + ~12 old docs) | `incidents-enhancements-nightly.yml` (nightly) |

So a doc written today only reaches production if someone happens to run the full-tree uploader.
The nightly job silently skips it.

---

## 2. What changed

### 2.1 Committed symbol→asset-class cache (code fix)
`audit_trail/asset_classification.py`:
- new `_SYMBOL_CLASS_CACHE_PATH = audit_trail/symbol_asset_class_cache.json` (committed, hand-verified).
- new `_symbol_class_cache_lookup()` — fail-open: unreadable/absent/garbage cache ⇒ `None` ⇒
  exactly the old behaviour. `UNKNOWN` entries and non-enum values are rejected, so the cache can
  never class something as `UNKNOWN` (pointless) or crash the INSERT path.
- `resolve_asset_class()` now consults the cache **only after** `classify_asset()` returns
  `UNKNOWN`. Priority order is otherwise untouched, so crypto guard / `=F` / `=X` suffix overrides /
  explicit `raw` category hints all still win — the cache cannot mislabel PEPEUSDT as a bond.

Seed cache content (from the yfinance-verified backfill): 29 symbols —
`AMD, QUBT, PLTR, SOFI, SNDL, DNA, LCID, RIVN, IONQ, OPEN, NIO, AXP, TXN, GS, AMC` (EQUITY) and
`EFA, USO, EMB, EEM, TLH, MUB, USMV, EWY, EWA, UNG, XBI, XLK, DBA` (ETF).

### 2.2 Deploy gap (docs fix)
- `tools/deploy_audit_files.py`: the `updates` tag now also expands `updates/*.md` modified in the
  last 45 days, so the nightly FTP job keeps recently-written docs live without a hand-maintained
  list. Explicit `UPLOADS` entries still win (no duplicates).
- `updates/index.html` headline entry corrected (it claimed "No code files were modified this
  session", which stopped being true when the classifier fix landed) and now references this file.

---

## 3. Verification

| Check | Result |
|---|---|
| `python3 -c "import py_compile; py_compile.compile('audit_trail/asset_classification.py', doraise=True)"` | OK |
| Behavior cases: `PLTR/AMD→EQUITY`, `EFA/XLK/USO→ETF`, crypto/forex/futures paths unchanged, junk still `UNKNOWN` | 13/14 PASS (`TLT→ETF` is pre-existing ordering, untouched) |
| Repo test suite | **146 passed, 2 failed** — both failures (`test_equity_30d_pf_above_tier2_floor`, `test_commodity_30d_kill_in_progress`) reproduce on the pre-change file (verified by swapping it back): data-driven pipeline-gap assertions, not regressions |
| Live `…/updates/2026-10-18-legacy-status-…-plan.md` | was **404**, **200** after re-upload |
| Live `…/updates/index.html` | HTTP 200 |
| `at_raw_picks.status IS NULL` | **0** (was 3,126) |
| OPEN rows by class after backfill | EQUITY 2,567 · ETF 211 · FOREX 125 · FUTURES 114 · CRYPTO 100 · UNKNOWN 6 · BOND 3 |

**P0 post-PR-#734 insert probe — VERIFIED (2026-10-18 06:58 UTC).** The first post-merge batch
landed at 06:58:38-39Z: 8 rows, all `status='OPEN'` (the NULL-status root cause is dead) and all
canonically classified — `DOGEUSDT`/`BTCUSDT`/`ETHUSDT`/`BNBUSDT` → CRYPTO, `USDCAD=X`/`EURGBP=X`
→ FOREX, `AMZN` → EQUITY. `at_raw_picks.status IS NULL` remains **0**. One row, `DNA`, still came
back **UNKNOWN**: production runs the merged code, which does not yet contain this cache — `DNA` is
literally one of the 29 symbols in `symbol_asset_class_cache.json`, so that row is a live proof
that the fix is needed and will classify it as EQUITY the moment it reaches `main`. (A 5-min
watcher polled the whole window and was shut down after this batch was confirmed.)

---

## 4. Rest of the P1 list — what was closed today, and what the gaps actually are

### 4.1 CLOSED — hard-coded core stats in `template.html` are now payload-driven
`audit_dashboard/template.html`:
- L850 truth-layer line: the `2026-05-29 (n=73,817): WR 25.28% / PF 0.61` prose is now explicitly
  labelled a **dated one-off DB audit**, and a new `#truth-live-headline` chip renders
  `summary.overall_win_rate` / `profit_factor` / `valid_closed_picks` / `W-L` with the payload's
  `generated_at` — recomputed every hourly `dashboard_data.json` run.
- L1472 `Real-money posture as of 2026-05-31` is now `#real-money-posture`: a live chip row built
  from `performance.asset_class_health` (status · WR · PF · n · `sizing_allowed`) plus
  `money_ready_verdicts`, stamped with `generated_at`. The old prose is preserved inside a
  `<details>` forensic snapshot.
- Fail-open: if the payload is missing both spans keep their static/loading text. Rendering hooks
  `DOMContentLoaded` + the existing `dashboard-data-loaded` event + 1.5/4/9 s safety retries.
- Verified in headless Chromium against `tools/serve_local.py` (`/audit/template.html`): with the
  fresh payload the chip reads `WR 44.8% · PF 1.15 · n=7470 valid closed · 3532W/4210L — regenerated
  2026-10-18 05:36 UTC` and the posture row shows all 9 classes with live n. Zero page errors; all
  15 inline `<script>` blocks still pass `node --check`.

### 4.2 CLOSED (as a bug) — the two "404 sidecars" are phantom names
`pick_funnel_nightly.json` and `surface_metrics_export.json` have **no producer and no consumer**
anywhere: a repo-wide grep (any extension, worktrees excluded) finds only the plan doc that named
them, and neither string appears in the live `/audit/` HTML. Both live URLs 404 because nothing
ever generated them. The real funnel sidecars (`pick_funnel_today.json`, `pick_funnel_90d.json`,
`nav_surface_edge_matrix.json`) all answer **HTTP 206**. Action taken: no code change needed —
this item is closed, not deferred.

### 4.3 CLOSED — local `audit_dashboard/data` mirror rot
Root cause: `audit_dashboard/data/dashboard_data.json` is **gitignored** (`.gitignore:218`, ~24 MB,
regenerated only in CI), so a dev box's copy is whatever someone last pulled by hand — here,
`generated_at 2026-06-02`, i.e. 4.5 months stale, while production served fresh numbers. New helper
**`tools/refresh_local_audit_mirror.py`** pulls the CORE payloads (and `--all` for every local
`*.json`) from `https://findtorontoevents.ca/audit/data/`, atomically, refusing to clobber a local
file with an error page. First run: **8/8 core payloads refreshed** (`dashboard_data.json` was
3,281 h old → now `2026-10-18T05:36Z`, matching production).

### 4.4 ASSESSED — per-class emitter coverage (the real shape of the hole)
DB probe, `ejaguiar1_stocks.at_raw_picks`, last 30 d:

| class | inserts / 30 d | last insert | emitter path |
|---|---|---|---|
| CRYPTO | 4,208 | 2026-10-18 04:57 | `AlphaEngine` / aggregator (+17 `mega_mutation`) |
| FOREX | 2,207 | 2026-10-18 04:57 | `AlphaEngine` / aggregator |
| EQUITY | 1,295 | 2026-10-18 04:57 | `AlphaEngine` / aggregator |
| FUTURES | 742 | 2026-10-18 04:57 | `AlphaEngine` / aggregator |
| ETF | 473 | 2026-10-18 04:57 | `AlphaEngine` / aggregator |
| BOND | 28 | 2026-10-18 03:02 | `AlphaEngine` / aggregator |
| COMMODITY / MEME / PENNY_STOCK | **0** | — (0 in 90 d) | — |

**Every production row for 30 days came from one funnel** (`source_system='AlphaEngine'`,
`created_by='aggregator'`). The three zero classes are not dead code — they are blocked,
quarantined, or wired to a different pipe:

- **COMMODITY — deliberately frozen at intake, multiple layers.** `BLOCKED_ASSET_CLASSES =
  {FOREX, COMMODITY, FUTURES, BOND}` (`audit_trail/quality_gates.py:1735`) scores it −60;
  `per_source_volume_cap.py` hard-zeros `multi_asset_cot` COMMODITY intake (`{"COMMODITY": 0.0}`);
  `production_scanner.py` kills COMMODITY `SHORT`/`SELL` emission; `COMMODITY_BLACKLIST` blocks
  pre-write; `CT=F` capped at 40 % of a cycle; and the two live commodity emitters
  (`commodity_inventory_report.py`, `commodity_cross_momentum.py`) are **DEFAULT-OFF** behind
  `COMMODITY_INVENTORY_REPORT_ENABLED` / `COMMODITY_CROSS_MOMENTUM_ENABLED`, which **no workflow
  sets**. So the class cannot produce a pick without an operator decision.
  **Plus a classifier artifact** (verified against `origin/main`, so pre-existing, NOT caused by
  this cache change): `resolve_asset_class()` short-circuits `*=F*` → `FUTURES` **before** the
  commodity patterns, so `GC=F` / `CL=F` / `SI=F` land in the FUTURES bucket, not COMMODITY —
  part of why the COMMODITY tile reads empty. Fixing that is a one-line ordering decision
  (`_COMMODITY_RE` before the `=F` override) but it moves rows between classes, so it is left as
  an operator call, not smuggled in with this change.
- **PENNY_STOCK — healthy engine, wrong pipe.** `.github/workflows/penny-stock-picks.yml` runs
  green every weekday 12:00 UTC (`scripts/penny_stock_picks.py`) but writes to a **separate PHP
  API** (`findtorontoevents.ca/findstocks/portfolio2/api`) + `findstocks/portfolio2/data/
  penny_picks_latest.json`. It never touches `at_raw_picks`, so the class is invisible to `/audit`
  per-class stats. Wiring = a sync step, not a new emitter.
- **MEME — prototype only.** `meme_momentum_squeeze.py` / `june2026_research_candidates.py` define
  a MEME universe and `*_v2` strategies, but nothing in the aggregator source map emits a MEME
  `active_picks.json`.
- **BOND — emitting, but thin and frozen.** 28 picks/30 d, `bond-agent.yml` + `etf-bond-scanner.yml`
  both green daily; BOND is in `BLOCKED_ASSET_CLASSES` and has n=0 in `asset_class_health`.

### 4.5 Still open

- **P2** — per-class real-money-grade pick quality (0/N classes money-ready; overall realised
  WR 44.8 % / PF 1.15 is coin-flip after costs).
- **P2** — extend the live-chip treatment (§4.1) to the remaining dated prose blocks on `/audit`
  (e.g. "DATA QUALITY IMPROVEMENTS (2026-05-31)", the COMMODITY filter-survival gap note) and give
  every sidecar a `generated_at` staleness tooltip.
- **Operator decisions needed** (not code): lift or keep the COMMODITY freeze; decide whether the
  PENNY pipe syncs into `at_raw_picks`; decide whether MEME gets an emitter at all.
- **Deploy blocker for §4.1**: `template.html` only reaches production via the hourly
  `audit-dashboard.yml` cron rebuilding `index.html` **from `main`** — my branch-level edit is not
  visible to it until merged.

*NFA — research/educational.*