# Live Trading Monitor — Architecture

## System Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                     Live Trading Monitor                        │
├──────────┬──────────┬──────────────┬──────────────┬─────────────┤
│  Feed    │  Lag     │  Correlation │  Signal      │  Hot        │
│  Valid.  │  Monitor │  Engine      │  Classifier  │  Router     │
│          │          │              │              │             │
│  data_   │  data_   │ correlation_ │ signal_      │ hot_signal_ │
│  lag_    │  lag_    │ engine.py    │ classifier   │ router.py   │
│  monitor │  monitor │              │ .py          │             │
│  .py     │  .py     │              │              │             │
└──────────┴──────────┴──────────────┴──────────────┴─────────────┘
       │          │           │              │              │
       ▼          ▼           ▼              ▼              ▼
  ┌────────────────────────────────────────────────────────────┐
  │                    JSON File Layer                         │
  │  alpha_signals.json · corr_matrix.json · feed_data.json   │
  │  lag_stats.json · routed_signals.json                     │
  └────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

### 1. Live Data Feed Validator (`scripts/data_lag_monitor.py`)
- **Input**: Raw feed data (JSON with timestamped entries)
- **Output**: `lag_stats.json` with staleness metrics
- **Key logic**: Computes time delta between feed timestamp and `generated_at`, flags entries > 60 minutes stale
- **CLI**: `python data_lag_monitor.py --input feeds.json --dry-run`

### 2. Correlation Engine (`scripts/correlation_engine.py`)
- **Input**: Raw price series (JSON or CSV, `--format` flag)
- **Output**: Correlation matrix JSON with Pearson coefficients
- **Key logic**: Sliding window Pearson correlation, configurable window size
- **CLI**: `python correlation_engine.py --input prices.csv --format csv --window 20`

### 3. Signal Classifier (`scripts/signal_classifier.py`)
- **Input**: `alpha_signals.json` (raw signals with confidence, direction, risk)
- **Output**: Classified signals with BUY/SELL/HOLD/AVOID actions
- **Classification rules**:
  - `confidence <= 0.3` → AVOID
  - `risk_score > 0.5` → AVOID
  - `direction=long, confidence >= 0.7, risk <= 0.5` → BUY
  - `direction=short, confidence >= 0.7, risk <= 0.5` → SELL
  - Everything else → HOLD
- **CLI**: `python signal_classifier.py --input signals.json --dry-run`

### 4. Hot Signal Router (`scripts/hot_signal_router.py`)
- **Input**: Classified signals
- **Output**: Routed signals with urgency and execution tiers
- **Priority mapping**: BUY=high, SELL=high, HOLD=medium, AVOID=low
- **Tier mapping**: confidence≥0.85→tier_1, ≥0.7→tier_2, ≥0.5→tier_3, else→tier_4

### 5. Correlation Schema (`schemas/correlation_schema.json`)
- JSON Schema Draft-07 for correlation matrix output
- Validates: asset names, coefficient range [-1,1], matrix dimensions

### 6. Alpha Signals Schema (`schemas/alpha_signals_schema.json`)
- Validates input signals: required fields, direction enum, confidence/risk range [0,1]

## Data Flow

```
Feed Data → data_lag_monitor → lag_stats.json
                                      │
                                      ▼
                              ┌─── Alert if ───┐
                              │  max_lag > 60m  │
                              └─────────────────┘

Price Data → correlation_engine → corr_matrix.json
                                       │
                                       ▼
                               correlation_schema.json (validation)

alpha_signals.json → signal_classifier → classified signals
                                              │
                                              ▼
                                       hot_signal_router → routed signals
```

## JSON File Contracts

### alpha_signals.json (input)
```json
{
  "generated_at": "ISO-8601",
  "strategy": "string",
  "signals": [
    {
      "asset": "BTC",
      "direction": "long|short|neutral",
      "confidence": 0.85,
      "risk_score": 0.3,
      "volatility": 0.4,
      "timeframe": "1h|4h|1d|1w",
      "created_at": "ISO-8601"
    }
  ]
}
```

### corr_matrix.json (output)
```json
{
  "assets": ["BTC", "ETH", ...],
  "matrix": [[1.0, 0.75, ...], ...],
  "window": 20,
  "generated_at": "ISO-8601"
}
```

### lag_stats.json (output)
```json
{
  "generated_at": "ISO-8601",
  "max_lag_minutes": 45.2,
  "avg_lag_minutes": 12.5,
  "stale_count": 3,
  "flagged": [
    {"symbol": "DOGE", "lag_minutes": 90.0, "timestamp": "ISO-8601"}
  ]
}
```

## Design Decisions

1. **Zero external dependencies**: Only `json`, `csv`, `math`, `datetime`, `shutil`, `argparse`, `sys`, `os`
2. **JSON-first**: All inter-component communication via JSON files
3. **Dry-run everywhere**: Every script supports `--dry-run` for safe testing
4. **Backup on write**: In-place modifications always create `.bak.YYYYMMDD_HHMMSS` backups
5. **No network calls**: Purely local computation, no HTTP/WS dependencies
6. **Graceful degradation**: Missing fields get sensible defaults, scripts don't crash

## Future Work

- WebSocket feed ingestion (replace JSON polling)
- Real-time correlation streaming
- ML-based signal confidence adjustment
- Portfolio-level risk budgeting integration
