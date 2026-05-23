# Redis Bus Message Specifications
## findtorontoevents.ca Prediction System

**Date:** April 6, 2026  
**Bus Location:** `localhost:6379`  
**Python Helper:** `C:/Users/zerou/redis-bus/agent_bus.py`

---

## 1. Message Types Overview

| Channel | Direction | Purpose |
|---------|-----------|---------|
| `predictions:new` | Publish | New pick generated |
| `predictions:update` | Publish | Pick status change (TP/SL hit) |
| `predictions:conflict` | Publish | Direction conflict detected |
| `scores:recalc` | Request | Trigger score recalculation |
| `alerts:quality` | Publish | Data quality issues |
| `bus:broadcast:log` | Broadcast | System announcements |
| `bus:tasks:pending` | Queue | Background tasks |

---

## 2. Prediction Messages

### 2.1 New Prediction Generated

```json
{
  "type": "prediction_new",
  "timestamp": "2026-04-06T12:00:00Z",
  "agent_id": "alpha_engine",
  "pick": {
    "id": "pick_btc_20260406_001",
    "symbol": "BTCUSDT",
    "asset_class": "CRYPTO",
    "direction": "LONG",
    "entry_price": 85000.00,
    "take_profit": 93500.00,
    "stop_loss": 80750.00,
    "risk_reward": 2.0,
    "timeframe": "1h"
  },
  "scoring": {
    "quality_score": 87,
    "grade": "A-",
    "confidence": 0.82,
    "trust_score": 8.6,
    "score_components": {
      "backtest_validity": 0.92,
      "statistical_significance": 0.85,
      "risk_adjusted_return": 0.88,
      "regime_alignment": 0.75,
      "consensus_strength": 0.90,
      "market_structure": 0.80
    }
  },
  "consensus": {
    "agreeing_systems": ["alpha_engine", "mercury2", "dna_genome", "kimi"],
    "disagreeing_systems": ["battleground"],
    "consensus_count": 4,
    "total_systems": 5,
    "consensus_pct": 80.0
  },
  "strategy": {
    "dna_hash": "a1b2c3d4e5f6",
    "strategy_id": "ema_cross_btc_1h_v1",
    "genes": {
      "timeframe": "1h",
      "primary_indicator": "EMA",
      "entry_logic": "golden_cross",
      "risk_profile": "medium"
    }
  },
  "sizing": {
    "position_size_pct": 3.5,
    "kelly_fraction": 0.5,
    "max_risk_pct": 5.0,
    "expected_return_pct": 10.0
  },
  "metadata": {
    "regime": "trending_bull",
    "market_session": "us_equity_open",
    "volatility_regime": "normal"
  }
}
```

**Redis Command:**
```bash
rc PUBLISH predictions:new '{"type":"prediction_new",...}'
```

### 2.2 Prediction Outcome Update

```json
{
  "type": "prediction_outcome",
  "timestamp": "2026-04-06T15:30:00Z",
  "agent_id": "alpha_engine",
  "pick_id": "pick_btc_20260406_001",
  "symbol": "BTCUSDT",
  "outcome": {
    "status": "closed",
    "result": "win",
    "exit_price": 93500.00,
    "exit_reason": "TP_HIT",
    "exit_time": "2026-04-06T15:30:00Z",
    "pnl_pct": 10.0,
    "pnl_amount": 850.00,
    "holding_hours": 3.5
  },
  "performance": {
    "expected_r": 2.0,
    "actual_r": 2.0,
    "slippage_pct": 0.05,
    "fill_quality": "good"
  },
  "impact": {
    "strategy_win_rate": 0.65,
    "system_pnl_update": 850.00,
    "grade_trajectory": "improving"
  }
}
```

### 2.3 Direction Conflict Alert

