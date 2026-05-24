# Continuous Improvement Report

Generated: 2026-05-24T15:21:44.815297+00:00

## Topline
- Open positions: 98
- Price coverage: 98.98%
- Open average PnL: 13.5556%
- Directional correctness: 45.36%
- Regime: BULLISH

## Alerts
- [CRITICAL] PORTFOLIO_DRAWDOWN_BREACH: Paper portfolio derivatives hit 10.15% drawdown
- [HIGH] PEER_STALE: alpha_engine data is stale (85147.7m old)
- [HIGH] PEER_STALE: copy_trader_intel data is stale (114.3m old)
- [HIGH] PEER_STALE: paper_trading data is stale (113440.8m old)
- [HIGH] STRATEGY_DECAY: claude_ml_moderate_mut is a rehabilitation candidate (WR 57.14%, PF 0.969, Sharpe -0.237)
- [MEDIUM] PEER_DIRECTION_CONFLICT: Peer systems disagree on XRPUSDT ({'LONG': 2, 'SHORT': 4})

## Recommendations
- tighten_risk_and_reduce_gross_exposure: Choppy regime or drawdown breach warrants smaller sizing and tighter review cadence.
- refresh_local_monitors: Data freshness or pricing gaps need a local refresh cycle before acting on signals. (`refresh_kpis`)
- route_claude_ml_moderate_mut_to_mutation_or_inverse: claude_ml_moderate_mut is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- route_stocks_rsi2_pullback_to_mutation_or_inverse: stocks_rsi2_pullback is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- route_forex_rsi2_mean_reversion_to_mutation_or_inverse: forex_rsi2_mean_reversion is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- review_symbol_level_peer_conflicts: Conflicting peer directions can indicate regime disagreement or stale assumptions. (`refresh_portfolio_monitor`)
- prefer_validated_leaders_for_next_cycle: Current leaders are ml_enhanced_ZKUSDT_4h_D_ensemble_stack, luxalgo_confluence, quan_engine_swing. Bias new risk toward proven survivors.