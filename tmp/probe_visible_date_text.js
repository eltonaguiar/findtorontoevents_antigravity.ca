const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  await page.goto('https://findtorontoevents.ca/', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(2200);
  await page.getByRole('button', { name: 'Tomorrow', exact: true }).click();
  await page.waitForTimeout(2500);

  const rows = await page.evaluate(() => {
    const cards = Array.from(
      document.querySelectorAll('[class*="glass-panel"]:not(.animate-pulse), [class*="event-card"], [class*="EventCard"]')
    ).filter((c) => {
      const s = getComputedStyle(c);
      if (s.display === 'none' || s.visibility === 'hidden') return false;
      if (c.classList.contains('event-card-hidden')) return false;
      const g = c.closest('.group');
      if (g && g.classList.contains('event-group-hidden')) return false;
      return true;
    }).slice(0, 8);
    const parse = window.__parseCardDisplayedDate__;
    return cards.map((c) => {
      const h = c.querySelector('h2, h3');
      const text = (c.innerText || '').split('\n').map((x) => x.trim()).filter(Boolean).slice(0, 8);
      return { title: h ? h.textContent.trim() : '', disp: parse ? parse(c) : null, lines: text };
    });
  });
  console.dir(rows, { depth: 4 });
  await browser.close();
})();

