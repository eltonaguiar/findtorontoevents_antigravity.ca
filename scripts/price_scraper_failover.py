#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
price_scraper_failover.py — Yahoo Finance web scraper for stock prices.
Used as failover when Finnhub/API/cache fail in live_signals.php.

Usage: python price_scraper_failover.py SYMBOL
Output: JSON to stdout: {"ok": true, "price": 185.23, "source": "yahoo_scraper"}
        or {"ok": false, "error": "..."}

Requires: pip install beautifulsoup4 requests
"""
import sys
import json
import re

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print(json.dumps({"ok": False, "error": "Missing deps: pip install beautifulsoup4 requests"}))
    sys.exit(1)


def scrape_yahoo_price(ticker):
    """Scrape current/latest price from Yahoo Finance quote page."""
    url = 'https://finance.yahoo.com/quote/' + ticker
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, 'html.parser')
        # Yahoo quote page: look for data-test="quote-price" or finance-streamer
        price_el = soup.find('fin-streamer', {'data-field': 'regularMarketPrice'})
        if price_el and price_el.get('value'):
            return float(price_el['value'])
        # Fallback: regex for yahoo's JSON blob in page
        match = re.search(r'"regularMarketPrice":\s*{"raw":\s*([\d.]+)', r.text)
        if match:
            return float(match.group(1))
        match = re.search(r'"regularMarketPrice"\s*:\s*([\d.]+)', r.text)
        if match:
            return float(match.group(1))
        return None
    except Exception as e:
        return None


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"ok": False, "error": "Usage: price_scraper_failover.py SYMBOL"}))
        sys.exit(1)
    ticker = sys.argv[1].strip().upper()
    if not ticker or not re.match(r'^[A-Z0-9.]{1,10}$', ticker):
        print(json.dumps({"ok": False, "error": "Invalid ticker"}))
        sys.exit(1)
    price = scrape_yahoo_price(ticker)
    if price is not None and price > 0:
        print(json.dumps({"ok": True, "price": round(price, 4), "source": "yahoo_scraper"}))
        sys.exit(0)
    print(json.dumps({"ok": False, "error": "Could not scrape price"}))
    sys.exit(1)


if __name__ == '__main__':
    main()
