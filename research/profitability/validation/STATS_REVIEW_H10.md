# Adversarial Statistical Review — H10 (`H10_CORE_RSI2_CASH`)

**Review date:** 2026-11-14T18:25Z
**Reviewer role:** adversarial statistical reviewer (read-only; no repo source modified)
**Claim under review:** H10 passes all pre-registered gates with cumulative `N=12`;
DSR 0.979, p=0.0018, Bonferroni α=0.00417, PBO 0.238, bootstrap p05 1.28, 2×-cost Sharpe 1.68.

> **ERRATUM (2026-11-14T18:40Z):** the numbers in this review were computed on the 18:25Z
> pre-fix snapshot. `run_v1.py`/`run_v2.py` were regenerated at 18:34:40/18:36:05 after the
> cost-timing and RSI edge-case fixes. Final committed H10: Sharpe **1.8322**, DSR **0.9776**,
> p **0.001941**, 2× **1.6596**, bootstrap p05 **1.2690**; PBO 0.106 is OOS-only, full-sample
> all-12 is **0.417**. The conclusion is unchanged: H10 is NOT_PROVED (contaminated OOS,
> effective N≈38 DSR 0.9365, ex-best-day 0.8993, 2-day lag 0.696).

**Bottom line:** the arithmetic reproduces, and the *implemented* gate code returns `PROVISIONAL`.
The statistical and protocol integrity does **not** support `PROVISIONAL`. The OOS window was
already inspected in v1, and H10 is explicitly a post-hoc capital-efficiency variant of H7
(identical risk weights; only a T-bill sleeve added). Under the protocol's own §4 rolling-OOS rule
the H10 OOS is contaminated. The DSR/Bonferroni pass also depends on `N=12` (it fails at the
effective `N≈38` once the 27-cell grid inspected on OOS is counted) and on one trading day
(DSR 0.979 → 0.899 without 2025-04-09). A 2-day execution lag drops Sharpe to 0.70. Recommendation:
**downgrade to `NOT_PROVED`** and earn `PROVISIONAL` only with a genuinely clean forward OOS.

---

## 0. Method and evidence

All numbers below were independently recomputed two ways:

1. Directly from `runs/v2/oos_returns.csv` (721 daily rows, 2024-01-02..2026-11-13) with explicit
   formulas.
2. By re-running the cached strategy code (`strategies.py`, `backtest.py`) against the cached
   price/T-bill CSVs in `data/cache/` (no network), reproducing the H10 weights and returns.

The recomputed H10 return series matches `oos_returns.csv` to `9.84e-17` max absolute error.
Repository source was not modified. This review added only this report (a separate
`validation/REPLICATION_H10.md` already exists in the folder).

**Status legend:** `PASS` = claim reproduces and gate is met; `FAIL` = gate/claim does not survive
audit; `CONDITIONAL` = reproduces as coded but is not robust / not a valid inference;
`UNVERIFIED` = cannot be established from the committed artifacts.

---

## 1. Independent recomputation

### 1.1 Formulas used

Let `r_t` be the daily net portfolio return, `n` the number of OOS days, `ann=252` for ETFs.

- Sharpe (rf=0, as the protocol specifies): `SR = mean(r) / std(r, ddof=1) * sqrt(ann)`
- CAGR: `(prod(1+r_t))^(ann/n) - 1`
- Max drawdown: `min_t( equity_t / max_{s<=t} equity_s - 1 )`
- Bootstrap (block 20, 2,000 resamples, seed 7, `nb=ceil(n/20)`, uniform block starts, length
  truncated to `n`): percentile 5 and 95 of resampled Sharpe.
- DSR (Bailey–López de Prado): with daily `sr = mean/std`, sample skew `γ3`, non-excess kurtosis
  `γ4`, `γ=0.5772156649`,
  `var_sr = (1 - γ3*sr + (γ4-1)/4*sr^2)/(n-1)`,
  `sr0 = sqrt(var_sr) * [ (1-γ)Φ^-1(1-1/N) + γΦ^-1(1-1/(N e)) ]`,
  `DSR = Φ( (sr - sr0)/sqrt(var_sr) )`.
- p-value (two-sided, normal approximation): `t = (mean/std)*sqrt(n)`, `p = 2(1-Φ(|t|))`.
- Bonferroni: `α/N`; BH step-up at `α*i/N` on sorted p-values.

### 1.2 H10 headline metrics

