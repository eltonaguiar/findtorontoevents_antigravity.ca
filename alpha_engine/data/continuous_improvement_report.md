# Continuous Improvement Report

Generated: 2026-05-25T13:48:47.164830+00:00

## Topline
- Open positions: 158
- Price coverage: 88.61%
- Open average PnL: 23.9548%
- Directional correctness: 52.14%
- Regime: CHOPPY

## Alerts
- [CRITICAL] PORTFOLIO_DRAWDOWN_BREACH: Paper portfolio derivatives hit 10.15% drawdown
- [HIGH] PEER_STALE: alpha_engine data is stale (86494.7m old)
- [HIGH] PEER_STALE: copy_trader_intel data is stale (96.8m old)
- [HIGH] PEER_STALE: paper_trading data is stale (114787.8m old)
- [HIGH] STRATEGY_DECAY: fx_smart_carry_trade_momentum is a rehabilitation candidate (WR 33.33%, PF 0.252, Sharpe -11.049)
- [MEDIUM] PEER_DIRECTION_CONFLICT: Peer systems disagree on BTCUSDT ({'LONG': 4, 'SHORT': 4})

## Recommendations
- tighten_risk_and_reduce_gross_exposure: Choppy regime or drawdown breach warrants smaller sizing and tighter review cadence.
- refresh_local_monitors: Data freshness or pricing gaps need a local refresh cycle before acting on signals. (`refresh_kpis`)
- route_fx_smart_carry_trade_momentum_to_mutation_or_inverse: fx_smart_carry_trade_momentum is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- route_cot_positioning_to_mutation_or_inverse: cot_positioning is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- route_futures_momentum_to_mutation_or_inverse: futures_momentum is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- review_symbol_level_peer_conflicts: Conflicting peer directions can indicate regime disagreement or stale assumptions. (`refresh_portfolio_monitor`)
- prefer_validated_leaders_for_next_cycle: Current leaders are ml_enhanced_ZKUSDT_4h_D_ensemble_stack, ml_enhanced_BNBUSDT_15m_B_lightgbm, luxalgo_confluence. Bias new risk toward proven survivors.