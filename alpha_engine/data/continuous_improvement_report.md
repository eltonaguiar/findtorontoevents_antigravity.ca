# Continuous Improvement Report

Generated: 2026-05-24T04:04:54.436017+00:00

## Topline
- Open positions: 139
- Price coverage: 97.12%
- Open average PnL: 31.5784%
- Directional correctness: 58.52%
- Regime: CHOPPY

## Alerts
- [CRITICAL] PORTFOLIO_DRAWDOWN_BREACH: Paper portfolio derivatives hit 10.15% drawdown
- [HIGH] PEER_STALE: alpha_engine data is stale (84470.9m old)
- [HIGH] PEER_STALE: copy_trader_intel data is stale (66.9m old)
- [HIGH] PEER_STALE: paper_trading data is stale (112763.9m old)
- [HIGH] STRATEGY_DECAY: fx_smart_carry_trade_momentum is a rehabilitation candidate (WR 6.25%, PF 0.046, Sharpe -28.944)
- [MEDIUM] PEER_DIRECTION_CONFLICT: Peer systems disagree on BTCUSDT ({'LONG': 6, 'SHORT': 4})

## Recommendations
- tighten_risk_and_reduce_gross_exposure: Choppy regime or drawdown breach warrants smaller sizing and tighter review cadence.
- refresh_local_monitors: Data freshness or pricing gaps need a local refresh cycle before acting on signals. (`refresh_kpis`)
- route_fx_smart_carry_trade_momentum_to_mutation_or_inverse: fx_smart_carry_trade_momentum is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- route_clone_hl_copy_Auros_66M_to_mutation_or_inverse: clone_hl_copy_Auros_66M is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`copytrader_mutation_extract`)
- route_cta_cross_asset_tsmom_to_mutation_or_inverse: cta_cross_asset_tsmom is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- review_symbol_level_peer_conflicts: Conflicting peer directions can indicate regime disagreement or stale assumptions. (`refresh_portfolio_monitor`)
- prefer_validated_leaders_for_next_cycle: Current leaders are clone_hl_copy_PensionFund_24M, luxalgo_confluence, claude_ml_moderate_mut. Bias new risk toward proven survivors.