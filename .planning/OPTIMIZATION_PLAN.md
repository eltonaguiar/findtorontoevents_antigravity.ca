# Trading Systems Optimization Plan
**Generated:** 2026-03-02 | **Based on:** Quant Lab analysis + full system inventory

---

## Executive Summary

After running all quant lab analyses and inventorying every live system, here are the critical findings:

| Metric | Value | Verdict |
|--------|-------|---------|
| **Ruin Probability** | 100% at $1,000 | DANGER |
| **Critical Risk Alerts** | 15 of 20 strategies | DANGER |
| **Diversification Score** | 0.367 (of 1.0) | POOR — strategies too correlated |
| **Compliant Allocation** | $154.88 of $1,000 | Only 5 strategies pass compliance |
| **Walk-Forward Profitable** | 7 of 35 strategies | 80% are unreliable |
| **Consensus Picks** | 0 (empty output) | Cross-aggregator threshold too high |
| **Hub Systems** | 15 listed, 17+ exist | Missing System F + ensemble + ML predictor |
| **Battleground Strategies** | 171 total, 124 passed | 30+ baby strats not tracked in any bundle |

---

## Phase 1: Hub Page — Add All Missing Systems

### Problem
Hub has 15 systems in its `SYSTEMS` array but at least 2 active signal-producing systems are missing:
- **ML Battleground Ensemble** — `ml_battleground/ensemble_data/active_picks.json` (aggregates A-E)
- **ML Crypto Predictor** — `ml_crypto_predictor/enhanced_models/live_picks/active_picks.json`

System F (Claws of Doom) IS already in the array (id: `claws_of_doom`) but uses an external `COD_BASE` URL from the CLAWSOFDOOM repo.

