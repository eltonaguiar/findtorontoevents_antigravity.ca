# Continuous Improvement Report

Generated: 2026-05-25T14:32:06.607350+00:00

## Topline
- Open positions: 103
- Price coverage: 99.03%
- Open average PnL: 37.1872%
- Directional correctness: 55.88%
- Regime: CHOPPY

## Alerts
- [CRITICAL] PORTFOLIO_DRAWDOWN_BREACH: Paper portfolio derivatives hit 10.15% drawdown
- [HIGH] PEER_STALE: alpha_engine data is stale (86538.1m old)
- [HIGH] PEER_STALE: copy_trader_intel data is stale (140.1m old)
- [HIGH] PEER_STALE: paper_trading data is stale (114831.1m old)
- [HIGH] STRATEGY_DECAY: stocks_rsi2_pullback is a rehabilitation candidate (WR 14.29%, PF 0.194, Sharpe -14.028)
- [MEDIUM] PEER_DIRECTION_CONFLICT: Peer systems disagree on XRPUSDT ({'LONG': 2, 'SHORT': 4})

## Recommendations
- tighten_risk_and_reduce_gross_exposure: Choppy regime or drawdown breach warrants smaller sizing and tighter review cadence.
- refresh_local_monitors: Data freshness or pricing gaps need a local refresh cycle before acting on signals. (`refresh_kpis`)
- route_stocks_rsi2_pullback_to_mutation_or_inverse: stocks_rsi2_pullback is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- route_fx_smart_carry_trade_momentum_to_mutation_or_inverse: fx_smart_carry_trade_momentum is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- route_quan_engine_swing_to_mutation_or_inverse: quan_engine_swing is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- review_symbol_level_peer_conflicts: Conflicting peer directions can indicate regime disagreement or stale assumptions. (`refresh_portfolio_monitor`)
- prefer_validated_leaders_for_next_cycle: Current leaders are ml_enhanced_ZKUSDT_4h_D_ensemble_stack, luxalgo_confluence, combined_confidence. Bias new risk toward proven survivors.