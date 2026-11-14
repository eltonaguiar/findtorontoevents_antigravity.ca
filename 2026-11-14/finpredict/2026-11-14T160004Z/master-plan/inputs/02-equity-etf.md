# EQUITY + ETF — Consolidated Peer Review (5 agents)

**Consolidator:** ME (finpredict 160004Z). **Inputs:** V2 (`finpredict-v2` remediation + `sub/D_non_crypto.md`), V3-QUICK (`161500Z/QUICK_WINS`), V3-PEER (`161700Z/PEER_REVIEW`), V4 (`audits/…/finpredict-v4`), ML (`updates/…/ML-AUDIT-childlike-airport`), ME (`160004Z/quick-wins`).
**Scope:** EQUITY + ETF only. READ-ONLY; no code touched.

---

## 1. Consensus findings (≥2 peers agree)

| # | Finding | Evidence | Peers |
|---|---|---|---|
| C1 | **"0.00% PnL" is an unpriced artifact, not a live mark.** `current_price == entry_price` (bit-identical to Friday 2026-11-13 close). Audit ran Saturday; entries were never repriced. | 10/10 ETF curated entries == Yahoo 11-13 close to full float (`D:228`); ADBE 243.08 == 11-13 close (`D:120`); 17/17 non-crypto curated rows identity-priced (`D:426`). | V2, V3-QUICK, V3-PEER, ME, V4 |
| C2 | **Thin-sample headline stats are misleading.** EQUITY "75% WR / PF 8.86" is n=8 (95% CI ~[0.41,0.93]); larger policy-clean cohort n=461 → WR 43%, PF 0.70, z=-3.03 (significantly *below* 50%). ETF PF 1.84 is n=15, z=+1.81, fails 9-class Bonferroni (|z|=2.77). | V2 `E_statistical:208-212`; `D:125-131`; v1 n=8; v2 n=461. | V2, V3-QUICK, V3-PEER, ME, V4 |
| C3 | **Massive stale/zombie OPEN backlog.** EQUITY 94 OPEN / 82 >30d stale (V2) or 757 open (V4) or 5 stale ~172d (ML); ETF 30 OPEN (V2) / 1,722 open (V4). Mostly never resolved, dragging aggregate PnL. | `D:98-102`, `D:216-219`; V4 deep-dive §2/§3; ML stocks §1. | V2, V3-PEER, V4, ML |
| C4 | **Asset-class mislabeling: ETF↔EQUITY↔BOND boundary broken.** EQUITY contains SPY/QQQ/XLE/XLK (9 rows); ETF contains bond fund VCSH; `ETF_SYMBOLS` missing KWEB/VLUE (fall back to EQUITY); crypto-ETFs BITO/IBIT unsegregated. | `D:78-81`; ML-etfs §1/§3.2; V3-PEER ETF #1. | V2, V3-PEER, ML |
| C5 | **`summary_picks` win-rate denominator bug → WR >100%.** EQUITY 162.4%, ETF 232.9% (wins/losses counted over larger population than `resolved`). | `D:21`; V2 P0-4. | V2 (V3-PEER cites it) |

---

## 2. Unique per-peer findings (single proposer)

