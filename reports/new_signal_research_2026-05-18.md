# New-Signal Research — Fork 2 — 2026-05-18

_Generated 2026-05-18T02:33:54+00:00 by `tools/new_signal_research.py`._

**Status: OPT-IN RESEARCH SIDECAR. No production wiring.** This module has no caller in `quality_gates.py`, `dashboard_generator.py`, or any pick-generation / scoring path. It reads market data and writes this report — nothing else. Per the repo Wire-Up Rule it is explicitly an opt-in research sidecar.

## Mandate

`reports/EDGE_VERDICT_2026-05-18.md` ruled the existing pick ledger has no durable edge — re-hunting it is exhausted. Fork 2 of the strategic fork is *new signal sources*. This tests the three converged candidates from `reports/PICK_IMPROVEMENT_HARVEST_CLOUD_2026-05-18.md` (5th cloud round, 4 models). Each was pre-registered in `reports/hypothesis_registry.json` (H-006/H-007/H-008) **before** any backtest, per M-107.

## Method (identical leakage controls for all three)

1. Compute the signal z-score from REAL data using ONLY strictly-past observations (rolling 30-obs window).
2. Entry is the first price bar STRICTLY AFTER the signal date — no look-ahead. Forward return measured over a fixed hold.
3. Each signal event becomes a synthetic resolved pick (status=WON/LOST from the direction-signed forward return).
4. Purged + embargoed walk-forward (5-day embargo, 14-day blocks).
5. **Verdict gate:** records fed through `tools/edge_stability_harness.evaluate()` — the SAME admissibility gate the EDGE_VERDICT names. ADMISSIBLE iff |eff| >= 0.3, same sign, >= 3 of the scored 14-day windows.

**A gaudy in-sample win rate is NOT a pass.** Only the harness verdict counts. The base rate after three straight kills (method_a_score, risk_reward, COT z-score) is poor.

## H-006 — CRYPTO — [REJECTED]

- **Signal:** perpetual funding-rate z-score (contrarian) x forward perp return
- **Data source:** Binance fapi mirrors -> Bybit v5 -> OKX (failover chain)
- **Sample size:** 58 signal events

| instrument | events |
|---|---|
| BTCUSDT | 14 |
| ETHUSDT | 16 |
| SOLUSDT | 8 |
| BNBUSDT | 15 |
| XRPUSDT | 5 |

### Purged + embargoed walk-forward
- too few signal events (58) for the harness (needs >= 80/window)

### Harness verdict (THE gate)
- **REJECTED** — INSUFFICIENT DATA — 58 events, harness needs >= 80 per 14d window

## H-007 — COMMODITY — [REJECTED]

- **Signal:** front-to-second roll-yield z-score (futures-continuous vs roll-ETF spread proxy) x forward futures return
- **Data source:** yfinance continuous-front (=F) + roll-tracking ETF (USO/GLD/SLV/CPER/UNG/CORN/WEAT/SOYB) — TERM-STRUCTURE PROXY
- **Sample size:** 2964 signal events
- **Data caveat:** yfinance does not freely expose a true second-month series; the roll yield is approximated by the continuous-front-vs-roll-ETF log spread. This is a documented PROXY, not the CME calendar spread.

| instrument | events |
|---|---|
| CL=F | 394 |
| GC=F | 299 |
| SI=F | 337 |
| HG=F | 358 |
| NG=F | 323 |
| ZC=F | 420 |
| ZW=F | 414 |
| ZS=F | 419 |

### Purged + embargoed walk-forward
- OOS sample: n=2964, pooled WR=49.0%
- embargo: 5 days

