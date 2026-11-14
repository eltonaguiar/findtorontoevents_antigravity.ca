# CRYPTO — Consolidated Peer Review

**Consolidated:** 2026-11-14T17:45Z · **Read-only review** · 8 source docs from 5 peers.
**Peers:** V2 (`crypto_commodity.md`, `sub/C_crypto.md`), V3 (`QUICK_WINS`, `PEER_REVIEW`), V4 (`crypto_deep_dive.md`, `proposed_fixes/QUICK_WINS.md`), ML (`FIX_PROPOSED.md`), ME (`quick-wins/by-asset-class/CRYPTO.md`).

---

## 1. Consensus findings (≥2 peers, independent confirmation)

### C1 — Frozen 0.00% PnL is a stale-price artifact, not true flat (ALL peers)
- Curated panel: **19/20** rows have `current_price == entry_price` (V2 C_crypto:56); the only non-zero row is NEARUSDT (+2.74%).
- XRP/BTC are exact entry copies while Binance shows real moves: XRP `0.9842→0.9716` = **+1.28%** (V2:33, V3 QW-C1), V4 measured `0.9842→0.9698` = **+1.46%** at a later tick (V4:64). BTC `66,300→65,672.05` = **+0.95%** (V2:33, V3), V4 `66300→65658.01` = **+0.97%** (V4:96).
- Raw feed: **3,170/3,577 (88.6%)** crypto rows have `current_price = null`; **3,322/3,577 (92.9%)** have `pnl_pct == 0.0`; 485/691 OPEN raw rows are unpriced (V2 C_crypto:51-54, V2 P0-1:16).
- All peers agree the flat mass is a no-quote artifact; the price feed itself is sound (Binance/CoinGecko/Coinbase agree within ~0.15%, V2 C_crypto:34).

### C2 — `inverse_mutations` / `inverse_luxalgo_confluence` zombie factory = **2,267 rows** (V2, V3)
- Exactly 2,267 rows, 20 symbols, 167 emission days, first 2026-05-23, last 2026-11-13, ~one row per symbol per day.
- Of these: **2,231 EXPIRED, 2,255 `pnl=0.0`, 2,254 null price** — they are **71%** of all crypto null-current rows (V2 C_crypto:152-158, V2 P0-7, V3 QW-C2:13, V3 PEER_REVIEW:27).
- Cause: date-only IDs (`%Y-%m-%d`) + unbounded merge/append in `inverse_strategies.py:410,436,547-560` and competing overwrite writer `inverse_loser_mutations.py:398-400` (V2 P1-2).

### C3 — Zero / garbage entry rows, incl. `XRPUSDT SHORT entry=0.0` (V2, V3, ME, ML)
- **85 zero-entry crypto rows** (mape_evolver 28, genetic_programmer 21, ensemble_evolver 10, neat_neural 8, hyperparam_dna 8, genome 4, failure_evolver 3, prediction_market_consensus 3) (V2 C_crypto:166, V2 P0-5:35).
- Named phantom: `pm_consensus_XRPUSDT_202611141354` SHORT `entry=0.0` at 13:54:51Z (V2 P0-5). Absurd-low entries: BTC `0.2608/0.3322/1.334`, ETH `0.092`, LINK `0.1656`, AVAX `0.1544` (V2 C_crypto:168, V3 QW-C1).
- Root cause: `entry_price = get("entry_price") or 0` coercion (ME QW-2) at `alpha_engine/prediction_market_consensus.py:589-591` (V2 P0-5).

### C4 — Duplicate IDs + cross-ledger conflicts (V2, V3, ML)
- **218 duplicate `id` values** (max 4 repeats); **55 IDs appear in both `active_raw` and `recent_closed` with conflicting status/PnL** (V2 C_crypto:172, V2 P0-4, V3 QW-C4:15).
- Example: `clone_hl_copy_PensionFund_24M::NEARUSDT::2026-03-19_1150` = EXPIRED 0.0 in raw vs WON +3.4483 in closed.
- ML adds a case-duplication defect: **1,348 `crypto` (lowercase) rows** separate from 6,400 `CRYPTO` closed rows (ML:20).

