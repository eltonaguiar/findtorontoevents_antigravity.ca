# Continuous Improvement Report

Generated: 2026-05-25T08:12:06.218783+00:00

## Topline
- Open positions: 183
- Price coverage: 90.16%
- Open average PnL: 35.3216%
- Directional correctness: 64.24%
- Regime: CHOPPY

## Alerts
- [CRITICAL] PORTFOLIO_DRAWDOWN_BREACH: Paper portfolio derivatives hit 10.15% drawdown
- [HIGH] CONFIDENCE_INVERSION: High-confidence picks are underperforming low-confidence picks (55.2% vs 74.0%)
- [HIGH] PEER_STALE: alpha_engine data is stale (86158.1m old)
- [HIGH] PEER_STALE: copy_trader_intel data is stale (103.5m old)
- [HIGH] PEER_STALE: paper_trading data is stale (114451.1m old)
- [HIGH] STRATEGY_DECAY: ml_enhanced_TRXUSDT_1d_B_lightgbm is a rehabilitation candidate (WR 11.54%, PF 0.003, Sharpe -32.451)
- [MEDIUM] PEER_DIRECTION_CONFLICT: Peer systems disagree on BTCUSDT ({'SHORT': 5, 'LONG': 6})

## Recommendations
- tighten_risk_and_reduce_gross_exposure: Choppy regime or drawdown breach warrants smaller sizing and tighter review cadence.
- refresh_local_monitors: Data freshness or pricing gaps need a local refresh cycle before acting on signals. (`refresh_kpis`)
- audit_confidence_calibration: High-confidence picks are not earning their weight; calibration likely drifted. (`refresh_pick_quality`)
- route_ml_enhanced_TRXUSDT_1d_B_lightgbm_to_mutation_or_inverse: ml_enhanced_TRXUSDT_1d_B_lightgbm is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- route_fx_smart_carry_trade_momentum_to_mutation_or_inverse: fx_smart_carry_trade_momentum is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- route_clone_hl_copy_Auros_66M_to_mutation_or_inverse: clone_hl_copy_Auros_66M is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`copytrader_mutation_extract`)
- review_symbol_level_peer_conflicts: Conflicting peer directions can indicate regime disagreement or stale assumptions. (`refresh_portfolio_monitor`)
- prefer_validated_leaders_for_next_cycle: Current leaders are ml_enhanced_ZKUSDT_4h_D_ensemble_stack, ml_enhanced_BNBUSDT_15m_B_lightgbm, clone_hl_copy_PensionFund_24M. Bias new risk toward proven survivors.