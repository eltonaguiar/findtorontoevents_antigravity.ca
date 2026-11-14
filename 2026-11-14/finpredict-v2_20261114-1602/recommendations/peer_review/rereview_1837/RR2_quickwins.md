# RR2 — Review of peer quick-win bundle (flaxen-hair `quick_wins/` + finpredict `2026-11-14T160004Z`)

**Reviewer:** RR2 · **Clock:** 2026-11-14T18:40Z · **Mode:** read-only (no repo source modified; only this report written)
**Subject:** `.kilo/worktrees/finpredict/quick_wins/**` (11 files) + `.../2026-11-14/finpredict/2026-11-14T160004Z/quick-wins/by-asset-class/{BOND,CRYPTO,FOREX}.md` + `peer-review/PEER_RECONCILIATION.md`
**Compared against:** `recommendations/QUICK_WINS.md`, `per_asset_class/{bond_mutual_funds,crypto_commodity,equity_etf,forex_futures}.md`, `patch_plan/P0_QUICK_WINS.md`, `MASTER_AUDIT.md`
**Code baseline:** worktree `finpredict-v2`, branch `finpredict-v2`, HEAD `b951bcf2d7a`

---

## VERDICT: **FAIL** (do not merge the bundle as written)

**Selective merge: PASS** for the ~20 classifier/data-honesty items enumerated below.

The peer bundle is strong on **findings** and weak on **fix execution**. Four blocking reasons:

1. **Destructive fixes** — purge/DELETE, close-at-entry-or-stale-price, `pnl_pct = 0.0` on expiry, backdated `closed_at`, a direction-blind mass `UPDATE`, and an explicit ML-gate inversion (details in §5).
2. **PnL unit contradiction** — the shared script normalizes to **decimal ratio**, peer `FX-1` says **percent**, peer ETF verification requires **ratio**, and our deployed generator writes **percent** (`dashboard_generator.py:8062-8064`). Merging the script unchanged flips every displayed PnL by 100×.
3. **Dedup-key conflict** — five different peer keys; most collapse legitimate cross-strategy/re-entry rows and contradict our canonical registry key.
4. **Mutual-fund build** — `MF-2..MF-10` create the exact always-empty class our `NOT_BUILT` recommendation exists to prevent.

Findings that merely corroborate our audit are welcome and need no re-work (see §2, "ALREADY_COVERED").

---

## 1. Per-file table

| # | Peer file | What it adds | Disposition |
|---:|---|---|---|
| 1 | `quick_wins/README.md` | 10 merged findings, P0–P3 order, script index | Findings **ADOPT** (corroboration). Order **MERGE**. No standalone fix. |
| 2 | `01_overall/OVERALL_QUICK_WINS.md` | 13 cross-cutting fixes + 5-class PF table + staleness table | **MERGE** mostly; `MUTUAL_FUND` class item **REJECT**; PF ratios **UNVERIFIED/stale**. |
| 3 | `02_equity_stocks/EQUITY_QUICK_WINS.md` | EQ-1..EQ-10 | **MERGE** 8, **REJECT** 1 (EQ-2 hand-edit pattern), **ADOPT** 1 (EQ-10 after P0-1). |
| 4 | `03_bonds/BONDS_QUICK_WINS.md` | BO-1..BO-9 | **MERGE** 6, **REJECT/VETO** 1 (BO-3), **UNVERIFIED** 2 (BO-5, BO-7). |
| 5 | `04_etfs/ETFS_QUICK_WINS.md` | ET-1..ET-9 | **ADOPT** 3, **MERGE** 4, **REJECT/VETO** 1 (ET-4 snippet), 1 bad citation. |
| 6 | `05_mutual_funds/MUTUAL_FUNDS_QUICK_WINS.md` | MF-1..MF-12 | **REJECT** MF-2..MF-10; **ALREADY_COVERED** MF-1; **MERGE** caveat from MF-11/MF-12. |
| 7 | `06_forex/FOREX_QUICK_WINS.md` | FX-1..FX-11 | **ADOPT** 4, **MERGE** 3, **REJECT/VETO** 3 (FX-3/4/8 as written), **UNVERIFIED** 1. |
| 8 | `07_crypto/CRYPTO_QUICK_WINS.md` | CR-1..CR-10 | **ADOPT** 1 (CR-6 intent), **MERGE** 5, **REJECT/VETO** 3 (CR-1/5/8/9). |
| 9 | `08_commodities_futures/COMMODITIES_FUTURES_QUICK_WINS.md` | CM-1..CM-9 | **ADOPT** 1 (CM-5), **MERGE** 3, **ALREADY_COVERED** 3. |
| 10 | `shared/normalize_pnl_units.py` | PnL repair CLI | **MERGE after rewrite**; not CI-safe; unit conflict. |
| 11 | `shared/validate_pick_ids.py` | Duplicate-ID CI check | **ADOPT after 4 hardening fixes**; usable as CI gate. |
| 12 | `.../by-asset-class/BOND.md` | 2 fixes: real mark + no entry-stamp; 24h no-quote expiry | **ADOPT** both (best-executed file in the bundle). |
| 13 | `.../by-asset-class/CRYPTO.md` | 7 fixes: failover, none→0, entry band, unquoted label, Kalshi, flat-3%, seed flag | **ADOPT** all 7 (map to our enum). |
| 14 | `.../by-asset-class/FOREX.md` | 3 fixes: quarantine phantoms, price-file age guard, min-agreement 2 | **ADOPT** all 3. |
| 15 | `peer-review/PEER_RECONCILIATION.md` | Corrections, veto list, unified contract | **ADOPT** as merge guidance; it already vetoes most of what RR2 vetoes. |

