# Proven Research Strategies + Beta Confluence Score — Design Spec

**Date:** 2026-03-16
**Approach:** A — Alpha Engine + Cross-Agg Beta Score
**Status:** Sections 1-3 design-approved. Section 1 module created (stubs). Spec review passed with fixes applied.

---

## Background

### Problem

The trading platform has 35+ signal systems generating 500+ algorithms, but audit results show most are underperforming:
- KIMI: 36.7% WR (confirmer-only, disabled Mar 12)
- Alpha Engine: 45.1% WR (breakeven)
- 6 systems banned (ML Battleground A/B/C/ensemble, multi_asset, crypto_winners)
- Only 12 strategies in the "proven" filter actually perform

An institutional-grade audit of the platform identified critical gaps: no VWAP strategies, no statistical arbitrage, no candlestick pattern systems, no supply/demand zone trading, and no multi-factor confluence scoring gate.

### Research Sources

Six strategy research files were analyzed:
1. **Docx audit** — Quant/hedge fund-level analysis of platform performance
2. **Kimi_Agent_Proven Crypto_Forex Strategies** — 12 proven strategies with backtests
3. **Kimi_Agent_Proven Crypto_Forex Strategies (1)** — 6 hybrid "DNA mutation" strategies
4. **Kimi_Agent_Crypto Signal Strategy Analysis** — ML benchmarks, on-chain metrics, top-3 per market
5. **Kimi_Agent_Crypto Signal Strategy Analysis (1)** — Subset of file 4
6. **Kimi_Agent_Crypto Picks Audit Review** — Platform audit and evaluation framework

### Decision

- **Add 10 new high-WR strategies** from research files into Alpha Engine
- **Add a "beta" confluence score** (0-100) alongside the existing production score
- **Add volatility-scaled TP/SL and confidence-weighted adjustments** for better exit quality
- **Monitor both scores** side-by-side in the audit dashboard
- **Decide which score to use** based on real forward-test data (50+ closed picks)

---

## Section 1: New Strategy Module (MODULE CREATED — STUBS ONLY)

> **Clarification:** "Implemented" means the module file exists and is registered via the import pattern. The 10 strategy functions are stubs returning empty lists. Full strategy logic is part of the implementation plan.

### File: `alpha_engine/proven_research_strategies.py`

10 research-backed strategies following the exact existing pattern:

```python
def strategy_name(data: dict[str, pd.DataFrame]) -> list[dict]:
    """
    Returns list of pick dicts with keys:
    strategy, symbol, category, signal_type, entry_price, take_profit, stop_loss,
    confidence, risk_reward, reason, timeframe, rsi_at_entry, atr_at_entry,
    volume_ratio, timestamp, research_cohort
    """
```

### Strategy Inventory

| # | Function Name | Expected WR | Indicators | Timeframe | Source |
|---|---|---|---|---|---|
| 1 | `vwap_trend_bounce` | 65-70% | VWAP + volume rejection candle in established trend | 1H/4H | Prop firm verified, PF 1.7-2.1 |
| 2 | `hoffman_ema_irb` | 62% | EMA 3/5/18 alignment + IRB pullback arrow | 15M/1H | 100-trade forward test, PF 1.8-2.0 |
| 3 | `statistical_pairs_zscore` | 70-75% | Z-score at ±2 SD, exit at 0, correlation >0.8 | 4H/1D | Institutional-grade, market-neutral |
| 4 | `supply_demand_zone` | 55-65% | Fresh supply/demand zones + volume confirmation | 1H | EA backtest +225% AUDJPY 23mo, PF 1.6-2.2 |
| 5 | `three_white_soldiers_rsi` | 83% | 3 consecutive bullish candles + RSI < 35 entry filter | 4H/1D | ES backtest PF 2.68, Sharpe 2.50 |
| 6 | `bearish_engulfing_reversal` | 75.76% | Bearish engulfing pattern as counter-intuitive BUY signal | 1D | ES backtest PF 2.73, Sharpe 1.98 |
| 7 | `golden_confluence_swing` | 72.3% | RSI + MACD + volume + Fear & Greed + exchange flows | 4H/1D | Multi-layer confluence, PF 2.8, DD -14.7% |
| 8 | `vwap_rsi_institutional` | 70-75% | VWAP return + RSI 14 < 40 + RSI 21 > 50 + RSI 50 > 55 | 1H/4H | Hybrid: VWAP + triple RSI confirmation |
| 9 | `rsi_weighted_pairs_arb` | 75-82% | Pairs Z-score < -2 + RSI of underperformer < 35 + cointegration | 4H/1D | Hybrid: pairs + RSI weighting, PF 2.2-2.8 |
| 10 | `hoffman_keltner_expansion` | 68-73% | EMA 3/5/18 alignment + Keltner bandwidth < 2% + IRB + volume | 1H | Hybrid: Hoffman + Keltner compression |

