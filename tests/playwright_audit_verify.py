"""Playwright verification of audit dashboard fixes."""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')

from playwright.sync_api import sync_playwright
import time

results = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1920, "height": 1080})

    errors = []
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    page.on("pageerror", lambda err: errors.append(str(err)))

    page.goto("file:///E:/findtorontoevents_antigravity.ca/audit_dashboard/index.html", timeout=60000)
    page.wait_for_load_state("domcontentloaded", timeout=30000)
    time.sleep(5)

    # TEST 1: No buildStratDrillDown crash
    js_errors = [e for e in errors if "buildStratDrillDown" in e]
    results.append(("No buildStratDrillDown crash", len(js_errors) == 0, str(js_errors[:2]) if js_errors else "clean"))

    # TEST 2: Toast system exists
    toast_exists = page.locator(".toast-container").count() > 0
    results.append(("Toast container exists", toast_exists, ""))

    # TEST 3: Systems table renders
    sys_rows = page.locator("tr").count()
    results.append(("Systems table renders", sys_rows > 10, f"{sys_rows} rows"))

    # TEST 4: Copy trader picks visible
    body = page.text_content("body")
    copy_count = body.count("copy_hl_")
    results.append(("Copy trader picks visible", copy_count > 0, f"{copy_count} mentions"))

    # TEST 5: Clone picks visible
    clone_count = body.count("clone_")
    results.append(("Clone picks visible", clone_count > 0, f"{clone_count} mentions"))

    # TEST 6: Dashboard data loaded
    scores = page.evaluate("""() => {
        const data = window.DASHBOARD_DATA;
        if (!data || !data.picks) return {active: 0, scores: []};
        const active = data.picks.active || [];
        const closed = (data.picks.recent_closed || []);
        const sc = active.map(p => p.score).filter(s => s != null);
        return {
            active: active.length,
            closed: closed.length,
            systems: (data.systems || []).length,
            scores_count: sc.length,
            score_100_count: sc.filter(s => s === 100).length,
            avg_score: sc.length ? (sc.reduce((a,b) => a+b, 0) / sc.length).toFixed(1) : "0"
        };
    }""")
    results.append(("Dashboard data loaded", scores["active"] > 0,
        f'{scores["active"]} active, {scores["closed"]} closed, {scores["systems"]} systems'))
    results.append(("Scores computed", scores["scores_count"] > 0,
        f'{scores["scores_count"]} scored, avg={scores["avg_score"]}'))

    # TEST 7: Score-performance correlation
    corr = page.evaluate("""() => {
        const data = window.DASHBOARD_DATA;
        if (!data || !data.picks) return {insufficient: true};
        const closed = data.picks.recent_closed || [];
        if (closed.length < 10) return {insufficient: true, count: closed.length};
        const q = {high: [], mid: [], low: []};
        closed.forEach(p => {
            const s = p.score || 0;
            const pnl = parseFloat(p.pnl_pct) || 0;
            if (s >= 70) q.high.push(pnl);
            else if (s >= 40) q.mid.push(pnl);
            else q.low.push(pnl);
        });
        const avg = arr => arr.length ? (arr.reduce((a,b) => a+b, 0) / arr.length).toFixed(2) : "N/A";
        const wr = arr => arr.length ? (arr.filter(x => x > 0).length / arr.length * 100).toFixed(1) : "N/A";
        return {
            high: {n: q.high.length, wr: wr(q.high), pnl: avg(q.high)},
            mid: {n: q.mid.length, wr: wr(q.mid), pnl: avg(q.mid)},
            low: {n: q.low.length, wr: wr(q.low), pnl: avg(q.low)}
        };
    }""")
    if "insufficient" not in corr:
        h, m, l = corr["high"], corr["mid"], corr["low"]
        results.append(("Score-perf correlation", True,
            f'High(>=70): {h["n"]}p WR={h["wr"]}% PnL={h["pnl"]}% | '
            f'Mid(40-70): {m["n"]}p WR={m["wr"]}% PnL={m["pnl"]}% | '
            f'Low(<40): {l["n"]}p WR={l["wr"]}% PnL={l["pnl"]}%'))
    else:
        results.append(("Score-perf correlation", False, f'Only {corr.get("count", 0)} closed'))

    # TEST 8: Copy trader performance
    ct = page.evaluate("""() => {
        const data = window.DASHBOARD_DATA;
        if (!data || !data.picks) return {};
        const all = [...(data.picks.active || []), ...(data.picks.recent_closed || [])];
        const ct = all.filter(p => (p.strategy || "").includes("copy_hl_") || (p.source_system || "").includes("copy_trader"));
        const cl = all.filter(p => (p.strategy || "").includes("clone_"));
        const stats = (arr) => {
            const c = arr.filter(p => p.pnl_pct != null);
            const pnls = c.map(p => parseFloat(p.pnl_pct) || 0);
            return {
                total: arr.length, closed: c.length,
                wr: c.length ? (pnls.filter(x => x > 0).length / c.length * 100).toFixed(1) : "N/A",
                pnl: pnls.length ? (pnls.reduce((a,b) => a+b, 0) / pnls.length).toFixed(2) : "N/A"
            };
        };
        return {copy: stats(ct), clone: stats(cl)};
    }""")
    cp = ct.get("copy", {})
    cl = ct.get("clone", {})
    results.append(("Copy trader data", cp.get("total", 0) > 0,
        f'COPY: {cp.get("total",0)} total, {cp.get("closed",0)} closed, WR={cp.get("wr","?")}%, PnL={cp.get("pnl","?")}%'))
    results.append(("Clone data", cl.get("total", 0) > 0,
        f'CLONE: {cl.get("total",0)} total, {cl.get("closed",0)} closed, WR={cl.get("wr","?")}%, PnL={cl.get("pnl","?")}%'))

    # TEST 9: No critical JS errors
    critical = [e for e in errors if "ReferenceError" in e or "TypeError" in e or "SyntaxError" in e]
    results.append(("No critical JS errors", len(critical) == 0, "; ".join(critical[:3]) if critical else "clean"))

    # TEST 10: Non-Crypto Performance Panel renders
    nc_panel = page.evaluate("""() => {
        const data = window.DASHBOARD_DATA;
        if (!data || !data.summary) return {no_summary: true};
        const ncPerf = data.summary.non_crypto_performance || {};
        const cats = ncPerf.categories || {};
        const agg = ncPerf.aggregate || {};
        const result = {aggregate: agg, categories: {}};
        for (const [k, v] of Object.entries(cats)) {
            if (v.active > 0 || v.closed > 0) result.categories[k] = v;
        }
        return result;
    }""")
    nc_cats = nc_panel.get("categories", {})
    nc_agg = nc_panel.get("aggregate", {})
    has_nc = len(nc_cats) > 0
    results.append(("Non-Crypto categories present", has_nc,
        f'{len(nc_cats)} categories: {", ".join(nc_cats.keys())}'))
    results.append(("Non-Crypto aggregate stats", nc_agg.get("resolved", 0) > 0,
        f'active={nc_agg.get("active",0)}, closed={nc_agg.get("closed",0)}, '
        f'WR={nc_agg.get("win_rate","N/A")}%, PnL={nc_agg.get("total_pnl_pct","N/A")}%'))

    # TEST 11: Equities have closed picks (not just "No closed picks yet")
    equity_cat = nc_cats.get("EQUITY", nc_cats.get("STOCK", {}))
    results.append(("Equities have closed history", equity_cat.get("closed", 0) > 0,
        f'active={equity_cat.get("active",0)}, closed={equity_cat.get("closed",0)}, '
        f'wins={equity_cat.get("wins",0)}, losses={equity_cat.get("losses",0)}'))

    # TEST 12: Forex has closed picks
    forex_cat = nc_cats.get("FOREX", {})
    results.append(("Forex has closed history", forex_cat.get("closed", 0) > 0,
        f'active={forex_cat.get("active",0)}, closed={forex_cat.get("closed",0)}, '
        f'wins={forex_cat.get("wins",0)}, losses={forex_cat.get("losses",0)}'))

    # TEST 13: Commodity/ETF categories exist
    commodity_cat = nc_cats.get("COMMODITY", {})
    etf_cat = nc_cats.get("ETF", {})
    results.append(("Commodity data exists", commodity_cat.get("active", 0) > 0 or commodity_cat.get("closed", 0) > 0,
        f'active={commodity_cat.get("active",0)}, closed={commodity_cat.get("closed",0)}'))
    results.append(("ETF data exists", etf_cat.get("active", 0) > 0 or etf_cat.get("closed", 0) > 0,
        f'active={etf_cat.get("active",0)}, closed={etf_cat.get("closed",0)}'))

    # TEST 14: Non-crypto panel HTML renders on page
    nc_html = page.locator("#non-crypto-panel").inner_html()
    has_nc_html = "Non-Crypto Performance" in nc_html or "nc-card" in nc_html
    results.append(("NC panel HTML rendered", has_nc_html,
        f'{len(nc_html)} chars' if nc_html else 'empty'))

    page.screenshot(path="tests/screenshots/audit_fixed_verify.png", full_page=False)

    # ── MOBILE VIEWPORT TEST ──
    mobile_page = browser.new_page(viewport={"width": 375, "height": 812})  # iPhone SE
    mobile_page.goto("file:///E:/findtorontoevents_antigravity.ca/audit_dashboard/index.html", timeout=60000)
    mobile_page.wait_for_load_state("domcontentloaded", timeout=30000)
    time.sleep(5)

    # TEST 15: Mobile loads without crash
    mobile_body = mobile_page.text_content("body") or ""
    results.append(("Mobile viewport loads", len(mobile_body) > 100, f'{len(mobile_body)} chars'))

    # TEST 16: Mobile NC panel renders
    mobile_nc = mobile_page.locator("#non-crypto-panel").inner_html()
    results.append(("Mobile NC panel renders", len(mobile_nc) > 10,
        f'{len(mobile_nc)} chars'))

    # TEST 17: Mobile no critical JS errors
    # (errors list is shared from page.on above - mobile runs after desktop)

    mobile_page.screenshot(path="tests/screenshots/audit_mobile_verify.png", full_page=False)
    mobile_page.close()

    browser.close()

print("=" * 80)
print("PLAYWRIGHT VERIFICATION RESULTS")
print("=" * 80)
for name, passed, detail in results:
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] {name}: {detail}")
print(f"\nTotal: {sum(1 for _, p, _ in results if p)}/{len(results)} passed")
