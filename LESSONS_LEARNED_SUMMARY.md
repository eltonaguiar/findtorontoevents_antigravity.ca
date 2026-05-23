# Closed Picks Analysis: Summary & Actions Taken

**Date:** April 6, 2026  
**Status:** COMPLETE - Redis Bus Messages Sent

---

## 📊 Key Findings from 1,974 Closed Picks

### 1. Score Correlation is INVERTED ⚠️
| Score Range | Avg PnL | Hit Rate | Assessment |
|-------------|---------|----------|------------|
| **80+** | **-2.08%** | 48.9% | 🔴 OVERVALUED |
| **60-79** | **+3.59%** | 66.0% | 🟢 UNDERVALUED |

**Problem:** Our highest-scoring picks are our worst performers.

### 2. Direction Bias: SHORT Dominates
| Direction | Win Rate | Avg PnL | Assessment |
|-----------|----------|---------|------------|
| **SHORT** | **67.1%** | **+4.20%** | 🟢 SUPERIOR |
| **LONG** | 33.3% | -2.07% | 🔴 FAILING |

**Problem:** We're 79% LONG-biased in a SHORT-favoring market.

### 3. Asset Class Performance
| Asset | Avg PnL | Assessment |
|-------|---------|------------|
| **CRYPTO** | **+0.42%** | 🟢 Keep |
| **EQUITY** | **-5.35%** | 🔴 Avoid |
| **FOREX** | -0.06% | 🟡 Neutral |

**Problem:** EQUITY picks destroying portfolio performance.

### 4. System Hierarchy (Realized)
| System | Avg PnL | Win Rate |
|--------|---------|----------|
| **inverse_mutations** | **+9.06%** | 72% |
| **short_engine** | **+3.32%** | 68% |
| battleground | +0.52% | 51% |
| alpha_engine | -0.50% | 43% |

---

## 📡 Redis Bus Messages Sent

### 1. Broadcast to ALL_SYSTEMS ✅
```
Channel: bus:broadcast:log
Priority: HIGH
Content: Critical score correlation issue + direction bias fix
Status: DELIVERED (visible in log)
```

### 2. Direct Messages ✅
| To | Message | Status |
|----|---------|--------|
| quality_engine | Update scoring config with multipliers | SENT |
| picks_generator | Adjust pick distribution 60/40 SHORT/LONG | SENT |
| conflict_detector | Favor SHORT on conflicts | SENT |

### 3. Files Created
| File | Purpose |
|------|---------|
| `CLOSED_PICKS_LESSONS_LEARNED.md` | Full analysis (9 KB) |
| `REDIS_BUS_RECOMMENDATIONS.md` | Bus message specs (8 KB) |
| `scoring_tweaks_config.json` | Config file (5 KB) |

---

## 🔧 Recommended Scoring Tweaks

### Immediate Deployment
```python
# 1. Direction Bias (CRITICAL)
DIRECTION_MULTIPLIERS = {
    'SHORT': 1.25,  # +25% boost
    'LONG': 0.75    # -25% penalty
}

# 2. Asset Class Adjustments
ASSET_MULTIPLIERS = {
    'CRYPTO': 1.10,
    'EQUITY': 0.85,   # -15% penalty
    'FOREX': 1.00
}

# 3. System Trust Recalibration
SYSTEM_MULTIPLIERS = {
    'inverse_mutations': 1.50,  # +50% (best performer)
    'short_engine': 1.30,       # +30%
    'battleground': 1.20,
    'alpha_engine': 1.00,
    'pm_kalshi_signals': 0.80   # -20% (underperforming)
}

# 4. Symbol Blacklist
BLACKLIST = ['OPUSDT', 'KATUSDT', 'KITEUSDT', 'RESOLVUSDT']

# 5. Strategy Restrictions
STRATEGY_RULES = {
    'macd_crossover': 'disable_long',      # 19.6% LONG WR
    'luxalgo_confluence': 'short_only',    # 32.3% LONG WR
    'crypto_keltner_v1': 'favor_short_80'  # 82% SHORT WR
}
```

---

## 📈 Expected Impact

| Metric | Before | Target | Timeline |
|--------|--------|--------|----------|
| Overall Win Rate | 42% | 55% | 1 week |
| Score 80+ Correlation | -2.08% | +3.0% | 1 week |
| Avg PnL per Pick | -0.5% | +1.5% | 2 weeks |
| Direction Balance | 79% LONG | 60% SHORT | Immediate |

---

## ⚠️ Rollback Criteria

If any of these occur, revert changes:
1. Overall WR drops below 40% for 3 consecutive days
2. Score correlation remains negative after 1 week
3. Single-day drawdown >10% from SHORT bias

---

## 📅 Next Steps

| Task | Owner | Due |
|------|-------|-----|
| Deploy scoring config | quality_engine | 2026-04-07 00:00 UTC |
| Adjust pick distribution | picks_generator | 2026-04-07 00:00 UTC |
| Update conflict resolution | conflict_detector | 2026-04-07 00:00 UTC |
| Market regime analysis | market_research_agent | 2026-04-08 00:00 UTC |
| Validation report | data_analytics_agent | 2026-04-13 00:00 UTC |
| Review meeting | ALL | 2026-04-13 15:00 UTC |

---

## ✅ Confirmation Checklist

- [x] Closed picks analyzed (1,974 picks)
- [x] Lessons learned documented
- [x] Scoring recommendations created
- [x] Redis Bus broadcast sent
- [x] Direct messages sent to key systems
- [x] Config file created
- [x] Rollback criteria defined

---

**Analysis Complete:** April 6, 2026  
**Redis Bus Status:** ACTIVE  
**Next Review:** April 13, 2026
