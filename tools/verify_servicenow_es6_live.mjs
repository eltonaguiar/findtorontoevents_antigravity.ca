#!/usr/bin/env node
/**
 * Standalone Playwright verification against the LIVE deployed page.
 * Confirms the ES6 examples section renders without overflow on the real URL,
 * including a page-level horizontal-overflow sweep at 390/768/1024/1280/1440px.
 *
 * Usage: node tools/verify_servicenow_es6_live.mjs
 */
import { chromium } from 'playwright';

const URL = `https://findtorontoevents.ca/servicenow/javascript/index.html?cb=${Date.now()}`;

const VIEWPORTS = [390, 768, 1024, 1280, 1440];
const TOLERANCE = 2; // px — sub-pixel rounding on the .page max-width

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });

const errors = [];
page.on('pageerror', (e) => errors.push(e.message));

const resp = await page.goto(URL, { waitUntil: 'domcontentloaded' });
console.log(`[HTTP] status=${resp?.status()}`);

// 1. New heading present
const headingCount = await page.locator('h3:has-text("Production-Grade ServiceNow Examples")').count();
console.log(`[Heading] "Production-Grade ServiceNow Examples" count = ${headingCount}`);

// 2. Single-column ES6 grid with 5 cards
const es6Grid = page.locator('.api-grid.es6-examples');
const gridCount = await es6Grid.count();
const cardCount = await es6Grid.locator('.api-card').count();
console.log(`[ES6 Grid] count = ${gridCount}, cards = ${cardCount}`);

// 3. Old Animal/Dog code absent from ES6 section
const es6Text = await es6Grid.innerText();
const hasOldAnimal = es6Text.includes('var Animal = Class.create()');
const hasOldDog = es6Text.includes('Dog.prototype = Object.extendsObject');
console.log(`[Old code] Animal present = ${hasOldAnimal}, Dog present = ${hasOldDog}`);

// 4. Grid overflow
const gridMetrics = await es6Grid.evaluate((el) => ({
  scrollWidth: el.scrollWidth,
  clientWidth: el.clientWidth,
  overflow: el.scrollWidth > el.clientWidth + 2,
}));
console.log(`[ES6 Grid] scrollWidth=${gridMetrics.scrollWidth}, clientWidth=${gridMetrics.clientWidth}, overflow=${gridMetrics.overflow}`);

// 5. Each card's pre block. NOTE: scrollWidth > clientWidth on a pre is CORRECT
//    behavior (code scrolls inside the block), so informational only.
const preMetrics = await page.locator('.api-grid.es6-examples .api-card pre').evaluateAll((els) =>
  els.map((el, i) => ({
    i: i + 1,
    scrollWidth: el.scrollWidth,
    clientWidth: el.clientWidth,
    overflow: el.scrollWidth > el.clientWidth + 2,
  }))
);
for (const m of preMetrics) {
  console.log(`[Card ${m.i} pre] scrollWidth=${m.scrollWidth}, clientWidth=${m.clientWidth}, scrollsInternally=${m.overflow}`);
}

// 5b. Quick Reference must ship all three patterns (GetById/Count were added
//     after the previous upload and silently never deployed)
const quickrefFiles = await page.locator('#quickref .filename').allInnerTexts();
console.log(`[QuickRef] patterns = ${JSON.stringify(quickrefFiles)}`);

// 5c. Footer menu must link every ServiceNow guide, and every link must resolve
const footerLinks = await page.locator('.footer-nav a').evaluateAll((els) => els.map((e) => ({ text: e.textContent.trim(), href: e.getAttribute('href') })));
console.log(`[Footer] ${footerLinks.length} links = ${JSON.stringify(footerLinks.map((l) => l.text))}`);
const linkStatus = [];
for (const l of footerLinks) {
  if (!l.href || !l.href.startsWith('/')) continue;
  try {
    const r = await page.request.get(`https://findtorontoevents.ca${l.href}?cb=${Date.now()}`);
    linkStatus.push({ text: l.text, href: l.href, status: r.status() });
  } catch (e) {
    linkStatus.push({ text: l.text, href: l.href, status: -1 });
  }
}
for (const l of linkStatus) console.log(`[Footer link] ${l.href} -> ${l.status} (${l.text})`);

