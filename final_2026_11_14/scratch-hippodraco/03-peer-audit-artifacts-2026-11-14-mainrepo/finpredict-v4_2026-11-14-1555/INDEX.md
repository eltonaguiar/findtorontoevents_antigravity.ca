# Prediction System Audit Archive — CORRECTED & INTEGRATED
**Date:** 2026-11-14  
**Auditor:** Kilo (finpredict-v4 worktree iteration)  
**Worktree lineage:** finpredict → finpredict-v2 → finpredict-v3 → finpredict-v4  
**Audit worktree:** `wt-audit-prediction-system` (isolated branch from fresh `origin/main`, commit `7c80a160759`)  
**Archive:** `audits/2026-11-14/finpredict-v4_2026-11-14-1555/`  
**Last updated:** 2026-11-14T17:55Z (post peer-review round 2)

## Scope
Full audit of the prediction system (stocks, crypto, forex, bonds, ETFs, futures, commodities) at
https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/ with live output at
findtorontoevents.ca/audit and findtorontoevents.ca/audit/hyrotrader.

## Reports Included
| # | File | Description |
|---|------|-------------|
| 1 | `actions_health_report.md` | GitHub Actions workflow health (365 workflows) |
| 2 | `dashboard_data_report.md` | Active picks, frozen data, closed performance by asset class |
| 3 | `market_crossref_report.md` | Cross-reference of picks against live public market data |
| 4 | `crypto_deep_dive.md` | CRYPTO: live Binance verification, timestamp freshness, metric validation |
| 5 | `forex_deep_dive.md` | FOREX: live rate verification, PR #6 block verification, consensus audit |
| 6 | `noncrypto_deep_dive.md` | EQUITY/ETF/BOND/COMMODITY/FUTURES: alive-vs-dead check |
| 7 | `dashboard_metrics_sources.md` | Dashboard metrics, data sources, filter permutations, HyroTrader audit |

## Evidence Included
| File | Description |
|------|-------------|
| `evidence_money_ready_verdict.json` | Per-asset-class money-ready gates (ALL FAIL) |
| `evidence_intrabar_truth.json` | Honest intrabar-true performance by class (ALL FAIL) |
| `evidence_pick_summary_stats.json` | 14d/48h summary stats; dashboard vs raw DB divergence |
| `evidence_db_health.json` | DB health check showing 22,947 ghost rows |

---

## CONSOLIDATED FINDINGS

### 1. Actions Health — FAIL
- **365 workflow files** (361 active, 4 disabled)
- **28 workflows** failed their most recent run
- **39 workflows** have >=3 failures/cancellations in last 5 runs
- Repeat offenders: Live Trading Bot, ALPHA ENGINE, Autonomous Trading Bot, Outcome Resolver
- **20 workflows never ran; 19 last ran >90 days ago**
- **Alpha Engine (primary scanner) is DEAD**: last 10 runs = 9 cancelled + 1 failure (~24h outage)

### 2. Active Picks — FAIL (all asset classes)
**Correction:** The live dashboard shows **20 curated active picks** (`dashboard_data.json` generated 2026-11-14T14:30Z). The "0 active picks" claim in our original audit referred to the **stale local repo copy** (Oct 23), not the deployed site. The Alpha Engine is impaired (93 forex KeyError failures in 24h) but the DB is actively writing.

| Asset Class | Live Picks | Avg Open PnL | Honest WR | Honest PF | n | Verdict |
|-------------|------------|--------------|-----------|-----------|---|---------|
| **CRYPTO** | 3 (curated) | — | 35.9% | 0.92 | 3,705 | FAIL |
| **EQUITY** | 757 | **-5.22%** | 59.0% | 0.934 | 249 | FAIL |
| **FOREX** | 2 (curated) | +0.26%* | 32.2% | 0.66 | 612 | FAIL |
| **COMMODITY** | 4 | +3.57% | 40.2% | 1.026 | 229 | FAIL |
| **ETF** | 1,722 | **-0.20%** | 2.3% | 0.022 | 44 | INSUFFICIENT_N |
| **BOND** | 1,293 | **-1.66%** | 7.7% | 0.391 | 26 | INSUFFICIENT_N |
| **FUTURES** | 0 | N/A | 42.3% | 1.094 | 52 | INSUFFICIENT_N |
| **MEMECOIN** | — | — | 29.4% | 0.661 | 102 | FAIL |

\* FOREX avg from cached `picks_now_live_pnl.json`.

**0/9 asset classes pass money-ready criteria.**

