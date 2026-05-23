# Cross-System Aggregation Architecture — AI Audit Reference

> **Dashboard:** https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/cross_aggregation/
> **Last updated:** 2026-03-11
> **Purpose:** This document describes the full architecture for AI agents to audit logic and identify improvements.

---

## 1. What This System Does

The Cross-System Aggregator combines trading signals from **12+ independent systems** into consensus picks. The thesis: if multiple systems independently agree on a trade, the signal has higher conviction than any single system alone.

**Pipeline:**
```
12+ Trading Systems (each produces picks independently)
    ↓
Aggregator (deduplicates, votes, scores, filters)
    ↓
Consensus Picks (≥2 systems agree on symbol + direction)
    ↓
SUPER Signals (≥3 systems + ≥60% cross-pair alignment)
    ↓
Outcome Tracker (validates TP/SL against live Binance prices)
    ↓
Dashboard + Discord notifications
```

---

## 2. Source Systems & Their Performance

### Active Systems (as of 2026-03-11)

| System | Source File | Pick Count | Role |
|--------|-----------|------------|------|
| alpha_engine | alpha_engine/data/active_picks.json | ~40-100 | 100+ strategies, LightGBM ML ranking |
| kimi | KIMI_RISEOFTHECLAW/data/active_picks.json | ~40-70 | 81 algorithms, elimination tournament |
| breakout_b | breakout_arena/data/active_picks_b.json | ~10-20 | ML-based breakout detection |
| breakout_c | breakout_arena/data/active_picks_c.json | ~5-15 | Spike reversal patterns |
| battleground | ml_battleground/data/active_picks.json | ~10-30 | Multi-system ML ensemble |
| ml_crypto_pred | ml_crypto_predictor/data/active_picks.json | ~10-20 | Per-coin price prediction |
| crypto_ml_edge | crypto_ml_edge/data/active_picks.json | ~10-20 | Per-coin LightGBM models |
| coinglass_strategies | coinglass_strategies/data/active_picks.json | ~5-15 | Funding rate, OI, liquidation signals |
| predictions | predictions/data/active_picks.json | ~5-10 | Ensemble price predictions |
| rl_agent_ppo | rl_agent/data/active_picks.json | ~5-10 | Reinforcement learning agent |
| genome | genome/data/universal_picks.json | ~4 | Merged DNA evolution output |
| genome_genesis | genome/data/gp_active_picks.json | ~50 | Genetic programming evolved formulas |
| genome_legion | genome/data/ensemble_active_picks.json | ~25 | Coevolved voting teams |
| genome_atlas | genome/data/mape_active_picks.json | ~27 | MAP-Elites quality-diversity search |
| paper_trading | paper_trading/data/active_picks.json | ~10-20 | Paper portfolio signals |

### Demoted Systems (excluded from consensus)

| System | Reason | WR |
|--------|--------|-----|
| ml_bg_a | 0/3 = 0% WR | 0% |
| ml_bg_b | 0/13 = 0% WR | 0% |
| ml_bg_c | 0/5 = 0% WR | 0% |
| ml_bg_d, ml_bg_e | Dead (no picks) | N/A |
| ml_bg_ensemble | 0/8 = 0% WR | 0% |
| signal_engine | Stalled (0/2) | 0% |
| regime_terminal | Dead | N/A |

### Historical Performance (in consensus picks, from outcome tracker)

| System | W | L | WR | Cum PnL | Avg PnL | Status |
|--------|---|---|-----|---------|---------|--------|
| predictions | 5 | 0 | 100% | +25.0% | +5.0% | Strong |
| breakout_b | 3 | 0 | 100% | +15.0% | +5.0% | Strong |
| rl_agent_ppo | 1 | 0 | 100% | +5.0% | +5.0% | Strong (low n) |
| alpha_engine | 1 | 0 | 100% | +5.0% | +5.0% | Strong (low n) |
| ml_crypto_pred | 6 | 2 | 75% | +24.7% | +3.1% | Strong |
| coinglass_strategies | 6 | 7 | 46% | +13.3% | +1.0% | Neutral |
| kimi | 8 | 12 | 40% | +3.6% | +0.2% | Review |
| battleground | 5 | 8 | 38% | -0.5% | -0.04% | Review |
| crypto_ml_edge | 4 | 7 | 36% | +3.3% | +0.3% | Review |
| mercury2 | 0 | 1 | 0% | -1.3% | -1.3% | Review |

**Overall consensus stats:** 14W/13L = 51.9% WR, +30.32% cumulative PnL, +1.12% avg per trade

---

