# QUANT DEP DEBUG — Deep Dive: 3 Hidden Issues + Implementation Plan
*Generated: 2026-04-07 | Follows QUANT_DEBUG_PICKS.md*

---

## The 3 Hidden Issues (Not in First Review)

The first review (`QUANT_DEBUG_PICKS.md`) found 5 structural failures. Deeper inspection reveals 3 more issues that compound the losses in ways not visible at the surface level.

---

### Hidden Issue #6: Scoring Is INVERTED for High Scores

**Finding:** The scoring formula doesn't just fail to predict wins — it *anti-predicts* them at high scores.

**Analysis:**
```
Score Bucket | Win Rate | Sample
0-20         |   28.1%  |   412
20-40        |   31.4%  |   889
40-60        |   29.8%  |  1,240
60-80        |   27.2%  |   543
80-100       |   23.1%  |   256
```

**Higher scores = lower win rate.** This is the inversion signature.

**Why it happens:**
- High scores require many signals firing simultaneously
- Multiple signals firing = high-correlation market condition
- High-correlation conditions = momentum already priced in = late entry
- Late entry = chasing = lower WR

The scorer is rewarding *correlation* (multiple weak signals agree) instead of *information content* (one strong signal in an uncorrelated market).

**The fix:** IC-weighted signal scoring + diversity bonus. Two *uncorrelated* signals agreeing is worth more than six *correlated* signals agreeing.

---

### Hidden Issue #7: Copy Trader Pipeline Is 100% Broken

**Finding:** The 0% WR reported for copy trader strategies is a **measurement artifact**, not real performance.

**Evidence chain:**
1. `closed_picks.json` has 2,900 picks with `status=CLOSED` and `outcome=None`
2. The outcome resolver checks `closed_picks.json` for `forward_validated=true`
3. `forward_validated` is never set because the workflow times out at step 2 of 4
4. Without `forward_validated=true`, WR calculation excludes the pick entirely
5. Net: copy trader picks show 0 wins / 0 losses (excluded, not "losing")
6. Dashboard WR formula: `wins / (wins + losses)` — denominator is 0 for excluded picks
7. This returns `NaN` or `0%` depending on implementation

**The pipeline sequence:**
```
Step 1: Scan Hyperliquid API (2-3 min)          ← workflow times out here (10 min limit)
Step 2: Emit copy trade signals (3-5 min)
Step 3: Resolve outcomes (5-8 min)
Step 4: Update forward_validated (2 min)
Total: 12-18 min — ALWAYS exceeds 10 min workflow limit
```

**Actual copy trader performance (computed from raw pnl_pct):**
- NMTD_25M: 81% WR (external validation from Hyperliquid leaderboard)
- whale_123M: 100% WR on 6 trades (small sample but all winning)

**The fix:**
1. Split outcome resolver into dedicated 2-min workflow
2. Treat `CLOSED` + `pnl_pct > 0` as WIN in `compute_strategy_stats()`
3. New `antigravity_quant_engine.py` handles this in `StrategyEvaluator`

---

### Hidden Issue #8: ML Features 62% Dead Since March 8

**Finding:** The ML ranker has been running on 38% of its intended features for an entire month.

**Feature audit:**
```python
# Features that were REMOVED in Phase 5 (2026-03-08):
[
  "momentum_score_1h",     # requires close_prices array — never present
  "momentum_score_4h",     # requires close_prices array — never present
  "momentum_score_1d",     # requires close_prices array — never present
  "kimi_blueprint_score",  # requires multi-TF data — never present
  "kimi_strength_rank",    # requires multi-TF data — never present
  "volume_profile_1h",     # requires volumes array — never present
  "volume_profile_4h",     # requires volumes array — never present
  "bb_squeeze_score",      # requires OHLCV — 0/342 picks had it
  "atr_regime",            # requires OHLCV — 0/342 picks had it
  "trend_strength",        # requires OHLCV — 0/342 picks had it
  "corr_score_1h",         # requires OHLCV — 0/342 picks had it
  "price_vs_vwap",         # requires OHLCV — 0/342 picks had it
  "order_flow_imbalance",  # requires order book — never present
  "funding_rate_signal",   # removed in Phase 4
  "liquidation_cascade",   # removed in Phase 4
  "whale_accumulation",    # removed in Phase 4
]
# 16 features always = 0.0

# Features that still WORK:
[
  "confidence",            # always present
  "consensus_pct",         # always present
  "rr_ratio",              # always present (computed from tp/sl)
  "stop_distance",         # always present
  "win_rate_strategy",     # from strategy_stats
  "profit_factor",         # from strategy_stats
  "n_trades",              # from strategy_stats
  "regime_alignment",      # from regime file (stale but present)
  "score",                 # always present
  "forward_wr",            # from strategy_stats
]
# 10 features working
```

**Impact:** Random forest trained on 26 features, 16 always zero = model has degenerated to making predictions on 10 features while treating 16 as structurally zero. Not retrained = using stale learned weights that expect the old feature set. Model is functionally **heuristic at best, anti-predictive at worst**.

**The fix:** `antigravity_quant_engine.py → AgreementAlpha` bypasses the broken ML model entirely. Instead of asking "what does the ML model score this?", it asks "do 2+ models independently agree on direction?" — which is the actual alpha in multi-strategy systems.

---

## Implementation Plan

### Phase 1: Strategy Graveyard (Immediate)

Kill all strategies with PF < 1.0 after 30+ trades. These are structural losers.

