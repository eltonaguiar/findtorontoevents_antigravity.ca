const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  await page.goto('https://findtorontoevents.ca/MOVIESHOWS3/?_cb=' + Date.now(), { 
    waitUntil: 'domcontentloaded', timeout: 60000 
  });
  await page.waitForTimeout(2000);

  // Get info about the video card at index 2158 (Mercy)
  const info = await page.evaluate(() => {
    const cards = document.querySelectorAll('.video-card');
    const card = cards[2158];
    if (!card) return { error: 'Card not found' };
    
    const iframe = card.querySelector('iframe');
    return {
      cardExists: true,
      iframeExists: !!iframe,
      iframeSrc: iframe ? iframe.src : 'none',
      iframeRect: iframe ? iframe.getBoundingClientRect() : null
    };
  });
  
  console.log('Card 2158 info:', JSON.stringify(info, null, 2));

  await browser.close();
})();
