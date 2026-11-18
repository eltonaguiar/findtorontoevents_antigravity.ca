# BONDS_EDGE_VERDICT_2026-11-17

**Source:** ejaguiar1_stocks proxy (bonds DB 1045-blocked)
**Symbols:** TLT, IEF, AGG, SHY, TIP, HYG, LQD, BND, GOVT, MUB, JNK, EMB
**Tables:** trading_picks, at_pick_outcomes, at_signal_outcomes, at_raw_picks (WON/LOST only)
**Method:** Win/loss classified by pnl_pct sign (>0 win, <0 loss, =0 dropped); combined across all tables
**Total bond rows with pnl:** 785

## Qualified configs (n>=30, PF>=1.25)

| Symbol | Strategy | Direction | n | Wins | Losses | Win Rate | Profit Factor | Avg Win | Avg Loss | Max DD |
|--------|----------|-----------|---|------|--------|----------|---------------|---------|----------|--------|
| IEF | bond_yield_curve_slope | LONG | 108 | 39 | 69 | 36.1% | **1.35** | 0.837 | 0.349 | 7.74 |
| TLT | cta_cross_asset_tsmom | SHORT | 57 | 45 | 12 | 78.9% | **128.53** | 2.344 | 0.068 | 0.04 |
| IEF | cta_cross_asset_tsmom | SHORT | 34 | 32 | 2 | 94.1% | **183.66** | 0.451 | 0.039 | 0.00 |

## Verdict

**EDGE** — 3 configurations meet n>=30 and PF>=1.25 thresholds.

---

## Top configs by n (n>=10)

| Symbol | Strategy | Direction | n | Win Rate | Profit Factor | Avg Win | Avg Loss | Max DD |
|--------|----------|-----------|---|----------|---------------|---------|----------|--------|
| IEF | bond_yield_curve_slope | LONG | 108 | 36.1% | **1.35** | 0.837 | 0.349 | 7.74 |
| TLT | bond_yield_curve_slope | LONG | 60 | 18.3% | 0.25 | 0.927 | 0.832 | 30.56 |
| TLT | cta_cross_asset_tsmom | SHORT | 57 | 78.9% | **128.53** | 2.344 | 0.068 | 0.04 |
| HYG | bond_yield_momentum | LONG | 55 | 16.4% | 0.09 | 0.219 | 0.473 | 19.80 |
| TLT | bond_tlt_ief_v3 | LONG | 37 | 10.8% | 0.08 | 0.471 | 0.676 | 20.44 |
| IEF | cta_cross_asset_tsmom | SHORT | 34 | 94.1% | **183.66** | 0.451 | 0.039 | 0.00 |
| EMB | bond_yield_momentum | LONG | 29 | 31.0% | 0.06 | 0.428 | 3.022 | 56.58 |
| JNK | bond_yield_momentum | LONG | 27 | 22.2% | 0.02 | 0.223 | 3.026 | 62.21 |
| LQD | bond_yield_momentum | LONG | 26 | 0.0% | 0.00 | 0.000 | 0.772 | 20.07 |
| TLT | bond_mean_reversion | LONG | 22 | 45.5% | 0.80 | 0.472 | 0.492 | 1.95 |
| MUB | bond_yield_momentum | LONG | 19 | 15.8% | 0.01 | 0.051 | 1.793 | 28.54 |
| TLT | bond_yield_curve_slope | SHORT | 16 | 18.8% | 0.15 | 0.549 | 0.857 | 9.87 |
| EMB | bond_mean_reversion | LONG | 16 | 37.5% | 0.06 | 0.195 | 1.859 | 17.42 |
| TLT | cta_golden_cross_200 | SHORT | 12 | 91.7% | 5421.71 | 1.725 | 0.004 | 0.00 |
| IEF | bond_yield_momentum | LONG | 12 | 0.0% | 0.00 | 0.000 | 0.547 | 6.56 |
| IEF | bond_yield_momentum | SHORT | 12 | 0.0% | 0.00 | 0.000 | 0.283 | 3.40 |
| IEF | bond_mean_reversion | LONG | 10 | 80.0% | 2.11 | 0.205 | 0.388 | 0.00 |

---

**Verdict:** EDGE
