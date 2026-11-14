# Peer Review PR2 — EQUITY / ETF / BOND / MUTUAL FUNDS

**Verdict: FAIL** — the v2 plan is directionally correct and its core counts reproduce, but it is not ready to ship as-is. Two of its own recommendations are internally inconsistent (a broken validation snippet in P0-6 and a UNQUOTED-vs-LAST_CLOSE label collision in P0-1/P0-2), its mutual-fund evidence is stale against the main checkout, and it omits four material peer actions. Full must-fix list in §9.

**Reviewer:** Peer Reviewer PR2 · **Clock:** 2026-11-14T16:25Z
**Repo:** `/home/eaguiar2015/findtorontoevents_antigravity.ca` · worktree HEAD `1d9354ab9e2` (branch `finpredict-v2`), `origin/main` `b9a9e5b859b`
**Scope:** EQUITY, ETF, BOND, MUTUAL FUNDS only. Read-only; no repo source modified.
**Our archive reviewed:** `2026-11-14/finpredict-v2_20261114-1602/` (`MASTER_AUDIT.md`, `recommendations/per_asset_class/{equity_etf,bond_mutual_funds}.md`, `recommendations/QUICK_WINS.md`, `recommendations/patch_plan/P0_QUICK_WINS.md`, `PEER_CROSSREF.md`, `sub/D_non_crypto.md`, `raw/*`).
**Peers reviewed:** v1 (`finpredict` 2026-11-14T160004Z + its `quick-wins/by-asset-class/*.md` on `origin/main`), v3 (`finpredict-v3` 2026-11-14T155500Z + its `QUICK_WINS/asset_classes/*.md` and `PEER_REVIEW/*.md` at 161500Z/161700Z on `origin/main`), v4 (`audits/2026-11-14/finpredict-v4_2026-11-14-1555/`), ML peer (`updates/2026-11-14-ML-AUDIT-childlike-airport.md` + `proposed_fixes/{stocks,etfs,bonds,mutual_funds}/FIX_PROPOSED.md`).

---

## 1. Population reconciliation — the root of the v4 count dispute

All "active" numbers in this review belong to one of five different populations. They are not interchangeable; most peer contradictions disappear once the population is named.

| Population | Source | EQUITY | ETF | BOND | Notes |
|---|---|---:|---:|---:|---|
| Curated panel | `picks.active` @ `dashboard_data.json` (gen `2026-11-14T14:30:07Z`) | **2** | **10** | **0** | The 20-row page |
| Raw dashboard inventory | `picks.active_raw` (status OPEN) | **94** | **30** | **15** | 4,148 rows total |
| Pre-gate/per-class tile | `performance.by_asset_class[*].active` | **58** | **15** | **3** | Sums to 158 |
| Legacy tracker | `audit_dashboard/data/picks_now_live_pnl.json` (gen `2026-11-12T18:57:19Z`) | **757** | **1,722** | **1,293** | `n_open=4,310`, no CRYPTO; 45 h old |
| Local stale payload | `audit_dashboard/data/dashboard_data.json` (gen `2026-10-19T19:40Z`) | 23 active total | — | — | 26 days old; `active_raw=4,142` |

Recomputed from our archived live payload (`raw/dashboard_data.json`, verified 16:25Z):
`picks.active=20`, `picks.active_raw=4,148`, `picks.recent_closed=3,500`, `summary.total_active_picks=20`, `summary.concentration_summary.total_active=263`, `performance.by_asset_class.active` sum = 158 (CRYPTO 58, EQUITY 58, FOREX 20, FUTURES 1, BOND 3, ETF 15, SPORTS 1, COMMODITY 2).

`active_raw` per class (rows / OPEN / frozen at `current==entry` or null) reproduces exactly:
EQUITY 182/94/40 · ETF 38/30/15 · BOND 15/15/9 · FOREX 277/118/93 · CRYPTO 3,577/402/334 · COMMODITY 44/27/18 · FUTURES 13/3/3 · SPORTS 2/2/2.

### v4's 757 / 1,722 / 1,293 — resolved, not wrong

These are exact counts from `audit_dashboard/data/picks_now_live_pnl.json` (`by_class`: BOND 1,293 · ETF 1,722 · FOREX 534 · EQUITY 757 · COMMODITY 4; `n_open=4,310`). They are a **separate legacy tracker**, not `picks.active` or `picks.active_raw`. Our `MASTER_AUDIT.md:372` calls them "DB/backlog populations" — correct in spirit, imprecise in label. Say **`picks_now_live_pnl.json` (legacy tracker)** to prevent a third mismatch.

### v4's "0 active picks" — contradicted by the live artifact, and internally inconsistent

