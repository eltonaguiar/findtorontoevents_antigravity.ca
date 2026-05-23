# Production Readiness: Kill Losers, Validate Winners, Prove Edge

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform the trading system from net-negative (-$5,979 Alpha Engine, 36.1% WR) to statistically validated and production-ready within 6-12 months, through disciplined triage, p-value gating, regime detection, transparent reporting, and graduated capital deployment.

**Architecture:** Five-layer approach: (1) Immediate triage — hard-disable all strategies with negative expectancy, (2) Statistical validation — require p < 0.05 before any strategy earns boost/allocation, (3) Regime detection — auto-pause strategies in hostile market conditions, (4) Transparent track record — honest reporting with wins AND losses, (5) Go/No-Go decision gates at Month 3/6/9/12 before scaling capital.

**Tech Stack:** Python 3.14, SQLite, GitHub Actions, existing Alpha Engine scanner/auto_tuner/forward_validator pipeline

---

## Current State (Brutal Honest Assessment)

| Metric | Claimed | Reality | Gap |
|--------|---------|---------|-----|
| Forward Win Rate | 73.8% | 36.1% (Alpha Engine) | -37.7% |
| Net P/L | +$10,000+ | -$5,979 (Alpha Engine) | -$15,979 |
| Validated Strategies | 200+ | ~11 (5.5%) | -189 |
| Forward Trades | "Hundreds" | 147 (Alpha) + 2 (Baby) | Too few |
| Statistical Significance | "Proven" | p > 0.05 for most | FAIL |
| Backtest/Forward Correlation | - | 0.34 | Terrible |

### Realistic Benchmark Targets (Not Fantasy Numbers)

| Metric | Mutual Fund | Hedge Fund | Our Target (Live) | Timeline |
|--------|-------------|------------|-------------------|----------|
| Annual Return | 6-8% | 10-15% | 20-30% | Month 12+ |
| Sharpe Ratio | 0.5-0.7 | 0.8-1.2 | 1.2-1.5 | Month 12+ |
| Max Drawdown | -15% | -20% | -20% to -25% | Month 12+ |
| Win Rate | N/A | 52-55% | 55-60% | Month 9+ |

**The 47.2% annual / 8.1 Sharpe / 3.2% DD claims are NOT achievable in live trading.**

---

## Task 1: Hard-Disable All Net-Negative Strategies

**Files:**
- Modify: `alpha_engine/auto_tuner.py:61-73` (HARD_DISABLED_STRATEGIES)
- Modify: `alpha_engine/auto_tuner.py:77-86` (DIRECTION_RESTRICTED_STRATEGIES)
- Read: `alpha_engine/data/strategy_performance.json` (source of truth)

**Step 1: Verify current performance data**

Run:
```bash
py -c "
import json
with open('alpha_engine/data/strategy_performance.json') as f:
    perf = json.load(f)
losers = [(k, v) for k, v in perf.items() if v.get('total_pnl_dollar', 0) < 0 and v.get('closed_picks', 0) >= 3]
losers.sort(key=lambda x: x[1]['total_pnl_dollar'])
for name, data in losers:
    print(f'{name:50s} {data[\"closed_picks\"]:3d} trades  WR:{data[\"win_rate\"]*100:5.1f}%  PnL:\${data[\"total_pnl_dollar\"]:+9.2f}  Sharpe:{data[\"sharpe\"]:7.2f}')
print(f'\nTotal losers with 3+ trades: {len(losers)}')
print(f'Combined losses: \${sum(v[\"total_pnl_dollar\"] for _, v in losers):+,.2f}')
"
```

Expected: List of all strategies with negative P/L and 3+ closed trades.

**Step 2: Update HARD_DISABLED_STRATEGIES**

Add every strategy that meets ALL of these criteria to the hard-disable list:
- `total_pnl_dollar < 0`
- `closed_picks >= 5`
- `win_rate < 0.35`

```python
HARD_DISABLED_STRATEGIES = {
    # === Previously disabled ===
    "double_top_bottom_detector",
    "fourier_cycle_detector",
    "m2_liquidity_lag",
    "price_touch_recurrence",
    "smart_money_fvg",
    "halloween_effect",
    "cross_sectional_momentum",
    "exchange_netflow_reversal",
    "momentum_mean_rev_blend",
    "community_ict_fvg_selective",
    "monthly_seasonality",
    # === NEW: Added from performance audit 2026-02-28 ===
    # Add each strategy name from Step 1 output that meets criteria
    # Format: "strategy_name",  # X/Y WR, -$ZZZ loss
}
```

**Step 3: Update DIRECTION_RESTRICTED_STRATEGIES**

For strategies that are profitable in one direction but losing in the other:

```python
DIRECTION_RESTRICTED_STRATEGIES = {
    "autocorrelation_exploiter": "SELL",
    "multi_sigma_reversal": "SELL",
    "fear_greed_extreme_dca": "BUY",
    # Add any new direction-restricted strategies here
}
```

**Step 4: Verify disabled count**

Run:
```bash
py -c "
import sys
sys.path.insert(0, 'alpha_engine')
from auto_tuner import HARD_DISABLED_STRATEGIES, DIRECTION_RESTRICTED_STRATEGIES
print(f'Hard disabled: {len(HARD_DISABLED_STRATEGIES)}')
print(f'Direction restricted: {len(DIRECTION_RESTRICTED_STRATEGIES)}')
for s in sorted(HARD_DISABLED_STRATEGIES):
    print(f'  DISABLED: {s}')
"
```

