# Folder Review — ML-AUDIT childlike-airport (READ-ONLY)

Reviewed: `updates/2026-11-14-ML-AUDIT-childlike-airport.md` (audit summary) + `updates/2026-11-14-ML-AUDIT-childlike-airport/proposed_fixes/{overall,crypto,stocks,bonds,etfs,forex,mutual_funds}/FIX_PROPOSED.md`.

## 1. Inventory (complete)

Top-level audit summary: `updates/2026-11-14-ML-AUDIT-childlike-airport.md` (165 lines; NOT inside `proposed_fixes/`). 7 fix docs, one per asset class + `overall`. No other files in the folder.

## 2. Headline ML/DB findings (from audit summary)

- ML sound: `ml_ranker_fixed.py` (chronological 80/20, ROC-AUC, isotonic calibration, leakage guards); `ml_gatekeeper/gatekeeper.py` (trained on 3,500+ real closed picks, documents leakage features, `ML_GATE_DROP_LEAKAGE` mask). No ML-layer defects.
- DB broken (root cause, infra not math): `data/live_picks.db` 129 active picks (69 ACTIVE + 60 OPEN), 128 stale ~172d (entry_time/last_checked = 2026-05-24/25). PnL: 8 sign contradictions, 15 calc mismatches vs `(cp-ep)/ep`. `asset_class` missing for 6 DB rows; `dashboard/live_picks.json` 17 active all `UNK`. `pick_history` 136 rows all `REGISTERED` (no TP/SL/exit). `data/audit_trail.db` mostly empty. `consensus_active_picks.json` fresh but 0 picks. No mutual funds anywhere. Divergent stores confirmed: SQLite / MySQL (`alpha_engine/audit_sync.py`, `mysql_trading_sync.py`) / JSON feeds.

## 3. SAFE vs DESTRUCTIVE per fix doc

**SAFE (code-only, additive, read-only refs):**
- mutual_funds §3.1/§3.2/§3.5 — additive `asset_class.py` frozenset/maps, `ASSET_CLASS_MAP` +7, dashboard tile lists. No DB mutation, no re-map of existing classes.
- etfs §3.2 — add `KWEB`,`VLUE` to `ETF_SYMBOLS` (code edit). etfs §3.4 stats aggregation (INSERT only, non-destructive).
- overall §3.7 (dbpasses: nothing) — no-op.

**DESTRUCTIVE (mutate DB/JSON/status — flag before running):**
- **crypto §3.1** — blanket `UPDATE live_picks SET unrealized_pnl_pct=…, pnl_pct=…, last_checked=<now> WHERE asset_class='CRYPTO' AND status='ACTIVE'` — rewrites PnL + timestamp for ALL 101 crypto active rows. §3.3 "emit EXIT_STALE / close / mark EXPIRED" flips status. §3.4 dedupe re-aggregates class labels.
- **overall §3.1–§3.6** — recompute PnL for all 129 rows, refresh `current_price`/`last_checked`, backfill `asset_class`, emit resolution events, populate `audit_trail.db` tables. All write to `live_picks.db`/`audit_trail.db`.
- **stocks §3.3** — force-close aged picks: flips `ACTIVE -> CLOSED` at last-known price (STOCKS closed count 1 → ~19). §3.1 refresh UPDATE.
- **bonds §3.1** — upsert `active_picks_bond.json` → `live_picks.db` (INSERT/REPLACE). §3.3 "insert closed-pick row; **Move row from active to closed**" (row move = delete+insert). §3.2 refresh UPDATE.
- **etfs §3.1** — `INSERT OR REPLACE` keyed by (id,system) into `live_picks` table (REPLACE is a destructive upsert). §3.3 refresh + resolver writes.
- **forex §3.1** — `UPDATE … SET status='CLOSED'/'EXPIRED'` on stale rows; §3.2 "Remove resolved picks from `.picks.active`"; §3.4 case-normalize `asset_class` UPDATE.
- **mutual_funds §3.3** — NEW `mutual_fund_scanner.py` stub that EMITS `active_picks_mutual_fund.json` with placeholder/empty signals and supports `--merge` into `active_picks.json`. Risk: a placeholder-emitting scanner merged into the live feed can clobber or pollute `active_picks.json`. Do not wire into production merge path until real fund data exists.

## 4. Cross-doc contradictions (would break the proposed SQL)

- **Schema mismatch:** audit summary line 37-38 states `asset_class`, `pnl_pct`, `last_checked` live **inside `metadata` JSON**, not top-level columns. But crypto §3.1 (`WHERE asset_class='CRYPTO'`), bonds (verification `WHERE asset_class='BOND'`), forex §3.1 (`WHERE asset_class ILIKE 'forex'`), stocks §4 (`GROUP BY asset_class`) all treat `asset_class` as a top-level column. etfs §1 correctly notes "no `asset_class` column". Net: most per-class SQL would no-op or fail against the real schema.
- **Table/DB name drift:** bonds/forex/stocks reference `picks`/`closed_picks` tables and a separate `closed_picks.db`; audit summary names `live_picks`/`pick_history` tables in `data/live_picks.db`. Paths also drift (stocks §5 uses repo-root `live_picks.db`; overall/crypto use `data/live_picks.db`).
- **internal inconsistency in audit:** §2 says audit_trail.db has "11 tables"; §6 row 7 says "9 tables × 0 rows"; §2 actually lists 8 zero-row tables + `bt_backtest_runs`(20) + `meta`(1).

## 5. Numbers correcting / refining the known list

- **WUSDT & HBARUSDT "correct" `pnl_pct` are themselves wrong** (audit §3.2): WUSDT entry 0.01248 → current 0.01254 ⇒ expected **+0.0048**, audit lists `pnl_pct=+0.9615` (~200× off). HBARUSDT 0.08923→0.08899 ⇒ expected **-0.0027**, audit lists `-0.269` (~100× off). These two rows contaminate the "correct" column; sign contradiction is real but the "correct" value is a magnitude error.
- **audit_trail.db not fully empty:** `bt_backtest_runs=20`, `meta=1` are non-empty; "empty" applies to 8 (not cleanly 9) tables.
- Known "128/129 stale" confirmed as 129 active (69 ACTIVE + 60 OPEN), 128 stale. "8 sign / 15 mismatch" confirmed verbatim. "no mutual fund coverage" confirmed (zero active + zero closed + zero strategies).
- §3.2 table lists only 6 example symbols while text claims "8 picks" (and §3.3 "15 picks" = 6 + 9) — examples are a subset, not a miscount, but the 2 wrong rows sit inside those 6.

## Bottom line

Audit's ML-sound / data-broken conclusion is correct and reproducible. The per-class fix docs are directionally right but **not implementation-ready**: several SQL statements target a nonexistent top-level `asset_class` column and wrong table names/paths. Destructive actions (crypto §3.1 blanket UPDATE; any `INSERT OR REPLACE`/row-move/status-flip; mutual_funds placeholder scanner merge) must be reviewed and guarded against `entry_price=0`, `current_price NULL`, and stale-feed clobbering before execution.