- Our archived live payload has `picks.active` length **20** and **no top-level `n_active_picks` key**. A direct live fetch by v1 and v2 both returned 20. v4's "0" is not reproducible against the live payload.
- v4's own two reports disagree with each other: `dashboard_metrics_sources.md` says live `dashboard_data.json` is `generated_at 2026-11-14T14:30:07Z` (~1.4 h) and then claims `n_active_picks: 0`; `noncrypto_deep_dive.md` says the same file is **26 days old** (`2026-10-19T19:40Z`). Both statements cannot describe the same file.
- The 26-day file is real: **local** `audit_dashboard/data/dashboard_data.json` is `generated_at 2026-10-19T19:40:11Z`, 23 active / 4,142 raw / 3,500 closed. v4 likely mixed the local file (26 d) with the live HTTP file (1.4 h) and then read a zero-valued UI field as `n_active_picks`.

**Conclusion:** v4's class counts are usable as a **legacy-tracker population**; its "0 active / empty dashboard" headline is FALSE for the live surface and should not be used to justify pipeline work. Its underlying finding (Alpha Engine unhealthy) remains correct and is independently confirmed by v1/v2.

---

## 2. Per-class reconciliation

Legend for evidence: `rc` = `picks.recent_closed`; `policy` = `pf_registry.by_asset_class_policy_clean_net`; `intrabar` = v4 `intrabar_truth_by_class.json`; `picks_now` = legacy tracker.

### 2.1 EQUITY

| Claim | v1 | v2 (ours) | v3 | v4 | ML | Reconciliation |
|---|---|---|---|---|---|---|
| Open picks | 94 raw / 2 curated | 94 raw / 2 curated | "ALIVE", curated shown | **757** (`picks_now`) | 5 in `live_picks.db`; 14 in `stocksunify2` | Different populations; all three numbers are real |
| Frozen/0% rows | 40/94 (43%) | 40/94 | prices are legitimate Fri close; "parked", not stale | avg PnL −5.22% (`picks_now`) | 128/129 stale in `live_picks.db` | Two different phenomena: parked Friday close (curated) vs 172-day-old DB rows |
| Returned PnL | n=738, 47.0%, +238.4% (rc); headline n=8 75%/PF 8.86 | same + policy n=461, PF 0.7022, z=−3.03 | n=8 CI [0.41,0.93]; larger ~43–46%/PF ~0.70 | intrabar n≈249–250, WR 59.0–59.2%, PF 0.934–0.939, FAIL | — | All sub-1.5 PF; the n=8 "edge" is meaningless. No contradiction on direction |
| Defect class | price provenance + misleading headline | quote provenance (P0-1/2/3) + ledger integrity (P1-7) + n<100 display (P1-6) | **statistical disclosure** (n+CI, n≥30 gate) | purge >14 d, demote WATCH, MeanReversionBB graduation | asset_class backfill, PnL refresh, age-out, re-run equity scanners | Different but compatible fixes |
| Two impossible AAPL entries | — | yes (P1-7) | — | — | — | Ours is the only audit that caught this; keep it |

**Net:** EQUITY evidence agrees that there is no robust edge. The only real contradiction is terminological: "frozen 40/94" (v1/v2) vs "legitimate parked Friday close" (v3). Both can be true — the price is correct, but `pnl_pct==0` is an identity, not an observation. v3 is right that it is not a *price-fidelity* bug; our P0-2/P0-3 are the correct remedy, but P0-1's `UNQUOTED` label is the wrong status for these rows (see §5.1).

### 2.2 ETF

| Claim | v1 | v2 (ours) | v3 | v4 | ML | Reconciliation |
|---|---|---|---|---|---|---|
| Open picks | 30 raw / 10 curated / 15 frozen | 30 raw / 10 curated / 15 frozen | 10 active pinned at Friday close | **1,722** (`picks_now`) | `active_picks_etf.json` 16 picks (2 d) | Different populations |
| Closed/thin stats | n=567, 44.3%, +22.9% (rc); n=8, 37.5%, PF 0.76 | policy n=15, WR 73.33%, PF 1.8358, z=+1.81 | n=8, 37.5%, PF 0.76 | intrabar n=44–45, WR 2.2–2.3%, PF 0.022–0.02 | — | **Four different ETF cohorts with PF 0.02 / 0.76 / 1.84.** None is a credible edge; the 1.84 is the thinnest (n=15) |
| Classification | — | EQUITY carries SPY/QQQ/XLE/XLK; ETF carries VCSH | — | BITO/IBIT appear as top ETF picks in `picks_now` | KWEB/VLUE missing from `ETF_SYMBOLS` | All agree the symbol classifier is incomplete; ML independently confirms KWEB/VLUE → equity |
| Remedy | parked label, n+CI | quote provenance + symbol routing + n<100 gate | parked label + re-quote at open + n badge | retire or pivot; intrabar record is a design failure | add KWEB/VLUE, sync to DB, refresh PnL | Compatible; our P1-6 n<100 gate is weaker than v4's "retire/pivot" but not contradictory |

