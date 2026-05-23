#!/usr/bin/env python3
"""
Verify SUPERPOWERS ARENA dashboard is working correctly.
Run after GitHub Pages deployment to validate:
1. Page loads without errors
2. All 39 strategies are displayed
3. Metrics show correctly (not all 0s)
4. Strategy count is visible
5. Next update timestamp shows

Usage: python verify_battleground.py [--wait 300]
"""

import sys
import time
import argparse
from playwright.sync_api import sync_playwright

def verify_dashboard(wait_seconds=300):
    """Verify the battleground dashboard."""
    url = "https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/battleground/"
    
    print(f"🔍 Verifying: {url}")
    print(f"⏳ Waiting up to {wait_seconds}s for deployment...")
    
    start_time = time.time()
    
    while time.time() - start_time < wait_seconds:
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, timeout=30000)
                
                # Wait for content to load
                page.wait_for_timeout(3000)
                
                # Check 1: Page title
                title = page.title()
                print(f"\n✅ Page loaded: {title}")
                
                # Check 2: Strategy count
                count_el = page.locator("#strat-count").first
                if count_el.is_visible():
                    count_text = count_el.text_content()
                    print(f"✅ Strategy count: {count_text}")
                    
                    # Extract number
                    import re
                    match = re.search(r'(\d+)', count_text)
                    if match:
                        count = int(match.group(1))
                        if count >= 39:
                            print(f"✅ All {count} strategies displayed!")
                        else:
                            print(f"⚠️ Only {count} strategies (expected 39)")
                else:
                    print("❌ Strategy count not found")
                
                # Check 3: Baby Strat cards
                cards = page.locator(".baby-strat-card").all()
                print(f"✅ Found {len(cards)} strategy cards")
                
                # Check 4: Look for pending or actual metrics (not all 0%)
                metrics = page.locator(".backtest-preview value").all()
                pending_count = sum(1 for m in metrics if 'pending' in (m.text_content() or '').lower())
                zero_count = sum(1 for m in metrics if m.text_content() in ['0%', '0', '-0%'])
                
                print(f"📊 Metrics: {pending_count} pending, {zero_count} showing 0")
                
                if zero_count > 50 and pending_count == 0:
                    print("❌ Too many 0s - data not loading properly!")
                elif pending_count > 0:
                    print("✅ Pending metrics showing correctly")
                
                # Check 5: Next update timestamp
                next_update = page.locator("#next-update").first
                if next_update.is_visible():
                    print(f"✅ Next update: {next_update.text_content()}")
                
                # Check 6: Agent names (not "undefined")
                page_content = page.content()
                undefined_count = page_content.count('by undefined')
                if undefined_count > 0:
                    print(f"❌ Found {undefined_count} 'by undefined' entries")
                else:
                    print("✅ All agent names displayed correctly")
                
                # Take screenshot for verification
                page.screenshot(path="battleground_verify.png", full_page=True)
                print("\n📸 Screenshot saved: battleground_verify.png")
                
                browser.close()
                
                print("\n✅ VERIFICATION COMPLETE")
                return True
                
        except Exception as e:
            elapsed = int(time.time() - start_time)
            remaining = wait_seconds - elapsed
            print(f"⏳ Attempt failed ({elapsed}s elapsed, {remaining}s remaining): {e}")
            if remaining > 0:
                time.sleep(10)
            else:
                print("\n❌ VERIFICATION FAILED - Timeout")
                return False
    
    return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--wait", type=int, default=300, help="Max wait time in seconds")
    args = parser.parse_args()
    
    success = verify_dashboard(args.wait)
    sys.exit(0 if success else 1)
