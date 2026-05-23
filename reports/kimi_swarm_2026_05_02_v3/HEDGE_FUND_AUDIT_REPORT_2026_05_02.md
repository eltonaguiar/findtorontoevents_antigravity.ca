# Hedge-Fund-Grade Audit Report
**Repository:** `eltonaguiar/findtorontoevents_antigravity.ca`  
**Date:** 2026-05-03 00:15Z  
**Auditor:** Kimi K2 + Claude Opus 4.7 cross-verification  
**Data source:** `audit_dashboard/data/dashboard_data.json` (n=3500 closed, 37 active, generated 2026-05-02T23:02Z)

---

## 1. Current Performance by Asset Class

**Tier Definitions:**
- **Tier 1:** PF > 2.0, WR > 55%, MDD < 10%
- **Tier 2:** PF > 1.5, WR > 50%, MDD < 20%
- **Tier 3:** PF > 1.2, WR > 48%, MDD < 30%

| Asset | 24h | 72h | 7d | 30d | Verdict |
|-------|-----|-----|-----|-----|---------|
| **CRYPTO** | T1 ✅ (PF 3.18, WR 61%) | T3 (PF 2.17, WR 56%, MDD 26%) | Below (PF 1.33, WR 45%) | Below (PF 1.36, WR 44%) | Diluted by volume |
| **EQUITY** | — | T1 (PF 38, WR 83%, n=6) | Below (PF 1.07, WR 49%) | T3 (PF 3.29, WR 62%, MDD 28%) | 7d weak, 30d strong |
| **FOREX** | T2 (PF 1.61, WR 57%, n=7) | Below (PF 0.46, WR 20%) | Below (PF 0.43, WR 17%) | Below (PF 0.79, WR 11%) | Structural, needs broader review |
| **COMMODITY** | — | Below (PF 1.73, WR 40%) | Below (PF 1.18, WR 20%) | Below (PF 0.81, WR 11%) | Thin volume, marginal |
| **ETF** | — | T1 (PF ∞, WR 100%, n=5) | T2 (PF 1.57, WR 63%) | T1 (PF 4.06, WR 78%) | **Best performing class** |
| **BOND** | — | — | — | — | No data |

### Key Insight: CRYPTO 24h/72h vs 7d Divergence
- **24h:** Tier-1 quality when top strategies dominate
- **7d:** Diluted by `quan_engine` (n=171, 18% of volume, PF 0.70) and `unknown` (n=66, PF 0.35)
- **Root cause:** Volume concentration — one strategy shouldn't exceed 15% of asset-class volume

---

## 2. Top Strategies by Asset Class (7d window)

### CRYPTO — Carrying the Asset
| Strategy | n | PF | WR | Tier | Notes |
|----------|---|-----|-----|------|-------|
| `strong consensus (alpha_engine, ml_crypto_pred)` | 105 | 2.34 | 60% | T1 | Core alpha generator |
| `st_fear_greed_contrarian` | 81 | 2.57 | 67% | T1 | Sentiment edge |
| `claude_ml_moderate_mut` | 30 | 2.46 | 60% | T1 | Model-based |
| `MeanReversionBB` | 23 | 3.97 | 70% | T1 | Mean reversion |
| `atr_percentile_gate` | 22 | 13.51 | 96% | T1 | Volatility edge |

### CRYPTO — Dragging the Asset
| Strategy | n | PF | WR | Action |
|----------|---|-----|-----|--------|
| `quan_engine` | 171 | 0.70 | 32% | **Cap volume or raise floor** |
| `unknown` | 66 | 0.35 | 14% | Investigate source |
| `ensemble` | 27 | 0.91 | 33% | Review conflation |

### EQUITY — Mixed
| Strategy | n | PF | WR | Action |
|----------|---|-----|-----|--------|
| `stocks_rsi2_pullback` | 14 | 0.89 | 36% | **Mutation review** — borderline |
| `mtf-align-scout` | 4 | 2.17 | 75% | Keep |
| `goldmine_5x_consensus` | 4 | 12.54 | 75% | Keep |

### FOREX — Below Tier-2
| Strategy | n | PF | WR | Action |
|----------|---|-----|-----|--------|
| `forex_rsi2_mean_reversion` | 52 | 0.13 | 14% | **Investigate** — mostly pre-#687 JPY picks |
| `non_crypto_consensus` | 18 | 2.26 | 72% | **Investigate** — zero edge per pick, 83% status WR |
| `fx_smart_carry_trade_momentum` | 8 | 0.24 | 13% | **Review** — carry trade misfit |

### ETF — Best in Class
| Strategy | n | PF | WR | Status |
|----------|---|-----|-----|--------|
| (various) | 36 | 4.06 | 78% | T1 across all windows |

---

## 3. Gate Framework Assessment

### Current Hard-Blocked Pairs (verified in `main`)

| Block Type | Pairs | Status |
|------------|-------|--------|
| Asset-Strategy | `forex_carry_momentum` (FOREX), `goldmine_6x_consensus` (EQUITY) | ✅ Active |
| Strategy-Symbol | `quan_engine` × `HYPEUSDT` | ✅ Active |
| JPY-Cross | All JPY crosses except USDJPY, direction=LONG/BUY/BULLISH | ✅ Active |
| GC=F Protection | Gold entry $800-$12000 | ✅ Active |

### Gate Health (Real-Time, 37 Active Picks)

| Check | Failures | Status |
|-------|----------|--------|
| Killed strategies in active | 0 | ✅ |
| JPY-cross LONG in active | 0 | ✅ |
| quan_engine + HYPEUSDT in active | 0 | ✅ |
| Trust-tier garbage | 0 | ✅ |

**Inflow is 100% clean. All gates working.**

