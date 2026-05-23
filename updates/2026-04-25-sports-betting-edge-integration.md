# Sports Betting Edge Integration - Investigation and Suggestions

## Date
2026-04-25

## Investigation Summary

### Betting Sites Analyzed
- **OLG.ca (Ontario Lottery and Gaming)**: Offers PROLINE+ sportsbook with Canadian odds. Focuses on major sports like NHL, NBA, NFL, MLB, soccer. Features live betting and props.
- **Betway.com**: International sportsbook with odds in CAD for Canadian users. Covers global sports including NBA, NHL, soccer leagues, tennis.

### Methodologies Researched
- **Value Betting**: Identify bets where true probability exceeds bookmaker-implied probability.
- **Expected Value (EV) Calculations**: Use formulas to quantify edge.
- **Arbitrage**: Exploit price differences across books for guaranteed profit.
- **Line Shopping**: Compare odds across platforms to find best value.
- **Data-Driven Analysis**: Incorporate advanced metrics, AI models, historical data.
- **First Half/Period Betting**: Focus on shorter timeframes with less variance.
- **Accumulator Strategies**: Build multi-leg bets with correlated outcomes.
- **Bankroll Management**: Kelly Criterion for optimal staking.

### Prediction Communities and Markets
- **Polymarket**: Blockchain-based prediction market with $10B+ monthly volume. Covers NFL, NBA, NHL, soccer. Crowd-sourced probabilities often more accurate than single books.
- **Kalshi**: CFTC-regulated with $12B+ volume. Sports contracts for NFL, NBA, etc.
- **FanDuel Predicts**: Sports-focused prediction markets.
- **SharpPredict**: US legal prediction market for sports outcomes.
- **Communities**: Reddit (r/sportsbook), Twitter betting analysts, forums like ProbWin.

## Identified Edges

### High-Probability Wins Opportunities
1. **Prediction Market vs Bookmaker Discrepancies**: Prediction markets like Polymarket aggregate crowd wisdom, potentially more accurate. E.g., if Polymarket shows Arsenal at 88% for EPL win but bookmaker implied prob is 80%, edge in betting with bookmaker.
2. **Value in Underserved Markets**: Sports with rich data (NBA, NHL) where models can predict better than lines.
3. **Props and Futures**: Mispriced player props, season awards where public bias skews lines.
4. **Live Betting Edges**: During games, prediction markets update faster than bookmaker odds.
5. **Arbitrage Between Platforms**: Odds differences between OLG, Betway, and international books.

### Specific Edge Examples
- **NBA Games**: Use first-half betting strategies; data shows less variance in early periods.
- **Soccer Accumulators**: Correlated outcomes in leagues with prediction market coverage.
- **NHL Props**: Goalie saves, shots on goal where advanced metrics reveal value.

## Integration Suggestions

### New Module: `alpha_engine/sports_betting_edge.py`
- Scrape odds from OLG and Betway APIs (if available) or use Selenium/Puppeteer for site scraping.
- Fetch prediction market data from Polymarket/Kalshi APIs.
- Calculate EV by comparing implied probabilities.
- Output high-EV bets with staking recommendations using Kelly Criterion.

### Integration with Existing Code
- Add to `production_scanner.py`: Include sports betting scans alongside crypto/stock scans.
- Leverage `prediction_market_consensus.py` for cross-market consensus including sports.
- Use `ml_gatekeeper/gatekeeper.py` to validate sports predictions.
- Update `audit_trail/dashboard_generator.py` to include sports betting edges in audit dashboard.

### Implementation Steps
1. Build odds scraper with error handling for geo-restrictions.
2. Integrate prediction market APIs (Polymarket has public API).
3. Develop EV calculator using existing math utilities.
4. Add to scanner pipeline with configurable thresholds (e.g., min EV 2%).
5. Test with paper trading in existing paper_trading/strategies.

### Potential Challenges
- API access: OLG/Betway may not have public APIs; require web scraping.
- Regulatory: Ensure compliance with Canadian betting laws.
- Latency: Prediction markets update in real-time; ensure timely data.
- Model Accuracy: Validate against historical data before live use.

### Verification
- Backtest against past seasons using historical odds data.
- Monitor paper trading performance.
- Update audit trail with findings.

## Recommended Next Steps
- Implement scraper prototype.
- Add sports edge scanning to production runs.
- Document in AGENTS.md for future reference.