# Finding True Edge — Source Quality, Cross-Asset Signals & Regime Reality

**Date:** 2026-04-12  
**Context:** Previous analyses showed inflated PnL from survivor bias and outliers. This report separates real edge from luck, identifies truly reliable sources, and maps cross-asset opportunities.

---

## Executive Summary

After stripping away the noise, **three sources produce genuine, consistent edge:**

1. **`claude_gainer_st` (quant engine):** 805 crypto picks, 65.8% WR, +917% PnL, median +1.35% per trade. This is real — high volume, positive median.
2. **`st_fear_greed_contrarian` (strategy):** 83.3% of days are winning days. The most consistent strategy by far. It doesn't get lucky on one big day — it wins *most* days.
3. **`multi_asset_copytrader` (copy trading):** 550 picks across FOREX/COMMODITY/BOND, 47.8% WR but PF 1.50. Modest but genuine edge on non-crypto.

**Everything else is either noise, regime luck, or broken.** The ML systems are net -144%. Equity strategies are -317% via `stocks_competition` alone. The "great PnL" we saw was driven by:
- Apr 7-9 regime match: crypto hit 55.6% WR and +510% — a 2-day bull window
- Apr 10-11 another regime match: 68.9% crypto WR
- 5 kimi_signal_tracking forex outliers: +298% PnL from impossible-looking moves

**Regime labeled on 0% of picks.** Every single closed pick has `regime = UNKNOWN`. The regime detector exists in code but its output isn't being stored on picks. We literally can't do regime-conditional analysis because the data isn't captured.

---

## 1. The Time Reality — Code Changes vs Regime Luck

### Performance by period

| Period | Picks | WR | Median PnL | Sum PnL | What happened |
|--------|-------|-----|-----------|---------|---------------|
| Before Apr 7 | 1,370 | 44.7% | -0.008% | +42% | Mixed. Equity -191%, Crypto +202% |
| **Apr 7-9** | **634** | **56.3%** | **+0.818%** | **+581%** | Crypto bull. +510% in 2 days |
| Apr 9-10 | 403 | 50.1% | +0.013% | +182% | Crypto still running |
| **Apr 10-11** | **309** | **63.8%** | **+0.864%** | **+480%** | Best period. Forex +205% (kimi outliers) |
| Apr 11-12 | 253 | 49.8% | +0.000% | +83% | Cooling off. Median is zero. |

**The entire +934% crypto "PnL" in `recent_closed` is concentrated in 3 days: Apr 7-11.** Before that, crypto was +202% over weeks. This isn't consistent alpha — it's a regime match.

### 6-hour window analysis reveals the volatility

The system oscillates wildly between 6-hour blocks:

- **Apr 5 06h:** 38 picks, **13.2% WR**, -50%
- **Apr 5 18h:** 140 picks, **72.1% WR**, +153%
- **Apr 7 12h:** 168 picks, 47.0% WR, -17%
- **Apr 7 18h:** 231 picks, **75.3% WR**, +446%
- **Apr 8 18h:** 69 picks, **26.1% WR**, -57%
- **Apr 9 00h:** 99 picks, **17.2% WR**, -117%
- **Apr 9 12h:** 161 picks, **68.3% WR**, +181%

**This is not a system with edge — this is a system that wins when the market goes up and loses when it goes down.** A truly hedged system would show more stability across 6-hour windows.

---

## 2. Source Quality — Who Actually Produces Edge?

### Tier 1: Genuine Edge (positive median, consistent across days)

| Source | Category | Picks | WR | Median PnL | Sum PnL | Day Win% |
|--------|----------|-------|-----|-----------|---------|----------|
| `claude_gainer_st` | Quant Engine | 805 | 65.8% | **+1.349%** | +917% | High |
| `dna_winner_picks` | Quant Engine | 61 | 65.6% | +2.500% | +70% | — |
| `kimi_signal_tracking` | Signal | 44 | 59.1% | +2.046% | +258% | — |
| `signal_validation` | Signal | 34 | 61.8% | +2.065% | +34% | — |
| `luxalgo_filters` | Scanner | 179 | 52.0% | +1.137% | +70% | 66.7% |

**`claude_gainer_st` is the system's alpha engine.** It runs `st_fear_greed_contrarian` and other `st_*` strategies. 805 picks with +1.35% median — this is not outlier-driven.

### Tier 2: Modest Edge (positive sum but low/zero median)

| Source | Category | Picks | WR | Median PnL | Sum PnL |
|--------|----------|-------|-----|-----------|---------|
| `multi_asset_copytrader` | Copy Trader | 550 | 47.8% | **0.000%** | +56% |
| `kimi_riseoftheclaw` | Signal | 267 | 41.9% | -0.415% | +65% |
| `rapid_fire` | Scanner | 154 | 42.2% | -0.369% | +17% |
| `mercury2` | Scanner | 52 | 40.4% | -0.729% | +23% |

**These sources are breakeven on median — their positive PnL sum comes from outlier wins.**

### Tier 3: Net Losers (kill or inverse)

