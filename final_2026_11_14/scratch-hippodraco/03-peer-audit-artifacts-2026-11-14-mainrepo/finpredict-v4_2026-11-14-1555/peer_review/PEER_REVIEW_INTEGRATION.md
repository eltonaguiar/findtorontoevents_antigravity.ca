# Peer Review Integration — childlike-airport (ML/Algo Audit)
**Peer auditor:** Kilo (childlike-airport worktree)  
**Peer audit file:** `updates/2026-11-14-ML-AUDIT-childlike-airport.md`  
**Peer audit time:** 2026-11-14T16:04:48Z  
**This integration:** 2026-11-14T16:17Z

---

## Peer Findings That Extend Our Audit

### 1. `data/live_picks.db` — SQLite Database (NOT MySQL)
The peer audited the **local SQLite database** `data/live_picks.db`, which our audit did not examine.

| Finding | Severity | Our Audit Status |
|---------|----------|------------------|
| **128 of 129 active picks are 172 days stale** (2026-05-24/25) | Critical | **NEW** — we audited MySQL DB and JSON files, not this SQLite DB |
| **PnL sign contradictions** — `unrealized_pnl_pct` has opposite sign of `pnl_pct` in 8 picks | Critical | **NEW** — SQLite-level bug not visible in JSON feeds |
| **PnL calc mismatch** — 15 picks where `unrealized_pnl_pct` != `(current_price - entry_price) / entry_price` | High | **NEW** |
| **Missing `asset_class`** — 6 picks in DB + 17 picks in `dashboard/live_picks.json` show `asset_class='UNK'` | Medium | **NEW** |
| **`pick_history` has only REGISTERED events** — no CLOSED/EXIT/TP/SL events ever recorded | High | **Partially covered** — we noted 4,220 TIME_EXIT limbo picks but not this root cause |
| **`audit_trail.db` completely empty** — all 9 tables have 0 rows | High | **NEW** — we found `db_freshness.json` is 175 days stale but not that the underlying SQLite audit DB is empty |
| **`consensus_active_picks.json` is empty** | Low | **NEW** — our dashboard metrics audit showed 0 consensus picks but didn't trace to empty JSON |
| **`stocksunify2_active_picks.json` is 79 days stale** | Medium | **Partially covered** — we noted stocksunify2 was stale but not exact age |
| **`active_picks.json` is 169 days stale / empty** | Medium | **NEW** |
| **No mutual fund coverage anywhere** | Medium | **NEW** — we didn't check for mutual funds |

### 2. ML Algorithms Peer-Reviewed
The peer read key ML files and found them **mathematically sound**:
- `ml_ranker_fixed.py` — proper chronological train/test split, ROC-AUC, isotonic calibration, overfitting guard
- `ml_gatekeeper/gatekeeper.py` — trained on 3,500+ real closed picks, leakage features documented
- `alpha_engine/asset_class.py` — canonical single source of truth for asset-class normalization

**Our audit did not review these files.** The peer's finding that the ML code is sound **contradicts our finding of "inverted ML confidence"** — the issue is not the ML code itself, but the **data feeding it** (inverted confidence bands in the DB due to schema bugs or miscalibrated upstream generators).

### 3. Peer Proposed Fixes
1. Refresh stale picks (re-run price enrichment for 129 active picks)
2. Fix PnL sign bug (`unrealized_pnl_pct = (cp-ep)/ep`)
3. Backfill `asset_class` using `alpha_engine.asset_class.normalize_asset_class`
4. Add mutual fund class to `asset_class.py` + strategies + DB schema
5. Emit CLOSED/EXIT/TP/SL events into `pick_history`
6. Populate `audit_trail.db` (consensus_picks, feature_edge_snapshots, etc.)
7. Investigate why `consensus_active_picks.json` is empty
8. Harmonize freshness schedules

### 4. Cross-Cutting Observations
- **The SQLite DB and MySQL DB are divergent.** `live_picks.db` has 129 rows (mostly 172 days stale), while MySQL `trading_picks` has 90,523 rows per `db_health.json`. The system has **two parallel data stores** that are not synchronized.
- **The dashboard JSONs are a third data layer** (`dashboard_data.json`, `picks_now.json`, `picks_now_live_pnl.json`). These three layers (SQLite, MySQL, JSON) show different counts, different ages, and different PnL values for the same picks.
- **Our audit focused on JSON + MySQL; the peer focused on SQLite + JSON.** Together we cover all three layers, revealing a **three-way data divergence** that neither audit caught alone.

---

## Updated Priority Based on Peer + Our Findings

| Priority | Fix | Source |
|----------|-----|--------|
| **P0** | Fix Alpha Engine cancellations (root cause of 0 dashboard picks) | Our audit |
| **P0** | Fix PnL sign bug in `data/live_picks.db` (8 picks have inverted signs) | Peer audit |
| **P0** | Refresh 172-day stale SQLite picks (128/129) | Peer audit |
| **P1** | Fix frozen prices in dashboard JSON (crypto + forex showing 0% PnL) | Our audit |
| **P1** | Backfill missing `asset_class` (6 in DB + 17 in dashboard JSON) | Peer audit |
| **P1** | Populate empty `audit_trail.db` (all tables 0 rows) | Peer audit |
| **P2** | Purge 8-month zombie AI Challenge picks | Our audit |
| **P2** | Fix inverted ML confidence bands (data issue, not code issue) | Both audits |
| **P2** | Add pick lifecycle events (CLOSED/EXIT/TP/SL) to `pick_history` | Peer audit |
| **P3** | Add mutual fund class | Peer audit |
| **P3** | Deduplicate three-way data stores (SQLite, MySQL, JSON) | Combined finding |

---

## Files to Reference
- Peer audit: `peer_review/2026-11-14-ML-AUDIT-childlike-airport.md`
- Our audit: `INDEX.md`, `dashboard_data_report.md`, `market_crossref_report.md`
