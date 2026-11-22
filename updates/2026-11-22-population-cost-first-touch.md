# Full-population cost audit + honest first-touch with real bars — 2026-11-22

Two follow-ups on the ledger's honesty, plus one correction to my own earlier work.

## 1. Full population, not the 3,500 recent window

`reports/2026-11-22-population-cost-audit.{json,md}` from
`tools/population_cost_audit.py`, reading the canonical
`pf_registry.json::by_asset_class_policy_clean` class rows (the authoritative
aggregates), with the 20/10/10/8/12 bp round-trip cost model.

| class | n | PF gross | PF net (approx) | exp gross % | exp net % | breakeven cost bp |
|---|---|---|---|---|---|---|
| CRYPTO | 22,864 | 0.2656 | −0.3635 | **−0.0464** | −0.2464 | −4.6 |
| FOREX | 468 | 0.1778 | −0.2361 | −0.0275 | −0.1075 | −2.8 |
| EQUITY | 217 | 0.6206 | −0.1222 | −0.0159 | −0.1159 | −1.6 |
| COMMODITY | 35 | 0.3528 | −0.2749 | −0.0156 | −0.1356 | −1.6 |
| ETF | 32 | 1.8846 | 0.4662 | +0.0499 | −0.0501 | +5.0 |
| FUTURES | 17 | 1.3519 | −0.2995 | +0.0041 | −0.1159 | +0.4 |

**The full population is negative GROSS.** CRYPTO loses 0.0464% per trade before
any cost, PF 0.2656 over 22,864 picks — matching the peer's 0.26 and confirming
that the 1.313 I quoted from the 3,500-pick window was window selection.

**Disclosed defect in the first version of this tool:** I initially aggregated
`by_asset_class_strategy_date` (25,289 cells) and got CRYPTO n=24,888 / PF 0.2346.
That view does **not** reconcile to the class row (n=22,864, gp 376.39, gl
1456.03): no combination of the per-cell policy flags brings it under 24,559, so
it over-counts by 1,695+ picks. The tool now defaults to the class rows and the
cell view is not used for any published number.

Expectancy under a uniform cost is exact; net PF is an approximation that holds
while every winner exceeds the cost, so net PF is slightly optimistic; net WR is
an upper bound. Stated in the report.

## 2. Honest first-touch, with real bars

`tools/ohlc_bars.py` (Binance public klines, no key, 6h cache in `/tmp`) +
`tools/first_touch_resolve.py`: walks daily bars from `entry_time` to
`closed_at`, re-derives which of SL/TP was touched first, and applies the
conservative rule **SL wins a same-bar tie**.

Coverage: 62 symbols, 60 fetched (GLD/IWM rejected — not Binance pairs), 1,717 of
2,070 CRYPTO picks resolved; 204 had no `entry_time`, 104 no bars, 43 neither
level hit.

| measure | recorded | honest re-walk |
|---|---|---|
| n | 1,717 | 1,717 |
| win rate | 46.1% | 47.8% |
| profit factor | **1.367** | **1.479** |
| expectancy % | +0.6160 | +0.6050 |

**922 of 1,717 exits (54%) have a first-touch level different from the recorded
reason**, 689 of them same-bar ties forced to SL. Yet honest PF is *higher* than
recorded (ratio 0.924) and expectancy is flat (−0.011 pp).

That is a real negative result against my own framing: the ~2× inflation H-120
measured does **not** reproduce on crypto. H-120's ratios (2.09× COMMODITY,
1.18× FX) came from re-resolving specific daily-resolution strategies; crypto's
TP/SL book is not inflated by exit-order mislabeling — if anything the recorded
exits are slightly worse than the bars imply. Residual limits: daily bars cannot
order two intrabar touches, ties are resolved conservatively to SL, and Stooq is
unusable (JS challenge) so EQUITY/ETF first-touch is still open.
