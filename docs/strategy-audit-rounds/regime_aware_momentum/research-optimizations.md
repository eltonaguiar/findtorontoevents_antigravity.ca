# Research & Optimizations — regime_aware_momentum

This page lists real academic and industry references underpinning the
`regime_filtered_momentum` production module, plus concrete optimization
options ranked by expected value against the FRED-gated 12-1 baseline.

## Primary references

- **Jegadeesh, N. & Titman, S. (1993).** "Returns to Buying Winners and
  Selling Losers: Implications for Stock Market Efficiency." *Journal of
  Finance* 48(1): 65-91. The seminal cross-sectional momentum paper; J&T
  documented the 3-12 month winner-minus-loser anomaly that survives in
  out-of-sample tests four decades later.
- **Asness, C. S., Moskowitz, T. J., & Pedersen, L. H. (2013).** "Value
  and Momentum Everywhere." *Journal of Finance* 68(3): 929-985. Confirms
  the 12-1 specification (skip-the-most-recent-month) generalizes across
  countries and asset classes.
- **Asness, C. S., Frazzini, A., & Pedersen, L. H. (2019).** "Quality
  Minus Junk." *Review of Accounting Studies* 24: 34-112. AQR's framework
  for combining momentum with quality factors; informs the future
  optimization where confidence is scaled by quality score.
- **Daniel, K. & Moskowitz, T. J. (2016).** "Momentum Crashes." *Journal
  of Financial Economics* 122(2): 221-247. Documents that momentum
  strategies suffer extreme drawdowns when bear markets reverse; explicit
  motivation for the macro gate in this strategy.
- **Estrella, A. & Hardouvelis, G. A. (1991).** "The Term Structure as a
  Predictor of Real Economic Activity." *Journal of Finance* 46(2):
  555-576. Foundational paper establishing the 10Y-2Y spread as a US
  recession leading indicator.
- **Estrella, A. & Mishkin, F. S. (1998).** "Predicting U.S. Recessions:
  Financial Variables as Leading Indicators." *Review of Economics and
  Statistics* 80(1): 45-61. Updated curve-as-recession-indicator with
  out-of-sample probit specifications.
- **Moskowitz, T. J., Ooi, Y. H., & Pedersen, L. H. (2012).** "Time
  Series Momentum." *Journal of Financial Economics* 104(2): 228-250.
  Time-series (vs cross-sectional) momentum is a candidate v2 extension.
- **Hong, H., Lim, T., & Stein, J. C. (2000).** "Bad News Travels
  Slowly." *Journal of Finance* 55(1): 265-295. Justifies asymmetric
  long-vs-short treatment in this strategy: short-side momentum returns
  are historically weaker.

## Optimizations ranked

1. **Volatility-targeting overlay** (Moskowitz, Ooi, Pedersen 2012, table V).
   Scale each LONG position by `target_vol / realized_vol` so the equal-
   weight portfolio runs at constant risk. Expected effect: Sharpe lift of
   ~0.2-0.4 on real data; reduces 2008/2020-style crash drawdowns.

2. **Replace 12-1 with multi-horizon (3-1, 6-1, 12-1) blend.** Asness et al.
   2013 show the average of 3, 6, 12-month signals is more robust than any
   single horizon. Implementation: sum z-scores, rank by composite.

3. **Quality-momentum interaction** (AQR QMJ + momentum). Filter momentum
   universe to top-half by gross profitability or ROIC before ranking by
   12-1 returns. Documented to cut crash risk in half on US large caps.

4. **Time-series momentum component** (TSMOM, MOP 2012). Add a per-symbol
   trend filter: only enter LONG if the same symbol's 12m return is also
   positive. Cuts cross-sectional whipsaws when entire universe is falling
   together (e.g., 2008Q4).

5. **Curve-slope continuous gate** rather than 3-bin labels. Use the raw
   T10Y2Y value as a continuous confidence multiplier. Estrella &
   Hardouvelis 1991 found a near-monotonic relationship between curve
   slope and future GDP growth; the 3-bin labels in `fred_macro_context`
   discard signal.

6. **VIX term structure (VIX9D / VIX) instead of VIX level.** When the
   short-end VIX exceeds the standard VIX (backwardation), the panic
   signal is sharper than a level threshold. FRED has VIXCLS, but VIX9D
   would need a CBOE feed.

7. **Idiosyncratic momentum via residuals from a 3-factor model.** Blitz,
   Huij, Martens (2011) "Residual Momentum" shows momentum on Fama-French
   3-factor residuals has Sharpe roughly 2x raw momentum and far smaller
   drawdowns. Repo already has `alpha_engine/residual_momentum.py` —
   future PR can fuse the two.

## Out-of-scope but worth tracking

- AQR Capital's published live performance for "Momentum Long-Only" /
  "AMOM" sleeves (their public 13F filings give a noisy but useful prior).
- iShares MTUM ETF live results (post-2013 launch) as an external
  benchmark for un-gated 12-1 momentum.
- DBMF / KMLM managed-futures benchmarks for the time-series momentum
  variant.
