const { chromium } = require('/home/eaguiar2015/findtorontoevents_antigravity.ca/node_modules/playwright');
const fs = require('fs');

const URL = process.argv[2] || 'https://findtorontoevents.ca/weather/';
const SHOT = process.argv[3] || '/tmp/weather-shots';
const results = [];
function add(name, status, detail) { results.push({ name, status, detail }); }

(async () => {
  fs.mkdirSync(SHOT, { recursive: true });
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, userAgent: 'Mozilla/5.0 (X11; Linux x86_64) FreebuffWeatherQA/1.0' });
  const page = await ctx.newPage();

  const consoleErrs = [], pageErrs = [], failed = [];
  page.on('console', m => { if (m.type() === 'error') consoleErrs.push(m.text().slice(0, 200)); });
  page.on('pageerror', e => pageErrs.push(String(e.message).slice(0, 200)));
  page.on('requestfailed', r => failed.push({ url: r.url().slice(0, 120), err: r.failure() && r.failure().errorText }));
  page.on('response', r => { if (r.status() >= 400) failed.push({ url: r.url().slice(0, 120), err: 'HTTP ' + r.status() }); });

  // 1 — load
  const t0 = Date.now();
  const resp = await page.goto(URL, { waitUntil: 'load', timeout: 90000 });
  const loadMs = Date.now() - t0;
  add('page_load', resp && resp.status() === 200 ? 'PASS' : 'FAIL', `HTTP ${resp && resp.status()} in ${loadMs}ms`);
  const title = await page.title();
  add('page_title', title && title.trim().length > 3 ? 'PASS' : 'WARN', JSON.stringify(title));

  await page.waitForTimeout(9000); // let weather APIs settle

  // 2 — errors
  add('page_js_errors', pageErrs.length === 0 ? 'PASS' : 'FAIL', pageErrs.length ? pageErrs.slice(0, 5) : 'none');
  add('console_errors', consoleErrs.length === 0 ? 'PASS' : 'WARN', consoleErrs.length ? consoleErrs.slice(0, 6) : 'none');
  add('failed_requests', failed.length === 0 ? 'PASS' : 'WARN', failed.length ? failed.slice(0, 8) : 'none');

  // 3 — core current conditions
  const core = await page.evaluate(() => {
    const txt = s => { const e = document.querySelector(s); return e ? e.textContent.trim().slice(0, 60) : null; };
    return {
      temp: txt('#cur-temp'), feels: txt('#cur-feels'), cond: txt('#condition'),
      humid: txt('#humid'), cloud: txt('#cloud-cover'), gust: txt('#gust'),
      daylight: txt('#daylight-left'), area: txt('#area-label'), updated: txt('#last-updated'),
      hourlyChildren: (document.querySelector('#hourly') || {}).childElementCount,
      forecastChildren: (document.querySelector('#forecast') || {}).childElementCount,
      alertsHTML: (document.querySelector('#alerts') || {}).innerHTML.length,
      rainFill: (document.querySelector('#rain-fill') || {}).style && document.querySelector('#rain-fill').style.width,
      bodyChars: document.body.innerText.length,
    };
  });
  const hasDeg = s => s && /[°º]|\d/.test(s);
  add('current_temperature', hasDeg(core.temp) ? 'PASS' : 'FAIL', core.temp);
  add('feels_like', hasDeg(core.feels) ? 'PASS' : 'WARN', core.feels);
  add('condition_text', core.cond && core.cond.length > 1 ? 'PASS' : 'FAIL', core.cond);
  add('humidity', core.humid ? 'PASS' : 'WARN', core.humid);
  add('cloud_cover', core.cloud ? 'PASS' : 'WARN', core.cloud);
  add('wind_gust', core.gust ? 'PASS' : 'WARN', core.gust);
  add('daylight_widget', core.daylight ? 'PASS' : 'WARN', core.daylight);
  add('area_label', core.area ? 'PASS' : 'WARN', core.area);
  add('hourly_forecast_rendered', (core.hourlyChildren || 0) >= 4 ? 'PASS' : 'FAIL', `children=${core.hourlyChildren}`);
  add('daily_forecast_rendered', (core.forecastChildren || 0) >= 3 ? 'PASS' : 'FAIL', `children=${core.forecastChildren}`);
  add('body_rendered', core.bodyChars > 1200 ? 'PASS' : 'FAIL', `innerText chars=${core.bodyChars}`);
  add('rain_probability_bar', core.rainFill ? 'INFO' : 'WARN', `rain-fill width=${core.rainFill}`);

  // 4 — freshness
  const fresh = await page.evaluate(() => {
    const el = document.querySelector('#last-updated');
    return el ? el.textContent.trim() : '';
  });
  results.push({ name: 'last_updated_stamp', status: fresh ? 'INFO' : 'WARN', detail: fresh || 'missing #last-updated' });

  // 5 — entertainment tabs live INSIDE the left nav drawer, so open it first
  try {
    await page.click('#nav-toggle', { timeout: 5000 });
    await page.waitForTimeout(700);
  } catch (e) { /* handled below */ }
  const navState = () => page.evaluate(() => {
    const n = document.querySelector('#nav-panel');
    return n ? { open: n.classList.contains('open'), transform: getComputedStyle(n).transform, ariaHidden: n.getAttribute('aria-hidden') } : null;
  });
  const entTabs = await page.$$('#ent-tabs [data-tab], #ent-tabs button, #ent-tabs a');
  add('entertainment_tabs_present', entTabs.length >= 2 ? 'PASS' : 'WARN', `tabs=${entTabs.length} (inside #nav-panel drawer)`);
  for (let i = 0; i < Math.min(entTabs.length, 4); i++) {
    try {
      await entTabs[i].click({ timeout: 5000 });
      await page.waitForTimeout(500);
      const activeCount = await page.evaluate(() => document.querySelectorAll('#ent-tabs .ent-tab.active').length);
      const contentLen = await page.evaluate(() => (document.querySelector('#ent-content') || {}).innerHTML.length || 0);
      add(`ent_tab_${i}_click`, pageErrs.length === 0 ? activeCount === 1 ? 'PASS' : 'WARN' : 'FAIL',
          `activeTabs=${activeCount} ent-content chars=${contentLen}`);
    } catch (e) { add(`ent_tab_${i}_click`, 'WARN', String(e.message).slice(0, 90).replace(/\s+/g, ' ')); }
  }

  // close the drawer before testing the in-page player tabs (it overlays at z-index 400)
  try { await page.click('#nav-close', { force: true }); await page.waitForTimeout(700); } catch (e) {}

  const playerTabs = await page.$$('#player-tabs [data-tab], #player-tabs button, #player-tabs a');
  add('player_tabs_present', playerTabs.length >= 2 ? 'PASS' : 'WARN', `tabs=${playerTabs.length}`);
  for (let i = 0; i < Math.min(playerTabs.length, 3); i++) {
    try {
      await playerTabs[i].click({ timeout: 5000 });
      await page.waitForTimeout(700);
      const vis = await page.evaluate(() => {
        const out = {};
        ['player-songs', 'player-radio', 'player-video'].forEach(id => {
          const e = document.getElementById(id);
          out[id] = e ? (getComputedStyle(e).display !== 'none' && e.getBoundingClientRect().height > 0) : null;
        });
        return out;
      });
      add(`player_tab_${i}_click`, pageErrs.length === 0 ? 'PASS' : 'FAIL', JSON.stringify(vis));
    } catch (e) { add(`player_tab_${i}_click`, 'WARN', String(e.message).slice(0, 90).replace(/\s+/g, ' ')); }
  }

  try {
    await page.click('#audio-btn', { timeout: 6000, force: true });
    await page.waitForTimeout(1200);
    add('audio_button_click', pageErrs.length === 0 ? 'PASS' : 'WARN', 'clicked, no page error');
  } catch (e) { add('audio_button_click', 'WARN', String(e.message).slice(0, 90).replace(/\s+/g, ' ')); }

  // 6 — extras toggle (hide then RESTORE so later tests see the full page)
  try {
    const before = await page.evaluate(() => document.querySelector('#extras-toggle') && document.querySelector('#extras-toggle').textContent.trim());
    await page.click('#extras-toggle', { timeout: 5000 });
    await page.waitForTimeout(500);
    const after = await page.evaluate(() => document.querySelector('#extras-toggle') && document.querySelector('#extras-toggle').textContent.trim());
    await page.click('#extras-toggle', { timeout: 5000 });   // restore
    await page.waitForTimeout(500);
    const restored = await page.evaluate(() => document.querySelector('#extras-toggle') && document.querySelector('#extras-toggle').textContent.trim());
    add('extras_toggle_clickable', 'PASS', `label "${before}" -> "${after}" -> restored "${restored}"`);
  } catch (e) { add('extras_toggle_clickable', 'WARN', String(e.message).slice(0, 120)); }

  // 7 — nav (LAST: it overlays the page)
  try {
    let st = await navState();
    if (!st || !st.open) { await page.click('#nav-toggle', { timeout: 5000 }); await page.waitForTimeout(700); st = await navState(); }
    add('nav_toggle_opens', st && st.open ? 'PASS' : 'FAIL', JSON.stringify(st));
    add('nav_aria_hidden_while_open', st && st.ariaHidden === 'true' ? 'FAIL' : 'PASS', `aria-hidden=${st && st.ariaHidden} while open=${st && st.open}`);
    await page.click('#nav-close', { force: true });
    await page.waitForTimeout(800);
    const closed = await navState();
    add('nav_close_works', closed && !closed.open ? 'PASS' : 'FAIL', JSON.stringify(closed));
    if (closed && closed.open) {
      await page.keyboard.press('Escape').catch(() => {});
      await page.waitForTimeout(400);
      await page.mouse.click(1200, 500).catch(() => {});
      await page.waitForTimeout(600);
      const still = await navState();
      add('nav_close_via_escape_or_overlay', still && !still.open ? 'PASS' : 'FAIL', JSON.stringify(still));
    }
  } catch (e) { add('nav_toggle_opens', 'FAIL', String(e.message).slice(0, 120)); }

  // 8 — postal code lookup (changes location)
  try {
    const areaBefore = await page.evaluate(() => (document.querySelector('#area-label') || {}).textContent);
    await page.fill('#postal-input', 'M5V 2T6');
    const btn = await page.$('#fx-btns button, #postal-input + button, button[type=submit]');
    if (btn) await btn.click(); else await page.press('#postal-input', 'Enter');
    await page.waitForTimeout(6000);
    const areaAfter = await page.evaluate(() => (document.querySelector('#area-label') || {}).textContent);
    const tempAfter = await page.evaluate(() => (document.querySelector('#cur-temp') || {}).textContent);
    add('postal_lookup', (areaAfter && areaAfter !== areaBefore) || (tempAfter && /\d/.test(tempAfter)) ? 'PASS' : 'WARN',
        `area "${areaBefore}" -> "${areaAfter}", temp=${tempAfter}, pageErrs=${pageErrs.length}`);
  } catch (e) { add('postal_lookup', 'WARN', e.message.slice(0, 140)); }

  // 9 — audio button (moved earlier; kept as a no-op guard)

  await page.screenshot({ path: SHOT + '/desktop.png', fullPage: true });

  // 10 — accessibility basics
  const a11y = await page.evaluate(() => {
    const imgs = [...document.images];
    return {
      lang: document.documentElement.lang || null,
      viewportMeta: !!document.querySelector('meta[name=viewport]'),
      h1: [...document.querySelectorAll('h1')].map(h => h.textContent.trim()).slice(0, 2),
      imgs: imgs.length,
      imgsNoAlt: imgs.filter(i => !i.hasAttribute('alt')).length,
      buttonsNoLabel: [...document.querySelectorAll('button')].filter(b => !b.textContent.trim() && !b.getAttribute('aria-label')).length,
      linksNoText: [...document.querySelectorAll('a')].filter(a => !a.textContent.trim() && !a.getAttribute('aria-label') && !a.querySelector('img[alt]')).length,
    };
  });
  add('html_lang', a11y.lang ? 'PASS' : 'WARN', a11y.lang);
  add('viewport_meta', a11y.viewportMeta ? 'PASS' : 'FAIL', String(a11y.viewportMeta));
  add('h1_present', a11y.h1.length ? 'PASS' : 'WARN', JSON.stringify(a11y.h1));
  add('images_alt_coverage', a11y.imgs === 0 ? 'INFO' : (a11y.imgsNoAlt === 0 ? 'PASS' : 'WARN'), `${a11y.imgsNoAlt}/${a11y.imgs} imgs missing alt`);
  add('buttons_without_label', a11y.buttonsNoLabel === 0 ? 'PASS' : 'WARN', `${a11y.buttonsNoLabel} unlabelled buttons`);
  add('links_without_text', a11y.linksNoText === 0 ? 'PASS' : 'WARN', `${a11y.linksNoText} empty links`);

  // 11 — mobile viewport
  const mob = await ctx.newPage();
  const mobErrs = [];
  mob.on('pageerror', e => mobErrs.push(String(e.message).slice(0, 120)));
  await mob.setViewportSize({ width: 390, height: 844 });
  await mob.goto(URL, { waitUntil: 'load', timeout: 90000 });
  await mob.waitForTimeout(6000);
  const overflow = await mob.evaluate(() => ({
    scrollW: document.documentElement.scrollWidth, innerW: window.innerWidth,
    gridTrack: (() => { const g = document.querySelector('.grid'); return g ? getComputedStyle(g).gridTemplateColumns : null; })(),
    hourlyScrolls: (() => { const h = document.querySelector('#hourly'); return h ? { clientW: h.clientWidth, scrollW: h.scrollWidth } : null; })(),
    widest: (() => { let w = 0, el = null; document.querySelectorAll('body *').forEach(e => { const r = e.getBoundingClientRect(); if (r.right > w) { w = r.right; el = e; } }); return { right: Math.round(w), tag: el && el.tagName + (el.id ? '#' + el.id : '') }; })(),
  }));
  add('mobile_no_horizontal_overflow', overflow.scrollW <= overflow.innerW + 2 ? 'PASS' : 'FAIL',
      `scrollW=${overflow.scrollW} innerW=${overflow.innerW} widest=${overflow.widest.tag}@${overflow.widest.right}`);
  try { await mob.click('#nav-toggle', { timeout: 5000 }); await mob.waitForTimeout(500);
    const navVis = await mob.evaluate(() => { const p = document.querySelector('#nav-panel'); return p ? p.getBoundingClientRect().width > 0 : false; });
    add('mobile_nav_opens', navVis ? 'PASS' : 'FAIL', `visible=${navVis}`);
  } catch (e) { add('mobile_nav_opens', 'WARN', e.message.slice(0, 100)); }
  add('mobile_js_errors', mobErrs.length === 0 ? 'PASS' : 'FAIL', mobErrs.slice(0, 4));
  await mob.screenshot({ path: SHOT + '/mobile.png', fullPage: true });

  // 12 — perf timing
  const perf = await page.evaluate(() => {
    const t = performance.getEntriesByType('navigation')[0] || {};
    const res = performance.getEntriesByType('resource');
    return {
      domContentLoaded: Math.round(t.domContentLoadedEventEnd || 0),
      loadEvent: Math.round(t.loadEventEnd || 0),
      resources: res.length,
      thirdParty: res.filter(r => !r.name.includes('findtorontoevents.ca')).length,
    };
  });
  add('perf_timing', 'INFO', JSON.stringify(perf));

  await browser.close();

  const counts = results.reduce((a, r) => (a[r.status] = (a[r.status] || 0) + 1, a), {});
  console.log(JSON.stringify({ url: URL, summary: counts, results }, null, 1));
})();
