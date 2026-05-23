# Architecture Patterns

**Domain:** Verified forex/futures/commodity copy trader aggregation
**Researched:** 2026-03-21

## Recommended Architecture

### Multi-Platform Aggregation Pipeline

```
Platform Scrapers (per-platform)
       |
       v
Normalization Layer (standardize metrics)
       |
       v
Verification Scoring Engine (cross-platform trust score)
       |
       v
Signal Extraction (Darwinex API + C2 API)
       |
       v
Consensus Engine (cross-reference verified signals)
       |
       v
Dashboard + Alerts (audit_dashboard integration)
```

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| `darwinex_scraper.py` (new) | Fetch DARWIN performance, quotes, allocations via API | Normalization layer |
| `collective2_scraper.py` (new) | Fetch C2 strategy signals via API | Normalization layer |
| `myfxbook_scraper.py` (new) | Scrape verified EA/system data (browser automation) | Normalization layer |
| `etoro_scraper.py` (new) | Fetch popular investor portfolios via API (when available) | Normalization layer |
| `verified_trader_normalizer.py` (new) | Standardize metrics across all platforms | All scrapers, scoring engine |
| `verification_scorer.py` (new) | Calculate cross-platform verification trust score | Normalizer, consensus engine |
| `verified_consensus_engine.py` (new) | Cross-reference signals from verified sources only | Existing consensus_backtester.py |
| Existing `generate_dashboard_data.py` | Dashboard data generation | All components |

### Data Flow

```
darwinex_scraper.py ----\
                         \
collective2_scraper.py ----> verified_trader_normalizer.py --> verification_scorer.py
                         /         |                                    |
myfxbook_scraper.py ----/          v                                    v
                              SQLite DB                     verified_consensus_engine.py
etoro_scraper.py ------/     (trader_profiles,                         |
                              performance_history)                      v
                                                            active_verified_picks.json
                                                                       |
                                                                       v
                                                              Audit Dashboard
```

## Patterns to Follow

### Pattern 1: Platform-Agnostic Trader Profile
**What:** Standardized trader profile that works across all platforms.
**When:** Every scraper must output this format.

```python
{
    "trader_id": "darwinex:GRT",           # platform:id
    "platform": "darwinex",
    "platform_verification": "HIGHEST",     # HIGHEST/HIGH/MEDIUM/LOW
    "name": "GRT",
    "track_record_months": 24,
    "total_trades": null,                   # if available
    "win_rate_pct": null,                   # if available
    "profit_factor": null,                  # if available
    "sharpe_ratio": null,                   # if available
    "max_drawdown_pct": 4.09,
    "monthly_return_pct": 10.65,
    "six_month_return_pct": 23.63,
    "instruments": [],                      # if available
    "strategy_type": null,                  # if available
    "verification_score": 85,               # computed
    "last_updated": "2026-03-21T00:00:00Z",
    "scraping_method": "api",               # api/browser/manual
    "raw_data": {}                          # platform-specific extras
}
```

### Pattern 2: Verification Score Calculation
**What:** Composite score (0-100) combining platform trust + track record + consistency.
**When:** After normalization, before consensus.

```python
def calculate_verification_score(trader: dict) -> int:
    """
    Score breakdown:
    - Platform verification level: 0-40 points
      HIGHEST (Darwinex): 40
      HIGH (eToro, Myfxbook): 30
      MEDIUM-HIGH (C2, FTMO): 25
      MEDIUM (ZuluTrade): 15
      LOW (TradingView): 5
    - Track record duration: 0-25 points
      12+ months: 25, 6-12: 15, 3-6: 10, <3: 5
    - Trade count: 0-15 points
      500+: 15, 100-500: 10, 50-100: 7, <50: 3
    - Drawdown quality: 0-20 points
      <10%: 20, 10-20%: 15, 20-30%: 10, >30%: 5
    """
    score = 0
    # Platform trust
    platform_scores = {
        "darwinex": 40, "etoro": 30, "myfxbook": 30,
        "collective2": 25, "ftmo": 25, "zulutrade": 15, "tradingview": 5
    }
    score += platform_scores.get(trader["platform"], 0)
    # Track record
    months = trader.get("track_record_months", 0)
    score += 25 if months >= 12 else 15 if months >= 6 else 10 if months >= 3 else 5
    # Trade count
    trades = trader.get("total_trades") or 0
    score += 15 if trades >= 500 else 10 if trades >= 100 else 7 if trades >= 50 else 3
    # Drawdown
    dd = trader.get("max_drawdown_pct") or 50
    score += 20 if dd < 10 else 15 if dd < 20 else 10 if dd < 30 else 5
    return min(score, 100)
```