**Net:** v2's "do not quote ETF PF 1.84" is correct and is reinforced by v4 (PF 0.022) and v1/v3 (PF 0.76). Our plan should cite the intrabar evidence as the stronger reason ETF is not an edge, not merely "n too small."

### 2.3 BOND

| Claim | v1 | v2 (ours) | v3 | v4 | ML | Reconciliation |
|---|---|---|---|---|---|---|
| Open picks | 15 raw / 0 curated / 9 null price | 15 raw / 0 curated / 9 unpriced | 15 OPEN / 9 null | **1,293** (`picks_now`) | `active_picks_bond.json` 7 fresh; `live_picks.db` 2 stale (172 d) | Four populations; all real |
| Realized sample | newest closed 4.1 d | newest closed `2026-11-10T13:52:26Z` = 4.09 d; n=35, WR 34.3%, PF 0.586 (sub/D) | n=1 closed, `insufficient_data` | intrabar n=26, WR 7.7%, PF 0.391 | 3 closed rows all-time | `recent_closed` n=35 is **status-WON** WR; recomputed pnl>0 gives **37.1%** (see §5.4) |
| Policy-clean | — | **n=1**, 0/1, PF 0 | n=1 | — | — | Agreement |
| Vacuous PASS | — | yes (activeCount=0 → thresholdPass=true) | yes (`insufficient_data` health) | — | — | Agreement |
| Remedy | stamp `current_price=entry_price`; auto-expire >24 h | QW-1..7 (vacuous PASS, price coverage, dedupe, FRED, coverage gate) | backfill via `bond_data_fred`; suppress n<10; age-gate seeds; verify wiring | purge >14 d, demote WATCH, pivot/retire | sync feed→DB, refresh, emit exits, populate stats | **v1's `current_price=entry_price` stamp directly conflicts with our do-not-do #2** — reject it |

**Net:** BOND is unambiguously not a usable class. v4's 1,293 is a different tracker. Our QW-1..7 are the most concrete plan; v4's "pivot/retire" is a strategic layer we do not contradict but also do not adopt.

### 2.4 MUTUAL FUNDS

| Claim | v1 | v2 (ours) | v3 | v4 | ML |
|---|---|---|---|---|---|
| Status | UNBUILT | NOT BUILT | PLANNED, not implemented | not covered (only 5 non-crypto classes) | "zero presence anywhere" |
| Ranker | absent | absent from `origin/main`; untracked in main checkout | absent | — | absent from `alpha_engine/` |
| Page | absent | `/audit/mutual-funds.html` absent | `/audit/mutual-funds.html` absent; `audit_dashboard/funds.html` exists (role unconfirmed) | — | — |
| Metadata | — | absent from origin; untracked in main checkout | — | — | — |
| Recommendation | relabel "planned" | **de-advertise + NOT_BUILT; do not build** | planned badge, or minimal ranker | — | **add MF as first-class class** (symbol set, gatekeeper id 7, scanner stub, dashboard tile) |

**Net:** v1/v2/v3 agree MF is not a live class. The ML peer's "no mutual funds anywhere" is **true for `origin/main`, the live payload/DB and the tracked strategy inventory**, but literally false: the main checkout has an untracked prototype (see §7). The ML peer's recommendation to **add** MF directly conflicts with our de-advertise recommendation; see §5.5 for why we should keep de-advertising.

---

## 3. Contradictions flagged

1. **v4 "0 active picks" is false for the live surface.** Archived live payload: `picks.active=20`, no `n_active_picks` key. v4's own `dashboard_metrics_sources.md` and `noncrypto_deep_dive.md` disagree on whether `dashboard_data.json` is 1.4 h or 26 d old. Use the 26-day local file only for the legacy/local view.
2. **v4's 757/1,722/1,293 are `picks_now_live_pnl.json`, not the DB and not `active_raw`.** Our `MASTER_AUDIT.md:372` label should be corrected.
3. **ETF PF has four values (0.02 / 0.76 / 1.84 / "no edge").** They are different cohorts/methods, not arithmetic disagreements. The correct conclusion is "no cohort survives + the only positive one is n=15," not "peers disagree."
4. **BOND win rate: 34.3% vs 37.1% on the same n=35.** Definitional: sub/D counts `status=WON` (12/35 = 34.3%); recomputing `pnl_pct>0` gives 37.1%. Both are in our own archive; name the definition.
5. **EQUITY "parked" vs "frozen".** v3's price-fidelity check is correct (ADBE/SNDL equal Friday close), but `pnl_pct==0` is still an identity. Keep the "parked" nuance; do not call the price wrong.
6. **ML "no mutual funds anywhere" vs untracked prototype.** Scope the claim: no MF in production/origin; an untracked research prototype and output exist in the main checkout.