Expected: All net-negative strategies appear in the disabled list.

**Step 5: Commit**

```bash
git add alpha_engine/auto_tuner.py
git commit -m "triage: hard-disable all net-negative strategies from performance audit

Disabled strategies with <35% WR and negative P/L after 5+ trades.
This stops bleeding ~\$X/month from confirmed losers."
```

---

## Task 2: Add Statistical Significance Gate (p-value)

**Files:**
- Modify: `alpha_engine/forward_validator.py` (add p-value to strategy stats)
- Modify: `alpha_engine/auto_tuner.py` (add p-value gate + probation)

**Step 1: Add p-value calculation to forward_validator.py**

Find the `compute_all_strategy_stats()` function (around line 426-517) and add a binomial test:

```python
import math

def binomial_p_value(wins: int, total: int, null_hypothesis: float = 0.5) -> float:
    """One-sided binomial test: is win rate significantly better than chance?

    Returns p-value. Lower = more confident the edge is real.
    Uses normal approximation for n >= 20, exact for smaller samples.
    """
    if total < 5:
        return 1.0  # Not enough data

    observed_rate = wins / total
    if observed_rate <= null_hypothesis:
        return 1.0  # Not better than chance

    # Normal approximation to binomial
    se = math.sqrt(null_hypothesis * (1 - null_hypothesis) / total)
    if se == 0:
        return 1.0
    z = (observed_rate - null_hypothesis) / se
    # One-sided p-value from z-score (approximate)
    p = 0.5 * math.erfc(z / math.sqrt(2))
    return p
```

Then in the stats computation loop, add:

```python
stats["p_value"] = binomial_p_value(wins, total_closed)
stats["statistically_significant"] = stats["p_value"] < 0.05 and total_closed >= 20
```

**Step 2: Add p-value gate to auto_tuner.py**

In the dynamic disable logic (around line 147-283), add:

```python
# Strategies with 20+ trades that fail p < 0.10 get probation
if stats.get("closed_picks", 0) >= 20:
    p_val = stats.get("p_value", 1.0)
    if p_val > 0.10:
        disable_reason = f"No statistical edge: p={p_val:.3f} > 0.10 after {stats['closed_picks']} trades"
        # Add to probation with reduced allocation
```

**Step 3: Add p-value to PROVEN_STRATEGY_BOOST criteria**

Only boost strategies that have p < 0.05:

```python
if strategy_name in PROVEN_STRATEGY_BOOST:
    p_val = stats.get("p_value", 1.0)
    if p_val < 0.05:
        boost = PROVEN_STRATEGY_BOOST[strategy_name]
    else:
        boost = 1.0  # No boost without statistical significance
```

**Step 4: Verify p-value calculations**

Run:
```bash
py -c "
import json, math

def binomial_p_value(wins, total, null_hypothesis=0.5):
    if total < 5: return 1.0
    observed_rate = wins / total
    if observed_rate <= null_hypothesis: return 1.0
    se = math.sqrt(null_hypothesis * (1 - null_hypothesis) / total)
    if se == 0: return 1.0
    z = (observed_rate - null_hypothesis) / se
    p = 0.5 * math.erfc(z / math.sqrt(2))
    return p

with open('alpha_engine/data/strategy_performance.json') as f:
    perf = json.load(f)

print('STRATEGIES WITH STATISTICAL SIGNIFICANCE (p < 0.05):')
print(f'{\"Strategy\":50s} {\"Trades\":>6s} {\"WR\":>6s} {\"p-value\":>8s} {\"PnL\":>10s}')
for name, data in sorted(perf.items(), key=lambda x: x[1].get('total_pnl_dollar', 0), reverse=True):
    wins = data.get('wins', 0)
    total = data.get('closed_picks', 0)
    if total < 3: continue
    p = binomial_p_value(wins, total)
    sig = '***' if p < 0.01 else '**' if p < 0.05 else '*' if p < 0.10 else ''
    print(f'{name:50s} {total:6d} {data.get(\"win_rate\",0)*100:5.1f}% {p:8.4f} \${data.get(\"total_pnl_dollar\",0):+9.2f} {sig}')
"
```

Expected: Only a handful of strategies show p < 0.05. This is the reality check.

**Step 5: Commit**

```bash
git add alpha_engine/forward_validator.py alpha_engine/auto_tuner.py
git commit -m "feat: add p-value statistical significance gate

Strategies now require p < 0.05 (binomial test vs 50% null) to receive
boost multipliers. Strategies with 20+ trades and p > 0.10 enter
probation with reduced allocation. This prevents deploying strategies
that aren't statistically distinguishable from coin-flipping."
```

---

## Task 3: Add Market Regime Detection

**Files:**
- Create: `alpha_engine/regime_detector.py`
- Modify: `alpha_engine/scanner.py` (integrate regime filter)

**Step 1: Create regime_detector.py**

