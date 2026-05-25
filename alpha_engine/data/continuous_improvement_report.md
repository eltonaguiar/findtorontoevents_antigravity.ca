# Continuous Improvement Report

Generated: 2026-05-25T04:00:53.338311+00:00

## Topline
- Open positions: 116
- Price coverage: 99.14%
- Open average PnL: -76.8666%
- Directional correctness: 50.43%
- Regime: CHOPPY

## Alerts
- [CRITICAL] PORTFOLIO_DRAWDOWN_BREACH: Paper portfolio derivatives hit 10.15% drawdown
- [HIGH] PEER_STALE: alpha_engine data is stale (85906.9m old)
- [HIGH] PEER_STALE: copy_trader_intel data is stale (63.2m old)
- [HIGH] PEER_STALE: paper_trading data is stale (114199.9m old)
- [HIGH] STRATEGY_DECAY: ml_enhanced_POLUSDT_1d_B_lightgbm is a rehabilitation candidate (WR 48.15%, PF 0.668, Sharpe -2.843)
- [MEDIUM] PEER_DIRECTION_CONFLICT: Peer systems disagree on BNBUSDT ({'LONG': 4, 'SHORT': 3})

## Recommendations
- tighten_risk_and_reduce_gross_exposure: Choppy regime or drawdown breach warrants smaller sizing and tighter review cadence.
- refresh_local_monitors: Data freshness or pricing gaps need a local refresh cycle before acting on signals. (`refresh_kpis`)
- route_ml_enhanced_POLUSDT_1d_B_lightgbm_to_mutation_or_inverse: ml_enhanced_POLUSDT_1d_B_lightgbm is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- route_claude_ml_moderate_mut_to_mutation_or_inverse: claude_ml_moderate_mut is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- route_quan_engine_swing_to_mutation_or_inverse: quan_engine_swing is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- review_symbol_level_peer_conflicts: Conflicting peer directions can indicate regime disagreement or stale assumptions. (`refresh_portfolio_monitor`)
- prefer_validated_leaders_for_next_cycle: Current leaders are ml_enhanced_ZKUSDT_4h_D_ensemble_stack, ml_enhanced_BNBUSDT_15m_B_lightgbm, luxalgo_confluence. Bias new risk toward proven survivors.