#!/usr/bin/env node
/**
 * Node validation: confirm index.html has promo banner fix (4 items, alignment CSS).
 * Run: node tools/validate_promo_banners_node.js
 */
const fs = require('fs');
const path = require('path');

const indexPath = path.join(__dirname, '..', 'index.html');
const html = fs.readFileSync(indexPath, 'utf8');

let ok = true;

// 1. Grid CSS for promo section (structural selector + data-promo-grid for restored)
if (!html.includes('data-promo-grid') || !html.includes(':has(.promo-banner)')) {
  console.error('FAIL: missing promo grid CSS (data-promo-grid or :has(.promo-banner))');
  ok = false;
}
if (!html.includes('align-items: center') || !html.includes('grid-template-columns')) {
  console.error('FAIL: missing alignment/grid CSS for promo section');
  ok = false;
}

// 2. Normalization CSS (height 48px, flex, inline-flex for a/button)
const requiredCss = [
  'height: 48px',
  'align-items: center',
  'display: inline-flex',
  '.promo-banner',
  'main .promo-banner',
];
for (const s of requiredCss) {
  if (!html.includes(s)) {
    console.error('FAIL: missing expected CSS:', s);
    ok = false;
  }
}

// 3. Static HTML: exactly 2 promo blocks (match React to avoid #418); Fav Creators + Stocks in restore script
if (!html.includes('windows-fixer-promo') || !html.includes('movieshows-promo')) {
  console.error('FAIL: static HTML must include windows-fixer-promo and movieshows-promo');
  ok = false;
}
if (!html.includes('favcreators-promo') || !html.includes('stocks-promo')) {
  console.error('FAIL: restore script must include favcreators-promo and stocks-promo (in FAVCREATORS_HTML/STOCKS_HTML)');
  ok = false;
}

// 4. Restore script: FAVCREATORS_HTML and STOCKS_HTML
if (!html.includes('FAVCREATORS_HTML') || !html.includes('STOCKS_HTML')) {
  console.error('FAIL: missing restore script (FAVCREATORS_HTML / STOCKS_HTML)');
  ok = false;
}
if (!html.includes('ensureIconLinksFour')) {
  console.error('FAIL: missing ensureIconLinksFour');
  ok = false;
}

// 5. Promo section must have 4 static promo blocks (Windows Fixer, Movies & TV, Fav Creators, Stocks)
const sectionStart = html.indexOf('max-w-7xl mx-auto px-4 w-full grid');
const sectionEnd = html.indexOf('<div class="max-w-7xl mx-auto px-4 py-6">', sectionStart);
const section = sectionStart >= 0 && sectionEnd > sectionStart ? html.slice(sectionStart, sectionEnd) : '';
const inSectionCount = (section.match(/promo-banner/g) || []).length;
if (inSectionCount < 4) {
  console.error('FAIL: icon-links-section should have at least 4 .promo-banner in static HTML, got', inSectionCount);
  ok = false;
}

if (ok) {
  console.log('OK: promo banner fix validated (4 static promo blocks, CSS, restore script fallback)');
} else {
  process.exit(1);
}
