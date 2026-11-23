# Pre-registration — ETF trend/tactical-allocation overlay, FORWARD CLOCK only

**Date:** 2026-11-23
**Row:** R4b of `notes/per-asset-class-plan-copilot-2026-11-23`
**Status:** pre-registered. Clock starts at the first month-end after this date.
**This test is never backtested.** See §6 for why that is the whole point.

---

## 1. Why this row and not another

Our own measurements, not the literature:

| Class | Median vol | Max DD | Ret/yr | Sharpe |
|---|---|---|---|---|
| CRYPTO | 68.5% | −87.8% | −14.9% | −0.21 |
| EQUITY | 34.7% | −52.0% | +10.5% | 0.29 |
| COMMODITY | 24.6% | −41.1% | +5.7% | 0.22 |
| **ETF** | **16.2%** | **−25.9%** | **+4.4%** | **0.44** |
| FOREX | 8.8% | −16.1% | −0.2% | −0.03 |

ETF has the best risk-adjusted profile of any class we can measure, the shallowest
drawdown of any return-generating class, the **lowest measured transaction cost**
(~1–2 bp), no short leg (so no borrow), and no FX exposure in a USD account. It is the
only row where a small gross edge is not immediately eaten.

## 2. Frozen universe — 20 ETFs, fixed now

Equity: `SPY QQQ IWM DIA`
International equity: `EFA EEM`
Government bonds: `TLT IEF SHY TIP TLH`
Credit: `LQD HYG JNK`
Metals: `GLD SLV`
Sectors: `XLE XLF XLK XLV`

Deliberately **excludes** narrow thematic funds (`ARKK`, `SOXX`): a thematic ETF is a
single-idea bet, and a trend rule over themes measures the theme's survival, not
allocation skill. This list does not change. Adding a ticker later would be a new trial.

## 3. Frozen signal and portfolio

- **Signal:** 12-month (252 trading day) total return per ETF, computed from close prices
  as of the rebalance date. Total return is approximated by price return; dividend
  adjustments are acknowledged as a known small bias (INFO), identical for all names, so
  it does not drive the ranking.
- **Rank:** descending by 12-month return.
- **Hold:** the **top 5** ETFs whose 12-month return is **> 0**. If fewer than 5 are
  positive, hold only those that are.
- **Cash:** everything not held goes to cash, earning the hurdle proxy (T-bill).
- **Weighting:** equal weight across held names.
- **Rebalance:** monthly, on the **last trading day** of the month.
- **No shorts. No leverage.**

## 4. Cost treatment — measured, not assumed

- Commission: **$0** (verified Questrade tariff, buy and sell).
- Spread: **2.385 bp half-spread per side** (measured: 4.77 bp full spread median over
  n=191 names; ETF-only measured cost is 1–2 bp, so this is conservative).
- SEC fee: **0.206 bp on sales only**.
- Slippage: **0** — impact measured at 0.008% of median ADV at $20k/name.
- FX: **0**, assuming a USD account. If conversion is forced, cost becomes ~150 bp and
  the test is void, not failed — that must be reported as VOID.
- Cost is charged on realised turnover each rebalance.

## 5. Frozen kill / confirm rule

Evaluated **only** at the checkpoints in §7, against net annualised return on committed
capital and the **4.32%** hurdle (`tools/capacity_model.py: HURDLE_TBILL_APR = 0.0432`).

- **KILL** if net annualised ≤ 4.32% **and** the one-sided 95% **upper** bound ≤ 4.32%.
  Both conditions, so we do not kill on noise — an early point estimate below the hurdle
  with a wide interval is not evidence.
- **CONFIRM** if the one-sided 95% **lower** bound > 4.32%.
- **NEITHER** (the expected state for years): report as interval overlapping the hurdle,
  keep collecting, do not re-tune.
- A CONFIRM moves the family to forward observation — **it does not promote to
  INVESTABLE**.

## 6. Why forward-only, and why that is not laziness

The programme has spent **146 pre-registered trials** and **0/55 strategies survive
deflation** at SR\* = 1.014 with σ_SR = 0.439. Every additional backtest raises the bar
for the next one. HML demonstrated the trap live today: 186 names, 44 months, gross
+0.11%/yr — the premium was absent, and no amount of re-slicing history will conjure it.

A family tested **once, forward**, keeps its trial count at 1, so its deflation bar stays
near nominal instead of inheriting 146 trials of debt. That is the only remaining route to
a result that means anything.

**This also forbids the obvious cheat:** once the clock starts, we may not re-run the
signal on history and call it validation. Any backtest of this rule after today is a
different trial and inherits the full debt.

## 7. Checkpoints — and an honest statement of how long proof takes

With strategy volatility around 10%/yr, the standard error of the annualised mean is
≈ 10%/√n years. To get a standard error of 4.32% you need **n ≈ 5.4 years**. So:

| Checkpoint | When | What may be concluded |
|---|---|---|
| First record | next month-end after 2026-11-23 | positions only, no verdict |
| Interim | every 12 months | **INFO only** — no kill, no confirm |
| Earliest possible KILL | any month, if upper bound ≤ hurdle | decisively dead |
| Earliest possible CONFIRM | ~**60 months** | the interval can finally be tight enough |

**Stated plainly: this cannot be proven before roughly 2031.** Any claim of proof sooner
is a claim about noise. Recording that up front is the point of pre-registering.

## 8. What would make this VOID rather than failed

- Forced currency conversion (cost ~150 bp).
- The signal cannot be computed because a ticker stops trading (record and substitute per
  a rule fixed in advance: drop the name, do not replace it, note it).
- Fewer than 60 months of forward records exist but a verdict is demanded anyway.

## 9. Tamper-evidence

The forward clock appends a hash-chained record per rebalance, mirroring
`tools/provenance_ledger.py`: each record carries `created_at` (stamped by the recorder,
not by the caller), the signal values used, the resulting holdings, and `prev_sha256`.
A record written before the outcome exists cannot be revised afterwards without breaking
the chain.

Zero capital sanctioned. Not investment advice.
