# Hybrid Confluence + Tournament System Design

**Date:** 2026-03-07
**Status:** Approved
**Reviewed by:** Claude (Anthropic), Grok (xAI), Gemini (Google), User

## Problem Statement

The Alpha Engine's forward performance is critically underperforming:
- **36% win rate** across 147 closed trades (vs 60%+ backtest)
- **-$5,978 P&L** (-2.99%), profit factor 0.53
- Only **6 out of 100+** strategies are profitable in live trading
- 50-70% degradation from backtest to forward performance
- No effective strategy pairing — each strategy trades solo

## Design Goals

1. **Improve win rate** from 36% to 55%+ through cross-family confluence filtering
2. **Preserve strategy diversity** — every strategy gets a fair chance
3. **Enable strategy pairing** — weak strategies can win through combination
4. **Test risk levels empirically** — 3 parallel portfolios determine optimal risk
5. **ML-driven evolution** — system discovers non-obvious winning combinations

## Architecture Overview

```
100+ strategies fire raw signals
    ↓
Confluence Engine: group by symbol+direction, check family diversity
    ↓  (only signals with 2+ family agreement pass)
Tournament Engine: look up tier for each strategy/combo
    ↓  (position size determined by tier)
Portfolio Manager: route to Conservative/Moderate/Aggressive
    ↓  (apply portfolio-specific filters + circuit breakers)
ML Ranker: final scoring (existing 25-feature model)
    ↓
Execute: write to active_picks.json + SQLite
```

## 1. Indicator Family Classification

Every strategy is tagged with exactly one indicator family. Confluence requires agreement
across **different** families to reduce correlated false positives.

| Family | What it measures | Example strategies |
|--------|-----------------|-------------------|
| **Momentum** | Speed/direction of price change | RSI, MACD, Connors RSI, StochRSI, cross_sectional_momentum, rsi_macd_confluence, rsi_hidden_divergence |
| **Trend** | Directional bias | EMA stack, Ichimoku, Hull MA, ADX, btc_200d_sma_bounce, multi_timeframe_ema_stack, pentoshi_htf_structure |
| **Volume** | Buying/selling pressure | OBV, VWAP, Volume Profile, CMF, MFI, volume_climax_reversal, obv_divergence_breakout, cmf_zero_line_cross |
| **Sentiment** | Market psychology | Fear & Greed, funding rate, social momentum, ape_wisdom_social_momentum, crypto_fear_greed_contrarian |
| **On-Chain** | Blockchain fundamentals | MVRV, hash ribbon, whale flows, stablecoin supply, SOPR, hayes_liquidity_index, onchain_composite_score |
| **Structure** | Price structure/levels | Support/resistance, FVG, BOS, swing failure, Wyckoff, liquidity_sweep_reversal, fractal_support_resistance |
| **Volatility** | Expansion/contraction | Bollinger, Keltner, ATR breakout, DVOL, vol_risk_premium, dynamic_momentum_scaling, dvol_extreme_buy |

### Family Assignment Rules
- Each strategy belongs to **one** primary family
- If a strategy uses indicators from multiple families (e.g., RSI + Volume), assign to the
  family of its **primary signal** (the indicator that triggers the entry)
- Family assignments stored in `alpha_engine/config.py` as `STRATEGY_FAMILIES` dict

## 2. Confluence Engine

### Core Logic

A **confluence signal** forms when 2+ strategies from **different indicator families**
fire on the same symbol, same direction (BUY or SELL), within a configurable time window.

```python
class ConfluenceEngine:
    TIME_WINDOW = timedelta(hours=4)  # configurable per portfolio

    def process_signals(self, raw_signals: list[Signal]) -> list[ConfluenceSignal]:
        """Group signals by (symbol, direction), check family diversity."""
        groups = defaultdict(list)
        for sig in raw_signals:
            key = (sig.symbol, sig.direction)
            groups[key].append(sig)

        results = []
        for (symbol, direction), signals in groups.items():
            # Filter to signals within time window
            signals = self._within_window(signals)
            # Count unique families
            families = {s.family for s in signals}
            if len(families) >= self.min_families:
                results.append(ConfluenceSignal(
                    symbol=symbol,
                    direction=direction,
                    contributing_strategies=signals,
                    family_count=len(families),
                    confluence_score=self._score(signals, families),
                ))
        return results
```

### Confluence Scoring

```
confluence_score = (
    family_count_weight * num_unique_families +      # 40%
    tier_weight * avg_strategy_tier +                 # 30%
    ml_weight * avg_ml_score +                        # 20%
    agreement_weight * num_agreeing_strategies         # 10%
)
```

Higher confluence scores get priority when position limits are reached.

### Time Window Handling (Grok's concern: race conditions)

- Signals are **batched per scanner run** (every 15-30 min), not event-driven
- The time window looks back 4 hours from the current scan
- No race conditions because processing is synchronous within each scan cycle
- Signals are deduplicated by (strategy, symbol, direction) per window

## 3. Tournament Engine

### Tier Progression

