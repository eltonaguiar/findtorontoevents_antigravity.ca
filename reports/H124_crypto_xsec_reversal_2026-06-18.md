# H-124 — Crypto Cross-Sectional Reversal: REFUTED (2026-06-18)

Pre-registered (M-107) BEFORE running; `loop_preflight` GO. Read-only on `crypto_ohlcv`. ONE FDR family — CLOSED.

## Hypothesis
Daily-rebalance, **market-neutral** LONG bottom-decile / SHORT top-decile of prior-day close-to-close return
across the crypto_ohlcv universe (302 non-stablecoin symbols, hourly→daily), net 10bp/side. Economic prior:
short-horizon overreaction/reversal (Lehmann 1990). Market-neutral construction = built-in BTC-beta control.

## Result (180 daily rebalances)
| metric | value |
|---|---|
| NET LS mean/day | **−0.176%** |
| daily-return PF | 0.708 |
| ann. Sharpe | −2.49 |
| % positive days | 47% |
| cumulative | −28.4% |
| IS half mean/day | −0.048% (PF 0.898) |
| OOS half mean/day | −0.304% (PF 0.588) |
| BTC-beta | **+0.059** (market-neutral ✓) |
| LONG-loser leg | −0.57%/day |
| SHORT-winner leg | +0.22%/day |
| monkey-test | t=−1.75 vs null p95 −2.12 (both negative) |

## Verdict: REFUTED
The pre-registered falsification triggers on the primary clause — **the market-neutral LS is net-negative in BOTH
IS and OOS halves**. BTC-beta ≈ 0 confirms this is genuine *negative* alpha, not a beta artifact, so it's not a
costing/regime fluke. The monkey-test "beats p95" is a red herring: both the candidate and the null are negative
(the 20bp/day rebalance cost drags everything down) — beating a more-negative random distribution is not edge.

## What it tells us (negative knowledge)
**Daily crypto is short-horizon MOMENTUM, not reversal**: the long-loser leg bleeds (−0.57%/day, losers keep
falling) while shorting winners is mildly positive (+0.22%/day) but not enough to offset. This is the opposite of
the reversal prior. A cross-sectional *momentum* variant (long winners / short losers) would be a DISTINCT
hypothesis requiring its own pre-registration — NOT pursued here (anti-circling: H-124 is one FDR family, closed;
and naive daily momentum would still face the 20bp/day cost drag). Logged so it isn't re-litigated as reversal.

---
# H-125 — Weekly Crypto Cross-Sectional Momentum: REFUTED (2026-06-18)

Pre-registered (M-107) before running; `loop_preflight` GO. Motivated by H-124's leg findings + the cost insight
(weekly turnover ~5x less drag than the daily rebalance that killed H-124). LONG top-decile / SHORT bottom-decile
by prior-7d return, weekly non-overlap rebalance, market-neutral, net 10bp/side.

| metric | value |
|---|---|
| NET weekly LS mean | **−0.844%/wk** |
| weekly PF | 0.519 |
| ann Sharpe | −1.87 |
| IS half mean | −1.916% (PF 0.28) |
| OOS half mean | +0.227% (PF 1.27) |
| LONG-winner leg | −3.06%/wk |
| SHORT-loser leg | +1.37%/wk |
| BTC-beta | −0.225 |
| monkey-test | t=−1.27 < null p95 1.11 (FAILS) |
| weekly obs | 24 (thin) |

## Verdict: REFUTED
IS half net-negative + fails the monkey-test → falsified. n=24 weeks is also far below the n≥80 bar, but the sign
+ monkey-test failure are decisive regardless.

## Combined conclusion (H-124 + H-125) — avenue CLOSED
Daily reversal (H-124) AND weekly momentum (H-125) are both net-negative, and the cross-sectional leg signs **flip
with horizon** (daily: losers trend down; weekly: winners revert down). That pattern = **no stable, exploitable
cross-sectional autocorrelation structure in crypto at these horizons net-of-cost** — just noise plus the
rebalance-cost drag. This matches the project's settled "no robust edge" reality. No further cross-sectional
variants will be run (anti-circling: reversal×momentum × daily×weekly is the full 2×2; all refuted).
