# What is actually required to "prove" an asset class is profitable

Research note, 2026-11-22. This precedes more backtesting on purpose: running more
backtests without a proof standard is how a system generates confident nonsense.

Every gate below is either implemented in this repo already (named) or is a gap I am filling.

---

## 0 The one sentence version

A backtest can never prove profitability. It can only fail to disprove a hypothesis
efficiently. **Proof requires out-of-sample forward rows with honest fills, honest costs,
and an honest null.** Everything else is filtering.

Statistically: a strategy that survives selection has a *maximized* statistic, not a
sampled one, and the distribution of a maximum over N trials is not the distribution of
one trial. That is the entire reason DSR/PBO exist.

---

## 1 The statistics that are required, and why each one

| # | Statistic | What it protects against | Why a hedge fund needs it | Status here |
|---|---|---|---|---|
| S1 | Net expectancy + bootstrap CI (one-sided) | Luck on a small sample | The only decision-relevant number | In the ledger (`p_value`, `net_ci_pct`) |
| S2 | Selection alpha (pick minus direction-adjusted buy-and-hold) | Beta dressed as skill | In a bull market everything is positive; alpha is the only skill measure | In the ledger (G8), but covers only 24.2% of CRYPTO rows |
| S3 | Deflated Sharpe Ratio (DSR) | Multiple-testing inflation of Sharpe | If you tried 200 things, the best Sharpe is inflated by construction | `alpha_agent/validation/sharpe_metrics.py`, `tools/pbo_cscv.py` |
| S4 | Probability of Backtest Overfitting (PBO/CSCV) | Choosing the in-sample best config | Measures whether the selection procedure picks noise | `tools/pbo_cscv.py`, `alpha_engine/rigorous_backtest_harness.py` |
| S5 | Benjamini-Hochberg FDR | Family-wise false discovery | With 374 cells, some will look great by chance | In the ledger (`multiplicity`) |
| S6 | Split-half / regime stability | A single regime or a single period | A strategy that only works in one regime is a regime bet | In the ledger; Mercury3 found 3 of 7 classes sign-flip |
| S7 | 2x-cost stress | Cost underestimation | Retail costs are the usual killer | In the ledger (G9), but every class currently fails it |
| S8 | Concentration (symbol/source/date share) | One lucky name or one batch | 82% single-source is not a strategy | In the ledger and in `tools/edge_screen.py` |
| S9 | Intrabar first-touch resolution | Look-ahead in TP/SL ordering | Daily bars cannot tell you which of TP/SL hit first | `alpha_engine/intrabar_resolver.py` |
| S10 | **Survivorship-free universe** | Delisted losers missing | Backtests on today's tickers are upward-biased by construction | **GAP** — needs a delisted-inclusive universe |
| S11 | **Point-in-time fundamentals** | Restatements, look-ahead | Using today's earnings number for a past date is leakage | **PARTIAL** (`tools/point_in_time_audit.py` flags earnings without lag) |
| S12 | **Walk-forward with purge/embargo** | Leakage across the hold period | Adjacent folds share overlapping trades | **PARTIAL** (`alpha_engine/walk_forward_backtester.py`) |
| S13 | **Forward rows, n>=100, at the gate** | Everything above is still in-sample | The only out-of-sample test that counts | **GAP** — 430 rows, all one hypothesis, all CRYPTO |
| S14 | **Benchmark coverage** | Alpha measured on a subset | Needs the same asset and window | `alpha_engine/benchmark_closed_ledger.py` |

The repo already has most of S1-S9 and S14. The material gaps are **S10 (survivorship),
S11 (point-in-time data), S12 (purged walk-forward) and S13 (forward rows)**. Those four are
exactly what separates "a nice backtest" from "a proven edge".

---

## 2 Why each asset class needs a DIFFERENT proof

This is the part most systems get wrong: they apply one template to eight markets.

### EQUITY
- **The mechanism is a fundamental event, not a price pattern.** The user's example is right:
  a name that consistently beats earnings and drifts up afterwards is the classic PEAD.
  The drift is real in the literature but has decayed, and it needs a *point-in-time* earnings
  surprise (SUE), not today's restated number.
- **Survivorship is fatal here.** Delisted and acquired names are exactly the ones that failed.
  A universe of today's tickers can turn a losing strategy into a winner. This alone is why
  the equity-momentum result cannot be trusted yet.
- **Needed:** delisted-inclusive universe, SUE from a point-in-time feed, sector-neutral
  benchmark, 40bp+ round-trip cost, and a 60-90 day hold because the drift is slow.
