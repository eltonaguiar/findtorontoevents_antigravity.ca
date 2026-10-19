const { chromium } = require('playwright');

// Tests the PATCHED homepage (local http.server 5202) with every other request
// proxied to live production, so hydration runs against real chunks + data.
// Pass criteria: ZERO page errors (no React #418), React attached, cards render.
const BASE = 'http://localhost:5202';

(async () => {
  const b = await chromium.launch();
  const p = await (await b.newContext()).newPage();
  const errs = [], consErr = [], failed = [];
  p.on('pageerror', e => errs.push(String(e.message).slice(0, 120)));
  p.on('console', m => { if (m.type() === 'error') consErr.push(m.text().slice(0, 140)); });
  p.on('response', r => { if (r.status() >= 400) failed.push(r.status() + ' ' + r.url().slice(0, 120)); });

  await p.route('**/*', async route => {
    const u = new URL(route.request().url());
    if (u.origin === BASE) {
      if (u.pathname === '/index.html') return route.continue();
      // proxy everything else (css/js/json/images) to live
      const target = 'https://findtorontoevents.ca' + u.pathname + u.search;
      try {
        const resp = await route.fetch({ url: target });
        return route.fulfill({ response: resp });
      } catch (e) {
        return route.abort();
      }
    }
    return route.continue();
  });

  const t0 = Date.now();
  await p.goto(BASE + '/index.html', { waitUntil: 'load', timeout: 120000 });
  await p.waitForTimeout(9000);

  const s = await p.evaluate(() => {
    const main = document.querySelector('main');
    const heroP = document.querySelector('main header p');
    const cards = document.querySelectorAll('main article').length;
    return {
      mainChars: main ? main.innerHTML.length : 0,
      reactAttached: main ? Object.keys(main).some(k => k.startsWith('__reactContainer') || k.startsWith('__reactFiber') || k.startsWith('_reactRoot')) : false,
      heroText: heroP ? heroP.innerText.slice(0, 90) : 'NO HERO P',
      heroLinks: heroP ? heroP.querySelectorAll('a').length : -1,
      cards,
      injectedPromos: document.querySelectorAll('#injected-promos').length,
      footerVersion: (document.querySelector('main footer') || {}).innerText || 'NO FOOTER',
      bodyChars: document.body.innerText.length,
      whenReactHydratedFlag: typeof window.__whenReactHydrated__ === 'function' && window.__reactHydrated__ === true,
    };
  });

  const hydration418 = errs.filter(e => e.includes('418')).length;
  console.log(JSON.stringify({ loadMs: Date.now() - t0, pageErrors: errs.length, hydration418, errSample: errs.slice(0, 5), consoleErrors: consErr.length, consSample: consErr.slice(0, 5), failedReq: failed.length, failedSample: failed.slice(0, 6), ...s }, null, 1));
  const ok = errs.length === 0 && hydration418 === 0 && s.reactAttached && s.heroLinks === 0 && s.cards > 30 && s.injectedPromos === 1;
  console.log(ok ? 'RESULT: PASS' : 'RESULT: FAIL');
  await b.close();
  process.exit(ok ? 0 : 1);
})().catch(e => { console.error('HARNESS ERROR', e); process.exit(2); });
