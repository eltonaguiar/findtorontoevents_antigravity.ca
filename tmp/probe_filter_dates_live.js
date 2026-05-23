const { chromium } = require('playwright');

async function clickChip(page, text) {
  await page.evaluate((txt) => {
    const buttons = Array.from(document.querySelectorAll('button'));
    const btn = buttons.find((b) => (b.textContent || '').trim() === txt);
    if (btn) btn.click();
  }, text);
  await page.waitForTimeout(2500);
}

async function sample(page, label) {
  const rows = await page.evaluate(() => {
    const cards = Array.from(
      document.querySelectorAll('[class*="glass-panel"]:not(.animate-pulse), [class*="event-card"], [class*="EventCard"]')
    ).filter((c) => !c.classList.contains('event-card-hidden'));
    const parse = window.__parseCardDisplayedDate__;
    return cards.slice(0, 12).map((c) => {
      const h = c.querySelector('h2, h3');
      return { title: (h && h.textContent ? h.textContent : '').trim(), disp: parse ? parse(c) : null };
    });
  });
  console.log(`\n${label}`);
  console.log(rows.map((r) => r.disp).join(', '));
  console.log(rows.slice(0, 6));
}

async function forceApply(page, label) {
  const stats = await page.evaluate(() => {
    try {
      if (typeof applyFilters === 'function') applyFilters();
    } catch (_) {}
    const cards = Array.from(
      document.querySelectorAll('[class*="glass-panel"]:not(.animate-pulse), [class*="event-card"], [class*="EventCard"]')
    );
    const visible = cards.filter((c) => !c.classList.contains('event-card-hidden')).length;
    const hidden = cards.filter((c) => c.classList.contains('event-card-hidden')).length;
    return { visible, hidden, total: cards.length };
  });
  await page.waitForTimeout(500);
  console.log(`${label} force apply stats`, stats);
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  await page.goto('https://findtorontoevents.ca/', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForFunction(
    () => Array.from(document.querySelectorAll('button')).some((b) => (b.textContent || '').trim() === 'Tomorrow'),
    { timeout: 45000 }
  );

  await clickChip(page, 'Tomorrow');
  await sample(page, 'Tomorrow');
  await forceApply(page, 'Tomorrow');
  await sample(page, 'Tomorrow (after force apply)');
  await clickChip(page, 'This Week');
  await sample(page, 'This Week');
  await forceApply(page, 'This Week');
  await sample(page, 'This Week (after force apply)');
  await clickChip(page, 'This Month');
  await sample(page, 'This Month');
  await forceApply(page, 'This Month');
  await sample(page, 'This Month (after force apply)');

  await browser.close();
})();

