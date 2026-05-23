# H-037 ETF VIX Term-Structure Carry — Verdict Summary

**Hypothesis ID:** H-037
**Asset Class:** ETF
**Family:** vix_term_structure_carry
**Status update:** TESTED → TESTED_WEAK
**Assessed:** 2026-05-20

---

## Backtest Summary

Signal: Buy SPY/sector ETF basket when ^VIX < ^VIX3M (contango = carry positive); short when ^VIX > ^VIX3M (backwardation).
Period: 2021-05-19 to 2026-05-11 (5-year window)
Hold: 5-day
Universe: 11 SPDR sector ETFs (XLF, XLK, XLE, XLV, XLI, XLY, XLP, XLU, XLB, XLRE, XLC)
Data source: yfinance ^VIX, ^VIX3M daily (free)

| Metric | Value |
|---|---|
| n (trades) | 1,185 |
| Win Rate | 58.9% |
| Profit Factor | 1.295 |
| Avg Win | +1.37% |
| Avg Loss | −1.52% |
| Carry Spearman | −0.096 |
| WF Efficiency | 0.75 |
| WF Admissible | True (3/4 folds) |

Walk-forward folds (WR per fold): 56.96%, 54.43%, 62.87%, 56.96%
Note: Fold 2 WR=54.43% is below the 55% fold threshold but 3/4 folds pass (≥ min_windows_admissible=3).

---

## Acceptance Criteria Evaluation

| Criterion | Threshold | Actual | Pass? |
|---|---|---|---|
| WF efficiency | ≥ 0.30 | 0.75 | PASS |
| Min windows admissible | ≥ 3 | 3/4 | PASS (borderline) |
| Same sign (all folds WR > 0.5) | True | True | PASS |
| Cost survival (net edge / gross edge at 5bps RT) | ≥ 0.60 | 0.73 | PASS |

At 5bps round-trip slippage (typical for liquid SPDR ETFs):
- Gross edge per trade = WR × avg_win − (1−WR) × avg_loss = 0.589×1.37 − 0.411×1.517 = +0.183%
- Slippage cost = 0.05% (5bps RT)
- Net edge = +0.133%
- Cost survival = 0.133/0.183 = **72.7% > 60% threshold** → PASS

All four formal acceptance criteria pass at 5bps round-trip slippage.

---

## Why TESTED_WEAK (Not TESTED_PASS)

Despite formally passing all four criteria, three structural concerns prevent a PASS verdict:

**1. Carry Spearman = −0.096 (near-zero)**
The carry signal (^VIX minus ^VIX3M slope) has almost no rank-correlation with subsequent 5-day returns. The positive WR likely reflects the broad bull-market regime bias in the 2021-2026 sample rather than the carry signal per se. This weakens the economic mechanism argument.

**2. Avg loss (1.52%) > Avg win (1.37%) — win-rate-driven edge**
The edge is entirely dependent on maintaining WR ≥ ~57%. If live WR regresses 3pp to 56%, profit factor falls to approximately 1.0. Win-rate-driven edges are fragile under distribution shift.

**3. Fold 2 WR = 54.43% (barely passing)**
The borderline fold is concerning. Minimum admissible passes by exactly one fold. A slightly different train/test split could flip the walk-forward to non-admissible.

**4. In-sample period is predominantly bull market (2021-2026)**
The contango signal works in low-vol regimes. The backtest covers only one sustained vol-compression period. COVID shock is excluded (starts 2021). True out-of-sample coverage of backwardation regimes is thin.

---

## Verdict

**TESTED_WEAK**

The hypothesis shows a real statistical signal but with fragile edge characteristics. The formal criteria pass at 5bps RT slippage, but the near-zero Spearman, inverted win/loss ratio, and bull-market sample bias all suggest the edge could be a regime artifact rather than a durable carry signal.

---

## Recommendation

**Opt-in sidecar shadow only. Do not wire to production pick generation.**

1. Collect live shadow data for 60 days: log contango/backwardation state daily alongside sector ETF 5-day returns
2. After 60 days: if live WR ≥ 56% and Spearman strengthens to < −0.20, re-evaluate for TESTED_PASS
3. Stop criteria: if live WR < 52% after n=50 live signals, promote to TESTED_KILL

**Position sizing guidance (if operator chooses to trade it):**
- Maximum 10% fractional Kelly
- Trade-level max size: 1% of portfolio per signal
- Only trade contango signals (long ETF basket). Do not trade backwardation short without separate validation.

---

## Sources

- `reports/hypothesis_registry.json` (H-037 entry, result populated 2026-05-19)
- Acceptance criteria: H-037 `acceptance_criteria` block in registry
- This assessment: 2026-05-20
