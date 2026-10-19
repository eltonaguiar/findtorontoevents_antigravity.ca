const { chromium } = require('playwright');
const fs = require('fs');

// On the PATCHED local page: delay Next chunks (pristine capture) then let
// hydration run with events delayed; diff full document to find where the
// remaining React mismatch lives (main should now be clean).
const BASE = 'http://localhost:5202';

(async () => {
  const b = await chromium.launch();
  const p = await (await b.newContext()).newPage();

  let eventsDelayed = 0;
  await p.route('**/*', async route => {
    const u = new URL(route.request().url());
    if (u.origin !== BASE) return route.continue();
    if (u.pathname === '/index.html') return route.continue();
    const target = 'https://findtorontoevents.ca' + u.pathname + u.search;
    if (/events\.json|metadata\.json|githubusercontent/.test(u.pathname + u.search) && eventsDelayed < 5) {
      eventsDelayed++;
      return new Promise(res => setTimeout(res, 30000));
    }
    if (/_next\/static\/chunks\/.*\.js$/.test(u.pathname)) {
      return new Promise(res => setTimeout(res, 1500));
    }
    try {
      const resp = await route.fetch({ url: target });
      return route.fulfill({ response: resp });
    } catch (e) { return route.abort(); }
  });

  const errs = [];
  p.on('pageerror', e => errs.push(String(e.message).slice(0, 70)));

  await p.goto(BASE + '/index.html', { waitUntil: 'domcontentloaded', timeout: 120000 });
  await p.waitForTimeout(800);
  const before = await p.evaluate(() => document.documentElement.outerHTML);
  await p.waitForTimeout(4000); // chunks (t~1500) + hydration + recovery
  const after = await p.evaluate(() => document.documentElement.outerHTML);

  fs.writeFileSync('/tmp/patch_before.html', before);
  fs.writeFileSync('/tmp/patch_after.html', after);
  console.log('errors:', JSON.stringify(errs));
  console.log('before:', before.length, 'after:', after.length);
  await b.close();
})().catch(e => { console.error('HARNESS ERROR', e); process.exit(1); });
