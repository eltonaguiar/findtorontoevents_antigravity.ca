# Part 3 · P3-1: Strategy-Cell Ranking (closest to positive)

**Author:** GitHub Copilot / Mercury-3 AI (`githubcopilot-mercury3AI`)
**Date:** 2026-11-22 04:00 EST
**Source:** `audit3_ledger.json` `cells` (362 cells; 67 tested with n≥20)

---

## 1. What got tested

| Metric | Value |
|---|---|
| Total cells | 362 |
| Tested (n≥20) | 67 |
| WEAK | 59 |
| KILL | 8 |
| INSUFFICIENT_N | 295 |

All 67 tested cells carry verdict **WEAK** (keep observing) except the 8 KILLs. None is PROVEN/CANDIDATE — every cell fails at least one gate (most commonly DSR/overfit or net-CI-overlaps-zero).

---

## 2. Top 12 tested cells by net expectancy (%/trade)

| Rank | Class | Dir | Strategy | n | PF | DSR | Expectancy |
|---|---|---|---|---|---|---|---|
| 1 | CRYPTO | SHORT | strong consensus (alpha_engine, luxalgo) | 22 | 1265.5 | 0.9999 | +3.397 |
| 2 | CRYPTO | SHORT | macd_rsi_m048 | 24 | 2.84 | 0.321 | +3.026 |
| 3 | EQUITY | LONG | gap-and-go-stocks | 22 | 2.06 | 0.043 | +2.367 |
| 4 | CRYPTO | LONG | btc-4h-rsi-macd-scout | 35 | 2.15 | 0.157 | +2.005 |
| 5 | EQUITY | LONG | donchian-stock-breakout | 45 | 1.69 | 0.080 | +1.890 |
| 6 | EQUITY | LONG | vwap-reversion-scout | 26 | 1.68 | 0.033 | +1.804 |
| 7 | EQUITY | LONG | post-earnings-rev-scout | 21 | 1.84 | 0.033 | +1.332 |
| 8 | EQUITY | LONG | Breakout Momentum | 38 | 2.04 | 0.159 | +1.308 |
| 9 | FOREX | LONG | forex_rsi2_mean_reversion | 25 | 10.96 | 0.966 | +0.839 |
| 10 | EQUITY | LONG | rs-breakout-scout | 52 | 1.49 | 0.029 | +0.709 |
| 11 | CRYPTO | SHORT | ema_momentum_m006 | 21 | 1.46 | 0.024 | +0.664 |
| 12 | EQUITY | LONG | vol-contraction-scout | 62 | 1.31 | 0.016 | +0.641 |

---

## 3. Reading this correctly

- **The top cells are NOT promotable as-is.** They are WEAK because n<100 (or the class aggregate is KILL). E.g. rank-1 has n=22 and sits inside the CRYPTO KILL aggregate — the class-level kill overrides a cell that *looks* positive.
- **DSR tells the real story.** Only rank-1 (0.9999) and rank-9 (0.966) have DSR near the 0.95 threshold — the rest are far below (0.02–0.32), meaning high overfit risk. A high net expectancy with DSR 0.03 is not evidence.
- **Pattern:** the best cells are **EQUITY LONG breakout/momentum** (ranks 3,5,6,7,8,10,12) and **CRYPTO SHORT reversal** (ranks 1,2,11). These align with the audit2 pre-registered pod (EQUITY-BREAKOUT) and the CRYPTO SHORT confluence line.

---

## 4. Per-class "closest to positive" (for Part 2 forward focus)

| Class | Best cell (by DSR×expectancy) | What it needs |
|---|---|---|
| EQUITY | donchian-stock-breakout (+1.89, n=45) | n≥100 forward; 2× cost CI-LB>0 |
| ETF | rs-breakout-scout (+0.58, n=80) | n≥100; fix slippage model first |
| CRYPTO | strong consensus SHORT (+3.40, n=22) | n≥100; class kill must be reviewed first |
| FOREX | forex_rsi2_mean_reversion (+0.84, n=25) | n≥100; backfill fx_prices |
| COMMODITY | none positive | class is KILL |
| BOND | none tested | n<20 |

---

## 5. Recommendation

1. **Do not confuse "high expectancy" with "edge".** Gate n<100 and DSR<0.95 (overfit) before trusting any of these.
2. **Concentrate forward testing** on EQUITY breakout/momentum and CRYPTO SHORT reversal — the only coherent families with both positive expectancy and a defensible thesis.
3. **Review the class-KILL vs cell-positive conflict:** a positive SHORT cell inside a KILL CRYPTO class suggests the kill is driven by LONG emitters, not the whole class — the tribunal should segment kills by direction before extinguishing SHORT cells.

---
*Not investment advice. Data: audit3_ledger.json cells.*