---

## 4. Peer recommendations we missed

These are concrete actions present in peer artifacts (including `origin/main` quick-win directories that were not in our assigned reading list) that our plan does not cover.

| # | Source | Recommendation | Why it matters for EQUITY/ETF/BOND/MF | Our gap |
|---|---|---|---|---|
| M1 | v1 EQUITY #2; v3 EQUITY #1/#3, ETF #2/#4 | Put **`n` + Wilson 95% CI + "thin sample" badge** next to every headline WR/PF; suppress below n=30 | Kills the EQUITY "n=8 / 75% / PF 8.86" and ETF "n=8 / 37.5%" misread | We gate class-level n<100 (P1-6) but never fix the EQUITY n=8 headline; we mark its producer UNVERIFIED |
| M2 | v1 BOND #2; v4 fix 1.1; ML stocks 3.3 | **Force-close/age-out** stale unquoted open rows (BOND >24 h; EQUITY/ETF/BOND >14 d; stocks >30 d) with `STALE_NO_QUOTE`/`TIME_EXIT` | Our plan quarantines rows but leaves them OPEN forever; the resolver path is a missing action | P0-7 adds `quarantined:true` only |
| M3 | v4 fix 1.3 | **Demote ETF (and keep BOND) to `WATCH_ONLY_CLASSES` with `position_size_pct=0`** until n≥100/WR≥50/PF≥1.5 | `quality_gates.BLOCKED_ASSET_CLASSES` contains BOND but **not ETF**; our plan only suppresses ETF display | P1-6 is display-only |
| M4 | ML audit §3.2/§3.6/§3.7; ML bonds/ETFs/stocks fixes | **`live_picks.db` sync + PnL-sign bug**: `active_picks_bond.json`/`active_picks_etf.json` never reach the DB; `unrealized_pnl_pct` sign is inverted on 8 rows, 15 magnitude mismatches, `pick_history` is 136 `REGISTERED` only, `audit_trail.db` 9 tables empty | This is a second, DB-level data path that our dashboard-first plan does not touch | Mentioned once in `QUICK_WINS.md:30`, absent from the per-class plans |
| M5 | v3 MUTUAL_FUNDS #3 | **`audit_dashboard/funds.html` exists** (206,841 B, "Strategy Funds", on `origin/main`) and may be the intended destination | Our plan says "no page" and recommends a new page without reconciling `funds.html` | QW-2 should explicitly state `funds.html` is *not* a mutual-fund page and must not be wired |
| M6 | v4 fix 3.2 | Investigate the **`MeanReversionBB` MDD=0.9999 artifact** and the one EQUITY sleeve with n≥20 (n=200, WR 53.9%, PF 1.76) | The only plausible EQUITY salvage path in peer evidence; our P1-7 flags entry sanity but not MDD | Not covered |
| M7 | v1 EQUITY #1; v3 EQUITY #2 | Stamp **`last_quote` / `price_source` / `price_asof`** on the pick contract, not only `quote_status` | Our P0-1 is close, but peer evidence names `universal_price_enricher` and `long_term_pick_contract` as the producers | Our P0-1 targets the dashboard generator only |

---

## 5. Our recommendations that conflict with peer evidence

### 5.1 P0-1 / P0-2 / P0-3 double-label the same EQUITY/ETF cohort

`equity_etf.md` P0-1 says the "EQUITY 40 / ETF 15 frozen cohort becomes explicit `UNQUOTED`." P0-2/P0-3 say the same rows are `LAST_CLOSE` because their price equals the verified Friday close. v3 confirms the price is a legitimate Friday close, not a quote miss. The cohort must be split:

- `current_price` present and equal to the last **completed session** close → `LAST_CLOSE` (parked), PnL computable but labelled as-of close.
- `current_price` null or no quote for a symbol that should have one → `UNQUOTED`.

Ship P0-1 only after this split, or the "40/15 frozen" number will be mislabelled and the P0-2 badge and P0-1 badge will disagree on the same row.

### 5.2 P0-6 validation snippet is broken against the current classifier

`equity_etf.md` P0-6 validation calls:

```python
normalize_asset_class({"symbol": s, "category": "equity"})
```

and expects `SPY→etf`, `VCSH→bond`, `IBIT/BITO→etf`, `VTI→etf`. In this worktree **all eight cases return `equity`** because the category wins before the symbol sets (`alpha_engine/asset_class.py` category-first precedence). Verified 16:25Z:

```
SPY want etf got equity FAIL ... VTI want etf got equity FAIL
```

(the same call with `category:""` returns `SPY→etf`, but `VCSH/IBIT/BITO→equity`). The P0-6 code change as written ("let the symbol override a stamped EQUITY/ETF label in `_coerce_asset_class`") does not change `normalize_asset_class` precedence. Either fix the validation to call `classify_pick_asset_class_upper`, or extend `normalize_asset_class` with the same symbol-authority rule. As written, the acceptance test cannot pass.

