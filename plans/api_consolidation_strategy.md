# API Consolidation Strategy
## Unified Predictions Dashboard

**Goal:** Reduce 35+ APIs to 8 core endpoints while preserving functionality

---

## Current API Landscape Analysis

### Stocks APIs (15 endpoints)

**High-Performance (Keep & Enhance):**
- `/findstocks/api/cursor_genius.php` - **PRIORITY** (+1,324% return)
- `/findstocks/api/sector_rotation.php` - **PRIORITY** (+354% return)  
- `/findstocks/api/alpha_engine.php` - Core factor analysis

**Redundant (Consolidate):**
- `/findstocks/api/alpha_picks.php` → Merge into unified picks
- `/findstocks/api/quick_picks.php` → Merge into unified picks
- `/findstocks/api/blue_chip_picks.php` → Merge into unified picks
- `/findstocks/portfolio2/api/consolidated_picks.php` → Replace with unified

**Low Priority (Deprecate):**
- `/findstocks/api/etf_portfolio.php` (3.37% WR, failing)
- `/findstocks/api/sector_momentum.php` (0% WR, failing)

### Crypto APIs (8 endpoints)

**Current Status:** 0% WR, -2.25% avg (Failing)
- `/findcryptopairs/api/crypto_winners.php` → Keep but improve
- `/findcryptopairs/api/meme_scanner.php` → Keep but improve

### Sports Betting APIs (3 endpoints)

**High-Performance (Keep & Feature):**
- `/live-monitor/sports-betting.php` - **PRIORITY** (+25.3% ROI)

### Forex APIs (5 endpoints)

**Status:** Poor performance, low priority
- `/findforex2/api/*` → Consolidate into unified API

### Mutual Funds APIs (4 endpoints)

**Status:** Basic functionality, low priority
- `/findmutualfunds/api/*` → Consolidate into unified API

---

## Unified API Architecture

### Core Endpoints (8 Total)

```
/api/predictions/
├── v1/
│   ├── leaderboard/          # Performance metrics
│   ├── picks/               # Current recommendations
│   ├── regime/              # Market intelligence
│   ├── execution/           # Trade quality
│   ├── analytics/           # Performance attribution
│   ├── sports/              # Sports betting
│   ├── crypto/              # Crypto-specific
│   └── stocks/              # Stocks-specific
```

### Endpoint Specifications

#### 1. `/api/predictions/v1/leaderboard`

**Purpose:** Unified performance dashboard
**Sources:** cursor_genius, sector_rotation, sports_betting

```json
{
  "high_performers": [
    {
      "name": "Cursor Genius",
      "return": 1324.31,
      "win_rate": 65.3,
      "picks": 308,
      "status": "active"
    },
    {
      "name": "Sector Rotation", 
      "return": 354.24,
      "win_rate": 64.0,
      "picks": 275,
      "status": "active"
    }
  ],
  "market_regime": {
    "hmm_state": "sideways",
    "confidence": 99.94,
    "hurst": 0.560,
    "vix": 18.12
  }
}
```

#### 2. `/api/predictions/v1/picks`

**Purpose:** Unified recommendations across asset classes
**Parameters:** `?asset_class=all|stocks|crypto|forex|sports`

```json
{
  "high_confidence": [
    {
      "symbol": "AMZN",
      "asset_class": "stocks",
      "strategy": "Mean Reversion Sniper",
      "score": 63,
      "kelly_size": 0.15,
      "timeframe": "1-3 days"
    }
  ],
  "regime_aware": [
    {
      "symbol": "BTC/USDT",
      "asset_class": "crypto", 
      "strategy": "Momentum Continuation",
      "score": 52,
      "regime_filter": "trending",
      "kelly_size": 0.08
    }
  ]
}
```

#### 3. `/api/predictions/v1/regime`

**Purpose:** Market regime intelligence
**Sources:** HMM, Hurst, VIX analysis

```json
{
  "current": {
    "hmm": {
      "state": "sideways",
      "confidence": 99.94,
      "duration_days": 14
    },
    "hurst": {
      "exponent": 0.560,
      "regime": "trending",
      "confidence": 0.85
    },
    "vix": {
      "value": 18.12,
      "status": "normal",
      "percentile": 45.2
    }
  },
  "recommended_strategies": ["mean_reversion", "sector_rotation"]
}
```

#### 4. `/api/predictions/v1/execution`

**Purpose:** Address the execution quality gap

```json
{
  "signal_quality": 70.5,
  "execution_quality": 3.84,
  "gap_percentage": 66.66,
  "commission_drag": 8340,
  "win_loss_ratio": 0.06,
  "timeout_rate": 67.0,
  "improvements": [
    {
      "area": "commission_drag",
      "action": "negotiate_broker_fees",
      "potential_improvement": "83.4%"
    }
  ]
}
```

---

## Migration Strategy

