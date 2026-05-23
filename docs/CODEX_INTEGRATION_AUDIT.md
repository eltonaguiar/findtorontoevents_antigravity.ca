# Codex `continuous_improvement_monitor.py` Integration Audit

**Date:** 2026-03-24
**Author:** Claude Code (Opus 4.6) -- research only, no code changes
**Scope:** Overlap analysis between Codex's `continuous_improvement_monitor.py` and six existing alpha_engine modules

---

## Executive Summary

The Codex monitor is a **cross-system observability layer** that reads data from alpha_engine, copy_trader_intel, and paper_trading, then generates alerts and recommendations. It explicitly avoids killing strategies (routes to mutation/inverse instead). There are **six areas of overlap** with our existing modules, but most are complementary rather than conflicting. Two areas need attention to avoid double-penalization.

---

## 1. Missed Opportunity Analyzer (`missed_opportunity_analyzer.py`)

### What each system does

| Aspect | Our `missed_opportunity_analyzer.py` | Codex `continuous_improvement_monitor.py` |
|--------|--------------------------------------|------------------------------------------|
| **Focus** | Identifies top Binance gainers we missed + analyzes SL_HIT picks | Monitors open position health, directional correctness, strategy decay |
| **Wrong guess analysis** | Deep per-pick diagnosis (RSI, volume, regime, confidence) of SL_HIT trades in last 24h | No per-pick failure diagnosis; only tracks aggregate win rate and directional correctness |
| **Missed gainers** | Fetches Binance 24h tickers, compares against our universe + active picks | Not present -- Codex monitor does not track missed market opportunities |
| **Output** | `wrong_guesses_log.json`, `missed_gainers_log.json`, `hourly_improvement_report.json` | `continuous_improvement_report.json`, `continuous_improvement_report.md` |
| **Universe expansion** | `get_universe_additions()` recommends new symbols based on miss frequency | Not present |

### Conflict assessment: **NO CONFLICT -- Complementary**

The Codex monitor does not analyze wrong guesses at the individual pick level and does not track missed gainers. These are entirely separate concerns. The Codex monitor's `STRATEGY_DECAY` alert is at the strategy level (win rate, PF, Sharpe), while our missed_opportunity_analyzer works at the individual trade and symbol level.

### Recommendation: **Keep both**

No integration needed. They operate on different data and produce different insights.

---

## 2. Adaptive Trust Tuner (`adaptive_trust_tuner.py`)

### What each system does

| Aspect | Our `adaptive_trust_tuner.py` | Codex `continuous_improvement_monitor.py` |
|--------|-------------------------------|------------------------------------------|
| **Trust adjustment** | Computes per-strategy and per-symbol confidence boosts/penalties based on rolling WR and profit factor | Does NOT adjust trust/confidence scores at all |
| **Output mechanism** | Writes `trust_adjustments.json`; `apply_trust_adjustments(pick)` returns [-0.20, +0.20] confidence delta applied to each pick | Writes recommendations as text (e.g., "route X to mutation") but never modifies pick confidence |
| **Thresholds** | WR >= 70% -> +0.15 boost; WR < 30% -> -0.15 penalty; PF < 1.0 with avg_pnl < 0 -> -0.05 | WR floor: 42% (configurable); PF floor: 1.0; Sharpe floor: 0.5 -- but these are for alerting only |
| **Action on underperformers** | Adjusts confidence within bounded range (never kills) | Routes to mutation/inverse workflow (never kills) |

### Conflict assessment: **POTENTIAL DOUBLE-PENALIZATION**

Both systems penalize underperforming strategies, but through different mechanisms:
- Our trust tuner **directly reduces confidence** on picks from bad strategies (up to -0.20)
- The Codex monitor **flags** those same strategies as "rehabilitation candidates" and can trigger mutation scans

The double-penalization risk is LOW because:
1. The trust tuner acts on **pick confidence** (a numeric score adjustment)
2. The Codex monitor acts on **strategy routing** (mutation/inverse, not score adjustment)
3. They don't read each other's outputs

