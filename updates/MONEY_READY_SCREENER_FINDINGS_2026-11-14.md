# Money-Ready Screener Findings — 2026-11-14

**Repo:** eltonaguiar/findtorontoevents_antigravity.ca  
**Script:** `tools/money_ready_screener.py`  
**Data:** `recent_closed_array.json` (3,500 picks; 3,447 decisive WON/LOST; 53 non-decisive excluded)  
**Generated:** 2026-11-14  
**Results:** `updates/screener_results_2026-11-14.json`

---

## Bottom line: 0 of 166 strategy×class×direction cells pass all money-ready gates

No cell in the current data is profitable and statistically sound enough for real-money allocation. This is a **negative finding**, reported honestly rather than fabricated.

| Class | Cells | n (decisive) | WR | PF | Avg net expectancy | Passing cells |
|-------|-------|-------------|-----|-----|-------------------|---------------|
| CRYPCO | 67 | 2,069 | 45.7% | 1.31 | +0.385% | 0 |
| EQUITY | 44 | 680 | 48.2% | 1.23 | +0.486% | 0 |
| ETF | 32 | 503 | 44.3% | 1.07 | −0.165% | 0 |
| COMMODITY | 3 | 8 | 50.0% | 1.03 | +0.897% | 0 |
| FOREX | 9 | 159 | 40.3% | 0.66 | −0.528% | 0 |
| BOND | 10 | 27 | 33.3% | 0.56 | −0.342% | 0 |
| FUTURES | 1 | 1 | 0.0% | 0.00 | −0.675% | 0 |

**Every class fails** on at least one gate; most fail on several. No class has WR ≥ 50% or PF ≥ 1.5.

---

## Gate contract applied (all must hold)

| Gate | Threshold |
|------|-----------|
| n (decisive, TP/SL only; EXPIRED/CLOSED excluded) | ≥ 100 |
| Win Rate | ≥ 50% |
| Profit Factor (gross) | ≥ 1.5 |
| Net expectancy after slippage+fees | > 0, bootstrap CI lower bound > 0 |
| Max drawdown proxy | < 20% |
| Single-source concentration | < 60% |
| Multi-source confirmation | ≥ 2 independent sources |

Slippage (bps round trip): CRYPCO 15, EQUITY 10, COMMODITY 12, ETF 8, FOREX 5, BOND 8, FUTURES 10.

---

## Why the top cells still fail

The best-looking cells all fail on multiple gates:

| Cell | n | WR | PF | Net exp | Failing gates |
|------|-----|-----|-----|---------|---------------|
| `strong consensus (alpha_engine, quan_engine)` CRYPCO LONG | 10 | 40.0% | 43.45 | +26.94% | n<100, WR<50%, single-source=100% |
| `mega_mutation_macd_rsi_m048` CRYPCO LONG | 48 | 75.0% | 6.98 | +6.70% | n<100, **MDD=209.6%**, single-source=100% |
| `luxalgo_confluence` CRYPCO LONG (largest-n cell) | 563 | 44.0% | 1.24 | +0.03% | WR<50%, PF<1.5, **MDD=289.5%**, single-source=94% |
| `intermarket-flow-scout` ETF LONG | 97 | 48.5% | 1.18 | +0.03% | n<100 (3 short), WR<50%, PF<1.5, **MDD=173.8%**, single-source=100% |

Key observations:
1. **Every cell is single-source** (100% of picks from one `source_system`). No strategy has multi-source confirmation — the single-source gate fails on all 166 cells.
2. **Most cells have n < 100.** Only `luxalgo_confluence` CRYPCO LONG (n=563) clears the n gate, and it fails on WR, PF, MDD, and single-source.
3. **High-PF cells are outlier-driven, not robust.** Cells with PF > 5 (e.g., 43.45, 999.00) have n ≤ 4 and MDD near 0 simply because there's only 1–4 trades — statistically meaningless.
4. **Catastrophic MDD on positive-return cells.** `mega_mutation_macd_rsi_m048` (n=48, avg +6.7%) has MDD=209.6% — one bad run wipes out all gains and more.
5. **Net expectancy CI crosses zero** on nearly every cell — even where gross expectancy looks positive, it's not statistically distinguishable from zero after slippage.

---

## What this means

The system is **not real-money ready** across any asset class. This is consistent with the `money_ready_verdict.json` output (0/9 classes money-ready; `money_ready: []`).

The few positive readings are **multiple-testing / survivorship artifacts**, not a repeatable edge:
- High WR on tiny n (n=1–4) is chance.
- High PF on n < 5 is not statistically meaningful.
- Single-source dominance means the "edge" is a feed idiosyncrasy, not a class-level edge.
- EXPIRED/CLOSED picks (53 of 3,500) are correctly excluded here; counting them as WON would inflate WR (the previously-reported 78.93% CRYPCO "Smart Picks" cell was driven by this mislabeling).

---

## Path to a profitable approach (what's needed)

A cell would need to clear **all** of the following simultaneously to be considered:

1. **n ≥ 100 decisive picks** (currently only 1 of 166 cells clears this)
2. **WR ≥ 50%** with bootstrap CI not crossing 50%
3. **PF ≥ 1.5** gross, net of slippage
4. **Net expectancy > 0** with 95% CI lower bound > 0 after slippage+fees
5. **MDD < 20%**
6. **Multi-source**: ≥ 2 independent `source_system`s, no single source > 60%
7. **Regime-direction consistency**: no LONG in RISK_OFF (CRYPCO LONG is blocked by `config.py:447`)
8. **Recency**: data/picks < 48h old

None of the 166 cells currently meets even a majority of these. The honest next steps are **not** to paper over the gap with a tweaked threshold, but to:

1. **Fix data hygiene** (EXPIRED→WON relabeling, frozen journal, stale DB, dead price refresh) so the ledger is trustworthy and current.
2. **Generate multi-source confirmation** — the same signal must fire from ≥ 2 independent, non-correlated sources before a pick is emitted.
3. **Run walk-forward / out-of-sample validation** (CPCV) on survivors, requiring ≥ 2 strategies with n ≥ 20 each before PBO/SPA/FDR can even run.
4. **Only after** a cell passes all gates in paper trading (n ≥ 100 clean post-noise trades) consider real money.

Until then: **no allocation.** The gates correctly return "no passing cells," and that is the correct answer.

---

## Reproducing

```bash
python3 tools/money_ready_screener.py --data recent_closed_array.json
```

Emits a pass/fail table for all 166 cells. With `--json`, writes a machine-readable report.
