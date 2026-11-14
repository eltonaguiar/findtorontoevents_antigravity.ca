# FP2 — Independent Review: deepAI `PROFITABLE_APPROACH_v1`

**Verdict: FAIL** — the “provably profitable” claim is **FALSIFIED as stated**; the core metrics are
**UNVERIFIED** (not reproducible from the archived evidence); the residual forward-pilot hypothesis is
**PROVISIONAL**.

**Review clock:** 2026-11-14T20:20Z
**Reviewer:** FP2 (independent reproduction / methodology audit)
**Claim under review:** `origin/audit/live-audit-2026-11-14` @ `cc0226bdaf0e6a1d8c3cd67e642e39b2300301d9`
`2026-11-14/deepAI_final_audit_20261114_1809/PROFITABLE_APPROACH_v1.md`
**Constraint:** read-only on repo source. The only file written is this review. No source, data, or branch was modified.

---

## PASS/FAIL — the claim as stated

# **FAIL.**

**Verdict on the claim: FALSIFIED as stated.**
**Status of the core numbers: UNVERIFIED (not reproducible from the archived evidence).**
**Residual hypothesis (“variant C is worth a pre-registered forward pilot”): PROVISIONAL — not proved.**

The walk-forward *procedure* is implemented correctly in the narrow sense (selection uses only
prior months), and the document is unusually candid about its own limits. But the specific
“provably profitable / beats random at p<0.0013 / survives Bonferroni / net of costs” claim fails
on five independent grounds:

1. **The evidence needed to reproduce n=237 / PF 1.26 / +98.7pp / p<0.0013 is not in the archive.**
   The folder contains the script and auxiliary JSON, but **not** the `dashboard_payload.json`
   snapshot it reads, and **not** any output log. The script also implements only variant C — not
   A/B/D, not max drawdown, not the monthly table, not the cost break-even, not the by-class split.
2. **The same committed script, run on the only same-schema payload available in the repo, produces
   the opposite result:** n=764, WR 41.1%, PF **0.906**, **−134.5pp**, randomization p=**0.4825**.
   That payload is an Oct-23 snapshot, not the Nov-14 live pull, so it does not by itself refute the
   exact number — but it shows the result is **not robust to the dataset snapshot**, and the claimed
   PF sits exactly at the median of the null on that data.
3. **The “net of slippage” claim is false for the walk-forward.** `walkforward_v6.py` uses the stored
   `pnl_pct` directly and never calls `deduct_slippage`. `pnl_pct` is the **gross** price return
   (`outcome_resolver.py:1137`); the net value is stamped to a different field. The only call site
   that does apply the model (`dashboard_generator.py:15465`) passes percentage-point values into a
   function documented to expect fractions, so the deduction is ~100× too small.
4. **“+98.7pp vs random” conflates an absolute sum with a benchmark-relative excess.** +98.7pp is the
   arithmetic sum of 237 gross trade returns (+0.416pp/trade). The null benchmark is *random
   strategy selection*, not random entry and not buy-and-hold; no excess-over-null sum is reported,
   and no market benchmark is computed.
5. **The multiple-testing correction is truncated to 4 variants.** The document’s own V0–V6 history
   implies ≥46 cell tests (V1: 8 source + 12 source×class + 26 strategy) plus 3 splits + V4 + 4
   variants. Bonferroni over that family gives family-wise p ≈ 0.06–0.17, not <0.005. See §5.

**What would move this to PASS:** the archived Nov-14 payload + a full output log, a family-wise
max-statistic randomization over the full V0–V6 search, net-of-cost PF recomputed from gross
`pnl_pct` at realistic 0.1–0.2%/trade, and a buy-and-hold benchmark. Without those, this is a
pilot hypothesis, not a proof.

---

## 1. The exact claim, extracted

Source: `PROFITABLE_APPROACH_v1.md:1–92`.

### 1.1 The rule (variant C)

> “Every month, using **only data from prior months**: 1. Group closed trades by `strategy`; keep
> strategies with ≥20 training trades. 2. Rank by training profit factor; take the top 6 with
> training PF > 1.3. 3. Trade those 6 strategies in the next month.” (`:16–20`)

### 1.2 Claim table

| Field | Claim | Where |
|---|---|---|
| Strategy | Monthly top-6 strategy selector, training PF>1.3, ≥20 training trades (variant C) | `:16–20`, `:49–50` |
| Data | live `dashboard_payload.json` `.picks.recent_closed`, 3,500 rows, 2026-02-21 → 2026-11-14 | `:3–4` |
| P/L basis | “P/L net of the system’s slippage model (`deduct_slippage`, M-069)” | `:4–5` |
| Design | Expanding-window walk-forward; selection never sees the test month | `:22` |
| Window | 8 months, Apr→Nov 2026 | `:22`, `:36` |
| n | 237 forward trades | `:26` |
| Win rate | 47.3% | `:27` |
| Profit factor | 1.26 | `:28` |
| Total P/L | +98.7pp | `:29` |
| Max drawdown | −64.1pp (trade-weighted) | `:30` |
| Benchmark | Random 6-strategy selection per month | `:31`, `:64` |
| Randomization p | 0/800 → p<0.0013 | `:31` |
| Bonferroni | 4 variants → p<0.005, “SURVIVES” | `:32` |
| Cost buffer | Breakeven extra cost 0.416%/trade | `:33` |
| Expectancy | +0.42%/trade | `:34` |
| By class | ETF n=120 PF 1.21 +26.5pp; EQUITY n=112 PF 1.30 +73.1pp | `:39–41` |
| Other variants | A n=225 PF 1.18 +71.8 (p=0.049); B n=81 PF 1.32 +46.2 (p=0.044); D n=243 PF 1.19 +77.6 (p=0.040) | `:47–53` |
| Contributors | vwap-reversion-scout n=15 PF 3.74 +46.9; rs-breakout-scout n=110 PF 1.26 +35.3; donchian n=28 PF 1.39 +26.5; mtf n=19 PF 1.50 +10.4; gap-and-go n=1 +11.7 | `:43–45` |

