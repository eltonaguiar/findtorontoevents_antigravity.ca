# Pick Caps & Throttling Documentation
**Last updated:** 2026-03-13 by Claude (Opus)
**Audit method:** 2 parallel agents searched all Python, YAML, and config files

---

## ⚠️ TESTING SPRINT ACTIVE (2026-03-13)

**ALL pick caps across ALL systems have been set to 999 (effectively unlimited).**

Purpose: Run all systems uncapped for a few days to collect unfiltered pick data, then identify which systems produce quality picks vs. garbage. Every changed variable is tagged with `# TESTING SPRINT: was X, uncapped` in the code.

**To revert:** Search codebase for `TESTING SPRINT` and restore original values listed in the comments.

### Systems Uncapped:
| System | File | Variable | Was | Now |
|--------|------|----------|-----|-----|
| Sentinel | sentinel_hardened_integrator.py | max_signals_per_day | 2 | 999 |
| KIMI | alpha_engine_v2.py | MAX_PICKS | 8 | 999 |
| Mercury2 | config.py, scanner.py, mercury2_fast.py | MAX_CONCURRENT_PICKS, degraded_max, MAX_ACTIVE | 5/3/10 | 999 |
| Breakout Arena C | scanner.py | MAX_CONCURRENT | 2 | 999 |
| Cross-Agg | aggregator.py | MAX_DAILY/CRYPTO_LONGS/SHORTS/FOREX/PLAYBOOK/BETA | 10/4/2/3/5/3 | 999 |
| Cross-Agg | conviction_picks.py | MAX_PICKS_PER_RUN, MAX_CRYPTO_SAME_DIR | 3/2 | 999 |
| Cross-Agg | fc_crypto_pro.py | MAX_CRYPTO_SAME_DIR | 2 | 999 |
| Freshpicks Gate | freshpicks_gate.py | CONFIDENCE_FLOOR, STRATEGY_WR_FLOOR, RATE_CAP | 0.65/0.48/8 | 0.30/0.01/999 |
| ML Crypto Predictor | config.py, live_picks_tracker.py | max_concurrent, MAX_PER_DIRECTION, MAX_CONSECUTIVE_LOSSES | 3/3/4 | 999 |
| Crypto ML Edge | config.py, quick_scanner.py | MAX_CONCURRENT_PICKS | 5/10 | 999 |
| Coinglass | config.py | MAX_CONCURRENT_POSITIONS | 5 | 999 |
| ML Battleground | risk_manager.py, scanner.py | MAX_CONCURRENT, MAX_ACTIVE_PER_APPROACH | 8/3 | 999 |
| Genome | picks_generator.py, promoter.py, paper_trading_system.py | MAX_TOTAL_PICKS, MAX_LIVE_PICKS, max_positions | 10/20/5 | 999 |
| Signal Aggregator | picks_router.py | MAX_OPEN_POSITIONS, thresholds | 30/0.80/0.62 | 999/0.50/0.30 |
| Quan Engine | config.py | MAX_CONCURRENT_PER_MODE, MAX_CONCURRENT_TOTAL | 3/6 | 999 |
| Trading | position_manager.py | MAX_CONCURRENT_POSITIONS, MAX_CORRELATED | 5/2 | 999 |
| Claude Gainer ML | live_scanner.py | regime max_picks (all 5 regimes) | 2-8 | 999 |
| Alpha Engine | config.py | MAX_OPEN_PICKS | 45 | 999 |

---

## How This Works

Pick generation is throttled at **multiple layers** across multiple systems. A signal can be blocked at any layer:

```
Strategy generates signal
  → Auto-tuner: is strategy disabled? (39 hard-disabled, 12 direction-restricted)
  → ML filter: ml_score >= 0.50?
  → Confluence: pipeline_score >= 50?
  → R:R gate: risk:reward >= 1.5?
  → Direction gate: ALPHA_LONG_ENABLED? (now dynamic, was hardcoded off)
  → Per-strategy cap: < 3 active picks for this strategy?
  → Per-symbol dedup: not already open on this symbol+strategy?
  → Overall cap: < MAX_OPEN_PICKS? (now 999 = disabled)
  → Exposure caps: < 80% total, < 40% correlated?
  → Circuit breaker: system not halted?
  → Freshpicks gate: confidence >= 0.65? WR >= 0.48? R:R >= 1.0?
  → Rate limiter: < 8 picks per 60min window?
  → Signal freshness: < 15-45 min old?
```