### 5.3 QW-4's missing-ticker list is drifted

`bond_mutual_funds.md` QW-4 says the resolver is missing `SHY, JNK, EMB, LQD, AGG, BND, TIP, MUB, TLH, GOVT, BNDX` (12 of 14). The actual `BOND_SYMBOLS` has 14 members: `TLT, IEF, SHY, LQD, AGG, BND, HYG, JNK, SJNK, BKLN, EMB, TIP, MUB, IGIB`. `TLH`, `GOVT`, `BNDX` are **not** BOND members; `IEF`, `SJNK`, `BKLN`, `IGIB` are omitted from the list. The core defect (`_EQUITY_ETF_TICKERS` only knows TLT and HYG) is verified; the enumerated list should be corrected.

### 5.4 BOND WR is stated two ways in our own archive

`sub/D_non_crypto.md:270` and `bond_mutual_funds.md:20` say n=35, **WR 34.3%**, PF 0.586. `MASTER_AUDIT.md:233` says n=35, **WR 37.1%**, −7.7%. Both are computed from `recent_closed`; 34.3% counts `status=WON` (12/35), 37.1% counts `pnl_pct>0`. Pick one definition and label it; do not publish two "BOND WR" values.

### 5.5 ML peer recommends adding MF; we recommend de-advertising — keep our position

The ML peer's `proposed_fixes/mutual_funds/FIX_PROPOSED.md` proposes `MUTUAL_FUND_SYMBOLS`, `_CAT_MAP`/`_LOWER_TO_UPPER` entries, gatekeeper class id `7`, a scanner stub, and a dashboard tile. This does not conflict with their factual finding (none exists today), but it conflicts with our recommendation. Our reasons remain stronger:

- A mutual fund prices once daily at NAV (T+1; `multi_asset/portfolio_defs.py:714-718`), so `current_price`, intraday TP/SL and the resolver contract are structurally inapplicable.
- Adding a class with `activeCount=0` re-opens the vacuous-PASS bug we are fixing (QW-1), even if the tile renders empty.
- The only implementation is an **untracked prototype** whose output filename is misspelled (`mutut_fund_rankings.json`, `alpha_engine/mutual_fund_ranker.py:53`), with no coverage gate.
- Adding gatekeeper id `7` and a scanner stub is a multi-week cross-cutting change for a class with zero resolved outcomes.

Recommendation: keep **de-advertise + `NOT_BUILT`**, and explicitly reject the ML peer's build path in the master plan so the two workstreams do not collide.

### 5.6 Mutual-fund evidence in our UNVERIFIED is stale

`bond_mutual_funds.md:619` says the prototype "has never produced an output file (no `mutut_fund_rankings.json`, no NAV cache)." This is contradicted by the main checkout at 16:25Z:

- `audit_dashboard/data/mutut_fund_rankings.json` — 39,508 B (misspelled, matches line 53).
- `audit_dashboard/data/mutual_fund_nav_cache/` — populated CSV cache (e.g. `core_AGG.csv`…, ~2.8 MB dir).
- `reports/mutual_fund_results.json` — `generated_at 2026-10-23T04:07:06Z`, walk-forward results.
- `audit_dashboard/mutual-funds.html` — 206,841 B (untracked; not the same as `funds.html`).
- `alpha_engine/data/mutual_fund_metadata.csv` — 38 lines (37 funds + header).

Correct the UNVERIFIED to: "the prototype has produced an untracked output/cache/page in the main checkout, but none of it is committed to `origin/main` or wired into the live pipeline." The conclusion (not built in production) is unchanged.

### 5.7 MASTER_AUDIT path drift

`MASTER_AUDIT.md:91` lists `concentration_summary.total_active = 263`. The value 263 is correct, but the path is `summary.concentration_summary.total_active`; there is no top-level `concentration_summary` key. Similarly `MASTER_AUDIT.md:89` says `performance.by_asset_class "active" 158` — correct (recomputed sum 158), but ETF is 15 there, not 30; avoid mixing it with raw OPEN.

---

## 6. Citation spot-check (26 references)

All checks run at 16:20–16:26Z against worktree HEAD `1d9354ab9e2` (read-only). `$W` = worktree root.

### Valid (verified exact or within ±2 lines)

