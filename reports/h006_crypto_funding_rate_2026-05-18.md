# H-006 — CRYPTO Perpetual Funding-Rate — Deeper Archive — 2026-05-18

_Generated 2026-05-18T03:16:20+00:00 by `tools/h006_funding_research.py`._

**Status: OPT-IN RESEARCH SIDECAR. No production wiring.** No caller in `quality_gates.py`, `dashboard_generator.py`, or any pick-generation / scoring path. Reads market data, writes this report. Per the repo Wire-Up Rule it is explicitly an opt-in research sidecar.

## P2 mandate

`reports/PATH_TO_PROVEN_EDGE_2026-05-18.md` item P2: H-006 was UNTESTED in Fork 2 because `tools/new_signal_research.py` fetched funding history with a single `limit=1000` call. Binance `/fapi/v1/fundingRate` caps **1000 rows per request**, not in total — the endpoint accepts `startTime`/`endTime`. This module **paginates the full multi-year history** per symbol, adds a mark-vs-index basis confirming gate, and re-runs H-006 through the SAME `edge_stability_harness` admissibility gate the EDGE_VERDICT names.

## Method (identical leakage controls to Fork 2)

1. Funding-rate z-score from REAL data, rolling 30-obs window, strictly-past observations only.
2. Signal fires when |z| >= 1.0. Contrarian: positive funding z (crowded longs) -> SHORT; negative z -> LONG.
3. **Basis confirming gate:** the trade is taken only when the mark-vs-index basis sign agrees with the crowd being faded (crowded long confirmed by basis > 0; crowded short by basis < 0). Missing basis is treated as neutral (gate passes on funding alone).
4. Entry = first daily close STRICTLY AFTER the signal date (no look-ahead). Forward return over a fixed 3-day hold.
5. Each event -> a synthetic resolved pick (status WON/LOST from the direction-signed forward return).
6. Purged + embargoed walk-forward (5-day embargo, 14-day blocks).
7. **Verdict gate:** records fed through `edge_stability_harness.evaluate()` — ADMISSIBLE iff |eff| >= 0.3, same sign, >= 3 of the scored 14-day windows.

**A gaudy in-sample win rate is NOT a pass.** Only the harness verdict counts. Base rate after 5 prior kills is poor — be brutally honest.

## H-006 — CRYPTO — [REJECTED]

- **Signal:** perpetual funding-rate z-score (contrarian) x mark-vs-index basis confirming gate -> forward perp return
- **Data source:** Binance fapi mirrors (PAGINATED full history) -> Bybit v5 paginated -> OKX failover chain; basis from Binance premiumIndexKlines
- **Sample size:** 4838 signal events

| symbol | events | funding days | funding span | basis days |
|---|---|---|---|---|
| BTCUSDT | 521 | 2191 | 2020-05-19 -> 2026-05-18 | 2190 |
| ETHUSDT | 494 | 2191 | 2020-05-19 -> 2026-05-18 | 2190 |
| SOLUSDT | 448 | 2074 | 2020-09-13 -> 2026-05-18 | 2073 |
| BNBUSDT | 520 | 2191 | 2020-05-19 -> 2026-05-18 | 2190 |
| XRPUSDT | 478 | 2191 | 2020-05-19 -> 2026-05-18 | 2190 |
| ADAUSDT | 499 | 2191 | 2020-05-19 -> 2026-05-18 | 2190 |
| AVAXUSDT | 448 | 2065 | 2020-09-22 -> 2026-05-18 | 2064 |
| LINKUSDT | 477 | 2191 | 2020-05-19 -> 2026-05-18 | 2190 |
| DOGEUSDT | 457 | 2139 | 2020-07-10 -> 2026-05-18 | 2139 |
| LTCUSDT | 496 | 2191 | 2020-05-19 -> 2026-05-18 | 2190 |

### Purged + embargoed walk-forward
- OOS sample: n=4838, pooled WR=49.7%
- embargo: 5 days

