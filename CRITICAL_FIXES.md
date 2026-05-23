# CRITICAL BUGS & SECURITY ISSUES — Action Plan

## 🔴 SEVERITY: CRITICAL (Fix This Week)

### 1. SQL Injection Vulnerability
**File:** [alpha_engine/backtest_justin_bravo.py](alpha_engine/backtest_justin_bravo.py)  
**Line:** 77  
**Current Code:**
```python
query = f"""
    SELECT timestamp, open, high, low, close, volume
    FROM klines
    WHERE pair = '{db_symbol}'  # ⚠️ VULNERABLE
    ORDER BY timestamp DESC
    LIMIT {lookback_days * 288}
"""
df = pd.read_sql(query, conn)
```

**Attack Example:**
```
db_symbol = "BTC/USDT' OR '1'='1'; DROP TABLE klines; --"
# Executes: WHERE pair = 'BTC/USDT' OR '1'='1'; DROP TABLE klines; --'
# Result: Entire klines table deleted
```

**Fix (30 seconds):**
```python
query = f"""
    SELECT timestamp, open, high, low, close, volume
    FROM klines
    WHERE pair = ?
    ORDER BY timestamp DESC
    LIMIT {lookback_days * 288}
"""
df = pd.read_sql(query, conn, params=[db_symbol])
```

**Testing:**
```bash
# Add to test suite
assert sql.execute("SELECT * FROM klines WHERE pair = ?", ["BTC/USDT' OR '1'='1"])
# Should return only BTC/USDT data, not entire table
```

---

### 2. Lookahead Bias in Signal Generation
**File:** [alpha_engine/crypto_smart_picks.py](alpha_engine/crypto_smart_picks.py)  
**Lines:** 15-18  
**Current Code:**
```python
n = len(closes)
i = n - 1  # Last candle (INCOMPLETE)

# Uses incomplete current candle:
trending = closes[i] > ema20[i] and ema20[i] > ema50[i]
momentum = closes[i] > closes[max(0, i - 4)]
```

**Problem:** 
- For 5m candle strategy, `closes[-1]` is the price 4m 59s into the current candle
- Entry signal generated at 4m ago, but uses data not available for another ~1 minute
- In live trading, order fills 1+ minute late at stale price
- Backtest shows 50 bps better entries than reality

**Fix (5 minutes):**
```python
# Use completed candles only
i = n - 2  # Last COMPLETED candle

# Add assertion for signal freshness:
if n < 2:
    return None  # Need at least 2 complete candles

# Or split incoming data:
completed_closes = closes[:-1]  # All finished candles
unfinished_close = closes[-1]   # Current progress (for monitoring only)

# Compute features on completed data:
ema20 = ema(completed_closes, 20)
rsi14 = rsi(completed_closes, 14)

# Use last completed values:
trending = completed_closes[-1] > ema20[-1]
```

**Validation:**
```python
# Backtest should show 10-30% lower returns when using close[i] vs close[i-1]
# If difference is <5%, lookahead bias is minimal; if >50%, definitely present
```

---

### 3. ATR Vectorization Bug
**File:** [alpha_engine/indicators.py](alpha_engine/indicators.py)  
**Current Code:**
```python
def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14):
    # ... compute plus_dm, minus_dm ...
    tr = max(high - low, abs(high - close.shift()), abs(low - close.shift()))  # ⚠️ WRONG
    # Python max() on Series only compares indices, not elements
```

**Impact:**
- ATR returns scalar instead of Series
- All downstream volatility calculations (tp_dist, sl_dist) become NaN or wrong
- Position sizing fails silently

**Fix (2 minutes):**
```python
def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14):
    tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
    # Now tr is a Series of per-candle true ranges
    return tr.rolling(window=period).mean()
```

**Test:**
```python
# Should return Series of same length as input
assert len(atr) == len(close)
assert atr.dtype == float
assert atr[-1] > 0  # ATR should be positive
```

