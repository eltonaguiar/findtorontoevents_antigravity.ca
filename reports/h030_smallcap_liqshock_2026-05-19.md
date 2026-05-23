# H-030 EQUITY small-cap liquidity-shock reversion — 2026-05-19

_Generated 2026-05-19T04:35:55+00:00 by `tools/h030_smallcap_liqshock.py`._

**Status: OPT-IN RESEARCH SIDECAR. No production wiring.** No caller in `quality_gates.py`, `dashboard_generator.py`, or any pick / scoring path. Fetches free yfinance data, runs the pre-registered signal through `edge_stability_harness` (imported unmodified), writes this report.

## Pre-registered hypothesis (registry `local_harvest_2026_05_19` / H-030)

Fade a liquidity-shock day in liquid small-cap Russell-2000 names (price > $5). Day D qualifies when its volume is **> 3x the trailing 60-day mean volume** AND it **closes weak** (close in the bottom 25% of D's high-low range). Enter **LONG at the open of D+1**; exit at +3 trading days or +/-1xATR(14), whichever first. Continuous LONG-only multi-asset book over a fixed pre-registered basket, yfinance daily.

**No-look-ahead:** day-D qualification uses only bars strictly before D for the 60-day volume baseline and ATR(14); entry is the D+1 open and the exit scan only reads bars D+1..D+3.

## Data

- yfinance daily OHLCV, free, no key. Cached to `tools/cache/h030_smallcap_cache.json`.
- Fixed basket tickers fetched: 28.
- Continuous-book resolved records (every instrument-day): **71362**.
- Of which qualifying H-030 liquidity-shock signal days: **716**.

| ticker | records | signal days | wins | WR |
|---|---|---|---|---|
| PLUG | 6610 | 29 | 2827 | 42.8% |
| FUBO | 1666 | 37 | 757 | 45.4% |
| RIOT | 2481 | 14 | 1207 | 48.6% |
| MARA | 3310 | 32 | 1464 | 44.2% |
| SOFI | 1286 | 15 | 612 | 47.6% |
| CHPT | 1524 | 16 | 696 | 45.7% |
| RUN | 2649 | 14 | 1335 | 50.4% |
| BBBY | 5968 | 55 | 2890 | 48.4% |
| CLOV | 1427 | 6 | 624 | 43.7% |
| WKHS | 3462 | 76 | 1405 | 40.6% |
| SPCE | 2102 | 27 | 953 | 45.3% |
| GME | 6041 | 27 | 2996 | 49.6% |
| AMC | 3058 | 28 | 1364 | 44.6% |
| BLNK | 3860 | 62 | 1611 | 41.7% |
| FCEL | 8125 | 135 | 3543 | 43.6% |
| OPEN | 1423 | 2 | 661 | 46.5% |
| UPST | 1297 | 7 | 662 | 51.0% |
| AFRM | 1279 | 10 | 632 | 49.4% |
| DKNG | 1631 | 19 | 805 | 49.4% |
| PTON | 1606 | 11 | 771 | 48.0% |
| LCID | 1359 | 16 | 605 | 44.5% |
| RIVN | 1070 | 7 | 513 | 47.9% |
| JOBY | 1323 | 14 | 613 | 46.3% |
| ROOT | 1331 | 14 | 612 | 46.0% |
| DNA | 1214 | 4 | 574 | 47.3% |
| SKLZ | 1460 | 13 | 651 | 44.6% |
| RKLB | 1312 | 10 | 652 | 49.7% |
| ASTS | 1488 | 16 | 702 | 47.2% |

## Harness verdict (THE gate — harness imported UNMODIFIED)

- per-window eff (new->old): `+0.12 -0.11 -0.33 +0.00 +0.00 -0.09 -0.11 +0.00 +0.00 +0.00 -0.10 -0.13 +0.00 +0.00 -0.10 +0.08 -0.17 +0.10 -0.05 -0.11 +0.15 +0.06 -0.23 +0.12 -0.07 -0.12 +0.14 -0.14 -0.12 +0.16 +0.11 +0.00 +0.14 +0.00 -0.12 +0.00 +0.00 +0.14 +0.09 -0.23 -0.11 +0.00 +0.00 +0.00 +0.00 +0.11 +0.00 +0.00 -0.18 -0.19 -0.12 +0.17 -0.09 -0.12 +0.23 +0.00 +0.00 -0.06 +0.00 +0.00 -0.10 +0.00 -0.09 -0.16 +0.00 -0.09 +0.10 -0.05 +0.00 +0.06 -0.08 -0.13 -0.06 -0.10 +0.04 +0.08 +0.20 +0.17 +0.00 -0.12 +0.00 +0.00 +0.15 +0.08 -0.12 +0.12 +0.00 +0.00 -0.09 +0.00 -0.12 +0.18 -0.19 +0.00 +0.00 -0.08 +0.00 +0.16 -0.01 +0.00 +0.00 -0.23 +0.00 +0.00 -0.11 +0.00 +0.00 +0.00 +0.00 +0.00 +0.16 +0.00 +0.23 +0.00 +0.00 -0.08 -0.08 -0.09 -0.20 +0.14 -0.10 -0.13 +0.00 -0.11 -0.07 +0.15 -0.06 +0.03 -0.15 -0.34 +0.05 +0.33 +0.00 +0.16 -0.10 -0.21 +0.29 -0.20 -0.26 -0.20 -0.19 -0.33 +0.28 -0.18 +0.00 -0.12 -0.22 -0.09 +0.00 +0.02 -0.17 -0.15 +0.31 +0.15 +0.03 +0.00 +0.17 -0.08 -0.03 -0.12 +0.20 -0.14 -0.14 +0.12 -0.17 +0.23 -0.28 -0.20 +0.00 +0.30 -0.13 -0.22 +0.00 -0.15 +0.00 +0.00 +0.00 -0.17 +0.05 -0.36 -0.17 -0.14 +0.06 +0.31 +0.00 +0.00 +0.00 -0.14 -0.30 +0.00 +0.00 -0.18 +0.23 -0.05 +0.28 -0.21 +0.00 +0.00 +0.00 +0.00 -0.23 +0.00 -0.21 +0.27 +0.13 -0.04 +0.15 +0.21 +0.24 +0.21 -0.17 +0.00 -0.16 +0.24 +0.00 +0.00 -0.13 -0.17 +0.00 +0.04 -0.23 +0.24 -0.20 +0.02 -0.12 +0.08 +0.16 +0.00 -0.03 +0.23 +0.25 +0.00 +0.00 +0.00 +0.00 +0.27 -0.13 +0.24 -0.21 +0.00 -0.16 +0.21 -0.25 -0.17 +0.00 -0.20 -0.17 -0.25 -0.13 +0.00 +0.00 -0.22 +0.00 -0.23 -0.26 +0.00 +0.00 +0.00 -0.17 +0.00 +0.00 -0.13 -0.20 -0.22 -0.09 +0.00 +0.00 +0.00 +0.00 -0.24 +0.56 -0.17 +0.25 +0.00 +0.25 +0.00 -0.03`
- windows scored: 277  (strong: 10)
- sign: `mixed`  same-sign ok: False
- harness `is_admissible()`: False
- harness reason: REJECTED — strong in 10 windows but signs split (5+/5-); needs 3 same-sign

## Edge & cost survival (over the qualifying H-030 signal days)

- pooled WR: 41.06%
- gross mean per-trade return: -0.011609
- net mean per-trade return (after 30bps): -0.014609
- cost-survival (|gross| > 30bps): 96.0%  (gate >= 60%: PASS)

## VERDICT: **REJECTED**

Clean kill. The small-cap liquidity-shock reversion signal does not separate winners from losers with a stable sign across enough 14-day windows (or fails the 30bps cost gate). Do not wire or size. Archive as a tested failure.
