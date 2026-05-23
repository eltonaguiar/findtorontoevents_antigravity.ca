# KIMI Rise of the Claw — Scoring Reference

## Signal Generation
- 81 algorithms, each with strategy-specific confidence formula
- Raw confidence range: 0.56-0.85
- Drought relaxation: +0.01 per drought level to confidence floor

## Pre-Entry Gates
1. Price sanity check (min/max bounds per category)
2. Gap chase rejection (crypto +8%, meme +7%, stock +5%, forex +2%)
3. Global symbol concentration cap (max 2 algos per symbol)
4. Earnings blacklist (within 3 days)
5. Weekly trend filter (blocks TREND strategies in bear weekly)
6. Market hours gate (stocks 9:30-16:00 ET only)

## TP/SL (ATR-Based)
ATR multipliers by category:
- Crypto: TP=1.5×ATR, SL=1.0×ATR
- Meme: TP=2.0×ATR, SL=1.2×ATR
- Forex: TP=1.5×ATR, SL=1.0×ATR
- Stock: TP=1.5×ATR, SL=1.0×ATR

Static fallback: crypto(-8%/+15%/5d), meme(-12%/+25%/3d), forex(-2%/+4%/7d), stock(-5%/+10%/7d)

Signal probability: P(TP) = SL_dist / (TP_dist + SL_dist) × 100 [5%-95%]

## Allocation Sizing (Multi-Layer Multipliers)
base_alloc × vol_scale × kelly_mult × regime_mult × sector_rs_mult × macro_alloc_mult × vix_stock_mult × breadth_mult × vix_term_mult × fng_crypto_mult × cnn_stock_mult

## Confluence
- 1 algo (high conf ≥0.65): score=50, no size boost
- 2 algos: score=65, +25% size
- 3 algos: score=80, +50% size
- 4+ algos: score=100, +50% size
- Double ignite: same symbol had convergence in BOTH current AND previous scan

## ML Signal Ranker

### Heuristic mode (< 50 closed picks)
Score = 0.3×conf + 0.4×WR + 0.2×Sharpe + tier_bonus(0.1)
Range: [0.0, 1.0]

### ML mode (≥ 50 closed picks)
RandomForest: 200 trees, max_depth=8, balanced classes
Features: algo_id_enc, category_enc, symbol_enc, tier_enc, algo_wr, algo_sharpe, algo_drought, algo_closed, algo_kelly
TimeSeriesSplit 5-fold cross-validation

## Tournament Elimination
- Active: score ≥ 40
- Danger Zone: score < 40 for 3+ days
- Probation: confirmed downtrend
- Eliminated: score < 30 for 2+ days → replaced by challenger
- 20 reserve algorithms standing by

## Key Thresholds
- MIN_SAMPLES_FOR_ML: 50 closed picks
- HIGH_CONFIDENCE_BYPASS: 0.65
- MAX_PICKS_PER_ALGO: 3
- STARTING_CAPITAL: $10,000 per algo
- MAX_SAME_SYMBOL_GLOBAL: 2
- SL_BUFFER: 0.5%
- DANGER_ZONE_THRESHOLD: 40
- PROBATION_THRESHOLD: 30

## Key Files
- KIMI_RISEOFTHECLAW/live_scanner.py
- KIMI_RISEOFTHECLAW/ml_signal_ranker.py
- KIMI_RISEOFTHECLAW/elimination_engine.py
- KIMI_RISEOFTHECLAW/signal_tracker.py
