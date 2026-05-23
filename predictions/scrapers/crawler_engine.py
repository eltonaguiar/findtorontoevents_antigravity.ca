"""Advanced crawler engine using Crawl4AI and Scrapling.

Provides resilient crawling with multiple fallback methods:
1. Crawl4AI - JavaScript rendering, screenshot capability
2. Scrapling - TLS fingerprint evasion
3. Playwright - Full browser automation
4. Requests + BeautifulSoup - Static HTML fallback
"""
import asyncio
import re
import sys
import time
from pathlib import Path
from typing import Callable, Optional

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent.parent))

# Try to import optional dependencies
try:
    from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
    HAS_CRAWL4AI = True
except ImportError:
    HAS_CRAWL4AI = False

try:
    from scrapling import Fetcher
    HAS_SCRAPLING = True
except ImportError:
    HAS_SCRAPLING = False

try:
    from playwright.async_api import async_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

# Default headers for requests
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
}


class CrawlerEngine:
    """Advanced crawler with multiple fallback methods."""
    
    def __init__(self, delay: float = 1.0, timeout: int = 30):
        self.delay = delay
        self.timeout = timeout
        self.last_method_used = None
        
    async def fetch(self, url: str, use_js: bool = True) -> tuple[str, str]:
        """Fetch URL with automatic fallback chain.
        
        Returns: (html_content, method_used)
        """
        html = None
        method = None
        
        # Method 1: Crawl4AI (best for JS sites)
        if use_js and HAS_CRAWL4AI and not html:
            try:
                html = await self._fetch_crawl4ai(url)
                if html and len(html) > 1000:
                    method = "crawl4ai"
                    print(f"  ✓ Fetched via Crawl4AI")
            except Exception as e:
                print(f"  Crawl4AI failed: {e}")
        
        # Method 2: Scrapling (best for anti-bot)
        if HAS_SCRAPLING and not html:
            try:
                html = self._fetch_scrapling(url)
                if html and len(html) > 1000:
                    method = "scrapling"
                    print(f"  ✓ Fetched via Scrapling")
            except Exception as e:
                print(f"  Scrapling failed: {e}")
        
        # Method 3: Playwright (reliable JS rendering)
        if use_js and HAS_PLAYWRIGHT and not html:
            try:
                html = await self._fetch_playwright(url)
                if html and len(html) > 1000:
                    method = "playwright"
                    print(f"  ✓ Fetched via Playwright")
            except Exception as e:
                print(f"  Playwright failed: {e}")
        
        # Method 4: Requests (static fallback)
        if not html:
            try:
                html = self._fetch_requests(url)
                if html and len(html) > 1000:
                    method = "requests"
                    print(f"  ✓ Fetched via Requests")
            except Exception as e:
                print(f"  Requests failed: {e}")
        
        self.last_method_used = method
        return html or "", method or "failed"
    
    async def _fetch_crawl4ai(self, url: str) -> str | None:
        """Fetch using Crawl4AI with JavaScript rendering."""
        browser_config = BrowserConfig(
            headless=True,
            extra_args=["--disable-gpu", "--disable-dev-shm-usage", "--no-sandbox"]
        )
        
        run_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            page_timeout=self.timeout * 1000,
            wait_until="networkidle"
        )
        
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(url=url, config=run_config)
            if result.success:
                return result.html
        return None
    
    def _fetch_scrapling(self, url: str) -> str | None:
        """Fetch using Scrapling with TLS fingerprint evasion and stealth."""
        try:
            from scrapling import Fetcher
            
            # Configure Fetcher with stealth mode enabled
            # auto_match=True enables automatic browser fingerprint matching
            Fetcher.configure(auto_match=True)
            
            fetcher = Fetcher(timeout=self.timeout)
            
            # Add stealth headers and rotate User-Agent
            import random
            user_agents = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
            ]
            
            headers = {
                **DEFAULT_HEADERS,
                "User-Agent": random.choice(user_agents),
                "Accept-Language": random.choice(["en-US,en;q=0.9", "en-GB,en;q=0.8", "en-CA,en;q=0.9"]),
            }
            
            resp = fetcher.get(url, headers=headers)
            
            if resp.status == 200:
                print(f"  ✓ Scrapling stealth fetch successful")
                return resp.text
            else:
                print(f"  Scrapling returned status {resp.status}")
                
        except Exception as e:
            print(f"  Scrapling error: {e}")
        
        return None
    
    async def _fetch_playwright(self, url: str) -> str | None:
        """Fetch using Playwright browser automation."""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=DEFAULT_HEADERS["User-Agent"],
                viewport={"width": 1920, "height": 1080}
            )
            page = await context.new_page()
            
            try:
                await page.goto(url, wait_until="networkidle", timeout=self.timeout * 1000)
                await asyncio.sleep(2)  # Wait for JS to execute
                html = await page.content()
                await browser.close()
                return html
            except:
                await browser.close()
                return None
    
    def _fetch_requests(self, url: str) -> str | None:
        """Fetch using requests + BeautifulSoup."""
        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=self.timeout)
        if resp.status_code == 200:
            return resp.text
        return None
    
    def parse_html(self, html: str, parser: str = "html.parser") -> BeautifulSoup:
        """Parse HTML with BeautifulSoup."""
        return BeautifulSoup(html, parser)
    
    def extract_text(self, soup: BeautifulSoup, selector: str) -> str:
        """Extract text using CSS selector."""
        elem = soup.select_one(selector)
        return elem.get_text(strip=True) if elem else ""
    
    def extract_all_text(self, soup: BeautifulSoup, selector: str) -> list[str]:
        """Extract all matching texts."""
        return [elem.get_text(strip=True) for elem in soup.select(selector)]
    
    def extract_links(self, soup: BeautifulSoup, base_url: str = "") -> list[dict]:
        """Extract all links with text."""
        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith("/"):
                href = base_url + href
            links.append({
                "url": href,
                "text": a.get_text(strip=True),
                "title": a.get("title", "")
            })
        return links


# Synchronous wrapper for convenience
def fetch_page(url: str, use_js: bool = True, delay: float = 1.0) -> tuple[str, str]:
    """Synchronous wrapper to fetch a page with automatic fallback."""
    engine = CrawlerEngine(delay=delay)
    return asyncio.run(engine.fetch(url, use_js=use_js))


if __name__ == "__main__":
    # Test the crawler
    test_urls = [
        "https://coincodex.com/crypto/bitcoin/price-prediction/",
        "https://www.tradingview.com/symbols/BTCUSD/ideas/",
    ]
    
    for url in test_urls:
        print(f"\nTesting: {url}")
        html, method = fetch_page(url, use_js=True)
        print(f"Method: {method}, Length: {len(html)}")
