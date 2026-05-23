# QuanEngine Failover System

**Version:** 1.0  
**Last Updated:** 2026-03-08  
**Status:** Production Ready

---

## Overview

The QuanEngine Failover System provides multi-tier redundancy for all critical data paths and external services. When primary services fail (e.g., Binance API geo-restriction), the system automatically falls back through a chain of alternatives to ensure continuous operation.

### Key Features

- **4-Tier Data Source Failover:** yfinance → Binance → CoinGecko → CryptoCompare → Cache → Mock
- **5-Channel Notification Failover:** Discord Webhook → Discord Bot → Email → Slack → File Log
- **Automatic Health Monitoring:** Tracks source health, disables unhealthy sources, auto-recovery
- **Intelligent Caching:** Fresh cache → Stale cache → Mock data
- **Rate Limiting:** Respects API limits to avoid bans
- **Circuit Breaker:** Prevents cascading failures

---

## Quick Start

### 1. Validate Failovers

```bash
# Quick validation (2 minutes)
python scripts/validate_failovers.py --quick

# Full validation (5 minutes)
python scripts/validate_failovers.py --full
```

### 2. Check Health Status

```bash
# CLI report
python quan_engine/health_dashboard.py --report

# JSON output for monitoring
python quan_engine/health_dashboard.py --check --json

# Start HTTP server
python quan_engine/health_dashboard.py --serve --port 8080
# Then visit http://localhost:8080/health
```

### 3. Watch Mode

```bash
# Real-time monitoring
python quan_engine/health_dashboard.py --watch 30
```

---

## Architecture

### Data Source Failover Chain

```
┌─────────────────────────────────────────────────────────────────┐
│                    DATA FETCH REQUEST                           │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│ TIER 1: PRIMARY                                                  │
│ ├── yfinance (geo-safe, no API key)                             │
│ └── Binance.com + Binance.us + data-api.binance.vision         │
└─────────────────────┬───────────────────────────────────────────┘
                      │ All failed
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│ TIER 2: CRYPTO DATA APIs                                         │
│ ├── CoinGecko (free tier: 10-30 calls/min)                      │
│ └── CryptoCompare (free tier: 100k calls/month)                 │
└─────────────────────┬───────────────────────────────────────────┘
                      │ All failed
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│ TIER 3: CACHE                                                    │
│ ├── Fresh cache (< 60 min old)                                  │
│ └── Stale cache (< 24 hours old, with warning)                  │
└─────────────────────┬───────────────────────────────────────────┘
                      │ Cache empty
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│ TIER 4: MOCK DATA (Testing Only)                                 │
│ └── Synthetic data for testing (NEVER use in production)        │
└─────────────────────────────────────────────────────────────────┘
```

### Notification Failover Chain

Uses your existing Discord webhooks with automatic fallback:

```
┌─────────────────────────────────────────────────────────────────┐
│              NOTIFICATION REQUEST                                │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│ CHANNEL 1: Discord Primary (DISCORD_WEBHOOK_URL)                │
│          or DISCORD_WEBHOOK_PAPERTRADE (has default)            │
└─────────────────────┬───────────────────────────────────────────┘
                      │ Failed
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│ CHANNEL 2: Discord Portfolio (DISCORD_WEBHOOK_PORTFOLIO)        │
└─────────────────────┬───────────────────────────────────────────┘
                      │ Failed
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│ CHANNEL 3: Discord DNA (DISCORD_WEBHOOK_DNA_MASTER)             │
└─────────────────────┬───────────────────────────────────────────┘
                      │ Failed
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│ CHANNEL 4: Discord Bot API (DISCORD_BOT_TOKEN)                  │
└─────────────────────┬───────────────────────────────────────────┘
                      │ Failed
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│ CHANNEL 5: Email (SMTP) - if configured                         │
└─────────────────────┬───────────────────────────────────────────┘
                      │ Failed
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│ CHANNEL 6: Slack Webhook - if configured                        │
└─────────────────────┬───────────────────────────────────────────┘
                      │ Failed
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│ CHANNEL 7: File Fallback (ALWAYS WORKS)                         │
│ └── Logs to: logs/notifications/YYYY-MM-DD.jsonl               │
└─────────────────────────────────────────────────────────────────┘
```

---

## Configuration

### Environment Variables

The failover system uses your **existing configurations** (no new setup needed):