### C5 — Crypto has no statistically distinguishable edge; do not size (V2, V4, V3)
- V4 RSI5070: Net PF **1.113**, CI-LB **0.916** → gate FAIL below promotion bar (V4:236-253).
- V2: CRYPTO `NOT_READY`, policy-clean n=21,988, WR 42.35%, PF 0.2595, z=−22.69, `single_source_pct=0.9895` → single-source artifact (V2 P1-8).
- V3 cites v1: PF **0.93**, z=−7.1 (worse than random) (V3 PEER_REVIEW:28). V4 QW: raw DB PF **0.37**, WR **35.9%** (V4 QW:206).
- All 3 active picks: `forward_validated=false`, `forward_trades=0`, trust ≤4 WATCH (V4 deep dive).

### C6 — Status/PnL contradictions: 12 `LOST` rows with positive PnL + SL-above-entry (V2, V3)
- **12 `recent_closed` rows labelled LOST with positive PnL** (all `exit_reason=SL_HIT`) (V2 C_crypto:171, V3 QW-C5:14).
- SL above entry for LONG (BTC `69980` SL 77,569; ETH `2047.29` SL 2,072.80) violates `SL<entry<TP` (V2 C_crypto:171).
- ML adds sign-contradictions in `live_picks.db`: NEARUSDT `unrealized=-0.129` (should be +0.129), ZECUSDT +0.013 (should be −0.0136) — 8 sign + 15 calc mismatches (ML:15-17).

---

## 2. Unique per-peer findings (one line each)

- **V2 `crypto_commodity.md`:** `summary_picks` WR denominator bug — COMMODITY reports **240.2%** WR (3,476 W / 3,466 L vs resolved=1,447) and CRYPTO 98.3% because wins/losses count all rows but `resolved` counts only terminal statuses (`tools/sync_summary_picks_json.py:63-65,161`).
- **V2 `C_crypto.md`:** NEARUSDT +3.16% mark is **plausible and real** (Binance 15:00Z 1h close 3.219 → 3.1588%); entries validated inside surrounding hourly ranges, and there are **244 duplicate `(symbol,direction,entry,timestamp)` tuples** (max 12: HYPEUSDT LONG 39.91).
- **V3 `QUICK_WINS`:** proposes an entry sanity band `entry < 1e-3 * symbol_price` and SL/TP ordering rejection via `_heal_no_price_row` (`universal_pick_resolver.py:931`).
- **V3 `PEER_REVIEW`:** surfaces a **data-layer mismatch** — dashboard panel has 3 crypto picks, `active_raw` has 402 OPEN, but `live_picks.db` has **101 active** (~172d stale); also flags the AI-Challenge crypto cohort "all >8 months old (2026-03-15) still OPEN".
- **V4 `crypto_deep_dive.md`:** all 3 active picks are SHORT, all `_backfilled=true`, all `_emitter_registry_would_block=true`; BTC sits in the `[0.65,0.75)` confidence dead-zone (`_phase1_dz_shadow_reject`), and BTC has 13 contributing systems (crowded consensus).
- **V4 `QUICK_WINS.md`:** dashboard PF **1.80 vs raw DB PF 0.37 (~5× inflation)**; ML confidence is **inverted** (conf≥0.90 → 14.4% WR vs conf 0.50–0.60 → 60.3% WR); Smart Picks PF **9.69 on 3 rows** (91.7% `claude_gainer_st`).
- **ML `FIX_PROPOSED.md`:** 101 active `live_picks.db` crypto rows stale ~172 days (last activity 2026-05-25) needing `unrealized_pnl_pct` recompute; closed-pick coverage is adequate (not the defect).
- **ME `CRYPTO.md`:** `_fetch_prices_with_failover()` only tries **geo-blocked** endpoints (83% frozen); proposes prepending `_fetch_all_binance_prices()` mirror-failover; plus `kalshi_signal_agent` hardcodes `entry_price: 0`, a placeholder flat-3% cohort detector, and a 127-pick forward-scanner seed batch that is 96.9% frozen.

---

## 3. Consolidated proposed fixes

Unified IDs; deduplicated across peers. Naming normalized to V2's `quote_status` enum. Effort: S (<1d) / M (1–3d) / L (>3d). Risk: Low/Med/High.

