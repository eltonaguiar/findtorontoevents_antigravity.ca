# Continuous Improvement Report

Generated: 2026-05-24T09:35:49.864210+00:00

## Topline
- Open positions: 89
- Price coverage: 98.88%
- Open average PnL: 43.9247%
- Directional correctness: 57.95%
- Regime: BULLISH

## Alerts
- [CRITICAL] PORTFOLIO_DRAWDOWN_BREACH: Paper portfolio derivatives hit 10.15% drawdown
- [HIGH] CONFIDENCE_INVERSION: High-confidence picks are underperforming low-confidence picks (53.1% vs 82.6%)
- [HIGH] PEER_STALE: alpha_engine data is stale (84801.8m old)
- [HIGH] PEER_STALE: copy_trader_intel data is stale (196.0m old)
- [HIGH] PEER_STALE: paper_trading data is stale (113094.9m old)
- [HIGH] STRATEGY_DECAY: stocks_rsi2_pullback is a rehabilitation candidate (WR 38.71%, PF 1.103, Sharpe 0.734)
- [MEDIUM] PEER_DIRECTION_CONFLICT: Peer systems disagree on XRPUSDT ({'LONG': 2, 'SHORT': 4})

## Recommendations
- tighten_risk_and_reduce_gross_exposure: Choppy regime or drawdown breach warrants smaller sizing and tighter review cadence.
- refresh_local_monitors: Data freshness or pricing gaps need a local refresh cycle before acting on signals. (`refresh_kpis`)
- audit_confidence_calibration: High-confidence picks are not earning their weight; calibration likely drifted. (`refresh_pick_quality`)
- route_clone_hl_copy_Auros_66M_to_mutation_or_inverse: clone_hl_copy_Auros_66M is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- route_clone_hl_copy_lb_None_to_mutation_or_inverse: clone_hl_copy_lb_None is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- route_stocks_rsi2_pullback_to_mutation_or_inverse: stocks_rsi2_pullback is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- review_symbol_level_peer_conflicts: Conflicting peer directions can indicate regime disagreement or stale assumptions. (`refresh_portfolio_monitor`)
- prefer_validated_leaders_for_next_cycle: Current leaders are clone_hl_copy_PensionFund_24M, luxalgo_confluence, quan_engine_swing. Bias new risk toward proven survivors.