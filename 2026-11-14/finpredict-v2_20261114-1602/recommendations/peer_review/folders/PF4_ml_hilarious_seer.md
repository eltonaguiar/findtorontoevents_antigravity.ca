# PF4 — Peer review: ML audit (childlike-airport) + hilarious-seer

**Reviewer:** PF4
**Review clock:** 2026-11-14T17:55Z
**Scope:** the ML peer folder (`updates/2026-11-14-ML-AUDIT-childlike-airport.md` + 7 `proposed_fixes/*/FIX_PROPOSED.md`) and the hilarious-seer peer (`updates/2026-11-14-hilarious-seer-audit-summary.md` + 3 `audit_quickwins/**/quickwins.md`), reviewed against our archive (`2026-11-14/finpredict-v2_20261114-1602/`).
**Rule:** no repo source modified. All DB reads were opened read-only (`mode=ro&immutable=1`).

---

## VERDICT: **FAIL — not merge-ready as written** (findings are sound; fix blocks are not)

The **diagnostic findings** in both peer folders are largely reproducible and should be merged. The **proposed fix mechanics** are not safe to merge as written: they contain a mass `UPDATE` with a long-only formula, several "close at last known price" realisations that fabricate PnL, a mutual-fund taxonomy change that directly contradicts our recommendation, and two purge/archive instructions that delete rows. Merge the findings; **veto the fix blocks listed in §4** before hand-off.

- FAIL = do not copy either peer's `FIX_PROPOSED.md` / quickwins into the master plan verbatim.
- PASS (conditional) after §4 vetoes + §3 corrections = the findings and the corrected mechanics can merge into the per-class plans.

---

## 1. Inventory

### ML peer (childlike-airport)

| Path | mtime (UTC) | Size | Description |
|---|---|---|---|
| `updates/2026-11-14-ML-AUDIT-childlike-airport.md` | 2026-11-14 16:07 | 10,218 B | Main read-only audit: SQLite `live_picks.db` 172-day staleness, PnL sign/calc bugs, empty `audit_trail.db`, no mutual funds, ML-algorithm review. |
| `.../proposed_fixes/overall/FIX_PROPOSED.md` | 16:16 | 16,225 B | Cross-cutting PnL/staleness/asset_class/lifecycle/audit_trail/consensus plan (201 lines). |
| `.../proposed_fixes/crypto/FIX_PROPOSED.md` | 16:16 | 6,003 B | Crypto recompute SQL, price refresh, stale-close, case dedupe (98 lines). |
| `.../proposed_fixes/stocks/FIX_PROPOSED.md` | 16:15 | 7,175 B | EQUITY backfill, 5 stale stock refresh, age-out, scanner re-run (81 lines). |
| `.../proposed_fixes/bonds/FIX_PROPOSED.md` | 16:15 | 8,417 B | Bond feed→DB sync, stale refresh, exit emission, stats (138 lines). |
| `.../proposed_fixes/etfs/FIX_PROPOSED.md` | 16:17 | 7,848 B | ETF feed→DB sync, `ETF_SYMBOLS` additions (KWEB/VLUE), resolver inclusion (90 lines). |
| `.../proposed_fixes/forex/FIX_PROPOSED.md` | 16:16 | 6,337 B | 4 stale FX refresh, exit events, scanner re-run, FOREX_CODES backfill (71 lines). |
| `.../proposed_fixes/mutual_funds/FIX_PROPOSED.md` | 16:16 | 8,753 B | Full MUTUAL_FUND build: symbol set, `ASSET_CLASS_MAP:7`, scanner stub, dashboard tile (121 lines). |

### hilarious-seer peer

