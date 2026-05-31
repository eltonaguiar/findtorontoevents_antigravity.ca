# Per-Asset-Class Edge Hunt — Deep Dive Report
**Generated:** 2026-05-31 21:48 EST  
**Methodology:** MySQL direct query of ejaguiar1_stocks.trading_picks (42,665 rows) → per-strategy/direction analysis → Monte Carlo bootstrap (10K sims) → walk-forward (5-fold) → permutation test (5K perms)

---

## EXECUTIVE SUMMARY

35 positive-EV strategy/direction combos found across 6 asset classes. After Monte Carlo validation on the top 12 candidates:

| Class | Best Candidate | n | EV/trade | MC Verdict | Root Problem |
|-------|---------------|---|----------|------------|--------------|
| CRYPTO | mega_mutation | 283 | +2.54% | PROMISING | Permutation p=0.81 |
| CRYPTO | kimi_signal_tracking | 138 | +2.89% | PROMISING | n too small |
| FOREX | non_crypto_consensus SHORT | 1322 | +0.065% | PROMISING | 93% TIME_EXIT |
| FOREX | myfxbook_retail_contrarian SHORT | 1689 | +0.050% | PROMISING | 87% TIME_EXIT |
| FOREX | ig_contrarian_sentiment SHORT | 2470 | +0.057% | PROMISING | 89% TIME_EXIT |
| COMMODITY | cta_golden_cross_200 LONG | 231 | +0.475% | WEAK_EDGE | 88% TIME_EXIT |
| EQUITY | stocks_rsi2_pullback LONG | 1166 | +0.031% | NO_EDGE | CI crosses 0 |
| ETF | — | 29 | — | INSUFFICIENT | Not enough data |
| BOND | — | 89 | — | INSUFFICIENT | Not enough data |

---

## ROOT CAUSE: TIME_EXIT SATURATION

85-97% of ALL trades exit at TIME_EXIT with exactly 0.00% PnL. TP/SL thresholds are too wide.

| Strategy | n | TIME_EXIT% | TP_HIT% | SL+LOST% |
|----------|---|-----------|---------|----------|
| prediction_market_consensus SHORT | 1519 | 97% | 2.8% | 0.1% |
| non_crypto_consensus SHORT | 1322 | 93% | 3.8% | 3.3% |
| ig_contrarian_sentiment SHORT | 2470 | 89% | 4.8% | 5.9% |
| cta_golden_cross_200 LONG | 231 | 88% | 8.7% | 1.3% |
| stocks_rsi2_pullback LONG | 1166 | 95% | 2.4% | 2.6% |

---

## ACTIONABLE RECOMMENDATIONS

### Kill (Confirmed Losers)
- mercury2 (PF=0.34), ml_crypto_predictor losers, cta_replicator forex (PF=0.12)

### Fix
- Tighten TIME_EXIT thresholds across all strategies
- Pool forex contrarian SHORTs for aggregate testing (n=5,481)
- Continue mega_mutation forward test to n≥500

### Monitor
- mega_mutation: only all-decisive strategy, EV=+2.54%
- kimi_signal_tracking: EV=+2.89%, need n≥300
- commodity_term_structure: Claude MC found PF=1.06, p=0.0098

---

## CROSS-AI CONSENSUS

All agents agree: no statistically valid edge exists today. Path forward:
1. BUILD top-3 cross-AI-consensus strategies fresh
2. Paper-pilot 30+ days
3. Apply statistical framework from day 1
4. Gate: DSR>0.95, PBO<0.05, WF 4/5+, perm p<0.05
