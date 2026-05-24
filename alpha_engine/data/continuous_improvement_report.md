# Continuous Improvement Report

Generated: 2026-05-24T08:39:33.695958+00:00

## Topline
- Open positions: 88
- Price coverage: 98.86%
- Open average PnL: 41.773%
- Directional correctness: 58.62%
- Regime: BULLISH

## Alerts
- [CRITICAL] PORTFOLIO_DRAWDOWN_BREACH: Paper portfolio derivatives hit 10.15% drawdown
- [HIGH] CONFIDENCE_INVERSION: High-confidence picks are underperforming low-confidence picks (50.0% vs 81.8%)
- [HIGH] PEER_STALE: alpha_engine data is stale (84745.5m old)
- [HIGH] PEER_STALE: copy_trader_intel data is stale (139.7m old)
- [HIGH] PEER_STALE: paper_trading data is stale (113038.6m old)
- [HIGH] STRATEGY_DECAY: stocks_rsi2_pullback is a rehabilitation candidate (WR 38.71%, PF 1.103, Sharpe 0.734)
- [MEDIUM] PEER_DIRECTION_CONFLICT: Peer systems disagree on XRPUSDT ({'LONG': 2, 'SHORT': 4})
- [MEDIUM] REGIME_SHIFT: Regime changed CHOPPY -> BULLISH

## Recommendations
- tighten_risk_and_reduce_gross_exposure: Choppy regime or drawdown breach warrants smaller sizing and tighter review cadence.
- refresh_local_monitors: Data freshness or pricing gaps need a local refresh cycle before acting on signals. (`refresh_kpis`)
- audit_confidence_calibration: High-confidence picks are not earning their weight; calibration likely drifted. (`refresh_pick_quality`)
- route_stocks_rsi2_pullback_to_mutation_or_inverse: stocks_rsi2_pullback is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- route_forex_rsi2_mean_reversion_to_mutation_or_inverse: forex_rsi2_mean_reversion is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- route_regime_mild_bear_to_mutation_or_inverse: regime_mild_bear is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- review_symbol_level_peer_conflicts: Conflicting peer directions can indicate regime disagreement or stale assumptions. (`refresh_portfolio_monitor`)
- prefer_validated_leaders_for_next_cycle: Current leaders are luxalgo_confluence, quan_engine_swing. Bias new risk toward proven survivors.