### 3. Frozen / Stale Data — FAIL (corrected)
| Issue | Severity | Details |
|-------|----------|---------|
| **Local `dashboard_data.json`** | **CRITICAL** | 26 days old (Oct 19) in repo. **LIVE site is fresh** (2026-11-14T14:30Z). |
| `picks_now.json` | **HIGH** | 2+ days old (Nov 12). Top-25 curated picks. |
| `picks_now_live_pnl.json` | **HIGH** | 2+ days old. 4,310 open picks. Hourly refresh workflow IS running but push may be failing. |
| `at_signal_outcomes` intrabar truth | **MEDIUM** | Freshly computed today (2026-11-14). The "254 days" claim was overstated. |
| `db_freshness.json` | **CRITICAL** | 175 days old. Abandoned file. |
| `hourly_update_last_run.json` | **HIGH** | 44.6h old. |
| `feature_signals_latest.json` | **HIGH** | 79.5h old. |
| `hyro_quan_bridge.json` | **HIGH** | 45.8h old. HyroTrader panels "Loading..." |
| AI Challenge crypto picks | **HIGH** | 8 months old (Mar 2026), still marked active. |
| 4,220 picks in TIME_EXIT limbo | **HIGH** | Only 301/4,820 resolved (6.2%). |
| 22,947 ghost rows | **HIGH** | Mostly MEMECOIN duplicates. **SAFE fix**: mark, do not DELETE. |
| **1,541+ closed picks with ZERO outcome tracking** | **CRITICAL** | Across 13+ systems (rapid_fire, predictions, revival_*, copy_trader_intel, quan_engine, etc.) |
| **33% missing exit_price** on CLOSED picks | **CRITICAL** | 393 of 1,200 closed picks have `exit_price=None` |

### 4. Cross-Market Verification — FAIL
| Symbol | Dir | Dashboard Claim | Live Price | Discrepancy | Age | Verdict |
|--------|-----|-----------------|------------|-------------|-----|---------|
| NEARUSDT | SHORT | PnL +2.74% | $3.209 | Should be +3.46% | ~2.7h | Stale price, understated PnL |
| XRPUSDT | SHORT | PnL 0.0% | $0.9698 | Should be +1.46% | ~2h | Price frozen at entry |
| BTCUSDT | SHORT | PnL 0.0% | $65,658 | Should be +0.97% | ~2h | Price frozen at entry |
| USDCAD=X | SHORT | PnL -0.0% | 1.42603 | Should be +0.06% | ~1.5h | Price frozen at entry |
| NZDUSD=X | LONG | PnL -0.0% | 0.55273 | Should be +0.04% | ~1.5h | Price frozen at entry |

**All verified picks show prices frozen at or near entry_price**, resulting in false 0% PnL readings.

### 5. Dashboard Metrics & Data Sources — FAIL
- **edge, track, FWD WR%, FWD N, score, trust, confidence**: **ALL EMPTY** (0 active picks)
- **Smart Picks, Verified Alpha, High Conviction, Money Ready**: **ALL return None/0**
- **Alpha Engine**: DEAD (9 cancelled + 1 failure in last 10 runs)
- **Kalshi/Polymarket**: Code runs but failures are silent (`|| non-fatal`); output not reaching dashboard
- **Copy Trader**: Pipeline LIVE but output ORPHANED (exists in repo JSON, not in dashboard)
- **Claude Gainer**: Scanner LIVE but output ORPHANED
- **Grok/Mercury AI Tournament**: Gated off by repo variable; historical data stale
- **HyroTrader**: All tables "Loading..."; bridge JSON 46h old; zero journal trades

### 6. Closed Picks — FAIL
- **CRYPTO raw DB (90d)**: n=46,324 total / 2,001 decisive, WR 39.4%, PF 0.371
- **Dashboard recent-closed CRYPTO**: PF 1.80 vs raw DB PF 0.37 (**5x inflation**)
- **Smart Picks CRYPTO**: PF 9.69, WR 78.9% — 91.7% from single source `claude_gainer_st` with only **3 closed rows** in raw DB
- **EQUITY dashboard**: PF 0.70 (losers) while raw DB shows PF 5.56 (winners) — **filter inverts performance**
- **FOREX raw DB**: WR 83.3% but PF 0.108 — many small wins masking catastrophic losses
- **FUTURES raw PF 131.6**: Nonsensical; driven by 1-2 extreme wins across 2,681 rows

### 7. Actual Root Causes (not symptoms)

