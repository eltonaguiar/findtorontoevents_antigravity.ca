# Prediction Market Signal Engine — Technical Report

**Date:** 2026-05-20  
**Module:** `prediction_market_signals.py` (2325 lines)  
**Author:** Alpha Engine Team  
**Status:** Production Ready

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Signal Methodology](#2-signal-methodology)
3. [API Endpoints](#3-api-endpoints)
4. [Module Reference](#4-module-reference)
5. [Integration Instructions](#5-integration-instructions)
6. [GHA Workflow Configuration](#6-gha-workflow-configuration)
7. [Output Format](#7-output-format)
8. [Calibration & Quality](#8-calibration--quality)
9. [Performance Considerations](#9-performance-considerations)

---

## 1. Architecture Overview

```
                    ┌─────────────────────────────────────┐
                    │         DATA SOURCES                │
                    │  ┌──────────┐      ┌──────────┐    │
                    │  │Polymarket│      │  Kalshi  │    │
                    │  │Gamma+CLOB│      │  API v2  │    │
                    │  └────┬─────┘      └────┬─────┘    │
                    └───────┼────────────────┼──────────┘
                            │                │
              ┌─────────────┘                └──────────────┐
              ▼                                              ▼
    ┌──────────────────┐                          ┌──────────────────┐
    │  Gamma API Client │                          │  Kalshi Client   │
    │  • Events         │                          │  • KXBTC         │
    │  • Market Meta    │                          │  • KXETH         │
    │  • Slug Search    │                          │  • KXSOL + 6 more│
    └────────┬─────────┘                          └────────┬─────────┘
             │                                             │
             ▼                                             ▼
    ┌──────────────────┐                          ┌──────────────────┐
    │  CLOB API Client │                          │ Kalshi Signals   │
    │  • Price History │                          │ Extractor        │
    │  • Order Book    │                          └────────┬─────────┘
    └────────┬─────────┘                                   │
             │                                             │
             └───────────────────┬─────────────────────────┘
                                 │
                                 ▼
              ┌──────────────────────────────────┐
              │      SIGNAL EXTRACTOR ENGINE       │
              │  ┌──────────────────────────────┐  │
              │  │ Implied Probability Curve    │  │  (25%)
              │  │ Cumulative distribution from │  │
              │  │ "reach $X" / "dip $Y" mkts  │  │
              │  └──────────────────────────────┘  │
              │  ┌──────────────────────────────┐  │
              │  │ Probability Momentum         │  │  (40%) LEADING
              │  │ 4h rate-of-change >5% = SIGNAL│  │
              │  └──────────────────────────────┘  │
              │  ┌──────────────────────────────┐  │
              │  │ Dip Probability Skew         │  │  (35%)
              │  │ dip_probs / (dip+reach)      │  │
              │  └──────────────────────────────┘  │
              └─────────────────┬──────────────────┘
                                │
                                ▼
              ┌──────────────────────────────────┐
              │     CONSENSUS SCORER (0-100)      │
              │  Weighted ensemble of three       │
              │  components into unified score    │
              │                                   │
              │  >70  → STRONG_BULLISH           │
              │  55-70 → BULLISH                 │
              │  45-55 → NEUTRAL                 │
              │  30-45 → BEARISH                 │
              │  <30  → STRONG_BEARISH           │
              └─────────────────┬──────────────────┘
                                │
                                ▼
              ┌──────────────────────────────────┐
              │    TRADING SIGNAL CONVERTER       │
              │  → LONG/SHORT + confidence       │
              │  → premium_signals.json format   │
              └─────────────────┬──────────────────┘
                                │
                                ▼
              ┌──────────────────────────────────┐
              │     SIGNAL QUALITY TRACKER        │
              │  • Accuracy logging (SQLite)      │
              │  • Calibration scoring (Brier)    │
              │  • Alert on degradation           │
              └──────────────────────────────────┘
```

---

## 2. Signal Methodology

### 2.1 Implied Probability Curve (Weight: 25%)

**Purpose:** Build cumulative probability distribution from price-target markets and compare distribution median to spot price.

**Method:**
1. Collect all "reach $X" and "dip to $Y" markets for the target asset
2. Pair each target price with its YES probability
3. Compute weighted median of target prices (weights = probabilities)
4. Estimate spot price from the target with probability closest to 0.5 (market most uncertain)
5. Compute price premium: (median_implied - spot) / spot
6. Score: `50 + premium * 250` (clamped to 0-100)

**Interpretation:**
- High score (>50): Market implies price will go higher (bullish)
- Low score (<50): Market implies price will go lower (bearish)

### 2.2 Probability Momentum (Weight: 40%) — LEADING INDICATOR

**Purpose:** Detect sharp crowd repositioning that precedes spot price moves.

**Method:**
1. For each market, fetch hourly price history from CLOB API
2. Compute: `delta = current_prob - prob_4h_ago`
3. Rank by |delta|; take top 3 markets
4. Score: `50 + mean(delta_top3) * 250` (clamped to 0-100)
5. Threshold: |delta| > 0.05 (5% in 4 hours) → signal trigger

**Why it works:** Prediction market participants are often informed traders. Sharp probability moves reflect new information being impounded into prices before the spot market fully reacts.

**Parameters:**
- Window: 4 hours (configurable via `MOMENTUM_WINDOW_HOURS`)
- Threshold: 5% (`MOMENTUM_THRESHOLD`)
- Top-N markets considered: 3

### 2.3 Dip Probability Skew (Weight: 35%)

**Purpose:** Gauge fear vs greed sentiment by comparing dip probabilities to reach probabilities.

**Method:**
1. Sum all YES probabilities for "dip to $Y" markets
2. Sum all YES probabilities for "reach $X" markets
3. Compute: `skew = dip_sum / (dip_sum + reach_sum)`
4. Score: `(1 - skew) * 100` (clamped to 0-100)

**Interpretation:**
- skew > 0.6 → fear dominant → score < 40 → BEARISH
- skew < 0.4 → greed dominant → score > 60 → BULLISH
- 0.4-0.6 → balanced → 40-60 → NEUTRAL

### 2.4 Consensus Score Formula

```
score = 0.40 * momentum_component
      + 0.35 * dip_skew_component
      + 0.25 * implied_curve_component
```

Result mapped to direction:

| Score Range | Direction | Trading Signal |
|-------------|-----------|----------------|
| >= 70       | STRONG_BULLISH | LONG (confidence 0.70-0.95) |
| 55-69       | BULLISH | LONG (confidence 0.55-0.70) |
| 45-54       | NEUTRAL | No signal (filtered out) |
| 30-44       | BEARISH | SHORT (confidence 0.30-0.45 inverted) |
| < 30        | STRONG_BEARISH | SHORT (confidence 0.70-0.95) |

### 2.5 Confidence Calibration

Confidence is adjusted by calibration score:
```
adjusted_confidence = base_confidence * (0.5 + 0.5 * calibration_skill)
```

If Kalshi signals disagree with Polymarket consensus, confidence is penalized:
```
confidence *= 0.7  # 30% penalty for disagreement
```

---

## 3. API Endpoints

### 3.1 Polymarket Gamma API

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `https://gamma-api.polymarket.com/events` | GET | List active events (paginated, filterable) |
| `https://gamma-api.polymarket.com/events?slug={slug}` | GET | Fetch specific event by slug |
| `https://gamma-api.polymarket.com/markets` | GET | List active markets |

**Query Parameters:**
- `active=true` — only active markets
- `limit={N}` — page size (max ~100)
- `offset={N}` — pagination offset
- `order=volume` — sort by volume
- `ascending=false` — descending order
- `tags=crypto` — tag filter

**No authentication required.** Rate limits: ~10 req/s (gentle backoff implemented).

### 3.2 Polymarket CLOB API

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `https://clob.polymarket.com/prices-history` | GET | Price time series for token |
| `https://clob.polymarket.com/book` | GET | Live order book (bids/asks) |

**Query Parameters for prices-history:**
- `token_id={id}` — CLOB token ID (from Gamma API)
- `fidelity={min,hour,day}` — candle aggregation
- `start_ts={unix}` — start timestamp
- `end_ts={unix}` — end timestamp

**No authentication required.** Cached locally (15-min TTL).

### 3.3 Kalshi API v2

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `https://api.elections.kalshi.com/trade-api/v2/markets` | GET | List markets in a series |
| `https://api.elections.kalshi.com/trade-api/v2/markets/{id}/orderbook` | GET | Market order book |
| `https://api.elections.kalshi.com/trade-api/v2/trades` | GET | Recent trades |

**Supported Crypto Series:**

| Series | Asset | Description |
|--------|-------|-------------|
| KXBTC | Bitcoin | BTC price targets, range markets |
| KXETH | Ethereum | ETH price targets, range markets |
| KXSOL | Solana | SOL price targets |
| KXDOGE | Dogecoin | DOGE price targets |
| KXXRP | XRP | XRP price targets |
| KXAVAX | Avalanche | AVAX price targets |
| KXLINK | Chainlink | LINK price targets |
| KXDOT | Polkadot | DOT price targets |
| KXLTC | Litecoin | LTC price targets |

**Authentication:** Optional for public endpoints. API key in `KALSHI_API_KEY` env var or `--kalshi-key` flag.

---

## 4. Module Reference

### 4.1 Core Classes

#### `PMCacheManager`
SQLite-backed cache with three tables:
- `price_cache` — token_id → price history JSON (TTL: 15 min)
- `meta_cache` — generic key-value for API responses (TTL: 60 min)
- `accuracy_log` — resolved market outcomes for calibration

**Key Methods:**
```python
get_price_history(token_id) -> Optional[List[dict]]
set_price_history(token_id, data)
get_meta(cache_key) -> Optional[Any]
set_meta(cache_key, data)
log_accuracy(record: AccuracyRecord)
calibration_by_bins(asset, num_bins=10) -> pd.DataFrame
```

#### `PolymarketGammaClient`
Event and market metadata discovery.

**Key Methods:**
```python
fetch_active_crypto_events(limit=100, offset=0) -> List[PMEvent]
fetch_event_by_slug(slug) -> Optional[PMEvent]
fetch_all_crypto_events_deep(max_pages=10) -> List[PMEvent]
search_markets_by_keyword(keyword, limit=50) -> List[PMMarket]
```

#### `PolymarketClobClient`
Price history and order book data.

**Key Methods:**
```python
fetch_price_history(token_id, fidelity="hour") -> List[PMPricePoint]
fetch_price_history_bulk(token_ids) -> Dict[str, List[PMPricePoint]]
fetch_order_book(token_id) -> Dict[str, Any]
fetch_mid_price(token_id) -> float
```

#### `KalshiClient`
CFTC-regulated crypto series data.

**Key Methods:**
```python
fetch_crypto_series(ticker, active_only=True) -> List[Dict]
fetch_crypto_series_bulk(tickers) -> Dict[str, List[Dict]]
extract_yes_probability(market) -> float
fetch_series_trades(series_ticker, limit=1000) -> List[Dict]
```

#### `SignalExtractor`
Core signal computation engine.

**Key Methods:**
```python
implied_probability_curve(asset, events=None) -> Optional[ImpliedCurveReading]
probability_momentum(asset, events=None, window_hours=4) -> List[ProbabilityMomentumReading]
dip_probability_skew(asset, events=None) -> Optional[DipSkewReading]
kalshi_crypto_signals(kalshi=None) -> Dict[str, List[Dict]]
strongest_momentum_signals(asset, threshold=0.05, top_n=5) -> List[ProbabilityMomentumReading]
```

#### `ConsensusScorer`
Weighted signal combination.

**Key Methods:**
```python
compute(asset, momentum, dip_skew, implied_curve) -> ConsensusScore
compute_batch(assets, extractor) -> Dict[str, ConsensusScore]
classify_direction(score) -> SignalDirection
```

#### `SignalQualityTracker`
Accuracy monitoring and calibration.

**Key Methods:**
```python
record_resolution(market_id, source, predicted_prob, actual_outcome, ...)
get_accuracy_summary(asset=None, source=None) -> Dict
calibration_score(asset=None) -> Dict
check_calibration_alert(asset=None) -> Optional[str]
```

#### `TradingSignalConverter`
Convert consensus to trading signal format.

**Key Methods:**
```python
consensus_to_trading_signal(consensus, kalshi_signals=None, calibration_score=None) -> Optional[TradingSignal]
convert_batch(consensus_scores, kalshi_data, quality_tracker) -> List[TradingSignal]
```

#### `PredictionMarketPipeline`
End-to-end orchestrator.

**Key Methods:**
```python
run(assets, include_kalshi=True) -> Dict[str, Any]          # Full daily pipeline
run_momentum_only(assets) -> Dict[str, Any]                 # Hourly fast pipeline
save_signals(results, filepath) -> Path
save_to_premium_format(signals, filepath) -> Path
```

---

## 5. Integration Instructions

### 5.1 Direct Python Import

```python
from prediction_market_signals import (
    PredictionMarketPipeline,
    SignalExtractor,
    ConsensusScorer,
    SignalQualityTracker,
)

# Full pipeline
pipeline = PredictionMarketPipeline(
    cache_dir=Path("./alpha_engine/data"),
    kalshi_api_key="your_key",  # optional
    enable_kalshi=True,
)
results = pipeline.run(assets=["btc", "eth", "sol"])

# Access outputs
for sig in results["trading_signals"]:
    print(f"{sig['symbol']}: {sig['direction']} (conf={sig['confidence']:.2f})")

# Save to premium_signals.json
pipeline.save_to_premium_format(
    [TradingSignal(**s) for s in results["trading_signals"]]
)
```

### 5.2 CLI Usage

```bash
# Full daily pipeline
python prediction_market_signals.py full --assets btc,eth,sol --output ./alpha_engine/data

# Hourly momentum-only
python prediction_market_signals.py momentum --assets btc,eth --output ./alpha_engine/data

# With Kalshi API key
python prediction_market_signals.py full --assets btc,eth,sol,kxbtc,kxeth --kalshi-key $KALSHI_API_KEY
```

### 5.3 Individual Components

```python
from prediction_market_signals import (
    PolymarketGammaClient,
    PolymarketClobClient,
    KalshiClient,
    SignalExtractor,
)

# Just fetch Polymarket events
gamma = PolymarketGammaClient()
events = gamma.fetch_active_crypto_events(limit=50)
for ev in events:
    print(f"{ev.title}: {len(ev.markets)} markets, ${ev.volume:,.0f} volume")

# Just fetch price history
clob = PolymarketClobClient()
points = clob.fetch_price_history(token_id="abc123", fidelity="hour")
print(f"Got {len(points)} price points")

# Just Kalshi
kalshi = KalshiClient(api_key="optional_key")
btc_markets = kalshi.fetch_crypto_series("KXBTC")
for m in btc_markets[:3]:
    prob = kalshi.extract_yes_probability(m)
    print(f"{m['title']}: YES={prob:.1%}")
```

---

## 6. GHA Workflow Configuration

### 6.1 Daily Full Pipeline (`.github/workflows/pm_signals_daily.yml`)

```yaml
name: PM Signals — Daily Full Pipeline

on:
  schedule:
    - cron: "0 6 * * *"   # 06:00 UTC daily
  workflow_dispatch:

jobs:
  pm-signals:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install pandas numpy requests
      - name: Run PM Signal Pipeline
        env:
          KALSHI_API_KEY: ${{ secrets.KALSHI_API_KEY }}
        run: |
          python prediction_market_signals.py full \
            --assets btc,eth,sol \
            --output ./alpha_engine/data
      - name: Commit signals
        run: |
          git config user.name "PM Bot"
          git config user.email "bot@example.com"
          git add alpha_engine/data/pm_signals.json
          git add alpha_engine/data/premium_signals.json
          git diff --staged --quiet || git commit -m "PM signals $(date -u +%Y-%m-%d)"
          git push
```

### 6.2 Hourly Momentum Pipeline (`.github/workflows/pm_signals_hourly.yml`)

```yaml
name: PM Signals — Hourly Momentum

on:
  schedule:
    - cron: "0 * * * *"   # Every hour
  workflow_dispatch:

jobs:
  pm-momentum:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install pandas numpy requests
      - name: Run Momentum Pipeline
        run: |
          python prediction_market_signals.py momentum \
            --assets btc,eth \
            --output ./alpha_engine/data
      - name: Commit signals
        run: |
          git config user.name "PM Bot"
          git config user.email "bot@example.com"
          git add alpha_engine/data/pm_momentum_signals.json
          git add alpha_engine/data/premium_signals.json
          git diff --staged --quiet || git commit -m "PM momentum $(date -u +%Y-%m-%d-%H:00)"
          git push
```

---

## 7. Output Format

### 7.1 Trading Signal (premium_signals.json compatible)

```json
{
  "symbol": "BTCUSDT",
  "direction": "LONG",
  "confidence": 0.72,
  "source_system": "prediction_market",
  "strategy": "pm_consensus",
  "asset_class": "CRYPTO",
  "signal_time": "2026-05-20T06:00:00Z",
  "metadata": {
    "pm_source": "polymarket",
    "signal_type": "bullish",
    "pm_consensus_score": 72,
    "momentum_component": 78.5,
    "dip_skew_component": 65.0,
    "implied_curve_component": 55.2,
    "dip_skew": 0.35,
    "momentum_4h": 0.08,
    "calibration_score": 0.91,
    "implied_premium": 0.035,
    "spot_estimate": 98500,
    "kalshi_signals_count": 12,
    "kalshi_bullish_pct": 0.67,
    "kalshi_alignment": "LONG"
  }
}
```

### 7.2 Full Pipeline Output (`pm_signals.json`)

```json
{
  "metadata": {
    "run_time": "2026-05-20T06:00:00Z",
    "assets": ["btc", "eth", "sol"],
    "num_events_fetched": 24,
    "kalshi_enabled": true
  },
  "consensus_scores": {
    "btc": {
      "asset": "btc",
      "score": 72,
      "direction": "BULLISH",
      "momentum_component": 78.5,
      "dip_skew_component": 65.0,
      "implied_curve_component": 55.2,
      "sources": ["polymarket"],
      "signal_time": "2026-05-20T06:00:00Z"
    }
  },
  "trading_signals": [...],
  "kalshi_signals": {
    "KXBTC": [...]
  },
  "accuracy_summary": {
    "total": 156,
    "correct": 118,
    "accuracy_rate": 0.7564
  },
  "calibration": {
    "brier_score": 0.1832,
    "brier_skill": 0.2672,
    "is_calibrated": true,
    "bins": [...]
  },
  "alerts": []
}
```

---

## 8. Calibration & Quality

### 8.1 Brier Score

The Brier score measures prediction accuracy:
```
Brier = mean((predicted_prob - actual_outcome)^2)
```
- 0.0 = perfect predictions
- 0.25 = random guessing (baseline)
- < 0.20 = good calibration

Brier Skill Score (vs random):
```
Skill = 1 - (Brier / 0.25)
```
- > 0 = better than random
- > 0.2 = meaningfully useful

### 8.2 Calibration Bins

Predictions are binned by probability level (0-10%, 10-20%, ..., 90-100%).
For well-calibrated markets, actual frequency ≈ predicted probability.

Example calibration table:

| Bin | Predicted Avg | Actual Freq | Count | Calibrated? |
|-----|---------------|-------------|-------|-------------|
| 0-10% | 0.05 | 0.08 | 23 | ✓ |
| 10-20% | 0.15 | 0.14 | 31 | ✓ |
| 20-30% | 0.25 | 0.28 | 19 | ✓ |
| ... | ... | ... | ... | ... |

**Alert triggered** when mean absolute calibration error > 10%.

### 8.3 Accuracy by Market Type

Tracked separately for:
- `reach` markets ("BTC above $100K")
- `dip` markets ("ETH below $2K")
- `narrative` markets ("SEC approves ETF")

This enables per-strategy weight adjustment when one market type degrades.

---

## 9. Performance Considerations

### 9.1 Caching Strategy

| Data Type | Cache TTL | Storage |
|-----------|-----------|---------|
| Price history | 15 minutes | SQLite (pm_cache.db) |
| Event metadata | 60 minutes | SQLite (pm_cache.db) |
| Kalshi markets | 30 minutes | SQLite (pm_cache.db) |
| Accuracy log | Persistent | SQLite (pm_cache.db) |

### 9.2 Rate Limiting

All API clients implement:
- Exponential backoff (base 1.5s, max 3 retries)
- 429 response handling with sleep
- Gentle inter-call delays (0.2-0.3s)
- No authentication required for Polymarket public endpoints

### 9.3 Execution Times (estimated)

| Operation | Duration | Notes |
|-----------|----------|-------|
| Fetch 100 events (Gamma) | 2-5s | Single API call |
| Price history per token | 1-3s | Cached after first fetch |
| Full pipeline (3 assets) | 30-90s | ~15-30 token fetches |
| Momentum-only (3 assets) | 15-30s | Skips implied curve calc |
| Kalshi series (9 tickers) | 10-20s | Parallel-friendly |
| Consensus scoring | < 1s | Local computation |

### 9.4 Resource Requirements

```
Python: 3.9+
Packages: pandas, numpy, requests (standard)
Disk: ~10MB for SQLite cache (grows slowly with accuracy log)
Memory: < 100MB peak
Network: ~50 API calls per full run (~500KB data)
```

### 9.5 Error Handling

All API calls are wrapped in try/except with retry logic:
- Network errors: 3 retries with exponential backoff
- Rate limits (429): 2s * backoff_factor sleep
- Empty responses: graceful fallback to empty list/None
- Missing token IDs: market skipped, logged
- Parse errors: individual market skipped, pipeline continues

---

## Appendix A: Data Classes

### PMEvent
```python
@dataclass
class PMEvent:
    event_id: str
    title: str
    slug: str
    description: Optional[str]
    markets: List[PMMarket]
    category: Optional[str]
    tags: List[str]
    volume: float
    liquidity: float
    end_date: Optional[str]
```

### PMMarket
```python
@dataclass
class PMMarket:
    market_id: str
    event_id: str
    question: str
    slug: str
    condition_id: str
    token_ids: List[str]
    yes_token_id: Optional[str]
    no_token_id: Optional[str]
    volume: float
    liquidity: float
    outcomes: List[str]
    outcome_prices: List[float]
    tags: List[str]
    end_date: Optional[str]
    active: bool
    asset: Optional[str]
    market_type: Optional[str]
    target_price: Optional[float]
```

### ConsensusScore
```python
@dataclass
class ConsensusScore:
    asset: str
    score: float           # 0-100
    direction: SignalDirection
    momentum_component: float
    dip_skew_component: float
    implied_curve_component: float
    momentum_detail: Optional[ProbabilityMomentumReading]
    dip_skew_detail: Optional[DipSkewReading]
    implied_curve_detail: Optional[ImpliedCurveReading]
    sources: List[str]
    signal_time: str
```

---

## Appendix B: Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `KALSHI_API_KEY` | No | None | Kalshi API key for higher rate limits |
| `PM_CACHE_DIR` | No | `./alpha_engine/data` | Cache directory path |
| `PM_OUTPUT_DIR` | No | `./alpha_engine/data` | Signal output directory |

---

*End of Report — Prediction Market Signal Engine v1.0*