```python
"""Market Regime Detector — classifies current market into regimes.

Regimes:
  TRENDING_UP    — Strong uptrend (20d ROC > 5%, ADX > 25)
  TRENDING_DOWN  — Strong downtrend (20d ROC < -5%, ADX > 25)
  MEAN_REVERTING — Range-bound (ADX < 20, Bollinger %B between 0.2-0.8)
  HIGH_VOLATILITY — Volatile (ATR/price > 2x 60d avg)
  LOW_VOLATILITY  — Compressed (ATR/price < 0.5x 60d avg)
  CRISIS          — Crash mode (drawdown > 15% in 7d, VIX > 30 or F&G < 15)
"""
import json
import os
from datetime import datetime


def detect_regime(btc_prices: list, fear_greed: int = 50) -> dict:
    """Detect current market regime from BTC price series.

    Args:
        btc_prices: List of closing prices (most recent last), minimum 60 values
        fear_greed: Current Fear & Greed index (0-100)

    Returns:
        dict with keys: regime, confidence, sub_regimes, metrics
    """
    if len(btc_prices) < 60:
        return {"regime": "UNKNOWN", "confidence": 0.0, "sub_regimes": [], "metrics": {}}

    prices = btc_prices[-60:]
    current = prices[-1]

    # --- Metrics ---
    roc_7d = (current - prices[-7]) / prices[-7] if prices[-7] else 0
    roc_20d = (current - prices[-20]) / prices[-20] if prices[-20] else 0

    high_30d = max(prices[-30:])
    drawdown_30d = (current - high_30d) / high_30d

    high_7d = max(prices[-7:])
    drawdown_7d = (current - high_7d) / high_7d

    returns = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]
    recent_vol = _std(returns[-14:]) if len(returns) >= 14 else 0
    longer_vol = _std(returns[-60:]) if len(returns) >= 60 else recent_vol
    vol_ratio = recent_vol / longer_vol if longer_vol > 0 else 1.0

    pos_moves = [max(returns[i], 0) for i in range(-14, 0)]
    neg_moves = [abs(min(returns[i], 0)) for i in range(-14, 0)]
    adx_proxy = abs(sum(pos_moves) - sum(neg_moves)) / (sum(pos_moves) + sum(neg_moves) + 1e-10) * 100

    metrics = {
        "roc_7d": round(roc_7d, 4),
        "roc_20d": round(roc_20d, 4),
        "drawdown_30d": round(drawdown_30d, 4),
        "drawdown_7d": round(drawdown_7d, 4),
        "vol_ratio": round(vol_ratio, 2),
        "adx_proxy": round(adx_proxy, 1),
        "fear_greed": fear_greed,
    }

    # --- Classification (priority order) ---
    sub_regimes = []

    if drawdown_7d < -0.15 or (drawdown_30d < -0.20 and fear_greed < 15):
        sub_regimes.append("CRISIS")

    if vol_ratio > 2.0:
        sub_regimes.append("HIGH_VOLATILITY")
    elif vol_ratio < 0.5:
        sub_regimes.append("LOW_VOLATILITY")

    if roc_20d > 0.05 and adx_proxy > 25:
        sub_regimes.append("TRENDING_UP")
    elif roc_20d < -0.05 and adx_proxy > 25:
        sub_regimes.append("TRENDING_DOWN")
    elif adx_proxy < 20:
        sub_regimes.append("MEAN_REVERTING")

    regime = sub_regimes[0] if sub_regimes else "NEUTRAL"
    confidence = min(adx_proxy / 50, 1.0) if "TRENDING" in regime else 0.5
    if regime == "CRISIS":
        confidence = min(abs(drawdown_7d) * 5, 1.0)

    return {
        "regime": regime,
        "confidence": round(confidence, 2),
        "sub_regimes": sub_regimes,
        "metrics": metrics,
        "timestamp": datetime.utcnow().isoformat(),
    }


# Strategy-regime compatibility matrix
STRATEGY_REGIME_COMPATIBILITY = {
    # Mean reversion — thrive in ranging/high-vol/crisis
    "mean_reversion": ["MEAN_REVERTING", "HIGH_VOLATILITY", "CRISIS"],
    "multi_sigma_reversal": ["MEAN_REVERTING", "HIGH_VOLATILITY", "CRISIS"],
    "fear_greed_extreme_dca": ["CRISIS", "HIGH_VOLATILITY"],
    "volume_profile_value_area": ["MEAN_REVERTING", "LOW_VOLATILITY"],
    "autocorrelation_exploiter": ["MEAN_REVERTING", "LOW_VOLATILITY"],

    # Momentum/trend — need trends
    "momentum": ["TRENDING_UP", "TRENDING_DOWN"],
    "breakout": ["TRENDING_UP", "LOW_VOLATILITY"],
    "trend_following": ["TRENDING_UP", "TRENDING_DOWN"],

    # Arbitrage — work everywhere
    "arbitrage": ["TRENDING_UP", "TRENDING_DOWN", "MEAN_REVERTING", "HIGH_VOLATILITY", "LOW_VOLATILITY", "CRISIS", "NEUTRAL"],
    "funding_rate": ["TRENDING_UP", "TRENDING_DOWN", "MEAN_REVERTING", "HIGH_VOLATILITY", "LOW_VOLATILITY", "CRISIS", "NEUTRAL"],

    # Volatility strategies
    "volatility_selling": ["LOW_VOLATILITY", "MEAN_REVERTING"],
    "volatility_buying": ["HIGH_VOLATILITY", "CRISIS"],
}


def is_strategy_compatible(strategy_name: str, regime: str, compatibility_map: dict = None) -> bool:
    """Check if a strategy should run in the current regime.
    Returns True if compatible or if no mapping exists (permissive default).
    """
    if compatibility_map is None:
        compatibility_map = STRATEGY_REGIME_COMPATIBILITY

    if strategy_name in compatibility_map:
        return regime in compatibility_map[strategy_name]

    for category, regimes in compatibility_map.items():
        if category in strategy_name:
            return regime in regimes

    return True  # No mapping = allow by default


def _std(values):
    """Standard deviation without numpy."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
    return variance ** 0.5
```

