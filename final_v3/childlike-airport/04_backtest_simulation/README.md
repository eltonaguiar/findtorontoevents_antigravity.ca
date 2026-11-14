# 04 — Backtest & Simulation Plan (per Proposed Algorithm Fix)

**Date:** 2026-11-14 | **Standard:** reproducible, net-of-cost simulation per fix/algorithm with acceptance criteria and artifacts (config, data hash/window, seed, code rev).

## Global Rules
- Chronological OOS/walk-forward; params selected on train only.
- Costs: fees+spread+slippage (stress 1×/1.5×/2×), funding/roll/borrow/carry; gap-aware fills.
- Metrics: PF, Sharpe, ret/CAGR, MDD, WR, n, PBO/CSCV, DSR/P(SR>0) (effective-N), bootstrap CI, benchmark-relative.
- Robustness: subperiods/bull-bear, per-symbol & pooled, perturbations.
- Artifacts: equity curve, trade list, metrics JSON/MD, reproduction command.

## Per-Fix / Per-Algorithm Simulations

| ID | Fix / Algorithm | Simulation | Data/horizon | Acceptance |
|---|---|---|---|---|
| S1 | PnL/unit & sync fix | Deterministic recompute vs stored vs sampled marks | Eligible picks | 0 sign/calc mismatches; tests pass |
| S2 | Gap-aware fill | Gap-event replay naive vs gap-aware | Known gap bars | No better-than-gap fills |
| S3 | Per-class cost gate | With/without counterfactual | Recent windows/class | Suppresses negative-expectancy classes |
| S4 | Regime-Filtered VWAP-MR core (BTC,ETH,SOL,XRP,ADA) | 70/30 + walk-forward, regime filter, 40% size, cost stress 20/30/50bps, conservative fills | 4h, **>730d exchange** | PF≥1.2–1.5, Sharpe≥1.0, MDD<15–20%, **PBO<0.3**, DSR>0.95, stable core |
| S5 | Vol-Targeted TSMOM (50d+200d, 20% vol) | Daily full-history, subperiods/bear, vol target, realistic costs/funding | 10+ crypto, ≥7y | Robust net edge, CI>0, benchmark-aware |
| S6 | VWAP-MR + TSMOM ensemble | Risk-balanced/regime blend OOS | Core basket | Better risk-adjusted than components |
| S7 | mega_mutation_macd_rsi/ema_momentum | Independent reimpl, path-verified TP/SL, full costs | Independent data | Persists OOS net-of-cost else reject |
| S8 | Walk-Forward Variant C | Raw walk-forward, net costs, expanded universe | Multi-year daily equity/ETF | Gates pass, stable |
| S9 | Faber TAA / sector-neutral QVM | Costed trend/cross-sec vs benchmark | 10–20y ETFs/equities (+MF NAV proxy) | Net risk-adjusted outperformance, controlled MDD |
| S10 | MF low-fee allocation ($0-min subset) | NAV walk-forward, next-NAV, ER/constraints, overlay vs buy-hold | FXAIX/FSKAX/SWPPX/SWTSX/FXNAX+ | Net-of-fee acceptable MDD; overlay justified |
| S11 | Vol-Targeted Bond Trend | Rate-regime stress, carry/duration | Multi-cycle bonds | Robust across regimes |
| S12 | FX momentum + kill-switch | Spread/roll-inclusive, kill-switch stress | Majors/crosses | Survives costs, capped MDD |
| S13 | Commodity trend (post-fix) | Roll/margin-aware on corrected series | Diversified sectors | Net positive, PnL reconciles |

## Order
1. **S1–S3** integrity/gates → 2. **S4–S6** crypto → 3. **S8–S9** equity/ETF → 4. **S10** MF → 5. **S11–S13** post-fix/build.

## Reporting Template
run id, commit, data window/source, universe, params, costs, split, gross/net metrics, equity curve, gate pass/fail, benchmark, failure modes, next actions.
