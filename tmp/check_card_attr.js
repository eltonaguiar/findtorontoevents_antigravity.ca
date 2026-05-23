const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  await page.goto('https://findtorontoevents.ca/MOVIESHOWS3/?_cb=' + Date.now(), { 
    waitUntil: 'domcontentloaded', timeout: 60000 
  });
  await page.waitForTimeout(2000);

  const cards = await page.evaluate(() => {
    const allCards = document.querySelectorAll('.video-card');
    const results = [];
    for (let i = 0; i < Math.min(5, allCards.length); i++) {
      results.push({
        index: i,
        dataIndex: allCards[i].getAttribute('data-index'),
        hasIframe: !!allCards[i].querySelector('iframe'),
        rect: allCards[i].getBoundingClientRect()
      });
    }
    // Also check card around 2158
    const card2158 = document.querySelector('.video-card[data-index="2158"]');
    return {
      first5: results,
      card2158Exists: !!card2158,
      totalCards: allCards.length
    };
  });
  
  console.log(JSON.stringify(cards, null, 2));

  await browser.close();
})();
