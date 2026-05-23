# Design: System Enhancement + Social Media Prediction Competition
## Date: Feb 25, 2026
## Status: APPROVED

---

## Context

### Current State (Feb 25, 2026 13:43 UTC)
- **14 autonomous trading systems**, 22 GitHub Actions workflows
- **Mercury 2:** 8/8 wins closed, 100% WR, +28.66% total realized PnL (outstanding)
- **Alpha Engine:** Stocks/forex winning; crypto 41% WR (ICT/SMC strategies failing)
- **ML Battleground A/B:** -4.49% avg (PANIC_SELL shorts at market bottoms)
- **Breakout Arena C:** Stale/broken (no price updates since Feb 24)
- **Crypto ML Edge:** Too conservative (falling knife filter rejects all crypto in panic)
- **Claude Gainer ML:** No visibility (scanner never runs)
- **Market conditions:** F&G=11 (extreme fear), BTC dominance 56%

### External Review Consensus (Inception Labs + Grok + Perplexity)
All three independent AI reviewers converge on:
1. **Edge = regime filters + risk management, NOT ML predictions** (models are coin-flip)
2. **PANIC_SELL logic is catastrophic** — forces shorts at exact market bottoms
3. **Cross-system conflicts** — Mercury LONG vs Battleground SHORT on same assets
4. **ICT/SMC strategies need regime gating** — disable in extreme fear
5. **Feature poverty** — only price-derived TA; missing order-flow, funding term-structure
6. **Walk-forward validation needed** — current 80/20 split is unrealistic

### TJR Trades Analysis (ICT/SMC 70% vs Our 41%)
Deep investigation reveals our ICT/SMC implementations have 5 critical gaps vs TJR's methodology:
1. **No multi-timeframe bias** — we use daily only; TJR uses 4H bias + 15M entry
2. **No FVG retest confirmation** — we enter on first touch; TJR waits for retest + MSS
3. **Wrong R:R** — we use fixed 2 ATR TP (R:R ~1.4); TJR uses 1:3 with scale-out
4. **No setup quality filtering** — we take every signal; TJR filters to 1-2/week
5. **No Market Structure Shift validation** — we skip the confirmation step entirely

**Academic evidence:** FVGs hold as S/R zones ~60-66% of the time (Edgeful study). BOS/Order Blocks have zero peer-reviewed validation. TJR's 70% WR is **self-reported, unverified**.

---

## Phase 1: Fix Broken Systems (Quick Wins)

### 1A. ML Battleground A/B — Kill PANIC_SELL in Capitulation
**File:** `ml_battleground/shared/market_health.py` line 163
**Changes:**
- Raise confidence floor: `>= 0.50` → `>= 0.75`
- Switch `max(ml_score, strat_conf)` → `min()` (conservative estimate)
- Add capitulation gate: if F&G ≤ 15 AND 7d drawdown > 8% → block ALL shorts, allow LONGs only
- Keep originals running; launch A2/B2 alongside with enhanced logic

**Expected impact:** Stop losing -4.49% on shorts → neutral or slightly positive

### 1B. Breakout Arena C — Unfreeze Stale Picks
**File:** `breakout_arena/approach_c_spike_reverse/scanner.py`
**Changes:**
- Add `validate_picks()` call at end of main loop (imported but never called)
- Add live price fetching from Binance
- Set MAX_HOLD_HOURS=48 (currently infinite)
- Add HWM tracking like System A/B

**Expected impact:** Picks actually close; stale positions resolved

### 1C. Crypto ML Edge — Relax Falling Knife Filter
**File:** `crypto_ml_edge/quick_scanner.py` lines 44-45, 245-252
**Changes:**
- Make `MAX_BELOW_SMA_PCT` regime-adaptive:
  - Normal markets (F&G > 30): 20% (current)
  - Fear (F&G 15-30): 30%
  - Extreme fear (F&G < 15): 45% or disabled
- Disable retroactive sweep during panic regime

**Expected impact:** Capture bounces Mercury 2 is already profiting from

### 1D. Claude Gainer ML — Connect to Pipeline
**Changes:**
- Create `.github/workflows/claude-gainer-ml.yml` (run every 4h)
- Export picks to `claude_gainer_ml/data/active_picks.json`
- Add price validation loop

**Expected impact:** Visibility into a previously hidden system

