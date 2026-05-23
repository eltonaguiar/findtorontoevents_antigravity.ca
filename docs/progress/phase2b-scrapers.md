# Phase 2B: Social Media Scrapers Progress

## Task 7: Reddit Scraper
- [x] Created `social_prediction_tracker/scrapers/reddit_scraper.py`
- [x] PRAW-based scraping from 5 crypto subreddits
- [x] Regex extraction for entry/TP/SL from post text
- [x] 12 key symbols (BTC, ETH, SOL, BNB, DOGE, SHIB, LINK, SUI, DOT, ADA, AVAX, XRP)
- [x] Graceful degradation when PRAW not installed or credentials missing
- [x] Syntax verified

## Task 8: TradingView Scraper
- [x] Created `social_prediction_tracker/scrapers/tradingview_scraper.py`
- [x] Crawl4AI-based JS rendering for TradingView Ideas pages
- [x] 11 symbols scraped from ideas pages
- [x] Markdown parsing with direction/entry/TP/SL extraction
- [x] Graceful degradation when crawl4ai not installed
- [x] Syntax verified

## Common
- [x] Created `social_prediction_tracker/scrapers/__init__.py`
- [x] Both scrapers use shared `db.py` (get_db, insert_prediction)
- [x] Both log to `scrape_log` table
