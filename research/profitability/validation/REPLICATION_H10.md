# Independent Replication — H10 (SPY/QQQ RSI(2) + T-bill cash)

**Replication agent:** independent subagent (no repo source modified)
**Date:** 2026-11-14
**Root audited:** `research/profitability/`
**Isolated workdir:** `/tmp/h10_replication` (code/config copied; `cache/` excluded; all market data re-downloaded)
**Python:** pandas 2.2.3, numpy 2.4.6, scipy 1.17.1

**Claim under test:** H10 (SPY/QQQ RSI(2) entry<10, exit>50, max hold 5, 5 bps, idle cash at 13-week T-bill) has
OOS 2024-01-01..2026-11-13 Sharpe **1.85**, CAGR **22.0%**, maxDD **-7.6%**, DSR **0.979 (N=12)**,
p **0.0018**, PBO **0.238**.

---

## Verdict summary

| Task | Verdict | Basis |
|---|---|---|
| 1. Fresh-data numerical reproduction | **PASS** | Exact match to 10+ decimals; deltas 0.0000 |
| 2. Lookahead / leakage audit | **PASS** | `shift(1)` confirmed; RSI causal; cash aligned; no leak found |
| 3. Clean temporal holdout 2016-11-14..2017-12-31 | **PASS (executed)** | Positive but **underperforms B&H** on Sharpe and CAGR |
| 4. Out-of-universe DIA/IWM/VTI 2024-2026 | **PASS (executed)** | Edge is **not** SPY/QQQ-specific; present in all three |
| 5. Train-selected grid / pre-registration | **PARTIAL / UNVERIFIED** | Params 10/50/5 pre-registered via H7; H10 itself not pre-registered |
| 6. Overall claim as a **clean OOS** result | **FAIL (protocol §4)** | H10 reuses the OOS window H7 already used; OOS is "seen," not clean |

**Summary:** The headline arithmetic is reproducible exactly, and the code contains no lookahead that
would explain it. However, H10 is economically **H7 (the v1 RSI2 sleeve) plus T-bill interest on ~83%
idle cash**, evaluated on the **same 2024-2026 OOS window that H7 already used and failed**. By the
locked protocol's own §4 rule, H10's OOS is not clean. H10 also fails to beat a risk-matched passive
mix on total Sharpe, underperforms B&H in the clean 2016-2017 holdout, and its edge collapses under a
one-day extra execution lag (Sharpe 1.85 → 0.70). It should not be promoted to `PROVED` on this evidence.

---

## 1. Fresh-data reproduction

### Setup (repo source untouched)

```bash
rm -rf /tmp/h10_replication && mkdir -p /tmp/h10_replication/data
cd research/profitability
cp backtest.py strategies.py run_v2.py validate_h10.py \
   PROTOCOL.md HYPOTHESES.md PROTOCOL_ADDENDUM_1.md /tmp/h10_replication/
cp data/__init__.py data/loader.py /tmp/h10_replication/data/
mkdir -p /tmp/h10_replication/runs /tmp/h10_replication/validation
cd /tmp/h10_replication && python3 run_v2.py
```

The `/tmp` cache was empty at start. `run_v2.py` downloaded 22 Nasdaq ETF histories + the Treasury
13-week bill series fresh (manifest source `nasdaq` / `treasury.gov`; 2,514 rows per ETF,
2016-11-14..2026-11-13; T-bill 2,217 rows, 2018-01-02..2026-11-13).

**Fresh data check:** the re-downloaded `nasdaq_SPY_1d.csv`, `nasdaq_QQQ_1d.csv` and
`treasury_13w.csv` are **byte-identical** (same SHA-256) to the original cache, because both pulls
return the same vendor history as of 2026-11-13. This is a genuine re-download but **not an
independent data source**. SHA-256:
- SPY `c3ec90b1e2be599eefd5bf9f1a4caaa7abd3b07c98c98bbd4058311132ed5051`
- QQQ `f42b087bc9a8e343c346f85277454cb839e6cd832b315071762322b8c7dc84ad`
- T-bill `ed42dff398e92154368f03fe6f1ff86c8405cf08fc6d6e4977b1bdb7211374ef`

### Reproduced H10 metrics (fresh run)

