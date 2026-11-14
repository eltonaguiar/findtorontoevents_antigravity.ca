# Quick Wins — AI/ML Algorithm & Data Staleness Audit (MERGED)

**Worktree:** flaxen-hair | **Repo root:** /home/eaguiar2015/findtorontoevents_antigravity.ca
**Date:** 2026-11-14 | **Today:** 2026-11-14

## Sources merged
- **My audit** (flaxen-hair worktree): recomputation of `pnl_pct` on closed picks, non-unique pick IDs, `ml_score==confidence`, stale 2026-03/04 picks, no live PnL, empty `meta_strategy.db` tables, mutual funds zero coverage, `dbpasses.txt` at `/home/eaguiar2015/dbpasses.txt` (outside repo, live keys — not read/exposed).
- **Peer audit** (`audits/2026-11-14/finpredict-v4_2026-11-14-1555/`): live Binance/forex cross-checks, 365 GitHub Actions workflows, MySQL + SQLite health, three divergent data stores, Alpha Engine dead, TP/SL resolution bug, intrabar truth, 1,864 duplicate groups, 22,947 ghost rows, specific PnL mismatch magnitudes.
- **Peer proposed fixes** (`updates/2026-11-14-ML-AUDIT-childlike-airport/proposed_fixes/`): per-asset-class FIX_PROPOSED.md for stocks, bonds, etfs, forex, crypto, mutual_funds, overall.

## Folder structure

| Folder | Scope |
|---|---|
| `01_overall/` | Cross-cutting fixes (all asset classes) — MERGED with peer findings |
| `02_equity_stocks/` | Stocks / equity — MERGED |
| `03_bonds/` | Bonds / treasury / fixed income — MERGED |
| `04_etfs/` | ETFs — MERGED |
| `05_mutual_funds/` | Mutual funds (coverage gap) — MERGED |
| `06_forex/` | Forex — MERGED |
| `07_crypto/` | Crypto — MERGED |
| `08_commodities_futures/` | Commodities / futures — MERGED |
| `shared/` | Reusable scripts: PnL normalizer, pick-ID validator |

## Top cross-cutting findings (verified by both audits)

1. **PnL unit mismatch (CRITICAL):** `pnl_pct`/`realized_pnl_pct` stored as decimal ratio in some rows and as percent (×100) in others — up to 100× disagreement. Confirmed by recomputation AND by aggregate PF divergences (CRYPTO 4.9x, EQUITY -7.9x, FOREX -18.7x, FUTURES +226x).
2. **Non-unique pick IDs:** date-only IDs produce duplicates (my `vix_reversal::SI=F` ×4+; peer's 1,864 duplicate groups in CRYPTO 90d raw).
3. **ml_score == confidence:** on every OPEN pick — but ML code is SOUND; inversion is a DATA bug (conf≥0.90 → 14.4% WR; conf 0.50–0.60 → 60.3% WR).
4. **Stale picks:** 2026-03/04 resolved picks (~8 months); 172-day SQLite active picks; `at_signal_outcomes` last resolved 2026-03-04 (254 days stale).
5. **No verifiable live PnL:** multi_asset_picks.json (2026-11-12) all forward_test_only with null PnL; live dashboard shows 0 active picks (Alpha Engine dead).
6. **Three divergent data stores:** SQLite `live_picks.db` (128/129 picks 172 days stale), MySQL `trading_picks` (90,523 open / 21 active), JSON dashboard files (0 active) — divergent counts/ages/PnL.
7. **dbpasses.txt** at `/home/eaguiar2015/dbpasses.txt` (outside repo, live keys — not read/exposed). Not examined by either audit.
8. **Mutual funds:** ZERO coverage anywhere — confirmed by both audits.
9. **Empty tables:** my `meta_strategy.db` 5 empty tables; peer's `audit_trail.db` ALL 9 tables empty + `consensus_active_picks.json` empty.
10. **TP/SL resolution bug:** resolver checks TP before SL (close-price fallback), unfiltered OHLCV bars incl. pre-entry data → 92.4% TP_HIT rate impossible with fair R:R.

## Recommended fix order (P0 → P3)

**P0 (foundation — do these first, they block everything downstream):**
1. PnL calc + staleness refresh (recompute signed pnl_pct for ALL active picks, refresh current_price/last_checked)
2. asset_class backfill + MUTUAL_FUND class/schema
3. Pick lifecycle (emit CLOSED/EXIT/TP/SL; close/expire stale picks)
4. Fix Alpha Engine cancellations (root cause of 0 dashboard picks)
5. Fix TP/SL resolution bug (TP-before-SL close-price fallback)

**P1:**
6. audit_trail.db population (8 empty tables)
7. Ghost MEMECOIN row dedup (22,947 ghost rows)
8. TIME_EXIT limbo (4,220 of 4,820 unresolved)
9. JSON artifact freshness gate (dashboard_data.json 26d, picks_now.json 7d, etc.)
10. Fix frozen dashboard prices (live cross-check mismatches)

**P2:**
11. Decouple ml_score from confidence (data bug, not code bug)
12. Unique pick ID enforcement (1,864 duplicate groups)
13. recent_picks.txt header fix

**P3:**
14. dbpasses — nothing (no secrets; do not create dbpasses.txt unless requested)

## Shared scripts
- `shared/normalize_pnl_units.py` — recompute `pnl_pct` as decimal ratio (writes `.bak`)
- `shared/validate_pick_ids.py` — CI-enforced unique pick IDs

Per AGENTS.md: document each implemented fix in `updates/<date>-<description>.md` and commit fix + doc on a clean branch containing only your changes. Never push branches containing other authors' commits.
