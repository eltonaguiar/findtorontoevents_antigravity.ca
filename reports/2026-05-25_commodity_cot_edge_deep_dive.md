# COMMODITY "COT / multi_asset_copytrader" Edge — Deep-Dive Verification

**Date:** 2026-05-25
**Investigator:** Claude (audit-pick-flow)
**Source under audit:** `audit_dashboard/data/top_edges_per_class.json::by_class.COMMODITY` (generated 2026-05-25T04:18:46Z, window=90d, n_closed=1219)
**Cell of interest:** `conf=C0.60-0.70 & rr=RR1.0-1.5 & source=multi_asset_copytrader` — n=137, WR 70.07%, PF 3.274, holdout_pass=true

**TOP-LINE VERDICT: DATA-ARTIFACT — not a real edge.**

The 137-trade cell is one cotton-futures (CT=F) hot streak labelled by a replay-resolver, leaking into 50+ overlapping cell projections. The Bonferroni "correction" treats 673 cells as independent — true independent-test count for the COMMODITY class is ~7. The same filter on FOREX with the same source loses catastrophically, confirming it is symbol-specific, not source-skill.

---

## Numbers ground-truth (DB-side, replicated)

Cohort filter on `ejaguiar1_stocks.trading_picks` (90d): `category='COMMODITY' AND source_system='multi_asset_copytrader' AND confidence∈[0.60,0.70) AND status∈WIN/LOSS U {TP_HIT,SL_HIT,…} AND RR∈[1.0,1.5)`.

| Metric | JSON claim | DB ground truth | Match |
|---|---|---|---|
| n | 137 | **137** | ✅ |
| wins | 96 | **96** | ✅ |
| WR | 70.07% | 70.07% | ✅ |
| PF | 3.274 | 3.274 | ✅ |
| train_n / pf | 36 / 24.27 | 36 / 24.27 | ✅ |
| holdout_n / pf | 101 / 2.31 | 101 / 2.31 | ✅ |
| Total commodity decisive 90d | 1219 | 1219 | ✅ |

Replication is exact. The numbers in the JSON are not fabricated — the *interpretation* is wrong.

---

## Task-by-task

### 1. De-overlap of the 71 Bonferroni-passing cells — **FAIL**

