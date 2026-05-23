# Asset Class Master Plan – 2026‑03‑11 00:04 EST

## Objective
Create a reproducible, data‑driven system that generates and tracks trade picks across multiple asset classes (stocks, futures, ETFs, penny stocks, crypto, meme‑coins, forex, mutual funds, sports‑betting). Leverage existing “DNA evolution strategies”, back‑testing frameworks, and dashboards to identify high‑certaintyability opportunities with strong Sharpe, low draw‑down, and consistent P&L.

---

## 1. Architecture Overview
| Component | Description | Re‑use from repo |
|-----------|-------------|-----------------|
| **DNA Evolution Engine** | Genetic‑algorithm based optimizer that evolves strategy parameters. | `alpha_engine/mercury_ai_strategies.py`, `alpha_engine/strategy_mutation_engine.md` |
| **Portfolio Generator** | Creates 10‑30 portfolios per asset class, each with a distinct parameter set. | `alpha_engine/portfolio_manager.py` |
| **Back‑test Runner** | Runs historical simulations, records entry/exit timestamps, P&L, draw‑down, Sharpe. | `alpha_engine/survivor_backtest.py`, `alpha_engine/tournament_engine.py` |
| **Metrics Dashboard** | Stores and visualises realized/unrealized P&L %, position size, entry/exit EST, TP/SL. | `audit_pnl.py`, `alpha_engine/track_record.py` |
| **Tournament Engine** | Ranks portfolios per asset class and globally. | `alpha_engine/tournament_engine.py` |
| **Reporting** | Generates markdown/HTML summary of predictability success rates. | `alpha_engine/prove_winners.py` |

---

## 2. Asset‑Class Specific Plan (with concrete examples)
### 2.1 Stock & Futures (ES, NQ, CL, ZN …)
1. Pull existing stock dashboards (`*_Quantitative_Trading_Algorithms.md`).
2. Feed those symbols into the DNA engine with the following strategy families (see `ALL_STRATEGIES.md`):
   - Mean‑reversion (`connors_rsi2`, `kalman_mean_reversion`)
   - Market‑making (`orderbook_strategies`)
   - Statistical arbitrage (`pairs_spread_btceth` – adapted for equities)
   - Order‑flow (`smart_money_fvg`)
   - Trend‑following (`vol_risk_premium`, `dynamic_momentum_scaling`)
3. Generate 15 portfolios, each with a unique parameter genome.
4. Back‑test using `alpha_engine/backtest_new_strategies.py`.
5. Record: entry/exit EST, TP/SL, position size, Unrealized/Realized P&L %, Sharpe, max‑drawdown.

### 2.2 Forex (EURUSD, USDJPY, GBPUSD, AUDUSD …)
1. Use existing forex data (`findforex2/portfolio/`).
2. Apply DNA engine with macro‑driven and high‑frequency pattern families (see `ALL_STRATEGIES.md` – *Alpha Engine — Forex*):
   - `funding_rate_extreme`
   - `connors_rsi2_crypto`
   - `cross_sectional_momentum`
   - `ai_cci_divergence`
3. Create 20 portfolios, back‑test, capture same metrics.

### 2.3 Penny Stocks
1. Load list from `findstocks/portfolio2/penny‑stocks.html`.
2. Run a lightweight version of the DNA engine focusing on volatility breakout & liquidity filters (`baby_strategies` list).
3. Generate 10 portfolios.

### 2.4 Meme Coins & Crypto
1. Existing crypto portfolios are already audited – reuse them as baseline.
2. Add two new DNA‑evolved portfolios targeting low‑risk, high‑probability spikes (see `ALL_STRATEGIES.md` – *KIMI Rise of the Claw – Crypto Acceleration*):
   - `signal_pump_detector`
   - `signal_whale_size_trade`
3. Track volatility; if > 150% daily swing, flag as “high‑risk”.