```json
{
  "type": "conflict_detected",
  "timestamp": "2026-04-06T12:05:00Z",
  "agent_id": "cross_aggregation",
  "severity": "warning",
  "symbol": "BTCUSDT",
  "conflict": {
    "long_picks": [
      {
        "pick_id": "pick_btc_001",
        "system": "battleground",
        "score": 92,
        "entry_price": 85000
      },
      {
        "pick_id": "pick_btc_003",
        "system": "mercury2",
        "score": 88,
        "entry_price": 85100
      }
    ],
    "short_picks": [
      {
        "pick_id": "pick_btc_002",
        "system": "alpha_engine_fast",
        "score": 85,
        "entry_price": 84900
      }
    ],
    "net_exposure": "neutral",
    "conflict_score": 87.5,
    "recommendation": "review_required"
  },
  "resolution_options": [
    {
      "action": "take_higher_score",
      "winner": "LONG",
      "reason": "Higher aggregate score and consensus"
    },
    {
      "action": "net_exposure",
      "winner": "REDUCE_SIZE",
      "reason": "Conflicting signals suggest uncertainty"
    }
  ]
}
```

---

## 3. Scoring & Quality Messages

### 3.1 Score Recalculation Request

```json
{
  "type": "score_recalc_request",
  "timestamp": "2026-04-06T12:00:00Z",
  "agent_id": "quality_auditor",
  "request_id": "req_001",
  "target": {
    "scope": "symbol",
    "symbol": "BTCUSDT",
    "strategy_filter": null
  },
  "reason": "regime_change_detected",
  "priority": "high",
  "callback_channel": "scores:recalc:results"
}
```

**Redis Command:**
```bash
rc LPUSH bus:tasks:pending '{"type":"score_recalc_request",...}'
```

### 3.2 Score Update Broadcast

```json
{
  "type": "score_updated",
  "timestamp": "2026-04-06T12:01:00Z",
  "agent_id": "quality_engine",
  "pick_id": "pick_btc_20260406_001",
  "old_score": 87,
  "new_score": 92,
  "grade_change": "A- -> A",
  "reason": "improved_regime_alignment",
  "components_changed": {
    "regime_alignment": {
      "old": 0.75,
      "new": 0.90
    }
  }
}
```

### 3.3 Data Quality Alert

```json
{
  "type": "quality_alert",
  "timestamp": "2026-04-06T12:00:00Z",
  "agent_id": "data_validator",
  "severity": "critical",
  "category": "duplicate_detected",
  "details": {
    "symbol": "ETHUSDT",
    "duplicate_count": 3,
    "pick_ids": ["pick_eth_001", "pick_eth_002", "pick_eth_003"],
    "duplicate_type": "same_symbol_direction_system",
    "recommended_action": "consolidate_or_remove"
  }
}
```

---

## 4. System Status Messages

### 4.1 Agent Status Announcement

```json
{
  "type": "agent_status",
  "timestamp": "2026-04-06T12:00:00Z",
  "agent_id": "alpha_engine",
  "status": "active",
  "workload": {
    "picks_generated_today": 45,
    "active_picks": 12,
    "avg_processing_time_ms": 150
  },
  "health": {
    "last_prediction": "2026-04-06T11:58:00Z",
    "data_freshness": "current",
    "error_count_24h": 0
  },
  "capabilities": [
    "crypto_prediction",
    "forex_prediction",
    "scoring",
    "backtesting"
  ]
}
```

### 4.2 Broadcast Announcement

```json
{
  "type": "broadcast",
  "timestamp": "2026-04-06T12:00:00Z",
  "from": "system_orchestrator",
  "message": "Daily genome evolution completed. 12 new strategy variations promoted to production.",
  "priority": "info",
  "affected_systems": ["dna_genome", "alpha_engine", "mercury2"]
}
```

**Redis Command:**
```bash
rc LPUSH bus:broadcast:log '{"type":"broadcast",...}'
rc LTRIM bus:broadcast:log 0 99
```

---

## 5. Task Queue Messages

### 5.1 Background Task Submission

```json
{
  "type": "task_submit",
  "timestamp": "2026-04-06T12:00:00Z",
  "task_id": "task_001",
  "task_type": "backtest_strategy",
  "priority": 5,
  "payload": {
    "strategy_id": "new_variant_ema_rsi",
    "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
    "lookback_days": 90,
    "parameters": {
      "ema_fast": 9,
      "ema_slow": 21,
      "rsi_period": 14
    }
  },
  "submitted_by": "dna_engine",
  "estimated_duration_minutes": 30
}
```

### 5.2 Task Completion

