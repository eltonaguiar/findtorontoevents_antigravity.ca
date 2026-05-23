# Phase 2: Signal Quality Enhancements — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve pick quality through confidence-weighted TP/SL, multi-timeframe confirmation, order-book depth scoring, and adaptive position sizing — targeting +5-10% WR improvement on research cohort strategies.

**Architecture:** Four independent modules that plug into the existing beta scorer and strategy pipeline. Each module is self-contained with its own API, integrated via the aggregator's market_context and the portfolio manager's score_pick(). Order-book depth adds a 6th sub-score to the On-Chain pillar. Multi-TF confirmation filters picks before they reach consensus. Confidence-weighted TP/SL adjusts exit levels in the strategy functions themselves. Adaptive sizing uses beta + confidence to scale position_pct.

**Tech Stack:** Python 3.10+, pandas, requests (Binance public API for order book). No new dependencies.

**Spec:** `docs/superpowers/specs/2026-03-16-proven-research-strategies-beta-score-design.md` (Sections 4, 7)

**Depends on:** Phase 1 complete (Tasks 1-13 landed)

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `cross_aggregation/order_book_depth.py` | CREATE | Binance order book fetcher + imbalance calculator |
| `cross_aggregation/beta_confluence_scorer.py` | MODIFY | Add OB depth to On-Chain pillar, add to market_context |
| `alpha_engine/multi_tf.py` | CREATE | Higher-timeframe confirmation checker |
| `alpha_engine/proven_research_strategies.py` | MODIFY | Add confidence-weighted TP/SL adjustments |
| `alpha_engine/position_sizer.py` | MODIFY | Add beta-aware adaptive sizing |
| `audit_dashboard/portfolio_manager.py` | MODIFY | Wire adaptive sizing into score_pick() |
| `cross_aggregation/aggregator.py` | NO CHANGE | Multi-TF is applied at strategy level, not aggregator |

**Deferred to Phase 3:**
- Spec 4.1 (Volatility-scaled TP/SL) — already done in Phase 1 via ATR-based TP/SL in strategies
- Spec 4.4 (Adaptive R:R based on rolling WR) — needs 30+ closed trades per strategy first
- Spec 4.6 (TP/SL efficiency dashboard panel) — needs outcome data to populate

---

## Chunk 1: Order-Book Depth Integration

### Task 1: Create order_book_depth.py

**Files:**
- Create: `cross_aggregation/order_book_depth.py`

- [ ] **Step 1: Create the order book depth module**

```python
"""
Order-Book Depth — Binance public API integration for bid/ask imbalance.
Feeds into beta confluence scorer On-Chain pillar.
"""
import logging
import time
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Symbol mapping: our format → Binance format
_SYMBOL_MAP = {
    "BTC-USD": "BTCUSDT", "ETH-USD": "ETHUSDT", "SOL-USD": "SOLUSDT",
    "XRP-USD": "XRPUSDT", "BNB-USD": "BNBUSDT", "ADA-USD": "ADAUSDT",
    "DOGE-USD": "DOGEUSDT", "AVAX-USD": "AVAXUSDT", "DOT-USD": "DOTUSDT",
    "LINK-USD": "LINKUSDT", "MATIC-USD": "MATICUSDT",
}

_OB_CACHE: Dict[str, dict] = {}
_OB_CACHE_TTL = 120  # 2 min cache per symbol


def get_order_book_imbalance(symbol: str, depth: int = 20) -> Optional[Dict[str, float]]:
    """
    Fetch Binance order book and compute bid/ask imbalance.

    Returns:
        {
            "imbalance": float (-1 to 1, positive = more bids = bullish),
            "bid_volume": float,
            "ask_volume": float,
            "spread_pct": float (bid-ask spread as % of mid price),
        }
        or None if API fails or symbol not mapped.
    """
    binance_sym = _SYMBOL_MAP.get(symbol)
    if not binance_sym:
        return None

    # Check cache
    cached = _OB_CACHE.get(binance_sym)
    if cached and (time.time() - cached.get("_ts", 0)) < _OB_CACHE_TTL:
        return {k: v for k, v in cached.items() if k != "_ts"}

    try:
        import requests
        r = requests.get(
            f"https://api.binance.com/api/v3/depth",
            params={"symbol": binance_sym, "limit": depth},
            timeout=5,
        )
        if r.status_code != 200:
            return None

        data = r.json()
        bids = data.get("bids", [])
        asks = data.get("asks", [])

        if not bids or not asks:
            return None

        bid_volume = sum(float(b[1]) for b in bids)
        ask_volume = sum(float(a[1]) for a in asks)
        total = bid_volume + ask_volume

        imbalance = (bid_volume - ask_volume) / total if total > 0 else 0

        best_bid = float(bids[0][0])
        best_ask = float(asks[0][0])
        mid = (best_bid + best_ask) / 2
        spread_pct = (best_ask - best_bid) / mid * 100 if mid > 0 else 0

        result = {
            "imbalance": round(imbalance, 4),
            "bid_volume": round(bid_volume, 2),
            "ask_volume": round(ask_volume, 2),
            "spread_pct": round(spread_pct, 4),
        }

        # Cache
        _OB_CACHE[binance_sym] = {**result, "_ts": time.time()}
        return result

    except Exception as e:
        logger.warning(f"Order book fetch failed for {symbol}: {e}")
        return None


def get_bulk_imbalance(symbols: list, depth: int = 20) -> Dict[str, dict]:
    """Fetch order book for multiple symbols. Returns {symbol: imbalance_dict}."""
    results = {}
    for sym in symbols:
        ob = get_order_book_imbalance(sym, depth)
        if ob:
            results[sym] = ob
    return results
```