| Path | mtime (UTC) | Size | Description |
|---|---|---|---|
| `.kilo/worktrees/hilarious-seer/updates/2026-11-14-hilarious-seer-audit-summary.md` | 16:06 | 3,703 B | 41-line summary: model-404 fix (out of scope), per-class ML review, DB/PnL audit, 7 proposed fixes, FAIL verdict. |
| `.../audit_quickwins/2026-11-14-hilarious-seer/overall/quickwins.md` | 17:52 | 865 B | 5-line merged v3/v4 quick wins: 0/9 money-ready, P0 merges, DB/freshness. |
| `.../audit_quickwins/2026-11-14-hilarious-seer/crypto/quickwins.md` | 17:52 | 362 B | 2-line crypto: 3 stale SHORTs, PF inflation 5×, prune/resolver/live sync. |
| `.../audit_quickwins/2026-11-14-hilarious-seer/equity_others/quickwins.md` | 17:52 | 407 B | 2-line equity/ETF/bond/forex: 757 picks −5.22%, frozen FX, validator/resolver merges. |
| `.../audit_quickwins/2026-11-14-hilarious-seer/db_fixes/` | — | empty | No quickwins file. |
| `.kilo/worktrees/hilarious-seer/review_picks_audit/*.md` | 16:04 | 21K/5K/11K/22K | **Adjacent research only** (domain/scam/evaluation-framework reports); not evidence for the pick-DB audit. Excluded. |

**`forreviews*/**` produced today:** none under `hilarious-seer` (verified with `find`). `forreviews/` exists only in sibling worktrees `finpredict` and `finpredict-v3`, which are outside PF4's assigned peer scope.
**Branch/commit state:** hilarious-seer is on branch `hilarious-seer` @ `1d9354ab9e2` (2026-11-13); `audit_quickwins/` and the summary are **untracked** (`git status` → `??`). The ML peer has no archive folder/branch convention applied.

---

## 2. Findings reconciliation

Numbers below were re-derived read-only from `/home/eaguiar2015/findtorontoevents_antigravity.ca/data/{live_picks,audit_trail}.db` at 17:5xZ and from the worktree feeds.

