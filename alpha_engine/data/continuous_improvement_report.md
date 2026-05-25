# Continuous Improvement Report

Generated: 2026-05-25T06:11:17.012360+00:00

## Topline
- Open positions: 129
- Price coverage: 89.92%
- Open average PnL: 29.2439%
- Directional correctness: 59.48%
- Regime: CHOPPY

## Alerts
- [CRITICAL] PORTFOLIO_DRAWDOWN_BREACH: Paper portfolio derivatives hit 10.15% drawdown
- [HIGH] CONFIDENCE_INVERSION: High-confidence picks are underperforming low-confidence picks (55.2% vs 69.4%)
- [HIGH] PEER_STALE: alpha_engine data is stale (86037.2m old)
- [HIGH] PEER_STALE: copy_trader_intel data is stale (101.7m old)
- [HIGH] PEER_STALE: paper_trading data is stale (114330.3m old)
- [HIGH] STRATEGY_DECAY: ml_enhanced_TRXUSDT_1d_B_lightgbm is a rehabilitation candidate (WR 11.54%, PF 0.003, Sharpe -32.451)
- [MEDIUM] PEER_DIRECTION_CONFLICT: Peer systems disagree on BTCUSDT ({'SHORT': 4, 'LONG': 2})

## Recommendations
- tighten_risk_and_reduce_gross_exposure: Choppy regime or drawdown breach warrants smaller sizing and tighter review cadence.
- refresh_local_monitors: Data freshness or pricing gaps need a local refresh cycle before acting on signals. (`refresh_kpis`)
- audit_confidence_calibration: High-confidence picks are not earning their weight; calibration likely drifted. (`refresh_pick_quality`)
- route_ml_enhanced_TRXUSDT_1d_B_lightgbm_to_mutation_or_inverse: ml_enhanced_TRXUSDT_1d_B_lightgbm is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- route_cot_positioning_to_mutation_or_inverse: cot_positioning is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- route_ml_enhanced_JTOUSDT_1d_B_lightgbm_to_mutation_or_inverse: ml_enhanced_JTOUSDT_1d_B_lightgbm is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- review_symbol_level_peer_conflicts: Conflicting peer directions can indicate regime disagreement or stale assumptions. (`refresh_portfolio_monitor`)
- prefer_validated_leaders_for_next_cycle: Current leaders are ml_enhanced_ZKUSDT_4h_D_ensemble_stack, ml_enhanced_BNBUSDT_15m_B_lightgbm, luxalgo_confluence. Bias new risk toward proven survivors.