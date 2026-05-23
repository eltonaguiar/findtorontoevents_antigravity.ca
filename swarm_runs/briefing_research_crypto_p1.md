# CRYPTO research P1 — LITERATURE swarm briefing

You are one of 3 AI engines running P1 of the CRYPTO research pipeline.

## Current state
CRYPTO currently PF 1.25 / WR 44.6% / n=8067 (sub-T2). Quan_engine drag (PF 0.66, 21% vol).

## Universe constraint
We trade ETF-style instruments via yfinance: `['BTC-USD', 'ETH-USD', 'SOL-USD', 'BNB-USD', 'XRP-USD']`. No single-ticker exotic strategies needing futures contracts, swaps, or OTC instruments.

## Your mandate
Return ≥10 citations on CRYPTO trading strategies that:
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
  "asset_class": "CRYPTO",
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
