# System Health Review — Dashboard, ML, GitHub Actions, Silent Failures

**Date:** 2026-04-13  
**Scope:** Live dashboard at findtorontoevents.ca/audit, ML model health, CI/CD failures, data quality, profit factor analysis

---

## Executive Summary

**5 critical issues found:**

1. **`Alpha Engine ML Ranker` is 478 hours stale** — the XGBoost model hasn't retrained in 20 days
2. **`ml_crypto_predictor` has -29,375% PnL** on 5,347 closed picks at 43.3% WR — the single largest source of system losses, and its ML model status is "999h stale" (never updated in tracking)
3. **Conflict markers in production** — `meta_strategy/data/swarm_weights.json` has unresolved `<<<<<<< Updated upstream` / `>>>>>>> Stashed changes` merge conflicts, causing 25+ CI failures
4. **Binance API blocked (HTTP 451)** — all 3 Binance mirrors return 451 (geographic restriction), breaking price resolution and causing the dashboard build to timeout
5. **9 HIGH performance alerts firing** — strategies like `crypto_keltner_compression_expansion_v1` dropped from 69% baseline WR to 26% rolling 7d

---

## 1. ML Model Health

| Model | Type | AUC | Last Updated | Age | Status |
|-------|------|-----|-------------|-----|--------|
| KIMI ML Ranker | RandomForest (200 trees) | 0.708 | 5.2h ago | ✅ Fresh | Active |
| **Alpha Engine ML Ranker** | XGBoost (300 trees) | ? | **478h ago** | **🔴 20 DAYS STALE** | Needs retrain |
| Claude Gainer ML | RF+XGBoost Ensemble | 0.722 | 10.8h ago | ✅ Fresh | Active |
| **ML Crypto Predictor** | RF+GBT+XGB Ensemble | ? | **999h+ ago** | **🔴 NEVER TRACKED** | Dead |

### ML Algorithm Performance (all ML-tagged picks)

**ML TOTAL: 277 picks | 36.1% WR | -138.8% PnL.** ML is a net destroyer of capital.

| Status | Count | Description |
|--------|-------|-------------|
| ✅ Working | 8 strategies | `ml_enhanced_TONUSDT_4h_D` (100% WR), `claude_ml_moderate_mut` (60%), `ml_enhanced_ALGOUSDT` (100%) |
| ❌ BROKEN | 14 strategies | `enhanced_ml_A_xgboost` (28.6% WR, -80% PnL), `extreme_fear` (0% WR, -32%), multiple `ml_enhanced_*` variants |

**The Alpha Engine XGBoost hasn't been retrained in 20 days.** The model is making predictions on stale weights while the market regime has changed multiple times. This alone could explain much of the ML drift.

**Fix:** Set up automatic weekly retraining. The KIMI ranker and Claude Gainer models retrain regularly (5h and 11h ago respectively) — extend this pattern to Alpha Engine.

---

## 2. GitHub Actions Failures

### Active failures (last 24h)

| Workflow | Failures | Root Cause | Severity |
|----------|----------|-----------|----------|
| **Conflict Marker Check** | **25 failures** | `meta_strategy/data/swarm_weights.json` has unresolved merge conflict | 🔴 Critical |
| **Unified Audit Dashboard** | 2 failures | "Resolve active picks" step timed out (8min) + Binance 451 | 🔴 Critical |
| **Audit Drift Telemetry** | 3 failures | Likely same timeout/data issue | 🟡 Medium |
| **Deploy Competition to Live Site** | 2 failures | FTP directory `/pine_scripts` doesn't exist on server | 🟡 Medium |
| Dynamic Universe Scanner | 1 cancelled | Unknown | 🟡 Low |
| Copy Trader Portfolio Tracker | 1 cancelled | Unknown | 🟡 Low |

### Conflict Markers — Fix Immediately

