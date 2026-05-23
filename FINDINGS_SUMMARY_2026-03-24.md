# FINDINGS_SUMMARY_2026-03-24

## 1. Audit Findings
- **Battleground (Superpowers Arena)**: Top performer at 64.1% WR, +1357% PnL across 334 trades; 10 survivor strategies avg 63.7% WR [`AUDIT_REPORT_2026-03-06.md`](AUDIT_REPORT_2026-03-06.md).
  - High-performers: Keltner Mean Rev (67.6% WR, Sharpe 2.06), Connors R3 (71.4%, 1.53), Connors RSI-2 (68.4%, 1.17), MACD Divergence (67.8%).
- **Alpha Engine**: Positive PnL ($USD) but lower 35.9% WR (156 trades); standouts like autocorrelation_exploiter (83% WR, +$1459), multi_sigma_reversal (100% small N) [`AUDIT_REPORT_2026-03-06.md`](AUDIT_REPORT_2026-03-06.md), [`AUDIT_VARIATIONS_2026-03-08.md`](AUDIT_VARIATIONS_2026-03-08.md).
- **Baby Strats**: Retired (-5433% PnL, 41.8% WR); DNA evolution yielded 5 winners avg 68% WR, Sharpe 1.59 [`audit_summary_2026-03-02.md`](audit_summary_2026-03-02.md).
- **Issues/Outliers**: Signal conflicts (e.g., BTC long/short), tight R:R (slippage risk), missing filters (HMA slope, vol expansion); Feb audit showed 0 forward trades in many, ~39% aggregate WR [`AUDIT_REPORT_2026-02-18.md`](AUDIT_REPORT_2026-02-18.md).
- **New Developments**: Audit Ensemble evolver (68% WR proxy), variations with HMA/vol filters [`AUDIT_ENSEMBLE_UPDATE_2026-03-09.md`](AUDIT_ENSEMBLE_UPDATE_2026-03-09.md).

## 2. Agent Fleet Performance
- **Deployment**: 22 agents active (11 research, 11 cloners); March 16 deployed 4 new strats (VWAP+RSI, liquidation cascade, regime sentinel, RSI pairs arb) [`AGENT_FLEET_STATUS.md`](AGENT_FLEET_STATUS.md), [`AGENT_DEPLOYMENT_MARCH16.md`](AGENT_DEPLOYMENT_MARCH16.md).
- **Results** (scalping focus):
  | Strategy | WR | Sharpe/Return | Status |
  |----------|----|---------------|--------|
  | Funding Rate Arb | 100% | 21% APR | ⭐⭐⭐⭐⭐ Retail viable |
  | Range Scalping | 0% | -1.16% | Poor in trending mkt [`AGENT_FLEET_RESULTS.md`](AGENT_FLEET_RESULTS.md) |
  | Vol Breakout | 0 trades | N/A | Needs tuning |
  | Cross-Exchange Arb | N/A | Tight spreads | HFT only |
- **Insights**: Credible sources (Reddit u/DevFuturesTrader, Fabio Valentini); focus on funding arb, Asian range for retail.

## 3. Key Strategy Insights
- **Winners**: Battleground survivors (Keltner/Connors); Baby Bundles (7 active, e.g., EMA Ribbon Sharpe 2.69 T2-FULL, Heikin-Ashi 2.45); Alpha advanced_strategies.py (80k chars, 114 strats) [`BABY_BUNDLE_REGISTRY.md`](BABY_BUNDLE_REGISTRY.md).
- **Enhancements**: ATR-scaled TP/SL (2.5:1.5 R:R), HMA slope/vol confirmation, MTF RSI alignment [`AUDIT_REPORT_2026-03-06.md`](AUDIT_REPORT_2026-03-06.md).
- **Risks**: Regime mismatch, conflicts (no net exposure), overfitting (walk-forward demotions), expiration (94% in some).
- **File Structure**: alpha_engine/ (100+ py: backtests, scrapers, tuners); audit py (outliers, PNL, synthetic); baby_strategies (bundles, backtests); battle_test.py rigorous validation.

## 4. Recommendations/Next Steps
- **Immediate**: Fix conflicts/portfolio netting; add dashboard columns (RSI, HMA slope, vol ratio, last10 WR, current PnL); ATR TP/SL everywhere.
- **Short-term**: Promote forward winners (autocorr, multi-sigma); integrate agent strats (funding arb); HMA/vol/MTF filters.
- **Medium**: Regime-conditional routing, correlation filter, WebSocket feeds; full forward pipeline.
- **Project**: Heavy quant/crypto/backtest focus (2026 activity peak); automate audits/blueprints [`AUDIT_BLUEPRINT.md`](AUDIT_BLUEPRINT.md); expand baby bundles to reserved slots.