### 1E. Alpha Engine ICT/SMC — Regime Gate + TJR-Style Improvements
**Files:** `alpha_engine/crypto_strategies.py`, `alpha_engine/community_strategies.py`
**Changes:**
- Hard gate: Disable all ICT/SMC strategies when F&G < 20
- Add multi-timeframe data fetching (4H + 15M alongside daily)
- Add MSS (Market Structure Shift) confirmation before FVG/BOS entries
- Add FVG quality filters (age > 5 bars, size > 0.5 ATR, no opposing FVG clutter)
- Scale-out TP: TP1=1 ATR (25%), TP2=2 ATR (25%), TP3=3.5 ATR (50%)
- Raise volume confirmation on BOS from 1.2x → 2.0x minimum

**Expected impact:** ICT/SMC WR from 41% → 55-60%

---

## Phase 2: Social Media Prediction Competition

### Architecture: Modular Pipeline with Crawl4AI

```
social_prediction_tracker/
├── scrapers/
│   ├── tradingview_scraper.py    # Crawl4AI — JS-rendered ideas pages
│   ├── reddit_scraper.py         # PRAW — r/BitcoinMarkets, r/CryptoMarkets, etc.
│   ├── twitter_scraper.py        # snscrape — crypto prediction accounts
│   ├── crypto_blog_scraper.py    # Crawl4AI — CoinDesk, CryptoQuant Quicktakes
│   └── youtube_scraper.py        # Crawl4AI — crypto channel titles/descriptions
├── extraction/
│   ├── prediction_extractor.py   # LLM/regex → structured predictions
│   └── schemas.py                # Pydantic models
├── validation/
│   ├── price_validator.py        # Check TP/SL/entry vs live Binance prices
│   └── predictor_scorer.py       # Win rate, avg P&L, Sharpe per predictor
├── data/
│   ├── predictions.db            # SQLite — all predictions + outcomes
│   ├── leaderboard.json          # Top predictors ranked
│   └── active_predictions.json   # Currently tracked predictions
├── dashboard/
│   └── index.html                # Leaderboard page (GitHub Pages)
└── requirements.txt              # crawl4ai, praw, snscrape, etc.
```

### Platform Coverage

| Platform | Scraper | Method | Frequency | Cost |
|----------|---------|--------|-----------|------|
| TradingView Ideas | Crawl4AI | JS render + LLM extraction | Every 2h | Free |
| Reddit | PRAW | Official API (OAuth) | Every 30min | Free |
| X/Twitter | snscrape | Public scraping (fragile) | Every 2h | Free |
| CoinDesk/CryptoQuant | Crawl4AI | Blog/Quicktake scraping | Every 4h | Free |
| YouTube | Crawl4AI | Title/description parsing | Every 6h | Free |
| Price Validator | Binance API | TP/SL/entry checking | Every 15min | Free |

### Subreddits Monitored
- r/BitcoinMarkets (700k, HIGH quality predictions)
- r/CryptoMarkets (400k, MEDIUM-HIGH)
- r/CryptoCurrency (7.5M, daily discussion predictions)
- r/ethtrader (400k, ETH-focused)
- r/binance (1M, exchange ecosystem)

### TradingView Scraping
- Symbol-specific: `tradingview.com/symbols/BTCUSD/ideas/`
- Use `tradingview-scraper` PyPI package for metadata
- Use Crawl4AI with LLM extraction for entry/TP/SL from free text
- Focus on top/popular ideas for our 12 key symbols

### X/Twitter Accounts to Track
@CryptoCred, @Pentoshi, @HsakaTrades, @CryptoCapo_, @SmartContracter, and accounts discovered via high engagement on our symbols

### Data Model (SQLite)