- **V2** — deepest code-level tracing. Confirmed `summary_picks` denominator at `tools/sync_summary_picks_json.py:161`; no-quote path leaves carried/entry price untouched at `dashboard_generator.py:1739-1755`; green live dot at `index.html:9139`. Two impossible AAPL entries (315.98 vs day range 355.75-360.83) → closed-ledger integrity issue. 84.99× ETF daily-vs-intrabar PF inflation. Phantom classes INDEX/MANAGED_FUTURES/STOCKS/SPORTS.
- **V3-QUICK** — "ALIVE" verdict for both classes; frames 0% as *legitimate parked state*, defect is statistical disclosure only. Re-quote-on-open hook (ETF #3).
- **V3-PEER** — cross-peer triangulation. Identifies v4 **dashboard filter inversion** (raw DB 90d WR 66.7%/PF 5.56 vs dashboard 37.4%/0.70) — sign flips on filter. Flags BITO/IBIT as BTC proxies polluting ETF stats. Notes `proposed_fixes/equity/` EMPTY (v4) and ML `proposed_fixes/etfs/` EMPTY.
- **V4** — `dashboard_data.json` 26d stale (2026-10-19) vs `picks_now_live_pnl.json` 2d fresh; EQUITY avg PnL -5.22%, ETF -0.20%; all top picks demoted WATCH/null TP-SL; `MeanReversionBB` (n=191, PF 1.76) is the only salvageable EQUITY strategy; ETF intrabar n=44 WR 2.3% = "worst class".
- **ML** — `live_picks.db` has **no `asset_class` column** (derived at query time); only 1 closed STOCKS pick vs 6,400 crypto; 5 stale active stocks ~172d. ETF feed `active_picks_etf.json` fresh (2d) but never synced into `live_picks.db`.

---

## 3. Consolidated proposed fixes (dedup)

Legend: Effort S/M/L; Risk L/M/H. "DESTRUCTIVE" = mutates/deletes history; "VETOED" = contradicted by another peer's do-not-do.

| ID | Fix | Target file:line | Effort | Risk | Proposers | Flags |
|---|---|---|---|---|---|---|
| F1 | Stamp `quote_status`/`quote_source`/`quote_at` on every active pick; `UNQUOTED` on miss; never present carried/entry price as live mark. | `audit_trail/dashboard_generator.py:1681-1688,1739-1755,1821-1822` | S | L | V2(P0-1), ME(#1), V3-QUICK(#2), V3-PEER(#3) | additive; kill switch `QUOTE_STATUS_ENABLED=0` |
| F2 | Fix `summary_picks` WR denominator → `wins/(wins+losses)`; canonical class labels; `valid_for_sizing:false`. | `tools/sync_summary_picks_json.py:18-22,63-65,161` | S | L | V2(P0-4) | diagnostic file, non-fatal in CI |
| F3 | `LAST CLOSE Fri 13 Nov` / `UNQUOTED` render; kill green live dot when market closed; hide PnL when unquoted. | `audit_dashboard/index.html:4453-4466,4719-4732,8841-8905,9134-9145` | S | L | V2(P0-2,P0-3), ME(#1,#3), V3-QUICK(#1) | display-only; `QUOTE_BADGE_V2=0` |
| F4 | n + 95% CI on every class headline; suppress/gate WR/PF when n < 30 (EQUITY) / n < 100 (class PF). | `audit_trail/dashboard_generator.py:5916,15483`; `audit_dashboard/summary.html` | S-M | L | V3-QUICK(#1,#3,#4), V2(P1-6), ME(#2) | display policy |
| F5 | Symbol-authoritative ETF/BOND routing: add KWEB/VLUE (+IBIT/BITO w/ crypto_etf tag) to `ETF_SYMBOLS`; move VCSH→BOND; drop VTI/SCHB/ITOT from BOND regex. | `alpha_engine/asset_class.py:37-53`; `audit_trail/dashboard_generator.py:3645-3680`; `audit_trail/asset_classification.py:241-243` | S | M | V2(P0-6), ML-etfs(§3.2), V3-PEER(ETF#1) | ship behind `ASSET_CLASS_SYMBOL_AUTHORITY=1` |
| F6 | Age-out/quarantine stale OPEN rows (>14-30d): `quarantined:true` + `quarantine_reason`, exclude from "open" counts; emit TIME_EXIT/STALE_AGEOUT closes for 5-757 stale EQUITY + 30-1722 ETF rows. | `audit_trail/dashboard_generator.py:9540-9617,17459-17525`; `audit_trail/universal_pick_resolver.py`; `alpha_engine/pick_revalidator.py` | S | M | V2(P0-7), V4(1.1), ML(stocks§3.3), V3-PEER(#3) | **VETOED as delete**: V2 "do not delete" + `ACTIVE_RAW_QUARANTINE=0`; V4's SQL `status='EXPIRED_FORCE'` one-shot is DESTRUCTIVE → quarantine instead |
| F7 | Publish population split `open_count` vs `curated_count` vs `frozen_at_entry_count` to end 2-vs-58-vs-94 dispute. | `audit_trail/dashboard_generator.py:15400-15455,16800-16815` | S | L | V2(P0-5) | additive only |
| F8 | Backfill `asset_class` on `live_picks.db` / `live_picks.json` / `stocksunify2_active_picks.json` via `EQUITY_SYMBOLS`; sync fresh `active_picks_etf.json` into `live_picks.db` (store class in `metadata`). | `alpha_engine/asset_class.py:55`; `alpha_engine/etf_scanner.py::_merge_into_active_picks` | M | M | ML(stocks§3.2, etfs§3.1) | note: `live_picks` table has no `asset_class` column |
| F9 | Refresh `current_price`/`unrealized_pnl` for stale stock/ETF picks via `fetch_stock_prices.py`; expand symbol universe (10/10 ETF, not 2/10). | `audit_trail/fetch_stock_prices.py:20-105`; `alpha_engine/fetch_stock_prices.py` | M | M | ML(stocks§3.1), V2(P1-4), V4(2.1), V3-PEER(#4) | rate-limit risk; fail-closed |
| F10 | Hook non-crypto into intrabar resolver + backfill strategy stats so `intrabar_gate` leaves NO_DATA. | `audit_trail/universal_pick_resolver.py`; `alpha_engine/universal_pick_resolver.py` | M | M | V4(2.1,2.2), ML(etfs§3.4) | |
| F11 | EQUITY closed-ledger integrity: reject entries outside day [low,high] as `_entry_impossible`; quarantine 2 impossible AAPL rows. | `audit_trail/universal_pick_resolver.py:693-722,888-909` | M | M-H | V2(P1-7) | do NOT retro-edit statuses |
| F12 | Investigate v4 dashboard filter inversion (90d raw 66.7%/PF 5.56 vs dashboard 37.4%/0.70). | `audit_trail/dashboard_generator.py:6948-7078` | M | M | V3-PEER(#5) | UNIQUE to v4; verify before trusting closed WR |
| F13 | Demote ETF to WATCH/position_size=0 until n≥100 (mirror EQUITY). | `alpha_engine/non_crypto_policy.py`; `alpha_engine/scanner.py` | S | L | V4(1.3) | |
| F14 | Hide empty UEPS Swing/Closed-Holds tabs. | `audit_dashboard/ueps_section_renderer.py:909` | S | L | ME(ETF#2) | |
| F15 | MeanReversionBB graduation path (n=191, PF 1.76) — fix MDD 0.9999 artifact, bootstrap vs SPY, 1% cap. | `alpha_engine/benchmark_closed_ledger.py`; `proven_edge_strategies.py` | M-L | M | V4(3.2) | |

---

## 4. Conflicts

1. **`dashboard_data.json` freshness.** V4 says 26d stale (2026-10-19); V2/D says `dashboard_payload.json` generated 2026-11-14T14:30Z (1.6h old). **Likely two different artifacts** — V4's `dashboard_data.json` vs V2's `dashboard_payload.json`. Must resolve which file the /audit HTML actually consumes before "fixing freshness".
2. **"ALIVE/parked" (V3-QUICK) vs "FAIL/unpriced" (V2, V4).** Same underlying fact (identity pricing), opposite framing: V3 calls it a legit weekend snapshot needing a label; V2 calls it "never marked to market" needing a provenance contract. Reconciliation: it's a *parked* snapshot that is currently *presented as live* — F1/F3 satisfy both.
3. **EQUITY sign of edge.** v1 headline n=8 positive (+238.4 sum); v2 policy-clean n=461 PF 0.70 (losing, z=-3.03); v4 intrabar PF 0.934; recent_closed n=738 PF 1.154. Peer consensus: **roughly breakeven/losing; n=8 is a survivor artifact** — use n=461 policy-clean as canonical significance.
4. **ETF n=44 intrabar WR 2.3% (V4) vs n=15 policy-clean PF 1.84 (V2).** Same class, opposite directions; both tiny. Both fail significance → INSUFFICIENT_DATA.
5. **Purge vs quarantine.** V4 wants force-close/archive (SQL UPDATE); V2 mandates quarantine-not-delete. Adopt F6 quarantine form.
6. **Live EQUITY count.** ML `live_picks.db` = 5 active; V4 `picks_now_live_pnl.json` = 757 open; V2 raw = 94 OPEN. Different inventories/databases, not a bug per se.

---

## 5. UNVERIFIED

- **Headline EQUITY n=8 cohort producer** not located in repo (V2): exists only in live payload; code paths traced produce n=738/759/461. Do not "fix" n=8 until producer identified.
- **IBIT/BITO live row count** in ETF (V2): classification gap verified; live presence not in archived dump.
- **`stock_prices.json` as-of semantics**: only file-level `updated_at`; whether each value is close vs intraday unknown (V2).
- **Weekend/holiday workflow ordering**: whether `fetch_stock_prices.py` runs weekends / cache rebuilt pre-dashboard untraced (V2).
- **Yahoo `meta.regularMarketTime` availability through CORS proxies** (allorigins/corsproxy) unverified (V2).
- **Exact source of `STOCKS` label** in `audit_surface_truth.tournament.closed_by_class` (V2).
- **~43-46% WR / PF ~0.70** larger-sample figures (V3-QUICK) come from prior-audit context; re-confirm exact source.
- **V4's `dashboard_data.json` 26d-stale claim** — did not independently verify file mtime; conflicts with V2 payload freshness (see §4.1).
- **Frozen/stale counts** (82 stale / 94 OPEN / 40 frozen EQUITY; 30 OPEN / 15 frozen ETF) copied from V2 sub-report, not recomputed from a fresh live payload.

---

## 6. Recommended P0 order (top 5)

| Rank | Fix | Why first | Anchor |
|---|---|---|---|
| P0-1 | **F1 Quote provenance stamp** (`quote_status`/`quote_source`/`quote_at`) | Removes the false "flat market" reading that every other finding inherits; additive, reversible. | `dashboard_generator.py:1739-1755` |
| P0-2 | **F2 `summary_picks` WR denominator + canonical labels** | Eliminates arithmetically impossible WR (EQUITY 162.4%, ETF 232.9%); one-file, non-fatal-in-CI. | `tools/sync_summary_picks_json.py:161` |
| P0-3 | **F3 LAST CLOSE / UNQUOTED render + green-dot kill** | Users stop reading Friday's close as a Saturday move; pure render guard. | `audit_dashboard/index.html:9139` |
| P0-4 | **F4 n + 95% CI headline gating** | Kills the misleading "75% WR / PF 8.86" and "PF 1.84" claims without touching data. | `dashboard_generator.py:15483` |
| P0-5 | **F6 Quarantine stale zombies (non-destructive)** | Stops 85 auto-expired EQUITY rows + 1,722 ETF backlog counting as inventory/edge; no deletes. | `dashboard_generator.py:9540-9617` |