| ID | Root Cause | Location | Impact |
|----|-----------|----------|--------|
| **P0-1** | Forex `KeyError: 'LONG'` — `_forex_by_sym` dict only has `BUY`/`SELL` keys; signals with `LONG`/`SHORT` crash the scanner | `alpha_engine/scanner.py:2942` | **93 failed Alpha Engine runs / 24h** |
| **P0-2** | `summary_picks.json` win rate > 100% — `wins`/`losses` counted over all rows while `resolved` counts subset | `tools/sync_summary_picks_json.py:63-65` | Published WR of 1,141% for INDEX |
| **P0-3** | Python 3.14 masquerade — 197 workflows set `update-environment: false`, so pinned 3.11 never activates; pandas source-builds against system 3.14 and fails | 197 workflow YAMLs | Install dependencies step fails cluster |
| **P0-4** | Dashboard JS parse failure — malformed nested ternary in `dashboard_enhancements.js` committed since 2026-10-04; entire enhancement IIFE fails to parse | `audit_dashboard/dashboard_enhancements.js` | Edge/Track/FWD-WR columns empty (frontend, not backend) |
| **P0-5** | TP/SL resolution order bug — resolver checks TP before SL in close-price fallback; no intrabar-first-hit logic | `universal_pick_resolver.py`, `outcome_resolver.py` | 92.4% TP_HIT vs 4.5% SL_HIT (mathematically impossible) |
| **P1-1** | Score-PnL disconnect — confidence vs PnL Pearson r = +0.008 | `elite_score` computation | Scores are essentially noise |
| **P1-2** | Filter inversion — dashboard filters hide winners and show losers for some classes | `dashboard_generator.py` | EQUITY dashboard PF 0.70 vs raw DB PF 5.56 |
| **P1-3** | 1,541+ closed picks with zero outcome tracking across 13+ systems | Multiple resolvers | Aggregate WR/PF untrustworthy |
| **P1-4** | `sym_track_*` built from wrong population — active list filtered to closed statuses (always `[]`) | `dashboard_generator.py:1830-1832` | "Track" column dead |

### 8. Verdict — NOT PROFITABLE; MULTIPLE-TESTING / SURVIVORSHIP ARTIFACT
The system runs **100+ strategies** across **9 asset classes** with **365 GitHub Actions workflows** and **~4,300 open picks** in backlog. Despite this massive computational surface:

1. **No asset class passes industry-standard thresholds** (DSR>0.95, PF>1.5, WR>50%, n>=100)
2. **The "best" performers are cherry-picked sub-strategies with tiny n** (11-38 trades) that would not survive Bonferroni correction
3. **Dashboard filters create survivorship bias** by hiding losing cohorts and showing only recent cherry-picked windows
4. **Intrabar-true replay flips 23-24% of "wins" to SL-first**, collapsing headline PF by 2-3x
5. **ML confidence is inverted** (conf>=0.90 -> 14.4% WR; conf 0.50-0.60 -> 60.3% WR) — **data bug, not code bug**
6. **Data quality is catastrophic**: 22,947 ghost rows, 1,541+ untracked closed picks, 33% missing exit_price, three divergent data stores
7. **The upstream pick generator (Alpha Engine) is impaired** by P0-1 forex KeyError — not completely dead
8. **PR #6 FOREX block is bypassed** via cross-asset consensus pipeline

**Conclusion:** The system is not genuinely profitable. The apparent edge in backtests and dashboard summaries is an artifact of running hundreds of strategies until some win by chance, then surfacing only those winners while hiding or killing the losers. The honest intrabar-true metrics, raw DB aggregates, and live market cross-checks all confirm net-negative or break-even performance across every asset class.

---

## Unverified / Could Not Verify
- Exact current PnL for CRYPTO picks on the live dashboard (crypto active picks are served from a separate endpoint not located in this audit; the 3 cached picks found may not match what a user sees)
- Real-time status of Kalshi/Polymarket prediction market feeds (data files 404 on live site; code runs but output path unknown)
- Peer agent findings referenced at `C:\Users\zerou\Desktop\chat_transcript_2026-11-14.md` — Windows path not accessible from Linux environment; no equivalent local file found

## Corrections to Our Original Findings

**FALSE — "0 active picks" / "empty dashboard":**
- Our claim that "the live dashboard shows 0 active picks" (§2, §5) is **incorrect**.
- The live `findtorontoevents.ca/audit/data/dashboard_data.json` is `generated_at: 2026-11-14T14:30Z` with **20 curated active picks** / 4,148 raw / 3,500 recent-closed.
- The "0 active" reading came from the **stale local repo copy** (`audit_dashboard/data/dashboard_data.json` = Oct 23), not the deployed live site.
- The Alpha Engine is impaired but not completely dead — the DB is actively writing (`last_terminal_write = 2026-11-14 10:29:17`).

