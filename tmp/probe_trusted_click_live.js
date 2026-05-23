const { chromium } = require('playwright');

async function sample(page, label) {
  const payload = await page.evaluate(() => {
    const chips = ['🔥 Today', 'Tomorrow', 'This Week', 'This Month', 'All Dates'].map((n) => {
      const b = Array.from(document.querySelectorAll('button')).find((x) => (x.textContent || '').trim() === n);
      return { name: n, className: b ? b.className : null };
    });
    const cards = Array.from(
      document.querySelectorAll('[class*="glass-panel"]:not(.animate-pulse), [class*="event-card"], [class*="EventCard"]')
    ).filter((c) => {
      const style = window.getComputedStyle(c);
      if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return false;
      if (c.offsetParent === null && style.position !== 'fixed') return false;
      if (c.classList.contains('event-card-hidden')) return false;
      const g = c.closest('.group');
      if (g) {
        const gs = window.getComputedStyle(g);
        if (g.classList.contains('event-group-hidden')) return false;
        if (gs.display === 'none' || gs.visibility === 'hidden') return false;
      }
      return true;
    });
    const parse = window.__parseCardDisplayedDate__;
    const rows = cards.slice(0, 12).map((c) => {
      const h = c.querySelector('h2, h3');
      return { title: (h && h.textContent ? h.textContent : '').trim(), disp: parse ? parse(c) : null };
    });
    return {
      chips,
      flags: {
        tomorrowOverride: !!window.__tomorrowOverrideActive__,
        thisWeekOverride: !!window.__thisWeekOverrideActive__,
        thisMonthOverride: !!window.__thisMonthOverrideActive__,
        nextMonthOverride: !!window.__nextMonthFilterActive__
      },
      rows
    };
  });
  console.log(`\n${label}`);
  console.log(payload.chips);
  console.log(payload.flags);
  console.log(payload.rows.map((r) => r.disp).join(', '));
  console.log(payload.rows.slice(0, 6));
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  await page.goto('https://findtorontoevents.ca/', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForFunction(
    () => Array.from(document.querySelectorAll('button')).some((b) => (b.textContent || '').trim() === 'Tomorrow'),
    { timeout: 45000 }
  );

  await page.getByRole('button', { name: 'Tomorrow', exact: true }).click();
  await page.waitForTimeout(5500);
  await sample(page, 'Tomorrow (trusted click)');

  await page.getByRole('button', { name: 'This Week', exact: true }).click();
  await page.waitForTimeout(5500);
  await sample(page, 'This Week (trusted click)');

  await page.getByRole('button', { name: 'This Month', exact: true }).click();
  await page.waitForTimeout(5500);
  await sample(page, 'This Month (trusted click)');

  await browser.close();
})();

