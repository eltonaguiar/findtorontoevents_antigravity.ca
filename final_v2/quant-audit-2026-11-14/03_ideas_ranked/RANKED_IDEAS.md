# Ranked ideas — how to get to profitability, per asset class

Ranked by (expected money moved) ÷ (cost to test). Every item states its gate before the test, so a
negative result is as usable as a positive one. Ideas are ranked by evidence strength first, not
ambition.

---

## 1. Fill stops at the stop price (CRYPTO) — biggest single lever

**Evidence:** 703 of 773 crypto stops exited at a price different from the declared stop; mean
realized loss 2.990% against a mean planned risk of 1.919%. Total overshoot **+828.0pp** against a
class total of **−837.8pp** — 98.8% of the entire crypto loss.

**Do:** resolve stops against intrabar OHLCV; fill at the stop when the bar breaches it, at the bar
close only when price gaps through. Same for take-profits, symmetrically.

**Gate:** median realized loss on stopped trades within 5% of median planned risk.

**Expected:** PF 0.768 → ≈1.00. This does not create profit; it removes the deficit that currently
masks whether any signal has an edge. Every other crypto idea is unmeasurable until this is fixed.

---

## 2. Impose a cost gate: average PnL must be ≥ 3× round-trip cost

**Evidence:** average slippage as a share of average PnL is CRYPTO 39.7%, EQUITY 16.0%, ETF **267%**,
COMMODITY **422%**, FUTURES 72%. Three classes are flagged CRITICAL by the system's own validator.

**Do:** a hard pre-emit filter per class. ETF intraday (0.0187% expected against 0.05% slippage) and
commodity intraday cannot clear it and should not be emitted.

**Gate:** no pick emitted whose class fails the 3× test until the class's average PnL exceeds it.

**Expected:** removes an estimated 820 intraday ETF picks and the commodity intraday stream outright.
Cheapest possible reduction in losses: they are already at or below zero.

---

## 3. Cut trade count to T2-quality only

**Evidence:** 3,500 closed trades in 9 months ≈ 390/month. Two systems produce 85% of them —
`kimi_riseoftheclaw` n=1,706 at PF **0.828** and `luxalgo_filters` n=1,265 at PF 1.113. The single
largest strategy (`luxalgo_confluence`, n=1,278, 36.5% of the ledger) is scored by the payload's own
benchmark ledger as n=1,211, PF 1.0287, cumulative **−26.4%**, bootstrap pass **false**.

**Do:** require n≥30 forward trades and PF≥1.2 at the *strategy* level before a strategy may emit.

**Gate:** monthly trade count ≤ 60, aggregate PF ≥ 1.1 over the following 3 months.