| Metric | Reported | Recomputed | Status |
|---|---:|---:|---|
| OOS days | 721 | 721 (2024-01-02..2026-11-13) | PASS |
| OOS Sharpe | 1.85 | **1.845180** | PASS |
| OOS CAGR | 22.0% | **21.9637%** | PASS |
| OOS maxDD | −7.6% | **−7.6158%** | PASS |
| OOS total return | 76.5% | **76.4880%** | PASS |
| OOS vol | — | 11.0898% | PASS |
| Avg risk exposure | 0.17 | **0.173370** (cash 0.826630) | PASS |
| OOS changes / entries | 111 | **111 / 82** | PASS |
| Reported "train" Sharpe / CAGR / maxDD (2016-11-15..2023-12-31) | 0.67 / 6.7% / −15.8% | **0.6655 / 6.6843% / −15.8388%** | PASS as coded |
| Protocol train (2018-01-01..2023-12-31) | — | **0.6054 / 6.4361% / −15.8388%** | reporting discrepancy |
| Benchmark OOS Sharpe / CAGR | 1.02 / 18.6% | **1.023447 / 18.5507%** | PASS |
| Benchmark OOS vol / maxDD / total | — | **18.2513% / −20.9544% / 62.7224%** | PASS |
| 2× cost (10 bps) Sharpe | 1.68 | **1.683406** (CAGR 19.6138%) | PASS |
| Bootstrap p05 / p95 | 1.28 / 2.61 | **1.275667 / 2.610505** (mean 1.858278) | PASS |
| DSR (reported N=12) | 0.979 | **0.978851** | PASS as coded |
| p-value | 0.0018 | **0.00180184** (t=3.121) | PASS as coded |
| Bonferroni α (N=12) | 0.00417 | **0.00416667** | PASS at N=12 |
| PBO | 0.238 | **0.237685** | PASS as coded (see §2) |

**DSR inputs (recomputed):** `sr_daily=0.1162354`, `skew=5.419232`,
`kurtosis=102.326529`, `var_sr=0.000989362`, `sr0_annualized=0.831272`,
`DSR=Φ((0.1162354−0.052362)/sqrt(0.000989362))=0.978851`.

**Train-window discrepancy:** `split_metrics` uses `port.loc[:train_end]` with no lower bound, so
the reported "train" starts at the first return (2016-11-15), not the protocol's 2018-01-01. The
protocol-train (2018-2023) Sharpe is **0.6054** / CAGR **6.4361%** / maxDD **−15.8388%**, versus
the reported 0.6655. The difference is the 2016-2017 melt-up. The 27-cell grid's "train" column
also includes 2016-2017. This is a reporting discrepancy, not a lookahead; it does not change the
OOS result, but it does mean the claimed "train 0.67 → OOS 1.85" improvement is really
"0.61 → 1.85" and the grid's train column is mislabeled.

**Verdict on task 1:** all headline arithmetic **PASS**; the p-value is a normal approximation on
returns with skew 5.42 and kurtosis 102.3, so its nominal calibration is **UNVERIFIED** (the block
bootstrap is the more reliable inference, and it passes).

### 1.3 What actually drives the result

- H10's risk sleeve is **identical** to v1 H7: max absolute weight difference = `0.0`. H10 is
  H7 plus a T-bill sleeve (`_with_cash` in `strategies.py:132-146`).