| Metric (OOS 2024-01-02..2026-11-13, n=721) | Claimed | Reproduced | Delta |
|---|---:|---:|---:|
| Sharpe | 1.85 | **1.8451795287514774** | 0.0000 |
| CAGR | 22.0% | **21.9637%** | 0.000 |
| maxDD | -7.6% | **-7.6158%** | 0.000 |
| DSR (N=12) | 0.979 | **0.9788513242708463** | 0.0000 |
| p-value | 0.0018 | **0.0018018428773411976** | 0.0000 |
| PBO | 0.238 | **0.23768453768453768** | 0.0000 |

Additional reproduced detail:
- OOS total return 76.488%, annualized vol 11.090%, Sortino 1.554, Calmar 2.884, profit factor 2.254,
  hit rate 86.96%, turnover 39.15×/yr, avg exposure **0.1734**, **111** weight changes, **82** entries.
- Benchmark (equal-weight SPY/QQQ buy-and-hold, price-only, daily rebalanced, 0 bps): Sharpe
  **1.0234**, CAGR **18.5507%**, maxDD **-20.9544%**, total return 62.722%.
- Bootstrap OOS (2,000 × block-20, seed 7): mean 1.8583, p05 **1.2757**, p95 **2.6105**.
- 2× cost (10 bps): Sharpe **1.6834**, CAGR **19.6138%**.
- Train as reported by the run (2016-11-14..2023-12-29): Sharpe 0.6653, CAGR 6.6805%, maxDD -15.8388%,
  232 changes, 162 entries, exposure 0.1545.

**Verdict: PASS.** H10 reproduces exactly, far inside the ±0.05 Sharpe / ±0.5pp CAGR tolerance.

> Note: because only code/config were copied, the `/tmp` run's *combined* multiple-testing table has
> n=5 (v2 only); DSR uses the hard-coded `CUM_N = 12` and is unchanged. H10's own Sharpe/CAGR/maxDD/
> DSR/p/PBO do not depend on the v1 results file, and all match the original `runs/v2/results.json`
> to 10+ decimals.

---

## 2. Lookahead / leakage audit

### (a) `weights` at close t apply from t+1 via `w.shift(1)` — confirmed

`backtest.portfolio_returns` line 48: `port = (w.shift(1) * rets).sum(axis=1) - cost`.
Independent spot check (raw prices + weight CSV):

```
2024-01-03: sum(w[2024-01-02]*r[2024-01-03]) = -0.0105814849 = engine row (equal to 1e-15)
2024-01-04: sum(w[2024-01-03]*r[2024-01-04]) = -0.0041837725 = engine row
2024-01-08: sum(w[2024-01-05]*r[2024-01-08]) = +0.0174719358 = engine row
```

A clean re-implementation (no import of `backtest.py`) of the daily net returns from the weight CSV
and prices reproduces OOS Sharpe/CAGR/maxDD **exactly**: 1.8451795287514774 / 0.2196367988941514 /
-0.0761583498185935.

### (b) Three manual round trips from `h10_weights.csv` + prices

Signal at close t; position earns the close(t)→close(t+1) return; round trip pays 5 bps entry +
5 bps exit = 10 bps. RSI(2) values recomputed independently.

| # | Asset / state | Entry (close) | Exit (close) | RSI2 at entry | RSI2 at exit | Gross | Entry cost | Exit cost | Net segment |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | SPY only, w=1.0 | 2024-01-17, 472.29 | 2024-01-18, 482.43 | 9.13 (<10) | 70.99 (>50) | +0.8893% | 5 bps | 5 bps | **+0.8393%** |
| 2 | QQQ only, w=1.0 | 2024-02-21, 425.61 | 2024-02-22, 436.78 | 9.89 (<10) | 84.79 (>50) | +2.9276% | 5 bps | 5 bps | **+2.8776%** |
| 3 | SPY+QQQ, w=0.5/0.5 | 2024-04-04 | 2024-04-05 | SPY 5.57 / QQQ 7.93 | SPY 60.37 / QQQ 58.34 | SPY +1.0447%, QQQ +1.1784% → port +1.1115% | 5 bps | 5 bps | **+1.0615%** |

All three match the engine's daily rows exactly (weights, returns, costs). The RSI entry/exit
conditions are the declared `<10` / `>50`, and max-hold behaviour is consistent (held through day 5,
exit signal at the close of the last held day).

### (c) RSI(2) uses only past closes — confirmed