**Expected:** the ledger's own best-evidenced strategies by sample (rs-breakout-scout n=133 WR 53.4%
PF 1.652 t=2.37; battleground n=122 WR 56.6% PF 1.756 t=2.28) survive; the volume firehose does not.
Neither of those two survives multiple-testing correction as things stand (see #8) — but they are the
right shortlist to forward-test.

---

## 4. EQUITY: extend to 2 years and benchmark against SPY, not zero

**Evidence:** only class with a positive after-cost win-rate margin (+2.9pp), losses inside plan
(−0.84R average), and a working time-exit bucket (n=220, WR 61.4%, PF 1.988). But t=1.52 (p=0.12) and
second-half PF fell 1.342 → 0.977.

**Do:** pre-register the rules, extend the sample to 24 months, benchmark against SPY total return.

**Gate:** OOS Sharpe ≥ SPY Sharpe and PF ≥ 1.15 at n ≥ 500, with first-half and second-half PF both
≥ 1.05.

**Expected:** the honest prior is that this is beta. The peer program's three independent RSI(2)
variants all failed to beat buy-and-hold (1.50, 1.83, and DSR 0.603). Test it anyway: it is the only
class where the margin is currently positive.

---

## 5. CRYPTO POSITION-horizon picks: forward test at n≥100

**Evidence:** n=33, WR 69.7%, PF 3.180, +74.4pp — the only positive crypto bucket, against SWING at
PF 0.457 (**kill that one now**: 243 trades, −328.6pp, 39% of the class loss).

**Do:** freeze the POSITION-horizon rule set, emit only those, accumulate 100 forward trades.

**Gate:** forward PF ≥ 1.3 at n≥100 with WR ≥ 55%.

**Expected:** likely regression toward the class mean (n=33 is small and the bucket is probably
regime-selected), but it is a cheap, pre-registered test of the one positive signal in the ledger.

---

## 6. COMMODITY: CFTC COT contrarian at weekly frequency

**Evidence:** the only class with n≥200 at intrabar truth and PF≥1 (n=229, WR 40.17%, PF **1.0256**),
and a `commodity_cot_contrarian` sidecar already exists in `sidecar_promotion_status`. Structurally
the best fit: weekly data, low turnover, no intraday execution risk, and commercial positioning is a
documented basis rather than a mined pattern.

**Do:** weekly rebalance on COT extremes, hold 1–4 weeks, costs at 10bp.

**Gate:** OOS PF ≥ 1.15 on n≥100 trades, slippage <25% of average PnL, and beat an equal-weight
commodity benchmark (not zero).

**Expected:** modest but real, if anything here is real. It is also the only idea on this list whose
data source is not already exhausted by the 23-candidate research program.

---

## 7. Kill the exit taxonomy's best and worst buckets deliberately

**Evidence:** TIME_EXIT is the best-behaved exit in every class (EQUITY PF 1.988 WR 61.4%; ETF PF
3.062 WR 63.9%; overall n=517 WR 60.7% PF 1.766). SL_HIT is where classes die (n=1,468, mean −2.974).
FORCE_CLOSED (n=615, mean +0.019) is pure noise and should be split into its real causes.

**Do:** convert FORCE_CLOSED into a real exit reason; test a time-based primary exit against
stop-based, per class.

**Gate:** each class's realized expectancy improves with a named, pre-registered exit policy.

**Expected:** for equity and ETF, time exits are doing the work already. Making that explicit is a
cheap improvement — and it also removes the ability to attribute PnL to signals that never had a
chance to trade.

---

## 8. Fix the multiple-testing budget before testing anything else

**Evidence:** the repo's own `audit_dashboard/data/benchmark_ledger_proof.json` evaluates **170
ledgers** and finds **4** that pass paired bootstrap at 95% — against **8.5 expected by chance** at
that threshold. Fewer pass than chance predicts. That is the cleanest available statement that this
system's search space has no demonstrated edge anywhere in it.

**Do:** pre-register every forward test; count every trial; require |t| ≥ 3.5 (or BH-FDR at q=0.10
across the trial count) instead of 1.96. Publish trial counts next to results.

**Gate:** any future "proven" claim must state the number of trials and the corrected threshold.

**Expected:** this will reclassify several currently-published "validated" strategies as unproven. It
is the only change that makes the rest of the list meaningful.

---

## What not to do

- **Do not add mutual fund coverage.** Zero picks exist today; adding a daily-priced, fee-bearing
  instrument to a system losing 0.176pp/trade is negative expected value and pure work.
- **Do not trust PF from `picks.recent_closed` as a cross-class comparison.** Exit mix mechanically
  determines win/loss (TP_HIT is 99.9% wins by construction), so class PF mostly ranks exit
  composition. Use R-multiples.
- **Do not tune on the current window.** Every class decays half-to-half; fitting to the first half is
  fitting to a regime that already ended.
- **Do not cite the dashboard's per-class win rates without the intrabar cross-check.** ETF reads
  73.3%/PF 1.84 on a 15-row policy_clean subset and 2.22%/PF 0.0216 on 45 intrabar rows — an 85×
  inflation.