```
Challenger (paper-only, $0 risk)
    ↓ 10+ trades, WR ≥ threshold, PF > 1.0
Bronze (0.5% risk per trade)
    ↓ 25+ trades, WR ≥ threshold, Sharpe > 0.5
Silver (1.0% risk per trade)
    ↓ 50+ trades, WR ≥ threshold, Sharpe > 1.0, PF > 1.3
Gold (2.0% risk per trade)
```

### Promotion Criteria (per portfolio risk profile)

| Criterion | Conservative | Moderate | Aggressive |
|-----------|-------------|----------|------------|
| WR threshold | 60% | 50% | 45% |
| Min trades for Bronze | 10 | 10 | 10 |
| Min trades for Silver | 25 | 25 | 25 |
| Min trades for Gold | 50 | 50 | 50 |
| Profit factor min | 1.3 | 1.2 | 1.0 |

### Demotion Rules (EMA-based — per Google/Gemini review)

Raw consecutive-loss demotion causes tier churn (even a 65% WR strategy has ~4.3%
chance of 3 consecutive losses). Use EMA-smoothed win rate instead:

```
ema_wr = alpha * latest_result + (1 - alpha) * previous_ema_wr
# alpha = 0.1 (slow adaptation), latest_result = 1.0 (win) or 0.0 (loss)
# Demote when ema_wr < (tier_threshold - 10%) for 5+ consecutive evaluations
```

- **EMA WR below threshold** for 5+ evaluations → drop 1 tier
- **Max drawdown exceeds circuit breaker** → freeze to Challenger
- **Zero trades in 30 days** → drop to Challenger (inactivity penalty)

### Time-Weighted Performance Decay

- Recent trades (last 2 weeks): weight **1.0**
- Older trades (2-6 weeks): weight **0.7**
- Historical (6+ weeks): weight **0.4**
- Re-evaluate tier eligibility weekly or every 10 trades

### Per-Regime Tier Tracking

Each strategy has SEPARATE tournament records per market regime:
- A strategy can be **Gold-in-trending + Bronze-in-ranging** simultaneously
- Leverages existing `STRATEGY_REGIME_MAP` and `detect_market_regime()`
- Prevents unfair punishment during regime shifts

### Combo Strategy Tracking

When 2+ strategies fire together as a confluence signal, the **combination** is tracked
as its own entity with independent tier progression:

```python
combo_id = "rsi_hidden_divergence+volume_climax_reversal"  # sorted alphabetically
```

- Combos have their own win/loss record, WR, Sharpe, tier
- A combo can reach Gold even if both constituent strategies are stuck in Bronze
- Combo tier is used for position sizing when that specific combination fires again
- Max combo size: 4 strategies (beyond that, track the top-4 by ML score)

### Persistence

Tournament state stored in SQLite (`alpha.db`):

```sql
CREATE TABLE tournament_state (
    entity_id TEXT PRIMARY KEY,    -- strategy name or combo_id
    entity_type TEXT,              -- 'strategy' or 'combo'
    tier TEXT DEFAULT 'challenger', -- challenger/bronze/silver/gold
    portfolio TEXT,                 -- conservative/moderate/aggressive
    total_trades INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    win_rate REAL DEFAULT 0,
    sharpe REAL DEFAULT 0,
    profit_factor REAL DEFAULT 0,
    max_drawdown REAL DEFAULT 0,
    consecutive_losses INTEGER DEFAULT 0,
    last_trade_date TEXT,
    promoted_at TEXT,
    demoted_at TEXT,
    updated_at TEXT
);
```

## 4. Parallel Portfolio Manager

### Three Independent Portfolios

Each portfolio tracks its own P&L, positions, and circuit breaker state:

| Parameter | Conservative | Moderate | Aggressive |
|-----------|-------------|----------|------------|
| Min confluence families | 3+ | 2+ | 2+ |
| Promotion WR threshold | 60% | 50% | 45% |
| Circuit breaker (max DD) | 5% | 10% | 15% |
| Max open positions | 10 | 20 | 30 |
| Max per symbol | 1 | 2 | 3 |
| Max same-direction crypto | 4 | 6 | 8 |
| Starting capital (paper) | $10,000 | $10,000 | $10,000 |
| Kelly cap | 3% | 5% | 8% |

### Circuit Breaker Logic

```python
if portfolio.current_drawdown >= portfolio.circuit_breaker_pct:
    portfolio.freeze()       # no new picks
    portfolio.log_freeze()   # record timestamp + drawdown
```

### Graduated Recovery Protocol (per Google/Gemini review)

```
Circuit Breaker Tripped:
  1. Immediately halt new entries
  2. Allow existing positions to hit TP/SL naturally
  3. After 24h cooldown: resume at 50% position size
  4. After 7 days without new drawdown: resume full size
  5. If breaker trips 2x in 30 days: pause portfolio for manual review
```

### Portfolio Comparison Dashboard

After 90 days, generate a comparison report:
- Total P&L per portfolio
- Win rate per portfolio
- Sharpe per portfolio
- Best/worst strategies per portfolio
- Recommendation: which profile to promote to "primary"

## 5. ML Pairing Discovery

### Phase 1: Manual Bootstrap (Day 1)

Define logical cross-family pairings based on trading logic:

