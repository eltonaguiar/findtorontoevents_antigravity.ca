# v3 Verdict — Breadth

**Date:** 2026-11-14
**Protocol:** `PROTOCOL_v3.md` (N=8; cumulative N=20)
**Verdict: NOT PROVED — 0/8 passed.**

| Candidate | OOS Sharpe | OOS CAGR | Benchmark Sharpe | WF Sharpe | SPA p | Status |
|---|---:|---:|---:|---:|---:|---|
| H16 ETF XS momentum | 0.98 | 29.6% | 1.18 | 0.84 | 0.488 | NOT_PROVED |
| H18 ETF TSMOM breadth | 1.00 | 12.0% | 0.99 | 0.37 | 0.488 | NOT_PROVED |
| H17 ETF XS reversal | 0.76 | 15.2% | 1.18 | 0.60 | 0.488 | NOT_PROVED |
| H19 Country momentum | 0.76 | 16.8% | 0.99 | 0.55 | 0.488 | NOT_PROVED |
| H15 Crypto TSMOM breadth | 0.20 | −2.9% | 0.06 | 0.66 | 0.488 | NOT_PROVED |
| H13 Crypto XS momentum | −0.18 | −31.9% | −0.01 | 0.78 | 0.488 | NOT_PROVED |
| H20 Crypto momentum + BTC trend | −0.08 | −21.3% | −0.01 | 1.10 | 0.488 | NOT_PROVED |
| H14 Crypto XS reversal | −0.36 | −44.3% | −0.01 | 0.49 | 0.488 | NOT_PROVED |

## Why breadth did not help

- The best candidate (H16) earned a high absolute return but **underperformed its own equal-weight
  ETF benchmark** (Sharpe 0.98 vs 1.18) and failed the 12-1 momentum cost/execution tests.
- The Reality Check p-value across all candidates is **0.488** — the max observed performance is
  indistinguishable from the bootstrap null.
- PBO is 0.36 (ETF) / 0.59 (crypto); crypto candidates are overfit-prone.
- Crypto momentum/reversal were **negative in the 2024-2026 OOS** across 30 pairs; 2024-26 was not
  a repeat of 2020-21 momentum.
- Adding assets increases breadth but also correlates the bets; it did not create an independent
  edge.

## Conclusion

The documented "buy winners" / "buy losers" families do not survive cost-aware walk-forward +
Reality Check on this data. No v3 candidate is promoted. The funding-carry family (v4) is the only
remaining economically motivated test.
