# reconciliation_researcher — resolver flicker share

_Generated: 2026-05-02T04:02:15.958373+00:00_

**Question:** rec_001 — How much of the audit's 'wins' is sub-bps flicker?

| Class | n | Wins | <10 bps | <5 bps |
|---|---|---|---|---|
| COMMODITY | 76 | 61 | 100.0% | 55.7% |
| CRYPTO | 6884 | 2261 | 45.1% | 40.1% |
| EQUITY | 30 | 13 | 100.0% | 23.1% |
| FOREX | 423 | 115 | 100.0% | 100.0% |

**Wire-up:** asset-class-gated thresholds in `alpha_engine/outcome_resolver.py` v2 (already landed at lines 97-126); confirms the design is correct.

