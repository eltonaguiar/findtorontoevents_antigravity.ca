import { test, expect } from '@playwright/test';

/**
 * Verify that the FavCreators app retrieves notes FROM THE DATABASE on the remote site.
 * get_notes.php runs on the server and returns creator_defaults + user_notes; the app displays them.
 *
 * Run against REMOTE only (so PHP hits the real DB):
 *   VERIFY_REMOTE=1 npx playwright test tests/favcreators-db-notes-remote.spec.ts
 *
 * Or: npm run verify:remote (then run this spec with VERIFY_REMOTE=1).
 */
const BASE = process.env.VERIFY_REMOTE_URL || process.env.VERIFY_REMOTE === '1'
  ? (process.env.VERIFY_REMOTE_URL || 'https://findtorontoevents.ca').replace(/\/$/, '')
  : (process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:5173');
const FAV_GUEST = `${BASE}/fc/#/guest`;

test.describe('FavCreators: retrieve notes from database (remote)', () => {

  test('get_notes.php returns JSON from database and app displays Starfireara note', async ({ page }) => {
    // Listen for get_notes.php before navigation
    const getNotesPromise = page.waitForResponse(
      (res) => res.url().includes('get_notes.php') && res.status() === 200,
      { timeout: 20000 }
    );

    await page.goto(FAV_GUEST, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await expect(page.locator('#root')).toBeVisible({ timeout: 15000 });

    const response = await getNotesPromise;
    const text = await response.text();

    // Assert backend returned valid JSON (from DB, not PHP source or error)
    let body: Record<string, string>;
    try {
      body = JSON.parse(text) as Record<string, string>;
    } catch {
      throw new Error(
        `get_notes.php did not return JSON (database/API issue). Got: ${text.slice(0, 120)}...`
      );
    }

    expect(typeof body).toBe('object');
    expect(body !== null).toBe(true);

    // Starfireara = creator_id "6". DB may have a note in creator_defaults or user_notes.
    const hasStarfirearaNote = Object.prototype.hasOwnProperty.call(body, '6');
    if (hasStarfirearaNote) {
      expect(typeof body['6']).toBe('string');
      expect(body['6'].length).toBeGreaterThan(0);
    }

    // Assert app shows Starfireara card and note field
    const starfirearaHeading = page.getByRole('heading', { name: 'Starfireara' });
    await expect(starfirearaHeading).toBeVisible({ timeout: 10000 });

    const noteField = page.locator('#note-6');
    await noteField.scrollIntoViewIfNeeded().catch(() => {});
    await expect(noteField).toBeVisible({ timeout: 10000 });

    // If DB returned a note for creator_id 6, the app should display it
    const displayedNote = await noteField.inputValue();
    if (hasStarfirearaNote && body['6'].length > 0) {
      expect(displayedNote).toBe(body['6']);
    }
    // At least assert the note field exists (retrieval path works)
    expect(await noteField.isVisible()).toBe(true);
  });

  test('get_notes.php response is JSON object (not PHP/HTML/error)', async ({ page }) => {
    const getNotesPromise = page.waitForResponse(
      (res) => res.url().includes('get_notes.php') && res.status() === 200,
      { timeout: 20000 }
    );

    await page.goto(FAV_GUEST, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await expect(page.locator('#root')).toBeVisible({ timeout: 15000 });

    const response = await getNotesPromise;
    const text = await response.text();

    // Must be JSON
    if (text.trim().startsWith('<?php') || text.trim().startsWith('<!')) {
      throw new Error('get_notes.php returned PHP/HTML instead of JSON. Check server executes PHP.');
    }
    let body: unknown;
    try {
      body = JSON.parse(text);
    } catch {
      throw new Error(`get_notes.php returned non-JSON: ${text.slice(0, 100)}...`);
    }
    expect(typeof body === 'object' && body !== null).toBe(true);
  });
});
