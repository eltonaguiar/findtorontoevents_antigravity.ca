# ETF research P2 — CANDIDATES swarm briefing

You are one of 3 AI engines running P2 of the ETF research pipeline. P1 produced 20 raw citations; 6 passed HEAD-check verification and are included verbatim below.

Engine vote weights from P1: deepseek 0.0x, xai 0.0x.

## P1 verified citations (6)

```json
{
  "citations": [
    {
      "url": "https://www.aqr.com/Insights/Research/Journal-Article/Carry-Strategies-in-ETF-Markets",
      "title": "Carry Strategies in ETF Markets",
      "author": "Koijen, R.S.J., Moskowitz, T.J., Pedersen, L.H., Vrugt, E.B.",
      "year": "2018",
      "claim": "A carry factor constructed from sector ETFs (using dividend yield and futures basis) delivers a Sharpe ratio of 0.65 from 2010-2017, with low correlation to momentum and value factors.",
      "evidence_strength": "empirical"
    },
    {
      "url": "https://www.federalreserve.gov/econres/feds/files/2018050pap.pdf",
      "title": "ETF Arbitrage and Liquidity Provision: A Cross-Sectional Study",
      "author": "Ben-David, I., Franzoni, F., Moussawi, R.",
      "year": "2018",
      "claim": "ETF arbitrage strategies exploiting deviations between ETF prices and NAVs generate Sharpe ratios of 0.7-1.0 for sector ETFs (2010-2016), with strongest signals in XLF and XLE during high-volatility periods.",
      "evidence_strength": "empirical"
    },
    {
      "url": "https://www.bis.org/publ/work845.pdf",
      "title": "Cross-Asset Momentum in ETF Markets: Global Evidence",
      "author": "Bekaert, G., Harvey, C.R., Kiguel, A., Wang, X.",
      "year": "2020",
      "claim": "Cross-asset momentum strategies using sector ETFs and international equity ETFs generate Sharpe ratios of 0.6-0.8 from 2010-2019, with significant diversification benefits across asset classes.",
      "evidence_strength": "empirical"
    },
    {
      "url": "https://www.aqr.com/Insights/Research/Journal-Article/Value-and-Momentum-Everywhere",
      "title": "Value and Momentum Everywhere",
      "author": "Asness, Clifford S. et al.",
      "year": "2013",
      "claim": "This study explores value and momentum strategies across multiple asset classes, including ETFs representing equity sectors. The authors demonstrate that combining value and momentum in ETF portfolios yields significant risk-adjusted returns, with backtests from 2010 showing consistent outperformance over buy-and-hold strategies.",
      "evidence_strength": "empirical"
    },
    {
      "url": "https://www.aqr.com/Insights/Research/White-Paper/Carry",
      "title": "Carry",
      "author": "Koijen, Ralph S.J. et al.",
      "year": "2018",
      "claim": "This paper explores carry strategies across asset classes, including ETFs tied to equity sectors. The authors find that carry, defined as expected return from holding an asset, can be harvested in ETFs with high dividend yields or roll yields, with backtests post-2010 showing consistent profitability.",
      "evidence_strength": "empirical"
    },
    {
      "url": "https://arxiv.org/abs/1805.07134",
      "title": "Momentum and Mean-Reversion in Strategic Asset Allocation with ETFs",
      "author": "Wang, Peng and Yang, Jun",
      "year": "2018",
      "claim": "This study combines momentum and mean-reversion signals for ETF portfolio allocation, testing on sector ETFs from 2010-2017. Results indicate that hybrid strategies outperform single-style approaches, balancing short-term trends with long-term reversals for better risk-adjusted returns.",
      "evidence_strength": "empirical"
    }
  ]
}
```

## Your mandate

Propose at least 5 backtestable ETF strategy specs. Each spec must:

1. Reference ≥1 verified citation (by URL) above. No citing P1 hallucinated URLs.
2. Trade ETF instruments only (we backtest on yfinance daily bars):
   allowed universe = `['XLK', 'XLF', 'XLE', 'XLV', 'XLI', 'XLY', 'XLP', 'XLU', 'XLB', 'XLRE', 'XLC']`. Single-symbol picks OK, multi-leg pairs
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
  "asset_class": "ETF",
  "candidates": [
    {
      "spec_id": "etf_<slug>_v1",
      "asset_class": "ETF",
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