### 1.3 What the claim does *not* say (credit where due)

The document explicitly disclaims T2 certification: PF 1.26 < 1.5, WR 47.3% < 50%, single dataset,
no regime out-of-sample, fragile contributors, and “walk-forward null is random *strategy selection*,
not a fully independent market null” (`:59–66`). It proposes a pre-registered forward pilot with
kill criteria (`:67–78`). That framing is honest. The review below judges the **headline proof**,
not the pilot proposal.

---

## 2. Evidence inventory — what is actually reproducible

`git ls-tree` on the branch shows this folder:

```
PROFITABLE_APPROACH_v1.md
TODO_profitable_approach.md
AUDIT_FINAL.md
notes/01_actions_health.md … 05_verdict.md
notes/playwright_live_js_report.md
notes/evidence/
  closed_stats.json          (1,644 B)
  v1_cells.json              (3,624 B)
  wf_last_seen.json         (22,758 B)
  px_binance_sample.json       (304 B)
  px_yahoo.json              (1,412 B)
  symbol_groups.json         (1,765 B)
  repricing_open_picks.json (164 KB)
  walkforward_v6.py           (78 lines)
```

**Missing from the archive:**

- The `dashboard_payload.json` used by `walkforward_v6.py` (the script’s `sys.argv[1]`).
- Any captured stdout / result JSON from the walk-forward.
- Code for variants A, B, D; for max drawdown; for monthly PF; for the cost break-even; for the
  by-class split; for the top-contributor table; for the “alive-only” refinement.
- Price history for a buy-and-hold benchmark (only point-in-time snapshots exist).

Consequence: **the core metrics are UNVERIFIED.** `walkforward_v6.py` can reproduce *only* the
variant-C aggregate and its random null, and only if the reader has the exact payload.

---

## 3. Recomputation

### 3.1 Exact Nov-14 claim → **UNVERIFIED**

The live Nov-14 payload is not archived. The checked-in `audit_trail/data/dashboard_payload.json`
in the repo has the same schema and **exactly 3,500** `recent_closed` rows, but its date range is
**2026-02-21 → 2026-10-23**, not 2026-11-14 (file mtime 2026-10-23T02:04). It is a stale snapshot,
so the exact `n=237 / PF 1.26 / +98.7pp / p<0.0013` cannot be recomputed from it.

I state the exact claim as **UNVERIFIED**, not “wrong”.

### 3.2 Same script, available payload — a robustness cross-check

Command actually run (read-only):

```bash
cp .../walkforward_v6.py /tmp/fp2run/
python3 /tmp/fp2run/walkforward_v6.py \
  /home/eaguiar2015/findtorontoevents_antigravity.ca/audit_trail/data/dashboard_payload.json
```

Output:

```
VARIANT C walk-forward: n=764 WR=41.1% PF=0.91 sum=-134.5pp z=-4.92
randomization null: 386/800 = p=0.4825
```

I then re-implemented A/B/C/D from the document’s definitions (the committed script omits them) and
instrumented the null. Results on the same stale payload:

| Variant | n | WR | PF | Σpp | z (WR vs 50%) | maxDD (sum, close order) |
|---|---:|---:|---:|---:|---:|---:|
| A: top-6, PF>1.3, n≥10 | 811 | 40.7% | 0.897 | −153.8 | −5.30 | −279.7 |
| B: top-3, PF>1.3, n≥10 | 88 | 43.2% | 0.928 | −12.9 | −1.28 | −73.1 |
| **C: top-6, PF>1.3, n≥20** | **764** | **41.1%** | **0.906** | **−134.5** | **−4.92** | **−285.2** |
| D: top-6, no threshold, n≥10 | 811 | 40.7% | 0.897 | −153.8 | −5.30 | −279.7 |

Monthly detail for C (selection rotates heavily):

| Month | Train n | Test n | Selected strategies | Sel. n | PF | Σpp | WR |
|---|---:|---:|---|---:|---:|---:|---:|
| 2026-04 | 187 | 178 | (none qualified) | 0 | — | 0.0 | — |
| 2026-05 | 365 | 173 | rs-breakout-scout, crypto_liquidity_wick_reversal_v1 | 31 | 2.639 | +42.0 | 64.5% |
| 2026-06 | 538 | 469 | rs-breakout-scout, crypto_liquidity_wick_reversal_v1, vol-contraction-scout, forex-rsi-ema-scout, intermarket-flow-scout, atr_percentile_gate | 31 | 1.168 | +8.2 | 48.4% |
| 2026-07 | 1,007 | 194 | battleground_ml_relaxed_mut, rs-breakout-scout, luxalgo_confluence, mtf-align-scout, prediction_market_consensus, crypto_liquidity_wick_reversal_v1 | 21 | 0.570 | −14.0 | 33.3% |
| 2026-08 | 1,201 | 178 | battleground_ml_relaxed_mut, luxalgo_confluence, mtf-align-scout, prediction_market_consensus, crypto_liquidity_wick_reversal_v1, donchian-stock-breakout | 12 | 2.375 | +27.6 | 58.3% |
| 2026-09 | 1,379 | 970 | battleground_ml_relaxed_mut, luxalgo_confluence, vwap-reversion-scout, mtf-align-scout, prediction_market_consensus, donchian-stock-breakout | 641 | 0.903 | −113.7 | 40.6% |
| 2026-10 | 2,349 | 1,151 | battleground_ml_relaxed_mut, vwap-reversion-scout, prediction_market_consensus, crypto_liquidity_wick_reversal_v1, momentum_breakout, donchian-stock-breakout | 28 | 0.345 | −84.6 | 17.9% |