| ID | Peer finding | Peer claim | PF4 re-derivation | Disposition |
|---|---|---|---|---|
| M1 | `live_picks.db` all stale | 128/129 active ~172 d; 69 ACTIVE + 60 OPEN | **VERIFIED**: 129 rows; 69 ACTIVE + 60 OPEN; `MIN/MAX(last_updated)` = `2026-05-25T20:50:25` both → 172.9 d | **ADOPT** |
| M2 | PnL sign contradiction | 8 picks, `unrealized_pnl_pct` opposite `pnl_pct` | **VERIFIED, count drift**: exact opposite-sign pairs = **9** (NEAR, ATOM, ZEC, INJ, ETC, W, HBAR, ALGO, CHZ). `pnl_pct` missing in metadata on 100/129 rows | **ADOPT (fix), correct 8→9** |
| M3 | PnL calc mismatch | 15 rows ≠ `(cp−ep)/ep` | **VERIFIED, count drift**: **18** rows differ by >0.01 (metadata `pnl_pct` missing on 100 rows limits the test to 29) | **ADOPT (fix), correct 15→18** |
| M4 | Missing `asset_class` | 6 DB rows + 17 dashboard `UNK` | **PARTIAL**: DB metadata = 5 `UNK` **plus 1 lowercase `crypto`**; `dashboard/live_picks.json` = 17 rows but the `asset_class` key is **absent**, not literal `'UNK'` | **MERGE with correction** |
| M5 | No mutual funds | 0 active / 0 closed | **VERIFIED**: no MF in `live_picks.db`, `asset_class.py`, `ASSET_CLASS_MAP`, or feeds | **ADOPT finding; REJECT build** |
| M6 | `pick_history` no exits | 136 rows all `REGISTERED` | **VERIFIED**: `SELECT event,COUNT(*)` → `REGISTERED 136` | **ADOPT** |
| M7 | `audit_trail.db` empty | 9 audit tables × 0 rows | **VERIFIED**: all 0 except `bt_backtest_runs` 20, `meta` 1 (`aggregation_runs` also 0) | **ADOPT** |
| M8 | `consensus_active_picks.json` empty | 0 picks | **VERIFIED**: 0 picks, `generated_at 2026-11-12T19:40:59Z` | **ADOPT/MERGE** |
| M9 | Feed freshness table | bond 7 picks, ETF ~20, stocksunify2 14, `active_picks.json` 0 | **PARTIAL drift**: bond = **6** picks (LQD/MUB/SHY/TLT), ETF = **16** (10 unique symbols), stocksunify2 = **13** active, `active_picks.json` 0 | **MERGE with corrected counts** |
| M10 | ML algorithms sound | `ml_ranker_fixed.py`, `gatekeeper.py` sound; leakage mask documented | **PLAUSIBLE, not re-read line-by-line by PF4**; `ASSET_CLASS_MAP` and leakage docs verified; treat algorithm-soundness as peer claim | **ADOPT as context (no change)** |
| M11 | `ab_router` import masking | silent A/B disable at `gatekeeper.py:25-32`, print at `:30` | **VERIFIED** exact block | **ADOPT (structured warning)** |
| M12 | `asset_class.py` canonical source | frozensets lines 22–62; helpers 130/191/263/269 | **VERIFIED** exact | **ADOPT** |
| H1 | Regime layer nearly empty | 21 `closed_with_regime` vs 8,538 without; `regime_flip_detector` underused | **DIRECTION VERIFIED**: `raw/d_regime_report.json` last checked `2026-06-05` (162 d dead); `d_hmm_regime.json` 404; `page_audit.html` exposes the regime coverage fields. Exact 21/8,538 not re-derived (matches saved project memory) | **MERGE (corroboration), exact counts UNVERIFIED** |
| H2 | Stale DB/files | `hyro_pick_performance` 157 h, `pick_funnel_snapshot` 404, `active_raw` crypto median 89 d / oldest 267 d | **ALREADY COVERED**: our MASTER §3 has 157.9 h / 404 / 88.7 d; no new evidence needed | **ALREADY_COVERED** |
| H3 | Zombie rows | hundreds EXPIRED BTCUSDT/XRPUSDT pnl=0, never resolved | **ALREADY COVERED**: MASTER §2/§3 (3,377 EXPIRED; 22,947 ghosts) | **ALREADY_COVERED** |
| H4 | PnL not resolved / `current_price=None` / age mismatch | TP/SL unresolved, `current_price=None` in zombies, age mismatch `.picks.active` vs `active_raw` | **PARTIAL**: true in dashboard feeds (MASTER); **false for `live_picks.db`** — all 129 rows have non-null `current_price` (incl. BOND/FOREX) | **MERGE with scope correction** |
| H5 | Multiple testing + survivorship | 361 families + mutations; 21 Bonferroni survivors = single-source artifact | **ALREADY COVERED**: MASTER §5 quantifies 658 scored, 32.9 expected FP, 21 single-source cluster | **ALREADY_COVERED** |
| H6 | `dbpasses.txt` contains live keys, no exposure | reviewed masked; several dead providers | **PARTIAL CONFLICT**: ML peer says "no `dbpasses.txt` exists"; project memory says it exists **outside the repo** at `/home/eaguiar2015/dbpasses.txt`. Both agree no repo exposure. Do not read it | **ALREADY_COVERED + scope correction** |
| H7 | Model-config 402 fix | roster re-rank / remove dead providers | **OUT OF SCOPE**: different worktree/config; not a finpredict pick-audit fix. Conflicts with the existing opt-in free-tier design if applied globally | **REJECT for this merge** |
| H8 | Verdict FAIL (not demonstrably profitable) | regime FAIL | **AGREE**: ours is FAIL too (0/9 money-ready, policy-clean PF 0.27) | **ALREADY_COVERED** |

---

## 3. ADOPT / MERGE / REJECT / ALREADY_COVERED

