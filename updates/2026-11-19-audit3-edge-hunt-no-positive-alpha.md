# Edge hunt — there is no positive selection alpha in this ledger (and where value is destroyed)

**Date:** 2026-11-19
**Question:** the win rates look bad; can we find a *proven* edge?
**Answer:** not a positive one. We can prove, with intervals, where the system
destroys value — and that is the part an edge has to survive.

**New code**
- `alpha_engine/audit3_edge_hunt.py` — beta accounting, mirror test, leakage-free
  point-in-time gate replay, pre-registered battery, power/MDE.
- `alpha_engine/audit3_selection_alpha.py` — M1b: pick return minus
  direction-adjusted buy & hold over the same window, priced from the project's
  own `crypto_ohlcv` / `equity_daily_ohlcv` / `etf_daily_ohlcv` tables.
- `tests/test_audit3_edge_hunt.py` (15), `tests/test_audit3_selection_alpha.py` (9).

**Input:** live `dashboard_data.json`, 3,500 closed picks, 2026-02-21 → 2026-11-19
(246 distinct days), net of per-class slippage. Whole book: **−0.188%/trade**.

## 1. The "crypto short edge" is market beta, counted once

| | n | net/trade |
|---|---|---|
| CRYPTO LONG | 1,281 | **−1.136%** |
| CRYPTO SHORT | 570 | **+0.886%** |

Under pure beta, `mean(long) + mean(short) ≈ −2 × cost`. Observed: **−0.250%**
vs −0.300% predicted. The short mean implies a drift of **−1.036% per holding
window**, which predicts a long mean of −1.186%; observed −1.136%. Residual
selection alpha: **+0.025%** — inside one round-trip cost.

So the headline "crypto shorts win, crypto longs lose" is one fact about the
market (crypto fell ~1% per window), not two facts about skill. The monthly
table confirms it: in 2026-04 shorts were −0.09% while longs were +0.01%; the
whole +0.886% comes from October–November.

The tribunal's `PROVEN_EDGE` on T1 and `PROVEN_HARM` on T2 are therefore
statistically correct and economically meaningless without this decomposition.

## 2. The walk-forward gate is a rear-view mirror

`wf_verdict ∈ {VIABLE, STRONG}` looks superb: n=480, +0.964%/trade, q=0.0004,
positive spread in **10/10 months**, and positive in *every* class-direction
slice (crypto long +0.97%, crypto short +1.04%, equity +1.97%, ETF +0.84%).
That pattern is exactly what a contaminated flag looks like.

The leakage-free replay only lets a strategy's **already-closed** picks vote:
`prior WR >= 65%` → **−0.187%/trade (n=129)**; `55–65%` → +0.073% (n=246);
`35–45%` → +0.011% (n=1,023). Hi-vs-lo difference **+0.167%, CI [−0.686, +1.036],
not proven**. The apparent edge does not survive knowing only the past.

Corroborating: `at_issue_strat_fwd_wr` exists on just **215 of 3,500** rows (66 of
those are zero) while `strat_fwd_wr` is populated on 3,398 — the "at issue"
snapshot is largely absent, and the flag is derived from a field that fills in
later.

**Consequence:** the walk-forward gate cannot be used as evidence until the
pipeline stamps its inputs at issue time.

## 3. M1b selection alpha — the actual test of skill

Priced 2,213 of 3,500 picks from local OHLC. `alpha = pick net − direction-adjusted
hold over the same entry→exit window`.

| slice | n | pick | hold | **alpha** | 95% CI |
|---|---|---|---|---|---|
| whole book | 2,213 | −0.139% | +0.157% | **−0.296%** | [−0.621, +0.053] |
| CRYPTO | 1,712 | −0.305% | +0.051% | −0.357% | [−0.765, +0.057] |
| EQUITY | 240 | +0.908% | +0.794% | +0.114% | [−0.407, +0.593] |
| **ETF** | 261 | −0.008% | +0.264% | **−0.272%** | **[−0.504, −0.037]** |
| **CRYPTO LONG** | 1,142 | — | — | **−0.442%** | **[−0.892, −0.085]** |
| CRYPTO SHORT | 570 | — | — | −0.187% | [−0.964, +0.778] |
| EQUITY LONG | 239 | — | — | +0.115% | [−0.379, +0.589] |
| **ETF LONG** | 261 | — | — | **−0.272%** | **[−0.504, −0.037]** |

Two intervals exclude zero, and **both are negative**:

- **CRYPTO LONG: −0.442%/pick vs simply holding the same coin long.** The book
  does not merely suffer the market falling (−1.14%/pick); it underperforms the
  fall itself by another 0.44 points. Median crypto TP/SL is +2.50%/−1.50%,
  so the exit machinery is taking profit and stopping out *before* the move the
  hold would have captured.
- **ETF LONG: −0.272%/pick vs holding the ETF.** Intraday churn on instruments
  whose own drift was +0.264% during the same windows.

EQUITY LONG is alpha-neutral (+0.115%, CI spans zero): the equity picks neither
add nor destroy selection value; their +0.908% is mostly the underlying.

**No slice anywhere produces a positive alpha interval.** That is the answer to
the question.

## 4. What this does and does not license

Licensed by the data:
1. Stop emitting crypto longs under the current TP/SL geometry — proven to lose
   to the beta (−0.44%/pick) and to zero (−1.14%/pick).
2. Stop intraday ETF churn — proven to lose to holding (−0.27%/pick).
3. Treat `wf_verdict` as unproven until at-issue stats exist; do not size on it.
4. Keep the SWING timeframe out (−1.305%/trade, n=389): it is a proven harm.

Not licensed:
- Any claim of positive edge. Nothing here has a positive alpha CI.
- Inverting the crypto long book: the loss is beta plus exit geometry, and
  inverting would flip the beta sign in a rising market.

## 5. What would actually prove an edge

- **At-issue snapshots** on 100% of rows (today 6%), so gates can be replayed.
- **Selection-alpha CI > 0 in two different regimes** (e.g. a crypto up-month and
  a down-month), not just across months of one drift.
- **n counted in independent windows, not picks**: picks inside the same hour
  share one market move, so the effective n is closer to the hour count.
- The cheapest candidate that could get there: a *hold-benchmark pilot* — emit
  the pick and the same-symbol hold side by side in paper for a fixed window,
  and require alpha > 0 before the pick is allowed to size.

## 6. Limitations

- 1,287 picks could not be priced (FOREX 211, EQUITY 521, ETF 323, BOND 34,
  COMMODITY 55, FUTURES 4, no timestamp 130). Forex has no usable price table
  mapping, so its alpha is unknown rather than zero.
- Daily-bar alignment for equities/ETFs allows a 5-day tolerance and uses the
  first close at/after each timestamp; intraday equity alpha is approximate.
- Beta accounting assumes comparable entry/exit windows on both sides.
- Nine months is one regime. Every result here is regime-scoped.

## Verification

- `python3 -m pytest tests/test_audit3_edge_hunt.py tests/test_audit3_selection_alpha.py -q` — 24 tests.
- `python3 -m alpha_engine.audit3_edge_hunt --picks /tmp/eh/dd.json --out reports/edge_hunt.json`
- `python3 alpha_engine/audit3_selection_alpha.py --picks /tmp/eh/dd.json --out ...`
  — covered 2,213/3,500, overall alpha −0.296% CI [−0.621, +0.053].
- `py_compile` on both modules.
