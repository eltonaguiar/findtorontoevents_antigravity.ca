# FINAL Peer Adjudication — 2026-11-14 (v2, closing review)

Reviews every peer's final deliverable and the disputes among them. Where two peers
disagree, I adjudicate using the quant-audit (Freebuff) re-execution where available.

## Peer final map

| Peer | Final location | Verdict |
|---|---|---|
| finpredict v1 | `final_2026_11_14/finpredict/` | strong planning; ITERATION-005 trend is the best genuine edge candidate |
| finpredict-v2 | `final_2026_11_14/finpredict-v2/` | reconciliation backbone; best root causes (P0-1..9, Actions deep-dive) |
| finpredict-v3 (me) | `final_2026_11_14/finpredict-v3/` | data-hygiene guardian + ML/horizon harness; negative verdict |
| finpredict-v4 | `final_2026_11_14/…` + `audits/2026-11-14` | strong verification; some stale evidence, destructive SQL to hold |
| childlike-airport | `final_2026_11_14/childlike-airport/` | good structure; **VWAP claim refuted** (annualization) |
| quant-audit | `final_2026_11_14/quant-audit-2026-11-14/` | **adjudication** — refutes VWAP, corrects trend claim |
| flaxen-hair | `final_2026_11_14/…` (quick_wins) | PnL-unit mix defect = strongest single defect |
| scratch-hippodraco | `final_2026_11_14/…` | QW-ALL-1..9 implementation-ready checklist |
| hilarious-seer | `final_2026_11_14/…` | corroboration only |

## The key dispute — VWAP "Sharpe 3.76" (resolved)

- **childlike-airport** lists Regime-Filtered VWAP MR: Sharpe 3.76, DSR 1.0000,
  PBO 0.489, "VALIDATED".
- **quant-audit (Freebuff) refutes it**: 12.7% total over ~22 months implies an
  annualized vol of **1.84%** at Sharpe 3.76 — impossible at 40% position size in 4h
  crypto. Fatal annualization unit error; PBO gate inverted. Real Sharpe ≈1.18.
- **finpredict-v2 SCORECARD independently falsifies the same VWAP claim**: correct
  Sharpe ~1.18 (t=0.91, p=0.18), intrabar stops PF 0.81, CSCV PBO 0.84–0.97.
- **Adjudication: the 3.76 claim is rejected.** Do NOT adopt VWAP as a headline
  "validated" edge. It may be worth *re-testing* with correct annualization and a
  proper PBO gate, but it is not proof today.

## The trend claim — ITERATION-005 Sharpe 2.13 (adjudicated)

- finpredict v1 claims vol-targeted trend: net Sharpe 2.13, t=5.56, CI [1.25,3.25],
  OOS 2.06→2.33, 10/10 assets positive.
- quant-audit: **partially supported but mislabelled** — internally consistent, but
  ≈ beta; significance was tested against zero, not against buy-and-hold; their own
  caveat shows B&H of the same 10 had Sharpe ≈2.2. Also `TSMOM365` OOS Sharpe 0.57,
  null p=0.200 on their re-run.
- **Adjudication: the trend method is the best genuine edge candidate and should be
  built**, but its claim must be restated as "risk-adjusted vs B&H on drawdown/vol",
  not "outperforms B&H". It is a risk premium, not an alpha. Keep it, fix the
  benchmark framing, and add survivorship + execution stress.

## Agreed systemic findings (converged by all peers)
1. Frozen/fake 0% PnL (81% of open picks per deepAI; 11 FOREX phantoms).
2. Losses understated (claimed −106pp vs real −1,116pp).
3. Zombie/EXPIRED rows (78.6% of active_raw).
4. PnL-unit mix bug (flaxen-hair; ratio-vs-percent, up to 100×).
5. Backtest↔forward disconnect (0 rows with both bt_trades>0 and fwd_trades>0).
6. Multiple-testing inflation (N≈658 ⇒ ~32.9 false positives).
7. 0/9 money-ready; alpha engine dead (9 cancelled+1 failure of last 10 runs).

## Vetoes (carried from my R2, unchanged)
- v4/ML/destructive SQL (DELETE/UPDATE/INSERT OR REPLACE) → dry-run/archive only.
- Mutual-fund stub scanner → classification-only.
- hilarious-seer purge-old-picks (>30d) → quarantine-in-view.
- Unblocking FUTURES/COMMODITY without a real feed.

## Final recommendation to coordinator
1. Adopt **CRYPTO vol-targeted trend** as the first real profitable strategy (build,
   fix benchmark framing, add execution stress).
2. Adopt **ETF multi-asset trend** as the next build (diversifier).
3. Add **BTC funding/carry sleeve** (capital-capped).
4. Reject the VWAP 3.76 claim; optionally re-test it correctly.
5. Fix price-freshness FIRST (universal_price_enricher in the build) — nothing else is
   trustworthy until live prices are real.
6. Enforce the horizon-harness gate (n≥60, CI excludes 50%, PF>1.05, win-majority
   ≥66% windows) as the release criteria for every strategy.
