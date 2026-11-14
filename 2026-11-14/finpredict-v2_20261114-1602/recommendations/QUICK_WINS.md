# QUICK WINS — ranked P0 remediation

**Frame:** 2026-11-14T16:20Z · all items ≤ 1 engineering day unless marked · low blast radius ·
independently revertible · no trading-signal changes.
**Evidence:** `../MASTER_AUDIT.md`, `../sub/{A,B,C,D,E,F}*.md`, `../raw/*`.
Every `file:line` below was verified by the subagent that authored the detail block; see the
linked per-class / patch-plan file for the full rationale.

| Rank | Fix | Impact | Effort | Risk | Detail |
|---:|---|---|---|---|---|
| **1** | Guard the FX direction bucket (`KeyError: 'LONG'`) | Stops the dominant CI failure cluster: **93 failed runs/24 h** (ALPHA 47 + FAST 46) | S (30 min) | Low | `patch_plan/P0_QUICK_WINS.md` P0-1 → `alpha_engine/scanner.py:2937-2942` |
| **2** | Single-population `summary_picks` query + clamp/assert | Removes **7 impossible WRs** (BOND 127.8%, COMMODITY 240.2%, INDEX 1141.2%…); 8 classes have `wins+losses > resolved` | S (2 h) | Low | `patch_plan/P0_QUICK_WINS.md` P0-2 → `tools/sync_summary_picks_json.py:63-65,161` |
| **3** | Actually run Python 3.11 (remove `update-environment: false`) + add `xgboost` to FAST | Fixes the pandas 2.1.4 source-build cluster: **8–9 workflows**, 48+ failed runs/48 h | S (2 h) | Low | `patch_plan/P0_QUICK_WINS.md` P0-3 → `signal_tracking.yml:35`, `alpha-engine-fast.yml:35,40` |
| **4** | Space audit-dashboard cron to real runtime (or 2-hourly) | **61/168 runs cancelled in 7 d**; median success 84.5 min vs hourly cron | S (15 min) | Low | `patch_plan/P0_QUICK_WINS.md` P0-4 → `.github/workflows/audit-dashboard.yml:5,41,42,55` |
| **5** | Quote-provenance contract + `UNQUOTED` / `LAST_CLOSE` / `STALE` render | **19/20 curated rows show fake 0.00%**; 3,584/4,148 raw rows have null price | S/M (4 h) | Low/Med | `per_asset_class/crypto_commodity.md` P0-1/P0-2; `equity_etf.md` P0-1/P0-3; `forex_futures.md` P0-2 |
| **6** | Reject date-only timestamps at ingest | All 3 OPEN ES=F rows and 12 FOREX timestamps are date-only; resolver cannot parse them | S | Low | `per_asset_class/forex_futures.md` P0-1 → `dashboard_generator.py:8136-8154,8351-8352` |
| **7** | Kill the vacuous PASS; add `NOT_BUILT` | BOND (0 picks) renders green PASS; MUTUAL FUNDS is advertised but absent | S | Low | `per_asset_class/bond_mutual_funds.md` QW-1/QW-2 → `dashboard_generator.py:6824-6826`, `template.html:4946` |
| **8** | Publish the active population split (curated vs raw vs frozen) | Ends the "2 vs 94 vs 58" dispute per class; exposes 691 OPEN vs 4,148 raw | S | Low | `per_asset_class/equity_etf.md` P0-5; `crypto_commodity.md` P0-4 |
| **9** | Dedup key + quarantine EXPIRED from the default view (keep rows) | 4,148 rows / 3,851 IDs; 3,377 EXPIRED; 22,947 ghost rows; BOND 15→6 | S/M | Med | `patch_plan/P0_QUICK_WINS.md` P0-8; `bond_mutual_funds.md` QW-5 |
| **10** | Symbol-authoritative class routing (behind flag) | 44 COMMODITY rows are futures; 49/277 FOREX rows are not spot FX; ETFs inside EQUITY | S | Med-low | `equity_etf.md` P0-6; `forex_futures.md` P0-3 |
| **11** | Stop emitting zero-entry rows | 85 zero-entry rows incl. **XRPUSDT 0.0** from `prediction_market_consensus` | S | Low-Med | `crypto_commodity.md` P0-5 → `prediction_market_consensus.py:160,479,588-591` |
| **12** | Make the FOREX block observable (shadow) | The PR #6 allowlist has **0 call sites**; **0/277** FOREX rows pass it | S | Low | `forex_futures.md` P0-6 → `non_crypto_policy.py:698-741,1026-1040` |