| Source | Category | Picks | WR | Median PnL | Sum PnL |
|--------|----------|-------|-----|-----------|---------|
| `ml_crypto_pred` | ML | 195 | 27.2% | **-2.000%** | **-125%** |
| `stocks_competition` | — | 359 | 36.2% | -1.490% | **-317%** |
| `multi_asset_institutional` | — | 18 | 33.3% | -2.572% | -40% |
| `fast_stocks_competition` | — | 21 | 14.3% | -3.000% | -41% |
| `claude_gainer` | — | 21 | 47.6% | -0.602% | -49% |
| `multi_asset_scanner` | — | 71 | 16.9% | -0.004% | -10% |

**`stocks_competition` alone lost -317%.** It should be shut down. `ml_crypto_pred` (195 picks, 27.2% WR, -2% median) is the ML system's biggest failure.

---

## 3. Consistency Analysis — Winning Most Days vs Getting Lucky

**The hardest test: does a strategy win on most trading days?**

### Most Consistent (>60% of days are winning days)

| Strategy | Days | Win Days | Day WR | Picks | Total PnL | Verdict |
|----------|------|---------|--------|-------|-----------|---------|
| **st_fear_greed_contrarian** | 6 | 5 | **83.3%** | 310 | +576% | **PROVEN: wins almost every day** |
| **st_obv_support_divergence** | 6 | 5 | **83.3%** | 159 | +165% | PROVEN |
| atr_regime_rsi | 5 | 4 | 80.0% | 15 | +5% | Small sample |
| MeanReversionBB | 7 | 5 | 71.4% | 22 | +30% | PROVEN (small) |
| luxalgo_confluence | 9 | 6 | 66.7% | 179 | +70% | PROVEN |
| rs-breakout-scout | 9 | 6 | 66.7% | 13 | +26% | PROVEN (small) |

### Least Consistent (0-30% winning days — regime-dependent or broken)

| Strategy | Days | Win Days | Day WR | Picks | Total PnL |
|----------|------|---------|--------|-------|-----------|
| **enhanced_ml_A_xgboost** | 8 | **0** | **0.0%** | 189 | -113% |
| crypto_keltner_expansion | 4 | 0 | 0.0% | 10 | -3% |
| call-surge-scout | 6 | 0 | 0.0% | 12 | -25% |
| community_london_breakout | 3 | 0 | 0.0% | 16 | -8% |
| st_bb_squeeze_expansion | 9 | 1 | 11.1% | 52 | -26% |

**`enhanced_ml_A_xgboost` has ZERO winning days across 8 days of trading.** Not a single day where the majority of its picks are green. This is the strongest evidence it has no edge.

---

## 4. Regime Reality: We Don't Capture It

**Every single closed pick has `regime = UNKNOWN`.** The `regime_detector.py` exists and classifies markets into TRENDING_UP/DOWN, CHOPPY, HIGH_VOLATILITY, CRISIS — but the regime label is not being stored on picks at entry time.

**This is a critical gap.** Without regime labels on picks, we cannot:
- Measure which strategies work in which regimes
- Implement regime-conditional gating
- Detect regime-mismatch drift
- Prove whether a strategy has real edge vs lucky regime timing

**Fix:** In `scanner.py`, before `open_pick()`, call `regime_detector.detect_regime()` and store the result in `pick['regime_at_entry']`. This is a one-line fix with massive analytical value.

---

## 5. Cross-Asset Signals — Where to Look

### What we found (limited by 0% regime labeling)

When crypto has a good day (WR ≥ 55%), equity also performs well (+2.2% avg PnL) and forex is positive (+1.8%). Commodities show no correlation (-0.1%).

**This suggests crypto and equity are both "risk-on" assets in our system — they move together.** Our system doesn't hedge between them.

### Cross-Asset Opportunities to Investigate

**A. Crypto ↔ Macro Indicators**

| Indicator | Correlation to crypto | Data source | Implementation |
|-----------|----------------------|-------------|----------------|
| DXY (US Dollar Index) | Inverse — strong dollar = weak crypto | Yahoo Finance (`DX-Y.NYB`) | Add as feature in `ml_ranker.py` |
| US 10Y yield change | Inverse — rising rates = risk-off | FRED API | Daily feature |
| VIX level | Inverse — high VIX = crypto weakness | Yahoo Finance (`^VIX`) | Already in `fear_greed` strategies |
| S&P 500 5d momentum | Positive — risk-on/off correlation | Yahoo Finance (`^GSPC`) | Cross-asset momentum feature |
| Fed Funds rate expectations | Inverse — hawkish = bearish crypto | CME FedWatch | Monthly feature |

**B. Oil ↔ Energy Equities**

Our best equity symbols are XOM (65% WR) and CVX (72% WR) — both oil/energy companies. If we track:
- Crude Oil futures (CL=F) — already in commodity universe
- US gasoline retail prices (EIA weekly)
- OPEC+ production decisions
- Oil inventory reports (API/EIA weekly)

We can create a signal: "When oil inventories draw down and oil price rises → go long XOM/CVX with higher conviction."