- [ ] **Step 2: Verify it compiles**

Run: `python -c "import py_compile; py_compile.compile('cross_aggregation/order_book_depth.py', doraise=True)"`

- [ ] **Step 3: Commit**

```bash
git add cross_aggregation/order_book_depth.py
git commit -m "feat: add order_book_depth module — Binance bid/ask imbalance for beta scorer"
```

---

### Task 2: Wire order-book depth into beta scorer

**Files:**
- Modify: `cross_aggregation/beta_confluence_scorer.py:68-96` (On-Chain pillar) and `~213-266` (market context)

- [ ] **Step 1: Add OB data to build_market_context()**

In `build_market_context()`, after the LunarCrush block (before the cache write), add:

```python
        # Order book depth for top crypto symbols
        try:
            from cross_aggregation.order_book_depth import get_bulk_imbalance
            ob_data = get_bulk_imbalance(["BTC-USD", "ETH-USD", "SOL-USD"])
            ctx["order_book_depth"] = ob_data
        except Exception as e:
            logger.warning(f"Order book depth failed: {e}")
            ctx["order_book_depth"] = {}
```

Also add `"order_book_depth": {}` to the default ctx dict at the top of `build_market_context()`.

- [ ] **Step 2: Add OB scoring to _score_onchain()**

In `_score_onchain()`, the current max is 20 points (7 + 7 + 6). We need to rebalance to fit OB depth. Change the weights:
- Fear & Greed: 0-6 pts (was 0-7)
- Exchange flows: 0-5 pts (was 0-7)
- MVRV: 0-4 pts (was 0-6)
- Order book depth: 0-5 pts (NEW)

After the MVRV block, add:

```python
        # Order book depth (0-5)
        ob_data = ctx.get("order_book_depth", {})
        symbol = pick.get("symbol", "")
        ob = ob_data.get(symbol, {})
        if ob:
            imb = ob.get("imbalance", 0)
            if is_long and imb > 0.3:
                score += 5  # strong bid support
            elif is_long and imb > 0.1:
                score += 3
            elif not is_long and imb < -0.3:
                score += 5  # strong ask pressure
            elif not is_long and imb < -0.1:
                score += 3
            else:
                score += 1
        else:
            score += 2  # neutral if no OB data
```

- [ ] **Step 3: Rebalance existing On-Chain sub-scores**

Rebalance ALL branches (LONG and SHORT) for each sub-score:

**F&G scoring (change 7→6, 4→3) — BOTH branches:**
```python
        if is_long:
            if fg <= 25: score += 6
            elif fg <= 40: score += 3
            else: score += 1
        else:
            if fg >= 75: score += 6
            elif fg >= 60: score += 3
            else: score += 1
```