```bash
# Discord (already configured in your system)
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
export DISCORD_WEBHOOK_PAPERTRADE="https://discord.com/api/webhooks/..."
export DISCORD_WEBHOOK_DNA_MASTER="https://discord.com/api/webhooks/..."
export DISCORD_WEBHOOK_PORTFOLIO="https://discord.com/api/webhooks/..."
export DISCORD_WEBHOOK_SANDBOX="https://discord.com/api/webhooks/..."
export DISCORD_WEBHOOK_FRESHPICKS="https://discord.com/api/webhooks/..."

# Bot API (optional fallback)
export DISCORD_BOT_TOKEN="your-bot-token"
export DISCORD_ML_CHANNEL_ID="123456789"

# Email - SAME AS FINDTORONTOEVENTS.CA DATABASE BACKUPS
# Uses mail.50webs.com (configured in .github/workflows/db-backup-email.yml)
export SMTP_HOST="mail.50webs.com"
export SMTP_PORT="465"
export SMTP_USER="support@findtorontoevents.ca"
export SMTP_PASS="your-smtp-password"  # Same as EMAIL_SMTP_PASS secret
export ALERT_EMAIL_TO="zerounderscore@gmail.com,eaguiar2015@yahoo.ca"

# Slack (optional)
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."
```

**Notes:**
- Discord: System uses `DISCORD_WEBHOOK_PAPERTRADE` as default (already configured)
- Email: Uses the **same SMTP server** as your database backup workflow (mail.50webs.com)
- The password should be the same as your `EMAIL_SMTP_PASS` GitHub secret

### Config File (`quan_engine/config.py`)

```python
FAILOVER_CONFIG = {
    # Cache settings
    "cache_ttl_minutes": 60,
    "stale_data_ttl_hours": 24,
    "enable_stale_cache_fallback": True,
    "enable_mock_fallback": False,  # NEVER enable in production!
    
    # Retry settings
    "max_retries_per_source": 3,
    "retry_base_delay_seconds": 1.0,
    "retry_backoff_multiplier": 2.0,
    
    # Rate limits
    "rate_limits": {
        "coingecko": 10,       # calls per minute
        "cryptocompare": 100,
        "binance": 1200,
    },
}
```

---

## API Reference

### Data Fetching

```python
from quan_engine.failover_system import (
    fetch_klines_with_failover,
    fetch_price_with_failover,
    get_health_report
)

# Fetch OHLCV data (auto-failover)
df = fetch_klines_with_failover("BTCUSDT", "1h", limit=500)
if df.empty:
    logger.error("All data sources failed!")

# Fetch current price
price = fetch_price_with_failover("ETHUSDT")
if price is None:
    logger.error("Could not get price from any source")

# Check source health
health = get_health_report()
print(f"Healthy sources: {sum(1 for h in health.values() if h['is_healthy'])}")
```

### Notifications

```python
from shared.failover_notifications import (
    notify_info,
    notify_warning,
    notify_error,
    notify_critical,
    get_notification_health
)

# Info (batched with other non-critical)
notify_info("Scan complete", {"symbols": 10, "signals": 3})

# Warning
notify_warning("Rate limit approaching", {"calls_remaining": 50})

# Error (immediate)
notify_error("Binance API failed", {"error": "HTTP 451", "fallback": "CoinGecko"})

# Critical (guaranteed delivery, retries until success)
notify_critical("SYSTEM FAILURE", {"component": "database", "error": "Connection lost"})

# Check notification health
health = get_notification_health()
```

### Health Dashboard

```python
from quan_engine.health_dashboard import HealthDashboard

dashboard = HealthDashboard()

# Generate full report
report = dashboard.generate_report()
print(json.dumps(report, indent=2))

# Print formatted report
dashboard.print_report()

# Check individual components
results = dashboard.run_all_checks()
for name, status in results.items():
    print(f"{name}: {status.status} - {status.message}")
```

---

## Health Monitoring

### Component Status

| Component | Check Interval | Healthy Criteria |
|-----------|---------------|------------------|
| Data Sources | Every request | > 50% sources responding |
| Notifications | Every send | File fallback available |
| Database | On access | SQLite responsive |
| Disk Space | On request | < 80% used |
| Last Scan | On request | < 35 min ago |
| GitHub Actions | Manual | Workflows running |

### Health Status Levels

| Status | Color | Meaning | Action Required |
|--------|-------|---------|-----------------|
| Healthy | 🟢 | All systems operational | None |
| Degraded | 🟡 | Some redundancy lost | Monitor closely |
| Critical | 🔴 | Primary systems down | Immediate attention |

### Auto-Recovery

- **Unhealthy sources** are automatically disabled after 3 consecutive failures
- **Health checks** run continuously in background
- **Sources** are retested periodically for recovery
- **Circuit breaker** prevents cascading failures

