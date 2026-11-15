# Backtest and Research Record

**Agent:** buffy (Codebuff) · **Date:** 2026-11-15
**Engine:** `tools/sim_path_forward.py` · **Artifacts:** `artifacts/backtest_path_forward.json`, `artifacts/backtest_path_forward_2xcost.json`

---

## 1. Question and design rules (fixed before results were seen)

**Question:** is the proposed path — low-cost beta core + slow trend overlay, occasionally a short-horizon
swing rule — profitable after costs *and* better than the alternative the investor already has?

Design rules, all fixed in advance:

| Rule | Value |
|---|---|
| Trial count | **N = 8**, declared; adding a strategy invalidates the deflated Sharpe |
| Parameters | Textbook defaults only (Faber 10-month, 12-month momentum, RSI(2)<5, 200-day SMA, 60/40). **No search.** |
| Costs | 6 bps/side equity, 15 bps/side BTC, charged on every weight change. No cost-free run is reported as a result. |
| Cash | T-bill (`^IRX`) — never 0% |
| Split | IS 2003-01→2015-12 / OOS 2016-01→2026-11 (BTC: IS 2014-10→2020-12) |
| Benchmark | Each row's **own** exposure in SPY + cash. Absolute profitability is never reported as edge. |
| Stress | Full re-run at 2× costs |

---

## 2. Data

| Series | Source | Interval | Rows | Window |
|---|---|---|---:|---|
| SPY, TLT, GLD | Yahoo chart API, `adjclose` (div + splits) | monthly | 265 | 2004-12-01 → 2026-11-13 |
| SPY | same | daily | 6,506 | 2001-01-03 → 2026-11-13 |
| BTC-USD | same | daily | 4,442 | 2014-09-18 → 2026-11-13 |
| ^IRX (13-week T-bill) | same | daily | 6,493 | 2001-01-03 → 2026-11-13 |

Cached under `data/cache/sim/` (not committed — regenerable, large). Yahoo's daily endpoint requires
explicit `period1`/`period2`; `range=max&interval=1d` silently returns monthly bars (returned 407 rows
for SPY), which was caught and fixed during the build.

---

## 3. Method

| Metric | Definition used |
|---|---|
| Returns | Simple period returns net of cost: `w·r − abs(Δw)·c` |
| CAGR | `∏(1+r)^(1/years) − 1` |
| Sharpe | `mean(r − rf)·ppy / (sd(r − rf)·√ppy)` |
| Excess (ann.) | `mean(r − bench)·ppy` where `bench = exposure·SPY + (1−exposure)·rf` |
| IR | `mean(r − bench)·ppy / (sd(r − bench)·√ppy)` |
| Excess t-stat | `mean(d) / (sd(d)/√n)`, `d = r − bench` |
| Max drawdown | `min(eq / cummax(eq) − 1)` |
| DSR | Bailey & López de Prado (2014): `Φ((SR − SR₀)√(T−1) / √(1 − γ₃SR + ((γ₄−1)/4)SR²))`, `SR₀` from N trials and `var(SR)` **within the same frequency family** (monthly N=5, daily N=3) |

Deflated Sharpe uses **per-period** Sharpe and a trial variance computed within frequency
(monthly var 0.000792, daily var 0.003623). Mixing annualised monthly and daily Sharpes is the bug
described in §6.

---

## 4. The benchmark caveat — read this before quoting any excess number

The matched-exposure benchmark is built from the **realised** exposure path. For a pure long/flat rule
on the benchmark asset itself (e.g. FABER10 on SPY), that benchmark is a **cost-free clone** of the same
position — so `excess ≈ −costs` *by construction*, and the excess t-stat measures the reliability of the
cost stream, not the signal's information.

Consequence:

- **Do not** use the excess column to rank two long/flat SPY rules. It mostly ranks their turnover.
- **Do** use drawdown, Sharpe and Calmar for those rules — that is where the actual difference lives.
- For rules that hold a *different* asset than the benchmark (DUALMOM holding TLT, BTC rules vs SPY),
  the excess is a real cross-asset comparison and reads normally.

This is disclosed rather than hidden because the numbers look strange without it (FABER excess −0.09%
with t = −6.13 is exactly this artefact: 33 switches × 6 bps ÷ 22.08y = 0.0897%).

---

## 5. Results

### 5.1 Baseline (6 bps/side equity, 15 bps/side BTC)

