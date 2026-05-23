# Full System Audit: Crypto Prediction Platform
**Inspected:** `/audit/`, `/alpha/`, `/battleground/` + full codebase | **Date:** 3/6/2026

---

## 🏗️ Complete System Architecture

### Data Flow Pipeline
```
Alpha Engine (114 strategies)  →┐
Paper Trading scanner          →│  JSON files (local)     →┐
Battleground / Incubator       →│  SQLite DBs (local)     →│→ ejaguiar1_stocks MySQL (mysql.50webs.com)
Baby Bundles / DNA Combos      →│  at_raw_picks           │→ /audit/index.html (PHP-generated)
Coinglass / external feeds     →┘  at_signal_outcomes     └→ findtorontoevents.ca/audit/
```

**Key MySQL tables in `ejaguiar1_stocks`:**
- `at_raw_picks` — every signal from every system
- `at_signal_outcomes` — forward trade results (wins/losses)
- `bt_backtest_trades` — historical backtest trades from SQLite imports
- `strategy_registry` — master strategy catalog
- `at_strategy_symbol_performance` — per-strategy × per-symbol stats
- `at_discord_sent` — what was pushed to Discord

**Three Prediction Engines:**

| Engine | Status | Win Rate | Trade Count |
|---|---|---|---|
| **Battleground** (Superpowers Arena) | 🟢 BEST — 64.1% WR, +1357% PnL | Proven survivors avg 63.7% | 334 closed |
| **Alpha Engine** (`/alpha/`) | 🟡 OK — positive PnL in $USD | 35.9% WR but positive $ (avg 12.2% per win) | 156 closed |
| **Baby Strats Forward** (RETIRED) | 🔴 DESTROYED pipeline | 41.8% WR | 1975 closed, -5433% PnL |

---

## 📊 Active Picks Quality Analysis (Current 831 Picks)

### Current Open Positions (Battleground, as of 3/6/2026 ~6PM EST)

| Strategy | Symbol | Dir | Entry | TP | SL | PNL% | R:R | Bundle |
|---|---|---|---|---|---|---|---|---|
| crypto_keltner_compression_exp_v1 | BTCUSDT | SHORT | $68,350 | $67,028 | $69,097 | -0.11% | 1.9:1 | Volume-Confirmed Breakout |
| keltner_compression_exp_eth_v1 | ETHUSDT | SHORT | $1,984 | $1,934 | $2,012 | -0.16% | 1.8:1 | — |
| keltner_compression_exp_sol_v1 | SOLUSDT | SHORT | $84.70 | $82.26 | $85.83 | -0.33% | 2.1:1 | — |
| funding_momentum | BTCUSDT | SHORT | $68,350 | $66,575 | $69,533 | -0.11% | 1.4:1 | Funding Rate Momentum |
| atr_regime_rsi | BTCUSDT | LONG | $68,350 | $69,533 | $67,462 | +0.11% | 1.0:1 | Proven Winners |
| drawdown_recovery_rsi | BTCUSDT | LONG | $68,350 | $69,533 | $67,462 | +0.11% | 1.0:1 | Proven Winners |
| multi_period_rsi_confluence BTC | BTCUSDT | LONG | $68,350 | $69,533 | $67,462 | +0.11% | 1.0:1 | Proven Winners |
| multi_period_rsi_confluence XRPUSDT | XRPUSDT | LONG | $1.36 | $1.39 | $1.35 | +0.74% | 3.0:1 | — |

### ⚠️ Active Pick Quality Issues

**Issue 1 — Conflicting signals on same asset (no net-exposure logic):**
BTCUSDT has 3 LONG positions AND 2 SHORT positions open simultaneously from different strategies.
These self-cancel P&L and waste commission. The `cross_aggregation/freshpicks_gate.py` has gate
logic but it's not blocking direction conflicts at the portfolio level.

**Issue 2 — Weak R:R on Proven Winners LONG picks:**
- `atr_regime_rsi` LONG BTC: +1.73% TP, -1.30% SL = R:R 1.33:1 — barely positive at <57% WR
- The "Proven Winners (Long Only)" bundle FWD-tested at 62.4% WR, so net positive, but tight R:R
  means any slippage kills the edge

**Issue 3 — Missing indicator context in pick display:**
The `/audit/` Active Picks table shows: SYMBOL, DIR, ASSET, SYSTEM, STRATEGY, ENTRY, TP, SL
but is missing critical entry quality info:
- Current RSI (1h) — overbought/oversold at entry?
- HMA slope — trend with or against the pick?
- Volume confirmation — did volume expand at entry?
- Strategy "last 10" win rate — is this strategy in a hot/cold streak?
- Current PNL% — visible on Battleground but **missing from the /audit/ table**

**Issue 4 — NEAR-USD SHORT (alpha engine, `profit taking reentry`):**
- Entry $1.23, TP $0.73, SL $1.46 = 40.7% downside target, 18.7% upside risk
- Extremely wide stop, no visible context for why this was entered
- Typical of the -430% PnL drag from the alpha engine

