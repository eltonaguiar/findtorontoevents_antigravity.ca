#!/usr/bin/env node
/**
 * debug_card_images.js — diagnose why event-card thumbnails render as
 * "cut off / random colour" blocks on findtorontoevents.ca.
 *
 * For every injected .card-thumbnail (and any <img> inside the card that
 * matches an event) we collect:
 *   - src (after proxy), HTTP status, natural vs rendered size
 *   - computed object-fit / object-position
 *   - the exact source rectangle the browser paints into the box
 *   - whether the painted region is a flat colour (pixel-variance probe)
 *
 * Usage: node tools/debug_card_images.js [url] [matchTitle]
 */
const { chromium } = require('playwright');
const fs = require('fs');

const URL_ = process.argv[2] || 'https://findtorontoevents.ca/';
const MATCH = process.argv[3] || 'EarlyON';

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });

  const responses = {};
  page.on('response', (r) => {
    const u = r.url();
    if (/\.(jpg|jpeg|png|webp|gif)(\?|$)/i.test(u) || u.includes('/image-proxy') || u.includes('/uploads/images/')) {
      responses[u] = { status: r.status(), type: r.headers()['content-type'] || '' };
    }
  });
  const errors = [];
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text().slice(0, 200)); });
  page.on('requestfailed', (r) => { if (/\.(jpg|jpeg|png|webp)/i.test(r.url())) errors.push('REQFAIL ' + r.url() + ' :: ' + (r.failure() || {}).errorText); });

  await page.goto(URL_, { waitUntil: 'domcontentloaded', timeout: 90000 });
  // give the React feed + applyThumbnails() time to run
  await page.waitForTimeout(12000);

  const report = await page.evaluate(async (matchTitle) => {
    const out = {
      thumbnailsOn: document.body.classList.contains('thumbnails-on'),
      thumbCount: document.querySelectorAll('.card-thumbnail').length,
      gridCount: document.querySelectorAll('#events-grid img').length,
      samples: [],
    };

    const cards = Array.from(document.querySelectorAll('.card-thumbnail'));
    for (const thumb of cards.slice(0, 400)) {
      const card = thumb.closest('[class*="glass-panel"], [class*="event-card"]') || thumb.parentElement;
      const titleEl = card ? card.querySelector('h2, h3, [class*="title"]') : null;
      const title = titleEl ? (titleEl.textContent || '').trim() : '';
      const titleHit = matchTitle ? title.toLowerCase().includes(matchTitle.toLowerCase()) : true;

      const cs = getComputedStyle(thumb);
      const rect = thumb.getBoundingClientRect();
      const nw = thumb.naturalWidth, nh = thumb.naturalHeight;
      const bw = rect.width, bh = rect.height;
      const scale = Math.max(bw / (nw || 1), bh / (nh || 1)); // object-fit: cover
      const coverW = nw * scale, coverH = nh * scale;
      const crop = {
        srcW: Math.round(nw), srcH: Math.round(nh),
        paintedW: Math.round(coverW), paintedH: Math.round(coverH),
        visiblePctW: +(bw / coverW * 100).toFixed(1),
        visiblePctH: +(bh / coverH * 100).toFixed(1),
        aspectSrc: +(nw / (nh || 1)).toFixed(2),
        aspectBox: +(bw / (bh || 1)).toFixed(2),
      };
      out.samples.push({ title, hit: titleHit, classes: thumb.className, src: thumb.src, complete: thumb.complete, nw, nh, boxW: Math.round(bw), boxH: Math.round(bh), objectFit: cs.objectFit, objectPosition: cs.objectPosition, crop });
    }
    out.samples = out.samples.slice(0, 80);

    // pixel-variance probe on the first matching thumbnail (may taint canvas)
    const t = cards.find((el) => {
      const c = el.closest('[class*="glass-panel"], [class*="event-card"]') || el.parentElement;
      const h = c && c.querySelector('h2, h3');
      return h && (h.textContent || '').toLowerCase().includes(matchTitle.toLowerCase());
    }) || cards[0];
    if (t) {
      try {
        const probe = document.createElement('canvas');
        probe.width = 64; probe.height = 64;
        const ctx = probe.getContext('2d');
        // reproduce object-fit: cover, centered
        const nw = t.naturalWidth, nh = t.naturalHeight;
        const bw = t.getBoundingClientRect().width, bh = t.getBoundingClientRect().height;
        const s = Math.max(bw / nw, bh / nh);
        const dw = nw * s, dh = nh * s;
        ctx.drawImage(t, (bw - dw) / 2, (bh - dh) / 2, dw, dh);
        const d = ctx.getImageData(0, 0, 64, 64).data;
        let min = [255, 255, 255], max = [0, 0, 0], sum = 0;
        for (let i = 0; i < d.length; i += 4) {
          for (let k = 0; k < 3; k++) {
            min[k] = Math.min(min[k], d[i + k]); max[k] = Math.max(max[k], d[i + k]);
            sum += d[i + k];
          }
        }
        out.pixelProbe = { range: max.map((v, i) => v - min[i]), avg: Math.round(sum / (d.length / 4 * 3)), tainted: false };
      } catch (e) {
        out.pixelProbe = { error: String(e).slice(0, 120), tainted: true };
      }
    }
    return out;
  }, MATCH);

  // screenshot the matching card
  const card = page.locator('.card-thumbnail').first();
  try {
    const titleCard = await page.evaluate((m) => {
      const els = Array.from(document.querySelectorAll('.card-thumbnail'));
      const t = els.find((el) => {
        const c = el.closest('[class*="glass-panel"], [class*="event-card"]') || el.parentElement;
        const h = c && c.querySelector('h2, h3');
        return h && (h.textContent || '').toLowerCase().includes(m.toLowerCase());
      });
      if (t) { t.scrollIntoView({ block: 'center' }); return true; }
      return false;
    }, MATCH);      if (titleCard) {
      await page.waitForTimeout(1500);
      await page.screenshot({ path: '/tmp/card_image_diag.png' });
      report.screenshot = '/tmp/card_image_diag.png';
    }
    if (!titleCard) {
      await page.waitForTimeout(800);
      await page.screenshot({ path: '/tmp/card_image_diag_first.png' });
      report.screenshot = '/tmp/card_image_diag_first.png';
    }
  } catch (e) { report.shotErr = String(e).slice(0, 120); }

  report.imageResponses = Object.entries(responses).slice(0, 30);
  report.consoleErrors = errors.slice(0, 20);
  fs.writeFileSync('/tmp/card_image_diag.json', JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
  await browser.close();
})().catch((e) => { console.error('FATAL', e); process.exit(1); });
