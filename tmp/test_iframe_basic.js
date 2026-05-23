const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: false });
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 720 } });
  const page = await ctx.newPage();

  await page.goto('https://findtorontoevents.ca/MOVIESHOWS3/', { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(5000);

  // Test 1: Simple about:blank iframe
  const test1 = await page.evaluate(() => {
    var f = document.createElement('iframe');
    f.id = 'test1';
    f.src = 'about:blank';
    f.style.cssText = 'position:fixed;top:10px;left:10px;width:300px;height:200px;border:3px solid red;z-index:9999;';
    document.body.appendChild(f);
    return { w: f.clientWidth, h: f.clientHeight, cw: !!f.contentWindow };
  });
  console.log('Test 1 (about:blank):', JSON.stringify(test1));

  // Test 2: YouTube iframe at viewport origin
  const test2 = await page.evaluate(() => {
    var f = document.createElement('iframe');
    f.id = 'test2';
    f.src = 'https://www.youtube.com/embed/JUADqWkJiiE?autoplay=0';
    f.style.cssText = 'position:fixed;top:220px;left:10px;width:400px;height:225px;border:3px solid green;z-index:9999;';
    document.body.appendChild(f);
    return { w: f.clientWidth, h: f.clientHeight, cw: !!f.contentWindow };
  });
  console.log('Test 2 (YT immediate):', JSON.stringify(test2));

  // Wait for YouTube to load
  await page.waitForTimeout(5000);

  const test2b = await page.evaluate(() => {
    var f = document.getElementById('test2');
    return { w: f.clientWidth, h: f.clientHeight, cw: !!f.contentWindow };
  });
  console.log('Test 2 (YT after 5s):', JSON.stringify(test2b));

  // Test 3: Check first card's iframe (already working)
  const test3 = await page.evaluate(() => {
    var f = document.getElementById('player-0');
    return { w: f.clientWidth, h: f.clientHeight, cw: !!f.contentWindow, src: f.src.substring(0, 60) };
  });
  console.log('Test 3 (player-0):', JSON.stringify(test3));

  await page.screenshot({ path: 'test_iframes.png' });
  console.log('Screenshot: test_iframes.png');

  await browser.close();
})();