| # | Citation | Check |
|---:|---|---|
| 1 | `$W/audit_trail/dashboard_generator.py:6824-6826` | `threshold_pass = ( active_count == 0 or (` — vacuous PASS confirmed |
| 2 | `$W/audit_trail/dashboard_generator.py:1681-1688` | carried `current_price` accepted as fallback; comment matches |
| 3 | `$W/audit_trail/dashboard_generator.py:1739-1755` | `if price is None: … continue` leaves pick untouched |
| 4 | `$W/audit_trail/dashboard_generator.py:3645-3680` | `_coerce_asset_class` returns any non-UNKNOWN upstream label unchanged |
| 5 | `$W/audit_trail/dashboard_generator.py:15400-15455` | `ac_breakdown` iterates `active + _closed_fallback` before curation |
| 6 | `$W/audit_trail/dashboard_generator.py:11687-11688` | Tier-2 floor `n >= 100` |
| 7 | `$W/audit_trail/dashboard_generator.py:9538` | `active_raw_snapshot = list(active)` before dedupe at `:9876` |
| 8 | `$W/audit_trail/dashboard_generator.py:9831-9836` | dedupe key includes `source_system` (cross-emitter dupes survive) |
| 9 | `$W/audit_trail/dashboard_generator.py:18006-18012` | `asset_class_summary` attached from `_build_per_asset_quality_summary` |
| 10 | `$W/tools/sync_summary_picks_json.py:63-65,161` | three different populations; `100*wins/resolved` |
| 11 | `$W/audit_trail/fetch_stock_prices.py:68-77` | sections `active_picks/closed_picks/picks`; `picks` is a dict → skipped; allow-list omits `bond` |
| 12 | `$W/audit_trail/fetch_stock_prices.py:20-23,100-105` | `last_price or previous_close`; only file-level `updated_at` |
| 13 | `$W/audit_trail/universal_pick_resolver.py:433-443` | `_EQUITY_ETF_TICKERS` contains TLT/HYG only among bonds |
| 14 | `$W/audit_trail/quality_gates.py:1724` | `BLOCKED_ASSET_CLASSES = {"FOREX","COMMODITY","FUTURES","BOND"}` |
| 15 | `$W/audit_trail/quality_gates.py:495` | BOND `min_trades: 0` |
| 16 | `$W/audit_trail/quality_monitor.py:12,171-174` | `MIN_ACTIVE_FOR_ENFORCEMENT=10`; `active_count == 0 or` pass |
| 17 | `$W/alpha_engine/asset_class.py:28-53` | BOND/ETF frozensets; VCSH/IBIT/BITO/KWEB/VLUE absent |
| 18 | `$W/alpha_engine/money_ready_verdict.py:226` | `CANONICAL_ASSET_CLASSES` has 7, no MF |
| 19 | `$W/multi_asset/portfolio_defs.py:382-395,677-720` | `tactical_fund_rotation` + `mutual_fund` universe |
| 20 | `$W/multi_asset/portfolio_defs.py:714-718` | mutual funds "settle T+1 … only at NAV close" |
| 21 | `$W/.github/workflows/etf-bond-scanner.yml:152-156,159` | merge default + `SKIP_FRED: '1'` |
| 22 | `$W/alpha_engine/bond_scanner.py:289-296,319` | `fetch_bond_bundle`; `source_system="bond_scanner"` |
| 23 | `$W/alpha_engine/bond_data_fred.py:48,313` | `FRED_SERIES`; `fetch_bond_bundle` |
| 24 | `$W/.github/workflows/bond-agent.yml:126-148,217,246-320` | T10Y2Y only; writes `bond_picks.json`; merges |
| 25 | `$W/audit_dashboard/index.html:4453-4466,4509-4510,4719-4732,8889-8905,9134-9145,9393-9408,4368` | live-price apply, PnL cell, Current cell, closed-cols mapper, `_KNOWN_STOCKS` |
| 26 | `$W/audit_dashboard/template.html:4946` | `thresholdPass ? 'pass' : (activeCount > 0 ? 'warn' : 'idle')` — backend PASS wins |

### Invalid / drifted / needs correction

| # | Citation | Problem | Correct value |
|---:|---|---|---|
| D1 | `equity_etf.md` P0-6 validation (`normalize_asset_class({"symbol":s,"category":"equity"})`) | All 8 cases return `equity`; acceptance test cannot pass | Use `classify_pick_asset_class_upper`, or add symbol authority inside `normalize_asset_class` before category |
| D2 | `bond_mutual_funds.md:251` missing-ticker list | Includes non-members `TLH/GOVT/BNDX`; omits `IEF/SJNK/BKLN/IGIB` | 14 members listed in §5.3; core finding still valid |
| D3 | `bond_mutual_funds.md:619` "no output file / no NAV cache" | False in main checkout | Untracked `mutut_fund_rankings.json`, `mutual_fund_nav_cache/`, `reports/mutual_fund_results.json` exist |
| D4 | `MASTER_AUDIT.md:91` `concentration_summary.total_active` | Wrong path | `summary.concentration_summary.total_active = 263` |
| D5 | `equity_etf.md:173` "ETF contains bond fund `VCSH`" | Classifier maps VCSH→equity; it lands in ETF only via an upstream-stamped label | Say "upstream-stamped ETF"; the `_coerce_asset_class` explanation is correct |
| D6 | `bond_mutual_funds.md:27` "/audit/mutual-funds.html does not exist" | True for tracked/`origin/main`; an untracked page exists in the main checkout | "absent from `origin/main`; untracked prototype exists" |
| D7 | `bond_mutual_funds.md:20` BOND WR 34.3% | Same cohort as MASTER's 37.1% under a different win definition | Label `status=WON` vs `pnl_pct>0` |

