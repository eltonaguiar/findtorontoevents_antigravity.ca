const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
  const b = await chromium.launch();
  const p = await (await b.newContext()).newPage();
  const errs = []; p.on('pageerror', e => errs.push(String(e.message).slice(0,60)));
  await p.goto('https://findtorontoevents.ca/', { waitUntil: 'load', timeout: 120000 });
  await p.waitForTimeout(9000);
  const m = await p.evaluate(() => document.querySelector('main').outerHTML);
  fs.writeFileSync('/tmp/normal_main.html', m);
  console.log('errors:', JSON.stringify(errs), 'main len:', m.length);
  for (const k of ['events-freshness','horizontal-promo-container','injected-promos','v0.5.2','id="events-grid"','Last updated','max-w-0 opacity-0','article','window.fixer']) console.log(k, m.split(k).length-1);
  await b.close();
})().catch(e => { console.error(e); process.exit(1); });
