const { chromium } = require('playwright');

// Causal test for homepage React #418 (hydration mismatch, args=HTML):
// abort live-only site scripts one group at a time and see when the error dies.
const CASES = [
  ['baseline', []],
  ['no-theme-switcher', ['/theme-switcher.js']],
  ['no-theme-trio', ['/theme-switcher.js', '/theme-registry.js', '/theme-animations.js']],
  ['no-ai-assistant', ['/ai-assistant.js']],
  ['no-adsense-integration', ['/adsense-integration.js']],
  ['no-site-scripts-all', ['/theme-switcher.js', '/theme-registry.js', '/theme-animations.js', '/ai-assistant.js', '/adsense-integration.js']],
];

(async () => {
  const b = await chromium.launch();
  for (const [label, blocks] of CASES) {
    const ctx = await b.newContext();
    const p = await ctx.newPage();
    const errs = [];
    p.on('pageerror', e => errs.push(String(e.message).slice(0, 90)));
    if (blocks.length) {
      await p.route('**/*', route => {
        const u = route.request().url();
        if (blocks.some(bl => u.endsWith(bl))) return route.abort();
        return route.continue();
      });
    }
    await p.goto('https://findtorontoevents.ca/', { waitUntil: 'load', timeout: 120000 });
    await p.waitForTimeout(9000);
    const hydr = errs.filter(e => e.includes('418'));
    console.log(JSON.stringify({ case: label, pageErrors: errs.length, hydration418: hydr.length, other: errs.filter(e => !e.includes('418')).slice(0, 2) }));
    await ctx.close();
  }
  await b.close();
})().catch(e => { console.error('HARNESS ERROR', e); process.exit(1); });
