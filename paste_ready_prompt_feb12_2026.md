# System Performance Analysis Prompt — Feb 12, 2026

Analyze the performance, functionality, and user experience of our financial intelligence platform hosted at https://findtorontoevents.ca/index.html. Visit and evaluate each of the following user-facing URLs. For each page, assess: load speed, data freshness, UI/UX quality, mobile responsiveness, broken links/features, API errors, and overall functionality.

---

## STOCKS & PORTFOLIO (17 pages)

1. https://findtorontoevents.ca/findstocks/portfolio2/hub.html — Investment Portfolio Hub (main dashboard with cards linking all features)
2. https://findtorontoevents.ca/findstocks/portfolio2/picks.html — Daily Stock Picks
3. https://findtorontoevents.ca/findstocks/portfolio2/consolidated.html — Consolidated Picks (aggregated signals from multiple algorithms)
4. https://findtorontoevents.ca/findstocks/portfolio2/horizon-picks.html — Invest by Time Horizon (2-week, 1-year backtested picks)
5. https://findtorontoevents.ca/findstocks/portfolio2/leaderboard.html — Algorithm Leaderboard (ranking 17+ algorithms)
6. https://findtorontoevents.ca/findstocks/portfolio2/dashboard.html — My Portfolios (equity curves, positions, metrics, vs SPY benchmark)
7. https://findtorontoevents.ca/findstocks/portfolio2/algo-study.html — Algo Study (algorithm deep-dive analysis)
8. https://findtorontoevents.ca/findstocks/portfolio2/learning-lab.html — Learning Lab
9. https://findtorontoevents.ca/findstocks/portfolio2/learning-dashboard.html — Self-Learning Algorithms (watch optimization in real-time)
10. https://findtorontoevents.ca/findstocks/portfolio2/smart-learning.html — Smart Learning
11. https://findtorontoevents.ca/findstocks/portfolio2/stock-intel.html — Stock Intelligence Dashboard (analyst ratings, insider MSPR, 13F, consensus)
12. https://findtorontoevents.ca/findstocks/portfolio2/stock-profile.html — Stock Profile (cross-asset view)
13. https://findtorontoevents.ca/findstocks/portfolio2/dividends.html — Dividends Dashboard (4-tab: dividends, earnings, fundamentals, upcoming)
14. https://findtorontoevents.ca/findstocks/portfolio2/penny-stocks.html — Penny Stock Finder (Yahoo screener, blocks OTC/Pink Sheets)
15. https://findtorontoevents.ca/findstocks/portfolio2/daytrader-sim.html — DayTrader Simulator
16. https://findtorontoevents.ca/findstocks/portfolio2/stats/index.html — Stats Dashboard
17. https://findtorontoevents.ca/findstocks/research/index.html — Research Hub ("Can individuals beat supercomputers?")

## LIVE TRADING & ALGORITHMS (7 pages)

18. https://findtorontoevents.ca/live-monitor/live-monitor.html — Live Trading Monitor (20 algorithms, paper trading: $10K capital, 5% sizing, 10 max positions, auto SL/TP)
19. https://findtorontoevents.ca/live-monitor/edge-dashboard.html — Edge Dashboard
20. https://findtorontoevents.ca/live-monitor/opportunity-scanner.html — Opportunity Scanner
21. https://findtorontoevents.ca/live-monitor/winning-patterns.html — Winning Patterns
22. https://findtorontoevents.ca/live-monitor/hour-learning.html — Hour Learning
23. https://findtorontoevents.ca/live-monitor/algo-performance.html — Algo Performance (Learned vs Original parameter comparison)
24. https://findtorontoevents.ca/live-monitor/conviction-alerts.html — Conviction Alerts

## GOLDMINES & SMART MONEY (4 pages)

