# Adversarial Statistical Review — Regime-Filtered VWAP Mean Reversion (4h Crypto)

**Review date:** 2026-11-14T19:15Z
**Reviewer role:** VWAP-R2, adversarial statistical reviewer (read-only; no repo source modified)
**Claim under review:** `updates/2026-11-14-PROFITABLE-APPROACH-VWAP-MEAN-REVERSION.md`
**Claim headline:** PF 1.210, Sharpe 3.76, PBO 0.489, DSR `P(Sharpe>0)=1.0000`, MDD 10.0%, 129 trades, total return 12.7%, ~22 months OOS, "all statistical gates pass".

**Bottom line:** **FAIL — NOT PROVED.** The arithmetic of the saved v12 JSON reproduces exactly (129 trades, PF 1.2104, total return 12.699%, MDD 9.994%, PBO field 0.489), but the statistical interpretation does not survive audit:

- The reported "DSR" is not the Bailey–López de Prado Deflated Sharpe Ratio. It is a hand-rolled one-sided z-test that plugs an *annualized* Sharpe into a *per-period* standard-error formula. The true DSR is **0.8285 at N=1**, **0.0109 at N=960**, and **0.0022 at N=7,680** — far below the 0.95 gate.
- The reported PBO is not CSCV PBO. It is a bootstrap tail probability that is approximately 0.5 by construction. A proper CSCV over the 8-symbol selection set is **0.840** (S=16), and over the 5 selected symbols **0.945**; over the 960-parameter grid it is 0.014–0.237 depending on the sample/config set. The 0.489 value therefore has no overfitting-control meaning.
- The "~22 months OOS" is actually **218.5 days = 7.18 months**. The 70/30 split of 730 days gives ~511 days train and ~219 days test.
- The "5 symbols, 129 trades" headline is internally inconsistent: 129 trades is the **8-symbol** total; the 5-symbol subset is **72 trades**; the 3 symbols the report says were rejected (DOGE/AVAX/LINK) contribute **57 losing trades** and are still included in the 129-trade aggregate.
- The regime filter is applied **post hoc** to a trade sequence that was generated with no regime filter. Re-running the strategy correctly (skip entries when the regime is not MR-compatible) gives **355 trades, PF 0.974, per-trade Sharpe -0.0113, total return -7.23%, MDD 23.39%** — the edge disappears and becomes negative.
- The Sharpe 3.76 is an annualization artifact: per-trade Sharpe is **0.08031**, and the code multiplies by `sqrt(2190)=46.80`. The correct time-indexed portfolio Sharpe is **1.105** (trade-frequency annualization: **1.179**). The correct t-stat is **0.912** (p=0.181 one-sided), not z≈16; the 95% CI for the mean per-trade return includes zero.

Recommendation: **do not call this PROVED or VALIDATED.** The claim should be withdrawn or downgraded to `NOT_PROVED`; a clean forward test with a correctly implemented regime filter, execution lag, true DSR/PBO, and capital constraints is required.

---

## 0. Status legend and scope

- `PASS` — claim reproduces and the gate is met as stated.
- `FAIL` — gate/claim does not survive audit, or the reported computation is not the statistic named.
- `CONDITIONAL` — arithmetic reproduces as coded, but the inference is invalid or not robust.
- `UNVERIFIED` — cannot be established from the committed artifacts or the available data.

