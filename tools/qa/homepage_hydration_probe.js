const { chromium } = require('playwright');

// Localizes the homepage React minified error #418 (hydration mismatch):
// captures the uncaught error stack, pulls the offending _next chunk, and
// prints the minified source around the stack column so the component can be
// identified. Also reports final URL + widget counters.
(async () => {
  const b = await chromium.launch();
  const p = await (await b.newContext()).newPage();
  const errs = [];
  p.on('pageerror', e => errs.push({ msg: String(e.message).slice(0, 300), stack: String(e.stack || '') }));

  const t0 = Date.now();
  await p.goto('https://findtorontoevents.ca/', { waitUntil: 'load', timeout: 120000 });
  await p.waitForTimeout(12000);

  const info = await p.evaluate(() => ({
    finalUrl: location.href,
    pathname: location.pathname,
    bodyChars: document.body.innerText.length,
    eventLinks: document.querySelectorAll('a[href*="/event"], .event-card, .card').length,
    reactRoots: [...document.querySelectorAll('[data-reactroot], #__next, [id*=next]')].map(e => e.id || e.tagName).slice(0, 8),
  }));
  console.log('PAGE INFO', JSON.stringify(info, null, 1));
  console.log('PAGE ERRORS', errs.length);
  for (const e of errs) {
    console.log('--- msg:', e.msg);
    console.log('--- stack:', e.stack.split('\n').slice(0, 6).join('\n'));
  }

  // find the first _next chunk reference in any stack and pull context
  for (const e of errs) {
    const m = e.stack.match(/(https:\/\/[^"'\s]+?_next\/static\/chunks\/[^"'\s]+?):(\d+):(\d+)/);
    if (!m) { console.log('no _next chunk in stack'); continue; }
    const [, url, line, col] = m;
    console.log('CHUNK', url, 'line', line, 'col', col);
    const txt = await p.evaluate(async u => (await fetch(u)).text(), url).catch(err => 'FETCH FAIL ' + err);
    if (typeof txt !== 'string' || txt.startsWith('FETCH FAIL')) { console.log(txt); continue; }
    const srcLines = txt.split('\n');
    const target = srcLines[parseInt(line, 10) - 1] || srcLines[0];
    const c = parseInt(col, 10);
    console.log('len(line)=', target.length, 'total lines=', srcLines.length);
    console.log('SNIPPET AROUND COL:', '\n...' + target.slice(Math.max(0, c - 350), c + 350) + '...');
  }

  await b.close();
})().catch(e => { console.error('HARNESS ERROR', e); process.exit(1); });
