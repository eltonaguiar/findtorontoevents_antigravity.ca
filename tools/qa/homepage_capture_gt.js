const { chromium } = require('playwright');
const fs = require('fs');

// Capture the current bundle's render of <main> as the exact hydration target:
// events+metadata fetches delayed 30s (React still in loading state), legacy
// promo injector NOT yet fired (its hard fallback is 5s -> capture at 2.5s/4s).
(async () => {
  const b = await chromium.launch();
  const p = await (await b.newContext()).newPage();

  const delayMatches = [/events\.json/, /metadata\.json/, /githubusercontent\.com/];
  await p.route('**/*', route => {
    const u = route.request().url();
    if (delayMatches.some(re => re.test(u))) {
      return new Promise(res => setTimeout(() => res(route.continue().catch(() => {})), 30000));
    }
    return route.continue();
  });

  const errs = [];
  p.on('pageerror', e => errs.push(String(e.message).slice(0, 60)));

  await p.goto('https://findtorontoevents.ca/', { waitUntil: 'load', timeout: 120000 });
  await p.waitForTimeout(2500);
  const m1 = await p.evaluate(() => document.querySelector('main').outerHTML);
  await p.waitForTimeout(1500); // t=4.0s, still < 5s legacy fallback
  const m2 = await p.evaluate(() => document.querySelector('main').outerHTML);

  fs.writeFileSync('/tmp/gt2_main_1.html', m1);
  fs.writeFileSync('/tmp/gt2_main_2.html', m2);
  console.log('pageerrors:', JSON.stringify(errs));
  console.log('c1:', m1.length, 'c2:', m2.length, 'stable:', m1 === m2);
  console.log('sanity: injected-promos in c2 =', m2.split('injected-promos').length - 1,
    '| grid skeleton =', m2.split('animate-pulse').length - 1,
    '| v0.5.2 =', m2.split('v0.5.2').length - 1);
  await b.close();
})().catch(e => { console.error('HARNESS ERROR', e); process.exit(1); });
