# Strategy Audit Full Roadmap — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement all recommendations from the Inception Labs / Mercury AI strategy audit to bring coverage from ~35% to ~95%.

**Architecture:** Modular additions — each task creates a standalone module that integrates with existing systems via imports. No existing system is rewritten; we add new capabilities and wire them in.

**Tech Stack:** Python 3.11, numpy, pandas, requests, scikit-learn, scipy. No PyTorch/TensorFlow (keep lightweight for GitHub Actions).

---

## Phase 1: Quick Wins (Tasks 1-4)

### Task 1: Unified Feature Store

**Files:**
- Create: `shared/feature_store.py`
- Modify: `coinglass_strategies/signal_engine.py` (add feature_store import)
- Test: Run `python -c "from shared.feature_store import FeatureStore; fs = FeatureStore(); print('OK')"`

**What it does:**
Central singleton cache that computes and serves indicators (RSI, ATR, VWAP, OBV, funding rate, order-book imbalance, macro data). All systems call `FeatureStore.get()` instead of computing their own.

**Implementation:**
```python
# shared/feature_store.py
"""
Unified Feature Store — single source of truth for all computed features.
In-memory LRU cache with TTL. All systems import from here.
"""
import time
import numpy as np
from functools import lru_cache
from typing import Optional, Dict, Any

class FeatureStore:
    """Central feature cache with TTL-based expiry."""

    _instance = None
    _cache: Dict[str, tuple] = {}  # key -> (value, expiry_ts)
    TTL = 300  # 5 min default

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get(self, symbol: str, feature: str, **kwargs) -> Optional[float]:
        key = f"{symbol}:{feature}:{hash(frozenset(kwargs.items()))}"
        if key in self._cache:
            val, expiry = self._cache[key]
            if time.time() < expiry:
                return val
        val = self._compute(symbol, feature, **kwargs)
        self._cache[key] = (val, time.time() + self.TTL)
        return val

    def _compute(self, symbol, feature, **kwargs):
        computers = {
            "rsi": self._rsi,
            "atr": self._atr,
            "vwap_delta": self._vwap_delta,
            "obv": self._obv,
            "funding_rate": self._funding_rate,
            "orderbook_imbalance": self._ob_imbalance,
            "btc_dominance": self._btc_dominance,
            "fear_greed": self._fear_greed,
        }
        fn = computers.get(feature)
        if fn is None:
            raise ValueError(f"Unknown feature: {feature}")
        return fn(symbol, **kwargs)

    # Each _compute method fetches from appropriate API/data source
    # and returns a float value
```

**Step 1:** Create `shared/__init__.py` and `shared/feature_store.py` with full implementation
**Step 2:** Verify import works: `python -c "from shared.feature_store import FeatureStore"`
**Step 3:** Commit: `git commit -m "feat: unified feature store singleton with TTL cache"`

---

### Task 2: Cost Model Integration