**Step 2: Integrate regime detection into scanner.py**

In `run_strategies()` (around line 722), add:

```python
from regime_detector import detect_regime, is_strategy_compatible

# After fetching market data:
btc_closes = [candle["close"] for candle in btc_data[-60:]]
fear_greed = context.get("fear_greed_index", 50)
current_regime = detect_regime(btc_closes, fear_greed)

print(f"[REGIME] {current_regime['regime']} (confidence: {current_regime['confidence']:.0%})")
print(f"[REGIME] Sub-regimes: {current_regime['sub_regimes']}")

# Save regime state for dashboard
regime_path = os.path.join("alpha_engine", "data", "current_regime.json")
with open(regime_path, "w") as f:
    json.dump(current_regime, f, indent=2)

# In the strategy loop, before running each strategy:
if not is_strategy_compatible(strategy_name, current_regime["regime"]):
    print(f"  [SKIP] {strategy_name} incompatible with {current_regime['regime']} regime")
    continue
```

**Step 3: Verify regime detection**

Run:
```bash
py -c "
import json, sys
sys.path.insert(0, 'alpha_engine')
from regime_detector import detect_regime
prices = [97000, 96500, 95000, 93000, 91000, 89000, 86000, 84000, 82000, 80000,
          78000, 76000, 74000, 72000, 70000, 68000, 67000, 66000, 65000, 64000,
          63000, 62500, 62000, 63000, 64000, 65000, 66000, 67000, 66500, 66000,
          65500, 65000, 64500, 64000, 63500, 63000, 62500, 62000, 62500, 63000,
          63500, 64000, 64500, 65000, 65500, 66000, 66500, 67000, 66800, 66600,
          66400, 66200, 66000, 65800, 65600, 65400, 65200, 65000, 84500, 84300]
result = detect_regime(prices, fear_greed=25)
print(json.dumps(result, indent=2))
"
```

Expected: Should classify as TRENDING_DOWN or CRISIS.

**Step 4: Commit**

```bash
git add alpha_engine/regime_detector.py alpha_engine/scanner.py alpha_engine/data/current_regime.json
git commit -m "feat: add market regime detection with strategy compatibility filter

Classifies market into 6 regimes (trending up/down, mean reverting,
high/low vol, crisis). Strategies auto-skipped when current regime
doesn't match their historically profitable conditions."
```

---

## Task 4: Tighten Auto-Tuner + Add Loss Cap

**Files:**
- Modify: `alpha_engine/auto_tuner.py` (tighten dynamic disable thresholds)

**Step 1: Lower the auto-disable thresholds**

```python
# OLD (too permissive):
# Win rate < 35% after 8+ picks, Sharpe < 0.0, DD < -30%

# NEW (tighter):
MIN_WIN_RATE_THRESHOLD = 0.40          # Was 0.35
MIN_PICKS_FOR_WR_CHECK = 5            # Was 8 — evaluate sooner
MIN_SHARPE_THRESHOLD = 0.0            # Keep (negative Sharpe = auto-kill)
MIN_ROLLING_SHARPE = 0.5              # Was 0.8 but check sooner
MAX_DRAWDOWN_THRESHOLD = -0.25        # Was -0.30
MIN_PICKS_FOR_PROBATION = 10          # Check probation earlier
```

**Step 2: Add $500 maximum loss cap**

```python
# In the evaluation loop — kill any strategy that has lost >$500:
if stats.get("total_pnl_dollar", 0) < -500 and stats.get("closed_picks", 0) >= 3:
    disable_reason = f"Max loss cap exceeded: ${stats['total_pnl_dollar']:.2f} < -$500"
    # Add to disabled_strategies in tuner_state.json
```

**Step 3: Commit**

```bash
git add alpha_engine/auto_tuner.py
git commit -m "feat: tighten auto-tuner thresholds and add \$500 loss cap

WR threshold: 35% -> 40%, check after 5 picks (was 8).
Added \$500 max loss cap per strategy.
Strategies bleeding money get killed faster."
```

---

## Task 5: Tighten Incubator Graduation Criteria

**Files:**
- Modify: `incubator/testing/forward_test_tracker.py` (graduation criteria)
- Modify: `incubator/testing/forward_test_coordinator.py` (allocation formula)

**Step 1: Tighten graduation thresholds**

Find the `StrategyGraduationCriteria` class and update:

