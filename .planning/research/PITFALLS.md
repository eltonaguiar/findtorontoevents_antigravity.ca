# Domain Pitfalls

**Domain:** Verified forex/futures/commodity copy trader aggregation
**Researched:** 2026-03-21

## Critical Pitfalls

Mistakes that cause bad signals, wasted money, or security issues.

### Pitfall 1: Myfxbook Stats Manipulation
**What goes wrong:** Traders manipulate Myfxbook verified accounts by using multiple accounts (show winners, hide losers), opening hedged positions to hide drawdown, or using high leverage on small accounts to show massive gains.
**Why it happens:** Myfxbook connects to broker accounts but doesn't detect hedging, account swapping, or survivorship within a trader's account set.
**Consequences:** Following a "verified 3715% gain" account that is actually one of 50 accounts, where 49 blew up.
**Prevention:**
  - Cross-reference with independent verification (Darwinex, broker statements)
  - Flag accounts with suspiciously low drawdown relative to returns (FX Stabilizer: 3715% gain, 12% DD = extremely suspicious)
  - Check trade count vs. duration (4334 trades over 3549 days = reasonable)
  - Check profit factor: >3.0 on large sample size = likely manipulation
**Detection:** Profit factor > 3.0 AND drawdown < 15% AND gain > 500% = almost certainly manipulated or survivorship biased.

### Pitfall 2: Survivorship Bias in Platform Leaderboards
**What goes wrong:** You build a scraper that tracks "top 20 systems" on Myfxbook or "top 10 DARWINs." Next month, half are replaced by new top performers. The previous "top" systems crashed.
**Why it happens:** Leaderboards only show current winners. Failed strategies silently disappear.
**Consequences:** Always chasing yesterday's winners. Classic momentum trap in strategy selection.
**Prevention:**
  - Track ALL scraped traders over time, including those who drop off leaderboards
  - Weight by track record duration (minimum 12 months)
  - Penalize sudden appearances on leaderboards (likely recent lucky streak)
  - Record date of first discovery and date of last appearance
**Detection:** If >30% of your tracked traders disappear from leaderboards within 3 months, survivorship bias is significant.

### Pitfall 3: API Rate Limiting and IP Bans
**What goes wrong:** Scraper makes too many requests to Myfxbook/eToro/ZuluTrade, gets IP banned, and all data collection stops.
**Why it happens:** Many platforms have aggressive anti-scraping measures. Myfxbook returns 403 on direct web fetch. FTMO leaderboard is dynamically loaded.
**Consequences:** Complete data blackout until IP rotated or ban lifted.
**Prevention:**
  - 2-5 second delay between requests
  - Exponential backoff on 429/403 errors
  - Rotate user agents
  - Use official APIs where available (Darwinex, C2) instead of scraping
  - Cache aggressively -- trader profiles don't change hourly
**Detection:** Monitor HTTP response codes. >5% error rate = throttle immediately.

### Pitfall 4: Subscription Cost Creep (Collective2)
**What goes wrong:** You subscribe to 20 C2 strategies at $100-300/month each to monitor their signals. Monthly cost: $2,000-6,000.
**Why it happens:** C2 charges per-strategy subscription. The API only works for subscribed strategies.
**Consequences:** Massive ongoing cost with no guarantee of signal quality.
**Prevention:**
  - Start with 2-3 high-conviction strategies only
  - Monitor public leaderboard data (free) to identify candidates
  - Only subscribe after 3+ months of free monitoring
  - Calculate cost-per-signal and compare to potential returns
  - Set monthly budget cap ($200-500)
**Detection:** If subscription costs exceed 2% of trading capital monthly, it's not viable.

### Pitfall 5: Demo Account Illusion (FTMO)
**What goes wrong:** Treating FTMO leaderboard performance as equivalent to real-money track records. Building confidence in signals from what are fundamentally demo accounts.
**Why it happens:** FTMO explicitly states "all accounts are demo accounts with fictitious funds in a simulated environment." The leaderboard shows impressive numbers but without real market impact.
**Consequences:** False confidence in signal quality. Demo trading has no slippage, no emotional pressure, and different fill behavior.
**Prevention:**
  - Never use FTMO signals as primary data source
  - Use FTMO data only for strategy pattern identification (what types of strategies pass challenges)
  - Weight FTMO verification as MEDIUM at best, never HIGH
