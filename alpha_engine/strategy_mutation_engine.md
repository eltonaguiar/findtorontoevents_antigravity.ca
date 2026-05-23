# Strategy Mutation Engine

Live system: runs every 30min, mutates underperforming strategies based on forward perf.

## (A) MUTATION ALGORITHM

**Genome Representation** (JSON-serializable dict):
```python
strategy_genome = {
    "name": "rsi_whale_v2",
    "entry_conditions": [  # list of logic blocks
        {"type": "rsi", "period":14, "threshold":30, "direction":"<"},
        {"type": "volume_spike", "mult":5.0, "timeframe":"4h"}
    ],
    "exit_conditions": [
        {"type": "tp_pct", "pct":20.0},
        {"type": "sl_pct", "pct":-10.0}
    ],
    "family": "momentum",
    "params": {"atr_mult":2.0}  # strategy-specific
}
```

**Mutations** (guided by top-performers):
1. **Parameter Jitter**: For params in top strats, jitter ±10-20% (e.g., rsi_th=30 → 27-33)
2. **Logic Insertion**: Add condition from top strat (e.g., add whale_vol to RSI)
3. **Crossover**: 
   - Parent A (top perf): entry_logic
   - Parent B (complementary family): exit_logic
   ```python
   def crossover(parent_a, parent_b):
       child = parent_a.copy()
       child["entry_conditions"] = parent_a["entry_conditions"]
       child["exit_conditions"] = parent_b["exit_conditions"]
       child["name"] = f"{parent_a['name']}_x_{parent_b['name']}"
       return child
   ```
4. **Family Swap**: Change family bias (momentum → volatility)

**Generation**: 10 mutations per cycle from top 5 parents.

## (B) 5 NOVEL STRATEGIES

### 1. Order Flow Imbalance
**Entry**: Bid volume > Ask vol 3:1 on 5m + price > VWAP
**Exit**: TP 1.5%, SL -0.8%, trail after 0.5%
**WR Est**: 62% (imbalance precedes moves)
**Why**: Institutions accumulate quietly.
```python
def orderflow_imbalance(df):
    bid_vol = df['bid_volume'].iloc[-1]  # from orderbook API
    ask_vol = df['ask_volume'].iloc[-1]
    vwap = ta.vwap(df['hlc3'])
    if bid_vol / ask_vol > 3 and df['close'] > vwap.iloc[-1]:
        return {"signal":"LONG", "sl":-0.008, "tp":0.015}
```

### 2. Liquidation Cascade Detection
**Entry**: Long liq > $10M in 15m + price bounce off liq level
**Exit**: TP 5%, SL -2%
**WR**: 68% (capitulation bottoms)
**Why**: Cascades create oversold bounces.
```python
def liq_cascade(df, liq_data):
    recent_liq = sum(liq_data['long_liq'][-4:])  # 15m bars
    if recent_liq > 10e6 and df['low'].iloc[-1] <= liq_data['liq_price']:
        return {"signal":"LONG"}
```

### 3. Cross-Exchange Price Divergence
**Entry**: Binance price - Bybit price > 0.3% (arb opp)
**Exit**: Close when div < 0.1%
**WR**: 72% (stat arb)
**Why**: Slow arb in perps.
```python
prices = fetch_exchanges(["binance", "bybit"])
div_pct = (prices['binance'] - prices['bybit']) / prices['bybit']
if abs(div_pct) > 0.003:
    side = "BUY" if div_pct > 0 else "SELL"
```

### 4. Mempool/Funding Arb
**Entry**: Funding rate >0.1% + mempool tx count spike (whale tx pending)
**Exit**: TP funding neutral
**WR**: 65%
**Why**: Funding paid to contrarians.
```python
funding = get_funding_rate()
mempool_tx = get_mempool_count()
if funding > 0.001 and mempool_tx > mempool_tx.rolling(24).mean() * 2:
    return "SHORT"  # high funding = shorts pay longs
```

### 5. Smart Money vs Retail Divergence
**Entry**: Whale buys (CEX inflow <0) while retail sells (social sentiment negative)
**Exit**: TP 8%, SL -4%
**WR**: 64%
**Why**: Smart money accumulates on retail fear.
```python
whale_flow = get_cex_netflow()  # negative = accumulation
retail_sent = get_lunar_crush_bearish()
if whale_flow < 0 and retail_sent > 0.6:
    return "LONG"
```

## (C) FITNESS FUNCTION
```
fitness = (sharpe * 0.4) + (win_rate * 0.3) + (pf * 0.2) - decay_penalty - overfitting_penalty
where:
decay_penalty = max(0, (backtest_sharpe - forward_sharpe) / backtest_sharpe * 0.5)
overfit_penalty = max(0, 1 - trades/50) * 0.2  # min 50 trades
regime_consistency = std(sharpe across regimes) < 0.3 ? +0.1 : -0.2
Require: trades >=20, decay <20%, regime_std <0.3
```

**Code**:
```python
def fitness(stats, backtest_stats):
    if stats['trades'] < 20: return -1.0
    decay = max(0, (backtest_stats['sharpe'] - stats['sharpe']) / backtest_stats['sharpe'])
    overfit = max(0, 1 - stats['trades']/50)
    regime_std = stats['regime_sharpes'].std()
    cons = 0.1 if regime_std < 0.3 else -0.2
    return (stats['sharpe']*0.4 + stats['wr']*0.3 + stats['pf']*0.2 
            - decay*0.5 - overfit*0.2 + cons)
```

## (D) AUTO-KILL CRITERIA
- After 10 trades: WR<0.45 → kill
- After 20 trades: PF<1.0 or sharpe<0.2 → kill
- After 50 trades: decay>25% → kill
- "Needs data": trades<10 → continue
- Distinguish: if trades<10 and recent_pnl>0 → keep

**Code**:
```python
def should_kill(stats):
    trades = stats['trades']
    if trades < 10: return False  # needs data
    if stats['wr'] < 0.45: return True
    if trades >= 20 and (stats['pf'] < 1.0 or stats['sharpe'] < 0.2): return True
    return False
```

**Integration**: Cron every 30min: mutate → backtest → forward_sim → deploy top3 mutations.
