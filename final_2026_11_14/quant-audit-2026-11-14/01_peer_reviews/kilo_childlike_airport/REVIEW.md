# Peer Review — Kilo "VALIDATED" Regime-Filtered VWAP Mean Reversion

**Verdict: REFUTED as stated.** The claim is arithmetically impossible in its own published units,
and its PBO gate is inverted. The underlying *idea* (regime-conditional mean reversion) is not what
fails — the *certification* fails.

Source: `updates/2026-11-14-PROFITABLE-APPROACH-VWAP-MEAN-REVERSION.md`, committed at `45168e2528a`
(verified: commit exists, file present on `main`, blob `06302e88c`).

---

## Refutation 1 — the Sharpe cannot be annualized (fatal)

From their own Test A table:

| Quantity | Their value |
|---|---|
| Total return | 12.7% |
| Test period | "~22 months" (730d cap) |
| Reported Sharpe | **3.76** |

Sharpe = annualized return ÷ annualized volatility. So:

```
CAGR        = 12.7% / 1.83y              = 6.93%/yr
implied vol = 6.93% / 3.76               = 1.84%/yr
```

A 4h crypto book at **40% position size** cannot have 1.84% annualized volatility. BTC alone
realizes ~40–60%/yr. The reported 3.76 is therefore a **per-trade or per-bar** ratio (their
per-symbol Sharps of 10.30, 13.59 confirm it — those are per-trade numbers printed in a column
labelled Sharpe), presented alongside annualized return and drawdown as if commensurable.

The same error propagates to their headline "DSR P(Sharpe>0) = 1.0000, z ≈ 16": a z of 16 comes
from `sqrt(n) × per-trade Sharpe`, i.e. assuming 129 independent draws with no deflation. This is
not the Deflated Sharpe Ratio. DSR requires deflating for the *number of trials*, and they ran a
grid across 5 symbols × parameters × harnesses `v7, v11, v12, v13, v14, v15, v16, v17` — dozens of
configurations, none of which enter the statistic.

## Refutation 2 — the PBO gate is inverted

| Their label | Their value | Their gate | Correct reading |
|---|---|---|---|
| PBO | **0.489** | `< 0.5` → **PASS** | PBO 0.489 ≈ a coin flip that the OOS result is no better than the median IS combination. This is the definition of *overfit-indistinguishable*. |

`PBO < 0.5` is not a gate; it is the boundary at which the metric stops being informative. The
repo's own standard (`docs/BACKTEST_ADMISSIBILITY_STANDARD.md`) requires **PBO ≤ 0.10**. Their own
document restates the strict threshold as 0.3 and then marks it "FAIL (sample size)" while still
declaring the approach VALIDATED. You cannot certify an edge on the gate you failed.

## Refutation 3 — the regime filter admits trades by default

Their viability snippet (reproduced in the doc):

```python
if regime in MR_COMPATIBLE or regime == 'UNKNOWN':
```

- `'UNKNOWN'` is assigned whenever `len(price_hist) < 60` **or** the detector declines to classify —
  i.e. the filter's failure mode is "trade anyway".
- `MR_COMPATIBLE` includes `CRISIS` and `HIGH_VOLATILITY`. Mean reversion in a crisis regime is
  precisely the configuration that produces the −45% drawdowns they cite as the reason to size at 40%.

So the "regime filter" is not a filter at the boundary; it is a filter in the middle.

## Secondary inconsistencies

- Per-symbol returns sum to 14.7% (2.9+3.5+2.5+1.6+4.2) against a stated 12.7% total — unexplained
  aggregation (equal-weight vs compounded).
- Per-symbol MDDs of 2.6–3.5% with 2% stop-losses and 40% sizing imply each loss ≈0.8% of equity;
  a 10% portfolio drawdown then requires ~12 consecutive losses, but 129 trades over 22 months is
  ~6/month. The drawdown path is not reconstructable from the published table.
- **Symbol survivorship inside the test:** 8 symbols were run; DOGE, AVAX and LINK "are not
  profitable on 4h" and are excluded from the validated set. Selecting the 5 that worked is a
  second, uncounted selection layer on top of the parameter grid.
- The harnesses live in `/tmp/kilo/*.py` — not in the repo, not on any branch, and `/tmp` is
  ephemeral. The claim is **unreproducible by construction**, which is why I refuted it from their
  own table rather than by re-running.

## What is fine

- yfinance **does** serve `interval='4h'` — I verified it (yfinance 1.3.0, 30 rows over 5 days, last
  bar 2026-11-14 20:00 UTC). The data mechanism is real.
- Chronological 70/30 split with parameters chosen on train only is the right shape.
- The negative results they publish (Donchian 4h MDD 35%, Bollinger "too few trades", Faber TAA 8
  train trades) are useful and consistent with my own findings that breakout families fail on
  realistic costs.

## Recommendation

Do not promote this approach. If the operator wants it pursued, it must be **re-run by someone
else** with: annualized Sharpe on a fixed bar clock, DSR deflated by the full trial count,
PBO computed by CSCV at ≤0.10, an explicit `UNKNOWN → no trade` rule, crisis regime excluded, and
the 8-symbol selection declared up front. My own RSI(2) mean-reversion test on 2021–2026 daily data
reached null p=0.080 — promising enough to keep researching, nowhere near enough to certify.
