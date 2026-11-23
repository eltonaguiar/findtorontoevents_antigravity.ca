# EQUITY execution cost — measured, and the repo's two constants were both wrong

**Date:** 2026-11-23
**Tool:** `tools/equity_cost_hml.py` (read-only)
**Artifact:** `reports/equity_cost_hml.json`
**Unblocks:** blocker **B2** in `docs/preregistration/HML_VALUE_TEST_2026-11-22.md`

---

## Why this had to be measured

The HML pre-registration was blocked because EQUITY cost had never been measured.
Two constants in the repo disagreed by **5x**:

| Where | Value |
|---|---|
| `tools/measured_cost_recost.py` `ASSUMED` + `alpha_engine/cost_model.py` | 5.0 bp |
| `tools/pod_equity_breakout_backtest.py` `COST_BP_PRIMARY` | 25.0 bp |

With a 5x gap, "net of cost" was a choice of constant, not a measurement.

## Result

| Quantity | Value |
|---|---|
| names measured | **191** |
| daily bars | **238,810** (2021-11-22 → 2026-11-20) |
| 1-minute bars | **356,271** |
| Corwin-Schultz spread (median) | **0.77 bp** — usable on 65/191 names |
| Roll spread (median) | **4.77 bp** — structurally valid on 148/191 |
| high-low upper bound (median) | 209.63 bp (loose sanity bound only) |
| SEC fee (sell leg) | 0.206 bp |
| **round trip, conservative (Roll + SEC)** | **≈ 4.98 bp** |
| round trip, Corwin-Schultz + SEC | ≈ 0.98 bp |
| participation at $20k/name | **0.008%** of median ADV $251M |

**Both repo constants bracket the truth but only one is close.** Measured cost for
liquid S&P 500 names is **~1–5 bp round trip**. The 5.0 bp constant is therefore
about right for large caps; the **25.0 bp constant overstates by roughly 5x**.

Impact is negligible at this size (0.008% of ADV), so the cost is essentially all
spread, and spread is small for mega-caps.

## The Questrade tariff was mis-modelled in the repo — this was the real surprise

`alpha_engine/backtest/costs.py::CostModel.questrade_canada()` charges
`forex_fee_pct = 0.0175` on **every trade** (`price * shares * 0.0175`) and
`ecn_fee = 0.0035` per share. That is **175 bp per trade** plus ECN.

Verified against Questrade's own posted tariff (2026-11-23):

| Item | Repo model | Official questrade.com |
|---|---|---|
| Stock/ETF buy | 0 commission | **Free** |
| Stock/ETF sell | 0 commission | **Free** |
| ECN | $0.0035/share, every trade | **$0** on smart-routed orders (direct-routed only) |
| FX | **1.75% every trade** | 1.5%, **only on currency conversion**, and avoidable |
| SEC fee | absent | 0.0000206 × sell value |
| Commission min | — | none (the old $4.95–$9.95 tier is gone) |

Sources (both are Questrade's own pages, not third-party summaries):
`https://www.questrade.com/pricing/self-directed-commissions-plans-fees/transaction`
and `https://www.questrade.com/pricing-fees`.
Commissions table reads *"Stock Trade - Buy | Free"*, *"Stock Trade - Sell | Free"*.
ECN section: *"Orders for US securities: No ECN fees except…"* where the exceptions
all require **direct routed** orders.

Several third-party fee-comparison sites still publish the retired $4.95–$9.95
tier. They are **stale** and were not used.

**FX is the one term that can still destroy a strategy.** It is modelled at **0 bp**
because a dual-currency USD account avoids it — Questrade advertises dual-currency
as free. If a strategy is forced to convert, cost becomes **~151 bp**, which no
equity edge survives. The artifact records both, and `fx_sensitivity_if_not_avoided_bp`
is written into the JSON so the assumption cannot be silently lost.

## Two honest limitations, both written into the artifact

**1. Not point-in-time.** The ticker list is today's S&P 500, so it is
survivor-conditioned and skewed toward liquid names. Measured cost is therefore a
**lower bound** on a true PIT universe's cost. This was not assumed — it was
observed: `EA`, `DFS`, and `EQR` are in the list but returned *"possibly delisted,
no price data found"*, so they were dropped from the measurement. That is the
survivorship mechanism happening live.

**2. Time mismatch.** Spread is measured on the last ~5 trading sessions and applied
to a 2021–2026 backtest. Spreads have broadly compressed, so using current spreads
**mildly understates** historical cost. Minute bars are not available from the free
providers for older dates, so this cannot be back-filled.

## A dead end that is recorded rather than hidden

The first version measured Corwin-Schultz on **5 years of daily bars** and returned
**0.00 bp for 25/25 names** — every single estimate floored to zero. That is the
estimator failing, not free trading: on multi-year daily bars the volatility term
swamps the spread term for liquid large caps. Switched to 1-minute bars, where the
estimators are actually valid, and 65/191 names then produced a usable estimate.

Anyone re-running this must not use daily bars for spread on mega-caps.

## Verification

```
python3 tools/equity_cost_hml.py --limit 200
```
Reproduced n=191 / 238,810 daily bars / 356,271 minute bars. All figures above are
read directly from `reports/equity_cost_hml.json`.

Zero capital sanctioned. Not investment advice.
