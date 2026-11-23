# G1–G5 pick gate engine + per-symbol rankings (0 PASS — hold-time input missing)

**Date:** 2026-11-23
**Worktree:** vanilla-handsaw
**Author:** Kilo (orchestrator)
**Files:**
- `tools/pick_gate.py` — G1–G5 gate engine, measured cost inputs
- `tools/build_asset_class_rankings.py` — per-symbol ranked picks from the ledger
- `reports/asset_class_rankings.json` — generated output

## Gates implemented (per the human's spec)
| Gate | Rule | Measured input |
|---|---|---|
| G1 | gross edge > 2× measured round-trip cost | spread 6.04 bp/side = **12.07 bp RT** (13 names) + IBKR commission |
| G2 | survives holding ≥ 1 day | requires `hold_days` per pick |
| G3 | deflated Sharpe **with trial count stated** | `dsr` + `dsr_n_trials` (global max = 658) |
| G4 | return on **committed capital incl. cash collateral** vs **4.3% T-bill**, not notional | annualised net bp / 10000 × trades-per-year |
| G5 | pick recorded before outcome | `pre_recorded` flag |

Every pick carries `n`, `net_bp`, `kill_rule`, and the exact `ticket_usd` used for its bp figures.

IBKR commission is NOT scale-invariant: **11 bp/side at $1k, 0.4 bp/side at $25k** — every bp figure in the output states its ticket size.

## Result: 0 PASS / 69 FAIL
Every one of 69 per-symbol picks fails. The gate engine is correct; the failures are unanimous on the same two roots.

## Reported disagreements (plan/ledger vs measurement) — NOT adjusted to match
1. **Cost understated in ledger.** Ledger assumes EQUITY cost = **5.0 bp**. Measured RT = **12.87 bp** at $25k (2.57× larger). G1 uses the measured cost.
2. **`hold_days` absent from the ledger.** Neither `cells` nor `symbols` publishes `hold_days_mean/median`. Therefore:
   - **G2 is unmeasurable** → labelled FAIL:G2 on every pick.
   - **G4 = 0.0%** because holding_days=0 → annualisation is zero → cannot beat 4.3% T-bill.
   This is the single missing input blocking any PASS.
3. **`symbol = None` on cells.** Cells are strategy×class aggregates; the per-symbol names exist only under `symbols` (69 entries). The earlier draft that ranked `cells` mislabelled every pick with its class name — corrected to rank `symbols`.

## Top EQUITY (by net_bp, all FAIL)
| Symbol | n | net_bp @$25k | DSR (trials) | verdict |
|---|---|---|---|---|
| CVX | 35 | 163.06 | 0.318 (658) | FAIL:G2,G4,G5 |
| AMD | 83 | 103.21 | 0.033 (658) | FAIL:G2,G4,G5 |
| AMC | 22 | 68.47 | 0.004 (658) | FAIL:G2,G4,G5 |

## Top ETF (by net_bp, all FAIL)
| Symbol | n | net_bp @$25k | DSR (trials) | verdict |
|---|---|---|---|---|
| SOXX | 37 | 18.39 | 0.004 (658) | FAIL:G2,G4,G5 |
| XLE | 61 | 12.40 | 0.007 (658) | FAIL:G1,G2,G4,G5 |
| XLF | 48 | 6.36 | 0.010 (658) | FAIL:G1,G2,G4,G5 |

## Missing input (blocks END-GOAL B/C)
A **holding-period feed** (entry→exit days per symbol) so G2 and G4 can be computed. Without it, no pick can be honestly ranked as money-ready. This is a data gap, not a code gap — the gate will accept hold_days the moment the ledger publishes it.

## Verification
```
python3 tools/build_asset_class_rankings.py --ticket-usd 25000
# rankings written: reports/asset_class_rankings.json (69 picks, 0 PASS, 69 FAIL)
python3 -m pytest tests/test_assert_surface_parity.py -q   # 2 passed
```

*Nothing here is investment advice. 0 picks pass all five gates. Do not put real money in.*