This review recomputed the v12 strategy from a fresh yfinance 730d/4h download (4,373 bars per symbol; OOS test 1,312 bars per symbol; data as of 2026-11-14) using read-only audit scripts under `/tmp/kilo/vwap_audit*.py`. The saved `/tmp/kilo/regime_filtered_vwap_v12_results.json` was reproduced exactly for the aggregate and per-symbol rows, with one exception noted in §5.4 (the report's ADA row). No repository source file was modified; this report is the only file added.

**Protocol references:** `research/profitability/PROTOCOL.md` §7 (gates 1–9), §8 (multiple testing), §9 (anti-overfitting); `PROTOCOL_v3.md` §5 (gates 4, 5, 7, 10, 11); `SCORECARD.md` (current verdict: NOT PROVED, 23 candidates).

---

## 1. What reproduces, and what does not

| Metric | Claim | Independent recomputation | Status |
|---|---:|---:|---|
| OOS window | ~22 months | 2026-04-10 04:00Z .. 2026-11-14 16:00Z; **218.5 days = 7.18 months** | **FAIL** |
| Trades | 129 (said "5 symbols") | 129 = **8 symbols**; 5-symbol subset = **72**; 3 rejected = **57** | **FAIL** (mislabelled universe) |
| Profit factor | 1.210 | **1.210409** (8-symbol pooled, 20 bps RT) | PASS as coded |
| Win rate | 44.2% | **44.186%** | PASS as coded |
| Total return | 12.7% | **12.699%** (pooled trade compounding) | PASS as coded |
| Max drawdown | 10.0% | **9.994%** pooled; **10.995%** time-indexed portfolio | PASS as coded (method-sensitive) |
| Sharpe | 3.76 | **3.7583 = 0.08031 × sqrt(2190)**; correct time-indexed **1.105**; trade-frequency **1.179** | **FAIL** |
| DSR | 1.0000 | Proper DSR **0.8285 (N=1)**, **0.0109 (N=960)**, **0.0022 (N=7,680)**, **0.00036 (N=76,800)** | **FAIL** |
| PBO | 0.489 | Peer bootstrap function returns **0.489**; it is **not CSCV**. Proper CSCV: 8-symbol selection **0.840**; 5-symbol **0.945**; 960-grid pooled **0.014–0.237** | **FAIL as reported** |
| OOS trades >=30 | 129 | 129 (8-symbol) / 72 (5-symbol) | PASS on count; universe inconsistent |
| Test B | PF 1.435, Sharpe 7.10, 65 trades | **PF 1.43494, 65 trades**; Sharpe 7.10 = 0.15165 × sqrt(2190) | PASS arithmetic; **not independent** |
| ADA row | PF 2.23, Sharpe 13.59, +4.2% | Saved v12 JSON: **PF 2.987, Sharpe 19.645, +7.03%** | **FAIL** (does not reproduce) |
| Benchmark | not reported | BTC buy-and-hold OOS: **-8.25%**, Sharpe -0.194, MDD 29.39%; EW8: **-18.49%**, Sharpe -0.394, MDD 35.63% | UNVERIFIED in claim; strategy beats a bear-market benchmark on point estimate |

**Reproduction detail.** The v12 code runs the VWAP strategy on the 30% test slice, computes a regime for each test bar, and then keeps only trades whose *entry* regime is in `{MEAN_REVERTING, CHOPPY_TIGHT, CHOPPY_WIDE, HIGH_VOLATILITY, CRISIS}` or `UNKNOWN` (`/tmp/kilo/regime_filtered_vwap_v12.py:73`). The saved JSON's 129 pooled trades and per-symbol n/PF/return/MDD match a fresh reproduction exactly. The report's Test A headline is therefore the **8-symbol** aggregate, not the 5-symbol set shown in its table.

---

## 2. DSR audit — the reported "DSR" is not DSR

### 2.1 What the code actually does

`alpha_engine/validation/statistical_gates.py:159-252` contains a genuine Bailey–López de Prado style DSR *structure*:

```
sr        = mean(r)/std(r) * sqrt(annualization_factor)
var_sr    = (1/n) * (1 - skew*sr + (kurt/4)*sr^2)
E[max SR] = sqrt(var_sr) * [ (1-gamma)*Phi^-1(1-1/N) + gamma*Phi^-1(1-1/(N*e)) ]
DSR       = Phi( (sr - E[max SR]) / sqrt(var_sr) )
```

Two problems are material:

1. **The function is called with `num_trials=1`** (`regime_filtered_vwap_v12.py:168`). With `N=1`, `E[max SR]=0`, so the function degenerates to a one-sided test of `SR>0`. It is not a *deflated* Sharpe ratio at all.
2. **The function is called with `annualization_factor=2190`** (`8760//4`), i.e. the per-trade returns are annualized by `sqrt(2190)`. The variance formula expects the *per-period* Sharpe, not the annualized Sharpe. With `sr=3.758`, the term `1 - skew*sr + (kurt/4)*sr^2` becomes negative and `var_sr < 0`; the function returns `sr_std=NaN`, `dsr_probability=NaN`, `pass=False`. This is what happened in the v12 run.

The script then computes a separate `p_pass` by hand (`regime_filtered_vwap_v12.py:183-185`):

```
se     = sqrt( (1 + 0.5*sharpe^2) / (n-1) )
z      = sharpe / se
p_pass = 0.5 * (1 + erf(z/sqrt(2)))
```

Here `sharpe` is the *annualized* 3.758, but the `(1 + 0.5*sharpe^2)` formula is for the *per-period* Sharpe. The saved JSON field `dsr_probability` is `p_pass`, not the repo DSR output (`regime_filtered_vwap_v12.py:231`). The report then labels this `DSR P(Sharpe>0)=1.0000`. This is the core statistical error.

### 2.2 Why z ≈ 16 appears

With `SR_ann = 3.75826`, `n = 129`:

```
se     = sqrt( (1 + 0.5*3.75826^2) / 128 ) = 0.25087
z      = 3.75826 / 0.25087 = 14.98
p_pass = Phi(14.98) = 1.0000
```

The report says z≈16; the exact value is 14.98. More importantly, for large `SR_ann`, this formula converges to:

```
z -> sqrt(2n) = sqrt(258) = 16.06
```

so **z≈16 is the asymptotic ceiling of the formula, independent of the data**, not a measurement of a 16-sigma edge. Plugging an annualized Sharpe into a per-period SE is the error. The correct per-period calculation is:

```
SR_trade = 0.00100397 / 0.01250135 = 0.0803091
se_trade = sqrt( (1 + 0.5*0.0803091^2) / 128 ) = 0.08847
z_trade  = 0.0803091 / 0.08847 = 0.9077
p_one    = 0.182
```

Equivalently, the simple t-stat on the mean per-trade return is `0.0803091 * sqrt(129) = 0.9121`, p=0.1808 one-sided. The Newey–West t-stat is 1.00 (p=0.317, two-sided) on trades and 0.823 (p=0.411) on the time-indexed portfolio. The 95% CI for the mean per-trade return is **[-0.001153, +0.003161]**, which includes zero. The reported 1.0000 is therefore not evidence of a positive Sharpe; it is a numerical artifact.

### 2.3 Correct DSR with the actual trial count

Using the Bailey–López de Prado formula with per-trade returns (`T=129`), sample skew `γ3=1.06229`, excess kurtosis `0.18760` (`γ4=3.18760`), `sqrt(var_sr)=0.0846969`:

```
var_sr   = (1/(T-1)) * (1 - γ3*SR + ((γ4-1)/4)*SR^2)
E[maxSR] = sqrt(var_sr) * [ (1-γ)Φ^-1(1-1/N) + γΦ^-1(1-1/(N e)) ]
DSR      = Φ( (SR - E[maxSR]) / sqrt(var_sr) )
```

| N (trials) | E[max SR] | DSR |
|---:|---:|---:|
| 1 | 0.00000 | **0.8285** |
| 8 | 0.12357 | **0.3047** |
| 960 | 0.27471 | **0.01086** |
| 7,680 | 0.32148 | **0.00220** |
| 15,360 | 0.33577 | **0.00128** |
| 76,800 | 0.36700 | **0.000356** |

For comparison, the repo function called correctly (`annualization_factor=1`): `N=1` -> **0.8298**, `N=7,680` -> **0.00224** (the small difference is the repo function's kurtosis term). Called as v12 did (`annualization_factor=2190`, `N=1`): **NaN**.

**Verdict: FAIL.** The DSR gate is not met at any honest N. Even at N=1, the proper DSR is 0.8285 < 0.95. At the grid/symbol count, it is effectively zero. The reported 1.0000 is not the DSR.

### 2.4 Trial count used

The task's stated trial count is:

- 8 strategy families tested (VWAP, Donchian, Bollinger, dual momentum, Faber TAA, ensemble, etc.);
- 8 symbols;
- per-symbol grid `4 x 5 x 4 x 4 x 3 = 960` parameter combinations;
- 5 MR-compatible regimes;
- 2 reported tests (v11/v12).

A conservative count of parameter backtests is `960 x 8 = 7,680`. If each grid/symbol look is also combined with the 5 regime filters, `7,680 x 5 = 38,400`; if both v11/v12 are counted, `76,800`. The DSR column above covers this range. The report's `N=1` is not defensible. The count is also an *undercount*: `/tmp/kilo` contains additional VWAP variants (`vwap_4h_v7.py`, `vwap_position_sized_v9.py`, `regime_filtered_vwap_v13_1h.py`, `v14`, `v15`, `v16`, `v17`, plus v1/v2 harnesses). Those extra looks are `UNVERIFIED` in the report's N, so the true DSR is at most the N=76,800 value.

---

## 3. PBO audit — 0.489 is not CSCV PBO

### 3.1 What the code does

`regime_filtered_vwap_v12.py:96-110` defines:

```python
def pbo(pnls, n_boot=2000, seed=42):
    arr = np.array(pnls)
    obs = np.mean(arr) / np.std(arr, ddof=1)
    for _ in range(n_boot):
        s = np.random.choice(arr, size=len(arr), replace=True)
        bs = np.mean(s) / np.std(s, ddof=1)
        if bs >= obs:
            cnt += 1
    return cnt / n_boot
```

This is a bootstrap tail probability of the observed mean/vol ratio. The bootstrap distribution is centered at the observed statistic, so the fraction of resamples `>= obs` is approximately 0.5 **by construction**, regardless of whether there is an edge. It is not the Probability of Backtest Overfitting (CSCV) of Bailey et al. It also does not use the 960-parameter grid, the 8 symbol choices, or the 5 regime choices. The report's interpretation ("PBO < 0.5 means we can reject the null at the 50% confidence level") is not a property of PBO; PBO is the probability that the selected best strategy underperforms the median out-of-sample, not a hypothesis test with a 50% confidence level.

The peer function reproduces **0.489** on the 129 pooled trades. That number is real, but it is not the statistic the report names.

### 3.2 Proper CSCV PBO (S=16, 12,870 combinations)

We implemented the standard CSCV: split the return matrix into 16 contiguous blocks, use all 8-block in-sample combinations, select the best in-sample Sharpe, rank its out-of-sample Sharpe, and compute the fraction of combinations with logit <= 0.

| Config set | Sample | PBO | Status |
|---|---|---:|---|
| Peer `pbo()` bootstrap | 129 pooled trades | 0.489 | **Not CSCV**; ~0.5 by construction |
| 8 symbol strategies (best params, regime-filtered) | OOS test window | **0.840** | FAIL |
| 5 selected symbols (BTC/ETH/SOL/XRP/ADA) | OOS test window | **0.945** | FAIL |
| 3 rejected symbols (DOGE/AVAX/LINK) | OOS test window | **0.970** | FAIL |
| 960-param grid, pooled 8 symbols | OOS test window | **0.237** | PASS, but not the selection actually used |
| 960-param grid, pooled 5 symbols | OOS test window | **0.310** | PASS |
| 960-param grid, pooled 8 symbols | full sample | **0.0138** | PASS |
| 960-param grid, pooled 5 symbols | full sample | **0.0435** | PASS |
| Best-param 8 symbols | full sample | **0.2166** | PASS |
| Best-param 5 symbols | full sample | **0.1135** | PASS |
| Proper regime-filtered 8 symbols | full sample | **0.4600** | borderline PASS |
| Proper regime-filtered 5 symbols | full sample | **0.3975** | PASS |
| Post-hoc regime-filtered 8 symbols | full sample | **0.0000** | in-sample artifact, not evidence |

**Interpretation.** A proper CSCV PBO is *config-set dependent*. The parameter-grid PBO is low (0.01–0.24), but the **symbol-selection PBO is high (0.84–0.97)** on the OOS window, and the proper regime-filtered strategy's full-sample PBO is 0.46 (8 symbols) / 0.40 (5 symbols). The report's 0.489 is neither of these. The claim "PBO 0.489 < 0.5" is therefore **not established by a valid CSCV computation**; it should be marked `FAIL as reported` / `UNVERIFIED` as a single number until the config set is declared and the CSCV is computed on it. The high symbol-selection PBO is the most relevant number for the claim as written, because the report explicitly selected BTC/ETH/SOL/XRP/ADA and rejected DOGE/AVAX/LINK after seeing OOS.

**Note on the full-sample post-hoc PBO of 0.0:** this is not a positive result. The post-hoc filter on the full sample produces 625 trades with 73.9% win rate, PF 6.00, and +83,673% compounded return, dominated by the training period. This is the signature of in-sample selection, not a stable edge; the OOS post-hoc result is PF 1.21 and the proper OOS result is PF 0.97.

---

## 4. Multiple testing — the claim fails before correction

The pooled OOS result is not statistically significant even at `alpha=0.05` *before* any multiple-testing correction:

- per-trade Sharpe `0.08031`, `n=129`, `t=0.9121`, one-sided `p=0.1808`; two-sided `p=0.3617`;
- Newey–West trade t=1.00 (p=0.317); bar-level NW t=0.823 (p=0.411);
- 95% CI for mean per-trade return: `[-0.001153, +0.003161]`, includes zero.

Bonferroni thresholds at the stated counts:

| N | alpha/N |
|---:|---:|
| 960 | 5.21e-5 |
| 7,680 | 6.51e-6 |
| 76,800 | 6.51e-7 |

The observed p=0.1808 is far above all of them. BH-FDR across the 8 per-symbol tests also rejects none:

| Symbol | n | Per-trade SR | t | p (one-sided) | BH q | Reject? |
|---|---:|---:|---:|---:|---:|---|
| BTC | 11 | 0.2202 | 0.730 | 0.2326 | 0.5898 | no |
| ETH | 21 | 0.1902 | 0.872 | 0.1917 | 0.5898 | no |
| SOL | 26 | 0.1012 | 0.516 | 0.3029 | 0.5898 | no |
| XRP | 7 | 0.1268 | 0.336 | 0.3686 | 0.5898 | no |
| ADA | 7 | 0.4198 | 1.111 | 0.1334 | 0.5898 | no |
| DOGE | 5 | -0.1970 | -0.440 | 0.6702 | 0.6702 | no |
| AVAX | 33 | -0.0592 | -0.340 | 0.6332 | 0.6702 | no |
| LINK | 19 | -0.0437 | -0.191 | 0.5756 | 0.6702 | no |

**Verdict: FAIL.** The report's "all gates pass" depends entirely on the miscomputed z≈16. With a correct test, the point estimate is not distinguishable from zero, and the multiple-testing correction makes it worse.

---

## 5. OOS integrity

### 5.1 Split and window

The data span is 2024-11-15 00:00Z .. 2026-11-14 16:00Z (730 days, 4,373 4h bars per symbol). `TRAIN_FRAC=0.7` (`regime_filtered_vwap_v12.py:27`), `te=int(n*0.7)` (`:130`) gives 3,061 train bars and 1,312 test bars. The test window is **2026-04-10 04:00Z .. 2026-11-14 16:00Z = 218.5 days = 7.18 months**. The report's "~22 months OOS" is inconsistent with the code and the data by a factor of ~3. The full 730-day span is ~24 months; the OOS slice is only the last 7.2 months. This alone invalidates the "~22 months OOS" claim.

### 5.2 v7 and v12 share the same test window

`vwap_4h_v7.py` uses the same `730d`/`4h` data, the same `TRAIN_FRAC=0.7`, and the same `test_df = df.iloc[te:]` (`vwap_4h_v7.py:106`). Its per-symbol OOS results are the **same last-30% window** used by v12. The report cites v7's raw VWAP OOS results and uses them to argue the edge improves OOS and to select 4h/symbols. The v12 `BEST_PARAMS` are hardcoded from v7/v11 (`regime_filtered_vwap_v12.py:31-40`). Under `PROTOCOL.md` §4, an OOS window already inspected is "seen" and no longer counts as clean. v12 is not a clean OOS test of an untested hypothesis; it is a re-use of the v7 test window with a post-hoc regime filter. For AVAX/LINK, the params are not present in the v7 JSON, so their train-only selection is `UNVERIFIED`.

### 5.3 Symbol selection and the 129 vs 72 inconsistency

The report says "5 Symbols, 4h, 129 trades" and shows a 5-row per-symbol table, but 129 is the **8-symbol** total. The 5-symbol subset is 72 trades. The 3 symbols the report says were rejected (DOGE/AVAX/LINK) contribute 57 trades and -5.02% total return; they are included in the 129-trade aggregate that produces PF 1.210 / 12.7%. The 5-symbol subset alone produces PF **1.629**, total return **18.66%**, MDD **3.52%**, per-trade Sharpe **0.1941** (annualized by trade frequency **2.13**, not 3.76). The report mixes the 5-symbol table with the 8-symbol aggregate. If the 3 symbols were genuinely rejected ex ante, the headline should be 72 trades; if they were not, the table should show 8 rows. Either way, the reported universe is inconsistent.

The choice of the 5 winners after seeing OOS is exactly the selection-on-OOS that `PROTOCOL.md` §8 rejects: "A candidate that is 'significant' only because it was selected after seeing OOS is rejected." The 5-symbol post-hoc result (PF 1.63) is not a clean result; it is the best 5 of 8 after the fact.

### 5.4 Report inconsistencies

- **ADA row:** the report says PF 2.23, Sharpe 13.59, return +4.2%; the saved v12 JSON says PF 2.987, Sharpe 19.645, return +7.03%. The aggregate matches the JSON, so the ADA row is from a different run or a transcription error. It is `FAIL` to reproduce as printed.
- **MDD range:** the executive summary says "MDD=3.5-12.7%"; 12.7% is the total return, not an MDD. The observed MDDs are 3.52% (4-symbol subset), 9.99% (8-symbol pooled), and 10.995% (time-indexed). The range is mislabelled.
- **Test B is not independent:** Test B (4 symbols, 65 trades, PF 1.435, MDD 3.52%) is exactly the 4-symbol subset of Test A. We reproduce PF 1.43494, n=65, MDD 3.52%. Its Sharpe 7.10 is `0.15165 * sqrt(2190)`, the same annualization error. Counting Test A and Test B as two independent validations is double-counting the same trades.
- **"Edge improves OOS":** the v7 JSON's train Sharpes are 8.8–12.1 and test Sharpes are -4.7 to 3.5 per symbol; the raw VWAP edge decays, it does not improve. The report's "raw VWAP IS Sharpe=0.28 -> OOS Sharpe=3.10" is not supported by the v7 JSON and is `UNVERIFIED`.

### 5.5 The post-hoc regime filter is not a valid backtest

The v12 code runs the VWAP strategy on all test bars and then discards trades whose entry regime is not MR-compatible (`regime_filtered_vwap_v12.py:73`). This is **post-hoc filtering of a trade sequence that was generated without the filter**. It does not simulate the claimed strategy, because:

- the strategy can be in a non-MR position and therefore miss later MR entries;
- discarding a trade after the fact changes the trade sequence, capital path, and subsequent entries;
- the retained subset is selected on realized outcomes, not on a causal entry rule.

A correct implementation skips entries when the regime is not compatible. We ran both. With the same params, data, costs, and regime vector:

| Implementation | Trades (OOS) | PF | Per-trade SR | Total return | MDD |
|---|---:|---:|---:|---:|---:|
| v12 post-hoc filter (no lag) | 129 | 1.210 | 0.0803 | +12.70% | 9.99% |
| Proper skip-entry filter (no lag) | **355** | **0.974** | **-0.0113** | **-7.23%** | **23.39%** |
| Proper skip-entry filter (1-bar lag) | 359 | 0.957 | -0.0185 | -10.43% | 24.50% |
| Proper skip-entry, MR only (no UNKNOWN) | 354 | 0.961 | -0.0174 | -9.60% | 23.39% |

**Verdict: FAIL.** The correct implementation loses money out of sample. The v12 result is an artifact of post-hoc selection, not a tradable regime filter.

### 5.6 Regime detector usage

`alpha_engine/regime_detector.py` is written for a 60-bar price window with "7d/20d" ROC and "ADX" proxies. v12 passes 4h bars, so the function's "days" are actually 4h bars (20 bars = 3.3 days, 7 bars = 1.2 days). The labels are not the documented daily regimes. v12 also computes the regime on each symbol's own close, despite the docstring saying the input is a BTC price series. In practice, the filter keeps 126 `MEAN_REVERTING`, 2 `UNKNOWN`, and 1 `CRISIS` trade; it does not exercise the 5-regime set the report describes. The `UNKNOWN` category is allowed, so the first 60 test bars (regime warm-up) are not filtered, which is a minor but real inconsistency. These issues are `CONDITIONAL`/`UNVERIFIED` as a regime classifier, but they do not rescue the OOS result.

---

## 6. Economic validity

### 6.1 The Sharpe 3.76 is an annualization artifact

The per-trade statistics are:

```
mean = 0.00100397
std  = 0.01250135
SR_trade = 0.0803091
n = 129
```

The claim's annualization is `SR_ann = 0.0803091 * sqrt(2190) = 3.75826`, where 2190 = 6 bars/day × 365 days. That factor assumes **one independent trade per 4h bar for two years**, i.e. 2,190 trades/year. The strategy has 129 trades over 7.18 months, or **215.6 trades/year**. The correct trade-frequency annualization is `0.0803091 * sqrt(215.64) = 1.1793`. The time-indexed portfolio (P&L assigned to exit bars, 1,312 bars, zero when flat) gives:

```
mean_bar = 9.871e-5
std_bar  = 0.0041822
SR_bar   = 9.871e-5 / 0.0041822 * sqrt(2190) = 1.1046
ann_vol  = 0.0041822 * sqrt(2190) = 19.57%
arith_ann_return = 9.871e-5 * 2190 = 21.62%
CAGR = (1.125386)^(1/0.59822) - 1 = 21.83%
```

The claimed Sharpe 3.76 with 19.57% vol would imply an arithmetic annual return of `3.758 * 19.57% = 73.6%`, or a 12.7% total return over a much longer window. The actual 12.7% over 7.18 months is 21.8% CAGR at 19.6% vol, consistent with Sharpe ≈ 1.1, not 3.76. If the report's "22 months" were true, the CAGR would be 6.65% and the Sharpe at 19.6% vol would be ~0.34. In no consistent reading is 3.76 plausible.

Per-symbol correct annualized Sharpes (trade-frequency, 7.18-month window) versus the report's values:

| Symbol | Report Sharpe | Correct SR (trade-frequency) | n |
|---|---:|---:|---:|
| BTC | 10.30 | 0.944 | 11 |
| ETH | 8.90 | 1.127 | 21 |
| SOL | 4.74 | 0.667 | 26 |
| XRP | 5.94 | 0.434 | 7 |
| ADA | 13.59 (doc) / 19.645 (JSON) | 1.436 | 7 |
| DOGE | not shown | -0.570 | 5 |
| AVAX | not shown | -0.440 | 33 |
| LINK | not shown | -0.246 | 19 |

The report's per-symbol Sharpes are the same `sqrt(2190)` inflation. The 5 selected symbols still have positive corrected Sharpes (0.43–1.44), but they are not statistically significant (all p>0.13, BH q>0.58), and the 3 rejected symbols are negative.

### 6.2 Statistical significance

- simple t = 0.9121, one-sided p=0.1808, two-sided p=0.3617;
- Newey–West trade t=1.000, p=0.3173 (two-sided);
- Newey–West bar t=0.8227, p=0.4107 (two-sided);
- 95% CI mean per-trade: `[-0.001153, +0.003161]` (includes zero).

The point estimate of total return is positive, but it is not statistically distinguishable from zero. The report's "z≈16" is the only reason it looked significant.

### 6.3 Cost sensitivity

The base cost is 10 bps per side, 20 bps round trip, scaled by 0.4 position size. Stress results on the 129 pooled trades:

| Round-trip cost | PF | Total return | Per-trade SR | Annualized SR (trade-frequency) | MDD |
|---:|---:|---:|---:|---:|---:|
| 20 bps (base) | 1.210 | +12.70% | 0.0803 | 1.179 | 9.99% |
| 30 bps | 1.121 | +7.03% | 0.0483 | 0.709 | — |
| 40 bps (2x base) | **1.039** | **+1.65%** | **0.0163** | **0.239** | **13.95%** |
| 50 bps | **0.964** | **-3.46%** | **-0.0157** | negative | **15.86%** |
| 100 bps | 0.667 | -25.44% | -0.1757 | negative | — |

The report itself admits "at 50 bps PF would drop below 1.0"; we confirm PF 0.964 and a negative return. The protocol's 2x-cost gate (40 bps round trip) requires OOS Sharpe ≥0.5 and above benchmark. The annualized trade-frequency Sharpe at 40 bps is 0.239, below 0.5. **Gate 7 fails.** The edge is also concentrated near the cost threshold: a 10 bps increase in round-trip cost (20 -> 30 bps) cuts total return from 12.7% to 7.0%, and a 20 bps increase (20 -> 40 bps) cuts it to 1.65%.

### 6.4 Execution lag

The strategy enters at the **same-bar close** (`verified_strategies/strategies/vwap_reversion.py:68` reads `close.iloc[i]`; `:137-139` sets `entry_price = price`). There is no `t+1` execution. The protocol requires signals at close `t` and positions from `t+1` (`PROTOCOL.md` §5; `PROTOCOL_v3.md` §3). We simulated a one-bar lag on the correct skip-entry filter: PF **0.957**, per-trade SR **-0.0185**, total return **-10.43%**, MDD **24.50%**. The post-hoc filter with a one-bar lag gives an even better PF (2.16), which is a red flag: the result is highly sensitive to the trade sequence and is not a stable edge. **Execution-lag gate fails; the code has zero lag.**

The stop-loss and take-profit checks also use only the close (`vwap_reversion.py:68-108`); high/low are used for the VWAP band, not for intrabar stop fills. A stop breached within a 4h bar is therefore not filled at the stop until the close, which is optimistic in a fast market. The parallel replication report `validation/VWAP_REPLICATION.md` (VWAP-R1) counts 61% of trades breaching the stop intrabar and reports PF 0.810 / return -17.4% with intrabar stops. That count is **UNVERIFIED by this reviewer**, but the code path is clear: the backtest has no intrabar stop model. This is a material execution risk, not a minor caveat.

### 6.5 Capital and concurrency

The pooled statistic compounds `(1 + scaled_pnl)` across 129 trades as if they occur sequentially with no capital constraint. In reality, the maximum number of concurrent positions is **7**. At 40% per position, the gross exposure at that point is **280% of capital**. The 12.7% total return is therefore a levered, non-capital-constrained number. Scaling the whole P&L path to a 100% gross cap (divide by 2.8) gives:

- total return **4.60%** over 7.18 months (~7.8% CAGR);
- MDD **3.61%**;
- Sharpe unchanged (scale-invariant) at ~1.1.

The report's "40% position sizing is critical for MDD control" is not a capital model. It ignores concurrent positions, margin, and funding/borrow costs. The strategy is long/short; crypto perpetual funding is not modeled. **Capital gate: CONDITIONAL/FAIL** — the headline return requires up to 2.8x gross exposure and the risk model is incomplete.

### 6.6 Benchmark

Over the same 7.18-month OOS window:

- BTC buy-and-hold: total return **-8.25%**, Sharpe **-0.194**, MDD **29.39%**;
- equal-weight 8 crypto: total return **-18.49%**, Sharpe **-0.394**, MDD **35.63%**.

The strategy's +12.7% beats both on the point estimate, and the corrected time-indexed Sharpe 1.105 clears "benchmark + 0.30" (-0.194 + 0.30 = 0.106). So gates 1 and 2 pass on the point estimate **if** one accepts the 7.2-month, selected window. But the protocol's clean-OOS gate fails, the result is not statistically significant, and the comparison is not risk-matched (the strategy is flat much of the time and uses 40% sizing). This is a `CONDITIONAL` pass at best, not evidence of a proved edge.

---

## 7. Gate-by-gate comparison

Protocol v1 §7 gates plus the v3 additions named in the task.

| # | Gate | Requirement | Claim / recomputation | Status |
|---:|---|---|---|---|
| 1 | OOS net Sharpe | ≥1.0 and ≥ benchmark + 0.30 | 1.105 (time-indexed) ≥ 1.0; > -0.194+0.30=0.106 | **CONDITIONAL** (point estimate; not significant, contaminated OOS) |
| 2 | OOS net CAGR / total return | >0 and > benchmark | +21.8% CAGR / +12.7% total vs BTC -8.25%, EW8 -18.49% | **CONDITIONAL** (point estimate; 7.2-month selected window) |
| 3 | n ≥30 OOS trades | ≥30 | 129 (8-symbol) / 72 (5-symbol) | **CONDITIONAL** (count passes; universe inconsistent) |
| 4 | DSR | ≥0.95 at N=candidates | 0.8285 (N=1); 0.0109 (N=960); 0.0022 (N=7,680); 0.00036 (N=76,800) | **FAIL** |
| 5 | PBO | <0.50 where CSCV | 0.489 is not CSCV; proper CSCV 0.840 (8-symbol OOS), 0.945 (5-symbol), 0.970 (3-symbol); grid 0.014–0.237 | **FAIL as reported / UNVERIFIED** |
| 6 | Bootstrap p05 | >0 (block 20, 2,000 resamples) | trade p05 **-0.02969**; bar p05 **-1.3211** | **FAIL** |
| 7 | 2x cost | Sharpe ≥0.5 and > benchmark | 40 bps: PF 1.039, SR_trade 0.0163, annualized 0.239 | **FAIL** |
| 8 | Parameter stability | sign stable; train-only neighborhood | per-symbol params vary 30–100 VWAP, 0.75–1.5 band, 7–10% TP, 20–40 hold; no neighborhood grid; proper filter negative | **FAIL / UNVERIFIED** |
| 9 | No lookahead / survivorship | point-in-time, no backfill, no OOS selection | v7/v12 share the test window; 5 symbols selected after OOS; post-hoc regime filter; zero execution lag | **FAIL** |
| 10 | Walk-forward aggregate | Sharpe ≥0.8 and > benchmark | not performed | **UNVERIFIED** |
| 11 | CPCV | median OOS Sharpe ≥0.5 and PBO <0.5 | not performed; CSCV symbol PBO 0.84 | **FAIL / UNVERIFIED** |
| 12 | Reality Check / SPA | p<0.05 across N=20 | not performed | **UNVERIFIED** |
| 13 | Execution lag (v3) | extra-period Sharpe ≥1.0 and > benchmark | proper 1-bar lag: PF 0.957, SR -0.0185, -10.43% | **FAIL** |
| 14 | Capital | capital-constrained, no unmodeled leverage | max 7 concurrent × 40% = 280% gross; 100%-cap total return 4.60% over 7.18 months; funding/borrow not modeled | **CONDITIONAL / FAIL** |
| 15 | Clean OOS | OOS not previously inspected | v7 test = v12 test; symbol selection on OOS | **FAIL** |

**Overall: FAIL.** Gates 1–3 pass only as point estimates on a contaminated window; gates 4–9 and 13–15 fail or are unverified. The report's "all statistical gates pass" is false.

---

## 8. Top 6 risks

1. **The DSR is not DSR (fatal).** `N=1`, annualized SR in a per-period SE, and a hand-rolled `p_pass` saved as `dsr_probability`. The correct DSR is 0.8285 even with no multiple testing, and 0.0022 at N=7,680. The "z≈16 / 1.0000" is the `sqrt(2n)` ceiling of the misapplied formula, not a 16-sigma edge.
2. **The PBO is not CSCV (fatal).** The 0.489 is a bootstrap tail probability that is ~0.5 by construction. A proper CSCV over the 8-symbol selection set is 0.840; over the 5 selected symbols 0.945; over the 3 rejected symbols 0.970. The claim's PBO gate is not supported by its own computation.
3. **The regime filter is post hoc, not a strategy (fatal).** Filtering trades after running an unfiltered backtest changes the trade sequence and selects on outcomes. The correct skip-entry implementation yields 355 trades, PF 0.974, SR -0.0113, total return -7.23%, MDD 23.39% OOS. The claimed edge is an artifact.
4. **OOS contamination and universe mislabelling.** v7 and v12 use the same last-30% test window; the report uses v7's test results to select 4h/symbols; DOGE/AVAX/LINK were rejected after OOS but still contribute 57 of the 129 trades; the "5 symbols, 129 trades" table sums to 72; the OOS window is 7.18 months, not ~22. The ADA row does not reproduce.
5. **Sharpe 3.76 is an annualization artifact.** Per-trade SR is 0.0803; the code multiplies by `sqrt(2190)` although the strategy trades 215.6 times/year. Correct portfolio Sharpe is 1.105. The t-stat is 0.912 (p=0.181), the NW p is 0.32, and the 95% CI for the mean trade includes zero. A 3.76 Sharpe at 19.6% vol would imply ~73.6% annual return, inconsistent with 12.7% over 7.18 months.
6. **Cost, execution, and capital fragility.** At 2x cost (40 bps RT) annualized Sharpe is 0.239 and total return 1.65%; at 50 bps PF is 0.964 and the return is negative. The code has zero execution lag; a 1-bar lag on the correct filter loses 10.4%. Stops and targets are checked only on the close, not intrabar (a parallel replication's 61% intrabar-breach count is UNVERIFIED here, but the code path is clear). The headline return requires up to 280% gross exposure; capital-constrained to 100% it is 4.60% over 7.18 months, and funding/borrow is unmodeled.

---

## 9. Recommendation

**Verdict: `FAIL` — `NOT_PROVED`.** The claim cannot be called PROVED, VALIDATED, or "all gates pass". The arithmetic of the saved v12 JSON is reproducible, but the statistical inference is invalid at the DSR, PBO, significance, OOS-integrity, implementation, cost, execution, and capital levels.

Recommended next steps if the team wants to continue this line:

1. **Re-implement the regime filter causally.** Skip entries when the regime is not compatible; do not filter trades after the fact. Report the skip-entry result, including the negative OOS result.
2. **Add a 1-bar execution lag** (signal at close `t`, entry at `t+1`) and report the lagged result as the headline, not an optional stress.
3. **Use a clean OOS window** that was never used for symbol/param/regime selection. Freeze the protocol before looking. Do not reuse the v7 test window.
4. **Compute the true DSR at the actual N** (at least 960 × 8 = 7,680; include all v7/v9/v11–v17 looks and the 5 regime variants) and a **proper CSCV PBO** with a declared config set. Report the symbol-selection PBO separately.
5. **Report capital-constrained returns** with a 100% gross cap, concurrent-position accounting, and funding/borrow for shorts. Do not headline a 40%-per-trade result that reaches 280% gross.
6. **Report 2x cost (40 bps RT)** and a 1-bar lag as gates, not caveats. At 40 bps the current result is PF 1.039 / Sharpe 0.239; at 50 bps it is negative.
7. **Fix the reporting:** 8 symbols vs 5 symbols, 129 vs 72 trades, 7.18 months vs 22 months, ADA row vs saved JSON, Test B as a subset of Test A, and the `dsr_probability` field as `p_pass` not DSR.
8. **Independent replication** by a separate agent on a fresh data vendor (Binance, not yfinance) before any `PROVISIONAL` label.

The complementary `ITERATION-005` claim in the same update ("diversified vol-targeted trend, net Sharpe 2.13") is outside the scope of this review and is marked **UNVERIFIED** here; it requires its own audit.

---

## Appendix A — Formulas used

Let `r` be per-trade net returns (after 20 bps RT and 40% scaling), `n=129`.

```
SR_trade = mean(r) / std(r, ddof=1)
t        = SR_trade * sqrt(n)
p_one    = 1 - Phi(t)
CI95     = mean(r) +/- 1.96 * std(r)/sqrt(n)
SR_ann   = SR_trade * sqrt(trades_per_year)      # correct trade-frequency
SR_bar   = mean(r_bar)/std(r_bar) * sqrt(2190)   # time-indexed portfolio
```

DSR (Bailey–López de Prado):

```
var_sr   = (1/(n-1)) * (1 - skew*SR + ((kurtosis-1)/4)*SR^2)
E[maxSR] = sqrt(var_sr) * [ (1-gamma)*Phi^-1(1-1/N) + gamma*Phi^-1(1-1/(N*e)) ]
DSR      = Phi( (SR - E[maxSR]) / sqrt(var_sr) )
gamma    = 0.5772156649
```

CSCV PBO (Bailey et al.):

```
split T returns into S contiguous blocks
for each combination of S/2 blocks as IS:
    choose config with max IS Sharpe
    compute its OOS Sharpe rank (1=worst, N=best)
    omega = rank/(N+1); logit = log(omega/(1-omega))
PBO = fraction(logit <= 0)
```

---

## Appendix B — Reproduction artifacts

Read-only audit scripts (not committed to the repo):

- `/tmp/kilo/vwap_audit.py` — reproduces v12, computes corrected metrics, DSR, cost, capital, bootstrap, CSCV over symbol configs.
- `/tmp/kilo/vwap_audit2.py` — proper skip-entry regime filter, 1-bar lag, 5/4/3-symbol subsets.
- `/tmp/kilo/vwap_audit3.py` — peer PBO function, Newey–West, proper-filter DSR/bootstrap, BTC grid CSCV.
- `/tmp/kilo/vwap_audit4.py` — 960-param grid CSCV on the OOS window for all 8 symbols.
- `/tmp/kilo/vwap_audit5.py` — 960-param grid CSCV on the full sample; best-param symbol PBO.
- `/tmp/kilo/vwap_audit6.py` — full-sample PBO over the actual regime-filtered symbol strategies.

Result JSONs:

- `/tmp/kilo/vwap_audit_results.json`
- `/tmp/kilo/vwap_audit2_results.json`
- `/tmp/kilo/grid_pbo_results.json`
- `/tmp/kilo/fullgrid_pbo_results.json`
- `/tmp/kilo/regime_full_pbo_results.json`

Data: yfinance `730d` / `4h`, downloaded 2026-11-14; 4,373 bars per symbol; OOS test 1,312 bars per symbol; OOS 2026-04-10 04:00Z .. 2026-11-14 16:00Z. Yahoo/yfinance is not the protocol's primary data source (`PROTOCOL.md` §2 names Binance Vision/API); the data provenance is therefore `CONDITIONAL` at best.

**No repository source was modified. This report is the only file added.**