### Registration

**KNOWN ISSUE (must fix):** The current import in `crypto_strategies.py` is nested inside an `except ImportError` handler for `proven_scanner_strategies`, making it fragile. During implementation, move it to its own independent try/except block:

```python
# Proven Research Strategies — 2026-03-16 cohort
try:
    from proven_research_strategies import PROVEN_RESEARCH_STRATEGIES
    CRYPTO_STRATEGIES.update(PROVEN_RESEARCH_STRATEGIES)
except ImportError:
    pass
```

### Cohort Tracking

All picks include `"research_cohort": "2026-03-16"` for independent performance tracking of this batch.

### Available Indicators (VERIFIED)

From `alpha_engine/indicators.py` (actually present as function definitions):
- `vwap_session`, `ema`, `rsi`, `macd`, `bollinger_bands`, `keltner_channels` (note: plural), `atr`, `adx`, `obv`, `hma`, `ichimoku`

**NOT available (must implement inline or skip):**
- `stochastic_rsi`, `mfi`, `supertrend`, `dema`, `tema`, `zlema`, `pivot_points`, `donchian_channel`, `choppiness_index`, `fear_and_greed`

Strategies requiring missing indicators must either:
1. Compute the indicator inline within the strategy function (preferred for simple ones like stochastic RSI)
2. Add the indicator to `indicators.py` first

---

## Section 2: Beta Confluence Score

### File: `cross_aggregation/beta_confluence_scorer.py` (CREATE or FIX)

> **KNOWN ISSUE:** A partial/broken `beta_confluence_scorer.py` already exists with:
> - Semicolon instead of colon on line 17 (`-> Tuple[...];` — SyntaxError)
> - Returns `Tuple[float, Dict]` but spec integration code expects a dict
> - Must be rewritten to match this spec exactly.

A multi-factor confluence scoring system that runs alongside the existing production scoring. Every pick processed by the cross-aggregation system receives BOTH scores.

### Return Type (CANONICAL)

```python
def score_pick(self, pick: dict, system_data: dict, market_context: dict) -> dict:
    """
    Returns:
    {
        "total": float (0-100),
        "breakdown": {
            "technical": float (0-25),   # absolute points, not percentages
            "onchain": float (0-20),
            "sentiment": float (0-15),
            "risk_reward": float (0-20),
            "structure": float (0-20)
        },
        "qualified": bool (total >= 70)
    }
    """
```

### Pick Field Name Mapping (CRITICAL)

The aggregator's unified picks use these field names. The beta scorer MUST use these exact keys:

| Spec Concept | Unified Dict Key | Notes |
|---|---|---|
| Entry price | `entry` | Primary key in unified dict (fallback chain: `entry` → `entry_price` → `entryPrice` → `price`) |
| Take profit | `tp` | Primary key in unified dict (fallback chain: `tp` → `take_profit` → `tp_price` → `targetPrice`) |
| Stop loss | `sl` | Primary key in unified dict (fallback chain: `sl` → `stop_loss` → `sl_price` → `stopPrice`) |
| Direction | `direction` | `"LONG"` or `"SHORT"` in unified dict (note: NOT `"BUY"`/`"SELL"` — those are per-system) |
| Confidence | `confidence` | float 0-1 (WR-anchored, consensus-boosted, capped at 0.95) |
| Risk-reward | computed | Not stored directly — compute from `entry`, `tp`, `sl` |

### Market Context Builder (NEW — REQUIRED)

The spec review identified that no one currently builds the `market_context` dict. **This must be created as a helper function** in the beta scorer module:

```python
def build_market_context() -> dict:
    """
    Fetches and returns:
    {
        "fear_greed_index": int (0-100),          # from alternative.me API
        "btc_24h_pct": float,                      # BTC 24h % change from CoinGecko
        "volatility_regime": str,                  # "LOW"/"NORMAL"/"HIGH"/"EXTREME"
        "regime": str,                             # "TRENDING"/"RANGING"/"VOLATILE"
        "exchange_flows_net": float,               # net exchange flows (positive = inflow)
        "mvrv_zscore": float,                      # MVRV proxy from 200d SMA ratio
        "lunarcrush_galaxy_score": float | None     # from LUNARCRUSH_API if set
    }
    """
```

All fields have fallback defaults if APIs fail. The aggregator calls this ONCE per run and passes the result to all `score_pick()` calls.

### Formula: 5 Pillars, 100 Points Total

