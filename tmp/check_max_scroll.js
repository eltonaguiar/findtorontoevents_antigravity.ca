const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  await page.goto('https://findtorontoevents.ca/MOVIESHOWS3/?_cb=' + Date.now(), { 
    waitUntil: 'domcontentloaded', timeout: 60000 
  });
  await page.waitForTimeout(2000);

  const info = await page.evaluate(() => {
    const container = document.getElementById('container');
    const cards = document.querySelectorAll('.video-card');
    return {
      totalCards: cards.length,
      containerScrollHeight: container.scrollHeight,
      containerClientHeight: container.clientHeight,
      maxScrollTop: container.scrollHeight - container.clientHeight,
      windowHeight: window.innerHeight,
      expectedScrollFor2158: 2158 * window.innerHeight
    };
  });
  
  console.log(JSON.stringify(info, null, 2));

  await browser.close();
})();
