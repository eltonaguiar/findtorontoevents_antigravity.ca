# Folder Review Synthesis — 2026-11-14 (second pass)

**Reviewers:** PF1 (finpredict v1), PF2 (finpredict-v3, all 5 dated sets), PF3 (finpredict-v4 + audits), PF4 (ML + hilarious-seer), PF5 (recent-file sweep + merge plan).
**Clock:** 2026-11-14T17:55Z.
**Scope:** every peer audit folder modified today, plus GA1–GA4 Actions deep dive.

## Verdict

**Conditional PASS for merge.** Every peer group adds real evidence or fixes; none overturns the central FAIL verdict. Several groups ship destructive SQL or dangerous policy reversals and must be merged selectively. All findings below are recorded in `folders/PF1..PF5_*.md`.

## Coverage

| Group | Folder | Reviewer | Merge-readiness |
|---|---|---|---|
| v1 `finpredict` | `quick-wins/`, `peer-review/`, `master-plan/inputs/`, `updates/` | PF1 | PASS conditional (19/25 citations exact, 6 drifts, 10 vetoes) |
| v3 `finpredict-v3` | 1555 hygiene, 1615 QW, 1617 PR, 1745 ML_VALIDATION, 1751 PEER_REVIEW_R2 | PF2 | PASS conditional; 14 hygiene + 4 ML + 4 leakage tests pass |
| v4 `finpredict-v4` | 6 reports, 4 evidence JSON, `proposed_fixes/*`, `peer_review/*` | PF3 | **FAIL** (internal contradictions, stale evidence, destructive fixes) |
| ML + hilarious-seer | `updates/2026-11-14-ML-AUDIT-childlike-airport/**`, hilarious-seer audit/quickwins | PF4 | **FAIL as written**; findings merge, fixes mostly veto |
| Actions | `actions_deepdive/GA1..GA4` | GA1–GA4 | PASS; operational fixes are high-value |
| inspect-wt / deepAI | `2026-11-14/inspect-wt_*`, `deepAI_proposed_fixes_*` | PF5 | **NOT PRESENT** on this host or `origin` |

## Adopt / merge (highest value)

1. **Actions P0 set** — `scanner.py:2937-2942` (`KeyError:'LONG'`), 7× `update-environment:false`, CI `"ME"` alias, Playwright `ubuntu26.04`, 100 MB JSON, audit cron 2h + timeout 130, split `dashboard-publish`, PEAD push loop. See `../actions_deepdive/ACTIONS_DEEP_DIVE.md`.
2. **`pi_data_hygiene.py` + tests as a post-generation gate (G14)** — but harden first: require explicit `--json`, non-empty-array guard, baseline diff. As wired it can vacuous-pass via the `active_picks.json` fallback and reports 0 `PLACEHOLDER_ENTRY` while raw has 85 zero-entry rows (PF2).
3. **`pi_horizon_validation.py`** — standing rigor gate; reproduces 0/6 (n≥60) and 0/26 (n≥30) horizons. Adopt into `patch_plan/acceptance_tests.md`.
4. **Direction-aware, unit-consistent PnL** — fix 9 sign pairs + 18 mismatches in `data/live_picks.db`; one `pnl_pct` source (PF4).
5. **SQLite truth layer** — 129 rows, 69 ACTIVE/60 OPEN, max `last_updated 2026-05-25` (172.9 d); `pick_history` 136 all `REGISTERED`; `audit_trail.db` audit tables 0 rows (PF4).
6. **Alpha Engine concurrency** — `cancel-in-progress: true → false` (`alpha-engine-live.yml:39`) + fail-loud MySQL sync (PF3).
7. **FOREX consensus hygiene** — dedup `(symbol,direction,strategy)` + explicit blacklist + shadow hard-disable gate (PF3).
8. **COMMODITY provenance** — real `GC=F/SI=F/CL=F` feed, staleness guard, 1-pick/day cap; replace crypto proxies RNDR/ARB/XLM/DOT (PF3).
9. **ETF symbols** — add `KWEB`/`VLUE` to `ETF_SYMBOLS`; ETF feed freshness guard; sync 16 ETF picks (PF4).
10. **Orphan merge + `|| non-fatal` surfacing** — Copy Trader/Gainer; actual orphan count 42, not 58 (PF3).
11. **Resolver-written `pick_history`** — emit CLOSED/EXIT/TP/SL events; populate `audit_trail.db` (PF4).
12. **Wilson CI + n disclosure** — every published WR shows n and CI (PF1/v1).
13. **hilarious-seer regime-layer corroboration** — annotation only, not a hard gate (PF4).
14. **New concrete v1 fixes** — Kalshi `entry_price:0`, flat-3% detector, forward-seed flag, UEPS tabs, FX fallback age-guard, FOREX threshold, entry band (PF1).

