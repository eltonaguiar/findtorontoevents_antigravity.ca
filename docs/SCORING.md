# Antigravity Trading Systems — Scoring Reference

> Master document covering how every trading system scores, ranks, and grades picks.
> Last updated: 2026-03-16

## Table of Contents

1. [System Overview](#system-overview)
2. [Alpha Engine (Elite Scorer)](#alpha-engine)
3. [KIMI Rise of the Claw](#kimi)
4. [Cross-System Aggregator (Consensus)](#cross-system-aggregator)
5. [Claude Gainer ML](#claude-gainer-ml)
6. [ML Crypto Predictor](#ml-crypto-predictor)
7. [Audit Dashboard](#audit-dashboard)
8. [Other Systems](#other-systems)
9. [Known Flaws & Cross-System Issues](#known-flaws)

---

## System Overview

```
Individual Systems (generate picks independently)
├── Alpha Engine ───── 100 strategies, elite_score 0-100 (S/A/B/C/D/F)
├── KIMI ───────────── 81 algorithms, mlWinProb 0-1.0, tournament elimination
├── Claude Gainer ML ─ Ensemble (RF+XGB), pump_probability 0-1.0
├── ML Crypto Pred ─── Ensemble (RF+GBT+XGB), calibrated probability 0-1.0
├── Rapid Fire ─────── ATR scalps, multi-exchange price consensus 0.33-1.0
├── Quan Engine ────── Regime-routing consensus, avg_confidence 0-1.0
├── Battleground ───── DNA system, 4 significant strategies
├── Incubator ──────── Baby strategies forward-testing
└── Genome ─────────── Walk-forward tournament evolution
         │
         ▼
Cross-System Aggregator (consensus layer)
├── Trust-weighted voting (PROVEN 2.0x → BANNED 0.0x)
├── WR-anchored confidence (60% model + 40% real WR)
├── Beta Confluence Score (5 pillars, 0-100)
└── Pick classification (ELITE / PROVEN / EXPERIMENTAL)
         │
         ▼
Audit Dashboard (grading layer)
├── Strategy health score (0-100 → HEALTHY/WATCH/DEGRADED)
├── Pick quality grade (A/B/C/D/F)
└── System trust tiers (PROVEN/RELIABLE/WATCH/SANDBOX)
```

---

## Alpha Engine

> **Detailed reference:** [SCORING_ALPHA.md](SCORING_ALPHA.md)

### Elite Scorer (0-100 points, 7 components)

| Component | Max | What It Measures | Key Thresholds |
|-----------|-----|-----------------|----------------|
| ML Score | 25 | ML ranker confidence | `ml_score × 25` |
| Forward WR | 25 | Real forward-test win rate | 10+ trades @ >55% = full; 3+ trades @ >40% = partial |
| Confluence | 15 | Multiple strategies agreeing | 5+ strategies = 15pts; 2 = 8pts |
| Risk:Reward | 10 | TP/SL distance ratio | R:R ≥ 3.0 = 10pts; ≥ 2.0 = 7pts |
| Monte Carlo | 15 | Statistical significance | PROVEN = 15pts; INCONCLUSIVE = 3-5pts |
| Volume | 5 | Above-average volume | >2.0x = 5pts; >1.2x = 3pts |
| Regime | 5 | Direction matches market regime | Aligned = 5pts; Incompatible = 0pts |

### Grade Scale

| Grade | Score | Meaning |
|-------|-------|---------|
| **S** | 90-100 | Genuinely elite — all signals aligned |
| **A** | 75-89 | Very strong — proven strategy + confluence |
| **B** | 60-74 | Solid — good metrics, some gaps |
| **C** | 45-59 | Acceptable — adequate but unproven |
| **D** | 30-44 | Weak — missing multiple quality signals |
| **F** | <30 | Unproven — insufficient data or poor metrics |

### ML Ranker Pipeline

```
Raw Signals (100 strategies)
  → Falling knife filter (>25% below 200d SMA → reject)
  → R:R gate (< 1.5 → reject)
  → Regime penalty (counter-regime → ×0.70)
  → Volume warning (low vol breakout → ×0.80)
  → Repeat-loser cooldown (2+ SL in 72h → ×0.50)
  → ML scoring (trained RF/XGB or heuristic fallback)
  → Meta-labeling gate (win_prob < 0.65 → suppress)
  → MIN_ML_SCORE = 0.50 filter
  → Max 3 picks per symbol
  → Elite Scorer (0-100 composite)
```

### Key Files
- `alpha_engine/elite_scorer.py` — 7-component quality scoring
- `alpha_engine/scanner.py` — Signal ranking + filtering (lines 1338-1740)
- `alpha_engine/ml_ranker.py` — 39-feature ML model
- `alpha_engine/confluence_engine.py` — Synergy/anti-synergy detection
- `alpha_engine/forward_validator.py` — Forward-test gate + pick assembly

---

## KIMI

> **Detailed reference:** [SCORING_KIMI.md](SCORING_KIMI.md)

### Signal Confidence Pipeline

```
81 Algorithms fire independently
  → Raw confidence 0.56-0.85 (strategy-specific formulas)
  → Pre-entry gates (gap chase, concentration, earnings, hours)
  → ATR-based TP/SL (category-specific multipliers)
  → Signal probability = SL_dist / (TP_dist + SL_dist) [5%-95%]
  → Confluence filter (2+ algos OR single @ conf ≥ 0.65)
  → ML ranking (heuristic < 50 picks, RandomForest ≥ 50)
  → Final confidence = mlWinProb × 100
```

### ML Ranker (Two Modes)

**Heuristic mode** (< 50 closed picks):
- Base 0.5 + WR contribution (40%) + Sharpe (20%) + tier bonus (10%) + conf (30%)

**ML mode** (≥ 50 closed picks):
- RandomForest (200 trees, max_depth=8, balanced classes)
- 9 features: algo_id, category, symbol, tier, WR, Sharpe, drought, closed_count, Kelly
- TimeSeriesSplit 5-fold cross-validation

### Confluence Scoring

| Algo Count | Confluence Score | Size Boost |
|-----------|-----------------|------------|
| 1 (high conf) | 50 | None |
| 2 | 65 | +25% |
| 3 | 80 | +50% |
| 4+ | 100 | +50% |

### Tournament Elimination

| State | Threshold | Duration | Result |
|-------|-----------|----------|--------|
| Active | Score ≥ 40 | — | Normal operation |
| Danger Zone | Score < 40 | 3+ days | Warning state |
| Probation | Score < 30 | 2+ days | Final warning |
| Eliminated | Confirmed | — | Replaced by challenger |

### Key Files
- `KIMI_RISEOFTHECLAW/live_scanner.py` — Signal generation + allocation
- `KIMI_RISEOFTHECLAW/ml_signal_ranker.py` — ML/heuristic ranking
- `KIMI_RISEOFTHECLAW/elimination_engine.py` — Tournament scoring
- `KIMI_RISEOFTHECLAW/signal_tracker.py` — TP/SL validation

---

## Cross-System Aggregator

> **Detailed reference:** [SCORING_CONSENSUS.md](SCORING_CONSENSUS.md)

### Trust Tiers & Vote Weights

| Tier | Criteria | Vote Weight | Allocation Max |
|------|----------|-------------|----------------|
| **PROVEN** | WR > 65% AND 30+ trades | 2.0x | 50% |
| **RELIABLE** | WR 55-65% AND 10+ trades | 1.5x | 30% |
| **WATCH** | < 10 trades (any WR) | 1.0x | — |
| **UNTRUSTED** | WR < 50% AND 10-29 trades | 0.3x | 5% |
| **BANNED** | WR < 50% AND 30+ trades | 0.0x | 0% |

### Confidence Calculation (WR-Anchored)

```
Step 1: Blend model confidence with real performance
  blended_conf = 0.60 × raw_model_conf + 0.40 × system_WR
  (If WR unknown: blended_conf = raw_conf × 0.70)

Step 2: Consensus boost
  consensus_boost = 0.03 × min(agreeing_systems - 1, 3)
  (+3% per extra system, max +9%)

Step 3: Regime multiplier
  boosted_conf × regime_mult (0.90-1.10 based on strategy type)

Step 4: Hard cap at 0.95 (never 99%)
```

### Consensus Tiers

| Tier | Weighted Votes | Typical Scenario |
|------|---------------|------------------|
| **SUPER** | ≥ 6.0 | 3+ PROVEN/RELIABLE systems agree |
| **STRONG** | 3.0-5.99 | 1 PROVEN + 2 WATCH systems |
| **MODERATE** | 2.0-2.99 | 2 WATCH systems (minimum) |

### Beta Confluence Score (Experimental, 5 Pillars)

| Pillar | Max | Inputs |
|--------|-----|--------|
| Technical | 25 | RSI, volume ratio, model confidence, system agreement |
| On-chain | 20 | Fear & Greed, exchange flows, MVRV, order book |
| Sentiment | 15 | F&G regime match, LunarCrush Galaxy Score |
| Risk/Reward | 20 | R:R ratio, remaining TP room, SL distance vs ATR |
| Structure | 20 | Regime alignment, BTC correlation, volatility, funding rate |

**Qualified threshold:** ≥ 70/100

### Pick Classification (Discord Routing)

| Class | Route | Criteria |
|-------|-------|----------|
| **ELITE** | #dna-master-picks | ≥3 systems, 2+ PROVEN, conf ≥ 0.60 |
| **PROVEN** | #fresh-picks | ≥2 systems, 1+ with WR≥55% |
| **EXPERIMENTAL** | #sandbox | Everything else |

### Key Files
- `cross_aggregation/aggregator.py` — Main consensus orchestrator
- `cross_aggregation/system_trust_registry.py` — Tier definitions + dynamic computation
- `cross_aggregation/beta_confluence_scorer.py` — 5-pillar experimental scoring
- `cross_aggregation/freshpicks_gate.py` — 8 quality gates for Discord
- `cross_aggregation/pick_classifier.py` — ELITE/PROVEN/EXPERIMENTAL routing

---

## Claude Gainer ML

### Ensemble Architecture
- **Random Forest** (45-50% weight) + **XGBoost** (50-55% weight)
- 30 input features (volume, momentum, volatility, structure, sentiment)
- Output: `pump_probability` (0.0000-1.0000)

### Confidence Tiers

| Tier | Threshold | Meaning |
|------|-----------|---------|
| VERY HIGH | ≥ p95 percentile | Top 5% of predictions |
| HIGH | ≥ p80 percentile | Top 20% |
| MEDIUM | ≥ p60 percentile | Above average |
| LOW | < p60 percentile | Below average |

### TP/SL Targets
- **TP1:** +3% (allows TP2 chase)
- **TP2:** +8% (final target)
- **SL:** -5% (stop loss)
- **TIME_EXIT:** 8 days max hold

### Key Files
- `claude_gainer_ml/live_scanner.py` — Feature computation + ensemble prediction
- `claude_gainer_ml/tp_sl_tracker.py` — TP/SL tracking + performance

---

## ML Crypto Predictor

### Ensemble Architecture (v3.1)
- **Random Forest** (25% weight, Platt calibration)
- **Gradient Boosting** (35% weight, Isotonic calibration)
- **XGBoost** (40% weight)
- 50+ features + 4-state regime detection
- Walk-forward validation with 48-bar purge gap

### Regime States
- **BULL:** 30d return > +15%
- **BEAR:** 30d return < -15%
- **SIDEWAYS:** |return| ≤ 15%
- **HIGH_VOL:** 30d volatility > 80% (overrides)

### Confidence Levels

| Level | Criteria |
|-------|----------|
| STRONG BUY | prob ≥ 0.75 AND bullish regime AND backtest WR > 55% |
| BUY | prob ≥ 0.65 AND regime compatible |
| WATCH | prob ≥ 0.55 |
| HOLD | prob < 0.55 |

### Key Files
- `ml_crypto_predictor/production_engine.py` — Ensemble + calibration

---

## Audit Dashboard

> **Detailed reference:** [SCORING_AUDIT.md](SCORING_AUDIT.md)

### Strategy Health Score (0-100)

| Component | Weight | Good | Bad |
|-----------|--------|------|-----|
| Forward vs Backtest Decay | 30% | Decay > -10%: +15pts | Decay < -30%: -15pts |
| Recent vs Lifetime WR | 30% | Ratio ≥ 0.9: +15pts | Ratio < 0.7: -15pts |
| Sample Quality | 20% | ≥20 trades: +10pts | <5 trades: -10pts |
| Trade Volume | 20% | ≥20 closed: +10pts | <10: 0pts |

**Status:** ≥65 = HEALTHY | 40-64 = WATCH | <40 = DEGRADED

### Pick Quality Grade

| Grade | Score | Calculation |
|-------|-------|-------------|
| **A** | ≥ 80 | High WR + good PF + healthy strategy |
| **B** | 70-79 | Solid metrics, minor concerns |
| **C** | 55-69 | Moderate conviction |
| **D** | 40-54 | Low conviction |
| **F** | < 40 | Very low conviction or degraded strategy |

Formula: `performanceBase × healthMultiplier × csrMultiplier`
- performanceBase = (forward_wr × 0.6) + (PF/3 × 100 × 0.4)
- healthMultiplier: HEALTHY=1.0, WATCH=0.75, DEGRADED=0.4
- csrMultiplier: Common Sense Ratio weight (10%)

### System Trust Tiers (Audit-Specific)

| Tier | Criteria (≥20 trades) | Weight |
|------|----------------------|--------|
| PROVEN | WR ≥ 65% AND PF ≥ 2.0 | 0.95 |
| RELIABLE | WR 55-64% AND PF ≥ 1.5 | 0.85 |
| RELIABLE | WR 50-54% AND PF ≥ 1.0 | 0.75 |
| WATCH | WR 45-49% | 0.60 |
| SANDBOX | WR 35-44% | 0.40 |
| SANDBOX | WR < 35% | 0.25 |

### Key Files
- `audit_trail/dashboard_generator.py` — Health scoring + leaderboard
- `audit_dashboard/index.html` — Client-side trust tier + pick grading

---

## Other Systems

### Rapid Fire
- **Scoring:** Multi-exchange price consensus (0.33-1.0)
- **Exit:** ATR trailing stop (+1.5% activation, 1.5× ATR trail) or 24h time exit
- **Files:** `rapid_fire_data/pick_tracker.py`

### Quan Engine
- **Scoring:** Regime-routed consensus averaging
- **Pipeline:** RegimeRouter → QuanEnsemble → ModeDispatcher → RiskGate
- **Files:** `quan_engine/scanner.py`

### Incubator / Genome / Battleground
- **Incubator:** Forward-tests baby strategies, tracks per-strategy WR
- **Genome:** Walk-forward tournament evolution, survival of fittest
- **Battleground:** DNA system with 4 statistically significant strategies (65.2% WR)

---

## Known Flaws

### Cross-System Issues

| Flaw | Severity | Affected Systems | Detail |
|------|----------|-----------------|--------|
| **Crypto convergence trap** | HIGH | Alpha, Aggregator | 3+ crypto strategies agreeing = 25% WR (vs 52.9% solo). Mitigated with 0.75x penalty but may need more. |
| **No cross-system confidence normalization** | MEDIUM | All | Alpha uses 0-100, KIMI uses 0-1.0, Gainer uses percentile tiers. Aggregator blends incompatible scales. |
| **Stale pick accumulation** | MEDIUM | Monitor | Picks from disabled systems (Mercury2, ML Crypto Pred) remain in dashboards confusing metrics. |
| **Regime scoring defaults to "compatible"** | LOW | Alpha | `regime_compatible` defaults True, `current_regime` often empty. Every pick gets 5/5 regime points. |
| **Unvalidated confidence labels** | LOW | Claude Gainer | Every pick labeled "VERY HIGH" confidence — no real differentiation. |

### Alpha Engine Specific

| Flaw | Detail | Fix Status |
|------|--------|------------|
| Confluence was 0/15 for ALL picks | `confluence_strategies` field never populated | **FIXED** (2026-03-16) |
| Forward WR threshold too high (15 trades) | Only 1 of 36 strategies qualified | **FIXED** (lowered to 3/5/10 tiers) |
| Monte Carlo 0 for 91% of strategies | INSUFFICIENT_DATA with no partial credit | **FIXED** (partial credit for 3-5+ trades) |
| Volume ratio null for 93% of picks | Field not exported by strategies | **FIXED** (extract from reason text) |
| No repeat-loser protection | H, INJ, ZEC each lost twice | **FIXED** (72h cooldown after 2 SL hits) |

### KIMI Specific

| Flaw | Detail |
|------|--------|
| Solo picks from KIMI had -219% PnL | Now CONFIRMER-ONLY (can't lead consensus) |
| 81 algorithms but only 9 features in ML | Many algorithms behave similarly → false confluence |
| Drought relaxation can lower quality bars | Algorithms fire weaker signals after dry spells |

### Aggregator Specific

| Flaw | Detail |
|------|--------|
| Playbook boosts based on survivorship bias | +1% for preferred symbols, not statistically validated |
| CONSENSUS_THRESHOLD = 2 (was 3) | Lowered because 3 produced zero picks. May allow weak consensus. |
| FreshPicks gates nearly disabled for testing | Confidence ≥ 0.30, WR ≥ 0.01, rate cap 999/hr |

---

## Dashboards & Links

| Dashboard | URL | What It Shows |
|-----------|-----|--------------|
| **Cross-System Monitor** | [eltonaguiar.github.io/.../monitor/](https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/monitor/) | Consensus picks, leaderboard, system status |
| **Alpha Engine** | [eltonaguiar.github.io/.../alpha/](https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/alpha/) | 100 strategies, elite grades, active picks |
| **ML Gainer** | [findtorontoevents.ca/.../antigravity-ml-gainer.html](https://findtorontoevents.ca/updates/antigravity-ml-gainer.html) | ML predictions, scorecard, alpha picks |
| **Audit Dashboard** | [findtorontoevents.ca/audit/](https://findtorontoevents.ca/audit/) | Strategy health, pick grading, conflicts |
| **KIMI Dashboard** | [findtorontoevents.ca/riseoftheclaw.html](https://findtorontoevents.ca/riseoftheclaw.html) | 81 algorithms, tournament, live picks |
