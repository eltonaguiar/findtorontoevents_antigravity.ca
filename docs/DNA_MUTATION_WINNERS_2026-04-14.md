# DNA Mutations for Winning Low-Volume Strategies

**Date:** 2026-04-13 9:39 PM EDT  
**Methodology:** Per TESTING_PROTOCOL.MD — rehabilitation-first pipeline, three-axis mutation protocol  
**Data Source:** `audit_dashboard/data/dashboard_data.json` → `picks.recent_closed` (canonical, N=3,500)  
**Filter:** Definitive exits only (SL/TP/trailing hit) — no timeouts

---

## Executive Summary

32 winning strategies have < 80 total picks. These are proven edges starving for volume. Rather than building new unproven strategies, we should **mutate the winners to produce more picks** — expand their symbol universe, loosen entry thresholds, and replicate across asset classes.

**Top 5 mutation candidates (highest PF on definitive exits, proven edge, low volume):**

| Strategy | Def Picks | Def WR | Def PF | Asset | Mutation Plan |
|----------|----------|--------|--------|-------|--------------|
| `stocks_rsi2_pullback` | 9 | 100% | 99 | EQUITY | Expand to 20+ symbols |
| `MeanReversionBB` | 9 | 89% | 12.00 | CRYPTO,FOREX | Add 10+ crypto symbols |
| `st_obv_support_divergence` | 39 | 82% | 9.73 | CRYPTO | Loosen entry, add 10 symbols |
| `myfxbook_retail_contrarian` | 15 | 93% | 99 | FOREX | Add all major/minor pairs |
| `st_multi_day_momentum` | 37 | 70% | 5.51 | CRYPTO | Reduce hold requirement |

---

## 1. Mutation Specifications

### Mutation 1: `stocks_rsi2_pullback_expanded`

**Parent:** `stocks_rsi2_pullback` — 100% WR on definitive exits, PF 99 (9 trades), winning on XOM (4/4), CVX (2/2)

**Why it's low volume:** Only trades 5 symbols. RSI-2 pullback is a well-studied mean-reversion strategy (Connors RSI) that works broadly on liquid equities.

**Mutation:**
- **Symbol expansion:** Add all S&P 500 energy + large-cap value stocks: XOM, CVX, COP, EOG, SLB, MPC, VLO, PSX, HAL, OXY, PXD, HES, DVN, FANG, MRO + add SPY, QQQ, IWM for index exposure
- **Entry relaxation:** Current RSI-2 entry at RSI < 5 → mutate to RSI < 10 (doubles entry frequency while still deeply oversold)
- **TP/SL parameters:** Keep parent's ATR-based TP/SL (it's working perfectly)
- **Asset class expansion:** Test on FTSE 100 large-caps (if data available)

**Expected impact:** 5 symbols → 20+ symbols = ~4× pick volume at similar WR

**Validation per TESTING_PROTOCOL:**
- Layer 1: Backtest on expanded symbol list (2 years IS)
- Layer 2: 70/15/15 split
- Layer 2.5: Must pass Score ≥ 40, Trust ≥ 4 gates
- Layer 5: Bootstrap PF CI, must beat random baseline

---

### Mutation 2: `MeanReversionBB_expanded`

**Parent:** `MeanReversionBB` — 89% WR, PF 12.00 (9 def picks), winning on LINK-USD, ETH-USD

**Why it's low volume:** Bollinger Band mean reversion only fires on extreme band touches. Narrow symbol universe.

**Mutation:**
- **Symbol expansion (crypto):** Add all top-20 market cap coins: BTC, ETH, SOL, BNB, XRP, ADA, DOGE, AVAX, DOT, LINK, UNI, ATOM, APT, SUI, ARB, OP, RENDER (currently only trades 8 symbols)
- **Band parameter mutation:** Test BB(20, 2.0) → BB(20, 1.8) (more entries from tighter bands, slightly less extreme)
- **Timeframe mutation:** Test 4h in addition to current (likely 1h) — catches more swing-level reversion setups
- **Asset class crossover:** Test on FOREX majors (EURUSD, GBPUSD, USDJPY) — Bollinger reversion works well on ranging FX pairs

**Expected impact:** 8 → 20+ symbols + tighter bands = ~3-5× pick volume

---

### Mutation 3: `st_obv_support_divergence_amplified`

