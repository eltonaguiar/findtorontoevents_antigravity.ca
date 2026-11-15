# Near-miss rule and passive pivot

Stamp: 2026-11-15T0703Z. Applies to this repo. Not a claim that any sleeve is money-ready.

## Near-miss: paper clock, not a longer backtest

A near-miss is a candidate that already passed next-bar entry, walk-forward, friction, and the shuffle control, and failed only because n is too small for the CI or the bootstrap. H-103 is the current example: the backtest was filed, the binding test is forward n>=100, and `verified_strategies/paper_pilot/h103_forward_log.jsonl` has unscored month stamps, not closed trades.

Extend the paper test. Do not extend the backtest window after seeing the result.

A longer history searched until the CI clears zero is another trial. It must be a new registry id, locked before the run. Reusing the same sample with a new end date, a new lookback, or a dropped symbol is the search that made prior years fail.

Practical rule:

- If rungs 1, 2, 5, and 8 passed and only n is short: keep the frozen parameters. Score the months already logged. Let the pre-registered horizon accrue. Do not backfill a month that was not logged (H-103 is missing August).
- If walk-forward or the shuffle control failed: the candidate is dead. More data will not rescue a leak or a drifting parameter.
- Deploy size stays zero until the registered n and the cost-adjusted CI both clear.

## If the whole sweep is negative

Read the signature, then stop that family. Noise means do not spawn cousins. A cost death means a lower-turnover version only as a new id. A shuffle failure is a bug, not a market conclusion.

Publish the negative result: trial count, the deflated-Sharpe bar, and which rung killed each family. That file is the protection against repeating the search.

## Passive pivot for the audit page

If no directional rule passes, the measurable product is a passive allocation, not another pick tile.

What to show:

- One pre-registered book, not a scanner. Default: low-cost equity ETF plus a cash or short-bond sleeve (BIL or SGOV), or the already-registered H-103 universe held on its monthly rule. Pick one. Do not blend them after looking at both.
- Benchmark on the same window: SPY for the equity sleeve, BIL for the cash sleeve, and the 60/40 or the stated mix for the book.
- Proof that can pass: the book is long beta. Report CAGR, max drawdown, and tracking difference versus the benchmark after the stated expense ratio. Do not report a win rate. Do not show TP/SL. A passive book is not a pick.
- Label: `sizing_allowed` may be true only for the passive sleeve, and only as "matches the benchmark within costs," never as alpha. `money_ready` stays empty for every directional strategy.
- Kill: if the live book lags the benchmark by more than the expense ratio plus 50 bps over a full year, the implementation is wrong. That is an operations kill, not an alpha kill.

What not to do:

- Do not put penny stocks, $2–5 names, or a 1-of-10 rocket list on the audit page as a consistency strategy. That is a lottery. Survivorship hides the nine that go to zero. This repo's penny book is not a positive-expectancy sample.
- Do not leave STRONG_BUY emitters writing unregistered Faber, GLD, or BTC rows beside a passive panel. Those rows will be read as the product.
- Do not call drawdown reduction "profit" unless the comparison is paired on the same dates and net of the fee.

The honest sentence for the page: no directional class is proven; the measurable path is a named ETF allocation versus its benchmark, tracked monthly, with the fee stated.
