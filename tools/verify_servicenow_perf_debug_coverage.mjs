#!/usr/bin/env node
/**
 * Standalone Playwright verification for the performance / session-debugging
 * coverage added to the ServiceNow JavaScript reference page.
 *
 * Asserts that:
 *   - the new sections and their content actually render,
 *   - every TOC entry still resolves to a real section id,
 *   - the new tables have the expected number of rows,
 *   - the page produces zero page/console errors,
 *   - the page does not overflow horizontally at phone width (390 px).
 *
 * Usage: node tools/verify_servicenow_perf_debug_coverage.mjs
 * Exit code: 0 = all checks pass, 1 = at least one FAIL.
 */
import { chromium } from 'playwright';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const HTML_PATH = join(__dirname, '..', 'findtorontoevents.ca', 'servicenow', 'javascript', 'index.html');
const fileUrl = `file://${HTML_PATH}`;

const REQUIRED_TEXT = [
  // clock (response time indicator) + long-running transaction timer
  'Response Time Indicator',
  'glide.ui.response_time',
  'glide.ui.transaction.long_response.time',
  'long-running transaction timer',
  // tool breadcrumbs
  'Active Transactions (All Nodes)',
  'Transaction Cancellation Log',
  'Client Transactions',
  'maximum execution time exceeded',
  'Debug Metric Statistics',
  // session debugging: what + where
  'what to switch on, and why',
  'where the debug output lands',
  'glide.debugger.log.ui',
  'Disable All',
  // scenarios
  'Worked example — the Incident form takes 12 seconds to open',
  'Scenario playbooks — runaway loop vs very long latency',
  'Client script in an infinite loop',
  'Server script in an infinite loop',
  // client vs server test/tune matrix
  'Test and tune: client script vs server script',
  'The A/B trick',
];

const NEW_HEADINGS = [
  'Test and tune: client script vs server script',
  'Session debugging — what to switch on, and why',
  'Which page do I check? — where the debug output lands',
  'Worked example — the Incident form takes 12 seconds to open',
  'Scenario playbooks — runaway loop vs very long latency',
];

const results = [];
const check = (name, ok, detail = '') => results.push({ name, ok, detail });

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });

const pageErrors = [];
const consoleErrors = [];
page.on('pageerror', (e) => pageErrors.push(e.message));
page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text()); });

await page.goto(fileUrl, { waitUntil: 'domcontentloaded' });

// 1. No runtime errors
check('zero page errors', pageErrors.length === 0, pageErrors.join(' | '));
check('zero console errors', consoleErrors.length === 0, consoleErrors.join(' | '));

// 2. New headings render
for (const h of NEW_HEADINGS) {
  const n = await page.locator(`h3:has-text(${JSON.stringify(h)})`).count();
  check(`heading renders: ${h}`, n >= 1, `count=${n}`);
}

// 3. Required strings present somewhere in the rendered text
const bodyText = await page.locator('body').innerText();
for (const s of REQUIRED_TEXT) {
  check(`content present: ${s}`, bodyText.includes(s), '');
}

// 4. Every TOC link resolves to a real target
const tocLinks = await page.locator('nav.toc a[href^="#"]').evaluateAll((els) =>
  els.map((a) => a.getAttribute('href').slice(1)),
);
check('TOC has entries', tocLinks.length >= 40, `count=${tocLinks.length}`);
const missing = await page.evaluate((ids) => ids.filter((id) => !document.getElementById(id)), tocLinks);
check('TOC anchors all resolve', missing.length === 0, `missing=${missing.join(',')}`);

// 5. Jump navigation still works (click F2 in the TOC)
await page.locator('nav.toc a[href="#appendix-diagnosing"]').first().click();
const hash = await page.evaluate(() => location.hash);
check('TOC click sets #appendix-diagnosing', hash === '#appendix-diagnosing', `hash=${hash}`);

// 6. Row counts of the three new/changed tables inside Appendix F / F2
const rowCounts = await page.evaluate(() => {
  const countRows = (h3Text) => {
    const h3 = [...document.querySelectorAll('h3')].find((h) => h.textContent.includes(h3Text));
    if (!h3) return -1;
    let n = h3.nextElementSibling;
    while (n && !['TABLE', 'OL', 'DIV'].includes(n.tagName)) n = n.nextElementSibling;
    if (!n) return -1;
    const tbl = n.tagName === 'TABLE' ? n : n.querySelector('table');
    if (tbl) return tbl.querySelectorAll('tbody tr').length;
    if (n.tagName === 'OL') return n.querySelectorAll(':scope > li').length;
    return -1;
  };
  return {
    testTune: countRows('Test and tune'),
    scenarios: countRows('Scenario playbooks'),
    worked: countRows('Worked example'),
    breadcrumb: (() => {
      const h3 = [...document.querySelectorAll('h3')].find((h) => h.textContent.includes('Where to look'));
      if (!h3) return -1;
      let n = h3.nextElementSibling;
      while (n && !n.querySelector('table')) n = n.nextElementSibling;
      const tbl = n ? n.querySelector('table') : null;
      return tbl ? tbl.querySelectorAll('tbody tr').length : -1;
    })(),
  };
});
check('test & tune table = 4 rows', rowCounts.testTune === 4, `got=${rowCounts.testTune}`);
check('scenario playbook table = 5 rows', rowCounts.scenarios === 5, `got=${rowCounts.scenarios}`);
check('worked example list = 9 steps', rowCounts.worked === 9, `got=${rowCounts.worked}`);
check('Appendix F breadcrumb table = 9 rows', rowCounts.breadcrumb === 9, `got=${rowCounts.breadcrumb}`);

// 7. Knowledge checks in F2 (3 original + 3 new)
const f2Details = await page.evaluate(() => {
  const sec = document.getElementById('appendix-diagnosing');
  return sec ? sec.querySelectorAll('.kcheck details').length : 0;
});
check('F2 knowledge checks = 6', f2Details === 6, `got=${f2Details}`);

// 8. Horizontal overflow at phone width
await page.setViewportSize({ width: 390, height: 844 });
await page.waitForTimeout(250);
const overflow = await page.evaluate(() => ({
  doc: document.documentElement.scrollWidth,
  client: document.documentElement.clientWidth,
}));
check('no horizontal overflow at 390px', overflow.doc <= overflow.client + 2,
  `scrollWidth=${overflow.doc} clientWidth=${overflow.client}`);

// 9. Still no errors after resize/interactions
check('zero page errors (final)', pageErrors.length === 0, pageErrors.join(' | '));

await browser.close();

let pass = 0, fail = 0;
for (const r of results) {
  if (r.ok) { pass++; console.log(`PASS  ${r.name}`); }
  else { fail++; console.log(`FAIL  ${r.name} ${r.detail}`); }
}
console.log(`\n${pass}/${results.length} checks passed${fail ? `, ${fail} FAILED` : ''}`);
if (fail) process.exitCode = 1;
