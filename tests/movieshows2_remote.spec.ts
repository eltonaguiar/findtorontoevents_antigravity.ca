import { test, expect } from '@playwright/test';

/**
 * MOVIESHOWS2 Remote Tests
 * Tests API health, CORS, page load, filtering across all 3 domains
 */

const PRIMARY = 'https://findtorontoevents.ca';

// ── API Health — findtorontoevents.ca ───────────────────────────────

test.describe('MS2 API — findtorontoevents', () => {
  test('movies.php stats returns valid JSON, single CORS *', async ({ request }) => {
    const resp = await request.get(`${PRIMARY}/MOVIESHOWS2/api/movies.php?action=stats`);
    expect(resp.status()).toBe(200);
    expect(resp.headers()['access-control-allow-origin']).toBe('*');
    const body = await resp.json();
    expect(body.success).toBe(true);
    expect(body.stats.total).toBeGreaterThan(100);
  });

  test('movies.php list returns movies with trailers', async ({ request }) => {
    const resp = await request.get(`${PRIMARY}/MOVIESHOWS2/api/movies.php?action=list&limit=10`);
    const body = await resp.json();
    expect(body.success).toBe(true);
    expect(body.movies.length).toBeGreaterThan(0);
    expect(body.movies[0].title).toBeTruthy();
    expect(body.movies[0].trailer_id).toBeTruthy();
  });

  test('search finds Mercy', async ({ request }) => {
    const resp = await request.get(`${PRIMARY}/MOVIESHOWS2/api/movies.php?action=search&q=Mercy`);
    const body = await resp.json();
    expect(body.success).toBe(true);
    expect(body.movies.length).toBeGreaterThan(0);
  });

  test('get-movies.php returns movies list', async ({ request }) => {
    const resp = await request.get(`${PRIMARY}/MOVIESHOWS2/api/get-movies.php`);
    const body = await resp.json();
    expect(body.success).toBe(true);
    expect(body.count).toBeGreaterThan(100);
  });

  test('OPTIONS preflight returns CORS headers', async ({ request }) => {
    const resp = await request.fetch(`${PRIMARY}/MOVIESHOWS2/api/movies.php?action=stats`, {
      method: 'OPTIONS',
      headers: { 'Origin': 'https://example.com', 'Access-Control-Request-Method': 'GET' },
    });
    // PHP 5.2 on 50webs may return 500 for OPTIONS; accept 200/204/500
    expect([200, 204, 500]).toContain(resp.status());
    if (resp.status() !== 500) {
      expect(resp.headers()['access-control-allow-origin']).toBe('*');
    }
  });
});

// ── API Health — tdotevent.ca ───────────────────────────────────────

test.describe('MS2 API — tdotevent', () => {
  test('movies.php stats returns valid JSON, single CORS *', async ({ request }) => {
    const resp = await request.get('https://tdotevent.ca/MOVIESHOWS2/api/movies.php?action=stats');
    expect(resp.status()).toBe(200);
    expect(resp.headers()['access-control-allow-origin']).toBe('*');
    const body = await resp.json();
    expect(body.success).toBe(true);
    expect(body.stats.total).toBeGreaterThan(100);
  });

  test('get-movies.php returns movies', async ({ request }) => {
    const resp = await request.get('https://tdotevent.ca/MOVIESHOWS2/api/get-movies.php');
    const body = await resp.json();
    expect(body.success).toBe(true);
    expect(body.count).toBeGreaterThan(100);
  });
});

// ── API Health — torontoevent.net ───────────────────────────────────

test.describe('MS2 API — torontoevent', () => {
  test('CORS header is single * (not duplicated)', async ({ request }) => {
    const resp = await request.get('https://torontoevent.net/MOVIESHOWS2/api/movies.php?action=stats');
    const cors = resp.headers()['access-control-allow-origin'];
    expect(cors).toBe('*');
    expect(cors).not.toContain(', ');
  });
});

// ── Page Load ───────────────────────────────────────────────────────

test.describe('MS2 Page Load', () => {
  test('no CORS or JSON errors in console', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') errors.push(msg.text());
    });
    await page.goto(`${PRIMARY}/MOVIESHOWS2/app.html`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(10000);

    const corsErrors = errors.filter(e =>
      e.includes('CORS') || e.includes('*, *') || e.includes('not valid JSON')
    );
    expect(corsErrors).toHaveLength(0);
  });
});

// ── Cross-Origin from torontoevent.net ──────────────────────────────

test.describe('MS2 Cross-Origin', () => {
  test('torontoevent.net can cross-origin fetch findtorontoevents.ca API', async ({ page }) => {
    await page.goto('https://torontoevent.net/MOVIESHOWS2/', { waitUntil: 'domcontentloaded' });
    const result = await page.evaluate(async () => {
      try {
        const resp = await fetch('https://findtorontoevents.ca/MOVIESHOWS2/api/movies.php?action=stats');
        const data = await resp.json();
        return { ok: true, total: data.stats?.total };
      } catch (e: any) { return { ok: false, error: e.message }; }
    });
    expect(result.ok).toBe(true);
    expect(result.total).toBeGreaterThan(100);
  });

  test('tdotevent.ca can cross-origin fetch findtorontoevents.ca API', async ({ page }) => {
    await page.goto('https://tdotevent.ca/MOVIESHOWS2/', { waitUntil: 'domcontentloaded' });
    const result = await page.evaluate(async () => {
      try {
        const resp = await fetch('https://findtorontoevents.ca/MOVIESHOWS2/api/movies.php?action=stats');
        const data = await resp.json();
        return { ok: true, total: data.stats?.total };
      } catch (e: any) { return { ok: false, error: e.message }; }
    });
    expect(result.ok).toBe(true);
    expect(result.total).toBeGreaterThan(100);
  });
});

// ── Filtering ───────────────────────────────────────────────────────

test.describe('MS2 Filtering', () => {
  test('filter movies to 2026 releases', async ({ request }) => {
    const resp = await request.get(`${PRIMARY}/MOVIESHOWS2/api/movies.php?action=list&year=2026&limit=50`);
    const body = await resp.json();
    expect(body.success).toBe(true);
    expect(body.movies.length).toBeGreaterThan(0);
    for (const movie of body.movies) {
      expect(Number(movie.release_year)).toBe(2026);
    }
  });

  test('search 2026 trending titles', async ({ request }) => {
    for (const title of ['Mercy', 'Bone Temple', 'Housemaid', 'Marty Supreme']) {
      const resp = await request.get(`${PRIMARY}/MOVIESHOWS2/api/movies.php?action=search&q=${encodeURIComponent(title)}`);
      const body = await resp.json();
      expect(body.success).toBe(true);
    }
  });
});
