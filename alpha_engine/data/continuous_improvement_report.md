# Continuous Improvement Report

Generated: 2026-05-24T16:49:42.654286+00:00

## Topline
- Open positions: 94
- Price coverage: 98.94%
- Open average PnL: 21.6484%
- Directional correctness: 43.01%
- Regime: CHOPPY

## Alerts
- [CRITICAL] PORTFOLIO_DRAWDOWN_BREACH: Paper portfolio derivatives hit 10.15% drawdown
- [HIGH] PEER_STALE: alpha_engine data is stale (85235.7m old)
- [HIGH] PEER_STALE: copy_trader_intel data is stale (202.3m old)
- [HIGH] PEER_STALE: paper_trading data is stale (113528.8m old)
- [HIGH] STRATEGY_DECAY: ml_enhanced_JTOUSDT_1d_B_lightgbm is a rehabilitation candidate (WR 36.67%, PF 0.297, Sharpe -8.277)
- [MEDIUM] PEER_DIRECTION_CONFLICT: Peer systems disagree on XRPUSDT ({'LONG': 2, 'SHORT': 4})
- [MEDIUM] REGIME_SHIFT: Regime changed BULLISH -> CHOPPY

## Recommendations
- tighten_risk_and_reduce_gross_exposure: Choppy regime or drawdown breach warrants smaller sizing and tighter review cadence.
- refresh_local_monitors: Data freshness or pricing gaps need a local refresh cycle before acting on signals. (`refresh_kpis`)
- route_ml_enhanced_JTOUSDT_1d_B_lightgbm_to_mutation_or_inverse: ml_enhanced_JTOUSDT_1d_B_lightgbm is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- route_claude_ml_moderate_mut_to_mutation_or_inverse: claude_ml_moderate_mut is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- route_stocks_rsi2_pullback_to_mutation_or_inverse: stocks_rsi2_pullback is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- review_symbol_level_peer_conflicts: Conflicting peer directions can indicate regime disagreement or stale assumptions. (`refresh_portfolio_monitor`)
- prefer_validated_leaders_for_next_cycle: Current leaders are luxalgo_confluence, quan_engine_swing. Bias new risk toward proven survivors.