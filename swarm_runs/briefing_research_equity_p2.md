# EQUITY research P2 — CANDIDATES swarm briefing

You are one of 3 AI engines running P2 of the EQUITY research pipeline. P1 produced 30 raw citations; 14 passed HEAD-check verification and are included verbatim below.

Engine vote weights from P1: cerebras 1.0x, deepseek 0.0x, xai 0.0x.

## P1 verified citations (14)

```json
{
  "citations": [
    {
      "url": "https://doi.org/10.1016/j.jfineco.2012.06.001",
      "title": "Time Series Momentum",
      "author": "Tobias J. Moskowitz, Yao Hua Ooi, Lasse H. Pedersen",
      "year": "2012",
      "claim": "A simple time-series momentum strategy that buys (sells) assets with positive (negative) past 12-month returns generates annualized Sharpe ratios of 0.55-0.70 across major equity markets, including US large-cap stocks and ETFs such as SPY and QQQ, after accounting for transaction costs.",
      "evidence_strength": "peer-reviewed|empirical"
    },
    {
      "url": "https://doi.org/10.1016/j.jfineco.2017.02.001",
      "title": "Volatility-Managed Portfolios",
      "author": "Pedro G. Moreira, Bryan T. Muir",
      "year": "2017",
      "claim": "Scaling equity exposure inversely to recent realized volatility (vol-targeting) delivers a 1.2% higher annualized return and a Sharpe ratio improvement of 0.15 relative to a static 100% equity allocation, demonstrated on SPY and QQQ from 2000-2016.",
      "evidence_strength": "peer-reviewed|empirical"
    },
    {
      "url": "https://doi.org/10.1016/j.jfineco.2015.02.004",
      "title": "Regime-Switching and Momentum",
      "author": "Pedro Barroso, Pedro Santa-Clara",
      "year": "2015",
      "claim": "A regime-conditional momentum strategy that switches off during low-volatility regimes and stays on during high-volatility regimes generates an annualized Sharpe ratio of 0.68 on US equity ETFs, outperforming unconditional momentum by 30% in risk-adjusted terms.",
      "evidence_strength": "peer-reviewed|empirical"
    },
    {
      "url": "https://doi.org/10.1016/j.jfineco.2013.04.001",
      "title": "Equity Carry: A New Factor?",
      "author": "Robert Novy-Marx",
      "year": "2013",
      "claim": "Constructing a carry portfolio that goes long high-dividend-yield stocks and short low-yield stocks yields an average annual excess return of 3.8% with a Sharpe ratio of 0.62 when applied to broad-market ETFs (SPY, VTI) over 1990-2012, supporting carry as a distinct equity factor.",
      "evidence_strength": "peer-reviewed|empirical"
    },
    {
      "url": "https://arxiv.org/abs/1502.03044",
      "title": "Statistical Arbitrage Strategies and the Cross-Section of Stock Returns",
      "author": "Marco Avellaneda, Jeong-Hoon Lee",
      "year": "2015",
      "claim": "A mean-reversion statistical-arbitrage strategy based on pairwise cointegration of US equities delivers a mean annualized return of 4.1% and a Sharpe ratio of 0.58 after transaction costs, using daily data on constituents of the S&P 500 (proxied by SPY).",
      "evidence_strength": "peer-reviewed|empirical"
    },
    {
      "url": "https://doi.org/10.1016/j.jfineco.2020.09.001",
      "title": "Machine Learning for Regime Detection in Equity Markets",
      "author": "Jiang Gu, Andrew W. Kelly, Lasse Heje Pedersen",
      "year": "2020",
      "claim": "A hidden-Markov-model classifier identifies bull and bear regimes with 85% accuracy; conditioning a momentum strategy on the identified bull regime improves its Sharpe ratio from 0.55 to 0.73 on SPY and QQQ (2005-2019).",
      "evidence_strength": "peer-reviewed|empirical"
    },
    {
      "url": "https://doi.org/10.1016/j.jfineco.2016.02.001",
      "title": "Quantitative Equity Strategies: A Review",
      "author": "Catherine M. Harvey, Yan Liu, Yan Zhu",
      "year": "2016",
      "claim": "A survey of 30 quantitative equity strategies (including value, momentum, and volatility-targeting) shows that diversified multi-factor portfolios of US ETFs achieve an average annualized Sharpe ratio of 0.71, with the highest performance coming from portfolios that combine value and momentum.",
      "evidence_strength": "peer-reviewed|empirical"
    },
    {
      "url": "https://www.aqr.com/Insights/Research/Quantitative-Equity-Market-Timing",
      "title": "Quantitative Equity Market Timing",
      "author": "AQR Capital Management",
      "year": "2018",
      "claim": "An equity market-timing model that adjusts exposure based on a composite signal of valuation, momentum, and volatility achieves a 1.1% higher annualized return and a Sharpe ratio improvement of 0.12 versus a static 100% equity allocation, using SPY and VTI backtested from 1995-2017.",
      "evidence_strength": "empirical"
    },
    {
      "url": "https://www.nber.org/papers/w16865",
      "title": "Betting Against Beta",
      "author": "Frazzini, A., Pedersen, L.H.",
      "year": "2014",
      "claim": "A betting-against-beta (BAB) strategy that is long low-beta stocks and short high-beta stocks yields significant risk-adjusted returns of 0.7-1.0% per month in US equities (1962-2012), with higher Sharpe ratios than the market.",
      "evidence_strength": "peer-reviewed"
    },
    {
      "url": "https://www.bis.org/publ/work790.pdf",
      "title": "Equity Momentum and Reversals: A Global Perspective",
      "author": "Bali, T.G., Brown, S.J., Cakici, N.",
      "year": "2019",
      "claim": "Short-term reversal (1-month) and medium-term momentum (12-month) strategies in global equity ETFs (including US) generate significant alphas of 0.5-1.0% per month, with reversal stronger in small-cap (IWM) and momentum in large-cap (SPY).",
      "evidence_strength": "empirical"
    },
    {
      "url": "https://www.dx.doi.org/10.1016/j.jfineco.2021.05.001",
      "title": "Factor Investing in the ETF Era",
      "author": "Bhootra, A., Hur, J.",
      "year": "2021",
      "claim": "Factor-based ETF strategies (value, momentum, low-vol) on US equity ETFs (SPY, IWM, QQQ) yield net Sharpe ratios of 0.4-0.7 after fees (2005-2020), with momentum and low-vol factors most robust.",
      "evidence_strength": "peer-reviewed"
    },
    {
      "url": "https://arxiv.org/abs/1803.07977",
      "title": "Mean Reversion in Stock Prices: Evidence and Implications",
      "author": "James M. Poterba, Lawrence H. Summers",
      "year": "2018",
      "claim": "This paper revisits mean reversion in equity markets, using post-2010 data to demonstrate that stock prices exhibit significant mean-reverting behavior over medium-term horizons. Backtests on broad indices like SPY and VTI show that mean reversion strategies can generate alpha, particularly in low-volatility regimes, though transaction costs erode returns.",
      "evidence_strength": "empirical"
    },
    {
      "url": "https://www.aqr.com/Insights/Research/Journal-Article/Volatility-Targeting-for-Equities",
      "title": "Volatility Targeting for Equities",
      "author": "Brian Hurst, Yao Hua Ooi, Lasse Heje Pedersen",
      "year": "2014",
      "claim": "This paper explores volatility-targeting strategies in equity markets, showing through backtests from 2010 onwards that dynamically adjusting exposure based on realized volatility improves risk-adjusted returns for ETFs like SPY and VOO. The strategy reduces drawdowns during high-volatility periods while maintaining upside participation.",
      "evidence_strength": "empirical"
    },
    {
      "url": "https://www.aqr.com/Insights/Research/White-Paper/Value-Investing-in-Equities",
      "title": "Value Investing in Equities",
      "author": "Clifford S. Asness, John M. Liew",
      "year": "2013",
      "claim": "This white paper analyzes value strategies in equity markets, with backtests from 2010 onwards showing that value factors applied to broad indices like SPY and VTI can outperform growth-oriented strategies over long horizons, though performance varies with market cycles and interest rate environments.",
      "evidence_strength": "empirical"
    }
  ]
}
```

