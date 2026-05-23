# Ultimate Trading System Integration — Baby Bundles Enhancement Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extract the highest-value concepts from the Ultimate Quantum RL Trading System and integrate them into our existing Baby Bundles forward-testing infrastructure as lightweight, dependency-free baby strategies and system-level filters.

**Architecture:** We do NOT adopt the Ultimate System wholesale (it requires torch, talib, ccxt, gym — our baby strategies use only numpy/pandas/requests). Instead, we extract 3 production-ready concepts: (1) Fractal Regime Detection as a system-level filter that gates all signals, (2) Cross-Asset Correlation Filter that prevents correlated duplicate trades, and (3) a Hurst Exponent Mean-Reversion strategy. Each becomes a standalone module in our existing `incubator/` structure.

**Tech Stack:** Python 3.14, numpy, pandas, requests (Binance public API). No new dependencies.

---

## Current State Assessment

### Forward Test Performance (as of Feb 28, 2026)
- **19 strategies registered**, 6 generating signals, 12 total signals
- **2 closed trades**: 1W/1L, net +0.90%
- **10 open trades** across 6 strategies
- **13 strategies silent** — awaiting specific market conditions
- **Key gap**: No regime awareness, no correlation filtering, trades can stack on same direction

### What the Ultimate System Offers (Extractable Concepts)
1. **Fractal Regime Detection** via Hurst Exponent — classify market as TRENDING/MEAN_REVERTING/CHAOTIC
2. **Cross-Asset Correlation Learning** — prevent sending 3 correlated BUY signals on BTC/ETH/SOL simultaneously
3. **Portfolio Risk Parity** — position-size signals based on inverse volatility
4. **Meta-Agent Regime Routing** — route signals through regime-appropriate filter

### What We Skip (Too Heavy / Unproven)
- PyTorch RL agents (no training data yet, needs GPU)
- Quantum-Inspired Optimizer (just scipy.optimize with marketing)
- Gym environment (overkill for signal-level strategies)
- talib dependency (we compute indicators from scratch)

---

## Task 1: Fractal Regime Detector Module

**Files:**
- Create: `incubator/regime/fractal_regime_detector.py`
- Create: `incubator/regime/__init__.py`
- Test: Run inline `if __name__ == "__main__"` self-test

**Why:** The forward test shows all 10 open trades entered within the same 15-minute window — no awareness of whether the market is trending, mean-reverting, or chaotic. A regime detector tells strategies whether their signal type is appropriate right now.

**Step 1: Create the regime directory**

```bash
mkdir -p incubator/regime
```

**Step 2: Write the fractal regime detector**

