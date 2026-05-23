# Antigravity Prediction System — Code Review & Enhancement Plan
## Date: 2026-04-11
## Reviewer: Assistant (OpenClaw)

---

# PART 1: CODE REVIEW — What's Broken

## 1.1 The Scoring System is a Rube Goldberg Machine

`quality_gates.py` is **~3,000+ lines** of accumulated patches, each solving a local problem while creating global complexity. The scoring has:

- **50+ hardcoded constants** (SMART_PICKS_MIN_SCORE, per-asset-class floors, penalties, bonuses)
- **25+ penalty/bonus sources** stacking additively (Sunday penalty, direction conflict, LONG_OVERCONF, streak momentum, preferred pairs, cross-asset confluence, symbol strength tiers, asset class bonuses, forward viability bonuses, ML null penalties...)
- **Comments that contradict each other** — `SMART_PICKS_MIN_SCORE` was 70, then 60, then the comment explains why 70 was right but 60 was forced because no picks passed at 70. The threshold isn't wrong — the **scoring calibration** is wrong.

**The core problem**: When you have 25+ additive adjustments, each ±5-25 points, on a 0-100 scale, the final score is dominated by **which penalties happened to fire**, not by actual predictive signal. A pick with genuine edge can score 45 (filtered out) because it caught a Sunday penalty + direction conflict + ML null penalty. A mediocre pick can score 75 because it dodged penalties.

## 1.2 The `_compute_ml_composite()` in smart_picks_engine.py is Self-Defeating

```python
# Primary: ml_score*0.6 + confidence*0.3 + forward_wr*0.1
# Fallback (no ml_score): confidence*0.8 * ml_null_penalty
```

The AUDIT.md proved that **no ML model has out-of-sample edge** (AUC 0.25-0.28). Yet ml_score gets 60% weight in the composite. This means:
- When ml_score exists: a random-quality number dominates ranking
- When ml_score is missing: confidence fallback with 0.5x penalty pushes good picks DOWN