Null distribution (800 draws, variant C null): kept 800/800; null n median 250 (min 135, max 1,466);
null PF median **0.901**, p90 **1.060**, max **1.352**. Observed C PF **0.906** → p=**0.4825**,
i.e. **at the 50th percentile of the null**.

**Interpretation.** The stale payload is not the claimed dataset, so this is not a refutation of
n=237/PF 1.26. It is, however, a direct demonstration that:

- the procedure’s output flips from PF 1.26/+98.7pp to PF 0.91/−134.5pp across snapshots of the
  same schema;
- the selection set is highly unstable month-to-month (high-volume `luxalgo_confluence` /
  `battleground_ml_relaxed_mut` / `prediction_market_consensus` enter in Sep–Oct and bleed);
- the claimed early-month PFs are *close* to this snapshot (May 2.63 vs 2.639; Jul 0.50 vs 0.570;
  Jun 1.02 vs 1.168), while Sep/Oct diverge sharply (1.28 vs 0.903; 1.49 vs 0.345). That pattern
  suggests shared data lineage with a later re-resolution of the recent months, and it makes the
  Nov-14 divergence the single most important thing the archive should have documented — but did not.

### 3.3 Internal arithmetic of the claim — mostly self-consistent

Using the document’s own numbers:

- `+98.7pp / 237 = +0.4165pp/trade` ✓ matches +0.42%/trade.
- PF 1.26 with WR 47.3% ⇒ win/loss ratio = `1.26 × (1−0.473) / 0.473 = 1.404` ✓ matches 1.41.
- Kelly `f = p − q/b = 0.473 − 0.527/1.41 = 0.099` ✓ matches “full Kelly ≈10%”.
- ¼ Kelly = 2.5%; `−64.1pp × 2.5% = −1.60%` ✓ matches “≈1.6% bankroll drawdown”.
- Breakeven cost: PF=1 ⇔ Σ(x−c)=0 ⇔ c = mean = **0.4165pp** ✓ matches 0.416%/trade.

The arithmetic is sound. The problems are the inputs, the benchmark, and the correction family —
not the algebra.

### 3.4 Internal contradictions in the claim

These are contradictions *within the document*, independent of the data:

1. **“4 of 8 months negative”** (`:65`) contradicts the monthly PF list (`:36–37`), which shows only
   July below 1.0 (May 2.63, Jun 1.02, Jul **0.50**, Aug 1.74, Sep 1.28, Oct 1.49, Nov 1.72).
   For a monthly window, PF>1 ⇔ Σ P/L>0 (wins and losses partition the trades), so 6 of 7 listed
   months are positive. “4 of 8 negative” is mathematically inconsistent with the table.
2. **“four consecutive improving months”** (`:37`, headline `:9`) is contradicted by the same series:
   Aug **1.74** → Sep **1.28** is a decline; Oct 1.49 → Nov 1.72 is two months, not four.
3. **“8 months, Apr→Nov”** but only **7** monthly figures are listed (May–Nov). April is omitted;
   on the available payload variant C selects **zero** strategies in April. So “8 true walk-forward
   months” is really 8 evaluation blocks, one of which contributes zero trades.
4. **By-class n sums to 232, not 237** (ETF 120 + EQUITY 112), with the text adding “CRYPTO appears
   once” → 233; 4 trades are unaccounted. By-class Σpp = 99.6, not 98.7 (≈−0.9pp in the omitted
   trades). Plausible, but the table is incomplete.

None of these alone is fatal; together they show the headline is not a clean, audited summary.

---

## 4. Methodology audit

### 4.1 Walk-forward design — structurally correct, but not 8 independent OOS months

Code (`walkforward_v6.py:31–45`):

```python
for m in months:
    if m <= '2026-03': continue
    train = [p for p in rows if cdate(p)[:7] < m]
    test  = [p for p in rows if cdate(p)[:7] == m]
    ...
    picks = pick_fn(agg)
    fwd += [p for p in test if str(p.get('strategy')) in picks]
```

- **Correct:** test-month trades are never in the training set; selection is per-month, prior data only.
- **Not independent:** the training window is **expanding**, so consecutive test months share almost
  all training data. The selection is highly autocorrelated across months (the same few strategies
  recur). This is one expanding-window backtest with 8 evaluation blocks, not 8 independent
  out-of-sample periods. The document calls them “8 true out-of-sample months” (`:83`); that
  overstates independence.
- **April:** on the available payload the C rule selects nothing in April (`n≥20` + PF>1.3 yields no
  candidates). The claim’s monthly list silently omits April, consistent with 0 trades, but then
  “8 months” is a block count, not a traded-month count.

### 4.2 Variant C selection — the winner’s curse is not corrected

