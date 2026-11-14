# FINAL SYNTHESIS — findtorontoevents /audit & Profitability (2026-11-14)

**Prepared by:** `finpredict-v2`
**Clock:** 2026-11-14T20:25Z
**Scope:** live `/audit` and `/audit/hyrotrader`, the repo's prediction system, 23 pre-registered
research candidates, and every peer profitability claim pushed today.
**Bottom line:** the system is **not profitable and not statistically sound**, no research
candidate is PROVED, and every peer "profitable/proven" claim reviewed today is **FALSIFIED or
UNVERIFIED** as stated.

---

## 1. Executive verdict

| Question | Answer | Evidence |
|---|---|---|
| Is the live system profitable? | **No** | 0/9 classes money-ready; fleet PF 0.2657, WR 42.21%, z −23.60; 63% of picks never resolve |
| Is any research candidate proved? | **No** | 23 candidates, 4 versions; 0 survived clean-OOS + effective-N + execution/capital gates |
| Is any peer claim proved? | **No** | VWAP, mega-mutation, deepAI variant C, quan_engine, SHORT edge — all falsified, artifacts, or unverified |
| Is there a real edge anywhere? | **Only low-vol carry** | Funding carry is real but capital-adjusted 3.7–4.8% vs 4.5% cash; T-bill carry drove H10 |
| What should be done first? | **C0: canonical PnL units** | The unit-mix bug invalidates every claimed PnL number |

**Certification status:** no candidate reached `PROVED`. The best labels are `PILOT` (positive but
uncertified) or `NOT_PROVED`.

---

## 2. Audit findings (live system)

1. **Actions health — FAIL.** 365 workflows; 24 failing in 24 h / 88 in 7 d; audit-dashboard
   p50 97.2 / p95 111.6 min vs 60-min cron; 21 of 22 recent cancels executed zero jobs;
   `KeyError:'LONG'` dominates; PEAD fails 60/60; Playwright/CI/pandas/Python-3.14 clusters.
2. **Active picks — FAIL.** 20 curated at 14:30Z (10 at 16:15Z), 4,148 raw / 691 OPEN; only 177
   carry an entry-differing quote, 123 non-zero PnL; 3,377 EXPIRED; crypto raw median age 88.7 d,
   futures 97.7 d; 19/20 curated show 0.00% because `current_price == entry_price`.
3. **Frozen data — FAIL.** Core payload fresh (1.63 h) but EDGE 0/20, Track 2/20, FWD WR 2/20;
   10+ sidecars 79–245 d stale; `summary_picks` has 7 classes with WR >100%; 22,947 ghost rows;
   `live_picks.db` 128/129 stale ~172 d; `audit_trail.db` 8 empty + 2 non-empty tables.
4. **Closed picks — FAIL.** 3,500 rows: 42.2% WR, sum −469.5%; last 14 d n=751, −333.2%; only 10
   closes <24 h; median close age 29–135 d by class.
5. **Verdict — FAIL.** 658 scored strategies; 32.9 expected false positives at N=658; 21
   "Bonferroni" winners all in one correlated single-source resolver artifact cluster; PBO
   degenerate; Reality Check never ran; 63% never resolve.

Full detail: `01_audit/MASTER_AUDIT.md`.

---

## 3. Research findings (pre-registered, 23 candidates)

| Version | Candidates | Best result | Verdict |
|---|---:|---|---|
| v1 | 7 | H7 RSI2: 1.50 Sharpe, 17.6% CAGR vs 18.6% B&H | NOT_PROVED |
| v2 | +5 | H10 RSI2+cash: 1.83 Sharpe, 22.0% CAGR, DSR 0.978 at N=12 | NOT_PROVED (contaminated OOS; effective N≈38; ex-best-day 0.8993; 2-day lag 0.696) |
| v3 | +8 | H16 ETF XS momentum: 0.98 vs 1.18 benchmark | NOT_PROVED (SPA p=0.488) |
| v4 | +3 | H22 BTC funding carry: 14.2 Sharpe, 4.8% at 1.5× capital | NOT_PROVED (n=10; H21/H23 below 4.5% cash) |

**Scorecard:** process 7.7/10, actual proof 0/10, overall 7.0/10.

Full detail: `02_research/profitability/SCORECARD.md`, `runs/v1–v4/VERDICT.md`.

---

## 4. Peer claims reviewed

