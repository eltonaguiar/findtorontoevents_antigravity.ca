import { test, expect } from '@playwright/test';

// Map of product name → Amazon ASIN
const products: Record<string, string> = {
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

test('extract Amazon product image URLs', async ({ page }) => {
  const results: Record<string, string> = {};

  for (const [name, asin] of Object.entries(products)) {
    const url = `https://www.amazon.ca/dp/${asin}`;
    try {
      await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 15000 });
      // Wait a bit for images to load
      await page.waitForTimeout(2000);

      // Try multiple selectors for the main product image
      let imgUrl = '';
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
          const src = await el.getAttribute('src');
          const hiRes = await el.getAttribute('data-old-hires');
          imgUrl = hiRes || src || '';
          if (imgUrl && imgUrl.startsWith('http')) break;
        }
      }

      // Normalize to a consistent size (_AC_SL300_)
      if (imgUrl) {
        imgUrl = imgUrl.replace(/\._[A-Z0-9_,]+_\./, '._AC_SL300_.');
      }

      results[name] = imgUrl || 'NOT_FOUND';
      console.log(`${name} (${asin}): ${imgUrl || 'NOT_FOUND'}`);
    } catch (e) {
      results[name] = 'ERROR';
      console.log(`${name} (${asin}): ERROR - ${e}`);
    }
  }

  // Output JSON summary
  console.log('\n\n=== IMAGE URL MAP ===');
  console.log(JSON.stringify(results, null, 2));

  // At least some images should have been found
  const found = Object.values(results).filter(v => v !== 'NOT_FOUND' && v !== 'ERROR');
  console.log(`\nFound ${found.length} / ${Object.keys(products).length} images`);
});