**Exchange flows (change 7→5, 4→3) — BOTH branches:**
```python
        if is_long and flows < -500: score += 5
        elif is_long and flows < 0: score += 3
        elif not is_long and flows > 500: score += 5
        elif not is_long and flows > 0: score += 3
        else: score += 1
```

**MVRV (change 6→4, 3→2) — BOTH branches:**
```python
        if is_long and mvrv < -0.5: score += 4
        elif is_long and mvrv < 0: score += 2
        elif not is_long and mvrv > 2: score += 4
        elif not is_long and mvrv > 0.5: score += 2
        else: score += 1
```

Total LONG max: 6 + 5 + 4 + 5 = 20. Total SHORT max: 6 + 5 + 4 + 5 = 20. Symmetric.

- [ ] **Step 4: Verify and commit**

Run: `python -c "import sys; sys.path.insert(0, 'cross_aggregation'); from beta_confluence_scorer import BetaConfluenceScorer; s = BetaConfluenceScorer(); print('OK')"`

```bash
git add cross_aggregation/beta_confluence_scorer.py
git commit -m "feat: add order-book depth to beta scorer On-Chain pillar (rebalanced 6+5+4+5=20)"
```

---

## Chunk 2: Multi-Timeframe Confirmation

### Task 3: Create multi_tf.py

**Files:**
- Create: `alpha_engine/multi_tf.py`

- [ ] **Step 1: Create the multi-timeframe confirmation module**

```python
"""
Multi-Timeframe Confirmation — checks higher TF alignment before committing TP/SL.
1H signals check 4H, 4H signals check 1D.
"""
import pandas as pd
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)

try:
    from indicators import ema, rsi
except ImportError:
    from alpha_engine.indicators import ema, rsi


# Timeframe hierarchy
_HTF_MAP = {
    "5m": "1h",
    "15m": "1h",
    "1h": "4h",
    "4h": "1d",
    "1d": "1w",
}


def confirm_direction(symbol: str, direction: str, base_tf: str,
                      htf_data: Optional[pd.DataFrame] = None) -> Dict[str, any]:
    """
    Check if higher timeframe supports the pick direction.

    Args:
        symbol: e.g. "BTC-USD"
        direction: "BUY" or "SELL" (or "LONG"/"SHORT")
        base_tf: timeframe of the signal ("1h", "4h", etc.)
        htf_data: DataFrame of higher TF OHLCV (if pre-fetched)

    Returns:
        {
            "confirmed": bool,
            "htf": str (the higher timeframe checked),
            "htf_trend": str ("BULLISH", "BEARISH", "NEUTRAL"),
            "tp_adjustment": float (1.0 = no change, 0.8 = tighten 20%),
            "sl_adjustment": float (1.0 = no change, 1.1 = widen 10%),
        }
    """
    htf = _HTF_MAP.get(base_tf, "1d")
    is_long = direction in ("BUY", "LONG")

    # If no HTF data provided, try to fetch
    if htf_data is None:
        htf_data = _fetch_htf_data(symbol, htf)

    if htf_data is None or len(htf_data) < 30:
        return {
            "confirmed": True,  # default to confirmed if no data
            "htf": htf,
            "htf_trend": "UNKNOWN",
            "tp_adjustment": 1.0,
            "sl_adjustment": 1.0,
        }

    # Compute HTF indicators
    ema_21 = ema(htf_data["Close"], 21)
    ema_50 = ema(htf_data["Close"], 50)
    rsi_val = rsi(htf_data["Close"]).iloc[-1]
    price = htf_data["Close"].iloc[-1]

    # Determine HTF trend
    bullish = price > ema_21.iloc[-1] > ema_50.iloc[-1]
    bearish = price < ema_21.iloc[-1] < ema_50.iloc[-1]

    if bullish:
        htf_trend = "BULLISH"
    elif bearish:
        htf_trend = "BEARISH"
    else:
        htf_trend = "NEUTRAL"

    # Confirm direction alignment
    if is_long and htf_trend == "BULLISH":
        confirmed = True
        tp_adj = 1.1   # HTF confirms: widen TP 10%
        sl_adj = 0.95   # tighter SL (confident)
    elif not is_long and htf_trend == "BEARISH":
        confirmed = True
        tp_adj = 1.1
        sl_adj = 0.95
    elif htf_trend == "NEUTRAL":
        confirmed = True  # neutral is OK, no adjustment
        tp_adj = 1.0
        sl_adj = 1.0
    else:
        # HTF opposes direction
        confirmed = False
        tp_adj = 0.8    # tighten TP 20% (less room)
        sl_adj = 1.1    # widen SL 10% (more risk)

    return {
        "confirmed": confirmed,
        "htf": htf,
        "htf_trend": htf_trend,
        "tp_adjustment": tp_adj,
        "sl_adjustment": sl_adj,
    }


def adjust_tp_sl(entry: float, tp: float, sl: float, direction: str,
                 tp_adj: float, sl_adj: float) -> tuple:
    """Apply TP/SL adjustments from multi-TF confirmation."""
    is_long = direction in ("BUY", "LONG")

    if is_long:
        tp_dist = tp - entry
        sl_dist = entry - sl
        new_tp = entry + tp_dist * tp_adj
        new_sl = entry - sl_dist * sl_adj
    else:
        tp_dist = entry - tp
        sl_dist = sl - entry
        new_tp = entry - tp_dist * tp_adj
        new_sl = entry + sl_dist * sl_adj

    return new_tp, new_sl


def _fetch_htf_data(symbol: str, timeframe: str) -> Optional[pd.DataFrame]:
    """Try to fetch higher TF data via yfinance. Resamples 1H→4H since yfinance lacks 4H."""
    try:
        import yfinance as yf
        # yfinance doesn't support 4H candles — fetch 1H and resample
        if timeframe == "4h":
            yf_interval = "1h"
            period = "60d"
        elif timeframe == "1w":
            yf_interval = "1wk"
            period = "2y"
        else:
            yf_interval = timeframe
            period = "60d" if timeframe == "1h" else "1y"

        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=yf_interval)
        if df.empty:
            return None

        # Resample 1H → 4H if needed
        if timeframe == "4h" and yf_interval == "1h":
            df = df.resample("4h").agg({
                "Open": "first", "High": "max", "Low": "min",
                "Close": "last", "Volume": "sum"
            }).dropna()

        return df
    except Exception as e:
        logger.warning(f"HTF data fetch failed for {symbol} {timeframe}: {e}")
        return None
```