- H7 (risk-only) OOS: Sharpe **1.514575**, CAGR **17.6136%**, maxDD −7.6316%, total 59.0694%.
- H10 = H7 + cash. The cash sleeve averages **82.66%** of the portfolio and contributes
  **3.63%/yr** (17.7% of H10's mean return). H10's mean daily return is 0.000812 vs 0.000668
  risk-only.
- Without cash, H10's OOS total return (59.07%) is **below** the buy-and-hold benchmark (62.72%)
  and CAGR 17.61% < 18.55%. The cash carry is what makes gate 2 (total return > benchmark) pass.
- 2025-04-09 contributes **+11.2025%** in one day (the post-tariff-pause rebound; benchmark same
  day +11.2525%). Removing that day: H10 Sharpe 1.856, CAGR 17.55%, total 58.71%; DSR falls to
  **0.8993**; bootstrap p05 falls to 1.0146. Removing the top 3 days: DSR **0.8255**, bootstrap
  p05 0.9091. The DSR gate is therefore concentrated in a handful of days.
- H10 vs a market regression on excess returns: alpha **10.85%/yr**, HAC t=2.33, beta 0.365;
  upside capture 0.32, downside capture 0.16, correlation 0.60. There is some timing content, but
  the alpha t-stat is not significant after 12+ trials.

---

## 2. PBO / CSCV audit

### 2.1 Implementation

`backtest.pbo_cscv` (lines 135-159) does the following:

- drops any row with a NaN (`R.dropna(how="any")`);
- `S = columns`, `T = rows`; requires `S>=4` and `T>=64`;
- `blocks = np.array_split(np.arange(T), 16)`: **16 contiguous blocks** (first 46 days, rest 45
  for T=721);
- enumerates **all `C(16,8)=12,870`** combinations, uses 8 blocks as IS and the complement 8 as
  OOS;
- computes per-strategy IS Sharpe and OOS Sharpe (`mean/std(ddof=1)`, daily, ranking-invariant);
- picks the IS-best strategy, takes its OOS rank (1..S, average ties);
- `omega = rank/(S+1)`; `PBO = mean(omega <= 0.5)` (probability the IS-best is in the bottom half
  OOS).

This is **structurally correct CSCV**: 16 contiguous blocks, 8/8 split, rank of the IS-best in
OOS, all combinations. Minor notes: first block is 46 days (unequal block sizes), and for odd
`S=5` the median rank (3/5) counts as "overfit" (`3/6 = 0.5`), a standard/conservative convention.

### 2.2 The non-standard part: sample and candidate set

The run feeds `pd.concat(oos_matrix, axis=1).dropna()` — i.e. **only the 2024-2026 OOS returns**,
not the full 2018-2026 sample. Standard CSCV applies to the full backtest matrix (the period over
which the configurations were selected and evaluated). Using only the OOS period measures rank
stability inside the OOS, not the train→OOS overfitting that PBO is meant to quantify.

Recomputed PBO variants (same function, 16 blocks unless noted):

| Candidate set | Sample | PBO | Status |
|---|---|---:|---|
| 5 v2 ETF candidates (as reported) | OOS only | **0.237685** | matches |
| 5 v2 ETF candidates | full 2018-2026 | **0.1702** | still <0.5 |
| 6 = 5 v2 + H7 | OOS only / full | **0.1677 / 0.0796** | <0.5 |
| 7 = 5 v2 + H5 + H7 | OOS only / full | **0.2002 / 0.2702** | <0.5 |
| 12 = v1 7 + v2 5 | OOS only / full | **0.1036 / 0.4173** | <0.5 |
| 27-cell H10 RSI2 grid | OOS only / full | **0.6160 / 0.4061** | OOS-only fails; full passes |
| 27-cell grid, 8 blocks | full | **0.4857** | near boundary |

(Sensitivity of the reported 5-candidate OOS-only PBO by block count: 8→0.1286, 10→0.2778,
12→0.2619, 14→0.2751, 16→0.2377.)

**Is 0.238 meaningful for 5 strategies?** Weakly. `S=5` is the minimum for CSCV; the rank
resolution is 1/6, the 12,870 splits are highly dependent (complementary/overlapping), and there
is no confidence interval. It cannot reliably distinguish 0.24 from 0.50. It is directionally
favorable, not strong evidence. The reported 0.238 also uses the OOS-only sample; the standard
full-sample PBO is **0.170**, and the all-12 full-sample PBO is **0.417** (still a pass but much
closer). The 27-cell parameter family that contains H10's central cell gives **0.406 full-sample**
and **0.616 OOS-only** (the central cell itself was pre-declared for H7, not selected from this
grid, so this is a family-level overfitting diagnostic, not evidence of OOS tuning).

**Would including all 12 change the result?** Not the pass/fail: all-12 full-sample PBO is 0.417
(<0.50), OOS-only 0.104. But a 12-candidate set mixes crypto and ETF calendars and five weak
crypto strategies; adding many clearly inferior strategies mechanically lowers PBO because the
IS-best only has to beat them in OOS. It is not a stronger overfitting control than the focused
ETF/RSI2 family. **PBO status: PASS as coded, CONDITIONAL as evidence.**

---

## 3. Multiple-testing integrity

### 3.1 Is N=12 correct?

- The registry count is 7 v1 + 5 v2 = 12, and `run_v2.py` merges the v1 `multiple_testing.pvalues`
  with `setdefault` (lines 96-106), so no candidate is silently replaced. The arithmetic is fair.
- **However, `HYPOTHESES.md` was never updated for v2.** It still lists only H1-H7, status
  `TESTING`, and says "N=7 candidates" for v1. There is no H8-H12 row, no v2 version log, no
  `PROTOCOL_v2.md`. The protocol (§10) requires the registry/status update; the "pre-registered
  N=12" is therefore not documented in the registry.
- The 27-cell parameter grid *was evaluated on OOS* in `validate_h10.py` (ROBUSTNESS.md shows all
  27 OOS Sharpes). The protocol (§9) says parameter grids are evaluated on **train only**. Those
  are 26 additional OOS looks beyond the headline H10 cell. Counting them gives an effective
  `N=12+26=38` (conservative 39). At `N=38`:
  - Bonferroni α = 0.05/38 = **0.001316**; H10 p = 0.001802 → **no rejection**;
  - DSR = **0.9365** → **fails the 0.95 gate**.
  At `N=39`: α=0.001282, DSR=0.9352. So the DSR/Bonferroni pass is **conditional on excluding the
  grid looks**. The protocol's "every candidate tested counts" language supports counting them.

### 3.2 Is H10 a post-hoc variant of H7?

**Yes, plainly.**

- `run_v2.py` docstring: "H10 SPY/QQQ RSI(2) + T-bill cash (**H7 capital-efficiency variant;
  exploratory**)."