```sql
CREATE TABLE predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    predictor_id TEXT NOT NULL,        -- "tv:CryptoCapo" or "reddit:u/trader99"
    platform TEXT NOT NULL,            -- tradingview, reddit, twitter, blog, youtube
    symbol TEXT NOT NULL,              -- BTCUSDT, ETHUSDT, etc.
    direction TEXT NOT NULL,           -- LONG or SHORT
    entry_price REAL,
    take_profit REAL,
    stop_loss REAL,
    sentiment_score REAL,             -- FinBERT score (-1 to +1)
    source_url TEXT,
    source_text TEXT,                 -- original post text (for audit)
    scraped_at TEXT NOT NULL,
    status TEXT DEFAULT 'ACTIVE',     -- ACTIVE, TP_HIT, SL_HIT, EXPIRED, INVALID
    outcome_pnl_pct REAL,
    resolved_at TEXT,
    resolution_price REAL
);

CREATE TABLE predictors (
    predictor_id TEXT PRIMARY KEY,
    platform TEXT NOT NULL,
    display_name TEXT,
    profile_url TEXT,
    total_predictions INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    win_rate REAL DEFAULT 0.0,
    avg_pnl_pct REAL DEFAULT 0.0,
    best_pick_pnl REAL,
    worst_pick_pnl REAL,
    sharpe REAL DEFAULT 0.0,
    first_seen TEXT,
    last_active TEXT,
    tier TEXT DEFAULT 'UNRANKED'       -- ELITE, PROVEN, MIXED, LOSING, UNRANKED
);

CREATE TABLE scrape_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT,
    scraped_at TEXT,
    posts_found INTEGER,
    predictions_extracted INTEGER,
    errors TEXT
);
```

### Prediction Extraction Pipeline

1. **Scraper** fetches raw text (idea description, post body, tweet)
2. **Regex patterns** attempt fast extraction first:
   - `(entry|buy|sell|short|long)\s*[:@]?\s*\$?([\d,\.]+)`
   - `(tp|take profit|target)\s*[:=]?\s*\$?([\d,\.]+)`
   - `(sl|stop loss|stop)\s*[:=]?\s*\$?([\d,\.]+)`
3. **FinBERT** scores overall sentiment (87% accuracy on financial text)
4. If regex fails to extract all fields, **Crawl4AI LLM extraction** with Pydantic schema
5. Store structured prediction in SQLite
6. **Price validator** checks TP/SL vs live Binance prices every 15min

### Predictor Tier System

| Tier | Criteria | Badge |
|------|----------|-------|
| ELITE | WR >= 65%, >= 20 picks, Sharpe > 1.5 | Gold |
| PROVEN | WR >= 55%, >= 10 picks, Sharpe > 0.5 | Green |
| MIXED | WR 45-55%, >= 5 picks | Yellow |
| LOSING | WR < 45%, >= 5 picks | Red |
| UNRANKED | < 5 picks | Gray |

### Leaderboard Dashboard

Dark-themed HTML page at `/predictions/index.html` (deployed via GitHub Pages):
- **Leaderboard table** with sortable columns (Rank, Predictor, Platform, WR, Avg P&L, Sharpe, Tier)
- **Platform badges** (TradingView blue, Reddit orange, Twitter/X black, Blog green, YouTube red)
- **Per-predictor detail view** — click to see all predictions + outcomes
- **Active predictions ticker** — currently open predictions being tracked
- **Symbol filter** — filter by BTC, ETH, SOL, etc.
- **Time filter** — 7d, 30d, 90d, all-time
- **Auto-refresh** every 5 minutes from JSON endpoint