| # | Peer recommendation (source) | Class | Target in our plan |
|---|---|---|---|
| A1 | Truth-layer facts: 172-d `live_picks.db`, 136 REGISTERED-only history, empty `audit_trail.db` (ML `overall:18-27,93-102`) | **ADOPT** | `MASTER_AUDIT.md` §3 (already cited); keep the verified re-derivation |
| A2 | Direction-aware single PnL function; both `unrealized_pnl_pct` and `pnl_pct` derive from it (ML `overall:50-53`) | **ADOPT (mechanism only)** | `patch_plan/P0_QUICK_WINS.md` PnL contract; **not** the raw SQL |
| A3 | `asset_class` backfill via `alpha_engine.asset_class.py` (ML `overall:37,74-77`; stocks `:32-37`) | **ADOPT** | `equity_etf.md` P0-6 / `crypto_commodity.md`; **exclude** the MF clause |
| A4 | Add KWEB + VLUE to `ETF_SYMBOLS` (ML `etfs:31,47-52`) | **ADOPT** | `equity_etf.md` P1-5/P0-6 |
| A5 | ETF feed freshness guard (reject feed >48 h) + sync 16 ETF picks (ML `etfs:33,40-45`) | **ADOPT** | `equity_etf.md`; add to quote-provenance gate |
| A6 | Explicit `ab_router` warning + `ML_GATE_DROP_LEAKAGE` handling (ML `overall:38,139`) | **ADOPT** | `overall/CI_GATES.md` ML health |
| A7 | Staleness guard as a CI gate via `tools/db_freshness_check.py` (ML `overall:65,154-155`) | **MERGE** | `overall/CI_GATES.md` (dedupe with hilarious H-freshness) |
| A8 | Emit CLOSED/EXIT/TP/SL into `pick_history` via `audit_trail/universal_pick_resolver.py` (ML `overall:86-91`) | **MERGE** | `patch_plan/P1_STRUCTURAL.md` lifecycle |
| A9 | Populate `audit_trail.db` tables from scan/resolver outputs (ML `overall:97-102`) | **MERGE (P1)** | `overall/DATA_CONTRACT.md` |
| A10 | Investigate 0-pick consensus merger; don't fabricate (ML `overall:108-113`) | **MERGE** | `overall/DATA_CONTRACT.md` |
| A11 | Bond feed→DB sync, but count is **6** not 7 (ML `bonds:45-61`) | **MERGE with correction** | `bond_mutual_funds.md` P1-1 (single emitter) |
| A12 | Forex scanner re-run + `FOREX_CODES` backfill (ML `forex:36-44`) | **MERGE (guarded)** | `forex_futures.md` P1-1/P1-2 |
| A13 | Regime-layer corroboration + regime enforcement in new picks (hilarious `summary:11,15,31`) | **MERGE (annotation, not a hard block)** | `crypto_commodity.md` P1-7; regime must not become a gate that suppresses all picks while `regime_report` is dead |
| A14 | Stricter multiple-testing correction / fewer families (hilarious `summary:33`) | **ADOPT** | `MASTER_AUDIT.md` §5; `patch_plan/P1_STRUCTURAL.md` |
| A15 | Freshness guard on all JSON payloads (hilarious `summary:32`; quickwins overall `:4`) | **ALREADY_COVERED** | `overall/CI_GATES.md`, `db-freshness-guardian` |
| A16 | Zombie/EXPIRED cleanup, dedup, SQLite/MySQL/JSON harmonization (hilarious `summary:30`; quickwins overall `:3-4`; crypto `:2`) | **MERGE as quarantine only** | `crypto_commodity.md` P0-4/P0-7, `bond_mutual_funds.md` QW-5 |
| R1 | Full MUTUAL_FUND build: `MUTUAL_FUND_SYMBOLS`, `ASSET_CLASS_MAP["MUTUAL_FUND"]=7`, scanner stub, `_PER_ASSET_CLASSES`/`_AC_TF_GRID_ASSET_CLASSES` tile (ML `mutual_funds:24-34,49-73`; `overall:76`) | **REJECT** | conflicts with `bond_mutual_funds.md:446-462` + `QUICK_WINS.md:62` (see §5) |
| R2 | Crypto `UPDATE live_picks SET …` mass rewrite (ML `crypto:42-51`) | **REJECT (veto)** | §4 D1 |
| R3 | "Close at last known price" / force-close stale picks (ML `crypto:58-60`, `stocks:41-45`, `bonds:76-77`, `forex:28,34`) | **REJECT (veto)** | §4 D2 |
| R4 | "Purge" zombie rows / archive old picks (hilarious `summary:30,36`) | **REJECT (veto as deletion)** | §4 D3; keep quarantine |
| R5 | Invert the ML confidence gate (hilarious quickwins overall `:2`, "inverted ML conf") | **REJECT (veto)** | §4 D4 |
| R6 | Hilarious model-roster / 402 config changes (`summary:4-8,35`) | **REJECT for this merge** | out of scope; config belongs to another worktree |
| R7 | "Remove resolved picks from `.picks.active`" as a direct status rewrite (ML `forex:34`) | **REJECT as written** | use resolver events, not panel deletion |
| R8 | Crypto dedupe by normalizing `CRYPTO`/`crypto` (ML `crypto:37,62-64`) | **MERGE** | preserve `class_raw` + `class_mismatch` per our contract (`REVIEW_SYNTHESIS.md:39`) |

