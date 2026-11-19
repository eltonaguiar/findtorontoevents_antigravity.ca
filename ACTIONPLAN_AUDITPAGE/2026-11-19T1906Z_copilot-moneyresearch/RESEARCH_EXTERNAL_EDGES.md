Agent is idle (waiting for messages). agent_id: 6dd50096-973b-4b38-8010-24140b82f49a, agent_type: research, status: idle, description: Research per-asset-class edges, elapsed: 131s, total_turns: 1

[Turn 0]
# Retail trading edges by asset class for a ~$2,000 account (as of Nov 2026)

## Summary

- **Pick:** ETF trend/tactical allocation is the one class with credible net-of-cost evidence at a tolerable cost for a $2,000 account. Its horizon is monthly, not days-to-weeks.
- **Short-horizon trading:** every class's short-horizon retail track record is dominated by losses, because costs and informed counterparties absorb the gross edge. The strongest evidence is for day trading (Brazil, Taiwan), CFD/FX accounts and prediction-market takers.
- **Outdated premise:** the PDT $25k rule no longer exists for US equities (see 3 below).
- **Source quality:** the academic papers are primary. Many 2026 figures come from secondary blogs and aggregators (loss-rate tables, funding-rate datasets, prop-firm statistics, fee tables). I flag these as [secondary]. Treat them as directional until checked against the primary source.

## Cross-asset facts on retail failure and access

**Day-trading failure studies**
- **Brazil:** of 19,646 people who started day-trading mini-index futures in 2013–15, 1,551 persisted 300+ days. 97% of those lost money, only 1.1% earned more than minimum wage, and only 0.5% earned more than a bank teller's starting salary.
  - Chague, De-Losso & Giovannetti, "Day Trading for a Living?": https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3423101
  - Summary [secondary]: https://tradeedgealpha.com/day-trading-success-rate.html
- **Taiwan:** Barber, Lee, Liu, Odean & Zhang (2020), RAPS 10(1):61-93.
  - Day traders lost about 7 bp per day gross and about 23.9 bp per day net of fees, 1992–2006.
  - 72–74% of volume came from traders with a history of losses.
  - Survival was 44% at one year and 15% at three years.
  - Fewer than 3% of day traders were "predictably profitable."
  - Abstract: https://econpapers.repec.org/RePEc:oup:rasset:v:10:y:2020:i:1:p:61-93.
  - Detail [secondary]: https://www.tradicted.com/research/barber-learning-2020/
- **Caveat:** these samples are futures and equities day traders, not slower strategies.

**Publication decay**
- McLean & Pontiff: the average published anomaly's return is 26% lower out of sample and 58% lower after publication. Assume any "documented edge" is already weaker. https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2156623 (JSTOR copy: https://www.jstor.org/stable/pdf/43869094.pdf)

**Transaction costs**
- Novy-Marx & Velikov: costs often exceed half the gross spread for mid-turnover anomalies.
  - Only the net-issuance, earnings-momentum and momentum-family strategies keep statistically significant net returns.
  - Strategies with more than about 50% monthly turnover rarely survive costs.
  - https://www.nber.org/system/files/working_papers/w20721/w20721.pdf

---

## CRYPTO (spot + perps)

**1. Edges**
- **Perp/spot funding-rate carry (delta-neutral).**
  - He, Manela, Ross & von Wachter ("Fundamentals of Perpetual Futures", arXiv 2212.06888v6) report a BTC Sharpe of about 1.8 under retail-level Binance costs, and up to 3.5 for market makers. https://arxiv.org/abs/2212.06888v6
  - Their sample is early. Yield has since compressed [secondary]:
    - Annualized BTC funding was about 22% in 2021, about 13% in 2024, and about 6.2% in 2025.
    - It was about 2.7–3% in 2026 through Nov 2, before fees.
    - Sources: https://axeladlerjr.com/bitcoin-cash-and-carry-strategy/ and https://fluxy.io/blog/perp-funding-almanac-2020-2026.
    - These two sources use different averaging, so they are not identical.
  - **Realistic net expectancy:** after fees and the capital and basis risk of two legs, roughly 0–4% per year at 2026 funding.
  - The strategy needs margin on a derivatives venue and is hard for US residents. On a $2,000 account that is about $0–80 per year.
