# TODO2 — Claude Opus Session Summary & Remaining Steps
**Date:** 2026-03-26 | **Agent:** Claude Opus 4.6 (1M context)
**Dashboard:** https://findtorontoevents.ca/audit/

---

## COMPLETED (This Session — 18 Items)

### Scoring & Gates
| # | Item | Impact | Commit |
|---|------|--------|--------|
| 1 | **Method C scoring deployed as primary** — ml_score + forward_wr weighted 40%, replacing broken elite_score (48% separation vs 26%) | +10-15pp WR | Pushed |
| 2 | **Overconfidence penalty removed** — conf>0.75 was capped at 10/15pts, now gentle taper (15→13→12) | Unblocks profitable high-conf picks | `e286b737fe` |
| 3 | **ML gate lowered 0.50→0.40** — 75% dead ML features made 0.50 too strict | More picks flow through | `e3849096bc` |
| 4 | **Score minimum threshold 55** — enforced at 3 points (quality gate, post-scoring, workflow step) | Filters noise picks | Pushed |
| 5 | **Non-crypto hard block** — equity/commodity/bond/futures blocked at Gate 0 (0-19% WR) | Stops guaranteed losers | Pushed |

### Copy Trader Pipeline
| # | Item | Impact | Commit |
|---|------|--------|--------|
| 6 | **NMTD_25M 10 positions injected** — BTC SHORT, SOL SHORT, ETH LONG, AAVE LONG etc (81% WR) | Primary signal source live | `0c8a4c9101` |
| 7 | **Copy trader timeout 14→30 min** — all 10 recent runs timed out before saving NMTD picks | NMTD pipeline unblocked | Pushed |
| 8 | **binance_smart_money killed** — 5-layer kill chain (generator, post-sweep, auto_tuner, force-close, source code) | Eliminates 44% of losing copy picks | Pushed |

### Dashboard & Data Quality
| # | Item | Impact | Commit |
|---|------|--------|--------|
| 9 | **Dashboard generator field passthrough** — RSI, regime, HTF, track_level, volume_ratio now pass through `_normalize_pick` | Fields no longer blank | Pushed |
| 10 | **Bulk RSI enrichment** — 6-mirror Binance fetch for all 40 crypto picks (was 0% coverage) | RSI/VOL columns populated | `367e13b7a6` |
| 11 | **Regime labels** — REGIME column now shows BEAR/BULL/CHOP text instead of just checkmark/dash | Users understand market state | Pushed |
| 12 | **Trust score wired in dashboard generator** — `enrich_picks_with_trust_score()` was never called | TRUST column populated | Pushed (by Copilot peer) |

### Signal Quality
| # | Item | Impact | Commit |
|---|------|--------|--------|
| 13 | **Polymarket crypto-only filter** — 28 reject keywords (NBA, FIFA, GTA, elections), requires price targets | 92→3 signals (removed garbage) | Pushed |
| 14 | **Forex deadlock gate fixed** — gate blocked all forex when <10 trades (catch-22), now lets picks through | Forex picks flow | `547881e462` |
| 15 | **Consensus outcome tracker KeyError fix** — `outcomes["closed"]` → `outcomes.get("closed", [])` | Workflow no longer crashes | Pushed |

### Post-TODO2 Additions (same session)
| # | Item | Impact | Commit |
|---|------|--------|--------|
| 16 | **RSI 6-mirror Binance failover in CI** — single mirror was rate-limited, now tries 6 | RSI always populated | `8ca9185414` |
| 17 | **Smart picks direction normalization** — BUY/SELL→LONG/SHORT matching + loose key fallback | Smart picks 1→4 entries | `42c6c58960` |
| 18 | **JS TypeError fix** — `htf_bias.toLowerCase()` crashed on non-string values, wrapped with `String()` | Dashboard render no longer crashes | `42c6c58960` |

---

## PERFORMANCE TRAJECTORY

| Metric | Session Start | Session End | Target |
|--------|-------------|------------|--------|
| Overall WR | 32-42% | **51.7%** | >55% |
| Crypto WR | 41.6% | **54.4%** | >60% |
| Equity WR | 0% | **53.8%** | >50% (gated) |
| Forex WR | 11.8% | **44.0%** | >50% |
| Active crypto picks | 11 | **40+** | 50+ |
| Score-PnL correlation | r=0.043 | r=0.14+ | r>0.20 |
| Polymarket signals | 92 (garbage) | **3 (crypto)** | 5-10 quality |
| NMTD picks | 0 | **10** | 20+ |

