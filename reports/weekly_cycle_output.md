# Money-Ready Weekly Cycle Output — 2026-06-13 (tick 2)

**Author:** claude-opus (money-ready MASTER LOOP, tick 2) · 2026-06-13 ~17:00Z
**Plan:** `docs/MONEY_READY_MASTER_LOOP_2026-06.md`
**Scope:** READ-ONLY analysis. Every number below is direct-SQL-sourced against `ejaguiar1_stocks` via `tools/db_env.py` (no aggregate-table trust, no peer/subagent stats).
**Builds on tick 1** (`reports/FOREX_CONSENSUS_HONEST_FIRSTTOUCH_2026-06-13.md`, `reports/CRYPTO_RSI5070_US_LEAD_CANDIDATE_2026-06-13.md`).

---

## TL;DR (the three new results)

1. **H1 spot-replay: 20/20 match (100%)** — independent first-touch re-walk of 10 random recent CRYPTO + 10 random recent COMMODITY intrabar-resolved rows agrees with the stored `intrabar_status` on every single row. **H1 stays GREEN.** The honest ledger (`at_signal_outcomes.intrabar_*`) is verifiably faithful — the verdict-grade surface is trustworthy.
2. **The ~2.8x daily-resolution inflation GENERALIZES** (pre-registered H-120):
   - `non_crypto_consensus / COMMODITY`: daily PF **2.67 → honest first-touch 1.28** = **2.09x inflation** (n=135, CI-LB 0.92).
   - `forex_rsi2_mean_reversion`: daily PF **1.26 → honest first-touch 1.07** = **1.18x inflation** (n=120 outlier-clean, CI-LB 0.77). Milder, but honest PF is still sub-edge.
   - Both honest first-touch CI-LBs are **far below the 1.15 promotion bar**. Neither is a money-ready candidate.
3. **DELTA vs tick-1: none material.** Re-running all three MEASURE tools reproduces tick-1 to within rounding (CRYPTO PF 0.727, EQUITY 0.46, COMMODITY 1.048, FOREX 1.102; crypto_rsi5070_us still n=108 / gross PF 1.535). **0/9 classes pass Tier-2 (unchanged).**

**New incident-grade finding (FORWARD):** the **`pead_equity` Jun-14 gate cannot pass** — it has **0 accrued shadow picks** because the `pead-shadow-collector.yml` workflow has been **failing at the "Commit shadow log" step** (last 2 scheduled runs failed: 2026-06-13 01:46Z, 2026-06-12 22:34Z). Signals generate each run but are never persisted. This is an H1/H5 measurement-coverage failure, **not** a strategy verdict.

---

## 1. MEASURE — fresh snapshot vs tick-1 (DELTA = none material)

Re-ran the 3 tools at ~16:49–16:50Z. Source: `at_signal_outcomes.intrabar_*` (first-touch, SL-wins-ties, bad-geometry-excluded).

### `build_intrabar_truth_by_class.py --stdout` (honest per-class ledger)

| class | n | WR% | PF | avg_pnl% | verdict | tick-1 | delta |
|---|--:|--:|--:|--:|---|---|---|
| CRYPTO | 1155 | 32.4 | 0.727 | −0.41 | FAIL | PF 0.73 n=1155 | none |
| EQUITY | 119 | 34.5 | 0.460 | −1.24 | FAIL | 0.46 n=119 | none |
| COMMODITY | 115 | 34.8 | 1.048 | +0.07 | FAIL (n<… both gates) | 1.05 n=115 | none |
| FOREX | 95 | 41.1 | 1.102 | +0.03 | INSUFFICIENT_N | 1.10 n=95 | none |
| MEMECOIN | 77 | 26.0 | 0.580 | −0.45 | INSUFFICIENT_N | — | — |
| ETF | 16 | 0.0 | 0.000 | −2.85 | INSUFFICIENT_N | — | — |
| FUTURES | 16 | 31.2 | 0.490 | −0.60 | INSUFFICIENT_N | — | — |
| BOND | 6 | 33.3 | 2.242 | +0.52 | INSUFFICIENT_N | — | — |

**0/9 non-degenerate classes pass Tier-2.** Tool's lone T2-shaped strategy lead: `forex_rsi2_mean_reversion` n=20 / WR 60% / PF 2.15 — but this is the daily-resolved label inside the cohort; it is **refuted** by the honest first-touch in §3 (and is on the do-not-relitigate list, "forex_rsi2 small-n").

### `stamp_entry_conditions.py --stdout` (forward lane) — DELTA = none