---

## 🧬 Battleground Pipeline Deep Dive

### Pipeline Stages (confirmed from `bundle_baby_system.py` + UI)

```
PASSED  = Backtest passed 8 anti-overfit checks:
            - 24 symbols (crypto + equity + forex)
            - 5yr daily data
            - Walk-forward OOS validation
            - Regime robustness
            - Binomial p < 0.05
            - Both-halves consistency

PAPER   = 30-day forward paper test (out-of-sample)

GRADUATED = Paper test passed → Ready for live

Baby Bundle = Multiple GRADUATED strategies combined:
  - multi_symbol | multi_timeframe | direction_bias
  - Consensus signal required (2+ strategies agree)
```

### DNA System
**623 active combos** = genetic search over the 10 proven survivors' parameters. Each "DNA combo"
is a parameter mutation of an existing survivor that runs through the full PASSED → PAPER → GRADUATED
pipeline automatically.

### The 10 Survivor Strategies — Backtest Performance

| # | Strategy | Trades | Win Rate | Sharpe | Source |
|---|---|---|---|---|---|
| 1 | **Keltner Mean Rev** | 111 | **67.6%** | **2.06** ⭐ | Keltner 1960 / Raschke |
| 2 | **Connors R3** | 803 | **71.4%** | 1.53 | Connors & Alvarez 2008 |
| 3 | **Connors RSI-2** | 895 | **68.4%** | 1.17 | Connors & Alvarez 2008 |
| 4 | Supertrend ATR | 34 | 52.9% | 1.18 | Trend following |
| 5 | Bollinger Mean Rev | 361 | 60.7% | 0.72 | Bollinger 1980s |
| 6 | RSI Extreme Rev | 118 | 58.5% | 0.70 | Wilder 1978 |
| 7 | **MACD Divergence** | 515 | **67.8%** | 0.57 | Appel 1979 |
| 8 | VWAP Mean Rev | 732 | 64.3% | 0.53 | VWAP z-score |
| 9 | Williams %R | 475 | 59.8% | 0.39 | Larry Williams 1979 |
| 10 | Vol-Scaled Momentum | 568 | 65.8% | 0.32 | Moreira & Muir 2017 JFE |

**Baby Bundle "Proven Winners (Long Only)":** 117 forward trades, **62.4% WR, +56.56% realized PnL** ✅

---

## 🔧 Secondary Indicators — What to Add

**Currently in `alpha_engine/indicators.py`:**
`sma`, `ema`, `vwma`, `ichimoku`, `rsi`, `stoch_rsi`, `macd`, `adx`, `atr`, `bollinger_bands`,
`zscore`, `vwap_session`, `hurst_exponent`, `obv`

**Missing — high-value additions:**

### 1. Hull Moving Average (HMA) — Highest Priority

```python
def hma(series: pd.Series, period: int) -> pd.Series:
    """Hull Moving Average (Alan Hull 2005) — lag-reduced trend direction."""
    wma1 = series.ewm(span=period//2, adjust=False).mean() * 2
    wma2 = series.ewm(span=period, adjust=False).mean()
    raw = wma1 - wma2
    sqrt_n = int(period**0.5)
    return raw.ewm(span=sqrt_n, adjust=False).mean()

def hma_slope(series: pd.Series, period: int = 21) -> pd.Series:
    """Returns +1 (uptrend), -1 (downtrend), 0 (flat) for trend filter."""
    h = hma(series, period)
    return np.sign(h.diff())
```

Use as: take LONG only when `hma_slope > 0`, SHORT only when `hma_slope < 0`.

### 2. Multi-Timeframe RSI Alignment Filter

```python
# Require 1h AND 4h RSI to agree before entry
rsi_1h = rsi(close_1h, 14).iloc[-1]
rsi_4h = rsi(close_4h, 14).iloc[-1]

if signal == 'LONG' and not (rsi_1h > 45 and rsi_4h > 45):
    continue  # reject counter-trend signal
if signal == 'SHORT' and not (rsi_1h < 55 and rsi_4h < 55):
    continue
```

### 3. Volume Expansion Confirmation

```python
current_vol = df['volume'].iloc[-1]
avg_vol_20 = df['volume'].tail(20).mean()
vol_ratio = current_vol / avg_vol_20
if vol_ratio < 1.2:
    continue  # No volume = no conviction
```

### 4. ATR-Scaled TP/SL (replace fixed % TPs)

```python
atr_val = atr(high, low, close, 14).iloc[-1]
if signal == 'LONG':
    take_profit = entry + 2.5 * atr_val
    stop_loss   = entry - 1.5 * atr_val   # R:R always 1.67:1
elif signal == 'SHORT':
    take_profit = entry - 2.5 * atr_val
    stop_loss   = entry + 1.5 * atr_val
```

This fixes the current problem where BTC's TP is only 0.59 ATR away from entry — volatile days blast
through the TP before the genuine move completes, turning winners into scratches.

