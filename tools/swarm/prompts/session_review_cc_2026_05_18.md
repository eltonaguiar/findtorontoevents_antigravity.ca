# Session CC Review — 2026-05-18

## Context
Continuation of PATH_TO_PROVEN_EDGE. This session implemented the highest-ROI
action item from the session CA swarm review: replacing the noise-grade elite_score
ranker with a strategy-level rolling WR composite (M-108).

## Session deliverables

### 1. M-108 Strategy-Level Rolling WR Ranker (PRIMARY DELIVERABLE)
- File: `alpha_engine/strategy_wr_ranker.py` (committed 8f124b9546)
- Wired into: `alpha_engine/elite_scorer.py` (final sort step) + `alpha_engine/basket_generator.py`
- **Why:** Walk-forward harness proved elite_score has Cohen's d eff=0.005 (noise)
- **Composite rank formula:** 50% strategy_rolling_wr + 30% ml_composite + 20% confidence
- **Min n:** 10 closed picks in 60-day lookback before strategy WR is trusted
- **Fail-open:** falls back to elite_score if module unavailable
- **Live top strategies:** cot_positioning WR=78.4% (n=134), cftc_cot_commercial WR=74.8% (n=131)
- **14 tests passing**
- New field on picks: `strategy_rolling_wr`, `strategy_rolling_n`, `m108_rank_score`

### 2. H-001 COT Live Testing Allocation
- Quarter-Kelly sizing: 17% per CT=F pick at $10k account = $1,700 per trade
- Stop rule: if WR drops below 60% after n=50 live trades, pause
- Recorded in `reports/hypothesis_registry.json`

### 3. H-002 PEAD Research Prototype
- File: `tools/research/equity_pead_momentum.py` (committed 5ff7619305)
- Fetches Yahoo Finance earnings + EPS surprise → computes SUE → measures 30d drift
- Gracefully handles missing yfinance (returns NO_DATA status)
- OPT-IN sidecar; wiring blocked until deflated Sharpe > 0.6 on n >= 30 windows

## Review questions

1. Is the M-108 rank formula weights (50/30/20) well-calibrated, or should strategy_rolling_wr
   weight be higher (e.g., 70%) given that it's the only proven admissible signal?

2. DYDXUSDT shows 100% WR on n=30 in the strategy lookup (ml_enhanced_DYDXUSDT_15m_D_ensemble_stack).
   Prior session (AU) identified DYDXUSDT as a possible data artifact (source='?', avg PnL ~0.02%).
   Should we add a minimum avg_pnl_pct filter to strategy_wr_ranker.py to guard against data artifacts?

3. For H-001 COT: Kelly says 17% per pick at quarter-Kelly. Is this appropriate given
   that the COT signal is concentrated in one commodity (CT=F Cotton)? Should we cap
   the per-pick allocation to 10% regardless of Kelly to prevent over-concentration?

4. Is the PEAD prototype design sound? Yahoo Finance historical estimates are noisy —
   should we proceed with yfinance or invest in a better data source (IBKR fundamentals)?

5. Is the operator still blocking 3 strategies (futures_momentum, quan_engine_scalp,
   cta_replicator COMMODITY)? Is there any risk to the system while these remain active?

## Commits this session
- 8f124b9546: feat(M-108): strategy-level rolling WR ranker replaces elite_score as primary pick ranker
- 5ff7619305: feat(H-002): PEAD research prototype + H-001 Kelly allocation wired
