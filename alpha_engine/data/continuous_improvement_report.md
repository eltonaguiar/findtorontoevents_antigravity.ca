# Continuous Improvement Report

Generated: 2026-05-23T09:19:13.573371+00:00

## Topline
- Open positions: 102
- Price coverage: 89.22%
- Open average PnL: 435190.6558%
- Directional correctness: 38.46%
- Regime: BEARISH

## Alerts
- [CRITICAL] PORTFOLIO_DRAWDOWN_BREACH: Paper portfolio derivatives hit 10.15% drawdown
- [HIGH] PEER_STALE: alpha_engine data is stale (83345.2m old)
- [HIGH] PEER_STALE: paper_trading data is stale (111638.3m old)
- [HIGH] STRATEGY_DECAY: cta_commodity_momentum_term is a rehabilitation candidate (WR 0.0%, PF 0.0, Sharpe -130.155)
- [MEDIUM] PEER_DIRECTION_CONFLICT: Peer systems disagree on BNBUSDT ({'LONG': 4, 'SHORT': 3})

## Recommendations
- tighten_risk_and_reduce_gross_exposure: Choppy regime or drawdown breach warrants smaller sizing and tighter review cadence.
- refresh_local_monitors: Data freshness or pricing gaps need a local refresh cycle before acting on signals. (`refresh_kpis`)
- route_cta_commodity_momentum_term_to_mutation_or_inverse: cta_commodity_momentum_term is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- route_futures_momentum_to_mutation_or_inverse: futures_momentum is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- route_myfxbook_retail_contrarian_to_mutation_or_inverse: myfxbook_retail_contrarian is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- review_symbol_level_peer_conflicts: Conflicting peer directions can indicate regime disagreement or stale assumptions. (`refresh_portfolio_monitor`)
- prefer_validated_leaders_for_next_cycle: Current leaders are cg_whale_divergence, ml_enhanced_ZKUSDT_4h_D_ensemble_stack, ml_enhanced_BNBUSDT_15m_B_lightgbm. Bias new risk toward proven survivors.