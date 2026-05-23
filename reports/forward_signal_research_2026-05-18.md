# Forward-Signal Research — H-002 / H-003 / H-004 — 2026-05-18

_Generated 2026-05-18T06:49:49+00:00 by `tools/forward_signal_research.py`._

**Status: OPT-IN RESEARCH SIDECAR. No production wiring.** This module has no caller in `quality_gates.py`, `dashboard_generator.py`, `production_scanner.py`, or any pick-generation / scoring / gating path. It reads free market data and writes this report — nothing else. Per the repo Wire-Up Rule it is explicitly an opt-in research sidecar.

## Mandate

Three hypotheses were pre-registered in `reports/hypothesis_registry.json` (H-002 / H-003 / H-004, status `PENDING_IMPLEMENTATION`, M-107 gate) **before** any backtest. This module implements them through the same leakage-controlled pattern proven on H-006/H-007/H-008 and feeds the synthetic resolved-pick records to `tools/edge_stability_harness.evaluate()` — the SAME admissibility gate `reports/EDGE_VERDICT_2026-05-18.md` names as the only gate that counts.

## Method (identical leakage controls for all three)

1. Compute the signal from REAL data using ONLY strictly-past observations (rolling 30-obs window for time-series z; cross-sectional rank for H-003 uses inputs all dated <= rebalance).
2. Entry is the first price bar STRICTLY AFTER the signal date — no look-ahead. Forward return measured FORWARD only over a fixed hold.
3. Each signal event becomes a synthetic resolved pick (status=WON/LOST from the direction-signed forward return); the score field `signal_z` carries the conviction magnitude.
4. Purged + embargoed walk-forward (5-day embargo, 14-day blocks).
5. **Verdict gate:** records fed through `edge_stability_harness.evaluate()`. ADMISSIBLE iff |eff| >= 0.3, same sign, >= 3 of the scored 14-day windows (MIN_WINDOW_N=80).

**A gaudy in-sample win rate is NOT a pass.** Only the harness verdict counts. If free data cannot supply enough density the honest verdict is **UNTESTED** — explicitly NOT a pass.

## H-002 — EQUITY — [UNTESTED]

- **Signal:** SUE (standardized unexpected earnings) post-earnings drift z-score — long positive-SUE / short negative-SUE, 30-trading-day drift hold, entry strictly after the announcement date
- **Data source:** yfinance get_earnings_dates (reported vs estimate EPS) + yfinance daily auto-adjusted close — ~45 liquid US large-caps, ex-microcap by construction
- **Sample size:** 1964 signal events
- **Tickers with usable coverage:** 45
- **Data caveat:** SUE is a PROXY: yfinance get_earnings_dates supplies the reported-vs-estimate EPS pair; SUE is standardized by the std of each firm's own strictly-prior surprises (>=4 required). yfinance earnings-date coverage is shallower than a paid Compustat/AlphaVantage feed; if density is below the harness floor the verdict is UNTESTED, not a pass.

| instrument | events / status |
|---|---|
| AAPL | 44 |
| MSFT | 44 |
| AMZN | 42 |
| GOOGL | 44 |
| META | 44 |
| NVDA | 36 |
| TSLA | 39 |
| JPM | 44 |
| V | 44 |
| MA | 44 |
| UNH | 44 |
| HD | 45 |
| PG | 44 |
| JNJ | 44 |
| XOM | 44 |
| CVX | 44 |
| KO | 44 |
| PEP | 44 |
| WMT | 45 |
| COST | 45 |
| BAC | 44 |
| DIS | 44 |
| ADBE | 45 |
| CRM | 45 |
| NFLX | 40 |
| INTC | 43 |
| AMD | 41 |
| QCOM | 44 |
| TXN | 44 |
| ORCL | 45 |
| CSCO | 44 |
| MCD | 44 |
| NKE | 45 |
| ABBV | 44 |
| MRK | 44 |
| PFE | 44 |
| T | 44 |
| VZ | 44 |
| CAT | 44 |
| BA | 44 |
| GE | 44 |
| IBM | 44 |
| GS | 44 |
| MS | 44 |
| C | 44 |

