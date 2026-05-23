# DNA Mutation v2 — Design Document

**Date:** 2026-03-04
**Status:** Approved
**Approach:** A — "Evolutionary Upgrade" (in-place GA overhaul + pipeline fix)

## Problem

The DNA/Genome engine is broken in three fundamental ways:

1. **Evolution has flatlined** — fitness stuck at 0.5 for 15 generations. The GA isn't finding better strategies.
2. **Mutations are fake** — `dna_mutations.py` uses price proxies (e.g., `close.pct_change(7)` as "hash rate"), not real on-chain data.
3. **Pipeline is disconnected** — 176 factory strategies registered, 0 forward trades. DNA picks can't reach Discord because:
   - No tier filter on pick emission (INCUBATOR strategies emit picks)
   - Baby system and DNA factory use separate DBs that never talk
   - Promotion workflow never fires Discord alerts
   - `DISCORD_WEBHOOK_SANDBOX` missing = experimental picks silently dropped

**Audit trail evidence:**
- Zero DNA/genome strategies exist in `at_signal_outcomes` (MySQL)
- All 623 meta-strategy combos on PROBATION after DRAWDOWN_SPIRAL (2026-03-02)
- Only 2 strategies have real forward data: `crypto_kalman_trend_residual_reversion_v1` (62% WR, 29 trades) and `crypto_rsi_whaleconfirmed_v1` (65% WR, 77 trades)

## Solution

A full GA engine overhaul + pipeline fix, delivered as 5 components.

---

## Component 1: NSGA-II Multi-Objective Fitness

### Current State (broken)
Single weighted fitness in `genome/dna_engine.py`:
```python
overall_fitness = 0.25*sharpe + 0.20*win_rate + 0.20*min(pf/3,1) + 0.20*max(0,min(return/2,1)) + 0.15*max(0,1-abs(dd))
```
This produces overfit single-point solutions.

### New State
Replace with 3-objective Pareto optimization using `pymoo` (NSGA-II):

**Objectives (all maximized):**
1. `sharpe_ratio` — risk-adjusted returns
2. `-max_drawdown` — capital preservation (minimize DD = maximize -DD)
3. `win_rate * sqrt(trade_count)` — consistency weighted by statistical significance

**Selection:** After NSGA-II produces a Pareto front, use the "knee point" (best trade-off) as each island's champion. Keep the full Pareto front as population — not just one winner.

**Implementation:**
```python
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.core.problem import Problem
from pymoo.optimize import minimize

class StrategyEvolutionProblem(Problem):
    def __init__(self, n_genes, backtest_func, price_data):
        super().__init__(n_var=n_genes, n_obj=3, xl=gene_lower_bounds, xu=gene_upper_bounds)
        self.backtest = backtest_func
        self.data = price_data

    def _evaluate(self, X, out, *args, **kwargs):
        results = [self.backtest(genes, self.data) for genes in X]
        out["F"] = np.array([
            [-r.sharpe, r.max_drawdown, -(r.win_rate * math.sqrt(r.trade_count))]
            for r in results
        ])  # pymoo minimizes, so negate objectives we want to maximize
```

**Reference:** MOO3 paper (AI Review 2025) — 3-objective modified Sharpe consistently outperforms single-objective.

---

## Component 2: Adaptive Mutation Rates

### Current State (broken)
Fixed `mutation_rate = 0.10`, `mutation_strength = 0.3`. Applied per-gene independently. Results: 15 generations of zero improvement.

### New State
Stagnation-aware adaptive rate:

```python
def adaptive_mutation_rate(generation, stagnation_count, base_rate=0.02):
    if stagnation_count > 5:
        # Ramp up mutation to escape local optimum
        return min(base_rate * (1 + 0.3 * stagnation_count), 0.25)
    # Decay toward convergence
    return max(base_rate * 0.95 ** generation, 0.005)
```

Track `best_pareto_hypervolume` per generation. If it doesn't improve for 5 consecutive generations, ramp mutation rate.

**Reference:** CGA-Agent (arXiv 2510.07943) — dynamic parameter reoptimization on BTC/ETH/SOL.

---

## Component 3: 4-Island Model

### Current State (broken)
Single population of 50 strategies that converges to one local optimum (EMA golden cross on 4H).

### New State
Split into 4 islands of ~15 strategies, each evolving on different historical regimes:

