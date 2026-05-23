# Dynamic Non-Crypto Cap

## Overview

The **dynamic non-crypto cap** limits how many non-crypto signals can be emitted in a cycle, scaling the limit proportionally to the number of active non-crypto picks. This prevents non-crypto signals from flooding the portfolio during high-activity periods while ensuring a minimum floor during quiet periods.

---

## How It Works

### Formula

```
cap = max(non_crypto_cap_floor, int(non_crypto_cap_ratio * active_non_crypto_count))
```

Where:
- `non_crypto_cap_floor` = absolute minimum cap (default: `3`)
- `non_crypto_cap_ratio` = proportion of active picks (default: `0.05` = 5%)
- `active_non_crypto_count` = number of currently active non-crypto picks in the portfolio

### Flow

```
Signal Emission Cycle
     │
     ▼
┌──────────────────────────────┐
│  Count active non-crypto     │
│  picks in portfolio          │
└────────┬─────────────────────┘
         │
         ▼
┌──────────────────────────────┐
│  Calculate cap:              │
│  max(floor, int(0.05 × N))   │
└────────┬─────────────────────┘
         │
         ▼
┌──────────────────────────────┐
│  Rank candidate signals by   │
│  composite score (desc)      │
└────────┬─────────────────────┘
         │
         ▼
┌──────────────────────────────┐
│  Emit top `cap` signals;     │
│  queue or drop the rest      │
└──────────────────────────────┘
```

---

## Examples at Different Active Counts

| Active Non-Crypto Picks | `int(0.05 × N)` | Effective Cap (`max(3, …)`) | Explanation |
|------------------------|------------------|----------------------------|-------------|
| 0 | 0 | **3** | Floor applies — always allow at least 3 signals |
| 10 | 0 | **3** | Floor still applies |
| 40 | 2 | **3** | Floor still applies |
| 60 | 3 | **3** | Floor and ratio produce same result |
| 80 | 4 | **4** | Ratio starts to dominate |
| 100 | 5 | **5** | 5% of 100 |
| 200 | 10 | **10** | Scales linearly |
| 500 | 25 | **25** | Large portfolio, proportional signals |
| 1000 | 50 | **50** | At scale, cap grows with portfolio |

### Interpretation

- **Small portfolio (< 60 picks)**: The cap is clamped to the floor of 3. This ensures that even a tiny non-crypto allocation always gets a few high-quality signals.
- **Medium portfolio (60–200 picks)**: The cap grows slowly. At 100 active picks, only 5 new signals per cycle — roughly a 5% churn rate, which is conservative.
- **Large portfolio (200+ picks)**: The cap scales linearly. At 500 picks, 25 signals per cycle allows meaningful rebalancing without overwhelming the execution layer.

---

## Rationale

### Why proportional?

A fixed cap (e.g., "max 10 non-crypto signals") doesn't scale. A portfolio with 20 picks needs different signal volume than one with 500. Proportional capping ensures:

1. **Signal density stays consistent** — roughly 5% turnover per cycle regardless of portfolio size.
2. **No starvation at small scale** — the floor of 3 guarantees non-crypto always gets representation.
3. **No flooding at large scale** — the ratio prevents a 1000-pick portfolio from seeing 100 non-crypto signals at once.

### Why not a fixed number?

| Approach | 20 Picks | 200 Picks | 1000 Picks |
|----------|----------|-----------|------------|
| Fixed cap = 10 | 50% churn (too high) | 5% churn (good) | 1% churn (too low) |
| Proportional 5%, floor 3 | 15% churn (reasonable) | 5% churn (good) | 5% churn (good) |

A fixed number either floods small portfolios or starves large ones.

### Why a floor?

Without a floor, a portfolio with 0–60 active non-crypto picks would get 0–2 signals per cycle. At 0 signals, the non-crypto allocation effectively goes dormant — strategies may atrophy, and the system loses diversification benefit. The floor of 3 ensures a minimum signal flow even in low-activity periods.

---

## Configuration

| Parameter | Default | Notes |
|-----------|---------|-------|
| `dynamic_non_crypto_cap_enabled` | `true` | Set `false` to emit all qualifying non-crypto signals without cap |
| `non_crypto_cap_floor` | `3` | Absolute minimum signals per cycle |
| `non_crypto_cap_ratio` | `0.05` | 5% of active picks; adjust for more/less aggressive scaling |

### Tuning Guide

| Goal | Recommended Setting |
|------|---------------------|
| Conservative / low turnover | `cap_ratio: 0.03`, `cap_floor: 2` |
| Default / balanced | `cap_ratio: 0.05`, `cap_floor: 3` |
| Aggressive / high turnover | `cap_ratio: 0.10`, `cap_floor: 5` |
| No cap (all signals pass) | `dynamic_non_crypto_cap_enabled: false` |

---

## Edge Cases

- **Cap disabled**: If `dynamic_non_crypto_cap_enabled = false`, all qualifying non-crypto signals are emitted. Use only in backtesting or during controlled rollouts.
- **Active count = 0**: If there are no active non-crypto picks, the cap defaults to `cap_floor` (3). This allows the system to bootstrap a non-crypto allocation from scratch.
- **Signal count < cap**: If fewer signals qualify than the cap allows, all qualifying signals are emitted (no padding). The cap is an upper bound, not a quota.
- **Tie-breaking**: When candidate signals exceed the cap and have equal composite scores, ties are broken by signal freshness (newer first), then alphabetically by symbol.