### Key Symbols Tracked
BTC, ETH, SOL, BNB, DOGE, SHIB, LINK, SUI, DOT, ADA, AVAX, XRP
(matching our trading systems' universe)

### Safety: Read-Only Advisory
- Social predictions are **NOT used to change any existing system's behavior**
- They exist as a standalone competition/leaderboard
- Future potential: top ELITE predictors could be used as supplemental signals (advisory only)

---

## Phase 3: Cross-System Improvements (from AI Reviewer Consensus)

### 3A. Confluence Master Aggregator
- New micro-service: emit signal ONLY if >= 2 systems agree on direction + symbol
- Weight by recent out-of-sample hit rate in current regime bucket
- Resolves Mercury LONG vs Battleground SHORT conflicts

### 3B. Unified Backtest Schema (per Perplexity's feedback)
Per-trade normalized log:
- timestamp, symbol, direction, entry_price, stop_price, target_price
- exit_price, exit_reason, max_favorable_excursion, max_adverse_excursion
- fees+slippage model, trailing/time-exit modifications
- Regime bucket (panic, trend_up, trend_down, chop)

### 3C. Feature Enrichment (per Inception/Grok)
Add to all ML models:
- funding_z_1h, oi_pct_change_4h, btc_4h_return
- liquidation heatmap proxy
- cross-exchange basis spread

### 3D. Portfolio-Level Risk Guard
- Max 25% per coin, max 60% crypto allocation
- Correlation cap: if Pearson > 0.7 between active picks, drop lowest-confidence
- Global drawdown circuit breaker

---

## Implementation Priority

| Phase | What | Impact | Effort | When |
|-------|------|--------|--------|------|
| 1A | Kill PANIC_SELL + launch A2/B2 | +10-15% WR on battleground | Low | Today |
| 1B | Unfreeze Breakout Arena C | Fix stale picks | Low | Today |
| 1C | Relax falling knife filter | Capture bounces | Low | Today |
| 1D | Connect Claude Gainer ML | Visibility | Low | Today |
| 1E | ICT/SMC regime gate + TJR improvements | +14-19% WR on Alpha crypto | Medium | This week |
| 2 | Social Media Prediction Competition | New capability | High | 1-2 weeks |
| 3 | Cross-system improvements | Structural | High | 2-4 weeks |

---

## Dependencies

- **Crawl4AI:** Must be installed (`pip install crawl4ai`)
- **PRAW:** Already available (Reddit credentials in scripts/config.py)
- **snscrape:** Must be installed (`pip install snscrape`)
- **FinBERT:** Already available (`scripts/finbert_sentiment.py`)
- **Scrapling:** Already installed (fallback for anti-bot sites)
- **tradingview-scraper:** Must be installed (`pip install tradingview-scraper`)

---

---

## Phase 4: Advanced Techniques (from Google/Gemini Analysis)

### 4A. Betting Against BAD Beta (BABB) — Upgrade from BAB
**Source:** Campbell & Vuolteenaho (2004)
**Current:** Alpha Engine uses standard BAB factor for stock picks
**Upgrade:** Double-sort on market beta + "bad beta" (sensitivity to permanent cash-flow shocks)
- BABB delivers 15.0% annual vs 11.4% for standard BAB
- Five-factor alpha: 75 bps/month vs 51 bps/month
- More robust to regime shifts (Sharpe 1.09 vs 1.01)
- Add market-cap floor (exclude bottom 1-5%) to ensure liquidity
- Add "flight-to-quality" filter: after high sentiment, returns decline across beta quintiles

### 4B. Meta-Labeling (Marcos Lopez de Prado)
**Concept:** Two-stage ML pipeline — direction model + win/loss filter
- **Stage 1 (High Recall):** Existing strategies generate direction signals (LONG/SHORT)
- **Stage 2 (High Precision):** XGBoost meta-model predicts "will THIS signal win?" using:
  - Rolling 7d/30d volatility
  - OFI (order flow imbalance)
  - Gamma exposure (if available)
  - TED spread / funding term structure
  - Time-of-day / session features
- **Stage 3:** Size positions by meta-model confidence (0 = skip, 1 = full size)
- Expected improvement: +1-3% WR — modest but critical at scale

### 4C. Gamma Exposure (GEX) Integration
**Concept:** Options dealers' hedging creates predictable price dynamics
- **Positive GEX:** Dealers absorb shocks → range-bound → use mean-reversion strategies
- **Negative GEX:** Dealers amplify moves → trending → use momentum strategies
- **Gamma Flip point:** Dynamic pivot between regimes
- **Data source:** Options open interest from Deribit (crypto) or CBOE (equities)
- Integrate as feature in all ML models + use for strategy selection

### 4D. Multi-Level Order Flow Imbalance (MLOFI)
**Concept:** Net buying/selling pressure across 10 levels of order book depth
- Captures latent block order activity invisible on L1 data
- Reduces predictive RMSE by up to 74% in high-tick markets
- Combine with GARCH for crypto daily prediction
- **Data source:** Binance WebSocket depth stream (free, 100ms updates)

### 4E. Walk-Forward with Purging + Embargoing
**Current problem:** 80/20 split with potential information leakage
**Fix:**
- **Purging:** Remove training samples that overlap with test period boundaries
- **Embargoing:** Remove samples from training that follow a test set
- **Rolling windows:** 6-month train, 1-month test, roll forward monthly
- Only deploy strategies with Walk-Forward Efficiency (WFE) > 60%

### 4F. Brier Score Agent Weighting
**Current:** Simple win-rate for system comparison
**Upgrade:** Weight each sub-system by Brier Score (calibration quality)
- Brier Score = mean squared difference between predicted probability and actual outcome
- Decomposes into: Reliability (calibration) + Resolution (discrimination) + Uncertainty
- Favors well-calibrated models over noisy high-Sharpe models
- Use for cross-system arbitration weighting

### 4G. Behavioral Group Arbitration
**Current concept:** If 3+ systems agree, trade
**Upgrade:** Group signals by market perspective:
- **Group A (Volatility-positive):** Momentum, breakout, liquidation cascade
- **Group B (Volatility-negative):** Mean reversion, F&G contrarian, carry trade
- **Group C (Structural):** BAB/BABB, ICT/SMC, order flow
- Vote WITHIN groups first, then groups vote at ensemble level
- Reduces false positives from correlated signals (e.g., 5 momentum signals all agree but it's one perspective)

---

## Phase 5: Validation Architecture Fixes (from ChatGPT Deep Research)

### 5A. DSR/PSR on Returns, Not Probabilities
**Critical bug identified:** Multiple systems compute `deflated_sharpe_ratio(probs)` using mean predicted probabilities as if they were returns. DSR is designed to correct the Sharpe ratio for selection bias and non-normality when computed from **realized returns of a strategy**, not prediction probabilities.
**Fix:**
- Replace probability-based PSR/DSR with returns-based computation
- Define a deterministic trading policy → generate realized return series (including costs) → compute PSR/DSR on that series
- This is how "100 strategies" becomes provably robust rather than "selection bias as a service"

### 5B. Triple-Barrier Labeling (Align Training to Product)
**Current problem:** Training on "next-4h return > 0" but product delivers "entry + TP/SL quality" — these are different objectives.
**Fix:** Label using event-based outcomes tied to TP/SL/time (triple-barrier method):
- Upper barrier (TP hit first) = +1
- Lower barrier (SL hit first) = -1
- Time barrier (neither hit) = 0
- Aligns model score with subscriber-visible win rate
- For higher WR product: set closer TP1, label success as "TP1 hit before SL"

### 5C. Mercury 2 Guard Semantics Fix
**Bug:** `prob ≥ 2× cost` guard is economically meaningless — raw probability is not a return.
**Fix:** Port Crypto Signal Engine's cost-adjusted expected edge:
- `expected_edge = prob × tp_distance - (1-prob) × sl_distance - costs`
- Require `expected_edge > 0` instead of `prob > 2×cost`
- Will filter "barely positive" setups where noise dominates after fees

### 5D. Meta-Policy Arbiter (Cross-System Conflict Resolution)
**Problem:** ML Battleground SHORTs while Mercury 2 LONGs the same symbol in the same regime.
**Fix:** Single global arbiter as only component that emits "public picks":
- Inputs: all system proposals + regime state + each system's rolling forward stats
- When systems disagree: default to "no trade" unless one has materially superior recent forward performance in that regime bucket
- Weight votes by regime-conditioned accuracy (not overall accuracy)

### 5E. Purged + Embargoed Cross-Validation
**Problem:** 5-30 min scan frequency with 4h prediction horizons creates severe label overlap leakage.
**Fix:**
- Remove training samples whose label windows overlap with test fold boundaries (purging)
- Apply embargo buffer after each test fold to reduce residual leakage
- Critical for any system scanning at sub-horizon frequency

---

## Reviewer Summary

| Reviewer | Key Unique Contribution |
|----------|------------------------|
| **Inception Labs** | Dynamic confidence thresholds by regime; portfolio-level correlation cap |
| **Grok AI** | Mercury 2 now 8/8 wins; concrete P0-P3 priority code snippets; "Extreme-Fear AI" brand |
| **Perplexity** | Unified backtest schema requirement; expectancy > WR focus; asked for closed_picks.json |
| **Google/Gemini** | BABB upgrade, meta-labeling, GEX/OFI features, Brier Score weighting, behavioral group arbitration |
| **ChatGPT** | DSR/PSR computed on probs not returns (fundamental bug); triple-barrier labeling; `prob≥2×cost` guard semantically wrong; meta-policy arbiter for cross-system conflicts |
| **TJR Analysis** | 5 critical ICT/SMC gaps (no MTF, no retest, wrong R:R, no quality filter, no MSS) |

---

*Design approved Feb 25, 2026. Incorporating feedback from Inception Labs, Grok AI, Perplexity AI, Google/Gemini, ChatGPT Deep Research, and TJR Trades methodology analysis.*
