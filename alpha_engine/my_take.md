# My Take on the Portfolio and Strategy Mutation Enhancements

## Overview
The current crypto‑paper‑trading system is impressive in its breadth – *81 signal generators* feeding *15 portfolios* – but the performance metrics (44 % win‑rate, 0.71 profit factor, –3.24 % expectancy) show that the signal‑to‑position pipeline is too noisy. The forward‑validated top‑5 strategies are solid, yet they are drowned out by the mass of under‑performing models.

Below is a concise, pragmatic “take” that focuses on **what to change first**, **why it matters**, and **how to implement it** with minimal disruption to the existing code base.

---

## 1️⃣ Filter‑First, Trade‑Later

### What
1. **Enable the existing *forward‑gate*** (`FORWARD_GATE_MIN_TRADES`, `FORWARD_GATE_MIN_WR`).
2. **Add a *top‑strategy whitelist*** derived from the forward‑validated list (the five strategies you already know work). Any strategy not in the whitelist is either sandboxed (size = 0.5 % of capital) or killed after 5 trades with WR < 40 %.

### Why
- Reduces the 1 540 daily picks to a manageable set.
- Guarantees that the majority of capital is allocated to statistically proven edges.

### Implementation Sketch
```python
# In scanner.py before ML ranking
from alpha_engine.database import SQLiteStore
store = SQLiteStore()
TOP_STRATS = {
    "crypto_rsi_whaleconfirmed_v1",
    "funding_momentum",
    "crypto_keltner_compression_expansion",
    "crypto_vwap_deviation_reversion_vol",
    "crypto_kalman_trend_residual_reversion",
}

def filter_signal(sig):
    # Keep only whitelisted or sandboxed low‑trade strategies
    if sig["strategy"] in TOP_STRATS:
        return True
    stats = store.compute_strategy_stats(sig["strategy"])
    if stats.get("closed_picks",0) < 5:
        # sandbox – size will be reduced later
        return True
    return False
```

---

## 2️⃣ Kelly‑Based, Volatility‑Adjusted Position Sizing

### What
Replace the *fixed % of cash* sizing with a **half‑Kelly** approach that respects the per‑trade risk distance.

### Why
- Aligns risk with each strategy’s edge (win‑rate & payoff).
- Prevents oversized bets on high‑volatility entries that currently blow up.

### Code (add to `alpha_engine/backtest/position_sizing.py`)
```python

def kelly_sizing(capital, strat_stats, entry_price, stop_price, cur_atr, median_atr):
    # Edge
    p = strat_stats.get("win_rate", 0.5)
    avg_win = strat_stats.get("avg_win_pct", 0.15)
    avg_loss = abs(strat_stats.get("avg_loss_pct", -0.15))
    b = avg_win / avg_loss if avg_loss else 1
    f = p - (1-p) / b          # Kelly fraction
    f = max(0, min(f*0.5, 0.08))  # half‑Kelly, cap 8 %
    # Distance to stop (as % of entry)
    risk_dist = abs((entry_price - stop_price) / entry_price)
    # Volatility scaling – shrink size when current ATR > median
    vol_adj = median_atr / max(cur_atr, median_atr*0.5)
    # Base risk 2 % of capital, scaled by edge & vol
    risk_pct = f * vol_adj * 0.02
    # Dollar amount, capped at 12 % of capital
    size = min(capital * risk_pct / risk_dist, capital * 0.12)
    return size
```

---

## 3️⃣ Dynamic Stop‑Loss Management

### What
- **Trailing stop** activated after the trade reaches **+5 %** (or a 1:1 risk‑reward).
- **Time‑based exit**: 7 days if still negative, 14 days absolute max.

### Why
- Fixed TP/SL (0.40 % round‑trip cost) is too tight for the observed average win of +17.73 % and loss of –19.85 %.
- Trailing protects the upside while letting winners run.