| ID | Fix (unified) | Target file + line(s) | Effort | Risk | Proposed by |
|---|---|---|---|---|---|
| **F-1** | **Quote-provenance contract** — stamp `quote_status ∈ {LIVE, UNQUOTED, STALE, LAST_CLOSE}` + `quote_source`/`quote_at`/`quote_age_hours` on `picks.active` & `picks.active_raw`; final pass before serialization; keep list at `:279-309`. Do **not** mutate `pnl_pct` in the enrich loop. | `audit_trail/dashboard_generator.py:1618-1846` (miss path `:1739-1755`), `:16953`, `:17481-17485`, `:279-309` | S | Low | V2 P0-1, V3, V4 QW-1, ME QW-4 |
| **F-2** | **Re-quote live crypto at build (Binance mirror failover)** — prepend `alpha_engine.universal_price_enricher._fetch_all_binance_prices()` to the fetcher; merge results; fall through on failure. Fixes the 83% frozen mass. | `audit_trail/dashboard_generator.py:1179`; reuse `alpha_engine/universal_price_enricher.py:172,:52`; `audit_trail/fetch_stock_prices.py` (Binance path) | S–M | Low–Med (rate limits; cache per symbol) | ME QW-1, V3 QW-C3, V4 QW-1, V2 P1-1 |
| **F-3** | **`UNQUOTED`/`STALE`/`LAST CLOSE` render contract** — PnL cell never prints `+0.00%` for unquoted; status cell shows badge; Age cell shows `signal · quote` split. | `audit_dashboard/template.html:8889-8905`, `:8883-8887`, `:9134-9145`, `:9222-9227`, `:5075` | S | Low (pure render, flag-gated) | V2 P0-2, ME QW-4, V3 |
| **F-4** | **Stop `None → 0.0` entry coercion** — keep `None`; `status="SIGNAL"` when no real entry; tag `_invalid_entry`. Emitter + dashboard gate. | `alpha_engine/prediction_market_consensus.py:160,:479,:589-591`; `genome/mape_evolver.py:497-511`; `audit_trail/dashboard_generator.py:9722-9723` | S | Low–Med | V2 P0-5, ME QW-2, V3 QW-C1 |
| **F-5** | **Entry-price sanity band** — reject crypto entry outside 0.5×–2× of live Binance price; emit `_entry_reason`. | `audit_trail/quality_gates.py:9082` (`passes_active_gate` @ `:6739`), `:2375` | S | Low | ME QW-3, V3 QW-C1, V2 C_crypto rec2 |
| **F-6** | **Quarantine inverse zombies IN THE VIEW** (non-destructive) — `active_raw_open` excludes EXPIRED/`_quarantined` (`inverse_*` age>7d); keep `active_raw` intact. | `audit_trail/dashboard_generator.py:17481-17485`; (source fix = F-12) | S | Low | V2 P0-7, V3 QW-C2 |
| **F-7** | **Dedupe by `id` + cross-ledger conflict log** — build `id→row` index over `active_raw+recent_closed`; tag `_dup_id`/`_id_conflict`; emit `id_conflicts_*.jsonl`. | `audit_trail/dashboard_generator.py:9825-9877`, `:9888-9932`, `:17481-17485` | S–M | Low–Med (counts move down) | V2 P0-4/P1-5, V3 QW-C4, ML 3.4 |
| **F-8** | **Status/PnL sign + SL/TP ordering enforcement** — flag LOST-with-positive-PnL; reject `SL>entry` (LONG) / `SL<entry` (SHORT). | `audit_trail/universal_pick_resolver.py:931` (`_heal_no_price_row`) | S | Low | V3 QW-C5, V2 C_crypto rec3 |
| **F-9** | **Clock-expiry must not publish `pnl_pct=0.0`** — tag `resolution_kind="clock_expired"`, `quote_status="STALE"`, `pnl_display=None`; keep last price as history. | `audit_trail/dashboard_generator.py:9596-9605`, `:9618-9650` | S | Low | V2 P0-3 |
| **F-10** | **Fix `summary_picks` WR denominator** — `win_rate = wins/(wins+losses)` over same terminal predicate; fail closed (>100% → null). | `tools/sync_summary_picks_json.py:63-65`, `:161` | S | Low (diagnostic only) | V2 P0-6 |
| **F-11** | **Recompute `unrealized_pnl_pct` + fix 8 sign / 15 calc mismatches** in `live_picks.db`; refresh `current_price`/`last_checked`; emit EXIT_STALE for ~172d-old rows. | `live_picks.db` (SQL §3.1–3.3); `ml_gatekeeper/gatekeeper.py` (verify unchanged) | S | Low–Med | ML 3.1-3.3, V3 PEER_REVIEW rec1 |
| **F-12** | **Fix inverse emission at source** — stable ID from source pick, bounded merge (`MAX_OPEN_PER_STRATEGY=1`, 7d cap), single atomic writer. | `alpha_engine/inverse_strategies.py:410,:436,:547-560`; `alpha_engine/inverse_loser_mutations.py:231,:398-400` | M | Med (emission volume changes) | V2 P1-2, V3 QW-C2 |
| **F-13** | **Case-dupe asset_class normalization** — `CRYPTO`/`crypto` → single canonical class at ingest. | ingest path; `audit_trail/dashboard_generator.py` (`_MEME_TO_CRYPTO`), `audit_trail/trade_geometry.py` | S | Low | ML 3.4 |
| **F-14** | **Publication discipline / no-size gating** — class tiles print `n` + cohort + `single_source_pct`; block WATCH when policy-clean n<30. | `alpha_engine/money_ready_verdict.py`; `audit_dashboard/template.html:908` | S | Low | V2 P1-8, V4, V3 PEER_REVIEW rec4 |
| **F-15** | **ML confidence inversion flip** — `effective_conf = 1 - raw_conf` (crypto-only, flag) then re-calibrate. | `ml_gatekeeper/gatekeeper.py`; `ml_gatekeeper/crypto_calibration.json` | M | Med (band-aid) | V4 MF-2 |
| **F-16** | **PF inflation guard** — `source IN ('live_picks','closed_ledger')` filter + `COUNT(DISTINCT pick_id)`; show raw vs dashboard PF side-by-side. | `audit_trail/dashboard_generator.py` (PF aggregation); `audit_dashboard/template.html` | M | Med | V4 QW-2 |
| **F-17** | **Purge AI-Challenge zombie picks** — one-off `UPDATE … SET status='EXPIRED', exit_reason='audit_zombie_purge' WHERE source='ai_challenge' AND created_at<'2026-09-01'` + nightly age rule. | one-off SQL; `tools/db_freshness_check.py` | S–M | **Med — destructive SQL UPDATE on live rows (dry-run required)** | V4 QW-3, V3 PEER_REVIEW |
| **F-18** | **Kalshi refresh-or-drop** — `entry_price: 0 → None`; drop `kalshi_signal_agent` rows >7d; use `generate_kalshi_picks()` real entry. | `prediction_market_agents/kalshi_signal_agent.py:489`; `alpha_engine/kalshi_signals.py:621,:650`; `audit_trail/quality_gates.py:6739` | M | Med | ME QW-5 |
| **F-19** | **Placeholder flat-3% cohort detector** — stamp `_placeholder_stats=True` and exclude from WR/PF when all wins == fallback TP% (100% WR, no exit_price). | `audit_trail/dashboard_generator.py:7516,:8040-8081,:8102`; `alpha_engine/strategy_blocklist.py:270-292` | M | Med | ME QW-6 |
| **F-20** | **Forward-scanner seeded batch flag** — stamp `_seeded_at`+`_unquoted=True` at ingest until first refresh. | `incubator/backtest_team/forward_signal_scanner.py` | S | Med | ME QW-7 |
| **F-21** | **Smart Picks sample-size gate** — no PF/WR/Sharpe when `n_closed < 20`; weight by `sqrt(n_closed)`. | `alpha_engine/smart_picks_engine.py`; `audit_trail/dashboard_generator.py` | M | Low | V4 MF-3 |
| **F-22** | **Forward-validation repair-or-retire** — wire crypto to paper-trading OR replace `forward_validated` with `paper_trading_verified`. | `alpha_engine/forward_validator.py`; `paper_trading/strategies/crypto_paper_adapter.py` | M | Med | V4 MF-1 |
| **F-23** | **Server quote pipeline v2** — re-quote every OPEN row (not just curated), persist `quote_snapshot.json`, CI gate `open_quote_coverage ≥ 0.80`. | `audit_trail/dashboard_generator.py:9538,:14548-14551,:17481-17485` | M | Med | V2 P1-1 |

