# Phenomenal Performance Enhancement Plan — Asset Class Optimization

## 1. Goal & North Star
The objective is to achieve **sustainable, hedge-fund-grade performance** across all asset classes (EQUITY, CRYPTO, FOREX, COMMODITY, BOND, FUTURES) as surfaced on `findtorontoevents.ca/audit`. 

**Success Metrics:**
- **Tier 2 Minimum:** PF > 1.5, WR > 50%, MDD < 20%.
- **Tier 1 Target:** PF > 2.0, WR > 55%, MDD < 10%.
- **Noise Reduction:** Non-crypto noise share < 30% (verified via v2 resolver).

---

## 2. Asset Class Strategy Matrix

| Asset Class | Current Edge | Enhancement Path | Key Filter/Gate |
| :--- | :--- | :--- | :--- |
| **EQUITY** | Momentum/Value | Integrate UEPS Long-Term Value project | Fundamental Value-Floor Filter |
| **CRYPTO** | Vol-Target Mean Rev | Implement Inverse "Pump Watch" Gate | Skyrocket Potential $\le$ 0.9 |
| **FOREX** | JPY-cross Avoidance | CFTC COT Extreme Positioning alignment | Commercial Net Z-Score $\pm 2.0$ |
| **COMMODITY**| Industrial Metals | Restrict to HG=F / PL=F (Sub-class Kill) | `COMMODITY_BLACKLIST` |
| **BOND** | High PF / Low $n$ | Expand universe via ZN=F routing | Regime-Sourced and Duration-Gated |
| **FUTURES** | Whitelist-only | Expand whitelist based on COT signals | `Sourced` mapping validation |

---

## 3. Implementation Roadmap

### Phase A: Quality Gate Fortification (Immediate)
- **CRYPTO Pump Watch**: Block picks in "skyrocket" states to prevent buying tops.
- **HMM Regime Filter**: Stratify all asset classes by BULL/BEAR/CHOPPY regimes to avoid direction-regime mismatch.
- **CFTC COT Wire-up**: Use commercial trader extremes to validate FOREX/COMMODITY directions.

### Phase B: Pipeline & Data Integrity (Short-term)
- **UEPS Integration**: Migrate the US Equity Prediction System from `updates/` to `alpha_engine/ueps/` and wire into `production_scanner.py`.
- **History Pipeline Audit**: Update `dashboard_generator.py` to distinguish between `Insufficient Data (n<3)` and `Strategy Fallback` in "Track %" displays to avoid misleading the user.
- **Fundamental API Integration**: Integrate Alpha Vantage/Yahoo Finance to provide a "Value-Floor" for Equity picks.

### Phase C: Validation & Scaling (Mid-term)
- **A/B Resolver Replay**: Apply v2 resolver (5bp threshold + bar-replay) to historical ledger to establish a "Clean Truth" baseline.
- **Staggered Rollout**: Enable new gates (COT, Regime) per-class with a 14-day shadow period and Wilson 95% CI lower-bound verification.

---

## 4. Methodology & Validation
Every change follows the **Surgical-Sized-Sized** protocol:
1. **Sidecar Implementation**: New logic is added as a helper function.
2. **Default-OFF**: Gates are controlled by `ENV` flags.
3. **Shadow Logging**: Logic runs in "log-only" mode to collect data without affecting live picks.
4. **Statistically Significant Flip**: Gates are only enabled if $n \ge 30$ new closed picks prove an edge improvement.