- **Time-series momentum on weekly horizons.**
  - Liu & Tsyvinski, "Risks and Returns of Cryptocurrency" (NBER w24877): significant 1–4 week momentum.
  - A separate paper finds the top tercile returning about 8% per week versus about 1% for the bottom tercile, with an out-of-sample check (JSTOR 48616705).
  - Caveats: the samples are early (2011–2018 era) and gross of costs. Post-publication decay applies.
  - https://www.nber.org/system/files/working_papers//w24877/w24877.pdf
  - Treat this as a hypothesis to test rather than a proven net edge. I found no net-of-cost, post-2020 out-of-sample validation.

**2. Why retail fails**
- BIS Bulletin 69: a majority of crypto-app users in nearly all economies lost money on bitcoin holdings (Aug 2015–Dec 2022). The median user lost about $431 of $900 invested. https://www.bis.org/publications/bulletin-69-crypto-shocks-and-retail-losses.pdf
- Costs [secondary, and the two sources conflict on tiers]:
  - Coinbase Advanced entry tier is about 0.50–0.60% maker and 0.90–1.20% taker. Kraken Pro is about 0.40/0.80%. Binance.US is 0%/0.02%.
  - Sources: https://coinlaw.io/crypto-exchange-fees/ and https://www.altrady.com/blog/crypto-trading-platforms/crypto-exchange-comparison.
- At 0.9% per side, a round trip costs about 1.8% for takers. That is hundreds of times higher than ETF costs and fatal for short-term trading unless you use limit orders or low-fee venues.

**3. Access**
- There is no PDT rule on crypto spot.
- Fractional sizing is available (a $2,000 account can hold 4–5 positions).
- It trades 24/7.
- US residents face limits on offshore perps. Offshore exchanges Binance, Bybit, Bitget, KuCoin and Gate do not serve US residents [secondary, same Altrady source].

## EQUITY (US stocks)

**1. Edges**
- **Momentum (12-1 month, low-turnover implementation).** Novy-Marx & Velikov (above) show it is one of the few anomalies significant after costs.
- **Post-earnings announcement drift (PEAD).** Weak or dead for tradeable stocks.
  - Martineau, "Rest in Peace PEAD": for all-but-microcap stocks it has been non-existent since 2006, and since 2016 for microcaps. https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3111607
  - Novy-Marx & Velikov still list earnings momentum as net-significant, but that uses older data. Do not rely on PEAD.
- **Realistic expectancy:** a net equity-factor edge, if any, is a few percent per year with large drawdowns. On $2,000 that is not meaningful in dollars.

**2. Failure**
- The Taiwan and Brazil studies above.
- Barber & Odean household studies: retail trading underperforms after costs. I did not re-fetch these in this session.

**3. Access**
- **PDT:** FINRA Regulatory Notice 26-10 (April 20, 2026) replaces the day-trading margin rules entirely, including PDT and the $25,000 minimum.
  - Effective June 4, 2026. Brokers may phase it in until October 20, 2027.
  - The new rule requires margin proportional to intraday exposure. The usual maintenance requirements remain.
  - **Action:** confirm with your broker that it has actually implemented the new rule. Some may still enforce the old rule during phase-in.
  - Source: https://www.finra.org/rules-guidance/notices/26-10
- Commissions are $0 at most brokers, and fractional shares are available.

## ETF (tactical asset allocation / momentum)