| block start | n | WR |
|---|---|---|
| 2020-06-19 | 16 | 81.2% |
| 2020-07-03 | 25 | 60.0% |
| 2020-07-17 | 32 | 12.5% |
| 2020-07-31 | 35 | 34.3% |
| 2020-08-14 | 34 | 67.6% |
| 2020-08-28 | 20 | 60.0% |
| 2020-09-11 | 21 | 61.9% |
| 2020-09-25 | 20 | 40.0% |
| 2020-10-09 | 21 | 57.1% |
| 2020-10-23 | 30 | 76.7% |
| 2020-11-06 | 39 | 28.2% |
| 2020-11-20 | 59 | 55.9% |
| 2020-12-04 | 9 | 66.7% |
| 2020-12-18 | 33 | 42.4% |
| 2021-01-01 | 64 | 43.8% |
| 2021-01-15 | 19 | 57.9% |
| 2021-01-29 | 53 | 37.7% |
| 2021-02-12 | 57 | 59.6% |
| 2021-02-26 | 19 | 94.7% |
| 2021-03-12 | 6 | 50.0% |
| 2021-03-26 | 55 | 32.7% |
| 2021-04-09 | 69 | 50.7% |
| 2021-04-23 | 24 | 83.3% |
| 2021-05-07 | 9 | 22.2% |
| 2021-05-21 | 16 | 62.5% |
| 2021-06-04 | 2 | 100.0% |
| 2021-06-18 | 41 | 63.4% |
| 2021-07-02 | 14 | 42.9% |
| 2021-07-16 | 20 | 80.0% |
| 2021-07-30 | 34 | 8.8% |
| 2021-08-13 | 75 | 48.0% |
| 2021-08-27 | 60 | 56.7% |
| 2021-09-10 | 10 | 50.0% |
| 2021-09-24 | 14 | 57.1% |
| 2021-10-08 | 80 | 38.8% |
| 2021-10-22 | 54 | 40.7% |
| 2021-11-05 | 35 | 42.9% |
| 2021-11-19 | 14 | 28.6% |
| 2021-12-03 | 26 | 38.5% |
| 2021-12-17 | 4 | 75.0% |
| 2021-12-31 | 23 | 73.9% |
| 2022-01-14 | 49 | 36.7% |
| 2022-01-28 | 39 | 87.2% |
| 2022-02-11 | 31 | 71.0% |
| 2022-02-25 | 27 | 59.3% |
| 2022-03-11 | 6 | 50.0% |
| 2022-03-25 | 5 | 40.0% |
| 2022-04-08 | 53 | 34.0% |
| 2022-04-22 | 59 | 25.4% |
| 2022-05-06 | 46 | 60.9% |
| 2022-05-20 | 8 | 25.0% |
| 2022-06-03 | 26 | 57.7% |
| 2022-06-17 | 20 | 45.0% |
| 2022-07-01 | 20 | 100.0% |
| 2022-07-15 | 24 | 79.2% |
| 2022-07-29 | 19 | 89.5% |
| 2022-08-12 | 64 | 34.4% |
| 2022-08-26 | 47 | 72.3% |
| 2022-09-09 | 21 | 42.9% |
| 2022-09-23 | 16 | 12.5% |
| 2022-10-07 | 15 | 46.7% |
| 2022-10-21 | 20 | 75.0% |
| 2022-11-04 | 34 | 20.6% |
| 2022-11-18 | 10 | 40.0% |
| 2022-12-02 | 14 | 42.9% |
| 2022-12-16 | 25 | 52.0% |
| 2022-12-30 | 27 | 55.6% |
| 2023-01-13 | 34 | 67.6% |
| 2023-01-27 | 5 | 100.0% |
| 2023-02-10 | 36 | 77.8% |
| 2023-02-24 | 46 | 15.2% |
| 2023-03-10 | 42 | 50.0% |
| 2023-03-24 | 15 | 73.3% |
| 2023-04-07 | 31 | 83.9% |
| 2023-04-21 | 37 | 51.4% |
| 2023-05-05 | 30 | 46.7% |
| 2023-05-19 | 14 | 28.6% |
| 2023-06-02 | 40 | 42.5% |
| 2023-06-16 | 26 | 92.3% |
| 2023-06-30 | 19 | 73.7% |
| 2023-07-14 | 20 | 35.0% |
| 2023-07-28 | 13 | 53.8% |
| 2023-08-11 | 59 | 35.6% |
| 2023-08-25 | 38 | 60.5% |
| 2023-09-08 | 20 | 70.0% |
| 2023-09-22 | 15 | 46.7% |
| 2023-10-06 | 15 | 53.3% |
| 2023-10-20 | 65 | 27.7% |
| 2023-11-03 | 70 | 41.4% |
| 2023-11-17 | 5 | 80.0% |
| 2023-12-01 | 45 | 40.0% |
| 2023-12-15 | 60 | 66.7% |
| 2023-12-29 | 55 | 54.5% |
| 2024-01-12 | 4 | 25.0% |
| 2024-01-26 | 13 | 84.6% |
| 2024-02-09 | 67 | 70.1% |
| 2024-02-23 | 113 | 19.5% |
| 2024-03-08 | 27 | 74.1% |
| 2024-03-22 | 6 | 83.3% |
| 2024-04-05 | 38 | 73.7% |
| 2024-04-19 | 47 | 34.0% |
| 2024-05-03 | 16 | 50.0% |
| 2024-05-17 | 59 | 64.4% |
| 2024-05-31 | 49 | 61.2% |
| 2024-06-14 | 53 | 39.6% |
| 2024-06-28 | 28 | 64.3% |
| 2024-07-12 | 27 | 70.4% |
| 2024-07-26 | 50 | 54.0% |
| 2024-08-09 | 50 | 56.0% |
| 2024-08-23 | 22 | 22.7% |
| 2024-09-06 | 26 | 80.8% |
| 2024-09-20 | 10 | 60.0% |
| 2024-10-04 | 17 | 82.4% |
| 2024-10-18 | 6 | 66.7% |
| 2024-11-01 | 51 | 37.3% |
| 2024-11-15 | 39 | 25.6% |
| 2024-11-29 | 61 | 49.2% |
| 2024-12-13 | 62 | 37.1% |
| 2024-12-27 | 12 | 50.0% |
| 2025-01-10 | 29 | 72.4% |
| 2025-01-24 | 47 | 34.0% |
| 2025-02-07 | 32 | 56.2% |
| 2025-02-21 | 38 | 18.4% |
| 2025-03-07 | 30 | 66.7% |
| 2025-03-21 | 29 | 34.5% |
| 2025-04-04 | 22 | 63.6% |
| 2025-04-18 | 22 | 54.5% |
| 2025-05-02 | 25 | 76.0% |
| 2025-05-16 | 15 | 26.7% |
| 2025-05-30 | 27 | 66.7% |
| 2025-06-13 | 33 | 42.4% |
| 2025-06-27 | 15 | 53.3% |
| 2025-07-11 | 37 | 24.3% |
| 2025-07-25 | 38 | 81.6% |
| 2025-08-08 | 31 | 54.8% |
| 2025-08-22 | 25 | 24.0% |
| 2025-09-05 | 21 | 57.1% |
| 2025-09-19 | 40 | 32.5% |
| 2025-10-03 | 45 | 15.6% |
| 2025-10-17 | 32 | 68.8% |
| 2025-10-31 | 18 | 55.6% |
| 2025-11-14 | 29 | 44.8% |
| 2025-11-28 | 35 | 48.6% |
| 2025-12-12 | 27 | 48.1% |
| 2025-12-26 | 19 | 52.6% |
| 2026-01-09 | 36 | 36.1% |
| 2026-01-23 | 57 | 21.1% |
| 2026-02-06 | 30 | 33.3% |
| 2026-02-20 | 26 | 69.2% |
| 2026-03-06 | 16 | 87.5% |
| 2026-03-20 | 24 | 37.5% |
| 2026-04-03 | 25 | 68.0% |
| 2026-04-17 | 19 | 73.7% |
| 2026-05-01 | 19 | 63.2% |
| 2026-05-15 | 1 | 0.0% |