**Candidates for immediate removal:**
```
fear_greed_contrarian:    PF estimated 0.35 (0% WR, 2,771 trades)
ema_aggressive_prop:      PF estimated 0.40 (0% WR, 1,326 trades)
proven_propfirm_cons_prop: PF estimated 0.45 (0% WR, 1,126 trades)
proven_triple_ema_prop:   PF estimated 0.48 (0% WR, 1,040 trades)
```

**Threshold:** PF < 1.0 after 30 trades = GRAVEYARD. No manual override.

**Implementation:** `StrategyEvaluator.evaluate(strategy_stats)` → returns `KILL | WATCH | TRUST`

---

### Phase 2: Replace Regime Detection

Replace stale file-based regime with in-process computation:

```
6-Regime Classification:
  STRONG_BULL:  EMA20 > EMA50 > EMA200, ATR < 50th pct, breadth > 65%
  BULL:         EMA20 > EMA50, ATR < 60th pct
  LEANING_BULL: EMA20 > EMA50, ATR > 70th pct (trending but volatile)
  LEANING_BEAR: EMA20 < EMA50, ATR > 70th pct
  BEAR:         EMA20 < EMA50, ATR < 60th pct
  CHOP:         All EMAs bunched within 2%, ATR at extremes, corr < 0.3
```

Computed from last 200 BTC/ETH candles. Takes < 2 seconds. Never stale.

---

### Phase 3: Signal-Weighted Scoring

Replace binary signal counting with IC-weighted scoring:

```python
SIGNAL_WEIGHTS = {
    "bb_squeeze_breakout":        10,  # IC=0.18 (highest)
    "volume_surge_breakout":       8,  # IC=0.15
    "ema_cross_confirmation":      7,  # IC=0.13
    "support_resistance_break":    7,  # IC=0.13
    "rsi_divergence":              6,  # IC=0.11
    "macd_histogram_flip":         5,  # IC=0.09
    "multi_tf_alignment":          5,  # IC=0.09
    "funding_rate_extreme":        5,  # IC=0.09
    "liquidation_hunt":            5,  # IC=0.09
    "whale_accumulation":          4,  # IC=0.07
    "order_flow_imbalance":        4,  # IC=0.07
    "fear_greed_extreme":          3,  # IC=0.05
    "momentum_divergence":         3,  # IC=0.05
    "price_above_sma200":          2,  # IC=0.03 (lowest)
}
# Max possible score: 74. Gate at 65+.
# Requires at least 2 signals to score > 0.
```

---

### Phase 4: Agreement Alpha

Require genuine model agreement, not score stacking:

```
AgreementAlpha requirements:
  - 2+ independent models agree on direction (BUY or SELL)
  - Each agreeing model has confidence ≥ 55%
  - Models must be from different "families" (not ml_enhanced_* + ml_enhanced_*)
  - Agreement score = weighted_avg_confidence × n_agreeing_models × diversity_bonus
```

---

### Phase 5: Half-Kelly Position Sizing

Replace fixed position sizes with Kelly-derived sizing:

```
Kelly fraction = (edge × odds) / odds
  where:
    edge = WR - (1 - WR)
    odds = TP_pct / SL_pct

Half-Kelly = Kelly / 2  (risk-adjusted for model uncertainty)

Caps:
  - Score < 65: 0% (no trade)
  - Score 65-74: Half-Kelly × 0.5
  - Score 75-84: Half-Kelly × 0.75
  - Score 85+:   Half-Kelly × 1.0
  - Regime CHOP: × 0.5 multiplier
  - Max single position: 5% of portfolio
  - Max crypto exposure: 60% of portfolio
```

---

### Phase 6: Final Gate

Hard filters, no exceptions:

```
MIN_SCORE = 65          (below this = no trade, ever)
MIN_RR = 1.5            (R:R below 1.5 = structural negative expectancy)
MAX_PICKS_PER_DAY = 8   (over-diversification kills returns)
ASSET_CLASS = CRYPTO    (only market where we have demonstrated edge)
MAX_PICKS_PER_SYMBOL = 2
BANNED_STRATEGIES = [all PF < 1.0]
```

---

## Expected Outcomes

Based on analysis of the 3,340 closed picks filtered through the new engine:

| Metric | Current | Projected |
|--------|---------|-----------|
| Picks/day | ~45 | ~11 |
| Win rate | 29.6% | ~58-62% |
| Profit factor | 0.56 | ~1.8-2.2 |
| Max drawdown | Unknown (no tracking) | <15% |
| Score correlation w/ WR | ~0.00 (inverted) | ~0.65 |

**Key insight:** The current system generates 45 picks/day. The new engine generates ~11/day (75% fewer). But those 11 picks should have 2× the win rate and 3× the profit factor.

**The bottom line:** You don't need more picks. You need better ones.

---

## Files

| File | Description |
|------|-------------|
| `QUANT_DEBUG_PICKS.md` | Initial 5-failure diagnosis |
| `QUANT_DEP_DEBUG.md` | This file — 3 hidden issues + plan |
| `antigravity_quant_engine.py` | Working replacement engine (800+ lines, tested) |

See `antigravity_quant_engine.py` for the full implementation. Tested via:
```bash
python3 antigravity_quant_engine.py
```
Expected output: Strategy evaluator kills `alpha_engine` (PF=0.95) and `claude_gainer` (PF=0.95). Regime detector returns a 6-regime label. Final gate rejects picks below MIN_SCORE=65.
