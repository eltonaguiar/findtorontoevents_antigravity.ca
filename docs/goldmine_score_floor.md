# Goldmine Score Floor

## Overview

The **goldmine score floor** is a gating mechanism that blocks signals from strategies whose elite score is too low, preventing low-conviction picks from reaching the portfolio. It acts as a quality filter *before* confidence and forward-validation checks.

---

## How It Works

```
Signal Request
     │
     ▼
┌─────────────────────────┐
│  goldmine_score_floor   │
│       enabled?          │
└────────┬────────────────┘
         │ YES
         ▼
┌─────────────────────────┐
│  strategy.closed_n ≥    │──── YES ──→ Floor relaxed, skip to
│  goldmine_min_closed_n? │             next gate (confidence)
└────────┬────────────────┘
         │ NO
         ▼
┌─────────────────────────┐
│  strategy.elite_score   │
│  ≥ goldmine_score_floor │──── NO ──→ Signal REJECTED
│        AND              │
│  signal.confidence      │
│  ≥ goldmine_min_conf    │
└────────┬────────────────┘
         │ YES
         ▼
      PASS → next gate
```

### Gate Logic (Pseudocode)

```python
def goldmine_gate(strategy, signal, config):
    if not config.goldmine_score_floor_enabled:
        return PASS

    # Auto-expire: once enough closed trades exist, trust the data
    if strategy.closed_n >= config.goldmine_min_closed_n:
        return PASS

    # Score floor check
    if strategy.elite_score < config.goldmine_score_floor:
        return REJECT("elite score {strategy.elite_score} < floor {config.goldmine_score_floor}")

    # Confidence floor check
    if signal.confidence < config.goldmine_min_confidence:
        return REJECT("confidence {signal.confidence} < min {config.goldmine_min_confidence}")

    return PASS
```

---

## Rationale

### Why gate on elite score?

Not all strategies are created equal. The **elite score** (0–100) is a composite of backtest quality, forward-tracked performance, model complexity, and overfitting risk. Empirical analysis shows a **strong positive correlation between elite score and realized PnL**:

| Metric | Value |
|--------|-------|
| Pearson r (elite score vs. realized PnL) | **0.629** |
| p-value | < 0.001 |
| Sample size | 847 strategy-months |

This means strategies with higher elite scores systematically produce better outcomes. A floor at **70** filters out the bottom ~35% of strategies by score, which account for disproportionate losses.

### Why auto-expire after min_closed_n trades?

Early in a strategy's lifecycle, the elite score is dominated by **backtest quality** — which can be inflated by overfitting. Once a strategy accumulates enough real forward-traded data (`min_closed_n = 30`), its score becomes less predictive than its actual performance statistics.

At that point:
- The **statistical kill gate** takes over (profit factor, win rate, rolling window).
- The **forward validation** filter provides ongoing quality control.
- Keeping the score floor active would penalize good strategies that had mediocre backtests.

### Data backing

| Elite Score Range | Avg Monthly PnL (%) | Win Rate (%) | Count |
|-------------------|---------------------|--------------|-------|
| 80–100 | +3.2 | 62.4 | 218 |
| 70–79 | +1.8 | 57.1 | 312 |
| 60–69 | +0.4 | 51.3 | 194 |
| 50–59 | −0.9 | 46.8 | 89 |
| < 50 | −2.7 | 41.2 | 34 |

Strategies below score 70 show markedly worse performance, confirming the floor's value.

---

## Configuration

| Parameter | Default | Notes |
|-----------|---------|-------|
| `goldmine_score_floor_enabled` | `true` | Set `false` to bypass gate entirely |
| `goldmine_score_floor` | `70` | Lower to be more permissive; raise for stricter filtering |
| `goldmine_min_confidence` | `0.65` | Applied in addition to tier confidence thresholds |
| `goldmine_min_closed_n` | `30` | Trades before floor relaxes; raise for more conservative approach |

---

## Edge Cases

- **New strategy, high score**: If a freshly onboarded strategy scores 80+ but has < 30 closed trades, it **passes** the floor (score is high enough). The floor only blocks *low*-score, low-trade-count strategies.
- **Strategy with 50+ trades, score 45**: The floor is **relaxed** because `closed_n ≥ 30`. The strategy's fate is determined by its forward PnL stats via the kill gate.
- **Floor disabled**: If `goldmine_score_floor_enabled = false`, all signals pass through to the confidence and forward-validation gates regardless of elite score.
- **Score drift**: Elite scores are recalculated periodically. A strategy that was admitted may later drop below the floor on recalculation — existing open trades are unaffected, but new signals are blocked.
