# Deep Dive Validation: Trading Stats & Performance Issues (2026-03-24)

## Executive Summary
**Overall WR: 42.1% (11,302 closed picks). Health: D (47/100).** Battleground survivors hit 60%+ subsets, but full system underperforms due to:
- **Score-PnL corr: -0.0077** (top scores worse).
- **Consensus anti-predictive** (more systems = lower WR).
- **Gates blocking winners** (MAX_PICKS_PER_SYMBOL=1, sector caps, 2% risk/trade).
- **Concentration risk** (FETUSDT 157% PnL; capped PnL -704%).
- **Universe gaps** (miss CREAM+65%, ONT+45%; forex sparse).

**Low-score winners: 54** (e.g. ETH score=26 +3.34%). High-WR copytraders (81%) blocked by gates/small N.

**Fixes**: Relax gates for copytraders/ML, A/B test portfolios, expand alts/forex.

## 1. Stats Validation vs Audits
| Audit | Claim | Current | Valid? |
|-------|-------|---------|--------|
| Mar6 Battleground | 64.1% WR | Subsets 60%+ | ✅ Plausible |
| Alpha Engine | 35.9% | 42% overall | ✅ Matches |
| Baby Bundles | 62.4% fwd | v2 mostly <40% | ❌ Poor |
| ML Assumed | 55-62% | N/A (heuristic fallback) | ❓ Unverified |

**True but diluted**: System avg 42% < random. Sharpe low (0.2 net).

## 2. Top Score Picks by Asset Class
**532 active, 11k closed (crypto 95%+)**:
- **Crypto**: `ml_enhanced_*` WR94% (N=16), `copy_hl_NMTD` 81% (16t). Corr negative.
- **Forex**: Sparse; audits: 94% expiry (tight bands/daily data).
- **Stocks**: LONG 8.3% WR (12t), SHORT 0% (3t).
Latest: RANGING regime 42.1%.

## 3. Low-Score High-Perf Examples (54 anomalies)
```
ETHUSDT  score=26  +3.34%  (super signal)
FETUSDT  score=23  +4.24%  (super signal)
HYPEUSDT score=0   +5.17%  (strong consensus)
ETHUSDT  score=0   +11.02% (moderate consensus)
SOLUSDT  score=0   +3.82%  (ct_consensus)
```
Scoring penalizes winners.

## 4. Top Performers Missing
**Binance Gainers (24h)**: 3/20 caught.
- Misses: CREAM +65%, ONT +45%, PNT +45% (universe gaps).
**Polymarket/Other**: Pending fetch.

## 5. Why High-WR Copytraders/ML Fail Live?
**Suspects (from config.py + data)**:
1. **Gates Block**: `MAX_PICKS_PER_SYMBOL=1`, `MAX_SAME_DIRECTION_CRYPTO=15`, sector caps → few signals.
2. **Risk Params Mismatch**: Crypto TP15%/SL8% → many TIME_EXPIRY (audits 94%).
3. **Concentration**: FET 157% PnL → outliers mask losses.
4. **Small N**: High WR (94%) N=16 → overfitting/unstable.
5. **Timing/Execution**: Copytraders lag (public data); gates filter conviction.
6. **Score Penalty**: Low corr → top copytrader signals scored low/blocked.

**Consensus Bug**: Raw count anti (4-7 sys 0% WR); needs family diversity (2 families 53% vs 32%).

## 6. Comparisons
- **Hedge Funds**: Renaissance (Sharpe 3-6), Two Sigma (1.5-3) >> our 0.2.
- **Crypto Preds**: CryptoSignals.org 82%, Learn2Trade 76% >> 42%.
- **Polymarket**: BTC up 70% odds → our SHORT BTC active (losing).

## 7. A/B Test Plan (Deploy Agents)
Use `ab_testing_agent/`:
1. **Portfolio A (Current Gates)**: Baseline.
2. **B (Relaxed Gates)**: MAX_SYMBOL=3, no sector cap for copytraders/ML.
3. **C (Exceptions)**: Bypass score/gates for copy_hl_* (81% WR), ml_enhanced (94%).
4. **D (ATR TP/SL)**: Dynamic vs fixed %.
Forward test 30d, 20 symbols each.

**Agent Deployment**:
- Test Engineer: A/B portfolios.
- Orchestrator: Polymarket fetch/compare.
- Code Simplifier: Fix gates/score.

## Next: Implement A/B via ab_testing_agent/main.py