# Part 4 · What Is Closest to "Worth the Risk"? (Backtests + Candidates + Stocks)

**Author:** GitHub Copilot / Mercury-3 AI (`githubcopilot-mercury3AI`)
**Date:** 2026-11-22 05:00 EST
**Sources:** `audit3_ledger.json` · `cost_adjusted_walkforward_backtest.json` · `equity_top3.json` · `growth_stock_picks.json` · **`STOCKSUNIFY2`** repo (algorithm research) · `equity_top5_long_short.json`.

---

## 0. Executive summary

**The single most defensible edge in the whole book is US large-cap momentum — but only as a PAPER forward test, not a live bet yet.** Everything else is either KILL, insufficient, or untestable due to stale data. None of the 4 named megacaps (MCD, NVDA, AAPL, MSFT) is an individual "pick"; they are all constituents of the momentum sleeve.

---

## 1. Per-asset-class risk-worthiness ranking

| Rank | Class | Verdict | Closest-to-worth-the-risk? |
|---|---|---|---|
| 1 | **EQUITY** | WEAK | ✅ **Yes — the only class with positive selection alpha (+0.11%) and the only cost-surviving backtest.** |
| 2 | **FOREX** | WEAK | ⚠ Has a DSR-0.966 cell (rsi2 mean-reversion) but data-blocked (`fx_prices` stale). |
| 3 | **CRYPTO** | KILL | ⚠ Class KILL, but a SHORT cell has DSR 0.9999 — direction-split review needed. |
| 4 | **ETF** | WEAK | ❌ Slippage (~234% of PnL) makes it untestable until cadence fixed. |
| 5 | **BOND** | WEAK | ❌ n=37, insufficient. |
| 6 | **FUTURES** | INSUFFICIENT_N | ❌ n=4. |
| 7 | **COMMODITY** | KILL | ❌ net −3.57%, worst in book. |

---

## 2. The qualifying-candidate scan (audit2/audit3 metrics worth double-checking)

**Cells that clear DSR (overfit) gate but fail n<100:**

| Cell | n | DSR | Net expectancy | What it needs |
|---|---|---|---|---|
| CRYPTO strong-consensus SHORT | 22 | **0.9999** | +3.40% | n≥100 + class-kill review |
| FOREX forex_rsi2_mean_reversion | 25 | **0.966** | +0.84% | backfill fx_prices, n≥100 |
| CRYPTO macro_m_rsi_m048 SHORT | 24 | 0.32 | +3.03% | n≥100 |
| EQUITY Breakout Momentum | 38 | 0.16 | +1.31% | n≥100 |

**The only n≥100 positive-expectancy cell:** CRYPTO `momentum_breakout` LONG (n=129, +0.63%, PF 1.18) — but DSR only 0.021 (overfit risk high).

**Moral:** no cell is simultaneously n≥100 + DSR≥0.95 + positive net. The closest to *qualifying* is **FOREX rsi2** and **CRYPTO SHORT consensus** — both are 1 fix (n accumulation / data backfill) from being real candidates.

---

## 3. Equity momentum — the one cost-surviving backtest

From `cost_adjusted_walkforward_backtest.json` (cost 20 bps/trade, 27 combos):

| Metric | Best variant (lb=6, skip=2, nL=3) |
|---|---|
| Win rate | 61.7% |
| Profit factor | **2.94** |
| Sharpe (annualized) | **1.30** |
| Total return (2015+) | ~3,699% (vs SPY B&H 359%) |
| Max drawdown | 29.5% |
| Cost | 20 bps/trade (included) |

**Warnings (why it is NOT money-ready):**
- Only **4/27 combos raw-pass T2**, and ~1.35 are expected to be false passes at α=0.05 (Bonferroni). → treat each variant as a *hypothesis*, not proof.
- It's a **backtest**, not forward evidence. Zero forward rows exist yet.

---

## 4. The named stocks — MCD, NVDA, AAPL, MSFT

**These are all in the 30-stock momentum universe** (`equity_top3.json`). They are not individual "stable" picks — they are rotating constituents:

- Recent top-3 longs (2026-03 → 2026-05): mostly **AVGO, GOOGL, NVDA, TSLA, ORCL, GS, JNJ** — NVDA appears (2026-03, 2026-05); **AAPL/MSFT/MCD have not been selected** in the recent tail (regime preferred other names).
- `growth_stock_picks.json` (2026-11-19) current picks: **REGN** (confidence 0.65, RS 93) and **ABNB** (0.62) — not among the 4 you named.

**Honest answer:** The system does not emit "MCD/NVDA/AAPL/MSFT" as stand-alone conviction picks. If you want those names specifically, the correct vehicle is the **12-1m (or 6-2m) momentum sleeve**, which will include them when they rank top-3 by momentum — not as a fundamental bet.

---

## 5. Profitable "small tweaks" (from STOCKSUNIFY2 research + our metrics)

Cross-research of `STOCKSUNIFY2/STOCK_RESEARCH_ANALYSIS.md` surfaced concrete, low-cost changes that map to our own weak spots:

1. **RSI Z-Score instead of raw RSI** (regime-adaptive) — directly upgrades our RSI-based reverse (which currently fail DSR).
2. **Volume Z-score trigger (V_z>2.0)** instead of a fixed 1.5× multiplier — flags institutional entries.
3. **Minervini Volatility Contraction Pattern (VCP)** check on Stage-2 uptrends — filters "loose" price action that causes late-entry failures.
4. **Residual momentum** (36m regression α + residual rank) — pure alpha, avoids momentum crashes from beta rotation. This is the single most promising "pure edge" tweak and aligns with our finding that most cells are beta-dominant.
5. **Quality-minus-Junk (QMJ)** factor for downside protection — would help the EQUITY sleeve's 29-35% drawdown.
6. **Correlation-spike regime detection** (ρ→1) in the Composite Engine — when all stocks move together, technical strategies fail; add a regime gate.

---

## 6. Recommendation (what I'd do)

1. **Paper-test the equity momentum sleeve NOW** (6-2m or 12-1m, top-3 longs, 20bps cost) as an auto-tracked simulated portfolio — this is the closest thing to "worth the risk", and the only way to earn the forward evidence it needs.
2. **Backfill FOREX prices** to unlock the DSR-0.966 cell; **backfill CRYPTO forward n** to unlock the DSR-0.9999 SHORT cell.
3. **Apply tweaks 1, 2, 4** (RSI Z, Volume Z, residual momentum) to the equity sleeve before/while paper-testing.
4. **Do not invest real money yet** — nothing is forward-proven; keep it paper until n≥100 forward rows clear the 2× cost gate.

---
*Not investment advice. All numbers from cited data files / repos.*