## Your mandate

Propose at least 5 backtestable EQUITY strategy specs. Each spec must:

1. Reference ≥1 verified citation (by URL) above. No citing P1 hallucinated URLs.
2. Trade ETF instruments only (we backtest on yfinance daily bars):
   allowed universe = `['SPY', 'QQQ', 'IWM', 'VTI', 'VOO', 'DIA', 'MDY']`. Single-symbol picks OK, multi-leg pairs
   OK. Do not propose strategies needing futures contracts, swaps, options,
   or OTC instruments — exits scope.
3. Have a concrete entry rule, exit rule, and sizing rule expressible in pseudo-code.
4. Have a regime filter or "skip-when" condition (when NOT to fire).
5. Beat the cross-test (we compute ρ + symbol overlap vs every shipped strategy in `dashboard_data.json::systems`).

## Target outcome

Strategies that, when backtested over 2020-2025, can clear Tier-2 floors per CLAUDE.md:
  - PF ≥ 1.5
  - WR ≥ 50%
  - MDD < 20%
  - n ≥ 100 trades

If you BELIEVE the asset class has no scalable retail edge, say so — propose 1-2 "diagnostic" strategies that would CONFIRM no-edge if backtested, and explain in rationale why edge has likely decayed. NO_EDGE verdicts are first-class deliverables; don't fabricate fake edge.

## Output schema (JSON-strict, identical to BOND P2)

```json
{
  "schema_version": "v1",
  "engine": "<your name>",
  "asset_class": "EQUITY",
  "candidates": [
    {
      "spec_id": "equity_<slug>_v1",
      "asset_class": "EQUITY",
      "entry": "exact rule, e.g. 'long UUP when 60d momentum > 0 AND DXY 90d realized vol < 8%'",
      "exit": "e.g. 'exit on momentum sign flip or 30d hold'",
      "sizing": "e.g. 'risk-parity to 8% annualized vol'",
      "universe": ["UUP", "FXE", ...],
      "regime_filter": "e.g. 'skip when VIX > 30 or DXY rolling vol > 12%'",
      "source_refs": ["https://verified-url-1"],
      "proposed_by_engine": "<your name>",
      "expected_pf": 1.5,
      "expected_wr": 51.0,
      "expected_mdd_pct": 15.0,
      "expected_n_per_year": 10,
      "rationale": "1-2 sentences why this should clear T2 floors OR why it might NOT (diagnostic)"
    }
  ],
  "notes_to_p3": "1-paragraph hint for the backtest pass"
}
```

Return ONLY the JSON object. No prose preamble, no markdown fence.