| Strategy | Style | CAGR | Excess | IR | Sharpe | MaxDD | DSR | Trades | Exposure |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| BH_SPY | beta core | 10.76% | −0.00% | −0.213 | 0.65 | −50.8% | 0.99 | 1 | 1.00 |
| SIXTY_FORTY | beta core | 8.11% | −3.03% | −0.364 | 0.65 | −28.5% | 0.99 | 1 | 1.00 |
| FABER10_SPY | trend overlay | 8.33% | −0.09% | −1.304 | 0.66 | −21.8% | 0.99 | 33 | 0.78 |
| DUALMOM_2 | trend overlay | 7.59% | −2.57% | −0.177 | 0.50 | −27.6% | 0.96 | 28 | 0.91 |
| DUALMOM_3 | trend overlay | 8.13% | −1.88% | −0.100 | 0.45 | −30.0% | 0.94 | 55 | 0.92 |
| RSI2_SPY | swing | 0.21% | −2.30% | −11.399 | −0.64 | −14.5% | 0.00 | 117 | 0.02 |
| BTC_BH | beta core | 51.04% | +48.67% | 0.763 | 0.93 | −83.0% | 0.65 | 1 | 1.00 |
| BTC_TREND200 | trend overlay | 58.62% | +47.69% | 0.910 | 1.10 | −63.6% | 0.84 | 30 | 0.64 |

Gates passed (of 5: beats benchmark, IR>0, DSR≥0.95, OOS>0, IS>0):
`BH_SPY 1/5 · SIXTY_FORTY 1/5 · FABER10 1/5 · DUALMOM_2 1/5 · DUALMOM_3 1/5 · RSI2 0/5 · BTC_BH 4/5 ·
BTC_TREND200 4/5`. The BTC rules pass 4/5 only because their benchmark is SPY — a cross-asset artefact,
not skill; their DSR gate is the one that fails.

### 5.2 In-sample / out-of-sample

| Strategy | IS CAGR | IS excess | OOS CAGR | OOS excess |
|---|---:|---:|---:|---:|
| BH_SPY | 7.24% | −0.01% | 14.42% | 0.00% |
| SIXTY_FORTY | 7.77% | −0.18% | 8.45% | −5.90% |
| FABER10_SPY | 8.30% | −0.06% | 8.36% | −0.12% |
| DUALMOM_2 | 6.02% | −0.91% | 9.19% | −4.25% |
| DUALMOM_3 | 8.97% | **+2.55%** | 7.30% | **−6.34%** |
| RSI2_SPY | 0.56% | −1.79% | −0.17% | −2.87% |
| BTC_BH | 99.51% | +81.66% | 15.76% | +16.13% |
| BTC_TREND200 | 111.01% | +80.13% | 17.26% | +13.32% |

`DUALMOM_3` is the instructive row: **a full-sample average of −1.88% hiding a +2.55% success and a
−6.34% failure.** Reporting only the full sample would have called it "roughly flat"; the split
shows it is a regime bet that broke.

### 5.3 2× cost stress

| Strategy | CAGR | ΔCAGR | Sharpe | ΔSharpe | MaxDD |
|---|---:|---:|---:|---:|---:|
| BH_SPY | 10.75% | −0.00 | 0.65 | −0.00 | −50.8% |
| SIXTY_FORTY | 8.10% | −0.00 | 0.65 | −0.00 | −28.5% |
| FABER10_SPY | 8.23% | −0.10 | 0.65 | −0.01 | −22.1% |
| DUALMOM_2 | 7.44% | −0.14 | 0.49 | −0.01 | −27.9% |
| DUALMOM_3 | 7.85% | −0.29 | 0.44 | −0.02 | −30.7% |
| **RSI2_SPY** | **−0.34%** | **−0.54** | **−0.86** | **−0.22** | −20.4% |
| BTC_BH | 51.02% | −0.02 | 0.93 | −0.00 | −83.0% |
| BTC_TREND200 | 57.45% | −1.17 | 1.08 | −0.01 | −64.1% |

The swing rule is the only strategy where costs decide the sign. Everything else is cost-insensitive, so
its failure is about signal, not friction — which makes those verdicts robust to whatever cost assumption
the broker actually charges.

---

## 6. Bugs found and fixed during the build

Documented because each one would have produced a confidently wrong number:

