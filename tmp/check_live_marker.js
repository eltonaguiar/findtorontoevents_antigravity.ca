const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  await page.goto('https://findtorontoevents.ca/', { waitUntil: 'domcontentloaded', timeout: 60000 });
  const html = await page.content();
  console.log('strict marker', html.includes('_strictDateWindowActive'));
  console.log('timeout2 marker', html.includes('_categoryClickTimeout2'));
  console.log('html length', html.length);
  await browser.close();
})();

