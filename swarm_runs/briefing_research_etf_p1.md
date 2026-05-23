# ETF research P1 — LITERATURE swarm briefing

You are one of 3 AI engines running P1 of the ETF research pipeline.

## Current state
ETF currently PF 1.24 / WR 55.2% / n=87 (borderline; n→100).

## Universe constraint
We trade ETF-style instruments via yfinance: `['XLK', 'XLF', 'XLE', 'XLV', 'XLI', 'XLY', 'XLP', 'XLU', 'XLB', 'XLRE', 'XLC']`. No single-ticker exotic strategies needing futures contracts, swaps, or OTC instruments.

## Your mandate
Return ≥10 citations on ETF trading strategies that:
1. Have empirical backtest results in 2010+.
2. Cover diverse styles: momentum, mean reversion, carry, value, vol-targeting, regime-conditional.
3. URLs must resolve. We HEAD-check every URL. >25% hallucination = 0.5x weight; >50% = excluded from P2.

## Trusted domains
ssrn.com, arxiv.org, papers.nber.org, sciencedirect.com, journals.aeaweb.org, federalreserve.gov, bis.org, doi.org, aqr.com, qmom.com.

## Output schema (JSON-strict)
```json
{
  "schema_version": "v1",
  "engine": "<your name>",
  "asset_class": "ETF",
  "citations": [
    {
      "url": "https://...",
      "access_date": "2026-05-11",
      "title": "...",
      "author": "...",
      "year": "2018",
      "claim": "1-paragraph extracted claim",
      "evidence_strength": "peer-reviewed|empirical|anec",
      "instruments_studied": [...],
      "key_metric": "..."
    }
  ],
  "themes_observed": ["..."],
  "notes_to_p2": "1-paragraph hint"
}
```

Do NOT invent URLs. Drop unverified citations. Return ONLY the JSON object.