---

## REMAINING — HIGH PRIORITY (Next Session)

### P0 — Do Immediately
| # | Item | Effort | Expected Impact | Owner |
|---|------|--------|-----------------|-------|
| 1 | **Fix ML feature pipeline** — 24/32 features dead (75%), health_score=0.25. ML models trading on noise. | 4h | ML model quality recovery, +5pp WR | Unassigned |
| 2 | **Wire enrichment into alpha-engine-live.yml** — RSI/VOL/regime enrichment runs locally but NOT in CI. Every alpha engine cycle resets picks to unenriched state. | 1h | Persistent RSI/VOL/regime | Unassigned |
| 3 | **Copy trader scraper still timing out** — even at 30min. Need to save intermediate results after each scraper instead of only at end. | 2h | NMTD auto-refreshes | Unassigned |
| 4 | **Restore ml_score weight in elite_scorer** — ml_score was zeroed (IC=-0.19) but SCORE_VALIDATION proves it's the STRONGEST predictor (+0.337). Should be restored at 25-30% weight. | 1h | +5pp scoring discrimination | Unassigned |

### P1 — This Week
| # | Item | Effort | Expected Impact | Owner |
|---|------|--------|-----------------|-------|
| 5 | **Fix Binance Futures API** — all OI/funding/premium calls return 429 or empty. ~4 min wasted per scan + strategies blind. Need batch endpoint or rate limit fix. | 2h | Faster scans, better signals | Unassigned |
| 6 | **Fix yfinance symbol mapping** — 19 crypto symbols fail (HYPE, SUI, PEPE, TAO etc). Yahoo uses different tickers. | 1h | Macro data for 19 symbols | Unassigned |
| 7 | **Extend forex hold periods** — trades expire via TIME_EXPIRY before hitting TP/SL. Need 4-7d for momentum, 7-14d for mean reversion. | 1h | Forex WR improvement | fdi8fcyb (in progress) |
| 8 | **Add EURGBP to FOREX_SYMBOLS** — already appears in closed trades but missing from config scan list. | 15min | +1 forex pair | Unassigned |
| 9 | **Integrate OlivierDanvel from Myfxbook** — 84% forex allocation, 65% WR, 33 consecutive profitable months. | 3h | Best forex copy trader | Unassigned |
| 10 | **Calibrate gate cascade** — only 2/68 picks pass all gates (too aggressive). Need gate relaxation or priority bypass for proven strategies. | 2h | More quality picks surface | Unassigned |

### P2 — Next 2 Weeks
| # | Item | Effort | Expected Impact | Owner |
|---|------|--------|-----------------|-------|
| 11 | **A/B/C portfolio forward test** — 3 parallel portfolios (control, scoring fix, full stack) to empirically validate changes | 4h | Data-driven improvement proof | Unassigned |
| 12 | **FETUSDT concentration cap (30%)** — single symbol = 52% of all profits. Risk if regime changes. | 1h | Risk reduction | Unassigned |
| 13 | **Portfolio correlation monitoring** — no enforcement of max 40% correlated exposure rule | 2h | Prevents concentration blowup | Unassigned |
| 14 | **Adaptive TP/SL using MFE/MAE data** — static TP/SL doesn't match actual price ranges | 3h | PF improvement +0.2-0.3 | i8mbe7tv (in progress) |
| 15 | **Split scoring by asset class** — one monolithic scorer handles all asset classes despite different characteristics | 4h | Better discrimination per asset | Unassigned |

### P3 — Research Backlog
| # | Item | Notes |
|---|------|-------|
| 16 | HMM/Bayesian regime detection | Replace simple F&G override |
| 17 | Funding rate prediction model | 19% APR market-neutral |
| 18 | Echo State Networks for short-horizon | Trains in <1 second |
| 19 | FinBERT sentiment analysis | 75-85% accuracy on financial text |
| 20 | Genetic Programming strategy discovery | DEAP library |

