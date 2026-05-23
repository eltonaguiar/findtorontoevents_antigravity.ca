# BONDS — Asset Class Strategy Audit
**Date:** 2026-05-16 19:55 EST  
**Author:** Buffy (Codebuff)  
**Scope:** Forward-test performance, backtest, strategy gaps, data coverage

---

## 1. Forward-Test Performance

| Metric | Value |
|--------|-------|
| Total closed picks | 1 |
| Win Rate | 0.0% |
| Profit Factor | 0.00 |
| Avg PnL | −0.46% |
| Total PnL | −0.46% |

**Verdict:** ⚠️ **INSUFFICIENT DATA.** Only 1 forward-test pick. Cannot evaluate.

---

## 2. Backtest Performance

| Backtest | WR | PF | Max DD |
|----------|-----|-----|--------|
| `bond_duration_rotation_backtest.json` | 54.48% | 1.34 | 27.28% |
| `bond_tlt_ief_backtest.json` | 54.89% | 1.16 | 33.12% |
| `bond_credit_spread_overlay_backtest.json` | — | — | — |

**Verdict:** ⚠️ Marginal performance. 54-55% WR with 1.16-1.34 PF is better than random but below the 1.5 PF institutional threshold. Credit spread overlays may improve this.

---

## 3. Prediction Market & Copytrader Coverage

| Data Source | Covers BOND? | Status |
|-------------|--------------|--------|
| **Kalshi signals** | ✅ Yes | `alpha_engine/kalshi_signals.py` — Fed rate decisions, macro |
| **Polymarket signals** | ❌ No | Missing |
| **Multi-asset copytrader** | ✅ Yes | `copy_trader_intel/multi_asset_copytrader_scraper.py` |
| **Non-crypto consensus** | ✅ Yes | `copy_trader_intel/non_crypto_consensus.py` |

**Verdict:** ⚠️ Kalshi covers macro/fed events relevant to bonds. Polymarket does not cover bonds.

---

## 4. Strategy Gaps & Missing Data Sources

### What we HAVE:
- ✅ Duration rotation (TLT/IEF switching)
- ✅ Credit spread overlay
- ✅ Kalshi macro/Fed signals

### What we're MISSING:
- ❌ **Yield curve slope strategies** (2s10s steepener/flattener)
  - Free API: **FRED** (US Treasury daily)
  - Impact: Curve steepening/flattening is the #1 bond relative value trade
- ❌ **TIPS breakeven inflation strategies**
  - Free API: **FRED** (TIPS yields)
  - Impact: When breakeven > realized inflation by 50bps, short TIPS
- ❌ **Fed funds futures implied rate path**
  - Free API: **CME FedWatch** (scraping)
  - Impact: Market-implied rate path vs dot plot divergence = tradeable
- ❌ **Corporate bond OAS (Option-Adjusted Spread)**
  - Free API: **FRED** (ICE BofA indices)
  - Impact: Credit spread mean reversion is extremely reliable

### Highest-ROI gap to fill:
**CME FedWatch rate path** — free, scrapable, highly predictive. When market prices 3 cuts and dot plot shows 1, fading market pricing has been consistently profitable post-2022.

---

## 5. Statistical Edge Assessment

| Criterion | Status | Value |
|-----------|--------|-------|
| DSR (Deflated Sharpe) | ❌ | 1 closed pick — impossible to compute |
| PBO | ❌ | Not computable |
| Backtest edge | ⚠️ | 1.16-1.34 PF is marginal |

**Bottom line:** BONDS have no statistical edge yet. Backtests are borderline (PF 1.16-1.34) and forward-test data is nonexistent (1 pick). This is a low-priority asset class until at least 200+ forward-test picks accumulate.

---

## 6. Recommendations

1. **Generate more bond picks** — 1 pick is useless for validation. Configure scanner for bond signals
2. **Add yield curve steepener/flattener** — industry-standard bond strategy
3. **Integrate CME FedWatch** — free, high-predictive-value data
4. **Improve credit spread overlay** — mean reversion in spreads is reliable
5. **Do NOT trade bonds with real money** — insufficient data, marginal backtests
