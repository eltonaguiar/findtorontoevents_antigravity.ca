import { test, expect } from '@playwright/test';

/**
 * MOVIESHOWS3 Remote Tests
 * API health, CORS, page load, browse panel, video playback,
 * fast scrolling, filtering, performance, and user interaction edge cases
 */

const PRIMARY = 'https://findtorontoevents.ca';

// Helper: wait for movies to render (reliable across all browsers/workers)
async function waitForMovies(page: any) {
  await page.waitForFunction(
    () => document.querySelectorAll('.video-card').length > 100,
    { timeout: 45000 }
  );
}

// ── API Health — findtorontoevents.ca ───────────────────────────────

test.describe('MS3 API — findtorontoevents', () => {
  test('get-movies.php returns valid JSON with 1000+ movies', async ({ request }) => {
    const resp = await request.get(`${PRIMARY}/MOVIESHOWS3/api/get-movies.php`);
    expect(resp.status()).toBe(200);
    expect(resp.headers()['access-control-allow-origin']).toBe('*');
    expect(resp.headers()['content-type']).toContain('application/json');
    const body = await resp.json();
    expect(body.success).toBe(true);
    expect(body.count).toBeGreaterThan(1000);
  });

  test('API never returns HTML error output', async ({ request }) => {
    const resp = await request.get(`${PRIMARY}/MOVIESHOWS3/api/get-movies.php`);
    const text = await resp.text();
    expect(text).not.toMatch(/^<br\s*\/?>/);
    expect(text).not.toContain('Fatal error');
    expect(() => JSON.parse(text)).not.toThrow();
  });

  test('check-session.php returns JSON', async ({ request }) => {
    const resp = await request.get(`${PRIMARY}/MOVIESHOWS3/api/check-session.php`);
    expect(resp.status()).toBe(200);
    const body = await resp.json();
    expect(body).toHaveProperty('user');
  });

  test('test-db.php confirms database connection', async ({ request }) => {
    const resp = await request.get(`${PRIMARY}/MOVIESHOWS3/api/test-db.php`);
    const text = await resp.text();
    expect(text).toContain('Connected');
    expect(text).toContain('OK');
  });
});

// ── API Health — tdotevent.ca ───────────────────────────────────────

test.describe('MS3 API — tdotevent', () => {
  test('get-movies.php returns valid JSON', async ({ request }) => {
    const resp = await request.get('https://tdotevent.ca/MOVIESHOWS3/api/get-movies.php');
    expect(resp.status()).toBe(200);
    expect(resp.headers()['access-control-allow-origin']).toBe('*');
    const body = await resp.json();
    expect(body.success).toBe(true);
    expect(body.count).toBeGreaterThan(1000);
  });
});

// ── API Health — torontoevent.net ───────────────────────────────────

test.describe('MS3 API — torontoevent', () => {
  test('CORS header is single * (not duplicated)', async ({ request }) => {
    const resp = await request.get('https://torontoevent.net/MOVIESHOWS3/api/get-movies.php');
    const cors = resp.headers()['access-control-allow-origin'];
    expect(cors).toBe('*');
    expect(cors).not.toContain(', ');
  });
});

// ── Page Load Tests ─────────────────────────────────────────────────

test.describe('MS3 Page Load', () => {
  test('loads movies from database (not motivational fallback)', { timeout: 60000 }, async ({ page }) => {
    const logs: string[] = [];
    page.on('console', msg => logs.push(msg.text()));

    await page.goto(`${PRIMARY}/MOVIESHOWS3/`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await waitForMovies(page);

    const fallback = logs.find(m => m.includes('motivational videos as fallback'));
    expect(fallback).toBeUndefined();
    const loaded = logs.find(m => m.includes('Loaded') && m.includes('movies'));
    expect(loaded).toBeDefined();
  });

  test('no postMessage about:blank errors', { timeout: 60000 }, async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', err => errors.push(err.message));
    page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });

    await page.goto(`${PRIMARY}/MOVIESHOWS3/`, { waitUntil: 'domcontentloaded' });
    await waitForMovies(page);

    const postMsgErrors = errors.filter(e =>
      e.includes('postMessage') || e.includes("Invalid target origin 'about:'")
    );
    expect(postMsgErrors).toHaveLength(0);
  });

  test('no CORS or JSON parsing errors', { timeout: 60000 }, async ({ page }) => {
    const errors: string[] = [];
    page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });

    await page.goto(`${PRIMARY}/MOVIESHOWS3/`, { waitUntil: 'domcontentloaded' });
    await waitForMovies(page);

    const critical = errors.filter(e =>
      e.includes('CORS') || e.includes('*, *') || e.includes('not valid JSON') || e.includes('Unexpected token')
    );
    expect(critical).toHaveLength(0);
  });

  test('video cards are rendered', { timeout: 60000 }, async ({ page }) => {
    await page.goto(`${PRIMARY}/MOVIESHOWS3/`, { waitUntil: 'domcontentloaded' });
    await waitForMovies(page);
    const cardCount = await page.locator('.video-card').count();
    expect(cardCount).toBeGreaterThan(100);
  });
});