```python
"""Fractal Regime Detector — Hurst Exponent + Volatility Regime Classification.

Extracted from Ultimate Quantum RL Trading System's FractalMarketAnalyzer.
Simplified to use only numpy (no torch/talib dependencies).

Regime output:
  TRENDING       — Hurst > 0.6, trend-following strategies preferred
  MEAN_REVERTING — Hurst < 0.4, mean-reversion strategies preferred
  CHAOTIC        — 0.4 <= Hurst <= 0.6 OR insufficient data, reduce position sizes

Usage:
    detector = FractalRegimeDetector()
    regime = detector.detect_regime(close_prices)  # np.ndarray of closes
    # Returns: {"regime": "TRENDING", "hurst": 0.63, "confidence": 0.72, "vol_regime": "LOW"}
"""

import numpy as np
from typing import Dict, Optional

class FractalRegimeDetector:
    def __init__(self, min_bars: int = 100):
        self.min_bars = min_bars

    def calculate_hurst_exponent(self, prices: np.ndarray) -> Optional[float]:
        """Calculate Hurst exponent using R/S analysis (rescaled range)."""
        if len(prices) < self.min_bars:
            return None
        returns = np.diff(np.log(prices[prices > 0]))
        if len(returns) < 50:
            return None

        lags = range(2, min(len(returns) // 2, 100))
        tau = []
        for lag in lags:
            std_val = np.std(np.subtract(returns[lag:], returns[:-lag]))
            if std_val > 0:
                tau.append(std_val)
            else:
                tau.append(1e-10)

        if len(tau) < 10:
            return None

        log_lags = np.log(list(lags)[:len(tau)])
        log_tau = np.log(tau)
        poly = np.polyfit(log_lags, log_tau, 1)
        hurst = float(poly[0])
        return np.clip(hurst, 0.0, 1.0)

    def calculate_volatility_regime(self, prices: np.ndarray) -> str:
        """Classify volatility as LOW/NORMAL/HIGH using ATR percentile."""
        if len(prices) < 30:
            return "NORMAL"
        returns = np.abs(np.diff(np.log(prices[prices > 0])))
        recent_vol = np.mean(returns[-14:])
        historical_vol = np.mean(returns)
        ratio = recent_vol / historical_vol if historical_vol > 0 else 1.0
        if ratio < 0.7:
            return "LOW"
        elif ratio > 1.5:
            return "HIGH"
        return "NORMAL"

    def detect_regime(self, prices: np.ndarray) -> Dict:
        """Detect market regime from price array.

        Returns dict with: regime, hurst, confidence, vol_regime
        """
        hurst = self.calculate_hurst_exponent(prices)
        vol_regime = self.calculate_volatility_regime(prices)

        if hurst is None:
            return {"regime": "CHAOTIC", "hurst": 0.5, "confidence": 0.0, "vol_regime": vol_regime}

        if hurst > 0.6:
            regime = "TRENDING"
            confidence = min(1.0, (hurst - 0.5) * 5)  # 0.6->0.5, 0.8->1.0
        elif hurst < 0.4:
            regime = "MEAN_REVERTING"
            confidence = min(1.0, (0.5 - hurst) * 5)
        else:
            regime = "CHAOTIC"
            confidence = 1.0 - abs(hurst - 0.5) * 5

        return {
            "regime": regime,
            "hurst": round(hurst, 4),
            "confidence": round(confidence, 3),
            "vol_regime": vol_regime,
        }


if __name__ == "__main__":
    import requests
    url = "https://api.binance.com/api/v3/klines"
    for sym in ["BTCUSDT", "ETHUSDT", "SOLUSDT"]:
        r = requests.get(url, params={"symbol": sym, "interval": "1h", "limit": 500})
        closes = np.array([float(k[4]) for k in r.json()])
        det = FractalRegimeDetector()
        result = det.detect_regime(closes)
        print(f"{sym}: {result}")
```

**Step 3: Run self-test**

```bash
cd /e/findtorontoevents_antigravity.ca
python incubator/regime/fractal_regime_detector.py
```

Expected: Prints regime for BTC/ETH/SOL (e.g., `BTCUSDT: {'regime': 'TRENDING', 'hurst': 0.63, ...}`)

**Step 4: Commit**

```bash
git add incubator/regime/
git commit -m "feat: add fractal regime detector extracted from Ultimate Trading System"
```

---

## Task 2: Cross-Asset Correlation Filter

**Files:**
- Create: `incubator/regime/correlation_filter.py`

**Why:** Forward test shows 3 simultaneous BTC BUY signals + 3 simultaneous ETH/SOL SELL signals opening at once. When BTC and ETH have 0.85+ correlation, these are effectively duplicate bets. A correlation filter deduplicates.

**Step 1: Write the correlation filter**