`strategies.rsi` is `diff()` → `ewm(alpha=1/n, adjust=False)` on the close series; no future values.
Causality test: recomputing RSI on data truncated at 2026-06-01, and again after halving **all**
closes after 2026-06-01, leaves every RSI value up to 2026-06-01 bit-identical. ✓

Full end-to-end check: an independent, from-scratch RSI2 state machine (manual Wilder EWM + hold
counter) regenerates `h10_weights.csv` with **max abs difference 0.0** for SPY, QQQ and CASH.

### (d) CASH return alignment — confirmed

`prep()` sets `rets["CASH"] = rate[t]/100/252`; `portfolio_returns` multiplies by `w.shift(1)["CASH"]`.
Spot check 2024-01-09: `w_CASH[t-1]=1.0000`, `rate[t]=5.4000`, `rets_CASH[t]=0.00021429`,
contribution `0.00021429` = engine row. The position is from t-1, the rate is same-date t (the intended
convention). Lagging the rate by one day changes OOS Sharpe from 1.8452 to 1.8453 — immaterial, so the
same-date rate introduces no material lookahead. ✓

### (e) Benchmark and cost handling — confirmed

- Benchmark weights are `buy_hold(SPY/QQQ)` only (`columns=['SPY','QQQ']`); after reindex to the
  return panel the `CASH` weight is **0.0**. The benchmark earns no T-bill return. ✓
- Costs are computed on `risk_cols = [c for c in w.columns if c != "CASH"]` only. Sum of turnover is
  347.0 risk-only vs 634.0 if CASH were included; the engine uses the 347.0 (risk-only) figure. ✓
- Benchmark is evaluated at 0 bps, so it pays no rebalancing cost (slight advantage to the benchmark,
  i.e. conservative for H10).

### Bugs / discrepancies found (none change the headline arithmetic)

1. **Cost timing is shifted one row (minor).** Cost at row t is charged against day t's return, but the
   weight change at row t executes at the close of t and affects returns from t+1. This moves each
   cost by one day; total round-trip cost is still 2×5 bps. Not lookahead (cost is known at t), and
   immaterial to the metrics.
2. **`_with_cash(risk, cash_ret)` ignores `cash_ret`.** The argument is dead; CASH returns come from
   `rets["CASH"]`. In this run the caller passes the same series, so the result is correct, but it is
   a latent inconsistency.
3. **`treasury_bill_daily(start_year)` ignores `start_year` when the cache exists.** It returns the
   cached 2018-2026 file even when 2016 is requested, and `cash_returns` then `.bfill()`s the 2018
   rate into 2016-2017. This silently corrupts any pre-2018 cash yield (worked around in §3 by
   fetching 2016-2017 directly). It does **not** affect the 2024+ OOS.
4. **`rsi()` returns 50 (not 100) when the down-EWM is exactly 0** (`fillna(50)` on a NaN ratio). Rare
   for liquid ETFs but a modeling nuance; no material effect found.
5. **PBO is computed over the 5 v2 candidates only**, not the 12 counted in DSR. `pbo_cscv` requires
   S≥4; with S=5 the rank estimator is coarse (ω ∈ {1/6..5/6}).
6. **The reported "train" window is 2016-11-14..2023-12-29, not the protocol's 2018-01-01..2023-12-31.**
   `split_metrics` uses `port.loc[:train_end]` with no lower bound. Protocol-train 2018-2023 is
   Sharpe 0.6054 / CAGR 6.44% / maxDD -15.84% (vs reported 0.6653 / 6.68% / -15.84%). This is a
   reporting discrepancy and it means the 2016-2017 period was included in the reported train and in
   the grid's "train" column (see §5).
7. **Benchmark is price-only (no dividends) while H10 earns T-bill interest.** This slightly favors
   H10. The repo's dividend-fairness test (hardcoded SPY 1.3% / QQQ 0.6%) still gives H10 the edge:
   1.86 vs 1.08 Sharpe, 22.2% vs 19.7% CAGR.
8. **Risk-matched benchmark uses full-period exposure (0.160), not OOS exposure (0.173).** Minor.
9. **Manifest overwrites `source` with `"cache"` on the second call within a run** (cosmetic; the
   first pull in this replication was fresh, and hashes match).

---

## 3. Clean temporal holdout: 2016-11-14..2017-12-31

Nasdaq's ~10-year cap makes 2016-11-14 the earliest available bar. RSI `min_history=30` skips the
first 30 bars, so the first actionable entry is late December 2016. The T-bill loader cache bug (§2.3)
was bypassed by fetching 2016 and 2017 Treasury CSVs directly; the actual 13-week coupon-equivalent
mean over the window is **0.898%** (not the 1.44% 2018 rate that the cache would have back-filled).

