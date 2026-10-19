const { chromium } = require('playwright');
const fs = require('fs');

// Ground truth for what the CURRENT live bundle renders inside <main> at
// hydration time: normal chunk timing, ALL data fetches blocked (events +
// metadata), site scripts blocked. Capture post-recovery DOM twice for stability.
(async () => {
  const b = await chromium.launch();
  const p = await (await b.newContext()).newPage();

  await p.route('**/*', route => {
    const u = route.request().url();
    if (/\/theme-(switcher|registry|animations)\.js|\/ai-assistant\.js|\/adsense-integration\.js/.test(u)) return route.abort();
    if (/githubusercontent\.com|pagead2\.googlesyndication|doubleclick\.net/.test(u)) return route.abort();
    if (/events\.json|metadata\.json/.test(u)) return route.abort();
    return route.continue();
  });

  const errs = [];
  p.on('pageerror', e => errs.push(String(e.message).slice(0, 80)));

  await p.goto('https://findtorontoevents.ca/', { waitUntil: 'load', timeout: 120000 });
  await p.waitForTimeout(2500);
  const m1 = await p.evaluate(() => (document.querySelector('main') || {}).outerHTML || 'NO MAIN');
  await p.waitForTimeout(3000);
  const m2 = await p.evaluate(() => (document.querySelector('main') || {}).outerHTML || 'NO MAIN');

  fs.writeFileSync('/tmp/gt_main_1.html', m1);
  fs.writeFileSync('/tmp/gt_main_2.html', m2);
  console.log('pageerrors:', JSON.stringify(errs));
  console.log('capture1 len:', m1.length, 'capture2 len:', m2.length, 'stable:', m1 === m2);
  await b.close();
})().catch(e => { console.error('HARNESS ERROR', e); process.exit(1); });
