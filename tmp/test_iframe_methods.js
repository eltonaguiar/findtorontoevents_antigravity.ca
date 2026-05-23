const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: false });
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 720 } });
  const page = await ctx.newPage();

  await page.goto('https://findtorontoevents.ca/MOVIESHOWS3/', { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(5000);

  // Method 1: createElement (immediate)
  await page.evaluate(() => {
    var f = document.createElement('iframe');
    f.id = 'test-create';
    f.src = 'about:blank';
    f.style.cssText = 'position:fixed;top:10px;left:10px;width:300px;height:200px;border:3px solid red;z-index:9999;background:yellow;';
    document.body.appendChild(f);
  });

  // Method 2: insertAdjacentHTML (HTML parser)
  await page.evaluate(() => {
    document.body.insertAdjacentHTML('beforeend',
      '<iframe id="test-html" src="about:blank" style="position:fixed;top:10px;left:320px;width:300px;height:200px;border:3px solid green;z-index:9999;background:cyan;"></iframe>');
  });

  // Method 3: YouTube via insertAdjacentHTML
  await page.evaluate(() => {
    document.body.insertAdjacentHTML('beforeend',
      '<iframe id="test-yt" src="https://www.youtube.com/embed/JUADqWkJiiE?autoplay=1&mute=1" allow="autoplay" style="position:fixed;top:220px;left:10px;width:640px;height:360px;border:3px solid blue;z-index:9999;"></iframe>');
  });

  // Wait for render + YouTube load
  await page.waitForTimeout(5000);

  // Check dimensions
  const results = await page.evaluate(() => {
    var r = {};
    ['test-create', 'test-html', 'test-yt', 'player-0'].forEach(function(id) {
      var el = document.getElementById(id);
      if (el) {
        r[id] = {
          w: el.clientWidth,
          h: el.clientHeight,
          offW: el.offsetWidth,
          offH: el.offsetHeight,
          cw: !!el.contentWindow,
          vis: el.getBoundingClientRect().width > 0
        };
      } else {
        r[id] = 'not found';
      }
    });
    return r;
  });
  console.log('Results after 5s delay:');
  Object.keys(results).forEach(k => console.log('  ' + k + ':', JSON.stringify(results[k])));

  await page.screenshot({ path: 'test_methods.png' });
  console.log('Screenshot: test_methods.png');

  await browser.close();
})();
