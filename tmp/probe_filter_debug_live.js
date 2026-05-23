const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  page.on('pageerror', (e) => console.log('PAGEERROR:', e.message));
  page.on('console', (m) => {
    const t = m.text();
    if (m.type() === 'error' || t.includes('[FILTERS]')) {
      console.log('CONSOLE', m.type(), t);
    }
  });

  await page.goto('https://findtorontoevents.ca/', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(2500);

  await page.getByRole('button', { name: 'Tomorrow', exact: true }).click();
  await page.waitForTimeout(2600);
  const state1 = await page.evaluate(() => ({
    active: ['🔥 Today', 'Tomorrow', 'This Week', 'This Month', 'All Dates'].map((n) => {
      const b = Array.from(document.querySelectorAll('button')).find((x) => (x.textContent || '').trim() === n);
      return { n, className: b ? b.className : null };
    }),
    counts: {
      cards: document.querySelectorAll('[class*="glass-panel"], [class*="event-card"], [class*="EventCard"]').length,
      hidden: document.querySelectorAll('.event-card-hidden').length
    }
  }));
  console.log('STATE_AFTER_TOMORROW', JSON.stringify(state1));

  await page.getByRole('button', { name: 'This Week', exact: true }).click();
  await page.waitForTimeout(2600);
  const state2 = await page.evaluate(() => ({
    active: ['🔥 Today', 'Tomorrow', 'This Week', 'This Month', 'All Dates'].map((n) => {
      const b = Array.from(document.querySelectorAll('button')).find((x) => (x.textContent || '').trim() === n);
      return { n, className: b ? b.className : null };
    }),
    counts: {
      cards: document.querySelectorAll('[class*="glass-panel"], [class*="event-card"], [class*="EventCard"]').length,
      hidden: document.querySelectorAll('.event-card-hidden').length
    }
  }));
  console.log('STATE_AFTER_THISWEEK', JSON.stringify(state2));

  await browser.close();
})();

