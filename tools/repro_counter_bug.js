/**
 * repro_counter_bug.js
 *
 * Reproduces the "EVENTS FOUND" counter ↔ visible card count desync on the
 * live https://findtorontoevents.ca/ site. Captures:
 *   - default state (no filters)
 *   - after clicking "Today" date filter
 *   - after clicking "Today" + "Dating" category filter
 *
 * Records: counter span value, visible card count, console logs prefixed
 * with [FILTERS], DOM snapshot of the counter container.
 *
 * Run: node tools/repro_counter_bug.js
 */
const { chromium } = require('playwright');

const URL = process.env.TARGET_URL || 'https://findtorontoevents.ca/';

function readState() {
  return {
    counter: (() => {
      const g = document.querySelector('.glow-text');
      if (g) {
        const t = (g.textContent || '').trim();
        if (/^\d+$/.test(t)) return parseInt(t, 10);
      }
      return -1;
    })(),
    visible: (() => {
      const cards = document.querySelectorAll(
        '[class*="glass-panel"]:not(.animate-pulse), [class*="event-card"], [class*="EventCard"]',
      );
      let n = 0;
      for (const c of Array.from(cards)) {
        if (!c.querySelector('h2, h3')) continue;
        if (c.classList.contains('event-card-hidden')) continue;
        const g = c.closest('.group');
        if (g && g.style.display === 'none') continue;
        n++;
      }
      return n;
    })(),
    totalCards: document.querySelectorAll('[class*="glass-panel"]:not(.animate-pulse)').length,
    counterHTML: (() => {
      const g = document.querySelector('.glow-text');
      return g && g.parentElement ? g.parentElement.outerHTML.substring(0, 400) : '(none)';
    })(),
  };
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext();
  const page = await ctx.newPage();

  const filterLogs = [];
  page.on('console', (msg) => {
    const t = msg.text();
    if (t.includes('[FILTERS]')) filterLogs.push(t);
  });

  console.log(`Loading ${URL} ...`);
  await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 60_000 });

  // Wait for hydration: tbd-toggle is injected by the same init() that wires applyFilters
  await page.waitForFunction(() => !!document.getElementById('tbd-toggle'), {
    timeout: 30_000,
  }).catch(() => console.log('  (tbd-toggle never appeared)'));
  await page.waitForTimeout(5000); // settle

  console.log('\n── Default state (no filter clicked) ──');
  let s = await page.evaluate(`(${readState.toString()})()`);
  console.log(`counter=${s.counter}  visible=${s.visible}  totalCards=${s.totalCards}`);
  console.log(`match: ${s.counter === s.visible ? 'YES' : 'NO (BUG)'}`);
  console.log('Counter container HTML:', s.counterHTML);

  // --- click Today ---
  console.log('\n── Clicking "Today" ──');
  const todayBtn = page
    .locator('button, [role="tab"]')
    .filter({ hasText: /^Today$/i })
    .first();
  if (await todayBtn.count()) {
    await todayBtn.click({ timeout: 5000 }).catch((e) => console.log('  click err:', e.message));
    await page.waitForTimeout(3500); // safeApply runs ~400ms after click; +settle
    s = await page.evaluate(`(${readState.toString()})()`);
    console.log(`counter=${s.counter}  visible=${s.visible}  match=${s.counter === s.visible ? 'YES' : 'NO (BUG)'}`);
  } else {
    console.log('  Today button not found by text');
  }

  // --- click Dating ---
  console.log('\n── Clicking "Dating" (Today still active) ──');
  const datingBtn = page
    .locator('button, [role="tab"], [data-category]')
    .filter({ hasText: /^Dating$/i })
    .first();
  if (await datingBtn.count()) {
    await datingBtn.click({ timeout: 5000 }).catch((e) => console.log('  click err:', e.message));
    await page.waitForTimeout(3500);
    s = await page.evaluate(`(${readState.toString()})()`);
    console.log(`counter=${s.counter}  visible=${s.visible}  match=${s.counter === s.visible ? 'YES' : 'NO (BUG)'}`);
    console.log('Counter container HTML:', s.counterHTML);
  } else {
    console.log('  Dating button not found by text');
  }

  console.log(`\nCaptured ${filterLogs.length} [FILTERS] console logs:`);
  filterLogs.slice(-15).forEach((l) => console.log('  ' + l));

  await browser.close();
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