- H10's risk weights are bit-identical to H7 (max abs diff 0.0); same 111 changes.
- v1 ran at 18:20:28, v2 at 18:23:19 — H10 was created **~3 minutes after v1 results were known**.
- v1 H7 had OOS Sharpe 1.51, p=0.0104108, and DSR 0.9507; its only v1 gate failure was
  `below_benchmark_return` (17.6% vs 18.6% CAGR). Its p-value was above v1's Bonferroni threshold
  (0.05/7 = 0.0071429), although v1's formal gate list used DSR, not a p-value gate. H10's p
  improves to 0.0018 because the cash sleeve adds carry and lowers vol, not because new signal
  evidence was collected.
- The protocol §4 is explicit: "If a version is revised after seeing OOS, the next version's OOS
  starts at the revision date (rolling OOS), and the prior OOS is demoted to 'seen' and no longer
  counts as clean." v2 reused `OOS_START="2024-01-01"` and did not create `PROTOCOL_v2.md`.

### 3.3 Does the correction suffice?

No. The Bonferroni/BH arithmetic is valid (Bonferroni controls FWER under arbitrary dependence,
and BH is valid under the likely positive dependence), so **if the only problem were multiple
testing, N=12 would suffice**. The problem is **selection on the same OOS**: no p-value correction
repairs a test whose evaluation window was already inspected to design the candidate. The
contamination risk is high, not marginal:

> H7's OOS (2024-2026) was observed; H10 was then defined as H7 + cash; H10's "new" OOS is the
> same 2024-2026 window. The 0.0018 p-value and 0.979 DSR are therefore not clean confirmatory
> evidence for a new hypothesis; they are a re-description of the same OOS with a lower-vol
> overlay.

A clean test requires a forward OOS starting **2026-11-14** (or the actual v2 revision date),
pre-registered before the fact.

### 3.4 Minor code issue

`multiple_testing` (backtest.py:171-184) implements BH as "reject every i with p_i <= α*i/N"
rather than the step-up rule "find the largest k with p_k <= α*k/N, reject 1..k". These differ
when an earlier p fails but a later one passes. In this dataset only H10 is rejected either way,
so the reported result is unaffected; the implementation should still be fixed.

**Verdict on task 3: FAIL on integrity** (N=12 arithmetic is fair; N is undercounted if grid looks
count; H10 is post-hoc H7; §4 rolling-OOS violated; registry not updated; correction cannot cure
OOS reuse).

---

## 4. Benchmark / fairness

### 4.1 Dividends and price-only closes

The Nasdaq ETF series are `Close/Last`, price-only (Addendum 1). `validate_h10.py` adds constant
annual yields (`SPY` 1.3%, `QQQ` 0.6%) to both strategy and benchmark:

| Series | Sharpe | CAGR | maxDD |
|---|---:|---:|---:|
| H10, dividends added to both | **1.858478** | **22.1533%** | −7.6051% |
| Benchmark, dividends added to both | **1.075498** | **19.6815%** | −20.8523% |

Gate 1/2 still pass under this adjustment. **CONDITIONAL/PASS**, but the constant-yield
approximation is not an actual dividend series; exact total-return data would be better. The
ex-dividend price drop can also distort RSI(2) signals (it looks like a negative return), a small
signal-quality issue.

### 4.2 T-bill cash yield

H10 earns 13-week T-bill yield (`rate/100/252`) on the ~82.7% cash sleeve. Mean T-bill rate over
the OOS is 4.384%/yr. Cash contributes **3.63%/yr** and 17.7% of the mean return. Cash sensitivity:

| Case | OOS Sharpe | OOS CAGR |
|---|---:|---:|
| no cash | 1.514575 | 17.6136% |
| half cash | 1.679729 | 19.7690% |
| actual | 1.845180 | 21.9637% |
| cash + 1% | 1.920591 | 22.9759% |

The cash yield is real carry, but it is **not alpha**, and the protocol's `rf=0` Sharpe convention
counts it as return. Without it, H10 fails gate 2 (17.61% < 18.55% benchmark CAGR).

### 4.3 Risk-matched benchmark — the central fairness issue

`validate_h10.py` builds a static `expo` core / `(1-expo)` cash benchmark, daily rebalanced, no
costs. Recomputed at the full-sample exposure **0.159905**: Sharpe **2.285007**, CAGR **6.8512%**,
vol **2.9191%**, maxDD **−3.1358%**. At the **OOS** average exposure **0.173370** (the fairer
match): Sharpe **2.1684**, CAGR **7.0490%**, vol **3.1648%**, maxDD **−3.4439%** (recomputed;
matches the separate replication). Both exceed H10's 1.845 on the protocol's rf=0 convention.