The ml_null_penalty debate (PR #65 wants to reduce it) is bikeshedding — the entire ml_composite formula needs to be replaced with something that uses **only proven-predictive features**.

## 1.3 Conviction Stack Has Hardcoded Symbol Lists That Rot

```python
"tier_s_symbols": ["DOTUSDT", "SUIUSDT", "LTCUSDT", "NEARUSDT", "XRPUSDT"],
"tier_a_extra_symbols": ["LINKUSDT", "ATOMUSDT", "AVAXUSDT", "SOLUSDT", "ADAUSDT", "BNBUSDT"],
```

These are hand-picked "high conviction" symbols based on a snapshot of performance. Crypto markets rotate — last month's S-tier is this month's laggard. There's no mechanism to **automatically promote/demote** symbols based on rolling performance.

## 1.4 Strategy Kill List is a Growing Graveyard (Not a Learning System)

`PERMANENTLY_KILLED_STRATEGIES` has **40+ entries**, each with a forensic comment. The system has two modes:
- **Run a strategy** (accept all its picks)
- **Kill it forever** (add to blocklist)

There's no middle ground of "this strategy works on THESE symbols in THIS regime but not those." The mutation/rehabilitation system (`strategy_mutations.py`) exists but is bolted on as an afterthought with its own separate logic path.

## 1.5 Forward WR Lookup is a 4-Layer Fallback Waterfall

```python
def _forward_wr_pct(pick):
    # 1. Check extra_json
    # 2. Check top-level fields
    # 3. Check strategy_performance.json (with min_n=3)
    # 4. Check ml_enhanced base name
    # return 0.0 if all fail
```

This means the same strategy can get different forward_wr values depending on whether the data happened to be in extra_json vs top-level vs the performance file. The HC filter at 13:31 UTC returned "WAIT, no edge picks" partly because of this data fragmentation.

## 1.6 Non-Crypto is Quarantined but Not Leveraged

`smart_picks_engine.py` has:
```python
# Non-crypto (forex PF 0.53, equity PF 0.63) must NOT displace crypto picks.
MAX_NON_CRYPTO_PICKS = 3
```

But `quality_gates.py` has:
```python
ASSET_CLASS_BONUSES = {"EQUITY": 8, ...}  # 67.2% WR, PF 2.17
```

These contradict. The smart_picks_engine thinks equity is bad (PF 0.63) while quality_gates thinks it's the best asset class (PF 2.17). The discrepancy is because **different time windows and pick subsets** were analyzed. Nobody reconciled them.

---

# PART 2: HOW TO FIND EDGE PER STRATEGY/SYMBOL AND "PROVE IT"

## 2.1 The Statistical Framework You Need

For each `(strategy, symbol, direction, timeframe)` tuple:

### Minimum Requirements to Claim Edge:
1. **n ≥ 30 closed trades** (bare minimum for statistical inference)
2. **Win rate significantly above break-even** — use exact binomial test:
   - For R:R 2:1, break-even WR = 33%. Need p < 0.05 that WR > 33%.
   - For R:R 1:1, break-even WR = 50%. Need p < 0.05 that WR > 50%.
3. **Profit factor > 1.2** (covers transaction costs + slippage)
4. **Deflated Sharpe Ratio > 0** (accounts for multiple testing)
5. **Forward-test correlation > 0.3** with backtest (from PR #63 audit: only 5/23 strategies passed this)

### Multiple Testing Correction (CRITICAL — Currently Missing):
With 100+ strategy×symbol combinations, you expect ~5 to pass at p<0.05 by pure chance. Apply:
- **Bonferroni correction**: p_adjusted = p × N_tests
- **Or better**: Bailey & Lopez de Prado's **Deflated Sharpe Ratio** (already implemented in `advanced_validation.py` but NOT enforced in the pick pipeline)

### The Proof Protocol (5 stages):

```
Stage 1: BACKTEST VALIDATION
  - Walk-forward on 2+ years of data
  - Purged K-fold CV (already have this)
  - Must pass: Sharpe > 1.0, DSR > 0, PBO < 0.50

Stage 2: OUT-OF-SAMPLE HOLD-OUT
  - Train on data up to T-6months
  - Test on T-6months to T-3months
  - Must pass: metrics within 30% of Stage 1

Stage 3: PAPER FORWARD TEST (3 months minimum)
  - Generate signals in real-time, track against market
  - No lookahead, no parameter tweaking during test
  - Must pass: WR and PF within 25% of Stage 2

Stage 4: SMALL LIVE (1 month)
  - 10% position size
  - Stop if drawdown > 2x backtest max DD

Stage 5: FULL DEPLOYMENT
  - Graduate to normal position sizing
  - Continuous monitoring with auto-demotion if forward metrics degrade
```

## 2.2 How to Actually Find Which (Strategy, Symbol) Combos Work

### Step A: Build the Strategy×Symbol Performance Matrix

```python
# Pseudocode for the matrix builder
for strategy in all_strategies:
    for symbol in all_symbols:
        for direction in [LONG, SHORT]:
            closed = get_closed_picks(strategy, symbol, direction)
            if len(closed) < 10:
                matrix[strategy][symbol][direction] = "INSUFFICIENT_DATA"
                continue
            
            wr = sum(1 for p in closed if p.pnl > 0) / len(closed)
            pf = sum(p.pnl for p in closed if p.pnl > 0) / abs(sum(p.pnl for p in closed if p.pnl < 0))
            avg_pnl = mean(p.pnl for p in closed)
            sharpe = avg_pnl / std(p.pnl for p in closed) * sqrt(252)
            
            # Binomial test against break-even WR
            be_wr = 1 / (1 + avg_rr)  # break-even given actual R:R
            p_value = binom_test(wins, n, be_wr, alternative='greater')
            
            matrix[strategy][symbol][direction] = {
                "n": len(closed),
                "wr": wr,
                "pf": pf,
                "sharpe": sharpe,
                "p_value": p_value,
                "edge": p_value < 0.01 and pf > 1.2 and len(closed) >= 30
            }
```

### Step B: Classify Into Tiers (Replace Hardcoded Lists)

```
TIER S (Deploy Immediately):
  - n ≥ 50, p_value < 0.001, PF > 1.5, Sharpe > 2.0
  - Forward test confirms (correlation > 0.5)
  - Works across 3+ symbols (not curve-fit to one)

TIER A (Deploy with Monitoring):  
  - n ≥ 30, p_value < 0.01, PF > 1.2, Sharpe > 1.0
  - Forward test within 25% of backtest

TIER B (Paper Trade Only):
  - n ≥ 20, p_value < 0.05, PF > 1.0
  - Needs more data before deployment

TIER X (Kill or Mutate):
  - p_value > 0.10 OR PF < 0.8 OR Sharpe < 0
  - Route to mutation pipeline (inverse, symbol-lock, regime-filter)
```

### Step C: Auto-Update Tiers Weekly

Run the matrix builder every Sunday. Auto-promote/demote. No more manual kill lists.

---

# PART 3: THE ENHANCEMENT PLAN (Prioritized)

## Phase 0: Stop the Bleeding (Week 1)

### P0-1: Fix the Bitget Scraper 403
**Why**: Copy trader data has been stale for 7 days. Every signal downstream is operating on week-old data.
**How**: Debug the 403, add health check alert, add fallback to OKX/Bybit copy trader data.

### P0-2: Fix Signal Engine (0 Active Picks)
**Why**: One of 7 bots is producing nothing. Either it's correctly cautious or it's broken.
**How**: Check if the 0-picks state is intentional (all signals below threshold) or a bug.

### P0-3: Enforce min_n=10 (not 5) for HC Tier Entry
**Why**: n=5 gives p-value resolution of 0.031 — almost anything passes. n=10 gives meaningful discrimination.
**How**: Update `hf_conviction_tiers.json` → `min_forward_trades: 10`

### P0-4: Reconcile Equity PF Contradiction  
**Why**: smart_picks says PF 0.63, quality_gates says PF 2.17. One is wrong.
**How**: Run one authoritative analysis on ALL closed equity picks with ghost-pick filter, publish as single source of truth.

---

## Phase 1: Replace the Scoring System (Weeks 2-3)

### P1-1: Build the Strategy×Symbol×Direction Performance Matrix

Create `tools/build_performance_matrix.py`:
- Input: `closed_picks.json` (with ghost filter applied)
- Output: `alpha_engine/data/performance_matrix.json`
- Fields per tuple: n, wr, pf, sharpe, p_value, avg_pnl, max_dd, edge_tier
- Run nightly in CI

### P1-2: Replace Additive Scoring with Lookup-Based Ranking

Instead of:
```python
score = base + asset_bonus + preferred_pair_bonus + confluence_bonus 
        - sunday_penalty - direction_penalty - overconf_penalty ...
```

Do:
```python
def rank_pick(pick):
    key = (pick.strategy, pick.symbol, pick.direction)
    matrix_entry = PERFORMANCE_MATRIX.get(key, {})
    
    # Primary rank: forward-tested edge strength
    edge_score = matrix_entry.get("pf", 0) * matrix_entry.get("wr", 0)
    
    # Secondary: regime alignment (bull/bear/neutral)
    regime_mult = get_regime_multiplier(pick, current_regime)
    
    # Tertiary: freshness (newer picks > stale)
    freshness = time_decay(pick.entry_time, half_life=48h)
    
    return edge_score * regime_mult * freshness
```

This is **auditable** — you can explain exactly why pick A ranked above pick B by pointing to the matrix entry.

### P1-3: Kill the ML Composite (Replace with Forward-Tested Metrics)

Replace `_compute_ml_composite()` with:
```python
def compute_pick_rank(pick):
    # Use ONLY features with proven IC (information coefficient):
    # 1. forward_wr (IC +0.17) — from performance_matrix
    # 2. confidence (IC +0.20) — from consensus agreement
    # 3. regime_alignment (structural) — from regime detector
    # 4. strategy_pf (structural) — from performance_matrix
    
    # DO NOT USE:
    # - ml_score (AUC 0.25-0.28, IC ≈ 0)
    # - elite_score (r = -0.001 with PnL)
```

---

## Phase 2: Strategy Discovery & Validation (Weeks 3-5)

### P2-1: Audit Every Active Strategy Against the Matrix

Run the performance matrix against ALL ~100 strategies. Expected outcome:
- ~10-15 strategies with genuine edge (p < 0.01, n ≥ 30)
- ~20-30 strategies with insufficient data (need more forward test time)
- ~50-60 strategies that should be killed or mutated

### P2-2: For Strategies with Edge, Find the Optimal (Symbol, Direction, Regime) Grid

For each strategy that passes P2-1:
```python
# Which symbols does it work on?
working_symbols = [s for s in symbols if matrix[strategy][s].p_value < 0.01]

# Which direction?
long_edge = matrix[strategy][symbol]["LONG"].pf > 1.2
short_edge = matrix[strategy][symbol]["SHORT"].pf > 1.2

# Which regime?
for regime in ["bull", "neutral", "bear"]:
    regime_pf = compute_pf(picks_in_regime)
    # Some strategies only work in bull (trend-following)
    # Some only in bear (mean-reversion)
```

### P2-3: Implement Auto-Promotion/Demotion

```python
# Weekly job (Sunday midnight UTC)
def weekly_strategy_review():
    matrix = build_performance_matrix()
    
    for strategy in all_strategies:
        tier = classify_tier(matrix[strategy])
        
        if tier == "S":
            set_trust_tier(strategy, "PROVEN")
            set_position_size(strategy, "FULL")
        elif tier == "A":
            set_trust_tier(strategy, "RELIABLE")
            set_position_size(strategy, "STANDARD")
        elif tier == "B":
            set_trust_tier(strategy, "WATCH")
            set_position_size(strategy, "PAPER_ONLY")
        elif tier == "X":
            route_to_mutation_pipeline(strategy)
            # Try: inverse, symbol-lock, regime-filter, TP/SL tweak
            # If all mutations fail after 30 days → KILL
```

### P2-4: Better Strategies to Add

Based on the AUDIT.md and academic literature, strategies with structural edge:

| Strategy | Asset Class | Why It Works | Expected WR | Source |
|----------|-------------|-------------|-------------|--------|
| **RSI-2 Mean Reversion** | SPY/QQQ | Institutional bid creates floor | 70-75% | Already proven in alpha_engine |
| **PEAD (Post-Earnings Announcement Drift)** | Equity | Information asymmetry takes 60-90 days to price | 60-65% | Already in system, needs validation |
| **Funding Rate Arbitrage** | Crypto | Structural: longs pay shorts when funding is positive | 65-70% | In system (PR #63 says "viable") |
| **Pairs Trading (Stat Arb)** | Crypto/Equity | Mean-reversion of correlated pairs | 55-60% | In system (PR #63 says "viable") |
| **Volatility Contraction Breakout** | Crypto | Gainer ML's #1 feature (consolidation_range = 17.5% importance) | 50-55% | Feature exists, needs strategy wrapper |
| **COT Positioning** | Commodity/Forex | Commercial hedgers are informed — follow their positioning | 55-60% | In allowlist, needs more data |
| **Quality-Minus-Junk** | Equity | Fama-French factor — high quality outperforms | 55-60% | In system (PR #63 says "viable") |

### P2-5: Strategies to Investigate Killing/Mutating (Current Data Suggests No Edge)

- All `crypto_soc_*` family (already killed, confirmed)
- `quan_engine_scalp` (1793 trades, -352% PnL — enough data to confirm no edge)
- Any strategy with n > 50 and WR < 40% — mathematically cannot recover
- ML-based crypto predictors on 15m timeframe (AUDIT confirms near-efficient)

---

## Phase 3: Infrastructure Simplification (Weeks 5-8)

### P3-1: Reduce Bot Count from 7 to 3

Current: GSD Edge, Gainer Predictor, Signal Engine, Regime Terminal, QuanEngine, DARWIN, Specialized Scanner — all running every 20 minutes = 504 commits/day.

Proposed:
1. **Signal Generator** (runs every 30 min): Combines GSD Edge + Gainer + Signal Engine + Specialized Scanner into one. Generates candidate picks.
2. **Regime + Portfolio** (runs every hour): Combines Regime Terminal + DARWIN + Portfolio optimizer. Sets regime context and position sizing.
3. **Validator** (runs every hour): Takes candidates from #1, applies performance matrix gates from Phase 1, outputs final picks.

### P3-2: Single Source of Truth for Closed Pick Data

Currently: closed_picks.json, strategy_performance.json, extra_json fields, ab_test_portfolios, cross_asset_edge_finder_results.json — all contain overlapping performance data that may disagree.

Create: `alpha_engine/data/canonical_closed_picks.db` (SQLite)
- Single authoritative table with ghost-pick filter baked in
- All downstream consumers read from this
- Nightly integrity check (no conflict markers, no phantom trades)

### P3-3: Simplify quality_gates.py

The file should be < 500 lines. Replace the 25+ penalty system with:

```python
def passes_quality_gate(pick, matrix):
    key = (pick.strategy, pick.symbol, pick.direction)
    entry = matrix.get(key)
    
    # Hard gates (binary pass/fail)
    if pick.strategy in KILLED_STRATEGIES: return False
    if pick.symbol in BLOCKED_SYMBOLS: return False
    if entry is None or entry["n"] < 10: return False
    if entry["edge_tier"] == "X": return False
    
    # Soft gates (scoring)
    score = entry["pf"] * entry["wr"] * regime_alignment(pick)
    pick["quality_score"] = score
    return score > MINIMUM_SCORE_THRESHOLD
```

---

## Phase 4: Continuous Improvement (Ongoing)

### P4-1: Weekly Strategy Report (Automated)

Every Sunday, generate:
```
STRATEGY HEALTH REPORT — Week of 2026-04-07
=============================================
Total Closed This Week: 47
Aggregate WR: 54.2% | PF: 1.31 | Expectancy: +0.42%

TOP 5 STRATEGIES (by forward PnL this week):
1. st_fear_greed_contrarian LONG DOTUSDT: +12.3% (4/5 wins)
2. funding_rate_arbitrage LONG ETHUSDT: +8.1% (3/3 wins)
...

BOTTOM 5 (auto-demoted):
1. crypto_roc_acceleration LONG: -8.2% (0/4 wins) → DEMOTED to PAPER
...

PROMOTIONS: 2 strategies promoted from B→A
DEMOTIONS: 3 strategies demoted from A→B
KILLS: 1 strategy killed (exhausted mutation pipeline)
```

### P4-2: Regime-Aware Position Sizing

Stop using fixed sizes. In bull regimes, increase trend-following allocation. In bear regimes, increase mean-reversion allocation. In choppy regimes, reduce all sizes.

### P4-3: Monthly Backtest Refresh

Re-run walk-forward validation monthly on all active strategies. Markets change — a strategy's edge can decay. Catch it before forward PnL does.

---

# SUMMARY: Priority Ranking

| Priority | Item | Impact | Effort | Week |
|----------|------|--------|--------|------|
| 🔴 P0 | Fix Bitget scraper 403 | HIGH — 7 days stale data | LOW | 1 |
| 🔴 P0 | Fix Signal Engine 0 picks | HIGH — broken bot | LOW | 1 |
| 🔴 P0 | Raise min_n to 10 for HC | MED — reduces false positives | LOW | 1 |
| 🔴 P0 | Reconcile equity PF numbers | MED — resolves contradiction | LOW | 1 |
| 🟡 P1 | Build performance matrix | **HIGHEST** — foundation for everything | MED | 2 |
| 🟡 P1 | Replace additive scoring | HIGH — removes noise from ranking | MED | 2-3 |
| 🟡 P1 | Kill ml_composite, use forward metrics | HIGH — removes proven-useless signal | LOW | 2 |
| 🟢 P2 | Audit all strategies against matrix | HIGH — find which 10-15 actually work | MED | 3-4 |
| 🟢 P2 | Build strategy×symbol×regime grid | HIGH — precision deployment | MED | 4-5 |
| 🟢 P2 | Auto-promotion/demotion system | MED — removes manual maintenance | MED | 4-5 |
| 🔵 P3 | Reduce 7 bots to 3 | MED — operational simplification | HIGH | 5-6 |
| 🔵 P3 | Single closed-pick database | MED — eliminates data fragmentation | MED | 6-7 |
| 🔵 P3 | Simplify quality_gates.py | MED — maintainability | HIGH | 7-8 |

---

# THE ONE CHART THAT MATTERS

Track this weekly:

```
Forward-Test Net PnL (after costs) — rolling 30-day
====================================================
Target: > 0% (profitable)
Current: estimated -1.53% expectancy (from check_active_picks.py)
Goal Week 4: > 0% (break even)
Goal Week 8: > +0.5% per trade average
```

Everything else is noise until this number is positive.
