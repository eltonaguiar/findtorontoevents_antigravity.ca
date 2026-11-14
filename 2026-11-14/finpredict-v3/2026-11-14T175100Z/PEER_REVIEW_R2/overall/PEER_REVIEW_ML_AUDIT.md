# PEER REVIEW R2 — ML-AUDIT childlike-airport (Archive B)

**Reviewer:** R2 peer-review subagent · **Mode:** READ-ONLY · **Date:** 2026-11-14 ~17:58Z
**Reviewed archive:** `updates/2026-11-14-ML-AUDIT-childlike-airport/`
**Worktree check:** `.../worktrees/childlike-airport/` (top-level + `deploy/quick_wins_phase1/` + `docs/strategy-audit-rounds/`)

---

## 1. Inventory (complete)

`proposed_fixes/` holds **7 subfolders, each with a FIX_PROPOSED.md (all present):**

| Subfolder | Lines | Focus |
|---|---|---|
| `overall/` | 201 | Cross-cutting PnL/staleness/asset_class/lifecycle/audit_trail/consensus/secrets |
| `crypto/` | 98 | 101 stale crypto active rows; sign/calc PnL SQL |
| `stocks/` | 81 | 5 stale active, UNK backfill, age-out closes, scanner re-run |
| `bonds/` | 138 | Fresh feed↔DB sync gap; 2 stale rows; 3 closed; exit emission |
| `mutual_funds/` | 121 | ZERO coverage; propose new class, mapping, **stub scanner/strategies** |
| `forex/` | 71 | 4 stale active; case normalization; exit events; strategy_stats |
| `etfs/` | 90 | Fresh feed 16 picks; no `asset_class` column; KWEB/VLUE mislabel |

