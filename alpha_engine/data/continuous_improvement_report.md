# Continuous Improvement Report

Generated: 2026-05-25T13:01:42.727206+00:00

## Topline
- Open positions: 102
- Price coverage: 99.02%
- Open average PnL: 24.2337%
- Directional correctness: 51.49%
- Regime: CHOPPY

## Alerts
- [CRITICAL] PORTFOLIO_DRAWDOWN_BREACH: Paper portfolio derivatives hit 10.15% drawdown
- [HIGH] PEER_STALE: alpha_engine data is stale (86447.7m old)
- [HIGH] PEER_STALE: copy_trader_intel data is stale (155.0m old)
- [HIGH] PEER_STALE: paper_trading data is stale (114740.8m old)
- [HIGH] STRATEGY_DECAY: fx_smart_carry_trade_momentum is a rehabilitation candidate (WR 33.33%, PF 0.252, Sharpe -11.049)
- [MEDIUM] PEER_DIRECTION_CONFLICT: Peer systems disagree on SOLUSDT ({'LONG': 1, 'SHORT': 5})

## Recommendations
- tighten_risk_and_reduce_gross_exposure: Choppy regime or drawdown breach warrants smaller sizing and tighter review cadence.
- refresh_local_monitors: Data freshness or pricing gaps need a local refresh cycle before acting on signals. (`refresh_kpis`)
- route_fx_smart_carry_trade_momentum_to_mutation_or_inverse: fx_smart_carry_trade_momentum is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- route_quan_engine_swing_to_mutation_or_inverse: quan_engine_swing is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- route_forex_rsi2_mean_reversion_to_mutation_or_inverse: forex_rsi2_mean_reversion is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- review_symbol_level_peer_conflicts: Conflicting peer directions can indicate regime disagreement or stale assumptions. (`refresh_portfolio_monitor`)
- prefer_validated_leaders_for_next_cycle: Current leaders are ml_enhanced_ZKUSDT_4h_D_ensemble_stack, luxalgo_confluence, combined_confidence. Bias new risk toward proven survivors.