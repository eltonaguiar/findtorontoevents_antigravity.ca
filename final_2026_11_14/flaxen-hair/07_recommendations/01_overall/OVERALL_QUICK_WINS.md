# Overall / Cross-Cutting Quick Wins — MERGED

**Scope:** All asset classes (equity, bonds, ETFs, mutual funds, forex, crypto, commodities/futures)
**Merged sources:** My flaxen-hair audit + peer `finpredict-v4` audit (`audits/2026-11-14/finpredict-v4_2026-11-14-1555/`) + peer `childlike-airport` proposed fixes (`updates/2026-11-14-ML-AUDIT-childlike-airport/proposed_fixes/`)
**Date:** 2026-11-14 | **Today:** 2026-11-14

## Consolidated severity ordering (P0 → P3)

| Priority | Quick win | Severity | Effort | Source |
|---|---|---|---|---|
| **P0** | PnL calc + staleness refresh — recompute signed `pnl_pct`/`unrealized_pnl_pct` for ALL active picks (129 in SQLite live_picks.db, ~172 days stale), refresh `current_price`/`last_checked`, flag >30–60 day stale picks | Critical | Small/Med | Peer childlike §3.1–3.2; my quick_wins OW-1 |
| **P0** | `asset_class` backfill — backfill 6 DB rows + 17 dashboard `UNK` rows via `alpha_engine/asset_class.py`; add `MUTUAL_FUND` class + symbol set + schema | Critical | Small | Peer childlike §3.3; my quick_wins OW-7/05_mutual_funds |
| **P0** | Pick lifecycle — emit `CLOSED/EXIT/TP/SL` into `pick_history`; close/expire stale picks via `audit_trail/universal_pick_resolver.py` | Critical | Small/Med | Peer childlike §3.4; my quick_wins OW-6 |
| **P0** | Fix Alpha Engine cascading cancellations — `cancel-in-progress` on 2h cron kills 45–60 min runs (root cause of 0 dashboard picks) | Critical | Med | Peer audits infra QW-1 (`.github/workflows/alpha-engine-live.yml`) |
| **P0** | TP/SL resolution bug — resolver checks TP before SL (close-price fallback), unfiltered OHLCV bars incl. pre-entry data → 92.4% TP_HIT rate impossible with fair R:R | Critical | Med | Peer `investigate_tp_sl_bug.py`; audits overall QW-4 |
| **P1** | `audit_trail.db` population — 8 empty tables (consensus_picks, feature_edge_snapshots, symbol_strategy_stats, strategy_stats, raw_picks, audit_events, filter_log, bt_backtest_trades) via `alpha_engine/audit_sync.py` | High | Small | Peer childlike §3.5; my quick_wins OW-5 |
| **P1** | Ghost MEMECOIN row dedup — 22,947 ghost rows (DOGEUSDT ×3,569 identical); DELETE SQL + UNIQUE index | High | Small | Peer audits infra QW-5, overall QW-2 |
| **P1** | TIME_EXIT limbo — 4,220 of 4,820 TIME_EXIT picks unresolved (6.2%); batch resolver | High | Small | Peer audits infra MF-1/MF-4, overall MF-4 |
| **P1** | JSON artifact freshness gate — `dashboard_data.json` 26d, `picks_now.json` 7d, `picks_now_live_pnl.json` 45h, `db_freshness.json` 175d stale | High | Small | Peer audits equity 1.2, infra MF-3; my quick_wins OW-2 |
| **P1** | Fix frozen dashboard prices — live Binance/forex cross-check: NEARUSDT +0.72pp, XRPUSDT +1.46pp, BTCUSDT +0.97pp understated | High | Small | Peer audits market_crossref_report.md; forex/forex_deep_dive.md |
| **P2** | Decouple `ml_score` from `confidence` — ML code is SOUND; inversion is a DATA bug (conf≥0.90 → 14.4% WR; conf 0.50–0.60 → 60.3% WR) | Medium | Small | Peer audits INDEX.md L113; childlike declares ML sound |
| **P2** | Unique pick ID enforcement — 1,864 duplicate groups in CRYPTO 90d raw; no `pick_id` UNIQUE constraint | Medium | Small | Peer audits overall QW-2, forex MF-3; my quick_wins OW-3 |
| **P2** | `recent_picks.txt` header fix — claims "Past 2 Hours" but data dated 2026-03-11 (8 months stale) | Low | Trivial | My quick_wins OW-8 |
| **P3** | dbpasses — nothing to fix; no `dbpasses.txt` examined (live keys at `/home/eaguiar2015/dbpasses.txt`, outside repo) | None | None | Peer childlike §3.7; corrections.md |

