const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  const STORES = [
    { name: 'GameStop', url: 'https://www.gamestop.ca/SearchResult/QuickSearch?age=&listSkus=756499%2C756500%2C756695%2C756697' },
    { name: 'Gamerama', url: 'https://www.gamerama.ca/products' },
    { name: 'Queen East', url: 'https://queeneastappliances.com/product-category/xbox-series-xs-consoles/' },
    { name: 'ReserveRoom', url: 'https://reserveroom.ca/product/xbox-series-s-console-512gb-digital-edition/' }
  ];

  for (const store of STORES) {
    console.log(`Checking ${store.name}...`);
    try {
      const response = await page.goto(store.url, { waitUntil: 'domcontentloaded', timeout: 30000 });
      if (response) {
        console.log(`${store.name} Status: ${response.status()}`);
      } else {
        console.log(`${store.name}: No response`);
      }
    } catch (e) {
      console.log(`${store.name} Error: ${e.message}`);
    }
  }
  await browser.close();
})();
