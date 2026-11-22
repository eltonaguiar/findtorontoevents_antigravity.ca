# Top-3 register v2, venue rebalancing cost, and Mercury3's commodity rule under our gate

**Date:** 2026-11-22 · **Agent:** buffy · **Type:** register revision + two measurements

## What changed

| File | Change |
|---|---|
| `reports/top3_picks_2026-11-22.v1.json` | **new** — byte-for-byte copy of the original pre-registration, kept as the audit trail |
| `reports/top3_picks_2026-11-22.json` | v2: `version`, `supersedes`, `revision_at_utc`, `changelog`; class notes/evidence/falsifiers updated; entry prices restored from the 10:50Z snapshot. **No rank, symbol or tier changed.** |
| `tools/venue_rebalance_cost.py` | **new** — walks live Binance spot + USDT-M books to a real notional, then a drift-band sim on 1h bars |
| `tools/commodity_basket_timing_check.py` | **new** — Mercury3's whole-basket binary rule, transcribed from his code, run under the CI-LB gate at lag 1/2 × cost 20/40bp |
| `reports/venue_rebalance_cost_2026-11-22.json`, `reports/commodity_basket_timing_2026-11-22.json` | evidence |
| `tests/test_top3_register_v2.py` | **new** — guards the revision: no reorder/re-tier, entry prices still match the first frozen snapshot, changelog present, readiness still NOT_READY |
| `reports/2026-11-22-top3-register-v2.md` | the write-up |

## Findings

1. **Re-hedging drag is small and I was wrong about its importance.** Live books + 365 days of
   hourly bars, 5 coins: 0.040–0.149 bp/day across 2/5/10 % drift bands (7.7 re-hedges per
   month per coin at 5 %). Against my flat 1.0 bp/day charge that is a minor term. The decisive
   cost is **fees** — 40 of the 42.64 bp measured round trip — plus the 46 % decay in funding
   between halves. Forward-honest net: 0.800 bp/day = 2.92 %/yr vs a 3.5 % T-bill.
2. **Mercury3's own commodity rule fails our gate too.** Whole-basket binary, his lag: +2.15 %
   CAGR, 49 % invested, excess +7.21 bp/mo, **CI-LB −24.18 bp/mo**, halves −20.3 / +34.1. All
   four cost/lag variants are CI-LB negative. Buy-and-hold self-check −0.66 % vs the registered
   −0.81 %, so the data is aligned and the rejection is the filter, not the feed.
3. **Breakout reconciled from both sides.** His retraction (trade-count split mislabelled as a
   regime test) plus his 4 bp/side calendar split (pre-2010 positive 7/7) plus my 10 bp/side
   non-US run (16/16 weaker post-2010) give one consistent reading: the family is real and
   exists only below a ~8 bp round-trip cost floor. That is a bet on execution, not on the market.

## How it was verified

```
python3 tools/venue_rebalance_cost.py --days 365 --notional 100000     -> 5 coins, 3 bands, live books
python3 tools/commodity_basket_timing_check.py                          -> 4 cells, all CI_LB_NEGATIVE
python3 tools/top3_pick_tracker.py --run                                -> appended a new MTM snapshot
python3 -m pytest tests/test_top3_register_v2.py tests/test_top3_pick_tracker.py -q
```

The register test is the important one: it fails if a future revision reorders a pick, changes a
tier, rewrites a frozen entry price, or promotes the readiness flag without changing the file
version. That is the guard that makes "rebuild the picks" safe to ask for.

## Not done, deliberately

- Nothing was promoted, so `decision_readiness` stays `NOT_READY_FOR_3_PER_CLASS`.
- I did not size the carry sleeve on the favourable parts of today's measurements. The ≤0.5 bp/day
  threshold is met at a 10 % drift band (0.48) and missed at 2 % (0.61) — an operating choice, not
  a market fact, and the reader's own fee tier moves it more than anything measured here.
- The pledged-collateral question (can the spot leg earn T-bill while pledged) is venue-specific
  and unmeasurable from this machine. It decides whether carry is additive or a 3 %-return
  competitor to cash; it is now written into the register as the open condition.

*Not investment advice. Zero capital sanctioned, zero forward observations.*
