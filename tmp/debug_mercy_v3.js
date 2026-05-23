const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  console.log('Loading MOVIESHOWS3...');
  await page.goto('https://findtorontoevents.ca/MOVIESHOWS3/', { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(4000);
  await page.evaluate(() => { var o = document.getElementById('muteOverlay'); if (o) o.click(); });
  await page.waitForTimeout(500);

  // Get Mercy's index
  const idx = await page.evaluate(() => {
    var match = filteredMovies.find(function(m) { return m.title === 'Mercy'; });
    return match ? filteredMovies.indexOf(match) : -1;
  });
  console.log('Mercy index:', idx);

  // Check card #0 dimensions (the one that IS working)
  const card0 = await page.evaluate(() => {
    var card = document.querySelector('.video-card[data-index="0"]');
    var iframe = document.getElementById('player-0');
    return {
      cardW: card ? card.clientWidth : 0,
      cardH: card ? card.clientHeight : 0,
      cardStyle: card ? getComputedStyle(card).cssText.substring(0, 200) : 'N/A',
      iframeW: iframe ? iframe.clientWidth : 0,
      iframeH: iframe ? iframe.clientHeight : 0
    };
  });
  console.log('\nCard 0 (working):', JSON.stringify(card0, null, 2));

  // Check the Mercy card dimensions BEFORE scrolling
  const cardMercy = await page.evaluate((i) => {
    var card = document.querySelector('.video-card[data-index="' + i + '"]');
    var iframe = document.getElementById('player-' + i);
    return {
      cardExists: !!card,
      cardW: card ? card.clientWidth : 0,
      cardH: card ? card.clientHeight : 0,
      cardDisplay: card ? getComputedStyle(card).display : 'N/A',
      cardVisibility: card ? getComputedStyle(card).visibility : 'N/A',
      cardOverflow: card ? getComputedStyle(card).overflow : 'N/A',
      cardPosition: card ? getComputedStyle(card).position : 'N/A',
      iframeExists: !!iframe,
      iframeW: iframe ? iframe.clientWidth : 0,
      iframeH: iframe ? iframe.clientHeight : 0,
      iframeDisplay: iframe ? getComputedStyle(iframe).display : 'N/A',
      iframeStyle: iframe ? iframe.getAttribute('style') : 'N/A',
      iframeWidth: iframe ? iframe.getAttribute('width') : 'N/A',
      iframeHeight: iframe ? iframe.getAttribute('height') : 'N/A',
    };
  }, idx);
  console.log('\nMercy card (before scroll):', JSON.stringify(cardMercy, null, 2));

  // Check how the container is structured
  const containerInfo = await page.evaluate(() => {
    var c = document.getElementById('container');
    return {
      scrollHeight: c ? c.scrollHeight : 0,
      clientHeight: c ? c.clientHeight : 0,
      overflow: c ? getComputedStyle(c).overflow : 'N/A',
      totalCards: document.querySelectorAll('.video-card').length
    };
  });
  console.log('\nContainer:', JSON.stringify(containerInfo, null, 2));

  // Now scroll to Mercy 
  console.log('\nScrolling to Mercy...');
  await page.evaluate((i) => {
    var container = document.getElementById('container');
    container.scrollTo({ top: i * window.innerHeight, behavior: 'instant' });
  }, idx);
  await page.waitForTimeout(500);

  // Check Mercy card dimensions AFTER scroll
  const afterScroll = await page.evaluate((i) => {
    var card = document.querySelector('.video-card[data-index="' + i + '"]');
    var iframe = document.getElementById('player-' + i);
    return {
      cardW: card ? card.clientWidth : 0,
      cardH: card ? card.clientHeight : 0,
      iframeW: iframe ? iframe.clientWidth : 0,
      iframeH: iframe ? iframe.clientHeight : 0,
      iframeSrc: iframe ? iframe.src : 'N/A',
      iframeContentWindow: iframe ? !!iframe.contentWindow : false,
      cardTop: card ? card.getBoundingClientRect().top : 'N/A'
    };
  }, idx);
  console.log('\nMercy card (after scroll):', JSON.stringify(afterScroll, null, 2));

  // Now manually remove lazy, force reload the iframe
  console.log('\nForce-loading iframe...');
  await page.evaluate((i) => {
    var iframe = document.getElementById('player-' + i);
    iframe.removeAttribute('loading');
    var oldSrc = iframe.src;
    iframe.src = 'about:blank';
    setTimeout(function() {
      iframe.src = oldSrc.replace(/autoplay=[01]/, 'autoplay=1');
    }, 100);
  }, idx);
  await page.waitForTimeout(3000);

  const afterForce = await page.evaluate((i) => {
    var iframe = document.getElementById('player-' + i);
    return {
      iframeW: iframe ? iframe.clientWidth : 0,
      iframeH: iframe ? iframe.clientHeight : 0,
      iframeSrc: iframe ? iframe.src : 'N/A',
      iframeContentWindow: iframe ? !!iframe.contentWindow : false
    };
  }, idx);
  console.log('\nAfter force-load:', JSON.stringify(afterForce, null, 2));

  // Take screenshot
  await page.screenshot({ path: 'mercy_debug_screenshot.png', fullPage: false });
  console.log('\nScreenshot saved to mercy_debug_screenshot.png');

  await browser.close();
})();