**Flags:**
- **Destructive:** F-17 (SQL UPDATE purge of live rows) — V4 proposes it; dry-run + backup mandatory. V2 explicitly declines to delete rows (view-only quarantine F-6); V3 QW-C2 also says "drop at ingestion" (destructive).
- **No peer VETO recorded** on any fix; V2 VETOs *deleting* evidence (keeps `active_raw` intact).

---

## 4. Conflicts / disagreements

1. **Quote-status representation** — V2: enum `quote_status ∈ {LIVE,UNQUOTED,STALE,LAST_CLOSE}` (additive field). ME: boolean `_unquoted=True` + `pnl_pct=None`. V3/V4: plain "stale" label. Must pick one enum; enum wins (richer, non-mutating).
2. **null-vs-label `pnl_pct`** — V2 P0-1 says "do NOT mutate `pnl_pct` in enrichment; renderer decides." ME QW-4 says set `pnl_pct=None` when `current==entry` and unquoted. These are mutually exclusive; resolve before F-1/F-3 land.
3. **Dedup key** — V2 P0-4/P1-5: `id` first then 4-tuple `(source,symbol,direction,strategy)`. V2 C_crypto rec4: `(symbol,direction,entry,timestamp)`. ML: case-normalized `asset_class`. Pick one canonical key; note the different goals (ID-integrity vs tuple-dupe vs class-dupe) are complementary, not interchangeable.
4. **Entry sanity threshold** — ME: 0.5×–2× of Binance price. V3 QW-C1: `entry < 1e-3 * symbol_price`. V2 C_crypto: per-symbol band. Different magnitude triggers (0.5×–2× catches the 0.26/1.334 BTC garbage; 1e-3 catches only near-zero).
5. **Active-crypto count (layer mismatch)** — V4 = 3 (dashboard), V1 = 402 OPEN (`active_raw`), ML = 101 (`live_picks.db`). Different layers/DBs; reconcile before trusting any global count.
6. **NEAR PnL mark** — V4 dash 2.74% vs live 3.46%; V2 3.16% (@15:00Z); V1 3.07%. Same pick, different quote times; master plan must pick one mark convention (see F-2/F-23).
7. **Crypto PF magnitude** — V4 dash 1.80 vs raw 0.37 (5×); V2 policy-clean 0.2595; V1 0.93. Different cohorts/metrics (dashboard aggregate vs raw closed-ledger vs policy-clean) — needs a single published PF definition (F-16).
8. **Zombie quarantine scope** — V2 P0-7 = view-only (non-destructive). V3 QW-C2 = "drop at ingestion". V4 QW-3 = destructive SQL purge. Align on view-first (F-6), then source fix (F-12), purge last (F-17).