| Island | Historical Window | Mutation Bias | Seed Strategies |
|---|---|---|---|
| 0 - Bear | Last major drawdown | Defensive/short genes | `vwap_sd_mean_reversion` (70-75%), `connors_rsi2_crypto` (62.5%), `funding_rate_carry` (60%) |
| 1 - Bull | Last major rally | Momentum/long genes | `rsi_macd_confluence` (65%), `multi_timeframe_ema_stack` (65-72%), `hash_ribbon_buy` (78%) |
| 2 - Range | Low-vol sideways | Mean-reversion genes | `keltner_mean_reversion` (67.6%), `bollinger_mean_reversion` (60.7%), `consecutive_down_rsi` (74.3%) |
| 3 - Recent | Last 30 days | No bias (exploratory) | HMLF-style ensemble combos (4-signal voting + regime filter) |

**Migration:** Every 10 generations, top 2 strategies from each island migrate to the next (ring topology: 0→1→2→3→0).

**Seeding:** Each island starts with 3-4 proven winners, then generates 12+ mutations to fill to population size 15. This gives the GA a meaningful starting point.

**HMLF Ensemble Pattern (Island 3 seed):**
The "Recent" island seeds with ensemble strategies that combine 4 proven high-WR signals:
- Momentum: `rsi_macd_confluence` (65% WR)
- Liquidity: `liquidity_sweep_reversal` (60-72% WR)
- Mean-Reversion: `vwap_sd_mean_reversion` (70-75% WR)
- Carry: `funding_rate_carry` (60% WR)
- Regime filter: `hurst_regime_filter` gates signal in volatile periods

Weighted voting (0.35 mom + 0.30 liq + 0.20 vwap + 0.15 fund), threshold ≥ 0.6 to fire.

**Reference:** Island-based EA with Diverse Surrogates (ACM TELO 2024) — prevents premature convergence.

---

## Component 4: Real On-Chain Mutation Genes (`genome/onchain_data.py`)

### Current State (broken)
`dna_mutations.py` uses 4 fake proxies:
- "Hash rate momentum" = `close.pct_change(7)` (just price momentum)
- "Active address growth" = `volume.pct_change(3)` (just volume change)
- "Funding skew" = `(close - MA20) / close` (just price deviation)
- "Depth imbalance" = `(high - low) / volume` (just range/volume ratio)

### New State
Replace with real data from free APIs:

| Gene | Source | API Endpoint | Cost | Update Freq |
|---|---|---|---|---|
| `funding_rate` | Binance Futures | `/fapi/v1/fundingRate` | Free | Every 8h |
| `fear_greed_index` | alternative.me | `/fng/` | Free | Daily |
| `stablecoin_supply_ratio` | CoinGecko | `/global` (USDT+USDC cap / BTC cap) | Free | Hourly |
| `btc_dominance` | CoinGecko | `/global` | Free | Hourly |
| `exchange_volume_change` | CoinGecko | `/exchanges/{id}/volume_chart` | Free | Hourly |
| `dxy_proxy` | Already in forex_rates injection | Existing | Free | Existing |

**Mutation bias logic:**
```python
def get_mutation_bias(onchain_data):
    bias = {}
    if onchain_data['fear_greed'] < 20:  # extreme fear
        bias['entry_direction'] = 'long'
        bias['tp_mult_range'] = (2.0, 5.0)  # wider targets
    if onchain_data['funding_rate'] > 0.03:  # overleveraged longs
        bias['entry_direction'] = 'short'
    if onchain_data['ssr'] < 13:  # lots of stablecoin buying power
        bias['position_size_range'] = (0.05, 0.15)  # larger positions
    return bias
```

When a gene mutates, the bias shifts the mutation's random range toward the on-chain-indicated direction.

**Caching:** Cache all API responses for 1 hour in `genome/data/onchain_cache.json` to avoid rate limits. The 4h pipeline only needs 1 fresh fetch per run.

---

## Component 5: Pipeline Fix

### 5a. Tier-Gated Pick Emission (`genome/generate_picks.py`)

**Current:** All strategies emit picks to `genome/active_picks.json` regardless of tier.
**New:** Only SANDBOX+ tier strategies emit picks.

```python
def generate_picks(strategies, tier_data):
    picks = []
    for s in strategies:
        tier = tier_data.get(s.id, 'INCUBATOR')
        if tier in ('SANDBOX', 'FRESH_PICKS', 'DNA_MASTER'):
            picks.append(s.generate_pick())
    write_active_picks(picks)
```

