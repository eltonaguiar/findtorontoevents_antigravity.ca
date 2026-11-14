# Peer VWAP Claim — Independent Verdict

**Claim:** `updates/2026-11-14-PROFITABLE-APPROACH-VWAP-MEAN-REVERSION.md`
(regime-filtered VWAP mean reversion, 4h crypto).
**Reviewers:** VWAP-R1 replication + VWAP-R2 adversarial statistics.
**Date:** 2026-11-14
**Verdict: FAIL — NOT PROVED.** The claim does not survive independent replication.

## Claim vs independent result

| Metric | Peer claim | Independent | Basis |
|---|---:|---:|---|
| Trades | 129 (5 symbols) | 129 = **8-symbol** count; 5-symbol subset = **72** | harness + saved JSON |
| Profit factor | 1.210 | 1.210 arithmetic; **0.810 with intrabar stops** | 79/129 trades breached stops intrabar |
| Sharpe | 3.76 | **~1.18** (portfolio) / 1.105 | annualizer `sqrt(8760/4)=46.8` assumes 2,190 trades/yr; actual 215.6/yr |
| t-stat | "z≈16" (DSR) | **0.912, p≈0.18** | pooled per-trade mean-return test |
| DSR | 1.0000 | **0.828 (N=1); 0.011 (N=960)** | reported value is `P(Sharpe>0)`, not Deflated Sharpe |
| PBO | 0.489 | **0.840–0.970** (CSCV) | reported 0.489 is a bootstrap tail p≈0.5 by construction |
| OOS length | ~22 months | **7.18 months** (2026-04-10→2026-11-14) | `730d × 0.3` |
| Total return | +12.7% | **−17.4%** with intrabar stops; **−15.8%** concurrent 40%/symbol | 280% gross exposure |
| Max drawdown | 10.0% | **24.6%** intrabar; 25.4% concurrent | same |
| Cost break-even | 50 bps | **PF <1.0 at 25 bps** | reviewer recomputation |
| Regime filter | improves edge | post-hoc skip-entry OOS: **PF 0.974, Sharpe −0.011, return −7.23%** | filtering after an unfiltered run |

## Fatal issues

1. **Annualization error.** Annualizing a per-trade Sharpe with `sqrt(2190)` multiplies it by 3.19.
   Correct portfolio Sharpe is ~1.18, and the t-stat is 0.91 (p=0.18) — not significant.
2. **PBO is not PBO.** The reported 0.489 is a bootstrap p-value centered on the observed statistic,
   so it returns ~0.5 on noise (0.4935) and on a strong synthetic edge (0.503). Proper CSCV PBO is
   0.84–0.97.
3. **DSR is not DSR.** The printed `1.0000` is `P(Sharpe>0)` with an annualized Sharpe divided by a
   per-period SE. The true Deflated Sharpe is 0.83 at N=1 and ~0.01 once the 960-cell grid is
   counted.
4. **Ignored intrabar stops.** Stops are checked on closes only. 79/129 trades breached their stop
   intrabar and were never stopped out. With gap-aware intrabar stops: PF 0.81, return −17.4%,
   MDD 24.6%. The edge is the missing stop.
5. **OOS mislabelled and contaminated.** The test is 7.18 months, not 22; v7 and v12 share the same
   window; DOGE/AVAX/LINK losers were dropped from the table; the 5-symbol count is 72, not 129.
6. **Not implementable at 40% per symbol.** Five concurrent 40% positions = 280% gross exposure;
   realized concurrent return is −15.8%, MDD 25.4%. Capped at 100% gross it is −4.8%.
7. **Cost sensitivity.** PF falls below 1.0 at 25 bps round trip, not 50 bps.

## Conclusion

The peer's "provably profitable" VWAP claim is a **statistical and execution artifact**. It does
not establish a profitable approach, and it does not support the claim that TradingView contest
winners succeed by "trading with the regime." Our own **NOT_PROVED** verdict stands.

The correct next step is not another parameter search on the same 730-day intraday window; it is a
clean forward test with a proper annualization, CSCV PBO, true DSR, intrabar stops, and a concurrent
capital model.
