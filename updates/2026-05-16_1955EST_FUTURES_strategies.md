# FUTURES — Asset Class Strategy Audit
**Date:** 2026-05-16 19:55 EST  
**Author:** Buffy (Codebuff)  
**Scope:** Forward-test performance, backtest, strategy gaps, data coverage

---

## 1. Forward-Test Performance

| Metric | Value |
|--------|-------|
| Total closed picks | 203 |
| Win Rate | 3.0% |
| Profit Factor | 0.06 |
| Avg PnL per pick | −0.03% |
| Total PnL | −5.37% |

**Verdict:** ❌ **WORST PERFORMING ASSET CLASS.** 3.0% WR is catastrophic — essentially every trade loses. The single strategy (`futures_momentum`) is fundamentally broken.

---

## 2. Top Performing Strategies (≥10 picks)

| Strategy | Picks | WR | AvgPnL |
|----------|-------|-----|--------|
| `futures_momentum` | 201 | 2.0% | −0.03% |

**Only one strategy** with enough data. It's terrible. No other strategies exist for futures.

---

## 3. Top Performing Symbols (≥5 picks)

All symbols are negative:

| Symbol | Picks | WR | AvgPnL |
|--------|-------|-----|--------|
| ZW=F (Wheat) | 25 | 0.0% | −0.02% |
| GC=F (Gold) | 25 | 0.0% | −0.02% |
| CT=F (Cotton) | 25 | 0.0% | −0.02% |
| KC=F (Coffee) | 25 | 0.0% | −0.02% |
| HG=F (Copper) | 25 | 0.0% | −0.03% |

**Note:** These are the SAME symbols that perform well under COMMODITY with COT positioning. The problem is the STRATEGY, not the symbols.

---

## 4. Backtest Performance

| Backtest |
|----------|
| `futures_ts_momentum_backtest.json` |

Only one backtest file found. It likely shows the same terrible performance.

---

## 5. Prediction Market & Copytrader Coverage

| Data Source | Covers FUTURES? | Status |
|-------------|-----------------|--------|
| **Kalshi signals** | ❌ No | Missing |
| **Polymarket signals** | ❌ No | Missing |
| **Multi-asset copytrader** | ✅ Yes | `copy_trader_intel/multi_asset_copytrader_scraper.py` |
| **Non-crypto consensus** | ✅ Yes | `copy_trader_intel/non_crypto_consensus.py` |

**Verdict:** ⚠️ Prediction markets don't cover futures. Copytrader covers but with what quality?

---

## 6. Strategy Gaps & Missing Data Sources

### What we HAVE:
- ❌ `futures_momentum` — broken, 2.0% WR
- ✅ Copytrader coverage (theoretical)

### What we're MISSING:
- ❌ **ANY working strategy** — this is a complete strategy vacuum
- ❌ **Term structure / contango-backwardation strategies**
  - Free API: **Barchart**, **CME** daily settlement
  - Impact: Futures term structure is the #1 edge in managed futures (CTA industry standard)
- ❌ **Roll yield harvesting**
  - Free API: Same as above
  - Impact: Short contango, long backwardation = structural positive carry
- ❌ **Cross-asset futures spreads**
  - Free API: Already have price data
  - Impact: Crude crack spread, gold-silver ratio, wheat-corn spread

### Highest-ROI gap to fill:
**Term structure (contango/backwardation)** — the ENTIRE managed futures industry runs on this. Short contango (sell expensive front month, buy cheap back month) generates positive carry. Free data from CME daily bulletins. This single strategy type would replace the 2.0% WR momentum approach entirely.

---

## 7. Statistical Edge Assessment

| Criterion | Status | Value |
|-----------|--------|-------|
| DSR (Deflated Sharpe) | ❌ | PF 0.06 — deeply negative |
| PBO | ❌ | Irrelevant when WR is 2% |
| Any edge at all | ❌ | None |

**Bottom line:** FUTURES has NO edge and NO working strategies. It should be PAUSED from live trading until term structure / roll yield strategies are implemented.

---

## 8. Recommendations

1. **IMMEDIATELY pause `futures_momentum`** — 2.0% WR is not recoverable
2. **Implement term structure strategy** — contango/backwardation detection is industry-standard
3. **Add roll yield harvesting** — structural positive carry from short contango
4. **Consider merging with COMMODITY** — the same symbols work under COT positioning
5. **Add cross-asset spread strategies** — crack spreads, gold-silver ratio
6. **Do NOT trade futures with real money** until completely rebuilt
