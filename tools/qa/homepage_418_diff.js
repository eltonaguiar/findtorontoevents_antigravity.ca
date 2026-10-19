const { chromium } = require('playwright');
const fs = require('fs');

// Captures the homepage body (a) pristine, before the Next chunks run (scripts
// delayed), and (b) right after React's hydration attempt. Diffs them server-
// side; external noise sources (site scripts, events fetch, ads) are blocked.
(async () => {
  const b = await chromium.launch();
  const p = await (await b.newContext()).newPage();

  let eventsDelayed = 0;
  await p.route('**/*', route => {
    const u = route.request().url();
    if (/\/theme-(switcher|registry|animations)\.js|\/ai-assistant\.js|\/adsense-integration\.js/.test(u)) return route.abort();
    if (/githubusercontent\.com|pagead2\.googlesyndication|doubleclick\.net/.test(u)) return route.abort();
    // delay events.json long enough to snapshot the post-hydration DOM
    if (/events\.json/.test(u) && eventsDelayed < 4) {
      eventsDelayed++;
      return new Promise(res => setTimeout(() => res(route.continue().catch(() => {})), 30000));
    }
    if (/_next\/static\/chunks\/.*\.js$/.test(u)) {
      return new Promise(res => setTimeout(() => res(route.continue().catch(() => {})), 1800));
    }
    return route.continue();
  });

  const errs = [];
  p.on('pageerror', e => errs.push(String(e.message).slice(0, 80)));

  await p.goto('https://findtorontoevents.ca/', { waitUntil: 'domcontentloaded', timeout: 120000 });
  await p.waitForTimeout(1000); // before delayed chunks execute
  const pristine = await p.evaluate(() => document.body.outerHTML);
  fs.writeFileSync('/tmp/hydr_pristine.html', pristine);

  await p.waitForTimeout(1600); // chunks ran (~1800) + hydration attempted (~2100); events still delayed
  const after = await p.evaluate(() => document.body.outerHTML);
  fs.writeFileSync('/tmp/hydr_after.html', after);

  console.log('pageerrors:', JSON.stringify(errs));
  console.log('pristine len:', pristine.length, 'after len:', after.length);
  await b.close();
})().catch(e => { console.error('HARNESS ERROR', e); process.exit(1); });
