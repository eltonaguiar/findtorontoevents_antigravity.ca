# Continuous Improvement Report

Generated: 2026-05-22T21:07:30.194283+00:00

## Topline
- Open positions: 183
- Price coverage: 87.43%
- Open average PnL: 68.2564%
- Directional correctness: 58.75%
- Regime: CHOPPY

## Alerts
- [CRITICAL] PORTFOLIO_DRAWDOWN_BREACH: Paper portfolio derivatives hit 10.15% drawdown
- [HIGH] PEER_STALE: alpha_engine data is stale (82613.5m old)
- [HIGH] PEER_STALE: paper_trading data is stale (110906.6m old)
- [HIGH] STRATEGY_DECAY: ml_enhanced_TRXUSDT is a rehabilitation candidate (WR 0.0%, PF 0.0, Sharpe None)
- [MEDIUM] PEER_DIRECTION_CONFLICT: Peer systems disagree on RENDERUSDT ({'LONG': 7, 'SHORT': 6})

## Recommendations
- tighten_risk_and_reduce_gross_exposure: Choppy regime or drawdown breach warrants smaller sizing and tighter review cadence.
- refresh_local_monitors: Data freshness or pricing gaps need a local refresh cycle before acting on signals. (`refresh_kpis`)
- route_ml_enhanced_TRXUSDT_to_mutation_or_inverse: ml_enhanced_TRXUSDT is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- route_futures_momentum_to_mutation_or_inverse: futures_momentum is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- route_ml_enhanced_ARBUSDT_1h_D_ensemble_stack_to_mutation_or_inverse: ml_enhanced_ARBUSDT_1h_D_ensemble_stack is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- review_symbol_level_peer_conflicts: Conflicting peer directions can indicate regime disagreement or stale assumptions. (`refresh_portfolio_monitor`)