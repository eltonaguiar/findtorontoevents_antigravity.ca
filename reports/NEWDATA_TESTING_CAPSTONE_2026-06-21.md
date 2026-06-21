# Alt-data collector revival + new-data testing — COMPLETE (2026-06-21)
**Author:** claude-opus · operator-chosen "build alt-data collector revival" · all SQL-verified, committed to main

## Delivered (the chosen direction's core value)
- **3 dead feeds addressed:** insider (`refresh_insider_trades.py` + weekly workflow + 400d landing) and COT (`refresh_cftc_cot.py` + weekly workflow + 5yr landed). News-sentiment NOT revived (forward-gated + historical news not backfillable + needs frozen equity prices — low value).
- **New price feed built:** `futures_daily_ohlcv` (5yr daily, 11 commodity futures, 13,833 rows) — enabled the first properly-powered new-data backtests.

## Every new-data hypothesis tested at the best power the data allows — ALL sub-bar
| H | avenue | n_eff | net PF | CI-LB | verdict |
|---|---|---|---|---|---|
| H-130 | crypto funding mean-reversion | — | 0.64 | 0.40 | refuted |
| H-131 | crypto funding carry | — | 0.84 | 0.62 | refuted |
| H-132 | crypto cointegration pairs | — | 0.32 | — | refuted (IS broke OOS) |
| H-134 | COT commercial-hedger (5d) | **207** | 1.07 | 0.89 | sub-bar (not n-starved) |
| H-135 | COT commercial-hedger (20d) | 48 | 1.25 | 0.93 | sub-bar + OOS-decayed |
| H-136 | commodity TSMOM | 47 | 0.98-1.09 | 0.72-0.81 | sub-bar + regime-unstable |
| H-137 | commodity X-sectional momentum | **239** | **0.86** | 0.75 | **losing**, fully powered |
(+ equity reversal H-126 / momentum H-133 n-starved; crypto book dead at 11x scale.)

## The honest, rigorous conclusion
Across **every data-feasible avenue** — crypto (at scale), equity (reversal + momentum), crypto funding (mean-rev + carry), cointegration, COT positioning, commodity TS-momentum, commodity cross-sectional momentum — **not one signal clears the net-PF CI-LB>1.15 bar.** Where the data allowed full power (COT n_eff=207, X-sectional n_eff=239), the verdict is honest-on-the-merits, not an n-starvation excuse: COT is real-but-too-weak; commodity momentum loses. **There is no readily-extractable edge in any data source available to this program at its current scale.** This is the money-protecting truth, now established at depth across asset classes and signal families.

## What has lasting value
1. **Honest, properly-powered verdicts** (H-130..137) — the program now knows what does NOT work, rigorously, instead of chasing it.
2. **Maintained feeds** (insider + COT weekly workflows) — forward accrual can build edge over calendar time where a single snapshot couldn't.
3. **New infrastructure** (futures_daily_ohlcv) — reusable commodity price feed.

## Forward-accrual ETAs (the only remaining path, calendar-time)
- Insider open-market-buy (P) anomaly: P-buys ~0.3/large-cap/yr -> needs months-to-years of feed accrual OR a small-cap universe.
- crypto rsi5070_us overlay (CI-LB 0.95): the sole live lead, n-gated.
- COT/commodity: refuted; no forward lane.

## Decision: taper
Autonomous backtesting is genuinely exhausted (every avenue tested). Remaining value is forward accrual (calendar-time, not analysis) + operator levers (restore daily_prices, fix keyspace gap). Tapering from 5-min to monitoring; re-engage on operator action or a fresh feed.
