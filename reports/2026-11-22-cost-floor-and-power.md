# Per-class cost floor and detection limit

**2026-11-22 · paper only · zero capital sanctioned · not investment advice**

`tools/per_class_cost_floor.py` → `reports/per_class_cost_floor_2026-11-22.json`, from the
40-cell sweep (`reports/per_class_edge_2026-11-22.json`).

## 1. How much cost can each class bear?

Treating CI-LB as locally linear in cost between 1× and 2×, the multiple at which it hits zero is
`k* = 1 + CI_LB(1×) / (CI_LB(1×) − CI_LB(2×))`; the cost floor is the base cost × k*.

| class | representative cell | CI-LB (bp/day) | cost floor | reading |
|---|---|---|---|---|
| FUTURES | H-218 xsmom_top2_6m | 0.186 | **18 bp (1.8×)** | cost binds immediately — already at the edge |
| MUTUAL_FUND | H-220 xsmom_top2_6m | 0.997 | 47 bp (4.7×) | thin, but not the binding problem |
| INDEX | H-221 xsmom_top2_6m | 1.613 | 73 bp (7.3×) | |
| ETF | H-205 xsmom_top3_6m | 2.007 | 165 bp (8.2×) | |
| CRYPTO | H-206 tsmom_6m_long_flat | 8.452 | 667 bp (16.7×) | not cost-bound — it is a beta proxy |
| EQUITY | H-201 xsmom_top3_6m | 7.246 | **614 bp (30.7×)** | cost is irrelevant; multiplicity is the problem |
| BOND, COMMODITY, FOREX, PENNY | — | negative | **already below floor** | no floor exists to report |

**6 classes bounded, 4 already below floor, 0 unbounded.** No cell is "free" in the sense of
being indifferent to cost — but the *scale* is wildly uneven: FUTURES dies at 1.8× the assumed
cost while EQUITY would need a 614 bp round trip before cost decided anything. A programme that
treats "cost" as one problem is measuring six different problems.

## 2. Could this sample have detected the effect it claims?

MDE on the daily mean at 95% confidence / 80% power, `2.8016 × σ_daily / √n_days`:

| class | MDE (bp/day) | CI-LB | at detection limit? |
|---|---|---|---|
| BOND | 1.98 | −0.453 | no (already negative) |
| FOREX | 2.50 | −0.520 | no (already negative) |
| COMMODITY | 2.60 | −1.324 | no (already negative) |
| MUTUAL_FUND | 4.27 | 0.997 | no |
| FUTURES | 4.32 | 0.186 | **yes** |
| INDEX | 4.63 | 1.613 | **yes** |
| ETF | 4.86 | 2.007 | **yes** |
| EQUITY | 7.17 | 7.246 | **yes — CI-LB ≈ MDE** |
| CRYPTO | 11.48 | 8.452 | **yes** |
| PENNY_STOCK | 19.73 | −8.636 | no (already negative) |

**18 of 40 cells have a CI lower bound below their own MDE.** For EQUITY the two numbers are
almost identical (7.246 vs 7.17): the "best cell in the programme" is sitting exactly at the
detection limit of a 14-year sample. That is the arithmetic behind the multiplicity failure —
DSR 0.9469 is not bad luck, it is what a genuine-but-small effect looks like when you give it
40 competitors and 3,600 observations.

## 3. How long would it take to detect a *tradable* effect?

Target = twice the cash hurdle = 1.92 bp/day.

| class | years of daily data needed |
|---|---|
| BOND | 15.8 |
| FOREX | 26.2 |
| COMMODITY | 27.2 |
| MUTUAL_FUND | 73.7 |
| FUTURES | 75.4 |
| INDEX | 89.7 |
| ETF | 95.5 |
| EQUITY | 207.5 |
| CRYPTO | 632.7 |
| PENNY_STOCK | 1572.2 |

This is the most useful number in the memo and it is not flattering. **If the effect is 1.92
bp/day, no daily-return backtest on 14 years of data can distinguish it from noise in any class
here.** The response is not more years — it is more independent observations per year, which
means event-driven sampling (the per-trade basis H-201 actually uses, n=179 trades) rather than
daily means, or a different question.

**Caveat on the representative cell rule.** The class representative is the highest CI-LB among
*admissible* cells (excluding `INSUFFICIENT_N` and `DATA_INTEGRITY_FAIL`). My first version
elected `H-200:NVDA` (n=13) as EQUITY's best on CI-LB alone — exactly the selection trap this
programme exists to catch — so the rule now refuses to promote an inadmissible cell and reports
`NO_ADMISSIBLE_CELL` instead.

**Caveat on CRYPTO.** The MDE is computed from the representative cell's volatility (43%). The
carry cell is far lower-vol, so its MDE is much smaller and this row does not describe the carry.
Mixing them is why the class table must never be read as "crypto is hopeless" — it says the
*high-vol momentum cell* is hopeless to detect, which is a different sentence.

**Caveat on the MDE itself.** It assumes daily independent observations. That is conservative for
autocorrelated strategies and optimistic for event-driven ones. It is a screen, not a verdict.