---

## 4. Destructive-fix veto table

| # | Destructive pattern | Exact location | Veto reason |
|---|---|---|---|
| D1 | **Mass UPDATE** (long-only formula applied to every crypto row, `last_checked = <now>` placeholder) | `updates/2026-11-14-ML-AUDIT-childlike-airport/proposed_fixes/crypto/FIX_PROPOSED.md:42-51` | `SET unrealized_pnl_pct = (current_price - entry_price)/entry_price` is **wrong for SHORTs**; the audit itself documents sign-flipped shorts. A blind mass UPDATE of 101 rows also overwrites `pnl_pct` and cannot be rolled back. Replace with a versioned migration + direction-aware formula + per-row assertion; back up the DB first. |
| D2 | **Fabricated realization / status rewrite** ("close at last known price", `TIME_EXIT`/`STALE_AGEOUT`) | `crypto/FIX_PROPOSED.md:58-60`; `stocks/FIX_PROPOSED.md:41-45`; `bonds/FIX_PROPOSED.md:76-77`; `forex/FIX_PROPOSED.md:28,34` | Closing a 172-day-old pick at a stale/entry price manufactures a realised PnL that never traded. That is exactly the "frozen price = false 0%" artifact we are auditing. Quarantine as `STALE`/`EXPIRED` with `pnl=null`; only realise on a fresh timestamped quote. |
| D3 | **DELETE / purge** ("purge script", "archive old picks >30d") | `.kilo/worktrees/hilarious-seer/updates/2026-11-14-hilarious-seer-audit-summary.md:30,36` | Deletion destroys the evidence needed for survivorship/bias accounting (63% unresolved) and is irreversible. Our contract is quarantine-in-view, keep rows (`REVIEW_SYNTHESIS.md:44`). No `DELETE`/`git clean`. |
| D4 | **Invert the ML gate** ("inverted ML conf") | `.kilo/worktrees/hilarious-seer/audit_quickwins/2026-11-14-hilarious-seer/overall/quickwins.md:2` (claim only; **no ML-peer code line proposes it**) | The gatekeeper is a calibrated classifier trained on real closed picks; the documented defence is the leakage mask (`ML_GATE_DROP_LEAKAGE`), not sign inversion. Inverting would turn a low-confidence filter into a perverse selector and has no validation support. Already vetoed in `MASTER_AUDIT.md:432` / `REVIEW_SYNTHESIS.md:44`. |
| D5 | **MUTUAL_FUND taxonomy rewrite** (new class id, symbol set, dashboard buckets) | `mutual_funds/FIX_PROPOSED.md:31-32,50,54-62,69-73`; `overall/FIX_PROPOSED.md:76` | Creates a permanently n=0 class, re-opens the vacuous-PASS bug (QW-1), and conflicts with our de-advertise decision (§5). Additive code is not risk-free: it changes the gate's feature encoding and every per-class aggregate. |
| D6 | **Status rewrite on `.picks.active`** (remove rows directly) | `forex/FIX_PROPOSED.md:34` | Bypasses the resolver/audit trail; panel membership must be derived from status, not hand-deleted. Use resolver events + quarantine. |
| D7 | **force-push** | none proposed in either peer folder (searched `invert|force|push -f|reset --hard`) | Nothing to veto; recorded for completeness. Peer fixes must land on a clean branch, never `--force`. |

