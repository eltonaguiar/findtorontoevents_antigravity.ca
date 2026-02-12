# Hardened Sports Scrapers - Multi-Source Validation Guide

## Philosophy

**NEVER TRUST A SINGLE SOURCE.**

All data is cross-validated against multiple independent sources before being accepted. Each field receives a confidence score based on source agreement.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DATA VALIDATION LAYER                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   Source 1    Source 2    Source 3    Source N              │
│      │           │           │           │                  │
│      └───────────┴───────────┴───────────┘                  │
│                  │                                          │
│          ┌───────▼────────┐                                 │
│          │ CROSS-CHECK    │                                 │
│          │ - Match fields │                                 │
│          │ - Calculate CV │                                 │
│          │ - Weight by    │                                 │
│          │   reliability  │                                 │
│          └───────┬────────┘                                 │
│                  │                                          │
│          ┌───────▼────────┐                                 │
│          │ CONFIDENCE     │                                 │
│          │ SCORING        │                                 │
│          │                │                                 │
│          │ >90% = Accept  │                                 │
│          │ 70-90% = Flag  │                                 │
│          │ <70% = Reject  │                                 │
│          └───────┬────────┘                                 │
│                  │                                          │
│          ┌───────▼────────┐                                 │
│          │ CONSENSUS      │                                 │
│          │ OUTPUT         │                                 │
│          └────────────────┘                                 │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Data Sources by Sport

### NFL

| Source | Type | Reliability | Rate Limit |
|--------|------|-------------|------------|
| ESPN API | Official | 95% | 100 req/min |
| Pro-Football-Reference | Historical | 92% | Be nice |
| ESPN HTML | Scrape | 90% | 60 req/min |
| Yahoo Sports | Scrape | 85% | 30 req/min |
| CBS Sports | Scrape | 83% | 30 req/min |

### NBA

| Source | Type | Reliability | Notes |
|--------|------|-------------|-------|
| ESPN API | Official | 95% | Primary source |
| NBA.com | Official | 93% | Official stats |
| Basketball-Reference | Historical | 90% | Comprehensive |

### NHL

| Source | Type | Reliability | Notes |
|--------|------|-------------|-------|
| ESPN API | Official | 93% | Primary |
| NHL.com | Official | 94% | Box scores |
| Hockey-Reference | Historical | 89% | Advanced stats |

### MLB

| Source | Type | Reliability | Notes |
|--------|------|-------------|-------|
| ESPN API | Official | 94% | Game data |
| MLB.com | Official | 95% | Pitcher data |
| Baseball-Reference | Historical | 92% | Park factors |

---

## Validation Rules

### Confidence Calculation

```
Confidence = Σ(field_confidence × field_weight) / Σ(field_weights)
```

### Field Weights (NFL Example)

| Field | Weight | Critical? |
|-------|--------|-----------|
| game_date | 3.0 | YES |
| home_team | 2.5 | YES |
| away_team | 2.5 | YES |
| home_score | 2.0 | YES |
| away_score | 2.0 | YES |
| spread | 1.0 | No |
| total | 1.0 | No |

### Numeric Field Validation

Uses Coefficient of Variation (CV = std_dev / mean):

| CV Range | Discrepancy Level | Confidence |
|----------|-------------------|------------|
| < 1% | None | 95% |
| 1-5% | Minor | 85% |
| 5-15% | Moderate | 70% |
| > 15% | Critical | 50% |

### String Field Validation

Weighted voting by source reliability:

```php
consensus = argmax Σ(votes[source] × reliability[source])
```

---

## Anomaly Detection

### Automatic Red Flags

| Anomaly | Threshold | Action |
|---------|-----------|--------|
| Extreme total score | > 1.5× historical max | Flag for review |
| Blowout margin | > 1.5× historical max | Flag for review |
| Impossible stats | Pass yards > 600 | Reject |
| Negative time | TOP < 0 | Reject |
| Score mismatch | Sum of quarters ≠ final | Reject |

### Historical Baselines

```php
$nfl_baselines = array(
    'max_total' => 75,
    'avg_total' => 45,
    'max_spread' => 35
);
```

---

## API Reference

### Data Validator

```
POST /data_validator.php?action=validate
Body: {
    "game_id": "401547123",
    "sport": "nfl",
    "data": {
        "espn_api": { ... },
        "pfr": { ... },
        "yahoo": { ... }
    }
}

Response: {
    "ok": true,
    "validation": {
        "overall_confidence": 0.94,
        "fields_validated": {
            "home_score": {
                "confidence": 0.98,
                "discrepancy": "none",
                "consensus": 24
            }
        },
        "critical_errors": [],
        "warnings": []
    }
}
```

### NFL Hardened Scraper