Command: `python3 holdout_oou.py` (in `/tmp/h10_replication`).

| Series (2016-11-14..2017-12-31, n=284) | Sharpe | CAGR | maxDD |
|---|---:|---:|---:|
| **H10 with actual 2016-17 T-bill** | **1.755** | **7.46%** | **-1.67%** |
| H10 with 0% cash | 1.563 | 6.62% | -1.67% |
| EW SPY/QQQ buy-and-hold | **2.835** | **25.76%** | -3.24% |
| SPY buy-and-hold | 2.729 | 20.35% | -3.03% |
| QQQ buy-and-hold | 2.661 | 31.27% | -5.14% |
| Risk-matched passive (11.3% B&H / 88.7% T-bill) | 3.698 | 3.47% | -0.29% |

- H10: 20 entries, 27 changes, avg exposure 0.113, excess-over-cash Sharpe 1.539.
- H10 is **positive with a very low drawdown**, but it **underperforms B&H on both Sharpe and CAGR**
  in this clean pre-2018 window. That is expected for a cash-heavy strategy in the 2017 melt-up, but
  it does not corroborate the 2024-2026 magnitude.
- The risk-matched passive mix had a higher total Sharpe (3.70) and much lower CAGR (3.47%); H10 beat
  it on absolute return but not on total Sharpe — the same pattern as the OOS window.
- Caveat: because the code's "train" starts in 2016, this window was included in the reported train
  metrics and grid train column (§2.6). It is a genuine holdout relative to the protocol's 2018 train
  start and relative to OOS, but it was not unseen by the code that produced the report.

**Verdict: PASS (the holdout was executed cleanly), but it does not support the headline edge.**

---

## 4. Out-of-universe replication: DIA, IWM, VTI (2024-01-01..2026-11-13)

Same H10 logic (RSI(2) <10 entry, >50 exit, max hold 5, 5 bps, idle cash at the same 13-week T-bill),
single-asset, run against each ETF's own Nasdaq history. All B&H comparisons are price-only.

| Asset | H10 Sharpe | H10 CAGR | H10 maxDD | B&H Sharpe | B&H CAGR | B&H maxDD | H10 expo / entries |
|---|---:|---:|---:|---:|---:|---:|---:|
| DIA | **1.358** | 11.18% | -7.12% | 0.883 | 12.15% | -16.51% | 0.143 / 44 |
| IWM | **1.280** | 12.36% | -7.85% | 0.645 | 11.99% | -27.88% | 0.136 / 38 |
| VTI | **1.936** | 18.66% | -7.69% | 1.068 | 16.93% | -19.59% | 0.135 / 43 |
| SPY/QQQ (ref) | 1.845 | 21.96% | -7.62% | 1.023 | 18.55% | -20.95% | 0.173 / 82 |

- All three out-of-universe ETFs produce a **positive, higher-Sharpe, lower-drawdown** result vs their
  own buy-and-hold in 2024-2026. DIA's CAGR slightly lags its B&H (11.18% vs 12.15%); IWM and VTI beat
  it.
- **Interpretation:** the 2024-2026 RSI(2) edge is **not specific to SPY/QQQ**. It appears across
  large-cap (DIA), small-cap (IWM) and total-market (VTI) ETFs. That is more consistent with a broad
  short-term-reversal regime in 2024-2026 than with a unique SPY/QQQ property.
- Caveat: B&H is price-only (no dividends) while H10 earns T-bill interest, a small bias in H10's
  favor; the relative conclusion (edge present) is robust to that.

**Verdict: PASS (executed); edge generalizes across US equity ETFs in this window.**

---

## 5. Train-selection and pre-registration

### What is verifiable

- `HYPOTHESES.md` (mtime 2026-11-14 18:15:38) line 14 pre-registers **H7**: "Equity RSI(2) mean
  reversion | SPY/QQQ | entry 10, exit 50, max hold 5, 5 bps". This predates `run_v1.py`
  (18:18:11) and `runs/v1/REPORT.md` (18:20:28).