- C is the **maximum** of A/B/C/D on both PF (1.26) and Σpp (+98.7). A, B, D are 1.18/1.32/1.19 and
  p=0.049/0.044/0.040. The only difference between C and A is the training-sample floor
  (**n≥20 vs n≥10**), which changes the candidate pool and flips +71.8pp → +98.7pp. That is a large
  sensitivity to an arbitrary threshold.
- The document says C was “pre-specified before seeing its result” (`:16`) and that all four were
  reported (`:47`). If true, that is better than cherry-picking. But the *broader* V0–V4 search was
  not pre-registered, and C is the survivor of that larger search (see §5).
- On the available payload, C and A/D are statistically indistinguishable (PF 0.906 vs 0.897), so the
  n≥20 threshold is not a robust discriminator.

### 4.3 Costs — the walk-forward is gross, not net

This is the most concrete falsification of a stated claim.

- The claim: “P/L net of the system’s slippage model (`deduct_slippage`, M-069)” (`:4–5`).
- `walkforward_v6.py` reads `p['pnl_pct']` at `:24`, `:44`, `:53`, `:69`. It **never imports or calls
  `deduct_slippage`**.
- `outcome_resolver.py:1137` sets `pick["pnl_pct"] = round(pnl_pct, 6)` to the **gross** price
  return; `stamp_pick_net_pnl` writes `_pnl_pct_net` to a **separate** field
  (`charter_slippage.py:90–108`) and does not overwrite `pnl_pct`.
- The only place the dashboard applies the model to the verdict aggregate is
  `dashboard_generator.py:15465`:
  ```python
  pnl = deduct_slippage(float(p.get("pnl_pct", 0) or 0), ac)
  ```
  But `pnl_pct` in the payload is in **percentage points** (median |pnl_pct| = 2.59, p90 = 6.58,
  sample `[-2.0, -2.0, -3.5947, …]`), while `deduct_slippage` subtracts `round_trip_bps/10000`
  (0.0008) as a **fraction**. So the call deducts **0.0008pp**, not the intended **0.08pp** — a
  ~100× under-deduction. The M-069 fix corrected the fraction-vs-percent bug in the function, but
  this call site still feeds percentage points.
- Therefore the walk-forward’s +98.7pp / PF 1.26 is **gross**. At the document’s own “typical equity
  cost ~0.1–0.2%” round-trip, 237 trades cost **~24–47pp**, leaving roughly **+52 to +75pp** and a
  PF materially below 1.26. The document’s 0.416%/trade “breakeven buffer” is real arithmetic, but
  it is a buffer **from gross**, not an “extra” buffer after a cost model that was actually applied.

**Credit:** the breakeven calculation itself is correct (PF=1 ⇔ mean net = 0). The error is labelling
the result “net” when no cost was subtracted in the walk-forward.

### 4.4 Benchmark — neither random entry nor buy-and-hold

- The null is **random 6-strategy selection per month** (`walkforward_v6.py:64–68`): it samples 6
  strategies with ≥20 training trades, ignoring the PF>1.3/top-6 ranking. It tests “does ranking by
  trailing PF beat random strategy choice?” — a narrow question.
- It is **not** random entry (same trades, random dates/directions) and **not** buy-and-hold. There
  is no market-beta adjustment.
- The forward set is **51% ETF + 47% EQUITY**, long-biased, over a period when the equity market
  rose (the audit’s own snapshot: SPY 754.37, NVDA 162.85, QQQ 679.89 — `px_yahoo.json`). A passive
  long ETF/equity basket could plausibly produce a large positive sum without any selection edge.
- **+98.7pp is an absolute cumulative sum, not an excess over the benchmark.** The document never
  reports the null’s mean/median Σpp or the difference C − null. On the available payload the null
  median PF is 0.901 and C is 0.906 — no excess. The phrase “+98.7pp vs random” is not supported by
  the reported statistics: +98.7pp is C’s sum; the p-value is a PF test, not a sum test.
- The document’s caveat #5 (`:64`) admits the null is not a fully independent market null. That is
  the right caveat, but the headline still says “beats random selection decisively”.

### 4.5 Multiple testing — the correction is truncated

The claim: “Bonferroni (4 variants tested) — p<0.005 — SURVIVES” (`:32`).

What was actually searched, from the document’s own iteration log (`:89–92`) and TODO:

| Stage | Tests |
|---|---:|
| V0 baseline | 4 strategies checked |
| V1 cell search | **8 source + 12 source×class + 26 strategy = 46 cells** |
| V2 split-sample | 3 split points |
| V4 ensemble + OOS | ≥1 procedure |
| V5 refined rules | **4 variants (A/B/C/D)** |
| **Minimum family** | **≥54** |

Bonferroni arithmetic with the reported p:

- 4 tests: `1−(1−0.0013)^4 ≈ 0.0052` — the claimed “survives”.
- 46 tests: `1−(1−0.0013)^46 ≈ 0.058`.
- 54 tests: `1−(1−0.0013)^54 ≈ 0.068`.
- Using the **95% upper bound** of 0/800 (≈0.00374) × 46 ≈ **0.17**.

So the result does **not** robustly survive correction over the family the document itself
describes. It survives only over the hand-picked 4-variant family. The 46 V1 cells are correlated,
so the effective number is below 46 — but with 20 effective tests the family-wise p is already
≈0.026, and with 38 it is ≈0.048. The honest conclusion is **marginal at best**, not “p<0.005
survives”.

Additional correction issues:

