# Continuous Improvement Report

Generated: 2026-05-23T17:03:00.297491+00:00

## Topline
- Open positions: 144
- Price coverage: 97.92%
- Open average PnL: 65.3162%
- Directional correctness: 68.09%
- Regime: CHOPPY

## Alerts
- [CRITICAL] PORTFOLIO_DRAWDOWN_BREACH: Paper portfolio derivatives hit 10.15% drawdown
- [HIGH] CONFIDENCE_INVERSION: High-confidence picks are underperforming low-confidence picks (69.0% vs 90.6%)
- [HIGH] PEER_STALE: alpha_engine data is stale (83809.0m old)
- [HIGH] PEER_STALE: copy_trader_intel data is stale (99.9m old)
- [HIGH] PEER_STALE: paper_trading data is stale (112102.1m old)
- [HIGH] REGIME_SHIFT: Regime changed BEARISH -> CHOPPY while open PnL fell from 88.90% to 65.32%
- [HIGH] STRATEGY_DECAY: fx_smart_carry_trade_momentum is a rehabilitation candidate (WR 6.25%, PF 0.046, Sharpe -28.944)
- [MEDIUM] PEER_DIRECTION_CONFLICT: Peer systems disagree on BTCUSDT ({'LONG': 6, 'SHORT': 4})

## Recommendations
- tighten_risk_and_reduce_gross_exposure: Choppy regime or drawdown breach warrants smaller sizing and tighter review cadence.
- refresh_local_monitors: Data freshness or pricing gaps need a local refresh cycle before acting on signals. (`refresh_kpis`)
- audit_confidence_calibration: High-confidence picks are not earning their weight; calibration likely drifted. (`refresh_pick_quality`)
- route_fx_smart_carry_trade_momentum_to_mutation_or_inverse: fx_smart_carry_trade_momentum is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- route_regime_mild_bear_to_mutation_or_inverse: regime_mild_bear is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- route_clone_hl_copy_Auros_66M_to_mutation_or_inverse: clone_hl_copy_Auros_66M is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`copytrader_mutation_extract`)
- review_symbol_level_peer_conflicts: Conflicting peer directions can indicate regime disagreement or stale assumptions. (`refresh_portfolio_monitor`)
- prefer_validated_leaders_for_next_cycle: Current leaders are ml_enhanced_ZKUSDT_4h_D_ensemble_stack, clone_hl_copy_PensionFund_24M, luxalgo_confluence. Bias new risk toward proven survivors.