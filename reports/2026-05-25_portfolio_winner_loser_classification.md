# Portfolio Winner/Loser Classification — 2026-05-25

Source: `audit_dashboard/data/claudes_test_state.json`  
Generated: 2026-05-25T04:50:49.749186+00:00  
Total portfolios: **36**  

## Bucket counts

- **REPEAT_WINNER**: 3
- **REPEAT_LOSER**: 4
- **MIXED**: 29
- **INSUFFICIENT_HISTORY**: 0

## Repeat Winners (scale-up candidates) — n=3

| Portfolio | Methodology | Equity vs init % | Streak (+ / -) | MDD30d | WR% | Closed | Action |
|---|---|---:|---:|---:|---:|---:|---|
| `anti_meme` | anti_meme | -2.96% | 5 / 0 | 4.84% | 17.9 | 28 | scale_up_50pct; clone_to_new_universe |
| `high_conviction` | conviction | -0.98% | 3 / 0 | 4.84% | 31.2 | 32 | scale_up_50pct; clone_to_new_universe |
| `rr_kings` | rr | -3.18% | 3 / 0 | 6.15% | 31.2 | 16 | scale_up_50pct; clone_to_new_universe |

## Repeat Losers (invert-or-mutate per docs/MUTATION_THREE_AXIS_PROTOCOL.md) — n=4

| Portfolio | Methodology | Equity vs init % | Streak (+ / -) | MDD30d | WR% | Closed | Action |
|---|---|---:|---:|---:|---:|---:|---|
| `small_position` | score_small_position | -0.48% | 0 / 7 | 0.51% | 23.5 | 17 | invert_direction; tighten_gates; substitute_regime |
| `regime_aligned` | regime | -3.03% | 0 / 3 | 4.31% | 33.3 | 42 | invert_direction; tighten_gates; substitute_regime |
| `prop_conservative` | prop_conservative | -0.76% | 0 / 3 | 1.15% | 28.1 | 32 | invert_direction; tighten_gates; substitute_regime |
| `beaten_majors` | beaten_majors | -0.06% | 0 / 3 | 2.64% | 60.0 | 5 | invert_direction; tighten_gates; substitute_regime |

## Mixed (hold) — n=29

| Portfolio | Methodology | Equity vs init % | Streak (+ / -) | MDD30d | WR% | Closed | Action |
|---|---|---:|---:|---:|---:|---:|---|
| `all_asset_tournament` | noncrypto_diversified | +2.46% | 1 / 0 | 0.52% | 11.1 | 9 | — |
| `fear_greed_contrarian` | fear_greed | +2.11% | 0 / 2 | 3.03% | 100.0 | 5 | — |
| `stocks_short_term` | noncrypto_reversal | +2.07% | 2 / 0 | 1.60% | 0.0 | 4 | — |
| `stocks_best` | noncrypto_best | +1.89% | 0 / 1 | 1.37% | 44.4 | 9 | — |
| `multi_asset_diversified` | noncrypto_diversified | +1.72% | 1 / 0 | 1.60% | 0.0 | 11 | — |
| `htf_weekly_momentum` | htf_momentum | +1.46% | 0 / 2 | 2.70% | 46.1 | 13 | — |
| `high_consensus` | consensus_3plus | +1.42% | 0 / 1 | 0.89% | 34.4 | 32 | — |
| `claude_best` | best | +1.31% | 0 / 2 | 2.41% | 48.0 | 25 | — |
| `sector_rotation` | sector | +0.98% | 1 / 0 | 1.95% | 40.9 | 22 | — |
| `prop_swing` | prop_swing | +0.69% | 0 / 2 | 1.29% | 55.6 | 9 | — |
| `golden_only` | golden_insight_only | +0.48% | 0 / 1 | 0.40% | 42.9 | 7 | — |
| `hoffman_elite` | hoffman | +0.22% | 0 / 1 | 1.84% | 47.4 | 19 | — |
| `momentum_riders` | momentum | +0.07% | 1 / 0 | 2.04% | 37.1 | 35 | — |
| `futures_index` | noncrypto_best | +0.00% | 0 / 0 | 0.00% | -- | 0 | — |
| `etf_rotation` | noncrypto_best | -0.02% | 0 / 0 | 0.02% | -- | 0 | — |
| `forex_carry` | noncrypto_best | -0.03% | 0 / 0 | 0.33% | 22.2 | 9 | — |
| `regime_filtered` | regime_aligned_only | -0.17% | 0 / 1 | 1.09% | 40.9 | 22 | — |
| `sentiment_divergence` | sentiment_divergence_only | -0.21% | 0 / 0 | 0.21% | 0.0 | 3 | — |
| `relative_strength_recovery` | rel_strength | -0.35% | 0 / 1 | 3.34% | 50.0 | 4 | — |
| `basis_carry_only` | carry_arb_only | -0.39% | 0 / 1 | 1.87% | 20.0 | 10 | — |
| `rsi_capitulation` | rsi_capitulation | -0.44% | 0 / 1 | 5.30% | 40.0 | 15 | — |
| `consensus_plays` | consensus | -0.85% | 0 / 1 | 3.59% | 25.9 | 27 | — |
| `prop_aggressive` | prop_aggressive | -2.21% | 2 / 0 | 2.64% | 22.2 | 36 | — |
| `deep_drawdown_dca` | drawdown_dca | -2.24% | 0 / 1 | 4.74% | 28.6 | 7 | — |
| `proven_only` | proven | -2.29% | 0 / 2 | 3.69% | 26.5 | 34 | — |
| `fresh_signals` | fresh | -2.67% | 2 / 0 | 4.49% | 32.5 | 40 | — |
| `contrarian` | contrarian | -3.00% | 0 / 1 | 4.16% | 30.0 | 30 | — |
| `score_leaders` | score | -3.04% | 0 / 1 | 4.75% | 30.3 | 33 | — |
| `htf_trend_follow` | htf_trend | -3.70% | 0 / 2 | 3.79% | 20.0 | 15 | — |

## Insufficient History — n=0

_None._