| block start | n | WR |
|---|---|---|
| 2021-07-08 | 24 | 41.7% |
| 2021-07-22 | 17 | 52.9% |
| 2021-08-05 | 23 | 39.1% |
| 2021-08-19 | 19 | 47.4% |
| 2021-09-02 | 22 | 63.6% |
| 2021-09-16 | 31 | 64.5% |
| 2021-09-30 | 20 | 40.0% |
| 2021-10-14 | 19 | 36.8% |
| 2021-10-28 | 22 | 36.4% |
| 2021-11-11 | 31 | 64.5% |
| 2021-11-25 | 25 | 52.0% |
| 2021-12-09 | 24 | 58.3% |
| 2021-12-23 | 26 | 57.7% |
| 2022-01-06 | 19 | 42.1% |
| 2022-01-20 | 36 | 44.4% |
| 2022-02-03 | 31 | 41.9% |
| 2022-02-17 | 38 | 52.6% |
| 2022-03-03 | 33 | 36.4% |
| 2022-03-17 | 18 | 50.0% |
| 2022-03-31 | 20 | 25.0% |
| 2022-04-14 | 22 | 31.8% |
| 2022-04-28 | 22 | 59.1% |
| 2022-05-12 | 29 | 58.6% |
| 2022-05-26 | 21 | 61.9% |
| 2022-06-09 | 20 | 60.0% |
| 2022-06-23 | 31 | 38.7% |
| 2022-07-07 | 41 | 41.5% |
| 2022-07-21 | 30 | 60.0% |
| 2022-08-04 | 22 | 40.9% |
| 2022-08-18 | 16 | 31.2% |
| 2022-09-01 | 17 | 52.9% |
| 2022-09-15 | 35 | 57.1% |
| 2022-09-29 | 26 | 42.3% |
| 2022-10-13 | 32 | 43.8% |
| 2022-10-27 | 20 | 55.0% |
| 2022-11-10 | 27 | 37.0% |
| 2022-11-24 | 18 | 44.4% |
| 2022-12-08 | 25 | 80.0% |
| 2022-12-22 | 8 | 75.0% |
| 2023-01-05 | 14 | 28.6% |
| 2023-01-19 | 18 | 33.3% |
| 2023-02-02 | 27 | 40.7% |
| 2023-02-16 | 27 | 63.0% |
| 2023-03-02 | 16 | 37.5% |
| 2023-03-16 | 36 | 55.6% |
| 2023-03-30 | 25 | 52.0% |
| 2023-04-13 | 13 | 30.8% |
| 2023-04-27 | 22 | 27.3% |
| 2023-05-11 | 28 | 39.3% |
| 2023-05-25 | 33 | 63.6% |
| 2023-06-08 | 18 | 55.6% |
| 2023-06-22 | 24 | 58.3% |
| 2023-07-06 | 27 | 40.7% |
| 2023-07-20 | 23 | 56.5% |
| 2023-08-03 | 22 | 59.1% |
| 2023-08-17 | 21 | 52.4% |
| 2023-08-31 | 22 | 68.2% |
| 2023-09-14 | 25 | 56.0% |
| 2023-09-28 | 20 | 65.0% |
| 2023-10-12 | 22 | 54.5% |
| 2023-10-26 | 29 | 41.4% |
| 2023-11-09 | 24 | 62.5% |
| 2023-11-23 | 24 | 37.5% |
| 2023-12-07 | 25 | 60.0% |
| 2023-12-21 | 21 | 33.3% |
| 2024-01-04 | 13 | 61.5% |
| 2024-01-18 | 10 | 40.0% |
| 2024-02-01 | 18 | 61.1% |
| 2024-02-15 | 23 | 30.4% |
| 2024-02-29 | 29 | 44.8% |
| 2024-03-14 | 27 | 37.0% |
| 2024-03-28 | 19 | 68.4% |
| 2024-04-11 | 19 | 47.4% |
| 2024-04-25 | 30 | 56.7% |
| 2024-05-09 | 37 | 59.5% |
| 2024-05-23 | 18 | 77.8% |
| 2024-06-06 | 14 | 92.9% |
| 2024-06-20 | 30 | 36.7% |
| 2024-07-04 | 18 | 33.3% |
| 2024-07-18 | 35 | 54.3% |
| 2024-08-01 | 25 | 68.0% |
| 2024-08-15 | 21 | 23.8% |
| 2024-08-29 | 20 | 65.0% |
| 2024-09-12 | 26 | 80.8% |
| 2024-09-26 | 24 | 45.8% |
| 2024-10-10 | 11 | 54.5% |
| 2024-10-24 | 19 | 31.6% |
| 2024-11-07 | 26 | 26.9% |
| 2024-11-21 | 20 | 50.0% |
| 2024-12-05 | 36 | 44.4% |
| 2024-12-19 | 30 | 63.3% |
| 2025-01-02 | 16 | 43.8% |
| 2025-01-16 | 20 | 45.0% |
| 2025-01-30 | 26 | 19.2% |
| 2025-02-13 | 11 | 81.8% |
| 2025-02-27 | 25 | 48.0% |
| 2025-03-13 | 34 | 41.2% |
| 2025-03-27 | 25 | 16.0% |
| 2025-04-10 | 35 | 51.4% |
| 2025-04-24 | 23 | 73.9% |
| 2025-05-08 | 11 | 27.3% |
| 2025-05-22 | 17 | 29.4% |
| 2025-06-05 | 24 | 62.5% |
| 2025-06-19 | 32 | 31.2% |
| 2025-07-03 | 23 | 52.2% |
| 2025-07-17 | 14 | 78.6% |
| 2025-07-31 | 20 | 75.0% |
| 2025-08-14 | 11 | 63.6% |
| 2025-08-28 | 24 | 50.0% |
| 2025-09-11 | 35 | 28.6% |
| 2025-09-25 | 26 | 34.6% |
| 2025-10-09 | 20 | 35.0% |
| 2025-10-23 | 32 | 43.8% |
| 2025-11-06 | 20 | 45.0% |
| 2025-11-20 | 19 | 42.1% |
| 2025-12-04 | 23 | 39.1% |
| 2025-12-18 | 29 | 48.3% |
| 2026-01-01 | 22 | 59.1% |
| 2026-01-15 | 31 | 48.4% |
| 2026-01-29 | 33 | 57.6% |
| 2026-02-12 | 16 | 56.2% |
| 2026-02-26 | 17 | 47.1% |
| 2026-03-12 | 30 | 40.0% |
| 2026-03-26 | 16 | 31.2% |
| 2026-04-09 | 12 | 50.0% |
| 2026-04-23 | 24 | 54.2% |
| 2026-05-07 | 4 | 100.0% |