### Purged + embargoed walk-forward
- OOS sample: n=1964, pooled WR=53.2%
- embargo: 5 days

| block start | n | WR |
|---|---|---|
| 2016-05-16 | 216 | 50.9% |
| 2016-06-13 | 2 | 0.0% |
| 2016-06-27 | 2 | 50.0% |
| 2016-07-11 | 14 | 85.7% |
| 2016-07-25 | 19 | 47.4% |
| 2016-08-08 | 4 | 75.0% |
| 2016-08-22 | 1 | 0.0% |
| 2016-09-05 | 1 | 100.0% |
| 2016-09-19 | 4 | 25.0% |
| 2016-10-17 | 25 | 64.0% |
| 2016-10-31 | 8 | 12.5% |
| 2016-11-14 | 4 | 25.0% |
| 2016-11-28 | 1 | 0.0% |
| 2016-12-12 | 3 | 66.7% |
| 2017-01-09 | 8 | 62.5% |
| 2017-01-23 | 24 | 41.7% |
| 2017-02-06 | 4 | 0.0% |
| 2017-02-20 | 5 | 40.0% |
| 2017-03-06 | 2 | 50.0% |
| 2017-03-20 | 1 | 100.0% |
| 2017-04-17 | 26 | 46.2% |
| 2017-05-01 | 11 | 63.6% |
| 2017-05-15 | 5 | 20.0% |
| 2017-06-12 | 2 | 50.0% |
| 2017-06-26 | 1 | 100.0% |
| 2017-07-10 | 13 | 69.2% |
| 2017-07-24 | 21 | 57.1% |
| 2017-08-07 | 5 | 60.0% |
| 2017-08-21 | 1 | 0.0% |
| 2017-09-04 | 1 | 100.0% |
| 2017-09-18 | 2 | 100.0% |
| 2017-10-02 | 4 | 75.0% |
| 2017-10-16 | 21 | 57.1% |
| 2017-10-30 | 12 | 58.3% |
| 2017-11-13 | 4 | 50.0% |
| 2017-12-11 | 4 | 75.0% |
| 2018-01-08 | 7 | 57.1% |
| 2018-01-22 | 22 | 45.5% |
| 2018-02-05 | 8 | 37.5% |
| 2018-02-19 | 4 | 50.0% |
| ...(+192 more) | | |

### Harness verdict (THE gate)
- per-window eff (new->old): `-0.14`
- windows strong: 0/1  (+0/-0)
- **classification: UNTESTED (too few scored windows)** — only 1 window(s) had enough events to score; the harness needs >= 3. Not a pass.
- **UNTESTED** — REJECTED — only 0/1 windows reach eff>=0.3

_Supplementary check — 90-day windows (secondary view for a sparse signal; the 14-day verdict above remains authoritative per EDGE_VERDICT):_
- per-window eff: `-0.14`  (scored 1, strong 0, +0/-0)
- supplementary verdict: REJECTED — REJECTED — only 0/1 windows reach eff>=0.3

## H-003 — ETF — [REJECTED]

- **Signal:** 12-1 cross-sectional momentum z-score on liquid US sector ETFs (long top third / short bottom third, skip last month) — daily mark-to-market continuous-position book x a {5,10,21}-day holding ladder x forward return
- **Data source:** yfinance daily auto-adjusted close — 11 SPDR sector ETFs (XLK/XLF/XLE/XLV/XLI/XLY/XLP/XLU/XLB/XLRE/XLC)
- **Sample size:** 30864 signal events
- **Feasibility:** FULLY FEASIBLE on free data — yfinance covers the full sector-ETF universe. Modelled as a continuous-position book (the research_bond_continuous pattern) so density clears the harness MIN_WINDOW_N floor and a real verdict is rendered. Same hypothesis + leakage controls; the monthly-rebalance design only differs in cadence.

| instrument | events / status |
|---|---|
| XLK | 3116 |
| XLF | 3050 |
| XLE | 3944 |
| XLV | 2108 |
| XLI | 1892 |
| XLY | 2322 |
| XLP | 2732 |
| XLU | 3462 |
| XLB | 1791 |
| XLRE | 2778 |
| XLC | 3669 |

