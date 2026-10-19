const { chromium } = require('playwright');

// JS-error scan for the three public surfaces: /, /audit/, /weather/.
// Usage: node tools/qa/js_error_scan.js [--extra]
//   --extra also exercises homepage filter chips + audit tab switches.
const EXTRA = process.argv.includes('--extra');
const ONLY = process.argv.find(a => ['homepage', 'audit', 'weather'].includes(a));

(async () => {
  const b = await chromium.launch();
  const targets = [
    ['homepage', 'https://findtorontoevents.ca/', 12000],
    ['audit', 'https://findtorontoevents.ca/audit/', 16000],
    ['weather', 'https://findtorontoevents.ca/weather/', 8000],
  ];

  for (const [label, url, settle] of targets) {
    if (ONLY && label !== ONLY) continue;
    const p = await (await b.newContext()).newPage();
    const pageErrs = [], consErr = [], consWarn = [], failedReq = [], enhWarns = [];
    p.on('pageerror', e => pageErrs.push(String(e.message).slice(0, 200)));
    p.on('console', m => {
      const txt = m.text();
      if (m.type() === 'error') consErr.push(txt.slice(0, 200));
      if (m.type() === 'warning') consWarn.push(txt.slice(0, 160));
      if (txt.includes('[Enhancements]')) enhWarns.push(txt.slice(0, 160));
    });
    p.on('requestfailed', r => failedReq.push(r.url().slice(0, 120) + ' :: ' + (r.failure() && r.failure().errorText)));
    p.on('response', r => { if (r.status() >= 400) failedReq.push('HTTP ' + r.status() + ' ' + r.url().slice(0, 120)); });

    const t0 = Date.now();
    const resp = await p.goto(url, { waitUntil: 'load', timeout: 120000 });
    const loadMs = Date.now() - t0;
    await p.waitForTimeout(settle);

    if (label === 'homepage' && EXTRA) {
      // scroll to trigger lazy loads, then click a couple of filter chips
      await p.evaluate(async () => {
        for (let y = 0; y < document.body.scrollHeight; y += 700) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 120)); }
      });
      await p.waitForTimeout(1500);
      for (const sel of ['.filter-chip', '[data-filter]', 'button']) {
        try { await p.click(sel, { timeout: 900 }); await p.waitForTimeout(800); break; } catch (e) {}
      }
    }

    if (label === 'audit') {
      const tabSel = ['[data-tab=active]', '[data-tab=closed]', '[data-tab=overview]', '[data-tab=smart]'];
      if (EXTRA) tabSel.push('[data-tab=crypto]', '[data-tab=stocks]');
      for (const sel of tabSel) {
        try { await p.click(sel, { timeout: 2500 }); await p.waitForTimeout(1100); } catch (e) {}
      }
      // wait for dashboard-data-loaded style renders
      await p.waitForTimeout(4000);
    }

    const summary = await p.evaluate(() => {
      const s = {};
      s.bodyChars = document.body.innerText.length;
      s.title = document.title;
      if (location.pathname.startsWith('/audit')) {
        const oprt = document.getElementById('enh-operator-review-today');
        s.operatorReviewPanel = !!oprt;
        s.operatorReviewChars = oprt ? oprt.innerText.length : 0;
        const rows = document.querySelectorAll('#active-picks-table tbody tr, [data-pick-row], .pick-row');
        s.activePickRows = rows.length;
        s.stalePnlCells = [...document.querySelectorAll('td, .pnl, .pnl-pct')]
          .filter(el => /^\s*0\.0+%\s*$/.test(el.innerText)).length;
      }
      if (location.pathname.startsWith('/weather')) {
        s.hourlyCells = document.querySelectorAll('#hourly .h-item').length;
        s.allowFullscrIframes = document.querySelectorAll('iframe[allowfullscreen]').length;
      }
      if (location.pathname === '/') {
        s.eventLinks = document.querySelectorAll('a[href*="/event"], .event-card, .card').length;
      }
      return s;
    });

    console.log(JSON.stringify({
      label, http: resp && resp.status(), loadMs, ...summary,
      pageErrors: pageErrs.length, pageErrsSample: pageErrs.slice(0, 8),
      consoleErrors: consErr.length, consoleErrSample: consErr.slice(0, 8),
      failedRequests: failedReq.length, failedReqSample: failedReq.slice(0, 8),
      enhWarnings: enhWarns.length, enhWarnSample: enhWarns.slice(0, 6),
      warnings: consWarn.length, warnSample: consWarn.slice(0, 5),
    }, null, 1));
    await p.close();
  }
  await b.close();
})().catch(e => { console.error('HARNESS ERROR', e); process.exit(1); });