- Under the protocol's literal **rf=0** Sharpe, the static full-sample 16/84 mix **beats H10
  (2.285 > 1.845; 2.168 at the OOS 17.3% exposure)**. A literal reading of gate 1 vs a
  risk-matched benchmark **fails**.
- But the 2.285 is a **cash-carry artifact**: with 84% cash, the risk-free rate is counted as
  "return" while volatility collapses toward zero. On **excess-of-rf** Sharpe (subtract the same
  13-week T-bill series), H10 = **1.450**, buy-and-hold = **0.783**, risk-matched = **0.783**
  (scale-invariant: any static weight `w*bench + (1-w)*rf` has the same excess Sharpe as the
  benchmark). On the economically correct excess-return metric, H10 **beats** both.

So the answer to "are the gates still met under a fair benchmark?" is:
- vs the **declared buy-and-hold** benchmark: **PASS** (1.845 ≥ 1.023+0.30; 76.49% > 62.72%).
- vs a **literal rf=0 risk-matched** benchmark: **FAIL** (1.845 < 2.285).
- vs an **excess-of-rf risk-matched** benchmark: **PASS** (1.450 > 0.783).

The protocol is internally inconsistent because it mandates `rf=0`. That inflates any cash-heavy
strategy and makes the 2.29 comparison non-comparable. The protocol should use excess-of-rf Sharpe
as the primary metric and report the risk-matched benchmark at the **OOS** exposure.

### 4.4 Is "beat buy-and-hold" appropriate for a 17%-exposure strategy?

**No, not on total return.** H10 averages 17.3% risk exposure and 11.1% vol; the benchmark is
100% invested with 18.25% vol. Requiring total return > a 100%-invested benchmark is a risk-taking
test, not a skill test: a 17%-exposure strategy can beat it only by timing/selection, and H10 does
so partly through cash carry. The risk-adjusted comparison (excess Sharpe, vol-matched) is the
correct gate. Gate 2 should be restated as "net excess return > risk-matched benchmark" or
"Sharpe > risk-matched benchmark + 0.30 on excess returns", not raw total return.

### 4.5 2-day lag (execution degradation)

`validate_h10.py` shifts the target weights by 2 days instead of 1 (an extra day of execution
delay): **Sharpe 0.696355**, CAGR 8.1764%, maxDD −14.2205%, vol 12.3739%. A 3-day lag: Sharpe
**0.4772**, CAGR 5.26%. The pre-registered gate 1 requires Sharpe ≥1.0; **a 2-day lag fails it**.
The protocol does not include an execution-lag gate, so this is not a formal gate failure, but it
is a first-order execution risk: the edge decays by ~62% with one extra day. This is consistent
with a fast mean-reversion signal that may not survive realistic fills.

### 4.6 Cost stress

| Cost | OOS Sharpe | OOS CAGR |
|---|---:|---:|
| 5 bps | 1.845180 | 21.9637% |
| 10 bps (2×) | 1.683406 | 19.6138% |
| 20 bps | 1.348600 | 15.0456% |
| 30 bps | 1.000222 | 10.6476% |

2× cost passes (1.683 ≥ 0.5 and > benchmark 1.023). At 30 bps the Sharpe is exactly at the 1.0
gate boundary. OOS turnover is 112.0 (sum |Δw|), total cost drag 5.6% over 2.86 years (~1.96%/yr);
the strategy is cost-sensitive.

**Verdict on task 4: CONDITIONAL.** Dividends/costs are handled reasonably and the gate passes vs
the declared benchmark; the risk-adjusted picture is ambiguous under the protocol's `rf=0`
convention; the execution-lag result (0.70) is a material failure not covered by the gates.

---

## 5. Regime dependence

The yearly table in `ROBUSTNESS.md` mixes **in-sample (2018-2023)** and **OOS (2024-2026)** years
without labeling them. Only 2024-2026 is OOS.

| Year | H10 Sharpe | H10 CAGR | Bench Sharpe | Bench CAGR | H10 edge (Sharpe) |
|---|---:|---:|---:|---:|---:|
| 2018 (IS) | −0.74 | −10.0% | −0.09 | −3.6% | −0.65 |
| 2019 (IS) | 0.40 | 2.7% | 2.10 | 33.3% | −1.70 |
| 2020 (IS) | 2.03 | 38.4% | 0.97 | 31.1% | +1.06 |
| 2021 (IS) | 0.73 | 5.3% | 1.66 | 27.1% | −0.93 |
| 2022 (IS) | −0.15 | −2.8% | −0.96 | −26.6% | +0.81 |
| 2023 (IS) | 1.65 | 11.0% | 2.23 | 38.7% | −0.58 |
| 2024 (OOS) | 3.01 | 23.3% | 1.51 | 24.2% | +1.50 |
| 2025 (OOS) | 1.19 | 18.7% | 0.90 | 18.5% | +0.29 |
| 2026 (OOS) | 2.44 | 24.3% | 0.75 | 12.5% | +1.69 |