| condition | n | WR% | PF | last30d | note |
|---|--:|--:|--:|---|---|
| `crypto_rsi5070_us` (RSI(14,1h)∈[50,70] ∧ US session) | 108 | 47.2 | 1.535 (gross) | n=56/46.4%/1.39 | the lead, matches tick-1 exactly |
| `luxalgo_short` (luxalgo_confluence ∧ SHORT) | 38 | 71.1 | 2.211 | same | small-n probation watch |
| baseline_CRYPTO | 924 | 32.0 | 0.712 | n=398/28.6%/0.54 | class baseline |
| baseline_FOREX | 43 | 41.9 | 1.480 | n=42/40.5%/1.44 | class baseline |

### `check_one_sided_resolution.py --json` — EXIT 0 (no halt)

Flagged only source-level firehose strategies (`reddit/...`, `youtube/coinbureau`, `cross_sectional_reversal`, `cta_fx_multifactor`) as 100% one-sided in **`at_raw_picks`** — none are the focus strategies, and the honest intrabar cohort for CRYPTO and COMMODITY resolves to **both** sides (CRYPTO TP=374/SL=781; COMMODITY TP=40/SL=75). No one-sided artifact in the focus classes.

---

## 2. H1 STRATIFIED SPOT-REPLAY (the highest-value new check) — 20/20 = 100% match

Method: pulled the 120 most-recent intrabar-resolved (`TP_HIT`/`SL_HIT`) rows per focus class, random-sampled 10 (seed 20260613), and **independently** re-walked the underlying 1h bars (`crypto_ohlcv` for CRYPTO, `stock_ohlcv` for COMMODITY futures) with a from-scratch conservative SL-wins-ties first-touch walker (does NOT import `tools/reresolve_intrabar.replay`). Replay window = `opened_at` → `opened_at + intrabar_horizon_bars × 1h`.

| class | sampled | matched | match rate |
|---|--:|--:|--:|
| CRYPTO | 10 | 10 | 100% |
| COMMODITY | 10 | 10 | 100% |
| **OVERALL** | **20** | **20** | **100%** |

Every stored status reproduced (e.g. CRYPTO `id=857 ETHFIUSDT TP_HIT`, `id=731 QNTUSDT SL_HIT`; COMMODITY `id=380304 PL=F SHORT TP_HIT`, `id=650811 SI=F SHORT SL_HIT` on a 30-bar horizon). **Conclusion: H1 GREEN confirmed structurally, not just by counter.** The honest ledger is a faithful first-touch replay. Nothing in the loop is blocked by a resolver artifact in the focus classes.

---

## 3. GENERALIZATION TEST — does the daily-resolution inflation generalize? (pre-registered H-120)

**Pre-registration (M-107, written before running):** *H-120 — the daily-resolution gross-PF inflation proven on `non_crypto_consensus/FOREX` (daily 2.88 → honest 1.02, ~2.8x) generalizes to other daily-resolved `trading_picks` cohorts. Falsification: honest first-touch PF ≥ 0.8 × stored-daily PF ⇒ that cohort is NOT materially inflated.*

Method: `trading_picks` rows (`closed_at NOT NULL`, `created_at ≥ 2026-01-01`, geometry>0), dedup (symbol, day), first-touch SL-wins-ties (TIME_EXIT at last close), net of cost, cluster-bootstrap CI-LB (`tools/pf_ci_lower.py`, symbol-day clusters), head-to-head vs stored daily `pnl_pct` on the **same** deduped picks.

### (a) `forex_rsi2_mean_reversion` — fxp_price_history daily, 8 majors

- Raw majors-covered picks 1638 → dedup symbol-day 232 → 120 with ≥15 forward daily bars (fxp ends 2026-05-12, so only picks opened by ~mid-April qualify). 2 bad-geometry rows rejected (TP/SL > ±30% off entry — one was an `AUDUSD entry=0.05379, tp=0.694636` wrong-scale row that alone produced a fake +1191% "win" and inflated the raw gross PF to 22.4; this is exactly the contamination the geometry guards exist to catch).
- **Outlier-clean result (n=120, n_eff=120):**

| resolution | PF | CI-LB | WR |
|---|--:|--:|--:|
| **Honest first-touch (net 2bp/6bp)** | **1.067** | **0.767** | 45.8% |
| Stored daily `pnl_pct` | 1.260 | — | — |

**Inflation ratio (daily/honest): 1.18x.** Honest PF 1.07 / CI-LB 0.77 << 1.15 bar, WR < 50%. **No edge under honest resolution** — `forex_rsi2` REFUTED (consistent with its do-not-relitigate listing).

### (b) `non_crypto_consensus / COMMODITY` — stock_ohlcv 1h, =F futures

- Raw commodity picks 738 → dedup symbol-day 136 → 135 with ≥15 forward 1h bars. All =F futures had 1h coverage in `stock_ohlcv` (CL=F, CT=F, GC=F, KC=F, NG=F, PL=F, SI=F, ZC=F, ZS=F, ZW=F). First-touch counts: TP=32 / SL=49 / TIME_EXIT=54.

