const { chromium } = require('playwright');

const products = {
  'Fanxiang SSD': 'B0DDKTTR5N',
  'Urea Cream': 'B0FBGM7HXT',
  'Glysomed': 'B00QTX8LBW',
  'Light Therapy Lamp': 'B0CCDB1PTN',
  'Herbion Cold Flu': 'B00N75E4SE',
  'Popcorn Kit': 'B0B4X5SLKC',
  'Candy Sweet Sixteen': 'B08GKVJCHV',
  'Cholula Hot Sauce': 'B09K1LXDTJ',
  'Ninja Kettle': 'B09VTFJSCF',
  'Heated Eye Mask': 'B07KSJCY1R',
  'Systane Ultra': 'B00HHXI8ZM',
  'Thealoz Duo': 'B0BWSBGVFS',
  'Contact Lens Cleaner': 'B07NPJF4WY',
  'Lactase Tablets': 'B00P68HOGY',
  'Electrolytes': 'B01HH19AXC',
  'Red Bull Zero': 'B08MRXWM9C',
  'Remington Trimmer': 'B014TWNH18',
  'Hair Taming Stick': 'B0C5SV4JMG',
  'Wallet Tracker': 'B0FCM3VRV1',
  'Batteries USB-C': 'B0F8N5J2BJ',
  'Snake Camera': 'B0FMFJD8SC',
  'Meta Quest 3': 'B0CD1JTBSC',
};

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
  });
  const results = {};

  for (const [name, asin] of Object.entries(products)) {
    const page = await context.newPage();
    const url = `https://www.amazon.ca/dp/${asin}`;
    try {
      await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 15000 });
      await page.waitForTimeout(3000);

      let imgUrl = '';

      // Try #landingImage first (most common)
      const selectors = [
        '#landingImage',
        '#imgBlkFront',
        '#main-image',
        'img[data-a-image-name="landingImage"]',
        '#imageBlock img',
        '.a-dynamic-image',
      ];

      for (const sel of selectors) {
        const el = page.locator(sel).first();
        if (await el.count() > 0) {
          const hiRes = await el.getAttribute('data-old-hires') || '';
          const src = await el.getAttribute('src') || '';
          imgUrl = hiRes || src;
          if (imgUrl && imgUrl.startsWith('http') && imgUrl.includes('/images/I/')) break;
          imgUrl = '';
        }
      }

      // Fallback: look in page source for colorImages JSON
      if (!imgUrl) {
        const content = await page.content();
        const match = content.match(/"hiRes":"(https:\/\/m\.media-amazon\.com\/images\/I\/[^"]+)"/);
        if (match) imgUrl = match[1];
      }

      // Normalize to _AC_SL300_
      if (imgUrl && imgUrl.includes('/images/I/')) {
        const imgId = imgUrl.match(/\/images\/I\/([^.]+)/);
        if (imgId) {
          imgUrl = `https://m.media-amazon.com/images/I/${imgId[1]}._AC_SL300_.jpg`;
        }
      }

      results[name] = { asin, imgUrl: imgUrl || 'NOT_FOUND' };
      console.log(`OK: ${name} (${asin}) -> ${imgUrl || 'NOT_FOUND'}`);
    } catch (e) {
      results[name] = { asin, imgUrl: 'ERROR' };
      console.log(`ERR: ${name} (${asin}) -> ${e.message}`);
    }
    await page.close();
  }

  await browser.close();

  console.log('\n=== RESULTS JSON ===');
  console.log(JSON.stringify(results, null, 2));
})();
