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

## Completed in Session 2

- [x] **analyze.php** — Lookahead bias fix (`trade_date >` instead of `>=`)
- [x] **setup_schema.php** — Composite indexes (algo+date, ticker+date)
- [x] **live_signals.php** — Bybit funding rate integration (short squeeze detection)
- [x] **meme_scanner.php** — BTC regime adaptive scoring (bull/bear/chop adjustments)
- [x] **meme_scanner.php** — Expanded meme keywords (27→56)
- [x] **seed_signals.php** — SHORT signals for forex (Trend Following + Mean Reversion)
- [x] **sports_odds.php** — CLV tracking table + opening/closing odds comparison
- [x] **forex_insights.php** — ATR-based position sizing (2% risk, inversely to volatility)

---

## Deployment Status

| File | FTP Path | Status |
|------|----------|--------|
| `findstocks/api/analyze.php` | `/findstocks/api/analyze.php` | Pending |
| `findstocks/api/setup_schema.php` | `/findstocks/api/setup_schema.php` | Pending |
| `live-monitor/api/live_signals.php` | `/live-monitor/api/live_signals.php` | Pending |
| `findcryptopairs/api/meme_scanner.php` | `/findcryptopairs/api/meme_scanner.php` | Pending |
| `findforex2/api/seed_signals.php` | `/findforex2/api/seed_signals.php` | Pending |
| `live-monitor/api/sports_odds.php` | `/live-monitor/api/sports_odds.php` | Pending |
| `findforex2/portfolio/api/forex_insights.php` | `/findforex2/portfolio/api/forex_insights.php` | Pending |

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

## Summary of All Changes (Sessions 1+2)

### Total: 11 files modified, 16 improvements implemented

**Infrastructure (Session 1):**
1. cURL retry in import_picks.php
2. JSON validation in import_picks.php
3. Timeout 900s in daily_refresh.php
4. cURL retry in daily_refresh.php
5. Trailing stops in live_trade.php
6. Volatility position sizing in live_trade.php
7. ATR-based TP/SL in live_signals.php
8. Momentum crash protection in live_signals.php

**Algorithmic (Session 2):**
9. Lookahead bias fix in analyze.php
10. Composite indexes in setup_schema.php
11. Funding rate integration (Bybit) in live_signals.php
12. BTC regime adaptive scoring in meme_scanner.php
13. 56 meme keywords (was 27) in meme_scanner.php
14. SHORT signals for forex in seed_signals.php
15. CLV tracking in sports_odds.php
16. ATR position sizing in forex_insights.php