## Actions P0 (deep dive, 17:50Z)

These supersede the earlier CI ranks where they overlap. Full evidence: `../actions_deepdive/ACTIONS_DEEP_DIVE.md`.

| # | Fix | Exact target | Impact |
|---:|---|---|---|
| A1 | Normalize `LONG/SHORT → BUY/SELL` before the FX map lookup | `alpha_engine/scanner.py:2937-2942` | Removes **15/30** failures (~88/day, ~558 runner-min) |
| A2 | Remove `update-environment: false` (use `python -m pip`) so 3.11 is used | `forward_test.yml:33`, `live_trading.yml:29`, `live_trading_canada.yml:33`, `live_trading_canada_free.yml:43`, `picks_dispatch.yml:24`, `market_beating.yml:35`, `signal_tracking.yml:35` | Removes **7/30** failures, ~715 runner-min |
| A3 | Fix CI frequency alias | `tests/test_combined_book_sleeves.py:17` (`ME` → `M`/`MS`) or pin pandas 2.2 | Removes **2/30**, unblocks CI |
| A4 | Pin runner / upgrade Playwright | `sports-smoke-and-e2e.yml:53` (`ubuntu-24.04`), `:86`; `package.json:20` | Removes **5/30** |
| A5 | Stop committing the 100 MB JSON | `missed-opportunity-scan.yml:43`; `.gitignore`; `git rm --cached`; rotate/LFS | Removes **1/30** |
| A6 | Space audit cron to real runtime | `audit-dashboard.yml:5` → `'10 */2 * * *'`; `:55` timeout 115→130 | Eliminates ~21 zero-job discards/60 |
| A7 | Split the shared concurrency group | `operator-review-today.yml:39`, `rsi5070-forward-snapshot.yml:59` → `dashboard-publish-daily` | Removes 3-way 07:00 contention |
| A8 | Fix PEAD push loop | `pead-shadow-collector.yml:82-101` | Stops **60/60** commit failures |
| A9 | Remove duplicate push triggers | `signal_tracking.yml:9-14`, `market_beating.yml:9-14` | Removes duplicate runs in a 91-min queue |

## Same-day but data-source specific

- **Re-enable FRED in the bond scanner** (`SKIP_FRED=1` hard-coded): `bond_mutual_funds.md` QW-6 → `.github/workflows/etf-bond-scanner.yml:159`, `bond_scanner.py:289-296`. Effort S, low risk.
- **Fix BOND price coverage** (wrong payload path, `apikey=demo`, 12 missing ETFs): `bond_mutual_funds.md` QW-4 → `fetch_stock_prices.py:68-77`, `dashboard_generator.py:1599`, `universal_pick_resolver.py:433-443`. Effort S–M.
- **Track from the closed ledger, not the active slice**: `P0_QUICK_WINS.md` P0-6 → `dashboard_generator.py:1830-1832`. Track is empty on 18/20; `sym_track_total` is 0 on 20/20. Effort S.
- **Sidecar freshness manifest + hide-if-stale**: 10+ sidecars are 79–245 days old. Effort M. `P0_QUICK_WINS.md` P0-7.
- **Refresh/retire the 172-day-stale `live_picks.db`**: ML peer audit (`updates/2026-11-14-ML-AUDIT-childlike-airport.md`) found 128/129 active picks stale, 8 PnL sign contradictions, 15 PnL mismatches, and `audit_trail.db` empty. Effort S–M; separate from the dashboard JSON path.

## Additional items folded in after peer review

