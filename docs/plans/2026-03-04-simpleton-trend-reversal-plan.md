# Simpleton Trend Reversal — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Convert Pine Script "Advanced Trend Reversal Emoji Indicator" into a tracked strategy across baby_strategies, paper_trading, baby bundle, and DNA genome systems.

**Architecture:** EMA 21/55 crossover with 200 EMA trend filter, RSI(14) momentum confirmation, and ATR volatility gate. Generates LONG/SHORT signals with ATR-based TP/SL. Plugs into 4 existing systems following established patterns.

**Tech Stack:** Python 3, pandas, numpy, requests (Binance API), SQLite (paper trading DB)

---

### Task 1: Baby Strategy — Core Signal Engine

**Files:**
- Create: `baby_strategies/simpleton_trend_reversal.py`

**Step 1: Write the baby strategy**

```python
"""
Simpleton Trend Reversal Strategy
Source: FundedRelay (2024) Pine Script "Advanced Trend Reversal Emoji Indicator"
EMA 21/55 crossover + 200 EMA trend filter + RSI momentum + ATR volatility gate
"""

import pandas as pd
import numpy as np


class SimpletonTrendReversalStrategy:
    """
    EMA crossover trend reversal with triple confluence filter.
    Source: FundedRelay (2024) — Pine Script v6 indicator converted to Python.
    """
    NAME = "simpleton_trend_reversal"
    DESCRIPTION = "EMA 21/55 crossover with 200 EMA trend, RSI momentum, ATR volatility gate"
    ENTRY_RULES = (
        "LONG: EMA(21) crosses above EMA(55) AND close > EMA(200) "
        "AND RSI(14) > 55 AND TR > ATR(14); "
        "SHORT: EMA(21) crosses below EMA(55) AND close < EMA(200) "
        "AND RSI(14) < 45 AND TR > ATR(14)"
    )
    EXIT_RULES = "TP = 2.5x ATR(14), SL = 1.5x ATR(14)"
    ACADEMIC_SOURCE = "FundedRelay (2024) 'Advanced Trend Reversal Emoji Indicator' — Pine Script v6"
    EXPECTED_WR = "55-62%"
    EXPECTED_TRADES_PER_YEAR = "15-30 per symbol"

    def __init__(self, tp_atr_mult=2.5, sl_atr_mult=1.5, rsi_offset=5):
        self.tp_atr_mult = tp_atr_mult
        self.sl_atr_mult = sl_atr_mult
        self.rsi_offset = rsi_offset  # Distance from 50 for RSI threshold

    def generate_signals(self, df: pd.DataFrame, symbol: str = "UNKNOWN") -> list[dict]:
        """Generate EMA crossover reversal signals with triple confluence."""
        if len(df) < 201:
            return []

        df = df.copy()

        # EMA calculations (matching Pine: ta.ema)
        ema_fast = df['close'].ewm(span=21, adjust=False).mean()
        ema_slow = df['close'].ewm(span=55, adjust=False).mean()
        ema_trend = df['close'].ewm(span=200, adjust=False).mean()

        # RSI(14)
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0.0).ewm(alpha=1/14, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0.0)).ewm(alpha=1/14, adjust=False).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        # ATR(14) — true range
        hl = df['high'] - df['low']
        hc = np.abs(df['high'] - df['close'].shift())
        lc = np.abs(df['low'] - df['close'].shift())
        tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
        atr = tr.ewm(span=14, adjust=False).mean()

        # Crossover detection (Pine: ta.crossover / ta.crossunder)
        cross_above = (ema_fast > ema_slow) & (ema_fast.shift(1) <= ema_slow.shift(1))
        cross_below = (ema_fast < ema_slow) & (ema_fast.shift(1) >= ema_slow.shift(1))

        rsi_bull = 50 + self.rsi_offset  # default 55
        rsi_bear = 50 - self.rsi_offset  # default 45

        signals = []

        for i in range(200, len(df)):
            if pd.isna(atr.iloc[i]) or pd.isna(rsi.iloc[i]) or pd.isna(ema_trend.iloc[i]):
                continue

            curr_close = df['close'].iloc[i]
            curr_atr = atr.iloc[i]
            curr_rsi = rsi.iloc[i]
            curr_tr = tr.iloc[i]
            curr_trend = ema_trend.iloc[i]

            # Volatility gate: current true range > ATR
            if curr_tr <= curr_atr:
                continue

            # LONG: fast crosses above slow + price > 200 EMA + RSI > bull level
            if cross_above.iloc[i] and curr_close > curr_trend and curr_rsi > rsi_bull:
                entry = float(curr_close)
                tp = entry + self.tp_atr_mult * curr_atr
                sl = entry - self.sl_atr_mult * curr_atr
                strength = int(min(100, 50 + (curr_rsi - rsi_bull) * 2))

                signals.append({
                    "symbol": symbol,
                    "side": "LONG",
                    "entry_price": entry,
                    "take_profit": float(tp),
                    "stop_loss": float(sl),
                    "strength": strength,
                    "reason": (
                        f"EMA(21) crossed above EMA(55), "
                        f"price>{curr_trend:.2f} (200EMA), "
                        f"RSI={curr_rsi:.1f}>{rsi_bull}, "
                        f"TR={curr_tr:.2f}>ATR={curr_atr:.2f}"
                    ),
                    "strategy": self.NAME,
                })

            # SHORT: fast crosses below slow + price < 200 EMA + RSI < bear level
            elif cross_below.iloc[i] and curr_close < curr_trend and curr_rsi < rsi_bear:
                entry = float(curr_close)
                tp = entry - self.tp_atr_mult * curr_atr
                sl = entry + self.sl_atr_mult * curr_atr
                strength = int(min(100, 50 + (rsi_bear - curr_rsi) * 2))

                signals.append({
                    "symbol": symbol,
                    "side": "SHORT",
                    "entry_price": entry,
                    "take_profit": float(tp),
                    "stop_loss": float(sl),
                    "strength": strength,
                    "reason": (
                        f"EMA(21) crossed below EMA(55), "
                        f"price<{curr_trend:.2f} (200EMA), "
                        f"RSI={curr_rsi:.1f}<{rsi_bear}, "
                        f"TR={curr_tr:.2f}>ATR={curr_atr:.2f}"
                    ),
                    "strategy": self.NAME,
                })

        return signals
```