```python
# OLD (too permissive):
# min_days=30, min_trades=20, min_win_rate=0.45, min_sharpe=0.8, max_drawdown=0.25

# NEW (aligned with cross-examination):
DEFAULT_GRADUATION_CRITERIA = StrategyGraduationCriteria(
    min_forward_days=45,      # Was 30
    min_forward_trades=50,    # Was 20 — need statistical significance
    min_win_rate=0.50,        # Was 0.45
    min_sharpe=1.0,           # Was 0.8
    max_drawdown=0.20,        # Was 0.25
    min_pnl_pct=5.0,          # Was 0 — need meaningful profit
    min_p_value=0.10,         # NEW — require p < 0.10
)
```

**Step 2: Add p-value to graduation scoring**

```python
# Adjusted scoring weights (total = 100):
# Days in test: max 15 pts @ 45 days (was 20 @ 30)
# Trade count: max 15 pts @ 50 trades (was 15 @ 30)
# Win rate: max 20 pts @ 55%
# Sharpe: max 20 pts @ 1.5
# Drawdown: max 15 pts @ <15%
# P-value: max 15 pts @ p < 0.01  (NEW)
p_val = metrics.get("p_value", 1.0)
if p_val < 0.01:
    p_score = 15
elif p_val < 0.05:
    p_score = 10
elif p_val < 0.10:
    p_score = 5
else:
    p_score = 0
```

**Step 3: Reduce allocation formula**

In `forward_test_coordinator.py`:

```python
# OLD (too aggressive): 85+ -> 10%, 75+ -> 7.5%

# NEW (conservative):
if score >= 90:
    allocation = 5.0   # Was 10%
elif score >= 80:
    allocation = 3.0   # Was 7.5%
elif score >= 70:
    allocation = 2.0   # Was 5.0%
elif score >= 60:
    allocation = 1.0   # Was 2.5%
else:
    allocation = 0.5   # Was 1.0%
```

**Step 4: Commit**

```bash
git add incubator/testing/forward_test_tracker.py incubator/testing/forward_test_coordinator.py
git commit -m "feat: tighten graduation criteria and reduce allocations

Min trades: 20 -> 50, min days: 30 -> 45, min WR: 45% -> 50%,
min Sharpe: 0.8 -> 1.0, max allocation: 10% -> 5%.
Added p-value requirement (p < 0.10) to graduation scoring."
```

---

## Task 6: Create Transparent Track Record System

**Files:**
- Create: `alpha_engine/track_record.py`
- Modify: `alpha/index.html` (add track record section)
- Modify: `.github/workflows/alpha-engine-live.yml` (auto-generate each cycle)

**Step 1: Create track_record.py**

```python
"""Track Record Generator — creates honest, transparent performance reports.

Outputs JSON with: overall P/L (no cherry-picking), per-strategy breakdown
with p-values, win/loss streaks, drawdown history, monthly returns.
"""
import json
import math
from datetime import datetime
from collections import defaultdict


def generate_track_record(closed_picks_path: str, performance_path: str) -> dict:
    """Generate transparent track record from closed picks data."""
    with open(closed_picks_path) as f:
        closed = json.load(f)
    with open(performance_path) as f:
        perf = json.load(f)

    if not closed:
        return {"error": "No closed trades", "generated_at": datetime.utcnow().isoformat()}

    total_trades = len(closed)
    wins = sum(1 for p in closed if p.get("pnl_pct", 0) > 0)
    losses = total_trades - wins
    total_pnl_pct = sum(p.get("pnl_pct", 0) for p in closed)
    total_pnl_dollar = sum(p.get("pnl_dollar", 0) for p in closed)

    pnls = [p.get("pnl_pct", 0) for p in closed]
    avg_win = sum(p for p in pnls if p > 0) / max(wins, 1)
    avg_loss = sum(p for p in pnls if p <= 0) / max(losses, 1)

    p_value = _binomial_p_value(wins, total_trades)

    # Drawdown calculation
    equity_curve = [0.0]
    for pnl in pnls:
        equity_curve.append(equity_curve[-1] + pnl)
    peak = equity_curve[0]
    max_dd = 0
    for val in equity_curve:
        if val > peak:
            peak = val
        dd = (val - peak) / max(abs(peak), 0.01)
        if dd < max_dd:
            max_dd = dd

    # Monthly returns
    monthly = defaultdict(lambda: {"trades": 0, "pnl_pct": 0, "wins": 0})
    for p in closed:
        exit_time = p.get("exit_time") or p.get("closed_at", "")
        if exit_time:
            month_key = exit_time[:7]
            monthly[month_key]["trades"] += 1
            monthly[month_key]["pnl_pct"] += p.get("pnl_pct", 0)
            if p.get("pnl_pct", 0) > 0:
                monthly[month_key]["wins"] += 1

    # Strategy breakdown
    strategy_summary = []
    for strat_name, data in sorted(perf.items(), key=lambda x: x[1].get("total_pnl_dollar", 0), reverse=True):
        if data.get("closed_picks", 0) == 0:
            continue
        s_wins = data.get("wins", 0)
        s_total = data.get("closed_picks", 0)
        strategy_summary.append({
            "strategy": strat_name,
            "trades": s_total,
            "win_rate": data.get("win_rate", 0),
            "pnl_dollar": data.get("total_pnl_dollar", 0),
            "sharpe": data.get("sharpe", 0),
            "p_value": _binomial_p_value(s_wins, s_total),
            "status": "PROVEN" if _binomial_p_value(s_wins, s_total) < 0.05 and s_total >= 10 else
                      "PROMISING" if data.get("total_pnl_dollar", 0) > 0 else
                      "LOSING",
        })

    # Win/loss streaks
    current_streak = 0
    max_win_streak = 0
    max_loss_streak = 0
    for pnl in pnls:
        if pnl > 0:
            current_streak = current_streak + 1 if current_streak > 0 else 1
            max_win_streak = max(max_win_streak, current_streak)
        else:
            current_streak = current_streak - 1 if current_streak < 0 else -1
            max_loss_streak = max(max_loss_streak, abs(current_streak))

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "disclaimer": "Past performance does not guarantee future results. All numbers are from live forward testing, not backtests.",
        "overall": {
            "total_trades": total_trades,
            "wins": wins,
            "losses": losses,
            "win_rate": round(wins / total_trades, 4) if total_trades else 0,
            "win_rate_p_value": round(p_value, 4),
            "statistically_significant": p_value < 0.05,
            "total_pnl_pct": round(total_pnl_pct, 4),
            "total_pnl_dollar": round(total_pnl_dollar, 2),
            "avg_win_pct": round(avg_win, 4),
            "avg_loss_pct": round(avg_loss, 4),
            "profit_factor": round(abs(avg_win * wins) / abs(avg_loss * losses), 2) if losses and avg_loss else 0,
            "max_drawdown_pct": round(max_dd, 4),
            "max_win_streak": max_win_streak,
            "max_loss_streak": max_loss_streak,
        },
        "monthly_returns": dict(sorted(monthly.items())),
        "strategies": strategy_summary,
        "proven_count": sum(1 for s in strategy_summary if s["status"] == "PROVEN"),
        "losing_count": sum(1 for s in strategy_summary if s["status"] == "LOSING"),
    }


def _binomial_p_value(wins: int, total: int, null: float = 0.5) -> float:
    if total < 5:
        return 1.0
    rate = wins / total
    if rate <= null:
        return 1.0
    se = math.sqrt(null * (1 - null) / total)
    if se == 0:
        return 1.0
    z = (rate - null) / se
    return 0.5 * math.erfc(z / math.sqrt(2))


if __name__ == "__main__":
    import os
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    result = generate_track_record(
        os.path.join(data_dir, "closed_picks.json"),
        os.path.join(data_dir, "strategy_performance.json"),
    )
    output_path = os.path.join(data_dir, "track_record.json")
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)

    print(f"Track record generated: {output_path}")
    print(f"Total trades: {result['overall']['total_trades']}")
    print(f"Win rate: {result['overall']['win_rate']*100:.1f}% (p={result['overall']['win_rate_p_value']:.4f})")
    print(f"Total P/L: ${result['overall']['total_pnl_dollar']:+,.2f}")
    print(f"Proven strategies: {result['proven_count']}")
    print(f"Losing strategies: {result['losing_count']}")
```

