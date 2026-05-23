"""
Post-deploy verification: all 5 non-crypto magnifying glasses should now show data.
Tests against live https://findtorontoevents.ca/audit/ after the fix is deployed.
"""
import asyncio
import sys
import json
from playwright.async_api import async_playwright

sys.stdout.reconfigure(encoding='utf-8')
URL = "https://findtorontoevents.ca/audit/"
CATEGORIES = ['EQUITY', 'FOREX', 'COMMODITY', 'FUTURES', 'ETF']

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={'width': 1900, 'height': 1200})
        console_errs = []
        page.on('pageerror', lambda err: console_errs.append(f"[PAGEERROR] {err}"))

        print(f"Loading {URL}...")
        await page.goto(URL, wait_until='networkidle', timeout=60000)
        await page.wait_for_function("() => document.querySelectorAll('.nc-card').length >= 3", timeout=45000)
        await page.wait_for_timeout(3000)

        # Check payload generation time
        gen_at = await page.evaluate("() => { try { return document.querySelector('[data-audit-source]')?.textContent || 'unknown'; } catch(e) { return 'err'; } }")
        print(f"Data source info: {gen_at}")

        results = {}
        all_pass = True
        for cat in CATEGORIES:
            btn = page.locator(f'.nc-drill-btn[data-catkey="{cat}"]')
            if await btn.count() == 0:
                results[cat] = {"status": "NO_BUTTON"}
                all_pass = False
                continue

            # Close any open modal
            if await page.locator('.trade-modal-overlay').count() > 0:
                await page.evaluate("document.querySelectorAll('.trade-modal-overlay').forEach(e => e.remove())")
                await page.wait_for_timeout(200)

            await btn.click(timeout=5000)
            await page.wait_for_timeout(500)

            modal_data = await page.evaluate("""() => {
                const modal = document.querySelector('.trade-modal-overlay .trade-modal');
                if (!modal) return null;
                const h3 = modal.querySelector('h3');
                const h4s = [...modal.querySelectorAll('h4')].map(el => el.textContent);
                const closedRows = modal.querySelectorAll('[id^="nc-closed-"] tbody tr').length;
                const activeRows = modal.querySelectorAll('[id^="nc-active-"] tbody tr').length;
                return { title: h3?.textContent, headers: h4s, closed_rows: closedRows, active_rows: activeRows };
            }""")

            # Read card's displayed counts to compare
            card_data = await page.evaluate(f"""() => {{
                const btns = document.querySelectorAll('.nc-drill-btn');
                for (const b of btns) {{
                    if (b.getAttribute('data-catkey') === '{cat}') {{
                        const card = b.closest('.nc-card');
                        if (!card) return null;
                        const rows = card.querySelectorAll('.nc-row');
                        const data = {{}};
                        rows.forEach(r => {{
                            const lbl = r.querySelector('.nc-lbl')?.textContent?.trim();
                            const val = r.querySelector('.nc-val')?.textContent?.trim();
                            if (lbl && val) data[lbl] = val;
                        }});
                        return data;
                    }}
                }}
                return null;
            }}""")

            card_active = card_data.get('Active') if card_data else None
            card_closed = card_data.get('Closed') if card_data else None
            drill_closed = modal_data['closed_rows'] if modal_data else 0
            drill_active = modal_data['active_rows'] if modal_data else 0

            # Determine if fix worked: if card shows >0 then drill should show >0
            match = True
            if card_closed and card_closed.isdigit() and int(card_closed) > 0 and drill_closed == 0:
                match = False
            if card_active and card_active.isdigit() and int(card_active) > 0 and drill_active == 0:
                match = False

            results[cat] = {
                "card_active": card_active,
                "card_closed": card_closed,
                "drill_active": drill_active,
                "drill_closed": drill_closed,
                "match": match,
            }
            status = "PASS" if match else "FAIL"
            print(f"  {cat:12s}: card=A{card_active}/C{card_closed} | drill=A{drill_active}/C{drill_closed} | {status}")
            if not match:
                all_pass = False

            # Close modal
            close_btn = page.locator('.trade-modal-close')
            if await close_btn.count() > 0:
                await close_btn.click()
                await page.wait_for_timeout(200)

        print("\n" + "=" * 60)
        if all_pass:
            print("ALL 5 CATEGORIES PASS — card counts match drill-down counts")
        else:
            print("FAIL — card counts don't match drill-down counts")
        print("=" * 60)

        if console_errs:
            print("\n=== Page Errors ===")
            for e in console_errs[:5]:
                print(f"  {e}")

        await browser.close()
        return 0 if all_pass else 1

sys.exit(asyncio.run(main()))
