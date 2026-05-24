# Continuous Improvement Report

Generated: 2026-05-24T01:31:44.686769+00:00

## Topline
- Open positions: 169
- Price coverage: 92.9%
- Open average PnL: 27.705%
- Directional correctness: 55.41%
- Regime: CHOPPY

## Alerts
- [CRITICAL] PORTFOLIO_DRAWDOWN_BREACH: Paper portfolio derivatives hit 10.15% drawdown
- [HIGH] PEER_STALE: alpha_engine data is stale (84317.7m old)
- [HIGH] PEER_STALE: copy_trader_intel data is stale (132.2m old)
- [HIGH] PEER_STALE: paper_trading data is stale (112610.8m old)
- [HIGH] STRATEGY_DECAY: cta_commodity_momentum_term is a rehabilitation candidate (WR 0.0%, PF 0.0, Sharpe -140.452)
- [MEDIUM] PEER_DIRECTION_CONFLICT: Peer systems disagree on BNBUSDT ({'SHORT': 5, 'LONG': 6})

## Recommendations
- tighten_risk_and_reduce_gross_exposure: Choppy regime or drawdown breach warrants smaller sizing and tighter review cadence.
- refresh_local_monitors: Data freshness or pricing gaps need a local refresh cycle before acting on signals. (`refresh_kpis`)
- route_cta_commodity_momentum_term_to_mutation_or_inverse: cta_commodity_momentum_term is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- route_fx_smart_carry_trade_momentum_to_mutation_or_inverse: fx_smart_carry_trade_momentum is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- route_futures_momentum_to_mutation_or_inverse: futures_momentum is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- review_symbol_level_peer_conflicts: Conflicting peer directions can indicate regime disagreement or stale assumptions. (`refresh_portfolio_monitor`)
- prefer_validated_leaders_for_next_cycle: Current leaders are clone_hl_copy_PensionFund_24M, luxalgo_confluence. Bias new risk toward proven survivors.