- What already exists: `tools/h010_pead_research.py` (killed, kill #6),
  `tools/eq1_pead_backtest.py` (verdict FAIL, IS Sharpe -0.02, WR 0.366),
  `tools/h034_anti_pead_reversal.py`, `baby_strategies/equity_earnings_drift_pead.py`.

### ETF
- **There is no "earnings drift" mechanism.** An ETF is a basket; its edge comes from
  asset allocation, rebalancing, and cross-sectional rotation, not from a single company's surprise.
- **The relevant edges:** time-series momentum, dual momentum, sector rotation, and
  volatility targeting. Look-ahead risk is high because index constituents are revised retroactively.
- **Cost matters most here relative to the edge**: at 5bp the whole gross edge can vanish (measured:
  cost eats 114% of gross in the ETF dossier).
- **The one number that must never be quoted:** `/audit` ETF daily PF 1.8752 versus intrabar 0.0187
  (100.28x). Use the intrabar figure.

### BOND / MUTUAL_FUND
- **Bond edges are carry and curve, not directional.** Duration, credit spread, and roll-down.
  Rate regimes dominate, so the sample is effectively a handful of independent regimes even with
  thousands of rows. Effective n is much smaller than row n.
- **Mutual funds are the worst possible test vehicle**: NAV-only, end-of-day, no shorting, with
  fees and redemption lags. A "signal" measured on daily NAV is mostly autocorrelation.
  This is why MUTUAL_FUND has 0 rows: the honest answer is that it cannot be measured this way.

### COMMODITY / FUTURES
- **Roll yield and storage/seasonality dominate**, and the contract matters: you trade a specific
  expiry, not a continuous series. Continuous-series backtests have a roll-splice bias.
- **COT data has a publication lag** (the H-101 look-ahead already found here). Point-in-time is
  mandatory.
- Small n is structural: a few contracts, quarterly seasonality.

### FOREX
- **Carry plus regime**, and the "edge" is often just leverage on a funding differential.
  8,014 rows look impressive but they are many trades of a few currency pairs, so effective
  independent sample is small (USDJPY alone was 35-40% of one cell).

### CRYPTO
- **The deepest sample and the fastest decay.** Edges here die in weeks because of copy-trading,
  and costs are high (9.96bp measured). It is the only class with forward rows today.
- Funding rate, basis, and market microstructure are the real edges; simple crossovers are exhausted.

### MEME / PENNY_STOCK / INDEX / SPORTS
- Cost 30bp and a fat left tail. Treat as a lottery unless a mechanism with positive skew is proven.
- INDEX is an alias that leaks rows out of the denominator; SPORTS has no rows at all.

---

## 3 The "consistent up pattern" test, done properly

For the user's example, "it keeps going up even when it dips", the rigorous version is:

1. **Define the signal ex ante** (e.g. SUE in the top decile, or the name's 200d trend positive).
2. **Measure the conditional forward return distribution** against a matched benchmark
   (same sector and beta, or the same asset's buy-and-hold), not against zero.
3. **Check the shape, not just the mean**: median (a repeated small edge), skew (a few big winners),
   hit rate, max drawdown, and worst-case holding time.
4. **Split by regime** (VIX, rate trend). If the sign flips by regime, it is a regime bet.
5. **Purge and embargo** around the event so the hold window does not leak into the next fold.
6. **Apply costs at 1x and 2x.**
7. **Count every variant you tried** and feed that N into DSR/PBO.
8. **Only then** allocate forward rows.

Step 3 is what most people skip: a 60% win rate with one devastating loss is not an edge,
it is negative skew. That is why PF and mean alone are insufficient and why I also report
median, worst trade, and drawdown.

---

## 4 What "proven" will mean in this project, concretely

A class is **PROVEN** only when ALL hold, on forward rows dated after registration:

- n >= 100 forward rows, intrabar-honest first-touch on 100% of them
- net PF CI lower bound > 1.0, or IR >= 0.5
- selection alpha CI lower bound > 0 on the same rows
- 2x-cost net CI lower bound > 0
- both split halves positive, no symbol > 60%, no source > 90%
- benchmark coverage >= 90%
- DSR >= 0.95 with the true trial count
- persists across 2 consecutive runs
- and the universe was survivorship-free and point-in-time

Anything less is labelled **CANDIDATE**, **WEAK**, or **KILL** and nothing else. There is currently
**no** class meeting these, and the honest count is n_proven 0.

---

## 5 What I will do next, in order

1. Fill S10/S11/S12 gaps where the repo has the pieces (purged walk-forward, point-in-time audit).
2. Re-run the equity families with a survivorship caveat stated up front, since the delisted universe
   is the one thing I may not be able to obtain for free.
3. Backtest the classes that have never had an honest run: BOND (curve/carry), ETF (dual momentum,
   intrabar), FOREX (carry with regime), with the S1-S9 gates applied.
4. For each class, publish one row: best candidate, its n, its CI, its failing gate, and whether
   it is worth forward rows.
5. Only register forward pods for candidates that clear the screening gates.

The expected outcome, stated now so it cannot be spun later: most classes will fail, and the
deliverable will be a ranked, documented list of what is worth forward-testing and what is dead.

---

## Provenance

- model: none (curator-written from the repo's own tooling inventory and the frozen evidence)
- inventory: `search_files` over `*.py` on 2026-11-22 for DSR/PBO/PEAD/survivorship implementations
- prior results cited: `backtest_results/eq1_pead_S1.json` (FAIL),
  `docs/backtests/EQ1_PEAD_S1_RESULTS.md`, `reports/h010_equity_pead_2026-05-18.md` (kill #6)

---

## 6 All-class sweep result (2026-11-22, `--min-n 1` so nothing is dropped)

A first sweep used `--min-n 100` and silently omitted six classes. That was a reporting defect:
a class with 4 rows must appear as INSUFFICIENT_N, not vanish. Re-run with no minimum:

| class | n | gross PF | net PF | 2x PF | CI-LB | halves | WF | verdict |
|---|---|---|---|---|---|---|---|---|
| CRYPTO | 11007 | 1.0462 | 0.9917 | 0.9404 | -0.1334 | -0.018/-0.014 | 2/5 | WEAK |
| FOREX | 8041 | 1.5000 | 1.0629 | 0.8008 | -0.0033 | -0.018/0.026 | 2/5 | WEAK |
| COMMODITY | 1506 | 0.6202 | 0.5219 | 0.4455 | -0.6638 | -0.221/-0.820 | 0/5 | KILL |
| EQUITY | 1224 | 0.9931 | 0.9390 | 0.8885 | -0.2068 | -0.252/0.140 | 2/5 | WEAK |
| UNCATEGORIZED | 149 | 0.7414 | 0.6626 | 0.5929 | -0.8314 | -0.316/-0.565 | 0/5 | KILL |
| MEME | 102 | 0.9237 | 0.8188 | 0.7278 | -2.2517 | 0.276/-1.262 | 3/5 | WEAK |
| ETF | 79 | 1.5737 | 1.4974 | **1.4256** | -0.2660 | 0.989/-0.089 | n/a | INSUFFICIENT_N |
| BOND | 77 | 0.8074 | 0.6959 | 0.6050 | -0.2931 | -0.149/-0.086 | n/a | INSUFFICIENT_N |
| FUTURES | 70 | 1.0627 | 0.9432 | 0.8420 | -0.5608 | 0.178/-0.277 | n/a | INSUFFICIENT_N |
| INDEX | 25 | 0.3919 | 0.2634 | 0.1846 | -0.6880 | -0.297/-0.405 | n/a | INSUFFICIENT_N |
| MUTUAL_FUND | 0 | - | - | - | - | - | - | NO_ROWS |
| SPORTS | 0 | - | - | - | - | - | - | NO_ROWS |

**Zero classes have a positive CI lower bound. Zero have both halves positive.** No class clears
even the CANDIDATE bar, so no class is worth forward capital on this evidence.

Notes on the classes asked about specifically:
- **ETF** is the only class whose PF stays above 1 at **2x cost** (1.4256), which is why it deserved a
  second look. It does not survive: 79 rows across many sources (largest 14 on QQQ), 27 rows with no
  `created_at`, 11 with empty `exit_reason`, and the mean is carried by a few outliers
  (SPY +15.02, GLD +18.86, XLK -23.41). That is noise with a positive mean, not a mechanism.
- **BOND** at 77 rows is below 1 at every cost level, and its effective sample is a handful of rate
  regimes, not 77 independent bets.
- **FUTURES** is 70 rows, net below 1, second half negative.
- **PENNY_STOCK** has no rows in `trading_picks` under this filter, so it is NO_ROWS rather than a
  measured class; `/audit` reports only 4 picks for it.
- **MUTUAL_FUND** has 0 rows, which is the honest structural answer: NAV-only, end-of-day, no shorting.
