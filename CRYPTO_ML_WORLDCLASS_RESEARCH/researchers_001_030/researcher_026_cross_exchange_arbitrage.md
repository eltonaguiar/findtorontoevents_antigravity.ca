# Researcher Profile: Dr. Ivan Smirnov

## Persona
- **Title:** Cross-Exchange Arbitrage Specialist
- **Expertise:** Statistical arbitrage, basis trading, triangular arbitrage, latency arbitrage
- **Years Experience:** 10
- **Background:** PhD Moscow School of Economics, former arbitrage trader at Alfa-Trading, now focuses on crypto cross-exchange strategies.

## Research Scope
**Primary Question:** How do world-class arbitrage systems exploit price differences across crypto exchanges and what ML techniques enhance profitability?

**Target Systems/Areas:**
- Simple cross-exchange arbitrage (BTC price difference)
- Triangular arbitrage (currency loops)
- Funding rate arbitrage (perpetual vs spot)
- Statistical arbitrage (pairs of correlated coins)
- Latency arbitrage (speed advantage)

## Methodology
1. **Sources:** Full codebase audit of `alpha_engine/`, `ml_battleground/`, `KIMI_RISEOFTHECLAW/`, and standalone arbitrage scripts.
2. **Extraction:** Identified all multi-exchange data fetching, price comparison, funding rate collection, and pairs trading logic.
3. **Analysis:** Evaluated each arbitrage type for implementation completeness, exchange coverage, risk management, and ML integration.
4. **Validation:** Cross-referenced backtest results in `FUNDING_ARB_REPORT.md` and live signal data in `alpha_engine/data/funding_rate_signals.json`.

---

## Key Findings (REAL CODEBASE AUDIT)

### 1. Multi-Exchange Data Sourcing

**Rating: STRONG (7/10)**

The codebase has genuine multi-exchange failover chains in two critical locations:

**`ml_battleground/shared/data_fetcher.py`** (lines 29-130):
- **Primary:** Binance REST (`api.binance.com`)
- **Failover 1:** OKX (`okx.com/api/v5/market/candles`)
- **Failover 2:** Bybit (`api.bybit.com/v5/market/kline`)
- Automatic fallback: if Binance returns <50 candles, tries OKX, then Bybit
- Covers 20 USDT pairs across 3 tiers (liquid, alt L1, mid-cap)
- Rate limiting: 100ms between requests

**`KIMI_RISEOFTHECLAW/multi_source_fetcher.py`** (lines 1-80):
- **7-exchange failover chain:** Binance, Bybit, OKX, KuCoin, Kraken, CoinCap, yfinance
- Separate chains for crypto OHLCV, forex rates, and stocks/ETFs
- Forex failover: Frankfurter (ECB), ExchangeRate-API, yfinance
- All free-tier APIs, no authentication required
- Designed for GitHub Actions running every 15 minutes

**Gap:** No CCXT library usage anywhere in the codebase. All exchange connectivity is via direct REST API calls with `requests` or `urllib`. This limits scalability but reduces dependencies.

### 2. Spot-Futures Basis Spread (Cross-Exchange Spread)

**Rating: IMPLEMENTED BUT LIMITED (5/10)**

**`alpha_engine/event_strategies.py`** -- Strategy #54: `cross_exchange_spread` (lines 769-854):
- Compares Binance spot price (`api.binance.com/api/v3/ticker/price`) vs Binance futures price (`fapi.binance.com/fapi/v1/ticker/price`)
- Calculates basis: `(futures - spot) / spot * 100`
- Signals when `|basis| > 0.15%`:
  - Backwardation (basis < -0.15%): BUY signal (futures cheap)
  - Extreme contango (basis > 0.15%): SELL signal (futures expensive)
- Confidence: `min(0.75, 0.50 + |basis| * 0.15)`
- Covers BTC, ETH, SOL, BNB

**Critical limitation:** This is NOT true cross-exchange arbitrage. Both prices come from Binance (spot vs futures). It is a spot-futures basis trade on a single exchange. No inter-exchange price comparison (e.g., Binance BTC vs Kraken BTC) exists in production code.

### 3. Funding Rate Arbitrage

**Rating: EXCELLENT (9/10) -- Best arbitrage implementation in the codebase**