### Actions
1. **Add ML Battleground Ensemble** to SYSTEMS array in [hub/index.html:291](hub/index.html#L291):
   ```js
   {
     id: 'ml_bg_ensemble', name: 'ML: Battleground Ensemble', badge: 'new', scanInterval: 30,
     methodology: 'Meta-system aggregating Battleground A-E signals. Majority vote + confidence weighting.',
     activePath: BASE+'ml_battleground/ensemble_data/active_picks.json',
     closedPath: BASE+'ml_battleground/ensemble_data/closed_picks.json',
     dashboard: PAGES+'battleground/',
     extra: []
   }
   ```

2. **Add ML Crypto Predictor** to SYSTEMS array:
   ```js
   {
     id: 'ml_crypto_predictor', name: 'ML: Crypto Predictor', badge: 'new', scanInterval: 60,
     methodology: 'Enhanced ML models for crypto price prediction.',
     activePath: BASE+'ml_crypto_predictor/enhanced_models/live_picks/active_picks.json',
     closedPath: null,
     dashboard: PAGES+'predictions/dashboard/',
     extra: []
   }
   ```

3. **Add Predictions system** if it produces active_picks:
   ```js
   {
     id: 'predictions', name: 'Predictions Engine', badge: 'new', scanInterval: 60,
     methodology: 'Multi-analyst prediction aggregation with confidence scoring.',
     activePath: BASE+'predictions/data/active_picks.json',
     closedPath: BASE+'predictions/data/closed_picks.json',
     dashboard: PAGES+'predictions/dashboard/',
     extra: []
   }
   ```

4. **Mark dormant systems clearly** — Systems with 0 recent picks should auto-detect dormancy via JS (already partially done with `dormant: true` flag on A, C).

### Files to modify
- `hub/index.html` — SYSTEMS array (line 291-400)

---

## Phase 2: Battleground — Flag Untracked Strategies

### Problem
The battleground already has an "Unregistered Strategies" panel (panel 8), but it lacks:
- **AWAITING_BACKTEST** status — strategies that exist but haven't been through the sweep runner
- **BUNDLE_CANDIDATE** flag — strategies that passed backtesting but aren't in any production bundle
- **NOT_ELIMINATED** flag — strategies that haven't been killed by the elimination engine

Currently tracked statuses: `backtest_passed`, `validating`, `insufficient_data`, `backtest_failed`, `backtest_error`, `paper_trading`, `graduated`, `live`

### Actions
1. **Add new statuses** to `battleground/data/baby_strats_dashboard.json` status_definitions:
   ```json
   "awaiting_backtest": "Strategy code exists but has not been run through the real-data sweep runner yet.",
   "bundle_candidate": "Passed backtest gates and eligible for promotion into a production bundle/system.",
   "not_eliminated": "Has not been eliminated by any system's elimination engine — still viable."
   ```

2. **Add status chips** to STATUS_OPTIONS in [battleground/app.js:126](battleground/app.js#L126):
   ```js
   { id: "awaiting_backtest", label: "Awaiting Backtest" },
   { id: "bundle_candidate", label: "Bundle Candidate" },
   ```

3. **Add CSS classes** to [battleground/index.html](battleground/index.html):
   ```css
   .baby-strat-card.status-awaiting_backtest { border-left-color: #f59e0b; }
   .baby-strat-card.status-bundle_candidate { border-left-color: #8b5cf6; }
   ```

4. **Auto-classify unregistered strategies**: In `app.js` renderUnregistered(), instead of just listing names, tag them with actionable flags:
   - If the strategy file exists in `baby_strategies/` or `incubator/agents/` → `AWAITING_BACKTEST`
   - If a strategy has `backtest_passed` + Sharpe > 0.5 + WR > 50% + not in any bundle → `BUNDLE_CANDIDATE`

5. **Dashboard generator update**: Modify `incubator/backtest_team/generate_baby_strats_dashboard.py` to emit these new statuses.

### Files to modify
- `battleground/app.js` — STATUS_OPTIONS, renderUnregistered()
- `battleground/index.html` — CSS for new status colors
- `battleground/data/baby_strats_dashboard.json` — status_definitions
- `incubator/backtest_team/generate_baby_strats_dashboard.py` — emit new statuses

---

## Phase 3: Fix Cross-Aggregator (Consensus Currently Empty)

### Problem
`cross_aggregation/aggregator.py` has `CONSENSUS_THRESHOLD = 3`, meaning 3+ systems must agree on direction for a symbol. But most active systems scan at different intervals (5min, 15min, 30min, 60min) and have different symbol coverage. **Result: the aggregator output is perpetually empty.**

### Actions
1. **Lower consensus threshold to 2**: In [aggregator.py:55](cross_aggregation/aggregator.py#L55):
   ```python
   CONSENSUS_THRESHOLD: int = 2  # Was 3 — too high, produced zero picks
   ```

2. **Add time-window tolerance**: Currently picks must be "active" simultaneously. Add a 2-hour lookback window so picks from the 15min scanner can overlap with picks from the 60min scanner.

3. **Add tiered consensus output**:
   - **STRONG** (3+ systems agree) — full position size
   - **MODERATE** (2 systems agree) — half position size
   - **WEAK** (1 system, high confidence > 0.85) — quarter position size

4. **Sync scan timing**: Add a 1-minute jitter to workflows so scans don't all fire at exactly :00/:15/:30/:45.

### Files to modify
- `cross_aggregation/aggregator.py` — threshold, time window, tiered output

---

## Phase 4: Super Strategy — Cross-Pair/Cross-Timeframe Consensus

### Concept
A "Super Signal" fires when:
1. **Cross-pair consensus**: 60%+ of tracked crypto pairs show the same direction (e.g., 8 of 12 pairs are BUY)
2. **Cross-timeframe consensus**: The signal holds across 2+ timeframes (15min + 1h + 4h)
3. **Cross-system consensus**: 2+ independent systems agree

When all three conditions align → **Super Signal** = highest conviction trade.

### Design
```
super_strategy/
├── __init__.py
├── cross_pair_detector.py    # Scans all active_picks across symbols
├── cross_timeframe_detector.py  # Checks if signal persists on HTF
├── super_signal_engine.py    # Combines pair + TF + system consensus
└── data/
    └── super_signals.json    # Output: high-conviction signals
```

### Signal Logic
```python
def detect_super_signal(all_active_picks: dict) -> list:
    """
    all_active_picks = {system_id: [picks]}

    1. Group all picks by symbol
    2. For each symbol, count systems agreeing on direction
    3. Check cross-pair: what % of symbols lean same direction?
    4. If cross_pair_ratio >= 0.6 AND system_agree >= 2:
       → SUPER SIGNAL with confidence = cross_pair_ratio * system_count / total_systems
    """
```

### Integration Points
- Runs after cross-aggregator (uses its normalized data)
- Outputs to `super_strategy/data/super_signals.json`
- Discord notification via `cross_aggregation/discord_notify.py`
- Added to Hub as a new system card

### Win Finder Integration
The user mentioned another agent building "win finder combinatory backtesting" (SystemA + B + TradingView → reverse-engineer winning combos). The Super Strategy should:
- Feed its signal history to the win finder for validation
- Accept winning combinations discovered by the win finder as new signal rules
- This creates a feedback loop: Super Strategy → Win Finder → Improved Super Strategy

### Files to create
- `super_strategy/cross_pair_detector.py`
- `super_strategy/cross_timeframe_detector.py`
- `super_strategy/super_signal_engine.py`
- `.github/workflows/super-strategy.yml`

---

## Phase 5: Critical Risk Fixes

### 5A. Ruin Probability (100% → target <30%)

**Root cause:** Too many losing strategies diluting capital. Only 7 of 35 strategies are consistently profitable in walk-forward.

**Fix:**
1. **Kill bottom 80%**: Disable the 28 strategies that fail walk-forward validation
2. **Concentrate on the 7 winners**: adaptive_vr_confluence, hurst_regime_adaptive, multi_sigma_reversal, community_london_breakout, autocorrelation_exploiter, spike_macd_divergence + 1 more
3. **Apply Kelly criterion**: Use the Kelly fractions from `kpi_engine.py` to size positions (most are 0.01-0.05 = 1-5% of capital per trade)
4. **Add portfolio-level stop**: If total drawdown exceeds 15%, halt all new entries for 24h

**File:** `alpha_engine/strategy_guard.py` — already has disable logic, extend it

### 5B. Diversification (0.367 → target >0.65)

**Root cause:** Most strategies use the same crypto pairs (BTC, ETH) and similar indicators (RSI, EMA).

**Fix:**
1. **Enforce sector diversity**: Max 40% crypto, add more forex/equity allocation from proven strategies
2. **Correlation-based selection**: Before emitting picks, check if a new pick is >0.7 correlated with existing open positions → skip it
3. **Use the diversification score** from `regime_analyzer.py` as a real-time gate

### 5C. Compliance Allocation ($154 → target >$500 of $1000)

**Root cause:** Most strategies flagged as manipulation-risky or low-liquidity.

**Fix:**
1. **Focus on major pairs**: BTCUSDT, ETHUSDT, SOLUSDT have the deepest liquidity
2. **Remove micro-cap strategies** from production scanners
3. **Apply per-strategy position limits** from `regulated_assets.py`

---

## Phase 6: Dashboard Integration

### Predictions Dashboard Enhancement
The predictions dashboard at `predictions/dashboard/` should:
1. Pull Super Strategy signals and display them prominently
2. Show cross-system consensus heatmap (which systems agree on which symbols)
3. Add "Bundle Candidate" section showing battleground graduates ready for promotion

### Hub Enhancements
1. Add a "Super Signals" banner at top of Hub (similar to Fresh Picks banner)
2. Add system health indicators (green/yellow/red) based on rolling WR
3. Show correlation matrix between systems as a heatmap

---

## Implementation Priority

| Priority | Phase | Effort | Impact |
|----------|-------|--------|--------|
| **P0** | 5A. Kill losing strategies | 1h | Stops bleeding |
| **P0** | 3. Fix consensus threshold | 30min | Unblocks aggregator |
| **P1** | 1. Add missing Hub systems | 30min | Complete visibility |
| **P1** | 2. Battleground flags | 1h | Strategy pipeline clarity |
| **P2** | 4. Super Strategy | 3-4h | New alpha source |
| **P2** | 5B/5C. Diversification + compliance | 2h | Risk reduction |
| **P3** | 6. Dashboard integration | 2h | UX improvement |

---

## Quick Wins (Can Do Right Now)

1. **Add 2 missing systems to Hub** — 10 min edit to hub/index.html
2. **Lower consensus threshold from 3 → 2** — 1 line change in aggregator.py
3. **Add AWAITING_BACKTEST + BUNDLE_CANDIDATE statuses** — update app.js + CSS
4. **List the 7 walk-forward profitable strategies** in a visible place on the Hub