Two corrections to the prompt's framing:

1. The 2018/2019/2021/2023 underperformance is **in-sample**, not OOS. In the actual OOS
   (2024-2026) H10 beats the benchmark on Sharpe in all three years, roughly matches it on CAGR in
   2024/2025, and beats it in 2026. The OOS is **not** simply a "bull-market artifact" in the
   sense of lagging a bull market; it kept pace in 2024/2025 and won in 2026.
2. The OOS is still only **three calendar years, one regime path**, and the train→OOS Sharpe jump
   (protocol-train 0.605 → OOS 1.845) is large. The in-sample record shows the strategy's real weakness: **low-vol,
   persistent bull markets** (2019, 2021, 2023), where it lagged badly (CAGR 2.7/5.3/11.0 vs
   33.3/27.1/38.7). Those are precisely the periods in which a long-only RSI(2) dip-buyer sits in
   cash while the market grinds up.

**Is it a bull artifact?** Not in the narrow sense, but the OOS is a short, favorable sample, and
the strategy is regime-dependent (mean-reversion/high-vol vs low-vol trend). The correct statement
is: **the OOS evidence is consistent with a real but regime-conditional mean-reversion edge; it
does not establish regime robustness.** The result would be falsified by a forward period of low
realized vol and persistent uptrend in which H10 lags the benchmark and its Sharpe falls below
1.0, or by a forward execution-lag test with Sharpe <1.0.

Two further checks in `validation/REPLICATION_H10.md` (executed by a separate replication pass;
I did not re-run the holdout, but the numbers are consistent with the regime story):

- **Clean 2016-11-14..2017-12-31 holdout** (before the protocol's 2018 train start): H10 Sharpe
  **1.755** / CAGR **7.46%** / maxDD −1.67%, vs equal-weight SPY/QQQ B&H **2.835 / 25.76%** and a
  risk-matched passive mix **3.698 / 3.47%**. H10 underperformed B&H on both Sharpe and CAGR in
  that clean period; the 2024-2026 magnitude did not generalize. Caveat: the code's "train"
  includes 2016-2017, so this window was not unseen by the code that produced the report, but it
  is unseen relative to the protocol's 2018 train and the OOS.
- **Out-of-universe DIA/IWM/VTI, 2024-2026**: H10 Sharpe **1.358 / 1.280 / 1.936** vs their B&H
  **0.883 / 0.645 / 1.068**. The edge is present across US equity ETFs, not specific to SPY/QQQ.
  This is more consistent with a broad 2024-2026 short-term-reversal regime than with a unique
  SPY/QQQ property — good for breadth, bad for claiming a durable SPY/QQQ edge.

**Verdict on task 5: CONDITIONAL / UNVERIFIED** (short OOS; in-sample regime weakness is clear;
the clean 2016-2017 holdout underperforms B&H; forward out-of-regime evidence is missing).

---

## 6. Gate-by-gate audit

Protocol §7 gates, as implemented in `run_v2.py:114-126` plus `validate_h10.py`:

| # | Gate | Requirement | H10 | Status |
|---|---|---|---|---|
| 1 | OOS Sharpe | ≥1.0 and ≥ bench+0.30 | 1.845 ≥ 1.323 | PASS (vs declared benchmark) |
| 2 | OOS CAGR / total return | >0 and > benchmark | 21.96% / 76.49% > 18.55% / 62.72% | PASS as coded (unfair for 17% exposure; fails without cash) |
| 3 | OOS trades | ≥30 | 111 changes / 82 entries | PASS |
| 4 | DSR | ≥0.95 at N=candidates | 0.9789 at N=12; **0.9365 at N=38**; **0.8993 ex-top-1 day** | CONDITIONAL |
| 5 | PBO | <0.50 | 0.2377 coded; 0.170 full-sample; 0.406–0.616 grid family | CONDITIONAL (pass, underpowered/non-standard sample) |
| 6 | Bootstrap p05 | >0 | 1.2757 | PASS |
| 7 | 2× cost | ≥0.5 and > benchmark | 1.683 > 0.5 and >1.023 | PASS |
| 8 | Parameter stability | sign stable; train-only grid | train grid 0.316–1.013 (all positive) | PASS on sign; **process FAIL** (grid also evaluated on OOS) |
| 9 | No lookahead / survivorship | point-in-time, no backfill | lag test only; no point-in-time/survivorship test | UNVERIFIED |
| — | Execution lag (not a gate) | — | 2-day lag Sharpe 0.696 | FAIL (not gated) |
| — | Registry/protocol update | HYPOTHESES.md, PROTOCOL_v2.md | H8-H12 missing; no PROTOCOL_v2.md | FAIL |

**"H10 passes all pre-registered gates" is an overstatement:** gates 8 and 9 are not implemented
as pass/fail checks, and the OOS grid inspection violates §9. The code's gate list passes; the
protocol's full gate list does not.

---

## 7. Verdict

**Recommendation: `NOT_PROVED` (downgrade from `PROVISIONAL`).**

Reasons, in order:

1. **Contaminated OOS (protocol §4).** H10 is H7 + a deterministic cash sleeve, created ~3 minutes
   after v1's OOS was reported. The same 2024-2026 window is reused. No correction fixes this; a
   new forward OOS is required.
2. **DSR/Bonferroni are not robust.** They pass at N=12 but fail at N≈38 (grid looks counted:
   DSR 0.9365, α 0.001316 < p 0.001802) and fail after removing the single best day (DSR 0.8993).
3. **Execution fragility.** A 2-day lag drops Sharpe to 0.696, below the pre-registered 1.0 gate.
4. **Benchmark ambiguity.** Under the protocol's `rf=0` convention a static risk-matched mix has
   Sharpe 2.168 (OOS exposure) to 2.285 (full-sample exposure), both > 1.845; on excess-of-rf
   Sharpe H10 wins (1.450 vs 0.783). The protocol needs to resolve this; the current "beat
   buy-and-hold" gate is not risk-adjusted for 17% exposure.
5. **Registry/process failures.** H8-H12 are absent from `HYPOTHESES.md`; no `PROTOCOL_v2.md`;
   the 27-cell grid was evaluated on OOS despite §9; the reported "train" includes 2016-2017
   rather than the protocol's 2018-2023.
6. **Clean 2016-2017 holdout does not corroborate the magnitude.** H10 Sharpe 1.755 / CAGR 7.46%
   vs B&H 2.835 / 25.76% (separate replication) — the strategy underperformed B&H in a clean,
   low-rate, trending period. The 2024-2026 magnitude is not stable across regimes.

A separate replication in `validation/REPLICATION_H10.md` reproduces the arithmetic on a fresh
download and finds no lookahead. Its fresh CSVs are **byte-identical** to the cached Nasdaq/Treasury
files (same vendor, same as-of date), so it is an arithmetic replication, not an independent
data-vendor test. It reaches the same bottom line: do not promote H10 to `PROVED`; the 2024-2026
window is seen OOS under §4.

If the team wants a forward-looking label, use **"PROVISIONAL — CONTAMINATED OOS / FORWARD TEST
PENDING"**, not "passes all gates". `PROVED` is not remotely justified (no clean OOS, no
independent data-vendor replication, no adversarial review sign-off).

