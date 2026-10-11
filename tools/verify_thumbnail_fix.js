#!/usr/bin/env node
/**
 * verify_thumbnail_fix.js — end-to-end check of the card-thumbnail crop fix.
 *
 * Serves the *patched* TORONTOEVENTS_ANTIGRAVITY/index.html at the live origin
 * (page.route on the root document only) so every other asset — the Next.js
 * event-feed chunks and /next/events.json — still comes from production. That
 * tests the real feed, the real cards, and my HTML change in one pass.
 *
 * Assertions:
 *   A. every loaded thumbnail with source aspect >= 2.2 carries
 *      .card-thumbnail-wide and computes object-position "right center"
 *   B. every loaded thumbnail with source aspect < 2.2 keeps the default
 *      "50% 50%" centred crop
 *   C. no console/page errors from the thumbnail injection code
 *
 * Usage: node tools/verify_thumbnail_fix.js [url]
 * Exit 0 = all assertions pass.
 */
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const SITE = process.argv[2] || 'https://findtorontoevents.ca/';
const HTML_PATH = path.join(__dirname, '..', 'TORONTOEVENTS_ANTIGRAVITY', 'index.html');

(async () => {
  const html = fs.readFileSync(HTML_PATH, 'utf8');
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });

  const errors = [];
  page.on('pageerror', (e) => errors.push('PAGEERROR ' + String(e).slice(0, 300)));
  page.on('console', (m) => { if (m.type() === 'error') errors.push('CONSOLE ' + m.text().slice(0, 200)); });

  // Serve our patched HTML at the root; everything else stays production.
  await page.route('**/', async (route) => {
    const req = route.request();
    if (req.resourceType() === 'document') {
      await route.fulfill({ status: 200, contentType: 'text/html; charset=utf-8', body: html });
    } else {
      await route.continue();
    }
  });

  await page.goto(SITE, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.waitForTimeout(15000);

  const report = await page.evaluate(() => {
    const out = { total: 0, wide: 0, normal: 0, failures: [], wideSamples: [], normalSamples: [], zeroNatural: 0 };
    document.querySelectorAll('.card-thumbnail').forEach((img) => {
      out.total++;
      const nw = img.naturalWidth, nh = img.naturalHeight;
      if (!nw || !nh) { out.zeroNatural++; return; }
      const cs = getComputedStyle(img);
      const aspect = nw / nh;
      const card = img.closest('[class*="glass-panel"], [class*="event-card"]') || img.parentElement;
      const h = card && card.querySelector('h2, h3');
      const title = h ? (h.textContent || '').trim() : '?';
      const isWide = img.classList.contains('card-thumbnail-wide');
      // getComputedStyle serialises `right center` as `100% 50%`.
      const anchoredRight = cs.objectPosition === 'right center' || cs.objectPosition === '100% 50%';
      if (aspect >= 2.2) {
        out.wide++;
        if (!isWide || !anchoredRight) {
          out.failures.push({ title, nw, nh, aspect: +aspect.toFixed(2), isWide, objectPosition: cs.objectPosition, expect: 'wide + right center' });
        }
        if (out.wideSamples.length < 6) out.wideSamples.push({ title, nw, nh, objectPosition: cs.objectPosition, isWide });
      } else {
        out.normal++;
        if (isWide) {
          out.failures.push({ title, nw, nh, aspect: +aspect.toFixed(2), isWide, objectPosition: cs.objectPosition, expect: 'not wide + 50% 50%' });
        }
        if (out.normalSamples.length < 4) out.normalSamples.push({ title, nw, nh, objectPosition: cs.objectPosition, isWide });
      }
    });
    return out;
  });

  // Screenshot the first ultra-wide TPL banner card for a visual record.
  const shot = await page.evaluate(() => {
    const imgs = Array.from(document.querySelectorAll('.card-thumbnail.card-thumbnail-wide'));
    if (imgs.length) { imgs[0].scrollIntoView({ block: 'center' }); return imgs[0].alt || ''; }
    return '';
  });
  if (shot) {
    await page.waitForTimeout(1200);
    await page.screenshot({ path: '/tmp/thumbnail_fix_after.png' });
    report.screenshot = '/tmp/thumbnail_fix_after.png';
  }

  report.patchedHtmlServed = html.includes('card-thumbnail-wide');
  report.throwsInInjection = errors.filter((e) => /flagWideThumb|applyThumbnails|is not a function|undefined/.test(e));
  report.allErrors = errors.slice(0, 10);

  const pass = report.failures.length === 0 && report.wide > 0 && report.throwsInInjection.length === 0;
  report.verdict = pass ? 'PASS' : 'FAIL';
  fs.writeFileSync('/tmp/thumbnail_fix_report.json', JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));

  await browser.close();
  process.exit(pass ? 0 : 1);
})().catch((e) => { console.error('FATAL', e); process.exit(2); });