### Harness verdict (THE gate)
- per-window eff (new->old): ``
- windows strong: 0/0  (+0/-0)
- **classification: UNTESTED (insufficient density)** — the harness needs >= 80 resolved events AND >= 15 winners + >= 15 losers per 14-day window; the freely-available data is too thin per window to render an eff verdict. This is *not* a clean noise-reject — it is a data-coverage limit. It still does NOT pass.
- **REJECTED** — REJECTED — only 0/0 windows reach eff>=0.3

_Supplementary check — 60-day windows (secondary view for a sparse signal; the 14-day verdict above remains authoritative per EDGE_VERDICT):_
- per-window eff: `+0.41 +0.33 -0.01 -0.16 +0.12 -0.16 -0.25 -0.22 -0.16 +0.20 -0.62 +0.37 +0.39 -0.50 +0.16 +0.01 -0.17 +0.15 -0.07 +0.13 -0.07 -0.06 +0.07 -0.11 -0.22 +0.20 -0.20`  (scored 27, strong 6)
- supplementary verdict: REJECTED — REJECTED — strong in 6 windows but signs split (4+/2-); needs 3 same-sign

## H-008 — BOND — [REJECTED]

- **Signal:** 2s10s yield-curve-slope momentum z-score x forward Treasury-future return
- **Data source:** FRED DGS2/DGS10 (yield) + yfinance ZN/ZB (price)
- **Sample size:** 2358 signal events

| instrument | events |
|---|---|
| ZN=F | 1179 |
| ZB=F | 1179 |

### Purged + embargoed walk-forward
- OOS sample: n=2358, pooled WR=50.6%
- embargo: 5 days

