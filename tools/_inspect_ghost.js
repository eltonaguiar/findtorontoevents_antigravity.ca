const { chromium } = require('playwright');

(async () => {
  const b = await chromium.launch({ headless: true });
  const p = await b.newPage();
  const errors = [];
  const consoleLog = [];
  
  p.on('pageerror', e => errors.push('PageError: ' + e.message));
  p.on('console', m => {
    if (m.type() === 'error') consoleLog.push('ERR: ' + m.text());
    if (m.type() === 'warning') consoleLog.push('WARN: ' + m.text());
    if (m.text().includes('[THUMBNAILS]')) consoleLog.push('LOG: ' + m.text());
    if (m.text().includes('[EventFeed]')) consoleLog.push('LOG: ' + m.text());
    if (m.text().includes('[STATIC')) consoleLog.push('LOG: ' + m.text());
  });
  
  await p.goto('http://localhost:5173/', { waitUntil: 'networkidle', timeout: 30000 });
  await p.waitForTimeout(5000);
  
  const result = await p.evaluate(() => {
    // Real event cards (not skeletons)
    const glassPanels = document.querySelectorAll('.glass-panel:not(.animate-pulse)');
    const visibleCards = [];
    const invisibleCards = [];
    
    glassPanels.forEach((card, i) => {
      const rect = card.getBoundingClientRect();
      const style = window.getComputedStyle(card);
      const isVisible = style.display !== 'none' && 
                        style.visibility !== 'hidden' && 
                        parseFloat(style.opacity) > 0.1 &&
                        rect.width > 0 && rect.height > 0;
      
      const title = card.querySelector('h3') || card.querySelector('h2');
      const titleText = title ? title.textContent.substring(0, 40) : '(no title)';
      
      if (isVisible) {
        visibleCards.push({ i, titleText, w: Math.round(rect.width), h: Math.round(rect.height), opacity: style.opacity, top: Math.round(rect.top) });
      } else {
        invisibleCards.push({ i, titleText, display: style.display, visibility: style.visibility, opacity: style.opacity, w: Math.round(rect.width), h: Math.round(rect.height) });
      }
    });
    
    // Check for skeleton cards still present
    const skeletons = document.querySelectorAll('.animate-pulse');
    
    // Check for event grid
    const grids = document.querySelectorAll('[class*="grid"][class*="grid-cols"]');
    const gridInfos = [];
    grids.forEach(g => {
      gridInfos.push({
        tag: g.tagName,
        id: g.id || '',
        childCount: g.children.length,
        className: g.className.substring(0, 120)
      });
    });
    
    // Check for h-[400px] wrappers (event card wrappers)
    const h400 = document.querySelectorAll('[class*="h-[400px]"]');
    const h320 = document.querySelectorAll('[class*="h-[320px]"]');
    
    // Check body structure
    const bodyChildren = Array.from(document.body.children).map(c => ({
      tag: c.tagName,
      id: c.id || '',
      className: (c.className || '').substring(0, 80),
      visible: window.getComputedStyle(c).display !== 'none'
    }));
    
    return {
      totalGlassPanels: glassPanels.length,
      visibleCount: visibleCards.length,
      invisibleCount: invisibleCards.length,
      visibleSample: visibleCards.slice(0, 5),
      invisibleSample: invisibleCards.slice(0, 5),
      skeletonCount: skeletons.length,
      gridInfos: gridInfos,
      h400Count: h400.length,
      h320Count: h320.length,
      bodyChildCount: bodyChildren.length,
      bodyChildren: bodyChildren.slice(0, 15),
    };
  });
  
  console.log('\n=== PAGE INSPECTION ===');
  console.log(JSON.stringify(result, null, 2));
  
  console.log('\n=== CONSOLE MESSAGES ===');
  consoleLog.forEach(l => console.log(l));
  
  console.log('\n=== PAGE ERRORS (' + errors.length + ') ===');
  errors.forEach(e => console.log(e));
  
  await b.close();
  process.exit(0);
})().catch(e => { console.error(e); process.exit(1); });
