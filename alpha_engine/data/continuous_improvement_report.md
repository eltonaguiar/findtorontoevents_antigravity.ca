# Continuous Improvement Report

Generated: 2026-05-23T12:18:31.310542+00:00

## Topline
- Open positions: 142
- Price coverage: 97.89%
- Open average PnL: 16.1964%
- Directional correctness: 48.2%
- Regime: BEARISH

## Alerts
- [CRITICAL] PORTFOLIO_DRAWDOWN_BREACH: Paper portfolio derivatives hit 10.15% drawdown
- [HIGH] PEER_STALE: alpha_engine data is stale (83524.5m old)
- [HIGH] PEER_STALE: copy_trader_intel data is stale (108.9m old)
- [HIGH] PEER_STALE: paper_trading data is stale (111817.6m old)
- [HIGH] STRATEGY_DECAY: claude_ml_moderate_mut is a rehabilitation candidate (WR 0.0%, PF 0.0, Sharpe -35.449)
- [MEDIUM] PEER_DIRECTION_CONFLICT: Peer systems disagree on BTCUSDT ({'LONG': 6, 'SHORT': 4})

## Recommendations
- tighten_risk_and_reduce_gross_exposure: Choppy regime or drawdown breach warrants smaller sizing and tighter review cadence.
- refresh_local_monitors: Data freshness or pricing gaps need a local refresh cycle before acting on signals. (`refresh_kpis`)
- route_claude_ml_moderate_mut_to_mutation_or_inverse: claude_ml_moderate_mut is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- route_fx_smart_carry_trade_momentum_to_mutation_or_inverse: fx_smart_carry_trade_momentum is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- route_clone_hl_copy_Auros_66M_to_mutation_or_inverse: clone_hl_copy_Auros_66M is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`copytrader_mutation_extract`)
- review_symbol_level_peer_conflicts: Conflicting peer directions can indicate regime disagreement or stale assumptions. (`refresh_portfolio_monitor`)
- prefer_validated_leaders_for_next_cycle: Current leaders are clone_hl_copy_PensionFund_24M. Bias new risk toward proven survivors.