- The 27-cell grid in `validate_h10.py` (mtime 18:22:43) was run **after** the results. It reports a
  "train Sharpe" column and an OOS column. The central cell 10/50/5 is **not** the train-best:
  - train-best over the code's full history (2016-2023): 10/40/3 → 1.013 vs central 0.665
  - train-best over the protocol window (2018-2023): 10/40/3 → 0.961 vs central 0.605
  So the central parameter value was **not** tuned on train, and it was **not** selected from OOS
  either. The OOS-best cell happens to be 10/50/5 (1.85), but that value was already pre-declared
  for H7, so this is a favorable coincidence rather than evidence of OOS tuning.
- Therefore the **parameter values** 10/50/5 are consistent with pre-registration.

### What is not verifiable / fails

- **H10 is not in `HYPOTHESES.md`.** The registry still lists only H1-H7, all `TESTING` /
  "pending v1", even after both v1 and v2 ran. This violates PROTOCOL §10 (registry status must be
  updated) and leaves the N=12 bookkeeping undocumented.
- **H10 is a v2 "exploratory" cash variant of H7**, created after H7's v1 OOS result. `run_v2.py`
  docstring: "H10 SPY/QQQ RSI(2) + T-bill cash (H7 capital-efficiency variant; exploratory)." H7 failed
  v1 for exactly one gate: `below_benchmark_return` (17.6% CAGR vs 18.6% benchmark; all other gates
  passed, DSR 0.9507, Sharpe 1.51).
- **PROTOCOL §4 clean-OOS rule is violated.** The protocol says: "If a version is revised after seeing
  OOS, the next version's OOS starts at the revision date ... and the prior OOS is demoted to 'seen'
  and no longer counts as clean." H10 reuses the **same** 2024-01-01..2026-11-13 window that H7
  already used and failed. H10's "OOS" is therefore **seen OOS**, not clean OOS.
- **No git history.** `research/profitability/` is untracked (`git status` shows `?? research/profitability/`),
  so there are no commits, tags, or signed timestamps. File mtimes are the only timing evidence and
  can be edited. Strong (cryptographic/independent) pre-registration is therefore **UNVERIFIED**.
- **The grid's "train-only" label is inaccurate.** The grid uses `pp.loc[:TRAIN_END]`, which starts in
  2016, not 2018; it includes the 2016-2017 holdout. This does not change the conclusion (central is
  not train-best under either window) but it is a documentation discrepancy.

**Verdict: parameter values pre-registered = PASS (content-level); H10 candidate-level
pre-registration and clean OOS = FAIL; immutable pre-registration = UNVERIFIED.**

---

## 6. Economic decomposition (material finding)

H10 and H7 use the **same risk signals** (the same 111 OOS weight changes, the same -7.6% maxDD). The
only difference is that H10 earns T-bill interest on the ~82.7% of capital that is idle.

| Series | OOS Sharpe | OOS CAGR | OOS maxDD |
|---|---:|---:|---:|
| H7 (identical weights, idle cash = 0%) | 1.5146 | 17.61% | -7.63% |
| H10 (idle cash = 13-week T-bill) | 1.8452 | 21.96% | -7.62% |
| Difference | +0.3306 | +4.35pp | +0.01pp |

The difference is exactly the cash carry: `(1 - 0.1734) × 4.38% = 3.62pp` of annualized mean
(realized mean difference 3.63pp). The OOS T-bill rate averaged **4.38%** (2024-2026), versus **1.96%**
in the 2018-2023 train and **0.90%** in the 2016-2017 holdout. The 22.0% OOS CAGR is therefore partly a
**high-rate-regime windfall**, not a new equity edge.

Other material sensitivities (reproduced):
- **Extra execution lag (targets shifted 2 days instead of 1): Sharpe 0.696, CAGR 8.18%, maxDD -14.22%.**
  The edge is concentrated in the first post-signal day. The result assumes market-on-close execution
  at the signal bar's close; if entry is delayed to the next close, the headline collapses.
- 10 bps cost: Sharpe 1.683; 20 bps: 1.349; 30 bps: 1.000.
- **Risk-matched passive benchmark** (17.34% SPY/QQQ B&H + 82.66% T-bill, daily rebalanced):
  Sharpe **2.168**, CAGR **7.05%**, maxDD -3.44%, vol 3.16%. It beats H10 on **total Sharpe** (2.17 vs
  1.85) but not on absolute return (7.05% vs 21.96%). H10's **excess-over-cash** Sharpe is 1.450 vs the
  passive mix's 0.783, so the timing does add excess return — but it takes ~3.5× the volatility.