---

## 7. Mutual-fund existence check

Checked at 16:25Z with `git ls-tree origin/main`, `git cat-file -e origin/main:…`, and filesystem inspection.

| Artifact | `origin/main` | Worktree `finpredict-v2` | Main checkout |
|---|---|---|---|
| `alpha_engine/mutual_fund_ranker.py` | **ABSENT** (`git cat-file -e` → no) | absent | **present, untracked** — 23,931 B |
| `alpha_engine/data/mutual_fund_metadata.csv` | **ABSENT** | absent | **present, untracked** — 5,983 B / 38 lines (37 funds) |
| `audit_dashboard/mutual-funds.html` | **ABSENT** | absent | **present, untracked** — 206,841 B |
| `/audit/mutual-funds.html` deployed | **not deployed** (no deploy-list reference; only `institutional_readiness_plan.html:190` mentions it) | n/a | n/a |
| `audit_dashboard/funds.html` | **present** — 206,841 B, title "Strategy Funds"; *not* a mutual-fund page | present | present |
| MF output/cache | absent | absent | **present, untracked** — `audit_dashboard/data/mutut_fund_rankings.json` (39,508 B), `audit_dashboard/data/mutual_fund_nav_cache/` |
| MF in payload | **0 occurrences** of "mutual" in `dashboard_payload.json`; no MF rows in `picks.*` | same | same |
| MF in taxonomy | `CANONICAL_ASSET_CLASSES` 7 classes (no MF); `asset_class.py` no MF mapping; gatekeeper map 7 classes | same | same |
| MF strategies | none (`bond_*`, `etf_*`, `equity_*`, `forex_*`, `crypto_*`, `commodities_*`, `futures_*` exist) | same | none tracked |
| `findmutualfunds2/` | 3 PHP debug files only | 3 | 3 |
| DB families | `mf_` / `mf2_` recon only (`tools/recon_uncharted_tables.py:29-30`) | same | same |

**ML peer "no mutual funds anywhere":** confirmed for production scope — no MF class, strategy, symbol set, DB rows, payload rows, page, or ranker on `origin/main`. **Literally false** only because the main checkout contains an untracked research prototype, NAV cache, output JSON, metadata CSV, page, tests and `tools/mutual_fund_backtest.py`. Recommend the master plan phrase it as "no mutual-fund class in production; untracked research prototype exists and is not wired."

---

## 8. Recent-file scan (project root, since 2026-11-14 15:30Z)

Excluded `.git`, `node_modules`, `.kilo/worktrees`. New artifacts found:

**v4 audit (under `audits/2026-11-14/finpredict-v4_2026-11-14-1555/`):**
`actions_health_report.md`, `crypto_deep_dive.md`, `dashboard_data_report.md`, `dashboard_metrics_sources.md`, `forex_deep_dive.md`, `INDEX.md`, `market_crossref_report.md`, `noncrypto_deep_dive.md`, `evidence_db_health.json`, `evidence_intrabar_truth.json`, `evidence_money_ready_verdict.json`, `evidence_pick_summary_stats.json`, `peer_review/2026-11-14-ML-AUDIT-childlike-airport.md`, `peer_review/PEER_REVIEW_INTEGRATION.md`, `proposed_fixes/{commodity,crypto,equity,forex,infra,overall}/QUICK_WINS.md`.

**ML peer (under `updates/2026-11-14-ML-AUDIT-childlike-airport/`):**
`proposed_fixes/{stocks,etfs,bonds,mutual_funds,forex,overall}/FIX_PROPOSED.md` (the main `2026-11-14-ML-AUDIT-childlike-airport.md` is also new).

**Other project-root changes:** `bestiejob/{FRESH_JOBS.md,jobs.json,README.md,README.BAK_2026-11-14T153352Z.md,README.BAK_2026-11-14T160754Z.md,logs/cron_30min.log,public/**/jobs.json}`, `.github/gh_monitor_state.json`, `___HELL_HEALTH_OPENCODE.MD`, `.kilo/agent-manager.json`, `logs/vllm_8000.log`, `reports/peer_inbox_hourly.log`, `tools/ai_menu.sh`.

