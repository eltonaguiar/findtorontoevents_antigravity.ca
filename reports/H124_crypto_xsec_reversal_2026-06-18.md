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