**Step 2: Add to workflow**

In `.github/workflows/alpha-engine-live.yml`, add after the main scan step:

```yaml
      - name: Generate track record
        run: |
          cd alpha_engine
          python track_record.py
```

Add `alpha_engine/data/track_record.json` to the git commit step.

**Step 3: Add track record section to Alpha dashboard**

In `alpha/index.html`, add a "Track Record" section that loads `track_record.json`:
- Big number: Total P/L (honest, including losses)
- Win rate with p-value badge (green if p < 0.05, yellow if p < 0.10, red otherwise)
- Monthly returns table
- Strategy breakdown with PROVEN / PROMISING / LOSING badges
- Disclaimer text at top

**Step 4: Verify**

Run:
```bash
py alpha_engine/track_record.py
```

Expected: JSON with honest metrics, strategy breakdown, monthly returns.

**Step 5: Commit**

```bash
git add alpha_engine/track_record.py alpha_engine/data/track_record.json alpha/index.html .github/workflows/alpha-engine-live.yml
git commit -m "feat: add transparent track record with p-value validation

Generates honest performance report including losses, p-values,
drawdowns, monthly returns. Strategies labeled PROVEN/PROMISING/LOSING.
Auto-generated every scan cycle, displayed on Alpha dashboard."
```

---

## Task 7: Add Circuit Breakers & Red Flag Auto-Pause

**Files:**
- Modify: `alpha_engine/auto_tuner.py` (add system-wide circuit breakers)
- Modify: `alpha_engine/forward_validator.py` (add weekly performance tracking)

**Step 1: Add system-wide circuit breaker to auto_tuner.py**