```
meta_strategy/data/swarm_weights.json:2:<<<<<<< Updated upstream
meta_strategy/data/swarm_weights.json:3040:>>>>>>> Stashed changes
```

This is blocking 25+ workflow runs. Resolve the merge conflict in this file.

### Binance 451 — Geographic Block

```
Binance api.binance.com failed: HTTP Error 451
Binance api1.binance.com failed: HTTP Error 451
Binance api2.binance.com failed: HTTP Error 451
```

All 3 Binance mirrors are returning HTTP 451 (unavailable for legal reasons). This blocks:
- Price resolution for active picks
- TP/SL hit detection
- Live PnL calculation

**Fix:** Add Bybit/OKX as fallback price sources. Or route through a VPN/proxy in the GitHub Actions runner.

### Deploy Competition — Missing FTP Directory

```
cd: Access failed: 550 Can't change directory to /findtorontoevents.ca/pine_scripts: No such file or directory
```

The `/pine_scripts` directory doesn't exist on the FTP server. Create it or update the deployment workflow to create it before uploading.

---

## 3. Performance Alerts (from Dashboard Payload)

### HIGH Priority Alerts

| Strategy | 7d WR | Baseline WR | Drop |
|----------|-------|-----------|------|
| crypto_keltner_compression_expansion_v1 | **26%** | 69% | -43pp |
| crypto_kalman_trend_residual_reversion_v1 | **20%** | 55% | -35pp |
| stochrsi_macd_combo | **25%** | 44% | -19pp |
| crypto_bayesian_regime_transition_momentum_v1 | **37%** | 54% | -17pp |
| keltner_compression_expansion_eth_v1 | **33%** | 54% | -21pp |
| futures_momentum | **33%** | 49% | -16pp |
| rsi_bounce | **31%** | 47% | -16pp |
| crypto_soc_delta_divergence_a01_v1 | **38%** | 50% | -12pp |
| enhanced_ml_A_xgboost | **26%** | 40% | -14pp |

### MEDIUM Priority Alerts

| Alert | Details |
|-------|---------|
| riseoftheclaw silent | Hasn't produced a pick in 80 hours |
| multi_asset_institutional silent | Hasn't produced a pick in 239 hours |
| leveraged_etf_decay silent | Hasn't produced a pick in 192 hours |

**All 9 HIGH alerts are crypto strategies in rapid decay.** These should be paused immediately.

---

## 4. Silent Failures — Dead Systems

**52 systems have 0 active picks and haven't produced a signal in >12 hours.** The worst:

| System | Last Signal | Closed Picks | WR | Total PnL | Status |
|--------|-----------|-------------|-----|-----------|--------|
| `ml_crypto_predictor` | 16h ago | **5,347** | 43.3% | **-29,375%** | 🔴 Biggest loser in entire system |
| `stocks_competition` | 999h ago | 719 | 34.5% | -428% | Dead (good riddance) |
| `kimi_signal_tracking` | 98h ago | 258 | 34.6% | -715% | Blocked (per earlier report, recent crypto subset was winning) |
| `claude_gainer` | 22h ago | 355 | 32.3% | -813% | 🔴 Massive loser distinct from claude_gainer_st |
| `alpha_engine_fast` | 647h ago | 314 | 36.6% | -132% | Dead |
| `paper_trading` | 896h ago | 92 | 38.2% | -101% | Dead |

**Note:** `ml_crypto_predictor` (5,347 picks, -29,375% PnL) is the elephant in the room. This system produced more picks and lost more money than everything else combined. It appears in the `systems` list with massive closed_picks count, separate from the `recent_closed` (which is capped at 3,500). This is likely the source of the dashboard's -24,944% raw PnL figure.

### Systems that SHOULD be alive but went silent

| System | Last Signal | Note |
|--------|-----------|------|
| `luxalgo_filters` | 25h ago | Was running, may have stopped. 761 closed, 42.2% WR |
| `signal_validation` | 31h ago | Profitable system (54.8% WR, +70% PnL) — should be running |
| `copy_trader_highscore` | 26h ago | 55.2% WR — should be active |

