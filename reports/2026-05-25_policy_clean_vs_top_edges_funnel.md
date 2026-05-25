# Policy-Clean Verdict vs. Top-Edges — COMMODITY Funnel Audit (2026-05-25)

**Author:** Claude (subagent for /audit money_ready verdict pipeline)
**Sibling agent (a972ec...):** trade-level leakage check on the same edge cell
**Scope:** filter pipeline only — *why* `money_ready_verdict.COMMODITY.n_resolved=28` while `top_edges_per_class.COMMODITY` reports `n_closed=1219` with 71 Bonferroni-passing cells (top cell: `conf=C0.60-0.70 & rr=RR1.0-1.5 & source=multi_asset_copytrader`, n=137 / WR 70% / PF 3.27).

---

## TL;DR — Verdict (Q6)

**(c) Something else.** The discrepancy is **not** a filter killing alpha — it is **two completely disjoint cohorts** masquerading as the same dataset:

| Pipeline | Cohort source | Window | Raw COMMODITY rows |
|---|---|---|---|
| `top_edges.py` → `top_edges_per_class.json` | **MySQL DB `ejaguiar1_stocks.trading_picks`** (live via `tools.audit_pick_funnel._db.connect_stocks`) | last 90 days | **9,346** rows (1,219 closed WIN/LOSS) |
| `money_ready_verdict.py` → `money_ready_verdict.json` | **Local JSON closed-picks ledgers** (`alpha_engine/data/closed_picks.json`, `closed_picks_fast.json`, `battleground/...`, etc. — 32 source files routed through `build_pf_registry.load_rows()`) | lifetime | **60** rows (50 after dedup, 13 after policy-clean) |