| Pillar | Weight | Data Source | What It Measures |
|---|---|---|---|
| **Technical Confluence** | 25/100 | Pick's own indicators: RSI, MACD, volume ratio, trend alignment, ATR | How many independent technical signals agree with the pick direction |
| **On-Chain Support** | 20/100 | Fear & Greed Index (API), exchange flow proxies, MVRV SMA proxy | Whether on-chain data supports the trade |
| **Sentiment Alignment** | 15/100 | Fear & Greed index, LunarCrush Galaxy Score (via `LUNARCRUSH_API` env var if available) | Whether market sentiment aligns with the pick |
| **Risk-Reward Quality** | 20/100 | R:R ratio, entry room remaining (% to TP), ATR-based stop quality | How well-structured the trade setup is |
| **Market Structure** | 20/100 | Regime from `regime_terminal/`, BTC trend direction, volatility regime (VIX/ATR), ADX trend strength | Whether macro market conditions favor this trade type |

### Pillar Scoring Details

**Technical Confluence (0-25):**
- RSI alignment with direction: 0-5 pts (BUY + RSI < 40 = 5, RSI 40-50 = 3, RSI > 70 = 0)
- MACD histogram agreement: 0-5 pts
- Volume above 20-period average: 0-5 pts (>2x = 5, >1.5x = 3, >1x = 1)
- Trend alignment (EMA 21/50/200 stack): 0-5 pts
- Multiple system agreement: 0-5 pts (3+ systems = 5, 2 = 3, 1 = 0)

**On-Chain Support (0-20):**
- Fear & Greed alignment: 0-7 pts (BUY + F&G < 25 = 7, BUY + F&G < 40 = 4, neutral = 2)
- Exchange flow direction: 0-7 pts (outflows during BUY = bullish = 7)
- MVRV proxy (200d SMA ratio): 0-6 pts (below realized = accumulation zone)

**Sentiment Alignment (0-15):**
- Fear & Greed regime match: 0-8 pts
- LunarCrush Galaxy Score (if available): 0-7 pts (>70 for BUY = 7, fallback to F&G-based score if no API key)

**Risk-Reward Quality (0-20):**
- R:R ratio: 0-8 pts (>3:1 = 8, >2:1 = 5, >1.5:1 = 3, <1.5:1 = 0)
- Entry room remaining: 0-6 pts (>70% = 6, >50% = 4, <30% = 0)
- ATR-based stop quality: 0-6 pts (stop beyond 1.5 ATR = 6, tight stop < 0.5 ATR = 1)

**Market Structure (0-20):**
- Regime alignment: 0-8 pts (trending regime + momentum pick = 8, ranging + mean-reversion = 8, mismatched = 0)
- BTC trend (for crypto): 0-6 pts (BTC bullish + BUY alt = 6, BTC bearish + BUY alt = 0)
- Volatility regime: 0-6 pts (normal = 6, high = 3, extreme = 0)

### Thresholds (CANONICAL — single rule)

- **Beta-qualified:** score >= 70/100 — high-confluence, eligible for conviction picks
- **Beta-filtered:** score < 70/100 — still published (production score governs), flagged for monitoring only

UI colored bar uses the same rule:
- Green: >= 70 (qualified)
- Yellow: 50-69 (monitoring)
- Red: < 50 (low-confluence warning)

> The yellow band (50-69) is a visual cue only — it does NOT create a separate "marginal" tier. For all gating logic, picks are either qualified (>= 70) or filtered (< 70).

### Integration Into Existing Scoring Pipeline

**KNOWN ISSUE (must fix first — HARD BLOCKER):** `aggregator.py` line 41 has a corrupted import where `BetaConfluenceScorer` was spliced into the `regime_meta_router` try/except block with literal `\n\n` characters. **`aggregator.py` does not compile** in its current state. This must be **removed and replaced** with a clean, independent try/except block:

```python
# Beta Confluence Scorer — experimental A/B scoring (2026-03-16)
try:
    from beta_confluence_scorer import BetaConfluenceScorer
    _HAS_BETA_SCORER = True
except ImportError:
    _HAS_BETA_SCORER = False
```

**Injection point: after unified dict construction (~line 1256), before `aggregated.append(unified)`:**

The scorer receives the already-built `unified` dict (which has `entry`, `tp`, `sl`, `confidence`, `source_systems`, etc.) and the pre-built `market_context`:

