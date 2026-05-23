const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  await page.goto('https://findtorontoevents.ca/', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForFunction(
    () => Array.from(document.querySelectorAll('button')).some((b) => (b.textContent || '').trim() === 'Tomorrow'),
    { timeout: 45000 }
  );

  async function dump(label) {
    const rows = await page.evaluate(() => {
      const names = ['🔥 Today', 'Tomorrow', 'This Week', 'This Month', 'All Dates'];
      return names.map((name) => {
        const btn = Array.from(document.querySelectorAll('button')).find((b) => (b.textContent || '').trim() === name);
        return {
          name,
          found: !!btn,
          className: btn ? btn.className : null,
          ariaPressed: btn ? btn.getAttribute('aria-pressed') : null
        };
      });
    });
    console.log('\n' + label);
    console.log(rows);
  }

  await dump('Initial');
  await page.getByRole('button', { name: 'Tomorrow', exact: true }).click();
  await page.waitForTimeout(1200);
  await dump('After Tomorrow click');
  await page.getByRole('button', { name: 'This Week', exact: true }).click();
  await page.waitForTimeout(1200);
  await dump('After This Week click');

  await browser.close();
})();

