# R4b — the only row the programme can still prove, and the clock is now armed

> **Corrected 2026-11-23 (trial count).** These documents originally cited "146
> pre-registered trials" as a settled number. Commit `487a165cb1b` withdrew it: it was
> never derived, and the only 146 in `reports/*.json` is `by_status.OPEN` — a pick-status
> tally, not a trial count. The contested set is 120 pre-declared / 108 in worktrees / 362
> scored cells (conservative bound) / 658 rejected as a unit error. The argument that
> backfilling is expensive does not depend on 146; it depends on the fact that the count is
> already large and rising.

**Date:** 2026-11-23
**Pre-registration:** `docs/preregistration/ETF_TREND_FORWARD_2026-11-23.md`
**Clock:** `tools/etf_trend_forward_clock.py`
**Tests:** `tests/test_etf_trend_forward_clock.py` (10 passed)
**Plan row:** R4b of `notes/per-asset-class-plan-copilot-2026-11-23`

---

## Why this row

Of the ten classes, ETF had the best measured risk-adjusted profile — **Sharpe 0.44,
max drawdown −25.9%**, the shallowest of any return-generating class, the **lowest
measured cost (1–2 bp)**, no short leg (so no borrow), and no FX in a USD account. It is
the only row where a small gross edge is not instantly eaten.

## The design decision that matters: forward only

The programme's trial count is **contested** — 146 is WITHDRAWN as never derived (C1/C2,
commit 487a165cb1b); 120 are pre-declared and 362 scored cells is the conservative bound.
**0/55 strategies survive
deflation** at SR\* = 1.014, σ_SR = 0.439. Every further backtest raises the bar for the
next one. HML demonstrated the trap today: 186 names, 44 months, gross **+0.11%/yr** — the
premium was absent, and no re-slicing of history will conjure it.

A family tested **once, forward**, keeps its trial count at 1, so its deflation bar stays
near nominal rather than inheriting the programme's accumulated trial debt. That is the only
remaining route
to a result that means anything.

## Frozen and cannot be re-tuned after the fact

- **Universe:** 20 ETFs, fixed now — `SPY QQQ IWM DIA EFA EEM TLT IEF SHY TIP TLH LQD HYG JNK GLD SLV XLE XLF XLK XLV`. Deliberately excludes narrow thematics (`ARKK`, `SOXX`): a theme ETF measures the theme's survival, not allocation skill.
- **Signal:** 12-month (252-day) return; hold **top 5 with momentum > 0**, rest to cash.
- **Rebalance:** monthly, last trading day. Equal weight. No shorts, no leverage.
- **Cost:** $0 commission (verified tariff), 2.385 bp half-spread per side (measured), 0.206 bp SEC on sales, 0 slippage (impact 0.008% of ADV). FX = 0 in a USD account — if conversion is forced the test is **VOID**, not failed.
- **Kill:** net annualised ≤ 4.32% **and** 95% upper bound ≤ 4.32%. Both, so we do not kill on noise.
- **Confirm:** 95% **lower** bound > 4.32%.

## The clock is mechanically unable to cheat

`--asof` refuses any date before `CLOCK_START`. Verified live:

```
$ python3 tools/etf_trend_forward_clock.py
::error:: refusing to record 2026-11-19 -- it precedes CLOCK_START 2026-11-23.
Backfilling converts trial count 1 into many and inherits the deflation debt (and the count
itself is contested — see the trial-count note above).
```

It also refuses to duplicate a date, stamps `created_at` itself (never from a caller),
and hash-chains each record via `prev_sha256`. A decision written before the outcome
exists cannot be quietly revised afterwards.

**The clock has not fired yet, and that is correct.** Cached data ends 2026-11-19, which
precedes the clock start; the first record will be the **November month-end**. `--stats`
reports `n_records: 0`, and no ledger file exists.

## A bug the tests caught before it shipped

I initially wrote the ledger line using `canonical()`, which **strips `sha256`** so the
record can be hashed. That meant every record would have been persisted *without its
hash* — the chain could never have been verified, and a tamper-evident ledger that cannot
verify is worse than none because it looks like evidence.

`serialize()` now writes the full record including `sha256`; `canonical()` is used only as
hash input. `test_record_on_disk_carries_its_own_sha256` pins it.

## An honest statement about how long proof takes

With ~10%/yr strategy volatility, the standard error of the annualised mean is ≈ 10%/√n
years. Getting a standard error as small as 4.32% needs **n ≈ 5.4 years**.

So the earliest possible CONFIRM is roughly **2031**. Any claim of proof before then is a
claim about noise. Saying so now, in the pre-registration, is the whole point — it stops a
good two-year run from being sold as an edge later.

## Signal sanity check (dry run, nothing recorded)

As of the latest cached bar (2026-11-19), the rule would hold:

| ETF | 12-month return |
|---|---|
| XLE | +37.6% |
| XLV | +18.2% |
| XLK | +15.8% |
| IWM | +14.3% |
| EFA | +10.1% |

Coherent tactical allocation (energy, healthcare, tech, small-cap, international). This is
a **dry run only** — recording it would be exactly the backfill the guard exists to
prevent.

## Next actions

1. ~~Wire a month-end trigger so a record is written on the last trading day of each month.~~
   **Done 2026-11-23.** `--month-end-check` records only once a month is provably complete (the
   cache must contain a date in a later month), and
   `.github/workflows/etf-trend-forward-month-end.yml` runs it Tue–Sat after the US close. The
   trigger is calendar-free, so it has no exchange-holiday dependency, and a daily run is a
   no-op until the month actually ends. Live check today: `latest provable month-end 2026-10-30
   precedes CLOCK_START 2026-11-23`, so the first record will be November's last session
   (**2026-11-30**, a Monday). See `updates/2026-11-23-etf-forward-clock-month-end-trigger.md`.
2. Interim review at 12 months: **INFO only**, no verdict.
3. Do not backtest this rule. Ever. A backtest makes it a different trial.

Zero capital sanctioned. Not investment advice.