**OVERSTATED — "254-day stale intrabar truth":**
- `evidence_intrabar_truth.json` was generated today (14:25Z) and `money_ready_verdict.json` shows `recency.most_recent = 2026-11-13`.
- The "254 days" figure mixed two different metrics. Intrabar truth IS being freshly computed.

**MISLABELED — "FDR/single-source gates failed":**
- `evidence_money_ready_verdict.json` shows `_fdr_gate_enforce = false` and `_single_source_gate_enforce = false`.
- These gates are **DISABLED**, not failing. The verdict should read "gates off" rather than "gates failed."

---

## Peer Review (Cross-Agent Findings)

### childlike-airport (ML/DB audit)
- **Peer file:** `peer_review/2026-11-14-ML-AUDIT-childlike-airport.md`
- `data/live_picks.db` (SQLite): 128/129 picks **172 days stale**
- **PnL sign contradictions** in 8 SQLite rows
- **`audit_trail.db`** mostly empty (8 of 9 tables = 0 rows; `bt_backtest_runs=20`, `meta=1`)
- **`consensus_active_picks.json` is empty**
- **No mutual fund coverage anywhere**
- ML code (`ml_ranker_fixed.py`, `ml_gatekeeper.py`) is **mathematically sound** — inverted confidence is a **data bug**, not a code bug
- **Three divergent data stores** (SQLite/MySQL/JSON) with different counts/ages/PnL

### finpredict-v2 (actions deep-dive + P0 root causes)
- **P0-1 — Forex `KeyError: 'LONG'`** in `alpha_engine/scanner.py:2942` kills the ALPHA scanner. `_forex_by_sym` dict only has `BUY`/`SELL` keys; forex signals using `LONG`/`SHORT` raise `KeyError` → **93 failed runs / 24h**.
- **P0-2 — `summary_picks.json` reports WR > 100%** in 7 classes (INDEX 1,141%, FUTURES 364%, …). `tools/sync_summary_picks_json.py:63-65` counts `wins`/`losses` over all rows while `resolved` counts a subset.
- **P0-3 — Python 3.14 masquerade**: **197 workflows** set `update-environment: false`, so `actions/setup-python` never activates pinned 3.11; `pandas==2.1.4` source-builds against system 3.14 and fails.
- **P0-6 — `sym_track_*` built from wrong population**: `_enrich_live_pnl` calls `_build_strategy_symbol_track_stats` with active list filtered to closed statuses (always `[]`), not the closed ledger. Explains the dead "Track" column.
- **P0-9 — Security**: hardcoded Google API keys in `STOCKSUNIFY/…/stock-api-keys.ts` (×2) and `TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS2/scroll-fix.js`.

### finpredict-v3 (data-hygiene guardian + ML validation)
- Runnable artifact: `tools/pi_data_hygiene.py` (14 tests, exit 1 on findings)
- ML leakage fix committed (`d8c8dd25581`): `_drop_leakage_enabled()` default flipped to ON in gatekeeper
- Horizon harness: **n≥60 → 0/6 pass; n≥30 → 0/26 pass**. No strategy is solidly profitable across time.
- New detector: `FABRICATED_FLAT_PNL_COHORT` — strategies with ≥10 wins all pinned at exactly +3.00%.

### flaxen-hair (asset-class algorithms + backtests)
- **Score-PnL disconnect**: Confidence vs PnL Pearson r = **+0.008**; elite_score vs PnL r = **+0.203**
- **TRXUSDT concentration**: 96.8% of total losses come from TRXUSDT alone (-18,779%)
- **Direction bias**: SHORT picks = 72.0% WR; LONG picks = 20.3% WR. Scoring treats them identically.
- **TP/SL resolution bug**: `TP_HIT` rate 92.4% vs `SL_HIT` 4.5% — mathematically impossible. Root cause: resolver checks TP before SL in close-price fallback; no consideration of which level was hit first.
- **1,541+ closed picks have ZERO outcome tracking** across 13+ systems
- **33% missing exit_price** on closed picks (393 of 1,200)
- **Critical bugs**: SQL injection in `backtest_justin_bravo.py:77`, lookahead bias in `crypto_smart_picks.py:15-18`, ATR vectorization bug in `indicators.py`

---

## Veto List — Destructive Fixes (DO NOT APPLY)

The following fixes from our `proposed_fixes/*/QUICK_WINS.md` and peer docs are **destructive or dangerous** and must NOT be shipped:

