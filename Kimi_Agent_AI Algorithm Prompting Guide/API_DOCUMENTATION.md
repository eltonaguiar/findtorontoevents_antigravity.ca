# On-Chain Data Integration API Documentation

## Overview

This module provides on-chain data integration for crypto trading systems, acting as a **confidence multiplier** for existing signals rather than a primary signal source.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    SIGNAL ENHANCEMENT FLOW                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐      ┌──────────────────┐                     │
│  │   Existing   │      │   On-Chain Data  │                     │
│  │   Signal     │      │   Provider       │                     │
│  │  (62.4% WR)  │      │                  │                     │
│  └──────┬───────┘      └────────┬─────────┘                     │
│         │                       │                                │
│         │  Base Confidence      │ Whale + Exchange Flows         │
│         │       (0.65)          │       (0-1 score)              │
│         │                       │                                │
│         └───────────┬───────────┘                                │
│                     ▼                                            │
│         ┌──────────────────┐                                    │
│         │ Signal Enhancer  │  Combined = 70% Tech + 30% OnChain │
│         │                  │                                    │
│         │ Final Confidence │  → Position Size → Execute?        │
│         │    (0-1)         │                                    │
│         └──────────────────┘                                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## API Endpoints

### Whale Alert API

**Base URL:** `https://api.whale-alert.io/v1`

#### Get Transactions
```
GET /transactions
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| api_key | string | Yes | Your API key |
| start | int | Yes | Unix timestamp start |
| end | int | No | Unix timestamp end |
| cursor | string | No | Pagination cursor |
| min_value | int | No | Minimum USD value |
| currency | string | No | Filter by symbol |
| blockchain | string | No | Filter by chain |

**Free Tier Limits:**
- 10 calls per minute
- Historical data: 1 hour delay

**Example Response:**
```json
{
  "result": "success",
  "cursor": "2bc7c066-3e3c-4b5e-9424-1234567890",
  "count": 100,
  "transactions": [
    {
      "blockchain": "bitcoin",
      "symbol": "BTC",
      "id": "1234567890abcdef",
      "transaction_type": "transfer",
      "hash": "abc123...",
      "from": {
        "address": "1A1zP1...",
        "owner": "unknown",
        "owner_type": "unknown"
      },
      "to": {
        "address": "3FupZp...",
        "owner": "Binance",
        "owner_type": "exchange"
      },
      "timestamp": 1640995200,
      "amount": 500,
      "amount_usd": 25000000,
      "transaction_count": 1
    }
  ]
}
```

### Glassnode API

**Base URL:** `https://api.glassnode.com/v1`

#### Exchange Netflows
```
GET /metrics/distribution/exchange_netflow
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| a | string | Yes | Asset symbol (BTC, ETH) |
| api_key | string | Yes | Your API key |
| i | string | No | Interval (1h, 24h, 1w) |
| s | int | No | Start timestamp |
| u | int | No | End timestamp |

**Free Tier Limits:**
- 30 calls per minute
- Limited endpoints available

**Example Response:**
```json
[
  {"t": 1640995200, "v": 1250.5},
  {"t": 1640998800, "v": -890.2}
]
```

### Dune Analytics API

**Base URL:** `https://api.dune.com/api/v1`

#### Execute Query
```
POST /query/{query_id}/execute
```

**Free Tier Limits:**
- 2500 calls per month
- 5 requests per second

## Classes and Methods

### OnChainDataProvider

Main class for fetching and analyzing on-chain data.

#### Constructor
```python
provider = OnChainDataProvider(
    whale_alert_api_key: Optional[str] = None,
    glassnode_api_key: Optional[str] = None,
    dune_api_key: Optional[str] = None,
    cache_ttl: int = 300,
    whale_alert_rate_limit: int = 10,
)
```

#### Methods

##### `get_whale_flows()`
Fetch whale transactions with false positive filtering.

```python
transactions = provider.get_whale_flows(
    symbol: str,                    # "BTC", "ETH", etc.
    min_value_usd: float = 10_000_000,
    hours_back: int = 24,
    blockchain: Optional[str] = None
) -> List[WhaleTransaction]
```

**Returns:** List of `WhaleTransaction` objects with classified flow types.

##### `get_exchange_flows()`
Fetch exchange inflow/outflow data.

```python
flows = provider.get_exchange_flows(
    symbol: str,
    hours_back: int = 24,
    exchange: Optional[str] = None
) -> List[ExchangeFlow]
```

##### `calculate_confidence_boost()`
Main method for signal enhancement.

```python
signal = provider.calculate_confidence_boost(
    symbol: str,
    signal_direction: str,  # "long" or "short"
    lookback_hours: int = 24,
    base_confidence: float = 0.5
) -> OnChainSignal
```

**Returns:** `OnChainSignal` with:
- `combined_score`: Final confidence (0-1)
- `whale_score`: Whale-based confidence
- `exchange_score`: Exchange flow confidence
- `supporting_evidence`: List of evidence strings
- `warnings`: List of warning strings

### SignalEnhancer

Integration class for combining on-chain data with existing signals.

#### Methods

##### `enhance_signal()`
```python
enhanced = enhancer.enhance_signal(
    symbol: str,
    base_signal: str,        # "buy" or "sell"
    base_confidence: float,   # Your technical confidence
    strategy_wr: float = 0.624
) -> Dict
```