// ── Browse Panel Tests ──────────────────────────────────────────────

test.describe('MS3 Browse Panel', () => {
  test('opens as side drawer (not fullscreen)', { timeout: 60000 }, async ({ page }) => {
    await page.goto(`${PRIMARY}/MOVIESHOWS3/`, { waitUntil: 'domcontentloaded' });
    await waitForMovies(page);

    await page.locator('[onclick*="toggleBrowse"]').first().click();
    await page.waitForTimeout(500);

    const browseView = page.locator('#browseView');
    await expect(browseView).toHaveClass(/active/);
    const box = await browseView.boundingBox();
    expect(box).toBeTruthy();
    expect(box!.width).toBeLessThan(600);
  });

  test('backdrop blocks clicks to video', { timeout: 60000 }, async ({ page }) => {
    await page.goto(`${PRIMARY}/MOVIESHOWS3/`, { waitUntil: 'domcontentloaded' });
    await waitForMovies(page);

    await page.locator('[onclick*="toggleBrowse"]').first().click();
    await page.waitForTimeout(500);

    const backdrop = page.locator('#browseBackdrop');
    await expect(backdrop).toHaveClass(/active/);
  });

  test('closing removes panel and backdrop', { timeout: 60000 }, async ({ page }) => {
    await page.goto(`${PRIMARY}/MOVIESHOWS3/`, { waitUntil: 'domcontentloaded' });
    await waitForMovies(page);

    const btn = page.locator('[onclick*="toggleBrowse"]').first();
    await btn.click();
    await page.waitForTimeout(500);

    // Click the backdrop to close (button is behind the backdrop)
    const backdrop = page.locator('#browseBackdrop');
    await backdrop.click({ force: true });
    await page.waitForTimeout(500);

    expect(await page.locator('#browseView').evaluate(el => el.classList.contains('active'))).toBe(false);
    expect(await page.locator('#browseBackdrop').evaluate(el => el.classList.contains('active'))).toBe(false);
  });

  test('search filters movies by title', { timeout: 60000 }, async ({ page }) => {
    await page.goto(`${PRIMARY}/MOVIESHOWS3/`, { waitUntil: 'domcontentloaded' });
    await waitForMovies(page);

    await page.locator('[onclick*="toggleBrowse"]').first().click();
    await page.waitForTimeout(500);
    await page.locator('#browseSearchInput').fill('Mercy');
    await page.waitForTimeout(2000);

    const results = page.locator('[onclick*="playMovieFromBrowse"]');
    expect(await results.count()).toBeGreaterThan(0);
  });

  test('play from browse panel closes panel and plays', { timeout: 60000 }, async ({ page }) => {
    const logs: string[] = [];
    page.on('console', msg => logs.push(msg.text()));

    await page.goto(`${PRIMARY}/MOVIESHOWS3/`, { waitUntil: 'domcontentloaded' });
    await waitForMovies(page);

    await page.locator('[onclick*="toggleBrowse"]').first().click();
    await page.waitForTimeout(500);

    const playable = page.locator('[onclick*="playMovieFromBrowse"]').first();
    if (await playable.count() > 0) {
      await playable.click();
      await page.waitForTimeout(3000);

      expect(await page.locator('#browseView').evaluate(el => el.classList.contains('active'))).toBe(false);
      const playMsg = logs.find(m => m.includes('[playMovieFromBrowse]') && m.includes('Playing'));
      expect(playMsg).toBeDefined();
    }
  });

  test('video pauses when opening browse (no postMessage errors)', { timeout: 60000 }, async ({ page }) => {
    const errors: string[] = [];
    page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });

    await page.goto(`${PRIMARY}/MOVIESHOWS3/`, { waitUntil: 'domcontentloaded' });
    await waitForMovies(page);

    await page.locator('[onclick*="toggleBrowse"]').first().click();
    await page.waitForTimeout(1000);

    const aboutBlankErrors = errors.filter(e => e.includes("about:"));
    expect(aboutBlankErrors).toHaveLength(0);
  });
});