## 3. Consensus Logic (aggregator.py)

### Step 1: Load & Deduplicate
```
For each system:
  1. Load active_picks.json
  2. Discard picks older than 45 minutes (staleness guard)
  3. Filter out banned strategies (hardcoded 0% WR list)
  4. Normalize genome picks (convert tp_pct/sl_pct to absolute prices)
  5. Group picks by normalized symbol (BTC-USD/BTCUSD/BTCUSDT → BTCUSDT)
```

### Step 2: Vote
```
For each symbol:
  Count UNIQUE systems voting LONG vs SHORT
  (One system = one vote, regardless of how many picks it has for that symbol)

  If LONG votes ≥ 2 → emit LONG consensus pick
  Elif SHORT votes ≥ 2 → emit SHORT consensus pick
  Else → blocked conflict (logged, not emitted)
```

### Step 3: Score & Select Best
```
For each agreeing system on the winning direction:
  Keep only the highest-confidence pick per system

  score = adj_confidence × (0.5 + 0.5 × rolling_WR) × (0.5 + 2.0 × sharpe_weight)

  The highest-scoring system's pick becomes the official consensus entry.
```

### Step 4: Confidence Calculation (Fixed 2026-03-11)

**Old (broken):** raw_conf + playbook_boost + consensus_boost → always hit 99% cap.

**New (WR-anchored):**
```python
# Blend raw model confidence with actual system WR
if system has rolling WR data:
    blended = 0.6 × raw_conf + 0.4 × (WR / 100)
else:
    blended = raw_conf × 0.7  # 30% uncertainty discount

# Consensus boost scales with agreement count
consensus_boost = 0.03 × min(agree_count - 1, 3)  # +3% per extra system, max +9%

final_confidence = min(blended + consensus_boost, 0.95)  # Hard cap 95%, never 99%
```

**Example:** ml_crypto_pred with 75% WR, raw_conf=0.80, 3 systems agree:
- blended = 0.6×0.80 + 0.4×0.75 = 0.78
- consensus_boost = 0.03 × 2 = 0.06
- final = min(0.78 + 0.06, 0.95) = **84%** (was 99% before)

### Step 5: Concentration Gate
```
Max 4 crypto LONGs
Max 2 crypto SHORTs
Max 3 high-beta-crypto LONGs (ETH, SOL, AVAX, LINK, etc.)
Max 3 forex picks
Post-TP 4-hour cooldown per symbol
```

### Step 6: BTC Regime Filter
```
If BTC < 200-day SMA (bearish regime):
  Block low-confidence LONGs (conf < 0.70)
  Boost SHORT confidence by 5%
```

---

## 4. SUPER Signal Engine (super_signal.py)

SUPER tier fires when:
1. **Cross-pair alignment ≥ 60%** — most active symbols lean same direction
2. **≥3 independent systems** agree on a specific symbol
3. Confidence boosted by +5% per extra system beyond 2

Historical SUPER performance: 4W/0L (100% WR) — but extremely small sample. Treat as promising, not proven.

---

## 5. Outcome Tracking (consensus_outcome_tracker.py)

```
1. Ingest new consensus picks (≥2 agreement, within 0.5% of entry price)
2. Every 5 minutes: fetch live prices from Binance (4 failover endpoints)
3. Check TP/SL:
   LONG:  price ≥ TP → WON    price ≤ SL → LOST
   SHORT: price ≤ TP → WON    price ≥ SL → LOST
4. Picks expire after 7 days if neither TP nor SL hit
5. Stats computed: WR, cumulative PnL, avg PnL, best/worst trade
```

---

## 6. Genome DNA Evolution System

### 5 Parallel Engines

| Engine | Codename | Method | What It Evolves |
|--------|----------|--------|-----------------|
| genetic_programmer.py | GENESIS | Expression tree GP | Indicator formulas from scratch (26 inputs, math ops) |
| mape_evolver.py | ATLAS | MAP-Elites QD search | Diverse strategies across 5D behavioral grid (675 cells) |
| audit_ensemble_evolver.py | NEXUS | Meta-weight evolution | How much to trust each of 40+ systems |
| ensemble_evolver.py | LEGION | Team coevolution | Voting teams of 3-8 strategies (majority/weighted/bayesian) |
| dna_engine.py | HELIX | Island model GA | Strategy parameters (entry/exit/risk genes, 4 parallel islands) |

### Top Evolved Strategies (backtest)