**1. Edges**
- **Faber-style 10-month moving-average timing across a few asset classes.**
  - Illustrative replication on liquid US ETFs: Sharpe 0.66 versus 0.36 for buy-and-hold, about half the volatility, and max drawdown −12.7% versus −47.5%. CAGR was roughly the same (~4%) in that window.
  - https://github.com/bfl-almeida/etf-gtaa
  - A second blog gives GTAA Sharpe 0.85 versus 0.67 for 60/40 (https://quantengines.com/blog/tactical-asset-allocation). Both are secondary, window-dependent and not independent.
  - Faber's original paper (2007) is the primary source. I did not fetch it.
- **Dual momentum (Antonacci).** The replication above found it underperformed buy-and-hold with a −31% drawdown on a 5-asset universe. Treat it as unproven, not proven.
- **Underlying evidence:** Hurst, Ooi & Pedersen, "A Century of Evidence on Trend-Following": time-series momentum delivered positive returns in each decade since 1880. It is net of costs but gross of fees, with average Sharpe about 0.4 per market. https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2993026
- **Realistic net expectancy:** roughly buy-and-hold returns with materially lower drawdowns, Sharpe about 0.5–0.8, with high dispersion across windows. For $2,000 that is roughly $100–200 per year in return, with the value being drawdown control.

**2. Failure**
- Trend rules whipsaw in range-bound years, and a short window can mislead. The GitHub replication above had a hit ratio of only 61–64% even in its favorable result.
- The main retail failure is turnover, which the monthly schedule avoids.

**3. Access**
- ETFs trade commission-free at most brokers with fractional shares. There is no minimum beyond the broker's. This is the least constrained class.

## FOREX

**1. Edges**
- **Carry:** Burnside, Eichenbaum & Rebelo and Lustig-Roussanov-Verdelhan document positive average returns with crash risk. https://www.nber.org/papers/w16942
- **Currency momentum:** Menkhoff, Sarno, Schmeling & Schrimpf, up to about 10% per year, but it concentrates in hard-to-trade, high-cost currencies. They test costs at 50–75% of quoted spreads (BIS WP 366). https://www.bis.org/publications/working-paper-366-currency-momentum-strategies.pdf
  - Open items: I did not confirm net-of-cost numbers and did not find evidence retail can capture this.
- **Realistic net expectancy for $2,000:** near zero to low single digits. Carry means holding positions for months, which does not fit a days-to-weeks horizon.

**2. Failure**
- ESMA (2018): 74–89% of retail CFD accounts lose money (France more than 89%, Ireland 74%), with average losses of €1,600–29,000 per client. Leverage caps were set at 30:1 for major pairs. https://www.tradicted.com/research/esma-cfd-2018/ [secondary, quoting the ESMA decision]
- US forex dealer quarterly disclosures show roughly 27–41% of accounts profitable [secondary]. https://ftmarketwatch.com/research/retail-forex-trader-profitability-nfa-disclosures.html
- These are account-level figures at broker snapshots, not day-trader-only.
- The mechanism is spread and leverage with no fundamental edge on the retail side.

**3. Access**
- US retail forex goes through NFA-regulated dealers with a leverage limit of 50:1 on majors. I did not verify this in this session.
- There is no PDT rule. Position sizes are fine-grained.

## COMMODITY

**1. Edges**
- **Roll-yield / term-structure carry and momentum.** Erb & Harvey: the average individual commodity future earns about zero excess return, but rebalanced portfolios and roll-yield- and momentum-sorted portfolios can earn equity-like returns. https://ideas.repec.org/a/taf/ufajxx/v62y2006i2p69-97.html
- **Time-series momentum:** Moskowitz, Ooi & Pedersen (24 commodity futures, 1965–2009). https://www.sciencedirect.com/science/article/pii/S0304405X11002613
- **Realistic net expectancy for $2,000:** can't be done well. Futures need margin and contract sizes are large relative to $2,000. Commodity ETFs hold front-month futures, so roll costs and contango are a drag. Gold/silver physical-backed ETFs avoid roll but only offer directional exposure. I did not find a direct retail-return study in this session.

**2. Failure**
- Single-commodity retail products have contango drag. I did not verify USO/UNG figures.

**3. Access**
- Micro contracts exist for some commodities (micro gold and crude), but margin and tick risk are large for $2,000.
- Commodity ETFs trade with no minimum.

## BOND

**1. Edges**
- **Trend / duration timing.** A 12-month rule holding 10-year Treasuries only while they beat T-bills earned 6.4% versus 5.7% for buy-and-hold since 1963, cutting the worst loss from −26% to −10%. [secondary, backtest, not an academic study; the rule sat out 2022 entirely.] https://bondfish.com/readings/trend-following-in-bonds
- It beat T-bills only in some regimes (2021–26: buy-and-hold lost 2.5% per year, trend made 0.8%, and T-bills returned about 3.4%).
- Academic support: Hurst-Ooi-Pedersen and Moskowitz-Ooi-Pedersen include bond futures.
- **Realistic net expectancy:** a few percent per year. The real alternative is cash/T-bills at roughly 3.4–3.9% [same secondary source].

**2. Failure**
- Duration risk is large. The 20+ year Treasury ETF (TLT) has a 15.1-year duration and moved about ±5% in three weeks in the Oct 2026 swing [secondary]. https://10xinsights.com/articles/duration-in-practice-bond-etfs-rate-swing-2026-10
- Trend rules whipsaw around turning points.
- Short-horizon bond trading has little retail edge: bond ETFs are efficient and the edge is slow.

**3. Access**
- Bond ETFs are commission-free with fractional shares. Treasury bills can be bought through a broker.

## FUTURES

**1. Edges**
- **Time-series momentum / trend-following across many futures** is the documented edge (Hurst-Ooi-Pedersen, Moskowitz-Ooi-Pedersen). It works through diversification across dozens of markets.
- A $2,000 account cannot diversify across a futures universe. Realistic net expectancy for $2,000: not reachable.

**2. Failure**
- The Brazil study is futures day trading: 97% of persistent traders lost.

**3. Access**
- Micro E-mini S&P (MES) intraday margin starts around $144 at TradeStation, with overnight margin around $2,300–2,900 depending on broker [secondary]. https://emini-watch.com/futures-trading/futures-margin-requirements/
- One overnight MES position would use more than the entire $2,000 account. Intraday-only trading is possible but is the exact activity the Brazil study shows failing.
- There is no PDT rule on futures, and leverage is high. That makes ruin risk high rather than the edge better.

## PREDICTION MARKETS (Polymarket / Kalshi)

**1. Edges**
- **Maker-side / favorite-longshot structure.**
  - Kalshi study ("Makers and Takers", 300,000+ contracts): prices are informative, but low-price contracts win far less often than needed to break even after fees, while high-price contracts yield small positive returns. Makers earn more than takers. https://ideas.repec.org/p/gwc/wpaper/2026-001.html and https://www.econstor.eu/handle/10419/338324
  - An independent GitHub dataset analysis [secondary, unreviewed] found a mean-reversion signal with gross Sharpe of about +14 (very likely overstated) that was profitable at maker fees (1.75% fee rate) and unprofitable at taker fees (7%). Break-even was about 3.2%. https://github.com/aorlovvvv/poly_kalshi_dataset/blob/main/PROJECT_SUMMARY.md
- **Realistic expectancy:** small, and available mostly to limit-order makers and favorites near 90%+, where payoffs are small and tail loss is large.

**2. Failure** [secondary: WSJ analysis via predictionmarkets.us]
- 67–70%+ of Polymarket users lost money overall, and the top 0.1% of accounts took 67% of profits.
- 63% of retail trades were placed at extreme longshot prices.
- Moving from pure taker to pure maker reduced the probability of losing money by 9.3 percentage points.
- https://predictionmarkets.us/articles/prediction-market-retail-traders-losing-money-2026
- Fees: the Kalshi taker fee is 0.07 × contracts × P × (1−P), peaking at $1.75 per 100 contracts at 50¢, so a taker round trip is about 7% of the $50 stake. Makers pay 0.0175 × C × P × (1−P). https://kalshi.health/learn/kalshi-fees-explained and https://realize.tax/kalshi/fees
- Polymarket taker fees depend on market category; makers are not charged (same kalshi.health page).

**3. Access**
- No minimum, so $2,000 is workable. Kalshi is a US-licensed venue. Polymarket's international product is not generally available to US users (not verified in this session).
- No PDT or margin issues. Contracts settle on events and have resolution-rule risk.

---

## Which ONE class for $2,000?

**ETF tactical/trend allocation**, with one honest caveat about horizon.

- **Cost:** it has the lowest cost structure. Commission-free trading, monthly turnover (Novy-Marx & Velikov: strategies below ~50% monthly turnover keep their edge), and fractional sizing.
- **Evidence:** it has the deepest evidence base. Over 100 years of trend evidence (Hurst et al.) and the drawdown-reduction pattern are consistent across several sources. Expect Sharpe of about 0.5–0.8, not alpha.
- **PDT:** removed for equities from June 4, 2026, so it is no longer a differentiator for crypto.
- **Where crypto wins and loses:** crypto spot is the only class with documented 1–4 week momentum at your horizon, with 24/7 trading, no PDT and fine position sizing. But the evidence is gross and early-sample, round-trip costs are 0.8–1.8% at US retail tiers, and funding carry has compressed to about 2–6%.
- **Dollar caveat:** at $2,000, even a good net edge is roughly $100–200 per year, so the main benefit is learning and capital preservation, not income.

My ranking for days-to-weeks horizons, best to worst risk-adjusted: ETF (slow, monthly) > crypto spot momentum (experimental, maker orders only) > prediction-market makers > everything else. FX, futures and commodity day trading are the worst.

---

## Live paper-trading and forward-testing best practices

**Pre-registration and multiple testing**
- Pre-register the hypothesis, signal, universe, costs and stop rules before trading. This guards against the multiple-testing problem.
- Harvey, Liu & Zhu argue the conventional t > 2 is too low and recommend t > 3.0 (RFS 2016). Source [secondary summaries]: https://aitradingbook.com/backtest-overfitting.html and https://overfitcheck.com/docs/research
- Bailey & López de Prado: the Deflated Sharpe Ratio adjusts a Sharpe ratio for the number of trials, track-record length, and skew/kurtosis. Their Minimum Backtest Length formula gives the observations needed before a given Sharpe means anything. Same secondary sources.

**Minimum sample before scaling** (my own arithmetic)
- With a target t = 3 and t ≈ SR × √years, years needed = (3/SR)². A Sharpe of 0.5 needs about 36 years, a Sharpe of 1 needs about 9, and a Sharpe of 2 needs about 2.3. A few months of live data cannot confirm a modest edge.
- For win rates, 100 independent trades gives a standard error of about 5 percentage points.
- So forward-test to detect execution problems (slippage, fills, fee drag, rule drift against the pre-registered spec). Do not treat it as validating alpha.
- Scale in stages with predefined risk limits: paper, then a small live position (tens of dollars), then more.

**Walk-forward and validation**
- Fix parameters on one window, test on the next unseen window, roll forward, and never re-tune on the test data.
- López de Prado advocates purged and embargoed cross-validation for financial data. I did not fetch his book. Check it directly.
- Account for McLean-Pontiff decay by haircutting any backtested edge by 26–58%.

**How prop firms evaluate** (a good template for self-discipline)
- Evaluations use a profit target, a max drawdown limit (static or trailing), a daily loss limit, and a consistency rule that caps any single day's share of profit (e.g. 40%). https://prop.ninjatrader.com/blogs/prop-firm-evaluation/ and https://velotrade.com/reports/prop-firm-transparency [secondary]
- Pass rates are low: published figures run 5–14%, and about 7% of buyers ever reach a payout, in one 300,000-account data set [secondary]. https://chartwhisperer.ca/prop-firm-statistics
- Borrow the drawdown limit, daily loss limit and consistency rule for your own paper test. Beware that evaluation structures reward lucky streaks.

---

## Gaps and uncertainties

- **Primary sources not fetched:** Faber (2007), Antonacci, Barber & Odean household studies, López de Prado's book, and the Harvey-Liu-Zhu and Bailey-López de Prado papers. These are cited through secondary summaries, which may contain errors.
- **Weakly sourced items:** the FX Sharpe/net-return numbers, commodity ETF contango costs, and the NFA leverage limit are unverified or inferred.
- **Quality of 2026 data:** several statistics come from secondary aggregators (funding rates, prop-firm pass rates, fee tables, forex loss tables) whose methodology I did not verify. Prop-firm rates in particular are marketing-adjacent.
- **Source conflicts:** Coinbase fee tiers conflict between sources (0.60/1.20% versus 0.50/0.90%).
- **Not found:** a net-of-cost, post-2020 out-of-sample study of crypto spot momentum. My claim that it is early-sample and gross is based on the abstracts and snippets I read.
- **PDT:** the FINRA rule is effective June 4, 2026, but broker implementation may lag until October 2027, so check your broker.