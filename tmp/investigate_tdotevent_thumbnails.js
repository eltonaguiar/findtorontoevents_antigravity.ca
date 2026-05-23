/**
 * Investigate missing event thumbnails on tdotevent.ca
 */
const { chromium } = require('playwright');

(async () => {
  console.log('🔍 Investigating tdotevent.ca event thumbnails...\n');

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({
    viewport: { width: 1920, height: 1080 }
  });

  const consoleMessages = [];
  const jsErrors = [];
  const networkFailures = [];

  page.on('console', msg => consoleMessages.push({ type: msg.type(), text: msg.text() }));
  page.on('pageerror', err => jsErrors.push(err.message));
  page.on('response', res => {
    if (!res.ok() && res.status() !== 304) {
      const url = res.url();
      if (url.match(/\.(jpg|jpeg|png|gif|webp)(\?|$)/i) || url.includes('image') || url.includes('thumbnail')) {
        networkFailures.push({ url, status: res.status() });
      }
    }
  });

  try {
    console.log('1. Navigating to https://tdotevent.ca/index.html...');
    await page.goto('https://tdotevent.ca/index.html', {
      waitUntil: 'networkidle',
      timeout: 25000
    });

    console.log('2. Waiting 8s for events to load...');
    await page.waitForTimeout(8000);

    // Try to wait for event cards to appear
    const hasEventCards = await page.evaluate(() => {
      const cards = document.querySelectorAll('[class*="card"], article, [class*="event"]');
      return cards.length > 0;
    });
    if (!hasEventCards) {
      console.log('   ⚠️ No event cards found initially, continuing anyway...');
    }

    console.log('3. Analyzing event cards and images...\n');
    const analysis = await page.evaluate(() => {
      const selectors = [
        '[class*="event-card"]',
        '[class*="card"]',
        'article',
        '[class*="EventCard"]',
        '[class*="event"]'
      ];
      const seen = new Set();
      const cards = [];
      for (const sel of selectors) {
        document.querySelectorAll(sel).forEach(el => {
          if (seen.has(el)) return;
          // Skip promo/nav cards - look for event-like content
          const text = (el.innerText || '').substring(0, 200);
          if (text.length > 20 && !text.includes('Open App') && !text.includes('Learn More')) {
            seen.add(el);
            const imgs = el.querySelectorAll('img');
            const imgData = [];
            imgs.forEach(img => {
              imgData.push({
                src: img.src || img.getAttribute('src') || '',
                alt: img.alt || '',
                naturalWidth: img.naturalWidth,
                naturalHeight: img.naturalHeight,
                complete: img.complete
              });
            });
            cards.push({
              text: text.substring(0, 80),
              hasImg: imgs.length > 0,
              imgCount: imgs.length,
              images: imgData,
              placeholder: !!el.querySelector('[class*="placeholder"], [class*="card-thumb-placeholder"]')
            });
          }
        });
      }
      return { totalCards: cards.length, cards };
    });

    console.log('═══════════════════════════════════════════════════════════');
    console.log('REPORT: tdotevent.ca Event Thumbnails');
    console.log('═══════════════════════════════════════════════════════════\n');

    console.log(`📊 Total event-like cards found: ${analysis.totalCards}\n`);

    let withWorkingThumb = 0;
    let withBrokenThumb = 0;
    let withNoThumb = 0;
    const brokenUrls = new Set();
    const workingUrls = [];

    analysis.cards.forEach((c, i) => {
      if (c.hasImg) {
        const broken = c.images.some(img =>
          img.naturalWidth === 0 || img.naturalHeight === 0 || !img.complete
        );
        if (broken) {
          withBrokenThumb++;
          c.images.forEach(img => {
            if (img.src) brokenUrls.add(img.src);
          });
        } else {
          withWorkingThumb++;
          c.images.forEach(img => { if (img.src) workingUrls.push(img.src); });
        }
      } else {
        withNoThumb++;
      }
    });

    console.log(`   ✅ Cards with working thumbnails: ${withWorkingThumb}`);
    console.log(`   ❌ Cards with broken/missing thumbnails: ${withBrokenThumb}`);
    console.log(`   ⚪ Cards with no image (placeholder only): ${withNoThumb}\n`);

    if (brokenUrls.size > 0) {
      console.log('🔗 Broken image URLs (first 15):');
      [...brokenUrls].slice(0, 15).forEach((u, i) => console.log(`   ${i + 1}. ${u}`));
      if (brokenUrls.size > 15) console.log(`   ... and ${brokenUrls.size - 15} more`);
      console.log('');
    }

    if (workingUrls.length > 0) {
      console.log('✅ Sample working image URLs (first 5):');
      workingUrls.slice(0, 5).forEach((u, i) => console.log(`   ${i + 1}. ${u}`));
      console.log('');
    }

    const imageErrors = consoleMessages.filter(m =>
      m.text.toLowerCase().includes('404') ||
      m.text.toLowerCase().includes('failed to load') ||
      m.text.toLowerCase().includes('img') ||
      m.text.toLowerCase().includes('image')
    );

    const criticalErrors = jsErrors.concat(
      networkFailures.map(n => `[NET] ${n.status} ${n.url}`)
    );

    console.log('📋 Image-related console messages:');
    if (imageErrors.length === 0) console.log('   (none)');
    else imageErrors.slice(0, 10).forEach(m => console.log(`   [${m.type}] ${m.text.substring(0, 120)}`));

    console.log('\n❌ Page/network errors (image-related):');
    if (criticalErrors.length === 0) console.log('   (none)');
    else criticalErrors.slice(0, 15).forEach(e => console.log(`   ${e.substring(0, 150)}`));

    // Sample HTML of first few cards
    console.log('\n📄 Sample event card structure (first 3 with images):');
    const sampleCards = analysis.cards.filter(c => c.hasImg).slice(0, 3);
    sampleCards.forEach((c, i) => {
      console.log(`   Card ${i + 1}: "${c.text}..."`);
      c.images.forEach((img, j) => {
        const status = (img.naturalWidth && img.naturalHeight) ? 'OK' : 'BROKEN';
        console.log(`      img[${j}]: ${status} natural=${img.naturalWidth}x${img.naturalHeight} src=${(img.src || '').substring(0, 80)}`);
      });
    });

    // Scroll and re-check
    console.log('\n4. Scrolling down and re-checking...');
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight / 2));
    await page.waitForTimeout(2000);
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await page.waitForTimeout(3000);

    const afterScroll = await page.evaluate(() => {
      const imgs = document.querySelectorAll('img');
      let working = 0, broken = 0;
      const brokenSrcs = [];
      imgs.forEach(img => {
        if (img.src && !img.src.includes('logo') && !img.src.includes('icon')) {
          if (img.naturalWidth > 0 && img.naturalHeight > 0) working++;
          else { broken++; brokenSrcs.push(img.src); }
        }
      });
      return { totalImgs: imgs.length, working, broken, brokenSrcs: brokenSrcs.slice(0, 10) };
    });

    console.log(`   After scroll: ${afterScroll.working} working images, ${afterScroll.broken} broken`);
    if (afterScroll.brokenSrcs.length > 0) {
      console.log('   Additional broken srcs after scroll:', afterScroll.brokenSrcs);
    }

    // Save report
    const report = {
      url: 'https://tdotevent.ca/index.html',
      timestamp: new Date().toISOString(),
      summary: {
        totalCards: analysis.totalCards,
        withWorkingThumb,
        withBrokenThumb,
        withNoThumb
      },
      brokenUrls: [...brokenUrls],
      imageRelatedConsole: imageErrors,
      networkFailures,
      jsErrors
    };
    require('fs').writeFileSync(
      'tmp/tdotevent_thumbnail_report.json',
      JSON.stringify(report, null, 2)
    );
    console.log('\n✅ Report saved to tmp/tdotevent_thumbnail_report.json');

  } catch (err) {
    console.error('Error:', err.message);
  } finally {
    await browser.close();
  }
})();