---

## Testing

### Unit Tests

```bash
# Run all tests
pytest tests/test_failover_system.py -v

# Run specific test class
pytest tests/test_failover_system.py::TestCacheManager -v

# Run integration tests (hits real APIs)
pytest tests/test_failover_system.py -m integration --integration
```

### Manual Validation

```bash
# Test data fetch
python -c "
from quan_engine.failover_system import fetch_klines_with_failover
df = fetch_klines_with_failover('BTCUSDT', '1h', 100)
print(f'Fetched {len(df)} rows')
print(df.tail())
"

# Test notifications
python -c "
from shared.failover_notifications import notify_info, get_notification_health
notify_info('Test', {'key': 'value'})
print(get_notification_health())
"

# Test health dashboard
python -c "
from quan_engine.health_dashboard import HealthDashboard
d = HealthDashboard()
d.print_report()
"
```

---

## Troubleshooting

### Issue: All Data Sources Failing

**Symptoms:**
- `fetch_klines_with_failover()` returns empty DataFrame
- Health report shows 0 healthy sources

**Diagnosis:**
```bash
python scripts/validate_failovers.py
```

**Solutions:**
1. Check internet connectivity
2. Verify yfinance is installed: `pip install yfinance`
3. Check if running behind firewall/proxy
4. Review cache: Check `quan_engine/data/failover_cache/`

### Issue: Notifications Not Sending

**Symptoms:**
- Discord alerts not appearing
- No email received for critical errors

**Diagnosis:**
```bash
python -c "from shared.failover_notifications import get_notification_health; print(get_notification_health())"
```

**Solutions:**
1. Check file fallback: `tail logs/notifications/*.jsonl`
2. Verify Discord webhook URL is valid
3. Check SMTP credentials for email
4. Review rate limits

### Issue: Cache Growing Too Large

**Symptoms:**
- Disk space warning
- Slow cache operations

**Solution:**
```python
from quan_engine.failover_system import clear_cache
clear_cache()  # Clears all cached data
```

### Issue: Rate Limited by CoinGecko

**Symptoms:**
- HTTP 429 errors from CoinGecko
- Falling back to cache frequently

**Solutions:**
1. Reduce scan frequency
2. Upgrade to CoinGecko paid tier
3. Increase `coingecko_rate_limit` in config
4. Rely more on yfinance (primary source)

---

## Performance

### Latency Expectations

| Scenario | Expected Latency |
|----------|-----------------|
| yfinance (cached) | < 100ms |
| yfinance (fresh) | 1-3s |
| Binance API | 200-500ms |
| CoinGecko API | 500ms-2s |
| Cache read | < 50ms |
| Full failover chain | 5-15s |

### Rate Limits

| Source | Free Tier Limit | Our Config |
|--------|----------------|------------|
| yfinance | Unlimited | N/A |
| Binance | 1200 weight/min | Respected |
| CoinGecko | 10-30 calls/min | 10/min |
| CryptoCompare | 100k/month | 100/min |

---

## Deployment Checklist

Before deploying to production:

- [ ] Run `python scripts/validate_failovers.py --full`
- [ ] Set all environment variables for notifications
- [ ] Configure `enable_mock_fallback: False`
- [ ] Set up health dashboard monitoring
- [ ] Test Discord webhook in target channel
- [ ] Verify email SMTP credentials
- [ ] Check disk space for cache directory
- [ ] Review rate limit settings
- [ ] Set up log rotation for notification logs

---

## Roadmap

### Phase 1: Complete ✅
- [x] 4-tier data source failover
- [x] 5-channel notification failover
- [x] Health monitoring dashboard
- [x] Intelligent caching
- [x] Rate limiting

### Phase 2: Planned
- [ ] WebSocket fallback for real-time data
- [ ] Distributed cache (Redis)
- [ ] SMS notifications (Twilio)
- [ ] Push notifications (Firebase)
- [ ] Automatic circuit breaker tuning

### Phase 3: Future
- [ ] ML-based source quality prediction
- [ ] Geographic load balancing
- [ ] Peer-to-peer data sharing
- [ ] Blockchain-based audit trail

---

## Support

For issues or questions:

1. Check this documentation
2. Run validation: `python scripts/validate_failovers.py`
3. Check health: `python quan_engine/health_dashboard.py --report`
4. Review logs: `logs/notifications/`
5. File an issue with health report attached

---

**Remember:** The failover system is designed to be invisible when working correctly. If you're noticing it, something might need attention!
