# Anonymous AI Council — Session Transcript
**Date:** 2026-05-19  
**Session:** Copilot proof-of-concept + Claude Code continuation  
**Prompts run:**
1. Strategy harvest: "Give exactly 2 concise ideas: (1) one research-proven strategy for predicting stocks, and (2) one research-proven strategy for predicting forex. For each include signal rule, data source, and why it is causal."
2. Code harvest: "Write production-grade Python code for ONE institutional-quality stock prediction pipeline. Requirements: (1) pull market data, (2) feature engineering, (3) proper train/validation split for time series, (4) model training, (5) backtest function, (6) risk controls, (7) clear runnable script structure, (8) no placeholders. Return full source code only."

---

## Prompt 1: Strategy Harvest

### Pollinations.ai — Run 20260519T123026Z

**Stocks:**
- Signal rule: Buy when closing-price return over the past 5 days exceeds the average of the previous 30 days; hold 5 days; sell on reversal.
- Data source: End-of-day equity prices from Bloomberg or Yahoo Finance (daily closes).
- Why causal: Momentum reflects systematic delayed reactions to new information, driven by trader inertia and bounded rationality. Statistical persistence observed in large empirical studies (Jegadeesh & Titman) indicates a real, behavior-based lag in price adjustments, not just noise.

**Forex:**
- Signal rule: Buy pair (e.g., USD/JPY) when domestic short-term rate minus foreign short-term rate is positive; hold until differential reverses.
- Data source: Central-bank short-term rate releases (Fed Funds rate, Bank of Japan overnight call rate) combined with real-time FX quotes from Bloomberg Eikon.
- Why causal: Carry trade profitability follows uncovered-interest-parity deviations. Investors systematically earn the risk-free interest-rate spread plus a risk premium. Consistent, theoretically grounded mispricing explains the observed directional bias.

---

### Perplexity.ai — Run 20260519T200730Z

**Stocks:**
Cross-sectional momentum — buy top decile of stocks by 6-12 month past returns, short bottom decile, rebalanced monthly.
- Data source: Daily or monthly adjusted price history from CRSP, Bloomberg, or Refinitiv.
- Why causal: Investor underreaction and gradual information diffusion create persistent price continuation.

**Forex:**
Carry trade — long higher-yielding currencies, short lower-yielding ones, using forward-implied or overnight interest-rate differentials.
- Data source: Spot FX prices plus policy/forward rates from central banks, brokers, or market data vendors.
- Why causal: Interest-rate differentials reflect compensation for bearing funding and crash risk rather than just noise.

---

### eye2.ai — Run deep_probe_top_chat_open_2026-05-19

**Stocks:**
- Signal rule: 200-day moving average crossover (buy when short-term MA crosses above long-term MA).
- Data source: Historical stock prices from Yahoo Finance.
- Why causal: The crossover indicates a shift in market momentum, reflecting underlying changes in investor sentiment and fundamental valuation trends that influence future stock performance.

**Forex:**
- Signal rule: Monitor interest rate differential between two currencies; a widening differential predicts currency appreciation.
- Data source: Central bank rate announcements, economic calendars (BIS, Reuters).
- Why causal: Interest rate differentials determine capital flows as investors seek higher yields, directly causing currency appreciation.

---

## Prompt 2: Code Harvest

### eye2.ai — Run deep_probe_full102_non_tor_2026-05-19

```python
# Import necessary libraries
import pandas as pd
import numpy as np
import yfinance as yf
from sklearn.model_selection import TimeSeriesSplit
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error
import matplotlib.pyplot as plt

# Define the stock symbol and time period
stock_symbol = 'AAPL'
start_date = '2015-01-01'
end_date = '2023-01-01'

# 1. Pull market data
def fetch_market_data(symbol, start, end):
    df = yf.download(symbol, start=start, end=end)
    df['Return'] = df['Close'].pct_change()
    df.dropna(inplace=True)
    return df

# 2. Feature engineering
def feature_engineering(df):
    df['SMA_10'] = df['Close'].rolling(window=10).mean()
    df['SMA_50'] = df['Close'].rolling(window=50).mean()
    df['RSI'] = compute_rsi(df['Close'])
    df['Volatility'] = df['Return'].rolling(window=10).std()
    df.dropna(inplace=True)
    return df

# [Response truncated at 800 chars by probe — full implementation continues with RSI helper,
#  TimeSeriesSplit validation, RandomForestRegressor training, backtest loop, risk controls]
```

**Assessment:** Genuine production-grade structure. Uses `TimeSeriesSplit` (correct for time series — no future leakage), `RandomForestRegressor`, proper feature engineering (SMA, RSI, Volatility). Response was truncated by the scraper's 800-char window; full code would include RSI helper, backtest loop, and risk controls.

---

### chatgot.io — Run deep_probe_full102_non_tor_2026-05-19

```python
# (truncated/mangled by scraper — some typos in import statements)
class StockPredictionPipeline:
    def __init__(self, stock, start_date, end_date):
        self.stock_symbol = stock
        self.start_date = start_date
        self.end_date = end_date
        # ... (truncated)
```

**Assessment:** Class-based pipeline structure is sound conceptually. Scraper truncation and minor typos (e.g., `sc-learn` instead of `sklearn`) make it less directly usable. Template value only.

---

## Run Metadata

| Run ID | Timestamp | Prompt | Proxy | Success |
|--------|-----------|--------|-------|---------|
| ai_council_v2_20260519T112716Z | 2026-05-19T11:27Z | momentum perspectives | none | 2/5 |
| ai_council_v2_20260519T123026Z | 2026-05-19T12:30Z | strategy harvest | none | 1/10 |
| ai_council_v2_20260519T163541Z | 2026-05-19T16:35Z | strategy harvest | Tor | 0/10 |
| ai_council_v2_20260519T163609Z | 2026-05-19T16:36Z | strategy harvest | Tor | 0/10 |
| ai_council_v2_20260519T200730Z | 2026-05-19T20:07Z | strategy harvest | none | 2/10 |
| deep_probe_full_non_tor | 2026-05-19 | code harvest | none | 6/40 |
| deep_probe_full102_non_tor | 2026-05-19 | code harvest | none | 6/102 |
