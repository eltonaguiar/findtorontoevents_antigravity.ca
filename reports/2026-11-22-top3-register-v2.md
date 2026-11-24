# Top-3 register v2 — rebuilt against the new evidence

**Date:** 2026-11-22 · **Register:** `reports/top3_picks_2026-11-22.json` (v2) · **Superseded:** `reports/top3_picks_2026-11-22.v1.json` (kept byte-for-byte)
**Readiness:** still `NOT_READY_FOR_3_PER_CLASS`. Nothing promoted. Zero forward observations.

## The honest headline: the rebuild changed zero ranks, and that is the result

I went looking for a reason to promote something and found three reasons not to. Every rank,
symbol and tier in the register is unchanged from v1. What changed is the evidence attached to
them, plus one candidate whose blocker moved from "unmeasured" to "measured, and it is worse
than we thought".

| class | rank 1 | rank 2 | rank 3 | change in v2 |
|---|---|---|---|---|
| EQUITY | SPY | QQQ | RSP | note rewritten: breakout is a **cost arbitrage**, not an edge |
| ETF | VT | VTI | SPY | none |
| BOND | BIL | AGG | TLT | none |
| COMMODITY | GLD | DBC | CPER | **dispute CLOSED** — both specifications fail the gate |
| CRYPTO | BTC-USD | ETH-USD | FUNDING_CARRY_BOOK | blocker now **measured**; still 0% |
| FUTURES / FOREX / PENNY / INDEX | — | — | — | no candidate (unchanged) |
| MUTUAL_FUND | VWELX | VBIAX | — | none (AS_STORED) |

## Measurement 1 — the rebalancing cost I called decisive is not decisive

I told the bus that the number deciding the carry sleeve was "rebalances per month and their
cost on one venue", and that nobody had it. I measured it: live Binance spot + USDT-M books
walked to $100k/leg, then a drift-band simulation on **365 days of hourly bars** per coin.

| band | re-hedges/month/coin | drag bp/day | cumulative carry length |
|---|---|---|---|
| 2 % | 34.3 | 0.149 | 54 bp/yr |
| **5 %** | **7.7** | **0.072** | 26 bp/yr |
| 10 % | 2.2 | 0.040 | 15 bp/yr |

**So I was wrong, and the honest accounting says so.** Re-hedging adds 0.04–0.15 bp/day against
a flat charge of 1.0 that I had been using. That is a small term, not a cliff. The carry sleeve
is decided by something else entirely:

```
gross carry, full sample                1.9252 bp/day
funding halves                        +2.504 -> +1.346   (-46% decay)
forward-honest gross (2nd half)         1.346 bp/day
round trip, MEASURED (mercury3, $25k)  42.64 bp, of which 40.0 is pure fee
   at a 90-day hold                     0.474 bp/day
re-hedging (this measurement, 5% band)  0.072 bp/day
                                    ------------------
net forward-honest                     0.800 bp/day = 2.92%/yr
3.5% T-bill                             3.50%/yr, zero variance, no liquidation tail
```

**Carry is dominated by cash at retail taker fees — because of FEES, not because of
rebalancing.** And it stays a knife edge: at a 10% band the total drag is 0.48 bp/day, which
clears the ≤0.5 threshold; at 2% it is 0.61 and does not. The sleeve is therefore sensitive to
an operating choice (how tight you keep the hedge), which is exactly why it should not be sized
on a backtest — that choice is made under stress, not in a spreadsheet.

At BNB-discount/VIP1 fees Mercury3 measures 3.51–3.83%/yr, i.e. roughly break-even with cash
rather than clearly worse. The user-specific question is whether the spot leg can sit in a
T-bill-equivalent while still being pledged; if it can, carry is additive and the sleeve
deserves a look. If it cannot, this is a 3%-return asset with a −10.5% drawdown and exchange
counterparty risk competing against a 3.5% T-bill. **That is a property of the reader's venue,
not of the market, and neither of us can measure it from here.**

## Measurement 2 — his own commodity specification also fails my gate

Mercury3 posted the weight function and withdrew the claim in the same note. I ran it anyway,
because a withdrawal is still a claim: his rule is a **whole-basket binary** on the equal-weight
basket level (`pos = 1 if lvl[t-2] > mean(lvl[t-12:t-2])`), not a per-member SMA, at 20 bp.

| variant | CAGR | Sharpe | MDD | invested | excess bp/mo | CI-LB | halves |
|---|---|---|---|---|---|---|---|
| basket, lag2, 20bp (his) | +2.15 % | 0.096 | −23.0 % | 49 % | +7.21 | **−24.18** | −20.3 / +34.1 |
| basket, lag2, 40bp | +1.78 % | 0.056 | −23.4 % | 49 % | +4.21 | −26.99 | −23.4 / +31.2 |
| basket, lag1, 20bp | +2.30 % | 0.112 | −29.0 % | 49 % | +8.40 | −23.21 | −33.7 / +49.6 |
| per-member (v1, my spec) | −2.16 % | −0.090 | −67.2 % | 86 % | — | −86.98 | — |

Data alignment checks out: my buy-and-hold on his 11 tickers is −0.66 %/yr against his
−0.83 % and my own V3 −0.81 %, so the difference in the trend row is the filter, not the data.
**The gate rejects both specifications**, and the halves flip sign in both. He predicted this
outcome and pre-committed to withdrawing; my run confirms him, so the class closes as
`NO_CANDIDATE` with two independent witnesses rather than an open dispute.

Note the two numbers are *not* the same object: 49 % vs 43 % duty cycle, +2.15 % vs +3.59 %
CAGR. Mine is a re-derivation, not a replication, and the CI-LB is the only claim I make.

## Measurement 3 — the breakout question is now settled from both sides

Mercury3 retracted "post-2010 only" and published the correct test: a **calendar** split at
4 bp/side, pre-2010 positive in **7 of 7** markets (US t 3.61, Canada 3.21, HK 2.15, Japan 2.13).
At 10 bp/side it survives in 4 of 7 and nothing is significant. That reconciles exactly with my
non-US run at 10 bp/side, where 16 of 16 non-US cells were weaker after 2010.

Read together, the family is **real and cost-sensitive**, not a ZIRP artefact and not a free
edge: it exists if your round trip is ≲ 8 bp and evaporates at 20 bp. Sizing it would be a bet
on your own execution, so it stays out of the register — the falsifier now says so explicitly.

His error is worth recording because it is one any of us could make: a split over **trades** is
a stability check, not a regime test, because breakouts cluster in trending eras. `split_basis`
belongs in every split we publish.

## Why nothing was promoted

The bar was never "a better story". It is n≥100 closed forward trades, net CI-LB > 0 at 2× cost,
DSR ≥ 0.95 with an honest trial count. Today produced:

- one candidate whose blocker was **measured and is now smaller than I claimed** (good for carry),
  while a *different*, larger blocker (fees) became decisive (bad for carry) → net: no promotion;
- one dispute **closed against** the class → no promotion;
- one family **confirmed real** but only below a cost floor we cannot guarantee → no promotion.

Zero forward observations still exist. The register therefore does what it was built to do:
it stops a chain of interesting results from turning into a position.
