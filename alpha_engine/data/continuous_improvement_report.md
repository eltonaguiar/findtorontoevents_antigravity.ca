# Continuous Improvement Report

Generated: 2026-05-23T15:01:00.747428+00:00

## Topline
- Open positions: 108
- Price coverage: 100.0%
- Open average PnL: 73.8635%
- Directional correctness: 73.15%
- Regime: BEARISH

## Alerts
- [CRITICAL] PORTFOLIO_DRAWDOWN_BREACH: Paper portfolio derivatives hit 10.15% drawdown
- [HIGH] CONFIDENCE_INVERSION: High-confidence picks are underperforming low-confidence picks (67.9% vs 91.8%)
- [HIGH] PEER_STALE: alpha_engine data is stale (83687.0m old)
- [HIGH] PEER_STALE: copy_trader_intel data is stale (93.5m old)
- [HIGH] PEER_STALE: paper_trading data is stale (111980.1m old)
- [HIGH] STRATEGY_DECAY: claude_ml_moderate_mut is a rehabilitation candidate (WR 0.0%, PF 0.0, Sharpe -67.192)
- [MEDIUM] PEER_DIRECTION_CONFLICT: Peer systems disagree on BNBUSDT ({'LONG': 4, 'SHORT': 3})

## Recommendations
- tighten_risk_and_reduce_gross_exposure: Choppy regime or drawdown breach warrants smaller sizing and tighter review cadence.
- refresh_local_monitors: Data freshness or pricing gaps need a local refresh cycle before acting on signals. (`refresh_kpis`)
- audit_confidence_calibration: High-confidence picks are not earning their weight; calibration likely drifted. (`refresh_pick_quality`)
- route_claude_ml_moderate_mut_to_mutation_or_inverse: claude_ml_moderate_mut is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- route_fx_smart_carry_trade_momentum_to_mutation_or_inverse: fx_smart_carry_trade_momentum is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- route_stocks_rsi2_pullback_to_mutation_or_inverse: stocks_rsi2_pullback is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- review_symbol_level_peer_conflicts: Conflicting peer directions can indicate regime disagreement or stale assumptions. (`refresh_portfolio_monitor`)
- prefer_validated_leaders_for_next_cycle: Current leaders are ml_enhanced_ZKUSDT_4h_D_ensemble_stack. Bias new risk toward proven survivors.