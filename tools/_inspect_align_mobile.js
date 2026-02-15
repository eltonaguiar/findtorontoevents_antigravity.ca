const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 375, height: 812 } });
  await page.goto('https://findtorontoevents.ca/', { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(8000);

  const info = await page.evaluate(() => {
    var configBtn = document.querySelector('button[title*="System Configuration"]');
    var signIn = document.getElementById('signin-island');
    var result = {};

    if (configBtn) {
      var cr = configBtn.getBoundingClientRect();
      var par = configBtn.parentElement;
      var parR = par.getBoundingClientRect();
      var parCS = window.getComputedStyle(par);
      result.configBtn = {
        top: cr.top, left: cr.left, width: cr.width, height: cr.height
      };
      result.parent = {
        className: par.className,
        position: parCS.position,
        display: parCS.display,
        flexDirection: parCS.flexDirection,
        flexWrap: parCS.flexWrap,
        top: parR.top, left: parR.left, width: parR.width, height: parR.height,
        childCount: par.children.length,
        children: Array.from(par.children).map(function(c) {
          var cr2 = c.getBoundingClientRect();
          return {
            tag: c.tagName, id: c.id, class: c.className.substring(0, 60),
            top: cr2.top, left: cr2.left, width: cr2.width, height: cr2.height,
            display: window.getComputedStyle(c).display
          };
        })
      };
    }

    if (signIn) {
      var sr = signIn.getBoundingClientRect();
      result.signIn = {
        top: sr.top, left: sr.left, width: sr.width, height: sr.height,
        cssText: signIn.style.cssText,
        parentTag: signIn.parentElement.tagName,
        parentClass: signIn.parentElement.className.substring(0, 80)
      };
    }

    return result;
  });

  console.log(JSON.stringify(info, null, 2));
  await browser.close();
})();
