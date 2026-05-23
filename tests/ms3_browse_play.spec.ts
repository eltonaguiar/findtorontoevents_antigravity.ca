import { test, expect, Page } from '@playwright/test';

const MS3_URL = 'https://findtorontoevents.ca/MOVIESHOWS3/';

// Helper: wait for MS3 to fully load
async function waitForMS3Ready(page: Page, timeoutMs = 45000) {
  await page.waitForSelector('.video-card', { timeout: timeoutMs });
  await page.waitForTimeout(2000); // let JS initialize
}

// Helper: collect console logs for diagnostics
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
test.describe('MS3 Browse & Play', () => {

  // TEST 1: First video should play on load
  test('first video (card 0) plays on load — iframe visible, not about:blank', async ({ page }) => {
    collectConsoleLogs(page);
    await page.goto(MS3_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForMS3Ready(page);
    await page.waitForTimeout(2000);

    const iframe0 = page.locator('#player-0');
    await expect(iframe0).toBeAttached({ timeout: 10000 });

    const iframeSrc = await iframe0.getAttribute('src');
    console.log('[Test] Card 0 iframe src:', iframeSrc);
    expect(iframeSrc).toBeTruthy();
    expect(iframeSrc).not.toBe('about:blank');
    expect(iframeSrc).toContain('youtube.com/embed/');

    const iframeDisplay = await iframe0.evaluate(el => getComputedStyle(el).display);
    console.log('[Test] Card 0 iframe display:', iframeDisplay);
    expect(iframeDisplay).not.toBe('none');

    const currentlyPlaying = await page.evaluate(() => (window as any)._currentlyPlaying);
    console.log('[Test] _currentlyPlaying:', currentlyPlaying);
    expect(currentlyPlaying).toBe('0');
  });

  // TEST 2: Browse → search "Mercy" → play → video visible
  test('browse → search Mercy → play → iframe visible with YouTube src', async ({ page }) => {
    const consoleLogs = collectConsoleLogs(page);
    await page.goto(MS3_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForMS3Ready(page);

    // Open browse panel
    await page.locator('button[title="Browse All"]').click();
    await page.waitForTimeout(500);
    await expect(page.locator('#browseView')).toHaveClass(/active/);

    // Search for "Mercy"
    await page.locator('#browseSearchInput').fill('Mercy');
    await page.waitForTimeout(500);

    // Find clickable Mercy card
    const mercyCards = page.locator('#browseView .movie-card');
    const mercyCount = await mercyCards.count();
    console.log('[Test] Mercy search results count:', mercyCount);
    expect(mercyCount).toBeGreaterThan(0);

    let clickedIndex = -1;
    for (let i = 0; i < mercyCount; i++) {
      const card = mercyCards.nth(i);
      const onclickDiv = card.locator('[onclick*="playMovieFromBrowse"]');
      const divCount = await onclickDiv.count();
      if (divCount > 0) {
        const onclick = await onclickDiv.first().getAttribute('onclick');
        const match = onclick?.match(/playMovieFromBrowse\((\d+)\)/);
        if (match) {
          clickedIndex = parseInt(match[1]);
          console.log('[Test] Clicking Mercy at filteredMovies index:', clickedIndex);
          // Scroll into view and click via JS to handle browse panel scroll
          await page.evaluate((idx) => {
            const el = document.querySelector(`#browseView [onclick*="playMovieFromBrowse(${idx})"]`);
            if (el) {
              el.scrollIntoView({ block: 'center' });
              (el as HTMLElement).click();
            }
          }, clickedIndex);
          break;
        }
      }
    }
    expect(clickedIndex).toBeGreaterThanOrEqual(0);

    // Wait for browse close + iframe load
    await page.waitForTimeout(3000);

    // Browse should be closed
    const browseActive = await page.evaluate(() =>
      document.getElementById('browseView')?.classList.contains('active')
    );
    expect(browseActive).toBe(false);

    // Card should be visible
    const targetCard = page.locator(`.video-card[data-index="${clickedIndex}"]`);
    await expect(targetCard).toBeAttached({ timeout: 5000 });

    // iframe should have YouTube src and be visible
    const iframe = page.locator(`#player-${clickedIndex}`);
    await expect(iframe).toBeAttached({ timeout: 5000 });

    const iframeSrc = await iframe.getAttribute('src');
    console.log(`[Test] Card ${clickedIndex} iframe src:`, iframeSrc);
    expect(iframeSrc).toBeTruthy();
    expect(iframeSrc).not.toBe('about:blank');
    expect(iframeSrc).toContain('youtube.com/embed/');

    const iframeDisplay = await iframe.evaluate(el => getComputedStyle(el).display);
    console.log(`[Test] Card ${clickedIndex} iframe display:`, iframeDisplay);
    expect(iframeDisplay).not.toBe('none');

    const iframeBox = await iframe.boundingBox();
    console.log(`[Test] Card ${clickedIndex} iframe box:`, JSON.stringify(iframeBox));
    expect(iframeBox).not.toBeNull();
    expect(iframeBox!.width).toBeGreaterThan(100);
    expect(iframeBox!.height).toBeGreaterThan(50);

    // Poster should be hidden
    const posterDisplay = await page.evaluate((idx) => {
      const card = document.querySelector(`.video-card[data-index="${idx}"]`);
      const poster = card?.querySelector('.video-poster') as HTMLElement | null;
      return poster ? getComputedStyle(poster).display : 'NO_POSTER_FOUND';
    }, clickedIndex);
    console.log(`[Test] Card ${clickedIndex} poster display:`, posterDisplay);
    // Card 0 has no poster, others should have it hidden
    if (posterDisplay !== 'NO_POSTER_FOUND') {
      expect(posterDisplay).toBe('none');
    }

    // _currentlyPlaying should match
    const cp = await page.evaluate(() => (window as any)._currentlyPlaying);
    console.log('[Test] _currentlyPlaying:', cp);
    expect(cp).toBe(String(clickedIndex));

    if (consoleLogs.errors.length > 0) {
      console.log('[Test] Console errors:', consoleLogs.errors.slice(0, 5).join('\n'));
    }
  });

  // TEST 3: Browse play → scroll → next card also plays
  test('browse play → scroll to next → next video plays', async ({ page }) => {
    const consoleLogs = collectConsoleLogs(page);
    await page.goto(MS3_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForMS3Ready(page);

    // Open browse and find a playable card with index >= 2 (guaranteed lazy card, not first)
    await page.locator('button[title="Browse All"]').click();
    await page.waitForTimeout(500);

    // Use JS to find and click a card at index >= 2
    const playedIndex = await page.evaluate(() => {
      const cards = document.querySelectorAll('#browseView [onclick*="playMovieFromBrowse"]');
      for (const card of cards) {
        const onclick = card.getAttribute('onclick') || '';
        const match = onclick.match(/playMovieFromBrowse\((\d+)\)/);
        if (match && parseInt(match[1]) >= 2) {
          card.scrollIntoView({ block: 'center' });
          (card as HTMLElement).click();
          return parseInt(match[1]);
        }
      }
      return -1;
    });
    console.log('[Test] Browse-played index:', playedIndex);
    expect(playedIndex).toBeGreaterThanOrEqual(2);

    // Wait for playback to start
    await page.waitForTimeout(3000);

    // Verify iframe is playing
    const iframeSrc = await page.evaluate((idx) => {
      const iframe = document.getElementById('player-' + idx) as HTMLIFrameElement;
      return iframe?.src || 'NOT_FOUND';
    }, playedIndex);
    console.log(`[Test] Card ${playedIndex} iframe src:`, iframeSrc);
    expect(iframeSrc).toContain('youtube.com/embed/');

    const iframeVisible = await page.evaluate((idx) => {
      const iframe = document.getElementById('player-' + idx) as HTMLIFrameElement;
      return iframe ? getComputedStyle(iframe).display : 'NOT_FOUND';
    }, playedIndex);
    expect(iframeVisible).not.toBe('none');

    // Scroll to next card
    const nextIndex = playedIndex + 1;
    console.log('[Test] Scrolling to next card:', nextIndex);
    await page.evaluate((idx) => {
      const container = document.getElementById('container');
      container?.scrollTo({ top: idx * window.innerHeight, behavior: 'instant' });
    }, nextIndex);

    // Wait for observer suppression (2s) + debounce (150ms) + iframe load
    await page.waitForTimeout(4000);

    // Next card should have a playing iframe
    const nextState = await page.evaluate((idx) => {
      const iframe = document.getElementById('player-' + idx) as HTMLIFrameElement;
      if (!iframe) return { src: 'NOT_FOUND', display: 'NOT_FOUND', cp: null };
      return {
        src: iframe.src,
        display: getComputedStyle(iframe).display,
        cp: (window as any)._currentlyPlaying,
      };
    }, nextIndex);
    console.log(`[Test] Card ${nextIndex} state:`, JSON.stringify(nextState));
    expect(nextState.src).toContain('youtube.com/embed/');
    expect(nextState.display).not.toBe('none');
    expect(nextState.cp).toBe(String(nextIndex));
  });

  // TEST 4: DIAGNOSTIC — full state dump at multiple time points
  test('DIAGNOSTIC: card state after browse play at 200/500/1000/2000/3000ms', async ({ page }) => {
    collectConsoleLogs(page);
    await page.goto(MS3_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForMS3Ready(page);

    // Open browse and search Mercy
    await page.locator('button[title="Browse All"]').click();
    await page.waitForTimeout(500);
    await page.locator('#browseSearchInput').fill('Mercy');
    await page.waitForTimeout(500);

    // Find and click a playable Mercy card via JS
    const targetIdx = await page.evaluate(() => {
      const cards = document.querySelectorAll('#browseView [onclick*="playMovieFromBrowse"]');
      for (const card of cards) {
        const onclick = card.getAttribute('onclick') || '';
        const match = onclick.match(/playMovieFromBrowse\((\d+)\)/);
        if (match) {
          card.scrollIntoView({ block: 'center' });
          (card as HTMLElement).click();
          return parseInt(match[1]);
        }
      }
      return -1;
    });
    console.log('[Diagnostic] Target index:', targetIdx);
    expect(targetIdx).toBeGreaterThanOrEqual(0);

    // State dumps at multiple time points
    const checkpoints = [200, 500, 1000, 2000, 3000];
    let lastTime = 0;
    for (const ms of checkpoints) {
      await page.waitForTimeout(ms - lastTime);
      lastTime = ms;

      const state = await page.evaluate((idx) => {
        const card = document.querySelector(`.video-card[data-index="${idx}"]`);
        if (!card) return { error: 'CARD_NOT_FOUND' };
        const iframe = card.querySelector('iframe') as HTMLIFrameElement | null;
        const poster = card.querySelector('.video-poster') as HTMLElement | null;
        const playIcon = card.querySelector('.poster-play-icon') as HTMLElement | null;
        return {
          iframeSrc: iframe?.src?.substring(0, 80) || 'NO_IFRAME',
          iframeDisplay: iframe ? getComputedStyle(iframe).display : 'NO_IFRAME',
          iframeInlineStyle: iframe?.style.display ?? 'NO_IFRAME',
          hasDataEmbedUrl: !!(iframe?.dataset.embedUrl),
          posterInlineDisplay: poster?.style.display ?? 'NO_POSTER',
          playIconInlineDisplay: playIcon?.style.display ?? 'NO_ICON',
          currentlyPlaying: (window as any)._currentlyPlaying,
          browseScrolling: (window as any)._browseScrolling,
          msSinceBrowsePlay: (window as any)._lastBrowsePlayTime ? Date.now() - (window as any)._lastBrowsePlayTime : 'N/A',
          queueLength: (window as any).myQueue?.length ?? 0,
        };
      }, targetIdx);

      console.log(`[Diagnostic T+${ms}ms]`, JSON.stringify(state));
    }

    // Final check
    const final = await page.evaluate((idx) => {
      const card = document.querySelector(`.video-card[data-index="${idx}"]`);
      const iframe = card?.querySelector('iframe') as HTMLIFrameElement | null;
      return {
        src: iframe?.src || 'NO_IFRAME',
        display: iframe ? getComputedStyle(iframe).display : 'none',
      };
    }, targetIdx);

    expect(final.src).toContain('youtube.com/embed/');
    expect(final.display).not.toBe('none');
  });

  // TEST 5: Freestyle → play → queue continuation
  test('freestyle search → play → remaining items queued at front', async ({ page }) => {
    collectConsoleLogs(page);
    await page.goto(MS3_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForMS3Ready(page);

    // Open freestyle overlay
    const freestyleBtn = page.locator('button[title="Freestyle"]');
    const hasFreeBtn = await freestyleBtn.count();
    if (hasFreeBtn === 0) {
      console.log('[Test] No freestyle button found, skipping');
      return;
    }
    await freestyleBtn.click();
    await page.waitForTimeout(500);

    // Search for something popular
    await page.locator('#freestyleInput').fill('marvel');
    await page.locator('#freestyleSearchBtn, .freestyle-search-btn').first().click();
    await page.waitForTimeout(5000); // wait for API results

    // Check if results loaded
    const resultCount = await page.evaluate(() => (window as any).freestyleResults?.length || 0);
    console.log('[Test] Freestyle results count:', resultCount);
    if (resultCount === 0) {
      console.log('[Test] No freestyle results, skipping continuation test');
      return;
    }

    // Get queue before playing
    const queueBefore = await page.evaluate(() => (window as any).myQueue?.length || 0);
    console.log('[Test] Queue before freestyle play:', queueBefore);

    // Click first result's play button
    const playBtn = page.locator('.freestyle-card .play-trailer-btn, .freestyle-results [onclick*="playFreestyleTrailer"]').first();
    const playBtnCount = await playBtn.count();
    if (playBtnCount > 0) {
      await page.evaluate(() => {
        // Use JS to call the function directly for reliability
        if ((window as any).playFreestyleTrailer) {
          (window as any).playFreestyleTrailer(0);
        }
      });
      await page.waitForTimeout(2000);

      // Queue should have grown by (resultCount - 1)
      const queueAfter = await page.evaluate(() => (window as any).myQueue?.length || 0);
      console.log('[Test] Queue after freestyle play:', queueAfter);
      expect(queueAfter).toBeGreaterThan(queueBefore);

      // First items in queue should be freestyle results (not old browse items)
      const firstQueueItem = await page.evaluate(() => {
        const q = (window as any).myQueue;
        return q && q[0] ? { title: q[0].title, trailer_id: q[0].trailer_id } : null;
      });
      console.log('[Test] First queue item:', JSON.stringify(firstQueueItem));
      expect(firstQueueItem).not.toBeNull();
      expect(firstQueueItem!.trailer_id).toBeTruthy();
    } else {
      console.log('[Test] No play button found in freestyle results');
    }
  });
});
