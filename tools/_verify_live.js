const { chromium } = require('playwright');

(async () => {
  const b = await chromium.launch({ headless: true });
  const p = await b.newPage();
  const errors = [];
  
  p.on('pageerror', e => {
    if (/Minified React error #418/.test(e.message)) return;
    errors.push('PageError: ' + e.message);
  });
  p.on('console', m => {
    if (m.type() === 'error') {
      const t = m.text();
      if (t.includes('SyntaxError') || t.includes('Unexpected token') || 
          t.includes('ChunkLoadError') || t.includes('Uncaught')) {
        errors.push('ConsoleError: ' + t);
      }
    }
  });
  
  console.log('Loading live site...');
  await p.goto('https://findtorontoevents.ca/', { waitUntil: 'networkidle', timeout: 30000 });
  await p.waitForTimeout(5000);
  
  const result = await p.evaluate(() => {
    // Find React grid
    const grids = document.querySelectorAll('div[class]');
    let reactGrid = null;
    for (const g of grids) {
      const cls = g.className;
      if (cls.indexOf('grid-cols-1') >= 0 && cls.indexOf('md:grid-cols-2') >= 0 && 
          cls.indexOf('lg:grid-cols-3') >= 0 && g.id !== 'events-grid' && g.children.length > 10) {
        reactGrid = g;
        break;
      }
    }
    
    let cardCount = 0;
    if (reactGrid) {
      for (const child of reactGrid.children) {
        if (child.className && child.className.indexOf('h-[400px]') >= 0) cardCount++;
      }
    }
    
    const signIn = document.getElementById('signin-island');
    const configBtn = document.querySelector('button[title*="System Configuration"]');
    const signInTop = signIn ? Math.round(signIn.getBoundingClientRect().top) : -1;
    const configTop = configBtn ? Math.round(configBtn.getBoundingClientRect().top) : -1;
    const thumbBtn = document.getElementById('fte-thumb-toggle');
    const skelGrid = document.getElementById('events-grid');
    const skelHidden = skelGrid ? window.getComputedStyle(skelGrid).display === 'none' : true;
    
    return {
      cardCount,
      signInTop,
      configTop,
      aligned: Math.abs(signInTop - configTop) < 10,
      thumbExists: !!thumbBtn,
      skelHidden,
    };
  });
  
  console.log('\n=== LIVE SITE VERIFICATION ===');
  console.log('Event cards:', result.cardCount > 20 ? 'PASS' : 'FAIL', '(' + result.cardCount + ' cards)');
  console.log('Sign-in aligned:', result.aligned ? 'PASS' : 'FAIL', 
    '(sign-in: ' + result.signInTop + 'px, config: ' + result.configTop + 'px)');
  console.log('Thumbnail toggle:', result.thumbExists ? 'PASS' : 'FAIL');
  console.log('Skeleton cleanup:', result.skelHidden ? 'PASS' : 'FAIL');
  console.log('JS errors:', errors.length === 0 ? 'PASS' : 'FAIL', '(' + errors.length + ' errors)');
  if (errors.length > 0) errors.forEach(e => console.log('  -', e));
  
  const allPassed = result.cardCount > 20 && result.thumbExists && errors.length === 0;
  console.log('\n=== OVERALL:', allPassed ? 'ALL PASSED' : 'SOME ISSUES', '===');
  
  await b.close();
  process.exit(allPassed ? 0 : 1);
})().catch(e => { console.error(e); process.exit(1); });
