# Mutual funds — and the low-capital / low-fee subset

**Read this first:** "mutual funds are very likely profitable" is true, and it is a different claim
from everything else in this folder. It is the **equity risk premium**, not a prediction edge. A fund
held for 15 years makes money because the market makes money, on average, over long horizons. The
system in this repo cannot add to that, and its own ledger has **no mutual fund class at all**
(`readiness.by_class` = BOND, COMMODITY, CRYPTO, EQUITY, ETF, FOREX, FUTURES, MEME, PENNY_STOCK;
0 mutual fund rows across 3,500 closed picks — verified).

That distinction decides how this answer should be used: mutual funds are the **highest-probability
positive return** available and the **lowest-value prediction target**. They belong in the portfolio,
not in the pick engine. Peer packages agree unanimously (`hilarious-seer/MUTUAL_FUNDS.md`: NOT_BUILT;
`finpredict-v2`: do not build a live class).

## Why a mutual fund cannot be a live pick class (structural, not a judgment call)

| Constraint | Consequence |
|---|---|
| NAV struck once daily, after close | no intraday mark-to-market, no live PnL |
| Orders execute at *next* NAV | a "pick" cannot be entered at a known price |
| TP/SL execute at next NAV only | the entire resolver model (intrabar TP/SL) is meaningless here |
| Frequent-trading limits (often 30 days) | turnover-based strategies are structurally barred |
| Expense ratio + possibly load | cost model must include a fee the other classes do not have |

Any mutual fund "pick" is therefore an **allocation recommendation on a monthly clock**. It should be
labelled that way, never as an active pick.

## The subset asked for: less money in, less ongoing cost, less maintenance

Screen on **structural criteria you can verify from a fund's prospectus**, not on names. This is a
filter, not a recommendation list — no fund here has been audited by me.

| Criterion | Threshold | Why this one |
|---|---|---|
| Expense ratio | **≤ 0.20%**, ideally ≤ 0.10% | the only cost that compounds against you every year, guaranteed |
| Front/back load | **0%** | a 5% load is ~5 years of a 1% edge destroyed on day one |
| 12b-1 / trailing commission | **none** | hidden distribution fee, often 0.25–1.00%/yr |
| Minimum initial investment | **≤ $1,000**, ideally $0 | the "less money in" requirement, literally |
| AUM | **≥ $1B** | small funds get merged or liquidated; forced taxable events |
| Portfolio turnover | **≤ 20%/yr** | high turnover = tax drag + trading cost inside the fund |
| Tracking | R² ≥ 0.99 and tracking error ≤ 0.25% vs its index | proves it is actually passive |
| Share class | index / institutional / ETF share class where offered | same portfolio, lower fee tier |

Typical ranges worth expecting — **to verify per fund, not measured here**: broad-market index funds
sit around 0.03–0.20% expense ratio with $0–$3,000 minimums; actively managed equity funds commonly
run 0.60–1.20%; target-date funds 0.08–0.60% depending on whether the underlying is index or active.

## Ranked by "least capital + least maintenance", not by expected return

| Rank | Instrument type | Capital needed | Ongoing effort | What it actually buys |
|---|---|---|---|---|
| 1 | **Broad-market index fund / its ETF share class** | $0–$1,000 | none after purchase | the market return, minus ~0.05% |
| 2 | **Target-date index fund** | often $0–$1,000 | none — auto glide path | the same, with allocation drift handled |
| 3 | **Money-market fund** | often $0 | none | capital preservation, not growth |
| 4 | **Low-cost balanced / allocation fund** | $0–$3,000 | none | bond+equity mix without two purchases |
| 5 | Actively managed sector/thematic fund | $1,000–$3,000 | none, but higher fee | a bet, at 0.60–1.20%/yr |

Rank 1 and 2 are the honest answer to the question as asked: minimum capital, minimum fee, zero
maintenance. Everything below rank 3 trades more of your money and time for a *narrower* bet, which
is the opposite of what was requested.

## The trap in the premise

"High chance to be profitable" is horizon-dependent, and the repo's own data cannot test it:

- Over 1 month, a broad equity fund is roughly a coin flip. Over 15 years it has historically been
  positive — that is the premium, not a forecast.
- The cost of the fee is **certain** and the return is **not**. That asymmetry is why the expense
  ratio is the first column, not the last.
- A fund bought near a peak and sold in a drawdown is still a loss for that investor. "Profitable"
  needs the holding period stated, or it is not a claim.

## If mutual funds are to be measured at all

Minimum viable test, monthly clock, no intraday claims:

1. 10+ years of monthly NAV history per candidate, survivorship-free (delisted funds included).
2. Benchmark = **category average**, not zero, and not the S&P 500 for a bond fund.
3. Costs = expense ratio + any load + a 10bp monthly rebalance allowance.
4. Walk-forward with monthly folds; report the number of trials.
5. Gate: beats its category benchmark net of fees at n ≥ 120 monthly observations.

Until that exists, the dashboard should keep showing mutual funds as `NOT_BUILT`. It does today, and
that is correct.

## Bottom line for the focus decision

Mutual funds **do not count** toward the "1–2 profitable asset classes" goal, because they are not a
prediction problem and this system adds nothing to them. They solve a different job — cheap, passive,
low-maintenance market exposure — and on that job the low-fee index subset at rank 1–2 is the right
answer. Counting them as an "asset class win" would flatter the scorecard without testing the system.
See `../03_focus/DECISION.md`.
