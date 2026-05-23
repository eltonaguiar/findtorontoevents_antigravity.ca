# Peer Coordination Status — Updated 2026-03-24 03:15 UTC

## Session Summary (Claude Opus — this session)

### Completed This Session

#### P0 Bug Fixes (4 critical bugs found by deep code audit)
1. `hash(strat) % 100` → `sum(ord(c)) % 100` — Python hash() non-deterministic across sessions
2. `regime_position_sizer.py` writes to `regime_position_sizing.json` (was overwriting regime_report.json, destroying hysteresis)
3. `smart_picks_engine.py` reads `hmm_regime_state.json` (was reading non-existent `hmm_regime.json`)
4. `MAX_STOP_DISTANCE_PCT` 0.02 → 0.12 — was silently capping ALL stops to 2% (crypto noise zone)

#### P1 Scoring Fixes
- R:R < 1.2 blocked in smart_picks_engine (6/11 picks had bad R:R)
- Live TP/SL hit check added (prevents resolved picks appearing as "winning")
- Confluence: 2-3 agree = +2 bonus (was -2 penalty on best WR bucket 42%)
- Volume spike penalty: -20 → -8 (was 4:1 disproportionate)

#### New Strategies Deployed
- `tsmom_strategy.py` — Vol-scaled time-series momentum (Sharpe 1.12-2.17 academic)
- `bbkc_squeeze_strategy.py` — BB-KC volatility expansion breakout
- `cbc_flip.py` — MapleStax CBC Flip (VWAP + EMA + state machine)
- `funding_rate_arb.py` — Funding rate directional signals
- `btc_breakout_strategy.py` — BTC AutoTrader clone (78% WR MQL5)
- `short_dominant_engine.py` — SHORT-biased pick engine
- `rocket_scanner.py` + `rocket_scanner_v2.py` — High-conviction picks

#### Analysis & Research Tools
- `mtf_gate.py` — Multi-timeframe confirmation gate (1H/4H/1D)
- `regime_ensemble.py` — Regime-adaptive signal weighting
- `regime_flip_detector.py` — Momentum-confirmed (RSI + ADX + SMA slope)
- `strategy_killer.py` — 391 strategies killed, 7 PROVEN
- `top_trader_analyzer.py` — Golden filter: top 5 traders + score>=70 = 75.4% WR
- `winner_predictor.py` — Feature analysis, strategy_fwd_wr = #1 predictor
- `feedback_loop.py` — Online logistic regression win predictor
- `contrarian_consensus.py` — Inverse signal when 3+ strategies herd
- `online_scorer.py` — SGD logistic regression on closed picks
- `check_active_picks.py` — Recurring quality analysis
- `smart_picks_performance.py` — Performance tracker with backtest filters
- `ab_test_portfolios.py` — 8 A/B test portfolios
- `clone_ab_tester.py` — 12 clone variation portfolios
- `gap_analysis.py` — WR by hour/direction/system
- `risk_metrics.py` — VaR/ES/Gini/Sortino/Calmar
- `top_gainer_capture.py` — Recall@Top-5%: 21.2%
- `tp_sl_optimizer.py` — Data-driven TP/SL from 2,481 trades

#### 8 Deep Code Audits (verified ALL external AI feedback)
See `docs/AI_FEEDBACK_RAW.md` for full synthesis of 6 AI reviewers.

---

## VERIFIED DATA (use these, not external claims)

### What the Data Actually Shows

| Metric | Actual Value | Kimi/External Claim | Verdict |
|---|---|---|---|
| R:R 2.0-2.5 WR | **26.0%** | 73.7% | FALSE (inverted) |
| Confidence 0.60-0.70 WR | **28.3%** | 61% | FALSE |
| Confidence 0.75-0.80 WR | **79.2%** | N/A | BEST bucket |
| Asia session WR | **31.1%** | 74% | FALSE |
| Late NY (21-24 UTC) WR | **50.9%** | N/A | BEST session |
| LONG overall WR | **39.2%** | 0% | Session bias, not reality |
| SHORT overall WR | **31.8%** | Higher | LONGs actually better historically |
| Consensus 2-3 agree | **42.0% WR** | Anti-predictive | BEST agreement bucket |
| Consensus 4-7 agree | **34.8% WR** | N/A | Herding zone |
| FETUSDT % of total PnL | **153.1%** | ~150% | Confirmed |
| Score-PnL correlation | Spearman **0.423** | r=0.05 | Better than claimed |
| Forward validated picks WR | **71.4%** | N/A | Strong predictor |

### Golden Filter (HIGHEST PRIORITY)
- **Top 5 traders + score >= 70 = 75.4% WR on 69 picks**
- Top 5: whale_20.7M, NMTD_25M, whale_123M_87roi, whale_58M_287roi, lb_NMTD
- Direct copies: 55.2% WR vs clones: 35.3% WR — copy, don't clone

### LONG Entry Rules (verified)
- ALLOW when: confidence >= 0.75 (55% WR, 307 trades)
- ALLOW when: score >= 65 (73.1% WR, 26 trades)
- BLOCK when: technical verdict SELL (23.8% WR, 248 trades)
- BLOCK when: score < 30 (30.3% WR)
- BLOCK symbols: ZEC, TRX, OP, ATOM (< 20% WR)
- Best hours: 04-12 UTC (46-50% WR)

### Asset Class Performance
- CRYPTO: PF 1.26, +3,818% PnL — ONLY profitable class
- FOREX: PF 0.53, -18% — losing
- EQUITY: PF 0.63, -617% — hemorrhaging

---

## TASK ASSIGNMENTS FOR PEERS

### Priority 1: Crypto Alpha (everyone)
- Focus 100% on crypto until consistently profitable
- Use the Golden Filter (top 5 traders + score>=70)
- Wire MTF gate as mandatory (alpha_engine/mtf_gate.py)
- Implement 2-of-3 ensemble confirmation

### Priority 2: Scoring Fixes (peer wiring indicators)
- Merge Forward WR + Track Record into one 30pt component
- Remove copy trader pattern matching from Proven Strategy Bonus (lines 1136-1155)
- Reduce Position Performance from 0-10 to 0-3 pts
- Fix double age penalty (pick one location)
- Delete: Session Bonus, Hindsight Winner, Monte Carlo (dead code)

### Priority 3: Clone Improvement
- Clone A/B tester running (12 variations)
- Key finding: clones fail due to timing lag + context loss
- Fix: only clone swing traders (hold > 4h), add ATR TP/SL

### Priority 4: New Whale Traders
- 11 untracked whales identified (93.8%, 88.3%, 87.7% WR)
- Add to hyperliquid_scraper.py SEED_WALLETS
- See alpha_engine/data/expanded_trader_rankings.json

### DO NOT IMPLEMENT (verified harmful)
- Kimi's confidence inversion (Fix 3)
- Kimi's R:R 2.0-2.5 as "sweet spot"
- Kimi's Asia session bonus
- Any non-crypto strategies (all losing)

---

## CRITICAL RULES
- Edit `template.html` NOT `index.html` for dashboard
- Never run dashboard generators locally
- `git stash && git pull --rebase origin main && git stash pop` before push
- API failover: 3+ sources always (Binance mirrors → CoinGecko → KuCoin → CryptoCompare)