---

## ALPHA ENGINE (`alpha_engine/`)

### Pick Limits (`config.py`)
| Variable | Value | What It Limits | Risk |
|----------|-------|----------------|------|
| `MAX_OPEN_PICKS` | **999** (disabled) | Overall concurrent picks | None (intentionally disabled) |
| `MAX_PICKS_PER_STRATEGY` | **3** | Picks per strategy name | Low — prevents domination |
| `MAX_PICKS_PER_SYMBOL` | **3** | Positions on same symbol | Low |
| `MAX_SAME_DIRECTION_CRYPTO` | **6** | Concurrent crypto longs OR shorts | **Medium** — can block longs if 6 already open |
| `MAX_TOTAL_EXPOSURE` | **0.80** | 80% of capital deployed | Medium |
| `MAX_CORRELATED_EXPOSURE` | **0.40** | 40% in same asset class | Medium |

### Direction Gate (`forward_validator.py:860`)
- Was `ALPHA_LONG_ENABLED = False` (blocked ALL longs)
- Now **dynamic**: allows longs if WR >= 40% across 10+ trades

### R:R Gate (`forward_validator.py:856`)
- Rejects picks with risk:reward < 1.5
- Double-enforced in both `scanner.py` and `forward_validator.py`

### Auto-Tuner Kill Lists (`auto_tuner.py`)
| Mechanism | Count | Impact |
|-----------|-------|--------|
| `HARD_DISABLED_STRATEGIES` | **39** | Permanently disabled — many after only 1-2 trades |
| `DIRECTION_RESTRICTED_STRATEGIES` | **12** | Forced SELL-only or BUY-only (halves signal output) |
| Stabilization `disabled_strategies.json` | **36 disabled + 36 graveyard** | Another layer of disabling |
| Runtime auto-disable | Dynamic | 7-day cooldown after auto-disable |

**WARNING:** 39 strategies permanently killed after 1-2 trades is statistically insufficient. Many could recover.

### Circuit Breakers (`auto_tuner.py:636-642`)
| Trigger | Threshold | Action |
|---------|-----------|--------|
| Consecutive losing weeks | 3 | Halts ALL trading 24h |
| System drawdown | -15% | Halts ALL trading |
| System win rate | < 40% (last 50 trades) | Halts ALL trading |
| Single strategy loss | > $500 | Auto-disables that strategy |

### Confluence Pipeline (`confluence_pipeline.py:377`)
- `min_score = 50.0` — pipeline score must be >= 50/100
- Counter-regime penalty: -0.30 (can easily push below threshold)

### ML Filter (`scanner.py`)
- `MIN_ML_SCORE = 0.50` — signals below 0.50 rejected
- Strategies with <= 10% WR after 4+ trades: suppressed

### Exposure Caps (`portfolio_manager.py`)
| Mode | Max Positions | Max Per Symbol | Max Same Direction |
|------|---------------|----------------|-------------------|
| Conservative | 10 | 1 | 4 |
| Moderate | 20 | 2 | 6 |
| Aggressive | 30 | 3 | 8 |

---

## KIMI RISE OF THE CLAW (`KIMI_RISEOFTHECLAW/`)

| Variable | Value | File | Impact |
|----------|-------|------|--------|
| `MAX_PICKS_PER_ALGO` | **3** | `live_scanner.py:167` | Max 3 picks per algorithm (81 algos) |
| `MAX_PICKS` | **8** | `alpha_engine_v2.py:78` | **SEVERE** — despite 81 algos, only 8 total picks output |

---

## MERCURY2 (`mercury2/`)

