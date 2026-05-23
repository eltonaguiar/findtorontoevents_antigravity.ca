const { chromium } = require('@playwright/test');
(async () => {
  const b = await chromium.launch({ headless: true });
  const p = await b.newPage();
  // Intercept the page and inject a watcher BEFORE the real code runs
  await p.addInitScript(() => {
    // Watch for #custom-filter-controls to appear
    const observer = new MutationObserver(muts => {
      for (const m of muts) {
        for (const node of m.addedNodes) {
          if (node.nodeType === 1 && node.id === 'custom-filter-controls') {
            console.log('DETECTED: #custom-filter-controls added to DOM at', Date.now());
            observer.disconnect();
          }
        }
      }
    });
    observer.observe(document.documentElement, { childList: true, subtree: true });
    // Also patch addEventListener to detect when DOMContentLoaded is registered
    const origAdd = document.addEventListener.bind(document);
    document.addEventListener = function(type, fn, opts) {
      if (type === 'DOMContentLoaded') {
        console.log('DOMContentLoaded listener registered at readyState:', document.readyState);
      }
      return origAdd(type, fn, opts);
    };
  });
  const jsLogs = [];
  p.on('console', m => jsLogs.push(m.type() + ': ' + m.text().substring(0, 100)));
  p.on('pageerror', e => jsLogs.push('PAGEERROR: ' + e.message.substring(0, 100)));
  await p.goto('https://findtorontoevents.ca/', { waitUntil: 'domcontentloaded', timeout: 20000 });
  await new Promise(r => setTimeout(r, 5000));
  const fcExists = await p.evaluate(() => !!document.getElementById('custom-filter-controls'));
  console.log('After 5s, fcExists:', fcExists);
  // Show relevant console messages
  const relevant = jsLogs.filter(l => l.includes('FILTER') || l.includes('DOMContent') || l.includes('DETECTED') || l.includes('PAGEERROR'));
  console.log('Relevant logs:', relevant.slice(0, 10));
  console.log('All logs (first 10):', jsLogs.slice(0, 10));
  await b.close();
})().catch(e => console.error('ERROR:', e.message));
