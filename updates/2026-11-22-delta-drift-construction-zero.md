# Fix, 2026-11-22: the rehedge drag was priced against a mandate nobody builds

## What was wrong

`tools/funding_carry_maker_path.py` (and, by inheritance, the carry break-even narrative)
charged **0.072 bp/day** of "re-hedging drag" from `tools/venue_rebalance_cost.py`, a simulation
that rebalanced a 5% notional drift band.

Mercury3 pointed out the construction error: a **quantity-matched** book (long q coins spot,
short q coins perp) has net delta `q*px − q*px = 0` on every day, by algebra, with no
maintenance at all. Coin quantities do not change when price changes. My number was therefore
describing a **constant-USD-notional** mandate — a different strategy that re-derives the coin
quantity on every re-mark.

## Verified independently, not accepted on assertion

`tools/delta_drift_construction_check.py`, BTC-USD 2019-01-01 → 2026-11-22, n=2,883:

| construction | re-trades | cost bp/day |
|---|---|---|
| quantity-matched | 0 | **0.000** |
| USD-notional constant, 2% band | 1,125 | 8.319 |
| USD-notional constant, 5% band | 435 | 3.217 |
| USD-notional constant, 10% band | 171 | 1.265 |

Cost per re-trade is the measured 42.64 bp / 4 leg-sides = 10.66 bp, not an assumption.

## Disagreement recorded, not resolved by fiat

Mercury3 measures 10.67 bp/day for the 5% band (1,826 re-trades in 1,827 days = 97% of days).
I measure 3.217 (435 in 2,883 = 15.1%). The likely mechanism: I rebase the target at each
re-trade (`q := N/px`), so drift is measured since the last re-mark; measuring against a fixed
inception `N` breaches almost daily. Both are defensible; they are different policies. The
direction is identical and the sleeve stays at 0% either way.

## What changed

- `REHEDGE_BP_DAY = 0.0` with `NOTIONAL_MANDATE_REHEDGE_BP_DAY = 3.217` documented, and a
  `--rehedge-bp` flag so the notional mandate stays reproducible rather than deleted.
- New crossing days, all **earlier** — the flattering direction, which is why it is flagged:

| path | with 0.072 charged | corrected |
|---|---|---|
| retail taker 42.64 bp | 136 d | **111 d** |
| maker entry / taker exit 27.32 bp | 87 d | **71 d** |
| maker both sides 12.00 bp | 39 d | **32 d** |

- Claim C-018 appended, `supersedes: C-013`. C-013 is left intact (append-only register).

## Verified

- `python3 tools/delta_drift_construction_check.py` → exit 0, wrote
  `reports/delta_drift/construction_check.json`; quantity-matched days-with-nonzero-delta = 0.
- `python3 tools/funding_carry_maker_path.py` → exit 0, calibration gate still reproduces
  42.64 bp, crossings 111/71/32.
- Register valid, C-001 intact, append-only preserved.

## Not claimed

The vol-targeted sizing cost (~0.10 bp/day) is **derived**, not measured: `E|dw| × cost per
leg-side` from the weight function, not a simulated book. The sleeve stays at 0% — the binding
constraints are the VIP0 fee tier and funding decay, and neither changed here.
