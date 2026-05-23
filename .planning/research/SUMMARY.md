# Research Summary: Verified Forex/Futures/Commodity Copy Traders

**Domain:** Copy trading signal aggregation from verified platforms
**Researched:** 2026-03-21
**Overall confidence:** MEDIUM

## Executive Summary

Research across 7 major copy trading platforms reveals a clear hierarchy of verification quality. Darwinex stands far above the rest -- it is FCA/CNMV regulated, all trades execute on their servers, and DARWIN indices are independently audited synthetic financial products. Darwinex also has the most complete API ecosystem (REST + WebSocket + Python package), making it the top priority for programmatic integration.

Myfxbook provides the largest database of verified forex accounts (direct broker connection via investor password), but its API only accesses your own accounts -- extracting community/system data requires web scraping. The top verified EAs on Myfxbook show strong results (FX Stabilizer: 3715% gain over 3549 days, 12% max DD; Night Hunter Pro: 4+ years verified, prop-firm compatible). However, many high-return systems have suspiciously low drawdowns, suggesting potential manipulation or survivorship bias.

Collective2 is the strongest option for futures/forex signal automation -- it has 12K+ strategies with broker-linked fill verification and a proper Signal Entry + AutoTrading API. eToro recently launched public APIs (Oct 2025, early access) which will open programmatic access to 4,000+ copyable investors' portfolios.

FTMO and TradingView provide minimal integration value -- FTMO has no API and trades on demo accounts, while TradingView ideas are unexecuted forecasts with no verified fills.

## Key Findings

**Stack:** Darwinex Python API (darwinexapis) + Collective2 REST API for signal scraping, Myfxbook for benchmarking
**Architecture:** Multi-platform aggregation pipeline: Darwinex DARWINs + C2 strategies + Myfxbook EA monitoring -> consensus engine
**Critical pitfall:** Myfxbook stats can be manipulated (reported in Forex Factory threads). Never trust single-platform verification.

## Implications for Roadmap

Based on research, suggested phase structure:

1. **Phase 1: Darwinex Integration** - Highest verification, best API, immediate value
   - Addresses: Programmatic DARWIN monitoring, performance tracking, potential investing
   - Avoids: Unverified signal sources, API limitations

2. **Phase 2: Collective2 Futures/Forex Pipeline** - Second-best API, verified fills
   - Addresses: Futures signal sourcing, strategy discovery
   - Avoids: Subscription cost pitfall (need selective strategy subscription)

3. **Phase 3: Myfxbook EA Benchmarking** - Largest verified forex database
   - Addresses: EA performance benchmarking, community data scraping
   - Avoids: API limitations (need scraping infrastructure)

4. **Phase 4: eToro Popular Investor Monitoring** - Pending API general availability
   - Addresses: Regulated broker data, public portfolio tracking
   - Avoids: Early access restrictions

**Phase ordering rationale:**
- Darwinex first because it has the most complete API + highest verification
- C2 second because it covers futures (unique) and has direct signal access
- Myfxbook third because scraping infrastructure takes more effort
- eToro last because API is still in early access

**Research flags for phases:**
- Phase 1: Standard integration, unlikely to need more research
- Phase 2: Needs deeper research on C2 subscription model and which strategies to subscribe to
- Phase 3: Likely needs research on anti-scraping measures and rate limits
- Phase 4: Needs re-research when eToro API reaches general availability

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM | Darwinex API docs verified, C2 API confirmed, Myfxbook API limitations confirmed |
| Features | MEDIUM | Platform capabilities confirmed via multiple sources |
| Architecture | MEDIUM | Based on API documentation review, not implementation testing |
| Pitfalls | HIGH | Well-documented in forex communities (manipulation, survivorship bias) |

## Gaps to Address

- Could not access Myfxbook system pages (403) -- need browser automation to get full system listings
- ZuluTrade ranking data is dynamic and inaccessible via search
- FTMO leaderboard loads dynamically -- no static data available
- eToro API is in early access -- capabilities may change
- Darwinex DARWIN instruments/strategy types are not exposed in aggregator pages -- need per-DARWIN API queries
- Collective2 strategy pages returned 403 -- need direct platform access for full listings
