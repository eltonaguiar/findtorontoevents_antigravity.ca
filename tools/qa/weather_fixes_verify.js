const { chromium } = require('playwright');

const URL = process.argv[2] || 'http://localhost:5201/weather/index.html';
let pass = 0, fail = 0;
function t(name, ok, detail) {
  console.log(`${ok ? 'PASS' : 'FAIL'}\t${name}\t${detail || ''}`);
  ok ? pass++ : fail++;
}

(async () => {
  const browser = await chromium.launch();

  // ---------- DESKTOP: console + allow attr ----------
  const ctxD = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const pD = await ctxD.newPage();
  const errs = [], warns = [], allowWarn = [], failed = [];
  pD.on('pageerror', e => errs.push('pageerror: ' + e.message));
  pD.on('console', m => {
    const txt = m.text();
    if (m.type() === 'error') errs.push(txt);
    if (m.type() === 'warning') warns.push(txt);
    if (txt.includes('Allow attribute')) allowWarn.push(txt);
  });
  pD.on('response', r => { if (r.status() >= 400) failed.push(r.status() + ' ' + r.url()); });
  await pD.goto(URL, { waitUntil: 'load', timeout: 60000 });
  await pD.waitForTimeout(3500);

  const realErrs = errs.filter(e => !e.includes('404 (File not found)'));
  const nonFaviconFailed = failed.filter(u => !u.endsWith('/favicon.ico'));
  t('desktop_no_page_errors', realErrs.length === 0 && nonFaviconFailed.length === 0,
    `errs=${JSON.stringify(realErrs.slice(0, 3))} failed=${JSON.stringify(nonFaviconFailed.slice(0, 5))}`);
  if (failed.length) console.log('INFO\tfailed_requests_listed\t' + JSON.stringify(failed));
  t('no_allow_attribute_warning', allowWarn.length === 0, JSON.stringify(allowWarn.slice(0, 2)));
  t('no_iframe_allowfullscreen_attr', (await pD.locator('iframe[allowfullscreen]').count()) === 0,
    `count=${await pD.locator('iframe[allowfullscreen]').count()}`);
  const ifrAllow = await pD.$$eval('iframe', fs => fs.map(f => f.getAttribute('allow') || ''));
  t('iframes_allow_include_fullscreen', ifrAllow.every(a => a.includes('fullscreen')), JSON.stringify(ifrAllow));
  t('hourly_cells_rendered', (await pD.locator('#hourly .h-item').count()) >= 20,
    `cells=${await pD.locator('#hourly .h-item').count()}`);

  // ---------- NAV drawer aria (desktop) ----------
  await pD.click('#nav-toggle');
  await pD.waitForTimeout(400);
  const ariaOpen = await pD.getAttribute('#nav-panel', 'aria-hidden');
  const drawerOpen = await pD.$eval('#nav-panel', el => el.classList.contains('open'));
  t('nav_open_sets_aria_false', ariaOpen === 'false' && drawerOpen, `aria=${ariaOpen} open=${drawerOpen}`);
  await pD.click('#nav-overlay', { force: true }).catch(() => {});
  await pD.waitForTimeout(400);
  const ariaClosed = await pD.getAttribute('#nav-panel', 'aria-hidden');
  t('nav_close_sets_aria_true', ariaClosed === 'true', `aria=${ariaClosed}`);

  // ---------- Side panel aria ----------
  const sideBtn = await pD.$('#side-toggle');
  if (sideBtn) {
    const fnType = await pD.evaluate(() => typeof window.closeSide);
    console.log('INFO\ttypeof window.closeSide\t' + fnType);
    await sideBtn.click();
    await pD.waitForTimeout(300);
    const a1 = await pD.getAttribute('#side-panel', 'aria-hidden');
    const open1 = await pD.$eval('#side-panel', el => el.classList.contains('open'));
    t('side_open_sets_aria_false', a1 === 'false' && open1, `aria=${a1} open=${open1}`);
    await pD.click('#side-close');
    await pD.waitForTimeout(300);
    const a2 = await pD.getAttribute('#side-panel', 'aria-hidden');
    const open2 = await pD.$eval('#side-panel', el => el.classList.contains('open'));
    t('side_close_sets_aria_true', a2 === 'true' && !open2, `aria=${a2} open=${open2}`);
  } else {
    t('side_panel_toggle_present', false, 'no #side-toggle found');
  }

  await ctxD.close();

  // ---------- MOBILE: F1 overflow ----------
  const ctxM = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
  const pM = await ctxM.newPage();
  const errsM = [], failedM = [];
  pM.on('pageerror', e => errsM.push(e.message));
  pM.on('console', m => { if (m.type() === 'error') errsM.push(m.text()); });
  pM.on('response', r => { if (r.status() >= 400) failedM.push(r.status() + ' ' + r.url()); });
  await pM.goto(URL, { waitUntil: 'load', timeout: 60000 });
  await pM.waitForTimeout(3000);

  const sw = await pM.evaluate(() => document.documentElement.scrollWidth);
  t('mobile_no_horizontal_overflow', sw <= 400, `scrollWidth=${sw} (was 1807)`);

  const strip = await pM.evaluate(() => {
    const h = document.querySelector('.hourly');
    if (!h) return null;
    return { sw: h.scrollWidth, cw: h.clientWidth, overflow: getComputedStyle(h).overflowX };
  });
  t('hourly_strip_scrolls_internally', strip && strip.sw > strip.cw && strip.overflow === 'auto',
    JSON.stringify(strip));

  // strip actually scrolls
  if (strip && strip.sw > strip.cw) {
    const scrolled = await pM.evaluate(() => {
      const h = document.querySelector('.hourly');
      h.scrollLeft = 100;
      return h.scrollLeft;
    });
    t('hourly_strip_scrollable', scrolled > 0, `scrollLeft=${scrolled}`);
  }

  // nav aria on mobile too
  await pM.click('#nav-toggle');
  await pM.waitForTimeout(300);
  const ma = await pM.getAttribute('#nav-panel', 'aria-hidden');
  t('mobile_nav_aria_false_when_open', ma === 'false', `aria=${ma}`);

  const realErrsM = errsM.filter(e => !e.includes('404 (File not found)'));
  const failedMNonFav = failedM.filter(u => !u.endsWith('/favicon.ico'));
  t('mobile_no_page_errors', realErrsM.length === 0 && failedMNonFav.length === 0,
    `errs=${JSON.stringify(realErrsM.slice(0, 3))} failed=${JSON.stringify(failedMNonFav.slice(0, 5))}`);
  if (failedM.length) console.log('INFO\tfailed_requests_mobile\t' + JSON.stringify(failedM));

  await ctxM.close();
  await browser.close();

  console.log(`\nRESULT: ${pass} PASS / ${fail} FAIL`);
  process.exit(fail ? 1 : 0);
})().catch(e => { console.error('HARNESS ERROR', e); process.exit(2); });
