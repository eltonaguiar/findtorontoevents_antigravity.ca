# A1 — the Questrade model charged 350 bp of FX per round trip

**Date:** 2026-11-23
**File:** `alpha_engine/backtest/costs.py`
**Tests:** `tests/test_questrade_cost_model.py` (13 tests)

---

## What was broken

`CostModel` and its `questrade_canada()` factory mis-modelled the broker in three
separate ways:

| # | Defect | Effect |
|---|---|---|
| 1 | `forex_fee_pct = 0.0175` applied **per trade** inside `compute_entry_cost()` | 175 bp on entry |
| 2 | `compute_exit_cost()` **called** `compute_entry_cost()` internally | the same 175 bp again on exit → **350 bp round trip** |
| 3 | `ecn_fee = 0.0035` charged per share | ECN on every trade |
| 4 | No SEC fee modelled at all | the one real per-trade charge was missing |

Against the measured round-trip spread of **~5 bp**, the model was overstating cost by
roughly **70x**.

## What the tariff actually says

Verified 2026-11-23 from Questrade's own pages
(`pricing/self-directed-commissions-plans-fees/transaction`, `pricing-fees`):

- Stock and ETF **buy = Free**, **sell = Free** — there is no per-share commission and
  no $4.95 minimum any more. Several third-party fee sites still print the retired
  $4.95–$9.95 tier; they are stale.
- **ECN = $0 on smart-routed orders.** The listed exceptions (EDGA/IEX/NASDAQ/BATS/ARCA/
  NYSE/EDGX) all require **direct routed** orders.
- **SEC fee = 0.0000206 × sell notional**, on **sales only**.
- **FX = 1.5%, only on currency conversion.** A dual-currency USD account avoids it
  entirely.

The 1.75% figure was also simply the wrong number (it is 1.5%), but the far bigger
error was applying it as if every equity trade were a currency conversion.

## The fix

- Extracted `_per_side_cost()` so entry and exit charge their legs **exactly once**.
  This removes the structural double-charge, not just the Questrade symptom.
- FX is **removed from the per-trade path** and given its own explicit
  `currency_conversion_cost(notional)` method — one-off, opt-in, documented.
- SEC fee added via a `sec_fee_rate` field, charged on the **sale** leg:
  - a **long** sells on **exit** → fee on exit
  - a **short** sells on **entry** → fee on entry
- Added `max_commission` (was missing; Questrade had a $9.95 cap back when it charged).
- `questrade_canada()` now takes its spread from the measurement rather than guesses:
  half-spread **2.385 bp** per side (from the measured 4.77 bp full spread) and
  **0 slippage**, because impact measured at **0.008% of median ADV** at $20k/name,
  i.e. under 1 bp.

## Proven result

```
questrade  round-trip $9.95  = 4.98 bp     (was ~350 bp)
ib         round-trip $35.20 = 17.60 bp    (unchanged)
```

4.98 bp is exactly `2 × 2.385 + 0.206 SEC` — the measured figure.

## Scope: this bug was inert, and that is worth stating

`questrade_canada()` has **zero call sites** in the main tree. `CostModel` itself *is*
load-bearing — `alpha_engine/backtest/__init__.py` re-exports it and
`alpha_engine/backtest/engine.py` imports it — but the engine defaults to
`CostModel.interactive_brokers()`, and `questrade_mode` defaults to `False`.

So no historical backtest result changes because of this fix. It is a correctness fix to
a branch that was never executed, not a change in any published number. Anyone tempted
to read the 350 bp → 5 bp drop as "costs just got cheaper for our strategies" should
stop: nothing that has been reported ever used this path.

## Guard rails

`tests/test_questrade_cost_model.py`, 13 tests, pins **both** directions:

- **IB parity** — entry, exit and round-trip costs equal the original formula exactly.
  This is the one that matters: `engine.py` uses IB, so if IB moves, production moves.
- no commission, no ECN, no per-trade FX
- `test_old_fx_bug_would_have_been_350bp` asserts the old figure was 350 bp **and** that
  the new round trip is single-digit bp, so the defect cannot quietly return
- SEC on sale only, verified separately for long and short
- `currency_conversion_cost()` is one-off and does not leak into trade costs
- `max_commission` cap; `zero_cost()` still all-zero

Wider regression: `pytest tests/ -k "cost or backtest or engine"` → **480 passed, 5
skipped, 0 failed**.

Zero capital sanctioned. Not investment advice.