Additional smaller hazard (not a full veto): ML `overall:35` says "short: invert sign" correctly, but `copy_trader_intel/outcome_resolver.py:252` returns a **fraction** while `mercury2/scanner.py:481-483` returns **percent** (`*100`). The "canonical function" must also canonicalise the unit, or the same bug recurs. Adopt with this correction.

---

## 5. Conflict with our mutual-fund recommendation

Our position is unambiguous: **de-advertise MUTUAL FUNDS and label it `NOT_BUILT`; do not add it to the canonical taxonomy or build a live pick class** (`recommendations/per_asset_class/bond_mutual_funds.md:446-462`; `QUICK_WINS.md:62`; `REVIEW_SYNTHESIS.md:44`). Rationale: no tracked emitter/ranker, no page, no picks, and daily-NAV funds cannot support the intraday TP/SL/`current_price` contract.

The ML peer proposes the **opposite** in two places:

- `proposed_fixes/mutual_funds/FIX_PROPOSED.md:24-34` — add `MUTUAL_FUND_SYMBOLS`, `_CAT_MAP`/`_LOWER_TO_UPPER`, `ASSET_CLASS_MAP["MUTUAL_FUND"]=7`, `_PER_ASSET_CLASSES`/`_CANONICAL`/`_AC_TF_GRID_ASSET_CLASSES` tiles, and a `mutual_fund_scanner.py` stub.
- `proposed_fixes/overall/FIX_PROPOSED.md:76` — "Add a `MUTUAL_FUND` class + symbol set to `asset_class.py` … extend DB schema and picker."

**Resolution: REJECT both.** Keep the shared *finding* (zero MF coverage is real) and merge only the `NOT_BUILT` badge / de-advertise item (our QW-2). If the operator overrides, use our research-only path (`bond_mutual_funds.md:464-478`: weekly NAV ranking, no picks/TP/SL/sizing) — **not** the ML scanner stub, which would emit pick-shaped rows for an instrument with no intraday mark.

Minor internal drift found while checking the conflict: `mutual_funds/FIX_PROPOSED.md:18` cites `dashboard_generator.py:6128` for `_CANONICAL`, but the actual definitions are at `:6027` and `:6200` (and the same file cites `:6027` later at line 70). `_PER_ASSET_CLASSES` = `:6763` and `_AC_TF_GRID_ASSET_CLASSES` = `:14201` are correct.

---

## 6. Citation spot-check (>= 6 verified)

All reads in the `finpredict-v2` worktree or the main repo's read-only DBs.

