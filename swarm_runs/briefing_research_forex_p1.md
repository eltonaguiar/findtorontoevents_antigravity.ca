# FOREX research P1 — LITERATURE swarm briefing

You are one of 3 AI engines running P1 of the FOREX research pipeline at `findtorontoevents.ca/audit`.

## Current FOREX state (sub-floor, stress-test scenario)

PF 0.28, WR 45.6%, n=1249 (post-resolver-v2 7d clean recompute, 2026-05-05). Confirmed genuine sub-floor — NOT resolver noise. The existing strategy book has negative edge after costs. Mutate-before-kill per `docs/MUTATION_THREE_AXIS_PROTOCOL.md`.

Your job: dig deep into the literature. If FOREX has no scalable retail edge in 2020+, your output should help us SAY SO HONESTLY rather than chase ghosts. Equally, if there's a niche where a small operator can still extract carry / momentum / mean-reversion alpha, surface it with the strongest evidence.

## Universe constraint

We trade currency-ETF proxies (yfinance daily bars): `[UUP, FXE, FXY, FXB, FXA, FXC, FXF, UDN]` plus EM single-currency ETFs `[CYB, INR, BZF]` if liquid enough. Spot FX pairs (EURUSD, USDJPY, etc.) are out of scope for backtest harness — must use ETF proxies.

## Your mandate

Return ≥10 citations on FX strategies that:

1. Have empirical backtest results in 2010+ (post-quantitative-easing era — pre-QE results may not generalize).
2. Cover diverse styles: carry, momentum, value (real-exchange-rate), volatility-targeting, regime-conditional sizing, news/event filters.
3. Address the **post-2015 carry collapse** explicitly — strategies that worked 1990-2010 but died are well-documented; we want what survived OR new approaches.
4. URLs must resolve. We HEAD-check every URL post-swarm. >25% hallucination = 0.5x weight; >50% = excluded from P2.

## Trusted domain hints (broader scope welcome)

ssrn.com, arxiv.org, papers.nber.org, sciencedirect.com, journals.aeaweb.org, federalreserve.gov, bis.org, imf.org, ecb.europa.eu, bankofengland.co.uk, doi.org, aqr.com, qmom.com

## Output schema (JSON-strict, IDENTICAL to BOND P1)

```json
{
  "schema_version": "v1",
  "engine": "<your name>",
  "asset_class": "FOREX",
  "citations": [
    {
      "url": "https://...",
      "access_date": "2026-05-11",
      "title": "...",
      "author": "...",
      "year": "2018",
      "claim": "1-paragraph extracted claim — exact or close paraphrase, NOT a meta-summary",
      "evidence_strength": "peer-reviewed|empirical|anec",
      "instruments_studied": ["UUP", "FXE", "FXY", ...],
      "key_metric": "Sharpe 0.40 in 2010-2020 vs 0.85 in 1990-2010"
    }
  ],
  "themes_observed": [
    "1-line summary of recurring theme — esp. anything about regime sensitivity, edge decay, or surviving subsets"
  ],
  "notes_to_p2": "1-paragraph hint on which 3-5 strategies look most translatable to ETF universe AND most likely to survive cost + slippage at retail scale"
}
```

**Do NOT** invent URLs. **Do NOT** cite papers without verified URLs. If you cannot verify, drop the citation.

Return ONLY the JSON object. No prose preamble, no markdown fence.