However, if a mutation scan produces a new variant strategy and that variant inherits the original's trade history, the trust tuner could unfairly penalize the new variant.

### Recommendation: **Keep both, but document the interaction**

The trust tuner handles per-pick confidence tuning (fine-grained), while the Codex monitor handles strategy-level rehabilitation routing (coarse-grained). They serve different purposes. Ensure mutation-generated strategy variants get clean trade history.

---

## 3. Strategy Priority (`strategy_priority.py`)

### What each system does

| Aspect | Our `strategy_priority.py` | Codex `continuous_improvement_monitor.py` |
|--------|----------------------------|------------------------------------------|
| **Tier system** | ELITE (top 5, 3x sizing), PROVEN (next 10, 1x), EXPERIMENTAL (rest, 0.5x) | No tier system; only categorizes as "rehabilitation_candidates" vs "leaders" |
| **Kill list** | Auto-kill: WR < 30% on 20+ trades -> HARD_DISABLED, saved to `strategy_kill_list.json` | **Explicitly does NOT kill**: `"disable_strategies": False`, routes to mutation instead |
| **Confidence gates** | ELITE >= 0.65, PROVEN >= 0.70, EXPERIMENTAL >= 0.80 | No confidence gates |
| **Metrics** | Composite score: 0.4*WR + 0.3*PF + 0.3*avg_pnl | WR, PF, Sharpe (thresholds: WR 42%, PF 1.0, Sharpe 0.5) |
| **Position sizing** | Direct multiplier on pick position sizes | Recommends "tighten risk" on drawdown breach but does not modify sizes |

### Conflict assessment: **CONFLICTING KILL POLICY**

This is the most significant conflict:
- Our `strategy_priority.py` will **HARD_DISABLE** a strategy when WR < 30% on 20+ trades
- The Codex monitor's explicit policy is `"disable_strategies": False` and `"rehabilitation_policy": "mutate_or_inverse_before_kill"`

A strategy could be killed by `strategy_priority.py` before the Codex monitor ever gets a chance to route it to mutation.

Additionally, their WR thresholds differ:
- Our kill threshold: **WR < 30%** (hard kill)
- Codex rehabilitation threshold: **WR < 42%** (route to mutation)

This means strategies between 30-42% WR will be flagged by Codex for rehabilitation but left alive by our system -- which is correct behavior. But strategies below 30% will be killed by us before Codex can rehabilitate them.

### Recommendation: **Reconcile kill policy**

The project has a "mutate before kill" rule (per MEMORY.md). Our `strategy_priority.py` auto-kill at WR < 30% should check if a mutation has been attempted first before hard-disabling. Options:
1. Add a mutation-attempted check to `strategy_priority.py`'s auto-kill logic
2. Have `strategy_priority.py` read the Codex monitor's rehabilitation list and defer killing for one cycle
3. Accept the current behavior if 30% WR is considered so bad that mutation is pointless

---

## 4. Risk Controls (`risk_controls.py`)

### What each system does

| Aspect | Our `risk_controls.py` | Codex `continuous_improvement_monitor.py` |
|--------|------------------------|------------------------------------------|
| **Drawdown circuit breaker** | -5% WARNING, -10% CRITICAL (halt new picks), -15% EMERGENCY (close all) -- computed from 7-day realized + unrealized | -8% drawdown (configurable `portfolio_drawdown_limit_pct`) generates CRITICAL alert |
| **Daily loss limit** | -2% realized -> block new picks, -3% -> close bottom 30% | Not present |
| **Consecutive loss breaker** | 5+ consecutive losses -> 24h strategy cooldown | Not present |
| **Position sizing** | EMERGENCY: close all; CRITICAL: only ELITE, halve sizes; WARNING: halve EXPERIMENTAL | Recommends "tighten_risk_and_reduce_gross_exposure" on drawdown breach but does not directly modify sizes |
| **Scope** | Alpha engine only | Cross-system (alpha + copy_trader + paper_trading) |