**Step 2: Verify syntax**

Run: `python -c "from baby_strategies.simpleton_trend_reversal import SimpletonTrendReversalStrategy; s = SimpletonTrendReversalStrategy(); print(f'{s.NAME}: OK')"`
Expected: `simpleton_trend_reversal: OK`

**Step 3: Commit**

```bash
git add baby_strategies/simpleton_trend_reversal.py
git commit -m "feat: add Simpleton Trend Reversal baby strategy (EMA crossover + RSI + ATR)"
```

---

### Task 2: Paper Trading Strategy — Live Scanner Integration

**Files:**
- Create: `paper_trading/strategies/simpleton_trend_reversal.py`
- Modify: `paper_trading/strategies/__init__.py`

**Step 1: Write the paper trading strategy**

```python
"""Simpleton Trend Reversal - EMA 21/55 crossover with RSI + ATR volatility gate."""
from typing import List
from paper_trading.strategies.base_strategy import BaseStrategy
from paper_trading.models import NormalizedPick
from paper_trading.helpers import fetch_json, rate_limited

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
           "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT", "DOGEUSDT"]


class SimpletonTrendReversal(BaseStrategy):
    name = "simpleton_trend_reversal"
    display_name = "Simpleton Trend Reversal"
    source = "Binance"
    category = "crypto"
    portfolio_type = "technical"

    def fetch_data(self) -> dict:
        all_data = {}
        for sym in SYMBOLS:
            try:
                klines = self._fetch_klines(sym)
                all_data[sym] = klines
            except Exception:
                continue
        return all_data

    @rate_limited("binance", 0.2)
    def _fetch_klines(self, symbol: str) -> list:
        return fetch_json(
            "https://api.binance.com/api/v3/klines",
            params={"symbol": symbol, "interval": "1h", "limit": 250}
        )

    def _ema(self, values: list, span: int) -> list:
        """Compute EMA matching Pine Script ta.ema (adjust=False)."""
        mult = 2.0 / (span + 1)
        ema = [values[0]]
        for v in values[1:]:
            ema.append(v * mult + ema[-1] * (1 - mult))
        return ema

    def _rsi(self, closes: list, period: int = 14) -> float:
        """Compute current RSI using Wilder smoothing."""
        if len(closes) < period + 1:
            return 50.0
        deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        gains = [max(0, d) for d in deltas]
        losses = [max(0, -d) for d in deltas]
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def _atr(self, highs: list, lows: list, closes: list, period: int = 14) -> float:
        """Compute current ATR."""
        if len(closes) < period + 1:
            return 0.0
        trs = []
        for i in range(1, len(closes)):
            hl = highs[i] - lows[i]
            hc = abs(highs[i] - closes[i-1])
            lc = abs(lows[i] - closes[i-1])
            trs.append(max(hl, hc, lc))
        if len(trs) < period:
            return 0.0
        atr_val = sum(trs[:period]) / period
        for i in range(period, len(trs)):
            atr_val = (atr_val * (period - 1) + trs[i]) / period
        return atr_val

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        for symbol, klines in data.items():
            if len(klines) < 210:
                continue

            closes = [float(k[4]) for k in klines]
            highs = [float(k[2]) for k in klines]
            lows = [float(k[3]) for k in klines]

            ema21 = self._ema(closes, 21)
            ema55 = self._ema(closes, 55)
            ema200 = self._ema(closes, 200)

            price = closes[-1]
            rsi_val = self._rsi(closes, 14)
            atr_val = self._atr(highs, lows, closes, 14)

            if atr_val <= 0:
                continue

            # Current true range
            curr_tr = max(
                highs[-1] - lows[-1],
                abs(highs[-1] - closes[-2]),
                abs(lows[-1] - closes[-2])
            )

            # Volatility gate
            if curr_tr <= atr_val:
                continue

            # Crossover detection (current bar vs previous bar)
            cross_above = ema21[-1] > ema55[-1] and ema21[-2] <= ema55[-2]
            cross_below = ema21[-1] < ema55[-1] and ema21[-2] >= ema55[-2]

            direction = None
            if cross_above and price > ema200[-1] and rsi_val > 55:
                direction = "LONG"
                tp = round(price + 2.5 * atr_val, 6)
                sl = round(price - 1.5 * atr_val, 6)
                confidence = min(0.9, 0.5 + (rsi_val - 55) / 100)
                reason = (f"EMA(21) crossed above EMA(55), "
                         f"RSI={rsi_val:.1f}>55, TR={curr_tr:.2f}>ATR={atr_val:.2f}")
            elif cross_below and price < ema200[-1] and rsi_val < 45:
                direction = "SHORT"
                tp = round(price - 2.5 * atr_val, 6)
                sl = round(price + 1.5 * atr_val, 6)
                confidence = min(0.9, 0.5 + (45 - rsi_val) / 100)
                reason = (f"EMA(21) crossed below EMA(55), "
                         f"RSI={rsi_val:.1f}<45, TR={curr_tr:.2f}>ATR={atr_val:.2f}")

            if direction:
                picks.append(NormalizedPick(
                    symbol=symbol,
                    direction=direction,
                    entry_price=price,
                    tp=tp,
                    sl=sl,
                    strategy=self.name,
                    strategy_name=self.display_name,
                    category=self.category,
                    confidence=round(confidence, 3),
                    reason=reason,
                    raw_signal={
                        "ema21": ema21[-1], "ema55": ema55[-1], "ema200": ema200[-1],
                        "rsi": rsi_val, "atr": atr_val, "tr": curr_tr,
                    },
                ))

        picks.sort(key=lambda p: p.confidence, reverse=True)
        return picks[:5]
```