| block start | n | WR |
|---|---|---|
| 2021-05-17 | 1284 | 47.7% |
| 2021-05-31 | 8 | 25.0% |
| 2021-06-14 | 16 | 43.8% |
| 2021-06-28 | 4 | 50.0% |
| 2021-07-12 | 8 | 50.0% |
| 2021-07-26 | 10 | 100.0% |
| 2021-08-09 | 12 | 25.0% |
| 2021-08-23 | 8 | 62.5% |
| 2021-09-06 | 8 | 50.0% |
| 2021-09-20 | 14 | 42.9% |
| 2021-10-04 | 12 | 75.0% |
| 2021-10-18 | 14 | 71.4% |
| 2021-11-01 | 12 | 0.0% |
| 2021-11-15 | 2 | 0.0% |
| 2021-11-29 | 16 | 18.8% |
| 2021-12-13 | 10 | 80.0% |
| 2021-12-27 | 14 | 78.6% |
| 2022-01-10 | 6 | 100.0% |
| 2022-01-24 | 14 | 0.0% |
| 2022-02-07 | 8 | 75.0% |
| 2022-02-21 | 8 | 100.0% |
| 2022-03-07 | 6 | 33.3% |
| 2022-03-21 | 14 | 50.0% |
| 2022-04-04 | 12 | 66.7% |
| 2022-04-18 | 8 | 87.5% |
| 2022-05-02 | 4 | 0.0% |
| 2022-05-16 | 6 | 0.0% |
| 2022-05-30 | 2 | 100.0% |
| 2022-06-13 | 12 | 100.0% |
| 2022-06-27 | 2 | 0.0% |
| 2022-07-11 | 10 | 100.0% |
| 2022-07-25 | 6 | 100.0% |
| 2022-08-08 | 10 | 40.0% |
| 2022-08-22 | 18 | 100.0% |
| 2022-09-05 | 2 | 100.0% |
| 2022-09-19 | 12 | 8.3% |
| 2022-10-17 | 6 | 50.0% |
| 2022-10-31 | 14 | 85.7% |
| 2022-11-14 | 8 | 100.0% |
| 2022-11-28 | 4 | 100.0% |
| 2022-12-12 | 18 | 66.7% |
| 2022-12-26 | 12 | 16.7% |
| 2023-01-09 | 6 | 16.7% |
| 2023-02-06 | 2 | 0.0% |
| 2023-02-20 | 6 | 66.7% |
| 2023-03-06 | 18 | 72.2% |
| 2023-03-20 | 12 | 8.3% |
| 2023-04-03 | 4 | 0.0% |
| 2023-05-01 | 4 | 100.0% |
| 2023-05-15 | 6 | 83.3% |
| 2023-05-29 | 18 | 44.4% |
| 2023-06-26 | 4 | 0.0% |
| 2023-07-10 | 16 | 68.8% |
| 2023-07-24 | 4 | 100.0% |
| 2023-08-07 | 8 | 100.0% |
| 2023-08-21 | 6 | 0.0% |
| 2023-09-18 | 14 | 50.0% |
| 2023-10-02 | 12 | 100.0% |
| 2023-10-16 | 2 | 0.0% |
| 2023-10-30 | 12 | 100.0% |
| 2023-11-13 | 12 | 100.0% |
| 2023-12-25 | 12 | 100.0% |
| 2024-01-08 | 14 | 50.0% |
| 2024-01-22 | 16 | 31.2% |
| 2024-02-05 | 14 | 14.3% |
| 2024-03-04 | 6 | 66.7% |
| 2024-03-18 | 16 | 93.8% |
| 2024-04-01 | 8 | 50.0% |
| 2024-04-15 | 8 | 25.0% |
| 2024-04-29 | 10 | 80.0% |
| 2024-05-13 | 8 | 62.5% |
| 2024-05-27 | 2 | 100.0% |
| 2024-06-10 | 6 | 0.0% |
| 2024-06-24 | 12 | 0.0% |
| 2024-07-08 | 10 | 30.0% |
| 2024-07-22 | 6 | 0.0% |
| 2024-08-05 | 6 | 66.7% |
| 2024-08-19 | 12 | 75.0% |
| 2024-09-02 | 10 | 40.0% |
| 2024-09-16 | 8 | 100.0% |
| 2024-09-30 | 12 | 0.0% |
| 2024-10-14 | 4 | 0.0% |
| 2024-10-28 | 2 | 100.0% |
| 2024-11-11 | 2 | 100.0% |
| 2024-11-25 | 8 | 0.0% |
| 2024-12-09 | 14 | 100.0% |
| 2024-12-23 | 16 | 100.0% |
| 2025-01-06 | 2 | 0.0% |
| 2025-01-20 | 18 | 77.8% |
| 2025-02-03 | 18 | 77.8% |
| 2025-02-17 | 4 | 75.0% |
| 2025-03-03 | 16 | 62.5% |
| 2025-03-17 | 2 | 100.0% |
| 2025-03-31 | 10 | 60.0% |
| 2025-04-14 | 14 | 7.1% |
| 2025-04-28 | 12 | 0.0% |
| 2025-05-12 | 8 | 75.0% |
| 2025-05-26 | 2 | 100.0% |
| 2025-06-23 | 14 | 100.0% |
| 2025-07-07 | 6 | 33.3% |
| 2025-07-21 | 10 | 60.0% |
| 2025-08-04 | 6 | 16.7% |
| 2025-08-18 | 2 | 0.0% |
| 2025-09-01 | 4 | 0.0% |
| 2025-09-15 | 10 | 0.0% |
| 2025-10-27 | 6 | 16.7% |
| 2025-11-10 | 4 | 50.0% |
| 2025-11-24 | 10 | 90.0% |
| 2025-12-08 | 14 | 64.3% |
| 2025-12-22 | 10 | 40.0% |
| 2026-01-05 | 14 | 7.1% |
| 2026-01-19 | 6 | 83.3% |
| 2026-02-02 | 10 | 10.0% |
| 2026-02-16 | 16 | 0.0% |
| 2026-03-30 | 18 | 16.7% |
| 2026-04-13 | 6 | 100.0% |
| 2026-04-27 | 4 | 100.0% |

