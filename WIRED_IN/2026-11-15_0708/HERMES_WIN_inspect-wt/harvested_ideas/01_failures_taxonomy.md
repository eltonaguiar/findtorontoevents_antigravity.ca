# Failure Taxonomy — All Strategies Ever Tried

Every strategy in this repo has been classified against the 10 failure-mode taxonomy from the enhanced prompt. Each row cites the exact file path. **"Dead"** = fails shuffle control, walk-forward, or temporal discipline. **"Near-miss"** = passes 4+ proof steps but fails significance/Monte Carlo sample size. **"Actionable"** = passes all 10.

| ID | Strategy | File | Asset Class | Timeframe | Failure Mode(s) | Verdict | Why it Failed |
|----|----------|------|-------------|-----------|-----------------|---------|---------------|
| F1 | EMA600/EMA40 momentum cross | baby_strategies/kimi_ema600_40_momentum.py | equity | daily | significance (t=1.05 vs SPY NO_ALPHA_BETA #773), walk-forward params drift | Dead | Fails temporal discipline + NO_ALPHA_BETA peer verdict; EQUITY closed as beta, not a source of edge |
| F2 | LGBM feature engineering + VWAP | baby_strategies/kimi_lgbm_features.py | equity | daily | shuffle control (shuffled price series also profits), look-ahead bias in feature pipeline | Dead | Pipeline leak — future data leaked into feature computation |
| F3 | VPIN + LGBM ensemble | baby_strategies/kimi_vpin_lgbm_ensemble.py | equity | daily | significance (IC ≈ 0 after cost-adjustment), walk-forward efficiency < 50% | Near-miss | Edge exists but too small to harvest after costs; N trades insufficient |
| F4 | VPIN mean reversion | baby_strategies/kimi_vpin_reversion.py | equity | daily | walk-forward stability (params drift between windows), regime dependence | Dead | Works only in bull markets; fails in sideways/ bear |
| F5 | Volatility-momentum blend | baby_strategies/kimi_volatility_momentum_blend.py | equity | daily | Monte Carlo (wide spread, 68% negative paths after costs), friction model | Near-miss | Edge survives in-sample but vanishes under realistic costs + MC resampling |
| F6 | Quality-momentum factor | alpha_engine/advanced_strategies.py | equity | daily | significance vs SPY (excess +0.323% n=738, p=0.12), multiple testing deflated Sharpe | Dead | 52 tests project-wide; deflated Sharpe falls below threshold |
| F7 | Dual momentum (absolute + relative) | alpha_engine/advanced_strategies.py | equity | weekly | walk-forward stability (parameter drift > 30% between windows), regime dependence | Dead | Survives only in trending regimes; whipsaw in sideways markets |
| F8 | Risk parity allocation | alpha_engine/advanced_risk_system.py | multi_asset | weekly | walk-forward stability (consistency_score 0.5 threshold met, but real capital loss), friction model | Near-miss | Cost-adjusted PF ≈ 1.00, just at gate; marginal at real-capital scale |
| F9 | Crypto breakout + funding carry | alpha_engine/btc_breakout_strategy.py | crypto | hourly/daily | shuffle control FAIL (shuffled Bitcoin also profits), look-ahead bias | Dead | Pipeline bug: future return data leaked into breakout detection |
| F10 | Prediction market consensus (Kalshi/Polymarket) | alpha_engine/prediction_market_consensus.py | prediction_market | daily | structural zero-sum + bot dominance (not a signal failure per se), fees kill edge | Dead | Zero-sum nature + adverse selection + maker-taker fees; copy-trading cannot overcome |
| F11 | Token unlock timing signals | alpha_engine/token_unlock_signals.py | crypto | event-driven | Monte Carlo (wide spread), insufficient n trades | Near-miss | Event frequency too low; N < 30 after 2 years of data |
| F12 | COT + momentum commodity timing | alpha_engine/advanced_strategies.py | commodity | weekly | walk-forward stability borderline, significance vs buy-and-hold borderline | Near-miss | Survives in-sample; OOS performance erodes after cost model applied |
| F13 | FX carry + trend | alpha_engine/forex_carry_trend.py | forex | daily | friction model (spread erodes edge completely), Monte Carlo all negative paths | Dead | 0.1% round-turn spread erodes any edge; PF < 1.0 after costs |
| F14 | Turtles-style fixed-fractional position sizing | analysis/walkforward_optimizer.py | multi_asset | daily | walk-forward params drift, multiple testing (project-wide 1307 backtest configs) | Dead | Overfitted to specific volatility regime; no robustness across regimes |
| F15 | Bayesian regime-switching model | alpha_engine/bayesian_regime_reference.py | multi_asset | daily | shuffle control FAIL, regime detection unstable across windows | Dead | Regime labels change between adjacent windows; not auditable |
| F16 | HMM hidden-state momentum | analysis/score_calibration.py | equity | daily | significance (but only in-sample), walk-forward efficiency < 40% | Near-miss | OOS performance collapses; signal not stable |
| F17 | Conformal prediction sizing | alpha_engine/conformal_sizing.py | multi_asset | per_trade | passes significance + MC, but fails walk-forward consistency | Near-miss | Calibration interval too wide for practical position sizing |
| F18 | Grid search parameter optimization | alpha_engine/auto_tuner.py | multi_asset | grid_search | multiple testing dominates (100s of grid points), overfitting guaranteed | Dead | p-hacking across grid; no out-of-sample survival |
| F19 | Sterling ratio drawdown assessment | audit_trail/mercury2_scoring.py | multi_asset | weekly | significance vs benchmark, but fails Monte Carlo % positive paths | Near-miss | Drawdown distribution has fat tails; 5th percentile very negative |
| F20 | Block bootstrap confidence intervals | analysis/score_calibration.py | multi_asset | post_hoc | significance CI includes zero after block bootstrap preserving autocorrelation | Dead | True edge indistinguishable from noise when autocorrelation accounted for |
| F21 | Kelly fractional position sizing + 3x cost gate | tools/per_class_cost_gate.py | multi_asset | per_trade | friction model exactly at gate threshold (PF ≈ 1.00), default ON but borderline | Near-miss | Cost multiple = 3.0; any slippage pushes PF below 1.0 |
| F22 | Walker-forward with min_train_trades=20 | analysis/walkforward_optimizer.py | multi_asset | daily | walk-forward consistency meets threshold but forward PF < 1.15 | Near-miss | WFO passes internal consistency; fails forward OOS test |
| F23 | FDR single-source gate enforcement | alpha_engine/money_ready_verdict.py | multi_asset | weekly | FDR gate=0 (OFF by default); single-source gate OFF | Dead | Gates not enabled; promotion would be fail-closed without them |
| F24 | Gap-aware fill resolver (crypto only) | audit_trail/universal_pick_resolver.py | crypto | hourly | B4 resolved for crypto; fails if applied to non-crypto exits | Dead | Gap-aware makes EQUITY worse (−83.62 vs −63.41pp); misapplied |
| F25 | Intrabar resolver for kimi scanner | baby_strategies/kimi_cursor_v04.py | equity | daily | resolves B4 exit-fill mismatch; improves PF but still below gate | Near-miss | PF improves from 0.768→~0.80 but still fails PF≥1.15 gate |
| F26 | ATR-based trailing stop variations | alpha_engine/advanced_risk_system.py | multi_asset | trailing_stop | walk-forward stability borderline, significance vs SPY borderline | Near-miss | Stop distance optim regime-dependent; no single ATR multiple works universally |
| F27 | Mean reversion on meanervpind | baby_strategies/kimi_vpin_reversion.py | equity | daily | significance vs SPY borderline, fails walk-forward OOS | Near-miss | In-sample IC positive; OOS IC collapses |
| F28 | Portfolio equal-risk-parity combination | analysis/portfolio_manager.py | multi_asset | weekly | passes individual signal gates but fails combination multiple testing | Dead | Deflated Sharpe on combined strategy falls below threshold after 5-signal pool |
| F29 | Random forest classification on features | alpha_engine/advanced_statistical_strategies.py | equity | daily | shuffle control FAIL, look-ahead in feature pipeline | Dead | Same bug class as F2 — future data in features |
| F30 | Transformer sequence model on OHLCV | alpha_engine/advanced_statistical_strategies.py | crypto | daily | Monte Carlo all negative paths, insufficient n trades | Dead | Daily crypto data insufficient for transformer; N << required 500+ |

---

## Summary

- **Total strategies catalogued:** 30 failure-mode entries
- **Dead:** F1, F2, F6, F9, F14, F17, F20, F23, F24, F28, F28, F29, F30 = 13
- **Near-miss:** F3, F5, F8, F10(?), F12, F16, F19, F21, F22, F25, F26, F27 = 12
- **Passed all 10:** NONE (0/30)
- **Prediction markets structural failure:** F10 — zero-sum + bot dominance + fees, not recoverable by parameter tweak
- **Critical finding:** The only strategies that come closest to passing are near-misses failing only on sample size/costs (F3, F5, F21) — these are worth paper-trading extensions, not deployment
- **Repository-wide learning:** Every single attempted signal either fails temporal discipline, shuffle control, walk-forward stability, significance, or the friction model. Zero survived the full proof standard.

**Key repo-wide patterns:**
1. Look-ahead bias in feature engineering (F2, F28, F29) — the most common code bug
2. Walk-forward parameter drift (F4, F7, F15, F22) — parameters optimized to in-sample, not OOS
3. Friction model erodes all edges (F5, F13, F21, F26) — costs + slippage + spread
4. Shuffle control failures (F2, F9, F15, F29) — always indicates a pipeline bug, not a market fact
5. Prediction markets are structurally unrewarding for retail copy-trading (F10)