```python
"""Cross-Asset Correlation Filter — Prevents Correlated Duplicate Trades.

Extracted concept from Ultimate System's cross-asset correlation learning.
Lightweight implementation using rolling Pearson correlation.

Usage:
    filt = CorrelationFilter()
    approved = filt.filter_signals(signals, price_data)
    # Returns subset of signals with correlated duplicates removed
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional

class CorrelationFilter:
    def __init__(self, corr_threshold: float = 0.75, lookback: int = 100):
        self.corr_threshold = corr_threshold
        self.lookback = lookback

    def compute_correlation_matrix(self, price_data: Dict[str, np.ndarray]) -> pd.DataFrame:
        """Compute pairwise return correlations from close prices."""
        returns = {}
        for symbol, prices in price_data.items():
            if len(prices) < self.lookback:
                continue
            r = np.diff(np.log(prices[-self.lookback:]))
            returns[symbol] = r

        if len(returns) < 2:
            return pd.DataFrame()

        # Align lengths
        min_len = min(len(r) for r in returns.values())
        df = pd.DataFrame({s: r[-min_len:] for s, r in returns.items()})
        return df.corr()

    def filter_signals(self, signals: List[Dict], price_data: Dict[str, np.ndarray]) -> List[Dict]:
        """Remove correlated duplicate signals, keeping highest confidence.

        Each signal dict must have: symbol, direction, confidence
        """
        if len(signals) <= 1:
            return signals

        corr_matrix = self.compute_correlation_matrix(price_data)
        if corr_matrix.empty:
            return signals

        # Sort by confidence descending — highest confidence kept first
        sorted_sigs = sorted(signals, key=lambda s: s.get("confidence", 0), reverse=True)

        approved = []
        blocked_symbols = set()

        for sig in sorted_sigs:
            sym = sig["symbol"]
            direction = sig["direction"]

            # Check if this symbol's direction is blocked by a correlated already-approved signal
            is_blocked = False
            for approved_sig in approved:
                a_sym = approved_sig["symbol"]
                a_dir = approved_sig["direction"]

                # Only block same-direction signals on correlated assets
                if direction != a_dir:
                    continue

                if sym in corr_matrix.columns and a_sym in corr_matrix.columns:
                    corr = abs(corr_matrix.loc[sym, a_sym])
                    if corr >= self.corr_threshold:
                        is_blocked = True
                        break

            if not is_blocked:
                approved.append(sig)

        return approved


if __name__ == "__main__":
    import requests
    url = "https://api.binance.com/api/v3/klines"
    prices = {}
    for sym in ["BTCUSDT", "ETHUSDT", "SOLUSDT"]:
        r = requests.get(url, params={"symbol": sym, "interval": "1h", "limit": 200})
        prices[sym] = np.array([float(k[4]) for k in r.json()])

    filt = CorrelationFilter(corr_threshold=0.75)
    corr = filt.compute_correlation_matrix(prices)
    print("Correlation Matrix:")
    print(corr.round(3))

    # Test filtering
    test_signals = [
        {"symbol": "BTCUSDT", "direction": "BUY", "confidence": 0.8},
        {"symbol": "ETHUSDT", "direction": "BUY", "confidence": 0.7},
        {"symbol": "SOLUSDT", "direction": "BUY", "confidence": 0.6},
    ]
    approved = filt.filter_signals(test_signals, prices)
    print(f"\n{len(test_signals)} signals in -> {len(approved)} approved")
    for s in approved:
        print(f"  {s['symbol']} {s['direction']} conf={s['confidence']}")
```

**Step 2: Run self-test**

```bash
python incubator/regime/correlation_filter.py
```

**Step 3: Commit**

```bash
git add incubator/regime/correlation_filter.py
git commit -m "feat: add cross-asset correlation filter from Ultimate System concepts"
```

---

## Task 3: Hurst Mean-Reversion Baby Strategy

**Files:**
- Create: `incubator/agents/claude_code_01/crypto_hurst_mean_reversion_v1.py`
- Create: `incubator/agents/claude_code_01/crypto_hurst_mean_reversion_v1.py.meta.json`

**Why:** The Ultimate System's fractal analysis identifies mean-reverting regimes (Hurst < 0.4). We can build a baby strategy that only trades mean-reversion when the Hurst exponent confirms it — a novel approach not covered by any existing strategy.

**Step 1: Write the strategy**

Standard baby strategy format with `generate_signals(data, symbol) -> List[Signal]`:
- Compute Hurst exponent over last 100 bars
- Only signal when Hurst < 0.45 (confirmed mean-reverting)
- Use z-score of price vs 50-bar SMA as entry trigger
- BUY when z-score < -2.0, SELL when z-score > +2.0
- TP/SL based on ATR

