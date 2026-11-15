# BONDS

**Scan footprint:** 505 flagged files — non-trivial research, almost no trading.

**Closed-ledger measurement:**

| n | mean | median | WR | PF |
|---:|---:|---:|---:|---:|
| **28** | −0.23% | −0.76% | 35.7% | 0.56 |

**Verdict: INSTRUMENTED — NOT MEASURED.** n=28 is below any usable threshold. The negative PF is
not evidence against bonds; it is evidence the system has never traded them with a bond thesis.

**What has been tried:** duration timing (`reports/bond_duration_timing_backtest_2026-06-03.md`),
yield-curve slope strategies (`bond_yield_curve` 2026-05-12), 2s10s redesign
(`reports/h008_bond_2s10s_redesign_2026-05-18.md`), bond overlays with equity
(`reports/bond_overlay_attempts_20260513.md`), n-ramp analysis
(`reports/bond_n_ramp_analysis_2026-06-05.md`), deep dives 2026-05-31 and 2026-05-12.

**Why bonds are still the best *theoretical* candidate:** carry plus duration is a real,
documented premium; the data (FRED via `fredapi`, which is installed) is free and clean; the
timeframe is weeks-to-months, where this repo's daily-close machinery is actually adequate
(unlike its intraday picks).

**What is missing — everything empirical:**
- a fixed universe (TLT/IEF/SHY/LQD/HYG) with actual prices in the pipeline, not proxies;
- duration-adjusted excess vs a matched-duration benchmark, not vs SPY;
- a regime split on rate direction (cutting/hiking/hold) — the only regime that matters here;
- n ≥ 30 on a *thesis*, which means months of forward recording, not a backfill.

**Next experiment:** a carry/duration-timing hypothesis pre-registered in
`state/forward_test/plan.json` with a 6-month fixed sample, measured on excess vs IEF, before any
backtest. Nothing else in this class is worth running yet.