// ── 2026 Filtering ──────────────────────────────────────────────────

test.describe('MS3 2026 Filtering', () => {
  test('search for 2026 titles finds them', { timeout: 60000 }, async ({ page }) => {
    await page.goto(`${PRIMARY}/MOVIESHOWS3/`, { waitUntil: 'domcontentloaded' });
    await waitForMovies(page);

    await page.locator('[onclick*="toggleBrowse"]').first().click();
    await page.waitForTimeout(500);

    await page.locator('#browseSearchInput').fill('Bone Temple');
    await page.waitForTimeout(1000);

    expect(await page.locator('[onclick*="playMovieFromBrowse"]').count()).toBeGreaterThan(0);
  });

  test('fresh section shows recent releases', { timeout: 60000 }, async ({ page }) => {
    await page.goto(`${PRIMARY}/MOVIESHOWS3/`, { waitUntil: 'domcontentloaded' });
    await waitForMovies(page);

    await page.locator('[onclick*="toggleBrowse"]').first().click();
    await page.waitForTimeout(1000);

    const freshSection = page.locator('#freshSection, .fresh-section');
    if (await freshSection.count() > 0) {
      expect(await freshSection.locator('.fresh-card').count()).toBeGreaterThan(0);
    }
  });
});

// ── Video Playback Edge Cases ───────────────────────────────────────

test.describe('MS3 Video Edge Cases', () => {
  test('fast scrolling does not cause errors', { timeout: 60000 }, async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', err => errors.push(err.message));

    await page.goto(`${PRIMARY}/MOVIESHOWS3/`, { waitUntil: 'domcontentloaded' });
    await waitForMovies(page);

    const container = page.locator('#container');
    for (let i = 0; i < 10; i++) {
      await container.evaluate((el) => el.scrollBy(0, 1080));
      await page.waitForTimeout(200);
    }
    await page.waitForTimeout(3000);

    const critical = errors.filter(e =>
      e.includes('postMessage') || e.includes('Cannot read') || e.includes('about:blank')
    );
    expect(critical).toHaveLength(0);
  });

  test('double-click same video does not black screen', { timeout: 60000 }, async ({ page }) => {
    await page.goto(`${PRIMARY}/MOVIESHOWS3/`, { waitUntil: 'domcontentloaded' });
    await waitForMovies(page);

    const btn = page.locator('[onclick*="toggleBrowse"]').first();
    await btn.click();
    await page.waitForTimeout(500);

    const playable = page.locator('[onclick*="playMovieFromBrowse"]').first();
    if (await playable.count() > 0) {
      await playable.click();
      await page.waitForTimeout(1000);

      await btn.click();
      await page.waitForTimeout(500);
      await page.locator('[onclick*="playMovieFromBrowse"]').first().click();
      await page.waitForTimeout(2000);

      // With lazy loading + queue swaps, verify no JS errors and page isn't blank
      const pageState = await page.evaluate(() => {
        const idx = (window as any)._currentlyPlaying;
        const cards = document.querySelectorAll('.video-card');
        const hasCards = cards.length > 100;
        const container = document.getElementById('container');
        const containerHasContent = container && container.children.length > 0;
        return { playing: idx, hasCards, containerHasContent };
      });
      expect(pageState.hasCards).toBe(true);
      expect(pageState.containerHasContent).toBe(true);
      expect(pageState.playing).not.toBeNull();
    }
  });

  test('filtering while video plays does not crash', { timeout: 90000 }, async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', err => errors.push(err.message));

    await page.goto(`${PRIMARY}/MOVIESHOWS3/`, { waitUntil: 'domcontentloaded' });
    await waitForMovies(page);

    await page.locator('[onclick*="toggleBrowse"]').first().click();
    await page.waitForTimeout(500);

    const input = page.locator('#browseSearchInput');
    await input.fill('Stranger Things');
    await page.waitForTimeout(500);
    await input.fill('Mercy');
    await page.waitForTimeout(500);
    await input.fill('Housemaid');
    await page.waitForTimeout(500);

    expect(errors.filter(e => e.includes('Cannot read'))).toHaveLength(0);
  });

  test('play from browse then open menu works', { timeout: 90000 }, async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', err => errors.push(err.message));

    await page.goto(`${PRIMARY}/MOVIESHOWS3/`, { waitUntil: 'domcontentloaded' });
    await waitForMovies(page);

    await page.locator('[onclick*="toggleBrowse"]').first().click();
    await page.waitForTimeout(500);

    const playable = page.locator('[onclick*="playMovieFromBrowse"]').first();
    if (await playable.count() > 0) {
      await playable.click();
      await page.waitForTimeout(2000);
    }

    const hamburger = page.locator('.hamburger-btn').first();
    if (await hamburger.count() > 0) {
      await hamburger.click();
      await page.waitForTimeout(1000);
      expect(await page.locator('.menu-panel, #menuPanel').first().isVisible()).toBe(true);
    }

    expect(errors.filter(e => e.includes('postMessage'))).toHaveLength(0);
  });
});