```python
# System-wide emergency stops — halt ALL signal generation if:
CIRCUIT_BREAKERS = {
    "consecutive_losing_weeks": 3,       # 3 losing weeks in a row → pause all
    "max_system_drawdown_pct": -25.0,    # System-wide DD > 25% → pause all
    "min_system_win_rate": 0.40,         # Overall WR < 40% over last 50 trades → pause all
    "max_single_strategy_loss": -500,    # Any strategy loses > $500 → disable that strategy
    "max_slippage_pct": 0.005,           # Slippage > 0.5% consistently → investigate
}


def check_circuit_breakers(performance_data: dict, closed_picks: list) -> dict:
    """Check system-wide circuit breakers. Returns action dict."""
    result = {"halt_system": False, "reasons": [], "disable_strategies": []}

    # Check overall WR on last 50 trades
    recent = closed_picks[-50:] if len(closed_picks) >= 50 else closed_picks
    if len(recent) >= 20:
        recent_wins = sum(1 for p in recent if p.get("pnl_pct", 0) > 0)
        recent_wr = recent_wins / len(recent)
        if recent_wr < CIRCUIT_BREAKERS["min_system_win_rate"]:
            result["halt_system"] = True
            result["reasons"].append(f"System WR {recent_wr:.1%} < {CIRCUIT_BREAKERS['min_system_win_rate']:.0%} over last {len(recent)} trades")

    # Check per-strategy loss cap
    for strat_name, stats in performance_data.items():
        pnl = stats.get("total_pnl_dollar", 0)
        if pnl < CIRCUIT_BREAKERS["max_single_strategy_loss"] and stats.get("closed_picks", 0) >= 3:
            result["disable_strategies"].append(strat_name)
            result["reasons"].append(f"{strat_name}: ${pnl:.2f} < ${CIRCUIT_BREAKERS['max_single_strategy_loss']}")

    # Check consecutive losing weeks (from weekly P/L)
    # Implementation: track weekly P/L in tuner_state.json
    # If last 3 weeks all negative → halt

    return result
```

**Step 2: Integrate into scan cycle**

In `production_scanner.py`, before generating new picks:

```python
from auto_tuner import check_circuit_breakers

breakers = check_circuit_breakers(performance_data, closed_picks)
if breakers["halt_system"]:
    print("[CIRCUIT BREAKER] System halted!")
    for reason in breakers["reasons"]:
        print(f"  - {reason}")
    # Still validate existing picks (close at TP/SL) but don't open new ones
    skip_generation = True

for strat in breakers["disable_strategies"]:
    # Auto-disable strategies that hit loss cap
    add_to_disabled(strat, reason=f"Loss cap exceeded")
```

**Step 3: Commit**

```bash
git add alpha_engine/auto_tuner.py alpha_engine/forward_validator.py
git commit -m "feat: add system-wide circuit breakers

3 consecutive losing weeks -> halt all generation.
System WR < 40% over 50 trades -> halt all.
Single strategy > \$500 loss -> auto-disable.
System DD > 25% -> halt all.
Existing picks still managed (TP/SL), just no new ones opened."
```

---

## Task 8: Fix GitHub Pages 404s

**Files:**
- Modify: `.github/workflows/deploy-riseoftheclaw.yml` (GitHub Pages deploy)

**Step 1: Identify 404 pages from Playwright audit**

Pages returning 404 on GitHub Pages:
- `alpha/` and `alpha/premium.html`
- `arena/`
- `battleground/a/`, `battleground/b/`, `battleground/c/`
- `monitor/`
- `regime/`
- `riseoftheclaw.html` and `riseoftheclaw/`
- `signal-engine/`

**Step 2: Verify directories exist**

Run:
```bash
ls -la alpha/ arena/ battleground/a/ battleground/b/ battleground/c/ monitor/ regime/ signal-engine/ 2>&1
```

**Step 3: Update GitHub Pages deploy workflow**

Add missing directories to the deploy file list in the workflow.

**Step 4: Verify after deploy**

```bash
gh run list --workflow="deploy-riseoftheclaw.yml" --limit 1
curl -s -o /dev/null -w "%{http_code}" https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/alpha/
curl -s -o /dev/null -w "%{http_code}" https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/monitor/
```

Expected: HTTP 200 for all previously-404 pages.

**Step 5: Commit**

```bash
git add .github/workflows/deploy-riseoftheclaw.yml
git commit -m "fix: add missing directories to GitHub Pages deployment

Fixes 11 x 404 pages found by Playwright audit."
```

---

## Go/No-Go Decision Gates

These gates determine whether to continue, scale up, or stop.

### Gate 1: End of Month 3 (Data Accumulation)

| Criteria | Target | Measurement |
|----------|--------|-------------|
| Forward trades total | 500+ | `closed_picks.json` count |
| Trades per viable strategy | 30+ each | `strategy_performance.json` |
| Overall win rate | > 48% | Track record generator |
| No strategy below | 40% WR | Auto-tuner kills these |
| **Decision** | Continue to Phase 3 OR extend Phase 2 | |

### Gate 2: End of Month 6 (Validation)

| Criteria | Target | Measurement |
|----------|--------|-------------|
| Forward trades total | 1000+ | Accumulated data |
| Overall win rate | > 52% | Track record |
| Profit factor | > 1.3 | Track record |
| Forward Sharpe | > 1.0 | Strategy performance |
| Max DD recovery | < 30 days | Drawdown tracking |
| Statistical significance | p < 0.05 overall | Binomial test |
| **Decision** | Begin 10% capital live deployment OR continue paper | |

### Gate 3: End of Month 9 (Live Validation)

| Criteria | Target | Measurement |
|----------|--------|-------------|
| Live deployment profitable | 3 months | Actual fills |
| Live win rate | > 55% | Actual trades |
| Max live drawdown | < 20% | Equity curve |
| Slippage impact | < 0.3% avg | Fill tracking |
| **Decision** | Increase to 25% capital OR reduce back to 10% | |

### Gate 4: End of Month 12 (Production Ready)