```python
# Build market context ONCE per aggregation run (before the symbol loop)
if _HAS_BETA_SCORER:
    beta_scorer = BetaConfluenceScorer()
    market_context = beta_scorer.build_market_context()
else:
    market_context = {}

# Inside the symbol loop, after unified dict is built (~line 1256):
if _HAS_BETA_SCORER:
    try:
        beta_result = beta_scorer.score_pick(unified, market_context)
        unified["beta_score"] = beta_result["total"]
        unified["beta_breakdown"] = beta_result["breakdown"]
        unified["beta_qualified"] = beta_result["qualified"]
        best_breakdown["beta_total"] = beta_result["total"]
        best_breakdown["beta_pillars"] = beta_result["breakdown"]
    except Exception:
        unified["beta_score"] = None
        unified["beta_breakdown"] = None
        unified["beta_qualified"] = False
```

Note: `best_breakdown` is the `confidence_breakdown` dict already built for this pick.

### Bayesian Sub-Component

The existing `signal_aggregator/confidence_calculator.py` contains a Bayesian confidence module (Beta-Binomial conjugate prior, Dempster-Shafer evidence combination, Kalman filter, time-decay) that is currently **not wired into cross-aggregation**. The beta scorer imports its `calculate_signal_confidence()` method as a sub-component of the Technical Confluence pillar, contributing up to 5 of the 25 technical points. Import uses try/except with fallback to `pick.get("confidence", 0.5)`.

> **KNOWN ISSUE:** Dempster-Shafer in `confidence_calculator.py` (line ~226) can output values >1 (invalid probability). The beta scorer MUST clamp the output: `min(1.0, ds_result)` before using it as a sub-score.

---

## Section 3: Dashboard Monitoring & A/B Comparison

### CRITICAL: UI Changes Go in Template, Not index.html

> **`audit_dashboard/index.html` is auto-generated** by `audit_trail/dashboard_generator.py` (line ~3684-3685) from template data. Any direct edits to `index.html` will be overwritten on next generation. All UI changes MUST be made in the dashboard generator's template construction code OR in a separate `audit_dashboard/template.html` if one exists. Check `dashboard_generator.py` for the exact template mechanism before editing.

### CRITICAL: _normalize_pick Drops Unknown Fields

Both `audit_trail/dashboard_generator.py:_normalize_pick` (line ~657) and `cross_aggregation/consensus_outcome_tracker.py:_normalize_pick` (line ~349) return **fixed dicts** with hardcoded keys. They do NOT preserve unknown fields. Adding `beta_score`/`beta_breakdown`/`beta_qualified` to the unified dict is necessary but NOT sufficient — these normalizer functions must also be updated to include the new fields, or beta data will be silently dropped before reaching the dashboard.

**Fix:** Add to both `_normalize_pick` functions:
```python
"beta_score": pick.get("beta_score"),
"beta_breakdown": pick.get("beta_breakdown"),
"beta_qualified": pick.get("beta_qualified", False),
```

### Changes to `audit_dashboard/portfolio_manager.py`

1. **DO NOT add research strategies to `PROVEN_STRATEGIES`** — this would route them through proven/golden pick selection logic at line ~2379 and line ~2928, giving them unearned trust bonuses. Instead, create a **separate set**:

   ```python
   # Research cohort — forward testing, NOT proven yet (added 2026-03-16)
   # These get tracked but do NOT receive proven_bonus multipliers
   RESEARCH_COHORT_STRATEGIES = {
       'vwap_trend_bounce',
       'hoffman_ema_irb',
       'statistical_pairs_zscore',
       'supply_demand_zone',
       'three_white_soldiers_rsi',
       'bearish_engulfing_reversal',
       'golden_confluence_swing',
       'vwap_rsi_institutional',
       'rsi_weighted_pairs_arb',
       'hoffman_keltner_expansion',
   }
   ```

   In `score_pick()`, check membership separately:
   ```python
   is_research = any(rs in strat for rs in RESEARCH_COHORT_STRATEGIES)
   research_bonus = 1.0  # NO bonus — neutral until validated
   ```

   **Promotion path:** After 30+ closed trades with WR >= 55%, manually move from `RESEARCH_COHORT_STRATEGIES` to `PROVEN_STRATEGIES`.

2. **In `score_pick()`**, read `beta_score` from the pick dict and include in dashboard payload:
   ```python
   beta_score = p.get("beta_score", None)
   beta_qualified = p.get("beta_qualified", False)
   ```

3. **Add `beta_vs_production_divergence`** field with proper normalization:

   > **KNOWN ISSUE:** Production score from `score_pick()` (line ~2515) is unbounded, and the aggregator score (line ~1138) has no normalized 0-100 variant persisted in the unified pick. Must compute a normalized production score before comparing.

   ```python
   # Normalize production score to 0-100 using sigmoid scaling
   # This ensures comparability with the 0-100 beta score
   import math
   raw = production_score  # unbounded
   prod_normalized = 100.0 / (1.0 + math.exp(-0.1 * (raw - 50)))  # sigmoid centered at 50
   divergence = abs(prod_normalized - beta_score) if beta_score is not None else None
   ```

   Also persist `prod_normalized` in the pick dict so both scores are on the same 0-100 scale in the tracker.
   Divergence > 30 points triggers a visual alert in the dashboard.