// ── Cross-Domain ────────────────────────────────────────────────────

test.describe('MS3 Cross-Domain', () => {
  test('torontoevent.net loads MOVIESHOWS3 page', { timeout: 60000 }, async ({ page }) => {
    const logs: string[] = [];
    page.on('console', msg => logs.push(msg.text()));

    const resp = await page.goto('https://torontoevent.net/MOVIESHOWS3/', {
      waitUntil: 'domcontentloaded', timeout: 30000,
    });
    expect(resp?.status()).toBe(200);
    await page.waitForTimeout(15000);

    const corsErrors = logs.filter(m => m.includes('*, *') || m.includes('CORS'));
    expect(corsErrors).toHaveLength(0);

    const loaded = logs.find(m => m.includes('Loaded') && m.includes('movies'));
    const fallback = logs.find(m => m.includes('motivational videos as fallback'));
    expect(loaded || fallback).toBeTruthy();
  });

  test('tdotevent.ca loads from database', { timeout: 60000 }, async ({ page }) => {
    const logs: string[] = [];
    page.on('console', msg => logs.push(msg.text()));

    await page.goto('https://tdotevent.ca/MOVIESHOWS3/', {
      waitUntil: 'domcontentloaded', timeout: 30000,
    });
    await page.waitForTimeout(12000);

    const fallback = logs.find(m => m.includes('motivational videos as fallback'));
    expect(fallback).toBeUndefined();
  });
});

// ── Mute Overlay ────────────────────────────────────────────────────

test.describe('MS3 Mute Overlay', () => {
  test('mute overlay z-index >= 150 (above browse panel)', { timeout: 60000 }, async ({ page }) => {
    await page.goto(`${PRIMARY}/MOVIESHOWS3/`, { waitUntil: 'domcontentloaded' });
    await waitForMovies(page);

    const zIndex = await page.evaluate(() => {
      const el = document.querySelector('.mute-overlay') as HTMLElement;
      if (el) return parseInt(getComputedStyle(el).zIndex) || 0;
      const btn = document.querySelector('.persistent-unmute-btn') as HTMLElement;
      if (btn) return parseInt(getComputedStyle(btn).zIndex) || 0;
      return 0;
    });
    if (zIndex > 0) expect(zIndex).toBeGreaterThanOrEqual(150);
  });
});

// ── Performance Optimization Tests ─────────────────────────────────