// 5d. Scroll progress bar: present, position:fixed (out of flow — cannot affect
//     layout or scrollWidth), and it actually updates as the page scrolls.
const prog = page.locator('#scroll-progress');
const progCount = await prog.count();
let progPosition = 'missing', progStart = '', progMid = '', progEnd = '', progMoves = false;
if (progCount === 1) {
  progPosition = await prog.evaluate((el) => getComputedStyle(el).position);
  // The page sets html{scroll-behavior:smooth}, so scrollTo() animates. Disable it
  // for the measurement or we sample the bar mid-animation and read a false low value.
  await page.evaluate(() => { document.documentElement.style.scrollBehavior = 'auto'; });
  progStart = await prog.evaluate((el) => el.style.transform);
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight / 2));
  await page.waitForTimeout(120);
  progMid = await prog.evaluate((el) => el.style.transform);
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await page.waitForTimeout(120);
  progEnd = await prog.evaluate((el) => el.style.transform);
  const num = (s) => parseFloat(String(s).replace(/[^0-9.]/g, '')) || 0;
  progMoves = num(progEnd) > num(progStart) && num(progEnd) >= 0.9;
  await page.evaluate(() => window.scrollTo(0, 0));
}
console.log(`[Progress] count=${progCount} position=${progPosition} transform start=${progStart || '(none)'} mid=${progMid || '(none)'} end=${progEnd || '(none)'} moves=${progMoves}`);

// 5e. Decision table must expose UI Policy as a first-class artifact column.
//     7 columns (Scenario + 6 artifacts), UI Policy marked on the 3 form-behavior rows.
const dtHead = await page.locator('#decision-table thead th').allInnerTexts();
const dtRowCount = await page.locator('#decision-table tbody tr').count();
const dtPolicyMarks = await page.locator('#decision-table tbody tr').evaluateAll((rows) =>
  rows.filter((r) => (r.children[1].textContent || '').trim().length > 0).length
);
console.log(`[DecisionTable] head=${JSON.stringify(dtHead.map((h) => h.trim()))} rows=${dtRowCount} uiPolicyMarks=${dtPolicyMarks}`);
const dtOk = dtHead.length === 7 && dtHead[1].trim() === 'UI Policy' && dtRowCount === 8 && dtPolicyMarks === 3;

// 6. Page-level horizontal overflow sweep across viewports.
//    Invariant is on the DOCUMENT (does the page scroll sideways), not on pre blocks.
const sweep = [];
for (const width of VIEWPORTS) {
  const p = await browser.newPage({ viewport: { width, height: 900 } });
  await p.goto(URL, { waitUntil: 'domcontentloaded' });
  const m = await p.evaluate(() => {
    const d = document.documentElement;
    const clipped = (el) => {
      for (let n = el.parentElement; n && n !== document.body; n = n.parentElement) {
        const s = getComputedStyle(n);
        if (s.overflowX !== 'visible' || s.overflowY !== 'visible') return true;
      }
      return false;
    };
    const culprits = [];
    for (const el of document.querySelectorAll('main *, header *')) {
      const r = el.getBoundingClientRect();
      if (r.right > d.clientWidth + 1 && !clipped(el) && r.width > 0) {
        const sec = (el.closest('section') || {}).id || 'no-section';
        culprits.push(`${sec} > ${el.tagName}.${el.className || '?'}`);
      }
    }
    return { scrollWidth: d.scrollWidth, clientWidth: d.clientWidth, culprits };
  });
  const overflowPx = m.scrollWidth - m.clientWidth;
  sweep.push({ width, overflowPx, ok: overflowPx <= TOLERANCE });
  const uniqueCulprits = [...new Set(m.culprits)].slice(0, 6);
  console.log(
    `[Sweep ${width}px] scrollWidth=${m.scrollWidth} clientWidth=${m.clientWidth} overflowPx=${overflowPx}` +
      (uniqueCulprits.length ? ` culprits=${JSON.stringify(uniqueCulprits)}` : ' culprits=none')
  );
  await p.close();
}

// 7. Page errors
console.log(`[Page errors] ${errors.length === 0 ? 'none' : errors.join(' | ')}`);

await browser.close();

const quickrefOk = quickrefFiles.length === 3;
const footerOk = footerLinks.length === 5 && linkStatus.length === 5 && linkStatus.every((l) => l.status === 200);
const progressOk = progCount === 1 && progPosition === 'fixed' && progMoves;
const sweepOk = sweep.every((s) => s.ok);
const ok =
  resp?.status() === 200 &&
  headingCount === 1 &&
  gridCount === 1 &&
  cardCount === 5 &&
  !hasOldAnimal &&
  !hasOldDog &&
  !gridMetrics.overflow &&
  quickrefOk &&
  footerOk &&
  progressOk &&
  dtOk &&
  sweepOk &&
  errors.length === 0;
console.log(`[QuickRef] ${quickrefOk ? 'PASS (3 patterns)' : `FAIL (${quickrefFiles.length} patterns)`}`);
console.log(`[Footer] ${footerOk ? 'PASS (all links 200)' : 'FAIL'}`);
console.log(`[Progress] ${progressOk ? 'PASS' : 'FAIL'}`);
console.log(`[DecisionTable] ${dtOk ? 'PASS' : 'FAIL'}`);
console.log(`[Sweep] ${sweepOk ? 'PASS at all viewports' : 'FAIL — overflow at ' + sweep.filter((s) => !s.ok).map((s) => s.width + 'px').join(', ')}`);
console.log(`\nRESULT: ${ok ? 'PASS' : 'FAIL'}`);
process.exit(ok ? 0 : 1);