| Variable | Value | File | Impact |
|----------|-------|------|--------|
| `MAX_CONCURRENT_PICKS` | **5** | `config.py:34` | **Tight** — reduced from 10 |
| `MAX_ACTIVE` | **10** | `mercury2_fast.py:43` | Fast scanner override |
| `degraded_max_picks` | **3** | `scanner.py:175` | Drops to 3 in degraded mode |

---

## CRYPTO ML EDGE (`crypto_ml_edge/`)

| Variable | Value | File | Impact |
|----------|-------|------|--------|
| `MAX_CONCURRENT_PICKS` | **5** | `config.py:118` | **Tight** — completely blocks new picks when full |
| `MAX_CONCURRENT_PICKS` | **10** | `quick_scanner.py:39` | Quick scanner override |

Prints "All N slots occupied. No new picks this cycle." when full.

---

## CROSS AGGREGATION (`cross_aggregation/`)

### Aggregator (`aggregator.py`)
| Variable | Value | Impact |
|----------|-------|--------|
| `MAX_DAILY_PICKS` | **10** | Hard daily cap |
| `MAX_CRYPTO_LONGS` | **4** | **Tight** for crypto-heavy portfolio |
| `MAX_CRYPTO_SHORTS` | **2** | **Very tight** |
| `MAX_FOREX_PICKS` | **3** | Tight |
| `MAX_PER_SYMBOL` | **1** | Reasonable (dedup) |
| `PLAYBOOK_MAX_POSITIONS` | **5** | Tight |
| `MAX_HIGH_BETA_LONGS` | **3** | Moderate |
| `MAX_SIGNAL_AGE_MIN` | **45 min** | Discards stale signals |

### Conviction Picks (`conviction_picks.py`)
| Variable | Value | Impact |
|----------|-------|--------|
| `MAX_PICKS_PER_RUN` | **3** | Only 3 conviction picks per run |
| `MAX_CRYPTO_SAME_DIR` | **2** | **Very tight** |
| `DEDUP_COOLDOWN_HOURS` | **4** | Same symbol+direction blocked 4h |

### Freshpicks Gate (`freshpicks_gate.py`)
| Variable | Value | Impact |
|----------|-------|--------|
| `CONFIDENCE_FLOOR` | **0.65** | High bar — filters many valid signals |
| `STRATEGY_WR_FLOOR` | **0.48** | Strategies below 48% WR blocked (after 5+ trades) |
| `RR_FLOOR` | **1.0** | R:R must be >= 1.0 |
| `RATE_CAP` | **8** | Max 8 picks per 60-min window |
| `DEDUP_COOLDOWN_MIN` | **30** | 30-min cooldown per symbol+direction |
| `BANNED_STRATEGIES` | **8** | 8 strategies permanently banned |

---

## CLAUDE GAINER ML (`claude_gainer_ml/`)

| Condition | Max Picks | Impact |
|-----------|-----------|--------|
| Extreme Fear (F&G < 10) | **8** | Most generous |
| Fear (F&G 10-25) | **6** | Normal |
| Neutral (F&G 25-55) | **5** | Normal |
| Greed (F&G 55-75) | **3** | Restrictive |
| Extreme Greed (F&G > 75) | **2** | **Very restrictive** |

---

## ML CRYPTO PREDICTOR (`ml_crypto_predictor/`)

| Variable | Value | File | Impact |
|----------|-------|------|--------|
| `max_concurrent` | **3** | `config.py:308` | **Very tight** |
| `MAX_PER_DIRECTION` | **3** | `live_picks_tracker.py:131` | Per direction |
| `MAX_CONSECUTIVE_LOSSES` | **4** | `live_picks_tracker.py:133` | **Circuit breaker** — pauses ALL new picks |
| `MAX_PER_SYMBOL` | **1** | `live_picks_tracker.py:140` | One pick per coin |

---

## ML BATTLEGROUND (`ml_battleground/`)

| Variable | Value | File | Impact |
|----------|-------|------|--------|
| `MAX_CONCURRENT` | **8** | `shared/risk_manager.py:16` | Moderate |
| `DRAWDOWN_HALT_PCT` | **0.40** | `shared/risk_manager.py:19` | Halts at 40% DD |
| `MAX_ACTIVE_PER_APPROACH` | **3** | `abc_forward_test/scanner.py:37` | Only 9 total (3×3) |