**Files:**
- Create: `shared/cost_model.py` (production version, extend from ml_battleground's)
- Modify: Wire into existing backtest scripts
- Reference: `ml_battleground/shared/cost_model.py` (existing, 44 lines)

**What it does:**
Realistic trading cost calculator: taker fees + slippage based on order-book depth proxy. Injected into all backtests so WR numbers are honest.

**Implementation:**
```python
# shared/cost_model.py
"""
Unified cost model for realistic backtest and live trading.
Taker fee + slippage estimation based on asset tier and trade size.
"""

TIER_COSTS = {
    "tier1": {"fee": 0.001, "slippage": 0.0005},   # BTC, ETH
    "tier2": {"fee": 0.001, "slippage": 0.001},     # SOL, BNB, XRP, ADA
    "tier3": {"fee": 0.001, "slippage": 0.002},     # Mid-cap alts
    "tier4": {"fee": 0.0015, "slippage": 0.005},    # Low-cap alts
}

SYMBOL_TIERS = {
    "BTCUSDT": "tier1", "ETHUSDT": "tier1",
    "SOLUSDT": "tier2", "BNBUSDT": "tier2", "XRPUSDT": "tier2",
    "DOGEUSDT": "tier3", "PEPEUSDT": "tier4",
}

def estimate_round_trip_cost(symbol: str, size_usd: float = 1000) -> float:
    """Return total round-trip cost as a fraction (e.g., 0.003 = 0.3%)."""
    tier = SYMBOL_TIERS.get(symbol, "tier3")
    costs = TIER_COSTS[tier]
    # Round trip = 2x (entry + exit)
    return 2 * (costs["fee"] + costs["slippage"])

def apply_costs(entry_price: float, direction: str, symbol: str) -> tuple:
    """Return (adjusted_entry, cost_fraction) accounting for slippage."""
    tier = SYMBOL_TIERS.get(symbol, "tier3")
    costs = TIER_COSTS[tier]
    slip = costs["fee"] + costs["slippage"]
    if direction == "LONG":
        return entry_price * (1 + slip), slip
    else:
        return entry_price * (1 - slip), slip
```

**Step 1:** Create `shared/cost_model.py`
**Step 2:** Verify: `python -c "from shared.cost_model import estimate_round_trip_cost; print(estimate_round_trip_cost('BTCUSDT'))"`
**Step 3:** Commit: `git commit -m "feat: unified cost model for realistic backtest fees"`

---

### Task 3: Volatility-Targeted Stop-Loss Helper

**Files:**
- Create: `shared/vol_targeted_sl.py`

**What it does:**
Computes adaptive SL/TP distances based on ATR instead of fixed percentages. Reduces whipsaw in high-vol, tighter stops in low-vol.

**Implementation:**
```python
# shared/vol_targeted_sl.py
"""
Volatility-targeted stop-loss and take-profit calculator.
Adapts distances to current market regime via ATR.
"""
import numpy as np
from typing import Optional

def compute_atr(highs, lows, closes, period: int = 14) -> float:
    """Compute Average True Range from OHLC arrays."""
    trs = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i-1]),
            abs(lows[i] - closes[i-1])
        )
        trs.append(tr)
    if len(trs) < period:
        return np.mean(trs) if trs else 0.0
    return np.mean(trs[-period:])

def vol_targeted_levels(
    entry: float, direction: str, atr: float,
    sl_mult: float = 1.5, tp_mult: float = 2.5
) -> dict:
    """
    Compute SL and TP using ATR multiples.

    Args:
        entry: Entry price
        direction: "LONG" or "SHORT"
        atr: Current ATR value
        sl_mult: ATR multiplier for stop-loss (default 1.5)
        tp_mult: ATR multiplier for take-profit (default 2.5)

    Returns:
        dict with stop_loss, take_profit, risk_reward_ratio
    """
    if direction == "LONG":
        sl = entry - atr * sl_mult
        tp = entry + atr * tp_mult
    else:
        sl = entry + atr * sl_mult
        tp = entry - atr * tp_mult

    risk = abs(entry - sl)
    reward = abs(tp - entry)
    rr = reward / risk if risk > 0 else 0

    return {
        "stop_loss": round(sl, 6),
        "take_profit": round(tp, 6),
        "risk_reward_ratio": round(rr, 2),
        "atr": round(atr, 6),
        "sl_distance_pct": round(abs(entry - sl) / entry * 100, 2),
        "tp_distance_pct": round(abs(tp - entry) / entry * 100, 2),
    }
```

**Step 1:** Create `shared/vol_targeted_sl.py`
**Step 2:** Verify: `python -c "from shared.vol_targeted_sl import vol_targeted_levels; print(vol_targeted_levels(100000, 'LONG', 2500))"`
**Step 3:** Commit: `git commit -m "feat: volatility-targeted SL/TP helper using ATR multiples"`

---

### Task 4: Mean-Reversion Consolidation Base Class

**Files:**
- Create: `baby_strategies/mean_reversion_base.py`

**What it does:**
Single parameterized base class that replaces 12+ duplicate mean-reversion scripts. Each variant becomes a config dict instead of a separate file.

**Implementation:**
```python
# baby_strategies/mean_reversion_base.py
"""
Unified mean-reversion strategy base.
Replaces 12+ duplicate scripts with a single configurable engine.

Supported indicators: RSI, Bollinger, Keltner, Z-Score, Williams %R,
Stochastic, Connors RSI, ADX Range, KAMA, Kalman, Red Candle
"""
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timezone

# Each variant is just a config dict
VARIANTS = {
    "rsi_mean_reversion": {
        "indicator": "rsi", "period": 14,
        "oversold": 30, "overbought": 70,
        "lookback": 100, "name": "RSI Mean Reversion"
    },
    "bollinger_mean_reversion": {
        "indicator": "bollinger", "period": 20, "std_mult": 2.0,
        "lookback": 100, "name": "Bollinger Mean Reversion"
    },
    "zscore_mean_reversion": {
        "indicator": "zscore", "period": 20, "threshold": 2.0,
        "lookback": 100, "name": "Z-Score Mean Reversion"
    },
    "connors_rsi2_mean_reversion": {
        "indicator": "rsi", "period": 2,
        "oversold": 10, "overbought": 90,
        "lookback": 100, "name": "Connors RSI-2 Mean Reversion"
    },
    "keltner_mean_reversion": {
        "indicator": "keltner", "period": 20, "atr_mult": 1.5,
        "lookback": 100, "name": "Keltner Mean Reversion"
    },
    "williams_r_mean_reversion": {
        "indicator": "williams_r", "period": 14,
        "oversold": -80, "overbought": -20,
        "lookback": 100, "name": "Williams %R Mean Reversion"
    },
    "stochastic_mean_reversion": {
        "indicator": "stochastic", "period": 14,
        "oversold": 20, "overbought": 80,
        "lookback": 100, "name": "Stochastic Mean Reversion"
    },
    "adx_range_mean_reversion": {
        "indicator": "adx_rsi", "period": 14,
        "adx_threshold": 25, "oversold": 30, "overbought": 70,
        "lookback": 100, "name": "ADX Range Mean Reversion"
    },
    "red_candle_mean_reversion": {
        "indicator": "consecutive_red", "count": 3,
        "lookback": 50, "name": "Red Candle Mean Reversion"
    },
    "kalman_mean_reversion": {
        "indicator": "kalman", "period": 20, "threshold": 2.0,
        "lookback": 100, "name": "Kalman Mean Reversion"
    },
    "kama_mean_reversion": {
        "indicator": "kama", "fast": 2, "slow": 30,
        "lookback": 100, "name": "KAMA Mean Reversion"
    },
    "rsi_volume_mean_reversion": {
        "indicator": "rsi_volume", "period": 14,
        "oversold": 30, "volume_mult": 1.5,
        "lookback": 100, "name": "RSI + Volume Mean Reversion"
    },
}

class MeanReversionEngine:
    """Unified mean-reversion scanner. One engine, many configs."""

    def __init__(self, variant: str = "rsi_mean_reversion"):
        if variant not in VARIANTS:
            raise ValueError(f"Unknown variant: {variant}. Available: {list(VARIANTS.keys())}")
        self.config = VARIANTS[variant]
        self.name = self.config["name"]

    def scan(self, symbol: str, prices: np.ndarray, volumes: np.ndarray = None) -> Optional[dict]:
        """Run mean-reversion scan. Returns pick dict or None."""
        indicator = self.config["indicator"]

        if indicator == "rsi":
            return self._scan_rsi(symbol, prices)
        elif indicator == "bollinger":
            return self._scan_bollinger(symbol, prices)
        elif indicator == "zscore":
            return self._scan_zscore(symbol, prices)
        elif indicator == "keltner":
            return self._scan_keltner(symbol, prices)
        elif indicator == "williams_r":
            return self._scan_williams(symbol, prices)
        elif indicator == "stochastic":
            return self._scan_stochastic(symbol, prices)
        elif indicator == "adx_rsi":
            return self._scan_adx_rsi(symbol, prices)
        elif indicator == "consecutive_red":
            return self._scan_red_candles(symbol, prices)
        elif indicator == "rsi_volume":
            return self._scan_rsi_volume(symbol, prices, volumes)
        return None

    def _make_pick(self, symbol, direction, confidence, entry, reason):
        return {
            "symbol": symbol,
            "direction": direction,
            "confidence": round(confidence, 3),
            "entry_price": entry,
            "strategy": self.config.get("name", "mean_reversion"),
            "source": "mean_reversion_base",
            "reason": reason,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    # Each _scan_X method computes the indicator and returns a pick or None
    # Implementation follows the same pattern as existing individual scripts
```

**Step 1:** Create `baby_strategies/mean_reversion_base.py` with all indicator methods
**Step 2:** Verify: `python -c "from baby_strategies.mean_reversion_base import MeanReversionEngine, VARIANTS; print(f'{len(VARIANTS)} variants loaded')"`
**Step 3:** Commit: `git commit -m "feat: consolidated mean-reversion base class (12 variants in 1 engine)"`

---

## Phase 2: Mid-Term (Tasks 5-8)

### Task 5: Orderbook Imbalance v2 (Micro-Structure Module)

**Files:**
- Create: `shared/orderbook_imbalance_v2.py`
- Reference: `alpha_engine/data_ingest/orderbook_depth.py` (existing)

**What it does:**
Computes cumulative delta, footprint, and VWAP-delta across exchanges. Feeds into feature store. Goes beyond the existing simple bid/ask ratio.

**Key metrics:** Cumulative delta (aggressive buys - sells), bid/ask depth ratio at 5 levels, VWAP deviation, volume-weighted order flow imbalance.

**Step 1:** Create module with multi-exchange depth fetching (Binance + OKX)
**Step 2:** Register in feature store: `FeatureStore.get(symbol, "orderbook_imbalance")`
**Step 3:** Commit

---

### Task 6: Risk-Parity Position Sizer

**Files:**
- Create: `shared/risk_parity_sizer.py`

**What it does:**
Computes inverse-volatility weights per asset and scales to target portfolio vol (e.g., 10% annualized). Includes Kelly-optimal fraction with caps.

**Key functions:** `calc_position_size(signal, vol, corr, max_dd)`, `kelly_optimal_size(win_rate, avg_win, avg_loss, cap=0.02)`, `risk_parity_weights(assets, vols, corr_matrix, target_vol)`

**Step 1:** Create module
**Step 2:** Wire into cross-aggregation consensus picks
**Step 3:** Commit

---

### Task 7: Hierarchical Regime Detector

**Files:**
- Create: `regime_terminal/hierarchical_regime.py`
- Reference: `regime_terminal/hmm_engine.py` (existing flat 7-state HMM)

**What it does:**
3-level regime detection: macro (BTC dominance, DXY, Fed) → sector (alt-season vs BTC) → micro (order-book imbalance, volatility regime). Each level outputs probability vector used to weight signals.

**Implementation:** Stack 3 independent HMMs, each trained on different feature sets. Output a combined regime-weight vector that all signal generators can query.

**Step 1:** Create hierarchical module
**Step 2:** Wire into feature store as `regime_weights`
**Step 3:** Commit

---

### Task 8: Transformer-Based Price Forecaster

**Files:**
- Create: `ml_crypto_predictor/models/informer_lite.py`

**What it does:**
Lightweight attention-based forecaster (not full Informer — adapted for CPU/GitHub Actions). Uses self-attention on 1h OHLCV + features to predict next-bar direction.

**Note:** This is a numpy/scipy-only implementation (no PyTorch) to keep GitHub Actions compatible. Uses simplified multi-head attention with numpy matrix ops.

**Step 1:** Create module with attention mechanism
**Step 2:** Add training script
**Step 3:** Commit

---

## Phase 3: Long-Term (Tasks 9-13)

### Task 9: Cross-Exchange Arbitrage Engine

**Files:**
- Create: `alpha_engine/cross_exchange_arb.py`

**What it does:**
Monitors price differentials and funding-rate spreads across Binance, OKX, Kraken. Identifies arb opportunities with latency-adjusted execution estimates.

---

### Task 10: Crypto Options Volatility Surface

**Files:**
- Create: `alpha_engine/crypto_options_vol.py`

**What it does:**
Extracts implied vol, skew, and term structure from Deribit API. Generates signals when vol surface shows mispricing.

---

### Task 11: RL Market-Maker Agent

**Files:**
- Create: `rl_agent/market_maker.py`

**What it does:**
Deep Q-Learning agent that learns spread placement and inventory control. Generates "make-market" signals (not directional).

---

### Task 12: Portfolio Risk Manager

**Files:**
- Create: `shared/portfolio_risk_manager.py`

**What it does:**
Global risk controls: max-drawdown guard (stop adding at 12% DD), daily turnover cap (30%), leverage limits, risk-parity overlay across all signal buckets.

---

### Task 13: GNN On-Chain Risk Scorer

**Files:**
- Create: `ml_crypto_predictor/models/gnn_onchain.py`

**What it does:**
Builds token-transfer graph from on-chain data, outputs "whale-cluster risk" score. Uses simplified graph convolution (numpy-only).

---

## Phase 4: Integration & Wiring (Task 14)

### Task 14: Wire All Modules Into Existing Systems

**Files:**
- Modify: `cross_aggregation/aggregator.py` — add new signal sources
- Modify: `scripts/ml_system_health.py` — add health checks for new modules
- Modify: GitHub Actions workflows — add scheduled runs for new modules
- Create: `.github/workflows/strategy-audit-modules.yml`

**What it does:**
Connects all new modules to the existing pipeline so picks flow through to Discord and dashboards.

---

## Execution Order

Tasks 1-4 are independent (Phase 1 quick wins).
Tasks 5-8 depend on Task 1 (feature store).
Tasks 9-13 are independent of each other but benefit from Phase 1-2.
Task 14 wires everything together.
