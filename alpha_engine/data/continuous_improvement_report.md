# Continuous Improvement Report

Generated: 2026-05-24T09:30:24.618873+00:00

## Topline
- Open positions: 172
- Price coverage: 95.93%
- Open average PnL: 30.0547%
- Directional correctness: 60.0%
- Regime: BULLISH

## Alerts
- [CRITICAL] PORTFOLIO_DRAWDOWN_BREACH: Paper portfolio derivatives hit 10.15% drawdown
- [HIGH] CONFIDENCE_INVERSION: High-confidence picks are underperforming low-confidence picks (48.4% vs 70.0%)
- [HIGH] PEER_STALE: alpha_engine data is stale (84796.4m old)
- [HIGH] PEER_STALE: paper_trading data is stale (113089.4m old)
- [HIGH] STRATEGY_DECAY: clone_hl_copy_Auros_66M is a rehabilitation candidate (WR 60.0%, PF 0.123, Sharpe -10.511)
- [MEDIUM] PEER_DIRECTION_CONFLICT: Peer systems disagree on BTCUSDT ({'SHORT': 5, 'LONG': 9})

## Recommendations
- tighten_risk_and_reduce_gross_exposure: Choppy regime or drawdown breach warrants smaller sizing and tighter review cadence.
- refresh_local_monitors: Data freshness or pricing gaps need a local refresh cycle before acting on signals. (`refresh_kpis`)
- audit_confidence_calibration: High-confidence picks are not earning their weight; calibration likely drifted. (`refresh_pick_quality`)
- route_clone_hl_copy_Auros_66M_to_mutation_or_inverse: clone_hl_copy_Auros_66M is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- route_clone_hl_copy_lb_None_to_mutation_or_inverse: clone_hl_copy_lb_None is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- route_stocks_rsi2_pullback_to_mutation_or_inverse: stocks_rsi2_pullback is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- review_symbol_level_peer_conflicts: Conflicting peer directions can indicate regime disagreement or stale assumptions. (`refresh_portfolio_monitor`)
- prefer_validated_leaders_for_next_cycle: Current leaders are clone_hl_copy_PensionFund_24M, luxalgo_confluence, quan_engine_swing. Bias new risk toward proven survivors.