The funding rate arbitrage is implemented across FOUR separate modules with increasing sophistication:

#### 3a. Alpha Engine Scanner (`alpha_engine/funding_rate_scanner.py`, 584 lines)
- **Live scanner:** Fetches real-time funding rates from Binance FAPI for 10 symbols
- **Signal classification:**
  - Extreme negative (<-0.05%/8h): BUY at 85% confidence
  - Moderate negative (<-0.01%/8h): BUY at 65% confidence
  - Extreme positive (>+0.05%/8h): CAUTION signal
- **TP/SL:** +2%/-1% for extreme, +1.5%/-1% for moderate
- **Backtester included:** Downloads up to 1000 historical funding rate records, simulates entry/exit on 8h klines
- **Sharpe calculation:** Annualized via `sqrt(1095)` (3 intervals/day x 365)
- **Live data output:** `alpha_engine/data/funding_rate_signals.json` -- confirmed active as of 2026-02-24 (2 BUY signals: AVAXUSDT at -0.0145%/8h, XRPUSDT at -0.0136%/8h)

#### 3b. Full Backtest Engine (`funding_arb_backtest.py`, 622 lines)
- **Multi-exchange funding rate fetching:**
  - `fetch_binance_funding()` -- Binance FAPI with pagination
  - `fetch_okx_funding()` -- OKX funding rate history API
  - `fetch_bybit_funding()` -- Bybit v5 funding history with cursor pagination
- **Delta-neutral strategy:** Long spot + short perpetual futures
- **Cost model:** Spot taker 0.1%, futures taker 0.05%
- **Basis risk modeling:** Estimates PnL from basis convergence/divergence
- **Documented results (from `FUNDING_ARB_REPORT.md`):**
  - BTC: 21.04% annualized, Sharpe 18.65, max DD -0.05%
  - ETH: 21.39% annualized, Sharpe 19.01, max DD -0.09%
  - Win rate: >90% of funding periods positive

#### 3c. Extended Analysis (`funding_arb_extended.py`, 286 lines)
- Fetches up to 2 years (730 days) of historical funding data
- Monthly breakdown analysis
- **Cross-exchange comparison function `compare_exchanges()`:**
  - Fetches current Binance premium index
  - Fetches current Bybit funding rate
  - Side-by-side comparison for rate differential identification

#### 3d. ML-Enhanced Pilot (`ml_battleground/pilots/funding_rate_carry.py`, 346 lines)
- **GradientBoosting classifier** trained on historical funding sequences
- **Feature vector:** Last 5 funding rates, funding slope (10-period), 20-period mean, open interest, long/short ratio, 5d/10d price momentum, realized volatility
- **Heuristic fallback** when sklearn unavailable: rule-based scoring of funding trend + L/S ratio + momentum
- **Threshold:** Funding rate >0.01%/8h = profitable carry
- Cross-validated accuracy reported on training

#### 3e. On-Chain Strategy (#43, `alpha_engine/onchain_strategies.py`)
- `funding_rate_arbitrage` -- Market-neutral carry (long spot + short perps)
- References: 19-115% annual documented (Amberdata/ScienceDirect)
- Integrated into the 100-strategy Alpha Engine production scanner

### 4. Statistical Arbitrage / Pairs Trading

**Rating: STRONG (8/10)**

Three separate implementations with increasing rigor:

#### 4a. Ornstein-Uhlenbeck Pairs Trading (`ml_battleground/pilots/ou_pairs_trading.py`, 361 lines)
- **Academically rigorous:** References Huang (2016) -- OU optimal pairs, Sharpe 0.8-2.4
- **5 candidate pairs:** BTC/ETH, ETH/BNB, SOL/AVAX, LINK/DOT, XRP/ADA
- **Cointegration testing:** ADF test with statsmodels fallback to manual implementation
- **OU half-life estimation:** Regresses delta_spread on lagged spread to extract mean reversion speed `theta`, computes `ln(2)/theta`
- **Z-score signals:** Entry at |z| > 2.0, exit at |z| < 0.3, stop-loss at |z| > 3.5
- **Log-price spreads** for stability
- **Output:** `ml_battleground/pilots/data/ou_pairs.json`

