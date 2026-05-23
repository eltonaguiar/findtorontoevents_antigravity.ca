# 🐾 Kimi's Claw - Algorithm Battle Arena

A real-time competition system that pits our top trading algorithms against each other to determine which generates the best returns.

## Overview

Kimi's Claw creates a virtual trading competition where algorithms start with $10,000 in virtual capital and compete to generate the highest returns. The system tracks:

- **Portfolio Value** - Real-time tracking of each algorithm's virtual portfolio
- **Total Return %** - Performance relative to starting capital
- **Win Rate** - Percentage of profitable trades
- **Sharpe Ratio** - Risk-adjusted returns
- **Max Drawdown** - Largest peak-to-trough decline

## Competing Algorithms

| Algorithm | Type | Status | Strategy |
|-----------|------|--------|----------|
| Alpha Momentum | Momentum | Active | Multi-horizon momentum with trend confirmation |
| Mean Reversion | Mean Reversion | Active | Bollinger band reversals and short-term corrections |
| Sector Rotation | Sector | Active | Rotates between sectors based on macro signals |
| ML Ranker | Machine Learning | Active | LightGBM/XGBoost cross-sectional ranking |
| Quality Value | Value | Active | Quality compounders with value overlay |
| Earnings Drift | Earnings | Paused | PEAD (Post-Earnings Announcement Drift) |
| Breakout Hunter | Breakout | Active | Volatility breakouts with volume confirmation |
| Trend Follower | Trend | Active | Classic trend following with position sizing |

## Features

### 📊 Real-Time Portfolio Charts
- Interactive Chart.js visualization
- Toggle time ranges: All Time, 30 Days, 7 Days, Today
- Click legend to show/hide algorithms
- Hover for detailed portfolio values

### 🏆 Live Leaderboard
- Dynamic ranking by total return
- Podium view for top 3 algorithms
- Full statistics table
- Auto-refresh every 30 seconds

### 📈 Algorithm Cards
- Mini portfolio charts for each algorithm
- Quick stats: Return, Win Rate, Sharpe
- Status indicators (Active/Paused)

### 🔥 Current Picks
- Top performing picks across all algorithms
- Recent algorithm selections
- Real-time return tracking

## API Endpoints

### Dashboard Data
```
GET /api/competition.php?action=dashboard
```
Returns complete competition data including all algorithms, portfolio history, and current picks.

### Leaderboard
```
GET /api/competition.php?action=leaderboard
```
Returns ranked list of algorithms with key statistics.

### Update Algorithm Result (Admin)
```
GET /api/competition.php?action=update&key=kimisclaw2026&algorithm=Alpha%20Momentum&ticker=AAPL&result=win&return_pct=5.2
```
Records the result of a completed trade.

### Add New Pick (Admin)
```
GET /api/competition.php?action=add_pick&key=kimisclaw2026&algorithm=Alpha%20Momentum&ticker=AAPL&entry_price=150.00
```
Records a new algorithm pick.

### Initialize Algorithms (Admin)
```
GET /api/competition.php?action=init&key=kimisclaw2026
```
Creates the initial set of competing algorithms.

## Database Schema

### kc_algorithms
- Stores algorithm metadata and current stats
- Tracks total return, win rate, Sharpe ratio
- Status field for active/paused control

### kc_portfolio_history
- Daily snapshots of portfolio values
- Enables chart visualization over time

### kc_algorithm_picks
- Individual trades/picks per algorithm
- Entry/exit prices and returns
- Links to ticker and company info

### kc_competition_events
- Audit trail for all competition events
- For debugging and transparency

## Setup

1. **Initialize Database Tables**
   ```bash
   # Visit the init endpoint (admin only)
   https://yourdomain.com/findstocks/kimis_claw/api/competition.php?action=init&key=kimisclaw2026
   ```

2. **Populate Initial Data**
   - The system starts with mock data
   - Replace with real picks using the `add_pick` endpoint
   - Update results using the `update` endpoint

3. **Access the Dashboard**
   ```
   https://yourdomain.com/findstocks/kimis_claw/
   ```

## Competition Rules

1. **Starting Capital**: Each algorithm begins with $10,000 USD
2. **Trade Recording**: All picks must be recorded before market open
3. **Result Tracking**: Trades are marked as win/loss based on closing prices
4. **Rebalancing**: Algorithms can hold multiple positions simultaneously
5. **Ranking**: Primary sort by total return, secondary by Sharpe ratio

## Integration with Existing Systems

Kimi's Claw integrates with:
- `portfolio2` database for stock data
- `consensus_performance.php` for trade outcomes
- `alpha_engine` for algorithm signals
- Daily price feeds for real-time updates

## Future Enhancements

- [ ] Live WebSocket updates
- [ ] Algorithm vs algorithm head-to-head battles
- [ ] User predictions on winners
- [ ] Historical season analysis
- [ ] Risk-adjusted ranking options

---

**Note**: This is a simulated competition for educational and research purposes. No real money is traded.
