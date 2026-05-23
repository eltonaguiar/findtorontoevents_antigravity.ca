"""Playwright smoke test: High Conviction button + explainer panel.

Tests the template.html version (which has the new per-class edge filter
and explainer panel) served from a local HTTP server. Tests both desktop
viewport and Samsung Galaxy S20 mobile emulation.

Run: python scripts/test_hc_button_playwright.py

Assumes a local HTTP server is running at http://127.0.0.1:8765 with
audit_dashboard/ as the document root (so /template.html and /data/... resolve).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright, Page, ConsoleMessage

BASE = "http://127.0.0.1:8765/template.html"
OUT = Path("/tmp")


def run_test(label: str, viewport: dict, user_agent: str | None, is_mobile: bool) -> dict:
    results: dict = {"label": label, "viewport": viewport, "console_errors": [], "checks": {}}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context_args = {"viewport": viewport, "is_mobile": is_mobile, "has_touch": is_mobile}
        if user_agent:
            context_args["user_agent"] = user_agent
        context = browser.new_context(**context_args)
        page: Page = context.new_page()

        def on_console(msg: ConsoleMessage):
            if msg.type in ("error", "warning"):
                results["console_errors"].append(f"[{msg.type}] {msg.text[:200]}")
        page.on("console", on_console)
        page.on("pageerror", lambda err: results["console_errors"].append(f"[pageerror] {str(err)[:200]}"))

        print(f"\n=== {label} ({viewport['width']}x{viewport['height']}) ===")
        page.goto(BASE, wait_until="domcontentloaded", timeout=30000)
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        page.wait_for_timeout(1500)

        # 1. Button existence + visibility. The hero button is the one being wired.
        btn_hero = page.locator("#btn-conviction-picks-hero").first
        btn_exists = btn_hero.count() > 0
        results["checks"]["button_exists"] = btn_exists
        print(f"  button_exists: {btn_exists}")
        if not btn_exists:
            results["checks"]["FATAL"] = "button not found"
            page.screenshot(path=str(OUT / f"hc_{label}_no_button.png"), full_page=False)
            browser.close()
            return results

        btn_visible = btn_hero.is_visible()
        results["checks"]["button_visible"] = btn_visible
        print(f"  button_visible: {btn_visible}")

        # 2. Pre-click picks count
        pre_active_rows = page.locator("#tab-active .data-table tbody tr").count()
        results["checks"]["pre_click_active_rows"] = pre_active_rows
        print(f"  pre_click_active_rows: {pre_active_rows}")

        # 3. Explainer panel should be hidden before click
        panel = page.locator("#hc-explainer-panel")
        panel_exists = panel.count() > 0
        results["checks"]["panel_in_dom"] = panel_exists
        pre_panel_display = page.evaluate("() => { var p = document.getElementById('hc-explainer-panel'); return p ? getComputedStyle(p).display : 'MISSING'; }")
        results["checks"]["pre_click_panel_display"] = pre_panel_display
        print(f"  panel_in_dom: {panel_exists}, pre_click_display: {pre_panel_display}")

        # Pre-click screenshot
        page.screenshot(path=str(OUT / f"hc_{label}_before.png"), full_page=False)

        # 4. Click the HC button. Use force=true to bypass viewport clipping on mobile.
        try:
            btn_hero.scroll_into_view_if_needed(timeout=5000)
        except Exception:
            pass
        btn_hero.click(force=True, timeout=10000)
        page.wait_for_timeout(1500)

        # 5. Explainer panel should now be visible
        post_panel_display = page.evaluate("() => { var p = document.getElementById('hc-explainer-panel'); return p ? getComputedStyle(p).display : 'MISSING'; }")
        results["checks"]["post_click_panel_display"] = post_panel_display
        print(f"  post_click_panel_display: {post_panel_display}")

        # 6. Explainer should have populated class entries (7 asset classes)
        class_entries = page.locator("#hc-explainer-classes > div").count()
        results["checks"]["explainer_class_rows"] = class_entries
        print(f"  explainer_class_rows: {class_entries} (expected 7)")

        # 7. Check that _hcEdgeStrict flag is set
        hc_strict = page.evaluate("() => window._hcEdgeStrict === true")
        hc_conv = page.evaluate("() => window._convictionOnlyFilter === true")
        results["checks"]["hcEdgeStrict_flag"] = hc_strict
        results["checks"]["convictionOnlyFilter_flag"] = hc_conv
        print(f"  hcEdgeStrict={hc_strict}, convictionOnlyFilter={hc_conv}")

        # 8. Post-click row count (should be <= pre-count since filter is strict)
        post_active_rows = page.locator("#tab-active .data-table tbody tr").count()
        results["checks"]["post_click_active_rows"] = post_active_rows
        print(f"  post_click_active_rows: {post_active_rows} (was {pre_active_rows})")

        # 9. Verify per-class filter working: none of the displayed rows should be
        # COMMODITY/BOND/ETF/FUTURES asset classes (those are hidden by the strict gate).
        dead_rows = page.evaluate("""() => {
            var rows = document.querySelectorAll('#tab-active .data-table tbody tr');
            var violations = [];
            var dead = ['COMMODITY','BOND','ETF','FUTURES','COMMODITIES','BONDS'];
            for (var i = 0; i < rows.length; i++) {
                var r = rows[i];
                var txt = (r.textContent || '').toUpperCase();
                for (var j = 0; j < dead.length; j++) {
                    if (txt.indexOf(dead[j]) >= 0) { violations.push(dead[j]); break; }
                }
            }
            return violations.slice(0, 10);
        }""")
        results["checks"]["dead_class_rows_visible"] = dead_rows
        print(f"  dead_class_rows_visible: {dead_rows}")

        # Post-click screenshot
        page.screenshot(path=str(OUT / f"hc_{label}_after.png"), full_page=False)

        # 10. Close button test
        close_btn = page.locator("#hc-explainer-close")
        if close_btn.count() > 0:
            close_btn.click(force=True, timeout=5000)
            page.wait_for_timeout(800)
            closed_display = page.evaluate("() => getComputedStyle(document.getElementById('hc-explainer-panel')).display")
            results["checks"]["post_close_panel_display"] = closed_display
            print(f"  post_close_panel_display: {closed_display}")

        browser.close()
    return results


def main():
    tests = [
        {"label": "desktop_1920x1080", "viewport": {"width": 1920, "height": 1080}, "ua": None, "mobile": False},
        {"label": "galaxy_s20_412x915", "viewport": {"width": 412, "height": 915}, "ua": "Mozilla/5.0 (Linux; Android 11; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36", "mobile": True},
    ]

    all_results = []
    for t in tests:
        try:
            r = run_test(t["label"], t["viewport"], t["ua"], t["mobile"])
        except Exception as e:
            r = {"label": t["label"], "FATAL": str(e)}
        all_results.append(r)

    print("\n\n=== SUMMARY ===")
    print(json.dumps(all_results, indent=2, default=str))

    # Overall pass/fail
    pass_count = 0
    fail_count = 0
    for r in all_results:
        c = r.get("checks", {})
        if (c.get("button_exists") and c.get("button_visible") and
            c.get("post_click_panel_display") == "block" and
            c.get("explainer_class_rows", 0) == 7 and
            c.get("hcEdgeStrict_flag") is True and
            (not c.get("dead_class_rows_visible", []))):
            pass_count += 1
        else:
            fail_count += 1
    print(f"\n{pass_count}/{len(all_results)} viewports PASS, {fail_count} FAIL")
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