Also present at archive top: `2026-11-14-ML-AUDIT-childlike-airport.md` (the source audit summary; not inside `proposed_fixes/`). **NOT FOUND:** `proposed_fixes/{futures,commodity}/` subfolders — the two classes have no ML fix doc (consistent with other peers' "least-owned classes" note).

## 2. Key claims / numbers (quoted, attributed)

- **Staleness:** "`data/live_picks.db` has 129 active picks; 128 are ~172 days stale … all marked ACTIVE/OPEN" (overall §1). Crypto: "101 active crypto picks … all 101 stale ~172 days" (crypto §1).
- **PnL corruption:** "8 picks have `unrealized_pnl_pct` with the sign flipped vs `pnl_pct`; 15 picks mismatch the canonical formula `(current_price - entry_price) / entry_price`" (overall §1). Example: "NEARUSDT … `unrealized_pnl_pct=-0.129` (wrong sign) vs `pnl_pct=+0.128`" (crypto §1).
- **asset_class:** "missing for 6 DB rows; `dashboard/live_picks.json` has 17 active picks all `asset_class='UNK'`" (overall §1). ETF: "`live_picks` schema … has **no `asset_class` column** … KWEB and VLUE … default fallback `equity`" (etfs §1).
- **Lifecycle:** "`pick_history` has 136 rows, all `event='REGISTERED'` — no CLOSED/EXIT/TP/SL events" (overall §1).
- **Empty audit DB:** "`data/audit_trail.db` consensus/feature/strategy-stats tables are all 0 rows (only `bt_backtest_runs`=20, `meta`=1)" (overall §1). "`consensus_active_picks.json` is fresh (1d) but EMPTY" (overall §1).
- **ML sound:** "ML algorithms themselves are sound: `ml_ranker_fixed.py` … and `ml_gatekeeper/gatekeeper.py`" (overall §1).
- **Secrets:** "no `dbpasses.txt`; only the public keyless Pollinations info file — no secrets, nothing to fix" (overall §3.7). *(Note: this contradicts project memory that `/home/eaguiar2015/dbpasses.txt` exists outside the repo — the ML worktree simply does not contain it; scopes differ.)*
- **Bonds:** "`active_picks_bond.json` … 7 … FRESH — 2026-11-12 (~2d old) … `live_picks.db` … 2 active … STALE — ~172 days" (bonds §1). "Closed bond picks: only 3 rows across all time" (bonds §1).
- **Stocks:** "only 5 active stock picks … STALE ~172 days … Closed picks: STOCKS has only 1 closed pick vs 6,400 CRYPTO" (stocks §1).
- **Forex:** "4 active forex picks are stale … FOREX 1,097 closed picks + 120 lowercase `forex` closed picks" (forex §1).

## 3. Worktree (childlike-airport) — brief check

- **Top level:** mirror of the main repo (1370 entries incl. alpha_engine, data/, docs/, deploy/, updates/). `live_picks.db` present at root.
- **`deploy/quick_wins_phase1/`:** 3 JSON (deployment_checklist, enhanced_strategy_config, monitoring_dashboard). These are **dated 2026-03-08** (target_date) — pre-audit, unrelated to today's ML fixes; all items `pending`. Not part of this audit.
- **`docs/strategy-audit-rounds/`:** rounds 001–200 + named overlays (kronos_overlay, regime_aware_momentum, sentiment_contrarian, statistical_arbitrage_pairs) + `REVIEW_2026-05-09.md` + `COVERAGE_VALIDATION_2026-05-09.md`. Most recent round 200 (`factor_exposure_balanced`, generated 2026-05-08, performance: total_pnl 19.0, avg WR 0.55, sharpe 1.12). **No top-level index/README/summary file** — round index is implicit by directory number; content dates to May 2026 (pre-audit). Nothing here bears on the Nov 14 ML audit.

## 4. Strengths

- **ML-sound / data-broken is well-evidenced and reproducible** — concrete files, counts, and the canonical `(cp-ep)/ep` formula; verification steps are checkable.
- **Canonical PnL + freshness + asset_class backfill** via `alpha_engine/asset_class.py` as single source of truth is the right shape and consistent with the v1 master-plan P0.
- **Cross-cutting doc is the best integration point** — it correctly frames infra as gating for per-class work ("Do not start per-asset-class work until P0 is complete").

## 5. Weaknesses / gaps

- **Self-contradictory schema targets.** `overall` says `asset_class`/`pnl_pct`/`last_checked` live **inside `metadata` JSON** for `live_picks`; `etfs` §1 explicitly says there is **no `asset_class` column**. Yet `crypto` §3.1 (`WHERE asset_class='CRYPTO'`), `bonds` (`WHERE asset_class='BOND'`), `forex` §3.1 (`WHERE asset_class ILIKE 'forex'`), `stocks` §4 (`GROUP BY asset_class`) all treat it as a top-level column. Most per-class SQL would no-op or fail against the real schema. Must be reconciled **before** running.
- **Destructive / status-flipping actions** flagged: crypto §3.1 blanket UPDATE rewrites PnL+timestamp for all 101 rows; bonds §3.3 and forex §3.2 "move row from active to closed" (delete+insert) and remove from `.picks.active`; etfs uses `INSERT OR REPLACE` keyed by `(id,system)`. These need review + backup + guards against `entry_price=0`, `current_price NULL`, stale-feed clobbering.
- **Mutual-funds stub scanner (§3.3) emits placeholder/empty signals** and `--merge`s into `active_picks.json` — directly contradicts the v1 master-plan veto list ("Do NOT add MUTUAL_FUND to canonical classes before an emitter exists"; v3 explicitly vetoes placeholder emission). Adopt classification-only, defer emission.
- **Case-duplication inconsistent:** overall §3.3 lists "crypto 66 vs CRYPTO 6,400 vs crypto 1,348"; crypto §3.4 says "6,400 + 1,348"; forex lists 1,097+120. Minor, but counts should be pinned once.
- **No futures/commodity fix docs** (NOT FOUND) — gap for two classes.
- **`dbpasses` "nothing to fix"** is scope-limited to the worktree; the live secrets file lives outside the repo (per project memory). Do not treat as a repo-wide security clean bill.

## 6. Recommended merge / adjust for the master plan

1. **Adopt ML as the DB-divergence/reconciliation backbone** (live_picks.db staleness, empty audit_trail.db, empty consensus, PnL sign/calc) — map to master-plan Phase-1 "reconcile 3 data stores" and P0 quote/PnL contract.
2. **Resolve the asset_class schema question first** (metadata vs top-level column) and rewrite the per-class SQL accordingly; otherwise gate the fixes behind the schema decision.
3. **Route all ML P0 through quarantine-not-delete** (emit EXIT_STALE, flag STALE) consistent with the master-plan veto; never blanket-rewrite PnL/status without dry-run + backup.
4. **Mutual funds:** keep only the additive classification + dashboard-tile items (asset_class.py frozenset/maps, `ASSET_CLASS_MAP` +7); **reject** the stub-scanner `--merge` until real fund data exists.
5. **Add the 8 sign + 15 calc fixes** as concrete test rows in the canonical PnL test (`|stored - expected| < 1e-6`).
6. **Close the futures/commodity gap** by noting these classes have no ML fix doc; rely on v2/v4 class docs for them.

## 7. Verdict

Sound diagnosis, directionally correct fixes, but **not implementation-ready**: schema targets contradict across docs, several actions are destructive, and the mutual-fund stub must be vetoed. Merge with the adjustments above.