**Parent:** `st_obv_support_divergence` — 82% WR, PF 9.73 (39 def picks). Strong across 8+ crypto symbols (UNIUSDT 100%, ADAUSDT 100%, LTCUSDT 100%, XRPUSDT 100%, SUIUSDT 100%)

**Why it's low volume:** Only 73 total picks. The OBV divergence signal is inherently rare (requires price making new low/high while OBV doesn't confirm).

**Mutation:**
- **Entry threshold relaxation:** Current OBV divergence likely requires multi-bar confirmation. Mutate to allow 1-bar divergence (more frequent, slightly noisier)
- **Symbol expansion:** Add all definitive-edge symbols from other strategies: APTUSDT, ARBUSDT, DOTUSDT, ETHUSDT, SOLUSDT, FETUSDT, TIAUSDT, ATOMUSDT
- **Timeframe mutation:** If currently on 4h, add 1h variant. If on 1h, add 15m variant.
- **Regime filter:** Only fire in non-CRISIS regimes (this strategy's strength is volume-confirmed reversals, which fail in panic selloffs)
- **Hybrid crossover:** Combine OBV divergence entry with `st_fear_greed_contrarian` timing — enter OBV divergence only when Fear & Greed < 40

**Expected impact:** 16 → 24+ symbols + looser entry + additional timeframe = ~2-3× picks

---

### Mutation 4: `myfxbook_retail_contrarian_scaled`

**Parent:** `myfxbook_retail_contrarian` — 93% WR, PF 99 (15 def picks). Winning on NZDUSD, EURGBP, EURJPY.

**Why it's low volume:** Requires myfxbook retail sentiment data, which may only cover a few pairs. Also, contrarian-only fires when retail is extreme (>70% or <30% one-sided).

**Mutation:**
- **Symbol expansion:** Add all 28 major/minor FX pairs covered by myfxbook: EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, NZDUSD, USDCAD + all crosses
- **Threshold relaxation:** Current retail threshold likely >70% one-sided. Mutate to >65% (more frequent, slightly less extreme)
- **Data source expansion:** Add IG Client Sentiment (already have `ig_contrarian_sentiment` with 100% WR on 7 def picks) as a secondary signal. Cross-confirm: when BOTH myfxbook AND IG show >65% retail positioning → higher confidence
- **Hold time extension:** Forex retail positions unwind over days. Test 48h and 72h max hold vs current (likely 24h)

**Expected impact:** 5 → 28 pairs + looser threshold = ~5× pick volume

---

### Mutation 5: `st_multi_day_momentum_turbo`

**Parent:** `st_multi_day_momentum` — 70% WR, PF 5.51 (37 def picks), crypto only, strong on 4 symbols

**Why it's low volume:** Multi-day momentum requires sustained moves, which are rare. Only trades 4 symbols.

**Mutation:**
- **Symbol expansion:** Add all top-15 crypto by volume
- **Momentum threshold reduction:** Reduce from multi-day to 12h+ momentum persistence (captures shorter but still confirmed trends)
- **Confirmation relaxation:** If requiring 3 consecutive up bars, reduce to 2 consecutive
- **Volume confirmation variant:** Add variant that also requires volume > 1.5× average (higher conviction but same direction)

**Expected impact:** 4 → 15 symbols + 12h threshold = ~3× picks

---

## 2. Losers Entering Rehabilitation (Per TESTING_PROTOCOL Section 7)

The following strategies have ≥ 10 picks and WR < 35% — they auto-route to `REHAB_CANDIDATE` per the protocol:

| Strategy | Picks | WR | PF | Status | Rehab Stage |
|----------|-------|-----|-----|--------|------------|
| `enhanced_ml_A_xgboost` | 189 | 28% | varies | REHAB_CANDIDATE | Stage 1: Cross-symbol |
| `Value + Quality` | 48 | 6.2% | 0.14 | REHAB_CANDIDATE | Stage 3: Inverse |
| `Consecutive Beats` | 39 | 25.6% | 0.54 | REHAB_CANDIDATE | Stage 1: Cross-symbol |
| `Earnings Drift` | 19 | 15.8% | 0.30 | REHAB_CANDIDATE | Stage 3: Inverse |
| `st_bb_squeeze_expansion` | 52 | 28.8% | varies | REHAB_CANDIDATE | Stage 1: Symbol-lock |
| `community_london_breakout_v2_forex` | 16 | 0% | 0 | REHAB_CANDIDATE | Stage 3: Inverse |
| `volume_spike_breakout` | 89 | 39.3% | varies | REHAB_CANDIDATE | Stage 4: TP/SL mutation |

**Rehabilitation actions per protocol:**

**`enhanced_ml_A_xgboost` — REHAB Stage 1 (symbol-lock):**  
- Data shows 90% WR on SEIUSDT, 75% on TIAUSDT, 88% on ETCUSDT but 0% on TRXUSDT/JTOUSDT
- **Symbol-lock variant:** `enhanced_ml_A_xgboost_curated` — only trade SEIUSDT, TIAUSDT, ETCUSDT, WLDUSDT
- Block TRXUSDT, JTOUSDT, ARBUSDT, ALGOUSDT, FILUSDT

**`Value + Quality` — REHAB Stage 3 (inverse):**  
- 6.2% WR → inverse = 93.8% theoretical WR
- Create `value_quality_inverse` — flip direction on every signal
- Paper trade for 2 weeks, require 20+ picks and PF > 1.5 before promoting

**`community_london_breakout_v2_forex` — REHAB Stage 3 (inverse):**  
- 0% WR on 16 picks → perfect inverse candidate (100% if inverted)
- Create `london_breakout_contrarian` — fade every breakout signal
- This aligns with the known forex contrarian edge

---

## 3. Implementation Plan

### Phase 1: Create mutation configs (no code changes needed)

Add mutation definitions to `alpha_engine/data/dna_mutations.json`:

```json
{
  "mutations": [
    {
      "parent": "stocks_rsi2_pullback",
      "name": "stocks_rsi2_pullback_expanded",
      "type": "symbol_expansion",
      "params": {
        "symbols": ["XOM","CVX","COP","EOG","SLB","MPC","VLO","PSX","HAL","OXY","SPY","QQQ","IWM"],
        "rsi_entry_threshold": 10,
        "rsi_period": 2,
        "tp_sl_from_parent": true
      },
      "status": "PENDING_BACKTEST",
      "created": "2026-04-13T21:39:00-04:00"
    },
    {
      "parent": "MeanReversionBB",
      "name": "MeanReversionBB_expanded",
      "type": "symbol_expansion_and_param_tweak",
      "params": {
        "symbols_add": ["BTCUSDT","SOLUSDT","BNBUSDT","XRPUSDT","ADAUSDT","DOGEUSDT","AVAXUSDT","DOTUSDT","UNIUSDT","ATOMUSDT","APTUSDT","SUIUSDT","ARBUSDT"],
        "bb_std": 1.8,
        "bb_period": 20,
        "timeframes": ["1h", "4h"]
      },
      "status": "PENDING_BACKTEST",
      "created": "2026-04-13T21:39:00-04:00"
    },
    {
      "parent": "st_obv_support_divergence",
      "name": "st_obv_support_divergence_amplified",
      "type": "entry_relaxation_and_expansion",
      "params": {
        "symbols_add": ["APTUSDT","ARBUSDT","DOTUSDT","ETHUSDT","SOLUSDT","FETUSDT","TIAUSDT","ATOMUSDT"],
        "divergence_bars_min": 1,
        "regime_filter": "exclude_CRISIS",
        "fgi_gate": "< 40"
      },
      "status": "PENDING_BACKTEST",
      "created": "2026-04-13T21:39:00-04:00"
    },
    {
      "parent": "myfxbook_retail_contrarian",
      "name": "myfxbook_retail_contrarian_scaled",
      "type": "symbol_expansion_and_threshold_relaxation",
      "params": {
        "pairs_add": ["EURUSD","GBPUSD","USDJPY","USDCHF","AUDUSD","USDCAD","GBPJPY","EURJPY","AUDJPY","NZDJPY","CHFJPY","EURGBP","EURAUD","GBPAUD"],
        "retail_threshold": 65,
        "max_hold_hours": 72,
        "cross_confirm_with": "ig_contrarian_sentiment"
      },
      "status": "PENDING_BACKTEST",
      "created": "2026-04-13T21:39:00-04:00"
    },
    {
      "parent": "st_multi_day_momentum",
      "name": "st_multi_day_momentum_turbo",
      "type": "threshold_relaxation_and_expansion",
      "params": {
        "symbols_add": ["BNBUSDT","XRPUSDT","ADAUSDT","DOGEUSDT","AVAXUSDT","DOTUSDT","UNIUSDT","ATOMUSDT","APTUSDT","SUIUSDT","ARBUSDT"],
        "momentum_min_hours": 12,
        "consecutive_bars_min": 2,
        "volume_confirmation": true,
        "volume_min_ratio": 1.5
      },
      "status": "PENDING_BACKTEST",
      "created": "2026-04-13T21:39:00-04:00"
    }
  ],
  "rehabilitations": [
    {
      "parent": "enhanced_ml_A_xgboost",
      "name": "enhanced_ml_A_xgboost_curated",
      "type": "symbol_lock",
      "params": {
        "allow_symbols": ["SEIUSDT","TIAUSDT","ETCUSDT","WLDUSDT"],
        "block_symbols": ["TRXUSDT","JTOUSDT","ARBUSDT","ALGOUSDT","FILUSDT"]
      },
      "status": "PENDING_PAPER_TRADE",
      "rehab_stage": 1
    },
    {
      "parent": "Value + Quality",
      "name": "value_quality_inverse",
      "type": "inverse",
      "params": {"flip_direction": true, "tp_sl_from_parent": true},
      "status": "PENDING_PAPER_TRADE",
      "rehab_stage": 3
    },
    {
      "parent": "community_london_breakout_v2_forex",
      "name": "london_breakout_contrarian",
      "type": "inverse",
      "params": {"flip_direction": true, "asset_class": "FOREX"},
      "status": "PENDING_PAPER_TRADE",
      "rehab_stage": 3
    }
  ]
}
```

### Phase 2: Backtest mutations per TESTING_PROTOCOL Layers 1-2

For each mutation, run through the incubator:
1. `alpha_engine/incubator/run_incubator.py` with the mutation's expanded symbol list
2. Walk-forward with 14d train / 7d test windows (crypto) or 60d / 30d (equity/forex)
3. Apply Layer 2.5 quality gates: Score ≥ 40, no toxic combos
4. Bootstrap PF CI — must be above 1.0 at 95% confidence

### Phase 3: Paper trade passing mutations (2 weeks)

Per Layer 6:
- Wire mutations to forward test portfolios
- Require 20+ definitive-exit picks
- Must maintain PF ≥ 1.3 and WR ≥ 45% on definitive exits
- If mutation meets criteria after 2 weeks → promote to `DATA_VALIDATED`

---

## 4. Validation Checklist (Per TESTING_PROTOCOL)

For each mutation, before going live:

- [ ] Layer 0: Data integrity (timestamps UTC, adjusted prices, schema validated)
- [ ] Layer 1: IS backtest on expanded symbol list
- [ ] Layer 2: OOS validation (70/15/15 split, drift check)
- [ ] Layer 2.5: Quality gates (Score ≥ 40, Trust ≥ 4, no toxic combos)
- [ ] Layer 3: Walk-forward (weekly refresh, ≥ 200 picks, ≥ 3 asset classes where applicable)
- [ ] Layer 4: Statistical significance (BH FDR, bootstrap CI on PF)
- [ ] Layer 5: Regime robustness (must show edge in ≥ 2 FGI regimes)
- [ ] Layer 6: Forward test (20+ definitive picks, PF ≥ 1.3, 2 weeks)
- [ ] Layer 7: Promotion gate (persistent multi-layer pass)

---

## 5. High-Volume Winners to Protect (Do NOT Mutate)

These strategies have proven edge at scale. Do not change their parameters — only expand their allocation:

| Strategy | Def Picks | Def WR | Def PF | Action |
|----------|----------|--------|--------|--------|
| `luxalgo_confluence` | 61 | 98.4% | 125.66 | **Protect — max allocation** |
| `forex_rsi2_mean_reversion` | 183 | 99.5% | 99 | **Protect — core forex strategy** |
| `futures_momentum` | 111 | 100% | 99 | **Protect — core commodity strategy** |
| `strong consensus (alpha_engine, ml_crypto_pred)` | 68 | 91.2% | 24.55 | **Protect — consensus signal** |
| `st_rsi_momentum_confluence` | 40 | 72.5% | 1.90 | Protect but monitor for decay |

---

*Generated: 2026-04-13 9:39 PM EDT*  
*Per TESTING_PROTOCOL.MD rehabilitation-first pipeline and three-axis mutation protocol*
