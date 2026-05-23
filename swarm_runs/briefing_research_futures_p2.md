# FUTURES research P2 — CANDIDATES swarm briefing

You are one of 3 AI engines running P2 of the FUTURES research pipeline. P1 produced 20 raw citations; 8 passed HEAD-check verification and are included verbatim below.

Engine vote weights from P1: deepseek 0.0x, xai 0.5x.

## P1 verified citations (8)

```json
{
  "citations": [
    {
      "url": "https://www.bis.org/publ/work790.pdf",
      "title": "Carry Trade and Momentum in Currency and Commodity Markets",
      "author": "Menkhoff, L., Sarno, L., Schmeling, M., Schrimpf, A.",
      "year": "2019",
      "claim": "Carry and momentum strategies in commodity futures (using DBC-like baskets) generate significant excess returns from 1985-2015; carry is positively correlated with volatility and negatively with liquidity, while momentum is driven by past returns.",
      "evidence_strength": "peer-reviewed"
    },
    {
      "url": "https://www.federalreserve.gov/econres/feds/files/2018058pap.pdf",
      "title": "Regime-Dependent Commodity Futures Strategies",
      "author": "Bakshi, G., Gao, X., Rossi, A.",
      "year": "2018",
      "claim": "A regime-switching model (expansion vs. recession) applied to commodity futures (energy, metals, agriculture) yields higher risk-adjusted returns than static strategies; the regime-conditional momentum strategy outperforms in expansions, while carry dominates in recessions (1990-2017).",
      "evidence_strength": "empirical"
    },
    {
      "url": "https://www.nber.org/papers/w22910",
      "title": "Volatility Targeting for Commodity Futures",
      "author": "Harvey, C.R., Hoyle, E., Kormendi, R., Rattray, S., Sargaison, D., Van Hemert, O.",
      "year": "2017",
      "claim": "Volatility-targeting (constant 10% annualized volatility) applied to commodity futures momentum and carry strategies improves risk-adjusted returns by 30-50% compared to fixed-weight portfolios; backtest from 1985-2016.",
      "evidence_strength": "empirical"
    },
    {
      "url": "https://www.aqr.com/Insights/Research/Journal-Article/Commodities-for-the-Long-Run",
      "title": "Commodities for the Long Run",
      "author": "Levine, A., Ooi, Y. H., Richardson, M., & Sasseville, C.",
      "year": "2018",
      "claim": "This paper argues that commodity futures can provide long-term positive returns through a combination of carry and momentum strategies, showing that a diversified portfolio of commodity futures has delivered attractive risk-adjusted returns over multiple decades, with empirical backtests from 2010 onwards confirming the persistence of these premia.",
      "evidence_strength": "peer-reviewed"
    },
    {
      "url": "https://arxiv.org/abs/1904.04925",
      "title": "Mean Reversion in Futures Markets: Evidence and Implications",
      "author": "Bianchi, R. J., Drew, M. E., & Fan, J. H.",
      "year": "2019",
      "claim": "The paper provides evidence of mean-reverting behavior in commodity futures prices, with backtests post-2010 showing that mean reversion strategies can outperform buy-and-hold approaches, particularly in volatile markets like energy and agriculture.",
      "evidence_strength": "empirical"
    },
    {
      "url": "https://www.aqr.com/Insights/Research/White-Paper/Value-and-Momentum-Everywhere",
      "title": "Value and Momentum Everywhere",
      "author": "Asness, C. S., Moskowitz, T. J., & Pedersen, L. H.",
      "year": "2013",
      "claim": "This research highlights the presence of value and momentum premia in futures markets, including commodities, with backtests from 2010 onwards showing that combining value (cheap vs. expensive assets) and momentum (trending assets) yields superior risk-adjusted returns.",
      "evidence_strength": "peer-reviewed"
    },
    {
      "url": "https://www.aqr.com/Insights/Research/Journal-Article/Superstar-Investors",
      "title": "Superstar Investors and Commodity Strategies",
      "author": "Asness, C. S., & Liew, J. M.",
      "year": "2015",
      "claim": "This paper discusses how top investors exploit commodity futures using momentum and value strategies, with backtest results post-2010 showing that systematic approaches to these styles consistently beat benchmarks in commodity ETFs and futures.",
      "evidence_strength": "peer-reviewed"
    },
    {
      "url": "https://arxiv.org/abs/2003.05906",
      "title": "Dynamic Asset Allocation in Commodity Futures",
      "author": "Gorton, G., & Rouwenhorst, K. G.",
      "year": "2020",
      "claim": "The authors explore dynamic allocation strategies in commodity futures, incorporating momentum, carry, and volatility targeting, with post-2010 backtests demonstrating improved risk-adjusted returns through adaptive weighting of factors.",
      "evidence_strength": "empirical"
    }
  ]
}
```

## Your mandate

Propose at least 5 backtestable FUTURES strategy specs. Each spec must:

1. Reference ≥1 verified citation (by URL) above. No citing P1 hallucinated URLs.
2. Trade ETF instruments only (we backtest on yfinance daily bars):
   allowed universe = `['DBC', 'GSG', 'DBA', 'USO', 'UNG', 'PDBC']`. Single-symbol picks OK, multi-leg pairs
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
  "asset_class": "FUTURES",
  "candidates": [
    {
      "spec_id": "futures_<slug>_v1",
      "asset_class": "FUTURES",
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
