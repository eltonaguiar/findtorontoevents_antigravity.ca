# Final Verdict — v1 + v2

**Date:** 2026-11-14
**Protocol:** `PROTOCOL.md` v1.0 + Addendum 1 (Nasdaq ETF fallback)
**Candidates:** 12 (v1: H1–H7; v2: H8–H12) + 27-cell parameter grid
**Verdict: NOT PROVED.** No tested approach survives a clean, protocol-compliant proof.

## What was found

H10 — **SPY/QQQ RSI(2) (entry <10, exit >50, max hold 5), 5 bps, idle cash at 13-week T-bill** —
mechanically passed the pre-registered gates on 2024-01-01..2026-11-13:

| Metric | H10 | Benchmark (SPY/QQQ B&H) |
|---|---:|---:|
| OOS Sharpe | **1.83** | 1.02 |
| OOS CAGR | **22.0%** | 18.6% |
| OOS max drawdown | **−7.6%** | −21.0% |
| OOS trades | 111 | — |
| DSR (N=12) | 0.978 | — |
| p-value | 0.00194 | — |
| PBO (all 12) | 0.106 OOS-only / **0.417 full-sample** | — |
| 2× cost Sharpe | 1.68 | — |
| Bootstrap p05 | 1.28 | — |

It was independently reproduced by a separate agent and contains no lookahead bug. That is
**not** enough for a proof.

> **Artifact reconciliation.** The table above is from `results.json` regenerated at 18:36Z after
> the cost-timing and RSI edge-case fixes. The adversarial review was computed on the 18:25Z
> pre-fix snapshot (Sharpe 1.8452, DSR 0.9789, p 0.001802, 2× 1.6834). Both sets fail the strict
> standard; see the erratum in `validation/STATS_REVIEW_H10.md`. The PBO 0.106 is an OOS-only
> label; the standard full-sample all-12 CSCV PBO is **0.417** (still <0.5, but much weaker).

## Why H10 is NOT PROVED

1. **OOS contamination (protocol §4).** H10 is a cash-added variant of H7 created after H7's v1
   OOS was inspected. It reuses the **same 2024-2026 window**. The OOS is "seen," not clean.
2. **Effective multiple testing.** Counting the 27-cell parameter grid inspected on OOS,
   effective `N≈38`: **DSR 0.9365 < 0.95** and Bonferroni α 0.001316 < p 0.001802. Both fail.
3. **Single-day dependence.** 2025-04-09 contributes **+11.20%** in one day. Removing it drops
   DSR to **0.8993**; removing the top 3 days drops it to **0.8255**.
4. **Execution fragility.** An extra one-day lag drops Sharpe from 1.83 to **0.696** (CAGR 8.2%);
   a 3-day lag gives **0.477**. The pre-registered gate requires ≥1.0.
5. **Risk-matched benchmark ambiguity.** A static ~17% SPY/QQQ + ~83% T-bill mix has rf=0 Sharpe
   **2.168–2.285**, above H10's 1.83. On excess-of-rf returns H10 wins (1.45 vs 0.78), so the
   conclusion depends on the benchmark convention.
6. **Regime dependence.** Clean 2016-11-14..2017-12-31 holdout: H10 Sharpe **1.755 / CAGR 7.46%**
   vs B&H **2.835 / 25.76%** — positive but underperforms. H10 also lags badly in low-vol bull
   years (2019, 2021, 2023). The OOS T-bill yield averaged **4.38%** vs **0.90%** in the holdout.
7. **The edge is largely T-bill carry.** Same 111 risk changes: H7 with 0% cash = Sharpe 1.51 /
   CAGR 17.61%; H10 = 1.83 / 22.0%. The +3.6 pp is ~0.827 × the 4.38% cash yield.
8. **Out-of-universe is suggestive, not proof.** DIA/IWM/VTI 2024-2026 H10 Sharpes 1.28–1.94
   suggest a broad 2024-2026 short-term reversal regime, not a durable, regime-independent edge.

## Independent ledger cross-check (peer-reported, corroboration only)

A separate production-ledger audit (3,500 `recent_closed` rows) reached the same negative
direction, but the ledger is unstable intraday so treat these as corroboration, not a second proof:

- `recent_closed` net-negative: Σ PnL **−469.5%** at the 14:30Z snapshot; it moved to **−574.1%**
  and PF 0.92 → 0.903 by 17:58Z.
- No candidate survived **N=683** in the peer's Bonferroni sweep.
- OOS decay/reversal; 0/9 asset classes money-ready; `readiness.sizing_allowed=false` 9/9.
- Kill-switch exercised 42/56 yet `pf_lift = −0.0223`.

The peer's 70/30 split is **not** a clean OOS (the window was inside its own selection sample),
so it does not establish proof.

## What would prove it

A **clean forward OOS** with the exact H10 rules, frozen parameters, and no re-selection:

- Start: first signal after 2026-11-13 (seeded in `forward/ledger.csv`).
- Minimum: **90 calendar days or 30 round trips**, whichever is longer.
- Same gates, plus the stricter ones the reviewer recommended:
  - excess-of-rf Sharpe vs a risk-matched benchmark;
  - DSR ≥0.95 after including every look in the grid (N≥38);
  - DSR ≥0.95 after removing the single best day;
  - 2-day-lag Sharpe ≥1.0;
  - forward max drawdown within the pre-registered envelope.
- No parameter changes. Any change starts a new version and a new forward ledger.

## Honest conclusion

The system's existing surfaces were not profitable (audit verdict FAIL). This independent research
program also did **not** prove a profitable approach. It did produce one **exploratory** candidate
with strong retrospective risk-adjusted metrics that fails the strict proof standard on
contamination, multiple-testing, regime, and execution grounds. Publishing this negative result is
the correct outcome; claiming H10 as "proved" would repeat the original system's error.
