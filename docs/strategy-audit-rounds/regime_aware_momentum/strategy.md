# Strategy: regime_aware_momentum (production module: regime_filtered_momentum)

**Status:** new production strategy, shipped 2026-05-09. Closes the gap surfaced
by `docs/strategy-audit-rounds/COVERAGE_VALIDATION_2026-05-09.md` where prior
audit-round boilerplate (rounds 009/019/029/039) had reports for
`regime_aware_momentum` but no actual production definition existed.

**Production module:** `alpha_engine/regime_filtered_momentum.py`
**Entry point:** `regime_filtered_momentum(data: dict[str, pd.DataFrame], **kwargs) -> list[dict]`

## Edge thesis

The strategy combines two of the most replicated effects in the empirical
asset-pricing literature:

1. **Asness 12-1 cross-sectional momentum.** Following Jegadeesh & Titman
   (1993) "Returns to Buying Winners and Selling Losers" and Asness, Frazzini,
   Pedersen (2013) "Quality Minus Junk" / AQR's value-and-momentum work, we
   compute each symbol's 12-month return while skipping the most recent month
   to dodge the well-documented short-term reversal effect. The signal is
   `(close[-21] / close[-252]) - 1`. This factor has produced Sharpe ratios
   in the 0.6-1.0 range on US equity universes across decades, with the
   largest live drawdowns coinciding with macro-regime breaks (1932, 2002, 2009).

2. **FRED yield-curve recession gate.** Following Estrella & Hardouvelis (1991)
   "The Term Structure as a Predictor of Real Economic Activity" and the
   updated Estrella & Mishkin (1996, 1998) work, the slope of the Treasury
   curve (10Y-2Y, FRED series `T10Y2Y`) is one of the most reliable
   recession leading indicators ever discovered. Every US recession since
   1955 has been preceded by a curve inversion; the converse false-positive
   rate is low. Momentum strategies historically suffer their worst
   drawdowns when the macro regime breaks. By gating LONG entries to
   non-inverted curves and below-elevated VIX, we suppress entry into the
   exact regimes where the factor is most fragile (Daniel & Moskowitz 2016,
   "Momentum Crashes").

## Regime gate logic

`alpha_engine/fred_macro_context.get_macro_context()` returns a snapshot
with three regime labels: `curve` (`inverted` / `flat` / `steep`), `vol`
(`low` / `normal` / `elevated`), and `usd` (informational only).

| curve     | vol       | LONG | SHORT | Rationale                                    |
|-----------|-----------|------|-------|----------------------------------------------|
| steep     | low       | yes  | no    | Best regime for momentum; full LONG          |
| steep     | normal    | yes  | no    | Healthy expansion                            |
| steep     | elevated  | no   | no    | Vol spike breaks momentum; stand aside       |
| flat      | low       | yes  | no    | Late-cycle but constructive                  |
| flat      | normal    | yes  | no    | Late-cycle constructive                      |
| flat      | elevated  | no   | no    | Risk-off late-cycle; stand aside             |
| inverted  | low       | no   | no    | Recession risk but no panic; flat            |
| inverted  | normal    | no   | no    | Recession risk; flat                         |
| inverted  | elevated  | no   | yes   | Recession + panic = momentum-crash short opp |
| any       | unknown   | yes  | no    | Default permissive (FRED unavailable)        |

The SHORT branch is intentionally narrow. Asness-style momentum has weak
short-side returns historically (Hong, Lim, Stein 2000), so we only enter
shorts in the one regime where the curve+vol combination strongly indicates
a regime break is in progress.

## Output contract

Each signal carries `regime_context` (snapshot of the macro labels at signal
time), `extra.momentum_12_1` (the raw factor value), confidence clamped to
[0.50, 0.95] via `|mom| / 0.20`, an 8% stop, and a 15% take-profit. Min
absolute momentum to enter: 5%.

## Rollback / failure modes

- Set `REGIME_MOMENTUM_DISABLED=1` to fully disable.
- If `fred_macro_context` import fails or `get_macro_context()` returns `{}`,
  the strategy degrades to **default-permissive LONG-only** with
  `_macro_unavailable=True` flagged on every signal so downstream filters
  can choose to drop those.
- If the universe DataFrames lack 252+1 bars, the symbol is silently skipped.
