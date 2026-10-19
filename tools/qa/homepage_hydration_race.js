const { chromium } = require('playwright');

// Race probe: did the legacy inline JS mutate #events-grid BEFORE React's
// hydration error #418? Records every mutation with a timestamp and compares
// with the pageerror timing.
(async () => {
  const b = await chromium.launch();
  const p = await (await b.newContext()).newPage();

  await p.addInitScript(() => {
    window.__mutLog = [];
    window.__marks = [];
    const t0 = performance.now();
    const rec = (kind, detail) => window.__mutLog.push({ t: +(performance.now() - t0).toFixed(1), kind, detail });
    const startObs = () => {
      const grid = document.getElementById('events-grid');
      if (!grid) { setTimeout(startObs, 5); return; }
      rec('obs_started', 'grid found; initial children=' + grid.children.length);
      window.__gridInitial = grid.innerHTML.slice(0, 0);
      window.__initialChildren = grid.children.length;
      // snapshot initial inline styles of cards
      window.__initialStyles = [...grid.children].slice(0, 50).map(c => c.getAttribute('style') || '');
      new MutationObserver(muts => {
        for (const m of muts) {
          if (m.type === 'attributes') rec('attr', m.target.tagName + '.' + (m.target.className || '').toString().slice(0, 40) + ' ' + m.attributeName + '=' + String(m.target.getAttribute(m.attributeName)).slice(0, 60));
          else if (m.type === 'childList') rec('childList', 'added=' + m.addedNodes.length + ' removed=' + m.removedNodes.length + ' on ' + (m.target.id || m.target.tagName));
        }
      }).observe(grid, { subtree: true, childList: true, attributes: true });
      // keep watching whole document for grid re-creation
      new MutationObserver(() => {
        const g2 = document.getElementById('events-grid');
        if (g2 && g2 !== window.__gridRef) { window.__gridRef = g2; rec('grid_replaced', ''); }
      }).observe(document.documentElement, { childList: true, subtree: true });
    };
    document.addEventListener('DOMContentLoaded', startObs);
    // wrap console.error to timestamp React's minified error log if any
    const ce = console.error;
    console.error = function (...a) {
      rec('console.error', String(a[0]).slice(0, 80));
      return ce.apply(console, a);
    };
  });

  const errs = [];
  const errTimes = [];
  const t0 = Date.now();
  p.on('pageerror', e => { errs.push(String(e.message).slice(0, 120)); errTimes.push(Date.now() - t0); });

  await p.goto('https://findtorontoevents.ca/', { waitUntil: 'load', timeout: 120000 });
  await p.waitForTimeout(12000);

  const log = await p.evaluate(() => ({ muts: window.__mutLog || [], initial: window.__initialChildren, styles: window.__initialStyles }));
  console.log('pageErrors:', JSON.stringify(errs));
  console.log('pageError ms-after-nav:', JSON.stringify(errTimes));
  console.log('initial children:', log.initial);
  console.log('mutation count:', log.muts.length);
  console.log('first 25 mutations:', JSON.stringify(log.muts.slice(0, 25), null, 1));
  const attrMuts = log.muts.filter(m => m.kind === 'attr');
  console.log('attribute mutations:', attrMuts.length, JSON.stringify(attrMuts.slice(0, 10)));
  console.log('initial card styles sample:', JSON.stringify((log.styles || []).filter(Boolean).slice(0, 5)));
  await b.close();
})().catch(e => { console.error('HARNESS ERROR', e); process.exit(1); });
