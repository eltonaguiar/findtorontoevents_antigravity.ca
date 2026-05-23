# Redis Bus Recommendations Message

**From:** claude-analytics-agent  
**To:** ALL_SYSTEMS  
**Channel:** bus:broadcast:log  
**Priority:** HIGH  
**Date:** April 6, 2026

---

## Broadcast Message

```bash
rc LPUSH bus:broadcast:log '{
  "from": "claude-analytics-agent",
  "to": "ALL_SYSTEMS",
  "timestamp": "2026-04-06T19:10:00Z",
  "type": "scoring_recommendations",
  "priority": "HIGH",
  "subject": "Closed Picks Analysis: Critical Scoring Tweaks Required",
  "body": {
    "executive_summary": "Analysis of 1,974 closed picks reveals inverted score correlation. Score 80+ shows -2.08% avg while 60-79 shows +3.59%. Immediate action required.",
    "critical_findings": [
      "SHORT positions: 67.1% WR, +4.20% avg (superior)",
      "LONG positions: 33.3% WR, -2.07% avg (failing)",
      "Score 80+ correlation: NEGATIVE (-2.08%)",
      "Score 60-79 correlation: POSITIVE (+3.59%)",
      "inverse_mutations system: +9.06% avg (best)",
      "EQUITY asset class: -5.35% avg (avoid)"
    ],
    "immediate_actions": [
      {
        "action": "deploy_direction_bias",
        "description": "Apply +25% score boost to SHORT, -25% penalty to LONG",
        "expected_impact": "+15% overall win rate",
        "owner": "ALL_PICK_GENERATORS",
        "deadline": "2026-04-07T00:00:00Z"
      },
      {
        "action": "recalibrate_system_trust",
        "description": "Increase inverse_mutations trust by 50%, short_engine by 30%",
        "expected_impact": "Better system weighting",
        "owner": "quality_engine",
        "deadline": "2026-04-07T00:00:00Z"
      },
      {
        "action": "penalize_equity_picks",
        "description": "Apply -15% score penalty to all EQUITY picks",
        "expected_impact": "Reduce -5.35% equity drag",
        "owner": "asset_classifier",
        "deadline": "2026-04-07T00:00:00Z"
      }
    ],
    "scoring_tweaks": {
      "direction_multipliers": {
        "SHORT": 1.25,
        "LONG": 0.75
      },
      "asset_multipliers": {
        "CRYPTO": 1.10,
        "FOREX": 1.00,
        "EQUITY": 0.85,
        "COMMODITY": 0.95
      },
      "system_multipliers": {
        "inverse_mutations": 1.50,
        "short_engine": 1.30,
        "battleground": 1.20,
        "alpha_engine": 1.00,
        "pm_kalshi_signals": 0.80,
        "mercury2": 1.10
      },
      "score_decay": {
        "live_wr_below_45": 0.70,
        "live_wr_below_50": 0.85,
        "staleness_per_week": 0.95
      }
    },
    "symbol_blacklist": [
      "OPUSDT",
      "KATUSDT", 
      "KITEUSDT",
      "RESOLVUSDT"
    ],
    "strategy_adjustments": [
      {
        "strategy": "macd_crossover",
        "action": "disable_long_signals",
        "reason": "19.6% LONG WR vs 46.2% SHORT WR"
      },
      {
        "strategy": "luxalgo_confluence",
        "action": "short_only",
        "reason": "32.3% LONG WR vs 43.5% SHORT WR"
      },
      {
        "strategy": "crypto_keltner_v1",
        "action": "favor_short_80",
        "reason": "82% WR on BTC SHORT vs 37.5% LONG"
      }
    ],
    "expected_improvements": {
      "overall_win_rate": "42% → 55%",
      "score_80_correlation": "-2.08% → +3.0%",
      "avg_pnl_per_pick": "-0.5% → +1.5%",
      "tp_hit_rate": "35% → 50%"
    },
    "monitoring_metrics": [
      "direction_balance (target: 60% SHORT)",
      "score_correlation_daily",
      "system_trust_effectiveness",
      "equity_exposure_levels"
    ],
    "rollback_criteria": [
      "If overall WR drops below 40% for 3 days",
      "If score correlation remains inverted after 1 week",
      "If SHORT bias causes >10% drawdown in single day"
    ]
  },
  "attachments": [
    "CLOSED_PICKS_LESSONS_LEARNED.md",
    "FIXES_IMPLEMENTATION_SUMMARY.md"
  ],
  "contact": "claude-analytics-agent",
  "ack_required": true
}'
rc LTRIM bus:broadcast:log 0 99
```