| Fix | Source | Why vetoed |
|-----|--------|------------|
| Hard DELETE 22,947 ghost rows | overall/infra | Irreversible; no dry-run/backup |
| Bulk UPDATE TIME_EXIT→LOST + fabricate pnl_pct=0.0 | overall | Destroys PnL truth; contradicts "honest accounting" |
| Invert ML confidence gate (conf≥threshold → conf≤threshold) | crypto/overall | ML code is mathematically sound; inverted confidence is a **data** bug, not code |
| Force-close 3,772 open picks (EXPIRED_FORCE) | equity | Destroys open-pick history; corrupts closed-ledger stats |
| Unblock FUTURES/COMMODITY without real feed | commodity | Removes admin kill-switch; contradicts live HTML note |
| Placeholder mutual-fund scanner emitting empty signals | mutual_funds | Pollutes live feed with fabricated data |
| Add UNIQUE(symbol,direction,created_at,source_system) index | infra | Can fail/break against existing duplicates |
| Mass UPDATE crypto AI Challenge picks to EXPIRED | crypto | One-off bulk UPDATE on live data, no dry-run |

**Safe alternatives** are documented in each per-class fix file under "SAFE" headings.

## Proposed Fixes — Status

### Already Applied (P0 Truth Fixes)
| Fix | File | Status |
|-----|------|--------|
| P0-1 Forex direction KeyError guard | `alpha_engine/scanner.py` | **APPLIED** |
| P0-2 summary_picks WR > 100% | `tools/sync_summary_picks_json.py` | **APPLIED** |
| P0-3 prediction_market None coercion | `alpha_engine/prediction_market_consensus.py` | **APPLIED** |

### Applied Fixes (this session)
| Fix | File | Status |
|-----|------|--------|
| P0-1 Forex direction KeyError guard | `alpha_engine/scanner.py` | **APPLIED** — maps LONG/SHORT→BUY/SELL |
| P0-2 summary_picks WR > 100% | `tools/sync_summary_picks_json.py` | **APPLIED** — precise wins/losses + min(wins,resolved) cap |
| P0-3 prediction_market None coercion | `alpha_engine/prediction_market_consensus.py` | **APPLIED** — preserves None instead of 0 |
| P0-4 dashboard JS parse failure | `audit_dashboard/dashboard_enhancements.js` | **ALREADY IN MAIN** (fixed 2026-10-18) |
| P0-5 Python 3.14 masquerade | 197 workflow YAMLs | **APPLIED** — `update-environment: false` → `true` |

### Pending Safe Fixes (subagents in flight)
| Priority | Fix | Asset Class | Status |
|----------|-----|-------------|--------|
| P0 | Fix TP/SL resolution order (TP-before-SL bug) | All | **IN FLIGHT** |
| P1 | Add exit_price fallback for 393 closed picks with None | All | **IN FLIGHT** |
| P1 | Fix live_pnl_tracker.py crypto price fetch | CRYPTO | **IN FLIGHT** |
| P1 | Mark (don't DELETE) 22,947 ghost rows + add dedup index | Infra | Pending |
| P1 | Fix filter inversion in dashboard_generator.py | EQUITY | Pending |
| P1 | Kill quan_engine_scalp (PF 0.39, -427% PnL) | CRYPTO | Pending |
| P1 | Block yahoo_analyst_consensus (0% WR on 55 trades) | EQUITY | Pending |
| P2 | Implement TP/SL Quality Score component | All | Pending |
| P2 | Add direction-specific scoring (SHORT +20 WR bonus) | All | Pending |

### Vetoed / Destructive (see Veto List above)
- Hard DELETE ghost rows
- Bulk UPDATE TIME_EXIT→LOST with fabricated pnl_pct=0.0
- Invert ML confidence gate
- Force-close 3,772 open picks
- Unblock FUTURES/COMMODITY without real feed
- Placeholder mutual-fund scanner

## Sources Used
- GitHub Actions API (`gh run list`, `gh workflow list`)
- Live Binance API (api.binance.com)
- Live forex API (open.er-api.com)
- Live dashboard HTML + JSON payloads from findtorontoevents.ca/audit
- Repo JSON files in `audit_dashboard/data/`
- MySQL DB health reports (`db_health.json`)
- Peer SQLite audit (`data/live_picks.db`, `data/audit_trail.db`)

---
**Prepared for:** Next-stage review agent / master plan synthesis  
**Archive path:** `findtorontoevents_antigravity.ca/audits/2026-11-14/finpredict-v4_2026-11-14-1555/`
