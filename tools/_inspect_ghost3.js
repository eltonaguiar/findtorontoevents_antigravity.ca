const { chromium } = require('playwright');

(async () => {
  const b = await chromium.launch({ headless: true });
  const p = await b.newPage();
  
  await p.goto('http://localhost:5173/', { waitUntil: 'networkidle', timeout: 30000 });
  await p.waitForTimeout(5000);
  
  const result = await p.evaluate(() => {
    // Find a hidden glass-panel card and check what CSS rules apply
    const glassPanels = document.querySelectorAll('.glass-panel:not(.animate-pulse)');
    const hiddenInfo = [];
    
    for (const card of glassPanels) {
      const style = window.getComputedStyle(card);
      if (style.display === 'none') {
        // Get the full class list
        const classes = card.className;
        // Get the grandparent's full class list 
        const gp = card.parentElement?.parentElement;
        // Check if grandparent has display:none via another mechanism
        const gpStyle = gp ? window.getComputedStyle(gp) : null;
        
        // Check all stylesheets for matching display:none rules
        const matchingRules = [];
        for (const sheet of document.styleSheets) {
          try {
            for (const rule of sheet.cssRules) {
              if (rule.style && rule.style.display === 'none') {
                try {
                  if (card.matches(rule.selectorText)) {
                    matchingRules.push({
                      selector: rule.selectorText,
                      display: rule.style.display,
                      sheet: sheet.href || '(inline)'
                    });
                  }
                } catch(e) {}
              }
            }
          } catch(e) {}
        }
        
        hiddenInfo.push({
          classes: classes.substring(0, 200),
          gpClasses: gp ? gp.className.substring(0, 150) : '',
          gpDisplay: gpStyle ? gpStyle.display : '',
          matchingRules,
        });
        
        if (hiddenInfo.length >= 2) break;
      }
    }
    
    // Also check if there are TWO event grids on the page
    const allGrids = document.querySelectorAll('[class*="grid-cols-1"][class*="md:grid-cols-2"][class*="lg:grid-cols-3"]');
    const gridInfo = [];
    allGrids.forEach(g => {
      gridInfo.push({
        id: g.id || '',
        childCount: g.children.length,
        parentId: g.parentElement ? g.parentElement.id || '' : '',
        firstChildClass: g.firstElementChild ? g.firstElementChild.className.substring(0, 80) : '',
        isVisible: window.getComputedStyle(g).display !== 'none',
        top: Math.round(g.getBoundingClientRect().top),
      });
    });
    
    return { hiddenInfo, gridInfo };
  });
  
  console.log('\n=== HIDDEN CARD CSS RULES ===');
  console.log(JSON.stringify(result.hiddenInfo, null, 2));
  
  console.log('\n=== ALL EVENT GRIDS ===');
  console.log(JSON.stringify(result.gridInfo, null, 2));
  
  await b.close();
  process.exit(0);
})().catch(e => { console.error(e); process.exit(1); });