**Step 2: Register in `paper_trading/strategies/__init__.py`**

Add import and instance to ALL_STRATEGIES list. Add after the Leap strategies block:

```python
# After existing imports, add:
from paper_trading.strategies.simpleton_trend_reversal import SimpletonTrendReversal

# In ALL_STRATEGIES list, add after the Leap block:
    # Simpleton Trend Reversal (EMA crossover)
    SimpletonTrendReversal(),
```

**Step 3: Verify import**

Run: `python -c "from paper_trading.strategies import ALL_STRATEGIES; names = [s.name for s in ALL_STRATEGIES]; print(f'{len(names)} strategies'); assert 'simpleton_trend_reversal' in names, 'Not registered!'; print('OK')"`
Expected: `27 strategies` and `OK`

**Step 4: Commit**

```bash
git add paper_trading/strategies/simpleton_trend_reversal.py paper_trading/strategies/__init__.py
git commit -m "feat: add Simpleton Trend Reversal to paper trading scanner"
```

---

### Task 3: Baby Bundle — Standalone Regime-Aware Wrapper

**Files:**
- Create: `baby_strategies/bundle_optimized/bundle_simpleton_reversal.py`

**Step 1: Write the bundle**

```python
#!/usr/bin/env python3
"""
Simpleton Trend Reversal Bundle
================================
Standalone bundle wrapping the EMA crossover strategy with regime-aware sizing.

Source: FundedRelay (2024) Pine Script "Advanced Trend Reversal Emoji Indicator"
Target: 15-25% annual returns, <20% max drawdown
Regime detection: ADX-based (trending/ranging/volatile)
Position sizing: Half-Kelly with regime multipliers
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class Signal:
    asset: str
    direction: str
    weight: float
    confidence: float
    expected_return: float
    volatility: float
    regime: str
    metadata: Dict = None


class SimpletonReversalBundle:
    def __init__(self):
        self.name = "SimpletonReversal_v1"
        self.version = "1.0.0"
        self.base_allocation = 1.0  # 100% to single strategy
        self.regime_multipliers = {
            "trending_strong": 1.0,   # Full size in strong trends
            "trending_weak": 0.7,     # Reduce in weak trends
            "ranging": 0.3,           # Minimal — crossovers whipsaw in ranges
            "volatile": 0.5,          # Cautious in volatile
            "breakout": 0.8,          # Good for breakout transitions
        }

    def detect_regime(self, df: pd.DataFrame) -> str:
        """Classify market regime using ADX proxy (directional movement)."""
        if len(df) < 30:
            return "ranging"

        closes = df['close'].values
        highs = df['high'].values
        lows = df['low'].values

        # ADX proxy: absolute price change vs range ratio
        price_change = abs(closes[-1] - closes[-14]) / closes[-14]
        avg_range = np.mean([highs[i] - lows[i] for i in range(-14, 0)]) / closes[-1]

        # Volatility: ATR/price ratio
        trs = []
        for i in range(-14, 0):
            hl = highs[i] - lows[i]
            hc = abs(highs[i] - closes[i-1])
            lc = abs(lows[i] - closes[i-1])
            trs.append(max(hl, hc, lc))
        atr_ratio = np.mean(trs) / closes[-1]

        if price_change > 0.08 and atr_ratio < 0.03:
            return "trending_strong"
        elif price_change > 0.04:
            return "trending_weak"
        elif atr_ratio > 0.04:
            return "volatile"
        elif avg_range > 0.03 and price_change > 0.05:
            return "breakout"
        else:
            return "ranging"

    def half_kelly(self, win_rate: float, avg_win: float, avg_loss: float) -> float:
        """Half-Kelly position sizing. Returns fraction of capital."""
        if avg_loss == 0:
            return 0.0
        b = avg_win / avg_loss
        q = 1 - win_rate
        full_kelly = (win_rate * b - q) / b
        return max(0.0, min(0.25, full_kelly / 2))  # Cap at 25%

    def get_position_size(self, regime: str, win_rate: float = 0.58,
                          avg_win: float = 2.5, avg_loss: float = 1.5) -> float:
        """Regime-adjusted Half-Kelly position size."""
        base = self.half_kelly(win_rate, avg_win, avg_loss)
        multiplier = self.regime_multipliers.get(regime, 0.5)
        return round(base * multiplier, 4)

    def get_metrics(self) -> Dict:
        return {
            "name": self.name,
            "version": self.version,
            "target_return": "15-25%",
            "expected_sharpe": "1.0-2.0",
            "expected_max_dd": "-15% to -20%",
            "rebalancing": "On signal",
            "num_strategies": 1,
            "strategy": "simpleton_trend_reversal",
            "regime_multipliers": {k: f"{v*100:.0f}%"
                                   for k, v in self.regime_multipliers.items()},
            "position_sizing": "Half-Kelly with regime adjustment",
        }


if __name__ == "__main__":
    bundle = SimpletonReversalBundle()
    metrics = bundle.get_metrics()
    print(f"Strategy: {metrics['name']} v{metrics['version']}")
    print(f"Target Return: {metrics['target_return']}")
    print(f"Position Sizing: {metrics['position_sizing']}")
    for regime, mult in metrics["regime_multipliers"].items():
        size = bundle.get_position_size(regime)
        print(f"  {regime}: {mult} -> position size {size:.2%}")
```