## Corrections to our documents

| # | Correction | Action |
|---|---|---|
| 1 | v4 PF 1.80 vs 0.37 is a **173-day snapshot**; fresh values **0.9196 / 0.2628** | Fix `MASTER_AUDIT.md` §3 CRYPTO PF note |
| 2 | ML `audit_trail.db` is **8 empty + 2 non-empty**, not 9 empty | Fix §3 sqlite note |
| 3 | FDR gates are **disabled**, not failing | Fix §5 wording |
| 4 | Gatekeeper leakage-masking default flipped ON in **`d8c8dd25581`, already on origin/main** | Add unreviewed production-change note |
| 5 | Test counts: 14 hygiene, 4 ML-ranker, 4 leakage | Use 14, not 11 |
| 6 | z-score: use **−22.69** live policy-clean; −7.1 is historical June | Already fixed; keep |
| 7 | "FUTURES 0 closed ever" → "0 in `recent_closed`; full history n=13" | Already fixed; keep |
| 8 | COMMODITY "DEAD since June" is a June baseline, not today | Add to v4 reconciliation |
| 9 | v4 757/1722/1293 = `picks_now_live_pnl` backlog (4,310), not `picks.active` | Already noted; keep |
| 10 | `_CANONICAL` lines are `6027`/`6200`, not `6128`; resolver/fetch live under `audit_trail/` | Fix citation drift |
| 11 | BOND feed 7→6; stocksunify2 14→13 | Update ML drift table |
| 12 | `data/live_picks.db` BOND/FOREX `current_price` is non-null | Fix "null price" wording for sqlite |
| 13 | PnL-unit bug is missing from our P0 list | Add to `QUICK_WINS.md` |
| 14 | v3 `155500Z` edits to our `QUICK_WINS.md`/`P0_QUICK_WINS.md` are uncommitted | Ignore them; our archive is canonical |

## Veto list (do not implement)

- `DELETE` ghost/zombie rows (v4 `overall:31`, `infra:94-98`).
- `UPDATE TIME_EXIT → LOST, pnl_pct=0.0` (v4 `overall:132`).
- `EXPIRED_FORCE` / mass status rewrites (v4 `equity:32`, `crypto:54`).
- Long-only PnL mass UPDATE (ML `crypto/FIX_PROPOSED.md:42-51`) — corrupts SHORTs.
- Close-at-stale-price (ML `crypto:58-60`, `stocks:41-45`, `bonds:76-77`, `forex:28,34`).
- Invert the ML confidence gate (v4 `overall:58`, `crypto:97`; hilarious overall `:2`).
- Unblock FUTURES / add `MUTUAL_FUND` / retire 364 workflows (v4 `commodity:13`, `overall:191`).
- Purge/archive old picks >30 d (hilarious `summary:30,36`) — quarantine in view instead.
- Build the entire mutual-fund surface (ML `mutual_funds:24-34,49-73`) — de-advertise/`NOT_BUILT` per our plan.
- BOND entry-copy backfill (v1 `BOND.md:5`), FOREX/CRYPTO data purge (v1 `FOREX.md:5`, `CRYPTO.md:33`), `01-crypto.md:79` UPDATE.

## Workflow corrections for the master reviewer

- Use one `quote_status` enum and one dedup key across all plans.
- Replace the 84.5-min runtime with **GA4 p50 97.2 / p95 111.6** and the 56.6-min FTP driver.
- Apply edits from a fresh `origin/main` (our worktree is ~3,876 commits behind; the archive itself is already on main).
- inspect-wt/deepAI remain unavailable; do not claim their contents.

## Still unmerged / open

- v1 `master-plan/inputs/01..07` and scratch `QW-ALL-1..9` (PF1/PF5).
- v3 `174500Z` ML_VALIDATION and `175100Z` PEER_REVIEW_R2 (PF2).
- v4 `proposed_fixes/*` — selective only (PF3).
- ML `proposed_fixes/*` — findings yes, SQL no (PF4).
- hilarious-seer quickwins — regime annotation only (PF4).
- inspect-wt/deepAI — absent until the peer pushes or copies files.

## UNVERIFIED

- Whether v3's `pi_data_hygiene.py` catches the raw 85 zero-entry rows once its fallback is removed (PF2 inference).
- Exact fresh CRYPTO PF 0.9196/0.2628 provenance (PF1 reports it; not independently re-derived here).
- PEAD 60/60 push-failure root cause (3/3 sampled).
- Whether the guardian's 14 reruns ultimately succeed.
- The 17:33Z mass-failure root cause.
