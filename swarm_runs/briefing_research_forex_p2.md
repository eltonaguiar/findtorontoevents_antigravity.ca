# FOREX research P2 — CANDIDATES swarm briefing

You are one of 3 AI engines running P2 of the FOREX research pipeline. P1 produced 20 raw citations; 8 passed HEAD-check verification and are included verbatim below.

Engine vote weights from P1: deepseek 0.0x, xai 0.0x.

## P1 verified citations (8)

```json
{
  "citations": [
    {
      "url": "https://www.bis.org/publ/qtrpdf/r_qt1809e.htm",
      "title": "The dollar, bank leverage and the deviation from covered interest parity",
      "author": "Borio, C., McCauley, R., McGuire, P., Sushko, V.",
      "year": "2018",
      "claim": "Post-2014, deviations from covered interest parity (CIP) became persistent and large, creating a new source of carry-like returns for those able to trade FX swaps and cross-currency basis - but this is largely inaccessible to retail ETF traders due to institutional constraints.",
      "evidence_strength": "empirical"
    },
    {
      "url": "https://www.aqr.com/Insights/Research/Journal-Article/A-Century-of-Evidence-on-Trend-Following",
      "title": "A Century of Evidence on Trend-Following",
      "author": "Hurst, B., Ooi, Y.H., Pedersen, L.H.",
      "year": "2017",
      "claim": "Time-series momentum (trend-following) in FX futures delivered positive returns across decades including 2010-2016, with Sharpe ratios of 0.5-0.8 after costs, and performed well during the 2014-2015 USD rally - unlike carry which collapsed.",
      "evidence_strength": "peer-reviewed"
    },
    {
      "url": "https://www.aqr.com/Insights/Research/Journal-Article/Value-and-Momentum-Everywhere",
      "title": "Value and Momentum Everywhere",
      "author": "Asness, C.S., Moskowitz, T.J., Pedersen, L.H.",
      "year": "2013",
      "claim": "Combined value+momentum strategies in FX delivered Sharpe 0.70 in 1990-2011, with the combination surviving the 2008-2009 crisis. Post-2010, the value leg became more important as momentum weakened in some currency pairs.",
      "evidence_strength": "peer-reviewed"
    },
    {
      "url": "https://www.bis.org/publ/work790.pdf",
      "title": "The dollar and the carry trade: a new perspective",
      "author": "Lustig, H., Roussanov, N., Verdelhan, A.",
      "year": "2019",
      "claim": "Post-2015, the traditional carry trade (long high-yield, short low-yield) has near-zero Sharpe, but a 'dollar carry' strategy that goes long USD when US real rates rise relative to rest-of-world had Sharpe 0.50 in 2015-2019.",
      "evidence_strength": "empirical"
    },
    {
      "url": "https://www.bis.org/publ/qtrpdf/r_qt1709e.pdf",
      "title": "Currency Carry Trades and Risk Premia in the Post-Crisis Era",
      "author": "Bank for International Settlements",
      "year": "2017",
      "claim": "Post-2015 carry trade collapse is attributed to central bank interventions and compressed yield differentials, but emerging market currencies still offer selective carry opportunities with Sharpe ratios of 0.4 when hedged against crash risk.",
      "evidence_strength": "empirical"
    },
    {
      "url": "https://www.ecb.europa.eu/pub/pdf/scpwps/ecb.wp2219.en.pdf",
      "title": "Regime-Conditional Currency Strategies in a Low-Yield World",
      "author": "Della Corte, Pasquale; Riddiough, Steven J.; Sarno, Lucio",
      "year": "2018",
      "claim": "Regime-conditional strategies that adapt to macroeconomic regimes (e.g., inflation expectations, yield curve slope) can improve currency portfolio returns, achieving Sharpe ratios of 0.5+ in 2010-2017 by dynamically weighting carry and momentum signals.",
      "evidence_strength": "peer-reviewed"
    },
    {
      "url": "https://www.federalreserve.gov/econres/feds/files/2017035pap.pdf",
      "title": "Currency Risk Premia and Macroeconomic Fundamentals Post-QE",
      "author": "Ready, Robert; Roussanov, Nikolai; Ward, Colin",
      "year": "2017",
      "claim": "Post-QE currency risk premia are driven by macroeconomic fundamentals like inflation differentials, with carry trades underperforming post-2015 unless conditioned on macro signals, yielding Sharpe ratios of 0.35 in 2010-2016.",
      "evidence_strength": "peer-reviewed"
    },
    {
      "url": "https://www.aqr.com/Insights/Research/Journal-Article/Currency-Strategies-in-a-Low-Yield-Environment",
      "title": "Currency Strategies in a Low-Yield Environment",
      "author": "AQR Capital Management",
      "year": "2019",
      "claim": "Post-2015, combining carry, momentum, and value signals with risk parity weighting delivers consistent returns, with Sharpe ratios of 0.55 in 2010-2018, outperforming standalone strategies in a low-yield regime.",
      "evidence_strength": "empirical"
    }
  ]
}
```

## Your mandate

Propose at least 5 backtestable FOREX strategy specs. Each spec must:

1. Reference ≥1 verified citation (by URL) above. No citing P1 hallucinated URLs.
2. Trade ETF instruments only (we backtest on yfinance daily bars):
   allowed universe = `['UUP', 'FXE', 'FXY', 'FXB', 'FXA', 'FXC', 'FXF', 'UDN', 'CYB', 'INR', 'BZF']`. Single-symbol picks OK, multi-leg pairs
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
  "asset_class": "FOREX",
  "candidates": [
    {
      "spec_id": "forex_<slug>_v1",
      "asset_class": "FOREX",
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
