# 2026-11-20 — Retraction: the "Sharpe 0.88 / MaxDD −19%" ETF TAA claim

**Type:** documentation correction (research integrity). No code changed.
**Author:** `copilot-cli-moneyresearch`.
**Goal advanced:** #1 — a false "verified edge" in the money-ready track was driving
the $2,000 allocation recommendation.

---

## What was broken

Four **verdict-grade** documents presented the ETF tactical-rotation / dual-momentum
edge as a *verified* result on the strength of the following figures:

> top5-6m rotation, 2007–2026: **Sharpe 0.88 vs SPY 0.74, MaxDD −19% vs −51%**,
> look-ahead-free, positive in all three time-thirds

That pairing **does not reproduce** on an honest execution lag. It is reproducible
only at *same-close* (lag-0) execution, which is what the originating backtest
effectively did despite describing itself as having 1-day entry timing.

The most damaging instance was not the headline report but the **"verification"**
row in `reports/QUICKWIN_STRATEGY_TEMPLATES_2026-10-19.md`, which stamped
`✅ verified` on the figure while only checking that it **appeared** in the source
report. That stamp is what caused every downstream doc to treat the number as
independently confirmed. It was never re-derived.

## What changed

Corrections added to the four docs that carried the claim as live:

| File | Change |
|---|---|
| `reports/money_maker_per_asset_class_2026-11-19.md` | New **§0 CORRECTION** block at the top; §2 row `CORROBORATED` → **`RETRACTED 2026-11-20`**; §4 point 1 re-stated (return trails SPY, DD cut is 38% not 63%) |
| `docs/CROSS_AGENT_PLAN_money_maker_2026-11-19.md` | Same §2-row correction, pointing at §0 above |
| `reports/QUICKWIN_STRATEGY_TEMPLATES_2026-10-19.md` | `✅ verified` → **`❌ RETRACTED 2026-11-20`**, naming the anti-verification defect; §5 bullet annotated |
| `reports/edition_review_2026-07.md` | Correction blockquote under the July-edition rationale, which rested entirely on the figure |

Deliberately **not** touched: historical session dumps (`2026-11-14/`, `2026-11-15_*`,
`ACTIONPLAN_AUDITPAGE/`, `AUDIT_ENSEMBLE_UPDATE_*`, the `KIMI_*` research folders).
Those are records of what was said at the time, not live verdicts; rewriting them
would falsify the archive.

## The measured numbers

All read from `reports/taa_settle_2026-11-19.json` (576 cells) and
`reports/TAA_LAGGED_REPRODUCTION_2026-11-19.md`, not from prose.

- **Pre-registered criterion** (written into `tools/taa_settle_sweep.py` *before* the
  run): ≥1 cell with lag=1, cost ≥5bps, Sharpe ≥0.88 **and** MaxDD ≥−19% over
  2007–2026 → **0 of 576 cells met it.** Verdict field: `NOT_REPRODUCED`.
- **Same 14-ETF universe, honest 1-day lag, 5bps/leg:** Sharpe **0.82** vs SPY 0.69,
  MaxDD **−20.9%** vs −52.9%, CAGR **8.94%** vs SPY **10.79%**. So: Sharpe edge
  **+0.13** (not +0.14), drawdown roughly right, **return trails SPY**.
- **Literal-claim reconstruction** (`sectors_11spdr` top5/lb6, lag=1, 5bps):
  Sharpe **0.727** / MaxDD **−44.55%** / CAGR 9.83%.
- **Best lagged cell, 2007–2026, ≥5bps:** Sharpe **0.795** / MaxDD **−41.67%**
  (`sectors_11spdr` top5 lb12).
- **What survives:** drawdown control. MaxDD **−50.78% → −31.61%** = a **38%**
  reduction (not 63%) for **−0.54%/yr** of CAGR. Real, cost-robust, worth having —
  but it is **risk control, not alpha**.

## Diagnosis: window artefact, not look-ahead

This distinction matters for whether the family is salvageable.

- Of the **85** cells that clear *both* bars (Sharpe ≥0.88 and MaxDD ≥−19%),
  **all 85 sit in the 2018–2026 window**, which excludes 2008.
- In **2007–2026**, **zero** cells clear both — not even at lag-0 / zero cost.
  (Best such cell: Sharpe 0.933 / MaxDD −24.01%; 0 of 288 pair Sharpe ≥0.88 with
  MDD ≥−19%.)
- Unlagged-vs-lagged max Sharpe across all cells is **1.127 vs 1.045** — ~7%
  inflation, i.e. mild.

So the number was not primarily produced by look-ahead; it was produced by a window
that dropped the one event the strategy exists to survive.

## One overreach corrected in the settlement report itself

`reports/TAA_SETTLE_2026-11-19.md` states the claimed Sharpe is *"0.085 above the
entire grid's maximum."* That is true only of the **lagged / cost-bearing** grid. Over
all 576 cells the 2007–2026 maximum is **0.933** (lag-0, 0bps). The conclusion is
unaffected — no 2007–2026 cell pairs Sharpe ≥0.88 with MaxDD ≥−19% — but the
sentence as written overclaims, and §0 of the corrected report states it precisely.

## How it was verified

```
# 1. the artifact, not the prose — verdict + criterion
python3 -c "import json;d=json.load(open('reports/taa_settle_2026-11-19.json'));\
print(d['verdict'], d['n_cells'], d['n_winners'], d['settle_criterion'])"
#   -> NOT_REPRODUCED 576 0 {'lag':1,'min_cost_bps':5,'min_sharpe':0.88,...}

# 2. the literal-claim cell, straight from the grid
#    filters: sectors_11spdr / top5 / lb6 / lag1 / 5bps / 2007-01..2026-11 / no abs.mom
#   -> CAGR 9.832  Sharpe 0.727  MDD -44.55

# 3. window split of the 85 double-clearing cells
#   -> {'2018-01..2026-11': 85}   (zero in the 2007 window)

# 4. residual stale claims after the edit
grep -n 'Sharpe 0.88' reports/money_maker_per_asset_class_2026-11-19.md \
  docs/CROSS_AGENT_PLAN_money_maker_2026-11-19.md \
  reports/QUICKWIN_STRATEGY_TEMPLATES_2026-10-19.md reports/edition_review_2026-07.md
#   -> only inside RETRACTED-marked rows / correction text
```

## Why this was worth fixing ahead of new work

A wrong number that is *marked CORROBORATED* propagates. This one had already reached
four verdict-grade docs and the July edition review's entire rationale, and it was
carrying the real-money recommendation. The `✅ verified` row that seeded it is the
generalisable lesson:

> **Verifying that a number appears in a source report is not verifying the number.**

Cheap to write, expensive to inherit. Any future "✅ verified" row should name the
command that re-derived the figure.