25. https://findtorontoevents.ca/live-monitor/goldmine-dashboard.html — Goldmine Dashboard (multi-dimensional system health, underperformance detection)
26. https://findtorontoevents.ca/live-monitor/goldmine-alerts.html — Goldmine Alerts (critical alerts with severity levels)
27. https://findtorontoevents.ca/live-monitor/smart-money.html — Smart Money Intelligence (6-tab: Consensus, Analyst, Insider, Smart Money, Leaderboard, Showdown)
28. https://findtorontoevents.ca/live-monitor/multi-dimensional.html — Multi-Dimensional Dashboard (9D scoring system)

## CRYPTOCURRENCY (5 pages)

29. https://findtorontoevents.ca/findcryptopairs/index.html — Crypto Pairs Scanner (15 major pairs, 10 independent strategies)
30. https://findtorontoevents.ca/findcryptopairs/winners.html — Crypto Winner Scanner (multi-factor momentum, 7 technical indicators)
31. https://findtorontoevents.ca/findcryptopairs/meme.html — Meme Coin Scanner (DOGE, SHIB, PEPE, FLOKI with meme-specific indicators)
32. https://findtorontoevents.ca/findcryptopairs/portfolio/index.html — Crypto Portfolio Analysis (backtest strategies, compare scenarios)
33. https://findtorontoevents.ca/findcryptopairs/portfolio/stats/index.html — Crypto Portfolio Stats (performance metrics, strategy breakdowns)

## FOREX (3 pages)

34. https://findtorontoevents.ca/findforex2/index.html — Forex Scanner (15 major pairs, 8 independent strategies)
35. https://findtorontoevents.ca/findforex2/portfolio/index.html — Forex Portfolio Analysis (backtest, compare, find optimal TP/SL/hold)
36. https://findtorontoevents.ca/findforex2/portfolio/stats/index.html — Forex Portfolio Stats (win rates, performance metrics)

## SPORTS BETTING (1 page)

37. https://findtorontoevents.ca/live-monitor/sports-betting.html — Sports Bet Winner Finder (value bets & line shopping across 6 Canadian sportsbooks, NHL/NBA/NFL/MLB/CFL/MLS, paper betting: $1000 bankroll, quarter-Kelly sizing)

## GLOBAL / MULTI-ASSET (4 pages)

38. https://findtorontoevents.ca/findstocks2_global/index.html — Global Stocks Dashboard
39. https://findtorontoevents.ca/findstocks2_global/miracle.html — Miracle Stocks
40. https://findtorontoevents.ca/investments/index.html — Investment Hub (cross-asset entry point)
41. https://findtorontoevents.ca/findstocks/index.html — Stock Picks Landing Page

---

## WHAT TO EVALUATE PER PAGE

For each URL above, report on:

1. **Loads Successfully** — Does the page load without errors? Any console errors or broken resources?
2. **Data Freshness** — Is the data current or stale? Check timestamps, last-updated indicators.
3. **API Health** — Do the backend API calls return valid data? Any 500s, 404s, empty responses?
4. **UI/UX Quality** — Is the layout clean? Charts rendering? Tables populated? Tabs working?
5. **Mobile Responsiveness** — Does the page work on mobile viewports?
6. **Navigation** — Does the stock-nav.js navigation bar load and link correctly?
7. **Broken Features** — Any buttons, filters, search bars, or interactive elements that don't work?
8. **Performance** — Page load time, asset sizes, any obvious bottlenecks?

## SUMMARY FORMAT

After evaluating all 41 pages, provide:
- Overall health score (% of pages fully functional)
- List of critical issues (pages that fail to load or have major broken features)
- List of data freshness concerns (stale data older than expected refresh intervals)
- Top 5 highest-priority fixes
- Top 5 pages with best UX
- Any pages that appear to be duplicates or could be consolidated

## SYSTEM CONTEXT

- Platform: PHP 5.2.17 backend, React/TypeScript/Vite frontend, MySQL database
- Data sources: Yahoo Finance, Finnhub, TwelveData, FreeCryptoAPI, Foursquare, The Odds API, SEC EDGAR
- Automation: GitHub Actions run daily picks (weekdays 5PM EST), smart money (weekdays 6AM + Sunday 9AM), sports betting (5x daily)
- 20 trading algorithms with regime gating, paper trading simulation
- Sister site mirror: https://tdotevent.ca/