I re-built all cells from the raw 1219 commodity decisive picks (replicating `top_edges.py`). 124 cells passed the `n≥20 ∧ ws≥55% ∧ PF≥1.5` filter (the JSON's `n_holdout_pass=64` / `n_bonferroni_pass=71` is a stricter subset of these). I clustered the top-50 ranked-by-n cells by trade-id Jaccard:

| Threshold | Independent clusters | Cluster sizes |
|---|---|---|
| Jaccard = 1.0 (identical sets) | **25 collapsed pairs** covering 113 cells | many 2- and 3-tuples of dim projections |
| Jaccard ≥ 0.9 | **7 clusters** | 16, 14, 9, 6, 3, 1, 1 |
| Jaccard ≥ 0.5 | **3 clusters** | 25, 15, 10 |

The Bonferroni denominator (673) treats every dim-combo cell as an independent test. The true effective count for COMMODITY is **~3–7**, not 71. Re-correcting the published `wr_z=4.698` against an effective `m_eff=7`:
- Original two-sided p (z=4.70) ≈ 2.6e-6
- Bonf at m=7 → α=0.05/7=7.14e-3; pass = yes, but `−log10(p·m_eff)` drops the "stunning" headline by ~2 orders.

The "71 cells pass Bonferroni" headline is a counting illusion driven by dimension-projection redundancy. **VERDICT: FAIL.**

### 2. Trade-id ground truth — **PASS (numerically), FAIL (composition)**

n=137 matches. **But composition is pathological**:

| Symbol | n | share | WR | PF |
|---|---|---|---|---|
| **CT=F (Cotton)** | **120** | **87.59%** | **79.17%** | 4.361 |
| ZS=F (Soybean) | 12 | 8.76% | 0% | 0.0 |
| ZW=F (Wheat) | 4 | 2.92% | 0% | 0.0 |
| KC=F (Coffee) | 1 | 0.73% | 100% | ∞ |

**This is not a portfolio. It is the cotton-futures track record of one source-system, with 16 wheat/soy losses dragging it.** A 30%+ single-symbol-share flag triggers at 30%; this is **88%**. **VERDICT: FAIL (single-symbol concentration).**

Mean pnl_pct is **+0.0255% per trade** (sum_pos=5.026% / sum_neg=1.535% over 137 trades). With realistic round-trip cost for CT=F futures (commission + slippage typically 2–4 bp), the after-cost edge collapses to roughly 0 to slightly negative. PF 3.27 looks great until you see the wins are 0.04% each.

### 3. Leakage checklist — **MOSTLY PASS, one anomaly**

| Check | Count | Verdict |
|---|---|---|
| (a) `closed_at < created_at` | **1** (by 16,606s ≈ 4.6h) | minor — replay backfill artifact |
| (b) Zero-second hold | 1 (same row as a) | minor |
| (c) Dup `(symbol, created_at, source_system)` | 0 | PASS |
| (d) `EXPIRED` mislabelled `WON` | 0 in this cell (EXPIRED filtered out as `CLOSED_FLAT`) — broader source-pool has 42 EXPIRED rows, none WON | PASS |
| (e) `status=LOST` with `pnl_pct>0` | 0 | PASS |
| (f) Top-symbol concentration | **87.6%** (CT=F) | **FAIL — see §2** |
| (g) train/holdout PF reconciliation | train=36 picks 91.67% WR; holdout=101 picks 62.38% WR | **FAIL — see below** |

**Train/holdout discontinuity (g) decoded**: The 90d window splits at the chronological 60% mark of the FULL commodity decisive pool (not the cell). That split-point is **2026-05-04 ~20:00 UTC**. Of the 137 cell trades:
- Only 36 fall before 2026-05-04 (train) → 91.67% WR / PF 24.27 (3 losses of 0.51% combined vs 33 wins of 0.046% each)
- 101 fall after (holdout) → 62.38% WR / PF 2.31

The "edge" was essentially **born on 2026-05-04** when this source's CT=F volume picked up. The dropping holdout-PF (2.31 vs 24.27) is the natural decay of a small early-window streak hitting a larger, more representative sample. **The 24.27 train PF is statistically meaningless (n=36, almost lossless because three small losses).** **VERDICT: FAIL.**

### 4. Time stability — **FAIL**

| Window | n | WR | PF |
|---|---|---|---|
| Last 30d (bucketed) | 136 | 69.85% | 3.232 |
| 30–60d ago (bucketed) | 1 | 100% | n/a |
| 60–90d ago (bucketed) | 0 | — | — |

**Of 137 supposed-90d-edge trades, 136 fall in the last 30 days.** The "90d edge" is a 30d data point in a 90d denominator. The Bonferroni z-score was calibrated against an n that the time-bucketed reality does not support. **VERDICT: FAIL.**

### 5. OOS probe — **INCONCLUSIVE**

Picks matching the filter and `created_at > 2026-05-25 04:18:46` (build time): **2 total, 0 decisive.** The build window ran to ~21h before this audit; the cell's natural pick-rate is ~4–5/day; nothing has resolved forward yet. **No forward evidence available — recommend re-running this probe in 7–14 days.** **VERDICT: INCONCLUSIVE.**

### 6. Cross-class sanity — **FAIL (catastrophically)**

Same source + conf + RR filter applied to other asset classes (90d):

| Class | n (post-RR) | WR | PF | mean pnl |
|---|---|---|---|---|
| CRYPTO | 0 | — | — | — |
| EQUITY | 1 | 100% | n/a | +0.04% |
| **FOREX** | **585** | **43.59%** | **0.00** | **−190.27%** |

The exact same source/conf/RR cell on FOREX **loses catastrophically**. This proves the "edge" is not a `multi_asset_copytrader` skill at the conf=0.60–0.70 / RR=1.0–1.5 band; it is symbol-specific (CT=F), and FOREX is bleeding from the same source. The headline COMMODITY win is one-symbol survivorship, not a transferable source-systemic effect. **VERDICT: FAIL.**

---

## Per-task verdict summary

| Task | Verdict |
|---|---|
| 1. De-overlap / effective Bonferroni | **FAIL** (71 cells → ~7 independent) |
| 2. Trade-id ground truth | **PASS** numerically / **FAIL** composition (87.6% CT=F) |
| 3. Leakage checklist | **PASS** on most flags / **FAIL** on (f) and (g) |
| 4. Time stability | **FAIL** (136/137 in last 30d) |
| 5. OOS probe | **INCONCLUSIVE** (no resolved fresh picks) |
| 6. Cross-class sanity | **FAIL** (FOREX -190% mean pnl, PF 0) |

## Top-line edge-confidence judgement

**DATA-ARTIFACT.** Specifically:
1. The Bonferroni denominator over-counts ~10× (cell-projection redundancy).
2. The cohort is 88% one symbol (CT=F cotton) on a 30-day hot streak.
3. The wins are 0.04%/trade — within typical futures round-trip cost.
4. The same filter on FOREX from the same source is catastrophic, proving no source-systemic skill.
5. Forward OOS is empty — cannot rescue.

## Recommendations (no DB mutation; reporting only)

1. **Patch `tools/audit_pick_funnel/top_edges.py`**: add (a) per-cell `top1_symbol_share_pct` rejection if >30%; (b) `effective_m` via Jaccard de-overlap before applying Bonferroni; (c) per-class time-bucket stability check (reject if ≥80% of cell trades fall in <30% of the window).
2. **Do not promote** this cell to `updates/` "proven edge" cards or to `passes_smart_gate` until the patch lands and the cell is re-evaluated against the 30d-effective sample.
3. **Document** that `multi_asset_copytrader` on FOREX is a candidate for the mutate-before-kill protocol (PF=0.0 on 585 trades is below the FOREX floor referenced in CLAUDE.md Goal #1).
4. **Re-run OOS probe** on 2026-06-08 (14 days forward) — only if fresh CT=F volume continues to deliver after-cost positive expectancy should this cell be re-examined.

---

## Appendix — query artifact

Source script: `/tmp/commodity_deep_dive.py` (not committed). Raw output: `/tmp/commodity_deep_dive.out.json` (365 lines). Total query time: 0.77s, one MySQL connection, read-only.
