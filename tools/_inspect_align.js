const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  await page.goto('https://findtorontoevents.ca/', { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(8000);

  const info = await page.evaluate(() => {
    var configBtn = document.querySelector('button[title*="System Configuration"]');
    var signIn = document.getElementById('signin-island');
    var result = {};

    if (configBtn) {
      var par = configBtn.parentElement;
      var parCS = window.getComputedStyle(par);
      var parR = par.getBoundingClientRect();
      result.configBtn = {
        tag: configBtn.tagName,
        rect: configBtn.getBoundingClientRect(),
        parent: {
          tag: par.tagName,
          className: par.className.substring(0, 100),
          position: parCS.position,
          display: parCS.display,
          flexDirection: parCS.flexDirection,
          alignItems: parCS.alignItems,
          rect: { top: parR.top, left: parR.left, right: parR.right, width: parR.width, height: parR.height },
          childCount: par.children.length,
          childrenHTML: Array.from(par.children).map(function(c) {
            return c.tagName + '#' + c.id + ' ' + c.className.substring(0, 40) + ' [' +
              Math.round(c.getBoundingClientRect().top) + ',' + Math.round(c.getBoundingClientRect().left) + ']';
          })
        }
      };
      // Grandparent
      var gp = par.parentElement;
      if (gp) {
        var gpCS = window.getComputedStyle(gp);
        result.grandparent = {
          tag: gp.tagName,
          className: gp.className.substring(0, 100),
          position: gpCS.position,
          display: gpCS.display,
          flexDirection: gpCS.flexDirection,
          top: gpCS.top,
          right: gpCS.right,
          rect: gp.getBoundingClientRect(),
          childrenHTML: Array.from(gp.children).map(function(c) {
            return c.tagName + '#' + c.id + ' ' + c.className.substring(0, 40);
          })
        };
      }
    }

    if (signIn) {
      var siR = signIn.getBoundingClientRect();
      var siCS = window.getComputedStyle(signIn);
      result.signIn = {
        rect: siR,
        position: siCS.position,
        display: siCS.display,
        cssText: signIn.style.cssText.substring(0, 200),
        parentTag: signIn.parentElement ? signIn.parentElement.tagName : null,
        parentId: signIn.parentElement ? signIn.parentElement.id : null,
        parentClass: signIn.parentElement ? signIn.parentElement.className.substring(0, 80) : null
      };
    }

    return result;
  });

  console.log(JSON.stringify(info, null, 2));
  await browser.close();
})();
