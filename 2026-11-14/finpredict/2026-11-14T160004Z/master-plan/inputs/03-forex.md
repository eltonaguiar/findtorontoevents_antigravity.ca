# FOREX — Consolidated Peer Review (2026-11-14)

**Sources (7):** V2 `finpredict-v2_20261114-1602` (P0/P1 plan), V3 QUICK_WINS `161500Z`, V3 PEER_REVIEW `161700Z`, V4 `forex_deep_dive.md`, V4 `proposed_fixes/forex/QUICK_WINS.md`, ML `childlike-airport FIX_PROPOSED.md`, ME `finpredict 160004Z`.
**Class verdict (all peers agree):** net-unprofitable — V4 PF 0.48 / WR 36.6% / PnL -27.78%; V2 policy-clean n=438 PF 0.834 (still losing). Keep policy-frozen / paper-only.

---

## 1. Consensus findings (≥2 peers)

1. **FX price feed is broken → frozen-at-entry / null PnL.** 96.6% of stored FOREX picks have null PnL; active picks show `current_price ≈ entry_price` (`-0.0%`) while live rates give real moves (+0.061% USDCAD, +0.0385% NZDUSD). (V2 P0-2/P1-3, V3 QW2/QW4, V4 deep-dive rec#1, V4 QW MF-1, ML §3.1, ME #2.)
2. **PR#6 "all FOREX blocked" is FALSE in practice.** `non_crypto_consensus` (cross-asset engine) bypasses both the FX kill-switch and the FOREX block; `FOREX_HARD_DISABLE` is default OFF. 0/277 rows pass the advertised allowlist. (V2 P0-6/P1-2, V4 deep-dive §6 rec#2, V4 QW QW-2, V3 PEER.)
3. **Blocked/retired strategies feed consensus.** `forex_rsi2_mean_reversion` (in `_RETIRED_STRATEGIES`) still contributes; `ig_contrarian_sentiment`/`myfxbook_retail_contrarian` are sub-40% WR. (V2 P0-6, V4 deep-dive rec#3, V4 QW QW-1.)
4. **Over-emission / duplication.** 4x USDCAD, 4x AUDUSD; 40 dup-ID groups; single strategy votes twice across JSON files → fake "independent" consensus. (V2 P0-5/P1-4, V4 deep-dive rec#5, V4 QW QW-3/MF-3, V3 QW3.)
5. **Stale zombie/phantom rows pollute the closed set.** 11 frozen phantoms (Mar 2026, exit==entry, UNKNOWN), 4 stale active (172d), 158 EXPIRED FOREX rows. (V2 P1-6, V3 QW1, ML §1, ME #1, V3 PEER.)

---

## 2. Unique per-peer

- **V2** (most rigorous): date-only ISO timestamps (`entry_time="2026-11-14"` unresolvable), currency-ETF/EURUSDT misclassification (49/277 non-FX), FUTURES session guard (weekend seeds), FUTURES closed ledger (0 closes), impossible `summary_picks` WR 147.0%/363.9%, `quote_status`/`UNQUOTED` provenance. Annotation-only, no deletion.
- **V3 QW:** "by-construction zero" labeling (frozen-at-entry vs live), dedupe batch-identical `closed_at`.
- **V3 PEER:** best-of synthesis — enforce PR#6, propagate blocklist, paper-only; no live-quote source fix beyond "enricher".
- **V4 deep-dive:** live rate verification (open.er-api) with exact discrepancies; PR-D is a *sizing* gate not an emission block; per-strategy track records.
- **V4 QW:** consensus vote dedup by `(symbol,direction,strategy)`; replace contrarian sources with regime momentum; swap-cost forward lane (LF-1); retire `multi_asset_copytrader_scraper.py` FOREX branch (LF-2); per-symbol dynamic kill-switch (LF-3).
- **ML:** backfill `asset_class` case (120 lowercase `forex` vs `FOREX`), emit exit events for 4 stale, populate `strategy_stats`, re-run FX scanners, `FOREX_CODES` validation.
- **ME:** 217d-stale `stock_forex_prices.json` fallback age-guard; raise FOREX consensus threshold 1→2.

---

## 3. Consolidated fixes (dedup)

**Legend:** Effort S/M/L · Risk L/M/H. `⚠️ DESTRUCTIVE` = mutates DB rows or deletes. Vetoed items are marked.

### A. Policy enforcement (PR#6 / hard-disable)
| Fix | File:line | Effort/Risk | Proposer |
|---|---|---|---|
| Drop picks whose `strategy ∈ BLACKLISTED_STRATEGIES` before consensus vote | `copy_trader_intel/non_crypto_consensus.py` (~:303 after `_apply_quality_gate` / in `consensus_vote` ~:163) | S/L | V4 QW-1, V2 P1-2, V4 deep-dive rec#3 |
| Skip `asset_class=="FOREX"` when `FOREX_HARD_DISABLE` active (consensus + downstream consumers) | `non_crypto_consensus.py run_consensus()`; `alpha_engine/combined_confidence_strategy.py`; `alpha_engine/smart_picks_engine.py` (~:518) | S/L | V4 QW-2, V2 P1-2 |
| Shadow `_policy_blocked_reason` annotation (do NOT enforce yet) | `audit_trail/dashboard_generator.py` ingest | S/L | V2 P0-6 |
| Extract `passes_forex_consolidation()` into live `passes_non_crypto_policy()` | `alpha_engine/non_crypto_policy.py:698-741`, `:1026-1040`; `multi_asset/scanner.py:705` | M/H | V2 P1-2 |
| Resolve `cta_cross_asset_tsmom` allowlist vs blacklist contradiction | `non_crypto_policy.py:724` vs `config.py:298` | S/L | V2 P1-2 |
| Raise FOREX consensus threshold 1→2 (or require non-null `current_price`) | `non_crypto_consensus.py:134`, `:150` | S/L-M | ME #3, V2 (P0-6 threshold note) |

### B. Price fetch / PnL hydration
| Fix | File:line | Effort/Risk | Proposer |
|---|---|---|---|
| Add `quote_status`/`quote_source`/`quote_at`; mark `UNQUOTED` on miss, `_price_is_entry` when current==entry | `audit_trail/dashboard_generator.py:1681-1688`, `:1752-1755`, `:1821-1822`, post-pass `:17481-17485` | S/L | V2 P0-2 |
| FX provider branch for `=X` tickers (yfinance FX / open.er-api / OANDA) + write back `current_price` | `audit_trail/universal_pick_resolver.py`; `tools/forex_resolver_ab_replay.py`; `tools/fix_forex_pnl_clamping.py` | M/M | V4 QW MF-1, V2 P1-3, V4 deep-dive rec#1 |
| Age-guard `stock_forex_prices.json` fallback (>24h → skip) + ship fresh file | `alpha_engine/outcome_resolver.py:413`, `:424-437`; `production_scanner.py:2362`, `:2538`; `continuous_improvement_monitor.py:392`; `multi_asset_test_portfolios.py:105` | M/M-H | ME #2 |
| Per-pair freshness flag (quote age) | `audit_trail/universal_pick_resolver.py` | S-M/L | V3 QW4 |
| Label "frozen at entry (live quote)" instead of stale when current==entry | `universal_pick_resolver.py` stale-detection branch | S/L | V3 QW2 |

### C. Deduplication
| Fix | File:line | Effort/Risk | Proposer |
|---|---|---|---|
| Exact-ID dedup: annotate `_duplicate_of`, keep newest timestamp, exclude from counts (no delete) | `dashboard_generator.py:17481-17485` | S/L | V2 P0-5 |
| Consensus vote dedup by `(symbol,direction,strategy)` | `non_crypto_consensus.py consensus_vote()` (~:163) | S/L | V4 QW-3 |
| Canonical trade-key dedup with UTC-day + entry-price window (NOT symbol+direction alone) | `dashboard_generator.py:17481-17485`; `multi_asset_copytrader_scraper.py:444` | M/M | V2 P1-4 |
| Symbol-level `(symbol,direction)` uniqueness guard at ingest | `alpha_engine/mysql_trading_sync.py` / `scanner.py`; `dashboard_generator.py` | M/M | V4 QW MF-3 |
| Unique `closed_at` per resolved row (not batch stamp) | resolver/closure writer (`universal_pick_resolver.py` / `alpha_engine/audit_sync.py`) | M/L | V3 QW3 |

### D. Data hygiene (stale/phantom/zombie + class)
| Fix | File:line | Effort/Risk | Proposer |
|---|---|---|---|
| **Quarantine (annotate, do NOT delete)** 11 phantom closed rows — drop `exit_reason in ("","UNKNOWN") AND pnl==0 AND exit==entry` from *stats* via filter, keep rows | `dashboard_generator.py _is_valid_resolved_pick()` (:4850/:4867/:4903/:4942) or `_build_recent_closed_picks()` (:6948); `alpha_engine/outcome_resolver.py:1180/:2660` | M/H | ME #1, V3 QW1 (V2 P1-6 vetoes hard-delete) |
| ⚠️ **DESTRUCTIVE (VETO as-is):** hard-delete / one-off DB purge of 11 phantom rows | "one-off DB cleanup script" | M/M-H | V3 QW1 ("Mark VOID **or hard-delete**") — prefer VOID/quarantine |
| ⚠️ **DESTRUCTIVE (SQL UPDATE/DELETE on live DB):** `UPDATE live_picks SET current_price,pnl,status='CLOSED'/'EXPIRED' WHERE asset_class ILIKE 'forex' AND status='ACTIVE' AND (current_price IS NULL OR pnl=0)` | `live_picks.db` / `closed_picks.db` | M/H | ML §3.1 — requires explicit approval + backup; not read-only |
| ⚠️ **DESTRUCTIVE:** backfill `asset_class` case (`UPDATE ... SET asset_class='FOREX'`) | `live_picks.db` / `closed_picks.db` via `alpha_engine/asset_class.py FOREX_CODES` | S/M | ML §3.4 |
| ⚠️ **DESTRUCTIVE:** remove 4 resolved stale picks from `.picks.active` + append exit events | `universal_pick_resolver.py`; `audit_trail/exit_events.json` | M/M | ML §3.2 |
| Retention contract: `lifecycle_state` (OPEN/EXPIRED/PLACEHOLDER/RESOLVED), split `inventory_count` vs `open_count`, quarantine EXPIRED | `dashboard_generator.py:9538`, `:9540-9617`, `:17481-17485`; `universal_pick_resolver.py:931-963` | S-M/L | V2 P1-6 |
| ISO-8601 entry-time: prefer full timestamps, reject date-only, stamp `_ts_precision="DATE_ONLY"` (no `T00:00:00Z` fabrication) | `dashboard_generator.py:8136-8154`, `:8351-8352`; `multi_asset_copytrader_scraper.py:452` | S/L | V2 P0-1 |
| Class-correctness shadow: currency-ETF + EURUSDT → `class_mismatch` annotation (49 rows) | `dashboard_generator.py:3439-3444`, `:3516-3532`, `:3567-3568`, `:3659-3661`; `asset_class.py:37-53`, `:222-224` | S/L | V2 P0-3 |

### E. Statistical / reporting
| Fix | File:line | Effort/Risk | Proposer |
|---|---|---|---|
| Suppress impossible FOREX/FUTURES WR (147.0% / 363.9%) — `invalid_denominator:true` | `tools/sync_summary_picks_json.py:63-65`, `:161` | S/L | V2 P1-7 |
| Populate `strategy_stats` for FX strategy keys (null → gatekeeper scores unproven) | `ml_gatekeeper/gatekeeper.py` backfill | S-M/L | ML §3.5 |

### F. Longer-term (P1+/weeks)
- V4 QW MF-2: replace `ig_contrarian_sentiment`/`myfxbook_retail_contrarian` with `regime_filtered_momentum`.
- V4 QW LF-1: swap-cost forward lane (`paper_trading/strategies/forex_forward_lane.py`).
- V4 QW LF-2: retire/refactor `multi_asset_copytrader_scraper.py` FOREX branch (lines 480-524, 2472).
- V4 QW LF-3: per-`(symbol,direction)` dynamic kill-switch (`quality_gates.py`).
- V2 P1-1: flip class normalize from shadow→enforce (dual-write `asset_class_raw`).
- V2 P1-5: FUTURES closed ledger + resolver (new `FUTURES_V2` cohort).

---

## 4. Conflicts

1. **Purge vs quarantine.** V3 QW1 + ME #1 want to *purge/hard-delete* the 11 phantom rows; V2 `Do-not-do #2` and P1-6 mandate *annotation/quarantine, never delete*. → Resolve: VOID/quarantine, keep rows.
2. **`FOREX_HARD_DISABLE` default.** V4 QW asserts "HARD_DISABLED since 2026-05-18, flag=1 in `quality_gates.py`"; V2 proves the computed default is **OFF** (`config.py:345`, 277 rows imply gate inactive). → V2 is line-verified; flag is currently OFF.
3. **Live active count.** V4 dashboard = 2 active; ML DB = 4 stale active; V2 `active_raw` = 118 OPEN. → Different layers (curated panel vs DB vs pre-filter audit pool).
4. **Severity.** V4 aggregate PF 0.48/-27.78% vs V2 policy-clean n=438 PF 0.834 (z=-6.02) — same losing sign, different magnitude (raw vs clean).
5. **Enforce-now vs shadow-first.** V4 QW-2 wants immediate hard-disable enforcement; V2 mandates shadow (P0-6) → warn → block **new** emissions only, never delete history.
6. **`cta_cross_asset_tsmom`.** Allowlisted (`non_crypto_policy.py:724`) but blacklisted (`config.py:298`) — unresolved authority.

---

## 5. UNVERIFIED

- Exact DB write persisting `entry_time="2026-11-14"` (V2).
- "158 FOREX rows >30d" — not reproducible as age count; 114 of 233 parseable are >30d (V2).
- Live CI value of `FOREX_HARD_DISABLE` env (repo default OFF; deployed value unobservable) (V2).
- `cta_cross_asset_tsmom` allowlist intent (stale entry vs deliberate) (V2).
- CME/FX holiday calendar (V2 P0-4 covers weekends only).
- Realized slippage/fill quality — no live fills in repo (V2).
- Browser rendering of new `UNQUOTED`/`PLACEHOLDER` badges (V2).
- Provenance of the 11 phantom rows (which DB/log produced them) (V3).
- Exact price-fetch producer path — "enricher"/`fetchForexPrices()` wiring not confirmed (V3 PEER gap, ML).
- Closed-pick count: dashboard `picks.closed` = 0 FX vs aggregate = 82 (V4 §4, V3 PEER).

---

## 6. P0 order (top 5)

1. **Enforce PR#6 / hard-disable on `non_crypto_consensus`** — blacklist guard + FOREX skip + vote dedup by `(symbol,direction,strategy)`. Stops the single largest bypass; ~1 day; low risk if staged (shadow→block-new).
2. **Fix FX price hydration + `UNQUOTED` provenance** — `quote_status`/`quote_at` stamping + FX provider branch + age-guard on stale `stock_forex_prices.json`. Converts 96.6% null-PnL into measurable data.
3. **Dedup over-emission** — exact-ID annotation first, then trade-key dedup with UTC-day+price window (NOT symbol+direction alone).
4. **Quarantine stale/phantom rows** — 11 phantoms + 4 stale active + 158 EXPIRED → `lifecycle_state`/VOID (quarantine only; **hard-delete and DB UPDATE/DELETE vetoed pending operator sign-off + backup**).
5. **Reconcile `FOREX_HARD_DISABLE` default + shadow-count 0/277** before any enforcement, and suppress impossible WR 147.0%/363.9%.