**Rule (peer childlike §4):** Do not start per-asset-class work until P0 is complete — stale/mislabeled data invalidates per-class results.

## Consolidated cross-cutting findings (verified by both audits)

### Three divergent data stores (NEW — not in my original audit)
| Store | Active picks | Age | State |
|---|---|---|---|
| SQLite `data/live_picks.db` | 128/129 active | ~172 days stale (2026-05-24/25) | All marked ACTIVE/OPEN, never refreshed |
| MySQL `trading_picks` | 90,523 open / 21 active | Mixed | Divergent counts from SQLite |
| JSON dashboard files (`dashboard_data.json`, `picks_now.json`, `picks_now_live_pnl.json`) | 0 active on live dashboard | 26d / 7d / 45h stale | Alpha Engine dead → empty shell |

### Specific PnL mismatches (live recomputation vs dashboard claim)
| Symbol | Dir | Entry | Dashboard current | Live price | Dashboard claimed | Recomputed | Error |
|---|---|---|---|---|---|---|---|
| NEARUSDT | SHORT | 3.324 | 3.233 | 3.209 (Binance) | +2.74% | +3.46% | +0.72pp understated |
| XRPUSDT | SHORT | 0.9842 | 0.9842 (frozen at entry) | 0.9698 (Binance) | 0.0% | +1.46% | +1.46pp understated |
| BTCUSDT | SHORT | 66300.0 | 66300.0 (frozen at entry) | 65658.01 (Binance) | 0.0% | +0.97% | +0.97pp understated |
| USDCAD=X | SHORT | 1.4269 | ≈entry | 1.42603 (er-api) | -0.0% | +0.061% | ~+0.06pp understated |
| NZDUSD=X | LONG | 0.552517 | ≈entry | 0.55273 (er-api) | -0.0% | +0.0385% | ~+0.04pp understated |

### Aggregate dashboard-vs-raw-DB PF/WR divergences
| Class | Dashboard PF | Raw DB PF | Ratio | Dashboard WR | Raw DB WR |
|---|---|---|---|---|---|
| CRYPTO | 1.801 | 0.371 | 4.9x inflated | 51.57% | 39.38% |
| EQUITY | 0.704 | 5.555 | -7.9x (filter inverts) | 37.39% | 66.69% |
| FOREX | 2.02 | 0.108 | -18.7x | 45.54% | 83.28% |
| FUTURES | 0.582 | 131.6 | +226x outlier artifact | 7.14% | 49.98% |
| ETF | 0.338 | 2.594 | -7.7x | 30.77% | 67.77% |

### Staleness summary (vs today 2026-11-14)
- `at_signal_outcomes` intrabar truth: last resolved **2026-03-04** (254 days stale — note source audit has internal arithmetic inconsistency; Mar 4 date is authoritative anchor)
- `dashboard_data.json`: **26 days** (2026-10-19)
- `db_freshness.json`: **175 days** (2026-05-23)
- `hourly_update_last_run.json`: **44.6h** (2026-11-12)
- `picks_now_live_pnl.json`: **45h**, prices frozen at Nov 12
- `feature_signals_latest.json`: **79.5h**, all 19 picks forward_validated=false
- `hyro_quan_bridge.json`: **45.8h**
- `dna_factory.db` factory_strategies: **2026-05-26** (~172 days)
- AI Challenge / Tournament active picks: **~8 months** (2026-03-15), still OPEN, PnL stuck at 0.0