---

## 🚀 Backtest Ideas for the DNA Pipeline

### Idea 1 — Keltner Mean Rev + HMA Filter (DNA Mutation)
- **Base:** Keltner Mean Rev (Sharpe 2.06, best performer)
- **Mutation:** `hma_slope_filter = True` — only enter in trend direction
- **Expected:** Fewer trades, target WR improvement from 67.6% → 72%+

### Idea 2 — Connors R3 × RSI Extreme Rev Combo Bundle
- Both are proven survivors with complementary signals
- Require **both to fire simultaneously** on the same symbol
- Expected: Lower frequency, target >75% WR

### Idea 3 — MACD Divergence + Volume Expansion Filter
- MACD Divergence: 67.8% WR, Sharpe only 0.57 (good WR, exits at wrong time)
- Add: `volume_ratio >= 1.3` on the MACD divergence bar
- Should improve Sharpe by filtering low-conviction signals

### Idea 4 — Autocorrelation Exploiter → Battleground Incubation
- **Alpha engine forward stats:** 5W/1L (83% WR), avg +12.2% per trade, +$1,459 PnL
- Currently not in the Battleground's 10 survivors (no backtest validation)
- **Action:** Run `alpha_engine/statistical_strategies.py` `autocorrelation_exploiter` through
  the full 8-check backtest pipeline. If passes → promote to Baby Strat → DNA expansion.

### Idea 5 — Multi-Sigma Reversal → Battleground Incubation
- Alpha forward stats: 3W/0L (100%), avg +10.9%, +$656 PnL
- Statistical mean reversion — strong academic backing
- Same action: push through incubator pipeline

### Idea 6 — Funding Momentum SHORT + RSI Overbought Gate
- Current: `funding_momentum` fires on any positive funding rate (no price confirmation)
- Enhancement: `rsi_4h >= 65` required as overbought confirmation
- Prevents shorting into already-declining price where funding is high but momentum is down

---

## 📱 Dashboard Feature Enhancements

### A. Add These Columns to Active Picks Table in `/audit/`

Add to `at_raw_picks` MySQL schema:
```sql
ALTER TABLE at_raw_picks 
  ADD COLUMN rsi_1h DECIMAL(5,2),
  ADD COLUMN hma_slope TINYINT,          -- +1, 0, -1
  ADD COLUMN volume_ratio DECIMAL(5,2),
  ADD COLUMN pnl_pct_current DECIMAL(8,4),
  ADD COLUMN hours_open INT,
  ADD COLUMN strategy_last10_wr DECIMAL(5,2);
```

| Column | Description |
|---|---|
| **Current PNL%** | Missing from `/audit/` (shown on Battleground but not Audit) |
| **RSI 1h** | Entry momentum: 🔴 <30 or >70 = extreme; 🟡 moderate |
| **HMA Slope** | 🟢 aligned / 🔴 opposing pick direction |
| **Age (hrs)** | How long the pick has been open |
| **Dist. to SL%** | How close to being stopped |
| **Last 10 WR** | Strategy recent form (rolling window) |

### B. "Recent Performance" Rolling Window on Leaderboard

```
keltner_compression_expansion_v1
  ✅ All-time:  64.1% WR (334 trades)     +1357% PnL
  🟡 Last 30d:  58.3% WR (24 trades)      — Slight decay
  🔴 Last 10:   40.0% WR (10 trades)      ⚠️ REGIME ALERT — consider pausing
```

Query against `at_signal_outcomes`:
```sql
SELECT 
  strategy_name,
  AVG(CASE WHEN pnl_pct > 0 THEN 1.0 ELSE 0.0 END) as last10_wr
FROM (
  SELECT * FROM at_signal_outcomes 
  WHERE strategy_name = ? 
  ORDER BY exit_time DESC LIMIT 10
) recent;
```

### C. Asset-Specific Strategy Performance View

Filter the Leaderboard by asset (e.g. "How does Keltner Mean Rev perform on BTCUSDT specifically?"):
```sql
SELECT symbol, COUNT(*) as trades,
       AVG(CASE WHEN pnl_pct > 0 THEN 1.0 ELSE 0.0 END) as win_rate,
       SUM(pnl_pct) as total_pnl
FROM at_signal_outcomes
WHERE strategy_name = 'keltner_mean_rev'
GROUP BY symbol ORDER BY win_rate DESC;
```

### D. Conflict Detection Banner

On Active Picks table, highlight conflicting directions:
```
⚠️ BTCUSDT: [LONG × 3] vs [SHORT × 2] — NET NEUTRAL — 5 systems conflicting
```

### E. Strategy Health Score

Computed badge: 🟢 HEALTHY / 🟡 WATCH / 🔴 DEGRADED

Score inputs:
- Forward decay vs backtest: 30%
- Last 10 WR vs lifetime WR: 30%
- Days since last profitable trade: 20%
- Volume of recent activity: 20%

---

