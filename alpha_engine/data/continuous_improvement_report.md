# Continuous Improvement Report

Generated: 2026-05-23T11:43:36.564783+00:00

## Topline
- Open positions: 84
- Price coverage: 100.0%
- Open average PnL: 30.9605%
- Directional correctness: 48.81%
- Regime: BEARISH

## Alerts
- [CRITICAL] PORTFOLIO_DRAWDOWN_BREACH: Paper portfolio derivatives hit 10.15% drawdown
- [HIGH] PEER_STALE: alpha_engine data is stale (83489.6m old)
- [HIGH] PEER_STALE: copy_trader_intel data is stale (128.9m old)
- [HIGH] PEER_STALE: paper_trading data is stale (111782.6m old)
- [HIGH] STRATEGY_DECAY: fx_smart_carry_trade_momentum is a rehabilitation candidate (WR 6.25%, PF 0.046, Sharpe -28.944)
- [MEDIUM] PEER_DIRECTION_CONFLICT: Peer systems disagree on SOLUSDT ({'LONG': 1, 'SHORT': 5})

## Recommendations
- tighten_risk_and_reduce_gross_exposure: Choppy regime or drawdown breach warrants smaller sizing and tighter review cadence.
- refresh_local_monitors: Data freshness or pricing gaps need a local refresh cycle before acting on signals. (`refresh_kpis`)
- route_fx_smart_carry_trade_momentum_to_mutation_or_inverse: fx_smart_carry_trade_momentum is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- route_bollinger_squeeze_to_mutation_or_inverse: bollinger_squeeze is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- route_clone_hl_copy_Auros_66M_to_mutation_or_inverse: clone_hl_copy_Auros_66M is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`copytrader_mutation_extract`)
- review_symbol_level_peer_conflicts: Conflicting peer directions can indicate regime disagreement or stale assumptions. (`refresh_portfolio_monitor`)
- prefer_validated_leaders_for_next_cycle: Current leaders are ml_enhanced_ZKUSDT_4h_D_ensemble_stack. Bias new risk toward proven survivors.