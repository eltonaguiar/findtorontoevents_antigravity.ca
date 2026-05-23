# Continuous Improvement Report

Generated: 2026-05-23T10:03:40.977900+00:00

## Topline
- Open positions: 102
- Price coverage: 100.0%
- Open average PnL: 29.5783%
- Directional correctness: 45.1%
- Regime: BEARISH

## Alerts
- [CRITICAL] PORTFOLIO_DRAWDOWN_BREACH: Paper portfolio derivatives hit 10.15% drawdown
- [HIGH] PEER_STALE: alpha_engine data is stale (83389.6m old)
- [HIGH] PEER_STALE: copy_trader_intel data is stale (81.4m old)
- [HIGH] PEER_STALE: paper_trading data is stale (111682.7m old)
- [HIGH] STRATEGY_DECAY: fx_smart_carry_trade_momentum is a rehabilitation candidate (WR 14.29%, PF 0.18, Sharpe -14.292)
- [MEDIUM] PEER_DIRECTION_CONFLICT: Peer systems disagree on BTCUSDT ({'LONG': 4, 'SHORT': 3})

## Recommendations
- tighten_risk_and_reduce_gross_exposure: Choppy regime or drawdown breach warrants smaller sizing and tighter review cadence.
- refresh_local_monitors: Data freshness or pricing gaps need a local refresh cycle before acting on signals. (`refresh_kpis`)
- route_fx_smart_carry_trade_momentum_to_mutation_or_inverse: fx_smart_carry_trade_momentum is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- route_cta_cross_asset_tsmom_to_mutation_or_inverse: cta_cross_asset_tsmom is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- route_stocks_rsi2_pullback_to_mutation_or_inverse: stocks_rsi2_pullback is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- review_symbol_level_peer_conflicts: Conflicting peer directions can indicate regime disagreement or stale assumptions. (`refresh_portfolio_monitor`)
- prefer_validated_leaders_for_next_cycle: Current leaders are cg_whale_divergence, ml_enhanced_ZKUSDT_4h_D_ensemble_stack. Bias new risk toward proven survivors.