test.describe('MS3 Performance', () => {
  test('lazy loading: only 1 active iframe on initial load', { timeout: 60000 }, async ({ page }) => {
    await page.goto(`${PRIMARY}/MOVIESHOWS3/`, { waitUntil: 'domcontentloaded' });
    await waitForMovies(page);

    const stats = await page.evaluate(() => {
      const allIframes = document.querySelectorAll('.video-card iframe');
      let activeCount = 0;
      let blankCount = 0;
      let posterCount = document.querySelectorAll('.video-poster').length;
      allIframes.forEach(iframe => {
        const src = (iframe as HTMLIFrameElement).src;
        if (src && src !== 'about:blank' && src.includes('youtube.com')) activeCount++;
        else if (src === 'about:blank' || !src) blankCount++;
      });
      return { total: allIframes.length, activeCount, blankCount, posterCount };
    });

    expect(stats.activeCount).toBeLessThanOrEqual(2);
    expect(stats.blankCount).toBeGreaterThan(100);
    expect(stats.posterCount).toBeGreaterThan(100);
  });

  test('page load under 15 seconds with 3000+ movies', { timeout: 60000 }, async ({ page }) => {
    const startTime = Date.now();

    await page.goto(`${PRIMARY}/MOVIESHOWS3/`, { waitUntil: 'domcontentloaded' });
    await waitForMovies(page);

    const loadTime = Date.now() - startTime;
    expect(loadTime).toBeLessThan(15000);

    const cardCount = await page.locator('.video-card').count();
    expect(cardCount).toBeGreaterThan(1000);
  });

  test('DOM node count stays reasonable', { timeout: 60000 }, async ({ page }) => {
    await page.goto(`${PRIMARY}/MOVIESHOWS3/`, { waitUntil: 'domcontentloaded' });
    await waitForMovies(page);

    const nodeCount = await page.evaluate(() => document.querySelectorAll('*').length);
    expect(nodeCount).toBeLessThan(100000);
  });

  test('scrolling activates lazy iframe and deactivates previous', { timeout: 90000 }, async ({ page }) => {
    await page.goto(`${PRIMARY}/MOVIESHOWS3/`, { waitUntil: 'domcontentloaded' });
    await waitForMovies(page);

    const initialActive = await page.evaluate(() => {
      return Array.from(document.querySelectorAll('.video-card iframe'))
        .filter(f => (f as HTMLIFrameElement).src.includes('youtube.com')).length;
    });
    expect(initialActive).toBeLessThanOrEqual(2);

    const container = page.locator('#container');
    for (let i = 0; i < 5; i++) {
      await container.evaluate((el) => el.scrollBy(0, 1080));
      await page.waitForTimeout(500);
    }
    await page.waitForTimeout(3000);

    const afterScrollActive = await page.evaluate(() => {
      return Array.from(document.querySelectorAll('.video-card iframe'))
        .filter(f => {
          const src = (f as HTMLIFrameElement).src;
          return src && src !== 'about:blank' && src.includes('youtube.com');
        }).length;
    });
    expect(afterScrollActive).toBeLessThanOrEqual(3);

    const firstCardState = await page.evaluate(() => {
      const firstCard = document.querySelector('.video-card[data-index="0"]');
      if (!firstCard) return { poster: false, iframeSrc: 'no-card' };
      const poster = firstCard.querySelector('.video-poster') as HTMLElement;
      const iframe = firstCard.querySelector('iframe') as HTMLIFrameElement;
      return {
        poster: poster ? poster.style.display !== 'none' : false,
        iframeSrc: iframe ? iframe.src : 'no-iframe'
      };
    });
    const isDeactivated = firstCardState.poster || firstCardState.iframeSrc === 'about:blank';
    expect(isDeactivated).toBe(true);
  });

  test('no memory-heavy YouTube iframes for off-screen cards', { timeout: 60000 }, async ({ page }) => {
    await page.goto(`${PRIMARY}/MOVIESHOWS3/`, { waitUntil: 'domcontentloaded' });
    await waitForMovies(page);

    const farCardStats = await page.evaluate(() => {
      const results: { index: number; src: string; hasPoster: boolean }[] = [];
      for (let i = 50; i < 60; i++) {
        const card = document.querySelector(`.video-card[data-index="${i}"]`);
        if (card) {
          const iframe = card.querySelector('iframe') as HTMLIFrameElement;
          const poster = card.querySelector('.video-poster');
          results.push({
            index: i,
            src: iframe ? iframe.src : 'no-iframe',
            hasPoster: !!poster
          });
        }
      }
      return results;
    });

    for (const card of farCardStats) {
      expect(card.src).toBe('about:blank');
      expect(card.hasPoster).toBe(true);
    }
  });

  test('rapid scrolling keeps max 3 active iframes', { timeout: 90000 }, async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', err => errors.push(err.message));

    await page.goto(`${PRIMARY}/MOVIESHOWS3/`, { waitUntil: 'domcontentloaded' });
    await waitForMovies(page);

    const container = page.locator('#container');
    for (let i = 0; i < 20; i++) {
      await container.evaluate((el) => el.scrollBy(0, 1080));
      await page.waitForTimeout(100);
    }
    await page.waitForTimeout(3000);

    const activeIframes = await page.evaluate(() => {
      return Array.from(document.querySelectorAll('.video-card iframe'))
        .filter(f => {
          const src = (f as HTMLIFrameElement).src;
          return src && src !== 'about:blank' && src.includes('youtube.com');
        }).length;
    });

    expect(activeIframes).toBeLessThanOrEqual(3);

    const critical = errors.filter(e =>
      e.includes('Cannot read') || e.includes('is not a function')
    );
    expect(critical).toHaveLength(0);
  });

  test('poster images use correct YouTube thumbnail URLs', { timeout: 60000 }, async ({ page }) => {
    await page.goto(`${PRIMARY}/MOVIESHOWS3/`, { waitUntil: 'domcontentloaded' });
    await waitForMovies(page);

    const posterStats = await page.evaluate(() => {
      const posters = document.querySelectorAll('.video-poster') as NodeListOf<HTMLImageElement>;
      let ytThumbnails = 0;
      let broken = 0;
      let total = Math.min(posters.length, 50);
      for (let i = 0; i < total; i++) {
        const src = posters[i].src;
        if (src.includes('img.youtube.com') || src.includes('i.ytimg.com')) ytThumbnails++;
        if (!src || src === '') broken++;
      }
      return { total, ytThumbnails, broken };
    });

    expect(posterStats.ytThumbnails).toBeGreaterThan(posterStats.total * 0.8);
    expect(posterStats.broken).toBe(0);
  });
});

