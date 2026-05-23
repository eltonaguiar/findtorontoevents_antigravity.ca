# Audit Dashboard — Scoring Reference

## Strategy Health Score (0-100, baseline 50)

| Component | Weight | Good | Bad |
|-----------|--------|------|-----|
| FWD vs BT Decay | 30% | Decay>-10%: +15pts | Decay<-30%: -15pts |
| Recent vs Lifetime WR | 30% | Ratio≥0.9: +15pts | Ratio<0.7: -15pts |
| Sample Quality | 20% | ≥20 trades: +10pts | <5 trades: -10pts |
| Trade Volume | 20% | ≥20 closed: +10pts | <10: 0pts |

Status: ≥65 HEALTHY | 40-64 WATCH | <40 DEGRADED

## Pick Quality Grade (0-100)
Formula: performanceBase × healthMultiplier × csrMultiplier
- performanceBase = (fwd_wr × 0.6) + (min(PF, 3)/3 × 100 × 0.4)
- healthMultiplier: HEALTHY=1.0, WATCH=0.75, DEGRADED=0.4
- csrMultiplier: Common Sense Ratio (10% weight)

Grades: A(≥80), B(70-79), C(55-69), D(40-54), F(<40)

## System Trust Tiers (≥20 trades)
| WR + PF | Tier | Weight |
|---------|------|--------|
| WR≥65% + PF≥2.0 | PROVEN | 0.95 |
| WR 55-64% + PF≥1.5 | RELIABLE | 0.85 |
| WR 50-54% + PF≥1.0 | RELIABLE | 0.75 |
| WR 45-49% | WATCH | 0.60 |
| WR 35-44% | SANDBOX | 0.40 |
| WR <35% | SANDBOX | 0.25 |

## Confidence Extraction Priority
1. Numeric fields: confidence, ml_score, score, probability (0-1 or 0-100)
2. Text mapping: "very high"→0.90, "high"→0.80, "medium"→0.60, "low"→0.40
3. Fallback: sentiment_score, win_rate/100, min(0.90, 0.40+sharpe×0.15)
4. Default: 0.0

## Advanced Metrics
- CSR (Common Sense Ratio): (WR%×AvgWin) / ((1-WR%)×AvgLoss)
- Omega Ratio: sum(gains) / sum(losses) for ≥5 trades
- Tail Ratio: 95th pct wins / abs(5th pct losses)
- Calmar Ratio: annualized return / max drawdown

## Conflict Detection
- Groups active picks by symbol + direction
- Trust-weighted vote resolution for LONG vs SHORT conflicts
- Same timeframe = "genuine conflict"; different TF = "may coexist"

## Auto-Expiry & Filtering
- Picks >72h auto-expired (excluded from metrics if 0% PnL)
- Garbage price detection (symbol-aware ceilings: DOGE max $10, BTC max $500K)
- PnL sanity cap: ±500%

## Key Files
- audit_trail/dashboard_generator.py
- audit_dashboard/index.html
- hub/data/systems_manifest.json
