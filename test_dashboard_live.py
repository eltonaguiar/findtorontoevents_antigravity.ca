#!/usr/bin/env python3
"""Test the live dashboard using Playwright"""
import asyncio
from playwright.async_api import async_playwright

async def test_dashboard():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Load the dashboard
        url = 'https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/predictions/dashboard/'
        print(f'Loading {url}...')
        
        try:
            await page.goto(url, wait_until='networkidle', timeout=30000)
            print('Page loaded successfully')
            
            # Wait for content to load
            await asyncio.sleep(3)
            
            # Get stats
            predictors = await page.text_content('#s-predictors')
            predictions = await page.text_content('#s-predictions')
            active = await page.text_content('#s-active')
            
            print(f'\nDashboard Stats:')
            print(f'  Predictors: {predictors}')
            print(f'  Total Picks: {predictions}')
            print(f'  Active: {active}')
            
            # Count visible prediction cards
            cards = await page.query_selector_all('.active-card')
            print(f'\nVisible prediction cards: {len(cards)}')
            
            # Get sources
            sources = await page.eval_on_selector_all('.active-card', '''elements => {
                return elements.map(el => el.getAttribute('data-source'));
            }''')
            
            from collections import Counter
            print('\nBy source (visible):')
            for src, count in Counter(sources).most_common():
                print(f'  {src}: {count}')
            
            # Check for data warning
            warning = await page.text_content('#data-warning')
            if warning:
                print(f'\nData warning: {warning}')
            
            # Take screenshot
            await page.screenshot(path='dashboard_screenshot.png', full_page=False)
            print('\nScreenshot saved: dashboard_screenshot.png')
            
        except Exception as e:
            print(f'Error: {e}')
        finally:
            await browser.close()

if __name__ == '__main__':
    asyncio.run(test_dashboard())