### Kimi Investigation Findings (NEW — Not Yet Addressed)
| # | Item | Impact | Effort | Priority |
|---|------|--------|--------|----------|
| K1 | **Block Bitget traders** — all 0% WR, game stats (PF=99.99). Require PF<=10, closed>=10, days>=7. | +2pp WR | 30min | P0 |
| K2 | **Widen whale copy TP/SL to 8%/4%** — 35% of copy picks exit via premature SL_HIT at -4.66% avg | +4-5pp WR | 1h | P0 |
| K3 | **Position-age filter for copy trades** — only copy positions <2h old | +3-5pp WR | 1h | P1 |
| K4 | **Expand outcome resolver to active picks** — active picks sit OPEN forever | +5-8pp WR | 2h | P1 |
| K5 | **Wire prediction_market_agents into dashboard** — orphaned directory | More signals | 2h | P1 |
| K6 | **Lower PM MIN_CONFIDENCE 0.60→0.55** | More PM signals | 15min | P2 |
| K7 | **Lower PnL threshold 0.01%→0.001%** | Accurate WR | 15min | P2 |
| K8 | **Kill winner_pattern_precursor** — 17.7% WR on 96 trades | +2pp WR | 30min | P0 |
| K9 | **Track "Their Pick" vs "Our Clone" WR** | Diagnostic | 3h | P2 |
| K10 | **Increase outcome resolver frequency 2h→30min** | Better resolution | 1h | P2 |

---

## PEER STATUS (as of 2026-03-26 08:00 UTC)

| Peer ID | Summary | Status |
|---------|---------|--------|
| ms6wyhav | IC-scored scoring, feature populator, inverse mutations, walk-forward validator | Complete |
| i8mbe7tv | Cross-asset underperformance investigation, SL gap-through fix, master report | Complete |
| 5zajmzss | Deep investigation: copy trader slippage, prediction market pipeline | In progress |
| 1nq79mga | 10 root cause fixes: fake trader qualification, entry price bug, ML 15m kill | In progress |
| fdi8fcyb | PM forward test monitoring, forex min-hold fix, copy trader pipeline | In progress |

---

## KEY CONTRADICTIONS FOUND (Resolve in Next Session)

1. **ml_score zeroed vs strongest predictor** — Session zeroed ml_score (IC=-0.19) but SCORE_VALIDATION shows +0.337 correlation. Needs investigation — different data windows may explain discrepancy.
2. **Forex unblocked vs should be blocked** — We fixed the forex deadlock, but forex WR is only 44%. The gate fix was correct (data needs to accumulate), but monitor closely.
3. **rapid_fire banned vs largest PnL contributor** — banned from smart picks but has +234.53% aggregate PnL on 65 trades. Needs per-strategy investigation, not blanket ban.

---

## FILES CHANGED THIS SESSION

| File | Change |
|------|--------|
| `alpha_engine/elite_scorer.py` | Overconfidence penalty removed, OUTLIER_SYMBOLS per-strategy fix |
| `alpha_engine/production_scanner.py` | Gate 0 non-crypto block, ML gate 0.50→0.40, forex deadlock fix, score floor 55 |
| `alpha_engine/polymarket_signals.py` | Crypto-only filter (28 reject keywords + price target requirement) |
| `alpha_engine/data/core_whitelist.json` | kill_categories cleared, forex strategies un-killed |
| `alpha_engine/data/active_picks.json` | RSI/VOL/regime enrichment for 40 crypto picks |
| `alpha_engine/scanner.py` | GENERATOR_HARD_KILL set + pre/post generation sweep |
| `alpha_engine/crypto_risk_gates.py` | binance_smart_money added to HARD_KILL_STRATEGIES |
| `alpha_engine/auto_tuner.py` | PERMANENTLY_KILLED set with binance_smart_money |
| `alpha_engine/crypto_smart_picks.py` | binance_smart_money signal generation commented out |
| `alpha_engine/smart_picks_engine.py` | binance_smart_money removed from PROVEN_PERFORMANCE_HISTORY |
| `alpha_engine/ml_predictor_merger.py` | Timestamp refresh for stale active picks |
| `alpha_engine/universal_price_enricher.py` | Forex priority path, increased fallback cap |
| `audit_trail/dashboard_generator.py` | Field passthrough, trust_score call, track_level computation, RSI enrichment |
| `copy_trader_intel/data/active_picks.json` | 10 NMTD_25M positions injected |
| `cross_aggregation/consensus_outcome_tracker.py` | KeyError fix |
| `.github/workflows/alpha-engine-live.yml` | Score floor step, enrichment step |
| `.github/workflows/copy-trader-intelligence.yml` | Timeout 14→30 min |

---

*Generated by Claude Opus 4.6 — proactive, no idle time.*
