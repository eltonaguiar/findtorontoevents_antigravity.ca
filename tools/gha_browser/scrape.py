#!/usr/bin/env python3
"""Scrape GitHub Actions pages through a logged-in Chrome (CDP port 9222).

Avoids the REST API entirely — HTML scraping only.

Usage:
  scrape.py wait-login [timeout_s]   wait until github.com login cookie appears
  scrape.py login-status             print login state
  scrape.py workflows                list workflows from /actions sidebar
  scrape.py runs <query> [--pages N] scrape /actions?query=... run list rows
                                     e.g. runs "is:queued" / "is:in_progress"
                                          runs "is:failure created:>2026-11-09"
  scrape.py wf-history <wf-file> [--pages N]   per-workflow run history
  scrape.py run-detail <run-id>      one run page: jobs + step results
  scrape.py raw <url>                dump visible text of any page
"""
import json
import re
import sys
import time
import urllib.parse

from playwright.sync_api import sync_playwright

REPO = "eltonaguiar/findtorontoevents_antigravity.ca"
BASE = f"https://github.com/{REPO}"
CDP = "http://localhost:9222"


def attach(p):
    browser = p.chromium.connect_over_cdp(CDP)
    ctx = browser.contexts[0]
    return browser, ctx


def login_state(ctx):
    cookies = {c["name"]: c for c in ctx.cookies("https://github.com")}
    has = "user_session" in cookies or cookies.get("logged_in", {}).get("value") == "yes"
    user = None
    return has, user


def wait_login(ctx, timeout_s=600):
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        has, _ = login_state(ctx)
        if has:
            return True
        time.sleep(3)
    return False


ROW_JS = """
() => {
  const seen = new Map();
  document.querySelectorAll('a[href*="/actions/runs/"]').forEach(a => {
    const m = a.getAttribute('href').match(/\\/actions\\/runs\\/(\\d+)/);
    if (!m) return;
    const id = m[1];
    if (seen.has(id)) return;
    let row = a;
    for (let i = 0; i < 6 && row.parentElement; i++) {
      row = row.parentElement;
      if (row.querySelector && row.querySelector('relative-time')) break;
    }
    const rt = row.querySelector ? row.querySelector('relative-time') : null;
    const svgs = row.querySelectorAll ? row.querySelectorAll('svg') : [];
    const icons = Array.from(svgs).map(s => s.getAttribute('class') || '');
    const aria = Array.from(svgs).map(s => s.getAttribute('aria-label') || '').filter(Boolean);
    const sr = Array.from(row.querySelectorAll ? row.querySelectorAll('.sr-only, .visually-hidden') : [])
      .map(e => e.textContent.trim()).filter(Boolean);
    const branchA = row.querySelector ? row.querySelector('a[href*="/tree/"]') : null;
    const titleA = Array.from(row.querySelectorAll ? row.querySelectorAll('a') : [])
      .find(x => /\\/actions\\/runs\\/\\d+$/.test(x.getAttribute('href') || ''));
    const text = (row.innerText || '').split('\\n').map(s => s.trim()).filter(Boolean);
    seen.set(id, {
      id,
      title: titleA ? titleA.textContent.trim() : '',
      title_aria: titleA ? (titleA.getAttribute('aria-label') || titleA.getAttribute('title') || '') : '',
      when: rt ? rt.getAttribute('datetime') : '',
      icons, aria, sr,
      branch: branchA ? branchA.textContent.trim() : '',
      row_text: text.slice(0, 8),
    });
  });
  return Array.from(seen.values());
}
"""


def classify(row):
    sr = " ".join(row.get("sr", [])).lower()
    txt = " ".join(row.get("row_text", [])).lower()
    blob = " ".join(row.get("icons", []) + row.get("aria", [])).lower() + " " + sr + " " + txt
    if "queued:" in sr or txt.rstrip().endswith("queued"):
        return "queued"
    if "currently running" in sr or "in progress" in txt:
        return "in_progress"
    if "waiting" in sr or "waiting" in txt:
        return "waiting"
    if "cancel" in blob:
        return "cancelled"
    if "octicon-x" in blob or "failure" in blob or "failed" in blob:
        return "failure"
    if "octicon-check" in blob or "success" in blob:
        return "success"
    if "octicon-skip" in blob or "skipped" in blob:
        return "skipped"
    return "?"


def scrape_runs(page, query, pages=1):
    out = []
    for pg in range(1, pages + 1):
        url = f"{BASE}/actions?query={urllib.parse.quote(query)}&page={pg}"
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle")
        rows = page.evaluate(ROW_JS)
        if not rows:
            break
        for r in rows:
            r["status"] = classify(r)
            r["src_query"] = query
        out.extend(rows)
        if len(rows) < 25:
            break
    return out


def scrape_workflows(page):
    page.goto(f"{BASE}/actions", wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle")
    return page.evaluate("""
    () => Array.from(document.querySelectorAll('a[href*="/actions/workflows/"]')).map(a => ({
      file: (a.getAttribute('href') || '').split('/actions/workflows/')[1] || '',
      name: a.textContent.trim(),
    })).filter(x => x.file)
    """)


def scrape_wf_history(page, wf_file, pages=1):
    out = []
    for pg in range(1, pages + 1):
        url = f"{BASE}/actions/workflows/{wf_file}?page={pg}"
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle")
        rows = page.evaluate(ROW_JS)
        if not rows:
            break
        for r in rows:
            r["status"] = classify(r)
        out.extend(rows)
        if len(rows) < 25:
            break
    return out


def scrape_run_detail(page, run_id):
    page.goto(f"{BASE}/actions/runs/{run_id}", wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle")
    return page.evaluate("""
    () => {
      const jobs = [];
      document.querySelectorAll('div[class*="CheckStep"], details, .js-build-list-item, [data-testid="job-name"]').forEach(() => {});
      const text = document.body.innerText;
      return {url: location.href, text: text.slice(0, 12000)};
    }
    """)


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return
    cmd, rest = args[0], args[1:]
    with sync_playwright() as p:
        browser, ctx = attach(p)
        if cmd == "login-status":
            has, _ = login_state(ctx)
            print(json.dumps({"logged_in": has}))
        elif cmd == "wait-login":
            to = int(rest[0]) if rest else 600
            ok = wait_login(ctx, to)
            print(json.dumps({"logged_in": ok}))
            sys.exit(0 if ok else 1)
        elif cmd == "workflows":
            page = ctx.new_page()
            print(json.dumps(scrape_workflows(page), indent=1))
            page.close()
        elif cmd == "runs":
            query = rest[0]
            pages = 1
            if "--pages" in rest:
                pages = int(rest[rest.index("--pages") + 1])
            page = ctx.new_page()
            print(json.dumps(scrape_runs(page, query, pages)))
            page.close()
        elif cmd == "wf-history":
            wf = rest[0]
            pages = 1
            if "--pages" in rest:
                pages = int(rest[rest.index("--pages") + 1])
            page = ctx.new_page()
            print(json.dumps(scrape_wf_history(page, wf, pages)))
            page.close()
        elif cmd == "run-detail":
            page = ctx.new_page()
            print(json.dumps(scrape_run_detail(page, rest[0]), indent=1))
            page.close()
        elif cmd == "raw":
            page = ctx.new_page()
            page.goto(rest[0], wait_until="domcontentloaded")
            page.wait_for_load_state("networkidle")
            print(page.inner_text("body")[:20000])
            page.close()
        else:
            print(__doc__)
        browser.close()


if __name__ == "__main__":
    main()