| resolution | PF | CI-LB | WR |
|---|--:|--:|--:|
| **Honest first-touch (net 3bp, n=135, n_eff=135)** | **1.278** | **0.920** | 48.1% |
| Stored daily `pnl_pct` | 2.668 | — | — |

**Inflation ratio (daily/honest): 2.09x.** This is the clean confirmation of the headline: the daily resolver roughly doubles the commodity-consensus gross PF. Honest CI-LB 0.92 < 1.15 ⇒ **not promotable.** (Note: a 1h-bar walk here is *stronger* than the FOREX daily-bar walk — finer first-touch resolution — and still deflates ~2x.)

### Verdict on H-120
**H-120 SUPPORTED, not falsified.** Both cohorts show honest PF well under 0.8× their stored-daily PF (forex_rsi2 0.85×; commodity 0.48×). The durable rule from tick-1 holds and now has 3 independent confirmations (consensus/FOREX 2.8x, consensus/COMMODITY 2.09x, forex_rsi2 1.18x): **all daily-resolved `trading_picks` gross PF is inflated 1.2–2.8x vs honest first-touch — re-resolve before believing.** The `at_signal_outcomes` intrabar ledger remains the only verdict-grade source.

---

## 4. DIAGNOSE — H1–H5 per focus class (master MD §3)

Scored on direct-SQL evidence this cycle. Rubric: 0 = no problem … 3 = dominant problem.

### CRYPTO (honest n=1155, PF 0.727, WR 32.4%)

| H | score | evidence |
|---|--:|---|
| H1 resolver error | **0** | 10/10 spot-replay match; both-sided (TP 374 / SL 781); dup-rate 18.9% on intrabar cohort |
| H2 backtest-only | 1 | not the binding constraint — the honest ledger IS forward-shaped; bt DB is fantasy (foreclosed tick-1) |
| H3 data/signal supply | 1 | n=1155 is ample; the lead `crypto_rsi5070_us` is the signal-selection answer (n=108, accruing) |
| **H4 mispriced external trust** | **2** | class baseline PF 0.71 / WR 32% — broad emitter mix loses; edge is a thin entry-condition slice, not the class |
| H5 coverage gaps | 1 | coverage good; concentration low (top symbol RENDERUSDT 4.2%) |

**Top hypothesis: H4** — the CRYPTO *class* has no edge; the only positive structure is the `crypto_rsi5070_us` entry-condition (gross 1.53 / net 1.36 / OOS-robust 1.30) which is a selection effect, not a class property. Remedy: keep the entry-condition forward lane accruing to the n≥150 gate; do not size the class.

### COMMODITY (honest n=115, PF 1.048, WR 34.8%)

| H | score | evidence |
|---|--:|---|
| H1 resolver error | **0** | 10/10 spot-replay match; both-sided (TP 40 / SL 75) |
| H2 backtest-only | 1 | consensus daily-PF 2.67 collapses to 1.28 honest (§3) — the "survivor" was a resolution artifact, not a bt-only edge per se |
| **H3 data/signal supply** | **3** | intrabar cohort dedups 115→48 (58% dup rate) and **SI=F is 30% of rows** — thinness + concentration dominate; honest n is effectively ~48 |
| H4 mispriced external trust | 2 | consensus/COMMODITY honest CI-LB 0.92 — the consensus source does not clear the bar |
| H5 coverage gaps | 1 | =F futures have full 1h coverage in stock_ohlcv (good); the gap is *breadth*, not bars |

**Top hypothesis: H3** — COMMODITY is too thin and too concentrated (effectively ~48 independent symbol-day bets, 30% SI=F) for a verdict. The pre-registered n=100 checkpoint is met on raw intrabar count but FAILS on quality (dedup + concentration). Remedy: widen the commodity universe / raise emission breadth in the shadow lane; do not promote consensus/COMMODITY (honest CI-LB 0.92).

---

## 5. FORWARD — pre-registered checkpoint calendar with live n (master MD §7)

| Date | Checkpoint | Bar | Live n (SQL this cycle) | Status |
|---|---|---|---|---|
| **2026-06-14** | `pead_equity` review gate | ≥100 shadow + PF≥1.5 + WR≥50 | **0 shadow picks** (DB: 0 rows any table; shadow log ABSENT) | **CANNOT PASS — emission broken** (see below) |
| ~2026-06-13-16 | COMMODITY n=100 honest | first honest class verdict | honest n=115 (raw) / **48 deduped** / SI=F 30% | **CROSSED on raw; FAILS on quality** — verdict: no edge (PF 1.05; consensus honest CI-LB 0.92) |
| ~2026-06-16-20 | FOREX n=100 honest | same | honest n=95 | **not yet** (~5 short; ETA holds) |
| ~2026-06-25 | `crypto_rsi5070_us` n≥150 | WR≥50 ∧ PF≥1.5 ∧ R1/R2/R3 re-pass | forward n=108 | **accruing** (42 short; ETA ~Jun-25 holds); current net CI-LB 0.95 < 1.15 |