**Detection:** If FTMO-sourced signals are a top contributor to consensus, your verification scoring is too lenient.

## Moderate Pitfalls

### Pitfall 6: Currency/Symbol Normalization Failures
**What goes wrong:** Darwinex reports "EURUSD," Myfxbook reports "EUR/USD," C2 reports "6E" (futures), eToro reports "EURUSD." Same instrument, four formats.
**Prevention:**
  - Build symbol normalization map (already exists for crypto in your system)
  - Include futures contract codes (6E, 6B, 6J = EUR, GBP, JPY futures)
  - Handle with/without slashes, uppercase/lowercase
  - Map commodity names: "Gold" = "XAU/USD" = "GC=F" = "XAUUSD"

### Pitfall 7: Time Zone Mismatches in Signal Timing
**What goes wrong:** A Darwinex signal fires at 14:00 UTC, an FTMO trader's London session entry is 07:00 UTC, Myfxbook timestamps are in broker time (varies). Consensus engine thinks they're different signals.
**Prevention:**
  - Normalize all timestamps to UTC
  - Define signal windows (same day = same signal, not same minute)
  - Account for platform-specific timestamp conventions

### Pitfall 8: Darwinex Risk Adjustment Confusion
**What goes wrong:** DARWIN returns are risk-managed by Darwinex independently of the trader. A DARWIN showing 10% monthly is NOT what the underlying trader earned -- Darwinex applies its own leverage/deleveraging.
**Prevention:**
  - Use D-Score and Performance (Pf) attribute to assess underlying strategy quality
  - Understand that DARWIN returns reflect Darwinex's risk management, not raw strategy returns
  - Do not compare DARWIN monthly returns directly with Myfxbook account returns

### Pitfall 9: eToro CopyTrader Minimum Investment Requirements
**What goes wrong:** You identify a great eToro trader to monitor, but their minimum copy investment is $20,000 (JeppeKirkBonde) or even more.
**Prevention:**
  - Focus on monitoring portfolio data via API, not actual copy trading
  - Track their positions as signals without needing to copy
  - Budget accordingly if actual copy trading is desired

## Minor Pitfalls

### Pitfall 10: Stale Data from Infrequent Updates
**What goes wrong:** Running scrapers daily but trader rankings update monthly. Wasting compute and API calls.
**Prevention:** Match scraping frequency to data update frequency:
  - Darwinex DARWIN quotes: Real-time (WebSocket)
  - Darwinex DarwinIA rankings: Monthly
  - Myfxbook system stats: Daily
  - C2 signals: Real-time (when subscribed)
  - eToro portfolios: Hourly at most

### Pitfall 11: Forex Factory Forum Noise
**What goes wrong:** Using Forex Factory threads as a signal source or validation tool. Threads are full of affiliate marketers, vendor shills, and survivorship bias.
**Prevention:** Use Forex Factory ONLY for identifying manipulation patterns and red flags, never as a positive signal source.

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Darwinex Integration | Risk-adjustment confusion | Use D-Score + raw performance, not DARWIN return |
| Darwinex Integration | Token expiry (3600s trading API) | Auto-refresh mechanism |
| Collective2 Pipeline | Subscription cost creep | Budget cap, start with 2-3 strategies |
| Collective2 Pipeline | Simulated vs. real fills | Only trust broker-linked fills |
| Myfxbook Scraping | Stats manipulation | Cross-reference, flag suspicious profiles |
| Myfxbook Scraping | IP ban from scraping | Rate limiting, browser automation, caching |
| eToro Monitoring | API early access restrictions | Build scraper-ready code, enable when API opens |
| Cross-Platform Consensus | Symbol normalization | Comprehensive mapping including futures codes |
| All Phases | Survivorship bias | Track traders over time, penalize new entrants |

## Sources

- Forex Factory Myfxbook manipulation discussion: https://www.forexfactory.com/thread/588456-be-cautious-of-myfxbook-stats-they-can-be-manipulated
- Darwinex D-Score documentation: https://help.darwinex.com/d-score
- Darwinex Performance attribute: https://help.darwinex.com/performance-attribute
- Collective2 fee structure: https://collective2.com/reviews
- FTMO disclaimer on demo accounts: https://ftmo.com/en/leaderboard/
- eToro Popular Investor requirements: https://www.etoro.com/discover/people