---

## 5. UNVERIFIED items

- Root cause of `0.0 / 0.26 / 1.334` BTC entries in `inverse_luxalgo_confluence` (likely units/last-price lookup bug) — untraced to source (V2 C_crypto:219).
- Exact intraday exit prints used by the dashboard resolver (TP/SL/FORCE_CLOSED) — only daily/1h klines fetched (V2 C_crypto:217).
- Whether `current_price == entry_price` with `pnl=0.0` is an intentional "no quote" sentinel or a bug (V2 C_crypto:218).
- The 14:30Z freeze cause — invocation/timing vs total-fetch miss; arithmetic path verified correct on re-run (V2 P0-1:41).
- `dashboard_data.json` 26-day staleness — diagnosed by all, fixed by none (V3 PEER_REVIEW:62).
- `kalshi_mtf_consensus` ~7-month-stale on-disk snapshot — flagged, not hardened (V3 PEER_REVIEW:64).
- Real-money vs paper distinction for active picks (V3 PEER_REVIEW:63).
- FX intraday moves for USDCAD=X / NZDUSD=X — only daily rates checked (V2 C_crypto:220).

---

## 6. Recommended P0 implementation order (top 5, impact ÷ risk)

1. **F-4 — Stop `None → 0.0` entry coercion.** Kills the XRP phantom and 85 zero-entry rows at the source; one-line emitter change; gate already rejects `entry<=0`. Highest impact per risk.
2. **F-2 + F-1 — Re-quote live crypto + quote-provenance stamp.** Directly fixes the headline 83%-frozen / 19/20 `current==entry` defect and makes every unpriced row countable instead of silently 0.00%.
3. **F-6 — Quarantine inverse zombies in the view.** Non-destructive; removes 71% of null-current crypto rows from the default raw view (4,148 → 691).
4. **F-3 — `UNQUOTED`/`STALE`/`LAST CLOSE` render contract.** Stops `+0.00%` being published as a claim; display-only, flag-gated.
5. **F-7 — Dedupe by `id` + cross-ledger conflict log.** Removes the "same trade counted 2–4×" error from counts/PF; additive tags + a review artifact, no row removal.