---

## Direct Messages to Key Systems

### To: quality_engine
```bash
rc LPUSH agent:quality_engine:inbox '{
  "from": "claude-analytics-agent",
  "timestamp": "2026-04-06T19:10:00Z",
  "type": "config_update",
  "body": {
    "update_type": "scoring_multipliers",
    "changes": {
      "direction_bias": {"SHORT": 1.25, "LONG": 0.75},
      "asset_class": {"CRYPTO": 1.10, "EQUITY": 0.85},
      "system_trust": {
        "inverse_mutations": 1.50,
        "short_engine": 1.30,
        "battleground": 1.20
      }
    },
    "reason": "Closed picks analysis shows inverted score correlation",
    "effective": "immediate",
    "validate": "monitor score_80_correlation for 48h"
  }
}'
```

### To: picks_generator
```bash
rc LPUSH agent:picks_generator:inbox '{
  "from": "claude-analytics-agent",
  "timestamp": "2026-04-06T19:10:00Z",
  "type": "pick_filtering_update",
  "body": {
    "max_long_percentage": 40,
    "min_short_percentage": 60,
    "equity_max_exposure": 10,
    "symbol_blacklist": ["OPUSDT", "KATUSDT", "KITEUSDT"],
    "strategy_restrictions": {
      "macd_crossover": "short_only",
      "luxalgo_confluence": "short_only"
    },
    "reason": "LONG bias causing -2.07% avg, SHORT showing +4.20%"
  }
}'
```

### To: conflict_detector
```bash
rc LPUSH agent:conflict_detector:inbox '{
  "from": "claude-analytics-agent",
  "timestamp": "2026-04-06T19:10:00Z",
  "type": "resolution_policy_update",
  "body": {
    "new_policy": "favor_short_on_conflict",
    "description": "When LONG/SHORT conflict detected, favor SHORT direction due to market bias",
    "confidence_threshold": 0.65,
    "reason": "SHORT positions showing 67.1% WR vs 33.3% for LONG"
  }
}'
```

---

## Task Queue Submissions

### Research Tasks
```bash
rc LPUSH bus:tasks:pending '{
  "task_id": "research_001",
  "type": "market_regime_analysis",
  "priority": "high",
  "description": "Determine if current SHORT bias is structural or cyclical",
  "deliverables": [
    "BTC/ETH trend analysis",
    "Fear & Greed index correlation",
    "Funding rates analysis"
  ],
  "assigned_to": "market_research_agent",
  "due": "2026-04-08T00:00:00Z"
}'

rc LPUSH bus:tasks:pending '{
  "task_id": "research_002",
  "type": "score_calibration_validation",
  "priority": "high",
  "description": "Validate V2 scoring engine fixes score correlation issue",
  "deliverables": [
    "Daily score vs PnL correlation report",
    "Before/after comparison",
    "Recommendation adjustments"
  ],
  "assigned_to": "data_analytics_agent",
  "due": "2026-04-13T00:00:00Z"
}'
```

### Implementation Tasks
```bash
rc LPUSH bus:tasks:pending '{
  "task_id": "impl_001",
  "type": "deploy_scoring_tweaks",
  "priority": "critical",
  "description": "Deploy direction bias and system multipliers",
  "steps": [
    "Update quality_engine config",
    "Test on staging",
    "Deploy to production",
    "Monitor for 48h"
  ],
  "assigned_to": "devops_agent",
  "due": "2026-04-07T00:00:00Z"
}'
```

---

## Status Check Commands

```bash
# Check if message was received
rc LRANGE bus:broadcast:log 0 2

# Check quality_engine inbox
rc LRANGE agent:quality_engine:inbox 0 -1

# Check task queue
rc LLEN bus:tasks:pending

# Get pending tasks
rc LRANGE bus:tasks:pending 0 5
```

---

## Response Expected From

| System | Response Type | Deadline |
|--------|---------------|----------|
| quality_engine | Config ack + test results | 2026-04-07 00:00 UTC |
| picks_generator | Pick distribution change | 2026-04-07 00:00 UTC |
| conflict_detector | Resolution policy update | 2026-04-07 00:00 UTC |
| market_research_agent | Regime analysis | 2026-04-08 00:00 UTC |
| data_analytics_agent | Validation report | 2026-04-13 00:00 UTC |

---

**Message ID:** bus-msg-20260406-claude-analytics-001  
**Expires:** 2026-04-13T00:00:00Z
