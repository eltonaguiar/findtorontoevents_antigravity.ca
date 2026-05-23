# 26-Portfolio Challenge Action Items

## Critical Data Integrity (Complete after sanitizer push)
- [x] Deploy state sanitizer + price guard to portfolio_manager.py (auto-cleans corrupt trades on every load)
- [x] Deep clean claudes_test_state.json ($6K fake PnL removed, dupes purged)
- [x] Fix RL agent synthetic prices (symbol-specific base prices)
- [x] Fix forex asset classification (_derive_asset_class strips =X, checks forex first)
- [x] Add 3-layer price reference (Binance + CoinGecko + hardcoded fallback)
- [x] Overhaul portfolio_history.html (live prices, EST timestamps, price warnings, 26-portfolio tabs)
- [x] Update updates/index.html with corrected PnL scoreboard + post-mortem

## Deployment & Verification
- [ ] Verify GitHub Pages deploy includes sanitizer (check live claudes_test_state.json has no DOGE@50K)
- [ ] Fix 50webs FTP audit_dashboard path (mkdir -p $REMOTE_BASE/audit_dashboard)
- [ ] Run playwright audit on portfolio_history.html (every trade price/timestamp/PnL)
- [ ] Confirm updates page live with corrected returns (RSI Cap +3.4%, no +31.5% Momentum)

## Recurring Automation
- [x] 2h quality check cron (f252bc0f, expires 3 days)
- [ ] Set up hourly portfolio_manager.py cron (regenerate dashboard + updates entry)
- [ ] Hourly updates/index.html auto-update workflow (progress + PnL snapshot)

## Forex & Non-Crypto
- [ ] Resume forex research agent (a34bfb8daef2592cf) — apply findings to forex_carry (0 picks)
- [ ] Add asset-class staleness filter (CRYPTO 2h, FOREX 8h, EQUITY 12h) — DONE locally, deploy
- [ ] Test non-crypto portfolios (stocks_best, forex_carry) post-firewall + classification fix

## Data Sources Cleanup
- [ ] Clean MySQL ejaguiar1_stocks (DELETE corrupt DOGE/JNJ/TRX, dupes, extreme PnL)
- [ ] Purge corrupt picks from all source JSONs (rl_agent/data, alpha_engine/data, etc.)
- [ ] Add unique constraints + price CHECKs to MySQL tables

## Maintenance & Evolution
- [ ] First hourly run: extensive checks (price sanity, diversity, WR recalc)
- [ ] Evolve portfolios: mutate DNA for underperformers (Contrarian -0.23%, Prop Aggressive BLOWN)
- [ ] Honest reporting: track real forward PnL, no inflation

**Status: 25/26 ACTIVE | 1 BLOWN (Prop Aggressive)**  
**Next: Deploy sanitizer → Clean MySQL → Hourly cron → Playwright verify**