- The null test is **per-variant**, not a **max-statistic** (Westfall–Young) test over A/B/C/D. The
  correct family-wise randomization would, for each null draw, compute the max PF across all four
  procedures and compare to max(observed A,B,C,D)=C. That yields a larger p than 0/800.
- The p-value is computed on the **PF** statistic while the headline reports the **sum** (+98.7pp).
  These are different statistics; the p does not directly test the +98.7pp.

### 4.6 Overlapping windows and pseudo-replication

- Test months are disjoint, so there is no direct train/test overlap. But training windows are
  expanding and nested: month M's training set contains month M−1's training set. Selection
  persistence across months means the 8 blocks are not independent draws.
- The 237 trades are **not 237 independent observations**. They come from ~6 strategies × 8 months,
  with many trades per strategy and repeated symbols. Trades within a strategy/symbol are
  correlated. The binomial WR z (`walkforward_v6.py:56`) and the PF comparison treat trades as iid;
  effective n is on the order of the number of strategy-month units (~48) or fewer.
- The randomization samples at the **strategy** level, which partially preserves clustering — a
  point in its favour — but it does not correct the observed statistic’s variance for within-strategy
  correlation. The p is therefore anti-conservative relative to a trade-level iid test and still
  conditional on the 8 fixed months.

### 4.7 Data snooping — two layers, only one corrected

- The strategy universe is the output of a large discovery process: `alpha_engine/config.py` has
  **361** `STRATEGY_FAMILIES` (verified by import), plus baby strategies and mutation variants
  (the deepAI doc says 285 baby files; the branch has **227** `.py`; our MASTER_AUDIT counts 84 baby
  meta-strategies + 231 hand mutations). The strategies were selected/evolved on the same kind of
  ledger data.
- Variant C is a **second** selection layer: rank already-selected strategies by trailing PF. The
  random-strategy null corrects only this second layer. It does **not** correct for the first layer
  (the 361+ strategy discovery), which is the dominant source of false positives in this system.
- The available-payload run illustrates the mechanism: strategies that look good in training
  (`luxalgo_confluence`, `battleground_ml_relaxed_mut`) are selected in Sep–Oct and then lose
  heavily — textbook regression to the mean / data snooping.
- The same audit found `69/80` strategies flagged `OVERFIT_LIKELY` (`live_anti_overfit_audit.json`),
  PBO computed on **20** observations (the claim says 21), and the White Reality Check **never ran**
  (`arch` missing). That is the environment in which variant C was selected; it is not a clean
  discovery sample.

### 4.8 Data quality of the outcome variable

The outcome variable is the system’s own `pnl_pct`, not an independent intrabar replay. The same
audit (`AUDIT_FINAL.md`) documents:

- 81% of open picks show 0/None P/L; true mean −1.80% vs claimed; aggregate loss understated ~10×
  (`AUDIT_FINAL.md:42–60`).
- 78.6% of `active_raw` are `EXPIRED` with pnl=0; the time-expiry resolver writes `pnl_pct=0`
  instead of close-vs-entry (`AUDIT_FINAL.md:66–68`, `reports/zero_pnl_data_pipeline_audit_2026-06-05.md`).
- Intrabar replay reclassifies **28–100%** of “TP hits” as actual SL hits
  (`reports/PAPER_PILOT_RESOLVER_FAIL_2026-06-05.md`).
- The deepAI audit itself says external market data verifies *prices*, not the system’s intrabar
  fills (`AUDIT_FINAL.md:152–153`).

`walkforward_v6.py` filters only `isinstance(pnl_pct, (int,float))`; it does not exclude zero-P/L
expired rows. On the available payload there are 11 zeros and they are not a problem at scale, but
the DOC’s own “81% fake 0% P/L” note (`:82`) means the live Nov-14 closed set may contain zeros.
Zeros do not affect PF (they are excluded from GP/GL) but they **inflate n** and **depress WR** —
both are certification metrics. The claim does not report how many of the 237 are zero-P/L rows.

### 4.9 p-value adequacy

- 0/800 with add-one correction → **p ≈ 1/801 = 0.00125**. Reporting “p<0.0013” is defensible as a
  randomization point estimate.
- But the **95% upper confidence bound** for 0/800 is `1 − 0.05^(1/800) ≈ 0.00374` (rule of three
  ≈ 3/800). So the data are consistent with a true p as high as ~0.0037. Multiplying that by 4 gives
  **0.015**, which does **not** survive Bonferroni at 0.05. The “survives Bonferroni” conclusion is
  within the resolution noise of an 800-draw null.
- The null is **conditional on the 8 months and the fixed dataset**. It is an in-sample
  randomization p, not a population p-value. It supports “C beat random strategy selection in this
  sample”, not “C is provably profitable”.
- `walkforward_v6.py:70` keeps a null draw only if `len(rf) >= 30`. That conditions the null on
  sample size (on the available payload all 800 draws passed, so the effect is nil there, but it is
  a latent selection on the null). The PF statistic is also not sample-size normalized, so null
  draws with n=135 vs n=1,466 are compared on unequal footing.

### 4.10 Latent look-ahead bug in the date parser

`walkforward_v6.py:27`:

```python
def cdate(p):
    return str(p.get('closed_at') or p.get('exit_date') or '9999')[:10]
```

Rows with no date get month `'9999'`. In the loop (`:34`) `'9999' > '2026-03'`, so those rows become
a “test month” whose training set is **all rows** — a look-ahead leak — and they are included in the
forward set. The available payload has **0** undated rows, so this is latent, not demonstrated. The
live Nov-14 payload was not archived, so it cannot be ruled out. Any row with `closed_at=None` and
`exit_date=None` would be silently traded with full-sample training.