#### 4b. Pairs Trading Scanner (`ml_battleground/pairs_trading_scanner.py`, 186 lines)
- Uses **Engle-Granger cointegration test** via `shared/sr_engine.py` (`statsmodels.tsa.stattools.coint`)
- Scans 20 USDT pairs for cointegrated relationships
- **Risk-parity position sizing:** Allocates based on inverse volatility
- **Cost-aware:** Uses `round_trip_cost()` model per symbol
- **Risk management:** Max drawdown checks, trade count limits, 24-hour timeout on positions
- Discord notifications for new signals

#### 4c. Alpha Engine Cointegrated Pairs (`alpha_engine/quant_strategies.py`, Strategy #45)
- References: Springer (2024) -- 79-100% WR in backtests
- OLS regression: `beta = cov(A,B) / var(B)`
- 90-day lookback for spread estimation
- Trades BTC/ETH, SOL/AVAX, LINK/DOT spreads

#### 4d. Engle-Granger Engine (`ml_battleground/shared/sr_engine.py`)
- `find_cointegrated_pairs()`: Tests all N*(N-1)/2 symbol combinations
- Filters: p-value < 0.05 AND |correlation| > 0.6
- Computes spread volatility for position sizing

### 5. Triangular Arbitrage

**Rating: NOT IMPLEMENTED (0/10)**

No triangular arbitrage logic exists in the codebase. There is no:
- Currency loop detection (e.g., BTC->ETH->USDT->BTC)
- Multi-hop routing optimization
- Cross-pair spread calculation

This is unsurprising given the strategy's requirement for sub-second execution and co-located infrastructure, which is incompatible with a GitHub Actions-based pipeline running on 15-30 minute intervals.

### 6. Latency Considerations

**Rating: NOT APPLICABLE FOR CURRENT ARCHITECTURE (2/10)**

The entire system runs on **GitHub Actions** with 15-30 minute scan intervals. This architecture is fundamentally incompatible with latency-sensitive arbitrage:

- **Execution latency:** GitHub Actions cold start + API round-trips = seconds to minutes
- **Rate limiting:** 100-200ms sleep between API calls (by design, to respect rate limits)
- **No WebSocket connections:** All data fetching is REST-based (request-response)
- **No co-location:** No exchange proximity hosting
- **No order execution:** The system generates signals only; no exchange API keys for trading are used in production

**What IS handled well:**
- API timeout management (8-30 second timeouts across modules)
- Retry/failover logic (3-exchange chain in data_fetcher.py)
- Rate limit politeness (0.1-0.2s sleeps between requests)

### 7. Exchange Counterparty Risk Management

**Rating: PARTIAL (4/10)**

**What exists:**
- `funding_arb_backtest.py` (lines 571-598): Explicit risk matrix identifying exchange insolvency as "HIGH" severity risk, with mitigation: "Use multiple exchanges, withdraw frequently"
- `funding_arb_analysis.py` (lines 229-291): Detailed risk assessment table covering exchange insolvency, basis risk, negative funding, execution risk, liquidity risk, regulatory risk
- Multi-exchange data sourcing provides implicit diversification awareness

**What is MISSING:**
- No exchange health monitoring (uptime, withdrawal status)
- No automatic position distribution across exchanges
- No counterparty exposure limits per exchange
- No withdrawal automation or collateral rebalancing
- No exchange insurance fund monitoring (e.g., Binance SAFU)
- No real-time exchange solvency indicators

---

## Summary Scorecard

