const { chromium } = require('playwright');

// Precise: logs EVERY childList/attr mutation after DOMContentLoaded with a
// DOM-path of the target and what was added/removed, plus in-page timestamps
// for the React hydration error, so the pre-hydration DOM change that breaks
// hydration (React #418, args=HTML) can be identified exactly.
(async () => {
  const b = await chromium.launch();
  const p = await (await b.newContext()).newPage();

  await p.addInitScript(() => {
    window.__log = [];
    const t0 = performance.now();
    const path = (n) => {
      if (!n || n.nodeType !== 1) return String(n && n.nodeName);
      const parts = [];
      let e = n;
      for (let d = 0; e && d < 6; d++) {
        let s = e.tagName.toLowerCase();
        if (e.id) { s += '#' + e.id; parts.unshift(s); break; }
        if (e.className && typeof e.className === 'string') s += '.' + e.className.trim().split(/\s+/).slice(0, 2).join('.');
        parts.unshift(s);
        e = e.parentElement;
      }
      return parts.join('>');
    };
    const tag = (n) => n.nodeType === 1 ? n.tagName.toLowerCase() + (n.id ? '#' + n.id : '') : '#text';
    window.__rec = (kind, detail) => window.__log.push({ t: +(performance.now() - t0).toFixed(1), kind, detail });
    window.addEventListener('error', ev => window.__rec('PAGEERROR', String(ev.message).slice(0, 100)));
    document.addEventListener('DOMContentLoaded', () => {
      window.__rec('DCL', '');
      new MutationObserver(muts => {
        for (const m of muts) {
          if (m.type === 'childList') {
            const added = [...m.addedNodes].map(tag).join(',') || '-';
            const removed = [...m.removedNodes].map(tag).join(',') || '-';
            if (added === '-' && removed === '-') continue;
            window.__rec('childList', path(m.target) + ' +' + added + ' -' + removed);
          } else if (m.type === 'attributes') {
            window.__rec('attr', path(m.target) + ' ' + m.attributeName + '=' + String(m.target.getAttribute(m.attributeName)).slice(0, 80));
          }
        }
      }).observe(document.documentElement, { subtree: true, childList: true, attributes: true, attributeOldValue: false });
    });
  });

  const nodeErrs = [];
  p.on('pageerror', e => nodeErrs.push(String(e.message).slice(0, 100)));

  await p.goto('https://findtorontoevents.ca/', { waitUntil: 'load', timeout: 120000 });
  await p.waitForTimeout(8000);

  const out = await p.evaluate(() => ({ log: window.__log || [], n: (window.__log || []).length }));
  console.log('node pageerrors:', JSON.stringify(nodeErrs));
  console.log('total mutations:', out.n);
  const first40 = out.log.slice(0, 40);
  for (const m of first40) console.log(String(m.t).padStart(7), m.kind.padEnd(10), m.detail.slice(0, 180));
  const errIdx = out.log.findIndex(m => m.kind === 'PAGEERROR');
  console.log('--- PAGEERROR at index', errIdx, errIdx >= 0 ? out.log[errIdx] : '');
  if (errIdx > 0) {
    console.log('--- 6 mutations BEFORE error:');
    for (const m of out.log.slice(Math.max(0, errIdx - 6), errIdx)) console.log(String(m.t).padStart(7), m.kind.padEnd(10), m.detail.slice(0, 180));
  }
  const attrAfter = out.log.filter(m => m.kind === 'attr').slice(0, 8);
  console.log('--- attribute mutations (first 8):');
  for (const m of attrAfter) console.log(String(m.t).padStart(7), 'attr'.padEnd(10), m.detail.slice(0, 180));
  await b.close();
})().catch(e => { console.error('HARNESS ERROR', e); process.exit(1); });