### Purged + embargoed walk-forward
- OOS sample: n=30864, pooled WR=50.7%
- embargo: 5 days

| block start | n | WR |
|---|---|---|
| 2019-06-21 | 162 | 55.6% |
| 2019-07-05 | 180 | 48.3% |
| 2019-07-19 | 180 | 78.9% |
| 2019-08-02 | 180 | 71.1% |
| 2019-08-16 | 180 | 55.6% |
| 2019-08-30 | 162 | 45.1% |
| 2019-09-13 | 180 | 78.9% |
| 2019-09-27 | 180 | 31.7% |
| 2019-10-11 | 180 | 25.0% |
| 2019-10-25 | 180 | 36.1% |
| 2019-11-08 | 180 | 47.2% |
| 2019-11-22 | 162 | 42.6% |
| 2019-12-06 | 180 | 50.0% |
| 2019-12-20 | 144 | 68.1% |
| 2020-01-03 | 180 | 68.3% |
| 2020-01-17 | 162 | 66.7% |
| 2020-01-31 | 180 | 51.7% |
| 2020-02-14 | 162 | 51.9% |
| 2020-02-28 | 180 | 52.8% |
| 2020-03-13 | 180 | 50.0% |
| 2020-03-27 | 180 | 50.0% |
| 2020-04-10 | 162 | 37.7% |
| 2020-04-24 | 180 | 51.7% |
| 2020-05-08 | 180 | 45.0% |
| 2020-05-22 | 162 | 55.6% |
| 2020-06-05 | 180 | 73.3% |
| 2020-06-19 | 180 | 68.9% |
| 2020-07-03 | 162 | 44.4% |
| 2020-07-17 | 180 | 57.8% |
| 2020-07-31 | 180 | 62.2% |
| 2020-08-14 | 180 | 53.3% |
| 2020-08-28 | 162 | 47.5% |
| 2020-09-11 | 180 | 62.8% |
| 2020-09-25 | 180 | 57.2% |
| 2020-10-09 | 180 | 47.2% |
| 2020-10-23 | 180 | 46.7% |
| 2020-11-06 | 180 | 54.4% |
| 2020-11-20 | 162 | 56.2% |
| 2020-12-04 | 180 | 57.8% |
| 2020-12-18 | 162 | 49.4% |
| ...(+139 more) | | |

### Harness verdict (THE gate)
- per-window eff (new->old): `+0.16 +0.16 -0.60 -0.25 -0.64 -0.49 -0.34 -0.16 +0.32 -0.08 +0.82 -0.23 -0.79 -0.29 -0.76 -0.49 -0.25 -0.23 -0.09 +0.01 -0.10 -0.73 -0.54 -0.46 -0.15 -0.61 -0.12 -0.29 +0.35 -0.26 -0.60 +0.10 -0.16 -0.21 -0.42 -0.08 +0.22 -0.55 -0.58 +0.27 -0.00 +0.05 +0.06 +0.42 +0.76 -0.00 -0.19 +0.34 +0.01 +0.21 +0.29 -0.24 -0.71 +0.05 +0.40 +0.92 +0.53 +0.43 +0.95 +1.14 +1.00 +1.02 +0.37 +0.61 +0.65 -0.20 +0.05 +0.03 -0.17 +0.07 +0.04 -0.04 +0.04 -0.14 +0.01 +0.22 +0.13 -0.29 -0.36 -0.14 -0.09 -0.14 +0.34 +0.41 +0.76 +1.65 +0.37 +0.12 -0.78 -0.45 +0.36 +0.66 +0.53 +0.17 +0.03 +0.13 +0.57 +0.16 +0.28 -0.66 -0.59 +0.29 +0.46 +0.54 +0.29 +0.46 +0.06 +0.32 +0.77 -0.59 +0.04 -0.31 +0.32 -0.20 -0.47 -0.47 -0.10 +0.63 +0.84 +0.99 +0.30 -0.40 -0.23 -0.15 +0.00 +0.28 +0.22 -0.02 -0.10 -0.28 -0.85 -0.89 -0.87 -0.07 -0.86 -0.64 -0.06 +0.01 -0.52 +0.49 -0.56 -0.45 -0.35 +0.18 +0.31 +0.64 +0.32 +0.61 +0.70 +0.16 +0.20 +0.41 +0.56 +0.00 -0.17 -0.38 -0.29 -0.29 -0.08 +0.06 +0.03 +0.04 +0.65 +0.61 +0.32 -0.20 +0.14 +0.33 +0.14 -0.26 +0.22 -0.03 -0.01 -0.07 +0.23 +0.46 +0.59 +0.18`
- windows strong: 85/178  (+49/-36)
- **classification: tested — harness rendered a verdict on the eff stability.**
- **REJECTED** — REJECTED — strong in 85 windows but signs split (49+/36-); needs 3 same-sign

