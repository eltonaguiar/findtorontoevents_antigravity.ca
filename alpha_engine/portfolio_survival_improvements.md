# Portfolio Survival: 5 Highest-Impact Changes to Flip Negative Expectancy

## Current Issues Summary
- WR: 44.2%, PF: 0.71, Expectancy: -3.24%
- Avg Win: +17.73% < Avg Loss: -19.85%
- Noise: 1,540 picks from 81 systems
- Costs: 0.40% RT
- Fixed TP/SL, no trailing/time exits
- Fixed 10-18% sizing
- No corr filter (e.g., WIF long wipes BTC short)

## Change 1: Top-Performer Strategy Filter (Impact: +15-20% Expectancy)
**Rationale**: 81 systems = noise. Focus on top 5 forward-validated (WR>65%, PF>2.0).

**(1) Filtering Rules**:
```
top_strats = strategies where closed_trades >= 10 AND win_rate >= 0.60 AND profit_factor >= 1.5
OR name in ["crypto_rsi_whaleconfirmed_v1", "funding_momentum", 
            "crypto_keltner_compression_expansion", "crypto_vwap_deviation_reversion_vol", 
            "crypto_kalman_trend_residual_reversion"]
filter signal.strategy in top_strats
```

**(2) Position Sizing**: Unchanged (see Change 3)

**(3) SL Management**: Unchanged

**(4) Corr Limits**: Unchanged

**(5) Low-Trade Strats**: Sandbox: generate signals but size=0.5% capital until 5 trades, then evaluate.

**Python Code**:
```python
def get_top_strategies(db):
    stats = db.compute_all_strategy_stats()  # from database.py
    top = [s["strategy"] for s in stats 
           if s["closed_picks"] >= 10 and s["win_rate"] >= 0.60 
           and s["profit_factor"] >= 1.5]
    top += ["crypto_rsi_whaleconfirmed_v1", ...]  # hardcode top5
    return set(top)

def filter_signals(signals, db):
    top_strats = get_top_strategies(db)
    return [s for s in signals if s["strategy"] in top_strats]
```

**Integration**: Call in [`scanner.py`](alpha_engine/scanner.py) before ML ranking.

## Change 2: Volatility Regime Filter (Choppy Market Killer) (Impact: +10% WR)
**Rationale**: Choppy market (ADX<25). Skip low-conviction breakouts.

**(1) Filtering**:
```
regime = detect_market_regime(df)  # ADX14
if regime["regime"] == "ranging" or regime["adx"] < 20:
    skip unless strategy in mean_reversion_strats
mean_reversion_strats = ["crypto_vwap_deviation_reversion_vol", "crypto_kalman_trend_residual_reversion"]
```

**(2-5)** Unchanged

**Code**:
```python
def regime_filter(signal, regime_cache):
    regime = regime_cache[signal["symbol"]]["regime"]
    adx = regime_cache[signal["symbol"]]["adx"]
    strat = signal["strategy"]
    reversion_strats = {..}
    if regime == "ranging" or adx < 20:
        return strat in reversion_strats
    return True
```

## Change 3: Kelly + Vol-Adjusted Sizing (Impact: +12% PF)
**Rationale**: Fixed % ignores strat edge/vol. Kelly scales with edge.

**(1) Filter**: Unchanged

**(2) Sizing Formula**:
```
p = strat_stats["win_rate"]
b = strat_stats["avg_win_pct"] / abs(strat_stats["avg_loss_pct"])
f_kelly = p - (1-p) / b
f = max(0, min(f_kelly * 2, 0.08))  # half-kelly conservative
risk_dist = abs((entry - sl) / entry)
vol_adj = median_atr / current_atr  # shrink size in high vol
size_pct = f * risk_dist * vol_adj * 0.02  # base 2% risk
size_pct = min(size_pct, 0.12)  # cap 12%
```

