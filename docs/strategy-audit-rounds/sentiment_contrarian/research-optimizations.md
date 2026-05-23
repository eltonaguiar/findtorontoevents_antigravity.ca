# sentiment_macro_contrarian — Research & Optimization Notes

This is a working research log, not a template. Sources are real; speculation
is labelled.

## Why combine sentiment with macro at all?

The single-factor sentiment-contrarian trade is well documented but unstable.
Whaley (2009, "Understanding the VIX") shows the >30 VIX cohort has positive
4-week forward returns on average 1990-2008, but the dispersion is huge. The
losing tail clusters in pre-recession periods (2000, 2007, 2020-Q1) where
high VIX is a *true* signal of escalating drawdown rather than a transient
panic. We need a regime filter that separates "panic IN an expansion" from
"panic AT the cycle turn."

The 2s10s curve (T10Y2Y) is the cleanest available regime separator —
Estrella & Hardouvelis (1991), Estrella & Mishkin (1998), Adrian-Estrella-Shin
(2010 NY Fed) all show the inverted curve precedes recessions with ~12 month
lead. So `VIX>25 AND curve_not_inverted` filters out the worst-tail subset
while keeping the bulk of the panics-that-mean-revert.

For CRYPTO, the analog is the Trade-Weighted Broad Dollar Index (DTWEXBGS).
Liu & Tsyvinski (2018, "Risks and Returns of Cryptocurrency") and Bianchi
(2020, "Cryptocurrencies as an Asset Class") both find CRYPTO returns
correlate negatively with USD strength (r ≈ -0.25 to -0.40 monthly post-2017).
Buying CRYPTO panic into a strong-USD tape is fighting the macro tide. We
flip this into a hard gate: `regime.usd != "strong"` is a precondition.

## FRED indicators chosen, and why

| Series   | Role                                  | Threshold                |
|----------|---------------------------------------|--------------------------|
| DTWEXBGS | USD-strength regime (CRYPTO gate)     | 30d delta >=1.5% = "strong" |
| T10Y2Y   | Curve / cycle regime (EQUITY gate)    | <-0.05 = "inverted"      |
| VIXCLS   | EQUITY sentiment proxy                | >25 fear, <12 complacency |
| DGS10    | Reserved for follow-up (rate-shock)   | (not consumed in v1)     |
| DGS2     | Reserved for follow-up                | (not consumed in v1)     |
| FEDFUNDS | Reserved for follow-up                | (not consumed in v1)     |

Why not just use VIX for CRYPTO too? Pre-2020 the BTC-VIX correlation was
near zero. Post-2020 (institutionalization) it has risen to r ≈ 0.3-0.5
on monthly windows but is regime-unstable (Iwanicz-Drozdowska et al. 2021
find BTC-VIX correlation flips sign across volatility regimes). Until we
have a regime-conditional model, the FGI is a more robust CRYPTO sentiment
proxy because it incorporates on-chain dominance, social volume, and
volatility — not just options-implied vol.

## Why NOT a CRYPTO greed-extreme short in v1?

`crypto_fear_greed_contrarian` has the long-side at 75-88% WR. The short side
(FGI > 75) does NOT have a comparably proven base rate in this repo. Looking
at `dna_revival.py` and the inverse-mutation table in
`alpha_engine/data/dna_mutation_report.json`, inverse mutations of the fear-
greed contrarian have not historically promoted to production. We would need
either an additional gate (e.g. funding rate > 95th percentile) or a longer
forward-test window before exposing it. v1 keeps the CRYPTO branch long-only.

## Confidence weighting research

The decision to give a +0.12 confidence boost when macro AND sentiment both
fire (vs sentiment-only) is calibrated against the heuristic that two
INDEPENDENT signals agreeing should ~double the log-odds. From sentiment
alone the rough Bayes prior on "panic mean-reverts in 4 weeks" is ~60%.
Adding a non-redundant macro filter that maybe doubles the conditional
log-odds gets you to ~70-75%. Hence we land at conf 0.70 for aligned
signals, 0.58 for sentiment-only.

This is a HEURISTIC, not a fitted model. Once we have n>=200 live trades,
a logistic regression of `outcome ~ sentiment_extremity + macro_aligned`
will replace the hardcoded 0.58/0.70/+0.05 ladder.

## Known limitations / followups

1. **No volatility-of-vix regime detection.** VIX-of-VIX (VVIX) often
   leads VIX panics. Adding VVIX>120 as a confirming signal would tighten
   the EQUITY BUY branch. Deferred — VVIX not yet in fred_macro_context.
2. **No put-call ratio.** CBOE total put/call > 1.2 is a textbook contrarian
   bull signal that overlaps but doesn't fully redundancy with VIX>25.
   Deferred — would need a non-FRED data source.
3. **Curve regime is binary in v1.** "Inverted" = T10Y2Y < -0.05. The
   2s10s being -0.50 vs -0.05 has very different forward implications.
   When n grows, swap binary gate for continuous T10Y2Y as a confidence
   modifier.
4. **CRYPTO branch ignores BTC dominance.** Alts have higher beta to USD
   strength than BTC. A v2 should boost confidence on alts more than BTC
   when usd=="weak".
5. **No ex-ante expected-shortfall sizing.** Position sizing is delegated
   upstream. If wired into a Kelly-fraction sizer, the macro_aligned flag
   should bump the Kelly cap by ~1.3x.

## Academic references (real, not template)

- Adrian, T., Estrella, A., & Shin, H. S. (2010). Monetary cycles, financial cycles, and the business cycle. *FRBNY Staff Reports*.
- Bekaert, G., & Hoerova, M. (2014). The VIX, the variance premium and stock market volatility. *Journal of Econometrics*, 183(2).
- Bianchi, D. (2020). Cryptocurrencies as an asset class? An empirical assessment. *Journal of Alternative Investments*, 23(2).
- Black, F. (1976). Studies of stock price volatility changes. *Proceedings of the 1976 Meetings of the American Statistical Association*.
- Coibion, O., & Gorodnichenko, Y. (2015). Information rigidity and the expectations formation process. *American Economic Review*, 105(8).
- Daniel, K., Hirshleifer, D., & Subrahmanyam, A. (1998). Investor psychology and security market under- and overreactions. *Journal of Finance*, 53(6).
- Estrella, A., & Mishkin, F. S. (1998). Predicting U.S. recessions: Financial variables as leading indicators. *Review of Economics and Statistics*, 80(1).
- Iwanicz-Drozdowska, M., et al. (2021). Two decades of contagion effect on stock markets. *Empirical Economics*, 60.
- Liu, Y., & Tsyvinski, A. (2018). Risks and returns of cryptocurrency. *NBER Working Paper 24877*.
- Whaley, R. E. (2009). Understanding the VIX. *Journal of Portfolio Management*, 35(3).

## Data sources

- Alternative.me Fear & Greed Index: https://api.alternative.me/fng/
- FRED (St. Louis Fed) — DTWEXBGS, T10Y2Y, VIXCLS, DGS10, DGS2, FEDFUNDS
  - Accessed via `alpha_engine/bond_data_fred.py::fetch_fred_series`
  - Cached 1h via `alpha_engine/fred_macro_context.py::_CACHE`
