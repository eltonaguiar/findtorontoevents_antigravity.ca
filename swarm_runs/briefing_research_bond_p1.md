# BOND research P1 — LITERATURE swarm briefing

You are one of 3 AI engines (deepseek, cerebras, inception) running in
parallel for the BOND asset-class research pipeline at
`findtorontoevents.ca/audit`. Your output feeds a 5-pass protocol:

  P1 LITERATURE  ← (this pass) gather cited sources
  P2 CANDIDATES  — propose backtestable strategies referencing P1
  P3 BACKTEST    — orchestrator runs walk-forward via alpha_engine.backtest
  P4 CROSS-TEST  — overlap vs already-shipped strategies
  P5 SYNTHESIS   — vote go/no-go, draft wiring plan

## Current BOND state (CLAUDE.md MAJOR GOAL banner, 2026-05-11)

PF 1.72, WR 55.6%, n=18 — meets Tier-2 PF + WR thresholds but blocked by
the charter floor n≥100. We need publishable strategies that drive n into
the hundreds without burning the existing edge.

## Your mandate

Return ≥10 citations on bond-market trading strategies that:

1. Have empirical backtest results in the source (we'll cross-test, so
   don't pad with theoretical-only papers — actual numbers matter).
2. Cover diverse styles: duration carry, curve momentum, credit spread,
   TIPS breakeven, term-premium, value/momentum, vol-targeting, regime-
   conditional sizing.
3. Are REAL — URLs must resolve. We HEAD-check every URL post-swarm and
   downgrade engines >25% hallucination rate to 0.5x vote weight in P5.
4. Include `access_date` so future readers can date the lit review.

## Trusted domain hints (not enforced — broader scope welcome)

ssrn.com, arxiv.org, papers.nber.org, sciencedirect.com, jstor.org,
journals.aeaweb.org, federalreserve.gov, bis.org, imf.org, doi.org,
aqr.com, qmom.com, research-affiliates.com, fred.stlouisfed.org

## Output schema (JSON-strict)

```json
{
  "schema_version": "v1",
  "engine": "<your name>",
  "asset_class": "BOND",
  "citations": [
    {
      "url": "https://...",
      "access_date": "2026-05-11",
      "title": "...",
      "author": "...",
      "year": "2014",
      "claim": "1-paragraph extracted claim — exact or close paraphrase, NOT a meta-summary",
      "evidence_strength": "peer-reviewed|empirical|anec",
      "instruments_studied": ["IEF", "TLT", "TIP", "LQD", ...],
      "key_metric": "Sharpe 0.85 over 1995-2019 ..."
    }
  ],
  "themes_observed": [
    "1-line summary of recurring theme, e.g. 'term-premium predictability strongest in 2y-10y slope'"
  ],
  "notes_to_p2": "1-paragraph hint for the candidate-generation pass — which 3-5 strategies look most translatable to ETF universe"
}
```

**Do NOT** invent URLs. **Do NOT** cite paywalled papers without a
verified SSRN/arxiv/NBER preprint URL. If you can't verify, drop the
citation.

Return ONLY the JSON object. No prose preamble, no markdown fence.
