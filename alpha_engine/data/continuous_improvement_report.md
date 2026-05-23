# Continuous Improvement Report

Generated: 2026-05-23T09:06:22.199400+00:00

## Topline
- Open positions: 153
- Price coverage: 98.04%
- Open average PnL: 22.3113%
- Directional correctness: 52.0%
- Regime: BEARISH

## Alerts
- [CRITICAL] PORTFOLIO_DRAWDOWN_BREACH: Paper portfolio derivatives hit 10.15% drawdown
- [HIGH] PEER_STALE: alpha_engine data is stale (83332.3m old)
- [HIGH] PEER_STALE: copy_trader_intel data is stale (751.2m old)
- [HIGH] PEER_STALE: paper_trading data is stale (111625.4m old)
- [HIGH] REGIME_SHIFT: Regime changed CHOPPY -> BEARISH while open PnL fell from 68.26% to 22.31%
- [HIGH] STRATEGY_DECAY: myfxbook_retail_contrarian is a rehabilitation candidate (WR 17.39%, PF 0.194, Sharpe -13.225)
- [MEDIUM] PEER_DIRECTION_CONFLICT: Peer systems disagree on BTCUSDT ({'LONG': 8, 'SHORT': 3})

## Recommendations
- tighten_risk_and_reduce_gross_exposure: Choppy regime or drawdown breach warrants smaller sizing and tighter review cadence.
- refresh_local_monitors: Data freshness or pricing gaps need a local refresh cycle before acting on signals. (`refresh_kpis`)
- route_myfxbook_retail_contrarian_to_mutation_or_inverse: myfxbook_retail_contrarian is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- route_forex_rsi2_mean_reversion_to_mutation_or_inverse: forex_rsi2_mean_reversion is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`alpha_mutation_scan`)
- route_clone_hl_copy_Auros_66M_to_mutation_or_inverse: clone_hl_copy_Auros_66M is under threshold. Follow the repo policy: mutate or invert instead of disabling. (`copytrader_mutation_extract`)
- review_symbol_level_peer_conflicts: Conflicting peer directions can indicate regime disagreement or stale assumptions. (`refresh_portfolio_monitor`)
- prefer_validated_leaders_for_next_cycle: Current leaders are cg_whale_divergence, clone_hl_copy_PensionFund_24M, cftc_cot_commercial_signal. Bias new risk toward proven survivors.