### 4.11 Contributor fragility (the claim’s own numbers)

The document flags this (`:63`) but the headline does not reflect it. Arithmetic from the claim’s
own aggregate:

- Total: n=237, PF=1.26, Σ=+98.7 ⇒ GL=379.6, GP=478.3.
- `vwap-reversion-scout`: n=15, PF=3.74, Σ=+46.9 ⇒ GL=17.1, GP=64.0. It contributes **47.5%** of the
  total P/L on **6.3%** of the trades.
- Drop it: GP=414.3, GL=362.5 ⇒ **PF 1.14**, Σ=+51.8, n=222.
- Drop it **and** `gap-and-go-stocks` (n=1, +11.7): GP=402.6, GL=362.5 ⇒ **PF 1.11**, Σ=+40.1, n=221.
- Drop only `rs-breakout-scout` (n=110, PF 1.26, +35.3): PF stays ≈1.26 (because its PF equals the
  aggregate PF), so the edge is not solely rs-breakout — but it is heavily dependent on a 15-trade
  VWAP strategy and a 1-trade contributor.

A result whose PF falls from 1.26 to 1.11 after removing two flagged contributors is not a robust
“proof”; it is a fragile pilot.

---

## 5. Multiple-testing / selection — the decisive section

| Correction | Family size | Family-wise p from 0.00125 | Verdict |
|---|---:|---:|---|
| Reported | 4 | 0.0050 | “survives” (by construction) |
| V1 cell search only | 46 | **0.056** | fails 0.05 |
| V0–V5 minimum | 54 | **0.065** | fails 0.05 |
| 4 × 95% upper bound | 4 | **0.015** | fails 0.05 |
| 46 × 95% upper bound | 46 | **0.158** | fails badly |

- The document’s “Bonferroni for 4 tested variants” is **true for 4** and **false for the search it
  describes**. The 4-variant family is the *output* of the search, not the search itself.
- The V1 cell search alone (46 cells) pushes the family-wise p above 0.05. Adding V2/V4/V5 makes it
  worse. Correlation among cells reduces the effective count, but the claim provides no effective-N
  calculation, and the 95% upper bound makes even the 4-variant correction fragile.
- The correct procedure is a **max-statistic / Westfall–Young randomization** over all tried
  configurations, or a **deflated Sharpe / PBO** on the selected rule. Neither was run. The system’s
  own anti-overfit audit has PBO on 20 observations and no Reality Check (`arch` missing), so it
  cannot supply the missing correction either.

**Conclusion:** the “p<0.005 survives Bonferroni” headline is not supported once the correction family
is the one the document itself enumerates. This is the single strongest reason the claim is
FALSIFIED as stated.

---

## 6. Comparison to our 23-candidate program and the VWAP falsification

### 6.1 Our program (`research/profitability/HYPOTHESES.md`, N=23)

- 23 pre-registered hypotheses (H1–H23); **0/23 PROVED**; all `NOT_PROVED`.
- Our gates: clean train (2018–2023) / OOS (2024–2026), 5–10 bps costs, DSR, PBO/CSCV, SPA/Reality
  Check, n≥30, adversarial review. H10 mechanically passed but was downgraded for post-hoc
  selection, effective N≈38, ex-top-1/day fragility, 2-day lag, and contaminated OOS.
- DeepAI’s result fails our gates on every axis that matters:
  - **Data purity:** uses the system’s own `pnl_pct`, not independent intrabar replay; the same
    audit documents resolver zero-P/L and 28–100% TP→SL reclassification.
  - **n≥100:** n=237 nominal, but effective n is strategy-month units (~48) and the top contributor
    is n=15.
  - **PF>1.5:** 1.26 (gross; lower net).
  - **Bootstrap CI:** not computed.
  - **Multiple testing:** 4 instead of ≥46; no DSR/PBO/SPA.
  - **OOS walk-forward:** expanding-window on one dataset; no clean forward holdout; no regime out-of-sample.
  - **Costs:** gross, not net.
  - **WR≥50%:** 47.3%.

By our standard, this is a **pilot hypothesis**, not a proved edge — which is exactly what the
document says in its caveats, but not what its headline says.

### 6.2 The VWAP falsification (`research/profitability/validation/VWAP_VERDICT.md`)

Our independent VWAP review falsified a different peer claim (regime-filtered 4h crypto VWAP mean
reversion) on: annualization error (Sharpe 3.76 → ~1.18, t=0.91), PBO 0.489 → 0.84–0.97, DSR 1.0 →
0.83/0.01, 79/129 intrabar stop breaches (PF 1.21 → 0.81, −17.4%), OOS 7.18 months not 22, 5-symbol
n=72 not 129, 280% gross concurrency, and PF<1 at 25bps.

The deepAI claim is **not the same strategy** (`vwap-reversion-scout` here is a system-ledger scout,
not the 4h crypto peer strategy), but the failure mode is the same family:

- a **small-n VWAP contributor** (n=15, PF 3.74) supplies ~47% of the claimed P/L;
- the cost buffer is computed from gross returns;
- the “OOS” is an expanding-window backtest, not a clean forward record;
- the correction family is understated.

Our VWAP lesson applies directly: **do not certify a VWAP-flavoured edge from a short, gross,
single-dataset window with a post-hoc stop/cost model.** The deepAI document is more honest than the
VWAP peer (it labels the result “pilot-grade” and flags n=15), but it still overstates the proof.

