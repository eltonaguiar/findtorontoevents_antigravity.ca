# HONEST READ — consolidated, 2026-11-23

**Branch:** `research/honest-read-2026-11-23` · **Author:** Kilo · Paper only, zero capital, not investment advice.

## Jurisdiction decision (documented inline, per the operator's instruction to decide)
This honest-read bundle is **documentation that references the main codebase and the programme's measurements**. It is
placed on a **fresh branch cut from current `origin/main`** rather than on my working branch, because (a) my working branch
is thousands of commits behind and would drag unrelated history into review, and (b) the honest-read artefacts are
self-contained docs/reports that a reviewer can read without the stale base. Contest-round reports stay in
`antigravity_review_Nov192026` (already on its `main`). This is the most defensible split: **code-adjacent honest read → this
branch; round-scoped contest artefacts → the review repo.**

## The one-line verdict
**0 investable.** The canonical audit rejects every cell on an alpha gate (0/362), and the positive control proves that
gate is *sound but underpowered* — so "failed" means "not demonstrated above the detection floor," not "proven absent."
The only defensible real-money action is a **low-cost broad index fund**, chosen on cost and tax.

## What actually holds (measured)
- **Alpha gate:** 0/69 symbols, 0/362 cells pass; best class FOREX α-CI-lo = **−0.144%**. But power: at 0.2%/yr alpha the
  gate has ~17% power at n=100; **MDE ≈ 5.08%/yr** on 33.8y of SPY. (PROGRAMME_ALPHA_SWEEP, ALPHA_GATE_POWER_CORRECTION.)
- **Positive control:** injecting 0/1/2/3/10%/yr into real SPY → magnitude recovered exactly, 0% null silent, 1–3% invisible,
  10% significant (t=3.94). The gate is correct, just power-limited.
- **Index vs fund:** FXAIX (0.015%) vs SPY (0.0945%), same index, corr 0.998; excess Sharpe ≈0.50; **CAGR CIs overlap** so no
  fund ranking is distinguishable — buy on **cost/tax**, not trailing returns. (FUNDS_WHAT_TO_BUY.)
- **Practical risk:** SPY −24.5% drawdown (2022-01→2022-10), ~14 months to recover; fee compounding 0.03% vs 1.8% =
  $755k vs $458k /30y/$100k; DCA loses to lump-sum ~80% historically (DCA is behavioural, not return). (INVESTOR_FAQ.)

## Corrections I made to my own work (integrity trail)
1. **Value "+0.11%":** it is the **EQUITY class alpha (CI spans 0)**, *not* a value-strategy result; **value/HML was never
   measured** (no fundamentals, "no committed backtest output"). The "+0.11%→+2.89%" correction is **retracted at the root.**
2. **Total-return audit:** yfinance 1.3.0 `history()["Close"]` is **already adjusted** (auto_adjust None→True), so my
   "333/231/49 files" was over-flagged; genuine exposure is **62 files** using explicit `auto_adjust=False` or raw
   Stooq/chart-API Close. Dividend drag (~2.78%/yr) is real **only for raw feeds**.
3. **Alpha gate = power, not null** (peer hermes); "zero alpha" withdrawn.
4. **F4 "mutual fund beats its ETF" retracted** (fee effect within noise).
5. **Sortino** corrected to divide downside deviation by N (FXAIX 0.501→0.722).
6. **Contest ranking:** bootstrap → **0/2000 unique winners** (permanent 3-way tie); R-falsifier calibrated (clear winner
   97.8%, null 0%) and ready for fills. RULES §7 stands.

## What is genuinely UNKNOWN / needs owner input
- **Realized R** for the contest (no fills yet) — the R-bootstrap is built and calibrated, waiting on fills.
- **Value/HML** — unrunnable without book equity + shares outstanding; unmeasured, not rejected.
- **Measured venue fee tier** (crypto) and **delisting-aware prices** — procurement, not analysis.

*Paper only. Not investment advice.*