| Arbitrage Type | Implementation | ML Integration | Production Ready | Score |
|---|---|---|---|---|
| Funding Rate Arb | 4 separate modules, live data | GradientBoosting classifier | YES (running every 30min) | 9/10 |
| Stat Arb / Pairs | 3 implementations, OU + Engle-Granger | Cointegration + Z-score | YES (ml_battleground pilot) | 8/10 |
| Spot-Futures Basis | Binance spot vs futures | Confidence scaling | YES (Alpha Engine strat #54) | 5/10 |
| Multi-Exchange Data | 3-7 exchange failover | N/A | YES (data_fetcher.py) | 7/10 |
| Triangular Arb | Not implemented | N/A | NO | 0/10 |
| Latency Arb | Not applicable | N/A | NO | 0/10 |
| Counterparty Risk | Documentation only | N/A | PARTIAL | 4/10 |

**Overall Arbitrage Capability: 5.5/10**

---

## Actionable Recommendations

### High Priority (Would Significantly Improve Arbitrage Edge)
- [x] Funding rate arbitrage is well-implemented with backtested results (21% annualized)
- [x] Statistical arbitrage (pairs trading) has rigorous OU + Engle-Granger implementations
- [x] Multi-exchange data sourcing covers 3-7 exchanges with failover
- [ ] **ADD true cross-exchange price arbitrage:** Compare BTC price on Binance vs Bybit vs OKX simultaneously (the data fetcher already connects to all three; just add price comparison logic)
- [ ] **ADD CCXT integration:** Would replace 500+ lines of manual exchange API code with a unified interface and add support for 100+ exchanges
- [ ] **ADD funding rate cross-exchange comparison as a strategy:** `funding_arb_extended.py` already has `compare_exchanges()` -- promote this to a production signal (e.g., "Binance funding 0.05%, Bybit funding 0.02% -> carry on Binance, hedge on Bybit")

### Medium Priority
- [ ] **ADD exchange health monitoring:** Ping exchange status endpoints before routing signals
- [ ] **ADD counterparty exposure limits:** Track notional exposure per exchange, cap at configurable threshold
- [ ] **Enhance ML for funding rate prediction:** The GradientBoosting model in `funding_rate_carry.py` should include cross-exchange funding rate differentials as features
- [ ] **ADD WebSocket feeds for basis monitoring:** REST polling every 30 min misses intraday basis spikes

### Low Priority (Require Infrastructure Changes)
- [ ] Triangular arbitrage (requires co-located execution, not feasible on GitHub Actions)
- [ ] Latency arbitrage (requires sub-second execution, incompatible with current architecture)
- [ ] Order execution integration (requires exchange API keys with trade permissions)

---

## Key Files Audited

| File | Purpose | Lines |
|---|---|---|
| `alpha_engine/funding_rate_scanner.py` | Live funding rate scanner + backtester | 584 |
| `alpha_engine/event_strategies.py` | Cross-exchange spread (strat #54) | ~960 |
| `alpha_engine/quant_strategies.py` | Cointegrated pairs (strat #45) | ~300 |
| `alpha_engine/onchain_strategies.py` | Funding rate arbitrage (strat #43) | ~800 |
| `ml_battleground/pairs_trading_scanner.py` | Pairs trading scanner with risk mgmt | 186 |
| `ml_battleground/pilots/ou_pairs_trading.py` | OU process pairs trading | 361 |
| `ml_battleground/pilots/funding_rate_carry.py` | ML-enhanced funding carry | 346 |
| `ml_battleground/shared/data_fetcher.py` | 3-exchange OHLCV fetcher | 164 |
| `ml_battleground/shared/sr_engine.py` | Engle-Granger cointegration engine | ~100 |
| `KIMI_RISEOFTHECLAW/multi_source_fetcher.py` | 7-exchange failover fetcher | ~400 |
| `funding_arb_backtest.py` | Full funding arb backtester (3 exchanges) | 622 |
| `funding_arb_extended.py` | Extended funding analysis + exchange comparison | 286 |
| `funding_arb_analysis.py` | Funding distribution analysis + risk matrix | 297 |
| `alpha_engine/data/funding_rate_signals.json` | Live signal data (last scan: 2026-02-24) | ~158 |

## References (From Codebase)
- Huang (2016): OU optimal pairs trading, Sharpe 0.8-2.4
- Springer (2024): Cointegrated crypto pairs, 79-100% WR
- Gate.io (2025): Funding rate carry, 19-115% annual documented
- Amberdata/ScienceDirect: Funding arb profitability documentation
- Daniel & Moskowitz (2016) JFE: Momentum crash risk (used in momentum_crash_hedge strat #55)
- Keyrock (2024): 16,000 token unlock events analyzed
- Han, Kang & Ryu (2024): Time-series momentum, Sharpe 1.51

---
*Researcher ID: 026* | *Status: Complete* | *Audit Date: 2026-02-24*