### Proposed Unified Gate Framework

```yaml
# config/unified_gates.yaml
asset_classes:
  CRYPTO:
    max_strategy_volume_pct: 15      # No strategy > 15% of class volume
    min_pf_threshold: 1.2            # Auto-disable below T3
    min_wr_threshold: 48
    jpy_cross_buy_kill: true
    
  EQUITY:
    max_strategy_volume_pct: 15
    min_pf_threshold: 1.2
    min_wr_threshold: 48
    
  FOREX:
    max_strategy_volume_pct: 15
    min_pf_threshold: 1.0            # Lower bar (structurally harder)
    min_wr_threshold: 40
    jpy_cross_buy_kill: true
    
  ETF:
    max_strategy_volume_pct: 20      # Higher allowed (strong performance)
    min_pf_threshold: 1.5
    min_wr_threshold: 50
    
  COMMODITY:
    max_strategy_volume_pct: 15
    min_pf_threshold: 1.0
    min_wr_threshold: 35            # Lower bar (thin data)

strategy_health:
  evaluation_window_days: 7
  auto_disable:
    consecutive_windows_below_pf: 3
    pf_floor: 0.8
    wr_floor: 35
  
  mutation_review:
    trigger: "borderline"  # PF 0.8-1.2 or WR 35-48%
    action: "reduce_notional"  # Halve position size, not kill
```

---

## 4. Performance Gap & Biggest Drags

| Asset | Gap to Tier-2 | #1 Drag | #2 Drag |
|-------|--------------|---------|---------|
| CRYPTO | PF +0.17, WR +5.5% | `quan_engine` (PF 0.70, 18% vol) | `unknown` (PF 0.35, 7% vol) |
| EQUITY | PF +0.43, WR +1.5% | `stocks_rsi2_pullback` (PF 0.89, 42% 7d vol) | Small sample (n=33 in 7d) |
| FOREX | PF +1.07, WR +33% | `forex_rsi2_mean_reversion` (PF 0.13, 54% 7d vol) | `fx_smart_carry_trade_momentum` (PF 0.24) |
| COMMODITY | PF +0.32, WR +30% | Thin data (n=60 7d) | Low conviction |
| ETF | **Above Tier-2** | — | — |

---

## 5. Recommendations (Prioritized)

### Immediate (0-72h)
1. ✅ **JPY-cross fix deployed** (#687) — wait for pre-fix picks to age out of 7d window
2. ✅ **Toxic strategies killed** (#692) — `forex_carry_momentum`, `goldmine_6x_consensus`
3. ✅ **HYPEUSDT blocked** (#694) — concentration guard active
4. 📊 **Re-audit in 72h** — measure FOREX improvement post-JPY aging

### Short-Term (1-2 weeks)
5. **Cap `quan_engine` volume** — 18% of CRYPTO at PF 0.70 swamps Tier-1 strategies
6. **Investigate `non_crypto_consensus` FOREX** — 83% status WR but near-zero per-pick PnL. Copy-trader semantics (FORCE_CLOSED=50/114 in 30d) suggest it closes when source closes, not on TP/SL.
7. **Mutation review `stocks_rsi2_pullback`** — 36% WR in 7d but not catastrophic. Halve notional, don't kill.

### Medium-Term (2-4 weeks)
8. **Implement unified gate framework** (config above) — per-asset-class volume caps, auto-disable rules
9. **FOREX broader review** — if 7d PF < 0.6 after JPY aging, investigate strategy-fit for FX market structure
10. **Penny stocks / meme coins** — see §6

---

## 6. Penny Stocks / Meme Coins Integration Plan

### Penny Stocks (Equity sub-class)
- **Data source:** Add `yahoo_finance` penny stock screener (price < $5, volume > 1M)
- **Gate modifications:** 
  - Max position: 2% of portfolio (vs 5% for large-cap)
  - SL width: 8% (vs 3% for large-cap) — higher volatility
  - Minimum market cap: $50M (prevent pump-and-dump)
- **Strategy:** Adapt `stocks_rsi2_pullback` with wider SL, or create `penny_momentum_breakout` variant

### Meme Coins (Crypto sub-class)
- **Data source:** Add CoinGecko meme coin category + Twitter sentiment
- **Gate modifications:**
  - Max position: 1% of portfolio
  - SL width: 15%
  - Require confluence: 2+ of (social sentiment spike, volume breakout, exchange listing signal)
- **Strategy:** Create `meme_sentiment_momentum` — enters on social volume spike + 4h RSI < 30, exits on RSI > 70 or 48h hold
- **Risk:** Auto-disable if 3 consecutive picks SL-hit (meme coin rug-pull detection)

---

## 7. Data & Feature Audit Findings

| Data Source | Asset Classes | Freshness | Issues |
|-------------|---------------|-----------|--------|
| `yfinance` (OHLC) | CRYPTO, EQUITY, FOREX, COMMODITY, ETF | Real-time | Timeout stalls in `outcome_resolver.py` — fixed in #684 |
| `alpha_engine/ml_crypto_pred` | CRYPTO | Real-time | Core alpha generator, no issues |
| `forward_validator.py` | All | 15-min lag | WINNER_FILTER active, refutes Plan v2.1 claim |
| `cftc_cot` | FOREX, COMMODITY | Weekly | Retired in #683, migrated to PEAD cache |
| `coingecko` | CRYPTO | 5-min lag | Need for meme coin expansion |

**Leakage check:** No look-ahead bias detected. All features computed at pick emission time.

---

*Report generated 2026-05-03 00:15Z. All metrics derived from live dashboard data. Threshold=0.01% (1bp) for win/loss classification. Cross-verified with Claude Opus 4.7 methodology document.*
