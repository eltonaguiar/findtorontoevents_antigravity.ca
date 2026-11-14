# Peer Review — ITERATION-005 "PROVEN: diversified vol-targeted trend"

**Verdict: INTERNALLY CONSISTENT, but "PROVEN" is the wrong word.** The arithmetic checks out; the
significance test does not test what the claim needs it to test.

Source: `2026-11-14/finpredict/2026-11-14T160004Z/research/ITERATION-005.md`, commit `05a4ef3ff14`
(verified: exists, is an ancestor of `main`).

## What checks out

| Check | Result |
|---|---|
| Sharpe consistency | CAGR 23.0% ÷ vol 9.7% = 2.37 vs stated 2.13 → consistent once a risk-free rate is subtracted. Unlike the Kilo claim, **the units are coherent**. |
| Cost assumption | 0.1%/side is realistic for crypto majors. |
| Bootstrap | Block-bootstrap CI [1.25, 3.25] excluding zero is the right *shape* of test for autocorrelated daily returns. |
| Turnover | ~293 position-changes/yr is genuinely low; not a churn artifact. |
| Per-asset | 10/10 positive (0.47–1.11) — diversification is real, not one lucky symbol. |

## What the test does not establish

1. **t = 5.56 tests mean daily return > 0, not > buy-and-hold.** In a bull window, a long-only/flat
   crypto book passes that test on beta alone. The peer says so themselves: *"Buy-and-hold of same 10
   also had Sharpe ~2.2."* A Sharpe of 2.13 against a benchmark Sharpe of 2.2 is **not an edge** — it
   is the benchmark, risk-managed.

2. **The window is bull-biased by their own admission** (2017–2024). My independent test on
   Binance daily 2021-01→2026-11 (which contains a real bear) gives TSMOM 365d an OOS Sharpe of
   **0.57** with +31.7% and 27.4% MDD, and a matched random-entry null at **p = 0.200** over 600
   iterations. Same family, honest window, no significance. Both results can be true: trend is a
   real risk premium that a bull sample flatters and a 600-draw null cannot separate from luck.

3. **Bar count doesn't match the claimed history.** 2,490 daily bars over "7.4 years" = 336 bars/yr.
   Daily crypto should be ~365/yr (≈2,700 bars). The 8% deficit is unexplained — either missing days
   or a shorter window than stated. Minor, but it is the kind of undocumented gap that should not
   appear in a document whose title is PROVEN.

4. **PF 1.40 is not a profit factor.** PF is trade-based; a vol-targeted daily overlay with ~293
   position changes/yr evaluated on bar returns produces a bar-level ratio, not PF. Reporting it
   invites comparison with ledger PFs that mean something else.

## Fair reading

This is a **credible, well-constructed harvest of the documented time-series momentum risk premium**
(Moskowitz–Ooi–Pedersen 2012) with vol targeting and diversification — the CTA playbook. It is
probably worth running as a diversifying sleeve *if* the operator accepts ~0.5–2.1 Sharpe depending
on regime and wants the drawdown profile, not the return.

It is not evidence that this repository's prediction system has an edge, and calling it PROVEN in a
commit message invites exactly the confirmation the audit was written to stop. Rename to
"risk-premium harvest, benchmark-relative alpha unproven".

## Recommendation

- Add a **benchmark-relative** test: excess return vs equal-weight buy-and-hold of the same 10, with
  a paired bootstrap. That is the number that decides whether the trend rule earns its turnover.
- Pre-register the forward run; measure excess-of-benchmark monthly.
- If it clears on a full bear-inclusive window, it becomes a legitimate sleeve — still unrelated to
  the 166-cell ledger, which remains 0/166 money-ready.
