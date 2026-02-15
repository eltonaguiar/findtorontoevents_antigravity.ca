const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 375, height: 812 } });
  await page.goto('http://localhost:5173/index.html', { waitUntil: 'networkidle', timeout: 25000 });
  await page.waitForTimeout(6000);

  // Find all "Dating" buttons and their parent containers
  const datingInfo = await page.evaluate(() => {
    var results = [];
    var buttons = document.querySelectorAll('button, [role="button"]');
    for (var i = 0; i < buttons.length; i++) {
      var txt = buttons[i].textContent.trim();
      if (/^💘?Dating$/i.test(txt) || txt === '💘Dating') {
        var el = buttons[i];
        var rect = el.getBoundingClientRect();
        // Walk up to find the containing section
        var parent = el.parentElement;
        var parentInfo = [];
        for (var p = 0; p < 5 && parent; p++) {
          parentInfo.push({
            tag: parent.tagName,
            id: parent.id || '',
            class: parent.className ? parent.className.substring(0, 80) : '',
            childCount: parent.children.length
          });
          parent = parent.parentElement;
        }
        // Get sibling buttons (category tabs in same container)
        var siblings = [];
        var parentEl = el.parentElement;
        if (parentEl) {
          for (var s = 0; s < parentEl.children.length && s < 10; s++) {
            var sib = parentEl.children[s];
            siblings.push(sib.textContent.trim().substring(0, 30));
          }
        }
        results.push({
          text: txt,
          rect: { top: Math.round(rect.top), left: Math.round(rect.left) },
          siblings: siblings,
          parents: parentInfo
        });
      }
    }
    return results;
  });

  console.log('=== Dating Buttons Detail ===');
  datingInfo.forEach((d, i) => {
    console.log(`\nButton #${i + 1}: "${d.text}" at top=${d.rect.top}, left=${d.rect.left}`);
    console.log('  Siblings:', d.siblings.join(' | '));
    console.log('  Parent chain:');
    d.parents.forEach((p, j) => {
      console.log(`    ${j}: <${p.tag}> id="${p.id}" class="${p.class}" children=${p.childCount}`);
    });
  });

  // Also check bottom-right icon stack positions
  console.log('\n=== Bottom-Right Icon Stack ===');
  const stack = await page.evaluate(() => {
    var items = [];
    // Gear button
    var gear = document.querySelector('.fixed.bottom-6.right-6');
    if (gear) {
      var r = gear.getBoundingClientRect();
      items.push({ name: 'Gear', bottom: Math.round(window.innerHeight - r.bottom), right: Math.round(window.innerWidth - r.right), h: Math.round(r.height) });
    }
    // AI btn
    var ai = document.getElementById('fte-ai-btn');
    if (ai) {
      var r = ai.getBoundingClientRect();
      items.push({ name: 'AI btn', bottom: Math.round(window.innerHeight - r.bottom), right: Math.round(window.innerWidth - r.right), h: Math.round(r.height) });
    }
    // Mute btn
    var mute = document.getElementById('fte-mute-btn');
    if (mute) {
      var r = mute.getBoundingClientRect();
      items.push({ name: 'Mute btn', bottom: Math.round(window.innerHeight - r.bottom), right: Math.round(window.innerWidth - r.right), h: Math.round(r.height) });
    }
    // Thumb toggle
    var thumb = document.getElementById('fte-thumb-toggle');
    if (thumb) {
      var r = thumb.getBoundingClientRect();
      items.push({ name: 'Thumb toggle', bottom: Math.round(window.innerHeight - r.bottom), right: Math.round(window.innerWidth - r.right), h: Math.round(r.height) });
    }
    return items.sort((a, b) => a.bottom - b.bottom);
  });
  stack.forEach(s => {
    console.log(`  ${s.name}: bottom=${s.bottom}px, right=${s.right}px, height=${s.h}px`);
  });

  await browser.close();
})();