### 2.5 ETFs & Indices
1. Pull ETF list from internal dashboards.
2. Apply trend‑following & sector‑rotation strategies (`sector_momentum_7d`, `etf_flow_rotation`).
3. Create 12 portfolios.

### 2.6 Mutual Funds (future work)
1. Pull stats from the provided URLs.
2. Run a simplified DNA run focusing on risk‑adjusted return.
3. Create 5 exploratory portfolios.

### 2.7 Sports Betting (future work)
1. Treat each betting market as a binary asset class.
2. Apply the same tournament ranking logic.

---

## 3. Data Capture Schema (CSV/DB)
| Column | Description |
|--------|-------------|
| `asset_class` | e.g., `stock`, `forex`, `crypto` |
| `portfolio_id` | Unique identifier for the DNA‑generated portfolio |
| `symbol` | Ticker or contract code |
| `entry_dt_est` | Entry timestamp (EST) |
| `exit_dt_est` | Exit timestamp (EST) |
| `position_size` | Dollar or contract amount |
| `tp` | Take‑profit level |
| `sl` | Stop‑loss level |
| `unrealized_pnl_pct` | % P&L while position is open |
| `realized_pnl_pct` | % P&L after exit |
| `sharpe` | Annualised Sharpe ratio |
| `max_drawdown_pct` | Maximum draw‑down during trade |
| `status` | `open`, `closed`, `filtered` |

All tables are stored under `alpha_engine/track_record.py` and exported to `audit_report_findtorontoevents.md`.

---

## 4. Tournament & Ranking
1. After back‑testing, feed results into `alpha_engine/tournament_engine.py`.
2. Scoring criteria (weights):
   - Sharpe × 0.4
   - Realized P&L × 0.3
   - Max‑drawdown (inverse) × 0.2
   - Consistency (percentage of winning trades) × 0.1
3. Produce per‑class leaderboard and a global leaderboard.
4. Export markdown summary `ASSET_CLASS_MASTERPLAN_2026-03-11_0004.md` with tables of top‑5 portfolios per class.

---

## 5. Next Steps (Action Items)
- [ ] **Create CSV schema & database tables** – `alpha_engine/track_record.py`.
- [ ] **Implement portfolio generator** for each class – `alpha_engine/portfolio_manager.py`.
- [ ] **Run back‑tests** – schedule via `alpha_engine/survivor_backtest.py`.
- [ ] **Collect metrics** – extend `audit_pnl.py` to output the schema above.
- [ ] **Run tournament** – `alpha_engine/tournament_engine.py`.
- [ ] **Generate final markdown report** – update this file with live results.

---

## 6. Expected Outcome
A continuously updating, transparent system that:
- Generates 10‑30 diversified portfolios per asset class.
- Tracks every trade with entry/exit EST timestamps, TP/SL, position size.
- Provides real‑time Unrealized/Realized P&L %.
- Ranks portfolios by Sharpe, draw‑down, and consistency.
- Identifies the most predictable asset classes (likely stocks, futures, forex) while flagging high‑volatility crypto and meme‑coins.
- Supplies a concise markdown summary for decision‑makers.

---

## 7. Sub‑Agent Deployment Strategy
We will split the work across specialized sub‑agents (or iterative workflows) to create and verify portfolios for each asset class.

### Agent 1 – High‑Liquidity / Macro Predictors
- **Focus:** Stock index futures (ES, NQ), commodities (CL), rates (ZN), and major forex pairs (EURUSD, USDJPY, GBPUSD, AUDUSD).
- **Mission:** Connect to institutional data sources (OANDA, Polygon) and run statistically‑driven arbitrage, order‑flow, and mean‑reversion DNA mutations. Leverage the DNA evolution engine to generate 10‑30 portfolios per class, each with distinct parameter genomes.
- **Key Strategies (from `ALL_STRATEGIES.md`):** `connors_rsi2`, `kalman_mean_reversion`, `orderbook_strategies`, `vol_risk_premium`, `dynamic_momentum_scaling`.