```python
MANUAL_PAIRINGS = {
    "momentum_volume": {
        "families": ["momentum", "volume"],
        "rationale": "RSI oversold + volume surge confirms real buying pressure",
        "example": "rsi_hidden_divergence + volume_climax_reversal",
    },
    "trend_sentiment": {
        "families": ["trend", "sentiment"],
        "rationale": "EMA alignment + extreme fear = high-probability trend continuation",
        "example": "multi_timeframe_ema_stack + crypto_fear_greed_contrarian",
    },
    "onchain_volatility": {
        "families": ["on_chain", "volatility"],
        "rationale": "Whale accumulation + volatility expansion = breakout incoming",
        "example": "whale_accumulation_detector + atr_volatility_breakout",
    },
    "structure_momentum": {
        "families": ["structure", "momentum"],
        "rationale": "Support bounce + RSI divergence = reversal confirmation",
        "example": "fractal_support_resistance + rsi_hidden_divergence",
    },
    "sentiment_onchain": {
        "families": ["sentiment", "on_chain"],
        "rationale": "Extreme fear + whale buying = smart money accumulation",
        "example": "crypto_fear_greed_contrarian + whale_accumulation_detector",
    },
}
```

### Phase 2: ML Discovery (After 200+ closed combo trades)

Train a LightGBM model on combo outcomes:

**Features:**
- strategy_a_encoded, family_a_encoded
- strategy_b_encoded, family_b_encoded
- regime (bull/bear/sideways)
- symbol_category (major/alt/meme/forex/equity)
- time_gap_minutes (between signals)
- avg_ml_score (of contributing signals)
- avg_tier (of contributing strategies)
- market_fear_greed, funding_rate, btc_dominance

**Target:** Binary win/loss

**Output:** Predicted win probability for each possible pair. Surface non-obvious
combos with predicted WR > 55% that weren't in manual pairings.

**Training trigger:** Auto-retrain every 50 new closed combo trades.

## 6. New Files

```
alpha_engine/
├── confluence_engine.py     # ~200 lines: voter aggregation, family matching, scoring
├── tournament_engine.py     # ~250 lines: tier management, promotion/demotion, combos
├── portfolio_manager.py     # ~200 lines: 3 parallel portfolios, circuit breakers
├── combo_tracker.py         # ~150 lines: combo ID generation, ML feature extraction
├── ml_pairing.py            # ~200 lines: Phase 1 frequency table, Phase 2 LightGBM
└── config.py                # Updated: STRATEGY_FAMILIES dict, portfolio params
```

### Integration Points

- `scanner.py`: After raw signals generated, call `confluence_engine.process_signals()`
- `scanner.py`: Before position sizing, call `tournament_engine.get_tier(entity_id, portfolio)`
- `scanner.py`: Route picks through `portfolio_manager.allocate(pick, portfolio)`
- `database.py`: Add `tournament_state` and `combo_trades` tables
- `ml_ranker.py`: Add `confluence_score` and `combo_tier` as new features (27 total)

## 7. Migration Plan

### Week 1: Foundation
- Implement `confluence_engine.py` and `tournament_engine.py`
- Add `STRATEGY_FAMILIES` mapping for all 100+ strategies
- Add `tournament_state` table to SQLite schema
- Wire confluence engine into scanner.py (feature-flagged)

### Week 2: Portfolios + Combos
- Implement `portfolio_manager.py` with 3 parallel portfolios
- Implement `combo_tracker.py` for pairing identification
- Update dashboard to show portfolio comparison + combo stats
- Deploy with all 3 portfolios running in paper mode

### Week 3: ML + Refinement
- Implement `ml_pairing.py` Phase 1 (manual pairings + frequency table)
- Add confluence metrics to the Alpha Engine dashboard
- Begin collecting combo trade data for future ML training
- Monitor and adjust family assignments based on early results

### Week 4+: Evolution
- Once 200+ combo trades accumulated, train Phase 2 ML model
- Surface discovered pairings on dashboard
- Promote best-performing portfolio to primary
- Iterate on thresholds based on empirical data

## 8. Success Metrics (90-Day Target)

| Metric | Current | Target | How measured |
|--------|---------|--------|-------------|
| Forward win rate | 36% | 55%+ | Closed picks in alpha.db |
| Profit factor | 0.53 | 1.3+ | Gross wins / gross losses |
| Max drawdown | -302% | < 15% | Portfolio manager tracking |
| Profitable strategies | 6/100 | 20+/100 | Including combos |
| Sharpe ratio | Negative | > 1.0 | Annualized risk-adjusted return |
| Combo discovery | 0 | 10+ winning combos | ML pairing model output |

## 9. Risk Mitigation

- **Complexity risk:** Phased rollout with feature flags; each module independently testable
- **Data starvation (Grok's concern):** Aggressive portfolio uses 2+ confluence (not 3+), preserving volume
- **Race conditions (Grok's concern):** Batch processing per scan cycle, no event-driven timing
- **Overfitting combos:** Minimum 15 trades before combo tier promotion; Monte Carlo validation
- **Circuit breaker false positives:** 7-day cool-off with 50% recovery threshold before unfreeze