```python
# Proposed: Oil-energy leading indicator
def oil_energy_signal():
    """Use oil futures momentum as leading indicator for energy equities."""
    cl_5d = get_return('CL=F', days=5)  # Crude oil 5-day return
    cl_20d = get_return('CL=F', days=20)  # 20-day trend
    
    if cl_5d > 0.02 and cl_20d > 0:  # Oil rising in uptrend
        return {'signal': 'LONG', 'targets': ['XOM', 'CVX', 'COP'],
                'confidence_boost': 0.15}
    elif cl_5d < -0.02 and cl_20d < 0:  # Oil falling in downtrend
        return {'signal': 'AVOID', 'targets': ['XOM', 'CVX', 'COP']}
    return None
```

**C. Forex ↔ Rate Differentials**

`forex_rsi2_mean_reversion` (326 picks, 48.2% WR) is our core forex strategy. Its edge could be amplified by:
- Interest rate differential between currency pairs (carry signal)
- COT positioning data (institutional vs retail)
- The existing `myfxbook_retail_contrarian` (45.5% WR, 11 picks) uses retail sentiment — scale this up

**D. Crypto ↔ On-Chain Data**

The Fear & Greed Index is already powering our best strategy. Expand with:
- Exchange inflow/outflow (selling pressure signal)
- Stablecoin supply changes (buying power indicator)
- BTC funding rate z-score (already a feature but defaulting to 0 for many picks)
- Open interest changes (leverage buildup/unwind)

---

## 6. What We Should Actually Trust

### The Proven Core (keep and amplify)

| Component | Evidence | Action |
|-----------|----------|--------|
| `st_fear_greed_contrarian` | 83% day WR, 310 picks, +576% | **MAX ALLOCATION.** This is our real edge. |
| `st_obv_support_divergence` | 83% day WR, +165% | Increase allocation |
| `luxalgo_confluence` | 67% day WR, 179 picks, +70% | Reliable scanner signal |
| `MeanReversionBB` | 71% day WR, +30% | Small but consistent |
| Copy trader (forex/commodity) | 550 picks, PF 1.50, breakeven median | Modest edge, keep for diversification |
| `stocks_rsi2_pullback` | 88.9% WR (9 picks via copytrader) | Scale up within equity |

### The Pretenders (looks good but regime-dependent)

| Component | Reality | Action |
|-----------|---------|--------|
| `st_multi_day_momentum` | +167% but only 50% day WR — big wins on bull days | Reduce allocation, regime-gate |
| `alpha_engine` (broad) | 52% WR but median +0.07% — near breakeven | Don't amplify, maintain |
| `rapid_fire` | 42.2% WR, -0.37% median — sum is positive from outliers | Reduce or regime-gate |

### The Destroyers (kill or inverse)

| Component | Damage | Action |
|-----------|--------|--------|
| `stocks_competition` | -317% on 359 picks, 36.2% WR | **KILL** |
| `enhanced_ml_A_xgboost` | -113% on 189 picks, 0% winning days | **KILL or INVERSE** |
| `ml_crypto_pred` | -125% on 195 picks, 27.2% WR | **KILL or INVERSE** |
| `claude_gainer` (not _st) | -49% on 21 picks | KILL |
| All equity except XOM/CVX/RSI2 | Losing on 60%+ of stocks | Pause equity, keep only VALUE_ENERGY |

---

## 7. Implementation Priorities

### Immediate (today)

1. **Store regime on every pick.** Add `pick['regime_at_entry'] = detect_regime()` in scanner before `open_pick()`. One line of code, unlocks all regime analysis.
2. **Kill `stocks_competition`** — -317% is the single biggest PnL drain.
3. **Kill `enhanced_ml_A_xgboost`** — 0% winning days on 8 days of data.
4. **Kill `ml_crypto_pred`** — 27.2% WR, -125%, median loss -2%.

### Short-term (this week)

5. Add DXY and VIX as features in `ml_ranker.py` / scoring pipeline.
6. Add oil futures momentum as leading indicator for XOM/CVX picks.
7. Scale up `st_fear_greed_contrarian` allocation — it's our proven edge.
8. Wire `myfxbook_retail_contrarian` to more forex pairs — retail contrarian has genuine theoretical basis.

### Medium-term

9. Implement proper regime-conditional strategy activation.
10. Add on-chain data (exchange flows, stablecoin supply) as crypto features.
11. Build cross-asset momentum signals (SPX→crypto risk-on/off).
12. Create "copy the copy trader" — track which `multi_asset_copytrader` strategies win and scale those up.

---

## Key Takeaway

**We have exactly one proven edge: sentiment contrarian on crypto via `st_fear_greed_contrarian` and related `st_*` strategies in `claude_gainer_st`.** Everything else is either breakeven, regime-dependent, or actively losing money. The path forward isn't more strategies — it's:
1. Protect the proven edge (sentiment contrarian)
2. Kill the destroyers (stocks_competition, xgboost, ml_crypto_pred)
3. Add cross-asset intelligence (DXY, VIX, oil→energy, on-chain)
4. Actually capture regime data so we can measure what works when

---

*Generated 2026-04-12 from 3,500 closed picks, source system analysis, 6-hour time segmentation, daily consistency scoring, and code change impact analysis.*