- **COMMODITY/FUTURES are gate-blocked:** `audit_trail/quality_gates.py:1724` sets `BLOCKED_ASSET_CLASSES = {"FOREX","COMMODITY","FUTURES","BOND"}`. Any COMMODITY "live" bucket is a display artifact. Do not ship canonical-class plumbing that implies live commodity exposure until the block is deliberately resolved.
- **COMMODITY provenance is synthetic:** `alpha_engine/commodity_signal_generator.py:231-238` maps RNDR/ARB to "silver" and `:250` maps XLM/DOT to "oil". Tag these rows as proxies; do not present them as commodity exposure.
- **AI Challenge registry is stale:** `audit_dashboard/data/ai_challenge_antigravity_active_picks.json` — 9 OPEN, all null price, PnL 0.0, no timestamps.
- **SQLite layer needs its own sync:** `data/live_picks.db` 128/129 active picks ~172 days stale; **9 PnL sign contradictions + 18 PnL mismatches** (direction-aware, unit-consistent formula required); `data/audit_trail.db` 8 audit tables with 0 rows + 2 non-empty; `pick_history` has no exits. Add a `live_picks` refresh/retire job and a PnL-sign assertion.
- **Headline n + Wilson CI:** every published WR must show n and a binomial/Wilson CI next to it (v1 `QW-1`). A WR without n is not a result.
- **Force-close/age-out stale opens:** 691 OPEN, 63% of all picks never resolve. Add an age-out policy that emits a documented `TIME_EXIT` (not a silent 0% close).
- **ETF watch-only:** `WATCH_ONLY_CLASSES` currently contains only BOND; add ETF while its policy-clean n is 15 and PF is not significant.
- **FOREX phantom sweep:** 11 frozen March-2026 closed FOREX rows with `exit UNKNOWN` / `exit_price == entry` must be resolved or quarantined, not left as 0% closes.

## Canonical quote-status contract (use this everywhere)

| Status | Meaning | PnL display |
|---|---|---|
| `LIVE` | Fresh external quote, `quote_at` within the class SLA | computed PnL + quote age |
| `LAST_CLOSE` | Price equals the last completed session close (weekend/holiday) | PnL labelled "as of close" |
| `STALE` | Quote exists but older than the class SLA | PnL labelled stale, no green dot |
| `UNQUOTED` | No price / `current_price` null | `—`, never `0.00%` |
| `PLACEHOLDER` | Seed/gated row with no real position | `—`, excluded from performance |

Rule: **never** emit `pnl_pct = 0.0` merely because a quote is missing. Use `null` + the status above.

## Veto list — do not implement these peer proposals

- `DELETE` ghost/zombie rows (destroys audit trail). Quarantine/tag instead.
- `UPDATE TIME_EXIT → LOST, pnl_pct = 0.0` (fabricates outcomes).
- `EXPIRED_FORCE` mass rewrite of historical statuses.
- Invert the ML confidence gate (the inversion is an artifact of a broken label, not a signal).
- Unblock FUTURES/COMMODITY without a real feed and a session guard.
- Add `MUTUAL_FUND` to canonical classes before a real emitter/NAV source exists.
- Re-enable the audit-dashboard `push:` trigger.

## Open items the next agent must resolve

1. **Classifier precedence:** `normalize_asset_class({"symbol":"SPY","category":"equity"})` returns `equity`; the symbol-authority acceptance test cannot pass unless `normalize_asset_class` is changed or the test calls `classify_pick_asset_class_upper`.
2. **Label collision:** split `UNQUOTED` (null) from `LAST_CLOSE` (verified Friday close); do not apply both to the same row.
3. **BOND ticker list drift:** the resolver list should use the canonical `BOND_SYMBOLS` (TLT, IEF, SHY, LQD, AGG, BND, HYG, JNK, SJNK, BKLN, EMB, TIP, MUB, IGIB), not TLH/GOVT/BNDX.
4. **Mutual-fund prototype:** decide de-advertise (`NOT_BUILT`) vs productionize; do not count untracked prototype output as a live class.

## What deliberately is NOT a quick win

- Re-enabling the audit-dashboard `push:` trigger — the 2026-05-19 cancel cascade is still active.
- Deleting zombie/EXPIRED/ghost rows — they must stay auditable; quarantine/tag instead.
- Recomputing history to make the numbers look better — fix forward and label the break.
- Promoting any class to "money-ready" — 0/9 currently qualify; a threshold change is not a fix.
- Building mutual-fund strategies/pages — recommended action is **de-advertise + `NOT_BUILT`**, not a rushed live class.