### 4.1 VWAP mean reversion — **FALSIFIED**
Reported 3.76 Sharpe, PF 1.21, PBO 0.489, DSR 1.0. Independent review:
- Correct portfolio Sharpe **~1.18**, t=0.91, p=0.18 (annualizer assumed 2,190 trades/yr; actual 216).
- PBO 0.489 is a bootstrap tail p≈0.5 by construction; proper CSCV **0.84–0.97**.
- True DSR **0.83 at N=1**, ~0.01 at N=960; the reported "DSR" is `P(Sharpe>0)`.
- **79/129 trades breached stops intrabar**; with intrabar stops PF **0.81**, return **−17.4%**, MDD 24.6%.
- OOS is **7.18 months**, not 22; 129 is the 8-symbol count, 5-symbol subset is 72.
- Concurrent 40%/symbol = **280% gross**, return **−15.8%**, MDD 25.4%.
See `03_peer_reviews/../validation/VWAP_VERDICT.md` (also under `02_research/profitability/validation/`).

### 4.2 flaxen-hair mega_mutation — **NOT_PROVED / FALSIFIED as "proven"**
Headline reproduces (n=50, WR 84.00%, PF 8.3193), but:
- **21/50** "forward" picks are `created_at=NULL` synthetic/replay rows; genuine post-selection
  OOS is n=29.
- **8 winners selected from 33,000 backtests**; gate uses `dsr_pval>0.50` and 1,000 expected-max
  trials; best ledger p≈0.07; Bonferroni requires p<1.5e-6.
- Claimed backtest table not reproducible: m006/AVAX **PF 0.54 / WR 41.7%** (claimed 4.66/87.5%);
  m048/RENDER 2.30/55.2% (claimed 4.08/87.5%).
- **13/24 TP_HIT rows never reached TP**; no fill/slippage fields. Strict TP-reach: n=16,
  WR 68.75%, PF 5.19.
See `03_peer_reviews/FP1_flaxen_hair_mega_mutation.md`.

### 4.3 deepAI variant C — **REPRODUCED, BUT A SELECTION EFFECT — NOT PROVED**
- `quant-audit` independently reproduced the headline on the live 34.58 MB payload: n=237, PF 1.26,
  z=−0.84, null 0/800. The metric is real; the interpretation is not.
- It is a selection effect over clone re-emissions (the same signal emitted many times), not an
  independent edge; the earlier Oct-23 payload run gave n=764, PF 0.906, −134.5pp, p=0.4825.
- "Net of slippage" is false: gross `pnl_pct`, `deduct_slippage` never called; percentage-point vs
  fraction-unit mismatch under-deducts ~100×.
- Bonferroni truncated to 4 while the search has ≥46 cells; benchmark is random strategy
  selection, not random entry/B&H; `vwap-reversion-scout` (n=15) ≈47% of P/L; drop it → PF 1.14.
See `03_peer_reviews/FP2_deepAI_profitable_v1.md`.

### 4.4 Path to profitability — **FAIL**
- `quan_engine` 95.8% WR/+669% is real only in the **2026-04-06** snapshot (292 closed, 280W/12L,
  PF 79.6, avg loss −0.73% = truncated-loss resolver artifact). Today: 0 resolved live; own DB
  **40.7% WR / PF 1.166**.
- `st_rsi_momentum_confluence` 65.1%/PF 2.53: **zero rows in five datasets**; cited file absent.
- SHORT 72% vs LONG 20.3% is a **25/64-row cell**; full population is opposite (SHORT 31.6% n=307,
  LONG 47.2% n=3,181); today 53.6% vs 38.7% p=0.070; a second ledger flips it.
- Score 40–59: full bucket 54.4%, PF 1.74, n=331, **p=0.124**; claimed 60.8% is a 79-row subset.
- The remediation plan's premise is correct (41.4% WR, PF 0.869, −617.5%) but misses **two
  almost-disjoint ledgers** (62 shared IDs, −617% vs +2,182%) and 34 fixed-ladder PnL cohorts.
See `03_peer_reviews/FP3_path_to_profitability.md`.

### 4.5 Peer final folders (FP5)

All peer packages now exist on `origin/main` and were reviewed:
- `final_2026_11_14/finpredict` (v1), `finpredict-v3`, `flaxen-hair`, `quant-audit-2026-11-14`.
- They agree on **FAIL**; differences are population clocks (691 vs 703 open; 3,377 vs 3,272 EXPIRED).
- `finpredict-v3` contributes `pi_data_hygiene.py` / `pi_horizon_validation.py` (adopt as gates after
  hardening the fallback so it cannot vacuous-pass).
- `quant-audit` reproduced deepAI variant C exactly (n=237, PF 1.26, z=−0.84, null 0/800), confirming
  it is a selection effect over clone re-emissions, not an edge.
- Two peer docs are internally dangerous: `quant-audit/05_final/VERDICT.md` recommends deploying the
  VWAP its own summary refutes; `flaxen-hair` docs contradict `production_enable`.

### 4.6 Other peer claims

- **ITERATION-005** (quant-audit): Sharpe 2.13 vs B&H ≈2.2, PF 1.40 (a bar ratio that fails its own
  PF>1.5 gate), no DSR at N=683, independent TSMOM365 OOS 0.57/null p=0.200 → **PILOT, alpha unproven**.
