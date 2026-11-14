# Peer final_v2 Status — 2026-11-14

**Reviewer:** FP6 (`FP6_final_v2_peers.md`).
**Coverage:** PASS for reading; FAIL for reproducibility.

## Folders reviewed

| Folder | Status | Notes |
|---|---|---|
| `final_v2/finpredict` | PARTIAL | audit + quick wins + master plan; no run artifacts; cites our older package |
| `final_v2/finpredict-v3` | OVERSTATED | calls trend/carry/mean-reversion "real profitable"; its own folder refutes VWAP |
| `final_v2/flaxen-hair` | **DANGEROUS / REJECT** | re-asserts mega_mutation `production_enable=true`; FP1 falsified; 170-ledger m006 PF 0.767; 4 passes vs 8.5 expected |
| `quant-audit-2026-11-14` (self-contained) | **STRONGEST NEGATIVE** | stop-fill, 170-ledger, per-class R-multiple; no edge |

## Classification

- **7 ADOPT:** stop-fill replay, 170-ledger benchmark, 3× cost gate, `universal_price_enricher`,
  CRYPTO POSITION/SWING split, horizon-harness thresholds (after fixing `MIN_WINDOWS`), R-multiple
  reporting.
- **12 MERGE:** 50d+200d trend variant, 4-factor 50+ name portfolio, and other per-class fixes.
- **11 REJECT:** short-term reversal, `MUTUAL_FUND` build, decimal-ratio PnL, TradingView winner
  windows, "all other classes negative", mega_mutation enablement, and others.
- **4 ALREADY_COVERED.**

## Contradictions that matter

1. `finpredict-v3` "real profitable families" — no proof; 23 candidates, 0 proved; 0/9 money-ready.
2. `flaxen-hair` `production_enable=true` — contradicts FP1, quant-audit, and its own caveats.
3. "All other classes negative (PF 0.18–0.31)" — false on `recent_closed` (EQUITY 1.154, ETF 1.036).
4. Peers cite our older `final_2026_11_14` package; final_v2 was not on main when they wrote.

No peer final_v2 establishes a profitable edge. The strongest new material is negative: stop-fill
slippage, the 170-ledger pass rate, and the per-class cost/R-multiple analysis.
