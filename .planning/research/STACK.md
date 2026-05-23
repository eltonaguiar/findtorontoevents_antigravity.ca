# Technology Stack

**Project:** Verified Forex/Futures/Commodity Copy Trader Integration
**Researched:** 2026-03-21

## Recommended Stack

### Core Integration Libraries
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| darwinexapis | Latest | Darwinex DARWIN data + trading API | Official Python package, OAuth2, REST + WebSocket, highest verification platform |
| requests | 2.31+ | Collective2 API, Myfxbook API | Standard HTTP client for REST APIs |
| playwright | Latest | Myfxbook/FTMO/ZuluTrade scraping | Browser automation for pages that block direct fetch (403s) |

### Data Storage
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| SQLite | 3.x | Trader profiles, performance history, signal tracking | Already used by KIMI system (signal_tracker.db), consistent with existing architecture |
| JSON files | - | Active picks, quick-access data | Consistent with existing copy_trader_intel/data/ pattern |

### Infrastructure
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| GitHub Actions | - | Scheduled scraping/monitoring | Already running every 15-30 min for existing systems |
| Python 3.10+ | 3.10+ | All scrapers and integrations | Consistent with existing codebase |

### Supporting Libraries
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| myfxbook (PyPI) | Latest | Python Myfxbook API wrapper | For own-account monitoring |
| websockets | Latest | Darwinex real-time quotes | When implementing live DARWIN monitoring |
| beautifulsoup4 | Latest | HTML parsing fallback | Simpler scraping where playwright overkill |

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Darwinex API | darwinexapis (Python) | dwxconnect (MT4/5 bridge) | dwxconnect is for trading on Darwinex, not monitoring DARWINs |
| Browser automation | Playwright | Selenium | Playwright faster, better async support, smaller footprint |
| Data store | SQLite | PostgreSQL | Overkill for this use case, SQLite already in project |
| Scheduling | GitHub Actions | Cron/Celery | Already have Actions infrastructure, no new infra needed |

## API Authentication Requirements

```bash
# Darwinex: OAuth2 tokens
# - Data API: 6-month TTL token
# - Trading API: 3600-second TTL (auto-refresh needed)
# Get credentials at: https://www.darwinex.com/data/darwin-api

# Collective2: API key
# - Signal Entry API: key-based auth
# - AutoTrading API: username/password login
# Requires strategy subscription ($50-300/mo per strategy)

# Myfxbook: Session-based
# - Login with email/password
# - Session IP-bound, 1-month TTL
# API endpoint: https://www.myfxbook.com/api

# eToro: Account-based (early access)
# - Requires verified eToro account
# - Portal: https://api-portal.etoro.com/
```

## Installation

```bash
# Core
pip install darwinexapis requests beautifulsoup4 playwright websockets

# Playwright browsers
playwright install chromium

# Optional: Myfxbook Python wrapper
pip install myfxbook
```

## Environment Variables Needed

```bash
# Darwinex
DARWINEX_API_TOKEN=<OAuth2 token>
DARWINEX_CONSUMER_KEY=<app key>
DARWINEX_CONSUMER_SECRET=<app secret>

# Collective2
C2_API_KEY=<API key>
C2_USERNAME=<username>
C2_PASSWORD=<password>

# Myfxbook
MYFXBOOK_EMAIL=<email>
MYFXBOOK_PASSWORD=<password>

# eToro (when available)
ETORO_API_KEY=<key>
```

## Sources

- Darwinex API: https://api.darwinex.com/store/, https://github.com/darwinex/darwinexapis
- Collective2 API: https://collective2.com/api-docs/latest
- Myfxbook API: https://www.myfxbook.com/api
- eToro API: https://api-portal.etoro.com/