### Phase 1: Create Unified Endpoints (Week 1)

**Create these files:**
- `/api/predictions/v1/leaderboard.php`
- `/api/predictions/v1/picks.php`
- `/api/predictions/v1/regime.php`
- `/api/predictions/v1/execution.php`

**Update navigation to use new endpoints:**
- Update dashboard to fetch from `/api/predictions/v1/leaderboard`
- Update picks display to use `/api/predictions/v1/picks`

### Phase 2: Redirect Legacy APIs (Week 2)

**Add redirects to legacy endpoints:**
```php
// /findstocks/api/alpha_picks.php
header('Content-Type: application/json');
echo json_encode([
  "message": "This endpoint is deprecated. Use /api/predictions/v1/picks",
  "redirect": "/api/predictions/v1/picks",
  "data": get_legacy_data() // Temporary backward compatibility
]);
```

### Phase 3: Deprecation Warnings (Week 3)

**Add warnings to legacy endpoints:**
```php
// Add to all legacy endpoints
$deprecation_warning = [
  "deprecated": true,
  "message": "Endpoint deprecated on 2026-03-01",
  "alternative": "/api/predictions/v1/picks",
  "sunset_date": "2026-04-01"
];
```

### Phase 4: Complete Migration (Week 4)

**Remove legacy endpoints:**
- Delete redundant API files
- Update all references to use unified endpoints
- Remove redirects

---

## Implementation Details

### Database Schema Changes

**Create unified predictions table:**
```sql
CREATE TABLE predictions_unified (
    id INT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20),
    asset_class ENUM('stocks','crypto','forex','sports'),
    strategy VARCHAR(50),
    score DECIMAL(5,2),
    kelly_size DECIMAL(5,4),
    timeframe VARCHAR(20),
    regime_filter VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_asset_class (asset_class),
    INDEX idx_strategy (strategy),
    INDEX idx_score (score)
);
```

### Performance Optimization

**Caching strategy:**
```php
// predictions/api/cache.php
function get_cached_predictions($key, $ttl = 300) {
    $cache_file = "/tmp/predictions_{$key}_" . date('Y-m-d-H') . ".json";
    if (file_exists($cache_file) {
        $age = time() - filemtime($cache_file);
        if ($age < $ttl) {
            return json_decode(file_get_contents($cache_file), true);
        }
    }
    return null;
}
```

### Error Handling

**Graceful degradation:**
```php
function get_unified_data() {
    try {
        $cursor_data = get_cursor_genius_data();
        $sector_data = get_sector_rotation_data();
        return array_merge($cursor_data, $sector_data);
    } catch (Exception $e) {
        // Log error but return partial data
        error_log("Unified API error: " . $e->getMessage());
        return get_fallback_data();
    }
}
```

---

## Testing Strategy

### API Endpoint Testing

**Test each unified endpoint:**
```bash
# Test leaderboard endpoint
curl "https://findtorontoevents.ca/api/predictions/v1/leaderboard"

# Test picks with filters
curl "https://findtorontoevents.ca/api/predictions/v1/picks?asset_class=stocks"

# Test regime detection
curl "https://findtorontoevents.ca/api/predictions/v1/regime"
```

### Performance Testing

**Compare response times:**
- Legacy endpoints vs unified endpoints
- Cache effectiveness
- Concurrent user load

### Data Consistency Testing

**Verify data matches:**
- Unified picks vs legacy picks
- Performance metrics consistency
- Regime detection accuracy

---

## Risk Mitigation

### Data Loss Prevention

**Backup strategy:**
```bash
# Daily backups of legacy data
mysqldump -u user -p database predictions_legacy > backup_$(date +%Y%m%d).sql
```

### Rollback Plan

**Quick rollback procedure:**
1. Restore legacy endpoints from backup
2. Update navigation to point to legacy URLs
3. Remove unified API endpoints temporarily

### Monitoring

**Real-time monitoring:**
```php
// predictions/api/monitor.php
function log_api_usage($endpoint, $response_time, $success) {
    $log_entry = [
        'timestamp' => time(),
        'endpoint' => $endpoint,
        'response_time' => $response_time,
        'success' => $success
    ];
    file_put_contents('/logs/api_usage.log', json_encode($log_entry) . "\n", FILE_APPEND);
}
```

---

## Success Metrics

### API Performance
- ✅ Response time < 200ms for all endpoints
- ✅ 99.9% uptime
- ✅ Cache hit rate > 80%

### User Adoption
- ✅ 90% of traffic uses unified endpoints within 30 days
- ✅ Legacy endpoint usage decreases by 80%
- ✅ User satisfaction increases (survey)

### Data Quality
- ✅ No data discrepancies between legacy and unified
- ✅ Real-time regime detection accuracy > 95%
- ✅ Execution quality metrics tracking operational

---

**Ready for implementation review and feedback.**