- [ ] **Step 2: Verify it compiles**

Run: `python -c "import py_compile; py_compile.compile('alpha_engine/multi_tf.py', doraise=True)"`

- [ ] **Step 3: Commit**

```bash
git add alpha_engine/multi_tf.py
git commit -m "feat: add multi-timeframe confirmation module (HTF trend + TP/SL adjustment)"
```

---

### Task 4: Wire multi-TF into proven research strategies

**Files:**
- Modify: `alpha_engine/proven_research_strategies.py`

- [ ] **Step 1: Add multi-TF import at top of file**

After existing imports, add:

```python
try:
    from multi_tf import confirm_direction, adjust_tp_sl
    _HAS_MULTI_TF = True
except ImportError:
    _HAS_MULTI_TF = False
```

- [ ] **Step 2: Add a helper that applies multi-TF to any pick**

After the `_buy_pick` helper, add:

```python
def _apply_multi_tf(pick: dict, data: dict) -> dict:
    """Apply multi-TF confirmation to a pick. Adjusts TP/SL and adds confirmation metadata."""
    if not _HAS_MULTI_TF:
        return pick

    symbol = pick.get("symbol", "")
    direction = pick.get("signal_type", "BUY")
    timeframe = pick.get("timeframe", "1h")
    htf_data = data.get(symbol)  # pass the same data, multi_tf will fetch HTF

    try:
        result = confirm_direction(symbol, direction, timeframe, htf_data=None)
        pick["htf_confirmed"] = result["confirmed"]
        pick["htf_trend"] = result["htf_trend"]

        if result["tp_adjustment"] != 1.0 or result["sl_adjustment"] != 1.0:
            entry = pick["entry_price"]
            tp = pick["take_profit"]
            sl = pick["stop_loss"]
            new_tp, new_sl = adjust_tp_sl(entry, tp, sl, direction,
                                           result["tp_adjustment"], result["sl_adjustment"])
            pick["take_profit"] = round(new_tp, 8)
            pick["stop_loss"] = round(new_sl, 8)
            # Recalculate R:R
            reward = abs(new_tp - entry)
            risk = abs(entry - new_sl)
            pick["risk_reward"] = round(reward / risk, 2) if risk > 0 else 0
    except Exception:
        pass  # graceful degradation

    return pick
```