Tier routing through the aggregator:
```
INCUBATOR    → silent (tracked internally, no picks emitted)
SANDBOX      → picks go to #sandbox Discord channel (EXPERIMENTAL class)
FRESH_PICKS  → picks enter main consensus (#fresh-picks / main)
DNA_MASTER   → picks go to #dna-master-picks (ELITE class)
```

### 5b. Forward Trades → MySQL `at_signal_outcomes`

When a DNA pick gets resolved (TP/SL hit via `signal_tracker.py` or `signal_validator.py`):

```python
def log_outcome_to_mysql(pick, outcome, exit_price, pnl_pct):
    sql = """
        INSERT INTO at_signal_outcomes
        (symbol, direction, entry_price, take_profit, stop_loss,
         exit_price, outcome, pnl_pct, source_system, strategy,
         asset_class, opened_at, closed_at, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
    """
    params = (pick['symbol'], pick['direction'], pick['entry_price'],
              pick['tp'], pick['sl'], exit_price, outcome, pnl_pct,
              'dna_genome', pick['strategy_id'], 'CRYPTO',
              pick['opened_at'], datetime.utcnow())
    cursor.execute(sql, params)
```

This means the Strategy Health Monitor (already built, running every 4h) automatically:
- Computes expectancy and profit factor for DNA strategies
- Assigns CORE/INCUBATOR/BANNED tier
- Writes to `banned_strategies.json` if banned
- Logs tier changes to `strategy_health_audit`

### 5c. Standalone Promotion Check

Add a new job to `dna_strategy_pipeline.yml` that runs independently:

```yaml
  check-promotions:
    runs-on: ubuntu-latest
    needs: [generate-picks]  # runs after picks, not dependent on factory-register
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install pymysql requests
      - name: Check promotions and notify
        env:
          MYSQL_HOST: mysql.50webs.com
          MYSQL_USER: ejaguiar1_stocks
          MYSQL_PASSWORD: ${{ secrets.MYSQL_PASSWORD }}
          MYSQL_DB: ejaguiar1_stocks
          DISCORD_WEBHOOK_DNA_MASTER: ${{ secrets.DISCORD_WEBHOOK_DNA_MASTER }}
          DISCORD_WEBHOOK_URL: ${{ secrets.DISCORD_WEBHOOK_URL }}
          DISCORD_WEBHOOK_SANDBOX: ${{ secrets.DISCORD_WEBHOOK_SANDBOX }}
        run: python -m genome.progressive_promotion --check --notify
```

### 5d. Strategy Health Monitor Integration

Add `dna_genome` as a data source in `strategy_health/monitor.py`:

```python
def fetch_strategy_metrics(conn):
    # Existing: at_signal_outcomes, cw_winners
    # New: also fetch dna_genome strategies from at_signal_outcomes
    # (they auto-appear because we write to at_signal_outcomes in 5b)
    # No code change needed — the monitor already queries all source_systems
    pass
```

The monitor already queries `at_signal_outcomes` grouped by `source_system, strategy`. Once DNA writes there, it's automatically tracked.

---

## File Structure

```
genome/
    dna_engine.py              # MODIFY — NSGA-II, adaptive mutation, island model
    dna_mutations.py           # REWRITE — real on-chain gene bias
    onchain_data.py            # NEW — API fetcher (Binance, CoinGecko, alternative.me)
    seed_strategies.py         # NEW — proven winners as island seeds
    evolve_strategies.py       # MODIFY — use new engine, seed islands
    generate_picks.py          # MODIFY — tier-gated emission
    progressive_promotion.py   # MODIFY — --check --notify mode, MySQL outcome writer
    data/
        onchain_cache.json     # Cached API responses (1h TTL)
.github/workflows/
    dna_strategy_pipeline.yml  # MODIFY — add pymoo, promotion-check step
cross_aggregation/
    aggregator.py              # MODIFY — tier-aware gating for DNA (partially done)
strategy_health/
    monitor.py                 # MODIFY — DNA strategies auto-tracked via at_signal_outcomes
```

---

## Workflow: Updated `dna_strategy_pipeline.yml`