| # | Bug | Symptom | Fix |
|---|---|---|---|
| 1 | `fetch()` returns `(dates, prices)` but the BTC call assigned only prices to the price variable | `IndexError: index 6492 out of bounds for axis 0 with size 6492`, then "only 0 return periods" | Align both series on dates explicitly; raise if < 500 common days |
| 2 | Daily returns sliced `[1:]` twice (off-by-one between position and return arrays) | Position on day t earned day t−1's return — a one-bar lookahead | `pos[:-1]` paired with `rets` from the same alignment; assert equal lengths |
| 3 | Cash earned 0% inside strategies while the benchmark paid T-bill | Every cash-holding rule looked worse than it was; 60/40 and FABER were understated | Cash leg earns `^IRX` (monthly mean ÷ 12; daily ÷ 252) in both strategy and benchmark |
| 4 | DSR mixed annualised monthly and daily Sharpe in one trial-variance pool | SPY reported DSR 0.14 (absurd) | Per-period Sharpe + variance computed **within** frequency family; SPY now 0.99 |
| 5 | Hardcoded "sample size needed" table was wrong | Would have justified killing strategies that only needed 39 trades | Correct formula `n = ((1.645+0.842)/SR)²`: 0.40→39, 0.30→69, 0.20→155, 0.15→275, 0.10→619 |
| 6 | `range=max&interval=1d` on Yahoo silently returns monthly bars | SPY "daily" series had 407 rows | Explicit `period1`/`period2` epoch parameters |

Bug 4 is the important one: an understated DSR would have killed the only strategy that passes.

---

## 7. Research consulted

| Source | Used for |
|---|---|
| Faber (2007), *A Quantitative Approach to Tactical Asset Allocation* | The 10-month SMA rule and its drawdown claim |
| Antonacci, *Dual Momentum Investing* | 12-month absolute + relative momentum construction |
| Connors & Alvarez, *Short Term Trading Strategies That Work* | RSI(2), exit thresholds, 200-day regime filter |
| Moskowitz, Ooi & Pedersen (2012), *Time Series Momentum* | Why slow trend can persist across asset classes |
| Bailey & López de Prado (2014), *The Deflated Sharpe Ratio* | Multiple-testing correction at N trials |
| SPIVA (YE2025) | 92.89% of large-cap active funds trailed the S&P 500 over 20 years — cited in `BENCHMARK_GATES.md` |

Internal prior work this builds on: `2026-11-15_1233AM_winning-strategies/buffy/03_benchmark_relative/BENCHMARK_GATES.md`
(the matched-exposure rule and gate list), `02_prediction_markets/WHY_NO_WINNERS.md` (fee curve and the
missing class), `2026-11-15_1227AM_profitability/buffy/02_style_matrix/STYLE_MATRIX.md` (cost ladder).

**On SubQ:** the earlier rounds used SubQ (`api.subq.ai`, `subq-snap-1.2`) for second-opinion
adjudication. It is a language model with **no browsing and no retrieval**, so it cannot fact-check a
primary source — it was used to challenge reasoning, and one disagreement (it ranked FOREX above EQUITY
as next target; I ranked EQUITY first) is kept on the record rather than resolved by appeal to it.

---

## 8. What was NOT researched or measured

- Single-stock equity picks (no point-in-time universe, no survivorship-free data) — see `SPEC_EQUITY.md` §0
- FOREX (no rate differentials, no swap model) — see `SPEC_FOREX.md`
- Prediction markets (no `PREDICTION` class, no settlement data) — see `SPEC_PREDICTION.md`
- Futures/roll yield, credit spreads, options/vol strategies
- Intraday anything
- Taxes and ETF expense ratios (both excluded, and both stated on every result)
- Live repo picks of any class — their excess return has still never been computed

---

## 9. Verification performed

| Check | Result |
|---|---|
| Both result JSONs parse | pass |
| Doc numbers vs JSON spot check (CAGR, excess, Sharpe, MDD, DSR for 7 fields) | match, modulo rounding (−21.77 → −21.8) |
| `tools/forward_tracker.py selftest` | **8/8** verdict-rule cases |
| Markdown tables well-formed (no ragged rows) | pass |
| Cost identity: 33 switches × 6 bps ÷ 22.08y = 0.0897% vs reported −0.09% | confirmed |

Reproduce:

```bash
python3 tools/sim_path_forward.py
python3 tools/sim_path_forward.py --cost-mult 2.0 --out reports/backtest_path_forward_2xcost.json
python3 tools/forward_tracker.py selftest
```

---

## 10. Threats to validity

1. **One sample, one draw.** 22 years is one realisation of a stochastic process; it is not 22 independent tests. This is why the DSR correction matters and why forward testing is still required.
2. **Universe selected with hindsight.** Rules were pre-registered, but SPY/TLT/GLD were chosen in 2026 knowing they are the canonical trio. A survivor-universe bias is plausible and unquantified.
3. **No taxes, no TER.** Stated, not modelled. A monthly-switching rule in a taxable account is materially worse than shown.
4. **Close-to-close execution.** Signals at the close, fills at the close. A one-bar implementation lag would shave a few bps and is not modelled.
5. **Benchmark artefact** (§4): excess for long/flat rules is mechanically ≈ −costs.
6. **The trend overlay's drawdown benefit depends on trends existing.** The sample contains 2008 and 2022; a different 22 years could look worse.