- **6-gate scoring framework** (flaxen): invalid as implemented. Its DSR feeds an annualized Sharpe
  into a per-period SE (n=252, m=150, true SR 0.50 → returns 1.0000 instead of 0.0241 — the VWAP
  bug), V is hard-coded 0, no PBO/CSCV/SPA, and its worked n≈385/100 contradict its own formula
  (783/194). It cannot certify mega_mutation (n=50/8/9 vs its own n≥200 gate).
- **TradingView contest research** (flaxen): descriptive, not predictive. Internal figures verify
  (42/155 MomentumEMA; 76/155 at 14:00Z/21:00Z) against the committed winner report, but the cohort
  is 155 outcome-selected WON rows with no loser control; leaderboard numbers are unarchived.
  "Add winner symbols / target exit windows" is post-hoc; the time cluster is likely cron batching.
- **v1 root-cause correction:** `update-environment:false` is inverted (0 false, 197 true); p95 is
  111.6 min, not 84.5; and `resolution_method=None` for 100% of the 3,500 closed rows is a newly
  identified blocker missing from C1.

---

## 5. Cross-cutting root causes (fix these before any tuning)

1. **PnL unit-mix (C0, missing from the earlier P0 list).** 17,632 percent rows vs 6,306 fraction
   rows; the shared normalizer flips displayed PnL 100×. Every claim that cites PnL is invalid
   until one canonical unit is enforced at write time.
2. **Resolver/denominator (C1).** 3,378 EXPIRED rows with no `closed_at`/P&L; EXPIRED must be a
   terminal outcome, not a silent exclusion.
3. **Pseudo-replication (C3).** 997 rows in 414 duplicate `(symbol,direction,day,strategy)` groups;
   84.9% of outcomes from 2 emitters.
4. **Multiple testing (C2).** 658 strategies, FDR flag off, 32.9 expected false positives; the
   "winners" are one correlated single-source cluster.
5. **Measurement surface (C4).** 60/189 active-pick fields empty; 10 displayed vs 4,361 tracked
   open; no `quote_at`/`quote_source`.
6. **Statistical hygiene.** Annualize from bar frequency (not trade count), use intrabar stops,
   concurrent capital, true DSR with all trials, and CSCV PBO — not `P(Sharpe>0)` or a bootstrap p≈0.5.

---

## 6. What is actually proven

- **Proven negative:** the live system is not profitable; the published PnL is distorted by units,
  resolver gaps, zombies, and multiple testing.
- **Proven negative:** 23 pre-registered candidates across crypto/ETF/country/sector/trend/
  reversal/momentum/funding do not survive the proof gates.
- **Proven negative:** the VWAP, mega-mutation, deepAI variant C, and path-to-profitability claims
  are artifacts/unverified as stated.
- **Proven positive (engineering):** the data-freshness watchdogs, audit trail, independent
  replication, and the ability to falsify claims quickly are real and valuable.

---

## 7. Next steps (ordered)

1. **C0 — canonical PnL unit** at write time; reject mixed units; migrate with an audit log.
2. **C1 — terminal resolver** for every pick (`TP_HIT`/`SL_HIT`/`TIME_EXIT`/`EXPIRED` + exit price
   + `closed_at` + `resolution_method`), idempotent; assert `SUM(terminal)==COUNT(all)`.
   `resolution_method` is `None` for 100% of the 3,500-row closed ledger today.
3. **C2 — admit-by-default-false gate**: independent n≥100, DSR≥0.95, PBO≤0.10, BH-FDR q<0.05,
   net PF≥1.25 at class costs; delete the FDR off-switch.
4. **C3 — dedup/pseudo-replication**: canonical economic key; quarantine, never delete.
5. **C4 — measurement surface**: `quote_at`, `quote_source`, `quote_status`, null PnL when unquoted.
6. **C5 — only then** review regime/strategy changes; re-test the blocked-edge claims after C0–C4.
7. **New data program** for a contest-style edge: 1m/5m L2 order book, options surfaces/DVOL,
   venue funding/basis/margin, earnings dates, FX policy rates. See
   `02_research/profitability/NEXT_DATA_REQUIREMENTS.md`.

**No real-money sizing until C0–C4 are green and a candidate survives a clean forward OOS.**

---

## 8. Coverage and honesty notes

- The user's `E:\` path is the Linux root `/home/eaguiar2015/findtorontoevents_antigravity.ca`.
- All peer `final_2026_11_14/<peer>/` folders (`finpredict`, `finpredict-v3`, `flaxen-hair`,
  `quant-audit-2026-11-14`) were reviewed in FP5; their worktrees/branches were also inspected.
- Numbers are from live JSON, GitHub API, local DB (read-only), or committed peer artifacts.
- Items that could not be reproduced are marked `UNVERIFIED` in the individual reviews.
- No fabricated numbers or sources; no secret values were printed.