---

## 5. Profit Factor Analysis

### Systems Ranked by Profit Factor (min 5 picks)

**Top tier (PF > 1.5):**

| System | N | WR | PF | Avg Win | Avg Loss | Total |
|--------|---|-----|-----|---------|---------|-------|
| signal_engine_mutations | 7 | 85.7% | **11.53** | +2.38% | -1.24% | +13% |
| signal_validation | 25 | 68.0% | **3.37** | +2.55% | -1.61% | +31% |
| kimi_signal_tracking | 29 | 44.8% | 2.40 | +24.51% | -8.30% | +186% |
| dna_winner_picks | 31 | 58.1% | **2.29** | +2.31% | -1.40% | +23% |
| claude_gainer_st | 589 | 56.4% | **2.09** | +2.13% | -1.32% | +369% |
| multi_asset_copytrader | 573 | 47.8% | **1.54** | +0.58% | -0.35% | +56% |

**PF Enhancement opportunity:** The top-tier systems share a pattern — **avg win > 1.5× avg loss.** Their edge comes from asymmetric payoffs, not high WR. `signal_validation` is the model: 68% WR + 2.55% avg win vs 1.61% avg loss = PF 3.37.

**Bottom tier (PF < 0.5) — destroying capital:**

| System | N | PF | Total PnL | Action |
|--------|---|-----|-----------|--------|
| super_signals | 15 | 0.24 | -20% | Kill |
| forex_copy_trader | 7 | 0.24 | -1% | Kill |
| ml_bg_system_f | 12 | 0.25 | -40% | Kill |
| claude_gainer (not _st) | 5 | 0.26 | -35% | Kill |
| multi_asset_institutional | 18 | 0.26 | -40% | Kill |
| fast_stocks_competition | 21 | 0.28 | -41% | Kill |
| rapid_fire | 81 | 0.31 | -78% | Kill or major reform |

---

## 6. Data Quality Issues

| Issue | Count | % | Severity |
|-------|-------|---|----------|
| Zero PnL on resolved picks | 58 | 1.7% | 🟡 Possible resolution bug |
| TP > 20% away from entry | 7 | 0.2% | 🟡 Too-wide targets |
| SL > 15% away from entry | 6 | 0.2% | 🟡 Too-wide stops |
| PnL > 50% on single trade | 3 | 0.1% | 🟡 Outlier/data error |
| TP on wrong side (SHORT) | 1 | 0.0% | 🔴 Logic bug |

**The 58 zero-PnL resolved picks** suggest the outcome resolver is closing picks without computing PnL, or entry/exit prices are the same. This should be investigated.

---

## 7. Immediate Action Items

| Priority | Action | Impact |
|----------|--------|--------|
| **P0** | Resolve merge conflict in `meta_strategy/data/swarm_weights.json` | Unblocks 25+ CI runs |
| **P0** | Add Bybit/OKX price fallback for Binance 451 block | Restores price resolution |
| **P0** | Retrain Alpha Engine ML Ranker (20 days stale) | Fresh model weights |
| **P1** | Pause all 9 HIGH-alert strategies | Stops active bleeding |
| **P1** | Kill systems with PF < 0.5 (super_signals, ml_bg_system_f, etc.) | Saves ~254% PnL |
| **P1** | Investigate why `ml_crypto_predictor` has -29,375% PnL | Find and fix root cause |
| **P2** | Create `/pine_scripts` on FTP server | Fixes deploy workflow |
| **P2** | Fix 58 zero-PnL resolved picks | Data quality |
| **P2** | Restart `signal_validation` and `luxalgo_filters` if they're unintentionally stopped | Restore profitable systems |

---

*Generated 2026-04-13 from `dashboard_payload.json`, GitHub Actions API (gh cli), and ML health data.*
