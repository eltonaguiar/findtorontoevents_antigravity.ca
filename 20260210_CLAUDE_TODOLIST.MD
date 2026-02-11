# Kimi Swarm Audit — Claude Implementation Todolist
## Generated: 2026-02-10 (Session 2)

### Context
Based on 6 Kimi Swarm research documents analyzing the entire trading platform.
Session 1 handled P0 infrastructure fixes (import_picks, daily_refresh, live_trade, live_signals).
Session 2 handles remaining algorithmic + data improvements.

**NOT FEASIBLE** (user confirmed):
- MyISAM → InnoDB migration
- Foreign key constraints (requires InnoDB)
- Transaction wrappers (requires InnoDB)

---

## Completed in Session 1 (Previous)

- [x] **import_picks.php** — cURL retry replacing `@file_get_contents` (P0)
- [x] **import_picks.php** — JSON decode validation + fetch_log (P0)
- [x] **daily_refresh.php** — Timeout 600→900s, `@` removed (P0)
- [x] **daily_refresh.php** — cURL retry in `dr_fetch()` (P0)
- [x] **live_trade.php** — Trailing stops (activate 50% TP, trail 60% SL)
- [x] **live_trade.php** — Volatility-adjusted position sizing (3-7%)
- [x] **live_signals.php** — ATR-based dynamic TP/SL (14-period ATR)
- [x] **live_signals.php** — Momentum crash protection (block 6 algos when ATR > 2.5x)

---

## Session 2 Action Items

### 1. Fix Lookahead Bias in analyze.php (P0)
- **File**: `findstocks/api/analyze.php`
- **Issue**: `_mini_backtest()` queries `trade_date >= '$safe_d'` — includes pick day itself, using same-day high/low the algorithm already saw
- **Fix**: Change to `trade_date > '$safe_d'` (start from DAY AFTER pick)
- **Impact**: +5-10% Sharpe (backtests will be more realistic, not overstated)
- [ ] Implemented
- [ ] Deployed
- [ ] Verified

### 2. Add Composite Indexes to setup_schema.php
- **File**: `findstocks/api/setup_schema.php`
- **Issue**: Individual indexes exist but no composite indexes for common query patterns
- **Fix**: Add `(algorithm_name, pick_date)` and `(ticker, pick_date)` composite indexes
- **Impact**: Faster backtest/analysis queries
- [ ] Implemented
- [ ] Deployed
- [ ] Verified

### 3. Add Funding Rate Integration for Crypto
- **File**: `live-monitor/api/live_signals.php`
- **Issue**: No perpetual futures funding rate data (misses short squeeze opportunities)
- **Fix**: Fetch from Bybit public API (free, no auth), use as additional signal factor
- **Impact**: +10-15% crypto win rate
- [ ] Implemented
- [ ] Deployed
- [ ] Verified

### 4. BTC Regime Adaptive Scoring for Meme/Crypto
- **File**: `findcryptopairs/api/meme_scanner.php`
- **Issue**: Static scoring weights regardless of market regime
- **Fix**: Detect BTC trend (SMA20 vs SMA50), adjust scoring: bull=boost momentum, bear=boost volume/breakout
- **Impact**: +15-20% improvement in meme coin win rate
- [ ] Implemented
- [ ] Deployed
- [ ] Verified

### 5. Expand Meme Keyword List (27→50+)
- **File**: `findcryptopairs/api/meme_scanner.php`
- **Issue**: Only 27 keywords, missing new trending meme coins
- **Fix**: Add 25+ new keywords from 2025-2026 meme cycles
- **Impact**: +5-10% discovery of emerging meme coins
- [ ] Implemented
- [ ] Deployed
- [ ] Verified

### 6. Add SHORT Signals for Forex
- **File**: `findforex2/api/seed_signals.php`
- **Issue**: Only LONG signals generated (missing 50% of profit potential)
- **Fix**: Generate both Trend Following + Mean Reversion signals with proper directions
- **Impact**: +25% return potential
- [ ] Implemented
- [ ] Deployed
- [ ] Verified

### 7. Add CLV Tracking for Sports Betting
- **File**: `live-monitor/api/sports_odds.php`
- **Issue**: No closing line value tracking — can't validate if edge is real
- **Fix**: Store opening odds snapshot, compute CLV when odds refresh before game
- **Impact**: +5-10% edge validation
- [ ] Implemented
- [ ] Deployed
- [ ] Verified

### 8. Add ATR-Based Position Sizing for Forex
- **File**: `findforex2/portfolio/api/forex_insights.php`
- **Issue**: Fixed 10% position sizing, no volatility adjustment
- **Fix**: Calculate ATR(14) and size positions inversely to volatility
- **Impact**: -30% drawdown improvement
- [ ] Implemented
- [ ] Deployed
- [ ] Verified

---

## Deferred Items (Require External APIs / Paid Services)
- Social sentiment via LunarCrush ($50/mo)
- On-chain metrics via Glassnode/CryptoQuant ($200/mo)
- Interest rate differential data for forex
- Economic calendar integration
- Injury/weather APIs for sports
- ML model training (Python infrastructure)
- Deep learning / LSTM / Transformers
- Broker API integration (Alpaca, IBKR)

---

## Files Modified in This Session
| File | Change |
|------|--------|
| `findstocks/api/analyze.php` | Lookahead bias fix |
| `findstocks/api/setup_schema.php` | Composite indexes |
| `live-monitor/api/live_signals.php` | Funding rate integration |
| `findcryptopairs/api/meme_scanner.php` | BTC regime scoring + expanded keywords |
| `findforex2/api/seed_signals.php` | SHORT signal generation |
| `live-monitor/api/sports_odds.php` | CLV tracking |
| `findforex2/portfolio/api/forex_insights.php` | ATR position sizing |