## H-004 — COMMODITY — [UNTESTED]

- **Signal:** EIA weekly inventory-surprise z-score (vs a rolling-mean expected baseline) GATED by front-vs-roll-ETF curve-shape agreement x forward 14-day futures return
- **Data source:** EIA v2 open-data API (api.eia.gov — petroleum/stoc/wstk WCESTUS1 crude / WGTSTUS1 gasoline; natural-gas/stor/wkly NW2_EPG0_SWO_R48_BCF working gas) + yfinance futures-continuous (CL/RB/NG) + roll-ETF (USO/UGA/UNG)
- **Sample size:** 0 signal events
- **DATA GAP (UNTESTED reason):** NO EIA API KEY — api.eia.gov requires a free registered key (returns 403 API_KEY_MISSING without one); no EIA_API_KEY (or any EIA-named var) is in the Windows environment, and FRED does NOT redistribute the EIA weekly inventory STOCKS series (only EIA prices / monthly NBER-era data). H-004 is therefore UNTESTED for a data-access reason — not an edge reason. To test it, register a free key at eia.gov/opendata/register.php and set EIA_API_KEY; the module will then run end-to-end.
- **Data caveat:** TWO STACKED PROXIES even with an EIA key: (1) no FREE consensus / expected-inventory series exists, so the 'expected' baseline is a DOCUMENTED PROXY — the rolling mean of the weekly inventory CHANGE, with the surprise = deviation of the latest change from that baseline; a real Bloomberg/Reuters analyst consensus would behave differently. (2) The roll-yield curve shape is the futures-continuous-vs-roll-ETF log-spread PROXY documented for H-007 — not a true CME calendar spread. Read the verdict accordingly.

| instrument | events / status |
|---|---|
| crude oil — EIA weekly crude stocks ex-SPR | no EIA_API_KEY in environment — api.eia.gov returns 403 API_KEY_MISSING; weekly inventory stocks unavailable on free keyless sources |
| gasoline — EIA weekly total motor gasoline stocks | no EIA_API_KEY in environment — api.eia.gov returns 403 API_KEY_MISSING; weekly inventory stocks unavailable on free keyless sources |
| natural gas — EIA weekly Lower-48 working gas in storage | no EIA_API_KEY in environment — api.eia.gov returns 403 API_KEY_MISSING; weekly inventory stocks unavailable on free keyless sources |

### Purged + embargoed walk-forward
- too few signal events (0) for the harness (needs >= 80/window)

### Harness verdict (THE gate)
- **UNTESTED** — INSUFFICIENT DATA — 0 events, harness needs >= 80 per 14d window

## Honest conclusion

- **ADMISSIBLE (0):** none
- **REJECTED — tested, harness fail (1):** H-003 ETF
- **UNTESTED — data too thin to render a verdict (2):** H-002 EQUITY, H-004 COMMODITY

**0 of 3 candidate signals cleared `edge_stability_harness`.** None may rank or gate picks. None is wired. None is sized. The economic priors (post-earnings drift, cross-sectional momentum, storage-model inventory carry) are academically sound — but a sound prior is not an edge until the harness says so, and today it does not. This is consistent with the EDGE_VERDICT base rate. The paper-only posture (Fork 3) stands.
