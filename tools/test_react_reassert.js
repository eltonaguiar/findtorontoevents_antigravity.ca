/**
 * Probe whether React rewrites our counter value after applyFilters runs.
 * Strategy: load page, find counter span, set up a MutationObserver, manually
 * write "FOOBAR" to span, watch what happens.
 */
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const URL = 'https://findtorontoevents.ca/';
const LOCAL_HTML = path.join(__dirname, '..', 'TORONTOEVENTS_ANTIGRAVITY', 'index.html');

(async () => {
  const html = fs.readFileSync(LOCAL_HTML, 'utf8');
  const browser = await chromium.launch({ headless: true });
  const page = await (await browser.newContext()).newPage();
  await page.route(URL, async (r) => {
    if (r.request().resourceType() === 'document') {
      await r.fulfill({ status: 200, contentType: 'text/html; charset=utf-8', body: html });
    } else { await r.continue(); }
  });
  await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForFunction(() => !!document.getElementById('tbd-toggle'), { timeout: 30000 }).catch(()=>{});
  await page.waitForTimeout(7000);

  const result = await page.evaluate(async () => {
    const counter = document.querySelector('.glow-text.tabular-nums');
    if (!counter) return { error: 'no counter' };
    const original = (counter.textContent||'').trim();
    const events = [];

    const obs = new MutationObserver((muts) => {
      muts.forEach(m => events.push({
        type: m.type, target: m.target.nodeName,
        oldValue: m.oldValue, newText: (m.target.textContent||'').substring(0,30)
      }));
    });
    obs.observe(counter, { childList: true, subtree: true, characterData: true, characterDataOldValue: true });

    // Manually write a marker value
    counter.textContent = 'TESTMARKER';
    await new Promise(r => setTimeout(r, 500));
    const after500ms = counter.textContent;

    // Wait longer to see if React re-renders
    await new Promise(r => setTimeout(r, 3000));
    const after3500ms = counter.textContent;

    obs.disconnect();
    return { original, after500ms, after3500ms, mutations: events.slice(0,15) };
  });

  console.log(JSON.stringify(result, null, 2));
  await browser.close();
})();