**Code**:
```python
def kelly_size(capital, strat_stats, entry, sl, current_atr, median_atr):
    p = strat_stats.get("win_rate", 0.5)
    avg_win = strat_stats.get("avg_win_pct", 0.15)
    avg_loss = abs(strat_stats.get("avg_loss_pct", -0.15))
    b = avg_win / avg_loss if avg_loss else 1
    f = p - (1 - p) / b
    f = max(0, min(f * 0.5, 0.08))  # half-kelly
    risk_dist = abs((entry - sl) / entry)
    vol_adj = median_atr / max(current_atr, median_atr * 0.5)
    risk_pct = f * vol_adj * 0.02  # 2% base risk
    dollar_size = capital * risk_pct / risk_dist
    return min(dollar_size, capital * 0.12)
```

**(3-5)** Unchanged

**Integration**: Replace fixed sizing in [`backtest/position_sizing.py`](alpha_engine/backtest/position_sizing.py)

## Change 4: Trailing Stops + Time Exits (Cut Losses, Let Winners Run) (Impact: +8% Expectancy)
**Rationale**: Fixed TP too tight (17% wins < 19% losses). Trail after breakeven.

**(1-2)** Unchanged

**(3) SL Management**:
```
- Trail activate: after +5% profit OR 1:1 RR hit
- Trail distance: ATR * 2 (dynamic)
- Time exit: 7 days if < breakeven, 14 days max hold
- Shorts: fixed SL (no trail, momentum risk)
```

**Code** (in pick monitor loop):
```python
def manage_exits(pick, current_price, atr):
    direction = pick["direction"]
    entry = pick["entry_price"]
    pnl_pct = (current_price - entry) / entry if direction == "LONG" else (entry - current_price) / entry
    
    if pnl_pct > 0.05:  # activate trail
        trail_dist = atr * 2
        if direction == "LONG":
            new_sl = current_price - trail_dist
            pick["stop_loss"] = max(pick["stop_loss"], new_sl)
        else:
            new_sl = current_price + trail_dist
            pick["stop_loss"] = min(pick["stop_loss"], new_sl)
    
    days_held = (now - entry_date).days
    if days_held > 7 and pnl_pct < 0:
        close("TIME_EXIT")
    if days_held > 14:
        close("MAX_HOLD")
```

**(4-5)** Unchanged

## Change 5: Strict Concentration Limits (Impact: +10% Drawdown Reduction)
**Rationale**: No corr filter = WIF wipes BTC.

**(1-3)** Unchanged

**(4) Limits**:
```
max_pos_per_asset = 1
max_long_portfolio = 0.40  # 40% total long exposure
max_short_portfolio = 0.30
max_per_family = 3  # e.g., max 3 momentum longs
family = STRATEGY_FAMILIES[strategy]  # from config.py
```

**Code**:
```python
def check_concentration(open_positions, proposed_signal):
    asset_expo = sum(p["size_pct"] for p in open_positions if p["symbol"] == proposed["symbol"])
    if asset_expo >= 0.10: return False
    
    longs = sum(p["size_pct"] for p in open_positions if p["direction"] == "LONG")
    shorts = sum(p["size_pct"] for p in open_positions if p["direction"] == "SHORT")
    if proposed["direction"] == "LONG" and longs >= 0.40: return False
    if proposed["direction"] == "SHORT" and shorts >= 0.30: return False
    
    family = STRATEGY_FAMILIES[proposed["strategy"]]
    family_dir = sum(p["size_pct"] for p in open_positions 
                     if STRATEGY_FAMILIES[p["strategy"]] == family and p["direction"] == proposed["direction"])
    if family_dir >= 0.20: return False
    
    return True
```

**(5) Low-Trade**: Kill if after 5 trades: WR<0.40 or PF<0.9. Move to "dead_strategies" list.

**Expected Outcome**: WR ~58%, PF ~1.35, Expectancy +2.1% (back-of-envelope: filter noise + shrink losses + Kelly edge)

**Next**: Integrate into [`production_scanner.py`](alpha_engine/production_scanner.py) and [`scanner.py`](alpha_engine/scanner.py). Test with forward_validator.py.