### pead_equity Jun-14 gate — root cause (incident-grade, FORWARD finding)
- DB: `trading_picks` / `at_signal_outcomes` / `at_raw_picks` all return **0 rows** for any `pead`/`earnings` label.
- The sleeve writes to a JSONL shadow log (`alpha_engine/data/pead_shadow_log.jsonl`), which is **ABSENT** on this branch and uncommitted on main.
- `pead-shadow-collector.yml` **runs the collector successfully** (earnings refresh + signal generation pass) but **FAILS at the "Commit shadow log" step** (exit code 1) — last 2 scheduled runs failed (2026-06-13 01:46Z, 2026-06-12 22:34Z; the 2026-06-12 19:44Z manual run was the last success).
- **Implication:** the Jun-14 gate will fail the n≥100 precondition with n=0. This is an **H5 coverage / CI-persistence failure**, NOT a pead_equity performance verdict. Recommend an operator look at the commit step (shared-tree push conflict or empty-diff guard) so the shadow lane actually accrues. The gate should be re-scheduled once the collector persists, not failed-and-killed on a measurement bug.

---

## 6. RATCHET — synthesis, what converged, what to do

**What this cycle proved:**
1. **The measurement layer is sound** (H1 GREEN, 20/20 independent spot-replay). This is the system's most defensible asset and it held under fresh independent attack.
2. **The "candidate carousel" was a resolution artifact, now with three confirmations.** forex_rsi2 (1.18x), consensus/COMMODITY (2.09x), consensus/FOREX (2.8x, tick-1) all inflate under daily resolution. No daily-resolved `trading_picks` PF should be trusted without first-touch re-resolution. This is now a generalized, evidenced rule — not a one-off.
3. **0/9 classes pass Tier-2; no DELTA vs tick-1.** The only honest lead remains `crypto_rsi5070_us` (forward-accruing to n≥150 ~Jun-25; net CI-LB 0.95 today, sub-bar but the only candidate that survives cost + holds OOS + is diversified).

**What circled / what's blocked:**
- COMMODITY's n=100 checkpoint is technically met but quality-fails (effective n ~48, SI=F 30%). Under the anti-circling rule, COMMODITY is on its way to a focus-rotation-out unless breadth improves — flag for the next cycle.
- pead_equity's forward lane is **not accruing** due to a CI commit failure (operator item).

**Pre-registered for next cycle (no action taken this cycle — read-only):**
- H-120 logged as SUPPORTED (daily-resolution inflation generalizes). Add to the do-not-relitigate corpus: `non_crypto_consensus/COMMODITY` daily PF (artifact) and `forex_rsi2` honest refutation.
- Velocity-principle falsification test (Addendum E): when `crypto_rsi5070_us` reaches n≥80 *forward* (it is at 108 forward-lane n), compute forward-PF / replay-PF; pre-registered ≥0.8 holds / <0.5 recalibrate — ready to run at the Jun-25 gate.

**Operator items surfaced (not actioned — read-only cycle):**
1. `pead-shadow-collector.yml` "Commit shadow log" step failing (exit 1) — shadow lane starved. (H5)
2. COMMODITY universe breadth — the class is too thin/concentrated for a verdict.

---

## Reproduce
- MEASURE: `python3 tools/build_intrabar_truth_by_class.py --stdout`; `python3 tools/stamp_entry_conditions.py --stdout`; `python3 tools/check_one_sided_resolution.py --json`.
- H1 spot-replay: random-sample 10 recent `at_signal_outcomes` (intrabar TP/SL) rows per class, re-walk `crypto_ohlcv`/`stock_ohlcv` 1h bars from `opened_at` for `intrabar_horizon_bars`, conservative SL-wins-ties first-touch, compare to stored `intrabar_status`.
- Generalization (H-120): `trading_picks` (closed, 2026+, geometry>0) for `forex_rsi2_mean_reversion` (fxp_price_history daily, 8 majors, strip `=X`, reject TP/SL > ±30% off entry) and `non_crypto_consensus/commodity` (stock_ohlcv 1h, =F); dedup symbol-day; first-touch; `tools/pf_ci_lower.py` net of cost (FX 2bp / JPY 6bp; commodity 3bp) vs stored daily `pnl_pct`.
- DB via `tools/db_env.get_stocks_creds()`. No mutations, no commits, no dashboard generators run.