**Committed peer artifacts now on `origin/main` that were not in our assigned reading list:**
`2026-11-14/finpredict-v3/2026-11-14T161500Z/QUICK_WINS/{00_INDEX.md,overall/GLOBAL_QUICK_WINS.md,asset_classes/{CRYPTO,EQUITY,ETF,BOND,FOREX,FUTURES,COMMODITY,MUTUAL_FUNDS}.md}`, `2026-11-14/finpredict-v3/2026-11-14T161700Z/PEER_REVIEW/{00_INDEX.md,overall/PEER_REVIEW_OVERALL.md,asset_classes/*.md}`, and `2026-11-14/finpredict/2026-11-14T160004Z/quick-wins/by-asset-class/*.md`. The v1/v3 per-class quick wins reviewed in §4 come from these.

---

## 9. Ranked must-fix list (before the plan is shippable)

1. **Fix the P0-6 acceptance test / classifier precedence.** All eight `normalize_asset_class(..., category="equity")` cases return `equity`; the proposed symbol-authority fix must be applied inside `normalize_asset_class` (or the test must call `classify_pick_asset_class_upper`). *Blocking: the plan's own green test cannot pass.*
2. **Split `UNQUOTED` from `LAST_CLOSE`.** Use `LAST_CLOSE` for EQUITY/ETF rows whose price equals the verified Friday close (v3); reserve `UNQUOTED` for null/unfetched prices. Update P0-1's "40/15 become UNQUOTED" claim. *Blocking: two badges would disagree on the same row.*
3. **Correct the mutual-fund evidence.** Replace "never produced output / no NAV cache / page does not exist" with "untracked prototype + output + cache + page exist in the main checkout; none are on `origin/main` or wired." Add `funds.html` to QW-2 as a *different* page that must not be wired. *Blocking: factual accuracy of the MF section.*
4. **Add the missing peer actions:** (a) n + Wilson CI + "thin sample" badge for EQUITY/ETF headlines (M1); (b) force-close/age-out stale unquoted rows (M2); (c) add ETF to `WATCH_ONLY_CLASSES` / `BLOCKED_ASSET_CLASSES` (M3); (d) `live_picks.db` sync + PnL-sign fix (M4). *Blocking: plan incompleteness against peer evidence.*
5. **Fix the drifted citations:** QW-4 ticker list (D2); `summary.concentration_summary` path (D4); VCSH wording (D5); BOND WR definition 34.3% vs 37.1% (D7). *Non-blocking but should be corrected before publication.*
6. **Explicitly reject the ML peer's "add MF class" proposal** in the master plan, with the NAV-only / vacuous-PASS / untracked-prototype rationale. *Non-blocking; prevents workstream collision.*
7. **Correct the v4 reconciliation label** from "DB/backlog populations" to "`picks_now_live_pnl.json` legacy tracker (4,310 rows, 45 h old)" and keep the live-payload contradiction. *Non-blocking.*
8. **Optional / later:** investigate `MeanReversionBB` MDD=0.9999 and the one EQUITY sleeve with n≥20 (v4 fix 3.2); add `last_quote`/`price_source`/`price_asof` at the enricher/contract layer (v1 EQUITY #1). *Non-blocking.*

---

## 10. UNVERIFIED

- **Whether the live site advanced after the 14:30:07Z payload.** All counts here are from our archived `raw/dashboard_data.json` (gen 14:30:07Z) and recomputation; no new HTTP fetch was made in this review.
- **Exact producer of the EQUITY headline n=8 / 75% / PF 8.86.** Still not located in repo source (our `equity_etf.md:375` also marks this UNVERIFIED). v1/v3 quote it; v2 traced only n=738/759/461.
- **Which ETF cohort the 1,722 legacy-tracker picks actually resolve against.** We confirmed the count and 45 h age; we did not resolve those rows to a closed-ledger cohort.
- **Whether `mutual_fund_ranker.py` output is trustworthy.** The output JSON and NAV cache exist untracked, but the ranker's coverage gate, data freshness (`nav_through`) and the `mutut` filename typo are unverified at runtime.
- **Whether `audit_dashboard/funds.html` shares data with the MF prototype.** Title is "Strategy Funds"; no reference to `mutual_fund` was found, but this was not exhaustively audited.
- **`live_picks.db` PnL-sign contradiction root cause.** The ML peer's 8/15 counts were read from its report; we did not re-query the SQLite DB in this pass.
- **v4's `intrabar_truth_by_class.json` provenance.** We used v4's reported n/WR/PF as peer evidence; we did not re-derive them from `at_signal_outcomes`.
- **Workflow mid-retry root causes and browser rendering** remain UNVERIFIED, as in `MASTER_AUDIT.md` §8.

---

*No fabricated numbers. Every count above is from the archived live payload, a `git` tree/status check, a `file:line` read in the worktree, or a named peer artifact. Where a peer number could not be reproduced, it is marked UNVERIFIED.*
