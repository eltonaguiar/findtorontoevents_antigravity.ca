const { chromium } = require('playwright');

(async () => {
  const b = await chromium.launch({ headless: true });
  const p = await b.newPage();
  
  await p.goto('http://localhost:5173/', { waitUntil: 'networkidle', timeout: 30000 });
  await p.waitForTimeout(5000);
  
  const result = await p.evaluate(() => {
    // Find config button (gear icon) 
    const allButtons = document.querySelectorAll('button[title*="Configuration"], button[title*="Config"]');
    const configBtns = [];
    for (const btn of allButtons) {
      const rect = btn.getBoundingClientRect();
      const style = window.getComputedStyle(btn);
      configBtns.push({
        title: btn.title,
        rect: { top: Math.round(rect.top), right: Math.round(window.innerWidth - rect.right), width: Math.round(rect.width), height: Math.round(rect.height) },
        parentId: btn.parentElement ? btn.parentElement.id || '' : '',
        parentClass: btn.parentElement ? btn.parentElement.className.substring(0, 100) : '',
        visible: style.display !== 'none' && rect.width > 0,
      });
    }
    
    // Find sign-in island
    const signIn = document.getElementById('signin-island');
    let signInInfo = null;
    if (signIn) {
      const rect = signIn.getBoundingClientRect();
      const style = window.getComputedStyle(signIn);
      signInInfo = {
        rect: { top: Math.round(rect.top), right: Math.round(window.innerWidth - rect.right), width: Math.round(rect.width), height: Math.round(rect.height) },
        position: style.position,
        inlineStyle: signIn.style.cssText.substring(0, 200),
        parentTag: signIn.parentElement ? signIn.parentElement.tagName : '',
        parentId: signIn.parentElement ? signIn.parentElement.id || '' : '',
      };
    }
    
    // Find top-right-buttons
    const topRightBar = document.getElementById('top-right-buttons');
    
    return { configBtns, signInInfo, topRightBarExists: !!topRightBar };
  });
  
  console.log('Config buttons:', JSON.stringify(result.configBtns, null, 2));
  console.log('\nSign-in island:', JSON.stringify(result.signInInfo, null, 2));
  console.log('\ntop-right-buttons exists:', result.topRightBarExists);
  
  await b.close();
  process.exit(0);
})().catch(e => { console.error(e); process.exit(1); });