### Agent 2 – Legacy Dashboards Resurrection
- **Focus:** Pre‑existing stock, mutual‑fund, and multi‑asset dashboards.
- **Mission:** Audit the stale endpoints (`findstocks/portfolio2/`, `findmutualfunds/portfolio1/`), fix 404s, and wire the data into the unified Portfolio Schema. Verify whether any legacy ML‑tracked picks still achieve a Sharpe > 1.5.

### Agent 3 – Asymmetric Speculation
- **Focus:** Penny stocks and meme‑coins.
- **Mission:** Detect volatility spikes, sentiment surges, and pump‑dump patterns. Allocate ultra‑strict risk (≤ 0.5 % capital per trade) and treat each bet like an option. Use the baby‑strategy suite (`baby_strategies/*.py`) for rapid signal generation.

### Agent 4 – Crypto Audit Monitoring
- **Focus:** Crypto assets.
- **Mission:** Continue monitoring existing crypto portfolios; automatically disable any strategy that falls below the live‑ready threshold (Sharpe < 1.0, WR < 45 %). No new capital will be allocated until volatility stabilises.

---

## 8. Immediate Next Action
Start with **Agent 1** – refactor the DNA strategy engine to accept Futures and Forex data formats. This involves:
1. Abstracting the data‑ingestion layer (`alpha_engine/data/`).
2. Adding symbol‑specific adapters for futures (e.g., `ES`, `NQ`) and forex (e.g., `EURUSD`).
3. Running a pilot generation of 5 portfolios per class and storing the results in `alpha_engine/track_record.py`.

Once the pilot results are available, we will evaluate Sharpe, draw‑down, and consistency before scaling to the full 10‑30 portfolio range.

---

## 9. Asset‑Class Specific Game‑Plans & Scoring Filters
We will use the live audit interface **https://findtorontoevents.ca/audit/** to expose a searchable, scored list of picks. Each asset class will have a tailored scoring model that combines:
- **Freshness** – time since entry (≤ 24 h gets a freshness boost).
- **Profitability** – realized P&L % and expected TP/SL distance.
- **Risk** – max draw‑down, volatility regime, and position‑size relative to capital.
- **User Risk Profile** – three preset profiles (Conservative, Balanced, Aggressive) that weight the above factors differently.

The scoring function (example for a single pick) is:
```python
score = (
    0.3 * (1 - age_hours/48)                     # freshness (0‑1)
    + 0.3 * (realized_pnl_pct / 100)              # profit
    + 0.2 * (1 - max_drawdown_pct/0.2)            # risk (max 20% DD)
    + 0.2 * (1 - volatility_regime_score)         # regime (0‑1, lower vol = higher score)
)
# Adjust weights per profile:
#   Conservative: risk weight +0.2, profit weight -0.1
#   Balanced:    default weights (as above)
#   Aggressive:  profit weight +0.2, risk weight -0.1
```

### 9.1 Stocks & Futures
- **Data Sources:** `alpha_engine/forex_strategies.py`, `alpha_engine/equity_strategies.py`.
- **Key Strategies:** `connors_rsi2`, `vol_risk_premium`, `dynamic_momentum_scaling`.
- **Filter Criteria:**
  - Freshness ≤ 12 h.
  - Sharpe ≥ 1.2.
  - Max draw‑down ≤ 10 %.
  - Position size ≤ 2 % of capital.
- **Scoring Adjustments:** Conservative profile adds +0.1 to risk weight; Aggressive adds +0.1 to profit weight.

### 9.2 Forex
- **Data Sources:** `alpha_engine/forex_strategies.py`.
- **Key Strategies:** `funding_rate_extreme`, `cross_sectional_momentum`, `ai_cci_divergence`.
- **Filter Criteria:**
  - Entry within the last 4 h (high‑frequency edge).
  - Realized P&L ≥ 0.5 % per trade.
  - Volatility regime **NORMAL** (ADX < 20).