### Harness verdict (THE gate)
- per-window eff (new->old): `-0.13`
- windows strong: 0/1  (+0/-0)
- **classification: UNTESTED (too few scored windows)** — only 1 window(s) had enough events to score; the harness needs >= 3. Not a pass.
- **REJECTED** — REJECTED — only 0/1 windows reach eff>=0.3

_Supplementary check — 90-day windows (secondary view for a sparse signal; the 14-day verdict above remains authoritative per EDGE_VERDICT):_
- per-window eff: `-0.13`  (scored 1, strong 0)
- supplementary verdict: REJECTED — REJECTED — only 0/1 windows reach eff>=0.3

## Honest conclusion

**0 of 3 candidate signals cleared `edge_stability_harness`.** None may rank or gate picks. But the honest breakdown matters — and it is *not* the same as the three prior clean kills:

- **Cleanly tested and REJECTED (0):** none. The harness rendered an eff-stability verdict and the signal failed it — a real result.
- **UNTESTED — insufficient data density (3):** H-006 CRYPTO, H-007 COMMODITY, H-008 BOND. The harness needs >= 80 resolved events with >= 15 winners and >= 15 losers per 14-day window. Free data (Binance funding history capped at ~1000 rows; yfinance daily bars) does not yield enough signal events per window for these. This is honestly an *untested* verdict, not a pass and not a clean fail — testing them properly needs a longer/denser history (paid funding-rate archives, true CME calendar spreads).

Either way the outcome is the same operationally: **no signal here is admissible, none is wired, none is sized.** The economic priors (funding crowding tax, term-structure carry, slope momentum) are sound and 4 cloud models converged on them — but a sound prior is not an edge until the harness says so, and today it does not.

This is consistent with the EDGE_VERDICT base rate: rigorous leakage-controlled testing keeps returning 'no admissible edge'. Per the EDGE_VERDICT standing rule, the honest default (Fork 3 — paper-only) remains in force. The genuine next step for Fork 2 is not more free-data backtests — it is acquiring the denser data these three signals need to be tested at all.
