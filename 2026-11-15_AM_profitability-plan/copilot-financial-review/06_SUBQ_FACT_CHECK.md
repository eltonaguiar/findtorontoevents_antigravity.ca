# SubQ methodology consultation and independent fact-check

## What actually ran

Two HTTP200Calls to the official Decisions endpoint, model`subq-snap-1.2`, eight abstract questions per call. One arm supplied only questions; the second supplied generic public financial principles. Sanitized requests, timestamps, question schemas, request hashes and returned decisions are in [SUBQ_METHODOLOGY_REVIEW.json](./SUBQ_METHODOLOGY_REVIEW.json).

The locally stored credential was used only in an Authorization header; no key, personal portfolio, source code or confidential file was sent or retained in the output.

The API returned structured decisions/scores, not researched citations or explanations. The table's **independent reasoning is ours**, corroborated below. Difference between bare/evidence arms is sensitivity, **not fact-check verification**.

| Question | SubQ P(yes), bare / principles | Independent check |
|---|---:|---|
| Enough fund holding time guarantees positive real return **and** SPY outperformance | 0.001329 / 0.000337 | Unsupported guarantee. FINRA says fund/ETF risks depend on holdings and can lose; exact-index exposure does not automatically beat its benchmark |
| Zero approved survivors among23proves no profitable strategy anywhere | 0.000317 / 0.000156 | Invalid universal inference from a finite selected family; no theorem/prospective probability follows |
| An authentic contest-winning account alone proves replicable risk-adjusted retail alpha | 0.000301 / 0.000224 | Official World Cup multiple-account/past-result caveats; exact rules/ledger/OOS/risk and replication are missing |
| Visible leader positions without fills/full hedge/fees/latency/exits establish follower profit | 0.000313 / 0.000223 | Incomplete cashflow and execution accounting cannot establish follower account PnL |
| A real flat intraday fill differing from daily close proves fabrication | 0.001375 / 0.000535 | Different market timestamps can legitimately differ; daily close is not intraday execution |
| +15%strategy beats matched+18%SPY in absolute return | 0.000332 / 0.000241 | Arithmetic:15<18. Positive profit is not benchmark outperformance |
| Lower drawdown alone proves positive factor-adjusted alpha | 0.000199 / 0.000151 | Cash/less-beta exposure can reduce drawdown without alpha; risk-matched control/regression required |
| Best first task with unverified fills/marks/costs | measurement choice, confidence0.999671 /0.999714 | Garbage labels/costs invalidate subsequent profitability estimates; measurement before tuning is a methodological recommendation |

**These are model decision probabilities, not empirical market frequencies or profitability probabilities.** Very confident answers are not evidence the provider is calibrated. The consistent conclusions are independently supported; scores themselves do not support capital admission.

## Source checks and limits

- [SubQ official docs](https://docs.subq.ai/) and [Decisions API](https://docs.subq.ai/endpoints/decisions-api/) establish endpoint/model/schema behavior, not an investment oracle.
- [Data retention](https://docs.subq.ai/using-the-api/data-retention/) describes provider retention; only abstract questions/public principles were transmitted.
- [FINRA funds/ETF](https://www.finra.org/investors/insights/etf-vs-mutual-fund) supports wrapper mechanics and investment loss risk.
- [Official World Cup caveats](https://www.worldcupchampionships.com/world-cup-trading-championship-standings) qualify contest-account claims.
- Numerical return comparison, timestamps and complete-account identity are direct arithmetic/logical checks, not AI-authority claims.

No provider response was allowed to invent historical returns, fetch a website it did not access, certify Hoffman wins, approve code, or grant trading authority. No future strategy-success percentage has been inferred.