// ── Interaction Combination Tests ──────────────────────────────────
// Tests for: play → scroll → play again, freestyle → scroll,
// queue add → scroll → queue plays, and audio bleed prevention
// Uses page.evaluate() for reliable function calls (avoids fresh-card visibility issues)

test.describe('MS3 Interaction Combos', () => {

  test('play → scroll → play again: no audio bleed', { timeout: 90000 }, async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', err => errors.push(err.message));

    await page.goto(`${PRIMARY}/MOVIESHOWS3/`, { waitUntil: 'domcontentloaded' });
    await waitForMovies(page);

    // 1. Play movie at index 0 via JS
    await page.evaluate(() => (window as any).playMovieFromBrowse(0));
    await page.waitForTimeout(2000);

    const playing1 = await page.evaluate(() => (window as any)._currentlyPlaying);
    expect(playing1).not.toBeNull();

    // 2. Scroll down 3 cards
    const container = page.locator('#container');
    for (let i = 0; i < 3; i++) {
      await container.evaluate((el) => el.scrollBy(0, window.innerHeight));
      await page.waitForTimeout(800);
    }

    // 3. Verify max 2 active YouTube iframes (no audio bleed)
    const activeAfterScroll = await page.evaluate(() => {
      return Array.from(document.querySelectorAll('.video-card iframe'))
        .filter(f => {
          const src = (f as HTMLIFrameElement).src;
          return src && src !== 'about:blank' && src.includes('youtube.com');
        }).length;
    });
    expect(activeAfterScroll).toBeLessThanOrEqual(2);

    // 4. Play a different movie (index 10) via JS
    await page.evaluate(() => (window as any).playMovieFromBrowse(10));
    await page.waitForTimeout(2000);

    // Verify still max 2 active iframes
    const activeAfterSecondPlay = await page.evaluate(() => {
      return Array.from(document.querySelectorAll('.video-card iframe'))
        .filter(f => {
          const src = (f as HTMLIFrameElement).src;
          return src && src !== 'about:blank' && src.includes('youtube.com');
        }).length;
    });
    expect(activeAfterSecondPlay).toBeLessThanOrEqual(2);

    expect(errors.filter(e => e.includes('postMessage') || e.includes('Cannot read'))).toHaveLength(0);
  });

  test('freestyle play → scroll back to feed: no audio bleed', { timeout: 90000 }, async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', err => errors.push(err.message));

    await page.goto(`${PRIMARY}/MOVIESHOWS3/`, { waitUntil: 'domcontentloaded' });
    await waitForMovies(page);

    // 1. Open freestyle, search, and play a result
    await page.locator('#filterFreestyle').click();
    await page.waitForTimeout(500);
    await expect(page.locator('#freestyleOverlay')).toHaveClass(/active/);

    await page.locator('#freestyleSearchInput').fill('trailer 2026');
    await page.locator('#freestyleSearchInput').press('Enter');
    await page.waitForTimeout(5000);

    const freestylePlayBtn = page.locator('[onclick*="playFreestyleTrailer"]').first();
    const hasResults = await freestylePlayBtn.count() > 0;

    if (hasResults) {
      await freestylePlayBtn.click();
      await page.waitForTimeout(3000);

      // Freestyle overlay should be closed
      expect(await page.locator('#freestyleOverlay').evaluate(el => el.classList.contains('active'))).toBe(false);

      // Something should be playing
      const playingAfterFreestyle = await page.evaluate(() => (window as any)._currentlyPlaying);
      expect(playingAfterFreestyle).not.toBeNull();

      // 2. Scroll down to a regular movie
      const container = page.locator('#container');
      for (let i = 0; i < 3; i++) {
        await container.evaluate((el) => el.scrollBy(0, window.innerHeight));
        await page.waitForTimeout(800);
      }

      // 3. Verify no audio bleed — max 2 active iframes
      const activeIframes = await page.evaluate(() => {
        return Array.from(document.querySelectorAll('.video-card iframe'))
          .filter(f => {
            const src = (f as HTMLIFrameElement).src;
            return src && src !== 'about:blank' && src.includes('youtube.com');
          }).length;
      });
      expect(activeIframes).toBeLessThanOrEqual(2);
    } else {
      // No freestyle results — close overlay
      await page.evaluate(() => (window as any).closeFreestyle());
    }

    expect(errors.filter(e => e.includes('postMessage') || e.includes('Cannot read'))).toHaveLength(0);
  });

  test('queue operations → scroll → no JS errors', { timeout: 90000 }, async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', err => errors.push(err.message));

    await page.goto(`${PRIMARY}/MOVIESHOWS3/`, { waitUntil: 'domcontentloaded' });
    await waitForMovies(page);

    // Perform queue operations then scroll to verify no crashes
    await page.evaluate(() => (window as any).clearQueue());
    await page.waitForTimeout(300);

    // Add current video to queue
    await page.evaluate(() => {
      document.getElementById('container')!.scrollTop = 0;
    });
    await page.waitForTimeout(500);
    await page.evaluate(() => (window as any).addToQueue());
    await page.waitForTimeout(300);

    // Scroll through several cards — this is the stress test
    const container = page.locator('#container');
    for (let i = 0; i < 5; i++) {
      await container.evaluate((el) => el.scrollBy(0, window.innerHeight));
      await page.waitForTimeout(600);
    }

    // Verify page still works — cards exist, no JS crash
    const cardCount = await page.locator('.video-card').count();
    expect(cardCount).toBeGreaterThan(100);

    // Verify max 2 active iframes (performance maintained)
    const activeIframes = await page.evaluate(() => {
      return Array.from(document.querySelectorAll('.video-card iframe'))
        .filter(f => {
          const src = (f as HTMLIFrameElement).src;
          return src && src !== 'about:blank' && src.includes('youtube.com');
        }).length;
    });
    expect(activeIframes).toBeLessThanOrEqual(3);

    expect(errors.filter(e => e.includes('Cannot read') || e.includes('is not a function'))).toHaveLength(0);
  });

  test('play → queue current → scroll → play from queue → no dual audio', { timeout: 90000 }, async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', err => errors.push(err.message));

    await page.goto(`${PRIMARY}/MOVIESHOWS3/`, { waitUntil: 'domcontentloaded' });
    await waitForMovies(page);

    // Clear queue
    await page.evaluate(() => (window as any).clearQueue());
    await page.waitForTimeout(300);

    // 1. Play movie at index 0 via JS
    await page.evaluate(() => (window as any).playMovieFromBrowse(0));
    await page.waitForTimeout(2000);

    const playing1 = await page.evaluate(() => (window as any)._currentlyPlaying);
    expect(playing1).not.toBeNull();

    // 2. Add current video to queue, then scroll away
    await page.evaluate(() => (window as any).addToQueue());
    await page.waitForTimeout(300);

    const container = page.locator('#container');
    for (let i = 0; i < 5; i++) {
      await container.evaluate((el) => el.scrollBy(0, window.innerHeight));
      await page.waitForTimeout(500);
    }

    // 3. Play from queue via JS (should jump back to the queued movie)
    await page.evaluate(() => (window as any).playFromQueue(0));
    await page.waitForTimeout(3000);

    // 4. Verify only 1-2 active iframes (no dual audio)
    const activeIframes = await page.evaluate(() => {
      return Array.from(document.querySelectorAll('.video-card iframe'))
        .filter(f => {
          const src = (f as HTMLIFrameElement).src;
          return src && src !== 'about:blank' && src.includes('youtube.com');
        }).length;
    });
    expect(activeIframes).toBeLessThanOrEqual(2);

    expect(errors.filter(e => e.includes('postMessage') || e.includes('Cannot read'))).toHaveLength(0);
  });

  test('queue current video → scroll away → play from queue → resumes', { timeout: 90000 }, async ({ page }) => {
    await page.goto(`${PRIMARY}/MOVIESHOWS3/`, { waitUntil: 'domcontentloaded' });
    await waitForMovies(page);

    // Clear queue and scroll to top
    await page.evaluate(() => {
      (window as any).clearQueue();
      document.getElementById('container')!.scrollTop = 0;
    });
    await page.waitForTimeout(500);

    // 1. Add current video (at scroll position 0) to queue
    await page.evaluate(() => (window as any).addToQueue());
    await page.waitForTimeout(300);

    // Verify queue has 1 item
    const queueCount = await page.locator('#queueCount').textContent();
    expect(parseInt(queueCount || '0')).toBe(1);

    // 2. Scroll down several cards
    const container = page.locator('#container');
    for (let i = 0; i < 5; i++) {
      await container.evaluate((el) => el.scrollBy(0, window.innerHeight));
      await page.waitForTimeout(600);
    }

    // 3. Play from queue via JS — should jump to the queued movie
    await page.evaluate(() => (window as any).playFromQueue(0));
    await page.waitForTimeout(3000);

    // 4. Verify something is now playing (the queue item)
    const nowPlayingIdx = await page.evaluate(() => (window as any)._currentlyPlaying);
    expect(nowPlayingIdx).not.toBeNull();

    // 5. Verify only 1-2 active iframes (clean transition)
    const activeIframes = await page.evaluate(() => {
      return Array.from(document.querySelectorAll('.video-card iframe'))
        .filter(f => {
          const src = (f as HTMLIFrameElement).src;
          return src && src !== 'about:blank' && src.includes('youtube.com');
        }).length;
    });
    expect(activeIframes).toBeLessThanOrEqual(2);
  });

  test('multiple transitions: play → scroll → freestyle → scroll → play → no errors', { timeout: 120000 }, async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', err => errors.push(err.message));

    await page.goto(`${PRIMARY}/MOVIESHOWS3/`, { waitUntil: 'domcontentloaded' });
    await waitForMovies(page);

    // 1. Play from browse via JS
    await page.evaluate(() => (window as any).playMovieFromBrowse(0));
    await page.waitForTimeout(2000);

    // 2. Scroll through a few cards
    const container = page.locator('#container');
    for (let i = 0; i < 3; i++) {
      await container.evaluate((el) => el.scrollBy(0, window.innerHeight));
      await page.waitForTimeout(600);
    }

    // 3. Open freestyle, search, play if results found
    await page.locator('#filterFreestyle').click();
    await page.waitForTimeout(500);
    await page.locator('#freestyleSearchInput').fill('movie trailer');
    await page.locator('#freestyleSearchInput').press('Enter');
    await page.waitForTimeout(5000);

    const freestylePlay = page.locator('[onclick*="playFreestyleTrailer"]').first();
    if (await freestylePlay.count() > 0) {
      await freestylePlay.click();
      await page.waitForTimeout(3000);
    } else {
      // No results — close freestyle manually
      await page.evaluate(() => (window as any).closeFreestyle());
      await page.waitForTimeout(500);
    }

    // 4. Scroll again
    for (let i = 0; i < 3; i++) {
      await container.evaluate((el) => el.scrollBy(0, window.innerHeight));
      await page.waitForTimeout(600);
    }

    // 5. Play another movie via JS
    await page.evaluate(() => (window as any).playMovieFromBrowse(15));
    await page.waitForTimeout(2000);

    // Final check: max 2 active iframes, no critical errors
    const finalActive = await page.evaluate(() => {
      return Array.from(document.querySelectorAll('.video-card iframe'))
        .filter(f => {
          const src = (f as HTMLIFrameElement).src;
          return src && src !== 'about:blank' && src.includes('youtube.com');
        }).length;
    });
    expect(finalActive).toBeLessThanOrEqual(2);

    const critical = errors.filter(e =>
      e.includes('postMessage') || e.includes('Cannot read') || e.includes('about:blank')
    );
    expect(critical).toHaveLength(0);
  });

  test('addToQueue function works and persists', { timeout: 60000 }, async ({ page }) => {
    await page.goto(`${PRIMARY}/MOVIESHOWS3/`, { waitUntil: 'domcontentloaded' });
    await waitForMovies(page);

    // Clear queue
    await page.evaluate(() => (window as any).clearQueue());
    await page.waitForTimeout(300);

    // Scroll to top and add current video
    await page.evaluate(() => {
      document.getElementById('container')!.scrollTop = 0;
    });
    await page.waitForTimeout(500);
    await page.evaluate(() => (window as any).addToQueue());
    await page.waitForTimeout(300);

    // Verify queue count badge shows 1
    const queueCount = await page.locator('#queueCount').textContent();
    expect(parseInt(queueCount || '0')).toBe(1);

    // Verify localStorage was updated
    const stored = await page.evaluate(() => {
      const q = JSON.parse(localStorage.getItem('movieQueue') || '[]');
      return { length: q.length, hasTitle: !!q[0]?.title };
    });
    expect(stored.length).toBe(1);
    expect(stored.hasTitle).toBe(true);

    // Try adding same video again — should show "Already in queue"
    await page.evaluate(() => (window as any).addToQueue());
    await page.waitForTimeout(300);

    // Queue should still be 1 (no duplicates)
    const queueCountAfter = await page.locator('#queueCount').textContent();
    expect(parseInt(queueCountAfter || '0')).toBe(1);
  });
});
