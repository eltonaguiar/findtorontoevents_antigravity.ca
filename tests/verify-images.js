const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  const failedImages = [];
  page.on('response', response => {
    const url = response.url();
    if (url.includes('media-amazon.com/images/I/') && response.status() !== 200) {
      failedImages.push({ url, status: response.status() });
    }
  });

  await page.goto('https://findtorontoevents.ca/affiliates/', { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(3000);

  const imgCount = await page.locator('.product-img-wrap img').count();
  console.log('Product images found: ' + imgCount);

  const broken = await page.evaluate(() => {
    const imgs = document.querySelectorAll('.product-img-wrap img');
    const results = [];
    imgs.forEach(img => {
      if (img.naturalWidth === 0 || !img.complete) {
        results.push(img.src);
      }
    });
    return results;
  });

  if (broken.length > 0) {
    console.log('BROKEN images (' + broken.length + '):');
    broken.forEach(src => console.log('  ' + src));
  } else {
    console.log('All images loaded successfully!');
  }

  if (failedImages.length > 0) {
    console.log('Failed HTTP responses:');
    failedImages.forEach(f => console.log('  ' + f.status + ': ' + f.url));
  }

  const cardCount = await page.locator('.product-card').count();
  console.log('Product cards: ' + cardCount);

  const content = await page.content();
  const hasOldUrls = content.includes('ws-na.amazon-adsystem.com');
  console.log('Old broken URLs still present: ' + hasOldUrls);

  await browser.close();
})();