### Harness verdict (THE gate)
- per-window eff (new->old): `-0.18 +0.16`
- windows strong: 0/2  (+0/-0)
- **classification: UNTESTED (too few scored windows)** — only 2 window(s) scored; harness needs >= 3. NOT a pass.
- **REJECTED** — REJECTED — only 0/2 windows reach eff>=0.3

_Supplementary check — 30-day windows (secondary view; the 14-day verdict above remains authoritative per EDGE_VERDICT):_
- per-window eff: `-0.38 -0.26 -0.36 +0.59 +0.28 -0.25 -0.68 -0.04 +0.26 +0.34 -0.03 +0.24 +0.47 -0.04 -0.38 +0.01 -0.23 +0.12 -0.27 -0.25 +0.43`  (scored 21, strong 8)
- supplementary verdict: REJECTED — REJECTED — strong in 8 windows but signs split (4+/4-); needs 3 same-sign

## Honest conclusion

**H-006 is now TESTABLE — and it FAILS.** The deeper paginated funding archive is the genuine fix the P2 mandate asked for: Fork 2 had 58 events, this run has 4838 across 10 perps spanning ~6 years (2020-2026). The canonical 14-day harness still scored only 2 window(s) because extreme funding z-scores cluster in regime episodes — most 14-day buckets fall below the harness's 80-pick / 15-winner-15-loser floor. But the supplementary 30-day windowing — a fair eff-stability look at the SAME records — scored 21 windows with 8 strong, and the eff SIGN SPLITS (4+/4-). That is a genuine fail of the eff-stability requirement, not a data-coverage gap — the identical failure mode that killed `method_a_score` and H-007: in-sample separation that flips sign across regimes. Pooled walk-forward WR is 49.7% — a coin-flip. **This is kill #6.** The economic prior (funding is a crowding tax) is sound, but a sound prior is not an edge until the harness says so, and on a properly deep sample it does not.

Honest caveat on the 14-day verdict: strictly by the letter of the EDGE_VERDICT rule (>=3 *14-day* windows), H-006 is UNTESTED — only 2 14-day window(s) scored. A purist would say 'still untested at the canonical resolution.' But the deeper archive removed the *data* excuse: the signal genuinely fires too sparsely and clusters, and where it CAN be scored (30-day windows) it is sign-unstable. Re-running with a lower |z| threshold to force 14-day density would be p-hacking the window count, not finding edge. The defensible read is: H-006 is a fail.

Either way: **H-006 is NOT admissible, NOT wired, NOT sized.** Per the EDGE_VERDICT standing rule the honest default (Fork 3 — paper-only) remains in force for CRYPTO.
