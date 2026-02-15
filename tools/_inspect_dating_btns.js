const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  // Test on mobile viewport too
  const page = await browser.newPage({ viewport: { width: 375, height: 812 } }); // iPhone-like

  console.log('Loading page (mobile viewport 375x812)...');
  await page.goto('http://localhost:5173/index.html', { waitUntil: 'networkidle', timeout: 25000 });
  await page.waitForTimeout(6000);

  // 1. Find all buttons containing "Dating"
  console.log('\n=== Dating Buttons ===');
  const datingBtns = await page.evaluate(() => {
    var results = [];
    var allEls = document.querySelectorAll('button, a, [role="button"]');
    for (var i = 0; i < allEls.length; i++) {
      var el = allEls[i];
      var txt = el.textContent.trim();
      if (/dating/i.test(txt) && txt.length < 100) {
        var rect = el.getBoundingClientRect();
        results.push({
          tag: el.tagName,
          text: txt.substring(0, 80),
          class: (el.className || '').substring(0, 100),
          rect: { top: Math.round(rect.top), left: Math.round(rect.left), w: Math.round(rect.width), h: Math.round(rect.height) },
          visible: rect.width > 0 && rect.height > 0
        });
      }
    }
    return results;
  });
  console.log('Found', datingBtns.length, 'dating-related buttons:');
  datingBtns.forEach((b, i) => {
    console.log(`  ${i + 1}. <${b.tag}> "${b.text}" | pos: top=${b.rect.top} left=${b.rect.left} | size: ${b.rect.w}x${b.rect.h} | visible: ${b.visible}`);
  });

  // 2. Check "Honey Social Club" event
  console.log('\n=== Honey Social Club Event ===');
  const honeyEvent = await page.evaluate(() => {
    var cards = document.querySelectorAll('[class*="glass-panel"]:not(.animate-pulse)');
    var found = [];
    cards.forEach(function(c) {
      var t = c.querySelector('h2, h3');
      if (t && /honey.social/i.test(t.textContent)) {
        found.push({
          title: t.textContent.substring(0, 80),
          hidden: c.classList.contains('event-card-hidden'),
          visible: window.getComputedStyle(c).display !== 'none'
        });
      }
    });
    return found;
  });
  console.log('Honey Social Club cards:', honeyEvent.length);
  honeyEvent.forEach(e => console.log('  Title:', e.title, '| hidden:', e.hidden, '| visible:', e.visible));

  // 3. Check bell icon and thumbnail toggle positions
  console.log('\n=== Fixed Bottom-Right Icons (Mobile) ===');
  const fixedIcons = await page.evaluate(() => {
    var icons = [];
    // Bell / notification
    var allFixed = document.querySelectorAll('[class*="fixed"][class*="bottom"]');
    allFixed.forEach(function(el) {
      var rect = el.getBoundingClientRect();
      if (rect.right > window.innerWidth - 100 && rect.bottom > window.innerHeight - 300) {
        icons.push({
          id: el.id || '(no id)',
          tag: el.tagName,
          text: el.textContent.trim().substring(0, 40),
          rect: { top: Math.round(rect.top), right: Math.round(window.innerWidth - rect.right), bottom: Math.round(window.innerHeight - rect.bottom), w: Math.round(rect.width), h: Math.round(rect.height) }
        });
      }
    });
    // Thumbnail toggle
    var thumb = document.getElementById('fte-thumb-toggle');
    if (thumb) {
      var r = thumb.getBoundingClientRect();
      icons.push({
        id: 'fte-thumb-toggle',
        tag: 'BUTTON',
        text: thumb.title || 'thumbnail toggle',
        rect: { top: Math.round(r.top), right: Math.round(window.innerWidth - r.right), bottom: Math.round(window.innerHeight - r.bottom), w: Math.round(r.width), h: Math.round(r.height) }
      });
    }
    return icons;
  });
  console.log('Bottom-right fixed elements:');
  fixedIcons.forEach(i => {
    console.log(`  ${i.id} <${i.tag}> "${i.text}" | top=${i.rect.top} right=${i.rect.right} bottom=${i.rect.bottom} | ${i.rect.w}x${i.rect.h}`);
  });

  // 4. Check overlap
  console.log('\n=== Overlap Check ===');
  const overlapCheck = await page.evaluate(() => {
    var thumb = document.getElementById('fte-thumb-toggle');
    if (!thumb) return { hasThumb: false };
    var thumbRect = thumb.getBoundingClientRect();

    // Find the nearest fixed element below the thumb
    var bellLike = null;
    var allFixed = document.querySelectorAll('button[class*="fixed"], [class*="fixed"] button');
    var allBottomRight = [];
    document.querySelectorAll('*').forEach(function(el) {
      if (el === thumb) return;
      var cs = window.getComputedStyle(el);
      if (cs.position === 'fixed') {
        var r = el.getBoundingClientRect();
        if (r.right > window.innerWidth - 100 && r.bottom > window.innerHeight - 300 && r.width > 20 && r.height > 20) {
          allBottomRight.push({
            id: el.id || el.className.substring(0, 50),
            rect: { top: Math.round(r.top), bottom: Math.round(r.bottom), left: Math.round(r.left), right: Math.round(r.right) }
          });
        }
      }
    });

    // Check if thumb overlaps any
    var overlaps = [];
    allBottomRight.forEach(function(el) {
      if (thumbRect.bottom > el.rect.top && thumbRect.top < el.rect.bottom &&
          thumbRect.right > el.rect.left && thumbRect.left < el.rect.right) {
        overlaps.push(el.id);
      }
    });

    return {
      hasThumb: true,
      thumbRect: { top: Math.round(thumbRect.top), bottom: Math.round(thumbRect.bottom), right: Math.round(thumbRect.right) },
      bottomRightElements: allBottomRight.length,
      overlaps: overlaps
    };
  });
  console.log('Thumb toggle exists:', overlapCheck.hasThumb);
  if (overlapCheck.hasThumb) {
    console.log('Thumb rect:', JSON.stringify(overlapCheck.thumbRect));
    console.log('Other bottom-right fixed elements:', overlapCheck.bottomRightElements);
    console.log('Overlapping elements:', overlapCheck.overlaps.length > 0 ? overlapCheck.overlaps.join(', ') : 'NONE');
  }

  // 5. Now click "Dating" button and check if Honey Social Club appears
  console.log('\n=== Dating Filter Test ===');
  if (datingBtns.length >= 1) {
    for (let idx = 0; idx < datingBtns.length; idx++) {
      const btn = datingBtns[idx];
      if (!btn.visible) continue;
      console.log(`  Clicking dating button #${idx + 1} at top=${btn.rect.top}...`);
      try {
        await page.evaluate((btnText) => {
          var allEls = document.querySelectorAll('button, a, [role="button"]');
          for (var i = 0; i < allEls.length; i++) {
            if (allEls[i].textContent.trim().substring(0, 80) === btnText) {
              allEls[i].click();
              break;
            }
          }
        }, btn.text);
        await page.waitForTimeout(2000);

        const cards = await page.evaluate(() => {
          var cs = document.querySelectorAll('[class*="glass-panel"]:not(.animate-pulse)');
          var visible = [];
          cs.forEach(function(c) {
            if (c.classList.contains('event-card-hidden')) return;
            var w = c.parentElement;
            var mx = 3;
            while (w && mx > 0) { if (w.className && w.className.indexOf('h-[400px]') >= 0) break; w = w.parentElement; mx--; }
            if (w && w.classList.contains('event-wrapper-hidden')) return;
            var t = c.querySelector('h2, h3');
            if (t) visible.push(t.textContent.substring(0, 60));
          });
          return visible;
        });
        console.log(`    Visible cards: ${cards.length}`);
        var hasHoney = cards.some(c => /honey.social/i.test(c));
        console.log(`    Has "Honey Social Club": ${hasHoney}`);
        if (!hasHoney && cards.length < 20) {
          console.log('    Cards:', cards.join(' | '));
        }
      } catch (e) {
        console.log('    Error clicking:', e.message);
      }
    }
  }

  await browser.close();
})();
