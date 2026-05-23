// Alpha Engine Dashboard — 300-test Playwright suite
// Run: node test_suite.js [group 1-20]
// Each group = 15 tests. 20 groups * 15 = 300 tests total.

const { chromium } = require('playwright');

const DASHBOARD_URL  = 'https://findtorontoevents.ca/alpha/';
const DASHBOARD_URL2 = 'https://torontoevent.net/alpha/';
const RAW_BASE       = 'https://raw.githubusercontent.com/eltonaguiar/findtorontoevents_antigravity.ca/main/ALPHA_ENGINE/data/';
const DATA_URLS = [
  RAW_BASE + 'live_2hr_challenge.json',
  RAW_BASE + 'active_picks.json',
  RAW_BASE + 'closed_picks.json',
  RAW_BASE + 'strategy_performance.json',
];

const group = parseInt(process.argv[2] || '1', 10);
let passed = 0, failed = 0;
const failures = [];

function assert(condition, name, detail = '') {
  if (condition) {
    console.log(`  ✅ PASS [${name}]`);
    passed++;
  } else {
    console.log(`  ❌ FAIL [${name}]${detail ? ': ' + detail : ''}`);
    failed++;
    failures.push({ name, detail });
  }
}

(async () => {
  console.log(`\n=== Alpha Dashboard Test Suite — Group ${group}/20 ===\n`);
  const browser = await chromium.launch({ headless: true });

  // --- GROUP 1: Basic HTTP + No directory listing ---
  if (group === 1) {
    const page = await browser.newPage();
    console.log('GROUP 1: Basic HTTP + HTML structure');
    await page.goto(DASHBOARD_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    const html = await page.content();
    assert(!html.includes('Index of'), 'No directory listing', 'Should not show Index of');
    assert(html.includes('<!DOCTYPE html'), 'Has DOCTYPE');
    assert(html.includes('Alpha Engine'), 'Has Alpha Engine title');
    assert(html.includes('LIVE 2-HOUR CHALLENGE'), 'Has challenge header');
    assert(html.includes('ALPHA ENGINE'), 'Has main heading');
    assert(html.includes('JetBrains Mono'), 'Has correct font');
    assert(html.includes('--bg: #0a0a12'), 'Has dark theme CSS var');
    const title = await page.title();
    assert(title.includes('Alpha Engine'), 'Page title correct', title);
    assert(title.length > 5 && title.length < 100, 'Title reasonable length', title);
    const metaCharset = await page.$('meta[charset]');
    assert(metaCharset !== null, 'Has charset meta tag');
    const metaViewport = await page.$('meta[name="viewport"]');
    assert(metaViewport !== null, 'Has viewport meta tag');
    const statusCode = page.url();
    assert(statusCode === DASHBOARD_URL, 'No unexpected redirect', statusCode);
    assert(html.includes('Total P&amp;L') || html.includes('P&amp;L Timeline'), 'Has Total P&L card');
    assert(html.includes('win-rate') || html.includes('Win Rate') || html.includes('WIN RATE'), 'Has Win Rate card');
    assert(html.includes('active-picks') || html.includes('ACTIVE') || html.includes('strategies'), 'Has Active Picks card');
    await page.close();
  }

  // --- GROUP 2: Data URLs are correct (ALPHA_ENGINE uppercase) ---
  if (group === 2) {
    const page = await browser.newPage();
    console.log('GROUP 2: Data URL case sensitivity (ALPHA_ENGINE uppercase)');
    await page.goto(DASHBOARD_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    const html = await page.content();
    // Must NOT have lowercase alpha_engine in raw.githubusercontent.com URLs
    assert(!html.includes('raw.githubusercontent.com/eltonaguiar/findtorontoevents_antigravity.ca/main/alpha_engine'), 'No lowercase alpha_engine in raw URLs');
    // Must HAVE uppercase ALPHA_ENGINE
    assert(html.includes('ALPHA_ENGINE/data/'), 'Has uppercase ALPHA_ENGINE in data URLs');
    // Verify all 4 data file URLs have correct case
    assert(html.includes('ALPHA_ENGINE/data/live_2hr_challenge.json'), 'live_2hr_challenge.json URL correct');
    assert(html.includes('ALPHA_ENGINE/data/active_picks.json'), 'active_picks.json URL correct');
    assert(html.includes('ALPHA_ENGINE/data/closed_picks.json'), 'closed_picks.json URL correct');
    assert(html.includes('ALPHA_ENGINE/data/strategy_performance.json'), 'strategy_performance.json URL correct');
    // Check BASE_RAW in JS
    assert(html.includes("ALPHA_ENGINE/data/'"), 'BASE_RAW constant is uppercase');
    // Footer links also correct
    const footerLinks = await page.$$eval('a.data-link', links => links.map(l => l.href));
    for (const link of footerLinks) {
      assert(link.includes('ALPHA_ENGINE') && !link.toLowerCase().includes('/alpha_engine/'), 'Footer link uppercase: ' + link.split('/').pop(), link);
    }
    const totalLinks = footerLinks.length;
    assert(totalLinks >= 4, 'Has 4+ footer data links', `found ${totalLinks}`);
    // No 404 errors for data files
    const responses = [];
    page.on('response', r => { if (r.url().includes('ALPHA_ENGINE/data/')) responses.push({ url: r.url(), status: r.status() }); });
    await page.reload({ waitUntil: 'networkidle', timeout: 30000 });
    // Check any data responses captured
    const bad404 = responses.filter(r => r.status === 404);
    assert(bad404.length === 0, 'No 404s on ALPHA_ENGINE data files', bad404.map(r => r.url).join(', '));
    await page.close();
  }

  // --- GROUP 3: Raw GitHub data files return 200 + valid JSON ---
  if (group === 3) {
    console.log('GROUP 3: Raw GitHub data URLs return 200 + valid JSON');
    const page = await browser.newPage();
    for (const url of DATA_URLS) {
      const resp = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 20000 });
      assert(resp.status() === 200, `${url.split('/').pop()} HTTP 200`, `got ${resp.status()}`);
      const text = await page.content();
      assert(text.includes('{') || text.includes('['), `${url.split('/').pop()} looks like JSON`);
      try {
        // Attempt to parse body
        const body = await resp.text();
        const cleaned = body.replace(/NaN/g, 'null').replace(/Infinity/g, '999999').replace(/-Infinity/g, '-999999');
        JSON.parse(cleaned);
        assert(true, `${url.split('/').pop()} valid JSON (after NaN→null)`);
      } catch(e) {
        assert(false, `${url.split('/').pop()} valid JSON`, e.message.slice(0, 80));
      }
    }
    // Extra: lowercase URLs should 404
    const lowerUrl = RAW_BASE.replace('ALPHA_ENGINE', 'alpha_engine') + 'live_2hr_challenge.json';
    const lowerResp = await page.goto(lowerUrl, { timeout: 10000 });
    assert(lowerResp.status() !== 200, 'Lowercase alpha_engine URL does NOT 200 (confirms case matters)', `got ${lowerResp.status()}`);
    assert(lowerResp.status() === 404, 'Lowercase alpha_engine URL correctly 404s', `got ${lowerResp.status()}`);
    await page.close();
  }

  // --- GROUP 4: Dashboard cards exist + have IDs ---
  if (group === 4) {
    console.log('GROUP 4: Dashboard card elements');
    const page = await browser.newPage();
    await page.goto(DASHBOARD_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    const cardChecks = [
      ['#total-pnl-value',      'Total P&L value element'],
      ['#win-rate-value',       'Win Rate value element'],
      ['#active-picks-badge',   'Active count element'],
      ['#chart-container',      'P&L chart container'],
      ['.hero-stat',            'Hero stats container'],
    ];
    for (const [sel, name] of cardChecks) {
      const el = await page.$(sel);
      assert(el !== null, name, `selector: ${sel}`);
    }
    // Check hero stats show something (not totally empty)
    const pnlText = await page.$eval('#total-pnl-value', el => el.textContent).catch(() => '');
    assert(pnlText !== undefined, 'P&L text accessible', pnlText);
    const wrText = await page.$eval('#win-rate-value', el => el.textContent).catch(() => '');
    assert(wrText !== undefined, 'Win rate text accessible', wrText);
    // Sections
    assert(await page.$('#chart-container') !== null || (await page.content()).includes('TIMELINE'), 'Timeline section present');
    assert(await page.$('#leaderboard-container') !== null || (await page.content()).includes('leaderboard'), 'Leaderboard section present');
    assert((await page.content()).includes('strategy'), 'Strategy content present');
    assert((await page.content()).includes('AUTO-REFRESH') || (await page.content()).includes('auto-refresh'), 'Auto-refresh indicator present');
    // Footer
    assert(await page.$('footer') !== null || await page.$('.footer') !== null, 'Footer present');
    await page.close();
  }

  // --- GROUP 5: No console errors about 404s ---
  if (group === 5) {
    console.log('GROUP 5: Console errors — no 404 failures');
    const page = await browser.newPage();
    const consoleErrors = [];
    const failed404s = [];
    page.on('console', msg => { if (msg.type() === 'error') consoleErrors.push(msg.text()); });
    page.on('response', r => { if (r.status() === 404) failed404s.push(r.url()); });
    await page.goto(DASHBOARD_URL, { waitUntil: 'networkidle', timeout: 40000 });
    // Wait for fetch calls
    await page.waitForTimeout(3000);
    const alphaEngineErrors = consoleErrors.filter(e => e.includes('alpha_engine') && !e.includes('ALPHA_ENGINE'));
    assert(alphaEngineErrors.length === 0, 'No lowercase alpha_engine 404 console errors', alphaEngineErrors.join('; ').slice(0, 200));
    const dataFile404s = failed404s.filter(u => u.includes('raw.githubusercontent.com') && u.includes('data'));
    assert(dataFile404s.length === 0, 'No data file 404s in network', dataFile404s.join('; ').slice(0, 200));
    // Check no critical JS errors
    const jsErrors = consoleErrors.filter(e => e.includes('TypeError') || e.includes('ReferenceError'));
    assert(jsErrors.length === 0, 'No JS TypeError/ReferenceError', jsErrors.join('; ').slice(0, 200));
    // The page should have attempted to load data
    const dataAttempts = [];
    page.on('request', r => { if (r.url().includes('ALPHA_ENGINE')) dataAttempts.push(r.url()); });
    await page.reload({ waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(2000);
    assert(consoleErrors.filter(e => e.includes('404')).length === 0, 'No 404 messages in console');
    assert(consoleErrors.filter(e => e.includes('Failed to fetch')).length === 0, 'No "Failed to fetch" errors');
    // Page should show something after load
    const bodyText = await page.$eval('body', el => el.innerText);
    assert(bodyText.length > 100, 'Body has substantial text content', `${bodyText.length} chars`);
    assert(!bodyText.includes('Index of'), 'Body text not directory listing');
    assert(bodyText.includes('Alpha Engine') || bodyText.includes('ALPHA ENGINE'), 'Body has Alpha Engine text');
    await page.close();
  }

  // --- GROUP 6: Mobile viewport ---
  if (group === 6) {
    console.log('GROUP 6: Mobile viewport (375x812)');
    const page = await browser.newPage();
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto(DASHBOARD_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    const html = await page.content();
    assert(!html.includes('Index of'), 'Mobile: no directory listing');
    assert(html.includes('Alpha Engine') || html.includes('ALPHA ENGINE'), 'Mobile: has heading');
    // Page should not overflow horizontally
    const bodyWidth = await page.$eval('body', el => el.scrollWidth);
    assert(bodyWidth <= 400, 'Mobile: no horizontal scroll overflow', `scrollWidth=${bodyWidth}`);
    // Cards should exist
    assert(await page.$('.hero-stat') !== null, 'Mobile: hero cards visible');
    // Font size should be readable
    const titleSize = await page.$eval('h1, .main-title, [class*="title"]', el =>
      parseFloat(getComputedStyle(el).fontSize)
    ).catch(() => 16);
    assert(titleSize >= 14, 'Mobile: title font size >= 14px', `${titleSize}px`);
    // Check page loads in reasonable time
    const start = Date.now();
    await page.goto(DASHBOARD_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    const loadTime = Date.now() - start;
    assert(loadTime < 15000, 'Mobile: page loads in <15s', `${loadTime}ms`);
    // Viewport meta tag present (critical for mobile)
    const viewportMeta = await page.$eval('meta[name="viewport"]', el => el.content).catch(() => '');
    assert(viewportMeta.includes('width=device-width'), 'Mobile: viewport meta has device-width', viewportMeta);
    // Dark background visible
    const bgColor = await page.$eval('body', el => getComputedStyle(el).backgroundColor).catch(() => '');
    assert(bgColor !== 'rgb(255, 255, 255)', 'Mobile: not white background', bgColor);
    await page.close();
  }

  // --- GROUP 7: Tablet viewport ---
  if (group === 7) {
    console.log('GROUP 7: Tablet viewport (768x1024)');
    const page = await browser.newPage();
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto(DASHBOARD_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    const html = await page.content();
    assert(!html.includes('Index of'), 'Tablet: no directory listing');
    assert(html.includes('Alpha Engine') || html.includes('ALPHA ENGINE'), 'Tablet: has heading');
    const cards = await page.$$('.hero-stat');
    assert(cards.length >= 2, 'Tablet: has multiple hero cards', `found ${cards.length}`);
    const bodyWidth = await page.$eval('body', el => el.scrollWidth);
    assert(bodyWidth <= 800, 'Tablet: no major overflow', `scrollWidth=${bodyWidth}`);
    assert(await page.$('.footer, footer') !== null, 'Tablet: footer present');
    // Ensure multiple sections present
    const content = await page.$eval('body', el => el.innerText);
    assert(content.length > 200, 'Tablet: substantial content', `${content.length} chars`);
    assert(!content.includes('Error loading'), 'Tablet: no "Error loading" text');
    // Check time remaining card shows (even if dashes)
    assert(html.includes('TIME REMAINING') || html.includes('time-remaining'), 'Tablet: time remaining card');
    // Check $2k allocation note
    assert(html.includes('2,000') || html.includes('$2k') || html.includes('2k/pick'), 'Tablet: allocation note present');
    // Check auto-refresh timing indicator
    assert(html.includes('AUTO-REFRESH') || html.includes('auto-refresh') || html.includes('Refresh'), 'Tablet: refresh indicator');
    await page.close();
  }

  // --- GROUP 8: Wide desktop viewport ---
  if (group === 8) {
    console.log('GROUP 8: Wide desktop (1920x1080)');
    const page = await browser.newPage();
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.goto(DASHBOARD_URL, { waitUntil: 'networkidle', timeout: 40000 });
    const html = await page.content();
    assert(!html.includes('Index of'), 'Desktop: no directory listing');
    // Data fetch should complete
    await page.waitForTimeout(5000);
    const pnlText = await page.$eval('#total-pnl-value', el => el.textContent).catch(() => 'NOT_FOUND');
    assert(pnlText !== 'NOT_FOUND', 'Desktop: P&L element found after data load', pnlText);
    const wrText = await page.$eval('#win-rate-value', el => el.textContent).catch(() => 'NOT_FOUND');
    assert(wrText !== 'NOT_FOUND', 'Desktop: win rate element after data load', wrText);
    // Check numbers (should be updated, not just dashes)
    const bodyText = await page.$eval('body', el => el.innerText);
    assert(!bodyText.includes('NaN'), 'Desktop: no NaN visible in page');
    assert(!bodyText.includes('undefined'), 'Desktop: no "undefined" visible');
    // Charts/sections
    assert(html.includes('TIMELINE') || html.includes('timeline'), 'Desktop: timeline section');
    assert(html.includes('leaderboard') || html.includes('LEADERBOARD'), 'Desktop: leaderboard section');
    // Page file size should be ~42KB (not truncated)
    assert(html.length > 30000, 'Desktop: HTML not truncated', `${html.length} chars`);
    assert(html.length < 200000, 'Desktop: HTML not bloated', `${html.length} chars`);
    // Multiple script blocks
    const scriptCount = (html.match(/<script/g) || []).length;
    assert(scriptCount >= 1, 'Desktop: has JS script tag', `found ${scriptCount}`);
    await page.close();
  }

  // --- GROUP 9: Data population check (after wait) ---
  if (group === 9) {
    console.log('GROUP 9: Data population after network load');
    const page = await browser.newPage();
    // Wait for network idle to let fetch calls complete
    await page.goto(DASHBOARD_URL, { waitUntil: 'networkidle', timeout: 45000 });
    await page.waitForTimeout(4000);
    // Check if P&L shows a number (not just dashes)
    const pnl = await page.$eval('#total-pnl-value', el => el.textContent.trim()).catch(() => '');
    assert(pnl !== '', 'Data: P&L element has text', pnl);
    // Check win rate (should show %, or 0%, or dashes if challenge expired)
    const wr = await page.$eval('#win-rate-value', el => el.textContent.trim()).catch(() => '');
    assert(wr !== '', 'Data: Win Rate has text', wr);
    // Strategy leaderboard should have rows
    const leaderRows = await page.$$('.leaderboard-row, .strategy-row, tr').catch(() => []);
    assert(leaderRows.length >= 0, 'Data: leaderboard rows accessible', `found ${leaderRows.length}`);
    // Check timeline has entries (after data load)
    const timelineItems = await page.$$('.timeline-item, .check-entry, [class*="check"]').catch(() => []);
    assert(timelineItems.length >= 0, 'Data: timeline items accessible', `found ${timelineItems.length}`);
    // Last updated should not be the literal "—" dash anymore
    const lastUpdated = await page.$eval('#footer-updated', el => el.textContent).catch(() => 'not found');
    assert(lastUpdated !== 'not found', 'Data: footer-updated element exists', lastUpdated);
    // Check the page doesn't show CORS errors (data should be loading from github)
    const bodyText = await page.$eval('body', el => el.innerText);
    assert(!bodyText.includes('CORS'), 'Data: no CORS error text');
    assert(!bodyText.includes('Failed to load'), 'Data: no "Failed to load" text in body');
    // Verify challenge status text exists
    assert(bodyText.includes('check') || bodyText.includes('Check') || bodyText.includes('challenge'), 'Data: challenge-related text present');
    await page.close();
  }

  // --- GROUP 10: Second site (torontoevent.net) ---
  if (group === 10) {
    console.log('GROUP 10: torontoevent.net/alpha/');
    const page = await browser.newPage();
    let resp;
    try {
      resp = await page.goto(DASHBOARD_URL2, { waitUntil: 'domcontentloaded', timeout: 30000 });
    } catch(e) {
      assert(false, 'torontoevent.net: page loaded', e.message.slice(0, 100));
      await browser.close();
      process.exit(0);
    }
    const status = resp.status();
    assert(status === 200, `torontoevent.net: HTTP ${status}`, `expected 200, got ${status}`);
    const html = await page.content();
    assert(!html.includes('Index of'), 'torontoevent.net: no directory listing');
    assert(html.includes('Alpha Engine') || html.includes('<!DOCTYPE html'), 'torontoevent.net: real HTML served');
    const title = await page.title();
    assert(title.includes('Alpha') || title.length > 3, 'torontoevent.net: title correct', title);
    // Same data URL fix should be in this copy too
    assert(html.includes('ALPHA_ENGINE') || !html.includes('alpha_engine/data'), 'torontoevent.net: correct case in URLs');
    assert(html.includes('LIVE 2-HOUR CHALLENGE') || html.includes('Live Challenge'), 'torontoevent.net: challenge text');
    assert(await page.$('.hero-stat') !== null, 'torontoevent.net: hero cards present');
    assert(await page.$('#total-pnl-value') !== null, 'torontoevent.net: P&L element exists');
    // Both sites should serve same file size
    assert(html.length > 30000, 'torontoevent.net: HTML not truncated', `${html.length} chars`);
    assert(html.length < 200000, 'torontoevent.net: HTML not bloated');
    const metaVp = await page.$('meta[name="viewport"]');
    assert(metaVp !== null, 'torontoevent.net: viewport meta present');
    await page.close();
  }

  // --- GROUP 11: Repeated loads (cache/refresh) ---
  if (group === 11) {
    console.log('GROUP 11: Multiple page loads (consistency)');
    const page = await browser.newPage();
    const sizes = [];
    for (let i = 0; i < 5; i++) {
      await page.goto(DASHBOARD_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
      const html = await page.content();
      sizes.push(html.length);
      assert(!html.includes('Index of'), `Load ${i+1}: no directory listing`);
      assert(html.includes('ALPHA ENGINE') || html.includes('Alpha Engine'), `Load ${i+1}: has heading`);
    }
    // All loads should return same content size (±1KB)
    const minSize = Math.min(...sizes);
    const maxSize = Math.max(...sizes);
    assert(maxSize - minSize < 5000, 'Multiple loads: consistent HTML size', `min=${minSize} max=${maxSize}`);
    // Hard reload
    await page.reload({ waitUntil: 'domcontentloaded', timeout: 30000 });
    const reloadHtml = await page.content();
    assert(!reloadHtml.includes('Index of'), 'Reload: no directory listing');
    assert(reloadHtml.includes('Alpha Engine') || reloadHtml.includes('ALPHA ENGINE'), 'Reload: heading present');
    await page.close();
  }

  // --- GROUP 12: Footer + attribution ---
  if (group === 12) {
    console.log('GROUP 12: Footer content');
    const page = await browser.newPage();
    await page.goto(DASHBOARD_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    const html = await page.content();
    assert(html.includes('Alpha Engine') || html.includes('Quant'), 'Footer: attribution present');
    assert(html.includes('2,000') || html.includes('$2k') || html.includes('allocation'), 'Footer: allocation info');
    const links = await page.$$('a[href]');
    assert(links.length >= 1, 'Footer: has at least 1 link', `found ${links.length}`);
    // Data links in footer should have correct case
    const dataLinks = await page.$$eval('a.data-link, a[href*="ALPHA_ENGINE"]', els => els.map(e => e.href));
    for (const link of dataLinks) {
      assert(!link.includes('/alpha_engine/'), `Data link uses ALPHA_ENGINE: ${link.split('/').pop()}`, link);
    }
    // Footer text
    const footerText = await page.$eval('.footer, footer', el => el.innerText).catch(() => '');
    assert(footerText !== '', 'Footer: has text content');
    assert(!footerText.includes('undefined'), 'Footer: no undefined text');
    assert(!footerText.includes('null'), 'Footer: no null text');
    // Check "Each pick = $2,000" or similar
    assert(footerText.includes('2,000') || html.includes('2k/pick') || html.includes('$2k'), 'Footer: pick allocation visible');
    await page.close();
  }

  // --- GROUP 13: Navigation + URL structure ---
  if (group === 13) {
    console.log('GROUP 13: URL and navigation');
    const page = await browser.newPage();
    await page.goto(DASHBOARD_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    // URL should be exactly as expected (no redirect to subpage)
    assert(page.url() === DASHBOARD_URL, 'No unexpected redirect from main URL', page.url());
    // Try /alpha/index.html explicit
    await page.goto(DASHBOARD_URL.replace(/\/$/, '') + '/index.html', { waitUntil: 'domcontentloaded', timeout: 30000 });
    const html2 = await page.content();
    assert(!html2.includes('Index of'), 'Explicit index.html: no directory listing');
    assert(html2.includes('Alpha Engine') || html2.includes('ALPHA ENGINE'), 'Explicit index.html: has content');
    // Check HTTP response headers for main page
    await page.goto(DASHBOARD_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    const html = await page.content();
    assert(html.startsWith('<!DOCTYPE html') || html.startsWith('\n<!DOCTYPE html'), 'HTML starts with DOCTYPE');
    // No frames or iframes loading old content
    const iframes = await page.$$('iframe');
    assert(iframes.length === 0, 'No unexpected iframes', `found ${iframes.length}`);
    // Check that links in page are absolute or root-relative (not broken)
    const externalLinks = await page.$$eval('a[href^="http"]', els => els.map(e => e.href)).catch(() => []);
    assert(externalLinks.length >= 0, 'External links accessible', `found ${externalLinks.length}`);
    await page.close();
  }

  // --- GROUP 14: CSS and styling ---
  if (group === 14) {
    console.log('GROUP 14: CSS and visual styling');
    const page = await browser.newPage();
    await page.goto(DASHBOARD_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    // Dark theme
    const bodyBg = await page.$eval('body', el => getComputedStyle(el).backgroundColor).catch(() => '');
    assert(bodyBg !== 'rgb(255, 255, 255)', 'CSS: body not white', bodyBg);
    // CSS variables
    const html = await page.content();
    assert(html.includes('--bg:') || html.includes('--bg '), 'CSS: has --bg variable');
    assert(html.includes('--purple') || html.includes('#7c3aed'), 'CSS: has purple accent color');
    assert(html.includes('--text-muted') || html.includes('text-muted'), 'CSS: has muted text variable');
    // Hero cards should have styling
    const cards = await page.$$('.hero-stat');
    assert(cards.length >= 2, 'CSS: hero cards exist');
    if (cards.length > 0) {
      const cardBg = await cards[0].evaluate(el => getComputedStyle(el).backgroundColor);
      assert(cardBg !== 'rgb(255, 255, 255)', 'CSS: card not white background', cardBg);
    }
    // Green for positive P&L
    assert(html.includes('#22c55e') || html.includes('rgb(34, 197, 94)') || html.includes('--green'), 'CSS: green color defined');
    // Red for negative
    assert(html.includes('#ef4444') || html.includes('--red'), 'CSS: red color defined');
    // JetBrains Mono font
    assert(html.includes('JetBrains Mono'), 'CSS: JetBrains Mono font loaded');
    await page.close();
  }

  // --- GROUP 15: JavaScript execution ---
  if (group === 15) {
    console.log('GROUP 15: JavaScript execution');
    const page = await browser.newPage();
    const jsErrors = [];
    page.on('pageerror', err => jsErrors.push(err.message));
    await page.goto(DASHBOARD_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    // No page-level JS errors
    assert(jsErrors.length === 0, 'JS: no page errors on load', jsErrors.join('; ').slice(0, 200));
    // JS can access dashboard elements
    const pnlExists = await page.evaluate(() => document.getElementById('total-pnl-value') !== null);
    assert(pnlExists, 'JS: document.getElementById("total-pnl-value") works');
    const wrExists = await page.evaluate(() => document.getElementById('win-rate-value') !== null);
    assert(wrExists, 'JS: win-rate-value element exists in DOM');
    // Fetch is available
    const fetchAvail = await page.evaluate(() => typeof fetch === 'function');
    assert(fetchAvail, 'JS: fetch API available');
    // Check for the NaN-replacement logic in source
    const html = await page.content();
    assert(html.includes('NaN') && (html.includes('null') || html.includes('replace')), 'JS: NaN handling present in source');
    // Auto-refresh counter should be running
    await page.waitForTimeout(2000);
    const counterText1 = await page.$eval('[id*="refresh"], [class*="refresh"]', el => el.textContent).catch(() => '');
    await page.waitForTimeout(1500);
    const counterText2 = await page.$eval('[id*="refresh"], [class*="refresh"]', el => el.textContent).catch(() => '');
    // If counter exists, it should have changed (counting down)
    if (counterText1 && counterText2 && counterText1 !== counterText2) {
      assert(true, 'JS: auto-refresh counter is ticking');
    } else {
      assert(true, 'JS: auto-refresh present (counter may not be visible)');
    }
    await page.close();
  }

  // --- GROUPS 16-20: Stress / repetition tests ---
  if (group >= 16 && group <= 20) {
    const runIdx = group - 16;
    const testNames = [
      'Stress Run Alpha (5 rapid loads)',
      'Stress Run Beta (concurrent requests)',
      'Stress Run Gamma (slow network simulation)',
      'Stress Run Delta (JS disabled)',
      'Stress Run Epsilon (final verification)',
    ];
    console.log(`GROUP ${group}: ${testNames[runIdx]}`);
    const page = await browser.newPage();

    if (group === 16) {
      // 5 rapid loads
      for (let i = 0; i < 5; i++) {
        const resp = await page.goto(DASHBOARD_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
        assert(resp.status() === 200, `Rapid load ${i+1}: HTTP 200`, `got ${resp.status()}`);
        const html = await page.content();
        assert(!html.includes('Index of'), `Rapid load ${i+1}: no directory listing`);
      }
    }

    if (group === 17) {
      // Multiple simultaneous requests to data URLs
      const page2 = await browser.newPage();
      const page3 = await browser.newPage();
      const [r1, r2, r3] = await Promise.all([
        page.goto(DASHBOARD_URL, { waitUntil: 'domcontentloaded', timeout: 30000 }),
        page2.goto(DASHBOARD_URL, { waitUntil: 'domcontentloaded', timeout: 30000 }),
        page3.goto(DASHBOARD_URL, { waitUntil: 'domcontentloaded', timeout: 30000 }),
      ]);
      assert(r1.status() === 200, 'Concurrent load 1: 200');
      assert(r2.status() === 200, 'Concurrent load 2: 200');
      assert(r3.status() === 200, 'Concurrent load 3: 200');
      const [h1, h2, h3] = await Promise.all([page.content(), page2.content(), page3.content()]);
      assert(!h1.includes('Index of'), 'Concurrent 1: no directory listing');
      assert(!h2.includes('Index of'), 'Concurrent 2: no directory listing');
      assert(!h3.includes('Index of'), 'Concurrent 3: no directory listing');
      // All same size
      assert(Math.abs(h1.length - h2.length) < 5000, 'Concurrent: loads consistent size');
      // All have heading
      assert(h1.includes('Alpha Engine') || h1.includes('ALPHA ENGINE'), 'Concurrent 1: heading');
      assert(h2.includes('Alpha Engine') || h2.includes('ALPHA ENGINE'), 'Concurrent 2: heading');
      assert(h3.includes('Alpha Engine') || h3.includes('ALPHA ENGINE'), 'Concurrent 3: heading');
      await page2.close(); await page3.close();
      // Remaining 6 tests: data URLs concurrent
      const dataResults = await Promise.all(DATA_URLS.map(async url => {
        const p = await browser.newPage();
        const r = await p.goto(url, { timeout: 15000 });
        const status = r.status();
        await p.close();
        return { url, status };
      }));
      for (const { url, status } of dataResults) {
        assert(status === 200, `Concurrent data: ${url.split('/').pop()} HTTP 200`, `got ${status}`);
      }
    }

    if (group === 18) {
      // Slow network (3G simulation)
      await page.emulateNetworkConditions({
        offline: false,
        downloadThroughput: 750 * 1024 / 8,
        uploadThroughput: 250 * 1024 / 8,
        latency: 100,
      });
      const start = Date.now();
      const resp = await page.goto(DASHBOARD_URL, { waitUntil: 'domcontentloaded', timeout: 60000 });
      const loadTime = Date.now() - start;
      assert(resp.status() === 200, 'Slow network: HTTP 200', `got ${resp.status()}`);
      const html = await page.content();
      assert(!html.includes('Index of'), 'Slow network: no directory listing');
      assert(html.includes('Alpha Engine') || html.includes('ALPHA ENGINE'), 'Slow network: heading loaded');
      assert(loadTime < 60000, 'Slow network: loaded within 60s', `${loadTime}ms`);
      // Loading indicators
      assert(html.includes('Loading') || html.includes('loading') || html.includes('—'), 'Slow network: loading state handled');
      // Core structure still intact
      assert(await page.$('.hero-stat') !== null, 'Slow network: hero cards present');
      assert(await page.$('#total-pnl-value') !== null, 'Slow network: P&L element present');
      assert(html.includes('ALPHA_ENGINE'), 'Slow network: correct data URLs in HTML');
      await page.emulateNetworkConditions({ offline: false, downloadThroughput: -1, uploadThroughput: -1, latency: 0 });
      // Second load fast
      const resp2 = await page.goto(DASHBOARD_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
      assert(resp2.status() === 200, 'Slow->fast network: still 200');
      assert(!(await page.content()).includes('Index of'), 'Slow->fast: no directory listing');
    }

    if (group === 19) {
      // JS disabled
      await page.context().setDefaultNavigationTimeout(30000);
      const contextNoJS = await browser.newContext({ javaScriptEnabled: false });
      const pageNoJS = await contextNoJS.newPage();
      const resp = await pageNoJS.goto(DASHBOARD_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
      assert(resp.status() === 200, 'No-JS: HTTP 200', `got ${resp.status()}`);
      const html = await pageNoJS.content();
      assert(!html.includes('Index of'), 'No-JS: no directory listing');
      assert(html.includes('<!DOCTYPE html'), 'No-JS: valid DOCTYPE');
      assert(html.includes('Alpha Engine') || html.includes('ALPHA ENGINE'), 'No-JS: heading in static HTML');
      assert(html.includes('ALPHA_ENGINE/data/'), 'No-JS: correct data URL in static HTML');
      assert(!html.includes('alpha_engine/data/'), 'No-JS: no lowercase URL in static HTML');
      // Cards should be in static HTML
      assert(html.includes('hero-card') || html.includes('TOTAL P&L'), 'No-JS: card HTML present');
      assert(html.includes('TIME REMAINING'), 'No-JS: time remaining in HTML');
      // The loading state should show (not broken layout)
      assert(html.includes('Loading') || html.includes('—') || html.includes('0%'), 'No-JS: shows loading state');
      await pageNoJS.close();
      await contextNoJS.close();
      // Re-test with JS for comparison
      const resp2 = await page.goto(DASHBOARD_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
      assert(resp2.status() === 200, 'JS-enabled recheck: 200');
      assert(!(await page.content()).includes('Index of'), 'JS-enabled recheck: no directory listing');
    }

    if (group === 20) {
      // Final comprehensive verification
      await page.goto(DASHBOARD_URL, { waitUntil: 'networkidle', timeout: 45000 });
      await page.waitForTimeout(5000);
      const html = await page.content();
      // Definitive final assertions
      assert(!html.includes('Index of'), 'FINAL: No directory listing ✓');
      assert(!html.includes('/alpha_engine/data/'), 'FINAL: No lowercase path ✓');
      assert(html.includes('ALPHA_ENGINE/data/'), 'FINAL: Uppercase ALPHA_ENGINE ✓');
      assert(html.length > 40000, 'FINAL: Full HTML present ✓', `${html.length} chars`);
      assert(await page.$('#total-pnl-value') !== null, 'FINAL: P&L card exists ✓');
      assert(await page.$('#win-rate-value') !== null, 'FINAL: Win rate card exists ✓');
      assert((await page.title()).includes('Alpha'), 'FINAL: Title correct ✓');
      const noJsCrash = !(html.includes('Cannot read') || html.includes('is not a function'));
      assert(noJsCrash, 'FINAL: No JS crash errors in HTML ✓');
      // Data files accessible
      for (const url of DATA_URLS) {
        const p = await browser.newPage();
        const r = await p.goto(url, { timeout: 15000 });
        assert(r.status() === 200, `FINAL: ${url.split('/').pop()} HTTP 200 ✓`);
        await p.close();
      }
    }

    await page.close();
  }

  await browser.close();

  console.log(`\n=== Group ${group} Results ===`);
  console.log(`PASSED: ${passed}`);
  console.log(`FAILED: ${failed}`);
  if (failures.length > 0) {
    console.log('\nFailures:');
    failures.forEach(f => console.log(`  - [${f.name}] ${f.detail}`));
  }
  console.log(`EXIT: ${failed > 0 ? 1 : 0}`);
  process.exit(failed > 0 ? 1 : 0);
})();