| Strategy | Type | Symbol | WR | Sharpe | PF | Trades |
|----------|------|--------|-----|--------|-----|--------|
| ENS_EnsembleM_G10_64695a | Ensemble | DOGEUSDT | 76.5% | 45.55 | 3.18 | 17 |
| ENS_EnsembleM_G10_7084af | Ensemble | DOGEUSDT | 68.8% | 44.17 | 3.15 | 16 |
| MAPE_GPM_Gen337_4a026d | MAP-Elites | BTCUSDT | 65.0% | 8.39 | 1.32 | 20 |

**WARNING:** These are BACKTEST results. Forward-test degradation of 10-20% WR is expected. No forward-testing data exists yet for genome strategies.

### Integration Status
- Genome engines produce picks in `genome/data/*.json`
- Aggregator now loads genome_genesis, genome_legion, genome_atlas as independent voting sources
- Each genome engine counts as 1 vote in consensus (can't inflate by having 4 genome engines all vote)

---

## 7. KIMI Rise of the Claw

### Architecture
- 68 active algorithms in elimination tournament
- Algorithms compete: Champions League (≥75 pts), Premier/Challenger/Qualification/Danger Zone
- Bottom performers eliminated, replaced by 20 challengers
- Running every 20 min via GitHub Actions

### Current State (2026-03-11)
- Scanner: ALIVE, producing 39+ signals per cycle
- GitHub Pages: Fixed (was stuck since March 1 due to .db file blocking git push)
- Consensus contribution: 8W/12L = 40% WR (below 45% review threshold)

### Dashboard
- https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/riseoftheclaw.html

---

## 8. Research Questions for AI Audit

### Critical (Answer These First)

1. **Is 51.9% WR statistically significant?** With 27 decided trades, z = (0.519 - 0.5) / sqrt(0.5×0.5/27) = 0.198. p ≈ 0.42. **NOT significant.** Need 100+ trades to determine if edge is real.

2. **Should kimi/battleground/crypto_ml_edge be demoted?** All have WR < 45% in consensus. They may be dragging consensus quality down. But small sample sizes (8-12 losses each).

3. **Are genome strategies overfitting?** 76.5% WR with Sharpe 45 is suspiciously high. Need forward-test validation before trusting.

4. **Confidence calibration:** Does 84% confidence actually win 84% of the time? Need calibration curve (predicted vs actual WR by confidence bucket).

### Important

5. **Optimal consensus threshold:** Is 2 systems too low? Would 3 or 4 systems produce better quality at the cost of fewer picks?

6. **System weighting:** Should high-performing systems (ml_crypto_pred 75% WR) get more weight than low-performers (kimi 40% WR)?

7. **Time-of-day analysis:** Do consensus picks perform differently across Asian/European/US sessions?

8. **Correlation between genome engines:** If all 4 genome engines agree on the same symbol, does that count as 4 independent votes or is it essentially 1 correlated vote?

### Data Quality

9. **Staleness threshold:** Is 45 minutes too generous? Most crypto moves happen in seconds.

10. **Entry price accuracy:** Consensus entry price is from the source system's scan time, not the time user enters. Slippage could be significant.

11. **TP/SL asymmetry:** Average win +1.12% but individual wins range +1.6% to +6.4%. Are TP levels optimally set?

---

## 9. File Map

```
cross_aggregation/
├── aggregator.py           # Main consensus engine (1000+ lines)
├── super_signal.py         # SUPER tier detection
├── conviction_picks.py     # Ultra-selective conviction filter
├── consensus_outcome_tracker.py  # Forward-test TP/SL validator
├── discord_notify.py       # Discord webhook notifications
├── dna_master_tracker.py   # ELITE-tier DNA forward tracking
├── index.html              # Dashboard (GitHub Pages)
├── data/
│   ├── consensus_outcomes.json  # Historical wins/losses
│   └── super_signals.json       # Current SUPER tier picks
└── SYSTEM_ARCHITECTURE.md  # This document

Data flow: system JSONs → aggregator.py → data/aggregated_picks.json
                                        → data/super_signals.json
                        → consensus_outcome_tracker.py → data/consensus_outcomes.json
```

---

## 10. Known Weaknesses

1. **Small sample size** — 27 decided trades is not statistically significant
2. **Survivorship bias in playbook** — preferred symbols derived from winners-only dataset
3. **No forward-test for genome** — 76% WR backtest could be 55% forward
4. **KIMI dragging WR** — 40% WR but still allowed in consensus
5. **Single direction bias** — 86.7% cross-pair alignment LONG suggests market regime dependency
6. **MySQL dependency** — local runs spam errors; works in GitHub Actions only
7. **No position sizing guidance** — consensus picks say WHAT to trade, not HOW MUCH