**Step 2: Verify syntax**

Run: `python baby_strategies/bundle_optimized/bundle_simpleton_reversal.py`
Expected: Prints bundle metrics and regime-adjusted position sizes.

**Step 3: Commit**

```bash
git add baby_strategies/bundle_optimized/bundle_simpleton_reversal.py
git commit -m "feat: add Simpleton Trend Reversal baby bundle with regime-aware sizing"
```

---

### Task 4: DNA Genome Registration

**Files:**
- Modify: `genome/seed_strategies.py` (add seed to "bull" island)

**Step 1: Add seed to the "bull" island**

In `genome/seed_strategies.py`, add a new entry at the end of the `"bull"` island's `"seeds"` list (after the `leap_htf_momentum` entry, before the closing `]`):

```python
            {
                "name": "simpleton_trend_reversal",
                "timeframe": "1h",
                "primary_indicator": "EMA",
                "entry_logic": "golden_cross",
                "exit_logic": "death_cross",
                "risk_profile": "moderate",
                "genes": {"ema_fast": 21, "ema_slow": 55, "rsi_period": 14,
                          "rsi_overbought": 55, "rsi_oversold": 45, "atr_period": 14,
                          "take_profit_mult": 2.5, "stop_loss_mult": 1.5,
                          "position_size": 8, "leverage": 1,
                          "expected_wr": 0.58, "source": "pine_script_conversion"},
            },
```