### Mutually confirmed findings (both audits)
- **PnL unit inconsistency:** ratio vs percent, up to 100× disagreement (my recomputation); confirmed in spirit by peer's aggregate PF divergences (4.9x–226x)
- **Non-unique pick IDs:** date-only IDs produce duplicates (my `vix_reversal::SI=F` ×4+); peer confirms 1,864 duplicate groups in CRYPTO 90d raw
- **ml_score==confidence:** identical on every OPEN pick (my finding); peer clarifies ML CODE is sound, inversion is a DATA bug
- **Stale picks:** 2026-03/04 (my finding) + 172-day SQLite picks (peer finding)
- **No live PnL:** confirmed by both (my forward_test_only null PnL; peer's 0 dashboard picks, null pnl_pct)
- **Empty tables:** my `meta_strategy.db` 5 empty tables; peer's `audit_trail.db` ALL 9 tables empty + `consensus_active_picks.json` empty
- **Mutual funds:** ZERO coverage anywhere — confirmed by both
- **dbpasses.txt:** at `/home/eaguiar2015/dbpasses.txt` (outside repo, live keys — not read/exposed); not examined by either audit

## Files referenced across both audits (consolidated)
- `alpha_engine/asset_class.py:22-62,125,130,191,263,269` — symbol sets + normalization (single source of truth); add MUTUAL_FUND class/symbol set
- `alpha_engine/audit_sync.py` — portfolio/MySQL sync path writing audit_trail tables
- `alpha_engine/production_scanner.py` — production scan orchestrator (Alpha Engine — DEAD)
- `alpha_engine/fetch_stock_prices.py` — server-side stock price fetcher
- `alpha_engine/fetch_stock_prices.py` — stock price fetcher
- `audit_trail/universal_pick_resolver.py` — Active pick TP/SL/time exit resolver (write path for pick_history)
- `audit_trail/dashboard_generator.py` — Dashboard payload consumer
- `audit_trail/exit_events.json` — exit events
- `audit_trail/trade_geometry.py` — `_ASSET_CLASS_MAP`/`AssetClass`
- `copy_trader_intel/non_crypto_consensus.py` — non-crypto consensus (FOREX block bypass)
- `copy_trader_intel/outcome_resolver.py:252` — resolved PnPct `round((current - entry) / entry, 4)`
- `copy_trader_intel/data/consensus_active_picks.json` — consensus output (empty, 0 picks)
- `copy_trader_intel/data/consensus_active_picks.json` — consensus output (empty, 0 picks)
- `ml_gatekeeper/gatekeeper.py:73,25-32` — ASSET_CLASS_MAP; ab_router import masking; `ML_GATE_DROP_LEAKAGE` mask
- `ml_ranker_fixed.py` — ML ranker (declared sound by peer)
- `mercury2/scanner.py:127-128,481-485` — price enrichment + long/short PnL calc pattern
- `forward_trade_executor.py:100-102` — canonical long/short PnPct formula reference
- `dashboard/generate_dashboard.py:15,24` — PnL display consumer
- `tools/db_freshness_check.py` — DB freshness guardian (extend to JSON files + T-1 day gate)
- `data/live_picks.db` — SQLite live_picks (128/129 stale) + pick_history (136 rows, all REGISTERED)
- `dashboard/live_picks.json` — 17 active picks all `asset_class='UNK'`
- `alpha_engine/data/active_picks.json` — 99 local picks, orphaned (never reach dashboard)
- `stocksunify2_active_picks.json` — 14 equity picks ~79 days stale
- `active_picks_bond.json` — 7 bond picks fresh (2026-11-12)
- `active_picks_etf.json` — 16 ETF picks fresh (2026-11-12T18:17:06Z)
- `data/audit_trail.db` — SQLite, all 9 tables empty (0 rows)
- `data/cftc_cot/calendar.json` — stub from 2026-06-05, tickers empty
- `coinglass_strategies/data/coinglass.db` — positions stale (max opened 2026-11-06)
- `meta_strategy/data/meta_strategy.db` — 5 empty tables (my finding)
- `multi_asset/data/multi_asset_closed.json` (93 rows) / `institutional_closed.json` (23 rows) — PnL unit mismatches (my recomputation)
- `multi_asset/data/multi_asset_picks.json` (41 picks) / `institutional_picks.json` (22 picks) — forward_test_only, null PnL

## Per-asset-class quick win folders
See `quick_wins/02_equity_stocks/`, `03_bonds/`, `04_etfs/`, `05_mutual_funds/`, `06_forex/`, `07_crypto/`, `08_commodities_futures/` for per-class detail.

## Shared scripts
- `quick_wins/shared/normalize_pnl_units.py` — recompute `pnl_pct` as decimal ratio (writes `.bak`)
- `quick_wins/shared/validate_pick_ids.py` — CI-enforced unique pick IDs

Per AGENTS.md: document each implemented fix in `updates/<date>-<description>.md` and commit fix + doc on a clean branch containing only your changes.
