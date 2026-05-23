# Feature Landscape

**Domain:** Verified forex/futures/commodity copy trader aggregation
**Researched:** 2026-03-21

## Table Stakes

Features the system must have to be useful.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Multi-platform trader discovery | Need breadth across platforms | Med | Darwinex, C2, Myfxbook minimum |
| Verification badge/level per trader | Core requirement -- must distinguish verified from self-reported | Low | Map each platform's verification method |
| Performance normalization | Different platforms report different metrics | Med | Normalize to: win_rate, profit_factor, sharpe, max_dd, monthly_return |
| Historical performance tracking | Need to track if trader stays consistent | Med | SQLite time-series per trader |
| Signal extraction (where possible) | Convert trader data into actionable picks | High | Only feasible for Darwinex + C2 programmatically |
| Cross-platform consensus | Same trader/strategy across platforms should be unified | Med | Symbol normalization already exists |

## Differentiators

Features that add unique value beyond basic aggregation.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Verification score (0-100) | Weighted score combining platform verification level + track record duration + trade count + drawdown | Med | No other aggregator does cross-platform verification scoring |
| Strategy reverse-engineering from verified traders | Identify patterns in top traders' instruments/timing/risk | High | Already have strategy_reverse_engineer.py |
| Regime detection per trader | Flag when a trader's edge degrades (regime change) | High | Compare rolling 30d vs lifetime stats |
| Consensus signals from verified-only sources | Only aggregate signals from traders above verification threshold | Med | Ties into existing consensus_backtester.py |
| Darwinex DARWIN portfolio builder | Auto-build diversified DARWIN portfolio via API | Med | Darwinex API supports investing |
| Cost-of-signal tracker | Track what it costs to access each signal source (C2 subscriptions, etc.) | Low | Helps with ROI calculation |

## Anti-Features

Features to explicitly NOT build.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| TradingView idea scraping | Ideas are unverified forecasts, not trades | Use Pine Script + webhooks for your own strategies |
| FTMO leaderboard scraping | Demo accounts, no signal export, dynamic JS | Monitor FTMO blog for strategy patterns (manual) |
| Auto-investing in DARWINs | Legal/regulatory complexity, risk management | Build monitoring + alerting first, manual investing |
| Blind signal copying | Following any top-ranked trader without vetting | Require minimum verification score + consensus |
| Real-money auto-execution | Massive liability and risk | Signal dashboard + alerts only, manual execution |

## Feature Dependencies

```
Platform API Integration -> Trader Discovery -> Performance Normalization -> Verification Scoring
Performance Normalization -> Historical Tracking -> Regime Detection
Signal Extraction -> Cross-Platform Consensus -> Consensus Signals
Verification Scoring + Consensus Signals -> Verified-Only Consensus Dashboard
```

## MVP Recommendation

Prioritize:
1. **Darwinex DARWIN monitor** -- API ready, highest verification, Python package available
2. **Performance normalization engine** -- Standardize metrics across platforms
3. **Verification scoring system** -- Core differentiator
4. **Myfxbook EA benchmarking scraper** -- Largest verified forex database

Defer:
- Collective2 integration: Subscription costs make it expensive to explore broadly
- eToro integration: API still in early access
- DARWIN portfolio auto-builder: Regulatory complexity
- Regime detection: Needs 3+ months of historical data first

## Sources

- Platform API documentation (Darwinex, C2, Myfxbook, eToro)
- BuyStocks.ai Darwinex top traders data
- Myfxbook community forums on API limitations
- eToro press release on public API launch (Oct 2025)