- **Scoring Adjustments:** Balanced profile uses default weights; Aggressive boosts profit component.

### 9.3 ETFs & Indexes
- **Data Sources:** `alpha_engine/equity_strategies.py` – sector‑rotation module.
- **Key Strategies:** `sector_momentum_7d`, `etf_flow_rotation`.
- **Filter Criteria:**
  - Minimum 5‑day hold to avoid churn.
  - Sharpe ≥ 1.0.
  - Max draw‑down ≤ 12 %.
- **Scoring Adjustments:** Conservative adds a volatility‑penalty for high‑beta ETFs.

### 9.4 Penny Stocks
- **Data Sources:** `baby_strategies/*.py`.
- **Key Strategies:** `adaptive_momentum`, `bb_squeeze_breakout`.
- **Filter Criteria:**
  - Volume ≥ 200 k shares on entry day.
  - Entry price ≤ $5.
  - Max draw‑down ≤ 30 % (higher tolerance due to volatility).
- **Scoring Adjustments:** Aggressive profile gives a +0.15 boost to profit weight; Conservative caps position size to 0.5 % of capital.

### 9.5 Meme Coins
- **Data Sources:** `alpha_engine/crypto_strategies.py`.
- **Key Strategies:** `signal_pump_detector`, `signal_whale_size_trade`.
- **Filter Criteria:**
  - Freshness ≤ 6 h.
  - Volatility ≤ 150 % (exclude extreme spikes).
  - Expected TP/SL ratio ≥ 1.5.
- **Scoring Adjustments:** Aggressive profile heavily weights profit; Conservative adds a high‑risk penalty for volatility > 100 %.

### 9.6 Crypto (Core)
- **Data Sources:** `alpha_engine/crypto_strategies.py` and `KIMI_RISEOFTHECLAW`.
- **Key Strategies:** `funding_rate_extreme`, `crypto_keltner_compression_expansion`.
- **Filter Criteria:**
  - Sharpe ≥ 1.5.
  - Max draw‑down ≤ 15 %.
  - Freshness ≤ 12 h.
- **Scoring Adjustments:** Balanced profile; Conservative adds a volatility‑penalty for assets with 24‑h price swing > 80 %.

### 9.7 Mutual Funds (Future)
- **Data Sources:** `findmutualfunds/portfolio1/` (static reports).
- **Key Strategies:** `sentiment_filter`, `risk_parity`.
- **Filter Criteria:**
  - Minimum 30‑day forward‑test history.
  - Sharpe ≥ 0.8.
  - Max draw‑down ≤ 20 %.
- **Scoring Adjustments:** Conservative profile favours low‑drawdown; Aggressive favours higher Sharpe.

---

## 10. Implementation Steps for the Scoring Dashboard
1. **Expose Picks API** – Extend `audit_dashboard` to serve JSON at `/audit/picks.json` containing all live picks with the fields defined in the Data Capture Schema.
2. **Scoring Engine** – Add a new module `alpha_engine/scoring_engine.py` that implements the scoring function above and applies the user‑selected risk‑profile.
3. **Frontend Filter UI** – Create a simple React component (or plain HTML/JS) on `https://findtorontoevents.ca/audit/` that:
   - Loads the picks JSON.
   - Allows the user to select a risk profile (Conservative / Balanced / Aggressive).
   - Provides sliders for freshness, profit, and risk weight overrides.
   - Displays a sortable table of picks with the computed score, colour‑coded by risk.
4. **Scheduler** – Use the existing `alpha_engine/track_record.py` cron to recompute scores every 5 minutes.
5. **Testing** – Run a back‑test of the scoring on the last 30 days of picks to verify that the top‑scored picks indeed have higher Sharpe and lower draw‑down than the baseline.

---

*Prepared by Kilo Code – 2026‑03‑11 00:04 EST*