### Exact additional tests needed to earn `PROVISIONAL` / `PROVED`

1. **Pre-register v2 properly, before any new OOS look:** add H8-H12 (and the full RSI2 parameter
   family) to `HYPOTHESES.md` with status and N; create `PROTOCOL_v2.md` covering the T-bill cash
   sleeve, the new universes, and the excess-Sharpe metric. Freeze it.
2. **New rolling OOS starting 2026-11-14** (or the actual v2 revision timestamp). Do not reuse
   2024-2026 for H10. Require ≥30 trades and ≥2 years (or a pre-declared minimum).
3. **Correct N:** count every OOS evaluation, including the 27-cell grid (N≥38), or pre-declare
   the central cell and never evaluate the grid on OOS. Report DSR and Bonferroni at that N.
4. **Primary metric = excess-of-rf Sharpe**, with the risk-matched benchmark at the **OOS** average
   exposure; report both rf=0 and excess for comparability. Gate 1 should compare excess Sharpe to
   the risk-matched benchmark + 0.30, not to 100% buy-and-hold.
5. **Add an execution-lag gate:** 2-day-lag OOS Sharpe ≥1.0 (currently 0.696) and 2-day-lag total
   return > risk-matched benchmark. Also test 3-day lag.
6. **Add a concentration gate:** results must survive dropping the top 1/3/5 days; currently the
   DSR fails ex-top-1 (0.8993). Require DSR ≥0.95 after the drop.
7. **Actual total-return data:** use dividend-adjusted series or total-return ETFs (not constant
   yields); verify the RSI signal is not distorted by ex-dividend price drops.
8. **Point-in-time / survivorship audit:** document the ETF universe's delisting history; confirm
   no backfilled symbols. (Low risk for SPY/QQQ; higher for the sector/intl set.)
9. **Independent replication** by a separate agent, fresh data pull, same code, per protocol §10.
10. **Decompose the claim:** report H7 (risk-only) and H10 (with cash) separately. If the edge is
    the cash carry, say so; H7's OOS p=0.0104 failed v1 Bonferroni (α=0.00714), so the signal
    alone is not proven.

---

## 8. Residual risks, ranked

