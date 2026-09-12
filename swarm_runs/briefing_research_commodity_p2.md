# COMMODITY research P2 — CANDIDATES swarm briefing

You are one of 3 AI engines running P2 of the COMMODITY research pipeline. P1 produced 20 raw citations; 6 passed HEAD-check verification and are included verbatim below.

Engine vote weights from P1: deepseek 0.5x, xai 0.0x.

## P1 verified citations (6)

```json
{
  "citations": [
    {
      "url": "https://www.aqr.com/Insights/Research/Journal-Article/Time-Series-Momentum-in-Commodities",
      "title": "Time Series Momentum in Commodities",
      "author": "Miffre, J. and Rallis, G.",
      "year": "2007",
      "claim": "Time-series momentum (trend-following) generates significant excess returns in commodity futures from 1979-2004, with Sharpe ratios exceeding 0.5 across 31 commodities, robust to transaction costs.",
      "evidence_strength": "peer-reviewed"
    },
    {
      "url": "https://www.bis.org/publ/work853.pdf",
      "title": "Commodity carry and momentum: A joint analysis",
      "author": "Boons, M. and Prado, M.",
      "year": "2019",
      "claim": "Commodity carry (based on futures curve slope) generates 0.8% monthly returns from 1985-2017, orthogonal to momentum; combined carry+momentum portfolio improves Sharpe ratio by 40%.",
      "evidence_strength": "empirical"
    },
    {
      "url": "https://www.federalreserve.gov/econres/feds/files/2018075pap.pdf",
      "title": "Commodity Value Strategies",
      "author": "Bianchi, R.J., Drew, M.E., and Fan, J.H.",
      "year": "2018",
      "claim": "Commodity value (long cheap, short expensive based on 5-year price relative to moving average) yields 0.6% monthly alpha from 1980-2016, with low correlation to momentum and carry.",
      "evidence_strength": "empirical"
    },
    {
      "url": "https://www.aqr.com/Insights/Research/Journal-Article/Commodity-Momentum-A-Perspective",
      "title": "Commodity Momentum: A Perspective",
      "author": "Asness, C.S., Moskowitz, T.J., and Pedersen, L.H.",
      "year": "2013",
      "claim": "Commodity momentum (both time-series and cross-sectional) is a robust factor across 1972-2011, with average monthly return of 0.8% and Sharpe ratio 0.6, partially explained by business cycle risk.",
      "evidence_strength": "peer-reviewed"
    },
    {
      "url": "https://www.bis.org/publ/work732.pdf",
      "title": "Commodity index investing and commodity futures prices",
      "author": "Hamilton, J.D. and Wu, J.C.",
      "year": "2018",
      "claim": "Commodity index roll yield (carry) explains 40% of commodity futures returns from 2000-2016, with backwardation providing positive returns and contango negative returns.",
      "evidence_strength": "empirical"
    },
    {
      "url": "https://www.aqr.com/Insights/Research/Journal-Article/Superstar-Investors",
      "title": "Superstar Investors",
      "author": "Cliff Asness, Antti Ilmanen, Thomas Maloney",
      "year": "2017",
      "claim": "This article discusses various investment styles, including momentum and value in commodities, with backtests from 2010 to 2016. The authors highlight that commodity momentum strategies consistently outperform passive benchmarks, driven by persistent price trends in metals and energy.",
      "evidence_strength": "empirical"
    }
  ]
}
```

## Your mandate

Propose at least 5 backtestable COMMODITY strategy specs. Each spec must:

1. Reference ≥1 verified citation (by URL) above. No citing P1 hallucinated URLs.
2. Trade ETF instruments only (we backtest on yfinance daily bars):
   allowed universe = `['GLD', 'SLV', 'PPLT', 'PALL', 'CPER', 'DBA']`. Single-symbol picks OK, multi-leg pairs
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
  "asset_class": "COMMODITY",
  "candidates": [
    {
      "spec_id": "commodity_<slug>_v1",
      "asset_class": "COMMODITY",
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