---

### 4. Silent Empty DataFrame Returns
**Files:** 
- [alpha_engine/backtest_justin_bravo.py](alpha_engine/backtest_justin_bravo.py#84-90)
- [alpha_engine/advanced_strategies.py](alpha_engine/advanced_strategies.py)

**Current Code:**
```python
try:
    conn = sqlite3.connect(self.data_source)
    query = f"SELECT ... FROM klines WHERE pair = '{db_symbol}' ..."
    df = pd.read_sql(query, conn)
except Exception as e:
    print(f"Error loading {symbol}: {e}")  # ⚠️ SILENT SWALLOW
    return pd.DataFrame()  # Returns empty DF, no stacktrace
```

**What Happens:**
1. Network timeout → empty DataFrame
2. Callers process empty DF → NaN features
3. Model sees all-NaN signals → predicts 0.5 confidence
4. Positions open at random times
5. No alert to ops team

**Fix (10 minutes):**
```python
import logging
logger = logging.getLogger(__name__)

def load_crypto_data(self, symbol: str) -> pd.DataFrame:
    try:
        # ... connect & query ...
        if df.empty:
            logger.error(f"Query returned 0 rows for {symbol}. DB may be down.")
            # Option 1: raise exception (preferred)
            raise ValueError(f"No data for {symbol}")
            # Option 2: return last cached data
            # Option 3: email alert + pause trading
    except Exception as e:
        logger.exception(f"Failed to load {symbol}: {e}")  # Full stacktrace
        if "Timeout" in str(e) or "refused" in str(e):
            logger.critical(f"Database unavailable; halting strategy {strategy_name}")
            # Trigger alert/circuit-breaker
            raise
        raise  # Don't silently swallow
    
    return df
```

---

## 🟡 SEVERITY: HIGH (Fix This Sprint)

### 5. NaN/Missing Value Handling
**Files:** ab_test_portfolios.py, advanced_strategies.py

**Current Code:**
```python
all_returns[symbol] = df["Close"].pct_change().dropna()
returns_df = returns_df.fillna(0.0)  # ⚠️ Fills missing as zero return
```

**Problem:**
- `fillna(0.0)` treats missing data as zero return (artificial stability)
- `dropna()` silently removes rows (what gets removed? Why?)
- Correlation matrix becomes biased (zero returns = "stable")

**Fix:**
```python
def safe_returns(df: pd.DataFrame, min_periods: int = 50) -> pd.Series:
    """Compute returns with validation."""
    returns = df["Close"].pct_change()
    
    # Count missing
    n_missing = returns.isna().sum()
    n_total = len(returns)
    pct_missing = n_missing / n_total * 100
    
    if n_missing > 0:
        logger.warning(f"{n_missing} missing returns ({pct_missing:.1f}%)")
    
    if n_total - n_missing < min_periods:
        raise ValueError(f"Only {n_total - n_missing} non-missing returns (need {min_periods})")
    
    # Forward-fill up to 2 periods, then drop remaining NaN
    returns = returns.fillna(method='ffill', limit=2).dropna()
    
    return returns
```

---

### 6. Synergy & Confluence Overfitting
**File:** [alpha_engine/confluence_engine.py](alpha_engine/confluence_engine.py)  
**Lines:** 80-95

**Current Code:**
```python
SYMBOL_STRATEGY_GOLDEN = {
    ("TONUSDT", "variance_ratio_momentum"): 1.40,  # 5wins/0losses = 100% WR
    ("EURUSD=X", "spike_macd_divergence"): 1.30,   # 2wins/0losses = 100% WR
}
```

**Problem:**
- 5 trades = sample size too small (στ_WR ≈ ±40%)
- Data is in-sample (used for strategy development)
- Confidence boosting based on noise = overfitting
- Live trading: 100% backtest WR → 40% live WR

**Fix:**
```python
# Only keep synergies with sufficient out-of-sample data
SYNERGY_PAIRS_VALIDATED = {
    frozenset({"variance_ratio_momentum", "fear_greed_extreme_dca"}): {
        "boost": 1.35,
        "n_trades": 247,  # ✅ Large sample
        "oos_wr": 0.68,   # ✅ Out-of-sample validation
        "live_wr": 0.64,  # ✅ Real money confirmation
        "confidence": 0.95
    },
    frozenset({"spike_volume_explosion", "variance_ratio_momentum"}): {
        "boost": 0.60,
        "n_trades": 42,   # ⚠️ Small, suppress
        "confidence": 0.65  # Low confidence
    }
}

# Apply boost only if confidence high & recent trades available:
def get_synergy_boost(strats: list[str], symbol: str) -> float:
    pair = frozenset(strats)
    if pair not in SYNERGY_PAIRS_VALIDATED:
        return 1.0
    
    config = SYNERGY_PAIRS_VALIDATED[pair]
    
    # Require recent data (last 14 days)
    symbol_strat_history = get_trade_history(symbol, strats, days=14)
    if len(symbol_strat_history) < 3:
        logger.warning(f"Insufficient recent data for {pair} + {symbol}; no boost")
        return 1.0
    
    # Check confidence threshold
    if config["confidence"] < 0.75:
        logger.warning(f"Low confidence synergy {pair}; reducing boost")
        return 1.0 + (config["boost"] - 1.0) * 0.5  # Half the boost
    
    return config["boost"]
```

---

## 🟢 SEVERITY: MEDIUM (Do Next Month)

### 7. Configurable Thresholds
Move hard-coded values to config:
```python
# BEFORE:
if confidence < 0.70:
    return None
if rr < 1.0 or rr >= 2.0:
    return None

# AFTER:
CONFIDENCE_MIN = float(os.getenv('CONF_MIN', 0.70))
RR_MIN = float(os.getenv('RR_MIN', 1.0))
RR_MAX = float(os.getenv('RR_MAX', 2.0))

if confidence < CONFIDENCE_MIN:
    return None
if rr < RR_MIN or rr > RR_MAX:
    return None
```

### 8. Data Freshness Checks
```python
# Add to all data loading functions:
df_age = pd.Timestamp.utcnow() - df.index[-1]
if df_age > pd.Timedelta(hours=1):
    logger.error(f"Data is {df_age} old; refusing to trade")
    raise ValueError("Stale data")
```

### 9. Rate Limit Backoff
```python
# api_failover.py
import time
import random

def _fetch_with_retry(url, max_retries=3):
    for attempt in range(max_retries):
        try:
            return requests.get(url, timeout=10)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:  # Too many requests
                wait = min(2 ** attempt + random.uniform(0, 1), 60)
                logger.warning(f"Rate limited; backoff {wait:.1f}s")
                time.sleep(wait)
            else:
                raise
```

---

## Testing Checklist

- [ ] SQL injection: `exec("WHERE pair = 'x' OR '1'='1'")` should not delete data
- [ ] Lookahead: Backtest with `close[i-1]` should show 5-30% lower returns
- [ ] ATR: `len(atr(high, low, close)) == len(close)`
- [ ] Empty data: Exceptions raised, not silent returns
- [ ] Missing values: Logged with clear percentage
- [ ] Synergies: Only `n_trades >= 50` applied; < 50 → 0.5x boost
- [ ] Data freshness: Errors if data older than 1h

---

## Deployment Order

1. **Day 1 (Monday):** SQL injection + silent errors (stop data loss)
2. **Day 2 (Tuesday):** Lookahead bias + ATR fix (improve signal quality)
3. **Day 3 (Wednesday):** Missing value handling + validation (improve robustness)
4. **Week 2:** Synergy overfitting + config externalization (improve generalization)

---

**Report Date:** April 12, 2026  
**Estimated Fix Time:** 4-6 hours total  
**Risk of Delay:** High (especially SQL injection + lookahead bias)
