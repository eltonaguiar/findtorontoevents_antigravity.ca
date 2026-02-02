import { test, expect } from '@playwright/test';

/**
 * Verify localhost GUEST user sees personal notes for at least one creator (e.g. Starfireara).
 * With mock: serve_local returns fake note. With real MySQL: set FAVCREATORS_API_PROXY so API is proxied to live site.
 *
 * Mock:  python tools/serve_local.py
 * Real: FAVCREATORS_API_PROXY=https://findtorontoevents.ca python tools/serve_local.py
 * Then: PLAYWRIGHT_BASE_URL=http://localhost:PORT npx playwright test tests/favcreators-guest-notes-local.spec.ts
 *
 * If you see "get_notes.php returned PHP/HTML": stop Vite/npx serve on that port and run serve_local.
 */
const BASE = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:5173';
const FAV_GUEST = `${BASE}/fc/#/guest`;

test.describe('FavCreators localhost guest: personal notes', () => {

  test('guest sees at least one personal note (e.g. Starfireara) from get_notes', async ({ page }) => {
    const getNotesPromise = page.waitForResponse(
      (res) => res.url().includes('get_notes.php') && res.status() === 200,
      { timeout: 20000 }
    );

    await page.goto(FAV_GUEST, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await expect(page.locator('#root')).toBeVisible({ timeout: 15000 });

    const response = await getNotesPromise;
    const text = await response.text();

    if (text.trim().startsWith('<?php') || text.trim().startsWith('<!')) {
      throw new Error(
        'get_notes.php returned PHP/HTML instead of JSON. ' +
        'Stop any other server on port 5173 (Vite, npx serve, etc.) and run: python tools/serve_local.py'
      );
    }

    let body: Record<string, string>;
    try {
      body = JSON.parse(text) as Record<string, string>;
    } catch {
      throw new Error(
        'get_notes.php did not return valid JSON. Run: python tools/serve_local.py (from project root) on port 5173.'
      );
    }

    expect(typeof body === 'object' && body !== null).toBe(true);

    // If proxied to live site and DB fails, body may have "error"
    if (Object.prototype.hasOwnProperty.call(body, 'error')) {
      throw new Error(`API returned error (check MySQL on server): ${(body as { error?: string }).error}`);
    }

    // At least one creator note (Starfireara = creator_id "6") so guest sees a personal note (mock or real MySQL)
    const hasNote = Object.prototype.hasOwnProperty.call(body, '6') && typeof body['6'] === 'string' && body['6'].length > 0;
    expect(hasNote).toBe(true);

    // App displays the note in the personal note field for Starfireara
    const noteField = page.locator('#note-6');
    await noteField.scrollIntoViewIfNeeded().catch(() => {});
    await expect(noteField).toBeVisible({ timeout: 10000 });
    await expect(noteField).toHaveValue(body['6'], { timeout: 8000 });
  });
});
