# Continuous Improvement Report

Generated: 2026-05-24T11:20:05.931577+00:00

## Topline
- Open positions: 102
- Price coverage: 99.02%
- Open average PnL: 33.8256%
- Directional correctness: 55.45%
- Regime: BULLISH

## Alerts
- [CRITICAL] PORTFOLIO_DRAWDOWN_BREACH: Paper portfolio derivatives hit 10.15% drawdown
- [HIGH] CONFIDENCE_INVERSION: High-confidence picks are underperforming low-confidence picks (47.1% vs 73.3%)
- [HIGH] PEER_STALE: alpha_engine data is stale (84906.1m old)
- [HIGH] PEER_STALE: copy_trader_intel data is stale (147.4m old)
- [HIGH] PEER_STALE: paper_trading data is stale (113199.1m old)
- [HIGH] STRATEGY_DECAY: stocks_rsi2_pullback is a rehabilitation candidate (WR 38.71%, PF 1.103, Sharpe 0.734)
- [MEDIUM] PEER_DIRECTION_CONFLICT: Peer systems disagree on XRPUSDT ({'LONG': 2, 'SHORT': 4})

## Recommendations
- tighten_risk_and_reduce_gross_exposure: Choppy regime or drawdown breach warrants smaller sizing and tighter review cadence.
- refresh_local_monitors: Data freshness or pricing gaps need a local refresh cycle before acting on signals. (`refresh_kpis`)
- audit_confidence_calibration: High-confidence picks are not earning their weight; calibration likely drifted. (`refresh_pick_quality`)
- route_stocks_rsi2_pullback_to_mutation_or_inverse: stocks_rsi2_pullback is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- route_forex_rsi2_mean_reversion_to_mutation_or_inverse: forex_rsi2_mean_reversion is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- route_regime_mild_bear_to_mutation_or_inverse: regime_mild_bear is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- review_symbol_level_peer_conflicts: Conflicting peer directions can indicate regime disagreement or stale assumptions. (`refresh_portfolio_monitor`)
- prefer_validated_leaders_for_next_cycle: Current leaders are ml_enhanced_ZKUSDT_4h_D_ensemble_stack, luxalgo_confluence, quan_engine_swing. Bias new risk toward proven survivors.