| Rank | Risk | Evidence | Severity |
|---:|---|---|---|
| 1 | **OOS contamination / post-hoc H10 = H7 + cash** | identical weights (max diff 0.0); v2 run 3 min after v1; protocol §4 requires rolling OOS | Critical |
| 2 | **DSR/Bonferroni fail once grid looks are counted** | N=38: DSR 0.9365 <0.95; α 0.001316 < p 0.001802 | Critical |
| 3 | **DSR depends on one day** | 2025-04-09 +11.20%; DSR 0.979 → 0.899 ex-top-1; 0.826 ex-top-3 | High |
| 4 | **Execution lag destroys the edge** | 2-day lag Sharpe 0.696; 3-day 0.477; 30 bps 1.000 | High |
| 5 | **Clean 2016-2017 holdout underperforms B&H** | H10 1.755 / 7.46% vs B&H 2.835 / 25.76% (separate replication) | High |
| 6 | **Short, favorable OOS / regime dependence** | OOS 2024-2026 only; in-sample lags low-vol bulls (2019/2021/2023); protocol-train 0.605 vs OOS 1.845 | High |
| 7 | **Fair-benchmark ambiguity (rf=0 vs excess)** | risk-matched rf=0 2.168 (OOS expo) / 2.285 (full expo) > 1.845; excess 0.783 < 1.450 | Medium-High |
| 8 | **Cash carry drives gate 2** | no-cash CAGR 17.61% < benchmark 18.55%; cash 3.63%/yr, 82.7% weight | Medium-High |
| 9 | **PBO underpowered / non-standard sample** | S=5; OOS-only 0.238 vs full-sample 0.170; grid 0.406–0.616; no CI | Medium |
| 10 | **Registry/protocol gaps** | H8-H12 absent from HYPOTHESES.md; no PROTOCOL_v2.md; grid OOS look violates §9 | Medium |
| 11 | **Replication is not independent data** | fresh download byte-identical to cache (same Nasdaq/Treasury vendor, same as-of date) | Medium |
| 12 | **Train-window mislabel** | reported "train" includes 2016-2017; protocol train 2018-2023 is Sharpe 0.6054 | Low-Medium |
| 13 | **Data approximations** | price-only closes, constant dividend yields, T-bill coupon/252, reconstructed v1 returns for all-12 PBO | Low-Medium |
| 14 | **Code issues (non-material to OOS)** | cost timing one-row shift; `_with_cash` dead `cash_ret`; T-bill cache ignores `start_year` pre-2018; `rsi()` fills 50 on zero down-EWM | Low |
| 15 | **BH implementation deviation** | per-index vs largest-k step-up; no effect here (only H10 rejected) | Low |
| 16 | **Bootstrap minor issues** | block-start upper bound excludes final block; no bias correction; 20-day blocks vs regimes | Low |

---

## 9. Reproduction notes

- H10 recomputation used `data/cache/nasdaq_SPY_1d.csv`, `nasdaq_QQQ_1d.csv`,
  `treasury_13w.csv` and the committed `strategies.py` / `backtest.py`; the resulting return
  series matches `runs/v2/oos_returns.csv` to `9.84e-17`.
- The all-12 PBO is a **reconstruction** because v1 did not save `runs/v1/oos_returns.csv`; v1
  portfolio returns were regenerated from cached data. Ranking is daily Sharpe, so the 252-vs-365
  annualization difference between v1 crypto and v2 ETF does not affect PBO ranks. Marked
  **UNVERIFIED** against the original v1 return files (they do not exist).
- The 27-cell grid PBO uses the 27 `(entry, exit, max_hold)` cells in
  `validate_h10.py:73-81`, recomputed over full sample and OOS.
- Risk-matched excess Sharpe uses the same 13-week T-bill series; the benchmark's reported
  2.285 is rf=0 and is not directly comparable to an excess-return Sharpe.
- A separate replication exists at `validation/REPLICATION_H10.md`. It re-downloaded the data into
  `/tmp` and reproduced all headline metrics exactly; I independently verified its protocol-train
  (2018-2023: Sharpe 0.6054) and OOS-exposure risk-matched (2.1684) numbers here. Its fresh CSVs
  are **byte-identical** to the cache (same vendor/as-of date), so it is an arithmetic replication,
  not an independent data-vendor test.
- The clean 2016-11-14..2017-12-31 holdout and the DIA/IWM/VTI out-of-universe results are quoted
  from `validation/REPLICATION_H10.md`; I did not re-run those two experiments. They are marked as
  peer-reported, not independently re-verified by this review.
- No fabricated numbers: every figure above is either from `results.json` / `robustness.json` /
  `oos_returns.csv` / `validation/REPLICATION_H10.md` or from the independent recomputation
  described here. Items I could not verify are labeled `UNVERIFIED`.

---

**Final status: `NOT_PROVED` (recommend downgrade).** The implemented gate code passes; the
scientific claim of a clean, multiple-testing-corrected OOS edge does not.