The 28 number in the published `money_ready_verdict.json` (today's snapshot) and the 13 number my live re-run produced are both correct readings of the **JSON ledger** universe — they include zero of the 864 `multi_asset_copytrader` COMMODITY picks the DB has from the last 90 days, because **`multi_asset_copytrader` never writes to those JSON files**. Its closed picks live exclusively in the DB.

The policy-clean filter *also* removes alpha (see §3) but that is a secondary effect on top of the already-tiny JSON cohort. The primary discrepancy is **input scope**, not filter aggression.

---

## 1. Filters applied by `money_ready_verdict.py` between "raw" and `n_resolved=28`

`money_ready_verdict.py::_load_picks()` (lines 320-347) hands off the entire cohort load to `tools/build_pf_registry.py::load_rows() + classify_rows() + _is_policy_excluded()`. The filters are layered as follows:

### Stage A — `load_rows()` (build_pf_registry.py:311-343)
- Inputs: the closed-pick JSON files listed in `dashboard_generator.JSON_PICK_SOURCES` (canonical) — 32 files. **The MySQL `trading_picks` table is NOT in this list.**
- Output: 7,398 raw rows total → **60 raw COMMODITY rows** all-time.

### Stage B — `classify_rows()` (build_pf_registry.py:349-420)
Three sub-filters applied in order:
1. **Not-closed drop** (`CLOSED_STATUSES = {"CLOSED","WON","LOST","LOSS","EXPIRED","WIN"}` + non-null `pnl_pct`) — line 367-372.
2. **Spot-flicker drop** — non-CRYPTO rows whose `|pnl_pct| < 0.0002` (2 bp) are dropped as resolver artifacts. Line 383. `SPOT_FLICKER_THRESHOLD = 0.0002`.
3. **Dollar-scale artifact drop** — `|pnl_pct| > 1.0` (>100%) dropped as raw-dollar-in-percent-field bug. Line 386. `DOLLAR_SCALE_ARTIFACT_THRESHOLD = 1.0`.
4. **Re-emission dedup** — key = `(strategy, norm_symbol, direction, trade_date, round(entry_price,2))`. Line 397-411.

For COMMODITY this yields **50 rows kept** (10 dropped to dedup/flicker/open).

### Stage C — `_is_policy_excluded()` (build_pf_registry.py:192-225) — three-layer (M-110, 2026-05-18)
1. **Flat exclusion** — strategy OR source_system in any of `PERMANENTLY_KILLED_STRATEGIES`, `BLOCKED_SOURCE_SYSTEMS`, `PF_REGISTRY_POLICY_EXCLUDED` (quality_gates.py).
2. **Direction triple** — `(asset_class, strategy, direction)` in `BLOCKED_DIRECTION_TRIPLES` (e.g. `("FOREX","multi_asset_copytrader","LONG")` — quality_gates.py:3003).
3. **Asset-strategy pair** — `(asset_class, strategy)` in `BLOCKED_ASSET_STRATEGY_PAIRS` (quality_gates.py:2638+) — e.g. `("FUTURES","multi_asset_copytrader")` line 2719, `("COMMODITY","multi_asset")` line 2701, `("COMMODITY","alpha_engine_fast")` line 2691.

For COMMODITY this drops **50 → 13** rows kept.

### Stage D — `money_ready_verdict._class_stats()` (lines 421-505)
- Re-applies `_load_blocked()` (defense-in-depth no-op on canonical path).
- M-105 ml_enhanced quarantine (CRYPTO only).
- **M-069 (2026-05-17): NET re-judgment of win/loss** — `wins = sum(1 for v in nets if v>0)` where `nets = [_net_pnl(p) for p in ps]`. `_net_pnl` deducts per-class round-trip slippage (`alpha_engine/charter_slippage.py`). A gross WIN with pnl < 12bp (COMMODITY round-trip) is **re-classed as a net LOSS** for both WR and PF math.

### Stage E — Verdict gates (`_verdict()` line 642)
`n_ok` floor = 50 (`MIN_N_CLASS`). COMMODITY n=13 fails → verdict `INSUFFICIENT_DATA`. Today's published JSON shows `n_resolved=28` because the JSON ledgers have shifted between snapshots — the structural answer is identical regardless of 13 vs 28.

**M-067** (per task) is a *different* code path: `audit_trail/dashboard_generator.py:5644-5731` (`build_ac_breakdown_from_registry`) — it makes `compute_asset_class_health` read `pf_registry.json::by_asset_class_policy_clean_net` instead of a recompute, so the /audit tile and the verdict share one source of truth. That source of truth is **exactly the same JSON-only universe** that produces n=13. The CLAUDE.md numbers (COMMODITY PF 1.78 / n=750) are stale — they pre-date the M-069 NET re-judgment that turned most CT=F 7bp wins into net losses.

---

## 2. `top_edges.py` cohort — the OTHER universe

`tools/audit_pick_funnel/top_edges.py::main()` calls `fetch_picks(connect_stocks(), 90)` — straight `SELECT … FROM trading_picks WHERE created_at >= NOW() - INTERVAL 90 DAY`. No dedup, no flicker filter, no policy exclusion, no NET re-judgment.

Cells are scored on:
- All `C(7,3)+C(7,4) = 70` tag-dim combos over `{trust, conf, rr, fam, dir, score_dec, source}`.
- Top-200 cells per class by `n` are kept (everything below MIN_N=20 dropped).
- Bonferroni alpha = `0.05 / total_cells_evaluated`.
- Holdout split: 60/40 chrono; both halves must clear PF≥1.2.

The 1,219 / PF-3.27 numbers are **gross**, **DB-direct**, **lifetime-policy-blind**, and **not normalized for emission re-fire** (COT signals repeat every 72h release cycle — see `COT_DEDUP_SYSTEMS` in quality_gates.py:2082, which explicitly includes `multi_asset_copytrader` precisely because it re-emits `cftc_cot_commercial_signal` on the same CT=F symbol every CFTC cycle).

---

## 3. The `multi_asset_copytrader` smoking gun (Q4)

This source IS in production. It is **NOT** in `BLOCKED_SOURCE_SYSTEMS` (verified — quality_gates.py:1899+ does not contain it). Its policy status is **surgical, not blanket**:

| Quality-gate entry | Effect |
|---|---|
| `COT_DEDUP_SYSTEMS ∋ "multi_asset_copytrader"` (line 2089) | Subject to the 72h same-symbol dedup window when emitting COT signals. |
| `BLOCKED_ASSET_STRATEGY_PAIRS ∋ ("FUTURES","multi_asset_copytrader")` (line 2719) | All FUTURES picks excluded from policy-clean (2026-05-19, WR=2.5%). |
| `BLOCKED_DIRECTION_TRIPLES ∋ ("FOREX","multi_asset_copytrader","LONG")` (line 3003) | FOREX LONG side blocked. |
| `BLOCKED_SOURCE_SYMBOL_PAIRS ∋ ("multi_asset_copytrader","PL=F"/"GC=F"/"HG=F")` (lines 2471-2473) | Platinum/Gold/Copper picks blocked. |
| **No `("COMMODITY","multi_asset_copytrader")` pair** | COMMODITY picks DO pass the policy-clean filter. |
| `_SOURCE_SYSTEM_SCORES["multi_asset_copytrader"] = -10` (line 5660) | Live score penalty (-10 base). |
| Historical `("COMMODITY","multi_asset_copytrader"): 30` (line 5578) | **REMOVED 2026-05-16** after a swarm deep-dive proved the WR=93.8% PF=20.54 was a pre-dedup artifact (46× over-emission on CT=F cotton). Post-dedup the cell collapsed to WR=40% PF=0.17. |

**Translation:** the policy pipeline does NOT explicitly exclude `multi_asset_copytrader` from COMMODITY. It DID once trust it enough to award a +30 score boost, then quarantined the boost on 2026-05-16 with documented evidence that the headline number was an emission artifact.

---

## 4. The COMMODITY funnel — both pipelines, side by side

### A. Policy-clean (money_ready_verdict) — JSON ledger cohort
```
raw rows (all 32 closed-pick JSON files)                       = 7,398
raw COMMODITY                                                  =    60
  - drop non-closed / null pnl_pct                  (Stage B.1)
  - drop spot-flicker (|pnl| < 2bp, non-CRYPTO)     (Stage B.2)
  - drop dollar-scale artifact (|pnl| > 100%)       (Stage B.3)
  - dedup re-emissions on (strat,sym,dir,date,ep)   (Stage B.4)
after classify_rows() COMMODITY                                =    50
  - Layer 1 flat exclusion                          (Stage C.1)
  - Layer 2 direction-triple                        (Stage C.2)
  - Layer 3 asset-strategy pair                     (Stage C.3)
after _is_policy_excluded COMMODITY                            =    13
  surviving source mix: multi_asset_copytrader=13   ← ALL survivors are this source
  surviving strategy mix: cftc_cot_commercial_signal=11, futures_bb_mean_reversion=2
```

### B. Top-edges (top_edges.py) — MySQL DB cohort, last 90d
```
DB picks last 90d (all classes)                                = 45,432
DB COMMODITY rows (last 90d)                                   =  9,346
DB COMMODITY closed WIN/LOSS                                   =  1,219
DB COMMODITY × multi_asset_copytrader closed                   =    864
  gross WR = 38.66%  gross PF = 1.044   (n=864, NO dedup, NO net)
Top edge cell after 7-dim slicing:
  conf=C0.60-0.70 & rr=RR1.0-1.5 & source=multi_asset_copytrader
  n=137  WR=70.07%  PF=3.27  train_pf=24.27  holdout_pf=2.31
```

### The gap
- 864 DB rows of multi_asset_copytrader COMMODITY (90d) vs 31 in the JSON ledgers (lifetime, pre-policy) vs 13 (post-policy). The biggest single discrepancy is **the JSON ledgers do not contain DB-side scanner output for `multi_asset_copytrader`** — it never writes to `closed_picks*.json`.
- Of the 31 pre-policy JSON `multi_asset_copytrader` COMMODITY rows, 18 get dropped — likely by Layer-3 `("COMMODITY","multi_asset")` (a *different* source) plus dedup; none of the COMMODITY-side blocks target `multi_asset_copytrader` directly.

---

## 5. Verdict (Q6)

**(c) Something else: input-scope mismatch dominates; the policy-clean filter is acting *defensively but reasonably* on the tiny JSON cohort it sees.**

Sub-claims:
- The 71 Bonferroni-passing cells in `top_edges_per_class.json` are computed on a **gross**, **pre-dedup**, **pre-net** universe. The same `multi_asset_copytrader` CT=F COT signal has a 2026-05-16 swarm autopsy on record (quality_gates.py:5575-5581) showing the WR=93.8% PF=20.54 number was a pre-dedup artifact that collapsed to WR=40% PF=0.17 after the 72h COT dedup window. The top_edges cell looks suspiciously like the same pattern — 137 picks at conf 0.60-0.70 / RR 1.0-1.5 with `train_pf=24.27`, `holdout_pf=2.31` (12× PF degradation between halves is itself a red flag the holdout gate at PF≥1.2 fails to catch).
- The verdict pipeline correctly applies M-069 (NET re-judgment after slippage), COT dedup logic via `COT_DEDUP_SYSTEMS`, and three-layer policy exclusion. None of those is wrongly *excluding* a Bonferroni-validated source — they are correctly *not aware of* the DB rows because the JSON ledgers are the verdict's input universe.
- The real bug is upstream: **`build_pf_registry.SOURCE_FILES` does not include the MySQL `trading_picks` table**, so 90d of live DB-emitted picks (especially from DB-only sources like `multi_asset_copytrader` and `cftc_cot_commercial_signal`) are invisible to the money-ready verdict. CLAUDE.md's COMMODITY headline numbers (n=750, PF=1.78) come from `asset_class_health` populated in a *third* path that did once read the DB; M-067 then re-routed `asset_class_health` to read pf_registry.json (JSON-only), which is why today's tile shows n=13/28 instead of n=750+.

---

## 6. Recommended action (Q7)

**Minimum-risk fix — add the DB as a registry source.**

Change scope:
1. `tools/build_pf_registry.py::load_rows()` — add an optional MySQL ingestion path behind an env flag `PF_REGISTRY_INCLUDE_DB=1` (default 0 for a soft rollout). When enabled, ingest `SELECT … FROM trading_picks WHERE status IN ('WIN','LOSS','LOST','EXPIRED','CLOSED','WON') AND created_at >= NOW()-INTERVAL <window>` (window default 180d to comfortably cover the 90d top_edges window plus settling time).
2. Normalize DB columns into the JSON-ledger row shape `(strategy, source_system, symbol, direction, status, pnl_pct, asset_class, entry_price, closed_at)` before appending — `extract_funnel.py` already does this normalization for top_edges, so reuse `fetch_picks()`.
3. **Crucial:** the M-069 NET filter, three-layer policy exclusion, 72h COT dedup, and re-emission dedup MUST run on the merged cohort. This is the whole point — DB-side picks are precisely the ones most exposed to COT over-emission, so they need the same defenses.

**A/B comparison metric (run before/after flipping the flag):**
- For each asset class, log: `n_raw_json`, `n_raw_db`, `n_after_dedup`, `n_after_flicker`, `n_after_policy`, `n_after_net_judgment`, `wr_gross`, `wr_net`, `pf_gross`, `pf_net`.
- Headline expectation: COMMODITY moves from n=13 to ~200-400 surviving rows; the `multi_asset_copytrader` "edge cell" PF should collapse from 3.27 toward ~0.3-1.0 after dedup+net, *consistent with the 2026-05-16 swarm autopsy on the same source*. If it instead stays >1.5 NET, **this is the first real evidence of a COMMODITY edge** and the next step is per-symbol decomposition (CT=F vs ZW=F vs ZS=F) before any production scoring change.
- CI gate: extend `tools/ci_gate_money_ready_vs_registry` (referenced in money_ready_verdict.py:106-107) with a `tools/ci_gate_pf_registry_vs_db` check that warns when DB COMMODITY closes > 10× JSON COMMODITY closes — that drift was the silent precondition for this bug.

**Do not flip without operator review.** The downstream effect of merging the DB feed is large and irreversible inside one snapshot — it will inflate n across every class and may re-promote classes that are currently `INSUFFICIENT_DATA`.

---

## Appendix — files & lines cited

- `alpha_engine/money_ready_verdict.py:94-198, 320-347, 421-505, 642-690, 802-939`
- `tools/build_pf_registry.py:48-90, 118-225, 311-420`
- `tools/audit_pick_funnel/top_edges.py:1-409`
- `tools/audit_pick_funnel/extract_funnel.py` (DB query path)
- `tools/audit_pick_funnel/_db.py` (MySQL DictCursor connector)
- `audit_trail/dashboard_generator.py:5644-5731` (M-067 registry-backed asset_class_health)
- `audit_trail/quality_gates.py:1899` (`BLOCKED_SOURCE_SYSTEMS` — does NOT contain `multi_asset_copytrader`)
- `audit_trail/quality_gates.py:2082-2091` (`COT_DEDUP_SYSTEMS` — DOES include `multi_asset_copytrader` for 72h dedup)
- `audit_trail/quality_gates.py:2719` (`("FUTURES","multi_asset_copytrader")` blocked)
- `audit_trail/quality_gates.py:3003` (`("FOREX","multi_asset_copytrader","LONG")` blocked)
- `audit_trail/quality_gates.py:5575-5581` (2026-05-16 deep-dive — the +30 COMMODITY override REMOVED because pre-dedup artifact; documents PF 20.54→0.17 collapse on the very same source the top-edges file now ranks #1)
- `audit_dashboard/data/pf_registry.json` (raw/dedup/policy-clean/policy-clean-net views; canonical_view = `by_asset_class_policy_clean_net`)
- `audit_dashboard/data/money_ready_verdict.json` (today: COMMODITY n_resolved=28, WR 10.71%, PF 0.31, verdict INSUFFICIENT_DATA, data_source closed_picks)
- `audit_dashboard/data/top_edges_per_class.json` (today: COMMODITY n_closed=1219, n_bonferroni_pass=71, top cell PF 3.27 n=137)
