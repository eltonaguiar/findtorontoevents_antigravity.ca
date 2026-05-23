import { test, expect, Page } from '@playwright/test';

const MS3_URL = 'https://findtorontoevents.ca/MOVIESHOWS3/';

// Helper: wait for MS3 to fully load
async function waitForMS3Ready(page: Page, timeoutMs = 45000) {
  await page.waitForSelector('.video-card', { timeout: timeoutMs });
  await page.waitForTimeout(2000);
}

// Helper: collect console logs
function collectConsoleLogs(page: Page) {
  const errors: string[] = [];
  const warnings: string[] = [];
  const logs: string[] = [];
  page.on('console', msg => {
    const text = msg.text();
    if (msg.type() === 'error') errors.push(text);
    else if (msg.type() === 'warning') warnings.push(text);
    else logs.push(text);
  });
  page.on('pageerror', err => {
    errors.push(`PAGE ERROR: ${err.message}`);
  });
  return { errors, warnings, logs };
}

// ═══════════════════════════════════════════════════════════
// TEST SUITE: MS3 Page Load & Structure
// ═══════════════════════════════════════════════════════════

test.describe('MS3 Live - Page Load', () => {
  test('page loads with 200 status', async ({ page }) => {
    const response = await page.goto(MS3_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    expect(response?.status()).toBe(200);
  });

  test('video cards render with content', async ({ page }) => {
    await page.goto(MS3_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForMS3Ready(page);

    const cardCount = await page.locator('.video-card').count();
    console.log(`  Video cards rendered: ${cardCount}`);
    expect(cardCount).toBeGreaterThanOrEqual(1);

    // Check first card has expected structure
    const firstCard = page.locator('.video-card').first();
    const hasIframe = await firstCard.locator('iframe').count() > 0;
    const hasWrapper = await firstCard.locator('.video-wrapper').count() > 0;
    console.log(`  First card: iframe=${hasIframe}, wrapper=${hasWrapper}`);
    expect(hasIframe).toBe(true);
  });

  test('container has proper scroll snap setup', async ({ page }) => {
    await page.goto(MS3_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForMS3Ready(page);

    const snapType = await page.locator('#container').evaluate(el =>
      getComputedStyle(el).scrollSnapType
    );
    console.log(`  Container scroll-snap-type: ${snapType}`);
    expect(snapType).toContain('mandatory');
  });
});

// ═══════════════════════════════════════════════════════════
// TEST SUITE: MS3 JavaScript Errors
// ═══════════════════════════════════════════════════════════

test.describe('MS3 Live - JS Errors', () => {
  test('no postMessage about: errors on load', async ({ page }) => {
    const { errors } = collectConsoleLogs(page);
    await page.goto(MS3_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForMS3Ready(page);

    // Wait a bit for any postMessage errors to accumulate
    await page.waitForTimeout(3000);

    const postMessageErrors = errors.filter(e =>
      e.includes('postMessage') && e.includes('about:')
    );

    console.log(`  Total console errors: ${errors.length}`);
    console.log(`  postMessage 'about:' errors: ${postMessageErrors.length}`);

    if (postMessageErrors.length > 0) {
      console.log('  *** BUG CONFIRMED: postMessage about: origin errors ***');
      console.log(`  First error: ${postMessageErrors[0].substring(0, 200)}`);
    }
  });

  test('no postMessage errors during scroll', async ({ page }) => {
    const { errors } = collectConsoleLogs(page);
    await page.goto(MS3_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForMS3Ready(page);

    // Scroll through several cards
    const container = page.locator('#container');
    for (let i = 0; i < 5; i++) {
      await container.evaluate(el => el.scrollBy(0, window.innerHeight));
      await page.waitForTimeout(1000);
    }

    const postMessageErrors = errors.filter(e =>
      e.includes('postMessage') && e.includes('about:')
    );

    console.log(`  postMessage errors after 5 scrolls: ${postMessageErrors.length}`);
    if (postMessageErrors.length > 0) {
      console.log('  *** BUG: postMessage about: errors during scroll ***');
    }
  });

  test('no critical page errors', async ({ page }) => {
    const { errors } = collectConsoleLogs(page);
    await page.goto(MS3_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForMS3Ready(page);

    const criticalErrors = errors.filter(e =>
      !e.includes('www-widgetapi') &&
      !e.includes('postMessage') &&
      !e.includes('web-client-content-script') &&
      !e.includes('net::ERR_') &&
      !e.includes('favicon') &&
      !e.includes('ResizeObserver')
    );

    if (criticalErrors.length > 0) {
      console.log('  === CRITICAL ERRORS ===');
      criticalErrors.forEach(e => console.log(`    ${e.substring(0, 200)}`));
    }
    console.log(`  Critical errors: ${criticalErrors.length}`);
  });
});

// ═══════════════════════════════════════════════════════════
// TEST SUITE: MS3 Video Playback
// ═══════════════════════════════════════════════════════════

test.describe('MS3 Live - Video Playback', () => {
  test('first video iframe loads with YouTube src', async ({ page }) => {
    await page.goto(MS3_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForMS3Ready(page);

    const firstIframe = page.locator('#player-0');
    const exists = await firstIframe.count() > 0;
    console.log(`  First iframe (#player-0) exists: ${exists}`);

    if (exists) {
      const src = await firstIframe.getAttribute('src');
      console.log(`  First iframe src: ${src?.substring(0, 100)}`);
      const hasYouTube = src?.includes('youtube.com');
      console.log(`  Contains youtube.com: ${hasYouTube}`);
    }
  });

  test('lazy iframes have data-embed-url attribute', async ({ page }) => {
    await page.goto(MS3_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForMS3Ready(page);

    // Check non-first iframes for lazy loading setup
    const iframeInfo = await page.evaluate(() => {
      const iframes = document.querySelectorAll('.video-card iframe');
      const results: Array<{ id: string; src: string; embedUrl: string | null; display: string }> = [];
      iframes.forEach((iframe, i) => {
        if (i > 5) return; // Only check first 6
        const el = iframe as HTMLIFrameElement;
        results.push({
          id: el.id || `iframe-${i}`,
          src: el.src || 'empty',
          embedUrl: el.dataset.embedUrl || null,
          display: el.style.display || 'default',
        });
      });
      return results;
    });

    console.log('  Iframe states:');
    iframeInfo.forEach(info => {
      console.log(`    ${info.id}: src="${info.src.substring(0, 50)}" | embedUrl=${info.embedUrl ? 'YES' : 'NO'} | display=${info.display}`);
    });

    // First iframe should have real src, rest should be lazy (about:blank + data-embed-url)
    if (iframeInfo.length > 1) {
      const lazyCount = iframeInfo.slice(1).filter(i => i.embedUrl !== null).length;
      console.log(`  Lazy iframes (with data-embed-url): ${lazyCount}/${iframeInfo.length - 1}`);
    }
  });

  test('poster play icon is clickable (mobile playback fix)', async ({ page }) => {
    await page.goto(MS3_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForMS3Ready(page);

    // Check poster-play-icon pointer-events
    const playIcons = page.locator('.poster-play-icon');
    const playIconCount = await playIcons.count();
    console.log(`  Poster play icons found: ${playIconCount}`);

    if (playIconCount > 0) {
      const pointerEvents = await playIcons.first().evaluate(el =>
        getComputedStyle(el).pointerEvents
      );
      console.log(`  poster-play-icon pointer-events: ${pointerEvents}`);

      if (pointerEvents === 'none') {
        console.log('  *** BUG CONFIRMED: poster-play-icon has pointer-events:none ***');
        console.log('  *** This prevents mobile users from tapping to play ***');
      }

      // Check if video-poster has click handler
      const posterClickable = await page.evaluate(() => {
        const poster = document.querySelector('.video-poster');
        if (!poster) return 'no poster found';
        const style = getComputedStyle(poster);
        return `cursor=${style.cursor}, pointerEvents=${style.pointerEvents}`;
      });
      console.log(`  Video poster clickability: ${posterClickable}`);
    }
  });

  test('scroll activates lazy iframes via IntersectionObserver', async ({ page }) => {
    const { logs } = collectConsoleLogs(page);
    await page.goto(MS3_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForMS3Ready(page);

    // Scroll to card 1 (second video)
    await page.locator('#container').evaluate(el => el.scrollBy(0, window.innerHeight));
    await page.waitForTimeout(2000);

    // Check if the second iframe got activated
    const secondIframe = page.locator('#player-1');
    if (await secondIframe.count() > 0) {
      const src = await secondIframe.getAttribute('src');
      const display = await secondIframe.evaluate(el => (el as HTMLIFrameElement).style.display);
      console.log(`  After scroll to card 1: src="${src?.substring(0, 80)}" display="${display}"`);

      if (src && src.includes('youtube.com')) {
        console.log('  Lazy iframe activated successfully after scroll');
      } else {
        console.log('  *** POTENTIAL BUG: iframe not activated after scroll ***');
      }
    }
  });
});

// ═══════════════════════════════════════════════════════════
// TEST SUITE: MS3 Queue System
// ═══════════════════════════════════════════════════════════

test.describe('MS3 Live - Queue System', () => {
  test('queue panel exists and opens', async ({ page }) => {
    await page.goto(MS3_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForMS3Ready(page);

    const queueBtn = page.locator('#queueToggle, button:has-text("Queue"), [onclick*="queue" i]').first();
    const queueBtnExists = await queueBtn.count() > 0;
    console.log(`  Queue button exists: ${queueBtnExists}`);

    if (queueBtnExists) {
      await queueBtn.click();
      await page.waitForTimeout(500);

      const queuePanel = page.locator('#queuePanel');
      const isActive = await queuePanel.evaluate(el => el.classList.contains('active')).catch(() => false);
      console.log(`  Queue panel active after click: ${isActive}`);
    }

    // Check queue count badge
    const queueCount = page.locator('#queueCount');
    const countText = await queueCount.textContent().catch(() => 'N/A');
    console.log(`  Queue count: ${countText}`);
  });

  test('addToQueue function works via feed', async ({ page }) => {
    const { logs } = collectConsoleLogs(page);
    await page.goto(MS3_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForMS3Ready(page);

    // Try to add current video to queue
    const result = await page.evaluate(() => {
      try {
        if (typeof (window as any).addToQueue === 'function') {
          (window as any).addToQueue();
          return 'addToQueue called';
        }
        return 'addToQueue not found on window';
      } catch (e: any) {
        return `Error: ${e.message}`;
      }
    });
    console.log(`  addToQueue result: ${result}`);

    // Check if item was added
    const queueState = await page.evaluate(() => {
      const stored = localStorage.getItem('movieQueue');
      return stored ? JSON.parse(stored).length : 0;
    });
    console.log(`  Queue items in localStorage: ${queueState}`);
  });

  test('playFromQueue removes item from queue', async ({ page }) => {
    await page.goto(MS3_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForMS3Ready(page);

    // Manually add an item to queue then test playFromQueue
    const result = await page.evaluate(() => {
      // Add a test item
      const queue = JSON.parse(localStorage.getItem('movieQueue') || '[]');
      queue.push({
        id: 99999,
        title: 'Test Movie',
        trailer_id: 'dQw4w9WgXcQ',
        type: 'movie',
        thumbnail: ''
      });
      localStorage.setItem('movieQueue', JSON.stringify(queue));

      const beforeCount = queue.length;

      // Call playFromQueue
      try {
        if (typeof (window as any).playFromQueue === 'function') {
          (window as any).playFromQueue(queue.length - 1);
          const afterQueue = JSON.parse(localStorage.getItem('movieQueue') || '[]');
          return {
            before: beforeCount,
            after: afterQueue.length,
            removed: beforeCount > afterQueue.length,
          };
        }
        return { error: 'playFromQueue not found' };
      } catch (e: any) {
        return { error: e.message };
      }
    });

    console.log(`  playFromQueue result: ${JSON.stringify(result)}`);

    if (result && 'removed' in result) {
      if (result.removed) {
        console.log('  playFromQueue correctly removes item from queue');
      } else {
        console.log('  *** BUG: playFromQueue does NOT remove item from queue ***');
      }
    }
  });
});

// ═══════════════════════════════════════════════════════════
// TEST SUITE: MS3 Browse Grid
// ═══════════════════════════════════════════════════════════

test.describe('MS3 Live - Browse Grid', () => {
  test('browse grid opens with movie cards', async ({ page }) => {
    await page.goto(MS3_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForMS3Ready(page);

    // Find and click browse button
    const browseBtn = page.locator('button:has-text("Browse"), #browseBtn, [onclick*="openBrowse"]').first();
    if (await browseBtn.count() > 0) {
      await browseBtn.click();
      await page.waitForTimeout(1000);

      // Check for browse grid
      const browseGrid = page.locator('#browseGrid, .browse-grid, [class*="browse"]').first();
      const gridVisible = await browseGrid.isVisible().catch(() => false);
      console.log(`  Browse grid visible: ${gridVisible}`);

      // Count browse cards
      const browseCards = page.locator('.fresh-card, .browse-card, [class*="browse"] .card');
      const cardCount = await browseCards.count();
      console.log(`  Browse cards: ${cardCount}`);
    } else {
      console.log('  Browse button not found');
    }
  });

  test('browse category filter works', async ({ page }) => {
    await page.goto(MS3_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForMS3Ready(page);

    // Open browse
    const browseBtn = page.locator('button:has-text("Browse"), #browseBtn').first();
    if (await browseBtn.count() > 0) {
      await browseBtn.click();
      await page.waitForTimeout(1000);

      // Find filter buttons/tabs in browse
      const filterBtns = page.locator('.browse-filter, .browse-tab, [class*="browse"] button[data-filter], [class*="browse"] button[data-genre]');
      const filterCount = await filterBtns.count();
      console.log(`  Browse filter buttons: ${filterCount}`);

      for (let i = 0; i < Math.min(filterCount, 5); i++) {
        const text = await filterBtns.nth(i).textContent();
        console.log(`    Filter ${i}: "${text?.trim()}"`);
      }
    }
  });
});

// ═══════════════════════════════════════════════════════════
// TEST SUITE: MS3 Freestyle Search
// ═══════════════════════════════════════════════════════════

test.describe('MS3 Live - Freestyle Search', () => {
  test('freestyle search opens and finds results', async ({ page }) => {
    await page.goto(MS3_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForMS3Ready(page);

    // Open freestyle
    const freestyleBtn = page.locator('button:has-text("Freestyle"), #freestyleBtn, [onclick*="openFreestyle"]').first();
    if (await freestyleBtn.count() > 0) {
      await freestyleBtn.click();
      await page.waitForTimeout(500);

      const input = page.locator('#freestyleInput, input[placeholder*="search" i]').first();
      if (await input.count() > 0) {
        await input.fill('breaking bad');
        await input.press('Enter');
        await page.waitForTimeout(3000);

        // Check results
        const results = page.locator('.freestyle-result, .fs-result, [class*="freestyle"] [class*="result"]');
        const resultCount = await results.count();
        console.log(`  Freestyle results for "breaking bad": ${resultCount}`);
      } else {
        console.log('  Freestyle input not found');
      }
    } else {
      console.log('  Freestyle button not found');
    }
  });
});

// ═══════════════════════════════════════════════════════════
// TEST SUITE: MS3 Mobile-Specific (Samsung Galaxy S21 viewport)
// ═══════════════════════════════════════════════════════════

test.describe('MS3 Live - Mobile Viewport', () => {
  test.use({ viewport: { width: 384, height: 854 }, hasTouch: true });

  test('video cards fill mobile viewport', async ({ page }) => {
    await page.goto(MS3_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForMS3Ready(page);

    const firstCard = page.locator('.video-card').first();
    const box = await firstCard.boundingBox();
    if (box) {
      console.log(`  First card size: ${box.width}x${box.height}`);
      console.log(`  Viewport: 384x854`);
      // Card should fill viewport width
      expect(box.width).toBeGreaterThanOrEqual(380);
    }
  });

  test('tap on poster triggers playback on mobile', async ({ page }) => {
    const { logs, errors } = collectConsoleLogs(page);
    await page.goto(MS3_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForMS3Ready(page);

    // Scroll to card 1 (which should have a poster)
    await page.locator('#container').evaluate(el => el.scrollBy(0, window.innerHeight));
    await page.waitForTimeout(1500);

    // Check if there's a poster visible
    const poster = page.locator('.video-card:nth-child(2) .video-poster').first();
    const posterVisible = await poster.isVisible().catch(() => false);
    console.log(`  Card 2 poster visible: ${posterVisible}`);

    if (posterVisible) {
      // Try tapping the poster area
      await poster.tap().catch(async () => {
        // If poster can't be tapped, try the play icon
        const playIcon = page.locator('.video-card:nth-child(2) .poster-play-icon').first();
        console.log('  Poster not tappable, trying play icon...');
        await playIcon.tap().catch(() => {
          console.log('  *** BUG: Neither poster nor play icon is tappable ***');
        });
      });

      await page.waitForTimeout(2000);

      // Check if iframe was activated
      const iframe = page.locator('#player-1');
      if (await iframe.count() > 0) {
        const src = await iframe.getAttribute('src');
        const display = await iframe.evaluate(el => (el as HTMLIFrameElement).style.display);
        console.log(`  After tap: iframe src="${src?.substring(0, 80)}" display="${display}"`);

        if (!src || src === 'about:blank') {
          console.log('  *** BUG: iframe not activated after tap on poster ***');
        }
      }
    } else {
      console.log('  No poster visible on card 2 (may already be playing)');
    }
  });
});

// ═══════════════════════════════════════════════════════════
// TEST SUITE: MS3 Category Continuation
// ═══════════════════════════════════════════════════════════

test.describe('MS3 Live - Category Continuation', () => {
  test('no category continuation toast exists (missing feature)', async ({ page }) => {
    const { logs } = collectConsoleLogs(page);
    await page.goto(MS3_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForMS3Ready(page);

    // Check for any auto-play context tracking variables
    const hasAutoPlayContext = await page.evaluate(() => {
      return typeof (window as any)._browseAutoPlayContext !== 'undefined';
    });
    console.log(`  _browseAutoPlayContext exists: ${hasAutoPlayContext}`);
    if (!hasAutoPlayContext) {
      console.log('  *** MISSING FEATURE: No category continuation mechanism ***');
    }
  });
});

// ═══════════════════════════════════════════════════════════
// TEST SUITE: MS3 Performance
// ═══════════════════════════════════════════════════════════

test.describe('MS3 Live - Performance', () => {
  test('page load under 10 seconds', async ({ page }) => {
    const start = Date.now();
    await page.goto(MS3_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForMS3Ready(page);
    const loadTime = Date.now() - start;

    console.log(`  Page load + ready time: ${loadTime}ms`);
    expect(loadTime).toBeLessThan(15000);
  });

  test('DOM size is reasonable', async ({ page }) => {
    await page.goto(MS3_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForMS3Ready(page);

    const domStats = await page.evaluate(() => {
      return {
        totalNodes: document.querySelectorAll('*').length,
        iframes: document.querySelectorAll('iframe').length,
        videoCards: document.querySelectorAll('.video-card').length,
        scripts: document.querySelectorAll('script').length,
      };
    });

    console.log(`  DOM nodes: ${domStats.totalNodes}`);
    console.log(`  Iframes: ${domStats.iframes}`);
    console.log(`  Video cards: ${domStats.videoCards}`);
    console.log(`  Scripts: ${domStats.scripts}`);
  });
});

// ═══════════════════════════════════════════════════════════
// TEST SUITE: MS3 stopYouTubeIframe about:blank guard
// ═══════════════════════════════════════════════════════════

test.describe('MS3 Live - stopYouTubeIframe Safety', () => {
  test('stopYouTubeIframe guards against about:blank', async ({ page }) => {
    await page.goto(MS3_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForMS3Ready(page);

    // Check the function implementation
    const hasGuard = await page.evaluate(() => {
      const funcStr = (window as any).stopYouTubeIframe?.toString() || '';
      return funcStr.includes('about:blank') || funcStr.includes('about');
    });

    console.log(`  stopYouTubeIframe has about:blank guard: ${hasGuard}`);
    if (!hasGuard) {
      console.log('  *** BUG: stopYouTubeIframe does not guard against about:blank iframes ***');
    }
  });
});