| # | Citation | Result | Evidence |
|---|---|---|---|
| C1 | `live_picks.db`: 129 rows, 69 ACTIVE / 60 OPEN, last update 2026-05-25 | **VERIFIED** | SQL: count 129; status `ACTIVE 69, OPEN 60`; `MAX(last_updated)=2026-05-25T20:50:25` |
| C2 | `pick_history`: 136 rows, all `REGISTERED` | **VERIFIED** | `GROUP BY event` → `REGISTERED 136` |
| C3 | `audit_trail.db`: 9 audit tables empty; `bt_backtest_runs` 20; `meta` 1 | **VERIFIED** | table counts: `consensus_picks/feature_edge_snapshots/symbol_strategy_stats/strategy_stats/raw_picks/audit_events/filter_log/bt_backtest_trades = 0` |
| C4 | `ml_gatekeeper/gatekeeper.py:73` `ASSET_CLASS_MAP` (no MUTUAL_FUND) | **VERIFIED** | exact line; 7 classes only |
| C5 | `ml_gatekeeper/gatekeeper.py:25-32` ab_router masking, print at `:30` | **VERIFIED** | exact block |
| C6 | `alpha_engine/asset_class.py:22-62` frozensets; `:130/:191/:263/:269` helpers | **VERIFIED** | `FOREX_CODES:22`, `BOND_SYMBOLS:28`, `ETF_SYMBOLS:37`, `EQUITY_SYMBOLS:55`, `COMMODITY_SYMBOLS:62`; defs at 130/191/263/269 |
| C7 | `audit_trail/quality_gates.py:1724` `BLOCKED_ASSET_CLASSES` | **VERIFIED** | `{"FOREX","COMMODITY","FUTURES","BOND"}` |
| C8 | `alpha_engine/non_crypto_policy.py:698` / `:1026` | **VERIFIED** | `evaluate_non_crypto_candidate` at 698, allowlist `_FOREX_ALLOWED` at 724-726; `passes_non_crypto_policy` at 1026 |
| C9 | `sync_summary_picks_json.py:63-65,161` wins/losses/resolved division | **VERIFIED** | actual path `tools/sync_summary_picks_json.py` |
| C10 | `mercury2/scanner.py:127-128` and `:481-485` writes PnL/`last_checked` | **VERIFIED** | exact lines |
| C11 | `copy_trader_intel/outcome_resolver.py:252` | **VERIFIED**, but **unit drift** | returns `round((current-entry)/entry, 4)` (fraction) vs scanner `*100` (percent) |
| C12 | `forward_trade_executor.py:100-102` long/short formula | **VERIFIED** | exact lines |
| C13 | `audit_trail/dashboard_generator.py:6763` / `:14201` | **VERIFIED** | `_PER_ASSET_CLASSES` tuple; `_AC_TF_GRID_ASSET_CLASSES` list |
| C14 | `ETF_SYMBOLS` missing KWEB/VLUE | **VERIFIED** | grep `NOT PRESENT`; KWEB is in `active_picks_etf.json` |
| C15 | `alpha_engine/data/active_picks_etf.json` 16 picks, gen 2026-11-12T18:17:06Z | **VERIFIED** | feed count 16 (10 unique symbols) |
| C16 | `alpha_engine/data/active_picks_bond.json` 7 picks | **DRIFT** | actual `count=6`, 6 picks, 4 symbols (LQD/MUB/SHY/TLT); bond FIX repeats "7" at `:38,:61` |
| C17 | `stocksunify2_active_picks.json` 14 picks | **DRIFT** | actual `active_picks` = **13**, `generated_at 2026-08-26` (79 d) |
| C18 | `dashboard/live_picks.json` 17 `UNK` | **DRIFT** | 17 rows, but no `asset_class` key at all (absent, not `'UNK'`) |
| C19 | `alpha_engine/universal_pick_resolver.py` (forex `:18,32,63`) | **DRIFT** | file does not exist; actual path `audit_trail/universal_pick_resolver.py` |
| C20 | `alpha_engine/fetch_stock_prices.py` / `tools/fetch_stock_prices.py` (stocks `:19,28,69`; bonds `:68`) | **DRIFT** | neither exists; actual `audit_trail/fetch_stock_prices.py` |
| C21 | BOND/FOREX rows `current_price=None` (bonds `:65`, forex `:9`) | **DRIFT for `live_picks.db`** | BOND IEF 93.88 / HYG 79.91; FOREX USDJPY=EURJPY=NZDUSD=entry, CADJPY differs — all non-null. True instead for dashboard zombies |
| C22 | Regime 21/8,538 | **PARTIAL/UNVERIFIED** | `d_regime_report.json` dead since `2026-06-05` (162 d), `d_hmm_regime.json` 404; exact counts not re-derived |
| C23 | `254d resolver`, `26d dashboard` (hilarious overall `:2`) | **UNVERIFIED** | No resolver-status artifact found; the "26 d dashboard" is the known stale **repo** copy (`MASTER_AUDIT`/v4 artifact), not the live 1.63 h payload |

**Drift summary:** count drift is material only for bond (7→6), stocksunify2 (14→13), PnL sign (8→9) and mismatch (15→18); path drift is material for `universal_pick_resolver` and `fetch_stock_prices` (both `audit_trail/`). None of the drifts overturns a conclusion.

---

## 7. What to merge into our per-class plans (exact)