- Against 100% buy-and-hold (the protocol's headline benchmark: Sharpe 1.02, maxDD -20.95%), H10 wins
  on Sharpe and drawdown, but B&H carries ~3× the exposure.

---

## 7. Discrepancies and UNVERIFIED items

**Verified:**
- All six headline numbers (Sharpe, CAGR, maxDD, DSR, p, PBO) reproduce exactly.
- `w.shift(1)` timing; RSI causality; CASH alignment; benchmark has no CASH; costs on risk weights only.
- 3 round trips reconcile to the engine; independent signal regeneration is exact.
- H7 pre-registration line and mtimes.
- 2016-2017 and DIA/IWM/VTI runs.

**UNVERIFIED / not supportable:**
- **Clean OOS status of 2024-2026 for H10** — contradicted by PROTOCOL §4 and by H7's prior use of the
  same window. This is a FAIL, not merely unverified.
- **Immutable pre-registration** — no git history; folder untracked; mtimes only.
- **N=12 as 12 independent pre-declared trials** — the registry documents 7 v1 + 5 v2 candidates, but
  H10 is an undocumented post-hoc variant of H7; the effective independent trial count is lower.
- **PBO 0.238 as a 12-candidate PBO** — it is computed over the 5 v2 candidates only.
- **Independent data source** — fresh download is the same Nasdaq/Treasury vendor and the same
  as-of date; CSVs are byte-identical. It does not test data-vendor robustness.
- **Dividend total return** — price-only closes; dividend-fairness test uses hardcoded yields.
- **Intraday/MOC fill quality** — daily bars only; execution at the signal close is assumed.

---

## 8. Reproduction commands

```bash
# 1. isolated copy (no cache)
rm -rf /tmp/h10_replication && mkdir -p /tmp/h10_replication/data
cd /home/eaguiar2015/findtorontoevents_antigravity.ca/.kilo/worktrees/finpredict-v2/research/profitability
cp backtest.py strategies.py run_v2.py validate_h10.py PROTOCOL.md HYPOTHESES.md \
   PROTOCOL_ADDENDUM_1.md /tmp/h10_replication/
cp data/__init__.py data/loader.py /tmp/h10_replication/data/
mkdir -p /tmp/h10_replication/runs /tmp/h10_replication/validation

# 2. fresh-data replication
cd /tmp/h10_replication && python3 run_v2.py          # ~59 s, 22 ETF + T-bill downloads
python3 validate_h10.py                              # robustness (identical to runs/v2/ROBUSTNESS.md)

# 3. independent audit (shift, round trips, RSI causality, CASH, benchmark/cost)
python3 audit_h10.py

# 4. clean holdout + out-of-universe
python3 holdout_oou.py

# 5. compare to original
diff -u <original>/runs/v2/REPORT.md /tmp/h10_replication/runs/v2/REPORT.md
diff -u <original>/runs/v2/ROBUSTNESS.md /tmp/h10_replication/runs/v2/ROBUSTNESS.md
```

Artifacts in `/tmp/h10_replication`: `runs/v2/results.json`, `runs/v2/REPORT.md`,
`runs/v2/ROBUSTNESS.md`, `runs/v2/h10_weights.csv`, `holdout_oou.json`, `audit_h10_out.txt`,
`holdout_oou_out.txt`, and the fetched cache.

---

## 9. Bottom line

- **As arithmetic:** the claim is **PASS** — H10 reproduces exactly on a fresh data pull, and the code
  has no lookahead that would explain the result.
- **As a "clean OOS edge":** the claim is **FAIL** — H10 is H7 plus T-bill carry, evaluated on the
  same OOS window H7 already used, in a period with unusually high cash yields. The clean 2016-2017
  holdout does not reproduce the magnitude (H10 1.76 Sharpe / 7.5% CAGR vs B&H 2.84 / 25.8%), the
  edge is not SPY/QQQ-specific (DIA/IWM/VTI show it too), and a one-day execution delay cuts Sharpe
  to 0.70.
- **Recommendation:** keep H10 as `PROVISIONAL` at most; do **not** promote to `PROVED`. Demote the
  2024-2026 window to "seen OOS" per PROTOCOL §4, add H10 to `HYPOTHESES.md`, record the cash-carry
  decomposition, and require a genuinely unseen window (e.g. post-2026-11-14) plus a risk-matched
  benchmark gate before any promotion.