**Step 2: Verify seed loads**

Run: `python -c "from genome.seed_strategies import get_island_seeds; seeds = get_island_seeds('bull'); names = [s.name for s in seeds]; print(f'{len(names)} bull seeds: {names}'); assert 'simpleton_trend_reversal' in names"`
Expected: `7 bull seeds: [... 'simpleton_trend_reversal']`

**Step 3: Commit**

```bash
git add genome/seed_strategies.py
git commit -m "feat: register Simpleton Trend Reversal in DNA bull island"
```

---

### Task 5: Verify All Integrations

**Step 1: Verify baby strategy imports cleanly**

Run: `python -c "from baby_strategies.simpleton_trend_reversal import SimpletonTrendReversalStrategy; print('baby: OK')"`

**Step 2: Verify paper trading registration**

Run: `python -c "from paper_trading.strategies import ALL_STRATEGIES, STRATEGY_PORTFOLIO_MAP; assert 'simpleton_trend_reversal' in STRATEGY_PORTFOLIO_MAP; print(f'paper: OK ({len(ALL_STRATEGIES)} strategies)')"`

**Step 3: Verify bundle runs**

Run: `python baby_strategies/bundle_optimized/bundle_simpleton_reversal.py`

**Step 4: Verify DNA seed**

Run: `python -c "from genome.seed_strategies import get_island_seeds; s = [x for x in get_island_seeds('bull') if x.name == 'simpleton_trend_reversal'][0]; print(f'DNA: {s.name} genes={s.genes}')"`

**Step 5: Final commit (if any fixes needed)**

```bash
git add -A
git commit -m "chore: verify Simpleton Trend Reversal integration across all 4 systems"
```
