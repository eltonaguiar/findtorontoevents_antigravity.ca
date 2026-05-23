// Full-site Playwright inspection of findtorontoevents.ca
// Captures: console (all levels), network failures, JS errors, per-chip behavior, gear-icon scroll
const { chromium } = require('playwright');
const fs = require('fs');

const URL = process.env.TARGET_URL || 'https://findtorontoevents.ca/';
const ART = 'tmp/inspection_artifacts';
fs.mkdirSync(ART, { recursive: true });

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
  const page = await ctx.newPage();

  const events = {
    console: [],          // {type, text, ts}
    pageErrors: [],       // {message, stack, ts}
    requestFailed: [],    // {url, failure, ts}
    responseErr: [],      // {url, status, ts}
    filterCounter: [],    // [FILTERS] Counter span updated lines
    applyFiltersCalls: 0, // count of "[FILTERS] Applying filters"
  };

  page.on('console', m => {
    const t = m.text();
    events.console.push({ type: m.type(), text: t.slice(0, 500), ts: Date.now() });
    if (t.includes('[FILTERS] Applying filters')) events.applyFiltersCalls++;
    if (t.includes('Counter span updated')) events.filterCounter.push(t);
  });
  page.on('pageerror', e => events.pageErrors.push({ message: e.message, stack: (e.stack || '').slice(0, 1000), ts: Date.now() }));
  page.on('requestfailed', r => events.requestFailed.push({ url: r.url().slice(0, 200), failure: r.failure()?.errorText, ts: Date.now() }));
  page.on('response', r => { if (r.status() >= 400) events.responseErr.push({ url: r.url().slice(0, 200), status: r.status(), ts: Date.now() }); });

  console.log(`[insp] loading ${URL}`);
  await page.goto(URL, { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(8000);
  console.log(`[insp] initial: console=${events.console.length} errors=${events.pageErrors.length} reqFail=${events.requestFailed.length} applyFilters=${events.applyFiltersCalls}`);

  // ====== TEST 1: oscillation detection ======
  const oscillStart = events.applyFiltersCalls;
  await page.waitForTimeout(5000);
  const oscillEnd = events.applyFiltersCalls;
  events.oscillationDelta = oscillEnd - oscillStart;
  console.log(`[insp] oscillation in 5s idle: +${events.oscillationDelta} applyFilters calls`);

  // ====== TEST 2: per-chip behavior ======
  const chipTests = {};
  for (const chip of ['🔥 Today', 'Tomorrow', 'This Week', 'This Month', 'Next Month', 'All Dates']) {
    const before = events.console.length;
    await page.evaluate((label) => {
      for (const b of document.querySelectorAll('button')) {
        if ((b.textContent || '').trim() === label) { b.click(); return; }
      }
    }, chip);
    await page.waitForTimeout(2500);
    const visible = await page.evaluate(() => document.querySelectorAll('.group:not([style*="display: none"]) [class*="event-card"]:not(.event-card-hidden)').length);
    const counter = await page.evaluate(() => {
      const el = document.querySelector('.glow-text.tabular-nums');
      return el ? el.textContent.trim() : null;
    });
    chipTests[chip] = { visible, counter, consoleAdded: events.console.length - before };
    console.log(`[insp] chip "${chip}": visible=${visible} counter=${counter}`);
  }
  events.chipTests = chipTests;

  // ====== TEST 3: gear icon open + scroll ======
  try {
    // Find the gear-icon button (top-right). Most likely class hint or aria-label.
    const gearOpened = await page.evaluate(() => {
      const candidates = document.querySelectorAll('button, [role="button"]');
      for (const el of candidates) {
        const aria = (el.getAttribute('aria-label') || '').toLowerCase();
        const txt = (el.textContent || '').trim();
        if (aria.includes('settings') || aria.includes('gear') || aria.includes('preferences') ||
            txt === '⚙' || txt === '⚙️' || el.querySelector('svg[class*="gear"], svg[class*="cog"], svg[class*="settings"]')) {
          el.click();
          return { clicked: true, aria, txt };
        }
      }
      return { clicked: false };
    });
    await page.waitForTimeout(1000);
    if (gearOpened.clicked) {
      const beforeScroll = await page.evaluate(() => {
        // Find any modal/dropdown panel that's now visible
        const panels = document.querySelectorAll('[role="dialog"], [class*="modal"], [class*="dropdown"], [class*="settings"]');
        let visiblePanels = 0;
        for (const p of panels) {
          const r = p.getBoundingClientRect();
          if (r.width > 0 && r.height > 0) visiblePanels++;
        }
        return { visiblePanels, panelsTotal: panels.length };
      });
      // Scroll the page
      await page.evaluate(() => window.scrollBy(0, 300));
      await page.waitForTimeout(800);
      const afterScroll = await page.evaluate(() => {
        const panels = document.querySelectorAll('[role="dialog"], [class*="modal"], [class*="dropdown"], [class*="settings"]');
        let visiblePanels = 0, blurred = 0;
        for (const p of panels) {
          const r = p.getBoundingClientRect();
          const cs = window.getComputedStyle(p);
          if (r.width > 0 && r.height > 0) {
            visiblePanels++;
            if (cs.filter && cs.filter.includes('blur')) blurred++;
            if (parseFloat(cs.opacity) < 0.5) blurred++;
          }
        }
        return { visiblePanels, blurred };
      });
      events.gearTest = { gearOpened, beforeScroll, afterScroll };
      console.log(`[insp] gear: opened=${gearOpened.clicked} beforeScroll=${JSON.stringify(beforeScroll)} afterScroll=${JSON.stringify(afterScroll)}`);
    } else {
      events.gearTest = { gearOpened };
      console.log(`[insp] gear: NOT FOUND`);
    }
  } catch (e) {
    events.gearTest = { error: String(e) };
  }

  // ====== TEST 4: tabular view toggle ======
  try {
    const tabClicked = await page.evaluate(() => {
      const els = document.querySelectorAll('button, [role="button"]');
      for (const el of els) {
        const t = (el.textContent || '').trim();
        if (t.includes('Tabular') || t.includes('📊')) { el.click(); return true; }
      }
      return false;
    });
    if (tabClicked) {
      await page.waitForTimeout(1500);
      const tabState = await page.evaluate(() => {
        const tables = document.querySelectorAll('table');
        let visible = 0, rows = 0;
        for (const t of tables) {
          const r = t.getBoundingClientRect();
          if (r.width > 0 && r.height > 0) { visible++; rows = Math.max(rows, t.querySelectorAll('tbody tr').length); }
        }
        return { tables: tables.length, visibleTables: visible, maxRows: rows };
      });
      events.tabularTest = { clicked: true, ...tabState };
    } else {
      events.tabularTest = { clicked: false };
    }
    console.log(`[insp] tabular: ${JSON.stringify(events.tabularTest)}`);
  } catch (e) {
    events.tabularTest = { error: String(e) };
  }

  // Final dump
  events.summary = {
    consoleTotal: events.console.length,
    consoleErrors: events.console.filter(c => c.type === 'error').length,
    consoleWarns: events.console.filter(c => c.type === 'warning').length,
    pageErrors: events.pageErrors.length,
    requestFailed: events.requestFailed.length,
    responseErrors: events.responseErr.length,
    applyFiltersCallsTotal: events.applyFiltersCalls,
    oscillationDelta_5s_idle: events.oscillationDelta,
  };

  fs.writeFileSync(`${ART}/full_inspection_summary.json`, JSON.stringify(events.summary, null, 2));
  fs.writeFileSync(`${ART}/full_inspection_console.json`, JSON.stringify(events.console.slice(-200), null, 2));
  fs.writeFileSync(`${ART}/full_inspection_errors.json`, JSON.stringify({ pageErrors: events.pageErrors, requestFailed: events.requestFailed, responseErr: events.responseErr }, null, 2));
  fs.writeFileSync(`${ART}/full_inspection_chips.json`, JSON.stringify(events.chipTests, null, 2));
  fs.writeFileSync(`${ART}/full_inspection_misc.json`, JSON.stringify({ gear: events.gearTest, tabular: events.tabularTest, filterCounter: events.filterCounter.slice(-50) }, null, 2));

  console.log('\n=== SUMMARY ===');
  console.log(JSON.stringify(events.summary, null, 2));

  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
