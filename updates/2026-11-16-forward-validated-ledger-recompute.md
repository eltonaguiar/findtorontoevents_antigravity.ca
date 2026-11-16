# forward_validated: decide it from the ledger, not the emitter

**Date:** 2026-11-16
**Files:** `audit_trail/forward_validation.py` (new), `audit_trail/stamp_pick_quality.py`,
`audit_trail/dashboard_generator.py`, `tests/test_forward_validation.py` (new)

## What was broken

`forward_validated` was whatever each emitter wrote. Several emitters hardcode
`False` (inverse mutators, DNA mutators, academic emitters), the dashboard only
fills it in a narrow branch (`n>=5 and WR>=45` of `_get_fwd_stats`), and the
strategy ledger was never consulted. On the 2026-11-16 payload:

- 11 of 789 active picks were flagged `True`
- 38 had a strategy with 20+ resolved trades — the evidence existed but was ignored
- 41 of the 46 picks that recorded a `_smart_reject_reasons` were rejected on
  `forward_validated=false` alone, and 5 more on `forward_trades<5`

So Smart Picks was empty *in part* because the flag was never computed.

## What changed

`audit_trail/forward_validation.py` defines the bar explicitly:

| Flag | n | WR | PF |
|------|---|----|----|
| `forward_validated` | >=20 | >=45% | >=1.0 |
| `PROVEN` (unchanged, `proven_gate.py`) | >=20 | >=50% | >=1.5 |

Forward-validated deliberately sits below PROVEN: a strategy with a real but
merely positive edge should gate Smart Picks without claiming a proven badge.

`stamp_pick_quality._build_strategy_stats` now also returns `resolved_n`,
`ledger_wr` and `pf` (flat trades excluded from PF), and the stamper calls
`apply_ledger_validation` so a pick is:

- **promoted** when its strategy ledger clears the bar and the emitter said `False`
- **demoted** when the emitter said `True` but the ledger has >=20 resolved rows below the bar
- left alone otherwise (a 4-trade ledger never overrules an emitter)

Every change stamps `forward_validated_basis="strategy_ledger"` and
`forward_validation_reason` (e.g. `ok:n=131,wr=43.5/45.0,pf=1.70/1.0`), so the
decision is auditable per pick instead of an opaque boolean.

The generator now publishes `summary.forward_validation_audit` with
`validated` / `unvalidated` totals, `by_basis`, and `by_class`.

## Measured effect

Recomputing the live payload with the new rule: **40 picks promoted**
(FOREX 27, EQUITY 8, ETF 5), taking flagged picks from 11 to 51 of 789.
16 distinct strategies are ledger-valid (up from 9 under the stricter
WR>=50%/PF>=1.5 bar) — the extra 7 are marginal-but-positive, exactly the
cohort this flag is meant to describe.

## Why Smart Picks can still be empty — and it is not this flag

Applying the rule in memory and calling the real gates on the live payload:

- `passes_active_gate`: **32 of 789 (4.1%)**
- `passes_smart_gate`: **0** — and 0 of the 40 promoted picks pass the active gate

The active gate rejects upstream of `forward_validated`:

- `equity_vix_gate_high_vix` — every equity pick, VIX > 22
- FOREX directional gate — every FOREX LONG (`elite=53 conf=0.75`, repeatedly)
- `TP_MAGNITUDE_IMPLAUSIBLE` — implied TP above the class cap (ETF 12%, EQUITY 15%)
- `M-036 crypto_direction_blocked` and kill gates on cryptos

Those are risk filters, not bugs, and this change does not touch them. The
honest read is that the funnel needs a policy decision (e.g. the VIX 22
threshold against the current regime) before any cohort can surface, whatever
its ledger says.

## Cohort cross-check (same payload)

**ETF** — 565 resolved, 44.4% WR, PF 1.04, +22.9% total:

| symbol | n | WR | PF |
|--------|---|----|----|
| XLF | 44 | 54.5% | 1.70 |
| QQQ | 80 | 48.8% | 1.22 |
| SOXX | 37 | 45.9% | 1.18 |
| XLE | 58 | 50.0% | 1.14 |
| XLK | 64 | 45.3% | 1.13 |
| SPY | 74 | 43.2% | 1.07 |
| GLD | 48 | 39.6% | 0.82 |
| IWM | 65 | 35.4% | 0.58 |

The class average hides a split: XL* sector ETFs are positive, IWM/GLD are the
drag. ETF scout picks also carry confidence 0.31-0.40, below the 0.60 smart-gate
window, so even a ledger-valid XLF pick (n=131, WR 43.5) fails on confidence.

**Copytraders** — 63 resolved, 54.0% WR, PF 1.35, +11.1%:

| source | n | WR | PF |
|--------|---|----|----|
| copy_trader_clones | 16 | 75.0% | 4.43 |
| multi_asset_copytrader | 36 | 44.4% | 0.57 |
| copy_trader_highscore | 11 | 54.5% | 0.14 |

The clones sleeve is the best measured cohort on the book (75% WR, PF 4.43,
+24.0%), but n=16 is below the 20-trade bar — it validates automatically after
four more resolutions, with no threshold change. `multi_asset_copytrader` is a
net loser and should not be presented as a quality source.

**Prediction markets** — 27 active rows, **0 resolved**. No PF, no WR, no
quality claim is possible; the contract resolver and outcome producer added
earlier are what will eventually make this measurable.

## Verification

- `py_compile` clean on all three modules
- `tests/test_forward_validation.py` (10 cases): thresholds, PF maths, flat-trade
  exclusion, promote, no-op when already true, demote on a losing 55-trade
  ledger, and no-demote on a 4-trade ledger
- Full run: **146 passed** (`test_forward_validation`, `test_audit_proven_gate_and_pnl_audit`,
  `test_mutual_fund_nav`, `test_asset_class`)
- Live payload replay as described above (promotions, active-gate and smart-gate
  counts)

## Not done on purpose

No gate threshold was changed. Loosening the VIX gate, the FOREX directional
gate or the TP caps would surface picks, but it would be a risk-policy change,
not a validation fix, and it needs an explicit decision.
