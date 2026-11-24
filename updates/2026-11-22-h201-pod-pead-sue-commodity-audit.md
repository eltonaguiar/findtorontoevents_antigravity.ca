# H-201 forward pod, a real PEAD-SUE attempt, and why COMMODITY is unmeasurable

## 1. H-201 is now a live forward pod (the first one with a benchmark leg)

`tools/forward_book.py` could only price Binance symbols, so it refused every
equity entry — a pod that cannot price its own instrument is not a forward test.
Added `equity_bars()` + `bars_for()` to `tools/ohlc_bars.py`, then registered the
pre-registered H-201 spec as a rule:

| field | value | why |
|---|---|---|
| rule | `xsmom_equity_top3_6m` | same mechanism that passed the backtest gates |
| universe | the frozen 10-name list | changing it would be a different experiment |
| lookback / top_k | 126 sessions / 3 | frozen at registration |
| TP / SL | **none** | the registered backtest had no levels; adding them forward tests a different strategy |
| max hold | 21 sessions | time exit, matching the monthly rebalance |
| benchmark | SPY | so a beta result cannot be mistaken for alpha |
| cost | 10 bps | as registered |

Entries carry `pod`, `spec_ref`, `benchmark`, and `registered_at`; resolution now
records `benchmark_pct` and `excess_pct`, and `publish` emits `by_pod` stats with
mean benchmark and mean excess. First emission (2026-11-22): **AAPL, MSFT, JNJ**
(3 entries, SPY leg, no TP/SL). Ranked by 126-session return at emission time.

`--emit-pod h201` is idempotent and safe to run daily; it only adds entries whose
id (symbol|rule|entry_date) does not already exist.

## 2. PEAD on 12-quarter SUE: implemented, and it does not work on this data

The literature result being tested: Kaczmarek & Zaremba (2025) revive PEAD by
using multi-quarter standardized unexpected earnings instead of the latest
surprise. Implemented as registered (H-222): each surprise z-scored against all
**prior** surprises (≥8 quarters, no lookahead), enter next open when SUE ≥ 1.0,
hold 20 sessions, 10 bps.

**Result: 13 events, and the z-score is broken by a regime artifact** — not by
PEAD being absent. yfinance's history starts in 2021, where COVID-recovery prints
were 18 %, 42 % and 28 %. Those set a mean of **14.0 %** and sd of **14.8 %**, so
a normal 6 % beat scores **−0.4**; AAPL would need a ≥28.8 % surprise to fire
again, and never does. Hence 0 events for AAPL and JPM, 1–3 for the rest.

Labelled `INSUFFICIENT_N` (13 events), **not** refuted. The honest fixes are:
a longer surprise history (SEC XBRL, 40+ quarters), or cross-sectional scoring
within each quarter, both of which need a data source we do not have keyless.
Recorded as a data limitation, not a verdict on the anomaly.

## 3. COMMODITY: `DATA_INTEGRITY_FAIL`, not "weak"

The 0.165 profit factor is explained. The series are contaminated:

- **ZC=F**: −23.6 %, −17.4 %, −16.8 %, −13.1 % on **July 15/17 of four different
  years** — contract roll, not market.
- **CL=F**: one **negative close** (−37.63 on 2020-04-20), which makes
  `pct_change` mathematically meaningless (−306 %), plus 55 moves over 8 %.
- **NG=F**: 150 moves over 8 %, with spikes recurring on the same month-day across
  up to six years (01-30 in 2014, 2018, 2023, 2024, 2025, 2026).

Winsorising at ±5 % moves CL's mean from −0.89 bps/day to +0.27 and ZC's from
−1.77 to −0.61, i.e. the sign of the result is an artifact of the roll gaps.
`commodity_integrity()` now detects negative prices and recurring month-day
spikes; COMMODITY cells report `DATA_INTEGRITY_FAIL` until rebuilt on
roll-adjusted contracts. GC=F, SI=F and HG=F pass the check.

## Verification

- `pytest tests/test_forward_book_h201_pod.py tests/test_per_class_edge_harness.py`
  → **11 passed** (frozen spec, no TP/SL, time exit, benchmark excess identity,
  pod publish stats; exposure ≤ 1, dropped-name closure, lookahead independence).
- Harness re-run: **34 cells**, PBO 0.09, n_trials 23; H-222 `INSUFFICIENT_N`;
  COMMODITY cells `DATA_INTEGRITY_FAIL`; only H-201 still clears every gate.
- Forward book: 8 entries, 3 in pod H-201, all OPEN (no bar after entry yet).