- [ ] **Step 3: Apply multi-TF to each strategy's output**

In each of the 10 strategy functions, before `signals.append(pick)`, add:
```python
                pick = _apply_multi_tf(pick, data)
```

This is a mechanical change — find every `signals.append(` call and wrap the pick with `_apply_multi_tf` first. There should be ~15-20 append calls across the 10 strategies.

- [ ] **Step 4: Verify and commit**

Run: `python -c "import py_compile; py_compile.compile('alpha_engine/proven_research_strategies.py', doraise=True)"`

```bash
git add alpha_engine/proven_research_strategies.py
git commit -m "feat: apply multi-TF confirmation to all 10 research strategies"
```

---

## Chunk 3: Confidence-Weighted TP/SL

### Task 5: Add confidence-weighted TP/SL adjustment to strategies

**Files:**
- Modify: `alpha_engine/proven_research_strategies.py`

- [ ] **Step 1: Add confidence TP/SL helper**

After the `_apply_multi_tf` helper, add:

```python
def _confidence_adjust_tp_sl(pick: dict) -> dict:
    """
    Scale TP/SL by confidence level.
    Higher confidence → wider TP (let winners run), slightly tighter SL.
    """
    conf = pick.get("confidence", 0.5)
    entry = pick.get("entry_price", 0)
    tp = pick.get("take_profit", 0)
    sl = pick.get("stop_loss", 0)

    if not entry or not tp or not sl:
        return pick

    # Confidence factor: 0.7 + conf*0.6, then clamped to [0.85, 1.15]
    # conf 0.5 → 1.0 (neutral), conf 0.75 → 1.15 (capped), conf 0.25 → 0.85 (capped)
    conf_factor = 0.7 + (conf * 0.6)
    conf_factor = max(0.85, min(1.15, conf_factor))

    direction = pick.get("signal_type", "BUY")
    is_long = direction in ("BUY", "LONG")

    if is_long:
        tp_dist = tp - entry
        sl_dist = entry - sl
        pick["take_profit"] = round(entry + tp_dist * conf_factor, 8)
        pick["stop_loss"] = round(entry - sl_dist / conf_factor, 8)
    else:
        tp_dist = entry - tp
        sl_dist = sl - entry
        pick["take_profit"] = round(entry - tp_dist * conf_factor, 8)
        pick["stop_loss"] = round(entry + sl_dist / conf_factor, 8)

    # Recalculate R:R
    new_tp = pick["take_profit"]
    new_sl = pick["stop_loss"]
    reward = abs(new_tp - entry)
    risk = abs(entry - new_sl)
    pick["risk_reward"] = round(reward / risk, 2) if risk > 0 else 0

    return pick
```

- [ ] **Step 2: Apply to each strategy pick (after multi-TF)**

In the `_apply_multi_tf` wrapper (or create a combined wrapper), chain both adjustments:

Replace each `pick = _apply_multi_tf(pick, data)` with:
```python
                pick = _confidence_adjust_tp_sl(_apply_multi_tf(pick, data))
```

Or create a combined helper:
```python
def _enhance_pick(pick: dict, data: dict) -> dict:
    """Apply all Phase 2 enhancements: multi-TF + confidence TP/SL."""
    pick = _apply_multi_tf(pick, data)
    pick = _confidence_adjust_tp_sl(pick)
    return pick
```

Then use `pick = _enhance_pick(pick, data)` everywhere.

- [ ] **Step 3: Verify and commit**

Run: `python -c "import py_compile; py_compile.compile('alpha_engine/proven_research_strategies.py', doraise=True)"`