### 6.3 Side-by-side

| Dimension | DeepAI variant C | Our 23-candidate program | VWAP peer claim |
|---|---|---|---|
| Data | system `pnl_pct` ledger, one snapshot | independent OHLCV, multi-year | 4h crypto OHLCV, 730d |
| Selection | top-6 trailing PF, 4 variants | 23 pre-registered hypotheses | parameter grid |
| OOS | expanding-window, 8 blocks | 2024–2026 holdout | mislabelled 7.18m |
| Costs | gross (claimed net) | 5–10 bps | 50 bps claimed, fails at 25 |
| Multiple testing | 4 (truncated) | DSR/PBO/SPA | DSR/PBO misapplied |
| Best metric | PF 1.26, WR 47.3%, +98.7pp | 0/23 proved; best H10 downgraded | PF 1.21 → 0.81 intrabar |
| Verdict | **FALSIFIED as stated; pilot PROVISIONAL** | **NOT PROVED (0/23)** | **FALSIFIED** |

---

## 7. Verdict

| Proposition | Verdict | Basis |
|---|---|---|
| “Variant C is a **provably profitable** approach” | **FALSIFIED** | Gross, not net; +98.7pp is absolute, not benchmark-relative; PF 1.26 < T2; no independent OOS |
| “Beats random selection at **p<0.0013**” | **UNVERIFIED / not robust** | Exact data absent; 0/800 upper bound ≈0.0037; conditional on 8 months; effective n ≪ 237 |
| “Survives **Bonferroni**” | **FALSIFIED** | Only over 4 variants; over the document’s own ≥46-cell family, p≈0.06–0.17 |
| “P/L **net of slippage**” | **FALSIFIED** | Script never calls `deduct_slippage`; `pnl_pct` is gross; call site is 100× under-deducting |
| “+98.7pp **vs random**” | **FALSIFIED as wording** | +98.7pp is C’s absolute sum; no null-sum/excess reported; benchmark is random strategy, not random entry/B&H |
| “8 true OOS months / 4 consecutive improving / 4 of 8 negative” | **FALSIFIED** | Internal contradictions; April omitted; Sep decline; only July <1.0 |
| “Variant C is a **pilot candidate** worth a pre-registered forward test” | **PROVISIONAL** | Reasonable as a hypothesis; not proved; requires clean forward ledger, net costs, B&H benchmark, full family correction |
| Core metrics n=237 / PF 1.26 / +98.7pp / MDD −64.1pp | **UNVERIFIED** | Payload and output not archived; script covers only C |

**Bottom line:** the document is a useful, honest *pilot proposal* wrapped in an overclaimed
*proof*. The walk-forward mechanism is correct, the arithmetic is mostly self-consistent, and the
caveats are real. But the three claims that make it a “profitable approach” — **net of costs**,
**beats a benchmark**, and **survives multiple testing** — do not hold. On the only same-schema
payload available, the procedure returns PF 0.906 / −134.5pp / p=0.48. The correct disposition is:
**do not cite this as a proved edge; keep variant C only as a pre-registered forward pilot, with
gross-to-net cost accounting, a buy-and-hold benchmark, and a full-family correction.**

---

## 8. UNVERIFIED (explicit)

1. **Nov-14 payload** and its exact 3,500-row window (2026-02-21 → 2026-11-14). Available repo copy
   is 2026-02-21 → **2026-10-23**.
2. **n=237, WR 47.3%, PF 1.26, +98.7pp, MDD −64.1pp, by-class stats, contributor stats.** No output
   artifact; no payload.
3. **A/B/D table** (no code in the archive; I re-implemented the definitions, but on the stale payload).
4. **Breakeven cost 0.416%/trade and monthly PF series** (no code; arithmetic only).
5. **114 distinct strategies / 15 source systems** in the live window. Available stale payload:
   **164 strategies / 24 source systems**. Snapshot-dependent.
6. **285 baby strategy files.** Branch has **227** `.py`; our MASTER_AUDIT counts 84 baby
   meta-strategies + 231 hand mutations.
7. **p<0.0013 exact value.** Code confirms 800 draws; the exact data are absent.
8. **Buy-and-hold benchmark.** No price history in the evidence; only point-in-time snapshots
   (`px_yahoo.json`, `px_binance_sample.json`).
9. **Intrabar fills / outcome truth.** The audit explicitly says external prices do not verify the
   system’s intrabar fills.
10. **Whether the live Nov-14 payload contains undated or zero-P/L closed rows** (the latent
    `'9999'` look-ahead and the zero-dilution issue).

---

## 9. Citation verification (≥6 numeric/file checks)

