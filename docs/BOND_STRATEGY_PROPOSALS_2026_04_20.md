# BOND Strategy Proposals — S0 Hypotheses

**Date:** 2026-04-20
**Status:** S0 (hypothesis) per Strategy Factory v1.1 — NOT deployed, NOT in registry
**Data source:** FRED (`alpha_engine/bond_data_fred.py`)
**Motivation:** BOND asset class currently a "data desert" in the effectiveness
audit (n=12 resolved trades all-time, 0 active live picks). Adding reliable
yield/spread data unlocks systematic BOND signal emitters.

## Reference snapshot (12m window, 2025-04-20 → 2026-04-20)

| Series        | Latest | 12m Min | 12m Max | Median |
|---------------|-------:|--------:|--------:|-------:|
| DGS2          | 3.72   | 3.38    | 4.05    | 3.61   |
| DGS10         | 4.26   | 3.97    | 4.58    | 4.23   |
| DGS30         | 4.88   | 4.54    | 5.08    | 4.83   |
| T10Y2Y        | 0.52   | 0.43    | 0.74    | 0.55   |
| T10Y3M        | 0.61   | -0.17   | 0.71    | 0.13   |
| T10YIE        | 2.38   | 2.22    | 2.45    | 2.32   |
| T5YIFR        | 2.16   | 2.05    | 2.41    | 2.23   |
| BAMLH0A0HYM2  | 2.87   | 2.64    | 4.16    | 2.94   |
| BAMLC0A0CM    | 0.81   | 0.73    | 1.12    | 0.81   |

---

## S0-1: Yield-Curve Carry & Roll-Down (2s10s)

**Hypothesis:** When `T10Y2Y` is positive *and* steepening (5d delta > 0)
while `DGS10` is range-bound, a long 7-10Y duration position (e.g. `IEF`
proxy) earns both coupon carry and roll-down P&L as the held bond walks
down a positively-sloped curve. Entry: `T10Y2Y > 0.30 pp` AND 5d change
> 0 AND `DGS10` 20d realized vol < 12 bp/day. Exit / stop: `T10Y2Y`
flattens below 0.20 pp, or `DGS10` breaks its 60d high. Target horizon:
20 trading days. Kill switch: curve inverts (`T10Y2Y < 0`). Current
regime (0.52 pp, trending up from 0.43 min) is near the entry zone —
backtest needs to validate on 2017-2019 and 2024-2025 steepening episodes.

## S0-2: TIPS Breakeven Mean Reversion (5y5y Forward)

**Hypothesis:** The 5y5y forward breakeven (`T5YIFR`) is the Fed's
preferred market-implied long-run inflation gauge and historically
mean-reverts to 2.00-2.30% with a half-life of roughly 30-60 trading
days. When `T5YIFR` deviates > 1.0 σ from its 252d mean, fade the move:
short breakevens via TIP/IEF spread (or long TIP if below band, short if
above). Entry thresholds (from 12m stats): z > +1.0 (≈ 2.35%) → short
breakevens; z < -1.0 (≈ 2.10%) → long. Stop: 1.5 σ adverse. Current
reading 2.16% (near lower band) hints at a long-breakeven setup pending
formal z-score + cointegration checks. Risk: inflation regime break —
kill if monthly CPI surprises > 0.3 pp for two consecutive prints.

## S0-3: Credit Spread Regime Switch (HY OAS)

**Hypothesis:** The ICE BofA US HY OAS (`BAMLH0A0HYM2`) is a
high-frequency risk-regime oscillator. Regime flips from "tight" (< 350
bp) to "widening" (5d Δ > +25 bp or level > 420 bp) precede equity and
HY-bond drawdowns by 3-10 days. Signal: when HY OAS crosses above its
63d moving average by > +15 bp AND the 5d change is positive, rotate
BOND allocation from HY/IG corporates into long-duration Treasuries
(`DGS30`); reverse when OAS crosses back below the MA and 5d Δ < 0. Hard
stop: OAS breaks 60d high by > 30 bp (defensive exit regardless).
Current OAS at 2.87% / 287 bp (median 294 bp) is comfortably in "tight"
regime — useful as a calibration baseline. Kill switch: OAS prints > 600
bp (stress regime, governance re-review required).

---

## Next steps (not part of this task)

1. Backtest each S0 against 2015-2025 daily data; require Sharpe > 0.8,
   max DD < 8%, ≥ 60 trades before S1 promotion.
2. Wire into the signal bus as `emitter_bond_*` with a separate
   `BOND_FRED` data lineage tag (distinct from existing `alpha_engine/
   fred_liquidity.py` liquidity signal).
3. Log first 20 paper trades before any live allocation per
   `TESTING_PROTOCOL.MD` §7.