```bash
git add alpha_engine/proven_research_strategies.py
git commit -m "feat: add confidence-weighted TP/SL adjustment to research strategies"
```

---

## Chunk 4: Adaptive Position Sizing

### Task 6: Add beta-aware sizing to position_sizer.py

**Files:**
- Modify: `alpha_engine/position_sizer.py:232-266` (`_calculate_size` method)

- [ ] **Step 1: Read position_sizer.py to find _calculate_size**

Find the `_calculate_size(self, signal, regime_cell)` method (~line 232).

- [ ] **Step 2: Add beta-aware multiplier**

Inside `_calculate_size`, after the regime multiplier is applied, add:

```python
        # Beta-aware sizing: scale by beta score if available
        beta_score = signal.get("beta_score", 50)
        beta_mult = 0.7 + (beta_score / 100) * 0.6  # range: 0.7 (score=0) to 1.3 (score=100)
        beta_mult = max(0.5, min(1.5, beta_mult))
        position_size *= beta_mult

        # Confidence boost
        conf = signal.get("confidence", 0.5)
        conf_mult = 0.8 + conf * 0.4  # range: 0.8 (conf=0) to 1.2 (conf=1.0)
        position_size *= conf_mult
```

Note: The existing variable in `_calculate_size` is `position_size` (not `position_size_pct`).

- [ ] **Step 3: Cap the position size**

Ensure the result is capped (this line likely already exists — just verify):
```python
        position_size = min(position_size, self.max_risk_pct)
```

- [ ] **Step 4: Verify and commit**

Run: `python -c "import py_compile; py_compile.compile('alpha_engine/position_sizer.py', doraise=True)"`

```bash
git add alpha_engine/position_sizer.py
git commit -m "feat: add beta-score and confidence-aware adaptive position sizing"
```

---

### Task 7: Wire beta multiplier into portfolio_manager score_pick()

**Files:**
- Modify: `audit_dashboard/portfolio_manager.py:~2540-2560`

> **NOTE:** Phase 1 already added `beta_score`/`beta_qualified`/`beta_breakdown` reading and `normalize_production_score` to this file (~lines 2552-2576). This task ONLY adds the beta multiplier to the production_score calculation. Do NOT duplicate the existing code.

- [ ] **Step 1: Add beta_score as a multiplier in score_pick()**

Find the `production_score = max(0, raw)` line (~line 2548). Replace it with:

```python
    # Beta score multiplier (Phase 2)
    beta_mult = 1.0
    if beta_score is not None:
        if beta_qualified:
            beta_mult = 1.3  # 30% boost for beta-qualified picks
        elif beta_score >= 50:
            beta_mult = 1.0  # neutral for marginal
        else:
            beta_mult = 0.7  # 30% penalty for low-beta picks

    production_score = max(0, raw) * beta_mult
```

This replaces the existing `production_score = max(0, raw)` with the beta-weighted version. The divergence calculation already exists from Phase 1 — do NOT add it again.

- [ ] **Step 3: Verify and commit**

Run: `python -c "import py_compile; py_compile.compile('audit_dashboard/portfolio_manager.py', doraise=True)"`

```bash
git add audit_dashboard/portfolio_manager.py
git commit -m "feat: add beta-score multiplier and divergence to portfolio manager scoring"
```

---

## Chunk 5: Updates Page + Verification

### Task 8: Update the updates page

**Files:**
- Modify: `updates/index.html`

- [ ] **Step 1: Insert Phase 2 entry at top of latest month section**

Find the Mar 16 entry from Phase 1. Insert BEFORE it (at the very top of March section):

