# Peer Handoff — Session arlbhmd9 (March 19-24, 2026)

## What I Built (Complete List)

### Quality Gates & Filters
- Confidence >= 0.70 hard gate (production_scanner.py Gate 1)
- ML score >= 0.50 gate (Gate 2)
- Forex data-driven gate (Gate 3 — blocks if WR < 30% on 10+ trades)
- Smart short validator (Gate 4 — proven/toxic/unproven tiers)
- Volume ratio > 5.0 gate (Gate 5)
- Unvalidated strategy gate (Gate 6)
- BTC gate (Gate 7 — needs conf>=0.85 AND ml>=0.70)
- Portfolio cap at MAX_ACTIVE_PICKS=20 (Gate 8)
- PnL format normalization (decimal, not percentage)
- Confidence format normalization (0-1, not 0-100)
- Bad symbol filter (kPEPE, stablecoins, digit-prefix)
- Stale pick cleanup (>48h with no price update)
- TP cap (12% crypto, 1% forex)

### New Strategies (36+)
- beta_adjusted_residual_momentum (Liu & Tsyvinski, Sharpe 1.8)
- cross_sectional_reversal (anti-momentum hedge, corr -0.6)
- stablecoin_flow_momentum (DefiLlama, 3-7 day lead)
- disposition_effect_contrarian (behavioral finance)
- token_unlock_event_short (Keyrock data, 90% negative)
- btc_power_law_deviation (Santostasi 2024)
- nvm_metcalfe_valuation (Ante 2024)
- eth_gas_fee_reversal (Cong et al 2023)
- okx_top_trader_consensus (free public API)
- binance_crowd_contrarian (L/S ratio extremes)
- cme_cot_positioning (top trader L/S proxy)
- weekly_oi_change_momentum
- miner_capitulation_recovery (hash ribbon)
- 8 symbol-specific variants (SOL, ETH, BTC, DOGE, XRP, midcap)
- grid_range_scalper (sideways market, 75-85% WR)
- squeeze_range_fade (BB inside KC, 70-80% WR)
- intraday_seasonality (21-23 UTC, 60% WR)
- Heikin Ashi trend filter (global confidence adjuster)
- vpin_momentum_after_flow (microstructure)
- cointegration_halflife_exit (pairs trading)
- sweep_breakout_scaler (liquidity sweep + FVG)
- gainer_auto_promote (Binance top gainers pipeline)
- contrarian_consensus_flip (fade low-quality agreement)

### ML Fixes
- Removed 4 leaky features (Phase 11)
- Removed 7 dead regime features (Phase 12)
- Added purged time-series CV with 2% embargo
- Added CatBoost with has_time=True ordered boosting
- Fixed strategy_encoded (hash-based, not label encoder)
- Deleted stale Boruta cache
- Raised META_LABEL_PROBABILITY_GATE 0.50 -> 0.55
- Added Mercury2 RSI overbought guard (RSI >= 70 blocks)
- Fixed feature pipeline (expanded fallback chains for FnG, funding, OBI)
- Killed 0% WR strategies (BTCUSDT_15m_D, ADAUSDT_15m_D)

### Self-Improvement Systems
- Missed Opportunity Analyzer (hourly, expands universe)
- Adaptive Trust Tuner (12h, adjusts confidence per strategy)
- Forward-Test Tracker (6h, monitors 13 research strategies)
- Optimal Entry Condition Finder (permutation search)
- Indicator Correlation Tracker (14 indicators, hourly)
- Precision/Recall Calculator (12h)
- Pick Quality Monitor (hourly with live prices)

### Copy Trader Intelligence
- 1,325+ trader database across 15+ platforms
- 11 working scrapers (853 profiles, 324 picks per cycle)
- HFT filter, per-symbol confidence, conflict resolution, stale rejection
- Copy trader confidence deflated from 0.95 to 0.70
- Post-merge conflict resolver
- Databases: Bitget (350), Forex (311), OKX (294), DEX (191), Hyperliquid (89), BingX/Gate/MEXC (37), Bybit (14), aggregators (20)

### Scoring Fixes
- Elite scorer: copy trader deflation, SELL penalty, volume spike penalty, ranging boost
- Disabled: session bonus, Monte Carlo, meta label, hindsight winner, skyrocket potential
- Confluence flipped to contrarian (agreement = penalty)
- SmartPicks: removed currently_winning, added htf_alignment, rebalanced weights
- Strategy tiers (ELITE/PROVEN/EXPERIMENTAL) with position multipliers
- Auto-kill list (4 strategies: volume_spike_backfill, winner_pattern_precursor, momentum_catcher, hl_funding_fade)

### Infrastructure
- Fast regime detector (5-min cache, Binance+Bybit+CoinGecko)
- Kelly position sizer (half-Kelly, vol-scaled, correlation-adjusted)
- Direction gate lowered 40% -> 30%
- Forex tuner_state cleared (11 strategies re-enabled)
- 10 workflows upgraded with exponential backoff
- safe_commit_push.sh shared retry script

### Data Sources Wired to Production
- CoinMetrics (MVRV, NVT, active addresses)
- Mempool.space (fee rates, congestion)
- Market modifiers (BTC dominance, treasury, supply)
- Missed opportunity universe expansion
- HTF confirmation filter (daily EMA/RSI/BB/MACD)

## Known Issues (For Other Peers)
1. ML model currently NOT on disk — awaiting retrain (model_comparison.json says force_retrain)
2. 25 of 32 ML features still dead (feature pipeline partially fixed)
3. 13 new research strategies have zero closed trades (need time to accumulate)
4. Binance fapi returns 451 (geo-blocked) from GitHub Actions — Bybit fallback added
5. active_picks.json occasionally gets merge conflicts from concurrent workflows

## Future Plans / What Needs Doing
1. Wire indicator predictions into scoring (agent running now)
2. Polymarket API integration (free, 5,406 active crypto markets)
3. Myfxbook community outlook as contrarian forex signal
4. Full ML retrain with populated features (need 5,000+ samples)
5. Walk-forward validation (train months 1-6, test month 7, repeat)
6. SHAP-based feature importance monitoring
7. Separate ML models per regime (bull/bear/sideways)
8. Max 20 active picks enforcement (deployed but needs validation)
