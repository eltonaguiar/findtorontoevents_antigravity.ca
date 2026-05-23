# Cross-System Aggregator — Scoring Reference

## Trust Tiers & Vote Weights
| Tier | Criteria | Vote Weight | Score Mult | Alloc Max |
|------|----------|-------------|------------|-----------|
| PROVEN | WR>65% AND 30+ trades | 2.0x | 1.5x | 50% |
| RELIABLE | WR 55-65% AND 10+ trades | 1.5x | 1.2x | 30% |
| WATCH | <10 trades | 1.0x | 1.0x | — |
| UNTRUSTED | WR<50% AND 10-29 trades | 0.3x | 0.5x | 5% |
| BANNED | WR<50% AND 30+ trades | 0.0x | 0.0x | 0% |

Phase 3 minimum-trade gate: systems with <10 trades get vote_weight × (closed_trades/10)

## Consensus Detection
- Threshold: ≥2 weighted votes
- Confirmer-only systems (KIMI) only count after 2+ base systems agree
- Conflict resolution via trust-weighted tiebreaker

## Per-System Scoring
score = adj_conf × (0.5 + 0.5×WR) × (0.5 + 2.0×Sharpe_wt) × trust_mult
Best system selected by highest composite score

## Confidence Calculation (WR-Anchored, fixed 2026-03-11)
1. blended_conf = 0.60×raw_conf + 0.40×system_WR (or 0.70× if WR unknown)
2. consensus_boost = 0.03 × min(agree_count - 1, 3) → max +9%
3. regime_mult = 0.90-1.10 (strategy-type aware)
4. Hard cap: 0.95

## Consensus Tiers
- SUPER: ≥6 weighted votes
- STRONG: 3-5.99 weighted votes
- MODERATE: 2-2.99 weighted votes

## Beta Confluence Score (5 Pillars, 0-100)
| Pillar | Max | Inputs |
|--------|-----|--------|
| Technical | 25 | RSI, volume ratio, model confidence, system agreement |
| On-chain | 20 | F&G, exchange flows, MVRV, order book |
| Sentiment | 15 | F&G regime match, LunarCrush Galaxy Score |
| Risk/Reward | 20 | R:R ratio, TP room, SL distance vs ATR |
| Structure | 20 | Regime alignment, BTC correlation, volatility, funding rate |
Qualified: ≥70

## Pick Classification
- ELITE: ≥3 systems, 2+ PROVEN, conf ≥0.60 → #dna-master-picks
- PROVEN: ≥2 systems, 1+ WR≥55% → #fresh-picks
- EXPERIMENTAL: everything else → #sandbox

## FreshPicks Gates (8 gates, currently in TESTING mode)
G1: Dedup (30min cooldown) | G2: Confidence ≥0.30 | G3: Strategy WR ≥0.01 | G4: R:R ≥1.0 | G5: Dynamic ATR TP/SL | G6: Kelly sizing (max 2%) | G7: Rate cap 999/hr | G8: Regime penalty

## Key Files
- cross_aggregation/aggregator.py
- cross_aggregation/system_trust_registry.py
- cross_aggregation/beta_confluence_scorer.py
- cross_aggregation/freshpicks_gate.py
- cross_aggregation/pick_classifier.py