### Code (in the pick‑monitor loop, e.g., `alpha_engine/transaction_costs.py` or `scanner.py`)
```python

def manage_exit(pick, cur_price, atr):
    direction = pick["direction"]
    entry = pick["entry_price"]
    pnl = (cur_price - entry) / entry if direction == "LONG" else (entry - cur_price) / entry
    # Trail activation
    if pnl > 0.05:
        trail = atr * 2
        if direction == "LONG":
            pick["stop_loss"] = max(pick["stop_loss"], cur_price - trail)
        else:
            pick["stop_loss"] = min(pick["stop_loss"], cur_price + trail)
    # Time exits
    days = (datetime.now(timezone.utc) - pick["entry_date"]).days
    if days > 7 and pnl <= 0:
        close(pick, "TIME_EXIT")
    if days > 14:
        close(pick, "MAX_HOLD")
```

---

## 4️⃣ Concentration & Correlation Controls

### What
- **Max 1 position per symbol** (override `MAX_PER_SYMBOL` if needed).
- **Max 40 % exposure per asset class** (`MAX_CORRELATED_EXPOSURE`).
- **Family‑based direction caps** (`MAX_SAME_DIRECTION_CRYPTO` already exists, but tighten to 4).

### Why
- Prevents the WIF meme‑coin wipe‑out you observed.
- Diversifies across families (momentum, trend, volume, etc.) to reduce correlated drawdowns.

### Quick Patch (in `alpha_engine/portfolio_manager.py`)
```python
# Adjust constants
MAX_PER_SYMBOL = 1
MAX_CORRELATED_EXPOSURE = 0.40
MAX_SAME_DIRECTION_CRYPTO = 4
```

---

## 5️⃣ Low‑Trade Strategies – Sandbox → Kill

### What
- Strategies with **< 5 forward trades** stay in a *sandbox* pool with **0.5 %** allocation.
- After **5 trades** they are evaluated; if WR < 40 % or PF < 0.9 they are moved to a *dead‑list* and no longer generate picks.

### Why
- Gives new ideas a chance to prove themselves without risking capital.
- Cleans up the signal pool automatically.

### Implementation (in `alpha_engine/forward_validator.py` or the forward‑gate logic)
```python
if stats["closed_picks"] < 5:
    # sandbox – allocation handled downstream
    return True
if stats["closed_picks"] >= 5 and (stats["win_rate"] < 0.40 or stats.get("profit_factor",0) < 0.9):
    # mark dead
    dead.add(strategy)
    return False
```

---

## 📦 How to Deploy
1. **Create a new script** `alpha_engine/portfolio_survival_improvements.py` that imports the snippets above and patches the runtime objects (e.g., monkey‑patch `PortfolioManager.route_signal`).
2. **Run a short forward‑test** (`python production_scanner.py --dry-run`) to verify that the number of daily picks drops from ~1 500 to ~300 and that the average position size shrinks to ~5 % of capital.
3. **Monitor** the new `portfolio_summary` endpoint for win‑rate, PF, and draw‑down.
4. **Iterate** – if the win‑rate improves but PF drops, tighten the trailing‑stop activation threshold.

---

## TL;DR – Immediate Action List
| Step | File | Code Snippet |
|------|------|--------------|
| 1 | `scanner.py` | `filter_signal` whitelist + sandbox logic |
| 2 | `backtest/position_sizing.py` | `kelly_sizing` function |
| 3 | `scanner.py` (pick monitor) | `manage_exit` trailing & time‑exit |
| 4 | `portfolio_manager.py` | Adjust `MAX_PER_SYMBOL`, `MAX_CORRELATED_EXPOSURE`, `MAX_SAME_DIRECTION_CRYPTO` |
| 5 | `forward_validator.py` | Sandbox/killing rule for low‑trade strategies |

Implement these five changes, run a forward‑validation window of 2 weeks, and you should see **expectancy flip to +1 % – 2 %** with a healthier profit factor (> 1.2). The strategy‑mutation engine you outlined can then be layered on top of this cleaner signal foundation.