### Conflict assessment: **THRESHOLD MISMATCH (but complementary)**

The drawdown thresholds differ:
- Our `risk_controls.py`: WARNING at -5%, CRITICAL at -10%, EMERGENCY at -15%
- Codex monitor: CRITICAL alert at -8%

This means the Codex monitor will fire a CRITICAL drawdown alert at -8%, but our risk_controls.py is only at WARNING level (-5%) and hasn't reached CRITICAL (-10%) yet. The Codex alert will recommend tightening risk, but our system won't enforce it at the CRITICAL level until -10%.

The Codex monitor's drawdown check is on **paper trading portfolios** (max drawdown field), while our risk_controls checks **alpha engine realized+unrealized PnL**. They measure slightly different things.

### Recommendation: **Keep both -- they're complementary layers**

Our risk_controls.py is the enforcement layer (actually modifies picks and blocks generation). The Codex monitor is the alerting/observability layer (generates human-readable alerts). They don't conflict because:
1. Different data sources (alpha realized PnL vs paper trading max drawdown)
2. Different actions (enforcement vs alerting)
3. The Codex monitor's recommendation to "tighten risk" could trigger a refresh of our risk_controls, which is the correct escalation path

Consider aligning the Codex drawdown config (`portfolio_drawdown_limit_pct: 8.0`) to match our WARNING threshold (-5%) so the Codex alert fires at the same point our system starts acting.

---

## 5. Prediction Anomaly Detector (`prediction_anomaly_detector.py`)

### What each system does

| Aspect | Our `prediction_anomaly_detector.py` | Codex `continuous_improvement_monitor.py` |
|--------|--------------------------------------|------------------------------------------|
| **SPC on win rate** | Rolling 20-trade p-chart with UCL/LCL, fires DEGRADATION if WR < LCL | Fires REALIZED_WIN_RATE_BREACH if overall WR < 45% (configurable) |
| **Prediction drift** | PSI (Population Stability Index) on ml_score distribution, mean shift detection | Fires CONFIDENCE_INVERSION if high-conf picks underperform low-conf picks |
| **OOD detection** | Z-score outlier detection on pick feature vectors, applies -0.05 confidence penalty | Not present |
| **Consecutive patterns** | Detects 5+ loss streaks per strategy, 10+ herding (same direction) | Not present |
| **Sizing reduction** | CRITICAL alert -> 50% sizing multiplier (via `get_sizing_multiplier()`) | Recommends "tighten risk" but does not directly reduce sizing |
| **Alert output** | `prediction_alerts.json` with severity levels | Alerts in `continuous_improvement_report.json` |

### Conflict assessment: **POTENTIAL DOUBLE-ALERT on degradation**

Both systems detect win-rate degradation, but differently:
- Our detector uses **statistical process control** (3-sigma control limits relative to historical baseline)
- Codex uses a **fixed threshold** (WR < 45%)

Scenario: If historical WR is 50% and drops to 43%:
- Our SPC might NOT fire (43% could be within control limits depending on sample size)
- Codex WILL fire (43% < 45% floor)

Scenario: If historical WR is 60% and drops to 48%:
- Our SPC WILL fire (48% is likely below LCL for a 60% baseline)
- Codex WILL also fire (48% > 45%, so actually Codex will NOT fire)

They actually have different sensitivity profiles, making them complementary rather than duplicative. The bigger concern is the **confidence inversion** alert in Codex vs our **prediction drift** detection -- these detect different symptoms of the same underlying problem (model miscalibration).

### Recommendation: **Keep both -- no double-alert risk in practice**

