const { chromium } = require('playwright');

(async () => {
  const b = await chromium.launch({ headless: true });
  const p = await b.newPage();
  
  await p.goto('http://localhost:5173/', { waitUntil: 'networkidle', timeout: 30000 });
  await p.waitForTimeout(5000);
  
  const result = await p.evaluate(() => {
    // Find the 3 hidden cards and inspect why
    const glassPanels = document.querySelectorAll('.glass-panel:not(.animate-pulse)');
    const hiddenCards = [];
    
    glassPanels.forEach((card, i) => {
      const style = window.getComputedStyle(card);
      if (style.display === 'none') {
        const title = card.querySelector('h3, h2');
        const parent = card.parentElement;
        const grandparent = parent ? parent.parentElement : null;
        
        // Check inline style vs computed style
        hiddenCards.push({
          i,
          title: title ? title.textContent.substring(0, 60) : '(no title)',
          inlineStyle: card.style.cssText,
          parentInlineStyle: parent ? parent.style.cssText : '',
          parentClass: parent ? parent.className.substring(0, 120) : '',
          parentDisplay: parent ? window.getComputedStyle(parent).display : '',
          grandparentClass: grandparent ? grandparent.className.substring(0, 120) : '',
          grandparentDisplay: grandparent ? window.getComputedStyle(grandparent).display : '',
          // Check if an ad element is nearby
          prevSibling: card.previousElementSibling ? {
            tag: card.previousElementSibling.tagName,
            className: (card.previousElementSibling.className || '').substring(0, 80)
          } : null,
          nextSibling: card.nextElementSibling ? {
            tag: card.nextElementSibling.tagName,
            className: (card.nextElementSibling.className || '').substring(0, 80)
          } : null,
        });
      }
    });
    
    // Also check if suppressHydrationWarning is on html
    const htmlAttrs = {};
    for (let attr of document.documentElement.attributes) {
      htmlAttrs[attr.name] = attr.value;
    }
    
    // Check if there are any ins (ad) elements in the event grid
    const mainGrid = document.querySelector('.grid.grid-cols-1.md\\:grid-cols-2.lg\\:grid-cols-3.xl\\:grid-cols-4.gap-6');
    const adsInGrid = mainGrid ? mainGrid.querySelectorAll('ins, iframe, [class*="adsbygoogle"]') : [];
    
    // Check remaining skeletons
    const skeletons = document.querySelectorAll('.animate-pulse');
    const skeletonInfo = [];
    skeletons.forEach((skel, i) => {
      const rect = skel.getBoundingClientRect();
      const style = window.getComputedStyle(skel);
      skeletonInfo.push({
        i,
        tag: skel.tagName,
        className: skel.className.substring(0, 100),
        display: style.display,
        visible: style.display !== 'none' && style.visibility !== 'hidden' && parseFloat(style.opacity) > 0.1,
        top: Math.round(rect.top),
        height: Math.round(rect.height),
        parentTag: skel.parentElement ? skel.parentElement.tagName : '',
      });
    });
    
    return {
      hiddenCards,
      htmlAttrs,
      adsInGridCount: adsInGrid.length,
      skeletonInfo,
    };
  });
  
  console.log('\n=== HIDDEN CARDS ===');
  console.log(JSON.stringify(result.hiddenCards, null, 2));
  
  console.log('\n=== HTML ATTRIBUTES ===');
  console.log(JSON.stringify(result.htmlAttrs, null, 2));
  
  console.log('\n=== ADS IN GRID ===');
  console.log('Count:', result.adsInGridCount);
  
  console.log('\n=== SKELETONS STILL PRESENT ===');
  console.log(JSON.stringify(result.skeletonInfo, null, 2));
  
  await b.close();
  process.exit(0);
})().catch(e => { console.error(e); process.exit(1); });
