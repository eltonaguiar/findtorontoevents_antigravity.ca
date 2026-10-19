const { chromium } = require('playwright');

// Fast-path (no delays) run of the PATCHED local page: whole-document mutation
// log with timestamps + error timestamp, to catch the mutation that lands
// DURING React's hydration walk (content itself is proven clean by the slow run).
const BASE = 'http://localhost:5202';

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
      for (let d = 0; e && d < 5; d++) {
        let s = e.tagName.toLowerCase();
        if (e.id) { s += '#' + e.id; parts.unshift(s); break; }
        if (e.className && typeof e.className === 'string' && e.className.trim()) s += '.' + e.className.trim().split(/\s+/)[0];
        parts.unshift(s);
        e = e.parentElement;
      }
      return parts.join('>');
    };
    const tag = (n) => n.nodeType === 1 ? n.tagName.toLowerCase() + (n.id ? '#' + n.id : '') : '#text';
    window.__rec = (k, d) => window.__log.push({ t: +(performance.now() - t0).toFixed(1), k, d });
    window.addEventListener('error', ev => window.__rec('PAGEERROR', String(ev.message).slice(0, 80)));
    document.addEventListener('DOMContentLoaded', () => {
      window.__rec('DCL', '');
      new MutationObserver(muts => {
        for (const m of muts) {
          if (m.type === 'childList') {
            const a = [...m.addedNodes].map(tag).join(',') || '-';
            const r = [...m.removedNodes].map(tag).join(',') || '-';
            if (a === '-' && r === '-') continue;
            window.__rec('childList', path(m.target) + ' +' + a + ' -' + r);
          } else if (m.type === 'attributes') {
            window.__rec('attr', path(m.target) + ' [' + m.attributeName + ']=' + String(m.target.getAttribute(m.attributeName)).slice(0, 60));
          }
        }
      }).observe(document.documentElement, { subtree: true, childList: true, attributes: true });
    });
  });

  const errs = [];
  p.on('pageerror', e => errs.push(String(e.message).slice(0, 70)));

  await p.route('**/*', async route => {
    const u = new URL(route.request().url());
    if (u.origin !== BASE) return route.continue();
    if (u.pathname === '/index.html') return route.continue();
    try {
      const resp = await route.fetch({ url: 'https://findtorontoevents.ca' + u.pathname + u.search });
      return route.fulfill({ response: resp });
    } catch (e) { return route.abort(); }
  });

  await p.goto(BASE + '/index.html', { waitUntil: 'load', timeout: 120000 });
  await p.waitForTimeout(6000);

  const out = await p.evaluate(() => window.__log || []);
  console.log('pageerrors:', JSON.stringify(errs));
  console.log('total mutations:', out.length);
  const ei = out.findIndex(m => m.k === 'PAGEERROR');
  console.log('error at index', ei, ei >= 0 ? out[ei].t : '');
  const start = Math.max(0, (ei >= 0 ? ei : out.length) - 25);
  console.log('--- window around error (25 entries before):');
  for (const m of out.slice(start, Math.min(out.length, (ei >= 0 ? ei : out.length) + 5))) {
    console.log(String(m.t).padStart(8), m.k.padEnd(10), m.d.slice(0, 165));
  }
  await b.close();
})().catch(e => { console.error('HARNESS ERROR', e); process.exit(1); });