```html
<div class="update-entry" style="--dot-color: #3b82f6;" data-tags="alpha-engine,cross-aggregation,audit-dashboard" data-category="trading" data-types="feature,improvement">
  <div class="update-date">Mar 16, 2026</div>
  <div class="update-title">
    <span class="badge badge-feature">Enhancement</span>
    Phase 2: Signal Quality — Order Book Depth, Multi-TF, Adaptive Sizing
  </div>
  <div class="update-body">
    <h4>Order-Book Depth Integration</h4>
    <p>Binance Level-2 order book data now feeds into the beta confluence scorer's On-Chain pillar. Bid/ask imbalance scoring adds up to 5 points — strong bid support for longs, strong ask pressure for shorts.</p>

    <h4>Multi-Timeframe Confirmation</h4>
    <p>All 10 research strategies now check a higher timeframe before committing exits:</p>
    <ul>
      <li>1H signals verify against 4H trend</li>
      <li>4H signals verify against 1D trend</li>
      <li>HTF confirms: TP widened 10%, SL tightened 5%</li>
      <li>HTF opposes: TP tightened 20%, SL widened 10%</li>
    </ul>

    <h4>Confidence-Weighted TP/SL</h4>
    <p>Take profit and stop loss levels now scale with strategy confidence (0.85x-1.15x). Higher confidence picks get wider TP targets to let winners run.</p>

    <h4>Adaptive Position Sizing</h4>
    <p>Position sizes now scale by beta score (0.7x-1.3x) and confidence (0.8x-1.2x). Beta-qualified picks (score 70+) get 30% larger allocations; low-beta picks get 30% smaller.</p>

    <h4>Affected Dashboards</h4>
    <ul>
      <li><a href="https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/alpha/">Alpha Engine Dashboard</a> — enhanced TP/SL on research strategies</li>
      <li><a href="https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/monitor/">Cross-Aggregation Monitor</a> — order-book depth in beta scores</li>
    </ul>
  </div>
</div>
```

- [ ] **Step 2: Verify and commit**

```bash
git add updates/index.html
git commit -m "feat: add Phase 2 update entry — OB depth, multi-TF, adaptive sizing"
```

---

### Task 9: End-to-end verification

- [ ] **Step 1: Compile all modified files**

```bash
python -c "
import py_compile
files = [
    'cross_aggregation/order_book_depth.py',
    'cross_aggregation/beta_confluence_scorer.py',
    'alpha_engine/multi_tf.py',
    'alpha_engine/proven_research_strategies.py',
    'alpha_engine/position_sizer.py',
    'audit_dashboard/portfolio_manager.py',
]
for f in files:
    try:
        py_compile.compile(f, doraise=True)
        print(f'OK: {f}')
    except py_compile.PyCompileError as e:
        print(f'FAIL: {f} -- {e}')
"
```
Expected: All OK.

- [ ] **Step 2: Verify beta scorer still works with OB depth**

```bash
python -c "
import sys; sys.path.insert(0, 'cross_aggregation')
from beta_confluence_scorer import BetaConfluenceScorer
s = BetaConfluenceScorer()
mock = {'entry': 100, 'tp': 106, 'sl': 97, 'direction': 'LONG', 'confidence': 0.65,
        'agreement_count_raw': 2, 'symbol': 'BTC-USD', 'strategy': 'vwap_trend_bounce'}
ctx = {'fear_greed_index': 30, 'btc_24h_pct': 2.5, 'volatility_regime': 'NORMAL',
       'regime': 'TRENDING', 'exchange_flows_net': -100, 'mvrv_zscore': -0.3,
       'lunarcrush_galaxy_score': None,
       'order_book_depth': {'BTC-USD': {'imbalance': 0.35, 'bid_volume': 100, 'ask_volume': 50, 'spread_pct': 0.01}}}
result = s.score_pick(mock, ctx)
print(f'Beta score: {result[\"total\"]}/100 (with OB depth)')
print(f'Breakdown: {result[\"breakdown\"]}')
assert result['total'] <= 100
print('All OK')
"
```

- [ ] **Step 3: Verify multi-TF module loads**

```bash
python -c "
import sys; sys.path.insert(0, 'alpha_engine')
from multi_tf import confirm_direction, adjust_tp_sl
# Test with no data (should default to confirmed)
result = confirm_direction('BTC-USD', 'BUY', '1h')
print(f'HTF confirmation: {result}')
assert result['confirmed'] == True
# Test TP/SL adjustment
new_tp, new_sl = adjust_tp_sl(100, 106, 97, 'BUY', 0.8, 1.1)
print(f'Adjusted: TP={new_tp}, SL={new_sl}')
assert new_tp < 106  # tightened
assert new_sl < 97   # widened
print('All OK')
"
```