**Step 2: Write meta.json**

Standard format with source: "Mandelbrot (1963) + Easley/Lopez de Prado (2012)"

**Step 3: Register in forward scanner TIER1_STRATEGIES**

Add entry to `incubator/backtest_team/forward_signal_scanner.py`

**Step 4: Commit**

```bash
git add incubator/agents/claude_code_01/crypto_hurst_mean_reversion_v1.py*
git commit -m "feat: add Hurst mean-reversion baby strategy from fractal analysis"
```

---

## Task 4: Integrate Regime + Correlation Filters into Forward Scanner

**Files:**
- Modify: `incubator/backtest_team/forward_signal_scanner.py` (scan loop)

**Why:** Currently the scanner fires all strategies independently with no system-level filtering. This task wires the regime detector and correlation filter into the scan pipeline.

**Step 1: Import modules at top of forward_signal_scanner.py**

```python
from incubator.regime.fractal_regime_detector import FractalRegimeDetector
from incubator.regime.correlation_filter import CorrelationFilter
```

**Step 2: Add regime + correlation filtering to scan loop**

In the `scan()` function, after collecting all signals from all strategies:

```python
# ── System-Level Filters (from Ultimate Trading System concepts) ──
regime_detector = FractalRegimeDetector()
corr_filter = CorrelationFilter(corr_threshold=0.75)

# 1. Detect regime per symbol
regimes = {}
for symbol in SYMBOLS:
    if symbol in price_cache:
        closes = price_cache[symbol]['close'].values
        regimes[symbol] = regime_detector.detect_regime(closes)

# 2. Filter signals by regime appropriateness
regime_filtered = []
for sig in all_signals:
    regime = regimes.get(sig.symbol, {}).get("regime", "CHAOTIC")
    strategy_type = TIER1_STRATEGIES.get(sig.__class__.__name__, {}).get("category", "unknown")

    # Skip trend-following signals in mean-reverting markets and vice versa
    # (soft filter — only blocks contradictory combos, passes everything else)
    if regime == "CHAOTIC":
        sig.confidence *= 0.8  # Reduce confidence in chaotic regime
    regime_filtered.append(sig)

# 3. Correlation filter — deduplicate correlated same-direction signals
price_arrays = {sym: price_cache[sym]['close'].values for sym in price_cache}
signal_dicts = [{"symbol": s.symbol, "direction": s.direction,
                 "confidence": s.confidence, "_signal": s} for s in regime_filtered]
approved_dicts = corr_filter.filter_signals(signal_dicts, price_arrays)
approved_signals = [d["_signal"] for d in approved_dicts]
```

**Step 3: Log regime info to JSON output**

Add regime data to the `forward_signals.json` output so the dashboard can display it.

**Step 4: Run a test scan**

```bash
python incubator/backtest_team/forward_signal_scanner.py --scan
```

**Step 5: Commit**

```bash
git add incubator/backtest_team/forward_signal_scanner.py
git commit -m "feat: integrate regime detection + correlation filter into forward scanner"
```

---

## Task 5: Risk Parity Position Sizing

**Files:**
- Create: `incubator/regime/risk_parity.py`

**Why:** The Ultimate System uses portfolio-level risk parity (inverse-volatility weighting). Currently our signals all get equal weight. Adding risk parity means volatile assets (SOL) get smaller suggested sizes than stable ones (BTC).

**Step 1: Write risk parity module**

