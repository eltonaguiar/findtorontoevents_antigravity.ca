# BOND research P2 — CANDIDATES swarm briefing

You are one of 3 AI engines running P2 of the BOND research pipeline. P1 produced 20 raw citations; 8 passed HEAD-check verification and are included verbatim below.

Engine vote weights from P1: deepseek 0.5x, inception 0.0x.

## P1 verified citations (8)

```json
{
  "citations": [
    {
      "url": "https://www.aqr.com/Insights/Research/Journal-Article/Bond-Momentum",
      "title": "Bond Momentum",
      "author": "Asness, C., Moskowitz, T., Pedersen, L.",
      "year": "2013",
      "claim": "Cross-sectional momentum in government bonds across countries generates significant excess returns with a Sharpe ratio of 0.85 for a long-short portfolio from 1972-2011, orthogonal to equity momentum and value factors.",
      "evidence_strength": "peer-reviewed"
    },
    {
      "url": "https://www.bis.org/publ/work878.pdf",
      "title": "The term premium and bond return predictability in times of crisis",
      "author": "BIS (Committee on the Global Financial System)",
      "year": "2020",
      "claim": "Term premium estimates from affine term structure models predict 1-month excess returns on 10-year US Treasuries with an out-of-sample R² of 8-12% from 1990-2019, with strongest signals during recessionary regimes.",
      "evidence_strength": "empirical"
    },
    {
      "url": "https://www.federalreserve.gov/econres/feds/files/2018057pap.pdf",
      "title": "Treasury Bond Illiquidity and the Cross-Section of Expected Returns",
      "author": "Musto, D., Nini, G., Schwarz, K.",
      "year": "2018",
      "claim": "On-the-run vs off-the-run Treasury yield spreads predict short-term bond returns; a long-short portfolio based on liquidity premia yields a Sharpe ratio of 0.65 from 1997-2016.",
      "evidence_strength": "empirical"
    },
    {
      "url": "https://www.nber.org/system/files/working_papers/w23619/w23619.pdf",
      "title": "Bond Risk Premia and the Macroeconomy",
      "author": "Ludvigson, S., Ng, S.",
      "year": "2017",
      "claim": "Macroeconomic factors (real activity, inflation, financial conditions) explain 20-30% of variation in 1-year excess bond returns from 1964-2015, with predictive power concentrated in the 2-5 year maturity segment.",
      "evidence_strength": "peer-reviewed"
    },
    {
      "url": "https://www.federalreserve.gov/econresdata/feds/2015/files/2015055pap.pdf",
      "title": "Regime-Conditional Bond Sizing: A Markov-Switching Approach",
      "author": "Ang, A., Bekaert, G., Wei, M.",
      "year": "2015",
      "claim": "A two-regime Markov-switching model (low/high volatility) for US Treasuries generates a Sharpe ratio of 0.90 from 1985-2014 by dynamically adjusting duration exposure, with 70% of months in low-vol regime.",
      "evidence_strength": "empirical"
    },
    {
      "url": "https://www.nber.org/papers/w18893",
      "title": "The Term Premium and the Yield Curve: Evidence from the US Treasury Market",
      "author": "Adrian, Tobias, Richard D. Crump, and Michael R. Moench",
      "year": "2013",
      "claim": "A term-premium model based on forward rates predicts excess Treasury returns with an out-of-sample R² of 0.12 and an annualized Sharpe of 0.62 for a 10-year horizon (1990-2012).",
      "evidence_strength": "empirical"
    },
    {
      "url": "https://www.nber.org/papers/w10823",
      "title": "Regime Switching and the Predictability of Bond Returns",
      "author": "Andrew Ang and Monika Piazzesi",
      "year": "2005",
      "claim": "A two-state Markov regime model that switches between high-growth and low-growth periods improves the Sharpe of a duration-adjusted Treasury strategy from 0.62 to 0.89 (1995-2004) by allocating more weight in the high-growth regime.",
      "evidence_strength": "empirical"
    },
    {
      "url": "https://www.nber.org/papers/w7355",
      "title": "The Term Structure of Credit Spreads",
      "author": "Darrell Duffie, Satoshi Saita, and Monika Wang",
      "year": "2000",
      "claim": "A term-structure model of corporate credit spreads predicts excess returns on investment-grade bonds with an out-of-sample Sharpe of 0.65 (1992-1999) and a significant spread-term premium of 1.4% per annum.",
      "evidence_strength": "empirical"
    }
  ]
}
```

## Your mandate

Propose at least 5 backtestable BOND strategy specs. Each spec must:

1. Reference ≥1 verified citation (by URL) above. No citing P1 hallucinated URLs.
2. Trade ETF instruments only (we backtest on yfinance daily bars):
   allowed universe = `['IEF', 'TLT', 'SHY', 'IEI', 'TIP', 'LQD', 'VCIT', 'VCSH', 'HYG', 'BND', 'TIPS', 'MBB', 'AGG']`. Single-symbol picks OK, multi-leg pairs
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
  "asset_class": "BOND",
  "candidates": [
    {
      "spec_id": "bond_<slug>_v1",
      "asset_class": "BOND",
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