| # | Citation in claim | Check | Result |
|---|---|---|---|
| 1 | `PROFITABLE_APPROACH_v1.md:22–34` claim table | read on branch | **verified** (values as quoted) |
| 2 | `walkforward_v6.py` implements variant C + 800-draw null | read; ran it | **verified**; 78 lines; no A/B/D, no MDD, no cost, no monthly |
| 3 | Script uses `pnl_pct` with no slippage | `walkforward_v6.py:24,44,53,69` | **verified** (gross) |
| 4 | `deduct_slippage` expects a fraction; M-069 | `alpha_engine/charter_slippage.py:67–80` | **verified**; `pnl_pct` is pp at `outcome_resolver.py:1137`; `dashboard_generator.py:15465` feeds pp → ~100× under-deduction |
| 5 | 361 strategy families | `alpha_engine/config.py`, `len(STRATEGY_FAMILIES)` | **verified = 361** |
| 6 | `live_anti_overfit_audit.json`: 69/80 OVERFIT_LIKELY | branch file `2026-11-14/inspect-wt_20261114_1058/live_anti_overfit_audit.json` | **verified**; PBO `n_observations=20` (claim says 21); `reality_check` error: `arch` missing |
| 7 | `v1_cells.json` strategy stats | file | **verified**: vwap 38/2.527; rs-breakout 133/1.652/z=0.78; luxalgo 1,284/1.133/z=−5.02 |
| 8 | `closed_stats.json` 30d ALL n=1,273 PF 0.80 Σ −424.0; 7d n=401 PF 0.79 Σ −139.0 | file | **verified** |
| 9 | 7 workflows failing in 5h | `wf_last_seen.json` | **verified**: incl. ALPHA ENGINE Dynamic Runner 16:19:21Z id 43614960770; ALPHA ENGINE FAST, Sports, Signal Tracking, CI Tests, robust-edge-miner, Mirror |
| 10 | `mega_mutation::crypto` n=295 WR 64.1% PF 3.16 | `reports/2026-06-05-PER-CLASS-T2-INVENTORY-POST-FILTER.md:22` | **verified** |
| 11 | 28–100% of TP hits reclassified as SL | `reports/PAPER_PILOT_RESOLVER_FAIL_2026-06-05.md` | **verified** |
| 12 | 100% of 28,218 zero rows EXPIRED; 81.2%/96.6% | `reports/zero_pnl_data_pipeline_audit_2026-06-05.md` | **verified** |
| 13 | 3,500 rows / 2026-02-21 start | `audit_trail/data/dashboard_payload.json` | **partially verified**: count 3,500 and min 2026-02-21 ✓; max 2026-10-23 ✗ vs claim 2026-11-14 |
| 14 | Our 23-candidate program | `research/profitability/HYPOTHESES.md` | **verified**: 23 rows, 0/23 proved |
| 15 | VWAP falsification | `research/profitability/validation/VWAP_VERDICT.md` | **verified** |

---

## 10. Reproduction commands (read-only)

```bash
# 1. Extract the peer folder from the branch
git -C /home/eaguiar2015/findtorontoevents_antigravity.ca archive \
  origin/audit/live-audit-2026-11-14 \
  2026-11-14/deepAI_final_audit_20261114_1809 | tar -x -C /tmp/deepai

# 2. Run the committed script on the only same-schema payload in the repo
cp /tmp/deepai/2026-11-14/deepAI_final_audit_20261114_1809/notes/evidence/walkforward_v6.py /tmp/fp2run/
python3 /tmp/fp2run/walkforward_v6.py \
  /home/eaguiar2015/findtorontoevents_antigravity.ca/audit_trail/data/dashboard_payload.json
# -> VARIANT C: n=764 WR=41.1% PF=0.91 sum=-134.5pp z=-4.92
# -> null: 386/800 = p=0.4825

# 3. Confirm pnl_pct units and gross setting
python3 - <<'PY'
import json, statistics
d=json.load(open('/home/eaguiar2015/findtorontoevents_antigravity.ca/audit_trail/data/dashboard_payload.json'))
v=sorted(abs(p['pnl_pct']) for p in d['picks']['recent_closed'] if isinstance(p.get('pnl_pct'),(int,float)))
print('median |pnl_pct|', statistics.median(v), 'p90', v[int(.9*len(v))])
PY
# -> ~2.59 / ~6.58  (percentage points, not fractions)
```

---

## 11. Top 6 findings

1. **The core numbers are unreproducible from the archive.** No Nov-14 payload, no output log, and
   the committed script implements only variant C. n=237 / PF 1.26 / +98.7pp / p<0.0013 are
   **UNVERIFIED**.
2. **The same script on the only available same-schema payload gives the opposite result:**
   n=764, WR 41.1%, PF **0.906**, **−134.5pp**, null p=**0.4825**. The procedure is not robust to the
   dataset snapshot; the claim’s early-month PFs partially match this snapshot, making the
   unexplained Sep/Oct/Nov divergence the key missing evidence.
3. **“Net of slippage” is false.** The walk-forward uses gross `pnl_pct`; `deduct_slippage` is never
   called; the only call site passes percentage points into a fraction-unit function (~100×
   under-deduction). At the document’s own 0.1–0.2%/trade realistic cost, 237 trades cost ~24–47pp.
4. **Multiple testing is truncated to 4.** The document’s own V0–V6 search contains ≥46 V1 cells plus
   3 splits + V4 + 4 variants. Bonferroni over that family gives p≈0.06–0.17 (0.158 using the 95%
   upper bound of 0/800), not <0.005. The result does not robustly survive.
5. **The benchmark is random strategy selection, not random entry or buy-and-hold, and +98.7pp is an
   absolute gross sum, not an excess.** A long ETF/EQUITY book in a rising market is an unaddressed
   confound; no market-neutral or passive benchmark is computed.
6. **The headline depends on two fragile contributors and contradicts itself.** `vwap-reversion-scout`
   (n=15, +46.9pp) supplies ~47% of the P/L; dropping it gives PF 1.14, and dropping it plus the
   n=1 `gap-and-go` gives PF 1.11. The document also says “4 of 8 months negative” (only July is
   <1.0 in its own table) and “four consecutive improving months” (Aug 1.74 → Sep 1.28 is a decline).