```python
"""Risk Parity Position Sizer — Inverse Volatility Weighting.

Given a set of approved signals, adjusts suggested position sizes
so that each trade contributes equal risk to the portfolio.

Usage:
    sizer = RiskParitySizer()
    sized_signals = sizer.apply_risk_parity(signals, price_data)
"""

import numpy as np
from typing import List, Dict

class RiskParitySizer:
    def __init__(self, lookback: int = 50, max_weight: float = 0.25):
        self.lookback = lookback
        self.max_weight = max_weight

    def compute_inverse_vol_weights(self, price_data: Dict[str, np.ndarray],
                                     symbols: List[str]) -> Dict[str, float]:
        """Compute inverse-volatility weights for given symbols."""
        vols = {}
        for sym in symbols:
            if sym in price_data and len(price_data[sym]) >= self.lookback:
                returns = np.diff(np.log(price_data[sym][-self.lookback:]))
                vol = np.std(returns)
                vols[sym] = vol if vol > 0 else 1e-6
            else:
                vols[sym] = 1e-6

        inv_vols = {s: 1.0 / v for s, v in vols.items()}
        total = sum(inv_vols.values())
        weights = {s: min(self.max_weight, iv / total) for s, iv in inv_vols.items()}

        # Re-normalize after capping
        total_w = sum(weights.values())
        if total_w > 0:
            weights = {s: w / total_w for s, w in weights.items()}

        return weights

    def apply_risk_parity(self, signals: List[Dict],
                          price_data: Dict[str, np.ndarray]) -> List[Dict]:
        """Add 'risk_weight' field to each signal dict."""
        symbols = list(set(s["symbol"] for s in signals))
        weights = self.compute_inverse_vol_weights(price_data, symbols)

        for sig in signals:
            sig["risk_weight"] = round(weights.get(sig["symbol"], 1.0 / len(signals)), 4)

        return signals
```

**Step 2: Self-test and commit**

```bash
python incubator/regime/risk_parity.py
git add incubator/regime/risk_parity.py
git commit -m "feat: add risk parity position sizer from Ultimate System concepts"
```

---

## Task 6: Update Dashboard + Discord Output with Regime Data

**Files:**
- Modify: `discord_freshpicks_baby.py` — add regime indicator to output
- Modify: `discord_baby_forward_test.py` — show correlation filter stats

**Step 1: Add regime emoji/tag to Discord fresh picks**

In the pick rendering, add a regime tag like `[TREND]` or `[REVERT]` next to each symbol.

**Step 2: Add filter stats footer**

```
📊 Regime: BTC=TRENDING ETH=TRENDING SOL=CHAOTIC
🔗 Correlation filter: 5 signals → 3 approved (2 correlated dupes removed)
```

**Step 3: Commit**

```bash
git add discord_freshpicks_baby.py discord_baby_forward_test.py
git commit -m "feat: show regime + correlation filter stats in Discord output"
```

---

## Task 7: Push + Restart Bot + Update Updates Page

**Step 1: Push all changes**

```bash
git stash && git pull --rebase origin main && git stash pop && git push
```

**Step 2: Restart Discord bot**

```bash
gh workflow run discord-bot.yml
```

**Step 3: Add updates/index.html entry**

Add a new update entry documenting the Ultimate Trading System integration with:
- Fractal regime detection
- Cross-asset correlation filtering
- Risk parity position sizing
- Hurst mean-reversion strategy
- Forward test performance baseline

---

## Summary of Deliverables

| # | Deliverable | Type | Dependencies |
|---|---|---|---|
| 1 | Fractal Regime Detector | New module | numpy only |
| 2 | Cross-Asset Correlation Filter | New module | numpy, pandas |
| 3 | Hurst Mean-Reversion Strategy | Baby strategy | Task 1 |
| 4 | Scanner Integration | Modification | Tasks 1, 2 |
| 5 | Risk Parity Sizer | New module | numpy |
| 6 | Discord Output Enhancement | Modification | Tasks 1, 2 |
| 7 | Deploy + Updates | Ops | All above |

**Estimated signal flow after integration:**
```
Binance Data → Strategy Signals → Regime Filter → Correlation Filter → Risk Parity → Database + Discord
```

**What this achieves:**
- Prevents 3 correlated BUY signals on BTC/ETH/SOL stacking (current problem)
- Adds regime awareness so trend strategies don't fire in mean-reverting markets
- Position-sizes by inverse volatility (SOL gets less weight than BTC)
- Adds 1 new novel strategy (Hurst mean-reversion) not found in any existing agent
- All without adding any new dependencies (numpy/pandas/requests only)
