# Continuous Improvement Report

Generated: 2026-05-24T19:18:56.384533+00:00

## Topline
- Open positions: 147
- Price coverage: 97.28%
- Open average PnL: 24.3123%
- Directional correctness: 53.15%
- Regime: CHOPPY

## Alerts
- [CRITICAL] PORTFOLIO_DRAWDOWN_BREACH: Paper portfolio derivatives hit 10.15% drawdown
- [HIGH] PEER_STALE: alpha_engine data is stale (85384.9m old)
- [HIGH] PEER_STALE: copy_trader_intel data is stale (116.9m old)
- [HIGH] PEER_STALE: paper_trading data is stale (113678.0m old)
- [HIGH] STRATEGY_DECAY: clone_hl_copy_Auros_66M is a rehabilitation candidate (WR 60.0%, PF 0.123, Sharpe -10.511)
- [MEDIUM] PEER_DIRECTION_CONFLICT: Peer systems disagree on BTCUSDT ({'SHORT': 4, 'LONG': 6})

## Recommendations
- tighten_risk_and_reduce_gross_exposure: Choppy regime or drawdown breach warrants smaller sizing and tighter review cadence.
- refresh_local_monitors: Data freshness or pricing gaps need a local refresh cycle before acting on signals. (`refresh_kpis`)
- route_clone_hl_copy_Auros_66M_to_mutation_or_inverse: clone_hl_copy_Auros_66M is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`copytrader_mutation_extract`)
- route_claude_ml_moderate_mut_to_mutation_or_inverse: claude_ml_moderate_mut is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- route_clone_hl_copy_lb_None_to_mutation_or_inverse: clone_hl_copy_lb_None is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`copytrader_mutation_extract`)
- review_symbol_level_peer_conflicts: Conflicting peer directions can indicate regime disagreement or stale assumptions. (`refresh_portfolio_monitor`)
- prefer_validated_leaders_for_next_cycle: Current leaders are luxalgo_confluence, clone_hl_copy_PensionFund_24M, quan_engine_swing. Bias new risk toward proven survivors.