### Changes to Dashboard UI (via `dashboard_generator.py` or `template.html`)

> **All changes below target the template/generator, NOT `index.html` directly.**

1. **"Beta Score" column** in pick tables:
   - Colored bar: red (< 40), yellow (40-69), green (>= 70)
   - Shows numeric score + pillar breakdown on hover/expand

2. **"Score Comparison" panel** (new section in dashboard):
   - Production score (normalized) vs Beta score for each pick (visual comparison)
   - Win rate of beta-qualified picks (>= 70) vs beta-filtered (< 70)
   - Top divergence alerts — picks where scores strongly disagree
   - Research cohort badge on strategies from `proven_research_strategies.py`

3. **"Beta Analytics" tab** (new dashboard tab):
   - TP/SL efficiency metrics per strategy
   - Beta-production divergence scatter
   - Cohort-level WR, PF, and Sharpe displayed as a group

4. **Research Cohort Tracking:**
   - Distinct "RESEARCH" badge/tag (visually distinct from PROVEN/GOLD badges)
   - Cohort-level WR, PF, and Sharpe displayed as a group

### Changes to `cross_aggregation/aggregator.py`

1. **Fix corrupted import** at line 41 (remove spliced BetaConfluenceScorer from regime_meta_router block — **HARD BLOCKER**, file doesn't compile)
2. Add clean, independent `BetaConfluenceScorer` import with try/except
3. Build `market_context` dict once per aggregation run (via `build_market_context()`)
4. Call `score_pick(unified, market_context)` for every unified pick AFTER dict construction, BEFORE `aggregated.append()`
5. Add `beta_score` + `beta_breakdown` + `beta_qualified` to the `unified` dict
6. Log beta score to `best_breakdown` (confidence_breakdown) dict for audit trail
7. Append open picks (with beta scores, outcome=null) to `beta_score_tracker.json` at end of each run

### Changes to Normalizer Functions (REQUIRED — beta data will be silently dropped without this)

Update BOTH normalizer functions to preserve beta fields:
- `audit_trail/dashboard_generator.py:_normalize_pick` (~line 657)
- `cross_aggregation/consensus_outcome_tracker.py:_normalize_pick` (~line 349)

### New Data File: `cross_aggregation/data/beta_score_tracker.json`

**Ownership split:**
- **Aggregator** (`aggregator.py`) writes new open picks with beta scores (outcome=null) at end of each run
- **Consensus outcome tracker** (`consensus_outcome_tracker.py`) updates the `outcome` and `outcome_timestamp` fields when picks close (TP/SL hit). This is where outcome closure already happens (~line 380, 563), so it's the natural place to merge outcome data back into the tracker.

Accumulates every pick's scores and outcomes:

```json
{
  "picks": [
    {
      "symbol": "BTC-USD",
      "direction": "BUY",
      "timestamp": "2026-03-16T12:00:00Z",
      "production_score": 0.72,
      "beta_score": 85,
      "beta_breakdown": {"technical": 22, "onchain": 18, "sentiment": 13, "risk_reward": 17, "structure": 15},
      "beta_qualified": true,
      "outcome": null,
      "outcome_timestamp": null
    }
  ],
  "summary": {
    "total_picks": 0,
    "closed_picks": 0,
    "beta_qualified_wr": null,
    "beta_filtered_wr": null,
    "production_only_wr": null,
    "correlation": null
  }
}
```

**Decision point:** After 50+ closed picks with beta scores, compute which scoring system better predicts winners. If beta-qualified picks have significantly higher WR than production-only, consider promoting beta score to primary.

---

## Section 4: TP/SL Quality Enhancements

### 4.1 Volatility-Scaled TP/SL

Add to each strategy in `proven_research_strategies.py`:

```python
atr_val = atr(df, period=14)
tp = entry_price + (atr_val * tp_multiplier)  # tp_multiplier varies by strategy type
sl = entry_price - (atr_val * sl_multiplier)  # sl_multiplier varies by strategy type
```

**Multiplier guidelines by strategy type:**
- Momentum/breakout: TP 3.0x ATR, SL 1.5x ATR (2:1 R:R)
- Mean-reversion: TP 2.0x ATR, SL 1.0x ATR (2:1 R:R)
- Scalping: TP 1.5x ATR, SL 0.75x ATR (2:1 R:R)
- Swing: TP 4.0x ATR, SL 2.0x ATR (2:1 R:R)

### 4.2 Confidence-Weighted TP/SL Adjustments

After computing base TP/SL, scale by confidence and beta score:

```python
# Higher confidence → wider TP (let winners run), tighter SL
confidence_factor = 0.8 + (confidence * 0.4)  # range: 0.8 to 1.2
tp = entry + (base_tp_distance * confidence_factor)
sl = entry - (base_sl_distance / confidence_factor)

# If beta score available, further adjust
if beta_score and beta_score >= 70:
    tp = entry + (base_tp_distance * 1.1)  # 10% wider TP for beta-qualified
```

### 4.3 Multi-Timeframe TP/SL Confirmation

Before committing TP/SL levels, check the higher timeframe:
- If strategy runs on 1H, check 4H trend direction
- If 4H trend opposes the pick direction, tighten TP by 20% and widen SL by 10%
- If 4H trend confirms, use standard TP/SL

### 4.4 Adaptive R:R Based on Rolling Win Rate

Adjust target R:R based on strategy's recent performance:

```python
# Strategies with higher recent WR can afford tighter R:R
if rolling_wr >= 0.65:
    target_rr = 1.5  # can take more frequent smaller wins
elif rolling_wr >= 0.55:
    target_rr = 2.0  # standard
else:
    target_rr = 3.0  # need bigger wins to compensate lower WR
```

### 4.5 Order-Book Depth Filter (When Available)

For strategies with access to Binance order book data:
- Strong bid support below entry → tighten SL (support is real)
- Thin ask wall above entry → widen TP (less resistance)
- Thin bid support → widen SL (support may fail)

### 4.6 TP/SL Efficiency Dashboard Panel

Add to `audit_dashboard/template.html` (via dashboard generator):
- **TP Hit Rate** per strategy (what % of picks hit TP vs SL vs expired)
- **Average % captured** (how much of the TP distance was actually captured)
- **SL Efficiency** (how many SL hits were within 10% of SL level — tight stops getting hunted?)
- **Time to Resolution** (average hours from entry to TP/SL hit)

---

## Section 5: Updates Page Entry

After all implementation is complete, add an entry to `updates/index.html` documenting:

- 10 new research-backed strategies added (names, expected WRs, sources)
- Beta confluence scoring system (what it is, how it works, 5 pillars)
- Volatility-scaled TP/SL + confidence-weighted adjustments
- Dashboard A/B monitoring (side-by-side comparison, divergence alerts)
- Beta Analytics tab with TP/SL efficiency metrics
- Links to affected dashboards:
  - Alpha Engine: https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/alpha/
  - Cross-Aggregation Monitor: https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/monitor/

---

## Data Flow Summary

```
Research Files (6 documents)
    ↓ (extracted 10 strategies)
Alpha Engine / proven_research_strategies.py
    ↓ (generates picks with research_cohort tag + ATR-scaled TP/SL)
Alpha Engine Scanner (every 30 min via alpha-engine-live.yml)
    ↓ (active_picks.json)
Cross-Aggregation / aggregator.py
    ↓ (applies BOTH scoring systems)
    ├── Production Score: adj_conf * (0.5 + 0.5*wr_weight) * (0.5 + 2.0*sharpe_wt) * trust_mult
    ├── Beta Score: technical(25) + onchain(20) + sentiment(15) + rr(20) + structure(20)
    └── market_context built once per run (F&G, BTC trend, regime, flows)
    ↓
    ├── aggregated_picks.json (both scores)
    ├── beta_score_tracker.json (A/B tracking)
    └── Discord webhooks (both scores shown)
    ↓
Audit Dashboard / index.html
    ├── Pick tables with Beta Score column (colored bar)
    ├── Score Comparison panel (A/B)
    ├── Beta Analytics tab (TP/SL efficiency, scatter, divergence)
    ├── Research Cohort tracking (badge + group stats)
    └── Divergence alerts (>30 pt spread)
    ↓
After 50+ closed picks → Decision: which score wins?
```

---

## Section 6: Tournament System Integration

The beta scoring system plugs into the existing tournament/elimination architecture:

### Tournament Flow

```
Strategy Pool (all candidates incl. research cohort)
    ↓ scoring
Production Score + Beta Score (dual scoring)
    ↓ brackets
Group by asset class / timeframe / family
    ↓ selection
Top-N picks per bracket (combined weighted score)
    ↓ execution
Live picks logged to beta_score_tracker.json
    ↓ evaluation (after 30+ closed trades)
Kill criteria: WR < 45% OR PF < 1.0 OR beta divergence > 30
    ↓ elimination
Blocked → mutation sandbox → re-qualification
```

### Elimination Logic

Leverages existing kill criteria in `portfolio_manager.py` (`KILL_WR_THRESHOLD`, `KILL_PF_THRESHOLD`):
- After 30 closed trades: evaluate WR, PF, and beta-production divergence
- Strategies failing any threshold → `BLOCKED_SYSTEMS`
- Blocked strategies can be mutated (parameter tweaks) via `experimental_strategies.py` and re-tested

### Automated Elimination Script

**New file: `scripts/run_elimination.py`**
- Reads `beta_score_tracker.json`
- Applies kill criteria per strategy
- Updates `BLOCKED_SYSTEMS`
- Writes summary report CSV
- Run weekly (Monday 00:00 UTC) or on-demand

### Data Archival

Rotate `beta_score_tracker.json` weekly:
- Rename to `beta_score_tracker_YYYYMMDD.json`
- Keep last 12 weeks
- Dashboard loads most recent file automatically

---

## Files Modified / Created

| Action | File | Purpose |
|---|---|---|
| **CREATED** (stubs done) | `alpha_engine/proven_research_strategies.py` | 10 new strategy stubs → fill with logic |
| **MODIFIED** (done, needs fix) | `alpha_engine/crypto_strategies.py` | Import block — move to independent try/except |
| **CREATE/REWRITE** | `cross_aggregation/beta_confluence_scorer.py` | Beta scoring engine (fix existing broken file) |
| **MODIFY** | `cross_aggregation/aggregator.py` | Fix corrupted line 41, wire beta scorer, build market_context |
| **MODIFY** | `audit_dashboard/portfolio_manager.py` | Add `RESEARCH_COHORT_STRATEGIES` (NOT PROVEN), add beta score to payload |
| **MODIFY** | `audit_trail/dashboard_generator.py` | Add beta score column, comparison panel, Beta Analytics tab to template |
| **MODIFY** | `audit_trail/dashboard_generator.py:_normalize_pick` | Add beta_score/beta_breakdown/beta_qualified to normalized dict |
| **MODIFY** | `cross_aggregation/consensus_outcome_tracker.py:_normalize_pick` | Add beta_score/beta_breakdown/beta_qualified to normalized dict |
| **CREATE** | `cross_aggregation/data/beta_score_tracker.json` | A/B score tracking data |
| **CREATE** | `scripts/run_elimination.py` | Automated weekly elimination script |
| **MODIFY** | `alpha_engine/indicators.py` | Add missing indicators (stochastic_rsi, mfi, etc.) |
| **MODIFY** | `updates/index.html` | Document all enhancements |

---

## Known Issues to Fix During Implementation

| # | Severity | File | Issue | Fix |
|---|---|---|---|---|
| 1 | CRITICAL | `aggregator.py:41` | Corrupted import — BetaConfluenceScorer spliced into regime_meta_router try/except with literal `\n\n` | Remove corrupted line, add clean independent try/except |
| 2 | CRITICAL | `beta_confluence_scorer.py:17` | Semicolon instead of colon (`-> Tuple[...];`) = SyntaxError | Rewrite file per this spec |
| 3 | CRITICAL | `beta_confluence_scorer.py` | Returns Tuple but spec expects dict — TypeError on `beta_result["total"]` | Rewrite to return dict per spec |
| 4 | CRITICAL | `beta_confluence_scorer.py:1` | File is malformed HTML-escaped one-liner, no usable class | Full rewrite required |
| 5 | HIGH | `dashboard_generator.py:657` | `_normalize_pick` returns fixed dict, drops unknown fields like beta_score | Add beta fields to normalized dict |
| 6 | HIGH | `consensus_outcome_tracker.py:349` | `_normalize_pick` same issue — drops beta fields | Add beta fields to normalized dict |
| 7 | HIGH | `index.html` | Auto-generated by `dashboard_generator.py` — direct edits are ephemeral | All UI changes go in template/generator |
| 8 | HIGH | `portfolio_manager.py:2379,2928` | Adding research strategies to PROVEN_STRATEGIES routes them as proven/golden | Use separate RESEARCH_COHORT_STRATEGIES set |
| 9 | IMPORTANT | `beta_confluence_scorer.py` | Reads `entry`/`tp`/`sl` but unified picks use `entry_price`/`target_price`/`stop_price` | Use fallback: `pick.get("entry") or pick.get("entry_price")` |
| 10 | IMPORTANT | `crypto_strategies.py:~4012` | Research strategies import nested in wrong except block | Move to own independent try/except |
| 11 | IMPORTANT | `indicators.py` | 9 of 21 indicators listed don't exist (stochastic_rsi, mfi, etc.) | Add to indicators.py before strategy implementation |
| 12 | IMPORTANT | `aggregator.py` | No one builds `market_context` dict | Add `build_market_context()` with 5s timeout per API call |
| 13 | MEDIUM | `portfolio_manager.py:2515` | Production score is unbounded — can't compare to 0-100 beta score | Add sigmoid normalization helper |
| 14 | MEDIUM | `confidence_calculator.py:226` | Dempster-Shafer can output >1 (invalid probability) | Clamp: `min(1.0, ds_result)` in beta scorer |
| 15 | MEDIUM | `build_market_context()` | External API latency could timeout aggregation run | Wrap each request with `timeout=5`, fallback to last-known cached values |

---

## Section 7: High-Value Enhancements (from review feedback)

### Priority: HIGH (implement in this sprint)

**7.1 Adaptive Position Sizing** — In `portfolio_manager.py` `score_pick()`, compute dynamic `position_pct`:
```python
position_pct = base_pct * (risk_reward / avg_risk_reward) * (confidence + beta_score/100)
```
Scales up capital for high-RR + high-confidence signals, scales down for marginal ones.

**7.2 Multi-Timeframe Confirmation Engine** — New file `alpha_engine/multi_tf.py`:
- `tf_confirmation(symbol, direction, base_tf, data)` → checks same indicator on higher TF
- 1H signals check 4H, 4H check 1D
- If higher TF opposes direction, tighten TP by 20%, widen SL by 10%
- Wired into aggregator before scoring

**7.3 Order-Book Depth Pillar** — New file `cross_aggregation/order_book_depth.py`:
- Pull Level-2 depth from Binance: `order_book_imbalance = (bid_vol - ask_vol) / (bid_vol + ask_vol)`
- Feeds into beta scorer as bonus points in On-Chain Support pillar (max +5 pts)
- Adds "Liquidity Heatmap" badge on dashboard

**7.4 Missing Indicators** — Add to `alpha_engine/indicators.py`:
- `stochastic_rsi`, `mfi`, `supertrend`, `dema`, `tema`, `zlema`, `pivot_points`, `donchian_channel`, `choppiness_index`, `fear_and_greed`
- Required before strategies can be fully implemented

### Priority: MEDIUM (implement after core is stable)

**7.5 Dynamic Beta-Qualified Threshold** — Instead of hard 70/100, compute 80th percentile of beta scores per run. Stores threshold in `beta_score_tracker.json`.

**7.6 Rolling WR-Based Adaptive R:R** — Per-strategy rolling 30-day WR stored in SQLite. WR > 60% → target 1.5:1 R:R; WR < 45% → target 2.5:1 R:R.

**7.7 Strategy Feature Flags** — `feature_flags` dict per strategy: `{use_beta, use_multi_tf, use_order_book}`. Enables granular experimentation.

**7.8 Market-Context Caching** — Cache `build_market_context()` results for 5 min in local JSON file. API failure → fallback to cached values.

### Priority: LOW (implement when bandwidth allows)

**7.9 A/B Evaluation Dashboard Tab** — Chart.js scatter plot of production vs beta scores, correlation coefficient, WR comparison.

**7.10 TP/SL Backtesting Harness** — `scripts/backtest_tp_sl.py`: grid search over ATR multipliers, confidence weights, beta thresholds → `backtest_results.csv`.

**7.11 Automated Elimination Script** — `scripts/run_elimination.py`: reads tracker, applies kill criteria, updates BLOCKED_SYSTEMS, writes CSV report. Weekly cron.

**7.12 Performance Documentation** — Post-run step writes `docs/strategy_performance/performance_summary.md` with per-strategy WR/PF/Sharpe/beta-qualified counts.

---

## Risk Mitigation

- **Requires normalizer updates:** `_normalize_pick` in `dashboard_generator.py` and `consensus_outcome_tracker.py` returns fixed-schema dicts — beta fields MUST be added to both or data is silently dropped. This is NOT optional.
- **Graceful degradation:** If beta scorer fails, picks still get production score (try/except wrapper)
- **API fallback:** LunarCrush sentiment pillar falls back to Fear & Greed if `LUNARCRUSH_API` not set
- **Regime fallback:** Market Structure pillar uses ADX-based regime detection if `regime_terminal` data unavailable
- **Cohort isolation:** Research strategies tagged separately — if they underperform, they can be killed without touching existing strategies
- **TP/SL safety:** ATR-scaled stops ensure minimum 1.0 ATR distance regardless of confidence adjustments
- **Indicator gaps:** Strategies compute missing indicators inline rather than depending on non-existent functions