- **CRYPTO / COMMODITY** (`per_asset_class/crypto_commodity.md`): merge M1–M3 truth-layer facts and the **direction-aware** PnL function (A2), the `CRYPTO`/`crypto` case normalisation (R8, keep `class_raw`), and quarantine-not-delete for zombies (A16). Do **not** merge `crypto:42-51` SQL or stale-price closes.
- **EQUITY / ETF** (`per_asset_class/equity_etf.md`): merge A3 (EQUITY backfill), A4 (KWEB/VLUE), A5 (ETF freshness + 16-pick sync), and the 13-pick stocksunify2 correction. Do not merge force-close (`stocks:41-45`).
- **BOND / MF** (`per_asset_class/bond_mutual_funds.md`): merge A11 (single bond emitter; count 6), the refresh/PnL repair via fresh quotes, and exit emission via the **`audit_trail/`** resolver. **Reject** R1/D5 wholesale; keep only the `NOT_BUILT` badge.
- **FOREX / FUTURES** (`per_asset_class/forex_futures.md`): merge A12 (FOREX_CODES backfill + guarded scanner re-run), corrected paths (C19/C20), and resolver-event exits. Do not merge the `.picks.active` removal (D6).
- **Overall** (`overall/CI_GATES.md`, `DATA_CONTRACT.md`, `patch_plan/P1_STRUCTURAL.md`): merge A6–A10 (ab_router warning, freshness CI gate, lifecycle, audit_trail population, consensus investigation), A13 (regime annotation, non-blocking) and A14 (multiple-testing correction). Reject D4 and the model-roster work.

**Reject outright:** D1–D7, R1, R4, R5, R6, R7.

---

## 8. UNVERIFIED

- Exact regime counts **21 / 8,538** (direction corroborated by dead `regime_report`; exact numbers not re-derived).
- hilarious "**254d resolver**" — no resolver-status artifact reproduces it.
- hilarious "**26d dashboard**" — true only for the stale repo snapshot; live payload is 1.63 h (`MASTER_AUDIT` §3).
- ML claim that `ml_ranker_fixed.py` was read line-by-line and "sound" — PF4 verified only the gatekeeper/asset-class citations.
- hilarious "**757** equity picks / −5.22%" and "**3 stale SHORTs PF 0.37–0.92**" — not independently re-derived (our EQUITY populations are 738/759; direction agrees).
- ML "no `dbpasses.txt`" — true **in-repo**; project memory records the live-secret file **outside** the repo (never read).
- Whether any consumer reads `consensus_active_picks.json` / `stocksunify2_active_picks.json` — out of PF4 scope.
- Hidden/destructive edits in hilarious-seer: the worktree is untracked/dirty; **no source diff was applied by PF4**.

---

## 9. Top 5 merge / veto items

**Merge**
1. **M1 + M6 + M7** — SQLite truth layer (129 rows/172.9 d, 136 REGISTERED-only, all audit tables 0) is verified; carry as the authoritative addendum to `MASTER_AUDIT` §3.
2. **A2 (corrected)** — one direction-aware, unit-consistent PnL function; fix the 9 sign pairs and 18 mismatches, `pnl_pct` as the only stored source.
3. **A4/A5** — add KWEB/VLUE to `ETF_SYMBOLS`, guard ETF feed freshness, and sync the 16 ETF picks.
4. **A8/A9/A10** — resolver-written `pick_history` events + `audit_trail.db` population + consensus-root-cause, all as P1 (no fabrication).
5. **A13/A14** — merge hilarious-seer's regime-layer corroboration (annotation, not a hard gate) and the stricter multiple-testing correction.

**Veto**
1. **D1** — `crypto/FIX_PROPOSED.md:42-51` mass `UPDATE` (long-only formula, 101 rows, placeholder timestamp).
2. **D2** — close-at-stale-price in `crypto:58-60`, `stocks:41-45`, `bonds:76-77`, `forex:28,34`.
3. **R1/D5** — the entire MUTUAL_FUND build (`mutual_funds:24-34,49-73`; `overall:76`); conflicts with `bond_mutual_funds.md:446-462`.
4. **D3** — hilarious "purge script" / "archive old picks >30d" (`summary:30,36`); quarantine in view instead.
5. **D4** — invert-the-ML-gate (`hilarious quickwins overall:2`); unsupported and contradicts the calibrated gatekeeper.

---

*File: `2026-11-14/finpredict-v2_20261114-1602/recommendations/peer_review/folders/PF4_ml_hilarious_seer.md` — evidence-backed; no repo source modified.*
