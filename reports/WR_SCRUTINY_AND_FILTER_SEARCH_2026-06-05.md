# Win-Rate Scrutiny + Profitable-Filter Search — 2026-06-05

Operator ask: "double-check anything over 60% WR (or even 50%) — is it skewed? Is there a set of
filters that, traded over a large period, would have been profitable? Or is it random chance /
underperforming buy & hold?" Answered by 2 grounded DB audits (SELECT-only, every number cited).

## PART A — high-WR cells: do they survive scrutiny? (31 cells, WR>=50% & n>=20)
**ZERO survive clean.** Breakdown:
- **7 ARTIFACT:** `ml_enhanced_INJUSDT` (all 24 resolved_at NULL, PF=999 placeholder); `regime_mild_bear`
  (14/17 "wins" are pnl=0, PF 0.12, avg pnl NEGATIVE); `clone_hl_copy_*` (10-12 of 16 wins are pnl=0);
  `MeanReversionBB` crypto+"EQUITY" + `hs_lb_None` (PnL **templated to 2-4 fixed values** = synthetic
  fixed-RR placeholders, not realized PnL; the "EQUITY" one is entirely crypto symbols mislabeled).
- **~22 SKEWED:** 17 `ml_enhanced_*`/`keltner_*` cells are **100% one symbol** (single-name bets, not
  class edges); `cta_cross_asset_tsmom` 57% USDJPY, `cta_golden_cross_200` 71% HG=F. Many are
  **high-WR but PF<1 money-losers** (APEUSDT 50% WR / PF 0.07 / avg -28.5%; ALGOUSDT 62.5% / PF 0.60).
  Several are **coin-flip** (binomial p: non_crypto_consensus 0.21, combined_confidence 0.59,
  spot_perp_basis_arb 0.42 — WR indistinguishable from 50%).
- **Lone "real-looking" (caveated):** `prediction_market_consensus` CRYPTO 83.8% WR PF 16.5 n=105 —
  but 44% of picks resolved on ONE batch day (2026-04-15, 45/46 wins) + 48% DOGEUSDT → cannot be
  distinguished from simply holding DOGE over that up-move. Not a durable class edge.

## PART B — is there a profitable filter set over time? **NO.**
- **Resolved panel:** 10,220 WON/LOST rows (Feb-22 → Jun-4). EXPIRED (28,878, pnl=0) correctly excluded.
- **Baseline "trade everything":** WR 44.9%, gross PF 1.00; **net of 15bps: PF 0.91, −0.155%/trade,
  cumulative −1,583%.** Both time-halves negative. A net loser that also loses to buy-and-hold.
- **Best in-sample filter (FOREX, PF 1.55) COLLAPSES out-of-sample:** early-half PF 2.54 → late-half
  **0.62**. COMMODITY 1.30 → 0.11. The OOS-disciplined family filter (PF>1.5 & n>=30 defined on the
  EARLY half, traded LATE) → **PF 0.88, cum −14.5**. Edge does not persist.
- **Random-chance tests:** no asset class has WR significantly > 50% (all binomial p≈1.0). Bootstrap PF
  95% CI lower bound clears 1.0 for **no** class (FOREX [0.51,3.17] straddles 1 — its PF is a few big
  winners at 40% WR, not consistency).
- **vs buy-and-hold:** the only positive-avg cells are long exposure in a rising-market window; none
  beat passively holding the market net of costs.
- **Data-quality reality:** 10.1% sign-mismatch (status vs pnl sign) → labels partly unreliable;
  resolved_at is batch-stamped (2026-05-31 alone = 1,180 rows); most rows are `backfill_*` (reconstructed
  history, NOT a live forward track record). These only WEAKEN edge claims — they can't manufacture one.

## VERDICT (direct answers)
- **>60% WR skewed?** Every one — single-symbol concentration, templated/placeholder PnL, flat-as-WON,
  or NULL-resolve. None is a real class edge.
- **>50% skewed?** Yes — coin-flip-or-worse, PF<1, or concentration.
- **A profitable filter set over a large period?** **NO.** Every apparent edge is in-sample selection;
  it dies out-of-sample, loses net of 15bps costs, and underperforms buy-and-hold. The cherry-picked
  full-sample PF 2.37 is pure overfit (dies OOS).
- **Random chance?** Yes — the high WRs are statistically indistinguishable from a coin flip given n,
  and the high PFs are a handful of big winners (PF inflation), not durable skill.

## The one honest exception (NOT in this ledger)
The pick-ledger has no edge. The single validated thing repo-wide is the **clean-bar ETF dual-momentum
sleeve (H-103)** — but that is a separate yfinance daily-bar backtest that passed leakage-free
attribution (alpha t=2.36), NOT a strategy in this contaminated pick ledger. It is a forward-pilot
candidate (n→100 via the monthly cron), not money-ready.

## Bottom line
`money_ready=[]` is **correct and now triple-confirmed**: high-WR cells are artifacts/concentration/
coin-flips; no filter set is profitable out-of-sample or vs buy-and-hold. Do not deploy capital on any
pick-ledger strategy. The only forward path is the clean-bar archetype track + fixing the data
(sign-mismatch, batch-stamp, templated-PnL, live-vs-backfill) so a real edge could even be detected.