```json
{
  "type": "task_complete",
  "timestamp": "2026-04-06T12:30:00Z",
  "task_id": "task_001",
  "status": "success",
  "results": {
    "win_rate": 0.62,
    "profit_factor": 1.8,
    "sharpe_ratio": 1.4,
    "max_drawdown": 0.12,
    "total_trades": 156
  },
  "actions": [
    {
      "type": "promote_strategy",
      "strategy_id": "new_variant_ema_rsi",
      "grade": "B+"
    }
  ]
}
```

---

## 6. Paper Trading Messages

### 6.1 Paper Trade Execution

```json
{
  "type": "paper_trade_executed",
  "timestamp": "2026-04-06T12:00:00Z",
  "agent_id": "paper_trader",
  "trade": {
    "trade_id": "paper_001",
    "pick_id": "pick_btc_20260406_001",
    "symbol": "BTCUSDT",
    "direction": "LONG",
    "entry_price": 85000.00,
    "position_size": 0.001,
    "position_value": 85.00,
    "portfolio_id": "TESTER",
    "strategy": "Antigravity Safe Protocol"
  },
  "portfolio": {
    "cash_before": 10000.00,
    "cash_after": 9915.00,
    "exposure_pct": 0.85
  }
}
```

### 6.2 Portfolio Update

```json
{
  "type": "portfolio_update",
  "timestamp": "2026-04-06T15:30:00Z",
  "agent_id": "portfolio_tracker",
  "portfolio_id": "TESTER",
  "summary": {
    "total_value": 10935.00,
    "cash": 8500.00,
    "positions_value": 2435.00,
    "total_pnl_pct": 9.35,
    "day_pnl_pct": 1.2
  },
  "positions": [
    {
      "symbol": "BTCUSDT",
      "direction": "LONG",
      "entry_price": 85000,
      "current_price": 93500,
      "pnl_pct": 10.0,
      "status": "tp_hit_pending"
    }
  ]
}
```

---

## 7. Command Reference

### 7.1 Publish Prediction
```bash
# Using redis-cli
rc PUBLISH predictions:new '<json_payload>'

# Using Python helper
$PY $BUS broadcast alpha_engine '<json_payload>'
```

### 7.2 Queue Task
```bash
# Add to task queue
rc LPUSH bus:tasks:pending '<task_json>'

# Claim task (blocking)
rc BRPOP bus:tasks:pending 5
```

### 7.3 Send Direct Message
```bash
rc LPUSH agent:<target_id>:inbox '<message_json>'
```

### 7.4 Check Recent Broadcasts
```bash
rc LRANGE bus:broadcast:log 0 9
```

### 7.5 File Lock
```bash
# Acquire lock
rc SET lock:file:audit_dashboard/template.html <agent_id> NX EX 300

# Release lock
rc DEL lock:file:audit_dashboard/template.html
```

---

## 8. Message Routing Patterns

### 8.1 Prediction Flow
```
alpha_engine → predictions:new 
             → cross_aggregator (conflict detection)
             → quality_engine (scoring validation)
             → audit_dashboard (UI update)
             → paper_trader (optional execution)
```

### 8.2 Score Update Flow
```
regime_detector → scores:recalc (request)
                → quality_engine (processing)
                → predictions:update (broadcast)
                → audit_dashboard (UI refresh)
```

### 8.3 Conflict Resolution Flow
```
cross_aggregator → predictions:conflict (alert)
                 → portfolio_manager (netting logic)
                 → affected_systems (inbox notification)
                 → audit_dashboard (warning banner)
```

---

## 9. Error Handling

### 9.1 Failed Message Format
```json
{
  "type": "error",
  "timestamp": "2026-04-06T12:00:00Z",
  "agent_id": "alpha_engine",
  "error_code": "PREDICTION_FAILED",
  "severity": "error",
  "message": "Insufficient backtest data for BTCUSDT",
  "context": {
    "symbol": "BTCUSDT",
    "strategy": "ema_cross",
    "available_trades": 12,
    "required_trades": 20
  },
  "retry_eligible": true,
  "retry_count": 0
}
```

### 9.2 Dead Letter Queue
Failed messages after max retries:
```bash
rc LPUSH bus:dead_letter:failed_predictions '<failed_message>'
```

---

**Document Version:** 1.0  
**Last Updated:** April 6, 2026  
**Bus Status:** Active (localhost:6379)
