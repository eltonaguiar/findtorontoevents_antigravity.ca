# H-031 COMMODITY agricultural harvest-seasonality — 2026-05-19

_Generated 2026-05-19T04:37:47+00:00 by `tools/h031_harvest_seasonality.py`._

**Status: OPT-IN RESEARCH SIDECAR. No production wiring.** No caller in `quality_gates.py`, `dashboard_generator.py`, or any pick / scoring path. Fetches free yfinance data, runs the pre-registered signal through `edge_stability_harness` (imported unmodified), writes this report.

## Pre-registered hypothesis (registry `local_harvest_2026_05_19` / H-031)

Calendar-anchored corn (ZC=F) + wheat (ZW=F) harvest-cycle directional windows. The directional sign for each calendar month and the very decision to trade it are derived **only from training years strictly before the fixed cut date**, then applied **unchanged** to the out-of-sample test years — genuinely look-ahead-free.

- train/test cut: **2019-01-01** (training = before; test = on/after).
- a month is traded iff its training-year mean daily return is >= 2.0 bps/day in magnitude.

## Frozen calendar learned from TRAINING years only

- **ZC=F**: Jan LONG (+3.3bps/d, n=357), Feb LONG (+14.8bps/d, n=343), Mar LONG (+4.7bps/d, n=391), Apr LONG (+3.4bps/d, n=372), May LONG (+6.2bps/d, n=382), Jun SHORT (-13.8bps/d, n=384), Jul SHORT (-13.8bps/d, n=391), Aug LONG (+2.4bps/d, n=423), Sep SHORT (-2.1bps/d, n=382), Oct LONG (+14.2bps/d, n=414), Nov SHORT (-5.0bps/d, n=387), Dec LONG (+25.6bps/d, n=383)
- **ZW=F**: Jan SHORT (-9.7bps/d, n=365), Feb LONG (+6.0bps/d, n=343), Mar SHORT (-8.1bps/d, n=386), Apr LONG (+6.6bps/d, n=372), May LONG (+12.1bps/d, n=380), Jun SHORT (-6.6bps/d, n=384), Jul LONG (+25.0bps/d, n=391), Aug SHORT (-3.6bps/d, n=422), Sep LONG (+11.6bps/d, n=383), Nov SHORT (-4.2bps/d, n=389), Dec LONG (+13.8bps/d, n=387)

## Data

- yfinance daily OHLCV for ZC=F / ZW=F, free, no key. Cached to `tools/cache/h031_harvest_cache.json`.
- Out-of-sample test-year resolved records: **3555**.

## Harness verdict (THE gate — harness imported UNMODIFIED)

- per-window eff (new->old): ``
- windows scored: 0  (strong: 0)
- sign: `mixed`  same-sign ok: False
- harness `is_admissible()`: False
- harness reason: REJECTED — only 0/0 windows reach eff>=0.3

## Edge & cost survival (out-of-sample test years)

- pooled WR: 49.48%
- gross mean per-trade return: 0.000852
- net mean per-trade return (after 30bps): -0.002148
- cost-survival (|gross| > 30bps): 84.5%  (gate >= 60%: PASS)

## VERDICT: **UNTESTED**

Honest data-gap non-verdict. COMMODITY harvest-seasonal windows are sparse — the out-of-sample period did not give the harness >= 3 scored 14-day windows. Not a pass and not a clean fail; the blocker is sample coverage. A longer out-of-sample period or more grain contracts would help.
