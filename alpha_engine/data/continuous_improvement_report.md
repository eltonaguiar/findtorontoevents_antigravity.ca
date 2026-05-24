# Continuous Improvement Report

Generated: 2026-05-24T17:02:46.029784+00:00

## Topline
- Open positions: 192
- Price coverage: 90.62%
- Open average PnL: 21.6941%
- Directional correctness: 54.02%
- Regime: CHOPPY

## Alerts
- [CRITICAL] PORTFOLIO_DRAWDOWN_BREACH: Paper portfolio derivatives hit 10.15% drawdown
- [HIGH] CONFIDENCE_INVERSION: High-confidence picks are underperforming low-confidence picks (50.0% vs 67.1%)
- [HIGH] PEER_STALE: alpha_engine data is stale (85248.7m old)
- [HIGH] PEER_STALE: copy_trader_intel data is stale (215.4m old)
- [HIGH] PEER_STALE: paper_trading data is stale (113541.8m old)
- [HIGH] STRATEGY_DECAY: cta_commodity_momentum_term is a rehabilitation candidate (WR 0.0%, PF 0.0, Sharpe -140.452)
- [MEDIUM] PEER_DIRECTION_CONFLICT: Peer systems disagree on XRPUSDT ({'LONG': 4, 'SHORT': 4})

## Recommendations
- tighten_risk_and_reduce_gross_exposure: Choppy regime or drawdown breach warrants smaller sizing and tighter review cadence.
- refresh_local_monitors: Data freshness or pricing gaps need a local refresh cycle before acting on signals. (`refresh_kpis`)
- audit_confidence_calibration: High-confidence picks are not earning their weight; calibration likely drifted. (`refresh_pick_quality`)
- route_cta_commodity_momentum_term_to_mutation_or_inverse: cta_commodity_momentum_term is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- route_ml_enhanced_TRXUSDT_1d_B_lightgbm_to_mutation_or_inverse: ml_enhanced_TRXUSDT_1d_B_lightgbm is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- route_cot_positioning_to_mutation_or_inverse: cot_positioning is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- review_symbol_level_peer_conflicts: Conflicting peer directions can indicate regime disagreement or stale assumptions. (`refresh_portfolio_monitor`)
- prefer_validated_leaders_for_next_cycle: Current leaders are ml_enhanced_ZKUSDT_4h_D_ensemble_stack, ml_enhanced_BNBUSDT_15m_B_lightgbm, luxalgo_confluence. Bias new risk toward proven survivors.