### Pattern 3: Consensus Signal from Verified Sources
**What:** Only aggregate signals from traders with verification_score >= threshold.
**When:** After scoring, before dashboard output.

```python
def verified_consensus(picks: list, min_score: int = 60) -> list:
    """
    Filter picks to verified-only, then find consensus.
    Consensus = 2+ verified sources agree on direction for same instrument.
    """
    verified = [p for p in picks if p["verification_score"] >= min_score]
    # Group by normalized symbol
    by_symbol = {}
    for p in verified:
        sym = normalize_symbol(p["symbol"])
        by_symbol.setdefault(sym, []).append(p)
    # Find consensus
    consensus = []
    for sym, group in by_symbol.items():
        longs = [p for p in group if p["direction"] == "LONG"]
        shorts = [p for p in group if p["direction"] == "SHORT"]
        if len(longs) >= 2:
            consensus.append({"symbol": sym, "direction": "LONG",
                            "sources": len(longs), "avg_score": avg([p["verification_score"] for p in longs])})
        elif len(shorts) >= 2:
            consensus.append({"symbol": sym, "direction": "SHORT",
                            "sources": len(shorts), "avg_score": avg([p["verification_score"] for p in shorts])})
    return consensus
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Trusting Single-Platform Verification
**What:** Treating any single platform's "verified" badge as absolute truth.
**Why bad:** Myfxbook stats can be manipulated (Forex Factory reports). eToro risk scores can be gamed. FTMO accounts are demo.
**Instead:** Cross-reference across platforms. Require 2+ independent verifications for HIGH confidence.

### Anti-Pattern 2: Following Monthly Return Without Context
**What:** Ranking traders purely by highest monthly return.
**Why bad:** High returns often mean high risk. QXC showed 23.35% monthly return but is a brand-new DARWIN with no track record.
**Instead:** Weight by risk-adjusted metrics (Sharpe, Calmar ratio) and track record duration.

### Anti-Pattern 3: Scraping Without Rate Limiting
**What:** Hitting platform APIs/pages as fast as possible.
**Why bad:** Gets IP banned. Myfxbook already returns 403 on direct fetch.
**Instead:** Minimum 2-second delay between requests, exponential backoff on errors, respect robots.txt.

### Anti-Pattern 4: Storing Raw Platform Data as Source of Truth
**What:** Keeping platform-specific data formats in the main database.
**Why bad:** Each platform uses different metrics, scales, and time periods. Makes comparison impossible.
**Instead:** Always normalize to the standard trader profile format (Pattern 1) before storage.

## Scalability Considerations

| Concern | At 100 traders | At 1K traders | At 10K traders |
|---------|---------------|---------------|----------------|
| Scraping time | <5 min | 30-60 min | Need parallel scraping |
| Storage | ~1MB SQLite | ~50MB SQLite | Consider PostgreSQL |
| Consensus quality | Sparse | Good coverage | Excellent, but noise increases |
| API costs | Free (Darwinex) + 1-2 C2 subs | Moderate | Significant C2 subscription costs |

## Sources

- Darwinex API architecture: https://api.darwinex.com/store/
- Collective2 API docs: https://collective2.com/api-docs/latest
- Myfxbook verification help: https://help.myfxbook.com/knowledge-base/verification/
- Forex Factory Myfxbook manipulation thread: https://www.forexfactory.com/thread/588456-be-cautious-of-myfxbook-stats-they-can-be-manipulated
