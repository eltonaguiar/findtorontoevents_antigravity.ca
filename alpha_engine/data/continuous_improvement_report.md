# Continuous Improvement Report

Generated: 2026-05-24T15:02:36.598979+00:00

## Topline
- Open positions: 129
- Price coverage: 89.92%
- Open average PnL: 13.8653%
- Directional correctness: 47.41%
- Regime: BULLISH

## Alerts
- [CRITICAL] PORTFOLIO_DRAWDOWN_BREACH: Paper portfolio derivatives hit 10.15% drawdown
- [HIGH] PEER_STALE: alpha_engine data is stale (85128.6m old)
- [HIGH] PEER_STALE: copy_trader_intel data is stale (95.2m old)
- [HIGH] PEER_STALE: paper_trading data is stale (113421.6m old)
- [HIGH] STRATEGY_DECAY: futures_momentum is a rehabilitation candidate (WR 5.0%, PF 0.104, Sharpe -15.467)
- [MEDIUM] PEER_DIRECTION_CONFLICT: Peer systems disagree on XRPUSDT ({'LONG': 3, 'SHORT': 4})

## Recommendations
- tighten_risk_and_reduce_gross_exposure: Choppy regime or drawdown breach warrants smaller sizing and tighter review cadence.
- refresh_local_monitors: Data freshness or pricing gaps need a local refresh cycle before acting on signals. (`refresh_kpis`)
- route_futures_momentum_to_mutation_or_inverse: futures_momentum is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- route_cot_positioning_to_mutation_or_inverse: cot_positioning is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- route_ml_enhanced_JTOUSDT_1d_B_lightgbm_to_mutation_or_inverse: ml_enhanced_JTOUSDT_1d_B_lightgbm is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- review_symbol_level_peer_conflicts: Conflicting peer directions can indicate regime disagreement or stale assumptions. (`refresh_portfolio_monitor`)
- prefer_validated_leaders_for_next_cycle: Current leaders are ml_enhanced_ZKUSDT_4h_D_ensemble_stack, ml_enhanced_BNBUSDT_15m_B_lightgbm. Bias new risk toward proven survivors.