```yaml
name: DNA Strategy Pipeline v2
on:
  schedule:
    - cron: '0 */4 * * *'
  workflow_dispatch:

permissions:
  contents: write

jobs:
  evolve-strategies:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install deps
        run: pip install pymysql requests pymoo numpy pandas
      - name: Fetch on-chain data
        run: python -m genome.onchain_data
      - name: Evolve population (NSGA-II + islands)
        env:
          MYSQL_HOST: mysql.50webs.com
          MYSQL_USER: ejaguiar1_stocks
          MYSQL_PASSWORD: ${{ secrets.MYSQL_PASSWORD }}
          MYSQL_DB: ejaguiar1_stocks
        run: python -m genome.evolve_strategies --generations 20 --islands 4
      - name: Generate picks (tier-gated)
        run: python -m genome.generate_picks --tier-filter
      - name: Commit results
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add genome/results/ genome/active_picks.json genome/data/
          git diff --cached --quiet || git commit -m "DNA v2: evolution + picks [$(date -u '+%Y-%m-%d %H:%M UTC')]"
          git pull --rebase origin main || true
          git push

  check-promotions:
    runs-on: ubuntu-latest
    needs: [evolve-strategies]
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install pymysql requests
      - name: Check promotions and notify Discord
        env:
          MYSQL_HOST: mysql.50webs.com
          MYSQL_USER: ejaguiar1_stocks
          MYSQL_PASSWORD: ${{ secrets.MYSQL_PASSWORD }}
          MYSQL_DB: ejaguiar1_stocks
          DISCORD_WEBHOOK_DNA_MASTER: ${{ secrets.DISCORD_WEBHOOK_DNA_MASTER }}
          DISCORD_WEBHOOK_URL: ${{ secrets.DISCORD_WEBHOOK_URL }}
          DISCORD_WEBHOOK_SANDBOX: ${{ secrets.DISCORD_WEBHOOK_SANDBOX }}
        run: python -m genome.progressive_promotion --check --notify
```

---

## Config & Secrets

| Parameter | Source | Default |
|---|---|---|
| `MYSQL_HOST` | env / secret | mysql.50webs.com |
| `MYSQL_USER` | env / secret | ejaguiar1_stocks |
| `MYSQL_PASSWORD` | GitHub secret | (required) |
| `MYSQL_DB` | env | ejaguiar1_stocks |
| `DISCORD_WEBHOOK_DNA_MASTER` | GitHub secret | (required) |
| `DISCORD_WEBHOOK_URL` | GitHub secret | (required) |
| `DISCORD_WEBHOOK_SANDBOX` | GitHub secret | (required) |
| `COINGECKO_API_KEY` | GitHub secret | (optional, for higher rate limits) |

---

## Testing

1. **Unit tests** (`tests/test_dna_engine_v2.py`)
   - NSGA-II produces a Pareto front with 3 objectives
   - Adaptive mutation rate ramps on stagnation, decays on improvement
   - Island migration transfers top strategies correctly
   - On-chain data fetcher returns valid gene values (mock APIs)

2. **Dry-run mode** — `python -m genome.evolve_strategies --dry-run`
   - Prints evolution stats without writing to DB
   - Shows which strategies would emit picks at each tier

3. **Integration test**
   - Run full pipeline locally, verify picks appear in `active_picks.json`
   - Verify forward trade results write to `at_signal_outcomes`
   - Verify Strategy Health Monitor picks up dna_genome strategies

---

## Summary of Changes

| File | Action |
|---|---|
| `genome/dna_engine.py` | MODIFY — NSGA-II 3-objective, adaptive mutation, island model |
| `genome/dna_mutations.py` | REWRITE — real on-chain gene bias from APIs |
| `genome/onchain_data.py` | NEW — Binance/CoinGecko/alternative.me data fetcher |
| `genome/seed_strategies.py` | NEW — proven winners as island seeds |
| `genome/evolve_strategies.py` | MODIFY — use new engine, seed islands |
| `genome/generate_picks.py` | MODIFY — tier-gated emission (SANDBOX+ only) |
| `genome/progressive_promotion.py` | MODIFY — MySQL outcome writer, --check --notify mode |
| `.github/workflows/dna_strategy_pipeline.yml` | MODIFY — pymoo dep, promotion step |
| `cross_aggregation/aggregator.py` | MODIFY — tier-aware DNA gating |
| `strategy_health/monitor.py` | NO CHANGE — auto-tracks dna_genome via at_signal_outcomes |
