#!/usr/bin/env node
/**
 * Standalone Playwright verification for the ServiceNow JavaScript reference page.
 * Loads the local file:// URL and measures overflow in the ES6 examples section.
 *
 * Usage: node tools/verify_servicenow_es6_overflow.mjs
 */
import { chromium } from 'playwright';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const HTML_PATH = join(__dirname, '..', 'findtorontoevents.ca', 'servicenow', 'javascript', 'index.html');
const fileUrl = `file://${HTML_PATH}`;

// Widths below 1024 drop the 300px TOC sidebar (single-column layout) and are
// where .anti/.good comparison cards historically blew out the grid track.
const VIEWPORTS = [390, 768, 1024, 1280, 1440];
const TOLERANCE = 2; // px — sub-pixel rounding on the .page max-width

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });

const errors = [];
page.on('pageerror', (e) => errors.push(e.message));

await page.goto(fileUrl, { waitUntil: 'domcontentloaded' });

// 1. Confirm the NEW heading is present (proves not the stale Animal/Dog version)
const headingCount = await page.locator('h3:has-text("Production-Grade ServiceNow Examples")').count();
console.log(`[Heading] "Production-Grade ServiceNow Examples" count = ${headingCount}`);

// 2. Confirm the single-column ES6 grid exists and has 5 cards
const es6Grid = page.locator('.api-grid.es6-examples');
const gridCount = await es6Grid.count();
const cardCount = await es6Grid.locator('.api-card').count();
console.log(`[ES6 Grid] count = ${gridCount}, cards = ${cardCount}`);

// 3. Confirm old Animal/Dog code is NOT in the ES6 section
const es6Text = await es6Grid.innerText();
const hasOldAnimal = es6Text.includes('var Animal = Class.create()');
const hasOldDog = es6Text.includes('Dog.prototype = Object.extendsObject');
console.log(`[Old code] Animal present = ${hasOldAnimal}, Dog present = ${hasOldDog}`);

// 4. Measure grid overflow
const gridMetrics = await es6Grid.evaluate((el) => ({
  scrollWidth: el.scrollWidth,
  clientWidth: el.clientWidth,
  overflow: el.scrollWidth > el.clientWidth + 2,
}));
console.log(`[ES6 Grid] scrollWidth=${gridMetrics.scrollWidth}, clientWidth=${gridMetrics.clientWidth}, overflow=${gridMetrics.overflow}`);

// 5. Measure each card's pre block. NOTE: scrollWidth > clientWidth on a pre is
//    CORRECT behavior (code scrolls inside the block), so this is informational
//    only and does not gate the result. The page-level sweep in step 6 does.
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

// 5b. Footer menu must present all ServiceNow guides
const footerLinkCount = await page.locator('.footer-nav a').count();
const footerTexts = await page.locator('.footer-nav a').allInnerTexts();
console.log(`[Footer] links = ${footerLinkCount} ${JSON.stringify(footerTexts)}`);

// 5c. Scroll progress bar: present, position:fixed (out of flow — cannot affect
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

// 6. Page-level horizontal overflow sweep across viewports.
//    The invariant is on the DOCUMENT (does the page scroll sideways), not on
//    individual pre blocks.
const sweep = [];
for (const width of VIEWPORTS) {
  const p = await browser.newPage({ viewport: { width, height: 900 } });
  await p.goto(fileUrl, { waitUntil: 'domcontentloaded' });
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
    `[Sweep ${width}px] scrollWidth=${m.scrollWidth} clientWidth=${m.clientWidth} overflowPx=${overflowPx} culprits=${JSON.stringify(uniqueCulprits)}`
  );
  await p.close();
}

// 6b. Decision table must expose UI Policy as a first-class artifact column.
//     7 columns (Scenario + 6 artifacts), UI Policy marked on the 3 form-behavior rows.
const dtHead = await page.locator('#decision-table thead th').allInnerTexts();
const dtRowCount = await page.locator('#decision-table tbody tr').count();
const dtPolicyMarks = await page.locator('#decision-table tbody tr').evaluateAll((rows) =>
  rows.filter((r) => (r.children[1].textContent || '').trim().length > 0).length
);
console.log(`[DecisionTable] head=${JSON.stringify(dtHead.map((h) => h.trim()))} rows=${dtRowCount} uiPolicyMarks=${dtPolicyMarks}`);
const dtOk = dtHead.length === 7 && dtHead[1].trim() === 'UI Policy' && dtRowCount === 8 && dtPolicyMarks === 3;

// 7. Page errors
console.log(`[Page errors] ${errors.length === 0 ? 'none' : errors.join(' | ')}`);

await browser.close();

// Exit non-zero if the critical assertions fail
const sweepOk = sweep.every((s) => s.ok);
const progressOk = progCount === 1 && progPosition === 'fixed' && progMoves;
const ok = headingCount === 1 && gridCount === 1 && cardCount === 5 && !hasOldAnimal && !hasOldDog && !gridMetrics.overflow && footerLinkCount === 5 && progressOk && dtOk && sweepOk && errors.length === 0;
console.log(`[Progress] ${progressOk ? 'PASS' : 'FAIL'}`);
console.log(`[DecisionTable] ${dtOk ? 'PASS' : 'FAIL'}`);
console.log(`\n[Sweep] ${sweepOk ? 'PASS at all viewports' : 'FAIL — overflow at ' + sweep.filter((s) => !s.ok).map((s) => s.width + 'px').join(', ')}`);
console.log(`RESULT: ${ok ? 'PASS' : 'FAIL'}`);
process.exit(ok ? 0 : 1);
