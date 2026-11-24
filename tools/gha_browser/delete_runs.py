#!/usr/bin/env python3
"""Delete phantom queued GitHub runs via the logged-in browser UI (CDP 9222).

Usage: delete_runs.py <run_id> [<run_id> ...] [--dry-run]
"""
import json
import sys
import time

from playwright.sync_api import sync_playwright

REPO = "eltonaguiar/findtorontoevents_antigravity.ca"


def delete_run(page, run_id):
    url = f"https://github.com/{REPO}/actions/runs/{run_id}"
    page.goto(url, wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle")
    if "Page not found" in page.title():
        return {"id": run_id, "result": "not-found"}

    btn = page.locator('button[aria-label="More options"]').first
    if btn.count() == 0:
        btn = page.locator("summary[aria-label]").first
    if btn.count() == 0:
        page.screenshot(path=f"/tmp/kilo/gha_browser/fail_{run_id}.png")
        return {"id": run_id, "result": "no-kebab"}
    btn.click()
    time.sleep(0.5)

    item = page.get_by_role("menuitem", name="Delete workflow run")
    if item.count() == 0:
        item = page.locator("a,button", has_text="Delete workflow run").first
    if item.count() == 0:
        page.screenshot(path=f"/tmp/kilo/gha_browser/fail_{run_id}.png")
        return {"id": run_id, "result": "no-menu-item"}
    item.click()
    time.sleep(0.5)

    confirm = page.locator('form[method="post"] button, [role="dialog"] button, dialog button',
                           has_text="Delete workflow run").last
    try:
        confirm.click(timeout=3000)
    except Exception:
        pass
    time.sleep(1.0)
    page.wait_for_load_state("networkidle")

    gone = page.locator("text=Page not found").count() > 0 or "not found" in page.title().lower()
    return {"id": run_id, "result": "deleted" if gone else "check-manually"}


def main():
    ids = [a for a in sys.argv[1:] if a.isdigit()]
    dry = "--dry-run" in sys.argv
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://localhost:9222")
        ctx = browser.contexts[0]
        page = ctx.new_page()
        out = []
        for rid in ids:
            if dry:
                out.append({"id": rid, "result": "dry"})
                continue
            out.append(delete_run(page, rid))
            print(json.dumps(out[-1]), flush=True)
        page.close()
        browser.close()
    ok = sum(1 for r in out if r["result"] == "deleted")
    print(json.dumps({"deleted": ok, "total": len(out)}))


if __name__ == "__main__":
    main()
