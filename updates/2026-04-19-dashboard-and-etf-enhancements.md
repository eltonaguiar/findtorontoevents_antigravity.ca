# Dashboard & Risk Profile Enhancements (2026-04-19)

**What Was Broken/Missing:**
1. 3x Leveraged ETFs (like TQQQ, SOXL) were inheriting the standard ETF risk profile (5% Stop Loss), which is too tight for their high volatility.
2. The Dashboard's `fetchStockPrices` function was batching all non-crypto tickers into a single massive Yahoo Finance API URI, causing HTTP 414 (URI Too Long) errors as the ETF/Bond universe expanded.
3. The Dashboard lacked a way to easily compare aggregate performance across different asset classes natively.

**What Changed:**
1. **Leveraged ETF Risk Class:** Added `leveraged_etf` to `CATEGORY_RISK` in `alpha_engine/config.py` with 3x wider stops (-0.15 SL / 0.30 TP). Updated `get_asset_class()` to automatically detect 3x tickers based on substrings (e.g. `QQQ` and `SOX`).
2. **Yahoo API Pagination:** Refactored `audit_dashboard/template.html` to chunk all Yahoo Finance fetch calls into arrays of 50 tickers, avoiding the URI length limit.
3. **Asset Class Leaderboard:** Added Feature 4 to `audit_dashboard/dashboard_enhancements.js`, which dynamically parses closed picks and generates a clean UI table showing WR, Net PnL, and Total Trades for Crypto vs Equity vs ETF vs Forex vs Futures vs Bonds.

**Verification:**
- The `alpha_engine` now correctly maps `TQQQ` to the wider risk category.
- The dashboard generator creates the new Asset Class breakdown table with real-time stats.
- Yahoo API handles 100+ stock tickers without crashing.