---

## COINGLASS (`coinglass_strategies/`)

| Variable | Value | File | Impact |
|----------|-------|------|--------|
| `MAX_CONCURRENT_POSITIONS` | **5** | `config.py:41` | **Tight** |

---

## BREAKOUT ARENA (`breakout_arena/`)

| Variable | Value | File | Impact |
|----------|-------|------|--------|
| `MAX_CONCURRENT` | **2** | `approach_c_spike_reverse/scanner.py:50` | **Very tight** |
| `MAX_DRAWDOWN` | **0.20** | Same file:51 | 20% DD circuit breaker |

---

## GENOME (`genome/`)

| Variable | Value | File | Impact |
|----------|-------|------|--------|
| `MAX_PICKS_PER_SYMBOL` | **2** | `picks_generator.py:75` | Moderate |
| `MAX_TOTAL_PICKS` | **10** | `picks_generator.py:76` | Moderate |
| `max_positions` | **5** | `paper_trading_system.py:284` | Tight |
| `MAX_LIVE_PICKS` | **20** | `mutation_lab/promoter.py:32` | Moderate |

---

## SIGNAL AGGREGATOR (`signal_aggregator/`)

### Picks Router (`picks_router.py`)
| Variable | Value | Impact |
|----------|-------|--------|
| `MASTER_PICKS_THRESHOLD` | **0.80** | Only 80%+ confidence reaches master channel |
| `FRESHPICKS_THRESHOLD` | **0.62** | Below 62% = nowhere |
| `SIGNAL_FRESHNESS_MAX_SECONDS` | **900** (15 min) | Stale signals rejected |

### Circuit Breaker Levels
| Level | Master Picks | Fresh Picks | Impact |
|-------|-------------|-------------|--------|
| GREEN | 5 | 10 | Normal |
| YELLOW | 2 | 5 | 50% reduction |
| RED/HALT | **0** | **0** | **Total shutdown** |

---

## SENTINEL HARDENED INTEGRATOR

| Variable | Value | Impact |
|----------|-------|--------|
| `max_signals_per_day` | **2** | **MOST RESTRICTIVE CAP IN ENTIRE CODEBASE** |

---

## OTHER SYSTEMS

| System | Variable | Value | Impact |
|--------|----------|-------|--------|
| STOCKS Competition | `MAX_ACTIVE_PICKS` | **8** | Moderate |
| Paper Trading | `MAX_POSITIONS_PER_PORTFOLIO` | **10** | Moderate |
| Trading | `MAX_CONCURRENT_POSITIONS` | **5** | Tight |
| Trading | `MAX_CORRELATED_POSITIONS` | **2** | Tight |
| Quan Engine | `MAX_CONCURRENT_TOTAL` | **6** | Moderate |
| Quan Engine | `MAX_CONCURRENT_PER_MODE` | **3** | Tight |
| Asterdex Paper | `MAX_OPEN_POSITIONS` | **30** | Generous |

---

## TOP STARVATION RISKS (Ranked)

1. **Sentinel Hardened Integrator** — `max_signals_per_day = 2` — by far the worst
2. **39 HARD_DISABLED strategies** in Alpha Engine — many killed after 1-2 trades
3. **KIMI alpha_engine_v2** — `MAX_PICKS = 8` despite 81 algorithms
4. **Breakout Arena C** — `MAX_CONCURRENT = 2`
5. **Cross-Agg crypto shorts** — `MAX_CRYPTO_SHORTS = 2`
6. **ML Crypto Predictor** — `max_concurrent = 3` + circuit breaker after 4 losses
7. **Mercury2** — `MAX_CONCURRENT_PICKS = 5` (halved from 10)
8. **Crypto ML Edge** — `MAX_CONCURRENT_PICKS = 5` (blocks entirely when full)
9. **Claude Gainer in greed** — drops to 2 picks during extreme greed
10. **Freshpicks gate** — `CONFIDENCE_FLOOR = 0.65` is a high bar