```
GET /nfl_hardened.php?action=schedule&year=2024&week=1

Response: {
    "ok": true,
    "year": 2024,
    "week": 1,
    "sources_used": ["espn_api", "pro_football_reference"],
    "games_count": 16,
    "games": [
        {
            "game_id": "401547123",
            "game_key": "2024_WK1_det_at_kc",
            "confidence": 0.96,
            "data": {
                "home_team": "Kansas City Chiefs",
                "away_team": "Detroit Lions",
                "home_score": 21,
                "away_score": 20
            },
            "sources": ["espn_api", "pfr"]
        }
    ],
    "validation_summary": {
        "total_validated": 16,
        "high_confidence_count": 15,
        "average_confidence": 0.94
    }
}
```

### Player Stats Validation

```
GET /data_validator.php?action=player_stats&player=Patrick+Mahomes&date=2024-01-15

Response: {
    "ok": true,
    "player": "Patrick Mahomes",
    "date": "2024-01-15",
    "confidence": 0.91,
    "stats": {
        "passing_yards": {
            "confidence": 0.95,
            "consensus": 328,
            "std_deviation": 2.1
        }
    }
}
```

### Anomaly Detection

```
POST /data_validator.php?action=anomalies
Body: [games array]

Response: {
    "ok": true,
    "anomalies": {
        "game_123": [
            "Unusually high total score: 89",
            "Suspicious passing yards: 612"
        ]
    }
}
```

### Validation Report

```
GET /data_validator.php?action=report&sport=nfl&start=2024-01-01&end=2024-01-31

Response: {
    "ok": true,
    "report": {
        "sport": "nfl",
        "date_range": "2024-01-01 to 2024-01-31",
        "total_validations": 267,
        "average_confidence": 0.932,
        "high_confidence_rate": 0.89,
        "low_confidence_count": 12,
        "games_with_critical_errors": 3
    }
}
```

---

## Integration Example

```php
<?php
// Using the hardened scraper in your application

require_once 'data_validator.php';
require_once 'nfl_hardened.php';

$scraper = new NFLHardenedScraper($conn);

// Get schedule with full validation
$schedule = $scraper->get_hardened_schedule(2024, 1);

if ($schedule['ok']) {
    foreach ($schedule['games'] as $game) {
        if ($game['confidence'] >= 0.9) {
            // High confidence - safe to use
            store_game_data($game['data']);
        } elseif ($game['confidence'] >= 0.7) {
            // Moderate confidence - flag for review
            store_game_data($game['data'], 'NEEDS_REVIEW');
        } else {
            // Low confidence - reject or manual entry
            log_error("Low confidence game: {$game['game_id']}");
        }
    }
}
?>
```

---

## Deployment

```bash
# Deploy hardened scrapers
cd /path/to/project
python deploy_scrapers.py

# The hardened modules will be included automatically
```

---

## Monitoring

### Validation Health Dashboard

Check validation statistics:

```
GET /data_validator.php?action=report&sport=nfl&start=2024-01-01&end=2024-01-31
```

### Key Metrics

| Metric | Target | Alert If |
|--------|--------|----------|
| Avg Confidence | > 90% | < 85% |
| High Confidence Rate | > 85% | < 80% |
| Critical Errors | < 1% | > 2% |
| Sources Available | ≥ 2 | < 2 |

---

## Troubleshooting

### Low Confidence Issues

1. **Check source availability**
   ```
   GET /nfl_hardened.php?action=schedule&year=2024&week=1
   Check "sources_used" in response
   ```

2. **Review validation details**
   ```
   Check "validation" object for field-level details
   ```

3. **Common causes:**
   - Source API rate limited
   - HTML structure changed (scrapers)
   - Game postponed/cancelled
   - Data entry timing differences

### Handling Source Failures

The system automatically:
- Falls back to secondary sources
- Increases confidence threshold requirements
- Logs all failures for review
- Never presents unvalidated data as fact

---

## Best Practices

1. **Always check confidence scores** before using data
2. **Flag low-confidence data** for manual review
3. **Monitor validation reports** regularly
4. **Update source reliability scores** based on accuracy tracking
5. **Never use data with < 70% confidence** for automated decisions
6. **Log all critical errors** for investigation
7. **Cross-validate player props** across multiple books

---

## File Structure

```
live-monitor/api/scrapers/
├── data_validator.php       # Core validation engine
├── nfl_hardened.php         # Hardened NFL scraper
├── nba_hardened.php         # Hardened NBA scraper (TODO)
├── nhl_hardened.php         # Hardened NHL scraper (TODO)
├── mlb_hardened.php         # Hardened MLB scraper (TODO)
└── HARDENED_SCRAPERS_GUIDE.md  # This file
```

---

## Future Enhancements

- [ ] Machine learning for anomaly detection
- [ ] Automatic source reliability updates
- [ ] Real-time validation alerts
- [ ] Historical accuracy tracking per source
- [ ] Consensus algorithm improvements
- [ ] Additional sports (CFL, NCAAF, NCAAB)