---

## 2. Fix classification (ADOPT / MERGE / REJECT / ALREADY_COVERED)

### 2.1 Cross-cutting (README + OVERALL)

| Peer ID | Fix | Class | Our target |
|---|---|---|---|
| README-1 / OW-1 | Recompute signed PnL + refresh `current_price`/`last_checked`, flag >30–60d stale | **MERGE** | `patch_plan/P0_QUICK_WINS.md` P0-5 (unit must be percent) + `QUICK_WINS.md` #5 |
| README-2 / OW-3 | Unique pick IDs | **ADOPT** (stable ID, not counters) | `P0_QUICK_WINS.md` P0-8 |
| README-3 / OW-11 | Decouple `ml_score` from `confidence` | **ADOPT with correction** | `crypto_commodity.md` P1-8 / `equity_etf.md` (data fix) — drop the claim "ML code is SOUND"; v3 found leakage (`gatekeeper.py:170-186`) |
| README-4 / OW-2 | Stale-pick refresh/lifecycle | **MERGE** | `QUICK_WINS.md` "force-close/age-out → documented TIME_EXIT" |
| README-5 | No verifiable live PnL | **ALREADY_COVERED** | `QUICK_WINS.md` quote contract (#5) |
| README-6 | Three divergent stores | **ALREADY_COVERED** | `MASTER_AUDIT.md` §2 populations table |
| README-7 | dbpasses — do nothing | **ALREADY_COVERED** | `MASTER_AUDIT.md`, corrections.md |
| README-8 | Mutual funds zero coverage | **ALREADY_COVERED** | `bond_mutual_funds.md` QW-2 / `MASTER_AUDIT.md` §2 |
| README-9 | Empty tables (`audit_trail.db` 9 empty) | **MERGE** (correct the count) | `P0_QUICK_WINS.md` / `bond_mutual_funds.md` — reconciliation says 8 empty + `bt_backtest_runs=20`,`meta=1`, so "all 9 empty" is wrong |
| README-10 | TP/SL resolver checks TP before SL, includes pre-entry bars | **MERGE as P1 investigation** | `equity_etf.md` P1-7; do **not** change ordering in a display quick-win (our do-not-do #6) |
| OW asset_class backfill | Backfill 6 DB + 17 dashboard `UNK` rows | **ADOPT** (query-time derivation if DB has no column) | `equity_etf.md` P0-6; **not** a blind `UPDATE live_picks SET asset_class` (schema UNVERIFIED) |
| OW `MUTUAL_FUND` class + schema | Add class/symbol set | **REJECT** | conflicts `bond_mutual_funds.md` QW-2 + do-not-do #4/#8 |
| OW Alpha Engine `cancel-in-progress` | Remove `cancel-in-progress: true` on 2h cron | **MERGE-CONDITIONAL / UNVERIFIED** | `.github/workflows/alpha-engine-live.yml:39` is indeed `true` (verified), but the "kills 45–60 min runs" mechanism is unproven: a 45–60 min body finishes inside a 2h cron. Verify with run timing before flipping; per `PEER_RECONCILIATION:109` resolve per-workflow, not globally |
| OW JSON freshness gate | Sidecar freshness manifest | **ALREADY_COVERED** | `P0_QUICK_WINS.md` P0-7 |
| OW frozen dashboard prices | Live cross-check fixes | **ALREADY_COVERED** | `QUICK_WINS.md` #5 |
| OW ghost dedup (DELETE + UNIQUE index) | Remove 22,947 rows | **MERGE (quarantine only)** / DELETE **VETO** | `QUICK_WINS.md` #9, `P0_QUICK_WINS.md` P0-8 |
| OW TIME_EXIT limbo | Batch resolver | **MERGE** | `QUICK_WINS.md` force-close/age-out (documented TIME_EXIT, not 0%) |

### 2.2 EQUITY

| Peer ID | Class | Note / target |
|---|---|---|
| EQ-1 PnL normalize | **MERGE** | must also update `realized_pnl_pct`/`unrealized_pnl_pct` (script does not) |
| EQ-2 expire META open pick | **MERGE (via resolver/ingest)** | `EXPIRED` + `pnl_pct: null` is contract-compatible; **reject** hand-editing shipped JSON, and do not name a fake close price |
| EQ-3 unique equity IDs | **ADOPT** | replace `#N` suffix with stable source-derived ID |
| EQ-4 decouple ml_score | **ADOPT (data)** | `equity_strategies.py:594` citation is **FALSE** (see §4) |
| EQ-5 SPY/QQQ as ETF | **ALREADY_COVERED** | `equity_etf.md` P0-6 symbol authority |
| EQ-6 equity freshness gate | **MERGE** | `equity_etf.md` P1-4 |
| EQ-7 asset_class backfill | **ADOPT (conditional)** | `live_picks` has no `asset_class` column per peer ET-7; contradictory with BO-7. Verify schema first |
| EQ-8 refresh 5 stale prices | **MERGE** | real quote + `quote_status`; never copy entry |
| EQ-9 emit CLOSED/EXIT | **ADOPT** | documented exit, real price or `null` |
| EQ-10 rerun scanners | **ADOPT after P0-1** | rerun is not a root-cause fix; `KeyError: 'LONG'` is |

### 2.3 BONDS

| Peer ID | Class | Note / target |
|---|---|---|
| BO-1 PnL normalize | **MERGE** | percent canonical |
| BO-2 unique IDs | **ADOPT** | `multi_asset/scanner.py:589` `_pick_id` verified date-only |
| BO-3 close ZN=F, `realized_pnl_pct: 0.0`, `closed_at: 2026-04-25` | **REJECT / VETO** | fabricates outcome + backdates. Replace: `EXPIRED`, `pnl_pct: null`, `closed_at: now`, reason `STALE_NO_QUOTE` |
| BO-4 BOND category mapping | **MERGE** | `equity_etf.md` P0-6 / `forex_futures.md` P1-1 |
| BO-5 verify migration | **ADOPT (read-only)** | DB value **UNVERIFIED** from this worktree |
| BO-6 bond MF/ETF data feed | **MERGE (bond ETF only)** | our `bond_mutual_funds.md` QW-4; MF part REJECT |
| BO-7 sync `active_picks_bond.json` | **MERGE-CONDITIONAL** | schema contradiction (see §4); dedupe by `(symbol,strategy)` keeps SHY×3 unless strategy differs — does not match our key |
| BO-8 refresh 2 stale bond rows | **MERGE** | real quote only |
| BO-9 emit exits / populate `symbol_strategy_stats` | **ADOPT** | pairs with our QW-1 |

### 2.4 ETFs

| Peer ID | Class | Note / target |
|---|---|---|
| ET-1 PnL normalize | **MERGE** | percent canonical; peer's own "ratio" verification is the conflict |
| ET-2 dedupe XLE×2/XLY×2, keep highest confidence | **REJECT as written** | key `(symbol, entry_date, direction)` collapses different strategies; "keep highest confidence" biases the sample; snippet also deletes rows (`or list(best.values())` path). Use our `_collapse_cross_source_dupes` with `(asset_class, symbol, direction, strategy)` + annotate |
| ET-3 globally unique IDs (uuid) | **REJECT as written** | uuid4 breaks idempotency: every re-run creates a "new" pick. Use stable source-derived ID |
| ET-4 resolve stale ETF opens, `exit=current or entry`, PnL arithmetic | **REJECT / VETO** | close-at-stale/entry. Quarantine + `quote_status=STALE`, `pnl_pct: null` |
| ET-5 decouple ml_score | **ADOPT** | data-level |
| ET-6 add KWEB, VLUE to `ETF_SYMBOLS` | **ADOPT** | extend: `VCSH→BOND`, `IBIT/BITO→ETF` per our P0-6 |
| ET-7 sync ETF picks into `live_picks` metadata | **MERGE-CONDITIONAL / UNVERIFIED** | no DB in worktree; schema claims conflict |
| ET-8 48h ETF freshness guard | **MERGE** | express as class SLA in quote contract, not a separate flag |
| ET-9 ETF tile + `strategy_stats` | **ALREADY_COVERED** | `bond_mutual_funds.md` QW-1/QW-2 + `equity_etf.md` P1-6 |

### 2.5 MUTUAL FUNDS

| Peer ID | Class | Note |
|---|---|---|
| MF-1 gap documentation | **ALREADY_COVERED** | `bond_mutual_funds.md` QW-2 |
| MF-2 `MUTUAL_FUND_SYMBOLS` | **REJECT** | class with no emitter/NAV source |
| MF-3 `_CAT_MAP`/`_LOWER_TO_UPPER` | **REJECT** | same |
| MF-4 classify fund symbols before equity | **REJECT** | same |
| MF-5 `"MUTUAL_FUND": 7` in gatekeeper | **REJECT** | creates reachable class for non-existent picks |
| MF-6 dashboard MF tile | **REJECT** | conflicts NOT_BUILT badge |
| MF-7 `is_mutual_fund()` | **REJECT** | helper without consumer |
| MF-8 strategy hints | **REJECT** | same |
| MF-9 `mutual_fund_scanner.py` | **REJECT** | stub emitter = placeholder picks (already vetoed in `PEER_RECONCILIATION:86`) |
| MF-10 `mutual_fund_strategies.py` stubs | **REJECT** | same |
| MF-11 wire MF into PnL/freshness | **MERGE (caveat only)** | NAV is daily/T+1; use it in the NOT_BUILT rationale, do not build a pick schema |
| MF-12 propose NAV source | **MERGE (research note)** | acceptable as documentation, not a quick win |

### 2.6 FOREX

| Peer ID | Class | Note / target |
|---|---|---|
| FX-1 normalize to **percent** | **ADOPT** | this is the correct unit; conflicts with the shared ratio script |
| FX-2 `recent_picks.txt` hardcoded header | **ADOPT** | `fetch_recent_picks.py:13` verified exact; trivial |
| FX-3 expire 23 forward-test picks, `pnl_pct: 0.0` | **REJECT (0.0) / MERGE (status)** | use `EXPIRED_FORWARD_TEST` + `pnl_pct: null` |
| FX-4 widen `PROVEN_STRATEGIES` incl. blacklisted `forex_rsi2_mean_reversion` | **REJECT (blacklisted) / MERGE-CONDITIONAL** | `carry_momentum` only after evidence; peer's "proven" claim is UNVERIFIED. Blacklisted strategy is a veto |
| FX-5 unique IDs | **ADOPT** | stable ID, not timestamp+counter if re-run repeats |
| FX-6 decouple ml_score | **ADOPT** | data-level |
| FX-7 honor `BLACKLISTED_STRATEGIES` | **ADOPT (shadow)** | our `forex_futures.md` P0-6 annotate first; skip-vote is safe but count `would_drop` |
| FX-8 respect `FOREX_HARD_DISABLE=1` | **REJECT as P0** | our audit shows the computed default is **OFF** (`config.py:345`); enforcing today drops 277 rows. Shadow/annotate only our P0-6 |
| FX-9 dedupe consensus votes `(symbol,direction,strategy)` | **ADOPT** | vote-level only; compatible |
| FX-10 fix FX resolver (96.6% null) | **ADOPT/MERGE** | `forex_futures.md` P1-3 quote pipeline |
| FX-11 replace IG/myfxbook with regime momentum | **REJECT (not a quick win)** | strategy change, unvalidated |

### 2.7 CRYPTO

| Peer ID | Class | Note / target |
|---|---|---|
| CR-1 expire stale positions at `exit_price=entry_price`, `pnl=0` | **REJECT / VETO** | fabricated flat close. `EXPIRED` + `pnl_pct: null`, keep last observed price as history |
| CR-2 PnL normalize | **MERGE (careful)** | `ratio_store.py:165-167` already writes **percent**; do not divide it again |
| CR-3 unique `signal_id` (uuid4 snippet) | **ADOPT intent / REJECT snippet** | idempotent stable ID from source pick; uuid4 breaks re-run stability |
| CR-4 decouple ml_score | **ADOPT** | data-level; `gmx_scraper.py:555` verified |
| CR-5 mass `UPDATE positions SET pnl_pct=...` | **REJECT / VETO** | formula `(exit-entry)/entry*100` has no direction term → corrupts every SHORT; mass update on live DB |
| CR-6 fix crypto price fetcher | **ADOPT (retarget)** | citation `audit_trail/fetch_stock_prices.py` is the **wrong module**; use `dashboard_generator._fetch_prices_with_failover:1179` + `coinglass_strategies/data_fetcher.py:463` |
| CR-7 kill PF inflation via source tag + `COUNT(DISTINCT pick_id)` | **MERGE** | adopt source-tag cohorting; **not** `pick_id` dedupe (our registry key). "5×" is stale — fresh CRYPTO PF 0.9196 per `PEER_RECONCILIATION:84` |
| CR-8 purge 8-month zombie picks | **REJECT / VETO** | deletion destroys audit trail; quarantine |
| CR-9 invert ML calibration (`1 - raw_conf`, `CRYPTO_CONF_FLIP`) | **REJECT / VETO** | double-inverts an already-broken label; in our veto list |
| CR-10 Smart Picks n>=20 | **ADOPT (intermediate)** | keep class headline at n>=100 (our P1-6); n>=20 only inside Smart Picks |

### 2.8 COMMODITIES / FUTURES

| Peer ID | Class | Note / target |
|---|---|---|
| CM-1 PnL normalize | **MERGE** | percent canonical; line refs verified exact |
| CM-2 resolve 11 stale commodity opens | **MERGE** | quarantine/`EXPIRED`, null PnL |
| CM-3 unique IDs | **ADOPT** | but `SEEN_IDS` process-local in snippet is non-deterministic; use persistent registry key |
| CM-4 decouple ml_score | **ADOPT** | data-level |
| CM-5 COT freshness guard + `CFTC_COT_FETCHER_ENABLED=1` | **ADOPT** | `tools/cftc_cot_fetcher.py` confirms env-gated; 7-day reject is reasonable |
| CM-6 FUTURES 0 live / 26d artifact | **ALREADY_COVERED** | `forex_futures.md` P1-5/P1-6 + class gate |
| CM-7 COMMODITY 4 picks 156d | **ALREADY_COVERED** | populations table / quarantine |
| CM-8 CT=F DSR falsified | **ADOPT as documentation** | no code change |
| CM-9 PF 131.6 artifact | **ALREADY_COVERED** | `crypto_commodity.md` P1-8 |

### 2.9 by-asset-class files (the strongest peer artifacts)

| Peer fix | Class | Note |
|---|---|---|
| BOND #1 real mark via `universal_price_enricher`; **never** stamp `current_price=entry_price`; `<80% priced → DATA_STALE` | **ADOPT** | exactly our quote contract; complements `bond_mutual_funds.md` QW-4/QW-7 |
| BOND #2 auto-expire `current_price=null` + age>24h as `STALE_NO_QUOTE` | **ADOPT** | must also set `pnl_pct=null` (implied, make explicit) |
| CRYPTO #1 prepend Binance mirror failover | **ADOPT** | `crypto_commodity.md` P1-1 |
| CRYPTO #2 None entry must stay None | **ADOPT** | `prediction_market_consensus.py:589` verified |
| CRYPTO #3 entry band 0.5×–2× known price | **ADOPT** | new, concrete (BTC 0.3322 / 1.334 garbage) |
| CRYPTO #4 `_unquoted=True`, `pnl_pct=None` | **MERGE** | map to our `quote_status="UNQUOTED"`; one enum, not two flags |
| CRYPTO #5 Kalshi `entry_price: 0 → None`, exclude >7d | **ADOPT** | `kalshi_signal_agent.py:489` verified |
| CRYPTO #6 flat-fallback-TP placeholder detector (key on fallback TP, not 3.0) | **ADOPT** | targets `dashboard_generator.py:7516/8081/8102` verified |
| CRYPTO #7 forward-seed `_seeded_at`/`_unquoted` | **MERGE** | map to `PLACEHOLDER`/`UNQUOTED` |
| FOREX #1 quarantine 11 phantoms via validity filter, no hard delete | **ADOPT** | matches our P1-6 + do-not-do |
| FOREX #2 `stock_forex_prices.json` >24h age guard | **ADOPT** | concrete consumer list; complements P0-7 |
| FOREX #3 FOREX min agreement 1→2 (shadow) | **ADOPT** | `non_crypto_consensus.py:134` verified |

---

## 3. Citation spot-check (28 claims opened)

**Method:** `grep -n` / `sed -n` / `json` reads in `finpredict-v2` at HEAD `b951bcf2d7a`. A line is "exact" only if the cited symbol/statement is at the cited line.

| # | Peer citation | Verified content | Result |
|---:|---|---|---|
| 1 | `ml_gatekeeper/gatekeeper.py:73` | `ASSET_CLASS_MAP` 7 classes, no MF | EXACT |
| 2 | `dashboard_generator.py:6763` | `_PER_ASSET_CLASSES` 7 classes | EXACT |
| 3 | `dashboard_generator.py:6824-6826` | `threshold_pass = (active_count == 0 or ...)` | EXACT |
| 4 | `alpha_engine/scanner.py:2937-2942` | `{"BUY": [], "SELL": []}` then `[sig_type].append` | EXACT |
| 5 | `tools/sync_summary_picks_json.py:63-65,161` | resolved / wins / losses then `100*wins/resolved` | EXACT |
| 6 | `prediction_market_consensus.py:589` | `entry_price = ... or 0` | EXACT |
| 7 | `quality_gates.py:1724` | `BLOCKED_ASSET_CLASSES = {"FOREX","COMMODITY","FUTURES","BOND"}` | EXACT |
| 8 | `institutional_picks_engine.py:1455` | `f"{strat}::{sym}::{today}"` | EXACT (path drift: real path `multi_asset/institutional_picks_engine.py`) |
| 9 | `alpha_engine/config.py:264` | `BLACKLISTED_STRATEGIES = [` | EXACT |
| 10 | `non_crypto_consensus.py:134` | `_min_agreement_for_pick(..., default: int = 2)` | EXACT |
| 11 | `audit_dashboard/portfolio_manager.py:88` | `PROVEN_STRATEGIES = {` | EXACT |
| 12 | `tools/edge_filter_engine_v3.py:57` | `FOREX_PROVEN_STRATEGIES = {` / `"forex-rsi-ema-scout"` | EXACT |
| 13 | `fetch_recent_picks.py:13` | `now_est = datetime.fromisoformat('2026-03-11T20:24:32-04:00')` | EXACT |
| 14 | `coinglass_strategies/config.py:69` | `MAX_HOLD_HOURS = 48` | EXACT |
| 15 | `coinglass_strategies/ratio_store.py:165-167` | `pnl_pct = ... * 100` (percent) | EXACT |
| 16 | `copy_trader_intel/gmx_scraper.py:555` | `"ml_score": confidence` | EXACT |
| 17 | `dashboard_generator.py:8065-8072` | fraction/percent heuristic `if abs(pnl_val) < 0.10: *100` | EXACT |
| 18 | `universal_pick_resolver.py:433-443` | `_EQUITY_ETF_TICKERS` — TLT/HYG only from BOND set | EXACT |
| 19 | `.github/workflows/etf-bond-scanner.yml:159` | `SKIP_FRED: '1'` | EXACT |
| 20 | `alpha_engine/bond_scanner.py:289-296` | `fetch_bond_bundle(lookback_days=365)` | EXACT |
| 21 | `multi_asset/portfolio_defs.py:382-395,677` | `tactical_fund_rotation` + `mutual_fund` universe | EXACT |
| 22 | `commodity_signal_generator.py:231-238,250` | RNDR/ARB "silver", XLM/DOT "oil" | EXACT |
| 23 | `coinglass_strategies/scanner.py:38` | `cmd_portfolio()` calls `monitor_positions()` | EXACT |
| 24 | `multi_asset/scanner.py:589` | `_pick_id` = `strategy::symbol::dt` | EXACT |
| 25 | `multi_asset_closed.json:78,104,130`; `institutional_closed.json:500` | `-0.7481`, `-3.6402`, `-0.3754`, `-0.8789` | EXACT |
| 26 | `dashboard_generator.py:7516/8081/8102` | `_coerce_closed_zero_pnl_from_outcome`, call, `_ac_defaults` fallback TP | EXACT |
| 27 | `prediction_market_agents/kalshi_signal_agent.py:489` | `"entry_price": 0,` | EXACT |
| 28 | `.github/workflows/alpha-engine-live.yml:39` | `cancel-in-progress: true` (2h cron, 45–60 min body) | EXACT (causal claim unproven) |

**Drift / wrong citations**

| ID | Claim | Reality |
|---|---|---|
| D1 | MF file: `_CANONICAL` at `dashboard_generator.py:6128` | No `_CANONICAL` at 6128; sets are at **6027** and **6200** |
| D2 | ETF key observation: `equity_strategies.py:594` sector_rotation sets confidence only | `grep -n sector_rotation alpha_engine/equity_strategies.py` → **0 matches**; the file has 1,349 lines and line 594 is a comment block. Citation is false |
| D3 | CR-6: crypto fetch lives in `audit_trail/fetch_stock_prices.py (crypto path)` | Crypto fetch is `dashboard_generator._fetch_prices_with_failover` + `coinglass_strategies/data_fetcher.py`; `fetch_stock_prices.py` is equities/bonds |
| D4 | `asset_class.py:22-62` for `BOND_SYMBOLS` | `BOND_SYMBOLS` starts at **28**; `ETF_SYMBOLS` 37; `EQUITY_SYMBOLS` 55 |
| D5 | `coinglass_strategies/data_fetcher.py:462` | `fetch_current_price` `def` is at **463**; 462 is the section comment |
| D6 | `vix_reversal::AAPL` ×5, `GBPUSD=X` ×4 | In this worktree: AAPL **×4**, GBPUSD **×5** (SI/ZN/AAPL all ×4). Data-file variance, not code drift — peer's underlying duplicate claim holds |
| D7 | "`audit_trail.db` ALL 9 tables empty" | Contradicted by `PEER_RECONCILIATION:86`: `bt_backtest_runs=20`, `meta=1`, 8 empty |
| D8 | `live_picks.db` 128/129 stale, columns, row counts | **Not verifiable here**: no `data/live_picks.db` in this worktree. All SQLite-specific claims are UNVERIFIED |

---

## 4. Contract conflicts

### 4.1 Quote-status contract — CONFLICT (unit + status vocabulary)

- Our contract (`QUICK_WINS.md`): `LIVE / LAST_CLOSE / STALE / UNQUOTED / PLACEHOLDER`; `pnl_pct=null` when unquoted, never `0.0`.
- Peer by-class files **match** this (BOND #1 explicitly forbids `current_price=entry_price`; CRYPTO #4 uses `_unquoted` + null).
- Peer `quick_wins/` **violates** it in 5 places: CR-1 (`exit=entry, pnl=0`), ET-4 (`exit=current or entry`), BO-3 (`realized 0`, backdated close), FX-3 (`pnl=0.0`), EQ-8 ("refresh price" with no provenance field).
- Two-flag drift: peer adds `_unquoted`/`_seeded_at`; we have `quote_status`. **Merge rule:** one enum; `_unquoted` → `UNQUOTED`, seeded → `PLACEHOLDER`. Do not ship both.

### 4.2 Dedup key — CONFLICT

Our canonical: **ID-first**, then economic key `(strategy, normalized symbol, direction, UTC trade_date, round(entry_price, ENTRY_PRICE_ROUND))` (`P0_QUICK_WINS.md` P0-8, mirroring `tools/build_pf_registry.py:818-835`), and "do not dedupe by `pick_id` alone" across emitters.

Peer keys:
- ET-2 `(symbol, entry_date, direction)` + keep-highest-confidence → collapses different strategies and biases.
- BO-7 upsert `(symbol, strategy)` → preserves SHY×3 when strategies differ; does not match.
- CR-7 `COUNT(DISTINCT pick_id)` → directly contradicts our "IDs are source-prefixed, never match across emitters".
- CM-3 process-local `SEEN_IDS` → non-deterministic across runs.
- FX-9 `(symbol, direction, strategy)` → **compatible** for consensus votes only.
- CR-3/bond IDs date-only → violates stable-ID requirement.

### 4.3 `summary_picks` denominator — NO CONFLICT, GAP

Peer bundle never fixes the WR>100% denominator. Its aggregate PF claims (`CRYPTO 4.9x`, `EQUITY −7.9x`, `FOREX −18.7x`, `FUTURES +226x`) are **stale snapshots** (`PEER_RECONCILIATION:84`: fresh CRYPTO PF 0.9196; the 1.80/0.37 pair came from a 173-day-old snapshot). Keep our `QUICK_WINS.md` #2 / `P0_QUICK_WINS.md` P0-2 / `bond_mutual_funds.md` QW-3; do not import the ratios.

### 4.4 Mutual-fund NOT_BUILT — DIRECT CONFLICT

`MF-2..MF-10` add symbol set, gatekeeper class id, dashboard tile, `is_mutual_fund()`, hints, scanner and strategy stubs. This is the "add `MUTUAL_FUND` before an emitter exists" line already vetoed in `QUICK_WINS.md` §Veto and `PEER_RECONCILIATION:69`. The file's claim "no existing class is re-mapped" is technically true but misses that it creates a permanently `n=0` class that re-opens the vacuous-PASS bug. **REJECT.**

### 4.5 PnL unit — CONFLICT (highest merge risk)

| Source | Unit |
|---|---|
| Deployed generator (`dashboard_generator.py:8062-8064`) | **percent** (`*100`) |
| Our payload evidence (NEAR +2.74) | percent |
| Peer `normalize_pnl_units.py` | **ratio** |
| Peer `FX-1` | **percent** |
| Peer ETF verification | **ratio** (`-1 <= x <= 1`) |
| Peer `ratio_store.py` | already percent |

Merging the shared script unchanged makes every displayed PnL 100× too small. **Decision required before any merge:** declare `pnl_pct` = percent + `pnl_unit:"percent"` (recommended, zero display churn), or add a separate `pnl_ratio` field. Do not run the script until this is settled.

---

## 5. Script safety / CI-gate assessment

### 5.1 `normalize_pnl_units.py` — **not safe as-is; not a CI gate**

What is good: backs up to `.bak` (`shutil.copy2`), direction-aware formula, nulls OPEN rows, idempotent on a clean fixture.

Defects (all reproduced on a `/tmp` fixture, no repo files touched):

1. **Leaves the field that usually holds the value.** It only rewrites `pnl_pct`. A row with `pnl_pct:null` + `realized_pnl_pct:-3.6402` becomes `pnl_pct:-0.036402` **and keeps `realized_pnl_pct:-3.6402`** — new mixed units inside one row. Confirmed on the real shape of `multi_asset_closed.json`.
2. **Trusts stored percent over the price recompute.** `if abs(existing) > 1: pnl = existing/100` (`:60-62`). A stale/wrong percent (e.g. exit price frozen) is preserved, merely rescaled, instead of recomputed.
3. **`|v| == 1.0` boundary is misclassified** (strict `>`), so 1% and 100% are ambiguous and silently treated as ratio.
4. **`ambiguous` stat is dead** — always 0; no row is ever reported ambiguous, though the docstring/labels imply otherwise.
5. **Non-atomic in-place write** (`p.write_text`) with only a sidecar `.bak`; no `--dry-run`/`--check`, no unit metadata, exit 0 even when everything was skipped.
6. **Ratio output is incompatible with the deployed display** (§4.5).

**Recommendation:** treat as a one-time repair template, rewrite before use: percent output + `pnl_unit`, recompute-first, reconcile all three PnL fields, `--dry-run`, report ambiguity. Never wire into CI.

### 5.2 `validate_pick_ids.py` — **usable as a CI gate after 4 fixes**

Good: read-only, stdlib only, exit 1 on duplicates (verified), human-readable JSON.

Blocking issues:
1. **No-argument run exits 0 and prints `{"valid": true, "files": 0}`** (verified). A mistyped path list silently passes CI. Fix: `if not paths: return 2`.
2. **Rejects `entry_price: null`** on `status="SIGNAL"` rows (verified on a fixture). This conflicts with our stop-emitting-zero-entry contract. Fix: skip entry check when `status in {SIGNAL, PENDING_SIGNAL}` or `_invalid_entry`.
3. **No ID-format check.** It only catches exact duplicates; a unique date-only ID (the actual root cause of one-per-day duplicates) passes. Add `YYYY-MM-DD$` rejection.
4. **No baseline/warn-only mode** for the first rollout; today it fails on 25 duplicate groups in one closed file (verified), so it cannot be merged green immediately.

**Verdict:** ADOPT as our P0-8 CI assertion after (1)–(4); run warn-only for one release, then fail. It is a good fit for `tests/` + `P0_QUICK_WINS.md` P0-8.

---

## 6. Veto list (do not implement as written)

1. **Invert ML confidence calibration** — `CRYPTO_QUICK_WINS.md` CR-9 (`effective_conf = 1.0 - raw_conf`, `CRYPTO_CONF_FLIP`). Also in `QUICK_WINS.md` veto and `PEER_RECONCILIATION:69`.
2. **Purge / DELETE audit rows** — CR-8 ("purge 8-month zombies"), ET-4 ("close/purge"), OVERALL ghost dedup DELETE. Quarantine/tag instead.
3. **Close-at-entry-or-stale price** — ET-4 (`exit_price = current_price or entry_price`), CR-1 (`exit_price=entry_price`), BO-3 (`realized_pnl_pct: 0.0`), FX-3 (`pnl_pct: 0.0`). Fabricates outcomes.
4. **Backdated `closed_at`** — BO-3 sets `2026-04-25` for a pick being closed in November. Never backdate a resolution event.
5. **Mass `UPDATE` PnL without direction** — CR-5 `UPDATE positions SET pnl_pct = (exit-entry)/entry*100`, `pnl_dollar = quantity*pct/100`. Corrupts every SHORT and mass-writes a live DB.
6. **Mutual-fund class build** — MF-2..MF-10. Conflicts with `NOT_BUILT` and re-opens vacuous PASS.
7. **FOREX enforcement now** — FX-8 (`FOREX_HARD_DISABLE=1` respected everywhere) would drop all 277 rows; FX-4 adds the blacklisted `forex_rsi2_mean_reversion` to a proven whitelist. Shadow/annotate first.
8. **Non-idempotent IDs** — ET-3 uuid4, EQ `#N` counter, CR uuid4, CM process-local `SEEN_IDS`. Every rerun manufactures "new" picks.

Not present in these peer files (so no veto needed, but confirmed absent): **unblock FUTURES/COMMODITY**, **force-push / history rewrite**, **re-enable audit-dashboard `push:`**. Those risks exist in v4/ML, not here.

---

## 7. Top 8 additions for `QUICK_WINS.md` / per-class plans

| Rank | Addition | Source | Our target |
|---:|---|---|---|
| 1 | Crypto entry provenance trio: keep `None` (never `or 0`), reject entry outside 0.5×–2× known price, stamp `_unquoted` → `UNQUOTED` + `pnl_pct=null` | `by-asset-class/CRYPTO.md` #2–#4 | `crypto_commodity.md` P0-5 + new P0-8; `QUICK_WINS.md` #11 |
| 2 | Kalshi `entry_price: 0 → None` + exclude >7d stale Kalshi rows | `by-asset-class/CRYPTO.md` #5 (`kalshi_signal_agent.py:489`) | `crypto_commodity.md` P0-5 |
| 3 | Flat-fallback-TP placeholder detector (key on "all wins == fallback TP", not 3.0) and exclude from WR/PF | `by-asset-class/CRYPTO.md` #6 (`dashboard_generator.py:7516/8081/8102`) | `crypto_commodity.md` P1-8 + `E_statistical` |
| 4 | BOND: real mark only, never stamp entry; `<80% priced ⇒ DATA_STALE`; 24h no-quote expiry as `STALE_NO_QUOTE` with null PnL | `by-asset-class/BOND.md` #1–#2 | `bond_mutual_funds.md` QW-4/QW-7 (implementation detail) |
| 5 | `stock_forex_prices.json` >24h age guard in resolver consumers | `by-asset-class/FOREX.md` #2 | `QUICK_WINS.md` P0-7 + `forex_futures.md` P1-3 |
| 6 | FOREX consensus `_min_agreement_for_pick` 1→2, shadow-counted | `by-asset-class/FOREX.md` #3 (`non_crypto_consensus.py:134`) | `forex_futures.md` P0-6 |
| 7 | CFTC COT freshness gate (7-day reject) + enable `CFTC_COT_FETCHER_ENABLED=1` | `COMMODITIES_FUTURES_QUICK_WINS.md` CM-5 | `crypto_commodity.md` new P2 |
| 8 | Harden `validate_pick_ids.py` as CI gate + reject date-only `id` | `shared/validate_pick_ids.py` | `QUICK_WINS.md` #9 / `P0_QUICK_WINS.md` P0-8 / CI_GATES |

Runner-ups (not top 8): TP/SL ordering investigation (`investigate_tp_sl_bug.py` is read-only, no writes — safe to run); alpha-engine `cancel-in-progress` review (verify run timing first); 48h ETF SLA folded into the quote contract.

---

## 8. Bottom line

- **Findings:** largely corroborate ours, and the by-asset-class trio (BOND/CRYPTO/FOREX) is better engineered than the merged class files.
- **Fixes:** ~20 are mergeable after rewriting for stable IDs, percent units, our dedup key, and quarantine-instead-of-delete; 8 are veto-level.
- **Merge readiness:** **FAIL as-written**; **PASS for selective merge** of §2.9 plus §7.
- **No repo source was modified during this review.**

---

## UNVERIFIED

- `data/live_picks.db` counts/schema/172-day staleness — DB absent from this worktree.
- `audit_trail.db` "9 empty" vs "8 empty + 2 non-empty" — peer documents disagree; not queried.
- TP_HIT 92.4% / SL_HIT 4.5% — requires MySQL `at_pick_outcomes`; `investigate_tp_sl_bug.py` exists and is read-only but was not executed.
- "1,864 duplicate groups in CRYPTO 90d raw", "22,947 ghost rows", "1,273/4,820 TIME_EXIT" — DB-derived, not reproducible here.
- `_CANONICAL` at `:6128` (D1) — no such symbol at that line; may refer to an older revision.
- `equity_strategies.py:594` sector_rotation (D2) — no such function in the file at HEAD.
- Alpha-engine `cancel-in-progress` causal claim ("kills 45–60 min runs") — line verified, mechanism not.
- Whether `live_picks` has an `asset_class` column (EQ-7) or not (ET-7) — peer files contradict each other; DB not present.
- BOND migration applied on live MySQL — not queried.
- Post-fix values (post-normalization WR/PF, post-dedup counts) — not predicted.