**Returns:** Dictionary with:
- `combined_confidence`: Weighted confidence score
- `position_size_pct`: Recommended position size
- `expected_value`: Expected value in R multiples
- `execute`: Boolean - should you take the trade?

## Confidence Score Calculation

### Formula

```
Combined Confidence = (Base Confidence × 0.7) + (On-Chain Score × 0.3)

Where:
  On-Chain Score = (Whale Score × 0.4) + (Exchange Score × 0.6)
```

### Whale Score Calculation

```python
def calculate_whale_score(transactions, signal_direction):
    # Categorize flows
    outflows = [tx for tx in transactions if tx.type == "exchange_outflow"]
    inflows = [tx for tx in transactions if tx.type == "exchange_inflow"]

    # Volume-weighted scoring
    outflow_volume = sum(tx.amount_usd for tx in outflows)
    inflow_volume = sum(tx.amount_usd for tx in inflows)
    total = outflow_volume + inflow_volume

    if signal_direction == "long":
        # Outflows = bullish
        score = 0.5 + ((outflow_volume - inflow_volume) / total) * 0.5
    else:
        # Inflows = bearish
        score = 0.5 + ((inflow_volume - outflow_volume) / total) * 0.5

    return clamp(score, 0, 1)
```

### Exchange Score Calculation

```python
def calculate_exchange_score(flows, signal_direction):
    total_netflow = sum(f.netflow for f in flows)
    total_volume = sum(abs(f.inflow) + abs(f.outflow) for f in flows)

    netflow_ratio = total_netflow / total_volume

    if signal_direction == "long":
        score = 0.5 + netflow_ratio * 0.5  # Positive = bullish
    else:
        score = 0.5 - netflow_ratio * 0.5  # Negative = bearish

    return clamp(score, 0, 1)
```

## False Positive Filtering

### Filtered Transaction Types

| Type | Filtered? | Reason |
|------|-----------|--------|
| Staking deposits | ✅ Yes | Not sell pressure |
| Staking withdrawals | ✅ Yes | Not accumulation |
| OTC trades | ✅ Yes | Off-exchange, neutral |
| Custody transfers | ✅ Yes | Internal movements |
| Exchange→Exchange | ✅ Yes | Arbitrage, neutral |
| Exchange outflows | ❌ No | Accumulation signal |
| Exchange inflows | ❌ No | Distribution signal |

### Staking Detection

```python
KNOWN_STAKING = {
    "lido": ["0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84"],
    "rocketpool": ["0x1CC9cF5596522c6F997E1122b123B36E3b706791"],
}

STAKING_KEYWORDS = ["stake", "staking", "lido", "rocketpool", "validator"]
```

## Position Sizing

### Confidence Thresholds

| Confidence | Position Size | Action |
|------------|---------------|--------|
| < 0.40 | 0% | Skip trade |
| 0.40-0.50 | 50% | Reduced size |
| 0.50-0.65 | 75% | Moderate size |
| 0.65-0.80 | 100% | Full size |
| > 0.80 | 125% | Overweight |

### Example Calculation

```python
# Your existing signal
base_confidence = 0.65  # Keltner/RSI confluence

# On-chain boost
onchain_score = 0.78    # Strong exchange outflows

# Combined
combined = (0.65 * 0.7) + (0.78 * 0.3) = 0.689

# Position size
if combined >= 0.65:
    position_size = 1.0  # 100%
```

## Rate Limiting & Caching

### Default Limits

| API | Calls/Min | Cache TTL |
|-----|-----------|-----------|
| Whale Alert | 10 | 60 seconds |
| Glassnode | 30 | 300 seconds |

### Cache Strategy

```python
# Whale data: 1 minute (frequent updates)
# Exchange flows: 5 minutes (slower changes)
# Confidence scores: 2 minutes (balanced)
```

## Integration Example

```python
from onchain_data_module import OnChainDataProvider, SignalEnhancer

# Initialize
provider = OnChainDataProvider(
    whale_alert_api_key="YOUR_KEY",
    glassnode_api_key="YOUR_KEY",
)

enhancer = SignalEnhancer(provider)

# Your existing signal
my_signal = {
    "symbol": "BTC",
    "direction": "long",
    "confidence": 0.65,
}

# Enhance
result = enhancer.enhance_signal(
    symbol=my_signal["symbol"],
    base_signal=my_signal["direction"],
    base_confidence=my_signal["confidence"],
)

# Use result
if result["execute"]:
    size = result["position_size_pct"]
    confidence = result["combined_confidence"]
    print(f"Execute with {size:.0%} size, {confidence:.1%} confidence")
```

## Error Handling

```python
try:
    signal = provider.calculate_confidence_boost("BTC", "long")
except RateLimitError:
    # Fall back to cached data
    signal = provider.get_cached_signal("BTC")
except APIError as e:
    logger.error(f"API error: {e}")
    # Use neutral confidence
    signal = OnChainSignal.neutral("BTC")
```

## Monitoring & Alerts

```python
# Check API usage
stats = provider.get_api_usage_stats()
print(f"Whale Alert calls today: {stats['calls_today']['whale_alert']}")

# Set up alerts
if stats['calls_today']['whale_alert'] > 500:
    send_alert("Approaching API limit!")
```