Our detector focuses on statistical anomalies in the model itself (drift, OOD, distribution shifts). The Codex monitor focuses on practical outcome metrics (is WR below floor, are high-conf picks actually better). They catch different problems. There is no double-penalization because:
1. Our detector's 50% sizing multiplier is read via `get_sizing_multiplier()`
2. The Codex monitor only recommends actions (doesn't enforce sizing)

---

## 6. Kill Switch (`kill_switch.py`)

### What each system does

| Aspect | Our `kill_switch.py` | Codex `continuous_improvement_monitor.py` |
|--------|----------------------|------------------------------------------|
| **Kill conditions** | Drawdown spike (2x historical 95th pctile), SL rate >60% of last 10, WR collapse (<25% on 20 trades), 5+ consecutive losses | No kill conditions -- explicitly `"disable_strategies": False` |
| **Severity levels** | ok/warning/critical/emergency | LOW/MEDIUM/HIGH/CRITICAL (for alerts only) |
| **Actions** | `pause_new_entries` (critical), `close_all` (emergency), `reduce_size` (warning) | Recommends actions but never pauses or closes |
| **Feature health** | Warns on >75% dead features (never blocks) | Not present |
| **Output** | `kill_switch_status.json` with `is_killed` boolean | `continuous_improvement_report.json` -- no kill flag |

### Conflict assessment: **PHILOSOPHICAL CONFLICT but no runtime conflict**

The philosophical difference is clear:
- Our kill_switch will **halt signal generation entirely** on critical/emergency conditions
- The Codex monitor's policy is **never disable, always rehabilitate**

However, there is **no runtime conflict** because:
1. The kill_switch runs inline during the scanner pipeline and blocks pick generation
2. The Codex monitor runs as a separate observability process and only generates reports
3. They don't read each other's outputs
4. The kill_switch acts first (during pick generation), so the Codex monitor would only see the aftermath

The Codex monitor's `STRATEGY_DECAY` alert and rehabilitation routing would be moot for a strategy that our kill_switch has already paused. But since the kill_switch operates at the **system level** (all strategies paused) while the Codex monitor operates at the **individual strategy level** (route this one strategy to mutation), they address different scopes.

### Recommendation: **Keep both -- they operate at different levels**

The kill_switch is the "emergency brake" for the whole system. The Codex monitor is the "strategy doctor" for individual strategies. The only improvement would be: when the kill_switch is in critical/emergency state, the Codex monitor should detect this (read `kill_switch_status.json`) and suppress its own recommendations, since they're moot while the system is halted.

---

## Summary Matrix

| Overlap Area | Conflict Level | Double-Penalize Risk | Recommendation |
|-------------|---------------|---------------------|----------------|
| Wrong guess analysis | NONE | None | Keep both (different granularity) |
| Trust/confidence adjustment | LOW | Low (different mechanisms) | Keep both, ensure mutation variants get clean history |
| Strategy routing / kill lists | **MEDIUM** | Medium (kill before mutation) | Reconcile: add mutation-check before auto-kill |
| Drawdown thresholds | LOW | None (alert vs enforce) | Keep both, consider aligning thresholds |
| Degradation detection | LOW | None (different methods) | Keep both (complementary sensitivity) |
| Kill vs rehabilitate philosophy | LOW (runtime) | None | Keep both (different scopes: system vs strategy) |

---

## Action Items (Priority Order)

1. **[MEDIUM]** `strategy_priority.py` auto-kill (WR<30%, 20+ trades) should respect "mutate before kill" by checking if a mutation has been attempted before hard-disabling. This aligns with the project rule in MEMORY.md and the Codex monitor's rehabilitation policy.

2. **[LOW]** Consider having the Codex monitor read `kill_switch_status.json` and `circuit_breaker.json` to suppress recommendations when the system is in critical/emergency state.

3. **[LOW]** Align the Codex monitor's `portfolio_drawdown_limit_pct` (8.0%) with our risk_controls.py WARNING threshold (-5%) or CRITICAL threshold (-10%) so alerts and enforcement fire at coordinated levels.

4. **[LOW]** Ensure that when the Codex monitor triggers mutation actions (`alpha_mutation_scan`, `kimi_inverse_scan`), the resulting mutated strategies get fresh trade history so the adaptive_trust_tuner doesn't inherit the parent's negative adjustments.