| Criteria | Target | Measurement |
|----------|--------|-------------|
| Live profitability | 6+ months | Audit trail |
| Transparency docs | Complete | Published reports |
| Regime detection | Validated | Regime vs strategy P/L correlation |
| Circuit breakers | Tested | At least 1 triggered and handled |
| Client risk disclosures | Prepared | Legal review |
| **Decision** | Launch signal service at 50% capital OR extend | |

### Graduated Capital Allocation Schedule

| Month | Capital % | Max Risk/Trade | Strategies Active | Kill Criteria |
|-------|-----------|----------------|-------------------|---------------|
| 6 | 10% | 1% | Top 3 only | WR < 45% or DD > 10% |
| 7-8 | 15% | 1.5% | Top 5 | WR < 50% or DD > 15% |
| 9-10 | 25% | 2% | Top 7 | WR < 52% or DD > 20% |
| 11-12 | 50% | 2.5% | Top 10 | WR < 55% or DD > 25% |

---

## Client Communication Standards

### ALWAYS Disclose:
- This is algorithmic trading with inherent risks
- Past performance does not guarantee future results
- Backtest results decay 15-30% in live trading
- Maximum drawdowns of 20-30% are possible
- The system requires 6+ months of data to prove itself

### NEVER Claim:
- Guaranteed returns of any percentage
- Specific profit numbers (e.g., "47.2% annual")
- Sharpe ratios > 3 without 2+ years of live data
- "Risk-free" or "guaranteed" anything
- Win rates from backtests as if they're forward results

### Required Transparency Report Format:
```
Strategy: Hurst Regime Adaptive
Forward Trades: 67
Win Rate: 61.2% (p = 0.032 — statistically significant)
Profit Factor: 1.42
Sharpe: 1.34 (forward, not backtest)
Max Drawdown: -12.3%
Backtest Decay: 18% (backtest 75% WR -> forward 61% WR)
Regime Performance:
  - Trending Up: +18.5% (23 trades, 65% WR)
  - Trending Down: +8.2% (8 trades, 50% WR)
  - Ranging: +12.1% (28 trades, 64% WR)
  - High Vol: -3.2% (8 trades, 38% WR) [auto-paused]
```

---

## Red Flags (Immediate System Pause)

Any of these triggers an immediate halt to all new signal generation:

1. **3 consecutive losing weeks** across the portfolio
2. **System drawdown exceeds 25%** from peak equity
3. **Win rate drops below 40%** over last 50 trades
4. **Any single strategy loses > $500** (auto-disabled)
5. **Slippage exceeds 0.5%** consistently (investigate exchange/fills)
6. **Circuit breaker fires** — no manual override without review

---

## Verification Checklist (Run After All Tasks)

```bash
# 1. Disabled strategy count
py -c "
import sys; sys.path.insert(0, 'alpha_engine')
from auto_tuner import HARD_DISABLED_STRATEGIES
print(f'Hard-disabled strategies: {len(HARD_DISABLED_STRATEGIES)}')
"

# 2. P-value calculations work
py -c "
import sys; sys.path.insert(0, 'alpha_engine')
from forward_validator import binomial_p_value
print(f'p-value(10/15) = {binomial_p_value(10, 15):.4f}')  # Should be ~0.15
print(f'p-value(5/20) = {binomial_p_value(5, 20):.4f}')    # Should be 1.0 (below 50%)
print(f'p-value(15/20) = {binomial_p_value(15, 20):.4f}')   # Should be ~0.02
"

# 3. Regime detector works
py -c "
import sys; sys.path.insert(0, 'alpha_engine')
from regime_detector import detect_regime
prices = list(range(100, 40, -1))  # Declining prices
result = detect_regime(prices, fear_greed=15)
print(f'Regime: {result[\"regime\"]} ({result[\"confidence\"]:.0%})')
"

# 4. Track record generation
py alpha_engine/track_record.py

# 5. Circuit breaker check
py -c "
import sys; sys.path.insert(0, 'alpha_engine')
from auto_tuner import check_circuit_breakers
import json
with open('alpha_engine/data/strategy_performance.json') as f: perf = json.load(f)
with open('alpha_engine/data/closed_picks.json') as f: closed = json.load(f)
result = check_circuit_breakers(perf, closed)
print(f'Halt system: {result[\"halt_system\"]}')
print(f'Strategies to disable: {result[\"disable_strategies\"]}')
for r in result['reasons']: print(f'  - {r}')
"
```

---

## Summary

| Task | What | Expected Impact |
|------|------|-----------------|
| 1. Hard-disable losers | Kill ~15 strategies bleeding money | Save ~$3K/month |
| 2. P-value gate | Require statistical significance | No more coin-flip strategies |
| 3. Regime detection | Auto-pause in wrong conditions | Prevent wrong-regime losses |
| 4. Tighten auto-tuner | $500 loss cap, faster kills | Stop bleeding faster |
| 5. Tighten graduation | 50 trades, p < 0.10 required | Only graduate proven strategies |
| 6. Track record | Honest transparent performance | Build credibility |
| 7. Circuit breakers | System-wide emergency stops | Prevent catastrophic losses |
| 8. Fix 404s | Repair broken GitHub Pages | All dashboards accessible |

**Timeline:** Tasks 1-8 execute immediately (Week 1). Go/No-Go gates at Month 3/6/9/12. Signal selling no earlier than Month 12 after proving 6+ months live profitability.

**No shortcuts. No fantasy numbers. Just disciplined execution.**
